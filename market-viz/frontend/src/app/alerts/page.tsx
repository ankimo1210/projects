'use client'

import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { getAlerts } from '@/lib/api'
import { fmtNum } from '@/lib/utils'
import type { AlertRow } from '@/lib/types'

const COND_LABEL: Record<string, string> = {
  return_1d:  '📈 リターン1D',
  zscore_20d: '📊 Z-Score(20)',
  vol_spike:  '⚡ ボラ急騰',
}

export default function AlertsPage() {
  const [days, setDays]               = useState(180)
  const [zscoreThresh, setZscoreThresh] = useState(2.0)
  const [retThresh, setRetThresh]       = useState(5.0)
  const [volMult, setVolMult]           = useState(1.5)

  const { data: alerts = [], isLoading, refetch } = useQuery({
    queryKey: ['alerts', days, zscoreThresh, retThresh, volMult],
    queryFn: () => getAlerts(days, zscoreThresh, retThresh, volMult),
  })

  const byType = (t: string) => alerts.filter(a => a.condition_type === t)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">🔔 Alert Monitor</h1>
        <button onClick={() => refetch()}
          className="bg-zinc-700 hover:bg-zinc-600 text-sm px-3 py-1 rounded transition-colors">
          🔄 再計算
        </button>
      </div>

      {/* Thresholds */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-zinc-900 border border-zinc-800 rounded-lg p-4">
        <Param label="評価期間" unit="日">
          <select value={days} onChange={e => setDays(+e.target.value)}
            className="w-full bg-zinc-800 border border-zinc-700 text-sm rounded px-2 py-1">
            {[90,180,365].map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </Param>
        <Param label={`Z-Score閾値 (±${zscoreThresh})`} unit="">
          <input type="range" min={1} max={3} step={0.1} value={zscoreThresh}
            onChange={e => setZscoreThresh(+e.target.value)} className="w-full accent-orange-400" />
        </Param>
        <Param label={`1日リターン閾値 (${retThresh}%)`} unit="">
          <input type="range" min={1} max={10} step={0.5} value={retThresh}
            onChange={e => setRetThresh(+e.target.value)} className="w-full accent-orange-400" />
        </Param>
        <Param label={`ボラ急騰倍率 (${volMult}x)`} unit="">
          <input type="range" min={1} max={3} step={0.1} value={volMult}
            onChange={e => setVolMult(+e.target.value)} className="w-full accent-orange-400" />
        </Param>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: '総アラート', value: alerts.length, color: 'text-zinc-200' },
          { label: 'リターン系',  value: byType('return_1d').length, color: 'text-orange-400' },
          { label: 'Z-Score系',  value: byType('zscore_20d').length, color: 'text-blue-400' },
          { label: 'ボラ急騰',    value: byType('vol_spike').length,  color: 'text-red-400' },
        ].map(m => (
          <div key={m.label} className="bg-zinc-900 border border-zinc-800 rounded-lg p-3">
            <p className="text-xs text-zinc-500">{m.label}</p>
            <p className={`text-2xl font-bold mt-1 ${m.color}`}>{m.value}</p>
          </div>
        ))}
      </div>

      {isLoading && <p className="text-zinc-500">計算中...</p>}

      {alerts.length === 0 && !isLoading && (
        <div className="text-center py-12 text-zinc-500">
          <p className="text-4xl mb-2">✅</p>
          <p>アクティブなアラートはありません</p>
        </div>
      )}

      {alerts.length > 0 && (
        <div className="overflow-auto rounded-lg border border-zinc-800">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-zinc-800 text-zinc-400">
                {['銘柄','条件','現在値','閾値','メッセージ','発生時刻'].map(h => (
                  <th key={h} className="px-3 py-2 text-left font-normal whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((a: AlertRow) => (
                <tr key={a.alert_id} className="border-b border-zinc-900 hover:bg-zinc-900/50 transition-colors">
                  <td className="px-3 py-2 font-bold text-white">{a.ticker}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{COND_LABEL[a.condition_type] ?? a.condition_type}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNum(a.current_value, 3)}</td>
                  <td className="px-3 py-2 text-right font-mono text-zinc-500">{fmtNum(a.threshold, 3)}</td>
                  <td className="px-3 py-2 text-zinc-300 max-w-sm truncate">{a.message}</td>
                  <td className="px-3 py-2 text-zinc-500 whitespace-nowrap">
                    {new Date(a.triggered_at).toLocaleString('ja-JP', { month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function Param({ label, unit, children }: { label: string; unit: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-xs text-zinc-400">{label}{unit && ` (${unit})`}</label>
      {children}
    </div>
  )
}
