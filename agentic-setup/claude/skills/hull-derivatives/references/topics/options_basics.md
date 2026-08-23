# Topic: Options Basics

## 対応章
- Ch.10 Mechanics of Options Markets — [chapters/ch10_options_mechanics.md](../chapters/ch10_options_mechanics.md)
- Ch.11 Properties of Stock Options — [chapters/ch11_option_properties.md](../chapters/ch11_option_properties.md)
- Ch.12 Trading Strategies Involving Options — [chapters/ch12_option_strategies.md](../chapters/ch12_option_strategies.md)
- Ch.17 Options on Stock Indices and Currencies — [chapters/ch17_index_currency_options.md](../chapters/ch17_index_currency_options.md)
- Ch.18 Futures Options and Black's Model — [chapters/ch18_futures_options_black.md](../chapters/ch18_futures_options_black.md)

## クイック公式

### Payoff (call / put)
$$\text{Long call} = \max(S_T - K,\; 0)$$
$$\text{Long put}  = \max(K - S_T,\; 0)$$
- $S_T$: terminal stock price; $K$: strike
- See: ch10 §3

### Put-Call Parity (European, no dividends)
$$c + Ke^{-rT} = p + S_0$$
- See: ch11 §3

### Put-Call Parity (continuous yield $q$)
$$c + Ke^{-rT} = p + S_0 e^{-qT}$$
- Applies to index options ($q$ = index yield) and FX options ($q = r_f$)
- See: ch11 §3, ch17 §3

### Put-Call Parity (discrete dividends $D$)
$$c + D + Ke^{-rT} = p + S_0$$
- $D$ = PV of dividends during option life
- See: ch11 §3

### European Option Bounds (no dividends)
$$c \ge \max(S_0 - Ke^{-rT},\; 0), \quad p \ge \max(Ke^{-rT} - S_0,\; 0)$$
- See: ch11 §3

### BSM with Continuous Yield (Merton)
$$c = S_0 e^{-qT} N(d_1) - K e^{-rT} N(d_2)$$
$$p = K e^{-rT} N(-d_2) - S_0 e^{-qT} N(-d_1)$$
$$d_1 = \frac{\ln(S_0/K) + (r - q + \sigma^2/2)\,T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$
- Set $q=0$ for non-dividend stock; $q=r_f$ for FX (Garman-Kohlhagen)
- See: ch17 §3

### Black's Model (Futures Options)
$$c = e^{-rT}[F_0 N(d_1) - K N(d_2)]$$
$$d_1 = \frac{\ln(F_0/K) + \sigma^2 T/2}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$
- Equivalent to BSM with $q = r$ (futures = zero-cost asset)
- See: ch18 §3

### Strategy Payoffs

**Bull call spread** ($K_1 < K_2$):
$$\text{Payoff} = \begin{cases} 0 & S_T \le K_1 \\ S_T - K_1 & K_1 < S_T < K_2 \\ K_2 - K_1 & S_T \ge K_2 \end{cases}$$

**Straddle** (long call + long put, same $K$):
$$\text{Payoff} = |S_T - K|$$

**Strangle** ($K_1$ put, $K_2 > K_1$ call):
$$\text{Payoff} = \max(K_1 - S_T, 0) + \max(S_T - K_2, 0)$$

**Butterfly** ($K_1 < K_2 < K_3$, $K_2 = (K_1+K_3)/2$):
$$\text{Payoff} = \max(S_T-K_1,0) - 2\max(S_T-K_2,0) + \max(S_T-K_3,0)$$
- See: ch12 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


# ── Core BSM with continuous yield (index, FX, stock with q) ──────────────
def bs_yield(S, K, r, q, sigma, T, kind='call'):
    """BSM with continuous yield. Use q=r_f for Garman-Kohlhagen (FX)."""
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind == 'call':
        return S * math.exp(-q * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    return K * math.exp(-r * T) * norm.cdf(-d2) - S * math.exp(-q * T) * norm.cdf(-d1)


def fx_option(S0, K, r_dom, r_for, sigma, T, kind='call'):
    """Garman-Kohlhagen: FX option with foreign rate as continuous yield."""
    return bs_yield(S0, K, r_dom, r_for, sigma, T, kind)


def black_futures(F, K, r, sigma, T, kind='call'):
    """Black-76: European option on futures."""
    d1 = (math.log(F / K) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind == 'call':
        return math.exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d2))
    return math.exp(-r * T) * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def put_call_parity_check(c, p, S, K, r, T, q=0.0):
    """Returns LHS - RHS of c + K*e^{-rT} = p + S*e^{-qT}. Zero = parity holds."""
    return (c + K * math.exp(-r * T)) - (p + S * math.exp(-q * T))


# ── Strategy payoffs (vectorized) ─────────────────────────────────────────
def straddle(S: np.ndarray, K: float) -> np.ndarray:
    return np.abs(S - K)

def strangle(S: np.ndarray, K1: float, K2: float) -> np.ndarray:
    """K1 = put strike (low), K2 = call strike (high)."""
    return np.maximum(K1 - S, 0) + np.maximum(S - K2, 0)

def butterfly(S: np.ndarray, K1: float, K2: float, K3: float) -> np.ndarray:
    """Long butterfly. K2 = (K1+K3)/2."""
    return (np.maximum(S - K1, 0)
            - 2 * np.maximum(S - K2, 0)
            + np.maximum(S - K3, 0))

def bull_call_spread(S: np.ndarray, K1: float, K2: float) -> np.ndarray:
    return np.clip(S - K1, 0, K2 - K1)
```

## デシジョンガイド

**American vs European early exercise**
- No-dividend stock call: $C = c$ (never early-exercise; time value + insurance > intrinsic)
- No-dividend stock put: $P > p$; early exercise rational if deep ITM ($r$ high, $\sigma$ low)
- With dividends: call early exercise only just before ex-dividend date; use Black's approximation

**Which pricing form to use**
| Underlying | Formula | Key substitution |
|---|---|---|
| Non-dividend stock | BSM ($q=0$) | — |
| Continuous-yield stock / index | BSM with $q$ | $q$ = dividend yield |
| Foreign currency | Garman-Kohlhagen | $q = r_f$ |
| Futures contract | Black-76 | $q = r$ (futures drift = 0) |

**Strategy selection by view**
| Market view | Vol view | Strategy |
|---|---|---|
| Bullish | Neutral | Bull call spread (limited risk/reward) |
| Bearish | Neutral | Bear put spread |
| Neutral | Low | Butterfly (long), calendar spread |
| Directional uncertainty | High | Straddle (simpler), strangle (cheaper) |
| Bearish tilt + vol | High | Strip (1 call + 2 puts) |
| Bullish tilt + vol | High | Strap (2 calls + 1 put) |

**Common pitfalls**
- Box spread valid only with European options (American box spread has early-exercise risk)
- Put-call parity is model-free but European-only; American options satisfy inequality only
- Straddle near events: IV usually already elevated, so expected return may be negative
