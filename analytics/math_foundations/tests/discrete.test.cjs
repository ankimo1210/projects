'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = path.join(__dirname, '../assets/discrete.js');
const math = fs.existsSync(source) ? require(source) : {};
const api = name => { assert.equal(typeof math[name], 'function', `${name} must be implemented`); return math[name]; };

// Repeated addition with wraparound and trial divisors are independent of the
// production multiplication/modulo and Euclidean algorithm.
function wrapProduct(a, x, m) {
  let result = 0;
  for (let i = 0; i < x; i++) { result += a; while (result >= m) result -= m; }
  return result;
}
function divisorGcd(a, m) {
  let greatest = 1;
  for (let d = 1; d <= m; d++) if (a / d === Math.floor(a / d) && m / d === Math.floor(m / d)) greatest = d;
  return greatest;
}

test('modular multiplication, image and inverse match exhaustive residue enumeration', () => {
  const state = api('modularState');
  for (let m = 2; m <= 12; m++) for (let a = 0; a < m; a++) {
    const expected = Array.from({ length: m }, (_, x) => wrapProduct(a, x, m));
    const inverse = expected.findIndex(value => value === 1);
    for (let x = 0; x < m; x++) {
      const s = state(Object.freeze({ m, a, x }));
      assert.equal(s.value, expected[x]); assert.deepEqual(s.residues, expected);
      assert.deepEqual(s.image, [...new Set(expected)].sort((u, v) => u - v));
      assert.equal(s.gcd, divisorGcd(a, m));
      assert.equal(s.inverse, inverse === -1 ? null : inverse);
      assert.equal(s.image.length * s.gcd, m);
      assert.equal(s.inverse !== null, s.image.length === m);
      if (s.inverse !== null) assert.equal(wrapProduct(a, s.inverse, m), 1);
    }
  }
});

test('noninvertible zero multiplier remains different from an invertible zero output', () => {
  const state = api('modularState');
  const zero = state({ m: 6, a: 0, x: 5 });
  assert.equal(zero.value, 0); assert.equal(zero.gcd, 6); assert.equal(zero.inverse, null); assert.deepEqual(zero.image, [0]);
  const invertible = state({ m: 6, a: 5, x: 0 });
  assert.equal(invertible.value, 0); assert.equal(invertible.inverse, 5);
});

// A tiling corresponds to a subset of the n-1 internal boundaries at which
// dominoes start; neighboring starts are forbidden. No recurrence is used.
function enumerateTilings(n) {
  if (n < 2) return 1;
  let count = 0;
  for (let starts = 0; starts < 2 ** (n - 1); starts++) if ((starts & (starts << 1)) === 0) count++;
  return count;
}

test('tiling recurrence matches independent nonoverlapping-domino enumeration including empty board', () => {
  const state = api('recurrenceState');
  for (let n = 0; n <= 8; n++) {
    const s = state(Object.freeze({ n }));
    assert.equal(s.value, enumerateTilings(n)); assert.equal(s.values.length, n + 1);
    s.values.forEach((value, index) => assert.equal(value, enumerateTilings(index)));
    assert.equal(s.additions, Math.max(0, n - 1));
    if (n < 2) assert.deepEqual(s.subproblems, []);
    else assert.deepEqual(s.subproblems, [{ n: n - 1, value: enumerateTilings(n - 1) }, { n: n - 2, value: enumerateTilings(n - 2) }]);
  }
});

test('n=20 is exact and cached results cannot leak mutations between calls', () => {
  const state = api('recurrenceState');
  const s = state({ n: 20 });
  assert.equal(s.value, 10946); assert.equal(s.additions, 19);
  assert.deepEqual(s.subproblems, [{ n: 19, value: 6765 }, { n: 18, value: 4181 }]);
  assert(s.values.every(Number.isSafeInteger));
  s.values[0] = 999; assert.equal(state({ n: 20 }).values[0], 1);
  const modular = api('modularState')({ m: 7, a: 3, x: 4 }); modular.image[0] = 999;
  assert.equal(api('modularState')({ m: 7, a: 3, x: 4 }).image[0], 0);
});

function allSimplePaths(graph, source, target) {
  const answers = [];
  function visit(current, route, weight) {
    if (current === target) { answers.push({ route, weight }); return; }
    for (const edge of graph.edges) {
      const next = edge.from === current ? edge.to : edge.to === current ? edge.from : null;
      if (next !== null && !route.includes(next)) visit(next, route.concat(next), weight + edge.weight);
    }
  }
  visit(source, [source], 0);
  return answers;
}

test('every preset distance and reconstructed route agree with all-simple-path search from every source', () => {
  const state = api('shortestPathState');
  assert(math.shortestPresets, 'shortest presets must be available');
  for (const graph of Object.values(math.shortestPresets)) for (const source of graph.vertices.map(v => v.id)) for (const target of graph.vertices.map(v => v.id)) {
    const candidates = allSimplePaths(graph, source, target);
    const expected = candidates.length ? Math.min(...candidates.map(p => p.weight)) : Infinity;
    const s = state({ graph, source, target });
    assert.equal(s.distance, expected, `${source} to ${target}`);
    assert.equal(s.distances[target], expected);
    if (expected === Infinity) assert.equal(s.route, null);
    else assert(candidates.some(p => p.weight === expected && JSON.stringify(p.route) === JSON.stringify(s.route)), JSON.stringify(s.route));
  }
});

test('normal graph has the stated route and preserves independent initial and settled snapshots', () => {
  const s = api('shortestPathState')({ graph: math.shortestPresets.normal, source: 'A', target: 'F' });
  assert.deepEqual(s.route, ['A', 'B', 'E', 'F']); assert.equal(s.distance, 5);
  assert.deepEqual(s.distances, { A: 0, B: 2, C: 4, D: 4, E: 3, F: 5 });
  const initial = s.steps[0];
  assert.equal(initial.step, 0); assert.equal(initial.current, null); assert.deepEqual(initial.settled, []);
  assert.deepEqual(initial.distances, { A: 0, B: Infinity, C: Infinity, D: Infinity, E: Infinity, F: Infinity });
  assert.equal(initial.route, null); assert.deepEqual(initial.relaxations, []);
  assert.deepEqual(s.steps.map(step => step.current), [null, 'A', 'B', 'E', 'C', 'D', 'F']);
  assert.deepEqual(s.steps[1].relaxations.map(r => [r.from, r.to, r.previous, r.distance]), [['A', 'B', Infinity, 2], ['A', 'D', Infinity, 5]]);
  for (let i = 1; i < s.steps.length; i++) {
    const step = s.steps[i], previous = s.steps[i - 1];
    assert.equal(step.step, i); assert.equal(step.settled.length, i);
    assert.deepEqual(step.settled.slice(0, -1), previous.settled);
    assert.equal(step.current, step.settled[i - 1]);
    for (const v of step.settled) assert.equal(step.distances[v], s.distances[v]);
    for (const v of Object.keys(step.distances)) assert(step.distances[v] <= previous.distances[v]);
    if (i > 1) assert(step.distances[step.current] >= previous.distances[previous.current]);
  }
  s.steps.at(-1).distances.B = 999; s.steps.at(-1).settled.push('X');
  assert.equal(s.steps[1].distances.B, 2); assert.equal(s.distances.B, 2); assert.deepEqual(initial.settled, []);
});

test('zero edge and deterministic ties differ from disconnection', () => {
  const state = api('shortestPathState');
  const zero = state({ graph: math.shortestPresets.zeroTie, source: 'A', target: 'B' });
  assert.equal(zero.distance, 0); assert.deepEqual(zero.route, ['A', 'B']);
  assert.deepEqual(zero.steps.map(s => s.current), [null, 'A', 'B', 'E', 'C', 'D', 'F']);
  assert.equal(zero.parents.D, 'A', 'equal relaxation retains the first parent');
  const missing = state({ graph: math.shortestPresets.disconnected, source: 'A', target: 'F' });
  assert.equal(missing.distance, Infinity); assert.equal(missing.route, null); assert.equal(missing.parents.F, null);
  assert.equal(missing.steps.length, 6); assert(!missing.steps.at(-1).settled.includes('F'));
});

test('single vertex, isolated source and a zero-weight cycle have sound routes', () => {
  const state = api('shortestPathState');
  const graph = { vertices: ['S', 'T', 'U', 'V'].map(id => ({ id })), edges: [{ from: 'S', to: 'T', weight: 0 }, { from: 'T', to: 'U', weight: 0 }, { from: 'S', to: 'U', weight: 0 }] };
  const self = state({ graph, source: 'S', target: 'S' }); assert.equal(self.distance, 0); assert.deepEqual(self.route, ['S']);
  const zero = state({ graph, source: 'S', target: 'U' }); assert.equal(zero.distance, 0); assert.deepEqual(zero.route, ['S', 'U']);
  const isolated = state({ graph, source: 'V', target: 'S' }); assert.equal(isolated.steps.length, 2); assert.equal(isolated.route, null);
  const single = state({ graph: { vertices: [{ id: 'S' }], edges: [] }, source: 'S', target: 'S' }); assert.equal(single.steps.length, 2); assert.deepEqual(single.route, ['S']);
});

test('modular and recurrence APIs reject missing, nonfinite, fractional and out-of-domain parameters', () => {
  const badTypes = [undefined, null, false, '2', NaN, Infinity, -Infinity, [], {}];
  for (const [name, valid] of [['modularState', { m: 6, a: 5, x: 4 }], ['recurrenceState', { n: 5 }]]) {
    const state = api(name);
    for (const bad of badTypes) assert.throws(() => state(bad), TypeError);
    for (const key of Object.keys(valid)) for (const bad of badTypes) assert.throws(() => state({ ...valid, [key]: bad }), TypeError);
  }
  for (const m of [1, 13, 2.5]) assert.throws(() => api('modularState')({ m, a: 0, x: 0 }), RangeError);
  for (const key of ['a', 'x']) for (const bad of [-1, 6, .5]) assert.throws(() => api('modularState')({ m: 6, a: 1, x: 1, [key]: bad }), RangeError);
  for (const n of [-1, .5, 21]) assert.throws(() => api('recurrenceState')({ n }), RangeError);
});

test('Dijkstra rejects bad graph domains, vertices, endpoints and negative or nonfinite weights', () => {
  const state = api('shortestPathState');
  const graph = { vertices: [{ id: 'A' }, { id: 'B' }], edges: [{ from: 'A', to: 'B', weight: 1 }] };
  const run = g => state({ graph: g, source: 'A', target: 'B' });
  for (const bad of [undefined, null, [], 'graph', 0]) assert.throws(() => run(bad), TypeError);
  for (const bad of [undefined, null, NaN, Infinity, -Infinity, '1', false]) assert.throws(() => run({ ...graph, edges: [{ from: 'A', to: 'B', weight: bad }] }), TypeError);
  assert.throws(() => run({ ...graph, edges: [{ from: 'A', to: 'B', weight: -1 }] }), RangeError);
  for (const bad of ['', 'Z', null, NaN]) {
    assert.throws(() => state({ graph, source: bad, target: 'B' }));
    assert.throws(() => state({ graph, source: 'A', target: bad }));
  }
  for (const invalid of [
    { vertices: [], edges: [] },
    { vertices: [{ id: 'A' }, { id: 'A' }], edges: [] },
    { vertices: [{ id: 'A', x: NaN }], edges: [] },
    { ...graph, edges: [{ from: 'A', to: 'Z', weight: 1 }] },
    { ...graph, edges: [{ from: 'A', to: 'A', weight: 1 }] },
    { ...graph, edges: graph.edges.concat({ from: 'B', to: 'A', weight: 2 }) }
  ]) assert.throws(() => run(invalid));
});

test('discrete classic script exports a frozen namespace without changing other globals or presets', () => {
  assert(fs.existsSync(source), 'discrete module must exist');
  const sentinel = Object.freeze({ untouched: true });
  const context = vm.createContext({ MathProbability: sentinel });
  vm.runInContext(fs.readFileSync(source, 'utf8'), context);
  assert.equal(context.MathProbability, sentinel); assert(Object.isFrozen(context.MathDiscrete));
  assert.equal(context.MathDiscrete.recurrenceState({ n: 20 }).value, 10946);
  assert(Object.isFrozen(math.shortestPresets));
  assert(Object.values(math.shortestPresets).every(graph => Object.isFrozen(graph) && Object.isFrozen(graph.vertices) && Object.isFrozen(graph.edges) && graph.edges.every(Object.isFrozen)));
});
