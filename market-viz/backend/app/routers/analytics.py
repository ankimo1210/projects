from datetime import date, timedelta

import numpy as np
from fastapi import APIRouter, Query
from market_viz.analytics.correlation import latest_correlations, rolling_correlation
from market_viz.analytics.signals import build_signal_df

from backend.app.deps import get_db, get_ticker_meta, load_instruments
from backend.app.models.schemas import (
    CorrelationResponse,
    DashboardResponse,
    DashboardRow,
    RollingCorrelationResponse,
    SignalRow,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _safe(v) -> float | None:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return float(v)


def _get_prices_all(days: int):
    db = get_db()
    tickers = [i["ticker"] for i in load_instruments()]
    start = (date.today() - timedelta(days=days)).isoformat()
    return db.get_prices(tickers, frequency="1d", start=start)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(days: int = Query(365, ge=30, le=1825)):
    prices_df = _get_prices_all(days)
    meta = get_ticker_meta()

    if prices_df.empty:
        return DashboardResponse(rows=[], updated_at=date.today())

    sig_df = build_signal_df(prices_df)
    rows: list[DashboardRow] = []
    for _, r in sig_df.iterrows():
        ticker = r["ticker"]
        m = meta.get(ticker, {})
        rows.append(
            DashboardRow(
                ticker=ticker,
                name=m.get("name", ticker),
                asset_class=m.get("asset_class", ""),
                last_close=_safe(r.get("last_close")),
                ret_1d=_safe(r.get("ret_1d")),
                ret_5d=_safe(r.get("ret_5d")),
                ret_20d=_safe(r.get("ret_20d")),
                ret_60d=_safe(r.get("ret_60d")),
                vol_20d=_safe(r.get("vol_20d")),
                vol_60d=_safe(r.get("vol_60d")),
                zscore_20d=_safe(r.get("zscore_20d")),
                zscore_60d=_safe(r.get("zscore_60d")),
                pct_20d=_safe(r.get("pct_20d")),
                pct_60d=_safe(r.get("pct_60d")),
                current_dd=_safe(r.get("current_dd")),
                max_dd=_safe(r.get("max_dd")),
                signal=str(r.get("signal", "N/A")),
            )
        )

    from datetime import datetime

    return DashboardResponse(rows=rows, updated_at=datetime.now())


# ---------------------------------------------------------------------------
# Signals / Ranking
# ---------------------------------------------------------------------------


@router.get("/signals", response_model=list[SignalRow])
def get_signals(days: int = Query(365, ge=30, le=1825)):
    prices_df = _get_prices_all(days)
    meta = get_ticker_meta()
    if prices_df.empty:
        return []
    sig_df = build_signal_df(prices_df)
    rows: list[SignalRow] = []
    for _, r in sig_df.iterrows():
        ticker = r["ticker"]
        m = meta.get(ticker, {})
        rows.append(
            SignalRow(
                ticker=ticker,
                name=m.get("name", ticker),
                asset_class=m.get("asset_class", ""),
                last_close=_safe(r.get("last_close")),
                ret_1d=_safe(r.get("ret_1d")),
                ret_5d=_safe(r.get("ret_5d")),
                ret_20d=_safe(r.get("ret_20d")),
                vol_20d=_safe(r.get("vol_20d")),
                vol_60d=_safe(r.get("vol_60d")),
                zscore_20d=_safe(r.get("zscore_20d")),
                zscore_60d=_safe(r.get("zscore_60d")),
                pct_20d=_safe(r.get("pct_20d")),
                pct_60d=_safe(r.get("pct_60d")),
                current_dd=_safe(r.get("current_dd")),
                max_dd=_safe(r.get("max_dd")),
                signal=str(r.get("signal", "N/A")),
            )
        )
    return rows


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


@router.get("/correlation", response_model=CorrelationResponse)
def get_correlation(
    days: int = Query(365, ge=60, le=1825),
    window: int = Query(60, ge=10, le=252),
):
    prices_df = _get_prices_all(days)
    if prices_df.empty:
        return CorrelationResponse(tickers=[], matrix=[], window=window)

    corr = latest_correlations(prices_df, window=window)
    tickers = corr.columns.tolist()
    matrix = [[_safe(corr.loc[r, c]) for c in tickers] for r in tickers]
    return CorrelationResponse(tickers=tickers, matrix=matrix, window=window)


@router.get("/correlation/rolling", response_model=RollingCorrelationResponse)
def get_rolling_correlation(
    ticker_a: str = Query(...),
    ticker_b: str = Query(...),
    days: int = Query(365, ge=60, le=1825),
    window: int = Query(20, ge=5, le=120),
):
    prices_df = _get_prices_all(days)
    rc = rolling_correlation(prices_df, ticker_a, ticker_b, window=window)
    rc = rc.dropna()
    return RollingCorrelationResponse(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        window=window,
        timestamps=rc.index.tolist(),
        values=[_safe(v) for v in rc.values],
    )
