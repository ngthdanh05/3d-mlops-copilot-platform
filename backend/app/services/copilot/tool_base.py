"""Shared types for copilot tools."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.copilot import Action


@dataclass
class ToolContext:
    """State of one chat request, shared by the tools it calls."""

    db: AsyncSession
    experiment_id: int | None
    actions: list[Action] = field(default_factory=list)


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: Callable[[ToolContext, Any], Awaitable[dict[str, Any]]]
