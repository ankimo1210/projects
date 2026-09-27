from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Query

from backend.app.deps import get_db
from backend.app.models.schemas import OHLCVBar, PricesResponse

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("/{ticker}", response_model=PricesResponse)
def get_prices(
    ticker: str,
    frequency: str = Query("1d", description="1d | 1h | 1m"),
    days: int = Query(365, ge=1, le=1825),
    start: str | None = Query(None),
):
    db = get_db()
    start_str = start or (date.today() - timedelta(days=days)).isoformat()
    df = db.get_prices([ticker], frequency=frequency, start=start_str)
    if df.empty:
        raise HTTPException(404, f"No data for {ticker} (freq={frequency})")

    df = df.sort_values("timestamp")
    bars = [
        OHLCVBar(
            timestamp=row["timestamp"],
            open=row.get("open"),
            high=row.get("high"),
            low=row.get("low"),
            close=row.get("close"),
            volume=row.get("volume"),
        )
        for _, row in df.iterrows()
    ]
    return PricesResponse(ticker=ticker, frequency=frequency, bars=bars)
