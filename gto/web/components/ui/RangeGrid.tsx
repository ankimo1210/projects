"use client";

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"] as const;

type CellType = "suited" | "offsuit" | "pair";

interface Cell {
  label: string;
  type: CellType;
  rank1: string;
  rank2: string;
}

function buildCells(): Cell[][] {
  return RANKS.map((r1, i) =>
    RANKS.map((r2, j) => {
      if (i === j) return { label: `${r1}${r2}`, type: "pair" as CellType, rank1: r1, rank2: r2 };
      if (i < j) return { label: `${r1}${r2}s`, type: "suited" as CellType, rank1: r1, rank2: r2 };
      return { label: `${r2}${r1}o`, type: "offsuit" as CellType, rank1: r2, rank2: r1 };
    })
  );
}

const CELLS = buildCells();

const cellBase =
  "flex items-center justify-center text-[10px] font-mono border border-zinc-700 cursor-pointer select-none rounded-sm transition-colors";

const cellColors: Record<CellType, string> = {
  pair: "bg-amber-600 hover:bg-amber-500 text-white",
  suited: "bg-sky-700 hover:bg-sky-600 text-white",
  offsuit: "bg-zinc-700 hover:bg-zinc-600 text-zinc-200",
};

interface RangeGridProps {
  selected?: Set<string>;
  onToggle?: (label: string) => void;
  title?: string;
}

export function RangeGrid({ selected, onToggle, title }: RangeGridProps) {
  return (
    <div>
      {title && <p className="text-sm text-zinc-400 mb-1">{title}</p>}
      <div className="grid grid-cols-13 gap-px" style={{ display: "grid", gridTemplateColumns: "repeat(13, minmax(0, 1fr))", gap: "1px" }}>
        {CELLS.flat().map((cell) => {
          const isSelected = selected?.has(cell.label);
          return (
            <div
              key={cell.label}
              className={`${cellBase} ${cellColors[cell.type]} ${isSelected ? "ring-2 ring-white" : ""} aspect-square`}
              onClick={() => onToggle?.(cell.label)}
              title={cell.label}
            >
              {cell.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}
