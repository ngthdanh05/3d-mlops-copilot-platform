"""Tools that drive the frontend. They only record actions for the chat response."""

from typing import Any

from pydantic import Field

from app.schemas.base import InputSchema
from app.schemas.copilot import FocusCameraAction, HighlightRunsAction, OpenInspectorAction
from app.services import tracking
from app.services.copilot.tool_base import Tool, ToolContext
from app.services.errors import NotFoundError


class HighlightRunsArgs(InputSchema):
    run_ids: list[int] = Field(min_length=1, max_length=50, description="Runs to highlight")


class RunIdArgs(InputSchema):
    run_id: int = Field(ge=1)


async def _highlight_runs(context: ToolContext, args: HighlightRunsArgs) -> dict[str, Any]:
    found: list[int] = []
    missing: list[int] = []
    for run_id in args.run_ids:
        try:
            await tracking.get_run(context.db, run_id)
        except NotFoundError:
            missing.append(run_id)
        else:
            found.append(run_id)
    if found:
        context.actions.append(HighlightRunsAction(run_ids=found))
    return {"highlighted": found, "not_found": missing}


async def _focus_camera(context: ToolContext, args: RunIdArgs) -> dict[str, Any]:
    await tracking.get_run(context.db, args.run_id)
    context.actions.append(FocusCameraAction(run_id=args.run_id))
    return {"focused": args.run_id}


async def _open_inspector(context: ToolContext, args: RunIdArgs) -> dict[str, Any]:
    await tracking.get_run(context.db, args.run_id)
    context.actions.append(OpenInspectorAction(run_id=args.run_id))
    return {"opened": args.run_id}


UI_TOOLS = [
    Tool(
        name="highlight_runs",
        description="Highlight runs in the 3D workspace.",
        args_model=HighlightRunsArgs,
        handler=_highlight_runs,
    ),
    Tool(
        name="focus_camera",
        description="Fly the 3D camera to a run.",
        args_model=RunIdArgs,
        handler=_focus_camera,
    ),
    Tool(
        name="open_inspector",
        description="Open the detail panel for a run.",
        args_model=RunIdArgs,
        handler=_open_inspector,
    ),
]
