"""Value at Risk and Expected Shortfall (Hull 11e, Ch.22)."""

import math

import numpy as np
from scipy.stats import norm


def historical_var_es(pnl, alpha=0.99):
    """Historical-simulation VaR and ES from a P&L array (gains positive).

    Hull's convention with n scenarios: k = max(1, ceil((1-alpha)*n));
    VaR = k-th worst loss; ES = mean of the k worst losses
    (99% with 500 scenarios -> 5th worst / mean of worst five).
    Returns (var, es) as positive loss amounts.
    """
    losses = -np.asarray(pnl, dtype=float)
    n = len(losses)
    k = max(1, round((1.0 - alpha) * n))
    worst = np.sort(losses)[::-1][:k]
    return float(worst[-1]), float(worst.mean())


def normal_var(sigma, alpha=0.99, horizon=1.0, mu=0.0):
    """Model-building VaR = z_alpha * sigma * sqrt(h) - mu * h (Hull Ch.22).

    sigma is the one-day standard deviation in currency units.
    """
    return float(norm.ppf(alpha) * sigma * math.sqrt(horizon) - mu * horizon)


def normal_es(sigma, alpha=0.99, horizon=1.0, mu=0.0):
    """Normal ES = sigma * sqrt(h) * phi(z_alpha)/(1-alpha) - mu*h (Hull eq. 22.1)."""
    z = norm.ppf(alpha)
    return float(sigma * math.sqrt(horizon) * norm.pdf(z) / (1.0 - alpha) - mu * horizon)


def portfolio_sigma(amounts, vols, corr):
    """Dollar sigma of a linear portfolio: sqrt(a^T C a), C_ij = rho_ij s_i s_j
    (Hull eq. 22.3/22.4). amounts in currency units, vols daily."""
    a = np.asarray(amounts, dtype=float)
    v = np.asarray(vols, dtype=float)
    c = np.asarray(corr, dtype=float) * np.outer(v, v)
    return float(np.sqrt(a @ c @ a))
