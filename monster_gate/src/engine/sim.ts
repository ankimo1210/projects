import { botAction, DEFAULT_BOT, newMemory, type BotConfig } from "./bot";
import { createRun } from "./dungeon";
import type { DungeonDef } from "./dungeon-def";
import { step } from "./turn";
import type { CardId, ClassId, DungeonResult } from "./types";

export type SimResult = { result: Exclude<DungeonResult, null> | "timeout"; floor: number; turns: number; cardsUsed: number; winCollected: number };

export function simulate(seed: number, def: DungeonDef, hand: CardId[], cfg: BotConfig = DEFAULT_BOT, maxTurns = 3000, cls: ClassId = "warrior"): SimResult {
  let s = createRun(seed, def, hand, cls);
  let cardsUsed = 0;
  let guard = 0;
  const mem = newMemory();
  while (!s.result && s.turn < maxTurns && guard < maxTurns * 3) {
    guard++;
    const a = botAction(s, cfg, mem);
    const r = step(s, a);
    if (r.events.some((e) => e.t === "cardUsed")) cardsUsed++;
    // a blocked action would loop forever; fall back to waiting
    s = r.state === s ? step(s, { type: "wait" }).state : r.state;
  }
  return { result: s.result ?? "timeout", floor: s.floorNo, turns: s.turn, cardsUsed, winCollected: s.winCollected };
}

export type Summary = { n: number; clear: number; dead: number; escaped: number; timeout: number; deathsByFloor: number[]; avgTurns: number; avgCards: number };

export function summarize(results: SimResult[], floors: number): Summary {
  const deathsByFloor = new Array<number>(floors + 1).fill(0);
  let turns = 0;
  let cards = 0;
  const c = { clear: 0, dead: 0, escaped: 0, timeout: 0 };
  for (const r of results) {
    c[r.result]++;
    if (r.result === "dead") deathsByFloor[r.floor]!++;
    turns += r.turns;
    cards += r.cardsUsed;
  }
  return { n: results.length, ...c, deathsByFloor, avgTurns: turns / results.length, avgCards: cards / results.length };
}
