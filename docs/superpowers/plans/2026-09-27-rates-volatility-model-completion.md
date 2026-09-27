# rates_volatility_model Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `rates_volatility_model` correct and verifiable: fix the model bugs found in the 2026-09-27 review, move the model code into a tested package that the notebook imports, and retire the broken generator pipeline and stale docs.

**Architecture:** A small src-layout package `ratesvol` (six modules: options, curves, short_rate, market_models, smile, rfr) holds every model function, each pinned by pytest against closed forms, no-arbitrage identities, or an independent implementation. The single notebook `rates_volatility_models.ipynb` becomes the only notebook source; its cells import from `ratesvol` and keep only plotting and narrative. A headless notebook-execution test forces ipywidgets callbacks to run and raise, so interactive cells can no longer fail silently.

**Tech Stack:** Python 3.12, NumPy ≥ 2.0, SciPy, matplotlib, ipywidgets, nbformat / nbclient, pytest, ruff, uv workspace (root `/home/kazumasa/projects`).

**Spec:** This plan has no separate spec. The "Review findings" section below is the spec: every finding names the task that fixes it, and `rates_volatility_model/docs/STATUS.md` (created in Task 8) carries the same table forward.

**Provenance:** Every code block in this plan was run on 2026-09-27 against a scratch copy of the repository: 60 unit tests + 1 notebook-execution test passed, `ruff check` and `ruff format --check` were clean on the new `.py` files, and the three notebook-rewire scripts were applied in order to the committed notebook and produced a notebook that executes without errors.

## Review findings (the spec)

| # | Where (cell id) | Defect | Evidence | Fixed in |
|---|---|---|---|---|
| 1 | HJM `e59676d6` | Drift integrates σ over [T, T_max] instead of [t, T] although the comment says "CORRECTED" | σ = 1%: α(0, 10y) = 0 (correct 1.0e-3), α(0, 0.1y) = 9.9e-4 (correct 1.0e-5) | Task 3, Task 6 |
| 2 | HJM `e59676d6` / `b1207d2e` | `np.trapz` no longer exists in NumPy 2.4.6 (workspace version) → `AttributeError`. ipywidgets `interact` swallows it, so a headless run reports 0 errors | A plain `nbconvert --execute` shows no error; calling the HJM function directly raises | Task 5, Task 6 |
| 3 | LMM `5bd8fa3b`, `5ac8a9d6` | Two definitions (the second sits under the SABR heading); the first sums k > j with a + sign (neither spot nor terminal measure); forwards keep moving after their fixing; the old validation claimed E[L] = L, which is false under the spot measure | read of both cells | Task 3, Task 6 |
| 4 | `test_suite_validation.py` | Tests its own re-implementations, not the notebook code; its SABR (`hagan_sabr_t8`) has wrong correction terms (α²/(FK)^{2(1-β)}, ρβν/(4α)) | "8/8 PASS" says nothing about the notebook | Tasks 1–4, Task 8 |
| 5 | Ch1 `5066fcf0`, Ch2 `7eca6d1b` | Bachelier vega printed "per 1bp vol" but is per unit of vol (1e4× off); Black-76 gamma printed "per 1%" but is per unit of F | output: `Vega: 0.398942 (per 1bp vol)` | Task 1, Task 5 |
| 6 | Ch0 `83c49f15` | Instantaneous forward computed as z + dz/dT (missing ×T) | code read | Task 2, Task 5 |
| 7 | Vasicek `d96aa475`, G2++ `7aaa0880` | Normal pdf in decimal units drawn over a %-axis histogram: density 100× off | code read | Task 5 |
| 8 | Vasicek calibration `33ad2205` | r0 fixed to the 6M zero rate → 21bp miss at the front; no note that b and σ are not identifiable from a curve alone | output: `T= 0.5y ... Diff=21.2bps` | Task 2, Task 5 |
| 9 | G2++ `41457d7d` | φ(t) is a constant 2%, not fitted to the curve, although the text and comparison table say "Auto curve fit" | code read | Task 2, Task 5 |
| 10 | SABR `a17337d8`, `c63a99a0`, `dfe9c5f8` | α described as vol-of-vol; weakness listed as "short maturities" (it is long maturities / low strikes); slider sets α = x% of F so moving β moves the ATM level wildly | markdown read | Task 6 |
| 11 | RFR `681b951c`, `b726fb30`, `13b8e5aa` | No compounding calculation at all (old docs claimed "SOFR compounding"); SONIA and €STR described as policy rates; "RFR = single curve"; a "Smile" row with no meaning | markdown/code read | Task 4, Task 6 |
| 12 | SVI `72c873ee`, `407804ce` | Only the slope bound is checked (text says 4/T, code says 4 in total-variance form); it is necessary, not sufficient; no g(k) check | Vogt example satisfies the bound but has g(k) < 0 | Task 4, Task 7 |
| 13 | 25Δ metrics `ea85e730` | 25Δ strikes solved with the ATM vol instead of the smile vol at that strike | code read | Task 4, Task 7 |
| 14 | `9417952b`, `eab070d5`, `d0147609` | SABR formula defined three times (plus a fourth, wrong, copy in the old test file); a SABR demo cell sits inside the RFR chapter | code read | Task 6, Task 7 |
| 15 | generator pipeline | `generate_notebook_part1.py` does not exist; appendices A/B exist only in the merged notebook, so re-running `merge_notebooks.py` deletes 7 cells | file listing | Task 8 |
| 16 | docs | `VALIDATION_SUMMARY.md` (46 cells / 86 KB / 6 tests / "完了", dated 2024) and `SABR_CORRECTION.md` (a simplified SABR that is not used) do not match reality; `venv/` is an empty environment; README is 2 lines | file read | Task 8 |
| 17 | CIR `f3029894`, `c3dca17a` | Feller condition described as the non-negativity condition (CIR is always ≥ 0; Feller is the condition for never hitting 0) | markdown read | Task 5 |

## Definition of done

1. `PYTHONPATH=rates_volatility_model/src $PY -m pytest rates_volatility_model/tests` → `61 passed` (60 unit + 1 notebook execution).
2. No model function is defined inside the notebook: `grep -c "def hagan_sabr\|def lmm_forward\|def hjm_forward\|def vasicek_path\|def cir_path\|def g2pp_path\|np.trapz" rates_volatility_model/rates_volatility_models.ipynb` → `0`.
3. Every row of the review table is fixed by the task named in it.
4. `rates_volatility_model/` contains only: `pyproject.toml`, `README.md`, `.gitignore`, `docs/STATUS.md`, `rates_volatility_models.ipynb`, `src/ratesvol/*.py`, `tests/*.py` (plus the untracked, ignored `venv/`, see Task 8 step 9).

## Global Constraints

- Python ≥ 3.12, `numpy>=2.0` (`np.trapezoid`; `np.trapz` is gone in the workspace's NumPy 2.4.6).
- No new third-party dependency: only packages already in the workspace lock (numpy, scipy, matplotlib, pandas, japanize-matplotlib, ipywidgets, ipykernel, jupyterlab, nbformat, nbclient).
- Distribution name `rates-volatility-model`, import name `ratesvol`, src layout, hatchling build.
- Units: rates and vols are decimals (0.03 = 3%); bp = ×1e4. Function names carry non-unit scaling (`*_per_bp`, `*_per_vol_pt`).
- Randomness: every simulator takes a `numpy.random.Generator` argument; the notebook creates one `RNG = np.random.default_rng(42)` in Ch0 and never calls `np.random.seed`.
- Language: notebook prose Japanese; code, identifiers and commit messages English (workspace `AGENTS.md`).
- Scope: touch only `rates_volatility_model/`, the root `pyproject.toml`, `uv.lock`, the root `Makefile` comment/help lines and the root `README.md` rows named in Task 8. Nothing else.
- Shared `.venv`: never run a plain (exact) `uv sync`; it can uninstall packages other sessions rely on. Inside the worktree do not sync at all — run tests with the main `.venv` interpreter and `PYTHONPATH`. Only after the merge, run `uv sync --all-packages --inexact` in the main tree (Task 8 step 9).
- Edit notebook cells by cell id (ids are stable; indices shift when cells are deleted).
- Commit on the feature branch only. Do not push. End each commit message with the attribution trailer lines the harness specifies for the session.

## Review Focus

1. **Negative forwards in Bachelier implied vol** — a user inverting a price at F = −0.20% expects the normal vol back, not nan. Test: `test_bachelier_implied_vol_works_for_negative_forwards` (Task 1).
2. **Tiny deep-OTM prices in Black implied vol** — a price of 1e-12 must give a finite vol, not an exception from the root bracket. Test: `test_black76_implied_vol_of_a_tiny_deep_otm_price_is_finite` (Task 1).
3. **CIR with the Feller condition violated** — the slider allows it; paths must touch 0 but never go below. Test: `test_cir_stays_non_negative_when_feller_fails` (Task 2).
4. **LMM with irregular accrual periods** — τ_j differ (0.25y, 0.5y, 1y); the spot-measure drift must still reprice bonds. Test: `test_lmm_irregular_tenors_reprice_the_last_bond` (Task 3).
5. **Extreme SABR slider settings in the smile-metrics panels** — e.g. 10Y, β = 1, ρ = 0.9, ν = 1.5: the 25Δ strike cannot be bracketed; the panel must show nan RR/BF, not crash the widget. Test: `test_smile_metrics_return_nan_when_delta_cannot_be_bracketed` (Task 4).

---

## File structure

| Path (under `rates_volatility_model/`) | Responsibility |
|---|---|
| `pyproject.toml` | workspace member definition |
| `src/ratesvol/__init__.py` | package marker |
| `src/ratesvol/options.py` | Black-76 / Bachelier prices, Greeks with explicit units, implied vols |
| `src/ratesvol/curves.py` | discount factors, instantaneous and simple forwards |
| `src/ratesvol/short_rate.py` | Vasicek, CIR, Hull-White 1F, G2++ (simulation, bond prices, calibration, curve fit) |
| `src/ratesvol/market_models.py` | HJM drift and simulation, spot-measure LMM, spot numeraire |
| `src/ratesvol/smile.py` | SABR (Hagan 2002), SABR calibration, raw SVI with g(k), smile-consistent 25Δ metrics |
| `src/ratesvol/rfr.py` | compounded-in-arrears overnight rate |
| `tests/test_*.py` | one test file per module + `test_notebook_executes.py` |
| `rates_volatility_models.ipynb` | the notebook (rewired in Tasks 5–7) |
| `README.md`, `docs/STATUS.md` | project docs (Task 8) |

Deleted in Task 8: `generate_notebook_part2.py`, `generate_notebook_part3.py`, `generate_notebook_smile.py`, `merge_notebooks.py`, `rates_volatility_models_part1.ipynb`, `rates_volatility_models_part2.ipynb`, `rates_volatility_models_part3.ipynb`, `rates_volatility_models_smile.ipynb`, `test_suite_validation.py`, `SABR_CORRECTION.md`, `VALIDATION_SUMMARY.md`.

---

### Task 1: Package scaffold, workspace registration, option formulas

**Files:**
- Create: `rates_volatility_model/pyproject.toml`
- Create: `rates_volatility_model/src/ratesvol/__init__.py`
- Create: `rates_volatility_model/src/ratesvol/options.py`
- Create: `rates_volatility_model/tests/test_options.py`
- Modify: `pyproject.toml` (root): `[tool.uv.workspace].members`, `[tool.pytest.ini_options].testpaths`
- Modify: `uv.lock` (regenerated by `uv lock`, never hand-edited)

**Interfaces:**
- Consumes: nothing.
- Produces: `black76_call(F, K, T, sigma, df=1.0)`, `black76_put`, `black76_delta`, `black76_gamma`, `black76_vega_per_vol_pt`, `bachelier_call(F, K, T, sigma_n, df=1.0)`, `bachelier_put`, `bachelier_delta`, `bachelier_gamma`, `bachelier_vega`, `bachelier_vega_per_bp`, `black76_implied_vol(price, F, K, T, df=1.0, option_type="call")`, `bachelier_implied_vol(...)` — all scalar in, float out; implied vols return `nan` when there is no root.

- [ ] **Step 1: Create the worktree and session variables**

Use superpowers:using-git-worktrees to create a worktree of `/home/kazumasa/projects` on a new branch `rates-vol-completion` (other sessions share the main checkout's index — see memory note on shared worktrees). Then, in every shell used for this plan:

```bash
export WT=<absolute path of the new worktree>
export PY=/home/kazumasa/projects/.venv/bin/python
export RUFF=/home/kazumasa/projects/.venv/bin/ruff
export PYTHONPATH="$WT/rates_volatility_model/src"
export SCRATCH=<a scratch directory outside the repository>
cd "$WT"
$PY -c "import numpy, scipy, nbclient, japanize_matplotlib; print(numpy.__version__)"
```

Expected: prints `2.4.6` (any `2.x` is fine).

- [ ] **Step 2: Write the member `pyproject.toml` and package marker**

`rates_volatility_model/pyproject.toml`:

```toml
[project]
name = "rates-volatility-model"
version = "0.2.0"
description = "Japanese teaching notebook on interest-rate volatility models, backed by the tested ratesvol package"
requires-python = ">=3.12"
dependencies = [
    "numpy>=2.0",
    "scipy>=1.13",
    "matplotlib>=3.9",
    "pandas>=2.2",
    "japanize-matplotlib>=1.1",
    "ipywidgets>=8.1",
    "ipykernel>=6.29",
    "jupyterlab>=4.2",
    "nbformat>=5.10",
    "nbclient>=0.10",
]

[dependency-groups]
dev = ["pytest>=8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/ratesvol"]
```

`rates_volatility_model/src/ratesvol/__init__.py`:

```python
"""ratesvol: tested interest-rate volatility models used by rates_volatility_models.ipynb."""
```

- [ ] **Step 3: Register the member in the root `pyproject.toml` and relock**

In the root `pyproject.toml`, in `[tool.uv.workspace] members`, change

```toml
    "timesfm_lab",
]
```

to

```toml
    "timesfm_lab",
    "rates_volatility_model",
]
```

and in `[tool.pytest.ini_options] testpaths`, change

```toml
    "timesfm_lab/tests",
]
```

to

```toml
    "timesfm_lab/tests",
    "rates_volatility_model/tests",
]
```

Then run `uv lock` from `$WT`.
Expected: exits 0; `git diff --stat uv.lock` shows a small change that adds a `rates-volatility-model` package entry. No `.venv` is created or modified (`uv lock` only resolves).

- [ ] **Step 4: Write the failing tests**

`rates_volatility_model/tests/test_options.py`:

```python
import numpy as np
import pytest
from ratesvol.options import (
    bachelier_call,
    bachelier_delta,
    bachelier_gamma,
    bachelier_implied_vol,
    bachelier_put,
    bachelier_vega,
    bachelier_vega_per_bp,
    black76_call,
    black76_delta,
    black76_gamma,
    black76_implied_vol,
    black76_put,
    black76_vega_per_vol_pt,
)

F, K, T, SIG, SIG_N = 0.03, 0.032, 1.5, 0.25, 0.008


def test_black76_greeks_match_finite_differences():
    h = 1e-6
    fd_delta = (black76_call(F + h, K, T, SIG) - black76_call(F - h, K, T, SIG)) / (2 * h)
    h2 = 1e-5
    fd_gamma = (
        black76_call(F + h2, K, T, SIG)
        - 2 * black76_call(F, K, T, SIG)
        + black76_call(F - h2, K, T, SIG)
    ) / h2**2
    fd_vega_pt = black76_call(F, K, T, SIG + 0.005) - black76_call(F, K, T, SIG - 0.005)
    assert black76_delta(F, K, T, SIG) == pytest.approx(fd_delta, rel=1e-6)
    assert black76_gamma(F, K, T, SIG) == pytest.approx(fd_gamma, rel=1e-5)
    assert black76_vega_per_vol_pt(F, K, T, SIG) == pytest.approx(fd_vega_pt, rel=1e-4)


def test_bachelier_greeks_match_finite_differences():
    h = 1e-6
    fd_delta = (bachelier_call(F + h, K, T, SIG_N) - bachelier_call(F - h, K, T, SIG_N)) / (2 * h)
    h2 = 1e-5
    fd_gamma = (
        bachelier_call(F + h2, K, T, SIG_N)
        - 2 * bachelier_call(F, K, T, SIG_N)
        + bachelier_call(F - h2, K, T, SIG_N)
    ) / h2**2
    fd_vega_bp = bachelier_call(F, K, T, SIG_N + 0.5e-4) - bachelier_call(F, K, T, SIG_N - 0.5e-4)
    assert bachelier_delta(F, K, T, SIG_N) == pytest.approx(fd_delta, rel=1e-6)
    assert bachelier_gamma(F, K, T, SIG_N) == pytest.approx(fd_gamma, rel=1e-4)
    assert bachelier_vega_per_bp(F, K, T, SIG_N) == pytest.approx(fd_vega_bp, rel=1e-6)
    # the old notebook printed the per-unit vega as "per 1bp": the two differ by 1e4
    assert bachelier_vega(F, K, T, SIG_N) == pytest.approx(
        1e4 * bachelier_vega_per_bp(F, K, T, SIG_N)
    )


def test_put_call_parity():
    df = 0.97
    assert black76_call(F, K, T, SIG, df) - black76_put(F, K, T, SIG, df) == pytest.approx(
        df * (F - K)
    )
    assert bachelier_call(F, K, T, SIG_N, df) - bachelier_put(F, K, T, SIG_N, df) == pytest.approx(
        df * (F - K)
    )


def test_bachelier_prices_negative_forwards_and_black_refuses_them():
    assert bachelier_call(-0.002, 0.0, 1.0, 0.006) > 0
    with pytest.raises(ValueError):
        black76_call(-0.002, 0.001, 1.0, 0.2)


@pytest.mark.parametrize("strike", [0.01, 0.02, 0.03, 0.04, 0.05])
def test_implied_vol_round_trip(strike):
    assert black76_implied_vol(black76_call(F, strike, T, SIG), F, strike, T) == pytest.approx(
        SIG, abs=1e-10
    )
    assert bachelier_implied_vol(
        bachelier_call(F, strike, T, SIG_N), F, strike, T
    ) == pytest.approx(SIG_N, abs=1e-12)


def test_implied_vol_is_nan_below_intrinsic():
    assert np.isnan(black76_implied_vol(0.0, F, 0.02, T))
    assert np.isnan(bachelier_implied_vol(0.0, F, 0.02, T))


def test_bachelier_implied_vol_works_for_negative_forwards():
    price = bachelier_call(-0.002, 0.001, 1.0, 0.006)
    assert bachelier_implied_vol(price, -0.002, 0.001, 1.0) == pytest.approx(0.006, abs=1e-12)


def test_black76_implied_vol_of_a_tiny_deep_otm_price_is_finite():
    assert np.isfinite(black76_implied_vol(1e-12, 0.03, 0.06, 1.0))
```

- [ ] **Step 5: Run the tests to verify they fail**

Run: `$PY -m pytest rates_volatility_model/tests/test_options.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'ratesvol.options'`.

- [ ] **Step 6: Implement `options.py`**

`rates_volatility_model/src/ratesvol/options.py`:

```python
"""Black-76 and Bachelier (normal) option formulas, Greeks and implied vols.

Units: rates and vols are decimals (0.03 = 3%). ``df`` is the discount factor
to the payment date. Greeks are per unit of the underlying input unless the
function name says otherwise (``*_per_bp`` / ``*_per_vol_pt``).
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm


def _black_d1(F, K, T, sigma):
    return (np.log(F / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))


def black76_call(F, K, T, sigma, df=1.0):
    """Black-76 call on a forward rate: df * (F N(d1) - K N(d2))."""
    if sigma <= 0 or T <= 0:
        return df * max(F - K, 0.0)
    if F <= 0 or K <= 0:
        raise ValueError("Black-76 needs F > 0 and K > 0; use the Bachelier model instead")
    d1 = _black_d1(F, K, T, sigma)
    d2 = d1 - sigma * np.sqrt(T)
    return df * (F * norm.cdf(d1) - K * norm.cdf(d2))


def black76_put(F, K, T, sigma, df=1.0):
    """Black-76 put via put-call parity."""
    return black76_call(F, K, T, sigma, df) - df * (F - K)


def black76_delta(F, K, T, sigma, df=1.0):
    """dCall/dF (per unit move in F)."""
    if sigma <= 0 or T <= 0:
        return df * (1.0 if F > K else 0.0)
    return df * norm.cdf(_black_d1(F, K, T, sigma))


def black76_gamma(F, K, T, sigma, df=1.0):
    """d2Call/dF2 (per unit move in F, not per 1%)."""
    if sigma <= 0 or T <= 0:
        return 0.0
    return df * norm.pdf(_black_d1(F, K, T, sigma)) / (F * sigma * np.sqrt(T))


def black76_vega_per_vol_pt(F, K, T, sigma, df=1.0):
    """Price change for a 1 vol-point (0.01) move in the Black vol."""
    if sigma <= 0 or T <= 0:
        return 0.0
    return df * F * norm.pdf(_black_d1(F, K, T, sigma)) * np.sqrt(T) * 0.01


def bachelier_call(F, K, T, sigma_n, df=1.0):
    """Bachelier (normal) call: df * ((F-K) N(d) + sigma_n sqrt(T) n(d))."""
    if sigma_n <= 0 or T <= 0:
        return df * max(F - K, 0.0)
    s = sigma_n * np.sqrt(T)
    d = (F - K) / s
    return df * ((F - K) * norm.cdf(d) + s * norm.pdf(d))


def bachelier_put(F, K, T, sigma_n, df=1.0):
    """Bachelier put via put-call parity."""
    return bachelier_call(F, K, T, sigma_n, df) - df * (F - K)


def bachelier_delta(F, K, T, sigma_n, df=1.0):
    """dCall/dF."""
    if sigma_n <= 0 or T <= 0:
        return df * (1.0 if F > K else 0.0)
    return df * norm.cdf((F - K) / (sigma_n * np.sqrt(T)))


def bachelier_gamma(F, K, T, sigma_n, df=1.0):
    """d2Call/dF2."""
    if sigma_n <= 0 or T <= 0:
        return 0.0
    s = sigma_n * np.sqrt(T)
    return df * norm.pdf((F - K) / s) / s


def bachelier_vega(F, K, T, sigma_n, df=1.0):
    """dCall/dsigma_n per unit (1.0 = 10,000bp) of normal vol."""
    if sigma_n <= 0 or T <= 0:
        return 0.0
    return df * np.sqrt(T) * norm.pdf((F - K) / (sigma_n * np.sqrt(T)))


def bachelier_vega_per_bp(F, K, T, sigma_n, df=1.0):
    """Price change for a 1bp (0.0001) move in the normal vol."""
    return bachelier_vega(F, K, T, sigma_n, df) * 1e-4


def _implied(price_fn, price, F, K, T, df, option_type, lo, hi):
    intrinsic = df * (max(F - K, 0.0) if option_type == "call" else max(K - F, 0.0))
    if price <= intrinsic + 1e-14:
        return np.nan
    try:
        return brentq(lambda s: price_fn(F, K, T, s, df) - price, lo, hi, xtol=1e-12)
    except ValueError:
        return np.nan


def black76_implied_vol(price, F, K, T, df=1.0, option_type="call"):
    """Black vol that reproduces ``price``; nan if no root in [1e-6, 20]."""
    fn = black76_call if option_type == "call" else black76_put
    return _implied(fn, price, F, K, T, df, option_type, 1e-6, 20.0)


def bachelier_implied_vol(price, F, K, T, df=1.0, option_type="call"):
    """Normal vol that reproduces ``price``; nan if no root in [1e-8, 1]."""
    fn = bachelier_call if option_type == "call" else bachelier_put
    return _implied(fn, price, F, K, T, df, option_type, 1e-8, 1.0)
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `$PY -m pytest rates_volatility_model/tests/test_options.py -q`
Expected: `12 passed`.

- [ ] **Step 8: Lint and format check**

Run: `$RUFF check rates_volatility_model/src rates_volatility_model/tests && $RUFF format --check rates_volatility_model/src rates_volatility_model/tests`
Expected: `All checks passed!` and no file would be reformatted. If `ruff check` reports only `I001` (import order), run `$RUFF check --fix` on the same two paths (never add `--select` together with `--fix`) and re-run.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock rates_volatility_model/pyproject.toml rates_volatility_model/src rates_volatility_model/tests
git commit -m "feat(rates_volatility_model): add ratesvol package with tested option formulas"
```

---

### Task 2: Curves and short-rate models

**Files:**
- Create: `rates_volatility_model/src/ratesvol/curves.py`
- Create: `rates_volatility_model/src/ratesvol/short_rate.py`
- Create: `rates_volatility_model/tests/test_curves.py`
- Create: `rates_volatility_model/tests/test_short_rate.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces:
  - `discount_factor(zero_rate, T)`, `instantaneous_forward(zero_rates, T) -> ndarray`, `simple_forward(zero_rates, T_grid, T1, T2) -> float`
  - `vasicek_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng) -> ndarray (n_paths, n_steps+1)`, `vasicek_terminal_moments(r0, a, b, sigma, T) -> (mean, std)`, `vasicek_zcb(r, a, b, sigma, tau)`, `vasicek_zero_rate(r, a, b, sigma, tau)`, `calibrate_vasicek(T_grid, market_zero, x0=...) -> ((r0, a, b, sigma), rmse_bp)`
  - `feller_condition(a, b, sigma) -> bool`, `cir_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng)`
  - `hw1f_theta(T_grid, market_zero, a, sigma) -> ndarray`, `hw1f_simulate(T_grid, market_zero, a, sigma, T, n_steps, n_paths, rng)`
  - `mc_zcb_from_short_rate(paths, T) -> (price, stderr)`
  - `g2pp_phi(t, T_grid, market_zero, a, b, sigma, eta, rho) -> float`, `g2pp_simulate(T_grid, market_zero, a, b, sigma, eta, rho, T, n_steps, n_paths, rng) -> (x, y, r)`

- [ ] **Step 1: Write the failing tests**

`rates_volatility_model/tests/test_curves.py`:

```python
import numpy as np
import pytest
from ratesvol.curves import discount_factor, instantaneous_forward, simple_forward

T = np.linspace(0, 10, 201)
Z = 0.02 + 0.03 * (1 - np.exp(-T / 5))


def test_instantaneous_forward_is_z_plus_t_dz_dt():
    exact = Z + T * 0.03 / 5 * np.exp(-T / 5)
    assert np.max(np.abs(instantaneous_forward(Z, T) - exact)) < 1e-4


def test_flat_curve_has_flat_forward():
    flat = np.full_like(T, 0.02)
    assert np.allclose(instantaneous_forward(flat, T), 0.02)


def test_discount_factor_and_simple_forward_are_consistent():
    p1, p2 = discount_factor(np.interp(2.0, T, Z), 2.0), discount_factor(np.interp(5.0, T, Z), 5.0)
    assert simple_forward(Z, T, 2.0, 5.0) == pytest.approx(np.log(p1 / p2) / 3.0)


def test_simple_forward_rejects_reversed_dates():
    with pytest.raises(ValueError):
        simple_forward(Z, T, 5.0, 2.0)
```

`rates_volatility_model/tests/test_short_rate.py`:

```python
import numpy as np
import pytest
from ratesvol.short_rate import (
    calibrate_vasicek,
    cir_simulate,
    feller_condition,
    g2pp_simulate,
    hw1f_simulate,
    hw1f_theta,
    mc_zcb_from_short_rate,
    vasicek_simulate,
    vasicek_terminal_moments,
    vasicek_zcb,
    vasicek_zero_rate,
)

T_GRID = np.linspace(0, 10, 201)
Z_MKT = 0.02 + 0.03 * (1 - np.exp(-T_GRID / 5))


def market_zcb(T):
    return np.exp(-np.interp(T, T_GRID, Z_MKT) * T)


def test_vasicek_terminal_distribution_matches_theory():
    paths = vasicek_simulate(0.03, 0.15, 0.05, 0.02, 10.0, 100, 20000, np.random.default_rng(0))
    mean, std = vasicek_terminal_moments(0.03, 0.15, 0.05, 0.02, 10.0)
    assert abs(paths[:, -1].mean() - mean) < 4 * std / np.sqrt(20000)
    assert paths[:, -1].std() == pytest.approx(std, rel=0.03)


def test_vasicek_mc_bond_price_matches_closed_form():
    paths = vasicek_simulate(0.03, 0.15, 0.05, 0.02, 5.0, 500, 20000, np.random.default_rng(1))
    price, se = mc_zcb_from_short_rate(paths, 5.0)
    assert abs(price - vasicek_zcb(0.03, 0.15, 0.05, 0.02, 5.0)) < 4 * se


def test_vasicek_calibration_refits_its_own_curve():
    T = np.linspace(0.5, 10, 20)
    target = vasicek_zero_rate(0.025, 0.3, 0.045, 0.01, T)
    _, rmse_bp = calibrate_vasicek(T, target)
    assert rmse_bp < 0.5


def test_cir_is_non_negative_and_mean_reverts():
    paths = cir_simulate(0.03, 0.15, 0.05, 0.02, 10.0, 200, 20000, np.random.default_rng(2))
    mean_th = 0.05 + (0.03 - 0.05) * np.exp(-1.5)
    assert paths.min() >= 0.0
    assert abs(paths[:, -1].mean() - mean_th) < 4 * paths[:, -1].std() / np.sqrt(20000)


def test_feller_condition():
    assert feller_condition(0.15, 0.05, 0.02)
    assert not feller_condition(0.1, 0.02, 0.1)


def test_hw1f_theta_has_the_right_sign():
    # the previous notebook flipped the sign of df/dt; for this upward curve theta must be > 0
    assert np.all(hw1f_theta(T_GRID, Z_MKT, 0.1, 0.01) > 0)


@pytest.mark.parametrize("T", [2.0, 5.0, 10.0])
def test_hw1f_reprices_the_initial_curve(T):
    paths = hw1f_simulate(
        T_GRID, Z_MKT, 0.1, 0.01, T, int(T * 100), 20000, np.random.default_rng(3)
    )
    price, se = mc_zcb_from_short_rate(paths, T)
    assert abs(price - market_zcb(T)) < 4 * se


@pytest.mark.parametrize("T", [2.0, 5.0, 10.0])
def test_g2pp_reprices_the_initial_curve(T):
    _, _, r = g2pp_simulate(
        T_GRID,
        Z_MKT,
        0.1,
        0.03,
        0.01,
        0.005,
        -0.5,
        T,
        int(T * 100),
        20000,
        np.random.default_rng(4),
    )
    price, se = mc_zcb_from_short_rate(r, T)
    assert abs(price - market_zcb(T)) < 4 * se


def test_g2pp_starts_on_the_curve():
    _, _, r = g2pp_simulate(
        T_GRID, Z_MKT, 0.1, 0.03, 0.01, 0.005, -0.5, 1.0, 10, 5, np.random.default_rng(5)
    )
    assert np.allclose(r[:, 0], Z_MKT[0] + 0.0, atol=1e-4)


def test_cir_stays_non_negative_when_feller_fails():
    paths = cir_simulate(0.01, 0.1, 0.02, 0.1, 5.0, 200, 5000, np.random.default_rng(6))
    assert paths.min() == 0.0  # zero is reached...
    assert (paths >= 0).all()  # ...but never crossed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest rates_volatility_model/tests/test_curves.py rates_volatility_model/tests/test_short_rate.py -q`
Expected: two collection errors, `ModuleNotFoundError: No module named 'ratesvol.curves'` and `... 'ratesvol.short_rate'`.

- [ ] **Step 3: Implement `curves.py`**

`rates_volatility_model/src/ratesvol/curves.py`:

```python
"""Zero-curve helpers (continuous compounding)."""

from __future__ import annotations

import numpy as np


def discount_factor(zero_rate, T):
    """P(0,T) = exp(-z(T) T)."""
    return np.exp(-np.asarray(zero_rate) * np.asarray(T))


def instantaneous_forward(zero_rates, T):
    """f(0,T) = z(T) + T dz/dT, derivative by finite differences on the grid."""
    zero_rates = np.asarray(zero_rates, dtype=float)
    T = np.asarray(T, dtype=float)
    return zero_rates + T * np.gradient(zero_rates, T)


def simple_forward(zero_rates, T_grid, T1, T2):
    """Continuously compounded forward between T1 < T2 from a linearly interpolated zero curve."""
    if T2 <= T1:
        raise ValueError("T2 must be greater than T1")
    z1 = np.interp(T1, T_grid, zero_rates)
    z2 = np.interp(T2, T_grid, zero_rates)
    return (z2 * T2 - z1 * T1) / (T2 - T1)
```

- [ ] **Step 4: Implement `short_rate.py`**

`rates_volatility_model/src/ratesvol/short_rate.py`:

```python
"""Short-rate models: Vasicek, CIR, Hull-White 1F, G2++.

Every simulator takes a ``numpy.random.Generator`` so results are reproducible
without touching global random state.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from ratesvol.curves import instantaneous_forward


# ----------------------------------------------------------------- Vasicek
def vasicek_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng):
    """Exact Vasicek transition: dr = a(b - r)dt + sigma dW. Returns (n_paths, n_steps+1)."""
    dt = T / n_steps
    e = np.exp(-a * dt)
    sd = sigma * np.sqrt((1 - e**2) / (2 * a))
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        paths[:, i + 1] = b + (paths[:, i] - b) * e + sd * rng.standard_normal(n_paths)
    return paths


def vasicek_terminal_moments(r0, a, b, sigma, T):
    """Mean and std of r_T under Vasicek."""
    mean = b + (r0 - b) * np.exp(-a * T)
    std = sigma * np.sqrt((1 - np.exp(-2 * a * T)) / (2 * a))
    return mean, std


def vasicek_zcb(r, a, b, sigma, tau):
    """Zero-coupon bond P = A exp(-B r) with B = (1 - e^{-a tau})/a."""
    B = (1 - np.exp(-a * tau)) / a
    log_A = (b - sigma**2 / (2 * a**2)) * (B - tau) - sigma**2 * B**2 / (4 * a)
    return np.exp(log_A - B * r)


def vasicek_zero_rate(r, a, b, sigma, tau):
    """Continuously compounded zero rate implied by the Vasicek bond price."""
    return -np.log(vasicek_zcb(r, a, b, sigma, tau)) / tau


def calibrate_vasicek(T_grid, market_zero, x0=(0.03, 0.1, 0.05, 0.01)):
    """Least-squares fit of (r0, a, b, sigma) to a zero curve. Returns (params, rmse_bp)."""
    T_grid = np.asarray(T_grid, dtype=float)
    market_zero = np.asarray(market_zero, dtype=float)

    def sse(p):
        r0, a, b, s = p
        return np.sum((vasicek_zero_rate(r0, a, b, s, T_grid) - market_zero) ** 2)

    bounds = [(-0.05, 0.2), (0.01, 2.0), (-0.05, 0.3), (1e-4, 0.1)]
    res = minimize(sse, x0, method="L-BFGS-B", bounds=bounds)
    rmse_bp = np.sqrt(res.fun / len(T_grid)) * 1e4
    return res.x, rmse_bp


# --------------------------------------------------------------------- CIR
def feller_condition(a, b, sigma):
    """True when 2ab >= sigma^2 (zero is unattainable)."""
    return 2 * a * b >= sigma**2


def cir_simulate(r0, a, b, sigma, T, n_steps, n_paths, rng):
    """Full-truncation Euler for dr = a(b - r)dt + sigma sqrt(r) dW (Lord et al. 2010).

    The auxiliary process may dip below zero; the returned short rate is max(., 0).
    """
    dt = T / n_steps
    x = np.full(n_paths, float(r0))
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        xp = np.maximum(x, 0.0)
        x = x + a * (b - xp) * dt + sigma * np.sqrt(xp * dt) * rng.standard_normal(n_paths)
        paths[:, i + 1] = np.maximum(x, 0.0)
    return paths


# ------------------------------------------------------------ Hull-White 1F
def hw1f_theta(T_grid, market_zero, a, sigma):
    """theta(t) = df(0,t)/dt + a f(0,t) + sigma^2/(2a) (1 - e^{-2at}) on the curve grid."""
    T_grid = np.asarray(T_grid, dtype=float)
    f = instantaneous_forward(market_zero, T_grid)
    return np.gradient(f, T_grid) + a * f + sigma**2 / (2 * a) * (1 - np.exp(-2 * a * T_grid))


def hw1f_simulate(T_grid, market_zero, a, sigma, T, n_steps, n_paths, rng):
    """Euler simulation of dr = (theta(t) - a r)dt + sigma dW starting at r0 = f(0,0)."""
    T_grid = np.asarray(T_grid, dtype=float)
    theta = hw1f_theta(T_grid, market_zero, a, sigma)
    r0 = instantaneous_forward(market_zero, T_grid)[0]
    dt = T / n_steps
    paths = np.empty((n_paths, n_steps + 1))
    paths[:, 0] = r0
    for i in range(n_steps):
        th = np.interp(i * dt, T_grid, theta)
        paths[:, i + 1] = (
            paths[:, i]
            + (th - a * paths[:, i]) * dt
            + sigma * np.sqrt(dt) * rng.standard_normal(n_paths)
        )
    return paths


def mc_zcb_from_short_rate(paths, T):
    """P(0,T) estimate = mean(exp(-integral r dt)) with the trapezoid rule. Returns (price, stderr)."""
    n_steps = paths.shape[1] - 1
    dt = T / n_steps
    integral = dt * (paths[:, 1:-1].sum(axis=1) + 0.5 * (paths[:, 0] + paths[:, -1]))
    disc = np.exp(-integral)
    return disc.mean(), disc.std(ddof=1) / np.sqrt(len(disc))


# -------------------------------------------------------------------- G2++
def g2pp_phi(t, T_grid, market_zero, a, b, sigma, eta, rho):
    """Deterministic shift that fits G2++ to the market curve (Brigo-Mercurio eq. 4.12)."""
    f = np.interp(t, T_grid, instantaneous_forward(market_zero, T_grid))
    ea, eb = 1 - np.exp(-a * t), 1 - np.exp(-b * t)
    return (
        f
        + sigma**2 / (2 * a**2) * ea**2
        + eta**2 / (2 * b**2) * eb**2
        + rho * sigma * eta / (a * b) * ea * eb
    )


def g2pp_simulate(T_grid, market_zero, a, b, sigma, eta, rho, T, n_steps, n_paths, rng):
    """Euler simulation of r = x + y + phi(t), dx = -a x dt + sigma dW1, dy = -b y dt + eta dW2.

    Returns (x, y, r), each (n_paths, n_steps+1).
    """
    dt = T / n_steps
    x = np.zeros((n_paths, n_steps + 1))
    y = np.zeros((n_paths, n_steps + 1))
    r = np.zeros((n_paths, n_steps + 1))
    r[:, 0] = g2pp_phi(0.0, T_grid, market_zero, a, b, sigma, eta, rho)
    for i in range(n_steps):
        z1 = rng.standard_normal(n_paths)
        z2 = rho * z1 + np.sqrt(1 - rho**2) * rng.standard_normal(n_paths)
        x[:, i + 1] = x[:, i] - a * x[:, i] * dt + sigma * np.sqrt(dt) * z1
        y[:, i + 1] = y[:, i] - b * y[:, i] * dt + eta * np.sqrt(dt) * z2
        phi = g2pp_phi((i + 1) * dt, T_grid, market_zero, a, b, sigma, eta, rho)
        r[:, i + 1] = x[:, i + 1] + y[:, i + 1] + phi
    return x, y, r
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m pytest rates_volatility_model/tests/test_curves.py rates_volatility_model/tests/test_short_rate.py -q`
Expected: `18 passed` (4 + 14), in a few seconds. The Monte Carlo tests use fixed seeds and a 4-standard-error band; the seeds were checked on 2026-09-27, so a failure means a code change, not bad luck.

- [ ] **Step 6: Lint and format check**

Run: `$RUFF check rates_volatility_model/src rates_volatility_model/tests && $RUFF format --check rates_volatility_model/src rates_volatility_model/tests`
Expected: clean (same `I001` rule as Task 1 step 8).

- [ ] **Step 7: Commit**

```bash
git add rates_volatility_model/src/ratesvol/curves.py rates_volatility_model/src/ratesvol/short_rate.py rates_volatility_model/tests/test_curves.py rates_volatility_model/tests/test_short_rate.py
git commit -m "feat(rates_volatility_model): add curve helpers and short-rate models fitted to the curve"
```

---

### Task 3: HJM and spot-measure LMM

**Files:**
- Create: `rates_volatility_model/src/ratesvol/market_models.py`
- Create: `rates_volatility_model/tests/test_market_models.py`

**Interfaces:**
- Consumes: `black76_call` (Task 1) in tests only.
- Produces:
  - `hjm_drift(t, T_grid, vol_func, n_quad=33) -> ndarray` — `vol_func(t, u)` may return a scalar or an array shaped like `u`.
  - `hjm_simulate(T_grid, f0, vol_func, t_grid, n_paths, rng) -> ndarray (n_paths, len(t_grid), len(T_grid))`
  - `lmm_simulate_spot(tenor_dates, L0, vols, corr, steps_per_period, n_paths, rng) -> (times, L)` with `L` shaped `(n_paths, len(times), N)`; `len(tenor_dates) == N + 1`, else `ValueError`.
  - `lmm_fixings(times, L, tenor_dates) -> ndarray (n_paths, N)`, `spot_numeraire(fixings, tenor_dates) -> ndarray (n_paths, N)` where column n−1 is B(T_n).

- [ ] **Step 1: Write the failing tests**

`rates_volatility_model/tests/test_market_models.py`:

```python
import numpy as np
import pytest
from ratesvol.market_models import (
    hjm_drift,
    hjm_simulate,
    lmm_fixings,
    lmm_simulate_spot,
    spot_numeraire,
)
from ratesvol.options import black76_call

# ------------------------------------------------------------------ HJM
T_HJM = np.linspace(0.1, 10, 11)
F0_HJM = 0.02 + 0.03 * (1 - np.exp(-T_HJM / 5))


def flat_vol(t, u):
    return 0.01


def test_hjm_drift_is_integral_from_t_to_maturity():
    # constant sigma: alpha(t,T) = sigma^2 (T - t). The old code integrated from T to T_max.
    alpha = hjm_drift(2.0, T_HJM, flat_vol)
    expected = np.where(T_HJM > 2.0, 1e-4 * (T_HJM - 2.0), 0.0)
    assert np.allclose(alpha, expected, atol=1e-15)


def test_hjm_ho_lee_forward_mean():
    t_grid = np.linspace(0, 5, 26)
    fc = hjm_simulate(T_HJM, F0_HJM, flat_vol, t_grid, 20000, np.random.default_rng(10))
    t, T = 5.0, T_HJM[-1]
    expected = F0_HJM[-1] + 1e-4 * t * (T - t / 2)
    se = fc[:, -1, -1].std() / np.sqrt(20000)
    assert abs(fc[:, -1, -1].mean() - expected) < 4 * se


def test_hjm_freezes_matured_forwards():
    t_grid = np.linspace(0, 5, 26)
    fc = hjm_simulate(T_HJM, F0_HJM, flat_vol, t_grid, 100, np.random.default_rng(11))
    j = 1  # T = 1.09y
    first_after = int(np.searchsorted(t_grid, T_HJM[j]))
    assert np.array_equal(fc[:, first_after, j], fc[:, -1, j])


# ------------------------------------------------------------------ LMM
TENOR = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
L0 = np.array([0.030, 0.032, 0.034, 0.035, 0.036, 0.036])
VOLS = np.array([0.20, 0.19, 0.18, 0.17, 0.16, 0.15])
CORR = np.exp(-0.3 * np.abs(np.subtract.outer(TENOR[:-1], TENOR[:-1])))
TAU = np.diff(TENOR)
P0 = np.cumprod(1 / (1 + TAU * L0))


@pytest.fixture(scope="module")
def lmm_run():
    times, L = lmm_simulate_spot(TENOR, L0, VOLS, CORR, 10, 40000, np.random.default_rng(12))
    fixings = lmm_fixings(times, L, TENOR)
    return times, L, fixings, spot_numeraire(fixings, TENOR)


@pytest.mark.parametrize("n", [2, 4, 6])
def test_lmm_spot_measure_reprices_zero_coupon_bonds(lmm_run, n):
    x = 1 / lmm_run[3][:, n - 1]
    assert abs(x.mean() - P0[n - 1]) < 4 * x.std() / np.sqrt(len(x))


@pytest.mark.parametrize("k", [1, 3, 5])
def test_lmm_caplet_matches_black76(lmm_run, k):
    fixings, B = lmm_run[2], lmm_run[3]
    pay = TAU[k] * np.maximum(fixings[:, k] - L0[k], 0) / B[:, k]
    black = P0[k] * TAU[k] * black76_call(L0[k], L0[k], TENOR[k], VOLS[k])
    assert abs(pay.mean() - black) < 4 * pay.std() / np.sqrt(len(pay))


def test_lmm_freezes_forwards_after_fixing(lmm_run):
    times, L = lmm_run[0], lmm_run[1]
    fix_idx = int(np.argmin(np.abs(times - TENOR[2])))
    assert np.array_equal(L[:, fix_idx, 2], L[:, -1, 2])


def test_lmm_rejects_mismatched_tenors():
    with pytest.raises(ValueError):
        lmm_simulate_spot(TENOR[:-1], L0, VOLS, CORR, 2, 10, np.random.default_rng(0))


def test_lmm_irregular_tenors_reprice_the_last_bond():
    tenor = np.array([0.0, 0.25, 0.5, 1.0, 2.0])
    l0 = np.array([0.03, 0.031, 0.033, 0.035])
    vols = np.array([0.2, 0.2, 0.18, 0.16])
    corr = np.exp(-0.3 * np.abs(np.subtract.outer(tenor[:-1], tenor[:-1])))
    times, paths = lmm_simulate_spot(tenor, l0, vols, corr, 10, 40000, np.random.default_rng(13))
    numeraire = spot_numeraire(lmm_fixings(times, paths, tenor), tenor)
    x = 1 / numeraire[:, -1]
    p0 = np.prod(1 / (1 + np.diff(tenor) * l0))
    assert abs(x.mean() - p0) < 4 * x.std() / np.sqrt(len(x))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest rates_volatility_model/tests/test_market_models.py -q`
Expected: collection error, `ModuleNotFoundError: No module named 'ratesvol.market_models'`.

- [ ] **Step 3: Implement `market_models.py`**

`rates_volatility_model/src/ratesvol/market_models.py`:

```python
"""HJM (one factor, fixed-maturity grid) and the LIBOR/forward market model under the spot measure."""

from __future__ import annotations

import numpy as np


# --------------------------------------------------------------------- HJM
def hjm_drift(t, T_grid, vol_func, n_quad=33):
    """No-arbitrage drift alpha(t,T) = sigma(t,T) * integral_t^T sigma(t,u) du; zero for T <= t.

    ``vol_func(t, u)`` must accept an array ``u`` (a scalar return is broadcast).
    """
    T_grid = np.asarray(T_grid, dtype=float)
    sig_T = np.broadcast_to(vol_func(t, T_grid), T_grid.shape)
    alpha = np.zeros_like(T_grid)
    for j, T in enumerate(T_grid):
        if T <= t:
            continue
        u = np.linspace(t, T, n_quad)
        alpha[j] = sig_T[j] * np.trapezoid(np.broadcast_to(vol_func(t, u), u.shape), u)
    return alpha


def hjm_simulate(T_grid, f0, vol_func, t_grid, n_paths, rng):
    """Euler simulation of df(t,T) = alpha dt + sigma dW for every T on ``T_grid``.

    Forwards with T <= t are frozen. Returns (n_paths, len(t_grid), len(T_grid)).
    """
    T_grid = np.asarray(T_grid, dtype=float)
    t_grid = np.asarray(t_grid, dtype=float)
    out = np.empty((n_paths, len(t_grid), len(T_grid)))
    out[:, 0, :] = np.asarray(f0, dtype=float)
    for i in range(1, len(t_grid)):
        t, dt = t_grid[i - 1], t_grid[i] - t_grid[i - 1]
        alive = T_grid > t
        sig = np.broadcast_to(vol_func(t, T_grid), T_grid.shape) * alive
        alpha = hjm_drift(t, T_grid, vol_func)
        dW = np.sqrt(dt) * rng.standard_normal(n_paths)
        out[:, i, :] = out[:, i - 1, :] + alpha * dt + dW[:, None] * sig[None, :]
    return out


# --------------------------------------------------------------------- LMM
def lmm_simulate_spot(tenor_dates, L0, vols, corr, steps_per_period, n_paths, rng):
    """Log-Euler LMM under the spot (rolling) measure.

    ``tenor_dates`` = T_0=0 < T_1 < ... < T_N; forward L_i accrues over [T_i, T_{i+1}] and
    fixes at T_i. Drift for alive i >= eta(t): mu_i = sigma_i sum_{j=eta(t)}^{i}
    tau_j rho_ij sigma_j L_j / (1 + tau_j L_j)  (Glasserman 2003, eq. 3.112).

    Returns (times, L) with L of shape (n_paths, len(times), N); forwards are frozen after
    their fixing date.
    """
    T = np.asarray(tenor_dates, dtype=float)
    L0 = np.asarray(L0, dtype=float)
    vols = np.asarray(vols, dtype=float)
    N = len(L0)
    if len(T) != N + 1:
        raise ValueError("need len(tenor_dates) == len(L0) + 1")
    tau = np.diff(T)
    chol = np.linalg.cholesky(corr)
    times = [0.0]
    for k in range(N):
        times.extend(np.linspace(T[k], T[k + 1], steps_per_period + 1)[1:])
    times = np.array(times)
    L = np.empty((n_paths, len(times), N))
    L[:, 0, :] = L0
    for s in range(1, len(times)):
        t, dt = times[s - 1], times[s] - times[s - 1]
        eta = int(np.searchsorted(T, t, side="right"))  # first forward not yet fixed
        cur = L[:, s - 1, :].copy()
        dW = (rng.standard_normal((n_paths, N)) @ chol.T) * np.sqrt(dt)
        new = cur.copy()
        for i in range(eta, N):
            j = np.arange(eta, i + 1)
            w = tau[j] * cur[:, j] / (1 + tau[j] * cur[:, j])
            mu = vols[i] * (w * (corr[i, j] * vols[j])).sum(axis=1)
            new[:, i] = cur[:, i] * np.exp((mu - 0.5 * vols[i] ** 2) * dt + vols[i] * dW[:, i])
        L[:, s, :] = new
    return times, L


def lmm_fixings(times, L, tenor_dates):
    """L_i(T_i) for each forward: array (n_paths, N)."""
    T = np.asarray(tenor_dates, dtype=float)
    idx = [int(np.argmin(np.abs(times - T[i]))) for i in range(L.shape[2])]
    return np.stack([L[:, idx[i], i] for i in range(L.shape[2])], axis=1)


def spot_numeraire(fixings, tenor_dates):
    """B(T_n) = prod_{j<n} (1 + tau_j L_j(T_j)) for n = 1..N: array (n_paths, N)."""
    tau = np.diff(np.asarray(tenor_dates, dtype=float))
    return np.cumprod(1 + tau * fixings, axis=1)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest rates_volatility_model/tests/test_market_models.py -q`
Expected: `12 passed`.

- [ ] **Step 5: Lint and format check**

Run: `$RUFF check rates_volatility_model/src rates_volatility_model/tests && $RUFF format --check rates_volatility_model/src rates_volatility_model/tests`
Expected: clean.

- [ ] **Step 6: Commit**

```bash
git add rates_volatility_model/src/ratesvol/market_models.py rates_volatility_model/tests/test_market_models.py
git commit -m "feat(rates_volatility_model): add HJM with the t-to-T drift and a spot-measure LMM"
```

---

### Task 4: Smile models and RFR compounding

**Files:**
- Create: `rates_volatility_model/src/ratesvol/smile.py`
- Create: `rates_volatility_model/src/ratesvol/rfr.py`
- Create: `rates_volatility_model/tests/test_smile.py`
- Create: `rates_volatility_model/tests/test_rfr.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `sabr_black_vol(F, K, T, alpha, beta, rho, nu) -> float` (nan for non-positive F, K, T)
  - `sabr_alpha_from_atm_vol(F, T, atm_vol, beta, rho, nu) -> float`
  - `calibrate_sabr(F, T, strikes, market_vols, beta, x0=None) -> (alpha, rho, nu, rmse_bp, fitted_vols)`
  - `svi_total_variance(k, a, b, rho, m, sig)`, `svi_density_g(k, a, b, rho, m, sig)`, `calibrate_svi(F, T, strikes, market_vols, x0=...) -> (params, rmse_bp, fitted_vols)`
  - `delta_strike(F, T, vol_of_strike, target_delta) -> float` (nan if not bracketable), `smile_metrics(F, T, vol_of_strike, delta=0.25) -> (atm, rr, bf)`
  - `compounded_in_arrears(daily_rates, day_weights, day_basis=360) -> float`, `simple_average(daily_rates, day_weights) -> float`

- [ ] **Step 1: Write the failing tests**

`rates_volatility_model/tests/test_smile.py` (the golden values were computed with this implementation and agree to machine precision with the independent `hullkit.sabr.sabr_implied_vol` in `johnhull/hullkit`; the test does not import hullkit, to keep the projects independent):

```python
import numpy as np
import pytest
from ratesvol.smile import (
    calibrate_sabr,
    calibrate_svi,
    delta_strike,
    sabr_alpha_from_atm_vol,
    sabr_black_vol,
    smile_metrics,
    svi_density_g,
    svi_total_variance,
)
from scipy.stats import norm

# Golden values: identical to machine precision with the independent implementation
# hullkit.sabr.sabr_implied_vol (johnhull/hullkit), checked 2026-09-27.
GOLDEN = [
    ((0.03, 0.02, 1.0, 0.02, 0.5, -0.3, 0.4), 0.16976693425780964),
    ((0.03, 0.03, 1.0, 0.02, 0.5, -0.3, 0.4), 0.11661784596633339),
    ((0.03, 0.045, 5.0, 0.01, 0.5, -0.2, 0.5), 0.09900176371397934),
    ((0.05, 0.04, 2.0, 0.25, 1.0, -0.5, 0.3), 0.265763885941224),
]


@pytest.mark.parametrize("args,expected", GOLDEN)
def test_sabr_matches_golden_values(args, expected):
    assert sabr_black_vol(*args) == pytest.approx(expected, rel=1e-12)


def test_sabr_lognormal_without_volvol_is_flat_at_alpha():
    for K in [0.01, 0.03, 0.06]:
        assert sabr_black_vol(0.03, K, 2.0, 0.2, 1.0, 0.0, 0.0) == pytest.approx(0.2, rel=1e-12)


def test_sabr_is_continuous_at_the_money():
    F = 0.03
    atm = sabr_black_vol(F, F, 1.0, 0.02, 0.5, -0.3, 0.4)
    assert sabr_black_vol(F, F * (1 + 1e-7), 1.0, 0.02, 0.5, -0.3, 0.4) == pytest.approx(
        atm, rel=1e-6
    )


def test_sabr_alpha_from_atm_vol_round_trips():
    alpha = sabr_alpha_from_atm_vol(0.03, 1.0, 0.2, 0.5, -0.3, 0.4)
    assert sabr_black_vol(0.03, 0.03, 1.0, alpha, 0.5, -0.3, 0.4) == pytest.approx(0.2, abs=1e-10)


def test_sabr_calibration_recovers_noise_free_parameters():
    F, T = 0.031, 1.0
    strikes = F + np.arange(-100, 101, 25) / 1e4
    vols = np.array([sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45) for K in strikes])
    alpha, rho, nu, rmse_bp, _ = calibrate_sabr(F, T, strikes, vols, 0.5)
    assert (alpha, rho, nu) == pytest.approx((0.014, -0.45, 0.45), abs=2e-3)
    assert rmse_bp < 0.1


def test_svi_g_matches_finite_differences():
    p = (0.04, 0.4, -0.4, 0.0, 0.1)
    k = np.linspace(-1.5, 1.5, 301)
    h = 1e-5
    w = svi_total_variance(k, *p)
    w1 = (svi_total_variance(k + h, *p) - svi_total_variance(k - h, *p)) / (2 * h)
    w2 = (svi_total_variance(k + h, *p) - 2 * w + svi_total_variance(k - h, *p)) / h**2
    g_fd = (1 - k * w1 / (2 * w)) ** 2 - w1**2 / 4 * (1 / w + 0.25) + w2 / 2
    assert np.max(np.abs(svi_density_g(k, *p) - g_fd)) < 1e-4


def test_svi_vogt_example_has_butterfly_arbitrage_despite_slope_bound():
    # Gatheral-Jacquier (2014) / Axel Vogt: satisfies b(1+|rho|) < 4 but g(k) < 0 somewhere
    vogt = (-0.0410, 0.1331, 0.3060, 0.3586, 0.4153)
    assert vogt[1] * (1 + abs(vogt[2])) < 4
    assert svi_density_g(np.linspace(-1.5, 1.5, 3001), *vogt).min() < 0


def test_svi_calibration_is_arbitrage_free_and_close():
    F, T = 0.031, 1.0
    strikes = F * np.exp(np.linspace(-0.4, 0.4, 9))
    vols = np.array([sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45) for K in strikes])
    params, rmse_bp, _ = calibrate_svi(F, T, strikes, vols)
    assert rmse_bp < 10
    assert svi_density_g(np.linspace(-1.5, 1.5, 301), *params).min() >= 0


def test_delta_strike_uses_the_smile_vol():
    F, T = 0.031, 1.0

    def smile(K):
        return sabr_black_vol(F, K, T, 0.014, 0.5, -0.45, 0.45)

    K = delta_strike(F, T, smile, 0.25)
    s = smile(K)
    assert norm.cdf((np.log(F / K) + 0.5 * s**2 * T) / (s * np.sqrt(T))) == pytest.approx(
        0.25, abs=1e-8
    )


def test_flat_smile_has_zero_risk_reversal_and_butterfly():
    atm, rr, bf = smile_metrics(0.03, 1.0, lambda K: 0.2)
    assert (atm, rr, bf) == pytest.approx((0.2, 0.0, 0.0), abs=1e-12)


def test_smile_metrics_return_nan_when_delta_cannot_be_bracketed():
    atm, rr, bf = smile_metrics(
        0.034, 10.0, lambda K: sabr_black_vol(0.034, K, 10.0, 0.039, 1.0, 0.9, 1.5)
    )
    assert np.isfinite(atm) and np.isnan(rr) and np.isnan(bf)
```

`rates_volatility_model/tests/test_rfr.py`:

```python
import pytest
from ratesvol.rfr import compounded_in_arrears, simple_average


def test_constant_rate_compounds_like_the_closed_form():
    expected = ((1 + 0.05 / 360) ** 90 - 1) * 360 / 90
    assert compounded_in_arrears([0.05] * 90, [1] * 90) == pytest.approx(expected, rel=1e-12)


def test_weekend_fixing_counts_three_days():
    expected = ((1 + 0.05 / 360) * (1 + 0.06 * 3 / 360) - 1) * 360 / 4
    assert compounded_in_arrears([0.05, 0.06], [1, 3]) == pytest.approx(expected, rel=1e-12)
    assert simple_average([0.05, 0.06], [1, 3]) == pytest.approx(0.0575)


def test_compounding_beats_the_simple_average_for_positive_rates():
    rates, weights = [0.05] * 60 + [0.0525] * 30, [1] * 90
    assert compounded_in_arrears(rates, weights) > simple_average(rates, weights)


def test_shape_mismatch_is_rejected():
    with pytest.raises(ValueError):
        compounded_in_arrears([0.05, 0.05], [1])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest rates_volatility_model/tests/test_smile.py rates_volatility_model/tests/test_rfr.py -q`
Expected: two collection errors, `ModuleNotFoundError: No module named 'ratesvol.smile'` and `... 'ratesvol.rfr'`.

- [ ] **Step 3: Implement `smile.py`**

`rates_volatility_model/src/ratesvol/smile.py`:

```python
"""Smile models: SABR (Hagan 2002 lognormal expansion), raw SVI, and smile metrics."""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq, minimize
from scipy.stats import norm


# -------------------------------------------------------------------- SABR
def sabr_black_vol(F, K, T, alpha, beta, rho, nu):
    """Hagan et al. (2002) Black implied vol for dF = a F^beta dW1, da = nu a dW2, <dW1,dW2> = rho dt.

    ``alpha`` is the initial vol level (not vol-of-vol); ``nu`` is the vol-of-vol.
    Returns nan for non-positive F, K or T.
    """
    if F <= 0 or K <= 0 or T <= 0:
        return np.nan
    one_b = 1 - beta
    fk_mid = (F * K) ** (one_b / 2)
    correction = 1 + T * (
        one_b**2 / 24 * alpha**2 / fk_mid**2
        + rho * beta * nu * alpha / (4 * fk_mid)
        + (2 - 3 * rho**2) / 24 * nu**2
    )
    log_fk = np.log(F / K)
    if abs(log_fk) < 1e-12:
        return alpha / F**one_b * correction
    z = nu / alpha * fk_mid * log_fk
    x_z = np.log((np.sqrt(1 - 2 * rho * z + z**2) + z - rho) / (1 - rho))
    ratio = z / x_z if abs(z) > 1e-8 else 1 - 0.5 * rho * z
    denom = 1 + one_b**2 / 24 * log_fk**2 + one_b**4 / 1920 * log_fk**4
    return alpha / (fk_mid * denom) * ratio * correction


def sabr_alpha_from_atm_vol(F, T, atm_vol, beta, rho, nu):
    """Alpha that reproduces a target ATM Black vol (so beta can move without moving the ATM level)."""
    return brentq(lambda a: sabr_black_vol(F, F, T, a, beta, rho, nu) - atm_vol, 1e-8, 10.0)


def calibrate_sabr(F, T, strikes, market_vols, beta, x0=None):
    """Least-squares (alpha, rho, nu) for fixed beta. Returns (alpha, rho, nu, rmse_bp, fitted_vols)."""
    strikes = np.asarray(strikes, dtype=float)
    market_vols = np.asarray(market_vols, dtype=float)
    if x0 is None:
        x0 = (market_vols[len(market_vols) // 2] * F ** (1 - beta), -0.3, 0.4)

    def model(p):
        return np.array([sabr_black_vol(F, K, T, p[0], beta, p[1], p[2]) for K in strikes])

    def sse(p):
        v = model(p)
        return 1e6 if np.any(~np.isfinite(v)) else np.sum((v - market_vols) ** 2)

    bounds = [(1e-6, None), (-0.999, 0.999), (1e-4, 5.0)]
    res = minimize(sse, x0, method="L-BFGS-B", bounds=bounds)
    fitted = model(res.x)
    rmse_bp = np.sqrt(np.mean((fitted - market_vols) ** 2)) * 1e4
    return res.x[0], res.x[1], res.x[2], rmse_bp, fitted


# --------------------------------------------------------------------- SVI
def svi_total_variance(k, a, b, rho, m, sig):
    """Raw SVI: w(k) = a + b (rho (k-m) + sqrt((k-m)^2 + sig^2)), k = ln(K/F), w = vol^2 T."""
    k = np.asarray(k, dtype=float)
    return a + b * (rho * (k - m) + np.sqrt((k - m) ** 2 + sig**2))


def svi_density_g(k, a, b, rho, m, sig):
    """Gatheral-Jacquier (2014) g(k); the smile is free of butterfly arbitrage iff g >= 0 and w > 0."""
    k = np.asarray(k, dtype=float)
    x = k - m
    root = np.sqrt(x**2 + sig**2)
    w = svi_total_variance(k, a, b, rho, m, sig)
    w1 = b * (rho + x / root)
    w2 = b * sig**2 / root**3
    return (1 - k * w1 / (2 * w)) ** 2 - w1**2 / 4 * (1 / w + 0.25) + w2 / 2


def calibrate_svi(F, T, strikes, market_vols, x0=(None, 0.05, -0.3, 0.0, 0.1)):
    """Fit raw SVI total variance with a penalty on g(k) < 0 over k in [-1.5, 1.5].

    Returns (params, rmse_bp, fitted_vols). Slope bound b(1+|rho|) <= 4 (Rogers-Tehranchi) is a bound.
    """
    k = np.log(np.asarray(strikes, dtype=float) / F)
    w_mkt = np.asarray(market_vols, dtype=float) ** 2 * T
    k_check = np.linspace(-1.5, 1.5, 301)
    a0 = 0.5 * w_mkt.min() if x0[0] is None else x0[0]

    def obj(p):
        b, r = p[1], p[2]
        if b * (1 + abs(r)) > 4:
            return 1e6
        w = svi_total_variance(k_check, *p)
        if np.any(w <= 0):
            return 1e6
        g = svi_density_g(k_check, *p)
        penalty = 1e3 * np.sum(np.minimum(g, 0.0) ** 2)
        return np.sum((svi_total_variance(k, *p) - w_mkt) ** 2) / w_mkt.mean() ** 2 + penalty

    bounds = [(-1.0, 1.0), (1e-6, 4.0), (-0.999, 0.999), (-1.0, 1.0), (1e-4, 2.0)]
    res = minimize(obj, (a0, *x0[1:]), method="L-BFGS-B", bounds=bounds)
    fitted = np.sqrt(svi_total_variance(k, *res.x) / T)
    rmse_bp = np.sqrt(np.mean((fitted - market_vols) ** 2)) * 1e4
    return res.x, rmse_bp, fitted


# ---------------------------------------------------------- smile metrics
def delta_strike(F, T, vol_of_strike, target_delta):
    """Strike whose smile-consistent forward Black delta equals ``target_delta``.

    Call delta = N(d1), put delta = N(d1) - 1; ``vol_of_strike(K)`` is the smile.
    Returns nan when the smile is too extreme for the delta to be bracketed.
    """
    atm = vol_of_strike(F)
    lo, hi = F * np.exp(-8 * atm * np.sqrt(T)), F * np.exp(8 * atm * np.sqrt(T))

    def f(K):
        s = vol_of_strike(K)
        d1 = (np.log(F / K) + 0.5 * s**2 * T) / (s * np.sqrt(T))
        delta = norm.cdf(d1) if target_delta > 0 else norm.cdf(d1) - 1
        return delta - target_delta

    try:
        return brentq(f, lo, hi)
    except ValueError:
        return np.nan


def smile_metrics(F, T, vol_of_strike, delta=0.25):
    """ATM vol, delta risk reversal (call - put) and butterfly ((call + put)/2 - ATM)."""
    atm = vol_of_strike(F)
    k_c = delta_strike(F, T, vol_of_strike, delta)
    k_p = delta_strike(F, T, vol_of_strike, -delta)
    if np.isnan(k_c) or np.isnan(k_p):
        return atm, np.nan, np.nan
    v_c, v_p = vol_of_strike(k_c), vol_of_strike(k_p)
    return atm, v_c - v_p, 0.5 * (v_c + v_p) - atm
```

- [ ] **Step 4: Implement `rfr.py`**

`rates_volatility_model/src/ratesvol/rfr.py`:

```python
"""Overnight risk-free-rate (SOFR/TONA/SONIA-style) compounding."""

from __future__ import annotations

import numpy as np


def compounded_in_arrears(daily_rates, day_weights, day_basis=360):
    """Annualised compounded rate: (prod(1 + r_i n_i / basis) - 1) * basis / sum(n_i).

    ``day_weights`` n_i is the number of calendar days each fixing applies to
    (a Friday fixing usually covers 3 days). Use basis 360 for SOFR/ESTR, 365 for TONA/SONIA.
    """
    r = np.asarray(daily_rates, dtype=float)
    n = np.asarray(day_weights, dtype=float)
    if r.shape != n.shape:
        raise ValueError("daily_rates and day_weights must have the same shape")
    growth = np.prod(1 + r * n / day_basis)
    return (growth - 1) * day_basis / n.sum()


def simple_average(daily_rates, day_weights):
    """Day-weighted arithmetic average of the fixings (no compounding)."""
    r = np.asarray(daily_rates, dtype=float)
    n = np.asarray(day_weights, dtype=float)
    return float((r * n).sum() / n.sum())
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m pytest rates_volatility_model/tests/test_smile.py rates_volatility_model/tests/test_rfr.py -q`
Expected: `18 passed` (14 + 4).

- [ ] **Step 6: Run the whole unit suite, lint, format**

Run: `$PY -m pytest rates_volatility_model/tests -q && $RUFF check rates_volatility_model/src rates_volatility_model/tests && $RUFF format --check rates_volatility_model/src rates_volatility_model/tests`
Expected: `60 passed`; ruff clean.

- [ ] **Step 7: Commit**

```bash
git add rates_volatility_model/src/ratesvol/smile.py rates_volatility_model/src/ratesvol/rfr.py rates_volatility_model/tests/test_smile.py rates_volatility_model/tests/test_rfr.py
git commit -m "feat(rates_volatility_model): add SABR, arbitrage-checked SVI, smile metrics and RFR compounding"
```

---

### Task 5: Notebook execution test and Chapters 0–6

**Files:**
- Create: `rates_volatility_model/tests/test_notebook_executes.py`
- Modify: `rates_volatility_model/rates_volatility_models.ipynb` — cells `83c49f15`, `5066fcf0`, `7eca6d1b`, `740f9884`, `d96aa475`, `2949d726`, `33ad2205`, `f3029894`, `c3dca17a`, `9d0dca12`, `0d1042ca`, `122f2370`, `d47b1084`, `f992a6a3`, `41457d7d`, `7aaa0880`

**Interfaces:**
- Consumes: `ratesvol.curves`, `ratesvol.options`, `ratesvol.short_rate` (Tasks 1–2).
- Produces: notebook global `RNG` (created in cell `83c49f15`), used by every later cell; globals `T_grid`, `market_zero_curve` (defined in `41457d7d`, used by `7aaa0880`).

- [ ] **Step 1: Write the execution test, marked strict-xfail**

`rates_volatility_model/tests/test_notebook_executes.py` — the content below, with one addition for this task only: put

```python
import pytest


@pytest.mark.xfail(strict=True, reason="HJM chapter still calls np.trapz until Task 6")
```

directly above `def test_notebook_executes_without_errors():` (the `import pytest` goes with the other imports). `strict=True` makes the test fail if the notebook unexpectedly passes, so this task still has a meaningful green run.

```python
"""Execute the notebook headlessly, with widget callbacks forced to run and to raise."""

from pathlib import Path

import nbformat
from nbclient import NotebookClient

NOTEBOOK = Path(__file__).resolve().parents[1] / "rates_volatility_models.ipynb"

# ipywidgets swallows exceptions in two places: interact() shows them inside the
# widget, and `with Output():` prints the traceback and suppresses it. A plain
# headless run therefore stays green even when every interactive cell is broken
# (the np.trapz crash in the HJM chapter was invisible this way).
_PREAMBLE = """
import matplotlib
matplotlib.use("Agg")
import ipywidgets as _w

def _interact_now(f, **kwargs):
    f(**{k: (v.value if hasattr(v, "value") else v) for k, v in kwargs.items()})
    return f

class _RaisingOutput(_w.Output):
    def __exit__(self, etype, evalue, tb):
        super().__exit__(None, None, None)
        return False

_w.interact = _interact_now
_w.Output = _RaisingOutput
"""


def test_notebook_executes_without_errors():
    nb = nbformat.read(NOTEBOOK, as_version=4)
    nb.cells.insert(0, nbformat.v4.new_code_cell(_PREAMBLE))
    # raises CellExecutionError, with the failing cell's traceback, on the first error
    NotebookClient(nb, timeout=600, kernel_name="python3").execute()
```

- [ ] **Step 2: Confirm the test catches the hidden crash in the current notebook**

Run: `$PY -m pytest rates_volatility_model/tests/test_notebook_executes.py -q -rx`
Expected: `1 xfailed`. To see the reason, add `--runxfail`: the test then fails with `AttributeError: module 'numpy' has no attribute 'trapz'`.

- [ ] **Step 3: Write the Chapter 0–6 rewire script**

Save as `$SCRATCH/rewire_ch0_6.py` (any scratch directory outside the repository; it is not committed):

```python
"""Rewire Chapters 0-6 of rates_volatility_models.ipynb onto the ratesvol package."""

import sys

import nbformat

PATH = sys.argv[1]
nb = nbformat.read(PATH, as_version=4)


def cell(cid):
    found = [c for c in nb.cells if c.get("id") == cid]
    assert len(found) == 1, f"cell {cid} not found exactly once"
    return found[0]


def set_source(cid, src):
    cell(cid).source = src.strip("\n") + "\n"


def replace(cid, old, new):
    c = cell(cid)
    assert c.source.count(old) == 1, f"{cid}: expected one match for {old[:50]!r}"
    c.source = c.source.replace(old, new)


# ---------------------------------------------------------------- Ch0
set_source("83c49f15", r'''
import numpy as np
import matplotlib.pyplot as plt
import japanize_matplotlib  # noqa: F401  日本語ラベル用

from ratesvol.curves import discount_factor, instantaneous_forward

plt.rcParams['figure.figsize'] = (12, 6)
RNG = np.random.default_rng(42)  # 全章で共有する乱数生成器（再実行で同じ結果）

T_array = np.linspace(0.5, 10, 50)
curves = {
    'Flat': np.full_like(T_array, 0.02),
    'Upward': 0.02 + 0.01 * (1 - np.exp(-T_array / 5)),
    'Inverted': 0.03 - 0.01 * (1 - np.exp(-T_array / 3)),
}

print("Ch0: Yield Curve Basics")
print("=" * 60)
for name, z in curves.items():
    print(f"{name:>8} curve: zero {z[0]*100:.2f}% -> {z[-1]*100:.2f}%")

fig, axes = plt.subplots(1, 3, figsize=(15, 4))
for name, z in curves.items():
    axes[0].plot(T_array, z * 100, label=name)
    axes[1].plot(T_array, instantaneous_forward(z, T_array) * 100, label=name)
    axes[2].plot(T_array, discount_factor(z, T_array), label=name)
titles = ['Zero rate z(0,T) (%)', 'Instantaneous forward f(0,T) = z + T dz/dT (%)',
          'Discount factor P(0,T)']
for ax, title in zip(axes, titles):
    ax.set_title(title, fontsize=10)
    ax.set_xlabel('Maturity (years)')
    ax.grid(True, alpha=0.3)
    ax.legend()
plt.tight_layout()
plt.show()
''')

# ---------------------------------------------------------------- Ch1
set_source("5066fcf0", r'''
from ratesvol.options import (black76_call, black76_delta, black76_gamma,
                              black76_vega_per_vol_pt)

F, K, T, vol = 0.05, 0.05, 1.0, 0.20

print("Ch1: Black 76 Model")
print("=" * 60)
print(f"Forward: {F*100:.1f}%, Strike: {K*100:.1f}%, T: {T:.1f}y, Vol: {vol*100:.1f}%")
print(f"Price:  {black76_call(F, K, T, vol)*1e4:.4f} bp of notional (df = 1)")
print(f"Delta:  {black76_delta(F, K, T, vol):.4f}")
print(f"Gamma:  {black76_gamma(F, K, T, vol):.4f} (per unit move in F)")
print(f"Vega:   {black76_vega_per_vol_pt(F, K, T, vol)*1e4:.4f} bp per 1 vol-point")
''')

# ---------------------------------------------------------------- Ch2
set_source("7eca6d1b", r'''
from ratesvol.options import bachelier_call, bachelier_delta, bachelier_vega_per_bp

F, K, T, vol_n = 0.02, 0.02, 1.0, 0.005

print("Ch2: Bachelier / Normal Model")
print("=" * 60)
print(f"Forward: {F*100:.1f}%, Strike: {K*100:.1f}%, T: {T:.1f}y, Normal vol: {vol_n*1e4:.0f} bp")
print(f"Price:  {bachelier_call(F, K, T, vol_n)*1e4:.4f} bp of notional (df = 1)")
print(f"Delta:  {bachelier_delta(F, K, T, vol_n):.4f}")
print(f"Vega:   {bachelier_vega_per_bp(F, K, T, vol_n)*1e4:.4f} bp per 1bp of normal vol")
# マイナス金利でも価格が付く（Black-76 は F <= 0 を扱えない）
print(f"F = -0.20%, K = 0.00% の call: {bachelier_call(-0.002, 0.0, 1.0, 0.006)*1e4:.4f} bp")
''')

# ---------------------------------------------------------------- Ch3 Vasicek
set_source("740f9884", r'''
from ratesvol.short_rate import vasicek_simulate, vasicek_terminal_moments

r0, a_val, b_val, sigma_val = 0.03, 0.15, 0.05, 0.02
T, n_steps, n_paths = 10.0, 100, 1000

print("Parameters:")
print(f"  r0: {r0*100:.2f}%  a: {a_val}  b: {b_val*100:.2f}%  sigma: {sigma_val*100:.2f}%")
print(f"  T: {T} years, n_paths: {n_paths}")

paths = vasicek_simulate(r0, a_val, b_val, sigma_val, T, n_steps, n_paths, RNG)
mean_th, std_th = vasicek_terminal_moments(r0, a_val, b_val, sigma_val, T)

print(f"\nr_T at T={T}:")
print(f"  MC mean {paths[:, -1].mean()*100:.3f}%  (theory {mean_th*100:.3f}%)")
print(f"  MC std  {paths[:, -1].std()*100:.3f}%  (theory {std_th*100:.3f}%)")
print(f"  長期平均 b={b_val*100:.2f}% へは T->inf で近づく"
      f"（T={T:.0f} では初期差の e^(-aT)={np.exp(-a_val*T):.2f} 倍が残る）")
''')

set_source("d96aa475", r'''
# ===== Vasicek 動的可視化（ipywidgets）=====
from ipywidgets import FloatSlider, interact
from scipy.stats import norm as sp_norm


def plot_vasicek_sensitivity(a_param, b_param, sigma_param):
    """a, b, sigma をスライダーで調整し、パスと終端分布の変化を見る。"""
    r0, T, n_steps, n_paths = 0.03, 10.0, 100, 500
    paths = vasicek_simulate(r0, a_param, b_param, sigma_param, T, n_steps, n_paths, RNG)
    time_grid = np.linspace(0, T, n_steps + 1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Vasicek Sensitivity: a={a_param:.2f}, b={b_param*100:.2f}%, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')

    for i in range(100):
        axes[0].plot(time_grid, paths[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    axes[0].plot(time_grid, paths.mean(axis=0) * 100, 'r-', linewidth=2.5, label='Mean Path')
    axes[0].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[0].set_xlabel('Time (years)')
    axes[0].set_ylabel('Short Rate (%)')
    axes[0].set_title('Short Rate Paths (Blue) vs Mean (Red)', fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    axes[1].hist(paths[:, -1] * 100, bins=50, density=True, alpha=0.7, color='skyblue', edgecolor='black')
    mean_th, std_th = vasicek_terminal_moments(r0, a_param, b_param, sigma_param, T)
    x_range = np.linspace(mean_th - 4 * std_th, mean_th + 4 * std_th, 200)
    # 横軸を % にしたので密度も 1/100 倍する
    axes[1].plot(x_range * 100, sp_norm.pdf(x_range, mean_th, std_th) / 100, 'r-', linewidth=2,
                 label='Theoretical')
    axes[1].set_xlabel('Short Rate at T (%)')
    axes[1].set_ylabel('Density')
    axes[1].set_title(f'Terminal Distribution (T={T} years)', fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


interact(
    plot_vasicek_sensitivity,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.15, description='a:'),
    b_param=FloatSlider(min=0.01, max=0.10, step=0.005, value=0.05, description='b:'),
    sigma_param=FloatSlider(min=0.001, max=0.05, step=0.005, value=0.02, description='σ:'),
)
''')

replace("2949d726",
        "市場の zero curve が観測されているとき、 $a, b, \\sigma$ を推定します。",
        "市場の zero curve が観測されているとき、 $r_0, a, b, \\sigma$ を推定します。\n\n"
        "**注意**: 長期金利は $b - \\sigma^2/(2a^2)$ で決まるため、カーブだけでは $b$ と $\\sigma$ を"
        "分離できません（同じくらい当たる組が多数あります）。実務では $\\sigma$ をキャップ・"
        "スワップション価格から決めます。")

set_source("33ad2205", r'''
from ratesvol.short_rate import calibrate_vasicek, vasicek_zero_rate

T_cal = np.linspace(0.5, 10, 20)
market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_cal / 5))  # Upward curve

(r0_cal, a_cal, b_cal, sigma_cal), rmse_bp = calibrate_vasicek(T_cal, market_zero_curve)
print(f"Calibrated: r0={r0_cal*100:.3f}%, a={a_cal:.4f}, b={b_cal*100:.3f}%, σ={sigma_cal*100:.3f}%")
print(f"RMSE: {rmse_bp:.2f} bp")
print(f"長期金利 b - σ²/(2a²) = {(b_cal - sigma_cal**2 / (2 * a_cal**2))*100:.3f}%")

model_zero = vasicek_zero_rate(r0_cal, a_cal, b_cal, sigma_cal, T_cal)
for T, z_mkt, z_mdl in zip(T_cal[::4], market_zero_curve[::4], model_zero[::4]):
    print(f"  T={T:4.1f}y: Market={z_mkt*100:.3f}% Model={z_mdl*100:.3f}% Diff={(z_mdl-z_mkt)*1e4:+.2f}bp")
''')

# ---------------------------------------------------------------- Ch4 CIR
replace("f3029894",
        "CIR が非負を保つためには：\n\n$$2ab \\geq \\sigma^2$$\n\n"
        "この条件が満たされれば、$r_t \\geq 0$ が保証されます。",
        "CIR の短期金利は常に $r_t \\geq 0$ です。さらに\n\n$$2ab \\geq \\sigma^2$$\n\n"
        "が成り立てば $r_t$ は 0 に到達しません（厳密に正）。")
replace("f3029894",
        "- 金利がゼロに達すると、$\\sqrt{r_t}$ の項がゼロになり反射\n"
        "- Boundary condition: $r_t$ がゼロに達すると反射",
        "- $r_t$ は 0 に到達し得るが、$\\sqrt{r_t}$ の項が消えてドリフト $ab>0$ で直ちに押し戻される（瞬間反射）\n"
        "- 離散化（Euler）では負値が出るので、下の実装は full truncation（$\\max(r,0)$ を使う）で扱う")
replace("c3dca17a", "- ✅ **非負性を保証**（Feller条件下で）",
        "- ✅ **非負**（Feller 条件下では厳密に正）")

set_source("9d0dca12", r'''
from ratesvol.short_rate import cir_simulate, feller_condition

r0, a_val, b_val, sigma_val = 0.03, 0.15, 0.05, 0.02
T, n_steps, n_paths = 10.0, 100, 1000

print(f"Parameters: a={a_val}, b={b_val*100:.2f}%, σ={sigma_val*100:.2f}%")
print(f"Feller Condition (2ab >= σ²): {feller_condition(a_val, b_val, sigma_val)}")
print(f"  2ab = {2*a_val*b_val:.6f}")
print(f"  σ² = {sigma_val**2:.6f}")

paths_cir = cir_simulate(r0, a_val, b_val, sigma_val, T, n_steps, n_paths, RNG)
print("\nCIR Simulation:")
print(f"  Terminal mean: {paths_cir[:, -1].mean()*100:.4f}%  "
      f"(theory {(b_val + (r0 - b_val) * np.exp(-a_val * T))*100:.4f}%)")
print(f"  Terminal min: {paths_cir[:, -1].min()*100:.4f}%")
print(f"  Terminal max: {paths_cir[:, -1].max()*100:.4f}%")
print(f"  Share of (path, time) points at r = 0: {(paths_cir == 0).mean()*100:.2f}%")
''')

set_source("0d1042ca", r'''
# ===== Vasicek vs CIR 比較 + ipywidgets =====
from ipywidgets import FloatSlider, interact


def plot_vasicek_vs_cir(a_param, b_param, sigma_param):
    """同じ (a, b, σ) で Vasicek と CIR のパスを並べる。"""
    r0, T, n_steps, n_paths = 0.03, 10.0, 100, 500
    paths_vasicek = vasicek_simulate(r0, a_param, b_param, sigma_param, T, n_steps, n_paths, RNG)
    paths_cir = cir_simulate(r0, a_param, b_param, sigma_param, T, n_steps, n_paths, RNG)
    time_grid = np.linspace(0, T, n_steps + 1)
    feller_ok = feller_condition(a_param, b_param, sigma_param)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Vasicek vs CIR: a={a_param:.2f}, b={b_param*100:.2f}%, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')

    for i in range(100):
        axes[0].plot(time_grid, paths_vasicek[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    axes[0].plot(time_grid, paths_vasicek.mean(axis=0) * 100, 'b-', linewidth=2.5, label='Vasicek Mean')
    axes[0].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[0].set_xlabel('Time (years)')
    axes[0].set_ylabel('Short Rate (%)')
    axes[0].set_title('Vasicek Paths (Can go negative)', fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    for i in range(100):
        axes[1].plot(time_grid, paths_cir[i, :] * 100, 'r-', alpha=0.1, linewidth=0.5)
    axes[1].plot(time_grid, paths_cir.mean(axis=0) * 100, 'r-', linewidth=2.5, label='CIR Mean')
    axes[1].axhline(b_param * 100, color='green', linestyle='--', linewidth=2, label='Long-term Mean')
    axes[1].axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    axes[1].set_xlabel('Time (years)')
    axes[1].set_ylabel('Short Rate (%)')
    feller_str = "Feller OK (never hits 0)" if feller_ok else "Feller violated (can touch 0)"
    axes[1].set_title(f'CIR Paths (non-negative) - {feller_str}', fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


interact(
    plot_vasicek_vs_cir,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.15, description='a:'),
    b_param=FloatSlider(min=0.01, max=0.10, step=0.005, value=0.05, description='b:'),
    sigma_param=FloatSlider(min=0.001, max=0.05, step=0.005, value=0.02, description='σ:'),
)
''')

# ---------------------------------------------------------------- Ch5 Hull-White
set_source("122f2370", r'''
from ratesvol.short_rate import hw1f_theta, hw1f_simulate, mc_zcb_from_short_rate

T_grid = np.linspace(0, 10, 201)
market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_grid / 5))
a_param, sigma_param = 0.1, 0.01

theta_array = hw1f_theta(T_grid, market_zero_curve, a_param, sigma_param)
print("Hull-White theta(t) from market zero curve:")
print(f"Parameters: a={a_param}, σ={sigma_param*100:.2f}%")
for t, theta in zip(T_grid[::40], theta_array[::40]):
    print(f"  t={t:4.1f}y: θ(t)={theta*100:7.4f}%")

# 初期カーブへのフィットを MC で確認: E[exp(-∫r dt)] = P_market(0,T)
print("\nZero-coupon bond: MC under HW1F vs market")
for T_chk in [2.0, 5.0, 10.0]:
    paths = hw1f_simulate(T_grid, market_zero_curve, a_param, sigma_param,
                          T_chk, int(T_chk * 100), 20000, RNG)
    p_mc, se = mc_zcb_from_short_rate(paths, T_chk)
    p_mkt = np.exp(-np.interp(T_chk, T_grid, market_zero_curve) * T_chk)
    print(f"  T={T_chk:4.1f}y: MC {p_mc:.5f} ± {se:.5f}   market {p_mkt:.5f}")
''')

set_source("d47b1084", r'''
# ===== Hull-White Path + Initial Curve Fit =====
from ipywidgets import FloatSlider, interact


def plot_hw1f_analysis(a_param, sigma_pct):
    """Hull-White のパスと、初期カーブから作ったドリフト θ(t)。"""
    T_grid = np.linspace(0, 10, 201)
    market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_grid / 5))
    sigma_param = sigma_pct / 100
    theta_array = hw1f_theta(T_grid, market_zero_curve, a_param, sigma_param)

    T, n_steps, n_paths = 10.0, 100, 300
    paths = hw1f_simulate(T_grid, market_zero_curve, a_param, sigma_param, T, n_steps, n_paths, RNG)
    time_grid = np.linspace(0, T, n_steps + 1)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'Hull-White 1F: a={a_param:.2f}, σ={sigma_param*100:.2f}%',
                 fontsize=12, fontweight='bold')

    for i in range(100):
        axes[0].plot(time_grid, paths[i, :] * 100, 'b-', alpha=0.1, linewidth=0.5)
    axes[0].plot(time_grid, paths.mean(axis=0) * 100, 'r-', linewidth=2.5, label='Mean Path')
    axes[0].set_xlabel('Time (years)')
    axes[0].set_ylabel('Short Rate (%)')
    axes[0].set_title('HW1F Short Rate Paths', fontweight='bold')
    axes[0].legend(fontsize=9)
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(T_grid, market_zero_curve * 100, 'g-', linewidth=2, label='Market Zero Curve')
    ax2 = axes[1].twinx()
    ax2.plot(T_grid, theta_array * 100, 'b-', linewidth=2, label='θ(t) drift')
    axes[1].set_xlabel('Time (years)')
    axes[1].set_ylabel('Zero Rate (%)', color='g')
    ax2.set_ylabel('θ(t) (%)', color='b')
    axes[1].set_title('Initial Curve & HW Drift', fontweight='bold')
    axes[1].tick_params(axis='y', labelcolor='g')
    ax2.tick_params(axis='y', labelcolor='b')
    axes[1].grid(True, alpha=0.3)
    lines1, labels1 = axes[1].get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    axes[1].legend(lines1 + lines2, labels1 + labels2, fontsize=9)

    plt.tight_layout()
    plt.show()


interact(
    plot_hw1f_analysis,
    a_param=FloatSlider(min=0.01, max=1.0, step=0.05, value=0.1, description='a:'),
    sigma_pct=FloatSlider(min=0.1, max=5, step=0.2, value=1, description='σ (%):'),
)
''')

# ---------------------------------------------------------------- Ch6 G2++
replace("f992a6a3",
        "- $\\phi(t)$ = Deterministic term (initial curve fit)",
        "- $\\phi(t)$ = Deterministic term (initial curve fit)\n\n"
        "初期カーブに合わせる $\\phi(t)$（Brigo-Mercurio 式 4.12）:\n\n"
        "$$\\phi(t) = f^M(0,t) + \\frac{\\sigma^2}{2a^2}(1-e^{-at})^2 + \\frac{\\eta^2}{2b^2}(1-e^{-bt})^2"
        " + \\rho\\frac{\\sigma\\eta}{ab}(1-e^{-at})(1-e^{-bt})$$")

set_source("41457d7d", r'''
from ratesvol.short_rate import g2pp_phi, g2pp_simulate, mc_zcb_from_short_rate

T_grid = np.linspace(0, 10, 201)
market_zero_curve = 0.02 + 0.03 * (1 - np.exp(-T_grid / 5))
a, b, sigma, eta, rho = 0.1, 0.03, 0.01, 0.005, -0.5
T, n_steps, n_paths = 10.0, 1000, 20000

x_paths, y_paths, r_paths = g2pp_simulate(T_grid, market_zero_curve, a, b, sigma, eta, rho,
                                          T, n_steps, n_paths, RNG)
print("G2++ Simulation (φ(t) fitted to the market curve):")
print(f"Parameters: a={a}, b={b}, σ={sigma*100:.2f}%, η={eta*100:.2f}%, ρ={rho}")
print(f"Terminal r_T: mean {r_paths[:, -1].mean()*100:.4f}%, std {r_paths[:, -1].std()*100:.4f}%")

p_mc, se = mc_zcb_from_short_rate(r_paths, T)
p_mkt = np.exp(-np.interp(T, T_grid, market_zero_curve) * T)
print(f"P(0,{T:.0f}y): MC {p_mc:.5f} ± {se:.5f}   market {p_mkt:.5f}")
''')

set_source("7aaa0880", r'''
# ===== G2++ Interactive: 相関ρの効果を可視化 =====
from ipywidgets import FloatSlider, interact
from scipy.stats import norm as sp_norm


def plot_g2pp_analysis(rho_param, a_param, b_param):
    """2 ファクターの動きと、相関 ρ を変えたときの r_T の分布。"""
    sigma_param, eta_param = 0.01, 0.005
    T, n_steps, n_paths = 10.0, 100, 300
    x_paths, y_paths, r_paths = g2pp_simulate(
        T_grid, market_zero_curve, a_param, b_param, sigma_param, eta_param, rho_param,
        T, n_steps, n_paths, RNG,
    )
    time_grid = np.linspace(0, T, n_steps + 1)
    phi = np.array([g2pp_phi(t, T_grid, market_zero_curve, a_param, b_param,
                             sigma_param, eta_param, rho_param) for t in time_grid])

    fig, axes = plt.subplots(2, 2, figsize=(14, 9))
    fig.suptitle(f'G2++: a={a_param:.2f}, b={b_param:.2f}, σ={sigma_param*100:.1f}%, '
                 f'η={eta_param*100:.1f}%, ρ={rho_param:.2f}', fontsize=12, fontweight='bold')

    for ax, paths, color, name in [(axes[0, 0], x_paths, 'b', 'x_t (factor a)'),
                                   (axes[0, 1], y_paths, 'g', 'y_t (factor b)')]:
        for i in range(50):
            ax.plot(time_grid, paths[i, :] * 100, f'{color}-', alpha=0.2, linewidth=0.5)
        ax.plot(time_grid, paths.mean(axis=0) * 100, f'{color}-', linewidth=2, label=f'Mean {name}')
        ax.axhline(0, color='k', alpha=0.3)
        ax.set_ylabel(f'{name} (%)')
        ax.set_title(name, fontweight='bold')
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)

    for i in range(50):
        axes[1, 0].plot(time_grid, r_paths[i, :] * 100, 'r-', alpha=0.2, linewidth=0.5)
    axes[1, 0].plot(time_grid, r_paths.mean(axis=0) * 100, 'r-', linewidth=2, label='Mean r_t')
    axes[1, 0].plot(time_grid, phi * 100, 'k--', alpha=0.7, label='φ(t) (curve fit)')
    axes[1, 0].set_xlabel('Time (years)')
    axes[1, 0].set_ylabel('r_t (%)')
    axes[1, 0].set_title('Total Short Rate: r_t = x_t + y_t + φ(t)', fontweight='bold')
    axes[1, 0].legend(fontsize=9)
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].hist(r_paths[:, -1] * 100, bins=40, density=True, alpha=0.7,
                    color='skyblue', edgecolor='black', label='Empirical')
    mean_term, std_term = r_paths[:, -1].mean(), r_paths[:, -1].std()
    x_range = np.linspace(mean_term - 4 * std_term, mean_term + 4 * std_term, 200)
    axes[1, 1].plot(x_range * 100, sp_norm.pdf(x_range, mean_term, std_term) / 100,
                    'r-', linewidth=2, label='Normal fit')
    axes[1, 1].set_xlabel('r_T (%)')
    axes[1, 1].set_ylabel('Density')
    axes[1, 1].set_title('Terminal r_T Distribution', fontweight='bold')
    axes[1, 1].legend(fontsize=9)
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


interact(
    plot_g2pp_analysis,
    rho_param=FloatSlider(min=-0.9, max=0.9, step=0.1, value=-0.5, description='ρ:'),
    a_param=FloatSlider(min=0.01, max=0.5, step=0.05, value=0.1, description='a:'),
    b_param=FloatSlider(min=0.001, max=0.1, step=0.01, value=0.03, description='b:'),
)
''')

nbformat.write(nb, PATH)
print("rewired Ch0-6")
```

- [ ] **Step 4: Apply it**

Run: `$PY $SCRATCH/rewire_ch0_6.py rates_volatility_model/rates_volatility_models.ipynb`
Expected: prints `rewired Ch0-6`. Any `AssertionError: cell ... not found` or `expected one match` means the notebook differs from the reviewed version — stop and report.

- [ ] **Step 5: Verify Chapters 0–6 now run and the failure moved nowhere**

Run: `$PY -m pytest rates_volatility_model/tests/test_notebook_executes.py -q --runxfail 2>&1 | grep -o "AttributeError.*trapz'" | sort -u`
Expected: `AttributeError: module 'numpy' has no attribute 'trapz'` — i.e. execution now gets through every rewired cell and still stops at the HJM cell, which Task 6 fixes. Then `$PY -m pytest rates_volatility_model/tests -q` → `60 passed, 1 xfailed`.

- [ ] **Step 6: Commit**

```bash
git add rates_volatility_model/tests/test_notebook_executes.py rates_volatility_model/rates_volatility_models.ipynb
git commit -m "fix(rates_volatility_model): run chapters 0-6 on ratesvol and add a notebook execution test"
```

---

### Task 6: Chapters 7–10 and the comparison chapter

**Files:**
- Modify: `rates_volatility_model/rates_volatility_models.ipynb` — cells `e59676d6`, `b1207d2e`, `bdc15fa9`, `5bd8fa3b`, `6b8c4b50`, `a17337d8`, `9417952b`, `dfe9c5f8`, `9a26fd94`, `c63a99a0`, `681b951c`, `b726fb30`, `13b8e5aa`, `0d47d24d`, `0ab5b8d0`; delete cells `5ac8a9d6`, `eab070d5`
- Modify: `rates_volatility_model/tests/test_notebook_executes.py` (remove the xfail marker)

**Interfaces:**
- Consumes: `ratesvol.market_models`, `ratesvol.smile`, `ratesvol.rfr`, `ratesvol.options` (Tasks 1, 3, 4); notebook global `RNG`.
- Produces: notebook globals `sabr_black_vol`, `calibrate_sabr`, `sabr_alpha_from_atm_vol` (imported in `9417952b`) used by Chapter 11 in Task 7.

- [ ] **Step 1: Remove the xfail marker and confirm the test now fails for real**

Delete the `@pytest.mark.xfail(...)` line and the `import pytest` line added in Task 5 step 1.
Run: `$PY -m pytest rates_volatility_model/tests/test_notebook_executes.py -q`
Expected: `1 failed` with `AttributeError: module 'numpy' has no attribute 'trapz'`.

- [ ] **Step 2: Write the Chapter 7–10 rewire script**

Save as `$SCRATCH/rewire_ch7_10.py`:

```python
"""Rewire Chapters 7-10 and the comparison chapter onto the ratesvol package."""

import sys

import nbformat

PATH = sys.argv[1]
nb = nbformat.read(PATH, as_version=4)


def cell(cid):
    found = [c for c in nb.cells if c.get("id") == cid]
    assert len(found) == 1, f"cell {cid} not found exactly once"
    return found[0]


def set_source(cid, src):
    cell(cid).source = src.strip("\n") + "\n"


def replace(cid, old, new):
    c = cell(cid)
    assert c.source.count(old) == 1, f"{cid}: expected one match for {old[:50]!r}"
    c.source = c.source.replace(old, new)


def delete(cid):
    nb.cells.remove(cell(cid))


# ---------------------------------------------------------------- Ch7 HJM
set_source("e59676d6", r'''
from ratesvol.market_models import hjm_drift, hjm_simulate

T_hjm = np.linspace(0.1, 10, 50)
f0_hjm = 0.02 + 0.03 * (1 - np.exp(-T_hjm / 5))


def vol_parallel(t, T):
    return 0.01


# 無裁定ドリフトの確認: σ 一定なら α(t,T) = σ²(T - t)（T <= t では 0）
t_chk = 2.0
alpha = hjm_drift(t_chk, T_hjm, vol_parallel)
expected = np.where(T_hjm > t_chk, 0.01**2 * (T_hjm - t_chk), 0.0)
print(f"max |α(t,T) - σ²(T-t)| at t={t_chk}: {np.abs(alpha - expected).max():.2e}")

# MC: σ 一定（Ho-Lee）なら E[f(t,T)] = f(0,T) + σ² t (T - t/2)
t_grid = np.linspace(0, 5, 51)
fc = hjm_simulate(T_hjm, f0_hjm, vol_parallel, t_grid, 2000, RNG)
t_end, T_last = t_grid[-1], T_hjm[-1]
mean_th = f0_hjm[-1] + 0.01**2 * t_end * (T_last - t_end / 2)
se = fc[:, -1, -1].std() / np.sqrt(fc.shape[0])
print(f"E[f({t_end:.0f}y, {T_last:.0f}y)]: MC {fc[:, -1, -1].mean()*100:.4f}% ± {se*100:.4f}%"
      f"   theory {mean_th*100:.4f}%")
''')

set_source("b1207d2e", r'''
# ===== HJM Forward Curve Evolution 可視化 =====
from ipywidgets import RadioButtons, interact

VOL_SHAPES = {
    'Parallel': ('Parallel Shifts', lambda t, T: 0.01),
    'Hump': ('Hump-Shaped Vol', lambda t, T: 0.01 * np.exp(-(T - 5) ** 2 / 10)),
    'Downward': ('Downward Sloping Vol', lambda t, T: 0.015 - 0.001 * T),
}


def plot_hjm_forward_evolution(vol_type):
    """ボラティリティ構造ごとのフォワードカーブの動き（1 パス）と σ(T)。"""
    title_suffix, vol_func = VOL_SHAPES[vol_type]
    t_array = np.linspace(0, 5, 11)
    forward_curves = hjm_simulate(T_hjm, f0_hjm, vol_func, t_array, 200, RNG)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'HJM Framework: {title_suffix}', fontsize=12, fontweight='bold')

    for i in range(0, len(t_array), 2):
        axes[0].plot(T_hjm, forward_curves[0, i, :] * 100,
                     alpha=0.3 + 0.7 * (i / len(t_array)), linewidth=1.5,
                     label=f't={t_array[i]:.1f}y')
    axes[0].set_xlabel('Maturity T (years)')
    axes[0].set_ylabel('Forward Rate f(t,T) (%)')
    axes[0].set_title('Forward Curve Evolution (one path; T <= t is frozen)', fontweight='bold')
    axes[0].legend(fontsize=8, loc='best')
    axes[0].grid(True, alpha=0.3)

    vols = np.broadcast_to(vol_func(2.5, T_hjm), T_hjm.shape)
    axes[1].plot(T_hjm, vols * 100, 'b-', linewidth=2, label='σ(t,T)')
    axes[1].plot(T_hjm, hjm_drift(0.0, T_hjm, vol_func) * 1e4, 'r--', linewidth=2,
                 label='drift α(0,T) (bp / year)')
    axes[1].set_xlabel('Maturity T (years)')
    axes[1].set_title('Volatility Structure and No-Arbitrage Drift', fontweight='bold')
    axes[1].legend(fontsize=9)
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


interact(
    plot_hjm_forward_evolution,
    vol_type=RadioButtons(options=list(VOL_SHAPES), description='Vol Shape:', value='Parallel'),
)
''')

# ---------------------------------------------------------------- Ch8 LMM
replace("bdc15fa9",
        "**ポイント:**\n- 各テナーが独立のブラウン運動\n- Lognormal distributionを仮定\n"
        "- Caplet = Black76 formula で直接価格付け",
        "**ポイント:**\n"
        "- 上の式はドリフトがない。これは $L_i$ を **自身の $T_{i+1}$-フォワード測度** で見たとき"
        "だけ成り立つ\n"
        "- 全フォワードを **一つの測度（spot 測度）** で同時に動かすとドリフトが付く:\n\n"
        "$$\\mu_i(t) = \\sigma_i \\sum_{j=\\eta(t)}^{i} \\frac{\\tau_j \\rho_{ij} \\sigma_j L_j(t)}"
        "{1 + \\tau_j L_j(t)}$$\n\n"
        "  （$\\eta(t)$ = まだ fixing していない最初のフォワード、Glasserman 2003 式 3.112）\n"
        "- ブラウン運動は **相関 $\\rho_{ij}$** を持つ（独立ではない）\n"
        "- Caplet は Black-76 で価格付けできる。下の MC はこれを spot 測度で再現して確かめる")

set_source("5bd8fa3b", r'''
from ratesvol.market_models import lmm_fixings, lmm_simulate_spot, spot_numeraire
from ratesvol.options import black76_call

tenor_dates = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0])  # T_0 .. T_N（半年ごと）
L0 = np.array([0.030, 0.032, 0.034, 0.035, 0.036, 0.036])    # L_i は [T_i, T_{i+1}] のフォワード
lmm_vols = np.array([0.20, 0.19, 0.18, 0.17, 0.16, 0.15])
starts = tenor_dates[:-1]
corr_matrix = np.exp(-0.3 * np.abs(np.subtract.outer(starts, starts)))
tau = np.diff(tenor_dates)

times, L_paths = lmm_simulate_spot(tenor_dates, L0, lmm_vols, corr_matrix, 10, 20000, RNG)
fixings = lmm_fixings(times, L_paths, tenor_dates)
B = spot_numeraire(fixings, tenor_dates)
P0 = np.cumprod(1 / (1 + tau * L0))

print("無裁定チェック 1: E[1/B(T_n)] = P(0,T_n)")
for n in [2, 4, 6]:
    x = 1 / B[:, n - 1]
    print(f"  T={tenor_dates[n]:.1f}y: MC {x.mean():.5f} ± {x.std()/np.sqrt(len(x)):.5f}"
          f"   P(0,T) {P0[n-1]:.5f}")

print("無裁定チェック 2: ATM caplet の MC 価格 = Black-76")
for k in [1, 3, 5]:
    K = L0[k]
    pay = tau[k] * np.maximum(fixings[:, k] - K, 0) / B[:, k]
    black = P0[k] * tau[k] * black76_call(L0[k], K, tenor_dates[k], lmm_vols[k])
    print(f"  L_{k} ({tenor_dates[k]:.1f}y->{tenor_dates[k+1]:.1f}y): MC {pay.mean()*1e4:.3f} ± "
          f"{pay.std()/np.sqrt(len(pay))*1e4:.3f} bp   Black-76 {black*1e4:.3f} bp")
''')

set_source("6b8c4b50", r'''
# ===== LMM Forward Rate Paths + Correlation Heatmap =====
fig, axes = plt.subplots(2, 4, figsize=(16, 8))
fig.suptitle('LMM under the spot measure: forward rates L_i(t)', fontsize=12, fontweight='bold')
axes = axes.flatten()

for i in range(len(L0)):
    ax = axes[i]
    for path_idx in range(100):
        ax.plot(times, L_paths[path_idx, :, i] * 100, 'b-', alpha=0.1, linewidth=0.5)
    ax.plot(times, L_paths[:, :, i].mean(axis=0) * 100, 'r-', linewidth=2, label='Mean')
    ax.axvline(tenor_dates[i], color='k', linestyle=':', label='fixing T_i')
    ax.set_title(f'L_{i}: [{tenor_dates[i]:.1f}y, {tenor_dates[i+1]:.1f}y]', fontsize=10)
    ax.set_xlabel('Time (years)', fontsize=9)
    ax.set_ylabel('Rate (%)', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7)

ax = axes[6]
im = ax.imshow(corr_matrix, cmap='RdBu_r', vmin=0, vmax=1)
labels = [f'L_{i}' for i in range(len(L0))]
ax.set_xticks(range(len(L0)))
ax.set_yticks(range(len(L0)))
ax.set_xticklabels(labels, fontsize=8)
ax.set_yticklabels(labels, fontsize=8)
ax.set_title('Correlation ρ_ij = exp(-0.3 |T_i - T_j|)', fontsize=10)
for i in range(len(L0)):
    for j in range(len(L0)):
        ax.text(j, i, f'{corr_matrix[i, j]:.2f}', ha='center', va='center', fontsize=7)
plt.colorbar(im, ax=ax)
axes[7].set_visible(False)

plt.tight_layout()
plt.show()
''')

# ---------------------------------------------------------------- Ch9 SABR
replace("a17337d8", "- $\\alpha$ = Volatility of volatility (initial)",
        "- $\\alpha$ = 初期ボラティリティ水準 $\\alpha_0$（vol-of-vol ではない）")
delete("5ac8a9d6")  # duplicated LMM definition that sat under the SABR heading
set_source("9417952b", r'''
from ratesvol.smile import calibrate_sabr, sabr_alpha_from_atm_vol, sabr_black_vol
''')

set_source("dfe9c5f8", r'''
# ===== SABR Interactive: Smile/Skew 動的可視化 =====
from ipywidgets import FloatSlider, interact


def plot_sabr_smile(atm_vol_pct, beta_param, rho_param, nu_param):
    """ATM vol を固定したまま β, ρ, ν を動かす（α は ATM vol から逆算）。"""
    F_atm, T = 0.03, 1.0
    alpha = sabr_alpha_from_atm_vol(F_atm, T, atm_vol_pct / 100, beta_param, rho_param, nu_param)
    strikes = np.linspace(0.01, 0.05, 100)
    impl_vols = np.array([sabr_black_vol(F_atm, K, T, alpha, beta_param, rho_param, nu_param)
                          for K in strikes])

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(f'SABR Smile: ATM vol={atm_vol_pct:.0f}% (α={alpha:.4f}), β={beta_param:.2f}, '
                 f'ρ={rho_param:.2f}, ν={nu_param:.2f}', fontsize=12, fontweight='bold')

    axes[0].plot(strikes * 100, impl_vols * 100, 'b-', linewidth=2.5, label='SABR Smile')
    axes[0].axvline(F_atm * 100, color='r', linestyle='--', alpha=0.7, linewidth=2, label='ATM')
    axes[0].set_xlabel('Strike (%)')
    axes[0].set_ylabel('Black Implied Volatility (%)')
    axes[0].set_title('Smile / Skew Shape', fontweight='bold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    dv = 0.001
    sens = [(sabr_black_vol(F_atm, K, T, alpha, beta_param, rho_param, nu_param + dv)
             - sabr_black_vol(F_atm, K, T, alpha, beta_param, rho_param, nu_param - dv)) / (2 * dv)
            for K in strikes]
    axes[1].plot(strikes * 100, sens, 'g-', linewidth=2.5)
    axes[1].axvline(F_atm * 100, color='r', linestyle='--', alpha=0.7, linewidth=2)
    axes[1].set_xlabel('Strike (%)')
    axes[1].set_ylabel('∂σ_impl / ∂ν')
    axes[1].set_title('Implied-vol sensitivity to vol-of-vol ν', fontweight='bold')
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


interact(
    plot_sabr_smile,
    atm_vol_pct=FloatSlider(min=5, max=60, step=1, value=20, description='ATM vol %:'),
    beta_param=FloatSlider(min=0, max=1, step=0.1, value=0.5, description='β:'),
    rho_param=FloatSlider(min=-0.9, max=0.9, step=0.1, value=-0.5, description='ρ:'),
    nu_param=FloatSlider(min=0.01, max=2, step=0.1, value=0.5, description='ν:'),
)
''')

set_source("9a26fd94", r'''
# ===== 疑似市場クォートの生成（True SABR + 2bp ノイズ） =====
F_cal, T_cal, beta_cal = 0.03, 1.0, 0.5
true_alpha, true_rho, true_nu = 0.014, -0.45, 0.45
offsets_bp = np.array([-100, -75, -50, -25, 0, 25, 50, 75, 100])
strikes_cal = F_cal + offsets_bp / 1e4

true_vols = np.array([sabr_black_vol(F_cal, K, T_cal, true_alpha, beta_cal, true_rho, true_nu)
                      for K in strikes_cal])
market_vols_cal = true_vols + RNG.normal(0, 2e-4, len(strikes_cal))

a_fit, r_fit, n_fit, rmse, fitted_v = calibrate_sabr(F_cal, T_cal, strikes_cal, market_vols_cal,
                                                     beta_cal)
print("=== SABR Calibration Demo ===")
print(f"True:   α={true_alpha:.4f}, ρ={true_rho:.3f}, ν={true_nu:.3f}")
print(f"Fitted: α={a_fit:.4f}, ρ={r_fit:.3f}, ν={n_fit:.3f}")
print(f"RMSE: {rmse:.2f} bp")

fine_k = np.linspace(0.005, 0.055, 200)
true_fine = [sabr_black_vol(F_cal, K, T_cal, true_alpha, beta_cal, true_rho, true_nu) for K in fine_k]
fit_fine = [sabr_black_vol(F_cal, K, T_cal, a_fit, beta_cal, r_fit, n_fit) for K in fine_k]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle('SABR Calibration to Market Quotes', fontsize=13, fontweight='bold')
axes[0].plot(fine_k * 100, np.array(true_fine) * 100, 'k--', lw=1.5, label='True SABR')
axes[0].plot(fine_k * 100, np.array(fit_fine) * 100, 'b-', lw=2.5, label=f'Calibrated (RMSE={rmse:.1f}bp)')
axes[0].scatter(strikes_cal * 100, market_vols_cal * 100, color='red', s=60, zorder=5, label='Market quotes')
axes[0].axvline(F_cal * 100, color='gray', ls=':', lw=1.5, label='ATM')
axes[0].set_xlabel('Strike (%)')
axes[0].set_ylabel('Implied Vol (%)')
axes[0].set_title('Smile Fit')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

residuals = (fitted_v - market_vols_cal) * 1e4
axes[1].bar(offsets_bp, residuals, color=['#d62728' if e > 0 else '#1f77b4' for e in residuals], alpha=0.8)
axes[1].axhline(0, color='k', lw=0.8)
axes[1].set_xlabel('Strike Offset (bp)')
axes[1].set_ylabel('Fitted − Market (bp)')
axes[1].set_title('Calibration Residuals')
axes[1].grid(True, alpha=0.3)
plt.tight_layout()
plt.show()
print("詳細は Chapter 11 へ")
''')

replace("c63a99a0", "- ❌ Short maturities では精度低下",
        "- ❌ 長い満期・低いストライクで Hagan 近似が崩れる（確率密度が負＝バタフライ裁定）")

# ---------------------------------------------------------------- Ch10 RFR
replace("681b951c",
        "**LIBOR廃止**（2023年）に伴い、世界の金利市場は **Reference Rate (RFR)** へ移行しました。",
        "**LIBOR 廃止**（GBP・EUR・CHF・JPY の全設定と USD の一部は 2021 年末、残る USD の主要設定は"
        " 2023 年 6 月末で公表停止）に伴い、金利市場は **Risk-Free Rate (RFR)** へ移行しました。")
replace("681b951c", "| **英国** | GBP LIBOR | SONIA | Bank of England政策レート |",
        "| **英国** | GBP LIBOR | SONIA | 無担保翌日物（BoE が算出・公表） |")
replace("681b951c", "| **EU** | EUR LIBOR | ESTR | ECB政策レート |",
        "| **ユーロ圏** | EUR LIBOR | €STR | 無担保翌日物（ECB が算出・公表） |")
replace("681b951c",
        "R(T_{start}, T_{end}) = \\prod_{d=1}^{D}(1 + r_d \\delta_d) - 1",
        "R(T_{start}, T_{end}) = \\frac{1}{\\delta}\\left[\\prod_{d=1}^{D}(1 + r_d \\delta_d) - 1\\right]"
        ",\\quad \\delta = \\sum_d \\delta_d")
delete("eab070d5")  # a SABR smile table that had drifted into the RFR chapter

set_source("b726fb30", r'''
# ===== RFR: 後決め複利（compounded in arrears）と単純平均 =====
from ipywidgets import FloatSlider, interact

from ratesvol.rfr import compounded_in_arrears, simple_average


def plot_rfr_compounding(on_vol_bp, hike_bp):
    """3 か月の O/N fixing から期末に決まるクーポンを計算する（ACT/360）。"""
    days = np.arange(91)                           # 暦日 0..90（0 = 月曜）
    business = days[(days % 7) < 5]               # 月〜金だけ fixing（祝日は無視）
    weights = np.diff(np.append(business, 91))    # 金曜の fixing は土日を含め 3 日分
    rate = 0.05 + (business >= 45) * hike_bp / 1e4
    rate = rate + on_vol_bp / 1e4 * RNG.standard_normal(len(business))

    running = [compounded_in_arrears(rate[:i + 1], weights[:i + 1]) for i in range(len(rate))]
    comp = compounded_in_arrears(rate, weights)
    avg = simple_average(rate, weights)

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.step(business, rate * 100, where='post', color='tab:blue', alpha=0.6, label='O/N fixing')
    ax.plot(business, np.array(running) * 100, color='tab:red', lw=2,
            label='compounded rate so far')
    ax.axhline(avg * 100, color='gray', ls='--', label=f'simple average {avg*100:.4f}%')
    ax.set_xlabel('Calendar day in the accrual period')
    ax.set_ylabel('Rate (%)')
    ax.set_title(f'Compounded in arrears = {comp*100:.4f}%  '
                 f'(複利効果 {(comp - avg)*1e4:+.2f} bp、クーポンは期末まで確定しない)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


interact(
    plot_rfr_compounding,
    on_vol_bp=FloatSlider(min=0, max=10, step=1, value=2, description='O/N noise bp:'),
    hike_bp=FloatSlider(min=0, max=100, step=25, value=25, description='hike bp:'),
)
''')

replace("13b8e5aa",
        "**RFR時代（2023年以降）:**\n- **単一RFR曲線**でDiscounting & Forward rateを統一\n"
        "- LIBOR legacy商品とRFR新商品を区別管理",
        "**RFR時代（2023年以降）:**\n"
        "- RFR スワップは同じ RFR（OIS）カーブで projection と discounting ができる\n"
        "- それでも multi-curve は残る: 担保通貨ごとの割引カーブ、TIBOR・EURIBOR・Term SOFR"
        " などの projection カーブ、クロスカレンシーベーシス\n"
        "- LIBOR legacy商品とRFR新商品を区別管理")
replace("13b8e5aa", "| **Curve数** | Multi-curve（OIS+LIBOR）| Single curve |",
        "| **Curve数** | Multi-curve（OIS+LIBOR）| RFR 商品は 1 本で完結、ただし担保・他指標で複数 |")
replace("13b8e5aa", "| **Smile** | High（LIBOR basis） | Low（単純化） |\n", "")
replace("13b8e5aa", "- ✅ **単一曲線で完結**（シンプル）",
        "- ✅ RFR 商品だけなら 1 本のカーブで完結（シンプル）")
replace("13b8e5aa", "- ❌ RFR basis（テナー別RFRは存在しない）",
        "- ❌ クーポンが期末まで確定しない（後決め）。前決めが必要な商品は Term RFR を使う")

# ---------------------------------------------------------------- Comparison
replace("0d47d24d", "- 計算複雑度",
        "- 計算複雑度\n\n（Complexity と Industry Use は筆者の主観スコア）")
replace("0ab5b8d0",
        "'Smile': ['No', 'No', 'No', 'No', 'No', 'No', 'No', 'No', 'Yes', 'Yes'],",
        "'Smile': ['No', 'No', 'No', 'No', 'No', 'No', 'No', 'No', 'Yes', 'No'],")

nbformat.write(nb, PATH)
print("rewired Ch7-10")
```

- [ ] **Step 3: Apply it**

Run: `$PY $SCRATCH/rewire_ch7_10.py rates_volatility_model/rates_volatility_models.ipynb`
Expected: prints `rewired Ch7-10`.

- [ ] **Step 4: Run the execution test**

Run: `$PY -m pytest rates_volatility_model/tests/test_notebook_executes.py -q`
Expected: `1 passed` (about 10 s). Chapter 11 still uses its own local copies at this point; they are replaced in Task 7.

- [ ] **Step 5: Check the printed no-arbitrage diagnostics once by eye**

Run:

```bash
$PY - <<'EOF'
import nbformat
from nbclient import NotebookClient
nb = nbformat.read("rates_volatility_model/rates_volatility_models.ipynb", as_version=4)
NotebookClient(nb, timeout=600, kernel_name="python3").execute()
for c in nb.cells:
    if c.get("id") in {"122f2370", "41457d7d", "e59676d6", "5bd8fa3b"}:
        print("".join(o.get("text", "") for o in c.outputs if o.output_type == "stream"))
EOF
```

Expected: every "MC ... ± se" line is within about 3 standard errors of its theory/market value (HW1F and G2++ bond prices, HJM mean forward, LMM bonds and caplets), and `max |α(t,T) - σ²(T-t)|` is below `1e-15`. Do not write the executed notebook back here; Task 8 does the final execution.

- [ ] **Step 6: Commit**

```bash
git add rates_volatility_model/tests/test_notebook_executes.py rates_volatility_model/rates_volatility_models.ipynb
git commit -m "fix(rates_volatility_model): correct HJM drift, LMM measure, SABR text and RFR chapter"
```

---

### Task 7: Chapter 11 and the appendices

**Files:**
- Modify: `rates_volatility_model/rates_volatility_models.ipynb` — cells `6539f865`, `d0147609`, `f7a87287`, `72c873ee`, `407804ce`, `52e4703f`, `ea85e730`, `512f9479`, `d0580c3c`

**Interfaces:**
- Consumes: `calibrate_sabr` (imported in cell `9417952b` by Task 6), `ratesvol.options`, `ratesvol.smile`.
- Produces: notebook helpers kept for the later cells: `hagan_sabr_vol` (alias of `sabr_black_vol`), `calibrate_sabr_smile(F, T, strikes, market_vols, beta=0.5) -> ((alpha, rho, nu), rmse_bp, fitted)`, `compute_smile_metrics(F, T, alpha, beta, rho, nu) -> (atm, rr, bf)`. Cells `819d7460`, `d4624019`, `d313aded`, `bf4cde9e`, `69c84beb`, `0a5c8427`, `f8b4b1f1`, `9bd12540` use these names unchanged.

- [ ] **Step 1: Write the Chapter 11 rewire script**

Save as `$SCRATCH/rewire_ch11.py`:

```python
"""Rewire Chapter 11 and the appendices onto the ratesvol package."""

import sys

import nbformat

PATH = sys.argv[1]
nb = nbformat.read(PATH, as_version=4)


def cell(cid):
    found = [c for c in nb.cells if c.get("id") == cid]
    assert len(found) == 1, f"cell {cid} not found exactly once"
    return found[0]


def set_source(cid, src):
    cell(cid).source = src.strip("\n") + "\n"


def replace(cid, old, new):
    c = cell(cid)
    assert c.source.count(old) == 1, f"{cid}: expected one match for {old[:50]!r}"
    c.source = c.source.replace(old, new)


def replace_between(cid, start, end, new):
    """Replace text from ``start`` (inclusive) up to ``end`` (exclusive)."""
    c = cell(cid)
    i, j = c.source.find(start), c.source.find(end)
    assert 0 <= i < j, f"{cid}: markers not found in order"
    c.source = c.source[:i] + new.strip("\n") + "\n\n" + c.source[j:]


# ---------------------------------------------------------------- 11.1
set_source("6539f865", r'''
from ratesvol.options import (bachelier_call, bachelier_implied_vol, black76_call,
                              black76_implied_vol)

print("=== Implied Vol Round-Trip Test ===")
print(f"{'Strike':>8} {'B76 inv σ':>12} {'Error (bp)':>12} {'Bac inv σN':>12} {'Error (bp)':>12}")
print("-" * 60)

F, T = 0.03, 1.0
sigma_true = 0.30            # 30% lognormal vol
sigma_n_true = F * sigma_true  # 同程度の normal vol（90bp）

b76_errors, bac_errors = [], []
for K in [0.010, 0.015, 0.020, 0.025, 0.030, 0.035, 0.040, 0.045, 0.050]:
    iv_b76 = black76_implied_vol(black76_call(F, K, T, sigma_true), F, K, T)
    iv_bac = bachelier_implied_vol(bachelier_call(F, K, T, sigma_n_true), F, K, T)
    err_b76 = (iv_b76 - sigma_true) * 1e4
    err_bac = (iv_bac - sigma_n_true) * 1e4
    b76_errors.append(abs(err_b76))
    bac_errors.append(abs(err_bac))
    print(f"  K={K*100:.1f}%  {iv_b76*100:10.6f}%  {err_b76:+10.2e}  {iv_bac*100:10.6f}%  {err_bac:+10.2e}")

print(f"\nMax B76 error: {max(b76_errors):.2e} bp | Max Bachelier error: {max(bac_errors):.2e} bp")
''')

# ---------------------------------------------------------------- 11.2
replace_between("d0147609", "# ===== SABR 公式（Hagan et al. 2002 近似） =====",
                "# ===== 合成マーケットデータの設定 =====",
                "# Ch11 以降は短い別名で呼ぶ（中身は ratesvol.smile.sabr_black_vol）\n"
                "from ratesvol.smile import sabr_black_vol as hagan_sabr_vol")

# ---------------------------------------------------------------- 11.3
replace_between("f7a87287", "# ===== SABR キャリブレーション（単一スマイル） =====",
                "# ===== デモ: Expiry = 1Y のスマイルにキャリブレーション =====", r'''
# ===== SABR キャリブレーション（単一スマイル） =====
def calibrate_sabr_smile(F, T, strikes, market_vols, beta=0.5):
    """ratesvol.smile.calibrate_sabr を ((alpha, rho, nu), rmse_bp, fitted) の形で返す。"""
    alpha_fit, rho_fit, nu_fit, rmse, fitted = calibrate_sabr(F, T, strikes, market_vols, beta)
    return (alpha_fit, rho_fit, nu_fit), rmse, fitted
''')

# ---------------------------------------------------------------- 11.5 SVI
replace("72c873ee",
        "### 無裁定条件（Butterfly Arbitrage Free）\n\n$$b(1 + |\\rho|) < \\frac{4}{T}$$",
        "### 無裁定条件（Butterfly Arbitrage Free）\n\n"
        "Gatheral-Jacquier (2014): スマイルにバタフライ裁定がない ⇔ すべての $k$ で $w(k) > 0$ かつ\n\n"
        "$$g(k) = \\left(1 - \\frac{k w'}{2w}\\right)^2 - \\frac{w'^2}{4}\\left(\\frac{1}{w}"
        " + \\frac{1}{4}\\right) + \\frac{w''}{2} \\geq 0$$\n\n"
        "傾きの上限 $b(1 + |\\rho|) \\leq 4$（total variance 表記、Rogers-Tehranchi）は **必要条件にすぎない**"
        "（満たしても裁定が残る例がある）。下の実装は $g(k) \\ge 0$ をペナルティで課し、結果も $g$ の最小値で確認する。")
replace_between("407804ce", "# ===== SVI パラメタリゼーション =====",
                "# ===== デモ: 1Y スマイルに SABR と SVI を比較 =====", r'''
# ===== SVI パラメタリゼーション =====
from ratesvol.smile import calibrate_svi, svi_density_g, svi_total_variance
''')
replace("407804ce",
        "# 無裁定チェック\nbutterfly_ok = b_ * (1 + abs(r_)) < 4\n"
        "print(f\"Butterfly arbitrage-free: {'✓ OK' if butterfly_ok else '✗ VIOLATED'}\")",
        "# 無裁定チェック: g(k) >= 0 なら butterfly 裁定なし\n"
        "g_min = svi_density_g(np.linspace(-1.5, 1.5, 301), *svi_params).min()\n"
        "print(f\"min g(k) on k in [-1.5, 1.5]: {g_min:.4f} -> "
        "{'no butterfly arbitrage' if g_min >= 0 else 'butterfly arbitrage'}\")")
replace("407804ce",
        "fine_svi = svi_implied_vol(log_k_fine, T_svi, a_, b_, r_, m_, xi_)",
        "fine_svi = np.sqrt(svi_total_variance(log_k_fine, *svi_params) / T_svi)")

# ---------------------------------------------------------------- 11.6 metrics
replace("52e4703f",
        "Black76 で $\\Delta_{call} = N(d_1) = 0.25$ となる $K$ を数値的に求める。\n\n"
        "$$K_{25\\Delta C} : N\\left(\\frac{\\ln(F/K) + 0.5\\sigma_{ATM}^2 T}{\\sigma_{ATM}\\sqrt{T}}\\right) = 0.25$$",
        "Black76 で $\\Delta_{call} = N(d_1) = 0.25$ となる $K$ を数値的に求める。$d_1$ にはその"
        "ストライク自身のスマイル vol $\\sigma(K)$ を使う（ATM vol で代用するとストライクがずれる）。\n\n"
        "$$K_{25\\Delta C} : N\\left(\\frac{\\ln(F/K) + 0.5\\sigma(K)^2 T}{\\sigma(K)\\sqrt{T}}\\right) = 0.25$$")
replace_between("ea85e730", "# ===== 25Δ ストライクの計算 =====",
                "# ===== 全テナーのメトリクスを集計 =====", r'''
# ===== 25Δ ストライクとスマイルメトリクス =====
from ratesvol.smile import delta_strike, smile_metrics


def compute_smile_metrics(F, T, alpha, beta, rho, nu):
    """SABR スマイルの (ATM vol, 25Δ RR, 25Δ BF)。25Δ が求まらない極端なスマイルでは RR/BF = nan。"""
    return smile_metrics(F, T, lambda K: hagan_sabr_vol(F, K, T, alpha, beta, rho, nu))
''')
replace("ea85e730",
        "    sigma_atm_i = hagan_sabr_vol(F, F, T, p['alpha'], BETA, p['rho'], p['nu'])\n"
        "    K25c = find_delta_strike(F, T, sigma_atm_i, 0.25, 'call')\n"
        "    K25p = find_delta_strike(F, T, sigma_atm_i, -0.25, 'put')",
        "\n    def smile_i(K, F=F, T=T, p=p):\n"
        "        return hagan_sabr_vol(F, K, T, p['alpha'], BETA, p['rho'], p['nu'])\n\n"
        "    K25c = delta_strike(F, T, smile_i, 0.25)\n"
        "    K25p = delta_strike(F, T, smile_i, -0.25)")

# ---------------------------------------------------------------- summary / appendix text
replace("512f9479", "| SVI パラメタライズ | Gatheral 公式、無裁定チェック | SABR 同等 |",
        "| SVI パラメタライズ | raw SVI、g(k) ≥ 0 ペナルティ | 数 bp RMSE |")
replace("512f9479", "| Smile メトリクス | ATM / 25Δ RR / 25Δ BF | 数値デルタ計算 |",
        "| Smile メトリクス | ATM / 25Δ RR / 25Δ BF | スマイル整合デルタ |")
replace("d0580c3c", "| **Δα** | 全期限の α（vol of vol level）に均一シフト |",
        "| **Δα** | 全期限の α（初期ボラ水準）に均一シフト |")
replace("d0580c3c", "| **β** | 全期限共通の SABR β（0=Normal, 1=Lognormal） |",
        "| **β** | 全期限共通の SABR β（0=Normal, 1=Lognormal）。α は固定なので β を動かすと ATM 水準も大きく動く |")

nbformat.write(nb, PATH)
print("rewired Ch11")
```

- [ ] **Step 2: Apply it**

Run: `$PY $SCRATCH/rewire_ch11.py rates_volatility_model/rates_volatility_models.ipynb`
Expected: prints `rewired Ch11`.

- [ ] **Step 3: Run the execution test and the no-local-models check**

Run:

```bash
$PY -m pytest rates_volatility_model/tests -q
grep -c "def hagan_sabr\|def lmm_forward\|def hjm_forward\|def vasicek_path\|def cir_path\|def g2pp_path\|def find_delta_strike\|def svi_implied_vol\|np.trapz" rates_volatility_model/rates_volatility_models.ipynb
```

Expected: `61 passed`; the grep prints `0`.

- [ ] **Step 4: Commit**

```bash
git add rates_volatility_model/rates_volatility_models.ipynb
git commit -m "fix(rates_volatility_model): arbitrage-checked SVI and smile-consistent 25-delta in chapter 11"
```

---

### Task 8: Retire the generator pipeline, rewrite the docs, final execution

**Files:**
- Delete: the 11 files listed under "File structure"
- Create: `rates_volatility_model/docs/STATUS.md`
- Modify: `rates_volatility_model/README.md` (full rewrite)
- Modify: `rates_volatility_model/rates_volatility_models.ipynb` (kernelspec + executed outputs)
- Modify: root `pyproject.toml` (drop the per-file ignore for the deleted test script), root `Makefile` (comment + help), root `README.md` (two rows)

**Interfaces:**
- Consumes: everything above.
- Produces: the finished project.

- [ ] **Step 1: Delete the superseded files**

```bash
git rm rates_volatility_model/generate_notebook_part2.py rates_volatility_model/generate_notebook_part3.py \
  rates_volatility_model/generate_notebook_smile.py rates_volatility_model/merge_notebooks.py \
  rates_volatility_model/rates_volatility_models_part1.ipynb rates_volatility_model/rates_volatility_models_part2.ipynb \
  rates_volatility_model/rates_volatility_models_part3.ipynb rates_volatility_model/rates_volatility_models_smile.ipynb \
  rates_volatility_model/test_suite_validation.py rates_volatility_model/SABR_CORRECTION.md \
  rates_volatility_model/VALIDATION_SUMMARY.md
```

Expected: 11 `rm '...'` lines. (They remain in git history; the review table in STATUS records why they went.)

- [ ] **Step 2: Rewrite `README.md` and add `docs/STATUS.md`**

`rates_volatility_model/README.md`:

````markdown
# Rates Volatility Model

金利ボラティリティモデルを日本語で学ぶ Jupyter ノートブックと、その計算部分をまとめたテスト付きパッケージ `ratesvol`。データはすべて合成。

## 中身

| パス | 役割 |
|---|---|
| `rates_volatility_models.ipynb` | 本体。Ch0 カーブの基礎 → Ch1–2 Black-76 / Bachelier → Ch3–6 Vasicek / CIR / Hull-White 1F / G2++ → Ch7–8 HJM / LMM → Ch9 SABR → Ch10 RFR 複利 → モデル比較 → Ch11 スマイル（SABR サーフェス・SVI・RR/BF）→ 付録 A/B（SABR サーフェス・ボラキューブ） |
| `src/ratesvol/` | モデル実装。ノートブックはここから import する（`options` / `curves` / `short_rate` / `market_models` / `smile` / `rfr`） |
| `tests/` | 単体テスト（解析解・無裁定条件・独立実装との一致）と、ノートブック全体の実行テスト |
| `docs/STATUS.md` | 完成条件と検証状況 |

## 動かし方（リポジトリのルートで）

```bash
uv sync --all-packages --inexact     # 共有 .venv に ratesvol を editable で入れる
uv run --no-sync jupyter lab rates_volatility_model/rates_volatility_models.ipynb
uv run --no-sync pytest rates_volatility_model/tests
```

## 規約

- 金利・ボラは小数（0.03 = 3%）。bp 表示は ×1e4。
- 乱数は `numpy.random.Generator` を引数で渡す。ノートブックは Ch0 で作る `RNG` を全章で共有する。
- ノートブックを編集したら `tests/test_notebook_executes.py` を通す。このテストは ipywidgets が握りつぶす例外（`interact` と `Output`）を表に出す。普通のヘッドレス実行ではインタラクティブセルの失敗が見えない。

## 既知の限界

- データは合成。実市場のカーブ・スマイルではない。
- SABR は Hagan (2002) の lognormal 近似のみ。長い満期・低いストライクで崩れる（負の確率密度）。マイナス金利向けの shifted / normal SABR は無い。
- 短期金利・HJM・LMM のシミュレーションは Euler（Vasicek のみ厳密遷移）。価格は MC 標準誤差の範囲で検証している。
- スワップションの解析価格（Jamshidian など）と Bermudan は扱わない。
````

`rates_volatility_model/docs/STATUS.md`:

```markdown
# rates_volatility_model — status

更新日: 2026-09-27

## ゴール

ノートブックの数式・数値・文章が正しく、現在の環境で最後まで実行でき、その正しさがノートブックの実コードに対するテストで裏付けられている状態にする。

## 完成条件

1. `uv run --no-sync pytest rates_volatility_model/tests` が緑（単体 60 + ノートブック実行 1 = 61）
2. ノートブックのモデル関数はすべて `ratesvol` から import しており、同名関数の再定義が無い
3. 2026-09-27 レビューの指摘 17 件（下表）がすべて解消している
4. README と本ファイルが実態と一致し、旧生成スクリプト・分割ノートブック・旧検証スクリプトが無い

## 2026-09-27 レビュー指摘と対応

| # | 指摘 | 対応 |
|---|---|---|
| 1 | HJM ドリフトが ∫_T^{T_max} を積分していた（「CORRECTED」のコメント付き） | `hjm_drift` を ∫_t^T に。σ 一定で α = σ²(T−t) をテスト |
| 2 | HJM が `np.trapz` を使い NumPy 2.4 で落ちる。ipywidgets が例外を握りつぶし、ヘッドレス実行ではエラー 0 件に見えた | `np.trapezoid`。例外を表に出すノートブック実行テスト |
| 3 | LMM が 2 通り定義され（片方は Ch9 の下）、どちらも測度が不整合、fixing 後もフォワードが動く。旧検証の「E[L]=L」は spot 測度では誤り | spot 測度 LMM を 1 本に。割引債と caplet を Black-76 と照合 |
| 4 | 旧 `test_suite_validation.py` はノートブックでなく自前の再実装を検証。その SABR は補正項が誤り | ノートブックが import する `ratesvol` を pytest で検証 |
| 5 | Bachelier vega を「per 1bp」と表示（実際は per unit、1e4 倍違う）、Black-76 gamma を「per 1%」と表示 | 関数名と表示に単位を明記 |
| 6 | Ch0 の瞬間フォワードが z + dz/dT（×T が抜けていた） | `instantaneous_forward` |
| 7 | Vasicek・G2++ のヒストグラムに重ねた密度が 100 倍ずれていた（% 軸に小数の pdf） | pdf を 1/100 |
| 8 | Vasicek キャリブで r0 を 6M ゼロ金利に固定し短期で 21bp 外れていた。カーブだけでは b と σ が識別できない旨の説明が無かった | r0 も推定、識別性の注記 |
| 9 | G2++ の φ(t) が定数 2% で、カーブにフィットしていなかった | Brigo-Mercurio の φ(t)。MC で初期カーブ再現をテスト |
| 10 | SABR の α を vol-of-vol と説明、弱点を「短い満期」と記載、スライダーで β を動かすと ATM 水準が跳ぶ | 文言修正、ATM vol から α を逆算 |
| 11 | Ch10 に複利計算が無い。SONIA・€STR を政策金利と記載、「RFR は単一カーブ」 | `compounded_in_arrears` のデモ、事実関係を修正 |
| 12 | SVI の無裁定条件が必要条件だけ（文は 4/T、コードは 4）で g(k) 検査が無い | g(k) ≥ 0 をペナルティと検査に |
| 13 | 25Δ ストライクを ATM vol で求めていた | スマイル整合デルタ |
| 14 | SABR 式が 3 か所に重複、セルの章ずれ（LMM が Ch9、SABR 表が Ch10） | `ratesvol.smile` に一本化、迷子セル削除 |
| 15 | 再生成パイプラインが壊れていた（part1 生成器が無い、付録は統合版にしか無い＝再統合で 7 セル消える） | 生成器と分割版を廃止し、統合ノートブックを正本に |
| 16 | `VALIDATION_SUMMARY.md`（46 セル・6 テスト・完了）と `SABR_CORRECTION.md` が実態と不一致、`venv/` は空 | 本ファイルと README に置き換え |
| 17 | CIR の Feller 条件を「非負の条件」と説明（実際は 0 に到達しない条件） | 文言修正 |

## 検証

実行記録は完了時に下へ追記する（コマンドと、その出力の最終行）。
```

- [ ] **Step 3: Update the root files**

Root `pyproject.toml`: delete the line

```toml
"rates_volatility_model/test_suite_validation.py" = ["E402"]
```

Root `Makefile`: change the comment line

```make
# `rates_volatility_model/`, `notebooks/` have no managed env.
```

to

```make
# `notebooks/` has no managed env.
```

change

```make
	@echo "  quantkit deep_hedge_price optimal_execution rough_volatility"
```

to

```make
	@echo "  quantkit deep_hedge_price optimal_execution rough_volatility rates_volatility_model"
```

and change

```make
	@echo "  rates_volatility_model, notebooks, kaggle, shortest_path, cpp_algo_lab (manual envs)"
```

to

```make
	@echo "  notebooks, kaggle, shortest_path, cpp_algo_lab (manual envs)"
```

Root `README.md`: change the project-index row

```markdown
| [`rates_volatility_model/`](rates_volatility_model/) | 金利ボラティリティ・モデリングのリサーチノート | Python / Jupyter |
```

to

```markdown
| [`rates_volatility_model/`](rates_volatility_model/) | 金利ボラティリティモデルの学習ノート（Black-76〜HJM/LMM/SABR/SVI、テスト付きパッケージ `ratesvol`） | Python / Jupyter |
```

and in the "例外:" bullet, change `` `rates_volatility_model` / `notebooks` / `models` / `kaggle` は env 管理なし`` to `` `notebooks` / `models` / `kaggle` は env 管理なし``.

- [ ] **Step 4: Replace the machine-specific kernelspec**

The notebook metadata names a kernel `tf-gpu (3.12.2)` that exists only on one machine. Run:

```bash
$PY - <<'EOF'
import nbformat
p = "rates_volatility_model/rates_volatility_models.ipynb"
nb = nbformat.read(p, as_version=4)
nb.metadata["kernelspec"] = {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"}
nbformat.write(nb, p)
EOF
```

- [ ] **Step 5: Execute the notebook in place so the committed outputs match the code**

Run: `$PY -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 --ExecutePreprocessor.kernel_name=python3 rates_volatility_model/rates_volatility_models.ipynb`
Expected: exits 0 and writes the notebook (a few hundred KB; the previous 1.7 MB came from saved widget renders). Static figures appear for the non-interactive cells; interactive cells render when the notebook is opened in Jupyter.

- [ ] **Step 6: Full verification**

Run:

```bash
$PY -m pytest rates_volatility_model/tests -q
$RUFF check rates_volatility_model/src rates_volatility_model/tests
$RUFF format --check rates_volatility_model/src rates_volatility_model/tests
git status --short rates_volatility_model
ls rates_volatility_model rates_volatility_model/src/ratesvol rates_volatility_model/tests rates_volatility_model/docs
```

Expected: `61 passed`; ruff clean; the listing matches "Definition of done" item 4.

- [ ] **Step 7: Record the evidence in STATUS**

Append to the end of `rates_volatility_model/docs/STATUS.md` (replace the bracketed parts with the real values from step 6):

```markdown
- 2026-09-27: `PYTHONPATH=rates_volatility_model/src python -m pytest rates_volatility_model/tests` → `[final pytest summary line]`（worktree `rates-vol-completion`、NumPy [version]）
- ruff check / format: clean（`src/`, `tests/`）。ノートブックの未改修セルに既存の style 指摘が残る（改修前 405 件 → 約 66 件）
```

- [ ] **Step 8: Commit**

```bash
git add -A rates_volatility_model pyproject.toml Makefile README.md
git commit -m "docs(rates_volatility_model): retire generator pipeline and stale reports, add README and STATUS"
```

- [ ] **Step 9: Finish the branch, then post-merge checks in the main checkout**

Use superpowers:finishing-a-development-branch to review and merge. After the merge, in `/home/kazumasa/projects`:

```bash
uv sync --all-packages --inexact
uv run --no-sync pytest rates_volatility_model/tests -q
```

Expected: `61 passed` using the installed editable `ratesvol` (no `PYTHONPATH`).

The untracked, git-ignored `rates_volatility_model/venv/` in the main checkout is an empty environment (only `pyvenv.cfg` and interpreter symlinks). Deleting it is optional and outside git; ask the user before running `rm -rf rates_volatility_model/venv`.

---

## Out of scope (candidates for a later plan)

- Shifted / normal (Bachelier) SABR for negative rates, and Free-Boundary SABR.
- Analytic swaption pricing under HW1F / G2++ (Jamshidian), Bermudan pricing, calibration to caps/swaptions.
- Real market data (the notebook stays synthetic).
- Lint cleanup of the untouched plotting cells in Chapter 11 and the appendices (about 66 style findings, none functional).

## Self-review (done while writing)

1. **Spec coverage:** every row of the review table names its task(s): rows 1–3 → Tasks 3, 5, 6; row 4 → Tasks 1–4, 8; rows 5–9 → Tasks 1, 2, 5; rows 10–11 → Tasks 4, 6; rows 12–14 → Tasks 4, 6, 7; rows 15–16 → Task 8; row 17 → Task 5.
2. **Placeholders:** none in code; the only bracketed text is Task 8 step 7, which records run output that cannot exist before the run.
3. **Type consistency:** notebook helper names (`hagan_sabr_vol`, `calibrate_sabr_smile`, `compute_smile_metrics`, `RNG`, `T_grid`, `market_zero_curve`) match between the rewire scripts and the untouched cells that use them; the three scripts were applied in sequence to the committed notebook and the result executed cleanly.
4. **Review Focus:** each of the five lines has its test in the owning task (Tasks 1, 1, 2, 3, 4).
