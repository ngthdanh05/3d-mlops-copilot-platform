"""LLM access behind one interface. A real provider plugs in at `get_llm_client`."""

import json
import re
import unicodedata
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal, Protocol

from google import genai
from google.genai import errors, types

from app.config import get_settings

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
_GEMINI_TIMEOUT_MS = 30_000


class LLMError(Exception):
    """The provider failed (timeout, malformed reply...)."""


class LLMRateLimitError(LLMError):
    """The provider's quota is used up for now."""


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMMessage:
    role: Literal["user", "assistant", "tool"]
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    tool_name: str | None = None
    provider_content: Any = None  # the assistant turn exactly as the provider returned it


@dataclass(frozen=True)
class LLMReply:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    provider_content: Any = None


class LLMClient(Protocol):
    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply: ...

    def stream(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> AsyncIterator[str | LLMReply]:
        """Yield text as it is written, then the complete reply as the last item."""
        ...


_BEST_RUN_PHRASES = ("tốt nhất", "cao nhất", "thấp nhất", "best")
_FAKE_PREFIX = "[LLM giả lập]"


class FakeLLMClient:
    """Stand-in that needs no API key and follows the same tool-calling protocol.

    It only understands "which run is best" questions, and every number in its
    answer comes from the tool result, as a real model is instructed to do.
    """

    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply:
        question = unicodedata.normalize("NFC", messages[0].content or "").lower()
        if not any(phrase in question for phrase in _BEST_RUN_PHRASES):
            return LLMReply(text=f"{_FAKE_PREFIX} Hiện chỉ trả lời được câu hỏi tìm run tốt nhất.")

        tool_messages = [m for m in messages if m.role == "tool"]
        if not tool_messages:
            metric = "val_loss" if "loss" in question else "val_accuracy"
            return LLMReply(tool_calls=[ToolCall("1", "find_best_runs", {"metric": metric})])

        result = json.loads(tool_messages[0].content or "{}")
        if "error" in result:
            return LLMReply(text=f"{_FAKE_PREFIX} Không tra cứu được: {result['error']}")
        if not result["runs"]:
            return LLMReply(
                text=f"{_FAKE_PREFIX} Chưa có run hoàn thành nào có {result['metric']}."
            )

        best = result["runs"][0]
        return LLMReply(
            text=(
                f"{_FAKE_PREFIX} {best['run_name']} có {result['metric']} "
                f"tốt nhất: {best['value']:.4f}."
            )
        )

    async def stream(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> AsyncIterator[str | LLMReply]:
        reply = await self.complete(system, messages, tools)
        for word in re.findall(r"\S+\s*", reply.text or ""):
            yield word
        yield reply


def _to_gemini_contents(messages: list[LLMMessage]) -> list[types.Content]:
    contents: list[types.Content] = []
    previous_role: str | None = None
    for message in messages:
        if message.role == "user":
            contents.append(
                types.Content(role="user", parts=[types.Part.from_text(text=message.content or "")])
            )
        elif message.role == "assistant":
            # Resent unchanged: its parts can carry thought signatures the model needs back.
            contents.append(message.provider_content)
        else:
            part = types.Part(
                function_response=types.FunctionResponse(
                    id=message.tool_call_id or None,
                    name=message.tool_name,
                    response=json.loads(message.content or "{}"),
                )
            )
            if previous_role == "tool":
                contents[-1].parts = [*(contents[-1].parts or []), part]
            else:
                # The API rejects role="tool": function results are sent as a user turn.
                contents.append(types.Content(role="user", parts=[part]))
        previous_role = message.role
    return contents


def _first_candidate_content(response: types.GenerateContentResponse) -> types.Content | None:
    return response.candidates[0].content if response.candidates else None


def _reply_from_content(content: types.Content | None) -> LLMReply:
    parts = (content.parts if content else None) or []
    return LLMReply(
        text="".join(p.text for p in parts if p.text and not p.thought) or None,
        tool_calls=[
            ToolCall(
                id=p.function_call.id or "",
                name=p.function_call.name or "",
                arguments=p.function_call.args or {},
            )
            for p in parts
            if p.function_call
        ],
        provider_content=content,
    )


@contextmanager
def _provider_errors() -> Iterator[None]:
    """Turn every SDK failure into the errors the copilot engine handles."""
    try:
        yield
    except errors.APIError as exc:
        if exc.code == 429:
            raise LLMRateLimitError("Gemini quota exceeded") from exc
        raise LLMError(f"Gemini API error {exc.code}") from exc
    except Exception as exc:  # network and timeout errors from the SDK's HTTP library
        raise LLMError(f"Gemini request failed: {type(exc).__name__}") from exc


class GeminiLLMClient:
    def __init__(self, client: genai.Client, model: str) -> None:
        self._client = client
        self._model = model

    def _config(self, system: str, tools: list[ToolDefinition]) -> types.GenerateContentConfig:
        declarations = [
            types.FunctionDeclaration(
                name=tool.name,
                description=tool.description,
                parameters_json_schema=tool.parameters,
            )
            for tool in tools
        ]
        return types.GenerateContentConfig(
            system_instruction=system,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply:
        with _provider_errors():
            response = await self._client.aio.models.generate_content(
                model=self._model,
                contents=_to_gemini_contents(messages),
                config=self._config(system, tools),
            )
        return _reply_from_content(_first_candidate_content(response))

    async def stream(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> AsyncIterator[str | LLMReply]:
        parts: list[types.Part] = []
        with _provider_errors():
            chunks = await self._client.aio.models.generate_content_stream(
                model=self._model,
                contents=_to_gemini_contents(messages),
                config=self._config(system, tools),
            )
            async for chunk in chunks:
                content = _first_candidate_content(chunk)
                for part in (content.parts if content else None) or []:
                    parts.append(part)
                    if part.text and not part.thought:
                        yield part.text
        # Every part is kept: thought signatures must go back to the model unchanged.
        yield _reply_from_content(types.Content(role="model", parts=parts))


@lru_cache
def get_llm_client() -> LLMClient:
    """Gemini when `LLM_API_KEY` is set, otherwise the stand-in."""
    settings = get_settings()
    if not settings.llm_api_key:
        return FakeLLMClient()
    client = genai.Client(
        api_key=settings.llm_api_key,
        http_options=types.HttpOptions(timeout=_GEMINI_TIMEOUT_MS),
    )
    return GeminiLLMClient(client, settings.llm_model or DEFAULT_GEMINI_MODEL)
