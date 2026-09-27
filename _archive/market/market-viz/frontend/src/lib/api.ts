import axios from 'axios'
import type {
  Instrument, PricesResponse, DashboardResponse,
  CorrelationResponse, RollingCorrelationResponse,
  SignalRow, AlertRow, BacktestRequest, BacktestResponse, UpdateResponse,
} from './types'

// 空文字 = 相対パス → Next.js が /api/* をバックエンドへ proxy する
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ''
const api = axios.create({ baseURL: BASE })

export const getInstruments = (): Promise<Instrument[]> =>
  api.get('/api/instruments').then(r => r.data)

export const getPrices = (ticker: string, days = 365, frequency = '1d'): Promise<PricesResponse> =>
  api.get(`/api/prices/${encodeURIComponent(ticker)}`, { params: { days, frequency } }).then(r => r.data)

export const getDashboard = (days = 365): Promise<DashboardResponse> =>
  api.get('/api/analytics/dashboard', { params: { days } }).then(r => r.data)

export const getSignals = (days = 365): Promise<SignalRow[]> =>
  api.get('/api/analytics/signals', { params: { days } }).then(r => r.data)

export const getCorrelation = (days = 365, window = 60): Promise<CorrelationResponse> =>
  api.get('/api/analytics/correlation', { params: { days, window } }).then(r => r.data)

export const getRollingCorrelation = (
  ticker_a: string, ticker_b: string, days = 365, window = 20,
): Promise<RollingCorrelationResponse> =>
  api.get('/api/analytics/correlation/rolling', { params: { ticker_a, ticker_b, days, window } }).then(r => r.data)

export const getAlerts = (
  days = 180, zscore_thresh = 2.0, return_thresh_pct = 5.0, vol_spike_mult = 1.5,
): Promise<AlertRow[]> =>
  api.get('/api/alerts', { params: { days, zscore_thresh, return_thresh_pct, vol_spike_mult } }).then(r => r.data)

export const runBacktest = (req: BacktestRequest): Promise<BacktestResponse> =>
  api.post('/api/backtest', req).then(r => r.data)

export const updateDaily = (days = 365): Promise<UpdateResponse> =>
  api.post('/api/data/update/daily', null, { params: { days } }).then(r => r.data)

export const updateCryptoIntraday = (timeframe = '1m', days = 3): Promise<UpdateResponse> =>
  api.post('/api/data/update/crypto-intraday', null, { params: { timeframe, days } }).then(r => r.data)
