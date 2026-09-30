"""Hull GE §26.4 gap options: validated entry point and pricing identities."""

import math

import numpy as np
import pytest
from hullkit import bsm, exotics, gap_options

MARKET = dict(spot=100.0, r=0.05, sigma=0.25, T=1.0, q=0.02)


def _gap(kind="call", **changes):
    args = {**MARKET, "K1": 90.0, "K2": 100.0, **changes}
    return gap_options.gap_option(
        kind, args["spot"], args["K1"], args["K2"], args["r"], args["sigma"], args["T"], args["q"]
    )


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("K1", [80.0, 100.0, 125.0])
def test_price_is_the_regular_option_plus_a_signed_cash_binary(kind, K1):
    result = _gap(kind, K1=K1)
    regular = (bsm.call_price if kind == "call" else bsm.put_price)(
        MARKET["spot"], 100.0, MARKET["r"], MARKET["sigma"], MARKET["T"], MARKET["q"]
    )
    cash = exotics.cash_or_nothing(
        MARKET["spot"], 100.0, MARKET["r"], MARKET["sigma"], MARKET["T"], MARKET["q"], kind=kind
    )
    sign = 1.0 if kind == "call" else -1.0
    assert result.regular_price == pytest.approx(regular, rel=1e-14)
    assert result.trigger_adjustment == pytest.approx(sign * (100.0 - K1) * cash, abs=1e-12)
    assert result.price == pytest.approx(
        result.regular_price + result.trigger_adjustment, abs=1e-12
    )
    assert result.trigger_probability == pytest.approx(cash * math.exp(MARKET["r"] * MARKET["T"]))


def test_equal_strikes_give_the_regular_option_and_parity_holds():
    call, put = _gap("call", K1=100.0), _gap("put", K1=100.0)
    assert call.trigger_adjustment == 0.0 and put.trigger_adjustment == 0.0
    assert call.price == pytest.approx(call.regular_price, rel=1e-14)
    spot, r, T, q = MARKET["spot"], MARKET["r"], MARKET["T"], MARKET["q"]
    for K1 in (0.0, 70.0, 130.0):
        difference = _gap("call", K1=K1).price - _gap("put", K1=K1).price
        assert difference == pytest.approx(
            spot * math.exp(-q * T) - K1 * math.exp(-r * T), abs=1e-12
        )


def test_zero_settlement_strike_is_the_asset_or_nothing_option():
    args = (MARKET["spot"], 100.0, MARKET["r"], MARKET["sigma"], MARKET["T"], MARKET["q"])
    assert _gap("call", K1=0.0).price == pytest.approx(exotics.asset_or_nothing(*args), rel=1e-14)
    assert _gap("put", K1=0.0).price == pytest.approx(
        -exotics.asset_or_nothing(*args, kind="put"), rel=1e-14
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_zero_value_settlement_is_the_conditional_mean(kind):
    level = _gap(kind).zero_value_settlement
    assert _gap(kind, K1=level).price == pytest.approx(0.0, abs=1e-12)
    assert (level > 100.0) if kind == "call" else (level < 100.0)


def test_hull_example_26_1_insurer_cost():
    regular = gap_options.gap_option("put", 500_000.0, 400_000.0, 400_000.0, 0.05, 0.20, 1.0)
    gap = gap_options.gap_option("put", 500_000.0, 400_000.0, 350_000.0, 0.05, 0.20, 1.0)
    assert round(regular.price) == 3_436
    assert round(gap.price) == 1_896
    assert 1.0 - gap.price / regular.price == pytest.approx(0.448277597587, abs=1e-11)


def test_payoff_is_not_floored_and_jumps_at_the_trigger():
    call = _gap("call", K1=110.0)
    put = _gap("put", K1=90.0)
    grid = np.array([95.0, 100.0, 100.0 + 1e-9, 105.0, 120.0])
    assert call.payoff(grid) == pytest.approx([0.0, 0.0, -10.0 + 1e-9, -5.0, 10.0])
    assert put.payoff(np.array([80.0, 95.0, 100.0, 120.0])) == pytest.approx([10.0, -5.0, 0.0, 0.0])


@pytest.mark.parametrize(
    ("name", "value", "match"),
    [
        ("K1", -1.0, "K1"),
        ("K1", math.nan, "K1"),
        ("K1", math.inf, "K1"),
        ("K2", 0.0, "K2"),
        ("K2", math.nan, "K2"),
        ("spot", 0.0, "spot"),
        ("spot", math.inf, "spot"),
        ("sigma", 0.0, "sigma"),
        ("T", 0.0, "T"),
        ("T", math.inf, "T"),
        ("r", math.nan, "r"),
        ("r", math.inf, "r"),
        ("q", -math.inf, "q"),
        ("r", -800.0, "overflow"),
        ("q", -800.0, "overflow"),
    ],
)
def test_invalid_inputs_raise_value_error(name, value, match):
    with pytest.raises(ValueError, match=match):
        _gap("call", **{name: value})


def test_unknown_kind_and_boolean_inputs_are_rejected():
    with pytest.raises(ValueError, match="kind"):
        _gap("straddle")
    with pytest.raises(ValueError, match="K1"):
        _gap("call", K1=True)


def test_zero_value_settlement_needs_a_positive_trigger_probability():
    far = _gap("call", K2=1e30)
    assert far.trigger_probability == 0.0
    with pytest.raises(ValueError, match="trigger probability"):
        _ = far.zero_value_settlement


def test_price_overflow_is_a_value_error():
    with pytest.raises(ValueError, match="overflow"):
        _gap("call", K1=1e308, K2=100.0, r=-1.0)


def test_non_real_inputs_name_the_expected_type():
    with pytest.raises(ValueError, match="finite real number"):
        _gap("call", K1="90")


def test_small_spot_with_large_carry_keeps_a_finite_forward():
    quote = gap_options.gap_option("call", 0.5, 1.0, 1.0, 710.0, 0.2, 1.0)
    assert math.isfinite(quote.forward)
    assert quote.price == pytest.approx(0.5, rel=1e-12)


def test_forward_overflow_is_a_value_error():
    with pytest.raises(ValueError, match="forward"):
        gap_options.gap_option("call", 1e300, 1.0, 1.0, 100.0, 0.2, 1.0)
