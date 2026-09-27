'use client'

interface Props {
  tickers: string[]
  matrix: (number | null)[][]
}

function cellColor(v: number | null): string {
  if (v == null) return 'bg-zinc-800'
  if (v >= 0.8)  return 'bg-red-700'
  if (v >= 0.5)  return 'bg-red-500'
  if (v >= 0.2)  return 'bg-red-400/50'
  if (v <= -0.8) return 'bg-blue-700'
  if (v <= -0.5) return 'bg-blue-500'
  if (v <= -0.2) return 'bg-blue-400/50'
  return 'bg-zinc-700'
}

export default function HeatmapChart({ tickers, matrix }: Props) {
  if (!tickers.length) return <p className="text-zinc-500 text-sm">データなし</p>

  const shortLabel = (t: string) => t.replace('-USD', '').replace('=X', '').replace('^', '')

  return (
    <div className="overflow-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="w-16" />
            {tickers.map(t => (
              <th key={t} className="p-0.5 text-zinc-400 font-normal rotate-45 h-16 align-bottom">
                <span className="block -rotate-45 origin-bottom-left whitespace-nowrap">{shortLabel(t)}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickers.map((rowTicker, ri) => (
            <tr key={rowTicker}>
              <td className="pr-2 text-zinc-400 text-right whitespace-nowrap">{shortLabel(rowTicker)}</td>
              {matrix[ri]?.map((v, ci) => (
                <td
                  key={ci}
                  className={`w-8 h-8 text-center ${cellColor(v)}`}
                  title={`${shortLabel(rowTicker)} / ${shortLabel(tickers[ci])}: ${v?.toFixed(2) ?? '—'}`}
                >
                  <span className="text-white/80">{v != null ? v.toFixed(2) : ''}</span>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
