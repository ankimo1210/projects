"""Hull 18.4 European futures parity and American inequalities."""

import math
from fractions import Fraction

import pytest
from hullkit import _futures_options as futures
from hullkit.trees import crr_price


def test_example_18_5_put_price_from_call():
    result = futures.futures_parity(8, 8.5, 0.1, 0.5, call=0.56)
    assert result["put"] == pytest.approx(1.04, abs=0.005)
    assert result["put"] == pytest.approx(1.035614712, abs=5e-10)


def test_call_quote_from_put_and_negative_rate_european_parity():
    result = futures.futures_parity(8, 8.5, -0.02, 0.5, put=1.1)
    assert result["call"] == pytest.approx(1.1 + math.exp(0.01) * (8 - 8.5), abs=1e-14)


def test_source_two_portfolios_against_independent_fraction_cash():
    initial, strike = Fraction(8), Fraction(17, 2)
    for terminal in [Fraction(5), initial, strike, Fraction(12)]:
        call_and_bond = max(terminal - strike, 0) + strike
        put_future_and_bond = max(strike - terminal, 0) + (terminal - initial) + initial
        assert float(call_and_bond) == pytest.approx(float(put_future_and_bond))
        assert float(call_and_bond) == pytest.approx(float(max(terminal, strike)))
    quotes = futures.black_details(8, 8.5, 0.1, 0.3, 0.5)
    parity = futures.futures_parity(8, 8.5, 0.1, 0.5, call=quotes["call"], put=quotes["put"])
    assert parity["residual"] == pytest.approx(0, abs=1e-14)


@pytest.mark.parametrize("forward", [5, 8, 12])
def test_source_american_difference_interval_with_actual_futures_trees(forward):
    call = crr_price(forward, 8.5, 0.1, 0.3, 0.5, 600, q=0.1, american=True)
    put = crr_price(forward, 8.5, 0.1, 0.3, 0.5, 600, q=0.1, kind="put", american=True)
    lower, upper = futures.futures_american_difference_bounds(forward, 8.5, 0.1, 0.5)
    assert lower - 1e-10 <= call - put <= upper + 1e-10


def test_inconsistent_quotes_report_nonzero_parity_residual():
    result = futures.futures_parity(8, 8.5, 0.1, 0.5, call=0.56, put=1.0)
    assert result["residual"] == pytest.approx(0.035614712, abs=5e-10)


def test_missing_quote_infeasible_quote_and_american_negative_rate():
    with pytest.raises(ValueError):
        futures.futures_parity(8, 8.5, 0.1, 0.5)
    with pytest.raises(ValueError):
        futures.futures_parity(8, 8.5, 0.1, 0.5, put=0)
    with pytest.raises(ValueError):
        futures.futures_american_difference_bounds(8, 8.5, -0.02, 0.5)


def test_parity_accepts_a_model_call_whose_put_rounds_one_ulp_below_zero():
    # Deep ITM: call minus the 28,000 parity difference is -3.6e-12 from rounding alone.
    call = futures.black_details(30000, 1000, 0.03, 0.2, 1)["call"]
    result = futures.futures_parity(30000, 1000, 0.03, 1, call=call)
    assert result["put"] == pytest.approx(0, abs=1e-9)
    with pytest.raises(ValueError):
        futures.futures_parity(30000, 1000, 0.03, 1, call=call - 1e-3)
