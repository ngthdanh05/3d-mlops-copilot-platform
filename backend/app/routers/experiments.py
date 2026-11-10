from fastapi import APIRouter, status

from app.routers.deps import DbSession, PathId, error_responses
from app.schemas import ExperimentCreate, ExperimentRead
from app.services import tracking

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.post(
    "",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409),
    summary="Create an experiment",
)
async def create_experiment(data: ExperimentCreate, db: DbSession):
    return await tracking.create_experiment(db, data)


@router.get("", response_model=list[ExperimentRead], summary="List experiments")
async def list_experiments(db: DbSession):
    return await tracking.list_experiments(db)


@router.get(
    "/{experiment_id}",
    response_model=ExperimentRead,
    responses=error_responses(404),
    summary="Get an experiment",
)
async def get_experiment(experiment_id: PathId, db: DbSession):
    return await tracking.get_experiment(db, experiment_id)


@router.delete(
    "/{experiment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(404),
    summary="Delete an experiment with its runs and metrics",
)
async def delete_experiment(experiment_id: PathId, db: DbSession) -> None:
    await tracking.delete_experiment(db, experiment_id)
