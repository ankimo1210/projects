# Topic: Numerical Methods

## 対応章
- Ch.21 Basic Numerical Procedures — [chapters/ch21_basic_numerical.md](../chapters/ch21_basic_numerical.md)
- Ch.27 More on Models and Numerical Procedures — [chapters/ch27_more_models_numerical.md](../chapters/ch27_more_models_numerical.md)

## クイック公式

### Trinomial Tree Parameters
$$u = e^{\sigma\sqrt{3\Delta t}}, \quad d = 1/u, \quad m = 1$$
$$p_u = \sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}, \quad p_m = \frac{2}{3}, \quad p_d = \frac{1}{6} - \sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right)$$
- Check $p_u + p_m + p_d = 1$ and all probabilities $\geq 0$
- Equivalent to explicit finite-difference on $Z = \ln S$ grid
- See: ch21 §3

### CRR Binomial Parameters
$$u = e^{\sigma\sqrt{\Delta t}}, \quad d = 1/u, \quad p = \frac{e^{(r-q)\Delta t} - d}{u - d}$$
- See: ch21 §3

### Control Variate (Tree)
$$f^* = f_{\text{Am,tree}} + (f_{\text{Eu,BSM}} - f_{\text{Eu,tree}})$$
- Corrects systematic tree error; use identical tree for both American and European
- See: ch21 §3

### MC Standard Error
$$\text{SE} = \frac{s}{\sqrt{N}}, \qquad \hat{f} = e^{-rT}\frac{1}{N}\sum_{i=1}^N f_T^{(i)}$$
- $s$: sample std dev of discounted payoffs; 95% CI: $\hat{f} \pm 1.96\cdot s/\sqrt{N}$
- See: ch21 §3

### Antithetic Variates
$$\bar{f} = \frac{f(\epsilon) + f(-\epsilon)}{2}$$
- Pairs each $\epsilon$ with $-\epsilon$; roughly halves variance for symmetric payoffs
- See: ch21 §3

### Implicit FD Scheme (uniform $S$ grid)
$$a_j f_{i,j-1} + b_j f_{i,j} + c_j f_{i,j+1} = f_{i+1,j}$$
$$a_j = \tfrac{1}{2}\sigma^2 j^2 \Delta t - \tfrac{1}{2}(r-q)j\,\Delta t, \quad b_j = 1 + \sigma^2 j^2\Delta t + r\,\Delta t, \quad c_j = -\tfrac{1}{2}\sigma^2 j^2 \Delta t - \tfrac{1}{2}(r-q)j\,\Delta t$$
- Tri-diagonal system per time step; unconditionally stable
- See: ch21 §3

### Heston SDE (Stochastic Volatility)
$$dS = (r-q)S\,dt + \sqrt{v}\,S\,dz_1, \qquad dv = \kappa(\theta - v)\,dt + \xi\sqrt{v}\,dz_2, \quad dz_1 dz_2 = \rho\,dt$$
- Feller condition for non-zero variance: $2\kappa\theta > \xi^2$
- See: ch27 §3

### Merton Jump-Diffusion Series
$$c = \sum_{n=0}^{\infty} \frac{e^{-\lambda' T}(\lambda' T)^n}{n!}\, c_{\text{BSM}}(S, K, r_n, \sigma_n, T, q)$$
$$\sigma_n^2 = \sigma^2 + n\delta^2/T, \quad r_n = r - \lambda k + n(\gamma + \delta^2/2)/T, \quad \lambda' = \lambda(1+k)$$
- See: ch27 §3

### Hagan SABR ATM Implied Vol
$$\sigma_B \approx \frac{\sigma_0}{F_0^{1-\beta}}\!\left[1 + \left(\frac{(1-\beta)^2\sigma_0^2}{24F_0^{2-2\beta}} + \frac{\rho\beta\nu\sigma_0}{4F_0^{1-\beta}} + \frac{(2-3\rho^2)\nu^2}{24}\right)T\right]$$
- See: ch27 §3

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm


# 1) Monte Carlo European call with antithetic variates
def mc_european_call(S0, K, r, sigma, T, n_paths=100_000, q=0.0, rng=None):
    """MC European call; returns (price, std_error). Uses antithetic variates."""
    rng = rng or np.random.default_rng(0)
    Z = rng.standard_normal(n_paths // 2)
    Z_both = np.concatenate([Z, -Z])
    ST = S0 * np.exp((r - q - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * Z_both)
    disc_payoff = math.exp(-r * T) * np.maximum(ST - K, 0.0)
    return disc_payoff.mean(), disc_payoff.std(ddof=1) / math.sqrt(len(disc_payoff))


# 2) Implicit finite-difference European put (unconditionally stable)
def implicit_fd_put(S0, K, r, sigma, T, q=0.0, S_max=None, M=200, N=200):
    """Implicit FD on uniform S grid — European put."""
    S_max = S_max or 3.0 * max(S0, K)
    dS = S_max / M
    dt = T / N
    j = np.arange(M + 1, dtype=float)
    V = np.maximum(K - j * dS, 0.0)
    a = 0.5 * dt * (sigma**2 * j**2 - (r - q) * j)
    b = 1.0 + dt * (sigma**2 * j**2 + r)
    c = -0.5 * dt * (sigma**2 * j**2 + (r - q) * j)
    A = np.diag(b[1:-1]) + np.diag(a[2:-1], -1) + np.diag(c[1:-2], 1)
    for _ in range(N):
        rhs = V[1:-1].copy()
        rhs[0] -= a[1] * V[0]
        rhs[-1] -= c[-2] * V[-1]
        V[1:-1] = np.linalg.solve(A, rhs)
        V[0] = K          # deep ITM boundary
        V[-1] = 0.0       # deep OTM boundary
    return float(np.interp(S0, j * dS, V))


# 3) LSM American put (Longstaff-Schwartz)
def lsm_american_put(S0, K, r, sigma, T, n_steps=50, n_paths=50_000, rng=None):
    """Least-squares MC for American put; polynomial basis degree 2."""
    rng = rng or np.random.default_rng(42)
    dt = T / n_steps
    disc = math.exp(-r * dt)
    Z = rng.standard_normal((n_steps, n_paths))
    lnS = np.full(n_paths, math.log(S0))
    paths = np.empty((n_steps + 1, n_paths))
    paths[0] = S0
    for t in range(n_steps):
        lnS += (r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * Z[t]
        paths[t + 1] = np.exp(lnS)
    cashflow = np.maximum(K - paths[-1], 0.0)
    for t in range(n_steps - 1, 0, -1):
        cashflow *= disc
        itm = paths[t] < K
        if itm.sum() < 5:
            continue
        X = paths[t, itm]
        Y = cashflow[itm]
        A = np.column_stack([np.ones_like(X), X, X**2])
        beta, _, _, _ = np.linalg.lstsq(A, Y, rcond=None)
        continuation = A @ beta
        exercise = (K - X) > continuation
        idx = np.where(itm)[0][exercise]
        cashflow[idx] = K - X[exercise]
    return float(disc * cashflow.mean())


# Verification
if __name__ == '__main__':
    S0, K, r, sigma, T = 100, 100, 0.05, 0.20, 1.0
    price, se = mc_european_call(S0, K, r, sigma, T)
    print(f"MC Euro call:   {price:.4f}  SE={se:.5f}")
    print(f"Implicit FD put:{implicit_fd_put(S0, K, r, sigma, T):.4f}")
    print(f"LSM Amer put:   {lsm_american_put(S0, K, r, sigma, T):.4f}")
```

## デシジョンガイド

**Method selection by problem type**
| Problem type | Best method |
|---|---|
| European, path-independent | Closed form (BSM/Black-76) |
| American / Bermudan, 1D | Binomial or trinomial tree; or implicit FD |
| Path-dependent (Asian, lookback) | Monte Carlo |
| American + path-dependent | LSM (Longstaff-Schwartz) |
| Multi-asset, dim ≤ 3 | FD (sparse grid) |
| Multi-asset, dim ≥ 4 | Monte Carlo |
| Barrier options | Tree with nodes on barrier; or FD |

**Variance reduction priority**
1. Antithetic variates: free, always apply first
2. Control variate (analytic European price): apply when closed form exists
3. Quasi-random sequences (Sobol): error $O((\log N)^d/N)$ vs $O(N^{-1/2})$ — effective for dim ≤ 10
4. Importance sampling: useful for deep OTM paths

**Finite-difference stability rules**
- Explicit FD / trinomial: conditionally stable; use $\Delta Z = \sigma\sqrt{3\Delta t}$ on $Z=\ln S$ grid to avoid negative probabilities
- Implicit FD: unconditionally stable; preferred for American options
- Crank-Nicolson: 2nd-order accurate, unconditionally stable; but oscillates near payoff discontinuities → use Rannacher startup (first 2 steps implicit only)

**Stochastic-vol model choice**
| Model | Smile fit | Complexity | Use case |
|---|---|---|---|
| Heston | Good, semi-analytic | Medium | Equity, FX |
| SABR | Excellent for rates | Medium | IR caps/swaptions (Ch.29) |
| Merton JD | Heavy tails, skew | Low (series) | Equity crash risk |
| Local vol (Dupire) | Perfect fit | High (numerical $\partial^2 c/\partial K^2$) | Barrier/exotic pricing |

- LSM basis: degree-2 polynomial $\{1, S, S^2\}$ is usually sufficient; never exceed degree 3 (overfitting)
- Merton series: truncate at $n=40$; verify convergence by checking $n=20$ vs $n=40$
- SABR Hagan approximation: fails for long maturity and deep OTM; switch to Normal-SABR for negative rates
