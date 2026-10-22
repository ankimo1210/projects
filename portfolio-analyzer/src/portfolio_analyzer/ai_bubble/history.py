"""Industry run-ups and crashes in Kenneth French's data library (spec 7).

A run-up (Greenwood, Shleifer and You 2019) is a 24-month value-weighted return of
at least 100%, raw and net of the market, with at least 50% over 60 months, in an
industry with ten or more firms that month. A crash is a fall of 40% or more from
any point to any later point within the 24 months that follow. An episode starts at
the first run-up month and blocks new starts for the next 24 months. Returns are
chained into index levels; a missing month breaks the chain, and every window that
touches it is unknown rather than filled in.
"""

from __future__ import annotations

import math
import random
import re
from typing import Any

MISSING = (-99.99, -999.0)
VW_MONTHLY = "Average Value Weighted Returns -- Monthly"
FIRMS = "Number of Firms in Portfolios"


def _value(text: str) -> float | None:
    x = float(text)
    return None if x in MISSING else x


def _month(key: str) -> str:
    return f"{key[:4]}-{key[4:]}"


def parse_french_industry(text: str) -> dict[str, Any]:
    """Monthly value-weighted returns (decimals) and firm counts per industry; the
    equal-weighted, annual and other sections are skipped."""
    version = re.search(r"created using the (\d{6}) CRSP database", text)
    section, header = "", None
    tables: dict[str, dict[str, list[float | None]]] = {VW_MONTHLY: {}, FIRMS: {}}
    months: dict[str, list[str]] = {VW_MONTHLY: [], FIRMS: []}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split(",")]
        if not line.strip():
            continue
        if line.startswith(","):
            header = cells[1:]
            continue
        if not re.fullmatch(r"\d{4}|\d{6}", cells[0]):
            section, header = line.strip(), None
            continue
        if section not in tables or len(cells[0]) != 6 or header is None:
            continue
        months[section].append(_month(cells[0]))
        for name, cell in zip(header, cells[1:], strict=True):
            tables[section].setdefault(name, []).append(_value(cell))
    if months[VW_MONTHLY] != months[FIRMS]:
        raise ValueError("the return and firm-count sections cover different months")
    return {
        "version": version.group(1) if version else None,
        "months": months[VW_MONTHLY],
        "industries": list(tables[VW_MONTHLY]),
        "vw": {
            k: [None if v is None else v / 100 for v in vs] for k, vs in tables[VW_MONTHLY].items()
        },
        "nfirms": {
            k: [None if v is None else int(v) for v in vs] for k, vs in tables[FIRMS].items()
        },
    }


def parse_french_factors(text: str) -> dict[str, Any]:
    """Monthly ``Mkt-RF`` and ``RF`` as decimals; the annual section is skipped."""
    header: list[str] | None = None
    out: dict[str, list[Any]] = {"months": [], "mkt_rf": [], "rf": []}
    for line in text.splitlines():
        cells = [c.strip() for c in line.split(",")]
        if line.startswith(",") and header is None:
            header = cells[1:]
            continue
        if header is None or not re.fullmatch(r"\d{6}", cells[0]):
            continue
        row = dict(zip(header, cells[1:], strict=True))
        out["months"].append(_month(cells[0]))
        out["mkt_rf"].append(float(row["Mkt-RF"]) / 100)
        out["rf"].append(float(row["RF"]) / 100)
    return out


def parse_french_sic(text: str) -> list[tuple[int, int, str]]:
    """SIC ranges per industry from ``Siccodes49.txt``, in file order."""
    ranges, current = [], None
    for line in text.splitlines():
        span = re.match(r"^\s+(\d{4})-(\d{4})\b", line)
        if span and current:
            ranges.append((int(span.group(1)), int(span.group(2)), current))
            continue
        head = re.match(r"^\s*\d+\s+(\S+)\s", line)
        if head:
            current = head.group(1)
    return ranges


def industry_for_sic(sic: int, ranges: list[tuple[int, int, str]]) -> str:
    """The industry whose range holds ``sic``; codes outside every range are Other."""
    return next((name for lo, hi, name in ranges if lo <= sic <= hi), "Other")


def levels(returns: list[float | None]) -> list[float | None]:
    """Chained index levels; None at a missing month, restarting after it."""
    out: list[float | None] = []
    level: float | None = None
    for r in returns:
        level = None if r is None else (1.0 if level is None else level) * (1 + r)
        out.append(level)
    return out


def _window(lv: list[float | None], start: int, end: int) -> list[float] | None:
    if start < 0 or end >= len(lv):
        return None
    window = lv[start : end + 1]
    return None if any(x is None for x in window) else window  # type: ignore[return-value]


def forward_drawdown(lv: list[float | None], start: int, months: int) -> float | None:
    """``min(I_v / I_u - 1)`` over ``start <= u < v <= start + months``; None unless the
    whole window is known."""
    window = _window(lv, start, start + months)
    if window is None:
        return None
    worst, peak = math.inf, window[0]
    for x in window[1:]:
        worst = min(worst, x / peak - 1)
        peak = max(peak, x)
    return worst


def runup_flags(
    ind: list[float | None],
    mkt: list[float | None],
    nfirms: list[int | None],
    threshold: float = 1.0,
    five_year: float | None = 0.5,
    min_firms: int = 10,
    net: str = "difference",
    net_threshold: float | None = None,
) -> list[bool | None]:
    """Run-up months from index levels. The net return is the difference of the
    cumulative returns, or with ``net="compounded"`` the compounded monthly excess.
    None where the firm count is short or a window is not fully known."""
    net_threshold = threshold if net_threshold is None else net_threshold
    span = 24 if five_year is None else 60
    flags: list[bool | None] = []
    for t in range(len(ind)):
        firms = nfirms[t]
        own, market = _window(ind, t - span, t), _window(mkt, t - 24, t)
        if firms is None or firms < min_firms or own is None or market is None:
            flags.append(None)
            continue
        raw = own[-1] / own[-25] - 1
        if net == "difference":
            excess = raw - (market[-1] / market[0] - 1)
        elif net == "compounded":
            excess = (
                math.prod(
                    1 + own[k] / own[k - 1] - market[k - span + 24] / market[k - span + 23]
                    for k in range(span - 23, span + 1)
                )
                - 1
            )
        else:
            raise ValueError(f"unknown net method {net!r}")
        long_ok = five_year is None or own[-1] / own[0] - 1 >= five_year
        flags.append(raw >= threshold and excess >= net_threshold and long_ok)
    return flags


def episode_starts(flags: list[bool | None], gap: int = 24) -> list[int]:
    """First run-up months, each blocking new starts for ``gap`` months after it."""
    starts: list[int] = []
    for i, flag in enumerate(flags):
        if flag and (not starts or i - starts[-1] >= gap):
            starts.append(i)
    return starts


def outcome(
    ind: list[float | None],
    mkt: list[float | None],
    start: int,
    months: int = 24,
    drawdown: float = -0.4,
) -> dict[str, Any]:
    """The crash flag and the 1- and 2-year raw and net returns after ``start``."""
    dd = forward_drawdown(ind, start, months)

    def ret(lv: list[float | None], horizon: int) -> float | None:
        window = _window(lv, start, start + horizon)
        return None if window is None else window[-1] / window[0] - 1

    out: dict[str, Any] = {"crash": None if dd is None else dd <= drawdown, "drawdown": dd}
    for horizon in (12, 24):
        raw, market = ret(ind, horizon), ret(mkt, horizon)
        out[f"raw_{horizon}m"] = raw
        out[f"net_{horizon}m"] = None if raw is None or market is None else raw - market
    return out


def crash_flags(
    lv: list[float | None],
    nfirms: list[int | None],
    months: int = 24,
    drawdown: float = -0.4,
    min_firms: int = 10,
) -> list[bool | None]:
    """For every month: a crash in the window that starts there (the unconditional rate)."""
    flags: list[bool | None] = []
    for t, firms in enumerate(nfirms):
        dd = None if firms is None or firms < min_firms else forward_drawdown(lv, t, months)
        flags.append(None if dd is None else dd <= drawdown)
    return flags


def pooled_mean(values_by_cluster: dict[str, list[float]]) -> float:
    values = [v for vs in values_by_cluster.values() for v in vs]
    return sum(values) / len(values)


def cluster_bootstrap(
    values_by_cluster: dict[str, list[float]], reps: int, seed: int
) -> list[float]:
    """Means of the values pooled from clusters drawn with replacement (calendar years)."""
    rng = random.Random(seed)
    keys = sorted(values_by_cluster)
    draws = []
    for _ in range(reps):
        pooled = [v for key in rng.choices(keys, k=len(keys)) for v in values_by_cluster[key]]
        draws.append(sum(pooled) / len(pooled))
    return draws


def quantile(values: list[float], q: float) -> float:
    """The ``q`` quantile with linear interpolation between order statistics."""
    ordered = sorted(values)
    h = (len(ordered) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (h - lo) * (ordered[hi] - ordered[lo])


def percentile_interval(draws: list[float], level: float = 0.95) -> tuple[float, float]:
    """The central ``level`` interval of bootstrap draws."""
    tail = (1 - level) / 2
    return quantile(draws, tail), quantile(draws, 1 - tail)


def trailing_return(lv: list[float | None], end: int, months: int) -> float | None:
    """The return over the ``months`` before ``end``; None unless the window is known."""
    window = _window(lv, end - months, end)
    return None if window is None else window[-1] / window[0] - 1


def s_classify(
    flag: bool | None,
    net_24m: float | None,
    net_q75: float | None,
    *,
    crash_ci_low: float,
    unconditional: float,
) -> str:
    """Spec 8: a run-up whose crash-rate interval clears the unconditional rate supports
    overheating; no run-up and a 24-month net return under the industry's own 75th
    percentile weakens it; anything between is mixed."""
    if flag is None or net_24m is None or net_q75 is None:
        return "データ不足"
    if flag and crash_ci_low > unconditional:
        return "支持"
    if not flag and net_24m < net_q75:
        return "弱める"
    return "混在"


def predictive_splits(years: list[str], min_per_split: int = 10, splits: int = 3) -> dict[str, Any]:
    """Spec 7.3: chronological train, validation and test splits cut on calendar-year
    clusters alone; prediction is tested only with ``min_per_split`` years in each."""
    distinct = sorted(set(years))
    if len(distinct) < min_per_split * splits:
        return {"clusters": len(distinct), "feasible": False, "splits": None}
    size, rest = divmod(len(distinct), splits)
    bounds, i = [], 0
    for k in range(splits):
        n = size + (1 if k < rest else 0)
        bounds.append([distinct[i], distinct[i + n - 1]])
        i += n
    return {"clusters": len(distinct), "feasible": True, "splits": bounds}
