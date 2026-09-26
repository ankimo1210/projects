"""Hull 11e GE §27.2: time-dependent and stochastic volatility building blocks."""

import math

import numpy as np
import pytest
from hullkit import bsm
from hullkit import stochastic_volatility as sv

HESTON = dict(v0=0.04, reversion=1.5, long_run=0.04, vol_of_variance=0.6)


def test_hull_average_variance_example():
    average = sv.average_variance_rate((0.5, 0.5), (0.20, 0.30))
    assert average == pytest.approx(0.065, abs=1e-15)
    assert round(math.sqrt(average), 3) == 0.255
    price = sv.time_dependent_bsm_price(100.0, 100.0, 0.05, (0.5, 0.5), (0.20, 0.30))
    assert price == pytest.approx(float(bsm.call_price(100, 100, 0.05, math.sqrt(0.065), 1.0)))
    arithmetic = float(bsm.call_price(100, 100, 0.05, 0.25, 1.0))
    assert price - arithmetic > 0.18


def test_put_call_parity_and_dividends_for_time_dependent_price():
    args = (100.0, 95.0, 0.03, (0.25, 0.75), (0.4, 0.2), 0.01)
    call = sv.time_dependent_bsm_price(*args)
    put = sv.time_dependent_bsm_price(*args, kind="put")
    assert call - put == pytest.approx(100 * math.exp(-0.01) - 95 * math.exp(-0.03), abs=1e-12)


def test_expected_average_variance_matches_exact_sampling():
    expected = sv.expected_average_variance(0.09, 2.0, 0.04, 0.5)
    assert expected == pytest.approx(0.04 + 0.05 * (1 - math.exp(-1.0)) / 1.0)
    assert sv.expected_average_variance(0.09, 0.0, 0.04, 0.5) == 0.09
    samples = sv.simulate_average_variance(
        0.09, 2.0, 0.04, 0.5, 0.5, n_steps=100, n_paths=40_000, seed=11
    )
    error = samples.std(ddof=1) / math.sqrt(samples.size)
    assert abs(samples.mean() - expected) < 4 * error
    assert np.all(samples > 0.0)


def test_mixing_price_matches_heston_fourier_at_zero_correlation():
    samples = sv.simulate_average_variance(
        **HESTON, expiry=1.0, n_steps=100, n_paths=60_000, seed=3
    )
    for strike in (80.0, 100.0, 130.0):
        mixed, error = sv.mixing_price(100.0, strike, 0.05, 1.0, samples)
        fourier = sv.heston_price(100.0, strike, 0.05, 1.0, **HESTON, rho=0.0)
        assert abs(mixed - fourier) < 4 * error


def test_deterministic_mixing_is_bsm_and_zero_correlation_smile_is_symmetric():
    price, error = sv.mixing_price(100.0, 90.0, 0.05, 1.0, [0.04, 0.04])
    assert price == pytest.approx(float(bsm.call_price(100, 90, 0.05, 0.2, 1.0)), abs=1e-13)
    assert error == 0.0
    from hullkit.volatility import implied_vol

    forward = 100 * math.exp(0.05)
    vols = []
    for strike in (forward * math.exp(0.3), forward * math.exp(-0.3)):
        vols.append(
            implied_vol(
                sv.heston_price(100.0, strike, 0.05, 1.0, **HESTON, rho=0.0),
                100.0,
                strike,
                0.05,
                1.0,
            )
        )
    assert vols[0] == pytest.approx(vols[1], abs=1e-8)


def test_bsm_overprices_atm_and_underprices_wings_without_correlation():
    flat = math.sqrt(sv.expected_average_variance(0.04, 1.5, 0.04, 1.0))
    gap = {
        k: sv.heston_price(100.0, k, 0.05, 1.0, **HESTON, rho=0.0)
        - float(bsm.call_price(100.0, k, 0.05, flat, 1.0))
        for k in (60.0, 100.0, 160.0)
    }
    assert gap[100.0] < 0.0 < min(gap[60.0], gap[160.0])


def test_heston_parity_negative_skew_and_small_xi_limit():
    call = sv.heston_price(100.0, 110.0, 0.04, 0.75, **HESTON, rho=-0.5, dividend_yield=0.02)
    put = sv.heston_price(
        100.0, 110.0, 0.04, 0.75, **HESTON, rho=-0.5, dividend_yield=0.02, kind="put"
    )
    assert call - put == pytest.approx(100 * math.exp(-0.015) - 110 * math.exp(-0.03), abs=1e-10)
    from hullkit.volatility import implied_vol

    def vol(strike, rho):
        return implied_vol(
            sv.heston_price(100.0, strike, 0.05, 1.0, **HESTON, rho=rho), 100.0, strike, 0.05, 1.0
        )

    assert vol(90.0, -0.7) > vol(110.0, -0.7)
    assert vol(90.0, 0.7) < vol(110.0, 0.7)
    small = sv.heston_price(100.0, 100.0, 0.05, 1.0, 0.04, 1.5, 0.04, 1e-3, 0.0)
    assert small == pytest.approx(float(bsm.call_price(100, 100, 0.05, 0.2, 1.0)), abs=1e-5)


@pytest.mark.parametrize(
    "call",
    [
        lambda: sv.average_variance_rate((0.5,), (0.2, 0.3)),
        lambda: sv.average_variance_rate((0.0, 1.0), (0.2, 0.3)),
        lambda: sv.average_variance_rate((0.5, 0.5), (-0.2, 0.3)),
        lambda: sv.time_dependent_bsm_price(0.0, 100.0, 0.05, (1.0,), (0.2,)),
        lambda: sv.time_dependent_bsm_price(100.0, 100.0, 0.05, (1.0,), (0.2,), kind="digital"),
        lambda: sv.expected_average_variance(0.04, 1.0, 0.04, 0.0),
        lambda: sv.simulate_average_variance(
            0.04, 1.0, 0.04, 0.3, 1.0, n_steps=0, n_paths=10, seed=1
        ),
        lambda: sv.simulate_average_variance(
            0.04, 1.0, 0.04, 0.0, 1.0, n_steps=5, n_paths=10, seed=1
        ),
        lambda: sv.mixing_price(100.0, 100.0, 0.05, 1.0, [0.04]),
        lambda: sv.mixing_price(100.0, 100.0, 0.05, 1.0, [0.04, -0.01]),
        lambda: sv.heston_price(100.0, 100.0, 0.05, 1.0, 0.04, 1.5, 0.04, 0.6, 1.0),
        lambda: sv.heston_price(100.0, 100.0, 0.05, 1.0, 0.04, 1.5, 0.04, 1e-4, 0.0),
        lambda: sv.heston_price(100.0, 100.0, float("nan"), 1.0, 0.04, 1.5, 0.04, 0.6, 0.0),
    ],
)
def test_invalid_inputs_are_rejected(call):
    with pytest.raises(ValueError):
        call()
