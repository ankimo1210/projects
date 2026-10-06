"""Hull 20.8: one anticipated event, two terminal states and a frown."""

import math

import numpy as np
import pytest
from hullkit import _smile_surface as smile
from hullkit._index_currency import carry_implied_vol
from scipy.integrate import quad
from scipy.stats import norm


def density_price(spot, strike, rate, yield_rate, sigma, time, kind):
    width = sigma * math.sqrt(time)
    mean = math.log(spot) + (rate - yield_rate - sigma * sigma / 2) * time
    cutoff = (math.log(strike) - mean) / width
    sign = 1 if kind == "call" else -1
    low, high = (cutoff, 12) if kind == "call" else (-12, cutoff)
    return (
        math.exp(-rate * time)
        * quad(
            lambda z: max(sign * (math.exp(mean + width * z) - strike), 0) * norm.pdf(z),
            low,
            high,
            epsabs=1e-14,
        )[0]
    )


STRIKES = np.arange(42, 59, 2, dtype=float)
CALL_QUOTES = np.array([8.42, 7.37, 6.31, 5.26, 4.21, 3.16, 2.10, 1.05, 0])
PUT_QUOTES = np.array([0, 0.93, 1.86, 2.78, 3.71, 4.64, 5.57, 6.50, 7.42])


def example(strikes=STRIKES):
    return smile.single_jump_details(50, 42, 58, 0.12, 1 / 12, strikes)


def test_textbook_up_down_growth_and_probability():
    result = example()
    assert result["up_factor"] == pytest.approx(1.16, abs=1e-12)
    assert result["down_factor"] == pytest.approx(0.84, abs=1e-12)
    assert result["growth_factor"] == pytest.approx(1.0101, abs=0.00005)
    assert result["up_probability"] == pytest.approx(0.5314, abs=0.00005)
    p = result["up_probability"]
    assert p * 58 + (1 - p) * 42 == pytest.approx(50 * math.exp(0.12 / 12), abs=1e-12)


def test_table_20_3_all_call_and_put_prices_and_parity():
    result = example()
    assert result["call_prices"] == pytest.approx(CALL_QUOTES, abs=0.005)
    assert result["put_prices"] == pytest.approx(PUT_QUOTES, abs=0.005)
    assert result["call_prices"] - result["put_prices"] == pytest.approx(
        50 - STRIKES * math.exp(-0.12 / 12), abs=1e-12
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_prices_independent_two_state_stock_bank_replication(kind):
    sign = 1 if kind == "call" else -1
    result = example()
    replicated = []
    for strike in STRIKES:
        # Solve for stock shares and dollars paid by the bank at maturity.
        payoff = np.maximum(sign * (np.array([42.0, 58.0]) - strike), 0)
        shares, terminal_cash = np.linalg.solve(np.array([[42.0, 1.0], [58.0, 1.0]]), payoff)
        replicated.append(shares * 50 + terminal_cash * math.exp(-0.12 / 12))
    assert result[kind + "_prices"] == pytest.approx(replicated, abs=1e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_model_iv_reprices_with_independent_lognormal_payoff_integral(kind):
    result = example()
    sign = 1 if kind == "call" else -1
    for strike, iv, price in zip(
        STRIKES, result["implied_volatility"], result[kind + "_prices"], strict=True
    ):
        independent = (
            math.exp(-0.12 / 12) * max(sign * (50 * math.exp(0.12 / 12) - strike), 0)
            if iv == 0
            else density_price(50, strike, 0.12, 0, iv, 1 / 12, kind)
        )
        assert price == pytest.approx(independent, abs=1e-10)
    assert result["implied_volatility"][[0, -1]] == pytest.approx([0, 0], abs=1e-12)


def test_rounded_call_quote_ivs_retain_printed_k56_discrepancy():
    iv = np.array(
        [
            carry_implied_vol(float(price), 50, float(strike), 0.12, 0, 1 / 12)
            for price, strike in zip(CALL_QUOTES[1:-1], STRIKES[1:-1], strict=True)
        ]
    )
    printed = np.array([58.8, 66.6, 69.5, 69.2, 66.1, 60.0])
    # Quotes rounded to cents do not carry the model's full-precision IV.
    # K44: the rounded call gives 58.850 (58.9 at one decimal); the printed
    # 58.8 matches the rounded put 0.93 instead.
    assert iv[1:-1] * 100 == pytest.approx(printed[1:], abs=0.05)
    assert iv[0] * 100 == pytest.approx(58.85004, abs=0.00001)
    put_iv = carry_implied_vol(float(PUT_QUOTES[1]), 50, 44.0, 0.12, 0, 1 / 12, kind="put")
    assert put_iv * 100 == pytest.approx(printed[0], abs=0.05)
    assert iv[-1] * 100 == pytest.approx(49.88574, abs=0.00001)
    assert abs(iv[-1] * 100 - 49.0) > 0.8
    assert example()["implied_volatility"][-2] * 100 == pytest.approx(49.93360, abs=0.00001)
    assert abs(example()["implied_volatility"][1] - iv[0]) > 0.0005
    for strike, price, vol in zip(STRIKES[1:-1], CALL_QUOTES[1:-1], iv, strict=True):
        assert density_price(50, strike, 0.12, 0, vol, 1 / 12, "call") == pytest.approx(
            price, abs=1e-10
        )


def test_frown_maximum_near_atm_and_zero_at_extreme_strikes():
    iv = example()["implied_volatility"]
    assert np.all(np.diff(iv[:4]) > 0)
    assert np.all(np.diff(iv[3:]) < 0)


def test_atm_iv_overprices_strikes_44_and_56_as_textbook_describes():
    result = example()
    atm_iv = result["implied_volatility"][4]
    for index in [1, 7]:
        fixed_iv = density_price(50, STRIKES[index], 0.12, 0, atm_iv, 1 / 12, "call")
        assert fixed_iv > result["call_prices"][index]


@pytest.mark.parametrize("spot,maturity", [(70, 1 / 12), (50, 0)])
def test_mathematically_invalid_state_or_time(spot, maturity):
    with pytest.raises(ValueError):
        smile.single_jump_details(spot, 42, 58, 0.12, maturity, STRIKES)


def test_currency_unit_rescaling_preserves_iv_and_scales_prices():
    a = example()
    b = smile.single_jump_details(5000, 4200, 5800, 0.12, 1 / 12, STRIKES * 100)
    assert b["call_prices"] == pytest.approx(a["call_prices"] * 100, abs=1e-10)
    assert b["implied_volatility"] == pytest.approx(a["implied_volatility"], abs=1e-11)
