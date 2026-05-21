from datetime import date, timedelta
from typing import Optional
import math

from fastapi import APIRouter, HTTPException

from backend.app.deps import get_db
from backend.app.models.schemas import BacktestRequest, BacktestResponse, BacktestMetrics
from src.analytics.backtest import (
    run_backtest,
    ma_cross_signal,
    zscore_reversion_signal,
    momentum_signal,
    volatility_breakout_signal,
)

router = APIRouter(prefix="/backtest", tags=["backtest"])


def _safe_float(v) -> Optional[float]:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


@router.post("", response_model=BacktestResponse)
def run(req: BacktestRequest):
    db = get_db()
    start = (date.today() - timedelta(days=req.period_days)).isoformat()
    prices_df = db.get_prices([req.ticker], frequency="1d", start=start)
    if prices_df.empty:
        raise HTTPException(404, f"No data for {req.ticker}")

    strategy_map = {
        "ma_cross": lambda c: ma_cross_signal(c, fast=req.fast, slow=req.slow),
        "zscore_reversion": lambda c: zscore_reversion_signal(c, window=req.z_window, entry=req.z_entry, exit_=req.z_exit),
        "momentum": lambda c: momentum_signal(c, window=req.mom_window),
        "vol_breakout": lambda c: volatility_breakout_signal(c, window=req.vb_window, mult=req.vb_mult),
    }
    if req.strategy not in strategy_map:
        raise HTTPException(400, f"Unknown strategy: {req.strategy}")
    if req.strategy == "ma_cross" and req.fast >= req.slow:
        raise HTTPException(400, f"ma_cross: fast ({req.fast}) must be less than slow ({req.slow})")

    result = run_backtest(
        prices_df, req.ticker,
        signal_fn=strategy_map[req.strategy],
        commission=req.commission,
        slippage=req.slippage,
    )

    m = result.metrics
    return BacktestResponse(
        ticker=req.ticker,
        strategy=req.strategy,
        metrics=BacktestMetrics(
            total_return=float(m.get("total_return", 0) or 0),
            annual_return=float(m.get("annual_return", 0) or 0),
            annual_volatility=_safe_float(m.get("annual_volatility")),
            sharpe_ratio=float(m.get("sharpe_ratio", 0) or 0),
            max_drawdown=float(m.get("max_drawdown", 0) or 0),
            win_rate=float(m.get("win_rate", 0) or 0),
            trade_count=int(m.get("trade_count", 0)),
        ),
        equity_timestamps=[t.to_pydatetime() for t in result.equity.index],
        equity_values=[float(v) for v in result.equity.values],
        trades=[
            {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()}
            for row in result.trades.to_dict("records")
        ],
    )
