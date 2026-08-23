# Topic: Volatility Smile and Surface

## 対応章
- Ch.20 Volatility Smiles and Volatility Surfaces — [chapters/ch20_vol_smile.md](../chapters/ch20_vol_smile.md)

## クイック公式

### Put-Call Parity (model-independent)
$$p + S_0 e^{-qT} = c + K e^{-rT}$$
- Consequence: call and put implied vols are **equal** at the same $(K, T)$
- See: ch20 §3

### BSM Price Error Equality
$$p_{\text{BS}} - p_{\text{mkt}} = c_{\text{BS}} - c_{\text{mkt}}$$
- The BSM mispricing is identical for same-strike call and put
- See: ch20 §3

### Risk Reversal (25Δ)
$$\text{RR}_{25} = \sigma_{25\Delta C} - \sigma_{25\Delta P}$$
- Positive: call wing higher than put wing; equity: large negative (leverage effect)
- See: ch20 §3

### Butterfly Spread (25Δ)
$$\text{BF}_{25} = \tfrac{1}{2}(\sigma_{25\Delta C} + \sigma_{25\Delta P}) - \sigma_{\text{ATM}}$$
- Measures smile curvature (convexity); positive = U-shape wings
- See: ch20 §3

### Breeden-Litzenberger (Risk-Neutral Density)
$$g(K) = e^{rT}\frac{\partial^2 c}{\partial K^2}$$
- Finite-difference approximation (spacing $\delta$):
$$g(K) \approx e^{rT}\frac{c(K-\delta) - 2c(K) + c(K+\delta)}{\delta^2}$$
- See: ch20 §3

### Volatility Surface
$$\sigma = \sigma(K, T)$$
- Normalized abscissa: $\frac{1}{\sqrt{T}}\ln(K/F_0)$ removes most of the term-structure dependence
- See: ch20 §3

### Minimum Variance Delta
$$\Delta_{\text{MV}} = \Delta_{\text{BSM}} + \mathcal{V}_{\text{BSM}} \frac{\partial E[\sigma_{\text{imp}}]}{\partial S}$$
- For equities: $\partial E[\sigma_{\text{imp}}]/\partial S < 0$ → $\Delta_{\text{MV}} < \Delta_{\text{BSM}}$
- See: ch20 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def bs_call(S, K, r, sigma, T, q=0.0):
    """BSM European call price."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def implied_vol(price, S, K, r, T, q=0.0, kind="call"):
    """Invert BSM to find implied volatility via Brent root-find."""
    if kind == "put":
        # Convert put to call price via put-call parity
        price = price + S * math.exp(-q * T) - K * math.exp(-r * T)
    f = lambda s: bs_call(S, K, r, s, T, q) - price
    return brentq(f, 1e-6, 5.0)


def smile_from_prices(strikes, prices, S, r, T, q=0.0, kind="call"):
    """Recover vol smile by inverting BSM at each strike."""
    return np.array(
        [implied_vol(p, S, K, r, T, q, kind) for K, p in zip(strikes, prices)]
    )


def implied_density_breeden_litzenberger(strikes, call_prices, r, T):
    """Risk-neutral density f(K) = e^{rT} * d^2c/dK^2 via central differences."""
    K = np.asarray(strikes, dtype=float)
    c = np.asarray(call_prices, dtype=float)
    density = np.zeros_like(c)
    dK = np.diff(K)
    for i in range(1, len(K) - 1):
        h = 0.5 * (dK[i - 1] + dK[i])
        density[i] = (c[i + 1] - 2 * c[i] + c[i - 1]) / h**2
    return math.exp(r * T) * density


def check_no_arb_butterfly(strikes, call_prices):
    """Return True if call prices are convex in K (butterfly no-arb)."""
    c = np.asarray(call_prices)
    return bool(np.all(np.diff(c, 2) >= 0))


# Example: equity-style downward skew
S, r, T = 100.0, 0.02, 0.5
strikes = np.linspace(80, 120, 21)
true_vols = 0.20 + 0.10 * (S - strikes) / S   # skew: low K → high vol
prices = np.array([bs_call(S, K, r, sv, T) for K, sv in zip(strikes, true_vols)])
recovered = smile_from_prices(strikes, prices, S, r, T)
print("max abs IV error:", float(np.max(np.abs(recovered - true_vols))))  # ~0.0
density = implied_density_breeden_litzenberger(strikes, prices, r, T)
dK = strikes[1] - strikes[0]
print("density integral:", float(np.sum(density[1:-1]) * dK))  # near 1.0
```

## デシジョンガイド

**Equity vs FX smile shape**
| Market | Smile shape | Primary cause |
|---|---|---|
| Equity | Downward skew (smirk) | Leverage effect; crash-o-phobia post-1987 |
| FX | Symmetric U-shape | Fat tails (jump risk) in both directions |
| Commodity | Varies by contract | Supply shocks, seasonality |

**Sticky-strike vs sticky-delta hedging**
- Sticky-strike: IV at fixed $K$ is constant when $S$ moves → BSM delta used as-is
  - Convenient for quoting; but over-hedges equities (ignores negative $\partial\sigma/\partial S$)
- Sticky-delta: IV at fixed $\Delta$ (moneyness) is constant → delta adjustment needed
  - More realistic for FX; minimum-variance delta lies between the two
- Rule of thumb: use $\Delta_{\text{MV}}$ for equity vanilla hedging; flag with model-risk reserve

**Smile interpolation must preserve no-arb conditions**
1. Butterfly (convexity): $\partial^2 c/\partial K^2 \geq 0$ at every $K$ (density non-negative)
2. Calendar: total variance $\sigma^2(K,T)\cdot T$ non-decreasing in $T$
3. Use SVI or cubic spline on IV; always verify Breeden-Litzenberger density is positive

**When to escalate beyond BSM smile**
| Need | Model |
|---|---|
| Consistent smile dynamics | Local vol (Dupire, Ch.27) |
| Stochastic vol with mean-reversion | Heston (Ch.27) |
| IR derivatives smiles | SABR (Ch.27, Ch.29) |
| Jump skew (equity crash) | Merton JD (Ch.27) |

- For vanilla options: BSM with implied vol is sufficient for pricing; smile matters for exotics
- BSM is a quoting convention, not a model — different strikes need different $\sigma$ inputs
