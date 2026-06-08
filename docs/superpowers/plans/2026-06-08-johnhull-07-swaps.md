# johnhull 07_swaps Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.swaps` (IRS/currency swap valuation on rates.py curves, TDD) and the 25-cell `volumes/07_swaps/swaps.ipynb` covering Hull 11e Ch.7 and Ch.34.

**Architecture:** As volumes 01–06. The verification axis: the two textbook valuation decompositions (bonds vs FRAs) are algebraically identical — tests pin that equality to 1e-10, and the par swap rate zeroes both.

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-07-swaps-design.md`

Implementer notes (as previous volumes): ruff lints hullkit src/tests, NOT `build_*_notebook.py`; ruff clean before each commit; commits on main, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` after blank line; stage only what each task specifies.

---

### Task 1: hullkit.swaps (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_swaps.py`
- Create: `johnhull/hullkit/src/hullkit/swaps.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_swaps.py`:

```python
"""Tests for hullkit.swaps (Hull 11e Ch.7)."""

import math

import numpy as np
import pytest

from hullkit import swaps

# upward-sloping test curve (continuous zeros)
CURVE = ([0.5, 1.0, 1.5, 2.0, 3.0], [0.020, 0.024, 0.027, 0.029, 0.032])
PAY_TIMES = [0.5, 1.0, 1.5, 2.0]


def _simple_rate_to(t1, curve):
    # curve-consistent simple rate for the period (0, t1)
    from hullkit import rates

    z1 = rates.zero_interp(t1, *curve)
    return (math.exp(z1 * t1) - 1.0) / t1


def test_par_swap_has_zero_value_both_ways():
    s = swaps.swap_rate(PAY_TIMES, CURVE)
    r1 = _simple_rate_to(0.5, CURVE)
    v_bonds = swaps.irs_value_bonds(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    v_fras = swaps.irs_value_fras(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    assert v_bonds == pytest.approx(0.0, abs=1e-9)
    assert v_fras == pytest.approx(0.0, abs=1e-9)


def test_bonds_equals_fras_off_market():
    r1 = _simple_rate_to(0.5, CURVE)
    for s_fixed in (0.01, 0.03, 0.05):
        v_b = swaps.irs_value_bonds(250.0, s_fixed, PAY_TIMES, CURVE, next_float_rate=r1)
        v_f = swaps.irs_value_fras(250.0, s_fixed, PAY_TIMES, CURVE, next_float_rate=r1)
        assert v_b == pytest.approx(v_f, abs=1e-10)


def test_swap_rate_flat_curve_hand_value():
    flat = ([0.5, 1.0, 1.5, 2.0], [0.03, 0.03, 0.03, 0.03])
    s = swaps.swap_rate([0.5, 1.0, 1.5, 2.0], flat)
    # hand: (1 - e^{-0.06}) / (0.5 * (e^{-0.015}+e^{-0.03}+e^{-0.045}+e^{-0.06}))
    num = 1.0 - math.exp(-0.06)
    den = 0.5 * sum(math.exp(-0.03 * t) for t in (0.5, 1.0, 1.5, 2.0))
    assert s == pytest.approx(num / den, abs=1e-12)
    # flat continuous 3% -> par semiannual simple rate slightly above 3%
    assert 0.030 < s < 0.0305


def test_currency_swap_hand_pin():
    dom = ([1.0, 2.0, 3.0], [3.0, 3.0, 103.0], ([1.0, 2.0, 3.0], [0.04, 0.04, 0.04]))
    forn = ([1.0, 2.0, 3.0], [60.0, 60.0, 1260.0], ([1.0, 2.0, 3.0], [0.015, 0.015, 0.015]))
    v = swaps.currency_swap_value(dom[0], dom[1], dom[2], forn[0], forn[1], forn[2], 0.009)
    assert v == pytest.approx(85.1075, abs=5e-4)


def test_receive_fixed_loses_value_when_rates_rise():
    s = swaps.swap_rate(PAY_TIMES, CURVE)
    r1 = _simple_rate_to(0.5, CURVE)
    bumped = (CURVE[0], [z + 0.01 for z in CURVE[1]])
    r1_b = _simple_rate_to(0.5, bumped)
    v0 = swaps.irs_value_bonds(100.0, s, PAY_TIMES, CURVE, next_float_rate=r1)
    v1 = swaps.irs_value_bonds(100.0, s, PAY_TIMES, bumped, next_float_rate=r1_b)
    assert v1 < v0 - 1e-6


def test_discount_basic():
    assert swaps.discount(1.0, ([1.0], [0.05])) == pytest.approx(np.exp(-0.05), abs=1e-12)
```

- [ ] **Step 2: Run to verify failure** (ImportError)

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/swaps.py`**

```python
"""Interest-rate and currency swap valuation (Hull 11e, Ch.7).

A curve is a (times, zero_rates) tuple with continuous compounding,
interpolated via rates.zero_interp; P(0, t) = exp(-z(t) * t).
"""

import math

import numpy as np

from . import rates


def discount(t, curve):
    """Discount factor P(0, t) from a (times, zeros) curve tuple."""
    times, zeros = curve
    return math.exp(-rates.zero_interp(t, times, zeros) * t)


def swap_rate(pay_times, curve):
    """Par swap rate s = (1 - P(0,t_n)) / sum(tau_i * P(0,t_i)) (Hull Ch.7)."""
    pay_times = np.asarray(pay_times, dtype=float)
    taus = np.diff(np.concatenate([[0.0], pay_times]))
    annuity = float(sum(tau * discount(float(t), curve) for tau, t in zip(taus, pay_times)))
    return (1.0 - discount(float(pay_times[-1]), curve)) / annuity


def irs_value_bonds(notional, s_fixed, pay_times, curve, next_float_rate, accrual_to_next=None):
    """Receive-fixed IRS value via the bond decomposition V = B_fix - B_fl.

    next_float_rate is the simple rate already set for the next floating
    payment; the floating bond is worth par immediately after that payment
    (Hull Ch.7), so B_fl = (L + L * r * tau1) * P(0, t1).
    """
    pay_times = np.asarray(pay_times, dtype=float)
    taus = np.diff(np.concatenate([[0.0], pay_times]))
    b_fix = sum(
        notional * s_fixed * tau * discount(float(t), curve)
        for tau, t in zip(taus, pay_times)
    )
    b_fix += notional * discount(float(pay_times[-1]), curve)
    tau1 = float(taus[0]) if accrual_to_next is None else accrual_to_next
    b_fl = (notional + notional * next_float_rate * tau1) * discount(float(pay_times[0]), curve)
    return b_fix - b_fl


def irs_value_fras(notional, s_fixed, pay_times, curve, next_float_rate=None):
    """Receive-fixed IRS value via the FRA decomposition (Hull's preferred).

    Each floating payment is assumed to realize the curve's forward rate
    (simple, over its accrual period); the preset first rate can be given.
    """
    pay_times = np.asarray(pay_times, dtype=float)
    times_aug = np.concatenate([[0.0], pay_times])
    value = 0.0
    for i in range(len(pay_times)):
        t0, t1 = float(times_aug[i]), float(times_aug[i + 1])
        tau = t1 - t0
        if i == 0 and next_float_rate is not None:
            f_simple = next_float_rate
        else:
            z0 = rates.zero_interp(t0, *curve) if t0 > 0.0 else 0.0
            z1 = rates.zero_interp(t1, *curve)
            f_cont = (z1 * t1 - z0 * t0) / tau
            f_simple = (math.exp(f_cont * tau) - 1.0) / tau
        value += notional * (s_fixed - f_simple) * tau * discount(t1, curve)
    return value


def currency_swap_value(
    domestic_times, domestic_cfs, domestic_curve,
    foreign_times, foreign_cfs, foreign_curve, spot,
):
    """Receive-domestic / pay-foreign swap value in domestic units: B_D - S0 * B_F."""
    b_d = sum(cf * discount(float(t), domestic_curve)
              for t, cf in zip(domestic_times, domestic_cfs))
    b_f = sum(cf * discount(float(t), foreign_curve)
              for t, cf in zip(foreign_times, foreign_cfs))
    return b_d - spot * b_f
```

- [ ] **Step 4: Verify** — 6 passed; full suite 68 passed; ruff clean. Quote the actual currency-swap value (should be ≈ 85.1075).

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/swaps.py johnhull/hullkit/tests/test_swaps.py
git commit -m "feat(hullkit): IRS and currency swap valuation with decomposition-identity tests"
```

---

### Task 2: build script — intro + Ch.7 (cells 00–12)

**Files:**
- Create: `johnhull/volumes/07_swaps/build_swaps_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–12** (helpers + assembly footer verbatim from `volumes/06_numerical_methods/build_numerical_notebook.py`; docstring title `build_swaps_notebook.py`; output `swaps.ipynb`)

````python
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
ax1.set_title(f"受取固定はデュレーション・ロング（DV01 ≈ {dv01:,.0f}/bp）")
display(fig1.canvas)""")
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

- 2010年代以降、割引も参照も **OIS（SOFR/SONIA/TONAR）** が標準に
- LIBOR 時代の「LIBOR で割引・LIBOR を参照」から、
  クレジット・スプレッドをほぼ含まないレートへ移行
- 本シリーズでは単一カーブで簡略化（Hull 11e の扱いと同じ）""")
)
````

- [ ] **Step 2: Build and validate** — `Total cells: 13`; nbformat validate → `13 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/07_swaps
git commit -m "feat(johnhull): 07 build script with IRS cells"
```

---

### Task 3: build script — currency swaps + Ch.34 + closing (cells 13–24)

**Files:**
- Modify: `johnhull/volumes/07_swaps/build_swaps_notebook.py`

- [ ] **Step 1: Insert cells 13–24 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
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

# Cell 14: currency swap demo
cells.append(
    code(r"""# --- 例: ドル建て3%債 vs 円建て1.5%債（想定元本 $100 ↔ ¥12,000、spot 0.009 $/¥相当） ---
dom_times = [1.0, 2.0, 3.0]
dom_cfs = [3.0, 3.0, 103.0]
dom_curve = ([1.0, 2.0, 3.0], [0.04, 0.04, 0.04])
for_times = [1.0, 2.0, 3.0]
for_cfs = [60.0, 60.0, 1260.0]  # 円のクーポン60＋償還1200
for_curve = ([1.0, 2.0, 3.0], [0.015, 0.015, 0.015])
SPOT_FX = 0.009

v_ccy = swaps.currency_swap_value(dom_times, dom_cfs, dom_curve,
                                  for_times, for_cfs, for_curve, SPOT_FX)
b_d = sum(cf * swaps.discount(t, dom_curve) for t, cf in zip(dom_times, dom_cfs))
b_f = sum(cf * swaps.discount(t, for_curve) for t, cf in zip(for_times, for_cfs))
print(f"B_D = {b_d:.4f}（ドル） ／ B_F = {b_f:.4f}（円） ／ S0 = {SPOT_FX}")
print(f"V = B_D − S0·B_F = {v_ccy:.4f}（ドル受取側）")""")
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

# Cell 17: compounding swap demo
cells.append(
    code(r"""# --- コンパウンディングスワップ: フォワード実現仮定で評価 ---
# 固定側 3% を年1回複利で2年間積算、満期一括 vs 変動側も同様に複利積算
pay_T = 2.0
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
    md(r"""## 6. LIBOR-in-arrears と凸性調整（Ch.34 → Ch.30）

標準スワップは「期首に観測・期末に支払」。in-arrears は「期末に観測・即支払」。
このタイミングのずれは**フォワードレートでは正しく評価できず**、調整が要ります：

$$\hat F = F + \frac{F^2 \sigma^2 \tau T}{1 + F\tau}$$

（$F$: フォワードレート、$\sigma$: そのボラ、$T$: 観測時点、$\tau$: 期間）
調整は常に正 — in-arrears の受け手はフォワードより高いレートを期待できます。""")
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

- **エクイティスワップ**: 指数トータルリターン vs 固定/変動。
  支払直後の価値はゼロ（指数1単位と変動債1単位の交換に等価）
- **キャンセラブルスワップ** = 普通のスワップ ＋ スワプション。
  複数解約日ならバミューダン・スワプション（評価は第11冊 Ch.29 の Black、
  またはツリー/LSM — 第6冊の技法がここで効く）
- **アクルアルスワップ** = 日次バイナリ・キャップレットの束""")
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
checks.append(("通貨スワップ・ピン 85.1075", v_ccy, 85.1075, 5e-4))

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
````

- [ ] **Step 2: Rebuild and validate** — `Total cells: 25`; nbformat validate → `25 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/07_swaps
git commit -m "feat(johnhull): 07 currency/nonstandard swap cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/07_swaps/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 7 → done; module list gains `swaps`)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output swaps_executed.ipynb`). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc.**

- [ ] **Step 3: Tests + lint:** hullkit suite → 68 passed; ruff johnhull clean; workspace minus gto (explicit paths) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/07_swaps/PROGRESS.md`**

```markdown
# 07_swaps — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `swaps.ipynb` (25 cells) generated by `build_swaps_notebook.py`
- Coverage: Hull 11e Ch.7 (IRS mechanics, bond vs FRA valuation identity,
  currency swaps, comparative advantage), Ch.34 (nonstandard swap zoo,
  compounding demo, in-arrears convexity)
- hullkit addition: `swaps.py` (discount, swap_rate, irs_value_bonds,
  irs_value_fras, currency_swap_value — 6 tests; suite 68)
- Verified: headless nbconvert, decomposition-identity assertion cell,
  hullkit pytest, ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_swaps_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-05 mechanics / 06-12 valuation /
  13-15 currency / 16-20 Ch.34 / 21 verification / 22 exercises / 23-24 summary
- CMS/quanto numerics + swaptions → volume 11; dual-curve OIS machinery
  out of scope per Hull's single-curve simplification
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 7 → done; module list `..., fd.` → `..., fd, swaps.`**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/07_swaps/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 07_swaps complete"
```

- [ ] **Step 7: Report** with quoted outputs.
