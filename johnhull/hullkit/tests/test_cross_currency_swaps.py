import importlib
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._cross_currency_swaps")


def test_currency_spot_leg_value_cip_forward_conversion_and_reversal():
    m = model()
    ts = np.array([1, 2, 3])
    pd = np.exp(-0.04 * ts)
    pf = np.exp(-0.03 * ts)
    cd = np.array([4.5, 4.5, 104.5])
    cf = np.array([2, 2, 82])
    spot = 1.25
    result = m.currency_leg_value(float(cd @ pd), float(cf @ pf), spot)
    fx = m.cip_fx_forward(spot, pd, pf)
    independent = float(cd @ pd - (cf * fx) @ pd)
    assert result == pytest.approx(independent, abs=1e-12)
    assert m.currency_leg_value(float(cf @ pf), float(cd @ pd), 1 / spot) == pytest.approx(
        -result / spot, abs=1e-12
    )
    assert m.currency_leg_value(100, 80, spot) == pytest.approx(0, abs=1e-12)


def test_fair_foreign_coupon_spread_calibration_is_explicit_not_value_clipping():
    m = model()
    times = np.array([1, 2, 3])
    pd = np.exp(-0.04 * times)
    pf = np.exp(-0.03 * times)
    domestic = float(np.array([4.5, 4.5, 104.5]) @ pd)
    foreign = float(np.array([2, 2, 82]) @ pf)
    spot = 1.25
    annuity = 80 * pf.sum()
    spread = m.fair_foreign_coupon_spread(domestic, foreign, annuity, spot)
    assert abs(m.currency_leg_value(domestic, foreign, spot)) > 0.01
    repriced = foreign + spread * annuity
    assert m.currency_leg_value(domestic, repriced, spot) == pytest.approx(0, abs=1e-12)


def params():
    return dict(
        notional=1e6,
        accrual=0.5,
        forward_rate=0.05,
        value_volatility=0.2,
        fixing=2.0,
        payment=3.0,
        payment_discount=0.9,
        first=-4.0,
        second=20.0,
        rate_volatility=0.15,
        timing_correlation=0.3,
        quanto_fx_volatility=0.12,
        quanto_correlation=-0.25,
        rate_frequency=1,
    )


def test_cms_convexity_timing_quanto_components_and_zero_limits():
    m = model()
    p = params()
    row = m.adjusted_rate_coupon(**p)
    conv = 0.05 - 0.5 * 0.05**2 * 0.2**2 * 2 * 20 / (-4)
    signed = -0.15 * 0.05 * (3 - 2) / (1 + 0.05)
    timing = math.exp(0.3 * 0.2 * signed * 2)
    quanto = math.exp(-0.25 * 0.2 * 0.12 * 2)
    assert row["convexity_adjusted_forward"] == pytest.approx(conv, abs=1e-14)
    assert row["timing_factor"] == pytest.approx(timing, abs=1e-14)
    assert row["quanto_factor"] == pytest.approx(quanto, abs=1e-14)
    assert row["pv"] == pytest.approx(1e6 * 0.5 * 0.9 * conv * timing * quanto, abs=1e-9)
    zero = m.adjusted_rate_coupon(**dict(p, value_volatility=0))
    assert zero["pv"] == pytest.approx(1e6 * 0.5 * 0.9 * 0.05, abs=1e-10)
    cor0 = m.adjusted_rate_coupon(**dict(p, timing_correlation=0, quanto_correlation=0))
    assert cor0["pv"] == pytest.approx(1e6 * 0.5 * 0.9 * conv, abs=1e-9)


def test_combined_frozen_timing_and_quanto_matches_independent_normalized_gaussian_tilt():
    m = model()
    p = params()
    p.update(second=0)
    row = m.adjusted_rate_coupon(**p)
    T = p["fixing"]
    sv = p["value_volatility"]
    loading = (
        -p["rate_volatility"] * p["forward_rate"] * (p["payment"] - T) / (1 + p["forward_rate"])
    )
    # Only the projection of the normalized combined ratio on the value
    # driver remains after integrating the other independent Gaussian drivers.
    projected = (
        p["timing_correlation"] * loading + p["quanto_correlation"] * p["quanto_fx_volatility"]
    )
    expectation = quad(
        lambda z: (
            p["forward_rate"]
            * math.exp(-0.5 * sv * sv * T + sv * math.sqrt(T) * z)
            * math.exp(projected * math.sqrt(T) * z - 0.5 * projected**2 * T)
            * norm.pdf(z)
        ),
        -12,
        12,
        epsabs=1e-13,
    )[0]
    assert row["pv"] == pytest.approx(
        p["notional"] * p["accrual"] * p["payment_discount"] * expectation, abs=1e-8
    )


def test_math_domains():
    m = model()
    with pytest.raises(ValueError):
        m.cip_fx_forward(0, 0.9, 0.9)
    with pytest.raises(ValueError):
        m.fair_foreign_coupon_spread(1, 1, 0, 1)
    with pytest.raises(ValueError):
        m.adjusted_rate_coupon(**dict(params(), payment=1))
