"""Four European options on options, thresholds and contract limits."""

import importlib
import math

import numpy as np
import pytest

KINDS = ("call_on_call", "put_on_call", "call_on_put", "put_on_put")
MARKET = dict(S=100, K1=10, K2=100, r=0.05, sigma=0.2, T1=0.5, T2=1, q=0.02)
PINS = (3.2568270197744167, 3.7829206319036883, 1.299803100157501, 4.722821592890913)


def module():
    return importlib.import_module("hullkit.compound")


@pytest.mark.parametrize("kind,expected", zip(KINDS, PINS, strict=True))
def test_four_independently_integrated_prices(kind, expected):
    result = module().compound_price(**MARKET, kind=kind)
    assert isinstance(result, float)
    assert result == pytest.approx(expected, abs=1e-9)
    assert result == module().compound_price(**MARKET, kind=kind)


@pytest.mark.parametrize(
    "inner,expected", [("call", 105.77296228027585), ("put", 90.73021992506433)]
)
def test_critical_spot_solves_inner_value(inner, expected):
    from hullkit import bsm

    root = module()._critical_spot(10, 100, 0.05, 0.2, 0.5, 0.02, inner)
    assert root == pytest.approx(expected, abs=1e-9)
    price = getattr(bsm, inner + "_price")(root, 100, 0.05, 0.2, 0.5, 0.02)
    assert price == pytest.approx(10, abs=1e-9)


@pytest.mark.parametrize("inner", ["call", "put"])
def test_compound_parity_and_currency_homogeneity(inner):
    from hullkit import bsm

    api = module().compound_price
    call = api(**MARKET, kind="call_on_" + inner)
    put = api(**MARKET, kind="put_on_" + inner)
    plain = getattr(bsm, inner + "_price")(100, 100, 0.05, 0.2, 1, 0.02)
    assert call - put == pytest.approx(plain - 10 * math.exp(-0.05 * 0.5), abs=1e-9)
    scaled = {**MARKET, "S": 170, "K1": 17, "K2": 170}
    assert api(**scaled, kind="call_on_" + inner) == pytest.approx(1.7 * call, abs=1e-9)


@pytest.mark.parametrize("kind", KINDS)
def test_zero_outer_strike_and_deterministic_volatility(kind):
    from hullkit import bsm

    outer, inner = kind.split("_on_")
    plain = getattr(bsm, inner + "_price")(100, 100, 0.05, 0.2, 1, 0.02)
    assert module().compound_price(**{**MARKET, "K1": 0}, kind=kind) == pytest.approx(
        plain if outer == "call" else 0
    )
    s1 = 100 * math.exp(0.03 * 0.5)
    inner1 = max((100 * math.exp(0.03) - 100) * (1 if inner == "call" else -1), 0) * math.exp(
        -0.05 * 0.5
    )
    assert s1 > 100
    payoff = max(inner1 - 10, 0) if outer == "call" else max(10 - inner1, 0)
    assert module().compound_price(**{**MARKET, "sigma": 0}, kind=kind) == pytest.approx(
        payoff * math.exp(-0.05 * 0.5), abs=1e-12
    )


@pytest.mark.parametrize("factor", [1, 1.00001, 2])
def test_inner_put_bound_has_no_finite_root(factor):
    from hullkit import bsm

    strike = factor * 100 * math.exp(-0.05 * 0.5)
    market = {**MARKET, "K1": strike}
    assert module()._critical_spot(strike, 100, 0.05, 0.2, 0.5, 0.02, "put") is None
    assert module().compound_price(**market, kind="call_on_put") == 0
    expected = strike * math.exp(-0.05 * 0.5) - bsm.put_price(100, 100, 0.05, 0.2, 1, 0.02)
    assert module().compound_price(**market, kind="put_on_put") == pytest.approx(
        expected, abs=1e-10
    )


def test_market_broadcast_with_mixed_boundaries():
    api = module().compound_price
    market = {
        **MARKET,
        "S": np.array([[80], [100]]),
        "K1": np.array([0, 10, 110]),
        "sigma": np.array([0, 0.2, 0.2]),
    }
    values = api(**market, kind="put_on_put")
    assert values.shape == (2, 3)
    assert values[:, 0].tolist() == [0, 0]
    for i, s in enumerate((80, 100)):
        for j, k in enumerate((0, 10, 110)):
            assert values[i, j] == pytest.approx(
                api(**{**MARKET, "S": s, "K1": k, "sigma": (0, 0.2, 0.2)[j]}, kind="put_on_put"),
                abs=1e-10,
            )


@pytest.mark.parametrize("rho", [-0.99999, -0.7, 0, 0.7, 0.99999])
def test_bivariate_zero_threshold_identity(rho):
    assert module()._bivariate_normal(0, 0, rho) == pytest.approx(
        0.25 + math.asin(rho) / (2 * math.pi), abs=1e-12
    )


def test_first_exercise_near_second_date_is_finite():
    for kind in KINDS:
        actual = module().compound_price(**{**MARKET, "T1": 0.9999}, kind=kind)
        assert math.isfinite(actual) and actual >= 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("S", 0),
        ("S", -1),
        ("K1", -1),
        ("K2", 0),
        ("sigma", -0.1),
        ("T1", 0),
        ("T1", 1),
        ("T2", 0.5),
        ("S", float("nan")),
        ("r", float("inf")),
        ("q", float("-inf")),
        ("sigma", 1j),
        ("S", np.array([1 + 1j], dtype=object)),
        ("K1", 10**1000),
        ("r", -10000),
        ("q", -10000),
    ],
)
def test_invalid_or_unrepresentable_market_is_rejected(field, value):
    with pytest.raises(ValueError):
        module().compound_price(**{**MARKET, field: value})


@pytest.mark.parametrize("kind", ["call", "Call_on_call", None, [], 1])
def test_invalid_contract_kind_is_rejected(kind):
    with pytest.raises(ValueError):
        module().compound_price(**MARKET, kind=kind)


def test_incompatible_broadcast_is_rejected():
    with pytest.raises(ValueError):
        module().compound_price(**{**MARKET, "S": [80, 90], "K1": [5, 10, 20]})


def test_large_positive_rate_has_a_representable_limit():
    assert module().compound_price(**{**MARKET, "r": 10000}) == pytest.approx(
        100 * math.exp(-0.02), abs=1e-10
    )
