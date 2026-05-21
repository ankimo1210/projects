'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, LineSeries } from 'lightweight-charts'

interface DataPoint { time: string; value: number }
interface Series { name: string; data: DataPoint[]; color?: string }

interface Props {
  series: Series[]
  height?: number
  formatValue?: (v: number) => string
}

const COLORS = ['#10b981', '#60a5fa', '#fbbf24', '#f97316', '#a78bfa']

export default function LineChart({ series, height = 280, formatValue }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || series.length === 0) return

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#09090b' }, textColor: '#a1a1aa' },
      grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
      rightPriceScale: { borderColor: '#3f3f46' },
      timeScale: { borderColor: '#3f3f46', timeVisible: true },
      width: containerRef.current.clientWidth,
      height,
    })

    series.forEach((s, i) => {
      const line = chart.addSeries(LineSeries, {
        color: s.color ?? COLORS[i % COLORS.length],
        lineWidth: 2,
        title: s.name,
        priceLineVisible: false,
        lastValueVisible: true,
      })
      line.setData(s.data)
    })

    chart.timeScale().fitContent()

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { chart.remove(); ro.disconnect() }
  }, [series, height])

  return <div ref={containerRef} className="w-full" style={{ height }} />
}
