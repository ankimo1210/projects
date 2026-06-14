"""
build_swaps_notebook.py
================================
nbformat-dict pattern to generate swaps.ipynb (Hull 11e Ch.7, 34).

Usage:
    uv run python build_swaps_notebook.py
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
    md(r"""# スワップ編（Hull 11e Ch.7, 34）

`johnhull/volumes` シリーズ第7冊。OTC デリバティブの主役：

- **金利スワップ（IRS）** — 仕組み、比較優位論とその批判（Ch.7）
- **2つの評価法** — 債券分解 vs FRA 分解（**恒等的に一致** — `hullkit.swaps` で確認）
- **通貨スワップ** — B_D − S₀·B_F（Ch.7）
- **非標準スワップの動物園** — コンパウンディング、LIBOR-in-arrears、CMS、キャンセラブル（Ch.34）

> 第4冊の `rates.py`（bootstrap カーブ）を本格活用します""")
)
cells.append(
    md(r"""> **核心** — 金利スワップ＝固定と変動の交換。評価は『カーブで割引くだけ』。<br>
> **直感** — 変動脚は次回 CF＋額面に分解するとパーになる → 評価が驚くほど単純に。<br>
> **実務** — 世界最大級のデリバ市場。ヘッジ・調達・ALM のあらゆる場面で使われる。""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import nbplot, rates, swaps

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.7 mechanics
# ===========================================================================

# Cell 03: IRS mechanics md
cells.append(
    md(r"""## 1. 金利スワップの仕組み（Ch.7）

プレーン・バニラ IRS: 同一名目元本 $L$ に対して**固定**と**変動**（SOFR 等）を周期交換。
元本は交換しない。市場では固定側のレート（スワップレート）がクォートされ、
LIBOR 廃止後は割引・参照とも **OIS/SOFR** が標準。

| 用語 | 意味 |
|---|---|
| 固定払い側 | 固定を払い変動を受ける（金利上昇にロング） |
| スワップレート | 開始時に価値ゼロになる固定レート＝パー債券クーポン |
| ベーシススワップ | 変動 vs 変動（異なる参照レート） |""")
)
cells.append(
    md(r"""> **核心** — 固定金利と変動金利(参照レート)を定期的に交換する相対契約。<br>
> **直感** — 元本は交換せず差金決済。固定受け＝変動払い。<br>
> **実務** — 企業の変動→固定転換、銀行の金利リスク管理の基本ツール。""")
)

# Cell 04: cashflow table demo
cells.append(
    code(r"""# --- キャッシュフロー表（名目1億、固定3%受取、半年毎、実現変動レートはシナリオ） ---
L_SW = 100_000_000.0
S_FIX = 0.03
float_scenario = [0.024, 0.027, 0.031, 0.034]  # 実現した6ヶ月レート（年率、シナリオ）
rows = []
for i, rf in enumerate(float_scenario, start=1):
    cf_fix = L_SW * S_FIX * 0.5
    cf_fl = L_SW * rf * 0.5
    rows.append({"支払時点 t（年）": 0.5 * i, "固定受取": f"{cf_fix:,.0f}",
                 "変動支払": f"{cf_fl:,.0f}", "ネット": f"{cf_fix - cf_fl:,.0f}"})
df_cf = pd.DataFrame(rows)
display(df_cf)
print("変動レートが固定3%を超える期間はネット支払いに転じる")""")
)

# Cell 05: comparative advantage md
cells.append(
    md(r"""## 2. 比較優位論とその批判（Ch.7）

| | 固定市場 | 変動市場 |
|---|---|---|
| AAA社 | 4.0% | SOFR + 0.3% |
| BBB社 | 5.2% | SOFR + 1.0% |
| スプレッド差 | a = 1.2% | b = 0.7% |

総利得 $= a - b = 0.5\%$ を両社（と仲介銀行）で分配できる。

**批判**: 固定市場のスプレッド差が大きいのは、固定で長期に貸す方が
信用リスクの期間が長いから。BBB 社の「変動での優位」は
ロールオーバーリスクを抱え込んでいるだけ、という面がある。""")
)
cells.append(
    md(r"""> **核心** — 『比較優位で双方得』の古典説明には穴がある。<br>
> **直感** — 得に見えるスプレッドは、実はロールオーバー(信用)リスクの対価。<br>
> **実務** — 『うまい話』の裏のリスクを見抜く訓練。タダ飯は基本ない。""")
)

# ===========================================================================
# Section 2: Ch.7 valuation
# ===========================================================================

# Cell 06: valuation approaches md
cells.append(
    md(r"""## 3. IRS の評価 — 2つの分解（Ch.7）

**債券分解**: 固定受取スワップ = 固定債ロング + 変動債ショート

$$V = B_{\text{fix}} - B_{\text{fl}}, \qquad B_{\text{fl}} = (L + L r^* \tau_1) P(0, t_1)$$

（変動債は次回支払直後に額面 — これが評価を簡単にする鍵）

**FRA 分解**（Hull 推奨）: スワップ = FRA の列。各期間の変動を
カーブのフォワードレートが実現すると仮定して

$$V = \sum_i L (s - f_i) \tau_i P(0, t_i)$$

**両者は恒等的に同じ値**になります（下で数値確認）。""")
)
cells.append(
    md(r"""> **核心** — 『債券の差』としても『FRA の列』としても評価でき、同じ値になる。<br>
> **直感** — 固定脚＝固定利付債、変動脚＝変動債(パー)。差し引きが価値。<br>
> **実務** — 2つの見方が一致することが実装の検算。どちらでカーブを当てるかは用途次第。

> **実務での出番 — なぜ変動債はパーなのか**
>
> 次回クーポンは確定済み、その先の変動 CF はフォワードで決まり割引と相殺する——結局『次回 CF＋額面を次回支払日まで割引く』だけになり、リセット直後は額面(パー)に等しい。この一見不思議な事実が IRS 評価を劇的に単純化する。スワップ評価の心臓部。""")
)

# Cell 07: swap rate from bootstrap curve
cells.append(
    code(r"""# --- 第4冊の bootstrap カーブからスワップレートを計算 ---
instruments = [
    (0.25, 0.0, 99.6), (0.50, 0.0, 99.0), (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5), (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
CURVE = (bt_times, bt_zeros)
PAY_T = [0.5, 1.0, 1.5, 2.0]
s_par = swaps.swap_rate(PAY_T, CURVE)
print(f"2年・半年払いのパー・スワップレート = {s_par:.4%}")
print("（カーブのゼロレート 2.0–2.4% に整合する水準）")

# 次回変動レート（カーブ整合のリセット済みレート）
r_next = (math.exp(rates.zero_interp(0.5, *CURVE) * 0.5) - 1.0) / 0.5
print(f"設定済みの次回6ヶ月レート（単利） = {r_next:.4%}")""")
)

# Cell 08: both approaches agree
cells.append(
    code(r"""# --- パーで両分解ともゼロ、オフマーケットでも完全一致 ---
rows = []
for s_fix in (s_par, 0.02, 0.03, 0.04):
    vb = swaps.irs_value_bonds(L_SW, s_fix, PAY_T, CURVE, next_float_rate=r_next)
    vf = swaps.irs_value_fras(L_SW, s_fix, PAY_T, CURVE, next_float_rate=r_next)
    rows.append({"固定レート": f"{s_fix:.4%}", "債券分解": round(vb, 2),
                 "FRA分解": round(vf, 2), "差": f"{abs(vb - vf):.2e}"})
df_val = pd.DataFrame(rows)
display(df_val)
print("固定3%受取は現行カーブ（〜2.4%）より有利 → 正の価値")""")
)

# Cell 09: floating bond intuition md
cells.append(
    md(r"""### なぜ変動債は「パー」か

リセット直後の変動債を考える。次回クーポンは市場レートそのもの →
次回支払時点での価値は（クーポン＋元本の現在価値の合計が）ちょうど額面。
帰納的に、**リセットの瞬間の変動債は常に額面**。
期中は「確定済みの次回クーポン＋額面」を次回支払日まで割り引くだけでよい。""")
)

# Cell 10: DV01 / sensitivity chart
cells.append(
    code(r"""# --- 平行シフト感応度（受取固定の価値 vs シフト幅） ---
shifts = np.linspace(-0.02, 0.02, 41)
vals = []
for ds in shifts:
    crv = (CURVE[0], [z + ds for z in CURVE[1]])
    rn = (math.exp(rates.zero_interp(0.5, *crv) * 0.5) - 1.0) / 0.5
    vals.append(swaps.irs_value_bonds(L_SW, s_par, PAY_T, crv, next_float_rate=rn))
vals = np.array(vals)
dv01 = (vals[21] - vals[19]) / 2.0 / 10.0  # 10bp あたり→1bp

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(shifts * 1e4, np.array(vals) / 1e6, lw=2)
ax1.axhline(0.0, color="black", lw=0.8)
ax1.set_xlabel("平行シフト（bp）")
ax1.set_ylabel("スワップ価値（百万）")
ax1.set_title(f"受取固定はデュレーション・ロング（DV01 ≈ {abs(dv01):,.0f}/bp）")
display(fig1.canvas)
print("※ ここではシフト後カーブで次回変動レートも再計算（開始直後のアニュイティDV01）。設定済みレートを固定すると感応度はやや小さくなる")""")
)

# Cell 11: interactive shift
cells.append(
    code(r"""# --- 金利シナリオ（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
shift_sl = widgets.FloatSlider(value=0.0, min=-200.0, max=200.0, step=10.0,
                               description="シフト(bp)")
fix_sl = widgets.FloatSlider(value=round(s_par * 100, 2), min=1.0, max=5.0, step=0.05,
                             description="固定(%)")


def _upd_swap(change=None):
    ax2.clear()
    ds = shift_sl.value / 1e4
    s_fx = fix_sl.value / 100.0
    crv = (CURVE[0], [z + ds for z in CURVE[1]])
    rn = (math.exp(rates.zero_interp(0.5, *crv) * 0.5) - 1.0) / 0.5
    taus = np.diff(np.concatenate([[0.0], np.asarray(PAY_T)]))
    times_aug = np.concatenate([[0.0], np.asarray(PAY_T)])
    pvs = []
    for i, t in enumerate(PAY_T):
        t0, t1 = times_aug[i], times_aug[i + 1]
        if i == 0:
            f_simple = rn
        else:
            z0 = rates.zero_interp(t0, *crv)
            z1 = rates.zero_interp(t1, *crv)
            f_simple = (math.exp((z1 * t1 - z0 * t0)) - 1.0) / (t1 - t0)
        pvs.append(L_SW * (s_fx - f_simple) * taus[i] * swaps.discount(float(t1), crv) / 1e6)
    ax2.bar([str(t) for t in PAY_T], pvs)
    ax2.axhline(0.0, color="black", lw=0.8)
    total = swaps.irs_value_fras(L_SW, s_fx, PAY_T, crv, next_float_rate=rn) / 1e6
    ax2.set_xlabel("支払時点（年）")
    ax2.set_ylabel("ネットCFのPV（百万）")
    ax2.set_title(f"受取固定 {s_fx:.2%}, シフト {shift_sl.value:+.0f}bp → 合計 {total:+.2f} 百万")
    fig2.canvas.draw_idle()


shift_sl.observe(_upd_swap, "value")
fix_sl.observe(_upd_swap, "value")
_upd_swap()
display(widgets.HBox([shift_sl, fix_sl]), fig2.canvas)""")
)

# Cell 12: OIS note md
cells.append(
    md(r"""### OIS / SOFR 移行メモ（Ch.7）

- 割引は2010年代に OIS へ、参照レートは2021–23年の LIBOR 廃止で SOFR/SONIA/TONAR へ移行
- LIBOR 時代の「LIBOR で割引・LIBOR を参照」から、
  クレジット・スプレッドをほぼ含まないレートへ移行
- 本シリーズでは単一カーブで簡略化（Hull 11e の扱いと同じ）""")
)

# ===========================================================================
# Section 3: Ch.7 currency swaps
# ===========================================================================

# Cell 13: currency swap md
cells.append(
    md(r"""## 4. 通貨スワップ（Ch.7）

固定-固定の通貨スワップ: **元本と利息を異なる通貨で交換**
（金利スワップと違い、開始・終了時に元本も交換）。

評価は債券分解で：ドル受取・外貨払いなら

$$V_{\text{swap}} = B_D - S_0 B_F$$

（$B_D$: ドル CF をドルカーブで割引、$B_F$: 外貨 CF を外貨カーブで割引、$S_0$: スポット）
フォワード為替の列として評価する方法も等価です。""")
)
cells.append(
    md(r"""> **核心** — 異通貨の元本・金利を交換。元本も交換する点が IRS と違う。<br>
> **直感** — 2つの債券(各通貨)の差、またはフォワード為替の列として評価する。<br>
> **実務** — 多通貨調達・為替ヘッジ。元本交換ぶんエクスポージャが大きく信用リスクも大きい。""")
)

# Cell 14: currency swap demo
cells.append(
    code(r"""# --- Hull Example 7.2/7.3: ドル4%払い・円3%受け（$10M ↔ ¥1,200M, S0=1/110） ---
dom_times = [1.0, 2.0, 3.0]
dom_cfs = [0.4, 0.4, 10.4]            # ドル: 4% クーポン + 償還（百万ドル）
dom_curve = ([1.0, 2.0, 3.0], [0.025, 0.025, 0.025])
for_times = [1.0, 2.0, 3.0]
for_cfs = [36.0, 36.0, 1236.0]        # 円: 3% クーポン + 償還（百万円）
for_curve = ([1.0, 2.0, 3.0], [0.015, 0.015, 0.015])
SPOT_FX = 1.0 / 110.0                  # ドル/円

b_d = sum(cf * swaps.discount(t, dom_curve) for t, cf in zip(dom_times, dom_cfs))
b_f = sum(cf * swaps.discount(t, for_curve) for t, cf in zip(for_times, for_cfs))
v_ccy = -swaps.currency_swap_value(dom_times, dom_cfs, dom_curve,
                                   for_times, for_cfs, for_curve, SPOT_FX)  # 円受け側
print(f"B_D = {b_d:.4f} 百万ドル ／ B_F = {b_f:.2f} 百万円 ／ S0·B_F = {SPOT_FX * b_f:.4f} 百万ドル")
print(f'円受け・ドル払いスワップの価値 = S0·B_F - B_D = {v_ccy:.4f} 百万ドル (Hull: 0.9629)')""")
)

# Cell 15: forwards view md
cells.append(
    md(r"""### フォワード分解の見方

各交換日を「その日の為替フォワードで決済する FX フォワード」とみなしても
同じ価値になります（金利平価 $F_t = S_0 e^{(r-r_f)t}$ がカーブ整合だから）。
信用リスクの観点では、通貨スワップは**満期に元本交換がある**ぶん
金利スワップよりエクスポージャーが大きい点に注意。""")
)

# Cell 16: zoo intro md
cells.append(
    md(r"""## 5. 非標準スワップの動物園（Ch.34）

| 型 | 仕掛け | 評価 |
|---|---|---|
| step-up / amortizing | 元本が時間変化 | フォワード実現仮定でOK |
| コンパウンディング | クーポンを複利積算し満期一括 | 同上（下で実演） |
| ベーシス | 変動 vs 変動 | 同上 |
| **LIBOR-in-arrears** | 観測=支払が同時点 | **凸性調整が必要** |
| **CMS** | スワップレート参照 | **凸性調整が必要**（→第11冊） |
| **diff (quanto)** | 外貨金利×自国元本 | **クアント調整**（→第11冊） |
| アクルアル | レンジ内の日数でクーポン | バイナリオプション分解 |
| キャンセラブル | 解約権付き | スワップ＋スワプション（→第11冊） |""")
)
cells.append(
    md(r"""> **核心** — アモチ・ステップアップ・ベーシス・キャンセラブル等、変種は無数。<br>
> **直感** — 標準スワップ＋α(オプション性など)に分解して評価する。<br>
> **実務** — 顧客ニーズに合わせた仕立て。分解して既知の部品で値付けるのが定石。""")
)

# Cell 17: compounding swap demo
cells.append(
    code(r"""# --- コンパウンディングスワップ: フォワード実現仮定で評価 ---
# 固定側 3% を年1回複利で2年間積算、満期一括 vs 変動側も同様に複利積算
fix_compounded = L_SW * ((1.0 + 0.03) ** 2 - 1.0)
f1 = (math.exp(rates.zero_interp(1.0, *CURVE) * 1.0) - 1.0)  # 0→1年の単利フォワード
z1 = rates.zero_interp(1.0, *CURVE)
z2 = rates.zero_interp(2.0, *CURVE)
f2 = math.exp(z2 * 2.0 - z1 * 1.0) - 1.0  # 1→2年の単利フォワード
fl_compounded = L_SW * ((1.0 + f1) * (1.0 + f2) - 1.0)
v_comp = (fix_compounded - fl_compounded) * swaps.discount(2.0, CURVE)
print(f"固定積算 = {fix_compounded:,.0f} ／ 変動積算（フォワード実現） = {fl_compounded:,.0f}")
print(f"受取固定コンパウンディングスワップの価値 = {v_comp:,.0f}")""")
)

# Cell 18: in-arrears md
cells.append(
    md(r"""## 6. LIBOR-in-arrears と凸性調整（Ch.30 の適用）

標準スワップは「期首に観測・期末に支払」。in-arrears は「期末に観測・即支払」。
このタイミングのずれは**フォワードレートでは正しく評価できず**、調整が要ります：

$$\hat F = F + \frac{F^2 \sigma^2 \tau T}{1 + F\tau}$$

（$F$: フォワードレート、$\sigma$: そのボラ、$T$: 観測時点、$\tau$: 期間）
調整は常に正 — in-arrears の受け手はフォワードより高いレートを期待できます。
（この閉形式は eq (30.1) を1期間債 G(y)=1/(1+yτ) に適用したもの。旧版 §34 の古典式で、11e 本文は Ch.30 に委譲）""")
)
cells.append(
    md(r"""> **核心** — 支払タイミングが標準とずれると、凸性調整が必要になる。<br>
> **直感** — 測度(ニュメレール)が変わると、フォワードに小さな補正項が乗る。<br>
> **実務** — 非標準の支払構造の正確な値付け。無視すると系統的に誤る。""")
)

# Cell 19: in-arrears chart
cells.append(
    code(r"""F_IA, SIG_IA, TAU_IA = 0.05, 0.20, 0.5
ts_ia = np.linspace(0.5, 10.0, 60)
adj_ia = F_IA**2 * SIG_IA**2 * TAU_IA * ts_ia / (1.0 + F_IA * TAU_IA)

fig3, ax3 = plt.subplots(figsize=(7.5, 4))
fig3.canvas.header_visible = False
ax3.plot(ts_ia, adj_ia * 1e4, lw=2)
ax3.set_xlabel("観測時点 T（年）")
ax3.set_ylabel("調整幅（bp）")
ax3.set_title(f"in-arrears 凸性調整（F={F_IA:.0%}, σ={SIG_IA:.0%}, τ={TAU_IA}）: T に比例して拡大")
display(fig3.canvas)
print(f"T=5年: 調整 = {F_IA**2 * SIG_IA**2 * TAU_IA * 5.0 / (1.0 + F_IA * TAU_IA) * 1e4:.2f} bp")""")
)

# Cell 20: equity / cancellable md
cells.append(
    md(r"""## 7. エクイティスワップとキャンセラブル（Ch.34）

- **エクイティスワップ**: 指数トータルリターン vs 変動。
  支払直後の価値はゼロ（指数1単位と変動債1単位の交換に等価。固定との交換では一般にゼロでない）
- **キャンセラブルスワップ** = 普通のスワップ ＋ スワプション。
  複数解約日ならバミューダン・スワプション（欧州型解約は第11冊 Ch.29 の Black で、
  バミューダン型はツリー/LSM — 第6冊の技法がここで効く）
- **アクルアルスワップ** = 日次バイナリ・キャップレットの束""")
)
cells.append(
    md(r"""> **核心** — 株式リターンと金利の交換、解約権付きなど。<br>
> **直感** — エクイティ脚＝株トータルリターン、解約権＝スワプション内蔵。<br>
> **実務** — ファンドの合成エクスポージャ取得、資本効率化に使われる。""")
)

# ===========================================================================
# Section 4: verification / exercises / summary
# ===========================================================================

# Cell 21: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_swaps.py にも同等の検証あり） ---
checks = []
vb_par = swaps.irs_value_bonds(L_SW, s_par, PAY_T, CURVE, next_float_rate=r_next)
vf_par = swaps.irs_value_fras(L_SW, s_par, PAY_T, CURVE, next_float_rate=r_next)
checks.append(("パーで債券分解 ≈ 0", vb_par / L_SW, 0.0, 1e-9))
checks.append(("パーで FRA 分解 ≈ 0", vf_par / L_SW, 0.0, 1e-9))
vb_off = swaps.irs_value_bonds(L_SW, 0.03, PAY_T, CURVE, next_float_rate=r_next)
vf_off = swaps.irs_value_fras(L_SW, 0.03, PAY_T, CURVE, next_float_rate=r_next)
checks.append(("分解の恒等一致（s=3%）", vb_off / L_SW, vf_off / L_SW, 1e-12))
checks.append(("通貨スワップ Hull Ex 7.3 ≈ 0.9629", v_ccy, 0.9628, 1.5e-3))

ia_5 = F_IA**2 * SIG_IA**2 * TAU_IA * 5.0 / (1.0 + F_IA * TAU_IA)
assert ia_5 > 0.0
print(f"[OK] in-arrears 調整 > 0（T=5: {ia_5 * 1e4:.2f}bp）")

crv_up = (CURVE[0], [z + 0.01 for z in CURVE[1]])
rn_up = (math.exp(rates.zero_interp(0.5, *crv_up) * 0.5) - 1.0) / 0.5
v_up = swaps.irs_value_bonds(L_SW, s_par, PAY_T, crv_up, next_float_rate=rn_up)
assert v_up < vb_par - 1.0
print(f"[OK] +100bp で受取固定の価値低下: {vb_par:,.0f} → {v_up:,.0f}")

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 22: exercises
cells.append(
    md(r"""## 8. 練習問題

**Q1.** 受取固定スワップの残存1.5年、固定4%・半年払い、フラット連続3%カーブ、
直前リセットの6ヶ月レート（単利）3.05%。債券分解の B_fl は？

<details><summary>解答</summary>

B_fl = (1 + 0.0305×0.5)·e^{−0.03×0.5} ≈ 1.0001（額面1あたり）。
リセット直後なのでほぼ額面どおり。
</details>

**Q2.** スワップレートが「パー債券のクーポン」と同じものなのはなぜ？

<details><summary>解答</summary>

s·Σ τP + P(t_n) = 1 ⇔ 固定債の価格が額面 ⇔ V = B_fix − B_fl = 0
（変動債はパー）。同じ等式。
</details>

**Q3.** LIBOR-in-arrears で調整が「正」になる直感は？

<details><summary>解答</summary>

レートが高い状態では割引が強く効き、支払いの現在価値の非対称性が生じる。
F の凸関数の期待値 > 期待値の関数（Jensen）で、in-arrears 観測は
高レート側に厚く払う構造 → フォワードより高い実効レート。
</details>""")
)

# Cell 23: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| IRS | 固定 vs 変動。スワップレート＝パー債券クーポン |
| 評価 | 債券分解 ≡ FRA 分解（変動債はリセット直後パー） |
| 通貨スワップ | B_D − S₀B_F。元本交換ありで信用エクスポージャー大 |
| 非標準 | 大半は「フォワード実現」でOK。観測/支払タイミングが歪むと凸性調整 |
| 接続 | 凸性・CMS・クアント・スワプション → 第11冊（Ch.29–30） |

**次へ**: `volumes/08_risk_var`（Ch.22 — VaR/ES）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 24: closing pointer md
cells.append(
    md(r"""---
*第7冊おわり。`hullkit.swaps` は第11冊（キャップ・スワプション）の土台になります。*""")
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
for i, cell in enumerate(nb["cells"]):
    cell["id"] = f"cell-{i:03d}"
    src = cell["source"]
    if isinstance(src, list) and len(src) > 1:
        for i in range(len(src) - 1):
            if not src[i].endswith("\n"):
                src[i] += "\n"
        if src[-1].endswith("\n"):
            src[-1] = src[-1].rstrip("\n")

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swaps.ipynb")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook saved: {out_path}")
print(f"Total cells: {len(cells)}")
