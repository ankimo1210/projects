"""Tests for hullkit.pnl_explain: factor exposures, delta-gamma-vega P&L,
attribution, limit utilization, and the desk report assembler."""

from __future__ import annotations

import itertools
import json
import math

import numpy as np
import pytest
from hullkit import bsm, pnl_explain, var_backtest

# --- aggregate_exposures -------------------------------------------------


def test_aggregate_exposures_basic():
    weights = np.array([2.0, -1.0])
    deltas = np.array([[50.0, 20.0], [10.0, 5.0]])
    gammas = np.array([[1.0, 0.5], [0.2, 0.1]])
    vegas = np.array([[3.0, 1.0], [0.5, 0.2]])

    delta_p, gamma_p, vega_p = pnl_explain.aggregate_exposures(weights, deltas, gammas, vegas)

    assert delta_p == pytest.approx(weights @ deltas, abs=1e-12)
    assert gamma_p == pytest.approx(weights @ gammas, abs=1e-12)
    assert vega_p == pytest.approx(weights @ vegas, abs=1e-12)


def test_aggregate_exposures_shape_mismatch_raises():
    weights = np.array([1.0, 1.0])
    deltas = np.array([[1.0, 2.0], [3.0, 4.0]])
    gammas = np.array([[1.0, 2.0], [3.0, 4.0]])
    vegas = np.array([[1.0, 2.0], [3.0, 4.0]])

    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures(weights[:-1], deltas, gammas, vegas)
    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures(weights, deltas[:, :-1], gammas, vegas)
    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures(weights, deltas, gammas[:, :-1], vegas)
    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures(weights, deltas, gammas, vegas[:1, :])


def test_aggregate_exposures_empty_raises():
    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures([], np.empty((0, 2)), np.empty((0, 2)), np.empty((0, 2)))


def test_aggregate_exposures_non_finite_raises():
    weights = np.array([1.0, math.nan])
    deltas = np.array([[1.0, 2.0], [3.0, 4.0]])
    gammas = np.array([[1.0, 2.0], [3.0, 4.0]])
    vegas = np.array([[1.0, 2.0], [3.0, 4.0]])
    with pytest.raises(ValueError):
        pnl_explain.aggregate_exposures(weights, deltas, gammas, vegas)


# --- delta_gamma_vega_pnl -------------------------------------------------


def test_delta_gamma_vega_pnl_basic():
    delta_p = np.array([10.0, -5.0])
    gamma_p = np.array([2.0, 1.0])
    vega_p = np.array([3.0, 0.5])
    dx = np.array([0.5, -0.2])
    dvol = np.array([0.01, -0.02])

    result = pnl_explain.delta_gamma_vega_pnl(delta_p, gamma_p, vega_p, dx, dvol)

    expected_delta = float(delta_p @ dx)
    expected_gamma = float(0.5 * gamma_p @ dx**2)
    expected_vega = float(vega_p @ dvol)
    assert result["delta"] == pytest.approx(expected_delta, abs=1e-12)
    assert result["gamma"] == pytest.approx(expected_gamma, abs=1e-12)
    assert result["vega"] == pytest.approx(expected_vega, abs=1e-12)
    assert result["total"] == pytest.approx(
        expected_delta + expected_gamma + expected_vega, abs=1e-12
    )
    assert isinstance(result["total"], float)


def test_delta_gamma_vega_pnl_shape_mismatch_raises():
    delta_p = np.array([10.0, -5.0])
    with pytest.raises(ValueError):
        pnl_explain.delta_gamma_vega_pnl(delta_p, [2.0], [3.0, 0.5], [0.1, 0.1], [0.01, 0.01])
    with pytest.raises(ValueError):
        pnl_explain.delta_gamma_vega_pnl(delta_p, [2.0, 1.0], [3.0, 0.5], [0.1], [0.01, 0.01])
    with pytest.raises(ValueError):
        pnl_explain.delta_gamma_vega_pnl(delta_p, [2.0, 1.0], [3.0, 0.5], [0.1, 0.1], [0.01])


def test_delta_gamma_vega_pnl_non_finite_raises():
    with pytest.raises(ValueError):
        pnl_explain.delta_gamma_vega_pnl([math.inf], [1.0], [1.0], [0.1], [0.01])


def test_delta_gamma_vega_pnl_empty_raises():
    with pytest.raises(ValueError):
        pnl_explain.delta_gamma_vega_pnl([], [], [], [], [])


# --- pnl_attribution -------------------------------------------------------


def test_pnl_attribution_basic():
    result = pnl_explain.pnl_attribution(full_pnl=105.0, explained_total=100.0)
    assert result["explained"] == pytest.approx(100.0, abs=1e-12)
    assert result["unexplained"] == pytest.approx(5.0, abs=1e-12)
    assert result["unexplained_share"] == pytest.approx(5.0 / 105.0, abs=1e-12)


def test_pnl_attribution_unexplained_share_floor_at_zero_full_pnl():
    result = pnl_explain.pnl_attribution(full_pnl=0.0, explained_total=0.0002)
    assert result["unexplained"] == pytest.approx(-0.0002, abs=1e-12)
    # denominator floored at 1e-12 so the ratio stays finite and well-defined.
    assert result["unexplained_share"] == pytest.approx(0.0002 / 1e-12, rel=1e-9)


def test_pnl_attribution_non_finite_raises():
    with pytest.raises(ValueError):
        pnl_explain.pnl_attribution(full_pnl=math.nan, explained_total=1.0)
    with pytest.raises(ValueError):
        pnl_explain.pnl_attribution(full_pnl=1.0, explained_total=math.inf)


# --- limit_utilization ------------------------------------------------------


def test_limit_utilization_basic():
    measures = np.array([80.0, 120.0, 50.0])
    limits = np.array([100.0, 100.0, 100.0])
    result = pnl_explain.limit_utilization(measures, limits)
    assert np.allclose(result["utilization"], [0.8, 1.2, 0.5])
    assert list(result["breached"]) == [False, True, False]


def test_limit_utilization_non_positive_limit_raises():
    with pytest.raises(ValueError):
        pnl_explain.limit_utilization([50.0, 50.0], [100.0, 0.0])
    with pytest.raises(ValueError):
        pnl_explain.limit_utilization([50.0, 50.0], [100.0, -1.0])


def test_limit_utilization_shape_mismatch_raises():
    with pytest.raises(ValueError):
        pnl_explain.limit_utilization([50.0, 50.0], [100.0])


def test_limit_utilization_empty_raises():
    with pytest.raises(ValueError):
        pnl_explain.limit_utilization([], [])


def test_limit_utilization_non_finite_raises():
    with pytest.raises(ValueError):
        pnl_explain.limit_utilization([math.nan], [100.0])


# --- Validation: linear book ------------------------------------------------


def test_linear_book_delta_explain_matches_full_revaluation():
    # A purely linear (gamma = vega = 0) book: full revaluation of
    # weights @ deltas @ dx equals the delta-only explain to 1e-12.
    weights = np.array([2.0, -1.0, 0.5])
    deltas = np.array([[40.0, -10.0], [15.0, 5.0], [-8.0, 12.0]])
    zeros = np.zeros_like(deltas)

    delta_p, gamma_p, vega_p = pnl_explain.aggregate_exposures(weights, deltas, zeros, zeros)
    dx = np.array([0.03, -0.02])
    dvol = np.array([0.0, 0.0])

    full_pnl = float(weights @ (deltas @ dx))
    result = pnl_explain.delta_gamma_vega_pnl(delta_p, gamma_p, vega_p, dx, dvol)

    assert result["gamma"] == pytest.approx(0.0, abs=1e-12)
    assert result["vega"] == pytest.approx(0.0, abs=1e-12)
    assert result["total"] == pytest.approx(full_pnl, abs=1e-12)

    attribution = pnl_explain.pnl_attribution(full_pnl, result["total"])
    assert attribution["unexplained"] == pytest.approx(0.0, abs=1e-12)


# --- Validation: pure quadratic payoff ---------------------------------------


def test_pure_quadratic_payoff_delta_gamma_exact():
    # V(x1, x2) = a + b . x + 0.5 * (c1 x1^2 + c2 x2^2), no cross term:
    # the Taylor expansion of a diagonal-quadratic payoff about any point
    # is exact, so delta+gamma must match full revaluation to 1e-12.
    a = 1_000.0
    b = np.array([25.0, -12.0])
    c = np.array([4.0, 9.0])
    x0 = np.array([2.0, -1.0])
    dx = np.array([0.7, -1.3])

    def payoff(x):
        return a + b @ x + 0.5 * np.sum(c * x**2)

    full_pnl = payoff(x0 + dx) - payoff(x0)

    delta_p = b + c * x0  # local delta at x0 for the diagonal quadratic
    gamma_p = c
    vega_p = np.zeros_like(c)
    dvol = np.zeros_like(c)

    result = pnl_explain.delta_gamma_vega_pnl(delta_p, gamma_p, vega_p, dx, dvol)
    assert result["total"] == pytest.approx(full_pnl, abs=1e-12)


# --- Validation: BSM full revaluation, Taylor-order shrinkage ---------------


def test_bsm_taylor_dgv_residual_smaller_than_delta_only_and_shrinks_quadratically():
    S, K, r, sigma, T = 100.0, 105.0, 0.03, 0.25, 0.75
    delta = float(bsm.call_delta(S, K, r, sigma, T))
    gam = float(bsm.gamma(S, K, r, sigma, T))
    veg = float(bsm.vega(S, K, r, sigma, T))
    base_price = float(bsm.call_price(S, K, r, sigma, T))

    dS0, dsigma0 = 3.0, 0.015
    halvings = [0.5, 0.25, 0.125, 0.0625]
    dgv_residuals = []

    for h in halvings:
        dS = dS0 * h
        dsigma = dsigma0 * h
        full_pnl = float(bsm.call_price(S + dS, K, r, sigma + dsigma, T)) - base_price
        delta_only = delta * dS
        dgv_total = pnl_explain.delta_gamma_vega_pnl([delta], [gam], [veg], [dS], [dsigma])["total"]

        res_delta_only = abs(full_pnl - delta_only)
        res_dgv = abs(full_pnl - dgv_total)

        # Cross-gammas (vanna/vomma) are out of scope, so delta-gamma-vega
        # still beats delta-only at every move size tested.
        assert res_dgv < res_delta_only
        dgv_residuals.append(res_dgv)

    # Documented Taylor order: with cross-gammas out of scope, the
    # dominant leftover term is the cross (vanna) / vol-convexity (vomma)
    # contribution, O(h^2) -- residual shrinks ~4x per halving of the move.
    for prev_res, curr_res in itertools.pairwise(dgv_residuals):
        ratio = prev_res / curr_res
        assert 2.5 < ratio < 4.5, f"expected ~quadratic shrinkage, got ratio={ratio}"


# --- limit_utilization + desk_report integration ----------------------------


def test_desk_report_deterministic_and_json_able():
    var, es = 1_200_000.0, 1_650_000.0
    components = pnl_explain.delta_gamma_vega_pnl(
        [1500.0, -300.0], [40.0, 5.0], [900.0, 150.0], [0.5, -0.2], [0.01, -0.005]
    )
    utilization = pnl_explain.limit_utilization(
        [950_000.0, 1_800_000.0], [1_000_000.0, 1_500_000.0]
    )
    backtest = var_backtest.basel_traffic_light(4, 250)

    report1 = pnl_explain.desk_report(var, es, components, utilization, backtest)
    report2 = pnl_explain.desk_report(var, es, components, utilization, backtest)

    assert report1 == report2
    assert report1["var"] == pytest.approx(var, abs=1e-12)
    assert report1["es"] == pytest.approx(es, abs=1e-12)
    assert isinstance(report1["utilization"]["utilization"], list)
    assert isinstance(report1["utilization"]["breached"], list)
    assert report1["backtest"]["zone"] == "green"

    # Pure JSON-able: no numpy scalars/arrays or dataclasses left behind.
    json.dumps(report1)
