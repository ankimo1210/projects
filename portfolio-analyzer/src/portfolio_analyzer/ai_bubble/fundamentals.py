"""The inputs of the reverse DCF, built from as-of rows (``select_as_of`` output).

Flows are reported year to date, so the last twelve months at a quarter end are
the last fiscal year plus this year to date less last year's same period;
periods match within days so 52/53-week years work. Only the accounting basis
of the latest period is used for a trailing figure; fiscal-year history takes
each year in the latest basis that reports it.

Balance sheet items are read at one date. Debt is taken from the first
complete recipe below (filers tag it differently: Oracle as notes and loans,
CoreWeave only as the carrying amount of its instruments), plus short-term
borrowing and commercial paper, which sit outside long-term debt. Operating
lease liabilities stay out of debt because the operating lease cost is already
inside operating income under US GAAP; finance leases are debt. Investments
whose returns sit outside operating income (marketable securities, equity
stakes, equity-method investees) are netted like cash and left out of
operating capital, so the value of operations is compared with the cash flow
of operations.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

YEAR_DAYS = (350, 380)
MATCH_DAYS = 10
DEBT_RECIPES = (
    ("debt_total",),
    ("debt_lt_current", "debt_lt_noncurrent"),
    ("debt_lt_noncurrent",),
    ("debt_combined",),
    ("notes_and_loans_noncurrent", "notes_payable_current"),
    ("notes_and_loans_noncurrent",),
    ("debt_instruments",),
)
SHORT_TERM_DEBT = ("short_term_borrowings", "commercial_paper")
CASH_LIKE = ("cash", "short_term_investments", "lt_marketable")
LT_INVESTMENT_TOTALS = ("lt_investments", "other_lt_investments")
LT_INVESTMENT_PARTS = ("equity_securities_fv", "equity_securities_nrdfv", "equity_method")
QUARTER_DAYS = (80, 100)


def _date(text: str) -> date:
    return date.fromisoformat(text)


def _year_before(day: date) -> date:
    try:
        return day.replace(year=day.year - 1)
    except ValueError:  # 29 February
        return day.replace(year=day.year - 1, day=28)


def _durations(rows: list[dict[str, Any]], metric: str) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if (
            row["metric"] != metric
            or row["value"] is None
            or row["period_start"] == row["period_end"]
        ):
            continue
        start, end = _date(row["period_start"]), _date(row["period_end"])
        out.append(
            {
                "start": start,
                "end": end,
                "days": (end - start).days + 1,
                "value": float(row["value"]),
                "basis": row["accounting_basis"],
            }
        )
    return out


def _is_year(item: dict[str, Any]) -> bool:
    return YEAR_DAYS[0] <= item["days"] <= YEAR_DAYS[1]


def _ttm_at(items: list[dict[str, Any]], end: date) -> float | None:
    at_end = [i for i in items if i["end"] == end]
    if not at_end:
        return None
    years = [i for i in at_end if _is_year(i)]
    if years:
        return years[0]["value"]
    ytd = max(at_end, key=lambda i: i["days"])
    fy_end = ytd["start"] - timedelta(days=1)
    prev_fy = [i for i in items if _is_year(i) and abs((i["end"] - fy_end).days) <= MATCH_DAYS // 2]
    target = _year_before(end)
    prev_ytd = [
        i
        for i in items
        if abs((i["end"] - target).days) <= MATCH_DAYS
        and abs(i["days"] - ytd["days"]) <= MATCH_DAYS
        and not _is_year(i)
    ]
    if not prev_fy or not prev_ytd:
        return None
    best_ytd = min(
        prev_ytd, key=lambda i: (abs(i["days"] - ytd["days"]), abs((i["end"] - target).days))
    )
    return prev_fy[0]["value"] + ytd["value"] - best_ytd["value"]


def _latest_basis(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    last = max(i["end"] for i in items)
    bases = {i["basis"] for i in items if i["end"] == last}
    if len(bases) > 1:
        raise ValueError(f"more than one accounting basis at {last}: {sorted(bases)}")
    basis = bases.pop()
    return [i for i in items if i["basis"] == basis]


def ttm(rows: list[dict[str, Any]], metric: str) -> dict[str, Any] | None:
    """Trailing twelve months at the latest end that can be built, and a year before it."""
    items = _latest_basis(_durations(rows, metric))
    for end in sorted({i["end"] for i in items}, reverse=True):
        value = _ttm_at(items, end)
        if value is None:
            continue
        target = _year_before(end)
        prev_value, prev_end = None, None
        for other in sorted(
            {i["end"] for i in items if abs((i["end"] - target).days) <= MATCH_DAYS}
        ):
            prev_value = _ttm_at(items, other)
            if prev_value is not None:
                prev_end = other
                break
        return {
            "value": value,
            "end": end.isoformat(),
            "prev_value": prev_value,
            "prev_end": prev_end.isoformat() if prev_end else None,
            "basis": items[0]["basis"],
        }
    return None


def quarters(rows: list[dict[str, Any]], metric: str) -> list[tuple[str, float]]:
    """(end, value) of single fiscal quarters in the latest basis: three-month rows, else
    the year to date less the year to date one quarter earlier with the same start."""
    items = _latest_basis(_durations(rows, metric))
    out: dict[date, float] = {}
    for end in sorted({i["end"] for i in items}):
        at_end = [i for i in items if i["end"] == end]
        direct = [i for i in at_end if QUARTER_DAYS[0] <= i["days"] <= QUARTER_DAYS[1]]
        if direct:
            out[end] = direct[0]["value"]
            continue
        for ytd in sorted(at_end, key=lambda i: i["days"]):
            earlier = [
                i
                for i in items
                if i["start"] == ytd["start"]
                and QUARTER_DAYS[0] <= (ytd["end"] - i["end"]).days <= QUARTER_DAYS[1]
            ]
            if earlier:
                out[end] = ytd["value"] - earlier[0]["value"]
                break
    return [(end.isoformat(), value) for end, value in sorted(out.items())]


def fiscal_years(rows: list[dict[str, Any]], metric: str) -> list[tuple[str, float]]:
    """(end, value) of each twelve-month period; a year reported in several bases takes the latest one."""
    items = [i for i in _durations(rows, metric) if _is_year(i)]
    if not items:
        return []
    latest = max(items, key=lambda i: i["end"])["basis"]
    by_end: dict[date, dict[str, Any]] = {}
    for item in items:
        held = by_end.get(item["end"])
        if held is None or (item["basis"] == latest and held["basis"] != latest):
            by_end[item["end"]] = item
    return [(end.isoformat(), by_end[end]["value"]) for end in sorted(by_end)]


def history_stats(
    revenue: list[tuple[str, float]], ebit: list[tuple[str, float]], *, last_n: int = 5
) -> dict[str, Any]:
    """Average operating margin of the last ``last_n`` fiscal years, the lowest margin on
    record, and the worst change of revenue over two consecutive fiscal years."""
    ebit_by_end = dict(ebit)
    margins = [
        (end, ebit_by_end[end] / value)
        for end, value in revenue
        if end in ebit_by_end and value > 0
    ]
    recent = margins[-last_n:]
    worst = None
    for i in range(2, len(revenue)):
        (end0, rev0), (end2, rev2) = revenue[i - 2], revenue[i]
        gap = (_date(end2) - _date(end0)).days
        if 700 <= gap <= 760 and rev0 > 0:
            change = rev2 / rev0 - 1
            worst = change if worst is None else min(worst, change)
    return {
        "avg_margin": sum(m for _, m in recent) / len(recent) if recent else None,
        "avg_margin_years": len(recent),
        "min_margin": min(m for _, m in margins) if margins else None,
        "worst_2y_revenue_change": worst,
        "history_years": len(revenue),
        "first_year_end": revenue[0][0] if revenue else None,
    }


def _investments(items: dict[str, float]) -> tuple[float, str]:
    """Long-term investments: a total tag if there is one, else the equity securities and
    equity-method stakes that are tagged (a combined fair-value tag replaces its two parts)."""
    for total in LT_INVESTMENT_TOTALS:
        if total in items:
            return items[total], total
    parts = (
        ("equity_securities_combined", "equity_method")
        if "equity_securities_combined" in items
        else LT_INVESTMENT_PARTS
    )
    present = [p for p in parts if p in items]
    if not present:
        return 0.0, "none tagged"
    return sum(items[p] for p in present), f"{'+'.join(parts)} (present: {'+'.join(present)})"


def balance(rows: list[dict[str, Any]], on: str) -> dict[str, Any]:
    """Debt, finance leases, cash-like assets, long-term investments and equity at ``on``."""
    items = {
        r["metric"]: float(r["value"])
        for r in rows
        if r["period_start"] == on and r["period_end"] == on and r["value"] is not None
    }
    for alias in ("equity_parent", "equity_total"):  # 決算短信: owners' equity, else net assets
        if "equity" not in items and alias in items:
            items["equity"] = items[alias]
    if "equity" not in items:
        raise ValueError(f"no equity at {on}")
    debt, recipe = 0.0, "none tagged"
    for parts in DEBT_RECIPES:
        if all(p in items for p in parts):
            debt, recipe = sum(items[p] for p in parts), "+".join(parts)
            break
    extra = [p for p in SHORT_TERM_DEBT if items.get(p)]
    if extra:
        debt += sum(items[p] for p in extra)
        recipe = f"{recipe} (+{'+'.join(extra)})" if recipe != "none tagged" else "+".join(extra)
    if "finance_lease_liability" in items:
        leases = items["finance_lease_liability"]
    else:
        leases = items.get("finance_lease_current", 0.0) + items.get(
            "finance_lease_noncurrent", 0.0
        )
    cash_like = sum(items.get(p, 0.0) for p in CASH_LIKE)
    if "marketable_total" in items and not any(p in items for p in CASH_LIKE[1:]):
        cash_like += items["marketable_total"]  # KLA tags only the total of its debt securities
    investments, investments_recipe = _investments(items)
    return {
        "date": on,
        "debt": debt,
        "debt_recipe": recipe,
        "finance_leases": leases,
        "cash_like": cash_like,
        "cash_parts": {p: items[p] for p in (*CASH_LIKE, "marketable_total") if p in items},
        "investments": investments,
        "investments_recipe": investments_recipe,
        "equity": items["equity"],
        "net_debt": debt + leases - cash_like - investments,
        "invested_capital": items["equity"] + debt + leases - cash_like - investments,
    }


def tax_rate(
    *, income_tax: float | None, pretax: float | None, statutory: float
) -> tuple[float, str]:
    """Effective rate of the last twelve months within [0, 35%], else the statutory rate."""
    if income_tax is None or pretax is None or pretax <= 0:
        return statutory, "statutory"
    rate = income_tax / pretax
    if rate > 0.35:
        return 0.35, "effective, capped"
    if rate < 0:
        return 0.0, "effective, floored"
    return rate, "effective"


EBIT_PARTS = ("cost_of_revenue", "rnd", "sga")
PARTS_METHOD = "revenue - cost_of_revenue - rnd - sga"


def _ebit_ttm(
    rows: list[dict[str, Any]], revenue: dict[str, Any]
) -> tuple[float | None, str | None]:
    """Operating income of the revenue's twelve months; filers that stopped tagging it
    (KLA after 2015) are rebuilt from cost of revenue, R&D and SG&A."""
    reported = ttm(rows, "operating_income")
    if reported and reported["end"] == revenue["end"]:
        return reported["value"], "operating_income"
    parts = [ttm(rows, metric) for metric in EBIT_PARTS]
    if all(p and p["end"] == revenue["end"] for p in parts):
        return revenue["value"] - sum(p["value"] for p in parts), PARTS_METHOD
    return None, None


def ebit_fiscal_years(rows: list[dict[str, Any]]) -> list[tuple[str, float]]:
    """Operating income per fiscal year, rebuilt from its parts where it is not tagged."""
    reported = dict(fiscal_years(rows, "operating_income"))
    parts = [dict(fiscal_years(rows, metric)) for metric in EBIT_PARTS]
    out = []
    for end, revenue in fiscal_years(rows, "revenue"):
        if end in reported:
            out.append((end, reported[end]))
        elif all(end in p for p in parts):
            out.append((end, revenue - sum(p[end] for p in parts)))
    return out


def base_from_rows(
    rows: list[dict[str, Any]], *, statutory_tax: float, last_n: int = 5
) -> dict[str, Any]:
    """Everything the scenarios need from one issuer's as-of rows, with the reasons
    it cannot be evaluated (``evaluable`` False) and caveats (``flags``)."""
    out: dict[str, Any] = {"evaluable": False, "flags": []}
    revenue = ttm(rows, "revenue")
    if revenue is None:
        out["not_evaluable_because"] = "no trailing revenue"
        return out
    out.update(end=revenue["end"], revenue=revenue["value"], basis=revenue["basis"])
    out["g0"] = revenue["value"] / revenue["prev_value"] - 1 if revenue["prev_value"] else None
    ebit, method = _ebit_ttm(rows, revenue)
    if ebit is None:
        out["not_evaluable_because"] = "operating income not reported for the latest twelve months"
        return out
    out.update(ebit=ebit, ebit_method=method, margin=ebit / revenue["value"])
    tax, pretax = ttm(rows, "income_tax"), ttm(rows, "pretax_income")
    derived = None
    if not tax:  # 決算短信 has no tax line; IFRS releases give pretax and net income
        net = ttm(rows, "net_income")
        if net and pretax and net["end"] == pretax["end"]:
            tax, derived = (
                {"value": pretax["value"] - net["value"], "end": net["end"]},
                "pretax less net income",
            )
    elif not pretax or pretax["end"] != tax["end"]:  # Oracle stopped tagging total pretax income
        net = ttm(rows, "net_income")
        if net and net["end"] == tax["end"]:
            pretax, derived = (
                {"value": net["value"] + tax["value"], "end": net["end"]},
                "net income plus tax",
            )
    same_period = tax and pretax and tax["end"] == pretax["end"] == revenue["end"]
    rate, note = tax_rate(
        income_tax=tax["value"] if same_period else None,
        pretax=pretax["value"] if same_period else None,
        statutory=statutory_tax,
    )
    if derived and note.startswith("effective"):
        note = note.replace("effective", f"effective ({derived})", 1)
    out.update(tax_rate=rate, tax_note=note, statutory_tax=statutory_tax)
    out["history"] = history_stats(
        fiscal_years(rows, "revenue"), ebit_fiscal_years(rows), last_n=last_n
    )
    try:
        out["balance"] = balance(rows, revenue["end"])
    except ValueError as exc:
        out["not_evaluable_because"] = str(exc)
        return out
    capital = out["balance"]["invested_capital"]
    if capital <= 0:
        out["not_evaluable_because"] = f"invested capital is not positive ({capital:,.0f})"
        return out
    nopat = ebit * (1 - rate) if ebit > 0 else ebit
    out.update(sales_to_capital=revenue["value"] / capital, roic=nopat / capital, evaluable=True)
    if out["g0"] is None:
        out["flags"].append("no revenue a year earlier: g0 unknown")
        out["evaluable"] = False
        out["not_evaluable_because"] = "revenue growth over the last year cannot be built"
    if out["history"]["avg_margin_years"] < last_n:
        out["flags"].append(
            f"margin average over {out['history']['avg_margin_years']} fiscal years (< {last_n})"
        )
    if out["history"]["history_years"] < 10:
        out["flags"].append(
            f"revenue history {out['history']['history_years']} years (< 10) for the stress shock"
        )
    if note == "statutory":
        out["flags"].append("statutory tax rate")
    if out["balance"]["debt_recipe"] == "none tagged":
        out["flags"].append("no debt tagged")
    return out
