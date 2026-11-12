'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assets = path.join(__dirname, '../assets');
const source = path.join(assets, 'multivariable.js');
const math = fs.existsSync(source) ? require(source) : {};

function helper(name) {
  assert.equal(typeof math[name], 'function', `${name} must be implemented`);
  return math[name];
}

function close(actual, expected) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= 1e-12 * Math.max(1, Math.abs(expected)),
    `${actual} != ${expected}`);
}

test('norm handles the origin, a 3-4-5 triangle, and large finite coordinates', () => {
  const norm = helper('norm2');
  assert.equal(norm({ x: 3, y: 4 }), 5);
  assert.equal(norm({ x: 0, y: 0 }), 0);
  assert.equal(norm({ x: 1e300, y: 0 }), 1e300);
  assert.ok(norm({ x: 1e-200, y: 1e-200 }) > 0);
});

test('F separates both axes from the positive and negative diagonals', () => {
  const state = helper('pathState');
  for (const t of [-1, 1]) {
    assert.equal(state('axis-trap', 'x-axis', t).value, 0);
    assert.equal(state('axis-trap', 'y-axis', t).value, 0);
  }
  for (const t of [-0.5, 0.5]) assert.equal(state('axis-trap', 'line', t).value, 0.5);
  assert.equal(state('axis-trap', 'line', 0.5, -1).value, -0.5);
  const s = state('axis-trap', 'parabola', 0.5, 2);
  assert.deepEqual(s, { example: 'axis-trap', path: 'parabola', t: 0.5, coefficient: 2,
    point: { x: 0.5, y: 0.5 }, distance: Math.SQRT1_2, value: 0.5, atOrigin: false });
});

test('H distinguishes a straight path from parabola values checked as rational numbers', () => {
  const state = helper('pathState');
  close(state('curved-trap', 'line', 0.5).value, 2 / 5);
  close(state('curved-trap', 'line', -0.5).value, -2 / 5);
  for (const t of [-0.5, 0.5]) assert.equal(state('curved-trap', 'parabola', t).value, 0.5);
  const s = state('curved-trap', 'parabola', 0.5, 2);
  assert.deepEqual(s.point, { x: 0.5, y: 0.5 });
  close(s.value, 2 / 5);
  close(state('curved-trap', 'parabola', 0.5, -2).value, -2 / 5);
});

test('origin states express the definition value and zero coefficients degenerate to the x axis', () => {
  const state = helper('pathState');
  for (const example of ['axis-trap', 'curved-trap']) {
    for (const route of ['x-axis', 'y-axis', 'line', 'parabola']) {
      const s = state(example, route, 0, -2);
      assert.deepEqual(s.point, { x: 0, y: 0 });
      assert.equal(s.distance, 0);
      assert.equal(s.value, 0);
      assert.equal(s.atOrigin, true);
      assert.equal(s.coefficient, -2);
    }
    for (const route of ['line', 'parabola']) {
      const s = state(example, route, 0.5, 0);
      assert.deepEqual(s.point, { x: 0.5, y: 0 });
      assert.equal(s.value, 0);
      assert.equal(s.atOrigin, false);
    }
  }
  assert.equal(state('axis-trap', 'x-axis', 1, 2).coefficient, 2);
});

test('F keeps its diagonal value when raw coordinate squares would underflow or overflow', () => {
  const state = helper('pathState');
  for (const t of [1e-200, -1e-200, 1e300]) {
    const s = state('axis-trap', 'line', t);
    assert.equal(s.value, 0.5);
    assert.ok(s.distance > 0 && Number.isFinite(s.distance));
  }
});

test('P reports an independently known tangent prediction and exact quadratic remainder', () => {
  const s = helper('quadraticLinearState')({ x: 1, y: 1 }, { x: 0.1, y: -0.2 });
  assert.deepEqual(s.base, { x: 1, y: 1 });
  assert.deepEqual(s.delta, { x: 0.1, y: -0.2 });
  assert.deepEqual(s.point, { x: 1.1, y: 0.8 });
  assert.equal(s.baseValue, 3);
  assert.deepEqual(s.coefficients, { x: 3, y: 3 });
  close(s.linearValue, 2.7);
  close(s.value, 2.73);
  close(s.remainder, 3 / 100);
  close(s.distance, Math.sqrt(5) / 10);
  close(s.normalizedError, 3 / (10 * Math.sqrt(5)));
  close(s.errorBound, 3 / 40);
});

test('P remainder and bound shrink quadratically while normalized error shrinks linearly', () => {
  const state = helper('quadraticLinearState');
  const original = state({ x: 1, y: 1 }, { x: 0.1, y: -0.2 });
  for (const [rho, remainder, bound] of [[1, 0.03, 0.075], [0.5, 0.0075, 0.01875], [0.25, 0.001875, 0.0046875]]) {
    const s = state({ x: 1, y: 1 }, { x: rho * 0.1, y: rho * -0.2 });
    close(s.remainder, remainder);
    close(s.errorBound, bound);
    close(s.normalizedError, original.normalizedError * rho);
  }
});

test('P retains a nonzero remainder even when value and prediction round to the same number', () => {
  const s = helper('quadraticLinearState')({ x: 1, y: 1 }, { x: 1e-10, y: 0 });
  assert.equal(s.value, s.linearValue);
  assert.ok(s.remainder > 0);
  assert.ok(Math.abs(s.remainder / 1e-20 - 1) < 1e-12);
  assert.ok(s.normalizedError > 0);
});

test('P zero increment has zero remainder and an undefined normalized ratio', () => {
  const state = helper('quadraticLinearState');
  for (const base of [{ x: 1, y: 1 }, { x: -2, y: 3 }, { x: 0, y: 0 }]) {
    const s = state(base, { x: 0, y: 0 });
    assert.equal(s.value, s.baseValue);
    assert.equal(s.linearValue, s.baseValue);
    assert.equal(s.remainder, 0);
    assert.equal(s.distance, 0);
    assert.equal(s.errorBound, 0);
    assert.equal(s.normalizedError, null);
  }
});

test('P respects the analytic error bound within roundoff on a grid including both sharp diagonal directions', () => {
  const state = helper('quadraticLinearState');
  for (const x of [-1, -0.5, 0, 0.5, 1]) {
    for (const y of [-1, -0.5, 0, 0.5, 1]) {
      const s = state({ x: 1, y: 1 }, { x, y });
      assert.ok(s.remainder >= 0 && s.remainder <= s.errorBound + 1e-14);
      if (s.distance > 0) assert.ok(s.normalizedError <= 1.5 * s.distance + 1e-14);
    }
  }
  assert.equal(state({ x: 0, y: 0 }, { x: 1, y: 1 }).remainder, 3);
  assert.equal(state({ x: 0, y: 0 }, { x: 1, y: -1 }).remainder, 1);
});

test('P approximates the sharp decimal diagonal bound within relative roundoff', () => {
  const s = helper('quadraticLinearState')({ x: 0, y: 0 }, { x: -0.81, y: -0.81 });
  // In exact arithmetic both R and its sharp bound are 3 * (81/100)^2.
  // Their independently rounded approximations need not preserve the inequality exactly.
  const expected = 19683 / 10000;
  const tolerance = 16 * Number.EPSILON * Math.abs(expected);
  assert.ok(Math.abs(s.remainder - expected) <= tolerance);
  assert.ok(Math.abs(s.errorBound - expected) <= tolerance);
  assert.ok(s.remainder <= s.errorBound + tolerance);
});

test('coordinate and scalar type errors never coerce strings or accept nonfinite numbers', () => {
  const norm = helper('norm2');
  const state = helper('pathState');
  const quadratic = helper('quadraticLinearState');
  for (const point of [null, undefined, 1, '1', {}, { x: 1 }, { x: '1', y: 0 }, { x: 0, y: NaN }, { x: Infinity, y: 0 }]) {
    assert.throws(() => norm(point), TypeError);
    assert.throws(() => quadratic(point, { x: 0, y: 0 }), TypeError);
    assert.throws(() => quadratic({ x: 0, y: 0 }, point), TypeError);
  }
  for (const invalid of [null, undefined, '1', NaN, Infinity, -Infinity]) {
    assert.throws(() => state('axis-trap', 'line', invalid), TypeError);
    if (invalid !== undefined) assert.throws(() => state('axis-trap', 'x-axis', 1, invalid), TypeError);
  }
  assert.throws(() => state(null, 'line', 1), TypeError);
  assert.throws(() => state('axis-trap', null, 1), TypeError);
  assert.throws(() => state('unknown', 'line', 1), RangeError);
  assert.throws(() => state('axis-trap', 'unknown', 1), RangeError);
});

test('numeric range errors expose overflow and disappearing nonzero squares or path components', () => {
  const norm = helper('norm2');
  const state = helper('pathState');
  const quadratic = helper('quadraticLinearState');
  assert.throws(() => norm({ x: Number.MAX_VALUE, y: Number.MAX_VALUE }), RangeError);
  assert.throws(() => state('curved-trap', 'parabola', 1e-200), RangeError);
  assert.throws(() => state('curved-trap', 'line', 1e-200), RangeError);
  assert.throws(() => state('curved-trap', 'x-axis', 1e200), RangeError);
  assert.throws(() => state('axis-trap', 'parabola', 1e200), RangeError);
  assert.throws(() => state('axis-trap', 'line', Number.MIN_VALUE, 0.5), RangeError);
  assert.throws(() => state('axis-trap', 'parabola', 1e-160, 1e-10), RangeError);
  assert.throws(() => state('axis-trap', 'line', 1e308, 2), RangeError);
  assert.throws(() => quadratic({ x: 0, y: 0 }, { x: 1e-200, y: 0 }), RangeError);
  assert.throws(() => quadratic({ x: 1e-200, y: 0 }, { x: 0, y: 0 }), RangeError);
  assert.throws(() => quadratic({ x: 1e308, y: 1e308 }, { x: 0, y: 0 }), RangeError);
  assert.throws(() => quadratic({ x: 0, y: 0 }, { x: 1e154, y: 1e154 }), RangeError);
});

test('a nonzero ratio that disappears during scaling is reported as underflow', () => {
  const state = helper('pathState');
  // x squared survives as a subnormal, but its ratio to y is below Number.MIN_VALUE.
  assert.throws(() => state('curved-trap', 'line', 1e-160, 1e308), RangeError);
  // A negligible squared denominator term may vanish while the displayed value survives.
  const representable = state('axis-trap', 'line', 1, 1e-200);
  assert.ok(Math.abs(representable.value / 1e-200 - 1) < 1e-12);
});

test('P rejects subnormal squares to avoid severe relative precision loss', () => {
  const quadratic = helper('quadraticLinearState');
  // Each nonzero square rounds to Number.MIN_VALUE, causing a large relative bound discrepancy.
  for (const delta of [{ x: 1.6e-162, y: 1.6e-162 }, { x: 1.6e-162, y: -1.6e-162 }, { x: 1e-160, y: 0 }]) {
    assert.throws(() => quadratic({ x: 0, y: 0 }, delta), RangeError);
  }
  assert.throws(() => quadratic({ x: 1e-160, y: 0 }, { x: 0, y: 0 }), RangeError);
  const normalEdge = 2 ** -511;
  assert.throws(() => quadratic({ x: 0, y: 0 }, { x: normalEdge / 2, y: 0 }), RangeError);
  const s = quadratic({ x: 0, y: 0 }, { x: normalEdge, y: 0 });
  // Exact powers of two test the allowed normal boundary without an absolute tolerance.
  assert.equal(s.remainder, 2 ** -1022);
  assert.equal(s.errorBound, 1.5 * 2 ** -1022);
  assert.equal(s.normalizedError, normalEdge);
  assert.ok(s.remainder <= s.errorBound);
  assert.equal(helper('pathState')('axis-trap', 'line', 1e-200).value, 0.5);
  assert.equal(helper('norm2')({ x: Number.MIN_VALUE, y: 0 }), Number.MIN_VALUE);
  assert.equal(helper('norm2')({ x: 1e300, y: 0 }), 1e300);
});

test('frozen inputs remain intact and negative zeros are normalized throughout output', () => {
  const norm = helper('norm2');
  const state = helper('pathState');
  const quadratic = helper('quadraticLinearState');
  const base = Object.freeze({ x: -0, y: 1 });
  const delta = Object.freeze({ x: -0, y: -0 });
  const s = quadratic(base, delta);
  assert.equal(Object.is(base.x, -0), true);
  assert.equal(Object.is(delta.y, -0), true);
  assert.notEqual(s.base, base);
  assert.notEqual(s.delta, delta);
  function noNegativeZero(value) {
    if (typeof value === 'number') assert.equal(Object.is(value, -0), false);
    else if (value && typeof value === 'object') Object.values(value).forEach(noNegativeZero);
  }
  noNegativeZero(s);
  noNegativeZero(state('axis-trap', 'parabola', -0, -0));
  noNegativeZero(norm(delta));
});

test('the frozen browser API coexists with all three existing mathematics namespaces', () => {
  helper('pathState');
  assert.deepEqual(Object.keys(math).sort(), ['norm2', 'pathState', 'quadraticLinearState']);
  assert.equal(Object.isFrozen(math), true);
  const context = vm.createContext({});
  for (const filename of ['math.js', 'calculus.js', 'linear.js']) {
    vm.runInContext(fs.readFileSync(path.join(assets, filename), 'utf8'), context);
  }
  const originalGlobals = Object.keys(context).sort();
  const originals = originalGlobals.map(name => [name, context[name], Object.keys(context[name])]);
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.deepEqual(Object.keys(context).sort(), [...originalGlobals, 'MathMultivariable'].sort());
  for (const [name, reference, keys] of originals) {
    assert.equal(context[name], reference);
    assert.deepEqual(Object.keys(context[name]), keys);
  }
  assert.equal(context.MathFoundations.complexMultiply({ re: 0, im: 1 }, { re: 0, im: 1 }).re, -1);
  assert.equal(context.MathCalculus.squareRiemann(2).left, 0.125);
  assert.equal(context.MathLinear.determinant2([[1, 2], [3, 4]]), -2);
  assert.equal(context.MathMultivariable.pathState('axis-trap', 'line', 0.5).value, 0.5);
  assert.equal(Object.isFrozen(context.MathMultivariable), true);
});
