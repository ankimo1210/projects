# Topic: Real Options

## 対応章
- Ch.36 Real Options — [chapters/ch36_real_options.md](../chapters/ch36_real_options.md)

## クイック公式

### Static NPV baseline
$$
\text{NPV} = \sum_{t=0}^{T} \frac{CF_t}{(1 + r_\text{adj})^t}
$$
- $CF_t$: incremental cash flow at time $t$; $r_\text{adj}$: CAPM risk-adjusted rate
- Ignores managerial flexibility; option-adjusted NPV is always ≥ static NPV
- See: ch36 §36.1

### Market price of risk
$$
\lambda = \frac{\mu - r}{\sigma}
$$
<!-- Hull eq. (36.1) -->
- $\mu$: expected return on the traded asset that drives project value; $\sigma$: its volatility

### CAPM estimate of $\lambda$
$$
\lambda = \frac{\rho}{\sigma_m}(\mu_m - r)
$$
<!-- Hull eq. (36.2) -->
- $\rho$: instantaneous correlation of project variable with market index
- $\sigma_m$: market index volatility; $\mu_m$: market expected return
- If project variable uncorrelated with market ($\rho = 0$), set $\lambda = 0$

### Risk-neutral project value process
$$
dV = (\mu - \lambda\sigma)V\,dt + \sigma V\,dz \quad \text{under } \mathbb{Q}
$$
- Drift is reduced by risk premium $\lambda\sigma$; discount cash flows at $r$
- See: ch36 §36.2

### Binomial tree parameters
$$
u = e^{\sigma\sqrt{\Delta t}},\quad d = \frac{1}{u},\quad p = \frac{e^{r\Delta t} - d}{u - d}
$$

### Bellman equation (backward DP)
$$
V_t = \max\!\bigl(\text{exercise now},\; e^{-r\Delta t}\,\mathbb{E}[V_{t+1}]\bigr)
$$
- Defer (call): exercise now $= V - K$ (investment cost $K$)
- Abandon (put-like): exercise now $= \text{salvage}$
- Expand: exercise now $= \alpha V - C_\text{expand}$ ($\alpha$ = scale-up factor)
- See: ch36 §36.3–36.5

## 実装スニペット

```python
import math
import numpy as np


def project_npv(cash_flows, r):
    """Static NPV with risk-adjusted discount rate.

    cash_flows : list[float] — CF at t=0, 1, 2, ... (negative = investment)
    r          : risk-adjusted discount rate per period
    """
    return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))


def binomial_real_option_defer(V0, sigma, T, r, K, N):
    """Option to defer investment — American call on project value V.

    V0    : current project value
    sigma : project value volatility (annualised)
    T     : option horizon (years)
    r     : risk-free rate (continuous)
    K     : investment cost (strike)
    N     : number of time steps
    """
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    j = np.arange(N + 1)
    V_T = V0 * (u ** (N - j)) * (d ** j)
    payoff = np.maximum(V_T - K, 0.0)

    for step in range(N - 1, -1, -1):
        j_s = np.arange(step + 1)
        V_step = V0 * (u ** (step - j_s)) * (d ** j_s)
        cont = disc * (p * payoff[:-1] + (1 - p) * payoff[1:])
        immediate = np.maximum(V_step - K, 0.0)
        payoff = np.maximum(cont, immediate)

    return float(payoff[0])


def binomial_real_option_abandon(V0, sigma, T, r, salvage, N):
    """Option to abandon project — American put-like with floor = salvage.

    salvage : liquidation / salvage value (strike equivalent)
    """
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    j = np.arange(N + 1)
    V_T = V0 * (u ** (N - j)) * (d ** j)
    payoff = np.maximum(V_T, salvage)

    for step in range(N - 1, -1, -1):
        cont = disc * (p * payoff[:-1] + (1 - p) * payoff[1:])
        payoff = np.maximum(cont, salvage)

    return float(payoff[0])


# Quick usage
print("Static NPV :", project_npv([-100, 30, 35, 40, 45], r=0.10))
print("Defer option:", binomial_real_option_defer(
    V0=100, sigma=0.30, T=2.0, r=0.05, K=110, N=200))
print("Abandon opt :", binomial_real_option_abandon(
    V0=100, sigma=0.30, T=2.0, r=0.05, salvage=70, N=200))
```

## デシジョンガイド

- **Static NPV vs option-adjusted NPV**: static NPV rejects projects with $\text{NPV} < 0$; option-adjusted NPV may be positive once defer/expand/abandon flexibility is valued — never reject solely on static NPV.
- **Option taxonomy**:
  - Defer → American call (wait to invest; $K$ = investment cost)
  - Abandon → American put-like (salvage value as floor)
  - Expand → American call (additional capacity; $K$ = expansion cost)
  - Contraction → American put (reduced scale; $K$ = PV of saved costs)
  - Switch → American call/put depending on direction
- **Estimating $\sigma$ without a traded underlying**: use (a) historical cash-flow variability, (b) comparable listed companies' asset volatility, or (c) simulation of drivers (price, volume). Sensitivity analysis on $\sigma$ is mandatory.
- **Estimating $\lambda$**: use Hull eq. (36.2) with market beta data; if $\rho \approx 0$ (project cash flows uncorrelated with market), set $\lambda = 0$ — this is common for R&D or weather-driven projects.
- **Multiple real options are non-additive**: value(defer + abandon) ≠ value(defer) + value(abandon); always model simultaneously with explicit state tracking per node (e.g., "expanded/not expanded/abandoned").
- **LSM for path-dependent cases**: when project value depends on history (e.g., staged investment, cumulative output), use Longstaff-Schwartz MC regression (ch27 §27.8) instead of a tree.
- **Do not mix discount rates**: in the risk-neutral approach, drift is corrected by $\lambda\sigma$ and discounting uses $r$; never combine $r_\text{adj}$ discounting with risk-neutral cash flows.
