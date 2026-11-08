from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.base import InputSchema


class ChatRequest(InputSchema):
    """`POST /api/copilot/chat`."""

    message: str = Field(min_length=1, max_length=4000, examples=["Run nào tốt nhất?"])
    experiment_id: int | None = Field(default=None, ge=1)


class HighlightRunsAction(BaseModel):
    type: Literal["highlight_runs"] = "highlight_runs"
    run_ids: list[int]


class FocusCameraAction(BaseModel):
    type: Literal["focus_camera"] = "focus_camera"
    run_id: int


class OpenInspectorAction(BaseModel):
    type: Literal["open_inspector"] = "open_inspector"
    run_id: int


Action = Annotated[
    HighlightRunsAction | FocusCameraAction | OpenInspectorAction,
    Field(discriminator="type"),
]


class ChatResponse(BaseModel):
    message: str
    actions: list[Action] = Field(default_factory=list)
