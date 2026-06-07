from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from src.utils.sources import CONFIG_DIR, PROJECT_ROOT, load_yaml, now_jst_iso


RAW_DIR = PROJECT_ROOT / "data" / "raw" / "market_data"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def _fetch_yahoo_chart(symbol: str = "4667.T", range_: str = "2y") -> pd.DataFrame:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": range_, "interval": "1d", "events": "history"}
    headers = {"User-Agent": "Mozilla/5.0 aisan-lbo-case public research bot"}
    response = requests.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    result = payload["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    df = pd.DataFrame(quote)
    df["date"] = pd.to_datetime(timestamps, unit="s").date
    df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
    df["source"] = "Yahoo Finance chart API"
    return df


def _fetch_stooq(symbol: str = "4667.jp") -> pd.DataFrame:
    today = datetime.now().strftime("%Y%m%d")
    url = f"https://stooq.com/q/d/l/?s={symbol}&d1=20240101&d2={today}&i=d"
    df = pd.read_csv(url)
    df.columns = [c.lower() for c in df.columns]
    if "date" not in df.columns or df.empty:
        raise ValueError("Stooq returned no usable rows.")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["source"] = "Stooq"
    return df


def fetch_prices() -> pd.DataFrame:
    try:
        return _fetch_yahoo_chart()
    except Exception:
        return _fetch_stooq()


def summarize_market_data(prices: pd.DataFrame, assumptions: dict[str, Any]) -> dict[str, Any]:
    if prices.empty:
        fallback = assumptions["market_snapshot_manual_fallback"].copy()
        fallback["retrieved_at"] = now_jst_iso()
        fallback["data_status"] = "manual_fallback"
        return fallback

    prices = prices.copy()
    prices["date"] = pd.to_datetime(prices["date"])
    prices = prices.sort_values("date")
    last = prices.dropna(subset=["close"]).iloc[-1]
    shares = assumptions["share_data"]["shares_outstanding"]
    close = float(last["close"])
    volume = float(last.get("volume", 0) or 0)

    def vwap(days: int) -> float | None:
        sub = prices.tail(days).dropna(subset=["close", "volume"])
        denom = sub["volume"].sum()
        if denom == 0:
            return None
        return float((sub["close"] * sub["volume"]).sum() / denom)

    trailing_252 = prices.tail(252)
    return {
        "as_of": str(last["date"].date()),
        "close_price_jpy": close,
        "volume_shares": volume,
        "market_cap_jpy_mn": close * shares / 1_000_000,
        "high_52w": float(trailing_252["high"].max()),
        "low_52w": float(trailing_252["low"].min()),
        "vwap_3m": vwap(63),
        "vwap_6m": vwap(126),
        "source_id": "yahoo_finance_quote",
        "source_type": "sourced",
        "retrieved_at": now_jst_iso(),
        "data_status": "live_fetch",
    }


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    assumptions = load_yaml(CONFIG_DIR / "assumptions.yaml")
    try:
        prices = fetch_prices()
        prices.to_csv(RAW_DIR / "4667_prices.csv", index=False)
    except Exception as exc:  # noqa: BLE001
        prices = pd.DataFrame()
        (RAW_DIR / "4667_prices_fetch_error.txt").write_text(
            f"Fetch failed at {now_jst_iso()}\n{exc!r}\n", encoding="utf-8"
        )

    snapshot = summarize_market_data(prices, assumptions)
    pd.DataFrame([snapshot]).to_csv(PROCESSED_DIR / "market_snapshot.csv", index=False)


if __name__ == "__main__":
    main()
