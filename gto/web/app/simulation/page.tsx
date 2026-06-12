"use client";

import { useState } from "react";
import NeonShell from "@/components/layout/NeonShell";
import { runSimulation, SimResponse, BBHand } from "@/lib/simulation-api";
import { ACTION_COLORS, ACTION_LABELS } from "@/lib/library-api";

// ---------------------------------------------------------------------------
// Card picker (board selection)
// ---------------------------------------------------------------------------

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"];
const SUITS = ["c","d","h","s"];
const SUIT_SYM: Record<string,string> = { c:"♣", d:"♦", h:"♥", s:"♠" };
const SUIT_CLR: Record<string,string> = { c:"text-zinc-300", d:"text-rose-400", h:"text-rose-400", s:"text-zinc-300" };

function MiniCardPicker({ selected, onToggle }: { selected: string[]; onToggle: (c:string)=>void }) {
  return (
    <div className="grid gap-0.5" style={{ gridTemplateColumns:"repeat(13,1fr)" }}>
      {RANKS.map(r => SUITS.map(s => {
        const c = `${r}${s}`;
        const sel = selected.includes(c);
        const full = !sel && selected.length >= 3;
        return (
          <button key={c} onClick={() => !full && onToggle(c)} disabled={full} title={c}
            className={`aspect-square rounded text-[8px] font-mono flex items-center justify-center
              ${sel  ? "bg-cyan-500 text-black" : ""}
              ${full ? "opacity-20 cursor-not-allowed bg-zinc-800" : ""}
              ${!sel && !full ? "bg-zinc-800 hover:bg-zinc-700 text-zinc-300" : ""}`}>
            <span className={sel ? "" : SUIT_CLR[s]}>{r}</span>
          </button>
        );
      }))}
    </div>
  );
}

function BoardChip({ card, onRemove }: { card:string; onRemove:()=>void }) {
  const r = card[0], s = card[1];
  return (
    <button onClick={onRemove}
      className="px-2 py-1 border border-cyan-500/30 rounded text-sm font-bold hover:border-rose-500/50 hover:bg-rose-500/10 transition-all"
      style={{ boxShadow:"0 0 6px rgba(34,211,238,0.1)" }}>
      <span className={SUIT_CLR[s]}>{r}{SUIT_SYM[s]}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Frequency bar
// ---------------------------------------------------------------------------

function FreqBar({ label, value, color }: { label:string; value:number; color:string }) {
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-zinc-400">{label}</span>
        <span className="font-mono text-zinc-200">{(value*100).toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width:`${value*100}%`, background:color }} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// BB range heatmap (13×13 grid colored by call%)
// ---------------------------------------------------------------------------

const HAND_RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"];

function bbHandKey(r1: string, r2: string, i: number, j: number): string {
  if (i === j) return `${r1}${r2}`;
  if (i < j) return `${r1}${r2}s`;
  return `${r2}${r1}o`;
}

function callColor(pct: number): string {
  // 0% = dark, 100% = bright cyan
  const a = pct / 100;
  const r = Math.round(10 + 34 * a);
  const g = Math.round(15 + 211 * a);
  const b = Math.round(20 + 238 * a);
  return `rgb(${r},${g},${b})`;
}

function BBRangeGrid({ hands }: { hands: BBHand[] }) {
  const lookup: Record<string, BBHand> = {};
  for (const h of hands) lookup[h.hand] = h;

  return (
    <div className="grid gap-px" style={{ gridTemplateColumns:"repeat(13,1fr)" }}>
      {HAND_RANKS.map((r1, i) =>
        HAND_RANKS.map((r2, j) => {
          const label = bbHandKey(r1, r2, i, j);
          const h     = lookup[label];
          const callPct = h?.call_freq ?? 0;
          const bg    = callPct > 0 ? callColor(callPct) : "transparent";
          return (
            <div key={label} title={`${label}\nCall: ${callPct}%\nFold: ${h?.fold_freq ?? 100}%\n3Bet: ${h?.threebet_freq ?? 0}%`}
              className="aspect-square rounded-sm flex items-center justify-center text-[6px] font-mono"
              style={{ background: bg, color: callPct > 50 ? "#000" : "#666" }}>
              {label.slice(0,2)}
            </div>
          );
        })
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Spinner
// ---------------------------------------------------------------------------
function Spinner() {
  return (
    <div className="flex items-center gap-2 text-xs text-cyan-500/60 animate-pulse tracking-widest">
      <span className="inline-block w-3 h-3 border border-cyan-500/60 border-t-cyan-400 rounded-full animate-spin" />
      SOLVING…
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const POSITIONS = ["BTN","CO","SB","HJ","UTG"];
const FLOP_POTS: Record<string,number> = { BTN:6.5, CO:7.0, SB:5.0, HJ:7.0, UTG:7.0 };

export default function SimulationPage() {
  const [pos, setPos]       = useState("BTN");
  const [board, setBoard]   = useState<string[]>([]);
  const [iters, setIters]   = useState(300);
  const [result, setResult] = useState<SimResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);

  function toggleCard(c: string) {
    setBoard(prev => prev.includes(c) ? prev.filter(x => x !== c) : prev.length < 3 ? [...prev, c] : prev);
  }

  async function run() {
    if (loading) return;
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const r = await runSimulation({ position: pos, board, iterations: iters });
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }

  const rightSlot = (
    <>
      <div className="flex gap-1">
        {POSITIONS.map(p => (
          <button key={p} onClick={() => { setPos(p); setResult(null); }}
            className={`px-2 py-0.5 text-xs tracking-widest border transition-all
              ${pos === p ? "border-cyan-400 text-cyan-300 bg-cyan-400/10" : "border-zinc-700 text-zinc-500 hover:border-zinc-500"}`}>
            {p}
          </button>
        ))}
      </div>
      <span className="text-zinc-600">vs BB · 100bb</span>
    </>
  );

  return (
    <NeonShell rightSlot={rightSlot}>
      <div className="flex h-full">

        {/* Left: controls */}
        <aside className="w-72 border-r border-cyan-500/10 p-4 flex flex-col gap-4 overflow-y-auto">
          <p className="text-[9px] tracking-widest text-cyan-500/40">SIMULATION</p>

          {/* Board (optional) */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[9px] text-zinc-600 tracking-widest">FLOP (optional)</p>
              <button onClick={() => setShowPicker(p => !p)}
                className="text-[9px] text-zinc-600 hover:text-cyan-400 tracking-widest">
                {showPicker ? "CLOSE" : "SELECT"}
              </button>
            </div>
            <div className="flex items-center gap-1.5 min-h-[2.5rem]">
              {board.map(c => <BoardChip key={c} card={c} onRemove={() => setBoard(b => b.filter(x => x !== c))} />)}
              {board.length === 0 && (
                <span className="text-[10px] text-zinc-700">preflop only</span>
              )}
              {board.length > 0 && (
                <button onClick={() => setBoard([])}
                  className="text-[9px] text-zinc-700 hover:text-rose-400 ml-1">CLEAR</button>
              )}
            </div>
            {showPicker && (
              <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-lg p-2">
                <p className="text-[8px] text-zinc-600 mb-1.5">{board.length}/3 selected</p>
                <MiniCardPicker selected={board} onToggle={c => {
                  toggleCard(c);
                  if (board.length === 2 && !board.includes(c)) setShowPicker(false);
                }} />
              </div>
            )}
          </div>

          {/* Iterations */}
          <div className="space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-zinc-500 tracking-widest">ITERATIONS</span>
              <span className="text-zinc-200 font-mono">{iters}</span>
            </div>
            <input type="range" min={50} max={500} step={50} value={iters}
              onChange={e => setIters(Number(e.target.value))}
              className="w-full h-0.5 accent-cyan-400 bg-zinc-700 rounded cursor-pointer" />
          </div>

          {/* Run */}
          <button onClick={run} disabled={loading}
            className={`py-2 text-xs tracking-[0.3em] border transition-all
              ${!loading
                ? "border-cyan-400 text-cyan-300 hover:bg-cyan-400/10"
                : "border-zinc-700 text-zinc-600 cursor-not-allowed"}`}
            style={!loading ? { boxShadow:"0 0 10px rgba(34,211,238,0.25)" } : undefined}>
            {loading ? "SOLVING…" : board.length === 3 ? "RUN FULL SIMULATION →" : "CALC FOLD EQUITY →"}
          </button>

          {loading && <Spinner />}
          {error && (
            <div className="bg-rose-900/20 border border-rose-500/30 rounded-lg p-3 text-[10px] text-rose-400">
              {error}
            </div>
          )}

          {/* Quick-ref pot sizes */}
          <div className="border-t border-zinc-800 pt-3 space-y-1 text-[10px] text-zinc-600 mt-auto">
            <p className="text-zinc-500 tracking-widest">TYPICAL POTS</p>
            {Object.entries(FLOP_POTS).map(([p, v]) => (
              <div key={p} className="flex justify-between">
                <span>{p} vs BB</span><span className="text-zinc-500">{v}bb</span>
              </div>
            ))}
          </div>
        </aside>

        {/* Center: results */}
        <main className="flex-1 flex flex-col p-6 gap-6 overflow-auto">
          {!result && !loading && (
            <div className="flex-1 flex items-center justify-center">
              <p className="text-zinc-700 text-xs tracking-widest">
                Select position → Run simulation
              </p>
            </div>
          )}

          {result && (
            <>
              {/* Preflop outcome */}
              <div className="space-y-1">
                <p className="text-[9px] tracking-widest text-cyan-500/40">
                  PREFLOP — {result.position} OPEN vs BB
                </p>
                <div className="max-w-sm space-y-2.5 pt-1">
                  <FreqBar label="BB FOLDS"  value={result.fold_equity}  color="#f43f5e" />
                  <FreqBar label="BB CALLS"  value={result.call_freq}    color="#22d3ee" />
                  <FreqBar label="BB 3-BETS" value={result.threebet_freq} color="#c084fc" />
                </div>

                {/* Summary chips */}
                <div className="flex gap-3 pt-2 text-xs">
                  <span className="text-zinc-500">Fold equity:
                    <span className="ml-1 text-rose-400 font-bold">
                      {(result.fold_equity*100).toFixed(1)}%
                    </span>
                  </span>
                  <span className="text-zinc-500">Immediate EV:
                    <span className="ml-1 text-cyan-300 font-bold">
                      +{(result.fold_equity * 1.5).toFixed(2)}bb
                    </span>
                    <span className="text-zinc-700 ml-1">(vs 1.5bb pot)</span>
                  </span>
                </div>
              </div>

              {/* Postflop strategy */}
              {result.postflop && (
                <div className="space-y-3 border-t border-zinc-800 pt-4">
                  <p className="text-[9px] tracking-widest text-cyan-500/40">
                    POSTFLOP — {board.join(" ")} · IP ranges · {result.postflop.backend.toUpperCase()}
                    {result.postflop.equilibrium_claim ? (
                      <span className="ml-2 px-1.5 py-0.5 border border-cyan-500/40 text-cyan-400">EQUILIBRIUM</span>
                    ) : (
                      <span className="ml-2 px-1.5 py-0.5 border border-amber-500/40 text-amber-400">
                        APPROXIMATION — single-street preview
                      </span>
                    )}
                  </p>
                  <div className="max-w-sm space-y-2.5">
                    {result.postflop.strategy
                      .slice().sort((a,b) => b.freq - a.freq)
                      .map(a => (
                        <div key={a.action}>
                          <div className="flex justify-between text-xs mb-1">
                            <span className="text-zinc-400">{ACTION_LABELS[a.action] ?? a.action}</span>
                            <span className="font-mono text-zinc-200">{(a.freq*100).toFixed(1)}%</span>
                          </div>
                          <div className="h-2 bg-zinc-800 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{ width:`${a.freq*100}%`, background: ACTION_COLORS[a.action] ?? "#555" }} />
                          </div>
                        </div>
                      ))}
                  </div>
                  <p className="text-[9px] text-zinc-700">
                    exploit: {result.postflop.exploitability.toExponential(2)} · {result.postflop.iterations} iter
                  </p>
                </div>
              )}
            </>
          )}
        </main>

        {/* Right: BB call range grid */}
        <aside className="w-64 border-l border-cyan-500/10 p-3 flex flex-col gap-3">
          <p className="text-[9px] tracking-widest text-cyan-500/40">BB DEFENSE RANGE</p>

          {result ? (
            <>
              <BBRangeGrid hands={result.bb_hands} />
              <div className="flex items-center gap-2 text-[8px] mt-1">
                <span className="text-zinc-700">FOLD</span>
                <div className="flex-1 h-1.5 rounded" style={{
                  background:"linear-gradient(to right, rgb(10,15,20), rgb(34,211,238))"
                }} />
                <span className="text-cyan-400">CALL</span>
              </div>
              <p className="text-[9px] text-zinc-700 leading-relaxed mt-1">
                {result.bb_hands.filter(h=>h.call_freq>0).length} hands in BB call range
              </p>

              {/* Top 10 call hands */}
              <div className="border-t border-zinc-800 pt-2 space-y-0.5">
                <p className="text-[8px] text-zinc-600 tracking-widest mb-1">TOP CALLS</p>
                {result.bb_hands
                  .filter(h => h.call_freq > 0)
                  .slice(0, 10)
                  .map(h => (
                    <div key={h.hand} className="flex justify-between text-[9px]">
                      <span className="text-zinc-400 font-mono">{h.hand}</span>
                      <span className="text-cyan-400">{h.call_freq}%</span>
                    </div>
                  ))}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-zinc-700 text-[10px] text-center">
              Run simulation to see BB&apos;s defense range
            </div>
          )}
        </aside>

      </div>
    </NeonShell>
  );
}
