from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.sources import PROJECT_ROOT


PEER_SET = PROJECT_ROOT / "data" / "processed" / "peer_set.csv"
OUTPUT = PROJECT_ROOT / "data" / "processed" / "peer_multiples.csv"


def _none_if_missing(value: Any) -> Any:
    if value in ("", "N/A", "NaN", "nan"):
        return None
    return value


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        if numerator is None or denominator in (None, 0):
            return None
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _field(info: dict[str, Any], *names: str) -> Any:
    for name in names:
        value = _none_if_missing(info.get(name))
        if value is not None:
            return value
    return None


def fetch_one(yf, peer: dict[str, Any], retrieved_at: str) -> dict[str, Any]:
    ticker = peer["ticker"]
    row: dict[str, Any] = {
        "company": peer["company"],
        "ticker": ticker,
        "geography": peer.get("geography"),
        "category": peer.get("category"),
        "retrieved_at": retrieved_at,
        "source": "yfinance",
        "source_url": f"https://finance.yahoo.com/quote/{ticker}",
    }

    try:
        t = yf.Ticker(ticker)
        info = t.get_info()
    except Exception as exc:  # noqa: BLE001 - capture provider failures in output
        row.update(
            {
                "data_status": "fetch_failed",
                "notes": f"yfinance fetch failed: {type(exc).__name__}: {exc}",
            }
        )
        return row

    trading_currency = _field(info, "currency")
    financial_currency = _field(info, "financialCurrency")
    market_cap = _field(info, "marketCap")
    enterprise_value = _field(info, "enterpriseValue")
    revenue = _field(info, "totalRevenue")
    ebitda = _field(info, "ebitda")
    ev_revenue = _field(info, "enterpriseToRevenue")
    ev_ebitda = _field(info, "enterpriseToEbitda")

    if ev_revenue is None:
        ev_revenue = _safe_ratio(enterprise_value, revenue)
    if ev_ebitda is None:
        ev_ebitda = _safe_ratio(enterprise_value, ebitda)

    notes = "Public Yahoo/yfinance snapshot; verify in market-data terminal before bid."
    data_status = "sourced" if market_cap or enterprise_value else "limited_or_missing"
    if trading_currency and financial_currency and trading_currency != financial_currency:
        data_status = "needs_currency_check"
        notes = (
            "Trading currency differs from financial currency in yfinance; "
            "EV/revenue and EV/EBITDA may be distorted. Verify before use."
        )

    row.update(
        {
            "as_of": datetime.now(timezone.utc).date().isoformat(),
            "currency": trading_currency or financial_currency,
            "financial_currency": financial_currency,
            "price": _field(info, "currentPrice", "regularMarketPrice", "previousClose"),
            "market_cap": market_cap,
            "enterprise_value": enterprise_value,
            "total_revenue": revenue,
            "ebitda": ebitda,
            "ev_revenue": ev_revenue,
            "ev_ebitda": ev_ebitda,
            "trailing_pe": _field(info, "trailingPE"),
            "forward_pe": _field(info, "forwardPE"),
            "price_to_sales": _field(info, "priceToSalesTrailing12Months"),
            "dividend_yield": _field(info, "dividendYield"),
            "data_status": data_status,
            "notes": notes,
        }
    )
    return row


def main() -> None:
    import yfinance as yf

    peers = pd.read_csv(PEER_SET)
    retrieved_at = datetime.now().astimezone().isoformat(timespec="seconds")
    rows = [fetch_one(yf, row.to_dict(), retrieved_at) for _, row in peers.iterrows()]
    out = pd.DataFrame(rows)

    ordered_cols = [
        "company",
        "ticker",
        "geography",
        "category",
        "as_of",
        "retrieved_at",
        "currency",
        "financial_currency",
        "price",
        "market_cap",
        "enterprise_value",
        "total_revenue",
        "ebitda",
        "ev_revenue",
        "ev_ebitda",
        "trailing_pe",
        "forward_pe",
        "price_to_sales",
        "dividend_yield",
        "source",
        "source_url",
        "data_status",
        "notes",
    ]
    for col in ordered_cols:
        if col not in out:
            out[col] = None
    out = out[ordered_cols]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT, index=False)
    print(f"wrote {OUTPUT}")
    print(out[["ticker", "ev_revenue", "ev_ebitda", "forward_pe", "data_status"]].to_string(index=False))


if __name__ == "__main__":
    main()
