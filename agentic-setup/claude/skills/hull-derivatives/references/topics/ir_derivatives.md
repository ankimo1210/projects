# Topic: Interest Rate Derivatives

## 対応章
- Ch.29 Interest Rate Derivatives: The Standard Market Models — [chapters/ch29_ir_std_models.md](../chapters/ch29_ir_std_models.md)
- Ch.30 Convexity, Timing, and Quanto Adjustments — [chapters/ch30_convexity_timing_quanto.md](../chapters/ch30_convexity_timing_quanto.md)
- Ch.31 Equilibrium Models of the Short Rate — [chapters/ch31_equilibrium_short_rate.md](../chapters/ch31_equilibrium_short_rate.md)
- Ch.32 No-Arbitrage Models of the Short Rate — [chapters/ch32_noarb_short_rate.md](../chapters/ch32_noarb_short_rate.md)
- Ch.33 Modeling Forward Rates — [chapters/ch33_forward_rate_models.md](../chapters/ch33_forward_rate_models.md)

## クイック公式

### Caplet (Black-76)
$$\text{caplet} = \tau P_{\mathrm{pay}}[F N(d_1) - K N(d_2)]$$
$$d_1 = \frac{\ln(F/K)+\tfrac{1}{2}\sigma^2 T}{\sigma\sqrt{T}}, \quad d_2 = d_1 - \sigma\sqrt{T}$$
- $\tau = t_{k+1}-t_k$（テナー）、$P_{\mathrm{pay}} = P(0,t_{k+1})$、$F$: フォワード金利、$T = t_k$
- Cap = sum of caplets；Floor-cap parity: cap $-$ floor $=$ IRS (pay fixed $K$)
- See: ch29 eq.(29.7)

### Swaption (payer, Black-76)
$$V_{\mathrm{payer}} = L \cdot A(0)[s_F N(d_1) - s_K N(d_2)]$$
$$A(0) = \frac{1}{m}\sum_{i=1}^{mn} P(0, T_i)$$
- $s_F$: フォワードスワップレート、$s_K$: ストライク、$A(0)$: スワップアニュイティ
- Receiver swaption: $V_{\mathrm{rec}} = L \cdot A(0)[s_K N(-d_2) - s_F N(-d_1)]$
- See: ch29 eq.(29.10), (29.11)

### Convexity adjustment: futures → forward rate
$$\text{forward rate} = \text{futures rate} - \tfrac{1}{2}\sigma^2 t_1 t_2$$
- $\sigma$: 短期金利変化の標準偏差、$t_1$: 先物満期、$t_2$: アクルーアル期間終了
- $t_1 t_2 \approx t_1^2$：5年限月では1年限月の 25 倍の調整
- See: ch30 (ch6 初出)

### Timing adjustment (observation at $T$, payment at $T^*$)
$$E_{T^*}(V_T) = E_T(V_T)\exp\!\left[-\frac{\rho_{VR}\,\sigma_V\sigma_R R_F(T^*-T)}{1+R_F/m}\cdot T\right]$$
- See: ch30 eq.(30.3)

### Quanto adjustment (foreign → domestic drift)
$$\mu^d = \mu^f - \rho\,\sigma_S\,\sigma_V$$
- $\rho$: 資産 $V$ と為替 $S$ の相関；国内リスク中立測度でのドリフト補正
- See: ch30 eq.(30.7)

### Vasicek short-rate model
$$dr = a(b-r)\,dt + \sigma\,dz$$
$$P(t,T) = A(t,T)\,e^{-B(t,T)r(t)}, \quad B = \frac{1-e^{-a\tau}}{a}$$
$$\ln A = \frac{(B-\tau)(a^2b-\sigma^2/2)}{a^2} - \frac{\sigma^2 B^2}{4a}, \quad \tau = T-t$$
- ガウス過程 → 負金利あり；イールドカーブに自動フィットしない（均衡モデル）
- See: ch31 eq.(31.6)-(31.8)

### CIR short-rate model
$$dr = a(b-r)\,dt + \sigma\sqrt{r}\,dz, \quad \gamma = \sqrt{a^2+2\sigma^2}$$
$$B = \frac{2(e^{\gamma\tau}-1)}{(\gamma+a)(e^{\gamma\tau}-1)+2\gamma}, \quad A = \left[\frac{2\gamma e^{(a+\gamma)\tau/2}}{(\gamma+a)(e^{\gamma\tau}-1)+2\gamma}\right]^{2ab/\sigma^2}$$
- Feller 条件 $2ab \ge \sigma^2$ → $r \ge 0$；See: ch31 §31.2

### Hull-White (extended Vasicek, no-arb)
$$dr = [\theta(t) - ar]\,dt + \sigma\,dz$$
$$\theta(t) = F_t(0,t) + aF(0,t) + \frac{\sigma^2}{2a}(1-e^{-2at})$$
$$P(t,T) = A(t,T)\,e^{-B(t,T)r(t)}, \quad B = \frac{1-e^{-a(T-t)}}{a}$$
- 初期イールドカーブを正確に再現（no-arb）；閉形式ゼロ債オプションあり
- See: ch32 eq.(32.4)-(32.8)

### HW European zero-coupon bond option
$$\text{call} = L\,P(0,s)\,N(h) - K\,P(0,T)\,N(h-\sigma_P)$$
$$\sigma_P = \frac{\sigma}{a}[1-e^{-a(s-T)}]\sqrt{\frac{1-e^{-2aT}}{2a}}, \quad h = \frac{1}{\sigma_P}\ln\frac{L\,P(0,s)}{K\,P(0,T)}+\frac{\sigma_P}{2}$$
- $T$: オプション満期、$s$: 債券満期（$s>T$）；Jamshidian 分解でスワップション評価に拡張
- See: ch32 eq.(32.10)

### HJM drift constraint (no-arbitrage backbone)
$$m(t,T) = \sum_k s_k(t,T)\int_t^T s_k(t,\tau)\,d\tau$$
- ドリフトはボラティリティ関数だけで一意に決まる；See: ch33 eq.(33.6)
- 特殊ケース: $s=\sigma e^{-a(T-t)}$ → Hull-White；$s=\sigma$ → Ho-Lee

### LMM (LIBOR Market Model) under forward measure
$$dF_k(t) = \zeta_k(t)\,F_k(t)\,dz \quad (\mathbb{Q}^{k+1}\text{ 下でドリフトゼロ})$$
**ローリングリスク中立世界でのドリフト補正:**
$$\frac{dF_k}{F_k} = \sum_{i=m(t)}^{k}\frac{\delta_i F_i \zeta_i \zeta_k}{1+\delta_i F_i}\,dt + \zeta_k\,dz$$
- $F_k$: Black 公式と整合的；キャップを一貫して扱える；スワップションは相関依存
- See: ch33 eq.(33.7), (33.10)

## 実装スニペット

```python
import math
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


# ── Black-76: Caplet / Swaption ──────────────────────────────────────────────

def caplet_black(F, K, sigma, tau, P_pay, T):
    """Black-76 caplet. tau: accrual period; P_pay: discount factor to payment;
    T: time to rate observation (= t_k). Hull eq. (29.7).
    """
    d1 = (math.log(F/K) + 0.5*sigma**2*T) / (sigma*math.sqrt(T))
    d2 = d1 - sigma*math.sqrt(T)
    return tau * P_pay * (F*norm.cdf(d1) - K*norm.cdf(d2))


def swaption_black(F_swap, K, sigma, T_exp, annuity, kind='payer'):
    """European swaption via Black's model on forward swap rate.
    annuity = (1/m) * sum of P(0, T_i) over all swap payment dates.
    Hull eq. (29.10).
    """
    d1 = (math.log(F_swap/K) + 0.5*sigma**2*T_exp) / (sigma*math.sqrt(T_exp))
    d2 = d1 - sigma*math.sqrt(T_exp)
    if kind == 'payer':
        return annuity * (F_swap*norm.cdf(d1) - K*norm.cdf(d2))
    return annuity * (K*norm.cdf(-d2) - F_swap*norm.cdf(-d1))


# ── Vasicek zero-coupon bond price ───────────────────────────────────────────

def vasicek_bond_price(r0, a, b, sigma, t, T):
    """Vasicek P(t,T): dr = a(b-r)dt + sigma dz. Hull eq. (31.6)-(31.8)."""
    tau = T - t
    if tau <= 0:
        return 1.0
    B = (1 - math.exp(-a*tau)) / a
    A = math.exp(
        (B - tau) * (a**2*b - sigma**2/2) / a**2
        - sigma**2 * B**2 / (4*a)
    )
    return A * math.exp(-B * r0)


# ── CIR zero-coupon bond price ───────────────────────────────────────────────

def cir_bond_price(r0, a, b, sigma, t, T):
    """CIR P(t,T): dr = a(b-r)dt + sigma*sqrt(r) dz. Hull §31.2."""
    tau = T - t
    if tau <= 0:
        return 1.0
    gamma = math.sqrt(a**2 + 2*sigma**2)
    den = (gamma + a)*(math.exp(gamma*tau) - 1) + 2*gamma
    B = 2*(math.exp(gamma*tau) - 1) / den
    A = (2*gamma*math.exp((a + gamma)*tau/2) / den) ** (2*a*b/sigma**2)
    return A * math.exp(-B * r0)


# ── Hull-White European bond option ─────────────────────────────────────────

def hw_zero_bond_option(call_put, K, L, T, s, a, sigma, P0_T, P0_s):
    """European option on zero-coupon bond (HW / Vasicek). Hull eq. (32.10).

    Parameters
    ----------
    call_put : 'call' or 'put'
    K        : strike per unit face value
    L        : face value (notional)
    T        : option expiry
    s        : bond maturity (s > T)
    a, sigma : HW parameters
    P0_T     : P(0, T)
    P0_s     : P(0, s)
    """
    sigma_p = (
        (sigma/a) * (1 - math.exp(-a*(s-T)))
        * math.sqrt((1 - math.exp(-2*a*T)) / (2*a))
    )
    h = (math.log(L*P0_s / (K*P0_T)) + 0.5*sigma_p**2) / sigma_p
    if call_put == 'call':
        return L*P0_s*norm.cdf(h) - K*P0_T*norm.cdf(h - sigma_p)
    return K*P0_T*norm.cdf(-h + sigma_p) - L*P0_s*norm.cdf(-h)


# ── Cap vol stripping ────────────────────────────────────────────────────────

def cap_flat_to_spot_vols(cap_quotes, fwd_rates, K, taus, P_pays, T_starts):
    """Strip caplet (spot) vols from cumulative cap prices. Hull §29.3."""
    spot_vols = []
    cum = 0.0
    for i, cap_price in enumerate(cap_quotes):
        F, tau, P, T = fwd_rates[i], taus[i], P_pays[i], T_starts[i]
        target = cap_price - cum
        if T <= 0:
            spot_vols.append(0.0)
            continue
        sigma_i = brentq(
            lambda s: caplet_black(F, K, s, tau, P, T) - target, 1e-4, 5.0
        )
        spot_vols.append(sigma_i)
        cum += caplet_black(F, K, sigma_i, tau, P, T)
    return spot_vols


# ── Convexity / timing / quanto ──────────────────────────────────────────────

def convexity_adj_futures(futures_rate, sigma, t1, t2):
    """Forward = futures - 0.5 * sigma^2 * t1 * t2.  Hull ch6/ch30."""
    return futures_rate - 0.5 * sigma**2 * t1 * t2


def timing_adjustment(E_T_V, rho_VR, sigma_V, sigma_R, R_F, T, T_star, m=1.0):
    """E^{T*}[V_T] from E^T[V_T] for delayed payment. Hull eq. (30.3)."""
    tau = T_star - T
    exponent = -rho_VR * sigma_V * sigma_R * R_F * tau / (1 + R_F/m) * T
    return E_T_V * math.exp(exponent)


def quanto_drift_adjust(mu_foreign, rho, sigma_V, sigma_S):
    """Domestic drift = foreign drift - rho * sigma_V * sigma_S. Hull eq. (30.7)."""
    return mu_foreign - rho * sigma_V * sigma_S
```

## デシジョンガイド

**Black-76 vs Hull-White vs LMM**
| モデル | 長所 | 短所 | 適用場面 |
|---|---|---|---|
| Black-76 | 実装容易；市場のボル呼値に直結 | 3 モデル間で内部矛盾；CMS等に不正確 | 標準キャップ・スワップション価格確認 |
| Hull-White (HW) | 初期カーブに no-arb フィット；閉形式ゼロ債オプション；Jamshidian 分解 | Gaussian → 負金利；スマイル非対応 | Bermudan swaption、CMS、コーラブル債 |
| LMM (BGM) | キャップボラティリティと完全整合；相関構造を明示的にモデル化 | MC 必須；スワップションは相関依存；負金利は Shifted LMM | ラチェットキャップ、CMS spread、非標準金利商品 |

**均衡モデル (Vasicek/CIR) vs no-arb モデル (HW/BK)**
- 均衡モデルはパラメータ固定 → 今日のイールドカーブに厳密にフィットしない
- HW は $\theta(t)$ を時間依存にすることで初期カーブを完全再現
- 学術研究・教育: Vasicek/CIR；実務価格付け: HW または LMM を使う

**Vasicek/CIR の負金利**
- Vasicek: ガウス過程 → $r < 0$ が起こりうる；近年の負金利環境では現実的
- CIR: Feller 条件 $2ab > \sigma^2$ を満たせば $r \ge 0$；MC では $\max(r, 0)$ 吸収境界を必ず適用

**LMM の測度選択**
- フォワード測度 $\mathbb{Q}^{k+1}$: $F_k$ のドリフトゼロ → 単一キャップレット評価に使う
- ローリングリスク中立世界: 複数フォワードレートを同時にシミュレーション → eq.(33.10) のドリフト修正が必要
- 測度を間違えると系統的な価格誤差が生じる

**Shifted LMM と負金利**
- 標準 LMM は $F_k$ の対数正規を仮定 → 負金利不可
- Shifted LMM: $F_k + s$ を対数正規とみなす（$s > 0$ のシフト）
- SOFR/ESTR の低金利・負金利環境では必須

**HJM ドリフト制約とモデルの統一**
- HJM は no-arb の backbone：ドリフト = $\sum_k s_k \cdot \int s_k d\tau$
- $s = \sigma$ → Ho-Lee；$s = \sigma e^{-a(T-t)}$ → Hull-White（再結合ツリー可）
- 一般 HJM はノン・マルコフ → MC 必須（ノード数 $2^n$ で爆発）

**凸性・タイミング・クアント調整の適用判断**
- 調整量 $\propto \rho \cdot \sigma_1 \cdot \sigma_2$（二次オーダー）；短期・低ボラなら無視可
- 5年超の先物レートや長期 CMS では数十 bp になりうる → 必ず適用
- ED 先物コンベクシティは $t_1 t_2$ で増大；5年限月では調整が数 bp 超になる
