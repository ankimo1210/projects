(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathCalculus = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function finite(value) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
  }
  function count(value, maximum) {
    if (!Number.isInteger(value) || value < 1 || value > maximum) throw new RangeError('Count out of range');
  }
  function secantSquare(a, h) {
    finite(a); finite(h);
    const x = a + h;
    const y = x * x;
    const derivative = 2 * a;
    const tangentY = a * a + derivative * h;
    const error = h * h;
    if (![x, y, derivative, tangentY, error].every(Number.isFinite)) throw new RangeError('Numeric overflow');
    return { a, h, x, y, derivative, tangentY, error, quotient: h === 0 ? null : 2 * a + h };
  }
  function squareRiemann(n) {
    count(n, 4096);
    return { n, left: (n - 1) * (2 * n - 1) / (6 * n * n),
      right: (n + 1) * (2 * n + 1) / (6 * n * n), integral: 1 / 3 };
  }
  function geometricPartial(ratio, n) {
    finite(ratio); count(n, 200);
    const partials = [];
    let term = 1, sum = 0;
    for (let k = 0; k < n; k += 1) {
      sum += term;
      if (!Number.isFinite(sum)) throw new RangeError('Numeric overflow');
      partials.push(sum);
      if (k + 1 < n) term *= ratio;
    }
    const converges = Math.abs(ratio) < 1;
    return { ratio, n, sum, partials, converges,
      limit: converges ? 1 / (1 - ratio) : null,
      errorBound: converges ? Math.abs(ratio ** n / (1 - ratio)) : null };
  }
  return Object.freeze({ secantSquare, squareRiemann, geometricPartial });
}));
