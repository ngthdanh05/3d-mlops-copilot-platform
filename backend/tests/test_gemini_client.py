"""GeminiLLMClient through the real SDK, with only the HTTP layer faked."""

import json

import httpx
import pytest
from google import genai
from google.genai import types

from app.config import Settings
from app.main import app
from app.services.copilot import llm_client
from app.services.copilot.llm_client import (
    FakeLLMClient,
    GeminiLLMClient,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMReply,
    ToolDefinition,
    get_llm_client,
)

TOOLS = [
    ToolDefinition(
        name="find_best_runs",
        description="Rank runs",
        parameters={"type": "object", "properties": {"metric": {"type": "string"}}},
    )
]


def gemini_reply(*parts: dict) -> dict:
    return {"candidates": [{"content": {"role": "model", "parts": list(parts)}}]}


class FakeGeminiServer:
    def __init__(self, *responses: httpx.Response) -> None:
        self.responses = list(responses)
        self.requests: list[dict] = []
        self.urls: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        self.urls.append(str(request.url))
        return self.responses.pop(0)

    def client(self, model: str = "test-model") -> GeminiLLMClient:
        http = httpx.AsyncClient(transport=httpx.MockTransport(self))
        sdk = genai.Client(api_key="k", http_options=types.HttpOptions(httpx_async_client=http))
        return GeminiLLMClient(sdk, model)


def ok(*parts: dict) -> httpx.Response:
    return httpx.Response(200, json=gemini_reply(*parts))


USER = LLMMessage(role="user", content="Run nào tốt nhất?")


async def test_request_carries_model_system_tools_and_question():
    server = FakeGeminiServer(ok({"text": "hello"}))

    reply = await server.client("my-model").complete("be brief", [USER], TOOLS)

    assert reply.text == "hello" and reply.tool_calls == []
    assert "models/my-model:generateContent" in server.urls[0]
    body = server.requests[0]
    assert body["systemInstruction"]["parts"][0]["text"] == "be brief"
    assert body["contents"] == [{"role": "user", "parts": [{"text": "Run nào tốt nhất?"}]}]
    declaration = body["tools"][0]["functionDeclarations"][0]
    assert declaration["name"] == "find_best_runs"
    assert declaration["parameters_json_schema"] == TOOLS[0].parameters


async def test_tool_round_trip_keeps_signature_and_matches_results():
    server = FakeGeminiServer(
        ok(
            {
                "functionCall": {"id": "c1", "name": "highlight_runs", "args": {"run_ids": [7]}},
                "thoughtSignature": "c2ln",
            },
            {"functionCall": {"id": "c2", "name": "focus_camera", "args": {"run_id": 7}}},
        ),
        ok({"text": "done"}),
    )
    client = server.client()

    first = await client.complete("s", [USER], TOOLS)

    assert [(c.id, c.name, c.arguments) for c in first.tool_calls] == [
        ("c1", "highlight_runs", {"run_ids": [7]}),
        ("c2", "focus_camera", {"run_id": 7}),
    ]

    await client.complete(
        "s",
        [
            USER,
            LLMMessage(
                role="assistant",
                tool_calls=first.tool_calls,
                provider_content=first.provider_content,
            ),
            LLMMessage(role="tool", tool_call_id="c1", tool_name="highlight_runs", content="{}"),
            LLMMessage(
                role="tool", tool_call_id="c2", tool_name="focus_camera", content='{"focused": 7}'
            ),
        ],
        TOOLS,
    )

    model_turn, tool_turn = server.requests[1]["contents"][1:]
    assert model_turn["role"] == "model"
    assert model_turn["parts"][0]["thoughtSignature"] == "c2ln"
    assert tool_turn["role"] == "user"  # the live API rejects role="tool"
    assert [p["functionResponse"] for p in tool_turn["parts"]] == [
        {"id": "c1", "name": "highlight_runs", "response": {}},
        {"id": "c2", "name": "focus_camera", "response": {"focused": 7}},
    ]


async def test_thought_text_is_not_shown_to_the_user():
    server = FakeGeminiServer(ok({"text": "secret plan", "thought": True}, {"text": "answer"}))
    reply = await server.client().complete("s", [USER], TOOLS)
    assert reply.text == "answer"


async def test_blocked_response_has_no_text_or_calls():
    server = FakeGeminiServer(httpx.Response(200, json={"candidates": []}))
    reply = await server.client().complete("s", [USER], TOOLS)
    assert reply.text is None and reply.tool_calls == []


def sse(*chunks: dict) -> httpx.Response:
    body = "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks)
    return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=body)


async def collect(stream) -> tuple[list[str], LLMReply]:
    items = [item async for item in stream]
    return items[:-1], items[-1]


async def test_stream_yields_text_pieces_and_hides_thoughts():
    server = FakeGeminiServer(
        sse(
            gemini_reply({"text": "plan", "thought": True}),
            gemini_reply({"text": "Xin "}),
            gemini_reply({"text": "chào"}),
        )
    )

    pieces, reply = await collect(server.client("my-model").stream("s", [USER], TOOLS))

    assert pieces == ["Xin ", "chào"]
    assert reply.text == "Xin chào" and reply.tool_calls == []
    assert "models/my-model:streamGenerateContent" in server.urls[0]


async def test_stream_keeps_tool_calls_and_signature_for_the_next_turn():
    server = FakeGeminiServer(
        sse(
            gemini_reply(
                {
                    "functionCall": {"id": "c1", "name": "find_best_runs", "args": {}},
                    "thoughtSignature": "c2ln",
                }
            )
        ),
    )

    pieces, reply = await collect(server.client().stream("s", [USER], TOOLS))

    assert pieces == []
    assert [(c.id, c.name) for c in reply.tool_calls] == [("c1", "find_best_runs")]
    assert reply.provider_content.parts[0].thought_signature == b"sig"


async def test_stream_quota_error_is_distinguished():
    server = FakeGeminiServer(
        *[httpx.Response(429, json={"error": {"code": 429, "message": "x"}}) for _ in range(10)]
    )
    with pytest.raises(LLMRateLimitError):
        await collect(server.client().stream("s", [USER], TOOLS))


@pytest.mark.parametrize("status", [400, 429, 500])
async def test_api_errors_become_llm_error(status):
    server = FakeGeminiServer(
        *[
            httpx.Response(status, json={"error": {"code": status, "message": "nope"}})
            for _ in range(10)
        ]
    )
    with pytest.raises(LLMError):
        await server.client().complete("s", [USER], TOOLS)


async def test_quota_error_is_distinguished():
    server = FakeGeminiServer(
        *[httpx.Response(429, json={"error": {"code": 429, "message": "x"}}) for _ in range(10)]
    )
    with pytest.raises(LLMRateLimitError):
        await server.client().complete("s", [USER], TOOLS)


async def test_quota_error_tells_the_user_to_wait(client):
    server = FakeGeminiServer(
        *[httpx.Response(429, json={"error": {"code": 429, "message": "x"}}) for _ in range(10)]
    )
    gemini = server.client()
    app.dependency_overrides[get_llm_client] = lambda: gemini

    response = await client.post("/api/copilot/chat", json={"message": "q"})

    assert response.status_code == 200
    assert "giới hạn" in response.json()["message"]


async def test_full_chat_through_gemini_client(client):
    experiment = (await client.post("/api/experiments", json={"name": "e"})).json()["id"]
    run = (
        await client.post("/api/runs", json={"experiment_id": experiment, "run_name": "r"})
    ).json()["id"]
    await client.post(f"/api/runs/{run}/metrics", json={"epoch": 1, "accuracy": 0.9, "loss": 0.1})
    await client.put(f"/api/runs/{run}", json={"status": "completed"})

    server = FakeGeminiServer(
        ok({"functionCall": {"id": "1", "name": "find_best_runs", "args": {"metric": "accuracy"}}}),
        ok({"functionCall": {"id": "2", "name": "focus_camera", "args": {"run_id": run}}}),
        ok({"text": "r có accuracy 0.9"}),
    )
    gemini = server.client()
    app.dependency_overrides[get_llm_client] = lambda: gemini

    response = await client.post("/api/copilot/chat", json={"message": "best"})

    assert response.json() == {
        "message": "r có accuracy 0.9",
        "actions": [{"type": "focus_camera", "run_id": run}],
    }
    tool_result = server.requests[1]["contents"][-1]["parts"][0]["functionResponse"]
    assert tool_result["response"]["runs"][0]["value"] == 0.9


@pytest.fixture
def fresh_client_cache():
    get_llm_client.cache_clear()
    yield
    get_llm_client.cache_clear()


def use_settings(monkeypatch, **values) -> None:
    # _env_file is a pydantic-settings init option that static checkers cannot see.
    settings = Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]
    monkeypatch.setattr(llm_client, "get_settings", lambda: settings)


def test_no_key_uses_the_stand_in(monkeypatch, fresh_client_cache):
    use_settings(monkeypatch, llm_api_key="")
    assert isinstance(get_llm_client(), FakeLLMClient)


def test_key_selects_gemini_with_default_model(monkeypatch, fresh_client_cache):
    use_settings(monkeypatch, llm_api_key="k", llm_model="")
    selected = get_llm_client()
    assert isinstance(selected, GeminiLLMClient)
    assert selected._model == llm_client.DEFAULT_GEMINI_MODEL


def test_configured_model_is_used(monkeypatch, fresh_client_cache):
    use_settings(monkeypatch, llm_api_key="k", llm_model="other")
    selected = get_llm_client()
    assert isinstance(selected, GeminiLLMClient)
    assert selected._model == "other"
