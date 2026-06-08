"""
build_ir_options_notebook.py
================================
nbformat-dict pattern to generate ir_options.ipynb (Hull 11e Ch.29, 30).

Usage:
    uv run python build_ir_options_notebook.py
"""

import json
import os

# ---------------------------------------------------------------------------
# Cell helpers (same pattern as build_foundations_notebook.py)
# ---------------------------------------------------------------------------


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.split("\n")}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source.split("\n"),
        "outputs": [],
        "execution_count": None,
    }


cells = []

# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# 金利デリバティブ標準市場モデル（Hull 11e Ch.29, 30）

`johnhull/volumes` シリーズ第11冊。実務の金利オプション評価：

- **Black の標準市場モデル（Ch.29）** — 債券オプション、キャップ/フロア、スワプション
- **キャップ-フロア-スワップのパリティ**、ボラティリティ・ストリッピング
- **3つの調整（Ch.30）** — コンベクシティ、タイミング、クォント

> `hullkit`（ir_options / rates / swaps / nbplot）から import。
> 第4冊（カーブ）・第7冊（スワップ）・第10冊（測度）がここで合流します""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.optimize import brentq

from hullkit import ir_options, nbplot, rates, swaps

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.29 standard market models
# ===========================================================================

# Cell 03: why hard md
cells.append(
    md(r"""## 1. なぜ金利は難しいか（Ch.29）

株式・為替は単一変数だが、金利は**イールドカーブ全体**が動き、
割引率とペイオフの**両方**に影響します。実務の標準解は
「商品ごとに **Black モデル（Black-76）** を当てる」こと：

| 商品 | 対数正規と仮定するもの |
|---|---|
| 債券オプション | 将来の債券価格 |
| キャップレット | 将来の短期金利（フォワードレート） |
| スワプション | 将来のスワップレート |

3つは互いに整合しない（同時には正しくない）が、実務では独立に使われます。""")
)

# Cell 04: bond option md
cells.append(
    md(r"""## 2. 債券オプション（§29.1、eq 29.1/29.2）

$$c = P(0,T)[F_B N(d_1) - K N(d_2)], \qquad
d_1 = \frac{\ln(F_B/K) + \sigma_B^2 T/2}{\sigma_B\sqrt{T}}$$

- $F_B = (B_0 - I)/P(0,T)$: フォワード債券価格（キャッシュプライス）
- $\sigma_B$: フォワード債券価格のボラティリティ
- **利回りボラとの変換**: $\sigma_B \approx D\,y_0\,\sigma_y$（$D$=修正デュレーション）""")
)

# Cell 05: bond option demo
cells.append(
    code(r"""# 債券オプション: フォワード債券価格102, ストライク100, σ_B=8%, T=2, P(0,2)=0.90
P0T, F_B, K_bo, sig_B, T_bo = 0.90, 102.0, 100.0, 0.08, 2.0
c_bo = ir_options.bond_option_black(P0T, F_B, K_bo, sig_B, T_bo, kind="call")
p_bo = ir_options.bond_option_black(P0T, F_B, K_bo, sig_B, T_bo, kind="put")
print(f"コール = {c_bo:.4f} ／ プット = {p_bo:.4f}")
print(f"パリティ c−p = {c_bo - p_bo:.4f} ／ P(0,T)(F_B−K) = {P0T * (F_B - K_bo):.4f}")

# 利回りボラ → 価格ボラ
D_mod, y0, sig_y = 4.2, 0.05, 0.15
print(f"\n利回りボラ変換: σ_B ≈ D·y·σ_y = {D_mod}×{y0}×{sig_y} = {D_mod * y0 * sig_y:.4f}")""")
)

# Cell 06: caps md
cells.append(
    md(r"""## 3. キャップとフロア（§29.2、eq 29.7/29.8）

**キャップ** = 変動金利が上限 $R_K$ を超えた差額を受け取る金利コールの列。
1本（キャップレット）は Black モデルで：

$$\text{caplet} = L\delta_k P(0,t_{k+1})[F_k N(d_1) - R_K N(d_2)], \quad
d_1 = \frac{\ln(F_k/R_K) + \sigma_k^2 t_k/2}{\sigma_k\sqrt{t_k}}$$

ボラは**観測時点** $t_k$ で $\sqrt{t_k}$、割引は**支払時点** $t_{k+1}$ の $P(0,t_{k+1})$。
キャップ = キャップレットの和。""")
)

# Cell 07: caplet from curve
cells.append(
    code(r"""# --- 第4冊の bootstrap カーブからフォワードを出してキャップを価格付け ---
instruments = [
    (0.25, 0.0, 99.6), (0.50, 0.0, 99.0), (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5), (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
CURVE = (bt_times, bt_zeros)


def fwd_simple(t0, t1):
    z0 = rates.zero_interp(t0, *CURVE) if t0 > 0 else 0.0
    z1 = rates.zero_interp(t1, *CURVE)
    f_cont = (z1 * t1 - z0 * t0) / (t1 - t0)
    return (math.exp(f_cont * (t1 - t0)) - 1.0) / (t1 - t0)


L_CAP, R_K, SIG_FLAT = 1e6, 0.025, 0.20
periods = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0)]
forwards = [fwd_simple(a, b) for a, b in periods]
accruals = [b - a for a, b in periods]
pay_disc = [swaps.discount(b, CURVE) for a, b in periods]
fix_times = [a for a, b in periods]
caplets = [ir_options.caplet_black(L_CAP, d, f, R_K, SIG_FLAT, t, p)
           for f, d, p, t in zip(forwards, accruals, pay_disc, fix_times)]
cap = sum(caplets)
display(pd.DataFrame({"観測t_k": fix_times, "フォワードF_k": [f"{f:.4%}" for f in forwards],
                     "キャップレット": [round(c, 2) for c in caplets]}))
print(f"キャップ（フラット vol {SIG_FLAT:.0%}, R_K={R_K:.1%}）= {cap:,.2f}")""")
)

# Cell 08: cap-floor parity
cells.append(
    code(r"""# --- キャップ − フロア = 固定 R_K 払いスワップ ---
cap_v = ir_options.cap_black(L_CAP, forwards, R_K, SIG_FLAT, accruals, pay_disc, fix_times, kind="cap")
floor_v = ir_options.cap_black(L_CAP, forwards, R_K, SIG_FLAT, accruals, pay_disc, fix_times, kind="floor")
swap_v = sum(L_CAP * d * p * (f - R_K) for f, d, p in zip(forwards, accruals, pay_disc))
print(f"キャップ = {cap_v:,.2f}")
print(f"フロア   = {floor_v:,.2f}")
print(f"キャップ − フロア = {cap_v - floor_v:,.2f}")
print(f"R_K 払いスワップの価値 = {swap_v:,.2f}（恒等）")
print("→ ATM（R_K = フォワードスワップレート）ではキャップ = フロア")""")
)

# Cell 09: vol stripping md
cells.append(
    md(r"""## 4. フラット vol とスポット vol のストリッピング（§29.2）

市場はキャップ1本に**フラットボラティリティ** $\hat\sigma$ を1つ呼びます。
でも各キャップレットの「真の」ボラ（**スポット vol** $\sigma_k$）は満期で異なる。
短いキャップから順に「キャップ価格 = 累積キャップレット + 新キャップレット」を
解いて $\sigma_k$ を**ストリッピング**します（brentq）。""")
)

# Cell 10: vol stripping demo
cells.append(
    code(r"""# 市場フラット vol（満期ごと）からスポット vol を逆算
market_flat = {1.0: 0.18, 1.5: 0.20, 2.0: 0.19}  # キャップ満期 → フラット vol
# 各満期キャップの市場価格 = フラット vol で全キャップレットを評価した値
spot_vols = []
cum_price = 0.0
for idx, (a, b) in enumerate(periods):
    mat = b
    flat = market_flat[mat]
    # この満期キャップの市場価格（フラット vol で全レット評価）
    mkt_price = sum(ir_options.caplet_black(L_CAP, accruals[j], forwards[j], R_K, flat,
                                            fix_times[j], pay_disc[j])
                    for j in range(idx + 1))
    target_caplet = mkt_price - cum_price  # 新キャップレットの価値

    def _obj(sig, j=idx):
        return ir_options.caplet_black(L_CAP, accruals[j], forwards[j], R_K, sig,
                                       fix_times[j], pay_disc[j]) - target_caplet

    sig_k = brentq(_obj, 1e-4, 2.0)
    spot_vols.append(sig_k)
    cum_price += ir_options.caplet_black(L_CAP, accruals[idx], forwards[idx], R_K, sig_k,
                                         fix_times[idx], pay_disc[idx])

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(fix_times, [market_flat[b] * 100 for a, b in periods], "o--", label="フラット vol")
ax1.plot(fix_times, np.array(spot_vols) * 100, "s-", label="スポット vol（ストリップ）")
ax1.set_xlabel("キャップレット観測時点 t_k")
ax1.set_ylabel("ボラティリティ (%)")
ax1.set_title("フラット vol は平均、スポット vol が各レットの真の vol")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 11: swaption md
cells.append(
    md(r"""## 5. スワプション（§29.3、eq 29.10/29.11）

将来 $T$ に $n$ 年スワップに入る権利。ペイヤー（固定払い権）は Black で：

$$V_{\text{payer}} = L\,A(0)[s_F N(d_1) - s_K N(d_2)], \qquad
A(0) = \frac{1}{m}\sum_{i=1}^{mn} P(0,T_i)$$

$s_F$ はフォワードスワップレート、$A(0)$ はスワップ・アニュイティ。
レシーバーはプット型。ATM（$s_K = s_F$）では payer = receiver。""")
)

# Cell 12: swaption demo
cells.append(
    code(r"""# 1年後にスタートする2年スワップのスワプション（半年払い）
swap_pays = [1.5, 2.0, 2.5, 3.0]  # スワップの支払時点
annuity = 0.5 * sum(swaps.discount(t, CURVE) for t in swap_pays)  # A(0) = (1/m)ΣP
# フォワードスワップレート s_F
s_F = (swaps.discount(1.0, CURVE) - swaps.discount(3.0, CURVE)) / annuity
print(f"フォワードスワップレート s_F = {s_F:.4%}, アニュイティ A(0) = {annuity:.4f}")

L_SW, SIG_SW, T_OPT = 1e6, 0.20, 1.0
for s_K in (s_F, 0.03, 0.04):
    pay = ir_options.swaption_black(L_SW, annuity, s_F, s_K, SIG_SW, T_OPT, kind="payer")
    rec = ir_options.swaption_black(L_SW, annuity, s_F, s_K, SIG_SW, T_OPT, kind="receiver")
    tag = " ← ATM（payer=receiver）" if abs(s_K - s_F) < 1e-9 else ""
    print(f"s_K={s_K:.4%}: ペイヤー {pay:,.2f} / レシーバー {rec:,.2f}{tag}")""")
)

# Cell 13: interactive vol cube slice
cells.append(
    code(r"""# --- ボラティリティ・キューブの断面（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
sig_sl = widgets.FloatSlider(value=0.20, min=0.05, max=0.50, step=0.02, description="σ_swap")
t_sl = widgets.FloatSlider(value=1.0, min=0.25, max=3.0, step=0.25, description="オプション満期T")


def _upd_swaption(change=None):
    ax2.clear()
    sks = np.linspace(0.01, 0.06, 60)
    payers = [ir_options.swaption_black(L_SW, annuity, s_F, sk, sig_sl.value, t_sl.value,
                                        kind="payer") for sk in sks]
    recs = [ir_options.swaption_black(L_SW, annuity, s_F, sk, sig_sl.value, t_sl.value,
                                      kind="receiver") for sk in sks]
    ax2.plot(sks * 100, payers, lw=2, label="ペイヤー")
    ax2.plot(sks * 100, recs, lw=2, label="レシーバー")
    ax2.axvline(s_F * 100, color="crimson", ls="--", lw=1, label=f"ATM s_F={s_F:.2%}")
    ax2.set_xlabel("ストライク s_K (%)")
    ax2.set_ylabel("スワプション価値")
    ax2.set_title(f"σ={sig_sl.value:.0%}, T={t_sl.value}年（ストライク×満期×テナーがキューブ）")
    ax2.legend()
    fig2.canvas.draw_idle()


sig_sl.observe(_upd_swaption, "value")
t_sl.observe(_upd_swaption, "value")
_upd_swaption()
display(widgets.HBox([sig_sl, t_sl]), fig2.canvas)""")
)

# Cell 14: model inconsistency md
cells.append(
    md(r"""### 3モデルの非整合（§29.3）

債券価格・金利・スワップレートが**すべて同時に対数正規**ということはあり得ません
（一方が対数正規なら他方はそうでない）。それでも実務で並用されるのは、
各市場のクォート慣行に合っているから。負金利環境では
**シフト対数正規**や**正規（Bachelier）モデル**が使われます（本書では概念のみ）。""")
)

# ===========================================================================
# Section 2: Ch.30 convexity / timing / quanto
# ===========================================================================

# Cell 15: 2-step md
cells.append(
    md(r"""## 6. 標準2ステップ評価と、その綻び（Ch.30）

通常の評価は「①フォワード値で期待値を計算 → ②リスクフリーで割引」。
これが正しいのは変数が**その支払いの自然な測度のマルチンゲール**のとき。
非標準デリバティブでは3つの補正が要ります：

| 調整 | 原因 |
|---|---|
| **コンベクシティ** | 債券価格-利回りの非線形性 |
| **タイミング** | 観測時点 ≠ 支払時点 |
| **クォント** | 外貨建て変数を自国通貨で決済 |

いずれも**ニュメレール変更に伴うドリフト補正**（第10冊 Ch.28 の枠組み）です。""")
)

# Cell 16: convexity md
cells.append(
    md(r"""## 7. コンベクシティ調整（§30.1、eq 30.1）

フォワード利回り $y_F$ を**そのまま期待利回りとして使うと過小**になります
（債券価格が利回りに対して凸 → Jensen）：

$$E_T(y_T) = y_F - \tfrac{1}{2}y_F^2\sigma_y^2 T\,\frac{G''(y_F)}{G'(y_F)}$$

$G'<0, G''>0$ なので $G''/G'<0$、調整は**正**（期待利回り > フォワード利回り）。
第4冊で見た先物-フォワードのコンベクシティ調整 $\tfrac12\sigma^2 t_1 t_2$ も同型です。""")
)

# Cell 17: convexity demo
cells.append(
    code(r"""# --- コンベクシティ調整の大きさ（満期・ボラ依存） ---
y_F, sig_y = 0.05, 0.20
# 標準クーポン債の G''/G'（残存n年・年1回クーポン）の絶対値を近似
def g2_over_g1(y, n):
    # G(y) = Σ c e^{-y t} の D と C から G''/G' ≈ C/(-D) の絶対値
    times = np.arange(1.0, n + 1.0)
    cfs = np.array([y] * (int(n) - 1) + [1.0 + y]) if n >= 1 else np.array([1.0 + y])
    pv = cfs * np.exp(-y * times)
    g1 = -np.sum(times * pv)
    g2 = np.sum(times**2 * pv)
    return abs(g2 / g1)


ratio = g2_over_g1(y_F, 5)
ts = np.linspace(0.25, 10.0, 60)
adj = [ir_options.convexity_adjustment(y_F, sig_y, t, ratio) for t in ts]
fig3, ax3 = plt.subplots(figsize=(7.5, 4))
fig3.canvas.header_visible = False
ax3.plot(ts, np.array(adj) * 1e4, lw=2)
ax3.set_xlabel("満期 T（年）")
ax3.set_ylabel("コンベクシティ調整（bp）")
ax3.set_title(f"E_T(y) − y_F（y_F={y_F:.0%}, σ_y={sig_y:.0%}, |G''/G'|={ratio:.2f}）")
display(fig3.canvas)
print(f"T=5年: 調整 = {ir_options.convexity_adjustment(y_F, sig_y, 5.0, ratio) * 1e4:.2f} bp")
print("→ CMS スワップ（スワップレート参照）等でこの調整が効く")""")
)

# Cell 18: futures convexity recap md
cells.append(
    md(r"""### 先物コンベクシティの再訪（§30, 第4冊リンク）

ユーロドル/SOFR 先物の「先物レート > フォワードレート」も同じ話：

$$\text{forward rate} = \text{futures rate} - \tfrac{1}{2}\sigma^2 t_1 t_2$$

先物の日次値洗いが金利と相関するため、長い限月ほど $t_1 t_2$ で調整が拡大します
（第4冊 Ch.6 で実装したものの理論的位置づけ）。""")
)

# Cell 19: timing md
cells.append(
    md(r"""## 8. タイミング調整（§30.2、eq 30.2/30.3）

変数の**観測時点** $T$ と**支払時点** $T^* > T$ がずれると、ニュメレールを
$P(t,T)$ から $P(t,T^*)$ に変える必要があり、期待値に補正が入ります：

$$E_{T^*}(V_T) = E_T(V_T)\exp\!\left[-\frac{\rho_{VR}\sigma_V\sigma_R R_F(T^*-T)}{1+R_F/m}\,T\right]$$

LIBOR-in-arrears（第7冊）の凸性調整はこの特殊ケースです
（観測と支払いが同時 = タイミングのずれ）。""")
)

# Cell 20: quanto md
cells.append(
    md(r"""## 9. クォント調整（§30.3、eq 30.5）

外貨建ての変数 $V$ を**自国通貨で決済**する（クォント）と、為替との相関ぶん
ドリフトが変わります：

$$E_X(V_T) = E_Y(V_T)\,e^{\rho_{VW}\sigma_V\sigma_W T}
\;\approx\; E_Y(V_T)(1 + \rho_{VW}\sigma_V\sigma_W T)$$

$\sigma_W \approx$ 為替ボラ、$\rho_{VW}\approx$ 変数と為替の相関。
**ジーゲルのパラドックス**（$S$ と $1/S$ の非対称）もこの調整で解消します。
diff スワップ（外貨金利×自国元本）が典型例です。""")
)

# Cell 21: quanto demo
cells.append(
    code(r"""# --- クォント調整の大きさ（相関依存） ---
V_fwd, sig_V, sig_S, T_q = 0.04, 0.15, 0.10, 2.0
rows = []
for rho in (-0.5, -0.2, 0.0, 0.3, 0.6):
    adj_factor = math.exp(rho * sig_V * sig_S * T_q)
    rows.append({"相関ρ": rho, "調整係数": round(adj_factor, 5),
                 "調整後の期待値": f"{V_fwd * adj_factor:.4%}",
                 "調整(bp)": round((V_fwd * adj_factor - V_fwd) * 1e4, 2)})
display(pd.DataFrame(rows))
print("ρ>0（外貨金利と為替が正相関）なら自国測度での期待金利は上がる")
print("3つの調整はすべて「ニュメレール変更 → ドリフト補正」（Ch.28）の応用")""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 22: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_ir_options.py にも同等の検証あり） ---
checks = []
p_chk = math.exp(-0.065 * 1.25)
caplet_chk = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p_chk, kind="caplet")
floorlet_chk = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p_chk, kind="floorlet")
checks.append(("caplet 519.0046", caplet_chk, 519.0046, 1e-3))
checks.append(("floorlet 2823.9125", floorlet_chk, 2823.9125, 1e-3))
checks.append(("caplet−floorlet パリティ", caplet_chk - floorlet_chk,
               1e6 * 0.25 * p_chk * (0.07 - 0.08), 1e-6))
checks.append(("キャップ−フロア = スワップ", cap_v - floor_v, swap_v, 1e-6))

pay_atm = ir_options.swaption_black(L_SW, annuity, s_F, s_F, SIG_SW, T_OPT, kind="payer")
rec_atm = ir_options.swaption_black(L_SW, annuity, s_F, s_F, SIG_SW, T_OPT, kind="receiver")
checks.append(("ATM スワプション payer=receiver", pay_atm, rec_atm, 1e-9))
pay_off = ir_options.swaption_black(L_SW, annuity, s_F, 0.03, SIG_SW, T_OPT, kind="payer")
rec_off = ir_options.swaption_black(L_SW, annuity, s_F, 0.03, SIG_SW, T_OPT, kind="receiver")
checks.append(("payer−receiver = L·A·(s_F−s_K)", pay_off - rec_off,
               L_SW * annuity * (s_F - 0.03), 1e-6))

checks.append(("コンベクシティ調整 > 0",
               float(ir_options.convexity_adjustment(0.05, 0.2, 5.0, ratio) > 0), 1.0, 0.0))
checks.append(("コンベクシティ調整 ∝ T",
               ir_options.convexity_adjustment(0.05, 0.2, 2.0, ratio),
               2.0 * ir_options.convexity_adjustment(0.05, 0.2, 1.0, ratio), 1e-12))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 23: exercises
cells.append(
    md(r"""## 10. 練習問題

**Q1.** ATM キャップとフロア（同一ストライク・満期）の価格が等しいのはなぜ？

<details><summary>解答</summary>

キャップ − フロア = R_K 払いスワップの価値。ATM では R_K = フォワードスワップレート
なのでスワップ価値 = 0 → キャップ = フロア。
</details>

**Q2.** フォワード利回りをそのまま期待利回りに使うと、CMS の価値はどちらにずれる？

<details><summary>解答</summary>

過小評価。コンベクシティ調整は正（E[y] > y_F）なので、スワップレート参照の
ペイオフは調整を加えないと低く出る。
</details>

**Q3.** 債券オプションで利回りボラ σ_y しか分からないとき、価格ボラ σ_B は？

<details><summary>解答</summary>

σ_B ≈ D·y₀·σ_y（D=修正デュレーション、y₀=フォワード利回り）。
デュレーションが価格と利回りの感応度を橋渡しする。
</details>""")
)

# Cell 24: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| Black 標準モデル | 商品ごとに対数正規を仮定（債券価格/金利/スワップレート） |
| キャップ | キャップレットの和。Black で価格付け |
| パリティ | キャップ − フロア = R_K 払いスワップ。ATM で cap=floor |
| ストリッピング | フラット vol → スポット vol を逐次逆算 |
| スワプション | payer/receiver。ATM で payer=receiver。vol キューブ |
| コンベクシティ | E[y] > y_F（凸性）。CMS・先物レートで効く |
| タイミング/クォント | 観測≠支払 / 外貨決済。ニュメレール変更の補正 |

**次へ**: `volumes/12_qualitative_summary`（Ch.1, 8, 16, 35, 36, 37 — 最終巻）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 25: closing md
cells.append(
    md(r"""---
*第11冊おわり。Black の標準市場モデルと3つの測度変更調整で、金利デリバの実務評価を一巡しました。*""")
)

# ===========================================================================
# Notebook assembly
# ===========================================================================

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "cells": cells,
}

# Normalize cell sources: all lines except the last should end with \n
for cell in nb["cells"]:
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_options.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
