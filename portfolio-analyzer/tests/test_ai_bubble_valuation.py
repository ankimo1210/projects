"""Reverse DCF: enterprise value, terminal cash flow, fade paths and root finding (spec 5)."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.valuation import (
    enterprise_value,
    growth_path,
    implied_irr,
    per,
    project_fcff,
    required_growth,
    solve_roots,
    terminal_fcff,
    v_classify,
)


@pytest.mark.parametrize("years", [1, 5])
def test_a_steady_firm_is_worth_its_perpetuity(years):
    assert enterprise_value([10.0] * years, 10.0, 0.10, 0.0) == pytest.approx(100.0)


def test_terminal_cash_flow_is_discounted_as_given_not_rebuilt_from_the_last_year():
    # a terminal flow taken from the last year (10) instead of the one passed (20) gives 100
    assert enterprise_value([10.0], 20.0, 0.10, 0.0) == pytest.approx(2100 / 11)


def test_rate_at_or_below_growth_is_refused():
    with pytest.raises(ValueError, match="r"):
        enterprise_value([10.0], 10.0, 0.03, 0.03)


def test_terminal_fcff_keeps_the_reinvestment_growth_needs():
    assert terminal_fcff(100.0, 0.03, 0.15) == pytest.approx(80.0)


def test_growth_fades_geometrically_to_the_terminal_rate():
    assert growth_path(0.5, 0.03, 0.6, 3) == pytest.approx([0.312, 0.1992, 0.13152])


def test_shocks_replace_the_growth_of_their_years():
    assert growth_path(0.5, 0.03, 0.6, 3, shocks={1: -0.2, 2: -0.1}) == pytest.approx(
        [-0.2, -0.1, 0.13152]
    )


def test_solve_roots_returns_every_root_and_nothing_without_a_sign_change():
    roots = solve_roots(lambda x: (x - 0.1) * (x - 0.3), 0.0, 1.0)
    assert roots == pytest.approx([0.1, 0.3], abs=1e-9)
    assert solve_roots(lambda x: x * x + 1, 0.0, 1.0) == []


BASE = {"revenue": 1000.0, "tax_rate": 0.2, "sales_to_capital": 2.0}


def scenario(g0, *, years=10, margin=0.3, ronic=0.15, g_inf=0.03, phi=0.6):
    return {
        "growth": growth_path(g0, g_inf, phi, years),
        "margin": [margin] * years,
        "ronic": ronic,
        "g_inf": g_inf,
    }


def test_project_fcff_takes_reinvestment_from_sales_growth_and_capital_turnover():
    out = project_fcff(BASE, {"growth": [0.1], "margin": [0.3], "ronic": 0.15, "g_inf": 0.03}, 1)
    assert out["revenue"] == pytest.approx([1100.0])
    assert out["nopat"] == pytest.approx([1100 * 0.3 * 0.8])
    assert out["reinvestment"] == pytest.approx([50.0])
    assert out["fcff"] == pytest.approx([264.0 - 50.0])
    # year T+1 revenue grows at g_inf, terminal FCFF reinvests g_inf / RONIC of NOPAT
    nopat_next = 1100 * 1.03 * 0.3 * 0.8
    assert out["terminal_fcff"] == pytest.approx(nopat_next * (1 - 0.03 / 0.15))


def test_falling_sales_release_no_capital():
    out = project_fcff(BASE, {"growth": [-0.2], "margin": [0.3], "ronic": 0.15, "g_inf": 0.03}, 1)
    assert out["reinvestment"] == [0.0]


def test_a_loss_is_not_taxed_into_a_gain():
    out = project_fcff(BASE, {"growth": [0.0], "margin": [-0.1], "ronic": 0.15, "g_inf": 0.03}, 1)
    assert out["nopat"] == pytest.approx([-100.0])


def _ev(g0, r=0.09):
    flows = project_fcff(BASE, scenario(g0), 10)
    return enterprise_value(flows["fcff"], flows["terminal_fcff"], r, 0.03)


def test_required_growth_recovers_the_growth_that_made_the_value():
    target = _ev(0.4)
    out = required_growth(lambda g0: _ev(g0), target, bounds=(-0.5, 2.0))
    assert out["status"] == "ok"
    assert out["solutions"][0] == pytest.approx(0.4, abs=1e-6)
    assert out["bounds"] == (-0.5, 2.0)


def test_required_growth_outside_the_bounds_is_no_solution():
    out = required_growth(lambda g0: _ev(g0), _ev(3.0), bounds=(-0.5, 2.0))
    assert out == {"status": "no_solution", "solutions": [], "bounds": (-0.5, 2.0)}


def test_implied_irr_recovers_the_rate_that_made_the_value():
    flows = project_fcff(BASE, scenario(0.4), 10)
    target = enterprise_value(flows["fcff"], flows["terminal_fcff"], 0.11, 0.03)
    out = implied_irr(flows["fcff"], flows["terminal_fcff"], 0.03, target, bounds=(0.04, 0.30))
    assert out["status"] == "ok"
    assert out["solutions"][0] == pytest.approx(0.11, abs=1e-6)


def test_implied_irr_above_the_bounds_is_no_solution():
    flows = project_fcff(BASE, scenario(0.4), 10)
    target = enterprise_value(flows["fcff"], flows["terminal_fcff"], 0.11, 0.03) / 100
    out = implied_irr(flows["fcff"], flows["terminal_fcff"], 0.03, target, bounds=(0.04, 0.30))
    assert out["status"] == "no_solution"


def test_per_is_unchanged_by_a_split_and_counts_ordinary_shares_per_adr():
    assert per(200.0, 10.0) == pytest.approx(20.0)
    assert per(200.0 / 5, 10.0 / 5) == pytest.approx(20.0)
    assert per(100.0, 1.0, adr_ratio=5) == pytest.approx(20.0)


@pytest.mark.parametrize("eps", [0.0, -1.0, None])
def test_per_without_positive_earnings_is_none(eps):
    assert per(100.0, eps) is None


@pytest.mark.parametrize(
    ("central", "optimistic", "observed", "label"),
    [
        (95.0, 130.0, 100.0, "弱める"),
        (80.0, 85.0, 100.0, "支持"),
        (80.0, 120.0, 100.0, "混在"),
        (80.0, 85.0, 0.0, "保留"),
        (80.0, 85.0, -5.0, "保留"),
    ],
)
def test_v_classify(central, optimistic, observed, label):
    assert v_classify(central, optimistic, observed) == label


from portfolio_analyzer.ai_bubble.valuation import scenario_paths  # noqa: E402

FIRM = {
    "revenue": 1000.0,
    "g0": 0.5,
    "margin": 0.40,
    "tax_rate": 0.15,
    "statutory_tax": 0.25,
    "sales_to_capital": 2.0,
    "roic": 0.60,
    "history": {"avg_margin": 0.30, "min_margin": 0.10, "worst_2y_revenue_change": -0.36},
}


def test_central_fades_growth_and_walks_the_margin_to_its_average_by_year_five():
    s = scenario_paths(FIRM, "central", r_j=0.09)
    assert s["growth"] == pytest.approx(growth_path(0.5, 0.03, 0.6, 10))
    assert s["margin"][:6] == pytest.approx([0.38, 0.36, 0.34, 0.32, 0.30, 0.30])
    assert s["ronic"] == pytest.approx(0.14)
    # tax moves from the effective rate to the statutory rate by year 10
    assert s["tax"][0] == pytest.approx(0.15 + (0.25 - 0.15) * 1 / 10)
    assert s["tax"][-1] == pytest.approx(0.25)
    assert s["tax_terminal"] == pytest.approx(0.25)


def test_optimistic_holds_the_margin_slows_the_fade_and_earns_todays_return():
    s = scenario_paths(FIRM, "optimistic", r_j=0.09)
    assert s["growth"] == pytest.approx(growth_path(0.5, 0.03, 0.85, 10))
    assert s["margin"] == pytest.approx([0.40] * 10)
    assert s["ronic"] == pytest.approx(0.60)


def test_stress_spreads_the_worst_two_years_over_years_one_and_two():
    s = scenario_paths(FIRM, "stress", r_j=0.09)
    assert s["growth"][:2] == pytest.approx([-0.2, -0.2])  # 0.8 x 0.8 = 0.64
    assert s["growth"][2:] == pytest.approx(growth_path(0.5, 0.03, 0.6, 10)[2:])
    assert s["margin"][:5] == pytest.approx([0.10, 0.10, 0.1 + 0.2 / 3, 0.1 + 0.4 / 3, 0.30])
    assert s["ronic"] == pytest.approx(0.09)


def test_stress_without_a_two_year_decline_on_record_holds_sales_flat():
    firm = dict(FIRM, history=dict(FIRM["history"], worst_2y_revenue_change=4.0))
    s = scenario_paths(firm, "stress", r_j=0.09)
    assert s["growth"][:2] == [0.0, 0.0]
    assert "no two-year decline" in s["note"]


def test_project_fcff_uses_the_scenario_tax_path():
    out = project_fcff(
        {"revenue": 100.0, "tax_rate": 0.0, "sales_to_capital": 1.0},
        {
            "growth": [0.0, 0.0],
            "margin": [0.5, 0.5],
            "tax": [0.1, 0.2],
            "tax_terminal": 0.3,
            "ronic": 0.2,
            "g_inf": 0.0,
        },
        2,
    )
    assert out["nopat"] == pytest.approx([45.0, 40.0])
    assert out["nopat_next"] == pytest.approx(35.0)


def test_optimistic_return_below_terminal_growth_falls_back_to_the_central_ronic():
    firm = dict(FIRM, roic=-0.05)
    s = scenario_paths(firm, "optimistic", r_j=0.09)
    assert s["ronic"] == pytest.approx(0.14)
    assert "central RONIC" in s["note"]


from portfolio_analyzer.ai_bubble.valuation import value_company  # noqa: E402


def _central_ev(firm, r):
    s = scenario_paths(firm, "central", r_j=r)
    f = project_fcff(firm, s, 10)
    return enterprise_value(f["fcff"], f["terminal_fcff"], r, 0.03)


def test_value_company_at_a_price_equal_to_the_central_value():
    observed = _central_ev(FIRM, 0.09)
    out = value_company(FIRM, r_j=0.09, ev_observed=observed)
    assert out["ev"]["central"] == pytest.approx(observed)
    assert out["v"] == "弱める"
    assert out["required_growth"]["status"] == "ok"
    assert out["required_growth"]["solutions"][0] == pytest.approx(0.5, abs=1e-6)
    path = growth_path(0.5, 0.03, 0.6, 10)
    cagr5 = 1.0
    for g in path[:5]:
        cagr5 *= 1 + g
    assert out["required_growth"]["cagr_5y"][0] == pytest.approx(cagr5 ** (1 / 5) - 1, abs=1e-6)
    assert out["required_margin"]["solutions"][0] == pytest.approx(0.30, abs=1e-6)
    assert out["implied_irr"]["solutions"][0] == pytest.approx(0.09, abs=1e-6)
    assert 0 < out["terminal_share"] < 1


def test_value_company_reports_the_grid_and_capital_turnover_sensitivity():
    out = value_company(FIRM, r_j=0.09, ev_observed=1000.0)
    keys = {(g["T"], g["r"], g["g_inf"]) for g in out["grid"]}
    assert len(keys) == 2 * 5 * 3
    assert all(g["r"] > g["g_inf"] for g in out["grid"])
    low, high = out["turnover"]["x0.75"], out["turnover"]["x1.25"]
    assert low < out["ev"]["central"] < high  # less capital per unit of sales is worth more


from portfolio_analyzer.ai_bubble.valuation import (  # noqa: E402
    cycle_per,
    layer_consistency,
    multiples,
    price_decomposition,
)


def test_multiples_on_one_period_and_basis():
    out = multiples(
        market_cap=1000.0, ev=1100.0, net_income=50.0, ebit=80.0, operating_cf=70.0, capex=30.0
    )
    assert out["earnings_yield"] == pytest.approx(0.05)
    assert out["per"] == pytest.approx(20.0)
    assert out["ev_ebit"] == pytest.approx(13.75)
    assert out["ocf_to_net_income"] == pytest.approx(1.4)
    assert out["fcf_after_capex"] == pytest.approx(40.0)
    assert out["fcf_yield"] == pytest.approx(0.04)


def test_a_loss_has_no_per_and_no_cash_conversion_ratio():
    out = multiples(
        market_cap=1000.0, ev=900.0, net_income=-10.0, ebit=-5.0, operating_cf=None, capex=None
    )
    assert out["earnings_yield"] == pytest.approx(-0.01)
    assert out["per"] is None and out["ev_ebit"] is None and out["ocf_to_net_income"] is None
    assert out["fcf_after_capex"] is None and out["fcf_yield"] is None


def test_cycle_per_sets_the_latest_quarter_against_twenty_quarters():
    quarters = [(f"q{i:02d}", float(i)) for i in range(1, 25)]  # 24 quarters, the last 20 are 5..24
    out = cycle_per(1000.0, quarters)
    assert out["per_latest_x4"] == pytest.approx(1000 / (4 * 24))
    assert out["per_cycle"] == pytest.approx(1000 / (4 * 14.5))
    assert (out["quarters"], out["first_end"], out["reference_only"]) == (20, "q05", False)


def test_cycle_per_with_fewer_quarters_is_reference_only():
    out = cycle_per(1000.0, [(f"q{i}", 10.0) for i in range(8)])
    assert out["quarters"] == 8 and out["reference_only"] is True


def test_buyers_cutting_investment_while_suppliers_grow_is_flagged():
    buyers = [
        {"revenue": [100.0, 110.0, 115.0, 118.0], "sales_to_capital": 1.0}
    ]  # investment 10, 5, 3
    suppliers = [{"revenue": [50.0, 60.0, 66.0]}]
    out = layer_consistency(buyers, suppliers, years=2)
    assert [y["buyers_investment_change"] for y in out] == pytest.approx([-0.5, -0.4])
    assert [y["suppliers_revenue_change"] for y in out] == pytest.approx([0.2, 0.1])
    assert [y["warning"] for y in out] == [True, True]


def test_investment_and_supplier_revenue_moving_together_is_not_flagged():
    buyers = [{"revenue": [100.0, 110.0, 125.0], "sales_to_capital": 2.0}]  # investment 5, 7.5
    out = layer_consistency(buyers, [{"revenue": [50.0, 60.0]}], years=1)
    assert out[0]["buyers_investment_change"] == pytest.approx(0.5)
    assert out[0]["warning"] is False


def test_price_change_splits_into_earnings_and_multiple():
    out = price_decomposition(price0=100.0, price1=150.0, eps0=5.0, eps1=6.0)
    assert out["dlog_price"] == pytest.approx(out["dlog_eps"] + out["dlog_per"])
    assert out["dlog_per"] == pytest.approx(__import__("math").log(1.25))
    assert price_decomposition(price0=100.0, price1=150.0, eps0=-1.0, eps1=6.0) is None


def test_value_company_reports_the_central_value_with_a_five_year_forecast():
    out = value_company(FIRM, r_j=0.09, ev_observed=1000.0)
    s = scenario_paths(FIRM, "central", r_j=0.09, years=5)
    f = project_fcff(FIRM, s, 5)
    assert out["ev_central_T5"] == pytest.approx(
        enterprise_value(f["fcff"], f["terminal_fcff"], 0.09, 0.03)
    )
