export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || isNaN(v)) return '—'
  return (v * 100).toFixed(digits) + '%'
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null || isNaN(v)) return '—'
  return v.toFixed(digits)
}

export function fmtPrice(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return '—'
  return v.toLocaleString('en-US', { maximumFractionDigits: 4 })
}

export function signalColor(signal: string): string {
  switch (signal) {
    case 'Overbought': return 'text-orange-400 font-bold'
    case 'Oversold':   return 'text-blue-400 font-bold'
    case 'Watch-High': return 'text-yellow-300'
    case 'Watch-Low':  return 'text-yellow-300'
    default:           return 'text-zinc-400'
  }
}

export function retColor(v: number | null | undefined): string {
  if (v == null) return ''
  return v >= 0 ? 'text-emerald-400' : 'text-red-400'
}

export function zscoreColor(v: number | null | undefined): string {
  if (v == null) return ''
  if (Math.abs(v) >= 2) return 'text-orange-400 font-bold'
  if (Math.abs(v) >= 1.5) return 'text-yellow-300'
  return ''
}
