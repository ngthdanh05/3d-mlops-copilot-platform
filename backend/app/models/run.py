from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.experiment import Experiment
    from app.models.metric import Metric


class RunStatus(enum.StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(Base):
    __tablename__ = "runs"
    __table_args__ = (UniqueConstraint("experiment_id", "run_name", name="uq_run_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    run_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[RunStatus] = mapped_column(
        Enum(
            RunStatus,
            name="run_status",
            native_enum=False,
            validate_strings=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=RunStatus.RUNNING,
        index=True,
    )
    hyperparams: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    experiment: Mapped[Experiment] = relationship(back_populates="runs")
    metrics: Mapped[list[Metric]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Metric.epoch",
    )

    def __repr__(self) -> str:
        return f"<Run id={self.id} name={self.run_name!r} status={self.status.value}>"
