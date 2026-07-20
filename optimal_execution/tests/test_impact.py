"""Impact-model tests (spec §21.2), including hand-calculated examples."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.impact import (
    ImpactChannels,
    classical_execution,
    manipulation_profit,
    propagator_displacement,
    propagator_matrix,
    round_trip_pnl,
    sqrt_impact,
    temporary_concession,
    temporary_cost,
    transient_decay_curve,
    transient_displacement,
)


def _flat_mid(cfg, n_paths, n_steps):
    return np.full((n_paths, n_steps + 1), cfg.arrival_price)


def test_zero_trade_zero_impact(cfg):
    n = cfg.n_decision_steps
    q = np.zeros((3, n))
    res = classical_execution(
        cfg, q, _flat_mid(cfg, 3, n), channels=ImpactChannels(True, True, True)
    )
    assert np.allclose(res["temporary"], 0)
    assert np.allclose(res["permanent"], 0)
    assert np.allclose(res["transient"], 0)
    d_pre, d_end = transient_displacement(q, cfg.dt, 1e-6, 0.01)
    assert np.allclose(d_pre, 0) and np.allclose(d_end, 0)


def test_larger_trade_costs_more(cfg):
    dt = cfg.dt
    assert temporary_cost(2000.0, dt, 5e-5) > temporary_cost(1000.0, dt, 5e-5)
    assert temporary_concession(200.0, 5e-5) > temporary_concession(100.0, 5e-5)


def test_temporary_impact_hand_example():
    # eta = 5e-5, q = 3000 shares over dt = 60 s -> v = 50 sh/s
    # concession = eta * v = 2.5e-3 currency; cash cost = concession * q = 7.5
    assert temporary_concession(50.0, 5e-5) == pytest.approx(2.5e-3)
    assert temporary_cost(3000.0, 60.0, 5e-5) == pytest.approx(7.5)


def test_temporary_does_not_alter_unaffected_price(cfg):
    n = cfg.n_decision_steps
    q = np.full((1, n), cfg.initial_inventory / n)
    mid = _flat_mid(cfg, 1, n)
    res = classical_execution(cfg, q, mid, channels=ImpactChannels(True, False, False))
    # impacted mid (perm+transient state) stays at the unaffected price
    np.testing.assert_allclose(res["impacted_mid"], mid[:, :-1])
    # but execution price is strictly worse for a sell
    assert np.all(res["exec_price"] < cfg.arrival_price)


def test_permanent_accumulates_hand_example(cfg):
    # gamma = 1e-6, two steps of 1000 shares (sell):
    # step0 sees gamma*(0 + 500) = 5e-4; step1 sees gamma*(1000 + 500) = 1.5e-3
    c = cfg.with_overrides({"impact": {"permanent_gamma": 1e-6}})
    q = np.array([[1000.0, 1000.0]])
    mid = np.full((1, 3), 100.0)
    res = classical_execution(c, q, mid, channels=ImpactChannels(False, True, False))
    np.testing.assert_allclose(res["permanent"][0], [5e-4, 1.5e-3])
    # impacted mid reflects only completed (pre-step) permanent shift
    np.testing.assert_allclose(res["impacted_mid"][0], [100.0, 100.0 - 1e-3])


def test_transient_decays_at_configured_rate():
    dt, eta_t, rho = 60.0, 2e-6, 0.01
    q = np.array([[5000.0, 0.0, 0.0, 0.0]])
    d_pre, d_end = transient_displacement(q, dt, eta_t, rho)
    j = eta_t * 5000.0  # displacement jump at the trade instant
    g = np.exp(-rho * dt)
    # point-impulse recursion D_{k+1} = g (D_k + eta q_k):
    # trade at k=0 -> D_1 = j g; D_2 = j g^2; D_3 = j g^3; end state j g^4
    np.testing.assert_allclose(d_pre[0], [0.0, j * g, j * g**2, j * g**3])
    assert d_end[0] == pytest.approx(j * g**4)
    curve = transient_decay_curve(j, rho, dt, 3)
    np.testing.assert_allclose(curve, [j, j * g, j * g**2, j * g**3])


def test_higher_resilience_recovers_faster():
    q = np.array([[10000.0] + [0.0] * 9])
    _, d_slow = transient_displacement(q, 60.0, 2e-6, 0.001)
    _, d_fast = transient_displacement(q, 60.0, 2e-6, 0.1)
    assert d_fast[0] < d_slow[0]


def test_propagator_exponential_matches_recursion(cfg):
    rng = np.random.default_rng(0)
    q = rng.uniform(0, 2000, size=(4, 12))
    dt = cfg.dt
    c = cfg.with_overrides({"impact": {"propagator": "exponential"}})
    d_prop = propagator_displacement(q, dt, c)
    d_rec, _ = transient_displacement(q, dt, c.impact.transient_eta, c.impact.resilience_rho)
    np.testing.assert_allclose(d_prop, d_rec, rtol=1e-10)


def test_propagator_powerlaw_decays_slower_at_long_lags(cfg):
    c = cfg.with_overrides(
        {"impact": {"propagator": "powerlaw", "powerlaw_beta": 0.5, "powerlaw_tau0": 30.0}}
    )
    P_pow = propagator_matrix(20, cfg.dt, c, "powerlaw")
    P_exp = propagator_matrix(20, cfg.dt, c, "exponential")
    # both are 1-ish at short lags; power law dominates at long lags
    assert P_pow[19, 0] > P_exp[19, 0]
    assert np.all(np.triu(P_pow) == 0)


def test_sqrt_impact_scaling(cfg):
    i1 = sqrt_impact(cfg.initial_inventory, cfg)
    i4 = sqrt_impact(4 * cfg.initial_inventory, cfg)
    assert i4 == pytest.approx(2 * i1)
    assert i1 > 0


def test_buy_sell_signs(cfg):
    n = cfg.n_decision_steps
    q = np.full((1, n), cfg.initial_inventory / n)
    mid = _flat_mid(cfg, 1, n)
    sell = classical_execution(cfg, q, mid)
    buy = classical_execution(cfg.with_overrides({"side": "buy"}), q, mid)
    assert np.all(sell["exec_price"] < cfg.arrival_price)
    assert np.all(buy["exec_price"] > cfg.arrival_price)
    # symmetric magnitudes
    np.testing.assert_allclose(
        cfg.arrival_price - sell["exec_price"], buy["exec_price"] - cfg.arrival_price
    )


# ---- Huberman–Stanzl no-manipulation diagnostic -----------------------------


def test_round_trip_pnl_zero_for_linear_impact():
    """delta = 1: PnL = -(gamma/2)(sum z)^2 = 0 for any round trip."""
    rng = np.random.default_rng(7)
    z = rng.normal(size=25) * 1000.0
    z -= z.mean()  # round trip: sum z = 0
    assert round_trip_pnl(z, gamma=2.5e-7, delta=1.0) == pytest.approx(0.0, abs=1e-6)


def test_round_trip_pnl_matches_closed_form_linear():
    """Non-round-trip sanity: PnL = -(gamma/2)(sum z)^2 under delta = 1."""
    z = np.array([1000.0, 2000.0, -500.0])
    gamma = 1e-6
    expected = -0.5 * gamma * z.sum() ** 2
    assert round_trip_pnl(z, gamma=gamma, delta=1.0) == pytest.approx(expected)


def test_manipulation_zero_at_linear(cfg):
    result = manipulation_profit(cfg, delta=1.0)
    assert result["best_pnl"] == pytest.approx(0.0, abs=1e-6)


def test_concave_impact_admits_pump_and_dump(cfg):
    """delta < 1: many small trades then one block earns a positive PnL."""
    result = manipulation_profit(cfg, delta=0.6, n_pieces=10)
    assert result["pieces_then_block"] > 0
    assert result["best_pnl"] == pytest.approx(result["pieces_then_block"])
    # closed form: (gamma Q^2 / 2)(n^{1-delta} - 1)
    Q = cfg.initial_inventory
    gamma = cfg.impact.permanent_gamma
    expected = 0.5 * gamma * Q * Q * (10 ** (1 - 0.6) - 1)
    assert result["pieces_then_block"] == pytest.approx(expected, rel=1e-9)


def test_convex_impact_admits_block_then_pieces(cfg):
    """delta > 1: one block then many small trades earns a positive PnL."""
    result = manipulation_profit(cfg, delta=1.4, n_pieces=10)
    assert result["block_then_pieces"] > 0
    assert result["best_pnl"] == pytest.approx(result["block_then_pieces"])
