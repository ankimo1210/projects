"""Public moment-matched basket-option pricing contracts (Hull §26.15)."""

import json
import math
from pathlib import Path

import numpy as np
import pytest
from hullkit import bsm, exotics


def test_basket_pricing_public_api_is_importable():
    """Removing either public basket function breaks the public pricing contract."""
    assert callable(exotics.basket_moments)
    assert callable(exotics.basket_option_price)


def test_single_asset_basket_is_bsm():
    """A one-asset basket must retain the exact Black-Scholes-Merton price."""
    got = exotics.basket_option_price([100.0], [1.0], 100.0, 0.05, [0.02], [0.2], [[1.0]], 1.0)
    assert got == pytest.approx(bsm.call_price(100.0, 100.0, 0.05, 0.2, 1.0, q=0.02), rel=0.0, abs=1e-11)


def test_two_asset_moments_match_direct_sum():
    """Dropping cross terms from the second basket moment changes this result."""
    got = exotics.basket_moments(
        [100.0, 80.0], [0.6, 0.5], 0.03, [0.01, 0.025], [0.2, 0.3], [[1.0, 0.35], [0.35, 1.0]], 1.0
    )
    f1 = 60.0 * math.exp(0.02)
    f2 = 40.0 * math.exp(0.005)
    want_m1 = f1 + f2
    want_m2 = f1 * f1 * math.exp(0.04) + 2.0 * f1 * f2 * math.exp(0.021) + f2 * f2 * math.exp(0.09)
    assert got == pytest.approx((want_m1, want_m2), rel=0.0, abs=1e-12)


def test_three_asset_moments_match_direct_sum():
    """A three-asset basket must include every ordered covariance term."""
    spots = [90.0, 110.0, 70.0]
    weights = [0.5, 0.25, 0.8]
    rate = 0.01
    dividends = [0.0, 0.02, 0.01]
    volatilities = [0.15, 0.25, 0.35]
    correlations = [[1.0, -0.2, 0.4], [-0.2, 1.0, 0.1], [0.4, 0.1, 1.0]]
    expiry = 1.5
    forwards = [
        weight * spot * math.exp((rate - dividend) * expiry)
        for spot, weight, dividend in zip(spots, weights, dividends, strict=True)
    ]
    want = (
        sum(forwards),
        sum(
            forwards[i]
            * forwards[j]
            * math.exp(correlations[i][j] * volatilities[i] * volatilities[j] * expiry)
            for i in range(3)
            for j in range(3)
        ),
    )
    got = exotics.basket_moments(spots, weights, rate, dividends, volatilities, correlations, expiry)
    assert got == pytest.approx(want, rel=0.0, abs=1e-12)


def test_saved_two_asset_moment_match_prices_are_reproduced():
    """A change to the lognormal proxy no longer reproduces frozen M7a prices."""
    root = Path(__file__).resolve().parents[2] / "docs" / "validation" / "section-26-15"
    rows = json.loads((root / "prices.json").read_text())["rows"]
    cases = [row for row in rows if len(row["spots"]) == 2 and row["kind"] == "call" and row["anchor"] is None]
    assert len(cases) == 18
    for row in cases:
        got = exotics.basket_option_price(
            row["spots"], row["weights"], row["K"], row["r"], row["dividends"], row["volatilities"],
            row["correlation"], row["T"], row["kind"]
        )
        assert got == pytest.approx(row["approximation"], rel=0.0, abs=1e-11), (row["market"], row["K"])


def test_call_put_parity_uses_the_exact_first_moment():
    """Pricing put through a separate approximation can violate basket parity."""
    args = ([100.0, 80.0], [0.6, 0.5], 100.0, 0.03, [0.01, 0.025], [0.2, 0.3], [[1.0, 0.35], [0.35, 1.0]], 1.0)
    call = exotics.basket_option_price(*args, kind="call")
    put = exotics.basket_option_price(*args, kind="put")
    m1, _ = exotics.basket_moments(args[0], args[1], args[3], args[4], args[5], args[6], args[7])
    assert call - put == pytest.approx(math.exp(-args[3] * args[7]) * (m1 - args[2]), rel=0.0, abs=1e-12)


def test_proportional_perfectly_correlated_basket_is_bsm():
    """A rho=1 proportional basket remains a single exact lognormal asset."""
    got = exotics.basket_option_price(
        [100.0, 80.0], [0.6, 0.5], 100.0, 0.04, [0.02, 0.02], [0.25, 0.25], [[1.0, 1.0], [1.0, 1.0]], 1.0
    )
    assert got == pytest.approx(bsm.call_price(100.0, 100.0, 0.04, 0.25, 1.0, q=0.02), rel=0.0, abs=1e-11)


@pytest.mark.parametrize("kind, expected", [("call", 0.0), ("put", 5.0)])
def test_zero_matched_variance_prices_the_deterministic_basket(kind, expected):
    """A zero proxy variance must not divide by zero or create NaN prices."""
    got = exotics.basket_option_price([100.0], [1.0], 105.0, 0.0, [0.0], [0.0], [[1.0]], 1.0, kind)
    assert got == pytest.approx(expected, rel=0.0, abs=1e-12)


@pytest.mark.parametrize(
    "args",
    [
        ([100.0], [1.0, 0.0], 100.0, 0.01, [0.0], [0.2], [[1.0]], 1.0),
        ([100.0], [0.0], 100.0, 0.01, [0.0], [0.2], [[1.0]], 1.0),
        ([100.0], [1.0], 0.0, 0.01, [0.0], [0.2], [[1.0]], 1.0),
        ([100.0], [1.0], 100.0, math.nan, [0.0], [0.2], [[1.0]], 1.0),
        ([100.0, 80.0], [0.5, 0.5], 100.0, 0.01, [0.0, 0.0], [0.2, 0.3], [[1.0, 0.2], [0.1, 1.0]], 1.0),
        ([100.0, 80.0], [0.5, 0.5], 100.0, 0.01, [0.0, 0.0], [0.2, 0.3], [[1.0, 1.2], [1.2, 1.0]], 1.0),
    ],
)
def test_invalid_basket_contracts_raise_value_error(args):
    """Malformed, nonfinite, or non-PSD basket inputs must not be repriced silently."""
    with pytest.raises(ValueError):
        exotics.basket_option_price(*args)


def test_invalid_option_kind_raises_value_error():
    """Unsupported payoff kinds must not be treated as puts."""
    with pytest.raises(ValueError, match="kind"):
        exotics.basket_option_price([100.0], [1.0], 100.0, 0.01, [0.0], [0.2], [[1.0]], 1.0, "digital")


def test_tiny_nonzero_basket_variance_is_not_treated_as_deterministic():
    """A small but real diffusion must retain its Black-Scholes time value."""
    got = exotics.basket_option_price([1e8], [1.0], 1e8, 0.0, [0.0], [1e-7], [[1.0]], 1.0)
    expected = bsm.call_price(1e8, 1e8, 0.0, 1e-7, 1.0)
    assert got == pytest.approx(expected, rel=0.0, abs=1e-9)


def test_complex_nan_component_is_rejected_before_float_conversion():
    """Casting complex inputs must not silently discard a nonfinite imaginary component."""
    with pytest.raises(ValueError, match="real"):
        exotics.basket_moments(
            np.array([complex(100.0, float("nan"))]), [1.0], 0.0, [0.0], [0.2], [[1.0]], 1.0
        )


def test_zero_weight_asset_does_not_overflow_moment_calculation():
    """A zero holding cannot make an otherwise valid one-asset basket overflow."""
    got = exotics.basket_option_price(
        [100.0, 100.0], [1.0, 0.0], 100.0, 0.0, [0.0, 0.0], [0.2, 100.0], [[1.0, 0.0], [0.0, 1.0]], 1.0
    )
    assert got == pytest.approx(bsm.call_price(100.0, 100.0, 0.0, 0.2, 1.0), rel=0.0, abs=1e-12)
