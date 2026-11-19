"""Versioned stratified split and identical evaluation/inference preprocessing."""

import hashlib
import json
import random
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

BACKEND = Path(__file__).resolve().parents[1]
CLASSES = ["airplane", "automobile", "bird", "cat", "deer", "dog", "frog", "horse", "ship", "truck"]
# Common CIFAR-10 channel statistics, recorded explicitly in every manifest.
MEAN = [0.4914, 0.4822, 0.4465]
STD = [0.2470, 0.2435, 0.2616]


def resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else BACKEND / path


def atomic_json(path: str | Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def split_manifest(
    targets: Sequence[int],
    seed: int = 42,
    validation_per_class: int = 500,
    data: np.ndarray | None = None,
) -> dict[str, Any]:
    rng = random.Random(seed)
    train, val = [], []
    for label in range(10):
        indices = [i for i, target in enumerate(targets) if target == label]
        if len(indices) <= validation_per_class:
            raise ValueError("Insufficient samples per class")
        rng.shuffle(indices)
        val.extend(indices[:validation_per_class])
        train.extend(indices[validation_per_class:])
    mean, std = MEAN, STD
    if data is not None:
        # Streaming moments over train indices only; no validation/test leakage and
        # no full-dataset float32 allocation on a 16 GB Windows machine.
        sums, squares, pixels = np.zeros(3), np.zeros(3), 0
        for offset in range(0, len(train), 128):
            batch = data[train[offset : offset + 128]].astype(np.float64) / 255
            sums += batch.sum(axis=(0, 1, 2))
            squares += (batch * batch).sum(axis=(0, 1, 2))
            pixels += batch.shape[0] * batch.shape[1] * batch.shape[2]
        mean = (sums / pixels).tolist()
        std = np.sqrt(squares / pixels - np.square(mean)).tolist()
    value = {
        "version": 1,
        "dataset": "torchvision:CIFAR10:python-v1",
        "seed": seed,
        "classes": CLASSES,
        "train_indices": sorted(train),
        "validation_indices": sorted(val),
        "test_namespace": "official-test",
        "test_indices": list(range(10000)),
        "preprocessing": {
            "mean": mean,
            "std": std,
            "size": [32, 32],
            "source": "channel moments from deterministic training split only"
            if data is not None
            else "fixture defaults; production preparation computes train moments",
        },
    }
    value["split_id"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def transform(
    augment: bool = False, preprocessing: dict[str, Any] | None = None
) -> transforms.Compose:
    config = preprocessing or {"mean": MEAN, "std": STD}
    steps = [transforms.Resize((32, 32))]
    if augment:
        steps += [transforms.RandomCrop(32, padding=4), transforms.RandomHorizontalFlip()]
    return transforms.Compose(
        steps + [transforms.ToTensor(), transforms.Normalize(config["mean"], config["std"])]
    )


def local_dataset(
    root: str | Path,
    train: bool,
    augment: bool = False,
    preprocessing: dict[str, Any] | None = None,
) -> datasets.CIFAR10:
    root = resolve(root)
    try:
        return datasets.CIFAR10(
            str(root), train=train, transform=transform(augment, preprocessing), download=False
        )
    except RuntimeError as exc:
        raise RuntimeError(
            f"CIFAR-10 missing/corrupt at {root}. Run scripts/prepare_cifar10.py "
            "online first; offline commands never download."
        ) from exc


def load_split(root: str | Path, seed: int = 42) -> dict[str, Any]:
    root = resolve(root)
    train = local_dataset(root, True)
    local_dataset(root, False)
    path = root / f"split-{seed}.json"
    if not path.exists():
        raise RuntimeError(f"Missing {path}; run prepare_cifar10.py --seed {seed}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = split_manifest(train.targets, seed, data=train.data)
    if manifest != expected:
        raise ValueError("Split manifest differs from the versioned deterministic split")
    return manifest


def seed_worker(_worker_id: int) -> None:
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def loaders(
    root: str | Path,
    manifest: dict[str, Any],
    batch_size: int = 32,
    workers: int = 0,
    seed: int = 42,
    subset: int | None = None,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    generator = torch.Generator().manual_seed(seed)
    indices = manifest["train_indices"]
    val_indices = manifest["validation_indices"]
    if subset:
        indices, val_indices = indices[:subset], val_indices[:subset]
    common = {
        "batch_size": batch_size,
        "num_workers": workers,
        "worker_init_fn": seed_worker,
        "drop_last": False,
    }
    preprocessing = manifest["preprocessing"]
    training = DataLoader(
        Subset(local_dataset(root, True, True, preprocessing), indices),
        shuffle=True,
        generator=generator,
        **common,
    )
    evaluation = DataLoader(
        Subset(local_dataset(root, True, preprocessing=preprocessing), indices), **common
    )
    validation = DataLoader(
        Subset(local_dataset(root, True, preprocessing=preprocessing), val_indices), **common
    )
    return training, evaluation, validation
