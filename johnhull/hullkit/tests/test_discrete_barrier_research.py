"""Behavioral tests for saved-weight replay and discrete study serving."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "research/RB-F05/discrete"


def _load(name):
    spec = importlib.util.spec_from_file_location("barrier_" + name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _network():
    return {
        "kind": "barrier_nn",
        "dml": True,
        "feature_mean": np.array([100.0, 0.0]),
        "feature_std": np.array([10.0, 1.0]),
        "price_mean": 2.0,
        "price_scale": 0.8,
        "delta_scale": 0.2,
        "layer0_weight": np.array([[0.2, 0.1], [-0.3, 0.4]]),
        "layer0_bias": np.array([0.1, -0.2]),
        "layer1_weight": np.array([[0.4, -0.1], [0.2, 0.3]]),
        "layer1_bias": np.array([0.05, -0.03]),
        "layer2_weight": np.array([[0.6, -0.5]]),
        "layer2_bias": np.array([0.02]),
    }


def test_replay_delta_differentiates_same_price():
    replay = _load("replay")
    x = np.array([[90.0, 0.25], [110.0, 2.0]])
    value = replay.predict_nn(_network(), x)
    high, low = x.copy(), x.copy()
    high[:, 0] += 1e-3
    low[:, 0] -= 1e-3
    bump = (
        replay.predict_nn(_network(), high)[:, 0] - replay.predict_nn(_network(), low)[:, 0]
    ) / 0.002
    np.testing.assert_allclose(value[:, 1], bump, rtol=2e-8, atol=1e-10)


def test_hermite_derivative_uses_same_price_and_log_time_blend():
    replay = _load("replay")
    spots = np.array([80.0, 100.0, 119.0])
    times = np.array([0.25, 1.0, 2.0])
    prices = np.array([0.001 * spots**2 + np.log(t) for t in times])
    deltas = np.tile(0.002 * spots, (3, 1))
    surface = replay.HermiteSurface(spots, times, prices, deltas)
    x = np.array([[90.0, 0.5], [115.0, 1.5]])
    actual = surface(x)
    np.testing.assert_allclose(actual[:, 0], 0.001 * x[:, 0] ** 2 + np.log(x[:, 1]), atol=1e-12)
    np.testing.assert_allclose(actual[:, 1], 0.002 * x[:, 0], atol=1e-12)
    high, low = x.copy(), x.copy()
    high[:, 0] += 0.001
    low[:, 0] -= 0.001
    np.testing.assert_allclose(
        actual[:, 1], (surface(high)[:, 0] - surface(low)[:, 0]) / 0.002, atol=1e-10
    )


def test_safe_policy_retains_jump_undefined_delta_and_routes_ood():
    replay = _load("replay")
    x = np.array([[100.0, 1.0], [70.0, 0.1], [120.0, 1.0], [121.0, 1.0], [-1.0, 1.0]])
    calls = []

    def oracle(rows):
        calls.extend(rows.tolist())
        return np.tile([1.2, -0.1], (len(rows), 1))

    def approximate(rows):
        return np.tile([2.0, -0.2], (len(rows), 1))

    result = replay.serve(approximate, x, oracle)
    assert result["status"].tolist() == [
        "approximation",
        "fallback",
        "delta_undefined",
        "knocked_out",
        "invalid",
    ]
    np.testing.assert_allclose(result["prediction"][:2], [[2.0, -0.2], [1.2, -0.1]])
    assert result["prediction"][2, 0] == 0 and np.isnan(result["prediction"][2, 1])
    np.testing.assert_allclose(result["prediction"][3], [0.0, 0.0])
    assert calls == [[70.0, 0.1]]
    assert np.isnan(result["prediction"][4]).all()


def test_safe_price_violation_falls_back_instead_of_clipping():
    replay = _load("replay")
    x = np.array([[100.0, 1.0], [115.0, 1.0]])

    def approximate(rows):
        return np.array([[-0.01, 1.0], [21.0, -1.0]])

    result = replay.serve(approximate, x, lambda rows: np.tile([1.0, -0.2], (len(rows), 1)))
    assert result["status"].tolist() == ["fallback", "fallback"]
    np.testing.assert_allclose(result["prediction"], [[1.0, -0.2], [1.0, -0.2]])


def test_changed_contract_is_unsupported():
    replay = _load("replay")

    def forbidden(rows):
        raise AssertionError("unsupported contract must not invoke learned model/oracle")

    result = replay.serve(
        forbidden, np.array([[100.0, 1.0]]), forbidden, contract={"barrier": 121.0}
    )
    assert result["status"].tolist() == ["unsupported"]
    assert np.isnan(result["prediction"]).all()


def test_metrics_are_physical_and_zero_se_is_explicit():
    replay = _load("replay")
    target = np.zeros((2, 2))
    actual = np.array([[3.0, 4.0], [0.0, 0.0]])
    scores = replay.metrics(actual, target)
    assert scores["price_rmse"] == pytest.approx(3 / np.sqrt(2))
    assert scores["delta_rmse"] == pytest.approx(4 / np.sqrt(2))


@pytest.mark.parametrize("bad_price", [-0.01, 21.0])
def test_invalid_oracle_price_is_failure_not_successful_fallback(bad_price):
    replay = _load("replay")

    def forbidden(rows):
        raise AssertionError("OOD must bypass approximate model")

    actual = replay.serve(
        forbidden, np.array([[70.0, 1.0]]), lambda rows: np.array([[bad_price, 0.1]])
    )
    assert actual["status"].tolist() == ["oracle_failure"]
    assert np.isnan(actual["prediction"]).all()
