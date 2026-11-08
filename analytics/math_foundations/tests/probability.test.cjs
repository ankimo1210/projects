'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assets = path.join(__dirname, '../assets');
const source = path.join(assets, 'probability.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };
function close(actual, expected, tolerance = 1e-12) { assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance * Math.max(1, Math.abs(expected)), `${actual} != ${expected}`); }
const bayes = extra => ({ prior: .01, sensitivity: .9, falsePositive: .05, ...extra });
const independent = extra => ({ a: .5, b: .5, joint: .25, ...extra });
const lln = extra => ({ n: 100, p: .5, epsilon: .1, seed: 42, ...extra });

test('Bayes factory model distinguishes joint masses and posterior', () => {
  const s = api('bayesState')(Object.freeze(bayes()));
  close(s.truePositive, .009); close(s.falsePositiveMass, .0495);
  close(s.positive, .0585); close(s.posterior, 2 / 13);
  assert.equal(s.cells.length, 4); close(s.cells.reduce((a, b) => a + b), 1);
  s.cells.forEach(v => assert(v >= 0));
});

test('Bayes endpoint models preserve undefined conditioning as null', () => {
  const state = api('bayesState');
  for (const prior of [0, .01, .5, 1]) for (const sensitivity of [0, .9, 1]) for (const falsePositive of [0, .05, 1]) {
    const s = state({ prior, sensitivity, falsePositive });
    close(s.cells.reduce((a, b) => a + b), 1); s.cells.forEach(v => assert(v >= 0 && v <= 1));
    if (s.positive === 0) assert.equal(s.posterior, null);
    else close(s.posterior * s.positive, s.truePositive);
  }
  assert.equal(state(bayes({ sensitivity: 0, falsePositive: 0 })).posterior, null);
  assert.equal(state(bayes({ prior: 0 })).posterior, 0);
  assert.equal(state(bayes({ prior: 1 })).posterior, 1);
});

test('independence uses a feasible nonnegative joint table and conditional denominator B', () => {
  const state = api('independenceState');
  const s = state(independent({ a: .3, b: .6, joint: .18 }));
  close(s.product, .18); close(s.difference, 0); close(s.conditional, .3);
  s.cells.forEach((v, i) => close(v, [.18, .12, .42, .28][i]));
  for (const a of [0, .1, .3, .8, 1]) for (const b of [0, .2, .7, .9, 1]) {
    for (const joint of [Math.min(a, b, Math.max(0, a + b - 1)), a * b, Math.min(a, b)]) {
      let result;
      assert.doesNotThrow(() => { result = state({ a, b, joint }); }, JSON.stringify({ a, b, joint }));
      assert(result.cells.every(v => v >= 0)); close(result.cells.reduce((x, y) => x + y), 1);
      close(result.cells[0] + result.cells[1], a); close(result.cells[0] + result.cells[2], b);
      if (b === 0) assert.equal(result.conditional, null); else close(result.conditional, joint / b);
    }
  }
});

test('independence rejects joint probabilities outside the Frechet bounds', () => {
  const state = api('independenceState');
  for (const joint of [.099, .401]) assert.throws(() => state(independent({ a: .7, b: .4, joint })), RangeError);
  assert.throws(() => state(independent({ a: 0, joint: 1e-10 })), RangeError);
});

test('independence accepts decimal lower endpoints without changing the requested joint mass', () => {
  const state = api('independenceState');
  for (const input of [{ a: .8, b: .8, joint: .6 }, { a: .15, b: .9, joint: .05 }]) {
    let s;
    assert.doesNotThrow(() => { s = state(input); }, JSON.stringify(input));
    assert.equal(s.joint, input.joint); assert.equal(s.cells[3], 0);
    close(s.cells.reduce((sum, mass) => sum + mass, 0), 1);
  }
});

test('independence accepts every reachable decimal UI grid point and rejects genuine outside values', () => {
  const state = api('independenceState');
  const failures = [];
  let checked = 0;
  // Use integer hundredths, independently of the implementation and browser slider arithmetic.
  for (let ai = 10; ai <= 90; ai += 5) for (let bi = 10; bi <= 90; bi += 5) {
    const a = ai / 100, b = bi / 100, lower = Math.max(0, ai + bi - 100), upper = Math.min(ai, bi);
    for (let ji = lower; ji <= upper; ji++) {
      const joint = ji / 100;
      let s;
      try { s = state({ a, b, joint }); } catch (error) { failures.push({ a, b, joint, error: error.name }); continue; }
      checked++;
      assert.equal(s.joint, joint); assert(s.cells.every(mass => Number.isFinite(mass) && mass >= 0));
      close(s.cells.reduce((sum, mass) => sum + mass, 0), 1);
      close(s.cells[0] + s.cells[1], a); close(s.cells[0] + s.cells[2], b);
    }
    if (lower > 0) for (const gap of [1e-13, 1e-6]) assert.throws(() => state({ a, b, joint: lower / 100 - gap }), RangeError);
    for (const gap of [Number.EPSILON, 1e-6]) assert.throws(() => state({ a, b, joint: upper / 100 + gap }), RangeError);
  }
  assert.equal(failures.length, 0, `Rejected decimal grid points: ${JSON.stringify(failures)}`);
  assert.equal(checked, 6579);
  // The upper bound min(a,b) has no arithmetic cancellation and remains strict even near zero.
  assert.throws(() => state({ a: 0, b: .5, joint: Number.MIN_VALUE }), RangeError);
});

test('binomial PMF and CDF match hand calculations and moments', () => {
  const s = api('binomialState')({ n: 4, p: .5 });
  assert.equal(s.pmf.length, 5); assert.equal(s.cdf.length, 5);
  [1, 4, 6, 4, 1].forEach((v, k) => close(s.pmf[k], v / 16));
  [1, 5, 11, 15, 16].forEach((v, k) => close(s.cdf[k], v / 16));
  close(s.mean, 2); close(s.variance, 1);
  const t = api('binomialState')({ n: 3, p: .2 });
  [.512, .384, .096, .008].forEach((v, k) => close(t.pmf[k], v));
});

test('binomial is normalized at endpoints, extreme probabilities and n=200', () => {
  const state = api('binomialState');
  for (const n of [1, 2, 40, 200]) for (const p of [0, Number.MIN_VALUE, 1e-12, .01, .3, .5, .99, 1 - 1e-12, 1]) {
    const s = state(Object.freeze({ n, p }));
    assert.equal(s.pmf.length, n + 1); assert.equal(s.cdf.length, n + 1);
    close(s.pmf.reduce((a, b) => a + b), 1); assert.equal(s.cdf[n], 1);
    let sum = 0;
    s.pmf.forEach((v, k) => { assert(Number.isFinite(v) && v >= 0 && v <= 1); sum += v; close(s.cdf[k], sum); if (k) assert(s.cdf[k] >= s.cdf[k - 1]); });
    close(s.pmf.reduce((a, v, k) => a + k * v, 0), n * p);
    close(s.pmf.reduce((a, v, k) => a + (k - s.mean) ** 2 * v, 0), s.variance);
    if (p === 0 || p === 1) { assert.equal(s.pmf[p === 0 ? 0 : n], 1); assert.equal(s.pmf.filter(v => v !== 0).length, 1); }
  }
  const first = state({ n: 4, p: .5 }), second = state({ n: 4, p: .5 }); first.pmf[0] = 9; close(second.pmf[0], 1 / 16);
});

test('density has exact CDF values, integrates to one, and may exceed height one', () => {
  const state = api('densityState');
  for (const b of [0, .25, .5, .75, 1]) { const s = state(b); close(s.b, b); close(s.density, 2 * b); close(s.probability, b * b); }
  assert.equal(state(1).probability, 1); assert.equal(state(1).density, 2);
  // On each interval a linear density integrates exactly by the trapezoid rule.
  close((state(.25).density + state(.75).density) / 2 * .5, state(.75).probability - state(.25).probability);
});

test('LLN LCG has known first values, deterministic seed prefixes and endpoint means', () => {
  const state = api('llnState');
  const short = state(lln({ n: 8 })), long = state(lln({ n: 200 }));
  [1, 1, 2 / 3, .75, .8, 5 / 6, 6 / 7, .875].forEach((v, i) => close(short.trajectory[i], v));
  assert.deepEqual(long.trajectory.slice(0, 8), short.trajectory); close(short.mean, .875);
  assert.deepEqual(state(lln({ n: 8 })).trajectory, short.trajectory);
  assert.notDeepEqual(state(lln({ n: 8, seed: 43 })).trajectory, short.trajectory);
  for (const p of [0, 1]) { const s = state(lln({ p, seed: 4294967295 })); assert(s.trajectory.every(v => v === p)); assert.equal(s.mean, p); assert.equal(s.bound, 0); assert.equal(s.exactTail, 0); }
});

test('LLN exact tail agrees with independent enumeration of all small Bernoulli sequences', () => {
  const state = api('llnState');
  for (let n = 1; n <= 8; n++) for (const p of [0, .25, .5, .75, 1]) for (const epsilon of [.125, .25, .5, 1]) {
    let expected = 0;
    for (let bits = 0; bits < 2 ** n; bits++) {
      let successes = 0, weight = 1;
      for (let i = 0; i < n; i++) { const success = (bits >>> i) & 1; successes += success; weight *= success ? p : 1 - p; }
      // All parameters here are exact eighths; this integer inequality has no rounding boundary.
      if (Math.abs(8 * successes - n * (8 * p)) >= n * (8 * epsilon)) expected += weight;
    }
    const s = state(lln({ n, p, epsilon })); close(s.exactTail, expected);
    close(s.bound, Math.min(1, p * (1 - p) / (n * epsilon ** 2)));
    assert(s.exactTail >= 0 && s.exactTail <= 1 && s.exactTail <= s.bound + 1e-12);
  }
});

test('LLN includes equality at decimal boundaries and excludes the exact mean for tiny epsilon', () => {
  const state = api('llnState');
  const pmf = api('binomialState')({ n: 10, p: .3 }).pmf;
  const expected = pmf.reduce((sum, v, k) => sum + (k <= 2 || k >= 4 ? v : 0), 0);
  close(state(lln({ n: 10, p: .3, epsilon: .1 })).exactTail, expected);
  close(state(lln({ n: 10, p: .3, epsilon: .100000000001 })).exactTail, expected - pmf[2] - pmf[4]);
  close(state(lln({ n: 2, p: .5, epsilon: Number.MIN_VALUE })).exactTail, .5);
  assert.equal(state(lln({ n: 2, p: .5, epsilon: Number.MIN_VALUE })).bound, 1);
  close(state(lln({ n: 100, p: .5, epsilon: .1 })).bound, .25);
});

test('all probability APIs reject incorrect types and finite values outside supported domains', () => {
  const objectCases = [['bayesState', bayes(), ['prior', 'sensitivity', 'falsePositive']], ['independenceState', independent(), ['a', 'b', 'joint']], ['binomialState', { n: 10, p: .5 }, ['n', 'p']], ['llnState', lln(), ['n', 'p', 'epsilon', 'seed']]];
  const badTypes = [undefined, null, '0.5', NaN, Infinity, -Infinity, true, {}, []];
  for (const [name, valid, keys] of objectCases) {
    const state = api(name);
    for (const bad of badTypes) assert.throws(() => state(bad), TypeError);
    for (const key of keys) for (const bad of badTypes) assert.throws(() => state({ ...valid, [key]: bad }), TypeError);
  }
  const density = api('densityState');
  for (const bad of badTypes) assert.throws(() => density(bad), TypeError);
  for (const bad of [-1e-12, 1.000000000001]) assert.throws(() => density(bad), RangeError);
  for (const key of ['prior', 'sensitivity', 'falsePositive']) for (const bad of [-1e-12, 1.000000000001]) assert.throws(() => api('bayesState')(bayes({ [key]: bad })), RangeError);
  for (const key of ['a', 'b']) for (const bad of [-1e-12, 1.000000000001]) assert.throws(() => api('independenceState')(independent({ [key]: bad })), RangeError);
  for (const name of ['binomialState', 'llnState']) {
    const valid = name === 'llnState' ? lln() : { n: 10, p: .5 };
    for (const n of [0, -1, 1.5, 200.1, 201]) assert.throws(() => api(name)({ ...valid, n }), RangeError);
    for (const p of [-1e-12, 1.000000000001]) assert.throws(() => api(name)({ ...valid, p }), RangeError);
  }
  for (const epsilon of [-.1, 0, 1.000000001]) assert.throws(() => api('llnState')(lln({ epsilon })), RangeError);
  for (const seed of [-1, .5, 4294967296]) assert.throws(() => api('llnState')(lln({ seed })), RangeError);
});

test('probability UMD is frozen and coexists with existing math namespaces', () => {
  assert(fs.existsSync(source), 'probability module must exist');
  const context = vm.createContext({});
  const existing = [['math.js', 'MathFoundations'], ['calculus.js', 'MathCalculus'], ['linear.js', 'MathLinear'], ['multivariable.js', 'MathMultivariable'], ['multivariable-middle.js', 'MathMultivariableMiddle'], ['multivariable-integration.js', 'MathMultivariableIntegration']];
  for (const [file] of existing) vm.runInContext(fs.readFileSync(path.join(assets, file), 'utf8'), context);
  const snapshots = existing.map(([, name]) => [name, context[name], Object.keys(context[name])]);
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  for (const [name, object, keys] of snapshots) { assert.equal(context[name], object); assert.deepEqual(Object.keys(context[name]), keys); }
  assert(Object.isFrozen(context.MathProbability));
  assert.deepEqual(Object.keys(context.MathProbability).sort(), ['bayesState', 'binomialState', 'densityState', 'independenceState', 'llnState']);
  close(context.MathProbability.bayesState(bayes()).posterior, 2 / 13);
});
