"""Tools that read experiment data. They go through the service layer, never the DB."""

from collections.abc import Sequence
from statistics import fmean, median
from typing import Any, get_args

from pydantic import Field, field_validator

from app.models import Metric, Run, RunStatus
from app.schemas import RankingMetric, RunSummary
from app.schemas.base import InputSchema
from app.services import tracking
from app.services.copilot.tool_base import RunIdArgs, Tool, ToolContext

# Overfitting thresholds. Accuracy gaps are train minus validation.
_MIN_EPOCHS = 4  # fewer than this cannot show a trend
_SMOOTHING_EPOCHS = 3  # epochs averaged at each end, so one noisy epoch cannot decide
_CLEAR_GAP = 0.05
_MILD_GAP = 0.02
_GAP_WIDENING = 0.02
_CLEAR_VAL_LOSS_RISE = 0.20  # relative to the lowest validation loss
_MILD_VAL_LOSS_RISE = 0.10


class NoArgs(InputSchema):
    pass


class FindBestRunsArgs(InputSchema):
    metric: RankingMetric = Field(default="val_accuracy", description="Metric to rank by")
    top_k: int = Field(default=1, ge=1, le=10, description="How many runs to return")
    experiment_id: int | None = Field(
        default=None, ge=1, description="Defaults to the experiment the user is viewing"
    )


class FindRunsByNameArgs(InputSchema):
    run_names: list[str] = Field(
        min_length=1, max_length=10, description="Run names as the user wrote them"
    )
    experiment_id: int | None = Field(
        default=None, ge=1, description="Defaults to the experiment the user is viewing"
    )


class CompareRunsArgs(InputSchema):
    run_ids: list[int] = Field(min_length=2, max_length=10, description="Runs to compare")

    @field_validator("run_ids")
    @classmethod
    def _distinct(cls, run_ids: list[int]) -> list[int]:
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("run_ids must be distinct")
        return run_ids


async def _list_experiments(context: ToolContext, _: NoArgs) -> dict[str, Any]:
    experiments = await tracking.list_experiments(context.db)
    return {
        "experiments": [
            {"experiment_id": e.id, "name": e.name, "description": e.description}
            for e in experiments
        ]
    }


async def _find_best_runs(context: ToolContext, args: FindBestRunsArgs) -> dict[str, Any]:
    ranked = await tracking.find_best_runs(
        context.db,
        args.metric,
        experiment_id=args.experiment_id or context.experiment_id,
        top_k=None,
    )
    values = [value for _, value in ranked]
    return {
        "metric": args.metric,
        "completed_runs": len(ranked),
        "median_value": median(values) if values else None,
        "runs": [
            {
                "run_id": run.id,
                "run_name": run.run_name,
                "value": value,
                "hyperparams": run.hyperparams,
            }
            for run, value in ranked[: args.top_k]
        ],
    }


async def _find_runs_by_name(context: ToolContext, args: FindRunsByNameArgs) -> dict[str, Any]:
    runs = await tracking.find_runs_by_name(
        context.db,
        args.run_names,
        experiment_id=args.experiment_id or context.experiment_id,
    )
    found = {run.run_name.casefold() for run in runs}
    return {
        "runs": [{**_identify(run), "experiment_id": run.experiment_id} for run in runs],
        "not_found": [name for name in args.run_names if name.casefold() not in found],
    }


async def _get_run(context: ToolContext, args: RunIdArgs) -> dict[str, Any]:
    run = await tracking.get_run(context.db, args.run_id, with_metrics=True)
    return {
        **_identify(run),
        "experiment_id": run.experiment_id,
        "hyperparams": run.hyperparams,
        "epochs": [
            {
                "epoch": m.epoch,
                "accuracy": m.accuracy,
                "loss": m.loss,
                "val_accuracy": m.val_accuracy,
                "val_loss": m.val_loss,
            }
            for m in run.metrics
        ],
    }


async def _compare_runs(context: ToolContext, args: CompareRunsArgs) -> dict[str, Any]:
    runs = [
        await tracking.get_run(context.db, run_id, with_metrics=True) for run_id in args.run_ids
    ]
    summaries = [RunSummary.from_run(run) for run in runs]
    return {
        "runs": [
            {
                **_identify(run),
                "final_epoch": summary.final_epoch,
                **{f"final_{m}": getattr(summary, f"final_{m}") for m in get_args(RankingMetric)},
            }
            for run, summary in zip(runs, summaries, strict=True)
        ],
        **_split_hyperparams(runs),
        "best_by_metric": _best_by_metric(summaries),
    }


async def _detect_overfitting(context: ToolContext, args: RunIdArgs) -> dict[str, Any]:
    run = await tracking.get_run(context.db, args.run_id, with_metrics=True)
    gap = _accuracy_gap(run.metrics)
    val_loss = _val_loss_trend(run.metrics)
    return {
        **_identify(run),
        "verdict": _overfitting_verdict(gap, val_loss),
        "epochs_logged": len(run.metrics),
        "accuracy_gap": gap,
        "val_loss_trend": val_loss,
    }


def _identify(run: Run) -> dict[str, Any]:
    return {"run_id": run.id, "run_name": run.run_name, "status": run.status.value}


def _split_hyperparams(runs: Sequence[Run]) -> dict[str, dict[str, Any]]:
    """Hyperparameters every run agrees on, and the per-run values of the others."""
    shared: dict[str, Any] = {}
    differing: dict[str, dict[str, Any]] = {}
    for key in sorted({key for run in runs for key in run.hyperparams}):
        values = {str(run.id): run.hyperparams.get(key) for run in runs}
        first = values[str(runs[0].id)]
        if all(value == first for value in values.values()):
            shared[key] = first
        else:
            differing[key] = values
    return {"hyperparams_shared": shared, "hyperparams_differing": differing}


def _best_by_metric(summaries: Sequence[RunSummary]) -> dict[str, dict[str, Any]]:
    """Best completed run per metric, as `find_best_runs` would rank them."""
    best: dict[str, dict[str, Any]] = {}
    for metric in get_args(RankingMetric):
        field = f"final_{metric}"
        candidates = [
            s
            for s in summaries
            if s.status is RunStatus.COMPLETED and getattr(s, field) is not None
        ]
        if not candidates:
            continue
        ordered = sorted(
            candidates,
            key=lambda s: getattr(s, field),
            reverse=metric not in tracking.LOWER_IS_BETTER,
        )
        winner_value, worst_value = getattr(ordered[0], field), getattr(ordered[-1], field)
        best[metric] = {
            "run_id": ordered[0].id,
            "run_name": ordered[0].run_name,
            "value": winner_value,
            "spread_to_worst": round(abs(winner_value - worst_value), 4),
        }
    return best


def _window(size: int) -> int:
    return min(_SMOOTHING_EPOCHS, size // 2)


def _accuracy_gap(metrics: Sequence[Metric]) -> dict[str, Any] | None:
    """Train-minus-validation accuracy per epoch, smoothed at the start and at the end."""
    gaps = [(m.epoch, m.accuracy - m.val_accuracy) for m in metrics if m.val_accuracy is not None]
    if len(gaps) < _MIN_EPOCHS:
        return None
    window = _window(len(gaps))
    start = fmean(gap for _, gap in gaps[:window])
    end = fmean(gap for _, gap in gaps[-window:])
    return {
        "start": round(start, 4),
        "end": round(end, 4),
        "change": round(end - start, 4),
        "by_epoch": [{"epoch": epoch, "gap": round(gap, 4)} for epoch, gap in gaps],
    }


def _val_loss_trend(metrics: Sequence[Metric]) -> dict[str, Any] | None:
    """How far validation loss has climbed back up from its lowest point."""
    points = [m for m in metrics if m.val_loss is not None]
    if len(points) < _MIN_EPOCHS:
        return None
    window = _window(len(points))
    lowest = min(points, key=lambda m: m.val_loss)
    final_val_loss = fmean(m.val_loss for m in points[-window:])
    final_train_loss = fmean(m.loss for m in points[-window:])
    return {
        "lowest": lowest.val_loss,
        "lowest_epoch": lowest.epoch,
        "final": round(final_val_loss, 4),
        "rise_ratio": (
            round(final_val_loss / lowest.val_loss - 1, 4) if lowest.val_loss > 0 else None
        ),
        "train_loss_at_lowest": lowest.loss,
        "train_loss_final": round(final_train_loss, 4),
    }


def _overfitting_verdict(gap: dict[str, Any] | None, val_loss: dict[str, Any] | None) -> str:
    if gap is None and val_loss is None:
        return "insufficient_data"

    gap_end = gap["end"] if gap else 0.0
    widened = gap is not None and gap["change"] >= _GAP_WIDENING

    # A rising val loss only means overfitting if the model still improves on the train set;
    # when both rise, training is diverging instead.
    rise = 0.0
    if val_loss and val_loss["train_loss_final"] < val_loss["train_loss_at_lowest"]:
        rise = val_loss["rise_ratio"] or 0.0

    if (gap_end >= _CLEAR_GAP and widened) or rise >= _CLEAR_VAL_LOSS_RISE:
        return "overfitting"
    if gap_end >= _CLEAR_GAP or (gap_end >= _MILD_GAP and widened) or rise >= _MILD_VAL_LOSS_RISE:
        return "possible_overfitting"
    return "no_overfitting"


QUERY_TOOLS = [
    Tool(
        name="list_experiments",
        description="List all experiments with their ids and names.",
        args_model=NoArgs,
        handler=_list_experiments,
    ),
    Tool(
        name="find_best_runs",
        description="Rank completed runs by a metric and return the best ones.",
        args_model=FindBestRunsArgs,
        handler=_find_best_runs,
    ),
    Tool(
        name="find_runs_by_name",
        description=(
            "Look up the run_id of runs the user refers to by name, such as run-002. "
            "Several results for one name mean it exists in several experiments."
        ),
        args_model=FindRunsByNameArgs,
        handler=_find_runs_by_name,
    ),
    Tool(
        name="get_run",
        description="Get one run: status, hyperparameters and metrics of every epoch.",
        args_model=RunIdArgs,
        handler=_get_run,
    ),
    Tool(
        name="compare_runs",
        description=(
            "Compare runs: final metrics, which hyperparameters differ, "
            "and the best completed run per metric."
        ),
        args_model=CompareRunsArgs,
        handler=_compare_runs,
    ),
    Tool(
        name="detect_overfitting",
        description=(
            "Diagnose overfitting of one run from its train/validation curves. Returns a "
            "verdict (overfitting, possible_overfitting, no_overfitting, insufficient_data) "
            "and the numbers behind it. Use this verdict instead of judging the curves yourself."
        ),
        args_model=RunIdArgs,
        handler=_detect_overfitting,
    ),
]
