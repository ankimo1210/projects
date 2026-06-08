"""Credit risk and credit derivatives (Hull 11e, Ch.24/25)."""

import math

from scipy.optimize import fsolve
from scipy.stats import norm


def survival_prob(t, hazard):
    """Survival probability S(t) = exp(-lambda * t) for a constant hazard."""
    return math.exp(-hazard * t)


def default_prob(t, hazard):
    """Cumulative default probability Q(t) = 1 - S(t) (Hull eq. 24.1)."""
    return 1.0 - survival_prob(t, hazard)


def hazard_from_spread(spread, recovery):
    """Average hazard rate from a credit spread: lambda ~ s / (1 - R) (Hull eq. 24.2)."""
    return spread / (1.0 - recovery)


def cds_spread(hazard, recovery, r, maturity, freq=4):
    """Par CDS spread under a constant hazard (Hull Ch.25 discrete legs).

    Protection leg: per-period default prob (S_{i-1} - S_i) times (1 - R),
    discounted to mid-period. Premium leg: spread * survival-weighted annuity
    plus accrual on default. Returns the par spread (protection / annuity).
    """
    n = round(maturity * freq)
    dt = 1.0 / freq
    protection = 0.0
    annuity = 0.0
    s_prev = 1.0
    for i in range(1, n + 1):
        t = i * dt
        s = survival_prob(t, hazard)
        d_pd = s_prev - s
        df_mid = math.exp(-r * (t - 0.5 * dt))
        protection += (1.0 - recovery) * df_mid * d_pd
        annuity += math.exp(-r * t) * s * dt + df_mid * d_pd * 0.5 * dt
        s_prev = s
    return protection / annuity


def merton_default_prob(E0, sigma_E, D, r, T):
    """Merton structural model: solve for (V0, sigma_V) and risk-neutral Q.

    Equity = call on firm assets (Hull eq. 24.3); Ito link (eq. 24.4).
    Returns (V0, sigma_V, Q) with Q = N(-d2).
    """

    def equations(x):
        v0, sig_v = x
        d1 = (math.log(v0 / D) + (r + 0.5 * sig_v**2) * T) / (sig_v * math.sqrt(T))
        d2 = d1 - sig_v * math.sqrt(T)
        eq1 = v0 * norm.cdf(d1) - D * math.exp(-r * T) * norm.cdf(d2) - E0
        eq2 = norm.cdf(d1) * sig_v * v0 - sigma_E * E0
        return [eq1, eq2]

    v0, sig_v = fsolve(equations, [E0 + D, 0.2], full_output=False)
    d1 = (math.log(v0 / D) + (r + 0.5 * sig_v**2) * T) / (sig_v * math.sqrt(T))
    d2 = d1 - sig_v * math.sqrt(T)
    return float(v0), float(sig_v), float(norm.cdf(-d2))


def gaussian_copula_conditional(q, a, factor):
    """Conditional default prob given systemic factor F (Hull eq. 24.8)."""
    return float(norm.cdf((norm.ppf(q) - a * factor) / math.sqrt(1.0 - a**2)))


def vasicek_credit_var(q, rho, conf):
    """Vasicek single-factor credit-VaR loss rate (Hull eq. 24.10)."""
    return float(norm.cdf((norm.ppf(q) + math.sqrt(rho) * norm.ppf(conf)) / math.sqrt(1.0 - rho)))
