import { describe, expect, it } from "vitest";
import { DUNGEON_LIST, YUKAI } from "../src/engine/dungeon-def";
import { DEFAULT_BOT } from "../src/engine/bot";
import { simulate, summarize } from "../src/engine/sim";
import type { CardId } from "../src/engine/types";

const STARTER: CardId[] = ["potion20", "potion20", "potion20", "potion40", "fire", "fire", "fire"];
const STRONG: CardId[] = ["powerUp", "potion80", "potion80", "meteor", "thunder", "multiFire", "longSword", "powerShield", "reviveRing", "potion40"];
const N = Number(import.meta.env.SIM_N ?? 200);

describe("balance simulation", () => {
  it("starter hand: reports clear rate and keeps it in the target band", () => {
    const results = [];
    for (let seed = 1; seed <= N; seed++) results.push(simulate(seed, YUKAI, STARTER));
    const s = summarize(results, YUKAI.floors.length);
    const rate = s.clear / s.n;
    console.log(`[sim starter] n=${s.n} clear=${(rate * 100).toFixed(1)}% dead=${s.dead} timeout=${s.timeout} deathsByFloor=${s.deathsByFloor.slice(1).join("/")} avgTurns=${s.avgTurns.toFixed(0)} avgCards=${s.avgCards.toFixed(1)}`);
    expect(s.timeout).toBe(0);
    expect(rate).toBeGreaterThan(0.15);
    expect(rate).toBeLessThan(0.45);
  }, 60_000);

  it("every dungeon: report clear rates (no assertion beyond termination)", () => {
    for (const def of DUNGEON_LIST) {
      const results = [];
      for (let seed = 1; seed <= Math.min(N, 100); seed++) results.push(simulate(seed, def, STARTER.slice(0, def.handSize)));
      const s = summarize(results, def.floors.length);
      const strong = [];
      for (let seed = 1; seed <= Math.min(N, 100); seed++) strong.push(simulate(seed, def, STRONG.slice(0, def.handSize)));
      const t = summarize(strong, def.floors.length);
      console.log(`[sim ${def.id} ★${def.stars}] starter clear=${((s.clear / s.n) * 100).toFixed(1)}% deaths=${s.deathsByFloor.slice(1).join("/")}  |  strong clear=${((t.clear / t.n) * 100).toFixed(1)}% deaths=${t.deathsByFloor.slice(1).join("/")} turns=${t.avgTurns.toFixed(0)}`);
      // The reference bot occasionally fails to navigate ice within the turn cap.
      // Goals themselves are provably reachable (see expansion.test.ts).
      expect(s.timeout).toBeLessThanOrEqual(10);
      expect(t.timeout).toBeLessThanOrEqual(10);
    }
  }, 120_000);

  it("all three classes can clear the standard dungeon", () => {
    for (const cls of ["warrior", "mage", "gambler"] as const) {
      const results = [];
      for (let seed = 1; seed <= Math.min(N, 100); seed++) results.push(simulate(seed, YUKAI, STARTER, DEFAULT_BOT, 3000, cls));
      const s = summarize(results, YUKAI.floors.length);
      console.log(`[sim class ${cls}] clear=${((s.clear / s.n) * 100).toFixed(1)}% dead=${s.dead} avgTurns=${s.avgTurns.toFixed(0)}`);
      expect(s.clear / s.n).toBeGreaterThan(0.15);
      expect(s.timeout).toBeLessThanOrEqual(10);
    }
  }, 120_000);

  it("empty hand is clearly harder than the starter hand", () => {
    const a = [];
    const b = [];
    for (let seed = 1; seed <= N; seed++) {
      a.push(simulate(seed, YUKAI, []));
      b.push(simulate(seed, YUKAI, STARTER));
    }
    const ra = summarize(a, 7).clear / N;
    const rb = summarize(b, 7).clear / N;
    console.log(`[sim empty] clear=${(ra * 100).toFixed(1)}%  vs starter ${(rb * 100).toFixed(1)}%`);
    expect(ra).toBeLessThan(rb);
  }, 60_000);
});
