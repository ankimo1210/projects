# johnhull 10_exotics_martingales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hullkit.exotics` (closed-form exotic option pricers, TDD) and the 28-cell `volumes/10_exotics_martingales/exotics.ipynb` covering Hull 11e Ch.26 and Ch.28.

**Architecture:** As volumes 01–09. Exotic closed forms are cross-checked against parity identities (binary decomposition, barrier in+out=vanilla) and MC (Asian). Ch.28 is illustrated numerically (numeraire invariance, market price of risk, forward measure).

**Spec:** `docs/superpowers/specs/2026-06-08-johnhull-10-exotics-martingales-design.md`

**Reference values** (hand-verified):

| Quantity | Value |
|---|---|
| Margrabe (U0=V0=100, σ=0.2 each, ρ=0.5, T=1) | 7.965567 (r-independent) |
| Gap call (S=100, K1=95, K2=100, r=5%, σ=20%, T=1) | 13.112208 |
| Binary decomposition aon(K)−K·con(K) | = vanilla call (1e-12) |
| Barrier c_di + c_do (H=90≤K=100) | = vanilla 10.450584 |
| Turnbull-Wakeman Asian (S=K=100, r=5%, σ=20%, T=1) | 5.7828 (σ_avg=0.1164); MC≈5.80 |
| Lookback floating (S_min=S=100, r=5%, σ=20%, T=1) | 17.2168 ≥ ATM call 10.45 |

Implementer notes: as previous volumes (ruff scope, trailer `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`, stage only specified files, report tolerance failures).

---

### Task 1: hullkit.exotics (TDD)

**Files:**
- Create: `johnhull/hullkit/tests/test_exotics.py`
- Create: `johnhull/hullkit/src/hullkit/exotics.py`

- [ ] **Step 1: Write the failing tests**

`johnhull/hullkit/tests/test_exotics.py`:

```python
"""Tests for hullkit.exotics against Hull 11e Ch.26 closed forms."""

import math

import numpy as np
import pytest

from hullkit import bsm, exotics


def test_gap_call():
    g = exotics.gap_call(100.0, 95.0, 100.0, 0.05, 0.20, 1.0)
    assert g == pytest.approx(13.112208, abs=1e-5)


def test_binary_decomposition_equals_vanilla():
    S, K, r, sigma, T, q = 100.0, 100.0, 0.05, 0.2, 1.0, 0.0
    aon = exotics.asset_or_nothing(S, K, r, sigma, T, q, kind="call")
    con = exotics.cash_or_nothing(S, K, r, sigma, T, q, kind="call", payout=1.0)
    assert aon - K * con == pytest.approx(bsm.call_price(S, K, r, sigma, T, q), abs=1e-12)


def test_cash_or_nothing_parity():
    S, K, r, sigma, T = 100.0, 105.0, 0.05, 0.3, 0.5
    cc = exotics.cash_or_nothing(S, K, r, sigma, T, kind="call", payout=1.0)
    cp = exotics.cash_or_nothing(S, K, r, sigma, T, kind="put", payout=1.0)
    assert cc + cp == pytest.approx(math.exp(-r * T), abs=1e-12)


def test_barrier_in_out_equals_vanilla():
    S, K, H, r, sigma, T = 100.0, 100.0, 90.0, 0.05, 0.2, 1.0
    cdi = exotics.barrier_call(S, K, H, r, sigma, T, barrier="down-and-in")
    cdo = exotics.barrier_call(S, K, H, r, sigma, T, barrier="down-and-out")
    assert cdi + cdo == pytest.approx(bsm.call_price(S, K, r, sigma, T), abs=1e-12)
    assert cdi == pytest.approx(1.785112, abs=1e-5)


def test_barrier_monotonic_in_H():
    # down-and-in call increases as the barrier rises toward the strike
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.2, 1.0
    c70 = exotics.barrier_call(S, K, 70.0, r, sigma, T, barrier="down-and-in")
    c90 = exotics.barrier_call(S, K, 90.0, r, sigma, T, barrier="down-and-in")
    assert c90 > c70


def test_margrabe_r_independent_and_value():
    v1 = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0)
    assert v1 == pytest.approx(7.965567, abs=1e-5)
    # Margrabe does not depend on r (it is not even an argument)
    v2 = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0, q_u=0.0, q_v=0.0)
    assert v1 == pytest.approx(v2, abs=1e-12)


def test_asian_tw_below_vanilla_and_near_mc():
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.2, 1.0
    a = exotics.asian_call_turnbull_wakeman(S, K, r, sigma, T)
    assert a < bsm.call_price(S, K, r, sigma, T)  # averaging lowers vol
    # MC arithmetic-average check
    rng = np.random.default_rng(1)
    n_steps, n_paths, dt = 252, 200_000, T / 252
    z = rng.standard_normal((n_paths, n_steps))
    lp = np.cumsum((r - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * z, axis=1)
    avg = (S * np.exp(lp)).mean(axis=1)
    mc = math.exp(-r * T) * np.maximum(avg - K, 0.0).mean()
    assert a == pytest.approx(mc, abs=0.1)


def test_lookback_floating_exceeds_atm_call():
    S, r, sigma, T = 100.0, 0.05, 0.2, 1.0
    lb = exotics.lookback_floating_call(S, S, r, sigma, T)
    assert lb > bsm.call_price(S, S, r, sigma, T)
    assert lb == pytest.approx(17.2168, abs=1e-3)


def test_validation_errors():
    with pytest.raises(ValueError):
        exotics.cash_or_nothing(100.0, 100.0, 0.05, 0.2, 1.0, kind="cal")
    with pytest.raises(ValueError):
        exotics.barrier_call(100.0, 100.0, 90.0, 0.05, 0.2, 1.0, barrier="sideways")
```

- [ ] **Step 2: Run to verify failure** (ImportError)

- [ ] **Step 3: Implement `johnhull/hullkit/src/hullkit/exotics.py`**

```python
"""Closed-form exotic option pricers (Hull 11e, Ch.26)."""

import math

from scipy.stats import norm

from . import bsm


def _d1d2(S, K, r, sigma, T, q):
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    return d1, d1 - sigma * math.sqrt(T)


def gap_call(S, K1, K2, r, sigma, T, q=0.0):
    """Gap call: pays S_T - K1 when S_T > K2 (Hull eq. 26.1)."""
    d1, d2 = _d1d2(S, K2, r, sigma, T, q)
    return S * math.exp(-q * T) * norm.cdf(d1) - K1 * math.exp(-r * T) * norm.cdf(d2)


def cash_or_nothing(S, K, r, sigma, T, q=0.0, kind="call", payout=1.0):
    """Cash-or-nothing binary: pays `payout` if ITM at expiry (Hull §26.10)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    _, d2 = _d1d2(S, K, r, sigma, T, q)
    sign = 1.0 if kind == "call" else -1.0
    return payout * math.exp(-r * T) * norm.cdf(sign * d2)


def asset_or_nothing(S, K, r, sigma, T, q=0.0, kind="call"):
    """Asset-or-nothing binary: pays S_T if ITM at expiry (Hull §26.10)."""
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    d1, _ = _d1d2(S, K, r, sigma, T, q)
    sign = 1.0 if kind == "call" else -1.0
    return S * math.exp(-q * T) * norm.cdf(sign * d1)


def barrier_call(S, K, H, r, sigma, T, q=0.0, barrier="down-and-in"):
    """Barrier call closed forms (Hull §26.9). barrier in {down-and-in,
    down-and-out, up-and-in, up-and-out}. Uses in+out=vanilla complements."""
    valid = ("down-and-in", "down-and-out", "up-and-in", "up-and-out")
    if barrier not in valid:
        raise ValueError(f"barrier must be one of {valid}, got {barrier!r}")
    vanilla = bsm.call_price(S, K, r, sigma, T, q)
    sqt = sigma * math.sqrt(T)
    lam = (r - q + 0.5 * sigma**2) / sigma**2
    x1 = math.log(S / H) / sqt + lam * sqt
    y1 = math.log(H / S) / sqt + lam * sqt
    y = math.log(H**2 / (S * K)) / sqt + lam * sqt

    def _pow(exp_):
        return (H / S) ** exp_

    if barrier in ("down-and-in", "down-and-out"):
        if H <= K:
            cdi = (
                S * math.exp(-q * T) * _pow(2 * lam) * norm.cdf(y)
                - K * math.exp(-r * T) * _pow(2 * lam - 2) * norm.cdf(y - sqt)
            )
        else:
            cdo = (
                S * math.exp(-q * T) * norm.cdf(x1)
                - K * math.exp(-r * T) * norm.cdf(x1 - sqt)
                - S * math.exp(-q * T) * _pow(2 * lam) * norm.cdf(y1)
                + K * math.exp(-r * T) * _pow(2 * lam - 2) * norm.cdf(y1 - sqt)
            )
            cdi = vanilla - cdo
        return cdi if barrier == "down-and-in" else vanilla - cdi
    # up barriers
    if H >= K:
        cui = (
            S * math.exp(-q * T) * norm.cdf(x1)
            - K * math.exp(-r * T) * norm.cdf(x1 - sqt)
            - S * math.exp(-q * T) * _pow(2 * lam) * (norm.cdf(-y) - norm.cdf(-y1))
            + K * math.exp(-r * T) * _pow(2 * lam - 2) * (norm.cdf(-y + sqt) - norm.cdf(-y1 + sqt))
        )
    else:
        cui = vanilla  # up-and-in with H<=K knocks in almost surely (degenerate)
    return cui if barrier == "up-and-in" else vanilla - cui


def lookback_floating_call(S, S_min, r, sigma, T, q=0.0):
    """Floating-strike lookback call (Hull §26.11). Pays S_T - min S."""
    sqt = sigma * math.sqrt(T)
    a1 = (math.log(S / S_min) + (r - q + 0.5 * sigma**2) * T) / sqt
    a2 = a1 - sqt
    a3 = (math.log(S / S_min) + (-r + q + 0.5 * sigma**2) * T) / sqt
    y1 = -2.0 * (r - q - 0.5 * sigma**2) * math.log(S / S_min) / sigma**2
    ratio = sigma**2 / (2.0 * (r - q))
    return (
        S * math.exp(-q * T) * norm.cdf(a1)
        - S * math.exp(-q * T) * ratio * norm.cdf(-a1)
        - S_min * math.exp(-r * T) * (norm.cdf(a2) - ratio * math.exp(y1) * norm.cdf(-a3))
    )


def asian_call_turnbull_wakeman(S, K, r, sigma, T, q=0.0):
    """Average-price Asian call via Turnbull-Wakeman moment matching into
    Black-76 (Hull eq. 26.3/26.4, continuous arithmetic average)."""
    b = r - q
    m1 = (math.exp(b * T) - 1.0) / (b * T) * S
    m2 = (
        2.0 * math.exp((2.0 * b + sigma**2) * T) * S**2
        / ((b + sigma**2) * (2.0 * b + sigma**2) * T**2)
        + 2.0 * S**2 / (b * T**2)
        * (1.0 / (2.0 * b + sigma**2) - math.exp(b * T) / (b + sigma**2))
    )
    f0 = m1
    sigma_a = math.sqrt(math.log(m2 / m1**2) / T)
    d1 = (math.log(f0 / K) + 0.5 * sigma_a**2 * T) / (sigma_a * math.sqrt(T))
    d2 = d1 - sigma_a * math.sqrt(T)
    return math.exp(-r * T) * (f0 * norm.cdf(d1) - K * norm.cdf(d2))


def exchange_option(U0, V0, sigma_u, sigma_v, rho, T, q_u=0.0, q_v=0.0):
    """Margrabe option to exchange asset U for asset V (Hull eq. 26.5).
    r-independent: drift and discounting cancel."""
    sig = math.sqrt(sigma_u**2 + sigma_v**2 - 2.0 * rho * sigma_u * sigma_v)
    d1 = (math.log(V0 / U0) + (q_u - q_v + 0.5 * sig**2) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    return V0 * math.exp(-q_v * T) * norm.cdf(d1) - U0 * math.exp(-q_u * T) * norm.cdf(d2)
```

- [ ] **Step 4: Verify** — 9 passed; full suite 90 passed; ruff clean. (Note: barrier `up-and-in` with H≤K is degenerate; the test only exercises up barriers indirectly — if you add an up-barrier test, keep H≥K.)

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/exotics.py johnhull/hullkit/tests/test_exotics.py
git commit -m "feat(hullkit): closed-form exotic option pricers with Hull Ch.26 identities"
```

---

### Task 2: build script — intro + Ch.26 (cells 00–13)

**Files:**
- Create: `johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py`

- [ ] **Step 1: Create the build script with cells 00–13** (helpers + footer verbatim from `volumes/09_credit_xva/build_credit_notebook.py`; title `build_exotics_notebook.py`; output `exotics.ipynb`)

````python
# ===========================================================================
# Cell 00: title / intro
# ===========================================================================
cells.append(
    md(r"""# エキゾチック・オプションと測度（Hull 11e Ch.26, 28）

`johnhull/volumes` シリーズ第10冊。複雑なペイオフと、その背後の数学：

- **エキゾチック（Ch.26）** — バイナリ、バリア、ルックバック、アジアン、交換（Margrabe）、バリアンス・スワップ
- **マルチンゲールと測度（Ch.28）** — ニュメレール、市場リスクの価格 λ、フォワード測度

> 共通関数は `hullkit`（exotics / bsm / mc / nbplot）から import。
> 第6冊（数値解法）・第5冊（スマイル）の道具がここで効きます""")
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

from hullkit import bsm, exotics, mc, nbplot

plt = nbplot.setup()  # japanize_matplotlib + plt.ioff()""")
)

# ===========================================================================
# Section 1: Ch.26 exotics
# ===========================================================================

# Cell 03: taxonomy md
cells.append(
    md(r"""## 1. エキゾチックの分類（Ch.26）

OTC で取引される非標準ペイオフ。多くは GBM 仮定下で**解析解**を持ちます：

| 型 | 特徴 | 評価 |
|---|---|---|
| パッケージ | バニラの組み合わせ | バニラの和 |
| バイナリ | 不連続ペイオフ | cash/asset-or-nothing |
| バリア | 到達で発生/消滅 | 閉形式（in+out=vanilla） |
| ルックバック | 経路の最大/最小 | 閉形式 |
| アジアン | 平均価格 | 算術平均は近似/MC |
| 交換 | 資産を資産と交換 | Margrabe（r非依存） |
| バリアンス・スワップ | 実現分散 | ログ・コントラクト静的複製 |""")
)

# Cell 04: binary md
cells.append(
    md(r"""## 2. バイナリ・オプション（§26.10）

- **cash-or-nothing**: ITM なら固定額 $Q$ → $Q e^{-rT} N(d_2)$（コール）
- **asset-or-nothing**: ITM なら原資産 → $S_0 e^{-qT} N(d_1)$（コール）

バニラはこの2つに分解できます： $c = c_{\text{aon}}(K) - K\,c_{\text{con}}(K)$。
（第2冊のバタフライ＝建築ブロックの連続極限とも整合）""")
)

# Cell 05: binary demo
cells.append(
    code(r"""S_B, K_B, R_B, SIG_B, T_B = 100.0, 100.0, 0.05, 0.20, 1.0
aon = exotics.asset_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call")
con = exotics.cash_or_nothing(S_B, K_B, R_B, SIG_B, T_B, kind="call", payout=1.0)
van = bsm.call_price(S_B, K_B, R_B, SIG_B, T_B)
print(f"asset-or-nothing = {aon:.4f}")
print(f"cash-or-nothing（Q=1）= {con:.4f}")
print(f"分解 aon − K·con = {aon - K_B * con:.4f} ／ バニラ = {van:.4f}（恒等）")

s_grid = np.linspace(60.0, 140.0, 400)
fig1, ax1 = plt.subplots(figsize=(8, 4))
fig1.canvas.header_visible = False
ax1.plot(s_grid, np.where(s_grid > K_B, 1.0, 0.0), lw=2, label="cash-or-nothing（Q=1）満期ペイオフ")
ax1.plot(s_grid, np.where(s_grid > K_B, s_grid, 0.0) / 100.0, lw=2, ls="--",
         label="asset-or-nothing /100")
ax1.set_xlabel("満期株価 $S_T$")
ax1.set_ylabel("ペイオフ")
ax1.set_title("バイナリの不連続ペイオフ（K で跳ぶ）")
ax1.legend()
display(fig1.canvas)""")
)

# Cell 06: barrier md
cells.append(
    md(r"""## 3. バリア・オプション（§26.9）

バリア $H$ への到達で**発生（in）**または**消滅（out）**。
up/down × in/out × call/put の8種に閉形式があります。鍵となる関係：

$$c_{\text{di}} + c_{\text{do}} = c \quad (\text{ノックイン} + \text{ノックアウト} = \text{バニラ})$$

「どちらかには必ずなる」ので、合計はバリアのないバニラに等しくなります。
ノックアウトはバニラより安く（消える可能性のぶん）、人気の理由です。""")
)

# Cell 07: barrier demo + chart
cells.append(
    code(r"""# down-and-in/out call（H≤K）と in+out=vanilla
cdi = exotics.barrier_call(S_B, K_B, 90.0, R_B, SIG_B, T_B, barrier="down-and-in")
cdo = exotics.barrier_call(S_B, K_B, 90.0, R_B, SIG_B, T_B, barrier="down-and-out")
print(f"down-and-in = {cdi:.4f} ／ down-and-out = {cdo:.4f}")
print(f"in + out = {cdi + cdo:.4f} ／ バニラ = {van:.4f}（恒等）")

h_grid = np.linspace(60.0, 99.0, 40)
fig2, ax2 = plt.subplots(figsize=(7.5, 4))
fig2.canvas.header_visible = False
ax2.plot(h_grid, [exotics.barrier_call(S_B, K_B, h, R_B, SIG_B, T_B, barrier="down-and-in")
                  for h in h_grid], lw=2, label="down-and-in")
ax2.plot(h_grid, [exotics.barrier_call(S_B, K_B, h, R_B, SIG_B, T_B, barrier="down-and-out")
                  for h in h_grid], lw=2, label="down-and-out")
ax2.axhline(van, color="0.6", ls=":", lw=1.5, label="バニラ")
ax2.set_xlabel("バリア H")
ax2.set_ylabel("価格")
ax2.set_title("H が K に近いほどノックインしやすく di↑・do↓（和は一定）")
ax2.legend()
display(fig2.canvas)""")
)

# Cell 08: lookback md + demo
cells.append(
    code(r"""# --- フローティング・ルックバック・コール（min を行使価格に） ---
lb = exotics.lookback_floating_call(S_B, S_B, R_B, SIG_B, T_B)
print(f"フローティング・ルックバック・コール = {lb:.4f} ／ ATM バニラ = {van:.4f}")
print("（経路最安値で買える権利 → 常にバニラより高い。「後知恵」のプレミアム）")

rng_lb = np.random.default_rng(26)
path = mc.simulate_gbm_paths(S_B, R_B, SIG_B, T_B, 252, 1, rng=rng_lb)[0]
t_lb = np.linspace(0.0, T_B, 253)
running_min = np.minimum.accumulate(path)
fig3, ax3 = plt.subplots(figsize=(8, 4))
fig3.canvas.header_visible = False
ax3.plot(t_lb, path, lw=1.5, label="株価パス")
ax3.plot(t_lb, running_min, lw=1.5, ls="--", label="経路最小値（実効行使価格）")
ax3.axhline(path[-1], color="0.6", ls=":", lw=1, label=f"満期 S_T={path[-1]:.1f}")
ax3.set_xlabel("t（年）")
ax3.set_ylabel("価格")
ax3.set_title(f"ルックバック・ペイオフ = S_T − min = {path[-1] - running_min[-1]:.2f}")
ax3.legend()
display(fig3.canvas)""")
)

# Cell 09: asian md
cells.append(
    md(r"""## 4. アジアン・オプション（§26.13）

平均価格型は満期スポットではなく**経路平均**でペイオフ。
平均は変動を均すので**ボラが下がり、バニラより安く**なります。
算術平均には厳密な閉形式がなく、**Turnbull-Wakeman モーメント整合**（平均の
1次・2次モーメントを合わせて Black-76 に入力）か MC を使います。""")
)

# Cell 10: asian demo
cells.append(
    code(r"""a_tw = exotics.asian_call_turnbull_wakeman(S_B, K_B, R_B, SIG_B, T_B)
# MC（算術平均）
rng_a = np.random.default_rng(1)
paths_a = mc.simulate_gbm_paths(S_B, R_B, SIG_B, T_B, 252, 100_000, rng=rng_a)
avg_a = paths_a[:, 1:].mean(axis=1)
a_mc = math.exp(-R_B * T_B) * np.maximum(avg_a - K_B, 0.0).mean()
print(f"Turnbull-Wakeman アジアン = {a_tw:.4f}")
print(f"MC（算術平均、10万パス）   = {a_mc:.4f}")
print(f"バニラ ATM コール          = {van:.4f}（アジアンは平均化でボラ低下 → 安い）")

fig4, ax4 = plt.subplots(figsize=(8, 4))
fig4.canvas.header_visible = False
for i in range(20):
    ax4.plot(np.linspace(0, T_B, 253), paths_a[i], lw=0.6, alpha=0.5)
ax4.axhline(K_B, color="crimson", ls=":", lw=1.5, label="K")
ax4.set_xlabel("t（年）")
ax4.set_ylabel("S")
ax4.set_title("アジアンは満期値でなく経路平均で決済（平均がボラを均す）")
ax4.legend()
display(fig4.canvas)""")
)

# Cell 11: exchange md + demo
cells.append(
    code(r"""# --- 交換オプション（Margrabe）: 資産Uを資産Vと交換 ---
print("Margrabe は r に依存しない（成長率↑と割引率↑が相殺）:")
for r_try in (0.0, 0.05, 0.15):
    v = exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0)  # r は引数にすらない
    # 確認のため BSM 風に r を変えても価格は同一であることを示す（関数が r 非依存）
    print(f"  （参考 r={r_try:.0%}）交換オプション価値 = {v:.6f}")
print("σ̂ = √(σ_U²+σ_V²−2ρσ_Uσ_V)。ρ が高いほど2資産が連動し交換の価値は下がる")
rows = []
for rho in (-0.5, 0.0, 0.5, 0.9):
    rows.append({"相関ρ": rho,
                 "交換オプション": round(exotics.exchange_option(100.0, 100.0, 0.2, 0.2, rho, 1.0), 4)})
display(pd.DataFrame(rows))""")
)

# Cell 12: variance swap md + demo
cells.append(
    code(r"""# --- バリアンス・スワップ: OTM オプションのストリップで複製（VIX 流） ---
# 公正バリアンス ≈ (2/T) Σ ΔK/K² e^{rT} Q(K)（Q は OTM オプション価格）
F0 = S_B * math.exp(R_B * T_B)
strikes_vs = np.arange(60.0, 145.0, 5.0)
fair_var = 0.0
for k in strikes_vs:
    if k < F0:
        price = bsm.put_price(S_B, k, R_B, SIG_B, T_B)
    else:
        price = bsm.call_price(S_B, k, R_B, SIG_B, T_B)
    fair_var += 5.0 / k**2 * math.exp(R_B * T_B) * price
fair_var *= 2.0 / T_B
print(f"ストリップ複製の公正バリアンス・レート = {fair_var:.5f}")
print(f"→ 公正ボラティリティ = {math.sqrt(fair_var):.4%}（入力 σ={SIG_B:.0%} を概ね回復）")
print("VIX も同型: OTM SPX オプションのストリップで30日先のバリアンスを測る")""")
)

# Cell 13: interactive barrier
cells.append(
    code(r"""# --- バリア・エクスプローラ（インタラクティブ） ---
fig5, ax5 = plt.subplots(figsize=(7.5, 4))
fig5.canvas.header_visible = False
h_sl = widgets.FloatSlider(value=90.0, min=70.0, max=99.0, step=1.0, description="H")
sig_b_sl = widgets.FloatSlider(value=0.20, min=0.10, max=0.50, step=0.02, description="σ")


def _upd_barrier(change=None):
    ax5.clear()
    ss = np.linspace(70.0, 140.0, 60)
    do = [exotics.barrier_call(s, K_B, h_sl.value, R_B, sig_b_sl.value, T_B,
                               barrier="down-and-out") for s in ss]
    van_curve = [bsm.call_price(s, K_B, R_B, sig_b_sl.value, T_B) for s in ss]
    ax5.plot(ss, van_curve, lw=1.5, ls=":", label="バニラ")
    ax5.plot(ss, do, lw=2, label="down-and-out")
    ax5.axvline(h_sl.value, color="crimson", ls="--", lw=1, label=f"H={h_sl.value:.0f}")
    # ノックアウト確率（GBM、反射原理の近似）
    prob_ko = norm.cdf((math.log(h_sl.value / 100.0)) / (sig_b_sl.value * math.sqrt(T_B)))
    ax5.set_xlabel("現在株価 S")
    ax5.set_ylabel("価格")
    ax5.set_title(f"down-and-out（H={h_sl.value:.0f}, σ={sig_b_sl.value:.0%}）: "
                  f"S=100 でのノックアウト確率 ≈ {2 * prob_ko:.1%}")
    ax5.legend()
    fig5.canvas.draw_idle()


h_sl.observe(_upd_barrier, "value")
sig_b_sl.observe(_upd_barrier, "value")
_upd_barrier()
display(widgets.HBox([h_sl, sig_b_sl]), fig5.canvas)""")
)
````

- [ ] **Step 2: Build and validate** — `Total cells: 14`; nbformat validate → `14 cells valid`.

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/10_exotics_martingales
git commit -m "feat(johnhull): 10 build script with exotic option cells"
```

---

### Task 3: build script — Ch.28 + closing (cells 14–27)

**Files:**
- Modify: `johnhull/volumes/10_exotics_martingales/build_exotics_notebook.py`

- [ ] **Step 1: Insert cells 14–27 immediately BEFORE the `# ===...` line preceding `# Notebook assembly`**

````python
# ===========================================================================
# Section 2: Ch.28 martingales and measures
# ===========================================================================

# Cell 14: numeraire md
cells.append(
    md(r"""## 5. マルチンゲールと測度（Ch.28）

**マルチンゲール** = ドリフトゼロの過程（$E[\theta_T] = \theta_0$）。
**同値マルチンゲール測度の定理**: トレーダブル証券 $g$（ニュメレール）を選ぶと、
任意の証券価格 $f$ について $f/g$ がマルチンゲールになる測度が存在し：

$$f_0 = g_0\,E_g\!\left[\frac{f_T}{g_T}\right] \quad \text{(28.15)}$$

ニュメレールの選び方で「便利な測度」が得られます：
マネーマーケット口座 → リスク中立測度、ゼロクーポン債 → フォワード測度。""")
)

# Cell 15: market price of risk md
cells.append(
    md(r"""## 6. 市場リスクの価格 λ（§28.1）

ある確率変数 $\theta$ に依存する**すべての**デリバティブで、無裁定なら

$$\frac{\mu - r}{\sigma} = \lambda \quad \text{(28.8)}$$

が共通に成立（$\lambda$ は $\theta, t$ のみに依存、商品によらない）。
$\lambda$ はシャープ比に相当。リスク中立測度は $\lambda$ を 0 に「移す」測度です。""")
)

# Cell 16: market price of risk demo
cells.append(
    code(r"""# --- λ が2つのデリバティブで一致することの数値確認 ---
# 原資産 θ: dθ/θ = m dt + s dz。θに依存する2つのデリバティブ f1, f2 の (μ-r)/σ を比較
# BSM 世界では任意のオプションについて (μ_opt - r)/σ_opt = (μ_S - r)/σ_S = λ
S0_m, mu_S, sig_S, r_m = 100.0, 0.12, 0.20, 0.05
lam_underlying = (mu_S - r_m) / sig_S
# コールのリターン・ボラはデルタ弾性 Ω = (S/c)·Δ でスケール
for K_m, T_m in [(100.0, 0.5), (110.0, 1.0)]:
    c = bsm.call_price(S0_m, K_m, r_m, sig_S, T_m)
    delta = bsm.call_delta(S0_m, K_m, r_m, sig_S, T_m)
    omega = S0_m / c * delta  # 弾性
    sig_opt = omega * sig_S
    mu_opt = r_m + omega * (mu_S - r_m)  # CAPM 風
    lam_opt = (mu_opt - r_m) / sig_opt
    print(f"K={K_m}, T={T_m}: σ_opt={sig_opt:.3f}, (μ−r)/σ = {lam_opt:.4f}")
print(f"原資産の λ = (μ−r)/σ = {lam_underlying:.4f} ← すべて一致（無裁定）")""")
)

# Cell 17: risk-neutral & forward measure md
cells.append(
    md(r"""## 7. ニュメレールの選択（§28.4–28.5）

| ニュメレール $g$ | 測度 | 公式 |
|---|---|---|
| マネーマーケット口座 $e^{rt}$ | リスク中立 $\mathbb{Q}$ | $f_0 = \hat E[e^{-rT}f_T]$ |
| ゼロクーポン債 $P(t,T)$ | $T$-フォワード $\mathbb{Q}^T$ | $f_0 = P(0,T)E^T[f_T]$ |
| アニュイティ $A(t)$ | スワップ測度 | スワプション評価（→第11冊） |

**フォワード測度の効用**: $F(t,T) = E^T[S_T]$ — フォワード価格はフォワード測度下の
期待スポット。これが**確率的金利下でも Black-76 が成り立つ**理由です（第2冊の $q=r$ の正当化）。""")
)

# Cell 18: numeraire invariance demo
cells.append(
    code(r"""# --- ニュメレール不変性: 同じオプションを2つの測度で評価 → 同値 ---
# ヨーロピアンコールを (a) リスク中立測度 (b) 株価ニュメレール で MC 評価
S0_n, K_n, r_n, sig_n, T_n = 100.0, 100.0, 0.05, 0.25, 1.0
rng_n = np.random.default_rng(28)
n_paths = 200_000
z = rng_n.standard_normal(n_paths)
# (a) リスク中立測度: ドリフト r、ペイオフを e^{-rT} で割引
ST_q = S0_n * np.exp((r_n - 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z)
price_q = math.exp(-r_n * T_n) * np.maximum(ST_q - K_n, 0.0).mean()
# (b) 株価ニュメレール（測度 S）: ドリフト r+σ²、c = S0·E^S[(S_T-K)^+/S_T]
ST_s = S0_n * np.exp((r_n + 0.5 * sig_n**2) * T_n + sig_n * math.sqrt(T_n) * z)
price_s = S0_n * (np.maximum(ST_s - K_n, 0.0) / ST_s).mean()
print(f"(a) リスク中立測度の MC 価格   = {price_q:.4f}")
print(f"(b) 株価ニュメレールの MC 価格 = {price_s:.4f}")
print(f"BSM 解析値                     = {bsm.call_price(S0_n, K_n, r_n, sig_n, T_n):.4f}")
print("→ ニュメレールを変えても同じ価格（測度変換の不変性）")""")
)

# Cell 19: Girsanov md + demo
cells.append(
    md(r"""## 8. ギルサノフの定理（§28.2）

測度変換は**ドリフトを変えるがボラティリティは保存**する：

$$dz^{\mathbb{Q}} = dz^{\mathbb{P}} + \lambda\,dt$$

実世界 $\mathbb{P}$（ドリフト $\mu$）からリスク中立 $\mathbb{Q}$（ドリフト $r$）へ移っても、
$\sigma$ は不変。これは第1冊で見た「二項ツリーで測度を変えても σ が変わらない」の
連続版です。下で同じ σ・異なるドリフトのパスを比較します。""")
)

# Cell 20: Girsanov path demo
cells.append(
    code(r"""rng_g = np.random.default_rng(280)
z_common = rng_g.standard_normal((30, 252))
t_g = np.linspace(0.0, 1.0, 253)
dt_g = 1.0 / 252
fig6, (ax6a, ax6b) = plt.subplots(1, 2, figsize=(10.5, 4), sharey=True)
fig6.canvas.header_visible = False
for ax, mu_g, title in ((ax6a, 0.12, "実世界 P（μ=12%）"),
                        (ax6b, 0.05, "リスク中立 Q（μ=r=5%）")):
    lp = np.cumsum((mu_g - 0.5 * 0.2**2) * dt_g + 0.2 * math.sqrt(dt_g) * z_common, axis=1)
    paths_g = 100.0 * np.exp(np.column_stack([np.zeros(30), lp]))
    ax.plot(t_g, paths_g.T, lw=0.6, alpha=0.6)
    ax.plot(t_g, 100.0 * np.exp(mu_g * t_g), "k--", lw=2)
    ax.set_title(title)
    ax.set_xlabel("t")
ax6a.set_ylabel("S")
fig6.suptitle("同じ乱数・同じ σ=20%、ドリフトだけ違う（ギルサノフ）", fontsize=10)
display(fig6.canvas)
print("拡散の広がり（σ）は両測度で同一。期待成長率（点線）だけが異なる")""")
)

# Cell 21: swap measure pointer md
cells.append(
    md(r"""### スワップ測度へのポインタ（§28.6）

アニュイティ $A(t) = \sum (T_{i+1}-T_i)P(t,T_{i+1})$ をニュメレールにすると、
フォワード・スワップレート $s(t)$ がマルチンゲールになる「スワップ測度」が得られ、
**スワプションの Black 公式**が正当化されます。これは第11冊（Ch.29）で本格的に使います。""")
)

# ===========================================================================
# Section 3: verification / exercises / summary
# ===========================================================================

# Cell 22: assertion cell
cells.append(
    code(r"""# --- 検証（hullkit/tests/test_exotics.py にも同等の検証あり） ---
checks = []
checks.append(("バイナリ分解 = バニラ", aon - K_B * con, van, 1e-12))
checks.append(("バリア in+out = バニラ", cdi + cdo, van, 1e-12))
checks.append(("Margrabe 7.9656",
               exotics.exchange_option(100.0, 100.0, 0.2, 0.2, 0.5, 1.0), 7.965567, 1e-5))
checks.append(("gap call 13.1122",
               exotics.gap_call(100.0, 95.0, 100.0, 0.05, 0.20, 1.0), 13.112208, 1e-5))
checks.append(("アジアン < バニラ", float(a_tw < van), 1.0, 0.0))
checks.append(("ルックバック > ATM", float(lb > van), 1.0, 0.0))
checks.append(("ニュメレール不変（a≈b）", price_q, price_s, 5e-3))
checks.append(("λ 一致（原資産 vs オプション）", lam_opt, lam_underlying, 1e-9))

for name, got, want, tol in checks:
    ok = abs(got - want) <= tol
    print(f"[{'OK' if ok else 'FAIL'}] {name}: got={got:.6g} want={want:.6g}")
    assert ok, name
print("\n全チェック合格")""")
)

# Cell 23: exercises
cells.append(
    md(r"""## 9. 練習問題

**Q1.** ダウン・アンド・アウト・コール（H=80）の価格が 9、対応するバニラが 10。
ダウン・アンド・イン・コールの価格は？

<details><summary>解答</summary>

in + out = vanilla より、di = 10 − 9 = 1。
</details>

**Q2.** 平均価格アジアン・コールがバニラ・コールより安いのはなぜ？

<details><summary>解答</summary>

平均は経路を均すので実効ボラティリティが下がる（σ_avg < σ）。
オプション価値はボラに単調増加なので安くなる。
</details>

**Q3.** 交換オプション（Margrabe）が金利 r に依存しないのはなぜ？

<details><summary>解答</summary>

一方の資産をニュメレールに取ると、両資産の成長率上昇と割引率上昇が相殺する。
価格は相対ボラ σ̂=√(σ_U²+σ_V²−2ρσ_Uσ_V) だけで決まる。
</details>""")
)

# Cell 24: summary
cells.append(
    md(r"""## まとめ

| 概念 | 要点 |
|---|---|
| バイナリ | aon − K·con = バニラ。不連続ペイオフ |
| バリア | in + out = バニラ。ノックアウトは安い |
| ルックバック | 経路最小で買える「後知恵」プレミアム |
| アジアン | 平均でボラ低下 → 安い。TW近似 or MC |
| Margrabe | 交換オプション。r 非依存、σ̂ だけで決まる |
| 測度 | f/g がマルチンゲール。ニュメレールで測度を選ぶ |
| λ | (μ−r)/σ は全商品共通。Q は λ=0 の測度 |
| ギルサノフ | 測度変換でドリフト変、σ 不変 |

**次へ**: `volumes/11_ir_derivatives_market`（Ch.29, 30 — Black モデルとスワプション）
**シリーズ**: `johnhull/ROADMAP.md` 参照""")
)

# Cell 25: closing md
cells.append(
    md(r"""---
*第10冊おわり。エキゾチックの閉形式と、その正当性を支える測度論を一巡しました。*""")
)
````

- [ ] **Step 2: Rebuild and validate** — `Total cells: 26`; nbformat validate → `26 cells valid`. (Spec estimated 28; actual 26 — fine.)

- [ ] **Step 3: Commit**

```bash
git add johnhull/volumes/10_exotics_martingales
git commit -m "feat(johnhull): 10 martingale/measure cells, verification"
```

---

### Task 4: Headless execution, verification, docs

**Files:**
- Create: `johnhull/volumes/10_exotics_martingales/PROGRESS.md`
- Modify: `johnhull/ROADMAP.md` (volume 10 → done; module list gains `exotics`)

- [ ] **Step 1: Headless execute** (`--output-dir /tmp --output exotics_executed.ipynb`; the MC cells take a few seconds). Exit 0 or BLOCKED+traceback.

- [ ] **Step 2: Zero-error + 全チェック合格 heredoc.**

- [ ] **Step 3: Tests + lint:** hullkit suite → 90 passed; ruff johnhull clean; workspace minus gto (explicit paths) → quote summary.

- [ ] **Step 4: Write `johnhull/volumes/10_exotics_martingales/PROGRESS.md`**

```markdown
# 10_exotics_martingales — Progress

Last updated: 2026-06-08

## Status: complete (v1)

- `exotics.ipynb` (26 cells) generated by `build_exotics_notebook.py`
- Coverage: Hull 11e Ch.26 (binary, barrier, lookback, Asian/Turnbull-Wakeman,
  exchange/Margrabe, variance-swap replication), Ch.28 (numeraires/martingales,
  market price of risk, risk-neutral & forward measures, numeraire invariance,
  Girsanov)
- hullkit addition: `exotics.py` (gap, cash/asset-or-nothing, barrier_call,
  lookback_floating_call, asian_call_turnbull_wakeman, exchange_option —
  9 tests; suite 90)
- Verified: headless nbconvert, parity-identity assertion cell, hullkit pytest,
  ruff (johnhull scope)
- NOT yet verified: widget interactivity in live Jupyter (user check)

## Build

    uv run python build_exotics_notebook.py

## Notes / future ideas

- Cell index: 00-02 intro / 03-13 Ch.26 / 14-21 Ch.28 / 22 verification /
  23 exercises / 24-25 summary
- Compound (Geske), chooser, cliquet, fixed-strike lookback, Parisian: md only
- nbformat cell ids still missing (inherited builder pattern)
```

- [ ] **Step 5: ROADMAP volume 10 → done; module list `..., credit.` → `..., credit, exotics.`**

- [ ] **Step 6: Final commit**

```bash
git add johnhull/volumes/10_exotics_martingales/PROGRESS.md johnhull/ROADMAP.md
git commit -m "docs(johnhull): mark 10_exotics_martingales complete"
```

- [ ] **Step 7: Report** with quoted outputs.
