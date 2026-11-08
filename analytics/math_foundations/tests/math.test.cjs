'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = path.join(__dirname, '../assets/math.js');
const math = fs.existsSync(source) ? require(source) : {};

function helper(name) {
  assert.equal(typeof math[name], 'function', `${name} must be implemented`);
  return math[name];
}

function close(actual, expected, tolerance = 1e-12) {
  assert.ok(Math.abs(actual - expected) <= tolerance,
    `expected ${actual} to be within ${tolerance} of ${expected}`);
}

test('complex multiplication agrees with a known product and i squared', () => {
  const multiply = helper('complexMultiply');
  assert.deepEqual(multiply({ re: 2, im: 3 }, { re: -1, im: 4 }), { re: -14, im: 5 });
  assert.deepEqual(multiply({ re: 0, im: 1 }, { re: 0, im: 1 }), { re: -1, im: 0 });
});

test('integer powers of i cycle through all four quarter-turns', () => {
  const quarterTurn = helper('quarterTurn');
  const expected = [
    { re: 1, im: 0 }, { re: 0, im: 1 },
    { re: -1, im: 0 }, { re: 0, im: -1 },
  ];
  for (let n = 0; n <= 12; n += 1) assert.deepEqual(quarterTurn(n), expected[n % 4]);
  assert.deepEqual(quarterTurn(-1), expected[3]);
});

test('sqrt bisection preserves a root bracket and its midpoint error bound', () => {
  const bisectionState = helper('bisectionState');
  for (const iterations of [0, 1, 2, 5, 10, 20, 30]) {
    const state = bisectionState('sqrt', iterations);
    assert.equal(state.rootGuaranteed, true);
    assert.equal(state.continuous, true);
    assert.ok(state.a <= Math.SQRT2 && Math.SQRT2 <= state.b);
    close(state.width, 2 / (2 ** iterations), 1e-14);
    close(state.errorBound, state.width / 2, 1e-14);
    assert.ok(Math.abs(state.midpoint - Math.SQRT2) <= state.errorBound);
    assert.ok(state.fa <= 0 && state.fb >= 0);
  }
});

test('a shrinking step bracket has no root guarantee or root', () => {
  const state = helper('bisectionState')('step', 20);
  assert.equal(state.continuous, false);
  assert.equal(state.rootGuaranteed, false);
  assert.equal(state.hasRoot, false);
  assert.ok(state.a <= 1.3 && 1.3 <= state.b);
  assert.ok(state.width < 0.000002);
  assert.equal(Math.abs(state.value), 1);
  assert.equal(state.errorBound, null);
});

test('a shrinking pole bracket does not claim a root or a root error bound', () => {
  const state = helper('bisectionState')('pole', 20);
  assert.equal(state.continuous, false);
  assert.equal(state.rootGuaranteed, false);
  assert.equal(state.hasRoot, false);
  assert.ok(state.a < 1.3 && 1.3 < state.b);
  assert.ok(Math.abs(state.value) > 100000);
  assert.equal(state.errorBound, null);
  for (const key of ['a', 'b', 'fa', 'fb', 'midpoint', 'value', 'width']) {
    assert.equal(Number.isFinite(state[key]), true, `${key} should be finite`);
  }
});

test('example values distinguish the step value from the undefined pole', () => {
  const evaluateExample = helper('evaluateExample');
  assert.equal(evaluateExample('sqrt', 0), -2);
  assert.equal(evaluateExample('sqrt', 2), 2);
  assert.equal(evaluateExample('step', 1.299), -1);
  assert.equal(evaluateExample('step', 1.3), 1);
  assert.equal(evaluateExample('pole', 1.3), null);
  close(evaluateExample('pole', 2), 1 / 0.7);
});

test('a right-angle rotation and its matrix give the expected coordinates', () => {
  const rotated = helper('rotateVector')({ x: 2, y: 0 }, 90);
  close(rotated.x, 0);
  close(rotated.y, 2);
  const matrix = helper('rotationMatrix')(90);
  close(matrix[0][0], 0);
  close(matrix[0][1], -1);
  close(matrix[1][0], 1);
  close(matrix[1][1], 0);
});

test('rotation composition equals the sum angle and preserves length', () => {
  const rotate = helper('rotateVector');
  const vector = { x: 2, y: -3 };
  for (const [alpha, beta] of [[30, 45], [-90, 270], [180, -75], [360, 360]]) {
    const successive = rotate(rotate(vector, alpha), beta);
    const together = rotate(vector, alpha + beta);
    close(successive.x, together.x);
    close(successive.y, together.y);
    close(Math.hypot(successive.x, successive.y), Math.hypot(vector.x, vector.y));
    const matrix = helper('rotationMatrix')(alpha + beta);
    close(matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0], 1);
  }
});

test('complex unit multiplication agrees with the composed rotation', () => {
  const multiply = helper('complexMultiply');
  const first = helper('rotateVector')({ x: 1, y: 0 }, 35);
  const second = helper('rotateVector')({ x: 1, y: 0 }, 110);
  const result = multiply({ re: first.x, im: first.y }, { re: second.x, im: second.y });
  const total = helper('rotateVector')({ x: 1, y: 0 }, 145);
  close(result.re, total.x);
  close(result.im, total.y);
});

test('non-finite numbers and malformed complex/vector inputs are rejected', () => {
  const multiply = helper('complexMultiply');
  const rotate = helper('rotateVector');
  const matrix = helper('rotationMatrix');
  for (const invalid of [NaN, Infinity, -Infinity, '2', undefined]) {
    assert.throws(() => multiply({ re: invalid, im: 0 }, { re: 1, im: 0 }));
    assert.throws(() => rotate({ x: 1, y: invalid }, 90));
    assert.throws(() => matrix(invalid));
    assert.throws(() => helper('evaluateExample')('sqrt', invalid));
  }
  assert.throws(() => multiply(null, { re: 1, im: 0 }));
  assert.throws(() => rotate(undefined, 90));
});

test('invalid powers, example names, and iteration counts are rejected', () => {
  const quarterTurn = helper('quarterTurn');
  const bisectionState = helper('bisectionState');
  const evaluateExample = helper('evaluateExample');
  for (const invalid of [1.5, NaN, Infinity, Number.MAX_SAFE_INTEGER + 1, '2']) {
    assert.throws(() => quarterTurn(invalid), RangeError);
  }
  for (const invalid of [-1, 0.5, 31, NaN, Infinity, '2']) {
    assert.throws(() => bisectionState('sqrt', invalid), RangeError);
  }
  assert.throws(() => bisectionState('missing', 0), RangeError);
  assert.throws(() => evaluateExample('missing', 1), RangeError);
});
