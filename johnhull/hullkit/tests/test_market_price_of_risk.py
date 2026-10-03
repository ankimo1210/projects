"""Signed loadings, a common lambda and the riskless two-derivative portfolio (§28.1)."""

import numpy as np
import pytest
from hullkit import bsm
from hullkit.market_price_of_risk import (
    ito_growth_and_loading,
    market_price_of_risk,
    required_growth,
    riskless_holdings,
)


def test_printed_examples_28_1_and_28_2():
    assert market_price_of_risk(0.12, 0.2, 0.08) == pytest.approx(0.2, abs=1e-12)
    lam = market_price_of_risk(0.03, 0.2, 0.06)
    assert lam == pytest.approx(-0.15, abs=1e-12)
    assert required_growth(0.06, lam, 0.3) == pytest.approx(0.015, abs=1e-12)


def test_negative_loading_and_broadcast():
    # A claim that falls when u rises has s < 0; with lambda > 0 it grows below r.
    assert required_growth(0.05, 0.35, -1.3) == pytest.approx(0.05 - 0.455)
    out = market_price_of_risk(np.array([0.12, -0.0]), np.array([0.2, -0.1]), 0.05)
    assert isinstance(out, np.ndarray) and out == pytest.approx([0.35, 0.5])
    assert isinstance(market_price_of_risk(0.12, 0.2, 0.05), float)


def test_ito_growth_matches_common_lambda_for_calls_and_puts():
    s, k, r, sigma, t, mu = 100.0, 105.0, 0.05, 0.2, 0.75, 0.12
    for price, theta, delta in (
        (bsm.call_price, bsm.call_theta, bsm.call_delta),
        (bsm.put_price, bsm.put_theta, bsm.put_delta),
    ):
        growth, loading = ito_growth_and_loading(
            price(s, k, r, sigma, t),
            theta(s, k, r, sigma, t),
            delta(s, k, r, sigma, t),
            bsm.gamma(s, k, r, sigma, t),
            s,
            mu,
            sigma,
        )
        assert market_price_of_risk(growth, loading, r) == pytest.approx(0.35, abs=1e-12)
    assert loading < 0  # the put's loading is signed; its volatility is |s|


def test_riskless_holdings_cancel_dz_and_earn_r():
    f1, s1, f2, s2, r, lam = 10.0, 1.2, 6.0, -1.3, 0.05, 0.35
    m1, m2 = required_growth(r, lam, s1), required_growth(r, lam, s2)
    n1, n2 = riskless_holdings(f1, s1, f2, s2)
    assert (n1, n2) == pytest.approx((s2 * f2, -s1 * f1))
    value = n1 * f1 + n2 * f2
    assert n1 * s1 * f1 + n2 * s2 * f2 == pytest.approx(0, abs=1e-14)
    assert (n1 * m1 * f1 + n2 * m2 * f2) / value == pytest.approx(r, abs=1e-14)


@pytest.mark.parametrize(
    "call",
    [
        lambda: market_price_of_risk(0.1, 0.0, 0.05),
        lambda: market_price_of_risk(np.nan, 0.2, 0.05),
        lambda: market_price_of_risk(0.1, 0.2 + 1j, 0.05),
        lambda: market_price_of_risk(np.array([np.complex128(0.1 + 1j)], dtype=object), 0.2, 0.05),
        lambda: required_growth("x", 0.2, 0.3),
        lambda: required_growth(0.05, 1e308, 1e308),
        lambda: riskless_holdings(0.0, 1.0, 1.0, 2.0),
        lambda: riskless_holdings(1.0, 1.0, 1.0, 1.0),
        lambda: ito_growth_and_loading(-1.0, 0.0, 1.0, 0.0, 100.0, 0.1, 0.2),
        lambda: ito_growth_and_loading(1.0, 0.0, 1.0, 0.0, 0.0, 0.1, 0.2),
    ],
)
def test_invalid_inputs_raise(call):
    with pytest.raises(ValueError):
        call()
