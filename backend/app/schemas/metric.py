from pydantic import Field

from app.schemas.base import InputSchema, NonNegativeFloat, ORMSchema, Probability, UTCDateTime


class MetricCreate(InputSchema):
    """Metrics logged for one epoch: `POST /api/runs/{id}/metrics`."""

    epoch: int = Field(ge=1, examples=[1])
    accuracy: Probability = Field(examples=[0.9567])
    loss: NonNegativeFloat = Field(examples=[0.145])
    val_accuracy: Probability | None = Field(default=None, examples=[0.9412])
    val_loss: NonNegativeFloat | None = Field(default=None, examples=[0.188])


class MetricRead(ORMSchema):
    id: int
    run_id: int
    epoch: int
    accuracy: float
    loss: float
    val_accuracy: float | None
    val_loss: float | None
    logged_at: UTCDateTime
