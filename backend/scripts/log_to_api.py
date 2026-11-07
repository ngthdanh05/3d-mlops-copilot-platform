"""Minimal tracking client: send experiments, runs and per-epoch metrics to the API.

Usage:
    from log_to_api import TrackingClient

    with TrackingClient("http://localhost:8000") as client:
        exp = client.ensure_experiment("MNIST-CNN-v1", "demo")
        with client.start_run(exp["id"], hyperparams={"learning_rate": 1e-3}) as run:
            for epoch in range(1, 6):
                run.log(epoch, accuracy=0.9, loss=0.3, val_accuracy=0.88, val_loss=0.35)
        # leaving the block marks the run "completed" ("failed" if an exception escaped)
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_API_URL = "http://localhost:8000"


class TrackingError(RuntimeError):
    pass


class TrackingClient:
    def __init__(self, base_url: str = DEFAULT_API_URL, timeout: float = 10.0) -> None:
        self._http = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    # ── lifecycle ────────────────────────────────────────────────────────────
    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> TrackingClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def check_health(self) -> None:
        try:
            self._request("GET", "/api/health")
        except httpx.TransportError as exc:
            raise TrackingError(
                f"Cannot reach the API at {self._http.base_url}. Is the backend running? ({exc})"
            ) from exc

    # ── experiments ──────────────────────────────────────────────────────────
    def ensure_experiment(self, name: str, description: str | None = None) -> dict[str, Any]:
        """Return the experiment called `name`, creating it if needed."""
        for exp in self._request("GET", "/api/experiments"):
            if exp["name"] == name:
                return exp
        return self._request(
            "POST", "/api/experiments", json={"name": name, "description": description}
        )

    # ── runs ─────────────────────────────────────────────────────────────────
    def list_runs(self, experiment_id: int | None = None) -> list[dict[str, Any]]:
        params = {"experiment_id": experiment_id} if experiment_id else None
        return self._request("GET", "/api/runs", params=params)

    def next_run_name(self, experiment_id: int, prefix: str = "run-") -> str:
        taken = {r["run_name"] for r in self.list_runs(experiment_id)}
        i = 1
        while f"{prefix}{i:03d}" in taken:
            i += 1
        return f"{prefix}{i:03d}"

    def create_run(
        self, experiment_id: int, run_name: str, hyperparams: dict[str, Any]
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/runs",
            json={"experiment_id": experiment_id, "run_name": run_name, "hyperparams": hyperparams},
        )

    def update_run(self, run_id: int, status: str) -> dict[str, Any]:
        return self._request("PUT", f"/api/runs/{run_id}", json={"status": status})

    def log_metric(
        self,
        run_id: int,
        epoch: int,
        accuracy: float,
        loss: float,
        val_accuracy: float | None = None,
        val_loss: float | None = None,
    ) -> dict[str, Any]:
        values = {"accuracy": accuracy, "loss": loss, "val_accuracy": val_accuracy,
                  "val_loss": val_loss}  # fmt: skip
        for key, value in values.items():
            if value is not None and not math.isfinite(value):
                raise TrackingError(f"{key}={value} is not finite (training diverged?)")
        body = {"epoch": epoch} | {k: float(v) for k, v in values.items() if v is not None}
        return self._request("POST", f"/api/runs/{run_id}/metrics", json=body)

    @contextmanager
    def start_run(
        self,
        experiment_id: int,
        hyperparams: dict[str, Any],
        run_name: str | None = None,
    ) -> Iterator[ActiveRun]:
        """Create a run; mark it completed on success, failed if the block raises."""
        name = run_name or self.next_run_name(experiment_id)
        run = self.create_run(experiment_id, name, hyperparams)
        active = ActiveRun(self, run)
        try:
            yield active
        except BaseException:
            self.update_run(run["id"], "failed")
            raise
        else:
            self.update_run(run["id"], "completed")

    # ── internals ────────────────────────────────────────────────────────────
    def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        resp = self._http.request(method, url, **kwargs)
        if resp.is_error:
            try:
                detail = resp.json().get("detail", resp.text)
            except ValueError:
                detail = resp.text
            raise TrackingError(f"{method} {url} -> {resp.status_code}: {detail}")
        return resp.json()


@dataclass
class ActiveRun:
    client: TrackingClient
    data: dict[str, Any]

    @property
    def id(self) -> int:
        return self.data["id"]

    @property
    def name(self) -> str:
        return self.data["run_name"]

    def log(self, epoch: int, **metrics: float | None) -> dict[str, Any]:
        return self.client.log_metric(self.id, epoch, **metrics)
