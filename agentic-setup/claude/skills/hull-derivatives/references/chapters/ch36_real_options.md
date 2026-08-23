# Ch.36 Real Options

> **Source**: Hull 11e, Chapter 36 (pp. 802-814). Paraphrased summary for personal use.

## 1. 要点

- 伝統的 NPV アプローチは埋め込みオプション（放棄・拡張・繰延など）を正しく割り引けない。各オプションのリスク特性は基本プロジェクトと異なり、適切な割引率が不明なため。
- リスク中立評価を実物資産に拡張できる：各確率変数の期待成長率をリスクの市場価格 $\lambda$ 分だけ引き下げ、キャッシュフローをリスクフリーレートで割り引く。
- 市場価格リスク $\lambda$ は CAPM から推定できる：$\lambda = (\rho/\sigma_m)(\mu_m - r)$（eq.36.2）。ヒストリカルデータがなければ代理変数や主観的判断を用いる。
- 埋め込みオプション（放棄・拡張・縮小・繰延・延命）はそれぞれアメリカン put / call に対応し、二項ツリーの後ろ向き DP で評価する。
- 複数オプションが共存する場合は非加法的（相互作用する）ため、ノードごとに状態（拡張済み/放棄済み等）を明示的に保持して合算しなければならない。

## 2. キー用語

- **Real option（実物オプション）**: 実物資産への投資機会に内在する経営上の柔軟性をオプションとして評価する手法。
- **NPV（正味現在価値）**: 将来キャッシュフローをリスク調整済み割引率で割り引いた現在価値。静的 NPV は柔軟性を無視する。
- **Market price of risk（リスクの市場価格）** $\lambda$: 変数 $\theta$ の超過収益率をボラティリティで割った量。$\lambda = (\mu - r)/\sigma$（eq.36.1）。
- **Risk-neutral growth rate（リスク中立成長率）**: 実世界の成長率 $m$ からリスクプレミアム分 $\lambda s$ を差し引いた $m - \lambda s$。
- **Option to abandon（放棄オプション）**: プロジェクトをいつでも清算できる権利。ストライク＝清算価値のアメリカン put。
- **Option to expand（拡張オプション）**: 追加投資で生産規模を拡大できる権利。追加容量コストをストライクとするアメリカン call。
- **Option to defer（繰延オプション）**: 投資を将来に延期できる権利。プロジェクト価値をアンダーライングとするアメリカン call。
- **Contraction option（縮小オプション）**: 事業規模を縮小できる権利。削減される将来支出の PV をストライクとするアメリカン put。
- **Compound option（複合オプション）**: 多段階投資のように、あるオプションの行使がさらにオプションを生み出す構造。
- **LSM（Longstaff-Schwartz）法**: モンテカルロと最小二乗回帰を組み合わせてアメリカン型オプションを評価する手法（Section 27.8）。

## 3. 主要公式

### 静的 NPV（離散・リスク調整割引率）

$$
\text{NPV} = \sum_{t=0}^{T} \frac{CF_t}{(1+r_{\text{adj}})^t}
$$

- $CF_t$: $t$ 期のインクリメンタルキャッシュフロー
- $r_{\text{adj}}$: CAPM ベースのリスク調整済み割引率

### リスクの市場価格の定義

$$
\lambda = \frac{\mu - r}{\sigma}
$$

<!-- Hull eq. (36.1) -->

- $\mu$: 変数 $\theta$ に依存する投資資産の期待収益率
- $r$: リスクフリーレート
- $\sigma$: 投資資産収益率のボラティリティ

### CAPM によるリスクの市場価格推定

$$
\lambda = \frac{\rho}{\sigma_m}(\mu_m - r)
$$

<!-- Hull eq. (36.2) -->

- $\rho$: 変数の変化率と市場インデックス収益率の瞬間相関
- $\sigma_m$: 市場インデックスのボラティリティ
- $\mu_m$: 市場インデックスの期待収益率

### リスク中立世界でのプロセス補正

実世界で $d\theta/\theta = m\,dt + s\,dz$ に従う変数は、リスク中立世界では成長率を補正して

$$
d\theta/\theta = (m - \lambda s)\,dt + s\,dz
$$

と扱い、キャッシュフローをリスクフリーレートで割り引く。

### 連続時間プロジェクト価値プロセス（市場価格リスク補正後）

$$
dV = (\mu - \lambda\sigma)V\,dt + \sigma V\,dz \quad \text{under } \mathbb{Q}
$$

- $V$: プロジェクト価値
- $\lambda\sigma$: リスクプレミアム補正項

### 二項ツリーのパラメータ（実物オプション版）

$$
u = e^{\sigma\sqrt{\Delta t}}, \quad d = \frac{1}{u}, \quad p = \frac{e^{r\Delta t} - d}{u - d}
$$

### ベルマン方程式（後ろ向き DP）

$$
V_t = \max\!\left(\text{exercise now},\; e^{-r\Delta t}\,\mathbb{E}[V_{t+1}]\right)
$$

- **繰延オプション（defer）**: $\text{exercise now} = V - K$（投資コスト $K$）
- **放棄オプション（abandon）**: $\text{exercise now} = \text{salvage}$
- **拡張オプション（expand）**: $\text{exercise now} = \alpha V - C_{\text{expand}}$（$\alpha$ は拡張倍率）

### 商品価格プロセス（Hull eq.36.3）

$$
d\ln S = [\theta(t) - a\ln S]\,dt + \sigma\,dz
$$

<!-- Hull eq. (36.3) -->

- 平均回帰型（Ornstein-Uhlenbeck）。Section 35.4 のツリー構築に対応。

## 4. アルゴリズム / 手順

1. **プロジェクト価値ツリーの構築**
   - 対象変数（商品価格、売上など）のリスク中立プロセスを確定する（$m - \lambda s$ で補正）。
   - 二項または三項ツリーを構築し、各ノードのキャッシュフローを計算する。
   - ノードに必要な状態変数（拡張済み・放棄済みなど）を付与する。

2. **後ろ向き DP による最適行使**
   - 末端ノードでペイオフを計算する。
   - 1 期前に戻り、各ノードで「今すぐ行使」と「継続価値 $e^{-r\Delta t}\mathbb{E}[V]$」を比較し大きい方を採用する。
   - 複数オプションが存在する場合は各状態について独立に計算し、不可能な遷移（放棄後は拡張不可等）を除外する。

3. **MC + LSM による経路依存実物オプション**
   - 多変数確率過程をモンテカルロでシミュレートする（Section 27.8）。
   - 各タイムステップで「継続価値」を状態変数の多項式に最小二乗回帰して推定する。
   - 逐次比較で最適行使タイミングを決定し、割り引いてオプション価値を算出する。

4. **感度分析（静的 NPV との比較）**
   - 静的 NPV（オプションなし）と実物オプション NPV を計算して差（オプションプレミアム）を確認する。
   - $\sigma$、$\lambda$、投資コスト $K$ の変化に対する感度をシナリオ分析する。
   - プロジェクトが静的 NPV < 0 でも実物オプション調整後に正となりうることを明示する。

## 5. Python reference

```python
import math
import numpy as np


def project_npv(cash_flows, r):
    """Static NPV (discrete, risk-adjusted rate).

    Parameters
    ----------
    cash_flows : list[float]
        CF at t=0, 1, 2, ... (negative for investments)
    r : float
        Risk-adjusted discount rate per period
    """
    return sum(cf / (1 + r) ** t for t, cf in enumerate(cash_flows))


def binomial_real_option_defer(V0, sigma, T, r, K, N):
    """Defer option: at each node decide to invest now (V - K) or wait.

    Modelled as American call on project value V (no convenience yield).

    Parameters
    ----------
    V0    : float  current project value
    sigma : float  project value volatility
    T     : float  option horizon (years)
    r     : float  risk-free rate (continuous)
    K     : float  investment cost (strike)
    N     : int    number of time steps
    """
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    j = np.arange(N + 1)
    V_T = V0 * (u ** (N - j)) * (d ** j)
    payoff = np.maximum(V_T - K, 0.0)

    for step in range(N - 1, -1, -1):
        j_s = np.arange(step + 1)
        V_step = V0 * (u ** (step - j_s)) * (d ** j_s)
        cont = disc * (p * payoff[:-1] + (1 - p) * payoff[1:])
        immediate = np.maximum(V_step - K, 0.0)
        payoff = np.maximum(cont, immediate)

    return float(payoff[0])


def binomial_real_option_abandon(V0, sigma, T, r, salvage, N):
    """Abandon option: at each node receive max(continuation, salvage).

    Modelled as American put with strike = salvage on project value V.

    Parameters
    ----------
    V0      : float  current project value
    sigma   : float  project value volatility
    T       : float  option horizon (years)
    r       : float  risk-free rate (continuous)
    salvage : float  liquidation / salvage value (strike)
    N       : int    number of time steps
    """
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)

    j = np.arange(N + 1)
    V_T = V0 * (u ** (N - j)) * (d ** j)
    payoff = np.maximum(V_T, salvage)

    for step in range(N - 1, -1, -1):
        cont = disc * (p * payoff[:-1] + (1 - p) * payoff[1:])
        payoff = np.maximum(cont, salvage)

    return float(payoff[0])


# Example
print("Static NPV :", project_npv([-100, 30, 35, 40, 45], r=0.10))
print("Defer option:", binomial_real_option_defer(
    V0=100, sigma=0.30, T=2.0, r=0.05, K=110, N=200))
print("Abandon opt :", binomial_real_option_abandon(
    V0=100, sigma=0.30, T=2.0, r=0.05, salvage=70, N=200))
```

## 6. 注意点 / 典型的なミス

- **取引可能なアンダーライングが存在しない**: プロジェクト価値 $V$ は市場で取引されないため、$\sigma$ と $\lambda$ をキャッシュフロー変動や類似上場企業から推定せざるを得ない。この推定は本質的に主観的であり、感度分析が必須。
- **λ の推定エラー**: CAPM の $\lambda = (\rho/\sigma_m)(\mu_m - r)$ を使う際、$\rho$（変数と市場指数の相関）は短い時系列や性質の異なる代理変数に基づくことが多い。ゼロと仮定することが適切なケースもある。
- **最適行使の仮定**: 理論値はマネジメントが常に最適に行使する前提だが、実際の行使は遅れる・過剰行使されるケースがある。実際の option value は理論上限を下回る傾向がある。
- **複数オプションの非加法性**: 放棄オプション価値 + 拡張オプション価値 ≠ 両方保有時の合算価値。オプション同士が相互に影響するため、必ず同時に状態管理して評価する。
- **静的 NPV < 0 でも投資価値あり**: 繰延・拡張・放棄オプションを加味すると option-adjusted NPV が正になりうる。NPV のみで却下するのは誤り。
- **割引率の混用**: リスク中立アプローチでは成長率補正後のキャッシュフローをリスクフリーレートで割り引く。リスク調整済み割引率と混用しない。

## 7. 関連トピック

- See: [topics/real_options.md](../topics/real_options.md), Ch.13 (二項ツリーの基礎), Ch.21 (数値計算・LSM), Ch.27 (Section 27.8 LSM によるアメリカンオプション), Ch.28 (マルチンゲール・リスク中立尺度), Ch.35 (商品・エネルギー価格の確率過程), Ch.5 (先物価格・コストオブキャリー).
