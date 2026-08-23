# Ch.26 Exotic Options

> **Source**: Hull 11e, Chapter 26 (pp. 614-639). Paraphrased summary for personal use.

## 1. 要点

- エキゾチック・オプションは標準的なプレーン・バニラ製品よりペイオフ規則が複雑な OTC 派生商品であり、通常のオプションより利益率が高い。
- バリア・オプション（ノックイン/ノックアウト）、アジアン・オプション、ルックバック、チューザー、コンパウンドなど 15 類型を扱う。多くは BSM と同じ幾何ブラウン運動の仮定下で解析的に評価できるが、算術平均型アジアンや複雑なクリケは MC が必要。
- パス依存型オプションは 1 次元 PDE では解けず、状態変数を増やすか MC を使う必要がある。
- バリア・オプションのクローズドフォームはノックイン＋ノックアウト＝バニラ関係（$c_\text{di} + c_\text{do} = c$）を利用する。
- バリアンス・スワップは OTM オプションのストリップ（ログ・コントラクト）で静的に複製でき、公正バリアンス・レートが直接計算可能。

## 2. キー用語

- **Package（パッケージ）**: 標準欧州コール・プット・フォワード・現金・原資産の組み合わせ。ゼロコストレンジフォワードはその一例。
- **Perpetual American option（永久米国型オプション）**: 満期のない米国型。解析解あり（$\alpha_1, \alpha_2$ で決まる閾値）。
- **Bermudan option（バミューダン）**: 特定の日にのみ早期行使可能な米国型変形。
- **Gap option（ギャップ）**: $S_T > K_2$ のときに $S_T - K_1$ を支払う。トリガー価格と支払い価格が異なる。
- **Forward start option（フォワードスタート）**: 将来時点 $T_1$ に ATM でスタートするオプション。現在価値は $c e^{-qT_1}$。
- **Cliquet（クリケ）**: 定期的にリセットされるフォワードスタートの系列。ラチェット・オプションとも。
- **Compound option（コンパウンド）**: オプションに対するオプション（call on call 等）。二変量正規分布で評価（Geske 公式）。
- **Chooser option（チューザー）**: 指定日にコールかプットかを選べる。パッケージ（コール＋割引プット）に分解可能。
- **Barrier option（バリア）**: ノックアウト（バリア到達で消滅）またはノックイン（バリア到達で発生）。up/down × in/out の 4 種 × コール/プット = 8 種。
- **Binary / Digital option（バイナリー）**: キャッシュ・オア・ナッシング、アセット・オア・ナッシングの 2 種。不連続ペイオフ。
- **Lookback option（ルックバック）**: 浮動行使価格型（フローティング）と固定行使価格型（フィックス）。経路中の最大・最小値に依存。
- **Shout option（シャウト）**: 存続中に 1 度だけ現在水準を固定できる欧州型。ルックバックより安価。
- **Asian option（アジアン）**: 平均価格型（average price）と平均行使価格型（average strike）。算術平均に解析解なし。
- **Exchange option（交換オプション）**: 資産 $U$ を資産 $V$ と交換する権利。Margrabe 公式で評価。
- **Rainbow option（レインボー）**: 複数資産に依存するオプション（バスケット等）。
- **Variance swap（バリアンス・スワップ）**: 実現バリアンスと固定バリアンス・レートの差を交換。ログ・コントラクトで静的複製可能。
- **Volatility swap（ボラティリティ・スワップ）**: 実現ボラティリティと固定ボラティリティを交換。バリアンス・スワップより評価が難しい。
- **Static options replication（静的複製）**: エキゾチックのペイオフを境界条件でバニラ・ポートフォリオで近似するヘッジ手法。
- **Parisian option（パリジャン）**: バリアを一定期間連続して（または累積で）超えた場合のみノックイン/アウト。

## 3. 主要公式

### Gap call option
$$c_\text{gap} = S_0 e^{-qT} N(d_1) - K_1 e^{-rT} N(d_2)$$

- $d_1 = \dfrac{\ln(S_0/K_2) + (r - q + \sigma^2/2)T}{\sigma\sqrt{T}}$, $\quad d_2 = d_1 - \sigma\sqrt{T}$
- $K_2$: トリガー価格（行使判定）、$K_1$: ペイオフ時の支払い水準

<!-- Hull eq. (26.1) -->

### Forward start option (ATM at $T_1$)
$$V_0 = c \, e^{-qT_1}$$

- $c$: $T_2 - T_1$ の残存期間を持つ ATM コールの現在価値
- 無配当株 ($q=0$) では通常の ATM コールと同値

### Cliquet (n reset dates)
$$V_\text{cliquet} = c + \sum_{i=1}^{n-1} (\text{forward start}_i)$$

各フォワードスタートを Section 26.5 の手法で評価して合計する。

### Compound option: call on call (Geske formula)
$$V_{cc} = S_0 e^{-qT_2} M(a_1, b_1;\, \sqrt{T_1/T_2}) - K_2 e^{-rT_2} M(a_2, b_2;\, \sqrt{T_1/T_2}) - K_1 e^{-rT_1} N(a_2)$$

$$a_1 = \frac{\ln(S_0/S^*) + (r-q+\sigma^2/2)T_1}{\sigma\sqrt{T_1}}, \quad a_2 = a_1 - \sigma\sqrt{T_1}$$

$$b_1 = \frac{\ln(S_0/K_2) + (r-q+\sigma^2/2)T_2}{\sigma\sqrt{T_2}}, \quad b_2 = b_1 - \sigma\sqrt{T_2}$$

- $M(a,b;\rho)$: 二変量累積正規分布（相関 $\rho$）
- $S^*$: $T_1$ 時点でコール価値が $K_1$ に等しくなる資産価格

<!-- Hull eq. (26.7 形式、Geske 1979) -->

### Chooser option (same strike $K$, maturity $T_2$, choice at $T_1$)
$$V_\text{chooser} = c(K, T_2) + e^{-q(T_2-T_1)} p\!\left(K e^{-(r-q)(T_2-T_1)},\, T_1\right)$$

- コール（満期 $T_2$, 行使 $K$）と割引プット（満期 $T_1$, 行使 $Ke^{-(r-q)(T_2-T_1)}$）のパッケージ

### Barrier options: key parameters
$$\lambda = \frac{r - q + \sigma^2/2}{\sigma^2}, \quad y = \frac{\ln[H^2/(S_0 K)]}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}$$

$$x_1 = \frac{\ln(S_0/H)}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}, \quad y_1 = \frac{\ln(H/S_0)}{\sigma\sqrt{T}} + \lambda\sigma\sqrt{T}$$

**Down-and-in call** ($H \le K$):
$$c_\text{di} = S_0 e^{-qT}(H/S_0)^{2\lambda} N(y) - K e^{-rT}(H/S_0)^{2\lambda-2} N(y - \sigma\sqrt{T})$$

**Down-and-out call**: $c_\text{do} = c - c_\text{di}$

**Down-and-out call** ($H \ge K$):
$$c_\text{do} = S_0 N(x_1)e^{-qT} - Ke^{-rT}N(x_1-\sigma\sqrt{T}) - S_0 e^{-qT}(H/S_0)^{2\lambda}N(y_1) + Ke^{-rT}(H/S_0)^{2\lambda-2}N(y_1-\sigma\sqrt{T})$$

同様に up-and-in / up-and-out call・put の閉形式あり（本文 pp.621-622）。

<!-- Hull §26.9 -->

### Binary / Digital options
**Cash-or-nothing call** (固定額 $Q$ を支払う):
$$c_\text{con} = Q e^{-rT} N(d_2)$$

**Cash-or-nothing put**:
$$p_\text{con} = Q e^{-rT} N(-d_2)$$

**Asset-or-nothing call**:
$$c_\text{aon} = S_0 e^{-qT} N(d_1)$$

**Asset-or-nothing put**:
$$p_\text{aon} = S_0 e^{-qT} N(-d_1)$$

分解: $c_\text{vanilla} = c_\text{aon}(K) - K \cdot c_\text{con}(K)$

<!-- Hull §26.10 -->

### Floating lookback call (closed form)
$$c_\text{fl} = S_0 e^{-qT} N(a_1) - S_0 e^{-qT} \frac{\sigma^2}{2(r-q)} N(-a_1) - S_\text{min} e^{-rT}\!\left[N(a_2) - \frac{\sigma^2}{2(r-q)} e^{Y_1} N(-a_3)\right]$$

$$a_1 = \frac{\ln(S_0/S_\text{min}) + (r-q+\sigma^2/2)T}{\sigma\sqrt{T}}, \quad a_2 = a_1 - \sigma\sqrt{T}$$

$$a_3 = \frac{\ln(S_0/S_\text{min}) + (-r+q+\sigma^2/2)T}{\sigma\sqrt{T}}, \quad Y_1 = -\frac{2(r-q-\sigma^2/2)\ln(S_0/S_\text{min})}{\sigma^2}$$

浮動ルックバック・プット $p_\text{fl}$ および固定型は put–call parity 類似の変換で求める（pp.624-625）。

<!-- Hull §26.11 -->

### Asian option: moment-matching (Turnbull–Wakeman)
Black モデルに入力する等価パラメータ:
$$F_0 = M_1, \quad \sigma^2 = \frac{1}{T} \ln\!\left(\frac{M_2}{M_1^2}\right)$$

連続平均の場合:
$$M_1 = \frac{e^{(r-q)T}-1}{(r-q)T} S_0$$

$$M_2 = \frac{2e^{[2(r-q)+\sigma^2]T} S_0^2}{(r-q+\sigma^2)(2r-2q+\sigma^2)T^2} + \frac{2S_0^2}{(r-q)T^2}\!\left(\frac{1}{2(r-q)+\sigma^2} - \frac{e^{(r-q)T}}{r-q+\sigma^2}\right)$$

算術平均の閉形式は存在せず、このモーメント整合近似または MC を用いる。

<!-- Hull eq. (26.3)(26.4) -->

### Exchange option (Margrabe formula)
資産 $U$（yield $q_U$）を資産 $V$（yield $q_V$）と交換する権利:
$$V_\text{exch} = V_0 e^{-q_V T} N(d_1) - U_0 e^{-q_U T} N(d_2)$$

$$d_1 = \frac{\ln(V_0/U_0) + (q_U - q_V + \hat\sigma^2/2)T}{\hat\sigma\sqrt{T}}, \quad d_2 = d_1 - \hat\sigma\sqrt{T}$$

$$\hat\sigma = \sqrt{\sigma_U^2 + \sigma_V^2 - 2\rho\sigma_U\sigma_V}$$

注: 無リスク金利 $r$ に依存しない（成長率増加と割引率上昇が相殺）。

<!-- Hull eq. (26.5) -->

### Variance swap: fair variance rate (log-contract replication)
$$\hat{E}[\overline{V}] = \frac{2}{T}\ln\frac{F_0}{S^*} - \frac{2}{T}\!\left[\frac{F_0}{S^*}-1\right] + \frac{2}{T}\!\left[\int_0^{S^*}\!\frac{e^{rT}}{K^2}p(K)\,dK + \int_{S^*}^{\infty}\!\frac{e^{rT}}{K^2}c(K)\,dK\right]$$

離散近似（実務・VIX 計算）:

$$\hat{E}[\overline{V}] \approx -\!\left(\frac{F_0}{S^*}-1\right)^2 + \frac{2}{T}\sum_{i=1}^n \frac{\Delta K_i}{K_i^2} e^{rT} Q(K_i)$$

バリアンス・スワップの価値（固定レート $V_K$ で受け取る側）:
$$L_\text{var}[\hat{E}(\overline{V}) - V_K] e^{-rT}$$

<!-- Hull eq. (26.6)(26.7)(26.8)(26.10) -->

### Quanto option
外国資産に基づくペイオフを国内通貨で受け取る。リスク中立測度の変換（Chapter 30）により、外国資産の成長率を $r_f - \rho\sigma_f\sigma_x$ に調整して評価する（本文では言及のみ）。

## 4. アルゴリズム / 手順

### 1. MC: 算術平均アジアンコールの評価（基本）
1. $dt = T/n$, ドリフト $\mu = (r - q - \sigma^2/2)dt$, ボラティリティ $v = \sigma\sqrt{dt}$ を設定。
2. 各パスで $S_0$ から $n$ ステップの対数価格を累積加算してパスを生成。
3. 各パス上の算術平均 $\bar{S}$ を計算し、ペイオフ $\max(\bar{S} - K, 0)$ を割り引く。
4. $N_\text{paths}$ 個のペイオフ平均を取りオプション価値とする。

### 2. MC: バリア・オプション（ノックアウト）の評価
1. アジアン MC と同様にパスを生成。
2. 各パスで全ステップの最小値（ダウン系）または最大値（アップ系）を求める。
3. バリアを越えていればペイオフをゼロに置き換える。
4. 平均割引ペイオフをオプション価値とする。
   - 注: 離散モニタリングは連続モニタリングより安く出る。Broadie–Glasserman–Kou の補正でバリア $H$ を $He^{\pm 0.5826\sigma\sqrt{T/m}}$ に調整する。

### 3. 幾何平均アジアンをコントロール変量とする分散削減
1. 各パスで算術平均ペイオフ $P_A$ と幾何平均ペイオフ $P_G$ を計算。
2. 幾何平均アジアンの理論値 $P_G^*$ を閉形式（修正 BSM）で計算。
3. $\beta = \text{Cov}(P_A, P_G) / \text{Var}(P_G)$ を推定。
4. 調整後推定値 $\hat{P}_A = P_A - \beta(P_G - P_G^*)$ の平均を取る。
   - 分散が大幅に削減され、必要パス数を 10–100 倍程度削減できる。

### 4. バリアンス・スワップの静的複製（ログ・コントラクト）
1. 現在の先物価格 $F_0$ と $S^*$（$F_0$ 直下のストライク）を特定。
2. 市場に存在する全 OTM オプション（プット: $K < S^*$、コール: $K > S^*$）を列挙。
3. 各オプションに $\Delta K_i / K_i^2$ のウェイトを付けて合成（ログ・コントラクト近似）。
4. 式 (26.6) または (26.10) で公正バリアンス・レート $\hat{E}[\overline{V}]$ を算出。
5. バリアンス・スワップ価値 = $L_\text{var}[\hat{E}(\overline{V}) - V_K] e^{-rT}$。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


def asian_geometric_call(S, K, r, sigma, T, q=0.0):
    """Closed-form geometric Asian call (continuous average, modified BSM)."""
    sigma_a = sigma / math.sqrt(3.0)
    b = 0.5 * (r - q - sigma**2 / 6.0)
    d1 = (math.log(S / K) + (b + 0.5 * sigma_a**2) * T) / (sigma_a * math.sqrt(T))
    d2 = d1 - sigma_a * math.sqrt(T)
    return S * math.exp((b - r) * T) * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)


def asian_arithmetic_call_mc(S, K, r, sigma, T, n_steps=252, n_paths=50_000, rng=None):
    """Arithmetic average Asian call via MC with geometric control variate."""
    rng = rng or np.random.default_rng(0)
    dt = T / n_steps
    drift = (r - 0.5 * sigma**2) * dt
    vol = sigma * math.sqrt(dt)
    Z = rng.standard_normal((n_paths, n_steps))
    log_paths = np.log(S) + np.cumsum(drift + vol * Z, axis=1)
    paths = np.exp(log_paths)
    arith_avg = paths.mean(axis=1)
    geom_avg = np.exp(np.log(paths).mean(axis=1))
    disc = math.exp(-r * T)
    arith_pay = np.maximum(arith_avg - K, 0.0) * disc
    geom_pay = np.maximum(geom_avg - K, 0.0) * disc
    # Control variate correction
    geom_true = asian_geometric_call(S, K, r, sigma, T)
    beta = np.cov(arith_pay, geom_pay)[0, 1] / np.var(geom_pay)
    adj = arith_pay - beta * (geom_pay - geom_true)
    return float(adj.mean()), float(adj.std(ddof=1) / math.sqrt(n_paths))


def barrier_down_and_out_call_mc(S, K, H, r, sigma, T, n_steps=252, n_paths=50_000, rng=None):
    """Down-and-out call via MC (discrete monitoring)."""
    rng = rng or np.random.default_rng(1)
    dt = T / n_steps
    drift = (r - 0.5 * sigma**2) * dt
    vol = sigma * math.sqrt(dt)
    Z = rng.standard_normal((n_paths, n_steps))
    log_paths = np.log(S) + np.cumsum(drift + vol * Z, axis=1)
    paths = np.exp(log_paths)
    alive = paths.min(axis=1) > H
    payoff = np.where(alive, np.maximum(paths[:, -1] - K, 0.0), 0.0)
    disc = payoff * math.exp(-r * T)
    return float(disc.mean()), float(disc.std(ddof=1) / math.sqrt(n_paths))


def margrabe_exchange(V0, U0, sigma_v, sigma_u, rho, q_v, q_u, T):
    """Margrabe formula: right to receive V and give up U."""
    sigma_hat = math.sqrt(sigma_v**2 + sigma_u**2 - 2 * rho * sigma_v * sigma_u)
    d1 = (math.log(V0 / U0) + (q_u - q_v + 0.5 * sigma_hat**2) * T) / (sigma_hat * math.sqrt(T))
    d2 = d1 - sigma_hat * math.sqrt(T)
    return V0 * math.exp(-q_v * T) * norm.cdf(d1) - U0 * math.exp(-q_u * T) * norm.cdf(d2)


def variance_swap_fair_rate(F0, S_star, r, T, strikes, option_prices, option_types):
    """
    Fair variance rate via log-contract (Hull eq. 26.6 / 26.8 discrete).
    strikes: array of strike prices
    option_prices: array of corresponding OTM option prices (puts below S_star, calls above)
    option_types: array of 'p' or 'c' for each strike
    Returns annualised expected variance E[V_bar].
    """
    n = len(strikes)
    delta_K = np.zeros(n)
    delta_K[0] = strikes[1] - strikes[0]
    delta_K[-1] = strikes[-1] - strikes[-2]
    delta_K[1:-1] = 0.5 * (strikes[2:] - strikes[:-2])
    integral = np.sum(delta_K / strikes**2 * math.exp(r * T) * option_prices)
    log_term = (2 / T) * math.log(F0 / S_star)
    linear_term = -(2 / T) * (F0 / S_star - 1)
    return log_term + linear_term + (2 / T) * integral


# Example
print("Geo Asian call:", round(asian_geometric_call(100, 100, 0.05, 0.20, 1.0), 4))
price, se = asian_arithmetic_call_mc(100, 100, 0.05, 0.20, 1.0)
print(f"Arith Asian call (MC+CV): {price:.4f} ± {1.96*se:.4f}")
price_b, se_b = barrier_down_and_out_call_mc(100, 100, 80, 0.05, 0.20, 1.0)
print(f"Down-and-out call: {price_b:.4f} ± {1.96*se_b:.4f}")
print("Exchange option:", round(margrabe_exchange(100, 100, 0.20, 0.25, 0.30, 0.0, 0.0, 1.0), 4))
```

## 6. 注意点 / 典型的なミス

- **バリア MC の離散モニタリング誤差**: 連続モニタリングの解析値より安く出る（ノックアウト）。Broadie–Glasserman–Kou の連続補正（バリアを $He^{\pm 0.5826\sigma\sqrt{T/m}}$ に調整）を適用すること。
- **算術平均アジアンに閉形式なし**: モーメント整合近似（Turnbull–Wakeman）は速いが近似値。精度を要する場合はコントロール変量付き MC を使う。コントロール変量（幾何平均の閉形式）による分散削減効果は大きく、標準誤差を 10 倍以上改善できることがある。
- **パス依存オプションは 1 次元 PDE で解けない**: バリアや lookback は 2 次元（$S$ と経路統計量）になるか MC が必要。無理に 1 次元で解こうとしないこと。
- **Margrabe: $r$ に依存しない**: 成長率の上昇と割引率の上昇が相殺するため。$\hat\sigma$ を間違えてどちらか一方の $\sigma$ だけ使うミスに注意。
- **バリアンス・スワップとスキュー**: ログ・コントラクトの理論では $E[\int_0^T \sigma^2 dt] = -\frac{2}{T}E[\ln(S_T/S_0)]$（リスク中立）。スキューが存在するとこの近似が崩れ、静的複製も完全ではなくなる。
- **バイナリーの価格操作リスク**: 行使判定価格付近で原資産を大量売買して判定を操作するインセンティブが生じる。流動性の低い原資産には特に注意。
- **チューザーの分解**: 同一行使価格・満期の場合のみパッケージ分解（コール＋割引プット）が使える。コール・プットで満期や行使価格が異なる場合はコンパウンド・オプションに類似した評価が必要。
- **ルックバックの高コスト**: 解析値は連続モニタリングを前提とするため、実際の離散モニタリング（日次）との乖離に注意。Broadie–Glasserman–Kou の補正が利用可能。

## 7. 関連トピック

- See: [topics/exotics.md](../topics/exotics.md)（作成予定）
- Ch.15 (BSM 基礎、標準コール・プット公式)
- Ch.17 (インデックス・通貨オプション; $q$ の扱い方)
- Ch.18 (先物オプション; Black モデル → アジアン近似に利用)
- Ch.19 (デルタ・ヘッジ; エキゾチックへの適用とその難しさ)
- Ch.21 (数値手法: MC・二項ツリー・有限差分; エキゾチック評価の基礎)
- Ch.27 (より高度な数値手法; パス依存・バリア・ルックバックの精度改善)
- Ch.28 (マルタンゲールと測度変換; Margrabe 公式の証明, Quanto の $q$ 調整)
- Ch.20 (ボラティリティ・スマイル; バリア・エキゾチックの実務的な評価に不可欠)
