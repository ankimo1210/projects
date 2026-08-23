# Topic: Credit Risk and Credit Derivatives

## 対応章
- Ch.08 Securitization and the Financial Crisis of 2007-8 — [chapters/ch08_securitization.md](../chapters/ch08_securitization.md)
- Ch.09 XVAs — [chapters/ch09_xvas.md](../chapters/ch09_xvas.md)
- Ch.24 Credit Risk — [chapters/ch24_credit_risk.md](../chapters/ch24_credit_risk.md)
- Ch.25 Credit Derivatives — [chapters/ch25_credit_derivatives.md](../chapters/ch25_credit_derivatives.md)

## クイック公式

### ハザードレートと生存確率
$$S(t) = e^{-\int_0^t \lambda(u)\,du}, \qquad Q(t) = 1 - S(t)$$
- 定数ハザード: $S(t) = e^{-\lambda t}$, $Q(T) = 1 - e^{-\lambda T}$
- See: ch24 eq.(24.1)

### スプレッドからハザードレートの近似
$$\lambda \approx \frac{s}{1-R}$$
- $s$: 連続複利イールドスプレッド、$R$: 回収率（通常 0.40）
- 一次近似；精密解にはクーポン付き債券のブートストラップが必要
- See: ch24 eq.(24.2)

### Merton モデル：株式価値とリスク中立デフォルト確率
$$E_0 = V_0 N(d_1) - De^{-rT} N(d_2), \qquad Q = N(-d_2)$$
$$d_1 = \frac{\ln(V_0/D) + (r+\sigma_V^2/2)T}{\sigma_V\sqrt{T}}, \quad d_2 = d_1 - \sigma_V\sqrt{T}$$
- $V_0$: 企業資産価値、$D$: 債務額（ゼロクーポン）、$\sigma_V$: 資産ボラティリティ
- See: ch24 eq.(24.3)

### KMV 距離 to Default
$$\mathrm{DD} = d_2 = \frac{\ln(V_0/D) + (r-\sigma_V^2/2)T}{\sigma_V\sqrt{T}}$$
- DD が大きいほどデフォルト確率は低い；KMV は $d_2$ を単調変換して実世界 EDF に換算
- See: ch24 §24.6

### CVA（ノー・ウロング・ウェイ・リスク仮定下）
$$\mathrm{CVA} = (1-R)\sum_{i=1}^{N} q_i D_i E_i$$
- $q_i$: 区間 $i$ のデフォルト確率、$D_i$: 割引係数、$E_i$: 期待正エクスポージャー (EPE)
- See: ch09 eq.(9.1), ch24

### CDS パー・スプレッド
$$s = \frac{\text{PV(protection leg)}}{\text{PV(risky annuity)}}, \quad s \approx \lambda(1-R) \text{ (近似)}$$
- 離散実装: protection leg $= (1-R)\sum_i e^{-r t_i}(S_{i-1}-S_i)$、annuity $= \sum_j e^{-r t_j} S(t_j)\Delta t_j$
- See: ch25 §25.2

### ガウスコピュラ因子モデル
$$X_i = \sqrt{\rho}\,M + \sqrt{1-\rho}\,Z_i$$
$$Q_i(T \mid F) = N\!\left(\frac{N^{-1}[Q_i(T)] - \sqrt{\rho}\,F}{\sqrt{1-\rho}}\right)$$
- $M$: 共通因子（市場）、$Z_i$: 個別因子（独立）、$\rho$: コピュラ相関
- See: ch24 eq.(24.7), ch25 eq.(25.5)

### ABS ウォーターフォール損失（簡易）
$$L_{\text{mezz}}^{\text{ABS}} = \frac{\max(L-0.05,\,0)}{0.15}, \quad L_{\text{senior}}^{\text{ABS CDO}} = \frac{\max(L_{\text{mezz}}-0.35,\,0)}{0.65}$$
- エクイティ 5%・メザニン 15%・シニア 80% の ABS、ABS CDO エクイティ 10%・メザニン 25%・シニア 65% の例
- See: ch08 Table 8.1

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq, fsolve


# ── Hazard rate / survival probability ──────────────────────────────────────

def survival_prob(t, hazard):
    """S(t) = exp(-hazard * t) for constant hazard, or piecewise list."""
    if np.isscalar(hazard):
        return math.exp(-hazard * t)
    full = int(t)
    frac = t - full
    total = sum(hazard[:full]) + hazard[min(full, len(hazard)-1)] * frac
    return math.exp(-total)


def default_prob_from_spread(spread, recovery=0.4):
    """Average hazard rate lambda = s / (1 - R).  Hull eq. (24.2).
    Use 1 - exp(-lambda * T) for Q(T).
    """
    return spread / (1.0 - recovery)


# ── Merton model ─────────────────────────────────────────────────────────────

def merton_default_prob(V0, D, r, sigma_V, T):
    """Risk-neutral default probability N(-d2) from Merton model."""
    d2 = (math.log(V0/D) + (r - 0.5*sigma_V**2)*T) / (sigma_V*math.sqrt(T))
    return float(norm.cdf(-d2))


def merton_solve_V_sigmaV(E0, sigma_E, D, r, T):
    """Solve for (V0, sigma_V) given equity market data. Hull §24.6."""
    def equations(x):
        V0, sigma_V = x
        if V0 <= 0 or sigma_V <= 0:
            return [1e10, 1e10]
        d1 = (math.log(V0/D) + (r + 0.5*sigma_V**2)*T) / (sigma_V*math.sqrt(T))
        d2 = d1 - sigma_V*math.sqrt(T)
        eq1 = V0*norm.cdf(d1) - D*math.exp(-r*T)*norm.cdf(d2) - E0
        eq2 = norm.cdf(d1)*sigma_V*V0 - sigma_E*E0
        return [eq1, eq2]
    sol = fsolve(equations, [E0 + D, sigma_E], full_output=False)
    return float(sol[0]), float(sol[1])


# ── CDS par spread ────────────────────────────────────────────────────────────

def cds_par_spread(hazard_curve, tenors, r=0.02, recovery=0.4, n_periods=4):
    """Par CDS spread for piecewise-constant hazard curve.
    hazard_curve: hazard rates per tenor bucket; tenors: cumulative years.
    """
    T = tenors[-1]
    grid = np.linspace(0, T, int(T * n_periods) + 1)

    def lam_at(t):
        for i, te in enumerate(tenors):
            if t <= te:
                return hazard_curve[i]
        return hazard_curve[-1]

    lams = np.array([lam_at(t) for t in grid])
    S = np.exp(-np.cumsum(np.diff(grid, prepend=0) * lams))
    df = np.exp(-r * grid)
    dS = np.diff(S, prepend=1.0)
    protection = (1 - recovery) * np.sum(df[1:] * (-dS[1:]))
    pay_times = np.arange(1/n_periods, T + 1/n_periods, 1/n_periods)
    pay_S = np.array([
        math.exp(-sum(lam_at(s)*(1/n_periods)
                      for s in np.arange(0, t, 1/n_periods)))
        for t in pay_times
    ])
    annuity = (1/n_periods) * np.sum(pay_S * np.exp(-r * pay_times))
    return float(protection / annuity)


# ── Gaussian copula nth-to-default MC ─────────────────────────────────────────

def gaussian_copula_nth_default_mc(hazard_rates, rho, T, nth,
                                    n_paths=50_000, rng=None):
    """Probability that nth default occurs within T, using 1-factor Gaussian copula.
    Hull eq. (24.7), ch25 §25.10.
    """
    rng = rng or np.random.default_rng(0)
    n = len(hazard_rates)
    M = rng.standard_normal(n_paths)
    Z = rng.standard_normal((n_paths, n))
    X = math.sqrt(rho) * M[:, None] + math.sqrt(1 - rho) * Z
    U = norm.cdf(X)
    tau = -np.log(1 - U) / np.array(hazard_rates)[None, :]
    nth_times = np.partition(tau, nth - 1, axis=1)[:, nth - 1]
    return float(np.mean(nth_times <= T))
```

## デシジョンガイド

**リスク中立デフォルト確率 vs 実世界デフォルト確率**
- リスク中立確率（CDS スプレッド・債券スプレッドから推定）は実世界確率より通常 5〜10 倍高い（Hull Table 24.2）
- デリバティブ価格付け・CVA 計算: **リスク中立確率を使う**
- 信用 VaR・ストレステスト・経済資本: **実世界確率を使う**
- 混同すると CVA の系統的な過小/過大計上につながる

**Gaussian コピュラの限界**
- 共倒れ（joint default）確率を過小評価；テールが薄すぎる
- 2007-09 年の金融危機で ABS CDO エクイティトランシェの損失を著しく過小評価
- 代替: Student-t コピュラ・二重 t コピュラはテールをより厚く表現できる
- 相関スマイル（トランシェ毎にインプライド相関が異なる）はモデルの不完全性の証左

**CDS vs 債券スプレッドからのハザード推定**
- CDS スプレッド: リスク中立デフォルト確率をより直接反映；流動性が高い
- 債券スプレッド: 流動性プレミアムを含む；スプレッド近似 $\lambda \approx s/(1-R)$ は一次近似
- 精密なブートストラップにはキャッシュフロー積分が必要（ch24 Example 24.2 参照）

**CVA の Wrong-Way Risk**
- 標準 CVA はデフォルト確率とエクスポージャーが独立と仮定（ノー・ウロング・ウェイ・リスク）
- Wrong-way risk（正の相関）が存在すると CVA を過小評価；典型例: 相手方が参照企業と同業種
- 正確な処理にはコピュラまたは相関付き MC が必要

**ABS vs ABS CDO の脆弱性**
- ABS シニア (AAA): 原資産プール損失率が 20% を超えなければ保護される
- ABS CDO シニア (AAA): 原資産プール損失率 10.25% 超で急激に損失が発生
- 同じ格付けでもリスクプロファイルは大きく異なる（Hull Table 8.1）
- デフォルト相関は平時に低く、ストレス期に急上昇するため平時データでのモデル校正は危険
