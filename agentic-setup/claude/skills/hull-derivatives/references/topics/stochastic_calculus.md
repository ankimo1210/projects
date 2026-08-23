# Topic: Stochastic Calculus

## 対応章
- Ch.14 Wiener Processes and Itô's Lemma — [chapters/ch14_wiener_ito.md](../chapters/ch14_wiener_ito.md)
- Ch.28 Martingales and Measures — [chapters/ch28_martingales_measures.md](../chapters/ch28_martingales_measures.md)

## クイック公式

### Wiener Increment
$$\Delta z = \epsilon\sqrt{\Delta t}, \quad \epsilon \sim N(0,1)$$
$$E[\Delta z] = 0, \quad \mathrm{Var}[\Delta z] = \Delta t$$
- Over period $T$: $z(T) - z(0) \sim N(0, T)$
- See: ch14 §3

### Generalized Wiener Process
$$dx = a\,dt + b\,dz$$
- Drift $a$ (expected change per unit time), diffusion $b$ (std dev per $\sqrt{\text{time}}$)
- Over $T$: $x(T) - x(0) \sim N(aT,\, b^2 T)$
- See: ch14 §3

### Geometric Brownian Motion (GBM)
$$dS = \mu S\,dt + \sigma S\,dz \quad \Longleftrightarrow \quad \frac{dS}{S} = \mu\,dt + \sigma\,dz$$
- $\mu$: expected return (use $r$ or $r-q$ in risk-neutral world); $\sigma$: volatility
- See: ch14 §3

### Itô's Lemma
For $G(x,t)$ where $dx = a(x,t)\,dt + b(x,t)\,dz$:
$$dG = \left(\frac{\partial G}{\partial x}\,a + \frac{\partial G}{\partial t} + \frac{1}{2}\frac{\partial^2 G}{\partial x^2}\,b^2\right)dt + \frac{\partial G}{\partial x}\,b\,dz$$
- Extra $\frac{1}{2}G_{xx}b^2$ term vs. ordinary calculus: $(\Delta x)^2 \approx b^2\,\Delta t$ (not zero)
- See: ch14 §3

### Log-Price under GBM
$$d(\ln S) = \left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma\,dz$$
$$\ln S_T \sim N\!\left(\ln S_0 + \left(\mu - \frac{\sigma^2}{2}\right)T,\; \sigma^2 T\right)$$
- $\mu$ = expected return; $\mu - \sigma^2/2$ = expected log-return (lower by variance drag)
- See: ch14 §3

### Moments of $S_T$
$$E[S_T] = S_0 e^{\mu T}, \quad \mathrm{Var}[S_T] = S_0^2 e^{2\mu T}(e^{\sigma^2 T} - 1)$$
- See: ch14 §3

### Girsanov: Measure Change and Drift Shift
$$dz^Q = dz^P + \lambda\,dt \quad \Longleftrightarrow \quad dz^P = dz^Q - \lambda\,dt$$
- $\lambda = (\mu - r)/\sigma$: market price of risk
- Measure change shifts drift; volatility $\sigma$ is invariant across measures
- See: ch28 §3

### Equivalent Martingale Measure Result (Numeraire $g$)
$$f_0 = g_0\,E_g\!\left[\frac{f_T}{g_T}\right]$$
$$d\!\left(\frac{f}{g}\right) = (\sigma_f - \sigma_g)\frac{f}{g}\,dz \quad \text{(zero drift → martingale)}$$
- See: ch28 §3

### Key Numeraires and Measures
| Numeraire $g$ | Measure | Key property |
|---|---|---|
| Money-market account $e^{rt}$ | Risk-neutral $\mathbb{Q}$ | $f_0 = e^{-rT}\hat{E}[f_T]$ |
| Zero-coupon bond $P(t,T)$ | $T$-forward $\mathbb{Q}^T$ | $F(t,T) = E_T[S_T]$ |
| Annuity $A(t)$ | Swap measure | $s(t)$ is martingale under swap measure |

### T-Forward Measure Pricing
$$f_0 = P(0,T)\,E_T[f_T]$$
- Caplet resets at $T_i$, pays at $T_{i+1}$: use $P(0,T_{i+1})$ as numeraire → $L(T_i)$ is martingale under $\mathbb{Q}^{T_{i+1}}$
- See: ch28 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


# ── GBM path simulation (exact log-Euler) ────────────────────────────────
def simulate_gbm_paths(S0, mu, sigma, T, n_steps, n_paths, rng=None):
    """Simulate GBM paths using exact log-Euler method.

    Returns array shape (n_paths, n_steps+1); column 0 = S0.
    In risk-neutral world pass mu = r - q.
    """
    rng = rng or np.random.default_rng(42)
    dt = T / n_steps
    Z = rng.standard_normal((n_paths, n_steps))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_paths = np.log(S0) + np.cumsum(log_returns, axis=1)
    paths = np.column_stack([np.full((n_paths, 1), S0), np.exp(log_paths)])
    return paths


def gbm_theory(S0, mu, sigma, T):
    """Theoretical E[S_T] and Var[S_T] under GBM."""
    e_st = S0 * np.exp(mu * T)
    var_st = S0**2 * np.exp(2 * mu * T) * (np.exp(sigma**2 * T) - 1)
    return e_st, var_st


# ── Importance sampling via Girsanov ─────────────────────────────────────
def importance_sample_call(S, K, r, sigma, T, n_paths, mu_shift, rng=None):
    """MC European call with Girsanov drift shift for variance reduction.

    mu_shift: lambda (drift shift in sigma units); set ~(ln(K/S)/sigma/sqrt(T))
              to centre samples near the strike.
    Returns (price_estimate, std_error).
    """
    rng = rng or np.random.default_rng(0)
    Z = rng.standard_normal(n_paths)
    # Shifted drift: (r - sigma^2/2)*T + mu_shift*sigma*sqrt(T)
    drift = (r - 0.5 * sigma**2) * T + mu_shift * sigma * math.sqrt(T)
    ST = S * np.exp(drift + sigma * math.sqrt(T) * Z)
    # Radon-Nikodym likelihood ratio (Girsanov)
    LR = np.exp(-mu_shift * Z - 0.5 * mu_shift**2)
    payoff = np.maximum(ST - K, 0.0) * LR
    disc = math.exp(-r * T)
    price = float(disc * payoff.mean())
    se = float(disc * payoff.std(ddof=1) / math.sqrt(n_paths))
    return price, se


# ── Example: verify lognormal property ───────────────────────────────────
if __name__ == '__main__':
    S0, mu, sigma, T = 100.0, 0.10, 0.20, 1.0
    paths = simulate_gbm_paths(S0, mu, sigma, T, n_steps=252, n_paths=100_000)
    ST = paths[:, -1]
    e_th, v_th = gbm_theory(S0, mu, sigma, T)
    print(f"E[S_T]  sim={ST.mean():.4f}  theory={e_th:.4f}")
    print(f"E[lnS]  sim={np.log(ST).mean():.4f}  "
          f"theory={math.log(S0)+(mu-0.5*sigma**2)*T:.4f}")

    # Importance sampling for deep OTM call
    p_naive, se_naive = importance_sample_call(100, 140, 0.05, 0.20, 1.0, 50_000, 0.0)
    p_is, se_is = importance_sample_call(100, 140, 0.05, 0.20, 1.0, 50_000, 2.0)
    print(f"OTM call naive: {p_naive:.5f} SE={se_naive:.5f}")
    print(f"OTM call IS   : {p_is:.5f}   SE={se_is:.5f}")
```

## デシジョンガイド

**When to use which measure**
| Instrument | Recommended measure | Why |
|---|---|---|
| Equity/FX European option | Risk-neutral $\mathbb{Q}$ | $e^{-rT}\hat{E}[f_T]$ is simplest |
| Caplet (resets $T_i$, pays $T_{i+1}$) | $T_{i+1}$-forward $\mathbb{Q}^{T_{i+1}}$ | Forward LIBOR is martingale |
| Swaption (expiry $T$) | Annuity/swap measure | Forward swap rate is martingale |
| Convexity/timing adjustment | Explicit measure mismatch correction | Ch.30 |

**Itô vs ordinary calculus**
- Always use Itô's lemma for functions of stochastic processes
- The $\frac{1}{2}G_{xx}b^2$ term is critical: omitting it gives $d(\ln S) = \mu\,dt + \sigma\,dz$ instead of the correct $(\mu - \sigma^2/2)\,dt + \sigma\,dz$

**Exact log-Euler vs naive Euler**
- Always use exact method: $\ln S_{t+\Delta t} = \ln S_t + (\mu - \sigma^2/2)\Delta t + \sigma\epsilon\sqrt{\Delta t}$
- Naive Euler ($\Delta S/S = \mu\Delta t + \sigma\epsilon\sqrt{\Delta t}$) accumulates discretization bias especially at large $\Delta t$ or high $\sigma$

**Girsanov / importance sampling**
- Useful for deep OTM options where standard MC wastes paths on zero-payoff outcomes
- Shift drift toward the strike; reweight each path by the Radon-Nikodym derivative $e^{-\lambda Z - \lambda^2 T/2}$
- Measure change does not alter $\sigma$ — only drifts change
