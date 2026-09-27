"""Signal generation from analytics matrices."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from market_viz.analytics.drawdown import build_drawdown_matrix
from market_viz.analytics.returns import build_return_matrix
from market_viz.analytics.volatility import build_vol_matrix
from market_viz.analytics.zscore import build_zscore_matrix


def _classify_zscore(z: float, ob: float = 2.0, os: float = -2.0, watch: float = 1.5) -> str:
    if z >= ob:
        return "Overbought"
    if z <= os:
        return "Oversold"
    if z >= watch:
        return "Watch-High"
    if z <= -watch:
        return "Watch-Low"
    return "Neutral"


def build_signal_df(prices_df: pd.DataFrame) -> pd.DataFrame:
    """Build a combined signal DataFrame from all analytics."""
    if prices_df.empty:
        return pd.DataFrame()

    ret_df = build_return_matrix(prices_df, periods=[1, 5, 20, 60, 252])
    vol_df = build_vol_matrix(prices_df, windows=[20, 60])
    z_df = build_zscore_matrix(prices_df, windows=[20, 60])
    dd_df = build_drawdown_matrix(prices_df)

    combined = ret_df.join(vol_df, how="outer").join(z_df, how="outer").join(dd_df, how="outer")

    if "zscore_20d" in combined.columns:
        combined["signal"] = combined["zscore_20d"].apply(
            lambda z: _classify_zscore(z) if pd.notna(z) else "N/A"
        )
    else:
        combined["signal"] = "N/A"

    return combined.reset_index()


def build_alert_df(
    prices_df: pd.DataFrame,
    vol_spike_mult: float = 1.5,
    zscore_thresh: float = 2.0,
    return_thresh_pct: float = 5.0,
) -> pd.DataFrame:
    """Generate alert rows from prices data."""
    alerts: list[dict] = []

    pivot = prices_df.pivot(index="timestamp", columns="ticker", values="close").sort_index()
    ret_pivot = pivot.pct_change()

    from market_viz.analytics.volatility import realized_vol
    from market_viz.analytics.zscore import rolling_zscore

    now = datetime.now()
    for ticker in pivot.columns:
        s = pivot[ticker].dropna()
        if len(s) < 21:
            continue

        # 1-day return alert
        ret_1d = ret_pivot[ticker].iloc[-1]
        if pd.notna(ret_1d) and abs(ret_1d) >= return_thresh_pct / 100:
            alerts.append(
                {
                    "alert_id": f"{ticker}_ret1d_{now.strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "condition_type": "return_1d",
                    "threshold": return_thresh_pct / 100,
                    "current_value": ret_1d,
                    "status": "active",
                    "triggered_at": now,
                    "message": f"{ticker} 1D return: {ret_1d:.1%}",
                }
            )

        # z-score alert
        z = rolling_zscore(s, window=20)
        last_z = z.iloc[-1]
        if pd.notna(last_z) and abs(last_z) >= zscore_thresh:
            direction = "above" if last_z > 0 else "below"
            alerts.append(
                {
                    "alert_id": f"{ticker}_zscore_{now.strftime('%Y%m%d')}",
                    "ticker": ticker,
                    "condition_type": "zscore_20d",
                    "threshold": zscore_thresh,
                    "current_value": last_z,
                    "status": "active",
                    "triggered_at": now,
                    "message": f"{ticker} z-score(20d)={last_z:.2f} ({direction} ±{zscore_thresh})",
                }
            )

        # vol spike alert
        rv = realized_vol(s, window=20)
        rv_60 = realized_vol(s, window=60)
        if len(rv) >= 2 and pd.notna(rv.iloc[-1]) and pd.notna(rv_60.iloc[-1]):
            if rv_60.iloc[-1] > 0 and rv.iloc[-1] / rv_60.iloc[-1] >= vol_spike_mult:
                alerts.append(
                    {
                        "alert_id": f"{ticker}_volspike_{now.strftime('%Y%m%d')}",
                        "ticker": ticker,
                        "condition_type": "vol_spike",
                        "threshold": vol_spike_mult,
                        "current_value": rv.iloc[-1] / rv_60.iloc[-1],
                        "status": "active",
                        "triggered_at": now,
                        "message": (
                            f"{ticker} vol spike: 20d={rv.iloc[-1]:.1%} vs 60d={rv_60.iloc[-1]:.1%}"
                        ),
                    }
                )

    return pd.DataFrame(alerts) if alerts else pd.DataFrame()
