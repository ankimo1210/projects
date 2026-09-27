'use client'

import dynamic from 'next/dynamic'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { getInstruments, runBacktest } from '@/lib/api'
import { fmtPct, fmtNum } from '@/lib/utils'
import type { BacktestResponse } from '@/lib/types'

const LineChart = dynamic(() => import('@/components/charts/LineChart'), { ssr: false })

type Strategy = 'ma_cross' | 'zscore_reversion' | 'momentum' | 'vol_breakout'

const STRATEGIES: { value: Strategy; label: string }[] = [
  { value: 'ma_cross',         label: 'MA Cross' },
  { value: 'zscore_reversion', label: 'Z-Score Reversion' },
  { value: 'momentum',         label: 'Momentum' },
  { value: 'vol_breakout',     label: 'Volatility Breakout' },
]

export default function BacktestPage() {
  const [ticker, setTicker] = useState('BTC-USD')
  const [strategy, setStrategy] = useState<Strategy>('ma_cross')
  const [periodDays, setPeriodDays] = useState(365)
  const [commission, setCommission] = useState(0.1)
  const [fast, setFast] = useState(20)
  const [slow, setSlow] = useState(60)
  const [zWindow, setZWindow] = useState(60)
  const [zEntry, setZEntry] = useState(2.0)
  const [zExit, setZExit] = useState(0.5)
  const [momWindow, setMomWindow] = useState(20)
  const [vbWindow, setVbWindow] = useState(20)
  const [vbMult, setVbMult] = useState(1.0)

  const { data: instruments } = useQuery({ queryKey: ['instruments'], queryFn: getInstruments })

  const { mutate, data: result, isPending, error } = useMutation({
    mutationFn: (req: Parameters<typeof runBacktest>[0]) => runBacktest(req),
  })

  const handleRun = () => {
    mutate({
      ticker, strategy, period_days: periodDays,
      commission: commission / 100, slippage: 0.0005,
      fast, slow, z_window: zWindow, z_entry: zEntry, z_exit: zExit,
      mom_window: momWindow, vb_window: vbWindow, vb_mult: vbMult,
    })
  }

  const equitySeries = result ? [{
    name: 'Equity',
    data: result.equity_timestamps.map((t, i) => ({
      time: t.slice(0, 10),
      value: result.equity_values[i],
    })),
    color: '#10b981',
  }] : []

  const m = result?.metrics

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold">🔬 Backtest</h1>

      {/* Settings */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="space-y-1">
          <label className="text-xs text-zinc-400">銘柄</label>
          <select value={ticker} onChange={e => setTicker(e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1.5">
            {(instruments ?? []).map(i => <option key={i.ticker} value={i.ticker}>{i.name}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-zinc-400">戦略</label>
          <select value={strategy} onChange={e => setStrategy(e.target.value as Strategy)}
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1.5">
            {STRATEGIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-zinc-400">期間</label>
          <select value={periodDays} onChange={e => setPeriodDays(+e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1.5">
            {[180,365,730,1825].map(d => <option key={d} value={d}>{d}日</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <label className="text-xs text-zinc-400">手数料 (%)</label>
          <input type="number" value={commission} step={0.01} min={0} max={0.5}
            onChange={e => setCommission(+e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1.5" />
        </div>
      </div>

      {/* Strategy params */}
      <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 space-y-3">
        <p className="text-xs text-zinc-400 font-semibold uppercase tracking-wide">戦略パラメータ</p>
        {strategy === 'ma_cross' && (
          <div className="flex gap-6">
            <Slider label={`Fast MA (${fast})`} value={fast} min={5} max={100} onChange={setFast} />
            <Slider label={`Slow MA (${slow})`} value={slow} min={20} max={300} onChange={setSlow} />
          </div>
        )}
        {strategy === 'zscore_reversion' && (
          <div className="flex gap-6 flex-wrap">
            <Slider label={`Z Window (${zWindow})`} value={zWindow} min={10} max={252} onChange={setZWindow} />
            <Slider label={`Entry ±${zEntry}`} value={zEntry} min={1} max={3} step={0.1} onChange={setZEntry} />
            <Slider label={`Exit ±${zExit}`} value={zExit} min={0} max={1.5} step={0.1} onChange={setZExit} />
          </div>
        )}
        {strategy === 'momentum' && (
          <Slider label={`Window (${momWindow})`} value={momWindow} min={5} max={252} onChange={setMomWindow} />
        )}
        {strategy === 'vol_breakout' && (
          <div className="flex gap-6">
            <Slider label={`Window (${vbWindow})`} value={vbWindow} min={5} max={100} onChange={setVbWindow} />
            <Slider label={`Mult (${vbMult}x)`} value={vbMult} min={0.5} max={3} step={0.1} onChange={setVbMult} />
          </div>
        )}
      </div>

      <button onClick={handleRun} disabled={isPending}
        className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors">
        {isPending ? '⏳ 計算中...' : '▶ バックテスト実行'}
      </button>

      {error && (
        <p className="text-red-400 text-sm">
          エラー: {(error as {response?: {data?: {detail?: string}}})?.response?.data?.detail ?? 'データが不足しているか、パラメータが不正です'}
        </p>
      )}

      {m && (
        <div className="space-y-4">
          {/* Metrics */}
          <div className="grid grid-cols-4 md:grid-cols-7 gap-2">
            {[
              { label: '累積リターン', value: fmtPct(m.total_return), color: m.total_return >= 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: '年率リターン', value: fmtPct(m.annual_return), color: m.annual_return >= 0 ? 'text-emerald-400' : 'text-red-400' },
              { label: '年率ボラ',     value: fmtPct(m.annual_volatility), color: 'text-zinc-300' },
              { label: 'Sharpe',      value: fmtNum(m.sharpe_ratio),       color: m.sharpe_ratio >= 1 ? 'text-emerald-400' : m.sharpe_ratio >= 0 ? 'text-yellow-300' : 'text-red-400' },
              { label: '最大DD',       value: fmtPct(m.max_drawdown),       color: 'text-red-400' },
              { label: '勝率',          value: fmtPct(m.win_rate),            color: 'text-zinc-300' },
              { label: '取引数',        value: String(m.trade_count),         color: 'text-zinc-300' },
            ].map(item => (
              <div key={item.label} className="bg-zinc-900 border border-zinc-800 rounded p-2">
                <p className="text-xs text-zinc-500">{item.label}</p>
                <p className={`text-lg font-bold mt-0.5 ${item.color}`}>{item.value}</p>
              </div>
            ))}
          </div>

          {/* Equity curve */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden">
            <p className="text-xs text-zinc-400 px-3 pt-2">エクイティカーブ</p>
            <LineChart series={equitySeries} height={280} />
          </div>
        </div>
      )}
    </div>
  )
}

function Slider({ label, value, min, max, step = 1, onChange }: {
  label: string; value: number; min: number; max: number; step?: number
  onChange: (v: number) => void
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-zinc-400 min-w-36">
      {label}
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(+e.target.value)}
        className="accent-emerald-500" />
    </label>
  )
}
