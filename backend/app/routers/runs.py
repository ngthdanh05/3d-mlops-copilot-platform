from typing import Annotated

from fastapi import APIRouter, Query, status

from app.routers.deps import DbSession, error_responses
from app.schemas import RunCreate, RunDetail, RunRead, RunSummary, RunUpdate
from app.services import tracking

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post(
    "",
    response_model=RunRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409),
    summary="Create a run (status starts as 'running')",
)
async def create_run(data: RunCreate, db: DbSession):
    return await tracking.create_run(db, data)


@router.get(
    "",
    response_model=list[RunSummary],
    responses=error_responses(404),
    summary="List runs with their final-epoch metrics",
)
async def list_runs(
    db: DbSession,
    experiment_id: Annotated[int | None, Query(ge=1, description="Filter by experiment")] = None,
):
    runs = await tracking.list_runs(db, experiment_id)
    return [RunSummary.from_run(run) for run in runs]


@router.get(
    "/{run_id}",
    response_model=RunDetail,
    responses=error_responses(404),
    summary="Get a run with its full metrics timeline",
)
async def get_run(run_id: int, db: DbSession):
    return await tracking.get_run(db, run_id, with_metrics=True)


@router.put(
    "/{run_id}",
    response_model=RunRead,
    responses=error_responses(404, 409),
    summary="Update run status (completed / failed / running)",
)
async def update_run(run_id: int, data: RunUpdate, db: DbSession):
    return await tracking.update_run(db, run_id, data)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(404),
    summary="Delete a run with its metrics",
)
async def delete_run(run_id: int, db: DbSession) -> None:
    await tracking.delete_run(db, run_id)
