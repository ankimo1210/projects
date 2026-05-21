'use client'

import { useQuery } from '@tanstack/react-query'
import { useState, useMemo } from 'react'
import { getSignals } from '@/lib/api'
import { fmtPct, fmtNum, retColor, zscoreColor, signalColor } from '@/lib/utils'
import type { SignalRow } from '@/lib/types'

type SortKey = 'zscore_20d' | 'zscore_60d' | 'pct_20d' | 'ret_20d' | 'vol_20d' | 'current_dd'
const SIGNALS_FILTER = ['Overbought', 'Oversold', 'Watch-High', 'Watch-Low', 'Neutral', 'N/A']

export default function SignalsPage() {
  const [days, setDays] = useState(365)
  const [assetFilter, setAssetFilter] = useState<string>('all')
  const [signalFilter, setSignalFilter] = useState<string[]>(['Overbought', 'Oversold', 'Watch-High', 'Watch-Low'])
  const [sortKey, setSortKey] = useState<SortKey>('zscore_20d')

  const { data: rows = [], isLoading } = useQuery({
    queryKey: ['signals', days],
    queryFn: () => getSignals(days),
  })

  const assetClasses = useMemo(() => ['all', ...new Set(rows.map(r => r.asset_class).filter(Boolean))], [rows])

  const filtered = useMemo(() =>
    rows
      .filter(r => assetFilter === 'all' || r.asset_class === assetFilter)
      .filter(r => signalFilter.includes(r.signal))
      .sort((a, b) => Math.abs(b[sortKey] ?? 0) - Math.abs(a[sortKey] ?? 0)),
  [rows, assetFilter, signalFilter, sortKey])

  const toggleSignal = (s: string) =>
    setSignalFilter(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">🚦 Signal Ranking</h1>
        <select value={days} onChange={e => setDays(+e.target.value)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1">
          {[90,180,365,730].map(d => <option key={d} value={d}>{d}日</option>)}
        </select>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex gap-1 flex-wrap">
          {assetClasses.map(ac => (
            <button key={ac} onClick={() => setAssetFilter(ac)}
              className={`text-xs px-2 py-0.5 rounded border transition-colors
                ${assetFilter === ac ? 'border-zinc-400 bg-zinc-700 text-white' : 'border-zinc-700 text-zinc-400'}`}>
              {ac}
            </button>
          ))}
        </div>
        <div className="flex gap-1 flex-wrap">
          {SIGNALS_FILTER.map(s => (
            <button key={s} onClick={() => toggleSignal(s)}
              className={`text-xs px-2 py-0.5 rounded border transition-colors
                ${signalFilter.includes(s) ? 'border-zinc-400 bg-zinc-700 text-white' : 'border-zinc-700 text-zinc-400'}`}>
              {s}
            </button>
          ))}
        </div>
        <select value={sortKey} onChange={e => setSortKey(e.target.value as SortKey)}
          className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs rounded px-2 py-1">
          <option value="zscore_20d">ソート: Z(20)</option>
          <option value="zscore_60d">ソート: Z(60)</option>
          <option value="pct_20d">ソート: Pct(20)</option>
          <option value="ret_20d">ソート: Ret(20D)</option>
          <option value="vol_20d">ソート: Vol(20)</option>
          <option value="current_dd">ソート: 現在DD</option>
        </select>
      </div>

      <p className="text-xs text-zinc-500">{filtered.length}件</p>

      {isLoading && <p className="text-zinc-500">読み込み中...</p>}

      {filtered.length > 0 && (
        <div className="overflow-auto rounded-lg border border-zinc-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                {['Ticker','名前','Class','1D%','5D%','20D%','Vol20','Vol60','Z20','Z60','Pct20','現在DD','最大DD','シグナル'].map(h => (
                  <th key={h} className="px-3 py-2 text-left font-normal whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((r: SignalRow) => (
                <tr key={r.ticker} className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors">
                  <td className="px-3 py-2 font-bold text-white whitespace-nowrap">{r.ticker}</td>
                  <td className="px-3 py-2 text-zinc-400 max-w-28 truncate">{r.name}</td>
                  <td className="px-3 py-2 text-zinc-500">{r.asset_class}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_1d)}`}>{fmtPct(r.ret_1d)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_5d)}`}>{fmtPct(r.ret_5d)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_20d)}`}>{fmtPct(r.ret_20d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{fmtPct(r.vol_20d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{fmtPct(r.vol_60d)}</td>
                  <td className={`px-3 py-2 text-right ${zscoreColor(r.zscore_20d)}`}>{fmtNum(r.zscore_20d)}</td>
                  <td className={`px-3 py-2 text-right ${zscoreColor(r.zscore_60d)}`}>{fmtNum(r.zscore_60d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{r.pct_20d != null ? r.pct_20d.toFixed(0)+'%' : '—'}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.current_dd)}`}>{fmtPct(r.current_dd)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.max_dd)}`}>{fmtPct(r.max_dd)}</td>
                  <td className={`px-3 py-2 whitespace-nowrap ${signalColor(r.signal)}`}>{r.signal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
