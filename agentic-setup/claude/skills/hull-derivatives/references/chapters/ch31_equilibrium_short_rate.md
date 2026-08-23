# Ch.31 Equilibrium Models of the Short Rate

> **Source**: Hull 11e, Chapter 31 (pp. 719-731). Paraphrased summary for personal use.

## 1. 要点

- リスク中立世界でショートレート $r$ のマルコフ過程を指定すると、任意の満期のゼロクーポン債価格・金利が $r$ の関数として理論的に算出できる。
- **Rendleman-Bartter** は対数正規ショートレート（株価と同じ幾何ブラウン運動）だが平均回帰がなく、金利モデルとして一般的に棄却される。
- **Vasicek** は平均回帰 + ガウスノイズ。ショートレートが負になりうるが、解析的な債券価格式を持つ。
- **CIR (Cox-Ingersoll-Ross)** は拡散項が $\sigma\sqrt{r}$ で、フェラー条件 $2ab \ge \sigma^2$ を満たせばショートレートが非負に保たれる。
- 均衡モデルは現在のイールドカーブに正確にフィットしない（≠ no-arb モデル）。実際の価格付けには Ch.32 の無裁定モデルが必要。

## 2. キー用語

- **ショートレート (short rate)** $r$: 瞬間的な無リスク金利（instantaneous short rate）。ボンド価格・デリバティブ価格はすべて $r$ の過程に依存する。
- **平均回帰 (mean reversion)**: 金利が長期均衡水準 $b$ に引き戻される性質。金利が高いと負のドリフト、低いと正のドリフト。
- **アフィンモデル (affine term structure model)**: ゼロクーポン債価格が $P(t,T) = A(t,T)e^{-B(t,T)r(t)}$ の形で表せるモデル。Vasicek・CIR の両方がアフィン。
- **市場価格リスク (market price of risk)** $\lambda$: リスク中立過程と現実世界過程の差を結ぶパラメータ。金利に対しては負値。
- **フェラー条件 (Feller condition)**: CIR で $2ab \ge \sigma^2$ を満たすと $r(t)$ が常に正。
- **均衡モデル vs 無裁定モデル**: 均衡モデルは経済的な仮定から導出され初期イールドカーブに厳密に合わない。無裁定モデル（Ch.32）は初期カーブを正確に再現するよう設計される。
- **二因子モデル (two-factor model)**: $r$ の平均回帰水準自体が確率過程に従う拡張モデル（例: Hull-White 二因子、Longstaff-Schwartz）。

## 3. 主要公式

### 一般一因子ショートレートモデル

$$dr = m(r,t)\,dt + s(r,t)\,dz$$

<!-- Hull eq. (p.720, general form) -->

- $m(r,t)$: ドリフト関数
- $s(r,t)$: 拡散（ボラティリティ）関数
- 定常性を仮定するとパラメータが時間に依存しない: $dr = m(r)\,dt + s(r)\,dz$

### 金利デリバティブの偏微分方程式（BSM の金利版）

$$\frac{\partial f}{\partial t} + m\frac{\partial f}{\partial r} + \tfrac{1}{2}s^2\frac{\partial^2 f}{\partial r^2} = rf$$

<!-- Hull eq. (31.5) for bond price P(t,T) -->

### Rendleman-Bartter モデル

$$dr = \mu r\,dt + \sigma r\,dz$$

<!-- Hull §31.2 — Rendleman-Bartter -->

- $r$ が幾何ブラウン運動（対数正規）で常に正。ただし平均回帰なし。
- $m(r)=\mu r$, $s(r)=\sigma r$

### Vasicek モデル

$$dr = a(b - r)\,dt + \sigma\,dz$$

<!-- Hull eq. (p.722) — Vasicek -->

- $a$: 平均回帰速度、$b$: 長期均衡水準、$\sigma$: 定数ボラティリティ
- ショートレートは正規分布 → 負値になりうる

**Vasicek ゼロクーポン債価格:**

$$P(t,T) = A(t,T)\,e^{-B(t,T)\,r(t)}$$

<!-- Hull eq. (31.6) -->

$$B(t,T) = \frac{1 - e^{-a(T-t)}}{a}$$

<!-- Hull eq. (31.7) -->

$$A(t,T) = \exp\!\left[\frac{(B(t,T) - (T-t))(a^2 b - \sigma^2/2)}{a^2} - \frac{\sigma^2 B(t,T)^2}{4a}\right]$$

<!-- Hull eq. (31.8) -->

（$a=0$ のとき $B=T-t$, $A=\exp[\sigma^2(T-t)^3/6]$）

**ゼロ金利の表現:**

$$R(t,T) = -\frac{1}{T-t}\ln A(t,T) + \frac{1}{T-t}B(t,T)\,r(t)$$

<!-- Hull eq. (31.10) -->

$R(t,T)$ は $r(t)$ の線形関数 → $r(t)$ がイールドカーブの水準を決める。

### CIR モデル

$$dr = a(b - r)\,dt + \sigma\sqrt{r}\,dz$$

<!-- Hull §31.2 — Cox-Ingersoll-Ross -->

- 拡散項 $\sigma\sqrt{r}$ により $r$ が大きいほどボラティリティが増す
- フェラー条件 $2ab \ge \sigma^2$ のとき $r(t) \ge 0$ が保証される

**CIR ゼロクーポン債価格:**

$$P(t,T) = A(t,T)\,e^{-B(t,T)\,r(t)}$$

$$B(t,T) = \frac{2(e^{\gamma(T-t)}-1)}{(\gamma+a)(e^{\gamma(T-t)}-1)+2\gamma}$$

$$A(t,T) = \left[\frac{2\gamma\,e^{(a+\gamma)(T-t)/2}}{(\gamma+a)(e^{\gamma(T-t)}-1)+2\gamma}\right]^{2ab/\sigma^2}$$

$$\gamma = \sqrt{a^2 + 2\sigma^2}$$

<!-- Hull §31.2 — CIR bond price formulas -->

### 実世界プロセスとリスク中立プロセスの関係（Vasicek）

リスク中立: $dr = a(b-r)\,dt + \sigma\,dz$

実世界（市場リスク価格 $\lambda$ を組み込み）:

$$dr = a(b^* - r)\,dt + \sigma\,dz, \quad b^* = b + \frac{\lambda\sigma}{a}$$

<!-- Hull eq. (31.13) -->

（$\lambda < 0$ なので $b^* < b$：実世界での平均回帰水準はリスク中立世界より低い）

### 二因子 Vasicek 拡張

$$dr = (u - ar)\,dt + \sigma_1\,dz_1, \quad du = -bu\,dt + \sigma_2\,dz_2$$

$$P(t,T) = A(t,T)\,e^{-B(t,T)r - C(t,T)u}$$

$$C(t,T) = \frac{1}{a(a-b)}e^{-a(T-t)} - \frac{1}{b(a-b)}e^{-b(T-t)} + \frac{1}{ab}$$

<!-- Hull eq. (31.14) -->

## 4. アルゴリズム / 手順

### 1. Vasicek 債券価格（解析解）

1. $\tau = T - t$ を計算。$\tau \le 0$ なら $P = 1$ を返す。
2. $B = (1 - e^{-a\tau})/a$ を計算。
3. $A = \exp\!\left[(B-\tau)(a^2 b - \sigma^2/2)/a^2 - \sigma^2 B^2/(4a)\right]$ を計算。
4. $P = A \cdot e^{-B r_0}$ を返す。

### 2. Vasicek 債券オプション価格（Hull §31.3 相当）

（Hull 本文にはこの章で閉形式が示されており、ゼロクーポン債オプションに適用可能）

1. Vasicek では $P(t,T)$ は $r(t)$ の正規関数 → オプション価格もガウス積分で解析的に求まる。
2. 将来時点 $s$ における $P(s,T)$ の条件付き分布を $r(s)$ の分布から導出（正規分布）。
3. コールオプション価格 $= \hat{E}[e^{-\bar{r}(s-t)} \max(P(s,T)-K, 0)]$ をガウス閉形式で計算。

### 3. CIR モンテカルロ（Euler-Maruyama + 吸収境界）

1. $dt = T / N$, 初期値 $r_0$ を設定。
2. 各ステップ: $r_{i+1} = r_i + a(b - r_i)\,dt + \sigma\sqrt{r_i}\sqrt{dt}\,Z_i$, $Z_i \sim \mathcal{N}(0,1)$。
3. 吸収処理: $r_{i+1} = \max(r_{i+1}, 0)$（フェラー条件を満たさない場合に必要）。
4. 割引因子 $e^{-\sum r_i \cdot dt}$ の期待値でボンド価格を推定。

### 4. Vasicek を過去データにキャリブレーション

1. 観測系列 $r_0, r_1, \ldots, r_n$（間隔 $\Delta t$）を用意。
2. $\Delta r_i = r_{i+1} - r_i$ を計算。
3. OLS: $\Delta r_i \approx \alpha + \beta r_i$ を回帰。
4. $a = -\beta/\Delta t$, $b = -\alpha/\beta$, $\sigma = \sqrt{\text{Var}(\text{残差})/\Delta t}$ と変換。
5. リスク中立パラメータへの変換には $\lambda$（市場リスク価格）の推定が別途必要。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm, ncx2


def vasicek_bond_price(r0, a, b, sigma, t, T):
    """Vasicek zero-coupon bond price P(t, T).

    dr = a(b - r) dt + sigma dW

    At t=T returns 1 by construction.
    """
    tau = T - t
    if tau <= 0:
        return 1.0
    B = (1 - math.exp(-a * tau)) / a
    A = math.exp(
        (B - tau) * (a**2 * b - sigma**2 / 2) / a**2
        - (sigma**2 * B**2) / (4 * a)
    )
    return A * math.exp(-B * r0)


def vasicek_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng=None):
    """Simulate short-rate paths under Vasicek (Euler-Maruyama)."""
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    r = np.full((n_paths, n_steps + 1), r0, dtype=float)
    for i in range(1, n_steps + 1):
        Z = rng.standard_normal(n_paths)
        r[:, i] = r[:, i-1] + a * (b - r[:, i-1]) * dt + sigma * math.sqrt(dt) * Z
    return r


def vasicek_calibrate_historical(r_series, dt):
    """OLS calibration of Vasicek (a, b) from observed short-rate series."""
    r = np.asarray(r_series)
    dr = np.diff(r)
    X = np.column_stack([np.ones_like(r[:-1]), r[:-1]])
    coefs, *_ = np.linalg.lstsq(X, dr, rcond=None)
    a_dt, b_neg_a_dt = coefs[1], coefs[0]   # dr = (b a - a r) dt
    a = -a_dt / dt
    b = -b_neg_a_dt / a_dt
    residual_var = np.var(dr - X @ coefs, ddof=2)
    sigma = math.sqrt(residual_var / dt)
    return dict(a=float(a), b=float(b), sigma=float(sigma))


def cir_bond_price(r0, a, b, sigma, t, T):
    """CIR zero-coupon bond price."""
    tau = T - t
    if tau <= 0:
        return 1.0
    gamma = math.sqrt(a**2 + 2*sigma**2)
    den = (gamma + a) * (math.exp(gamma*tau) - 1) + 2*gamma
    B = 2*(math.exp(gamma*tau) - 1) / den
    A = (2*gamma*math.exp((a + gamma)*tau/2) / den) ** (2*a*b/sigma**2)
    return A * math.exp(-B * r0)


# Examples
print("Vasicek P(0, 1):", vasicek_bond_price(0.03, a=0.1, b=0.04, sigma=0.01, t=0.0, T=1.0))
print("Vasicek P(T, T):", vasicek_bond_price(0.03, a=0.1, b=0.04, sigma=0.01, t=1.0, T=1.0))  # = 1
print("CIR P(0, 1):", cir_bond_price(0.03, a=0.1, b=0.04, sigma=0.05, t=0.0, T=1.0))
```

## 6. 注意点 / 典型的なミス

- **均衡モデルはイールドカーブに厳密にフィットしない**: パラメータが小さいほどモデルと市場の乖離が大きくなる。実務での価格付けには Ch.32 の無裁定モデル（Hull-White など）を使う。
- **Vasicek は負金利を許容**: ガウス過程のため $r < 0$ が起こりうる。現在の低金利環境では現実的だが、伝統的には欠陥とみなされていた。
- **CIR の非負性条件**: フェラー条件 $2ab > \sigma^2$ が満たされないと $r$ がゼロに触れることがある。MC シミュレーションでは吸収境界（$\max(r,0)$）を必ず適用する。
- **Rendleman-Bartter は平均回帰なし**: 株価モデルと同じ構造で金利モデルとして不適切。実務・学術ともに使用されない。
- **過去データでの推定 = 実世界パラメータ**: OLS キャリブレーションで得られる $a, b$ は現実世界のもの。リスク中立世界でのパラメータ（価格付けに使う）への変換にはリスクプレミアム $\lambda$ の推定が別途必要。Hull の実例では $\lambda = -0.175$ が最適値として得られた（Table 31.1）。
- **$B(t,T)$ の代替デュレーション**: Vasicek/CIR では通常の Modified Duration の代わりに $\hat{D} = B(t,T)$ を使う（ショートレート変化に対する感応度）。イールド変化に対する通常のデュレーションより小さくなる（平均回帰効果）。

## 7. 関連トピック

- See: [topics/ir_derivatives.md](../topics/ir_derivatives.md)
- **Ch.32**: 無裁定モデル（No-Arbitrage Models）— Hull-White は Vasicek を拡張し初期イールドカーブに正確にフィットする。
- **Ch.33**: HJM フレームワーク・LIBOR Market Model（フォワードレートの直接モデリング）。
- **Ch.28**: マルチンゲールと測度変換（リスク中立世界 vs 現実世界の関係）。
- **Ch.29**: キャップ・フロア・スワップションのブラックモデル（本章のモデルが置き換える標準モデル）。
