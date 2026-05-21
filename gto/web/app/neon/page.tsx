"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchQuiz, submitAnswer, Quiz, AnswerResult } from "@/lib/trainer-api";
import { handToCards, cardColor } from "@/lib/cards";
import NeonShell from "@/components/layout/NeonShell";

const RANKS = ["A","K","Q","J","T","9","8","7","6","5","4","3","2"] as const;
const CELLS = RANKS.flatMap((r1, i) =>
  RANKS.map((r2, j) => ({
    label: i===j ? `${r1}${r2}` : i<j ? `${r1}${r2}s` : `${r2}${r1}o`,
    type:  (i===j ? "pair" : i<j ? "suited" : "offsuit") as "pair"|"suited"|"offsuit",
  }))
);

// RFI action labels
const RFI_ACTIONS    = [
  { key:"R", label:"RAISE",  color:"border-cyan-400 text-cyan-300",   glow:"rgba(34,211,238,0.5)" },
  { key:"F", label:"FOLD",   color:"border-rose-500 text-rose-400",   glow:"rgba(244,63,94,0.5)" },
];
const FACING_ACTIONS = [
  { key:"3B", label:"3-BET", color:"border-fuchsia-400 text-fuchsia-300", glow:"rgba(232,121,249,0.5)" },
  { key:"C",  label:"CALL",  color:"border-cyan-400 text-cyan-300",        glow:"rgba(34,211,238,0.5)" },
  { key:"F",  label:"FOLD",  color:"border-rose-500 text-rose-400",        glow:"rgba(244,63,94,0.5)" },
];

type Phase = "loading" | "quiz" | "result";

interface Session {
  hands: number;
  correct: number;
  evLoss: number;
}

function NeonCard({ card }: { card: string }) {
  return (
    <div
      className={`w-14 h-20 rounded-lg flex items-center justify-center text-2xl font-bold border select-none
        ${cardColor(card)} border-cyan-500/40`}
      style={{ background:"rgba(0,0,0,0.7)", boxShadow:"0 0 12px rgba(34,211,238,0.2), inset 0 0 8px rgba(34,211,238,0.05)" }}
    >
      {card}
    </div>
  );
}

function FreqBar({ label, freq, highlight }: { label: string; freq: number; highlight?: boolean }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className={highlight ? "text-cyan-300 font-bold" : "text-zinc-400"}>{label}</span>
        <span className={highlight ? "text-cyan-300 font-bold" : "text-zinc-500"}>{freq.toFixed(0)}%</span>
      </div>
      <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${highlight ? "bg-cyan-400" : "bg-zinc-600"}`}
          style={{ width:`${freq}%` }}
        />
      </div>
    </div>
  );
}

export default function NeonPage() {
  const [phase, setPhase]     = useState<Phase>("loading");
  const [quiz, setQuiz]       = useState<Quiz | null>(null);
  const [cards, setCards]     = useState<[string,string]>(["A♠","K♣"]);
  const [result, setResult]   = useState<AnswerResult | null>(null);
  const [session, setSession] = useState<Session>({ hands:0, correct:0, evLoss:0 });
  const [streak, setStreak]   = useState(0);
  const [loading, setLoading] = useState(false);

  const loadQuiz = useCallback(async () => {
    setPhase("loading");
    setResult(null);
    try {
      const q = await fetchQuiz();
      setQuiz(q);
      setCards(handToCards(q.hand));
      setPhase("quiz");
    } catch {
      setTimeout(loadQuiz, 1000);
    }
  }, []);

  useEffect(() => { loadQuiz(); }, [loadQuiz]);

  async function answer(chosen: string) {
    if (!quiz || loading) return;
    setLoading(true);
    try {
      const r = await submitAnswer(quiz, chosen);
      setResult(r);
      setPhase("result");
      setSession(s => ({
        hands:   s.hands + 1,
        correct: s.correct + (r.correct ? 1 : 0),
        evLoss:  s.evLoss + r.ev_loss,
      }));
      setStreak(s => r.correct ? s + 1 : 0);
    } finally {
      setLoading(false);
    }
  }

  const actions = quiz?.spot_type === "RFI" ? RFI_ACTIONS : FACING_ACTIONS;
  const accuracy = session.hands > 0 ? Math.round(session.correct / session.hands * 100) : 0;

  const rightSlot = (
    <>
      <span className="text-zinc-500">HANDS <span className="text-zinc-300">{session.hands}</span></span>
      <span className="text-zinc-500">ACC <span className={accuracy >= 70 ? "text-cyan-300" : "text-rose-400"}>{accuracy}%</span></span>
      <span className="text-zinc-500">EV LOSS <span className="text-rose-400">-{session.evLoss.toFixed(2)}bb</span></span>
      {streak > 0 && (
        <span className="text-fuchsia-300 font-bold" style={{ textShadow: "0 0 8px rgba(232,121,249,0.8)" }}>
          ×{streak} STREAK
        </span>
      )}
    </>
  );

  return (
    <NeonShell rightSlot={rightSlot}>
      <div className="flex h-full">
        {/* Left: range grid */}
        <aside className="w-52 border-r border-cyan-500/10 p-3 flex flex-col gap-3">
          <p className="text-[9px] tracking-widest text-cyan-500/40">RANGE MATRIX</p>
          <div className="grid gap-px" style={{ gridTemplateColumns:"repeat(13,1fr)" }}>
            {CELLS.map((c) => (
              <div key={c.label} title={c.label}
                className={`aspect-square flex items-center justify-center text-[6px] rounded-sm transition-all
                  ${c.label === quiz?.hand
                    ? "ring-1 ring-cyan-400 bg-cyan-400/30 text-cyan-200"
                    : c.type==="pair"    ? "bg-fuchsia-900/30 text-fuchsia-400/60 hover:bg-fuchsia-500/20"
                    : c.type==="suited"  ? "bg-cyan-900/30 text-cyan-400/50 hover:bg-cyan-500/20"
                    :                     "bg-zinc-900/60 text-zinc-600 hover:bg-zinc-700/40"
                  }`}>
                {c.label.slice(0,2)}
              </div>
            ))}
          </div>
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-[9px] mt-auto">
            <span className="text-fuchsia-400">■ PAIR</span>
            <span className="text-cyan-400">■ SUITED</span>
            <span className="text-zinc-600">■ OFF</span>
          </div>
        </aside>

        {/* Center: main area */}
        <main className="flex-1 flex flex-col items-center justify-center gap-7 px-8">
          {/* Spot info */}
          <div className="text-center space-y-1">
            <p className="text-[9px] tracking-[0.4em] text-zinc-600">
              {quiz?.spot_type === "RFI" ? "RAISE FIRST IN" : "FACING OPEN"}
            </p>
            <p className="text-zinc-400 text-sm tracking-wider">
              {quiz?.description ?? "Loading…"}
            </p>
          </div>

          {/* Cards */}
          <div className="flex gap-4">
            {cards.map((c, i) => <NeonCard key={i} card={c} />)}
          </div>

          {/* Hand label */}
          <div className="text-center">
            <span className="text-2xl font-bold tracking-widest text-white"
              style={{ textShadow:"0 0 20px rgba(34,211,238,0.6)" }}>
              {quiz?.hand}
            </span>
          </div>

          {/* Action buttons / Result */}
          {phase === "quiz" && (
            <div className="flex gap-3">
              {actions.map(a => (
                <button key={a.key}
                  onClick={() => answer(a.key)}
                  disabled={loading}
                  className={`px-6 py-2.5 text-xs tracking-[0.2em] border transition-all duration-150
                    ${a.color} disabled:opacity-30`}
                  style={{ boxShadow:`0 0 0 transparent`, }}
                  onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = `0 0 16px ${a.glow}`; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.boxShadow = "none"; }}
                >
                  {a.label}
                </button>
              ))}
            </div>
          )}

          {phase === "result" && result && (
            <div className="text-center space-y-3">
              {/* Correct / Wrong */}
              <div className={`text-lg font-bold tracking-widest ${result.correct ? "text-cyan-300" : "text-rose-400"}`}
                style={{ textShadow:result.correct ? "0 0 15px rgba(34,211,238,0.8)" : "0 0 15px rgba(244,63,94,0.8)" }}>
                {result.correct ? "✓ CORRECT" : "✗ INCORRECT"}
              </div>

              {/* EV loss */}
              {!result.correct && (
                <p className="text-xs text-rose-400">
                  EV LOSS: <span className="font-bold">-{result.ev_loss.toFixed(2)}bb</span>
                </p>
              )}

              <button onClick={loadQuiz}
                className="px-8 py-2.5 text-xs tracking-[0.3em] border border-cyan-400 text-cyan-300 hover:bg-cyan-400/10 transition-all"
                style={{ boxShadow:"0 0 10px rgba(34,211,238,0.3)" }}>
                NEXT HAND →
              </button>
            </div>
          )}

          {phase === "loading" && (
            <p className="text-xs text-zinc-600 tracking-widest animate-pulse">LOADING…</p>
          )}
        </main>

        {/* Right: GTO breakdown */}
        <aside className="w-52 border-l border-cyan-500/10 p-4 flex flex-col gap-5">
          <p className="text-[9px] tracking-widest text-cyan-500/40">GTO SOLUTION</p>

          {phase === "result" && result ? (
            <>
              <div className="space-y-3">
                {result.all_actions.map(a => (
                  <FreqBar
                    key={a.action}
                    label={a.action}
                    freq={a.freq}
                    highlight={a.action === result.gto_action}
                  />
                ))}
              </div>

              <div className="border-t border-cyan-500/10 pt-4 space-y-2">
                <p className="text-[9px] text-zinc-600 tracking-widest">YOUR CHOICE</p>
                <p className={`text-sm font-bold tracking-wider ${result.correct ? "text-cyan-300" : "text-rose-400"}`}>
                  {result.chosen} · {result.all_actions.find(a=>a.action===result.chosen)?.freq.toFixed(0) ?? 0}%
                </p>
                <p className="text-[9px] text-zinc-600">GTO OPTIMAL</p>
                <p className="text-sm font-bold text-cyan-300 tracking-wider">
                  {result.gto_action} · {result.gto_freq.toFixed(0)}%
                </p>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-zinc-700 text-xs">
              answer to reveal
            </div>
          )}

          {/* Session stats */}
          <div className="border-t border-cyan-500/10 pt-4 space-y-2 mt-auto">
            <p className="text-[9px] text-zinc-600 tracking-widest">SESSION</p>
            {[
              { label:"HANDS",   val: String(session.hands) },
              { label:"CORRECT", val: `${session.correct}/${session.hands}` },
              { label:"EV LOSS", val: `-${session.evLoss.toFixed(2)}bb` },
              { label:"STREAK",  val: `×${streak}` },
            ].map(s => (
              <div key={s.label} className="flex justify-between text-[10px]">
                <span className="text-zinc-600">{s.label}</span>
                <span className="text-zinc-300">{s.val}</span>
              </div>
            ))}
          </div>
        </aside>
      </div>
    </NeonShell>
  );
}
