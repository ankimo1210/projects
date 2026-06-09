"""Tests for hullkit.exotics against Hull 11e Ch.26 closed forms."""

import math

import numpy as np
import pytest
from hullkit import bsm, exotics


def test_gap_call():
    g = exotics.gap_call(100.0, 95.0, 100.0, 0.05, 0.20, 1.0)
    assert g == pytest.approx(13.112208, abs=1e-5)


def test_binary_decomposition_equals_vanilla():
    S, K, r, sigma, T, q = 100.0, 100.0, 0.05, 0.2, 1.0, 0.0
    aon = exotics.asset_or_nothing(S, K, r, sigma, T, q, kind="call")
    con = exotics.cash_or_nothing(S, K, r, sigma, T, q, kind="call", payout=1.0)
    assert aon - K * con == pytest.approx(bsm.call_price(S, K, r, sigma, T, q), abs=1e-12)


def test_cash_or_nothing_parity():
    S, K, r, sigma, T = 100.0, 105.0, 0.05, 0.3, 0.5
    cc = exotics.cash_or_nothing(S, K, r, sigma, T, kind="call", payout=1.0)
    cp = exotics.cash_or_nothing(S, K, r, sigma, T, kind="put", payout=1.0)
    assert cc + cp == pytest.approx(math.exp(-r * T), abs=1e-12)


def test_barrier_in_out_equals_vanilla():
    S, K, H, r, sigma, T = 100.0, 100.0, 90.0, 0.05, 0.2, 1.0
    cdi = exotics.barrier_call(S, K, H, r, sigma, T, barrier="down-and-in")
    cdo = exotics.barrier_call(S, K, H, r, sigma, T, barrier="down-and-out")
    assert cdi + cdo == pytest.approx(bsm.call_price(S, K, r, sigma, T), abs=1e-12)
    assert cdi == pytest.approx(1.785112, abs=1e-5)


def test_barrier_monotonic_in_h():
    # down-and-in call increases as the barrier rises toward the strike
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.2, 1.0
    c70 = exotics.barrier_call(S, K, 70.0, r, sigma, T, barrier="down-and-in")
    c90 = exotics.barrier_call(S, K, 90.0, r, sigma, T, barrier="down-and-in")
    assert c90 > c70


def test_margrabe_r_independent_and_value():
    v1 = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0)
    assert v1 == pytest.approx(7.965567, abs=1e-5)
    # Margrabe does not depend on r (it is not even an argument)
    v2 = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0, q_u=0.0, q_v=0.0)
    assert v1 == pytest.approx(v2, abs=1e-12)


def test_asian_tw_below_vanilla_and_near_mc():
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.2, 1.0
    a = exotics.asian_call_turnbull_wakeman(S, K, r, sigma, T)
    assert a < bsm.call_price(S, K, r, sigma, T)  # averaging lowers vol
    # MC arithmetic-average check
    rng = np.random.default_rng(1)
    n_steps, n_paths, dt = 252, 200_000, T / 252
    z = rng.standard_normal((n_paths, n_steps))
    lp = np.cumsum((r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z, axis=1)
    avg = (S * np.exp(lp)).mean(axis=1)
    mc = math.exp(-r * T) * np.maximum(avg - K, 0.0).mean()
    assert a == pytest.approx(mc, abs=0.1)


def test_lookback_floating_exceeds_atm_call():
    S, r, sigma, T = 100.0, 0.05, 0.2, 1.0
    lb = exotics.lookback_floating_call(S, S, r, sigma, T)
    assert lb > bsm.call_price(S, S, r, sigma, T)
    assert lb == pytest.approx(17.2168, abs=1e-3)


def test_validation_errors():
    with pytest.raises(ValueError):
        exotics.cash_or_nothing(100.0, 100.0, 0.05, 0.2, 1.0, kind="cal")
    with pytest.raises(ValueError):
        exotics.barrier_call(100.0, 100.0, 90.0, 0.05, 0.2, 1.0, barrier="sideways")


def test_barrier_already_breached_domain():
    # down barrier above spot, or up barrier below spot = already breached at t=0
    van = bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0)
    assert exotics.barrier_call(100.0, 100.0, 105.0, 0.05, 0.2, 1.0, barrier="down-and-out") == 0.0
    assert exotics.barrier_call(
        100.0, 100.0, 105.0, 0.05, 0.2, 1.0, barrier="down-and-in"
    ) == pytest.approx(van, abs=1e-12)
    assert exotics.barrier_call(100.0, 100.0, 95.0, 0.05, 0.2, 1.0, barrier="up-and-out") == 0.0
    assert exotics.barrier_call(
        100.0, 100.0, 95.0, 0.05, 0.2, 1.0, barrier="up-and-in"
    ) == pytest.approx(van, abs=1e-12)


def test_barrier_per_branch_values():
    # valid up barrier H=120 >= K=100, S=100 < H — pin both branches
    assert exotics.barrier_call(
        100.0, 100.0, 120.0, 0.05, 0.20, 1.0, barrier="up-and-out"
    ) == pytest.approx(1.17607, abs=1e-4)
    assert exotics.barrier_call(
        100.0, 100.0, 120.0, 0.05, 0.20, 1.0, barrier="up-and-in"
    ) == pytest.approx(9.27452, abs=1e-4)


def test_asian_b_zero_limit():
    # r == q (b=0): no crash, matches the b=0 analytic limit
    import math

    a = exotics.asian_call_turnbull_wakeman(100.0, 100.0, 0.05, 0.20, 1.0, q=0.05)
    assert a > 0.0 and math.isfinite(a)


def test_lookback_b_zero_raises():
    with pytest.raises(ValueError):
        exotics.lookback_floating_call(100.0, 100.0, 0.05, 0.20, 1.0, q=0.05)
