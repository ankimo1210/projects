export interface Instrument {
  ticker: string
  name: string
  asset_class: string
  market: string
  source: string
}

export interface OHLCVBar {
  timestamp: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
}

export interface PricesResponse {
  ticker: string
  frequency: string
  bars: OHLCVBar[]
}

export interface DashboardRow {
  ticker: string
  name: string
  asset_class: string
  last_close: number | null
  ret_1d: number | null
  ret_5d: number | null
  ret_20d: number | null
  ret_60d: number | null
  vol_20d: number | null
  vol_60d: number | null
  zscore_20d: number | null
  zscore_60d: number | null
  pct_20d: number | null
  pct_60d: number | null
  current_dd: number | null
  max_dd: number | null
  signal: string
}

export interface DashboardResponse {
  rows: DashboardRow[]
  updated_at: string
}

export interface CorrelationResponse {
  tickers: string[]
  matrix: (number | null)[][]
  window: number
}

export interface RollingCorrelationResponse {
  ticker_a: string
  ticker_b: string
  window: number
  timestamps: string[]
  values: (number | null)[]
}

export interface SignalRow {
  ticker: string
  name: string
  asset_class: string
  last_close: number | null
  ret_1d: number | null
  ret_5d: number | null
  ret_20d: number | null
  vol_20d: number | null
  vol_60d: number | null
  zscore_20d: number | null
  zscore_60d: number | null
  pct_20d: number | null
  pct_60d: number | null
  current_dd: number | null
  max_dd: number | null
  signal: string
}

export interface AlertRow {
  alert_id: string
  ticker: string
  condition_type: string
  threshold: number
  current_value: number
  message: string
  triggered_at: string
}

export interface BacktestRequest {
  ticker: string
  strategy: string
  period_days: number
  commission: number
  slippage: number
  fast?: number
  slow?: number
  z_window?: number
  z_entry?: number
  z_exit?: number
  mom_window?: number
  vb_window?: number
  vb_mult?: number
}

export interface BacktestMetrics {
  total_return: number
  annual_return: number
  annual_volatility: number | null
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  trade_count: number
}

export interface BacktestResponse {
  ticker: string
  strategy: string
  metrics: BacktestMetrics
  equity_timestamps: string[]
  equity_values: number[]
  trades: Record<string, unknown>[]
}

export interface UpdateResponse {
  results: Record<string, string>
  ok_count: number
  error_count: number
  skipped_count: number
}
