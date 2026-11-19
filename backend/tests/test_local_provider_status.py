import httpx

from app.config import Settings
from app.routers import copilot


async def test_fake_status_is_explicit_and_has_no_secret_fields(client, monkeypatch):
    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: Settings(_env_file=None, llm_provider="fake", llm_api_key="must-not-leak"),
    )
    response = await client.get("/api/copilot/status")
    assert response.json() == {
        "provider": "fake",
        "model": None,
        "available": True,
        "offline": True,
    }


async def test_local_status_checks_cached_model_without_generating_text(client, monkeypatch):
    monkeypatch.setattr(
        copilot,
        "get_settings",
        lambda: Settings(_env_file=None, llm_provider="ollama", llm_model="qwen3:4b"),
    )
    original_client = httpx.AsyncClient
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"models": [{"name": "qwen3:4b"}]})

    monkeypatch.setattr(
        copilot.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(**kwargs, transport=httpx.MockTransport(handler)),
    )
    response = await client.get("/api/copilot/status")
    assert response.json()["available"] is True
    assert len(requests) == 1 and requests[0].url.path == "/api/tags"
