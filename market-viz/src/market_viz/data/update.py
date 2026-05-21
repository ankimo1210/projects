"""Orchestrate data update: fetch → normalize → store."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

from market_viz.data.loaders import load_ccxt, load_yfinance
from market_viz.data.normalize import normalize_prices
from market_viz.storage.duckdb_client import DuckDBClient

_ROOT = Path(__file__).parent.parent.parent


def _load_instruments(config_path: str = "") -> list[dict]:
    path = Path(config_path) if config_path else _ROOT / "src/config/instruments.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    result: list[dict] = []
    for group in cfg.get("instruments", {}).values():
        result.extend(group)
    return result


def _load_settings(config_path: str = "") -> dict:
    path = Path(config_path) if config_path else _ROOT / "src/config/settings.yaml"
    with open(path) as f:
        return yaml.safe_load(f)


def update_daily(
    db: DuckDBClient,
    lookback_days: int = 365,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Fetch daily OHLCV for all instruments and upsert into DB.
    Returns {ticker: status} mapping.
    """
    instruments = _load_instruments()
    settings = _load_settings()
    sleep_sec = settings["data"].get("yfinance_sleep_sec", 0.5)

    default_start = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    results: dict[str, str] = {}

    for inst in instruments:
        ticker = inst["ticker"]
        yf_ticker = inst.get("yf_ticker") or ticker

        # incremental: start from last stored date + 1
        latest = db.get_latest_timestamp(ticker, frequency="1d")
        if latest:
            start = (pd.Timestamp(latest) + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            start = default_start

        today = datetime.today().strftime("%Y-%m-%d")
        if start >= today:
            results[ticker] = "up-to-date"
            if on_progress:
                on_progress(f"[skip] {ticker} already up-to-date")
            continue

        if on_progress:
            on_progress(f"[fetch] {ticker} from {start}")

        try:
            raw = load_yfinance(yf_ticker, start=start, interval="1d", sleep_sec=sleep_sec)
            if raw.empty:
                results[ticker] = "no-data"
                continue
            raw["ticker"] = ticker
            raw["asset_class"] = inst.get("asset_class", "")
            raw["market"] = inst.get("market", "")
            df = normalize_prices(raw)
            db.upsert_prices(df)
            results[ticker] = f"ok ({len(df)} rows)"
        except Exception as exc:
            results[ticker] = f"error: {exc}"
            if on_progress:
                on_progress(f"[error] {ticker}: {exc}")

    return results


def update_crypto_intraday(
    db: DuckDBClient,
    timeframe: str = "1m",
    lookback_days: int = 7,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, str]:
    """Fetch crypto intraday (1m/5m/1h) via ccxt and upsert into DB."""
    instruments = _load_instruments()
    settings = _load_settings()
    sleep_sec = settings["data"].get("ccxt_sleep_sec", 0.2)

    crypto_insts = [i for i in instruments if i.get("ccxt_symbol")]
    results: dict[str, str] = {}

    for inst in crypto_insts:
        ticker = inst["ticker"]
        ccxt_symbol = inst["ccxt_symbol"]
        ccxt_exchange = inst.get("ccxt_exchange", "binance")

        latest = db.get_latest_timestamp(ticker, frequency=timeframe)
        if latest:
            since_dt = pd.Timestamp(latest).to_pydatetime() + timedelta(minutes=1)
        else:
            since_dt = datetime.today() - timedelta(days=lookback_days)

        if on_progress:
            on_progress(f"[ccxt] {ccxt_symbol} ({timeframe}) from {since_dt.date()}")

        try:
            raw = load_ccxt(
                symbol=ccxt_symbol,
                exchange_id=ccxt_exchange,
                timeframe=timeframe,
                since_dt=since_dt,
                sleep_sec=sleep_sec,
            )
            if raw.empty:
                results[ticker] = "no-data"
                continue
            raw["ticker"] = ticker
            raw["asset_class"] = inst.get("asset_class", "crypto")
            raw["market"] = inst.get("market", "global")
            df = normalize_prices(raw)
            db.upsert_prices(df)
            results[ticker] = f"ok ({len(df)} rows)"
        except Exception as exc:
            results[ticker] = f"error: {exc}"
            if on_progress:
                on_progress(f"[error] {ticker}: {exc}")

    return results
