"""Shared Pydantic base classes and reusable field types."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _as_utc(value: datetime) -> datetime:
    """Treat naive datetimes as UTC (SQLite drops tzinfo) and normalize aware ones to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]
"""A datetime that is always timezone-aware UTC, serialized as ISO 8601."""

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
NonNegativeFloat = Annotated[float, Field(ge=0.0)]


class InputSchema(BaseModel):
    """Base for request bodies: strict about unknown fields, no NaN/inf, trims strings."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class ORMSchema(BaseModel):
    """Base for response bodies built from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)
