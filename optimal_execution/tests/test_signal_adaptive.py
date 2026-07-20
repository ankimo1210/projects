"""Signal-adaptive (stylized Lehalle–Neuman) schedule tests."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.almgren_chriss import ac_schedule, kappa_for_lambda
from optimal_execution.signal_adaptive import expected_signal_path, ln_schedule


def _lq_objective(cfg, q: np.ndarray, alpha_bar: np.ndarray, lam: float) -> float:
    """The exact discrete objective ln_schedule minimizes (constant sigma)."""
    n = len(q)
    dt = cfg.horizon_seconds / n
    x_next = cfg.initial_inventory - np.cumsum(q)
    return float(
        cfg.impact.temporary_eta * np.sum(q * q) / dt
        + lam * cfg.sigma_abs**2 * dt * np.sum(x_next**2)
        - dt * np.sum(alpha_bar * x_next)
    )


def test_signal_path_decays():
    path = expected_signal_path(2.0, 0.01, 600.0, 6)
    assert path[0] == pytest.approx(2.0)
    assert np.all(np.diff(path) < 0) and path[-1] > 0


def test_sums_to_inventory_and_nonnegative(cfg):
    for alpha0 in (-5e-4, 0.0, 5e-4):
        q = ln_schedule(cfg, alpha0=alpha0, kappa_alpha=1e-3)
        assert q.sum() == pytest.approx(cfg.initial_inventory)
        assert np.all(q >= -1e-9 * cfg.initial_inventory)


def test_zero_signal_reduces_to_discrete_ac(cfg):
    lam = cfg.risk_aversion_lambda
    n = 200  # fine grid: discrete optimum ~ continuous sinh solution
    q_ln = ln_schedule(cfg, alpha0=0.0, kappa_alpha=1e-3, n_steps=n, lam=lam)
    kappa = kappa_for_lambda(cfg, lam)
    q_ac = ac_schedule(cfg.initial_inventory, cfg.horizon_seconds, kappa, n)
    zeros = np.zeros(n)
    j_ln = _lq_objective(cfg, q_ln, zeros, lam)
    j_ac = _lq_objective(cfg, q_ac, zeros, lam)
    assert j_ln <= j_ac * (1 + 1e-9)  # LN is the discrete optimum
    assert j_ln == pytest.approx(j_ac, rel=2e-2)
    # both front-load under risk aversion
    assert q_ln[0] > q_ln[-1]


def test_zero_signal_zero_risk_is_twap(cfg):
    q = ln_schedule(cfg, alpha0=0.0, kappa_alpha=1e-3, lam=0.0)
    np.testing.assert_allclose(q, q[0], rtol=1e-6)


def test_favorable_signal_defers_adverse_front_loads(cfg):
    """Sell program: alpha0 > 0 (rising price) holds inventory longer."""
    lam = cfg.risk_aversion_lambda
    kap = 1e-3
    n = cfg.n_decision_steps
    dt = cfg.horizon_seconds / n

    def inventory_area(q: np.ndarray) -> float:
        return float(np.sum((cfg.initial_inventory - np.cumsum(q)) * dt))

    base = inventory_area(ln_schedule(cfg, 0.0, kap, lam=lam))
    up = inventory_area(ln_schedule(cfg, 5e-4, kap, lam=lam))
    down = inventory_area(ln_schedule(cfg, -5e-4, kap, lam=lam))
    assert up > base > down


def test_optimum_beats_ac_under_signal(cfg):
    """With a live signal the LN schedule must beat AC on the LN objective."""
    lam = cfg.risk_aversion_lambda
    kap = 1e-3
    n = cfg.n_decision_steps
    alpha_bar = expected_signal_path(5e-4, kap, cfg.horizon_seconds, n)
    q_ln = ln_schedule(cfg, 5e-4, kap, lam=lam)
    kappa = kappa_for_lambda(cfg, lam)
    q_ac = ac_schedule(cfg.initial_inventory, cfg.horizon_seconds, kappa, n)
    assert _lq_objective(cfg, q_ln, alpha_bar, lam) < _lq_objective(cfg, q_ac, alpha_bar, lam)
