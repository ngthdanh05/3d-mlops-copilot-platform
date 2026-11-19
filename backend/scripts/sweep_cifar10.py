"""Small sequential validation-only sweep after a completed full-data baseline."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.data import BACKEND, atomic_json, resolve
from training.engine import load_checkpoint


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="Completed baseline last.pt")
    args = parser.parse_args()
    baseline = resolve(args.baseline)
    _, state = load_checkpoint(baseline)
    config = state["config"]
    if config["subset"] or config["architecture"] != "small-cnn":
        raise ValueError("Sweep requires a full-data small CNN baseline")
    if json.loads((baseline.parent / "status.json").read_text())["status"] != "completed":
        raise ValueError("Complete baseline and reconcile tracking first")
    variants = [
        {"learning_rate": config["learning_rate"] / 2},
        {"batch_size": config["batch_size"] * 2},
        {"weight_decay": max(config["weight_decay"] * 10, 0.0001)},
        {"architecture": "resnet18"},
    ]
    directories = [baseline.parent]
    for variant in variants:
        existing = set(resolve("artifacts/cifar10").glob("*/manifest.json"))
        options = {
            key: config[key]
            for key in [
                "epochs",
                "seed",
                "device",
                "architecture",
                "batch_size",
                "learning_rate",
                "weight_decay",
                "workers",
                "data",
                "api_url",
            ]
        }
        options.update(variant)
        arguments = [
            token
            for key, value in options.items()
            for token in [f"--{key.replace('_', '-')}", str(value)]
        ]
        subprocess.run(
            [
                sys.executable,
                str(BACKEND / "scripts/run_offline.py"),
                "scripts/train_cifar10.py",
                *arguments,
            ],
            cwd=BACKEND,
            check=True,
        )
        created = set(resolve("artifacts/cifar10").glob("*/manifest.json")) - existing
        if len(created) != 1:
            raise RuntimeError("Could not identify sweep artifact directory")
        directories.append(next(iter(created)).parent)
    rows = []
    for directory in directories:
        cfg = json.loads((directory / "manifest.json").read_text())
        history = json.loads((directory / "history.json").read_text())
        rows.append(
            {
                **{
                    key: cfg[key]
                    for key in [
                        "run_id",
                        "architecture",
                        "seed",
                        "epochs",
                        "learning_rate",
                        "batch_size",
                        "weight_decay",
                        "split_id",
                    ]
                },
                "best_val_accuracy": max(h["val_accuracy"] for h in history),
                "final_val_accuracy": history[-1]["val_accuracy"],
                "final_val_loss": history[-1]["val_loss"],
                "best_epoch": max(history, key=lambda item: item["val_accuracy"])["epoch"],
                "seconds": sum(h["seconds"] for h in history),
                "peak_vram_bytes": max(h["peak_vram_bytes"] for h in history),
                "peak_rss_bytes": max(h["peak_rss_bytes"] for h in history),
                "artifact_id": directory.name,
            }
        )
    atomic_json(resolve("artifacts/cifar10/sweep.json"), rows)
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
