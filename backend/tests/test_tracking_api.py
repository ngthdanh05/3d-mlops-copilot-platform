import pytest


async def _experiment(client, name="MNIST-CNN-v1") -> dict:
    resp = await client.post("/api/experiments", json={"name": name, "description": "demo"})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _run(client, experiment_id: int, name="run-001", hyperparams=None) -> dict:
    resp = await client.post(
        "/api/runs",
        json={
            "experiment_id": experiment_id,
            "run_name": name,
            "hyperparams": hyperparams or {"lr": 0.001, "batch_size": 32},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _metric(client, run_id: int, epoch: int, **kw) -> dict:
    body = {"epoch": epoch, "accuracy": 0.5 + epoch / 20, "loss": 1 / epoch} | kw
    resp = await client.post(f"/api/runs/{run_id}/metrics", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Experiments ───────────────────────────────────────────────────────────────


async def test_create_and_list_experiments(client):
    exp = await _experiment(client)
    assert exp["id"] == 1 and exp["name"] == "MNIST-CNN-v1"
    assert exp["created_at"].endswith("Z")

    await _experiment(client, "CIFAR-ResNet")
    resp = await client.get("/api/experiments")
    assert resp.status_code == 200
    assert [e["name"] for e in resp.json()] == ["MNIST-CNN-v1", "CIFAR-ResNet"]

    assert (await client.get("/api/experiments/1")).json()["name"] == "MNIST-CNN-v1"
    assert (await client.get("/api/experiments/99")).status_code == 404


async def test_duplicate_experiment_is_409(client):
    await _experiment(client)
    resp = await client.post("/api/experiments", json={"name": "MNIST-CNN-v1"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


async def test_invalid_experiment_is_422(client):
    assert (await client.post("/api/experiments", json={})).status_code == 422
    assert (await client.post("/api/experiments", json={"name": ""})).status_code == 422


# ── Runs ──────────────────────────────────────────────────────────────────────


async def test_create_run(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    assert run["status"] == "running"
    assert run["hyperparams"] == {"lr": 0.001, "batch_size": 32}
    assert run["finished_at"] is None


async def test_create_run_errors(client):
    resp = await client.post("/api/runs", json={"experiment_id": 42, "run_name": "r"})
    assert resp.status_code == 404

    exp = await _experiment(client)
    await _run(client, exp["id"])
    dup = await client.post("/api/runs", json={"experiment_id": exp["id"], "run_name": "run-001"})
    assert dup.status_code == 409

    bad = await client.post(
        "/api/runs",
        json={"experiment_id": exp["id"], "run_name": "r2", "hyperparams": {"lr": -1}},
    )
    assert bad.status_code == 422


async def test_same_run_name_allowed_in_other_experiment(client):
    a = await _experiment(client, "A")
    b = await _experiment(client, "B")
    await _run(client, a["id"])
    await _run(client, b["id"])


async def test_list_runs_with_final_metrics_and_filter(client):
    a = await _experiment(client, "A")
    b = await _experiment(client, "B")
    r1 = await _run(client, a["id"], "run-001")
    r2 = await _run(client, a["id"], "run-002")
    r3 = await _run(client, b["id"], "run-003")
    for epoch in (1, 2, 3):
        await _metric(client, r1["id"], epoch, val_accuracy=0.6, val_loss=0.9)
    await _metric(client, r3["id"], 1)

    runs = (await client.get("/api/runs")).json()
    assert [r["run_name"] for r in runs] == ["run-001", "run-002", "run-003"]
    first = runs[0]
    assert first["final_epoch"] == 3
    assert first["final_accuracy"] == pytest.approx(0.65)
    assert first["final_loss"] == pytest.approx(1 / 3)
    assert first["final_val_accuracy"] == 0.6
    assert "metrics" not in first
    assert runs[1]["final_epoch"] is None  # run without metrics

    filtered = (await client.get("/api/runs", params={"experiment_id": a["id"]})).json()
    assert {r["id"] for r in filtered} == {r1["id"], r2["id"]}
    assert (await client.get("/api/runs", params={"experiment_id": 99})).status_code == 404
    assert (await client.get("/api/runs", params={"experiment_id": 0})).status_code == 422


async def test_get_run_detail(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    for epoch in (2, 1, 3):  # logged out of order
        await _metric(client, run["id"], epoch)

    resp = await client.get(f"/api/runs/{run['id']}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["run_name"] == "run-001"
    assert [m["epoch"] for m in detail["metrics"]] == [1, 2, 3]
    assert (await client.get("/api/runs/999")).status_code == 404


async def test_update_run_status(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])

    done = await client.put(f"/api/runs/{run['id']}", json={"status": "completed"})
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["finished_at"] is not None

    explicit = await client.put(
        f"/api/runs/{run['id']}",
        json={"status": "failed", "finished_at": "2026-11-06T17:00:00+07:00"},
    )
    assert explicit.json()["status"] == "failed"
    assert explicit.json()["finished_at"] == "2026-11-06T10:00:00Z"

    reopened = await client.put(f"/api/runs/{run['id']}", json={"status": "running"})
    assert reopened.json()["finished_at"] is None


async def test_update_run_errors(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    url = f"/api/runs/{run['id']}"

    assert (await client.put(url, json={})).status_code == 422
    assert (await client.put(url, json={"status": "paused"})).status_code == 422
    assert (await client.put("/api/runs/999", json={"status": "completed"})).status_code == 404
    # finished_at alone on a still-running run is a conflict
    only_ts = await client.put(url, json={"finished_at": "2026-11-06T10:00:00Z"})
    assert only_ts.status_code == 409


# ── Metrics ───────────────────────────────────────────────────────────────────


async def test_log_metric(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    metric = await _metric(client, run["id"], 1, val_accuracy=0.7, val_loss=0.8)
    assert metric["run_id"] == run["id"]
    assert metric["epoch"] == 1
    assert metric["val_accuracy"] == 0.7
    assert metric["logged_at"].endswith("Z")


async def test_log_metric_errors(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    url = f"/api/runs/{run['id']}/metrics"
    await _metric(client, run["id"], 1)

    dup = await client.post(url, json={"epoch": 1, "accuracy": 0.5, "loss": 0.5})
    assert dup.status_code == 409
    bad = await client.post(url, json={"epoch": 2, "accuracy": 1.5, "loss": 0.5})
    assert bad.status_code == 422
    missing = await client.post(
        "/api/runs/999/metrics", json={"epoch": 1, "accuracy": 0.5, "loss": 1}
    )
    assert missing.status_code == 404


async def test_deleted_rows_not_leaking_between_tests(client):
    """Each test gets a fresh in-memory DB."""
    assert (await client.get("/api/experiments")).json() == []


async def test_finished_at_can_be_corrected_on_finished_run(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    url = f"/api/runs/{run['id']}"
    await client.put(url, json={"status": "completed"})

    resp = await client.put(url, json={"finished_at": "2026-11-06T12:00:00Z"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
    assert resp.json()["finished_at"] == "2026-11-06T12:00:00Z"


# ── Delete ────────────────────────────────────────────────────────────────────


async def _metric_run_ids(session) -> list[int]:
    from sqlalchemy import select

    from app.models import Metric

    return sorted(await session.scalars(select(Metric.run_id)))


async def test_delete_run_cascades_to_its_metrics_only(client, session):
    exp = await _experiment(client)
    doomed = await _run(client, exp["id"], "doomed")
    kept = await _run(client, exp["id"], "kept")
    await _metric(client, doomed["id"], 1)
    await _metric(client, kept["id"], 1)

    resp = await client.delete(f"/api/runs/{doomed['id']}")
    assert resp.status_code == 204
    assert resp.content == b""

    assert (await client.get(f"/api/runs/{doomed['id']}")).status_code == 404
    assert (await client.get(f"/api/runs/{kept['id']}")).status_code == 200
    assert await _metric_run_ids(session) == [kept["id"]]


async def test_delete_experiment_cascades_to_runs_and_metrics(client, session):
    doomed = await _experiment(client, "doomed")
    kept = await _experiment(client, "kept")
    doomed_run = await _run(client, doomed["id"])
    kept_run = await _run(client, kept["id"])
    await _metric(client, doomed_run["id"], 1)
    await _metric(client, kept_run["id"], 1)

    resp = await client.delete(f"/api/experiments/{doomed['id']}")
    assert resp.status_code == 204
    assert resp.content == b""

    assert (await client.get(f"/api/experiments/{doomed['id']}")).status_code == 404
    assert (await client.get(f"/api/runs/{doomed_run['id']}")).status_code == 404
    assert [r["id"] for r in (await client.get("/api/runs")).json()] == [kept_run["id"]]
    assert await _metric_run_ids(session) == [kept_run["id"]]


async def test_deleted_name_can_be_reused(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    await client.delete(f"/api/runs/{run['id']}")
    await _run(client, exp["id"])

    await client.delete(f"/api/experiments/{exp['id']}")
    await _experiment(client)


@pytest.mark.parametrize("path", ["/api/experiments", "/api/runs"])
async def test_delete_errors(client, path):
    assert (await client.delete(f"{path}/999")).status_code == 404
    assert (await client.delete(f"{path}/abc")).status_code == 422


async def test_delete_twice_is_404(client):
    exp = await _experiment(client)
    url = f"/api/experiments/{exp['id']}"
    assert (await client.delete(url)).status_code == 204
    assert (await client.delete(url)).status_code == 404


# ── Validation (422) ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("body", "bad_field"),
    [
        ({"run_name": "r"}, "experiment_id"),
        ({"experiment_id": 1}, "run_name"),
        ({"experiment_id": 1, "run_name": "   "}, "run_name"),
        ({"experiment_id": "abc", "run_name": "r"}, "experiment_id"),
        ({"experiment_id": 0, "run_name": "r"}, "experiment_id"),
        ({"experiment_id": 1, "run_name": "r", "hyperparams": [1, 2]}, "hyperparams"),
        ({"experiment_id": 1, "run_name": "r", "hyperparams": {"learning_rate": 0}}, "hyperparams"),
        ({"experiment_id": 1, "run_name": "r", "hyperparams": {"lr": "fast"}}, "hyperparams"),
        ({"experiment_id": 1, "run_name": "r", "hyperparams": {"epochs": 0}}, "hyperparams"),
        ({"experiment_id": 1, "run_name": "r", "hyperparams": {"batch_size": 8.5}}, "hyperparams"),
        ({"experiment_id": 1, "run_name": "r", "status": "completed"}, "status"),
    ],
)
async def test_create_run_validation(client, body, bad_field):
    await _experiment(client)
    resp = await client.post("/api/runs", json=body)
    assert resp.status_code == 422, resp.text
    assert any(bad_field in err["loc"] for err in resp.json()["detail"])


@pytest.mark.parametrize(
    ("body", "bad_field"),
    [
        ({"accuracy": 0.5, "loss": 0.5}, "epoch"),
        ({"epoch": 1, "loss": 0.5}, "accuracy"),
        ({"epoch": 1, "accuracy": 0.5}, "loss"),
        ({"epoch": -1, "accuracy": 0.5, "loss": 0.5}, "epoch"),
        ({"epoch": 1, "accuracy": "high", "loss": 0.5}, "accuracy"),
        ({"epoch": 1, "accuracy": 0.5, "loss": 0.5, "val_accuracy": -0.2}, "val_accuracy"),
        ({"epoch": 1, "accuracy": 0.5, "loss": 0.5, "val_loss": -3}, "val_loss"),
        ({"epoch": 1, "accuracy": 0.5, "loss": 0.5, "f1": 0.4}, "f1"),
    ],
)
async def test_log_metric_validation(client, body, bad_field):
    exp = await _experiment(client)
    run = await _run(client, exp["id"])
    resp = await client.post(f"/api/runs/{run['id']}/metrics", json=body)
    assert resp.status_code == 422, resp.text
    assert any(bad_field in err["loc"] for err in resp.json()["detail"])


async def test_malformed_requests(client):
    resp = await client.post(
        "/api/experiments", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 422
    assert (await client.get("/api/runs/abc")).status_code == 422
    assert (await client.put("/api/runs/abc", json={"status": "failed"})).status_code == 422
    assert (await client.post("/api/runs/abc/metrics", json={})).status_code == 422
    assert (await client.post("/api/experiments", json={"name": "x" * 256})).status_code == 422


# ── Full cycle & service internals ────────────────────────────────────────────


async def test_full_tracking_cycle(client):
    exp = await _experiment(client)
    run = await _run(client, exp["id"], hyperparams={"learning_rate": 0.001, "epochs": 5})
    for epoch in range(1, 6):
        await _metric(client, run["id"], epoch, val_accuracy=0.5 + epoch / 25, val_loss=1 / epoch)
    await client.put(f"/api/runs/{run['id']}", json={"status": "completed"})

    [summary] = (await client.get("/api/runs", params={"experiment_id": exp["id"]})).json()
    assert summary["status"] == "completed"
    assert summary["final_epoch"] == 5
    assert summary["final_val_accuracy"] == pytest.approx(0.7)
    detail = (await client.get(f"/api/runs/{run['id']}")).json()
    assert len(detail["metrics"]) == 5


async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200 and resp.json() == {"status": "ok"}


async def test_non_unique_integrity_errors_are_not_masked(session):
    """Only UNIQUE violations become 409; other DB errors propagate (500)."""
    from sqlalchemy.exc import IntegrityError

    from app.models import Experiment, Metric, Run
    from app.services.tracking import _commit_or_conflict

    run = Run(run_name="r", experiment=Experiment(name="e"))
    session.add(Metric(run=run, epoch=1, accuracy=2.0, loss=0.1))  # violates CHECK
    with pytest.raises(IntegrityError):
        await _commit_or_conflict(session, "should not be used")
