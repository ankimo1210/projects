'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import { updateDaily, updateCryptoIntraday } from '@/lib/api'

const NAV = [
  { href: '/dashboard',    label: 'Dashboard',     icon: '📊' },
  { href: '/chart',        label: 'Chart',          icon: '📈' },
  { href: '/correlation',  label: 'Correlation',    icon: '🔗' },
  { href: '/signals',      label: 'Signals',        icon: '🚦' },
  { href: '/backtest',     label: 'Backtest',       icon: '🔬' },
  { href: '/alerts',       label: 'Alerts',         icon: '🔔' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [loading, setLoading] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  async function handleUpdate(type: 'daily' | 'crypto') {
    setLoading(type)
    setMsg(null)
    try {
      const res = type === 'daily'
        ? await updateDaily(365)
        : await updateCryptoIntraday('1m', 3)
      setMsg(`✅ ${res.ok_count}件更新 / ${res.skipped_count}件スキップ / ${res.error_count}件エラー`)
    } catch {
      setMsg('❌ 更新失敗')
    } finally {
      setLoading(null)
    }
  }

  return (
    <aside className="flex flex-col w-52 min-h-screen bg-zinc-900 border-r border-zinc-800 px-3 py-5 shrink-0">
      <div className="text-lg font-bold text-white mb-6 px-2">📈 Market Viz</div>

      <nav className="flex flex-col gap-1 flex-1">
        {NAV.map(({ href, label, icon }) => {
          const active = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors
                ${active
                  ? 'bg-zinc-700 text-white font-medium'
                  : 'text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100'}`}
            >
              <span>{icon}</span>
              <span>{label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="mt-6 border-t border-zinc-800 pt-4 flex flex-col gap-2">
        <button
          onClick={() => handleUpdate('daily')}
          disabled={loading !== null}
          className="w-full text-xs bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white py-2 rounded-md transition-colors"
        >
          {loading === 'daily' ? '⏳ 更新中...' : '📥 日次更新'}
        </button>
        <button
          onClick={() => handleUpdate('crypto')}
          disabled={loading !== null}
          className="w-full text-xs bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 text-white py-2 rounded-md transition-colors"
        >
          {loading === 'crypto' ? '⏳ 取得中...' : '⚡ Crypto 1分足'}
        </button>
        {msg && (
          <p className="text-xs text-zinc-400 break-words leading-tight mt-1">{msg}</p>
        )}
      </div>
    </aside>
  )
}
