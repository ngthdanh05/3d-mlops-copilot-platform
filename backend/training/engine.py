"""Sample-weighted metrics and atomic, weights-only compatible checkpoints."""

import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.optim import Optimizer
from torch.utils.data import DataLoader

from training.models import build_model


def seed_all(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def epoch(
    model: nn.Module,
    loader: DataLoader,
    device: str | torch.device,
    optimizer: Optimizer | None = None,
    confusion: bool = False,
) -> dict[str, Any]:
    model.train(optimizer is not None)
    total, correct, loss_sum = 0, 0, 0.0
    matrix = torch.zeros(10, 10, dtype=torch.int64)
    with torch.set_grad_enabled(optimizer is not None):
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            if optimizer is not None:
                optimizer.zero_grad(set_to_none=True)
            logits = model(inputs)
            loss = nn.functional.cross_entropy(logits, labels)
            if not torch.isfinite(loss):
                raise RuntimeError("Non-finite loss")
            if optimizer is not None:
                loss.backward()
                optimizer.step()
            predicted = logits.argmax(1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            loss_sum += loss.item() * labels.size(0)
            if confusion:
                matrix += torch.bincount((labels * 10 + predicted).cpu(), minlength=100).view(
                    10, 10
                )
    if not total:
        raise ValueError("Empty dataset")
    result = {"accuracy": correct / total, "loss": loss_sum / total, "samples": total}
    if confusion:
        result["confusion_matrix"] = matrix.tolist()
        result["per_class"] = [
            {
                "class_index": i,
                "support": int(matrix[i].sum()),
                "recall": float(matrix[i, i] / matrix[i].sum()) if matrix[i].sum() else None,
                "precision": float(matrix[i, i] / matrix[:, i].sum())
                if matrix[:, i].sum()
                else None,
            }
            for i in range(10)
        ]
    return result


def save_checkpoint(
    path: str | Path,
    model: nn.Module,
    optimizer: Optimizer,
    config: dict[str, Any],
    epoch_number: int,
    best: dict[str, Any],
    history: list[dict[str, Any]],
    generator: torch.Generator,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    numpy_state = np.random.get_state()
    state = {
        "version": 1,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "config": config,
        "epoch": epoch_number,
        "best": best,
        "history": history,
        "torch_rng": torch.get_rng_state(),
        "python_rng": random.getstate(),
        "numpy_rng": [numpy_state[0], numpy_state[1].tolist(), *numpy_state[2:]],
        "loader_rng": generator.get_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }
    temporary = path.with_suffix(".tmp")
    torch.save(state, temporary)
    temporary.replace(path)


def load_checkpoint(
    path: str | Path, device: str | torch.device = "cpu"
) -> tuple[nn.Module, dict[str, Any]]:
    state = torch.load(path, map_location="cpu", weights_only=True)
    if state["version"] != 1:
        raise ValueError("Unsupported checkpoint version")
    model = build_model(state["config"]["architecture"])
    model.load_state_dict(state["model"])
    return model.to(device), state


def restore_rng(state: dict[str, Any], generator: torch.Generator) -> None:
    random.setstate(state["python_rng"])
    values = state["numpy_rng"]
    np.random.set_state((values[0], np.array(values[1], dtype=np.uint32), *values[2:]))
    torch.set_rng_state(state["torch_rng"])
    generator.set_state(state["loader_rng"])
    if state["cuda_rng"] and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["cuda_rng"])
