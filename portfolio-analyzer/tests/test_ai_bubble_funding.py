"""Funding path over eight quarters, single quarters from year-to-date flows and the F label (spec 6)."""

from __future__ import annotations

import pytest
from portfolio_analyzer.ai_bubble.funding import (
    current_schedule,
    duplicate_payments,
    f_classify,
    funding_boundary,
    funding_path,
    payment_path,
    principal_plan,
    quarterize,
)


def q(ocf=0.0, principal=0.0, investment=0.0):
    return {"operating_cf": ocf, "debt_principal": principal, "investment": investment}


def test_a_quarter_short_of_cash_shows_its_shortfall():
    out = funding_path(100.0, [q(ocf=20.0, principal=80.0, investment=60.0)])
    assert out["balances"] == pytest.approx([100.0, -20.0])
    assert out["end_shortfall"] == pytest.approx(20.0)
    assert out["max_intra_shortfall"] == pytest.approx(20.0)
    assert (
        funding_path(100.0, [q(ocf=40.0, principal=80.0, investment=60.0)])["end_shortfall"] == 0.0
    )


def test_cash_arriving_later_does_not_hide_an_intra_period_gap():
    out = funding_path(100.0, [q(principal=120.0), q(ocf=40.0)])
    assert out["balances"] == pytest.approx([100.0, -20.0, 20.0])
    assert out["end_shortfall"] == 0.0
    assert out["max_intra_shortfall"] == pytest.approx(20.0)
    assert out["status"] == "ok"


def test_an_unknown_payment_is_unevaluated_not_zero():
    out = funding_path(
        100.0, [q(ocf=10.0), {"operating_cf": 10.0, "debt_principal": None, "investment": 0.0}]
    )
    assert out["status"] == "unevaluated"
    assert "debt_principal" in out["reason"] and "quarter 2" in out["reason"]
    assert out["max_intra_shortfall"] is None


def test_a_payment_in_two_categories_is_a_duplicate():
    quarters = [
        {
            "payments": [
                {"id": "lease-1", "category": "debt_principal"},
                {"id": "capex", "category": "investment"},
            ]
        },
        {"payments": [{"id": "lease-1", "category": "investment"}]},
    ]
    assert duplicate_payments(quarters) == ["lease-1"]
    assert duplicate_payments([{"payments": [{"id": "a", "category": "investment"}]}] * 2) == []


@pytest.mark.parametrize(
    ("central", "stress", "label"),
    [
        (5.0, 9.0, "支持"),
        (0.0, 0.0, "弱める"),
        (0.0, 3.0, "混在"),
        (None, 3.0, "データ不足"),
        (0.0, None, "データ不足"),
    ],
)
def test_f_classify(central, stress, label):
    def path(shortfall):
        if shortfall is None:
            return {"status": "unevaluated", "max_intra_shortfall": None}
        return {"status": "ok", "max_intra_shortfall": shortfall}

    assert f_classify(path(central), path(stress)) == label


def flow(start, end, value, metric="operating_cf"):
    return {
        "metric": metric,
        "period_start": start,
        "period_end": end,
        "value": value,
        "accounting_basis": "US-GAAP",
    }


def test_quarterize_differences_the_year_to_date_and_explains_gaps():
    rows = [
        flow("2025-01-01", "2025-03-31", 60.0),
        flow("2025-01-01", "2025-06-30", 150.0),
        flow("2025-01-01", "2025-12-31", 300.0),  # the nine-month row is missing
    ]
    out = quarterize(rows)
    assert [(r["start"], r["end"], r["value"], r["status"]) for r in out[:2]] == [
        ("2025-01-01", "2025-03-31", 60.0, "ok"),
        ("2025-04-01", "2025-06-30", 90.0, "ok"),
    ]
    assert out[2]["end"] == "2025-12-31" and out[2]["value"] is None
    assert out[2]["status"].startswith("missing:")


def test_funding_boundary_is_the_operating_cash_share_that_can_be_lost():
    # cash 100 against 50 of principal and 10 of investment a quarter: with operating
    # cash 10m a quarter the low point is quarter 8, 100 + 80m - 130 = 0 at m = 0.375
    quarters = [q(ocf=10.0, principal=50.0, investment=10.0)] + [q(ocf=10.0, investment=10.0)] * 7
    out = funding_boundary(100.0, quarters)
    assert out["ocf_multiplier"] == pytest.approx(0.375, abs=1e-9)
    assert out["ocf_loss_tolerated"] == pytest.approx(0.625, abs=1e-9)


def test_cash_alone_covering_the_window_tolerates_losing_all_operating_cash():
    out = funding_boundary(1000.0, [q(ocf=10.0, principal=50.0, investment=10.0)] * 8)
    assert (out["ocf_multiplier"], out["ocf_loss_tolerated"]) == (0.0, 1.0)


def test_a_boundary_beyond_the_search_range_is_reported_as_such():
    out = funding_boundary(0.0, [q(ocf=10.0, principal=1000.0)] + [q(ocf=10.0)] * 7)
    assert out["ocf_multiplier"] is None
    assert "above" in out["note"]


def test_no_boundary_without_positive_operating_cash():
    out = funding_boundary(100.0, [q(ocf=-5.0, investment=10.0)] * 8)
    assert out["ocf_multiplier"] is None
    assert "not positive" in out["note"]


def plan_for(debt=0.0, leases=0.0, at=None, debt_schedule=None, lease_schedule=None, **kw):
    return principal_plan(
        debt=debt,
        leases=leases,
        at=at or {},
        debt_schedule=debt_schedule or {},
        lease_schedule=lease_schedule or {},
        **kw,
    )


def test_a_maturity_schedule_spreads_year_one_and_year_two_and_paper_is_due_first():
    plan = plan_for(
        debt=100.0,
        at={"commercial_paper": 10.0},
        debt_schedule={"debt_due_remainder_fy": 8.0, "debt_due_y1": 12.0, "debt_due_y2": 40.0},
    )
    assert plan["by_quarter"] == pytest.approx([15.0, 5.0, 5.0, 5.0, 10.0, 10.0, 10.0, 10.0])
    assert plan["known_by_quarter"] == pytest.approx(plan["by_quarter"])
    assert plan["worst_case"] is False


def test_without_a_schedule_the_rest_of_the_debt_falls_due_in_quarter_five_as_the_worst_case():
    plan = plan_for(debt=100.0, at={"debt_lt_current": 20.0})
    assert plan["by_quarter"] == pytest.approx([5.0, 5.0, 5.0, 5.0, 80.0, 0.0, 0.0, 0.0])
    assert plan["known_by_quarter"] == pytest.approx([5.0, 5.0, 5.0, 5.0, 0.0, 0.0, 0.0, 0.0])
    assert plan["worst_case"] is True
    untagged = plan_for(debt=100.0)
    assert untagged["by_quarter"] == pytest.approx([100.0] + [0.0] * 7)
    assert untagged["known_by_quarter"] == pytest.approx([0.0] * 8)


def test_lease_payments_follow_their_schedule_or_the_current_split():
    plan = plan_for(
        leases=50.0, lease_schedule={"finance_lease_due_y1": 8.0, "finance_lease_due_y2": 4.0}
    )
    assert plan["by_quarter"] == pytest.approx([2.0] * 4 + [1.0] * 4)
    assert plan["worst_case"] is False
    fallback = plan_for(leases=50.0, at={"finance_lease_current": 8.0})
    assert fallback["by_quarter"] == pytest.approx([2.0] * 4 + [42.0, 0.0, 0.0, 0.0])
    assert fallback["worst_case"] is True


def test_principal_first_puts_each_years_amount_in_its_first_quarter():
    plan = plan_for(
        debt=100.0, debt_schedule={"debt_due_y1": 12.0, "debt_due_y2": 40.0}, first=True
    )
    assert plan["by_quarter"] == pytest.approx([12.0, 0.0, 0.0, 0.0, 40.0, 0.0, 0.0, 0.0])


def row(metric, end, value, start=None):
    return {"metric": metric, "period_start": start or end, "period_end": end, "value": value}


def test_a_schedule_older_than_the_latest_fiscal_year_end_is_not_current():
    metrics = ("debt_due_y1", "debt_due_y2")
    rows = [
        row("revenue", "2025-10-26", 30.0, start="2024-10-28"),
        row("debt_due_y1", "2010-10-31", 1.0),
        row("debt_due_y2", "2010-10-31", 2.0),
    ]
    assert current_schedule(rows, metrics, "2026-07-26") == {
        "date": None,
        "values": {},
        "stale_date": "2010-10-31",
    }
    rows.append(row("debt_due_y1", "2025-10-26", 3.0))
    assert current_schedule(rows, metrics, "2026-07-26") == {
        "date": "2025-10-26",
        "values": {"debt_due_y1": 3.0},
        "stale_date": None,
    }
    no_annual = [row("debt_due_y1", "2025-06-30", 1.0)]
    assert current_schedule(no_annual, metrics, "2026-07-26")["stale_date"] == "2025-06-30"


def test_a_shortfall_only_when_debt_of_unknown_timing_falls_due_is_unevaluated():
    plan = plan_for(debt=100.0, at={"debt_lt_current": 0.0})
    out = payment_path(50.0, [5.0] * 8, plan, investment=5.0)
    assert out["status"] == "unevaluated"
    assert out["max_intra_shortfall"] == pytest.approx(50.0)
    stays = payment_path(50.0, [0.0] * 8, plan, investment=10.0)
    assert stays["status"] == "ok"
    assert stays["max_intra_shortfall"] == pytest.approx(130.0)
    assert stays["shortfall_without_unknown_timing"] == pytest.approx(30.0)


def test_a_twelve_month_column_in_a_quarterly_report_is_not_a_fiscal_year_end():
    rows = [
        row("revenue", "2025-12-31", 700.0, start="2025-01-01") | {"form": "10-K"},
        row("operating_cf", "2026-06-30", 160.0, start="2025-07-01") | {"form": "10-Q"},
        row("debt_due_y1", "2025-12-31", 2.8),
    ]
    assert current_schedule(rows, ("debt_due_y1",), "2026-06-30")["date"] == "2025-12-31"
