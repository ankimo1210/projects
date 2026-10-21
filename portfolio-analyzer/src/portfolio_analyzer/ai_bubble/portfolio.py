"""Holdings impact of the AI-bubble scenarios (spec 8.1).

Holdings are traced to issuers through each fund's disclosed weights, and the part
of a fund the weights do not cover stays unknown instead of being spread over the
known names. Two layers sit side by side and are never added: the idiosyncratic
layer reprices the evaluated issuers at the central implied rate ``r*`` (zero
change in the central case, stress at ``r*`` plus the registered shift), and the
systematic layer replays past episodes through a proxy series per holding. A
holding without a proxy, or an issuer without an implied rate, is unevaluated.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from portfolio_analyzer.ai_bubble.valuation import solve_roots
from portfolio_analyzer.risk import episode_impacts


def lookthrough_paths(
    symbol: str,
    value_jpy: float,
    weights: dict[str, float],
    *,
    economic_currency: str | None,
    fx_hedge_ratio: float | None,
    as_of: str | None,
) -> list[dict[str, Any]]:
    """One path per disclosed issuer weight of a holding, plus the unknown remainder."""
    known = sum(weights.values())
    if known > 1 + 1e-9:
        raise ValueError(f"{symbol}: issuer weights add up to {known:.4f} > 1")
    base = {
        "position_symbol": symbol,
        "economic_currency": economic_currency,
        "fx_hedge_ratio": fx_hedge_ratio,
        "as_of": as_of,
    }
    paths = [
        base | {"issuer_id": issuer, "value_jpy": value_jpy * w} for issuer, w in weights.items()
    ]
    if known < 1:
        paths.append(base | {"issuer_id": None, "value_jpy": value_jpy * (1 - known)})
    return paths


def issuer_exposure(paths: list[dict[str, Any]]) -> dict[str, Any]:
    """Paths summed by issuer; paths without an issuer are the unknown part of funds."""
    issuers: dict[str, dict[str, Any]] = {}
    unknown = 0.0
    for p in paths:
        if p["issuer_id"] is None:
            unknown += p["value_jpy"]
            continue
        entry = issuers.setdefault(p["issuer_id"], {"value_jpy": 0.0, "paths": []})
        entry["value_jpy"] += p["value_jpy"]
        entry["paths"].append(p)
    return {
        "issuers": issuers,
        "unknown_jpy": unknown,
        "total_jpy": sum(p["value_jpy"] for p in paths),
    }


def repricing_change(ev_observed: float, net_debt: float, ev_scenario: float) -> float | None:
    """Change in equity value when the EV moves and net debt stays as it is; equity
    cannot fall below zero, and a firm without positive equity value is not judged."""
    equity = ev_observed - net_debt
    if equity <= 0:
        return None
    return max((ev_scenario - net_debt) / equity - 1, -1.0)


def fx_compose(local_return: float, fx_change: float) -> float:
    """Yen return of an unhedged foreign path: ``(1 + local)(1 + fx) - 1``."""
    return (1 + local_return) * (1 + fx_change) - 1


def idiosyncratic_layer(
    ev_observed: float,
    net_debt: float,
    value_at: Callable[[str, float], float],
    *,
    shift: float,
    bounds: tuple[float, float],
    steps: int = 400,
) -> dict[str, Any]:
    """Equity changes when the central, optimistic and stress cash flows are valued
    at the central implied rate ``r*`` (stress at ``r* + shift``)."""
    unevaluated = {"status": "unevaluated", "r_star": None, "change": None, "bounds": list(bounds)}
    if ev_observed - net_debt <= 0:
        return unevaluated | {"reason": "equity value not positive"}
    roots = solve_roots(lambda r: value_at("central", r) - ev_observed, *bounds, steps=steps)
    if len(roots) != 1:
        reason = "no implied rate within the bounds" if not roots else "several implied rates"
        return unevaluated | {"reason": reason, "solutions": roots}
    r = roots[0]
    return {
        "status": "ok",
        "r_star": r,
        "rates": {"central": r, "optimistic": r, "stress": r + shift},
        "change": {
            "central": 0.0,
            "optimistic": repricing_change(ev_observed, net_debt, value_at("optimistic", r)),
            "stress": repricing_change(ev_observed, net_debt, value_at("stress", r + shift)),
        },
        "bounds": list(bounds),
    }


def _bounds(dates: list[str], episode: dict[str, Any]) -> tuple[int, int] | None:
    before = [i for i, d in enumerate(dates) if d < str(episode["start"])]
    upto = [i for i, d in enumerate(dates) if d <= str(episode["end"])]
    return (before[-1], upto[-1]) if before and upto else None


def _covers(series: list[float | None], bounds: tuple[int, int] | None) -> bool:
    return bounds is not None and all(
        i < len(series) and series[i] is not None and series[i] > 0 for i in bounds
    )


def systematic_layer(
    values: dict[str, float],
    proxy_map: dict[str, str],
    proxy_prices_jpy: dict[str, list[float | None]],
    dates: list[str],
    episodes: list[dict[str, Any]],
    *,
    fallback_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Past episodes replayed on today's holdings through their yen proxy series
    (``risk.episode_impacts``), one episode at a time. A holding uses its fallback
    (an index) where its own proxy has no price at the episode's bounds; a holding
    without a proxy stays unevaluated."""
    fallback_map = fallback_map or {}
    rows = []
    for episode in episodes:
        bounds = _bounds(dates, episode)
        chosen: dict[str, str] = {}
        by_proxy: dict[str, float] = {}
        missing = []
        for holding, value in values.items():
            options = [
                p
                for p in (proxy_map.get(holding), fallback_map.get(holding))
                if p in proxy_prices_jpy
            ]
            proxy = next(
                (p for p in options if _covers(proxy_prices_jpy[p], bounds)),
                options[0] if options else None,
            )
            if proxy is None:
                missing.append(holding)
                continue
            chosen[holding] = proxy
            by_proxy[proxy] = by_proxy.get(proxy, 0.0) + value
        row = episode_impacts(
            by_proxy,
            [episode],
            dates,
            proxy_prices_jpy,
            total_nav=sum(values.values()),
            missing_holdings=missing,
        )[0]
        rows.append(row | {"proxies": chosen})
    return rows


def parse_h10(html: str) -> list[tuple[str, float | None]]:
    """Daily yen per dollar from a Federal Reserve H.10 history page; ND (no data) is None."""
    rows = re.findall(
        r"<th[^>]*>\s*(\d{1,2}-[A-Z]{3}-\d{2})\s*</th>\s*<td[^>]*>\s*([^<\s]+)\s*</td>", html
    )
    return [
        (
            datetime.strptime(day, "%d-%b-%y").date().isoformat(),
            None if value == "ND" else float(value),
        )
        for day, value in rows
    ]
