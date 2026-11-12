'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/complex.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };
function close(actual, expected, tolerance = 4e-12) {
  assert(Number.isFinite(actual), `nonfinite value: ${actual}`);
  assert(Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
}
function complexClose(actual, expected, tolerance) {
  assert(actual && typeof actual === 'object');
  close(actual.re, expected.re, tolerance); close(actual.im, expected.im, tolerance);
}

// These closed forms follow by expanding f(z+δ)-f(z). They do not evaluate
// the function at two points or divide complex numbers, unlike production.
function quotientOracle(name, x, y, h, theta) {
  const angle = theta * Math.PI / 180;
  const c = Math.cos(angle), s = Math.sin(angle), c2 = Math.cos(2 * angle), s2 = Math.sin(2 * angle);
  if (name === 'square') return { re: 2 * x + h * c, im: 2 * y + h * s };
  if (name === 'conjugate') return { re: c2, im: -s2 };
  return { re: x + x * c2 + y * s2 + h * c, im: -y + y * c2 - x * s2 - h * s };
}

test('finite difference quotients match independent closed forms over points, steps and directions', () => {
  const state = api('differenceState');
  for (const name of ['square', 'conjugate', 'absSquare']) {
    for (const x of [-1.5, -.75, 0, .5, 1.5]) for (const y of [-1.5, -.5, 0, .75, 1.5]) {
      for (let step = 1; step <= 20; step++) for (let theta = 0; theta <= 360; theta += 5) {
        const h = step / 20;
        const input = Object.freeze({ function: name, x, y, h, theta });
        const s = state(input);
        complexClose(s.selected, quotientOracle(name, x, y, h, theta));
        complexClose(s.orthogonal0, quotientOracle(name, x, y, h, 0));
        complexClose(s.orthogonal90, quotientOracle(name, x, y, h, 90));
        complexClose(s.point, { re: x, im: y });
        close(Math.hypot(s.delta.re, s.delta.im), h);
      }
    }
  }
  // Sweep every UI point coordinate too, at a nonquadrantal API direction.
  for (let ix = -30; ix <= 30; ix++) for (let iy = -30; iy <= 30; iy++) for (const name of ['square', 'conjugate', 'absSquare']) {
    const x = ix / 20, y = iy / 20, h = .05, theta = 37;
    complexClose(state({ function: name, x, y, h, theta }).selected, quotientOracle(name, x, y, h, theta));
  }
});

test('finite h, pointwise differentiability, holomorphic neighborhoods and zero rotation stay distinct', () => {
  const state = api('differenceState');
  for (const theta of [0, 39, 90, 180, 270, 360]) {
    const square = state({ function: 'square', x: .4, y: -.7, h: .05, theta });
    complexClose(square.derivative, { re: .8, im: -1.4 }); close(square.error, .05);
    assert.equal(square.differentiable, true); assert.equal(square.holomorphicNeighborhood, true);
    close(square.derivativeRotation, Math.atan2(-1.4, .8));
    const zero = state({ function: 'square', x: 0, y: 0, h: .5, theta });
    complexClose(zero.derivative, { re: 0, im: 0 }); assert.equal(zero.derivativeRotation, null);
    const modulus = state({ function: 'absSquare', x: 0, y: 0, h: .05, theta });
    complexClose(modulus.derivative, { re: 0, im: 0 }); close(modulus.error, .05);
    assert.equal(modulus.differentiable, true); assert.equal(modulus.holomorphicNeighborhood, false);
    assert.equal(modulus.derivativeRotation, null);
    for (const name of ['conjugate', 'absSquare']) {
      const s = state({ function: name, x: .3, y: -.5, h: .1, theta });
      assert.equal(s.derivative, null); assert.equal(s.error, null); assert.equal(s.derivativeRotation, null);
      assert.equal(s.differentiable, false); assert.equal(s.holomorphicNeighborhood, false);
    }
  }
});

test('logarithm lift, principal branch and exponential inversion agree throughout the supported domain', () => {
  const state = api('logarithmState');
  for (const radius of [.5, .75, 1, 1.5, 2]) for (let theta = -360; theta <= 360; theta += 5) {
    const s = state(Object.freeze({ radius, theta }));
    close(s.tracked.re, Math.log(radius)); close(s.tracked.im, theta * Math.PI / 180);
    complexClose({ re: Math.exp(s.tracked.re) * Math.cos(s.tracked.im), im: Math.exp(s.tracked.re) * Math.sin(s.tracked.im) }, s.point);
    if (Math.abs(theta) === 180) {
      assert.equal(s.principal, null); assert.equal(s.principalAngle, null); assert.equal(s.onCut, true);
    } else {
      assert.equal(s.onCut, false); assert(s.principalAngle > -Math.PI && s.principalAngle < Math.PI);
      close(s.principal.re, Math.log(radius)); close(s.principal.im, s.principalAngle);
      complexClose({ re: Math.exp(s.principal.re) * Math.cos(s.principal.im), im: Math.exp(s.principal.re) * Math.sin(s.principal.im) }, s.point);
    }
  }
});

test('quadrantal points are exact and revisiting a point retains the path lift', () => {
  const state = api('logarithmState');
  const points = [[-360, 1, 0], [-270, 0, 1], [-180, -1, 0], [-90, 0, -1], [0, 1, 0], [90, 0, 1], [180, -1, 0], [270, 0, -1], [360, 1, 0]];
  for (const [theta, re, im] of points) {
    const s = state({ radius: 2, theta }); assert.deepEqual(s.point, { re: 2 * re || 0, im: 2 * im || 0 });
  }
  for (const theta of [-360, 0, 360]) {
    const s = state({ radius: 1, theta }); assert.deepEqual(s.point, { re: 1, im: 0 });
    assert.deepEqual(s.principal, { re: 0, im: 0 }); close(s.tracked.im, theta * Math.PI / 180);
  }
});

test('only the cut itself is unavailable, without discarding its valid neighborhoods', () => {
  const state = api('logarithmState');
  for (const cut of [-180, 180]) for (const delta of [-1e-9, -1e-12, 1e-12, 1e-9]) {
    const s = state({ radius: 1, theta: cut + delta });
    assert.equal(s.onCut, false); assert(s.principal !== null);
    assert.equal(Math.sign(s.principal.im), Math.sign(s.point.im));
    close(Math.abs(s.principal.im), Math.PI, 1e-9);
  }
});

// Summing roots of z^n = -1 gives the even-midpoint formula below. It is
// independent of the sampled parametrized contour and complex division.
test('midpoint quadrature agrees with the independent even-root formula inside and outside', () => {
  const state = api('residueState');
  for (const a of [-2, -1.7, -1.01, -.999, -.9, -.5, 0, .5, .9, .999, 1.01, 1.7, 2]) {
    for (const n of [16, 32, 64, 128, 256]) for (const orientation of [-1, 1]) {
      const s = state(Object.freeze({ a, n, orientation }));
      const expected = orientation * 2 * Math.PI / (1 + a ** n);
      complexClose(s.numeric, { re: 0, im: expected }, 3e-11);
      complexClose(s.exact, { re: 0, im: Math.abs(a) < 1 ? orientation * 2 * Math.PI : 0 });
      close(s.error, Math.abs(expected - s.exact.im), 3e-11);
      assert.equal(s.region, Math.abs(a) < 1 ? 'inside' : 'outside');
    }
  }
});

test('contour poles are unavailable before sampling, even though their midpoint sum would be finite', () => {
  const state = api('residueState');
  for (const a of [-1, 1]) for (const orientation of [-1, 1]) for (const n of [16, 256]) {
    const wouldBeMidpoint = orientation * 2 * Math.PI / (1 + a ** n); close(wouldBeMidpoint, orientation * Math.PI);
    const s = state({ a, orientation, n });
    assert.equal(s.region, 'boundary'); assert.equal(s.exact, null); assert.equal(s.numeric, null); assert.equal(s.error, null);
  }
  for (const a of [-1 - Number.EPSILON, -1 + Number.EPSILON, 1 - Number.EPSILON, 1 + Number.EPSILON]) {
    const s = state({ a, orientation: 1, n: 16 }); assert.notEqual(s.region, 'boundary');
    assert(s.exact !== null); assert(s.numeric !== null); assert(Number.isFinite(s.numeric.im));
  }
});

test('refining a regular contour improves its observed error and reversing orientation negates both values', () => {
  const state = api('residueState');
  for (const a of [-1.2, -.8, .8, 1.2]) {
    const coarse = state({ a, n: 16, orientation: 1 }), fine = state({ a, n: 128, orientation: 1 });
    assert(fine.error < coarse.error);
    const reverse = state({ a, n: 128, orientation: -1 });
    complexClose(reverse.numeric, { re: -fine.numeric.re, im: -fine.numeric.im });
    complexClose(reverse.exact, { re: -fine.exact.re, im: -fine.exact.im });
  }
});

test('all APIs reject missing, nonnumeric and unsupported parameters', () => {
  const specifications = [
    ['differenceState', { function: 'square', x: 0, y: 0, h: .1, theta: 45 }, { x: [-1.51, 1.51], y: [-1.51, 1.51], h: [0, .049, 1.01], theta: [-.01, 360.01] }],
    ['logarithmState', { radius: 1, theta: 45 }, { radius: [0, .49, 2.01], theta: [-360.01, 360.01] }],
    ['residueState', { a: 0, orientation: 1, n: 64 }, { a: [-2.01, 2.01], orientation: [-2, 0, .5, 2], n: [0, 15, 17, 32.5, 257] }]
  ];
  const badTypes = [undefined, null, false, '1', NaN, Infinity, -Infinity, [], {}];
  for (const [name, valid, invalid] of specifications) {
    const state = api(name);
    for (const bad of badTypes) assert.throws(() => state(bad), TypeError);
    for (const key of Object.keys(valid).filter(key => key !== 'function')) for (const bad of badTypes) assert.throws(() => state({ ...valid, [key]: bad }), TypeError);
    for (const [key, values] of Object.entries(invalid)) for (const value of values) assert.throws(() => state({ ...valid, [key]: value }), RangeError);
  }
  for (const bad of [undefined, null, false, 2, [], {}]) assert.throws(() => api('differenceState')({ function: bad, x: 0, y: 0, h: .1, theta: 0 }), TypeError);
  assert.throws(() => api('differenceState')({ function: 'unknown', x: 0, y: 0, h: .1, theta: 0 }), RangeError);
});

test('classic script exports one frozen namespace and leaves existing globals intact', () => {
  assert(fs.existsSync(source), 'complex module must exist');
  const sentinel = Object.freeze({ untouched: true });
  const context = vm.createContext({ MathProbability: sentinel, MathDiscrete: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathProbability, sentinel); assert.equal(context.MathDiscrete, sentinel);
  assert(Object.isFrozen(context.MathComplex)); assert(Object.isFrozen(math));
  assert.equal(context.MathComplex.residueState({ a: 0, n: 16, orientation: 1 }).exact.im, 2 * Math.PI);
});
