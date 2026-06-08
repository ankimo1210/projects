"use client";

import { useState } from "react";
import NeonShell from "@/components/layout/NeonShell";
import {
  solveHu,
  HuStreet,
  STREET_CARDS,
  HuRiverResponse,
  aggressiveGrid,
  RANK_LABELS,
} from "@/lib/hu-api";

// ---------------------------------------------------------------------------
// Card picker (river: exactly 5 cards)
// ---------------------------------------------------------------------------

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const SUITS = ["c", "d", "h", "s"];
const SUIT_SYMBOLS: Record<string, string> = { c: "♣", d: "♦", h: "♥", s: "♠" };
const SUIT_COLORS: Record<string, string> = {
  c: "text-zinc-300",
  d: "text-rose-400",
  h: "text-rose-400",
  s: "text-zinc-300",
};

// Positional action palette: check (zinc) → escalating bets → all-in.
const ACTION_PALETTE = ["#3f3f46", "#0284c7", "#7c3aed", "#dc2626", "#f59e0b"];

function CardPicker({
  selected,
  onToggle,
  maxCards,
}: {
  selected: string[];
  onToggle: (c: string) => void;
  maxCards: number;
}) {
  return (
    <div className="grid gap-0.5" style={{ gridTemplateColumns: "repeat(13, 1fr)" }}>
      {RANKS.map((r) =>
        SUITS.map((s) => {
          const c = `${r}${s}`;
          const isSelected = selected.includes(c);
          const isFull = !isSelected && selected.length >= maxCards;
          return (
            <button
              key={c}
              onClick={() => !isFull && onToggle(c)}
              disabled={isFull}
              title={c}
              className={`aspect-square rounded text-[9px] font-mono flex items-center justify-center transition-all
                ${isSelected ? "bg-cyan-500 text-black ring-1 ring-cyan-300" : ""}
                ${isFull ? "opacity-20 cursor-not-allowed bg-zinc-800" : ""}
                ${!isSelected && !isFull ? "bg-zinc-800 hover:bg-zinc-700 text-zinc-300" : ""}
              `}
            >
              <span className={isSelected ? "" : SUIT_COLORS[s]}>
                {r}
                {SUIT_SYMBOLS[s]}
              </span>
            </button>
          );
        }),
      )}
    </div>
  );
}

function BoardCard({ card, onClick }: { card: string; onClick?: () => void }) {
  const r = card[0],
    s = card[1];
  return (
    <button
      onClick={onClick}
      title="click to remove"
      className="w-9 h-12 bg-white/5 border border-cyan-500/30 rounded flex items-center justify-center text-base font-bold hover:border-rose-500/50 hover:bg-rose-500/10 transition-all"
      style={{ boxShadow: "0 0 8px rgba(34,211,238,0.15)" }}
    >
      <span className={SUIT_COLORS[s]}>
        {r}
        {SUIT_SYMBOLS[s]}
      </span>
    </button>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-zinc-500 tracking-widest">{label}</span>
        <span className="text-zinc-200 font-mono">
          {value}
          {unit ?? ""}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-0.5 accent-cyan-400 bg-zinc-700 rounded appearance-none cursor-pointer"
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Range heatmap (13×13, colored by aggressive frequency)
// ---------------------------------------------------------------------------

function RangeGrid({ resp }: { resp: HuRiverResponse }) {
  const grid = aggressiveGrid(resp);
  return (
    <div className="inline-grid gap-px" style={{ gridTemplateColumns: "repeat(13, 1fr)" }}>
      {grid.map((rowArr, i) =>
        rowArr.map((v, j) => {
          const hi = RANK_LABELS[Math.min(i, j)];
          const lo = RANK_LABELS[Math.max(i, j)];
          const label = i === j ? `${hi}${lo}` : i < j ? `${hi}${lo}s` : `${lo}${hi}o`;
          const alpha = v == null ? 0 : v;
          return (
            <div
              key={`${i}-${j}`}
              title={v == null ? `${label} —` : `${label}  ${(v * 100).toFixed(0)}% aggressive`}
              className="w-7 h-7 flex items-center justify-center text-[7px] font-mono rounded-sm border border-black/40"
              style={{
                background:
                  v == null
                    ? "#18181b"
                    : `rgba(220,38,38,${0.12 + 0.88 * alpha})`,
                color: alpha > 0.55 ? "#fff" : "#a1a1aa",
              }}
            >
              {label}
            </div>
          );
        }),
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const RIVER_BOARD = ["Ah", "Kd", "7s", "2c", "9h"];
const TURN_BOARD = ["Ah", "Kd", "7s", "2c"];

export default function HuPage() {
  const [street, setStreet] = useState<HuStreet>("river");
  const [board, setBoard] = useState<string[]>(RIVER_BOARD);
  const [pot, setPot] = useState(20);
  const [stack, setStack] = useState(90);
  const [iters, setIters] = useState(5000);
  const [solving, setSolving] = useState(false);
  const [result, setResult] = useState<HuRiverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const need = STREET_CARDS[street];

  function changeStreet(s: HuStreet) {
    setStreet(s);
    setBoard(s === "river" ? RIVER_BOARD : TURN_BOARD);
    setIters(s === "river" ? 5000 : 10000);
    setResult(null);
    setError(null);
  }

  function toggleCard(c: string) {
    setBoard((prev) => (prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]));
    setResult(null);
    setError(null);
  }

  async function solve() {
    if (board.length !== need || solving) return;
    setSolving(true);
    setResult(null);
    setError(null);
    try {
      const res = await solveHu(street, {
        board,
        pot_bb: pot,
        effective_stack_bb: stack,
        iterations: iters,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Solver error");
    } finally {
      setSolving(false);
    }
  }

  const canSolve = board.length === need && !solving;

  return (
    <NeonShell>
      <div className="flex h-full">
        {/* Left: board + params */}
        <aside className="w-72 border-r border-cyan-500/10 p-4 flex flex-col gap-4 overflow-y-auto">
          <div>
            <p className="text-[9px] tracking-widest text-cyan-500/40">EXACT HU GTO SOLVER</p>
            <p className="text-[9px] text-zinc-600 mt-1">
              Correct equilibrium with an exact exploitability number — not the
              single-street GPU approximation.
            </p>
          </div>

          {/* Street selector */}
          <div className="flex gap-1">
            {(["river", "turn-river"] as HuStreet[]).map((s) => (
              <button
                key={s}
                onClick={() => changeStreet(s)}
                className={`flex-1 py-1 text-[10px] tracking-widest border transition-all
                  ${street === s ? "border-cyan-400 text-cyan-300 bg-cyan-400/10" : "border-zinc-700 text-zinc-600 hover:border-zinc-500"}`}
              >
                {s === "river" ? "RIVER" : "TURN+RIVER"}
              </button>
            ))}
          </div>
          {street === "turn-river" && (
            <p className="text-[9px] text-amber-500/70 leading-relaxed">
              ⚠ Turn+river enumerates the river as a public chance node — a solve
              takes ~30-40 s at 10k iterations. Exploitability is always exact.
            </p>
          )}

          <div className="flex items-center gap-1.5 flex-wrap min-h-[3rem]">
            {board.map((c) => (
              <BoardCard key={c} card={c} onClick={() => toggleCard(c)} />
            ))}
            {Array(need - board.length)
              .fill(0)
              .map((_, i) => (
                <div
                  key={i}
                  className="w-9 h-12 border border-zinc-700 border-dashed rounded opacity-20"
                />
              ))}
          </div>
          <p className="text-[9px] text-zinc-600">
            {street === "river" ? "RIVER" : "TURN"} BOARD ({board.length}/{need})
          </p>

          <CardPicker selected={board} onToggle={toggleCard} maxCards={need} />

          <div className="space-y-3 pt-2">
            <SliderRow label="POT" value={pot} min={2} max={60} step={2} unit="bb" onChange={(v) => { setPot(v); setResult(null); }} />
            <SliderRow label="STACK" value={stack} min={10} max={200} step={5} unit="bb" onChange={(v) => { setStack(v); setResult(null); }} />
            <SliderRow label="ITERATIONS" value={iters} min={1000} max={20000} step={1000} onChange={(v) => { setIters(v); setResult(null); }} />
          </div>

          <button
            onClick={solve}
            disabled={!canSolve}
            className={`mt-2 py-2 text-xs tracking-widest border rounded-sm transition-all
              ${canSolve ? "border-cyan-400/60 text-cyan-300 bg-cyan-400/10 hover:bg-cyan-400/20" : "border-zinc-800 text-zinc-700 cursor-not-allowed"}`}
          >
            {solving ? "SOLVING…" : "SOLVE EQUILIBRIUM"}
          </button>
          {error && <p className="text-[10px] text-rose-400 break-words">{error}</p>}
        </aside>

        {/* Right: results */}
        <main className="flex-1 p-6 overflow-auto">
          {!result && !solving && (
            <div className="h-full flex items-center justify-center text-zinc-700 text-xs tracking-widest">
              PICK A {need}-CARD {street === "river" ? "RIVER" : "TURN"} BOARD → SOLVE
            </div>
          )}
          {solving && (
            <div className="h-full flex items-center justify-center text-cyan-500/60 text-xs animate-pulse tracking-widest">
              <span className="inline-block w-4 h-4 border border-cyan-500/60 border-t-cyan-400 rounded-full animate-spin mr-3" />
              SOLVING EXACT EQUILIBRIUM…
            </div>
          )}
          {result && (
            <div className="space-y-6 max-w-3xl">
              {/* Exploitability banner — the headline differentiator */}
              <div className="grid grid-cols-3 gap-3">
                <Stat
                  label="EXPLOITABILITY"
                  value={`${result.exploitability.toFixed(4)} bb`}
                  hint="exact best-response gap"
                  glow
                />
                <Stat label="GAME VALUE (SB)" value={`${result.game_value_sb >= 0 ? "+" : ""}${result.game_value_sb.toFixed(3)} bb`} hint="avg vs avg" />
                <Stat
                  label="SOLVE TIME"
                  value={`${result.elapsed_secs.toFixed(2)}s`}
                  hint={`${result.iterations} iters`}
                />
              </div>

              {/* Root (OOP) strategy bars */}
              <div>
                <p className="text-[10px] tracking-widest text-cyan-500/40 mb-2">
                  OOP (BB) ROOT STRATEGY
                </p>
                <div className="space-y-1.5">
                  {result.strategy.map((a, i) => (
                    <div key={a.action} className="flex items-center gap-2">
                      <span className="w-28 text-[10px] text-zinc-400 text-right">{a.action}</span>
                      <div className="flex-1 h-5 bg-zinc-900 rounded-sm overflow-hidden">
                        <div
                          className="h-full transition-all"
                          style={{
                            width: `${a.freq * 100}%`,
                            background: ACTION_PALETTE[i % ACTION_PALETTE.length],
                          }}
                        />
                      </div>
                      <span className="w-12 text-[10px] text-zinc-300 font-mono">
                        {(a.freq * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Range heatmap */}
              <div>
                <p className="text-[10px] tracking-widest text-cyan-500/40 mb-2">
                  OOP RANGE — AGGRESSIVE FREQUENCY (bet/raise %)
                </p>
                <RangeGrid resp={result} />
              </div>
            </div>
          )}
        </main>
      </div>
    </NeonShell>
  );
}

function Stat({
  label,
  value,
  hint,
  glow,
}: {
  label: string;
  value: string;
  hint?: string;
  glow?: boolean;
}) {
  return (
    <div
      className={`border rounded-sm p-3 ${glow ? "border-cyan-400/40 bg-cyan-400/5" : "border-zinc-800"}`}
      style={glow ? { boxShadow: "0 0 16px rgba(34,211,238,0.12)" } : undefined}
    >
      <p className="text-[9px] tracking-widest text-zinc-500">{label}</p>
      <p
        className="text-lg font-mono mt-1"
        style={glow ? { color: "#67e8f9", textShadow: "0 0 8px rgba(34,211,238,0.5)" } : { color: "#e4e4e7" }}
      >
        {value}
      </p>
      {hint && <p className="text-[8px] text-zinc-600 mt-0.5">{hint}</p>}
    </div>
  );
}
