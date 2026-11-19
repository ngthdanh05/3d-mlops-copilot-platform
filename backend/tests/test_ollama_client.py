import json

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.services.copilot.llm_client import LLMError, LLMMessage, LLMReply, ToolDefinition
from app.services.copilot.ollama_client import OllamaLLMClient


def settings(**kwargs):
    return Settings(_env_file=None, llm_provider="ollama", llm_model="qwen3:4b", **kwargs)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://192.168.1.2:11434",
        "http://localhost@evil.com",
        "http://localhost/path",
    ],
)
def test_external_endpoints_refused(url):
    with pytest.raises(ValidationError):
        settings(llm_base_url=url)


async def test_model_is_kept_between_tool_rounds_then_explicitly_released():
    requests = []

    def handler(request):
        requests.append((request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"done": True, "message": {"content": "ok"}})

    client = OllamaLLMClient(settings(), httpx.MockTransport(handler))
    await client.complete("s", [], [])
    await client.release()
    assert requests[0][1]["keep_alive"] == "30s"
    assert requests[1] == ("/api/generate", {"model": "qwen3:4b", "keep_alive": 0, "stream": False})


def test_instruct_request_omits_unsupported_thinking_switch():
    config = Settings(
        _env_file=None, llm_provider="ollama", llm_model="qwen3:4b-instruct-2507-q4_K_M"
    )
    payload = OllamaLLMClient(config)._payload("s", [], [], False)
    assert "think" not in payload


async def test_tools_round_trip_and_ids():
    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        assert body["think"] is False
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "done": True,
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "find_best_runs",
                                    "arguments": {"metric": "accuracy"},
                                }
                            }
                        ]
                    },
                },
            )
        assert body["messages"][-1]["tool_name"] == "find_best_runs"
        assert body["messages"][-1]["tool_call_id"]
        return httpx.Response(200, json={"done": True, "message": {"content": "Run A: 0.8"}})

    client = OllamaLLMClient(settings(), httpx.MockTransport(handler))
    messages = [LLMMessage(role="user", content="best")]
    tools = [ToolDefinition("find_best_runs", "Find", {"type": "object"})]
    first = await client.complete("system", messages, tools)
    assert first.tool_calls[0].id
    messages += [
        LLMMessage(role="assistant", tool_calls=first.tool_calls),
        LLMMessage(
            role="tool",
            tool_call_id=first.tool_calls[0].id,
            tool_name="find_best_runs",
            content='{"accuracy":0.8}',
        ),
    ]
    assert (await client.complete("system", messages, tools)).text == "Run A: 0.8"


async def test_stream_ignores_thinking_and_completes():
    lines = [
        {"message": {"thinking": "private", "content": "Hello "}, "done": False},
        {"message": {"content": "world"}, "done": True},
    ]
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, text="\n".join(json.dumps(line) for line in lines))
    )
    client = OllamaLLMClient(settings(), transport)
    parts = [part async for part in client.stream("s", [], [])]
    assert isinstance(parts[-1], LLMReply)
    assert parts[-1].text == "Hello world"
    assert "".join(part for part in parts if isinstance(part, str)) == "Hello world"


async def test_embedded_reasoning_redacted_before_display():
    client = OllamaLLMClient(
        settings(),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"done": True, "message": {"content": "<think>private</think>Xin chào"}}
            )
        ),
    )
    assert (await client.complete("s", [], [])).text == "Xin chào"


async def test_prefilled_reasoning_open_marker_is_not_exposed():
    client = OllamaLLMClient(
        settings(),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200, json={"done": True, "message": {"content": "private</think>Xin chào"}}
            )
        ),
    )
    assert (await client.complete("s", [], [])).text == "Xin chào"


def test_leftover_key_does_not_select_cloud(monkeypatch):
    from app.services.copilot import llm_client
    from app.services.copilot.llm_client import FakeLLMClient, get_llm_client

    monkeypatch.setattr(
        llm_client, "get_settings", lambda: Settings(_env_file=None, llm_api_key="old")
    )
    get_llm_client.cache_clear()
    try:
        assert isinstance(get_llm_client(), FakeLLMClient)
    finally:
        get_llm_client.cache_clear()


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"done": True, "message": {}},
        {"done": True, "message": {"tool_calls": [{"function": {"name": "x", "arguments": "[]"}}]}},
        {"done": True, "message": {"content": "<think>private"}},
    ],
)
async def test_bad_responses_are_bounded_errors(body):
    client = OllamaLLMClient(
        settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    )
    with pytest.raises(LLMError):
        await client.complete("s", [], [])


async def test_timeout_no_fallback():
    def timeout(_):
        raise httpx.ReadTimeout("timeout")

    with pytest.raises(LLMError):
        await OllamaLLMClient(settings(), httpx.MockTransport(timeout)).complete("s", [], [])


async def test_context_not_silently_truncated():
    client = OllamaLLMClient(settings(llm_context=2048))
    with pytest.raises(LLMError, match="context"):
        await client.complete("x" * 3000, [], [])


async def test_truncated_output_is_reported_as_error():
    client = OllamaLLMClient(
        settings(),
        httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={"done": True, "done_reason": "length", "message": {"content": "partial 0."}},
            )
        ),
    )
    with pytest.raises(LLMError, match="budget"):
        await client.complete("s", [], [])


async def test_duplicate_provider_call_ids_normalized():
    body = {
        "done": True,
        "message": {
            "tool_calls": [
                {"id": "same", "function": {"name": "get_run", "arguments": {"run_id": 1}}},
                {"id": "same", "function": {"name": "get_run", "arguments": {"run_id": 2}}},
            ]
        },
    }
    client = OllamaLLMClient(
        settings(), httpx.MockTransport(lambda _: httpx.Response(200, json=body))
    )
    reply = await client.complete("s", [], [])
    assert len({call.id for call in reply.tool_calls}) == 2
