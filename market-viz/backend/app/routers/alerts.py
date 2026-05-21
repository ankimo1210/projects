from datetime import date, timedelta

from fastapi import APIRouter, Query
from market_viz.analytics.signals import build_alert_df

from backend.app.deps import get_db, load_instruments
from backend.app.models.schemas import AlertRow

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRow])
def get_alerts(
    days: int = Query(180, ge=30, le=1825),
    zscore_thresh: float = Query(2.0),
    return_thresh_pct: float = Query(5.0),
    vol_spike_mult: float = Query(1.5),
):
    db = get_db()
    tickers = [i["ticker"] for i in load_instruments()]
    start = (date.today() - timedelta(days=days)).isoformat()
    prices_df = db.get_prices(tickers, frequency="1d", start=start)
    if prices_df.empty:
        return []

    alerts_df = build_alert_df(
        prices_df,
        vol_spike_mult=vol_spike_mult,
        zscore_thresh=zscore_thresh,
        return_thresh_pct=return_thresh_pct,
    )
    if alerts_df.empty:
        return []

    return [
        AlertRow(
            alert_id=str(row["alert_id"]),
            ticker=str(row["ticker"]),
            condition_type=str(row["condition_type"]),
            threshold=float(row["threshold"]),
            current_value=float(row["current_value"]),
            message=str(row["message"]),
            triggered_at=row["triggered_at"],
        )
        for _, row in alerts_df.iterrows()
    ]
