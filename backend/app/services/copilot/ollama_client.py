"""Loopback-only Ollama adapter. Never pulls models or falls back to a cloud API."""

import json
import re
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

import httpx

from app.config import Settings
from app.services.copilot.llm_client import (
    LLMContextError,
    LLMLocalError,
    LLMMessage,
    LLMReply,
    ToolCall,
    ToolDefinition,
)


class OllamaLLMClient:
    ground_tool_results = True

    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.settings = settings
        self.transport = transport

    def _payload(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition], stream: bool
    ) -> dict[str, Any]:
        thinking = "-instruct" not in (self.settings.llm_model or "")
        if (self.settings.llm_model or "").startswith("qwen3") and thinking:
            system += "\n/no_think"
        turns = [{"role": "system", "content": system}]
        for message in messages:
            turn = {"role": message.role, "content": message.content or ""}
            if message.tool_calls:
                turn["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {"name": c.name, "arguments": c.arguments},
                    }
                    for c in message.tool_calls
                ]
            if message.role == "tool":
                turn.update(tool_name=message.tool_name, tool_call_id=message.tool_call_id)
            turns.append(turn)
        definitions = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]
        # Deliberately fail rather than silently truncate metrics. UTF-8 byte count is a
        # conservative upper estimate; the runtime's tokenizer may accept larger prompts.
        size = len(json.dumps([turns, definitions], ensure_ascii=False).encode("utf-8"))
        if size > self.settings.llm_context - 1024:
            raise LLMContextError("Local context budget exceeded; request fewer runs/epochs")
        payload = {
            "model": self.settings.llm_model,
            "messages": turns,
            "tools": definitions,
            "stream": stream,
            "keep_alive": "30s",
            "options": {
                "num_ctx": self.settings.llm_context,
                "temperature": 0,
                "num_predict": 1024,
            },
        }
        if thinking:
            payload["think"] = False
        return payload

    async def release(self) -> None:
        """Keep the model through tool rounds, then release VRAM at chat completion."""
        try:
            async with self._client() as client:
                response = await client.post(
                    "/api/generate",
                    json={"model": self.settings.llm_model, "keep_alive": 0, "stream": False},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMLocalError(
                "Unable to unload local model; it expires after 30 seconds"
            ) from exc

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.llm_base_url,
            timeout=self.settings.llm_timeout,
            trust_env=False,
            follow_redirects=False,
            transport=self.transport,
        )

    @staticmethod
    def _reply(message: Any) -> LLMReply:
        if not isinstance(message, dict):
            raise LLMLocalError("Malformed local message")
        calls = []
        call_ids = set()
        try:
            for call in message.get("tool_calls") or []:
                function = call["function"]
                arguments = function["arguments"]
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                if not isinstance(arguments, dict) or not isinstance(function["name"], str):
                    raise ValueError("Invalid tool arguments")
                call_id = call.get("id")
                if not isinstance(call_id, str) or not call_id or call_id in call_ids:
                    call_id = uuid4().hex
                call_ids.add(call_id)
                calls.append(ToolCall(call_id, function["name"], arguments))
            content = message.get("content") or ""
            if not isinstance(content, str):
                raise ValueError("Invalid content")
            # Some Qwen templates embed reasoning even with think=False. Buffering
            # permits complete redaction before any text reaches the UI.
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            # A provider may prefill the opening reasoning marker in its template;
            # then only the closing marker occurs in generated content.
            if "</think>" in content and "<think>" not in content:
                content = content.rsplit("</think>", 1)[1].strip()
            if "<think>" in content or "</think>" in content:
                raise ValueError("Unterminated reasoning")
            if not content.strip() and not calls:
                raise ValueError("Empty local response")
            return LLMReply(text=content or None, tool_calls=calls)
        except (KeyError, TypeError, ValueError) as exc:
            raise LLMLocalError("Malformed/empty local reply or tool arguments") from exc

    async def complete(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> LLMReply:
        payload = self._payload(system, messages, tools, False)
        try:
            async with self._client() as client:
                response = await client.post("/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("error") or not data.get("done"):
                    raise LLMLocalError("Local runtime did not complete the response")
                if data.get("done_reason") == "length":
                    raise LLMContextError("Local output budget exceeded; narrow the question")
                return self._reply(data.get("message"))
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            raise LLMLocalError(
                "Local runtime unavailable, timed out, or model not installed"
            ) from exc

    async def stream(
        self, system: str, messages: list[LLMMessage], tools: list[ToolDefinition]
    ) -> AsyncIterator[str | LLMReply]:
        # Buffer one bounded native NDJSON response: validate it before displaying text,
        # so malformed tool calls or reasoning can never leak into the chat UI.
        payload = self._payload(system, messages, tools, True)
        content, calls, done = [], [], False
        try:
            async with self._client() as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        if data.get("error"):
                            raise LLMLocalError("Local streaming error")
                        msg = data.get("message", {})
                        content.append(msg.get("content", ""))
                        calls.extend(msg.get("tool_calls") or [])
                        if sum(map(len, content)) > 100_000:
                            raise LLMLocalError("Local response too large")
                        if data.get("done"):
                            if data.get("done_reason") == "length":
                                raise LLMContextError("Local output budget exceeded")
                            done = True
                            break
            if not done:
                raise LLMLocalError("Local stream ended before completion")
            reply = self._reply({"content": "".join(content), "tool_calls": calls})
        except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise LLMLocalError("Local streaming response failed") from exc
        if reply.text and not reply.tool_calls:
            for start in range(0, len(reply.text), 80):
                yield reply.text[start : start + 80]
        yield reply
