import { useEffect, useRef } from "react";
import uPlot from "uplot";
import "uplot/dist/uPlot.min.css";
import type { TelemetryFrame } from "./types";

export interface Series {
  label: string;
  get: (f: TelemetryFrame) => number | null;
  color: string;
}

interface Props {
  title: string;
  series: Series[];
  frames: TelemetryFrame[];
  /** Bumped by the ring on each push; drives the uPlot data refresh. */
  version: number;
  height?: number;
}

/**
 * Thin uPlot wrapper: one x-axis (t_s) with N y-series. Rebuilds its data
 * from `frames` whenever `version` changes and resizes to its container.
 */
export function StripChart({ title, series, frames, version, height = 260 }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);

  useEffect(() => {
    if (!el.current) return;
    const opts: uPlot.Options = {
      title,
      width: el.current.clientWidth || 600,
      height,
      series: [
        {},
        ...series.map((s) => ({
          label: s.label,
          stroke: s.color,
          width: 1.5,
          spanGaps: false,
        })),
      ],
      axes: [
        { stroke: "#9aa", grid: { stroke: "#2a2f3a" } },
        { stroke: "#9aa", grid: { stroke: "#2a2f3a" } },
      ],
    };
    plot.current = new uPlot(opts, emptyData(series.length), el.current);
    const onResize = () =>
      plot.current?.setSize({
        width: el.current!.clientWidth || 600,
        height,
      });
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      plot.current?.destroy();
      plot.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, height, series.length]);

  useEffect(() => {
    if (!plot.current) return;
    const xs = frames.map((f) => f.t_s);
    const ys = series.map((s) => frames.map((f) => s.get(f)));
    plot.current.setData([xs, ...ys] as uPlot.AlignedData);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [version]);

  return <div ref={el} style={{ width: "100%", overflowX: "auto" }} />;
}

function emptyData(n: number): uPlot.AlignedData {
  return [[], ...Array.from({ length: n }, () => [])] as uPlot.AlignedData;
}
