"""Pydantic response/request schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------


class Instrument(BaseModel):
    ticker: str
    name: str
    asset_class: str
    market: str
    source: str


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------


class PricesResponse(BaseModel):
    ticker: str
    frequency: str
    bars: list[OHLCVBar]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class DashboardRow(BaseModel):
    ticker: str
    name: str
    asset_class: str
    last_close: float | None
    ret_1d: float | None
    ret_5d: float | None
    ret_20d: float | None
    ret_60d: float | None
    vol_20d: float | None
    vol_60d: float | None
    zscore_20d: float | None
    zscore_60d: float | None
    pct_20d: float | None
    pct_60d: float | None
    current_dd: float | None
    max_dd: float | None
    signal: str


class DashboardResponse(BaseModel):
    rows: list[DashboardRow]
    updated_at: datetime


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


class CorrelationResponse(BaseModel):
    tickers: list[str]
    matrix: list[list[float | None]]
    window: int


class RollingCorrelationResponse(BaseModel):
    ticker_a: str
    ticker_b: str
    window: int
    timestamps: list[datetime]
    values: list[float | None]


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class SignalRow(BaseModel):
    ticker: str
    name: str
    asset_class: str
    last_close: float | None
    ret_1d: float | None
    ret_5d: float | None
    ret_20d: float | None
    vol_20d: float | None
    vol_60d: float | None
    zscore_20d: float | None
    zscore_60d: float | None
    pct_20d: float | None
    pct_60d: float | None
    current_dd: float | None
    max_dd: float | None
    signal: str


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------


class AlertRow(BaseModel):
    alert_id: str
    ticker: str
    condition_type: str
    threshold: float
    current_value: float
    message: str
    triggered_at: datetime


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


class BacktestRequest(BaseModel):
    ticker: str
    strategy: str  # "ma_cross" | "zscore_reversion" | "momentum" | "vol_breakout"
    period_days: int = 365
    commission: float = 0.001
    slippage: float = 0.0005
    # strategy params
    fast: int = 20
    slow: int = 60
    z_window: int = 60
    z_entry: float = 2.0
    z_exit: float = 0.5
    mom_window: int = 20
    vb_window: int = 20
    vb_mult: float = 1.0


class BacktestMetrics(BaseModel):
    total_return: float
    annual_return: float
    annual_volatility: float | None
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trade_count: int


class BacktestResponse(BaseModel):
    ticker: str
    strategy: str
    metrics: BacktestMetrics
    equity_timestamps: list[datetime]
    equity_values: list[float]
    trades: list[dict]


# ---------------------------------------------------------------------------
# Data update
# ---------------------------------------------------------------------------


class UpdateResponse(BaseModel):
    results: dict[str, str]
    ok_count: int
    error_count: int
    skipped_count: int
