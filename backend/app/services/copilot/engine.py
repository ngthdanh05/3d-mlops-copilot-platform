"""The tool-calling loop behind `POST /api/copilot/chat`."""

import json
import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.copilot import ChatRequest, ChatResponse
from app.services.copilot.llm_client import (
    LLMClient,
    LLMError,
    LLMMessage,
    ToolCall,
    ToolDefinition,
)
from app.services.copilot.prompts import SYSTEM_PROMPT
from app.services.copilot.query_tools import QUERY_TOOLS
from app.services.copilot.tool_base import ToolContext
from app.services.copilot.ui_tools import UI_TOOLS
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 5

_TOOLS = {tool.name: tool for tool in [*QUERY_TOOLS, *UI_TOOLS]}
_TOOL_DEFINITIONS = [
    ToolDefinition(tool.name, tool.description, tool.args_model.model_json_schema())
    for tool in _TOOLS.values()
]

_LLM_ERROR_MESSAGE = "Trợ lý AI đang gặp sự cố. Bạn hãy thử lại sau ít phút."
_EMPTY_REPLY_MESSAGE = "Trợ lý AI không đưa ra được câu trả lời. Bạn hãy thử hỏi lại."
_TOO_MANY_ROUNDS_MESSAGE = "Câu hỏi này cần quá nhiều bước tra cứu. Bạn hãy hỏi cụ thể hơn."


async def _run_tool(call: ToolCall, context: ToolContext) -> dict[str, Any]:
    """Run one tool call. Failures become a result the model can read and correct."""
    tool = _TOOLS.get(call.name)
    if tool is None:
        return {"error": f"Unknown tool '{call.name}'"}
    try:
        args = tool.args_model.model_validate(call.arguments)
    except ValidationError as exc:
        problems = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
        return {"error": f"Invalid arguments: {'; '.join(problems)}"}
    try:
        return await tool.handler(context, args)
    except ServiceError as exc:
        return {"error": exc.detail}


async def answer(db: AsyncSession, llm: LLMClient, request: ChatRequest) -> ChatResponse:
    context = ToolContext(db=db, experiment_id=request.experiment_id)
    messages = [LLMMessage(role="user", content=request.message)]

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            reply = await llm.complete(SYSTEM_PROMPT, messages, _TOOL_DEFINITIONS)
            if not reply.tool_calls:
                return ChatResponse(
                    message=reply.text or _EMPTY_REPLY_MESSAGE, actions=context.actions
                )

            messages.append(
                LLMMessage(role="assistant", content=reply.text, tool_calls=reply.tool_calls)
            )
            for call in reply.tool_calls:
                result = await _run_tool(call, context)
                messages.append(
                    LLMMessage(
                        role="tool",
                        tool_call_id=call.id,
                        content=json.dumps(result, ensure_ascii=False),
                    )
                )
    except LLMError:
        logger.exception("LLM call failed")
        return ChatResponse(message=_LLM_ERROR_MESSAGE)

    return ChatResponse(message=_TOO_MANY_ROUNDS_MESSAGE, actions=context.actions)
