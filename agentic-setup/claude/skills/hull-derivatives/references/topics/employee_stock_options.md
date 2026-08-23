# Topic: Employee Stock Options

## 対応章
- Ch.16 Employee Stock Options — [chapters/ch16_employee_stock_options.md](../chapters/ch16_employee_stock_options.md)

## クイック公式

### BSM with Shortened Time (Expected-Life Approximation)
$$V_{\text{ESO}} = \text{BSM}(S_0, K, r, \sigma, q, T_{\text{exp}})$$
- $T_{\text{exp}}$: expected life estimated from historical exercise/forfeiture data, NOT contract maturity
- $r$: zero-coupon risk-free rate matching $T_{\text{exp}}$
- $\sigma$: long-run historical volatility
- See: ch16 §3

### Dilution Adjustment
$$V_{\text{ESO}}^{\text{diluted}} = \frac{N}{N+M} \cdot V_{\text{BSM}}$$
- $N$: shares currently outstanding; $M$: new shares issued on exercise
- Apply only for surprise grants not already priced in by market
- See: ch16 §3

### Binomial Node with Exit Rate $\lambda$
$$V_{\text{node}} = p_{\text{ex}}(S - K) + (1 - p_{\text{ex}})\!\left[(1-\lambda)\,e^{-r\Delta t}\,\mathbb{E}[V_{\text{next}}] + \lambda\max(S-K,0)\right]$$
- $\lambda$: per-period employee exit probability
- $p_{\text{ex}}$: voluntary exercise probability (function of $S/K$ and remaining life)
- See: ch16 §3

### Hull-White Exercise-Multiple Rule
$$\text{Exercise if } S \geq M \cdot K \text{ and option is vested}$$
- $M$: exercise multiple — estimated as average $S/K$ at exercise from historical data
- Exclude forced exercises (maturity, termination) when estimating $M$
- See: ch16 §3

## 実装スニペット

```python
import math
from scipy.stats import norm


def eso_bsm_shortened(
    S: float,
    K: float,
    r: float,
    sigma: float,
    expected_life: float,
    q: float = 0.0,
    N_shares: int = 0,
    M_new: int = 0,
) -> float:
    """Dilution-adjusted ESO value via BSM with shortened time-to-exercise.

    Parameters
    ----------
    S            : stock price (use S0 - PV(div) for discrete dividends, or pass q)
    K            : strike price
    r            : risk-free rate matching expected_life
    sigma        : annualised historical volatility
    expected_life: average time to exercise/expiry (years) — NOT contract maturity
    q            : continuous dividend yield
    N_shares     : shares outstanding (0 = skip dilution adjustment)
    M_new        : new shares issued on exercise (0 = skip dilution adjustment)
    """
    T = expected_life
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    value = (S * math.exp(-q * T) * norm.cdf(d1)
             - K * math.exp(-r * T) * norm.cdf(d2))
    if M_new > 0 and N_shares > 0:
        value *= N_shares / (N_shares + M_new)
    return value


def eso_binomial_exit(
    S: float,
    K: float,
    r: float,
    sigma: float,
    T: float,
    exit_rate: float,      # annual exit probability
    exercise_multiple: float,  # Hull-White M
    vesting_years: float = 0.0,
    N: int = 100,
) -> float:
    """Binomial ESO with Hull-White exercise-multiple and employee exit rate.

    At each vested node: exercise if S >= M*K; exit (forfeiture/exercise) at rate lambda.
    """
    dt = T / N
    lam = 1.0 - (1.0 - exit_rate) ** dt   # per-step exit probability (approx)
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    disc = math.exp(-r * dt)
    pu = (math.exp(r * dt) - d) / (u - d)
    pd = 1.0 - pu

    vesting_step = int(vesting_years / dt)

    # Terminal stock prices
    ST = [S * (u ** (N - 2 * j)) for j in range(N + 1)]
    V = [max(s - K, 0.0) for s in ST]

    for step in range(N - 1, -1, -1):
        S_node = [S * (u ** (step - 2 * j)) for j in range(step + 1)]
        V_new = []
        for j in range(step + 1):
            cont = disc * (pu * V[j] + pd * V[j + 1])
            intrinsic = max(S_node[j] - K, 0.0)
            if step >= vesting_step and S_node[j] >= exercise_multiple * K:
                # Hull-White: exercise immediately
                node_val = intrinsic
            else:
                # Exit: if ITM exercise, else forfeit
                node_val = (1.0 - lam) * cont + lam * intrinsic
            V_new.append(node_val)
        V = V_new

    return V[0]


# Example 16.1 (Hull p. 376): S=26 (adj), K=30, r=5%, sigma=25%, T_exp=4.5yr
val = eso_bsm_shortened(S=26, K=30, r=0.05, sigma=0.25, expected_life=4.5)
print(f"ESO BSM shortened: ${val:.2f}")  # expect ~$6.31
```

## デシジョンガイド

**Which valuation method?**
| Method | When to use |
|---|---|
| BSM shortened-T | Quick FAS 123R / IFRS 2 compliance; widely accepted; least computation |
| Binomial with exit rate | More accurate when exit patterns are complex; required if exercise multiple varies by employee group |
| Hull-White exercise multiple | When historical $M$ data is available; most theoretically grounded |

- FAS 123R / IFRS 2: both BSM-shortened and binomial methods are acceptable; disclose methodology
- Dilution adjustment: apply only if grant is not yet priced in (e.g., surprise announcement)
- If $T_{\text{exp}}$ data is scarce, use SEC simplified method: $T_{\text{exp}} = (T_{\text{vesting}} + T_{\text{maturity}}) / 2$
- Backdating red flags: if grant date always falls just before large price runups, audit grant-date selection
- RSU vs ESO: RSUs share downside; ESOs have asymmetric payoff → RSUs reduce excessive risk-taking incentive
- Repricing after stock decline destroys incentive alignment; if repricing is possible, option value is higher than naive BSM
