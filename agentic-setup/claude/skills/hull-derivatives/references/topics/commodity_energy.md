# Topic: Commodity and Energy Derivatives

## 対応章
- Ch.35 Energy and Commodity Derivatives — [chapters/ch35_commodity_energy.md](../chapters/ch35_commodity_energy.md)

## クイック公式

### Cost-of-carry forward (storable commodity)
$$
F_0 = S_0\,e^{(r + u - y)\,T}
$$
- $S_0$: current spot price; $r$: risk-free rate (continuous); $u$: storage cost rate; $y$: convenience yield; $T$: maturity
- $y > r + u$ → backwardation ($F_0 < S_0$); $y < r + u$ → contango
- See: ch35 §3 / ch05 §5.X

### Non-storable commodity (electricity) forward
$$
F_T = \hat{E}[S_T]
$$
- Cost-of-carry argument fails; futures price equals risk-neutral expected spot
- See: ch35 §35.4

### Simple risk-neutral process (time-dependent drift)
$$
\frac{dS}{S} = \mu(t)\,dt + \sigma\,dz, \qquad \mu(t) = \frac{\partial}{\partial t}[\ln F(t)]
$$
- $\mu(t)$ back-solved from observed futures curve
- See: ch35 eq. (35.1)

### Schwartz Model 1 — mean-reverting log-price
$$
d\ln S = [\theta(t) - a\ln S]\,dt + \sigma\,dz
$$
- $a$: mean-reversion speed; $\theta(t)$: time-dependent level fitted to futures curve (absorbs seasonality); $\sigma$: volatility
- Long-maturity vol decays as $\sigma_{\text{fwd}}(T) \approx \sigma e^{-aT}$
- See: ch35 eq. (35.2)

### Jump-diffusion extension (electricity / gas)
$$
d\ln S = [\theta(t) - a\ln S]\,dt + \sigma\,dz + dp
$$
- $dp$: Poisson jump process (Merton structure)
- See: ch35 §35.4

### HDD / CDD definitions (threshold 65°F)
$$
\mathrm{HDD} = \max(65 - A,\;0), \qquad \mathrm{CDD} = \max(A - 65,\;0)
$$
- $A$: daily average temperature (°F) = (high + low) / 2
- Monthly index = sum of daily values; CME standard contract: $\$20 \times$ monthly HDD (CDD)
- See: ch35 §35.5

### Weather option valuation (historical / burn analysis)
$$
V_0 = e^{-rT}\,\hat{E}[\mathrm{payoff}], \qquad \mathrm{payoff} = \omega\,\max(\mathrm{HDD}_\mathrm{cum} - K,\;0)
$$
- No systematic risk → real-world probabilities = risk-neutral; discount at $r$
- See: ch35 §35.7

## 実装スニペット

```python
import math
import numpy as np


def commodity_forward(S0, r, storage, convenience_yield, T):
    """Cost-of-carry forward for storable commodity.
    F0 = S0 * exp((r + u - y) * T)
    """
    return S0 * math.exp((r + storage - convenience_yield) * T)


def schwartz1_simulate(S0, theta, a, sigma, T, n_steps, n_paths, rng=None):
    """One-factor mean-reverting log-spot (Schwartz Model 1).

    theta : float or array of length n_steps — long-run log-price level
    a     : mean-reversion speed
    """
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    x = np.full(n_paths, math.log(S0))
    theta_arr = np.full(n_steps, theta) if np.isscalar(theta) else np.asarray(theta)
    for i in range(n_steps):
        Z = rng.standard_normal(n_paths)
        x = x + a * (theta_arr[i] - x) * dt + sigma * math.sqrt(dt) * Z
    return np.exp(x)


def hdd_cdd_payoff(daily_temps_F, threshold=65, contract_size=20, max_payoff=None):
    """Monthly HDD/CDD totals and contract payoff.

    daily_temps_F : daily average temperatures in Fahrenheit
    contract_size : $/HDD or $/CDD per index point (CME default 20)
    max_payoff    : optional payment cap
    """
    arr = np.asarray(daily_temps_F, dtype=float)
    hdd = np.maximum(threshold - arr, 0).sum()
    cdd = np.maximum(arr - threshold, 0).sum()
    hdd_pay = min(hdd * contract_size, max_payoff) if max_payoff else hdd * contract_size
    cdd_pay = min(cdd * contract_size, max_payoff) if max_payoff else cdd * contract_size
    return dict(hdd=float(hdd), cdd=float(cdd),
                hdd_payoff=float(hdd_pay), cdd_payoff=float(cdd_pay))


# Quick usage
S_T = schwartz1_simulate(S0=50, theta=math.log(60), a=0.5, sigma=0.30,
                          T=1.0, n_steps=252, n_paths=20_000)
print("E[S_T]:", S_T.mean().round(2),
      "F0_carry:", commodity_forward(50, 0.05, 0.02, 0.0, 1.0))
print("Weather:", hdd_cdd_payoff([40, 35, 50, 60, 70, 75]))
```

## デシジョンガイド

- **Storable vs non-storable**: cost-of-carry ($F_0 = S_0 e^{(r+u-y)T}$) applies only to storable commodities (oil, gas in storage, agricultural). For electricity, use $F_T = \hat{E}[S_T]$ — arbitrage cannot be constructed.
- **Seasonality required for energy**: calibrate $\theta(t)$ to the observed futures curve; deseasonalize → interpolate → reseasonalize to keep tree/MC consistent with market prices.
- **Mean reversion essential for term-vol structure**: Schwartz-1 produces realistic term-structure of volatility ($\sigma_\text{fwd} \approx \sigma e^{-aT}$); flat-vol BSM overprices long-dated commodity options.
- **Jumps needed for electricity/gas**: spikes during peak demand cannot be captured by diffusion alone; add Poisson process $dp$ fitted to historical spike frequency and size.
- **Weather payoffs — non-tradable underlying**: no replication possible; use historical burn analysis (30-50 years of daily temps) and discount expected payoff at $r$ (no risk premium for temperature risk).
- **Negative spot prices (April 2020 WTI)**: lognormal assumption breaks; consider normal or shifted-lognormal processes, or add a lower-bound reflection.
- **Backwardation ≠ bearish**: high convenience yield signals physical tightness (low inventory), not market pessimism; do not infer direction from curve shape alone.
- **Multiple hedge variables**: energy producers face both price risk and weather risk; run regression $Y = a + bP + cT + \varepsilon$ and hedge $-b$ with energy futures, $-c$ with weather futures independently.
