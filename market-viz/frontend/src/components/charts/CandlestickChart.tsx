'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, CandlestickSeries, HistogramSeries, LineSeries } from 'lightweight-charts'
import type { OHLCVBar } from '@/lib/types'

interface Props {
  bars: OHLCVBar[]
  ticker: string
  maWindows?: number[]
  showVolume?: boolean
  height?: number
}

function computeMA(bars: OHLCVBar[], window: number): { time: string; value: number }[] {
  const result: { time: string; value: number }[] = []
  for (let i = window - 1; i < bars.length; i++) {
    const slice = bars.slice(i - window + 1, i + 1)
    const valid = slice.filter(b => b.close != null)
    if (valid.length === 0) continue
    const avg = valid.reduce((s, b) => s + b.close!, 0) / valid.length
    result.push({ time: bars[i].timestamp.slice(0, 10), value: avg })
  }
  return result
}

const MA_COLORS = ['#fbbf24', '#60a5fa', '#f97316']

export default function CandlestickChart({
  bars, ticker, maWindows = [], showVolume = true, height = 480,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current || bars.length === 0) return

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#09090b' }, textColor: '#a1a1aa' },
      grid: { vertLines: { color: '#27272a' }, horzLines: { color: '#27272a' } },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: '#3f3f46' },
      timeScale: { borderColor: '#3f3f46', timeVisible: true },
      width: containerRef.current.clientWidth,
      height,
    })

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981', downColor: '#ef4444',
      borderUpColor: '#10b981', borderDownColor: '#ef4444',
      wickUpColor: '#10b981', wickDownColor: '#ef4444',
    })
    candle.setData(bars.filter(b => b.open != null && b.high != null && b.low != null && b.close != null).map(b => ({
      time: b.timestamp.slice(0, 10),
      open: b.open!,
      high: b.high!,
      low: b.low!,
      close: b.close!,
    })))

    maWindows.forEach((w, i) => {
      const line = chart.addSeries(LineSeries, {
        color: MA_COLORS[i % MA_COLORS.length],
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: true,
        title: `MA${w}`,
      })
      line.setData(computeMA(bars, w))
    })

    if (showVolume) {
      const vol = chart.addSeries(HistogramSeries, {
        color: '#3f3f46',
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
      })
      chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })
      vol.setData(bars.filter(b => b.volume != null).map(b => ({
        time: b.timestamp.slice(0, 10),
        value: b.volume!,
        color: (b.close != null && b.open != null && b.close >= b.open) ? '#10b98144' : '#ef444444',
      })))
    }

    chart.timeScale().fitContent()

    const ro = new ResizeObserver(() => {
      if (containerRef.current)
        chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { chart.remove(); ro.disconnect() }
  }, [bars, maWindows, showVolume, height])

  return <div ref={containerRef} className="w-full" style={{ height }} />
}
