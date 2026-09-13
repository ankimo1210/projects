# johnhull vol 28 Credit Desk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the Hull 11e Ch.24–25 credit-valuation gaps (bond/CDS bootstrap, CDS legs/MTM/fixed coupon/options, synthetic CDO and kth-to-default by Gauss–Hermite quadrature, compound/base correlation, double-t and heterogeneous copulas, CreditMetrics, netting/collateral CVA) as tested `hullkit` modules pinned to Hull's printed numbers, and ship them as artifact-only volume 28 with the vol 26–27 release contract.

**Architecture:** Four new torch-free `hullkit` modules (`credit_curve`, `cds`, `credit_portfolio`, `credit_metrics`) plus four additive functions in `xva`. `frontier_reference.volume28_reference` turns those APIs into a fingerprinted JSON+NPZ reference; `frontier_acceptance._volume28` recomputes 17 identities from the committed arrays; `build_frontier_notebooks.VOLUME_META[28]` renders the notebook; four Plotly figures join the existing `risk_credit` portal page.

**Tech Stack:** Python 3.12, numpy ≥2.0, scipy ≥1.13 (`brentq`, `norm`, `t`, `gammaln`), plotly, nbformat/nbclient, uv workspace, pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`

## Global Constraints

- Work in the worktree `/home/kazumasa/projects/.claude/worktrees/johnhull-vol28-credit-desk` on branch `worktree-johnhull-vol28-credit-desk`; run every command from that repo root with `uv run --no-sync --package hullkit ...` (the worktree has its own `.venv`).
- `hullkit` stays torch-free; only numpy/scipy imports in new modules.
- Existing functions in `credit.py`, `copula.py`, `xva.py` are not modified (only additions to `xva.py`).
- Every public function/class/dataclass carries a docstring (`test_docstrings.py`) and every new `module:symbol` appears in `MODEL_INDEX.md` (`test_model_index.py`).
- Hull discretisation: payments in arrears on an even grid (`freq` per year), defaults at interval midpoints, accrual = half a period; continuous-compounding flat `r`.
- Reference seed for vol 28 is `20260746` (`20260718 + 28`); `data_policy` stays `synthetic-offline`; Hull Table 24.4 / Table 25.6 constants are transcribed textbook fixtures.
- Commit after each task with the trailer lines
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_01TVMuyHMT9xAFe1kt53a6JH`.
- Prototype that already reproduces every Hull pin (throwaway, for reference):
  `/tmp/claude-1000/-home-kazumasa-projects/0d4c0a00-f8c4-4793-bd4a-aabab1846954/scratchpad/proto_credit.py`.

## File Structure

| Path | Responsibility |
|---|---|
| `johnhull/hullkit/src/hullkit/credit_curve.py` | `HazardCurve` (piecewise-constant λ), Example 24.1 average→forward, Example 24.2 bond-price bootstrap |
| `johnhull/hullkit/src/hullkit/cds.py` | Single-name CDS legs, par/MTM/binary, implied hazard, CDS-quote bootstrap, fixed coupon/upfront, forward spread, Black-type CDS option |
| `johnhull/hullkit/src/hullkit/credit_portfolio.py` | One-factor copula quadrature: tranche/kth-to-default valuation, compound & base correlation, expected-loss curve, double-t, ASB recursion |
| `johnhull/hullkit/src/hullkit/credit_metrics.py` | Table 24.4 transition matrix, thresholds, correlated migration MC, credit loss / VaR |
| `johnhull/hullkit/src/hullkit/xva.py` | + `default_probs_from_spreads`, `netting_set_exposure`, `collateralized_exposure`, `cva_single_payoff` |
| `johnhull/hullkit/src/hullkit/frontier_reference.py` | + `volume28_reference`, range 21–28 |
| `johnhull/hullkit/src/hullkit/__init__.py` | register the four modules |
| `johnhull/hullkit/tests/test_credit_curve.py`, `test_cds.py`, `test_credit_portfolio.py`, `test_credit_metrics.py`, `test_xva.py`, `test_frontier_reference.py` | Hull pins and identities |
| `johnhull/scripts/frontier_acceptance.py` | + `_volume28`, registry, range text |
| `johnhull/scripts/build_frontier_artifacts.py` | + `FILES[28]`, `UNITS_BY_VOLUME[28]` |
| `johnhull/scripts/build_frontier_notebooks.py` | + `VOLUME_META[28]` |
| `johnhull/scripts/verify_release.py` | range 18–28 |
| `johnhull/volumes/28_credit_desk/` | builder wrapper, notebook, `reference/`, `VALIDATION.md` |
| `johnhull/report/report_builder/frontier_figures.py`, `figures.py`, `report/tests/test_report_build.py` | 4 portal figures on `risk_credit` (8 → 12, total 78 → 82) |
| `johnhull/release_manifest.json`, `book/_toc.yml`, `book/notebooks/28_credit_desk.ipynb` (symlink), `book/notebooks/00_overview.md`, `MODEL_INDEX.md`, `ROADMAP.md`, `README.md`, `VALIDATION.md`, `docs/DATA_PROVENANCE.md`, `CLAUDE.md` | wiring and docs |

Hull pin values used throughout (from the 11e GE PDF, pp. 565–607):

| Pin | Value |
|---|---|
| Ex 24.1 average hazards for 150/180/195 bp, R=40% | 2.5%, 3.0%, 3.25%; forward 3.5%, 3.75% |
| Ex 24.2 bond prices (8% semiannual, yields 6.5/6.8/6.95% cc) | 101.33, 101.99, 102.47; risk-free 102.83, 105.52, 108.08; loss PV 1.50, 3.53, 5.61; λ = 2.46%, 3.48%, 3.74% |
| Table 25.2–25.4 (λ=2%, R=40%, r=5%, annual) | annuity 4.0728, accrual 0.0422, protection 0.0506, spread 123 bp; MTM to seller at 150 bp = 0.0111; 100 bp ⇒ λ=1.63%; binary payoff 0.0844 ⇒ 205 bp |
| Ex 25.1 (34/40 bp act/360, r=4%, quarterly) | act/act 0.345%/0.406%; λ=0.5717%; D=4.447; P=100.27 |
| Ex 25.2 (mezz 3–6%, ρ=0.15, R=40%, r=3.5%, quarterly, index 50 bp) | λ=0.83%; E₂₀(F)=0.9936/0.9600/0.8364/0.5648 at F=0.2020/−0.2020/−0.6060/−1.0104; A=4.2846, B=0.0187, C=0.1496; 348 bp |
| Ex 25.3 (10 names, λ=2%, 3rd-to-default, ρ=0.3, R=40%, r=5%, annual) | conditional at F=−1.0104: PD 0.0361…0.1830, P(≥3) 0.0047/0.0335/0.0928/0.1757/0.2717, PVs 0.1379/3.8443/0.1149; unconditional 0.0629/4.0580/0.0524; 153 bp |
| Table 25.6 → 25.8 (iTraxx 2007-01-31, r=3%, R=40%) | λ=0.382%; compound 17.7/7.8/14.0/18.2/23.3%; base 17.7/28.4/36.5/43.2/60.5% |
| Table 24.4 thresholds | AAA: 1.2719, 2.4089, 2.8070; BBB: −3.7190, −3.0618, −1.7866; BBB default > 2.9290 |
| §24.7 | netting 10/30/−25 → 15 vs 40; Ex 24.4 exposures 5/0/0/5 |

---

### Task 1: `credit_curve.py` — hazard curve, Example 24.1 and 24.2

**Files:**
- Create: `johnhull/hullkit/src/hullkit/credit_curve.py`
- Modify: `johnhull/hullkit/src/hullkit/__init__.py` (add `credit_curve`, `cds`, `credit_portfolio`, `credit_metrics` to the import list and `__all__`, alphabetically — do all four now; the modules are created in Tasks 1–4, so create empty-docstring stubs for `cds.py`, `credit_portfolio.py`, `credit_metrics.py` in this task: a single module docstring line each)
- Test: `johnhull/hullkit/tests/test_credit_curve.py`

**Interfaces:**
- Produces: `HazardCurve(knots: tuple[float, ...], hazards: tuple[float, ...])` with `.from_constant(hazard, horizon=100.0)`, `.forward_hazard(t)`, `.cumulative_hazard(t)`, `.survival(t)`, `.default_prob(t)`, `.default_prob_between(t0, t1)`; `average_hazards_from_spreads(spreads, recovery) -> np.ndarray`; `forward_hazards_from_average(tenors, average_hazards) -> HazardCurve`; `bond_price_from_yield(face, coupon_rate, maturity, yield_cc, freq=2) -> float`; `risk_free_bond_price(face, coupon_rate, maturity, r, freq=2) -> float`; `forward_risk_free_value(face, coupon_rate, maturity, r, tau, freq=2) -> float`; `expected_default_loss_pv(curve, face, coupon_rate, maturity, r, recovery, freq=2, default_step=0.5) -> float`; `BondBootstrapResult(curve, expected_loss_pv, risk_free_prices)`; `bootstrap_from_bonds(bond_prices, coupon_rate, maturities, r, recovery, face=100.0, freq=2, default_step=0.5) -> BondBootstrapResult`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hullkit.credit_curve: piecewise hazard curves and Hull 24.4 bootstraps."""

import math

import numpy as np
import pytest
from hullkit import credit_curve as cc


def test_constant_curve_matches_exponential_survival():
    curve = cc.HazardCurve.from_constant(0.02)
    assert curve.survival(2.0) == pytest.approx(math.exp(-0.04), abs=1e-12)
    assert curve.default_prob_between(2.0, 3.0) == pytest.approx(
        math.exp(-0.04) - math.exp(-0.06), abs=1e-12
    )


def test_piecewise_curve_integrates_segment_by_segment_and_extrapolates_flat():
    curve = cc.HazardCurve((1.0, 2.0), (0.01, 0.03))
    assert curve.cumulative_hazard(0.5) == pytest.approx(0.005)
    assert curve.cumulative_hazard(1.5) == pytest.approx(0.01 + 0.015)
    assert curve.cumulative_hazard(4.0) == pytest.approx(0.01 + 0.03 * 3.0)  # flat beyond 2y
    np.testing.assert_allclose(curve.forward_hazard(np.array([0.5, 1.5, 9.0])), [0.01, 0.03, 0.03])


def test_curve_validation():
    with pytest.raises(ValueError):
        cc.HazardCurve((2.0, 1.0), (0.01, 0.02))
    with pytest.raises(ValueError):
        cc.HazardCurve((1.0,), (-0.01,))
    with pytest.raises(ValueError):
        cc.HazardCurve((1.0, 2.0), (0.01,))


def test_example_24_1_average_and_forward_hazards():
    avg = cc.average_hazards_from_spreads([0.0150, 0.0180, 0.0195], recovery=0.4)
    np.testing.assert_allclose(avg, [0.025, 0.030, 0.0325], atol=1e-12)
    curve = cc.forward_hazards_from_average([1.0, 2.0, 3.0], avg)
    np.testing.assert_allclose(curve.hazards, [0.025, 0.035, 0.0375], atol=1e-12)
    # average over 3y is recovered from the forward curve
    assert curve.cumulative_hazard(3.0) / 3.0 == pytest.approx(0.0325, abs=1e-12)


def test_example_24_2_bond_prices():
    prices = [cc.bond_price_from_yield(100, 0.08, T, y) for T, y in ((1, 0.065), (2, 0.068), (3, 0.0695))]
    np.testing.assert_allclose(prices, [101.33, 101.99, 102.47], atol=0.005)
    risk_free = [cc.risk_free_bond_price(100, 0.08, T, 0.05) for T in (1, 2, 3)]
    np.testing.assert_allclose(risk_free, [102.83, 105.52, 108.08], atol=0.005)


def test_example_24_2_loss_given_default_points():
    # PV of loss if default at 3 months / 9 months on the 1-year bond (Hull: 63.33, 60.40)
    loss_3m = (cc.forward_risk_free_value(100, 0.08, 1.0, 0.05, 0.25) - 40.0) * math.exp(-0.05 * 0.25)
    loss_9m = (cc.forward_risk_free_value(100, 0.08, 1.0, 0.05, 0.75) - 40.0) * math.exp(-0.05 * 0.75)
    assert loss_3m == pytest.approx(63.33, abs=0.005)
    assert loss_9m == pytest.approx(60.40, abs=0.005)


def test_example_24_2_bootstrap_hazards():
    prices = [cc.bond_price_from_yield(100, 0.08, T, y) for T, y in ((1, 0.065), (2, 0.068), (3, 0.0695))]
    result = cc.bootstrap_from_bonds(prices, 0.08, [1.0, 2.0, 3.0], r=0.05, recovery=0.4)
    np.testing.assert_allclose(result.curve.hazards, [0.0246, 0.0348, 0.0374], atol=5e-5)
    np.testing.assert_allclose(result.expected_loss_pv, [1.50, 3.53, 5.61], atol=0.005)
    # round trip: the bootstrapped curve reprices the expected-loss targets
    for T, target in zip((1.0, 2.0, 3.0), result.expected_loss_pv, strict=True):
        repriced = cc.expected_default_loss_pv(result.curve, 100, 0.08, T, 0.05, 0.4)
        assert repriced == pytest.approx(target, abs=1e-9)


def test_bootstrap_rejects_bad_inputs():
    with pytest.raises(ValueError):
        cc.bootstrap_from_bonds([101.0, 102.0], 0.08, [1.0], r=0.05, recovery=0.4)
    with pytest.raises(ValueError):
        cc.bootstrap_from_bonds([101.0], 0.08, [1.0], r=0.05, recovery=1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_curve.py`
Expected: FAIL with `ImportError: cannot import name 'credit_curve'`

- [ ] **Step 3: Write the implementation**

```python
"""Hazard-rate curves and their calibration (Hull 11e, §24.4).

A :class:`HazardCurve` is a piecewise-constant default intensity.  The module
reproduces Example 24.1 (average → forward hazards from yield spreads) and
Example 24.2 (bootstrapping hazards from corporate bond prices with defaults at
the midpoints of six-month intervals).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


@dataclass(frozen=True)
class HazardCurve:
    """Piecewise-constant hazard rate: ``hazards[i]`` applies on ``(knots[i-1], knots[i]]``.

    ``knots`` are strictly increasing and positive; the last hazard extrapolates flat.
    """

    knots: tuple[float, ...]
    hazards: tuple[float, ...]

    def __post_init__(self) -> None:
        knots = tuple(float(k) for k in self.knots)
        hazards = tuple(float(h) for h in self.hazards)
        if not knots or len(knots) != len(hazards):
            raise ValueError("HazardCurve: knots and hazards must be non-empty and equal length")
        if knots[0] <= 0.0 or any(b <= a for a, b in zip(knots, knots[1:], strict=False)):
            raise ValueError("HazardCurve: knots must be positive and strictly increasing")
        if any(h < 0.0 or not math.isfinite(h) for h in hazards):
            raise ValueError("HazardCurve: hazards must be finite and >= 0")
        object.__setattr__(self, "knots", knots)
        object.__setattr__(self, "hazards", hazards)

    @classmethod
    def from_constant(cls, hazard: float, horizon: float = 100.0) -> HazardCurve:
        """Constant-hazard curve (flat extrapolation makes ``horizon`` immaterial)."""
        return cls((float(horizon),), (float(hazard),))

    def forward_hazard(self, t):
        """Instantaneous hazard at time ``t`` (array-friendly)."""
        t = np.asarray(t, dtype=float)
        idx = np.minimum(np.searchsorted(self.knots, t, side="left"), len(self.knots) - 1)
        return np.asarray(self.hazards)[idx]

    def cumulative_hazard(self, t):
        """∫₀ᵗ λ(u) du for scalar or array ``t`` (t >= 0)."""
        t = np.asarray(t, dtype=float)
        if np.any(t < 0.0):
            raise ValueError("cumulative_hazard: t must be >= 0")
        lower = np.concatenate([[0.0], self.knots[:-1]])
        upper = np.asarray(self.knots)
        hazards = np.asarray(self.hazards)
        total = np.zeros_like(t)
        for lo, hi, lam in zip(lower, upper, hazards, strict=True):
            total = total + lam * np.clip(np.minimum(t, hi) - lo, 0.0, None)
        total = total + hazards[-1] * np.clip(t - upper[-1], 0.0, None)
        return total

    def survival(self, t):
        """S(t) = exp(-∫₀ᵗ λ)."""
        return np.exp(-self.cumulative_hazard(t))

    def default_prob(self, t):
        """Q(t) = 1 - S(t)."""
        return 1.0 - self.survival(t)

    def default_prob_between(self, t0, t1):
        """Unconditional probability of default in (t0, t1]: S(t0) - S(t1)."""
        return self.survival(t0) - self.survival(t1)


def average_hazards_from_spreads(spreads, recovery: float):
    """Average hazard to each tenor from yield spreads: λ̄(T) = s(T)/(1-R) (Hull eq. 24.2)."""
    _check_recovery(recovery)
    return np.asarray(spreads, dtype=float) / (1.0 - recovery)


def forward_hazards_from_average(tenors, average_hazards) -> HazardCurve:
    """Convert average hazards λ̄(Tᵢ) into piecewise-constant forward hazards (Example 24.1)."""
    tenors = np.asarray(tenors, dtype=float)
    average = np.asarray(average_hazards, dtype=float)
    if tenors.shape != average.shape or tenors.ndim != 1:
        raise ValueError("tenors and average_hazards must be 1-D and equal length")
    cumulative = tenors * average
    previous_cum = np.concatenate([[0.0], cumulative[:-1]])
    previous_t = np.concatenate([[0.0], tenors[:-1]])
    forward = (cumulative - previous_cum) / (tenors - previous_t)
    return HazardCurve(tuple(tenors), tuple(forward))


def bond_price_from_yield(face: float, coupon_rate: float, maturity: float, yield_cc: float, freq: int = 2) -> float:
    """Price of a coupon bond from a continuously compounded yield (coupon just paid)."""
    n = _periods(maturity, freq)
    coupon = face * coupon_rate / freq
    times = np.arange(1, n + 1) / freq
    return float(np.sum(coupon * np.exp(-yield_cc * times)) + face * math.exp(-yield_cc * maturity))


def risk_free_bond_price(face: float, coupon_rate: float, maturity: float, r: float, freq: int = 2) -> float:
    """Value of the bond's promised cash flows discounted at the risk-free rate ``r``."""
    return bond_price_from_yield(face, coupon_rate, maturity, r, freq)


def forward_risk_free_value(face: float, coupon_rate: float, maturity: float, r: float, tau: float, freq: int = 2) -> float:
    """Risk-free value at time ``tau`` of the cash flows still outstanding after ``tau``."""
    n = _periods(maturity, freq)
    coupon = face * coupon_rate / freq
    times = np.arange(1, n + 1) / freq
    remaining = times[times > tau + 1e-12]
    return float(np.sum(coupon * np.exp(-r * (remaining - tau))) + face * math.exp(-r * (maturity - tau)))


def expected_default_loss_pv(
    curve: HazardCurve,
    face: float,
    coupon_rate: float,
    maturity: float,
    r: float,
    recovery: float,
    freq: int = 2,
    default_step: float = 0.5,
) -> float:
    """PV of expected default losses on a bond, defaults at midpoints of ``default_step`` intervals.

    Loss on default at τ is (risk-free forward value at τ − R·face) discounted to today
    (Hull Example 24.2: 63.33 and 60.40 for the 1-year bond).
    """
    _check_recovery(recovery)
    n = round(maturity / default_step)
    if n <= 0 or abs(n * default_step - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of default_step intervals")
    total = 0.0
    for i in range(1, n + 1):
        t0, t1 = (i - 1) * default_step, i * default_step
        tau = 0.5 * (t0 + t1)
        loss = (forward_risk_free_value(face, coupon_rate, maturity, r, tau, freq) - recovery * face) * math.exp(-r * tau)
        total += float(curve.default_prob_between(t0, t1)) * loss
    return total


@dataclass(frozen=True)
class BondBootstrapResult:
    """Bootstrapped hazard curve with the per-bond expected-loss PV targets it matched."""

    curve: HazardCurve
    expected_loss_pv: tuple[float, ...]
    risk_free_prices: tuple[float, ...]


def bootstrap_from_bonds(
    bond_prices,
    coupon_rate: float,
    maturities,
    r: float,
    recovery: float,
    face: float = 100.0,
    freq: int = 2,
    default_step: float = 0.5,
) -> BondBootstrapResult:
    """Solve piecewise-constant hazards so each bond's expected default loss matches its price gap.

    Bonds are processed in maturity order; the hazard on (Tᵢ₋₁, Tᵢ] is found by
    ``brentq`` so that ``expected_default_loss_pv`` equals risk-free price − market price
    (Hull Example 24.2: 2.46%, 3.48%, 3.74%).
    """
    _check_recovery(recovery)
    prices = np.asarray(bond_prices, dtype=float)
    tenors = np.asarray(maturities, dtype=float)
    if prices.shape != tenors.shape or prices.ndim != 1 or prices.size == 0:
        raise ValueError("bond_prices and maturities must be 1-D and equal length")
    if np.any(np.diff(tenors) <= 0.0) or tenors[0] <= 0.0:
        raise ValueError("maturities must be positive and strictly increasing")
    risk_free = [risk_free_bond_price(face, coupon_rate, float(T), r, freq) for T in tenors]
    targets = [rf - p for rf, p in zip(risk_free, prices, strict=True)]
    hazards: list[float] = []
    for i, T in enumerate(tenors):
        def gap(h: float, i: int = i, T: float = float(T)) -> float:
            trial = HazardCurve(tuple(tenors[: i + 1]), tuple(hazards + [h]))
            return expected_default_loss_pv(trial, face, coupon_rate, T, r, recovery, freq, default_step) - targets[i]

        try:
            hazards.append(float(brentq(gap, 1e-10, 5.0, xtol=1e-14)))
        except ValueError as exc:
            raise ValueError(f"bootstrap_from_bonds: no hazard in (0, 5] reprices bond {i}") from exc
    curve = HazardCurve(tuple(tenors), tuple(hazards))
    return BondBootstrapResult(curve, tuple(targets), tuple(risk_free))


def _check_recovery(recovery: float) -> None:
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")


def _periods(maturity: float, freq: int) -> int:
    n = round(maturity * freq)
    if n <= 0 or abs(n / freq - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of coupon periods")
    return n
```

Stub files (one line each, replaced in later tasks):

```python
"""Single-name CDS valuation (Hull 11e, §25.2–25.5)."""
```
```python
"""One-factor copula valuation of CDO tranches and basket CDS (Hull 11e, §25.6–25.11)."""
```
```python
"""CreditMetrics: rating transitions and credit VaR (Hull 11e, §24.9)."""
```

`__init__.py`: insert `cds,`, `credit_curve,`, `credit_metrics,`, `credit_portfolio,` after `carbon,` in the import tuple and the same names after `"carbon",` in `__all__` (keep alphabetical: carbon, cds, credit, credit_curve, credit_metrics, credit_portfolio, exotics …).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_curve.py`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/credit_curve.py johnhull/hullkit/src/hullkit/cds.py johnhull/hullkit/src/hullkit/credit_portfolio.py johnhull/hullkit/src/hullkit/credit_metrics.py johnhull/hullkit/src/hullkit/__init__.py johnhull/hullkit/tests/test_credit_curve.py
git commit -m "feat(hullkit): add piecewise hazard curves and Hull 24.4 bootstraps"
```

### Task 2: `cds.py` — single-name CDS (Tables 25.1–25.5, Example 25.1, §25.5)

**Files:**
- Create: `johnhull/hullkit/src/hullkit/cds.py` (replace stub)
- Test: `johnhull/hullkit/tests/test_cds.py`

**Interfaces:**
- Consumes: `credit_curve.HazardCurve` (Task 1)
- Produces: `CDSLegs(annuity, accrual, protection)` with `.risky_duration`, `.par_spread`; `cds_legs(curve, recovery, r, maturity, freq=1, binary=False, start=0.0) -> CDSLegs`; `cds_par_spread(curve, recovery, r, maturity, freq=1) -> float`; `cds_risky_duration(...) -> float`; `cds_mtm(contract_spread, curve, recovery, r, maturity, freq=1, side="seller") -> float`; `binary_cds_spread(curve, r, maturity, freq=1) -> float`; `implied_hazard(spread, recovery, r, maturity, freq=1) -> float`; `bootstrap_from_cds(tenors, spreads, recovery, r, freq=4) -> HazardCurve`; `actual360_to_actual_actual(rate) -> float`; `fixed_coupon_price(spread, coupon, duration) -> float`; `upfront_payment(spread, coupon, duration, notional=100.0) -> float`; `cds_forward_spread(curve, recovery, r, start, maturity, freq=1) -> float`; `cds_option(forward_spread, strike, sigma, expiry, risky_annuity, kind="payer") -> float`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hullkit.cds: Hull Tables 25.1–25.5, Example 25.1, CDS forwards/options."""

import math

import numpy as np
import pytest
from hullkit import cds
from hullkit.credit_curve import HazardCurve

HULL = dict(curve=0.02, recovery=0.4, r=0.05, maturity=5.0, freq=1)


def test_tables_25_2_to_25_4_legs_and_par_spread():
    legs = cds.cds_legs(**HULL)
    assert legs.annuity == pytest.approx(4.0728, abs=5e-5)
    assert legs.accrual == pytest.approx(0.0422, abs=5e-5)
    assert legs.protection == pytest.approx(0.0506, abs=5e-5)
    assert legs.risky_duration == pytest.approx(4.1150, abs=5e-5)
    assert cds.cds_par_spread(**HULL) * 1e4 == pytest.approx(123.0, abs=0.5)


def test_hazard_curve_and_float_inputs_agree():
    curve = HazardCurve.from_constant(0.02)
    assert cds.cds_par_spread(curve, 0.4, 0.05, 5.0) == pytest.approx(cds.cds_par_spread(0.02, 0.4, 0.05, 5.0), abs=1e-15)


def test_mark_to_market_at_150bp():
    assert cds.cds_mtm(0.0150, **HULL) == pytest.approx(0.0111, abs=5e-5)
    assert cds.cds_mtm(0.0150, side="buyer", **HULL) == pytest.approx(-0.0111, abs=5e-5)
    with pytest.raises(ValueError):
        cds.cds_mtm(0.0150, side="dealer", **HULL)


def test_implied_hazard_for_100bp_and_round_trip():
    lam = cds.implied_hazard(0.0100, 0.4, 0.05, 5.0)
    assert lam == pytest.approx(0.0163, abs=5e-5)
    assert cds.cds_par_spread(lam, 0.4, 0.05, 5.0) == pytest.approx(0.0100, abs=1e-12)


def test_binary_cds_table_25_5():
    legs = cds.cds_legs(0.02, 0.4, 0.05, 5.0, binary=True)
    assert legs.protection == pytest.approx(0.0844, abs=5e-5)
    assert cds.binary_cds_spread(0.02, 0.05, 5.0) * 1e4 == pytest.approx(205.0, abs=0.5)


def test_example_25_1_fixed_coupon_price():
    spread = cds.actual360_to_actual_actual(0.0034)
    coupon = cds.actual360_to_actual_actual(0.0040)
    assert spread == pytest.approx(0.00345, abs=5e-6)
    assert coupon == pytest.approx(0.00406, abs=5e-6)
    lam = cds.implied_hazard(spread, 0.4, 0.04, 5.0, freq=4)
    assert lam == pytest.approx(0.005717, abs=5e-6)
    duration = cds.cds_risky_duration(lam, 0.4, 0.04, 5.0, freq=4)
    assert duration == pytest.approx(4.447, abs=5e-4)
    assert cds.fixed_coupon_price(spread, coupon, duration) == pytest.approx(100.27, abs=5e-3)
    # seller pays 0.27% of notional up front (Hull: 1,000,000 * 125 * 0.0027 for the index)
    assert cds.upfront_payment(spread, coupon, duration, notional=1.0) == pytest.approx(-0.0027, abs=5e-5)


def test_bootstrap_from_cds_round_trip():
    tenors, quotes = [1.0, 3.0, 5.0], [0.0060, 0.0100, 0.0140]
    curve = cds.bootstrap_from_cds(tenors, quotes, recovery=0.4, r=0.05, freq=4)
    for T, q in zip(tenors, quotes, strict=True):
        assert cds.cds_par_spread(curve, 0.4, 0.05, T, freq=4) == pytest.approx(q, abs=1e-10)
    assert curve.hazards[0] < curve.hazards[1] < curve.hazards[2]  # upward-sloping quotes


def test_forward_spread_is_between_spot_spreads_for_upward_curve():
    curve = HazardCurve((1.0, 5.0), (0.01, 0.03))
    spot_1y = cds.cds_par_spread(curve, 0.4, 0.05, 1.0, freq=4)
    spot_5y = cds.cds_par_spread(curve, 0.4, 0.05, 5.0, freq=4)
    fwd = cds.cds_forward_spread(curve, 0.4, 0.05, start=1.0, maturity=5.0, freq=4)
    assert spot_1y < spot_5y < fwd  # forward exceeds both because the 1–5y hazard is 3%


def test_cds_option_parity_and_zero_vol_limit():
    F, K, A = 0.0280, 0.0250, 4.0
    payer = cds.cds_option(F, K, 0.5, 1.0, A, kind="payer")
    receiver = cds.cds_option(F, K, 0.5, 1.0, A, kind="receiver")
    assert payer - receiver == pytest.approx(A * (F - K), abs=1e-12)
    assert cds.cds_option(F, K, 1e-9, 1.0, A, kind="payer") == pytest.approx(A * max(F - K, 0.0), abs=1e-9)
    assert cds.cds_option(F, K, 1e-9, 1.0, A, kind="receiver") == pytest.approx(0.0, abs=1e-9)
    with pytest.raises(ValueError):
        cds.cds_option(F, K, 0.5, 1.0, A, kind="straddle")


def test_validation_errors():
    with pytest.raises(ValueError):
        cds.cds_legs(0.02, 1.0, 0.05, 5.0)
    with pytest.raises(ValueError):
        cds.cds_legs(0.02, 0.4, 0.05, 0.3, freq=1)
    with pytest.raises(ValueError):
        cds.cds_forward_spread(0.02, 0.4, 0.05, start=5.0, maturity=5.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_cds.py`
Expected: FAIL with `AttributeError: module 'hullkit.cds' has no attribute 'cds_legs'`

- [ ] **Step 3: Write the implementation**

```python
"""Single-name CDS valuation (Hull 11e, §25.2–25.5).

Discrete legs with payments in arrears and defaults at interval midpoints,
exactly as in Tables 25.1–25.5: annuity, accrual-on-default, protection.
Also the fixed-coupon/upfront convention (Example 25.1), a CDS-quote
bootstrap, forward CDS spreads, and Black-type CDS options.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

from .credit_curve import HazardCurve


@dataclass(frozen=True)
class CDSLegs:
    """Present values per unit notional and per unit spread (Hull Tables 25.2–25.4)."""

    annuity: float
    accrual: float
    protection: float

    @property
    def risky_duration(self) -> float:
        """Annuity + accrual: the multiplier of the spread (4.1150 in Hull's example)."""
        return self.annuity + self.accrual

    @property
    def par_spread(self) -> float:
        """Breakeven spread: protection / (annuity + accrual)."""
        return self.protection / self.risky_duration


def _as_curve(curve) -> HazardCurve:
    return curve if isinstance(curve, HazardCurve) else HazardCurve.from_constant(float(curve))


def _grid(start: float, maturity: float, freq: int) -> np.ndarray:
    if freq < 1 or int(freq) != freq:
        raise ValueError("freq must be a positive integer")
    if maturity <= start:
        raise ValueError("maturity must exceed start")
    n = round((maturity - start) * freq)
    if n <= 0 or abs(start + n / freq - maturity) > 1e-9:
        raise ValueError("maturity - start must be a whole number of payment periods")
    return start + np.arange(1, n + 1) / freq


def cds_legs(curve, recovery: float, r: float, maturity: float, freq: int = 1, binary: bool = False, start: float = 0.0) -> CDSLegs:
    """Annuity, accrual and protection PVs for a CDS paying ``freq`` times a year.

    ``curve`` is a :class:`HazardCurve` or a constant hazard. Defaults occur at the
    midpoint of each period; the accrual is half a period's spread. ``binary=True``
    pays 1 (not 1-R) on default (Table 25.5). ``start > 0`` values a forward-start
    CDS that knocks out on default before ``start`` (unconditional survival weights).
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    hazard = _as_curve(curve)
    times = _grid(start, maturity, freq)
    dt = 1.0 / freq
    previous = times - dt
    mid = times - 0.5 * dt
    survival = hazard.survival(times)
    default_in_period = hazard.survival(previous) - survival
    payoff = 1.0 if binary else 1.0 - recovery
    annuity = float(np.sum(survival * dt * np.exp(-r * times)))
    accrual = float(np.sum(0.5 * dt * default_in_period * np.exp(-r * mid)))
    protection = float(np.sum(payoff * default_in_period * np.exp(-r * mid)))
    return CDSLegs(annuity, accrual, protection)


def cds_par_spread(curve, recovery: float, r: float, maturity: float, freq: int = 1) -> float:
    """Breakeven CDS spread (Hull §25.2: 123 bp for λ=2%, R=40%, r=5%, 5y annual)."""
    return cds_legs(curve, recovery, r, maturity, freq).par_spread


def cds_risky_duration(curve, recovery: float, r: float, maturity: float, freq: int = 1) -> float:
    """Spread multiplier D = annuity + accrual (Hull §25.4 "duration")."""
    return cds_legs(curve, recovery, r, maturity, freq).risky_duration


def cds_mtm(contract_spread: float, curve, recovery: float, r: float, maturity: float, freq: int = 1, side: str = "seller") -> float:
    """Mark-to-market per unit notional: D·s_contract − protection to the seller (Hull: 0.0111 at 150 bp)."""
    legs = cds_legs(curve, recovery, r, maturity, freq)
    value = legs.risky_duration * contract_spread - legs.protection
    if side == "seller":
        return value
    if side == "buyer":
        return -value
    raise ValueError("side must be 'seller' or 'buyer'")


def binary_cds_spread(curve, r: float, maturity: float, freq: int = 1) -> float:
    """Par spread of a binary CDS paying 1 on default (Hull Table 25.5: 205 bp)."""
    return cds_legs(curve, 0.0, r, maturity, freq, binary=True).par_spread


def implied_hazard(spread: float, recovery: float, r: float, maturity: float, freq: int = 1) -> float:
    """Constant hazard that reproduces a par spread (Hull: 100 bp ⇒ 1.63%; Ex 25.1 ⇒ 0.5717%)."""
    if spread <= 0.0:
        raise ValueError("spread must be > 0")

    def gap(h: float) -> float:
        return cds_par_spread(h, recovery, r, maturity, freq) - spread

    try:
        return float(brentq(gap, 1e-10, 5.0, xtol=1e-14))
    except ValueError as exc:
        raise ValueError("implied_hazard: no constant hazard in (0, 5] matches the spread") from exc


def bootstrap_from_cds(tenors, spreads, recovery: float, r: float, freq: int = 4) -> HazardCurve:
    """Piecewise-constant hazards that reprice a term structure of par CDS spreads."""
    tenors = np.asarray(tenors, dtype=float)
    quotes = np.asarray(spreads, dtype=float)
    if tenors.shape != quotes.shape or tenors.ndim != 1 or tenors.size == 0:
        raise ValueError("tenors and spreads must be 1-D and equal length")
    if tenors[0] <= 0.0 or np.any(np.diff(tenors) <= 0.0):
        raise ValueError("tenors must be positive and strictly increasing")
    hazards: list[float] = []
    for i, (tenor, quote) in enumerate(zip(tenors, quotes, strict=True)):
        def gap(h: float, i: int = i, tenor: float = float(tenor), quote: float = float(quote)) -> float:
            trial = HazardCurve(tuple(tenors[: i + 1]), tuple(hazards + [h]))
            return cds_par_spread(trial, recovery, r, tenor, freq) - quote

        try:
            hazards.append(float(brentq(gap, 1e-10, 5.0, xtol=1e-14)))
        except ValueError as exc:
            raise ValueError(f"bootstrap_from_cds: no hazard in (0, 5] reprices tenor {tenor}") from exc
    return HazardCurve(tuple(tenors), tuple(hazards))


def actual360_to_actual_actual(rate: float) -> float:
    """Convert an actual/360 quote to actual/actual (×365/360), as in Hull Example 25.1."""
    return rate * 365.0 / 360.0


def fixed_coupon_price(spread: float, coupon: float, duration: float) -> float:
    """Price per 100 of a fixed-coupon CDS: P = 100 − 100·D·(s − c) (Hull §25.4)."""
    return 100.0 - 100.0 * duration * (spread - coupon)


def upfront_payment(spread: float, coupon: float, duration: float, notional: float = 100.0) -> float:
    """Amount the protection buyer pays up front, (100 − P)/100·notional; negative ⇒ the seller pays."""
    return (100.0 - fixed_coupon_price(spread, coupon, duration)) / 100.0 * notional


def cds_forward_spread(curve, recovery: float, r: float, start: float, maturity: float, freq: int = 1) -> float:
    """Par spread of a forward-start CDS on (start, maturity] that knocks out on early default (§25.5)."""
    if start < 0.0:
        raise ValueError("start must be >= 0")
    return cds_legs(curve, recovery, r, maturity, freq, start=start).par_spread


def cds_option(forward_spread: float, strike: float, sigma: float, expiry: float, risky_annuity: float, kind: str = "payer") -> float:
    """Black-type CDS option value: A·[F N(d₁) − K N(d₂)] (payer) or A·[K N(−d₂) − F N(−d₁)] (receiver).

    ``risky_annuity`` is the forward risky annuity of the underlying CDS; the option
    knocks out if the reference entity defaults before ``expiry`` (Hull §25.5; Hull & White 2003).
    """
    if kind not in ("payer", "receiver"):
        raise ValueError("kind must be 'payer' or 'receiver'")
    if forward_spread <= 0.0 or strike <= 0.0 or sigma < 0.0 or expiry <= 0.0 or risky_annuity <= 0.0:
        raise ValueError("forward_spread, strike, expiry and risky_annuity must be > 0 and sigma >= 0")
    vol = sigma * math.sqrt(expiry)
    if vol < 1e-12:
        intrinsic = forward_spread - strike if kind == "payer" else strike - forward_spread
        return risky_annuity * max(intrinsic, 0.0)
    d1 = (math.log(forward_spread / strike) + 0.5 * vol * vol) / vol
    d2 = d1 - vol
    if kind == "payer":
        return risky_annuity * (forward_spread * norm.cdf(d1) - strike * norm.cdf(d2))
    return risky_annuity * (strike * norm.cdf(-d2) - forward_spread * norm.cdf(-d1))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_cds.py`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/cds.py johnhull/hullkit/tests/test_cds.py
git commit -m "feat(hullkit): add single-name CDS legs, MTM, fixed coupon and options"
```

### Task 3: `credit_portfolio.py` — quadrature CDO, kth-to-default, implied correlations, double-t, ASB

**Files:**
- Create: `johnhull/hullkit/src/hullkit/credit_portfolio.py` (replace stub)
- Test: `johnhull/hullkit/tests/test_credit_portfolio.py`

**Interfaces:**
- Consumes: `cds.implied_hazard` (Task 2) in tests only.
- Produces: `gauss_hermite_factor(m=60) -> (nodes, weights)`; `conditional_default_prob(q, rho, factor)`; `binomial_pmf(n, p)`; `heterogeneous_default_pmf(cond_probs)`; `smallest_integer_above(x) -> int`; `tranche_principal_by_defaults(n_names, recovery, attach, detach) -> np.ndarray`; `TrancheValuation` (fields `payment_times, factor_nodes, factor_weights, expected_principal, annuity_by_factor, accrual_by_factor, protection_by_factor`; properties `annuity, accrual, protection, spread`; method `upfront(fixed_spread)`); `cdo_tranche_valuation(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq=4, m=60, copula="gaussian", nu=4.0) -> TrancheValuation`; `cdo_tranche_spread(...) -> float`; `cdo_upfront(..., fixed_spread=0.05) -> float`; `KthToDefaultValuation` (fields `payment_times, factor_nodes, factor_weights, cumulative_prob, payoff_by_factor, annuity_by_factor, accrual_by_factor`; properties `payoff, annuity, accrual, spread`); `kth_to_default_valuation(k, n_names, hazard, recovery, r, maturity, rho, freq=1, m=60) -> KthToDefaultValuation`; `kth_to_default_spread(...) -> float`; `compound_correlation(quote, attach, detach, hazard, recovery, r, maturity, n_names, freq=4, m=60, quote_kind="spread", fixed_spread=0.05, bracket=(1e-6, 0.999)) -> float`; `BaseCorrelationResult` (fields `attachments, detachments, compound, base, tranche_expected_loss, cumulative_expected_loss`); `base_correlations(quotes, attachments, hazard, recovery, r, maturity, n_names, freq=4, m=60, equity_fixed_spread=0.05) -> BaseCorrelationResult`; `expected_loss_curve(detachments, base_correlations, hazard, recovery, r, maturity, n_names, freq=4, m=60) -> np.ndarray`; `standardized_t_cdf(x, nu)`, `standardized_t_ppf(u, nu)`, `double_t_factor_quadrature(nu, m=60)`, `double_t_threshold(q, rho, nu, m=200) -> float`, `double_t_conditional_prob(q, rho, factor, nu, m=200)`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hullkit.credit_portfolio: Hull Examples 25.2/25.3, Table 25.8, copula identities."""

import numpy as np
import pytest
from hullkit import cds
from hullkit import credit_portfolio as cp
from scipy.stats import binom

EX_25_2 = dict(recovery=0.4, r=0.035, maturity=5.0, attach=0.03, detach=0.06, n_names=125, rho=0.15, freq=4)


@pytest.fixture(scope="module")
def mezz():
    lam = cds.implied_hazard(0.0050, 0.4, 0.035, 5.0, freq=4)
    return lam, cp.cdo_tranche_valuation(lam, **EX_25_2)


def _node_index(nodes, value):
    return int(np.argmin(np.abs(nodes - value)))


def test_gauss_hermite_nodes_match_table_25_7():
    nodes, weights = cp.gauss_hermite_factor(60)
    assert weights.sum() == pytest.approx(1.0, abs=1e-12)
    for value, weight in ((0.2020, 0.1579), (-0.2020, 0.1579), (-0.6060, 0.1342), (-1.0104, 0.0969)):
        i = _node_index(nodes, value)
        assert nodes[i] == pytest.approx(value, abs=5e-5)
        assert weights[i] == pytest.approx(weight, abs=5e-5)


def test_conditional_default_prob_matches_credit_module():
    from hullkit import credit

    q, rho, f = 0.05, 0.3, -1.0
    assert cp.conditional_default_prob(q, rho, f) == pytest.approx(
        credit.gaussian_copula_conditional(q, np.sqrt(rho), f), abs=1e-12
    )


def test_binomial_pmf_is_stable_and_matches_scipy():
    pmf = cp.binomial_pmf(125, np.array([0.0, 0.02, 1.0]))
    assert pmf.shape == (3, 126)
    np.testing.assert_allclose(pmf.sum(axis=1), 1.0, atol=1e-12)
    np.testing.assert_allclose(pmf[1], binom.pmf(np.arange(126), 125, 0.02), atol=1e-14)
    assert pmf[0, 0] == pytest.approx(1.0, abs=1e-12) and pmf[2, 125] == pytest.approx(1.0, abs=1e-12)


def test_heterogeneous_recursion_equals_binomial_when_homogeneous():
    p = np.full((3, 10), 0.07)
    p[1] = 0.3
    np.testing.assert_allclose(cp.heterogeneous_default_pmf(p)[0], binom.pmf(np.arange(11), 10, 0.07), atol=1e-12)
    np.testing.assert_allclose(cp.heterogeneous_default_pmf(p)[1], binom.pmf(np.arange(11), 10, 0.3), atol=1e-12)
    mixed = cp.heterogeneous_default_pmf(np.array([0.1, 0.5]))
    np.testing.assert_allclose(mixed, [0.45, 0.5, 0.05], atol=1e-12)


def test_example_25_2_hazard_and_conditional_columns(mezz):
    lam, val = mezz
    assert lam == pytest.approx(0.0083, abs=5e-5)
    cols = [_node_index(val.factor_nodes, v) for v in (0.2020, -0.2020, -0.6060, -1.0104)]
    np.testing.assert_allclose(val.expected_principal[cols, 19], [0.9953, 0.9687, 0.8636, 0.6134], atol=5e-5)
    np.testing.assert_allclose(val.expected_principal[cols, 20], [0.9936, 0.9600, 0.8364, 0.5648], atol=5e-5)
    np.testing.assert_allclose(val.annuity_by_factor[cols], [4.5624, 4.5345, 4.4080, 4.0361], atol=5e-5)
    np.testing.assert_allclose(val.accrual_by_factor[cols], [0.0007, 0.0043, 0.0178, 0.0478], atol=5e-5)
    np.testing.assert_allclose(val.protection_by_factor[cols], [0.0055, 0.0346, 0.1423, 0.3823], atol=5e-5)


def test_example_25_2_unconditional_legs_and_spread(mezz):
    _, val = mezz
    assert val.annuity == pytest.approx(4.2846, abs=5e-5)
    assert val.accrual == pytest.approx(0.0187, abs=5e-5)
    assert val.protection == pytest.approx(0.1496, abs=5e-5)
    assert val.spread * 1e4 == pytest.approx(348.0, abs=1.0)
    assert val.expected_principal[:, 0].min() == 1.0
    assert np.all(np.diff(val.expected_principal, axis=1) <= 1e-15)  # non-increasing in time
    order = np.argsort(val.factor_nodes)
    assert np.all(np.diff(val.expected_principal[order, -1]) >= -1e-15)  # non-decreasing in F


def test_capital_structure_loss_conservation(mezz):
    lam, _ = mezz
    bounds = [0.0, 0.03, 0.06, 0.09, 0.12, 0.22, 1.0]
    total = 0.0
    for lo, hi in zip(bounds[:-1], bounds[1:], strict=True):
        total += (hi - lo) * cp.cdo_tranche_valuation(lam, 0.4, 0.035, 5.0, lo, hi, 125, 0.15).protection
    whole = cp.cdo_tranche_valuation(lam, 0.4, 0.035, 5.0, 0.0, 1.0, 125, 0.15).protection
    assert total == pytest.approx(whole, abs=1e-12)


def test_example_25_3_third_to_default():
    val = cp.kth_to_default_valuation(3, 10, 0.02, 0.4, 0.05, 5.0, rho=0.3, freq=1)
    i = _node_index(val.factor_nodes, -1.0104)
    np.testing.assert_allclose(val.cumulative_prob[i, 1:], [0.0047, 0.0335, 0.0928, 0.1757, 0.2717], atol=5e-5)
    assert val.payoff_by_factor[i] == pytest.approx(0.1379, abs=5e-5)
    assert val.annuity_by_factor[i] == pytest.approx(3.8443, abs=5e-5)
    assert val.accrual_by_factor[i] == pytest.approx(0.1149, abs=5e-5)
    assert val.payoff == pytest.approx(0.0629, abs=5e-5)
    assert val.annuity == pytest.approx(4.0580, abs=5e-5)
    assert val.accrual == pytest.approx(0.0524, abs=5e-5)
    assert val.spread * 1e4 == pytest.approx(153.0, abs=1.0)
    spreads = [cp.kth_to_default_spread(k, 10, 0.02, 0.4, 0.05, 5.0, 0.3) for k in range(1, 6)]
    assert np.all(np.diff(spreads) < 0.0)


def test_table_25_8_compound_and_base_correlations():
    lam = cds.implied_hazard(0.0023, 0.4, 0.03, 5.0, freq=4)
    assert lam == pytest.approx(0.00382, abs=5e-6)
    quotes = [0.1034, 41.59e-4, 11.95e-4, 5.60e-4, 2.00e-4]
    result = cp.base_correlations(quotes, [0.0, 0.03, 0.06, 0.09, 0.12, 0.22], lam, 0.4, 0.03, 5.0, 125)
    np.testing.assert_allclose(result.compound * 100, [17.7, 7.8, 14.0, 18.2, 23.3], atol=0.15)
    np.testing.assert_allclose(result.base * 100, [17.7, 28.4, 36.5, 43.2, 60.5], atol=0.15)
    # implied correlations reprice the market quotes
    equity = cp.cdo_tranche_valuation(lam, 0.4, 0.03, 5.0, 0.0, 0.03, 125, result.compound[0])
    assert equity.upfront(0.05) == pytest.approx(0.1034, abs=1e-6)
    for lo, hi, rho, quote in zip([0.03, 0.06, 0.09, 0.12], [0.06, 0.09, 0.12, 0.22], result.compound[1:], quotes[1:], strict=True):
        assert cp.cdo_tranche_spread(lam, 0.4, 0.03, 5.0, lo, hi, 125, rho) == pytest.approx(quote, abs=1e-8)
    curve = cp.expected_loss_curve([0.03, 0.06, 0.09, 0.12, 0.22], result.base, lam, 0.4, 0.03, 5.0, 125)
    np.testing.assert_allclose(curve, result.cumulative_expected_loss, atol=1e-8)
    assert np.all(np.diff(curve) > 0.0) and np.all(np.diff(curve, n=2) < 0.0)  # increasing, concave


def test_double_t_limits_to_gaussian_and_threshold_is_consistent():
    q, rho = 0.04, 0.15
    assert cp.double_t_threshold(q, rho, nu=1e6) == pytest.approx(cp.conditional_default_prob(q, rho, 0.0) * 0 + __import__("scipy").stats.norm.ppf(q), abs=1e-4)
    nodes, weights = cp.double_t_factor_quadrature(4.0, 200)
    x_star = cp.double_t_threshold(q, rho, 4.0)
    unconditional = float(weights @ cp.double_t_conditional_prob(q, rho, nodes, 4.0))
    assert unconditional == pytest.approx(q, abs=1e-6)  # E_F[Q(t|F)] = Q(t)
    assert x_star != pytest.approx(__import__("scipy").stats.norm.ppf(q), abs=1e-3)
    gaussian = cp.cdo_tranche_spread(0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    limit = cp.cdo_tranche_spread(0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15, copula="double_t", nu=1e6)
    assert abs(limit - gaussian) * 1e4 < 0.5
    fat = cp.cdo_tranche_spread(0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15, copula="double_t", nu=4.0)
    assert fat != pytest.approx(gaussian, abs=1e-4)


def test_heterogeneous_hazards_reduce_to_homogeneous_valuation():
    hom = cp.cdo_tranche_valuation(0.0083, 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    het = cp.cdo_tranche_valuation(np.full(125, 0.0083), 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    assert het.spread == pytest.approx(hom.spread, abs=1e-12)
    skewed = cp.cdo_tranche_valuation(np.linspace(0.002, 0.0146, 125), 0.4, 0.035, 5.0, 0.03, 0.06, 125, 0.15)
    assert skewed.spread != pytest.approx(hom.spread, abs=1e-4)


def test_validation_errors():
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.06, 0.03, 125, 0.15)
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.03, 0.06, 125, 1.0)
    with pytest.raises(ValueError):
        cp.kth_to_default_valuation(0, 10, 0.02, 0.4, 0.05, 5.0, 0.3)
    with pytest.raises(ValueError):
        cp.cdo_tranche_valuation(0.01, 0.4, 0.03, 5.0, 0.03, 0.06, 125, 0.15, copula="clayton")
    with pytest.raises(ValueError):
        cp.double_t_threshold(0.05, 0.2, nu=2.0)
    with pytest.raises(ValueError):
        cp.base_correlations([0.1, 0.01], [0.01, 0.03, 0.06], 0.01, 0.4, 0.03, 5.0, 125)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_portfolio.py`
Expected: FAIL with `AttributeError: module 'hullkit.credit_portfolio' has no attribute ...`

- [ ] **Step 3: Write the implementation**

```python
"""One-factor copula valuation of CDO tranches and basket CDS (Hull 11e, §25.6–25.11).

The standard market model (Gaussian copula, Gauss–Hermite quadrature over the
common factor, eqs. 25.5–25.12), kth-to-default swaps, compound and base
correlations (Table 25.8), the double-t copula and the heterogeneous
Andersen–Sidenius–Basu recursion (§25.11).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq
from scipy.special import gammaln
from scipy.stats import norm
from scipy.stats import t as student_t


# --- factor quadrature -----------------------------------------------------


def gauss_hermite_factor(m: int = 60):
    """Nodes/weights approximating E[g(F)], F ~ N(0,1) (Hull eq. 25.12).

    With ``m=60`` the nodes nearest the origin are ±0.2020, −0.6060, −1.0104 with
    weights 0.1579, 0.1342, 0.0969 — the columns printed in Hull Table 25.7.
    """
    if int(m) != m or m < 1:
        raise ValueError("m must be a positive integer")
    x, w = np.polynomial.hermite.hermgauss(int(m))
    return np.sqrt(2.0) * x, w / np.sqrt(np.pi)


def standardized_t_cdf(x, nu: float):
    """CDF of a Student-t(ν) variable scaled to unit variance."""
    _check_nu(nu)
    return student_t.cdf(np.asarray(x, dtype=float) / math.sqrt((nu - 2.0) / nu), nu)


def standardized_t_ppf(u, nu: float):
    """Quantile of a unit-variance Student-t(ν) variable."""
    _check_nu(nu)
    return student_t.ppf(np.asarray(u, dtype=float), nu) * math.sqrt((nu - 2.0) / nu)


def double_t_factor_quadrature(nu: float, m: int = 60):
    """Nodes/weights for E[g(F)] with F a unit-variance t(ν): Gauss–Legendre in CDF space."""
    if int(m) != m or m < 1:
        raise ValueError("m must be a positive integer")
    x, w = np.polynomial.legendre.leggauss(int(m))
    u = 0.5 * (x + 1.0)
    return standardized_t_ppf(u, nu), 0.5 * w


def _factor_quadrature(copula: str, nu: float, m: int):
    if copula == "gaussian":
        return gauss_hermite_factor(m)
    if copula == "double_t":
        return double_t_factor_quadrature(nu, m)
    raise ValueError("copula must be 'gaussian' or 'double_t'")


# --- conditional default probabilities --------------------------------------


def conditional_default_prob(q, rho: float, factor):
    """Q(t | F) = N((N⁻¹(Q) − √ρ F)/√(1−ρ)) (Hull eq. 25.5), broadcasting over inputs."""
    _check_rho(rho)
    q = np.asarray(q, dtype=float)
    f = np.asarray(factor, dtype=float)
    return norm.cdf((norm.ppf(q) - math.sqrt(rho) * f) / math.sqrt(1.0 - rho))


def double_t_threshold(q: float, rho: float, nu: float, m: int = 200) -> float:
    """Default threshold x* with P(√ρF + √(1−ρ)Z ≤ x*) = q for unit-variance t(ν) factors."""
    _check_rho(rho)
    _check_nu(nu)
    if not 0.0 < q < 1.0:
        raise ValueError("q must lie in (0, 1)")
    nodes, weights = double_t_factor_quadrature(nu, m)
    scale = math.sqrt(1.0 - rho)

    def cdf(x: float) -> float:
        return float(weights @ standardized_t_cdf((x - math.sqrt(rho) * nodes) / scale, nu)) - q

    return float(brentq(cdf, -60.0, 60.0, xtol=1e-13))


def double_t_conditional_prob(q, rho: float, factor, nu: float, m: int = 200):
    """Q(t | F) under the double-t copula: T_std((x*(q) − √ρF)/√(1−ρ)) (Hull & White 2004)."""
    q = np.asarray(q, dtype=float)
    f = np.asarray(factor, dtype=float)
    thresholds = np.vectorize(lambda value: double_t_threshold(float(value), rho, nu, m))(q)
    return standardized_t_cdf((thresholds - math.sqrt(rho) * f) / math.sqrt(1.0 - rho), nu)


def _conditional_probs(q, rho: float, nodes: np.ndarray, copula: str, nu: float):
    """Conditional default probabilities with shape (M,) + q.shape."""
    q = np.asarray(q, dtype=float)
    f = nodes.reshape((-1,) + (1,) * q.ndim)
    if copula == "gaussian":
        return conditional_default_prob(q[None, ...], rho, f)
    return double_t_conditional_prob(q[None, ...], rho, f, nu)


# --- default-count distributions ---------------------------------------------


def binomial_pmf(n: int, p):
    """P(k defaults | p) for k = 0..n along a new trailing axis (Hull eq. 25.7), stable at p→0, 1."""
    if int(n) != n or n < 1:
        raise ValueError("n must be a positive integer")
    p = np.clip(np.asarray(p, dtype=float), 1e-300, 1.0 - 1e-16)[..., None]
    k = np.arange(n + 1, dtype=float)
    log_choose = gammaln(n + 1.0) - gammaln(k + 1.0) - gammaln(n - k + 1.0)
    return np.exp(log_choose + k * np.log(p) + (n - k) * np.log1p(-p))


def heterogeneous_default_pmf(cond_probs):
    """Default-count pmf for names with different conditional PDs (Andersen–Sidenius–Basu recursion).

    ``cond_probs`` has the names on its last axis; the result has k = 0..n on its last axis.
    With equal probabilities the recursion reproduces the binomial distribution.
    """
    p = np.asarray(cond_probs, dtype=float)
    if p.ndim == 0 or p.shape[-1] < 1:
        raise ValueError("cond_probs must have at least one name on its last axis")
    n = p.shape[-1]
    pmf = np.zeros(p.shape[:-1] + (n + 1,))
    pmf[..., 0] = 1.0
    for i in range(n):
        p_i = p[..., i][..., None]
        shifted = np.concatenate([np.zeros_like(pmf[..., :1]), pmf[..., :-1]], axis=-1)
        pmf = pmf * (1.0 - p_i) + shifted * p_i
    return pmf


def _default_count_pmf(hazard, times: np.ndarray, rho: float, nodes: np.ndarray, n_names: int, copula: str, nu: float):
    """Return the (M, len(times), n+1) default-count pmf for constant or per-name hazards."""
    hazard = np.asarray(hazard, dtype=float)
    if np.any(hazard < 0.0):
        raise ValueError("hazard must be >= 0")
    if hazard.ndim == 0:
        q = 1.0 - np.exp(-float(hazard) * times)
        return binomial_pmf(n_names, _conditional_probs(q, rho, nodes, copula, nu))
    if hazard.shape != (n_names,):
        raise ValueError("hazard must be a scalar or an array of length n_names")
    q = 1.0 - np.exp(-hazard[None, :] * times[:, None])
    return heterogeneous_default_pmf(_conditional_probs(q, rho, nodes, copula, nu))


# --- tranche principal --------------------------------------------------------


def smallest_integer_above(x: float) -> int:
    """m(x): the smallest integer strictly greater than x (Hull §25.10)."""
    return int(math.floor(x)) + 1


def tranche_principal_by_defaults(n_names: int, recovery: float, attach: float, detach: float):
    """Tranche principal (initial = 1) after k defaults, k = 0..n (Hull eq. 25.8 pieces)."""
    _check_tranche(attach, detach)
    _check_recovery(recovery)
    n_low = attach * n_names / (1.0 - recovery)
    n_high = detach * n_names / (1.0 - recovery)
    m_low, m_high = smallest_integer_above(n_low), smallest_integer_above(n_high)
    k = np.arange(n_names + 1)
    partial = (detach - k * (1.0 - recovery) / n_names) / (detach - attach)
    return np.where(k < m_low, 1.0, np.where(k >= m_high, 0.0, np.clip(partial, 0.0, 1.0)))


@dataclass(frozen=True)
class TrancheValuation:
    """Conditional and unconditional tranche legs (Hull eqs. 25.9–25.12); principal = 1, spread = 1."""

    payment_times: np.ndarray
    factor_nodes: np.ndarray
    factor_weights: np.ndarray
    expected_principal: np.ndarray
    annuity_by_factor: np.ndarray
    accrual_by_factor: np.ndarray
    protection_by_factor: np.ndarray

    @property
    def annuity(self) -> float:
        """A = E_F[A(F)]."""
        return float(self.factor_weights @ self.annuity_by_factor)

    @property
    def accrual(self) -> float:
        """B = E_F[B(F)]."""
        return float(self.factor_weights @ self.accrual_by_factor)

    @property
    def protection(self) -> float:
        """C = E_F[C(F)] — PV of expected tranche loss per unit tranche principal."""
        return float(self.factor_weights @ self.protection_by_factor)

    @property
    def spread(self) -> float:
        """Breakeven spread s = C/(A+B) (Hull eq. 25.4)."""
        return self.protection / (self.annuity + self.accrual)

    def upfront(self, fixed_spread: float) -> float:
        """Upfront payment as a fraction of tranche principal: C − s*(A+B)."""
        return self.protection - fixed_spread * (self.annuity + self.accrual)


def _payment_grid(maturity: float, freq: int):
    if int(freq) != freq or freq < 1:
        raise ValueError("freq must be a positive integer")
    n = round(maturity * freq)
    if n <= 0 or abs(n / freq - maturity) > 1e-9:
        raise ValueError("maturity must be a whole number of payment periods")
    times = np.arange(1, n + 1) / freq
    previous = times - 1.0 / freq
    return times, previous, 0.5 * (times + previous)


def cdo_tranche_valuation(
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    attach: float,
    detach: float,
    n_names: int,
    rho: float,
    freq: int = 4,
    m: int = 60,
    copula: str = "gaussian",
    nu: float = 4.0,
) -> TrancheValuation:
    """Standard market model for a synthetic CDO tranche (Hull §25.10, Example 25.2).

    ``hazard`` is a constant (homogeneous, binomial conditional counts) or an array of
    per-name hazards (heterogeneous, ASB recursion). ``copula`` selects the Gaussian
    or double-t one-factor copula. Returns conditional legs on the factor grid.
    """
    if int(n_names) != n_names or n_names < 1:
        raise ValueError("n_names must be a positive integer")
    _check_rho(rho)
    times, _previous, mid = _payment_grid(maturity, freq)
    nodes, weights = _factor_quadrature(copula, nu, m)
    pmf = _default_count_pmf(hazard, times, rho, nodes, int(n_names), copula, nu)
    principal = tranche_principal_by_defaults(int(n_names), recovery, attach, detach)
    expected = np.concatenate([np.ones((nodes.size, 1)), pmf @ principal], axis=1)
    dt = np.diff(np.concatenate([[0.0], times]))
    discount = np.exp(-r * times)
    discount_mid = np.exp(-r * mid)
    loss = expected[:, :-1] - expected[:, 1:]
    annuity = (dt * expected[:, 1:] * discount).sum(axis=1)
    accrual = (0.5 * dt * loss * discount_mid).sum(axis=1)
    protection = (loss * discount_mid).sum(axis=1)
    return TrancheValuation(times, nodes, weights, expected, annuity, accrual, protection)


def cdo_tranche_spread(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq=4, m=60, copula="gaussian", nu=4.0) -> float:
    """Breakeven tranche spread C/(A+B) (Hull Example 25.2: 348 bp)."""
    return cdo_tranche_valuation(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m, copula, nu).spread


def cdo_upfront(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq=4, m=60, copula="gaussian", nu=4.0, fixed_spread=0.05) -> float:
    """Upfront payment C − s*(A+B) for a tranche quoted with a fixed running spread (equity: 500 bp)."""
    return cdo_tranche_valuation(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m, copula, nu).upfront(fixed_spread)


# --- kth-to-default ------------------------------------------------------------


@dataclass(frozen=True)
class KthToDefaultValuation:
    """Conditional/unconditional legs of a kth-to-default CDS (Hull §25.10, Example 25.3)."""

    payment_times: np.ndarray
    factor_nodes: np.ndarray
    factor_weights: np.ndarray
    cumulative_prob: np.ndarray
    payoff_by_factor: np.ndarray
    annuity_by_factor: np.ndarray
    accrual_by_factor: np.ndarray

    @property
    def payoff(self) -> float:
        """PV of expected payoff, per unit notional."""
        return float(self.factor_weights @ self.payoff_by_factor)

    @property
    def annuity(self) -> float:
        """PV of regular payments per unit spread."""
        return float(self.factor_weights @ self.annuity_by_factor)

    @property
    def accrual(self) -> float:
        """PV of accrual payments per unit spread."""
        return float(self.factor_weights @ self.accrual_by_factor)

    @property
    def spread(self) -> float:
        """Breakeven spread payoff/(annuity + accrual)."""
        return self.payoff / (self.annuity + self.accrual)


def kth_to_default_valuation(k: int, n_names: int, hazard, recovery: float, r: float, maturity: float, rho: float, freq: int = 1, m: int = 60, copula: str = "gaussian", nu: float = 4.0) -> KthToDefaultValuation:
    """Value a kth-to-default CDS by conditioning on the factor (Hull Example 25.3: 153 bp).

    The kth default falls in (t_{j-1}, t_j] with conditional probability
    P(≥k by t_j | F) − P(≥k by t_{j-1} | F); settlement at the midpoint, accrual half a period.
    """
    if int(k) != k or int(n_names) != n_names or not 1 <= k <= n_names:
        raise ValueError("k must be an integer in [1, n_names]")
    _check_rho(rho)
    _check_recovery(recovery)
    times, _previous, mid = _payment_grid(maturity, freq)
    nodes, weights = _factor_quadrature(copula, nu, m)
    pmf = _default_count_pmf(hazard, times, rho, nodes, int(n_names), copula, nu)
    at_least_k = np.concatenate([np.zeros((nodes.size, 1)), pmf[:, :, int(k):].sum(axis=2)], axis=1)
    dt = np.diff(np.concatenate([[0.0], times]))
    discount = np.exp(-r * times)
    discount_mid = np.exp(-r * mid)
    trigger = at_least_k[:, 1:] - at_least_k[:, :-1]
    payoff = ((1.0 - recovery) * trigger * discount_mid).sum(axis=1)
    annuity = (dt * (1.0 - at_least_k[:, 1:]) * discount).sum(axis=1)
    accrual = (0.5 * dt * trigger * discount_mid).sum(axis=1)
    return KthToDefaultValuation(times, nodes, weights, at_least_k, payoff, annuity, accrual)


def kth_to_default_spread(k, n_names, hazard, recovery, r, maturity, rho, freq=1, m=60, copula="gaussian", nu=4.0) -> float:
    """Breakeven spread of a kth-to-default CDS."""
    return kth_to_default_valuation(k, n_names, hazard, recovery, r, maturity, rho, freq, m, copula, nu).spread


# --- implied correlations -------------------------------------------------------


def compound_correlation(
    quote: float,
    attach: float,
    detach: float,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    n_names: int,
    freq: int = 4,
    m: int = 60,
    quote_kind: str = "spread",
    fixed_spread: float = 0.05,
    bracket: tuple[float, float] = (1e-6, 0.999),
) -> float:
    """Copula correlation at which the model reproduces one tranche quote (Hull §25.10)."""
    if quote_kind not in ("spread", "upfront"):
        raise ValueError("quote_kind must be 'spread' or 'upfront'")

    def gap(rho: float) -> float:
        valuation = cdo_tranche_valuation(hazard, recovery, r, maturity, attach, detach, n_names, rho, freq, m)
        model = valuation.spread if quote_kind == "spread" else valuation.upfront(fixed_spread)
        return model - quote

    try:
        return float(brentq(gap, bracket[0], bracket[1], xtol=1e-12))
    except ValueError as exc:
        raise ValueError("compound_correlation: no correlation in the bracket reproduces the quote") from exc


@dataclass(frozen=True)
class BaseCorrelationResult:
    """Compound and base correlations with the expected-loss bookkeeping behind them."""

    attachments: np.ndarray
    detachments: np.ndarray
    compound: np.ndarray
    base: np.ndarray
    tranche_expected_loss: np.ndarray
    cumulative_expected_loss: np.ndarray


def base_correlations(
    quotes,
    attachments,
    hazard,
    recovery: float,
    r: float,
    maturity: float,
    n_names: int,
    freq: int = 4,
    m: int = 60,
    equity_fixed_spread: float = 0.05,
) -> BaseCorrelationResult:
    """Hull's four-step base-correlation bootstrap (Table 25.8).

    ``attachments`` are the tranche boundaries a_0=0 < a_1 < …; ``quotes[0]`` is the
    equity upfront fraction (running ``equity_fixed_spread``), the rest are spreads.
    Step 1 compound correlations; step 2 C_q per tranche; step 3 cumulative expected
    loss on 0–a_q as a fraction of portfolio principal; step 4 the ρ that prices 0–a_q.
    """
    bounds = np.asarray(attachments, dtype=float)
    quotes = np.asarray(quotes, dtype=float)
    if bounds.ndim != 1 or bounds.size != quotes.size + 1 or bounds[0] != 0.0 or np.any(np.diff(bounds) <= 0.0):
        raise ValueError("attachments must start at 0, be strictly increasing, and have len(quotes)+1 entries")
    lows, highs = bounds[:-1], bounds[1:]
    compound = np.empty(quotes.size)
    tranche_loss = np.empty(quotes.size)
    for i, (lo, hi, quote) in enumerate(zip(lows, highs, quotes, strict=True)):
        kind = "upfront" if i == 0 else "spread"
        compound[i] = compound_correlation(float(quote), float(lo), float(hi), hazard, recovery, r, maturity, n_names, freq, m, kind, equity_fixed_spread)
        tranche_loss[i] = cdo_tranche_valuation(hazard, recovery, r, maturity, float(lo), float(hi), n_names, compound[i], freq, m).protection
    cumulative = np.cumsum(tranche_loss * (highs - lows))
    base = np.empty(quotes.size)
    for i, hi in enumerate(highs):
        target = cumulative[i] / hi

        def gap(rho: float, hi: float = float(hi), target: float = float(target)) -> float:
            return cdo_tranche_valuation(hazard, recovery, r, maturity, 0.0, hi, n_names, rho, freq, m).protection - target

        try:
            base[i] = brentq(gap, 1e-6, 0.999, xtol=1e-12)
        except ValueError as exc:
            raise ValueError(f"base_correlations: no correlation prices the 0-{hi:.0%} tranche") from exc
    return BaseCorrelationResult(lows, highs, compound, base, tranche_loss, cumulative)


def expected_loss_curve(detachments, base_correlations, hazard, recovery: float, r: float, maturity: float, n_names: int, freq: int = 4, m: int = 60):
    """PV of expected loss on the 0–X% tranche as a fraction of portfolio principal (Hull Figure 25.3)."""
    detachments = np.asarray(detachments, dtype=float)
    rhos = np.asarray(base_correlations, dtype=float)
    if detachments.shape != rhos.shape:
        raise ValueError("detachments and base_correlations must have equal length")
    return np.asarray(
        [cdo_tranche_valuation(hazard, recovery, r, maturity, 0.0, float(x), n_names, float(rho), freq, m).protection * float(x) for x, rho in zip(detachments, rhos, strict=True)]
    )


# --- validation helpers ------------------------------------------------------------


def _check_rho(rho: float) -> None:
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")


def _check_recovery(recovery: float) -> None:
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")


def _check_tranche(attach: float, detach: float) -> None:
    if not 0.0 <= attach < detach <= 1.0:
        raise ValueError("tranche must satisfy 0 <= attach < detach <= 1")


def _check_nu(nu: float) -> None:
    if not nu > 2.0:
        raise ValueError("nu must exceed 2 so the t distribution has finite variance")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_portfolio.py`
Expected: 13 passed (Table 25.8 test takes a few seconds). If `double_t` limit exceeds 0.5 bp, raise the default `m` used by `double_t_factor_quadrature` inside `_factor_quadrature` to 200 and record the observed gap.

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/credit_portfolio.py johnhull/hullkit/tests/test_credit_portfolio.py
git commit -m "feat(hullkit): add one-factor copula CDO, kth-to-default and implied correlations"
```

### Task 4: `credit_metrics.py` — Table 24.4, thresholds, correlated migration MC

**Files:**
- Create: `johnhull/hullkit/src/hullkit/credit_metrics.py` (replace stub)
- Test: `johnhull/hullkit/tests/test_credit_metrics.py`

**Interfaces:**
- Produces: `RATINGS: tuple[str, ...]`; `HULL_TABLE_24_4: np.ndarray` (7×8, percent); `TransitionMatrix(probabilities, ratings=RATINGS)` with `.from_percent(table, ratings=RATINGS, tol=0.0005)`, `.row(initial)`, `.default_probability(initial)`, `.multi_period(years) -> TransitionMatrix`, `.index(rating) -> int`; `rating_thresholds(matrix, initial) -> np.ndarray`; `migrate(matrix, initial, x) -> np.ndarray[int]`; `simulate_rating_migrations(matrix, initial_ratings, rho, n_sims, rng=None) -> np.ndarray[int] (n_sims, n_obligors)`; `credit_loss_distribution(new_ratings, exposures, recovery, ratings=RATINGS, rating_values=None) -> np.ndarray (n_sims,)`; `credit_var(losses, confidence) -> float`; `expected_loss(losses) -> float`.

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for hullkit.credit_metrics: Hull Table 24.4 thresholds and correlated migrations."""

import numpy as np
import pytest
from hullkit import credit_metrics as cm


def test_hull_table_rows_sum_to_100_within_rounding():
    sums = cm.HULL_TABLE_24_4.sum(axis=1)
    np.testing.assert_allclose(sums, 100.0, atol=0.05)
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    assert matrix.probabilities.shape == (8, 8)
    assert matrix.probabilities[-1, -1] == 1.0  # default is absorbing


def test_thresholds_match_hull_page_582():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    aaa = cm.rating_thresholds(matrix, "AAA")
    np.testing.assert_allclose(aaa[:3], [1.2719, 2.4089, 2.8070], atol=2e-4)
    bbb = cm.rating_thresholds(matrix, "BBB")
    np.testing.assert_allclose(bbb[:3], [-3.7190, -3.0618, -1.7866], atol=2e-4)
    assert bbb[-1] == pytest.approx(2.9290, abs=2e-4)  # default when x > 2.9290


def test_migrate_uses_thresholds_in_column_order():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    x = np.array([1.0, 1.5, 2.5, 3.0, 9.0])
    np.testing.assert_array_equal(cm.migrate(matrix, "AAA", x), [0, 1, 2, 3, 7])
    x = np.array([-4.0, -3.5, -2.0, 0.0, 3.0])
    np.testing.assert_array_equal(cm.migrate(matrix, "BBB", x), [0, 1, 2, 3, 7])


def test_multi_period_matrix_is_a_matrix_power():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    two_year = matrix.multi_period(2)
    np.testing.assert_allclose(two_year.probabilities, matrix.probabilities @ matrix.probabilities, atol=1e-15)
    assert two_year.default_probability("CCC/C") > matrix.default_probability("CCC/C")


def test_simulation_default_frequency_matches_row_and_correlation_fattens_tail():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    initial = ["BBB"] * 200
    exposures = np.full(200, 1.0)
    independent = cm.simulate_rating_migrations(matrix, initial, rho=0.0, n_sims=20_000, rng=np.random.default_rng(1))
    correlated = cm.simulate_rating_migrations(matrix, initial, rho=0.2, n_sims=20_000, rng=np.random.default_rng(1))
    default_index = matrix.index("Default")
    freq = (independent == default_index).mean()
    p = matrix.default_probability("BBB")
    assert abs(freq - p) < 4 * np.sqrt(p * (1 - p) / (200 * 20_000))
    loss_ind = cm.credit_loss_distribution(independent, exposures, recovery=0.4)
    loss_cor = cm.credit_loss_distribution(correlated, exposures, recovery=0.4)
    assert cm.expected_loss(loss_ind) == pytest.approx(cm.expected_loss(loss_cor), rel=0.1)
    assert cm.credit_var(loss_cor, 0.999) > cm.credit_var(loss_ind, 0.999)


def test_rating_values_add_downgrade_losses():
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    new_ratings = np.array([[3, 4, 7]])  # BBB stays, BBB→BB, BBB→Default
    exposures = np.array([100.0, 100.0, 100.0])
    values = {"AAA": 1.02, "AA": 1.01, "A": 1.005, "BBB": 1.0, "BB": 0.97, "B": 0.93, "CCC/C": 0.85}
    losses = cm.credit_loss_distribution(new_ratings, exposures, recovery=0.4, rating_values=values, initial_ratings=["BBB"] * 3)
    assert losses[0] == pytest.approx(0.0 + 3.0 + 60.0, abs=1e-12)
    without = cm.credit_loss_distribution(new_ratings, exposures, recovery=0.4)
    assert without[0] == pytest.approx(60.0, abs=1e-12)
    assert matrix.index("BB") == 4


def test_validation_errors():
    bad = cm.HULL_TABLE_24_4.copy()
    bad[0, 0] += 1.0
    with pytest.raises(ValueError):
        cm.TransitionMatrix.from_percent(bad)
    matrix = cm.TransitionMatrix.from_percent(cm.HULL_TABLE_24_4)
    with pytest.raises(ValueError):
        cm.rating_thresholds(matrix, "Default")
    with pytest.raises(ValueError):
        cm.simulate_rating_migrations(matrix, ["AAA"], rho=1.0, n_sims=10)
    with pytest.raises(ValueError):
        cm.credit_var(np.array([1.0, 2.0]), confidence=1.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_metrics.py`
Expected: FAIL with `AttributeError: module 'hullkit.credit_metrics' has no attribute 'HULL_TABLE_24_4'`

- [ ] **Step 3: Write the implementation**

```python
"""CreditMetrics: rating transitions and credit VaR (Hull 11e, §24.9).

Hull Table 24.4 (S&P 1981–2019 one-year transition matrix, WR reallocated) is
transcribed as a textbook fixture. Rating changes are sampled with a one-factor
Gaussian copula: obligor i moves to the rating whose cumulative-probability
band (in column order AAA…Default) contains x_i = √ρ F + √(1−ρ) Z_i.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

RATINGS: tuple[str, ...] = ("AAA", "AA", "A", "BBB", "BB", "B", "CCC/C", "Default")

HULL_TABLE_24_4 = np.array(
    [
        [89.83, 9.37, 0.55, 0.05, 0.11, 0.03, 0.05, 0.00],
        [0.51, 90.77, 8.06, 0.50, 0.05, 0.06, 0.02, 0.02],
        [0.03, 1.74, 92.49, 5.27, 0.28, 0.12, 0.02, 0.05],
        [0.01, 0.10, 3.59, 91.83, 3.73, 0.47, 0.11, 0.17],
        [0.01, 0.03, 0.12, 5.23, 86.06, 7.27, 0.60, 0.67],
        [0.00, 0.02, 0.08, 0.18, 5.43, 85.38, 5.10, 3.80],
        [0.00, 0.00, 0.13, 0.22, 0.69, 15.33, 51.61, 32.03],
    ]
)
"""Hull 11e Table 24.4: one-year transition probabilities in percent (rows: initial rating)."""


@dataclass(frozen=True)
class TransitionMatrix:
    """Square one-period transition matrix (fractions) with an absorbing default state.

    Rows are kept as printed (no renormalisation) so that the thresholds reproduce
    Hull's page-582 numbers; the rounding residual of a row (≤ ``tol``) therefore
    falls into the last state when sampling.
    """

    probabilities: np.ndarray
    ratings: tuple[str, ...] = RATINGS

    def __post_init__(self) -> None:
        p = np.asarray(self.probabilities, dtype=float)
        n = len(self.ratings)
        if p.shape != (n, n):
            raise ValueError(f"probabilities must be {n}x{n} to match ratings")
        if np.any(p < 0.0) or np.any(~np.isfinite(p)):
            raise ValueError("probabilities must be finite and >= 0")
        if np.any(np.abs(p.sum(axis=1) - 1.0) > 5e-4):
            raise ValueError("each row must sum to 1 within 0.0005")
        object.__setattr__(self, "probabilities", p)
        object.__setattr__(self, "ratings", tuple(self.ratings))

    @classmethod
    def from_percent(cls, table, ratings: tuple[str, ...] = RATINGS, tol: float = 5e-4) -> TransitionMatrix:
        """Build from a percent table of live ratings × all states, appending the absorbing default row."""
        table = np.asarray(table, dtype=float) / 100.0
        n = len(ratings)
        if table.shape != (n - 1, n):
            raise ValueError(f"table must have shape {(n - 1, n)}")
        if np.any(np.abs(table.sum(axis=1) - 1.0) > tol):
            raise ValueError(f"rows must sum to 100% within {tol * 100:.2f} points")
        absorbing = np.zeros((1, n))
        absorbing[0, -1] = 1.0
        return cls(np.vstack([table, absorbing]), ratings)

    def index(self, rating: str) -> int:
        """Column/row index of a rating label."""
        try:
            return self.ratings.index(rating)
        except ValueError as exc:
            raise ValueError(f"unknown rating {rating!r}") from exc

    def row(self, initial: str) -> np.ndarray:
        """Transition probabilities out of ``initial``."""
        return self.probabilities[self.index(initial)]

    def default_probability(self, initial: str) -> float:
        """One-period probability of moving from ``initial`` to the default state."""
        return float(self.row(initial)[-1])

    def multi_period(self, years: int) -> TransitionMatrix:
        """Transition matrix over ``years`` periods (matrix power; Hull Technical Note 11)."""
        if int(years) != years or years < 1:
            raise ValueError("years must be a positive integer")
        return TransitionMatrix(np.linalg.matrix_power(self.probabilities, int(years)), self.ratings)


def rating_thresholds(matrix: TransitionMatrix, initial: str) -> np.ndarray:
    """Upper thresholds N⁻¹(cumulative probability) in column order for a live initial rating.

    For Hull's AAA row: 1.2719, 2.4089, 2.8070, …; for BBB: −3.7190, −3.0618, −1.7866, …, 2.9290.
    """
    if initial == matrix.ratings[-1]:
        raise ValueError("thresholds are defined for live ratings only")
    cumulative = np.cumsum(matrix.row(initial))[:-1]
    return norm.ppf(np.clip(cumulative, 0.0, 1.0))


def migrate(matrix: TransitionMatrix, initial: str, x) -> np.ndarray:
    """Map standard-normal draws to end-of-period rating indices via the thresholds."""
    thresholds = rating_thresholds(matrix, initial)
    return np.searchsorted(thresholds, np.asarray(x, dtype=float), side="right")


def simulate_rating_migrations(matrix: TransitionMatrix, initial_ratings, rho: float, n_sims: int, rng=None) -> np.ndarray:
    """Sample correlated rating changes: x_i = √ρ F + √(1−ρ) Z_i (Hull §24.9 CreditMetrics)."""
    if not 0.0 <= rho < 1.0:
        raise ValueError("rho must lie in [0, 1)")
    if int(n_sims) != n_sims or n_sims < 1:
        raise ValueError("n_sims must be a positive integer")
    rng = np.random.default_rng() if rng is None else rng
    labels = list(initial_ratings)
    factor = rng.standard_normal((int(n_sims), 1))
    idiosyncratic = rng.standard_normal((int(n_sims), len(labels)))
    x = np.sqrt(rho) * factor + np.sqrt(1.0 - rho) * idiosyncratic
    out = np.empty((int(n_sims), len(labels)), dtype=int)
    for j, label in enumerate(labels):
        out[:, j] = migrate(matrix, label, x[:, j])
    return out


def credit_loss_distribution(new_ratings, exposures, recovery: float, ratings: tuple[str, ...] = RATINGS, rating_values=None, initial_ratings=None) -> np.ndarray:
    """Portfolio credit loss per simulation: exposure·(1−R) on default, plus optional migration losses.

    ``rating_values`` maps live ratings to a value ratio (e.g. BBB 1.00, BB 0.97); with
    ``initial_ratings`` the loss on a non-defaulted obligor is exposure·(v_initial − v_new),
    so upgrades count as negative losses (CreditMetrics convention).
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    new_ratings = np.asarray(new_ratings, dtype=int)
    exposures = np.asarray(exposures, dtype=float)
    if new_ratings.ndim != 2 or new_ratings.shape[1] != exposures.size:
        raise ValueError("new_ratings must be (n_sims, n_obligors) matching exposures")
    default_index = len(ratings) - 1
    defaulted = new_ratings == default_index
    losses = (defaulted * exposures[None, :] * (1.0 - recovery)).sum(axis=1)
    if rating_values is not None:
        if initial_ratings is None:
            raise ValueError("initial_ratings are required with rating_values")
        values = np.array([rating_values[label] for label in ratings[:-1]] + [0.0])
        start = np.array([rating_values[label] for label in initial_ratings])
        migration = (start[None, :] - values[new_ratings]) * exposures[None, :]
        losses = losses + np.where(defaulted, 0.0, migration).sum(axis=1)
    return losses


def credit_var(losses, confidence: float) -> float:
    """Credit VaR: the ``confidence`` quantile of the simulated loss distribution."""
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie in (0, 1)")
    return float(np.quantile(np.asarray(losses, dtype=float), confidence))


def expected_loss(losses) -> float:
    """Mean simulated credit loss."""
    return float(np.mean(np.asarray(losses, dtype=float)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_credit_metrics.py`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/credit_metrics.py johnhull/hullkit/tests/test_credit_metrics.py
git commit -m "feat(hullkit): add CreditMetrics transition thresholds and correlated migrations"
```

### Task 5: `xva.py` additions — spread-implied q_i, netting, collateral, eq. 24.5

**Files:**
- Modify: `johnhull/hullkit/src/hullkit/xva.py` (append after `fva`)
- Test: `johnhull/hullkit/tests/test_xva.py` (append)

**Interfaces:**
- Produces: `default_probs_from_spreads(times, spreads, recovery) -> np.ndarray`; `netting_set_exposure(values, netting=True) -> np.ndarray`; `collateralized_exposure(value, lagged_value, threshold=0.0) -> np.ndarray`; `cva_single_payoff(no_default_value, recovery, default_probs) -> float`.

- [ ] **Step 1: Append the failing tests**

```python
def test_default_probs_from_spreads_follow_hull_24_7():
    times = np.array([1.0, 2.0, 3.0])
    spreads = np.array([0.0150, 0.0180, 0.0195])  # Example 24.1 spreads
    q = xva.default_probs_from_spreads(times, spreads, recovery=0.4)
    survival = np.exp(-spreads * times / 0.6)
    np.testing.assert_allclose(q, np.diff(np.concatenate([[1.0], survival])) * -1.0, atol=1e-15)
    assert q.sum() == pytest.approx(1.0 - survival[-1], abs=1e-15)


def test_netting_reduces_exposure_from_40_to_15():
    trades = np.array([10.0, 30.0, -25.0])
    assert xva.netting_set_exposure(trades) == pytest.approx(15.0)
    assert xva.netting_set_exposure(trades, netting=False) == pytest.approx(40.0)
    paths = np.array([[10.0, 30.0, -25.0], [-5.0, -5.0, 2.0]])
    np.testing.assert_allclose(xva.netting_set_exposure(paths), [15.0, 0.0])


def test_collateral_rule_reproduces_example_24_4():
    value = np.array([50.0, 50.0, -50.0, -50.0])
    lagged = np.array([45.0, 55.0, -45.0, -55.0])
    np.testing.assert_allclose(xva.collateralized_exposure(value, lagged), [5.0, 0.0, 0.0, 5.0])
    # a threshold reduces the collateral that would have been posted
    np.testing.assert_allclose(xva.collateralized_exposure(value, lagged, threshold=10.0), [15.0, 5.0, 0.0, 0.0])


def test_cva_special_case_matches_general_formula():
    r, T, f_nd, R, hazard = 0.05, 2.0, 7.0, 0.4, 0.03
    t = np.linspace(0.0, T, 401)
    q = xva.default_probs_from_spreads(t[1:], np.full(400, hazard * (1 - R)), R)
    special = xva.cva_single_payoff(f_nd, R, q)
    assert special == pytest.approx((1 - R) * f_nd * (1 - np.exp(-hazard * T)), abs=1e-12)
    # exposure of a single-payoff derivative grows at the risk-free rate: EE_t = f_nd e^{rt}
    general = xva.cva(t, f_nd * np.exp(r * t), hazard, R, r)
    assert general == pytest.approx(special, abs=2e-4)
```

Also add `import pytest` to the test module header.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_xva.py`
Expected: 4 failed with `AttributeError: module 'hullkit.xva' has no attribute 'default_probs_from_spreads'`

- [ ] **Step 3: Append the implementation to `xva.py`**

```python
def default_probs_from_spreads(times, spreads, recovery):
    """Per-interval default probabilities from a credit-spread term structure (Hull §24.7).

    q_i = exp(−s(t_{i−1}) t_{i−1}/(1−R)) − exp(−s(t_i) t_i/(1−R)) with t_0 = 0.
    """
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    times = np.asarray(times, dtype=float)
    spreads = np.asarray(spreads, dtype=float)
    if times.shape != spreads.shape or times.ndim != 1 or np.any(np.diff(times) <= 0.0) or times[0] <= 0.0:
        raise ValueError("times must be positive, increasing, and match spreads")
    survival = np.concatenate([[1.0], np.exp(-spreads * times / (1.0 - recovery))])
    return -np.diff(survival)


def netting_set_exposure(values, netting=True):
    """Exposure of a set of trades (last axis): max(Σv, 0) with netting, Σ max(v, 0) without.

    Hull §24.7: trades worth +10, +30, −25 expose 40 without netting and 15 with it.
    """
    values = np.asarray(values, dtype=float)
    if netting:
        return np.maximum(values.sum(axis=-1), 0.0)
    return np.maximum(values, 0.0).sum(axis=-1)


def collateralized_exposure(value, lagged_value, threshold=0.0):
    """Exposure under a two-way collateral agreement with a cure period (Hull Example 24.4).

    Collateral held by each side is set from the portfolio value one cure period earlier:
    received C_r = max(V_lag − θ, 0), posted C_p = max(−V_lag − θ, 0). Exposure is the
    uncollateralised positive value plus any excess collateral posted:
    max(V − C_r, 0) + max(C_p − max(−V, 0), 0). Hull's four cases give 5, 0, 0, 5.
    """
    if threshold < 0.0:
        raise ValueError("threshold must be >= 0")
    value = np.asarray(value, dtype=float)
    lagged = np.asarray(lagged_value, dtype=float)
    received = np.maximum(lagged - threshold, 0.0)
    posted = np.maximum(-lagged - threshold, 0.0)
    return np.maximum(value - received, 0.0) + np.maximum(posted - np.maximum(-value, 0.0), 0.0)


def cva_single_payoff(no_default_value, recovery, default_probs):
    """CVA of one uncollateralised derivative paying off at T: (1−R) f_nd Σ q_i (Hull eq. 24.5)."""
    if not 0.0 <= recovery < 1.0:
        raise ValueError("recovery must lie in [0, 1)")
    return float((1.0 - recovery) * no_default_value * np.sum(np.asarray(default_probs, dtype=float)))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_xva.py`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/xva.py johnhull/hullkit/tests/test_xva.py
git commit -m "feat(hullkit): add netting, collateral and spread-implied CVA helpers"
```

### Task 6: `MODEL_INDEX.md` rows and guard tests

**Files:**
- Modify: `johnhull/MODEL_INDEX.md` §6 (after the `XVA exposures` row)
- Test: `johnhull/hullkit/tests/test_model_index.py`, `test_docstrings.py` (existing)

- [ ] **Step 1: Run the guards to see them fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_model_index.py johnhull/hullkit/tests/test_docstrings.py`
Expected: 4 failed (`hullkit.cds`, `hullkit.credit_curve`, `hullkit.credit_metrics`, `hullkit.credit_portfolio` missing from MODEL_INDEX.md)

- [ ] **Step 2: Add the rows**

```markdown
| Piecewise hazard curves; bond-price and spread bootstraps | Hull §24.4 (Examples 24.1, 24.2) | `hullkit.credit_curve:HazardCurve`, `hullkit.credit_curve:average_hazards_from_spreads`, `hullkit.credit_curve:forward_hazards_from_average`, `hullkit.credit_curve:bond_price_from_yield`, `hullkit.credit_curve:risk_free_bond_price`, `hullkit.credit_curve:forward_risk_free_value`, `hullkit.credit_curve:expected_default_loss_pv`, `hullkit.credit_curve:bootstrap_from_bonds`, `hullkit.credit_curve:BondBootstrapResult` | `test_credit_curve.py` | vol 28 | Ex 24.1 average→forward 3.5/3.75%; Ex 24.2 λ=2.46/3.48/3.74%, loss PV 1.50/3.53/5.61 |
| Single-name CDS legs, MTM, binary, fixed coupon/upfront, forward, option | Hull §25.2–25.5 (Tables 25.1–25.5, Example 25.1); Hull & White (2003) | `hullkit.cds:CDSLegs`, `hullkit.cds:cds_legs`, `hullkit.cds:cds_par_spread`, `hullkit.cds:cds_risky_duration`, `hullkit.cds:cds_mtm`, `hullkit.cds:binary_cds_spread`, `hullkit.cds:implied_hazard`, `hullkit.cds:bootstrap_from_cds`, `hullkit.cds:actual360_to_actual_actual`, `hullkit.cds:fixed_coupon_price`, `hullkit.cds:upfront_payment`, `hullkit.cds:cds_forward_spread`, `hullkit.cds:cds_option` | `test_cds.py` | vol 28 | 4.0728s/0.0422s/0.0506 → 123 bp; MTM 0.0111; binary 205 bp; Ex 25.1 λ=0.5717%, D=4.447, P=100.27; option parity |
| Synthetic CDO / kth-to-default by one-factor copula quadrature; compound & base correlation; double-t; ASB recursion | Hull §25.6–25.11 (Examples 25.2, 25.3, Tables 25.6–25.8); Andersen–Sidenius–Basu (2003); Hull & White (2004) | `hullkit.credit_portfolio:gauss_hermite_factor`, `hullkit.credit_portfolio:conditional_default_prob`, `hullkit.credit_portfolio:binomial_pmf`, `hullkit.credit_portfolio:heterogeneous_default_pmf`, `hullkit.credit_portfolio:tranche_principal_by_defaults`, `hullkit.credit_portfolio:TrancheValuation`, `hullkit.credit_portfolio:cdo_tranche_valuation`, `hullkit.credit_portfolio:cdo_tranche_spread`, `hullkit.credit_portfolio:cdo_upfront`, `hullkit.credit_portfolio:KthToDefaultValuation`, `hullkit.credit_portfolio:kth_to_default_valuation`, `hullkit.credit_portfolio:kth_to_default_spread`, `hullkit.credit_portfolio:compound_correlation`, `hullkit.credit_portfolio:base_correlations`, `hullkit.credit_portfolio:BaseCorrelationResult`, `hullkit.credit_portfolio:expected_loss_curve`, `hullkit.credit_portfolio:double_t_threshold`, `hullkit.credit_portfolio:double_t_conditional_prob`, `hullkit.credit_portfolio:double_t_factor_quadrature` | `test_credit_portfolio.py` | vol 28 | Ex 25.2 A/B/C=4.2846/0.0187/0.1496 → 348 bp incl. Table 25.7 columns; Ex 25.3 153 bp; Table 25.8 compound 17.7/7.8/14.0/18.2/23.3%, base 17.7/28.4/36.5/43.2/60.5%; loss conservation; ν→∞ Gaussian limit; ASB = binomial |
| CreditMetrics rating-transition credit VaR | Hull §24.9 (Table 24.4) | `hullkit.credit_metrics:TransitionMatrix`, `hullkit.credit_metrics:rating_thresholds`, `hullkit.credit_metrics:migrate`, `hullkit.credit_metrics:simulate_rating_migrations`, `hullkit.credit_metrics:credit_loss_distribution`, `hullkit.credit_metrics:credit_var`, `hullkit.credit_metrics:expected_loss` | `test_credit_metrics.py` | vol 28 | Thresholds 1.2719/2.4089/2.8070 and −3.7190/−3.0618/−1.7866, BBB default > 2.9290; default frequency within binomial SE; ρ fattens the tail |
| Netting, collateral (cure period) and spread-implied CVA | Hull §24.7 (Example 24.4, eq. 24.5) | `hullkit.xva:default_probs_from_spreads`, `hullkit.xva:netting_set_exposure`, `hullkit.xva:collateralized_exposure`, `hullkit.xva:cva_single_payoff` | `test_xva.py` | vol 28 | 40 → 15 with netting; Ex 24.4 exposures 5/0/0/5; eq. 24.5 equals the general CVA with EE = f_nd e^{rt} |
```

Also update the `xva` row's Notebook column from `vol 16, 17` to `vol 16, 17, 28`.

- [ ] **Step 3: Run the guards and the whole hullkit suite**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests`
Expected: all passed (previous 794 + ~38 new), 0 failed

- [ ] **Step 4: Commit**

```bash
git add johnhull/MODEL_INDEX.md
git commit -m "docs(johnhull): index the credit-desk modules in MODEL_INDEX"
```

### Task 7: `frontier_reference.volume28_reference` and contract tests

**Files:**
- Modify: `johnhull/hullkit/src/hullkit/frontier_reference.py` (docstring `21--27` → `21--28`; import the new modules; `FrontierReference.__post_init__` range `(21, 29)` and message `[21, 28]`; add `volume28_reference`; `_BUILDERS[28]`; `build_frontier_reference` message `[21, 28]`)
- Modify: `johnhull/hullkit/tests/test_frontier_reference.py` (docstring; fixture `range(21, 29)`; `test_dispatcher_rejects...` match `\[21, 28\]`; `test_fixed_seed...` `range(21, 29)`; add the vol 28 parametrize entry and identity tests)

**Interfaces:**
- Consumes: Tasks 1–5 APIs.
- Produces: `volume28_reference(*, seed: int = 20260746) -> FrontierReference` whose `arrays`/`metrics` keys are exactly the ones listed in the `UNITS_BY_VOLUME[28]` map of Task 8 (keep the two lists in sync — the artifact builder raises on any mismatch).

- [ ] **Step 1: Add the failing contract tests**

Add to the parametrize list in `test_reference_contract_is_serialization_ready`:

```python
        (
            28,
            {
                "bond_bootstrap_hazard",
                "hull_bond_bootstrap_hazard",
                "cds_payment_pv",
                "cds_accrual_pv",
                "cds_payoff_pv",
                "cds_mtm_seller",
                "tranche_expected_principal",
                "tranche_spread_vs_rho",
                "kth_spread",
                "kth_conditional_cumulative_prob",
                "compound_correlation",
                "base_correlation",
                "el_curve_value",
                "double_t_spread",
                "transition_matrix",
                "threshold_bbb",
                "credit_loss_by_case",
                "collateral_case_exposure",
                "cva_default_prob",
            },
            {
                "cds_par_spread_bp",
                "cds_mtm_seller_150bp",
                "fixed_coupon_price",
                "cdo_mezz_spread_bp",
                "kth3_spread_bp",
                "base_correlation_max_reprice_error",
                "double_t_limit_gap_bp",
                "heterogeneous_binomial_gap",
                "cva_special_case",
            },
        ),
```

And new tests at the end of the file:

```python
# --- vol 28 credit desk -------------------------------------------------


def test_volume28_reproduces_hull_pins(references: dict[int, frontier_reference.FrontierReference]) -> None:
    reference = references[28]
    m, a = reference.metrics, reference.arrays
    assert m["cds_par_spread_bp"] == pytest.approx(123.0, abs=0.5)
    assert m["cds_mtm_seller_150bp"] == pytest.approx(0.0111, abs=1e-4)
    assert m["fixed_coupon_price"] == pytest.approx(100.27, abs=0.01)
    assert m["cdo_mezz_spread_bp"] == pytest.approx(348.0, abs=1.0)
    assert m["kth3_spread_bp"] == pytest.approx(153.0, abs=1.0)
    np.testing.assert_allclose(a["bond_bootstrap_hazard"], a["hull_bond_bootstrap_hazard"], atol=2e-4)
    np.testing.assert_allclose(a["compound_correlation"], a["hull_compound_correlation"], atol=0.01)
    np.testing.assert_allclose(a["base_correlation"], a["hull_base_correlation"], atol=0.01)
    np.testing.assert_allclose(a["collateral_case_exposure"], a["hull_collateral_case_exposure"], atol=1e-12)
    assert m["base_correlation_max_reprice_error"] < 1e-6
    assert m["double_t_limit_gap_bp"] < 0.5
    assert m["heterogeneous_binomial_gap"] < 1e-12


def test_volume28_identities_are_recomputable(references: dict[int, frontier_reference.FrontierReference]) -> None:
    reference = references[28]
    m, a = reference.metrics, reference.arrays
    spread = a["cds_payoff_pv"].sum() / (a["cds_payment_pv"].sum() + a["cds_accrual_pv"].sum())
    assert spread * 1e4 == pytest.approx(m["cds_par_spread_bp"], abs=1e-9)
    weights = a["factor_weight"]
    assert weights @ a["tranche_protection_by_factor"] == pytest.approx(m["cdo_mezz_protection"], abs=1e-12)
    widths = a["capital_structure_detach"] - a["capital_structure_attach"]
    assert widths @ a["capital_structure_expected_loss"] == pytest.approx(m["portfolio_expected_loss"], abs=1e-10)
    assert np.all(np.diff(a["kth_spread"]) < 0.0)
    assert np.all(np.diff(a["el_curve_value"]) > 0.0) and np.all(np.diff(a["el_curve_value"], n=2) < 0.0)
    assert m["netting_exposure"] == pytest.approx(15.0) and m["gross_exposure"] == pytest.approx(40.0)
    assert m["credit_var_correlated"] > m["credit_var_independent"]


def test_volume28_reference_is_deterministic() -> None:
    first = frontier_reference.volume28_reference()
    second = frontier_reference.volume28_reference()
    for name in first.arrays:
        np.testing.assert_array_equal(first.arrays[name], second.arrays[name])
    assert first.metrics == second.metrics
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_frontier_reference.py -k "28 or dispatcher"`
Expected: FAIL (`ValueError: frontier reference volume must lie in [21, 27]`)

- [ ] **Step 3: Implement `volume28_reference`**

Add `cds, credit_curve, credit_metrics, credit_portfolio, xva` to the module's relative import block, change the range/messages, and insert before `_BUILDERS`:

```python
def volume28_reference(*, seed: int = 20260746) -> FrontierReference:
    """Build the Hull Ch.24–25 credit-desk reference (vol 28).

    Every block reproduces a printed Hull 11e example with the tested
    :mod:`hullkit` credit APIs: the Example 24.1/24.2 hazard bootstraps, the
    Table 25.2–25.4 CDS legs and mark-to-market, the Example 25.1 fixed-coupon
    price, Black-type CDS options, the Example 25.2 mezzanine CDO by
    Gauss–Hermite quadrature, the Example 25.3 third-to-default swap, the
    Table 25.6 → 25.8 compound/base correlations, the double-t and
    heterogeneous variants, a CreditMetrics migration simulation from
    Table 24.4, and the §24.7 netting/collateral/CVA rules. Only the
    CreditMetrics block draws random numbers (fixed ``seed``).
    """
    recovery = 0.4

    # --- §24.4: spreads → hazards (Ex 24.1) and bond-price bootstrap (Ex 24.2) ---
    spread_tenor = np.array([1.0, 2.0, 3.0])
    yield_spread = np.array([0.0150, 0.0180, 0.0195])
    average_hazard = credit_curve.average_hazards_from_spreads(yield_spread, recovery)
    forward_curve = credit_curve.forward_hazards_from_average(spread_tenor, average_hazard)
    bond_yield = np.array([0.065, 0.068, 0.0695])
    bond_price = np.array([credit_curve.bond_price_from_yield(100.0, 0.08, float(T), float(y)) for T, y in zip(spread_tenor, bond_yield, strict=True)])
    bootstrap = credit_curve.bootstrap_from_bonds(bond_price, 0.08, spread_tenor, r=0.05, recovery=recovery)

    # --- §25.2: Tables 25.1–25.4 (λ = 2%, R = 40%, r = 5%, annual) ---
    cds_r, cds_hazard, cds_maturity = 0.05, 0.02, 5.0
    cds_year = np.arange(1.0, 6.0)
    cds_survival = np.exp(-cds_hazard * cds_year)
    cds_default_prob = -np.diff(np.concatenate([[1.0], cds_survival]))
    cds_discount_end = np.exp(-cds_r * cds_year)
    cds_discount_mid = np.exp(-cds_r * (cds_year - 0.5))
    cds_payment_pv = cds_survival * cds_discount_end
    cds_accrual_pv = 0.5 * cds_default_prob * cds_discount_mid
    cds_payoff_pv = (1.0 - recovery) * cds_default_prob * cds_discount_mid
    legs = cds.cds_legs(cds_hazard, recovery, cds_r, cds_maturity, freq=1)
    cds_contract_spread_grid = np.linspace(0.0, 0.03, 61)
    cds_mtm_seller = np.array([cds.cds_mtm(float(s), cds_hazard, recovery, cds_r, cds_maturity) for s in cds_contract_spread_grid])
    implied_100bp = cds.implied_hazard(0.0100, recovery, cds_r, cds_maturity)
    binary_spread = cds.binary_cds_spread(cds_hazard, cds_r, cds_maturity)
    cds_market_tenor = np.array([1.0, 3.0, 5.0, 7.0])
    cds_market_spread = np.array([0.0060, 0.0100, 0.0140, 0.0160])
    cds_curve = cds.bootstrap_from_cds(cds_market_tenor, cds_market_spread, recovery, cds_r, freq=4)
    cds_bootstrap_repriced_spread = np.array([cds.cds_par_spread(cds_curve, recovery, cds_r, float(T), freq=4) for T in cds_market_tenor])

    # --- §25.4: Example 25.1 fixed coupon / upfront ---
    index_spread = cds.actual360_to_actual_actual(0.0034)
    index_coupon = cds.actual360_to_actual_actual(0.0040)
    fixed_hazard = cds.implied_hazard(index_spread, recovery, 0.04, 5.0, freq=4)
    fixed_duration = cds.cds_risky_duration(fixed_hazard, recovery, 0.04, 5.0, freq=4)
    fixed_price = cds.fixed_coupon_price(index_spread, index_coupon, fixed_duration)
    index_quote_grid = np.linspace(10.0, 120.0, 45)  # bp, actual/360
    fixed_coupon_price_grid = np.empty_like(index_quote_grid)
    for i, quote_bp in enumerate(index_quote_grid):
        quote = cds.actual360_to_actual_actual(float(quote_bp) * 1e-4)
        duration = cds.cds_risky_duration(cds.implied_hazard(quote, recovery, 0.04, 5.0, freq=4), recovery, 0.04, 5.0, freq=4)
        fixed_coupon_price_grid[i] = cds.fixed_coupon_price(quote, index_coupon, duration)

    # --- §25.5: forward spread and Black-type options ---
    option_curve = credit_curve.HazardCurve((1.0, 6.0), (0.02, 0.035))
    option_forward = cds.cds_forward_spread(option_curve, recovery, cds_r, start=1.0, maturity=6.0, freq=4)
    option_annuity = cds.cds_legs(option_curve, recovery, cds_r, 6.0, freq=4, start=1.0).risky_duration
    option_sigma, option_expiry = 0.6, 1.0
    option_strike_grid = np.linspace(0.5, 1.5, 41) * option_forward
    payer_value = np.array([cds.cds_option(option_forward, float(k), option_sigma, option_expiry, option_annuity, "payer") for k in option_strike_grid])
    receiver_value = np.array([cds.cds_option(option_forward, float(k), option_sigma, option_expiry, option_annuity, "receiver") for k in option_strike_grid])

    # --- §25.10: Example 25.2 mezzanine tranche ---
    cdo_r, cdo_maturity, n_names = 0.035, 5.0, 125
    cdo_hazard = cds.implied_hazard(0.0050, recovery, cdo_r, cdo_maturity, freq=4)
    mezz = credit_portfolio.cdo_tranche_valuation(cdo_hazard, recovery, cdo_r, cdo_maturity, 0.03, 0.06, n_names, 0.15)
    rho_grid = np.linspace(0.02, 0.6, 30)
    standard_bounds = np.array([0.0, 0.03, 0.06, 0.09, 0.12, 0.22, 1.0])
    capital_structure_attach, capital_structure_detach = standard_bounds[:-1], standard_bounds[1:]
    tranche_names = np.array(["0-3%", "3-6%", "6-9%", "9-12%", "12-22%", "22-100%"])
    tranche_spread_vs_rho = np.array(
        [[credit_portfolio.cdo_tranche_spread(cdo_hazard, recovery, cdo_r, cdo_maturity, float(lo), float(hi), n_names, float(rho)) for lo, hi in zip(capital_structure_attach, capital_structure_detach, strict=True)] for rho in rho_grid]
    )
    capital_structure_expected_loss = np.array([credit_portfolio.cdo_tranche_valuation(cdo_hazard, recovery, cdo_r, cdo_maturity, float(lo), float(hi), n_names, 0.15).protection for lo, hi in zip(capital_structure_attach, capital_structure_detach, strict=True)])
    portfolio_expected_loss = credit_portfolio.cdo_tranche_valuation(cdo_hazard, recovery, cdo_r, cdo_maturity, 0.0, 1.0, n_names, 0.15).protection

    # --- §25.10: Example 25.3 third-to-default ---
    kth_order = np.arange(1, 6, dtype=float)
    kth_valuations = [credit_portfolio.kth_to_default_valuation(k, 10, 0.02, recovery, 0.05, 5.0, 0.3, freq=1) for k in range(1, 6)]
    kth_spread = np.array([v.spread for v in kth_valuations])
    third = kth_valuations[2]

    # --- §25.10: Table 25.6 → Table 25.8 implied correlations ---
    itraxx_r = 0.03
    itraxx_hazard = cds.implied_hazard(0.0023, recovery, itraxx_r, 5.0, freq=4)
    market_bounds = np.array([0.0, 0.03, 0.06, 0.09, 0.12, 0.22])
    market_tranche_quote = np.array([0.1034, 41.59e-4, 11.95e-4, 5.60e-4, 2.00e-4])
    implied = credit_portfolio.base_correlations(market_tranche_quote, market_bounds, itraxx_hazard, recovery, itraxx_r, 5.0, n_names)
    repriced_quote = np.empty(5)
    for i, (lo, hi, rho) in enumerate(zip(implied.attachments, implied.detachments, implied.compound, strict=True)):
        valuation = credit_portfolio.cdo_tranche_valuation(itraxx_hazard, recovery, itraxx_r, 5.0, float(lo), float(hi), n_names, float(rho))
        repriced_quote[i] = valuation.upfront(0.05) if i == 0 else valuation.spread
    el_curve_x = implied.detachments.copy()
    el_curve_value = credit_portfolio.expected_loss_curve(el_curve_x, implied.base, itraxx_hazard, recovery, itraxx_r, 5.0, n_names)
    hull_compound_correlation = np.array([0.177, 0.078, 0.140, 0.182, 0.233])
    hull_base_correlation = np.array([0.177, 0.284, 0.365, 0.432, 0.605])

    # --- §25.11: double-t copula and heterogeneous recursion ---
    double_t_nu_grid = np.array([3.0, 4.0, 6.0, 10.0, 30.0, 1e6])
    double_t_spread = np.array([credit_portfolio.cdo_tranche_spread(cdo_hazard, recovery, cdo_r, cdo_maturity, 0.03, 0.06, n_names, 0.15, copula="double_t", nu=float(nu)) for nu in double_t_nu_grid])
    gaussian_mezz_spread = mezz.spread
    asb_probe_prob = np.full(10, 0.07)
    asb_probe_pmf = credit_portfolio.heterogeneous_default_pmf(asb_probe_prob)
    binomial_probe = credit_portfolio.binomial_pmf(10, 0.07)
    heterogeneous_binomial_gap = float(np.max(np.abs(asb_probe_pmf - binomial_probe)))
    heterogeneous_spread_gap = float(abs(credit_portfolio.cdo_tranche_valuation(np.full(n_names, cdo_hazard), recovery, cdo_r, cdo_maturity, 0.03, 0.06, n_names, 0.15).spread - gaussian_mezz_spread))

    # --- §24.9: CreditMetrics from Table 24.4 ---
    matrix = credit_metrics.TransitionMatrix.from_percent(credit_metrics.HULL_TABLE_24_4)
    threshold_aaa = credit_metrics.rating_thresholds(matrix, "AAA")
    threshold_bbb = credit_metrics.rating_thresholds(matrix, "BBB")
    obligors = ["A"] * 20 + ["BBB"] * 40 + ["BB"] * 25 + ["B"] * 15
    exposures = np.full(len(obligors), 1.0)
    n_sims = 5000
    rng_independent = np.random.default_rng(seed)
    rng_correlated = np.random.default_rng(seed)
    migrations_independent = credit_metrics.simulate_rating_migrations(matrix, obligors, 0.0, n_sims, rng_independent)
    migrations_correlated = credit_metrics.simulate_rating_migrations(matrix, obligors, 0.2, n_sims, rng_correlated)
    credit_loss_by_case = np.vstack(
        [
            credit_metrics.credit_loss_distribution(migrations_independent, exposures, recovery),
            credit_metrics.credit_loss_distribution(migrations_correlated, exposures, recovery),
        ]
    )
    credit_loss_names = np.array(["independent", "rho=0.2"])
    credit_var_by_case = np.array([credit_metrics.credit_var(row, 0.999) for row in credit_loss_by_case])
    expected_loss_by_case = np.array([credit_metrics.expected_loss(row) for row in credit_loss_by_case])

    # --- §24.7: netting, collateral, spread-implied CVA ---
    netting_trade_value = np.array([10.0, 30.0, -25.0])
    netting_exposure = float(xva.netting_set_exposure(netting_trade_value))
    gross_exposure = float(xva.netting_set_exposure(netting_trade_value, netting=False))
    collateral_case_value = np.array([50.0, 50.0, -50.0, -50.0])
    collateral_case_lagged = np.array([45.0, 55.0, -45.0, -55.0])
    collateral_case_exposure = xva.collateralized_exposure(collateral_case_value, collateral_case_lagged)
    cva_r, cva_T, cva_f_nd, cva_hazard = 0.05, 2.0, 7.0, 0.03
    cva_grid_time = np.linspace(0.0, cva_T, 2001)
    cva_spread_term = np.full(cva_grid_time.size - 1, cva_hazard * (1.0 - recovery))
    cva_default_prob = xva.default_probs_from_spreads(cva_grid_time[1:], cva_spread_term, recovery)
    cva_special_case = xva.cva_single_payoff(cva_f_nd, recovery, cva_default_prob)
    cva_general_equivalent = xva.cva(cva_grid_time, cva_f_nd * np.exp(cva_r * cva_grid_time), cva_hazard, recovery, cva_r)

    arrays: ArrayMap = {
        "spread_tenor": spread_tenor,
        "yield_spread": yield_spread,
        "average_hazard": np.asarray(average_hazard),
        "forward_hazard": np.asarray(forward_curve.hazards),
        "bond_maturity_label": np.array(["1y", "2y", "3y"]),
        "bond_price": bond_price,
        "bond_risk_free_price": np.asarray(bootstrap.risk_free_prices),
        "bond_expected_loss_pv": np.asarray(bootstrap.expected_loss_pv),
        "bond_bootstrap_hazard": np.asarray(bootstrap.curve.hazards),
        "hull_bond_bootstrap_hazard": np.array([0.0246, 0.0348, 0.0374]),
        "cds_year": cds_year,
        "cds_year_label": np.array(["1", "2", "3", "4", "5"]),
        "cds_survival": cds_survival,
        "cds_default_prob": cds_default_prob,
        "cds_discount_end": cds_discount_end,
        "cds_discount_mid": cds_discount_mid,
        "cds_payment_pv": cds_payment_pv,
        "cds_accrual_pv": cds_accrual_pv,
        "cds_payoff_pv": cds_payoff_pv,
        "cds_contract_spread_grid": cds_contract_spread_grid,
        "cds_mtm_seller": cds_mtm_seller,
        "cds_market_tenor": cds_market_tenor,
        "cds_market_spread": cds_market_spread,
        "cds_bootstrap_hazard": np.asarray(cds_curve.hazards),
        "cds_bootstrap_repriced_spread": cds_bootstrap_repriced_spread,
        "index_quote_grid": index_quote_grid,
        "fixed_coupon_price_grid": fixed_coupon_price_grid,
        "option_strike_grid": option_strike_grid,
        "payer_value": payer_value,
        "receiver_value": receiver_value,
        "tranche_payment_time": mezz.payment_times,
        "factor_node": mezz.factor_nodes,
        "factor_weight": mezz.factor_weights,
        "tranche_expected_principal": mezz.expected_principal,
        "tranche_annuity_by_factor": mezz.annuity_by_factor,
        "tranche_accrual_by_factor": mezz.accrual_by_factor,
        "tranche_protection_by_factor": mezz.protection_by_factor,
        "rho_grid": rho_grid,
        "tranche_names": tranche_names,
        "capital_structure_attach": capital_structure_attach,
        "capital_structure_detach": capital_structure_detach,
        "tranche_spread_vs_rho": tranche_spread_vs_rho,
        "capital_structure_expected_loss": capital_structure_expected_loss,
        "kth_order": kth_order,
        "kth_spread": kth_spread,
        "kth_factor_node": third.factor_nodes,
        "kth_factor_weight": third.factor_weights,
        "kth_conditional_cumulative_prob": third.cumulative_prob,
        "kth_payoff_by_factor": third.payoff_by_factor,
        "kth_annuity_by_factor": third.annuity_by_factor,
        "kth_accrual_by_factor": third.accrual_by_factor,
        "market_tranche_label": np.array(["0-3%", "3-6%", "6-9%", "9-12%", "12-22%"]),
        "market_tranche_attach": implied.attachments,
        "market_tranche_detach": implied.detachments,
        "market_tranche_quote": market_tranche_quote,
        "repriced_quote": repriced_quote,
        "compound_correlation": implied.compound,
        "base_correlation": implied.base,
        "hull_compound_correlation": hull_compound_correlation,
        "hull_base_correlation": hull_base_correlation,
        "tranche_expected_loss": implied.tranche_expected_loss,
        "el_curve_x": el_curve_x,
        "el_curve_value": el_curve_value,
        "double_t_nu_grid": double_t_nu_grid,
        "double_t_spread": double_t_spread,
        "asb_probe_prob": asb_probe_prob,
        "asb_probe_pmf": asb_probe_pmf,
        "transition_matrix": matrix.probabilities,
        "rating_names": np.array(matrix.ratings),
        "threshold_index": np.arange(1.0, 8.0),
        "threshold_aaa": threshold_aaa,
        "threshold_bbb": threshold_bbb,
        "hull_threshold_aaa": np.array([1.2719, 2.4089, 2.8070]),
        "hull_threshold_bbb": np.array([-3.7190, -3.0618, -1.7866]),
        "credit_loss_names": credit_loss_names,
        "credit_loss_by_case": credit_loss_by_case,
        "credit_var_by_case": credit_var_by_case,
        "expected_loss_by_case": expected_loss_by_case,
        "netting_trade_value": netting_trade_value,
        "collateral_case_label": np.array(["50/45", "50/55", "-50/-45", "-50/-55"]),
        "collateral_case_value": collateral_case_value,
        "collateral_case_lagged": collateral_case_lagged,
        "collateral_case_exposure": np.asarray(collateral_case_exposure),
        "hull_collateral_case_exposure": np.array([5.0, 0.0, 0.0, 5.0]),
        "cva_grid_time": cva_grid_time,
        "cva_default_prob": cva_default_prob,
    }
    metrics: dict[str, Scalar] = {
        "recovery": recovery,
        "bond_bootstrap_hazard_1": float(bootstrap.curve.hazards[0]),
        "bond_bootstrap_hazard_2": float(bootstrap.curve.hazards[1]),
        "bond_bootstrap_hazard_3": float(bootstrap.curve.hazards[2]),
        "cds_hazard": cds_hazard,
        "cds_rate": cds_r,
        "cds_par_spread_bp": float(legs.par_spread * 1e4),
        "cds_risky_duration": float(legs.risky_duration),
        "cds_protection_pv": float(legs.protection),
        "cds_mtm_seller_150bp": float(cds.cds_mtm(0.015, cds_hazard, recovery, cds_r, cds_maturity)),
        "cds_implied_hazard_100bp": float(implied_100bp),
        "binary_cds_spread_bp": float(binary_spread * 1e4),
        "cds_bootstrap_max_reprice_error": float(np.max(np.abs(cds_bootstrap_repriced_spread - cds_market_spread))),
        "fixed_coupon_spread": float(index_spread),
        "fixed_coupon_coupon": float(index_coupon),
        "fixed_coupon_hazard": float(fixed_hazard),
        "fixed_coupon_duration": float(fixed_duration),
        "fixed_coupon_price": float(fixed_price),
        "option_forward_spread": float(option_forward),
        "option_risky_annuity": float(option_annuity),
        "option_sigma": option_sigma,
        "option_expiry": option_expiry,
        "cdo_index_hazard": float(cdo_hazard),
        "cdo_rate": cdo_r,
        "cdo_rho": 0.15,
        "cdo_mezz_annuity": mezz.annuity,
        "cdo_mezz_accrual": mezz.accrual,
        "cdo_mezz_protection": mezz.protection,
        "cdo_mezz_spread_bp": float(mezz.spread * 1e4),
        "portfolio_expected_loss": float(portfolio_expected_loss),
        "kth3_spread_bp": float(third.spread * 1e4),
        "kth3_payoff": third.payoff,
        "kth3_annuity": third.annuity,
        "kth3_accrual": third.accrual,
        "kth_rate": 0.05,
        "itraxx_hazard": float(itraxx_hazard),
        "itraxx_rate": itraxx_r,
        "base_correlation_max_reprice_error": float(np.max(np.abs(repriced_quote - market_tranche_quote))),
        "gaussian_mezz_spread": float(gaussian_mezz_spread),
        "double_t_limit_gap_bp": float(abs(double_t_spread[-1] - gaussian_mezz_spread) * 1e4),
        "heterogeneous_binomial_gap": heterogeneous_binomial_gap,
        "heterogeneous_spread_gap": heterogeneous_spread_gap,
        "creditmetrics_rho": 0.2,
        "creditmetrics_bbb_default_threshold": float(threshold_bbb[-1]),
        "hull_bbb_default_threshold": 2.9290,
        "credit_var_independent": float(credit_var_by_case[0]),
        "credit_var_correlated": float(credit_var_by_case[1]),
        "netting_exposure": netting_exposure,
        "gross_exposure": gross_exposure,
        "cva_no_default_value": cva_f_nd,
        "cva_rate": cva_r,
        "cva_special_case": float(cva_special_case),
        "cva_general_equivalent": float(cva_general_equivalent),
    }
    return FrontierReference(28, seed, arrays, metrics)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_frontier_reference.py`
Expected: all passed (the vol 28 build takes ~10–20 s because of the Table 25.8 root finds)

- [ ] **Step 5: Commit**

```bash
git add johnhull/hullkit/src/hullkit/frontier_reference.py johnhull/hullkit/tests/test_frontier_reference.py
git commit -m "feat(hullkit): build the vol 28 credit-desk reference payload"
```

### Task 8: acceptance `_volume28`, artifact builder wiring, reference generation

**Files:**
- Modify: `johnhull/scripts/frontier_acceptance.py` (docstring `18--27` → `18--28`; add numpy-only helpers and `_volume28`; `_EVALUATORS[28]`; error text `[18, 28]`)
- Modify: `johnhull/scripts/build_frontier_artifacts.py` (docstring `19--27` → `19--28`; `FILES[28]`; `UNITS_BY_VOLUME[28]`)
- Modify: `johnhull/scripts/verify_frontier_artifacts.py`, `verify_frontier_notebooks.py`, `verify_core_notebooks.py` docstrings (`27` → `28`)
- Modify: `johnhull/release_manifest.json` (vol 28 entry; `portal.figures` 78 → 82)
- Modify: `johnhull/scripts/verify_release.py` (`range(18, 29)`, message `18..28`)
- Create: `johnhull/volumes/28_credit_desk/reference/metrics.json`, `credit_scenarios.npz` (generated)
- Test: `johnhull/hullkit/tests/test_frontier_reference.py` (acceptance independence tests for vol 28)

**Interfaces:**
- Consumes: `volume28_reference` arrays/metrics (Task 7).
- Produces: `frontier_acceptance._volume28(metrics, arrays) -> (checks, negative_results)` with exactly these 17 check names: `cds_par_spread_hull_pin`, `cds_mtm_identity`, `cds_bootstrap_round_trip`, `bond_bootstrap_hull_pin`, `fixed_coupon_price_identity`, `cds_option_parity`, `cdo_mezz_spread_hull_pin`, `expected_principal_monotone`, `capital_structure_loss_conservation`, `kth_to_default_hull_pin_and_ordering`, `implied_correlation_reprices_quotes`, `implied_correlation_hull_pin`, `base_correlation_curve_shape`, `double_t_gaussian_limit`, `heterogeneous_equals_binomial`, `creditmetrics_thresholds_hull_pin`, `netting_collateral_and_cva_special_case`.

- [ ] **Step 1: Add failing acceptance tests to `test_frontier_reference.py`**

```python
# --- vol 28 acceptance gate independence -------------------------------


def _volume28_checks(metrics: dict, arrays: dict) -> dict[str, dict]:
    checks, _ = _frontier_acceptance()._volume28(metrics, arrays)
    return {check["name"]: check for check in checks}


def test_volume28_acceptance_passes_and_recomputes_from_arrays(
    references: dict[int, frontier_reference.FrontierReference],
) -> None:
    reference = references[28]
    arrays = {name: np.asarray(value) for name, value in reference.arrays.items()}
    checks = _volume28_checks(dict(reference.metrics), arrays)
    assert len(checks) == 17
    assert all(check["passed"] for check in checks.values()), [n for n, c in checks.items() if not c["passed"]]
    # tampering with the stored CDO metric is caught because A, B, C are re-integrated
    tampered = dict(reference.metrics)
    tampered["cdo_mezz_spread_bp"] = 300.0
    assert not _volume28_checks(tampered, arrays)["cdo_mezz_spread_hull_pin"]["passed"]
    # tampering with the committed implied correlations is caught by independent repricing
    broken = dict(arrays)
    broken["compound_correlation"] = arrays["compound_correlation"] + 0.05
    assert not _volume28_checks(dict(reference.metrics), broken)["implied_correlation_reprices_quotes"]["passed"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_frontier_reference.py -k volume28_acceptance`
Expected: FAIL with `AttributeError: module 'frontier_acceptance' has no attribute '_volume28'`

- [ ] **Step 3: Implement `_volume28` (numpy/math only, recomputed from the committed arrays)**

Insert before `_EVALUATORS`:

```python
# --- vol 28 helpers: numpy-only normal CDF/quantile and the standard market model ---


def _norm_cdf_np(x: np.ndarray) -> np.ndarray:
    return 0.5 * np.vectorize(math.erfc)(-np.asarray(x, dtype=float) / math.sqrt(2.0))


def _norm_ppf_np(p: float) -> float:
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if float(_norm_cdf_np(np.array(mid))) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _binomial_pmf_np(n: int, p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), 1e-300, 1.0 - 1e-16)[..., None]
    k = np.arange(n + 1, dtype=float)
    log_choose = np.array([math.lgamma(n + 1.0) - math.lgamma(i + 1.0) - math.lgamma(n - i + 1.0) for i in k])
    return np.exp(log_choose + k * np.log(p) + (n - k) * np.log1p(-p))


def _tranche_legs_np(
    hazard: float, recovery: float, r: float, maturity: float, attach: float, detach: float, n: int, rho: float, freq: int = 4, m: int = 60
) -> tuple[float, float, float]:
    """Hull eqs. 25.5–25.12 without hullkit: returns (A, B, C)."""
    x, w = np.polynomial.hermite.hermgauss(m)
    nodes, weights = math.sqrt(2.0) * x, w / math.sqrt(math.pi)
    times = np.arange(1, round(maturity * freq) + 1) / freq
    previous = times - 1.0 / freq
    n_low, n_high = attach * n / (1.0 - recovery), detach * n / (1.0 - recovery)
    m_low, m_high = int(math.floor(n_low)) + 1, int(math.floor(n_high)) + 1
    k = np.arange(n + 1)
    principal = np.where(k < m_low, 1.0, np.where(k >= m_high, 0.0, (detach - k * (1.0 - recovery) / n) / (detach - attach)))
    expected = np.ones((m, times.size + 1))
    for j, t in enumerate(times, start=1):
        q = 1.0 - math.exp(-hazard * t)
        conditional = _norm_cdf_np((_norm_ppf_np(q) - math.sqrt(rho) * nodes) / math.sqrt(1.0 - rho))
        expected[:, j] = _binomial_pmf_np(n, conditional) @ principal
    dt = times - previous
    discount, discount_mid = np.exp(-r * times), np.exp(-r * 0.5 * (times + previous))
    loss = expected[:, :-1] - expected[:, 1:]
    annuity = weights @ (dt * expected[:, 1:] * discount).sum(axis=1)
    accrual = weights @ (0.5 * dt * loss * discount_mid).sum(axis=1)
    protection = weights @ (loss * discount_mid).sum(axis=1)
    return float(annuity), float(accrual), float(protection)


def _volume28(
    metrics: dict[str, Any], arrays: dict[str, np.ndarray]
) -> tuple[list[dict[str, Any]], list[str]]:
    checks: list[dict[str, Any]] = []
    recovery = float(metrics.get("recovery", 0.4))

    # 1. CDS par spread re-summed from the Table 25.2–25.4 columns.
    annuity = float(np.sum(arrays["cds_payment_pv"]))
    accrual = float(np.sum(arrays["cds_accrual_pv"]))
    payoff = float(np.sum(arrays["cds_payoff_pv"]))
    spread_bp = payoff / (annuity + accrual) * 1e4
    _add(checks, "cds_par_spread_hull_pin", spread_bp, "Σpayoff/(Σpayment+Σaccrual) within 0.5 bp of Hull's 123 bp and 1e-9 bp of the stored metric",
         abs(spread_bp - 123.0) <= 0.5 and abs(spread_bp - float(metrics["cds_par_spread_bp"])) <= 1e-9)

    # 2. Mark-to-market identity at 150 bp.
    mtm = (annuity + accrual) * 0.015 - payoff
    grid = np.asarray(arrays["cds_contract_spread_grid"], dtype=float)
    at_150 = float(np.asarray(arrays["cds_mtm_seller"])[np.argmin(np.abs(grid - 0.015))])
    _add(checks, "cds_mtm_identity", mtm, "D·0.015 − protection equals the stored metric and the grid value (1e-10) and Hull's 0.0111 (1e-4)",
         abs(mtm - float(metrics["cds_mtm_seller_150bp"])) <= 1e-10 and abs(mtm - at_150) <= 1e-10 and abs(mtm - 0.0111) <= 1e-4)

    # 3. CDS bootstrap reprices its quotes.
    reprice_error = float(np.max(np.abs(np.asarray(arrays["cds_bootstrap_repriced_spread"]) - np.asarray(arrays["cds_market_spread"]))))
    _add(checks, "cds_bootstrap_round_trip", reprice_error, "max |repriced − market| <= 1e-10", reprice_error <= 1e-10)

    # 4. Bond bootstrap vs Hull Example 24.2.
    hazard_error = float(np.max(np.abs(np.asarray(arrays["bond_bootstrap_hazard"]) - np.asarray(arrays["hull_bond_bootstrap_hazard"]))))
    loss_error = float(np.max(np.abs(np.asarray(arrays["bond_expected_loss_pv"]) - np.array([1.50, 3.53, 5.61]))))
    _add(checks, "bond_bootstrap_hull_pin", max(hazard_error, loss_error), "hazards within 0.0002 of 2.46/3.48/3.74% and loss PVs within 0.01 of 1.50/3.53/5.61",
         hazard_error <= 2e-4 and loss_error <= 0.01)

    # 5. Fixed-coupon price identity (Example 25.1).
    price = 100.0 - 100.0 * float(metrics["fixed_coupon_duration"]) * (float(metrics["fixed_coupon_spread"]) - float(metrics["fixed_coupon_coupon"]))
    _add(checks, "fixed_coupon_price_identity", price, "100 − 100·D·(s−c) equals the stored price (1e-10) and Hull's 100.27 (0.01)",
         abs(price - float(metrics["fixed_coupon_price"])) <= 1e-10 and abs(price - 100.27) <= 0.01)

    # 6. Payer/receiver parity.
    strikes = np.asarray(arrays["option_strike_grid"], dtype=float)
    parity = float(np.max(np.abs(np.asarray(arrays["payer_value"]) - np.asarray(arrays["receiver_value"]) - float(metrics["option_risky_annuity"]) * (float(metrics["option_forward_spread"]) - strikes))))
    _add(checks, "cds_option_parity", parity, "max |payer − receiver − A(F−K)| <= 1e-10", parity <= 1e-10)

    # 7. Mezzanine tranche: re-integrate A, B, C from the committed E_j(F_k) and independently reprice.
    times = np.asarray(arrays["tranche_payment_time"], dtype=float)
    weights = np.asarray(arrays["factor_weight"], dtype=float)
    expected = np.asarray(arrays["tranche_expected_principal"], dtype=float)
    previous = np.concatenate([[0.0], times[:-1]])
    r_cdo = float(metrics["cdo_rate"])
    dt = times - previous
    loss = expected[:, :-1] - expected[:, 1:]
    a_val = float(weights @ (dt * expected[:, 1:] * np.exp(-r_cdo * times)).sum(axis=1))
    b_val = float(weights @ (0.5 * dt * loss * np.exp(-r_cdo * 0.5 * (times + previous))).sum(axis=1))
    c_val = float(weights @ (loss * np.exp(-r_cdo * 0.5 * (times + previous))).sum(axis=1))
    mezz_bp = c_val / (a_val + b_val) * 1e4
    a_ind, b_ind, c_ind = _tranche_legs_np(float(metrics["cdo_index_hazard"]), recovery, r_cdo, 5.0, 0.03, 0.06, 125, float(metrics["cdo_rho"]))
    independent_bp = c_ind / (a_ind + b_ind) * 1e4
    _add(checks, "cdo_mezz_spread_hull_pin", mezz_bp,
         "re-integrated C/(A+B) within 1 bp of Hull's 348 bp, 1e-9 bp of the stored metric, and 1e-6 bp of an independent numpy repricing; A/B/C within 0.002 of 4.2846/0.0187/0.1496",
         abs(mezz_bp - 348.0) <= 1.0 and abs(mezz_bp - float(metrics["cdo_mezz_spread_bp"])) <= 1e-9 and abs(mezz_bp - independent_bp) <= 1e-6
         and abs(a_val - 4.2846) <= 2e-3 and abs(b_val - 0.0187) <= 2e-3 and abs(c_val - 0.1496) <= 2e-3)

    # 8. Expected principal is monotone in time and in the factor.
    nodes = np.asarray(arrays["factor_node"], dtype=float)
    order = np.argsort(nodes)
    time_monotone = float(np.max(np.diff(expected, axis=1)))
    factor_monotone = float(np.min(np.diff(expected[order, -1])))
    _add(checks, "expected_principal_monotone", max(time_monotone, -factor_monotone), "E_j(F) non-increasing in j and non-decreasing in F (1e-12)",
         time_monotone <= 1e-12 and factor_monotone >= -1e-12)

    # 9. Loss conservation across the capital structure.
    widths = np.asarray(arrays["capital_structure_detach"], dtype=float) - np.asarray(arrays["capital_structure_attach"], dtype=float)
    conservation = float(abs(widths @ np.asarray(arrays["capital_structure_expected_loss"], dtype=float) - float(metrics["portfolio_expected_loss"])))
    _add(checks, "capital_structure_loss_conservation", conservation, "Σ width·C_tranche equals the 0–100% expected loss (1e-8)", conservation <= 1e-8)

    # 10. Third-to-default re-summed from the conditional cumulative probabilities; spreads fall with k.
    kth_weights = np.asarray(arrays["kth_factor_weight"], dtype=float)
    cumulative = np.asarray(arrays["kth_conditional_cumulative_prob"], dtype=float)
    kth_times = np.arange(1.0, cumulative.shape[1])
    r_kth = float(metrics["kth_rate"])
    trigger = cumulative[:, 1:] - cumulative[:, :-1]
    disc_mid = np.exp(-r_kth * (kth_times - 0.5))
    kth_payoff = float(kth_weights @ ((1.0 - recovery) * trigger * disc_mid).sum(axis=1))
    kth_annuity = float(kth_weights @ ((1.0 - cumulative[:, 1:]) * np.exp(-r_kth * kth_times)).sum(axis=1))
    kth_accrual = float(kth_weights @ (0.5 * trigger * disc_mid).sum(axis=1))
    kth_bp = kth_payoff / (kth_annuity + kth_accrual) * 1e4
    kth_spreads = np.asarray(arrays["kth_spread"], dtype=float)
    _add(checks, "kth_to_default_hull_pin_and_ordering", kth_bp, "re-summed 3rd-to-default spread within 1 bp of Hull's 153 bp and 1e-9 bp of the metric; spreads strictly decrease in k",
         abs(kth_bp - 153.0) <= 1.0 and abs(kth_bp - float(metrics["kth3_spread_bp"])) <= 1e-9 and bool(np.all(np.diff(kth_spreads) < 0.0)))

    # 11. Compound correlations reprice Table 25.6 (independent numpy pricer).
    attach = np.asarray(arrays["market_tranche_attach"], dtype=float)
    detach = np.asarray(arrays["market_tranche_detach"], dtype=float)
    quotes = np.asarray(arrays["market_tranche_quote"], dtype=float)
    compound = np.asarray(arrays["compound_correlation"], dtype=float)
    hazard_itx, r_itx = float(metrics["itraxx_hazard"]), float(metrics["itraxx_rate"])
    reprice = np.empty(quotes.size)
    for i in range(quotes.size):
        a_i, b_i, c_i = _tranche_legs_np(hazard_itx, recovery, r_itx, 5.0, float(attach[i]), float(detach[i]), 125, float(compound[i]))
        reprice[i] = c_i - 0.05 * (a_i + b_i) if i == 0 else c_i / (a_i + b_i)
    reprice_gap = float(np.max(np.abs(reprice - quotes)))
    _add(checks, "implied_correlation_reprices_quotes", reprice_gap, "independent repricing at the committed compound correlations within 1e-6 of the quotes (0.01 bp / 1e-4 upfront points)", reprice_gap <= 1e-6)

    # 12. Table 25.8 pins.
    compound_gap = float(np.max(np.abs(compound - np.asarray(arrays["hull_compound_correlation"], dtype=float))))
    base_gap = float(np.max(np.abs(np.asarray(arrays["base_correlation"], dtype=float) - np.asarray(arrays["hull_base_correlation"], dtype=float))))
    _add(checks, "implied_correlation_hull_pin", max(compound_gap, base_gap), "compound and base correlations within 1.0 point of Table 25.8", compound_gap <= 0.01 and base_gap <= 0.01)

    # 13. Expected-loss curve shape (increasing at a decreasing rate).
    curve = np.asarray(arrays["el_curve_value"], dtype=float)
    _add(checks, "base_correlation_curve_shape", float(np.max(np.diff(curve, n=2))), "0–X% expected-loss PV increasing with strictly negative second differences",
         bool(np.all(np.diff(curve) > 0.0)) and bool(np.all(np.diff(curve, n=2) < 0.0)))

    # 14. Double-t limit.
    gap_bp = float(abs(np.asarray(arrays["double_t_spread"], dtype=float)[-1] - float(metrics["gaussian_mezz_spread"])) * 1e4)
    _add(checks, "double_t_gaussian_limit", gap_bp, "ν→∞ double-t spread within 0.5 bp of the Gaussian spread", gap_bp <= 0.5)

    # 15. ASB recursion equals the binomial pmf (both recomputed here).
    probe = np.asarray(arrays["asb_probe_prob"], dtype=float)
    recursion = np.zeros(probe.size + 1)
    recursion[0] = 1.0
    for p_i in probe:
        recursion = recursion * (1.0 - p_i) + np.concatenate([[0.0], recursion[:-1]]) * p_i
    binomial = _binomial_pmf_np(probe.size, np.array(probe[0]))
    asb_gap = float(max(np.max(np.abs(recursion - binomial)), np.max(np.abs(recursion - np.asarray(arrays["asb_probe_pmf"], dtype=float)))))
    _add(checks, "heterogeneous_equals_binomial", asb_gap, "recursion pmf equals the binomial pmf and the committed pmf (1e-12)", asb_gap <= 1e-12)

    # 16. CreditMetrics thresholds from the committed matrix; correlation fattens the tail.
    matrix = np.asarray(arrays["transition_matrix"], dtype=float)
    aaa = np.array([_norm_ppf_np(float(p)) for p in np.cumsum(matrix[0])[:3]])
    bbb = np.array([_norm_ppf_np(float(p)) for p in np.cumsum(matrix[3])[:3]])
    bbb_default = _norm_ppf_np(float(np.cumsum(matrix[3])[-2]))
    threshold_gap = float(max(np.max(np.abs(aaa - np.asarray(arrays["hull_threshold_aaa"]))), np.max(np.abs(bbb - np.asarray(arrays["hull_threshold_bbb"]))), abs(bbb_default - 2.9290)))
    losses = np.asarray(arrays["credit_loss_by_case"], dtype=float)
    var_independent, var_correlated = (float(np.quantile(losses[0], 0.999)), float(np.quantile(losses[1], 0.999)))
    _add(checks, "creditmetrics_thresholds_hull_pin", threshold_gap, "thresholds recomputed from Table 24.4 within 0.0002 of Hull; 99.9% credit VaR larger with ρ=0.2 than independent",
         threshold_gap <= 2e-4 and var_correlated > var_independent)

    # 17. Netting, collateral rule, and eq. 24.5.
    trades = np.asarray(arrays["netting_trade_value"], dtype=float)
    netted, gross = max(float(trades.sum()), 0.0), float(np.maximum(trades, 0.0).sum())
    value = np.asarray(arrays["collateral_case_value"], dtype=float)
    lagged = np.asarray(arrays["collateral_case_lagged"], dtype=float)
    exposure = np.maximum(value - np.maximum(lagged, 0.0), 0.0) + np.maximum(np.maximum(-lagged, 0.0) - np.maximum(-value, 0.0), 0.0)
    collateral_gap = float(np.max(np.abs(exposure - np.asarray(arrays["hull_collateral_case_exposure"], dtype=float))))
    cva_special = (1.0 - recovery) * float(metrics["cva_no_default_value"]) * float(np.sum(arrays["cva_default_prob"]))
    cva_gap = abs(cva_special - float(metrics["cva_special_case"]))
    general_gap = abs(float(metrics["cva_general_equivalent"]) - cva_special)
    _add(checks, "netting_collateral_and_cva_special_case", max(collateral_gap, cva_gap, general_gap),
         "netting 15 <= gross 40 (Hull 24.7); Example 24.4 exposures 5/0/0/5; (1−R)f_nd Σq_i equals the stored CVA (1e-12) and the general CVA on a 2000-step grid (1e-5)",
         netted == 15.0 and gross == 40.0 and netted <= gross and collateral_gap <= 1e-12 and cva_gap <= 1e-12 and general_gap <= 1e-5)

    return checks, [
        "Hull Table 24.4 (S&P 1981–2019) and Table 25.6 (Creditex iTraxx quotes, 2007-01-31) are transcribed textbook constants, not downloaded market data.",
        "The Table 25.8 implied correlations match Hull to one decimal place; residual differences reflect DerivaGem's integration grid, not calibration quality.",
        "The double-t copula and ASB recursion are validated only by limits (ν→∞, homogeneous); Hull prints no numeric example for §25.11.",
        "Random recovery / random factor loadings, the implied copula, dynamic models and KMV EDF mappings are out of scope (documentation only).",
        "CDS options use the Black-type market formula; the full Hull–White (2003) knock-out treatment is not implemented.",
    ]
```

Register `28: _volume28` in `_EVALUATORS` and change the error message to `[18, 28]`.

- [ ] **Step 4: Wire the artifact builder**

`FILES[28] = ("28_credit_desk", "metrics.json", "credit_scenarios.npz")` and:

```python
    28: {
        "spread_tenor": "years",
        "yield_spread": "annualized decimal spread",
        "average_hazard": "annualized hazard rate",
        "forward_hazard": "annualized hazard rate",
        "bond_maturity_label": "label",
        "bond_price": "price per 100 face",
        "bond_risk_free_price": "price per 100 face",
        "bond_expected_loss_pv": "PV per 100 face",
        "bond_bootstrap_hazard": "annualized hazard rate",
        "hull_bond_bootstrap_hazard": "annualized hazard rate",
        "cds_year": "years",
        "cds_year_label": "label",
        "cds_survival": "probability",
        "cds_default_prob": "probability",
        "cds_discount_end": "discount factor",
        "cds_discount_mid": "discount factor",
        "cds_payment_pv": "PV per unit spread",
        "cds_accrual_pv": "PV per unit spread",
        "cds_payoff_pv": "PV per unit notional",
        "cds_contract_spread_grid": "annualized decimal spread",
        "cds_mtm_seller": "value per unit notional",
        "cds_market_tenor": "years",
        "cds_market_spread": "annualized decimal spread",
        "cds_bootstrap_hazard": "annualized hazard rate",
        "cds_bootstrap_repriced_spread": "annualized decimal spread",
        "index_quote_grid": "basis points (actual/360)",
        "fixed_coupon_price_grid": "price per 100 notional",
        "option_strike_grid": "annualized decimal spread",
        "payer_value": "value per unit notional",
        "receiver_value": "value per unit notional",
        "tranche_payment_time": "years",
        "factor_node": "standard normal factor",
        "factor_weight": "quadrature weight",
        "tranche_expected_principal": "fraction of tranche principal",
        "tranche_annuity_by_factor": "PV per unit spread",
        "tranche_accrual_by_factor": "PV per unit spread",
        "tranche_protection_by_factor": "PV per unit tranche principal",
        "rho_grid": "copula correlation",
        "tranche_names": "label",
        "capital_structure_attach": "fraction of portfolio principal",
        "capital_structure_detach": "fraction of portfolio principal",
        "tranche_spread_vs_rho": "annualized decimal spread",
        "capital_structure_expected_loss": "PV per unit tranche principal",
        "kth_order": "default order k",
        "kth_spread": "annualized decimal spread",
        "kth_factor_node": "standard normal factor",
        "kth_factor_weight": "quadrature weight",
        "kth_conditional_cumulative_prob": "probability",
        "kth_payoff_by_factor": "PV per unit notional",
        "kth_annuity_by_factor": "PV per unit spread",
        "kth_accrual_by_factor": "PV per unit spread",
        "market_tranche_label": "label",
        "market_tranche_attach": "fraction of portfolio principal",
        "market_tranche_detach": "fraction of portfolio principal",
        "market_tranche_quote": "upfront fraction (equity) or annualized decimal spread",
        "repriced_quote": "upfront fraction (equity) or annualized decimal spread",
        "compound_correlation": "copula correlation",
        "base_correlation": "copula correlation",
        "hull_compound_correlation": "copula correlation",
        "hull_base_correlation": "copula correlation",
        "tranche_expected_loss": "PV per unit tranche principal",
        "el_curve_x": "fraction of portfolio principal",
        "el_curve_value": "PV per unit portfolio principal",
        "double_t_nu_grid": "degrees of freedom",
        "double_t_spread": "annualized decimal spread",
        "asb_probe_prob": "probability",
        "asb_probe_pmf": "probability",
        "transition_matrix": "probability",
        "rating_names": "label",
        "threshold_index": "threshold ordinal",
        "threshold_aaa": "standard normal quantile",
        "threshold_bbb": "standard normal quantile",
        "hull_threshold_aaa": "standard normal quantile",
        "hull_threshold_bbb": "standard normal quantile",
        "credit_loss_names": "label",
        "credit_loss_by_case": "loss per unit exposure",
        "credit_var_by_case": "loss per unit exposure",
        "expected_loss_by_case": "loss per unit exposure",
        "netting_trade_value": "synthetic monetary units",
        "collateral_case_label": "label",
        "collateral_case_value": "synthetic monetary units",
        "collateral_case_lagged": "synthetic monetary units",
        "collateral_case_exposure": "synthetic monetary units",
        "hull_collateral_case_exposure": "synthetic monetary units",
        "cva_grid_time": "years",
        "cva_default_prob": "probability",
    },
```

Manifest entry (append after vol 27, and set `"portal": {"themes": 12, "figures": 82}`):

```json
    {
      "number": 28,
      "slug": "28_credit_desk",
      "notebook": "credit_desk.ipynb",
      "book_name": "28_credit_desk",
      "portal_page": "risk_credit",
      "portal_figures": [
        "cds_leg_pv_by_year",
        "tranche_spread_vs_correlation",
        "base_correlation_skew",
        "creditmetrics_loss_distribution"
      ],
      "semantic_sources": [
        "johnhull/hullkit/src/hullkit/frontier_reference.py",
        "johnhull/hullkit/src/hullkit/credit_curve.py",
        "johnhull/hullkit/src/hullkit/cds.py",
        "johnhull/hullkit/src/hullkit/credit_portfolio.py",
        "johnhull/hullkit/src/hullkit/credit_metrics.py",
        "johnhull/hullkit/src/hullkit/xva.py"
      ],
      "semantic_tests": [
        "johnhull/hullkit/tests/test_frontier_reference.py",
        "johnhull/hullkit/tests/test_credit_curve.py",
        "johnhull/hullkit/tests/test_cds.py",
        "johnhull/hullkit/tests/test_credit_portfolio.py",
        "johnhull/hullkit/tests/test_credit_metrics.py",
        "johnhull/hullkit/tests/test_xva.py"
      ],
      "references": [
        "reference/metrics.json",
        "reference/credit_scenarios.npz"
      ],
      "validation": "VALIDATION.md"
    }
```

`verify_release.py`: `if numbers != list(range(18, 29))` and the message `18..28`.

- [ ] **Step 5: Generate the reference and run the tests**

Run:
```bash
mkdir -p johnhull/volumes/28_credit_desk
uv run --no-sync --package hullkit python johnhull/scripts/build_frontier_artifacts.py --volume 28
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_frontier_reference.py
```
Expected: `Built vol 28: johnhull/volumes/28_credit_desk/reference/metrics.json + ...credit_scenarios.npz`; `acceptance.passed` is `true` in the JSON (check with `python -c "import json;d=json.load(open('johnhull/volumes/28_credit_desk/reference/metrics.json'));print(d['acceptance']['passed'], [c['name'] for c in d['acceptance']['checks'] if not c['passed']])"`); tests pass.

- [ ] **Step 6: Commit**

```bash
git add johnhull/scripts/frontier_acceptance.py johnhull/scripts/build_frontier_artifacts.py johnhull/scripts/verify_frontier_artifacts.py johnhull/scripts/verify_frontier_notebooks.py johnhull/scripts/verify_core_notebooks.py johnhull/scripts/verify_release.py johnhull/release_manifest.json johnhull/volumes/28_credit_desk/reference johnhull/hullkit/tests/test_frontier_reference.py
git commit -m "feat(johnhull): add the vol 28 acceptance gate and reference artifact"
```

### Task 9: `VOLUME_META[28]`, notebook wrapper, executed notebook and VALIDATION.md

**Files:**
- Modify: `johnhull/scripts/build_frontier_notebooks.py` (docstring `18--27` → `18--28`; add `VOLUME_META[28]`)
- Create: `johnhull/volumes/28_credit_desk/build_28_credit_desk_notebook.py`
- Create (generated): `johnhull/volumes/28_credit_desk/credit_desk.ipynb`, `johnhull/volumes/28_credit_desk/VALIDATION.md`
- Create: symlink `johnhull/book/notebooks/28_credit_desk.ipynb -> ../../volumes/28_credit_desk/credit_desk.ipynb`

- [ ] **Step 1: Add `VOLUME_META[28]`**

```python
    28: {
        "title": "Credit Desk — CDS, CDO, Correlation, CreditMetrics",
        "question": "Hull Ch.24–25 の印刷された数値例を、検証済みコードで一つ残らず再現できるか。",
        "focus": "vol.09 が説明文で済ませた節を節単位で埋める。債券価格と CDS 気配からの区分定数ハザード（Ex 24.1/24.2）、Table 25.2–25.4 の CDS レッグと MTM、Ex 25.1 の固定クーポン価格、Black 型 CDS オプション、Gauss–Hermite 求積による合成 CDO（Ex 25.2）と k-th-to-default（Ex 25.3）、Table 25.6 の iTraxx 気配から Table 25.8 のコンパウンド/ベース相関、double-t コピュラと不均質再帰（§25.11）、Table 24.4 の CreditMetrics 閾値と相関付き格付推移 MC、§24.7 のネッティング・担保・式 (24.5)。すべて Hull の離散化（期末払い・期中デフォルト）に合わせ、印刷値に ±許容で固定する。",
        "sections": [
            ("bond_bootstrap_hazard", "債券価格ブートストラップ vs Hull Ex 24.2", "bar:bond_maturity_label:hull_bond_bootstrap_hazard"),
            ("cds_payoff_pv", "CDS レッグの年別 PV（Table 25.3 vs 25.4）", "bar:cds_year_label:cds_accrual_pv"),
            ("cds_mtm_seller", "契約スプレッド別の売り手 MTM（150bp で 0.0111）", "line:cds_contract_spread_grid"),
            ("fixed_coupon_price_grid", "固定クーポン 40bp のアップフロント価格 vs 気配（Ex 25.1）", "line:index_quote_grid"),
            ("payer_value", "CDS オプション payer / receiver（Black 型）", "line2:option_strike_grid:receiver_value"),
            ("tranche_expected_principal", "メザニン期待元本 E_j(F_k)（Table 25.7）", "heatmap"),
            ("tranche_spread_vs_rho", "標準トランシェのブレークイーブンスプレッド vs ρ", "line:rho_grid"),
            ("kth_spread", "k-th-to-default スプレッド（Ex 25.3 は k=3）", "line:kth_order"),
            ("compound_correlation", "Table 25.8：コンパウンド vs ベース相関", "bar:market_tranche_label:base_correlation"),
            ("el_curve_value", "0–X% 期待損失 PV（Figure 25.3）", "line:el_curve_x"),
            ("double_t_spread", "double-t コピュラのメザニンスプレッド vs ν", "line:double_t_nu_grid"),
            ("threshold_aaa", "CreditMetrics 閾値：AAA vs BBB（Table 24.4）", "line2:threshold_index:threshold_bbb"),
            ("credit_loss_by_case", "信用損失分布：独立 vs ρ=0.2", "histrows:credit_loss_names"),
            ("collateral_case_exposure", "担保付きエクスポージャ：Ex 24.4 の 4 ケース", "bar:collateral_case_label:hull_collateral_case_exposure"),
        ],
        "verification": (
            "m = manifest['metrics']\n"
            "spread_bp = data['cds_payoff_pv'].sum() / (data['cds_payment_pv'].sum() + data['cds_accrual_pv'].sum()) * 1e4\n"
            "assert abs(spread_bp - 123.0) <= 0.5 and abs(spread_bp - m['cds_par_spread_bp']) <= 1e-9\n"
            "times = data['tranche_payment_time']; prev = np.concatenate([[0.0], times[:-1]]); w = data['factor_weight']\n"
            "E = data['tranche_expected_principal']; dt = times - prev; r = m['cdo_rate']\n"
            "loss = E[:, :-1] - E[:, 1:]\n"
            "A = w @ (dt * E[:, 1:] * np.exp(-r * times)).sum(axis=1)\n"
            "B = w @ (0.5 * dt * loss * np.exp(-r * 0.5 * (times + prev))).sum(axis=1)\n"
            "C = w @ (loss * np.exp(-r * 0.5 * (times + prev))).sum(axis=1)\n"
            "assert abs(C / (A + B) * 1e4 - 348.0) <= 1.0\n"
            "widths = data['capital_structure_detach'] - data['capital_structure_attach']\n"
            "assert abs(widths @ data['capital_structure_expected_loss'] - m['portfolio_expected_loss']) <= 1e-8\n"
            "assert np.all(np.diff(data['kth_spread']) < 0)\n"
            "assert np.all(np.diff(data['el_curve_value']) > 0) and np.all(np.diff(data['el_curve_value'], n=2) < 0)\n"
            "assert np.max(np.abs(data['compound_correlation'] - data['hull_compound_correlation'])) <= 0.01\n"
            "assert np.max(np.abs(data['base_correlation'] - data['hull_base_correlation'])) <= 0.01\n"
            "assert np.allclose(data['collateral_case_exposure'], [5, 0, 0, 5])\n"
            "print('PASS: 123bp / 348bp / 153bp / Table 25.8 / loss conservation / Ex 24.4 recomputed from the artifact')"
        ),
        "exercises": (
            "## 練習問題\n\n"
            "1. Table 25.2–25.4 の設定で支払いを四半期にしたとき、パースプレッドはどちらへ動くか。`cds_payment_pv` の構造から予想し、理由をアクルーアルの扱いで説明せよ。\n"
            "2. `cds_mtm_seller` の傾きは何に等しいか。150bp の MTM 0.0111 と D=4.1150 から確かめよ。\n"
            "3. Table 25.7 の列 F=−1.0104 で E_20 が 0.5648 まで落ちる理由を、条件付きデフォルト確率 Q(t|F) の式で説明せよ。\n"
            "4. `tranche_spread_vs_rho` でエクイティのスプレッドが ρ とともに下がり、シニアが上がるのはなぜか。`capital_structure_expected_loss` の合計が ρ に依存しないことと整合させよ。\n"
            "5. Table 25.8 でコンパウンド相関はスマイル、ベース相関はスキューになる。ガウシアンコピュラが市場と整合しているなら両者はどうなるはずか。`el_curve_value` の凹性はどの無裁定条件に対応するか。"
        ),
        "citations": "Hull (2022) Options, Futures, and Other Derivatives 11e, Ch.24–25; Vasicek (2002); Li (2000); Andersen, Sidenius & Basu (2003); Hull & White (2004); Hull & White (2003) CDS options.",
        "gate": "G10",
    },
```

- [ ] **Step 2: Wrapper, symlink, build**

`johnhull/volumes/28_credit_desk/build_28_credit_desk_notebook.py`:

```python
"""Build and execute the artifact-only volume 28 credit-desk notebook."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_frontier_notebooks import build_volume

build_volume(28)
```

Run:
```bash
ln -s ../../volumes/28_credit_desk/credit_desk.ipynb johnhull/book/notebooks/28_credit_desk.ipynb
uv run --no-sync --package hullkit python johnhull/volumes/28_credit_desk/build_28_credit_desk_notebook.py
```
Expected: `built johnhull/volumes/28_credit_desk/credit_desk.ipynb`; `VALIDATION.md` generated with `Gate: **PASS**` and 17 PASS rows; no cell error (the verification cell prints `PASS: ...`).

- [ ] **Step 3: Commit**

```bash
git add johnhull/scripts/build_frontier_notebooks.py johnhull/volumes/28_credit_desk johnhull/book/notebooks/28_credit_desk.ipynb
git commit -m "feat(johnhull): add the vol 28 credit-desk notebook"
```

### Task 10: portal figures, book, roadmap, README, VALIDATION, provenance

**Files:**
- Modify: `johnhull/report/report_builder/frontier_figures.py` (docstring; `_vol28_*`; `FRONTIER_BUILDERS`)
- Modify: `johnhull/report/report_builder/figures.py` (4 tuples in the `FIGURES.extend` list, book `risk_credit`)
- Modify: `johnhull/report/tests/test_report_build.py` (`risk_credit` 8 → 12, `FIGURES` 78 → 82)
- Modify: `johnhull/book/_toc.yml`, `johnhull/book/notebooks/00_overview.md`, `johnhull/ROADMAP.md`, `johnhull/README.md`, `johnhull/VALIDATION.md`, `johnhull/docs/DATA_PROVENANCE.md`, `johnhull/CLAUDE.md`

- [ ] **Step 1: Update the report test expectations first (they fail until the figures exist)**

`assert len(figures_for("risk_credit")) == 12` and `assert len(FIGURES) == 82`.

Run: `uv run --no-sync --package hullkit pytest -q johnhull/report/tests/test_report_build.py -k "figures or builds"`
Expected: FAIL (78 ≠ 82)

- [ ] **Step 2: Add the four figure builders**

```python
def _vol28_cds_legs() -> go.Figure:
    data = _load("28_credit_desk", "credit_scenarios.npz")
    metrics = _metrics("28_credit_desk")
    years = data["cds_year_label"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=years, y=data["cds_payment_pv"], name="期待支払い PV (×s)"))
    fig.add_trace(go.Bar(x=years, y=data["cds_accrual_pv"], name="期待アクルーアル PV (×s)"))
    fig.add_trace(go.Bar(x=years, y=data["cds_payoff_pv"], name="期待ペイオフ PV"))
    fig.update_layout(
        title=f"Hull Table 25.2–25.4 — D={metrics['cds_risky_duration']:.4f}, protection={metrics['cds_protection_pv']:.4f}, s={metrics['cds_par_spread_bp']:.0f} bp",
        barmode="group",
        xaxis_title="年",
        yaxis_title="現在価値（元本 1）",
    )
    return fig


def _vol28_tranche_spreads() -> go.Figure:
    data = _load("28_credit_desk", "credit_scenarios.npz")
    rho = data["rho_grid"]
    names = data["tranche_names"].astype(str)
    fig = go.Figure()
    for j, name in enumerate(names):
        fig.add_trace(go.Scatter(x=rho, y=data["tranche_spread_vs_rho"][:, j] * 1e4, mode="lines", name=name))
    fig.update_layout(
        title="標準トランシェのブレークイーブンスプレッド vs コピュラ相関（Ex 25.2 の設定）",
        xaxis_title="ρ",
        yaxis_title="スプレッド (bp/年)",
        yaxis_type="log",
    )
    return fig


def _vol28_base_correlation() -> go.Figure:
    data = _load("28_credit_desk", "credit_scenarios.npz")
    labels = data["market_tranche_label"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=data["compound_correlation"] * 100, name="コンパウンド相関（モデル）"))
    fig.add_trace(go.Bar(x=labels, y=data["base_correlation"] * 100, name="ベース相関（モデル）"))
    fig.add_trace(go.Scatter(x=labels, y=data["hull_compound_correlation"] * 100, mode="markers", marker_symbol="x", marker_size=11, name="Hull Table 25.8 コンパウンド"))
    fig.add_trace(go.Scatter(x=labels, y=data["hull_base_correlation"] * 100, mode="markers", marker_symbol="diamond-open", marker_size=11, name="Hull Table 25.8 ベース"))
    fig.update_layout(title="iTraxx Europe 2007-01-31（Table 25.6）から逆算したインプライド相関", barmode="group", yaxis_title="相関 (%)")
    return fig


def _vol28_credit_loss() -> go.Figure:
    data = _load("28_credit_desk", "credit_scenarios.npz")
    names = data["credit_loss_names"].astype(str)
    fig = go.Figure()
    for row, label, var in zip(data["credit_loss_by_case"], names, data["credit_var_by_case"], strict=True):
        fig.add_trace(go.Histogram(x=row, name=str(label), histnorm="probability density", opacity=0.55))
        fig.add_vline(x=float(var), line_dash="dash", annotation_text=f"99.9% VaR {label}: {var:.1f}")
    fig.update_layout(title="CreditMetrics 損失分布（Table 24.4、100 社、独立 vs ρ=0.2）", barmode="overlay", xaxis_title="損失（エクスポージャ 1/社）", yaxis_title="密度")
    return fig
```

Register in `FRONTIER_BUILDERS`: `"cds_leg_pv_by_year": _vol28_cds_legs, "tranche_spread_vs_correlation": _vol28_tranche_spreads, "base_correlation_skew": _vol28_base_correlation, "creditmetrics_loss_distribution": _vol28_credit_loss`.

Append to the tuple list in `figures.py` (same 5-field shape as the vol 27 entries, book `"risk_credit"`):

```python
    (
        "cds_leg_pv_by_year",
        "risk_credit",
        "CDS レッグの年別 PV（Hull Table 25.2–25.4）",
        "期待支払い・アクルーアル・ペイオフの現在価値を年別に。合計 4.1150s と 0.0506 の比が 123bp。",
        "CDS を『リスキー年金 × スプレッド = 期待損失』に分解して読む。デスクの MTM の骨格。",
    ),
    (
        "tranche_spread_vs_correlation",
        "risk_credit",
        "CDO トランシェスプレッド vs 相関",
        "Ex 25.2 の設定で 6 トランシェのブレークイーブンスプレッドを ρ で動かす。エクイティは下がりシニアは上がる。",
        "相関は損失の期待値を変えずに分布をトランシェ間で動かす。2008 年のシニアの崩れ方。",
    ),
    (
        "base_correlation_skew",
        "risk_credit",
        "コンパウンド相関のスマイルとベース相関のスキュー",
        "iTraxx 2007-01-31 の気配（Table 25.6）から逆算した相関。Hull Table 25.8 の印刷値を重ねる。",
        "ガウシアンコピュラが市場と整合しない証拠。ベース相関で非標準トランシェを補間する実務。",
    ),
    (
        "creditmetrics_loss_distribution",
        "risk_credit",
        "CreditMetrics 損失分布と信用 VaR",
        "Table 24.4 の推移行列と 1 ファクター相関で 100 社の損失を模擬。ρ=0.2 で 99.9% VaR が伸びる。",
        "格下げも損失に数える信用 VaR。規制資本の Vasicek 式との対応。",
    ),
```

- [ ] **Step 3: Docs**

- `book/_toc.yml`: change the last caption to `Hull の先 — インフレ連動・リスク管理デスク・信用デスク（vol 26–28）` and add `      - file: notebooks/28_credit_desk`.
- `book/notebooks/00_overview.md`: after the A5–A8 bullet add `- **信用デスク（vol 28）**: Hull Ch.24–25 の印刷数値例（Ex 24.2、Table 25.2–25.8、Ex 25.2/25.3）を再現する CDS/CDO/相関/CreditMetrics の検証済み実装。`
- `ROADMAP.md`: add a section after the vol 26–27 material:

```markdown
## vol 28 — 信用デスク（Hull Ch.24–25 の節単位の完全実装、2026-09-14）

Design: `docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`

| # | Volume | 内容 | Status |
|---|--------|------|--------|
| 28 | `volumes/28_credit_desk` | 24.4 債券/CDS ブートストラップ、24.7 ネッティング・担保・式 (24.5)、24.9 CreditMetrics、25.2 CDS レッグ/MTM/バイナリ、25.4 固定クーポン、25.5 フォワード/オプション、25.6+25.10 k-th-to-default、25.10 合成 CDO と コンパウンド/ベース相関、25.11 double-t・不均質再帰 | done |

vol 09 の設計書（2026-06-08）で「md/conceptual only」とした項目のうち、Hull 本文に数値例が
あるものをすべて hullkit（`credit_curve` / `cds` / `credit_portfolio` / `credit_metrics` / `xva` 追加分）
に実装し、印刷値に固定した。KMV EDF、ランダム回収率・ファクター負荷、implied copula、
動的モデルは引き続き説明のみ。`done` は integration・恒等式・再現性・教科書ピンの PASS を表し、
市場較正の承認ではない。
```

  Also append to the vol 09 row's Status column: `done（未実装節は vol 28 で実装）`.
- `README.md`: `volumes 18--27` → `18--28`, add `credit desk (Hull Ch.24–25 numeric examples)` to the list of beyond-Hull topics, `make hull-artifacts-check  # rebuild vol. 19–28`, `make hull-notebooks-check` comment `vol 18-28`, spec link line `vol 28 design: docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`.
- `VALIDATION.md`: Gate matrix row `| vol 28 | Hull Ch.24–25 credit desk: bond/CDS bootstraps, CDS legs/MTM/fixed coupon/options, quadrature CDO and kth-to-default, compound/base correlation, double-t/ASB, CreditMetrics, netting/collateral CVA | PASS (tracked release) |`; acceptance table row `| 28 | 17 | PASS | NO |`; Numerical evidence bullet with the observed values (123.0 bp, 347.6 bp, 153.0 bp, Table 25.8 max gap, double-t gap, thresholds); a new section `## 2026-09-14 vol 28 credit-desk run` with the command/result table (hullkit+report tests count, artifact check, notebook check, portal 12 themes / 82 figures, book pages, release check); Negative results bullet (textbook-transcribed constants; §25.11 limits only).
- `docs/DATA_PROVENANCE.md`: section `## Volume 28 credit-desk reference` stating that `metrics.json`/`credit_scenarios.npz` are generated from public `hullkit` APIs with seed `20260746`; that Hull Table 24.4 (S&P 1981–2019 transition matrix) and Table 25.6 (Creditex iTraxx Europe mid quotes, 2007-01-31) are transcribed textbook constants used as fixtures, not downloaded or redistributed vendor data; and that the values are for education/integration checks only.
- `CLAUDE.md`: `vol 18–27` → `vol 18–28` (both occurrences).
- `Makefile` help text (repo root): `vol 19-27` → `19-28`, `vol 18-27` → `18-28`.

- [ ] **Step 4: Run portal and report tests**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/report/tests`
Expected: all passed (figures = 82)

- [ ] **Step 5: Commit**

```bash
git add johnhull/report johnhull/book/_toc.yml johnhull/book/notebooks/00_overview.md johnhull/ROADMAP.md johnhull/README.md johnhull/VALIDATION.md johnhull/docs/DATA_PROVENANCE.md johnhull/CLAUDE.md Makefile
git commit -m "feat(johnhull): wire vol 28 into the portal, book and release docs"
```

### Task 11: full gates

- [ ] **Step 1: Scoped tests and lint**

```bash
uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests
uv run --no-sync ruff check johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts johnhull/report/report_builder johnhull/report/tests
uv run --no-sync ruff format --check johnhull/hullkit/src johnhull/hullkit/tests johnhull/scripts johnhull/report/report_builder johnhull/report/tests
```
Expected: all passed; ruff clean (fix any line-length findings by wrapping; `build_*_notebook.py` is excluded).

- [ ] **Step 2: Artifact, notebook, portal, book, release gates**

```bash
make hull-artifacts-check
make hull-notebooks-check
make hull-report
make hull-book
make hull-release-check
```
Expected: each exits 0. `hull-artifacts-check` rebuilds vol 19–28 in /tmp and reports byte identity; `hull-report` prints 12 themes / 82 figures; `hull-release-check` prints no findings.

- [ ] **Step 3: Confirm the untouched core**

Run: `git diff --stat main -- johnhull/hullkit/src/hullkit/credit.py johnhull/hullkit/src/hullkit/copula.py johnhull/volumes/09_credit_xva`
Expected: empty (no changes)

- [ ] **Step 4: Record the evidence and commit**

Fill the `VALIDATION.md` run table with the observed counts, then:

```bash
git add johnhull/VALIDATION.md
git commit -m "docs(johnhull): record the vol 28 validation run"
make hull-release-check HULL_RELEASE_FLAGS=--require-tracked
```
Expected: exit 0 with `--require-tracked` (every release file is committed).

## Self-review notes

- Spec coverage: §3.1 modules → Tasks 1–5; §3.2 volume → Tasks 7–9; §3.3 arrays → Task 7/8 (kept in one list, `UNITS_BY_VOLUME` mirrors it); §4 checks → Task 8 (17 names identical to the spec); §5 wiring → Tasks 8–10; §6 decisions honoured (data policy, Hull discretisation, untouched `credit.py`); §7 gates → Task 11.
- Deviation from the spec recorded here: `bootstrap_from_cds` lives in `cds.py` (not `credit_curve.py`) to avoid a circular import; the spec's `default_count_pmf` is named `binomial_pmf`; the spec's `smallest_integer_above`/`tranche_principal_by_defaults` are kept.
- Type consistency: `TrancheValuation.expected_principal` is `(M, m+1)` with a leading column of ones everywhere (reference, acceptance, notebook verification); `tranche_spread_vs_rho` is `(len(rho_grid), 6)` so the generic `line:rho_grid` plot draws one line per tranche.

