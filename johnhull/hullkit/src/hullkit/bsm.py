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


def gamma(S, K, r, sigma, T, q=0.0):
    """Gamma d2V/dS2 — identical for calls and puts (Hull Ch.19, Table 19.6)."""
    return math.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) / (S * sigma * math.sqrt(T))


def vega(S, K, r, sigma, T, q=0.0):
    """Vega dV/dsigma per 1.0 of vol (divide by 100 for per-1%); same for calls/puts."""
    return S * math.exp(-q * T) * norm.pdf(d1(S, K, r, sigma, T, q)) * math.sqrt(T)


def call_theta(S, K, r, sigma, T, q=0.0):
    """Call theta per YEAR (divide by 365 for per-calendar-day), Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * math.sqrt(T)
    return (
        -S * math.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * math.sqrt(T))
        - r * K * math.exp(-r * T) * norm.cdf(d_2)
        + q * S * math.exp(-q * T) * norm.cdf(d_1)
    )


def put_theta(S, K, r, sigma, T, q=0.0):
    """Put theta per YEAR, Hull Table 19.6."""
    d_1 = d1(S, K, r, sigma, T, q)
    d_2 = d_1 - sigma * math.sqrt(T)
    return (
        -S * math.exp(-q * T) * norm.pdf(d_1) * sigma / (2.0 * math.sqrt(T))
        + r * K * math.exp(-r * T) * norm.cdf(-d_2)
        - q * S * math.exp(-q * T) * norm.cdf(-d_1)
    )


def call_rho(S, K, r, sigma, T, q=0.0):
    """Call rho dV/dr, Hull Table 19.6."""
    return K * T * math.exp(-r * T) * norm.cdf(d2(S, K, r, sigma, T, q))


def put_rho(S, K, r, sigma, T, q=0.0):
    """Put rho dV/dr (negative), Hull Table 19.6."""
    return -K * T * math.exp(-r * T) * norm.cdf(-d2(S, K, r, sigma, T, q))
