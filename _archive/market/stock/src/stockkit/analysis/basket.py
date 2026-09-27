"""Index basket vs futures/ETF comparison.

Supports:
    Price-weighted indices (Nikkei 225, DJIA): weight_i = price_i / Σ price_j
    Market-cap weighted (S&P 500, NDX100): weight_i = mcap_i / Σ mcap_j

Note: For cap-weighted indices, current shares outstanding is used as a
constant approximation over the historical window (buybacks/issuances
ignored). Accuracy is best for short-medium periods.

Currency conversion: provide `to_currency='USD'` and the base currency code
(`base_ccy='JPY'`) to convert JPY-quoted results to USD using daily USD/JPY
(yfinance: JPY=X).
"""

from __future__ import annotations

import os
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import yfinance as yf

_DATA_DIR = Path(os.environ.get("STOCKKIT_DATA_DIR", Path(__file__).resolve().parents[3] / "_data"))
_SHARES_TTL_HOURS = 24


# ---------- Price fetching ----------


def fetch_basket_prices(
    tickers: list[str],
    start: str,
    end: str | None = None,
) -> pd.DataFrame:
    """Batch fetch Close prices via yfinance. Returns DataFrame[date, ticker]."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = yf.download(
            tickers,
            start=start,
            end=end,
            auto_adjust=False,
            progress=False,
            group_by="ticker",
            threads=True,
        )
    if df is None or df.empty:
        return pd.DataFrame()

    closes: dict[str, pd.Series] = {}
    if isinstance(df.columns, pd.MultiIndex):
        for tk in tickers:
            if (tk, "Close") in df.columns:
                closes[tk] = df[(tk, "Close")]
    else:
        if "Close" in df.columns and len(tickers) == 1:
            closes[tickers[0]] = df["Close"]

    out = pd.DataFrame(closes)
    out.index = pd.to_datetime(out.index).tz_localize(None)
    return out


def fetch_single_close(ticker: str, start: str, end: str | None = None) -> pd.Series | None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    if "Close" not in df.columns:
        return None
    s = df["Close"].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.ffill()


# Backwards-compat aliases
_fetch_single_close = fetch_single_close


def fetch_shares_outstanding(
    tickers: list[str],
    cache_key: str | None = None,
    max_workers: int = 20,
    use_cache: bool = True,
) -> pd.Series:
    """Fetch current shares outstanding (parallel + CSV cache).

    cache_key: optional name (e.g. "SP500") for CSV cache `_data/shares_{key}.csv`.
    max_workers: ThreadPoolExecutor concurrency for yfinance .info calls.
    use_cache: when True and cache is fresh (<24h), skip network entirely.
    """
    # 1. Try CSV cache
    if use_cache and cache_key:
        cache_path = _DATA_DIR / f"shares_{cache_key.lower()}.csv"
        if cache_path.exists():
            age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
            if age_hours < _SHARES_TTL_HOURS:
                cached = pd.read_csv(cache_path, index_col=0).iloc[:, 0]
                # Return cached values only for requested tickers
                hit = cached.reindex(tickers).dropna()
                if len(hit) >= len(tickers) * 0.95:  # 95%+ hit rate
                    return hit.rename("shares_outstanding")

    # 2. Parallel fetch using fast_info (no crumb needed, ~10x faster than .info)
    def _fetch_one(tk: str) -> tuple[str, float | None]:
        try:
            fi = yf.Ticker(tk).fast_info
            # fast_info exposes shares directly; fall back to market_cap / price
            so = getattr(fi, "shares", None)
            if so is None:
                mc = getattr(fi, "market_cap", None)
                px = getattr(fi, "last_price", None)
                if mc and px:
                    so = mc / px
            return tk, float(so) if so else None
        except Exception:
            return tk, None

    shares: dict[str, float] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for tk, val in ex.map(_fetch_one, tickers):
            if val:
                shares[tk] = val

    result = pd.Series(shares, name="shares_outstanding")

    # 3. Save cache
    if use_cache and cache_key and not result.empty:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        result.to_frame().to_csv(_DATA_DIR / f"shares_{cache_key.lower()}.csv")

    return result


# ---------- Weight & basket computation ----------


def compute_basket_returns(
    constituent_prices: pd.DataFrame,
    weighting: str = "price",
    shares: pd.Series | None = None,
) -> pd.Series:
    """Buy-and-hold basket cumulative returns.

    weighting='price': 1/price_i shares at t=0 (price-weighted, like Nikkei/DJIA)
    weighting='marketcap': shares_outstanding_i shares (cap-weighted, like SP500/NDX)
    """
    df = constituent_prices.dropna(how="all").ffill()
    if df.empty:
        return pd.Series(dtype=float)

    first_row = df.iloc[0].dropna()
    valid_tickers = first_row.index.tolist()
    df = df[valid_tickers]

    if weighting == "marketcap":
        if shares is None:
            raise ValueError("market-cap weighting requires `shares` series")
        held = shares.reindex(valid_tickers).fillna(0)
    else:  # price
        held = 1.0 / first_row

    basket_value = (df * held).sum(axis=1)
    if basket_value.iloc[0] <= 0:
        return pd.Series(dtype=float)
    return (basket_value / basket_value.iloc[0] - 1.0).rename("basket")


def compute_historical_weights(
    constituent_prices: pd.DataFrame,
    weighting: str = "price",
    shares: pd.Series | None = None,
) -> pd.DataFrame:
    """Time series of constituent weights."""
    df = constituent_prices.dropna(how="all").ffill()
    if df.empty:
        return pd.DataFrame()

    if weighting == "marketcap":
        if shares is None:
            raise ValueError("market-cap weighting requires `shares` series")
        mcap = df.mul(shares.reindex(df.columns).fillna(0), axis=1)
        row_sum = mcap.sum(axis=1)
        return mcap.div(row_sum, axis=0)
    else:
        row_sum = df.sum(axis=1)
        return df.div(row_sum, axis=0)


def weight_summary(
    weights: pd.DataFrame,
    names: pd.Series | None = None,
    top_n: int = 30,
) -> pd.DataFrame:
    """Per-ticker weight summary."""
    if weights.empty:
        return pd.DataFrame()
    start = weights.iloc[0]
    end = weights.iloc[-1]
    df = pd.DataFrame(
        {
            "current_weight": end,
            "start_weight": start,
            "weight_change_bp": (end - start) * 10000,
        }
    )
    if names is not None:
        df.insert(0, "name", df.index.map(names))
    return df.sort_values("current_weight", ascending=False).head(top_n)


# ---------- Currency conversion ----------


def to_usd(
    series: pd.Series, base_ccy: str = "JPY", start: str | None = None, end: str | None = None
) -> pd.Series:
    """Convert a JPY-quoted price series to USD using daily USD/JPY.

    series: pd.Series indexed by date, JPY values
    base_ccy: source currency (only JPY supported for now)
    """
    if base_ccy.upper() == "USD":
        return series
    if base_ccy.upper() != "JPY":
        raise NotImplementedError(f"Conversion from {base_ccy} not supported")

    fx = fetch_single_close("JPY=X", start=start or series.index[0].strftime("%Y-%m-%d"), end=end)
    if fx is None or fx.empty:
        return series
    # Align FX to series dates and forward-fill weekends
    fx_aligned = fx.reindex(series.index, method="ffill")
    return series / fx_aligned


# ---------- Comparison orchestration ----------


def compare_basket(
    universe: pd.DataFrame,
    start: str,
    end: str | None = None,
    weighting: str = "price",
    benchmarks: dict[str, str] | None = None,
    to_currency: str | None = None,
    base_ccy: str = "JPY",
    shares_cache_key: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series | None]:
    """Full pipeline: fetch prices → compute basket + benchmark returns.

    Returns (returns_df, constituent_prices_df, shares_outstanding_series).
    shares is None for price-weighted indices.
    shares_cache_key: pass index name (e.g. "SP500") to enable CSV cache.
    """
    benchmarks = benchmarks or {}

    # 1. Fetch constituents
    px = fetch_basket_prices(universe["ticker"].tolist(), start=start, end=end)

    # 2. Get shares outstanding if cap-weighted (with cache + parallel)
    shares = None
    if weighting == "marketcap":
        shares = fetch_shares_outstanding(
            universe["ticker"].tolist(),
            cache_key=shares_cache_key,
        )

    # 3. Basket returns
    basket_ret = compute_basket_returns(px, weighting=weighting, shares=shares)

    # 4. Benchmark cumulative returns
    result = pd.DataFrame({"basket": basket_ret})
    for label, ticker in benchmarks.items():
        s = fetch_single_close(ticker, start, end)
        if s is not None and not s.empty:
            result[label] = s / s.iloc[0] - 1.0
    result = result.dropna(how="all")

    # 5. Currency conversion (cumulative returns are already normalized,
    # so we convert the underlying basket value first, then re-normalize)
    if to_currency and to_currency.upper() != base_ccy.upper():
        # Re-compute basket as values, convert, then back to returns
        basket_value_jpy = (
            px.ffill().fillna(0)
            * (
                1.0 / px.iloc[0].dropna()
                if weighting == "price"
                else shares.reindex(px.columns).fillna(0)
            )
        ).sum(axis=1)
        basket_value_usd = to_usd(basket_value_jpy, base_ccy=base_ccy, start=start, end=end)
        result["basket"] = basket_value_usd / basket_value_usd.iloc[0] - 1.0

        # Convert each JPY-quoted benchmark
        for label, ticker in benchmarks.items():
            if label in result.columns and _is_jpy_ticker(ticker):
                s = fetch_single_close(ticker, start, end)
                if s is not None:
                    s_usd = to_usd(s, base_ccy="JPY", start=start, end=end)
                    result[label] = s_usd / s_usd.iloc[0] - 1.0

    return result, px, shares


def _is_jpy_ticker(ticker: str) -> bool:
    """Heuristic: tickers ending in .T or starting with ^N225 are JPY-quoted."""
    t = ticker.upper()
    return t.endswith(".T") or t == "^N225"


def tracking_error(returns: pd.DataFrame, vs: str) -> dict[str, float]:
    """Annualized tracking error vs reference column."""
    if vs not in returns.columns:
        return {}
    daily = (1 + returns).pct_change().dropna()
    ref = daily[vs]
    out: dict[str, float] = {}
    for col in returns.columns:
        if col == vs:
            continue
        diff = (daily[col] - ref).dropna()
        if len(diff) > 1:
            out[col] = float(diff.std() * (252**0.5))
    return out


# Backwards-compat alias
def compare_basket_vs_futures(start, end=None, universe=None):
    """Backwards-compat for the original Nikkei 225 entry point."""
    from stockkit.data.nikkei225 import load_constituents

    if universe is None:
        universe = load_constituents()
    benchmarks = {"n225": "^N225", "etf_1321": "1321.T", "futures_nkd": "NKD=F"}
    result, _, _ = compare_basket(
        universe, start=start, end=end, weighting="price", benchmarks=benchmarks
    )
    return result
