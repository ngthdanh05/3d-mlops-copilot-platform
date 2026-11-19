"""Reconcile a durable local epoch journal without duplicate writes."""

from typing import Any
from urllib.parse import urlsplit

from scripts.log_to_api import TrackingClient, TrackingError


def validate_tracking_url(value: str) -> None:
    url = urlsplit(value)
    if (
        url.scheme != "http"
        or url.hostname not in {"localhost", "127.0.0.1", "::1"}
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        raise ValueError("CIFAR tracking requires an HTTP loopback API URL")


def reconcile(client: TrackingClient, run_id: int, history: list[dict[str, Any]]) -> None:
    detail = client._request("GET", f"/api/runs/{run_id}")
    logged = {m["epoch"]: m for m in detail["metrics"]}
    if any(number > len(history) for number in logged):
        raise TrackingError("API is ahead of checkpoint; resume from the newest last.pt")
    for item in history:
        values = {k: item[k] for k in ("accuracy", "loss", "val_accuracy", "val_loss")}
        if item["epoch"] in logged:
            if any(abs(logged[item["epoch"]][k] - v) > 1e-7 for k, v in values.items()):
                raise TrackingError("Checkpoint and API metric values differ")
        else:
            client.log_metric(run_id, item["epoch"], **values)
