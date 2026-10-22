"""Trailing twelve months, fiscal-year history and the balance sheet items of the reverse DCF."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.fundamentals import (
    balance,
    fiscal_years,
    history_stats,
    tax_rate,
    ttm,
)


def flow(metric, start, end, value, basis="US-GAAP"):
    return {
        "metric": metric,
        "period_start": start,
        "period_end": end,
        "value": value,
        "accounting_basis": basis,
    }


def stock(metric, day, value, basis="US-GAAP"):
    return flow(metric, day, day, value, basis)


# A December fiscal year: FY2025, Q2 2026 year to date and its comparative.
REVENUE = [
    flow("revenue", "2024-01-01", "2024-12-31", 800.0),
    flow("revenue", "2025-01-01", "2025-12-31", 1000.0),
    flow("revenue", "2025-01-01", "2025-06-30", 450.0),
    flow("revenue", "2025-04-01", "2025-06-30", 240.0),
    flow("revenue", "2024-01-01", "2024-06-30", 380.0),
    flow("revenue", "2026-01-01", "2026-06-30", 600.0),
    flow("revenue", "2026-04-01", "2026-06-30", 320.0),
]


def test_ttm_adds_the_year_to_date_to_last_year_less_its_comparative():
    out = ttm(REVENUE, "revenue")
    assert out["end"] == "2026-06-30"
    assert out["value"] == pytest.approx(1000 + 600 - 450)
    # a year earlier: FY2024 + H1 2025 - H1 2024
    assert out["prev_end"] == "2025-06-30"
    assert out["prev_value"] == pytest.approx(800 + 450 - 380)


def test_ttm_at_a_fiscal_year_end_is_the_year():
    rows = [r for r in REVENUE if r["period_end"] <= "2025-12-31"]
    out = ttm(rows, "revenue")
    assert (out["end"], out["value"], out["prev_value"]) == ("2025-12-31", 1000.0, 800.0)


def test_52_week_years_match_the_comparative_within_days():
    rows = [
        flow("revenue", "2025-01-27", "2026-01-25", 200.0),  # 52 weeks
        flow("revenue", "2026-01-26", "2026-07-26", 180.0),
        flow("revenue", "2025-01-27", "2025-07-27", 90.0),
    ]
    assert ttm(rows, "revenue")["value"] == pytest.approx(200 + 180 - 90)


def test_two_bases_at_the_latest_period_are_refused():
    rows = [*REVENUE, flow("revenue", "2026-01-01", "2026-06-30", 601.0, basis="IFRS")]
    with pytest.raises(ValueError, match="basis"):
        ttm(rows, "revenue")


def test_ttm_uses_only_the_basis_of_the_latest_period():
    ifrs = [dict(r, accounting_basis="IFRS") for r in REVENUE]
    older = flow("revenue", "2025-01-01", "2025-12-31", 5.0)  # an old-basis twin of FY2025
    assert ttm([*ifrs, older], "revenue")["value"] == 1150.0


def test_ttm_falls_back_to_the_latest_end_it_can_build():
    # without the H1 2025 comparative the June 2026 TTM cannot be built
    rows = [
        r for r in REVENUE if (r["period_start"], r["period_end"]) != ("2025-01-01", "2025-06-30")
    ]
    out = ttm(rows, "revenue")
    assert (out["end"], out["value"], out["prev_value"]) == ("2025-12-31", 1000.0, 800.0)


def test_fiscal_years_keep_twelve_month_periods_only():
    assert fiscal_years(REVENUE, "revenue") == [("2024-12-31", 800.0), ("2025-12-31", 1000.0)]


def test_history_stats_average_minimum_and_worst_two_years():
    revenue = [
        (f"{y}-12-31", v)
        for y, v in zip(
            range(2015, 2026), [100, 120, 60, 50, 80, 100, 130, 150, 170, 190, 200], strict=True
        )
    ]
    ebit = [
        (d, v * m)
        for (d, v), m in zip(
            revenue, [0.2, 0.25, -0.1, 0.05, 0.1, 0.15, 0.2, 0.22, 0.24, 0.26, 0.28], strict=True
        )
    ]
    out = history_stats(revenue, ebit, last_n=5)
    assert out["avg_margin"] == pytest.approx((0.22 + 0.24 + 0.26 + 0.28 + 0.20) / 5)
    assert out["avg_margin_years"] == 5
    assert out["min_margin"] == pytest.approx(-0.1)
    # 120 (2016) -> 50 (2018) is the worst two-year change
    assert out["worst_2y_revenue_change"] == pytest.approx(50 / 120 - 1)
    assert out["history_years"] == 11


def test_history_shorter_than_requested_is_reported():
    revenue = [("2024-12-31", 100.0), ("2025-12-31", 150.0)]
    ebit = [("2024-12-31", 10.0), ("2025-12-31", 30.0)]
    out = history_stats(revenue, ebit, last_n=5)
    assert out["avg_margin_years"] == 2
    assert out["worst_2y_revenue_change"] is None


BAL = [
    stock("cash", "2026-06-30", 20.0),
    stock("short_term_investments", "2026-06-30", 50.0),
    stock("lt_marketable", "2026-06-30", 5.0),
    stock("equity", "2026-06-30", 400.0),
    stock("finance_lease_liability", "2026-06-30", 60.0),
    stock("debt_lt_current", "2026-06-30", 10.0),
    stock("debt_lt_noncurrent", "2026-06-30", 30.0),
    stock("commercial_paper", "2026-06-30", 2.0),
]


def test_balance_adds_short_term_borrowing_to_long_term_debt_and_nets_cash_like_assets():
    out = balance(BAL, "2026-06-30")
    assert out["debt"] == pytest.approx(42.0)
    assert out["debt_recipe"] == "debt_lt_current+debt_lt_noncurrent (+commercial_paper)"
    assert out["finance_leases"] == pytest.approx(60.0)
    assert out["cash_like"] == pytest.approx(75.0)
    assert out["net_debt"] == pytest.approx(42 + 60 - 75)
    assert out["invested_capital"] == pytest.approx(400 + 42 + 60 - 75)


def test_balance_prefers_the_total_debt_tag():
    out = balance([*BAL, stock("debt_total", "2026-06-30", 41.0)], "2026-06-30")
    assert out["debt"] == pytest.approx(43.0)
    assert out["debt_recipe"].startswith("debt_total")


def test_balance_without_any_debt_tag_says_so():
    rows = [
        r for r in BAL if not r["metric"].startswith("debt") and r["metric"] != "commercial_paper"
    ]
    out = balance(rows, "2026-06-30")
    assert out["debt"] == 0.0
    assert out["debt_recipe"] == "none tagged"


def test_balance_reads_items_dated_the_balance_date_only():
    out = balance([*BAL, stock("cash", "2026-03-31", 999.0)], "2026-06-30")
    assert out["cash_like"] == pytest.approx(75.0)
    with pytest.raises(ValueError, match="equity"):
        balance([r for r in BAL if r["metric"] != "equity"], "2026-06-30")


def test_tax_rate_is_the_effective_rate_within_bounds_or_the_statutory_rate():
    assert tax_rate(income_tax=20.0, pretax=100.0, statutory=0.25) == (0.20, "effective")
    assert tax_rate(income_tax=50.0, pretax=100.0, statutory=0.25) == (0.35, "effective, capped")
    assert tax_rate(income_tax=-5.0, pretax=100.0, statutory=0.25) == (0.0, "effective, floored")
    assert tax_rate(income_tax=5.0, pretax=-10.0, statutory=0.25) == (0.25, "statutory")
    assert tax_rate(income_tax=None, pretax=None, statutory=0.3062) == (0.3062, "statutory")


from portfolio_analyzer.ai_bubble.fundamentals import (  # noqa: E402
    base_from_rows,
    ebit_fiscal_years,
)


def _company(with_operating_income=True):
    rows = list(REVENUE) + list(BAL)
    for start, end, rev in [
        ("2024-01-01", "2024-12-31", 800.0),
        ("2025-01-01", "2025-12-31", 1000.0),
        ("2025-01-01", "2025-06-30", 450.0),
        ("2024-01-01", "2024-06-30", 380.0),
        ("2026-01-01", "2026-06-30", 600.0),
    ]:
        if with_operating_income:
            rows.append(flow("operating_income", start, end, rev * 0.3))
        rows += [
            flow("cost_of_revenue", start, end, rev * 0.5),
            flow("rnd", start, end, rev * 0.1),
            flow("sga", start, end, rev * 0.1),
        ]
        rows += [
            flow("pretax_income", start, end, rev * 0.3),
            flow("income_tax", start, end, rev * 0.3 * 0.2),
        ]
    return rows


def test_base_reads_ttm_growth_margin_tax_and_capital_turnover():
    base = base_from_rows(_company(), statutory_tax=0.25)
    assert base["end"] == "2026-06-30"
    assert base["revenue"] == pytest.approx(1150.0)
    assert base["g0"] == pytest.approx(1150 / 870 - 1)
    assert base["margin"] == pytest.approx(0.3)
    assert base["ebit_method"] == "operating_income"
    assert base["tax_rate"] == pytest.approx(0.2)
    assert base["sales_to_capital"] == pytest.approx(1150 / (400 + 42 + 60 - 75))
    assert base["roic"] == pytest.approx(1150 * 0.3 * 0.8 / (400 + 42 + 60 - 75))
    assert base["evaluable"] is True


def test_operating_income_untagged_is_rebuilt_from_its_parts():
    base = base_from_rows(_company(with_operating_income=False), statutory_tax=0.25)
    assert base["margin"] == pytest.approx(0.3)
    assert base["ebit_method"] == "revenue - cost_of_revenue - rnd - sga"


def test_operating_income_of_an_older_period_is_not_mixed_with_current_revenue():
    rows = [
        r
        for r in _company()
        if not (r["metric"] == "operating_income" and r["period_end"] >= "2025-06-30")
    ]
    rows = [r for r in rows if r["metric"] not in ("cost_of_revenue", "rnd", "sga")]
    base = base_from_rows(rows, statutory_tax=0.25)
    assert base["evaluable"] is False
    assert "operating income" in base["not_evaluable_because"]


def test_ebit_fiscal_years_fall_back_to_parts_year_by_year():
    rows = [
        r
        for r in _company()
        if not (r["metric"] == "operating_income" and r["period_end"] == "2025-12-31")
    ]
    assert ebit_fiscal_years(rows) == [("2024-12-31", 240.0), ("2025-12-31", 300.0)]


def test_negative_invested_capital_is_not_evaluable():
    # equity -30 with debt 42 + leases 60 - cash 75: capital of -3
    rows = [r for r in _company() if r["metric"] != "equity"] + [
        stock("equity", "2026-06-30", -30.0)
    ]
    base = base_from_rows(rows, statutory_tax=0.25)
    assert base["evaluable"] is False
    assert "invested capital" in base["not_evaluable_because"]


def test_total_marketable_securities_stand_in_only_when_neither_part_is_tagged():
    only_total = [r for r in BAL if r["metric"] not in ("short_term_investments", "lt_marketable")]
    only_total.append(stock("marketable_total", "2026-06-30", 30.0))
    assert balance(only_total, "2026-06-30")["cash_like"] == pytest.approx(20 + 30)
    both = [*BAL, stock("marketable_total", "2026-06-30", 999.0)]
    assert balance(both, "2026-06-30")["cash_like"] == pytest.approx(75.0)


def test_japanese_equity_columns_stand_in_for_equity():
    rows = [r for r in BAL if r["metric"] != "equity"]
    assert (
        balance([*rows, stock("equity_parent", "2026-06-30", 300.0)], "2026-06-30")["equity"]
        == 300.0
    )
    assert (
        balance([*rows, stock("equity_total", "2026-06-30", 310.0)], "2026-06-30")["equity"]
        == 310.0
    )


def test_tax_without_a_tax_line_is_pretax_less_net_income():
    rows = [r for r in _company() if r["metric"] != "income_tax"]
    for r in [r for r in _company() if r["metric"] == "pretax_income"]:
        rows.append(dict(r, metric="net_income", value=r["value"] * 0.75))
    base = base_from_rows(rows, statutory_tax=0.3062)
    assert base["tax_rate"] == pytest.approx(0.25)
    assert base["tax_note"] == "effective (pretax less net income)"


def test_long_term_investments_are_netted_with_cash_and_left_out_of_operating_capital():
    rows = [
        *BAL,
        stock("equity_securities_nrdfv", "2026-06-30", 30.0),
        stock("equity_method", "2026-06-30", 8.0),
    ]
    out = balance(rows, "2026-06-30")
    assert out["investments"] == pytest.approx(38.0)
    assert (
        out["investments_recipe"]
        == "equity_securities_fv+equity_securities_nrdfv+equity_method (present: equity_securities_nrdfv+equity_method)"
    )
    assert out["net_debt"] == pytest.approx(42 + 60 - 75 - 38)
    assert out["invested_capital"] == pytest.approx(400 + 42 + 60 - 75 - 38)


def test_a_total_long_term_investment_tag_is_not_added_to_its_parts():
    rows = [
        *BAL,
        stock("lt_investments", "2026-06-30", 36.0),
        stock("equity_method", "2026-06-30", 12.0),
    ]
    out = balance(rows, "2026-06-30")
    assert out["investments"] == pytest.approx(36.0)
    assert out["investments_recipe"] == "lt_investments"


def test_no_investment_tag_means_none_netted():
    out = balance(BAL, "2026-06-30")
    assert (out["investments"], out["investments_recipe"]) == (0.0, "none tagged")


def test_pretax_untagged_is_net_income_plus_tax():
    rows = [r for r in _company() if r["metric"] != "pretax_income"]
    for r in [r for r in _company() if r["metric"] == "income_tax"]:
        rows.append(dict(r, metric="net_income", value=r["value"] * 4))  # tax 20% of pretax
    base = base_from_rows(rows, statutory_tax=0.25)
    assert base["tax_rate"] == pytest.approx(0.2)
    assert base["tax_note"] == "effective (net income plus tax)"


from portfolio_analyzer.ai_bubble.fundamentals import quarters  # noqa: E402

QUARTERLY = [
    flow("net_income", "2025-01-01", "2025-03-31", 10.0),
    flow("net_income", "2025-01-01", "2025-06-30", 25.0),
    flow("net_income", "2025-04-01", "2025-06-30", 15.0),
    flow("net_income", "2025-01-01", "2025-09-30", 45.0),
    flow("net_income", "2025-01-01", "2025-12-31", 70.0),
    flow("net_income", "2026-01-01", "2026-03-31", 30.0),
]


def test_quarters_take_three_month_rows_and_difference_the_year_to_date():
    assert quarters(QUARTERLY, "net_income") == [
        ("2025-03-31", 10.0),
        ("2025-06-30", 15.0),
        ("2025-09-30", 20.0),
        ("2025-12-31", 25.0),
        ("2026-03-31", 30.0),
    ]


def test_a_quarter_without_its_prior_year_to_date_is_left_out():
    rows = [r for r in QUARTERLY if r["period_end"] != "2025-09-30"]
    assert [end for end, _ in quarters(rows, "net_income")] == [
        "2025-03-31",
        "2025-06-30",
        "2026-03-31",
    ]
