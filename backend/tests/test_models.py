import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.database import Base
from app.models import Experiment, Metric, Run, RunStatus


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


async def test_experiment_run_metric_roundtrip(session):
    exp = Experiment(name="MNIST-CNN-v1", description="demo")
    run = Run(run_name="run-001", hyperparams={"lr": 0.001, "batch_size": 32})
    run.metrics = [
        Metric(epoch=2, accuracy=0.9, loss=0.3, val_accuracy=0.88, val_loss=0.35),
        Metric(epoch=1, accuracy=0.8, loss=0.5),
    ]
    exp.runs.append(run)
    session.add(exp)
    await session.commit()
    session.expunge_all()  # force a fresh load from the DB

    loaded = (
        await session.execute(
            select(Run).options(selectinload(Run.metrics), selectinload(Run.experiment))
        )
    ).scalar_one()
    assert loaded.status is RunStatus.RUNNING
    assert loaded.hyperparams == {"lr": 0.001, "batch_size": 32}
    assert loaded.experiment.name == "MNIST-CNN-v1"
    assert [m.epoch for m in loaded.metrics] == [1, 2]
    assert loaded.created_at is not None


async def test_metric_accuracy_out_of_range_rejected(session):
    exp = Experiment(name="exp")
    run = Run(run_name="r", experiment=exp)
    session.add_all([exp, run, Metric(run=run, epoch=1, accuracy=1.5, loss=0.1)])
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_experiment_cascades(session):
    exp = Experiment(name="exp")
    run = Run(run_name="r", experiment=exp)
    run.metrics.append(Metric(epoch=1, accuracy=0.5, loss=1.0))
    session.add(exp)
    await session.commit()

    await session.delete(exp)
    await session.commit()
    assert (await session.execute(select(Metric))).first() is None
    assert (await session.execute(select(Run))).first() is None
