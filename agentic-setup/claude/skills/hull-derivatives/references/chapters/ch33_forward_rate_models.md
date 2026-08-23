# Ch.33 Modeling Forward Rates

> **Source**: Hull 11e, Chapter 33 (pp. 755-772). Paraphrased summary for personal use.

## 1. 要点

- HJM（Heath-Jarrow-Morton）フレームワークは、瞬間フォワードレート $F(t,T)$ の確率過程を直接モデル化し、無裁定条件からドリフト $m(t,T)$ がボラティリティ $s(t,T)$ の積分として一意に決まる（HJM ドリフト制約）。
- HJM の一般形はノン・マルコフであり、ツリーが非再結合になるため Monte Carlo 実装が基本。ただしボラティリティ関数が $s(t,T)=\sigma e^{-a(T-t)}$ のとき Hull-White モデルに帰着し、再結合ツリーが使える。
- BGM（LIBOR市場モデル / LMM）は HJM の問題点（瞬間フォワードレートが市場で直接観測できない点）を解決し、市場で取引されるキャップレートのフォワード $F_k(t)$ を対象とする。Black 公式と整合的にキャップを扱える。
- LMM では各フォワードレートが対応するフォワード測度のもとでマルティンゲール（ドリフトゼロ）となる。スポット LIBOR 測度（ローリングリスク中立世界）ではドリフト修正項が必要（Hull 式 33.10）。
- LMM をキャップボラティリティにキャリブレーションし、Monte Carlo でスワップションやラチェットキャップなどの非標準商品を評価するのが実務上の標準的アプローチ。エージェンシー MBS の評価（プリペイメント関数 + OAS）にも同フレームワークが応用される。

## 2. キー用語

- **HJM フレームワーク**: 瞬間フォワードレート $F(t,T)$ の SDE を無裁定条件から構築する汎用金利モデル体系（Heath, Jarrow, Morton 1992）
- **HJM ドリフト制約**: ドリフトがボラティリティ関数の積分で決まるという無裁定必要条件（式 33.5 / 33.6）
- **ノン・マルコフ性**: HJM の一般形でショートレート $r$ の将来分布が過去の経路に依存する性質。再結合ツリーが原則使えない
- **BGM モデル / LIBOR 市場モデル（LMM）**: Brace-Gatarek-Musiela らが提案した、市場フォワード $F_k(t)$ を直接モデル化する枠組み
- **フォワード測度 $\mathbb{Q}^{k+1}$**: ニューメレールを $P(t, t_{k+1})$ とする確率測度。この測度のもとで $F_k$ はマルティンゲール
- **ローリングリスク中立世界（スポット LIBOR 測度）**: ニューメレールを常に直近リセット日満期の債券とする世界。LMM 実装で最も使われる
- **$\Lambda_i$（BGM ボラティリティ）**: 次リセット日まで $i$ 期間のフォワードレートの瞬間ボラティリティ。ステップ関数として定義
- **ラチェットキャップ**: 各キャップレートが前回リセット時の実現金利＋スプレッドに設定される非標準キャップ
- **スティッキーキャップ**: キャップレートが $\min(前回金利, 前回設定キャップレート) + スプレッド$ に設定される非標準キャップ
- **OAS（オプション調整後スプレッド）**: 内包オプションをすべて考慮した後のモデル価格と市場価格を一致させるスプレッド。エージェンシー MBS 評価に使用
- **プリペイメント関数**: エージェンシー MBS の期待プリペイメントを金利水準・イールドカーブ履歴の関数として表したモデル
- **IO / PO（金利部分 / 元本部分）**: ストリップド MBS の二種類。プリペイメント増加で PO 上昇・IO 下落という逆の感応度を持つ

## 3. 主要公式

### ゼロクーポン債価格プロセス（リスク中立世界、単一因子）

$$
dP(t,T) = r(t)\,P(t,T)\,dt + v(t,T,\Omega_t)\,P(t,T)\,dz(t)
$$

- $v(t,T,\Omega_t)$: $P(t,T)$ のボラティリティ（満期で $v=0$）
- $r(t)$: ショートレート

<!-- Hull eq. (33.1) -->

### フォワードレートとゼロ債価格の関係

$$
f(t, T_1, T_2) = \frac{\ln P(t,T_1) - \ln P(t,T_2)}{T_2 - T_1}
$$

<!-- Hull eq. (33.2) -->

### HJM 瞬間フォワードレートのプロセス（単一因子）

$$
dF(t,T) = v(t,T,\Omega_t)\,v_T(t,T,\Omega_t)\,dt - v_T(t,T,\Omega_t)\,dz(t)
$$

<!-- Hull eq. (33.4) -->

### HJM ドリフト制約（単一因子）

$$
m(t,T,\Omega_t) = s(t,T,\Omega_t)\int_t^T s(t,\tau,\Omega_t)\,d\tau
$$

ここで $dF(t,T) = m(t,T,\Omega_t)\,dt + s(t,T,\Omega_t)\,dz$。ドリフトはボラティリティだけで決まる。

<!-- Hull eq. (33.5) -->

### HJM ドリフト制約（多因子）

$$
m(t,T,\Omega_t) = \sum_k s_k(t,T,\Omega_t)\int_t^T s_k(t,\tau,\Omega_t)\,d\tau
$$

<!-- Hull eq. (33.6) -->

### HJM マルコフ特殊ケース

- $s(t,T)=\sigma$（定数）$\Rightarrow$ Ho-Lee モデル
- $s(t,T)=\sigma e^{-a(T-t)}$ $\Rightarrow$ Hull-White モデル（再結合ツリー可）

### LMM：フォワード測度下でのフォワードレート SDE（単一因子）

$$
dF_k(t) = \zeta_k(t)\,F_k(t)\,dz
$$

$F_k$ は $P(t, t_{k+1})$ をニューメレールとする測度のもとでドリフトゼロのマルティンゲール。

<!-- Hull eq. (33.7) -->

### LMM：ローリングリスク中立世界でのドリフト修正（多因子版 eq. 33.10）

$$
\frac{dF_k(t)}{F_k(t)} = \sum_{i=m(t)}^{k} \frac{\delta_i F_i(t)\,\zeta_i(t)\,\zeta_k(t)}{1 + \delta_i F_i(t)}\,dt + \zeta_k(t)\,dz
$$

- $\delta_i = t_{i+1} - t_i$: アクルーアル期間
- $m(t)$: 時刻 $t$ での次リセット日インデックス
- $\zeta_k(t)$: $F_k(t)$ のボラティリティ

<!-- Hull eq. (33.10) -->

### LMM：キャップレートボラティリティ較正式

$$
\sigma_k^2\,t_k = \sum_{i=1}^{k} \Lambda_{k-i}^2\,\delta_{i-1}
$$

$\Lambda_i$：次リセット日まで $i$ 期間のフォワード瞬間ボラティリティ（ステップ関数）。この式を使って市場のキャップスポットボラティリティ $\sigma_k$ から $\Lambda_i$ を逐次的に求める。

<!-- Hull eq. (33.11) -->

### LMM Monte Carlo 実装（eq. 33.14 近似形）

$$
F_k(t_{j+1}) = F_k(t_j)\exp\!\left[\left(\sum_{i=j+1}^{k}\frac{\delta_i F_i(t_j)\,\Lambda_{i-j-1}\,\Lambda_{k-j-1}}{1+\delta_i F_i(t_j)} - \frac{\Lambda_{k-j-1}^2}{2}\right)\delta_j + \Lambda_{k-j-1}\,\epsilon\sqrt{\delta_j}\right]
$$

$\epsilon \sim \mathcal{N}(0,1)$。各アクルーアル区間内でドリフトを定数近似。

<!-- Hull eq. (33.14) -->

### Rebonato 風スワップションボラティリティ近似（eq. 33.18）

$$
\sigma_{\text{swap}} \approx \sqrt{\frac{1}{T_0}\int_0^{T_0}\sum_{q=1}^{p}\left[\sum_{k=0}^{N-1}\frac{\tau_k\,\beta_{k,q}(t)\,G_k(0)\,\gamma_k(0)}{1+\tau_k\,G_k(0)}\right]^2 dt}
$$

$\gamma_k$: スワップレートに対するフォワードレートの感応度ウェイト。$G_j(t)$ を $G_j(0)$ で近似することで解析的に計算可能。

<!-- Hull eq. (33.18) -->

### キャップレットのブラック公式（LMM と整合的）

$$
\text{Caplet} = \tau\,P(0,t_{k+1})\left[F_k(0)\,N(d_1) - K\,N(d_2)\right]
$$

$$
d_1 = \frac{\ln(F_k(0)/K) + \frac{1}{2}\sigma_k^2 t_k}{\sigma_k\sqrt{t_k}}, \quad d_2 = d_1 - \sigma_k\sqrt{t_k}
$$

## 4. アルゴリズム / 手順

### 手順 1: HJM Monte Carlo（フォワードレートパスの生成）

1. ボラティリティ関数 $s(t,T)$ を指定する（例: $\sigma e^{-a(T-t)}$）。
2. HJM ドリフト制約式 (33.5) または (33.6) からドリフト $m(t,T)$ を計算する。
3. 各時間ステップで $dz$ をサンプリングし、$dF(t,T) = m\,dt + s\,dz$ を Euler 離散化で積分する。
4. ショートレート $r(t)=F(t,t)$ を用いてキャッシュフローを割引く。
5. 注意: 一般形は非再結合ツリー（$n=30$ で約 $10^9$ ノード）。必ず Monte Carlo を使う。

### 手順 2: LMM Monte Carlo（ローリングフォワード測度、ドリフト修正付き）

1. 市場キャップボラティリティ $\sigma_k$ から式 (33.11) で $\Lambda_i$ を逐次求める。
2. 相関行列 $\rho_{ij}$ を主成分分析（PCA）または指数型モデルで設定する。
3. 式 (33.14) または (33.16)（多因子版）を使って各リセット日間で $F_k$ を更新する。
4. 各シミュレーショントライアルで対象商品のキャッシュフローを計算し割引く。
5. 全トライアルの平均を価格とする（分散削減: 対当変量法など）。

### 手順 3: LMM キャップレットボラティリティへのキャリブレーション

1. 市場キャップスポットボラティリティ $\{\sigma_1, \sigma_2, \ldots, \sigma_N\}$ を取得する。
2. 式 (33.11) を $k=1,2,\ldots$ と逐次解いて $\{\Lambda_0, \Lambda_1, \ldots\}$ を求める。
3. または最小二乗法（ペナルティ関数 $P$ 付き）で $\Lambda$ を滑らかに推定する（Levenberg-Marquardt）。
4. 多因子モデルでは PCA を用いて $\lambda_{j,q} = \Lambda_j\,\alpha_{j,q}\,s_q / \sqrt{\sum_q s_q^2 \alpha_{j,q}^2}$ と分解する（式 33.20）。

### 手順 4: Rebonato スワップションボラティリティ近似（swaption キャリブレーション）

1. 対象スワップの payment dates $T_1,\ldots,T_N$ と対応する $G_j(0)$ を確定する。
2. $\gamma_k(0)$ を計算する（スワップレートのフォワードレート感応度）。
3. 式 (33.18) の積分を数値積分し近似スワップションボラティリティを得る。
4. モデル価格と市場スワップションボラティリティの差を最小化するよう $\Lambda$ を調整する。

## 5. Python reference

```python
import math
import numpy as np


def hjm_drift_single_factor(vol_func, tenors, dt=1e-4):
    """Compute HJM no-arbitrage drifts m(t, T_k) given a vol function s(t, T).

    vol_func(T): instantaneous forward-rate volatility at maturity T (called at t=0).
    tenors: array of forward-rate maturities T_k.
    Returns drift array m[k] = s(T_k) * integral_{0}^{T_k} s(tau) dtau.
    """
    n = len(tenors)
    m = np.zeros(n)
    for k, T in enumerate(tenors):
        # Numerical integration of s(tau) from 0 to T
        tau_grid = np.arange(0.0, T + dt, dt)
        integral = np.trapz([vol_func(tau) for tau in tau_grid], tau_grid)
        m[k] = vol_func(T) * integral
    return m


def lmm_calibrate_lambdas(sigma_k, delta, n):
    """Compute BGM step-function vols Lambda_i from market cap spot vols sigma_k.

    sigma_k: array of Black cap spot vols (length n).
    delta:   common accrual period (scalar).
    Returns Lambda array of length n.  Hull eq. (33.11).
    """
    Lambda = np.zeros(n)
    for k in range(n):
        rhs = (sigma_k[k] ** 2) * (k + 1) * delta
        lhs_prev = sum(Lambda[k - i] ** 2 * delta for i in range(1, k + 1))
        val = rhs - lhs_prev
        Lambda[k] = math.sqrt(max(val / delta, 0.0))
    return Lambda


def lmm_simulate(F0, Lambda, corr, delta, n_steps_per_period, n_paths, rng=None):
    """LIBOR Market Model simulation under rolling risk-neutral (spot LIBOR) measure.

    F0:    initial forward rates F_k(0), shape (N,)
    Lambda: BGM step-function vols, shape (N,)
    corr:  N x N correlation matrix
    delta: common accrual period (scalar)
    n_steps_per_period: time steps per accrual period
    n_paths: Monte Carlo paths
    Returns F array of shape (n_paths, N) at terminal time T = N * delta.
    """
    rng = rng or np.random.default_rng(0)
    N = len(F0)
    dt = delta / n_steps_per_period
    L = np.linalg.cholesky(corr)
    F = np.tile(np.array(F0, dtype=float), (n_paths, 1))

    total_steps = N * n_steps_per_period
    for step in range(total_steps):
        t = step * dt
        m_t = int(t / delta)  # index of next reset date at time t
        Z_indep = rng.standard_normal((n_paths, N))
        Z = Z_indep @ L.T  # correlated normals

        periods_elapsed = step // n_steps_per_period
        # vol for F_k at this step: Lambda_{k - m(t)}
        for k in range(m_t, N):
            vol_index = k - m_t
            zeta_k = Lambda[vol_index] if vol_index < N else 0.0
            # Rolling risk-neutral drift (Hull eq. 33.10 / 33.12)
            drift = 0.0
            for i in range(m_t, k + 1):
                vol_index_i = i - m_t
                zeta_i = Lambda[vol_index_i] if vol_index_i < N else 0.0
                drift += (delta * F[:, i] * zeta_i * zeta_k * corr[k, i]
                          / (1.0 + delta * F[:, i]))
            F[:, k] *= np.exp(
                (drift - 0.5 * zeta_k ** 2) * dt
                + zeta_k * math.sqrt(dt) * Z[:, k]
            )
    return F


def lmm_caplet_price(F0, vol, K, tau, P_pay, T_reset):
    """Black caplet price consistent with LMM lognormal forward rates."""
    from scipy.stats import norm
    if T_reset <= 0 or vol <= 0:
        return tau * P_pay * max(F0 - K, 0.0)
    d1 = (math.log(F0 / K) + 0.5 * vol ** 2 * T_reset) / (vol * math.sqrt(T_reset))
    d2 = d1 - vol * math.sqrt(T_reset)
    return tau * P_pay * (F0 * norm.cdf(d1) - K * norm.cdf(d2))


# --- Example usage ---
if __name__ == "__main__":
    N = 4
    F0 = [0.03, 0.035, 0.040, 0.045]
    delta = 0.5  # semi-annual
    sigma_k = [0.20, 0.19, 0.18, 0.17]  # market cap vols

    # Step 1: calibrate Lambda from cap vols
    Lambda = lmm_calibrate_lambdas(sigma_k, delta, N)
    print("Lambda:", np.round(Lambda, 4))

    # Step 2: exponential decay correlation
    corr = np.exp(-0.05 * np.abs(np.subtract.outer(np.arange(N), np.arange(N))))

    # Step 3: simulate
    F_T = lmm_simulate(F0, Lambda, corr, delta, n_steps_per_period=20,
                       n_paths=4_000)
    print("Mean F_3 at T=2y:", float(F_T[:, 3].mean()))

    # Step 4: single caplet sanity check vs Black
    P_pay = math.exp(-0.03 * delta)
    price = lmm_caplet_price(F0[0], sigma_k[0], F0[0], delta, P_pay, delta)
    print(f"ATM Caplet (F={F0[0]:.2%}, K={F0[0]:.2%}, vol={sigma_k[0]:.0%}): {price:.6f}")

    # HJM drift example: Hull-White vol structure s(T) = sigma * exp(-a*T)
    sigma_hw, a_hw = 0.01, 0.1
    tenors = np.array([0.5, 1.0, 2.0, 5.0, 10.0])
    drifts = hjm_drift_single_factor(
        lambda T: sigma_hw * math.exp(-a_hw * T), tenors
    )
    print("HJM drifts (Hull-White vol):", np.round(drifts, 6))
```

## 6. 注意点 / 典型的なミス

- **HJM のノン・マルコフ性を忘れる**: 一般 HJM でショートレートを状態変数とした有限ツリーを構築しようとすると、ノードが $2^n$ に爆発する（$n=30$ で約 $10^9$）。必ず Monte Carlo を使う。マルコフ化できるのは $s(t,T)=\sigma e^{-a(T-t)}$ などの特殊構造のみ。
- **LMM のドリフトを測度に合わせないミス**: フォワード測度 $\mathbb{Q}^{k+1}$ ではドリフトゼロ、ローリングリスク中立世界では式 (33.10) の補正項が必要。測度を間違えると価格が系統的にずれる。
- **負金利対応の未考慮**: LMM は $F_k$ の対数正規性を仮定するため負金利が発生しない。SOFR/LIBOR 廃止後の低金利・マイナス金利環境では Shifted LMM（$F_k + s$ を対数正規とするシフト版）または Normal LMM を使う。
- **キャップとスワップションのボラティリティの不整合**: 同一の $\Lambda$ セットでもキャップボラティリティには唯一的に整合するが、スワップションボラティリティは相関構造 $\rho_{ij}$ に依存する。相関を正確に推定しないと、キャップに整合させてもスワップションが大きくずれる。
- **ドリフト近似誤差**: 式 (33.14) はアクルーアル区間内でドリフトを定数として近似する。アクルーアル期間が長い（年 1 回以上）場合でも誤差は小さいことが確認されているが、ボラティリティが極端に高い場合は要注意。
- **Monte Carlo 分散の管理**: LMM の Monte Carlo は状態変数が $N$ 個（フォワードレート全体のカーブ）あり分散が大きい。対当変量法（antithetic variates）や制御変量（キャップレットポートフォリオ）を使わないと収束が遅い。

## 7. 関連トピック

- See: [topics/ir_derivatives.md](../topics/ir_derivatives.md), Ch.29（Blackモデルによるキャップ・スワップションの基礎 — LMM の整合ベースライン）, Ch.30（コンベクシティ・タイミング・クアント調整 — 非自然な支払日のあるデリバティブに必要）, Ch.32（Hull-White は HJM の特殊ケース — 再結合ツリーが使えるマルコフ条件を確認）, Ch.34（スワップの再訪 — スワップション評価との連続性）
