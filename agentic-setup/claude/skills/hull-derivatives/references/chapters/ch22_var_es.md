# Ch.22 Value at Risk and Expected Shortfall

> **Source**: Hull 11e, Chapter 22 (pp. 514-541). Paraphrased summary for personal use.

## 1. 要点

- VaR は「信頼水準 $\alpha$（例: 99%）のもとで $N$ 日間に超えないと確信できる損失上限値」を単一数値で表すリスク指標。ES（期待ショートフォール、別名 CVaR）は VaR を超えた場合の条件付き期待損失であり、テール全体を反映する。
- 時系列的に独立・正規分布する場合は $N$ 日 VaR $= \sqrt{N} \times$ 1 日 VaR でスケールできるが、ボラティリティクラスタリングや裾の重さがある実際の市場ではこの仮定は近似にすぎない。
- 計算手法は大きく **ヒストリカル・シミュレーション**（実際の過去シナリオを再現）と **モデル構築法（分散共分散法）**（正規分布を仮定した解析解）の 2 種類に分かれ、オプションを含む場合は **モンテカルロ** または デルタ-ガンマ 二次近似が必要。
- VaR は劣加法性（subadditivity）を満たさない非コヒーレントな指標であり、分散化によってリスクが増大する例を構築できる。ES はコヒーレントな指標である。Basel IV（FRTB）はこの理由から市場リスク資本の基準を VaR 99% から ES 97.5% へ移行した。
- バックテスティング（事後検証）で VaR モデルの精度を確認するが、ES は VaR より事後検証が難しい。主成分分析（PCA）を使うと高相関の金利変数群を少数のファクターに集約して VaR 計算を効率化できる。

## 2. キー用語

- **VaR (Value at Risk)**: 信頼水準 $\alpha$ で $N$ 日間に損失が超えない上限値。$\Pr(L > \mathrm{VaR}_\alpha) = 1-\alpha$
- **ES (Expected Shortfall)**: VaR を超える損失の条件付き期待値。C-VaR / Expected Tail Loss とも呼ばれる。
- **ヒストリカル・シミュレーション**: 過去 501 日（500 シナリオ）の市場変数変化を今日の保有ポートフォリオに適用し、損益分布を構築する手法。
- **モデル構築法（分散共分散法）**: ポートフォリオのリターンが多変量正規分布に従うと仮定し、解析的に VaR/ES を計算する。
- **デルタ近似**: オプションを含むポートフォリオで $\Delta P \approx \delta \cdot \Delta S$ とする線形近似。
- **デルタ-ガンマ近似**: $\Delta P \approx \delta \cdot \Delta S + \tfrac{1}{2}\gamma (\Delta S)^2$ とする二次近似。
- **Stressed VaR / Stressed ES**: ポートフォリオに最も不利な 251 日間の過去データを用いて計算する規制上の指標。
- **Cornish-Fisher 展開**: 非正規分布の高次モーメント（歪度・尖度）からパーセンタイルを近似する手法。
- **バックテスティング**: 実際の損益が VaR 超過した日数の割合を確認し、モデルを検証する手続き。
- **コヒーレントなリスク指標**: 劣加法性・正斉次性・単調性・変換不変性の 4 公理を満たす指標。ES は満たすが VaR は満たさない。
- **キャッシュフロー・マッピング**: 債券・金利デリバティブのキャッシュフローを標準満期のゼロクーポン債ポジションに分解する操作。
- **主成分分析 (PCA)**: 高相関変数群を互いに無相関なファクターに変換し、少数のファクターで分散のほとんどを説明する統計手法。

## 3. 主要公式

### VaR の定義

$$
\Pr\!\left(L > \mathrm{VaR}_\alpha\right) = 1 - \alpha
$$

- $L$: 損失（正値が損失）
- $\alpha$: 信頼水準（例: 0.99）

<!-- Hull eq. (22.X) — definition, §22.1 -->

### ES の定義

$$
\mathrm{ES}_\alpha = E\!\left[L \mid L > \mathrm{VaR}_\alpha\right]
$$

<!-- Hull §22.1 -->

### $\sqrt{N}$ スケーリング（iid 正規仮定下）

$$
\mathrm{VaR}_{N\text{-day}} = \sqrt{N} \cdot \mathrm{VaR}_{1\text{-day}}, \qquad
\mathrm{ES}_{N\text{-day}} = \sqrt{N} \cdot \mathrm{ES}_{1\text{-day}}
$$

<!-- Hull p. 517 -->

### モデル構築法 VaR（線形ポートフォリオ、正規分布）

$$
\mathrm{VaR} = z_\alpha \cdot \sigma_P, \qquad
\sigma_P = \sqrt{\mathbf{\alpha}^\top C\, \mathbf{\alpha}} = \sqrt{\mathbf{w}^\top \Sigma\, \mathbf{w}}
$$

- $z_\alpha = \Phi^{-1}(\alpha)$（例: 99% では 2.326）
- $C$: 分散共分散行列（日次）
- $\mathbf{\alpha}$: 各資産へのドル投資額ベクトル
- $\mathbf{w}$: 各資産ウェイトベクトル（ポートフォリオ収益率ベースの場合）

<!-- Hull eq. (22.3), (22.4) -->

### 正規分布下での ES

$$
\mathrm{ES}_\alpha = \sigma_P \cdot \frac{\phi(z_\alpha)}{1 - \alpha}
\quad (\mu = 0 \text{ と仮定})
$$

- $\phi(\cdot)$: 標準正規密度関数

一般に平均 $\mu$ を含む場合（損失分布）:

$$
\mathrm{ES} = \mu + \sigma \cdot \frac{e^{-z_\alpha^2/2}}{\sqrt{2\pi}(1-\alpha)}
$$

<!-- Hull eq. (22.1) -->

### ポートフォリオ分散（線形モデル）

$$
\sigma_P^2 = \sum_{i=1}^n \sum_{j=1}^n \rho_{ij}\, \alpha_i \alpha_j \sigma_i \sigma_j
= \sum_{i=1}^n \sum_{j=1}^n \mathrm{cov}_{ij}\, \alpha_i \alpha_j
$$

<!-- Hull eq. (22.3), (22.4) -->

### デルタ-ガンマ近似（オプションを含む場合）

$$
\Delta P \approx \delta \cdot \Delta S + \tfrac{1}{2}\gamma (\Delta S)^2
$$

より一般に $n$ 変数の場合:

$$
\Delta P = \sum_{i=1}^n S_i \delta_i \Delta x_i + \sum_{i=1}^n \sum_{j=1}^n \tfrac{1}{2} S_i S_j \gamma_{ij} \Delta x_i \Delta x_j
$$

<!-- Hull eq. (22.7), (22.8) -->

### Cornish-Fisher 展開（非正規 VaR）

$\Delta P$ の歪度・尖度からモーメントを計算し、それを使って正規分布の分位点を補正してパーセンタイルを推定する。詳細は Hull Technical Note 10 参照。

### ヒストリカル・シミュレーション（シナリオ構築）

$v_i$ を Day $i$ の市場変数値とすると、今日（Day $n$）の変数に第 $i$ シナリオを適用した場合の仮想値:

$$
\text{Value under scenario } i = v_n \cdot \frac{v_i}{v_{i-1}}
$$

<!-- Hull p. 517 -->

## 4. アルゴリズム / 手順

### 1. ヒストリカル・シミュレーション VaR/ES

1. 対象ポートフォリオに影響する市場変数（株価指数、為替、金利など）を特定する。
2. 直近 501 営業日分のデータを収集し、500 の日次変化シナリオを作成する。
3. 各シナリオについて、今日の保有ポートフォリオを仮想価格で再評価し、1 日損益 $\Delta P_i$ を計算する。
4. 500 の損失を昇順にソートし、99% VaR は第 5 番目に大きい損失（= 損失の 99th パーセンタイル）とする。
5. ES は VaR を超えた上位 5 シナリオの損失の平均値とする。

### 2. モデル構築法（分散共分散法）VaR — 線形ポートフォリオ

1. 各資産の日次ボラティリティ $\sigma_i$ と相関係数 $\rho_{ij}$（または分散共分散行列 $C$）を推定する。
2. ポートフォリオ分散 $\sigma_P^2 = \mathbf{\alpha}^\top C\, \mathbf{\alpha}$ を計算する。
3. 1 日 VaR $= z_\alpha \cdot \sigma_P$（例: $z_{0.99} = 2.326$）。
4. $N$ 日 VaR $= \sqrt{N} \times$ 1 日 VaR。
5. ES $= \sigma_P \cdot \phi(z_\alpha) / (1-\alpha)$。

### 3. モンテカルロ VaR

1. 現在の市場変数値でポートフォリオを評価する。
2. $\Delta x_i$ の多変量正規分布からサンプルを 1 つ生成する。
3. 各市場変数を 1 日後の仮想値に更新しポートフォリオを再評価する。
4. 損益 $\Delta P$ を記録する。
5. ステップ 2-4 を多数回（例: 5,000 回）繰り返し、損失分布を構築する。
6. $\alpha$ パーセンタイルを VaR とし、超過損失の平均を ES とする。

### 4. ストレステスト

1. 金融危機など特定の過去の悪化期間（例: 251 営業日）を識別する（Stressed VaR/ES）。
2. その期間のシナリオを用いてポートフォリオの損失を計算する。
3. 仮想シナリオ（平行移動、急激な為替変動など）でも同様に再評価する。
4. 通常の VaR では捕捉しにくいテールリスクを把握する。

### 5. バックテスティング

1. 過去 250 営業日（約 1 年分）の各日について、当日の 1 日 99% VaR 推計値と実際の損益を照合する。
2. 実損失が VaR を超えた日数（例外回数）をカウントする。
3. 期待される例外回数は 250 × 1% = 2.5 日（約 2-3 回）。
4. Kupiec POF 検定（例外回数の二項検定）や Christoffersen 条件付きカバレッジ検定で統計的に評価する。
5. 超過が多すぎる場合（例: 7% 超）はモデルを再検討する。Basel 規制では超過回数でモデルの採用可否・乗数 $k$ を決定。

## 5. Python reference

```python
import numpy as np
from scipy.stats import norm


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


def portfolio_sigma(weights, cov):
    """Portfolio daily std dev from dollar weights and covariance matrix."""
    w = np.asarray(weights, dtype=float)
    return float(np.sqrt(w @ cov @ w))


def scale_var(var_1d, n_days):
    """Sqrt-time scaling under iid normal assumption."""
    return var_1d * np.sqrt(n_days)


def backtest_var(pnl_series, var_series, alpha=0.99):
    """Count VaR exceptions; expected rate = 1 - alpha."""
    losses = -np.asarray(pnl_series)
    vars_ = np.asarray(var_series)
    exceptions = int(np.sum(losses > vars_))
    expected = len(pnl_series) * (1 - alpha)
    return exceptions, expected


# --- Example: 2-asset portfolio ---
w = np.array([1_000_000, 2_000_000], dtype=float)
cov = np.array([[0.0001, 0.00005],
                [0.00005, 0.0004]])

sigma = portfolio_sigma(w, cov)
var_1d, es_1d = parametric_var_es(sigma, alpha=0.99)
var_10d = scale_var(var_1d, 10)

print(f"Portfolio sigma (daily): {sigma:,.0f}")
print(f"99% 1-day VaR:  {var_1d:,.0f},  ES: {es_1d:,.0f}")
print(f"99% 10-day VaR: {var_10d:,.0f}")

# Historical simulation example
rng = np.random.default_rng(42)
sim_pnl = rng.normal(0, sigma, 500)
h_var, h_es = historical_var_es(sim_pnl, alpha=0.99)
print(f"Historical 99% VaR: {h_var:,.0f},  ES: {h_es:,.0f}")
```

## 6. 注意点 / 典型的なミス

- **$\sqrt{N}$ スケーリングの乱用**: iid 正規リターンを仮定しているが、実際の市場ではボラティリティ・クラスタリングや裾の重さが存在し、長期ホライズンのリスクは過少評価される傾向がある。
- **VaR は非コヒーレント**: 分散化によって VaR が増大するポートフォリオを構築できる（劣加法性を満たさない）。ES はコヒーレントであり FRTB はこの理由で ES 97.5% に移行した。
- **線形モデルはオプションに不適**: デルタ近似はガンマを無視する。オプションを多く含むポートフォリオでは二次近似（デルタ-ガンマ）またはモンテカルロが必要。
- **ヒストリカル・シミュレーションの外挿不能**: 過去に観測されていないシナリオを推計できない。COVID-19 ショック前にはその後の急落が VaR に反映されなかった。
- **ポートフォリオ不変仮定**: VaR は「今日のポートフォリオが $N$ 日間変化しない」前提で計算するが、実際には毎日変化する。
- **ES のバックテストの困難性**: VaR は超過/非超過の二値で検証できるが、ES は超過損失の大きさも必要で検証が複雑になる。
- **Basel の乗数**: 99% VaR を計算しても、規制資本は VaR × 乗数 $k$（最低 3.0）で決まる。VaR 数値 = 資本要件ではない。

## 7. 関連トピック

- See: [topics/risk_management.md](../topics/risk_management.md)
- Ch.23 (ボラティリティ・相関の推定: EWMA, GARCH — VaR 計算のインプット)
- Ch.19 (ギリシャ文字: デルタ・ガンマ — デルタ-ガンマ近似の基礎)
- Ch.21 (数値計算手法: モンテカルロ — モンテカルロ VaR の実装基盤)
- Ch.24 (信用リスク — CVaR・信用 VaR との区別)
