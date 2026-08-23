# Ch.32 No-Arbitrage Models of the Short Rate

> **Source**: Hull 11e, Chapter 32 (pp. 732-754). Paraphrased summary for personal use.

## 1. 要点

- 均衡モデル（Ch.31）は今日のイールドカーブを自動的に再現しないが、ノーアービトラージモデルはドリフトを時間依存関数 $\theta(t)$ にすることで初期ターム構造を入力として完全フィットさせる。
- Ho-Lee モデル（1986）は最初のノーアービトラージ・ショートレートモデルであり、分析的扱いやすさを持つが、全満期の金利が等しく変動する（平坦なボラティリティ構造）。
- Hull-White 1因子モデルは Ho-Lee に mean reversion（速度 $a$）を加えた拡張 Vasicek で、分析的なボンド価格・オプション価格式と満期逓減ボラティリティ構造を持つ。
- Black-Karasinski モデルは $\ln r$ が正規分布に従う対数正規型で負金利を排除するが、closed-form がなくツリー評価のみ。
- Hull-White の2段階トリノミアルツリー構築法（Stage 1: $x^*$-ツリー、Stage 2: $\alpha_i$ シフトによるイールドカーブフィット）は、初期ゼロカーブとの整合性を保証し、アメリカン・オプション等の非解析的デリバティブ評価に使われる。
- ボラティリティパラメータ $a$, $\sigma$ はキャップ・スワプション等の市場価格へのキャリブレーション（Levenberg-Marquardt 等）で決定する。

## 2. キー用語

- **ノーアービトラージモデル**: 今日のターム構造を入力（not 出力）として厳密に再現するように設計されたモデル；ドリフトが $\theta(t)$（時間の関数）
- **Ho-Lee モデル**: 最初の連続時間ノーアービトラージモデル；$dr = \theta(t) dt + \sigma\, dz$；mean reversion なし
- **Hull-White モデル (extended Vasicek)**: $dr = [\theta(t) - ar] dt + \sigma\, dz$；mean reversion 速度 $a$、分析解あり
- **Black-Derman-Toy (BDT) モデル**: $d\ln r = [\theta(t) - a(t)\ln r] dt + \sigma(t)\, dz$；対数正規、$a(t)$ と $\sigma(t)$ が連動する制約あり
- **Black-Karasinski (BK) モデル**: $d\ln r = [\theta(t) - a\ln r] dt + \sigma\, dz$；$a$ と $\sigma$ 独立、対数正規、closed-form なし
- **$\theta(t)$**: ドリフトを今日のフォワードレートカーブに整合させる時間依存関数
- **トリノミアルツリー**: 各ノードで「上・中・下」3本の枝を持つ離散時間ツリー；HW の mean reversion 表現に binomial より適合
- **Arrow-Debreu 価格 $Q_{i,j}$**: ノード $(i, j)$ に到達する確率割引後の価値（状態価格）；ツリー Stage 2 の $\alpha_i$ 計算に使用
- **キャリブレーション**: 市場で観察されるオプション価格から $a$・$\sigma$ を最小二乗フィットで逆算する手続き
- **outside model hedging**: モデルが許容しない動き（ボラティリティ変化など）に対してもデルタ/ベガをヘッジする実務的手法
- **Jamshidian 分解**: クーポン債オプションを複数のゼロ債オプションの和に分解する手法（1因子モデルのみ適用可）

## 3. 主要公式

### Ho-Lee: ショートレート SDE

$$
dr = \theta(t)\, dt + \sigma\, dz
$$

<!-- Hull eq. (32.1) -->

- $\theta(t)$: 今日の瞬間フォワードレートの傾き＋分散補正：

$$
\theta(t) = F_t(0,t) + \sigma^2 t
$$

<!-- Hull eq. (32.2) -->

ここで $F(0,t)$ は今日から満期 $t$ への瞬間フォワードレート、$F_t = \partial F / \partial t$。

### Ho-Lee: ゼロクーポン債価格

$$
P(t, T) = A(t, T)\, e^{-r(t)(T-t)}
$$

<!-- Hull eq. (32.3) -->

$$
\ln A(t, T) = \ln \frac{P(0,T)}{P(0,t)} + (T-t)F(0,t) - \tfrac{1}{2}\sigma^2 t(T-t)^2
$$

### Hull-White 1因子: ショートレート SDE

$$
dr = [\theta(t) - a r]\, dt + \sigma\, dz
$$

<!-- Hull eq. (32.4) -->

- $a$: mean reversion 速度（定数）
- $\sigma$: ショートレートの瞬間標準偏差（定数）

$$
\theta(t) = F_t(0,t) + a F(0,t) + \frac{\sigma^2}{2a}(1 - e^{-2at})
$$

<!-- Hull eq. (32.5) -->

### Hull-White: ゼロクーポン債価格

$$
P(t, T) = A(t, T)\, e^{-B(t,T)\, r(t)}
$$

<!-- Hull eq. (32.6) -->

$$
B(t, T) = \frac{1 - e^{-a(T-t)}}{a}
$$

<!-- Hull eq. (32.7) -->

$$
\ln A(t, T) = \ln \frac{P(0,T)}{P(0,t)} + B(t,T) F(0,t) - \frac{\sigma^2}{4a^3}(e^{-aT} - e^{-at})^2(e^{2at} - 1)
$$

<!-- Hull eq. (32.8) -->

### Black-Karasinski: ショートレート SDE

$$
d\ln r = [\theta(t) - a\ln r]\, dt + \sigma\, dz
$$

<!-- Hull eq. (32.9) -->

$\theta(t)$ は初期ターム構造にフィットするよう決定される。closed-form なし。

### ゼロ債に対するヨーロピアン・コール（Hull-White / Ho-Lee / Vasicek 共通形）

$$
\text{call} = L\, P(0,s)\, N(h) - K\, P(0,T)\, N(h - \sigma_P)
$$

<!-- Hull eq. (32.10) -->

$$
h = \frac{1}{\sigma_P} \ln \frac{L\, P(0,s)}{K\, P(0,T)} + \frac{\sigma_P}{2}
$$

$$
\text{put} = K\, P(0,T)\, N(-h + \sigma_P) - L\, P(0,s)\, N(-h)
$$

ここで $L$: 元本、$K$: 行使価格、$T$: オプション満期、$s$: 債券満期 ($s > T$)。

Hull-White / Vasicek の場合：

$$
\sigma_P = \frac{\sigma}{a}\bigl[1 - e^{-a(s-T)}\bigr] \sqrt{\frac{1 - e^{-2aT}}{2a}}
$$

Ho-Lee の場合：$\sigma_P = \sigma(s - T)\sqrt{T}$

### フォワードレートのボラティリティ構造（Hull-White）

$$
\sigma_f(t, T) = \sigma\, e^{-a(T-t)}
$$

mean reversion が大きいほど長端フォワードボラティリティは低下（満期逓減構造）。

### トリノミアルツリー Stage 1: 分枝確率（中央枝 Figure 32.5a）

$$
p_u = \tfrac{1}{6} + \tfrac{1}{2}(a^2 j^2 \Delta t^2 - aj\Delta t), \quad
p_m = \tfrac{2}{3} - a^2 j^2 \Delta t^2, \quad
p_d = \tfrac{1}{6} + \tfrac{1}{2}(a^2 j^2 \Delta t^2 + aj\Delta t)
$$

格子間隔：$\Delta R = \sigma\sqrt{3\Delta t}$、枝切り替え閾値：$j_{\max}$ = $0.184/(a\Delta t)$ を超える最小整数。

### トリノミアルツリー Stage 2: $\alpha_m$ の決定式

$$
P_{m+1} = \sum_{j=-n_m}^{n_m} Q_{m,j} \exp[-(\alpha_m + j\Delta R)\Delta t]
$$

<!-- Hull eq. (32.12) -->

$$
\alpha_m = \frac{\ln \sum_{j=-n_m}^{n_m} Q_{m,j} e^{-j\Delta R \Delta t} - \ln P_{m+1}}{\Delta t}
$$

### 樹上でのボンド価格（$\Delta t$ 期レート $R$ を用いた修正版）

$$
P(t, T) = \hat{A}(t, T)\, e^{-\hat{B}(t,T)\, R}
$$

<!-- Hull eq. (32.15) -->

$$
\hat{B}(t,T) = \frac{B(t,T)}{B(t, t+\Delta t)}\Delta t, \quad
\ln \hat{A}(t,T) = \ln \frac{P(0,T)}{P(0,t)} - \frac{B(t,T)}{B(t,t+\Delta t)} \ln \frac{P(0,t+\Delta t)}{P(0,t)} - \frac{\sigma^2}{4a}(1-e^{-2at})B(t,T)[B(t,T)-B(t,t+\Delta t)]
$$

<!-- Hull eqs. (32.15)-(32.17) -->

## 4. アルゴリズム / 手順

1. **Hull-White キャリブレーション**
   1. キャリブレーション対象（キャップ、スワプション等）を選定する。
   2. 評価対象デリバティブと満期・行使条件が近いものを優先する。
   3. `goodness-of-fit` 指標 $\sum_i (U_i - V_i)^2$（$U_i$: 市場価格、$V_i$: モデル価格）を最小化。
   4. $a$ を固定し $\sigma$ を逆算する方法（implied $\sigma$）も実用的；Levenberg-Marquardt を使用。
   5. $\sigma$ を時間の階段関数にする場合はペナルティ項（平滑性ペナルティ）を追加する。

2. **HW トリノミアルツリー構築（Hull §32.5）**
   - **Stage 1 — $x^*$ ツリー**:
     1. $\Delta t$（時間刻み）と $\Delta R = \sigma\sqrt{3\Delta t}$ を設定。
     2. $j_{\max} = \lceil 0.184 / (a\Delta t) \rceil$ を計算、$j_{\min} = -j_{\max}$。
     3. 各ノード $(i,j)$ の分枝確率を中央 / 上端 / 下端の3タイプから選択（$j = j_{\max}$ で Figure 32.5c、$j = j_{\min}$ で Figure 32.5b に切替）。
   - **Stage 2 — $R$ ツリーへのシフト**:
     1. $Q_{0,0} = 1$、$\alpha_0 = $ 初期 $\Delta t$ 期ゼロレートとして出発。
     2. 前向き帰納で $Q_{i,j}$ を計算（式 32.12 の $Q_{m+1,j}$）。
     3. 各層 $m$ で $\alpha_m$ を解き（式 32.12）、$R_{i,j} = \alpha_i + j\Delta R$ を得る。
     4. 各 $\alpha_i$ は市場ゼロ債価格 $P_{m+1}$ を再現するように設定。

3. **Jamshidian スワプション評価**
   1. スワップのストライクレートと等しいクーポンを持つ債券価格がオプション行使時に行使価格と等しくなる臨界ショートレート $r^*$ を数値的に求める。
   2. 各クーポン期日のゼロ債を単独で $r^*$ に対応する行使価格 $K_i$（$= $ その時点での当該ゼロ債価格）でオプション評価（式 32.10 を使用）。
   3. クーポン債オプション価格 = 各ゼロ債オプション価格の和。
   4. スワプション = クーポン債コールとして同様に評価可能（1因子モデル限定）。

4. **Two-Factor Hull-White（概要）**
   - $r$ のドリフトに $\theta(t)$ を加えた2因子均衡モデルを拡張；フォワードレートボラティリティが「ハンプ型」（Figure 32.3(c)）になり、実証データや市場インプライドキャップボラティリティとより整合的。
   - トリノミアルツリー（Technical Note 14）または解析式が存在するが HW1F より実装が複雑。

## 5. Python reference

```python
import math
import numpy as np
from scipy.stats import norm


# ── Hull-White: B(t,T) ──────────────────────────────────────────────────────

def hw_B(a: float, t: float, T: float) -> float:
    """B(t,T) = (1 - exp(-a(T-t))) / a  [Hull eq. 32.7]"""
    if a == 0.0:
        return T - t
    return (1.0 - math.exp(-a * (T - t))) / a


# ── Hull-White: zero-coupon bond price ─────────────────────────────────────

def hw_bond_price(
    t: float, T: float, r_t: float,
    a: float, sigma: float,
    P_market_t: float, P_market_T: float, f_market_t: float,
) -> float:
    """Hull-White P(t,T), given today's discount factors P(0,t), P(0,T)
    and instantaneous fwd rate f(0,t).  [Hull eqs. 32.6-32.8]

    Parameters
    ----------
    t, T         : current time, bond maturity
    r_t          : short rate at time t
    a, sigma     : HW mean-reversion speed and vol
    P_market_t   : P(0,t)  — today's t-maturity zero-coupon price
    P_market_T   : P(0,T)  — today's T-maturity zero-coupon price
    f_market_t   : F(0,t)  — today's instantaneous forward rate at t
    """
    B = hw_B(a, t, T)
    # ln A(t,T) from eq. 32.8
    ln_A = (
        math.log(P_market_T / P_market_t)
        + B * f_market_t
        - (sigma**2) * (1.0 - math.exp(-2.0 * a * t)) * B**2 / (4.0 * a)
    )
    return math.exp(ln_A) * math.exp(-B * r_t)


# ── Hull-White: European option on zero-coupon bond (Jamshidian) ──────────

def hw_zero_bond_option(
    call_put: str, K: float, L: float,
    T: float, s: float,
    a: float, sigma: float,
    P0_T: float, P0_s: float,
) -> float:
    """European option on zero-coupon bond (HW / Vasicek).  [Hull eq. 32.10]

    Parameters
    ----------
    call_put : 'call' or 'put'
    K        : strike price per unit of face value
    L        : face value (notional)
    T        : option expiry
    s        : bond maturity (s > T)
    a, sigma : HW parameters
    P0_T     : P(0,T) — today's T-maturity zero price
    P0_s     : P(0,s) — today's s-maturity zero price
    """
    sigma_p = (
        (sigma / a)
        * (1.0 - math.exp(-a * (s - T)))
        * math.sqrt((1.0 - math.exp(-2.0 * a * T)) / (2.0 * a))
    )
    h = (math.log(L * P0_s / (K * P0_T)) + 0.5 * sigma_p**2) / sigma_p
    if call_put == 'call':
        return L * P0_s * norm.cdf(h) - K * P0_T * norm.cdf(h - sigma_p)
    else:  # put
        return K * P0_T * norm.cdf(-h + sigma_p) - L * P0_s * norm.cdf(-h)


# ── Hull-White trinomial tree Stage 1 ──────────────────────────────────────

def hw_trinomial_stage1(a: float, sigma: float, T: float, n_steps: int) -> dict:
    """Build Stage-1 symmetric x*-tree for Hull-White model.  [Hull §32.5]

    Returns dict with dt, dx (=dR), j_max, and a probability function.
    """
    dt = T / n_steps
    dx = sigma * math.sqrt(3.0 * dt)
    j_max = int(math.ceil(0.184 / (a * dt)))  # Hull's truncation rule

    def probs(j: int) -> tuple[float, float, float]:
        """Branching probabilities for node at level j (central branching)."""
        adt = a * dt
        eta = adt * j
        p_u = 1.0 / 6.0 + 0.5 * (eta**2 - eta)
        p_m = 2.0 / 3.0 - eta**2
        p_d = 1.0 / 6.0 + 0.5 * (eta**2 + eta)
        return p_u, p_m, p_d

    return dict(dt=dt, dx=dx, j_max=j_max, probs=probs)


# ── Convenience: forward rate from flat yield curve ────────────────────────

def flat_fwd(r: float) -> float:
    """Instantaneous fwd rate for a flat zero curve at rate r."""
    return r


# ── Example ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Parameters
    a, sigma = 0.1, 0.01
    r0 = 0.05  # flat term structure at 5%

    # Zero-coupon bond prices on flat 5% curve
    P0_T = math.exp(-r0 * 1.0)   # P(0,1)
    P0_s = math.exp(-r0 * 5.0)   # P(0,5)

    # European call on zero-coupon bond: expiry T=1, bond maturity s=5
    call = hw_zero_bond_option('call', K=0.70, L=1.0, T=1.0, s=5.0,
                               a=a, sigma=sigma, P0_T=P0_T, P0_s=P0_s)
    put  = hw_zero_bond_option('put',  K=0.70, L=1.0, T=1.0, s=5.0,
                               a=a, sigma=sigma, P0_T=P0_T, P0_s=P0_s)
    print(f"HW bond call option : {call:.6f}")
    print(f"HW bond put  option : {put:.6f}")

    # Trinomial tree Stage 1 geometry
    tree = hw_trinomial_stage1(a=a, sigma=sigma, T=3.0, n_steps=3)
    print(f"dx={tree['dx']:.5f}, j_max={tree['j_max']}")
    print(f"Probs at j=0 : {tree['probs'](0)}")
    print(f"Probs at j=1 : {tree['probs'](1)}")
```

## 6. 注意点 / 典型的なミス

- **HW は負金利を許容する**: Gaussian モデルなので $r < 0$ になりうる。近年の負金利環境では許容されるが、低ストライクのキャップ等では smile を考慮しないと誤差が大きい。HW を「使えない」と見なして BK を好む実務家もいたが、負金利が現実化して評価が変わった。
- **BK は closed-form なし**: ゼロ債価格やオプション価格の解析式が存在しないため、必ずツリーまたは MC で評価する必要がある。
- **Jamshidian 分解の適用範囲**: ボンド価格が $r$ の単調関数であることに依存するため、1因子モデルにのみ適用可。2因子モデルでは使えない（32.2 Practice Question 32.2）。
- **トリノミアル枝切り替え**: $|j| = j_{\max}$ でブランチパターンを Figure 32.5b/c に切り替えないと確率が負になる。切り替えを忘れると誤った価格が出る。
- **$A(t,T)$ と $\hat{A}(t,T)$ の使い分け**: ツリー上のノードは離散時間レート $R$（$\Delta t$ 期）を持つため、連続時間式 (32.6) ではなく修正式 (32.15) を用いる。
- **キャリブレーション instrument の選択**: 評価対象と満期・行使条件が近い instrument を選ばないと、フィットが局所的になりモデル外挿で大きな誤差が出る。
- **平滑性ペナルティ**: $\sigma(t)$ を時間関数にするときは、ペナルティ項なしでは解が不安定になることがある。

## 7. 関連トピック

- See: [topics/ir_derivatives.md](../topics/ir_derivatives.md)
- **Ch.31** (equilibrium short-rate models: Vasicek / CIR — HW の出発点)
- **Ch.33** (HJM / LIBOR Market Model — フォワードレート直接モデリングへの発展)
- **Ch.29** (Black's model — caps/floors/swaptions の市場標準；HW で代替する動機)
- **Ch.28** (forward measure — HW のリスク中立評価の基礎)
- **Ch.21** (数値手法概論: explicit finite difference ≡ trinomial tree の等価性)
