from __future__ import annotations

import numpy as np
import pytest

from deep_hedge_price import pricing_benchmark
from deep_hedge_price.pricing_benchmark import (
    TEACHER_IMPORT_ERROR,
    benchmark_callable,
    benchmark_pricing_suite,
    calibration_recovery,
)


def test_benchmark_records_conditions_and_calibration_recovers_sigma():
    rows = np.array([[1.0, 1.0, 0.0, 0.0, 0.2], [1.1, 0.5, 0.01, 0.0, 0.3]])
    timing = benchmark_callable(lambda value: value[:, 0] ** 2, rows, warmup=1, repeats=3)
    assert (
        timing["batch_size"] == 2
        and timing["repeats"] == 3
        and timing["median_ms"] >= 0
        and timing["device"] == "cpu"
    )

    def price_fn(value):
        return value[:, 4] ** 2

    result = calibration_recovery(price_fn, rows, rows[:, 4] ** 2, bounds=(0.05, 0.8))
    assert result["volatility_mae"] < 1e-5


def test_pricing_suite_uses_common_conditions_and_seeded_teachers(monkeypatch):
    calls = {"heston": 0, "mc": []}

    def fake_heston(*args, **kwargs):
        calls["heston"] += 1
        return float(args[0])

    def fake_mc(rows, *, n_paths, seed, chunk_size):
        calls["mc"].append((len(rows), n_paths, seed, chunk_size))
        return {"price": np.asarray(rows)[:, 0]}

    monkeypatch.setattr(
        pricing_benchmark,
        "_load_hullkit_teachers",
        lambda: (fake_heston, fake_mc),
    )
    inputs = np.array(
        [
            [1.0, 1.0, 0.02, 0.01, 0.2],
            [0.9, 0.5, 0.01, 0.00, 0.3],
            [1.1, 0.2, 0.00, 0.02, 0.4],
        ]
    )
    result = benchmark_pricing_suite(
        inputs,
        polynomial_function=lambda rows: rows[:, 0],
        neural_function=lambda rows: rows[:, 0],
        batch_sizes=(1, 3),
        warmup=1,
        repeats=2,
        mc_seed=77,
        mc_paths=16,
        heston_cos_terms=8,
    )
    assert result["conditions"] == {
        "batch_sizes": [1, 3],
        "warmup": 1,
        "repeats": 2,
        "device": "cpu",
        "common_input_slices": True,
    }
    for name in ("analytic", "heston_cos", "monte_carlo", "polynomial", "neural"):
        assert [row["batch_size"] for row in result[name]] == [1, 3]
        assert all(row["warmup"] == 1 and row["repeats"] == 2 for row in result[name])
        assert all(row["device"] == "cpu" and row["method"] == name for row in result[name])
    assert set(calls["mc"]) == {(1, 16, 77, 16), (3, 16, 77, 16)}
    assert result["teacher_metadata"]["monte_carlo"]["seed"] == 77
    assert calls["heston"] > 0


def test_missing_hullkit_has_actionable_optional_integration_error(monkeypatch):
    def missing(_name):
        raise ModuleNotFoundError("hullkit")

    monkeypatch.setattr(pricing_benchmark.importlib, "import_module", missing)
    with pytest.raises(RuntimeError, match="hullkit is required") as exc_info:
        pricing_benchmark._load_hullkit_teachers()
    assert str(exc_info.value) == TEACHER_IMPORT_ERROR
