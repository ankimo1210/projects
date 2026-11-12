(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathFoundations = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  function finiteNumber(value, name) {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      throw new TypeError(name + ' must be a finite number');
    }
    return value;
  }

  function pair(value, first, second) {
    if (!value || typeof value !== 'object') throw new TypeError('A coordinate pair is required');
    finiteNumber(value[first], first);
    finiteNumber(value[second], second);
  }

  function complexMultiply(a, b) {
    pair(a, 're', 'im');
    pair(b, 're', 'im');
    const re = a.re * b.re - a.im * b.im;
    const im = a.re * b.im + a.im * b.re;
    if (!Number.isFinite(re) || !Number.isFinite(im)) throw new RangeError('Product exceeds numeric range');
    return { re: re === 0 ? 0 : re, im: im === 0 ? 0 : im };
  }

  function quarterTurn(power) {
    if (!Number.isSafeInteger(power)) throw new RangeError('Power must be a safe integer');
    const turns = [{ re: 1, im: 0 }, { re: 0, im: 1 }, { re: -1, im: 0 }, { re: 0, im: -1 }];
    return turns[((power % 4) + 4) % 4];
  }

  function rotationMatrix(degrees) {
    finiteNumber(degrees, 'Angle');
    const radians = (degrees % 360) * Math.PI / 180;
    const cosine = Math.cos(radians);
    const sine = Math.sin(radians);
    return [[cosine, -sine], [sine, cosine]];
  }

  function rotateVector(vector, degrees) {
    pair(vector, 'x', 'y');
    const matrix = rotationMatrix(degrees);
    return {
      x: matrix[0][0] * vector.x + matrix[0][1] * vector.y,
      y: matrix[1][0] * vector.x + matrix[1][1] * vector.y,
    };
  }

  function exampleKind(kind) {
    if (!['sqrt', 'step', 'pole'].includes(kind)) throw new RangeError('Unknown example');
    return kind;
  }

  function evaluateExample(kind, x) {
    exampleKind(kind);
    finiteNumber(x, 'x');
    if (kind === 'sqrt') return x * x - 2;
    if (kind === 'step') return x < 1.3 ? -1 : 1;
    return x === 1.3 ? null : 1 / (x - 1.3);
  }

  function bisectionState(kind, iterations) {
    exampleKind(kind);
    if (!Number.isInteger(iterations) || iterations < 0 || iterations > 30) {
      throw new RangeError('Iterations must be an integer from 0 to 30');
    }
    let a = 0;
    let b = 2;
    let fa = evaluateExample(kind, a);
    let fb = evaluateExample(kind, b);
    for (let i = 0; i < iterations; i += 1) {
      const midpoint = (a + b) / 2;
      const value = evaluateExample(kind, midpoint);
      if (value === null) break;
      if (value === 0) {
        a = midpoint;
        b = midpoint;
        fa = 0;
        fb = 0;
        break;
      }
      if ((fa < 0 && value < 0) || (fa > 0 && value > 0)) {
        a = midpoint;
        fa = value;
      } else {
        b = midpoint;
        fb = value;
      }
    }
    const midpoint = (a + b) / 2;
    const continuous = kind === 'sqrt';
    return {
      kind, iterations, a, b, fa, fb, midpoint,
      value: evaluateExample(kind, midpoint),
      width: b - a,
      continuous,
      rootGuaranteed: continuous,
      hasRoot: continuous,
      errorBound: continuous ? (b - a) / 2 : null,
    };
  }

  return Object.freeze({ complexMultiply, quarterTurn, rotationMatrix, rotateVector, evaluateExample, bisectionState });
}));
