"""Offline CIFAR training with durable epoch journal and tracking reconciliation."""

import argparse
import json
import math
import sys
import time
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psutil
import torch
import torchvision

from scripts.log_to_api import TrackingClient
from training.data import atomic_json, load_split, loaders, resolve
from training.engine import epoch, load_checkpoint, restore_rng, save_checkpoint, seed_all
from training.models import build_model, device_for
from training.tracking import reconcile, validate_tracking_url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/cifar10")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--architecture", choices=["small-cnn", "resnet18"], default="small-cnn")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--subset", type=int, help="Smoke only; stored distinctly in metadata")
    parser.add_argument("--resume", help="Path to last.pt relative to backend")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    validate_tracking_url(args.api_url)
    if (
        min(args.batch_size, args.epochs) < 1
        or args.workers < 0
        or args.learning_rate <= 0
        or args.weight_decay < 0
        or not math.isfinite(args.learning_rate)
        or not math.isfinite(args.weight_decay)
        or not 0 <= args.seed < 2**32
        or (args.subset is not None and args.subset < 1)
    ):
        parser.error("Invalid training budget or optimizer configuration")
    device = device_for(args.device)
    seed_all(args.seed)
    manifest = load_split(args.data, args.seed)
    config = {
        **vars(args),
        "preprocessing": manifest["preprocessing"],
        "classes": manifest["classes"],
        "split_id": manifest["split_id"],
        "dataset": manifest["dataset"],
        "torch": str(torch.__version__),
        "torchvision": str(torchvision.__version__),
        "python": sys.version.split()[0],
        "train_metrics": "eval mode; deterministic train subset; sample weighted",
        "checkpoint_ties": "earliest val_accuracy maximum",
    }
    train, train_eval, validation = loaders(
        args.data, manifest, args.batch_size, args.workers, args.seed, args.subset
    )
    history, best, start, state = [], {"epoch": 0, "accuracy": -1.0}, 1, None
    if args.resume:
        model, state = load_checkpoint(resolve(args.resume), device)
        if args.epochs < state["epoch"]:
            raise ValueError("Target epochs cannot be less than the checkpoint epoch")
        for key in (
            "architecture",
            "split_id",
            "seed",
            "batch_size",
            "learning_rate",
            "weight_decay",
            "subset",
            "workers",
        ):
            if state["config"][key] != config[key]:
                raise ValueError(f"Resume configuration mismatch: {key}")
        history, best, start = state["history"], state["best"], state["epoch"] + 1
        config["run_id"] = state["config"]["run_id"]
        directory = resolve(args.resume).parent
        if Path(args.resume).name != "last.pt":
            raise ValueError("Resume requires last.pt, not best.pt")
    else:
        model = build_model(args.architecture).to(device)
        directory = resolve("artifacts/cifar10") / uuid4().hex
    optimizer = torch.optim.Adam(
        model.parameters(), lr=args.learning_rate, weight_decay=args.weight_decay
    )
    if state:
        optimizer.load_state_dict(state["optimizer"])
        restore_rng(state, train.generator)
    directory.mkdir(parents=True, exist_ok=True)
    with TrackingClient(args.api_url) as client:
        client.check_health()
        if state:
            reconcile(client, config["run_id"], history)
            client._request(
                "PUT",
                f"/api/runs/{config['run_id']}",
                json={"status": "running", "target_epochs": args.epochs},
            )
        else:
            experiment = client.ensure_experiment(
                "real-cifar10" + ("-smoke" if args.subset else ""),
                "Real CIFAR-10; not synthetic metrics",
            )
            run = client.create_run(
                experiment["id"],
                f"{args.architecture}-{directory.name[:12]}",
                {k: v for k, v in config.items() if k not in {"data", "resume", "api_url"}},
            )
            config["run_id"] = run["id"]
        run_id = config["run_id"]
        atomic_json(directory / "manifest.json", config)
        if device.type == "cuda":
            torch.cuda.reset_peak_memory_stats(device)
        try:
            for number in range(start, args.epochs + 1):
                started = time.perf_counter()
                epoch(model, train, device, optimizer)
                training = epoch(model, train_eval, device)
                val = epoch(model, validation, device)
                item = {
                    "epoch": number,
                    "accuracy": training["accuracy"],
                    "loss": training["loss"],
                    "val_accuracy": val["accuracy"],
                    "val_loss": val["loss"],
                    "seconds": time.perf_counter() - started,
                    "rss_bytes": psutil.Process().memory_info().rss,
                    "peak_rss_bytes": getattr(
                        psutil.Process().memory_info(),
                        "peak_wset",
                        psutil.Process().memory_info().rss,
                    ),
                    "peak_vram_bytes": torch.cuda.max_memory_allocated(device)
                    if device.type == "cuda"
                    else 0,
                }
                history.append(item)
                improved = val["accuracy"] > best["accuracy"]
                if improved:
                    best = {"epoch": number, "accuracy": val["accuracy"]}
                    save_checkpoint(
                        directory / "best.pt",
                        model,
                        optimizer,
                        config,
                        number,
                        best,
                        history,
                        train.generator,
                    )
                save_checkpoint(
                    directory / "last.pt",
                    model,
                    optimizer,
                    config,
                    number,
                    best,
                    history,
                    train.generator,
                )
                # Durable checkpoint comes BEFORE network writes, allowing replay after failure.
                atomic_json(directory / "history.json", history)
                print(json.dumps(item), flush=True)
                reconcile(client, run_id, history)
                artifacts = {"best_epoch": best["epoch"], "best_val_accuracy": best["accuracy"]}
                client._request("PUT", f"/api/runs/{run_id}", json={"artifacts": artifacts})
            client.update_run(run_id, "completed")
            atomic_json(directory / "status.json", {"status": "completed", "run_id": run_id})
        except BaseException as exc:
            atomic_json(
                directory / "status.json",
                {
                    "status": "needs_reconciliation",
                    "run_id": run_id,
                    "error_type": type(exc).__name__,
                    "last_durable_epoch": history[-1]["epoch"] if history else 0,
                },
            )
            try:
                client.update_run(run_id, "failed")
            except Exception:
                pass  # local journal is authoritative while API is unreachable
            raise
    print(f"Artifacts: {directory}; run_id={run_id}")


if __name__ == "__main__":
    main()
