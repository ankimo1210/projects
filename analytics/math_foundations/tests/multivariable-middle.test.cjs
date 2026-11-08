'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assets = path.join(__dirname, '../assets');
const source = path.join(assets, 'multivariable-middle.js');
const math = fs.existsSync(source) ? require(source) : {};
const examples = ['bowl', 'saddle', 'flat-min', 'flat-saddle'];
const angles = [-Math.PI, -Math.PI / 2, -Math.PI / 4, 0, Math.PI / 4, Math.PI / 2, Math.PI];

function helper(name) {
  assert.equal(typeof math[name], 'function', `${name} must be implemented`);
  return math[name];
}
function close(actual, expected) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= 1e-12, `${actual} != ${expected}`);
}
function vector(actual, x, y) { close(actual.x, x); close(actual.y, y); }
function noNegativeZero(value) {
  if (typeof value === 'number') assert.ok(!Object.is(value, -0));
  else if (value && typeof value === 'object') Object.values(value).forEach(noNegativeZero);
}

test('compass gives hand-calculated slopes, extrema and direction', () => {
  const state = helper('gradientCompassState');
  for (const [angle, slope] of [[0, 2], [Math.PI / 2, 1], [-Math.PI, -2]]) {
    const s = state({ x: 1, y: 0 }, angle);
    assert.deepEqual(s.gradient, { x: 2, y: 1 });
    close(s.slope, slope); close(s.maxSlope, Math.sqrt(5)); close(s.minSlope, -Math.sqrt(5));
    vector(s.steepest, 2 / Math.sqrt(5), 1 / Math.sqrt(5));
  }
  const diagonal = state({ x: 1, y: 1 }, Math.PI / 4);
  vector(diagonal.gradient, 3, 3);
  close(diagonal.slope, 3 * Math.SQRT2); close(diagonal.maxSlope, 3 * Math.SQRT2);
  assert.equal(state({ x: -1, y: 1 }, 0).slope, -1);
});

test('compass preserves a frozen input and distinguishes zero gradient from a small nonzero gradient', () => {
  const state = helper('gradientCompassState');
  const base = Object.freeze({ x: -0, y: 0 });
  const s = state(base, -0);
  assert.notEqual(s.base, base);
  assert.deepEqual(base, { x: -0, y: 0 });
  assert.equal(s.steepest, null);
  assert.equal(s.slope, 0); assert.equal(s.maxSlope, 0); assert.equal(s.minSlope, 0);
  noNegativeZero(s);
  const tiny = state({ x: 1e-10, y: 0 }, 0);
  assert.ok(tiny.slope > 0); assert.notEqual(tiny.steepest, null);
});

test('curvature separates quadratic curvature from higher-order shape', () => {
  const state = helper('curvatureState');
  const bowl = state('bowl', 0, 0.5);
  assert.deepEqual(bowl.hessian, { xx: 2, xy: 1, yy: 2 });
  vector(bowl.point, 0.5, 0); close(bowl.value, 1 / 4);
  close(bowl.quadraticValue, 1 / 4); close(bowl.directionalSecond, 2);
  assert.equal(bowl.remainder, 0); assert.equal(bowl.hessianVerdict, 'strict-min');
  for (const [angle, value, second] of [[Math.PI / 4, 3 / 2, 3], [-Math.PI / 4, 1 / 2, 1]]) {
    const s = state('bowl', angle, 1); close(s.value, value); close(s.directionalSecond, second);
  }
  const saddle = state('saddle', Math.PI / 2, 0.5);
  close(saddle.value, -1 / 4); close(saddle.quadraticValue, -1 / 4);
  close(saddle.directionalSecond, -2); assert.equal(saddle.remainder, 0);
  assert.deepEqual(saddle.hessian, { xx: 2, xy: 0, yy: -2 });
  assert.equal(saddle.hessianVerdict, 'saddle');
  const flat = state('flat-min', Math.PI / 4, 0.5);
  close(flat.value, 1 / 32); close(flat.remainder, 1 / 32);
  for (const [example, angle, value] of [['flat-min', Math.PI / 4, 1 / 32], ['flat-saddle', 0, 1 / 16], ['flat-saddle', Math.PI / 2, -1 / 16]]) {
    const s = state(example, angle, 0.5);
    close(s.value, value); assert.equal(s.quadraticValue, 0); assert.equal(s.directionalSecond, 0);
    assert.deepEqual(s.hessian, { xx: 0, xy: 0, yy: 0 });
    assert.equal(s.hessianVerdict, 'inconclusive');
  }
});

test('circle states expose a projection at arbitrary points and analytic extrema', () => {
  const state = helper('circleConstraintState');
  const s = state(0);
  vector(s.point, 1, 0); vector(s.tangent, 0, 1); vector(s.objectiveGradient, 1, 2);
  vector(s.constraintGradient, 2, 0); close(s.value, 1); close(s.tangentRate, 2);
  close(s.lambdaProjection, 1 / 2); vector(s.normalResidual, 0, 2);
  const top = state(Math.PI / 2);
  vector(top.point, 0, 1); close(top.value, 2); close(top.tangentRate, -1);
  close(top.lambdaProjection, 1); vector(top.normalResidual, 1, 0);
  const maximumAngle = Math.atan2(2, 1);
  for (const [angle, sign] of [[maximumAngle, 1], [maximumAngle - Math.PI, -1]]) {
    const p = state(angle);
    assert.equal(p.angleRad, angle);
    vector(p.point, sign / Math.sqrt(5), sign * 2 / Math.sqrt(5));
    close(p.value, sign * Math.sqrt(5)); close(p.tangentRate, 0);
    close(p.lambdaProjection, sign * Math.sqrt(5) / 2); vector(p.normalResidual, 0, 0);
  }
});

test('all APIs retain angle endpoints and reject types and adjacent out-of-range values', () => {
  const compass = helper('gradientCompassState');
  const curvature = helper('curvatureState');
  const circle = helper('circleConstraintState');
  const calls = [angle => compass({ x: 1, y: 0 }, angle), angle => curvature('bowl', angle, 0.5), circle];
  for (const call of calls) {
    for (const angle of [-Math.PI, Math.PI]) assert.equal(call(angle).angleRad, angle);
    for (const value of [undefined, null, '0', {}, NaN, Infinity, -Infinity]) assert.throws(() => call(value), TypeError);
    for (const value of [-Math.PI - Number.EPSILON * 2, Math.PI + Number.EPSILON * 2]) assert.throws(() => call(value), RangeError);
  }
  for (const value of [undefined, null, '0', {}, NaN, Infinity, -Infinity]) {
    assert.throws(() => compass({ x: value, y: 0 }, 0), TypeError);
    assert.throws(() => compass({ x: 0, y: value }, 0), TypeError);
    assert.throws(() => curvature('bowl', 0, value), TypeError);
  }
  for (const base of [undefined, null, 1, 'point', [], { x: 0 }, { y: 0 }]) assert.throws(() => compass(base, 0), TypeError);
  for (const value of [-1 - Number.EPSILON, 1 + Number.EPSILON]) {
    assert.throws(() => compass({ x: value, y: 0 }, 0), RangeError);
    assert.throws(() => compass({ x: 0, y: value }, 0), RangeError);
    assert.throws(() => curvature('bowl', 0, value), RangeError);
  }
  for (const value of [undefined, null, 0, {}, NaN]) assert.throws(() => curvature(value, 0, 0), TypeError);
  for (const value of ['', 'minimum', 'Bowl']) assert.throws(() => curvature(value, 0, 0), RangeError);
});

test('small supported grids preserve bounds, parity, decompositions and positive zeros', () => {
  const compass = helper('gradientCompassState');
  const curvature = helper('curvatureState');
  const circle = helper('circleConstraintState');
  for (const x of [-1, 0, 1]) for (const y of [-1, 0, 1]) for (const angle of angles) {
    const s = compass({ x, y }, angle);
    assert.ok(Math.abs(s.slope) <= s.maxSlope + 1e-12); noNegativeZero(s);
    const opposite = compass({ x, y }, angle < 0 ? angle + Math.PI : angle - Math.PI);
    close(s.slope, -opposite.slope);
  }
  for (const example of examples) for (const angle of angles) for (const t of [-1, -0.5, -0, 0.5, 1]) {
    const s = curvature(example, angle, t);
    close(s.value, s.quadraticValue + s.remainder); close(s.value, curvature(example, angle, -t).value);
    assert.ok(Math.abs(s.value) <= 1.5 + 1e-12); noNegativeZero(s);
    if (t === 0) { vector(s.point, 0, 0); assert.equal(s.value, 0); assert.equal(s.quadraticValue, 0); assert.equal(s.remainder, 0); }
  }
  for (let degree = -180; degree <= 180; degree += 1) {
    const s = circle(degree * Math.PI / 180);
    close(Math.hypot(s.point.x, s.point.y), 1); close(Math.hypot(s.tangent.x, s.tangent.y), 1);
    close(s.point.x * s.tangent.x + s.point.y * s.tangent.y, 0);
    close(s.constraintGradient.x * s.tangent.x + s.constraintGradient.y * s.tangent.y, 0);
    vector(s.normalResidual, s.tangentRate * s.tangent.x, s.tangentRate * s.tangent.y);
    assert.ok(Math.abs(s.value) <= Math.sqrt(5) + 1e-12); noNegativeZero(s);
  }
  for (const call of [angle => compass({ x: -1, y: 1 }, angle), angle => curvature('bowl', angle, 1), circle]) {
    const left = call(-Math.PI), right = call(Math.PI);
    vector(left.direction || left.point, (right.direction || right.point).x, (right.direction || right.point).y);
  }
});

test('UMD exports only three frozen functions and leaves the four existing math namespaces intact', () => {
  helper('gradientCompassState');
  assert.ok(Object.isFrozen(math));
  const names = ['gradientCompassState', 'curvatureState', 'circleConstraintState'];
  assert.deepEqual(Object.keys(math).sort(), names.sort());
  const context = vm.createContext({});
  const files = ['math.js', 'calculus.js', 'linear.js', 'multivariable.js'];
  for (const file of files) vm.runInContext(fs.readFileSync(path.join(assets, file), 'utf8'), context);
  const oldNames = ['MathFoundations', 'MathCalculus', 'MathLinear', 'MathMultivariable'];
  const previous = oldNames.map(name => ({ api: context[name], keys: Object.keys(context[name]) }));
  function existingValues() {
    const product = context.MathFoundations.complexMultiply({ re: 2, im: 3 }, { re: -1, im: 4 });
    return [product.re, product.im, context.MathCalculus.secantSquare(1, 0.5).quotient,
      context.MathLinear.determinant2([[-2, 0], [0, 3]]), context.MathMultivariable.norm2({ x: 3, y: 4 })];
  }
  assert.deepEqual(existingValues(), [-14, 5, 2.5, -6, 5]);
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  oldNames.forEach((name, index) => {
    assert.equal(context[name], previous[index].api);
    assert.deepEqual(Object.keys(context[name]), previous[index].keys);
  });
  assert.deepEqual(existingValues(), [-14, 5, 2.5, -6, 5]);
  assert.ok(Object.isFrozen(context.MathMultivariableMiddle));
  assert.deepEqual(Object.keys(context.MathMultivariableMiddle).sort(), names);
  close(context.MathMultivariableMiddle.circleConstraintState(0).value, 1);
});
