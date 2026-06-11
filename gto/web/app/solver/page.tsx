"use client";

import { useState } from "react";
import NeonShell from "@/components/layout/NeonShell";
import { solveSpot, SolveResponse } from "@/lib/solver-api";
import { ACTION_COLORS, ACTION_LABELS } from "@/lib/library-api";
import CustomSolve from "./CustomSolve";

// ---------------------------------------------------------------------------
// Card picker
// ---------------------------------------------------------------------------

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"];
const SUITS = ["c","d","h","s"];
const SUIT_SYMBOLS: Record<string, string> = { c:"♣", d:"♦", h:"♥", s:"♠" };
const SUIT_COLORS:  Record<string, string> = { c:"text-zinc-300", d:"text-rose-400", h:"text-rose-400", s:"text-zinc-300" };

function CardPicker({
  selected, onToggle, maxCards,
}: { selected: string[]; onToggle: (c: string) => void; maxCards: number }) {
  return (
    <div className="grid gap-0.5" style={{ gridTemplateColumns: "repeat(13, 1fr)" }}>
      {RANKS.map(r =>
        SUITS.map(s => {
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
                ${isFull    ? "opacity-20 cursor-not-allowed bg-zinc-800" : ""}
                ${!isSelected && !isFull ? "bg-zinc-800 hover:bg-zinc-700 text-zinc-300" : ""}
              `}
            >
              <span className={isSelected ? "" : SUIT_COLORS[s]}>{r}{SUIT_SYMBOLS[s]}</span>
            </button>
          );
        })
      )}
    </div>
  );
}

function BoardCard({ card, onClick }: { card: string; onClick?: () => void }) {
  const r = card[0], s = card[1];
  return (
    <button
      onClick={onClick}
      title="click to remove"
      className="w-9 h-12 bg-white/5 border border-cyan-500/30 rounded flex items-center justify-center text-base font-bold hover:border-rose-500/50 hover:bg-rose-500/10 transition-all"
      style={{ boxShadow: "0 0 8px rgba(34,211,238,0.15)" }}
    >
      <span className={SUIT_COLORS[s]}>{r}{SUIT_SYMBOLS[s]}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------
function Spinner() {
  return (
    <div className="flex items-center gap-3 text-cyan-500/60 text-xs animate-pulse tracking-widest">
      <span className="inline-block w-4 h-4 border border-cyan-500/60 border-t-cyan-400 rounded-full animate-spin" />
      SOLVING…
    </div>
  );
}

// ---------------------------------------------------------------------------
// Slider input
// ---------------------------------------------------------------------------
function SliderRow({
  label, value, min, max, step, unit, onChange,
}: {
  label: string; value: number; min: number; max: number; step: number;
  unit?: string; onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-zinc-500 tracking-widest">{label}</span>
        <span className="text-zinc-200 font-mono">{value}{unit ?? ""}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full h-0.5 accent-cyan-400 bg-zinc-700 rounded appearance-none cursor-pointer"
      />
      <div className="flex justify-between text-[9px] text-zinc-700">
        <span>{min}{unit ?? ""}</span>
        <span>{max}{unit ?? ""}</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

type Street = "flop" | "turn" | "river";
const STREET_MAX: Record<Street, number> = { flop: 3, turn: 4, river: 5 };

export default function SolverPage() {
  const [street, setStreet]     = useState<Street>("flop");
  const [board, setBoard]       = useState<string[]>([]);
  const [pot, setPot]           = useState(6.5);
  const [stack, setStack]       = useState(97.0);
  const [iters, setIters]       = useState(300);
  const [maxBets, setMaxBets]   = useState(2);
  const [solving, setSolving]   = useState(false);
  const [result, setResult]     = useState<SolveResponse | null>(null);
  const [error, setError]       = useState<string | null>(null);

  const maxCards = STREET_MAX[street];

  function toggleCard(c: string) {
    setBoard(prev => prev.includes(c) ? prev.filter(x => x !== c) : [...prev, c]);
    setResult(null);
    setError(null);
  }

  function changeStreet(s: Street) {
    setStreet(s);
    setBoard(prev => prev.slice(0, STREET_MAX[s]));
    setResult(null);
    setError(null);
  }

  async function solve() {
    if (board.length < 3 || solving) return;
    setSolving(true);
    setResult(null);
    setError(null);
    try {
      const res = await solveSpot({
        pot_bb: pot,
        effective_stack_bb: stack,
        board,
        iterations: iters,
        max_bets: maxBets,
      });
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Solver error");
    } finally {
      setSolving(false);
    }
  }

  const canSolve = board.length >= 3 && !solving;

  return (
    <NeonShell>
      <div className="flex h-full">

        {/* Left: board picker */}
        <aside className="w-72 border-r border-cyan-500/10 p-4 flex flex-col gap-4 overflow-y-auto">
          <p className="text-[9px] tracking-widest text-cyan-500/40">BOARD</p>

          {/* Street selector */}
          <div className="flex gap-1">
            {(["flop","turn","river"] as Street[]).map(s => (
              <button key={s} onClick={() => changeStreet(s)}
                className={`flex-1 py-1 text-[10px] tracking-widest border transition-all
                  ${street === s ? "border-cyan-400 text-cyan-300 bg-cyan-400/10" : "border-zinc-700 text-zinc-600 hover:border-zinc-500"}`}>
                {s.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Selected cards */}
          <div className="flex items-center gap-1.5 flex-wrap min-h-[3rem]">
            {board.map(c => <BoardCard key={c} card={c} onClick={() => toggleCard(c)} />)}
            {Array(maxCards - board.length).fill(0).map((_, i) => (
              <div key={i} className="w-9 h-12 border border-zinc-700 border-dashed rounded opacity-20" />
            ))}
          </div>

          <p className="text-[9px] text-zinc-600">SELECT {maxCards} CARDS ({board.length}/{maxCards})</p>

          <CardPicker selected={board} onToggle={toggleCard} maxCards={maxCards} />

          {board.length > 0 && (
            <button onClick={() => { setBoard([]); setResult(null); setError(null); }}
              className="text-[10px] text-zinc-600 hover:text-rose-400 tracking-widest text-left">
              CLEAR BOARD
            </button>
          )}
        </aside>

        {/* Center: settings + results */}
        <main className="flex-1 flex flex-col p-6 gap-6 overflow-auto">
          <p className="text-[9px] tracking-widest text-cyan-500/40">SPOT CONFIGURATION</p>

          {/* Settings */}
          <div className="max-w-sm space-y-5">
            <SliderRow label="POT"             value={pot}    min={2}   max={30}  step={0.5} unit="bb" onChange={setPot} />
            <SliderRow label="EFF. STACK"      value={stack}  min={10}  max={200} step={1}   unit="bb" onChange={setStack} />
            <SliderRow label="ITERATIONS"      value={iters}  min={50}  max={1000} step={50}          onChange={setIters} />
            <SliderRow label="MAX BETS/PLAYER" value={maxBets} min={1}  max={4}   step={1}            onChange={setMaxBets} />
          </div>

          {/* Solve button */}
          <button
            onClick={solve}
            disabled={!canSolve}
            className={`self-start px-8 py-2.5 text-xs tracking-[0.3em] border transition-all
              ${canSolve
                ? "border-cyan-400 text-cyan-300 hover:bg-cyan-400/10"
                : "border-zinc-700 text-zinc-600 cursor-not-allowed"}`}
            style={canSolve ? { boxShadow: "0 0 12px rgba(34,211,238,0.3)" } : undefined}
          >
            SOLVE →
          </button>

          {board.length < 3 && (
            <p className="text-[10px] text-zinc-700 tracking-widest">Select at least 3 board cards</p>
          )}

          {solving && <Spinner />}

          {error && (
            <div className="bg-rose-900/20 border border-rose-500/30 rounded-xl p-4 text-xs text-rose-400 max-w-md">
              {error}
            </div>
          )}

          {result && (
            <div className="space-y-4 max-w-md">
              <div className="flex items-center gap-4">
                <p className="text-[9px] tracking-widest text-zinc-600">STRATEGY</p>
                <span className="text-[9px] text-zinc-700">
                  {result.iterations} iters · {result.backend.toUpperCase()} ·
                  exploitability {result.exploitability.toExponential(2)}
                </span>
              </div>

              <div className="space-y-2.5">
                {result.strategy
                  .slice()
                  .sort((a, b) => b.freq - a.freq)
                  .map(a => (
                    <div key={a.action}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-zinc-400">{ACTION_LABELS[a.action] ?? a.action}</span>
                        <span className="font-mono text-zinc-200">{(a.freq * 100).toFixed(1)}%</span>
                      </div>
                      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{ width: `${a.freq * 100}%`, background: ACTION_COLORS[a.action] ?? "#555" }}
                        />
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Equilibrium custom solve (gto-hu, exact exploitability) — distinct
              from the legacy gto-cuda single-street approximation above. */}
          <div className="border-t border-cyan-500/10 pt-2">
            <CustomSolve />
          </div>
        </main>

        {/* Right: quick reference */}
        <aside className="w-52 border-l border-cyan-500/10 p-4 flex flex-col gap-5">
          <p className="text-[9px] tracking-widest text-cyan-500/40">QUICK REF</p>

          <div className="space-y-3 text-[10px] text-zinc-600">
            <div>
              <p className="text-zinc-500 mb-1">TYPICAL POTS</p>
              {[
                ["BTN vs BB", "6.5bb"],
                ["CO vs BB",  "7.0bb"],
                ["SB vs BB",  "5.0bb"],
              ].map(([pos, p]) => (
                <div key={pos} className="flex justify-between py-0.5">
                  <span>{pos}</span>
                  <button
                    onClick={() => setPot(parseFloat(p))}
                    className="text-cyan-600 hover:text-cyan-400 transition-colors"
                  >
                    {p}
                  </button>
                </div>
              ))}
            </div>

            <div>
              <p className="text-zinc-500 mb-1">TYPICAL STACKS</p>
              {[["100bb", "97.0"], ["50bb", "47.0"], ["200bb", "197.0"]].map(([label, v]) => (
                <div key={label} className="flex justify-between py-0.5">
                  <span>{label}</span>
                  <button
                    onClick={() => setStack(parseFloat(v))}
                    className="text-cyan-600 hover:text-cyan-400 transition-colors"
                  >
                    {v}bb
                  </button>
                </div>
              ))}
            </div>

            <div className="border-t border-zinc-800 pt-3">
              <p className="text-zinc-500 mb-1">ALGORITHM</p>
              <p>Discounted CFR</p>
              <p>α=1.5, β=0</p>
              <p>GPU: RTX 5080</p>
            </div>
          </div>

          {result && (
            <div className="border-t border-zinc-800 pt-3 space-y-1 mt-auto text-[10px]">
              <p className="text-zinc-600 tracking-widest">LAST SOLVE</p>
              <p className="text-zinc-400">{board.join(" ")}</p>
              <p className="text-zinc-500">{result.iterations} iter</p>
              <p className={result.backend === "gpu" ? "text-cyan-400" : "text-zinc-500"}>
                {result.backend.toUpperCase()}
              </p>
            </div>
          )}
        </aside>

      </div>
    </NeonShell>
  );
}
