(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathOptimization = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected optimization experiment parameters');
  }
  function bounded(value, min, max, integer = false) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max || (integer && !Number.isInteger(value))) throw new RangeError('Outside the supported range');
    return value === 0 ? 0 : value;
  }
  const zero = value => value === 0 ? 0 : value;
  function gradientState(input) {
    parameters(input);
    const kappa = bounded(input.kappa, 1, 16, true), alpha = bounded(input.alpha, 0, .5);
    const n = bounded(input.n, 0, 40, true), x0 = bounded(input.x0, -2, 2), y0 = bounded(input.y0, -2, 2);
    const factors = [1 - alpha, 1 - alpha * kappa], rho = Math.max(...factors.map(Math.abs));
    const contractsAll = alpha > 0 && alpha < 2 / kappa;
    const allInitialState = contractsAll ? 'contracting' : rho === 1 ? 'boundary' : 'unstable';
    const activeRho = Math.max(x0 === 0 ? 0 : Math.abs(factors[0]), y0 === 0 ? 0 : Math.abs(factors[1]));
    const trajectoryState = x0 === 0 && y0 === 0 ? 'fixed-origin' : activeRho < 1 ? 'contracting' : activeRho === 1 ? 'boundary' : 'unstable';
    const points = [];
    let x = x0, y = y0;
    for (let iteration = 0; iteration <= n; iteration++) {
      const objective = (x * x + kappa * y * y) / 2, gradient = [x, zero(kappa * y)];
      points.push({ iteration, x, y, objective, logObjective: objective === 0 ? null : Math.log10(objective), gradient, gradientNorm: Math.hypot(...gradient) });
      // Calculate the requested finite orbit by successive gradient updates;
      // tests compare this with the independent diagonal-power expression.
      if (iteration < n) { x = zero(x - alpha * gradient[0]); y = zero(y - alpha * gradient[1]); }
    }
    const initialObjective = points[0].objective, objective = points[n].objective;
    return { kappa, alpha, n, x0, y0, factors, rho, criticalAlpha: 2 / kappa, contractsAll, allInitialState,
      trajectoryConverges: activeRho < 1, trajectoryState, points, final: [x, y], objective, initialObjective,
      objectiveRatio: initialObjective === 0 ? null : objective / initialObjective };
  }
  function projectionState(input) {
    parameters(input);
    if (typeof input.kind !== 'string') throw new TypeError('Expected a projection set name');
    if (!['disk', 'box'].includes(input.kind)) throw new RangeError('Unsupported projection set');
    const kind = input.kind, x = bounded(input.x, -2, 2), y = bounded(input.y, -2, 2), radius = bounded(input.radius, .5, 1.5);
    const size = kind === 'disk' ? Math.hypot(x, y) : Math.max(Math.abs(x), Math.abs(y));
    let projected;
    if (size <= radius) projected = [x, y];
    else if (kind === 'disk') projected = [radius * x / size, radius * y / size];
    else projected = [Math.max(-radius, Math.min(radius, x)), Math.max(-radius, Math.min(radius, y))];
    projected = projected.map(zero);
    const residual = [zero(x - projected[0]), zero(y - projected[1])], distance = Math.hypot(...residual);
    return { kind, x, y, radius, projected, residual, distance, objective: distance * distance / 2,
      residualUnit: distance === 0 ? null : residual.map(value => zero(value / distance)),
      inputLocation: size < radius ? 'inside' : size === radius ? 'boundary' : 'outside' };
  }
  function kktState(input) {
    parameters(input);
    const a = bounded(input.a, -2, 2), b = bounded(input.b, -1.5, 1.5), lambda = bounded(input.lambda, 0, 4);
    const delta = b - a, xStar = Math.max(a, b), lambdaStar = Math.max(delta, 0), primalOptimal = lambdaStar * lambdaStar / 2;
    const dualValue = zero(lambda * delta - lambda * lambda / 2);
    // This algebraically equal gap avoids cancellation in p* - d(lambda),
    // particularly for a multiplier very close to lambdaStar.
    const dualGap = delta >= 0 ? (lambda - delta) ** 2 / 2 : lambda * lambda / 2 - delta * lambda;
    const stationarity = zero(xStar - a - lambda), gValue = zero(b - xStar), slack = zero(xStar - b);
    const complementarity = zero(lambda * gValue);
    return { a, b, lambda, xStar, lambdaStar, primalOptimal, dualValue, dualGap, stationarity, gValue, slack, complementarity,
      dualFeasible: true, active: xStar === b, kktSatisfied: stationarity === 0 && complementarity === 0 };
  }
  return Object.freeze({ gradientState, projectionState, kktState });
}));
