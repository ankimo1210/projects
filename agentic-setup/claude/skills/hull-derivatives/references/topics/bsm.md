# Topic: Black-Scholes-Merton Model

## 対応章
- Ch.15 The Black-Scholes-Merton Model — [chapters/ch15_bsm.md](../chapters/ch15_bsm.md)

## クイック公式

### BSM PDE
$$\frac{\partial f}{\partial t} + rS\frac{\partial f}{\partial S} + \frac{1}{2}\sigma^2 S^2 \frac{\partial^2 f}{\partial S^2} = rf$$
- Derived from delta-hedge portfolio (no $\mu$ — model-free of investor risk preference)
- See: ch15 §3

### European Call and Put (no dividends)
$$c = S_0 N(d_1) - K e^{-rT} N(d_2)$$
$$p = K e^{-rT} N(-d_2) - S_0 N(-d_1)$$
$$d_1 = \frac{\ln(S_0/K) + (r + \sigma^2/2)\,T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$
- $N(d_2)$: risk-neutral probability of call exercise
- See: ch15 §3

### BSM with Continuous Yield $q$
$$c = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$
$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)\,T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$
- Index: $q$ = dividend yield; FX (Garman-Kohlhagen): $q = r_f$; Futures (Black-76): $q = r$
- See: ch15 §3 (q-extension), ch17 §3

### Discrete Dividends
$$S_0' = S_0 - \mathrm{PV(div)} = S_0 - \sum_i D_i e^{-r t_i}$$
- Substitute $S_0'$ for $S_0$ in BSM; do NOT subtract from strike $K$
- See: ch15 §3

### Lognormal Distribution of $S_T$
$$\ln S_T \sim N\!\left(\ln S_0 + \left(r - \frac{\sigma^2}{2}\right)T,\; \sigma^2 T\right)$$
- Under risk-neutral measure ($\mu \to r$)
- See: ch15 §3

### Risk-Neutral Valuation
$$f = e^{-rT}\hat{E}[f_T]$$
- $\hat{E}$: expectation under risk-neutral measure (replace $\mu \to r$)
- See: ch15 §3

### Historical Volatility Estimator
$$u_i = \ln\frac{S_i}{S_{i-1}}, \quad s = \sqrt{\frac{1}{n-1}\sum_{i=1}^n (u_i - \bar{u})^2}, \quad \hat\sigma = \frac{s}{\sqrt{\tau}}$$
- $\tau = 1/252$ for daily prices; standard error $\approx \hat\sigma/\sqrt{2n}$
- See: ch15 §3

### Black's Approximation (American Call with Dividends)
$$C \approx \max\bigl(c(S_0', K, r, \sigma, T),\; c(S_0, K, r, \sigma, t_n)\bigr)$$
- First term: hold to maturity $T$ (use $S_0'$); second term: exercise just before last dividend $t_n$ (use $S_0$)
- See: ch15 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def bs_call(S, K, r, q, sigma, T):
    """European call on continuous-dividend lognormal stock.

    Parameters
    ----------
    S, K    : spot price, strike
    r       : domestic risk-free rate (continuous, annual)
    q       : continuous dividend yield (0 for no-dividend; r_f for FX)
    sigma   : volatility (annual)
    T       : time to maturity (years)
    """
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def bs_put(S, K, r, q, sigma, T):
    """European put via BSM."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def implied_vol_call(price, S, K, r, q, T, lo=1e-6, hi=5.0):
    """Implied volatility for a European call via Brent's method.

    Solves bs_call(sigma) = price in [lo, hi].
    """
    f = lambda s: bs_call(S, K, r, q, s, T) - price
    return brentq(f, lo, hi)


def hist_vol(prices, tau=1.0/252):
    """Annualized historical volatility from a price series (trading-day basis)."""
    u = np.log(np.array(prices[1:]) / np.array(prices[:-1]))
    s = np.std(u, ddof=1)
    return s / math.sqrt(tau)


def blacks_approx_american_call(S, K, r, sigma, T, dividends):
    """Black's approximation for American call with discrete dividends.

    dividends: list of (amount, time) tuples, e.g. [(D1, t1), (D2, t2)]
    Returns approximate American call price.
    """
    pv_div = sum(D * math.exp(-r * t) for D, t in dividends)
    S_prime = S - pv_div
    # Option held to maturity (uses S')
    c_maturity = bs_call(S_prime, K, r, 0.0, sigma, T)
    # Option exercised just before last dividend
    if dividends:
        t_n = max(t for _, t in dividends)
        c_last_div = bs_call(S, K, r, 0.0, sigma, t_n)
    else:
        c_last_div = 0.0
    return max(c_maturity, c_last_div)


# ── Verification (put-call parity) ────────────────────────────────────────
if __name__ == '__main__':
    S, K, r, q, sigma, T = 100, 100, 0.05, 0.0, 0.20, 1.0
    c = bs_call(S, K, r, q, sigma, T)
    p = bs_put(S, K, r, q, sigma, T)
    # Put-call parity: c - p = S - K*exp(-rT)
    print(f"C={c:.4f}  P={p:.4f}")
    print(f"C-P={c-p:.4f}  S-K*e^-rT={S - K*math.exp(-r*T):.4f}")
    # Expected: C=10.4506  P=5.5735  C-P=4.8771  S-Ke^-rT=4.8771
    iv = implied_vol_call(c, S, K, r, q, T)
    print(f"Implied vol: {iv:.4f}")  # Expected: 0.2000
```

## デシジョンガイド

**BSM vs Binomial**
- BSM (closed form): path-independent European options only; instantaneous computation
- Binomial: needed for American options, discrete dividends, or any path-dependent feature
- For non-dividend European calls/puts, BSM is exact; binomial converges to BSM

**Constant volatility assumption**
- BSM assumes $\sigma$ is constant; real markets exhibit vol smile/skew (Ch.20)
- Use BSM as a benchmark and quoting convention (implied vol); do not assume flat vol surface

**Dividend treatment**
| Dividend type | Approach |
|---|---|
| No dividend | $q = 0$, use BSM directly |
| Continuous yield (index) | $q$ = dividend yield, BSM with $q$ |
| Discrete (known amounts) | $S_0' = S_0 - \mathrm{PV(div)}$, then BSM |
| American call + discrete | Black's approximation |

**Historical vs implied volatility**
- Historical vol: backward-looking estimate; useful for checking reasonableness
- Implied vol: market-consensus forward-looking estimate; use for pricing and hedging
- When they diverge significantly, check for upcoming events (earnings, FOMC) already priced in IV

**When BSM fails**
- Jumps in stock price (Merton jump-diffusion, Ch.27)
- Stochastic volatility (Heston, Ch.27)
- Deep ITM/OTM long-dated options: vol smile matters most
- Interest-rate derivatives: use forward-measure / Black-76 instead (Ch.29)
