# Ch.23 Estimating Volatilities and Correlations

> **Source**: Hull 11e, Chapter 23 (pp. 542-561). Paraphrased summary for personal use.

## 1. 要点

- ボラティリティ・相関は時変であり、EWMA と GARCH(1,1) は過去データから現在水準を継続的に追跡する代表的モデル。
- EWMA は直近観測値に指数的に減衰する重みを付け、RiskMetrics では $\lambda = 0.94$ を採用。ストレージ効率が高く、前日の分散推定値と直近リターン 1 本だけを保持すればよい。
- GARCH(1,1) は EWMA に長期平均分散 $V_L$ への平均回帰を加えた構造を持ち、理論的に優位。パラメータは最尤法 (MLE) で推定する。
- GARCH(1,1) からの多期間ボラティリティ予測は $E[\sigma_{n+t}^2] = V_L + (\alpha+\beta)^t(\sigma_n^2 - V_L)$ で与えられ、$t \to \infty$ で $V_L$ に収束（ボラティリティ・タームストラクチャーの基礎）。
- 相関推定も EWMA / GARCH で共分散を更新して導出できるが、分散共分散行列は正半定値 (PSD) 条件を満たす必要がある。相関付き乱数生成には Cholesky 分解を用いる。

## 2. キー用語

- **分散レート (variance rate)**: $\sigma_n^2$。ボラティリティの二乗。日次パーセンタリターンの二乗の加重平均として推定される。
- **EWMA (Exponentially Weighted Moving Average)**: 重みが指数的に減衰するボラティリティ更新モデル。パラメータは $\lambda$ のみ。
- **GARCH(1,1)**: 前期リターン二乗と前期分散に加え長期平均分散に重みを付けるモデル。Bollerslev (1986) 提案。
- **長期平均分散 $V_L$**: GARCH の定常状態での分散。$V_L = \omega / (1 - \alpha - \beta)$。
- **平均回帰 (mean reversion)**: 分散が時間とともに $V_L$ に引き戻される性質。速度は $1 - \alpha - \beta$。
- **最尤法 (MLE)**: データが観測される確率（尤度）を最大化するパラメータ推定法。
- **バリアンス・ターゲティング (variance targeting)**: $V_L$ をサンプル分散に固定し $\alpha, \beta$ のみを MLE で推定する代替アプローチ。
- **Ljung-Box 統計量**: $u_i^2$ の自己相関の有意性検定。GARCH 適合後は $u_i^2 / \sigma_i^2$ に適用し自己相関の除去を確認。
- **正半定値行列 (positive-semidefinite matrix)**: すべてのベクトル $w$ に対し $w^\top \Omega w \ge 0$ を満たす行列。分散共分散行列の内部一貫性の必要条件。
- **Cholesky 分解**: 対称正定値行列 $\Sigma = L L^\top$ と分解する手法。相関付き正規乱数生成に使う。

## 3. 主要公式

### 不偏サンプル分散推定量
$$\sigma_n^2 = \frac{1}{m-1} \sum_{i=1}^{m} (u_{n-i} - \bar{u})^2$$
- $u_i = \ln(S_i / S_{i-1})$: 日次連続複利リターン
- $\bar{u}$: 直近 $m$ 観測の標本平均

<!-- Hull eq. (23.1) -->

### 標準推定量（ゼロ平均仮定）
$$\sigma_n^2 = \frac{1}{m} \sum_{i=1}^{m} u_{n-i}^2$$
- 日次モニタリング用に $\bar{u} = 0$、分母を $m$ に簡略化したもの

<!-- Hull eq. (23.3) -->

### EWMA ボラティリティ更新
$$\sigma_n^2 = \lambda \sigma_{n-1}^2 + (1 - \lambda) u_{n-1}^2$$
- $\lambda \in (0,1)$: 減衰パラメータ（RiskMetrics 標準値 $\lambda = 0.94$）
- $\lambda$ が大きいほど過去への重みが維持され、直近ショックへの反応が遅くなる

<!-- Hull eq. (23.7) -->

### GARCH(1,1) — 推定用形式
$$\sigma_n^2 = \omega + \alpha u_{n-1}^2 + \beta \sigma_{n-1}^2$$
- 定常条件: $\alpha + \beta < 1$（違反すると長期分散が負になる）
- 長期平均分散: $V_L = \omega / (1 - \alpha - \beta)$

<!-- Hull eq. (23.9) -->

### GARCH(1,1) — 平均回帰形式
$$\sigma_n^2 = \gamma V_L + \alpha u_{n-1}^2 + \beta \sigma_{n-1}^2, \quad \gamma = 1 - \alpha - \beta$$
- $\gamma$: $V_L$ に割り当てられる重み。EWMA は $\gamma = 0$ の特殊ケース

<!-- Hull eq. (23.8) -->

### MLE 目的関数（GARCH パラメータ推定）
$$\text{maximize} \quad \sum_{i=1}^{m} \left[ -\ln \sigma_i^2 - \frac{u_i^2}{\sigma_i^2} \right]$$
- $\sigma_i^2 = v_i$: day $i$ のモデル推定分散。各ステップで GARCH 漸化式により更新

<!-- Hull eq. (23.12) -->

### 多期間分散予測（GARCH）
$$E[\sigma_{n+t}^2] = V_L + (\alpha + \beta)^t \left( \sigma_n^2 - V_L \right)$$
- $t \to \infty$ で $V_L$ に収束。$\alpha + \beta$ が 1 に近いほど収束が遅い（持続性が高い）

<!-- Hull eq. (23.13) -->

### ボラティリティ・タームストラクチャー（年率換算）
$$\sigma(T)^2 = 252 \left( V_L + \frac{1 - e^{-aT}}{aT} \left[ V(0) - V_L \right] \right), \quad a = \ln\frac{1}{\alpha+\beta}$$

<!-- Hull eq. (23.14) -->

### 共分散の EWMA 更新
$$\mathrm{cov}_n = \lambda \, \mathrm{cov}_{n-1} + (1 - \lambda) \, x_{n-1} y_{n-1}$$
- $x_i, y_i$: 変数 $X, Y$ の日次パーセント変化

<!-- Hull eq. (23.7) 対応形式 -->

### 相関係数
$$\rho_{xy,n} = \frac{\mathrm{cov}_n}{\sigma_{x,n} \, \sigma_{y,n}}$$

### 正半定値条件
$$w^\top \Omega \, w \ge 0 \quad \text{for all } w$$
- 分散と共分散を同一の重み付けスキームで一貫して計算することが必要条件

<!-- Hull eq. (23.17) -->

### Cholesky 分解による相関付き正規乱数
$$X = L Z, \quad \Sigma = L L^\top$$
- $Z \sim \mathcal{N}(0, I)$: 独立標準正規ベクトル
- $X \sim \mathcal{N}(0, \Sigma)$: 相関構造 $\Sigma$ を持つ正規ベクトル

## 4. アルゴリズム / 手順

### 1. EWMA ボラティリティ更新（オンライン・逐次）
1. 初期分散 $\sigma_1^2$ をサンプル分散または最初のリターン二乗で設定する。
2. 新しい日次リターン $u_t$ が到着したら $\sigma_t^2 = \lambda \sigma_{t-1}^2 + (1 - \lambda) u_{t-1}^2$ を適用する。
3. 保存するのは $(\sigma_{t-1}^2, u_{t-1})$ のみ。古いデータは不要。

### 2. GARCH(1,1) の MLE 較正
1. 日次リターン系列 $\{u_i\}$ を用意する（対数リターン推奨）。
2. 初期パラメータ $(\omega, \alpha, \beta)$ を設定する（例: $\omega=10^{-6}, \alpha=0.05, \beta=0.90$）。
3. GARCH 漸化式で $v_i = \sigma_i^2$ を逐次計算する。最初の $v$ は $u_2^2$ か標本分散で初期化。
4. 対数尤度 $\sum_i [-\ln v_i - u_i^2 / v_i]$ を最大化するよう数値最適化（Nelder-Mead 等）を行う。
5. 最適解で $\gamma = 1 - \alpha - \beta$, $V_L = \omega / (1 - \alpha - \beta)$ を計算する。
6. （オプション）バリアンス・ターゲティング: $V_L$ = サンプル分散に固定し $\alpha, \beta$ のみを推定。

### 3. 多期間分散予測（GARCH 適合後）
1. 現在の分散推定値 $\sigma_n^2$ と $V_L, \alpha, \beta$ を確認する。
2. $t$ 日後の予測分散: $E[\sigma_{n+t}^2] = V_L + (\alpha+\beta)^t (\sigma_n^2 - V_L)$ を計算する。
3. 年率ボラティリティを求めるには eq.(23.14) で 252 日に換算する。

### 4. Cholesky 分解による相関付き乱数生成
1. 相関行列 $\Sigma$（または共分散行列）が PSD であることを確認する（固有値 $\ge 0$）。
2. Cholesky 分解 $\Sigma = L L^\top$ を計算する（`np.linalg.cholesky`）。
3. 独立標準正規ベクトル $Z$ を生成する。
4. $X = L Z$ で相関付き乱数を得る。

### 5. 固有値パッチング（PSD 修正）
1. 対称行列 $\Omega$ の固有値分解 $\Omega = Q \Lambda Q^\top$ を計算する。
2. 負の固有値を小さな正値（例: $10^{-8}$）にクリップする: $\Lambda' = \max(\Lambda, \epsilon)$。
3. 修正行列 $\Omega' = Q \Lambda' Q^\top$ を再構成し正規化して相関行列に戻す。

## 5. Python reference

```python
import numpy as np
from scipy.optimize import minimize


def ewma_var(returns, lam=0.94, init=None):
    """EWMA variance series. returns[i] is the return for day i."""
    r = np.asarray(returns, dtype=float)
    var = np.zeros_like(r)
    var[0] = init if init is not None else r[0] ** 2
    for i in range(1, len(r)):
        var[i] = lam * var[i - 1] + (1 - lam) * r[i - 1] ** 2
    return var


def garch11_filter(returns, omega, alpha, beta, sigma2_0=None):
    """Compute the GARCH(1,1) conditional variance series."""
    r = np.asarray(returns, dtype=float)
    sigma2 = np.zeros_like(r)
    sigma2[0] = sigma2_0 if sigma2_0 is not None else np.var(r)
    for i in range(1, len(r)):
        sigma2[i] = omega + alpha * r[i - 1] ** 2 + beta * sigma2[i - 1]
    return sigma2


def garch11_neg_loglik(params, returns):
    """Negative log-likelihood for GARCH(1,1) MLE (Hull eq. 23.12)."""
    omega, alpha, beta = params
    if min(omega, alpha, beta) < 0 or alpha + beta >= 1.0:
        return 1e10
    s2 = garch11_filter(returns, omega, alpha, beta)
    s2 = np.maximum(s2, 1e-12)
    r = np.asarray(returns, dtype=float)
    return float(np.sum(np.log(s2) + r ** 2 / s2))


def garch11_fit(returns, x0=(1e-6, 0.05, 0.90)):
    """Fit GARCH(1,1) via MLE. Returns dict with omega, alpha, beta, V_L."""
    res = minimize(
        garch11_neg_loglik, x0, args=(returns,),
        method="Nelder-Mead",
        options={"xatol": 1e-8, "fatol": 1e-8, "maxiter": 10000},
    )
    omega, alpha, beta = res.x
    return dict(
        omega=omega, alpha=alpha, beta=beta,
        long_run_var=omega / (1 - alpha - beta),
        loglik=-res.fun,
    )


def garch11_forecast(sigma2_n, V_L, alpha, beta, horizon):
    """Multi-step variance forecast: E[sigma^2_{n+t}] for t = 1..horizon."""
    t = np.arange(1, horizon + 1)
    return V_L + (alpha + beta) ** t * (sigma2_n - V_L)


def correlated_normals(corr, n_samples, rng=None):
    """Generate n_samples correlated standard normals via Cholesky (Hull §23.7)."""
    rng = rng or np.random.default_rng(0)
    L = np.linalg.cholesky(corr)
    Z = rng.standard_normal(size=(n_samples, corr.shape[0]))
    return Z @ L.T


def nearest_psd(matrix, epsilon=1e-8):
    """Eigenvalue clipping to repair a near-PSD matrix."""
    vals, vecs = np.linalg.eigh(matrix)
    vals = np.maximum(vals, epsilon)
    return vecs @ np.diag(vals) @ vecs.T


# --- Example ---
rng = np.random.default_rng(42)
returns = rng.standard_normal(1260) * 0.01   # ~5 years of daily returns

fit = garch11_fit(returns)
print("GARCH fit:", {k: f"{v:.6g}" for k, v in fit.items()})

sigma2_today = garch11_filter(returns, fit["omega"], fit["alpha"], fit["beta"])[-1]
fcast = garch11_forecast(sigma2_today, fit["long_run_var"], fit["alpha"], fit["beta"], 10)
print("10-day variance forecast:", fcast)
print("EWMA var[-1]:", ewma_var(returns)[-1])
```

## 6. 注意点 / 典型的なミス

- **$\lambda$ のトレードオフ**: $\lambda$ が 1 に近いほど平滑化が強く過去のボラティリティ・レジームが残存する。直近のショックへの反応が遅くなる。逆に低い $\lambda$ は推定値の変動が激しくなる。
- **定常性条件の確認**: $\alpha + \beta \ge 1$ ではGARCH が不安定（分散が発散）。最適化後に必ず確認すること。$\omega < 0$ になった場合は EWMA モデルへ切り替えを検討。
- **リターン単位の一貫性**: Hull は百分率日次リターン ($u_i = (S_i - S_{i-1})/S_{i-1}$) を標準として扱う。対数リターンとの混用に注意。$\omega$ の単位が変わる。
- **相関推定は分散より不安定**: ノイズが多いため、$\rho$ の推定には長いウィンドウが望ましい。短期窓では相関推定誤差がリスク計算に伝播する。
- **ボラティリティ予測の長期収束**: GARCH の多期間予測は $t \to \infty$ で $V_L$ へ収束する。これがタームストラクチャーの傾きを決定する（現在 $\sigma^2 > V_L$ なら右下がり）。
- **PSD 条件の違反**: 分散と共分散を異なるウィンドウ長や $\lambda$ で推定すると行列が PSD でなくなる可能性がある。Cholesky 分解が失敗する原因になる。固有値クリッピングで修正できるが、根本原因は一貫した推定スキームの使用。
- **MLE の局所最適**: 初期値依存で局所解に収束することがある。複数の初期値から試行するか、スケールを揃えた変数変換（Hull の Excel ヒント参照）を行うと安定する。

## 7. 関連トピック

- See: [topics/risk_management.md](../topics/risk_management.md), Ch.22 (VaR/ES — ボラティリティ・共分散行列の入力として本章の推定量を使用), Ch.20 (インプライド・ボラティリティ — 異なる概念：市場価格から逆算), [topics/vol_smile_surface.md](../topics/vol_smile_surface.md), Ch.27 (確率的ボラティリティモデル — GARCH の連続時間極限 $dV = a(V_L - V)dt + \xi V \, dz$).
