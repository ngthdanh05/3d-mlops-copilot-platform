"""Demo training script: train a scikit-learn MLP on handwritten digits and log to the API.

Every epoch is sent to `POST /api/runs/{id}/metrics`; at the end the run is marked
"completed" (or "failed" if training diverges / crashes) via `PUT /api/runs/{id}`.

Datasets:
  digits  (default) 8x8 digits bundled with scikit-learn, 1,797 images, no download.
  mnist   28x28 MNIST from OpenML (~15 MB download on first use, then cached).

Examples (backend must be running: `uv run uvicorn app.main:app`):
  uv run python scripts/train_mnist_demo.py --sweep
  uv run python scripts/train_mnist_demo.py --lr 0.001 --batch-size 32 --epochs 15
  uv run python scripts/train_mnist_demo.py --dataset mnist --mnist-samples 10000 --sweep
  uv run python scripts/train_mnist_demo.py --dataset mnist --random-search 30
"""

from __future__ import annotations

import argparse
import random
import sys
import time
import warnings
from dataclasses import asdict, dataclass, field, replace
from typing import Any

import numpy as np
from log_to_api import DEFAULT_API_URL, TrackingClient, TrackingError
from sklearn.datasets import fetch_openml, load_digits
from sklearn.metrics import log_loss
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier

EXPERIMENT_NAMES = {"digits": "real-digits-mlp", "mnist": "real-mnist-mlp"}

# Random search space. Epochs stay fixed so runs are comparable, which leaves alpha as the
# 3D Z axis. Its values are evenly spread because that axis is linear.
SEARCH_EPOCHS = 15
SEARCH_BATCH_SIZES = (16, 32, 64, 128, 256)
SEARCH_HIDDEN_LAYERS = ((64,), (128,), (256,), (128, 64), (256, 128))
SEARCH_ALPHAS = (0.0, 1.0, 2.0, 5.0, 10.0)


@dataclass(frozen=True)
class TrainConfig:
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 15
    hidden_layers: tuple[int, ...] = (128,)
    optimizer: str = "adam"  # "adam" | "sgd"
    alpha: float = 1e-4  # L2 regularization
    train_size: int | None = None  # cap on training samples (small → overfitting)
    seed: int = 42

    def hyperparams(self, dataset: str) -> dict[str, Any]:
        params = asdict(self) | {"hidden_layers": list(self.hidden_layers), "dataset": dataset}
        return {k: v for k, v in params.items() if v is not None}


# A small sweep that produces visibly different runs in the 3D workspace:
# good, slow, noisy, under-fitting, over-fitting and (likely) diverging configurations.
SWEEP: list[TrainConfig] = [
    TrainConfig(learning_rate=1e-3, batch_size=32, epochs=15, hidden_layers=(128,)),
    TrainConfig(learning_rate=3e-3, batch_size=64, epochs=12, hidden_layers=(256, 128)),
    TrainConfig(learning_rate=3e-4, batch_size=32, epochs=20, hidden_layers=(128, 64)),
    TrainConfig(learning_rate=1e-2, batch_size=128, epochs=10, hidden_layers=(64,)),
    TrainConfig(learning_rate=5e-2, batch_size=16, epochs=8, hidden_layers=(256,)),
    TrainConfig(learning_rate=1e-4, batch_size=128, epochs=6, hidden_layers=(32,), optimizer="sgd"),
    TrainConfig(
        learning_rate=3e-3,
        batch_size=16,
        epochs=25,
        hidden_layers=(256, 256),
        alpha=0.0,
        train_size=150,
    ),  # fmt: skip
    TrainConfig(learning_rate=1e-1, batch_size=64, epochs=12, hidden_layers=(64,), optimizer="sgd"),
    TrainConfig(learning_rate=5.0, batch_size=32, epochs=10, hidden_layers=(64,), optimizer="sgd"),
]


def random_search(n_runs: int, seed: int) -> list[TrainConfig]:
    """`n_runs` sampled configs plus deliberately bad ones. Same seed, same configs."""
    rng = random.Random(seed)
    sampled = [
        TrainConfig(
            learning_rate=float(f"{10 ** rng.uniform(-4, -1):.2g}"),
            batch_size=rng.choice(SEARCH_BATCH_SIZES),
            epochs=SEARCH_EPOCHS,
            hidden_layers=rng.choice(SEARCH_HIDDEN_LAYERS),
            optimizer=rng.choice(("adam", "adam", "sgd")),
            alpha=rng.choice(SEARCH_ALPHAS),
            seed=seed,
        )
        for _ in range(n_runs)
    ]
    overfitting = [
        TrainConfig(
            learning_rate=3e-3,
            batch_size=batch_size,
            epochs=SEARCH_EPOCHS,
            hidden_layers=(256, 256),
            alpha=0.0,
            train_size=200,
            seed=seed,
        )
        for batch_size in (16, 32, 64)
    ]
    unstable = [
        TrainConfig(
            learning_rate=learning_rate,
            batch_size=32,
            epochs=SEARCH_EPOCHS,
            hidden_layers=(64,),
            optimizer="sgd",
            alpha=1.0,
            seed=seed,
        )
        for learning_rate in (0.5, 1.0)
    ]
    return sampled + overfitting + unstable


@dataclass
class Dataset:
    x_train: np.ndarray
    y_train: np.ndarray
    x_val: np.ndarray
    y_val: np.ndarray
    classes: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        self.classes = np.unique(np.concatenate([self.y_train, self.y_val]))


def load_dataset(name: str, mnist_samples: int, seed: int) -> Dataset:
    if name == "digits":
        x, y = load_digits(return_X_y=True)
        x = x / 16.0
    else:
        print("Loading MNIST from OpenML (cached after the first download)...")
        # parser="liac-arff": the default parser would require pandas.
        x, y = fetch_openml(
            "mnist_784", version=1, return_X_y=True, as_frame=False, parser="liac-arff"
        )
        x, y = x[:mnist_samples] / 255.0, y[:mnist_samples].astype(int)
    x_train, x_val, y_train, y_val = train_test_split(
        x, y, test_size=0.2, stratify=y, random_state=seed
    )
    return Dataset(np.asarray(x_train), np.asarray(y_train), np.asarray(x_val), np.asarray(y_val))


def _evaluate(model: MLPClassifier, x: np.ndarray, y: np.ndarray, classes) -> tuple[float, float]:
    proba = model.predict_proba(x)
    if not np.all(np.isfinite(proba)):
        return float("nan"), float("nan")
    accuracy = float(np.mean(classes[np.argmax(proba, axis=1)] == y))
    return accuracy, float(log_loss(y, proba, labels=classes))


def train_and_log(
    client: TrackingClient, experiment_id: int, cfg: TrainConfig, data: Dataset, dataset: str,
    run_name: str | None = None,
) -> None:  # fmt: skip
    x_train, y_train = data.x_train, data.y_train
    if cfg.train_size is not None:
        x_train, y_train = x_train[: cfg.train_size], y_train[: cfg.train_size]

    model = MLPClassifier(
        hidden_layer_sizes=cfg.hidden_layers,
        solver=cfg.optimizer,
        learning_rate_init=cfg.learning_rate,
        # scikit-learn has no type hints: the checker infers str from the "auto" default.
        batch_size=min(cfg.batch_size, len(x_train)),  # pyright: ignore[reportArgumentType]
        alpha=cfg.alpha,
        momentum=0.9,
        random_state=cfg.seed,
    )

    started = time.perf_counter()
    try:
        with client.start_run(experiment_id, cfg.hyperparams(dataset), run_name) as run:
            print(f"\n> {run.name}  {cfg.hyperparams(dataset)}")
            for epoch in range(1, cfg.epochs + 1):
                # One partial_fit call = one pass over the (shuffled) training set.
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)  # overflow on divergence
                    model.partial_fit(x_train, y_train, classes=data.classes)
                    acc, loss = _evaluate(model, x_train, y_train, data.classes)
                    val_acc, val_loss = _evaluate(model, data.x_val, data.y_val, data.classes)
                run.log(epoch, accuracy=acc, loss=loss, val_accuracy=val_acc, val_loss=val_loss)
                print(
                    f"  epoch {epoch:>2}/{cfg.epochs}  acc={acc:.4f} loss={loss:.4f}  "
                    f"val_acc={val_acc:.4f} val_loss={val_loss:.4f}"
                )
    except TrackingError as exc:
        print(f"  [FAILED] run marked failed: {exc}")
        return
    print(f"  [OK] completed in {time.perf_counter() - started:.1f}s")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    default = TrainConfig()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--api-url", default=DEFAULT_API_URL)
    p.add_argument("--dataset", choices=["digits", "mnist"], default="digits")
    p.add_argument("--mnist-samples", type=int, default=10_000, help="subset size for mnist")
    p.add_argument("--experiment", help="experiment name (default depends on dataset)")
    p.add_argument("--sweep", action="store_true", help=f"run {len(SWEEP)} preset configs")
    p.add_argument(
        "--random-search",
        type=int,
        metavar="N",
        help="N reproducible random configs plus 5 deliberately bad ones",
    )
    p.add_argument("--run-name", help="defaults to the next free run-NNN")
    p.add_argument("--lr", type=float, default=default.learning_rate)
    p.add_argument("--batch-size", type=int, default=default.batch_size)
    p.add_argument("--epochs", type=int, default=default.epochs)
    p.add_argument("--hidden-layers", default="128", help="comma separated, e.g. 128,64")
    p.add_argument("--optimizer", choices=["adam", "sgd"], default=default.optimizer)
    p.add_argument("--alpha", type=float, default=default.alpha)
    p.add_argument("--train-size", type=int, default=None)
    p.add_argument("--seed", type=int, default=default.seed)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.random_search:
        configs = random_search(args.random_search, args.seed)
    elif args.sweep:
        configs = [replace(cfg, seed=args.seed) for cfg in SWEEP]
    else:
        configs = [
            TrainConfig(
                learning_rate=args.lr,
                batch_size=args.batch_size,
                epochs=args.epochs,
                hidden_layers=tuple(int(n) for n in args.hidden_layers.split(",") if n.strip()),
                optimizer=args.optimizer,
                alpha=args.alpha,
                train_size=args.train_size,
                seed=args.seed,
            )
        ]

    data = load_dataset(args.dataset, args.mnist_samples, args.seed)
    print(f"Dataset '{args.dataset}': {len(data.x_train)} train / {len(data.x_val)} val samples")

    with TrackingClient(args.api_url) as client:
        try:
            client.check_health()
        except TrackingError as exc:
            print(exc, file=sys.stderr)
            return 1
        name = args.experiment or EXPERIMENT_NAMES[args.dataset]
        experiment = client.ensure_experiment(
            name, f"scikit-learn MLPClassifier on the '{args.dataset}' dataset (demo)"
        )
        print(f"Experiment #{experiment['id']} '{experiment['name']}'")
        if args.random_search and client.list_runs(experiment["id"]):
            print("This experiment already has runs. Use --experiment to start a new one.")
            return 0
        for cfg in configs:
            train_and_log(
                client, experiment["id"], cfg, data, args.dataset,
                run_name=args.run_name if len(configs) == 1 else None,
            )  # fmt: skip

        runs = client.list_runs(experiment["id"])
    print(f"\nExperiment '{name}' now has {len(runs)} runs:")
    for r in runs:
        acc = f"{r['final_accuracy']:.4f}" if r["final_accuracy"] is not None else "  -   "
        print(f"  {r['run_name']}  {r['status']:<9}  epochs={r['final_epoch']}  acc={acc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
