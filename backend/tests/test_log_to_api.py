"""Tests for the scripts/log_to_api.py client, run against the real app in-process."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.deps import get_db
from scripts.log_to_api import TrackingClient, TrackingError


@pytest.fixture
def tracking(session_factory):
    async def _get_db():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _get_db
    # Not used as a context manager: that would run the lifespan against the real mlops.db.
    http = TestClient(app)  # httpx.Client subclass bound to the ASGI app
    client = TrackingClient()
    client._http.close()
    client._http = http
    yield client
    client.close()
    app.dependency_overrides.clear()


def test_full_run_lifecycle(tracking):
    exp = tracking.ensure_experiment("demo")
    assert tracking.ensure_experiment("demo")["id"] == exp["id"]  # idempotent

    with tracking.start_run(exp["id"], {"learning_rate": 0.01}) as run:
        assert run.name == "run-001"
        for epoch in (1, 2):
            run.log(epoch, accuracy=0.5, loss=1.0, val_accuracy=0.4, val_loss=None)

    [summary] = tracking.list_runs(exp["id"])
    assert summary["status"] == "completed"
    assert summary["final_epoch"] == 2
    assert tracking.next_run_name(exp["id"]) == "run-002"


def test_exception_marks_run_failed(tracking):
    exp = tracking.ensure_experiment("demo")
    with pytest.raises(TrackingError, match="not finite"):
        with tracking.start_run(exp["id"], {}) as run:
            run.log(1, accuracy=0.5, loss=float("nan"))
    assert tracking.list_runs(exp["id"])[0]["status"] == "failed"


def test_api_errors_raise_tracking_error(tracking):
    with pytest.raises(TrackingError, match="404"):
        tracking.create_run(999, "r", {})
