"""API behaviour at the edges: an empty database, the PoC's data scale and malformed input."""

from datetime import UTC, datetime

import pytest

from app.models import Experiment, Metric, Run, RunStatus

CHAT = "/api/copilot/chat"
BEST_RUN_QUESTION = {"message": "Run nào tốt nhất?"}
SQLITE_INT_MAX = 2**63 - 1
TOO_BIG_ID = SQLITE_INT_MAX + 1


async def seed_runs(session, count: int, name: str = "scale") -> tuple[int, dict[int, float]]:
    """Insert `count` completed runs. Returns the experiment id and val_accuracy by run id."""
    now = datetime.now(UTC)
    experiment = Experiment(name=name, created_at=now)
    experiment.runs = [
        Run(
            run_name=f"run-{index:04d}",
            status=RunStatus.COMPLETED,
            hyperparams={
                "learning_rate": 10 ** -(1 + index % 4),
                "batch_size": 2 ** (4 + index % 5),
            },
            created_at=now,
            finished_at=now,
            metrics=[
                Metric(
                    epoch=epoch,
                    accuracy=0.5,
                    loss=1.0 / epoch,
                    val_accuracy=0.4 + 0.5 * index / count,
                    val_loss=1.0 / epoch,
                    logged_at=now,
                )
                for epoch in (1, 2)
            ],
        )
        for index in range(count)
    ]
    session.add(experiment)
    await session.commit()
    return experiment.id, {run.id: run.metrics[-1].val_accuracy for run in experiment.runs}


# ── Empty database ────────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", ["/api/experiments", "/api/runs"])
async def test_lists_are_empty_on_a_new_database(client, path):
    response = await client.get(path)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/experiments/1"),
        ("GET", "/api/runs/1"),
        ("GET", "/api/runs?experiment_id=1"),
        ("DELETE", "/api/experiments/1"),
        ("DELETE", "/api/runs/1"),
    ],
)
async def test_lookups_are_404_on_a_new_database(client, method, path):
    assert (await client.request(method, path)).status_code == 404


async def test_run_list_is_empty_for_an_experiment_without_runs(client):
    created = await client.post("/api/experiments", json={"name": "no-runs"})
    response = await client.get("/api/runs", params={"experiment_id": created.json()["id"]})
    assert response.status_code == 200
    assert response.json() == []


async def test_copilot_answers_without_actions_on_a_new_database(client):
    response = await client.post(CHAT, json=BEST_RUN_QUESTION)
    assert response.status_code == 200
    assert response.json()["message"]
    assert response.json()["actions"] == []


async def test_copilot_stream_finishes_on_a_new_database(client):
    response = await client.post(f"{CHAT}/stream", json=BEST_RUN_QUESTION)
    assert response.status_code == 200
    assert '"type":"done"' in response.text


# ── Data scale (PoC limit: 500 runs per experiment) ───────────────────────────


@pytest.mark.parametrize("count", [101, 500])
async def test_run_list_returns_every_run_with_its_final_metrics(client, session, count):
    experiment_id, expected = await seed_runs(session, count)

    response = await client.get("/api/runs", params={"experiment_id": experiment_id})

    assert response.status_code == 200
    runs = response.json()
    assert len(runs) == count
    assert {run["id"]: run["final_val_accuracy"] for run in runs} == pytest.approx(expected)
    assert {run["final_epoch"] for run in runs} == {2}


async def test_final_metrics_come_from_the_highest_epoch_whatever_the_logging_order(client):
    experiment = await client.post("/api/experiments", json={"name": "order"})
    experiment_id = experiment.json()["id"]
    run = await client.post("/api/runs", json={"experiment_id": experiment_id, "run_name": "run"})
    run_id = run.json()["id"]
    for epoch, accuracy in [(3, 0.3), (1, 0.1), (2, 0.2)]:
        await client.post(
            f"/api/runs/{run_id}/metrics", json={"epoch": epoch, "accuracy": accuracy, "loss": 1}
        )

    [summary] = (await client.get("/api/runs", params={"experiment_id": experiment_id})).json()

    assert (summary["final_epoch"], summary["final_accuracy"]) == (3, 0.3)
    assert len((await client.get(f"/api/runs/{run_id}")).json()["metrics"]) == 3


async def test_copilot_picks_the_best_of_many_runs(client, session):
    experiment_id, expected = await seed_runs(session, 150)
    best_run_id = max(expected, key=lambda run_id: expected[run_id])

    response = await client.post(CHAT, json={**BEST_RUN_QUESTION, "experiment_id": experiment_id})

    assert response.status_code == 200
    assert {"type": "highlight_runs", "run_ids": [best_run_id]} in response.json()["actions"]
    assert {"type": "focus_camera", "run_id": best_run_id} in response.json()["actions"]


async def test_deleting_an_experiment_removes_all_of_its_many_runs(client, session):
    experiment_id, _ = await seed_runs(session, 150)
    other_experiment_id, other_runs = await seed_runs(session, 3, name="other")

    assert (await client.delete(f"/api/experiments/{experiment_id}")).status_code == 204

    remaining = (await client.get("/api/runs")).json()
    assert {run["id"] for run in remaining} == set(other_runs)
    assert {run["experiment_id"] for run in remaining} == {other_experiment_id}


# ── Malformed requests ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "path",
    ["/api/experiments", "/api/runs", "/api/runs/1/metrics", CHAT, f"{CHAT}/stream"],
)
@pytest.mark.parametrize("body", ["", "{not json", "[]", '"text"', "null"])
async def test_a_body_that_is_not_the_expected_object_is_422(client, path, body):
    response = await client.post(path, content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422


@pytest.mark.parametrize("path", ["/api/runs?experiment_id=abc", "/api/experiments/abc"])
async def test_a_non_integer_id_is_422(client, path):
    assert (await client.get(path)).status_code == 422


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", f"/api/experiments/{TOO_BIG_ID}", None),
        ("DELETE", f"/api/experiments/{TOO_BIG_ID}", None),
        ("GET", f"/api/runs?experiment_id={TOO_BIG_ID}", None),
        ("GET", f"/api/runs/{TOO_BIG_ID}", None),
        ("PUT", f"/api/runs/{TOO_BIG_ID}", {"status": "failed"}),
        ("DELETE", f"/api/runs/{TOO_BIG_ID}", None),
        ("POST", f"/api/runs/{TOO_BIG_ID}/metrics", {"epoch": 1, "accuracy": 0.5, "loss": 0.5}),
        ("POST", "/api/runs", {"experiment_id": TOO_BIG_ID, "run_name": "run"}),
    ],
)
async def test_an_id_too_large_for_the_database_is_rejected(client, method, path, body):
    response = await client.request(method, path, json=body)
    assert response.status_code == 422


async def test_an_epoch_too_large_for_the_database_is_rejected(client):
    experiment = await client.post("/api/experiments", json={"name": "exp"})
    run = await client.post(
        "/api/runs", json={"experiment_id": experiment.json()["id"], "run_name": "run"}
    )
    response = await client.post(
        f"/api/runs/{run.json()['id']}/metrics",
        json={"epoch": TOO_BIG_ID, "accuracy": 0.5, "loss": 0.5},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("run_id", [0, -1, -TOO_BIG_ID])
async def test_an_id_below_the_valid_range_is_422(client, run_id):
    assert (await client.get(f"/api/runs/{run_id}")).status_code == 422


async def test_the_largest_valid_id_is_just_not_found(client):
    assert (await client.get(f"/api/runs/{SQLITE_INT_MAX}")).status_code == 404


@pytest.mark.parametrize("body", [r'{"name": "a\ud800b"}', r'{"name": "\udfff"}'])
async def test_text_that_cannot_be_stored_is_rejected(client, body):
    response = await client.post(
        "/api/experiments", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]
