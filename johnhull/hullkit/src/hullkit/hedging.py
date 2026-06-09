"""Delta-hedging simulations (Hull 11e, Ch.19 §19.2/§19.4, Tables 19.1-19.4).

Scope: European call on a non-dividend stock (q=0). The writer hedges at
n_rebalance equally spaced times; cash carried at r; settlement at expiry
(buy the shortfall and deliver at K when ITM). Costs are discounted to t=0
per share. The mean cost converges to the BSM price as n_rebalance grows,
independently of the real-world drift mu; dispersion shrinks ~ 1/sqrt(n).
"""

import numpy as np
from scipy.stats import norm

from . import mc


def _call_delta_vec(S, K, r, sigma, tau):
    """Vectorized BSM call delta (q=0) for an array of spots at one tau."""
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * tau) / (sigma * np.sqrt(tau))
    return norm.cdf(d1)


def _settle(debt, holdings, s_T, K, growth, r, T):
    """Grow debt one last step, settle the written call, discount to t=0."""
    debt = debt * growth
    itm = s_T > K
    debt = np.where(
        itm,
        debt + (1.0 - holdings) * s_T - K,  # buy shortfall, deliver at K
        debt - holdings * s_T,  # sell leftover shares
    )
    return debt * np.exp(-r * T)


def simulate_delta_hedge(S0, K, r, sigma, T, n_rebalance, n_paths, mu=None, rng=None):
    """Discounted per-share cost of writing + delta-hedging one European call."""
    if n_rebalance < 1:
        raise ValueError("n_rebalance must be >= 1")
    if mu is None:
        mu = r
    dt = T / n_rebalance
    paths = mc.simulate_gbm_paths(S0, mu, sigma, T, n_rebalance, n_paths, rng=rng)
    growth = float(np.exp(r * dt))
    holdings = _call_delta_vec(paths[:, 0], K, r, sigma, T)
    debt = holdings * paths[:, 0]
    for i in range(1, n_rebalance):
        tau = T - i * dt
        delta_i = _call_delta_vec(paths[:, i], K, r, sigma, tau)
        debt = debt * growth + (delta_i - holdings) * paths[:, i]
        holdings = delta_i
    return _settle(debt, holdings, paths[:, -1], K, growth, r, T)


def simulate_stop_loss_hedge(S0, K, r, sigma, T, n_rebalance, n_paths, mu=None, rng=None):
    """Naive stop-loss 'hedge' (Hull §19.2): hold 1 share iff S > K, traded at grid prices."""
    if n_rebalance < 1:
        raise ValueError("n_rebalance must be >= 1")
    if mu is None:
        mu = r
    dt = T / n_rebalance
    paths = mc.simulate_gbm_paths(S0, mu, sigma, T, n_rebalance, n_paths, rng=rng)
    growth = float(np.exp(r * dt))
    holdings = (paths[:, 0] > K).astype(float)
    debt = holdings * paths[:, 0]
    for i in range(1, n_rebalance):
        target = (paths[:, i] > K).astype(float)
        debt = debt * growth + (target - holdings) * paths[:, i]
        holdings = target
    return _settle(debt, holdings, paths[:, -1], K, growth, r, T)
