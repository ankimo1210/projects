(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathMultivariableMiddle = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function clean(value) { return value === 0 ? 0 : value; }

  function bounded(value, lower, upper) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < lower || value > upper) throw new RangeError('Value outside the supported range');
    return clean(value);
  }

  function vector(x, y) { return { x: clean(x), y: clean(y) }; }

  function direction(angleRad) { return vector(Math.cos(angleRad), Math.sin(angleRad)); }

  function gradientCompassState(base, angleRad) {
    if (!base || typeof base !== 'object') throw new TypeError('Expected coordinates');
    base = vector(bounded(base.x, -1, 1), bounded(base.y, -1, 1));
    angleRad = bounded(angleRad, -Math.PI, Math.PI);
    const u = direction(angleRad);
    const gradient = vector(2 * base.x + base.y, base.x + 2 * base.y);
    const maxSlope = Math.hypot(gradient.x, gradient.y);
    const zeroGradient = gradient.x === 0 && gradient.y === 0;
    return {
      base, angleRad, direction: u, gradient,
      slope: zeroGradient ? 0 : clean(gradient.x * u.x + gradient.y * u.y),
      maxSlope, minSlope: clean(-maxSlope),
      steepest: zeroGradient ? null : vector(gradient.x / maxSlope, gradient.y / maxSlope)
    };
  }

  function curvatureState(example, angleRad, t) {
    if (typeof example !== 'string') throw new TypeError('Expected an example name');
    if (!['bowl', 'saddle', 'flat-min', 'flat-saddle'].includes(example)) throw new RangeError('Unknown example');
    angleRad = bounded(angleRad, -Math.PI, Math.PI);
    t = bounded(t, -1, 1);
    const u = direction(angleRad);
    const point = vector(t * u.x, t * u.y);
    const hessian = example === 'bowl' ? { xx: 2, xy: 1, yy: 2 }
      : example === 'saddle' ? { xx: 2, xy: 0, yy: -2 } : { xx: 0, xy: 0, yy: 0 };
    const directionalSecond = clean(hessian.xx * u.x * u.x + 2 * hessian.xy * u.x * u.y + hessian.yy * u.y * u.y);
    const quadraticValue = clean(0.5 * t * t * directionalSecond);
    const x2 = point.x * point.x, y2 = point.y * point.y;
    const value = clean(example === 'bowl' ? x2 + point.x * point.y + y2
      : example === 'saddle' ? x2 - y2
        : example === 'flat-min' ? x2 * x2 + y2 * y2 : x2 * x2 - y2 * y2);
    const quadratic = example === 'bowl' || example === 'saddle';
    return {
      example, angleRad, t, direction: u, point, value, quadraticValue,
      remainder: quadratic ? 0 : value, directionalSecond, hessian,
      hessianVerdict: example === 'bowl' ? 'strict-min' : example === 'saddle' ? 'saddle' : 'inconclusive'
    };
  }

  function circleConstraintState(angleRad) {
    angleRad = bounded(angleRad, -Math.PI, Math.PI);
    const point = direction(angleRad);
    const tangent = vector(-point.y, point.x);
    const objectiveGradient = vector(1, 2);
    const constraintGradient = vector(2 * point.x, 2 * point.y);
    // This coefficient is a normal projection at every point, not a solved multiplier.
    const lambdaProjection = clean((constraintGradient.x + 2 * constraintGradient.y)
      / (constraintGradient.x * constraintGradient.x + constraintGradient.y * constraintGradient.y));
    return {
      angleRad, point, tangent,
      value: clean(point.x + 2 * point.y), tangentRate: clean(-point.y + 2 * point.x),
      objectiveGradient, constraintGradient, lambdaProjection,
      normalResidual: vector(1 - lambdaProjection * constraintGradient.x, 2 - lambdaProjection * constraintGradient.y)
    };
  }

  return Object.freeze({ gradientCompassState, curvatureState, circleConstraintState });
}));
