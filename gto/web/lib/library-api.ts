import { canonicalizeBoard } from "@/lib/flop-canon";

// ---------------------------------------------------------------------------
// Position-level aggregate cache (pre-computed JSON, served from /solutions/cache/)
// ---------------------------------------------------------------------------

interface PositionCache {
  position: string;
  stack_bb: number;
  spots: Record<string, {
    texture: string;
    exploitability: number;
    strategy: Record<string, number>;
  }>;
}

// Module-level Map: "{pos}_{stack}" → PositionCache | null (null = fetch failed)
const _aggCache = new Map<string, PositionCache | null>();

async function loadAggregateCache(position: string, stackBb: number): Promise<PositionCache | null> {
  const key = `${position}_${Math.round(stackBb)}`;
  if (_aggCache.has(key)) return _aggCache.get(key)!;

  try {
    const res = await fetch(`/solutions/cache/${position}_${Math.round(stackBb)}.json`);
    if (!res.ok) { _aggCache.set(key, null); return null; }
    const data: PositionCache = await res.json();
    _aggCache.set(key, data);
    return data;
  } catch {
    _aggCache.set(key, null);
    return null;
  }
}

const BASE = "";

export interface ActionFreq {
  action: string;
  freq: number;
}

export interface SpotStrategy {
  spot_id: string;
  board: string;
  position: string;
  opponent: string;
  stack_bb: number;
  texture: string;
  exploitability: number;
  strategy: ActionFreq[];
}

export interface ComboStrategy {
  card_a: number;
  card_b: number;
  action: string;
  freq: number;
}

export interface FlopReport {
  board: string;
  texture: string;
  check_freq: number;
  bet33_freq: number;
  bet75_freq: number;
  bet100_freq: number;
}

export async function fetchFlopSolution(
  board: string,
  position: string,
  stackBb: number = 100,
): Promise<SpotStrategy | null> {
  // Parse board string into individual card tokens
  const cards = board.length === 6
    ? [board.slice(0, 2), board.slice(2, 4), board.slice(4, 6)]
    : board.split(/\s+/);

  // Try pre-computed cache first (instant, no API call)
  const canon = canonicalizeBoard(cards);
  const cache = await loadAggregateCache(position, stackBb);
  if (cache?.spots[canon]) {
    const s = cache.spots[canon];
    return {
      spot_id: `${position}_vs_BB_${Math.round(stackBb)}bb_${canon}_flop`,
      board: canon,
      position,
      opponent: "BB",
      stack_bb: stackBb,
      texture: s.texture,
      exploitability: s.exploitability,
      strategy: Object.entries(s.strategy)
        .map(([action, freq]) => ({ action, freq }))
        .sort((a, b) => b.freq - a.freq),
    };
  }

  // Fallback: API (handles spots not yet in cache, or cache unavailable)
  const url = new URL(`${window.location.origin}/api/library/flop`);
  url.searchParams.set("board", board);
  url.searchParams.set("position", position);
  url.searchParams.set("stack_bb", String(stackBb));
  const res = await fetch(url.toString());
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchComboStrategies(
  board: string,
  position: string,
  stackBb: number = 100,
): Promise<ComboStrategy[]> {
  const url = new URL(`${window.location.origin}/api/library/flop/combos`);
  url.searchParams.set("board", board);
  url.searchParams.set("position", position);
  url.searchParams.set("stack_bb", String(stackBb));
  const res = await fetch(url.toString());
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchFlopReport(
  position: string,
  stackBb: number = 100,
): Promise<FlopReport[]> {
  const url = new URL(`${window.location.origin}/api/library/report`);
  url.searchParams.set("position", position);
  url.searchParams.set("stack_bb", String(stackBb));
  url.searchParams.set("limit", "200");
  const res = await fetch(url.toString());
  if (!res.ok) return [];
  return res.json();
}

export async function solveLive(
  board: string[],
  potBb: number,
  stackBb: number,
  iterations: number = 100,
): Promise<SpotStrategy | null> {
  const res = await fetch(`/api/solver/solve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      board,
      pot_bb: potBb,
      effective_stack_bb: stackBb,
      iterations,
    }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return {
    spot_id: "live",
    board: board.join(""),
    position: "?",
    opponent: "BB",
    stack_bb: stackBb,
    texture: "",
    exploitability: data.exploitability,
    strategy: data.strategy,
  };
}

// --- Card helpers ---
// Backend card encoding (gto-core/src/card.rs): card = rank*4 + suit, with
// rank 0=2 … 12=A and suit 0=c,1=d,2=h,3=s. The integer card_a/card_b coming
// back from /api/library/flop/combos are in THIS encoding, so decoding must use
// RANK_ORDER (NOT the A-high display order) or every rank is mirror-flipped.
const RANK_ORDER = "23456789TJQKA"; // index == backend rank index
const SUITS = "cdhs";
// A-high strength order, used only to label/order combos for display.
const STRENGTH = "AKQJT98765432";

export function cardIndex(rank: string, suit: string): number {
  return RANK_ORDER.indexOf(rank) * 4 + SUITS.indexOf(suit);
}

export function cardFromIndex(idx: number): { rank: string; suit: string } {
  return { rank: RANK_ORDER[Math.floor(idx / 4)], suit: SUITS[idx % 4] };
}

export function comboKey(cardA: number, cardB: number): string {
  const a = cardFromIndex(cardA);
  const b = cardFromIndex(cardB);
  const ri = Math.min(STRENGTH.indexOf(a.rank), STRENGTH.indexOf(b.rank));
  const rj = Math.max(STRENGTH.indexOf(a.rank), STRENGTH.indexOf(b.rank));
  const r1 = STRENGTH[ri], r2 = STRENGTH[rj];
  if (ri === rj) return `${r1}${r2}`;
  const suited = a.suit === b.suit;
  return `${r1}${r2}${suited ? "s" : "o"}`;
}

// Action → neon color
export const ACTION_COLORS: Record<string, string> = {
  "Check":   "#3f3f46",   // zinc
  "Bet33":   "#0e7490",   // cyan-700
  "Bet(0)":  "#0e7490",
  "Bet75":   "#0284c7",   // sky-600
  "Bet(1)":  "#0284c7",
  "Bet100":  "#7c3aed",   // violet-600
  "Bet(2)":  "#7c3aed",
  "Fold":    "#be123c",   // rose-700
  "Call":    "#15803d",   // green-700
  "Raise33": "#c026d3",   // fuchsia-600
  "Raise75": "#e11d48",
  "Raise100":"#dc2626",
};

export const ACTION_LABELS: Record<string, string> = {
  "Check":   "Check",
  "Bet33":   "Bet 33%",  "Bet(0)": "Bet 33%",
  "Bet75":   "Bet 75%",  "Bet(1)": "Bet 75%",
  "Bet100":  "Bet 100%", "Bet(2)": "Bet 100%",
  "Fold":    "Fold",
  "Call":    "Call",
};
