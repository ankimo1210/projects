"""Reverse DCF of the whole firm (spec 5): what growth and margin the price needs.

Cash flows are FCFF = NOPAT - reinvestment. Reinvestment follows sales growth
through a fixed sales-to-capital ratio while the forecast runs, and the
terminal flow keeps the reinvestment its growth needs, NOPAT x (1 - g/RONIC),
so a high current return on capital cannot make the terminal value free.
A fall in sales releases no capital, and a loss earns no tax credit.

The solvers search a grid for sign changes and bisect each one, so a value
that two growth rates (or two discount rates) explain is reported as
"multiple" instead of returning whichever root a local method meets first.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any


def enterprise_value(
    cf: list[float], terminal_cf: float, discount_rate: float, terminal_growth: float
) -> float:
    """Value of FCFF in years 1..T plus the year T+1 flow growing at ``terminal_growth``."""
    r, g = discount_rate, terminal_growth
    if r <= g:
        raise ValueError(f"discount rate r={r} must exceed terminal growth g={g}")
    years = len(cf)
    value = sum(flow / (1 + r) ** t for t, flow in enumerate(cf, start=1))
    return value + terminal_cf / ((r - g) * (1 + r) ** years)


def terminal_fcff(nopat_next: float, terminal_growth: float, ronic: float) -> float:
    if ronic <= 0:
        raise ValueError("RONIC must be positive")
    return nopat_next * (1 - terminal_growth / ronic)


def growth_path(
    g0: float, g_inf: float, phi: float, years: int, shocks: dict[int, float] | None = None
) -> list[float]:
    """``g_t = g_inf + (g0 - g_inf) phi^t`` for t = 1..years; ``shocks`` replace their years."""
    path = [g_inf + (g0 - g_inf) * phi**t for t in range(1, years + 1)]
    for year, value in (shocks or {}).items():
        path[year - 1] = value
    return path


def project_fcff(base: dict[str, float], scenario: dict[str, Any], years: int) -> dict[str, Any]:
    """Revenue, NOPAT, reinvestment and FCFF for years 1..T and the terminal FCFF.

    ``base``: revenue (last twelve months), tax_rate, sales_to_capital.
    ``scenario``: growth and margin lists (one per year), ronic and g_inf, and
    optionally a tax list and tax_terminal (else the base rate throughout).
    """
    turnover = base["sales_to_capital"]
    taxes = scenario.get("tax") or [base["tax_rate"]] * years
    terminal_tax = scenario.get("tax_terminal", taxes[years - 1])
    if turnover <= 0:
        raise ValueError("sales_to_capital must be positive")
    revenue = [base["revenue"]]
    nopat, reinvestment, fcff = [], [], []
    for t in range(years):
        revenue.append(revenue[-1] * (1 + scenario["growth"][t]))
        ebit = revenue[-1] * scenario["margin"][t]
        nopat.append(ebit * (1 - taxes[t]) if ebit > 0 else ebit)
        reinvestment.append(max(revenue[-1] - revenue[-2], 0.0) / turnover)
        fcff.append(nopat[-1] - reinvestment[-1])
    next_ebit = revenue[-1] * (1 + scenario["g_inf"]) * scenario["margin"][years - 1]
    nopat_next = next_ebit * (1 - terminal_tax) if next_ebit > 0 else next_ebit
    return {
        "revenue": revenue[1:],
        "nopat": nopat,
        "reinvestment": reinvestment,
        "fcff": fcff,
        "nopat_next": nopat_next,
        "terminal_fcff": terminal_fcff(nopat_next, scenario["g_inf"], scenario["ronic"]),
    }


PHI = {"central": 0.6, "optimistic": 0.85, "stress": 0.6}
RONIC_PREMIUM = 0.05
MARGIN_YEARS = 5


def _walk(
    start: float, end: float, first: int, last: int, years: int, before: float
) -> list[float]:
    """``before`` until year ``first``, then a straight line to ``end`` at year ``last``, then ``end``."""
    path = []
    for t in range(1, years + 1):
        if t <= first:
            path.append(before)
        elif t >= last:
            path.append(end)
        else:
            path.append(start + (end - start) * (t - first) / (last - first))
    return path


def scenario_paths(
    firm: dict[str, Any], kind: str, *, r_j: float, years: int = 10, g_inf: float = 0.03
) -> dict[str, Any]:
    """The registered paths (spec 5.2) for one firm: ``central``, ``optimistic`` or ``stress``.

    Tax moves from the trailing effective rate to the statutory rate by year T
    and stays there in the terminal year, in every scenario.
    """
    history, note = firm["history"], ""
    m0, average = firm["margin"], history["avg_margin"]
    growth = growth_path(firm["g0"], g_inf, PHI[kind], years)
    ronic = r_j + RONIC_PREMIUM
    if kind == "central":
        margin = [
            m0 + (average - m0) * min(t, MARGIN_YEARS) / MARGIN_YEARS for t in range(1, years + 1)
        ]
    elif kind == "optimistic":
        margin = [m0] * years
        if firm.get("roic") is not None and firm["roic"] > g_inf:
            ronic = firm["roic"]
        else:
            note = "ROIC not above g_inf: optimistic uses the central RONIC"
    elif kind == "stress":
        worst = history["worst_2y_revenue_change"]
        if worst is None or worst >= 0:
            shock = 0.0
            note = "no two-year decline on record: sales held flat in years 1-2"
        else:
            shock = (1 + worst) ** 0.5 - 1
        growth = growth_path(firm["g0"], g_inf, PHI[kind], years, shocks={1: shock, 2: shock})
        low = history["min_margin"]
        margin = _walk(low, average, 2, MARGIN_YEARS, years, low)
        ronic = r_j
    else:
        raise ValueError(f"unknown scenario {kind}")
    effective, statutory = firm["tax_rate"], firm["statutory_tax"]
    tax = [effective + (statutory - effective) * t / years for t in range(1, years + 1)]
    return {
        "kind": kind,
        "growth": growth,
        "margin": margin,
        "tax": tax,
        "tax_terminal": statutory,
        "ronic": ronic,
        "g_inf": g_inf,
        "note": note,
    }


def solve_roots(f: Callable[[float], float], lo: float, hi: float, steps: int = 400) -> list[float]:
    """Every root of ``f`` on [lo, hi] that a grid of ``steps`` intervals brackets."""
    xs = [lo + (hi - lo) * k / steps for k in range(steps + 1)]
    ys = [f(x) for x in xs]
    roots: list[float] = []
    for k in range(steps + 1):
        if ys[k] == 0:
            roots.append(xs[k])
            continue
        if k < steps and ys[k + 1] != 0 and (ys[k] < 0) != (ys[k + 1] < 0):
            a, b, fa = xs[k], xs[k + 1], ys[k]
            for _ in range(200):
                mid = (a + b) / 2
                fm = f(mid)
                if fm == 0 or b - a < 1e-13:
                    a = b = mid
                    break
                if (fm < 0) == (fa < 0):
                    a, fa = mid, fm
                else:
                    b = mid
            roots.append((a + b) / 2)
    return roots


def _solved(roots: list[float], bounds: tuple[float, float]) -> dict[str, Any]:
    status = "no_solution" if not roots else "ok" if len(roots) == 1 else "multiple"
    return {"status": status, "solutions": roots, "bounds": bounds}


def required_growth(
    ev_of: Callable[[float], float],
    ev_observed: float,
    *,
    bounds: tuple[float, float],
    steps: int = 400,
) -> dict[str, Any]:
    """The value(s) of the driver (initial growth, or a margin) at which the model
    EV equals the observed EV; ``ev_of`` builds the EV from the driver."""
    return _solved(solve_roots(lambda x: ev_of(x) - ev_observed, *bounds, steps=steps), bounds)


def implied_irr(
    fcff: list[float],
    terminal_cf: float,
    g_inf: float,
    ev_observed: float,
    *,
    bounds: tuple[float, float],
    steps: int = 400,
) -> dict[str, Any]:
    """Discount rate(s) at which the given cash flows are worth the observed EV."""
    if bounds[0] <= g_inf:
        raise ValueError("the lower rate bound must exceed g_inf")
    roots = solve_roots(
        lambda r: enterprise_value(fcff, terminal_cf, r, g_inf) - ev_observed, *bounds, steps=steps
    )
    return _solved(roots, bounds)


def per(price: float, eps: float | None, adr_ratio: float = 1.0) -> float | None:
    """Price over earnings per quoted share; one ADR carries ``adr_ratio`` ordinary shares."""
    if eps is None or eps <= 0:
        return None
    return price / (eps * adr_ratio)


def v_classify(
    ev_central: float, ev_optimistic: float, ev_observed: float, band: float = 0.10
) -> str:
    """Spec 8: both scenarios below (1 - band) of the observed EV support V; a central
    EV at or above it weakens V; anything else is mixed. A non-positive observed EV
    (net cash above market cap) cannot be judged."""
    if ev_observed <= 0:
        return "保留"
    line = (1 - band) * ev_observed
    if ev_central >= line:
        return "弱める"
    if ev_optimistic < line:
        return "支持"
    return "混在"


GRID = {"T": (5, 10), "r": (0.06, 0.08, 0.10, 0.12, 0.14), "g_inf": (0.02, 0.03, 0.04)}


def _cagr(path: list[float], years: int) -> float:
    level = 1.0
    for g in path[:years]:
        level *= 1 + g
    return level ** (1 / years) - 1


def value_company(
    firm: dict[str, Any],
    *,
    r_j: float,
    ev_observed: float,
    years: int = 10,
    g_inf: float = 0.03,
    band: float = 0.10,
    growth_bounds: tuple[float, float] = (-0.5, 3.0),
    margin_bounds: tuple[float, float] = (-0.5, 0.95),
    irr_upper: float = 0.30,
) -> dict[str, Any]:
    """Scenario values at the registered rate, the V label, what the price needs
    (initial growth with its 5- and 10-year sales CAGR, or the margin the central
    path walks to), the implied IRR of the central path, and the sensitivities
    (display only: the r x g_inf x T grid and sales-to-capital x0.75 / x1.25)."""

    def flows(
        kind: str, f: dict[str, Any] = firm, t: int = years, g: float = g_inf
    ) -> dict[str, Any]:
        return project_fcff(f, scenario_paths(f, kind, r_j=r_j, years=t, g_inf=g), t)

    def ev(
        kind: str, f: dict[str, Any] = firm, r: float = r_j, t: int = years, g: float = g_inf
    ) -> float:
        out = flows(kind, f, t, g)
        return enterprise_value(out["fcff"], out["terminal_fcff"], r, g)

    values = {kind: ev(kind) for kind in ("central", "optimistic", "stress")}
    central = flows("central")
    terminal_pv = central["terminal_fcff"] / ((r_j - g_inf) * (1 + r_j) ** years)

    growth = required_growth(
        lambda g0: ev("central", {**firm, "g0": g0}), ev_observed, bounds=growth_bounds
    )
    paths = [growth_path(g0, g_inf, PHI["central"], years) for g0 in growth["solutions"]]
    growth["cagr_5y"] = [_cagr(p, 5) for p in paths]
    growth["cagr_10y"] = [_cagr(p, 10) for p in paths]
    margin = required_growth(
        lambda m: ev("central", {**firm, "history": {**firm["history"], "avg_margin": m}}),
        ev_observed,
        bounds=margin_bounds,
    )
    irr = implied_irr(
        central["fcff"],
        central["terminal_fcff"],
        g_inf,
        ev_observed,
        bounds=(g_inf + 0.01, irr_upper),
    )
    grid = [
        {
            "T": t,
            "r": r,
            "g_inf": g,
            "ev_central": ev("central", r=r, t=t, g=g),
            "ratio": ev("central", r=r, t=t, g=g) / ev_observed if ev_observed > 0 else None,
        }
        for t in GRID["T"]
        for r in GRID["r"]
        for g in GRID["g_inf"]
        if r > g
    ]
    turnover = {
        f"x{scale}": ev("central", {**firm, "sales_to_capital": firm["sales_to_capital"] * scale})
        for scale in (0.75, 1.25)
    }
    notes = {
        kind: scenario_paths(firm, kind, r_j=r_j, years=years, g_inf=g_inf)["note"]
        for kind in values
    }
    return {
        "r_j": r_j,
        "ev_observed": ev_observed,
        "ev": values,
        "ev_ratio": {k: v / ev_observed for k, v in values.items()} if ev_observed > 0 else None,
        "ev_central_T5": ev("central", t=5),
        "v": v_classify(values["central"], values["optimistic"], ev_observed, band),
        "terminal_share": terminal_pv / values["central"] if values["central"] > 0 else None,
        "required_growth": growth,
        "required_margin": margin,
        "implied_irr": irr,
        "grid": grid,
        "turnover": turnover,
        "notes": {k: v for k, v in notes.items() if v},
    }


def multiples(
    *,
    market_cap: float,
    ev: float,
    net_income: float,
    ebit: float,
    operating_cf: float | None = None,
    capex: float | None = None,
) -> dict[str, float | None]:
    """Trailing multiples on one basis and period (spec 5): PER only on positive
    earnings (a loss is 対象外, not dropped), EV/EBIT, operating cash flow over
    net income, and the cash left after capital expenditure."""
    fcf = operating_cf - capex if operating_cf is not None and capex is not None else None
    return {
        "earnings_yield": net_income / market_cap,
        "per": per(market_cap, net_income),
        "ev_ebit": ev / ebit if ebit > 0 and ev > 0 else None,
        "ocf_to_net_income": operating_cf / net_income
        if operating_cf is not None and net_income > 0
        else None,
        "fcf_after_capex": fcf,
        "fcf_yield": fcf / market_cap if fcf is not None else None,
    }


def cycle_per(
    market_cap: float, quarterly: list[tuple[str, float]], *, min_quarters: int = 20
) -> dict[str, Any]:
    """PER on the latest quarter x4 and on the average quarter of the last ``min_quarters``
    (spec 5: peak earnings make a low PER); fewer on record are reference only."""
    window = quarterly[-min_quarters:]
    average = sum(v for _, v in window) / len(window)
    return {
        "per_latest_x4": per(market_cap, 4 * quarterly[-1][1]),
        "per_cycle": per(market_cap, 4 * average),
        "latest_end": quarterly[-1][0],
        "first_end": window[0][0],
        "quarters": len(window),
        "reference_only": len(window) < min_quarters,
    }


def layer_consistency(
    buyers: list[dict[str, Any]], suppliers: list[dict[str, Any]], *, years: int = 5
) -> list[dict[str, Any]]:
    """Spec 5.2: the buyers' investment against the suppliers' sales, year by year.

    A buyer gives its revenue path from a year before the trailing figure
    (``[R_-1, R_0, R_1, ...]``) and its sales-to-capital ratio; its investment is
    the model's reinvestment, max(R_t - R_t-1, 0) / (sales/capital), so year 0 is
    measured like the projected years. A supplier gives ``[R_0, R_1, ...]``.
    A year whose two changes have opposite signs is a warning.
    """
    investment = [
        sum(max(b["revenue"][t + 1] - b["revenue"][t], 0.0) / b["sales_to_capital"] for b in buyers)
        for t in range(years + 1)
    ]
    sales = [sum(s["revenue"][t] for s in suppliers) for t in range(years + 1)]
    out = []
    for t in range(1, years + 1):
        d_inv = investment[t] / investment[t - 1] - 1 if investment[t - 1] > 0 else None
        d_sales = sales[t] / sales[t - 1] - 1
        out.append(
            {
                "year": t,
                "buyers_investment": investment[t],
                "suppliers_revenue": sales[t],
                "buyers_investment_change": d_inv,
                "suppliers_revenue_change": d_sales,
                "warning": d_inv is not None and (d_inv < 0) != (d_sales < 0),
            }
        )
    return out


def price_decomposition(
    *, price0: float, price1: float, eps0: float, eps1: float
) -> dict[str, float] | None:
    """Δlog(price) = Δlog(EPS) + Δlog(PER), an identity, for positive earnings at both ends."""
    if min(price0, price1, eps0, eps1) <= 0:
        return None
    dlog_price, dlog_eps = math.log(price1 / price0), math.log(eps1 / eps0)
    return {"dlog_price": dlog_price, "dlog_eps": dlog_eps, "dlog_per": dlog_price - dlog_eps}
