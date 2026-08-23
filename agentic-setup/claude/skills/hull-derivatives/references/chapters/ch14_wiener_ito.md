# Ch.14 Wiener Processes and Itô's Lemma

> **Source**: Hull 11e, Chapter 14 (pp. 316-337). Paraphrased summary for personal use.

## 1. 要点

- 株価などの連続時間確率過程は **マルコフ性** を持つ：将来の予測に必要なのは現在値だけであり、過去の経路は不要。
- 最も基本的な確率過程が **ウィーナー過程**（ブラウン運動）。ドリフト 0・分散レート 1.0/年で、不確実性は時間の平方根に比例して増大する。
- **一般化ウィーナー過程** ($dx = a\,dt + b\,dz$) および **伊藤過程** ($dx = a(x,t)\,dt + b(x,t)\,dz$) はウィーナー過程の拡張。
- 株価の標準モデルは **幾何ブラウン運動 (GBM)**：$dS = \mu S\,dt + \sigma S\,dz$。これにより株価の対数収益率が正規分布に従い、株価自体は対数正規分布に従う。
- **伊藤の補題** は、確率変数の関数が従う確率過程を求める公式。$(\Delta x)^2 \approx b^2 \Delta t$ という確率微分特有の事実（通常微分では $(\Delta x)^2 \to 0$）が補題の核心。

## 2. キー用語

- **確率過程 (stochastic process)**: 時間とともに不確実に変化する変数の確率論的な記述。
- **マルコフ過程 (Markov process)**: 将来の値の分布が現在値のみに依存し、過去の経路によらない確率過程。
- **ウィーナー過程 / ブラウン運動 (Wiener process / Brownian motion)**: ドリフト 0・分散レート 1.0 のマルコフ連続時間確率過程。
- **ドリフトレート (drift rate)**: 単位時間あたりの期待変化量。
- **分散レート (variance rate)**: 単位時間あたりの分散。
- **一般化ウィーナー過程 (generalized Wiener process)**: 定数ドリフト $a$・定数分散レート $b^2$ の確率過程 $dx = a\,dt + b\,dz$。
- **伊藤過程 (Itô process)**: ドリフトと拡散係数が $x$ と $t$ の関数である確率過程 $dx = a(x,t)\,dt + b(x,t)\,dz$。
- **幾何ブラウン運動 (GBM)**: 株価の標準モデル。期待収益率と変動が株価水準に比例する伊藤過程。
- **伊藤の補題 (Itô's lemma)**: 伊藤過程に従う変数 $x$ の関数 $G(x,t)$ が従う確率過程を与える公式。
- **対数正規分布 (lognormal distribution)**: GBM に従う株価 $S_T$ の分布。$\ln S_T$ が正規分布に従う。
- **フラクショナルブラウン運動 (fractional Brownian motion)**: ハースト指数 $H$ によって自己相関を持たせた一般化ブラウン運動。$H=0.5$ が通常の Wiener 過程。ラフボラティリティモデルで使用される。

## 3. 主要公式

### ウィーナー過程の増分

$$
\Delta z = \epsilon \sqrt{\Delta t}, \quad \epsilon \sim \phi(0,1)
$$

- $\Delta z$: 微小時間 $\Delta t$ における $z$ の変化量
- $E[\Delta z] = 0$, $\text{Var}[\Delta z] = \Delta t$
- 任意の異なる時間区間の $\Delta z$ は独立（マルコフ性）

<!-- Hull eq. (14.1) -->

長期変化：$z(T) - z(0) = \sum_{i=1}^{N} \epsilon_i \sqrt{\Delta t}$, $N = T/\Delta t$ として、
$z(T) - z(0) \sim \phi(0, T)$

<!-- Hull eq. (14.2) -->

### 一般化ウィーナー過程

$$
dx = a\,dt + b\,dz
$$

- $a$: 定数ドリフトレート（単位時間あたりの期待変化量）
- $b$: 定数拡散係数（分散レート $b^2$）
- 離散近似：$\Delta x = a\,\Delta t + b\,\epsilon\sqrt{\Delta t}$
- 期間 $T$ の変化：$x(T) - x(0) \sim \phi(aT,\, b^2 T)$

<!-- Hull eq. (14.3) -->

### 伊藤過程

$$
dx = a(x,t)\,dt + b(x,t)\,dz
$$

<!-- Hull eq. (14.4) -->

### 幾何ブラウン運動（GBM）—— 株価モデル

$$
dS = \mu S\,dt + \sigma S\,dz
$$

あるいは等価に

$$
\frac{dS}{S} = \mu\,dt + \sigma\,dz
$$

<!-- Hull eq. (14.6) -->

- $\mu$: 期待収益率（リスク中立世界では無リスク利子率 $r$）
- $\sigma$: ボラティリティ（株価の標準偏差レート）

### 離散化 GBM

$$
\frac{\Delta S}{S} = \mu\,\Delta t + \sigma\,\epsilon\sqrt{\Delta t}
$$

<!-- Hull eq. (14.7) -->

短期間の株価変化率は近似的に $\phi(\mu\,\Delta t,\, \sigma^2\,\Delta t)$ に従う。

<!-- Hull eq. (14.9) -->

### 伊藤の補題

$x$ が伊藤過程 $dx = a(x,t)\,dt + b(x,t)\,dz$ に従うとき、
$G(x,t)$ は次の伊藤過程に従う：

$$
dG = \left(\frac{\partial G}{\partial x}\,a + \frac{\partial G}{\partial t} + \frac{1}{2}\frac{\partial^2 G}{\partial x^2}\,b^2\right)dt + \frac{\partial G}{\partial x}\,b\,dz
$$

<!-- Hull eq. (14.12) -->

**直観**：通常の微分 $dG \approx \frac{\partial G}{\partial x}dx + \frac{\partial G}{\partial t}dt$ に対し、確率微分では $(\Delta x)^2 \approx b^2\,\epsilon^2\,\Delta t \to b^2\,\Delta t$（$\epsilon^2$ の期待値が 1）という「余分な項」が現れる。

### $\ln S$ への適用（対数正規性の導出）

$G = \ln S$ とおき、伊藤の補題を $dS = \mu S\,dt + \sigma S\,dz$ に適用：

$$
\partial G/\partial S = 1/S, \quad \partial^2 G/\partial S^2 = -1/S^2, \quad \partial G/\partial t = 0
$$

$$
d(\ln S) = \left(\mu - \frac{\sigma^2}{2}\right)dt + \sigma\,dz
$$

<!-- Hull eq. (14.17) -->

$\mu$ と $\sigma$ が定数のとき $\ln S$ は一般化ウィーナー過程に従い：

$$
\ln S_T - \ln S_0 \sim \phi\!\left[\left(\mu - \frac{\sigma^2}{2}\right)T,\; \sigma^2 T\right]
$$

<!-- Hull eq. (14.18) -->

すなわち $\ln S_T \sim \phi\!\left[\ln S_0 + \left(\mu - \frac{\sigma^2}{2}\right)T,\; \sigma^2 T\right]$

<!-- Hull eq. (14.19) -->

### 期待値と分散

$$
E(S_T) = S_0\,e^{\mu T}, \qquad \text{Var}(S_T) = S_0^2\,e^{2\mu T}\!\left(e^{\sigma^2 T} - 1\right)
$$

**$\mu$ と $\mu - \sigma^2/2$ の違い**：$\mu$ は期待収益率（算術平均的）、$\mu - \sigma^2/2$ は対数収益率の期待値（連続複利的）。
ボラティリティが高いほど対数収益率の期待値が下がる（Jensen の不等式）。例：$\mu=0.15$, $\sigma=0.20$ なら対数収益率の期待値は $0.15 - 0.02 = 0.13$。

## 4. アルゴリズム / 手順

### 1. GBM パスのモンテカルロシミュレーション（exact log-Euler 法）

1. パラメータ設定：$S_0$, $\mu$, $\sigma$, $T$, ステップ数 $N$, パス数 $M$。
2. $\Delta t = T / N$ を計算。
3. 各ステップ・各パスについて $\epsilon \sim \phi(0,1)$ をサンプリング。
4. 対数収益を計算：$\Delta \ln S_i = (\mu - \sigma^2/2)\,\Delta t + \sigma\,\epsilon\sqrt{\Delta t}$
5. 累積して $\ln S_{t_i} = \ln S_0 + \sum_{j=1}^{i} \Delta \ln S_j$
6. 指数をとって株価 $S_{t_i} = \exp(\ln S_{t_i})$ を得る。
7. 最終価格 $S_T$ の分布から $E[S_T]$, $\text{Var}[S_T]$ を推定し理論値と比較検証。

> 注：naive Euler-Maruyama 法（$\Delta S = \mu S\,\Delta t + \sigma S\,\epsilon\sqrt{\Delta t}$）は近似誤差が累積する。上記の exact log 法は $S_T$ の分布を正確に再現する。

### 2. 伊藤の補題のシミュレーション検証

1. $S$ と $G = \ln S$ の双方をシミュレーション。
2. $d(\ln S)$ のサンプル平均・分散と理論値 $(\mu - \sigma^2/2)\,\Delta t$, $\sigma^2\,\Delta t$ を比較。
3. 単純に $\Delta(\ln S) \approx \Delta S / S$（通常微分）と $d(\ln S) = (\mu - \sigma^2/2)\,dt + \sigma\,dz$（伊藤）のバイアス差を確認。

## 5. Python reference

```python
import numpy as np


def simulate_gbm_paths(S0, mu, sigma, T, n_steps, n_paths, rng=None):
    """Simulate GBM stock paths using the exact log-Euler method.

    Returns array of shape (n_paths, n_steps + 1) where column 0 = S0.
    """
    rng = rng or np.random.default_rng(42)
    dt = T / n_steps
    Z = rng.standard_normal(size=(n_paths, n_steps))
    # Exact solution: ln S_t = ln S_0 + (mu - sigma^2/2)*t + sigma*W_t
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
    log_paths = np.log(S0) + np.cumsum(log_returns, axis=1)
    paths = np.column_stack([np.full((n_paths, 1), S0), np.exp(log_paths)])
    return paths


def gbm_theory(S0, mu, sigma, T):
    """Theoretical E[S_T] and Var[S_T] under GBM."""
    e_st = S0 * np.exp(mu * T)
    var_st = S0**2 * np.exp(2 * mu * T) * (np.exp(sigma**2 * T) - 1)
    return e_st, var_st


# --- Verification ---
S0, mu, sigma, T = 100.0, 0.10, 0.20, 1.0
paths = simulate_gbm_paths(S0, mu, sigma, T, n_steps=252, n_paths=100_000)
ST = paths[:, -1]

e_theory, var_theory = gbm_theory(S0, mu, sigma, T)
print(f"E[S_T]  sim={ST.mean():.4f}  theory={e_theory:.4f}")
print(f"Var[S_T] sim={ST.var():.2f}  theory={var_theory:.2f}")

# Verify lognormal property: ln S_T ~ N(ln S0 + (mu - sigma^2/2)*T, sigma^2*T)
ln_mean_theory = np.log(S0) + (mu - 0.5 * sigma**2) * T
ln_var_theory = sigma**2 * T
print(f"E[ln S_T] sim={np.log(ST).mean():.4f}  theory={ln_mean_theory:.4f}")
print(f"Var[ln S_T] sim={np.log(ST).var():.4f}  theory={ln_var_theory:.4f}")
```

## 6. 注意点 / 典型的なミス

- **$\mu$ と $\mu - \sigma^2/2$ の混同**：「期待収益率 10%」から「1年後の期待対数収益」を $0.10T$ と誤計算しがち。正しくは $(\mu - \sigma^2/2)T$。ボラティリティが高いほどこの差（分散ドラッグ）が大きい。
- **naive Euler と exact log の差**：$\Delta S / S = \mu\Delta t + \sigma\epsilon\sqrt{\Delta t}$ を繰り返すと $S_T$ の期待値が理論値からずれる（特に大きな $\Delta t$、高い $\sigma$）。必ず exact log-Euler を使う。
- **ウィーナー過程の分散は加法的、標準偏差は非加法的**：2年間の標準偏差は $\sqrt{2}$ であり 2 ではない。
- **伊藤の補題の $\frac{1}{2}\frac{\partial^2 G}{\partial x^2}b^2$ 項の欠落**：通常微分の感覚で適用すると $G = \ln S$ から $dG = dS/S = \mu\,dt + \sigma\,dz$ と誤る。正しくは $d(\ln S) = (\mu - \sigma^2/2)\,dt + \sigma\,dz$。
- **リスク中立世界での $\mu$**：BSM モデルでは $\mu$ を無リスク利子率 $r$ に置き換える（リスク中立測度）。現実世界と混同しない。
- **分散の加法性とフラクショナルBM**：通常のBMは $\text{Var}[X(t)-X(s)] = \sigma^2(t-s)$。フラクショナルBMでは $\sigma^2(t-s)^{2H}$（$H \neq 0.5$）となりマルコフ性が失われる。ラフボラティリティ ($H < 0.5$) 適用時は通常のBMベースの公式が使えない。

## 7. 関連トピック

- See: Ch.15 Black-Scholes-Merton モデル（GBM + 伊藤の補題 → BSM 偏微分方程式）
- See: Ch.13 二項ツリー（GBM の離散近似として導出可能）
- See: Ch.21 数値手法（モンテカルロシミュレーションの詳細、Cholesky 分解）
- See: Ch.28 マルチンゲールと測度変換（リスク中立測度、Girsanov の定理）
- See: [topics/stochastic_calculus.md](../topics/stochastic_calculus.md) — 確率微分方程式の概観
