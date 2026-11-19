import { describe, expect, it } from "vitest";
import { Bot, runBot } from "../src/dev/bot";
import type { BotOptions, RouteName, RunResult } from "../src/dev/bot";
import { Sim } from "../src/sim/sim";

const verbose = Boolean(import.meta.env["VITE_ROUTE_LOG"]);

function play(route: RouteName, opts: BotOptions = {}, seed?: number, quiet = false): RunResult {
  const sim = seed === undefined ? new Sim() : new Sim(seed);
  const res = runBot(sim, new Bot(route, opts), 900);
  if (!quiet && (verbose || !res.cleared)) {
    console.log(
      `--- ${route} ${JSON.stringify(opts)} seed=${seed ?? "default"}: ${res.cleared ? "CLEAR" : "NOT CLEARED"} ` +
        `t=${res.time.toFixed(1)}s hp=${res.hp} ammo=${res.ammo} at (${res.x.toFixed(1)}, ${res.z.toFixed(1)}) ` +
        `leg="${res.lastLeg}" held=${res.held.toFixed(0)}s closest=${JSON.stringify(res.closest)}\n` +
        `${JSON.stringify(res.stats)}\n${res.events.join("\n")}`,
    );
  }
  return res;
}

describe("scripted playthroughs", () => {
  it("normal route: main street with the revolver reaches the station doors", () => {
    const res = play("normal");
    expect(res.cleared).toBe(true);
    expect(res.hasGun).toBe(true);
    expect(res.stats.shots).toBeGreaterThan(0);
    expect(res.stats.deaths).toBe(0);
  });

  it("no-ammo route: back alley, never fires, reaches the station doors", () => {
    const res = play("pacifist");
    expect(res.cleared).toBe(true);
    expect(res.stats.shots).toBe(0);
    expect(res.hasGun).toBe(false);
    expect(res.stats.deaths).toBe(0);
  });

  describe("the footbridge: three ways through while it comes down", () => {
    /** What happened between the panel being thrown and the far bank. */
    const atBridge = (res: RunResult): string[] => {
      const a = res.events.findIndex((e) => e.includes("bridge start"));
      const b = res.events.findIndex((e) => e.includes("checkpoint forecourt"));
      expect(a).toBeGreaterThanOrEqual(0);
      expect(b).toBeGreaterThan(a);
      return res.events.slice(a, b);
    };

    it("wait in cover: nobody notices", () => {
      const res = play("pacifist", { bridge: "hide" });
      const ev = atBridge(res);
      expect(res.cleared).toBe(true);
      expect(ev.some((e) => e.includes("spotted by"))).toBe(false);
      expect(res.stats.shots).toBe(0);
      expect(res.stats.deaths).toBe(0);
    });

    it("draw them off and go round: seen, chased, never fires", () => {
      const res = play("pacifist", { bridge: "lure" });
      const ev = atBridge(res);
      expect(res.cleared).toBe(true);
      expect(ev.some((e) => e.includes("spotted by"))).toBe(true);
      expect(res.stats.shots).toBe(0);
      expect(res.stats.deaths).toBe(0);
    });

    it("shoot the way open: holds the bridge head with the revolver", () => {
      const res = play("normal", { aim: "head", bridge: "shoot" });
      const ev = atBridge(res);
      expect(res.cleared).toBe(true);
      expect(ev.some((e) => e.includes("shot →"))).toBe(true);
      expect(res.stats.kills).toBeGreaterThan(0);
      expect(res.stats.deaths).toBe(0);
    });
  });

  // Not a pass/fail gate on its own numbers: prints how the routes hold up when
  // the dice fall differently (patrol pauses, where the drowned look, bullet spread).
  it("sweep: other seeds and sloppier aim", () => {
    const rows: string[] = [];
    const cases: [RouteName, BotOptions][] = [
      ["normal", { aim: "body" }],
      ["normal", { aim: "head" }],
      ["pacifist", {}],
      ["pacifist", { bridge: "lure" }],
      ["normal", { aim: "head", bridge: "shoot" }],
    ];
    for (const [route, opts] of cases) {
      let clears = 0;
      let clean = 0;
      let deaths = 0;
      let damage = 0;
      let tSum = 0;
      const N = 24;
      const bad: string[] = [];
      for (let k = 0; k < N; k++) {
        const seed = 1000 + k * 7919;
        const r = play(route, opts, seed, true);
        if (r.cleared) clears++;
        if (r.cleared && r.stats.deaths === 0) clean++;
        deaths += r.stats.deaths;
        damage += r.stats.damage;
        tSum += r.time;
        if (!r.cleared || r.stats.deaths > 0) bad.push(`${seed}:${r.cleared ? "" : "STUCK@" + r.lastLeg + " "}d${r.stats.deaths}`);
      }
      rows.push(
        `${route} ${JSON.stringify(opts)}: cleared ${clears}/${N}, without dying ${clean}/${N}, deaths ${deaths}, ` +
          `mean damage ${(damage / N).toFixed(0)}, mean time ${(tSum / N).toFixed(0)}s${bad.length ? "  [" + bad.join(" ") + "]" : ""}`,
      );
      expect(clears).toBe(N);
    }
    console.log(rows.join("\n"));
  });
});
