"""Which companies the study covers (spec 3.1), from market caps at the as-of time.

A daily bar counts only once its market has closed (the same rule as the daily
report, ``mtm.bar_is_final``); a currency bar is used from the next UTC day,
because its daily bar has no single close. Closes are split-adjusted by the
source, so share counts are put on the same basis (``shares_at``). Layers that take every candidate
need no caps; a ranked layer needs a cap for each candidate, or it cannot be
ranked.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from portfolio_analyzer.ai_bubble.inputs import parse_utc
from portfolio_analyzer.mtm import bar_is_final


def last_final_close(
    bars: list[tuple[str, float | None]], ticker: str, as_of_utc: str
) -> tuple[str, float]:
    """The latest (date, close) whose bar was final at ``as_of_utc``."""
    cutoff = parse_utc(as_of_utc, "as_of_utc")
    usable = []
    for day, close in bars:
        if close is None or close != close:  # NaN
            continue
        bar_date = date.fromisoformat(day)
        if ticker.endswith("=X"):
            final = bar_date + timedelta(days=1) <= cutoff.date()
        else:
            final = bar_is_final(ticker, bar_date, cutoff)
        if final:
            usable.append((day, float(close)))
    if not usable:
        raise ValueError(f"{ticker}: no final close at {as_of_utc}")
    return max(usable)


def market_cap_usd(
    *,
    price: float,
    shares: float,
    currency: str,
    jpy_per_usd: float | None = None,
    adr_ratio: float = 1,
) -> float:
    """Price times shares in dollars; ``shares`` are ordinary shares and one ADR
    represents ``adr_ratio`` of them."""
    value = price * shares / adr_ratio
    if currency == "USD":
        return value
    if currency == "JPY":
        if not jpy_per_usd:
            raise ValueError("a yen price needs jpy_per_usd")
        return value / jpy_per_usd
    raise ValueError(f"unsupported currency {currency}")


def select_universe(
    layers: list[dict[str, Any]], caps: dict[str, float], *, must_include: list[str]
) -> dict[str, list[str]]:
    """Per layer: every candidate, or the ``take`` largest by cap plus any must-include."""
    out: dict[str, list[str]] = {}
    for layer in layers:
        candidates = list(layer["candidates"])
        if layer["take"] >= len(candidates):
            out[layer["id"]] = candidates
            continue
        absent = [c for c in candidates if c not in caps]
        if absent:
            raise ValueError(f"layer {layer['id']}: no market cap for {', '.join(absent)}")
        ranked = sorted(candidates, key=lambda c: caps[c], reverse=True)
        chosen = ranked[: layer["take"]]
        chosen += [c for c in ranked[layer["take"] :] if c in must_include]
        out[layer["id"]] = chosen
    return out


def shares_at(
    shares: float, count_date: str, splits: list[tuple[str, float]]
) -> tuple[float, list[tuple[str, float]]]:
    """A filing's share count in the split basis of the price series.

    The price source divides past closes by every split it has recorded, so
    the count is multiplied by every split whose ex-date is after the count
    date. Price times count is then the market cap of the close date in any
    basis; nothing about later splits leaks into it.
    """
    counted = date.fromisoformat(count_date)
    applied = [
        (day, float(ratio)) for day, ratio in sorted(splits) if date.fromisoformat(day) > counted
    ]
    for _, ratio in applied:
        shares *= ratio
    return shares, applied
