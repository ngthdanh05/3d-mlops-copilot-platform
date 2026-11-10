from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.routers.deps import DbSession
from app.schemas.copilot import ChatRequest, ChatResponse
from app.services.copilot import engine
from app.services.copilot.llm_client import LLMClient, get_llm_client

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


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
