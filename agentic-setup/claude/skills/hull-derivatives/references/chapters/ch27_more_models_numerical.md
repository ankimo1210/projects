# Ch.27 More on Models and Numerical Procedures

> **Source**: Hull 11e, Chapter 27 (pp. 640-669). Paraphrased summary for personal use.

## 1. 要点

- BSM の弱点（ボラティリティスマイル）に対応するため、CEV・Merton ジャンプ拡散・分散ガンマ・確率的ボラティリティ (Heston/SABR) など複数の代替モデルが存在する。
- IVF（局所ボラティリティ）モデルは Dupire 公式でバニラオプション価格を完全に整合するが、エキゾチックオプションへの応用には注意が必要。
- パス依存デリバティブはモンテカルロが基本だが、ツリーで代表値補間を使う方法で American-style にも対応できる。
- コンバーティブル債はデフォルト確率を組み込んだ二項ツリーで評価し、コール・転換を各ノードで判定する。
- バリアオプションのツリー収束改善にはノードをバリア上に配置する適応的手法が有効。
- Longstaff-Schwartz (LSM) 法は MC シミュレーション中で継続価値を多項式回帰で推定し、アメリカンオプションを評価する。

## 2. キー用語

- **CEV (Constant Elasticity of Variance) モデル**: ボラティリティが株価の冪乗に比例する拡散モデル。$\beta < 1$ でエクイティ型スマイルを再現。
- **Levy プロセス**: 連続時間の定常増分確率過程の総称。CEV・ジャンプ拡散・分散ガンマを含む。
- **Merton ジャンプ拡散モデル**: 連続拡散にポアソンジャンプを重ね合わせたモデル。より重い裾を生成。
- **分散ガンマ (Variance-Gamma) モデル**: ガンマ過程で時間変換された純ジャンプモデル。パラメータ $\nu, \sigma, \theta$ で裾の重さと歪みを制御。
- **確率的ボラティリティ**: ボラティリティ自体がランダムウォークに従うモデル群。Hull-White, Heston, SABR など。
- **Heston モデル**: 分散が CIR 過程に従う確率的ボラティリティモデル。半解析的公式を持つ。
- **SABR モデル**: フォワードレート・ボラティリティが連立 SDE に従う確率的ボラティリティモデル。Hagan らの近似式でスマイルを解析的に表現。
- **IVF (Implied Volatility Function) / 局所ボラティリティモデル**: Dupire 方程式でマーケット価格と完全整合する $\sigma(S, t)$ を導出するモデル。
- **ラフボラティリティ**: フラクショナルブラウン運動に基づく確率的ボラティリティモデル。Hurst 指数 0.06-0.20 が実データに適合。
- **Longstaff-Schwartz (LSM) 法**: MC パスで各行使時点の継続価値を最小二乗回帰し、早期行使判定を行う手法。
- **適応的メッシュ (Adaptive Mesh) モデル**: バリア近傍に細かいツリーを埋め込み、収束速度を改善する手法。
- **転換社債 (Convertible Bond)**: 株式転換権（ホルダー）とコール権（発行体）を持つ社債。ハザードレートを組み込んだツリーで評価。
- **内側バリア / 外側バリア**: ツリーのバリア近似で生じる真バリアとの乖離。補間または適応的ツリーで軽減。

## 3. 主要公式

### CEV モデル — リスク中立 SDE

$$
dS = (r - q)\,S\,dt + \sigma S^\beta\,dz
$$

<!-- Hull eq. CEV SDE (§27.1) -->

- $\beta = 1$: 通常の幾何ブラウン運動 (BSM) に帰着
- $\beta < 1$: ボラティリティ $\propto S^{\beta-1}$ は株価下落で上昇 → エクイティ型スマイル（左裾重）
- $\beta > 1$: ボラティリティが株価上昇で上昇 → 右裾重（先物オプションで観察）
- $\alpha = \beta$ と表記する文献もある（Hull は $\beta$、他資料は $\alpha$ を使用）

**ヨーロピアン・コール公式** ($0 < \beta < 1$):

$$
c = S_0 e^{-qT}\bigl[1 - \chi^2(a,\,b+2,\,c)\bigr] - K e^{-rT}\chi^2(c,\,b,\,a)
$$

where

$$
a = \frac{[Ke^{-(r-q)T}]^{2(1-\beta)}}{(1-\beta)^2 \nu},\quad b = \frac{1}{1-\beta},\quad c = \frac{S_0^{2(1-\beta)}}{(1-\beta)^2 \nu}
$$

$$
\nu = \frac{\sigma^2}{2(r-q)(\beta-1)}\bigl[e^{2(r-q)(\beta-1)T} - 1\bigr]
$$

$\chi^2(z, k, \nu)$: 非心カイ二乗分布の累積確率（非心度 $\nu$、自由度 $k$、$z$ 以下）。

<!-- Hull eq. CEV European option (§27.1) -->

---

### Merton ジャンプ拡散モデル — SDE と級数公式

**SDE:**

$$
\frac{dS}{S} = (r - q - \lambda k)\,dt + \sigma\,dz + dp
$$

<!-- Hull eq. (§27.1) Merton JD SDE -->

- $\lambda$: 年間ジャンプ期待回数（強度）
- $k$: ジャンプサイズの期待値（資産価格比）
- $dp$: ポアソン過程（$dz$ と独立）

**Merton の級数公式** (ジャンプサイズの対数が正規分布 $N(\gamma, \delta^2)$ の場合):

$$
c = \sum_{n=0}^{\infty} \frac{e^{-\lambda' T}(\lambda' T)^n}{n!}\, c_{\mathrm{BSM}}\!\left(S, K, r_n, \sigma_n, T, q\right)
$$

$$
\lambda' = \lambda(1 + k),\quad k = e^{\gamma + \delta^2/2} - 1
$$

$$
\sigma_n^2 = \sigma^2 + \frac{n\delta^2}{T},\qquad r_n = r - \lambda k + \frac{n(\gamma + \delta^2/2)}{T}
$$

<!-- Hull eq. Merton series (§27.1) -->

---

### Hull-White 確率的ボラティリティモデル

$$
dS/S = (r - q)\,dt + \sqrt{V}\,dz_S, \qquad dV = a(V_L - V)\,dt + \xi V^\alpha\,dz_V
$$

<!-- Hull eq. (27.2)-(27.3) -->

ボラティリティがストック価格と無相関な場合、ヨーロピアン・コールは BSM 価格を平均分散率の分布で積分した値に等しい:

$$
c = \int_0^\infty c(\bar{V})\,g(\bar{V})\,d\bar{V}
$$

---

### Heston モデル

$$
dS = (r - q)\,S\,dt + \sqrt{v}\,S\,dz_1
$$

$$
dv = \kappa(\theta - v)\,dt + \xi\sqrt{v}\,dz_2, \qquad dz_1\,dz_2 = \rho\,dt
$$

<!-- Hull Heston (§27.2) — original with alpha=0.5 in eqs (27.2)-(27.3) -->

- $\kappa$: 平均回帰速度、$\theta$: 長期平均分散、$\xi$: 分散のボラティリティ（vol of vol）
- $\rho < 0$: 株価とボラティリティが負相関 → エクイティ型スマイル
- **Feller 条件**: $2\kappa\theta > \xi^2$ が成立しないと分散がゼロに張り付く

---

### SABR モデル

$$
dF = \sigma F^\beta\,dW_1, \qquad \frac{d\sigma}{\sigma} = \nu\,dW_2, \qquad dW_1\,dW_2 = \rho\,dt
$$

<!-- Hull SABR SDE (§27.2) -->

パラメータ: $\sigma_0$（初期ボラティリティ）、$\beta$（弾力性）、$\rho$（相関）、$\nu$（vol of vol）。$F_0$ は初期フォワード価格。

**Hagan SABR 近似式** (ブラック・モデルの impliedvol $\sigma_B$):

ATM ($F_0 = K$):

$$
\sigma_B \approx \frac{\sigma_0}{F_0^{1-\beta}} \left[1 + \left(\frac{(1-\beta)^2\sigma_0^2}{24 F_0^{2-2\beta}} + \frac{\rho\beta\nu\sigma_0}{4 F_0^{1-\beta}} + \frac{(2-3\rho^2)\nu^2}{24}\right)T\right]
$$

<!-- Hull Hagan SABR ATM (§27.2) -->

一般 $F_0 \neq K$ の場合、$x = (F_0 K)^{(1-\beta)/2}$、$y = (1-\beta)\ln(F_0/K)$、$\phi = \frac{\nu x}{\sigma_0}\ln\frac{F_0}{K}$ を用いた完全式を使用:

$$
\sigma_B = A \cdot B \cdot \phi / \chi(\phi)
$$

$$
A = \frac{\sigma_0}{x(1 + y^2/24 + y^4/1920)}, \quad \chi = \ln\!\left(\frac{\sqrt{1-2\rho\phi+\phi^2}+\phi-\rho}{1-\rho}\right)
$$

$\rho > 0$: スマイルは右上がり、$\rho < 0$: 右下がり、中間: U 字型。

---

### IVF / Dupire 局所ボラティリティ

$$
\left[\sigma_{\mathrm{loc}}(K, T)\right]^2 = \frac{2\,\dfrac{\partial c_{\mathrm{mkt}}}{\partial T} + 2q\,c_{\mathrm{mkt}} + K[r(T)-q(T)]\,\dfrac{\partial c_{\mathrm{mkt}}}{\partial K}}{K^2\,\dfrac{\partial^2 c_{\mathrm{mkt}}}{\partial K^2}}
$$

<!-- Hull eq. (27.4) -->

- $c_{\mathrm{mkt}}(K, T)$: 市場のヨーロピアン・コール価格
- マーケットのスマイルサーフェスから局所ボラティリティを直接導出
- 単一資産の時刻 $t$ の限界分布を正確に再現（ジョイント分布は不正確）

---

### コンバーティブル債の二項ツリー — デフォルト分岐

各ノードで 3 方向への分岐確率:

$$
p_u = \frac{a - d\,e^{-\lambda\Delta t}}{u - d}, \quad p_d = \frac{u\,e^{-\lambda\Delta t} - a}{u - d}, \quad p_{\rm def} = 1 - e^{-\lambda\Delta t}
$$

$$
u = e^{\sigma\sqrt{\Delta t}}, \quad d = 1/u, \quad a = e^{(r-q)\Delta t}
$$

<!-- Hull eq. (§27.4) convertible bond tree -->

ロールバック時: ホルダーは転換を最適判定、発行体はコールで強制転換を判定。

---

### バリア近傍の適応的ツリー — $u$ の選択

バリア $H$ にノードが乗るよう $u$ を調整:

$$
\ln u = \frac{\ln H - \ln S_0}{N}, \quad N = \operatorname{int}\!\left[\frac{\ln H - \ln S_0}{\sigma\sqrt{3\Delta t}} + 0.5\right]
$$

<!-- Hull barrier tree (§27.6) -->

三項ツリー確率:

$$
p_d = -\frac{(r-q-\sigma^2/2)\Delta t}{2\ln u} + \frac{\sigma^2\Delta t}{2(\ln u)^2}, \quad
p_m = 1 - \frac{\sigma^2\Delta t}{(\ln u)^2}, \quad
p_u = \frac{(r-q-\sigma^2/2)\Delta t}{2\ln u} + \frac{\sigma^2\Delta t}{2(\ln u)^2}
$$

---

### 二相関資産ツリー — 確率調整法

無相関を仮定した 2 つの二項ツリーを結合後、確率を相関 $\rho$ で調整 (Table 27.3):

| $S_2$ / $S_1$ | Down | Up |
|---|---|---|
| Up | $0.25(1-\rho)$ | $0.25(1+\rho)$ |
| Down | $0.25(1+\rho)$ | $0.25(1-\rho)$ |

<!-- Hull Table 27.3 (§27.7) -->

## 4. アルゴリズム / 手順

### 1. Heston Monte Carlo（反射 Euler-Maruyama）

1. 初期値 $S_0, v_0$ を設定。時間刻み $\Delta t = T / N$。
2. 各ステップで相関付き正規乱数 $(Z_1, Z_2)$ を生成: $Z_2 = \rho Z_1 + \sqrt{1-\rho^2} Z_1'$。
3. 分散更新（反射スキームで負値を排除）:
   $v_{t+\Delta t} = \max\!\bigl(v_t + \kappa(\theta - v_t)\Delta t + \xi\sqrt{v_t \Delta t}\,Z_2,\; 0\bigr)$
4. 株価更新:
   $S_{t+\Delta t} = S_t \exp\!\bigl((r - q - v_t/2)\Delta t + \sqrt{v_t \Delta t}\,Z_1\bigr)$
5. ペイオフを割引いて平均 → オプション価格。
6. 注: Feller 条件 $2\kappa\theta > \xi^2$ が満たされない場合は Full-Truncation Euler を使用。

---

### 2. Longstaff-Schwartz (LSM) — Bermudan/American

1. 多数のパスをフォワードにシミュレート; $N_{\rm paths} \times (N_{\rm steps}+1)$ の価格行列を保存。
2. 満期時のキャッシュフローを設定: $cf = \max(K - S_T, 0)$（プット）。
3. 各行使時点を満期側から逆向きに処理:
   a. イン・ザ・マネー (ITM) パスを抽出。
   b. 継続価値 $Y = cf \cdot e^{-r\Delta t}$ を被説明変数、$X = S_{\rm step}$ を説明変数として多項式回帰（次数 2-3）。
   c. 回帰値（推定継続価値）< 即時行使価値 のパスで行使; それ以外は継続。
4. 全パスのキャッシュフローを $t=0$ に割引いて平均。
5. 計算されたオプション価格は真値の下限（Lower Bound）。

---

### 3. Dupire 局所ボラティリティ (IVF モデル) の構築

1. 各 $(K, T)$ でのマーケットオプション価格 $c_{\rm mkt}(K, T)$ を収集（スプラインなどで補間）。
2. 1 階偏微分 $\partial c/\partial T$, $\partial c/\partial K$ および 2 階偏微分 $\partial^2 c/\partial K^2$ を数値微分で計算。
3. Dupire 式 (eq. 27.4) に代入して $\sigma_{\rm loc}^2(K, T)$ を計算。
4. 得られた局所ボラティリティ曲面をグリッド補間でモデルに組み込む（FD 法または MC で使用）。
5. 注意: 第 2 導関数の数値誤差が増幅されるため、差分前にスマイルをスムージングすること。

---

### 4. Merton ジャンプ拡散 — Poisson 混合 BSM 級数

1. パラメータ: $\lambda, \gamma, \delta, \sigma, r, q, S, K, T$。
2. $k = e^{\gamma + \delta^2/2} - 1$, $\lambda' = \lambda(1+k)$ を計算。
3. $n = 0, 1, \ldots, N_{\rm max}$（通常 $N_{\rm max} = 20$-40）について:
   - Poisson 重み $w_n = e^{-\lambda' T}(\lambda' T)^n / n!$
   - $\sigma_n = \sqrt{\sigma^2 + n\delta^2/T}$, $r_n = r - \lambda k + n(\gamma + \delta^2/2)/T$
   - $c_n = c_{\rm BSM}(S, K, r_n, \sigma_n, T, q)$
4. $c = \sum_n w_n c_n$ を合計。

---

### 5. CEV — 非心カイ二乗分布による評価

- $0 < \beta < 1$: 上記公式を使用。非心カイ二乗 CDF は `scipy.stats.ncx2` で計算可能。
- パラメータ $\sigma, \beta$ はバニラオプション価格へのフィットで最適化（最小二乗）。
- $\beta = 1$ は BSM に収束することで実装を検証可能。

---

### 6. パス依存オプションのツリー拡張（§27.5 Hull-White 法）

1. 通常通り資産価格ツリーを構築。
2. フォワードインダクションで各ノードの経路関数 $F$（例: 算術平均）の最大・最小を計算。
3. 各ノードで $F$ の代表値（均等間隔、通常 4-8 個）を選択。
4. バックワードインダクションで各代表値に対する派生価値を計算；他の値は補間。
5. American の場合: 各ノード・各代表値で早期行使判定を追加。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm, poisson


def bs_call(S, K, r, sigma, T, q=0.0):
    """Black-Scholes-Merton call price."""
    d1 = (math.log(S/K) + (r - q + 0.5*sigma**2)*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    return S*math.exp(-q*T)*norm.cdf(d1) - K*math.exp(-r*T)*norm.cdf(d2)


def merton_jump_diffusion_call(S, K, r, sigma, T, lam, gamma, delta, q=0.0, n_terms=40):
    """Merton's series — sum over Poisson jump count."""
    k = math.exp(gamma + 0.5*delta**2) - 1.0
    lam_p = lam * (1 + k)
    total = 0.0
    for n in range(n_terms):
        sig_n = math.sqrt(sigma**2 + n * delta**2 / T)
        r_n = r - lam*k + n*(gamma + 0.5*delta**2)/T
        w = math.exp(-lam_p*T) * (lam_p*T)**n / math.factorial(n)
        total += w * bs_call(S, K, r_n, sig_n, T, q)
    return total


def heston_mc_call(S, K, r, T, kappa, theta, xi, rho, v0, q=0.0,
                   n_steps=500, n_paths=20_000, rng=None):
    """Heston via reflection scheme (Euler-Maruyama)."""
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    S_t = np.full(n_paths, float(S))
    v_t = np.full(n_paths, float(v0))
    sqrt_dt = math.sqrt(dt)
    for _ in range(n_steps):
        Z1 = rng.standard_normal(n_paths)
        Z2 = rho*Z1 + math.sqrt(1 - rho**2)*rng.standard_normal(n_paths)
        v_pos = np.maximum(v_t, 0.0)
        v_t = np.maximum(
            v_t + kappa*(theta - v_t)*dt + xi*np.sqrt(v_pos)*sqrt_dt*Z2, 0.0
        )
        S_t *= np.exp((r - q - 0.5*v_pos)*dt + np.sqrt(v_pos)*sqrt_dt*Z1)
    payoff = np.maximum(S_t - K, 0.0)
    return float(math.exp(-r*T) * payoff.mean())


def hagan_sabr_implied_vol(F, K, T, alpha, beta, rho, nu):
    """Hagan SABR implied lognormal vol (Hull §27.2 notation: sigma_0=alpha)."""
    if abs(F - K) < 1e-12:
        FK_beta = F**(1 - beta)
        term2 = 1 + T * (
            (1-beta)**2 * alpha**2 / (24 * F**(2-2*beta))
            + rho*beta*nu*alpha / (4 * F**(1-beta))
            + (2 - 3*rho**2)*nu**2 / 24
        )
        return (alpha / FK_beta) * term2
    log_FK = math.log(F / K)
    FK_avg = (F * K)**((1 - beta) / 2)
    z = (nu / alpha) * FK_avg * log_FK
    x_z = math.log(
        (math.sqrt(1 - 2*rho*z + z**2) + z - rho) / (1 - rho)
    )
    y = (1 - beta) * log_FK
    factor1 = 1 + y**2/24 + y**4/1920
    sigma_b = alpha * z / (FK_avg * factor1 * x_z)
    factor2 = 1 + T * (
        (1-beta)**2 * alpha**2 / (24 * FK_avg**2)
        + rho*beta*nu*alpha / (4 * FK_avg)
        + (2 - 3*rho**2)*nu**2 / 24
    )
    return sigma_b * factor2


def lsm_american_put(S, K, r, sigma, T, n_steps=50, n_paths=10_000, rng=None):
    """Longstaff-Schwartz American put; polynomial basis degree 2."""
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    sqrt_dt = math.sqrt(dt)
    Z = rng.standard_normal((n_paths, n_steps))
    log_paths = np.log(S) + np.cumsum(
        (r - 0.5*sigma**2)*dt + sigma*sqrt_dt*Z, axis=1
    )
    paths = np.column_stack([np.full((n_paths, 1), S), np.exp(log_paths)])
    cf = np.maximum(K - paths[:, -1], 0.0)
    disc = math.exp(-r * dt)
    for step in range(n_steps - 1, 0, -1):
        S_step = paths[:, step]
        intrinsic = np.maximum(K - S_step, 0.0)
        itm = intrinsic > 0
        cf *= disc  # discount one step
        if itm.sum() > 0:
            X = S_step[itm]
            Y = cf[itm]  # already discounted
            beta_coef = np.polyfit(X, Y, 2)
            cont = np.polyval(beta_coef, X)
            exercise = intrinsic[itm] > cont
            cf[itm] = np.where(exercise, intrinsic[itm], cf[itm])
    return float(cf.mean() * disc)


# --- Examples ---
if __name__ == "__main__":
    print("Merton JD call:",
          merton_jump_diffusion_call(100, 100, 0.05, 0.20, 1.0,
                                     lam=1.0, gamma=-0.05, delta=0.15))
    print("Heston MC call:",
          heston_mc_call(100, 100, 0.05, 1.0,
                         kappa=2.0, theta=0.04, xi=0.5, rho=-0.7, v0=0.04))
    print("SABR ATM vol:",
          hagan_sabr_implied_vol(100, 100, 1.0, alpha=0.2, beta=0.8, rho=-0.3, nu=0.4))
    print("LSM Amer put:",
          lsm_american_put(36, 40, 0.06, 0.2, 1.0))
```

## 6. 注意点 / 典型的なミス

- **Heston Feller 条件**: $2\kappa\theta > \xi^2$ が成立しない場合、分散がゼロに張り付く。反射 Euler ではなく Full-Truncation Euler を使うか、より高精度な QE スキームを検討する。
- **Merton 級数の打ち切り**: $\lambda$ が小さければ $n = 20$-40 で十分だが、$\lambda T \gg 1$ の場合は $n_{\rm max}$ を増やして収束確認すること。
- **SABR Hagan 式の適用限界**: 漸近展開（小さな $T$ の近似）のため、長期・深いアウト・オブ・ザ・マネーで精度が低下。負金利環境では Normal-SABR (ZABR) に切り替える。
- **Dupire の数値微分**: マーケット価格の離散データに $\partial^2 c / \partial K^2$ を直接適用すると符号が逆転するなどのノイズが拡大する。Cubic spline などで事前スムージングが必須。
- **LSM 回帰基底**: 単項式 $\{1, S, S^2\}$ で十分なことが多いが、Laguerre 多項式や Hermite 多項式の方が数値的に安定。次数 2-3 を超えると過学習リスク。
- **バリアオプションのツリー収束**: 単純なツリーは $O(\sqrt{\Delta t})$ オーダーの誤差。ノードをバリア上に配置するか内側・外側バリア補間を使うことで $O(\Delta t)$ に改善。
- **コンバーティブル債のハザードレート**: クレジットリスクを無視すると債券キャッシュフローが過大評価される。$\lambda$ は CDS スプレッドまたは社債価格から推定。
- **分散ガンマの $\nu \to 0$ 極限**: $\nu \to 0$ でガンマ過程が連続ブラウン運動に収束し、VG モデルは BSM に帰着する。
- **準モンテカルロ (Sobol 列など)**: 高次元積分の収束を改善。MC の $O(N^{-1/2})$ に対し QMC は $O((\log N)^d / N)$ 程度。次元 $d$ が大きいと効果が薄れる。

## 7. 関連トピック

- BSM の前提: [topics/bsm.md](../topics/bsm.md)
- ボラティリティスマイル: [chapters/ch20_vol_smile.md](ch20_vol_smile.md)
- 基本数値手法 (ツリー・FD・MC): [chapters/ch21_basic_numerical.md](ch21_basic_numerical.md)
- ボラティリティ・相関の推定: [chapters/ch23_vol_corr_estimation.md](ch23_vol_corr_estimation.md)
- 金利モデルへの応用 (Ch.30-32): 同手法が Hull-White, LMM などで再利用される
- Quasi-MC 理論: [topics/numerical_methods.md](../topics/numerical_methods.md)
