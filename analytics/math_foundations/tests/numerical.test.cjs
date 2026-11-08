'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/numerical.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };
function close(a, b, tolerance = 5e-12) { assert(Number.isFinite(a)); assert(Math.abs(a - b) <= tolerance * Math.max(1, Math.abs(b)), `${a} != ${b}`); }
const polynomial = (name, x) => name === 'square' ? x * x - 2 : x * x * x - 2 * x + 2;

// Replacing sign selection or the final midpoint breaks inclusion and the
// dyadic width, independently of the implementation's iteration history.
test('bisection retains a sign-changing interval with an a priori error certificate', () => {
  const state = api('rootState');
  for (const name of ['square', 'cycle']) for (let steps = 0; steps <= 12; steps++) {
    const s = state(Object.freeze({ function: name, method: 'bisection', x0: 0, steps }));
    assert.equal(s.intervalGuaranteed, true); assert.equal(s.status, 'bracket');
    const [a, b] = s.bracket;
    assert(polynomial(name, a) * polynomial(name, b) <= 0);
    close(b - a, 2 / 2 ** steps); close(s.bound, 1 / 2 ** steps);
    close(s.estimate, (a + b) / 2); close(s.residual, polynomial(name, s.estimate));
    if (name === 'square') assert(Math.abs(s.estimate - Math.SQRT2) <= s.bound);
  }
});

test('Newton distinguishes a finite estimate, a zero derivative and a nonconverging cycle', () => {
  const state = api('rootState');
  const initial = state({ function: 'square', method: 'newton', x0: 0, steps: 0 });
  assert.equal(initial.estimate, 0); assert.equal(initial.bound, null); assert.equal(initial.status, 'steps');
  const flat = state({ function: 'square', method: 'newton', x0: 0, steps: 1 });
  assert.equal(flat.status, 'derivative-zero'); assert.equal(flat.estimate, 0); assert.equal(flat.iterations, 0);
  const one = state({ function: 'square', method: 'newton', x0: 1, steps: 1 });
  assert.equal(one.estimate, 1.5); assert.equal(one.intervalGuaranteed, false); assert.equal(one.bracket, null);
  for (let steps = 0; steps <= 12; steps++) {
    const cycle = state({ function: 'cycle', method: 'newton', x0: 0, steps });
    assert.equal(cycle.estimate, steps % 2); assert.equal(cycle.residual, steps % 2 ? 1 : 2);
    assert.equal(cycle.bound, null);
  }
  for (const x0 of [-2, -1, .5, 1, 2]) {
    const s = state({ function: 'square', method: 'newton', x0, steps: 8 });
    close(Math.abs(s.estimate), Math.SQRT2); assert.equal(s.bound, null);
  }
  const nearHorizontal = Math.sqrt(2 / 3) + 1e-9;
  const guarded = state({ function: 'cycle', method: 'newton', x0: nearHorizontal, steps: 1 });
  assert.equal(guarded.status, 'display-limit'); assert.equal(guarded.estimate, nearHorizontal);
  assert.equal(guarded.iterations, 0); assert.equal(guarded.bracket, null);
  for (const name of ['square', 'cycle']) for (const method of ['bisection', 'newton']) for (let i = -20; i <= 20; i++) for (let steps = 0; steps <= 12; steps++) {
    const s = state({ function: name, method, x0: i / 10, steps });
    assert(Number.isFinite(s.estimate)); assert(Number.isFinite(s.residual));
    assert(s.iterations <= steps); assert(s.history.every(p => Number.isFinite(p.x) && Number.isFinite(p.residual)));
  }
});

// expm1 avoids the subtraction used in production. The discrepancy of a
// floating difference from this real-arithmetic expression is allowed to
// grow with 1/h; it must remain within a conservative rounding scale.
test('difference formulas match independent exponential identities and truncation orders', () => {
  const state = api('differenceState');
  for (let ix = -20; ix <= 20; ix++) for (let exponent = 0; exponent <= 16; exponent++) {
    const x = ix / 10;
    const s = state(Object.freeze({ x, exponent })), h = 10 ** -exponent, exact = Math.exp(x);
    const forwardReal = exact * Math.expm1(h) / h;
    const centralReal = exact * (Math.expm1(h) - Math.expm1(-h)) / (2 * h);
    close(s.h, h); close(s.exact, exact);
    assert(Math.abs(s.forward - forwardReal) <= 16 * s.forwardRoundingScale + 1e-14);
    assert(Math.abs(s.central - centralReal) <= 16 * s.centralRoundingScale + 1e-14);
    assert(Math.abs(forwardReal - exact) <= s.forwardTruncationBound * (1 + 1e-12) + 1e-14);
    assert(Math.abs(centralReal - exact) <= s.centralTruncationBound * (1 + 1e-12) + 1e-14);
    close(s.forwardError, Math.abs(s.forward - exact)); close(s.centralError, Math.abs(s.central - exact));
  }
  const coarse = state({ x: 0, exponent: 2 }), fine = state({ x: 0, exponent: 3 });
  assert(coarse.forwardError / fine.forwardError > 9); assert(coarse.centralError / fine.centralError > 90);
  const tiny = state({ x: 2, exponent: 16 });
  assert.equal(tiny.forward, 0); assert.equal(tiny.inputResolved, false); assert(tiny.forwardError > 7);
  assert.equal(tiny.actualForwardStep, 0); assert.equal(tiny.actualBackwardStep, 0);
  const resolved = state({ x: 1, exponent: 1 });
  close(resolved.actualForwardStep, .1); close(resolved.actualBackwardStep, .1);
});

// The binomial polynomial is independent of repeated Euler additions.
function binomial(qMinusOne, k) {
  let answer = 1, choose = 1;
  for (let j = 1; j <= k; j++) { choose *= (k - j + 1) / j; answer += choose * qMinusOne ** j; }
  return answer;
}
test('Euler trajectory, convergence and stability obey independent closed forms including boundaries', () => {
  const state = api('odeState');
  for (let il = -16; il <= 8; il++) for (const y0 of [-2, 0, 1, 2]) for (let n = 1; n <= 64; n++) {
    const lambda = il / 4;
    const s = state(Object.freeze({ lambda, y0, n }));
    close(s.h, 2 / n); close(s.factor, 1 + 2 * lambda / n); assert.equal(s.points.length, n + 1);
    s.points.forEach((p, k) => {
      close(p.t, 2 * k / n); close(p.euler, y0 * s.factor ** k, 2e-10);
      close(p.exact, y0 * Math.exp(lambda * 2 * k / n)); close(p.error, Math.abs(p.euler - p.exact));
      if (k <= 8 && Math.abs(s.h * lambda) <= .5) close(p.euler, y0 * binomial(s.h * lambda, k));
    });
    assert.equal(s.stability, Math.abs(s.factor) < 1 ? 'decay' : Math.abs(s.factor) === 1 ? 'boundary' : 'growth');
  }
  assert.equal(state({ lambda: -1, y0: 1, n: 1 }).factor, -1);
  assert.equal(state({ lambda: -2, y0: 1, n: 1 }).stability, 'growth');
  assert.equal(state({ lambda: -1, y0: 1, n: 2 }).points.at(-1).euler, 0);
  for (const lambda of [-1, 1]) {
    const coarse = state({ lambda, y0: 1, n: 16 }).points.at(-1).error;
    const fine = state({ lambda, y0: 1, n: 64 }).points.at(-1).error;
    assert(fine < coarse / 3);
  }
});

test('all finite ranges, integer controls and names are validated before calculation', () => {
  const specifications = [
    ['rootState', { function: 'square', method: 'bisection', x0: 1, steps: 4 }, { x0: [-2.01, 2.01], steps: [-1, .5, 13] }],
    ['differenceState', { x: 0, exponent: 4 }, { x: [-2.01, 2.01], exponent: [-1, .5, 17] }],
    ['odeState', { lambda: -1, y0: 1, n: 8 }, { lambda: [-4.01, 2.01], y0: [-2.01, 2.01], n: [0, 1.5, 65] }]
  ];
  const badTypes = [undefined, null, false, '1', NaN, Infinity, -Infinity, [], {}];
  for (const [name, valid, ranges] of specifications) {
    const fn = api(name);
    for (const bad of badTypes) assert.throws(() => fn(bad), TypeError);
    for (const key of Object.keys(ranges)) {
      for (const bad of badTypes) assert.throws(() => fn({ ...valid, [key]: bad }), TypeError);
      for (const bad of ranges[key]) assert.throws(() => fn({ ...valid, [key]: bad }), RangeError);
    }
  }
  for (const key of ['function', 'method']) {
    const valid = { function: 'square', method: 'newton', x0: 1, steps: 1 };
    for (const bad of [null, 1, false, {}]) assert.throws(() => api('rootState')({ ...valid, [key]: bad }), TypeError);
    assert.throws(() => api('rootState')({ ...valid, [key]: 'unknown' }), RangeError);
  }
});

test('classic script exposes a frozen MathNumerical namespace without replacing other books', () => {
  assert(fs.existsSync(source));
  const sentinel = Object.freeze({ preserved: true }), context = vm.createContext({ MathComplex: sentinel, MathVector: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathComplex, sentinel); assert.equal(context.MathVector, sentinel);
  assert(Object.isFrozen(context.MathNumerical)); assert(Object.isFrozen(math));
  assert.equal(context.MathNumerical.odeState({ lambda: 0, y0: 0, n: 1 }).points[1].euler, 0);
});
