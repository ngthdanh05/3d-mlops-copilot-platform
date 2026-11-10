import json
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models import Experiment, Metric, Run, RunStatus
from app.schemas import (
    ExperimentCreate,
    ExperimentRead,
    MetricCreate,
    RunCreate,
    RunDetail,
    RunSummary,
    RunUpdate,
)

NAIVE_TS = datetime(2026, 11, 6, 10, 30, 0)  # what SQLite hands back


def _orm_run(with_metrics: bool = True) -> Run:
    run = Run(
        id=7,
        experiment_id=1,
        run_name="run-007",
        status=RunStatus.COMPLETED,
        hyperparams={"lr": 0.01, "batch_size": 64, "layers": [128, 64]},
        created_at=NAIVE_TS,
        finished_at=NAIVE_TS + timedelta(minutes=5),
    )
    if with_metrics:
        run.metrics = [
            Metric(id=i, run_id=7, epoch=i, accuracy=0.5 + i / 10, loss=1 / i, logged_at=NAIVE_TS)
            for i in (2, 3, 1)
        ]
        run.metrics[1].val_accuracy = 0.79
        run.metrics[1].val_loss = 0.4
    return run


# ── Experiment ────────────────────────────────────────────────────────────────


def test_experiment_create_strips_and_validates():
    exp = ExperimentCreate(name="  MNIST-CNN-v1 ")
    assert exp.name == "MNIST-CNN-v1"
    assert exp.description is None
    with pytest.raises(ValidationError):
        ExperimentCreate(name="   ")
    with pytest.raises(ValidationError):
        ExperimentCreate.model_validate({"name": "x", "unknown_field": 1})


def test_experiment_read_from_orm_is_utc():
    read = ExperimentRead.model_validate(
        Experiment(id=1, name="exp", description=None, created_at=NAIVE_TS)
    )
    assert read.created_at.tzinfo is UTC
    assert json.loads(read.model_dump_json())["created_at"] == "2026-11-06T10:30:00Z"


# ── Metric ────────────────────────────────────────────────────────────────────


def test_metric_create_valid():
    m = MetricCreate(epoch=1, accuracy=0.95, loss=0.12, val_accuracy=0.93, val_loss=0.2)
    assert m.epoch == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"epoch": 0},
        {"accuracy": 1.01},
        {"accuracy": -0.1},
        {"loss": -0.5},
        {"val_accuracy": 2},
        {"val_loss": -1},
        {"loss": float("nan")},
        {"loss": float("inf")},
    ],
)
def test_metric_create_rejects_invalid(overrides):
    data = {"epoch": 1, "accuracy": 0.5, "loss": 0.5} | overrides
    with pytest.raises(ValidationError):
        MetricCreate(**data)


# ── Run ───────────────────────────────────────────────────────────────────────


def test_run_create_valid_keeps_hyperparams_as_given():
    run = RunCreate.model_validate_json(
        '{"experiment_id": 1, "run_name": "run-001",'
        ' "hyperparams": {"lr": 0.001, "batch_size": 32, "optimizer": "adam", "layers": [64]}}'
    )
    assert run.hyperparams == {"lr": 0.001, "batch_size": 32, "optimizer": "adam", "layers": [64]}
    assert RunCreate(experiment_id=1, run_name="r").hyperparams == {}


@pytest.mark.parametrize(
    "hyperparams",
    [
        {"learning_rate": 0},
        {"lr": -0.01},
        {"lr": "0.01"},
        {"lr": True},
        {"epochs": 0},
        {"epochs": 2.5},
        {"batch_size": 0},
        {"batch_size": False},
        {"": 1},
    ],
)
def test_run_create_rejects_invalid_hyperparams(hyperparams):
    with pytest.raises(ValidationError):
        RunCreate(experiment_id=1, run_name="r", hyperparams=hyperparams)


def test_run_create_rejects_missing_fields():
    with pytest.raises(ValidationError):
        RunCreate.model_validate({"run_name": "r"})
    with pytest.raises(ValidationError):
        RunCreate(experiment_id=1, run_name="")


def test_run_update_rules():
    upd = RunUpdate.model_validate(
        {"status": "completed", "finished_at": "2026-11-06T17:30:00+07:00"}
    )
    assert upd.status is RunStatus.COMPLETED
    assert upd.finished_at is not None
    assert upd.finished_at == datetime(2026, 11, 6, 10, 30, tzinfo=UTC)
    assert upd.finished_at.tzinfo is UTC
    assert RunUpdate.model_validate({"status": "failed"}).finished_at is None

    with pytest.raises(ValidationError):
        RunUpdate()
    with pytest.raises(ValidationError):
        RunUpdate.model_validate({"status": "paused"})
    with pytest.raises(ValidationError):
        RunUpdate.model_validate(
            {"status": "running", "finished_at": datetime.now(timezone(timedelta(hours=7)))}
        )


def test_run_summary_uses_last_epoch():
    summary = RunSummary.from_run(_orm_run())
    assert summary.final_epoch == 3
    assert summary.final_accuracy == pytest.approx(0.8)
    assert summary.final_loss == pytest.approx(1 / 3)
    assert summary.final_val_accuracy == 0.79
    assert summary.final_val_loss == 0.4
    assert summary.status is RunStatus.COMPLETED
    assert "metrics" not in summary.model_dump()


def test_run_summary_without_metrics():
    summary = RunSummary.from_run(_orm_run(with_metrics=False))
    assert summary.final_epoch is None and summary.final_accuracy is None


def test_run_detail_json_roundtrip():
    detail = RunDetail.model_validate(_orm_run())
    payload = json.loads(detail.model_dump_json())
    assert payload["status"] == "completed"
    assert payload["hyperparams"]["layers"] == [128, 64]
    assert [m["epoch"] for m in payload["metrics"]] == [2, 3, 1]  # order comes from the ORM
    assert payload["finished_at"] == "2026-11-06T10:35:00Z"
    assert RunDetail.model_validate_json(detail.model_dump_json()) == detail
