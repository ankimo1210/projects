"""Hull GE §27.3: Dupire's local volatility from smooth call prices."""

import math

import pytest
from hullkit import bsm
from hullkit.local_volatility import dupire_local_vol


def test_call_price_docstring_identifies_today_discounted_currency_price():
    assert "discounted to today" in dupire_local_vol.__doc__
    assert "undiscounted-spot" not in dupire_local_vol.__doc__


def test_flat_bsm_surface_recovers_volatility_with_carry():
    def call(strike, expiry):
        return float(bsm.call_price(100, strike, 0.04, 0.23, expiry, 0.015))

    for strike in (75.0, 100.0, 125.0):
        for expiry in (0.5, 1.0, 2.0):
            found = dupire_local_vol(
                call, strike, expiry, 0.04, 0.015, strike_step=0.05, maturity_step=0.001
            )
            assert found == pytest.approx(0.23, abs=2e-4)


def test_time_varying_rate_and_dividend_yield_use_instantaneous_values():
    # Integrated rates define the vanilla surface; Dupire uses r(T), q(T).
    def call(strike, expiry):
        r_bar = 0.02 + 0.005 * expiry
        q_bar = 0.01 + 0.002 * expiry
        return float(bsm.call_price(100, strike, r_bar, 0.2, expiry, q_bar))

    assert dupire_local_vol(
        call, 105.0, 1.0, 0.03, 0.014, strike_step=0.05, maturity_step=0.001
    ) == pytest.approx(0.2, abs=2e-4)


def test_mixture_surface_recovers_analytic_conditional_variance():
    from scipy.stats import norm

    def call(strike, expiry):
        return 0.7 * float(bsm.call_price(100, strike, 0.03, 0.15, expiry, 0.01)) + 0.3 * float(
            bsm.call_price(100, strike, 0.03, 0.35, expiry, 0.01)
        )

    for strike in (85.0, 100.0, 115.0):
        for expiry in (0.5, 1.0):
            weights = []
            for sigma, p in ((0.15, 0.7), (0.35, 0.3)):
                d2 = (math.log(100 / strike) + (0.03 - 0.01 - 0.5 * sigma**2) * expiry) / (
                    sigma * math.sqrt(expiry)
                )
                density = (
                    math.exp(-0.03 * expiry) * norm.pdf(d2) / (strike * sigma * math.sqrt(expiry))
                )
                weights.append((p * density, sigma**2))
            expected = math.sqrt(sum(w * v for w, v in weights) / sum(w for w, _ in weights))
            found = dupire_local_vol(
                call, strike, expiry, 0.03, 0.01, strike_step=0.05, maturity_step=0.001
            )
            assert found == pytest.approx(expected, abs=2e-4)


@pytest.mark.parametrize(
    "strike,expiry,strike_step,maturity_step",
    [
        (0.0, 1.0, 0.1, 0.01),
        (100.0, 0.0, 0.1, 0.01),
        (0.1, 1.0, 0.1, 0.01),
        (100.0, 0.01, 0.1, 0.01),
        (100.0, 1.0, 0.0, 0.01),
        (100.0, 1.0, 0.1, -0.01),
    ],
)
def test_invalid_grid_is_rejected(strike, expiry, strike_step, maturity_step):
    with pytest.raises(ValueError):
        dupire_local_vol(
            lambda k, t: 1.0,
            strike,
            expiry,
            0.03,
            strike_step=strike_step,
            maturity_step=maturity_step,
        )


def test_nonconvex_and_negative_numerator_are_rejected():
    with pytest.raises(ValueError, match="convex"):
        dupire_local_vol(lambda k, t: -k * k, 100, 1, 0, strike_step=0.1, maturity_step=0.01)
    with pytest.raises(ValueError, match="positive"):
        dupire_local_vol(
            lambda k, t: (k - 100) ** 2 - 1000 * t, 100, 1, 0, strike_step=0.1, maturity_step=0.01
        )
