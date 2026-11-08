"""Tools that read experiment data. They go through the service layer, never the DB."""

from statistics import median
from typing import Any

from pydantic import Field

from app.schemas import RankingMetric
from app.schemas.base import InputSchema
from app.services import tracking
from app.services.copilot.tool_base import Tool, ToolContext


class FindBestRunsArgs(InputSchema):
    metric: RankingMetric = Field(default="val_accuracy", description="Metric to rank by")
    top_k: int = Field(default=1, ge=1, le=10, description="How many runs to return")
    experiment_id: int | None = Field(
        default=None, ge=1, description="Defaults to the experiment the user is viewing"
    )


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


QUERY_TOOLS = [
    Tool(
        name="find_best_runs",
        description="Rank completed runs by a metric and return the best ones.",
        args_model=FindBestRunsArgs,
        handler=_find_best_runs,
    ),
]
