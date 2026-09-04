export type FrameMeasurement = {
  fps: number;
  p95Ms: number;
  frames: number;
  durationMs: number;
};

// Frame-start intervals include the previous frame's CPU/GPU scheduling time.
// Start the clock only after the scene and environment are ready.
export function createFrameMeasurement(warmupMs = 1000, sampleMs = 4000) {
  let first: number | null = null;
  let previous: number | null = null;
  let durationMs = 0;
  const intervals: number[] = [];
  return (timestamp: number): FrameMeasurement | null => {
    first ??= timestamp;
    if (timestamp - first < warmupMs) return null;
    if (previous === null) {
      previous = timestamp;
      return null;
    }
    const delta = timestamp - previous;
    previous = timestamp;
    if (delta <= 0) return null;
    intervals.push(delta);
    durationMs += delta;
    if (durationMs < sampleMs) return null;
    const sorted = [...intervals].sort((a, b) => a - b);
    return {
      fps: (intervals.length * 1000) / durationMs,
      p95Ms: sorted[Math.ceil(sorted.length * 0.95) - 1],
      frames: intervals.length,
      durationMs,
    };
  };
}
