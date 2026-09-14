"""Variance and volatility swaps (Hull 11e GE §26.16, eqs. 26.6-26.10); audit item EX-05."""

import math

import numpy as np
import pytest
from hullkit import variance_swaps as vs

# Example 26.4 inputs (Hull 11e GE §26.16 p.630)
EX_S, EX_R, EX_Q, EX_T = 1020.0, 0.04, 0.01, 0.25
EX_STRIKES = np.arange(800.0, 1201.0, 50.0)
EX_VOLS = np.array([0.29, 0.28, 0.27, 0.26, 0.25, 0.24, 0.23, 0.22, 0.21])
EX_Q_PRINTED = np.array([2.22, 5.22, 11.05, 21.27, 51.21, 38.94, 20.69, 9.44, 3.57])


def test_example_26_4_setup_forward_s_star_spacing():
    """Hull p.630: F0 = 1,027.68, S* = 1,000, Delta K_i = 50 for all i."""
    F0 = EX_S * math.exp((EX_R - EX_Q) * EX_T)
    assert F0 == pytest.approx(1027.68, abs=5e-3)
    assert vs.default_s_star(EX_STRIKES, F0) == 1000.0
    assert np.all(vs.strike_spacing(EX_STRIKES) == 50.0)


def test_example_26_4_q_values_from_smile():
    """Hull p.630 prints DerivaGem's Q(K_i); BSM at the per-strike vols reproduces all nine to 2 dp."""
    from hullkit import bsm

    calls = bsm.call_price(EX_S, EX_STRIKES, EX_R, EX_VOLS, EX_T, EX_Q)
    puts = bsm.put_price(EX_S, EX_STRIKES, EX_R, EX_VOLS, EX_T, EX_Q)
    q_values = vs.otm_option_prices(EX_STRIKES, calls, puts, 1000.0)
    assert q_values == pytest.approx(EX_Q_PRINTED, abs=5e-3)
    assert q_values[4] == pytest.approx(0.5 * (calls[4] + puts[4]), abs=1e-12)  # K = S*


def test_example_26_4_fair_variance_and_swap_value():
    """Hull 11e GE §26.16 pp.630-631, Example 26.4.

    From the printed Q(K_i): sum dK/K^2 e^{rT} Q = 0.008139, E(V) = 0.0621, and
    the swap receiving variance against 0.045 on $100m is worth 1.69 ($m).
    Computed: strip 0.0081387 / E(V) 0.062101 / value 1.6931 with Q from the
    smile; with the 2-dp printed Q the strip is 0.0081385 (rounds to 0.008138,
    the gap is the Q rounding), E(V) 0.062099, value 1.6928.
    """
    from hullkit import bsm

    F0 = EX_S * math.exp((EX_R - EX_Q) * EX_T)
    weights = vs.strike_spacing(EX_STRIKES) / EX_STRIKES**2 * math.exp(EX_R * EX_T)
    calls = bsm.call_price(EX_S, EX_STRIKES, EX_R, EX_VOLS, EX_T, EX_Q)
    puts = bsm.put_price(EX_S, EX_STRIKES, EX_R, EX_VOLS, EX_T, EX_Q)
    q_smile = vs.otm_option_prices(EX_STRIKES, calls, puts, 1000.0)
    assert float(np.sum(weights * q_smile)) == pytest.approx(0.008139, abs=5e-7)
    assert float(np.sum(weights * EX_Q_PRINTED)) == pytest.approx(0.008139, abs=1e-6)

    ev_printed = vs.fair_variance(EX_STRIKES, EX_Q_PRINTED, F0, EX_R, EX_T)
    ev_smile = vs.fair_variance_from_implied_vols(EX_S, EX_STRIKES, EX_VOLS, EX_R, EX_T, EX_Q)
    for ev in (ev_printed, ev_smile):
        assert ev == pytest.approx(0.0621, abs=5e-5)
        value = vs.variance_swap_value(ev, 0.045, EX_R, EX_T, notional=100.0)
        assert value == pytest.approx(1.69, abs=5e-3)
    assert ev_printed == pytest.approx(0.0620986, abs=1e-7)
    assert ev_smile == pytest.approx(0.0621008, abs=1e-7)


def test_example_26_5_volatility_swap():
    """Hull 11e GE §26.16 p.631, Example 26.5.

    E(V) = 0.0621, var(V) = 0.01^2: E(sigma) = 0.2484; receiving realized vol
    against 23% on $100m is worth 1.82 ($m). Computed 0.248391 / 1.8208.
    """
    e_sigma = vs.expected_volatility(0.0621, 0.01**2)
    assert e_sigma == pytest.approx(0.2484, abs=5e-5)
    assert e_sigma < math.sqrt(0.0621)
    value = vs.volatility_swap_value(e_sigma, 0.23, EX_R, EX_T, notional=100.0)
    assert value == pytest.approx(1.82, abs=5e-3)


def test_vix_truncation_differs_only_by_the_log_expansion():
    """Eq. (26.10) replaces ln(F0/S*) by its two-term expansion (Hull p.631)."""
    F0 = EX_S * math.exp((EX_R - EX_Q) * EX_T)
    x = F0 / 1000.0
    ev = vs.fair_variance(EX_STRIKES, EX_Q_PRINTED, F0, EX_R, EX_T)
    vix = vs.vix_cumulative_variance(EX_STRIKES, EX_Q_PRINTED, F0, EX_R, EX_T)
    expansion_error = (2.0 / EX_T) * (math.log(x) - (x - 1.0) + 0.5 * (x - 1.0) ** 2)
    assert ev - vix / EX_T == pytest.approx(expansion_error, abs=1e-15)


@pytest.mark.parametrize(
    ("S", "r", "q", "sigma", "T"),
    [(100.0, 0.05, 0.0, 0.20, 1.0), (100.0, 0.03, 0.01, 0.25, 0.5)],
)
@pytest.mark.parametrize("dK", [2.5, 1.25, 0.5])
def test_flat_smile_recovers_sigma_squared_within_grid_bias(S, r, q, sigma, T, dK):
    """A flat smile must give E(V) = sigma^2 up to the grid bias.

    Tolerance: Q jumps from put to call at S* by e^{-rT}(F0 - K); the midpoint
    sum integrates that kink with error (dK^2/12) g'(S*), g(K) = (F0 - K)/K^2,
    so E(V)_grid - sigma^2 ~= dK^2 (2 F0 - S*) / (6 T S*^3) (the smooth put part
    contributes nothing at this order because its slope vanishes in both
    wings). The strip spans 0.15 F0 .. 4.5 F0, so truncation is negligible and
    the error must equal that bias to 0.2% — at dK = 2.5 the bias is ~1e-4 in
    variance, i.e. 0.24 vol points on 20%.
    """
    F0 = S * math.exp((r - q) * T)
    strikes = dK * np.arange(math.ceil(0.15 * F0 / dK), math.floor(4.5 * F0 / dK) + 1)
    ev = vs.fair_variance_from_implied_vols(S, strikes, sigma, r, T, q)
    s_star = vs.default_s_star(strikes, F0)
    bias = dK**2 * (2.0 * F0 - s_star) / (6.0 * T * s_star**3)
    assert ev - sigma**2 == pytest.approx(bias, rel=2e-3)


def test_truncated_strip_biases_low():
    # A strip that misses the wings under-replicates the log contract.
    ev = vs.fair_variance_from_implied_vols(100.0, np.arange(60.0, 141.0, 5.0), 0.20, 0.05, 1.0)
    assert ev < 0.04


def test_validation():
    with pytest.raises(ValueError):
        vs.strike_spacing([100.0])
    with pytest.raises(ValueError):
        vs.strike_spacing([100.0, 90.0])
    with pytest.raises(ValueError):
        vs.default_s_star([110.0, 120.0], 100.0)
    with pytest.raises(ValueError):
        vs.fair_variance([90.0, 100.0], [1.0], 100.0, 0.0, 1.0)
    with pytest.raises(ValueError):
        vs.fair_variance([90.0, 100.0], [1.0, 1.0], 100.0, 0.0, 0.0)
    with pytest.raises(ValueError):
        vs.expected_volatility(0.04, -1e-4)
    with pytest.raises(ValueError):
        vs.fair_variance_from_implied_vols(100.0, [90.0, 100.0], [0.2, 0.0], 0.0, 1.0)
