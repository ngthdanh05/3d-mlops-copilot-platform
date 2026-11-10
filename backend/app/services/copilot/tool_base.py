"""Shared types for copilot tools."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.base import InputSchema
from app.schemas.copilot import (
    Action,
    FocusCameraAction,
    HighlightRunsAction,
    OpenInspectorAction,
)


class RunIdArgs(InputSchema):
    run_id: int = Field(ge=1)


@dataclass
class ToolContext:
    """State of one chat request, shared by the tools it calls."""

    db: AsyncSession
    experiment_id: int | None
    actions: list[Action] = field(default_factory=list)
    chart_actions: list[Action] = field(default_factory=list)

    def show_runs(self, run_ids: list[int], main_run_id: int) -> None:
        """Mark the runs an answer is about, without spending an LLM round on it.

        The latest answering tool wins: a model that looks up the best run and then compares
        it with another is answering about the comparison.
        """
        self.chart_actions = [
            HighlightRunsAction(run_ids=run_ids),
            FocusCameraAction(run_id=main_run_id),
            OpenInspectorAction(run_id=main_run_id),
        ]

    @property
    def final_actions(self) -> list[Action]:
        """What the frontend should do. Anything the model asked for explicitly comes first."""
        return self.actions or self.chart_actions


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[ToolContext, Any], Awaitable[dict[str, Any]]]
