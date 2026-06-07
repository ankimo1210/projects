"""Black-Scholes-Merton analytic formulas (Hull 11e, Ch.15 / Ch.17).

The continuous yield ``q`` generalizes the formulas:
stock index -> q = dividend yield, currency -> q = foreign risk-free rate,
futures -> q = r (Black-76 with S = futures price).
"""

import math

from scipy.stats import norm


def d1(S, K, r, sigma, T, q=0.0):
    """Hull eq. (15.20) numerator term."""
    return (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))


def d2(S, K, r, sigma, T, q=0.0):
    return d1(S, K, r, sigma, T, q) - sigma * math.sqrt(T)


def call_price(S, K, r, sigma, T, q=0.0):
    """European call price, Hull eq. (15.20) / (17.4)."""
    return S * math.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q)) - K * math.exp(
        -r * T
    ) * norm.cdf(d2(S, K, r, sigma, T, q))


def put_price(S, K, r, sigma, T, q=0.0):
    """European put price, Hull eq. (15.21) / (17.5)."""
    return K * math.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q)) - S * math.exp(
        -q * T
    ) * norm.cdf(-d1(S, K, r, sigma, T, q))


def call_delta(S, K, r, sigma, T, q=0.0):
    """Analytic call delta e^{-qT} N(d1) (Hull Ch.19; needed for tree comparisons)."""
    return math.exp(-q * T) * norm.cdf(d1(S, K, r, sigma, T, q))


def put_delta(S, K, r, sigma, T, q=0.0):
    """Analytic put delta e^{-qT} (N(d1) - 1)."""
    return math.exp(-q * T) * (norm.cdf(d1(S, K, r, sigma, T, q)) - 1.0)
