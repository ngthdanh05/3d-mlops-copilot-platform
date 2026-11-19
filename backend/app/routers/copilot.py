from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.routers.deps import DbSession
from app.schemas.copilot import ChatRequest, ChatResponse
from app.services.copilot import engine
from app.services.copilot.llm_client import LLMClient, get_llm_client

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


@router.get("/status")
async def provider_status() -> dict[str, str | bool | None]:
    settings = get_settings()
    available = settings.llm_provider == "fake"
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=3, trust_env=False) as client:
                response = await client.get(settings.llm_base_url.rstrip("/") + "/api/tags")
                response.raise_for_status()
                available = any(
                    m.get("name") == settings.llm_model for m in response.json().get("models", [])
                )
        except (httpx.HTTPError, ValueError, TypeError):
            available = False
    return {
        "provider": settings.llm_provider,
        "model": settings.llm_model if settings.llm_provider != "fake" else None,
        "available": available,
        "offline": settings.offline,
    }


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Ask the copilot; returns an answer and UI actions",
)
async def chat(
    data: ChatRequest,
    db: DbSession,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
):
    return await engine.answer(db, llm, data)


async def _server_sent_events(events: AsyncIterator[engine.ChatEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield f"data: {event.model_dump_json()}\n\n"


@router.post(
    "/chat/stream",
    response_class=StreamingResponse,
    summary="Ask the copilot; streams the answer as server-sent events",
)
async def chat_stream(
    data: ChatRequest,
    db: DbSession,
    llm: Annotated[LLMClient, Depends(get_llm_client)],
):
    return StreamingResponse(
        _server_sent_events(engine.answer_events(db, llm, data)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
