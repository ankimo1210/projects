# Ch.30 Convexity, Timing, and Quanto Adjustments

> **Source**: Hull 11e, Chapter 30 (pp. 707-718). Paraphrased summary for personal use.

## 1. 要点

- デリバティブの標準的な2ステップ評価法（フォワード値で期待値を計算→リスクフリーレートで割引）は、非標準の金利デリバティブでは修正が必要になることがある。
- **コンベクシティ調整**：債券価格と利回りの非線形関係（図30.1）により、フォワード利回りをそのまま期待利回りとして使うと誤差が生じる。期待利回りはフォワード利回りより高い。
- **タイミング調整**：変数が観測される時点 $T$ と支払いが行われる時点 $T^*>T$ が異なる場合、ニュメレールの変更（$P(t,T)$ → $P(t,T^*)$）により期待値に補正が必要になる。
- **クオント調整**：外国通貨で計測された変数が国内通貨で決済される場合、為替レートとの相関に起因するドリフト補正が必要になる。
- 3つの調整はいずれも **ニュメレール変更に伴うドリフト補正** であり、本質的には同一の枠組み（Ch.28の結果）から導かれる。

## 2. キー用語

- **Convexity adjustment（コンベクシティ調整）**：債券価格-利回りの非線形性により生じる、フォワード利回りと期待利回りの差。$-\tfrac{1}{2} y_F^2 \sigma_y^2 T \, G''(y_F)/G'(y_F)$。
- **Forward bond yield（フォワード債券利回り）** $y_F$：フォワード債券価格 $B_F = G(y_F)$ から逆算される利回り。
- **Timing adjustment（タイミング調整）**：観測時点 $T$ と支払時点 $T^*$ がずれていることで必要になるドリフト補正。
- **Quanto（クオント）**：外国通貨建ての変数が国内通貨で決済されるクロスカレンシー・デリバティブ。
- **Quanto adjustment（クオント調整）**：国内ニュメレールへの変更により外国資産ドリフトに加わる $\rho \sigma_V \sigma_S$ 項。
- **Siegel's paradox（ジーゲルのパラドックス）**：$S$ と $1/S$ の対称性に見える矛盾。クオント調整により解消される（Business Snapshot 30.1）。
- **Numeraire ratio（ニュメレール比率）**：ニュメレール変更のキー量。タイミング調整では $W = P(t,T^*)/P(t,T)$、クオント調整では $W(t) = P_X(t,T)/P_Y(t,T) \cdot S(t)$。

## 3. 主要公式

### コンベクシティ調整（一般形：フォワード債券利回り）

$$
E_T(y_T) = y_F - \tfrac{1}{2} y_F^2 \sigma_y^2 T \frac{G''(y_F)}{G'(y_F)}
$$

- $y_F$：フォワード債券利回り（$B_F = G(y_F)$）
- $\sigma_y$：フォワード利回りのボラティリティ（年率）
- $T$：満期
- $G'$, $G''$：$G$ の一次・二次偏微分（$G'(y_F)<0$、$G''(y_F)>0$ なので調整は正）

<!-- Hull eq. (30.1) -->

### コンベクシティ調整（Eurodollar/SOFR先物レートからフォワードレートへ）

$$
\text{forward rate} = \text{futures rate} - \tfrac{1}{2} \sigma^2 t_1 t_2
$$

- $\sigma$：短期金利変化の標準偏差（年率）
- $t_1$：先物満期までの時間
- $t_2$：アクルーアル期間終了までの時間
- Ch.6で導入された式。$t_1 t_2$ の積が長期限月では調整を大きくする。

<!-- Hull Ch.6 Eurodollar convexity, referenced in Ch.30 context -->

### タイミング調整

観測時点 $T$、支払時点 $T^*$ のとき、$P(t,T)$ ニュメレールから $P(t,T^*)$ ニュメレールへの変更によりドリフトが変わる：

$$
\alpha_V = -\frac{\rho_{VR}\, \sigma_V \sigma_R R_F (T^* - T)}{1 + R_F/m}
$$

これを積分すると期待値の関係式：

$$
E_{T^*}(V_T) = E_T(V_T) \exp\!\left[-\frac{\rho_{VR}\, \sigma_V \sigma_R R_F (T^* - T)}{1 + R_F/m} \cdot T\right]
$$

- $R_F$：$T$ から $T^*$ までのフォワード金利（複利頻度 $m$）
- $\sigma_R$：$R_F$ のボラティリティ
- $\rho_{VR}$：$V$ と $R_F$ の瞬間相関（$= -\rho_{VW}$）

<!-- Hull eq. (30.2), (30.3) -->

### クオント調整（フォワード測度版）

通貨 $Y$ ニュメレール $P_Y(t,T)$ から通貨 $X$ ニュメレール $P_X(t,T)$ に変更すると $V$ のドリフトが増加する：

$$
\alpha_V = \rho_{VW}\, \sigma_V \sigma_W
$$

定常ボラティリティの仮定のもとで：

$$
E_X(V_T) = E_Y(V_T)\, e^{\rho_{VW}\, \sigma_V \sigma_W T}
$$

または近似（一次）：

$$
E_X(V_T) \approx E_Y(V_T)\,(1 + \rho_{VW}\, \sigma_V \sigma_W T)
$$

- $\sigma_W$：ニュメレール比率 $W = P_X(t,T)/P_Y(t,T) \cdot S(t)$ のボラティリティ（≈ 為替スポットレートのボラティリティ $\sigma_S$）
- $\rho_{VW}$：$V$ と $W$（≈ $S$）の相関

<!-- Hull eq. (30.4), (30.5), (30.6) -->

### クオント調整（伝統的リスク中立測度版）

通貨 $Y$ リスク中立世界から通貨 $X$ リスク中立世界への移行では、$V$ のドリフトが以下だけ増加する：

$$
\Delta\mu_V = \rho\, \sigma_V \sigma_S
$$

すなわち $\mu^d = \mu^f - \rho\, \sigma_V \sigma_S$（外国→国内）として、外国資産の国内測度ドリフトは：

$$
\mu^d = \mu^f - \rho\, \sigma_S \sigma_V
$$

<!-- Hull eq. (30.7) -->

**3調整の統一視点**：すべて $\Delta\mu \propto \rho \cdot \sigma_1 \cdot \sigma_2$ 型の一次ドリフト補正であり、ニュメレール変更の式（Ch.28 eq.28.35）から直接導かれる。

## 4. アルゴリズム / 手順

### 1. 先物レートからフォワードレートへのコンベクシティ調整（ED/SOFR先物）

1. 先物レート（ED/SOFR先物クォートから読み取り）、$\sigma$（短期金利ボラティリティ）、$t_1$（満期）、$t_2$（アクルーアル期末）を用意する。
2. $\text{forward} = \text{futures} - \tfrac{1}{2}\sigma^2 t_1 t_2$ を適用する。
3. 長期限月（5年超）では調整が数bpになるため必須。

### 2. 観測時点から支払時点へのタイミング調整

1. $E_T(V_T)$ を通常の2ステップ法（Ch.28）で計算する。
2. $R_F$（$T$〜$T^*$ 間のフォワード金利）、$\sigma_R$、$\sigma_V$、$\rho_{VR}$ を特定する。
3. 補正係数 $\exp\!\bigl[-\rho_{VR}\sigma_V\sigma_R R_F(T^*-T)/(1+R_F/m)\cdot T\bigr]$ を掛けて $E_{T^*}(V_T)$ を得る。
4. $P(0, T^*)$ で割引く。

### 3. 外国資産の国内通貨ペイオフへのクオント調整

1. 通貨 $Y$ の世界で $E_Y(V_T)$ を計算する（通常のフォワード価格）。
2. FX ボラティリティ $\sigma_S$、資産ボラティリティ $\sigma_V$、相関 $\rho$ を特定する。
3. $E_X(V_T) = E_Y(V_T) \exp(\rho\,\sigma_V\sigma_S T)$ を適用する。
4. 国内ゼロクーポン債 $P_X(0,T)$ で割引く。

### 4. 3つの調整を組み合わせる（例：CMS レートの遅延外国通貨払い）

1. **コンベクシティ調整**：CMS レートの利回り凸性補正（eq.30.1 型）を適用する。
2. **タイミング調整**：観測日≠支払日なら eq.(30.3) を適用する。
3. **クオント調整**：外国通貨払いなら eq.(30.5) または eq.(30.7) を適用する。
4. 3補正はすべて乗法的に組み合わせられる（ドリフトの積み上げ）。

## 5. Python reference

```python
import math


def convexity_adjustment_eurofutures(futures_rate: float, sigma: float,
                                      t1: float, t2: float) -> float:
    """Forward rate from Eurodollar/SOFR futures rate.

    forward = futures - 0.5 * sigma^2 * t1 * t2

    Args:
        futures_rate: quoted futures rate (e.g. 0.04 for 4%)
        sigma:  annualised std dev of short-rate changes
        t1:     time to futures expiry (years)
        t2:     time to end of accrual period (years)
    """
    return futures_rate - 0.5 * sigma**2 * t1 * t2


def convexity_adjustment_bond_yield(y_F: float, sigma_y: float, T: float,
                                     G_pp: float, G_p: float) -> float:
    """Expected bond yield under T-forward measure (Hull eq. 30.1).

    E_T(y_T) = y_F - 0.5 * y_F^2 * sigma_y^2 * T * G''(y_F) / G'(y_F)

    G_pp / G_p: second / first derivative of bond pricing function G
                evaluated at y_F.  G'<0, G''>0, so adjustment is positive.
    """
    return y_F - 0.5 * y_F**2 * sigma_y**2 * T * G_pp / G_p


def timing_adjustment(E_T_V: float, rho_VR: float, sigma_V: float,
                       sigma_R: float, R_F: float, T: float,
                       T_star: float, m: float = 1.0) -> float:
    """Adjust E^T[V_T] -> E^{T*}[V_T] for delayed payment (Hull eq. 30.3).

    Args:
        E_T_V:   E_T(V_T), expected value under P(t,T) numeraire
        rho_VR:  instantaneous correlation between V and R_F
        sigma_V: volatility of V
        sigma_R: volatility of R_F
        R_F:     forward rate for period [T, T*] with compounding freq m
        T:       observation time
        T_star:  payment time (T* > T)
        m:       compounding frequency (1 = annual, 2 = semi-annual, etc.)
    """
    tau = T_star - T
    exponent = -rho_VR * sigma_V * sigma_R * R_F * tau / (1 + R_F / m) * T
    return E_T_V * math.exp(exponent)


def quanto_adjustment_forward(E_Y_V: float, rho: float, sigma_V: float,
                               sigma_S: float, T: float) -> float:
    """E^X[V_T] from E^Y[V_T] for a quanto payoff (Hull eq. 30.5).

    Args:
        E_Y_V:   E_Y(V_T), expected value in foreign (Y) numeraire world
        rho:     instantaneous correlation between V and FX spot S (Y per X)
        sigma_V: volatility of V
        sigma_S: volatility of FX forward (≈ spot)
        T:       maturity
    """
    return E_Y_V * math.exp(rho * sigma_V * sigma_S * T)


def quanto_drift_adjust(mu_foreign: float, rho: float,
                         sigma_V: float, sigma_S: float) -> float:
    """Drift of V in domestic (X) risk-neutral world (Hull eq. 30.7).

    mu^domestic = mu^foreign - rho * sigma_V * sigma_S
    """
    return mu_foreign - rho * sigma_V * sigma_S


# ── Examples ──────────────────────────────────────────────────────────────────

# Example 1: ED futures convexity (5-year contract)
fwd = convexity_adjustment_eurofutures(
    futures_rate=0.04, sigma=0.012, t1=5.0, t2=5.25)
print(f"Forward rate (5y ED): {fwd:.6f}")   # ≈ 0.038106

# Example 2: CMS convexity (Example 30.1 in Hull)
#  3-year swap rate, y_F=6%, sigma_y=22%, G'=-2.6730, G''=9.8910
E_y = convexity_adjustment_bond_yield(
    y_F=0.06, sigma_y=0.22, T=3.0, G_pp=9.8910, G_p=-2.6730)
print(f"Expected swap rate (CMS): {E_y:.5f}")   # ≈ 0.06097

# Example 3: Quanto — Nikkei paid in USD (Example 30.3 in Hull)
E_Y_nkx = 15_150.75   # forward Nikkei in yen world
E_X_nkx = quanto_adjustment_forward(
    E_Y_V=E_Y_nkx, rho=0.3, sigma_V=0.20, sigma_S=0.12, T=1.0)
print(f"Quanto E[Nikkei] in USD world: {E_X_nkx:.2f}")   # ≈ 15260.23
```

## 6. 注意点 / 典型的なミス

- **全調整は2次オーダー**（ボラティリティの積に比例）。短期・低ボラティリティのポジションでは無視できるが、5年超の先物や長期CMS商品では数十bpになりうる。
- **クオント相関の符号**：$\rho > 0$（資産と為替が正相関）なら $E^d[V] > E^f[V]$。日経225と円/ドルのように一般に負相関の場合は逆方向に調整される。
- **ED先物コンベクシティは満期の2乗で増大**：$t_1 t_2 \approx t_1^2$ なので5年限月では1年限月の25倍。長期限月を無調整で使うのは重大な誤り。
- **コンベクシティ調整とタイミング調整の混同**：CMS スワップレート（長期スワップレートを短い支払い期間に適用）には両方の調整が必要。コンベクシティのみ、またはタイミングのみ適用するのは不十分。
- **eq.(30.1) のコンベクシティ調整は「一次近似」**：長期商品（10年超CMS等）では完全なHJM/LMM（Ch.33）を使うべき。eq.(30.1) 型の調整を重ねて使うのは危険。
- **$G'(y_F) < 0$, $G''(y_F) > 0$** の符号を間違えると調整の方向が逆になる。調整は常に正（期待利回り > フォワード利回り）であることを確認する。
- **タイミング調整の $\rho_{VR}$ は $-\rho_{VW}$**：$W = P(t,T^*)/P(t,T)$ は金利と負相関しているため符号に注意。

## 7. 関連トピック

- See: [topics/ir_derivatives.md](../topics/ir_derivatives.md)
- **Ch.6**：Eurodollar先物とコンベクシティ調整の初出。$t_1 t_2$ 公式の元ネタ。
- **Ch.28**：マルチンゲールと測度論（eq.28.35 がすべての調整の根拠）。ニュメレール変更のドリフト補正公式を導出。
- **Ch.29**：ブラックモデルによる金利デリバティブ評価。本章の調整を適用すべき文脈（cap/floor/swaption + CMS）。
- **Ch.33**：HJM・LMMによる完全フォワードレートモデル。本章の近似が不十分な場合の代替手法。
- **Ch.34**：非標準スワップ（diff swap、CMS swap）への本章結果の応用。
