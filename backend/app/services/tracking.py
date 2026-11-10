"""ML tracking CRUD operations: experiments, runs and per-epoch metrics."""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from app.models import Experiment, Metric, Run, RunStatus
from app.schemas import ExperimentCreate, MetricCreate, RankingMetric, RunCreate, RunUpdate
from app.services.errors import ConflictError, NotFoundError

LOWER_IS_BETTER = {"loss", "val_loss"}

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


async def delete_experiment(db: AsyncSession, experiment_id: int) -> None:
    """Delete an experiment; the database cascades to its runs and their metrics."""
    await db.delete(await get_experiment(db, experiment_id))
    await db.commit()


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
    """Runs, oldest first. `metrics` holds only each run's last epoch, for final summaries."""
    later = aliased(Metric)
    last_epoch = select(func.max(later.epoch)).where(later.run_id == Metric.run_id)
    stmt = (
        select(Run)
        .options(selectinload(Run.metrics.and_(Metric.epoch == last_epoch.scalar_subquery())))
        .order_by(Run.id)
    )
    if experiment_id is not None:
        await get_experiment(db, experiment_id)
        stmt = stmt.where(Run.experiment_id == experiment_id)
    result = await db.scalars(stmt)
    return result.all()


async def get_run(db: AsyncSession, run_id: int, *, with_metrics: bool = False) -> Run:
    options = [selectinload(Run.metrics)] if with_metrics else []
    # Without populate_existing, a run already in the session comes back without its metrics.
    run = await db.get(Run, run_id, options=options, populate_existing=with_metrics)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    return run


async def find_runs_by_name(
    db: AsyncSession, names: Sequence[str], *, experiment_id: int | None = None
) -> list[Run]:
    """Runs whose name matches, ignoring case. Names are only unique within an experiment."""
    stmt = select(Run).order_by(Run.id)
    if experiment_id is not None:
        await get_experiment(db, experiment_id)
        stmt = stmt.where(Run.experiment_id == experiment_id)
    wanted = {name.casefold() for name in names}
    return [run for run in await db.scalars(stmt) if run.run_name.casefold() in wanted]


async def find_best_runs(
    db: AsyncSession,
    metric: RankingMetric,
    *,
    experiment_id: int | None = None,
    top_k: int | None = 1,
) -> list[tuple[Run, float]]:
    """Completed runs ranked by their last-epoch `metric`, best first, with the value.

    `top_k=None` returns every ranked run.

    Running and failed runs are skipped: their last epoch is not a final result.
    """
    ranked: list[tuple[Run, float]] = []
    for run in await list_runs(db, experiment_id):
        if run.status is not RunStatus.COMPLETED or not run.metrics:
            continue
        value = getattr(max(run.metrics, key=lambda m: m.epoch), metric)
        if value is not None:
            ranked.append((run, value))
    ranked.sort(key=lambda pair: pair[1], reverse=metric not in LOWER_IS_BETTER)
    return ranked[:top_k]


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


async def delete_run(db: AsyncSession, run_id: int) -> None:
    """Delete a run; the database cascades to its metrics."""
    await db.delete(await get_run(db, run_id))
    await db.commit()


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
