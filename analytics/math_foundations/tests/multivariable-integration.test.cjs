'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assets = path.join(__dirname, '../assets');
const source = path.join(assets, 'multivariable-integration.js');
const math = fs.existsSync(source) ? require(source) : {};
function api(name) { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; }
function close(actual, expected) { assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= 1e-12 * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`); }
const polarInput = extra => ({ innerRadius: .5, radialWidth: .5, angleRad: 0, angularWidth: Math.PI / 2, ...extra });

test('rectangle known n=1 and n=2 sums match hand calculation', () => {
  const state = api('rectangleSumState');
  for (const [n, lower, upper, midpoint] of [[1, 0, 2, .5], [2, .25, 1.25, .625]]) {
    for (const rule of ['lower', 'upper', 'midpoint']) {
      const s = state(n, rule);
      assert.equal(s.n, n); assert.equal(s.rule, rule);
      close(s.lower, lower); close(s.upper, upper); close(s.midpoint, midpoint);
      close(s.sum, { lower, upper, midpoint }[rule]); close(s.integral, 2 / 3); close(s.cellArea, 1 / (n * n)); close(s.gap, 2 / n);
    }
  }
});

test('all rectangle sizes return correct representative cells and independently known sums', () => {
  const state = api('rectangleSumState');
  for (let n = 1; n <= 32; n++) for (const [rule, offset] of [['lower', 0], ['upper', 1], ['midpoint', .5]]) {
    const s = state(n, rule);
    assert.equal(s.cells.length, n * n);
    let total = 0;
    const indices = new Set();
    for (const cell of s.cells) {
      assert(Number.isInteger(cell.i) && cell.i >= 0 && cell.i < n);
      assert(Number.isInteger(cell.j) && cell.j >= 0 && cell.j < n);
      indices.add(`${cell.i},${cell.j}`);
      close(cell.x, (cell.i + offset) / n); close(cell.y, (cell.j + offset) / n);
      close(cell.density, cell.x ** 2 + cell.y ** 2);
      close(cell.weightedValue, cell.density / (n * n)); total += cell.weightedValue;
    }
    assert.equal(indices.size, n * n); close(total, s.sum);
    close(s.lower, (n - 1) * (2 * n - 1) / (3 * n * n));
    close(s.upper, (n + 1) * (2 * n + 1) / (3 * n * n));
    close(s.midpoint, 2 / 3 - 1 / (6 * n * n));
    close(s.sum, s[rule]); assert(s.lower <= s.integral && s.integral <= s.upper);
  }
  assert(api('rectangleSumState')(20, 'midpoint').gap <= .1);
});

test('rectangle rejects wrong types, nonintegral/outside counts, and unknown rules', () => {
  const state = api('rectangleSumState');
  for (const value of [null, undefined, '4', NaN, Infinity, -Infinity, true, {}]) assert.throws(() => state(value, 'midpoint'), TypeError);
  for (const value of [0, -1, 33, 4.5, 1 - 1e-6, 32 + 1e-6]) assert.throws(() => state(value, 'midpoint'), RangeError);
  for (const rule of [null, undefined, 1, true, {}]) assert.throws(() => state(4, rule), TypeError);
  for (const rule of ['', 'trapezoid', 'Midpoint']) assert.throws(() => state(4, rule), RangeError);
});

test('polar annular cells have hand-calculated areas, coordinate products and ratios', () => {
  const state = api('polarCellState');
  for (const [innerRadius, area, ratio] of [[0, Math.PI / 16, .25], [.5, 3 * Math.PI / 16, .75], [1, 5 * Math.PI / 16, 1.25]]) {
    const s = state(polarInput({ innerRadius }));
    close(s.exactArea, area); close(s.coordinateProduct, Math.PI / 4); close(s.areaRatio, ratio);
    close(s.midpointRadius, ratio); close(s.jacobianAtMidpoint, ratio);
    close(s.outerRadius, innerRadius + .5); close(s.endAngle, Math.PI / 2);
  }
  const s = state(polarInput({ angleRad: -Math.PI / 2 }));
  for (const [i, x, y] of [[0, 0, -.5], [1, 0, -1], [2, 1, 0], [3, .5, 0]]) { close(s.corners[i].x, x); close(s.corners[i].y, y); }
});

test('polar accepts all safe endpoints, preserves frozen input and does not reuse results', () => {
  const state = api('polarCellState');
  for (const innerRadius of [0, 1.5]) for (const radialWidth of [.1, .5]) for (const angleRad of [-Math.PI, 0, Math.PI]) for (const angularWidth of [Math.PI / 36, Math.PI / 2]) {
    const input = Object.freeze({ innerRadius, radialWidth, angleRad, angularWidth });
    const s = state(input);
    for (const key of Object.keys(input)) assert.equal(s[key], input[key]);
    assert(s.exactArea > 0 && s.coordinateProduct > 0); close(s.exactArea / s.coordinateProduct, s.midpointRadius);
    assert.equal(s.corners.length, 4);
    for (const p of s.corners) assert(Number.isFinite(p.x) && Number.isFinite(p.y) && Math.hypot(p.x, p.y) <= 2 + 1e-12);
  }
  const a = state(polarInput()), b = state(polarInput()); a.corners[0].x = 123; close(b.corners[0].x, .5);
});

test('polar rejects missing or incorrectly typed input without coercion', () => {
  const state = api('polarCellState');
  for (const input of [undefined, null, 1, '1', [], {}, true]) assert.throws(() => state(input), TypeError);
  for (const key of ['innerRadius', 'radialWidth', 'angleRad', 'angularWidth']) {
    for (const bad of [undefined, null, '0.5', NaN, Infinity, -Infinity, true, {}]) assert.throws(() => state(polarInput({ [key]: bad })), TypeError);
  }
});

test('polar rejects finite values just beyond all supported bounds', () => {
  const state = api('polarCellState');
  for (const [key, values] of Object.entries({ innerRadius: [-1e-6, 1.500001], radialWidth: [.099999, .500001], angleRad: [-Math.PI - 1e-6, Math.PI + 1e-6], angularWidth: [Math.PI / 36 - 1e-6, Math.PI / 2 + 1e-6] })) {
    for (const value of values) assert.throws(() => state(polarInput({ [key]: value })), RangeError);
  }
});

test('new UMD coexists with every available existing Math namespace', () => {
  assert(fs.existsSync(source), 'integration module must exist');
  const context = vm.createContext({});
  const existing = [['math.js', 'MathFoundations'], ['calculus.js', 'MathCalculus'], ['linear.js', 'MathLinear'], ['multivariable.js', 'MathMultivariable'], ['multivariable-middle.js', 'MathMultivariableMiddle']].filter(([name]) => fs.existsSync(path.join(assets, name)));
  for (const [file] of existing) vm.runInContext(fs.readFileSync(path.join(assets, file), 'utf8'), context);
  const snapshots = existing.map(([, name]) => [name, context[name], Object.keys(context[name])]);
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  for (const [name, object, keys] of snapshots) { assert.equal(context[name], object); assert.deepEqual(Object.keys(context[name]), keys); }
  const apiObject = context.MathMultivariableIntegration;
  assert.deepEqual(Object.keys(apiObject).sort(), ['polarCellState', 'rectangleSumState']); assert(Object.isFrozen(apiObject));
  close(apiObject.rectangleSumState(2, 'midpoint').sum, .625); close(apiObject.polarCellState(polarInput()).exactArea, 3 * Math.PI / 16);
});
