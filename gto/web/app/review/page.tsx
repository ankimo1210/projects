"use client";

import { useState, useCallback, useRef } from "react";
import NeonShell from "@/components/layout/NeonShell";
import {
  parseHandHistory,
  ParsedHand, ParseError, HandAction, DeviationFlag,
} from "@/lib/review-api";
import { buildStreetViews } from "@/lib/pot";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SUIT_SYMBOLS: Record<string, string> = { c:"♣", d:"♦", h:"♥", s:"♠" };
const SUIT_COLORS:  Record<string, string> = { c:"text-zinc-300", d:"text-rose-400", h:"text-rose-400", s:"text-zinc-300" };

// Action verb → text color in the timeline
const ACTION_TEXT_COLORS: Record<HandAction["action"], string> = {
  fold:  "text-rose-400",
  check: "text-zinc-400",
  call:  "text-emerald-400",
  bet:   "text-cyan-400",
  raise: "text-fuchsia-400",
};

// Deviation flag → badge style
const FLAG_STYLES: Record<DeviationFlag["flag"], string> = {
  ok:           "border-emerald-500/40 text-emerald-400 bg-emerald-500/10",
  loose:        "border-amber-500/40 text-amber-400 bg-amber-500/10",
  tight:        "border-sky-500/40 text-sky-400 bg-sky-500/10",
  missing_data: "border-zinc-700 text-zinc-500 bg-zinc-800/40",
};

// Preflop GTO action codes
const DEV_ACTION_LABELS: Record<string, string> = { R: "Raise", "3B": "3-Bet", C: "Call", F: "Fold" };
const DEV_ACTION_COLORS: Record<string, string> = { R: "#c026d3", "3B": "#e11d48", C: "#15803d", F: "#be123c" };

const STREET_LABELS: Record<string, string> = {
  preflop: "PREFLOP", flop: "FLOP", turn: "TURN", river: "RIVER",
};

const BLIND_LABELS: Record<string, string> = {
  small: "posts small blind", big: "posts big blind",
  small_and_big: "posts small & big blinds", ante: "posts ante",
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function fmt(n: number): string {
  return n.toFixed(2).replace(/\.?0+$/, "");
}

// ---------------------------------------------------------------------------
// Card chip
// ---------------------------------------------------------------------------

function CardChip({ card, hero = false, small = false }: {
  card: string; hero?: boolean; small?: boolean;
}) {
  const r = card[0], s = card[1];
  return (
    <div
      className={`${small ? "w-6 h-8 text-[11px]" : "w-9 h-12 text-base"}
        bg-white/5 border rounded flex items-center justify-center font-bold
        ${hero ? "border-cyan-400/60" : "border-cyan-500/30"}`}
      style={{ boxShadow: hero ? "0 0 10px rgba(34,211,238,0.35)" : "0 0 8px rgba(34,211,238,0.15)" }}
    >
      <span className={SUIT_COLORS[s] ?? "text-zinc-300"}>{r}{SUIT_SYMBOLS[s] ?? s}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Deviation badge
// ---------------------------------------------------------------------------

function DeviationBadge({ dev }: { dev: DeviationFlag }) {
  const freqs = Object.entries(dev.gto_frequencies).sort((a, b) => b[1] - a[1]);
  return (
    <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4 max-w-md">
      <div className="flex items-center gap-3 mb-3">
        <p className="text-[9px] tracking-widest text-cyan-500/40">PREFLOP DEVIATION</p>
        <span className={`px-2 py-0.5 text-[10px] tracking-widest border rounded-sm uppercase ${FLAG_STYLES[dev.flag]}`}>
          {dev.flag.replace("_", " ")}
        </span>
      </div>

      <div className="flex items-center gap-3 text-xs text-zinc-400 mb-3 flex-wrap">
        {dev.hand && <span className="text-white font-bold">{dev.hand}</span>}
        {dev.spot_type && <span className="text-zinc-500">{dev.spot_type}</span>}
        {dev.position && <span className="text-zinc-500">{dev.position}</span>}
        {dev.hero_action && (
          <span>
            HERO <span className="text-cyan-300">{DEV_ACTION_LABELS[dev.hero_action] ?? dev.hero_action}</span>
          </span>
        )}
        {dev.gto_action && (
          <span>
            GTO <span className="text-zinc-200">{DEV_ACTION_LABELS[dev.gto_action] ?? dev.gto_action}</span>
          </span>
        )}
      </div>

      {freqs.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[9px] text-zinc-600 tracking-widest">GTO FREQUENCIES</p>
          {freqs.map(([action, pct]) => (
            <div key={action}>
              <div className="flex justify-between text-[11px] mb-0.5">
                <span className="text-zinc-400">{DEV_ACTION_LABELS[action] ?? action}</span>
                <span className="font-mono text-zinc-200">{pct.toFixed(1)}%</span>
              </div>
              <div className="h-1 bg-zinc-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full"
                  style={{ width: `${Math.min(pct, 100)}%`, background: DEV_ACTION_COLORS[action] ?? "#555" }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {dev.ev_loss != null && (
        <p className="mt-3 text-[10px] text-zinc-500">
          EV LOSS <span className="text-rose-400 font-mono">{dev.ev_loss.toFixed(2)}</span>
        </p>
      )}
      {dev.reason && (
        <p className="mt-2 text-[10px] text-zinc-600">{dev.reason}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hand detail
// ---------------------------------------------------------------------------

function actionText(a: HandAction): string {
  switch (a.action) {
    case "fold":  return "folds";
    case "check": return "checks";
    case "call":  return `calls ${a.amount != null ? fmt(a.amount) : ""}`.trim();
    case "bet":   return `bets ${a.amount != null ? fmt(a.amount) : ""}`.trim();
    case "raise":
      return a.raise_to != null
        ? `raises${a.amount != null ? ` ${fmt(a.amount)}` : ""} to ${fmt(a.raise_to)}`
        : `raises${a.amount != null ? ` ${fmt(a.amount)}` : ""}`;
  }
}

function HandDetail({ hand }: { hand: ParsedHand }) {
  const streets = buildStreetViews(hand);
  const stakes = `${fmt(hand.stakes.small_blind)}/${fmt(hand.stakes.big_blind)} ${hand.stakes.currency}`;

  return (
    <div className="flex flex-col gap-5 max-w-3xl">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 flex-wrap">
          <p className="text-lg font-bold text-white tracking-wider"
            style={{ textShadow: "0 0 12px rgba(34,211,238,0.6)" }}>
            #{hand.hand_id}
          </p>
          {hand.zoom && (
            <span className="px-2 py-0.5 text-[10px] tracking-widest border border-violet-500/40 text-violet-400 bg-violet-500/10 rounded-sm">
              ZOOM
            </span>
          )}
        </div>
        <p className="text-[11px] text-zinc-500 mt-1">
          {hand.table_name} · {stakes}
          {hand.max_players != null && ` · ${hand.max_players}-max`}
          {hand.played_at && ` · ${hand.played_at.replace("T", " ")}${hand.timezone ? ` ${hand.timezone}` : ""}`}
        </p>
      </div>

      {/* Hero */}
      <div className="flex items-center gap-4">
        <p className="text-[9px] tracking-widest text-zinc-600">HERO</p>
        {hand.hero_name ? (
          <>
            <span className="text-xs text-cyan-300"
              style={{ textShadow: "0 0 8px rgba(34,211,238,0.6)" }}>
              {hand.hero_name}
            </span>
            {hand.positions[hand.hero_name] && (
              <span className="px-1.5 py-0.5 text-[10px] border border-cyan-400/40 text-cyan-300 rounded-sm">
                {hand.positions[hand.hero_name]}
              </span>
            )}
            <div className="flex gap-1.5">
              {hand.hero_cards
                ? hand.hero_cards.map(c => <CardChip key={c} card={c} hero />)
                : <span className="text-xs text-zinc-600">no hole cards</span>}
            </div>
          </>
        ) : (
          <span className="text-xs text-zinc-600">not at table</span>
        )}
      </div>

      {/* Preflop deviation */}
      {hand.preflop_deviation && <DeviationBadge dev={hand.preflop_deviation} />}

      {/* Players */}
      <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4 max-w-md">
        <p className="text-[9px] tracking-widest text-cyan-500/40 mb-2">PLAYERS</p>
        <div className="space-y-1">
          {hand.players.map(p => {
            const isHero = p.name === hand.hero_name;
            return (
              <div key={p.seat}
                className={`flex items-center gap-2 text-[11px] ${p.sitting_out ? "opacity-40" : ""}`}>
                <span className="w-4 text-zinc-600">{p.seat}</span>
                <span className="w-12 text-zinc-500">{hand.positions[p.name] ?? ""}</span>
                <span className={isHero ? "text-cyan-300" : "text-zinc-300"}>
                  {p.name}
                </span>
                {p.seat === hand.button_seat && (
                  <span className="px-1 text-[9px] border border-zinc-700 text-zinc-500 rounded-sm">BTN</span>
                )}
                {p.sitting_out && <span className="text-[9px] text-zinc-600">sitting out</span>}
                <span className="ml-auto font-mono text-zinc-400">{fmt(p.stack)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Streets */}
      <div className="space-y-4">
        {streets.map(sv => (
          <div key={sv.street} className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4">
            <div className="flex items-center gap-4 mb-3">
              <p className="text-[9px] tracking-widest text-cyan-500/40 w-16">
                {STREET_LABELS[sv.street]}
              </p>
              {sv.boardSoFar.length > 0 && (
                <div className="flex gap-1.5">
                  {sv.boardSoFar.map(c => <CardChip key={c} card={c} small />)}
                </div>
              )}
              <span className="ml-auto text-[10px] text-zinc-600 font-mono">
                POT {fmt(sv.potBefore)}
              </span>
            </div>

            {/* Blind posts (preflop only) */}
            {sv.street === "preflop" && hand.posts.length > 0 && (
              <div className="space-y-0.5 mb-2">
                {hand.posts.map((p, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px] text-zinc-600">
                    <span className={p.player === hand.hero_name ? "text-cyan-500/60" : ""}>{p.player}</span>
                    <span>{BLIND_LABELS[p.blind_type] ?? p.blind_type}</span>
                    <span className="font-mono">{fmt(p.amount)}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Actions */}
            {sv.rows.length > 0 ? (
              <div className="space-y-1">
                {sv.rows.map(({ action: a, potAfter }, i) => {
                  const isHero = a.actor === hand.hero_name;
                  return (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      <span className="w-12 text-[10px] text-zinc-600">{hand.positions[a.actor] ?? ""}</span>
                      <span className={isHero ? "text-cyan-300" : "text-zinc-300"}>
                        {a.actor}
                      </span>
                      <span className={ACTION_TEXT_COLORS[a.action]}>{actionText(a)}</span>
                      {a.all_in && (
                        <span className="px-1 text-[9px] border border-rose-500/40 text-rose-400 rounded-sm tracking-widest">
                          ALL-IN
                        </span>
                      )}
                      <span className="ml-auto font-mono text-[10px] text-zinc-700">{fmt(potAfter)}</span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="text-[10px] text-zinc-700">no action</p>
            )}
          </div>
        ))}
      </div>

      {/* Showdown */}
      {hand.showdown.length > 0 && (
        <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4">
          <p className="text-[9px] tracking-widest text-cyan-500/40 mb-2">SHOWDOWN</p>
          <div className="space-y-1.5">
            {hand.showdown.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                <span className={s.player === hand.hero_name ? "text-cyan-300" : "text-zinc-300"}>
                  {s.player}
                </span>
                {s.cards ? (
                  <div className="flex gap-1">
                    {s.cards.map(c => (
                      <CardChip key={c} card={c} small hero={s.player === hand.hero_name} />
                    ))}
                  </div>
                ) : s.mucked ? (
                  <span className="text-zinc-600">mucks</span>
                ) : null}
                {s.description && <span className="text-[10px] text-zinc-500">{s.description}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary */}
      <div className="bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-4">
        <p className="text-[9px] tracking-widest text-cyan-500/40 mb-2">SUMMARY</p>
        <div className="space-y-1 text-[11px]">
          {hand.uncalled_bets.map((u, i) => (
            <p key={i} className="text-zinc-500">
              Uncalled bet ({fmt(u.amount)}) returned to{" "}
              <span className={u.player === hand.hero_name ? "text-cyan-300" : "text-zinc-300"}>{u.player}</span>
            </p>
          ))}
          {hand.winners.map((w, i) => (
            <p key={i} className="text-zinc-400">
              <span className={w.player === hand.hero_name ? "text-cyan-300" : "text-zinc-200"}>{w.player}</span>
              {" "}collected <span className="font-mono text-emerald-400">{fmt(w.amount)}</span> from {w.pot}
            </p>
          ))}
          <p className="text-zinc-600 pt-1">
            Total pot{" "}
            <span className="font-mono text-zinc-300">
              {hand.total_pot != null ? fmt(hand.total_pot) : "—"}
            </span>
            {hand.rake != null && (
              <> · Rake <span className="font-mono">{fmt(hand.rake)}</span></>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ReviewPage() {
  const [text, setText] = useState("");
  const [hands, setHands] = useState<ParsedHand[]>([]);
  const [parseErrors, setParseErrors] = useState<ParseError[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [parsed, setParsed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Bumped on every parse/clear so a slow in-flight response cannot
  // overwrite state set by a later action (stale-response guard).
  const requestSeq = useRef(0);

  const parse = useCallback(async () => {
    if (!text.trim()) return;
    const seq = ++requestSeq.current;
    setLoading(true); setError(null);
    try {
      const res = await parseHandHistory(text);
      if (seq !== requestSeq.current) return; // superseded by clear/re-parse
      setHands(res.hands);
      setParseErrors(res.errors);
      setSelected(res.hands.length > 0 ? 0 : null);
      setParsed(true);
    } catch (e: unknown) {
      if (seq !== requestSeq.current) return;
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      if (seq === requestSeq.current) setLoading(false);
    }
  }, [text]);

  function clear() {
    requestSeq.current++; // invalidate any in-flight parse
    setText(""); setHands([]); setParseErrors([]);
    setSelected(null); setParsed(false); setError(null); setLoading(false);
  }

  const rightSlot = parsed ? (
    <span className="text-zinc-600">
      {hands.length} hand{hands.length === 1 ? "" : "s"} · {parseErrors.length} error{parseErrors.length === 1 ? "" : "s"}
    </span>
  ) : undefined;

  return (
    <NeonShell rightSlot={rightSlot}>
      <div className="flex h-full">
        {/* Left: paste area */}
        <div className="w-80 border-r border-cyan-500/10 p-3 flex flex-col gap-3 shrink-0">
          <p className="text-[9px] tracking-widest text-cyan-500/40">HAND HISTORY</p>
          <textarea
            value={text}
            onChange={e => setText(e.target.value)}
            placeholder="Paste PokerStars hand history here…"
            spellCheck={false}
            className="flex-1 min-h-40 bg-zinc-900/80 border border-cyan-500/10 rounded-xl p-3
              text-[11px] text-zinc-300 placeholder-zinc-700 resize-none font-mono
              focus:outline-none focus:border-cyan-500/40 transition-colors"
          />
          <div className="flex gap-2">
            <button
              onClick={parse}
              disabled={loading || !text.trim()}
              className="px-3 py-1.5 text-xs tracking-widest border border-cyan-400/60 text-cyan-300 bg-cyan-400/10
                hover:bg-cyan-400/20 transition-all rounded-sm disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? "PARSING…" : "PARSE"}
            </button>
            <button
              onClick={clear}
              className="px-3 py-1.5 text-xs tracking-widest border border-zinc-700 text-zinc-500
                hover:border-rose-500/40 hover:text-rose-400 transition-all rounded-sm"
            >
              CLEAR
            </button>
          </div>

          {error && (
            <div className="bg-rose-900/20 border border-rose-500/30 rounded-xl p-3 text-xs text-rose-400">
              {error}
            </div>
          )}

          {/* Parse errors */}
          {parseErrors.length > 0 && (
            <div className="overflow-auto">
              <p className="text-[9px] tracking-widest text-rose-400/60 mb-2">
                PARSE ERRORS ({parseErrors.length})
              </p>
              <div className="space-y-2">
                {parseErrors.map(err => (
                  <div key={err.index}
                    className="bg-rose-900/20 border border-rose-500/30 rounded-xl p-2 text-[10px]">
                    <p className="text-rose-400">hand #{err.index + 1}: {err.message}</p>
                    <p className="text-zinc-600 truncate mt-0.5">{err.snippet}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Middle: hand list */}
        <div className="w-72 border-r border-cyan-500/10 flex flex-col shrink-0">
          <p className="text-[9px] tracking-widest text-cyan-500/40 px-3 pt-3 pb-2">
            HANDS ({hands.length})
          </p>
          <div className="flex-1 overflow-auto px-2 pb-2 space-y-1">
            {hands.map((h, i) => (
              <button
                key={`${h.hand_id}-${i}`}
                onClick={() => setSelected(i)}
                className={`w-full text-left rounded-lg border p-2 transition-all
                  ${selected === i
                    ? "border-cyan-400/60 bg-cyan-400/10"
                    : "border-zinc-800 bg-zinc-900/50 hover:border-zinc-600"}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-[11px] font-mono ${selected === i ? "text-cyan-300" : "text-zinc-300"}`}>
                    #{h.hand_id}
                  </span>
                  {h.zoom && <span className="text-[8px] tracking-widest text-violet-400">ZOOM</span>}
                  {h.preflop_deviation && h.preflop_deviation.flag !== "ok" && h.preflop_deviation.flag !== "missing_data" && (
                    <span className={`px-1 text-[8px] tracking-widest border rounded-sm uppercase ${FLAG_STYLES[h.preflop_deviation.flag]}`}>
                      {h.preflop_deviation.flag}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] text-zinc-500">
                    {fmt(h.stakes.small_blind)}/{fmt(h.stakes.big_blind)} {h.stakes.currency}
                  </span>
                  <div className="flex gap-1">
                    {h.hero_cards
                      ? h.hero_cards.map(c => <CardChip key={c} card={c} small hero />)
                      : <span className="text-[10px] text-zinc-700">—</span>}
                  </div>
                  <span className="ml-auto text-[10px] font-mono text-zinc-500">
                    pot {h.total_pot != null ? fmt(h.total_pot) : "—"}
                  </span>
                </div>
              </button>
            ))}
            {parsed && hands.length === 0 && (
              <p className="text-[10px] text-zinc-700 px-1 pt-2">No hands parsed.</p>
            )}
            {!parsed && (
              <p className="text-[10px] text-zinc-700 px-1 pt-2">
                Paste a hand history and press PARSE.
              </p>
            )}
          </div>
        </div>

        {/* Right: hand detail */}
        <div className="flex-1 overflow-auto p-6">
          {selected != null && hands[selected] ? (
            <HandDetail hand={hands[selected]} />
          ) : (
            <div className="flex items-center justify-center h-full text-zinc-700 text-xs tracking-widest">
              {loading ? (
                <span className="text-cyan-500/60 animate-pulse">PARSING…</span>
              ) : (
                "SELECT A HAND TO REVIEW"
              )}
            </div>
          )}
        </div>
      </div>
    </NeonShell>
  );
}
