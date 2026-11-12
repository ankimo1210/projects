'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/vector.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };
function close(actual, expected, tolerance = 4e-12) {
  assert(Number.isFinite(actual), `nonfinite value: ${actual}`);
  assert(Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
}
function vectorClose(actual, expected) { assert.equal(actual.length, expected.length); actual.forEach((v, i) => close(v, expected[i])); }

// Antiderivatives and the sum of odd squares independently give these
// midpoint formulas; production must sample F(gamma(t)) dot gamma'(t).
test('work midpoint sums match closed forms for four paths, both fields and both orientations', () => {
  const state = api('workState');
  const rotation = { straight: 0, parabola: 1 / 3, 'x-first': 1, 'y-first': -1 };
  for (const field of ['gradient', 'rotation']) for (const path of Object.keys(rotation)) {
    for (let n = 16; n <= 128; n += 16) for (const orientation of [-1, 1]) {
      const input = Object.freeze({ field, path, n, orientation }), s = state(input);
      const exact = field === 'gradient' ? 1 : rotation[path];
      const midpoint = path === 'parabola' ? (field === 'gradient' ? 1 - 1 / (4 * n * n) : 1 / 3 - 1 / (12 * n * n)) : exact;
      close(s.exact, orientation * exact); close(s.numeric, orientation * midpoint);
      close(s.error, Math.abs(midpoint - exact));
      assert.equal(s.pieces, path.endsWith('first') ? 2 : 1);
      assert.equal(s.samples, n * s.pieces); assert.equal(s.domainState, 'defined');
      assert.deepEqual(s.start, orientation === 1 ? [0, 0] : [1, 1]);
      assert.deepEqual(s.end, orientation === 1 ? [1, 1] : [0, 0]);
    }
  }
});

test('flux separates positive area from signed flux and agrees with a cross-product oracle', () => {
  const state = api('fluxState');
  for (let ai = -4; ai <= 4; ai++) for (let bi = -4; bi <= 4; bi++) {
    for (let ci = -8; ci <= 8; ci++) for (const orientation of [-1, 1]) {
      const a = ai / 4, b = bi / 4, c = ci / 4, s = state(Object.freeze({ a, b, c, orientation }));
      const cross = [s.tangentU[1] * s.tangentV[2] - s.tangentU[2] * s.tangentV[1], s.tangentU[2] * s.tangentV[0] - s.tangentU[0] * s.tangentV[2], s.tangentU[0] * s.tangentV[1] - s.tangentU[1] * s.tangentV[0]];
      vectorClose(cross, [-a, -b, 1]);
      vectorClose(s.normalArea, cross.map(v => orientation * v));
      close(s.area, 4 * Math.hypot(...cross)); assert(s.area > 0); close(s.projectedArea, 4);
      vectorClose(s.unitNormal, cross.map(v => orientation * v / Math.hypot(...cross)));
      close(s.normalDensity * s.area, s.flux); close(s.flux, orientation * 4 * c);
      assert.equal(s.domainState, 'defined');
      if (c === 0) { assert.equal(s.flux, 0); assert.equal(s.normalDensity, 0); }
    }
  }
  // API accepts finite parameter values between the UI ticks.
  close(state({ a: .13, b: -.07, c: .31, orientation: 1 }).flux, 1.24);
});

// Integral of r+2 alpha r^3 gives pi(1+alpha). The independent midpoint
// error is -pi alpha/(2n^2); height is absent because curl has only z component.
test('Stokes radial midpoint sums match the independent cubic formula while height changes only the graph', () => {
  const state = api('stokesState');
  for (const height of [-1.5, -.7, 0, .75, 1.5]) for (let ai = -4; ai <= 4; ai++) {
    for (let n = 8; n <= 128; n += 8) for (const orientation of [-1, 1]) {
      const alpha = ai / 4, s = state(Object.freeze({ height, alpha, n, orientation }));
      const exact = orientation * Math.PI * (1 + alpha);
      close(s.circulationExact, exact); close(s.surfaceExact, exact);
      close(s.surfaceNumeric, exact - orientation * Math.PI * alpha / (2 * n * n));
      close(s.error, Math.PI * Math.abs(alpha) / (2 * n * n));
      assert.equal(s.regularGraph, true); assert.equal(s.boundaryRadius, 1); assert.equal(s.boundaryHeight, 0);
      vectorClose(s.centerNormalArea, [0, 0, orientation]); assert.equal(s.domainState, 'defined');
      if (alpha === -1) { assert.equal(s.surfaceExact, 0); assert.notEqual(s.surfaceNumeric, 0); }
    }
  }
});

test('refinement reduces the nonzero midpoint error by four and orientation negates integral values', () => {
  for (const [name, input, numeric, exact] of [
    ['workState', { field: 'rotation', path: 'parabola' }, 'numeric', 'exact'],
    ['stokesState', { height: -1.5, alpha: -1 }, 'surfaceNumeric', 'surfaceExact']
  ]) {
    const state = api(name), coarse = state({ ...input, n: 16, orientation: 1 }), fine = state({ ...input, n: 32, orientation: 1 });
    close(coarse.error / fine.error, 4, 1e-9);
    const reverse = state({ ...input, n: 32, orientation: -1 });
    close(reverse[numeric], -fine[numeric]); close(reverse[exact], -fine[exact]); close(reverse.error, fine.error);
  }
});

test('all vector APIs reject absent, nonfinite, out-of-domain and unsupported input', () => {
  const badTypes = [undefined, null, false, '1', NaN, Infinity, -Infinity, [], {}];
  const specifications = [
    ['workState', { field: 'gradient', path: 'straight', orientation: 1, n: 16 }, { orientation: [-2, 0, .5, 2], n: [0, 15, 17, 32.5, 129] }],
    ['fluxState', { a: 0, b: 0, c: 1, orientation: 1 }, { a: [-1.01, 1.01], b: [-1.01, 1.01], c: [-2.01, 2.01], orientation: [-2, 0, .5, 2] }],
    ['stokesState', { height: 0, alpha: 0, orientation: 1, n: 8 }, { height: [-1.51, 1.51], alpha: [-1.01, 1.01], orientation: [-2, 0, .5, 2], n: [0, 7, 9, 16.5, 129] }]
  ];
  for (const [name, valid, invalid] of specifications) {
    const state = api(name);
    for (const bad of badTypes) assert.throws(() => state(bad), TypeError);
    for (const key of Object.keys(valid).filter(k => typeof valid[k] === 'number')) for (const bad of badTypes) assert.throws(() => state({ ...valid, [key]: bad }), TypeError);
    for (const [key, values] of Object.entries(invalid)) for (const value of values) assert.throws(() => state({ ...valid, [key]: value }), RangeError);
  }
  for (const key of ['field', 'path']) {
    for (const value of [undefined, null, 1, false, [], {}]) assert.throws(() => api('workState')({ field: 'gradient', path: 'straight', orientation: 1, n: 16, [key]: value }), TypeError);
    assert.throws(() => api('workState')({ field: 'gradient', path: 'straight', orientation: 1, n: 16, [key]: 'unknown' }), RangeError);
  }
});

test('classic script and Node expose one frozen namespace and preserve existing globals', () => {
  assert(fs.existsSync(source), 'vector module must exist');
  const sentinel = Object.freeze({ untouched: true }), context = vm.createContext({ MathComplex: sentinel, MathProbability: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathComplex, sentinel); assert.equal(context.MathProbability, sentinel);
  assert(Object.isFrozen(context.MathVector)); assert(Object.isFrozen(math));
  close(context.MathVector.workState({ field: 'rotation', path: 'x-first', orientation: -1, n: 16 }).exact, -1);
});
