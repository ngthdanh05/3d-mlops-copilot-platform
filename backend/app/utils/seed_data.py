"""Seed the database with synthetic experiments and runs for frontend development.

No training happens: per-epoch curves are generated from the hyperparameters with a
simple model (exponential convergence, learning-rate sweet spot, regularization-driven
overfitting, divergence at high learning rates) plus noise, so they look realistic.

Usage (from backend/):
    uv run python -m app.utils.seed_data                 # 2 experiments x 15 runs
    uv run python -m app.utils.seed_data --runs-per-experiment 25 --seed 7
    uv run python -m app.utils.seed_data --reset         # drop & regenerate seed experiments

Only the seed experiments listed in PROFILES are created or reset; any other data
(e.g. runs logged by scripts/train_mnist_demo.py) is left untouched.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Experiment, Metric, Run, RunStatus

MAX_EPOCHS = 50  # PLAN data-scale constraint: <= 50 epochs per run


@dataclass(frozen=True)
class Profile:
    """How hard a synthetic task is and what model family it pretends to train."""

    name: str
    description: str
    model: str
    peak_accuracy: float  # best reachable val accuracy with ideal hyperparams
    chance_accuracy: float  # accuracy at epoch 0 (random guessing)
    initial_loss: float
    best_lr: float  # learning-rate sweet spot (log scale)


PROFILES: tuple[Profile, ...] = (
    Profile(
        name="MNIST-CNN-v1",
        description="[seed] Synthetic CNN runs on MNIST for frontend development",
        model="cnn-small",
        peak_accuracy=0.995,
        chance_accuracy=0.10,
        initial_loss=2.30,
        best_lr=1e-3,
    ),
    Profile(
        name="CIFAR10-ResNet18",
        description="[seed] Synthetic ResNet-18 runs on CIFAR-10 for frontend development",
        model="resnet18",
        peak_accuracy=0.935,
        chance_accuracy=0.10,
        initial_loss=2.30,
        best_lr=3e-3,
    ),
)


@dataclass
class SyntheticRun:
    run_name: str
    status: RunStatus
    hyperparams: dict[str, Any]
    created_at: datetime
    finished_at: datetime | None
    metrics: list[dict[str, Any]]

    def to_orm(self) -> Run:
        return Run(
            run_name=self.run_name,
            status=self.status,
            hyperparams=self.hyperparams,
            created_at=self.created_at,
            finished_at=self.finished_at,
            metrics=[Metric(**m) for m in self.metrics],
        )


def _sample_hyperparams(rng: random.Random, profile: Profile) -> dict[str, Any]:
    return {
        "learning_rate": float(f"{10 ** rng.uniform(-4.5, -0.5):.2g}"),
        "batch_size": rng.choice([16, 32, 64, 128, 256]),
        "epochs": rng.randint(8, MAX_EPOCHS),
        "optimizer": rng.choice(["adam", "adam", "sgd", "adamw"]),
        "dropout": rng.choice([0.0, 0.1, 0.2, 0.3, 0.5]),
        "weight_decay": rng.choice([0.0, 1e-5, 1e-4, 1e-3]),
        "model": profile.model,
    }


def _pick_status(rng: random.Random, lr: float) -> RunStatus:
    # Very high learning rates tend to blow up; otherwise a few runs crash or are in flight.
    if lr > 0.1 and rng.random() < 0.7:
        return RunStatus.FAILED
    roll = rng.random()
    if roll < 0.08:
        return RunStatus.FAILED
    if roll < 0.20:
        return RunStatus.RUNNING
    return RunStatus.COMPLETED


def generate_run(
    rng: random.Random, profile: Profile, index: int, created_at: datetime
) -> SyntheticRun:
    hp = _sample_hyperparams(rng, profile)
    lr, epochs = hp["learning_rate"], hp["epochs"]
    status = _pick_status(rng, lr)

    # ── quality of this configuration ────────────────────────────────────────
    lr_distance = abs(math.log10(lr) - math.log10(profile.best_lr))  # decades off the sweet spot
    lr_penalty = min(0.6, 0.06 * lr_distance**2)
    bs_penalty = 0.01 * abs(math.log2(hp["batch_size"] / 64))
    opt_penalty = 0.015 if hp["optimizer"] == "sgd" else 0.0
    ceiling = profile.chance_accuracy + (profile.peak_accuracy - profile.chance_accuracy) * (
        1 - lr_penalty - bs_penalty - opt_penalty
    )
    ceiling = max(profile.chance_accuracy + 0.05, ceiling)

    # Convergence speed: small learning rates converge slowly, SGD a bit slower.
    tau = max(1.0, 3.0 * (profile.best_lr / lr) ** 0.35 * (1.3 if hp["optimizer"] == "sgd" else 1))

    # Overfitting: weakly regularized runs start to diverge from validation after a point.
    regularization = hp["dropout"] * 2 + hp["weight_decay"] * 1000
    overfit_rate = max(0.0, 0.012 - 0.006 * regularization) * (1 - profile.peak_accuracy + 0.08)
    overfit_start = max(3, int(tau * 2.5))

    # ── how many epochs actually get logged ──────────────────────────────────
    if status is RunStatus.COMPLETED:
        logged = epochs
    elif status is RunStatus.RUNNING:
        logged = rng.randint(max(1, epochs // 5), max(1, epochs - 1))
    else:
        logged = rng.randint(2, max(2, min(epochs - 1, 12)))
    diverges = status is RunStatus.FAILED and lr > 0.03

    # ── generate per-epoch metrics ────────────────────────────────────────────
    metrics: list[dict[str, Any]] = []
    t = created_at + timedelta(seconds=rng.randint(5, 30))
    seconds_per_epoch = rng.uniform(20, 90) * (64 / hp["batch_size"]) ** 0.3
    for epoch in range(1, logged + 1):
        progress = 1 - math.exp(-epoch / tau)
        acc = profile.chance_accuracy + (ceiling - profile.chance_accuracy) * progress
        over = overfit_rate * max(0, epoch - overfit_start)
        train_acc = acc + over * 1.5 + rng.gauss(0, 0.004)
        val_acc = acc - over + rng.gauss(0, 0.006)

        floor_loss = max(0.005, -math.log(min(ceiling, 0.999)) * 0.6)
        loss = floor_loss + (profile.initial_loss - floor_loss) * (1 - progress)
        train_loss = loss * (1 - min(0.9, over * 8)) * rng.uniform(0.97, 1.03)
        val_loss = (loss + over * 6) * rng.uniform(0.97, 1.05)

        if diverges and epoch > logged - 2:  # loss explodes right before the crash
            blowup = 3 ** (epoch - logged + 3)
            train_loss, val_loss = train_loss * blowup, val_loss * blowup
            train_acc = val_acc = profile.chance_accuracy + rng.uniform(-0.02, 0.02)

        t += timedelta(seconds=seconds_per_epoch * rng.uniform(0.9, 1.1))
        metrics.append(
            {
                "epoch": epoch,
                "accuracy": round(_clip01(train_acc), 4),
                "loss": round(max(0.0, train_loss), 4),
                "val_accuracy": round(_clip01(val_acc), 4),
                "val_loss": round(max(0.0, val_loss), 4),
                "logged_at": t,
            }
        )

    return SyntheticRun(
        run_name=f"run-{index:03d}",
        status=status,
        hyperparams=hp,
        created_at=created_at,
        finished_at=None if status is RunStatus.RUNNING else t + timedelta(seconds=2),
        metrics=metrics,
    )


def _clip01(x: float) -> float:
    return min(1.0, max(0.0, x))


def generate_experiment_runs(
    rng: random.Random, profile: Profile, n_runs: int, now: datetime
) -> list[SyntheticRun]:
    """Runs created over the past few days, oldest first."""
    start = now - timedelta(days=3)
    offsets = sorted(rng.uniform(0, 3 * 24 * 3600 - 6 * 3600) for _ in range(n_runs))
    return [
        generate_run(rng, profile, i, start + timedelta(seconds=off))
        for i, off in enumerate(offsets, start=1)
    ]


async def seed_database(
    db: AsyncSession,
    runs_per_experiment: int = 15,
    seed: int = 42,
    reset: bool = False,
    now: datetime | None = None,
) -> dict[str, int]:
    """Create the seed experiments with synthetic runs. Returns {experiment: runs_created}.

    Existing seed experiments are skipped (idempotent) unless `reset` is True, in which case
    they are deleted (with their runs and metrics) and regenerated.
    """
    rng = random.Random(seed)
    now = now or datetime.now(UTC).replace(microsecond=0)
    created: dict[str, int] = {}

    for profile in PROFILES:
        existing = await db.scalar(select(Experiment).where(Experiment.name == profile.name))
        if existing is not None:
            if not reset:
                created[profile.name] = 0
                continue
            # Bulk delete (FK cascade in SQLite) instead of loading every run into memory.
            await db.execute(delete(Experiment).where(Experiment.id == existing.id))
            await db.flush()

        experiment = Experiment(
            name=profile.name,
            description=profile.description,
            created_at=now - timedelta(days=3, hours=1),
        )
        experiment.runs = [
            r.to_orm() for r in generate_experiment_runs(rng, profile, runs_per_experiment, now)
        ]
        db.add(experiment)
        created[profile.name] = runs_per_experiment

    await db.commit()
    return created


async def _main(args: argparse.Namespace) -> None:
    from app.database import AsyncSessionLocal, engine, init_db

    await init_db()
    try:
        async with AsyncSessionLocal() as db:
            result = await seed_database(db, args.runs_per_experiment, args.seed, args.reset)
    finally:
        await engine.dispose()

    for name, count in result.items():
        if count:
            print(f"  + {name}: {count} runs")
        else:
            print(f"  = {name}: already exists, skipped (use --reset to regenerate)")
    print(f"Done. Database: {engine.url}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Seed synthetic ML runs for development.")
    p.add_argument("--runs-per-experiment", type=int, default=15, choices=range(1, 501),
                   metavar="N", help="runs per seed experiment (default 15, max 500)")  # fmt: skip
    p.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    p.add_argument("--reset", action="store_true", help="drop and regenerate seed experiments")
    asyncio.run(_main(p.parse_args(argv)))


if __name__ == "__main__":
    main()
