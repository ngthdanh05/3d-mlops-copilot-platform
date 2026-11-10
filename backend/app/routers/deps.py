from typing import Annotated, Any

from fastapi import Depends, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.base import SQLITE_INT_MAX

DbSession = Annotated[AsyncSession, Depends(get_db)]
PathId = Annotated[int, Path(ge=1, le=SQLITE_INT_MAX)]


class ErrorResponse(BaseModel):
    detail: str


def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI docs for service errors (404 / 409) returned by an endpoint."""
    return {code: {"model": ErrorResponse} for code in codes}
