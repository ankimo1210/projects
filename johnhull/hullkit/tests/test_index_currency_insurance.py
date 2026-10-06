"""Hull GE 17.1: every CAPM table row and independent portfolio cash accounting."""

from fractions import Fraction

import pytest
from hullkit import _index_currency as index


def test_source_beta_one_insurance_contracts_strike_and_terminal_cash():
    plan = index.index_put_insurance(500000, 1000, 1, .12, .25, .04, .04, 450000)
    assert [plan["contracts"], plan["strike"]] == pytest.approx([5, 900])
    scenario = index.capm_portfolio_scenario(500000, 1000, 880, 1, .12, .25, .04, .04)
    cash = index.insurance_cash_value(scenario["price_value"], 880, plan["strike"], plan["contracts"])
    assert [cash["portfolio"], cash["put_payoff"], cash["total"]] == pytest.approx([440000, 10000, 450000])


def test_all_table_17_1_return_columns():
    scenario = index.capm_portfolio_scenario(500000, 1000, 1040, 2, .12, .25, .04, .04)
    keys = ["index_price_return", "index_income_return", "index_total_return", "risk_free_return", "index_excess_return", "portfolio_excess_return", "portfolio_total_return", "portfolio_price_return", "price_value"]
    assert [scenario[key] for key in keys] == pytest.approx([.04, .01, .05, .03, .02, .04, .07, .06, 530000], abs=1e-9)


def test_all_table_17_2_rows_and_beta_two_strike():
    plan = index.index_put_insurance(500000, 1000, 2, .12, .25, .04, .04, 450000)
    assert [plan["contracts"], plan["strike"]] == pytest.approx([10, 960])
    for level, printed in zip([1080, 1040, 1000, 960, 920, 880], [570000, 530000, 490000, 450000, 410000, 370000], strict=True):
        scenario = index.capm_portfolio_scenario(500000, 1000, level, 2, .12, .25, .04, .04)
        assert scenario["price_value"] == pytest.approx(printed, abs=1e-9)
        cash = index.insurance_cash_value(printed, level, plan["strike"], plan["contracts"])
        assert cash["total"] == pytest.approx(max(printed, 450000), abs=1e-9)
    assert index.insurance_cash_value(370000, 880, 960, 10)["put_payoff"] == pytest.approx(80000)


def test_source_dividend_inclusive_floor_strike_955():
    plan = index.index_put_insurance(500000, 1000, 2, .12, .25, .04, .04, 450000, include_dividends=True)
    assert plan["strike"] == pytest.approx(955)
    cash = index.insurance_cash_value(370000, 880, plan["strike"], plan["contracts"], cash_income=5000)
    assert cash["total"] == pytest.approx(450000)


def test_every_row_against_independent_fraction_capm_and_exercise_ledger():
    for terminal_index in [880, 920, 960, 1000, 1040, 1080]:
        price_return = Fraction(terminal_index, 1000)-1
        index_income = Fraction(1, 100)
        risk_free = Fraction(3, 100)
        portfolio_total = risk_free+2*(price_return+index_income-risk_free)
        portfolio = 500000*(1+portfolio_total-index_income)
        put_cash = 10*100*max(Fraction(960)-terminal_index, 0)
        result = index.capm_portfolio_scenario(500000, 1000, terminal_index, 2, .12, .25, .04, .04)
        assert result["price_value"] == pytest.approx(float(portfolio), abs=1e-9)
        assert index.insurance_cash_value(float(portfolio), terminal_index, 960, 10)["total"] == pytest.approx(float(portfolio+put_cash), abs=1e-9)


def test_basis_residual_and_cost_reduce_actual_floor():
    # CAPM conditional value at 880 is 370000, but actual value can differ.
    cash = index.insurance_cash_value(360000, 880, 960, 10, terminal_cost=2000)
    assert cash["total"] == pytest.approx(438000)
    assert cash["total"] < 450000


def test_put_insurance_plan_requires_positive_put_exposure():
    with pytest.raises(ValueError):
        index.index_put_insurance(500000, 1000, 0, .12, .25, .04, .04, 450000)
