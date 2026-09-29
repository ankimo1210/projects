"""Behavior pins for Hull GE §26.2 perpetual American options."""

import math

import hullkit
import pytest

perpetual_american = getattr(hullkit, "perpetual_american", None)


def test_public_entrypoint_exists():
    assert perpetual_american is not None


MARKET = dict(strike=100.0, r=0.05, sigma=0.20, q=0.03)


def test_continuation_values_match_independent_numeric_pin():
    call = perpetual_american.perpetual_option("call", 100.0, **MARKET)
    put = perpetual_american.perpetual_option("put", 100.0, **MARKET)
    assert call.exponent == pytest.approx(1.5811388300841895, rel=1e-13)
    assert put.exponent == pytest.approx(1.5811388300841895, rel=1e-13)
    assert call.boundary == pytest.approx(272.07592200561265, rel=1e-13)
    assert put.boundary == pytest.approx(61.25741132772069, rel=1e-13)
    assert call.price == pytest.approx(35.352057418829865, rel=1e-13)
    assert put.price == pytest.approx(17.850767636980986, rel=1e-13)
    assert not call.exercise_now
    assert not put.exercise_now


@pytest.mark.parametrize(
    ("kind", "spot", "price", "delta"),
    [
        ("call", 300.0, 200.0, 1.0),
        ("put", 50.0, 50.0, -1.0),
    ],
)
def test_exercise_region_pays_intrinsic_value(kind, spot, price, delta):
    option = perpetual_american.perpetual_option(kind, spot, **MARKET)
    assert option.exercise_now
    assert option.price == price
    assert option.delta == delta


def test_value_and_delta_join_smoothly_at_both_boundaries():
    call_boundary = 272.07592200561265
    put_boundary = 61.25741132772069
    for kind, boundary, wanted_delta in (
        ("call", call_boundary, 1.0),
        ("put", put_boundary, -1.0),
    ):
        continuation_spot = boundary * (1 - 1e-8 if kind == "call" else 1 + 1e-8)
        continuation = perpetual_american.perpetual_option(kind, continuation_spot, **MARKET)
        at_boundary = perpetual_american.perpetual_option(kind, boundary, **MARKET)
        intrinsic = boundary - 100.0 if kind == "call" else 100.0 - boundary
        assert at_boundary.price == pytest.approx(intrinsic, rel=1e-12)
        assert continuation.delta == pytest.approx(wanted_delta, abs=2e-7)


def test_tiny_positive_dividend_call_stays_below_stock_value():
    result = perpetual_american.perpetual_option(
        "call", 100.0, strike=100.0, r=0.05, sigma=0.2, q=1e-30
    )
    assert result.price <= 100.0
    assert result.boundary > 1e20


def test_tiny_yield_and_small_strike_keep_finite_call_boundary():
    result = perpetual_american.perpetual_option(
        "call", 1e-100, strike=1e-100, r=0.05, sigma=0.2, q=1e-320
    )
    assert math.isfinite(result.boundary)
    assert result.boundary == pytest.approx(7e218, rel=1e-3)
    assert result.price == pytest.approx(1e-100, rel=1e-12, abs=0.0)
    assert not result.exercise_now


def test_call_continuation_ratio_underflow_keeps_positive_value():
    result = perpetual_american.perpetual_option(
        "call", 1e-200, strike=1e-100, r=0.05, sigma=0.2, q=1e-300
    )
    assert result.price == pytest.approx(1e-200, rel=1e-12, abs=0.0)
    assert result.delta == pytest.approx(1.0, rel=1e-12)


def test_put_continuation_ratio_overflow_keeps_positive_value():
    result = perpetual_american.perpetual_option(
        "put", 1e210, strike=1e-100, r=1e-6, sigma=0.2, q=0.1
    )
    assert 0.9e-100 < result.price < 1e-100


@pytest.mark.parametrize(
    ("kind", "q"),
    [("call", 0.1), ("put", 0.0)],
)
def test_unresolvable_exercise_boundary_is_rejected(kind, q):
    with pytest.raises(ValueError, match=r"boundary.*strike"):
        perpetual_american.perpetual_option(kind, 1e16, strike=1e16, r=0.05, sigma=1e-9, q=q)


def test_underflowed_variance_is_rejected_as_unsupported():
    with pytest.raises(ValueError, match="sigma squared"):
        perpetual_american.perpetual_option("put", 100.0, strike=100.0, r=0.05, sigma=1e-200, q=0.0)


def test_zero_dividend_call_has_no_finite_exercise_boundary():
    result = perpetual_american.perpetual_option(
        "call", 100.0, strike=100.0, r=0.05, sigma=0.2, q=0.0
    )
    assert math.isinf(result.boundary)
    assert result.price == 100.0
    assert result.delta == 1.0
    assert not result.exercise_now


@pytest.mark.parametrize(
    ("change", "name"),
    [
        ({"spot": 0.0}, "spot"),
        ({"strike": -1.0}, "strike"),
        ({"r": 0.0}, "r"),
        ({"q": -0.01}, "q"),
        ({"sigma": 0.0}, "sigma"),
        ({"spot": math.inf}, "spot"),
    ],
)
def test_market_domain_is_explicit(change, name):
    args = dict(kind="put", spot=100.0, **MARKET)
    args.update(change)
    with pytest.raises(ValueError, match=name):
        perpetual_american.perpetual_option(**args)


def test_kind_must_be_call_or_put():
    with pytest.raises(ValueError, match="kind"):
        perpetual_american.perpetual_option("straddle", 100.0, **MARKET)
