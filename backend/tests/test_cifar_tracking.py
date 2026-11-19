import httpx
import pytest

from scripts.log_to_api import TrackingClient, TrackingError
from training.tracking import reconcile, validate_tracking_url


@pytest.mark.parametrize(
    "url", ["https://example.com", "http://localhost@evil.com", "http://192.168.1.2:8000"]
)
def test_cifar_tracking_refuses_external_urls(url):
    with pytest.raises(ValueError, match="loopback"):
        validate_tracking_url(url)


async def test_artifacts_preserve_final_epoch_and_old_runs(client):
    exp = (await client.post("/api/experiments", json={"name": "real"})).json()["id"]
    run = (await client.post("/api/runs", json={"experiment_id": exp, "run_name": "cnn"})).json()
    assert run["artifacts"] is None
    for number, accuracy in [(1, 0.8), (2, 0.7)]:
        response = await client.post(
            f"/api/runs/{run['id']}/metrics",
            json={"epoch": number, "accuracy": accuracy, "loss": 1, "val_accuracy": accuracy},
        )
        assert response.status_code == 201
    response = await client.put(
        f"/api/runs/{run['id']}", json={"artifacts": {"best_epoch": 1, "best_val_accuracy": 0.8}}
    )
    assert response.status_code == 200
    summary = (await client.get("/api/runs")).json()[0]
    assert summary["final_epoch"] == 2
    assert summary["final_val_accuracy"] == 0.7
    assert summary["artifacts"]["best_epoch"] == 1
    resumed = await client.put(f"/api/runs/{run['id']}", json={"target_epochs": 4})
    assert resumed.status_code == 200
    assert resumed.json()["hyperparams"]["epochs"] == 4
    assert (
        await client.put(f"/api/runs/{run['id']}", json={"target_epochs": 1})
    ).status_code == 409
    assert (
        await client.put(
            f"/api/runs/{run['id']}",
            json={
                "artifacts": {
                    "best_epoch": 1,
                    "best_val_accuracy": 0.8,
                    "best_checkpoint": "C:/secret/best.pt",
                }
            },
        )
    ).status_code == 422


def test_reconcile_skips_logged_and_replays_pending_epoch():
    logged = {"epoch": 1, "accuracy": 0.5, "loss": 1.0, "val_accuracy": 0.4, "val_loss": 1.1}
    pending = {**logged, "epoch": 2}
    writes = []

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json={"metrics": [logged]})
        writes.append(request)
        return httpx.Response(201, json={})

    with TrackingClient() as client:
        client._http.close()
        client._http = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
        reconcile(client, 1, [logged, pending])
        assert len(writes) == 1
        with pytest.raises(TrackingError, match="differ"):
            reconcile(client, 1, [{**logged, "accuracy": 0.1}])
