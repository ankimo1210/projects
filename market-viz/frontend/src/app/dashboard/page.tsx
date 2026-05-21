'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getDashboard } from '@/lib/api'
import { fmtPct, fmtNum, fmtPrice, retColor, zscoreColor, signalColor } from '@/lib/utils'
import type { DashboardRow } from '@/lib/types'

const ASSET_CLASSES = ['all', 'crypto', 'fx', 'equity', 'rates'] as const

export default function DashboardPage() {
  const [days, setDays] = useState(365)
  const [filter, setFilter] = useState<string>('all')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard', days],
    queryFn: () => getDashboard(days),
  })

  const rows: DashboardRow[] = (data?.rows ?? []).filter(
    r => filter === 'all' || r.asset_class === filter
  )

  const overbought = rows.filter(r => r.signal === 'Overbought').length
  const oversold   = rows.filter(r => r.signal === 'Oversold').length
  const watch      = rows.filter(r => r.signal.startsWith('Watch')).length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">📊 Market Dashboard</h1>
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={e => setDays(+e.target.value)}
            className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-sm rounded px-2 py-1"
          >
            {[90,180,365,730].map(d => <option key={d} value={d}>{d}日</option>)}
          </select>
          <button
            onClick={() => refetch()}
            className="bg-zinc-700 hover:bg-zinc-600 text-sm px-3 py-1 rounded transition-colors"
          >
            🔄 更新
          </button>
        </div>
      </div>

      {/* Summary metrics */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Overbought', value: overbought, color: 'text-orange-400' },
          { label: 'Oversold',   value: oversold,   color: 'text-blue-400'   },
          { label: 'Watch',      value: watch,       color: 'text-yellow-300' },
          { label: '銘柄数',      value: rows.length, color: 'text-zinc-300'  },
        ].map(m => (
          <div key={m.label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
            <p className="text-xs text-zinc-500">{m.label}</p>
            <p className={`text-2xl font-bold mt-1 ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {/* Asset class filter */}
      <div className="flex gap-2">
        {ASSET_CLASSES.map(ac => (
          <button
            key={ac}
            onClick={() => setFilter(ac)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors
              ${filter === ac
                ? 'border-zinc-400 bg-zinc-700 text-white'
                : 'border-zinc-700 text-zinc-400 hover:border-zinc-500'}`}
          >
            {ac}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-zinc-500">読み込み中...</p>}
      {error && <p className="text-red-400">エラー: APIに接続できません</p>}

      {rows.length > 0 && (
        <div className="overflow-auto rounded-lg border border-zinc-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                {['Ticker','名前','Class','終値','1D%','5D%','20D%','60D%','Vol20','Vol60','Z20','Z60','Pct20','現在DD','最大DD','シグナル'].map(h => (
                  <th key={h} className="px-3 py-2 text-left font-normal whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(r => (
                <tr key={r.ticker} className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors">
                  <td className="px-3 py-2 font-bold text-white whitespace-nowrap">{r.ticker}</td>
                  <td className="px-3 py-2 text-zinc-400 whitespace-nowrap max-w-32 truncate">{r.name}</td>
                  <td className="px-3 py-2 text-zinc-500">{r.asset_class}</td>
                  <td className="px-3 py-2 text-right">{fmtPrice(r.last_close)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_1d)}`}>{fmtPct(r.ret_1d)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_5d)}`}>{fmtPct(r.ret_5d)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_20d)}`}>{fmtPct(r.ret_20d)}</td>
                  <td className={`px-3 py-2 text-right ${retColor(r.ret_60d)}`}>{fmtPct(r.ret_60d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{fmtPct(r.vol_20d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{fmtPct(r.vol_60d)}</td>
                  <td className={`px-3 py-2 text-right ${zscoreColor(r.zscore_20d)}`}>{fmtNum(r.zscore_20d)}</td>
                  <td className={`px-3 py-2 text-right ${zscoreColor(r.zscore_60d)}`}>{fmtNum(r.zscore_60d)}</td>
                  <td className="px-3 py-2 text-right text-zinc-400">{r.pct_20d != null ? r.pct_20d.toFixed(0) + '%' : '—'}</td>
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
