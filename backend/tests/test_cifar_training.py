"""CPU tests with synthetic fixtures; never download datasets or pretrained weights."""
# ruff: noqa: E402

import random
import subprocess
import sys

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torchvision")

from PIL import Image
from torch.utils.data import DataLoader, TensorDataset

from scripts.predict_cifar10 import predict
from training.data import CLASSES, MEAN, STD, local_dataset, split_manifest, transform
from training.engine import epoch, load_checkpoint, restore_rng, save_checkpoint, seed_all
from training.models import build_model


@pytest.fixture(autouse=True)
def small_cpu_pool():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def test_official_split_disjoint_stratified_reproducible():
    targets = [i for i in range(10) for _ in range(5000)]
    split = split_manifest(targets)
    assert split == split_manifest(targets)
    assert len(split["train_indices"]) == 45000
    assert len(split["validation_indices"]) == 5000
    assert not set(split["train_indices"]) & set(split["validation_indices"])
    assert set(split["train_indices"] + split["validation_indices"]) == set(range(50000))
    for label in range(10):
        assert sum(targets[i] == label for i in split["validation_indices"]) == 500
    assert split["split_id"] != split_manifest(targets, seed=1)["split_id"]


def test_local_missing_does_not_download(tmp_path, monkeypatch):
    from torchvision.datasets import CIFAR10

    monkeypatch.setattr(CIFAR10, "download", lambda _: pytest.fail("unexpected download"))
    with pytest.raises(RuntimeError, match="prepare_cifar10"):
        local_dataset(tmp_path, True)


def test_preprocessing_deterministic():
    image = Image.new("RGB", (50, 40), "red")
    first = transform()(image)
    assert first.shape == (3, 32, 32)
    assert torch.equal(first, transform()(image))


def test_weighted_metrics_and_eval_mode():
    class Identity(torch.nn.Module):
        def forward(self, values):
            assert not self.training
            return values

    logits = torch.tensor([[4.0, 0], [4.0, 0], [0, 4.0]])
    labels = torch.tensor([0, 0, 0])
    result = epoch(Identity(), DataLoader(TensorDataset(logits, labels), batch_size=2), "cpu")
    assert result["accuracy"] == pytest.approx(2 / 3)
    assert result["loss"] == pytest.approx(torch.nn.functional.cross_entropy(logits, labels).item())


def test_gradient_and_one_batch_overfit():
    seed_all(7)
    model = build_model()
    inputs = torch.randn(4, 3, 32, 32)
    labels = torch.tensor([0, 1, 2, 3])
    loader = DataLoader(TensorDataset(inputs, labels), batch_size=4)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    before = epoch(model, loader, "cpu")["loss"]
    for _ in range(60):
        epoch(model, loader, "cpu", optimizer)
    after = epoch(model, loader, "cpu")
    assert after["accuracy"] == 1
    assert after["loss"] < before * 0.1


def test_checkpoint_resume_rng_optimizer_and_prediction(tmp_path):
    seed_all(42)
    model = build_model()
    optimizer = torch.optim.Adam(model.parameters())
    inputs, labels = torch.randn(3, 3, 32, 32), torch.tensor([1, 2, 3])
    loader = DataLoader(TensorDataset(inputs, labels), batch_size=2)
    epoch(model, loader, "cpu", optimizer)
    generator = torch.Generator().manual_seed(42)
    config = {
        "architecture": "small-cnn",
        "classes": CLASSES,
        "preprocessing": {"mean": MEAN, "std": STD},
    }
    path = tmp_path / "last.pt"
    save_checkpoint(
        path, model, optimizer, config, 1, {"epoch": 1, "accuracy": 0.2}, [{"epoch": 1}], generator
    )
    expected_rng = (random.random(), np.random.rand(), torch.rand(1))
    epoch(model, loader, "cpu", optimizer)
    resumed, state = load_checkpoint(path)
    new_optimizer = torch.optim.Adam(resumed.parameters())
    new_optimizer.load_state_dict(state["optimizer"])
    restore_rng(state, generator)
    assert random.random() == expected_rng[0]
    assert np.random.rand() == expected_rng[1]
    assert torch.equal(torch.rand(1), expected_rng[2])
    epoch(resumed, loader, "cpu", new_optimizer)
    for key, value in model.state_dict().items():
        assert torch.equal(value, resumed.state_dict()[key])
    for mode in ("RGB", "L", "RGBA"):
        image = tmp_path / f"{mode}.png"
        Image.new(mode, (40, 40)).save(image)
        result = predict(path, image)
        assert result["label"] in CLASSES
        assert sum(result["probabilities"].values()) == pytest.approx(1)
    with pytest.raises(ValueError, match="Image"):
        predict(path, tmp_path / "missing.jpg")
    script = (
        __import__("pathlib").Path(__file__).resolve().parents[1] / "scripts/predict_cifar10.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), str(path), str(image)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_resnet_has_cifar_stem_and_no_download():
    model = build_model("resnet18")
    assert model.conv1.kernel_size == (3, 3)
    assert isinstance(model.maxpool, torch.nn.Identity)
    assert model(torch.randn(2, 3, 32, 32)).shape == (2, 10)
