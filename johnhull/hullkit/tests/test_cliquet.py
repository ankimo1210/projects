"""Payment, reset and boundary contracts for Hull GE §26.6 simple cliquets."""

import importlib

import numpy as np
import pytest


def price(kind, *args, **kwargs):
    return getattr(importlib.import_module("hullkit.cliquet"), "cliquet_" + kind)(*args, **kwargs)


@pytest.mark.parametrize("kind,pin", [("call", 10.450583572185565), ("put", 5.573526022256971)])
def test_single_period_is_vanilla(kind, pin):
    actual = price(kind, 100, 0.05, 0.2, [1])
    assert isinstance(actual, float)
    assert actual == pytest.approx(pin, abs=1e-12)


@pytest.mark.parametrize("kind,pin", [("call", 17.04933624301734), ("put", 13.262906618476658)])
def test_two_reset_payments_with_yield(kind, pin):
    assert price(kind, 100, 0.05, 0.2, [1, 2], 0.03) == pytest.approx(pin, abs=1e-12)


@pytest.mark.parametrize("kind,pin", [("call", 23.13079843552097), ("put", 19.303218010187763)])
def test_irregular_schedule_discounts_each_payment(kind, pin):
    assert price(kind, 100, 0.05, 0.2, [0.2, 0.7, 1.4, 2], 0.03) == pytest.approx(pin, abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_broadcast_market_and_mixed_deterministic_limits(kind):
    actual = price(kind, [50, 100, 150], 0.05, [[0.2], [0]], [1, 2], 0.03)
    stochastic = 17.04933624301734 if kind == "call" else 13.262906618476658
    deterministic = 3.7864296245407036 if kind == "call" else 0
    np.testing.assert_allclose(
        actual,
        [np.array([0.5, 1, 1.5]) * stochastic, np.array([0.5, 1, 1.5]) * deterministic],
        atol=1e-12,
    )
    assert actual.shape == (2, 3)
    assert price("call", 100, 0.01, 0, [1, 2], 0.05) == 0
    assert price("put", 100, 0.01, 0, [1, 2], 0.05) > 0


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize(
    "schedule",
    [
        [],
        1,
        [[1, 2]],
        [0, 1],
        [-1, 2],
        [1, 1],
        [2, 1],
        [1, np.nan],
        [1, np.inf],
        [1 + 2j],
        np.array([1 + 2j], dtype=object),
        [10**400],
    ],
)
def test_invalid_schedule(kind, schedule):
    with pytest.raises(ValueError):
        price(kind, 100, 0.05, 0.2, schedule)


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize(
    "field,bad",
    [
        ("S", 0),
        ("S", -1),
        ("S", np.inf),
        ("sigma", -0.1),
        ("sigma", np.nan),
        ("r", np.inf),
        ("q", np.nan),
        ("S", 1 + 2j),
        ("S", np.array([1 + 2j], dtype=object)),
        ("S", object()),
        ("S", 10**400),
    ],
)
def test_invalid_market(kind, field, bad):
    market = dict(S=100, r=0.05, sigma=0.2, payment_times=[1, 2], q=0.03)
    market[field] = bad
    with pytest.raises(ValueError):
        price(kind, **market)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_shapes_and_overflow_raise_value_error(kind):
    with pytest.raises(ValueError):
        price(kind, [100, 120], 0.05, [0.1, 0.2, 0.3], [1, 2])
    with pytest.raises(ValueError):
        price(
            kind,
            1e308,
            0.05 if kind == "call" else -100,
            0.2,
            [1, 2],
            -100 if kind == "call" else 0.03,
        )
    with pytest.raises(ValueError):
        price(kind, 1e308, 0, 2, [1, 2, 3, 4])
