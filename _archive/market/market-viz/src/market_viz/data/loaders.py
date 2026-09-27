"""Data loaders: yfinance, ccxt (crypto intraday)."""

from __future__ import annotations

import time
from datetime import datetime

import ccxt
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# yfinance loader
# ---------------------------------------------------------------------------


def load_yfinance(
    ticker: str,
    start: str,
    end: str | None = None,
    interval: str = "1d",
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """Download OHLCV from yfinance and return normalized DataFrame."""
    end = end or datetime.today().strftime("%Y-%m-%d")
    raw = yf.download(
        ticker,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True,
        progress=False,
        multi_level_index=False,
    )
    if raw.empty:
        return pd.DataFrame()
    time.sleep(sleep_sec)

    df = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index.name = "timestamp"
    df = df.reset_index()
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df["ticker"] = ticker
    df["source"] = "yfinance"
    df["frequency"] = interval
    return df


# ---------------------------------------------------------------------------
# ccxt loader (crypto intraday)
# ---------------------------------------------------------------------------


def load_ccxt(
    symbol: str,
    exchange_id: str = "binance",
    timeframe: str = "1d",
    since_dt: datetime | None = None,
    limit: int = 1000,
    sleep_sec: float = 0.3,
) -> pd.DataFrame:
    """Download OHLCV from ccxt exchange (public, no API key needed)."""
    exchange_cls = getattr(ccxt, exchange_id)
    exchange = exchange_cls({"enableRateLimit": True})

    since_ms: int | None = None
    if since_dt:
        since_ms = int(since_dt.timestamp() * 1000)

    all_rows: list[list] = []
    while True:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since_ms, limit=limit)
        if not ohlcv:
            break
        all_rows.extend(ohlcv)
        if len(ohlcv) < limit:
            break
        since_ms = ohlcv[-1][0] + 1
        time.sleep(sleep_sec)

    if not all_rows:
        return pd.DataFrame()

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["ticker"] = symbol.replace("/", "-") + "-USD"
    df["source"] = f"ccxt:{exchange_id}"
    df["frequency"] = timeframe
    df = df.drop_duplicates(subset=["timestamp"])
    return df


# ---------------------------------------------------------------------------
# Batch loader (all instruments in config)
# ---------------------------------------------------------------------------


def load_all_yfinance(
    instruments: list[dict],
    start: str,
    end: str | None = None,
    interval: str = "1d",
    sleep_sec: float = 0.5,
) -> pd.DataFrame:
    """Load multiple tickers from yfinance. instruments = list of instrument dicts."""
    frames: list[pd.DataFrame] = []
    for inst in instruments:
        ticker = inst.get("yf_ticker") or inst["ticker"]
        try:
            df = load_yfinance(ticker, start=start, end=end, interval=interval, sleep_sec=sleep_sec)
            if not df.empty:
                df["ticker"] = inst["ticker"]  # normalize to config ticker
                df["asset_class"] = inst.get("asset_class", "")
                df["market"] = inst.get("market", "")
                frames.append(df)
        except Exception as exc:
            print(f"[WARN] yfinance load failed: {ticker} — {exc}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
