"""Numerical sanity checks for hull-derivatives chapter references.

Run with: uv run --with numpy --with scipy python verify_formula.py
"""
import math
import numpy as np
from scipy.stats import norm


# --- ch15: Black-Scholes-Merton -------------------------------------------------

def bs_call(S, K, r, q, sigma, T):
    """European call on a continuous-dividend lognormal stock."""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_put(S, K, r, q, sigma, T):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def test_bsm_put_call_parity():
    """C - P = S*e^{-qT} - K*e^{-rT}."""
    S, K, r, q, sigma, T = 100.0, 100.0, 0.05, 0.02, 0.20, 1.0
    c = bs_call(S, K, r, q, sigma, T)
    p = bs_put(S, K, r, q, sigma, T)
    lhs = c - p
    rhs = S * np.exp(-q * T) - K * np.exp(-r * T)
    assert abs(lhs - rhs) < 1e-10, f"parity violated: {lhs} vs {rhs}"
    print(f"[ch15] BSM put-call parity OK   C={c:.4f} P={p:.4f} C-P={lhs:.6f} ~ {rhs:.6f}")


# --- ch13: Binomial tree ------------------------------------------------------

def binomial_european_call(S, K, r, sigma, T, N):
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    j = np.arange(N + 1)
    ST = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(ST - K, 0.0)
    for _ in range(N):
        V = disc * (p * V[:-1] + (1 - p) * V[1:])
    return V[0]


def test_binomial_converges_to_bsm():
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    bsm = bs_call(S, K, r, 0.0, sigma, T)
    binom = binomial_european_call(S, K, r, sigma, T, N=500)
    err = abs(binom - bsm)
    assert err < 0.05, f"binomial too far from BSM: {err:.4f}"
    print(f"[ch13] Binomial -> BSM   BSM={bsm:.4f} Binomial(N=500)={binom:.4f} err={err:.4f}")


# --- ch31: Vasicek bond price -------------------------------------------------

def vasicek_bond_price(r0, a, b, sigma, t, T):
    """Zero-coupon bond price under dr = a(b - r) dt + sigma dW.

    P(t,T) = A(t,T) * exp(-B(t,T) * r0).
    """
    tau = T - t
    if tau <= 0:
        return 1.0
    B = (1 - math.exp(-a * tau)) / a
    A = math.exp(
        (B - tau) * (a**2 * b - sigma**2 / 2) / a**2
        - (sigma**2 * B**2) / (4 * a)
    )
    return A * math.exp(-B * r0)


def test_vasicek_at_t_equals_T():
    """At t=T the bond pays 1; at t=0 a 1Y bond is in (0.9, 1.0)."""
    p_end = vasicek_bond_price(0.03, 0.1, 0.04, 0.01, t=1.0, T=1.0)
    assert abs(p_end - 1.0) < 1e-10, f"P(T,T) != 1: {p_end}"
    p1 = vasicek_bond_price(0.03, 0.1, 0.04, 0.01, t=0.0, T=1.0)
    assert 0.9 < p1 < 1.0, f"1Y Vasicek bond out of expected range: {p1}"
    print(f"[ch31] Vasicek P(T,T)=1 OK; P(0,1)={p1:.4f}")


if __name__ == "__main__":
    test_bsm_put_call_parity()
    test_binomial_converges_to_bsm()
    test_vasicek_at_t_equals_T()
    print("All Hull reference checks passed.")
