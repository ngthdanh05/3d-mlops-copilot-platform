"""Copilot query tools, called the way the engine calls them."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Experiment, Metric, Run, RunStatus
from app.services.copilot.engine import _run_tool
from app.services.copilot.llm_client import ToolCall
from app.services.copilot.tool_base import ToolContext
from app.utils.seed_data import seed_database

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)


def final_val_accuracy(run: Run) -> float:
    value = run.metrics[-1].val_accuracy
    assert value is not None
    return value


async def run_tool(session, name: str, **arguments) -> dict:
    context = ToolContext(db=session, experiment_id=None)
    return await _run_tool(ToolCall(id="1", name=name, arguments=arguments), context)


async def add_run(
    session,
    curve: list[tuple[float, float, float | None, float | None]],
    *,
    name: str = "r",
    status: RunStatus = RunStatus.COMPLETED,
    hyperparams: dict | None = None,
) -> int:
    """Store a run from (accuracy, loss, val_accuracy, val_loss) per epoch."""
    experiment = await session.scalar(select(Experiment).where(Experiment.name == "e"))
    if experiment is None:
        experiment = Experiment(name="e")
        session.add(experiment)
    run = Run(
        experiment=experiment,
        run_name=name,
        status=status,
        hyperparams=hyperparams or {},
        metrics=[
            Metric(epoch=i, accuracy=acc, loss=loss, val_accuracy=val_acc, val_loss=val_loss)
            for i, (acc, loss, val_acc, val_loss) in enumerate(curve, start=1)
        ],
    )
    session.add(run)
    await session.commit()
    return run.id


async def seeded_runs(session, runs_per_experiment: int = 6) -> list[Run]:
    await seed_database(session, runs_per_experiment=runs_per_experiment, now=NOW)
    result = await session.scalars(select(Run).options(selectinload(Run.metrics)).order_by(Run.id))
    return list(result.all())


# ── list_experiments ──────────────────────────────────────────────────────────


async def test_list_experiments_returns_seeded_experiments(session):
    await seeded_runs(session)

    result = await run_tool(session, "list_experiments")

    assert [e["name"] for e in result["experiments"]] == [
        "mock-mnist-cnn",
        "mock-cifar10-resnet18",
    ]
    assert all(e["experiment_id"] for e in result["experiments"])


async def test_list_experiments_on_empty_database(session):
    assert await run_tool(session, "list_experiments") == {"experiments": []}


# ── find_best_runs ────────────────────────────────────────────────────────────


async def test_find_best_runs_matches_seeded_data(session):
    runs = await seeded_runs(session)
    completed = [r for r in runs if r.status is RunStatus.COMPLETED]
    expected = max(completed, key=final_val_accuracy)

    result = await run_tool(session, "find_best_runs", metric="val_accuracy")

    assert result["completed_runs"] == len(completed)
    assert result["runs"][0]["run_id"] == expected.id
    assert result["runs"][0]["value"] == expected.metrics[-1].val_accuracy


async def test_find_best_runs_reports_unknown_experiment(session):
    result = await run_tool(session, "find_best_runs", experiment_id=999)
    assert result == {"error": "Experiment 999 not found"}


# ── find_runs_by_name ─────────────────────────────────────────────────────────


async def test_find_runs_by_name_ignores_case_and_keeps_the_ids(session):
    a = await add_run(session, [], name="run-001")
    b = await add_run(session, [], name="run-002")
    await add_run(session, [], name="run-003")

    result = await run_tool(session, "find_runs_by_name", run_names=["RUN-001", "Run-002"])

    assert [r["run_id"] for r in result["runs"]] == [a, b]
    assert result["runs"][0]["run_name"] == "run-001"
    assert result["not_found"] == []


async def test_find_runs_by_name_reports_unknown_names(session):
    a = await add_run(session, [], name="run-001")

    result = await run_tool(session, "find_runs_by_name", run_names=["run-001", "Run-404"])

    assert [r["run_id"] for r in result["runs"]] == [a]
    assert result["not_found"] == ["Run-404"]


async def test_same_name_in_two_seeded_experiments_returns_both(session):
    runs = await seeded_runs(session)

    result = await run_tool(session, "find_runs_by_name", run_names=["run-001"])

    assert len(result["runs"]) == 2
    assert {r["experiment_id"] for r in result["runs"]} == {r.experiment_id for r in runs}


async def test_find_runs_by_name_is_scoped_to_the_viewed_experiment(session):
    runs = await seeded_runs(session)
    viewed = runs[-1].experiment_id
    context = ToolContext(db=session, experiment_id=viewed)
    call = ToolCall("1", "find_runs_by_name", {"run_names": ["run-001"]})

    result = await _run_tool(call, context)

    assert [r["experiment_id"] for r in result["runs"]] == [viewed]


async def test_find_runs_by_name_reports_unknown_experiment(session):
    result = await run_tool(session, "find_runs_by_name", run_names=["a"], experiment_id=999)
    assert result == {"error": "Experiment 999 not found"}


async def test_runs_found_by_name_can_be_compared_in_the_same_chat(session):
    await add_run(session, [(0.9, 0.2, 0.85, 0.3)], name="a")
    await add_run(session, [(0.8, 0.4, 0.75, 0.5)], name="b")
    session.expunge_all()  # as in a new request: the lookup loads them without metrics

    found = await run_tool(session, "find_runs_by_name", run_names=["a", "b"])
    result = await run_tool(session, "compare_runs", run_ids=[r["run_id"] for r in found["runs"]])

    assert result["best_by_metric"]["val_accuracy"]["run_name"] == "a"


# ── get_run ───────────────────────────────────────────────────────────────────


async def test_get_run_returns_every_epoch_of_a_seeded_run(session):
    run = (await seeded_runs(session))[0]

    result = await run_tool(session, "get_run", run_id=run.id)

    assert result["run_name"] == run.run_name
    assert result["status"] == run.status.value
    assert result["hyperparams"] == run.hyperparams
    assert [e["epoch"] for e in result["epochs"]] == [m.epoch for m in run.metrics]
    assert result["epochs"][-1]["val_loss"] == run.metrics[-1].val_loss


async def test_get_run_not_found(session):
    assert await run_tool(session, "get_run", run_id=999) == {"error": "Run 999 not found"}


@pytest.mark.parametrize("tool", ["get_run", "detect_overfitting"])
async def test_metrics_load_after_a_ui_tool_already_touched_the_run(session_factory, tool):
    async with session_factory() as s:
        run_id = await add_run(s, [(0.5, 1.0, 0.5, 1.0)])

    # One chat shares a session, and UI tools load the run without its metrics.
    async with session_factory() as s:
        context = ToolContext(db=s, experiment_id=None)
        await _run_tool(ToolCall("1", "focus_camera", {"run_id": run_id}), context)
        result = await _run_tool(ToolCall("2", tool, {"run_id": run_id}), context)

    assert "error" not in result


# ── compare_runs ──────────────────────────────────────────────────────────────


async def test_compare_runs_on_seeded_data(session):
    runs = [r for r in await seeded_runs(session) if r.status is RunStatus.COMPLETED][:3]

    result = await run_tool(session, "compare_runs", run_ids=[r.id for r in runs])

    assert [r["run_id"] for r in result["runs"]] == [r.id for r in runs]
    assert result["runs"][0]["final_val_loss"] == runs[0].metrics[-1].val_loss
    best = max(runs, key=final_val_accuracy)
    assert result["best_by_metric"]["val_accuracy"]["run_id"] == best.id


async def test_compare_runs_splits_hyperparams(session):
    a = await add_run(
        session,
        [(0.5, 1.0, 0.5, 1.0)],
        name="a",
        hyperparams={"optimizer": "adam", "learning_rate": 0.1, "layers": [64, 32]},
    )
    b = await add_run(
        session,
        [(0.5, 1.0, 0.5, 1.0)],
        name="b",
        hyperparams={
            "optimizer": "adam",
            "learning_rate": 0.01,
            "layers": [64, 32],
            "dropout": 0.2,
        },
    )

    result = await run_tool(session, "compare_runs", run_ids=[a, b])

    assert result["hyperparams_shared"] == {"layers": [64, 32], "optimizer": "adam"}
    assert result["hyperparams_differing"] == {
        "dropout": {str(a): None, str(b): 0.2},
        "learning_rate": {str(a): 0.1, str(b): 0.01},
    }


async def test_compare_runs_ranks_loss_lowest_first_and_gives_the_spread(session):
    a = await add_run(session, [(0.9, 0.2, 0.85, 0.30)], name="a")
    b = await add_run(session, [(0.8, 0.4, 0.75, 0.55)], name="b")

    best = (await run_tool(session, "compare_runs", run_ids=[b, a]))["best_by_metric"]

    assert best["val_loss"] == {
        "run_id": a,
        "run_name": "a",
        "value": 0.30,
        "spread_to_worst": 0.25,
    }
    assert best["val_accuracy"]["run_id"] == a


async def test_compare_runs_never_names_an_unfinished_run_best(session):
    running = await add_run(
        session, [(0.99, 0.01, 0.99, 0.01)], name="running", status=RunStatus.RUNNING
    )
    done = await add_run(session, [(0.6, 0.5, 0.6, 0.5)], name="done")

    result = await run_tool(session, "compare_runs", run_ids=[running, done])

    assert result["best_by_metric"]["val_accuracy"]["run_id"] == done
    assert result["runs"][0]["status"] == "running"


async def test_compare_runs_handles_runs_without_metrics(session):
    a = await add_run(session, [], name="a")
    b = await add_run(session, [], name="b")

    result = await run_tool(session, "compare_runs", run_ids=[a, b])

    assert result["runs"][0]["final_epoch"] is None
    assert result["best_by_metric"] == {}


async def test_compare_runs_reports_the_missing_run(session):
    real = await add_run(session, [(0.5, 1.0, 0.5, 1.0)])
    result = await run_tool(session, "compare_runs", run_ids=[real, 999])
    assert result == {"error": "Run 999 not found"}


@pytest.mark.parametrize("run_ids", [[1], [1, 1], []])
async def test_compare_runs_needs_two_different_runs(session, run_ids):
    result = await run_tool(session, "compare_runs", run_ids=run_ids)
    assert "Invalid arguments" in result["error"]


# ── detect_overfitting ────────────────────────────────────────────────────────


async def test_detects_a_widening_train_val_gap(session):
    run = await add_run(
        session,
        [
            (0.70, 0.90, 0.70, 0.90),
            (0.80, 0.60, 0.79, 0.65),
            (0.88, 0.40, 0.84, 0.50),
            (0.93, 0.25, 0.85, 0.48),
            (0.97, 0.15, 0.85, 0.50),
            (0.99, 0.08, 0.85, 0.52),
        ],
    )

    result = await run_tool(session, "detect_overfitting", run_id=run)

    assert result["verdict"] == "overfitting"
    assert result["accuracy_gap"]["start"] == pytest.approx(0.0167, abs=1e-4)
    assert result["accuracy_gap"]["end"] == pytest.approx(0.1133, abs=1e-4)
    assert result["accuracy_gap"]["by_epoch"][-1] == {"epoch": 6, "gap": 0.14}


async def test_detects_rising_val_loss_without_validation_accuracy(session):
    run = await add_run(
        session,
        [
            (0.7, 0.9, None, 0.90),
            (0.8, 0.6, None, 0.50),
            (0.9, 0.4, None, 0.60),
            (0.9, 0.3, None, 0.70),
            (0.9, 0.2, None, 0.80),
        ],
    )

    result = await run_tool(session, "detect_overfitting", run_id=run)

    assert result["verdict"] == "overfitting"
    assert result["accuracy_gap"] is None
    assert result["val_loss_trend"]["lowest_epoch"] == 2


async def test_healthy_curves_are_not_overfitting(session):
    run = await add_run(
        session,
        [
            (0.60, 1.00, 0.61, 1.00),
            (0.75, 0.70, 0.75, 0.72),
            (0.85, 0.50, 0.84, 0.52),
            (0.90, 0.35, 0.89, 0.38),
            (0.92, 0.30, 0.91, 0.33),
            (0.93, 0.27, 0.92, 0.30),
        ],
    )
    result = await run_tool(session, "detect_overfitting", run_id=run)
    assert result["verdict"] == "no_overfitting"


async def test_a_constant_gap_is_only_possible_overfitting(session):
    run = await add_run(
        session,
        [
            (0.90, 0.30, 0.82, 0.50),
            (0.91, 0.28, 0.83, 0.48),
            (0.92, 0.26, 0.84, 0.46),
            (0.93, 0.24, 0.85, 0.44),
        ],
    )
    result = await run_tool(session, "detect_overfitting", run_id=run)
    assert result["verdict"] == "possible_overfitting"


async def test_divergence_is_not_called_overfitting(session):
    # Train and validation loss explode together: the model is diverging.
    run = await add_run(
        session,
        [
            (0.5, 1.0, 0.5, 1.0),
            (0.6, 0.8, 0.6, 0.8),
            (0.1, 5.0, 0.1, 5.0),
            (0.1, 9.0, 0.1, 9.0),
        ],
        status=RunStatus.FAILED,
    )
    result = await run_tool(session, "detect_overfitting", run_id=run)
    assert result["verdict"] == "no_overfitting"


@pytest.mark.parametrize(
    "curve",
    [
        [],
        [(0.5, 1.0, 0.5, 1.0)] * 3,  # too short for a trend
        [(0.5, 1.0, None, None)] * 10,  # no validation data at all
    ],
)
async def test_too_little_validation_data(session, curve):
    run = await add_run(session, curve)
    result = await run_tool(session, "detect_overfitting", run_id=run)
    assert result["verdict"] == "insufficient_data"


async def test_detect_overfitting_not_found(session):
    result = await run_tool(session, "detect_overfitting", run_id=999)
    assert result == {"error": "Run 999 not found"}


async def test_verdicts_separate_seeded_regularized_and_unregularized_runs(session):
    completed = [
        r
        for r in await seeded_runs(session, runs_per_experiment=60)
        if r.status is RunStatus.COMPLETED and r.hyperparams["epochs"] >= 30
    ]
    regularized = [
        r
        for r in completed
        if r.hyperparams["dropout"] == 0.5 and r.hyperparams["weight_decay"] >= 1e-3
    ]
    unregularized = [
        r
        for r in completed
        if r.hyperparams["dropout"] == 0.0 and r.hyperparams["weight_decay"] == 0.0
    ]
    assert regularized and unregularized

    async def verdict(run: Run) -> str:
        return (await run_tool(session, "detect_overfitting", run_id=run.id))["verdict"]

    assert {await verdict(r) for r in regularized} == {"no_overfitting"}
    verdicts = [await verdict(r) for r in unregularized]
    assert verdicts.count("overfitting") > len(verdicts) / 2
