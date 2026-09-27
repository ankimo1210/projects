'use client'

import dynamic from 'next/dynamic'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getCorrelation, getRollingCorrelation, getInstruments } from '@/lib/api'

const HeatmapChart = dynamic(() => import('@/components/charts/HeatmapChart'), { ssr: false })
const LineChart = dynamic(() => import('@/components/charts/LineChart'), { ssr: false })

const DEFAULT_PAIRS = [
  ['BTC-USD', 'SPY'],
  ['USDJPY=X', '^N225'],
  ['^TNX', 'SPY'],
  ['BTC-USD', 'QQQ'],
  ['GLD', 'USDJPY=X'],
] as const

export default function CorrelationPage() {
  const [days, setDays] = useState(365)
  const [heatWindow, setHeatWindow] = useState(60)
  const [rollWindow, setRollWindow] = useState(20)
  const [customA, setCustomA] = useState('BTC-USD')
  const [customB, setCustomB] = useState('SPY')

  const { data: corrData, isLoading: corrLoading } = useQuery({
    queryKey: ['correlation', days, heatWindow],
    queryFn: () => getCorrelation(days, heatWindow),
  })

  const { data: instruments } = useQuery({ queryKey: ['instruments'], queryFn: getInstruments })

  const { data: customRoll } = useQuery({
    queryKey: ['rolling-corr', customA, customB, days, rollWindow],
    queryFn: () => getRollingCorrelation(customA, customB, days, rollWindow),
  })

  const tickers = instruments?.map(i => i.ticker) ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">🔗 Correlation Monitor</h1>

      {/* Controls */}
      <div className="flex flex-wrap gap-3 items-center">
        <label className="text-xs text-zinc-400 flex items-center gap-2">
          期間
          <select value={days} onChange={e => setDays(+e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1">
            {[90,180,365,730].map(d => <option key={d} value={d}>{d}日</option>)}
          </select>
        </label>
        <label className="text-xs text-zinc-400 flex items-center gap-2">
          ヒートマップWindow
          <input type="range" min={20} max={252} value={heatWindow}
            onChange={e => setHeatWindow(+e.target.value)} className="w-24 accent-zinc-400" />
          <span>{heatWindow}日</span>
        </label>
        <label className="text-xs text-zinc-400 flex items-center gap-2">
          ローリングWindow
          <input type="range" min={5} max={120} value={rollWindow}
            onChange={e => setRollWindow(+e.target.value)} className="w-24 accent-zinc-400" />
          <span>{rollWindow}日</span>
        </label>
      </div>

      {/* Heatmap */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-2">相関ヒートマップ (直近{heatWindow}日)</h2>
        <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
          {corrLoading
            ? <p className="text-zinc-500 text-sm">計算中...</p>
            : <HeatmapChart tickers={corrData?.tickers ?? []} matrix={corrData?.matrix ?? []} />
          }
        </div>
      </section>

      {/* Default pairs */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-2">ローリング相関 (デフォルトペア)</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {DEFAULT_PAIRS.map(([a, b]) => (
            <RollingPairCard key={`${a}-${b}`} tickerA={a} tickerB={b} days={days} window={rollWindow} />
          ))}
        </div>
      </section>

      {/* Custom pair */}
      <section>
        <h2 className="text-sm font-semibold text-zinc-300 mb-2">カスタムペア</h2>
        <div className="flex gap-3 mb-3">
          <select value={customA} onChange={e => setCustomA(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1">
            {tickers.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
          <span className="text-zinc-500 self-center">vs</span>
          <select value={customB} onChange={e => setCustomB(e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1">
            {tickers.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        {customRoll && customRoll.values.length > 0 && (
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-4">
            <p className="text-xs text-zinc-400 mb-2">
              最新: <span className="text-white font-bold">
                {customRoll.values.at(-1)?.toFixed(3) ?? '—'}
              </span>
            </p>
            <LineChart
              height={220}
              series={[{
                name: `${customA} vs ${customB}`,
                data: customRoll.timestamps.map((t, i) => ({
                  time: t.slice(0, 10),
                  value: customRoll.values[i] ?? 0,
                })).filter((_, i) => customRoll.values[i] != null),
              }]}
            />
          </div>
        )}
      </section>
    </div>
  )
}

function RollingPairCard({
  tickerA, tickerB, days, window,
}: { tickerA: string; tickerB: string; days: number; window: number }) {
  const { data } = useQuery({
    queryKey: ['rolling-corr', tickerA, tickerB, days, window],
    queryFn: () => getRollingCorrelation(tickerA, tickerB, days, window),
  })
  if (!data || data.values.length === 0) return null
  const latest = data.values.filter(v => v != null).at(-1)
  return (
    <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3">
      <div className="flex justify-between mb-1">
        <span className="text-xs text-zinc-400">{tickerA} / {tickerB}</span>
        <span className={`text-xs font-bold ${latest != null && latest >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {latest?.toFixed(3) ?? '—'}
        </span>
      </div>
      <LineChart
        height={140}
        series={[{
          name: `corr(${window}d)`,
          data: data.timestamps.map((t, i) => ({
            time: t.slice(0, 10),
            value: data.values[i] ?? 0,
          })).filter((_, i) => data.values[i] != null),
        }]}
      />
    </div>
  )
}
