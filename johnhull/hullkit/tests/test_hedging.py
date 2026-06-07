"""Tests for hullkit.hedging (Hull 11e Ch.19, Tables 19.1-19.4)."""

import numpy as np
import pytest
from hullkit import bsm, hedging

# Hull Ch.19 running example
P = dict(S0=49.0, K=50.0, r=0.05, sigma=0.20, T=0.3846)
BSM_PRICE = bsm.call_price(P["S0"], P["K"], P["r"], P["sigma"], P["T"])  # 2.4004


def test_shapes_and_determinism():
    a = hedging.simulate_delta_hedge(**P, n_rebalance=10, n_paths=500)
    b = hedging.simulate_delta_hedge(**P, n_rebalance=10, n_paths=500)
    assert a.shape == (500,)
    assert np.array_equal(a, b)  # mc default seed 42 -> deterministic


def test_mean_cost_converges_to_bsm_price():
    costs = hedging.simulate_delta_hedge(**P, n_rebalance=20, n_paths=20_000, mu=0.13)
    assert float(costs.mean()) == pytest.approx(BSM_PRICE, abs=0.05)


def test_mean_is_mu_invariant():
    m_hi = hedging.simulate_delta_hedge(
        **P,
        n_rebalance=20,
        n_paths=20_000,
        mu=0.13,
        rng=np.random.default_rng(1),
    ).mean()
    m_lo = hedging.simulate_delta_hedge(
        **P,
        n_rebalance=20,
        n_paths=20_000,
        mu=0.05,
        rng=np.random.default_rng(1),
    ).mean()
    assert abs(float(m_hi) - float(m_lo)) < 0.1


def test_performance_improves_with_frequency():
    # Hull Table 19.4: performance = std(cost) / BSM price falls ~ 1/sqrt(n)
    perf = {}
    for n in (8, 64):
        costs = hedging.simulate_delta_hedge(
            **P,
            n_rebalance=n,
            n_paths=10_000,
            mu=0.13,
            rng=np.random.default_rng(2),
        )
        perf[n] = float(costs.std()) / BSM_PRICE
    assert perf[64] < 0.6 * perf[8]  # expected ratio ~ sqrt(8/64) ~ 0.35


def test_stop_loss_does_not_converge():
    # Hull Table 19.1: stop-loss performance stays high at high frequency
    dh = hedging.simulate_delta_hedge(
        **P, n_rebalance=64, n_paths=10_000, mu=0.13, rng=np.random.default_rng(3)
    )
    sl = hedging.simulate_stop_loss_hedge(
        **P, n_rebalance=64, n_paths=10_000, mu=0.13, rng=np.random.default_rng(3)
    )
    perf_dh = float(dh.std()) / BSM_PRICE
    perf_sl = float(sl.std()) / BSM_PRICE
    assert perf_sl > 2.0 * perf_dh
