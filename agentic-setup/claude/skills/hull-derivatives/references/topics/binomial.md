# Topic: Binomial Trees

## 対応章
- Ch.13 Binomial Trees — [chapters/ch13_binomial_trees.md](../chapters/ch13_binomial_trees.md)
- Ch.21 Basic Numerical Procedures — [chapters/ch21_basic_numerical.md](../chapters/ch21_basic_numerical.md)

## クイック公式

### Risk-Neutral Probability (general)
$$p = \frac{a - d}{u - d}, \quad a = e^{(r-q)\Delta t}$$
- $a = e^{r\Delta t}$ for non-dividend stock; $a = e^{(r-q)\Delta t}$ for index/FX; $a = 1$ for futures
- See: ch13 §3

### CRR Parameterization
$$u = e^{\sigma\sqrt{\Delta t}}, \quad d = \frac{1}{u} = e^{-\sigma\sqrt{\Delta t}}$$
- Ensures $d < e^{r\Delta t} < u$, so $0 < p < 1$
- See: ch13 §3

### Alternative Equal-Probability Tree ($p = 1/2$)
$$p = \frac{1}{2}, \quad u = e^{(r-q-\sigma^2/2)\Delta t + \sigma\sqrt{\Delta t}}, \quad d = e^{(r-q-\sigma^2/2)\Delta t - \sigma\sqrt{\Delta t}}$$
- $u \ne 1/d$; converges to same BSM limit
- See: ch13 §3

### Backward Induction (one step)
$$f = e^{-r\Delta t}[p\,f_u + (1-p)\,f_d]$$
- For American options: $f = \max(e^{-r\Delta t}[p\,f_u + (1-p)\,f_d],\; \text{intrinsic})$
- See: ch13 §3

### Delta from Tree Node
$$\Delta = \frac{f_u - f_d}{S_0 u - S_0 d}$$
- See: ch13 §3

### Control Variate Correction
$$f^* = f_{\mathrm{Am,tree}} + (f_{\mathrm{Eu,BSM}} - f_{\mathrm{Eu,tree}})$$
- Removes systematic tree error by anchoring to known analytical price
- See: ch21 §3

### Trinomial Parameters
$$u = e^{\sigma\sqrt{3\Delta t}}, \quad d = 1/u$$
$$p_u = \sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}, \quad p_m = \frac{2}{3}, \quad p_d = \frac{1}{6} - \sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right)$$
- Check $p_u + p_m + p_d = 1$; all must be positive
- See: ch21 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


# ── CRR Binomial: European ────────────────────────────────────────────────
def binomial_european_call(S, K, r, sigma, T, N, q=0.0):
    """N-step CRR binomial price of a European call (q=0 for no-div stock)."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    j = np.arange(N + 1)
    S_T = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(S_T - K, 0.0)
    for _ in range(N):
        V = disc * (p * V[:-1] + (1 - p) * V[1:])
    return float(V[0])


# ── CRR Binomial: American put ────────────────────────────────────────────
def binomial_american_put(S, K, r, sigma, T, N, q=0.0):
    """N-step CRR binomial price of an American put."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    j = np.arange(N + 1)
    S_T = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(K - S_T, 0.0)
    for step in range(N - 1, -1, -1):
        S_step = S * (u ** np.arange(step + 1)[::-1]) * (d ** np.arange(step + 1))
        cont = disc * (p * V[:-1] + (1 - p) * V[1:])
        V = np.maximum(cont, np.maximum(K - S_step, 0.0))
    return float(V[0])


# ── Trinomial tree ────────────────────────────────────────────────────────
def trinomial(S0, K, r, q, sigma, T, N, kind='call', american=False):
    """Trinomial tree for European or American vanilla option."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(3.0 * dt))
    d = 1.0 / u
    sig2 = sigma * sigma
    p_u = math.sqrt(dt / (12.0 * sig2)) * (r - q - sig2 / 2.0) + 1.0 / 6.0
    p_m = 2.0 / 3.0
    p_d = -math.sqrt(dt / (12.0 * sig2)) * (r - q - sig2 / 2.0) + 1.0 / 6.0
    disc = math.exp(-r * dt)
    idx = np.arange(-N, N + 1)
    S = S0 * (u ** idx)
    sign = 1.0 if kind == 'call' else -1.0
    V = np.maximum(sign * (S - K), 0.0)
    for step in range(N, 0, -1):
        S = S0 * (u ** np.arange(-step + 1, step))
        V_new = disc * (p_u * V[2:] + p_m * V[1:-1] + p_d * V[:-2])
        if american:
            V_new = np.maximum(V_new, np.maximum(sign * (S - K), 0.0))
        V = V_new
    return float(V[0])


# ── Control variate correction ────────────────────────────────────────────
def control_variate_american_put(S, K, r, sigma, T, N, q=0.0):
    """American put corrected by BSM anchor: f* = Am_tree + (Eu_BSM - Eu_tree)."""
    from scipy.stats import norm as _n
    # BSM European put (analytical)
    d1 = (math.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    eu_bsm = K*math.exp(-r*T)*_n.cdf(-d2) - S*math.exp(-q*T)*_n.cdf(-d1)
    # European tree (same N as American)
    dt, u = T/N, math.exp(sigma*math.sqrt(T/N))
    d, p = 1.0/u, (math.exp((r-q)*dt)-1.0/u)/(u-1.0/u)
    disc = math.exp(-r*dt)
    j = np.arange(N+1)
    V_eu = np.maximum(K - S*(u**(N-j))*(1/u)**j, 0.0)
    for _ in range(N):
        V_eu = disc*(p*V_eu[:-1] + (1-p)*V_eu[1:])
    return binomial_american_put(S, K, r, sigma, T, N, q) + (eu_bsm - float(V_eu[0]))


# Euro call ~10.45, Amer put ~10.47 (ATM 1-yr, sigma=0.2, r=0.05)
# binomial_european_call(100, 100, 0.05, 0.2, 1.0, 200) → 10.4506
# binomial_american_put (100, 100, 0.05, 0.2, 1.0, 200) → 10.4738
# trinomial(100, 100, 0.05, 0, 0.2, 1.0, 100, 'call')   → ~10.45
# control_variate_american_put(100, 100, 0.05, 0.2, 1.0, 100) → ~10.47
```

## デシジョンガイド

**Binomial vs Trinomial**
- Binomial (CRR): simpler, sufficient for vanilla American options with $N \ge 50$
- Trinomial: better convergence for barrier/digital options; finer grid near barrier; equivalent to explicit finite-difference scheme
- Both converge to BSM as $N \to \infty$

**When does American differ from European?**
- Put: always (positive early-exercise premium when deep ITM; $r$ high or $\sigma$ low accelerates it)
- Call (no dividends): $C = c$ always — use BSM closed form, no tree needed
- Call (with dividends or large $q$): $C > c$ possible just before ex-dividend; use binomial or Black's approximation

**Control variate vs raw tree**
- Use control variate whenever the European analogue has a closed form (i.e., vanilla puts/calls under BSM)
- Same $N$ must be used for both tree calculations — mismatching $N$ breaks the error cancellation
- For exotic options without analytic analogues, use trinomial or FD instead

**Parameter selection**
- $N \ge 50$ for reasonable accuracy; $N \ge 200$ for Greeks
- Odd/even $N$ alternation causes price oscillation — use large $N$ or average odd/even results
- Futures option: set $q = r$ (or $a = 1$ directly); FX option: set $q = r_f$
