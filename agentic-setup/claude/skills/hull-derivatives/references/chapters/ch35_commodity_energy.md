# Ch.35 Energy and Commodity Derivatives

> **Source**: Hull 11e, Chapter 35 (pp. 785-801). Paraphrased summary for personal use.

## 1. 要点

- コモディティ（農産物・金属・エネルギー）の価格は**平均回帰**を示す傾向があり、金利モデルで培った手法が応用できる。
- エネルギー商品（原油・天然ガス・電力）はとくに重要で、価格ジャンプと季節性を持つ高度なモデルを要する。電力は**貯蔵不可**のため通常のコスト・オブ・キャリー議論が成立しない。
- **ウェザー・デリバティブ**は HDD/CDD を原資産とし、エネルギー消費量の気温依存リスクをヘッジする。
- **保険デリバティブ（CAT ボンド）**は巨大損害（ハリケーン・地震）リスクを資本市場に移転する手段であり、株式市場との相関がほぼゼロのため分散効果が高い。
- ウェザー・保険デリバティブには系統的リスクがないため、実世界の確率分布を用いて期待ペイオフを計算し、リスクフリーレートで割り引く「歴史シミュレーション法」が適用できる。

## 2. キー用語

- **Mean reversion（平均回帰）**: 価格が長期的均衡水準へ引き戻される性質。農産物・エネルギー・金利に顕著。
- **Convenience yield（利便利回り）**: 現物保有から得られる暗黙の利益（生産への即時投入など）。正値のとき先物価格はスポットより低い（バックワーデーション）。
- **Contango / Backwardation**: 先物価格がスポットより高い（コンタンゴ）/ 低い（バックワーデーション）状態。
- **Stocks-to-use ratio**: 年末在庫 ÷ 年間消費量。低いほど価格変動が大きくなる。
- **Schwartz Model 1（一要因モデル）**: 対数スポット価格が平均回帰する確率過程。
- **Gibson-Schwartz（二要因モデル）**: スポット価格＋確率的利便利回りの二要因モデル。
- **HDD（Heating Degree Days）**: 暖房需要指標。1日の平均気温が 65°F を下回る分の積算。
- **CDD（Cooling Degree Days）**: 冷房需要指標。1日の平均気温が 65°F を超える分の積算。
- **CAT bond（Catastrophe Bond）**: 保険会社が発行する高利回り債。災害損失が一定水準を超えると元本・利子が削減される。
- **Swing option（take-and-pay option）**: 一日ごとに受取量を変更できる電力・ガスのオプション。
- **Reinsurance（再保険）**: 保険会社が自社の巨大損失リスクを他の保険会社に転嫁する仕組み。
- **Excess-of-loss contract**: 損失の一定層（layer）を補償する再保険契約。ブル・スプレッドと等価。

## 3. 主要公式

### コスト・オブ・キャリー（貯蔵可能コモディティ）

$$
F_0 = S_0\, e^{(r + u - y)\,T}
$$

- $S_0$: 現在のスポット価格
- $r$: 連続複利リスクフリーレート
- $u$: 単位時間当たり保管コスト（率）
- $y$: 利便利回り（convenience yield）
- $T$: 先物満期

<!-- Hull eq. (5.X, 35 関連) -->

利便利回りが高い（現物供給がひっ迫している）場合、$y > r + u$ となりバックワーデーション（先物 < スポット）。

### 貯蔵不可コモディティ（電力）の先物

電力は貯蔵できないため、コスト・オブ・キャリー議論は成立しない。先物価格は期待スポット価格に一致する：

$$
F_T = \hat{E}[S_T]
$$

<!-- Hull §35.4 (a simple process) -->

### 単純リスク中立プロセス（時間依存ドリフト）

$$
\frac{dS}{S} = \mu(t)\,dt + \sigma\,dz \qquad \Rightarrow \qquad F(t) = \hat{E}[S(t)] = S(0)\,e^{\int_0^t \mu(\tau)\,d\tau}
$$

<!-- Hull eq. (35.1) -->

$\mu(t)$ は先物カーブから逆算: $\mu(t) = \frac{\partial}{\partial t}[\ln F(t)]$

### 平均回帰対数価格モデル（Schwartz Model 1 / one-factor）

$$
d\ln S = \bigl[\theta(t) - a\ln S\bigr]\,dt + \sigma\,dz
$$

<!-- Hull eq. (35.2) -->

- $a$: 平均回帰速度
- $\theta(t)$: 先物価格にフィットするための時間依存パラメータ（季節性を吸収）
- $\sigma$: ボラティリティ

等価な価格プロセス（Itô の補題により）:

$$
\frac{dS}{S} = \bigl[\theta^*(t) - a\ln S\bigr]\,dt + \sigma\,dz, \quad \theta^*(t) = \theta(t) + \tfrac{1}{2}\sigma^2
$$

### ジャンプ付き価格プロセス（電力・天然ガス）

$$
d\ln S = \bigl[\theta(t) - a\ln S\bigr]\,dt + \sigma\,dz + dp
$$

<!-- Hull §35.4 Jumps -->

$dp$: ポアソン過程（Merton のジャンプ拡散モデルと同型）。

### Gibson-Schwartz 二要因モデル（価格 ＋ 確率的利便利回り）

$$
\frac{dS}{S} = (r - y)\,dt + \sigma_1\,dz_1
$$

$$
dy = k(\alpha - y)\,dt + \sigma_2\,dz_2
$$

<!-- Hull §35.4 Other Models; Gibson & Schwartz (1990) -->

- $y$: 確率的利便利回り
- $k, \alpha$: 平均回帰速度・長期均衡
- $dz_1, dz_2$: 相関のある Wiener 過程
- 先物カーブへの完全フィットのため $\alpha$ を時間依存 $\alpha(t)$ とすることも可能

### Eydeland-Geman（確率的ボラティリティ・電力）

$$
\frac{dS}{S} = a(b - \ln S)\,dt + \sqrt{V}\,dz_1
$$

$$
dV = c(d - V)\,dt + e\sqrt{V}\,dz_2
$$

<!-- Hull §35.4 Other Models; Eydeland & Geman (1998) -->

### HDD / CDD の定義

$$
\mathrm{HDD} = \max(65 - A,\; 0)
$$

$$
\mathrm{CDD} = \max(A - 65,\; 0)
$$

<!-- Hull §35.5 -->

$A$: 当日の最高気温と最低気温の平均（°F）。例：最高 68°F、最低 44°F → $A = 56$、HDD = 9、CDD = 0。

月間 HDD/CDD = 日次 HDD（CDD）の月累計。標準的 CME 契約は **$20 × 月間 HDD（CDD）**。

### ウェザー・オプション評価（歴史シミュレーション）

HDD 分布を過去データから推定（例：対数正規）し、期待ペイオフをリスクフリーレートで割り引く：

$$
V_0 = e^{-rT}\,\hat{E}[\text{payoff}]
$$

<!-- Hull §35.7 -->

コールオプション（strike $K$、payment rate $\omega$）の期待ペイオフは Black-76 型式で計算可能：

$$
\text{payoff} = \omega\,\max(\mathrm{HDD}_{\text{cum}} - K,\; 0)
$$

### エネルギー生産者のヘッジ回帰式

$$
Y = a + bP + cT + \varepsilon
$$

<!-- Hull §35.8 -->

$Y$: 月次利益、$P$: エネルギー平均価格、$T$: HDD または CDD。
ヘッジ：エネルギー先物で $-b$、ウェザー先物で $-c$ のポジションを取る。

## 4. アルゴリズム / 手順

### 1. Commodity forward curve calibration with seasonality

1. 市場観測された先物価格（月次 or 四半期）を収集する。
2. 季節性ファクターを推定：スポット価格の 12ヶ月移動平均に対する月次比率（percentage seasonal factor）。
3. 先物価格を季節性ファクターで**脱季節化**（deseasonalize）する。
4. 脱季節化価格を内挿（例：線形内挿）して全タイムステップの先物価格を得る。
5. 内挿済み脱季節化価格に季節性ファクターを再掛けして**季節化**（reseasonalize）し、ツリー構築に使用する。
6. ボラティリティにも同様の季節性ファクターを適用（$\sigma \to \sigma(t)$）。

### 2. Mean-reverting MC for commodity spot (Schwartz-1)

1. $X = \ln S$ とおき、プロセス $dX = [\theta(t) - aX]\,dt + \sigma\,dz$ を離散化。
2. オイラー法：$X_{i+1} = X_i + a(\theta_i - X_i)\Delta t + \sigma\sqrt{\Delta t}\,Z_i$（$Z_i \sim N(0,1)$）。
3. $\theta(t)$ は前ステップの先物価格から逆算し、$F(t) = \hat{E}[\exp(X_t)]$ が市場価格に一致するよう設定。
4. モンテカルロで多数パスをシミュレートし、ペイオフの期待値を割り引く。

### 3. Weather option valuation via historical / burn-rate analysis

1. 対象地点・対象月の過去 30〜50 年の日次気温データを収集する。
2. 各年の月間 HDD（CDD）累計を計算し、経験的分布（または対数正規フィット）を作成する。
3. トレンド（温暖化など）を線形回帰で調整し、来期の平均・分散を補正する。
4. モンテカルロまたは解析式でオプションの期待ペイオフを計算する。
5. リスクフリーレートで割り引いて現在価値を得る（系統的リスクがないため実世界確率 = リスク中立確率）。

### 4. Real-option (storage / generation) valuation via stochastic dynamic programming

1. 平均回帰 MC または trinomial tree でコモディティ価格パスを生成する。
2. 状態変数（価格、在庫量、設備稼働状態など）を定義する。
3. 満期からバックワードに DP（動的計画法）を実行：各ノードで「保有継続 vs. 生産/放出」の最大化。
4. 最適停止・最適生産スケジュールとその現在価値を求める。
5. 詳細は Ch.36（Real Options）参照。

## 5. Python reference

```python
import math
import numpy as np


def schwartz1_simulate(S0, theta, a, sigma, T, n_steps, n_paths, rng=None):
    """One-factor mean-reverting log-spot price (Schwartz Model 1).

    theta: long-run log-price level (scalar or array of length n_steps)
    a:     mean-reversion speed
    """
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    x = np.full(n_paths, math.log(S0))
    theta_arr = np.full(n_steps, theta) if np.isscalar(theta) else np.asarray(theta)
    for i in range(n_steps):
        Z = rng.standard_normal(n_paths)
        x = x + a * (theta_arr[i] - x) * dt + sigma * math.sqrt(dt) * Z
    return np.exp(x)


def commodity_forward(S0, r, storage, convenience_yield, T):
    """Cost-of-carry forward for storable commodity.

    F0 = S0 * exp((r + u - y) * T)
    """
    return S0 * math.exp((r + storage - convenience_yield) * T)


def hdd_cdd_payoff(daily_temps_F, threshold=65, contract_size=20, max_payoff=None):
    """Compute HDD and CDD totals + payoff for a month-long contract.

    daily_temps_F: list of daily average temperatures (Fahrenheit)
    contract_size: $/HDD or $/CDD per index point
    max_payoff:    optional payment cap
    """
    arr = np.asarray(daily_temps_F, dtype=float)
    hdd = np.maximum(threshold - arr, 0).sum()
    cdd = np.maximum(arr - threshold, 0).sum()
    hdd_payoff = hdd * contract_size
    cdd_payoff = cdd * contract_size
    if max_payoff is not None:
        hdd_payoff = min(hdd_payoff, max_payoff)
        cdd_payoff = min(cdd_payoff, max_payoff)
    return dict(hdd=float(hdd), cdd=float(cdd),
                hdd_payoff=float(hdd_payoff), cdd_payoff=float(cdd_payoff))


def asian_strip_commodity_call(spot_avg_paths, K, r, T):
    """MC valuation of an Asian-style commodity call from simulated paths.

    spot_avg_paths: 1-D array of average spot price realizations
    """
    payoff = np.maximum(spot_avg_paths - K, 0.0)
    return float(math.exp(-r * T) * payoff.mean())


def deseasonalize_futures(futures_prices, seasonal_factors):
    """Remove seasonality from futures prices.

    futures_prices:   array of observed futures prices (length M)
    seasonal_factors: percentage seasonal factors for same months (length M)
    Returns deseasonalized prices.
    """
    return np.asarray(futures_prices) / np.asarray(seasonal_factors)


def reseasonalize_futures(deseas_prices, seasonal_factors):
    """Apply seasonality back to deseasonalized (interpolated) futures prices."""
    return np.asarray(deseas_prices) * np.asarray(seasonal_factors)


# --- Example ---
S_T = schwartz1_simulate(S0=50, theta=math.log(60), a=0.5, sigma=0.30,
                          T=1.0, n_steps=252, n_paths=20_000)
print("E[S_T]:", float(S_T.mean()), "  median:", float(np.median(S_T)))
print("F_T from carry (no convenience):",
      commodity_forward(50, 0.05, 0.02, 0.0, 1.0))
print("Weather:",
      hdd_cdd_payoff([40, 35, 50, 60, 70, 75], threshold=65, contract_size=20))
```

## 6. 注意点 / 典型的なミス

- **電力のキャリー議論は使えない**: 電力は実質的に貯蔵不可のため $F_0 = S_0 e^{rT}$ は成立しない。先物価格は期待スポット価格。ヒートウェーブ時は短期スポットが 1,000% 上昇することもある。
- **バックワーデーションの誤解**: 利便利回りが高いのは供給ひっ迫（在庫が薄い）ときであり、バックワーデーションは「市場の強気」ではなく「保有の実物メリット」を反映する。原油（戦時など）が典型例。
- **平均回帰とスポット vs 先物ボラティリティの乖離**: 平均回帰があると長期先物のボラティリティ（term structure of vol）はスポットより大幅に低い。ブラック・ショールズのフラットなボラティリティ仮定をそのまま適用すると長期オプションを過大評価する。
- **スポット原油の負値リスク**: 2020年4月のWTI先物は史上初のマイナスを記録。対数正規仮定が崩れるため、正規過程や反射壁を検討する必要がある。
- **ウェザー変数の非正規性**: 気温分布は正規に近いが、HDD/CDD の累計分布は非対称で裾が厚い。対数正規フィットか歴史シミュレーションが推奨される。
- **CAT ボンドの「ベーシスリスク」**: インデックス型 CAT ボンド（業界損失指標連動）では、個社損失と指標がずれるベーシスリスクが生じる。
- **季節性カリブレーションの注意**: 季節性ファクターで脱季節化してから内挿し、再び季節化する手順を守らないと、ツリーが市場先物価格と整合しない。
- **ジャンプのフィッティング**: 電力・ガスのジャンプ頻度・サイズ分布は歴史データから推定するが、サンプル数が少ないため不確実性が大きい。

## 7. 関連トピック

- See: [topics/commodity_energy.md](../topics/commodity_energy.md)
- **Ch.5**: 先物・フォワードの基礎、コスト・オブ・キャリーと利便利回りの導出
- **Ch.18**: コモディティ先物オプション（ブラックのモデル）
- **Ch.26**: アジアン・オプション（コモディティ平均価格ヘッジに多用）
- **Ch.27**: ジャンプ拡散モデル（Merton）、確率的ボラティリティモデル
- **Ch.32**: ノーアービトラージ短期金利モデル（三項ツリー構築手法をコモディティへ応用）
- **Ch.36**: Real Options（貯蔵・発電設備の最適運用を確率的DP で評価）
