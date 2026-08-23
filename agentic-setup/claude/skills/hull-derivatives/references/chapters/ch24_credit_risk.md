# Ch.24 Credit Risk

> **Source**: Hull 11e, Chapter 24 (pp. 562-586). Paraphrased summary for personal use.

## 1. 要点

- 信用リスクはデフォルト確率と回収率の2要素で決まる。格付機関の実績データからリアルワールド確率を、債券スプレッドや CDS スプレッドからリスク中立確率をそれぞれ推定できる。
- ハザードレート（デフォルト強度）$\lambda(t)$ を使うと、生存確率 $S(t) = e^{-\int_0^t \lambda(u)\,du}$ として累積デフォルト確率を連続時間で表現できる。
- リスク中立デフォルト確率は実世界確率より一般に 5〜10 倍高い。デリバティブの価格付けにはリスク中立確率、信用 VaR / ストレステストには実世界確率を使う。
- Merton モデルは企業株式を資産に対するコールオプションと見なし、株価・株式ボラティリティから倒産確率を推定する構造型アプローチの代表例である。
- OTC デリバティブの信用リスクは CVA・DVA で定量化し、ネッティングや担保（マージン）によって軽減される。デフォルト相関はガウスコピュラモデルで表現され、信用 VaR の基礎となる。

## 2. キー用語

- **ハザードレート（デフォルト強度）**: $\lambda(t)$。微小期間 $\Delta t$ でのデフォルト条件付き確率を $\lambda(t)\Delta t$ で与える瞬間デフォルト率。
- **生存確率**: 時刻 $t$ までにデフォルトしない確率 $S(t) = V(t)$。
- **累積デフォルト確率**: $Q(t) = 1 - S(t)$。
- **無条件デフォルト確率**: 今日の視点から見た特定年のデフォルト確率（条件付きデフォルト確率と区別）。
- **回収率** $R$: デフォルト時に回収できる債券額面に対する割合（通常 40% と仮定）。
- **クレジットスプレッド**: 社債利回りとリスクフリーレートの差。ハザードレートと回収率から近似される。
- **Merton モデル**: 株式を企業資産に対するコールオプションとして倒産確率を導く構造型モデル。
- **KMV モデル**: Merton モデルを拡張し、距離 to default (DD) から期待デフォルト頻度 (EDF) を推定するモデル。
- **CVA（Credit Valuation Adjustment）**: カウンターパーティーデフォルトの期待コスト現在価値（銀行にとっての損失）。
- **DVA（Debit Valuation Adjustment）**: 銀行自身のデフォルトによる期待損失の現在価値（銀行にとっての利益）。
- **ネッティング**: 複数のデリバティブをまとめて1取引として扱い、エクスポージャーを純額化すること。
- **ダウングレードトリガー**: カウンターパーティー格付けが特定水準を下回ると担保拠出を要求する契約条項。
- **Wrong-way risk**: デフォルト確率とエクスポージャーが正相関している状況。通常の CVA が過小推定になる。
- **Right-way risk**: デフォルト確率とエクスポージャーが負相関している状況。
- **デフォルト相関**: 複数企業が同時にデフォルトする傾向を表す尺度。
- **ガウスコピュラ**: デフォルト時刻の周辺分布を保ちつつ、結合分布の相関構造を多変量正規分布で表現するモデル。
- **信用 VaR（Credit VaR）**: 一定信頼水準・時間地平での最大信用損失。
- **CreditMetrics**: 信用格付け遷移行列を用いたモンテカルロによる信用 VaR 計算手法。

## 3. 主要公式

### ハザードレートと生存確率

$$S(t) = V(t) = e^{-\int_0^t \lambda(\tau)\,d\tau}$$

<!-- Hull eq. (24.1 導出) -->

### 累積デフォルト確率

$$Q(t) = 1 - S(t) = 1 - e^{-\bar{\lambda}(t)\,t}$$

<!-- Hull eq. (24.1) -->

ここで $\bar{\lambda}(t)$ は $[0,t]$ の平均ハザードレート。定数ハザード $\lambda$ の場合：

$$Q(T) = 1 - e^{-\lambda T}$$

### クレジットスプレッドからハザードレートを推定（近似）

$$\bar{\lambda}(T) \approx \frac{s(T)}{1 - R}$$

<!-- Hull eq. (24.2) -->

ここで $s(T)$ は満期 $T$ の社債イールドスプレッド（連続複利）、$R$ は回収率。

### 債券価格からクレジットスプレッドを計算

$$s = -\frac{1}{T} \ln \frac{B^{\text{corp}}(T)}{B^{\text{tsy}}(T)}$$

社債価格と同等の国債価格の比から直接スプレッドを算出する。

### Merton モデル：株式価値

$$E_0 = V_0 N(d_1) - D e^{-rT} N(d_2)$$

<!-- Hull eq. (24.3) -->

$$d_1 = \frac{\ln(V_0/D) + (r + \sigma_V^2/2)\,T}{\sigma_V \sqrt{T}}, \quad d_2 = d_1 - \sigma_V \sqrt{T}$$

- $V_0$: 企業資産の現在価値、$D$: 債務額（満期 $T$ のゼロクーポン債）
- $\sigma_V$: 資産ボラティリティ

### Merton モデル：リスク中立デフォルト確率

$$Q = N(-d_2)$$

### 株式ボラティリティと資産ボラティリティの関係（Itô の補題）

$$\sigma_E E_0 = N(d_1)\,\sigma_V V_0$$

<!-- Hull eq. (24.4) -->

### KMV 距離 to Default

$$\mathrm{DD} = d_2 = \frac{\ln(V_0/D) + (r - \sigma_V^2/2)\,T}{\sigma_V \sqrt{T}}$$

DD が大きいほどデフォルト確率は低い。KMV はこの $d_2$ を単調変換して実世界 EDF に変換する。

### CVA と DVA

$$\mathrm{CVA} = \sum_{i=1}^{N} q_i v_i, \quad \mathrm{DVA} = \sum_{i=1}^{N} q_i^* v_i^*$$

$q_i$: 第 $i$ 区間のカウンターパーティーのデフォルト確率、$v_i$: 損失の現在価値。

### ガウスコピュラ（1因子モデル）

$$x_i = a_i F + \sqrt{1 - a_i^2}\, Z_i$$

<!-- Hull eq. (24.7) -->

条件付きデフォルト確率：

$$Q_i(T \mid F) = N\!\left(\frac{N^{-1}[Q_i(T)] - a_i F}{\sqrt{1 - a_i^2}}\right)$$

<!-- Hull eq. (24.8) -->

### 信用 VaR（Vasicek 公式）

$$V(X, T) = N\!\left(\frac{N^{-1}[Q(T)] + \sqrt{\rho}\, N^{-1}(X)}{\sqrt{1 - \rho}}\right)$$

<!-- Hull eq. (24.10) -->

$X\%$ の確信度で、$T$ 年間のポートフォリオ損失割合は $V(X,T)$ を超えない。

## 4. アルゴリズム / 手順

### 1. 社債価格からハザードレートをブートストラップ

1. 最短満期社債を選ぶ。そのキャッシュフローと回収率からデフォルト損失の現在価値を期待損失として等式を立てる。
2. Solver（Excel）または数値解法で第1期間のハザードレート $\lambda_1$ を求める。
3. $\lambda_1$ 既知のもとで次の満期社債に進み $\lambda_2$ を求める。繰り返す（§24.4, Example 24.2 参照）。

### 2. Merton モデルの反復解法

既知量: 株式価値 $E_0$、株式ボラティリティ $\sigma_E$、債務額 $D$、無リスク金利 $r$、期間 $T$

1. 初期値 $V_0 = E_0 + D$、$\sigma_V = \sigma_E$ で始める。
2. $d_1, d_2$ を計算し、式 (24.3) と (24.4) の連立方程式残差を評価する。
3. `scipy.optimize.fsolve`（または Excel Solver）で $(V_0, \sigma_V)$ に収束させる。
4. $Q = N(-d_2)$ でリスク中立デフォルト確率を得る。

### 3. クレジットスプレッドからリスク中立デフォルト確率を推定

1. 社債利回り $y$ とリスクフリーレート $y_{\rm nd}$ からスプレッド $s = y - y_{\rm nd}$ を計算する。
2. 回収率 $R$ を仮定し（通常 40%）、$\bar{\lambda} = s / (1 - R)$ を求める。
3. $Q(T) = 1 - e^{-\bar{\lambda} T}$ で累積デフォルト確率を得る。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq, fsolve


def survival_prob(t, hazard):
    """S(t) = exp(-integral of hazard).

    hazard: float (constant) or list of annual piecewise-constant rates.
    """
    if np.isscalar(hazard):
        return math.exp(-hazard * t)
    # piecewise constant: hazard[k] applies to year k (0-indexed)
    full_years = int(t)
    frac = t - full_years
    total = sum(hazard[:full_years]) + hazard[min(full_years, len(hazard) - 1)] * frac
    return math.exp(-total)


def default_prob_from_spread(spread, recovery=0.4):
    """Hull's approximation: lambda = s / (1 - R).

    Returns average hazard rate (not cumulative probability).
    Use 1 - exp(-lambda * T) for Q(T).
    """
    return spread / (1.0 - recovery)


def cumulative_default_prob(spread, T, recovery=0.4):
    """Q(T) from constant hazard approximation."""
    lam = default_prob_from_spread(spread, recovery)
    return 1.0 - math.exp(-lam * T)


def merton_default_prob(V0, D, r, sigma_V, T):
    """Risk-neutral default probability N(-d2) from Merton model."""
    d2 = (math.log(V0 / D) + (r - 0.5 * sigma_V ** 2) * T) / (sigma_V * math.sqrt(T))
    return float(norm.cdf(-d2))


def merton_distance_to_default(V0, D, r, sigma_V, T):
    """KMV distance-to-default = d2."""
    return (math.log(V0 / D) + (r - 0.5 * sigma_V ** 2) * T) / (sigma_V * math.sqrt(T))


def merton_solve_V_sigmaV(E0, sigma_E, D, r, T):
    """Iteratively solve for V0, sigma_V given E0, sigma_E (Hull §24.6).

    Returns (V0, sigma_V).
    """
    def equations(x):
        V0, sigma_V = x
        if V0 <= 0 or sigma_V <= 0:
            return [1e10, 1e10]
        d1 = (math.log(V0 / D) + (r + 0.5 * sigma_V ** 2) * T) / (sigma_V * math.sqrt(T))
        d2 = d1 - sigma_V * math.sqrt(T)
        eq1 = V0 * norm.cdf(d1) - D * math.exp(-r * T) * norm.cdf(d2) - E0
        eq2 = norm.cdf(d1) * sigma_V * V0 - sigma_E * E0
        return [eq1, eq2]

    sol = fsolve(equations, [E0 + D, sigma_E], full_output=False)
    return float(sol[0]), float(sol[1])


def credit_var_vasicek(Q_T, rho, confidence=0.999):
    """Vasicek formula for worst-case default rate V(X, T).

    Hull eq. (24.10). Returns fraction of portfolio defaulting.
    """
    num = norm.ppf(Q_T) + math.sqrt(rho) * norm.ppf(confidence)
    return float(norm.cdf(num / math.sqrt(1.0 - rho)))


# --- Examples ---
print("=== Spread → hazard rate ===")
lam = default_prob_from_spread(0.02)           # 200 bp spread, R=0.4
print(f"lambda = {lam:.4f}, Q(5y) = {cumulative_default_prob(0.02, 5):.4f}")

print("\n=== Merton model ===")
# Hull Example 24.3: E0=3, sigma_E=0.80, D=10, r=0.05, T=1
V, sV = merton_solve_V_sigmaV(E0=3.0, sigma_E=0.80, D=10.0, r=0.05, T=1.0)
PD = merton_default_prob(V, 10.0, 0.05, sV, 1.0)
DD = merton_distance_to_default(V, 10.0, 0.05, sV, 1.0)
print(f"V0={V:.3f}, sigma_V={sV:.4f}, PD={PD:.4f}, DD={DD:.4f}")

print("\n=== Credit VaR (Vasicek) ===")
# Hull Example 24.8: Q=0.02, rho=0.1, X=99.9%
v = credit_var_vasicek(Q_T=0.02, rho=0.1, confidence=0.999)
print(f"Worst-case default rate = {v:.4f} (Hull: 0.128)")
```

## 6. 注意点 / 典型的なミス

- **リスク中立 vs 実世界のデフォルト確率**: リスク中立確率は通常 5〜10 倍高い（Table 24.2）。デリバティブ価格付けにはリスク中立確率を、信用 VaR やシナリオ分析には実世界確率を使う。両者を混同すると CVA の過小/過大計上につながる。
- **回収率の想定**: 回収率 $R$ はシニア無担保で通常 40% が参照されるが、劣後債や業種で大きく異なる（好況期は 60%、不況期は 30% 程度）。高デフォルト環境では回収率も低下する（負の相関）。
- **スプレッド近似の精度**: $\bar{\lambda} \approx s/(1-R)$ は一次近似であり、クーポン付き債券や複雑なキャッシュフロー構造では積分を用いた精密計算（Example 24.2 の手法）が必要。
- **Merton モデルの限界**: 単一債務・ゼロクーポン債の仮定が現実と乖離しやすい。KMV はこれを多層債務構造に拡張し、$d_2$ を単調変換して EDF に換算することでモデルの乖離を経験的に補正する。
- **Wrong-way risk**: CVA の標準計算はデフォルト確率とエクスポージャーが独立と仮定する。Wrong-way risk（正の相関）が存在すると CVA を過小評価する。典型例は相手方が自社と同一業種である場合。
- **ダウングレードトリガー**: 急激な格下げには機能しない（AIG の事例）。複数のデリバティブ相手に同一トリガーがある場合、担保要求が集中してトリガーの有効性が失われる。
- **ガウスコピュラの単純化**: 実際の信用損失分布は左右非対称で heavy tail を持つ。単一因子ガウスコピュラはこれを過小評価しやすく、2007–2008 年の金融危機で問題が顕在化した。
- **リスクフリーレートの選択**: 国債レートは流動性プレミアム分だけ低くなりすぎる。OIS レートまたは CDS スプレッドを基準にした方がより適切なハザードレートを与える（§24.4）。

## 7. 関連トピック

- See: topics/credit.md, Ch.9 (CVA/DVA の導入 — デフォルト確率を用いた XVA 計算), Ch.25 (CDS — CDS スプレッドからハザードレートを抽出), Ch.32 (ジャンプ拡散モデルによるデフォルトモデリング), Ch.8 (ABS CDO と金融危機 — デフォルト相関の影響の実例).
