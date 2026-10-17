import importlib.util
from pathlib import Path

import numpy as np
import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research/2026-10-jgb-term-premium"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"tp_{name}", RESEARCH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gates():
    return _load("gates")


def _report(**overrides):
    report = {
        "g1": {m: {"pass": True} for m in ("acm", "acm_bc", "dns", "shadow")},
        "g2": {"pass": True},
        "g3": {"pass": True},
        "g4": {"pass": True},
    }
    report.update(overrides)
    return report


def test_all_gates_pass_all_models(gates):
    assert gates.passed_models(_report()) == ["acm", "acm_bc", "shadow", "dns"]


def test_g2_failure_removes_both_acm_variants(gates):
    assert gates.passed_models(_report(g2={"pass": False})) == ["shadow", "dns"]


def test_g3_failure_removes_the_shadow_model(gates):
    assert gates.passed_models(_report(g3={"pass": False})) == ["acm", "acm_bc", "dns"]


def test_a_data_failure_stops_everything(gates):
    assert gates.passed_models(_report(g4={"pass": False})) == []


def test_g1_summary_uses_the_mean_error_and_the_median_rmse(gates):
    draws = [
        {"share_error": e, "tp_rmse": r} for e, r in ((0.08, 0.05), (-0.06, 0.12), (0.02, 0.30))
    ]
    out = gates._summary(draws)
    assert out["mean_share_error"] == pytest.approx(0.04 / 3)
    assert out["median_tp_rmse"] == pytest.approx(0.12)
    assert out["pass"]
    assert not gates._summary([{"share_error": 0.06, "tp_rmse": 0.05}] * 3)["pass"]
    assert not gates._summary([{"share_error": 0.0, "tp_rmse": 0.16}] * 3)["pass"]


def test_g1_draws_use_distinct_fixed_seeds(gates):
    first = gates._rng(1, 0).standard_normal(3)
    np.testing.assert_array_equal(first, gates._rng(1, 0).standard_normal(3))
    assert not np.allclose(first, gates._rng(1, 1).standard_normal(3))
    assert not np.allclose(first, gates._rng(2, 0).standard_normal(3))
    assert not np.allclose(first, gates._rng(1, 0, 1).standard_normal(3))
