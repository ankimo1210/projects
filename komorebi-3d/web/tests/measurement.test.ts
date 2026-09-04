import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createFrameMeasurement } from '../components/orbit/measurement.ts';

await test('excludes loading and warmup, computes throughput and nearest-rank p95', () => {
  const collect = createFrameMeasurement(100, 100);
  assert.equal(collect(3000), null);
  assert.equal(collect(3050), null);
  assert.equal(collect(3100), null);
  assert.equal(collect(3110), null);
  assert.equal(collect(3130), null);
  assert.equal(collect(3160), null);
  assert.deepEqual(collect(3200), {
    fps: 40,
    p95Ms: 40,
    frames: 4,
    durationMs: 100,
  });
});

await test('does not report a result without enough measured time', () => {
  const collect = createFrameMeasurement(100, 4000);
  assert.equal(collect(0), null);
  assert.equal(collect(100), null);
  assert.equal(collect(110), null);
  assert.equal(collect(120), null);
});
