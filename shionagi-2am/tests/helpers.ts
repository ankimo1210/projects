import type { Sim } from "../src/sim/sim";

/** Top-down ASCII rendering of the nav grid (1 char = `scale` metres). */
export function asciiMap(sim: Sim, scale = 1, marks: { x: number; z: number; ch: string }[] = []): string {
  const b = sim.level.bounds;
  const cols = Math.ceil((b.x1 - b.x0) / scale);
  const rows = Math.ceil((b.z1 - b.z0) / scale);
  const grid: string[][] = [];
  for (let j = 0; j < rows; j++) {
    const row: string[] = [];
    for (let i = 0; i < cols; i++) {
      // a cell is "open" if any nav sample inside it is free
      let free = 0;
      let total = 0;
      for (let sj = 0; sj < 2; sj++) {
        for (let si = 0; si < 2; si++) {
          total++;
          if (sim.nav.isFree(b.x0 + (i + 0.25 + si * 0.5) * scale, b.z0 + (j + 0.25 + sj * 0.5) * scale)) free++;
        }
      }
      row.push(free === total ? "." : free > 0 ? ":" : "#");
    }
    grid.push(row);
  }
  const put = (x: number, z: number, ch: string): void => {
    const i = Math.floor((x - b.x0) / scale);
    const j = Math.floor((z - b.z0) / scale);
    const row = grid[j];
    if (row && i >= 0 && i < cols) row[i] = ch;
  };
  for (const e of sim.level.enemies) put(e.x, e.z, e.dormant ? "z" : "e");
  for (const it of sim.level.interactables) put(it.x, it.z, "?");
  put(sim.level.start.x, sim.level.start.z, "S");
  for (const m of marks) put(m.x, m.z, m.ch);
  return grid.map((r, j) => `${String(Math.round(b.z0 + j * scale)).padStart(5)} ${r.join("")}`).join("\n");
}
