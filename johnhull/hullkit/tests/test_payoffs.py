"""Tests for hullkit.payoffs against Hull 11e Ch.12 piecewise formulas."""

import math

import numpy as np
import pytest
from hullkit import payoffs

S = np.linspace(50.0, 150.0, 201)


def test_bull_call_spread_is_clip():
    legs = payoffs.STRATEGIES["bull_call_spread"](95.0, 105.0)
    assert np.allclose(payoffs.strategy_payoff(S, legs), np.clip(S - 95.0, 0.0, 10.0))


def test_bear_put_spread_is_clip():
    legs = payoffs.STRATEGIES["bear_put_spread"](95.0, 105.0)
    assert np.allclose(payoffs.strategy_payoff(S, legs), np.clip(105.0 - S, 0.0, 10.0))


def test_butterfly_spike():
    legs = payoffs.STRATEGIES["butterfly"](90.0, 100.0, 110.0)
    pay = payoffs.strategy_payoff(S, legs)
    assert pay[np.argmin(np.abs(S - 100.0))] == pytest.approx(10.0)
    assert pay[0] == pytest.approx(0.0)
    assert pay[-1] == pytest.approx(0.0)
    assert np.all(pay >= -1e-12)


def test_straddle_abs():
    legs = payoffs.STRATEGIES["straddle"](100.0)
    assert np.allclose(payoffs.strategy_payoff(S, legs), np.abs(S - 100.0))


def test_strangle_piecewise():
    legs = payoffs.STRATEGIES["strangle"](90.0, 110.0)
    expected = np.maximum(90.0 - S, 0.0) + np.maximum(S - 110.0, 0.0)
    assert np.allclose(payoffs.strategy_payoff(S, legs), expected)


def test_strip_strap_weights():
    strip_pay = payoffs.strategy_payoff(S, payoffs.STRATEGIES["strip"](100.0))
    strap_pay = payoffs.strategy_payoff(S, payoffs.STRATEGIES["strap"](100.0))
    assert strip_pay[0] == pytest.approx(100.0)  # 2 puts deep ITM at S=50
    assert strap_pay[-1] == pytest.approx(100.0)  # 2 calls deep ITM at S=150


def test_covered_call_equals_short_put_plus_bond():
    # S - max(S-K,0) == K - max(K-S,0) == min(S,K)  (put-call parity, Hull §12.2)
    cc = payoffs.strategy_payoff(S, payoffs.STRATEGIES["covered_call"](100.0))
    short_put_plus_k = 100.0 - np.maximum(100.0 - S, 0.0)
    assert np.allclose(cc, short_put_plus_k)


def test_protective_put_equals_call_plus_bond():
    pp = payoffs.strategy_payoff(S, payoffs.STRATEGIES["protective_put"](100.0))
    call_plus_k = np.maximum(S - 100.0, 0.0) + 100.0
    assert np.allclose(pp, call_plus_k)


def test_box_spread_value():
    assert payoffs.box_spread_value(90.0, 110.0, 0.05, 1.0) == pytest.approx(
        20.0 * math.exp(-0.05), abs=1e-12
    )


def test_invalid_kind_and_missing_strike():
    with pytest.raises(ValueError):
        payoffs.leg_payoff(S, 1, "cal", 100.0)
    with pytest.raises(ValueError):
        payoffs.leg_payoff(S, 1, "call", None)
