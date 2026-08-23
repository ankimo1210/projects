# Ch.25 Credit Derivatives

> **Source**: Hull 11e, Chapter 25 (pp. 587-613). Paraphrased summary for personal use.

## 1. 要点

- クレジット・デリバティブはクレジット・リスクを売買可能にする金融契約であり、最も一般的な形態がクレジット・デフォルト・スワップ（CDS）である。
- CDS のバリュエーションはプロテクション・レッグ（期待損失の現在価値）とプレミアム・レッグ（スプレッド支払いの現在価値）を等置することで行われ、ハザード・レートはCDSスプレッドからブートストラップで推定できる。
- 信用インデックス（CDX NA IG、iTraxx Europe）はそれぞれ125社の均等加重バスケットであり、ポートフォリオ全体の信用保護を効率的に取引する手段となっている。
- バスケットCDS（nth-to-default）や合成CDOのトランシェ定価には、Gaussianコピュラ因子モデルによるデフォルト相関のモデル化が標準的に使用される。
- トランシェの市場価格からインプライド相関（コンパウンド相関・ベース相関）を逆算することで、モデルの整合性と相関スマイルが観察される。

## 2. キー用語

- **CDS（Credit Default Swap）**: 参照企業がデフォルトした場合に元本損失を補償する保険契約型のスワップ。
- **Reference Entity**: CDS が参照する企業または国。
- **Credit Event**: デフォルト、債務不履行、リストラクチャリングなど、CDSの支払い事由となる事象。
- **CDS Spread**: 保護購入者が売却者に支払う年間保険料率（bps）。CDSの公正価格を表す。
- **CDS–Bond Basis**: CDS スプレッド − 社債利回りスプレッド。理論上ゼロに近いが実際は乖離する。
- **Cheapest-to-Deliver Bond**: 物理決済時に参照企業が発行した債券の中で最も安い債券を引き渡せるオプション。
- **Hazard Rate (λ)**: 瞬間デフォルト強度。生存確率 $S(t) = e^{-\lambda t}$（定数ハザード）。
- **Recovery Rate (R)**: デフォルト直後の債券価値／額面価値。標準的に40%。
- **Risky Annuity**: CDS スプレッド1単位に対応する、生存確率加重ディスカウント済みキャッシュフローの現在価値。
- **Credit Index (CDX/iTraxx)**: 均等加重バスケット。インデックス・スプレッドはほぼ各社CDS スプレッドの平均。
- **Fixed Coupon CDS**: 2009年Big Bangプロトコル以降、クーポンは100bpか500bpに標準化され、差額はアップフロント支払いで調整。
- **Binary CDS**: デフォルト時の支払いが固定額（回収率に依存しない）のCDS。
- **Total Return Swap (TRS)**: 参照資産のトータルリターン（クーポン＋値上がり益）を変動金利プラス・スプレッドと交換するスワップ。
- **CDO（Collateralized Debt Obligation）**: 債券ポートフォリオから複数トランシェ（エクイティ・メザニン・シニア等）を生成する構造化商品。
- **Synthetic CDO**: CDSポートフォリオを参照するCDO。実際に債券を保有しない。
- **Tranche**: CDOの損失吸収区分。attachment point ($\alpha_L$) ～ detachment point ($\alpha_H$)。
- **Compound Correlation (Tranche Correlation)**: 特定トランシェ単独の市場価格に整合するコピュラ相関 $\rho$。
- **Base Correlation**: $\{0, \alpha_q\}$ トランシェ（0から特定 detachment まで）の市場整合相関。モノトーン増加でスキュー形状を示す。
- **Correlation Smile/Skew**: トランシェ毎にインプライド相関が異なる現象。Gaussianコピュラの不完全性を反映。
- **Basket CDS (nth-to-default)**: バスケット内でn番目のデフォルトが発生したときに支払われるCDS。
- **Single-Tranche Trading**: CDO全体を組成せず特定トランシェのみを取引すること。

## 3. 主要公式

### CDS パー・スプレッド

$$
s = \frac{\text{PV(protection leg)}}{\text{PV(risky annuity)}}
$$

<!-- Hull eq. (25.2) の文脈 -->

**Protection leg**（元本1、回収率 $R$、リスクフリー割引率 $r$）:

$$
\text{PV}_{\text{prot}} = (1-R)\int_0^T e^{-rt}\,(-dS(t)) = (1-R)\int_0^T e^{-rt}\,\lambda(t)S(t)\,dt
$$

**Premium leg**（スプレッド $s$、支払い連続近似）:

$$
\text{PV}_{\text{prem}} = s\int_0^T e^{-rt} S(t)\,dt
$$

実際には四半期払い＋デフォルト時アクルーアルを加算した離散和を使用する（Hull Tables 25.2–25.4 参照）。

<!-- Hull §25.2 -->

### 定数ハザード下の近似スプレッド

$$
s \approx \lambda(1-R)
$$

生存確率 $S(t) = e^{-\lambda t}$、割引率を省略した1次近似。

<!-- Hull §25.2 近似 -->

### CDSブートストラップ

各テナー $T_k$ について順次:

$$
s_k = \frac{(1-R)\sum_{i} e^{-r t_i}\,\Delta S_i}{\sum_{j} e^{-r t_j} S(t_j)\,\Delta t_j}
$$

を $s_k$ が市場観測値に一致するよう $\lambda_k$（区分定数ハザード）を数値的に解く。

<!-- Hull §25.2, §25.4 -->

### 信用インデックス（CDX / iTraxx）

均等加重（125社）のバスケットCDS:

$$
s_{\text{index}} \approx \frac{1}{n}\sum_{i=1}^n s_i
$$

厳密には最も高スプレッドの名義のウェイトが軽くなるため、単純平均よりわずかに低い。

<!-- Hull §25.3 -->

### Fixed Coupon CDS の価格

クーポン $c$、スプレッド $s$、デュレーション $D$（リスキー・アニュイティ）:

$$
P = 100 - 100 \times D \times (s - c)
$$

<!-- Hull §25.4 -->

### Gaussianコピュラ因子モデル

一因子モデル：企業 $i$ の標準正規変数:

$$
X_i = \sqrt{\rho}\,M + \sqrt{1-\rho}\,Z_i
$$

$M$：共通因子（市場）、$Z_i$：個別因子、$\rho$：コピュラ相関パラメータ。

<!-- Hull eq. (24.7), Ch.25 参照 -->

### 条件付きデフォルト確率（因子 $F$ 所与）

$$
Q(t \mid F) = N\!\left(\frac{N^{-1}[Q(t)] - \sqrt{\rho}\,F}{\sqrt{1-\rho}}\right)
$$

<!-- Hull eq. (25.5) -->

### 生存確率（定数ハザード）

$$
Q(t) = 1 - e^{-\lambda t}
$$

<!-- Hull eq. (25.6) -->

### 条件付き二項確率（$n$ 社同質ポートフォリオ）

$$
P(k, t \mid F) = \binom{n}{k} Q(t\mid F)^k [1 - Q(t\mid F)]^{n-k}
$$

<!-- Hull eq. (25.7) -->

### 合成CDO トランシェのブレークイーブン・スプレッド

$$
s = \frac{C}{A + B}
$$

$A$：割引済み期待プレミアム支払いの現在価値（リスキー・アニュイティ）、$B$：期待アクルーアルの現在価値、$C$：期待ペイオフの現在価値。

<!-- Hull eq. (25.4) -->

### Gaussianクアドラチャー（$F$ に関する積分）

$$
\int_{-\infty}^{\infty} \frac{1}{\sqrt{2\pi}} e^{-F^2/2}\,g(F)\,dF \approx \sum_{k=1}^{M} w_k\,g(F_k)
$$

<!-- Hull eq. (25.12) -->

## 4. アルゴリズム / 手順

### 1. CDSハザード曲線のブートストラップ（§25.2, §25.4）

1. 最短テナー（例：1年）から開始。
2. $s_1$ が市場スプレッドに一致するよう $\lambda_1$ を数値的に解く（bisection / brentq）。
3. $\lambda_1$ を固定し次のテナー $s_2$ から $\lambda_2$ を解く。
4. 全テナーを順次繰り返す（区分定数ハザード曲線が得られる）。

### 2. CDS バリュエーション（§25.2）

1. ハザード曲線から各時点の生存確率 $S(t_i) = \exp(-\sum_j \lambda_j \Delta t_j)$ を計算。
2. プロテクション・レッグ：$(1-R)\sum_i e^{-r t_i}(S_{i-1}-S_i)$。
3. プレミアム・レッグ（アニュイティ）：$(1/n_{\rm pay})\sum_j e^{-r t_j} S(t_j)$、アクルーアル項を加算。
4. $s = \text{protection} / \text{annuity}$。既存取引のMTMは固定スプレッドでのレッグ差額。

### 3. Gaussianコピュラ モンテカルロ（nth-to-default / CDOトランシェ）（§25.10）

1. 共通因子 $M \sim N(0,1)$ および個別因子 $Z_i \sim N(0,1)$ を多数シミュレーション。
2. $X_i = \sqrt{\rho} M + \sqrt{1-\rho} Z_i$ を算出。
3. $U_i = N(X_i)$ を一様乱数に変換し、デフォルト時刻 $\tau_i = -\ln(1-U_i)/\lambda_i$。
4. 各パスで $k$ 番目のデフォルト時刻（nth-to-default）またはトランシェ損失を集計。
5. 期待損失・プレミアムを割り引いてスプレッドを算出。

解析的手法（Gaussian quadrature）では上式を因子 $F$ に対して数値積分することで高速計算が可能（DerivaGem CDO ワークシート実装）。

### 4. インプライド相関の逆算（§25.10, ベース相関）

1. 各トランシェの市場スプレッドを取得。
2. **コンパウンド相関**：各トランシェ単独で $s_{\rm model}(\rho) = s_{\rm market}$ となる $\rho$ を反復探索（brentq）。
3. **ベース相関**：$\{0, \alpha_q\}$ トランシェの期待損失累積値を計算し、$\{0, \alpha_q\}$ トランシェが市場整合する $\rho_q$ を逆算。単調増加列が得られる。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


def cds_par_spread(hazard_curve, tenors, r=0.02, recovery=0.4, n_periods=4):
    """Par CDS spread for piecewise-constant hazard curve.

    hazard_curve: list of hazard rates per tenor bucket
    tenors: cumulative time points (years) matching hazard_curve
    r: flat discount rate (continuous)
    """
    T = tenors[-1]
    grid = np.linspace(0, T, int(T * n_periods) + 1)

    def lam_at(t):
        for i, te in enumerate(tenors):
            if t <= te:
                return hazard_curve[i]
        return hazard_curve[-1]

    lams = np.array([lam_at(t) for t in grid])
    # Survival probabilities
    S = np.exp(-np.cumsum(np.diff(grid, prepend=0) * lams))
    df = np.exp(-r * grid)
    # Protection leg: (1-R) * sum df * (S[i-1] - S[i])
    dS = np.diff(S, prepend=1.0)  # negative increments
    protection = (1 - recovery) * np.sum(df[1:] * (-dS[1:]))
    # Risky annuity (quarterly payment times)
    pay_times = np.arange(1 / n_periods, T + 1 / n_periods, 1 / n_periods)
    pay_S = np.array([
        math.exp(-sum(lam_at(s) * (1 / n_periods)
                      for s in np.arange(0, t, 1 / n_periods)))
        for t in pay_times
    ])
    pay_df = np.exp(-r * pay_times)
    annuity = (1 / n_periods) * np.sum(pay_S * pay_df)
    return float(protection / annuity)


def bootstrap_hazards(market_spreads, tenors, r=0.02, recovery=0.4):
    """Sequentially solve piecewise-constant hazards matching market CDS spreads."""
    hazards = []
    for k, _T_k in enumerate(tenors):
        def diff(h, k=k):
            cand = hazards + [h]
            return cds_par_spread(cand, tenors[:k + 1], r, recovery) - market_spreads[k]
        h = brentq(diff, 1e-6, 1.0)
        hazards.append(h)
    return hazards


def gaussian_copula_nth_default_mc(
    hazard_rates, rho, T, nth, n_paths=50_000, rng=None
):
    """First/nth-to-default basket probability using Gaussian copula factor model.

    Parameters
    ----------
    hazard_rates : list[float]  flat hazard rate per name
    rho          : float        copula correlation (common factor loading^2)
    T            : float        horizon (years)
    nth          : int          trigger on nth default (1 = first-to-default)
    """
    rng = rng or np.random.default_rng(0)
    n = len(hazard_rates)
    M = rng.standard_normal(n_paths)                   # common factor
    Z = rng.standard_normal((n_paths, n))              # idiosyncratic
    a = math.sqrt(rho)
    X = a * M[:, None] + math.sqrt(1 - rho) * Z       # eq. (24.7)
    U = norm.cdf(X)                                    # uniform marginals
    # Exponential default times consistent with flat hazard rates
    tau = -np.log(1 - U) / np.array(hazard_rates)[None, :]
    # nth-smallest default time per path
    nth_times = np.partition(tau, nth - 1, axis=1)[:, nth - 1]
    return float(np.mean(nth_times <= T))


def implied_compound_correlation(
    tranche_spread, attach, detach, index_hazard,
    n=125, r=0.02, recovery=0.4, T=5.0, M=20
):
    """Find compound correlation for a single tranche by root-finding.

    Uses simplified semi-analytic Gaussian quadrature approach (Hull §25.10).
    Returns rho in [0, 1) or raises if no solution found.
    """
    def model_spread(rho):
        return _tranche_spread_quadrature(
            rho, attach, detach, index_hazard, n, r, recovery, T, M
        )
    # Check boundary values
    lo, hi = model_spread(1e-4), model_spread(0.9999)
    if (lo - tranche_spread) * (hi - tranche_spread) > 0:
        raise ValueError("No solution in [0,1); check inputs.")
    return brentq(lambda rho: model_spread(rho) - tranche_spread, 1e-4, 0.9999)


def _tranche_spread_quadrature(rho, attach, detach, lam, n, r, R, T, M):
    """Semi-analytic tranche spread via Gauss-Hermite quadrature (simplified)."""
    from numpy.polynomial.hermite import hermgauss
    nodes, weights = hermgauss(M)
    F_vals = nodes * math.sqrt(2)          # convert to N(0,1) scale
    w_vals = weights / math.sqrt(math.pi)
    pay_times = np.arange(0.25, T + 0.25, 0.25)
    A = B = C = 0.0
    for F, w in zip(F_vals, w_vals):
        Q_cond = norm.cdf(
            (norm.ppf(1 - math.exp(-lam * T)) - math.sqrt(rho) * F)
            / math.sqrt(1 - rho)
        )
        # Binomial expected loss on tranche (simplified: single time slice)
        from scipy.stats import binom
        exp_loss = sum(
            binom.pmf(k, n, Q_cond) * max(0, min(k * (1 - R) / n, detach) - attach)
            / (detach - attach)
            for k in range(n + 1)
        )
        df = math.exp(-r * T)
        C += w * exp_loss * df
        # Risky annuity: approximate as T * survival of tranche
        survival = 1 - exp_loss
        A += w * survival * sum(0.25 * math.exp(-r * t) for t in pay_times)
    return C / A if A > 0 else 0.0


# ── Quick examples ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("CDS par spread (flat lambda=2%):", cds_par_spread([0.02], [5.0]))
    # Expected ≈ 0.0123 (123 bps, matches Hull Table 25.2-25.4 example)

    spreads = [0.0050, 0.0080, 0.0110, 0.0140, 0.0170]
    tenors = [1, 2, 3, 4, 5]
    haz = bootstrap_hazards(spreads, tenors)
    print("Bootstrapped hazards:", [f"{h:.4f}" for h in haz])

    p = gaussian_copula_nth_default_mc([0.02] * 10, rho=0.3, T=5, nth=1)
    print(f"P(1st default ≤ 5y, rho=0.3): {p:.4f}")
```

## 6. 注意点 / 典型的なミス

- **Gaussianコピュラは結合極端事象を過小評価する**: 共倒れ（joint default）確率が現実より低く、2007–09年の金融危機でCDOエクイティトランシェが想定外の損失を被った主因。Student-t コピュラや二重t コピュラ（Hull-White）はテイルをより厚く表現できる。
- **ベース相関の非存在域**: 非常にシニアなトランシェで市場スプレッドが低すぎると、ベース相関の解が存在しない場合（ノー・アービトラージ条件の破れ）が生じる。コンパウンド相関も同様。
- **標準クーポンとアップフロント支払い**: 2009年Big Bangプロトコル以降、CDSクーポンは100bpまたは500bpに標準化されており、市場スプレッドとの差額はアップフロント支払いで精算される（Hull §25.4）。単純に $s = $ 市場スプレッドで計算するのは誤り。
- **リスク中立vs現実デフォルト確率**: CDSのバリュエーションにはリスク中立デフォルト確率を使用すること。現実世界の格付けデータから得られる確率では系統的に過小評価となる（Hull §25.2 Estimating Default Probabilities）。
- **ネイキッドCDS**: 原債券を保有せずに保護を購入するポジション。ソブリン危機時に規制議論を招いた（欧州ではEU規制により一部禁止）。
- **回収率の二重使用**: 回収率 $R$ はリスク中立デフォルト確率の推定（CDS スプレッド / ボンド価格から）とCDSペイオフ計算の両方に使う。同一の $R$ を使う限りCDS評価は $R$ に非感応だが、バイナリCDS評価には重要（Hull §25.2 Recovery Rate 節）。
- **テナー構造のブートストラップ順序**: 短いテナーから長いテナーへ順次解くことが必須。逆順や一括求解は誤り。

## 7. 関連トピック

- See: [topics/credit.md](../topics/credit.md), Ch.24 (credit risk, Merton model, default probability estimation, copula intro §24.8), Ch.8 (securitization, ABS/CDO structures), Ch.9 (XVA, CVA), Ch.7 (swaps basics for TRS context).
- 数値手法：Gaussian quadrature (Ch.21 §21.9), モンテカルロ (Ch.21 §21.6).
- 市場実務：CDS Big Bang (2009 ISDA protocol), CDX/iTraxx index families, single-tranche trading.
