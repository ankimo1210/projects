import { describe, expect, it } from "vitest";
import { YUKAI } from "../src/engine/dungeon-def";
import { buyCard, canStart, finishRun, initialSave, loadSave, persist, reward, sellCard, startRun, STORAGE_CAP, type SaveV1, type Store } from "../src/game/meta";

function memStore(): Store & { data: Record<string, string> } {
  const data: Record<string, string> = {};
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => void (data[k] = v) };
}

describe("meta", () => {
  it("starting a run pays the BET and moves picked cards to the hand", () => {
    const s0 = initialSave();
    const { save, hand } = startRun(s0, YUKAI, [0, 4]);
    expect(save.win).toBe(90);
    expect(hand).toEqual(["potion20", "fire"]);
    expect(save.storage.length).toBe(s0.storage.length - 2);
    expect(save.stats.runs).toBe(1);
  });

  it("refuses to start without enough WIN or with too many cards", () => {
    const poor = { ...initialSave(), win: 5 };
    expect(canStart(poor, YUKAI, [])).toMatch(/WIN/);
    expect(canStart(initialSave(), YUKAI, Array(11).fill("potion20"))).toMatch(/10/);
    expect(() => startRun(poor, YUKAI, [])).toThrow();
  });

  it("rewards: clear = 90+collected, escape = collected, death = half", () => {
    expect(reward(YUKAI, { result: "clear", winCollected: 12, multiplier: 1, hand: [] })).toBe(102);
    expect(reward(YUKAI, { result: "escaped", winCollected: 12, multiplier: 1, hand: [] })).toBe(12);
    expect(reward(YUKAI, { result: "dead", winCollected: 12, multiplier: 1, hand: [] })).toBe(51);
  });

  it("finishing returns the hand to storage unless dead, and counts stats", () => {
    const s0 = { ...initialSave(), storage: [] as SaveV1["storage"] };
    const a = finishRun(s0, YUKAI, { result: "clear", winCollected: 0, multiplier: 1, hand: ["fire"] });
    expect(a.save.storage).toEqual(["fire"]);
    expect(a.save.win).toBe(190);
    expect(a.save.stats.clears).toBe(1);
    const b = finishRun(s0, YUKAI, { result: "dead", winCollected: 0, multiplier: 1, hand: ["fire"] });
    expect(b.save.storage).toEqual([]);
    expect(b.save.win).toBe(145);
    expect(b.save.stats.deaths).toBe(1);
  });

  it("storage overflow is reported and dropped", () => {
    const s0 = { ...initialSave(), storage: Array(STORAGE_CAP - 1).fill("potion20") as SaveV1["storage"] };
    const r = finishRun(s0, YUKAI, { result: "escaped", winCollected: 0, multiplier: 1, hand: ["fire", "thunder"] });
    expect(r.save.storage.length).toBe(STORAGE_CAP);
    expect(r.overflow).toEqual(["thunder"]);
  });

  it("shop: buy and sell", () => {
    const s0 = { ...initialSave(), storage: [] as SaveV1["storage"] };
    const a = buyCard(s0, "thunder");
    expect(a.error).toBeNull();
    expect(a.save.win).toBe(88);
    expect(a.save.storage).toEqual(["thunder"]);
    expect(buyCard(s0, "escape").error).toBe("非売品");
    expect(buyCard({ ...s0, win: 1 }, "fire").error).toMatch(/WIN/);
    const sold = sellCard(a.save, 0);
    expect(sold.win).toBe(94);
    expect(sold.storage).toEqual([]);
  });

  it("persists and reloads; garbage falls back to defaults", () => {
    const store = memStore();
    const s = { ...initialSave(), win: 555, storage: ["fire", "haste"] as SaveV1["storage"] };
    persist(store, s);
    expect(loadSave(store)).toEqual(s);
    store.data["monster_gate.save.v1"] = "{not json";
    expect(loadSave(store)).toEqual(initialSave());
    store.data["monster_gate.save.v1"] = JSON.stringify({ version: 1, win: 3, storage: ["fire", "bogus", 4] });
    expect(loadSave(store).storage).toEqual(["fire"]);
  });
});
