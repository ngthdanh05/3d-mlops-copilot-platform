"""Portable artifact references: never expose absolute filesystem paths."""

from typing import Literal

from pydantic import Field

from app.schemas.base import InputSchema


class ArtifactMetadata(InputSchema):
    version: Literal[1] = 1
    best_epoch: int = Field(ge=1)
    best_val_accuracy: float = Field(ge=0, le=1, allow_inf_nan=False)
    criterion: Literal["val_accuracy:max;ties:earliest"] = "val_accuracy:max;ties:earliest"
    best_checkpoint: Literal["best.pt"] = "best.pt"
    last_checkpoint: Literal["last.pt"] = "last.pt"
    test_accuracy: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    test_loss: float | None = Field(default=None, ge=0, allow_inf_nan=False)
