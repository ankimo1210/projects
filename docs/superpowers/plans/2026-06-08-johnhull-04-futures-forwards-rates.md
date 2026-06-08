# johnhull 04_futures_forwards_rates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.rates` (curve/bond utilities, TDD) and the 34-cell `volumes/04_futures_forwards_rates/futures_rates.ipynb` covering Hull 11e Ch.2–6, rates-centric.

**Architecture:** Mirrors volumes 01–03: hullkit module first (TDD), then build script → ipynb, headless nbconvert gate. `rates.py` is the dependency for volumes 07/11 (continuous compounding throughout, Hull's standard).

**Tech Stack:** Python 3.12, uv workspace, numpy/scipy (brentq), matplotlib + ipympl + ipywidgets + japanize-matplotlib, nbformat, pytest.

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-04-futures-forwards-rates-design.md`

**Reference values** (hand-verified; Hull prints in parens):

| Quantity | Exact | Hull prints |
|---|---|---|
| 10% semiannual → continuous | 0.097580 | 9.758% |
| Table 4.2 bond (zeros 5.0/5.8/6.4/6.8%, 2y 6% semi) | 98.385 / YTM 0.0676 | 98.39 / 6.76% |
| Table 4.3 bootstrap zeros | 0.016032 / 0.020101 / 0.022245 / 0.022845 / 0.024162 | 1.603 / 2.010 / 2.225 / 2.284 / 2.416 % |
| forward_rate(3%@1y, 4%@2y) | 0.05 exact | 5% |
| FRA(100M, 5.8%, 5.0%, 1.5→2.0, R2=4%) | 369,246.5 | ≈369,200 |
| Table 4.6 bond (3y, 10% semi coupons, y=12% cc) | B=94.213, D=2.653 | 94.213 / 2.653 |
| Forward price S=40, r=5%, T=0.25 | 40.5031 | 40.50 |
| h* = 0.928×0.0263/0.0313 | 0.77976; jet-fuel N*=37.13 | 0.78 / ≈37 |
| Beta hedge 1.5×5,050,000/(1010×250) | 30.0 | 30 |
| Duration hedge 10M×6.8/(93,062.50×9.2) | 79.42 | 79.42 |

Implementer notes (as previous volumes): ruff lints hullkit src/tests, NOT `build_*_notebook.py`; ruff check + format clean before each commit; commits on main, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>` after a blank line; stage only what each task specifies; GE-PDF citation conventions.

---

### Task 1: hullkit.rates (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_rates.py`
- Create: `johnhull/hullkit/src/hullkit/rates.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_rates.py`:

```python
"""Tests for hullkit.rates against Hull 11e Ch.4 tables."""

import numpy as np
import pytest

from hullkit import rates

# Hull Table 4.3: (maturity, annual coupon on face 100 semiannual, price)
TABLE_4_3 = [
    (0.25, 0.0, 99.6),
    (0.50, 0.0, 99.0),
    (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5),
    (2.00, 5.0, 105.0),
]


def test_compounding_conversions():
    assert rates.to_continuous(0.10, 2) == pytest.approx(0.097580, abs=1e-5)  # Hull 9.758%
    for m in (1, 2, 4, 12):
        round_trip = rates.from_continuous(rates.to_continuous(0.07, m), m)
        assert round_trip == pytest.approx(0.07, abs=1e-12)


def test_bond_price_and_yield_table_4_2():
    times = [0.5, 1.0, 1.5, 2.0]
    cfs = [3.0, 3.0, 3.0, 103.0]
    zeros = [0.050, 0.058, 0.064, 0.068]
    p = rates.bond_price(times, cfs, zeros)
    assert p == pytest.approx(98.385, abs=5e-3)  # Hull 98.39
    assert rates.bond_yield(times, cfs, p) == pytest.approx(0.0676, abs=2e-4)


def test_bootstrap_table_4_3():
    times, zeros = rates.bootstrap_zero_curve(TABLE_4_3)
    assert times == [0.25, 0.5, 1.0, 1.5, 2.0]
    expected = [0.016032, 0.020101, 0.022245, 0.022845, 0.024162]
    for got, want in zip(zeros, expected):
        assert got == pytest.approx(want, abs=5e-5)


def test_forward_rate_and_fra():
    assert rates.forward_rate(0.03, 1.0, 0.04, 2.0) == pytest.approx(0.05, abs=1e-12)
    v = rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040)
    assert v == pytest.approx(369_246.5, abs=1.0)  # Hull ~369,200


def test_duration_convexity_table_4_6():
    times = np.arange(0.5, 3.01, 0.5)
    cfs = [5.0] * 5 + [105.0]
    y = 0.12
    b = rates.bond_price(times, cfs, y)
    assert b == pytest.approx(94.213, abs=5e-3)
    d = rates.macaulay_duration(times, cfs, y)
    assert d == pytest.approx(2.653, abs=2e-3)
    # dB ~ -B D dy (Hull eq. 4.12)
    dy = 0.001
    actual = rates.bond_price(times, cfs, y + dy) - b
    assert actual == pytest.approx(-b * d * dy, abs=1e-3)
    # convexity improves the approximation for a large move
    dy = 0.02
    actual = rates.bond_price(times, cfs, y + dy) - b
    approx_lin = -b * d * dy
    c = rates.convexity(times, cfs, y)
    approx_conv = -b * d * dy + 0.5 * c * b * dy**2
    assert abs(actual - approx_conv) < abs(actual - approx_lin)


def test_zero_interp_flat_extrapolation():
    assert rates.zero_interp(0.10, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.02)
    assert rates.zero_interp(5.00, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.03)
    assert rates.zero_interp(0.625, [0.25, 1.0], [0.02, 0.03]) == pytest.approx(0.025)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest johnhull/hullkit/tests/test_rates.py -v`
Expected: ImportError — no `rates` module.

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/rates.py`**

```python
"""Interest-rate and bond utilities (Hull 11e, Ch.4).

Continuous compounding throughout — Hull's book standard. Used by the
volume-04 notebook and by later volumes (07 swaps, 11 IR derivatives).
"""

import math

import numpy as np
from scipy.optimize import brentq


def to_continuous(rate, m):
    """Annual rate compounded m times/year -> continuous (Hull eq. 4.3)."""
    return m * math.log(1.0 + rate / m)


def from_continuous(rate, m):
    """Continuous rate -> annual rate compounded m times/year (Hull eq. 4.4)."""
    return m * (math.exp(rate / m) - 1.0)


def bond_price(times, cashflows, zero_rates):
    """PV of cashflows under continuous zero rates (scalar or per-time array)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    zero_rates = np.broadcast_to(np.asarray(zero_rates, dtype=float), times.shape)
    return float(np.sum(cashflows * np.exp(-zero_rates * times)))


def bond_yield(times, cashflows, price):
    """Continuous-compounding YTM (Hull eq. 4.7) via brentq."""
    return brentq(lambda y: bond_price(times, cashflows, y) - price, -0.5, 5.0)


def macaulay_duration(times, cashflows, y):
    """Macaulay duration with continuous yield (Hull eq. 4.8)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    pv = cashflows * np.exp(-y * times)
    return float(np.dot(times, pv) / pv.sum())


def convexity(times, cashflows, y):
    """Convexity with continuous yield (Hull eq. 4.14)."""
    times = np.asarray(times, dtype=float)
    cashflows = np.asarray(cashflows, dtype=float)
    pv = cashflows * np.exp(-y * times)
    return float(np.dot(times**2, pv) / pv.sum())


def forward_rate(r1, t1, r2, t2):
    """Forward rate for (t1, t2) from continuous zeros (Hull eq. 4.5)."""
    return (r2 * t2 - r1 * t1) / (t2 - t1)


def fra_value(notional, rate_fixed, rate_forward, t1, t2, r2):
    """FRA value to the fixed-rate receiver (continuous rates, Hull §4.9)."""
    return notional * (rate_fixed - rate_forward) * (t2 - t1) * math.exp(-r2 * t2)


def zero_interp(t, times, rates):
    """Linear interpolation on a zero curve with flat extrapolation."""
    return float(np.interp(t, times, rates))


def bootstrap_zero_curve(instruments):
    """Bootstrap continuous zero rates from bond prices (Hull §4.7, Table 4.3).

    instruments: iterable of (maturity_years, annual_coupon, price) on face
    100 with SEMIANNUAL coupons (annual_coupon=0 -> zero-coupon), processed
    in increasing maturity. Coupon dates of later bonds must be covered by
    earlier maturities (interpolated). Returns (times, zero_rates) lists.
    """
    times, zeros = [], []
    for maturity, annual_coupon, price in sorted(instruments):
        coupon = annual_coupon / 2.0
        cf_times = np.arange(maturity, 0.0, -0.5)[::-1]  # ..., maturity
        pv_known = sum(
            coupon * math.exp(-zero_interp(t, times, zeros) * t) for t in cf_times[:-1]
        )
        final_cf = 100.0 + coupon
        rate = -math.log((price - pv_known) / final_cf) / maturity
        times.append(float(maturity))
        zeros.append(rate)
    return times, zeros
```

- [ ] **Step 4: Run tests to verify they pass**

`uv run --no-sync pytest johnhull/hullkit/tests/test_rates.py -v` → 6 passed.
Full suite → 45 passed. Ruff check + format → clean.

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/rates.py johnhull/hullkit/tests/test_rates.py
git commit -m "feat(hullkit): interest-rate and bond utilities with Hull Ch.4 table tests"
```

---

### Task 2: build script — intro + Ch.2 + Ch.3 + Ch.4 (cells 00–18)

**Files:**
- Create: `johnhull/volumes/04_futures_forwards_rates/build_futures_rates_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–18** (copy `md()`/`code()` helpers + assembly footer from `volumes/03_greeks/build_greeks_notebook.py` verbatim; docstring title `build_futures_rates_notebook.py`; output `futures_rates.ipynb`)

````python
# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# 先物・フォワード・金利編（Hull 11e Ch.2–6）

`johnhull/volumes` シリーズ第4冊。デリバティブの土台となる現物・先物・金利を扱います：

- **Ch.2 先物市場の仕組み** — 日次値洗い・証拠金・CCP
- **Ch.3 先物によるヘッジ** — ベーシスリスク、最小分散ヘッジ比率、ベータヘッジ
- **Ch.4 金利**（中核）— 複利変換、ゼロカーブ bootstrap、FRA、デュレーション（`hullkit.rates` を実装）
- **Ch.5 フォワード・先物価格の決定** — コストオブキャリー
- **Ch.6 金利先物** — デイカウント、CTD、デュレーションヘッジ

> 共通関数は `hullkit`（rates / mc / nbplot）から import""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display

from hullkit import nbplot, rates

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.2 futures markets
# ===========================================================================

# Cell 03: mechanics digest
cells.append(
    md(r"""## 1. 先物市場の仕組み（Ch.2 ダイジェスト）

- 取引所で標準化（原資産・サイズ・受渡月）。ほとんどは受渡し前に**反対売買で決済**
- **日次値洗い（marking to market）**: 毎日清算価格で損益を証拠金口座に反映。
  残高が**維持証拠金**を下回ると**マージンコール**（当初証拠金水準まで補充）
- クリアリングハウス/CCP が全取引の相手方となり信用リスクを吸収
- 満期接近で先物価格はスポットに収束（乖離は裁定で消える）

| | フォワード | 先物 |
|---|---|---|
| 取引 | OTC・相対 | 取引所・標準化 |
| 決済 | 満期一括 | 日次値洗い |
| 信用リスク | 相手方 | CCP が吸収 |""")
)

# Cell 04: margin account simulation
cells.append(
    code(r"""# --- 証拠金口座の日次決済シミュレーション（Hull Table 2.1 形式） ---
# 金先物 2枚 × 100オンス、当初証拠金 $6,000/枚、維持証拠金 $4,500/枚
N_OZ = 200
F0_M, INIT_M, MAINT_M = 1250.0, 12_000.0, 9_000.0
rng_m = np.random.default_rng(21)
moves = np.round(rng_m.normal(0.0, 9.0, 10), 1)
futures_path = F0_M + np.cumsum(moves)

rows, balance, total_calls = [], INIT_M, 0.0
prev = F0_M
for day, f in enumerate(futures_path, start=1):
    gain = (f - prev) * N_OZ
    balance += gain
    call = 0.0
    if balance < MAINT_M:
        call = INIT_M - balance
        balance = INIT_M
        total_calls += call
    rows.append({"日": day, "先物価格": round(f, 1), "日次損益": round(gain, 0),
                 "口座残高": round(balance, 0), "マージンコール": round(call, 0)})
    prev = f
df_margin = pd.DataFrame(rows)
display(df_margin)
total_gain = (futures_path[-1] - F0_M) * N_OZ
print(f"累積損益 = (F_最終 − F_0) × {N_OZ} = {total_gain:,.0f}"
      f" ／ 日次損益の合計 = {df_margin['日次損益'].sum():,.0f}（一致が値洗いの本質）")
print(f"マージンコール総額 = {total_calls:,.0f}")""")
)

# ===========================================================================
# Section 2: Ch.3 hedging with futures
# ===========================================================================

# Cell 05: hedge basics
cells.append(
    md(r"""## 2. 先物によるヘッジとベーシスリスク（§3.1–3.3）

- **ショートヘッジ**: 将来売る資産を持つ側（実現価格 $= F_1 + b_2$）
- **ロングヘッジ**: 将来買う予定の側
- **ベーシス** $b = S - F$。満期前決済やクロスヘッジ（対象資産 ≠ 先物原資産）では
  $b_2$ が不確実 — これが**ベーシスリスク**""")
)

# Cell 06: optimal hedge ratio
cells.append(
    code(r"""# --- 最小分散ヘッジ比率（ジェット燃料を灯油先物でクロスヘッジ、Hull §3.4） ---
RHO_H, SIG_S, SIG_F = 0.928, 0.0263, 0.0313
h_star = RHO_H * SIG_S / SIG_F  # eq (3.1)

rng_h = np.random.default_rng(31)
z1 = rng_h.standard_normal(5000)
z2 = rng_h.standard_normal(5000)
d_f = SIG_F * z1
d_s = SIG_S * (RHO_H * z1 + np.sqrt(1.0 - RHO_H**2) * z2)
h_grid = np.linspace(0.0, 1.6, 81)
var_h = [float(np.var(d_s - h * d_f)) for h in h_grid]
h_hat = float(np.polyfit(d_f, d_s, 1)[0])  # ΔS を ΔF に回帰 → 傾き ≈ h*

fig1, ax1 = plt.subplots(figsize=(7.5, 4))
fig1.canvas.header_visible = False
ax1.plot(h_grid, var_h, lw=2)
ax1.axvline(h_star, color="crimson", ls="--", lw=1.5, label=f"h* = ρσ_S/σ_F = {h_star:.3f}")
ax1.set_xlabel("ヘッジ比率 h")
ax1.set_ylabel("ヘッジ後ポジションの分散")
ax1.set_title("分散は h = h* で最小（ヘッジ効果 = ρ² = "
              f"{RHO_H**2:.3f}）")
ax1.legend()
display(fig1.canvas)
print(f"回帰推定 ĥ = {h_hat:.4f}（理論値 {h_star:.4f}）")
n_star = h_star * 2_000_000 / 42_000
print(f"ジェット燃料200万ガロンを 42,000ガロン/枚 の灯油先物で → N* = {n_star:.2f} ≈ {round(n_star)} 枚")""")
)

# Cell 07: beta hedging md
cells.append(
    md(r"""### 株価指数先物によるベータヘッジ（§3.5）

$$N^* = \beta\,\frac{V_A}{V_F} \quad \text{(eq 3.5)}, \qquad
\beta \to \beta^*: \; (\beta - \beta^*)\frac{V_A}{V_F}\ \text{枚ショート}$$

ヘッジで消えるのは**システマティックリスク**のみ。β を 0 にすればリスクフリー相当、
β を任意の目標値に調整することもできます。""")
)

# Cell 08: beta hedge demo
cells.append(
    code(r"""V_A, F_IDX, MULT, BETA = 5_050_000.0, 1_010.0, 250.0, 1.5
V_F = F_IDX * MULT
n_beta = BETA * V_A / V_F
print(f"ポートフォリオ ${V_A:,.0f}（β={BETA}）、先物1枚 = {F_IDX:.0f}×{MULT:.0f} = ${V_F:,.0f}")
print(f"完全ヘッジ: N* = β·V_A/V_F = {n_beta:.1f} 枚ショート\n")
rows = []
for b_target in (0.0, 0.75, 1.5, 2.0):
    k = (BETA - b_target) * V_A / V_F
    rows.append({"目標β*": b_target, "取引枚数": round(abs(k), 1),
                 "方向": "ショート" if k > 0 else ("ロング" if k < 0 else "—")})
display(pd.DataFrame(rows))""")
)

# ===========================================================================
# Section 3: Ch.4 interest rates (centerpiece)
# ===========================================================================

# Cell 09: compounding
cells.append(
    md(r"""## 3. 複利の単位（§4.2）

金利は複利頻度が決まって初めて意味を持ちます。本書（とこのシリーズ）の標準は**連続複利**：

$$R_c = m \ln\!\left(1 + \frac{R_m}{m}\right), \qquad R_m = m\left(e^{R_c/m} - 1\right) \quad \text{(4.3), (4.4)}$$""")
)

# Cell 10: conversion table
cells.append(
    code(r"""# 年率10%を各複利頻度から連続複利へ（hullkit.rates）
rows = []
for m, label in [(1, "年1回"), (2, "半年"), (4, "四半期"), (12, "月次"), (365, "日次")]:
    rc = rates.to_continuous(0.10, m)
    rows.append({"複利頻度": label, "m": m, "連続複利換算": f"{rc:.5%}",
                 "逆変換チェック": f"{rates.from_continuous(rc, m):.5%}"})
display(pd.DataFrame(rows))
print(f"半年複利10% → 連続複利 {rates.to_continuous(0.10, 2):.4%}（Hull: 9.758%）")""")
)

# Cell 11: bonds md
cells.append(
    md(r"""## 4. ゼロレート・債券価格・YTM・パーイールド（§4.4–4.6）

- **ゼロレート** $R(t)$: 満期 $t$ の一括払い投資に適用される金利
- **債券価格**: 各キャッシュフローを対応するゼロレートで個別に割引いた合計
- **YTM**: 全キャッシュフローを単一レート $y$ で割引いて価格に一致させる解
- **パーイールド**: 価格が額面に等しくなるクーポンレート""")
)

# Cell 12: Table 4.2 bond
cells.append(
    code(r"""# Hull Table 4.2: ゼロレート 5.0/5.8/6.4/6.8%（連続複利）、2年 6% 半年払い債
times_b = [0.5, 1.0, 1.5, 2.0]
cfs_b = [3.0, 3.0, 3.0, 103.0]
zeros_b = [0.050, 0.058, 0.064, 0.068]
price_b = rates.bond_price(times_b, cfs_b, zeros_b)
ytm_b = rates.bond_yield(times_b, cfs_b, price_b)
print(f"債券価格 = {price_b:.3f}（Hull: 98.39）")
print(f"YTM（連続複利）= {ytm_b:.4%}（Hull: 6.76%）")

# パーイールド: c·A/m + 100·d = 100 を解く（m=2）
d_factor = np.exp(-zeros_b[-1] * times_b[-1])
a_factor = sum(np.exp(-z * t) for z, t in zip(zeros_b, times_b))
par_c = (100.0 - 100.0 * d_factor) * 2.0 / a_factor
print(f"パーイールド = {par_c:.3f}%（年率、半年複利）")""")
)

# Cell 13: bootstrap md
cells.append(
    md(r"""## 5. ブートストラップ法によるゼロカーブ構築（§4.7）

市場で観測できるのは債券**価格**。短期のゼロクーポン債から順に、
クーポン債の既知キャッシュフローを既決ゼロレートで割引き、
残った最終キャッシュフローから未知のゼロレートを逐次的に解きます（Table 4.3）。""")
)

# Cell 14: bootstrap demo
cells.append(
    code(r"""# Hull Table 4.3 の5銘柄から bootstrap（hullkit.rates.bootstrap_zero_curve）
instruments = [
    (0.25, 0.0, 99.6),
    (0.50, 0.0, 99.0),
    (1.00, 0.0, 97.8),
    (1.50, 4.0, 102.5),
    (2.00, 5.0, 105.0),
]
bt_times, bt_zeros = rates.bootstrap_zero_curve(instruments)
df_bt = pd.DataFrame({"満期": bt_times, "ゼロレート": [f"{z:.4%}" for z in bt_zeros]})
display(df_bt)
print("Hull: 1.603% / 2.010% / 2.225% / 2.284% / 2.416%")

fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
t_fine = np.linspace(0.25, 2.0, 200)
ax2.plot(t_fine, [rates.zero_interp(t, bt_times, bt_zeros) * 100 for t in t_fine],
         lw=1.5, label="線形補間")
ax2.plot(bt_times, np.array(bt_zeros) * 100, "o", ms=7, label="bootstrap 点")
ax2.set_xlabel("満期（年）")
ax2.set_ylabel("ゼロレート（%）")
ax2.set_title("Table 4.3 から構築したゼロカーブ")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 15: forward/FRA md
cells.append(
    md(r"""## 6. フォワードレートと FRA（§4.8–4.9）

$$R_F = \frac{R_2 T_2 - R_1 T_1}{T_2 - T_1} \quad \text{(4.5)}$$

**FRA** は将来期間 $[T_1, T_2]$ の金利を固定する OTC 契約。固定受取側の価値：

$$V_{\text{FRA}} = L\,(R_K - R_F)\,(T_2 - T_1)\,e^{-R_2 T_2}$$

順イールドではフォワードレートはゼロレートの上に位置します。""")
)

# Cell 16: forward/FRA demo
cells.append(
    code(r"""# bootstrap カーブからフォワードレートを計算
rows = []
for (t1, z1), (t2, z2) in zip(list(zip(bt_times, bt_zeros))[:-1],
                              list(zip(bt_times, bt_zeros))[1:]):
    rows.append({"期間": f"{t1}→{t2}年", "フォワードレート": f"{rates.forward_rate(z1, t1, z2, t2):.4%}"})
display(pd.DataFrame(rows))

rf_simple = rates.forward_rate(0.03, 1.0, 0.04, 2.0)
print(f"例: 1年3% / 2年4% → 1→2年フォワード = {rf_simple:.2%}（eq 4.5）")
fra = rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040)
print(f"FRA（元本1億、固定5.8%受取、フォワード5.0%、1.5→2.0年、R2=4%）= {fra:,.0f}（Hull: ≈369,200）")""")
)

# Cell 17: duration md
cells.append(
    md(r"""## 7. デュレーションとコンベクシティ（§4.10–4.11）

$$D = \frac{\sum_i t_i c_i e^{-y t_i}}{B}, \qquad \frac{\Delta B}{B} \approx -D\,\Delta y \quad \text{(4.8), (4.12)}$$

$$\frac{\Delta B}{B} \approx -D\,\Delta y + \tfrac{1}{2} C (\Delta y)^2 \quad \text{(4.14)}$$

線形近似は**平行シフト・小変化**が前提。大きな変化はコンベクシティで2次補正します
（プレーン債券は $C>0$ → 「小さく損・大きく得」のバイアス）。""")
)

# Cell 18: duration demo + chart
cells.append(
    code(r"""# Hull Table 4.6: 3年・10%クーポン（半年5）・y=12%連続複利
times_d = np.arange(0.5, 3.01, 0.5)
cfs_d = [5.0] * 5 + [105.0]
y_d = 0.12
b_d = rates.bond_price(times_d, cfs_d, y_d)
dur_d = rates.macaulay_duration(times_d, cfs_d, y_d)
conv_d = rates.convexity(times_d, cfs_d, y_d)
print(f"B = {b_d:.3f}（Hull: 94.213） D = {dur_d:.3f}（Hull: 2.653） C = {conv_d:.3f}")
print(f"Δy=+10bp: 実際 {rates.bond_price(times_d, cfs_d, y_d + 0.001) - b_d:+.3f}"
      f" ／ −BDΔy = {-b_d * dur_d * 0.001:+.3f}")

dy_grid = np.linspace(-0.03, 0.03, 121)
actual = np.array([rates.bond_price(times_d, cfs_d, y_d + dy) - b_d for dy in dy_grid])
lin = -b_d * dur_d * dy_grid
quad = lin + 0.5 * conv_d * b_d * dy_grid**2

fig3, ax3 = plt.subplots(figsize=(8, 4.5))
fig3.canvas.header_visible = False
ax3.plot(dy_grid * 100, actual, lw=2, label="実際の価格変化")
ax3.plot(dy_grid * 100, lin, ls="--", lw=1.5, label="−BDΔy（線形）")
ax3.plot(dy_grid * 100, quad, ls=":", lw=2, label="＋½CB(Δy)²（2次）")
ax3.set_xlabel("Δy（%）")
ax3.set_ylabel("ΔB")
ax3.set_title("デュレーション近似とコンベクシティ補正")
ax3.legend()
display(fig3.canvas)""")
)
````

- [ ] **Step 2: Build and validate**

Run: `cd johnhull/volumes/04_futures_forwards_rates && uv run --no-sync python build_futures_rates_notebook.py`
Expected: `Total cells: 19`. nbformat validate → `19 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/04_futures_forwards_rates
git commit -m "feat(johnhull): 04 build script with futures/hedging/rates cells"
```

---

### Task 3: build script — Ch.5 + Ch.6 + closing (cells 19–33)

**Files:**
- Modify: `johnhull/volumes/04_futures_forwards_rates/build_futures_rates_notebook.py`

- [ ] **Step 1: Insert cells 19–33 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
# ===========================================================================
# Section 4: Ch.5 forward and futures prices
# ===========================================================================

# Cell 19: cost of carry md
cells.append(
    md(r"""## 8. フォワード価格＝コストオブキャリー（§5.4–5.7, §5.10）

| 資産 | フォワード価格 | キャリー c |
|---|---|---|
| 無収入 | $F_0 = S_0 e^{rT}$ (5.1) | $r$ |
| 既知収入 $I$（PV） | $F_0 = (S_0 - I)e^{rT}$ (5.2) | — |
| 連続利回り $q$ | $F_0 = S_0 e^{(r-q)T}$ (5.3) | $r-q$ |
| 外貨（金利平価） | $F_0 = S_0 e^{(r-r_f)T}$ (5.9) | $r-r_f$ |
| 保管コスト $u$ | $F_0 = S_0 e^{(r+u)T}$ (5.12) | $r+u$ |

裁定論法: $F_0$ が高すぎれば「借りて買って先渡し売り」、低すぎれば逆。""")
)

# Cell 20: forward price examples
cells.append(
    code(r"""print(f"無収入株: S=40, r=5%, T=3ヶ月 → F = 40e^(0.05×0.25) = "
      f"{40.0 * np.exp(0.05 * 0.25):.4f}（Hull: 40.50）")
s_i, pv_i, r_5, t_5 = 900.0, 40.0, 0.04, 0.75
print(f"既知収入（クーポン債）: S={s_i:.0f}, I(PV)={pv_i:.0f}, r=4%, T=9ヶ月 → "
      f"F = (900−40)e^(0.03) = {(s_i - pv_i) * np.exp(r_5 * t_5):.2f}")
print(f"株価指数: S=1300, q=1%, r=5%, T=0.25 → F = {1300.0 * np.exp((0.05 - 0.01) * 0.25):.2f}")
print(f"外貨: S=0.80, r=6%, r_f=2%, T=2 → F = {0.80 * np.exp((0.06 - 0.02) * 2.0):.4f}（金利平価）")""")
)

# Cell 21: forward value md
cells.append(
    md(r"""### フォワード契約の価値（§5.7）

締結時のデリバリー価格 $K = F_0$ で価値ゼロ。その後 $F_0$ が動くと：

$$f = (F_0 - K)e^{-rT} \quad \text{(5.4)}$$

無収入資産なら展開形 $f = S_0 - Ke^{-rT}$ (5.5) と恒等的に一致します。""")
)

# Cell 22: forward valuation demo
cells.append(
    code(r"""# 締結: S=25, r=10%, 6ヶ月 → K = F0
s_v, r_v = 25.0, 0.10
k_v = s_v * np.exp(r_v * 0.5)
print(f"締結時: K = F0 = {k_v:.4f}, f = 0")

# 3ヶ月後: S=24, 残存 0.25年
s_now, tau_v = 24.0, 0.25
f_now = s_now * np.exp(r_v * tau_v)
val_general = (f_now - k_v) * np.exp(-r_v * tau_v)  # eq (5.4)
val_direct = s_now - k_v * np.exp(-r_v * tau_v)     # eq (5.5)
print(f"3ヶ月後: F = {f_now:.4f}, f(5.4式) = {val_general:+.4f}, "
      f"f(5.5式) = {val_direct:+.4f}, 差 = {abs(val_general - val_direct):.2e}（恒等）")""")
)

# Cell 23: consumption assets md
cells.append(
    md(r"""### 消費資産・コンビニエンスイールド・先物と期待スポット（§5.11, §5.14）

- 消費資産は売り裁定が効かず $F_0 \le (S_0+U)e^{rT}$ — 等号回復のための
  **コンビニエンスイールド** $y$: $F_0 = S_0 e^{(r+u-y)T}$
- $y > r+u$ なら先物カーブは右下がり（**バックワーデーション**）、逆なら**コンタンゴ**
- 期待将来スポットとの関係: $F_0 = E(S_T)e^{(r-k)T}$ (5.20) —
  正の系統的リスク（$k>r$）なら $F_0 < E(S_T)$（normal backwardation）""")
)

# Cell 24: interactive carry curve
cells.append(
    code(r"""# --- 先物タームストラクチャー F0(T) = S e^{(r+u−q−y)T}（インタラクティブ） ---
fig4, ax4 = plt.subplots(figsize=(8, 4.5))
fig4.canvas.header_visible = False
S_TS = 100.0
T_TS = np.linspace(0.0, 2.0, 100)
r_ts_sl = widgets.FloatSlider(value=0.05, min=0.0, max=0.10, step=0.005, description="r")
u_ts_sl = widgets.FloatSlider(value=0.00, min=0.0, max=0.05, step=0.005, description="u 保管")
qy_ts_sl = widgets.FloatSlider(value=0.00, min=0.0, max=0.15, step=0.005, description="q+y 利回り")


def _upd_carry(change=None):
    ax4.clear()
    c_net = r_ts_sl.value + u_ts_sl.value - qy_ts_sl.value
    f_curve = S_TS * np.exp(c_net * T_TS)
    ax4.plot(T_TS, f_curve, lw=2)
    ax4.axhline(S_TS, color="0.7", ls=":", lw=1, label="スポット S")
    state = "コンタンゴ（右上がり）" if c_net > 0 else ("バックワーデーション（右下がり）" if c_net < 0 else "フラット")
    ax4.set_title(f"純キャリー c−y = {c_net:+.3f} → {state}")
    ax4.set_xlabel("満期 T（年）")
    ax4.set_ylabel("先物価格 F0(T)")
    ax4.legend()
    fig4.canvas.draw_idle()


for w in (r_ts_sl, u_ts_sl, qy_ts_sl):
    w.observe(_upd_carry, "value")
_upd_carry()
display(widgets.HBox([r_ts_sl, u_ts_sl, qy_ts_sl]), fig4.canvas)""")
)

# ===========================================================================
# Section 5: Ch.6 interest rate futures
# ===========================================================================

# Cell 25: day count md
cells.append(
    md(r"""## 9. デイカウントとクリーン/ダーティ価格（§6.1）

$$\text{現金価格（ダーティ）} = \text{クォート価格（クリーン）} + \text{経過利息}$$

| 慣行 | 用途 |
|---|---|
| actual/actual | 米国債 |
| 30/360 | 米国社債・地方債 |
| actual/360 | マネーマーケット |

同じ債券・同じ日付でも、慣行によって経過利息が変わります。""")
)

# Cell 26: accrued interest demo
cells.append(
    code(r"""# 半年クーポン 5.5（年11%）、クーポン期間181日（実日数）のうち54日経過のケース
coupon_semi = 5.5
ai_actual = 54.0 / 181.0 * coupon_semi          # actual/actual（国債方式）
ai_30_360 = 52.0 / 180.0 * coupon_semi          # 30/360 では同じ期間が 52/180 日と数えられる例
print(f"actual/actual: 54/181 × {coupon_semi} = {ai_actual:.4f}")
print(f"30/360       : 52/180 × {coupon_semi} = {ai_30_360:.4f}")
print(f"差 = {abs(ai_actual - ai_30_360):.4f} — 慣行の取り違えはそのまま価格誤差になる")""")
)

# Cell 27: T-bond futures md
cells.append(
    md(r"""## 10. T-bond 先物: コンバージョンファクターと CTD（§6.2）

ショート側は複数の**デリバラブル銘柄**から選んで受け渡せます：

$$\text{受取額} = \text{決済価格} \times \text{CF} + \text{経過利息}$$

CF は「6%利回りで評価した額面あたり価格」。ショートは

$$\text{クォート価格} - \text{決済価格} \times \text{CF}$$

を最小にする**最安受渡銘柄（CTD）**を選びます。""")
)

# Cell 28: CTD selection
cells.append(
    code(r"""# CTD 選択（決済価格 93.25、3銘柄の例）
df_ctd = pd.DataFrame({
    "債券": ["A", "B", "C"],
    "クォート価格": [99.50, 143.50, 119.75],
    "CF": [1.0382, 1.5188, 1.2615],
})
settle_px = 93.25
df_ctd["受渡しコスト"] = (df_ctd["クォート価格"] - settle_px * df_ctd["CF"]).round(3)
display(df_ctd)
ctd = df_ctd.loc[df_ctd["受渡しコスト"].idxmin(), "債券"]
print(f"CTD = 債券{ctd}（コスト最小）。利回り>6% では低クーポン・長期債が CTD になりやすい")""")
)

# Cell 29: eurodollar + duration hedge md
cells.append(
    md(r"""## 11. 金利先物によるデュレーションヘッジ（§6.3–6.4）

- **ユーロドル/SOFR 先物**: クォート 0.01 変化 = 1枚 $25。先物レート→フォワードレートには
  **コンベクシティ調整** $\text{forward} = \text{futures} - \tfrac{1}{2}\sigma^2 t_1 t_2$ が必要
- **デュレーションベースのヘッジ枚数**:

$$N^* = \frac{P\,D_P}{V_F\,D_F}$$

イールドカーブの**平行シフト**を仮定した近似です。""")
)

# Cell 30: convexity adj chart + duration hedge
cells.append(
    code(r"""fig5, ax5 = plt.subplots(figsize=(7.5, 4))
fig5.canvas.header_visible = False
sig_r = 0.012
t1_grid = np.arange(1.0, 10.01, 0.5)
adj_bp = 0.5 * sig_r**2 * t1_grid * (t1_grid + 0.25) * 1e4
ax5.plot(t1_grid, adj_bp, lw=2)
ax5.set_xlabel("先物満期 t1（年）")
ax5.set_ylabel("コンベクシティ調整（bp）")
ax5.set_title(f"σ={sig_r:.1%}: 調整は満期の2乗オーダーで拡大（先物レート > フォワードレート）")
display(fig5.canvas)

p_dur, d_p, v_f, d_f = 10_000_000.0, 6.8, 93_062.50, 9.2
n_dur = p_dur * d_p / (v_f * d_f)
print(f"ポートフォリオ $10M（D_P=6.8年）を T-bond 先物（V_F=$93,062.50, D_F=9.2年）でヘッジ:")
print(f"N* = P·D_P/(V_F·D_F) = {n_dur:.2f} ≈ {round(n_dur)} 枚ショート")""")
)

# ===========================================================================
# Section 6: verification / exercises / summary
# ===========================================================================

# Cell 31: assertion cell
cells.append(
    code(r"""# --- 教科書例題との突合せ（hullkit/tests/test_rates.py にも同等の検証あり） ---
checks = []
checks.append(("半年複利10%→連続 9.758%", rates.to_continuous(0.10, 2), 0.097580, 1e-5))
checks.append(("Table 4.2 価格 98.39", rates.bond_price(times_b, cfs_b, zeros_b), 98.385, 5e-3))
checks.append(("Table 4.2 YTM 6.76%", rates.bond_yield(times_b, cfs_b, price_b), 0.0676, 2e-4))
for (t_chk, z_chk), want in zip(zip(bt_times, bt_zeros),
                                [0.016032, 0.020101, 0.022245, 0.022845, 0.024162]):
    checks.append((f"bootstrap {t_chk}年", z_chk, want, 5e-5))
checks.append(("フォワード 5%", rates.forward_rate(0.03, 1.0, 0.04, 2.0), 0.05, 1e-12))
checks.append(("FRA 369,247", rates.fra_value(100e6, 0.058, 0.050, 1.5, 2.0, 0.040), 369_246.5, 1.0))
checks.append(("Table 4.6 B=94.213", b_d, 94.213, 5e-3))
checks.append(("Table 4.6 D=2.653", dur_d, 2.653, 2e-3))
checks.append(("F=40.50（S=40, 3ヶ月）", 40.0 * np.exp(0.05 * 0.25), 40.5031, 1e-3))
checks.append(("フォワード価値の恒等 (5.4)≡(5.5)", val_general, val_direct, 1e-12))
checks.append(("h* = 0.7798", h_star, 0.77976, 1e-4))
checks.append(("ベータヘッジ N*=30", n_beta, 30.0, 1e-9))
checks.append(("デュレーションヘッジ 79.42", n_dur, 79.42, 0.01))
checks.append(("値洗い不変量", float(df_margin["日次損益"].sum()),
               float((futures_path[-1] - F0_M) * N_OZ), 1e-6))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 32: exercises
cells.append(
    md(r"""## 12. 練習問題

**Q1.** 年2回複利で8%の金利。連続複利では？　月次複利では？

<details><summary>解答</summary>

連続: 2ln(1.04) = 7.844%。月次: 12(e^{0.07844/12}−1) = 7.870%。
</details>

**Q2.** ゼロレートが全満期 6%（連続）のとき、2年後に1.5年債を受け渡すフォワード価格はどう求める？

<details><summary>解答</summary>

債券のスポット価格を計算し、受渡しまでのクーポン PV を引いて $F_0=(S_0−I)e^{rT}$（eq 5.2）。
</details>

**Q3.** D=5.2年・$20M のポートフォリオを D_F=8.0年・1枚 $95,000 の先物でヘッジするには？

<details><summary>解答</summary>

N* = 20,000,000×5.2/(95,000×8.0) = 136.8 ≈ 137枚ショート。
</details>""")
)

# Cell 33: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| 値洗い | 日次損益の合計 = (F_T−F_0)×数量。マージンコールで信用リスクを抑える |
| ヘッジ比率 | h* = ρσ_S/σ_F（回帰の傾き）。効果は ρ²。指数先物は β·V_A/V_F |
| 複利変換 | 連続複利が解析の標準。R_c = m·ln(1+R_m/m) |
| bootstrap | 短期から逐次、既知 CF を割引いて残りを解く |
| デュレーション | ΔB ≈ −BDΔy（平行シフト前提）。大変化はコンベクシティ補正 |
| キャリー | F_0 = S e^{(r+u−q−y)T}。符号がコンタンゴ/バックワーデーションを決める |
| CTD | ショートはクォート − 決済×CF を最小化する銘柄を選ぶ |

**次へ**: `volumes/05_vol_smile_estimation`（Ch.20, 23）または `volumes/07_swaps`（Ch.7, 34 — `rates.py` を活用）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)
````

- [ ] **Step 2: Rebuild and validate**

`Total cells: 34`; nbformat validate → `34 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/04_futures_forwards_rates
git commit -m "feat(johnhull): 04 forward-pricing and IR-futures cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/04_futures_forwards_rates/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 4 → done)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output futures_rates_executed.ipynb`). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc** against `/tmp/futures_rates_executed.ipynb`.

- [ ] **Step 3: Tests + lint:** hullkit suite → 45 passed; ruff johnhull clean; workspace minus gto (explicit paths as in volume 03) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/04_futures_forwards_rates/PROGRESS.md`**

```markdown
# 04_futures_forwards_rates — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `futures_rates.ipynb` (34 cells) generated by `build_futures_rates_notebook.py`
- Coverage: Hull 11e Ch.2 (margining), Ch.3 (hedge ratios), Ch.4 (rates —
  centerpiece), Ch.5 (cost of carry), Ch.6 (IR futures)
- hullkit addition: `rates.py` (compounding, bond price/YTM, bootstrap,
  forward/FRA, duration/convexity — 6 tests; suite 45). Dependency for
  volumes 07/11.
- Verified: headless nbconvert, textbook assertion cell (Tables 4.2/4.3/4.6
  etc.), hullkit pytest, ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_futures_rates_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-04 Ch.2 / 05-08 Ch.3 / 09-18 Ch.4 /
  19-24 Ch.5 / 25-30 Ch.6 / 31 verification / 32 exercises / 33 summary
- Eurodollar-futures bootstrap (eq 6.2) and stack-and-roll: markdown only
- Day counts use fractional-period approximation (no calendar arithmetic)
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 4 → done; also append `rates` to the shared-module list line.**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/04_futures_forwards_rates/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 04_futures_forwards_rates complete"
```

- [ ] **Step 7: Report** with quoted outputs; flag widget check.
