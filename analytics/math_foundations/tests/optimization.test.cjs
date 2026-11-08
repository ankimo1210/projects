'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/optimization.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };
function close(actual, expected, tolerance = 2e-11) {
  assert(Number.isFinite(actual));
  assert(Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`);
}

// Powers of the diagonal eigenvalues are an oracle independent of repeated
// gradient subtraction. Check every stored step, including unstable orbits.
test('gradient updates agree with the independent closed form over the finite domain', () => {
  const state = api('gradientState');
  for (let kappa = 1; kappa <= 16; kappa++) for (let ia = 0; ia <= 20; ia++) {
    const alpha = ia / 40;
    for (const [x0, y0] of [[-2, 2], [1, 1], [0, -1], [1, 0], [0, 0]]) for (const n of [0, 1, 12, 40]) {
      const s = state(Object.freeze({ kappa, alpha, n, x0, y0 }));
      assert.equal(s.points.length, n + 1);
      const qx = 1 - alpha, qy = 1 - alpha * kappa;
      close(s.factors[0], qx); close(s.factors[1], qy);
      close(s.rho, Math.max(Math.abs(qx), Math.abs(qy))); close(s.criticalAlpha, 2 / kappa);
      assert.equal(s.contractsAll, alpha > 0 && alpha < 2 / kappa);
      s.points.forEach((p, iteration) => {
        const x = x0 * qx ** iteration, y = y0 * qy ** iteration;
        assert.equal(p.iteration, iteration); close(p.x, x); close(p.y, y);
        close(p.objective, (x * x + kappa * y * y) / 2);
        close(p.gradient[0], x); close(p.gradient[1], kappa * y);
        close(p.gradientNorm, Math.hypot(x, kappa * y));
        if (p.objective === 0) assert.equal(p.logObjective, null);
        else close(p.logObjective, Math.log10(p.objective));
      });
      close(s.final[0], x0 * qx ** n); close(s.final[1], y0 * qy ** n);
      close(s.objective, s.points[n].objective);
      close(s.initialObjective, (x0 * x0 + kappa * y0 * y0) / 2);
      if (s.initialObjective === 0) assert.equal(s.objectiveRatio, null);
      else close(s.objectiveRatio, s.objective / s.initialObjective);
    }
  }
});

test('global contraction, exceptional initial data, boundaries and zero steps remain distinct', () => {
  const state = api('gradientState'), input = { kappa: 4, alpha: .15, n: 12, x0: 1, y0: 1 };
  const stopped = state({ ...input, n: 0 });
  assert.deepEqual(stopped.final, [1, 1]); assert.equal(stopped.objectiveRatio, 1);
  for (const alpha of [0, .5]) {
    const s = state({ ...input, alpha });
    assert.equal(s.contractsAll, false); assert.equal(s.allInitialState, 'boundary');
    assert.equal(s.trajectoryConverges, false); assert.equal(s.trajectoryState, 'boundary');
  }
  const unstable = state({ ...input, kappa: 16, alpha: .5, n: 40, x0: 2, y0: 2 });
  assert.equal(unstable.allInitialState, 'unstable'); assert.equal(unstable.trajectoryState, 'unstable');
  assert(unstable.objective > 1e68 && unstable.objective < 2e69);
  const axis = state({ ...input, kappa: 16, alpha: .5, y0: 0 });
  assert.equal(axis.contractsAll, false); assert.equal(axis.trajectoryConverges, true); assert.equal(axis.trajectoryState, 'contracting');
  const origin = state({ ...input, kappa: 16, alpha: .5, x0: 0, y0: 0 });
  assert.equal(origin.trajectoryState, 'fixed-origin'); assert.equal(origin.trajectoryConverges, true);
  assert.equal(origin.objectiveRatio, null); assert(origin.points.every(p => p.objective === 0 && p.logObjective === null));
  const finiteZero = state({ ...input, kappa: 2, alpha: .5, x0: 0, n: 1 });
  assert.deepEqual(finiteZero.final, [0, 0]); assert.equal(finiteZero.objectiveRatio, 0);
  for (let kappa = 1; kappa <= 16; kappa++) {
    const critical = 2 / kappa;
    if (critical <= .5) {
      const s = state({ ...input, kappa, alpha: critical, n: 1, x0: 0 });
      assert.equal(s.factors[1], -1); assert.equal(s.final[1], -1); assert.equal(s.contractsAll, false);
    }
  }
});

// Verify the characterizing variational inequality against independently
// generated feasible points, as well as the nearest-distance property.
test('disk and box projections satisfy distance minimality and the variational inequality', () => {
  const state = api('projectionState');
  for (const kind of ['disk', 'box']) for (const radius of [.5, 1, 1.5]) {
    const feasible = kind === 'disk'
      ? Array.from({ length: 33 }, (_, k) => [radius * Math.cos(k * Math.PI / 16), radius * Math.sin(k * Math.PI / 16)]).concat([[0, 0], [radius / 3, -radius / 3]])
      : [-1, -.5, 0, .5, 1].flatMap(u => [-1, -.5, 0, .5, 1].map(v => [radius * u, radius * v]));
    for (let ix = -8; ix <= 8; ix++) for (let iy = -8; iy <= 8; iy++) {
      const x = ix / 4, y = iy / 4, s = state(Object.freeze({ kind, x, y, radius }));
      const [qx, qy] = s.projected, [rx, ry] = s.residual;
      close(rx, x - qx); close(ry, y - qy); close(s.distance, Math.hypot(rx, ry));
      close(s.objective, ((x - qx) ** 2 + (y - qy) ** 2) / 2);
      assert(kind === 'disk' ? Math.hypot(qx, qy) <= radius + 1e-12 : Math.max(Math.abs(qx), Math.abs(qy)) <= radius);
      const inputInside = kind === 'disk' ? Math.hypot(x, y) <= radius : Math.max(Math.abs(x), Math.abs(y)) <= radius;
      if (inputInside) { assert.deepEqual(s.projected, [x, y]); assert.equal(s.distance, 0); assert.equal(s.residualUnit, null); }
      else { close(Math.hypot(...s.residualUnit), 1); close(s.residualUnit[0] * s.distance, rx); close(s.residualUnit[1] * s.distance, ry); }
      if (!inputInside && kind === 'disk') {
        close(Math.hypot(qx, qy), radius); close(x * qy - y * qx, 0);
        assert(x * qx + y * qy > 0);
      }
      for (const [zx, zy] of feasible) {
        assert(rx * (zx - qx) + ry * (zy - qy) <= 2e-11);
        assert(s.distance <= Math.hypot(x - zx, y - zy) + 2e-11);
      }
    }
  }
  for (const kind of ['disk', 'box']) {
    const boundary = state({ kind, x: 1, y: 0, radius: 1 });
    assert.equal(boundary.inputLocation, 'boundary'); assert.equal(boundary.residualUnit, null);
  }
  const corner = state({ kind: 'box', x: 2, y: 2, radius: 1 });
  assert.deepEqual(corner.projected, [1, 1]); assert.deepEqual(corner.residual, [1, 1]);
});

test('KKT model verifies its dual lower bound, optimal multiplier and stable nonnegative gap', () => {
  const state = api('kktState');
  for (let ia = -20; ia <= 20; ia += 2) for (let ib = -15; ib <= 15; ib += 3) for (let il = 0; il <= 40; il += 2) {
    const a = ia / 10, b = ib / 10, lambda = il / 10, s = state(Object.freeze({ a, b, lambda }));
    const candidate = Math.max(a, b), minimizingLagrangianX = a + lambda;
    const lagrangianInf = (minimizingLagrangianX - a) ** 2 / 2 + lambda * (b - minimizingLagrangianX);
    close(s.xStar, candidate); close(s.lambdaStar, Math.max(0, b - a));
    close(s.primalOptimal, (candidate - a) ** 2 / 2); close(s.dualValue, lagrangianInf);
    assert(s.dualGap >= 0); close(s.dualGap, s.primalOptimal - lagrangianInf);
    close(s.stationarity, candidate - a - lambda); close(s.gValue, b - candidate);
    close(s.slack, candidate - b); close(s.complementarity, lambda * (b - candidate));
    assert.equal(s.active, candidate === b); assert.equal(s.dualFeasible, true);
    assert.equal(s.kktSatisfied, lambda === Math.max(0, b - a));
    for (const offset of [0, .1, 1, 4]) {
      const feasibleX = b + offset, objective = (feasibleX - a) ** 2 / 2;
      assert(s.dualValue <= objective + 1e-12); assert(s.primalOptimal <= objective + 1e-12);
    }
    const optimal = state({ a, b, lambda: s.lambdaStar });
    assert.equal(optimal.dualGap, 0); close(optimal.stationarity, 0); close(optimal.complementarity, 0);
    assert.equal(optimal.kktSatisfied, true);
  }
  const activeZero = state({ a: .5, b: .5, lambda: 0 });
  assert.equal(activeZero.active, true); assert.equal(activeZero.lambdaStar, 0); assert.equal(activeZero.kktSatisfied, true);
  const arbitrary = state({ a: 0, b: 1, lambda: 0 });
  assert.equal(arbitrary.dualFeasible, true); assert.equal(arbitrary.kktSatisfied, false); assert.equal(arbitrary.stationarity, 1);
  const tinyGap = state({ a: 0, b: 1, lambda: 1 + 1e-8 });
  assert(tinyGap.dualGap > 0); close(tinyGap.dualGap, (1e-8) ** 2 / 2, 1e-23);
  const decimal = state({ a: .1, b: .3, lambda: .2 });
  assert.equal(decimal.stationarity, .3 - .1 - .2);
  assert(decimal.stationarity !== 0 && decimal.dualGap > 0); assert.equal(decimal.kktSatisfied, false);
});

test('numeric types, finite ranges, integer fields and projection names are checked', () => {
  const specifications = [
    ['gradientState', { kappa: 4, alpha: .15, n: 12, x0: 1, y0: 1 }, { kappa: [0, 1.5, 17], alpha: [-.01, .501], n: [-1, .5, 41], x0: [-2.01, 2.01], y0: [-2.01, 2.01] }],
    ['projectionState', { kind: 'disk', x: 1.5, y: 1, radius: 1 }, { x: [-2.01, 2.01], y: [-2.01, 2.01], radius: [.49, 1.51] }],
    ['kktState', { a: 0, b: 1, lambda: 0 }, { a: [-2.01, 2.01], b: [-1.51, 1.51], lambda: [-.01, 4.01] }]
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
  for (const kind of [null, 1, false, {}]) assert.throws(() => api('projectionState')({ kind, x: 0, y: 0, radius: 1 }), TypeError);
  assert.throws(() => api('projectionState')({ kind: 'triangle', x: 0, y: 0, radius: 1 }), RangeError);
});

test('classic and Node scripts expose exactly the frozen MathOptimization API', () => {
  assert(fs.existsSync(source));
  const sentinel = Object.freeze({ preserved: true }), context = vm.createContext({ MathNumerical: sentinel, MathVector: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathNumerical, sentinel); assert.equal(context.MathVector, sentinel);
  assert.deepEqual(Object.keys(math).sort(), ['gradientState', 'kktState', 'projectionState']);
  assert(Object.isFrozen(context.MathOptimization)); assert(Object.isFrozen(math));
  assert.equal(context.MathOptimization.kktState({ a: 0, b: 1, lambda: 1 }).dualGap, 0);
});
