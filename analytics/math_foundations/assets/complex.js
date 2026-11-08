(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathComplex = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected complex experiment parameters');
    return input;
  }
  function bounded(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max) throw new RangeError('Outside the supported range');
    return value === 0 ? 0 : value;
  }
  const complex = (re, im) => ({ re: re === 0 ? 0 : re, im: im === 0 ? 0 : im });
  function unit(theta) {
    // Use the exact quadrantal value before evaluating trigonometry. In
    // particular sin(±π)'s floating-point residue must not choose a Log branch.
    if (theta % 90 === 0) {
      const quadrant = ((theta / 90) % 4 + 4) % 4;
      return [complex(1, 0), complex(0, 1), complex(-1, 0), complex(0, -1)][quadrant];
    }
    const radians = theta * Math.PI / 180;
    return complex(Math.cos(radians), Math.sin(radians));
  }
  function divide(a, b) {
    const denominator = b.re * b.re + b.im * b.im;
    return complex((a.re * b.re + a.im * b.im) / denominator, (a.im * b.re - a.re * b.im) / denominator);
  }
  function evaluate(name, z) {
    if (name === 'square') return complex(z.re * z.re - z.im * z.im, 2 * z.re * z.im);
    if (name === 'conjugate') return complex(z.re, -z.im);
    return complex(z.re * z.re + z.im * z.im, 0);
  }
  function differenceState(input) {
    parameters(input);
    const name = input.function;
    if (typeof name !== 'string') throw new TypeError('Expected a function name');
    if (!['square', 'conjugate', 'absSquare'].includes(name)) throw new RangeError('Unsupported function');
    const x = bounded(input.x, -1.5, 1.5), y = bounded(input.y, -1.5, 1.5);
    const h = bounded(input.h, .05, 1), theta = bounded(input.theta, 0, 360);
    const point = complex(x, y), value = evaluate(name, point);
    function quotient(angle) {
      const direction = unit(angle), delta = complex(h * direction.re, h * direction.im);
      const nextPoint = complex(x + delta.re, y + delta.im), nextValue = evaluate(name, nextPoint);
      return { delta, nextPoint, nextValue, quotient: divide(complex(nextValue.re - value.re, nextValue.im - value.im), delta) };
    }
    const selected = quotient(theta);
    const differentiable = name === 'square' || (name === 'absSquare' && x === 0 && y === 0);
    const derivative = !differentiable ? null : name === 'square' ? complex(2 * x, 2 * y) : complex(0, 0);
    return {
      function: name, x, y, h, theta, point, value, delta: selected.delta, nextPoint: selected.nextPoint, nextValue: selected.nextValue,
      selected: selected.quotient, orthogonal0: quotient(0).quotient, orthogonal90: quotient(90).quotient,
      differentiable, holomorphicNeighborhood: name === 'square', derivative,
      derivativeRotation: derivative === null || (derivative.re === 0 && derivative.im === 0) ? null : Math.atan2(derivative.im, derivative.re),
      error: derivative === null ? null : Math.hypot(selected.quotient.re - derivative.re, selected.quotient.im - derivative.im)
    };
  }
  function logarithmState(input) {
    parameters(input);
    const radius = bounded(input.radius, .5, 2), theta = bounded(input.theta, -360, 360);
    const direction = unit(theta), point = complex(radius * direction.re, radius * direction.im);
    const onCut = Math.abs(theta) === 180;
    const principalAngle = onCut ? null : Math.atan2(point.im, point.re);
    const real = Math.log(radius);
    return { radius, theta, point, onCut, tracked: complex(real, theta * Math.PI / 180), principalAngle,
      principal: onCut ? null : complex(real, principalAngle) };
  }
  function residueState(input) {
    parameters(input);
    const a = bounded(input.a, -2, 2), orientation = bounded(input.orientation, -1, 1), n = bounded(input.n, 16, 256);
    if (orientation !== -1 && orientation !== 1) throw new RangeError('Expected orientation -1 or 1');
    if (!Number.isInteger(n) || n % 16 !== 0) throw new RangeError('Expected a multiple of 16');
    // A finite midpoint sum at a=±1 is not the contour integral. Check the
    // mathematical domain before sampling; valid neighboring poles stay valid.
    const region = Math.abs(a) === 1 ? 'boundary' : Math.abs(a) < 1 ? 'inside' : 'outside';
    if (region === 'boundary') return { a, orientation, n, region, exact: null, numeric: null, error: null };
    const step = orientation * 2 * Math.PI / n;
    let real = 0, imaginary = 0;
    for (let k = 0; k < n; k++) {
      const angle = step * (k + .5), re = Math.cos(angle), im = Math.sin(angle);
      // f(γ(t))γ′(t) dt with γ=e^it and γ′=i e^it.
      const term = divide(complex(-im, re), complex(re - a, im));
      real += term.re * step; imaginary += term.im * step;
    }
    const numeric = complex(real, imaginary), exact = complex(0, region === 'inside' ? orientation * 2 * Math.PI : 0);
    return { a, orientation, n, region, exact, numeric, error: Math.hypot(numeric.re - exact.re, numeric.im - exact.im) };
  }
  return Object.freeze({ differenceState, logarithmState, residueState });
}));
