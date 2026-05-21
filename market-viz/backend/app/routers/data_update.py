from fastapi import APIRouter, Query
from market_viz.data.update import update_crypto_intraday, update_daily

from backend.app.deps import get_db
from backend.app.models.schemas import UpdateResponse

router = APIRouter(prefix="/data", tags=["data"])


@router.post("/update/daily", response_model=UpdateResponse)
def trigger_daily_update(days: int = Query(365, ge=30, le=1825)):
    db = get_db()
    results = update_daily(db, lookback_days=days)
    ok = sum(1 for v in results.values() if v.startswith("ok"))
    errors = sum(1 for v in results.values() if v.startswith("error"))
    skipped = sum(1 for v in results.values() if v == "up-to-date")
    return UpdateResponse(results=results, ok_count=ok, error_count=errors, skipped_count=skipped)


@router.post("/update/crypto-intraday", response_model=UpdateResponse)
def trigger_crypto_intraday(
    timeframe: str = Query("1m"),
    days: int = Query(3, ge=1, le=30),
):
    db = get_db()
    results = update_crypto_intraday(db, timeframe=timeframe, lookback_days=days)
    ok = sum(1 for v in results.values() if v.startswith("ok"))
    errors = sum(1 for v in results.values() if v.startswith("error"))
    skipped = sum(1 for v in results.values() if v == "up-to-date")
    return UpdateResponse(results=results, ok_count=ok, error_count=errors, skipped_count=skipped)
