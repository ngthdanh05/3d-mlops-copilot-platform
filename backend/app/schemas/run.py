from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import AfterValidator, Field, JsonValue, model_validator

from app.models.run import RunStatus
from app.schemas.base import DatabaseId, InputSchema, ORMSchema, UTCDateTime
from app.schemas.metric import MetricRead

if TYPE_CHECKING:
    from app.models.run import Run

# Well-known hyperparameter keys and the numeric constraint each must satisfy.
_POSITIVE_KEYS = ("learning_rate", "lr")
_POSITIVE_INT_KEYS = ("epochs", "batch_size")


def _validate_hyperparams(params: dict[str, JsonValue]) -> dict[str, JsonValue]:
    errors: list[str] = []
    for key, value in params.items():
        if not key.strip():
            errors.append("hyperparameter names must be non-empty")
            continue
        if key in _POSITIVE_KEYS:
            # bool is a subclass of int: reject it explicitly.
            if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
                errors.append(f"'{key}' must be a number > 0")
        elif key in _POSITIVE_INT_KEYS:
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                errors.append(f"'{key}' must be an integer >= 1")
    if errors:
        raise ValueError("; ".join(errors))
    return params


Hyperparams = Annotated[dict[str, JsonValue], AfterValidator(_validate_hyperparams)]
"""Free-form JSON hyperparameters; `learning_rate`/`lr` > 0, `epochs`/`batch_size` >= 1."""


class RunCreate(InputSchema):
    """`POST /api/runs`."""

    experiment_id: DatabaseId
    run_name: str = Field(min_length=1, max_length=255, examples=["run-001"])
    hyperparams: Hyperparams = Field(
        default_factory=dict,
        examples=[{"learning_rate": 0.001, "batch_size": 32, "epochs": 10}],
    )


class RunUpdate(InputSchema):
    """`PUT /api/runs/{id}` — mark a run completed / failed."""

    status: RunStatus | None = None
    finished_at: UTCDateTime | None = None

    @model_validator(mode="after")
    def _check(self) -> RunUpdate:
        if self.status is None and self.finished_at is None:
            raise ValueError("at least one of 'status' or 'finished_at' must be provided")
        if self.status is RunStatus.RUNNING and self.finished_at is not None:
            raise ValueError("'finished_at' cannot be set while status is 'running'")
        return self


class RunRead(ORMSchema):
    id: int
    experiment_id: int
    run_name: str
    status: RunStatus
    hyperparams: dict[str, JsonValue]
    created_at: UTCDateTime
    finished_at: UTCDateTime | None


class RunSummary(RunRead):
    """List item for `GET /api/runs`: run + metrics of its last logged epoch."""

    final_epoch: int | None = None
    final_accuracy: float | None = None
    final_loss: float | None = None
    final_val_accuracy: float | None = None
    final_val_loss: float | None = None

    @classmethod
    def from_run(cls, run: Run) -> RunSummary:
        """Build from an ORM `Run` whose `metrics` relationship is loaded."""
        summary = cls.model_validate(run)
        if run.metrics:
            last = max(run.metrics, key=lambda m: m.epoch)
            summary.final_epoch = last.epoch
            summary.final_accuracy = last.accuracy
            summary.final_loss = last.loss
            summary.final_val_accuracy = last.val_accuracy
            summary.final_val_loss = last.val_loss
        return summary


class RunDetail(RunRead):
    """`GET /api/runs/{id}`: run + full per-epoch metrics timeline."""

    metrics: list[MetricRead] = Field(default_factory=list)
