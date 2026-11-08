"""Random-search configuration of scripts/train_mnist_demo.py."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture
def trainer(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    return importlib.import_module("train_mnist_demo")


def test_same_seed_gives_same_configs(trainer):
    assert trainer.random_search(10, seed=7) == trainer.random_search(10, seed=7)
    assert trainer.random_search(10, seed=7) != trainer.random_search(10, seed=8)


def test_samples_stay_in_the_search_space(trainer):
    sampled = trainer.random_search(50, seed=1)[:50]
    assert all(1e-4 <= cfg.learning_rate <= 1e-1 for cfg in sampled)
    assert {cfg.batch_size for cfg in sampled} == set(trainer.SEARCH_BATCH_SIZES)
    assert {cfg.alpha for cfg in sampled} == set(trainer.SEARCH_ALPHAS)
    assert {cfg.epochs for cfg in sampled} == {trainer.SEARCH_EPOCHS}


def test_includes_deliberately_bad_runs(trainer):
    extras = trainer.random_search(5, seed=1)[5:]
    assert len(extras) == 5
    assert sum(cfg.train_size == 200 and cfg.alpha == 0.0 for cfg in extras) == 3
    assert sum(cfg.learning_rate >= 0.5 for cfg in extras) == 2


class StubClient:
    def __init__(self, existing_runs):
        self.existing_runs = existing_runs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def check_health(self):
        return None

    def ensure_experiment(self, name, description=None):
        return {"id": 1, "name": name}

    def list_runs(self, experiment_id=None):
        return self.existing_runs


def run_search(trainer, monkeypatch, existing_runs) -> list:
    trained = []
    monkeypatch.setattr(trainer, "TrackingClient", lambda url: StubClient(existing_runs))
    data = SimpleNamespace(x_train=[], x_val=[])
    monkeypatch.setattr(trainer, "load_dataset", lambda *args: data)
    monkeypatch.setattr(trainer, "train_and_log", lambda *args, **kw: trained.append(args[2]))
    assert trainer.main(["--random-search", "3"]) == 0
    return trained


def test_search_trains_every_config_on_a_new_experiment(trainer, monkeypatch):
    assert len(run_search(trainer, monkeypatch, existing_runs=[])) == 8


def test_search_does_not_duplicate_an_existing_experiment(trainer, monkeypatch):
    existing = [
        {
            "run_name": "run-001",
            "status": "completed",
            "final_epoch": 1,
            "final_accuracy": 0.5,
        }
    ]
    assert run_search(trainer, monkeypatch, existing_runs=existing) == []
