"""The tool-calling loop behind `POST /api/copilot/chat` and its streaming variant."""

import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.copilot import (
    ChatRequest,
    ChatResponse,
    DoneEvent,
    TextDeltaEvent,
    TextResetEvent,
)
from app.services import tracking
from app.services.copilot.llm_client import (
    LLMClient,
    LLMError,
    LLMMessage,
    LLMRateLimitError,
    LLMReply,
    ToolCall,
    ToolDefinition,
)
from app.services.copilot.prompts import SYSTEM_PROMPT
from app.services.copilot.query_tools import QUERY_TOOLS
from app.services.copilot.tool_base import ToolContext
from app.services.copilot.ui_tools import UI_TOOLS
from app.services.errors import ServiceError

logger = logging.getLogger(__name__)

# Longest legitimate chat, if the model makes one call per round: name lookup, two queries,
# three UI tools on request, an empty reply that gets nudged, and the answer.
MAX_TOOL_ROUNDS = 8

_TOOLS = {tool.name: tool for tool in [*QUERY_TOOLS, *UI_TOOLS]}
_TOOL_DEFINITIONS = [
    ToolDefinition(tool.name, tool.description, tool.args_model.model_json_schema())
    for tool in _TOOLS.values()
]

_LLM_ERROR_MESSAGE = "Trợ lý AI đang gặp sự cố. Bạn hãy thử lại sau ít phút."
_ANSWER_NOW_PROMPT = "Now write your final answer to my question, following your rules."
_RATE_LIMIT_MESSAGE = "Đã chạm giới hạn lượt gọi miễn phí của Gemini. Bạn hãy thử lại sau một phút."
_EMPTY_REPLY_MESSAGE = "Trợ lý AI không đưa ra được câu trả lời. Bạn hãy thử hỏi lại."
_TOO_MANY_ROUNDS_MESSAGE = "Câu hỏi này cần quá nhiều bước tra cứu. Bạn hãy hỏi cụ thể hơn."

_WORD = re.compile(r"[\w.-]+")


async def _named_runs_note(db: AsyncSession, request: ChatRequest) -> LLMMessage | None:
    """The run_id of runs the question names, which saves the model a lookup round."""
    words = [word.strip(".-") for word in _WORD.findall(request.message)]
    try:
        runs = await tracking.find_runs_by_name(db, words, experiment_id=request.experiment_id)
    except ServiceError:  # the model reports an unknown experiment when it uses a tool
        return None
    if not runs:
        return None
    listed = ", ".join(
        f"{run.run_name} is run_id {run.id} in experiment {run.experiment_id}" for run in runs
    )
    return LLMMessage(role="user", content=f"Note: {listed}.")


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


ChatEvent = TextDeltaEvent | TextResetEvent | DoneEvent


async def answer_events(
    db: AsyncSession, llm: LLMClient, request: ChatRequest, *, stream_text: bool = True
) -> AsyncIterator[ChatEvent]:
    """Run the loop, yielding answer text as it arrives. Always ends with one `DoneEvent`."""
    context = ToolContext(db=db, experiment_id=request.experiment_id)
    messages = [LLMMessage(role="user", content=request.message)]
    if note := await _named_runs_note(db, request):
        messages.append(note)
    nudged = False

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            reply = LLMReply()
            if stream_text:
                async for item in llm.stream(SYSTEM_PROMPT, messages, _TOOL_DEFINITIONS):
                    if isinstance(item, LLMReply):
                        reply = item
                    else:
                        yield TextDeltaEvent(text=item)
            else:
                reply = await llm.complete(SYSTEM_PROMPT, messages, _TOOL_DEFINITIONS)

            if not reply.tool_calls:
                if reply.text or nudged:
                    yield DoneEvent(
                        message=reply.text or _EMPTY_REPLY_MESSAGE, actions=context.final_actions
                    )
                    return
                # Models sometimes stop silently after their last tool call.
                nudged = True
                messages.append(LLMMessage(role="user", content=_ANSWER_NOW_PROMPT))
                continue

            # Text written alongside tool calls is thinking aloud, not the answer.
            if reply.text:
                yield TextResetEvent()
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=reply.text,
                    tool_calls=reply.tool_calls,
                    provider_content=reply.provider_content,
                )
            )
            for call in reply.tool_calls:
                result = await _run_tool(call, context)
                messages.append(
                    LLMMessage(
                        role="tool",
                        tool_call_id=call.id,
                        tool_name=call.name,
                        content=json.dumps(result, ensure_ascii=False),
                    )
                )
    except LLMRateLimitError:
        logger.warning("LLM quota exceeded")
        yield DoneEvent(message=_RATE_LIMIT_MESSAGE, actions=context.final_actions)
        return
    except LLMError:
        logger.exception("LLM call failed")
        yield DoneEvent(message=_LLM_ERROR_MESSAGE)
        return

    yield DoneEvent(message=_TOO_MANY_ROUNDS_MESSAGE, actions=context.final_actions)


async def answer(db: AsyncSession, llm: LLMClient, request: ChatRequest) -> ChatResponse:
    async for event in answer_events(db, llm, request, stream_text=False):
        if isinstance(event, DoneEvent):
            return ChatResponse(message=event.message, actions=event.actions)
    raise RuntimeError("The copilot loop ended without an answer")
