# johnhull 11_ir_derivatives_market Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.ir_options` (Black models for bond options/caps/swaptions + convexity adjustment, TDD) and the 27-cell `volumes/11_ir_derivatives_market/ir_options.ipynb` covering Hull 11e Ch.29 and Ch.30.

**Architecture:** As volumes 01–10. Built on rates.py (forwards/discounts) and swaps.py (annuity/swap rate). Black put-call parity identities are the verification axis.

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-11-ir-derivatives-market-design.md`

**Reference values** (hand-verified):

| Quantity | Value |
|---|---|
| Caplet (L=1e6, δ=0.25, F=7%, R_K=8%, σ=20%, t_k=1, P=e^{−0.065·1.25}) | 519.0046 |
| Floorlet (same) | 2823.9125 |
| caplet − floorlet | = L·δ·P·(F−R_K) = −2304.9079 (Black parity) |
| Swaption payer − receiver | = L·A·(s_F−s_K) |
| ATM swaption (s_K=s_F) | payer = receiver |

Implementer notes: as previous volumes (ruff scope, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`, stage only specified files, report tolerance failures).

---

### Task 1: hullkit.ir_options (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_ir_options.py`
- Create: `johnhull/hullkit/src/hullkit/ir_options.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_ir_options.py`:

```python
"""Tests for hullkit.ir_options against Hull 11e Ch.29/30."""

import math

import pytest

from hullkit import ir_options


def test_caplet_floorlet_values_and_parity():
    p = math.exp(-0.065 * 1.25)
    caplet = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p, kind="caplet")
    floorlet = ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.20, 1.0, p, kind="floorlet")
    assert caplet == pytest.approx(519.0046, abs=1e-3)
    assert floorlet == pytest.approx(2823.9125, abs=1e-3)
    # Black put-call parity: caplet - floorlet = L delta P (F - R_K)
    assert caplet - floorlet == pytest.approx(1e6 * 0.25 * p * (0.07 - 0.08), abs=1e-6)


def test_swaption_payer_receiver_parity_and_atm():
    L, A, s_F, sigma, T = 1e6, 3.5, 0.06, 0.20, 2.0
    payer = ir_options.swaption_black(L, A, s_F, 0.062, sigma, T, kind="payer")
    receiver = ir_options.swaption_black(L, A, s_F, 0.062, sigma, T, kind="receiver")
    assert payer - receiver == pytest.approx(L * A * (s_F - 0.062), abs=1e-6)
    # ATM: s_K = s_F -> payer == receiver
    pa = ir_options.swaption_black(L, A, s_F, s_F, sigma, T, kind="payer")
    ra = ir_options.swaption_black(L, A, s_F, s_F, sigma, T, kind="receiver")
    assert pa == pytest.approx(ra, abs=1e-9)


def test_cap_minus_floor_equals_swap():
    L = 1e6
    forwards = [0.05, 0.055, 0.06]
    accruals = [0.5, 0.5, 0.5]
    pay_disc = [math.exp(-0.05 * t) for t in (1.0, 1.5, 2.0)]
    fix_times = [0.5, 1.0, 1.5]
    R_K = 0.055
    cap = ir_options.cap_black(L, forwards, R_K, 0.2, accruals, pay_disc, fix_times, kind="cap")
    floor = ir_options.cap_black(L, forwards, R_K, 0.2, accruals, pay_disc, fix_times, kind="floor")
    swap = sum(
        L * d * p * (f - R_K) for f, d, p in zip(forwards, accruals, pay_disc)
    )
    assert cap - floor == pytest.approx(swap, abs=1e-6)


def test_bond_option_parity():
    p0t, f_b, k, sigma, T = 0.9, 102.0, 100.0, 0.08, 2.0
    c = ir_options.bond_option_black(p0t, f_b, k, sigma, T, kind="call")
    put = ir_options.bond_option_black(p0t, f_b, k, sigma, T, kind="put")
    assert c - put == pytest.approx(p0t * (f_b - k), abs=1e-9)


def test_convexity_adjustment_positive_and_scales():
    # G''/G' > 0 for a standard bond (price convex in yield) -> adjustment positive
    adj1 = ir_options.convexity_adjustment(0.05, 0.20, 1.0, 30.0)
    adj2 = ir_options.convexity_adjustment(0.05, 0.20, 2.0, 30.0)
    assert adj1 > 0.0
    assert adj2 == pytest.approx(2.0 * adj1, abs=1e-12)  # linear in T
    # expected yield = y_F + adjustment > y_F
    e_y = 0.05 + adj1
    assert e_y > 0.05


def test_validation_errors():
    with pytest.raises(ValueError):
        ir_options.caplet_black(1e6, 0.25, 0.07, 0.08, 0.2, 1.0, 0.9, kind="cap")
    with pytest.raises(ValueError):
        ir_options.swaption_black(1e6, 3.5, 0.06, 0.06, 0.2, 2.0, kind="straddle")
```

- [ ] **Step 2: Run to verify failure** (ImportError)

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/ir_options.py`**

```python
"""Black's-model interest-rate derivatives (Hull 11e, Ch.29/30)."""

import math

from scipy.stats import norm


def _black(forward, strike, sigma, T, df, kind_call):
    """Black-76 forward-price option value: df * [F N(d1) - K N(d2)] (call)."""
    d1 = (math.log(forward / strike) + 0.5 * sigma**2 * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if kind_call:
        return df * (forward * norm.cdf(d1) - strike * norm.cdf(d2))
    return df * (strike * norm.cdf(-d2) - forward * norm.cdf(-d1))


def bond_option_black(P0T, F_B, K, sigma_B, T, kind="call"):
    """European bond option, Black's model (Hull eq. 29.1/29.2).

    P0T = P(0, T); F_B = forward bond price; sigma_B = forward-price vol.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    return _black(F_B, K, sigma_B, T, P0T, kind == "call")


def caplet_black(L, delta, F, R_K, sigma, t_k, P_pay, kind="caplet"):
    """Single caplet/floorlet, Black's model (Hull eq. 29.7/29.8).

    L notional, delta accrual, F forward rate, R_K cap rate, sigma the rate's
    volatility, t_k the fixing time, P_pay = P(0, t_{k+1}).
    """
    if kind not in ("caplet", "floorlet"):
        raise ValueError(f"kind must be 'caplet' or 'floorlet', got {kind!r}")
    return L * delta * _black(F, R_K, sigma, t_k, P_pay, kind == "caplet")


def cap_black(L, forwards, R_K, sigma, accruals, pay_discounts, fixing_times, kind="cap"):
    """Cap or floor = sum of caplets/floorlets (Hull eq. 29.7). sigma is the
    flat volatility applied to every caplet (or pass spot vols via a loop)."""
    if kind not in ("cap", "floor"):
        raise ValueError(f"kind must be 'cap' or 'floor', got {kind!r}")
    leg = "caplet" if kind == "cap" else "floorlet"
    sig = sigma if isinstance(sigma, (list, tuple)) else [sigma] * len(forwards)
    return sum(
        caplet_black(L, d, f, R_K, s, t, p, kind=leg)
        for f, d, p, t, s in zip(forwards, accruals, pay_discounts, fixing_times, sig)
    )


def swaption_black(L, annuity, s_F, s_K, sigma, T, kind="payer"):
    """European swaption, Black's model (Hull eq. 29.10/29.11).

    annuity A(0) = sum of pay-date discount factors / m; s_F forward swap rate.
    """
    if kind not in ("payer", "receiver"):
        raise ValueError(f"kind must be 'payer' or 'receiver', got {kind!r}")
    return L * annuity * _black(s_F, s_K, sigma, T, 1.0, kind == "payer")


def convexity_adjustment(y_F, sigma_y, T, g2_over_g1):
    """Convexity adjustment to a forward bond yield (Hull eq. 30.1).

    Returns the amount to ADD to y_F to get the expected yield:
    -0.5 y_F^2 sigma_y^2 T (G''/G'). For a bond G'<0, G''>0 so G''/G' < 0 and
    the adjustment is positive; pass g2_over_g1 = |G''/G'| (a positive number).
    """
    return 0.5 * y_F**2 * sigma_y**2 * T * g2_over_g1
```

- [ ] **Step 4: Verify** — 6 passed; full suite 96 passed; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/ir_options.py johnhull/hullkit/tests/test_ir_options.py
git commit -m "feat(hullkit): Black-model IR derivatives (bond/cap/swaption) with parity tests"
```

---

### Task 2: build script — intro + Ch.29 (cells 00–14)

**Files:**
- Create: `johnhull/volumes/11_ir_derivatives_market/build_ir_options_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–14** (helpers + footer verbatim from `volumes/10_exotics_martingales/build_exotics_notebook.py`; title `build_ir_options_notebook.py`; output `ir_options.ipynb`)

````python
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
````

- [ ] **Step 2: Build and validate** — `Total cells: 15`; nbformat validate → `15 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/11_ir_derivatives_market
git commit -m "feat(johnhull): 11 build script with Black-model IR derivative cells"
```

---

### Task 3: build script — Ch.30 + closing (cells 15–26)

**Files:**
- Modify: `johnhull/volumes/11_ir_derivatives_market/build_ir_options_notebook.py`

- [ ] **Step 1: Insert cells 15–26 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
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
````

- [ ] **Step 2: Rebuild and validate** — `Total cells: 26`; nbformat validate → `26 cells valid`. (Spec estimated 27; actual 26 — fine.)

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/11_ir_derivatives_market
git commit -m "feat(johnhull): 11 convexity/timing/quanto cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/11_ir_derivatives_market/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 11 → done; module list gains `ir_options`)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output ir_options_executed.ipynb`). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc.**

- [ ] **Step 3: Tests + lint:** hullkit suite → 96 passed; ruff johnhull clean; workspace minus gto (explicit paths) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/11_ir_derivatives_market/PROGRESS.md`**

```markdown
# 11_ir_derivatives_market — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `ir_options.ipynb` (26 cells) generated by `build_ir_options_notebook.py`
- Coverage: Hull 11e Ch.29 (Black standard market models — bond options,
  caps/floors + cap-floor parity + vol stripping, swaptions + vol cube),
  Ch.30 (convexity, timing, quanto adjustments as numeraire changes)
- hullkit addition: `ir_options.py` (bond_option_black, caplet_black,
  cap_black, swaption_black, convexity_adjustment — 6 tests; suite 96).
  Built on rates.py / swaps.py.
- Verified: headless nbconvert, Black-parity assertion cell, hullkit pytest,
  ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_ir_options_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-14 Ch.29 / 15-21 Ch.30 / 22 verification /
  23 exercises / 24-25 summary
- Shifted-lognormal / Bachelier for negative rates, vol-cube calibration,
  Hull-White swaption analytic: md only (LMM/short-rate are in ir_models)
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 11 → done; module list `..., exotics.` → `..., exotics, ir_options.`**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/11_ir_derivatives_market/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 11_ir_derivatives_market complete"
```

- [ ] **Step 7: Report** with quoted outputs.
