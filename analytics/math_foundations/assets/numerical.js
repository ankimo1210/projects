(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathNumerical = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected numerical experiment parameters');
  }
  function bounded(value, min, max, integer = false) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max || (integer && !Number.isInteger(value))) throw new RangeError('Outside the supported range');
    return value === 0 ? 0 : value;
  }
  function named(value, choices) {
    if (typeof value !== 'string') throw new TypeError('Expected a name');
    if (!choices.includes(value)) throw new RangeError('Unsupported name');
    return value;
  }
  function rootState(input) {
    parameters(input);
    const name = named(input.function, ['square', 'cycle']), method = named(input.method, ['bisection', 'newton']);
    const x0 = bounded(input.x0, -2, 2), steps = bounded(input.steps, 0, 12, true);
    const f = x => name === 'square' ? x * x - 2 : x * x * x - 2 * x + 2;
    const df = x => name === 'square' ? 2 * x : 3 * x * x - 2;
    const history = [];
    let x, bracket = null, bound = null, status = method === 'bisection' ? 'bracket' : 'steps', iterations = 0;
    if (method === 'bisection') {
      let a = name === 'square' ? 0 : -2, b = name === 'square' ? 2 : 0;
      x = (a + b) / 2;
      history.push({ iteration: 0, x, residual: f(x) });
      for (let k = 1; k <= steps; k++) {
        const fm = f(x);
        if (fm === 0) { a = x; b = x; }
        else if (Math.sign(f(a)) === Math.sign(fm)) a = x;
        else b = x;
        x = (a + b) / 2;
        history.push({ iteration: k, x, residual: f(x) }); iterations = k;
      }
      bracket = [a, b]; bound = (b - a) / 2;
    } else {
      x = x0; history.push({ iteration: 0, x, residual: f(x) });
      for (let k = 1; k <= steps; k++) {
        const fx = f(x), derivative = df(x);
        if (fx === 0) { status = 'computed-zero'; break; }
        if (derivative === 0) { status = 'derivative-zero'; break; }
        const next = x - fx / derivative;
        // Keep the demonstration finite. This is a display guard, not a
        // mathematical divergence criterion or a universal Newton solver.
        if (!Number.isFinite(next) || Math.abs(next) > 1e6) { status = 'display-limit'; break; }
        x = next === 0 ? 0 : next; iterations = k;
        history.push({ iteration: k, x, residual: f(x) });
      }
      if (f(x) === 0) status = 'computed-zero';
    }
    return { function: name, method, x0, steps, estimate: x, residual: f(x), derivative: df(x), history, iterations, bracket, bound,
      status, intervalGuaranteed: method === 'bisection', error: name === 'square' ? Math.abs(Math.abs(x) - Math.SQRT2) : null };
  }
  function differenceState(input) {
    parameters(input);
    const x = bounded(input.x, -2, 2), exponent = bounded(input.exponent, 0, 16, true), h = 10 ** -exponent;
    const exact = Math.exp(x), plus = Math.exp(x + h), minus = Math.exp(x - h);
    const forward = (plus - exact) / h, central = (plus - minus) / (2 * h), maximum = Math.exp(x + h);
    return { x, exponent, h, exact, forward, central, forwardError: Math.abs(forward - exact), centralError: Math.abs(central - exact),
      forwardTruncationBound: maximum * h / 2, centralTruncationBound: maximum * h * h / 6,
      // Illustrative unit-roundoff scales, not certified bounds for Math.exp
      // or for the rounded arguments x±h. UI and text label them accordingly.
      forwardRoundingScale: Number.EPSILON * (Math.abs(plus) + Math.abs(exact)) / h,
      centralRoundingScale: Number.EPSILON * (Math.abs(plus) + Math.abs(minus)) / (2 * h),
      actualForwardStep: (x + h) - x, actualBackwardStep: x - (x - h),
      inputResolved: x + h !== x && x - h !== x };
  }
  function odeState(input) {
    parameters(input);
    const lambda = bounded(input.lambda, -4, 2), y0 = bounded(input.y0, -2, 2), n = bounded(input.n, 1, 64, true), h = 2 / n;
    const factor = 1 + h * lambda, points = [];
    let value = y0;
    for (let k = 0; k <= n; k++) {
      const t = k * h, exact = y0 * Math.exp(lambda * t);
      points.push({ t, euler: value === 0 ? 0 : value, exact: exact === 0 ? 0 : exact, error: Math.abs(value - exact) });
      value += h * lambda * value;
    }
    return { lambda, y0, n, h, factor, stability: Math.abs(factor) < 1 ? 'decay' : Math.abs(factor) === 1 ? 'boundary' : 'growth', points,
      final: points[n].euler, exact: points[n].exact, error: points[n].error };
  }
  return Object.freeze({ rootState, differenceState, odeState });
}));
