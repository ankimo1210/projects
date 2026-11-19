import { describe, expect, it } from "vitest";
import { Sim } from "../src/sim/sim";
import { asciiMap } from "./helpers";

function open(sim: Sim, o: { d1?: boolean; d2?: boolean; bridge?: boolean }): void {
  if (o.d1) sim.s.doors["D1"] = true;
  if (o.d2) sim.s.doors["D2"] = true;
  if (o.bridge) sim.s.bridge.state = "down";
  sim.syncDynamic();
}

const reach = (sim: Sim, x: number, z: number): boolean => {
  const mask = sim.nav.flood(sim.level.start.x, sim.level.start.z);
  const idx = sim.nav.index(x, z);
  return idx >= 0 && mask[idx] === 1;
};

describe("level", () => {
  it("keeps the player in the waiting hall until the staff door is opened", () => {
    const sim = new Sim();
    const mask = sim.nav.flood(sim.level.start.x, sim.level.start.z);
    let count = 0;
    for (let i = 0; i < mask.length; i++) {
      if (!mask[i]) continue;
      count++;
      const x = sim.nav.cx(i);
      const z = sim.nav.cz(i);
      expect(x > -14 && x < 6 && z > -14 && z < 0).toBe(true);
    }
    expect(count).toBeGreaterThan(1000);
  });

  it("gates progress: back door, then the bridge", () => {
    const sim = new Sim();
    open(sim, { d1: true });
    expect(reach(sim, 7.5, -12)).toBe(true); // staff corridor
    expect(reach(sim, 16, -12)).toBe(false); // lane
    open(sim, { d2: true });
    expect(reach(sim, 16, -12)).toBe(true);
    expect(reach(sim, -3, -60)).toBe(true); // main street (beside the box truck)
    expect(reach(sim, 18.4, -80)).toBe(true); // back alley
    expect(reach(sim, 9, -130.2)).toBe(true); // control panel
    expect(reach(sim, 24.25, -140)).toBe(false); // bridge deck
    expect(reach(sim, 24.25, -173.4)).toBe(false); // police station door
    open(sim, { bridge: true });
    expect(reach(sim, 24.25, -140)).toBe(true);
    expect(reach(sim, 24.25, -173.4)).toBe(true);
  });

  it("is sealed: nothing outside the town is reachable", () => {
    const sim = new Sim();
    open(sim, { d1: true, d2: true, bridge: true });
    const mask = sim.nav.flood(sim.level.start.x, sim.level.start.z);
    const outside: [number, number][] = [
      [-20, -60],
      [-20, -120],
      [0, -120],
      [36, -60],
      [45, -100],
      [0, 1.5],
      [-27, -180],
      [24, -189],
      [0, -140],
    ];
    for (const [x, z] of outside) {
      const idx = sim.nav.index(x, z);
      expect(mask[idx], `outside probe ${x},${z}`).toBe(0);
    }
    // every reachable cell lies in a named zone (with a small tolerance for doorways)
    for (let i = 0; i < mask.length; i++) {
      if (!mask[i]) continue;
      const x = sim.nav.cx(i);
      const z = sim.nav.cz(i);
      const ok = sim.level.zones.some((r) => x >= r.x0 - 0.4 && x <= r.x1 + 0.4 && z >= r.z0 - 0.4 && z <= r.z1 + 0.4);
      expect(ok, `cell ${x},${z} is outside every zone`).toBe(true);
    }
  });

  it("offers both routes through the shopping district", () => {
    const junction: [number, number] = [10, -107];
    // main street walled off: the alley still gets there
    const a = new Sim();
    open(a, { d1: true, d2: true });
    a.level.boxes.push({ x0: -5, z0: -90, x1: 5, z1: -40, y0: 0, y1: 3, solid: true, opaque: true, thin: false, ceil: false, on: true });
    a.syncDynamic();
    expect(reach(a, ...junction)).toBe(true);
    // alley walled off: the main street still gets there
    const b = new Sim();
    open(b, { d1: true, d2: true });
    b.level.boxes.push({ x0: 14, z0: -50, x1: 17, z1: -45, y0: 0, y1: 3, solid: true, opaque: true, thin: false, ceil: false, on: true });
    b.level.boxes.push({ x0: 17, z0: -100, x1: 20, z1: -95, y0: 0, y1: 3, solid: true, opaque: true, thin: false, ceil: false, on: true });
    b.syncDynamic();
    expect(reach(b, ...junction)).toBe(true);
    // both walled off: no way through
    b.level.boxes.push({ x0: -5, z0: -103, x1: 5, z1: -101, y0: 0, y1: 3, solid: true, opaque: true, thin: false, ceil: false, on: true });
    b.syncDynamic();
    expect(reach(b, ...junction)).toBe(false);
  });

  it("places everything on walkable ground", () => {
    const sim = new Sim();
    open(sim, { d1: true, d2: true, bridge: true });
    const mask = sim.nav.flood(sim.level.start.x, sim.level.start.z);
    const reachable = (x: number, z: number, r: number): boolean => {
      for (let dz = -r; dz <= r; dz += 0.25) {
        for (let dx = -r; dx <= r; dx += 0.25) {
          if (Math.hypot(dx, dz) > r) continue;
          const idx = sim.nav.index(x + dx, z + dz);
          if (idx >= 0 && mask[idx]) return true;
        }
      }
      return false;
    };
    for (const it of sim.level.interactables) expect(reachable(it.x, it.z, it.r - 0.3), `interactable ${it.id}`).toBe(true);
    for (const e of sim.level.enemies) {
      expect(sim.nav.isFree(e.x, e.z), `enemy ${e.id} spawn`).toBe(true);
      for (const p of e.patrol) expect(sim.nav.isFree(p.x, p.z), `enemy ${e.id} patrol`).toBe(true);
    }
    for (const cp of sim.level.checkpoints) expect(sim.nav.isFree(cp.x, cp.z), `checkpoint ${cp.id}`).toBe(true);
    // the plaza figures cannot get into the terminal before the player opens up
    const closed = new Sim();
    const plaza = closed.nav.flood(0, -20);
    expect(plaza[closed.nav.index(sim.level.start.x, sim.level.start.z)]).toBe(0);
  });

  it("renders a walkable map (set VITE_DUMP_MAP=1 to print it)", () => {
    const sim = new Sim();
    open(sim, { d1: true, d2: true, bridge: true });
    const map = asciiMap(sim, 1);
    expect(map.split("\n").length).toBeGreaterThan(150);
    expect(map).toContain("S");
    if (import.meta.env["VITE_DUMP_MAP"]) console.log(`\n${map}`);
  });
});
