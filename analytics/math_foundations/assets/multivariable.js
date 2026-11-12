(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathMultivariable = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function finite(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    return value === 0 ? 0 : value;
  }

  function coordinates(point) {
    if (!point || typeof point !== 'object') throw new TypeError('Expected coordinates');
    return { x: finite(point.x), y: finite(point.y) };
  }

  function result(value) {
    if (!Number.isFinite(value)) throw new RangeError('Numeric overflow');
    return value === 0 ? 0 : value;
  }

  function product(a, b) {
    const value = result(a * b);
    if (a !== 0 && b !== 0 && value === 0) throw new RangeError('Numeric underflow');
    return value;
  }

  function choice(value, options) {
    if (typeof value !== 'string') throw new TypeError('Expected a choice name');
    if (!options.includes(value)) throw new RangeError('Unknown choice');
  }

  function norm2(point) {
    const p = coordinates(point);
    return result(Math.hypot(p.x, p.y));
  }

  // Scaling keeps the denominator away from both zero and overflow.
  function ratio(x, y) {
    const scale = Math.max(Math.abs(x), Math.abs(y));
    if (scale === 0) return 0;
    const u = x / scale, v = y / scale;
    const value = result(u * v / (u * u + v * v));
    if (x !== 0 && y !== 0 && value === 0) throw new RangeError('Numeric underflow');
    return value;
  }

  function pathState(example, path, t, coefficient = 1) {
    choice(example, ['axis-trap', 'curved-trap']);
    choice(path, ['x-axis', 'y-axis', 'line', 'parabola']);
    t = finite(t);
    coefficient = finite(coefficient);
    let point;
    if (path === 'x-axis') point = { x: t, y: 0 };
    else if (path === 'y-axis') point = { x: 0, y: t };
    else point = { x: t, y: product(coefficient, path === 'line' ? t : product(t, t)) };
    const distance = norm2(point);
    const atOrigin = point.x === 0 && point.y === 0;
    const value = atOrigin ? 0 : ratio(example === 'axis-trap' ? point.x : product(point.x, point.x), point.y);
    return { example, path, t, coefficient, point, distance, value, atOrigin };
  }

  function quadraticResult(value) {
    value = result(value);
    // P requires normal nonzero squares/quadratic quantities (>= 2^-1022) to avoid
    // severe relative precision loss. Returned values are floating-point approximations;
    // rounding can still reverse the theoretical remainder <= bound by a few ulps.
    // This restriction is local to P; scaled F/H ratios and norm2 keep their own ranges.
    if (value !== 0 && Math.abs(value) < 2 ** -1022) throw new RangeError('Subnormal quadratic quantity');
    return value;
  }

  function quadratic(point) {
    const xx = quadraticResult(product(point.x, point.x)), yy = quadraticResult(product(point.y, point.y));
    return quadraticResult(xx + point.x * point.y + yy);
  }

  function quadraticLinearState(base, delta) {
    base = coordinates(base);
    delta = coordinates(delta);
    const point = { x: result(base.x + delta.x), y: result(base.y + delta.y) };
    const baseValue = quadratic(base);
    const coefficients = { x: result(2 * base.x + base.y), y: result(base.x + 2 * base.y) };
    const linearValue = result(baseValue + coefficients.x * delta.x + coefficients.y * delta.y);
    const value = quadratic(point);
    // Compute the remainder directly: subtracting value - linearValue loses small errors.
    const remainder = quadratic(delta);
    const distance = norm2(delta);
    const normalizedError = distance === 0 ? null : result(Math.abs(remainder) / distance);
    const errorBound = quadraticResult(1.5 * quadraticResult(distance * distance));
    return { base, delta, point, baseValue, coefficients, linearValue, value,
      remainder, distance, normalizedError, errorBound };
  }

  return Object.freeze({ norm2, pathState, quadraticLinearState });
}));
