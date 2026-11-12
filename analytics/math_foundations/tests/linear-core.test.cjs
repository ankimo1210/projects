'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/linear-core.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', name + ' must be implemented'); return math[name]; };
function close(actual, expected, tolerance = 5e-12) {
  assert(Number.isFinite(actual));
  assert(Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), actual + ' != ' + expected);
}
const dot = (a, b) => a.reduce((sum, x, i) => sum + x * b[i], 0);
const multiply = (a, v) => a.map(row => dot(row, v));
const mapDefault = { s: .5, t: 1, x: 1, y: 1, b1: 1, b2: 1 };
const lsDefault = { y0: 1, y1: 0, y2: 2, deltaA: 0, deltaB: 0 };
const spectralDefault = { lambda1: 2, lambda2: .5, theta: 30, x: 1, y: 1 };

// Wrong determinant signs, epsilon-based rank and inverse-coordinate errors
// are caught by exact quarter-grid cross products and Ax=b back checks.
test('map geometry and solutions obey exact grid rank and direct matrix multiplication', () => {
  const state = api('mapState');
  for (let is = -8; is <= 8; is++) for (let it = -8; it <= 8; it++) {
    for (const b of [[0, 0], [1, 1], [-2, .75]]) {
      const input = Object.freeze({ ...mapDefault, s: is / 4, t: it / 4, x: -.75, y: 1.25, b1: b[0], b2: b[1] });
      const s = state(input), determinant = (16 - is * it) / 16;
      assert.deepEqual(s.matrix, [[1, it / 4], [is / 4, 1]]);
      assert.deepEqual(s.columns, [[1, is / 4], [it / 4, 1]]);
      assert.equal(s.determinant, determinant); assert.equal(s.rank, determinant === 0 ? 1 : 2);
      assert.deepEqual(s.transformed, multiply(s.matrix, [input.x, input.y]));
      const consistent = is * b[0] === 4 * b[1];
      assert.equal(s.solutionKind, determinant !== 0 ? 'unique' : consistent ? 'infinite' : 'none');
      if (s.representativeSolution !== null) multiply(s.matrix, s.representativeSolution).forEach((v, i) => close(v, b[i]));
      if (determinant === 0) {
        assert.deepEqual(s.kernelDirection, [-it / 4, 1]);
        multiply(s.matrix, s.kernelDirection).forEach(v => close(v, 0));
        if (consistent) {
          assert.deepEqual(s.representativeSolution, [b[0], 0]);
          const other = s.representativeSolution.map((v, i) => v + 2.5 * s.kernelDirection[i]);
          multiply(s.matrix, other).forEach((v, i) => close(v, b[i]));
        } else assert.equal(s.representativeSolution, null);
      } else assert.equal(s.kernelDirection, null);
    }
  }
  assert.equal(state({ ...mapDefault, s: 2, t: 2 }).determinant, -3);
  assert.equal(state({ ...mapDefault, s: 1, t: 1, b1: 1, b2: 1 }).solutionKind, 'infinite');
  assert.equal(state({ ...mapDefault, s: 1, t: 1, b1: 1, b2: 0 }).solutionKind, 'none');
});

// The second difference d supplies a residual oracle without reusing the
// implementation's mean/slope or projection calculation.
test('least squares matches the independent second-difference residual and Pythagoras', () => {
  const state = api('leastSquaresState');
  for (let i = -8; i <= 8; i++) for (let j = -8; j <= 8; j++) for (let k = -8; k <= 8; k++) {
    const observed = [i / 4, j / 4, k / 4], d = (i - 2 * j + k) / 4;
    const s = state(Object.freeze({ ...lsDefault, y0: observed[0], y1: observed[1], y2: observed[2] }));
    const residual = [d / 6, -d / 3, d / 6], fitted = observed.map((v, n) => v - residual[n]);
    assert.deepEqual(s.observed, observed);
    residual.forEach((v, n) => close(s.residual[n], v));
    fitted.forEach((v, n) => close(s.fitted[n], v));
    close(s.a, fitted[1]); close(s.b, (fitted[2] - fitted[0]) / 2);
    close(s.normalResiduals[0], 0); close(s.normalResiduals[1], 0);
    close(s.sse, d * d / 6);
    close(s.observedNormSquared, dot(observed, observed)); close(s.fitNormSquared, dot(fitted, fitted));
    close(s.pythagoreanResidual, 0);
    close(s.observedNormSquared, s.fitNormSquared + s.sse);
  }
  const zero = state({ y0: 0, y1: 0, y2: 0, deltaA: 0, deltaB: 0 });
  assert.deepEqual(zero.residual, [0, 0, 0]); assert.equal(zero.sse, 0);
  const affine = state({ y0: -1, y1: .5, y2: 2, deltaA: 0, deltaB: 0 });
  assert.deepEqual(affine.fitted, [-1, .5, 2]); assert.equal(affine.sse, 0);
  const rounded = state({ y0: .25, y1: 0, y2: 0, deltaA: 0, deltaB: 0 });
  assert.equal(rounded.normalResiduals[0], rounded.residual.reduce((sum, v) => sum + v, 0));
  assert.equal(rounded.pythagoreanResidual, rounded.observedNormSquared - rounded.fitNormSquared - rounded.sse);
});

test('least-squares candidate gap is nonnegative and separates intercept from slope offsets', () => {
  const state = api('leastSquaresState');
  for (const observed of [[1, 0, 2], [0, 0, 0], [-2, .25, 1.5]]) for (let ia = -4; ia <= 4; ia++) for (let ib = -4; ib <= 4; ib++) {
    const s = state({ y0: observed[0], y1: observed[1], y2: observed[2], deltaA: ia / 4, deltaB: ib / 4 });
    const d = observed[0] - 2 * observed[1] + observed[2];
    const residual = [d / 6 - ia / 4 + ib / 4, -d / 3 - ia / 4, d / 6 - ia / 4 - ib / 4];
    close(s.candidateA, s.a + ia / 4); close(s.candidateB, s.b + ib / 4);
    s.candidateFitted.forEach((v, i) => close(v, observed[i] - residual[i]));
    close(s.candidateSSE, dot(residual, residual));
    close(s.excess, (3 * ia * ia + 2 * ib * ib) / 16);
    close(s.candidateSSE - s.sse, s.excess); assert(s.excess >= 0);
    assert.equal(s.excess === 0, ia === 0 && ib === 0);
  }
});

// Check the operator through eigenvector identities and quadratic forms,
// rather than regenerate it with the production midpoint/half formula.
test('symmetric model respects its eigenvectors, quadratic form and singular values', () => {
  const state = api('spectralState');
  for (let i = -8; i <= 12; i++) for (let j = -8; j <= 12; j++) for (let theta = 0; theta <= 180; theta += 15) {
    const eigenvalues = [i / 4, j / 4], x = [-.75, 1.5];
    const s = state(Object.freeze({ lambda1: eigenvalues[0], lambda2: eigenvalues[1], theta, x: x[0], y: x[1] }));
    assert.deepEqual(s.eigenvalues, eigenvalues); assert.equal(s.matrix[0][1], s.matrix[1][0]);
    close(dot(s.directions[0], s.directions[0]), 1); close(dot(s.directions[1], s.directions[1]), 1); close(dot(...s.directions), 0);
    s.directions.forEach((q, n) => multiply(s.matrix, q).forEach((v, k) => close(v, eigenvalues[n] * q[k])));
    multiply(s.matrix, x).forEach((v, k) => close(v, s.transformed[k]));
    close(s.quadraticForm, eigenvalues.reduce((sum, lambda, n) => sum + lambda * dot(s.directions[n], x) ** 2, 0));
    assert.equal(s.trace, eigenvalues[0] + eigenvalues[1]); assert.equal(s.determinant, eigenvalues[0] * eigenvalues[1] || 0);
    assert.equal(s.rank, Number(i !== 0) + Number(j !== 0));
    assert.deepEqual(s.singularValues, eigenvalues.map(Math.abs).sort((a, b) => b - a));
    assert.equal(s.repeatedEigenvalue, i === j); assert.equal(s.eigenDirectionsUnique, i !== j);
    assert.equal(s.singularDirectionsUnique, Math.abs(i) !== Math.abs(j));
  }
});

test('spectral zero, repeated values, sign and exact quadrant behavior remain distinct', () => {
  const state = api('spectralState');
  const cases = [[2, .5, 'positive-definite'], [-2, -.5, 'negative-definite'], [-2, 3, 'indefinite'],
    [0, 2, 'positive-semidefinite'], [-1, 0, 'negative-semidefinite'], [0, 0, 'zero']];
  cases.forEach(([lambda1, lambda2, formKind]) => assert.equal(state({ ...spectralDefault, lambda1, lambda2 }).formKind, formKind));
  for (let theta = 0; theta <= 180; theta += 15) {
    const s = state({ ...spectralDefault, lambda1: 1.25, lambda2: 1.25, theta });
    assert.deepEqual(s.matrix, [[1.25, 0], [0, 1.25]]);
    assert.equal(s.eigenDirectionsUnique, false); assert.equal(s.singularDirectionsUnique, false);
  }
  for (const [theta, matrix] of [[0, [[2, 0], [0, .5]]], [90, [[.5, 0], [0, 2]]], [180, [[2, 0], [0, .5]]]]) {
    assert.deepEqual(state({ ...spectralDefault, theta }).matrix, matrix);
  }
  const opposite = state({ ...spectralDefault, lambda1: -2, lambda2: 2 });
  assert.equal(opposite.eigenDirectionsUnique, true); assert.equal(opposite.singularDirectionsUnique, false);
  const collapsed = state({ ...spectralDefault, lambda1: 0, lambda2: 0 });
  assert.equal(collapsed.rank, 0); assert.deepEqual(collapsed.transformed, [0, 0]);
});

test('parameter validation rejects nonfinite, absent, off-grid and unsupported values', () => {
  const specs = [
    ['mapState', mapDefault, Object.fromEntries(Object.keys(mapDefault).map(key => [key, [-2.25, 2.25, .1]]))],
    ['leastSquaresState', lsDefault, { y0: [-2.25, 2.25, .1], y1: [-2.25, 2.25, .1], y2: [-2.25, 2.25, .1], deltaA: [-1.25, 1.25, .1], deltaB: [-1.25, 1.25, .1] }],
    ['spectralState', spectralDefault, { lambda1: [-2.25, 3.25, .1], lambda2: [-2.25, 3.25, .1], theta: [-15, 195, 7.5], x: [-2.25, 2.25, .1], y: [-2.25, 2.25, .1] }]
  ];
  const badTypes = [undefined, null, false, '1', NaN, Infinity, -Infinity, [], {}];
  specs.forEach(([name, valid, ranges]) => {
    const state = api(name);
    badTypes.forEach(value => assert.throws(() => state(value), TypeError));
    Object.entries(ranges).forEach(([key, values]) => {
      badTypes.forEach(value => assert.throws(() => state({ ...valid, [key]: value }), TypeError));
      values.forEach(value => assert.throws(() => state({ ...valid, [key]: value }), RangeError));
      const missing = { ...valid }; delete missing[key]; assert.throws(() => state(missing), TypeError);
    });
  });
});

test('classic and Node scripts expose the frozen MathLinearCore namespace without overwrites', () => {
  assert(fs.existsSync(source));
  const sentinel = Object.freeze({ preserved: true }), context = vm.createContext({ MathLinear: sentinel, MathOptimization: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathLinear, sentinel); assert.equal(context.MathOptimization, sentinel);
  assert.deepEqual(Object.keys(math).sort(), ['leastSquaresState', 'mapState', 'spectralState']);
  assert(Object.isFrozen(math)); assert(Object.isFrozen(context.MathLinearCore));
  assert.equal(context.MathLinearCore.mapState(mapDefault).determinant, .5);
});
