// Base-camp state: WIN balance, card storage, run bookkeeping. Pure functions
// over Save plus a tiny localStorage adapter.

import { CARDS } from "../engine/cards";
import { CLASSES, payoutFor, type DungeonDef } from "../engine/dungeon-def";
import type { CardId, ClassId, DungeonResult } from "../engine/types";

export type SaveV1 = {
  version: 1;
  win: number;
  cls: ClassId;
  storage: CardId[];
  stats: { runs: number; clears: number; deaths: number; escapes: number };
};

export const STORAGE_CAP = 100;
export const SAVE_KEY = "monster_gate.save.v1";

export function initialSave(): SaveV1 {
  return {
    version: 1,
    win: 100,
    cls: "warrior",
    storage: ["potion20", "potion20", "potion20", "potion40", "fire", "fire", "fire"],
    stats: { runs: 0, clears: 0, deaths: 0, escapes: 0 },
  };
}

export function canStart(save: SaveV1, def: DungeonDef, hand: CardId[]): string | null {
  if (hand.length > def.handSize) return `持ち込みは${def.handSize}枚まで`;
  if (save.win < def.bet) return `WINが足りない（BET ${def.bet}）`;
  return null;
}

/** Pay the BET and remove the chosen cards from storage (indices into storage). */
export function startRun(save: SaveV1, def: DungeonDef, pickIndices: number[]): { save: SaveV1; hand: CardId[] } {
  const hand = pickIndices.map((i) => {
    const c = save.storage[i];
    if (c === undefined) throw new Error(`bad storage index ${i}`);
    return c;
  });
  const err = canStart(save, def, hand);
  if (err) throw new Error(err);
  const picked = new Set(pickIndices);
  return {
    save: {
      ...save,
      win: save.win - def.bet,
      storage: save.storage.filter((_, i) => !picked.has(i)),
      stats: { ...save.stats, runs: save.stats.runs + 1 },
    },
    hand,
  };
}

export type RunOutcome = { result: Exclude<DungeonResult, null>; winCollected: number; multiplier: number; hand: CardId[] };

export function reward(def: DungeonDef, o: RunOutcome): number {
  return payoutFor(def, o);
}

/** Apply a finished run: pay out, return the hand to storage (unless dead). */
export function finishRun(save: SaveV1, def: DungeonDef, o: RunOutcome): { save: SaveV1; payout: number; overflow: CardId[] } {
  const payout = reward(def, o);
  const returned = o.result === "dead" ? [] : o.hand;
  const room = STORAGE_CAP - save.storage.length;
  const kept = returned.slice(0, Math.max(0, room));
  const overflow = returned.slice(kept.length);
  const stats = { ...save.stats };
  if (o.result === "clear") stats.clears++;
  else if (o.result === "dead") stats.deaths++;
  else stats.escapes++;
  return {
    save: { ...save, win: save.win + payout, storage: [...save.storage, ...kept], stats },
    payout,
    overflow,
  };
}

export function shopList(): { card: CardId; price: number }[] {
  return (Object.keys(CARDS) as CardId[]).flatMap((card) => {
    const price = CARDS[card].price;
    return price === undefined ? [] : [{ card, price }];
  });
}

export function buyCard(save: SaveV1, card: CardId): { save: SaveV1; error: string | null } {
  const price = CARDS[card].price;
  if (price === undefined) return { save, error: "非売品" };
  if (save.win < price) return { save, error: "WINが足りない" };
  if (save.storage.length >= STORAGE_CAP) return { save, error: "倉庫がいっぱい" };
  return { save: { ...save, win: save.win - price, storage: [...save.storage, card] }, error: null };
}

export function sellCard(save: SaveV1, index: number): SaveV1 {
  const card = save.storage[index];
  if (card === undefined) return save;
  const price = Math.floor((CARDS[card].price ?? 0) / 2);
  return { ...save, win: save.win + price, storage: save.storage.filter((_, i) => i !== index) };
}

// --- persistence -----------------------------------------------------------

export type Store = { getItem(k: string): string | null; setItem(k: string, v: string): void };

export function loadSave(store: Store): SaveV1 {
  try {
    const raw = store.getItem(SAVE_KEY);
    if (!raw) return initialSave();
    const parsed = JSON.parse(raw) as Partial<SaveV1>;
    if (parsed.version !== 1 || typeof parsed.win !== "number" || !Array.isArray(parsed.storage)) return initialSave();
    const storage = parsed.storage.filter((c): c is CardId => typeof c === "string" && c in CARDS);
    const cls: ClassId = typeof parsed.cls === "string" && parsed.cls in CLASSES ? parsed.cls : "warrior";
    return { ...initialSave(), ...parsed, cls, storage, stats: { ...initialSave().stats, ...parsed.stats } };
  } catch {
    return initialSave();
  }
}

export function persist(store: Store, save: SaveV1): void {
  try {
    store.setItem(SAVE_KEY, JSON.stringify(save));
  } catch {
    // storage unavailable (private mode etc.) — play on without persistence
  }
}
