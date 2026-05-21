"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchFlopSolution, fetchComboStrategies,
  SpotStrategy, ComboStrategy,
  ACTION_COLORS, ACTION_LABELS, comboKey, cardFromIndex,
} from "@/lib/library-api";
import { RangeHeatmap, ActionLegend } from "@/components/ui/RangeHeatmap";
import NeonShell from "@/components/layout/NeonShell";

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"];
const SUITS = ["c","d","h","s"];
const SUIT_SYMBOLS: Record<string, string> = { c:"♣", d:"♦", h:"♥", s:"♠" };
const SUIT_COLORS:  Record<string, string> = { c:"text-zinc-300", d:"text-rose-400", h:"text-rose-400", s:"text-zinc-300" };

const POSITIONS = ["BTN","CO","SB","HJ","UTG"];

// Board card picker
function CardPicker({
  selected, dead, onToggle,
}: { selected: string[]; dead: string[]; onToggle: (c: string) => void }) {
  return (
    <div className="grid gap-0.5" style={{ gridTemplateColumns: "repeat(13, 1fr)" }}>
      {RANKS.map(r =>
        SUITS.map(s => {
          const c = `${r}${s}`;
          const isSelected = selected.includes(c);
          const isDead     = dead.includes(c);
          return (
            <button
              key={c}
              onClick={() => !isDead && onToggle(c)}
              disabled={isDead}
              className={`aspect-square rounded text-[9px] font-mono flex items-center justify-center transition-all
                ${isSelected  ? "bg-cyan-500 text-black ring-1 ring-cyan-300" : ""}
                ${isDead      ? "opacity-20 cursor-not-allowed bg-zinc-800" : ""}
                ${!isSelected && !isDead ? "bg-zinc-800 hover:bg-zinc-700 text-zinc-300" : ""}
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

// Card display
function BoardCard({ card }: { card: string }) {
  const r = card[0], s = card[1];
  return (
    <div className="w-9 h-12 bg-white/5 border border-cyan-500/30 rounded flex items-center justify-center text-base font-bold"
      style={{ boxShadow: "0 0 8px rgba(34,211,238,0.15)" }}>
      <span className={SUIT_COLORS[s]}>{r}{SUIT_SYMBOLS[s]}</span>
    </div>
  );
}

function LibraryContent() {
  const searchParams = useSearchParams();
  const initBoard = searchParams.get("board") ?? "";
  const initPos   = searchParams.get("position") ?? "BTN";

  const [pos, setPos]            = useState(initPos);
  const [boardCards, setBoardCards] = useState<string[]>(
    initBoard.length === 6
      ? [initBoard.slice(0,2), initBoard.slice(2,4), initBoard.slice(4,6)]
      : []
  );
  const [solution, setSolution]  = useState<SpotStrategy | null>(null);
  const [combos, setCombos]      = useState<ComboStrategy[]>([]);
  const [selectedCombo, setSelectedCombo] = useState<string | null>(null);
  const [loading, setLoading]    = useState(false);
  const [error, setError]        = useState<string | null>(null);
  const [showPicker, setShowPicker] = useState(false);

  const fetchSolution = useCallback(async () => {
    if (boardCards.length !== 3) return;
    setLoading(true); setError(null); setSolution(null); setCombos([]);
    try {
      const board = boardCards.join("");
      const [sol, cms] = await Promise.all([
        fetchFlopSolution(board, pos),
        fetchComboStrategies(board, pos),
      ]);
      if (!sol) {
        setError(`No solution found for ${pos} vs BB — ${board}. Run batch computation or try a different spot.`);
      } else {
        setSolution(sol);
        setCombos(cms);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [boardCards, pos]);

  useEffect(() => { if (boardCards.length === 3) fetchSolution(); }, [fetchSolution]);

  function toggleCard(c: string) {
    setBoardCards(prev =>
      prev.includes(c) ? prev.filter(x => x !== c)
        : prev.length < 3 ? [...prev, c] : prev
    );
    setSelectedCombo(null);
  }

  const actions = solution ? [...new Set(solution.strategy.map(a => a.action))] : [];

  // Selected combo detail
  const comboDetail = selectedCombo
    ? combos.filter(cs => comboKey(cs.card_a, cs.card_b) === selectedCombo)
    : [];
  const comboFreqs = comboDetail.reduce((acc, cs) => {
    acc[cs.action] = (acc[cs.action] ?? 0) + cs.freq;
    return acc;
  }, {} as Record<string, number>);

  const rightSlot = (
    <>
      <div className="flex gap-1">
        {POSITIONS.map(p => (
          <button key={p} onClick={() => setPos(p)}
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
        {/* Left: range heatmap */}
        <div className="w-64 border-r border-cyan-500/10 p-3 flex flex-col gap-3">
          <p className="text-[9px] tracking-widest text-cyan-500/40">RANGE HEATMAP</p>
          <RangeHeatmap
            combos={combos}
            highlight={selectedCombo ?? undefined}
            onSelect={setSelectedCombo}
          />
          {actions.length > 0 && (
            <div className="mt-1">
              <ActionLegend actions={actions} />
            </div>
          )}
          {!solution && !loading && (
            <p className="text-[9px] text-zinc-700 text-center mt-2">
              Select a board to view
            </p>
          )}
        </div>

        {/* Center: board + solution */}
        <div className="flex-1 flex flex-col p-6 gap-5 overflow-auto">
          {/* Board selector */}
          <div className="flex items-center gap-4">
            <p className="text-[9px] tracking-widest text-zinc-600">BOARD</p>
            <div className="flex gap-2">
              {boardCards.map(c => <BoardCard key={c} card={c} />)}
              {Array(3 - boardCards.length).fill(0).map((_, i) => (
                <div key={i} className="w-9 h-12 border border-zinc-700 border-dashed rounded opacity-30" />
              ))}
            </div>
            <button
              onClick={() => setShowPicker(p => !p)}
              className="px-3 py-1 text-xs border border-zinc-700 text-zinc-400 hover:border-cyan-500 hover:text-cyan-400 transition-all tracking-widest">
              {showPicker ? "CLOSE" : "SELECT"}
            </button>
            {boardCards.length > 0 && (
              <button onClick={() => { setBoardCards([]); setSolution(null); setCombos([]); }}
                className="text-xs text-zinc-600 hover:text-rose-400 tracking-widest">
                CLEAR
              </button>
            )}
          </div>

          {/* Card picker */}
          {showPicker && (
            <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4 max-w-2xl">
              <p className="text-[9px] text-zinc-500 tracking-widest mb-3">
                SELECT 3 BOARD CARDS ({boardCards.length}/3)
              </p>
              <CardPicker
                selected={boardCards}
                dead={[]}
                onToggle={c => { toggleCard(c); if (boardCards.length === 2 && !boardCards.includes(c)) setShowPicker(false); }}
              />
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="flex items-center gap-3 text-xs text-cyan-500/60 animate-pulse">
              <span>FETCHING SOLUTION…</span>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="bg-rose-900/20 border border-rose-500/30 rounded-xl p-4 text-xs text-rose-400 max-w-lg">
              {error}
            </div>
          )}

          {/* Strategy bars */}
          {solution && (
            <div className="max-w-md">
              <p className="text-[9px] tracking-widest text-zinc-600 mb-3">
                AGGREGATE STRATEGY · {pos} vs BB · {solution.texture}
              </p>
              <div className="space-y-2">
                {solution.strategy.map(a => (
                  <div key={a.action}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-zinc-400">{ACTION_LABELS[a.action] ?? a.action}</span>
                      <span className="font-mono text-zinc-200">{(a.freq * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div className="h-full rounded-full transition-all duration-500"
                        style={{ width: `${a.freq * 100}%`, background: ACTION_COLORS[a.action] ?? "#555" }} />
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-[9px] text-zinc-700">
                exploitability: {solution.exploitability.toExponential(2)}
              </p>
            </div>
          )}
        </div>

        {/* Right: combo detail */}
        <div className="w-52 border-l border-cyan-500/10 p-4 flex flex-col gap-4">
          <p className="text-[9px] tracking-widest text-cyan-500/40">COMBO DETAIL</p>

          {selectedCombo ? (
            <>
              <div>
                <p className="text-[9px] text-zinc-600 tracking-widest mb-1">HAND</p>
                <p className="text-2xl font-bold text-white tracking-wider"
                  style={{ textShadow: "0 0 12px rgba(34,211,238,0.6)" }}>
                  {selectedCombo}
                </p>
              </div>

              {Object.entries(comboFreqs).length > 0 ? (
                <div className="space-y-2">
                  <p className="text-[9px] text-zinc-600 tracking-widest">STRATEGY</p>
                  {Object.entries(comboFreqs)
                    .sort((a, b) => b[1] - a[1])
                    .map(([action, freq]) => (
                      <div key={action}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-zinc-400">{ACTION_LABELS[action] ?? action}</span>
                          <span className="font-mono text-zinc-200">{(freq * 100).toFixed(0)}%</span>
                        </div>
                        <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                          <div className="h-full rounded-full"
                            style={{ width: `${freq * 100}%`, background: ACTION_COLORS[action] ?? "#555" }} />
                        </div>
                      </div>
                    ))
                  }
                </div>
              ) : (
                <p className="text-xs text-zinc-600">Dead combo (conflicts with board)</p>
              )}
            </>
          ) : (
            <p className="text-xs text-zinc-700 mt-4">
              Click a cell in the range grid to see per-hand strategy
            </p>
          )}
        </div>
      </div>
    </NeonShell>
  );
}

export default function LibraryPage() {
  return (
    <Suspense fallback={null}>
      <LibraryContent />
    </Suspense>
  );
}
