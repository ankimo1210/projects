"""Financial series, chosen so the evaluation windows sit after any training cutoff.

The TimesFM 3.0 card dates its named sources no later than November 2023
(Wikipedia pageviews; Google Trends ends in 2022; GiftEvalPretrain is built from
corpora assembled before that).  Market data from 2026 therefore cannot be in the
pretraining corpus under any reading of the card — which makes this the one part
of the bench where "unseen" is a property of the calendar rather than an
inference about a file listing.

Three targets, picked because they sit at different points on the
predictability scale:

- ``log_volume`` has a strong day-of-week cycle and is genuinely forecastable.
- ``range_vol`` (Parkinson) clusters, which is what HAR was built to exploit.
- ``log_return`` is the control. If a model beats a random walk here by a
  meaningful margin, suspect the harness before believing the result.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd

from .paths import DATA_DIR

CACHE = DATA_DIR / "finance_ohlcv.parquet"

TICKERS: tuple[str, ...] = (
    # US large caps and index ETFs
    "SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA",
    "JPM",  # XOM does not resolve on this yfinance endpoint; left out to keep runs clean
    # Tokyo
    "7203.T", "6758.T", "8306.T", "9984.T", "6857.T",
    # 24/7
    "BTC-USD", "ETH-USD",
)

FETCH_START = "2018-01-01"

# Every evaluation target must start at or after this date, so no held-out point
# can predate the model's training data.
POST_CUTOFF = pd.Timestamp("2026-01-01")

TARGETS: dict[str, str] = {
    "fin_log_volume": "log_volume",
    "fin_range_vol": "range_vol",
    "fin_log_return": "log_return",
}


def fetch(tickers: tuple[str, ...] = TICKERS, start: str = FETCH_START) -> pd.DataFrame:
    """Download daily OHLCV and cache it. Network access lives only here."""
    import yfinance as yf

    frames = []
    for t in tickers:
        df = yf.download(t, start=start, progress=False, auto_adjust=True, threads=False)
        if df is None or df.empty:
            print(f"  {t}: no data")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()[["Date", "Open", "High", "Low", "Close", "Volume"]]
        df["ticker"] = t
        frames.append(df)
        print(f"  {t}: {len(df)} rows, {df.Date.min().date()}..{df.Date.max().date()}")
    out = pd.concat(frames, ignore_index=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(CACHE, index=False)
    return out


def load_ohlcv() -> pd.DataFrame:
    if not CACHE.exists():
        raise FileNotFoundError(f"{CACHE} missing; run scripts/fetch_finance.py first")
    return pd.read_parquet(CACHE)


def _parkinson(high: np.ndarray, low: np.ndarray) -> np.ndarray:
    """Parkinson range volatility: a daily-bar estimator that needs no intraday data.

    Roughly five times more efficient than close-to-close at the same sample size,
    which matters here because a daily close-to-close series is nearly all noise.
    """
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.log(np.asarray(high, float) / np.asarray(low, float))
    r = np.where(np.isfinite(r) & (r > 0), r, np.nan)
    return r / np.sqrt(4.0 * np.log(2.0))


def build_targets(df: pd.DataFrame) -> dict[str, list[tuple[str, np.ndarray, pd.Series]]]:
    """Derive the three target series per ticker, keeping the dates alongside."""
    out: dict[str, list[tuple[str, np.ndarray, pd.Series]]] = {k: [] for k in TARGETS}
    for ticker, g in df.groupby("ticker", sort=True):
        g = g.sort_values("Date")
        close = g.Close.to_numpy(float)
        vol = g.Volume.to_numpy(float)
        pk = _parkinson(g.High.to_numpy(float), g.Low.to_numpy(float))

        series = {
            # +1 keeps zero-volume days finite instead of dropping the whole ticker.
            "log_volume": np.log(np.where(vol > 0, vol, np.nan) + 1.0),
            "range_vol": np.log(pk * 1e4),
            "log_return": np.concatenate([[np.nan], np.diff(np.log(close))]) * 100.0,
        }
        for key, target in TARGETS.items():
            v = series[target]
            ok = np.isfinite(v)
            if ok.sum() < 800:
                continue
            out[key].append((ticker, v[ok], g.Date.to_numpy()[ok]))
    return out


@dataclasses.dataclass(frozen=True)
class FinanceWindowPlan:
    """Where the windows may be cut so every held-out point is post-cutoff."""

    context_length: int = 512
    horizon: int = 20  # one trading month
    n_windows: int = 6

    def cutoffs(self, dates: np.ndarray) -> list[int]:
        """Latest ``n_windows`` non-overlapping cutoffs whose target starts post-cutoff."""
        n = len(dates)
        idx = []
        for w in range(self.n_windows):
            end = n - w * self.horizon
            cut = end - self.horizon
            if cut - self.context_length < 0:
                break
            if pd.Timestamp(dates[cut]) < POST_CUTOFF:
                break
            idx.append(cut)
        return sorted(idx)
