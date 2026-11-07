import random
from collections import Counter
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import Experiment, Metric, Run, RunStatus
from app.schemas import MetricCreate, RunCreate
from app.utils.seed_data import PROFILES, generate_experiment_runs, seed_database

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def _many_runs(n: int = 200):
    rng = random.Random(0)
    return [r for p in PROFILES for r in generate_experiment_runs(rng, p, n, NOW)]


def test_generated_runs_pass_api_validation():
    for run in _many_runs():
        RunCreate(experiment_id=1, run_name=run.run_name, hyperparams=run.hyperparams)
        for m in run.metrics:
            MetricCreate(**{k: v for k, v in m.items() if k != "logged_at"})


def test_generated_runs_are_consistent():
    for run in _many_runs():
        epochs = [m["epoch"] for m in run.metrics]
        assert epochs == list(range(1, len(epochs) + 1))
        assert len(epochs) <= run.hyperparams["epochs"] <= 50
        times = [m["logged_at"] for m in run.metrics]
        assert run.created_at < times[0] and times == sorted(times)
        if run.status is RunStatus.COMPLETED:
            assert len(epochs) == run.hyperparams["epochs"]
            assert run.finished_at > times[-1]
        elif run.status is RunStatus.RUNNING:
            assert run.finished_at is None
            assert len(epochs) < run.hyperparams["epochs"]
        else:
            assert run.finished_at is not None


def test_generated_runs_are_varied():
    runs = _many_runs()
    statuses = Counter(r.status for r in runs)
    assert statuses[RunStatus.COMPLETED] > len(runs) * 0.6
    assert statuses[RunStatus.RUNNING] > 0 and statuses[RunStatus.FAILED] > 0

    final_val = [r.metrics[-1]["val_accuracy"] for r in runs if r.status is RunStatus.COMPLETED]
    assert max(final_val) > 0.95 and min(final_val) < 0.6  # good and bad runs

    # Some completed runs overfit: train/val gap clearly opens at the end.
    gaps = [
        r.metrics[-1]["accuracy"] - r.metrics[-1]["val_accuracy"]
        for r in runs
        if r.status is RunStatus.COMPLETED
    ]
    assert max(gaps) > 0.05


def test_generation_is_deterministic():
    a = generate_experiment_runs(random.Random(5), PROFILES[0], 10, NOW)
    b = generate_experiment_runs(random.Random(5), PROFILES[0], 10, NOW)
    assert a == b


async def _counts(session) -> tuple[int, int, int]:
    return (
        await session.scalar(select(func.count()).select_from(Experiment)),
        await session.scalar(select(func.count()).select_from(Run)),
        await session.scalar(select(func.count()).select_from(Metric)),
    )


async def test_seed_database_is_idempotent_and_resettable(session):
    other = Experiment(name="Digits-MLP-demo")  # unrelated data must survive
    session.add(other)
    await session.commit()

    result = await seed_database(session, runs_per_experiment=10, now=NOW)
    assert result == {p.name: 10 for p in PROFILES}
    exps, runs, metrics = await _counts(session)
    assert (exps, runs) == (3, 20) and metrics > 20 * 5

    assert await seed_database(session, runs_per_experiment=10, now=NOW) == {
        p.name: 0 for p in PROFILES
    }
    assert await _counts(session) == (exps, runs, metrics)

    await seed_database(session, runs_per_experiment=4, reset=True, now=NOW)
    exps2, runs2, _ = await _counts(session)
    assert (exps2, runs2) == (3, 8)
    assert await session.get(Experiment, other.id) is not None


async def test_seeded_data_served_by_api(client, session_factory):
    async with session_factory() as s:
        await seed_database(s, runs_per_experiment=6, now=NOW)

    runs = (await client.get("/api/runs")).json()
    assert len(runs) == 12
    assert all(r["final_epoch"] for r in runs)
    detail = (await client.get(f"/api/runs/{runs[0]['id']}")).json()
    assert len(detail["metrics"]) == runs[0]["final_epoch"]
