# Topic: Risk Management (VaR, ES, Volatility Estimation)

## 対応章
- Ch.22 Value at Risk and Expected Shortfall — [chapters/ch22_var_es.md](../chapters/ch22_var_es.md)
- Ch.23 Estimating Volatilities and Correlations — [chapters/ch23_vol_corr_estimation.md](../chapters/ch23_vol_corr_estimation.md)

## クイック公式

### VaR 定義
$$\Pr(L > \mathrm{VaR}_\alpha) = 1 - \alpha$$
- $L$: 損失（正値が損失）、$\alpha$: 信頼水準（例: 0.99）
- See: ch22 §22.1

### ES 定義
$$\mathrm{ES}_\alpha = E[L \mid L > \mathrm{VaR}_\alpha]$$
- VaR を超えた場合の条件付き期待損失（CVaR / Expected Tail Loss）
- See: ch22 §22.1

### $\sqrt{N}$ スケーリング（iid 正規仮定下）
$$\mathrm{VaR}_{N\text{-day}} = \sqrt{N} \cdot \mathrm{VaR}_{1\text{-day}}$$
- iid・正規リターン仮定が必須；ボラティリティクラスタリングがある実市場では近似にすぎない
- See: ch22 p.517

### パラメトリック VaR（線形ポートフォリオ、正規分布）
$$\mathrm{VaR} = z_\alpha \sigma_P, \qquad \sigma_P = \sqrt{\mathbf{w}^\top \Sigma \mathbf{w}}$$
- $z_\alpha = \Phi^{-1}(\alpha)$（99% では 2.326、97.5% では 1.960）
- See: ch22 eq.(22.3), (22.4)

### 正規分布下での ES
$$\mathrm{ES}_\alpha = \sigma_P \frac{\phi(z_\alpha)}{1-\alpha}$$
- $\phi(\cdot)$: 標準正規密度関数；$\mu=0$ 仮定
- See: ch22 eq.(22.1)

### デルタ-ガンマ近似（オプションを含む場合）
$$\Delta P \approx \Delta \cdot \Delta S + \tfrac{1}{2}\Gamma(\Delta S)^2$$
- 線形近似（デルタのみ）はガンマを無視するため、オプションポートフォリオでは不十分
- See: ch22 eq.(22.7)

### EWMA ボラティリティ更新
$$\sigma_n^2 = \lambda \sigma_{n-1}^2 + (1-\lambda) u_{n-1}^2$$
- $\lambda$: 減衰パラメータ（RiskMetrics 標準値 $\lambda = 0.94$）；保存するのは $(\sigma_{n-1}^2, u_{n-1})$ のみ
- See: ch23 eq.(23.7)

### GARCH(1,1)
$$\sigma_n^2 = \omega + \alpha u_{n-1}^2 + \beta \sigma_{n-1}^2, \qquad V_L = \frac{\omega}{1-\alpha-\beta}$$
- 定常条件: $\alpha + \beta < 1$；$V_L$: 長期平均分散（平均回帰の引力点）
- See: ch23 eq.(23.9)

### GARCH 多期間分散予測
$$E[\sigma_{n+t}^2] = V_L + (\alpha+\beta)^t(\sigma_n^2 - V_L)$$
- $t \to \infty$ で $V_L$ に収束；$\alpha+\beta$ が 1 に近いほど収束が遅い
- See: ch23 eq.(23.13)

### Cholesky による相関付き正規乱数
$$X = LZ, \quad \Sigma = LL^\top, \quad Z \sim \mathcal{N}(0, I)$$
- 正半定値 (PSD) 条件が失敗した場合は固有値クリッピングで修正
- See: ch23 §23.7

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize


def historical_var_es(pnl, alpha=0.99):
    """VaR/ES from historical P&L series (positive = profit)."""
    losses = -np.asarray(pnl)
    var = np.quantile(losses, alpha)
    es = losses[losses >= var].mean()
    return float(var), float(es)


def parametric_var_es(sigma_P, alpha=0.99, mean=0.0):
    """1-day VaR/ES assuming normal P&L (mean=0 by default)."""
    z = norm.ppf(alpha)
    var = z * sigma_P - mean
    es = sigma_P * norm.pdf(z) / (1 - alpha) - mean
    return float(var), float(es)


def ewma_var(returns, lam=0.94, init=None):
    """EWMA variance series. Hull eq. (23.7)."""
    r = np.asarray(returns, dtype=float)
    var = np.zeros_like(r)
    var[0] = init if init is not None else r[0] ** 2
    for i in range(1, len(r)):
        var[i] = lam * var[i - 1] + (1 - lam) * r[i - 1] ** 2
    return var


def garch11_fit(returns, x0=(1e-6, 0.05, 0.90)):
    """Fit GARCH(1,1) via MLE. Returns dict with omega, alpha, beta, V_L.
    Hull eq. (23.12).
    """
    r = np.asarray(returns, dtype=float)

    def neg_loglik(params):
        omega, alpha, beta = params
        if min(omega, alpha, beta) < 0 or alpha + beta >= 1.0:
            return 1e10
        s2 = np.zeros_like(r)
        s2[0] = np.var(r)
        for i in range(1, len(r)):
            s2[i] = omega + alpha * r[i - 1] ** 2 + beta * s2[i - 1]
        s2 = np.maximum(s2, 1e-12)
        return float(np.sum(np.log(s2) + r ** 2 / s2))

    res = minimize(neg_loglik, x0, method="Nelder-Mead",
                   options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 10000})
    omega, alpha, beta = res.x
    return dict(omega=omega, alpha=alpha, beta=beta,
                long_run_var=omega / (1 - alpha - beta))


def garch11_forecast(sigma2_n, V_L, alpha, beta, horizon):
    """Multi-step variance forecast. Hull eq. (23.13)."""
    t = np.arange(1, horizon + 1)
    return V_L + (alpha + beta) ** t * (sigma2_n - V_L)


def correlated_normals(corr, n_samples, rng=None):
    """Generate correlated standard normals via Cholesky. Hull §23.7."""
    rng = rng or np.random.default_rng(0)
    L = np.linalg.cholesky(corr)
    Z = rng.standard_normal(size=(n_samples, corr.shape[0]))
    return Z @ L.T


def nearest_psd(matrix, epsilon=1e-8):
    """Eigenvalue clipping to repair near-PSD matrix."""
    vals, vecs = np.linalg.eigh(matrix)
    vals = np.maximum(vals, epsilon)
    return vecs @ np.diag(vals) @ vecs.T
```

## デシジョンガイド

**VaR vs ES**
- VaR は劣加法性を満たさない非コヒーレント指標；分散化でリスクが増大するポートフォリオを構築可能
- ES はコヒーレント（劣加法性・正斉次性・単調性・変換不変性を満たす）；Basel IV (FRTB) は VaR 99% から ES 97.5% へ移行
- ES のバックテストは VaR より難しい（超過損失の大きさも必要）

**ヒストリカル vs パラメトリック vs MC**
| 手法 | 長所 | 短所 |
|---|---|---|
| ヒストリカル | 分布仮定不要；ファットテール自動反映 | 過去にないシナリオ対応不可；500日分のデータ依存 |
| パラメトリック | 高速・解析的 | 正規分布仮定；オプション多数の場合は不適 |
| MC | 任意の分布・非線形ポートフォリオ対応 | 計算コスト高；モデルリスク |

**EWMA vs GARCH**
- EWMA: $\lambda$ の 1 パラメータのみ；実装容易；長期平均回帰なし
- GARCH: 平均回帰項 $\gamma V_L$ を含む；理論的に優位；MLE で 3 パラメータを推定
- 短期モニタリングは EWMA で十分；長期予測・タームストラクチャー構築には GARCH を使う

**正半定値共分散行列の保証**
- 分散と共分散を異なるウィンドウ長・$\lambda$ で推定すると PSD 条件が破れる
- 固有値クリッピング (`nearest_psd`) で修正可能だが根本原因は一貫した推定スキームの使用
- Cholesky 分解が失敗した場合は必ず PSD 修正を適用してから再試行

**$\sqrt{N}$ スケーリングの適用条件**
- 厳密には iid 正規リターン仮定下のみ有効
- ボラティリティクラスタリングや裾の重さがある実市場では長期ホライズンのリスクを過少評価しやすい
- Basel の規制資本計算では $\sqrt{10}$ スケーリングを用いるが、実務家はこれを近似として認識すること
