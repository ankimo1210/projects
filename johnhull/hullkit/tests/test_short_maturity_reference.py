"""Physical Greeks, C2 spot interpolation and honest short-study accounting."""

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

DIR = Path(__file__).resolve().parents[2] / "research/RB-F05/short_maturity"


def module(name):
    spec = importlib.util.spec_from_file_location("short_test_" + name, DIR / (name + ".py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def p():
    return module("protocol").candidate_protocol()


def test_clock_and_expiry_route(p):
    a = module("analytics")
    x = np.array([[100, 60, 1], [100, 1800, 0], [99, 0, 1], [100, 0, 1]])
    states = a.states(x, p)
    assert states[0].jump_mean_count == pytest.approx(0.028 / 30)
    assert states[0].carry_years == pytest.approx(60 / (365 * 86400))
    result = a.oracle(x, p)
    assert result.shape == (4, 3)
    assert result[2] == pytest.approx([0, 0, 0])
    assert result[3, 0] == pytest.approx(0)
    assert np.isnan(result[3, 1:]).all()


def polynomial_grid():
    # Independent polynomial in log spot, affine in log seconds.
    xs = np.linspace(-0.08, 0.08, 5)
    seconds = np.array([60.0, 600.0, 23400.0])
    values = np.empty((2, 3, 5, 3))
    for e in [0, 1]:
        for j, t in enumerate(seconds):
            z = np.log(t)
            values[e, j, :, 0] = 5 + e + 0.1 * z + 2 * xs + 3 * xs**2 + 4 * xs**3
            values[e, j, :, 1] = 2 + 6 * xs + 12 * xs**2
            values[e, j, :, 2] = 6 + 24 * xs
    return {"log_spot_nodes": xs, "seconds_nodes": seconds, "derivatives": values}


def test_quintic_same_price_physical_delta_gamma(p):
    a = module("analytics")
    grid = polynomial_grid()
    x = np.array([[100 * np.exp(0.017), 300.0, 1], [100 * np.exp(-0.04), 20000.0, 0]])
    got = a.hermite_predict(grid, x, p)
    logx = np.log(x[:, 0] / 100)
    c = 5 + x[:, 2] + 0.1 * np.log(x[:, 1]) + 2 * logx + 3 * logx**2 + 4 * logx**3
    cx = 2 + 6 * logx + 12 * logx**2
    cxx = 6 + 24 * logx
    expected = np.column_stack([c, cx / x[:, 0], (cxx - cx) / x[:, 0] ** 2])
    assert np.allclose(got, expected, atol=1e-12, rtol=1e-10)
    for node in grid["log_spot_nodes"][1:-1]:
        inputs = [[100 * np.exp(node + d), 600.0, 0] for d in [-1e-9, 0, 1e-9]]
        assert np.ptp(a.hermite_predict(grid, inputs, p)[:, 2]) < 1e-9


def test_real_hermite_nodes_and_bumps(p):
    a = module("analytics")
    grid = a.build_hermite(p)
    mid = len(grid["seconds_nodes"]) // 2
    spot = 100 * np.exp(grid["log_spot_nodes"][25])
    x = np.array([[spot, grid["seconds_nodes"][mid], 1]])
    assert a.hermite_predict(grid, x, p) == pytest.approx(a.oracle(x, p), rel=1e-9, abs=1e-10)
    h = 0.001
    vals = a.hermite_predict(grid, [[spot - h, x[0, 1], 1], x[0], [spot + h, x[0, 1], 1]], p)
    assert vals[1, 1] == pytest.approx((vals[2, 0] - vals[0, 0]) / (2 * h), rel=1e-5)
    assert vals[1, 2] == pytest.approx(
        (vals[2, 0] - 2 * vals[1, 0] + vals[0, 0]) / h**2, rel=1e-4, abs=1e-7
    )


def test_safe_preserves_raw_and_undefined_original_roster(p):
    a = module("analytics")
    inputs = np.array([[100, 60, 1], [101, 30, 0], [100, 0, 1], [99, -1, 0]])
    raw = np.array([[-1.0, 1.5, -0.1], [1, 0.5, 0.1], [0, 0.5, 0], [0, 0, 0]])
    original = raw.copy()
    r = a.safe_route(raw, inputs, p)
    assert np.array_equal(raw, original)
    assert r["routes"].tolist() == [
        "fallback_bound",
        "fallback_time",
        "expiry_undefined_atm",
        "invalid_contract",
    ]
    assert np.isnan(r["values"][2, 1:]).all()
    assert np.isnan(r["values"][3]).all()
    assert r["original_count"] == 4


def test_metric_failure_cannot_shrink_denominator():
    a = module("analytics")
    pred = np.array([[1, 0.5, 0.1], [np.nan, 0.2, 0]])
    ref = np.zeros_like(pred)
    r = a.error_summary(pred, ref, strike=100)
    assert r["original_count"] == 2 and r["failed_rows"] == 1
    assert r["status"] == "nonfinite"
    assert r["rmse"] is None
    good = a.error_summary(pred[:1], ref[:1], strike=100)
    assert good["rmse"] == pytest.approx([1, 0.5, 10])


def test_expenses_reject_duplicate_and_nested_double_charge():
    a = module("analytics")
    expenses = [
        {"id": "common", "category": "teacher", "seconds": 0.4, "charged": True},
        {"id": "fit", "category": "train", "seconds": 0.6, "charged": True},
        {
            "id": "train-loop",
            "category": "detail",
            "seconds": 0.5,
            "charged": False,
            "parent": "fit",
        },
        {"id": "pending", "category": "startup", "seconds": None, "charged": True},
    ]
    totals = a.expense_totals(expenses)
    assert totals["measured_seconds"] == pytest.approx(1)
    assert totals["pending_ids"] == ["pending"]
    with pytest.raises(ValueError, match="duplicate"):
        a.expense_totals([*expenses, expenses[0]])
    with pytest.raises(ValueError, match="nested"):
        a.expense_totals(
            [
                *expenses,
                {"id": "double", "category": "x", "seconds": 0.1, "charged": True, "parent": "fit"},
            ]
        )


def test_break_even_zero_negative_online_savings():
    a = module("analytics")
    assert a.break_even(10, 2, 0.1, 0.1)["queries"] is None
    assert a.break_even(10, 2, 0.2, 0.1)["queries"] is None
    assert a.break_even(10, 2, 0.1, 0.2)["queries"] == pytest.approx(80)


def test_hermite_exact_time_endpoints_have_distinct_log_nodes(p):
    a = module("analytics")
    g = a.build_hermite(p)
    assert np.all(np.diff(np.log(g["seconds_nodes"])) > 0)
    x = np.array([[100.0, 60.0, 0], [100.0, 60.0, 1], [100.0, 23400.0, 0], [100.0, 23400.0, 1]])
    got = a.hermite_predict(g, x, p)
    assert np.isfinite(got).all()
    assert np.allclose(got, a.oracle(x, p), rtol=1e-9, atol=1e-10)


def test_cost_all_ancestors_and_invalid_parent_graph():
    a = module("analytics")
    chain = [
        {"id": "pipeline", "category": "all", "seconds": 10.0, "charged": True},
        {
            "id": "setup",
            "category": "setup",
            "seconds": 8.0,
            "charged": False,
            "parent": "pipeline",
        },
        {
            "id": "teacher",
            "category": "teacher",
            "seconds": 4.0,
            "charged": True,
            "parent": "setup",
        },
    ]
    with pytest.raises(ValueError, match="nested"):
        a.expense_totals(chain)
    with pytest.raises(ValueError, match="parent"):
        a.expense_totals(
            [{"id": "x", "category": "x", "seconds": 1.0, "charged": False, "parent": "missing"}]
        )
    with pytest.raises(ValueError, match="cycle"):
        a.expense_totals(
            [
                {"id": "a", "category": "x", "seconds": 1.0, "charged": False, "parent": "b"},
                {"id": "b", "category": "x", "seconds": 1.0, "charged": False, "parent": "a"},
            ]
        )


def test_finite_huge_errors_stay_finite_and_overflow_keeps_roster():
    a = module("analytics")
    r = a.error_summary([[1e200, 0.5, 0.1]], [[0, 0, 0]], strike=100)
    assert np.isfinite(r["rmse"]).all()
    assert r["rmse"] == pytest.approx([1e200, 0.5, 10])
    r = a.error_summary([[1e308, 0, 0]], [[-1e308, 0, 0]], strike=100)
    assert r["status"] == "nonfinite" and r["failed_rows"] == 1
    assert r["original_count"] == 1 and r["rmse"] is None
    with pytest.raises(ValueError, match="strike"):
        a.error_summary([[0, 0, 0]], [[0, 0, 0]], strike=np.inf)


def test_safe_forward_lower_bound_preserves_raw(p):
    a = module("analytics")
    x = np.array([[105.0, 60.0, 0], [105.0, 60.0, 1]])
    raw = np.array([[0.0, 0.5, 0.0], [0.0, 0.5, 0.0]])
    r = a.safe_route(raw, x, p)
    assert r["routes"].tolist() == ["fallback_bound", "fallback_bound"]
    lower = x[:, 0] - 100 * np.exp(-0.03 * 60 / (365 * 86400))
    assert np.all(r["values"][:, 0] >= lower - 1e-12)
    assert np.array_equal(raw, [[0.0, 0.5, 0.0], [0.0, 0.5, 0.0]])
