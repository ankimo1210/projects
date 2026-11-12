(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathDiscrete = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected parameters');
    return input;
  }
  function finite(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    return value === 0 ? 0 : value;
  }
  function integer(value, min, max) {
    value = finite(value);
    if (!Number.isInteger(value) || value < min || value > max) throw new RangeError('Outside the supported integer range');
    return value;
  }
  function modularState(input) {
    parameters(input);
    const m = integer(input.m, 2, 12), a = integer(input.a, 0, m - 1), x = integer(input.x, 0, m - 1);
    const residues = Array.from({ length: m }, (_, index) => a * index % m);
    const image = [...new Set(residues)].sort((left, right) => left - right);
    let first = a, second = m;
    while (second) [first, second] = [second, first % second];
    const inverseIndex = residues.indexOf(1);
    return { m, a, x, value: residues[x], residues, image, gcd: first, inverse: inverseIndex < 0 ? null : inverseIndex };
  }
  function recurrenceState(input) {
    parameters(input);
    const n = integer(input.n, 0, 20), values = [1];
    if (n > 0) values.push(1);
    for (let i = 2; i <= n; i++) values.push(values[i - 1] + values[i - 2]);
    const subproblems = n < 2 ? [] : [{ n: n - 1, value: values[n - 1] }, { n: n - 2, value: values[n - 2] }];
    return { n, value: values[n], values, subproblems, additions: Math.max(0, n - 1) };
  }
  function graphCopy(input) {
    parameters(input);
    if (!Array.isArray(input.vertices) || !Array.isArray(input.edges)) throw new TypeError('Expected vertex and edge arrays');
    if (!input.vertices.length) throw new RangeError('Expected a nonempty graph');
    const ids = new Set();
    const vertices = input.vertices.map(vertex => {
      parameters(vertex);
      if (typeof vertex.id !== 'string' || !vertex.id.length) throw new TypeError('Expected a nonempty vertex id');
      if (ids.has(vertex.id)) throw new RangeError('Duplicate vertex');
      ids.add(vertex.id);
      const result = { id: vertex.id };
      for (const key of ['x', 'y']) if (vertex[key] !== undefined) result[key] = finite(vertex[key]);
      return result;
    });
    const pairs = new Set();
    const edges = input.edges.map(edge => {
      parameters(edge);
      if (!ids.has(edge.from) || !ids.has(edge.to) || edge.from === edge.to) throw new RangeError('Invalid edge endpoints');
      const pair = JSON.stringify([edge.from, edge.to].sort());
      if (pairs.has(pair)) throw new RangeError('Duplicate undirected edge');
      pairs.add(pair);
      const weight = finite(edge.weight);
      if (weight < 0) throw new RangeError('Dijkstra requires nonnegative weights');
      return { from: edge.from, to: edge.to, weight };
    });
    return { vertices, edges };
  }
  function shortestPathState(input) {
    parameters(input);
    const graph = graphCopy(input.graph), source = input.source, target = input.target;
    const ids = graph.vertices.map(vertex => vertex.id);
    if (typeof source !== 'string' || typeof target !== 'string') throw new TypeError('Expected source and target vertex ids');
    if (!ids.includes(source) || !ids.includes(target)) throw new RangeError('Unknown source or target');
    const distances = Object.fromEntries(ids.map(id => [id, id === source ? 0 : Infinity]));
    const parents = Object.fromEntries(ids.map(id => [id, null]));
    const neighbors = new Map(ids.map(id => [id, []]));
    graph.edges.forEach(edge => {
      neighbors.get(edge.from).push({ id: edge.to, weight: edge.weight });
      neighbors.get(edge.to).push({ id: edge.from, weight: edge.weight });
    });
    // Vertex-array order breaks distance ties, independently of edge-array order.
    const order = new Map(ids.map((id, index) => [id, index]));
    neighbors.forEach(list => list.sort((left, right) => order.get(left.id) - order.get(right.id)));
    const settled = [], known = new Set(), steps = [];
    function route() {
      if (!Number.isFinite(distances[target])) return null;
      const path = [target];
      while (path[0] !== source) {
        const parent = parents[path[0]];
        if (parent === null || path.includes(parent)) return null;
        path.unshift(parent);
      }
      return path;
    }
    function snapshot(current, relaxations) {
      return { step: settled.length, current, settled: settled.slice(), distances: { ...distances }, parents: { ...parents }, relaxations, route: route(), distance: distances[target] };
    }
    steps.push(snapshot(null, []));
    while (true) {
      let current = null;
      for (const id of ids) if (!known.has(id) && Number.isFinite(distances[id]) && (current === null || distances[id] < distances[current])) current = id;
      if (current === null) break;
      known.add(current); settled.push(current);
      const relaxations = [];
      for (const neighbor of neighbors.get(current)) {
        if (known.has(neighbor.id)) continue;
        const distance = distances[current] + neighbor.weight;
        if (!Number.isFinite(distance)) throw new RangeError('Path weight exceeds finite-number range');
        if (distance < distances[neighbor.id]) {
          relaxations.push({ from: current, to: neighbor.id, previous: distances[neighbor.id], distance });
          distances[neighbor.id] = distance;
          parents[neighbor.id] = current;
        }
      }
      steps.push(snapshot(current, relaxations));
    }
    return { source, target, graph, steps, distances: { ...distances }, parents: { ...parents }, route: route(), distance: distances[target] };
  }
  const vertices = [['A', 50, 70], ['B', 180, 40], ['C', 305, 70], ['D', 50, 240], ['E', 180, 275], ['F', 305, 240]].map(([id, x, y]) => Object.freeze({ id, x, y }));
  Object.freeze(vertices);
  const baseEdges = [['A', 'B', 2], ['B', 'C', 2], ['A', 'D', 5], ['B', 'E', 1], ['C', 'F', 3], ['D', 'E', 1], ['E', 'F', 2]];
  function preset(transform) {
    const edges = baseEdges.map(([from, to, weight]) => ({ from, to, weight })).map(transform).filter(Boolean).map(Object.freeze);
    return Object.freeze({ vertices, edges: Object.freeze(edges) });
  }
  const shortestPresets = Object.freeze({
    normal: preset(edge => edge),
    zeroTie: preset(edge => ({ ...edge, weight: edge.from === 'A' && edge.to === 'B' ? 0 : edge.from === 'A' && edge.to === 'D' ? 2 : edge.weight })),
    disconnected: preset(edge => edge.from === 'F' || edge.to === 'F' ? null : edge)
  });
  return Object.freeze({ modularState, recurrenceState, shortestPathState, shortestPresets });
}));
