from fastapi import APIRouter, status

from app.routers.deps import DbSession, error_responses
from app.schemas import MetricCreate, MetricRead
from app.services import tracking

router = APIRouter(prefix="/api/runs/{run_id}/metrics", tags=["metrics"])


@router.post(
    "",
    response_model=MetricRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409),
    summary="Log metrics for one epoch of a run",
)
async def log_metric(run_id: int, data: MetricCreate, db: DbSession):
    return await tracking.log_metric(db, run_id, data)
