"""Put counterparts, BGK discrete-monitoring correction and fixed lookbacks (Hull 11e GE Ch.26).

Audit item EX-02: gap put (§26.4), barrier puts and the Broadie-Glasserman-Kou
shift (§26.9), floating lookback put and fixed-strike lookbacks (§26.11).
"""

import math

import numpy as np
import pytest
from hullkit import bsm, exotics

BARRIER_PAIRS = (("down-and-in", "down-and-out"), ("up-and-in", "up-and-out"))


# --- §26.4 gap options ------------------------------------------------------


def test_gap_put_hull_example_26_1():
    """Hull 11e GE §26.4 p.617, Example 26.1.

    Insurance payout K1 - S_T when S_T < K2 with S0 = 500,000, K1 = 400,000,
    K2 = 350,000, r = 5%, q = 0, sigma = 20%, T = 1: printed $1,896 (hand
    calculation 1895.69). The regular put with K = 400,000 is printed as $3,436
    and equals the gap put with K1 = K2.
    """
    value = exotics.gap_put(500_000.0, 400_000.0, 350_000.0, 0.05, 0.20, 1.0)
    assert value == pytest.approx(1_896.0, abs=0.5)
    assert value == pytest.approx(1_895.69, abs=5e-3)
    regular = exotics.gap_put(500_000.0, 400_000.0, 400_000.0, 0.05, 0.20, 1.0)
    assert regular == pytest.approx(3_436.0, abs=0.5)
    assert regular == pytest.approx(bsm.put_price(500_000.0, 400_000.0, 0.05, 0.20, 1.0), rel=1e-12)
    # "reduces the cost of the policy ... by about 45%"
    assert 1.0 - value / regular == pytest.approx(0.45, abs=0.005)


@pytest.mark.parametrize(
    ("K1", "K2", "q"), [(95.0, 100.0, 0.0), (110.0, 100.0, 0.02), (100.0, 80.0, 0.04)]
)
def test_gap_call_minus_gap_put_parity(K1, K2, q):
    S, r, sigma, T = 100.0, 0.05, 0.25, 0.75
    call = exotics.gap_call(S, K1, K2, r, sigma, T, q)
    put = exotics.gap_put(S, K1, K2, r, sigma, T, q)
    assert call - put == pytest.approx(S * math.exp(-q * T) - K1 * math.exp(-r * T), abs=1e-10)


# --- §26.9 barrier puts -----------------------------------------------------


@pytest.mark.parametrize(("knock_in", "knock_out"), BARRIER_PAIRS)
@pytest.mark.parametrize("H", [70.0, 90.0, 100.0, 105.0, 115.0, 140.0])
@pytest.mark.parametrize(("S", "q"), [(100.0, 0.0), (110.0, 0.03)])
def test_barrier_put_in_plus_out_equals_vanilla(knock_in, knock_out, H, S, q):
    K, r, sigma, T = 105.0, 0.05, 0.25, 1.0
    p_in = exotics.barrier_put(S, K, H, r, sigma, T, q, barrier=knock_in)
    p_out = exotics.barrier_put(S, K, H, r, sigma, T, q, barrier=knock_out)
    assert p_in + p_out == pytest.approx(bsm.put_price(S, K, r, sigma, T, q), abs=1e-12)
    assert p_in >= -1e-12 and p_out >= -1e-12


def test_barrier_put_already_breached_domain():
    van = bsm.put_price(100.0, 100.0, 0.05, 0.2, 1.0)
    args = (100.0, 100.0)
    assert exotics.barrier_put(*args, 105.0, 0.05, 0.2, 1.0, barrier="down-and-out") == 0.0
    assert exotics.barrier_put(
        *args, 105.0, 0.05, 0.2, 1.0, barrier="down-and-in"
    ) == pytest.approx(van, abs=1e-12)
    assert exotics.barrier_put(*args, 95.0, 0.05, 0.2, 1.0, barrier="up-and-out") == 0.0
    assert exotics.barrier_put(*args, 95.0, 0.05, 0.2, 1.0, barrier="up-and-in") == pytest.approx(
        van, abs=1e-12
    )


def test_barrier_put_hull_degenerate_branches():
    # Hull p.622: a down barrier above the strike gives p_do = 0 and p_di = p.
    S, K, H, r, sigma, T = 110.0, 100.0, 105.0, 0.05, 0.25, 1.0
    van = bsm.put_price(S, K, r, sigma, T)
    assert exotics.barrier_put(S, K, H, r, sigma, T, barrier="down-and-out") == 0.0
    assert exotics.barrier_put(S, K, H, r, sigma, T, barrier="down-and-in") == van


@pytest.mark.parametrize(("S", "barrier"), [(110.0, "down-and-in"), (90.0, "up-and-in")])
def test_barrier_put_continuous_across_h_equals_k(S, barrier):
    # Hull switches formula at H = K; the two branches must meet there.
    K, r, sigma, T = 100.0, 0.05, 0.3, 1.0
    below = exotics.barrier_put(S, K, K - 1e-7, r, sigma, T, barrier=barrier)
    at = exotics.barrier_put(S, K, K, r, sigma, T, barrier=barrier)
    above = exotics.barrier_put(S, K, K + 1e-7, r, sigma, T, barrier=barrier)
    assert below == pytest.approx(at, abs=1e-6)
    assert above == pytest.approx(at, abs=1e-6)


def test_barrier_put_validation():
    with pytest.raises(ValueError):
        exotics.barrier_put(100.0, 100.0, 90.0, 0.05, 0.2, 1.0, barrier="sideways")
    with pytest.raises(ValueError):
        exotics.barrier_put(
            100.0, 100.0, 90.0, 0.05, 0.2, 1.0, barrier="down-and-out", n_observations=0
        )
    with pytest.raises(ValueError):
        exotics.barrier_call(100.0, 100.0, 90.0, 0.05, 0.2, 1.0, n_observations=2.5)


# --- Broadie-Glasserman-Kou discrete monitoring (§26.9 p.622) ---------------


def test_bgk_adjusted_barrier_shift_direction():
    """Hull 11e GE §26.9 p.622: H e^{+0.5826 sigma sqrt(T/m)} up, e^{-...} down."""
    H, sigma, T, m = 120.0, 0.3, 1.0, 52
    shift = math.exp(0.5826 * sigma * math.sqrt(T / m))
    assert exotics.bgk_adjusted_barrier(H, sigma, T, m, "up-and-out") == pytest.approx(
        H * shift, rel=1e-15
    )
    assert exotics.bgk_adjusted_barrier(H, sigma, T, m, "down-and-in") == pytest.approx(
        H / shift, rel=1e-15
    )
    with pytest.raises(ValueError):
        exotics.bgk_adjusted_barrier(H, sigma, T, m, "sideways")


@pytest.mark.parametrize("pricer", [exotics.barrier_call, exotics.barrier_put])
def test_bgk_correction_vanishes_as_monitoring_becomes_continuous(pricer):
    S, K, H, r, sigma, T = 100.0, 100.0, 120.0, 0.05, 0.3, 1.0
    cont = pricer(S, K, H, r, sigma, T, barrier="up-and-in")
    gaps = [
        abs(pricer(S, K, H, r, sigma, T, barrier="up-and-in", n_observations=m) - cont)
        for m in (4, 52, 252, 10_000, 1_000_000, 100_000_000)
    ]
    assert np.all(np.diff(gaps) < 0.0)
    assert gaps[-1] < 1e-3
    # the barrier shift is O(m^{-1/2}), so 100x more observations cut the gap ~10x
    assert gaps[3] / gaps[4] == pytest.approx(10.0, rel=0.02)


def test_bgk_matches_seeded_discrete_monitoring_mc():
    """Weekly-monitored (m = 52) up-and-in put, exact GBM sampled at the fixing dates.

    BGK must sit within 3 SE of the discrete MC while the continuous-monitoring
    formula is rejected by a wide margin (so the check has power).
    """
    S, K, H, r, sigma, T, m = 100.0, 100.0, 120.0, 0.05, 0.30, 1.0, 52
    n_paths = 200_000
    dt = T / m
    rng = np.random.default_rng(2026)
    z = rng.standard_normal((n_paths, m))
    log_paths = np.cumsum((r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z, axis=1)
    paths = S * np.exp(log_paths)
    knocked_in = paths.max(axis=1) >= H
    x = math.exp(-r * T) * np.maximum(K - paths[:, -1], 0.0) * knocked_in
    mc, se = x.mean(), x.std(ddof=1) / math.sqrt(n_paths)

    bgk = exotics.barrier_put(S, K, H, r, sigma, T, barrier="up-and-in", n_observations=m)
    cont = exotics.barrier_put(S, K, H, r, sigma, T, barrier="up-and-in")
    assert abs(bgk - mc) < 3.0 * se
    assert abs(cont - mc) > 10.0 * se


# --- §26.11 lookbacks --------------------------------------------------------


def test_floating_lookback_put_hull_example_26_2():
    """Hull 11e GE §26.11 p.624, Example 26.2.

    Newly issued floating lookback put: S0 = Smax = 50, sigma = 40%, r = 10%,
    q = 0, T = 0.25 (b1 = -0.025, b2 = -0.225, b3 = 0.025, Y2 = 0). Printed 7.79;
    computed 7.790219.
    """
    value = exotics.lookback_floating_put(50.0, 50.0, 0.10, 0.40, 0.25)
    assert value == pytest.approx(7.79, abs=5e-3)
    assert value == pytest.approx(7.790219, abs=1e-5)


def _continuous_extremes_mc(S, r, q, sigma, T, n_paths, n_steps, seed):
    """Exact continuous-monitoring max/min of GBM via the Brownian-bridge extreme law."""
    dt = T / n_steps
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_paths, n_steps))
    increments = (r - q - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z
    x = np.concatenate([np.zeros((n_paths, 1)), np.cumsum(increments, axis=1)], axis=1)
    x0, x1 = x[:, :-1], x[:, 1:]
    spread_max = np.sqrt((x1 - x0) ** 2 - 2.0 * sigma**2 * dt * np.log(rng.random(x0.shape)))
    spread_min = np.sqrt((x1 - x0) ** 2 - 2.0 * sigma**2 * dt * np.log(rng.random(x0.shape)))
    running_max = S * np.exp((0.5 * (x0 + x1 + spread_max)).max(axis=1))
    running_min = S * np.exp((0.5 * (x0 + x1 - spread_min)).min(axis=1))
    return running_max, running_min, S * np.exp(x[:, -1])


@pytest.fixture(scope="module")
def lookback_mc():
    S, r, q, sigma, T = 50.0, 0.10, 0.02, 0.40, 0.25
    running_max, running_min, s_T = _continuous_extremes_mc(S, r, q, sigma, T, 200_000, 20, seed=7)
    return {
        "S": S,
        "r": r,
        "q": q,
        "sigma": sigma,
        "T": T,
        "max": running_max,
        "min": running_min,
        "S_T": s_T,
    }


def _mc_mean_se(x):
    return x.mean(), x.std(ddof=1) / math.sqrt(x.size)


def test_lookbacks_match_continuous_monitoring_mc(lookback_mc):
    d = lookback_mc
    S, r, q, sigma, T = d["S"], d["r"], d["q"], d["sigma"], d["T"]
    disc = math.exp(-r * T)
    s_max0, s_min0 = 55.0, 45.0  # extremes observed before today
    m_tot = np.maximum(d["max"], s_max0)
    n_tot = np.minimum(d["min"], s_min0)
    cases = [
        (disc * (m_tot - d["S_T"]), exotics.lookback_floating_put(S, s_max0, r, sigma, T, q)),
        (disc * (d["S_T"] - n_tot), exotics.lookback_floating_call(S, s_min0, r, sigma, T, q)),
        (
            disc * np.maximum(m_tot - 52.0, 0.0),
            exotics.lookback_fixed_call(S, 52.0, s_max0, r, sigma, T, q),
        ),
        (
            disc * np.maximum(m_tot - 60.0, 0.0),
            exotics.lookback_fixed_call(S, 60.0, s_max0, r, sigma, T, q),
        ),
        (
            disc * np.maximum(48.0 - n_tot, 0.0),
            exotics.lookback_fixed_put(S, 48.0, s_min0, r, sigma, T, q),
        ),
        (
            disc * np.maximum(40.0 - n_tot, 0.0),
            exotics.lookback_fixed_put(S, 40.0, s_min0, r, sigma, T, q),
        ),
    ]
    for payoff, closed_form in cases:
        mc, se = _mc_mean_se(payoff)
        assert abs(closed_form - mc) < 3.0 * se


@pytest.mark.parametrize(("K", "S_max"), [(45.0, 50.0), (50.0, 50.0), (58.0, 55.0), (52.0, 55.0)])
def test_fixed_lookback_call_hull_relation(K, S_max):
    """Hull 11e GE §26.11 p.625: c_fix = p*_fl + S0 e^{-qT} - K e^{-rT}, S*_max = max(S_max, K)."""
    S, r, q, sigma, T = 50.0, 0.08, 0.01, 0.35, 0.5
    p_star = exotics.lookback_floating_put(S, max(S_max, K), r, sigma, T, q)
    c_fix = exotics.lookback_fixed_call(S, K, S_max, r, sigma, T, q)
    assert c_fix == pytest.approx(p_star + S * math.exp(-q * T) - K * math.exp(-r * T), abs=1e-12)
    assert c_fix >= bsm.call_price(S, K, r, sigma, T, q)  # max S_t >= S_T


@pytest.mark.parametrize(("K", "S_min"), [(55.0, 50.0), (50.0, 50.0), (42.0, 45.0), (48.0, 45.0)])
def test_fixed_lookback_put_hull_relation(K, S_min):
    """Hull 11e GE §26.11 p.625: p_fix = c*_fl + K e^{-rT} - S0 e^{-qT}, S*_min = min(S_min, K)."""
    S, r, q, sigma, T = 50.0, 0.08, 0.01, 0.35, 0.5
    c_star = exotics.lookback_floating_call(S, min(S_min, K), r, sigma, T, q)
    p_fix = exotics.lookback_fixed_put(S, K, S_min, r, sigma, T, q)
    assert p_fix == pytest.approx(c_star + K * math.exp(-r * T) - S * math.exp(-q * T), abs=1e-12)
    assert p_fix >= bsm.put_price(S, K, r, sigma, T, q)  # min S_t <= S_T


def test_lookback_new_functions_b_zero_and_domain_raise():
    with pytest.raises(ValueError):
        exotics.lookback_floating_put(100.0, 100.0, 0.05, 0.20, 1.0, q=0.05)
    with pytest.raises(ValueError):
        exotics.lookback_fixed_call(100.0, 100.0, 100.0, 0.05, 0.20, 1.0, q=0.05)
    with pytest.raises(ValueError):
        exotics.lookback_fixed_put(100.0, 100.0, 100.0, 0.05, 0.20, 1.0, q=0.05)
    with pytest.raises(ValueError):
        exotics.lookback_floating_put(100.0, 95.0, 0.05, 0.20, 1.0)  # S_max below spot
    with pytest.raises(ValueError):
        exotics.lookback_fixed_put(100.0, 100.0, 105.0, 0.05, 0.20, 1.0)  # S_min above spot
