"use client";

import { ComboStrategy, ACTION_COLORS, comboKey } from "@/lib/library-api";

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"] as const;

type CellType = "pair" | "suited" | "offsuit";

interface Cell {
  label: string;
  type: CellType;
}

const CELLS: Cell[][] = RANKS.map((r1, i) =>
  RANKS.map((r2, j) => ({
    label: i === j ? `${r1}${r2}` : i < j ? `${r1}${r2}s` : `${r2}${r1}o`,
    type:  (i === j ? "pair" : i < j ? "suited" : "offsuit") as CellType,
  }))
);

/** Build a label → {action: freq} map from combo strategies. */
function buildFreqMap(combos: ComboStrategy[]): Map<string, Record<string, number>> {
  const map = new Map<string, Record<string, number>>();
  for (const cs of combos) {
    const key = comboKey(cs.card_a, cs.card_b);
    if (!map.has(key)) map.set(key, {});
    const entry = map.get(key)!;
    entry[cs.action] = (entry[cs.action] ?? 0) + cs.freq;
  }
  // Normalize per combo
  for (const [, freqs] of map) {
    const total = Object.values(freqs).reduce((a, b) => a + b, 0);
    if (total > 0) {
      for (const k in freqs) freqs[k] /= total;
    }
  }
  return map;
}

/** Mix action colors by frequency to produce a CSS gradient or solid color. */
function mixColor(freqs: Record<string, number>): string {
  const entries = Object.entries(freqs)
    .filter(([, f]) => f > 0.01)
    .sort((a, b) => b[1] - a[1]);

  if (entries.length === 0) return "#18181b";
  if (entries.length === 1 || entries[0][1] > 0.95) {
    return ACTION_COLORS[entries[0][0]] ?? "#18181b";
  }

  // Multi-action: weighted CSS linear-gradient
  let pct = 0;
  const stops: string[] = [];
  for (const [action, freq] of entries) {
    const color = ACTION_COLORS[action] ?? "#18181b";
    stops.push(`${color} ${Math.round(pct)}%`);
    pct += freq * 100;
    stops.push(`${color} ${Math.round(pct)}%`);
  }
  return `linear-gradient(135deg, ${stops.join(", ")})`;
}

const BASE_COLORS: Record<CellType, string> = {
  pair:    "#3f2f00",
  suited:  "#0c2638",
  offsuit: "#1c1c1e",
};

interface RangeHeatmapProps {
  combos: ComboStrategy[];
  highlight?: string;
  onSelect?: (label: string) => void;
  compact?: boolean;
}

export function RangeHeatmap({ combos, highlight, onSelect, compact = false }: RangeHeatmapProps) {
  const freqMap = buildFreqMap(combos);
  const hasData = freqMap.size > 0;
  const sz = compact ? "6px" : "9px";

  return (
    <div
      className="grid gap-px"
      style={{ gridTemplateColumns: "repeat(13, 1fr)" }}
    >
      {CELLS.flat().map((cell) => {
        const freqs = freqMap.get(cell.label);
        const bg    = freqs ? mixColor(freqs) : BASE_COLORS[cell.type];
        const isHL  = cell.label === highlight;

        return (
          <div
            key={cell.label}
            title={cell.label}
            onClick={() => onSelect?.(cell.label)}
            className={`aspect-square flex items-center justify-center rounded-sm cursor-pointer transition-all duration-100
              ${isHL ? "ring-2 ring-white ring-inset" : ""}
              ${onSelect ? "hover:brightness-125" : ""}
              ${!hasData ? "opacity-30" : ""}
            `}
            style={{ background: bg, fontSize: sz }}
          >
            <span className="text-white/70 font-mono leading-none select-none">
              {cell.label.slice(0, 2)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** Legend for action colors */
export function ActionLegend({ actions }: { actions: string[] }) {
  const { ACTION_LABELS } = require("@/lib/library-api");
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {actions.map(a => (
        <div key={a} className="flex items-center gap-1.5 text-[10px]">
          <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: ACTION_COLORS[a] ?? "#555" }} />
          <span className="text-zinc-400">{ACTION_LABELS[a] ?? a}</span>
        </div>
      ))}
    </div>
  );
}
