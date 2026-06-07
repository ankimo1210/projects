"""CRR binomial trees (Hull 11e, Ch.13).

Node convention: level ``i`` (0..N) has ``i+1`` nodes indexed ``j=0..i``,
where ``j=0`` is the highest stock price: S_{i,j} = S0 * u^(i-j) * d^j.
"""

import math

import numpy as np


def crr_params(sigma, dt):
    """Cox-Ross-Rubinstein u and d (Hull eq. 13.15-13.16)."""
    u = math.exp(sigma * math.sqrt(dt))
    return u, 1.0 / u


def risk_neutral_p(u, d, r, dt, q=0.0):
    """Risk-neutral up probability p=(a-d)/(u-d), a=e^{(r-q)dt} (Hull eq. 13.18).

    q=0 plain stock; q=dividend yield for indices; q=foreign rate for
    currencies; q=r gives a=1 for futures options.
    """
    a = math.exp((r - q) * dt)
    p = (a - d) / (u - d)
    if not 0.0 < p < 1.0:
        raise ValueError(f"arbitrage: need d < e^((r-q)dt) < u, got p={p:.4f}")
    return p


def binomial_tree(S0, K, r, T, N, u, d, q=0.0, kind="call", american=False):
    """Full stock and option trees by backward induction (Hull eq. 13.5).

    Returns (stock, option): two lists of length N+1; element i is an
    ndarray of the i+1 node values at step i.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    dt = T / N
    p = risk_neutral_p(u, d, r, dt, q)
    disc = math.exp(-r * dt)

    def payoff(s):
        return np.maximum(s - K, 0.0) if kind == "call" else np.maximum(K - s, 0.0)

    stock = [S0 * (u ** (i - np.arange(i + 1))) * (d ** np.arange(i + 1)) for i in range(N + 1)]
    option = [None] * (N + 1)
    option[N] = payoff(stock[N])
    for i in range(N - 1, -1, -1):
        cont = disc * (p * option[i + 1][:-1] + (1.0 - p) * option[i + 1][1:])
        option[i] = np.maximum(cont, payoff(stock[i])) if american else cont
    return stock, option


def crr_price(S0, K, r, sigma, T, N, q=0.0, kind="call", american=False):
    """Price with CRR parameterization; returns the root option value."""
    u, d = crr_params(sigma, T / N)
    _, option = binomial_tree(S0, K, r, T, N, u, d, q=q, kind=kind, american=american)
    return float(option[0][0])


def tree_delta(stock, option):
    """Root-node delta (f_u - f_d) / (S0 u - S0 d) (Hull eq. 13.1)."""
    return float((option[1][0] - option[1][1]) / (stock[1][0] - stock[1][1]))
