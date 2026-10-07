"""Hull 19 appendix: spot/IV Taylor terms and independent mixed sensitivities."""

import math

import pytest
from hullkit import _greeks_hedging as greeks
from scipy.integrate import quad
from scipy.stats import norm


def density(spot, strike, rate, sigma, time, kind, yield_rate=0):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-11,
        )[0]
    )


def pathwise(spot, strike, rate, sigma, time, kind, yield_rate, parameter):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    boundary = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (boundary, 12) if kind == "call" else (-12, boundary)

    def integrand(z):
        terminal = math.exp(mean + width * z)
        tangent = (
            terminal / spot
            if parameter == "spot"
            else terminal * (math.sqrt(time) * z - sigma * time)
        )
        return sign * tangent * norm.pdf(z)

    return math.exp(-rate * time) * quad(integrand, low, high, epsabs=1e-11)[0]


def test_taylor_all_terms_cross_coefficient_and_absolute_iv_units():
    result = greeks.taylor_pnl(
        0.6, 0.02, -5, 2, 0.01, vega=12, vol_change=0.03, vanna=0.4, vomma=-8
    )
    assert [
        result[key] for key in ["delta", "gamma", "theta", "vega", "vanna", "vomma", "total"]
    ] == pytest.approx([1.2, 0.04, -0.05, 0.36, 0.024, -0.0036, 1.5704], abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_vanna_two_pathwise_derivative_orders_and_vomma_payoff_price_difference(kind):
    s, k, r, sig, t, q = 49, 50, 0.05, 0.2, 0.3846, 0.03
    result = greeks.option_greek_details(s, k, r, sig, t, kind=kind, yield_rate=q)
    dv, ds = 1e-5, 0.005
    delta_vol = (
        pathwise(s, k, r, sig + dv, t, kind, q, "spot")
        - pathwise(s, k, r, sig - dv, t, kind, q, "spot")
    ) / (2 * dv)
    vega_spot = (
        pathwise(s + ds, k, r, sig, t, kind, q, "vol")
        - pathwise(s - ds, k, r, sig, t, kind, q, "vol")
    ) / (2 * ds)
    assert result["vanna"] == pytest.approx(delta_vol, abs=3e-8)
    assert result["vanna"] == pytest.approx(vega_spot, abs=1e-7)
    hv = 0.0001
    vomma = (
        density(s, k, r, sig + hv, t, kind, q)
        - 2 * density(s, k, r, sig, t, kind, q)
        + density(s, k, r, sig - hv, t, kind, q)
    ) / hv**2
    assert result["vomma"] == pytest.approx(vomma, abs=3e-6)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_full_repricing_residual_shrinks_cubically_with_joint_spot_iv_and_time_shocks(kind):
    s, k, r, sig, t, q = 49, 50, 0.05, 0.2, 0.3846, 0.03
    risk = greeks.option_greek_details(s, k, r, sig, t, kind=kind, yield_rate=q)
    base = density(s, k, r, sig, t, kind, q)
    errors = []
    for scale in [1, 0.5, 0.25]:
        ds, dv, dt = scale, 0.01 * scale, 0.001 * scale**2
        exact = density(s + ds, k, r, sig + dv, t - dt, kind, q) - base
        prediction = greeks.taylor_pnl(
            risk["delta"],
            risk["gamma"],
            risk["theta"],
            ds,
            dt,
            vega=risk["vega"],
            vol_change=dv,
            vanna=risk["vanna"],
            vomma=risk["vomma"],
        )["total"]
        errors.append(abs(exact - prediction))
    assert errors[0] / errors[1] > 6
    assert errors[1] / errors[2] > 6


def test_spot_squared_and_calendar_time_terms_both_scale_as_elapsed_years():
    previous = None
    for dt in [0.04, 0.01, 0.0025]:
        result = greeks.taylor_pnl(0, -10000, 400, 0.2 * math.sqrt(dt), dt)
        assert result["gamma"] == pytest.approx(-200 * dt, abs=1e-12)
        assert result["theta"] == pytest.approx(400 * dt, abs=1e-12)
        if previous is not None:
            assert previous / result["total"] == pytest.approx(4, abs=1e-12)
        previous = result["total"]


def test_negative_elapsed_time_has_no_calendar_pnl_interpretation():
    with pytest.raises(ValueError):
        greeks.taylor_pnl(0, 1, -1, 1, -0.01, vol_change=0.01)
