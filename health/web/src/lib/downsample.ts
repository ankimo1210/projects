export type Point = { x: number; y: number | null };
/** Display only. Every segment's endpoints and min/max take priority over target. */
export function downsampleMinMax(
  points: readonly Point[],
  target = 2000,
): Point[] {
  if (!Number.isInteger(target) || target < 2)
    throw new RangeError("target must be an integer >= 2");
  for (let i = 0; i < points.length; i++)
    if (
      !Number.isFinite(points[i].x) ||
      (points[i].y !== null && !Number.isFinite(points[i].y)) ||
      (i > 0 && points[i].x < points[i - 1].x)
    )
      throw new RangeError("points must be finite and ordered");
  if (points.length <= target) return [...points];
  const keep = new Set<number>([0, points.length - 1]);
  const segments: [number, number][] = [];
  let start = 0;
  for (let i = 1; i <= points.length; i++) {
    if (
      i === points.length ||
      (points[i].y === null) !== (points[i - 1].y === null)
    ) {
      keep.add(start);
      keep.add(i - 1);
      if (points[start].y !== null) segments.push([start, i - 1]);
      start = i;
    }
  }
  // Reserve each segment's extrema before distributing the remaining budget.
  // A short isolated spike must not disappear when proportional allocation is zero.
  for (const [a, b] of segments) {
    let min = a,
      max = a;
    for (let i = a + 1; i <= b; i++) {
      if (points[i].y! < points[min].y!) min = i;
      if (points[i].y! > points[max].y!) max = i;
    }
    keep.add(min);
    keep.add(max);
  }
  const interior = segments.reduce(
    (n, [a, b]) => n + Math.max(0, b - a - 1),
    0,
  );
  const buckets = Math.floor(Math.max(0, target - keep.size) / 2);
  for (const [a, b] of segments) {
    const n = b - a - 1;
    const allocation = interior ? Math.floor((buckets * n) / interior) : 0;
    for (let k = 0; k < allocation; k++) {
      const lo = a + 1 + Math.floor((k * n) / allocation),
        hi = a + 1 + Math.floor(((k + 1) * n) / allocation);
      let min = lo,
        max = lo;
      for (let j = lo + 1; j < hi; j++) {
        if (points[j].y! < points[min].y!) min = j;
        if (points[j].y! > points[max].y!) max = j;
      }
      keep.add(min);
      keep.add(max);
    }
  }
  return [...keep].sort((a, b) => a - b).map((i) => points[i]);
}
/** Filter original full-resolution points on every zoom; never sample the preview. */
export function sampleWindow(
  points: readonly Point[],
  start: number,
  end: number,
  target = 2000,
  gap = 300000000,
) {
  const visible = points.filter((p) => p.x >= start && p.x <= end);
  const withGaps: Point[] = [];
  let min: number | null = null,
    max: number | null = null;
  for (const point of visible) {
    const previous = withGaps.at(-1);
    if (
      previous &&
      point.x - previous.x > gap &&
      previous.y !== null &&
      point.y !== null
    )
      withGaps.push({ x: previous.x + 1, y: null });
    withGaps.push(point);
    if (point.y !== null) {
      min = min === null ? point.y : Math.min(min, point.y);
      max = max === null ? point.y : Math.max(max, point.y);
    }
  }
  return {
    points: downsampleMinMax(withGaps, target),
    sourceCount: visible.length,
    min,
    max,
  };
}
