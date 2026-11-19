"""Exercise trainer failure/resume against an API that commits before disconnecting."""
# ruff: noqa: E402

import json
from pathlib import Path

import httpx
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

from torch.utils.data import DataLoader, TensorDataset

from scripts import train_cifar10 as trainer
from scripts.log_to_api import TrackingClient
from training.data import CLASSES, MEAN, STD


def test_ambiguous_metric_write_preserves_checkpoint_and_resumes_without_duplicates(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    original_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    manifest = {
        "classes": CLASSES,
        "preprocessing": {"mean": MEAN, "std": STD},
        "split_id": "fixture",
        "dataset": "synthetic-test-fixture",
    }
    monkeypatch.setattr(trainer, "load_split", lambda *args: manifest)
    monkeypatch.setattr(
        trainer, "resolve", lambda path: Path(path) if Path(path).is_absolute() else tmp_path / path
    )
    samples = TensorDataset(torch.randn(7, 3, 32, 32), torch.tensor([0, 1, 2, 3, 4, 5, 6]))

    def loaders(*args):
        train = DataLoader(
            samples, batch_size=3, shuffle=True, generator=torch.Generator().manual_seed(42)
        )
        evaluation = DataLoader(samples, batch_size=3)
        return train, evaluation, evaluation

    monkeypatch.setattr(trainer, "loaders", loaders)
    metrics, posts, statuses = {}, [], []
    disconnect = True

    def handler(request):
        nonlocal disconnect
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        if path == "/api/health":
            return httpx.Response(200, json={"status": "ok"})
        if path == "/api/experiments":
            return httpx.Response(200, json=[] if request.method == "GET" else {"id": 1})
        if path == "/api/runs":
            return httpx.Response(201, json={"id": 1})
        if path.endswith("/metrics"):
            assert body["epoch"] not in metrics, "duplicate POST after resume"
            metrics[body["epoch"]] = body
            posts.append(body["epoch"])
            if disconnect:
                disconnect = False
                raise httpx.ReadError("server committed but response was lost")
            return httpx.Response(201, json=body)
        if request.method == "GET":
            return httpx.Response(200, json={"metrics": list(metrics.values())})
        if "status" in body:
            statuses.append(body["status"])
        return httpx.Response(200, json={})

    class Client(TrackingClient):
        def __init__(self, *args):
            self._http = httpx.Client(
                base_url="http://test", transport=httpx.MockTransport(handler)
            )

    monkeypatch.setattr(trainer, "TrackingClient", Client)
    monkeypatch.setattr("sys.argv", ["train", "--device", "cpu", "--epochs", "2"])
    try:
        with pytest.raises(httpx.ReadError):
            trainer.main()
        checkpoint = next(tmp_path.glob("artifacts/cifar10/*/last.pt"))
        status_path = checkpoint.parent / "status.json"
        assert json.loads(status_path.read_text())["status"] == "needs_reconciliation"
        assert posts == [1]
        monkeypatch.setattr(
            "sys.argv", ["train", "--device", "cpu", "--epochs", "2", "--resume", str(checkpoint)]
        )
        trainer.main()
        assert posts == [1, 2]
        assert statuses == ["failed", "running", "completed"]
        assert json.loads(status_path.read_text())["status"] == "completed"
        state = torch.load(checkpoint, weights_only=True)
        assert state["epoch"] == 2
    finally:
        torch.set_num_threads(original_threads)
