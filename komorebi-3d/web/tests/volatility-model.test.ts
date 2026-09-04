import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  createDemoSurface,
  parseSurfaceCsv,
  toSurfaceCsv,
  nearestPoint,
  presets,
} from '../components/volatility/model.ts';

await test('demo units and ATM term structure have independently known values', () => {
  const grid = createDemoSurface(presets.equity.parameters);
  assert.equal(grid.moneyness.length, 25);
  assert.equal(grid.tenors.length, 24);
  assert.equal(grid.iv.length, 24);
  assert.equal(grid.iv[11][12], 0.2);
  assert.ok(Math.abs(grid.iv[2][12] - 0.185) < 1e-12);
  assert.deepEqual(grid.domain.iv, [0, 0.7]);
  for (const row of grid.iv)
    for (const iv of row) assert.ok(Number.isFinite(iv) && iv > 0 && iv < 0.7);
});

await test('unordered CSV preserves quote values and sorts actual tenor and moneyness axes', () => {
  const grid = parseSurfaceCsv(
    '\uFEFFtenor_years,moneyness,iv\r\n2,1.2,0.3\r\n0.25,0.8,0.4\r\n2,0.8,0.35\r\n0.25,1.2,0.2\r\n',
    'quotes.csv',
  );
  assert.deepEqual(grid.tenors, [0.25, 2]);
  assert.deepEqual(grid.moneyness, [0.8, 1.2]);
  assert.deepEqual(grid.iv, [
    [0.4, 0.2],
    [0.35, 0.3],
  ]);
  assert.equal(grid.source.kind, 'csv');
});

await test('rejects duplicate quotes, missing grid cells, invalid numbers and percent-unit mistakes', () => {
  const header = 'tenor_years,moneyness,iv\n';
  assert.throws(() => parseSurfaceCsv(header + '1,1,0.2\n1,1,0.3'), /重複/);
  assert.throws(
    () => parseSurfaceCsv(header + '1,1,0.2\n2,1,0.3\n2,1.2,0.25'),
    /欠損/,
  );
  for (const value of ['NaN', 'Infinity', '', '-0.2', '0', '25']) {
    assert.throws(() => parseSurfaceCsv(header + `1,1,${value}`), /IV|数値/);
  }
  assert.throws(() => parseSurfaceCsv('tenor,strike,vol\n1,100,20'), /列/);
});

await test('CSV round trip preserves every point without interpolation', () => {
  const original = createDemoSurface(presets.stress.parameters);
  const restored = parseSurfaceCsv(toSurfaceCsv(original));
  assert.deepEqual(restored.moneyness, original.moneyness);
  assert.deepEqual(restored.tenors, original.tenors);
  assert.deepEqual(restored.iv, original.iv);
});

await test('point lookup uses numeric coordinates on an irregular grid', () => {
  const grid = parseSurfaceCsv(
    'tenor_years,moneyness,iv\n0.1,0.8,0.2\n0.1,1,0.21\n0.1,1.8,0.22\n3,0.8,0.3\n3,1,0.31\n3,1.8,0.32',
  );
  assert.deepEqual(nearestPoint(grid, 1.1, 2.5), { row: 1, column: 1 });
});
