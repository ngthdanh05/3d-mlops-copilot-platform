"""LLM access behind one interface. A real provider plugs in at `get_llm_client`."""

import json
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


class LLMError(Exception):
    """The provider failed (timeout, quota, malformed reply...)."""


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


@dataclass(frozen=True)
class LLMReply:
    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(Protocol):
    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply: ...


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
        if len(tool_messages) == 1:
            return LLMReply(
                tool_calls=[
                    ToolCall("2", "highlight_runs", {"run_ids": [best["run_id"]]}),
                    ToolCall("3", "focus_camera", {"run_id": best["run_id"]}),
                ]
            )
        return LLMReply(
            text=(
                f"{_FAKE_PREFIX} {best['run_name']} có {result['metric']} "
                f"tốt nhất: {best['value']:.4f}."
            )
        )


def get_llm_client() -> LLMClient:
    """Return the configured client. Only the stand-in exists until a provider is chosen."""
    return FakeLLMClient()
