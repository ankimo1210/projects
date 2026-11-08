(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathVector = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const clean = value => value === 0 ? 0 : value;
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected vector experiment parameters');
  }
  function bounded(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max) throw new RangeError('Outside the supported range');
    return clean(value);
  }
  function choice(value, choices) {
    if (typeof value !== 'string') throw new TypeError('Expected a name');
    if (!choices.includes(value)) throw new RangeError('Unsupported name');
    return value;
  }
  function direction(value) {
    bounded(value, -1, 1);
    if (value !== -1 && value !== 1) throw new RangeError('Expected orientation -1 or 1');
    return value;
  }
  function subdivisions(value, min, step) {
    bounded(value, min, 128);
    if (!Number.isInteger(value) || value % step !== 0) throw new RangeError('Unsupported subdivision count');
    return value;
  }
  function workState(input) {
    parameters(input);
    const field = choice(input.field, ['gradient', 'rotation']);
    const path = choice(input.path, ['straight', 'parabola', 'x-first', 'y-first']);
    const orientation = direction(input.orientation), n = subdivisions(input.n, 16, 16);
    // Each piece supplies (x,y,dx/dt,dy/dt), with its own t in [0,1].
    const paths = {
      straight: [t => [t, t, 1, 1]],
      parabola: [t => [t, t * t, 1, 2 * t]],
      'x-first': [t => [t, 0, 1, 0], t => [1, t, 0, 1]],
      'y-first': [t => [0, t, 0, 1], t => [t, 1, 1, 0]]
    };
    const pieces = paths[path], directedPieces = orientation === 1 ? pieces : [...pieces].reverse();
    let numeric = 0;
    for (const piece of directedPieces) for (let k = 0; k < n; k++) {
      const t = orientation === 1 ? (k + .5) / n : 1 - (k + .5) / n;
      const [x, y, dx, dy] = piece(t);
      const fx = field === 'gradient' ? y : -y;
      numeric += (fx * dx + x * dy) * orientation / n;
    }
    const exact = clean(orientation * (field === 'gradient' ? 1 : { straight: 0, parabola: 1 / 3, 'x-first': 1, 'y-first': -1 }[path]));
    return { field, path, orientation, n, domainState: 'defined', start: orientation === 1 ? [0, 0] : [1, 1], end: orientation === 1 ? [1, 1] : [0, 0], pieces: pieces.length, samples: pieces.length * n, exact, numeric: clean(numeric), error: Math.abs(numeric - exact) };
  }
  function fluxState(input) {
    parameters(input);
    const a = bounded(input.a, -1, 1), b = bounded(input.b, -1, 1), c = bounded(input.c, -2, 2), orientation = direction(input.orientation);
    const norm = Math.hypot(a, b, 1), normalArea = [-a, -b, 1].map(value => clean(orientation * value));
    return { a, b, c, orientation, domainState: 'defined', tangentU: [1, 0, a], tangentV: [0, 1, b], normalArea, unitNormal: normalArea.map(value => clean(value / norm)), area: 4 * norm, projectedArea: 4, normalDensity: clean(orientation * c / norm), flux: clean(orientation * 4 * c) };
  }
  function stokesState(input) {
    parameters(input);
    const height = bounded(input.height, -1.5, 1.5), alpha = bounded(input.alpha, -1, 1), orientation = direction(input.orientation), n = subdivisions(input.n, 8, 8);
    const circulationExact = clean(orientation * Math.PI * (1 + alpha));
    // The angular integral 2*pi is analytic; only the radial integral is
    // approximated. Cartesian graph coordinates remain regular at the center.
    let radialSum = 0;
    for (let k = 0; k < n; k++) {
      const r = (k + .5) / n;
      radialSum += r + 2 * alpha * r * r * r;
    }
    const surfaceNumeric = clean(orientation * 2 * Math.PI * radialSum / n);
    return { height, alpha, orientation, n, domainState: 'defined', circulationExact, surfaceExact: circulationExact, surfaceNumeric, error: Math.abs(surfaceNumeric - circulationExact), boundaryRadius: 1, boundaryHeight: 0, regularGraph: true, centerNormalArea: [0, 0, orientation] };
  }
  return Object.freeze({ workState, fluxState, stokesState });
}));
