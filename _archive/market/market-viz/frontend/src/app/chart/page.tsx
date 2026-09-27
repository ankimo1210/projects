'use client'

import dynamic from 'next/dynamic'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getPrices, getInstruments } from '@/lib/api'
import { fmtPct, fmtNum } from '@/lib/utils'

const CandlestickChart = dynamic(() => import('@/components/charts/CandlestickChart'), { ssr: false })
const LineChart = dynamic(() => import('@/components/charts/LineChart'), { ssr: false })

const TABS = ['リターン', 'ボラティリティ', 'ドローダウン', 'Z-Score'] as const
type Tab = typeof TABS[number]

function computeSeries(bars: { timestamp: string; close: number | null }[], type: Tab, zWindow: number) {
  const closes = bars.filter(b => b.close != null).map(b => ({ t: b.timestamp.slice(0, 10), c: b.close! }))
  if (closes.length < 2) return []

  if (type === 'リターン') {
    let cum = 1
    const data = closes.slice(1).flatMap((b, i) => {
      if (closes[i].c === 0) return []
      cum *= (b.c / closes[i].c)
      return [{ time: b.t, value: +(cum - 1).toFixed(4) }]
    })
    return [{ name: '累積リターン', data }]
  }

  if (type === 'ボラティリティ') {
    const logRets = closes.slice(1).map((b, i) => Math.log(b.c / closes[i].c))
    const roll = (w: number) => logRets.map((_, i) => {
      if (i < w - 1) return null
      const slice = logRets.slice(i - w + 1, i + 1)
      const mean = slice.reduce((a, b) => a + b, 0) / w
      // ddof=1 to match pandas rolling std
      const std = w > 1 ? Math.sqrt(slice.reduce((a, b) => a + (b - mean) ** 2, 0) / (w - 1)) : 0
      return +(std * Math.sqrt(252)).toFixed(4)
    })
    return [
      { name: 'Vol(20)', data: roll(20).map((v, i) => v != null ? { time: closes[i + 1].t, value: v } : null).filter(Boolean) as {time:string;value:number}[] },
      { name: 'Vol(60)', data: roll(60).map((v, i) => v != null ? { time: closes[i + 1].t, value: v } : null).filter(Boolean) as {time:string;value:number}[] },
    ]
  }

  if (type === 'ドローダウン') {
    let peak = closes[0].c
    const data = closes.map(b => {
      if (b.c > peak) peak = b.c
      return { time: b.t, value: +((b.c - peak) / peak).toFixed(4) }
    })
    return [{ name: 'ドローダウン', data, color: '#ef4444' }]
  }

  // Z-Score
  const vals = closes.map(b => b.c)
  const w = zWindow
  const data = closes.map((b, i) => {
    if (i < w - 1) return null
    const slice = vals.slice(i - w + 1, i + 1)
    const mean = slice.reduce((a, v) => a + v, 0) / w
    // ddof=1 (sample std) to match backend pandas .std()
    const std = w > 1 ? Math.sqrt(slice.reduce((a, v) => a + (v - mean) ** 2, 0) / (w - 1)) : 0
    return { time: b.t, value: std > 0 ? +((b.c - mean) / std).toFixed(3) : 0 }
  }).filter(Boolean) as { time: string; value: number }[]
  return [{ name: `Z-Score(${w})`, data }]
}

export default function ChartPage() {
  const [ticker, setTicker] = useState('BTC-USD')
  const [days, setDays] = useState(365)
  const [maWindows, setMaWindows] = useState<number[]>([20, 50])
  const [activeTab, setActiveTab] = useState<Tab>('リターン')
  const [zWindow, setZWindow] = useState(60)

  const { data: instruments } = useQuery({ queryKey: ['instruments'], queryFn: getInstruments })
  const { data: prices, isLoading } = useQuery({
    queryKey: ['prices', ticker, days],
    queryFn: () => getPrices(ticker, days),
    enabled: !!ticker,
  })

  const bars = prices?.bars ?? []

  const toggleMA = (w: number) =>
    setMaWindows(prev => prev.includes(w) ? prev.filter(x => x !== w) : [...prev, w])

  const subSeries = computeSeries(bars, activeTab, zWindow)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">📈 Chart Workbench</h1>

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={ticker}
          onChange={e => setTicker(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1"
        >
          {(instruments ?? []).map(i => (
            <option key={i.ticker} value={i.ticker}>{i.name} ({i.ticker})</option>
          ))}
        </select>
        <select
          value={days}
          onChange={e => setDays(+e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1"
        >
          {[30,90,180,365,730,1825].map(d => <option key={d} value={d}>{d}日</option>)}
        </select>
        <div className="flex items-center gap-1 text-xs text-zinc-400">
          MA:
          {[10,20,50,100,200].map(w => (
            <button
              key={w}
              onClick={() => toggleMA(w)}
              className={`px-2 py-0.5 rounded border transition-colors
                ${maWindows.includes(w) ? 'border-yellow-400 text-yellow-400' : 'border-zinc-700 text-zinc-500'}`}
            >
              {w}
            </button>
          ))}
        </div>
      </div>

      {isLoading && <p className="text-zinc-500">読み込み中...</p>}

      {bars.length > 0 && (
        <>
          <div className="rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden">
            <CandlestickChart bars={bars} ticker={ticker} maWindows={maWindows} showVolume />
          </div>

          {/* Sub-chart tabs */}
          <div className="space-y-2">
            <div className="flex gap-2">
              {TABS.map(t => (
                <button
                  key={t}
                  onClick={() => setActiveTab(t)}
                  className={`text-xs px-3 py-1 rounded border transition-colors
                    ${activeTab === t
                      ? 'border-zinc-400 bg-zinc-700 text-white'
                      : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}
                >
                  {t}
                </button>
              ))}
              {activeTab === 'Z-Score' && (
                <input
                  type="range" min={10} max={252} value={zWindow}
                  onChange={e => setZWindow(+e.target.value)}
                  className="w-28 accent-zinc-400"
                />
              )}
              {activeTab === 'Z-Score' && (
                <span className="text-xs text-zinc-400 self-center">window={zWindow}</span>
              )}
            </div>
            <div className="rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden">
              <LineChart series={subSeries} height={220} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}
