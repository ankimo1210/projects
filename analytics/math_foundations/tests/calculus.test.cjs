'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const source = path.join(__dirname, '../assets/calculus.js');
const math = fs.existsSync(source) ? require(source) : {};
function close(actual, expected, tolerance = 1e-12) {
  assert.ok(Math.abs(actual - expected) < tolerance, `${actual} != ${expected}`);
}
test('secant distinguishes finite quotient from the derivative at zero increment', () => {
  const finite = math.secantSquare(1, 0.5);
  close(finite.quotient, 2.5);
  close(finite.derivative, 2);
  close(finite.error, 0.25);
  close(finite.y, 2.25);
  const zero = math.secantSquare(1, 0);
  assert.equal(zero.quotient, null);
  assert.equal(zero.derivative, 2);
  close(math.secantSquare(1, -0.5).quotient, 1.5);
});
test('square sums bracket the integral with analytically known errors', () => {
  const one = math.squareRiemann(1);
  assert.equal(one.left, 0);
  assert.equal(one.right, 1);
  const two = math.squareRiemann(2);
  close(two.left, 0.125);
  close(two.right, 0.625);
  for (const n of [4, 16, 64]) {
    const value = math.squareRiemann(n);
    assert.ok(value.left < 1 / 3 && 1 / 3 < value.right);
    close(value.right - value.left, 1 / n);
    close((value.right + value.left) / 2 - 1 / 3, 1 / (6 * n * n));
  }
});
test('geometric partial sums report a limit only inside its convergence range', () => {
  const finite = math.geometricPartial(0.5, 4);
  close(finite.sum, 1.875);
  close(finite.limit, 2);
  close(finite.errorBound, 0.125);
  close(math.geometricPartial(-0.5, 3).sum, 0.75);
  close(math.geometricPartial(0, 5).sum, 1);
  for (const ratio of [-1.2, -1, 1, 1.2]) {
    const state = math.geometricPartial(ratio, 10);
    assert.equal(state.converges, false);
    assert.equal(state.limit, null);
    assert.equal(state.errorBound, null);
  }
  assert.equal(math.geometricPartial(1, 10).sum, 10);
  assert.equal(math.geometricPartial(-1, 10).sum, 0);
});
test('invalid domains and nonfinite arithmetic do not reach the diagrams', () => {
  for (const name of ['squareRiemann', 'geometricPartial', 'secantSquare']) {
    assert.equal(typeof math[name], 'function');
  }
  for (const n of [0, -1, 1.5, Infinity, '2', 4097]) assert.throws(() => math.squareRiemann(n));
  for (const n of [0, -1, 1.5, 201]) assert.throws(() => math.geometricPartial(0.5, n));
  assert.throws(() => math.geometricPartial(Infinity, 4));
  assert.throws(() => math.geometricPartial(1e200, 5));
  assert.throws(() => math.secantSquare(NaN, 1));
  assert.throws(() => math.secantSquare(1e200, 1));
});
