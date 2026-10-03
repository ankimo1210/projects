"""Independent prices catch missing dividend scaling, timing and boundary errors."""

import importlib
import math

import numpy as np
import pytest

MARKET = dict(S=100, K=100, r=0.05, sigma=0.2, T1=0.5, T2=1, q=0.02)


def api():
    return importlib.import_module("hullkit.chooser").chooser_price


@pytest.mark.parametrize(
    "t1,pin",
    [
        (0.1, 10.483695744000126),
        (0.5, 13.344280448069238),
        (0.9, 15.168232237397923),
        (0.999999, 15.55708234558728),
    ],
)
def test_independent_conditional_integral_prices(t1, pin):
    result = api()(**{**MARKET, "T1": t1})
    assert isinstance(result, float)
    assert result == pytest.approx(pin, abs=1e-9)


@pytest.mark.parametrize("q", [0, 0.02, -0.03])
@pytest.mark.parametrize("r", [-0.02, 0.05])
def test_endpoints_bounds_homogeneity_and_decision_monotonicity(q, r):
    from hullkit import bsm

    m = {**MARKET, "q": q, "r": r}
    c = bsm.call_price(100, 100, r, 0.2, 1, q)
    p = bsm.put_price(100, 100, r, 0.2, 1, q)
    prices = api()(**{**m, "T1": np.linspace(0, 1, 21)})
    assert prices[0] == pytest.approx(max(c, p), abs=1e-12)
    assert prices[-1] == pytest.approx(c + p, abs=1e-12)
    assert np.all(np.diff(prices) >= -1e-12)
    assert np.all(prices >= max(c, p) - 1e-12)
    assert np.all(prices <= c + p + 1e-12)
    assert api()(**{**m, "S": 170, "K": 170}) == pytest.approx(1.7 * api()(**m), abs=1e-10)


def test_deterministic_and_zero_maturity_mixed_broadcast():
    from hullkit import bsm

    m = {**MARKET, "S": np.array([[80], [120]]), "T1": [0, 0.5, 1], "sigma": [0.2, 0, 0.2]}
    values = api()(**m)
    assert values.shape == (2, 3)
    for i, s in enumerate((80, 120)):
        c = bsm.call_price(s, 100, 0.05, 0, 1, 0.02)
        p = bsm.put_price(s, 100, 0.05, 0, 1, 0.02)
        assert values[i, 1] == pytest.approx(max(c, p), abs=1e-12)
        for j, t in enumerate((0, 0.5, 1)):
            assert values[i, j] == pytest.approx(
                api()(**{**MARKET, "S": s, "T1": t, "sigma": (0.2, 0, 0.2)[j]})
            )
    assert api()(**{**MARKET, "S": 80, "T1": 0, "T2": 0}) == 20
    assert api()(**{**MARKET, "S": np.array([])}).shape == (0,)


@pytest.mark.parametrize(
    "field,value",
    [
        ("S", 0),
        ("K", -1),
        ("sigma", -0.1),
        ("T1", -0.01),
        ("T1", 1.01),
        ("T2", -0.1),
        ("q", float("nan")),
        ("r", float("inf")),
        ("S", 1j),
        ("K", np.array([1 + 1j], dtype=object)),
        ("K", 10**1000),
        ("q", -10000),
        ("r", -10000),
    ],
)
def test_invalid_or_unrepresentable_inputs_are_rejected(field, value):
    with pytest.raises(ValueError):
        api()(**{**MARKET, field: value})


def test_incompatible_broadcast_is_rejected():
    with pytest.raises(ValueError):
        api()(**{**MARKET, "S": [80, 90], "K": [80, 100, 120]})


def test_representable_large_positive_rate_limit():
    assert api()(**{**MARKET, "r": 10000}) == pytest.approx(100 * math.exp(-0.02), abs=1e-10)
