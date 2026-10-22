"""Whether cash on hand and operating cash flow carry the committed payments (spec 6).

The balance runs quarter by quarter, ``B_q = B_q-1 + operating CF - debt
principal - investment``, from the cash that is free to use. Operating cash
flow is already after interest, tax and operating lease payments, so none of
these is deducted again; a lease's principal goes to debt principal once. The
end-of-window shortfall and the deepest shortfall inside the window are kept
apart, so cash arriving later cannot hide a quarter that runs dry. A payment
whose amount is unknown leaves the path unevaluated, which is not a zero.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from portfolio_analyzer.ai_bubble.fundamentals import QUARTER_DAYS, SHORT_TERM_DEBT, YEAR_DAYS

PATH_INPUTS = ("operating_cf", "debt_principal", "investment")
DEBT_SCHEDULE = ("debt_due_remainder_fy", "debt_due_y1", "debt_due_y2")
LEASE_SCHEDULE = ("finance_lease_due_y1", "finance_lease_due_y2")
QUARTERLY_FORMS = ("10-Q", "10-Q/A")
WINDOW = 8


def funding_path(cash: float, quarters: list[dict[str, Any]]) -> dict[str, Any]:
    """Balances ``B_0..B_n``, the end shortfall ``max(-B_n, 0)`` and the deepest
    intra-window shortfall ``max(-min(B_0..B_n), 0)``."""
    unknown = [
        f"{name} in quarter {i}"
        for i, quarter in enumerate(quarters, start=1)
        for name in PATH_INPUTS
        if quarter.get(name) is None
    ]
    if unknown:
        return {
            "status": "unevaluated",
            "reason": "unknown " + ", ".join(unknown),
            "balances": None,
            "end_shortfall": None,
            "max_intra_shortfall": None,
        }
    balances = [cash]
    for quarter in quarters:
        balances.append(
            balances[-1]
            + quarter["operating_cf"]
            - quarter["debt_principal"]
            - quarter["investment"]
        )
    return {
        "status": "ok",
        "balances": balances,
        "end_shortfall": max(-balances[-1], 0.0),
        "max_intra_shortfall": max(-min(balances), 0.0),
    }


def current_schedule(
    rows: list[dict[str, Any]], metrics: tuple[str, ...], on: str
) -> dict[str, Any]:
    """The maturity table of the latest annual report on or before ``on``: the latest
    date carrying any of ``metrics``, unless it is older than the last fiscal-year end
    (one year back without an annual row). A table last tagged years ago says nothing
    about today's debt, so it is reported as stale and not used. A twelve-month column
    in a quarterly report (Amazon's trailing cash flows) does not end a fiscal year."""
    years = [
        r["period_end"]
        for r in rows
        if r["period_start"] != r["period_end"]
        and r["period_end"] <= on
        and r.get("form") not in QUARTERLY_FORMS
        and YEAR_DAYS[0]
        <= (date.fromisoformat(r["period_end"]) - date.fromisoformat(r["period_start"])).days + 1
        <= YEAR_DAYS[1]
    ]
    floor = (
        max(years) if years else (date.fromisoformat(on) - timedelta(days=YEAR_DAYS[1])).isoformat()
    )
    found = [
        r
        for r in rows
        if r["metric"] in metrics
        and r["period_start"] == r["period_end"] <= on
        and r["value"] is not None
    ]
    if not found:
        return {"date": None, "values": {}, "stale_date": None}
    day = max(r["period_end"] for r in found)
    if day < floor:
        return {"date": None, "values": {}, "stale_date": day}
    return {
        "date": day,
        "values": {r["metric"]: r["value"] for r in found if r["period_end"] == day},
        "stale_date": None,
    }


def principal_plan(
    *,
    debt: float,
    leases: float,
    at: dict[str, float],
    debt_schedule: dict[str, float],
    lease_schedule: dict[str, float],
    first: bool = False,
) -> dict[str, Any]:
    """Principal falling due in each quarter of the window (prereg funding_details).

    A schedule's first year (with the rest of the fiscal year) is spread over quarters
    1-4 and its second over 5-8, or put in the first quarter of each year with
    ``first``. Commercial paper and short-term borrowings fall due in quarter 1.
    Without a schedule the current portion is spread over quarters 1-4 and the rest
    falls due in quarter 5, or all debt in quarter 1 where the split is not tagged:
    the worst case for the window, kept apart as payments of unknown timing."""
    items: list[dict[str, Any]] = []
    notes: list[str] = []

    def spread(name: str, amount: float, year: int) -> None:
        span = range(0, 4) if year == 1 else range(4, WINDOW)
        if first:
            items.append({"name": name, "quarter": span[0], "amount": amount, "known": True})
        else:
            items.extend(
                {"name": name, "quarter": q, "amount": amount / 4, "known": True} for q in span
            )

    def unknown(name: str, amount: float, quarter: int, note: str) -> None:
        if amount > 0:
            items.append({"name": name, "quarter": quarter, "amount": amount, "known": False})
            notes.append(note)

    short = sum(at.get(m, 0.0) for m in SHORT_TERM_DEBT)
    if short:
        items.append(
            {
                "name": "short-term borrowings and commercial paper",
                "quarter": 0,
                "amount": short,
                "known": True,
            }
        )
    rest = debt - short
    if debt_schedule:
        year_one = debt_schedule.get("debt_due_remainder_fy", 0.0) + debt_schedule.get(
            "debt_due_y1", 0.0
        )
        spread("debt due within the year", year_one, 1)
        spread("debt due in year two", debt_schedule.get("debt_due_y2", 0.0), 2)
    elif at.get("debt_lt_current") is None:
        unknown(
            "debt, timing unknown",
            rest,
            0,
            "no maturity schedule or current split: all debt assumed due in quarter 1",
        )
    else:
        spread("current portion of debt", at["debt_lt_current"], 1)
        unknown(
            "non-current debt, timing unknown",
            rest - at["debt_lt_current"],
            4,
            "no maturity schedule: non-current debt assumed due in quarter 5",
        )
    if lease_schedule:
        spread(
            "finance lease payments in year one", lease_schedule.get("finance_lease_due_y1", 0.0), 1
        )
        spread(
            "finance lease payments in year two", lease_schedule.get("finance_lease_due_y2", 0.0), 2
        )
    elif leases > 0:
        current = at.get("finance_lease_current", 0.0)
        spread("current lease liabilities", current, 1)
        unknown(
            "non-current lease liabilities, timing unknown",
            leases - current,
            4,
            "no lease schedule: non-current lease liabilities assumed due in quarter 5",
        )
    by_quarter, known = [0.0] * WINDOW, [0.0] * WINDOW
    for item in items:
        by_quarter[item["quarter"]] += item["amount"]
        if item["known"]:
            known[item["quarter"]] += item["amount"]
    return {
        "items": items,
        "by_quarter": by_quarter,
        "known_by_quarter": known,
        "notes": notes,
        "worst_case": any(not item["known"] for item in items),
    }


def payment_path(
    cash: float, operating_cf: list[float], plan: dict[str, Any], investment: float
) -> dict[str, Any]:
    """The path with the plan's principal and ``investment`` in every quarter. A
    shortfall that disappears once the payments of unknown timing leave the window
    appears only under the worst-case assumption and is unevaluated (prereg)."""

    def run(principal: list[float]) -> dict[str, Any]:
        quarters = [
            {"operating_cf": o, "debt_principal": p, "investment": investment}
            for o, p in zip(operating_cf, principal, strict=True)
        ]
        return funding_path(cash, quarters) | {"quarters": quarters}

    path = run(plan["by_quarter"])
    if path["status"] != "ok" or path["max_intra_shortfall"] == 0 or not plan["worst_case"]:
        return path
    known = run(plan["known_by_quarter"])["max_intra_shortfall"]
    if known > 0:
        return path | {"shortfall_without_unknown_timing": known}
    return path | {
        "status": "unevaluated",
        "reason": "a shortfall only when debt of unknown timing falls due inside the window",
    }


def duplicate_payments(quarters: list[dict[str, Any]]) -> list[str]:
    """Payment ids filed under more than one category (a lease principal counted as
    both debt repayment and investment is counted twice)."""
    categories: dict[str, set[str]] = {}
    for quarter in quarters:
        for payment in quarter.get("payments", []):
            categories.setdefault(payment["id"], set()).add(payment["category"])
    return sorted(pid for pid, seen in categories.items() if len(seen) > 1)


def f_classify(central: dict[str, Any], stress: dict[str, Any]) -> str:
    """Spec 8: a central shortfall supports fragility, none in either case weakens it,
    a stress-only shortfall is mixed; an unevaluated path is データ不足."""
    if central["status"] != "ok" or stress["status"] != "ok":
        return "データ不足"
    if central["max_intra_shortfall"] > 0:
        return "支持"
    if stress["max_intra_shortfall"] > 0:
        return "混在"
    return "弱める"


def funding_boundary(
    cash: float, quarters: list[dict[str, Any]], *, high: float = 3.0, tolerance: float = 1e-12
) -> dict[str, Any]:
    """The multiple of every quarter's operating cash flow at which the deepest shortfall
    reaches zero, and the share of it that can be lost before a shortfall appears."""
    if any(q["operating_cf"] is None or q["operating_cf"] <= 0 for q in quarters):
        return {
            "ocf_multiplier": None,
            "ocf_loss_tolerated": None,
            "note": "operating cash flow not positive in every quarter",
        }

    def low_point(m: float) -> float:
        scaled = [dict(q, operating_cf=q["operating_cf"] * m) for q in quarters]
        return min(funding_path(cash, scaled)["balances"])

    if low_point(0.0) >= 0:
        return {
            "ocf_multiplier": 0.0,
            "ocf_loss_tolerated": 1.0,
            "note": "cash on hand covers the window",
        }
    if low_point(high) < 0:
        return {
            "ocf_multiplier": None,
            "ocf_loss_tolerated": None,
            "note": f"needs above {high}x the operating cash flow",
        }
    lo, hi = 0.0, high
    while hi - lo > tolerance:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if low_point(mid) >= 0 else (mid, hi)
    return {"ocf_multiplier": hi, "ocf_loss_tolerated": 1.0 - hi, "note": ""}


def quarterize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Single quarters of one metric from its year-to-date rows: a three-month row as
    reported, else the year to date less the one a quarter earlier with the same start.
    A year to date without that comparative comes back with its reason, value None."""
    items = [
        (
            date.fromisoformat(r["period_start"]),
            date.fromisoformat(r["period_end"]),
            float(r["value"]),
        )
        for r in rows
        if r["value"] is not None and r["period_start"] != r["period_end"]
    ]
    out = []
    for end in sorted({e for _, e, _ in items}):
        at_end = [(s, e, v) for s, e, v in items if e == end]
        direct = [x for x in at_end if QUARTER_DAYS[0] <= (x[1] - x[0]).days + 1 <= QUARTER_DAYS[1]]
        if direct:
            s, e, v = direct[0]
            out.append({"start": s.isoformat(), "end": e.isoformat(), "value": v, "status": "ok"})
            continue
        start, _, value = max(at_end, key=lambda x: (x[1] - x[0]).days)
        earlier = [
            (s, e, v)
            for s, e, v in items
            if s == start and QUARTER_DAYS[0] <= (end - e).days <= QUARTER_DAYS[1]
        ]
        if earlier:
            _, prior_end, prior = earlier[0]
            out.append(
                {
                    "start": (prior_end + timedelta(days=1)).isoformat(),
                    "end": end.isoformat(),
                    "value": value - prior,
                    "status": "ok",
                }
            )
        else:
            out.append(
                {
                    "start": None,
                    "end": end.isoformat(),
                    "value": None,
                    "status": f"missing:no year-to-date row one quarter before {end.isoformat()} with start {start.isoformat()}",
                }
            )
    return out
