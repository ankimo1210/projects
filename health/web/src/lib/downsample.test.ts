import { describe, expect, it } from "vitest";
import { downsampleMinMax, sampleWindow, type Point } from "./downsample";

describe("display sampling", () => {
  it("preserves endpoints, both extrema, order and source without exceeding the gap-free budget", () => {
    const input = Array.from({ length: 10000 }, (_, x) => ({
      x: x * x,
      y: x === 5011 ? 190 : x === 5012 ? -80 : 60,
    }));
    const original = structuredClone(input);
    const result = downsampleMinMax(input, 2000);
    expect(input).toEqual(original);
    expect(result[0]).toEqual(input[0]);
    expect(result.at(-1)).toEqual(input.at(-1));
    expect(result).toContainEqual(input[5011]);
    expect(result).toContainEqual(input[5012]);
    expect(result.length).toBeLessThanOrEqual(2000);
    expect(result.every((p, i) => i === 0 || p.x > result[i - 1].x)).toBe(true);
  });
  it("keeps gap boundaries even when boundaries exceed budget", () => {
    const input: Point[] = [
      { x: 0, y: 2 },
      { x: 1, y: 3 },
      { x: 2, y: null },
      { x: 3, y: null },
      { x: 4, y: 9 },
      { x: 5, y: 8 },
      { x: 6, y: null },
      { x: 7, y: -2 },
    ];
    expect(downsampleMinMax(input, 3)).toEqual(input);
  });
  it("handles empty, singleton, flat values and rejects reversed input / invalid budgets", () => {
    expect(downsampleMinMax([])).toEqual([]);
    expect(downsampleMinMax([{ x: 3, y: 0 }])).toEqual([{ x: 3, y: 0 }]);
    const flat = Array.from({ length: 50 }, (_, x) => ({ x, y: 0 }));
    const result = downsampleMinMax(flat, 10);
    expect(result[0]).toEqual(flat[0]);
    expect(result.at(-1)).toEqual(flat.at(-1));
    expect(result.length).toBeLessThanOrEqual(10);
    expect(() =>
      downsampleMinMax([
        { x: 2, y: 1 },
        { x: 1, y: 2 },
      ]),
    ).toThrow();
    expect(() => downsampleMinMax(flat, 1)).toThrow();
  });
  it("zoom recomputes from full resolution, recovering previously hidden points", () => {
    const points = Array.from({ length: 36500 }, (_, x) => ({
      x: x * 2000000,
      y: 60 + Math.sin(x),
    }));
    const original = structuredClone(points);
    const wide = sampleWindow(points, 0, 73000000000, 100);
    const zoom = sampleWindow(points, 10000000000, 10020000000, 100);
    expect(zoom.sourceCount).toBe(11);
    expect(zoom.points).toEqual(points.slice(5000, 5011));
    expect(zoom.points.some((p) => !wide.points.includes(p))).toBe(true);
    expect(points).toEqual(original);
    expect(zoom.min).toBe(
      Math.min(...points.slice(5000, 5011).map((p) => p.y)),
    );
  });
  it("shows a missing marker for a known large time jump without mutating the full series", () => {
    const points = [
      { x: 0, y: 2 },
      { x: 1000000, y: 3 },
      { x: 900000000, y: 4 },
    ];
    const window = sampleWindow(points, 0, 900000000, 2000, 300000000);
    expect(window.sourceCount).toBe(3);
    expect(window.points.some((p) => p.y === null)).toBe(true);
    expect(points).toHaveLength(3);
  });
});

it("preserves both extrema of a tiny segment beside a long segment", () => {
  const short: Point[] = [
    { x: 0, y: 60 },
    { x: 1, y: 190 },
    { x: 2, y: -80 },
    { x: 3, y: 60 },
    { x: 4, y: null },
  ];
  const input = [
    ...short,
    ...Array.from({ length: 10000 }, (_, i) => ({ x: i + 5, y: 60 })),
  ];
  const original = structuredClone(input);
  const sampled = downsampleMinMax(input, 2000);
  expect(sampled).toContainEqual({ x: 1, y: 190 });
  expect(sampled).toContainEqual({ x: 2, y: -80 });
  expect(sampled).toContainEqual({ x: 4, y: null });
  expect(input).toEqual(original);
  expect(sampled.every((p, i) => i === 0 || p.x > sampled[i - 1].x)).toBe(true);
});
it("prioritizes every finite segment min/max over the requested budget", () => {
  const input: Point[] = Array.from({ length: 8 }, (_, i) => [
    { x: i * 10, y: 0 },
    { x: i * 10 + 1, y: 100 + i },
    { x: i * 10 + 2, y: -100 - i },
    { x: i * 10 + 3, y: 0 },
    { x: i * 10 + 4, y: null },
  ]).flat();
  const sampled = downsampleMinMax(input, 4);
  for (let i = 0; i < 8; i++) {
    expect(sampled).toContainEqual({ x: i * 10 + 1, y: 100 + i });
    expect(sampled).toContainEqual({ x: i * 10 + 2, y: -100 - i });
  }
  expect(sampled.length).toBeGreaterThan(4);
  expect(sampled).toEqual(input);
});
