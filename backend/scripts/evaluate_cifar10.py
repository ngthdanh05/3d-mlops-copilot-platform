"""Evaluate a selected checkpoint; test output is separate from epoch tracking."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from torch.utils.data import DataLoader, Subset

from scripts.log_to_api import TrackingClient
from training.data import atomic_json, load_split, local_dataset, resolve
from training.engine import epoch, load_checkpoint
from training.models import device_for
from training.tracking import validate_tracking_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint")
    parser.add_argument("--data", default="data/cifar10")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument(
        "--test", action="store_true", help="Only after validation selection is final"
    )
    parser.add_argument(
        "--api-url", help="Optionally attach final test metrics to the original run"
    )
    args = parser.parse_args()
    if args.api_url:
        validate_tracking_url(args.api_url)
    path = resolve(args.checkpoint)
    device = device_for(args.device)
    model, state = load_checkpoint(path, device)
    if args.test and (path.name != "best.pt" or state["epoch"] != state["best"]["epoch"]):
        raise ValueError("Final test evaluation requires the validation-selected best.pt")
    config = state["config"]
    manifest = load_split(args.data, config["seed"])
    if config["split_id"] != manifest["split_id"]:
        raise ValueError("Checkpoint split mismatch")
    validation = Subset(
        local_dataset(args.data, True, preprocessing=config["preprocessing"]),
        manifest["validation_indices"],
    )
    report = {
        "checkpoint_epoch": state["epoch"],
        "split_id": config["split_id"],
        "classes": config["classes"],
        "validation": epoch(
            model, DataLoader(validation, batch_size=args.batch_size), device, confusion=True
        ),
    }
    if args.test:
        report["test"] = epoch(
            model,
            DataLoader(
                local_dataset(args.data, False, preprocessing=config["preprocessing"]),
                batch_size=args.batch_size,
            ),
            device,
            confusion=True,
        )
    atomic_json(
        path.parent / ("evaluation-test.json" if args.test else "evaluation-val.json"), report
    )
    if args.api_url and args.test:
        with TrackingClient(args.api_url) as client:
            client._request(
                "PUT",
                f"/api/runs/{config['run_id']}",
                json={
                    "artifacts": {
                        "best_epoch": state["best"]["epoch"],
                        "best_val_accuracy": state["best"]["accuracy"],
                        "test_accuracy": report["test"]["accuracy"],
                        "test_loss": report["test"]["loss"],
                    }
                },
            )
    print(report)


if __name__ == "__main__":
    main()
