/** Deterministic PRNG (mulberry32) so world scatter is stable across reloads. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/** Random point inside a circle (uniform by area). */
export function pointInCircle(
  rand: () => number,
  cx: number,
  cz: number,
  radius: number,
): [number, number] {
  const r = radius * Math.sqrt(rand())
  const theta = rand() * Math.PI * 2
  return [cx + r * Math.cos(theta), cz + r * Math.sin(theta)]
}
