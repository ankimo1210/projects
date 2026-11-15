"""Protect split isolation, model sizing and held-out evaluation semantics."""

import numpy as np
import pytest
import torch
from nn_textbook import scale_experiment as scale


def fixture_data():
    rng = np.random.default_rng(7)
    images = torch.tensor(rng.uniform(0, 255, (60, 2, 2)), dtype=torch.uint8)
    labels = torch.arange(60) % 3
    test_images = torch.tensor(rng.uniform(0, 255, (15, 2, 2)), dtype=torch.uint8)
    return scale.prepare_data(
        images, labels, test_images, torch.arange(15) % 3, validation_per_class=4, split_seed=42
    )


def test_split_is_disjoint_stratified_and_training_normalized():
    data = fixture_data()
    assert len(data.train.x) == 48 and len(data.validation.x) == 12
    assert set(data.train.ids).isdisjoint(data.validation.ids)
    assert np.bincount(data.validation.y.numpy()).tolist() == [4, 4, 4]
    assert abs(data.train.x.mean().item()) < 1e-6
    assert abs(data.train.x.std(unbiased=False).item() - 1) < 1e-6
    assert data.fingerprint == fixture_data().fingerprint


def test_all_declared_parameter_counts_match_real_modules():
    expected = [7850, 12730, 118282, 932362, 14217226]
    actual = [scale.parameter_count(scale.make_model(spec["hidden"])) for spec in scale.MODELS]
    assert actual == expected


def test_evaluation_reconciles_confusion_and_restores_training_mode():
    model = scale.make_model([], input_features=4, n_classes=3)
    model.train()
    result = scale.evaluate(model, fixture_data().test, batch_size=7)
    assert result["n"] == 15
    assert sum(map(sum, result["confusion"])) == 15
    assert sum(result["confusion"][i][i] for i in range(3)) == result["correct"]
    assert result["accuracy"] == result["correct"] / 15
    assert model.training


def test_checkpoint_is_validation_selected_and_test_is_used_only_once(monkeypatch):
    calls = []
    real_evaluate = scale.evaluate

    def watched(model, data, **kwargs):
        calls.append(data.name)
        return real_evaluate(model, data, **kwargs)

    monkeypatch.setattr(scale, "evaluate", watched)
    result = scale.train_run(
        fixture_data(),
        {"id": "fixture", "hidden": [8]},
        seed=11,
        epochs=3,
        batch_size=12,
        device="cpu",
    )
    assert calls.count("test") == 1 and calls[-1] == "test"
    best = min(result["history"][1:], key=lambda row: row["validation"]["loss"])
    assert result["best_epoch"] == best["epoch"]
    assert result["test"]["n"] == 15
    assert result["fit_seconds"] > 0


def test_test_values_cannot_change_training_history():
    a, b = fixture_data(), fixture_data()
    b.test.x.fill_(100)
    b.test.y[:] = (b.test.y + 1) % 3
    spec = {"id": "fixture", "hidden": [8]}
    ra = scale.train_run(a, spec, seed=9, epochs=2, batch_size=12, device="cpu")
    rb = scale.train_run(b, spec, seed=9, epochs=2, batch_size=12, device="cpu")
    assert ra["best_epoch"] == rb["best_epoch"]
    for ha, hb in zip(ra["history"], rb["history"], strict=True):
        assert ha["train"] == hb["train"]
        assert ha["validation"] == hb["validation"]


def test_aggregation_retains_seed_variation_and_means():
    runs = [
        dict(model_id="a", test={"accuracy": v}, fit_seconds=t, peak_allocated_bytes=100)
        for v, t in [(0.8, 2), (0.9, 4), (1, 6)]
    ]
    row = scale.aggregate(runs)[0]
    assert row["test_accuracy_mean"] == pytest.approx(0.9)
    assert row["test_accuracy_std"] == pytest.approx(0.1)
    assert row["fit_seconds_mean"] == 4
