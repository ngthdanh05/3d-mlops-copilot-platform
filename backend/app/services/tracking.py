"""ML tracking CRUD operations: experiments, runs and per-epoch metrics."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Experiment, Metric, Run, RunStatus
from app.schemas import ExperimentCreate, MetricCreate, RunCreate, RunUpdate
from app.services.errors import ConflictError, NotFoundError

# ── Experiments ───────────────────────────────────────────────────────────────


async def create_experiment(db: AsyncSession, data: ExperimentCreate) -> Experiment:
    experiment = Experiment(**data.model_dump())
    db.add(experiment)
    await _commit_or_conflict(db, f"Experiment '{data.name}' already exists")
    await db.refresh(experiment)
    return experiment


async def list_experiments(db: AsyncSession) -> Sequence[Experiment]:
    result = await db.scalars(select(Experiment).order_by(Experiment.id))
    return result.all()


async def get_experiment(db: AsyncSession, experiment_id: int) -> Experiment:
    experiment = await db.get(Experiment, experiment_id)
    if experiment is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")
    return experiment


# ── Runs ──────────────────────────────────────────────────────────────────────


async def create_run(db: AsyncSession, data: RunCreate) -> Run:
    await get_experiment(db, data.experiment_id)
    run = Run(**data.model_dump(), status=RunStatus.RUNNING)
    db.add(run)
    await _commit_or_conflict(
        db, f"Run '{data.run_name}' already exists in experiment {data.experiment_id}"
    )
    await db.refresh(run)
    return run


async def list_runs(db: AsyncSession, experiment_id: int | None = None) -> Sequence[Run]:
    """Runs (with metrics loaded, for final-metric summaries), oldest first."""
    stmt = select(Run).options(selectinload(Run.metrics)).order_by(Run.id)
    if experiment_id is not None:
        await get_experiment(db, experiment_id)
        stmt = stmt.where(Run.experiment_id == experiment_id)
    result = await db.scalars(stmt)
    return result.all()


async def get_run(db: AsyncSession, run_id: int, *, with_metrics: bool = False) -> Run:
    options = [selectinload(Run.metrics)] if with_metrics else []
    run = await db.get(Run, run_id, options=options)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    return run


async def update_run(db: AsyncSession, run_id: int, data: RunUpdate) -> Run:
    run = await get_run(db, run_id)

    if data.status is not None:
        run.status = data.status
        if data.status is RunStatus.RUNNING:
            run.finished_at = None  # re-opened run
        else:
            run.finished_at = data.finished_at or datetime.now(UTC)
    elif data.finished_at is not None:
        if run.status is RunStatus.RUNNING:
            raise ConflictError(f"Run {run_id} is still running; set 'status' to finish it")
        run.finished_at = data.finished_at

    await db.commit()
    await db.refresh(run)
    return run


# ── Metrics ───────────────────────────────────────────────────────────────────


async def log_metric(db: AsyncSession, run_id: int, data: MetricCreate) -> Metric:
    await get_run(db, run_id)
    metric = Metric(run_id=run_id, **data.model_dump())
    db.add(metric)
    await _commit_or_conflict(db, f"Epoch {data.epoch} already logged for run {run_id}")
    await db.refresh(metric)
    return metric


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _commit_or_conflict(db: AsyncSession, message: str) -> None:
    """Commit; translate unique-constraint violations into a 409 ConflictError."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        if "UNIQUE constraint failed" in str(exc.orig):
            raise ConflictError(message) from exc
        raise
