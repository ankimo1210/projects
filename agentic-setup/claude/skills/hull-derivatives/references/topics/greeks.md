# Topic: Greek Letters

## 対応章
- Ch.19 The Greek Letters — [chapters/ch19_greeks.md](../chapters/ch19_greeks.md)

## クイック公式

### $d_1$, $d_2$ (general form with yield $q$)
$$d_1 = \frac{\ln(S/K) + (r - q + \tfrac{1}{2}\sigma^2)T}{\sigma\sqrt{T}}, \qquad d_2 = d_1 - \sigma\sqrt{T}$$
- See: ch19 §3

### Delta
$$\Delta_c = e^{-qT} N(d_1), \qquad \Delta_p = e^{-qT}(N(d_1) - 1)$$
- Range: $(0,1)$ for calls; $(-1,0)$ for puts
- Forward delta: $e^{-qT}$; futures delta: $e^{(r-q)T}$
- See: ch19 §3

### Gamma
$$\Gamma = \frac{e^{-qT} N'(d_1)}{S\,\sigma\sqrt{T}}, \qquad N'(x) = \frac{1}{\sqrt{2\pi}} e^{-x^2/2}$$
- Identical for calls and puts; always positive for long options
- See: ch19 §3

### Vega
$$\mathcal{V} = S e^{-qT} N'(d_1) \sqrt{T}$$
- Per unit of vol (÷100 for per-1%); identical for calls and puts
- See: ch19 §3

### Theta
$$\Theta_c = -\frac{S e^{-qT} N'(d_1)\sigma}{2\sqrt{T}} - r K e^{-rT} N(d_2) + q S e^{-qT} N(d_1)$$
$$\Theta_p = -\frac{S e^{-qT} N'(d_1)\sigma}{2\sqrt{T}} + r K e^{-rT} N(-d_2) - q S e^{-qT} N(-d_1)$$
- Per year; divide by 365 (calendar) or 252 (trading) for per-day
- See: ch19 §3

### Rho
$$\rho_c = K T e^{-rT} N(d_2), \qquad \rho_p = -K T e^{-rT} N(-d_2)$$
- See: ch19 §3

### BSM PDE Identity (portfolio $\Pi$)
$$\Theta + (r-q)S\Delta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$$
- Delta-neutral ($\Delta=0$): $\Theta + \tfrac{1}{2}\sigma^2 S^2 \Gamma = r\Pi$ — theta and gamma are opponents
- See: ch19 §3

### Portfolio Taylor P&L
$$\Delta\Pi \approx \Theta\,\Delta t + \Delta\cdot\Delta S + \tfrac{1}{2}\Gamma(\Delta S)^2 + \mathcal{V}\cdot\Delta\sigma_{\mathrm{imp}}$$
- Delta-neutral drop: first $\Delta\cdot\Delta S$ term is zero
- See: ch19 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


def _d1d2(S, K, r, q, sigma, T):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def delta(S, K, r, q, sigma, T, kind='call'):
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    if kind == 'call':
        return math.exp(-q * T) * norm.cdf(d1)
    return math.exp(-q * T) * (norm.cdf(d1) - 1.0)


def gamma(S, K, r, q, sigma, T):
    """Same for calls and puts."""
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    return math.exp(-q * T) * norm.pdf(d1) / (S * sigma * math.sqrt(T))


def vega(S, K, r, q, sigma, T):
    """Per 1.0 vol unit — divide by 100 for per-1%-vol."""
    d1, _ = _d1d2(S, K, r, q, sigma, T)
    return S * math.exp(-q * T) * norm.pdf(d1) * math.sqrt(T)


def theta(S, K, r, q, sigma, T, kind='call'):
    """Per year — divide by 365 for per-calendar-day."""
    d1, d2 = _d1d2(S, K, r, q, sigma, T)
    term1 = -S * math.exp(-q * T) * norm.pdf(d1) * sigma / (2 * math.sqrt(T))
    if kind == 'call':
        term2 = (-r * K * math.exp(-r * T) * norm.cdf(d2)
                 + q * S * math.exp(-q * T) * norm.cdf(d1))
    else:
        term2 = (r * K * math.exp(-r * T) * norm.cdf(-d2)
                 - q * S * math.exp(-q * T) * norm.cdf(-d1))
    return term1 + term2


def rho(S, K, r, q, sigma, T, kind='call'):
    _, d2 = _d1d2(S, K, r, q, sigma, T)
    if kind == 'call':
        return K * T * math.exp(-r * T) * norm.cdf(d2)
    return -K * T * math.exp(-r * T) * norm.cdf(-d2)


def taylor_pnl(dS, dt, dsigma, delta_val, gamma_val, theta_val, vega_val):
    """First/second-order P&L attribution."""
    return (delta_val * dS
            + theta_val * dt
            + 0.5 * gamma_val * dS**2
            + vega_val * dsigma)


def delta_gamma_hedge(port_delta, port_gamma, opt_delta, opt_gamma):
    """Return (option_qty w, underlying_qty h) for delta-gamma neutrality."""
    w = -port_gamma / opt_gamma
    h = -(port_delta + w * opt_delta)
    return w, h


def delta_vega_gamma_hedge(port_delta, port_gamma, port_vega,
                           g1, v1, d1_opt, g2, v2, d2_opt):
    """Two-option hedge for simultaneous gamma and vega neutrality."""
    A = np.array([[g1, g2], [v1, v2]])
    b = np.array([-port_gamma, -port_vega])
    w1, w2 = np.linalg.solve(A, b)
    h = -(port_delta + w1 * d1_opt + w2 * d2_opt)
    return w1, w2, h


# Verification: BSM PDE identity for ATM 1Y call
S, K, r, q, sigma, T = 100, 100, 0.05, 0.02, 0.20, 1.0
from scipy.stats import norm as _norm
d1v, d2v = _d1d2(S, K, r, q, sigma, T)
price = (S * math.exp(-q * T) * _norm.cdf(d1v)
         - K * math.exp(-r * T) * _norm.cdf(d2v))
lhs = (theta(S, K, r, q, sigma, T)
       + (r - q) * S * delta(S, K, r, q, sigma, T)
       + 0.5 * sigma**2 * S**2 * gamma(S, K, r, q, sigma, T))
print(f"PDE check: LHS={lhs:.4f}  r*price={r*price:.4f}")  # should match
```

## デシジョンガイド

**Scale conventions (common source of bugs)**
| Greek | Hull default unit | Per-day theta | Per-1%-vol vega |
|---|---|---|---|
| Θ | per year | ÷ 365 (calendar) or ÷ 252 (trading) | — |
| $\mathcal{V}$ | per 1.0 vol (= 100%) | — | ÷ 100 |
| ρ | per 1.0 (= 100 bps) | — | — |

**Gamma vs Theta trade-off**
- Long options: positive $\Gamma$, negative $\Theta$ (paying time decay for convexity)
- Short options: negative $\Gamma$, positive $\Theta$ (collecting time decay, exposed to large moves)
- Gamma scalping: delta-hedge continuously; P&L ∝ $\tfrac{1}{2}\Gamma(\Delta S)^2 - |\Theta|\Delta t$

**Static vs dynamic hedge**
- Static: set once, no rebalancing; works when delta is stable (deep ITM/OTM forwards)
- Dynamic: rebalance at every $\Delta t$; cost converges to BSM price but adds transaction costs

**When ρ matters**
- Short-dated options: ρ small — rate sensitivity negligible
- Long-dated (2Y+) positions, bonds, or currency swaps: ρ can dominate P&L

**Gamma/vega neutrality requires traded options**
- Underlying (delta=1, gamma=0) cannot change gamma
- Gamma-neutral: add $w_T = -\Gamma_\Pi/\Gamma_T$ units of one traded option, then re-delta-hedge
- Gamma + vega neutral simultaneously: need two distinct traded options (solve 2×2 system)

**Smile context**
- BSM Greeks assume flat vol; real delta should be adjusted for smile (minimum-variance delta, Ch.20)
- Higher-order: vanna ($\partial\Delta/\partial\sigma$) and vomma ($\partial^2 f/\partial\sigma^2$) matter for vol-surface hedging
