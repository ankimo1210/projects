"""Resilient-liquidity (OW-style) tests (spec §21.4)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.resilience import (
    cost_matrix,
    ow_closed_form,
    ow_numeric,
    resilience_sweep,
    transient_cost,
)


def test_closed_form_completes_and_shape(cfg):
    X, T, N = cfg.initial_inventory, cfg.horizon_seconds, cfg.n_decision_steps
    q = ow_closed_form(X, T, 0.01, N)
    assert q.sum() == pytest.approx(X)
    assert np.all(q > 0)
    # U-shaped: end blocks exceed interior rate
    assert q[0] > q[1] and q[-1] > q[-2]
    interior = q[1:-1]
    np.testing.assert_allclose(interior, interior[0])


def test_numeric_matches_closed_form_exponential(cfg):
    # fine grid: the discrete optimum approaches the continuous OW solution
    c = cfg.with_overrides({"impact": {"propagator": "exponential", "resilience_rho": 0.01}})
    N = 120
    q_num = ow_numeric(c, n_steps=N)
    q_cf = ow_closed_form(c.initial_inventory, c.horizon_seconds, 0.01, N)
    # costs agree tightly even where shapes differ slightly at the ends
    c_num = transient_cost(c, q_num)
    c_cf = transient_cost(c, q_cf)
    assert c_num <= c_cf * (1 + 1e-9)  # numeric is the optimum
    assert c_cf == pytest.approx(c_num, rel=0.02)
    # block structure: ends much larger than interior
    assert q_cf[0] > 3 * q_cf[1]
    assert q_num[0] > 3 * np.median(q_num)


def test_ow_discrete_converges_to_closed_form(cfg):
    """Grid-refinement convergence: as n_steps grows, the discrete OW optimum
    and the closed-form schedule agree in cost (both approach the continuous
    OW solution). The numeric optimum is a lower bound at every grid."""
    c = cfg.with_overrides({"impact": {"propagator": "exponential", "resilience_rho": 0.01}})
    rho = 0.01
    gaps = []
    for n_steps in (24, 72, 216):
        q_num = ow_numeric(c, n_steps=n_steps)
        q_cf = ow_closed_form(c.initial_inventory, c.horizon_seconds, rho, n_steps)
        c_num = transient_cost(c, q_num)
        c_cf = transient_cost(c, q_cf)
        assert c_num <= c_cf * (1 + 1e-9)  # numeric is the optimum at every grid
        gaps.append(abs(c_cf - c_num) / c_num)
    # refining the grid never increases the gap and drives it to ~0
    assert gaps[1] <= gaps[0] + 1e-6
    assert gaps[2] <= gaps[1] + 1e-6
    assert gaps[-1] < 5e-3


def test_ow_beats_twap_and_immediate(cfg):
    c = cfg.with_overrides({"impact": {"propagator": "exponential", "resilience_rho": 0.005}})
    N = c.n_decision_steps
    X = c.initial_inventory
    q_ow = ow_numeric(c)
    q_twap = np.full(N, X / N)
    q_imm = np.zeros(N)
    q_imm[0] = X
    c_ow = transient_cost(c, q_ow)
    assert c_ow < transient_cost(c, q_twap)
    assert c_ow < transient_cost(c, q_imm)


def test_impact_state_finite_and_psd(cfg):
    M = cost_matrix(cfg, cfg.n_decision_steps)
    assert np.all(np.isfinite(M))
    eigmin = np.linalg.eigvalsh(M).min()
    assert eigmin > -1e-8


def test_resilience_sweep_interpretation(cfg):
    sweep = resilience_sweep(cfg, (0.001, 0.01, 0.1))
    # low resilience (persistent impact) -> more weight in the end blocks
    lo = sweep[0.001]["closed_form"]
    hi = sweep[0.1]["closed_form"]
    assert lo[0] / lo.sum() > hi[0] / hi.sum()
    for _rho, res in sweep.items():
        assert res["cost_numeric"] <= res["cost_twap"] + 1e-9
        assert np.isfinite(res["cost_numeric"])


def test_powerlaw_numeric_valid(cfg):
    c = cfg.with_overrides({"impact": {"propagator": "powerlaw"}})
    q = ow_numeric(c)
    assert q.sum() == pytest.approx(c.initial_inventory)
    assert np.all(q >= 0)


def test_rho_zero_rejected(cfg):
    with pytest.raises(ValueError):
        ow_closed_form(1000.0, 100.0, 0.0, 10)
