from typing import Annotated

from fastapi import APIRouter, Depends

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
