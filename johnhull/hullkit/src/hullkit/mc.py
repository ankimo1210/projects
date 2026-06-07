"""GBM Monte Carlo simulation (Hull 11e, Ch.14)."""

import numpy as np


def simulate_gbm_paths(S0, mu, sigma, T, n_steps, n_paths, rng=None):
    """Simulate GBM paths with the exact log-Euler scheme.

    ln S_t = ln S0 + (mu - sigma^2/2) t + sigma W_t  (Hull eq. 14.17),
    so the terminal distribution is exact for any step size — unlike the
    naive Euler scheme dS = mu S dt + sigma S dz.

    Returns an array of shape (n_paths, n_steps + 1); column 0 equals S0.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    dt = T / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.log(S0) + np.cumsum(log_returns, axis=1)
    return np.column_stack([np.full(n_paths, S0), np.exp(log_paths)])


def gbm_theory(S0, mu, sigma, T):
    """Theoretical E[S_T] and Var[S_T] under GBM (Hull §14.7)."""
    e_st = S0 * np.exp(mu * T)
    var_st = S0**2 * np.exp(2.0 * mu * T) * (np.exp(sigma**2 * T) - 1.0)
    return float(e_st), float(var_st)
