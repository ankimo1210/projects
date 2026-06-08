# johnhull 09_credit_xva Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.credit` (hazard rates, CDS, Merton, copula, credit VaR — TDD) and the 27-cell `volumes/09_credit_xva/credit_xva.ipynb` covering Hull 11e Ch.24, 25, 9.

**Architecture:** As volumes 01–08. Hull Example 24.3 (Merton) and constant-hazard CDS pins anchor the tests.

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-09-credit-xva-design.md`

**Reference values** (hand-verified by running the formulas):

| Quantity | Value |
|---|---|
| Merton Ex 24.3 (E0=3, σE=0.8, D=10, r=5%, T=1) | V0=12.3954, σV=0.21230, Q=0.12697 (Hull 12.7%) |
| cds_spread(λ=0.02, R=0.4, r=5%, 5y, quarterly) | 0.012075 (≈ λ(1−R)=0.012) |
| hazard_from_spread(0.012, 0.4) | 0.02 |

Implementer notes: as previous volumes (ruff scope, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`, stage only specified files, report tolerance failures).

---

### Task 1: hullkit.credit (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_credit.py`
- Create: `johnhull/hullkit/src/hullkit/credit.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_credit.py`:

```python
"""Tests for hullkit.credit against Hull 11e Ch.24/25 examples."""

import math

import pytest
from scipy.stats import norm

from hullkit import credit


def test_survival_and_default_constant_hazard():
    assert credit.survival_prob(2.0, 0.02) == pytest.approx(math.exp(-0.04), abs=1e-12)
    assert credit.default_prob(2.0, 0.02) == pytest.approx(1.0 - math.exp(-0.04), abs=1e-12)
    assert credit.survival_prob(0.0, 0.05) == pytest.approx(1.0)


def test_hazard_from_spread():
    assert credit.hazard_from_spread(0.012, 0.4) == pytest.approx(0.02, abs=1e-12)


def test_cds_spread_near_lambda_times_loss():
    s = credit.cds_spread(0.02, 0.4, 0.05, 5.0, freq=4)
    assert s == pytest.approx(0.012075, abs=5e-5)
    assert 0.0119 < s < 0.0121  # close to lambda(1-R)=0.012


def test_merton_example_24_3():
    v0, sig_v, q = credit.merton_default_prob(3.0, 0.80, 10.0, 0.05, 1.0)
    assert v0 == pytest.approx(12.3954, abs=2e-3)
    assert sig_v == pytest.approx(0.21230, abs=5e-4)
    assert q == pytest.approx(0.12697, abs=5e-4)  # Hull 12.7%


def test_gaussian_copula_conditional_monotonic():
    q = 0.05
    a = 0.5
    pd_low_f = credit.gaussian_copula_conditional(q, a, -2.0)  # bad systemic state
    pd_high_f = credit.gaussian_copula_conditional(q, a, 2.0)  # good systemic state
    assert pd_low_f > q > pd_high_f
    assert credit.gaussian_copula_conditional(q, 0.0, 5.0) == pytest.approx(q, abs=1e-12)


def test_vasicek_credit_var():
    q, rho = 0.02, 0.1
    v999 = credit.vasicek_credit_var(q, rho, 0.999)
    assert v999 > q  # tail loss exceeds the mean PD
    # monotone in confidence and correlation
    assert credit.vasicek_credit_var(q, rho, 0.99) < v999
    assert credit.vasicek_credit_var(q, 0.3, 0.999) > v999
    # sanity vs closed form
    expected = norm.cdf(
        (norm.ppf(q) + math.sqrt(rho) * norm.ppf(0.999)) / math.sqrt(1.0 - rho)
    )
    assert v999 == pytest.approx(expected, abs=1e-12)
```

- [ ] **Step 2: Run to verify failure** (ImportError)

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/credit.py`**

```python
"""Credit risk and credit derivatives (Hull 11e, Ch.24/25)."""

import math

import numpy as np
from scipy.optimize import fsolve
from scipy.stats import norm


def survival_prob(t, hazard):
    """Survival probability S(t) = exp(-lambda * t) for a constant hazard."""
    return math.exp(-hazard * t)


def default_prob(t, hazard):
    """Cumulative default probability Q(t) = 1 - S(t) (Hull eq. 24.1)."""
    return 1.0 - survival_prob(t, hazard)


def hazard_from_spread(spread, recovery):
    """Average hazard rate from a credit spread: lambda ~ s / (1 - R) (Hull eq. 24.2)."""
    return spread / (1.0 - recovery)


def cds_spread(hazard, recovery, r, maturity, freq=4):
    """Par CDS spread under a constant hazard (Hull Ch.25 discrete legs).

    Protection leg: per-period default prob (S_{i-1} - S_i) times (1 - R),
    discounted to mid-period. Premium leg: spread * survival-weighted annuity
    plus accrual on default. Returns the par spread (protection / annuity).
    """
    n = int(round(maturity * freq))
    dt = 1.0 / freq
    protection = 0.0
    annuity = 0.0
    s_prev = 1.0
    for i in range(1, n + 1):
        t = i * dt
        s = survival_prob(t, hazard)
        d_pd = s_prev - s
        df_mid = math.exp(-r * (t - 0.5 * dt))
        protection += (1.0 - recovery) * df_mid * d_pd
        annuity += math.exp(-r * t) * s * dt + df_mid * d_pd * 0.5 * dt
        s_prev = s
    return protection / annuity


def merton_default_prob(E0, sigma_E, D, r, T):
    """Merton structural model: solve for (V0, sigma_V) and risk-neutral Q.

    Equity = call on firm assets (Hull eq. 24.3); Ito link (eq. 24.4).
    Returns (V0, sigma_V, Q) with Q = N(-d2).
    """

    def equations(x):
        v0, sig_v = x
        d1 = (math.log(v0 / D) + (r + 0.5 * sig_v**2) * T) / (sig_v * math.sqrt(T))
        d2 = d1 - sig_v * math.sqrt(T)
        eq1 = v0 * norm.cdf(d1) - D * math.exp(-r * T) * norm.cdf(d2) - E0
        eq2 = norm.cdf(d1) * sig_v * v0 - sigma_E * E0
        return [eq1, eq2]

    v0, sig_v = fsolve(equations, [E0 + D, 0.2], full_output=False)
    d1 = (math.log(v0 / D) + (r + 0.5 * sig_v**2) * T) / (sig_v * math.sqrt(T))
    d2 = d1 - sig_v * math.sqrt(T)
    return float(v0), float(sig_v), float(norm.cdf(-d2))


def gaussian_copula_conditional(q, a, factor):
    """Conditional default prob given systemic factor F (Hull eq. 24.8)."""
    return float(norm.cdf((norm.ppf(q) - a * factor) / math.sqrt(1.0 - a**2)))


def vasicek_credit_var(q, rho, conf):
    """Vasicek single-factor credit-VaR loss rate (Hull eq. 24.10)."""
    return float(
        norm.cdf((norm.ppf(q) + math.sqrt(rho) * norm.ppf(conf)) / math.sqrt(1.0 - rho))
    )
```

- [ ] **Step 4: Verify** — 6 passed; full suite 81 passed; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/credit.py johnhull/hullkit/tests/test_credit.py
git commit -m "feat(hullkit): credit risk (hazard, CDS, Merton, copula, Vasicek) with Hull tests"
```

---

### Task 2: build script — intro + Ch.24 (cells 00–10)

**Files:**
- Create: `johnhull/volumes/09_credit_xva/build_credit_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–10** (helpers + footer verbatim from `volumes/08_risk_var/build_risk_notebook.py`; title `build_credit_notebook.py`; output `credit_xva.ipynb`)

````python
# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# 信用リスクと XVA（Hull 11e Ch.24, 25, 9）

`johnhull/volumes` シリーズ第9冊。デフォルトの確率と価格：

- **信用リスク（Ch.24）** — ハザードレート、Merton 構造モデル、ガウスコピュラ、信用 VaR
- **クレジット・デリバティブ（Ch.25）** — CDS、インデックス、CDO トランシェ
- **XVA（Ch.9）** — CVA / DVA / FVA / MVA / KVA

> 共通関数は `hullkit`（credit / bsm / nbplot）から import。第8冊の VaR を信用損失へ拡張""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm

from hullkit import credit, nbplot

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.24 credit risk
# ===========================================================================

# Cell 03: hazard md
cells.append(
    md(r"""## 1. ハザードレートと生存確率（Ch.24）

ハザードレート（デフォルト強度）$\lambda(t)$ は「生存している条件で次の微小期間に
デフォルトする率」。生存確率と累積デフォルト確率は：

$$S(t) = e^{-\int_0^t \lambda(u)\,du}, \qquad Q(t) = 1 - S(t) \quad \text{(24.1)}$$

定数ハザードなら $Q(T) = 1 - e^{-\lambda T}$。""")
)

# Cell 04: survival curve
cells.append(
    code(r"""# --- 生存確率と累積デフォルト確率 ---
t_grid = np.linspace(0.0, 10.0, 200)
fig1, ax1 = plt.subplots(figsize=(8, 4))
fig1.canvas.header_visible = False
for lam in (0.01, 0.03, 0.06):
    ax1.plot(t_grid, [credit.default_prob(t, lam) for t in t_grid], lw=2,
             label=f"λ={lam:.0%} → 10年Q={credit.default_prob(10.0, lam):.1%}")
ax1.set_xlabel("年数 t")
ax1.set_ylabel("累積デフォルト確率 Q(t)")
ax1.set_title("定数ハザードの累積デフォルト確率")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 05: real vs RN md
cells.append(
    md(r"""## 2. 実世界確率 vs リスク中立確率（Ch.24）

- **リスク中立確率**（CDS・債券スプレッドから逆算）は**実世界確率の 5〜10 倍**高い
- 理由: 信用リスクプレミアム、流動性、デフォルトの系統性（皆同時に困る）
- **使い分け**: デリバティブ価格付け → リスク中立 ／ 信用 VaR・資本 → 実世界

$$\bar\lambda(T) \approx \frac{s(T)}{1-R} \quad \text{(24.2)}, \qquad
s = -\frac{1}{T}\ln\frac{B^{\text{corp}}}{B^{\text{tsy}}}$$""")
)

# Cell 06: spread to hazard
cells.append(
    code(r"""# スプレッドからハザード、回収率の影響
rows = []
for s_bp in (50, 100, 200, 400):
    s = s_bp / 1e4
    for R in (0.2, 0.4, 0.6):
        lam = credit.hazard_from_spread(s, R)
        rows.append({"スプレッド(bp)": s_bp, "回収率R": R,
                     "ハザードλ": f"{lam:.4f}", "5年Q": f"{credit.default_prob(5.0, lam):.2%}"})
display(pd.DataFrame(rows))
print("同じスプレッドでも回収率が低いほどλは小さく見える（損失1単位あたりの強度）")""")
)

# Cell 07: Merton md
cells.append(
    md(r"""## 3. Merton 構造モデル（Ch.24）

企業の**株式 = 資産に対するコールオプション**（行使価格 = 負債額 $D$）と見なす：

$$E_0 = V_0 N(d_1) - D e^{-rT} N(d_2) \quad \text{(24.3)}, \qquad
\sigma_E E_0 = N(d_1)\sigma_V V_0 \quad \text{(24.4)}$$

観測できる $E_0, \sigma_E$ からこの2式を解いて $V_0, \sigma_V$ を求め、
**リスク中立デフォルト確率** $Q = N(-d_2)$ を得ます
（$d_2$ は KMV の「distance to default」）。""")
)

# Cell 08: Merton example
cells.append(
    code(r"""# Hull Example 24.3: 株式$3M, σ_E=80%, 負債$10M（1年）, r=5%
v0, sig_v, q = credit.merton_default_prob(3.0, 0.80, 10.0, 0.05, 1.0)
d2 = (math.log(v0 / 10.0) + (0.05 - 0.5 * sig_v**2) * 1.0) / (sig_v * 1.0)
print(f"資産価値 V0 = {v0:.4f}（百万）  資産ボラ σ_V = {sig_v:.4%}")
print(f"distance to default d2 = {d2:.4f}")
print(f"リスク中立デフォルト確率 Q = N(−d2) = {q:.4%}（Hull: 12.7%）")
print(f"参考: 信用スプレッド ≈ −ln(1−(1−0.4)·Q)/1 ≈ {-math.log(1 - 0.6 * q):.4%}")""")
)

# Cell 09: interactive Merton
cells.append(
    code(r"""# --- Merton エクスプローラ（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
e_sl = widgets.FloatSlider(value=3.0, min=0.5, max=8.0, step=0.5, description="株式$M")
sige_sl = widgets.FloatSlider(value=0.80, min=0.3, max=1.5, step=0.05, description="σ_E")


def _upd_merton(change=None):
    ax2.clear()
    ds = np.linspace(5.0, 20.0, 40)
    qs = [credit.merton_default_prob(e_sl.value, sige_sl.value, d, 0.05, 1.0)[2] for d in ds]
    ax2.plot(ds, np.array(qs) * 100, lw=2)
    v0n, _, qn = credit.merton_default_prob(e_sl.value, sige_sl.value, 10.0, 0.05, 1.0)
    ax2.plot(10.0, qn * 100, "o", ms=9, color="crimson")
    ax2.set_xlabel("負債額 D（百万）")
    ax2.set_ylabel("デフォルト確率 Q (%)")
    ax2.set_title(f"株式{e_sl.value:.1f}M, σ_E={sige_sl.value:.0%}: D=10 で Q={qn:.1%}（レバレッジ↑・σ↑で Q↑）")
    fig2.canvas.draw_idle()


e_sl.observe(_upd_merton, "value")
sige_sl.observe(_upd_merton, "value")
_upd_merton()
display(widgets.HBox([e_sl, sige_sl]), fig2.canvas)""")
)

# Cell 10: copula md
cells.append(
    md(r"""## 4. デフォルト相関とガウスコピュラ（Ch.24）

複数企業の同時デフォルトは**1因子ガウスコピュラ**で表現：

$$x_i = a_i F + \sqrt{1-a_i^2}\,Z_i \quad \text{(24.7)}, \qquad
Q_i(T\mid F) = N\!\left(\frac{N^{-1}[Q_i(T)] - a_i F}{\sqrt{1-a_i^2}}\right) \quad \text{(24.8)}$$

共通因子 $F$ が悪い（負の）状態では全社のデフォルト確率が同時に上がる —
これがテールの厚さ（システミックリスク）の源です。""")
)
````

- [ ] **Step 2: Build and validate** — `Total cells: 11`; nbformat validate → `11 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/09_credit_xva
git commit -m "feat(johnhull): 09 build script with hazard/Merton cells"
```

---

### Task 3: build script — copula chart + Ch.25 + Ch.9 + closing (cells 11–26)

**Files:**
- Modify: `johnhull/volumes/09_credit_xva/build_credit_notebook.py`

- [ ] **Step 1: Insert cells 11–26 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
# Cell 11: conditional PD chart + credit VaR
cells.append(
    code(r"""# --- 条件付きデフォルト確率と Vasicek 信用VaR ---
fig3, (ax3a, ax3b) = plt.subplots(1, 2, figsize=(10.5, 4))
fig3.canvas.header_visible = False
f_grid = np.linspace(-3.0, 3.0, 100)
for q0 in (0.01, 0.05):
    for a in (0.3, 0.6):
        ax3a.plot(f_grid, [credit.gaussian_copula_conditional(q0, a, f) for f in f_grid],
                  lw=1.5, label=f"Q={q0:.0%}, a={a}")
ax3a.set_xlabel("共通因子 F（悪い ← → 良い）")
ax3a.set_ylabel("条件付きデフォルト確率")
ax3a.set_title("F が悪いと全社の PD が上昇")
ax3a.legend(fontsize=8)

confs = np.linspace(0.9, 0.9999, 100)
for rho in (0.1, 0.2, 0.4):
    ax3b.plot(confs * 100, [credit.vasicek_credit_var(0.02, rho, c) * 100 for c in confs],
              lw=1.5, label=f"ρ={rho}")
ax3b.axhline(2.0, color="0.6", ls=":", label="平均PD 2%")
ax3b.set_xlabel("信頼水準 (%)")
ax3b.set_ylabel("損失率 (%)")
ax3b.set_title("Vasicek 信用VaR（相関で裾が厚くなる）")
ax3b.legend(fontsize=8)
display(fig3.canvas)
print(f"ρ=0.2, 99.9% の信用VaR = {credit.vasicek_credit_var(0.02, 0.2, 0.999):.2%}（平均PD 2%の何倍にも）")""")
)

# ===========================================================================
# Section 2: Ch.25 credit derivatives
# ===========================================================================

# Cell 12: CDS md
cells.append(
    md(r"""## 5. クレジット・デフォルト・スワップ（Ch.25）

CDS = デフォルト保険。保護買い手がスプレッド $s$ を払い、デフォルト時に $(1-R)$ を受取る。
公正スプレッドは2レッグの現在価値を等置：

$$s = \frac{\text{PV(プロテクション・レッグ)}}{\text{PV(リスキー・アニュイティ)}}, \qquad
s \approx \lambda(1-R) \;(\text{1次近似})$$

リスキー・アニュイティは「生存確率で重み付けした割引アニュイティ」。""")
)

# Cell 13: CDS spread demo
cells.append(
    code(r"""# CDS スプレッド vs ハザード（R=40%, r=5%, 5年, 四半期払い）
rows = []
for lam in (0.005, 0.01, 0.02, 0.04):
    s = credit.cds_spread(lam, 0.4, 0.05, 5.0, freq=4)
    rows.append({"ハザードλ": f"{lam:.1%}", "CDSスプレッド": f"{s * 1e4:.1f}bp",
                 "近似 λ(1−R)": f"{lam * 0.6 * 1e4:.1f}bp"})
display(pd.DataFrame(rows))
print(f"厳密例: λ=2% → {credit.cds_spread(0.02, 0.4, 0.05, 5.0):.4%}（近似 1.20% の少し下、割引効果）")""")
)

# Cell 14: bootstrap md + demo
cells.append(
    code(r"""# --- CDS タームストラクチャーからハザードをブートストラップ（区分定数） ---
# 市場 CDS スプレッド（bp）: 各テナーに整合する区分定数ハザードを逐次に解く
from scipy.optimize import brentq

market_cds = {1.0: 60.0, 3.0: 100.0, 5.0: 140.0}  # bp


def piecewise_cds_spread(hazards, knots, R, r, maturity, freq=4):
    n = int(round(maturity * freq))
    dt = 1.0 / freq
    prot = ann = 0.0
    s_prev = 1.0
    cum = 0.0
    t_prev = 0.0
    for i in range(1, n + 1):
        t = i * dt
        lam = next(h for k, h in zip(knots, hazards) if t <= k + 1e-9)
        cum += lam * (t - t_prev)
        s = math.exp(-cum)
        d_pd = s_prev - s
        df_mid = math.exp(-r * (t - 0.5 * dt))
        prot += (1 - R) * df_mid * d_pd
        ann += math.exp(-r * t) * s * dt + df_mid * d_pd * 0.5 * dt
        s_prev, t_prev = s, t
    return prot / ann


knots = sorted(market_cds)
hazards = []
for k in knots:
    target = market_cds[k] / 1e4
    sol = brentq(lambda h: piecewise_cds_spread(hazards + [h], knots, 0.4, 0.05, k) - target,
                 1e-5, 1.0)
    hazards.append(sol)
display(pd.DataFrame({"テナー": knots, "CDS(bp)": [market_cds[k] for k in knots],
                     "区分ハザードλ": [f"{h:.4f}" for h in hazards]}))
print("上向きCDSカーブ → 後ろのテナーほどハザードが高い（フォワード・デフォルト強度）")""")
)

# Cell 15: index md
cells.append(
    md(r"""## 6. 信用インデックスと CDO（Ch.25）

- **CDX NA IG / iTraxx Europe**: 125社の均等加重バスケット。
  インデックススプレッド $\approx$ 各社 CDS の平均（高スプレッド名のウェイトが軽く厳密には少し下）
- **CDO**: 債券/CDS ポートフォリオの損失を**トランシェ**（エクイティ→メザニン→シニア）に分割。
  各トランシェは attachment〜detachment の損失帯を吸収
- トランシェ価格は**ガウスコピュラ**でデフォルト相関を入れて評価""")
)

# Cell 16: CDO tranche demo
cells.append(
    code(r"""# --- CDO トランシェの期待損失（1因子コピュラ MC） ---
def tranche_expected_loss(n_names, q, rho, attach, detach, n_sim, rng):
    a = math.sqrt(rho)
    f = rng.standard_normal(n_sim)
    thr = norm.ppf(q)
    # 各シナリオの条件付き PD → デフォルト数を二項近似
    cond_pd = norm.cdf((thr - a * f[:, None]) / math.sqrt(1 - rho))
    u = rng.random((n_sim, n_names))
    defaults = (u < cond_pd).sum(axis=1)
    loss = defaults / n_names * (1 - 0.4)  # 回収率40%
    tranche_loss = np.clip(loss, attach, detach) - attach
    return float(tranche_loss.mean() / (detach - attach))


rng_cdo = np.random.default_rng(25)
tranches = [("エクイティ 0–3%", 0.0, 0.03), ("メザニン 3–7%", 0.03, 0.07),
            ("シニア 7–15%", 0.07, 0.15)]
rows = []
for name, lo, hi in tranches:
    el_lo = tranche_expected_loss(125, 0.03, 0.1, lo, hi, 40_000, np.random.default_rng(25))
    el_hi = tranche_expected_loss(125, 0.03, 0.4, lo, hi, 40_000, np.random.default_rng(25))
    rows.append({"トランシェ": name, "期待損失率(ρ=0.1)": f"{el_lo:.2%}",
                 "期待損失率(ρ=0.4)": f"{el_hi:.2%}"})
display(pd.DataFrame(rows))
print("相関↑でエクイティの期待損失は下がり、シニアは上がる（相関はテールに損失を移す）")""")
)

# Cell 17: correlation smile md
cells.append(
    md(r"""### 相関スマイル（Ch.25）

各トランシェの市場価格から「インプライド相関」を逆算すると、トランシェごとに
値が異なる（**相関スマイル/スキュー**）。これはガウスコピュラがテール依存を
過小評価している証拠で、ボラティリティ・スマイル（第5冊）と同じ「モデルの綻び」です。
実務では**ベース相関**で整理します。""")
)

# ===========================================================================
# Section 3: Ch.9 XVA
# ===========================================================================

# Cell 18: XVA family md
cells.append(
    md(r"""## 7. XVA ファミリー（Ch.9）

OTC デリバティブの価格に乗る各種評価調整：

| 略称 | 名称 | 意味 |
|---|---|---|
| **CVA** | Credit Valuation Adj. | 相手方デフォルトの期待損失（自分の損） |
| **DVA** | Debit Valuation Adj. | 自分のデフォルトの期待利得（自分の得） |
| **FVA** | Funding Valuation Adj. | 無担保ポジションの資金調達コスト |
| **MVA** | Margin Valuation Adj. | 初期証拠金の調達コスト |
| **KVA** | Capital Valuation Adj. | 規制資本の保有コスト |

取引価格 = 無リスク価格 − CVA + DVA − FVA − MVA − KVA（符号は立場による）。""")
)

# Cell 19: CVA worked example
cells.append(
    code(r"""# --- CVA = Σ q_i v_i（スワップ的エクスポージャー・プロファイル上） ---
# 期待エクスポージャー（EE）が山形のプロファイル（スワップに典型）
times_cva = np.arange(0.5, 5.01, 0.5)
ee = 1_000_000 * np.sin(np.pi * times_cva / 5.0)  # 山形 EE（ドル）
lam_cp = 0.03  # 相手方ハザード
R_cp, r_cva = 0.4, 0.05
rows = []
cva = 0.0
s_prev = 1.0
for t, e in zip(times_cva, ee):
    s = credit.survival_prob(float(t), lam_cp)
    q_i = s_prev - s  # 区間デフォルト確率
    v_i = (1 - R_cp) * e * math.exp(-r_cva * t)  # 損失の現在価値
    cva += q_i * v_i
    rows.append({"t": t, "EE($)": round(e), "区間PD q_i": round(q_i, 4),
                 "寄与($)": round(q_i * v_i)})
    s_prev = s
display(pd.DataFrame(rows))
print(f"CVA = Σ q_i v_i = {cva:,.0f} ドル（この価格分だけ相手から見て割り引く）")""")
)

# Cell 20: netting chart
cells.append(
    code(r"""# --- ネッティングと担保の効果（EEを縮小） ---
fig4, ax4 = plt.subplots(figsize=(8, 4))
fig4.canvas.header_visible = False
ax4.plot(times_cva, ee / 1e6, "o-", lw=2, label="ネッティングなし EE")
ax4.plot(times_cva, ee / 1e6 * 0.5, "s-", lw=2, label="ネッティング後（相殺で半減）")
ax4.plot(times_cva, ee / 1e6 * 0.15, "^-", lw=2, label="担保（マージン）付き")
ax4.set_xlabel("時間（年）")
ax4.set_ylabel("期待エクスポージャー（百万$）")
ax4.set_title("ネッティング・担保は EE を下げ CVA を縮小する")
ax4.legend()
display(fig4.canvas)
print("CVA は EE に比例 → ネッティング・担保が信用リスク削減の主要手段")""")
)

# Cell 21: wrong-way / DVA md
cells.append(
    md(r"""### Wrong-way risk と DVA のパラドックス（Ch.9）

- **Wrong-way risk**: デフォルト確率とエクスポージャーが**正相関**（例: 産油国にFXを売る）→
  通常の CVA は過小評価。逆相関は **right-way**
- **DVA のパラドックス**: 自社の信用が**悪化**すると DVA が増え会計上の**利益**が出る —
  実現は自社デフォルト時のみで直感に反する。FVA との二重計上論争もある（Ch.9）""")
)

# ===========================================================================
# Section 4: verification / exercises / summary
# ===========================================================================

# Cell 22: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_credit.py にも同等の検証あり） ---
checks = []
checks.append(("S(2) = e^{-0.04}", credit.survival_prob(2.0, 0.02), math.exp(-0.04), 1e-12))
checks.append(("hazard from spread", credit.hazard_from_spread(0.012, 0.4), 0.02, 1e-12))
checks.append(("CDS spread ≈ 0.012075", credit.cds_spread(0.02, 0.4, 0.05, 5.0), 0.012075, 5e-5))
checks.append(("Merton V0 ≈ 12.3954", v0, 12.3954, 2e-3))
checks.append(("Merton σ_V ≈ 0.2123", sig_v, 0.21230, 5e-4))
checks.append(("Merton Q ≈ 0.127", q, 0.12697, 5e-4))
checks.append(("copula 単調（F悪い→PD↑）",
               float(credit.gaussian_copula_conditional(0.05, 0.5, -2.0)
                     > credit.gaussian_copula_conditional(0.05, 0.5, 2.0)), 1.0, 0.0))
checks.append(("信用VaR > 平均PD（99.9%）",
               float(credit.vasicek_credit_var(0.02, 0.2, 0.999) > 0.02), 1.0, 0.0))
assert cva > 0
print(f"[OK] CVA = {cva:,.0f} > 0")

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 23: exercises
cells.append(
    md(r"""## 8. 練習問題

**Q1.** 5年 CDS スプレッドが 150bp、回収率 40%。平均ハザードレートの概算は？

<details><summary>解答</summary>

λ ≈ s/(1−R) = 0.015/0.6 = 2.5%/年。5年累積デフォルト確率 ≈ 1−e^{−0.125} ≈ 11.8%。
</details>

**Q2.** Merton モデルでレバレッジ（D/V）が上がると Q はどうなる？

<details><summary>解答</summary>

上がる。d2 = [ln(V/D)+(r−σ²/2)T]/(σ√T) が小さくなり Q=N(−d2) が増加。
資産ボラ σ_V の上昇も同様に Q を上げる。
</details>

**Q3.** CDO で相関 ρ を 0 → 1 に上げると、エクイティとシニアの期待損失はどう動く？

<details><summary>解答</summary>

ρ↑ で損失が「全社デフォルト or 全社生存」の両極に寄る。エクイティの期待損失は減り、
シニアは増える（相関がテールへ損失を移す）。
</details>""")
)

# Cell 24: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| ハザード | S(t)=e^{−∫λ}。リスク中立PDは実世界の5〜10倍 |
| スプレッド | λ ≈ s/(1−R)。CDS は protection/annuity |
| Merton | 株式=資産コール。Q=N(−d2)、d2=distance to default |
| コピュラ | 1因子で同時デフォルト。相関がテールを厚く |
| CDO | 相関はエクイティ→シニアへ損失を移す。相関スマイル |
| XVA | CVA=Σq_i v_i。ネッティング・担保で削減。DVAパラドックス |

**次へ**: `volumes/10_exotics_martingales`（Ch.26, 28）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 25: closing md
cells.append(
    md(r"""---
*第9冊おわり。構造モデル・コピュラ・XVA まで信用の主要トピックを一巡しました。*""")
)
````

- [ ] **Step 2: Rebuild and validate** — `Total cells: 26`; nbformat validate → `26 cells valid`. (Note: cell count is 26, not 27 — the spec's "27" was an estimate; this is fine.)

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/09_credit_xva
git commit -m "feat(johnhull): 09 CDS/CDO/XVA cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/09_credit_xva/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 9 → done; module list gains `credit`)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output credit_xva_executed.ipynb`; the CDO-MC and bootstrap cells take a few seconds). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc.**

- [ ] **Step 3: Tests + lint:** hullkit suite → 81 passed; ruff johnhull clean; workspace minus gto (explicit paths) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/09_credit_xva/PROGRESS.md`**

```markdown
# 09_credit_xva — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `credit_xva.ipynb` (26 cells) generated by `build_credit_notebook.py`
- Coverage: Hull 11e Ch.24 (hazard rates, Merton structural model, Gaussian
  copula, Vasicek credit VaR), Ch.25 (CDS valuation/bootstrap, indices, CDO
  tranches, correlation smile), Ch.9 (XVA family, CVA worked example,
  netting/collateral, wrong-way risk, DVA paradox)
- hullkit addition: `credit.py` (survival/default, hazard_from_spread,
  cds_spread, merton_default_prob, gaussian_copula_conditional,
  vasicek_credit_var — 6 tests; suite 81)
- Verified: headless nbconvert, Hull-pin assertion cell (Merton Ex 24.3,
  CDS spread), hullkit pytest, ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_credit_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-11 Ch.24 / 12-17 Ch.25 / 18-21 Ch.9 /
  22 verification / 23 exercises / 24-25 summary
- KMV EDF, CreditMetrics, base correlation, full netting-set CVA: md only
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 9 → done; module list `..., risk.` → `..., risk, credit.`**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/09_credit_xva/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 09_credit_xva complete"
```

- [ ] **Step 7: Report** with quoted outputs.
