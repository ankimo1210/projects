// Pure numerics behind the labs, kept out of the .tsx/.ts canvas code so they can
// be imported by node --test. Same split as numerical-functions.mjs: nothing here
// touches a canvas, a React tree, or the DOM -- every export is a function of its
// arguments alone, which is what makes the regression tests in
// tests/numerical-regression.test.mjs possible.

import { normalCdf, normalPdf } from "./numerical-functions.mjs";

/**
 * Chambers-Mallows-Stuck sampler for a symmetric alpha-stable variable.
 * alpha = 2 degenerates to a Gaussian; smaller alpha means heavier tails.
 */
export function symmetricStable(random, alpha) {
  const angle = Math.PI * (random() - 0.5);
  const exponential = -Math.log(Math.max(random(), 1e-12));
  return Math.sin(alpha * angle) / Math.cos(angle) ** (1 / alpha) *
    (Math.cos((1 - alpha) * angle) / exponential) ** ((1 - alpha) / alpha);
}

/**
 * Autocovariance of fractional Gaussian noise at lags 0..steps-1, unit variance.
 * At hurst = 0.5 every lag past 0 vanishes -- that is the independent-increment
 * case, i.e. ordinary Brownian motion.
 */
export function fractionalGaussianCovariance(steps, hurst) {
  return Array.from({ length: steps }, (_, lag) =>
    0.5 * ((lag + 1) ** (2 * hurst) - 2 * lag ** (2 * hurst) + Math.abs(lag - 1) ** (2 * hurst))
  );
}

/** Cholesky factor of the Toeplitz matrix built from an autocovariance-by-lag array. */
export function toeplitzCholesky(covarianceByLag, steps) {
  const cholesky = Array.from({ length: steps }, () => Array.from({ length: steps }, () => 0));
  for (let row = 0; row < steps; row += 1) {
    for (let column = 0; column <= row; column += 1) {
      let sum = covarianceByLag[row - column];
      for (let inner = 0; inner < column; inner += 1) {
        sum -= cholesky[row][inner] * cholesky[column][inner];
      }
      cholesky[row][column] = row === column
        ? Math.sqrt(Math.max(sum, 1e-12))
        : sum / cholesky[column][column];
    }
  }
  return cholesky;
}

/** Black-Scholes call value and delta. */
export function callValueDelta(spot, strike, rate, sigma, tau) {
  if (tau <= 1e-9) return { value: Math.max(spot - strike, 0), delta: spot > strike ? 1 : 0 };
  const vol = sigma * Math.sqrt(tau);
  const d1 = (Math.log(spot / strike) + (rate + 0.5 * sigma ** 2) * tau) / vol;
  const d2 = d1 - vol;
  return {
    value: spot * normalCdf(d1) - strike * Math.exp(-rate * tau) * normalCdf(d2),
    delta: normalCdf(d1),
  };
}

/** Terminal payoff selector shared by the backward-equation lab. */
export function terminalPayoff(choice, value, strike) {
  if (choice === 1) return value > strike ? 1 : 0;
  if (choice === 2) return value * value;
  return Math.max(value - strike, 0);
}

/**
 * Closed-form solution of the backward Kolmogorov equation for arithmetic
 * Brownian motion: u(t, x) = E[payoff(X_T) | X_t = x].
 */
export function backwardValue(settings, choice, time, state) {
  const tau = Math.max(settings.horizon - time, 0);
  if (tau < 1e-8) return terminalPayoff(choice, state, settings.strike);
  const mean = state + settings.mu * tau;
  const sd = settings.sigma * Math.sqrt(tau);
  if (choice === 1) return normalCdf((mean - settings.strike) / sd);
  if (choice === 2) return mean * mean + sd * sd;
  const distance = mean - settings.strike;
  const d = distance / sd;
  return distance * normalCdf(d) + sd * normalPdf(d, 0, 1);
}

/**
 * Feynman-Kac in closed form for E[exp(-r T) exp(-X_T^2)] with X_T Gaussian:
 * the Gaussian integral of a Gaussian weight is a Gaussian again.
 */
export function feynmanKacExact(settings) {
  const variance = settings.sigma ** 2 * settings.horizon;
  const mean = settings.x0 + settings.mu * settings.horizon;
  return Math.exp(-settings.rate * settings.horizon) /
    Math.sqrt(1 + 2 * variance) *
    Math.exp(-(mean * mean) / (1 + 2 * variance));
}

/** Vasicek zero-coupon yield under Q, from the affine bond price P = A e^{-B r}. */
export function vasicekZeroYield(kappa, theta, sigma, shortRate, maturity) {
  const bondLoading = (1 - Math.exp(-kappa * maturity)) / kappa;
  const logA = (theta - sigma ** 2 / (2 * kappa ** 2)) * (bondLoading - maturity) -
    sigma ** 2 * bondLoading ** 2 / (4 * kappa);
  return -(logA - bondLoading * shortRate) / maturity;
}
