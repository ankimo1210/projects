# johnhull 08_risk_var Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.risk` (VaR/ES, TDD) and the 25-cell `volumes/08_risk_var/risk_var.ipynb` covering Hull 11e Ch.22.

**Architecture:** As volumes 01–07. Hull's classic Microsoft/AT&T example pins the variance-covariance path; constructed arrays pin the historical path; an options demo connects to bsm/mc.

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-08-risk-var-design.md`

Implementer notes: as previous volumes (ruff scope, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`, stage only specified files, report statistical-tolerance failures instead of widening).

---

### Task 1: hullkit.risk (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_risk.py`
- Create: `johnhull/hullkit/src/hullkit/risk.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_risk.py`:

```python
"""Tests for hullkit.risk against Hull 11e Ch.22 examples."""

import math

import numpy as np
import pytest
from scipy.stats import norm

from hullkit import risk


def test_hull_microsoft_att_example():
    # $10M Microsoft sigma=2%/day -> 10-day 99% VaR = 1,471,311 (Hull 1,471,300)
    v_ms = risk.normal_var(200_000.0, alpha=0.99, horizon=10.0)
    assert v_ms == pytest.approx(1_471_311.0, abs=5.0)
    # $5M AT&T sigma=1%/day -> 367,828 (Hull 367,800)
    v_att = risk.normal_var(50_000.0, alpha=0.99, horizon=10.0)
    assert v_att == pytest.approx(367_828.0, abs=5.0)
    # portfolio rho=0.3 -> sigma_P = 220,227, VaR = 1,620,140 (Hull 1,620,100)
    sig_p = risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, 0.3], [0.3, 1.0]])
    assert sig_p == pytest.approx(220_227.0, abs=5.0)
    v_p = risk.normal_var(sig_p, alpha=0.99, horizon=10.0)
    assert v_p == pytest.approx(1_620_114.0, abs=10.0)
    assert v_ms + v_att - v_p == pytest.approx(219_026.0, abs=20.0)  # diversification


def test_normal_es_exceeds_var():
    sigma = 200_000.0
    var_1d = risk.normal_var(sigma)
    es_1d = risk.normal_es(sigma)
    # ES/sigma = phi(z)/(1-alpha) = 2.6652 for alpha=0.99
    assert es_1d / sigma == pytest.approx(norm.pdf(norm.ppf(0.99)) / 0.01, abs=1e-9)
    assert es_1d > var_1d


def test_sqrt_horizon_scaling():
    sigma = 123_456.0
    assert risk.normal_var(sigma, horizon=10.0) == pytest.approx(
        math.sqrt(10.0) * risk.normal_var(sigma, horizon=1.0), abs=1e-9
    )
    assert risk.normal_es(sigma, horizon=10.0) == pytest.approx(
        math.sqrt(10.0) * risk.normal_es(sigma, horizon=1.0), abs=1e-9
    )


def test_historical_var_es_hull_convention():
    # 500 scenarios: P&L = -1..-500 shuffled; 99% -> k=5: VaR = 5th worst = 496
    pnl = -np.arange(1.0, 501.0)
    rng = np.random.default_rng(0)
    rng.shuffle(pnl)
    var, es = risk.historical_var_es(pnl, alpha=0.99)
    assert var == pytest.approx(496.0, abs=1e-12)
    assert es == pytest.approx(np.mean([496.0, 497.0, 498.0, 499.0, 500.0]), abs=1e-12)
    assert es > var


def test_historical_small_sample_k_floor():
    var, es = risk.historical_var_es([-1.0, -2.0, -3.0, 4.0], alpha=0.99)
    assert var == pytest.approx(3.0)
    assert es == pytest.approx(3.0)


def test_portfolio_sigma_single_asset_reduces():
    assert risk.portfolio_sigma([10e6], [0.02], [[1.0]]) == pytest.approx(200_000.0)
```

- [ ] **Step 2: Run to verify failure** (ImportError)

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/risk.py`**

```python
"""Value at Risk and Expected Shortfall (Hull 11e, Ch.22)."""

import math

import numpy as np
from scipy.stats import norm


def historical_var_es(pnl, alpha=0.99):
    """Historical-simulation VaR and ES from a P&L array (gains positive).

    Hull's convention with n scenarios: k = max(1, ceil((1-alpha)*n));
    VaR = k-th worst loss; ES = mean of the k worst losses
    (99% with 500 scenarios -> 5th worst / mean of worst five).
    Returns (var, es) as positive loss amounts.
    """
    losses = -np.asarray(pnl, dtype=float)
    n = len(losses)
    k = max(1, math.ceil((1.0 - alpha) * n))
    worst = np.sort(losses)[::-1][:k]
    return float(worst[-1]), float(worst.mean())


def normal_var(sigma, alpha=0.99, horizon=1.0, mu=0.0):
    """Model-building VaR = z_alpha * sigma * sqrt(h) - mu * h (Hull Ch.22).

    sigma is the one-day standard deviation in currency units.
    """
    return float(norm.ppf(alpha) * sigma * math.sqrt(horizon) - mu * horizon)


def normal_es(sigma, alpha=0.99, horizon=1.0, mu=0.0):
    """Normal ES = sigma * sqrt(h) * phi(z_alpha)/(1-alpha) - mu*h (Hull eq. 22.1)."""
    z = norm.ppf(alpha)
    return float(sigma * math.sqrt(horizon) * norm.pdf(z) / (1.0 - alpha) - mu * horizon)


def portfolio_sigma(amounts, vols, corr):
    """Dollar sigma of a linear portfolio: sqrt(a^T C a), C_ij = rho_ij s_i s_j
    (Hull eq. 22.3/22.4). amounts in currency units, vols daily."""
    a = np.asarray(amounts, dtype=float)
    v = np.asarray(vols, dtype=float)
    c = np.asarray(corr, dtype=float) * np.outer(v, v)
    return float(np.sqrt(a @ c @ a))
```

- [ ] **Step 4: Verify** — 6 passed; full suite 74 passed; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/risk.py johnhull/hullkit/tests/test_risk.py
git commit -m "feat(hullkit): VaR and ES with Hull Ch.22 example pins"
```

---

### Task 2: build script — intro + concept + variance-covariance (cells 00–12)

**Files:**
- Create: `johnhull/volumes/08_risk_var/build_risk_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–12** (helpers + footer verbatim from `volumes/07_swaps/build_swaps_notebook.py`; title `build_risk_notebook.py`; output `risk_var.ipynb`)

````python
# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# VaR と期待ショートフォール（Hull 11e Ch.22）

`johnhull/volumes` シリーズ第8冊。市場リスクを1つの数値に集約する：

- **VaR** — 「信頼水準 α で N 日間に超えない損失」／ **ES** — 超えたときの条件付き期待損失
- **分散共分散法** — Hull の Microsoft/AT&T 例を完全再現
- **ヒストリカル・シミュレーション** — 太い裾と正規仮定の乖離
- **オプションの VaR** — デルタ近似 vs デルタ-ガンマ vs 完全再評価（第3冊・第6冊の道具で）

> VaR は劣加法性を満たさない（→ Basel FRTB は ES 97.5% へ移行）— 反例も作ります""")
)

cells.append(code(r"""%matplotlib widget"""))

cells.append(
    code(r"""# --- imports & 共通設定 ---
import math

import numpy as np
import pandas as pd
import ipywidgets as widgets
from IPython.display import display
from scipy.stats import norm, t as t_dist

from hullkit import bsm, mc, nbplot, risk

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: definitions and coherence
# ===========================================================================

# Cell 03: definitions md
cells.append(
    md(r"""## 1. 定義（Ch.22）

$$\Pr(L > \mathrm{VaR}_\alpha) = 1 - \alpha, \qquad
\mathrm{ES}_\alpha = E[L \mid L > \mathrm{VaR}_\alpha]$$

- VaR は分位点（「どこから先がテールか」）、ES はテールの**深さの平均**
- iid 正規なら $\mathrm{VaR}_{N日} = \sqrt{N}\,\mathrm{VaR}_{1日}$（ボラ・クラスタリングがあると過小評価 — 第5冊）""")
)

# Cell 04: distribution chart
cells.append(
    code(r"""# --- 損失分布上の VaR と ES ---
sigma_demo = 1.0
z99 = norm.ppf(0.99)
es99 = norm.pdf(z99) / 0.01
x_l = np.linspace(-4.0, 4.0, 400)

fig1, ax1 = plt.subplots(figsize=(8, 4))
fig1.canvas.header_visible = False
ax1.plot(x_l, norm.pdf(x_l), lw=2)
ax1.fill_between(x_l, 0.0, norm.pdf(x_l), where=x_l >= z99, alpha=0.35, color="crimson")
ax1.axvline(z99, color="crimson", ls="--", lw=1.5, label=f"VaR99 = {z99:.3f}σ")
ax1.axvline(es99, color="darkred", ls=":", lw=2, label=f"ES99 = {es99:.3f}σ（赤領域の重心）")
ax1.set_xlabel("損失（σ単位）")
ax1.set_ylabel("密度")
ax1.set_title("VaR は境界、ES は超過部分の平均")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 05: coherence md
cells.append(
    md(r"""## 2. VaR は「コヒーレント」でない（Ch.22）

コヒーレントなリスク指標の4公理のうち、VaR は**劣加法性**
$\rho(A+B) \le \rho(A) + \rho(B)$ を満たさないことがある —
「分散化でリスク指標が増える」逆転が起こり得ます。ES は4公理すべてを満たします。

この理由で Basel（FRTB）は市場リスクの基準を **VaR 99% → ES 97.5%** に変更しました。""")
)

# Cell 06: subadditivity counterexample
cells.append(
    code(r"""# --- 劣加法性の反例: 独立な「0.8%で-10、それ以外0」の損失2つ ---
p_bad, loss_bad = 0.008, 10.0
# 単独: P(L >= 10) = 0.8% < 1% → VaR99 = 0
var_single = 0.0 if p_bad < 0.01 else loss_bad
# 合算: P(L >= 10) = 1 - (1-p)^2 ≈ 1.594% > 1% → VaR99 = 10
p_any = 1.0 - (1.0 - p_bad) ** 2
var_combined = loss_bad if p_any > 0.01 else 0.0
print(f"単独ポジションの VaR99 = {var_single}（P(大損) = {p_bad:.2%} < 1%）")
print(f"2つ合わせた VaR99 = {var_combined}（P(どちらか大損) = {p_any:.3%} > 1%）")
print(f"劣加法性: VaR(A+B) = {var_combined} > VaR(A)+VaR(B) = {2 * var_single} → 破れ")

# ES は破れない: 単独 ES99 = E[L|L>VaR]= 10×0.008/0.01 = 8 → 2つで16 ≥ 合算ES
es_single = loss_bad * p_bad / 0.01
print(f"参考: 単独 ES99 = {es_single}（テールを最初から見ている）")""")
)

# ===========================================================================
# Section 2: variance-covariance method
# ===========================================================================

# Cell 07: model building md
cells.append(
    md(r"""## 3. 分散共分散法（モデル構築法）（Ch.22）

リターンを多変量正規と仮定すると解析解：

$$\sigma_P = \sqrt{\boldsymbol{\alpha}^\top C \boldsymbol{\alpha}}, \qquad
\mathrm{VaR} = z_\alpha\,\sigma_P\sqrt{N}, \qquad
\mathrm{ES} = \sigma_P\sqrt{N}\,\frac{\phi(z_\alpha)}{1-\alpha}$$

（$\boldsymbol{\alpha}$: ドル投資額ベクトル、$C_{ij} = \rho_{ij}\sigma_i\sigma_j$ 日次）""")
)

# Cell 08: Hull example
cells.append(
    code(r"""# --- Hull の例: Microsoft $10M（σ=2%/日）+ AT&T $5M（σ=1%/日）、ρ=0.3 ---
v_ms = risk.normal_var(200_000.0, alpha=0.99, horizon=10.0)
v_att = risk.normal_var(50_000.0, alpha=0.99, horizon=10.0)
sig_p = risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, 0.3], [0.3, 1.0]])
v_port = risk.normal_var(sig_p, alpha=0.99, horizon=10.0)
display(pd.DataFrame([
    {"ポジション": "Microsoft $10M", "σ（日次$）": 200_000, "10日99%VaR": round(v_ms)},
    {"ポジション": "AT&T $5M", "σ（日次$）": 50_000, "10日99%VaR": round(v_att)},
    {"ポジション": "ポートフォリオ（ρ=0.3）", "σ（日次$）": round(sig_p), "10日99%VaR": round(v_port)},
]))
print(f"分散化メリット = {v_ms + v_att - v_port:,.0f}（Hull: 約219,000）")""")
)

# Cell 09: ES example
cells.append(
    code(r"""es_port = risk.normal_es(sig_p, alpha=0.99, horizon=10.0)
print(f"ポートフォリオの 10日 99% ES = {es_port:,.0f}")
print(f"ES / VaR = {es_port / v_port:.4f}（正規なら α=99% で常に {norm.pdf(norm.ppf(0.99)) / 0.01 / norm.ppf(0.99):.4f}）")""")
)

# Cell 10: interactive rho
cells.append(
    code(r"""# --- 相関と分散化メリット（インタラクティブ） ---
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
rho_sl = widgets.FloatSlider(value=0.3, min=-1.0, max=1.0, step=0.05, description="ρ")


def _upd_rho(change=None):
    ax2.clear()
    rhos = np.linspace(-1.0, 1.0, 81)
    vars_p = [risk.normal_var(
        risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, r_], [r_, 1.0]]),
        alpha=0.99, horizon=10.0) for r_ in rhos]
    ax2.plot(rhos, np.array(vars_p) / 1e6, lw=2)
    ax2.axhline((v_ms + v_att) / 1e6, color="0.6", ls=":", label="単純合算（ρ=1で一致）")
    r_now = rho_sl.value
    v_now = risk.normal_var(
        risk.portfolio_sigma([10e6, 5e6], [0.02, 0.01], [[1.0, r_now], [r_now, 1.0]]),
        alpha=0.99, horizon=10.0)
    ax2.plot(r_now, v_now / 1e6, "o", ms=9, color="crimson")
    ax2.set_xlabel("相関 ρ")
    ax2.set_ylabel("10日99% VaR（百万$）")
    ax2.set_title(f"ρ={r_now:+.2f}: VaR = {v_now:,.0f} ／ 分散化メリット = {v_ms + v_att - v_now:,.0f}")
    ax2.legend()
    fig2.canvas.draw_idle()


rho_sl.observe(_upd_rho, "value")
_upd_rho()
display(rho_sl, fig2.canvas)""")
)

# Cell 11: scaling md
cells.append(
    md(r"""### √N スケーリングの注意

$\sqrt{N}$ 規則は「日次リターンが iid」前提。第5冊で見たとおり実際は
**ボラティリティ・クラスタリング**があり、高ボラ局面では持続性（GARCH の α+β）
のぶん過小評価になります。規制（FRTB）は重なり合う10日リターンや
ストレス期間カリブレーションでこれに対処しています。""")
)

# Cell 12: bridge md
cells.append(
    md(r"""### ここまでの前提

分散共分散法は **(a) 線形ポジション (b) 正規リターン** の2つを仮定しています。
次節でそれぞれを外します：(b) → ヒストリカル法、(a) → デルタ-ガンマ近似。""")
)
````

- [ ] **Step 2: Build and validate** — `Total cells: 13`; nbformat validate → `13 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/08_risk_var
git commit -m "feat(johnhull): 08 build script with VaR concept and variance-covariance cells"
```

---

### Task 3: build script — historical sim + options + closing (cells 13–24)

**Files:**
- Modify: `johnhull/volumes/08_risk_var/build_risk_notebook.py`

- [ ] **Step 1: Insert cells 13–24 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
# ===========================================================================
# Section 3: historical simulation
# ===========================================================================

# Cell 13: historical md
cells.append(
    md(r"""## 4. ヒストリカル・シミュレーション（Ch.22）

過去 501 日 → 500 個の「昨日→今日」変化率シナリオを作り、
**今日のポートフォリオ**に適用して損益分布を構築：

$$\text{シナリオ}_i\text{ の価値} = v_n \cdot \frac{v_i}{v_{i-1}}$$

99% VaR は 500 シナリオの**5番目に大きい損失**、ES はワースト5の平均（Hull 流儀）。
分布形を仮定しないので**太い裾**をそのまま拾えます。""")
)

# Cell 14: historical demo
cells.append(
    code(r"""# --- 合成2資産（t分布の太い裾）でヒストリカル VaR/ES vs 正規 ---
rng8 = np.random.default_rng(80)
N_HIST = 500
NU_T = 4.0  # 自由度4のt分布（太い裾）
scale_t = math.sqrt((NU_T - 2.0) / NU_T)  # 分散を1に正規化
r1 = 0.02 * scale_t * t_dist.rvs(NU_T, size=N_HIST, random_state=rng8)
r2 = 0.01 * scale_t * t_dist.rvs(NU_T, size=N_HIST, random_state=rng8)
pnl_hist = 10e6 * r1 + 5e6 * r2  # 各シナリオの1日損益

var_h, es_h = risk.historical_var_es(pnl_hist, alpha=0.99)
sig_sample = float(np.std(pnl_hist, ddof=1))
var_n = risk.normal_var(sig_sample, alpha=0.99)
es_n = risk.normal_es(sig_sample, alpha=0.99)
display(pd.DataFrame([
    {"手法": "ヒストリカル", "1日99%VaR": round(var_h), "1日99%ES": round(es_h)},
    {"手法": "正規（同じσ）", "1日99%VaR": round(var_n), "1日99%ES": round(es_n)},
]))
print(f"太い裾 → ヒストリカルの方が VaR・ES とも大きい（VaR比 {var_h / var_n:.2f}）")""")
)

# Cell 15: histogram
cells.append(
    code(r"""fig3, ax3 = plt.subplots(figsize=(8, 4))
fig3.canvas.header_visible = False
ax3.hist(pnl_hist / 1e3, bins=60, alpha=0.7)
ax3.axvline(-var_h / 1e3, color="crimson", ls="--", lw=2, label=f"hist VaR99 = {var_h / 1e3:,.0f}k")
ax3.axvline(-es_h / 1e3, color="darkred", ls=":", lw=2, label=f"hist ES99 = {es_h / 1e3:,.0f}k")
ax3.axvline(-var_n / 1e3, color="steelblue", ls="--", lw=1.5, label=f"正規 VaR99 = {var_n / 1e3:,.0f}k")
ax3.set_xlabel("1日損益（千$）")
ax3.set_ylabel("シナリオ数")
ax3.set_title("500シナリオの損益分布")
ax3.legend(fontsize=9)
display(fig3.canvas)""")
)

# Cell 16: backtesting md
cells.append(
    md(r"""## 5. ストレス VaR とバックテスティング（Ch.22）

- **Stressed VaR/ES**: 過去で最も不利だった 251 日（例: 2008年）のシナリオで計算 —
  「平時のデータだけ」問題への規制対応
- **バックテスティング**: 実損益が VaR を超えた回数を数える。99% VaR なら
  期待超過率 1% — 大幅に多ければモデル不良（太い裾・ボラ変動の見落とし）""")
)

# Cell 17: backtest demo
cells.append(
    code(r"""# --- バックテスト: ローリング正規VaR vs 実現損益（GARCH的なボラ変動を含む系列） ---
rng9 = np.random.default_rng(90)
n_bt = 1000
vol_path = 0.01 * np.exp(0.4 * np.sin(np.linspace(0.0, 6.0 * np.pi, n_bt)))  # ゆっくり変動するボラ
ret_bt = vol_path * rng9.standard_normal(n_bt)
pnl_bt = 10e6 * ret_bt

window = 250
exceptions = 0
n_tests = 0
for i in range(window, n_bt):
    sig_w = float(np.std(pnl_bt[i - window:i], ddof=1))
    var_w = risk.normal_var(sig_w, alpha=0.99)
    n_tests += 1
    if -pnl_bt[i] > var_w:
        exceptions += 1
rate = exceptions / n_tests
print(f"超過回数 = {exceptions} / {n_tests}（{rate:.2%}、期待 1%）")
print("ボラが動く系列では等加重窓の正規VaRは超過が偏在しがち（クラスタリング）")""")
)

# ===========================================================================
# Section 4: options / nonlinearity
# ===========================================================================

# Cell 18: delta-gamma md
cells.append(
    md(r"""## 6. オプションを含む VaR — 線形近似の限界（Ch.22、eq 22.7–22.8）

$$\Delta P \approx \delta\,\Delta S \quad (\text{デルタ近似}), \qquad
\Delta P \approx \delta\,\Delta S + \tfrac{1}{2}\gamma(\Delta S)^2 \quad (\text{デルタ-ガンマ})$$

ロングコールは $\gamma > 0$ — 下落側の損失はデルタ近似より**小さい**
（曲率が守ってくれる）。線形近似はロングオプションの VaR を**過大評価**します。""")
)

# Cell 19: option VaR three ways
cells.append(
    code(r"""# --- ロングコール100枚（S=100, K=100, σ=25%, r=5%, T=0.5）の1日99%VaR ---
S_O, K_O, R_O, SIG_O, T_O = 100.0, 100.0, 0.05, 0.25, 0.5
N_OPT = 100.0
sig_1d = 0.25 / math.sqrt(252.0)  # 日次ボラ（原資産）
delta_o = bsm.call_delta(S_O, K_O, R_O, SIG_O, T_O)
gamma_o = bsm.gamma(S_O, K_O, R_O, SIG_O, T_O)
c0 = bsm.call_price(S_O, K_O, R_O, SIG_O, T_O)

# (1) デルタ正規
var_delta = risk.normal_var(N_OPT * delta_o * S_O * sig_1d, alpha=0.99)
# (2)(3) MC: 同一ショックでデルタ-ガンマ近似と完全再評価
rng_o = np.random.default_rng(11)
ds = S_O * sig_1d * rng_o.standard_normal(100_000)
pnl_dg = N_OPT * (delta_o * ds + 0.5 * gamma_o * ds**2)
pnl_full = N_OPT * (np.array([
    bsm.call_price(S_O + d, K_O, R_O, SIG_O, T_O - 1.0 / 252.0) for d in ds[:20_000]
]) - c0)
var_dg, es_dg = risk.historical_var_es(pnl_dg, alpha=0.99)
var_full, es_full = risk.historical_var_es(pnl_full, alpha=0.99)
display(pd.DataFrame([
    {"手法": "デルタ正規", "1日99%VaR": round(var_delta, 1)},
    {"手法": "デルタ-ガンマ（MC 100k）", "1日99%VaR": round(var_dg, 1)},
    {"手法": "完全再評価（MC 20k、Θ込み）", "1日99%VaR": round(var_full, 1)},
]))
print(f"γ = {gamma_o:.4f} > 0 → 曲率が下値を守り、デルタ正規が最も大きい")""")
)

# Cell 20: pointers md
cells.append(
    md(r"""### 発展ポインタ（Ch.22）

- **Cornish-Fisher 展開**: ΔP の歪度・尖度で正規分位点を補正（Technical Note 10）
- **キャッシュフロー・マッピング**: 債券を標準満期のゼロクーポン束に分解して C を適用
- **PCA**: 金利カーブの動きを「レベル・スロープ・曲率」少数因子に圧縮して VaR を効率化
  （第1冊 ir_models のカーブパターンが因子の直感に対応）""")
)

# ===========================================================================
# Section 5: verification / exercises / summary
# ===========================================================================

# Cell 21: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_risk.py にも同等の検証あり） ---
checks = []
checks.append(("MSFT 10日99%VaR 1,471,311", v_ms, 1_471_311.0, 5.0))
checks.append(("AT&T 367,828", v_att, 367_828.0, 5.0))
checks.append(("σ_P 220,227", sig_p, 220_227.0, 5.0))
checks.append(("ポートフォリオ VaR 1,620,114", v_port, 1_620_114.0, 10.0))
checks.append(("ES > VaR（正規）", float(es_port > v_port), 1.0, 0.0))
checks.append(("劣加法性の破れ", float(var_combined > 2 * var_single), 1.0, 0.0))
checks.append(("hist VaR > 正規 VaR（太い裾）", float(var_h > var_n), 1.0, 0.0))
checks.append(("デルタ-ガンマ < デルタ正規（ロングコール）", float(var_dg < var_delta), 1.0, 0.0))

pnl_known = -np.arange(1.0, 501.0)
var_k, es_k = risk.historical_var_es(pnl_known, alpha=0.99)
checks.append(("hist 規約: 5番目のワースト", var_k, 496.0, 1e-12))
checks.append(("hist ES: ワースト5平均", es_k, 498.0, 1e-12))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 22: exercises
cells.append(
    md(r"""## 7. 練習問題

**Q1.** σ=3%/日 の $1M ポジション。5日 97.5% VaR と ES は？（z=1.960、φ(z)/(1−α)=2.338）

<details><summary>解答</summary>

σ$ = 30,000。VaR = 1.960×30,000×√5 ≈ 131,500。ES = 2.338×30,000×√5 ≈ 156,800。
</details>

**Q2.** ヒストリカル法で 1,000 シナリオの 97.5% VaR は何番目の損失？

<details><summary>解答</summary>

k = (1−0.975)×1000 = 25 → 25番目に大きい損失。ES はワースト25の平均。
</details>

**Q3.** ショートコールのポートフォリオでは、デルタ近似はVaRを過大・過小どちらに評価する？

<details><summary>解答</summary>

過小評価。γ<0（ショートガンマ）では下落・上昇どちらでも損失が線形より膨らむ。
ロングと逆。
</details>""")
)

# Cell 23: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| VaR / ES | 分位点 vs テール平均。ES はコヒーレント（Basel は ES 97.5% へ） |
| 分散共分散 | VaR = z·√(αᵀCα)·√N。速いが線形＋正規仮定 |
| ヒストリカル | 分布仮定なし・太い裾を拾う。Hull 規約: 500中5番目 |
| √N | iid 前提。ボラ・クラスタリングで崩れる（第5冊） |
| オプション | ロングγはデルタ近似で過大、ショートγは過小評価 |

**次へ**: `volumes/09_credit_xva`（Ch.9, 24, 25 — 信用リスク）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 24: closing md
cells.append(
    md(r"""---
*第8冊おわり。`hullkit.risk` は第9冊（信用 VaR・CVA）でも使います。*""")
)
````

- [ ] **Step 2: Rebuild and validate** — `Total cells: 25`; nbformat validate → `25 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/08_risk_var
git commit -m "feat(johnhull): 08 historical-sim and option-VaR cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/08_risk_var/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 8 → done; module list gains `risk`)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output risk_var_executed.ipynb`; cell 19's 20k full revaluations take ~10s). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc.**

- [ ] **Step 3: Tests + lint:** hullkit suite → 74 passed; ruff johnhull clean; workspace minus gto (explicit paths) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/08_risk_var/PROGRESS.md`**

```markdown
# 08_risk_var — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `risk_var.ipynb` (25 cells) generated by `build_risk_notebook.py`
- Coverage: Hull 11e Ch.22 (VaR/ES definitions and coherence, the
  Microsoft/AT&T variance-covariance example, historical simulation with
  fat tails, backtesting, delta vs delta-gamma vs full-revaluation option VaR)
- hullkit addition: `risk.py` (historical_var_es, normal_var, normal_es,
  portfolio_sigma — 6 tests; suite 74)
- Verified: headless nbconvert, Hull-pin assertion cell, hullkit pytest,
  ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_risk_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-06 definitions+coherence / 07-12 var-covar /
  13-17 historical+backtest / 18-20 options / 21 verification / 22 exercises /
  23-24 summary
- Cornish-Fisher, PCA, cash-flow mapping: md pointers only
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 8 → done; module list `..., swaps.` → `..., swaps, risk.`**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/08_risk_var/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 08_risk_var complete"
```

- [ ] **Step 7: Report** with quoted outputs.
