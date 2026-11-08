(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathLinearCore = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const zero = value => value === 0 ? 0 : value;
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected linear algebra experiment parameters');
  }
  function grid(value, min, max, step = .25) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max || !Number.isInteger(value / step)) throw new RangeError('Outside the supported grid');
    return zero(value);
  }
  const squared = values => values.reduce((sum, value) => sum + value * value, 0);
  function mapState(input) {
    parameters(input);
    const s = grid(input.s, -2, 2), t = grid(input.t, -2, 2), x = grid(input.x, -2, 2), y = grid(input.y, -2, 2);
    const b1 = grid(input.b1, -2, 2), b2 = grid(input.b2, -2, 2);
    const determinant = zero(1 - s * t), rank = determinant === 0 ? 1 : 2;
    const solutionKind = determinant !== 0 ? 'unique' : b2 === s * b1 ? 'infinite' : 'none';
    let representativeSolution = null;
    if (solutionKind === 'unique') representativeSolution = [(b1 - t * b2) / determinant, (b2 - s * b1) / determinant].map(zero);
    else if (solutionKind === 'infinite') representativeSolution = [b1, 0];
    return { s, t, x, y, b1, b2, matrix: [[1, t], [s, 1]], columns: [[1, s], [t, 1]],
      transformed: [zero(x + t * y), zero(s * x + y)], determinant, rank, solutionKind, representativeSolution,
      kernelDirection: rank === 1 ? [zero(-t), 1] : null };
  }
  function leastSquaresState(input) {
    parameters(input);
    const y0 = grid(input.y0, -2, 2), y1 = grid(input.y1, -2, 2), y2 = grid(input.y2, -2, 2);
    const deltaA = grid(input.deltaA, -1, 1), deltaB = grid(input.deltaB, -1, 1);
    const observed = [y0, y1, y2], a = zero((y0 + y1 + y2) / 3), b = zero((y2 - y0) / 2);
    const fitted = [a - b, a, a + b].map(zero), residual = observed.map((value, i) => zero(value - fitted[i]));
    const normalResiduals = [zero(residual.reduce((sum, value) => sum + value, 0)), zero(-residual[0] + residual[2])];
    const sse = squared(residual), observedNormSquared = squared(observed), fitNormSquared = squared(fitted);
    const candidateA = zero(a + deltaA), candidateB = zero(b + deltaB);
    const candidateFitted = [candidateA - candidateB, candidateA, candidateA + candidateB].map(zero);
    const candidateResidual = observed.map((value, i) => value - candidateFitted[i]);
    // A stable algebraic gap for this fixed design matrix; candidateSSE
    // remains an independently evaluated floating-point sum of squares.
    const excess = 3 * deltaA * deltaA + 2 * deltaB * deltaB;
    return { y0, y1, y2, deltaA, deltaB, observed, a, b, fitted, residual, normalResiduals, sse,
      observedNormSquared, fitNormSquared, pythagoreanResidual: zero(observedNormSquared - fitNormSquared - sse),
      candidateA, candidateB, candidateFitted, candidateSSE: squared(candidateResidual), excess };
  }
  function sincos(degrees) {
    const angle = ((degrees % 360) + 360) % 360;
    if (angle === 0) return [0, 1];
    if (angle === 90) return [1, 0];
    if (angle === 180) return [0, -1];
    if (angle === 270) return [-1, 0];
    return [Math.sin(angle * Math.PI / 180), Math.cos(angle * Math.PI / 180)];
  }
  function spectralState(input) {
    parameters(input);
    const lambda1 = grid(input.lambda1, -2, 3), lambda2 = grid(input.lambda2, -2, 3);
    const theta = grid(input.theta, 0, 180, 15), x = grid(input.x, -2, 2), y = grid(input.y, -2, 2);
    const [sin, cos] = sincos(theta), [sin2, cos2] = sincos(2 * theta);
    const mid = (lambda1 + lambda2) / 2, half = (lambda1 - lambda2) / 2;
    const a = zero(mid + half * cos2), d = zero(mid - half * cos2), off = zero(half * sin2);
    const matrix = [[a, off], [off, d]], directions = [[cos, sin], [zero(-sin), cos]];
    const transformed = [zero(a * x + off * y), zero(off * x + d * y)];
    const low = Math.min(lambda1, lambda2), high = Math.max(lambda1, lambda2);
    const formKind = low === 0 && high === 0 ? 'zero' : low > 0 ? 'positive-definite' : high < 0 ? 'negative-definite'
      : low < 0 && high > 0 ? 'indefinite' : low === 0 ? 'positive-semidefinite' : 'negative-semidefinite';
    // Rank and sign describe the exact quarter-grid eigenvalue model,
    // not a threshold applied to a floating-point matrix determinant.
    return { lambda1, lambda2, theta, x, y, matrix, eigenvalues: [lambda1, lambda2], directions, transformed,
      quadraticForm: zero(x * transformed[0] + y * transformed[1]), trace: zero(lambda1 + lambda2),
      determinant: zero(lambda1 * lambda2), rank: Number(lambda1 !== 0) + Number(lambda2 !== 0), formKind,
      repeatedEigenvalue: lambda1 === lambda2, eigenDirectionsUnique: lambda1 !== lambda2,
      singularValues: [Math.abs(lambda1), Math.abs(lambda2)].sort((u, v) => v - u),
      singularDirectionsUnique: Math.abs(lambda1) !== Math.abs(lambda2) };
  }
  return Object.freeze({ mapState, leastSquaresState, spectralState });
}));
