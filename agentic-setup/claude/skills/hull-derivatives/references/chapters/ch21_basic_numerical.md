# Ch.21 Basic Numerical Procedures

> **Source**: Hull 11e, Chapter 21 (pp. 470-513). Paraphrased summary for personal use.

## 1. 要点

- 解析解が存在しない派生商品の評価に使う3大数値手法は、**二項・三項ツリー**、**モンテカルロシミュレーション**、**有限差分法**である。
- ツリー法はアメリカンオプションや早期行使付き商品に向く。各ノードで「継続価値 vs 行使価値」を比較しながら後ろ向きに遡ることで早期行使境界を自然に捉える。
- モンテカルロはパス依存（アジアン、ルックバック等）や多変数ペイオフに強いが、アメリカンオプションには直接使えず計算コストが高い。LSM（Longstaff-Schwartz）が代表的な回避策。
- 有限差分法（implicit / Crank-Nicolson）はBSM偏微分方程式を差分方程式に変換して解く。$Z = \ln S$ 変換で係数を定数化でき、三項ツリーと等価な構造を持つ。
- **分散削減技法**（対称変量、コントロール変量、重点サンプリング、準乱数列）で MC の収束を大幅に改善できる。

## 2. キー用語

- **CRR (Cox-Ross-Rubinstein) ツリー**: $u = e^{\sigma\sqrt{\Delta t}}$, $d=1/u$ を用いる再結合二項ツリー
- **コントロール変量法**: 解析解既知の欧州オプション誤差を使ってアメリカンオプション誤差を補正する手法
- **三項ツリー**: 各ノードから上・同・下の3方向に分岐する再結合ツリー; 明示的有限差分法と等価
- **モンテカルロシミュレーション**: リスク中立世界でパスをサンプリングし割引期待ペイオフを推定する手法
- **対称変量法 (Antithetic variates)**: 乱数 $\epsilon$ と $-\epsilon$ を対にして分散を削減する手法
- **重点サンプリング (Importance sampling)**: 深くアウト・オブ・ザ・マネーで無意味なパスを排除し重要な領域に集中させる手法
- **準乱数列 (Quasi-random / Low-discrepancy sequences)**: Sobol, Halton など。確率空間を一様にカバーし誤差を $O(1/N)$ に改善
- **暗示的有限差分法 (Implicit FD)**: 時刻 $t$ の3値と時刻 $t+\Delta t$ の1値を連立するスキーム; 無条件安定
- **陽的有限差分法 (Explicit FD)**: 時刻 $t+\Delta t$ の3値から時刻 $t$ の1値を直接計算; 三項ツリーと等価だが条件付き安定
- **Crank-Nicolson法**: 暗示的と陽的の平均; 2次精度で無条件安定
- **Longstaff-Schwartz (LSM)**: 回帰ベースの最小二乗MCでバミューダン/アメリカンオプションを評価
- **成長因子 (growth factor)**: $a = e^{(r-q)\Delta t}$; ツリーのリスク中立上昇確率 $p=(a-d)/(u-d)$ の分子
- **後退帰納法 (Backward induction)**: ツリーの末端から始点に向かって期待割引価値を逐次計算する方法

## 3. 主要公式

### CRR 二項ツリーパラメータ

$$
u = e^{\sigma\sqrt{\Delta t}}, \quad d = e^{-\sigma\sqrt{\Delta t}} = 1/u, \quad a = e^{(r-q)\Delta t}
$$

$$
p = \frac{a - d}{u - d}
$$

<!-- Hull eq. (21.4)–(21.7) -->

- $p$: リスク中立上昇確率
- $q$: 連続配当利回り（通貨オプションなら外国金利、先物オプションなら $q=r$）

---

### コントロール変量による補正 (Control Variate)

$$
f^* = f_{\mathrm{Am,tree}} + \bigl(f_{\mathrm{Eu,BSM}} - f_{\mathrm{Eu,tree}}\bigr)
$$

<!-- Hull §21.3 Control Variate Technique -->

- $f_{\mathrm{Am,tree}}$: ツリーで計算したアメリカンオプション価格
- $f_{\mathrm{Eu,BSM}}$: BSM解析値（既知）
- $f_{\mathrm{Eu,tree}}$: 同ツリーで計算した欧州版価格
- ツリーの系統誤差が Am/Eu 両方に同程度含まれるという仮定に基づく

---

### 三項ツリーパラメータ

$$
u = e^{\sigma\sqrt{3\Delta t}}, \quad d = 1/u, \quad m = 1 \; (\text{中央})
$$

$$
p_u = \sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}, \quad
p_m = \frac{2}{3}, \quad
p_d = -\sqrt{\frac{\Delta t}{12\sigma^2}}\!\left(r - q - \frac{\sigma^2}{2}\right) + \frac{1}{6}
$$

<!-- Hull §21.4, Figure 21.12 -->

- $p_u + p_m + p_d = 1$ を確認; パラメータが極端だと $p_u$ や $p_d$ が負になりうる（要注意）
- 三項ツリーは陽的有限差分法と等価（Hull §21.8）

---

### 時変パラメータ ($r(t)$, $q(t)$) への対応

$$
a = e^{[f(t) - g(t)]\Delta t}
$$

<!-- Hull eq. (21.11) -->

- $f(t)$: 時刻 $t$ から $t+\Delta t$ のフォワード金利
- $g(t)$: 同期間のフォワード配当利回り（または $r_f$）
- $u$, $d$ は $a$ に依存しないため木の形状は変わらない; $p$ のみ各列で異なる

---

### GBM 以外の確率過程のツリー化

$Z = \ln S$ と変数変換すると、$Z$ の分散は定数 $\sigma^2 \Delta t$ になる（GBM の性質）。  
ツリーを $Z$ の等間隔グリッド上に組み直すことで係数が $j$ に依らず定数になる。  
$\Delta Z = \sigma\sqrt{3\Delta t}$ に設定すると三項ツリーのパラメータと一致する。

---

### モンテカルロ — 欧州オプション

GBM の対数正規離散化（精度が高い）:

$$
S(t+\Delta t) = S(t)\exp\!\left[\left(\hat\mu - \frac{\sigma^2}{2}\right)\Delta t + \sigma\epsilon\sqrt{\Delta t}\right]
$$

<!-- Hull eq. (21.16) -->

リスク中立世界では $\hat\mu = r - q$。終端のみでよければ $N$ 通り同時生成:

$$
S_T^{(i)} = S_0 \exp\!\left[\left(r - q - \frac{\sigma^2}{2}\right)T + \sigma\epsilon_i\sqrt{T}\right]
$$

価格推定量と標準誤差:

$$
\hat{f} = e^{-rT}\frac{1}{N}\sum_{i=1}^{N} f_T^{(i)}, \qquad
\mathrm{SE} = \frac{s}{\sqrt{N}}
$$

<!-- Hull §21.6 Number of Trials -->

- $s$: 割引ペイオフ $\{e^{-rT}f_T^{(i)}\}$ の標本標準偏差
- 95% CI: $\hat f \pm 1.96 \cdot s/\sqrt{N}$

---

### 分散削減技法

**対称変量 (Antithetic variates)**:

$$
\bar{f} = \frac{f_1(\epsilon) + f_2(-\epsilon)}{2}
$$

最終推定値は $\bar{f}$ の平均; 標準誤差 $= \bar\omega/\sqrt{M}$（$\bar\omega$ は $\bar f$ の標準偏差）。

**コントロール変量 (MC版)**:

$$
f_A = f_A^* - f_B^* + f_B
$$

<!-- Hull eq. (21.20) -->

同一乱数ストリームで類似商品 B（解析解 $f_B$ あり）を同時評価し誤差を相殺。

**重点サンプリング**: 深くOTMのオプションで、ゼロペイオフを生む無駄なパスを排除する。  
**準乱数列 (Sobol, Halton)**: 標準誤差が $O(1/\sqrt{N})$ から実効的に $O(1/N)$ 近くに改善。

---

### 有限差分法 — BSM PDE

オプション価格 $f$ が満たすBSM PDE（配当利回り $q$）:

$$
\frac{\partial f}{\partial t} + (r-q)S\frac{\partial f}{\partial S} + \frac{1}{2}\sigma^2 S^2\frac{\partial^2 f}{\partial S^2} = rf
$$

<!-- Hull eq. (21.21) -->

---

### $Z = \ln S$ 変換後の定係数 PDE

$$
\frac{\partial f}{\partial t} + \left(r - q - \frac{\sigma^2}{2}\right)\frac{\partial f}{\partial Z} + \frac{1}{2}\sigma^2\frac{\partial^2 f}{\partial Z^2} = rf
$$

係数が $S$（$j$）に依らないため、グリッド上の係数 $\alpha_j, \beta_j, \gamma_j$ が一定になる利点がある。

---

### 暗示的有限差分スキーム（$S$ グリッド）

$$
a_j f_{i,j-1} + b_j f_{i,j} + c_j f_{i,j+1} = f_{i+1,j}
$$

<!-- Hull eq. (21.27) -->

$$
a_j = \tfrac{1}{2}(r-q)j\,\Delta t - \tfrac{1}{2}\sigma^2 j^2 \Delta t
$$
$$
b_j = 1 + \sigma^2 j^2\Delta t + r\,\Delta t
$$
$$
c_j = -\tfrac{1}{2}(r-q)j\,\Delta t - \tfrac{1}{2}\sigma^2 j^2 \Delta t
$$

各時刻ステップで $(M-1)\times(M-1)$ 三重対角連立方程式を解く。無条件安定。

---

### 陽的有限差分スキーム

$$
f_{i,j} = a_j^* f_{i+1,j-1} + b_j^* f_{i+1,j} + c_j^* f_{i+1,j+1}
$$

<!-- Hull eq. (21.34) -->

三項ツリーの後退帰納と等価。安定条件（概略）:

$$
\Delta t \le \frac{(\Delta S)^2}{\sigma^2 S^2}
\quad \Leftrightarrow \quad
\Delta t \le \frac{(\Delta Z)^2}{\sigma^2} \quad (\text{$Z$グリッドの場合})
$$

$j^2$ に比例する係数のため大きな $S$ で陽的スキームが負の確率を生む場合あり。

---

### Crank-Nicolson スキーム

暗示的スキームと陽的スキームの平均:

$$
\frac{f_{i+1,j} - f_{i,j}}{\Delta t} = \frac{1}{2}\left[\text{(implicit terms at }i\text{)} + \text{(explicit terms at }i+1\text{)}\right]
$$

2次精度で無条件安定。バリアや不連続ペイオフ近傍では振動が生じることがある（Rannacher smoothing で軽減）。

---

### ツリーからのグリーク計算

$$
\Delta = \frac{f_{1,1} - f_{1,0}}{S_0 u - S_0 d}
$$

<!-- Hull eq. (21.8) -->

$$
\Gamma = \frac{\left[(f_{2,2}-f_{2,1})/(S_0u^2 - S_0)\right] - \left[(f_{2,1}-f_{2,0})/(S_0 - S_0d^2)\right]}{h}, \quad h = \tfrac{1}{2}(S_0u^2 - S_0d^2)
$$

<!-- Hull eq. (21.9) -->

$$
\Theta = \frac{f_{2,1} - f_{0,0}}{2\Delta t}
$$

<!-- Hull eq. (21.10) -->

Vega, Rho: $\sigma$ または $r$ を微小変動させて同一ステップ数のツリーを再構築し差分を取る。

---

## 4. アルゴリズム / 手順

### 手順1: 三項ツリーによるオプション価格計算

1. パラメータ計算: $u = e^{\sigma\sqrt{3\Delta t}}$, $d = 1/u$, $p_u$, $p_m$, $p_d$（上記公式）
2. 終端ノード（ステップ $N$）の価格格子 $S_j = S_0 u^j$（$j = -N, \ldots, N$）を構築
3. 終端ペイオフを設定: コール $= \max(S_j - K, 0)$、プット $= \max(K - S_j, 0)$
4. 後退帰納: ステップ $N$ から $1$ まで逆向きに
   - 継続価値 $= e^{-r\Delta t}(p_u V_{j+1} + p_m V_j + p_d V_{j-1})$
   - アメリカンの場合: $V_j = \max(\text{継続価値},\; \text{行使価値})$
5. ステップ0の中央ノード（$j=0$）の価値がオプション価格

---

### 手順2: モンテカルロ（欧州オプション）

1. パス数 $N$（例 $10^5$）、乱数シードを設定
2. $\epsilon_i \sim N(0,1)$ を $N$ 個生成
3. 終端株価: $S_T^{(i)} = S_0 \exp[(r-q-\sigma^2/2)T + \sigma\sqrt{T}\,\epsilon_i]$
4. ペイオフ計算: $h_i = \max(S_T^{(i)} - K, 0)$（コール）
5. 割引平均: $\hat f = e^{-rT}\bar h$; 標準誤差 $= e^{-rT} s / \sqrt{N}$

---

### 手順3: パス依存オプション（アジアンコール）の MC

1. 各パスで $N_{\rm step}$ ステップの離散化株価路を生成（式 (21.16) を繰り返し適用）
2. パス $i$ のペイオフ: $h_i = \max(\bar S^{(i)} - K, 0)$（$\bar S$ = パス上の平均株価）
3. 割引平均で価格を推定

---

### 手順4: 暗示的有限差分法（欧州プット）

1. グリッド設定: $S_{\max} = 3\max(S_0, K)$, $\Delta S = S_{\max}/M$, $\Delta t = T/N$
2. 終端条件 ($t=T$): $f_{N,j} = \max(K - j\Delta S, 0)$
3. 境界条件: $f_{i,0} = K$ (プット深いITM),  $f_{i,M} = 0$ ($S=S_{\max}$)
4. 係数 $a_j, b_j, c_j$ を計算
5. $i = N-1, N-2, \ldots, 0$ の順に三重対角連立方程式 $Af_{i,\cdot} = f_{i+1,\cdot}$ を解く
   - アメリカンの場合は各 $j$ で $f_{i,j} \leftarrow \max(f_{i,j},\; K - j\Delta S)$
6. $S_0$ に対応するグリッド点（または線形補間）から価格を読み取る

---

### 手順5: Crank-Nicolson 法

1. 手順4と同じグリッド・境界条件
2. 各時刻ステップで暗示的スキームと陽的スキームの右辺を平均した方程式系を構成
3. 同じ三重対角ソルバーで解く（暗示的と同等コスト、精度は2次）

---

### 手順6: Longstaff-Schwartz (LSM) — アメリカンオプションの MC

1. $N_{\rm path}$ 本のパスをシミュレーション（式 (21.16) を各行使日まで適用）
2. 満期の行使価値でノード価値を初期化
3. 行使日を満期側から逐次遡る:
   - イン・ザ・マネーのパス群のみ抽出
   - $S$ の多項式基底（例: $1, S, S^2$）に対し、その後の割引継続価値を目的変数として OLS 回帰
   - 回帰で得た継続価値推定値 $\hat C$ と即時行使価値を比較; $E > \hat C$ なら行使フラグを立てる
4. 各パスの最初の行使ポイントを特定し、割引ペイオフの平均を価格とする

---

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


# 1) Trinomial tree (European or American option)
def trinomial(S0, K, r, q, sigma, T, N, kind='call', american=False):
    """Trinomial tree pricing for European or American vanilla option."""
    dt = T / N
    u = math.exp(sigma * math.sqrt(3.0 * dt))
    d = 1.0 / u
    sig2 = sigma * sigma
    p_u = math.sqrt(dt / (12.0 * sig2)) * (r - q - sig2 / 2.0) + 1.0 / 6.0
    p_m = 2.0 / 3.0
    p_d = -math.sqrt(dt / (12.0 * sig2)) * (r - q - sig2 / 2.0) + 1.0 / 6.0
    disc = math.exp(-r * dt)
    # Terminal nodes: index j from -N to +N; S = S0 * u**j
    idx = np.arange(-N, N + 1)
    S = S0 * (u ** idx)
    sign = 1.0 if kind == 'call' else -1.0
    V = np.maximum(sign * (S - K), 0.0)
    for step in range(N, 0, -1):
        S = S0 * (u ** np.arange(-step + 1, step))
        V_new = disc * (p_u * V[2:] + p_m * V[1:-1] + p_d * V[:-2])
        if american:
            intrinsic = np.maximum(sign * (S - K), 0.0)
            V_new = np.maximum(V_new, intrinsic)
        V = V_new
    return float(V[0])


# 2) Monte Carlo for European call (with antithetic variates)
def mc_european_call(S0, K, r, sigma, T, n_paths=100_000, rng=None):
    """MC European call; returns (price, std_error)."""
    rng = rng or np.random.default_rng(0)
    Z = rng.standard_normal(n_paths // 2)
    # Antithetic: pair Z with -Z
    Z_both = np.concatenate([Z, -Z])
    ST = S0 * np.exp((r - 0.5 * sigma ** 2) * T + sigma * math.sqrt(T) * Z_both)
    payoff = np.maximum(ST - K, 0.0)
    disc = math.exp(-r * T) * payoff
    return disc.mean(), disc.std(ddof=1) / math.sqrt(len(disc))


# 3) Implicit finite-difference for European put on BSM (Z = ln S grid)
def implicit_fd_put(S0, K, r, sigma, T, S_max=None, M=200, N=200):
    """Implicit FD scheme on uniform S grid — unconditionally stable."""
    S_max = S_max or 3.0 * max(S0, K)
    dS = S_max / M
    dt = T / N
    j = np.arange(M + 1, dtype=float)
    S = j * dS
    V = np.maximum(K - S, 0.0)
    # Tri-diagonal coefficients (interior j = 1..M-1)
    a = 0.5 * dt * (sigma ** 2 * j ** 2 - r * j)
    b = 1.0 + dt * (sigma ** 2 * j ** 2 + r)
    c = -0.5 * dt * (sigma ** 2 * j ** 2 + r * j)
    A = (np.diag(b[1:-1])
         + np.diag(a[2:-1], -1)
         + np.diag(c[1:-2], 1))
    for _ in range(N):
        rhs = V[1:-1].copy()
        # Boundary adjustments
        rhs[0] -= a[1] * V[0]
        rhs[-1] -= c[-2] * V[-1]
        V[1:-1] = np.linalg.solve(A, rhs)
        V[0] = K          # deep ITM: put ~ K at S=0
        V[-1] = 0.0       # deep OTM: put ~ 0 at S_max
    return float(np.interp(S0, S, V))


# 4) LSM (Longstaff-Schwartz) for American put
def lsm_american_put(S0, K, r, sigma, T, n_steps=50, n_paths=50_000, rng=None):
    """Least-squares MC for American put; polynomial basis degree 2."""
    rng = rng or np.random.default_rng(42)
    dt = T / n_steps
    disc = math.exp(-r * dt)
    # Simulate paths
    Z = rng.standard_normal((n_steps, n_paths))
    lnS = np.full(n_paths, math.log(S0))
    paths = np.empty((n_steps + 1, n_paths))
    paths[0] = S0
    for t in range(n_steps):
        lnS += (r - 0.5 * sigma ** 2) * dt + sigma * math.sqrt(dt) * Z[t]
        paths[t + 1] = np.exp(lnS)
    # Backward induction
    cashflow = np.maximum(K - paths[-1], 0.0)
    for t in range(n_steps - 1, 0, -1):
        cashflow *= disc          # discount one step
        itm = paths[t] < K        # in-the-money paths
        if itm.sum() < 5:
            continue
        X = paths[t, itm]
        Y = cashflow[itm]
        # Polynomial basis: [1, S, S^2]
        A = np.column_stack([np.ones_like(X), X, X ** 2])
        beta, _, _, _ = np.linalg.lstsq(A, Y, rcond=None)
        continuation = A @ beta
        exercise = K - X
        early = exercise > continuation
        idx = np.where(itm)[0][early]
        cashflow[idx] = exercise[early]
    return float(disc * cashflow.mean())


# Example (reference values)
if __name__ == '__main__':
    S0, K, r, q, sigma, T = 100, 100, 0.05, 0.0, 0.20, 1.0
    print(f"Trinomial Euro call : {trinomial(S0, K, r, q, sigma, T, 200, 'call', False):.4f}")
    print(f"Trinomial Amer put  : {trinomial(S0, K, r, q, sigma, T, 200, 'put',  True):.4f}")
    price, se = mc_european_call(S0, K, r, sigma, T)
    print(f"MC Euro call        : {price:.4f}  (SE={se:.5f})")
    print(f"Implicit FD put     : {implicit_fd_put(S0, K, r, sigma, T):.4f}")
    print(f"LSM Amer put        : {lsm_american_put(S0, K, r, sigma, T):.4f}")
```

## 6. 注意点 / 典型的なミス

- **三項ツリーの確率の符号**: $p_u$ や $p_d$ が負になるのは $r-q-\sigma^2/2$ が大きく、$\Delta t$ が粗い場合。確率が負だと後退帰納が発散する。$\Delta t$ を細かくするか CRR の別ブランチ方式 ($p=0.5$) に切り替える。
- **MCの誤差収束は $1/\sqrt{N}$**: 精度を10倍にするにはパス数を100倍必要。準乱数や分散削減技法を使わないと実用コストが高い。
- **陽的 FD の条件付き安定性**: $1 - \sigma^2 j^2 \Delta t < 0$ になる大きい $j$（株価が高い領域）で負の確率が生じ、数値が発散する。$S$ グリッドではなく $Z = \ln S$ グリッド + $\Delta Z = \sigma\sqrt{3\Delta t}$ を使えば係数が $j$ に依らず安定しやすい。
- **Crank-Nicolson のバリア/不連続近傍振動**: バリアオプションやデジタルのような不連続ペイオフでは Crank-Nicolson が振動することがある。Rannacher 法（最初の数ステップを暗示的スキームで実施）で軽減できる。
- **LSM の基底選択**: 多項式次数を高くしすぎると過学習になり継続価値推定が悪化する。一般に $S$ の2〜3次の多項式で十分。行使価値がゼロのパスはOLSに含めないこと（ITMのみで回帰）。
- **コントロール変量法の一貫性**: ツリーで Am と Eu を計算するとき、まったく同じツリー（同じ $N$、同じ $\Delta t$）を使うこと。ツリーを変えると誤差の性質が変わり補正が機能しない。
- **有限差分の境界条件**: $S=0$ ではプット $= K$（割引不要の場合と要割引の場合があるので問題設定に注意）、$S=S_{\max}$ ではプット $= 0$、コール $= S_{\max} - Ke^{-rT}$ を使うことが多い。
- **モンテカルロのアメリカン不適合**: 通常の MC はパスを前向きにしか進められないため早期行使境界を捉えられない。LSM や premiumdecomposition 等の特殊手法が必要。

## 7. 関連トピック

- See: [topics/numerical_methods.md](../topics/numerical_methods.md), [topics/binomial.md](../topics/binomial.md)
- Ch.13 (Binomial Trees — 基礎的な二項ツリー)
- Ch.19 (The Greek Letters — ツリーとMCからのグリーク計算の詳細)
- Ch.26 (Exotic Options — パス依存商品のMC適用例)
- Ch.27 (More on Models and Numerical Procedures — 高度数値手法、LSMの拡張、ジャンプ拡散へのツリー適用等)
