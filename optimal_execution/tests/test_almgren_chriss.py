"""Almgren–Chriss tests (spec §21.3)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.almgren_chriss import (
    ac_continuous_cost,
    ac_expected_cost,
    ac_inventory,
    ac_schedule,
    efficient_frontier,
    kappa_for_lambda,
)


def test_boundary_conditions(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    for kappa in (0.0, 1e-4, 1e-3, 1e-2):
        x = ac_inventory(X, T, kappa, N)
        assert x[0] == pytest.approx(X)
        assert x[-1] == pytest.approx(0.0, abs=1e-9 * X)
        assert np.all(np.diff(x) <= 1e-12)  # non-increasing (sell program)
        q = ac_schedule(X, T, kappa, N)
        assert np.all(q >= -1e-12)
        assert q.sum() == pytest.approx(X)


def test_risk_neutral_limit_is_twap(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    twap = X * (1 - np.arange(N + 1) / N)
    x_tiny = ac_inventory(X, T, 1e-9, N)
    np.testing.assert_allclose(x_tiny, twap, rtol=1e-6, atol=1e-6 * X)
    # decreasing kappa converges monotonically toward TWAP
    d1 = np.abs(ac_inventory(X, T, 1e-3, N) - twap).max()
    d2 = np.abs(ac_inventory(X, T, 1e-4, N) - twap).max()
    assert d2 < d1


def test_higher_risk_aversion_front_loads(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    q_lo = ac_schedule(X, T, kappa_for_lambda(cfg, 1e-8), N)
    q_hi = ac_schedule(X, T, kappa_for_lambda(cfg, 1e-5), N)
    assert q_hi[0] > q_lo[0]
    # first-quarter share of execution is larger under high risk aversion
    quarter = N // 4
    assert q_hi[:quarter].sum() > q_lo[:quarter].sum()


def test_higher_eta_slows_execution(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    lam = cfg.risk_aversion_lambda
    k_base = kappa_for_lambda(cfg, lam)
    cfg_hi_eta = cfg.with_overrides({"impact": {"temporary_eta": cfg.impact.temporary_eta * 10}})
    k_hi = kappa_for_lambda(cfg_hi_eta, lam)
    assert k_hi < k_base
    q_base = ac_schedule(X, T, k_base, N)
    q_hi = ac_schedule(X, T, k_hi, N)
    assert q_hi[0] < q_base[0]  # less front-loaded when impact is expensive


def test_large_kappa_numerically_stable(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    x = ac_inventory(X, T, 1.0, N)  # kappa*T = 1800 — would overflow naive sinh
    assert np.all(np.isfinite(x))
    assert x[0] == pytest.approx(X)
    q = ac_schedule(X, T, 1.0, N)
    assert q[0] / X > 0.9  # essentially immediate execution


def test_discrete_vs_continuous_cost(cfg):
    kappa = kappa_for_lambda(cfg, cfg.risk_aversion_lambda)
    q = ac_schedule(cfg.initial_inventory, cfg.horizon_seconds, kappa, cfg.n_decision_steps)
    disc = ac_expected_cost(cfg, q, include_spread_fees=False)
    cont = ac_continuous_cost(cfg, kappa)
    assert disc == pytest.approx(cont, rel=0.02)


def test_efficient_frontier_monotone(cfg):
    fr = efficient_frontier(cfg, np.logspace(-8, -5, 12))
    # higher risk aversion -> higher expected cost, lower risk
    assert np.all(np.diff(fr["expected_cost"]) >= -1e-9)
    assert np.all(np.diff(fr["cost_sd"]) <= 1e-9)
    assert np.all(fr["expected_cost_bps"] > 0)
