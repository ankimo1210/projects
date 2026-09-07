# quantkit Model Rigor (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give quantkit's model layer the statistical machinery to say "this model beats the baseline" (DSR, PBO, bootstrap IC), fix the two leakage bugs (stacking OOF, conformal calibration), add nested tuning / sample weights / target transforms, and run every tier on real US-equity and crypto snapshots with a fingerprinted leaderboard.

**Architecture:** Statistical tests live in `quantkit/backtest/stats.py` (they operate on return / IC series). Model fixes and additions stay in `quantkit/models/` under the existing `fit(X, y) / predict(X)` contract so `walk_forward_predict` is unchanged. A new `quantkit/experiments/` package holds the real-data snapshot, the leaderboard runner and the JSON record. Notebooks only *call* the library; nothing analytical lives in a notebook.

**Tech Stack:** Python 3.12, pandas 2.x, numpy, scipy, scikit-learn 1.9, pytest. No new dependencies in Phase 1 (lightgbm/torch arrive in Phase 2).

**Spec:** `docs/superpowers/specs/2026-09-06-quantkit-model-enhancement-design.md` (§2–§5, §7). Phase 2 (§6) gets its own plan after this one lands.

**Spec deviation (deliberate):** §4.1/§5.2 said PBO refits every candidate on combinatorial folds. This plan computes PBO the way Bailey et al. define CSCV — on the matrix of *already out-of-sample* daily IC series (dates × candidates) that the leaderboard produces anyway. It measures selection overfitting among N candidates (what PBO is for), costs no refits, and `pbo_folds` is therefore not needed. Model-fit leakage is already covered by CPCV.

## Global Constraints

- Run everything from the workspace root `/home/kazumasa/projects` with `uv run --no-sync ...`. Never run `uv sync --package` (it prunes the shared `.venv`).
- **Work in a dedicated worktree** — `~/projects` is shared by several sessions and its HEAD moves under you (it was on `codex/rates-ui-lab` when this plan was written). Create it with `git worktree add ../projects-quantkit-rigor -b claude/quantkit-model-rigor main` (or via the `superpowers:using-git-worktrees` skill) and run all commands there. Adjust paths below accordingly.
- Tests must be offline and deterministic (seeded). Live/network cells are confined to NB17's snapshot-building cell.
- **No silent forward-fill anywhere.** Missing rows are dropped and counted, never imputed.
- Every new public function gets a docstring in the style of its module (one paragraph on *why*, then parameters). Code, identifiers and commit messages in English; notebook prose in Japanese like the existing NBs.
- Commit messages end with:
  ```
  Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01BVhwX2wivMuVPhy5n3HpYu
  ```
- Test file convention: one new test module per task group (`tests/test_stats.py`, `tests/test_models_rigor.py`, `tests/test_experiments.py`), synthetic panels built by a local `_design()` helper like `tests/test_models_enh.py`.
- Baseline before you start: `uv run --no-sync pytest quantkit/tests -q` → `159 passed, 7 skipped`. `uv run --no-sync ruff check quantkit` → clean. Keep both green after every task.

---

## File map

| Path | Responsibility |
|---|---|
| `quantkit/src/quantkit/models/importance.py` (modify) | add `rank_ic_by_date`; `rank_ic` becomes its mean |
| `quantkit/src/quantkit/backtest/split.py` (modify) | add `purged_block_folds` (K contiguous test blocks, two-sided purge) |
| `quantkit/src/quantkit/backtest/stats.py` (new) | `ICResult`, `bootstrap_series`, `bootstrap_ic`, `ic_difference`, `sharpe_difference`, `probabilistic_sharpe`, `expected_max_sharpe`, `deflated_sharpe`, `min_track_record_length`, `PBOResult`, `pbo` |
| `quantkit/src/quantkit/backtest/__init__.py` (modify) | export the above |
| `quantkit/src/quantkit/models/base.py` (modify) | `fit(X, y, sample_weight=None)`; `SklearnModel` passes weights through when the estimator accepts them |
| `quantkit/src/quantkit/models/baselines.py`, `ranking.py`, `ensemble.py`, `uncertainty.py`, `walkforward.py`, `importance.py` (modify) | accept/propagate `sample_weight`; purge fixes in `StackingModel` / `ConformalModel` |
| `quantkit/src/quantkit/models/weights.py` (new) | `time_decay_weights`, `uniqueness_weights` |
| `quantkit/src/quantkit/models/target.py` (new) | `vol_scaled_target`, `demeaned_target` |
| `quantkit/src/quantkit/models/tuning.py` (new) | `TunedModel` (nested, purged inner walk-forward) |
| `quantkit/src/quantkit/models/__init__.py` (modify) | export new names |
| `quantkit/src/quantkit/experiments/__init__.py`, `snapshot.py`, `leaderboard.py`, `record.py` (new) | real-data snapshot + manifest, leaderboard runner, fingerprinted JSON record |
| `quantkit/configs/universe.yaml` (modify) | `experiments:` universes (us / crypto) |
| `quantkit/notebooks/17_real_data_model_leaderboard.ipynb` (new) | real-data leaderboard, executed with outputs |
| `quantkit/reports/experiments/*.json` (new) | committed leaderboard records |
| `quantkit/README.md` (modify) | Phase 4 status, test count, NB list, honest "outputs saved" claim |
| `quantkit/tests/test_stats.py`, `test_models_rigor.py`, `test_experiments.py` (new) | tests for all of the above |

---

### Task 1: Per-date rank IC (`rank_ic_by_date`)

**Files:**
- Modify: `quantkit/src/quantkit/models/importance.py:27-45`
- Modify: `quantkit/src/quantkit/models/__init__.py` (export)
- Test: `quantkit/tests/test_models_rigor.py` (new file)

**Interfaces:**
- Produces: `rank_ic_by_date(pred: pd.Series, label: pd.Series) -> pd.Series` — index `date` (DatetimeIndex, name `"date"`), values Spearman IC per date, dates with < 2 assets or undefined corr omitted, name `"rank_ic"`. `rank_ic(pred, label) -> float` unchanged in value (mean of the above, NaN if empty).

- [ ] **Step 1: Write the failing tests**

Create `quantkit/tests/test_models_rigor.py`:

```python
"""Rigor tests for the model layer: per-date IC, purged stacking/conformal,
sample weights, target transforms, weights, nested tuning.

Everything is synthetic and seeded. Where a test checks leakage it does so with a
spy model that records the dates it was fitted on, then asserts the platform's own
``is_purged`` / ``is_leakage_free`` on those dates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantkit import backtest as B
from quantkit import models as MD


def _design(n_dates=200, n_assets=20, seed=0, noise=0.5):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    a = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    b = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    eps = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    label = a - 0.5 * b + noise * eps
    X, y = MD.make_design({"a": a, "b": b}, label)
    return X, y, dates


# --- per-date rank IC ---------------------------------------------------------
def test_rank_ic_by_date_matches_mean_and_perfect_order():
    X, y, dates = _design(n_dates=30, n_assets=10)
    s = MD.rank_ic_by_date(y, y)  # a series against itself: IC = 1 every date
    assert s.index.name == "date" and len(s) == len(dates)
    np.testing.assert_allclose(s.to_numpy(), 1.0)
    pred = X["a"]
    s2 = MD.rank_ic_by_date(pred, y)
    assert MD.rank_ic(pred, y) == pytest.approx(float(s2.mean()))


def test_rank_ic_by_date_skips_dates_with_one_asset_and_constant_pred():
    X, y, dates = _design(n_dates=5, n_assets=3)
    d0 = dates[0]
    keep = X.index.get_level_values("date") != d0
    one_asset_day = X.index.get_level_values("date") == d0
    # keep one asset on d0 -> corr undefined -> date omitted
    mask = keep | (one_asset_day & (X.index.get_level_values("asset") == "A00"))
    s = MD.rank_ic_by_date(X["a"][mask], y[mask])
    assert d0 not in s.index and len(s) == 4
    const = pd.Series(0.0, index=X.index)  # constant prediction -> corr NaN -> empty
    assert MD.rank_ic_by_date(const, y).empty
    assert np.isnan(MD.rank_ic(const, y))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q`
Expected: FAIL — `AttributeError: module 'quantkit.models' has no attribute 'rank_ic_by_date'`

- [ ] **Step 3: Implement**

In `quantkit/src/quantkit/models/importance.py`, replace the `rank_ic` function (lines 27–45) with:

```python
def rank_ic_by_date(pred: pd.Series, label: pd.Series) -> pd.Series:
    """Cross-sectional rank IC (Spearman) between ``pred`` and ``label`` on each date.

    Both are ``(date, asset)``-indexed. Dates with fewer than two assets, or where
    the correlation is undefined (a constant prediction), are omitted rather than
    reported as 0 — an undefined IC is not "no skill", it is "no measurement".
    The returned Series is what the bootstrap and PBO in
    :mod:`quantkit.backtest.stats` resample.
    """
    df = pd.DataFrame({"pred": pred, "label": label}).dropna()
    if df.empty:
        return pd.Series(dtype="float64", name="rank_ic").rename_axis("date")
    dates = df.index.get_level_values("date")
    out: dict[pd.Timestamp, float] = {}
    for d, g in df.groupby(dates, sort=True):
        if len(g) < 2:
            continue
        ic = g["pred"].rank().corr(g["label"].rank())
        if pd.notna(ic):
            out[d] = float(ic)
    s = pd.Series(out, dtype="float64", name="rank_ic")
    s.index = pd.DatetimeIndex(s.index, name="date")
    return s


def rank_ic(pred: pd.Series, label: pd.Series) -> float:
    """Mean over dates of :func:`rank_ic_by_date` (NaN when no date is measurable)."""
    s = rank_ic_by_date(pred, label)
    return float(s.mean()) if len(s) else float("nan")
```

In `quantkit/src/quantkit/models/__init__.py`: change `from .importance import mda_importance, rank_ic` to `from .importance import mda_importance, rank_ic, rank_ic_by_date` and add `"rank_ic_by_date",` to `__all__` (keep the list sorted).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py quantkit/tests/test_validation.py -q`
Expected: all PASS (the MDA tests still pass because `rank_ic` values are unchanged).

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/importance.py quantkit/src/quantkit/models/__init__.py quantkit/tests/test_models_rigor.py
git commit -m "feat(quantkit): expose the per-date rank IC series behind rank_ic"
```

---

### Task 2: `purged_block_folds` in `backtest/split.py`

**Files:**
- Modify: `quantkit/src/quantkit/backtest/split.py` (append after `n_combinatorial_folds`)
- Modify: `quantkit/src/quantkit/backtest/__init__.py`
- Test: `quantkit/tests/test_stats.py` (new file; split helpers live here with the stats)

**Interfaces:**
- Produces: `purged_block_folds(index, *, n_splits: int, horizon: int = 0, embargo: int = 0) -> list[Fold]` — `n_splits` contiguous test blocks covering `index`; each fold's train is the two-sided-purged complement. Equivalent to `combinatorial_purged(index, n_groups=n_splits, k_test=1, ...)`.

- [ ] **Step 1: Write the failing test**

Create `quantkit/tests/test_stats.py`:

```python
"""Statistical tests for model comparison: bootstrap IC, deflated Sharpe, PBO —
plus the purged K-fold helper they and StackingModel share.

The point of every test here is that the statistic behaves correctly on *known*
synthetic cases: pure noise must not look like skill, a planted edge must.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quantkit import backtest as B
from quantkit.backtest import stats as ST


def _idx(n=240):
    return pd.bdate_range("2020-01-01", periods=n)


# --- purged block folds -------------------------------------------------------
def test_purged_block_folds_cover_index_and_are_purged():
    idx = _idx(240)
    folds = B.purged_block_folds(idx, n_splits=4, horizon=5, embargo=2)
    assert len(folds) == 4
    covered = pd.DatetimeIndex(np.concatenate([f.test.values for f in folds]))
    assert covered.sort_values().equals(idx)  # test blocks partition the index
    for f in folds:
        assert B.is_purged(f, idx, horizon=5, embargo=2)
        assert len(f.test) == 60
    # an interior block loses bars on BOTH sides of its test block
    interior = folds[1]
    assert len(interior.train) == 240 - 60 - 5 - 2


def test_purged_block_folds_rejects_bad_args():
    with pytest.raises(ValueError):
        B.purged_block_folds(_idx(10), n_splits=1)
    with pytest.raises(ValueError):
        B.purged_block_folds(_idx(3), n_splits=5)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q`
Expected: FAIL — `ImportError: cannot import name 'stats'` (the module doesn't exist yet). Create an empty `quantkit/src/quantkit/backtest/stats.py` containing only a module docstring `"""Statistical tests for model comparison (filled in by later tasks)."""` and re-run: FAIL with `AttributeError: ... has no attribute 'purged_block_folds'`.

- [ ] **Step 3: Implement**

Append to `quantkit/src/quantkit/backtest/split.py` (after `n_combinatorial_folds`):

```python
def purged_block_folds(
    index: pd.DatetimeIndex, *, n_splits: int, horizon: int = 0, embargo: int = 0
) -> list[Fold]:
    """K-fold in time: ``n_splits`` contiguous test blocks, purged complement as train.

    This is :func:`combinatorial_purged` with ``k_test=1`` — each block is a test set
    once and the training set is everything else minus the two-sided purge+embargo
    zone around it. It exists as a named helper because out-of-fold constructions
    (stacking meta-features, inner tuning folds) need exactly this and must not
    re-implement the purge.
    """
    if n_splits < 2:
        raise ValueError("n_splits must be >= 2")
    return combinatorial_purged(index, n_groups=n_splits, k_test=1, horizon=horizon, embargo=embargo)
```

In `quantkit/src/quantkit/backtest/__init__.py`: add `purged_block_folds,` to the `from .split import (...)` block and `"purged_block_folds",` to `__all__` (sorted).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q`
Expected: 2 PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/backtest/split.py quantkit/src/quantkit/backtest/__init__.py quantkit/src/quantkit/backtest/stats.py quantkit/tests/test_stats.py
git commit -m "feat(quantkit): add purged_block_folds (time K-fold with two-sided purge)"
```

---

### Task 3: Block-bootstrap IC and paired differences (`backtest/stats.py`)

**Files:**
- Modify: `quantkit/src/quantkit/backtest/stats.py`
- Modify: `quantkit/src/quantkit/backtest/__init__.py`
- Test: `quantkit/tests/test_stats.py`

**Interfaces:**
- Consumes: `quantkit.models.importance.rank_ic_by_date` (Task 1) — imported lazily inside functions to avoid a `backtest ↔ models` import cycle.
- Produces:
  - `ICResult(mean: float, lo: float, hi: float, n: int, ci: float)` frozen dataclass with property `beats_zero -> bool` (CI excludes 0; False when any bound is NaN).
  - `bootstrap_series(x: pd.Series, *, n_boot=1000, block=21, ci=0.95, random_state=0) -> ICResult` — circular block bootstrap of the mean.
  - `bootstrap_ic(pred, label, **kw) -> ICResult`
  - `ic_difference(pred_a, pred_b, label, **kw) -> ICResult` — paired on common dates.
  - `sharpe_difference(returns_a: pd.Series, returns_b: pd.Series, *, periods=252, n_boot=1000, block=21, ci=0.95, random_state=0) -> ICResult` — mean is the annualized Sharpe difference.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_stats.py`:

```python
from quantkit import models as MD


def _panel_design(n_dates=300, n_assets=20, seed=0, noise=1.0):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    sig = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    eps = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    label = sig + noise * eps
    X, y = MD.make_design({"sig": sig, "noise": eps.shift(1).bfill()}, label)
    return X, y


# --- block bootstrap ----------------------------------------------------------
def test_bootstrap_series_mean_is_sample_mean_and_ci_brackets_it():
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(0.05, 1.0, 500))
    r = ST.bootstrap_series(x, n_boot=500, block=10)
    assert r.mean == pytest.approx(float(x.mean()))
    assert r.lo <= r.mean <= r.hi and r.n == 500 and r.ci == 0.95
    # more data -> narrower interval
    wide = ST.bootstrap_series(x.iloc[:50], n_boot=500, block=10)
    assert (r.hi - r.lo) < (wide.hi - wide.lo)


def test_bootstrap_series_is_deterministic_and_handles_empty():
    x = pd.Series(np.arange(30, dtype=float))
    a, b = ST.bootstrap_series(x, n_boot=50), ST.bootstrap_series(x, n_boot=50)
    assert (a.lo, a.hi) == (b.lo, b.hi)
    e = ST.bootstrap_series(pd.Series(dtype="float64"))
    assert np.isnan(e.mean) and e.n == 0 and not e.beats_zero


def test_bootstrap_ic_detects_planted_edge_and_ic_difference_is_paired():
    X, y = _panel_design()
    strong = ST.bootstrap_ic(X["sig"], y, n_boot=300)
    weak = ST.bootstrap_ic(X["noise"], y, n_boot=300)
    assert strong.beats_zero and strong.lo > 0.3
    assert not weak.beats_zero
    same = ST.ic_difference(X["sig"], X["sig"], y, n_boot=300)
    assert same.mean == 0.0 and same.lo <= 0.0 <= same.hi and not same.beats_zero
    diff = ST.ic_difference(X["sig"], X["noise"], y, n_boot=300)
    assert diff.beats_zero and diff.mean > 0


def test_sharpe_difference_sign_and_pairing():
    rng = np.random.default_rng(2)
    idx = _idx(1000)
    good = pd.Series(rng.normal(0.001, 0.01, 1000), index=idx)
    flat = pd.Series(rng.normal(0.0, 0.01, 1000), index=idx)
    d = ST.sharpe_difference(good, flat, n_boot=300)
    assert d.mean > 0 and d.beats_zero
    # pairing aligns on common dates: a shorter series is fine
    d2 = ST.sharpe_difference(good.iloc[100:], flat, n_boot=100)
    assert d2.n == 900
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q`
Expected: FAIL — `AttributeError: module 'quantkit.backtest.stats' has no attribute 'bootstrap_series'`.

- [ ] **Step 3: Implement**

Replace the contents of `quantkit/src/quantkit/backtest/stats.py` with:

```python
"""Statistical tests for model comparison — the "did it really beat the baseline" layer.

Three complementary tools, each answering a different overfitting question:

  * **Block-bootstrap intervals** (:func:`bootstrap_ic`, :func:`ic_difference`,
    :func:`sharpe_difference`): is the out-of-sample IC / Sharpe (or the *paired*
    difference vs a baseline) distinguishable from zero, given serial correlation?
  * **Deflated Sharpe ratio** (:func:`deflated_sharpe`, Bailey & López de Prado 2014):
    after trying ``N`` candidates, is the best Sharpe more than what the best of ``N``
    noise strategies would show?
  * **Probability of backtest overfitting** (:func:`pbo`, Bailey et al. 2017 CSCV):
    when we pick the in-sample best among the candidates, how often is it below
    median out of sample?

All inputs are *already out-of-sample* series (walk-forward predictions or
backtest returns). Nothing here refits a model; the leaderboard in
:mod:`quantkit.experiments` wires these to the honest evaluation.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats as sps

_EULER_GAMMA = 0.5772156649015329


# --- result containers --------------------------------------------------------
@dataclass(frozen=True)
class ICResult:
    """A point estimate with a bootstrap confidence interval."""

    mean: float
    lo: float
    hi: float
    n: int
    ci: float

    @property
    def beats_zero(self) -> bool:
        """True when the interval excludes 0 (either side). NaN bounds never beat."""
        if not (np.isfinite(self.lo) and np.isfinite(self.hi)):
            return False
        return bool(self.lo > 0.0 or self.hi < 0.0)


def _empty(ci: float) -> ICResult:
    return ICResult(float("nan"), float("nan"), float("nan"), 0, ci)


# --- circular block bootstrap -------------------------------------------------
def _block_indices(n: int, *, n_boot: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """``(n_boot, n)`` resample indices from a circular block bootstrap.

    Blocks of ``block`` consecutive positions (wrapping around the end) are drawn
    with replacement until ``n`` positions are filled, so serial dependence within
    a block is preserved — the plain iid bootstrap understates the variance of
    autocorrelated IC or return series.
    """
    block = max(1, min(int(block), n))
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n, size=(n_boot, n_blocks))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]) % n
    return idx.reshape(n_boot, -1)[:, :n]


def bootstrap_series(
    x: pd.Series,
    *,
    n_boot: int = 1000,
    block: int = 21,
    ci: float = 0.95,
    random_state: int = 0,
) -> ICResult:
    """Block-bootstrap confidence interval for the mean of a (time-ordered) series.

    ``block`` should be at least the label horizon so overlapping-label
    autocorrelation stays inside a block. Deterministic given ``random_state``.
    """
    v = pd.Series(x).dropna().to_numpy(dtype="float64")
    n = len(v)
    if n == 0:
        return _empty(ci)
    rng = np.random.default_rng(random_state)
    means = v[_block_indices(n, n_boot=n_boot, block=block, rng=rng)].mean(axis=1)
    a = (1.0 - ci) / 2.0
    return ICResult(
        float(v.mean()), float(np.quantile(means, a)), float(np.quantile(means, 1.0 - a)), n, ci
    )


def bootstrap_ic(pred: pd.Series, label: pd.Series, **kw) -> ICResult:
    """Block-bootstrap interval for the mean cross-sectional rank IC of ``pred``."""
    from ..models.importance import rank_ic_by_date  # lazy: avoid backtest<->models cycle

    return bootstrap_series(rank_ic_by_date(pred, label), **kw)


def ic_difference(pred_a: pd.Series, pred_b: pd.Series, label: pd.Series, **kw) -> ICResult:
    """Paired block-bootstrap interval for ``IC_a - IC_b``, matched date by date.

    Pairing matters: two models evaluated on the same days share the market's
    good and bad days, so the difference is far less noisy than the two
    unpaired intervals suggest. Only dates where both ICs exist are used.
    """
    from ..models.importance import rank_ic_by_date

    a, b = rank_ic_by_date(pred_a, label), rank_ic_by_date(pred_b, label)
    both = pd.concat({"a": a, "b": b}, axis=1).dropna()
    return bootstrap_series(both["a"] - both["b"], **kw)


def sharpe_difference(
    returns_a: pd.Series,
    returns_b: pd.Series,
    *,
    periods: int = 252,
    n_boot: int = 1000,
    block: int = 21,
    ci: float = 0.95,
    random_state: int = 0,
) -> ICResult:
    """Paired block-bootstrap interval for the annualized Sharpe difference ``a - b``.

    Each resample draws the *same* block indices for both series, then computes
    ``SR_a - SR_b``; the point estimate is the full-sample difference.
    """
    both = pd.concat({"a": returns_a, "b": returns_b}, axis=1).dropna()
    n = len(both)
    if n < 3:
        return _empty(ci)
    a, b = both["a"].to_numpy(dtype="float64"), both["b"].to_numpy(dtype="float64")

    def _sr(m: np.ndarray) -> np.ndarray:
        sd = m.std(axis=-1, ddof=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(sd > 0, m.mean(axis=-1) / sd * np.sqrt(periods), np.nan)

    rng = np.random.default_rng(random_state)
    idx = _block_indices(n, n_boot=n_boot, block=block, rng=rng)
    diffs = _sr(a[idx]) - _sr(b[idx])
    diffs = diffs[np.isfinite(diffs)]
    point = float(_sr(a[None, :])[0] - _sr(b[None, :])[0])
    if diffs.size == 0:
        return ICResult(point, float("nan"), float("nan"), n, ci)
    q = (1.0 - ci) / 2.0
    return ICResult(point, float(np.quantile(diffs, q)), float(np.quantile(diffs, 1.0 - q)), n, ci)
```

(`itertools`, `Callable`, `sps` and `_EULER_GAMMA` are used by Tasks 4–5; ruff will flag them as unused until then — add `# noqa: F401` temporarily on the `import itertools`, `from collections.abc import Callable` and `from scipy import stats as sps` lines, and remove the markers in Task 5.)

In `quantkit/src/quantkit/backtest/__init__.py` add:

```python
from .stats import (
    ICResult,
    bootstrap_ic,
    bootstrap_series,
    ic_difference,
    sharpe_difference,
)
```

and the five names to `__all__` (sorted). Also add a line to the package docstring: `* :mod:`quantkit.backtest.stats` — bootstrap intervals, deflated Sharpe, PBO (the "did it beat the baseline" tests).`

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q && uv run --no-sync ruff check quantkit`
Expected: all PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/backtest/stats.py quantkit/src/quantkit/backtest/__init__.py quantkit/tests/test_stats.py
git commit -m "feat(quantkit): block-bootstrap IC / Sharpe intervals with paired differences"
```

---

### Task 4: Probabilistic & deflated Sharpe, MinTRL

**Files:**
- Modify: `quantkit/src/quantkit/backtest/stats.py`
- Modify: `quantkit/src/quantkit/backtest/__init__.py`
- Test: `quantkit/tests/test_stats.py`

**Interfaces:**
- Produces (all Sharpe quantities **per period, not annualized**, matching the paper):
  - `sharpe_moments(returns) -> tuple[float, int, float, float]` = `(sr, T, skew, kurt)` with kurt non-excess (normal = 3).
  - `probabilistic_sharpe(returns, *, sr_benchmark: float = 0.0) -> float`
  - `expected_max_sharpe(n_trials: int, sr_var: float) -> float` (= $SR_0$; 0.0 when `n_trials <= 1` or `sr_var <= 0`)
  - `deflated_sharpe(returns, *, n_trials: int, sr_var: float) -> float` = `probabilistic_sharpe(returns, sr_benchmark=expected_max_sharpe(...))`
  - `min_track_record_length(returns, *, sr_benchmark=0.0, alpha=0.05) -> float` (periods; `inf` when `sr <= sr_benchmark`)

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_stats.py`:

```python
# --- probabilistic / deflated Sharpe -------------------------------------------
def test_probabilistic_sharpe_matches_hand_formula_and_is_half_at_benchmark():
    rng = np.random.default_rng(3)
    r = pd.Series(rng.normal(0.05, 1.0, 2000))
    sr, t, skew, kurt = ST.sharpe_moments(r)
    assert sr == pytest.approx(r.mean() / r.std(ddof=1))
    z = (sr - 0.0) * np.sqrt(t - 1) / np.sqrt(1 - skew * sr + (kurt - 1) / 4 * sr**2)
    from scipy.stats import norm

    assert ST.probabilistic_sharpe(r) == pytest.approx(norm.cdf(z))
    assert ST.probabilistic_sharpe(r, sr_benchmark=sr) == pytest.approx(0.5)
    assert ST.probabilistic_sharpe(r) > 0.95  # SR 0.05/day over 2000 days is real


def test_expected_max_sharpe_grows_with_trials_and_is_zero_for_one_trial():
    assert ST.expected_max_sharpe(1, 0.01) == 0.0
    assert ST.expected_max_sharpe(10, 0.0) == 0.0
    e10, e100 = ST.expected_max_sharpe(10, 0.01), ST.expected_max_sharpe(100, 0.01)
    assert 0 < e10 < e100
    # variance scales the expectation linearly in its square root
    assert ST.expected_max_sharpe(10, 0.04) == pytest.approx(2 * e10)


def test_deflated_sharpe_is_not_fooled_by_the_best_of_many_noise_strategies():
    """The naive PSR of the best-of-50 noise strategies looks great; the DSR does not."""
    rng = np.random.default_rng(4)
    psr, dsr = [], []
    for _ in range(20):
        trials = rng.normal(0.0, 0.01, size=(50, 750))  # 50 noise strategies, 3y daily
        srs = trials.mean(axis=1) / trials.std(axis=1, ddof=1)
        best = pd.Series(trials[int(np.argmax(srs))])
        psr.append(ST.probabilistic_sharpe(best))
        dsr.append(ST.deflated_sharpe(best, n_trials=50, sr_var=float(np.var(srs, ddof=1))))
    assert np.mean(psr) > 0.9  # selection bias fools the plain PSR
    assert np.mean(dsr) < 0.7  # deflation removes most of it
    assert np.mean(dsr) < np.mean(psr)


def test_deflated_sharpe_monotone_in_trials_and_min_trl():
    rng = np.random.default_rng(5)
    r = pd.Series(rng.normal(0.0008, 0.01, 1000))
    d = [ST.deflated_sharpe(r, n_trials=n, sr_var=0.002) for n in (1, 5, 50, 500)]
    assert d[0] > d[1] > d[2] > d[3]
    trl = ST.min_track_record_length(r, sr_benchmark=0.0, alpha=0.05)
    assert trl > 0 and np.isfinite(trl)
    assert np.isinf(ST.min_track_record_length(r, sr_benchmark=10.0))
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q -k "sharpe or trials"`
Expected: FAIL — `AttributeError: ... 'sharpe_moments'`.

- [ ] **Step 3: Implement**

Append to `quantkit/src/quantkit/backtest/stats.py`:

```python
# --- probabilistic / deflated Sharpe -------------------------------------------
def sharpe_moments(returns: pd.Series) -> tuple[float, int, float, float]:
    """``(sr, T, skew, kurt)`` of a per-period return series (kurt non-excess, normal = 3).

    All Sharpe quantities in this module are **per period** (not annualized), as in
    Bailey & López de Prado — the ``sqrt(T-1)`` in the PSR already carries the
    sample-size information that annualization would double count.
    """
    r = pd.Series(returns).dropna().to_numpy(dtype="float64")
    t = len(r)
    if t < 3 or r.std(ddof=1) == 0:
        return float("nan"), t, float("nan"), float("nan")
    sr = float(r.mean() / r.std(ddof=1))
    skew = float(sps.skew(r, bias=False))
    kurt = float(sps.kurtosis(r, fisher=False, bias=False))
    return sr, t, skew, kurt


def probabilistic_sharpe(returns: pd.Series, *, sr_benchmark: float = 0.0) -> float:
    """PSR: probability that the true Sharpe exceeds ``sr_benchmark`` (per period).

    ``Φ[(SR − SR*)·√(T−1) / √(1 − γ₃·SR + (γ₄−1)/4·SR²)]`` — the non-normality
    of returns (skew γ₃, kurtosis γ₄) widens the Sharpe's standard error.
    """
    sr, t, skew, kurt = sharpe_moments(returns)
    if not np.isfinite(sr):
        return float("nan")
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    if denom <= 0:
        return float("nan")
    z = (sr - sr_benchmark) * math.sqrt(t - 1) / math.sqrt(denom)
    return float(sps.norm.cdf(z))


def expected_max_sharpe(n_trials: int, sr_var: float) -> float:
    """``SR₀``: the Sharpe the *best* of ``n_trials`` skill-less strategies is expected to show.

    ``√V[SR_n]·[(1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))]`` with Euler's γ. ``sr_var``
    is the variance of the trials' per-period Sharpe estimates. With one trial
    (or no dispersion) there is no selection effect and ``SR₀ = 0``.
    """
    if n_trials <= 1 or sr_var <= 0:
        return 0.0
    n = float(n_trials)
    z1 = sps.norm.ppf(1.0 - 1.0 / n)
    z2 = sps.norm.ppf(1.0 - 1.0 / (n * math.e))
    return float(math.sqrt(sr_var) * ((1.0 - _EULER_GAMMA) * z1 + _EULER_GAMMA * z2))


def deflated_sharpe(returns: pd.Series, *, n_trials: int, sr_var: float) -> float:
    """DSR: the PSR against ``SR₀`` — Sharpe deflated for having tried ``n_trials`` candidates.

    The leaderboard passes the number of candidates it evaluated and the variance
    of their Sharpes, so a model that "wins" a large tournament must clear the
    bar the tournament itself sets. A DSR near 0.5 says the winner did no better
    than the expected best of noise.
    """
    return probabilistic_sharpe(returns, sr_benchmark=expected_max_sharpe(n_trials, sr_var))


def min_track_record_length(
    returns: pd.Series, *, sr_benchmark: float = 0.0, alpha: float = 0.05
) -> float:
    """MinTRL: periods needed for the Sharpe to exceed ``sr_benchmark`` at confidence ``1-alpha``.

    ``1 + [1 − γ₃·SR + (γ₄−1)/4·SR²]·(Φ⁻¹(1−α) / (SR − SR*))²`` (Bailey & López de
    Prado 2012). ``inf`` when the observed Sharpe does not exceed the benchmark.
    """
    sr, _, skew, kurt = sharpe_moments(returns)
    if not np.isfinite(sr) or sr <= sr_benchmark:
        return float("inf")
    var_term = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr**2
    z = sps.norm.ppf(1.0 - alpha)
    return float(1.0 + var_term * (z / (sr - sr_benchmark)) ** 2)
```

Export `deflated_sharpe, expected_max_sharpe, min_track_record_length, probabilistic_sharpe, sharpe_moments` from `backtest/__init__.py` (add to the `from .stats import (...)` block and `__all__`).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/backtest/stats.py quantkit/src/quantkit/backtest/__init__.py quantkit/tests/test_stats.py
git commit -m "feat(quantkit): probabilistic/deflated Sharpe and minimum track-record length"
```

---

### Task 5: Probability of backtest overfitting (CSCV `pbo`)

**Files:**
- Modify: `quantkit/src/quantkit/backtest/stats.py`
- Modify: `quantkit/src/quantkit/backtest/__init__.py`
- Test: `quantkit/tests/test_stats.py`

**Interfaces:**
- Produces: `PBOResult(pbo: float, logits: np.ndarray, n_combinations: int, n_candidates: int)` and `pbo(perf: pd.DataFrame, *, n_groups: int = 16, stat: str = "mean") -> PBOResult`. `perf` is dates × candidates (daily IC or daily returns); columns that are entirely NaN are dropped, then rows with any NaN are dropped. `stat ∈ {"mean", "sharpe"}`.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_stats.py`:

```python
# --- PBO (CSCV) ---------------------------------------------------------------
def test_pbo_is_about_half_for_pure_noise_candidates():
    rng = np.random.default_rng(6)
    perf = pd.DataFrame(rng.normal(0, 1, (800, 8)), index=_idx(800))
    res = ST.pbo(perf, n_groups=8)
    assert res.n_combinations == 70 and res.n_candidates == 8
    assert 0.3 <= res.pbo <= 0.7
    assert len(res.logits) == 70


def test_pbo_is_low_when_one_candidate_has_a_real_edge():
    rng = np.random.default_rng(7)
    perf = pd.DataFrame(rng.normal(0, 1, (800, 6)), index=_idx(800))
    perf[0] += 0.5  # a genuine, stable edge
    assert ST.pbo(perf, n_groups=8).pbo < 0.1


def test_pbo_drops_all_nan_columns_and_validates_args():
    rng = np.random.default_rng(8)
    perf = pd.DataFrame(rng.normal(0, 1, (200, 3)), index=_idx(200))
    perf["const"] = np.nan  # e.g. a constant-prediction model with undefined IC
    res = ST.pbo(perf, n_groups=4)
    assert res.n_candidates == 3
    with pytest.raises(ValueError):
        ST.pbo(perf, n_groups=5)  # must be even
    with pytest.raises(ValueError):
        ST.pbo(perf.iloc[:, :1], n_groups=4)  # need >= 2 candidates
    sharpe_res = ST.pbo(perf, n_groups=4, stat="sharpe")
    assert 0.0 <= sharpe_res.pbo <= 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q -k pbo`
Expected: FAIL — `AttributeError: ... 'pbo'`.

- [ ] **Step 3: Implement**

Append to `quantkit/src/quantkit/backtest/stats.py` (and remove the temporary `# noqa: F401` markers from Task 3):

```python
# --- probability of backtest overfitting (CSCV) --------------------------------
@dataclass(frozen=True)
class PBOResult:
    """CSCV output: the PBO plus the per-combination logits behind it."""

    pbo: float
    logits: np.ndarray
    n_combinations: int
    n_candidates: int


def _group_stat(sums: np.ndarray, sq: np.ndarray, counts: np.ndarray, stat: str) -> np.ndarray:
    """Per-candidate statistic from pooled group sums (mean or per-period Sharpe)."""
    n = counts.sum()
    mean = sums.sum(axis=0) / n
    if stat == "mean":
        return mean
    var = (sq.sum(axis=0) - n * mean**2) / max(n - 1, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(var > 0, mean / np.sqrt(var), np.nan)


def pbo(perf: pd.DataFrame, *, n_groups: int = 16, stat: str = "mean") -> PBOResult:
    """Probability of backtest overfitting via combinatorially symmetric CV (Bailey et al.).

    ``perf`` holds one *out-of-sample* performance series per candidate (dates ×
    candidates — e.g. the daily rank IC from ``walk_forward_predict``). The rows
    are cut into ``n_groups`` contiguous blocks; for every choice of half the
    blocks as "in-sample" (the rest "out-of-sample"), pick the IS-best candidate
    and record its OOS relative rank ``ω ∈ (0,1)`` as a logit
    ``λ = log(ω/(1−ω))``. PBO is the share of combinations with ``λ ≤ 0`` — how
    often selecting the IS winner lands you below the OOS median. ≈0.5 means the
    selection carries no information; ≈0 means the winner is real.

    Columns that are entirely NaN (a constant-prediction model has no defined IC)
    are dropped before rows with any NaN are removed, so one degenerate candidate
    does not erase the sample. ``stat`` is ``"mean"`` (of the series) or
    ``"sharpe"`` (per-period mean/std).
    """
    if n_groups < 2 or n_groups % 2:
        raise ValueError("n_groups must be an even integer >= 2")
    if stat not in ("mean", "sharpe"):
        raise ValueError("stat must be 'mean' or 'sharpe'")
    m = perf.dropna(axis=1, how="all").dropna(axis=0, how="any")
    if m.shape[1] < 2:
        raise ValueError("need at least two candidates with data")
    if len(m) < n_groups:
        raise ValueError("fewer rows than n_groups")
    values = m.to_numpy(dtype="float64")
    groups = np.array_split(np.arange(len(values)), n_groups)
    sums = np.stack([values[g].sum(axis=0) for g in groups])
    sq = np.stack([(values[g] ** 2).sum(axis=0) for g in groups])
    counts = np.array([len(g) for g in groups], dtype="float64")
    n_cand = values.shape[1]
    logits: list[float] = []
    for combo in itertools.combinations(range(n_groups), n_groups // 2):
        is_g = np.array(combo)
        oos_g = np.array([g for g in range(n_groups) if g not in combo])
        s_is = _group_stat(sums[is_g], sq[is_g], counts[is_g], stat)
        s_oos = _group_stat(sums[oos_g], sq[oos_g], counts[oos_g], stat)
        if not np.all(np.isfinite(s_is)) or not np.all(np.isfinite(s_oos)):
            continue
        best = int(np.argmax(s_is))
        omega = sps.rankdata(s_oos)[best] / (n_cand + 1.0)
        logits.append(math.log(omega / (1.0 - omega)))
    lam = np.asarray(logits, dtype="float64")
    p = float((lam <= 0).mean()) if lam.size else float("nan")
    return PBOResult(pbo=p, logits=lam, n_combinations=int(lam.size), n_candidates=n_cand)
```

Export `PBOResult, pbo` from `backtest/__init__.py`.

- [ ] **Step 4: Run tests and lint**

Run: `uv run --no-sync pytest quantkit/tests/test_stats.py -q && uv run --no-sync ruff check quantkit`
Expected: all PASS; ruff clean (no leftover `noqa`).

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/backtest/stats.py quantkit/src/quantkit/backtest/__init__.py quantkit/tests/test_stats.py
git commit -m "feat(quantkit): probability of backtest overfitting (CSCV) on OOS performance matrices"
```

---

### Task 6: `sample_weight` through the model contract

**Files:**
- Modify: `quantkit/src/quantkit/models/base.py`
- Modify: `quantkit/src/quantkit/models/baselines.py`, `ranking.py`, `ensemble.py` (EnsembleModel only), `uncertainty.py` (QuantileModel only), `walkforward.py`, `importance.py` (`mda_importance`)
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Produces:
  - `Model.fit(self, X, y, sample_weight: pd.Series | None = None) -> Model` (abstract signature; every subclass accepts the kwarg).
  - `accepts_sample_weight(estimator) -> bool` and `subset_weights(sample_weight, selector) -> pd.Series | None` in `models/base.py` (selector = boolean mask array or an Index).
  - `SklearnModel.fit` passes weights to the estimator when it accepts them; otherwise fits without and emits `RuntimeWarning("<name>: estimator ignores sample_weight")`. A weight Series is aligned with `.loc[X.index]`; a length mismatch raises `ValueError`.
  - `walk_forward_predict(make_model, X, y, folds, *, sample_weight=None)`, `mda_importance(..., sample_weight=None)` slice weights per fold.
  - `EnsembleModel.fit`, `RankModel.fit`, `QuantileModel.fit` propagate weights. Baselines accept and ignore them (they estimate nothing worth weighting).

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- sample weights -----------------------------------------------------------
class _RecordingEstimator:
    """sklearn-like estimator that records what fit() received."""

    def __init__(self, with_weights: bool = True):
        self.calls: list[dict] = []
        self.with_weights = with_weights
        if with_weights:
            self.fit = self._fit_w
        else:
            self.fit = self._fit_nw

    def _fit_w(self, X, y, sample_weight=None):
        self.calls.append({"n": len(X), "w": None if sample_weight is None else np.asarray(sample_weight)})
        return self

    def _fit_nw(self, X, y):
        self.calls.append({"n": len(X), "w": "unsupported"})
        return self

    def predict(self, X):
        return np.zeros(len(X))


def test_sklearn_model_passes_aligned_weights_or_warns():
    X, y, _ = _design(n_dates=10, n_assets=3)
    w = pd.Series(np.linspace(1, 2, len(X)), index=X.index)
    est = _RecordingEstimator(with_weights=True)
    MD.SklearnModel(est, name="rec").fit(X, y, sample_weight=w.iloc[::-1])  # reversed order
    np.testing.assert_allclose(est.calls[0]["w"], w.to_numpy())  # aligned by index, not position
    est2 = _RecordingEstimator(with_weights=False)
    with pytest.warns(RuntimeWarning, match="ignores sample_weight"):
        MD.SklearnModel(est2, name="nw").fit(X, y, sample_weight=w)
    assert est2.calls[0]["w"] == "unsupported"
    with pytest.raises(ValueError):
        MD.SklearnModel(_RecordingEstimator(), name="bad").fit(X, y, sample_weight=np.ones(3))


def test_walk_forward_and_wrappers_slice_and_propagate_weights():
    X, y, dates = _design(n_dates=120, n_assets=4)
    w = pd.Series(1.0, index=X.index)
    folds = B.walk_forward(dates, train=40, test=20, horizon=1)
    seen: list[int] = []

    def factory():
        est = _RecordingEstimator()
        m = MD.SklearnModel(est, name="rec")
        seen.append(id(est))
        m._est = est
        return m

    made = []

    def spy_factory():
        m = factory()
        made.append(m)
        return m

    MD.walk_forward_predict(spy_factory, X, y, folds, sample_weight=w)
    for m, f in zip(made, folds, strict=True):
        assert len(m._est.calls[0]["w"]) == len(X[X.index.get_level_values("date").isin(f.train)])
    # wrappers propagate
    inner = _RecordingEstimator()
    MD.EnsembleModel([MD.SklearnModel(inner, name="i")]).fit(X, y, sample_weight=w)
    assert inner.calls[0]["w"] is not None
    inner2 = _RecordingEstimator()
    MD.RankModel(MD.SklearnModel(inner2, name="i")).fit(X, y, sample_weight=w)
    assert inner2.calls[0]["w"] is not None
    # baselines accept and ignore
    assert MD.MeanModel().fit(X, y, sample_weight=w).predict(X).nunique() == 1
    assert MD.ZeroModel().fit(X, y, sample_weight=w) is not None
    assert MD.PersistenceModel("a").fit(X, y, sample_weight=w) is not None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k weights`
Expected: FAIL — `TypeError: ... fit() got an unexpected keyword argument 'sample_weight'`.

- [ ] **Step 3: Implement**

`quantkit/src/quantkit/models/base.py` — replace the file body after the imports with:

```python
import inspect
import warnings
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class Model(ABC):
    """Fit/predict over a (date, asset)-indexed design matrix.

    ``sample_weight`` (a Series aligned to ``X.index``, or None) is part of the
    contract so time-decay or uniqueness weights (:mod:`quantkit.models.weights`)
    flow through every wrapper down to the estimator that can use them.
    """

    name: str = "model"

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> Model: ...

    @abstractmethod
    def predict(self, X: pd.DataFrame) -> pd.Series: ...


def accepts_sample_weight(estimator) -> bool:
    """True if ``estimator.fit`` declares a ``sample_weight`` parameter."""
    try:
        return "sample_weight" in inspect.signature(estimator.fit).parameters
    except (TypeError, ValueError):
        return False


def subset_weights(sample_weight: pd.Series | None, selector) -> pd.Series | None:
    """Slice weights by a boolean mask (array) or an Index; None stays None."""
    if sample_weight is None:
        return None
    if isinstance(selector, pd.Index):
        return sample_weight.loc[selector]
    return sample_weight[np.asarray(selector, dtype=bool)]


class SklearnModel(Model):
    """Adapter around any sklearn-style regressor.

    Optional standardization fits its mean/std on the **training** ``X`` only and
    reuses them at predict time, so test statistics never leak into the fit.
    Sample weights are forwarded when the estimator supports them; otherwise the
    fit proceeds unweighted with a ``RuntimeWarning`` — never silently.
    """

    def __init__(self, estimator, name: str | None = None, *, standardize: bool = True):
        self.estimator = estimator
        self.name = name or type(estimator).__name__
        self.standardize = standardize
        self._mu: pd.Series | None = None
        self._sd: pd.Series | None = None

    def _fit_scaler(self, X: pd.DataFrame) -> np.ndarray:
        if not self.standardize:
            return X.to_numpy()
        self._mu = X.mean()
        self._sd = X.std(ddof=0).replace(0.0, 1.0)
        return ((X - self._mu) / self._sd).to_numpy()

    def _apply_scaler(self, X: pd.DataFrame) -> np.ndarray:
        if not self.standardize:
            return X.to_numpy()
        return ((X - self._mu) / self._sd).to_numpy()

    def _weights_array(self, X: pd.DataFrame, sample_weight) -> np.ndarray:
        if isinstance(sample_weight, pd.Series):
            w = sample_weight.reindex(X.index)
            if w.isna().any():
                raise ValueError("sample_weight is missing entries for some rows of X")
            return w.to_numpy(dtype="float64")
        w = np.asarray(sample_weight, dtype="float64")
        if len(w) != len(X):
            raise ValueError(f"sample_weight length {len(w)} != rows of X {len(X)}")
        return w

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> SklearnModel:
        Xs = self._fit_scaler(X)
        if sample_weight is None:
            self.estimator.fit(Xs, y.to_numpy())
        elif accepts_sample_weight(self.estimator):
            self.estimator.fit(Xs, y.to_numpy(), sample_weight=self._weights_array(X, sample_weight))
        else:
            self._weights_array(X, sample_weight)  # still validate, so a bad call is loud
            warnings.warn(
                f"{self.name}: estimator ignores sample_weight (fit unweighted)",
                RuntimeWarning,
                stacklevel=2,
            )
            self.estimator.fit(Xs, y.to_numpy())
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        pred = self.estimator.predict(self._apply_scaler(X))
        return pd.Series(pred, index=X.index, name="prediction")
```

`baselines.py`: change the three `fit` signatures to `def fit(self, X, y, sample_weight=None) -> ...:` (bodies unchanged; add one sentence to the module docstring: "Baselines accept ``sample_weight`` for interface compatibility and ignore it.").

`ranking.py` `RankModel.fit`:

```python
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> RankModel:
        self.base.fit(X, cross_sectional_rank(y), sample_weight=sample_weight)
        return self
```

`ensemble.py` `EnsembleModel.fit`:

```python
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> EnsembleModel:
        for m in self.models:
            m.fit(X, y, sample_weight=sample_weight)
        return self
```

(`StackingModel.fit` gets its signature in Task 7 — for now add `sample_weight=None` to its signature and pass it to the full refits `fac().fit(X, y, sample_weight=sample_weight)` and the meta fit `self.meta_factory().fit(meta_train, y.loc[meta_train.index], sample_weight=subset_weights(sample_weight, meta_train.index))`; import `subset_weights` from `.base`.)

`uncertainty.py` `QuantileModel.fit`:

```python
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> QuantileModel:
        for q in self.quantiles:
            est = GradientBoostingRegressor(loss="quantile", alpha=q, **self._cfg)
            self._models[q] = SklearnModel(est, standardize=False).fit(X, y, sample_weight=sample_weight)
        return self
```

(`ConformalModel.fit` gets `sample_weight` in Task 8; add the kwarg to its signature now and pass `subset_weights(sample_weight, ~is_calib)` to `self.base.fit`.)

`walkforward.py`:

```python
def walk_forward_predict(
    make_model: Callable[[], Model],
    X: pd.DataFrame,
    y: pd.Series,
    folds: list[Fold],
    *,
    sample_weight: pd.Series | None = None,
) -> pd.Series:
    """... (existing docstring) ...

    ``sample_weight`` (aligned to ``X.index``) is sliced to each fold's training
    rows and passed to ``fit``.
    """
    dates = X.index.get_level_values("date")
    preds: list[pd.Series] = []
    for fold in folds:
        tr_mask = dates.isin(fold.train)
        tr = X[tr_mask]
        te = X[dates.isin(fold.test)]
        if tr.empty or te.empty:
            continue
        model = make_model().fit(tr, y.loc[tr.index], sample_weight=subset_weights(sample_weight, tr_mask))
        preds.append(model.predict(te))
    ...
```

(import `subset_weights` from `.base`.)

`importance.py` `mda_importance`: add `sample_weight: pd.Series | None = None` after `random_state`, and change the fit line to `model = make_model().fit(tr, y.loc[tr.index], sample_weight=subset_weights(sample_weight, tr_mask))` where `tr_mask = dates.isin(fold.train)` is computed first (import `subset_weights` from `.base`).

`models/__init__.py`: export `accepts_sample_weight, subset_weights` from `.base`.

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests -q && uv run --no-sync ruff check quantkit`
Expected: all previous tests still pass (the kwarg has a default), new tests pass, ruff clean.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models quantkit/tests/test_models_rigor.py
git commit -m "feat(quantkit): thread sample_weight through the model contract and walk-forward"
```

---

### Task 7: Purged out-of-fold stacking

**Files:**
- Modify: `quantkit/src/quantkit/models/ensemble.py:57-112`
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Consumes: `quantkit.backtest.split.purged_block_folds` (Task 2), `subset_weights` (Task 6).
- Produces: `StackingModel(base_models, meta_model, *, n_splits=5, horizon=0, embargo=0, name="stacking")`. OOF meta-features are built from folds whose training rows exclude the held block **and** its purge/embargo zone. Raises `ValueError` if no OOF rows remain.

- [ ] **Step 1: Write the failing test**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- purged stacking ----------------------------------------------------------
class _SpyModel(MD.Model):
    """Records the unique dates it was fitted on and the dates it predicted."""

    name = "spy"

    def __init__(self, log: list):
        self.log = log
        self._fit_dates = None

    def fit(self, X, y, sample_weight=None):
        self._fit_dates = pd.DatetimeIndex(sorted(X.index.get_level_values("date").unique()))
        return self

    def predict(self, X):
        te = pd.DatetimeIndex(sorted(X.index.get_level_values("date").unique()))
        self.log.append((self._fit_dates, te))
        return pd.Series(0.0, index=X.index, name="prediction")


def test_stacking_oof_folds_respect_purge_and_embargo():
    X, y, dates = _design(n_dates=120, n_assets=5)
    log: list = []
    stack = MD.StackingModel([lambda: _SpyModel(log)], MD.MeanModel, n_splits=4, horizon=5, embargo=2)
    stack.fit(X, y)
    oof_calls = [(tr, te) for tr, te in log if len(tr) < len(dates)]  # exclude the full refit
    assert len(oof_calls) == 4
    for tr, te in oof_calls:
        assert B.is_purged(B.Fold(tr, te), dates, horizon=5, embargo=2)
        # a leak-free fold really did drop bars next to the test block (edge blocks lose one side only)
        assert len(tr) <= len(dates) - len(te) - 2
    stack.predict(X)  # the full refit is used for prediction
    full = [tr for tr, _ in log if len(tr) == len(dates)]
    assert len(full) == 1


def test_stacking_without_purge_still_tracks_the_signal_and_errors_when_empty():
    X, y, _ = _design(noise=0.3)
    stack = MD.StackingModel([MD.ridge, MD.gradient_boosting], MD.ridge, n_splits=4, horizon=5).fit(X, y)
    assert MD.rank_ic(stack.predict(X), y) > 0.2
    Xs, ys, _ = _design(n_dates=6, n_assets=3)
    with pytest.raises(ValueError, match="out-of-fold"):
        MD.StackingModel([MD.ridge], MD.ridge, n_splits=3, horizon=10).fit(Xs, ys)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k stacking`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'horizon'`.

- [ ] **Step 3: Implement**

Replace `StackingModel` in `quantkit/src/quantkit/models/ensemble.py` with:

```python
class StackingModel(Model):
    """Stacked generalization with **purged** time-ordered out-of-fold meta-features.

    ``base_models`` and ``meta_model`` are **factories** (zero-arg callables returning
    a fresh :class:`Model`). The training dates are cut into ``n_splits`` contiguous
    blocks (:func:`quantkit.backtest.split.purged_block_folds`); each block's rows are
    predicted by base models fit on the *other* blocks minus the two-sided
    purge/embargo zone, so a training label whose ``horizon``-bar window reaches
    into the held block never informs that block's meta-feature. Pass the label
    horizon you used in :func:`quantkit.labels.forward_return` — with the default
    ``horizon=0`` adjacent blocks share overlapping labels and the meta-model is
    trained on leaked features (the bug NB16 exhibited: a stack worse than its
    members). For test prediction the base models are refit on the full training set.
    """

    def __init__(
        self,
        base_models: Sequence[Callable[[], Model]],
        meta_model: Callable[[], Model],
        *,
        n_splits: int = 5,
        horizon: int = 0,
        embargo: int = 0,
        name: str = "stacking",
    ):
        self.base_factories = list(base_models)
        self.meta_factory = meta_model
        self.n_splits = n_splits
        self.horizon = horizon
        self.embargo = embargo
        self.name = name
        self._cols = [f"m{i}" for i in range(len(self.base_factories))]
        self._base_full: list[Model] = []
        self._meta: Model | None = None

    def _meta_features(self, X: pd.DataFrame, models: Sequence[Model]) -> pd.DataFrame:
        return pd.DataFrame(
            {c: m.predict(X) for c, m in zip(self._cols, models, strict=True)}, index=X.index
        )

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> StackingModel:
        dates = X.index.get_level_values("date")
        unique = pd.DatetimeIndex(sorted(dates.unique()))
        n_splits = min(self.n_splits, len(unique))
        if n_splits < 2:
            raise ValueError("stacking needs at least two distinct dates")
        oof = pd.DataFrame(index=X.index, columns=self._cols, dtype="float64")
        folds = purged_block_folds(unique, n_splits=n_splits, horizon=self.horizon, embargo=self.embargo)
        for fold in folds:
            tr, te = dates.isin(fold.train), dates.isin(fold.test)
            if not tr.any() or not te.any():
                continue
            w_tr = subset_weights(sample_weight, tr)
            for c, fac in zip(self._cols, self.base_factories, strict=True):
                m = fac().fit(X[tr], y[tr], sample_weight=w_tr)
                oof.loc[te, c] = m.predict(X[te]).to_numpy()
        meta_train = oof.dropna()
        if meta_train.empty:
            raise ValueError("no out-of-fold rows left; lower n_splits, horizon or embargo")
        self._meta = self.meta_factory().fit(
            meta_train, y.loc[meta_train.index], sample_weight=subset_weights(sample_weight, meta_train.index)
        )
        self._base_full = [fac().fit(X, y, sample_weight=sample_weight) for fac in self.base_factories]
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if self._meta is None:
            raise RuntimeError("StackingModel must be fit before predict")
        z = self._meta_features(X, self._base_full)
        return self._meta.predict(z).rename("prediction")
```

Add `from ..backtest.split import purged_block_folds` and `from .base import Model, subset_weights` to the imports (drop the now-unused `numpy` import if ruff flags it).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py quantkit/tests/test_models_enh.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/ensemble.py quantkit/tests/test_models_rigor.py
git commit -m "fix(quantkit): purge and embargo the out-of-fold blocks in StackingModel"
```

---

### Task 8: Conformal — purged calibration, scaled scores, coverage by date

**Files:**
- Modify: `quantkit/src/quantkit/models/uncertainty.py:63-111`
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Produces: `ConformalModel(base, *, alpha=0.1, calib_fraction=0.3, horizon=0, scale: str | None = None, name="conformal")` with `fit(X, y, sample_weight=None)`, `predict(X) -> DataFrame[lower, point, upper]`, `coverage(X, y) -> float`, `coverage_by_date(X, y) -> pd.Series` (index `date`).

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- conformal: purge + scaled scores -----------------------------------------
def _hetero_design(n_dates=600, n_assets=30, seed=11):
    """Noise scale grows over time; 'rvol' is the (known) scale at each date."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    sigma = np.linspace(0.2, 2.0, n_dates)
    a = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    eps = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    rvol = pd.DataFrame(np.repeat(sigma[:, None], n_assets, axis=1), index=dates, columns=assets)
    label = a + rvol * eps
    X, y = MD.make_design({"a": a, "rvol": rvol}, label)
    return X, y, dates


def test_conformal_purges_the_train_calibration_boundary():
    X, y, dates = _design(n_dates=100, n_assets=4)
    log: list = []
    cm = MD.ConformalModel(_SpyModel(log), alpha=0.1, calib_fraction=0.3, horizon=5).fit(X, y)
    fit_dates, calib_pred_dates = log[0]  # predict() is first called on the calibration block
    n_calib = round(100 * 0.3)
    assert len(calib_pred_dates) == n_calib
    gap = dates.get_loc(calib_pred_dates[0]) - dates.get_loc(fit_dates[-1])
    assert gap > 5  # strictly more than `horizon` bars between last train and first calib
    assert cm.half_width_ is not None


def test_conformal_scaled_scores_recover_coverage_under_vol_drift():
    X, y, dates = _hetero_design()
    tr = X.index.get_level_values("date") < dates[400]
    raw = MD.ConformalModel(MD.ridge(1.0), alpha=0.1, horizon=1).fit(X[tr], y[tr])
    scaled = MD.ConformalModel(MD.ridge(1.0), alpha=0.1, horizon=1, scale="rvol").fit(X[tr], y[tr])
    cov_raw, cov_scaled = raw.coverage(X[~tr], y[~tr]), scaled.coverage(X[~tr], y[~tr])
    assert cov_raw < 0.85  # fixed-width interval under-covers once vol rises
    assert 0.86 <= cov_scaled <= 0.94
    by_date = scaled.coverage_by_date(X[~tr], y[~tr])
    assert by_date.index.name == "date" and len(by_date) == 200
    assert by_date.between(0, 1).all() and by_date.mean() == pytest.approx(cov_scaled, abs=1e-9)
    out = scaled.predict(X[~tr])
    assert (out["upper"] - out["lower"]).groupby(out.index.get_level_values("date")).mean().is_monotonic_increasing


def test_conformal_rejects_non_positive_scale():
    X, y, _ = _design(n_dates=40, n_assets=4)
    with pytest.raises(ValueError, match="strictly positive"):
        MD.ConformalModel(MD.ridge(), scale="a").fit(X, y)  # 'a' is signed
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k conformal`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'horizon'`.

- [ ] **Step 3: Implement**

Replace `ConformalModel` in `quantkit/src/quantkit/models/uncertainty.py` with:

```python
class ConformalModel:
    """Split-conformal prediction intervals around any base point model.

    The (time-ordered) training dates are split into an earlier fit block and the
    last ``calib_fraction`` of dates for calibration, with ``horizon`` bars purged
    between them so no fit label overlaps the calibration block. The interval
    half-width is the finite-sample ``1-alpha`` quantile of the calibration
    nonconformity scores ``|y - ŷ| / s(x)``, where ``s`` is 1 (``scale=None``) or a
    strictly positive feature column named by ``scale`` (e.g. trailing realized
    vol). Scaling makes the interval adapt to time-varying dispersion — under vol
    drift the fixed-width interval under-covers (NB16 measured 0.82 for a 0.90
    target); with ``scale`` the guarantee is restored as long as the *scaled*
    residuals are exchangeable. ``coverage_by_date`` shows where it holds.
    """

    def __init__(
        self,
        base: Model,
        *,
        alpha: float = 0.1,
        calib_fraction: float = 0.3,
        horizon: int = 0,
        scale: str | None = None,
        name: str = "conformal",
    ):
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        if not 0 < calib_fraction < 1:
            raise ValueError("calib_fraction must be in (0, 1)")
        self.base = base
        self.alpha = alpha
        self.calib_fraction = calib_fraction
        self.horizon = horizon
        self.scale = scale
        self.name = name
        self.half_width_: float | None = None

    def _scale(self, X: pd.DataFrame) -> pd.Series:
        if self.scale is None:
            return pd.Series(1.0, index=X.index)
        s = X[self.scale]
        if s.isna().any() or (s <= 0).any():
            raise ValueError(f"scale column {self.scale!r} must be strictly positive")
        return s

    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> ConformalModel:
        dates = X.index.get_level_values("date")
        unique = pd.DatetimeIndex(sorted(dates.unique()))
        n_calib = max(1, round(len(unique) * self.calib_fraction))
        n_fit = len(unique) - n_calib - self.horizon
        if n_fit < 1:
            raise ValueError("no fit dates left after calibration block and purge")
        fit_dates, calib_dates = unique[:n_fit], unique[-n_calib:]
        is_fit, is_calib = dates.isin(fit_dates), dates.isin(calib_dates)
        self.base.fit(X[is_fit], y[is_fit], sample_weight=subset_weights(sample_weight, is_fit))
        resid = (y[is_calib] - self.base.predict(X[is_calib])).abs()
        score = (resid / self._scale(X[is_calib])).to_numpy()
        n = len(score)
        level = min(1.0, np.ceil((n + 1) * (1 - self.alpha)) / n)  # finite-sample correction
        self.half_width_ = float(np.quantile(score, level, method="higher"))
        return self

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.half_width_ is None:
            raise RuntimeError("ConformalModel must be fit before predict")
        point = self.base.predict(X)
        h = self.half_width_ * self._scale(X)
        return pd.DataFrame({"lower": point - h, "point": point, "upper": point + h}, index=X.index)

    def _inside(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        out = self.predict(X)
        return ((y >= out["lower"]) & (y <= out["upper"])).astype("float64")

    def coverage(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Empirical fraction of ``y`` inside the predicted intervals."""
        return float(self._inside(X, y).mean())

    def coverage_by_date(self, X: pd.DataFrame, y: pd.Series) -> pd.Series:
        """Per-date empirical coverage — where (in time) the guarantee holds or breaks."""
        inside = self._inside(X, y)
        s = inside.groupby(inside.index.get_level_values("date")).mean().rename("coverage")
        s.index = pd.DatetimeIndex(s.index, name="date")
        return s
```

Add `from .base import Model, SklearnModel, subset_weights` to the imports. Update the module docstring's ConformalModel bullet to mention the purge and `scale`.

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py quantkit/tests/test_models_enh.py -q`
Expected: all PASS (the old `test_conformal_interval_achieves_target_coverage` still passes with `horizon=0`).

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/uncertainty.py quantkit/tests/test_models_rigor.py
git commit -m "fix(quantkit): purge the conformal calibration boundary; add scaled scores and coverage_by_date"
```

---

### Task 9: Sample-weight generators (`models/weights.py`)

**Files:**
- Create: `quantkit/src/quantkit/models/weights.py`
- Modify: `quantkit/src/quantkit/models/__init__.py`
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Produces: `time_decay_weights(index: pd.Index, halflife: float) -> pd.Series` (aligned to `index`; a `(date, asset)` MultiIndex or a DatetimeIndex; latest date = 1.0), `uniqueness_weights(touch_offset: pd.Series) -> pd.Series` (single-asset; NaN where offset NaN).

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- weight generators --------------------------------------------------------
def test_time_decay_weights_latest_is_one_and_halves_at_halflife():
    X, _, dates = _design(n_dates=50, n_assets=3)
    w = MD.time_decay_weights(X.index, halflife=10)
    assert w.index.equals(X.index)
    by_date = w.groupby(w.index.get_level_values("date")).first()
    assert by_date.loc[dates[-1]] == pytest.approx(1.0)
    assert by_date.loc[dates[-11]] == pytest.approx(0.5)
    assert by_date.is_monotonic_increasing
    plain = MD.time_decay_weights(dates, halflife=10)
    assert plain.iloc[-1] == 1.0 and len(plain) == 50


def test_uniqueness_weights_fixed_horizon_is_constant_and_overlap_halves():
    idx = pd.bdate_range("2020-01-01", periods=12)
    fixed = MD.uniqueness_weights(pd.Series(2.0, index=idx))
    interior = fixed.iloc[2:-2]
    assert interior.nunique() == 1 and interior.iloc[0] == pytest.approx(1 / 3)
    none = MD.uniqueness_weights(pd.Series(0.0, index=idx))  # windows of one bar never overlap
    np.testing.assert_allclose(none.to_numpy(), 1.0)
    two = MD.uniqueness_weights(pd.Series([1.0, 0.0], index=idx[:2]))
    assert two.iloc[0] == pytest.approx(0.75) and two.iloc[1] == pytest.approx(0.5)
    with_nan = MD.uniqueness_weights(pd.Series([1.0, np.nan, 0.0], index=idx[:3]))
    assert np.isnan(with_nan.iloc[1]) and with_nan.iloc[2] == pytest.approx(1.0)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k "decay or uniqueness"`
Expected: FAIL — `AttributeError: ... 'time_decay_weights'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/models/weights.py`:

```python
"""Sample-weight generators for the ``fit(X, y, sample_weight=)`` contract.

Two reasons to weight training rows in a panel:
  * **recency** — older regimes matter less; :func:`time_decay_weights` gives the
    latest date weight 1 and halves every ``halflife`` bars back;
  * **overlap** — labels spanning several bars share information, so a row that
    overlaps many others carries less unique evidence; :func:`uniqueness_weights`
    is López de Prado's average uniqueness (ch. 4). For a *fixed* horizon every
    interior label overlaps the same number of neighbours and the weight is a
    constant — it only discriminates for variable-length labels such as
    :func:`quantkit.labels.triple_barrier`'s ``touch_offset``.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def time_decay_weights(index: pd.Index, halflife: float) -> pd.Series:
    """Exponential decay by date: 1.0 on the latest date, 0.5 ``halflife`` bars earlier.

    ``index`` is a ``(date, asset)`` MultiIndex or a DatetimeIndex; the weight
    depends only on the date's position among the unique dates.
    """
    if halflife <= 0:
        raise ValueError("halflife must be positive")
    dates = index.get_level_values("date") if isinstance(index, pd.MultiIndex) else pd.DatetimeIndex(index)
    unique = pd.DatetimeIndex(sorted(pd.Index(dates).unique()))
    pos = pd.Series(np.arange(len(unique)), index=unique)
    age = (len(unique) - 1) - pos.reindex(dates).to_numpy()
    return pd.Series(0.5 ** (age / halflife), index=index, name="sample_weight")


def uniqueness_weights(touch_offset: pd.Series) -> pd.Series:
    """Average uniqueness of overlapping labels for one asset.

    ``touch_offset[t]`` is how many bars after ``t`` the label at ``t`` is decided
    (0 = same bar). Bar ``s`` is covered by ``c[s]`` open labels; label ``t``'s
    uniqueness is the mean of ``1/c[s]`` over its window ``[t, t+offset]``. Rows
    with a NaN offset get NaN (they are not labels).
    """
    off = pd.Series(touch_offset).to_numpy(dtype="float64")
    n = len(off)
    valid = np.isfinite(off) & (off >= 0)
    o = np.where(valid, off, 0).astype(int)
    span = n + (int(o.max()) if n else 0) + 2
    diff = np.zeros(span)
    for i in np.flatnonzero(valid):
        diff[i] += 1.0
        diff[i + o[i] + 1] -= 1.0
    concurrency = np.cumsum(diff)
    u = np.full(n, np.nan)
    for i in np.flatnonzero(valid):
        u[i] = float(np.mean(1.0 / concurrency[i : i + o[i] + 1]))
    return pd.Series(u, index=touch_offset.index, name="sample_weight")
```

Export both from `models/__init__.py` (`from .weights import time_decay_weights, uniqueness_weights`).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/weights.py quantkit/src/quantkit/models/__init__.py quantkit/tests/test_models_rigor.py
git commit -m "feat(quantkit): time-decay and label-uniqueness sample weights"
```

---

### Task 10: Target transforms (`models/target.py`)

**Files:**
- Create: `quantkit/src/quantkit/models/target.py`
- Modify: `quantkit/src/quantkit/models/__init__.py`
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Produces: `vol_scaled_target(fwd: pd.DataFrame, vol: pd.DataFrame, *, min_vol: float = 1e-8) -> pd.DataFrame`, `demeaned_target(fwd: pd.DataFrame, *, min_count: int = 2) -> pd.DataFrame`.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- target transforms --------------------------------------------------------
def test_vol_scaled_target_divides_by_causal_vol_and_never_fills():
    rng = np.random.default_rng(12)
    dates = pd.bdate_range("2020-01-01", periods=100)
    prices = pd.DataFrame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, (100, 3)), axis=0)), index=dates, columns=list("XYZ"))
    from quantkit import features as F
    from quantkit.labels import forward_return

    fwd = forward_return(prices, 5)
    vol = F.realized_volatility(prices, 20)
    scaled = MD.vol_scaled_target(fwd, vol)
    assert scaled.shape == fwd.shape
    valid = scaled.notna()
    np.testing.assert_allclose(scaled[valid].to_numpy().ravel(), (fwd / vol)[valid].to_numpy().ravel(), equal_nan=True)
    assert scaled.iloc[:19].isna().all().all()  # no vol yet -> no target (not filled)
    assert scaled.iloc[-5:].isna().all().all()  # no future yet
    zero_vol = vol.copy()
    zero_vol.iloc[30, 0] = 0.0
    assert np.isnan(MD.vol_scaled_target(fwd, zero_vol).iloc[30, 0])


def test_demeaned_target_is_market_neutral_per_date():
    rng = np.random.default_rng(13)
    dates = pd.bdate_range("2020-01-01", periods=10)
    fwd = pd.DataFrame(rng.normal(0.01, 0.02, (10, 5)), index=dates, columns=list("ABCDE"))
    fwd.iloc[2, 1:] = np.nan  # a date with a single asset
    d = MD.demeaned_target(fwd)
    means = d.drop(index=dates[2]).mean(axis=1)
    np.testing.assert_allclose(means.to_numpy(), 0.0, atol=1e-12)
    assert d.iloc[2].isna().all()  # min_count=2 -> undefined, not zero
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k target`
Expected: FAIL — `AttributeError: ... 'vol_scaled_target'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/models/target.py`:

```python
"""Target transforms — what the model is asked to predict.

Raw forward returns mix two things a cross-sectional model should not have to
learn: each asset's volatility level and the market's common move. Two causal
transforms remove them:

  * :func:`vol_scaled_target` divides the forward return by a trailing volatility
    known at ``t`` (the label stays "future"; only its *units* use the past), so
    high-vol names do not dominate the loss;
  * :func:`demeaned_target` subtracts each date's cross-sectional mean, so the
    model predicts *relative* performance — what a dollar-neutral book trades.

Neither fills gaps: where the scale or the cross-section is missing the target is NaN.
"""

from __future__ import annotations

import pandas as pd


def vol_scaled_target(fwd: pd.DataFrame, vol: pd.DataFrame, *, min_vol: float = 1e-8) -> pd.DataFrame:
    """``fwd / vol`` aligned on ``fwd``; NaN where ``vol`` is missing or ``<= min_vol``."""
    f, v = fwd.align(vol, join="left")
    v = v.where(v > min_vol)
    return f / v


def demeaned_target(fwd: pd.DataFrame, *, min_count: int = 2) -> pd.DataFrame:
    """Subtract each date's cross-sectional mean; dates with < ``min_count`` assets become NaN."""
    mean = fwd.mean(axis=1, skipna=True)
    enough = fwd.notna().sum(axis=1) >= min_count
    return fwd.sub(mean, axis=0).where(enough, other=float("nan"))
```

Export both from `models/__init__.py`.

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/target.py quantkit/src/quantkit/models/__init__.py quantkit/tests/test_models_rigor.py
git commit -m "feat(quantkit): vol-scaled and cross-sectionally demeaned targets"
```

---

### Task 11: Nested tuning (`TunedModel`)

**Files:**
- Create: `quantkit/src/quantkit/models/tuning.py`
- Modify: `quantkit/src/quantkit/models/__init__.py`
- Test: `quantkit/tests/test_models_rigor.py`

**Interfaces:**
- Consumes: `walk_forward`, `is_leakage_free` (backtest.split), `rank_ic` (Task 1), `subset_weights` (Task 6).
- Produces: `TunedModel(factory: Callable[..., Model], param_grid: dict[str, Sequence] | Sequence[dict], *, n_inner=3, horizon=0, embargo=0, scorer=None, mode="grid", n_iter=None, random_state=0)` implementing `Model`; after `fit`: `best_params_: dict`, `inner_scores_: pd.DataFrame` (columns `params`, `fold0..fold{n_inner-1}`, `mean`), `model_: Model`, `name = f"tuned[{model_.name}]"`. Static helper `TunedModel.inner_folds(unique_dates, *, n_inner, horizon, embargo) -> list[Fold]`.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_models_rigor.py`:

```python
# --- nested tuning ------------------------------------------------------------
def test_tuned_model_picks_the_informative_feature_and_records_scores():
    X, y, _ = _design(n_dates=150, n_assets=10, noise=0.3)
    X = X.assign(noise=np.random.default_rng(0).standard_normal(len(X)))
    tm = MD.TunedModel(MD.PersistenceModel, {"feature": ["noise", "a"]}, n_inner=3, horizon=2).fit(X, y)
    assert tm.best_params_ == {"feature": "a"}
    assert list(tm.inner_scores_.columns) == ["params", "fold0", "fold1", "fold2", "mean"]
    assert len(tm.inner_scores_) == 2 and tm.name == "tuned[persist[a]]"
    pd.testing.assert_series_equal(tm.predict(X), X["a"].rename("prediction"))


def test_tuned_model_inner_folds_are_leakage_free_and_inside_training_dates():
    X, y, dates = _design(n_dates=200, n_assets=5)
    train_dates = dates[:120]
    tr = X.index.get_level_values("date").isin(train_dates)
    folds = MD.TunedModel.inner_folds(train_dates, n_inner=3, horizon=5, embargo=2)
    assert len(folds) == 3
    for f in folds:
        assert B.is_leakage_free(f, train_dates, horizon=5)
        assert f.test[-1] <= train_dates[-1]
    log: list = []
    # the spy predicts constants (IC undefined) -> give the tuner a dummy scorer
    MD.TunedModel(lambda: _SpyModel(log), [{}], n_inner=3, horizon=5, embargo=2, scorer=lambda p, t: 0.0).fit(X[tr], y[tr])
    assert all(fit_d.max() <= train_dates[-1] and te.max() <= train_dates[-1] for fit_d, te in log)


def test_tuned_model_random_mode_and_walk_forward_integration():
    X, y, dates = _design(n_dates=300, n_assets=10, noise=0.5)
    grid = {"alpha": [0.01, 0.1, 1.0, 10.0]}
    tm = MD.TunedModel(MD.ridge, grid, mode="random", n_iter=2, random_state=1).fit(X, y)
    assert len(tm.inner_scores_) == 2
    folds = B.walk_forward(dates, train=150, test=50, horizon=1, embargo=1)
    pred = MD.walk_forward_predict(lambda: MD.TunedModel(MD.ridge, grid, n_inner=2, horizon=1), X, y, folds)
    assert MD.rank_ic(pred, y.loc[pred.index]) > 0.3
    short = X.index.get_level_values("date") < dates[20]
    with pytest.raises(ValueError, match="too few"):
        MD.TunedModel(MD.ridge, grid, n_inner=50).fit(X[short], y[short])
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_models_rigor.py -q -k tuned`
Expected: FAIL — `AttributeError: ... 'TunedModel'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/models/tuning.py`:

```python
"""Nested hyper-parameter tuning that stays inside the training window.

Choosing ``alpha`` by looking at the full sample is the quiet way to leak the test
period into the model. :class:`TunedModel` keeps the choice honest: inside
``fit`` it cuts the **training dates only** into an inner purged walk-forward
(:func:`quantkit.backtest.split.walk_forward`), scores every candidate parameter
set out-of-sample *within* training, refits the winner on the whole training
window, and exposes nothing else to the outer :func:`walk_forward_predict` — which
therefore becomes nested cross-validation without changing a line. The chosen
parameters and the inner score table are kept so the choice can be audited.

Cost: ``|candidates| × n_inner`` fits per outer fold. Keep grids small.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd

from ..backtest.split import Fold, walk_forward
from .base import Model, subset_weights
from .importance import rank_ic


class TunedModel(Model):
    """Pick ``factory(**params)`` by inner purged walk-forward score, then refit on all training rows."""

    def __init__(
        self,
        factory: Callable[..., Model],
        param_grid: dict[str, Sequence] | Sequence[dict],
        *,
        n_inner: int = 3,
        horizon: int = 0,
        embargo: int = 0,
        scorer: Callable[[pd.Series, pd.Series], float] | None = None,
        mode: str = "grid",
        n_iter: int | None = None,
        random_state: int = 0,
    ):
        if mode not in ("grid", "random"):
            raise ValueError("mode must be 'grid' or 'random'")
        if n_inner < 1:
            raise ValueError("n_inner must be >= 1")
        self.factory = factory
        self.param_grid = param_grid
        self.n_inner = n_inner
        self.horizon = horizon
        self.embargo = embargo
        self.scorer = scorer or rank_ic
        self.mode = mode
        self.n_iter = n_iter
        self.random_state = random_state
        self.name = "tuned"
        self.best_params_: dict | None = None
        self.inner_scores_: pd.DataFrame | None = None
        self.model_: Model | None = None

    # --- candidates -----------------------------------------------------------
    def candidates(self) -> list[dict]:
        """The parameter sets to try (full grid, or a seeded random subset)."""
        if isinstance(self.param_grid, dict):
            keys = list(self.param_grid)
            combos = [dict(zip(keys, vals, strict=True)) for vals in itertools.product(*(self.param_grid[k] for k in keys))]
        else:
            combos = [dict(p) for p in self.param_grid]
        if not combos:
            raise ValueError("param_grid produced no candidates")
        if self.mode == "random":
            k = min(self.n_iter or len(combos), len(combos))
            rng = np.random.default_rng(self.random_state)
            combos = [combos[i] for i in sorted(rng.choice(len(combos), size=k, replace=False))]
        return combos

    # --- inner folds ----------------------------------------------------------
    @staticmethod
    def inner_folds(unique_dates: pd.DatetimeIndex, *, n_inner: int, horizon: int, embargo: int) -> list[Fold]:
        """``n_inner`` equal test blocks after an equal initial train block, purged by ``horizon+embargo``."""
        n = len(unique_dates)
        gap = horizon + embargo
        test = (n - gap) // (n_inner + 1)
        if test < 1:
            raise ValueError(f"{n} training dates are too few for n_inner={n_inner} with gap={gap}")
        folds = walk_forward(unique_dates, train=test, test=test, horizon=horizon, embargo=embargo)
        return folds[:n_inner]

    # --- fit / predict --------------------------------------------------------
    def fit(self, X: pd.DataFrame, y: pd.Series, sample_weight: pd.Series | None = None) -> TunedModel:
        dates = X.index.get_level_values("date")
        unique = pd.DatetimeIndex(sorted(dates.unique()))
        folds = self.inner_folds(unique, n_inner=self.n_inner, horizon=self.horizon, embargo=self.embargo)
        rows: list[dict] = []
        for params in self.candidates():
            row: dict = {"params": params}
            for i, f in enumerate(folds):
                tr, te = dates.isin(f.train), dates.isin(f.test)
                if not tr.any() or not te.any():
                    row[f"fold{i}"] = float("nan")
                    continue
                m = self.factory(**params).fit(X[tr], y[tr], sample_weight=subset_weights(sample_weight, tr))
                row[f"fold{i}"] = float(self.scorer(m.predict(X[te]), y[te]))
            rows.append(row)
        table = pd.DataFrame(rows)
        fold_cols = [c for c in table.columns if c.startswith("fold")]
        table["mean"] = table[fold_cols].mean(axis=1)
        if table["mean"].isna().all():
            raise ValueError("every candidate scored NaN on the inner folds")
        self.inner_scores_ = table
        self.best_params_ = dict(table.loc[table["mean"].idxmax(), "params"])
        self.model_ = self.factory(**self.best_params_).fit(X, y, sample_weight=sample_weight)
        self.name = f"tuned[{self.model_.name}]"
        return self

    def predict(self, X: pd.DataFrame) -> pd.Series:
        if self.model_ is None:
            raise RuntimeError("TunedModel must be fit before predict")
        return self.model_.predict(X)
```

Export `TunedModel` from `models/__init__.py`; add one sentence to the `models/__init__.py` docstring: ":class:`~quantkit.models.tuning.TunedModel` selects hyper-parameters on an inner purged walk inside each training window (nested CV)."

- [ ] **Step 4: Run tests and lint**

Run: `uv run --no-sync pytest quantkit/tests -q && uv run --no-sync ruff check quantkit`
Expected: all PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/models/tuning.py quantkit/src/quantkit/models/__init__.py quantkit/tests/test_models_rigor.py
git commit -m "feat(quantkit): TunedModel — nested hyper-parameter search on an inner purged walk"
```

---

### Task 12: Real-data snapshot (`experiments/snapshot.py`)

**Files:**
- Create: `quantkit/src/quantkit/experiments/__init__.py`, `quantkit/src/quantkit/experiments/snapshot.py`
- Test: `quantkit/tests/test_experiments.py` (new)

**Interfaces:**
- Consumes: `quantkit.data` (`Connector`, `ConnectorError`, `get_prices`, `price_panel`), `quantkit.utils.paths.data_root`.
- Produces:
  - `SnapshotManifest` dataclass: `name, source, field, symbols: list[str], failed: dict[str, str], start: str, end: str, fetched_at: str, sha256: str, rows: int, n_assets: int, quality: dict[str, str], notes: list[str]`; `to_json() -> str`, `from_json(text) -> SnapshotManifest`.
  - `snapshot_dir(name) -> Path` = `<data root>/experiments/<name>`.
  - `sha256_of(path) -> str`.
  - `build_snapshot(name, symbols, start, end=None, *, source="auto", field="adj_close", connector: Connector | None = None, notes=()) -> SnapshotManifest` — writes `prices.parquet` + `manifest.json`.
  - `load_snapshot(name) -> tuple[pd.DataFrame, SnapshotManifest]` — verifies the sha256, raises `FileNotFoundError` / `ValueError`.

- [ ] **Step 1: Write the failing tests**

Create `quantkit/tests/test_experiments.py`:

```python
"""Experiments layer: snapshot (fetch once, hash, load offline), leaderboard
(every candidate on the same OOS walk, judged by DSR / IC-difference / PBO) and the
fingerprinted record. All offline: a fake connector stands in for the network and a
synthetic market has a planted, known edge.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from quantkit import backtest as B
from quantkit import experiments as EX
from quantkit import models as MD
from quantkit.data import CacheManager, Connector


class _FakeConnector(Connector):
    source = "fake"

    def __init__(self, cache, frames):
        super().__init__(cache=cache, retries=0)
        self.frames = frames

    def _download(self, symbol, start, end, **_):
        if symbol not in self.frames:
            raise RuntimeError(f"no such symbol {symbol}")
        return self.frames[symbol]

    def normalize(self, raw, symbol, **_):
        return raw


def _frames():
    idx = pd.bdate_range("2020-01-01", periods=40)
    a = pd.DataFrame({"close": np.linspace(100, 140, 40), "volume": 1.0}, index=idx)
    a["adj_close"] = a["close"]
    b = a.iloc[5:].copy() * 2  # lists later -> leading NaN in the panel, never filled
    return {"A": a, "B": b}


# --- snapshot -----------------------------------------------------------------
def test_build_snapshot_writes_prices_and_manifest_with_failures(tmp_path):
    conn = _FakeConnector(CacheManager(root=tmp_path / "cache"), _frames())
    m = EX.build_snapshot("t1", ["A", "B", "BAD"], "2020-01-01", "2020-03-01", connector=conn, notes=["synthetic"])
    assert m.symbols == ["A", "B"] and list(m.failed) == ["BAD"] and "no such symbol" in m.failed["BAD"]
    assert m.source == "fake" and m.n_assets == 2 and m.rows == 40 and m.notes == ["synthetic"]
    d = EX.snapshot_dir("t1")
    assert (d / "prices.parquet").exists() and (d / "manifest.json").exists()
    assert m.sha256 == hashlib.sha256((d / "prices.parquet").read_bytes()).hexdigest()
    on_disk = json.loads((d / "manifest.json").read_text())
    assert on_disk["sha256"] == m.sha256 and set(on_disk["quality"]) == {"A", "B"}


def test_load_snapshot_roundtrips_and_detects_tampering(tmp_path):
    conn = _FakeConnector(CacheManager(root=tmp_path / "cache"), _frames())
    m = EX.build_snapshot("t2", ["A", "B"], "2020-01-01", "2020-03-01", connector=conn)
    prices, m2 = EX.load_snapshot("t2")
    assert m2 == m and list(prices.columns) == ["A", "B"]
    assert isinstance(prices.index, pd.DatetimeIndex)
    assert prices["B"].isna().sum() == 5  # late listing stays NaN
    p = EX.snapshot_dir("t2") / "prices.parquet"
    prices.iloc[:-1].to_parquet(p)  # tamper
    with pytest.raises(ValueError, match="modified"):
        EX.load_snapshot("t2")
    with pytest.raises(FileNotFoundError):
        EX.load_snapshot("does-not-exist")


def test_build_snapshot_fails_loudly_when_nothing_fetched(tmp_path):
    conn = _FakeConnector(CacheManager(root=tmp_path / "cache"), {})
    from quantkit.data import ConnectorError

    with pytest.raises(ConnectorError, match="no symbol"):
        EX.build_snapshot("t3", ["X"], "2020-01-01", "2020-03-01", connector=conn)
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_experiments.py -q`
Expected: FAIL — `ImportError: cannot import name 'experiments' from 'quantkit'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/experiments/snapshot.py`:

```python
"""Real-data snapshots: fetch once, hash, then work offline.

A model comparison on live-fetched data cannot be re-run — free sources revise,
delist and drift. So an experiment starts by freezing its universe into a
parquet file plus a manifest (symbols, failures, fetch time, quality summaries
and the file's sha256). Everything downstream (:mod:`quantkit.experiments.leaderboard`,
the notebooks) reads the snapshot only, and :func:`load_snapshot` refuses a file
whose hash no longer matches the manifest. Symbols that fail to download are
recorded in ``failed`` — never silently dropped.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from ..data import Connector, ConnectorError, get_prices, price_panel
from ..utils import paths


@dataclass
class SnapshotManifest:
    """What was fetched, when, from where, how it looked — and the file's hash."""

    name: str
    source: str
    field: str
    symbols: list[str]
    failed: dict[str, str]
    start: str
    end: str
    fetched_at: str
    sha256: str
    rows: int
    n_assets: int
    quality: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> SnapshotManifest:
        return cls(**json.loads(text))


def snapshot_dir(name: str) -> Path:
    """``<data root>/experiments/<name>`` (the data root honours ``QUANTKIT_DATA_DIR``)."""
    return paths.data_root() / "experiments" / name


def sha256_of(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_snapshot(
    name: str,
    symbols: Iterable[str],
    start,
    end=None,
    *,
    source: str = "auto",
    field: str = "adj_close",
    connector: Connector | None = None,
    notes: Iterable[str] = (),
) -> SnapshotManifest:
    """Fetch ``symbols`` (via ``connector`` or :func:`quantkit.data.get_prices`), write the panel + manifest.

    Dates are the union across symbols with NaN where a symbol has no bar (no
    forward-fill). Failures are kept in the manifest; the call only raises when
    *nothing* could be fetched.
    """
    results, failed = {}, {}
    for sym in symbols:
        try:
            fr = connector.fetch(sym, start, end) if connector is not None else get_prices(sym, start, end, source=source)
        except ConnectorError as e:
            failed[sym] = str(e)
            continue
        results[sym] = fr
    if not results:
        raise ConnectorError(f"snapshot {name!r}: no symbol could be fetched ({len(failed)} failures)")
    prices = price_panel(results, field=field)
    d = snapshot_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    p = d / "prices.parquet"
    prices.to_parquet(p)
    manifest = SnapshotManifest(
        name=name,
        source=connector.source if connector is not None else source,
        field=field,
        symbols=list(results),
        failed=failed,
        start=str(pd.Timestamp(start).date()),
        end=str(pd.Timestamp(prices.index.max()).date()),
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
        sha256=sha256_of(p),
        rows=int(len(prices)),
        n_assets=int(prices.shape[1]),
        quality={s: r.quality.summary() for s, r in results.items()},
        notes=list(notes),
    )
    (d / "manifest.json").write_text(manifest.to_json(), encoding="utf-8")
    return manifest


def load_snapshot(name: str) -> tuple[pd.DataFrame, SnapshotManifest]:
    """Read a snapshot back; refuse it if ``prices.parquet`` no longer matches the manifest hash."""
    d = snapshot_dir(name)
    mp, pp = d / "manifest.json", d / "prices.parquet"
    if not (mp.exists() and pp.exists()):
        raise FileNotFoundError(f"snapshot {name!r} not found under {d}")
    manifest = SnapshotManifest.from_json(mp.read_text(encoding="utf-8"))
    actual = sha256_of(pp)
    if actual != manifest.sha256:
        raise ValueError(
            f"snapshot {name!r}: prices.parquet was modified "
            f"(sha256 {actual[:12]}… != manifest {manifest.sha256[:12]}…)"
        )
    prices = pd.read_parquet(pp)
    prices.index = pd.to_datetime(prices.index)
    return prices, manifest
```

Create `quantkit/src/quantkit/experiments/__init__.py`:

```python
"""quantkit.experiments — real-data model tournaments with a verdict you can defend.

:mod:`~quantkit.experiments.snapshot` freezes a universe (parquet + hashed manifest)
so a run is reproducible offline; :mod:`~quantkit.experiments.leaderboard` puts every
candidate on the same purged walk-forward and judges it with the statistics in
:mod:`quantkit.backtest.stats` (deflated Sharpe, paired IC difference, PBO);
:mod:`~quantkit.experiments.record` writes the result with a fingerprint (git sha,
snapshot hash, config hashes, versions). Losers stay in the table — that is the point.
"""

from __future__ import annotations

from .snapshot import SnapshotManifest, build_snapshot, load_snapshot, sha256_of, snapshot_dir

__all__ = [
    "SnapshotManifest",
    "build_snapshot",
    "load_snapshot",
    "sha256_of",
    "snapshot_dir",
]
```

Register the package in `quantkit/src/quantkit/__init__.py` if it lists subpackages (read it first; if it only holds a docstring/version, nothing to do).

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_experiments.py -q`
Expected: 3 PASS.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/experiments quantkit/tests/test_experiments.py
git commit -m "feat(quantkit): experiments.snapshot — hashed real-data snapshots for offline reruns"
```

---

### Task 13: Leaderboard runner (`experiments/leaderboard.py`)

**Files:**
- Create: `quantkit/src/quantkit/experiments/leaderboard.py`
- Modify: `quantkit/src/quantkit/experiments/__init__.py`
- Test: `quantkit/tests/test_experiments.py`

**Interfaces:**
- Consumes: Tasks 1–5 (`rank_ic_by_date`, `bootstrap_series`, `ic_difference`, `deflated_sharpe`, `sharpe_moments`, `pbo`), existing `make_design`, `walk_forward_predict`, `predictions_to_panel`, `cross_sectional_zscore`, `long_short_quantile`, `run_backtest`, `buy_and_hold`, `summary`, `forward_return`.
- Produces:
  - `predictions_to_backtest(pred, rets, *, horizon, quantile, cost, lag=1) -> BacktestResult` — z-score → L/S quantile weights rebalanced every `horizon` bars → backtest.
  - `LeaderboardResult(table: pd.DataFrame, predictions: dict[str, pd.Series], backtests: dict[str, BacktestResult], daily_ic: pd.DataFrame, pbo: PBOResult | None, settings: dict)`. `table` index name `candidate`; columns `ic_mean, ic_lo, ic_hi, ic_diff_vs_ref, ic_diff_lo, ic_diff_hi, sharpe, ann_return, max_drawdown, ann_turnover, dsr, n_oos_dates, pbo, beats_baseline`; includes an `equal_weight` row (Sharpe/return/DD only).
  - `run_leaderboard(prices, candidates, *, features, horizon, folds, cost, reference, quantile=0.3, n_boot=1000, block=None, pbo_groups=8, dsr_threshold=0.95, pbo_threshold=0.5, periods=252, random_state=0) -> LeaderboardResult`.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_experiments.py`:

```python
# --- leaderboard --------------------------------------------------------------
def _predictable_market(n_dates=600, n_assets=20, seed=21):
    """Tomorrow's return = 0.01 * today's `sig` + noise; `noise`/`half` are weaker features."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2017-01-01", periods=n_dates)
    assets = [f"A{i:02d}" for i in range(n_assets)]
    sig = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    noise = pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    half = sig + 2.0 * pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    rets = 0.01 * sig.shift(1) + 0.01 * pd.DataFrame(rng.standard_normal((n_dates, n_assets)), index=dates, columns=assets)
    rets.iloc[0] = 0.0
    prices = 100.0 * (1.0 + rets).cumprod()
    return prices, {"sig": sig, "noise": noise, "half": half}, dates


def test_predictions_to_backtest_rebalances_every_horizon_bars():
    from quantkit.labels import forward_return

    prices, feats, dates = _predictable_market(n_dates=120, n_assets=8)
    X, y = MD.make_design(feats, forward_return(prices, 5))
    pred = X["sig"].rename("prediction")
    res = EX.predictions_to_backtest(pred, prices.pct_change(fill_method=None), horizon=5, quantile=0.25, cost=B.CostModel(5, 2))
    changes = (res.weights.diff().abs().sum(axis=1) > 1e-12).sum()
    assert changes <= len(res.weights) / 5 + 2  # held between rebalances, not re-decided daily
    assert res.meta["lag"] == 1


def test_run_leaderboard_flags_planted_edges_and_keeps_losers():
    prices, feats, dates = _predictable_market()
    folds = B.walk_forward(dates, train=200, test=50, horizon=1, embargo=1)
    candidates = {
        "persist_noise": lambda: MD.PersistenceModel("noise"),
        "mean": MD.MeanModel,
        "persist_half": lambda: MD.PersistenceModel("half"),
        "persist_sig": lambda: MD.PersistenceModel("sig"),
    }
    res = EX.run_leaderboard(
        prices, candidates, features=feats, horizon=1, folds=folds, cost=B.CostModel(5, 2),
        reference="persist_noise", n_boot=200, pbo_groups=8,
    )
    t = res.table
    assert t.index.name == "candidate" and set(t.index) == {*candidates, "equal_weight"}
    assert t.loc["persist_sig", "beats_baseline"] and t.loc["persist_half", "beats_baseline"]
    assert not t.loc["persist_noise", "beats_baseline"] and not t.loc["mean", "beats_baseline"]
    assert not t.loc["equal_weight", "beats_baseline"]
    assert t.loc["persist_sig", "ic_mean"] > 0.5 and t.loc["persist_sig", "dsr"] > 0.99
    assert np.isnan(t.loc["mean", "ic_mean"])  # constant prediction: IC undefined, not 0
    assert t.loc["persist_sig", "ic_diff_lo"] > 0 and t.loc["persist_noise", "ic_diff_vs_ref"] == 0.0
    assert res.pbo is not None and res.pbo.n_candidates == 3 and res.pbo.pbo < 0.2  # 'mean' dropped
    assert (t["pbo"].dropna() == res.pbo.pbo).all()
    assert res.daily_ic.shape[1] == 4 and res.daily_ic.index.name == "date"
    test_dates = pd.DatetimeIndex(np.concatenate([f.test.values for f in folds]))
    for p in res.predictions.values():
        assert set(p.index.get_level_values("date")) <= set(test_dates)
    assert res.settings["horizon"] == 1 and res.settings["n_candidates"] == 4


def test_run_leaderboard_validates_reference():
    prices, feats, dates = _predictable_market(n_dates=150, n_assets=6)
    folds = B.walk_forward(dates, train=60, test=30, horizon=1)
    with pytest.raises(KeyError):
        EX.run_leaderboard(prices, {"a": MD.MeanModel, "b": MD.MeanModel}, features=feats, horizon=1, folds=folds, cost=B.CostModel(), reference="zzz")
    with pytest.raises(ValueError):
        EX.run_leaderboard(prices, {"a": MD.MeanModel}, features=feats, horizon=1, folds=folds, cost=B.CostModel(), reference="a")
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_experiments.py -q -k leaderboard`
Expected: FAIL — `AttributeError: module 'quantkit.experiments' has no attribute 'predictions_to_backtest'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/experiments/leaderboard.py`:

```python
"""Model leaderboard — every candidate on the same purged walk, judged by three tests.

For each candidate factory: walk-forward OOS predictions → daily rank IC → L/S
quantile weights rebalanced every ``horizon`` bars → the same backtest engine and
cost model. Then, across candidates:

  * **DSR** (:func:`quantkit.backtest.stats.deflated_sharpe`) with ``N`` = number of
    candidates and the variance of their Sharpes — the tournament sets its own bar;
  * **paired IC difference** vs the ``reference`` (a Tier-0 baseline) with a
    block-bootstrap interval;
  * **PBO** (:func:`quantkit.backtest.stats.pbo`) on the dates × candidates matrix of
    daily IC.

``beats_baseline`` is True only when all three agree (DSR ≥ threshold, IC-difference
interval above 0, PBO < threshold). Every candidate stays in the table, including
the reference and an equal-weight benchmark — losing is a result too.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..backtest import BacktestResult, CostModel, Fold, buy_and_hold, run_backtest, summary
from ..backtest.stats import PBOResult, bootstrap_series, deflated_sharpe, ic_difference, pbo, sharpe_moments
from ..features.price import cross_sectional_zscore
from ..labels import forward_return
from ..models import Model, make_design, predictions_to_panel, rank_ic_by_date, walk_forward_predict
from ..signals.normalize import long_short_quantile


@dataclass
class LeaderboardResult:
    """The verdict table plus everything needed to audit it."""

    table: pd.DataFrame
    predictions: dict[str, pd.Series]
    backtests: dict[str, BacktestResult]
    daily_ic: pd.DataFrame
    pbo: PBOResult | None
    settings: dict = field(default_factory=dict)


def predictions_to_backtest(
    pred: pd.Series,
    rets: pd.DataFrame,
    *,
    horizon: int,
    quantile: float,
    cost: CostModel,
    lag: int = 1,
) -> BacktestResult:
    """OOS predictions → cross-sectional z-score → dollar-neutral L/S quantile weights → backtest.

    Weights are re-decided every ``horizon`` bars (matching the label) and held in
    between; daily re-decision of a ``horizon``-bar forecast churns the book and
    lets costs eat the signal (NB07's lesson).
    """
    panel = predictions_to_panel(pred)
    score = cross_sectional_zscore(panel)
    w_h = long_short_quantile(score.iloc[::horizon], quantile)
    w = w_h.reindex(panel.index, method="ffill")
    return run_backtest(w, rets.reindex(panel.index), cost_model=cost, lag=lag)


def run_leaderboard(
    prices: pd.DataFrame,
    candidates: dict[str, Callable[[], Model]],
    *,
    features: dict[str, pd.DataFrame],
    horizon: int,
    folds: list[Fold],
    cost: CostModel,
    reference: str,
    quantile: float = 0.3,
    n_boot: int = 1000,
    block: int | None = None,
    pbo_groups: int = 8,
    dsr_threshold: float = 0.95,
    pbo_threshold: float = 0.5,
    periods: int = 252,
    random_state: int = 0,
) -> LeaderboardResult:
    """Run every candidate on ``folds`` and return the judged table (see module docstring).

    ``reference`` must be one of ``candidates`` (a Tier-0 baseline). ``block``
    defaults to ``max(horizon, 5)`` so overlapping-label autocorrelation stays
    inside a bootstrap block. ``periods`` is bars per year (252 equities, 365 crypto).
    """
    if reference not in candidates:
        raise KeyError(f"reference {reference!r} is not a candidate: {list(candidates)}")
    if len(candidates) < 2:
        raise ValueError("need the reference and at least one challenger")
    block = block or max(horizon, 5)
    X, y = make_design(features, forward_return(prices, horizon))
    rets = prices.pct_change(fill_method=None)

    preds: dict[str, pd.Series] = {}
    daily: dict[str, pd.Series] = {}
    for name, factory in candidates.items():
        p = walk_forward_predict(factory, X, y, folds)
        if p.empty:
            raise ValueError(f"{name}: no out-of-sample predictions (folds do not overlap the design dates)")
        preds[name] = p
        daily[name] = rank_ic_by_date(p, y.loc[p.index])
    daily_ic = pd.DataFrame(daily).sort_index()
    daily_ic.index = pd.DatetimeIndex(daily_ic.index, name="date")

    oos_start = min(p.index.get_level_values("date").min() for p in preds.values())
    rets_oos = rets.loc[rets.index >= oos_start]
    backtests = {
        name: predictions_to_backtest(p, rets_oos, horizon=horizon, quantile=quantile, cost=cost)
        for name, p in preds.items()
    }

    srs = np.array([sharpe_moments(b.returns)[0] for b in backtests.values()], dtype="float64")
    finite = srs[np.isfinite(srs)]
    sr_var = float(np.var(finite, ddof=1)) if finite.size > 1 else 0.0

    pbo_res: PBOResult | None = None
    usable = daily_ic.dropna(axis=1, how="all")
    if usable.shape[1] >= 2 and len(usable.dropna(how="any")) >= pbo_groups:
        pbo_res = pbo(usable, n_groups=pbo_groups)

    rows: dict[str, dict] = {}
    for name in candidates:
        ic = bootstrap_series(daily_ic[name], n_boot=n_boot, block=block, random_state=random_state)
        diff = ic_difference(preds[name], preds[reference], y, n_boot=n_boot, block=block, random_state=random_state)
        s = summary(backtests[name], periods)
        rows[name] = {
            "ic_mean": ic.mean,
            "ic_lo": ic.lo,
            "ic_hi": ic.hi,
            "ic_diff_vs_ref": diff.mean,
            "ic_diff_lo": diff.lo,
            "ic_diff_hi": diff.hi,
            "sharpe": s["sharpe"],
            "ann_return": s["ann_return"],
            "max_drawdown": s["max_drawdown"],
            "ann_turnover": s["ann_turnover"],
            "dsr": deflated_sharpe(backtests[name].returns, n_trials=len(candidates), sr_var=sr_var),
            "n_oos_dates": ic.n,
        }
    bench = summary(buy_and_hold(rets_oos), periods)
    rows["equal_weight"] = {
        "sharpe": bench["sharpe"],
        "ann_return": bench["ann_return"],
        "max_drawdown": bench["max_drawdown"],
    }
    table = pd.DataFrame.from_dict(rows, orient="index")
    table.index.name = "candidate"
    table["pbo"] = pbo_res.pbo if pbo_res is not None else np.nan
    beats = (table["dsr"] >= dsr_threshold) & (table["ic_diff_lo"] > 0) & (table["pbo"] < pbo_threshold)
    beats.loc[[reference, "equal_weight"]] = False
    table["beats_baseline"] = beats.astype(bool)

    settings = {
        "horizon": horizon,
        "quantile": quantile,
        "n_folds": len(folds),
        "n_candidates": len(candidates),
        "reference": reference,
        "cost_bps": cost.cost_bps,
        "slippage_bps": cost.slippage_bps,
        "n_boot": n_boot,
        "block": block,
        "pbo_groups": pbo_groups,
        "dsr_threshold": dsr_threshold,
        "pbo_threshold": pbo_threshold,
        "periods": periods,
        "sr_var": sr_var,
        "oos_start": str(pd.Timestamp(oos_start).date()),
        "features": list(features),
        "n_assets": int(prices.shape[1]),
    }
    return LeaderboardResult(table, preds, backtests, daily_ic, pbo_res, settings)
```

Add to `experiments/__init__.py`: `from .leaderboard import LeaderboardResult, predictions_to_backtest, run_leaderboard` and the three names to `__all__`.

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest quantkit/tests/test_experiments.py -q`
Expected: all PASS (the leaderboard test takes a few seconds).

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/experiments quantkit/tests/test_experiments.py
git commit -m "feat(quantkit): experiments.leaderboard — DSR / paired IC / PBO verdict on one OOS walk"
```

---

### Task 14: Fingerprinted experiment record (`experiments/record.py`)

**Files:**
- Create: `quantkit/src/quantkit/experiments/record.py`
- Modify: `quantkit/src/quantkit/experiments/__init__.py`
- Test: `quantkit/tests/test_experiments.py`

**Interfaces:**
- Produces:
  - `fingerprint(*, manifest_sha256: str | None = None, config_paths: Iterable[Path] = ()) -> dict[str, str]` with keys `git_sha`, `python`, `created_at`, `version_<pkg>` for `quantkit, pandas, numpy, scikit-learn, scipy, lightgbm, torch` (`"not installed"` when absent), `snapshot_sha256` (if given), `config_<filename>` sha256 per path.
  - `ExperimentRecord(name: str, fingerprint: dict, settings: dict, table: list[dict], notes: list[str])` with `to_frame() -> pd.DataFrame` (index `candidate`).
  - `make_record(name, result: LeaderboardResult, *, manifest_sha256=None, config_paths=(), notes=()) -> ExperimentRecord`
  - `save_record(record, path) -> Path`, `load_record(path) -> ExperimentRecord`.

- [ ] **Step 1: Write the failing tests**

Append to `quantkit/tests/test_experiments.py`:

```python
# --- record -------------------------------------------------------------------
def test_fingerprint_has_git_versions_and_config_hashes(tmp_path):
    cfg = tmp_path / "x.yaml"
    cfg.write_text("a: 1\n")
    fp = EX.fingerprint(manifest_sha256="abc", config_paths=[cfg])
    assert fp["git_sha"] == "unknown" or (len(fp["git_sha"]) == 40 and all(c in "0123456789abcdef" for c in fp["git_sha"]))
    assert fp["version_scikit-learn"] not in ("", "not installed") and fp["version_quantkit"]
    assert fp["snapshot_sha256"] == "abc"
    assert fp["config_x.yaml"] == hashlib.sha256(cfg.read_bytes()).hexdigest()
    assert "created_at" in fp and "python" in fp


def test_record_roundtrip_preserves_the_verdict_table(tmp_path):
    prices, feats, dates = _predictable_market(n_dates=300, n_assets=10)
    folds = B.walk_forward(dates, train=100, test=50, horizon=1, embargo=1)
    res = EX.run_leaderboard(
        prices, {"ref": lambda: MD.PersistenceModel("noise"), "sig": lambda: MD.PersistenceModel("sig")},
        features=feats, horizon=1, folds=folds, cost=B.CostModel(5, 2), reference="ref", n_boot=50, pbo_groups=4,
    )
    rec = EX.make_record("unit", res, manifest_sha256="deadbeef", notes=["synthetic"])
    path = EX.save_record(rec, tmp_path / "reports" / "unit.json")
    assert path.exists()
    back = EX.load_record(path)
    assert back.name == "unit" and back.notes == ["synthetic"] and back.fingerprint["snapshot_sha256"] == "deadbeef"
    frame = back.to_frame()
    assert frame.index.name == "candidate" and set(frame.index) == {"ref", "sig", "equal_weight"}
    assert bool(frame.loc["sig", "beats_baseline"]) == bool(res.table.loc["sig", "beats_baseline"])
    assert frame.loc["sig", "sharpe"] == pytest.approx(res.table.loc["sig", "sharpe"])
    assert back.settings["horizon"] == 1
    raw = json.loads(path.read_text())
    assert raw["table"][0]["candidate"] in {"ref", "sig", "equal_weight"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest quantkit/tests/test_experiments.py -q -k "fingerprint or record"`
Expected: FAIL — `AttributeError: ... 'fingerprint'`.

- [ ] **Step 3: Implement**

Create `quantkit/src/quantkit/experiments/record.py`:

```python
"""Fingerprinted experiment records — a leaderboard you can trace back to its inputs.

A verdict table is worthless without knowing which code, which data and which
settings produced it. :func:`make_record` bundles the table with a fingerprint
(git sha, snapshot sha256, config hashes, package versions, timestamp) and the
run settings, and :func:`save_record` writes JSON small enough to commit under
``reports/experiments/``. Loading gives the table back as a DataFrame.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path

import pandas as pd

from ..utils.paths import REPO_ROOT
from .leaderboard import LeaderboardResult

_PACKAGES = ("quantkit", "pandas", "numpy", "scikit-learn", "scipy", "lightgbm", "torch")


def _git_sha(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True, timeout=10
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _version(pkg: str) -> str:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return "not installed"


def fingerprint(*, manifest_sha256: str | None = None, config_paths: Iterable[Path] = ()) -> dict[str, str]:
    """Code + data + environment identifiers for one run."""
    fp = {
        "git_sha": _git_sha(REPO_ROOT),
        "python": platform.python_version(),
        "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    for pkg in _PACKAGES:
        fp[f"version_{pkg}"] = _version(pkg)
    if manifest_sha256:
        fp["snapshot_sha256"] = manifest_sha256
    for p in config_paths:
        p = Path(p)
        fp[f"config_{p.name}"] = hashlib.sha256(p.read_bytes()).hexdigest()
    return fp


@dataclass
class ExperimentRecord:
    """A leaderboard table with the fingerprint and settings that produced it."""

    name: str
    fingerprint: dict[str, str]
    settings: dict
    table: list[dict]
    notes: list[str] = field(default_factory=list)

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.table).set_index("candidate")


def make_record(
    name: str,
    result: LeaderboardResult,
    *,
    manifest_sha256: str | None = None,
    config_paths: Iterable[Path] = (),
    notes: Iterable[str] = (),
) -> ExperimentRecord:
    """Bundle ``result.table`` + settings with a fresh :func:`fingerprint`."""
    rows = json.loads(result.table.reset_index().to_json(orient="records", date_format="iso"))
    settings = json.loads(json.dumps(result.settings, default=str))
    return ExperimentRecord(
        name=name,
        fingerprint=fingerprint(manifest_sha256=manifest_sha256, config_paths=config_paths),
        settings=settings,
        table=rows,
        notes=list(notes),
    )


def save_record(record: ExperimentRecord, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def load_record(path: Path) -> ExperimentRecord:
    return ExperimentRecord(**json.loads(Path(path).read_text(encoding="utf-8")))
```

Add to `experiments/__init__.py`: `from .record import ExperimentRecord, fingerprint, load_record, make_record, save_record` and the names to `__all__` (sorted).

- [ ] **Step 4: Run tests and lint**

Run: `uv run --no-sync pytest quantkit/tests -q && uv run --no-sync ruff check quantkit`
Expected: all PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add quantkit/src/quantkit/experiments quantkit/tests/test_experiments.py
git commit -m "feat(quantkit): experiments.record — fingerprinted JSON leaderboard records"
```

---

### Task 15: Universes, NB17 (real data), committed records

**Files:**
- Modify: `quantkit/configs/universe.yaml` (append `experiments:`)
- Create: `quantkit/notebooks/17_real_data_model_leaderboard.ipynb` (generated, then executed in place)
- Create: `quantkit/reports/experiments/leaderboard_{us,crypto}_h{5,21}.json` (produced by the notebook)

**Interfaces:**
- Consumes: everything from Tasks 1–14; `quantkit.utils.config.load_config("universe")["experiments"]`; `CostModel.from_config(load_config("backtest_config"))`.
- Produces: four JSON records and an executed notebook. No library code.

**Network:** the snapshot cell downloads once (yfinance for US, Binance for crypto). Everything after it reads the snapshot. If a source is unreachable, the manifest records the failures — do not hand-edit the universe to hide them.

- [ ] **Step 1: Add the experiment universes**

Append to `quantkit/configs/universe.yaml`:

```yaml

# Real-data model leaderboard (notebooks/17). Hand-picked survivors as of 2026-09 —
# survivorship-biased BY CONSTRUCTION; every result that uses these must say so.
experiments:
  us:
    source: yfinance          # Stooq's JS wall is unreliable; yfinance is the free fallback
    start: "2010-01-01"
    periods: 252
    symbols: [SPY, QQQ, IWM, DIA, TLT, IEF, SHY, HYG, LQD, GLD, USO,
              XLF, XLK, XLE, XLV, XLY, XLP, XLI, XLU, XLRE, XLB,
              AAPL, MSFT, AMZN, GOOGL, META, NVDA, TSLA, BRK-B, JPM, JNJ,
              V, PG, UNH, HD, MA, XOM, CVX, PFE, KO, PEP,
              MRK, ABBV, BAC, WMT, COST, DIS, CSCO, ADBE, CRM, NFLX,
              INTC, AMD, QCOM, TXN, ORCL, IBM, MCD, NKE, CAT, GS]
    note: "21 ETFs + 40 large caps that exist today (survivorship bias). Late listings (META 2012, XLRE 2015) are NaN before listing, never filled."
  crypto:
    source: binance
    start: "2018-01-01"
    periods: 365              # crypto trades every calendar day
    symbols: [BTCUSDT, ETHUSDT, BNBUSDT, XRPUSDT, SOLUSDT, ADAUSDT, DOGEUSDT, TRXUSDT, LINKUSDT, AVAXUSDT,
              DOTUSDT, LTCUSDT, BCHUSDT, XLMUSDT, ATOMUSDT, ETCUSDT, FILUSDT, NEARUSDT, UNIUSDT, APTUSDT]
    note: "Binance USDT pairs with the largest volume as of 2026-09 (survivorship bias); many list after 2018 -> leading NaN."
```

Verify: `uv run --no-sync python -c "from quantkit.utils.config import load_config; e=load_config('universe')['experiments']; print(len(e['us']['symbols']), len(e['crypto']['symbols']))"` → `61 20`.

- [ ] **Step 2: Generate the notebook**

Run from the workspace root (`uv run --no-sync python - <<'EOF' ... EOF`):

```python
import nbformat as nbf
from pathlib import Path

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = []

cells.append(md("""# 17 実データ leaderboard — モデルはベースラインに勝ったと言えるか

Tier0–3 と合成モデル(ensemble / purged stacking / LTR / nested TunedModel)を **同じ purged walk-forward** に乗せ、
`quantkit.experiments.run_leaderboard` が 3 つの検定で判定する:

| 検定 | 問い | 閾値 |
|---|---|---|
| **DSR**(deflated Sharpe) | 候補 N 個の中の最良は、N 個の**ノイズ戦略**の最良より良いか | ≥ 0.95 |
| **IC 差の bootstrap CI**(対応あり) | Tier0 参照(`persist[mom]`)との日次 IC 差は 0 と区別できるか | 下限 > 0 |
| **PBO**(CSCV) | IS で最良を選ぶと OOS で中位より下に落ちる確率 | < 0.5 |

3 つすべてを満たしたときだけ `beats_baseline=True`。**負けた候補も表に残す**。

ユニバースは `configs/universe.yaml` の `experiments:`(米株 ETF+大型株 / crypto)。**手選びの現存銘柄＝サバイバーシップバイアス**があり、
無料データの調整・欠損の限界もそのまま載る。投資助言ではない。"""))

cells.append(code("""import time
import numpy as np
import pandas as pd
from quantkit import backtest as B, experiments as EX, features as F, models as MD
from quantkit.utils.config import load_config
from quantkit.utils.paths import CONFIG_DIR, REPO_ROOT

UNI = load_config('universe')['experiments']
COST = B.CostModel.from_config(load_config('backtest_config'))
REPORTS = REPO_ROOT / 'reports' / 'experiments'; REPORTS.mkdir(parents=True, exist_ok=True)
HORIZONS = (5, 21)
FAST = False   # True: 重い候補(stacking / tuned / mlp)を落として配線だけ確認
print('cost model:', COST, '| horizons:', HORIZONS)"""))

cells.append(md("""## Snapshot — 一度だけ取得し、以後はハッシュ検証つきでオフライン再利用

`build_snapshot` は `data/experiments/<name>/prices.parquet` と `manifest.json`(銘柄・失敗・取得時刻・sha256・品質要約)を書く。
既にあれば `load_snapshot` が sha256 を検証して読む。取得に失敗した銘柄は manifest の `failed` に残す(黙って落とさない)。"""))

cells.append(code("""snapshots = {}
for name, cfg in UNI.items():
    try:
        prices, manifest = EX.load_snapshot(name)
    except FileNotFoundError:
        manifest = EX.build_snapshot(name, cfg['symbols'], cfg['start'], source=cfg['source'], notes=[cfg['note']])
        prices, manifest = EX.load_snapshot(name)
    snapshots[name] = (prices, manifest)
    print(f"{name:7s} {manifest.source:9s} {manifest.start}..{manifest.end}  assets={manifest.n_assets} rows={manifest.rows} "
          f"failed={list(manifest.failed)} sha={manifest.sha256[:12]}  fetched={manifest.fetched_at}")"""))

cells.append(md("""## 特徴量と候補

特徴量は NB07 と同じ causal な 4 本(`mom_120_20` / `z_20` / `rvol_20` / `ma_ratio_50`)。参照は Tier0 の `persist[mom]`。
`stacking` は **purged**(`horizon`, `embargo=5`)、`tuned[*]` は各 fold の学習期間内で内側 walk-forward により選ぶ(nested)。"""))

cells.append(code("""def features_for(prices):
    return {
        'mom_120_20': F.momentum(prices, lookback=120, skip=20),
        'z_20': F.rolling_zscore(prices, 20),
        'rvol_20': F.realized_volatility(prices, 20),
        'ma_ratio_50': F.ma_ratio(prices, 50),
    }

def candidates_for(H):
    gbr = lambda: MD.gradient_boosting(n_estimators=100, max_depth=3)
    c = {
        'persist[mom]': lambda: MD.PersistenceModel('mom_120_20'),
        'mean': MD.MeanModel,
        'ridge': lambda: MD.ridge(1.0),
        'random_forest': lambda: MD.random_forest(n_estimators=150, max_depth=3),
        'gradient_boosting': gbr,
        'ltr[ridge]': lambda: MD.learning_to_rank(MD.ridge, alpha=1.0),
        'ensemble[ridge+gbr]': lambda: MD.EnsembleModel([MD.ridge(1.0), gbr()]),
    }
    if not FAST:
        c.update({
            'mlp': lambda: MD.mlp(hidden_layer_sizes=(32, 16), max_iter=300),
            'stacking[purged]': lambda: MD.StackingModel([lambda: MD.ridge(1.0), gbr], lambda: MD.ridge(1.0), n_splits=4, horizon=H, embargo=5),
            'tuned[ridge]': lambda: MD.TunedModel(MD.ridge, {'alpha': [0.1, 1.0, 10.0, 100.0]}, n_inner=3, horizon=H, embargo=5),
            'tuned[gbr]': lambda: MD.TunedModel(MD.gradient_boosting, {'max_depth': [2, 3], 'n_estimators': [100]}, n_inner=2, horizon=H, embargo=5),
        })
    return c

print(list(candidates_for(5)))"""))

cells.append(md("""## 実行 — ユニバース × horizon ごとに leaderboard を出し、fingerprint 付き JSON を `reports/experiments/` に保存"""))

cells.append(code("""results = {}
for name, (prices, manifest) in snapshots.items():
    periods = UNI[name]['periods']
    for H in HORIZONS:
        t0 = time.perf_counter()
        folds = B.walk_forward(prices.index, train=504, test=252, horizon=H, embargo=5)
        res = EX.run_leaderboard(
            prices, candidates_for(H), features=features_for(prices), horizon=H, folds=folds, cost=COST,
            reference='persist[mom]', quantile=0.3, n_boot=1000, pbo_groups=8, periods=periods,
        )
        key = f'leaderboard_{name}_h{H}'
        rec = EX.make_record(
            key, res, manifest_sha256=manifest.sha256,
            config_paths=[CONFIG_DIR / 'universe.yaml', CONFIG_DIR / 'backtest_config.yaml'],
            notes=[manifest.notes[0] if manifest.notes else '', f'wall_seconds={time.perf_counter() - t0:.0f}'],
        )
        EX.save_record(rec, REPORTS / f'{key}.json')
        results[key] = res
        print(f'=== {key}: {len(folds)} folds, OOS from {res.settings["oos_start"]}, PBO={res.pbo.pbo if res.pbo else float("nan"):.2f}, '
              f'{time.perf_counter() - t0:.0f}s')
        cols = ['ic_mean', 'ic_lo', 'ic_hi', 'ic_diff_vs_ref', 'ic_diff_lo', 'sharpe', 'max_drawdown', 'ann_turnover', 'dsr', 'pbo', 'beats_baseline']
        print(res.table[cols].round(3).to_string())
        print()"""))

cells.append(md("""## 結果の読み方

- `beats_baseline` が True の候補だけが「Tier0 参照に勝った」と言える。False は **「勝てなかった」という結果**であり、消さない。
- `dsr` は候補数 N(この表の行数)で割り引いた値。候補を増やすほど閾値は上がる(次の NB18 で N が増えると判定は厳しくなる)。
- `pbo` は表全体に一つ(候補の中から IS 最良を選ぶ行為の過学習確率)。近い実力の候補が複数あると 0.5 に寄るのは PBO の性質。
- 数字の限界: 手選びユニバース(サバイバーシップ)・無料データの調整差・コスト/スリッページは config の仮定・税/制約は未考慮。"""))

cells.append(code("""verdict = pd.DataFrame({k: r.table['beats_baseline'] for k, r in results.items()}).fillna(False).astype(bool)
verdict['n_wins'] = verdict.sum(axis=1)
print(verdict.sort_values('n_wins', ascending=False).to_string())
print()
print('records:', sorted(p.name for p in REPORTS.glob('leaderboard_*.json')))"""))

nb["cells"] = cells
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
Path("quantkit/notebooks/17_real_data_model_leaderboard.ipynb").write_text(nbf.writes(nb), encoding="utf-8")
print("written")
```

- [ ] **Step 3: Smoke-run with FAST=True (network happens here)**

Temporarily set `FAST = True` (edit the JSON string in the notebook, or `sed -i 's/FAST = False/FAST = True/'`), then:

```bash
uv run --no-sync jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 \
  quantkit/notebooks/17_real_data_model_leaderboard.ipynb
```

Expected: the snapshot cell prints two manifests (US ≈ 61 assets, crypto = 20, `failed=[]` or a short list), each leaderboard prints a table, four JSON files appear under `quantkit/reports/experiments/`. If a symbol fails, leave it in `failed` — do not edit the universe to make the list empty. If **all** US symbols fail (yfinance blocked), stop and report; do not substitute synthetic data.

- [ ] **Step 4: Full run**

Set `FAST = False` back and re-run the same `nbconvert` command. Expect roughly 1–2 hours in total (GBR/stacking/tuned on ~60 assets × ~4000 days dominate). Note each run's `wall_seconds` is stored in the record notes.

- [ ] **Step 5: Verify outputs are saved and honest**

```bash
uv run --no-sync python - <<'EOF'
import json, glob
nb = json.load(open("quantkit/notebooks/17_real_data_model_leaderboard.ipynb"))
n_out = sum(len(c.get("outputs", [])) for c in nb["cells"] if c["cell_type"] == "code")
assert n_out >= 5, n_out
for p in sorted(glob.glob("quantkit/reports/experiments/leaderboard_*.json")):
    r = json.load(open(p))
    wins = [row["candidate"] for row in r["table"] if row.get("beats_baseline")]
    print(p, "| git", r["fingerprint"]["git_sha"][:8], "| snapshot", r["fingerprint"]["snapshot_sha256"][:8], "| wins:", wins)
EOF
```

Expected: 4 files listed with fingerprints; `wins` may well be empty — that is a valid, reportable outcome.

- [ ] **Step 6: Commit**

```bash
git add quantkit/configs/universe.yaml quantkit/notebooks/17_real_data_model_leaderboard.ipynb quantkit/reports/experiments/
git commit -m "feat(quantkit): NB17 real-data model leaderboard (US ETFs+large caps, crypto) with fingerprinted records"
```

(`quantkit/data/experiments/` is gitignored by `data/*/*` — the snapshot itself is not committed; the manifest hash in each record is what ties the result to the data.)

---

### Task 16: Re-execute NB07–09, update README, final verification

**Files:**
- Modify (execute in place): `quantkit/notebooks/07_machine_learning_models.ipynb`, `08_deep_learning_models.ipynb`, `09_time_series_foundation_models.ipynb`
- Modify: `quantkit/README.md`

- [ ] **Step 1: Execute the three synthetic model notebooks so their outputs are saved**

```bash
for n in 07_machine_learning_models 08_deep_learning_models 09_time_series_foundation_models; do
  uv run --no-sync jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=600 \
    quantkit/notebooks/$n.ipynb
done
uv run --no-sync python -c "
import json
for n in ['07_machine_learning_models','08_deep_learning_models','09_time_series_foundation_models']:
    nb=json.load(open(f'quantkit/notebooks/{n}.ipynb'))
    print(n, sum(len(c.get('outputs',[])) for c in nb['cells'] if c['cell_type']=='code'), 'outputs')
"
```

Expected: each notebook reports > 0 outputs. (NB16 is left as is — it already has outputs. Its stacking IC of −0.0265 was measured with the unpurged code; add one markdown sentence at the end of NB16's stacking section only if you re-execute it, otherwise leave it and let the README point to NB17 for the purged result.)

- [ ] **Step 2: README edits**

In `quantkit/README.md`:

(a) In the status blockquote, replace the line

```
> NB 01–16 全実走(14–16 はレベルアップ層)・**159 tests**(+7 live、既定スキップ)。残るは鍵が要るソースのライブ確認のみ。
```

with (fill `<N>` from the final pytest count):

```
> **Phase 4(反証力)完了**: `backtest.stats`(deflated Sharpe / paired IC bootstrap / PBO)・purged stacking・
> purged+scaled conformal・nested `TunedModel`・`sample_weight`・目的変数変換、そして `experiments/`(hashed snapshot →
> leaderboard → fingerprint 付き JSON)。**NB17 は実データ**(米株 ETF+大型株 / crypto、`reports/experiments/*.json`)。
> NB 01–17 は出力保存済み(07–09 は 2026-09 に再実行)・**<N> tests**(+7 live、既定スキップ)。
```

(b) In the structure block, change `src/quantkit/   data/ macro/ features/ signals/ labels/ backtest/ models/ portfolio/ tax/ visualization/ utils/` to add `experiments/` after `models/`, and add a line `             backtest/stats.py = DSR / bootstrap IC / PBO(モデル比較の検定)` under the level-up line.

(c) Add a usage block after the model-layer example:

````markdown
```python
# 反証(Phase 4): 「ベースラインに勝った」は 3 つの検定で言う
from quantkit import experiments as EX, backtest as B

prices, manifest = EX.load_snapshot("us")                  # hashed snapshot(NB17 が作る)
res = EX.run_leaderboard(prices, candidates, features=feats, horizon=21,
                         folds=B.walk_forward(prices.index, train=504, test=252, horizon=21, embargo=5),
                         cost=B.CostModel(5, 2), reference="persist[mom]")
res.table[["ic_mean", "ic_diff_lo", "dsr", "pbo", "beats_baseline"]]   # 負けも残る
# 個別に: B.deflated_sharpe / B.ic_difference / B.pbo、リーク修正: StackingModel(horizon=), ConformalModel(horizon=, scale=)
# nested tuning: MD.TunedModel(MD.ridge, {"alpha": [...]}, n_inner=3, horizon=21)
```
````

(d) In the notebook list, append: `→ **反証**: \`17_real_data_model_leaderboard\`(実データ・DSR/IC 差/PBO の 3 検定・fingerprint 付き記録)。`

(e) In the roadmap, after the Phase 3 bullet, add:

```markdown
- **Phase 4(完了、2026-09)— 反証力**:`backtest.stats`(`deflated_sharpe`/`probabilistic_sharpe`/
  `min_track_record_length`、`bootstrap_ic`/`ic_difference`/`sharpe_difference`(circular block bootstrap)、
  `pbo`(CSCV))、`purged_block_folds`、**`StackingModel(horizon=, embargo=)` の OOF purge**(NB16 の −0.027 は
  リークした meta 特徴が原因)、**`ConformalModel(horizon=, scale=)`**(較正境界の purge・vol スケール非適合度・
  `coverage_by_date`)、`TunedModel`(nested)、`fit(..., sample_weight=)` + `time_decay_weights`/`uniqueness_weights`、
  `vol_scaled_target`/`demeaned_target`、`experiments/`(`build_snapshot`/`load_snapshot`・`run_leaderboard`・
  `make_record`)。**NB17 の判定**: <ここに 4 run の beats_baseline の要約を 1〜2 行で。勝者ゼロならそう書く>。
- **Phase 5(次)— 幅**:LightGBM・分類/meta-labeling・torch 系列モデル(`quantkit[deep]`)・Tier4 信号化・
  `model_config.yaml` を読む registry(設計書 §6)。
```

(f) In 「データ制限の警告」, add a bullet: `- **実データ leaderboard のユニバースは手選びの現存銘柄**(\`configs/universe.yaml\` \`experiments:\`)で、サバイバーシップバイアスを持つ。結果は「この手選びの中で」の話。`

(g) In the roadmap's Phase 3 bullet, the parenthetical `(レベルアップ層の NB 14–16 は実走済。)` stays; the test command block `# 159 passed, 7 skipped` → update to the new count.

- [ ] **Step 3: Full verification**

```bash
uv run --no-sync pytest quantkit/tests -q          # expect ~215 passed, 7 skipped
uv run --no-sync ruff check quantkit               # clean
uv run --no-sync ruff format --check quantkit      # clean (format any file you touched)
```

Record the exact pytest count in the README (step 2a/2g).

- [ ] **Step 4: Commit**

```bash
git add quantkit/notebooks/07_machine_learning_models.ipynb quantkit/notebooks/08_deep_learning_models.ipynb quantkit/notebooks/09_time_series_foundation_models.ipynb quantkit/README.md
git commit -m "docs(quantkit): Phase 4 (rigor) status, NB17 verdict, re-executed NB07-09 with saved outputs"
```

- [ ] **Step 5: Hand off**

Use `superpowers:finishing-a-development-branch` to merge `claude/quantkit-model-rigor` into `main` (fast-forward or merge commit; the workspace `make test` should also be run once from the merged tree — see AGENTS.md for the two suites it does not cover). Then write the Phase 2 plan from spec §6 against the now-real `experiments` API.

---

## Self-review notes (already applied)

- Spec §4.1 → Tasks 3–5; §4.2 → Tasks 2, 7, 8; §4.3 → Task 11; §4.4 → Tasks 6, 9; §4.5 → Task 10; §5.1–5.3 → Tasks 12–14; §5.4 → Task 15; §7.2–7.3 → Task 16. `rank_ic_by_date` (spec 4.1) → Task 1.
- Deviation from spec: PBO on the OOS performance matrix instead of refitting on `pbo_folds` (see header). `pbo_folds` is therefore not implemented.
- Names used across tasks: `ICResult(mean, lo, hi, n, ci)`, `PBOResult(pbo, logits, n_combinations, n_candidates)`, `purged_block_folds(index, *, n_splits, horizon, embargo)`, `subset_weights(sample_weight, selector)`, `TunedModel.inner_folds(unique_dates, *, n_inner, horizon, embargo)`, `predictions_to_backtest(pred, rets, *, horizon, quantile, cost, lag)`, `run_leaderboard(...)`, `make_record / save_record / load_record`.
