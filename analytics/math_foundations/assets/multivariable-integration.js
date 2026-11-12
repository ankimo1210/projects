(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathMultivariableIntegration = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function finite(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    return value === 0 ? 0 : value;
  }
  function bounded(value, min, max) {
    value = finite(value);
    if (value < min || value > max) throw new RangeError('Outside the supported range');
    return value;
  }
  function rectangleSumState(n, rule) {
    n = bounded(n, 1, 32);
    if (!Number.isInteger(n)) throw new RangeError('Expected an integer subdivision count');
    if (typeof rule !== 'string') throw new TypeError('Expected a rule name');
    if (!['lower', 'upper', 'midpoint'].includes(rule)) throw new RangeError('Unknown rectangle rule');
    const offset = { lower: 0, upper: 1, midpoint: .5 }[rule];
    const cellArea = 1 / (n * n);
    const cells = [];
    let sum = 0;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const x = (i + offset) / n, y = (j + offset) / n;
      const density = x * x + y * y;
      const weightedValue = density * cellArea;
      cells.push({ i, j, x, y, density, weightedValue });
      sum += weightedValue;
    }
    // The closed forms are independent of the selected representative-point sum.
    const lower = (n - 1) * (2 * n - 1) / (3 * n * n);
    const upper = (n + 1) * (2 * n + 1) / (3 * n * n);
    const integral = 2 / 3;
    const midpoint = integral - 1 / (6 * n * n);
    return { n, rule, cellArea, sum, lower, upper, midpoint, integral, gap: 2 / n, cells };
  }
  function polarCellState(input) {
    if (!input || typeof input !== 'object') throw new TypeError('Expected polar cell parameters');
    const innerRadius = bounded(input.innerRadius, 0, 1.5);
    const radialWidth = bounded(input.radialWidth, .1, .5);
    const angleRad = bounded(input.angleRad, -Math.PI, Math.PI);
    const angularWidth = bounded(input.angularWidth, Math.PI / 36, Math.PI / 2);
    const outerRadius = innerRadius + radialWidth;
    const endAngle = angleRad + angularWidth;
    const midpointRadius = innerRadius + radialWidth / 2;
    const exactArea = (outerRadius * outerRadius - innerRadius * innerRadius) * angularWidth / 2;
    const coordinateProduct = radialWidth * angularWidth;
    const corners = [[innerRadius, angleRad], [outerRadius, angleRad], [outerRadius, endAngle], [innerRadius, endAngle]].map(([radius, angle]) => {
      const x = radius * Math.cos(angle), y = radius * Math.sin(angle);
      return { x: x === 0 ? 0 : x, y: y === 0 ? 0 : y };
    });
    return { innerRadius, radialWidth, angleRad, angularWidth, outerRadius, endAngle,
      midpointRadius, jacobianAtMidpoint: midpointRadius, exactArea, coordinateProduct,
      areaRatio: midpointRadius, corners };
  }
  return Object.freeze({ rectangleSumState, polarCellState });
}));
