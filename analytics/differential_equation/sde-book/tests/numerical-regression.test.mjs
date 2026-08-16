import assert from "node:assert/strict";
import test from "node:test";

import { memoizedDiagnostics } from "../app/diagnostics-cache.mjs";
import { normalCdf, normalPdf, normalQuantile } from "../app/numerical-functions.mjs";
import { binomial, mulberry32 } from "../app/random-distributions.mjs";
import {
  backwardValue,
  callValueDelta,
  feynmanKacExact,
  fractionalGaussianCovariance,
  symmetricStable,
  terminalPayoff,
  toeplitzCholesky,
  vasicekZeroYield,
} from "../app/stochastic-models.mjs";

test("diagnostics are reused only for the same immutable settings and key", () => {
  const settings = { seed: 42 };
  let calculations = 0;
  const calculate = () => ({ value: ++calculations });

  const first = memoizedDiagnostics(settings, "lab-a", calculate);
  const repeated = memoizedDiagnostics(settings, "lab-a", calculate);
  const anotherLab = memoizedDiagnostics(settings, "lab-b", calculate);
  const changedSettings = memoizedDiagnostics({ seed: 43 }, "lab-a", calculate);

  assert.strictEqual(repeated, first);
  assert.equal(anotherLab.value, 2);
  assert.equal(changedSettings.value, 3);
  assert.equal(calculations, 3);
});

test("normal CDF and quantile remain numerical inverses", () => {
  for (const probability of [0.001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.999]) {
    assert.ok(Math.abs(normalCdf(normalQuantile(probability)) - probability) < 2e-7);
  }
  assert.ok(Math.abs(normalCdf(0) - 0.5) < 1e-7);
  assert.ok(Math.abs(normalCdf(-1.25) - (1 - normalCdf(1.25))) < 1e-12);
});

test("binomial preserves rare SIR infection probabilities", () => {
  const population = 120;
  const infected = 4;
  const susceptible = population - infected;
  const beta = 1.6;
  const dt = 10 / 300;
  const probability = 1 - Math.exp((-beta * infected * dt) / population);
  const exactAtLeastOne = 1 - (1 - probability) ** susceptible;
  const random = mulberry32(4201);
  const draws = 120_000;
  let atLeastOne = 0;
  let total = 0;

  for (let index = 0; index < draws; index += 1) {
    const value = binomial(random, susceptible, probability);
    total += value;
    if (value > 0) atLeastOne += 1;
  }

  assert.ok(Math.abs(atLeastOne / draws - exactAtLeastOne) < 0.004);
  assert.ok(Math.abs(total / draws - susceptible * probability) < 0.008);
});

test("binomial handles rare failures without leaving its support", () => {
  const random = mulberry32(4001);
  const trials = 100;
  const probability = 0.992;
  const draws = 80_000;
  let total = 0;

  for (let index = 0; index < draws; index += 1) {
    const value = binomial(random, trials, probability);
    assert.ok(value >= 0 && value <= trials);
    total += value;
  }

  assert.ok(Math.abs(total / draws - trials * probability) < 0.03);
  assert.equal(binomial(random, trials, 0), 0);
  assert.equal(binomial(random, trials, 1), trials);
});

test("feynmanKacExact matches quadrature of the discounted terminal weight", () => {
  // u(0, x0) = e^{-rT} E[exp(-X_T^2)] with X_T ~ N(x0 + mu T, sigma^2 T).
  // The closed form is only worth trusting if an independent integral agrees.
  for (const settings of [
    { sigma: 0.8, horizon: 1.4, x0: 0.3, mu: -0.2, rate: 0.05 },
    { sigma: 1.5, horizon: 0.6, x0: -1.1, mu: 0.7, rate: 0.0 },
    { sigma: 0.2, horizon: 3.0, x0: 0.0, mu: 0.0, rate: 0.12 },
  ]) {
    const mean = settings.x0 + settings.mu * settings.horizon;
    const sd = settings.sigma * Math.sqrt(settings.horizon);
    const steps = 20_000;
    const low = mean - 12 * sd;
    const step = (24 * sd) / steps;
    let integral = 0;
    for (let index = 0; index <= steps; index += 1) {
      const x = low + index * step;
      const weight = index === 0 || index === steps ? 0.5 : 1;
      integral += weight * Math.exp(-x * x) * normalPdf(x, mean, sd) * step;
    }
    const quadrature = Math.exp(-settings.rate * settings.horizon) * integral;
    assert.ok(
      Math.abs(feynmanKacExact(settings) - quadrature) < 1e-9,
      `closed form ${feynmanKacExact(settings)} vs quadrature ${quadrature}`,
    );
  }
});

test("backwardValue solves E[payoff(X_T)] for all three terminal payoffs", () => {
  const settings = { horizon: 2.0, mu: 0.15, sigma: 0.9, strike: 1.2 };
  const state = 0.7;

  for (const choice of [0, 1, 2]) {
    const tau = settings.horizon;
    const mean = state + settings.mu * tau;
    const sd = settings.sigma * Math.sqrt(tau);
    // The digital payoff jumps at the strike and the call payoff kinks there, so
    // the quadrature grid starts AT the strike -- a grid that straddles the jump
    // is only O(step) accurate and lands ~1e-4 off, which would look like a bug
    // in backwardValue rather than in the reference integral.
    const low = choice === 2 ? mean - 12 * sd : settings.strike;
    const high = mean + 12 * sd;
    // Midpoint rule, so no node lands exactly on the strike: the digital payoff
    // is discontinuous there and a trapezoid endpoint would silently drop half a
    // step of probability mass (5.8e-5 here -- big enough to look like a bug).
    const steps = 40_000;
    const step = (high - low) / steps;
    let expectation = 0;
    for (let index = 0; index < steps; index += 1) {
      const x = low + (index + 0.5) * step;
      expectation += terminalPayoff(choice, x, settings.strike) * normalPdf(x, mean, sd) * step;
    }
    // normalCdf is an Abramowitz-Stegun approximation, so ~1e-7 is the floor.
    assert.ok(
      Math.abs(backwardValue(settings, choice, 0, state) - expectation) < 2e-6,
      `choice ${choice}: ${backwardValue(settings, choice, 0, state)} vs ${expectation}`,
    );
  }

  // At the horizon the solution has to collapse onto the payoff itself.
  for (const choice of [0, 1, 2]) {
    assert.equal(
      backwardValue(settings, choice, settings.horizon, state),
      terminalPayoff(choice, state, settings.strike),
    );
  }
});

test("callValueDelta obeys put-call parity and reports its own derivative", () => {
  const strike = 100;
  const rate = 0.03;
  const sigma = 0.25;
  const tau = 0.75;

  for (const spot of [70, 90, 100, 115, 140]) {
    const { value, delta } = callValueDelta(spot, strike, rate, sigma, tau);

    // Parity: C - P = S - K e^{-rT}. Price the put by quadrature under the
    // risk-neutral lognormal and check the identity closes.
    const drift = (rate - 0.5 * sigma ** 2) * tau;
    const vol = sigma * Math.sqrt(tau);
    const steps = 40_000;
    const low = drift - 12 * vol;
    const step = (24 * vol) / steps;
    let put = 0;
    for (let index = 0; index <= steps; index += 1) {
      const z = low + index * step;
      const weight = index === 0 || index === steps ? 0.5 : 1;
      put += weight * Math.max(strike - spot * Math.exp(z), 0) * normalPdf(z, drift, vol) * step;
    }
    put *= Math.exp(-rate * tau);
    assert.ok(
      Math.abs(value - put - (spot - strike * Math.exp(-rate * tau))) < 2e-4,
      `parity broken at spot ${spot}: C=${value} P=${put}`,
    );

    // Delta must be the spot-derivative of the value it is returned with. The
    // tolerance is set by normalCdf's own error (~1e-7 on a value of order S)
    // divided by the bump, not by the finite difference itself.
    const bump = 0.1;
    const up = callValueDelta(spot + bump, strike, rate, sigma, tau).value;
    const down = callValueDelta(spot - bump, strike, rate, sigma, tau).value;
    assert.ok(Math.abs(delta - (up - down) / (2 * bump)) < 5e-5, `delta mismatch at spot ${spot}`);
  }

  // Expiry collapses onto intrinsic value.
  assert.deepEqual(callValueDelta(120, 100, 0.03, 0.25, 0), { value: 20, delta: 1 });
  assert.deepEqual(callValueDelta(80, 100, 0.03, 0.25, 0), { value: 0, delta: 0 });
});

test("symmetricStable is Gaussian at alpha = 2 and heavy-tailed below it", () => {
  const draws = 60_000;

  const random = mulberry32(9001);
  const gaussian = Array.from({ length: draws }, () => symmetricStable(random, 2));
  const mean = gaussian.reduce((a, b) => a + b, 0) / draws;
  const variance = gaussian.reduce((a, b) => a + (b - mean) ** 2, 0) / draws;
  const fourth = gaussian.reduce((a, b) => a + (b - mean) ** 4, 0) / draws;
  // CMS at alpha = 2 returns 2 * sin(theta)/... which has variance 2, not 1.
  assert.ok(Math.abs(mean) < 0.03, `mean ${mean}`);
  assert.ok(Math.abs(variance - 2) < 0.06, `variance ${variance}`);
  assert.ok(Math.abs(fourth / variance ** 2 - 3) < 0.15, `kurtosis ${fourth / variance ** 2}`);

  // Below alpha = 2 the tails stop being exponential while the bulk barely moves:
  // the median of |X| is nearly unchanged, but the 99.99% quantile and the sample
  // variance explode (a stable law with alpha < 2 has no finite variance at all,
  // so the sample variance is driven entirely by the largest draws).
  const heavyRandom = mulberry32(9001);
  const heavySample = Array.from({ length: draws }, () => symmetricStable(heavyRandom, 1.2));
  const heavyMean = heavySample.reduce((a, b) => a + b, 0) / draws;
  const heavyVariance = heavySample.reduce((a, b) => a + (b - heavyMean) ** 2, 0) / draws;
  const heavy = heavySample.map(Math.abs).sort((a, b) => a - b);
  const light = gaussian.map(Math.abs).sort((a, b) => a - b);
  const quantile = (sorted, p) => sorted[Math.floor(p * (sorted.length - 1))];

  assert.ok(Math.abs(quantile(heavy, 0.5) - quantile(light, 0.5)) < 0.15, "bulk should barely move");
  assert.ok(quantile(heavy, 0.9999) > 20 * quantile(light, 0.9999), "alpha=1.2 tail is not heavy");
  assert.ok(heavyVariance > 100 * variance, `sample variance ${heavyVariance} is not exploding`);
});

test("fractional Gaussian noise reduces to independent increments at H = 0.5", () => {
  const steps = 24;

  const brownian = fractionalGaussianCovariance(steps, 0.5);
  assert.ok(Math.abs(brownian[0] - 1) < 1e-12);
  for (let lag = 1; lag < steps; lag += 1) {
    assert.ok(Math.abs(brownian[lag]) < 1e-12, `lag ${lag} correlation ${brownian[lag]}`);
  }
  // Independent increments => the Cholesky factor is the identity.
  const identity = toeplitzCholesky(brownian, steps);
  for (let row = 0; row < steps; row += 1) {
    for (let column = 0; column <= row; column += 1) {
      assert.ok(Math.abs(identity[row][column] - (row === column ? 1 : 0)) < 1e-9);
    }
  }

  // Persistence above 0.5, anti-persistence below it.
  assert.ok(fractionalGaussianCovariance(steps, 0.8)[1] > 0.2);
  assert.ok(fractionalGaussianCovariance(steps, 0.2)[1] < -0.2);

  // The factor has to actually reproduce the covariance it came from.
  for (const hurst of [0.3, 0.7]) {
    const covariance = fractionalGaussianCovariance(steps, hurst);
    const factor = toeplitzCholesky(covariance, steps);
    for (let row = 0; row < steps; row += 1) {
      for (let column = 0; column <= row; column += 1) {
        let dot = 0;
        for (let inner = 0; inner <= column; inner += 1) dot += factor[row][inner] * factor[column][inner];
        assert.ok(Math.abs(dot - covariance[row - column]) < 1e-9, `H=${hurst} at (${row},${column})`);
      }
    }
  }
});

test("Vasicek zero yield reduces to the deterministic average rate as sigma -> 0", () => {
  const kappa = 0.6;
  const theta = 0.04;
  const shortRate = 0.015;

  for (const maturity of [0.25, 1, 5, 10]) {
    // With no diffusion, r(u) = theta + (r0 - theta) e^{-kappa u} is deterministic,
    // so the zero yield is just its time average over [0, T].
    const average = theta + (shortRate - theta) * (1 - Math.exp(-kappa * maturity)) / (kappa * maturity);
    assert.ok(
      Math.abs(vasicekZeroYield(kappa, theta, 0, shortRate, maturity) - average) < 1e-12,
      `maturity ${maturity}`,
    );
  }

  // With diffusion on, pin the convexity term against the independent Gaussian
  // route: integral_0^T r du is Gaussian, so P = exp(-E + Var/2) exactly.
  for (const sigma of [0.005, 0.02, 0.05]) {
    for (const maturity of [0.25, 1, 5, 10]) {
      const loading = (1 - Math.exp(-kappa * maturity)) / kappa;
      const meanIntegral = theta * maturity + (shortRate - theta) * loading;
      const varianceIntegral = (sigma ** 2 / kappa ** 2) *
        (maturity - 2 * loading + (1 - Math.exp(-2 * kappa * maturity)) / (2 * kappa));
      const expected = (meanIntegral - varianceIntegral / 2) / maturity;
      assert.ok(
        Math.abs(vasicekZeroYield(kappa, theta, sigma, shortRate, maturity) - expected) < 1e-14,
        `sigma ${sigma}, maturity ${maturity}`,
      );
    }
  }

  // Short maturities read off the current short rate.
  assert.ok(Math.abs(vasicekZeroYield(kappa, theta, 0.01, shortRate, 1e-4) - shortRate) < 1e-5);
  // Volatility lowers the yield (the convexity term is strictly negative).
  assert.ok(vasicekZeroYield(kappa, theta, 0.02, shortRate, 10) < vasicekZeroYield(kappa, theta, 0, shortRate, 10));
});
