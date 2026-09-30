"""Contract and boundary behavior for Hull GE §26.5 ATM forward-start calls."""

import importlib
import math

import numpy as np
import pytest


def price(*args, **kwargs):
    module = importlib.import_module("hullkit.forward_start")
    return module.forward_start_call(*args, **kwargs)


def test_immediate_start_matches_vanilla_numeric_pin():
    assert price(100, 0.05, 0.2, 0, 1) == pytest.approx(10.450583572185565, abs=1e-12)


def test_dividend_discount_and_remaining_tenor_numeric_pin():
    # c=8.652528553942709 for a one-year ATM call, then exp(-0.03).
    assert price(100, 0.05, 0.2, 1, 2, 0.03) == pytest.approx(8.396807689074635, abs=1e-12)


def test_zero_yield_delay_keeps_same_option_life():
    for start in (0, 0.25, 1, 3):
        assert price(100, 0.05, 0.2, start, start + 1) == pytest.approx(
            10.450583572185565, abs=1e-12
        )


def test_spot_homogeneity_and_broadcasted_yields():
    actual = price([50, 100, 150], 0.05, 0.2, 1, 2, [[0], [0.03]])
    np.testing.assert_allclose(
        actual,
        [
            [5.2252917860927825, 10.450583572185565, 15.675875358278348],
            [4.1984038445373175, 8.396807689074635, 12.595211533611952],
        ],
        rtol=1e-13,
    )
    assert actual.shape == (2, 3)


def test_mixed_zero_volatility_and_zero_length_contracts():
    actual = price(100, 0.05, [0.2, 0, 0.2], [1, 1, 2], [2, 2, 2], [0.03, 0.02, -1000])
    np.testing.assert_allclose(actual, [8.396807689074635, 2.8395619246375, 0], atol=1e-12)
    assert price(100, 1e308, 1e308, 1e308, 1e308, -1e308) == 0
    assert price(100, 0.01, 0, 1, 2, 0.05) == 0


@pytest.mark.parametrize(
    "field,bad",
    [
        ("S", 0),
        ("S", -1),
        ("S", math.inf),
        ("S", complex(1, 2)),
        ("r", math.nan),
        ("q", math.inf),
        ("sigma", -0.1),
        ("sigma", math.nan),
        ("T1", -1),
        ("T1", 3),
        ("T2", -1),
        ("T2", math.inf),
    ],
)
def test_invalid_market_element_is_rejected(field, bad):
    market = dict(S=100, r=0.05, sigma=0.2, T1=1, T2=2, q=0.03)
    market[field] = [market[field], bad]
    with pytest.raises(ValueError):
        price(**market)


def test_incompatible_shapes_are_rejected():
    with pytest.raises(ValueError):
        price([100, 120], 0.05, [0.1, 0.2, 0.3], 1, 2)


def test_unrepresentable_price_is_rejected_without_warning():
    with pytest.raises(ValueError):
        price(1e308, 0.05, 0.2, 1, 2, -100)


@pytest.mark.parametrize(
    "spot",
    [np.array([1 + 2j], dtype=object), object(), 10**400],
    ids=["object-complex", "nonreal-object", "huge-integer"],
)
def test_nonreal_or_unrepresentable_spot_raises_value_error(spot):
    with pytest.raises(ValueError):
        price(spot, 0.05, 0.2, 1, 2)
