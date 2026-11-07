from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.run import Run


class Metric(Base):
    """Per-epoch training/validation metrics of a run."""

    __tablename__ = "metrics"
    __table_args__ = (
        UniqueConstraint("run_id", "epoch", name="uq_metric_run_epoch"),
        CheckConstraint("epoch >= 1", name="ck_metric_epoch_positive"),
        CheckConstraint("accuracy >= 0 AND accuracy <= 1", name="ck_metric_accuracy_range"),
        CheckConstraint("loss >= 0", name="ck_metric_loss_non_negative"),
        CheckConstraint(
            "val_accuracy IS NULL OR (val_accuracy >= 0 AND val_accuracy <= 1)",
            name="ck_metric_val_accuracy_range",
        ),
        CheckConstraint(
            "val_loss IS NULL OR val_loss >= 0", name="ck_metric_val_loss_non_negative"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    epoch: Mapped[int]
    accuracy: Mapped[float] = mapped_column(Float)
    loss: Mapped[float] = mapped_column(Float)
    val_accuracy: Mapped[float | None] = mapped_column(Float, default=None)
    val_loss: Mapped[float | None] = mapped_column(Float, default=None)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    run: Mapped[Run] = relationship(back_populates="metrics")

    def __repr__(self) -> str:
        return f"<Metric run_id={self.run_id} epoch={self.epoch} acc={self.accuracy}>"
