(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.MathProbability = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  function parameters(input) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('Expected probability parameters');
    return input;
  }
  function bounded(value, min, max) {
    if (typeof value !== 'number' || !Number.isFinite(value)) throw new TypeError('Expected a finite number');
    if (value < min || value > max) throw new RangeError('Outside the supported range');
    return value === 0 ? 0 : value;
  }
  function integer(value, min, max) {
    value = bounded(value, min, max);
    if (!Number.isInteger(value)) throw new RangeError('Expected an integer');
    return value;
  }
  function bayesState(input) {
    parameters(input);
    const prior = bounded(input.prior, 0, 1), sensitivity = bounded(input.sensitivity, 0, 1), falsePositive = bounded(input.falsePositive, 0, 1);
    const truePositive = prior * sensitivity;
    const falsePositiveMass = (1 - prior) * falsePositive;
    const positive = truePositive + falsePositiveMass;
    const cells = [truePositive, prior * (1 - sensitivity), falsePositiveMass, (1 - prior) * (1 - falsePositive)];
    return { prior, sensitivity, falsePositive, truePositive, falsePositiveMass, positive, posterior: positive === 0 ? null : truePositive / positive, cells };
  }
  function independenceState(input) {
    parameters(input);
    const a = bounded(input.a, 0, 1), b = bounded(input.b, 0, 1);
    const maximum = Math.min(a, b);
    const minimum = Math.max(0, Math.min(maximum, a + b - 1));
    const joint = bounded(input.joint, 0, maximum);
    // Only the computed lower bound suffers cancellation. Allow a few arithmetic ulps
    // there, e.g. .8 + .8 - 1 rounds above the decimal endpoint .6. The exact upper
    // bound min(a,b), zero, and one remain strict; meaningful outside values still fail.
    const lowerRoundoff = 4 * Number.EPSILON * Math.max(a, b);
    if (joint < minimum && minimum - joint > lowerRoundoff) throw new RangeError('Outside the feasible joint range');
    // At a feasible endpoint the last subtraction can produce a tiny negative roundoff.
    const cells = [joint, a - joint, b - joint, Math.max(0, 1 - a - b + joint)];
    const product = a * b;
    return { a, b, joint, minimum, maximum, cells, product, difference: joint - product, conditional: b === 0 ? null : joint / b };
  }
  function binomialState(input) {
    parameters(input);
    const n = integer(input.n, 1, 200), p = bounded(input.p, 0, 1);
    const pmf = Array(n + 1).fill(0);
    if (p === 0 || p === 1) pmf[p === 0 ? 0 : n] = 1;
    else {
      // Relative weights from a mode avoid underflow from starting at p^n or (1-p)^n.
      const mode = Math.min(n, Math.floor((n + 1) * p));
      pmf[mode] = 1;
      for (let k = mode; k > 0; k--) pmf[k - 1] = pmf[k] * k / (n - k + 1) * ((1 - p) / p);
      for (let k = mode; k < n; k++) pmf[k + 1] = pmf[k] * (n - k) / (k + 1) * (p / (1 - p));
      const total = pmf.reduce((sum, mass) => sum + mass, 0);
      for (let k = 0; k <= n; k++) pmf[k] /= total;
    }
    let accumulated = 0;
    const cdf = pmf.map(mass => Math.min(1, accumulated += mass));
    cdf[n] = 1;
    return { n, p, pmf, cdf, mean: n * p, variance: n * p * (1 - p) };
  }
  function densityState(b) {
    b = bounded(b, 0, 1);
    return { b, density: 2 * b, probability: b * b };
  }
  function decimalRatio(value) {
    // Interpret the shortest decimal input representation exactly for threshold membership.
    // In particular |2/10 - .3| >= .1 includes the equality, without a blanket tolerance.
    const [coefficient, exponent = '0'] = value.toString().split('e');
    const pieces = coefficient.split('.');
    const numerator = BigInt(pieces.join(''));
    const places = (pieces[1] || '').length - Number(exponent);
    return places >= 0 ? [numerator, 10n ** BigInt(places)] : [numerator * 10n ** BigInt(-places), 1n];
  }
  function llnState(input) {
    parameters(input);
    const n = integer(input.n, 1, 200), p = bounded(input.p, 0, 1), epsilon = bounded(input.epsilon, 0, 1), seed = integer(input.seed, 0, 4294967295);
    if (epsilon === 0) throw new RangeError('Expected a positive epsilon');
    let generator = seed, successes = 0;
    const trajectory = [];
    for (let i = 1; i <= n; i++) {
      generator = (Math.imul(1664525, generator) + 1013904223) >>> 0;
      if (generator / 4294967296 < p) successes++;
      trajectory.push(successes / i);
    }
    const [pn, pd] = decimalRatio(p), [en, ed] = decimalRatio(epsilon);
    const denominator = pd * ed, center = BigInt(n) * pn * ed, radius = BigInt(n) * en * pd;
    const distribution = binomialState({ n, p });
    let exactTail = 0;
    distribution.pmf.forEach((mass, k) => {
      const distance = BigInt(k) * denominator - center;
      if ((distance < 0n ? -distance : distance) >= radius) exactTail += mass;
    });
    const variance = p * (1 - p);
    // Evaluate endpoints first so an underflowed epsilon^2 cannot turn 0/0 into NaN.
    const bound = variance === 0 ? 0 : Math.min(1, variance / (n * epsilon * epsilon));
    return { n, p, epsilon, seed, mean: trajectory[n - 1], trajectory, bound, exactTail: Math.min(1, exactTail) };
  }
  return Object.freeze({ bayesState, independenceState, binomialState, densityState, llnState });
}));
