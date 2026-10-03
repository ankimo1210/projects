"""Printed examples and signed one-factor risk loading contracts."""

import importlib

import numpy as np
import pytest


def api(name):
    return getattr(importlib.import_module("hullkit.risk_premium"), name)


@pytest.mark.parametrize(
    "mu,r,s,pin",
    [
        (0.12, 0.08, 0.2, 0.2),
        (0.03, 0.06, 0.2, -0.15),
        (0.015, 0.06, 0.3, -0.15),
        (0.105, 0.06, -0.3, -0.15),
        (-0.01, 0.04, -0.2, 0.25),
    ],
)
def test_printed_and_signed_loading_pins(mu, r, s, pin):
    value = api("market_price_of_risk")(mu, r, s)
    assert isinstance(value, float)
    assert value == pytest.approx(pin, abs=1e-14)
    assert api("required_return")(r, pin, s) == pytest.approx(mu, abs=1e-14)


def test_broadcast_coordinate_reversal_and_real_objects():
    r = np.array([[0.06], [-0.02]], dtype=object)
    lam = np.array([-0.15, 0.2, 0])
    s = np.array([-0.3, 0.2, 0.1], dtype=object)
    mu = api("required_return")(r, lam, s)
    assert mu.shape == (2, 3)
    assert np.allclose(mu, np.asarray(r, float) + lam * np.asarray(s, float))
    assert np.allclose(api("market_price_of_risk")(mu, r, s), np.broadcast_to(lam, mu.shape))
    assert np.array_equal(mu, api("required_return")(r, -lam, -s))
    assert np.allclose(api("market_price_of_risk")(mu, r, -s), -lam)


def test_zero_loading_is_unidentifiable_but_required_return_is_r():
    with pytest.raises(ValueError):
        api("market_price_of_risk")(0.06, 0.06, 0)
    assert api("required_return")(0.06, 0.2, 0) == 0.06
    with pytest.raises(ValueError):
        api("market_price_of_risk")([], 0.06, 0)
    assert api("market_price_of_risk")([], 0.06, 0.2).shape == (0,)
    assert api("required_return")(0.06, [], 0).shape == (0,)


@pytest.mark.parametrize("name", ["market_price_of_risk", "required_return"])
@pytest.mark.parametrize("field", range(3))
@pytest.mark.parametrize(
    "invalid",
    [
        np.nan,
        np.inf,
        1j,
        np.array([np.complex64(1 + 2j)], object),
        np.array(np.complex128(1 + 0j), object),
        10**1000,
    ],
)
def test_invalid_real_inputs_are_rejected(name, field, invalid):
    args = [0.12, 0.08, 0.2]
    args[field] = invalid
    with pytest.raises(ValueError):
        api(name)(*args)


@pytest.mark.parametrize("name", ["market_price_of_risk", "required_return"])
def test_invalid_values_do_not_disappear_in_empty_batches(name):
    with pytest.raises(ValueError):
        api(name)([], 0.06, np.nan)
    with pytest.raises(ValueError):
        api(name)([], 0.06, np.array([np.complex128(0.2 + 1j)], object))
    with pytest.raises(ValueError):
        api(name)([1, 2], [1, 2, 3], 0.2)


@pytest.mark.parametrize(
    "name,args",
    [
        ("market_price_of_risk", [1, 0, 5e-324]),
        ("market_price_of_risk", [-1e308, 1e308, 1]),
        ("required_return", [0, 1e308, 10]),
    ],
)
def test_unrepresentable_calculations_are_rejected(name, args):
    with pytest.raises(ValueError):
        api(name)(*args)
