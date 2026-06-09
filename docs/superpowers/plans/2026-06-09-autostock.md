# autostock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `~/projects/autostock/`, a demo that ports Karpathy's `autoresearch` autonomous-research loop from LLM pretraining to a Magnificent-7 trading-strategy search, where the agent edits only `strategy.py` and maximizes a cheat-proof out-of-sample Sharpe ratio.

**Architecture:** A read-only `prepare.py` holds fixed constants, yfinance data prep, and the ground-truth backtest engine (`evaluate()`): it lags weights one day (no same-day lookahead), charges turnover costs, caps leverage, and scores Sharpe on a held-out test segment plus a withheld lockbox. The agent-edited `strategy.py` only emits a weight panel. `program.md` drives the keep/discard loop.

**Tech Stack:** Python 3.12, pandas, numpy, yfinance, pyarrow, matplotlib, pytest. uv workspace member (virtual, `package = false`).

---

## File Structure

```
~/projects/autostock/
├── pyproject.toml      # virtual workspace member, deps
├── conftest.py         # puts project root on sys.path for tests
├── .gitignore          # run.log, results.tsv, __pycache__
├── README.md           # quick start (mirrors autoresearch README shape)
├── prepare.py          # READ-ONLY: constants, data prep, backtest engine, evaluate()
├── strategy.py         # AGENT EDITS: generate_weights() + hyperparams + run/print
├── program.md          # HUMAN EDITS: autonomous research-loop instructions
├── results.tsv         # untracked, created at research-run setup
└── tests/
    ├── test_metrics.py        # _sharpe, _max_drawdown
    ├── test_constraints.py    # enforce_constraints
    ├── test_engine.py         # no-lookahead lag + transaction cost
    ├── test_evaluate.py       # segments + lockbox withholding
    └── test_strategy.py       # baseline weights shape/values
```

Root `~/projects/pyproject.toml` is edited to register the member, add its testpath, and a ruff naming exception.

**Lookahead policy (important, honest framing):** the engine's 1-day lag prevents *same-day-close* lookahead — the single most common backtest bug (computing a signal from day *t*'s close and capturing day *t*'s return). It does **not** mechanically prevent a strategy from explicitly indexing a future return (e.g. `prices.shift(-1)`); that is forbidden by `program.md` and is the agent's responsibility. The test in Task 4 verifies the same-day guarantee precisely.

---

## Task 1: Scaffold project + register workspace member

**Files:**
- Create: `autostock/pyproject.toml`
- Create: `autostock/conftest.py`
- Create: `autostock/.gitignore`
- Create: `autostock/tests/__init__.py` (empty)
- Modify: `pyproject.toml` (workspace root)

- [ ] **Step 1: Create the project directory and member pyproject**

Create `autostock/pyproject.toml`:

```toml
[project]
name = "autostock"
version = "0.1.0"
description = "Autonomous trading-strategy research swarm (autoresearch port, Mag7)"
requires-python = ">=3.12"
dependencies = [
    "yfinance>=0.2.40",
    "pandas>=2.2",
    "numpy>=1.26",
    "pyarrow>=15.0",
    "matplotlib>=3.8",
]

# Virtual member: scripts live at the project root (prepare.py / strategy.py),
# no wheel is built. Dependencies still resolve into the shared workspace env.
[tool.uv]
package = false
```

- [ ] **Step 2: Create conftest.py so tests can `import prepare`**

Create `autostock/conftest.py`:

```python
import os
import sys

# prepare.py / strategy.py live at the project root (flat layout, like
# autoresearch). Put that root on sys.path so tests can import them under
# pytest's importlib mode.
sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 3: Create .gitignore and tests package marker**

Create `autostock/.gitignore`:

```
run.log
results.tsv
__pycache__/
*.pyc
```

Create empty `autostock/tests/__init__.py` (zero bytes).

- [ ] **Step 4: Register the member in the workspace root**

In `~/projects/pyproject.toml`, add `"autostock",` to `[tool.uv.workspace] members` (after `"akinator",`):

```toml
members = [
    "gto",
    "market-viz",
    "stock",
    "nbody-gpu",
    "line_backup",
    "land_price_api_app",
    "akinator",
    "autostock",
    "johnhull/hullkit",
]
```

Add `"autostock/tests",` to `[tool.pytest.ini_options] testpaths` (after `"akinator/tests",`):

```toml
testpaths = [
    "gto/tests",
    "market-viz/tests",
    "stock/tests",
    "nbody-gpu/tests",
    "line_backup/tests",
    "akinator/tests",
    "autostock/tests",
    "johnhull/hullkit/tests",
]
```

Add a naming exception under `[tool.ruff.lint.per-file-ignores]` (finance code uses uppercase math-style names):

```toml
"autostock/**/*.py" = ["N803", "N806", "N816", "E741"]
```

- [ ] **Step 5: Sync and verify the env resolves**

Run: `cd ~/projects && uv sync --all-packages`
Expected: completes without error; yfinance/pandas/pyarrow present (already in lock via market-viz).

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add autostock/pyproject.toml autostock/conftest.py autostock/.gitignore autostock/tests/__init__.py pyproject.toml uv.lock
git commit -m "chore(autostock): scaffold workspace member + deps"
```

---

## Task 2: prepare.py — constants + metric helpers (`_sharpe`, `_max_drawdown`)

**Files:**
- Create: `autostock/prepare.py`
- Test: `autostock/tests/test_metrics.py`

- [ ] **Step 1: Write failing tests for the metric helpers**

Create `autostock/tests/test_metrics.py`:

```python
import math

import pandas as pd
import pytest

import prepare


def test_sharpe_known_value():
    # ret = [0.01, 0.02, 0.03]: mean=0.02, std(ddof=1)=0.01
    ret = pd.Series([0.01, 0.02, 0.03])
    expected = 0.02 / 0.01 * math.sqrt(prepare.ANNUALIZATION)
    assert prepare._sharpe(ret) == pytest.approx(expected)


def test_sharpe_zero_std_is_zero():
    ret = pd.Series([0.005, 0.005, 0.005])
    assert prepare._sharpe(ret) == 0.0


def test_sharpe_too_short_is_zero():
    assert prepare._sharpe(pd.Series([0.01])) == 0.0


def test_max_drawdown():
    # equity: 1.1, 0.55, 0.55 -> trough 0.55 vs peak 1.1 -> -0.5
    ret = pd.Series([0.1, -0.5, 0.0])
    assert prepare._max_drawdown(ret) == pytest.approx(-0.5)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'prepare'` (file not created yet).

- [ ] **Step 3: Create prepare.py with constants + metric helpers**

Create `autostock/prepare.py`:

```python
"""
One-time data prep + the FIXED evaluation harness for autostock.

READ-ONLY: the agent must NOT modify this file. It is the ground-truth metric,
analogous to autoresearch's prepare.py / evaluate_bpb. It downloads the
Magnificent-7 prices and defines the cheat-proof backtest engine + Sharpe metric.

Usage:
    uv run prepare.py            # download + cache prices (idempotent)
    uv run prepare.py --force    # re-download
"""

import argparse
import math
import os

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (fixed, do not modify)
# ---------------------------------------------------------------------------

UNIVERSE = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
START_DATE = "2011-06-01"
TRAIN_END = "2020-12-31"      # train segment: START_DATE .. TRAIN_END
TEST_START = "2021-01-01"     # test (OOS, headline metric): TEST_START .. TEST_END
TEST_END = "2025-06-30"
LOCKBOX_START = "2025-07-01"  # lockbox: withheld until --reveal-lockbox

COST_BPS = 5.0                # transaction cost (basis points) per unit turnover
RF = 0.0                      # daily risk-free rate (0 for the demo)
ANNUALIZATION = 252           # trading days per year
MAX_GROSS = 1.0               # cap on sum(|w|)
MAX_NAME = 0.5                # cap on |w_i|
ROLL_WINDOW = 252             # rolling-Sharpe window (trading days)

CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "autostock")
PRICES_PATH = os.path.join(CACHE_DIR, "prices.parquet")

# ---------------------------------------------------------------------------
# Metric helpers
# ---------------------------------------------------------------------------


def _sharpe(ret):
    """Annualized Sharpe of a daily-return series. 0.0 if degenerate."""
    ret = ret.dropna()
    if len(ret) < 2:
        return 0.0
    sd = ret.std()
    if sd == 0 or math.isnan(sd):
        return 0.0
    return float((ret.mean() - RF) / sd * math.sqrt(ANNUALIZATION))


def _max_drawdown(ret):
    """Most-negative peak-to-trough drawdown of the equity curve (<= 0)."""
    ret = ret.dropna()
    if len(ret) == 0:
        return 0.0
    equity = (1.0 + ret).cumprod()
    dd = equity / equity.cummax() - 1.0
    return float(dd.min())


def _rolling_sharpe(ret, window=ROLL_WINDOW):
    """Vectorized rolling annualized Sharpe series."""
    rmean = ret.rolling(window).mean()
    rstd = ret.rolling(window).std()
    return (rmean - RF) / rstd * math.sqrt(ANNUALIZATION)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_metrics.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add autostock/prepare.py autostock/tests/test_metrics.py
git commit -m "feat(autostock): prepare.py constants + Sharpe/drawdown helpers"
```

---

## Task 3: prepare.py — `enforce_constraints`

**Files:**
- Modify: `autostock/prepare.py` (append function)
- Test: `autostock/tests/test_constraints.py`

- [ ] **Step 1: Write failing tests**

Create `autostock/tests/test_constraints.py`:

```python
import pandas as pd

import prepare


def _frame(rows, cols=("A", "B", "C")):
    idx = pd.date_range("2020-01-01", periods=len(rows), freq="D")
    return pd.DataFrame(rows, index=idx, columns=list(cols))


def test_per_name_cap():
    w = _frame([[0.8, -0.7, 0.0]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    # clipped to +/-0.5; gross = 1.0 == MAX_GROSS so no scaling
    assert out.iloc[0]["A"] == 0.5
    assert out.iloc[0]["B"] == -0.5


def test_gross_scaled_down():
    w = _frame([[0.5, 0.5, 0.5]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    # gross 1.5 -> scaled by 1/1.5 -> each 1/3; gross now 1.0
    assert abs(out.iloc[0]["A"] - 1.0 / 3.0) < 1e-9
    assert abs(out.iloc[0].abs().sum() - 1.0) < 1e-9


def test_undersized_gross_not_levered_up():
    w = _frame([[0.1, 0.0, 0.0]])
    tradeable = _frame([[True, True, True]])
    out = prepare.enforce_constraints(w, tradeable)
    assert out.iloc[0]["A"] == 0.1  # never scaled up


def test_missing_asset_zeroed():
    w = _frame([[0.4, 0.4, 0.4]])
    tradeable = _frame([[True, False, True]])  # B not tradeable
    out = prepare.enforce_constraints(w, tradeable)
    assert out.iloc[0]["B"] == 0.0
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_constraints.py -v`
Expected: FAIL — `AttributeError: module 'prepare' has no attribute 'enforce_constraints'`.

- [ ] **Step 3: Append `enforce_constraints` to prepare.py**

Add to `autostock/prepare.py` (after the metric helpers):

```python
# ---------------------------------------------------------------------------
# Position constraints (enforced by the engine — the agent cannot bypass these)
# ---------------------------------------------------------------------------


def enforce_constraints(weights, tradeable):
    """Zero non-tradeable assets, cap per-name to +/-MAX_NAME, then scale the
    row down (never up) so gross sum(|w|) <= MAX_GROSS."""
    w = weights.where(tradeable, 0.0).fillna(0.0)
    w = w.clip(lower=-MAX_NAME, upper=MAX_NAME)
    gross = w.abs().sum(axis=1)
    scale = (MAX_GROSS / gross.replace(0.0, np.nan)).clip(upper=1.0).fillna(0.0)
    return w.mul(scale, axis=0)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_constraints.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add autostock/prepare.py autostock/tests/test_constraints.py
git commit -m "feat(autostock): position-constraint enforcement"
```

---

## Task 4: prepare.py — `_net_returns` (no-lookahead lag + cost)

**Files:**
- Modify: `autostock/prepare.py` (append functions)
- Test: `autostock/tests/test_engine.py`

- [ ] **Step 1: Write failing tests (no-lookahead + cost)**

Create `autostock/tests/test_engine.py`:

```python
import pandas as pd

import prepare


def _prices_single():
    # returns: d1=+0.10, d2=-0.10, d3=+0.10
    idx = pd.date_range("2015-01-01", periods=4, freq="B")
    return pd.DataFrame({"X": [100.0, 110.0, 99.0, 108.9]}, index=idx)


def test_no_same_day_lookahead():
    prices = _prices_single()
    rets = prices.pct_change(fill_method=None)["X"]
    # "cheat" strategy: bet today's known return today (uses day-t close)
    cheat = rets.apply(lambda r: 1.0 if r > 0 else (-1.0 if r < 0 else 0.0))
    weights = pd.DataFrame({"X": cheat})

    net, turnover = prepare._net_returns(weights, prices)

    # weight is clipped to +/-0.5, then LAGGED one day by the engine, so the
    # position held on d2 is the (sign of d1's return) = +0.5, applied to d2's
    # return (-0.10): a LOSS, not the +0.05 same-day foresight would give.
    cost_d2 = (prepare.COST_BPS / 1e4) * 0.5  # turnover entering d2 = |0.5 - 0|
    assert abs(net.iloc[2] - (-0.05 - cost_d2)) < 1e-9
    assert net.iloc[2] < 0.0  # proves foresight was neutralized


def test_transaction_cost_reduces_return():
    prices = _prices_single()
    # churny strategy: flip full position every day
    flip = pd.DataFrame({"X": [0.5, -0.5, 0.5, -0.5]}, index=prices.index)

    net_cost, _ = prepare._net_returns(flip, prices)
    old = prepare.COST_BPS
    try:
        prepare.COST_BPS = 0.0
        net_free, _ = prepare._net_returns(flip, prices)
    finally:
        prepare.COST_BPS = old

    assert net_cost.sum() < net_free.sum()  # cost strictly hurts a churny book
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_engine.py -v`
Expected: FAIL — `AttributeError: module 'prepare' has no attribute '_net_returns'`.

- [ ] **Step 3: Append data/returns helpers + `_net_returns` to prepare.py**

Add to `autostock/prepare.py` (after `enforce_constraints`):

```python
# ---------------------------------------------------------------------------
# Returns + backtest engine (the FIXED metric — do not modify)
# ---------------------------------------------------------------------------


def compute_returns(prices):
    """Simple daily returns from adjusted close."""
    return prices.pct_change(fill_method=None)


def _net_returns(weights, prices):
    """Portfolio daily net-return series and per-day turnover.

    Enforces constraints, then applies a 1-day execution lag (weights decided
    at close of day t are held starting day t+1 — no same-day lookahead), and
    charges COST_BPS on turnover. Returns (net_return_series, turnover_series).
    """
    returns = compute_returns(prices)
    tradeable = prices.notna()
    wc = enforce_constraints(weights.reindex_like(prices), tradeable)
    w_held = wc.shift(1).fillna(0.0)                          # 1-day lag
    turnover = (w_held - w_held.shift(1).fillna(0.0)).abs().sum(axis=1)
    gross = (w_held * returns).sum(axis=1)
    net = gross - (COST_BPS / 1e4) * turnover
    return net, turnover
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_engine.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
cd ~/projects
git add autostock/prepare.py autostock/tests/test_engine.py
git commit -m "feat(autostock): backtest engine with no-lookahead lag + turnover cost"
```

---

## Task 5: prepare.py — `evaluate()` (segments, rolling, lockbox withholding)

**Files:**
- Modify: `autostock/prepare.py` (append function)
- Test: `autostock/tests/test_evaluate.py`

- [ ] **Step 1: Write failing tests**

Create `autostock/tests/test_evaluate.py`:

```python
import numpy as np
import pandas as pd

import prepare


def _synthetic_prices():
    # daily prices 2011-06 .. 2026-06 for all 7 names, reproducible random walk
    idx = pd.bdate_range("2011-06-01", "2026-06-09")
    rng = np.random.default_rng(0)
    data = {}
    for t in prepare.UNIVERSE:
        steps = rng.normal(0.0005, 0.02, size=len(idx))
        data[t] = 100.0 * np.exp(np.cumsum(steps))
    return pd.DataFrame(data, index=idx)


def _equal_weight(prices):
    n = len(prices.columns)
    return pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)


def test_lockbox_withheld_by_default():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices)
    assert "lockbox_sharpe" not in m
    assert "sharpe" in m and np.isfinite(m["sharpe"])
    assert "train_sharpe" in m


def test_lockbox_revealed_on_flag():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices, reveal_lockbox=True)
    assert "lockbox_sharpe" in m and np.isfinite(m["lockbox_sharpe"])


def test_rolling_and_annual_present():
    prices = _synthetic_prices()
    m = prepare.evaluate(_equal_weight(prices), prices)
    for k in ("roll_sharpe_mean", "roll_sharpe_min", "roll_sharpe_pos_frac"):
        assert k in m and np.isfinite(m[k])
    assert isinstance(m["annual_sharpe"], dict) and len(m["annual_sharpe"]) > 5
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_evaluate.py -v`
Expected: FAIL — `AttributeError: module 'prepare' has no attribute 'evaluate'`.

- [ ] **Step 3: Append `evaluate` to prepare.py**

Add to `autostock/prepare.py` (after `_net_returns`):

```python
def _slice(series, start, end=None):
    return series.loc[start:] if end is None else series.loc[start:end]


def evaluate(weights, prices, reveal_lockbox=False):
    """Compute the fixed metric set. Headline = OOS test Sharpe (higher better).

    The lockbox segment is withheld unless reveal_lockbox=True, to bound
    multiple-testing overfit accumulated across many experiments.
    """
    net, turnover = _net_returns(weights, prices)

    train = _slice(net, START_DATE, TRAIN_END)
    test = _slice(net, TEST_START, TEST_END)

    roll = _rolling_sharpe(net)
    roll_test = _slice(roll, TEST_START, TEST_END).dropna()

    visible = net.loc[:TEST_END]
    annual = {int(y): _sharpe(g) for y, g in visible.groupby(visible.index.year)}

    metrics = {
        "sharpe": _sharpe(test),
        "train_sharpe": _sharpe(train),
        "ann_return": float(test.dropna().mean() * ANNUALIZATION),
        "ann_vol": float(test.dropna().std() * math.sqrt(ANNUALIZATION)),
        "max_drawdown": _max_drawdown(test),
        "turnover": float(_slice(turnover, TEST_START, TEST_END).dropna().mean()),
        "roll_sharpe_mean": float(roll_test.mean()) if len(roll_test) else 0.0,
        "roll_sharpe_std": float(roll_test.std()) if len(roll_test) > 1 else 0.0,
        "roll_sharpe_min": float(roll_test.min()) if len(roll_test) else 0.0,
        "roll_sharpe_pos_frac": float((roll_test > 0).mean()) if len(roll_test) else 0.0,
        "annual_sharpe": annual,
    }
    if reveal_lockbox:
        metrics["lockbox_sharpe"] = _sharpe(_slice(net, LOCKBOX_START))
    return metrics
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_evaluate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full autostock test module to confirm no regressions**

Run: `cd ~/projects && uv run pytest autostock/tests -v`
Expected: PASS (all tests across metrics/constraints/engine/evaluate).

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add autostock/prepare.py autostock/tests/test_evaluate.py
git commit -m "feat(autostock): evaluate() with train/test/lockbox segments + rolling/annual Sharpe"
```

---

## Task 6: prepare.py — data download/load + fetch real data

**Files:**
- Modify: `autostock/prepare.py` (append download/load + `__main__`)
- Test: `autostock/tests/test_metrics.py` (append one load test)

- [ ] **Step 1: Write a failing test for `load_prices` missing-file behavior**

Append to `autostock/tests/test_metrics.py`:

```python
def test_load_prices_missing_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare, "PRICES_PATH", str(tmp_path / "nope.parquet"))
    try:
        prepare.load_prices()
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as e:
        assert "prepare.py" in str(e)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_metrics.py::test_load_prices_missing_raises -v`
Expected: FAIL — `AttributeError: module 'prepare' has no attribute 'load_prices'`.

- [ ] **Step 3: Append download/load + `__main__` to prepare.py**

Add to `autostock/prepare.py` (after `evaluate`):

```python
# ---------------------------------------------------------------------------
# Data download / load
# ---------------------------------------------------------------------------


def download_prices():
    """Download Mag-7 adjusted close via yfinance and cache to parquet."""
    import yfinance as yf

    os.makedirs(CACHE_DIR, exist_ok=True)
    raw = yf.download(UNIVERSE, start=START_DATE, auto_adjust=True, progress=False)
    prices = raw["Close"].reindex(columns=UNIVERSE).dropna(how="all").sort_index()
    prices.to_parquet(PRICES_PATH)
    return prices


def load_prices():
    if not os.path.exists(PRICES_PATH):
        raise FileNotFoundError(
            f"No cached prices at {PRICES_PATH}. Run `uv run prepare.py` first."
        )
    return pd.read_parquet(PRICES_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Mag-7 price data")
    parser.add_argument("--force", action="store_true", help="re-download even if cached")
    args = parser.parse_args()

    if args.force or not os.path.exists(PRICES_PATH):
        print(f"Downloading {len(UNIVERSE)} tickers to {PRICES_PATH} ...")
        prices = download_prices()
    else:
        prices = load_prices()
        print(f"Using cached prices at {PRICES_PATH}")

    print(f"Rows: {len(prices)}  Range: {prices.index.min().date()} -> {prices.index.max().date()}")
    print("Per-ticker first valid date:")
    for t in UNIVERSE:
        fv = prices[t].first_valid_index()
        print(f"  {t:6s}: {fv.date() if fv is not None else 'NA'}")
    print("Done. Ready to run strategy.py")
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_metrics.py::test_load_prices_missing_raises -v`
Expected: PASS.

- [ ] **Step 5: Fetch real data and observe output**

Run: `cd ~/projects/autostock && uv run prepare.py`
Expected: prints `Rows: ~3700+`, `Range: 2011-06-01 -> 2026-06-0x`, and per-ticker first valid dates (META ~2012-05, others earlier). **Quote the real output in the task report.**

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add autostock/prepare.py autostock/tests/test_metrics.py
git commit -m "feat(autostock): yfinance download/load + prepare.py CLI"
```

---

## Task 7: strategy.py — baseline + summary print

**Files:**
- Create: `autostock/strategy.py`
- Test: `autostock/tests/test_strategy.py`

- [ ] **Step 1: Write failing tests for the baseline**

Create `autostock/tests/test_strategy.py`:

```python
import pandas as pd

import strategy


def test_baseline_equal_weight_shape_and_values():
    idx = pd.date_range("2020-01-01", periods=10, freq="B")
    cols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    prices = pd.DataFrame(100.0, index=idx, columns=cols)
    w = strategy.generate_weights(prices)
    assert list(w.columns) == cols
    assert len(w) == len(idx)
    assert abs(w.iloc[0]["AAPL"] - 1.0 / 7.0) < 1e-9
    assert abs(w.iloc[0].sum() - 1.0) < 1e-9
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd ~/projects && uv run pytest autostock/tests/test_strategy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'strategy'`.

- [ ] **Step 3: Create strategy.py (baseline)**

Create `autostock/strategy.py`:

```python
"""
autostock strategy — the ONLY file the agent edits.

Edit generate_weights() and the hyperparameters below to search for a higher
out-of-sample Sharpe. prepare.py (the metric) is read-only.

Run:
    uv run strategy.py                 # normal experiment (lockbox withheld)
    uv run strategy.py --reveal-lockbox  # final check only, when finalizing
"""

import argparse

import pandas as pd

from prepare import UNIVERSE, evaluate, load_prices

# ---------------------------------------------------------------------------
# Hyperparameters (edit these directly, no CLI flags)
# ---------------------------------------------------------------------------
# (baseline has none; momentum/mean-reversion variants add lookbacks here)


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    """Return a date x asset weight panel using PAST data only.

    The engine applies a 1-day execution lag and turnover costs, so do NOT
    index future bars (e.g. prices.shift(-1)) — that is cheating and forbidden.

    Baseline: equal-weight long-only across the 7 names.
    """
    n = len(UNIVERSE)
    return pd.DataFrame(1.0 / n, index=prices.index, columns=prices.columns)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reveal-lockbox", action="store_true")
    args = ap.parse_args()

    prices = load_prices()
    weights = generate_weights(prices)
    m = evaluate(weights, prices, reveal_lockbox=args.reveal_lockbox)

    print("---")
    print(f"sharpe:               {m['sharpe']:.6f}")
    print(f"train_sharpe:         {m['train_sharpe']:.6f}")
    print(f"ann_return:           {m['ann_return']:.6f}")
    print(f"ann_vol:              {m['ann_vol']:.6f}")
    print(f"max_drawdown:         {m['max_drawdown']:.6f}")
    print(f"turnover:             {m['turnover']:.6f}")
    print(f"roll_sharpe_mean:     {m['roll_sharpe_mean']:.6f}")
    print(f"roll_sharpe_min:      {m['roll_sharpe_min']:.6f}")
    print(f"roll_sharpe_pos_frac: {m['roll_sharpe_pos_frac']:.6f}")
    if "lockbox_sharpe" in m:
        print(f"lockbox_sharpe:       {m['lockbox_sharpe']:.6f}")
    print("annual_sharpe:")
    for yr in sorted(m["annual_sharpe"]):
        print(f"  {yr}: {m['annual_sharpe'][yr]:.3f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd ~/projects && uv run pytest autostock/tests/test_strategy.py -v`
Expected: PASS.

- [ ] **Step 5: Run the baseline end-to-end on real data**

Run: `cd ~/projects/autostock && uv run strategy.py`
Expected: prints the `---` summary block with a real **test Sharpe** and an annual_sharpe table. **Quote the actual summary lines in the task report.**

- [ ] **Step 6: Commit**

```bash
cd ~/projects
git add autostock/strategy.py autostock/tests/test_strategy.py
git commit -m "feat(autostock): baseline equal-weight strategy + summary output"
```

---

## Task 8: program.md + README.md

**Files:**
- Create: `autostock/program.md`
- Create: `autostock/README.md`

- [ ] **Step 1: Create program.md (autonomous research loop)**

Create `autostock/program.md`:

```markdown
# autostock

An experiment in autonomous trading-strategy research, ported from autoresearch.
The agent edits only `strategy.py`; the metric in `prepare.py` is read-only.

## Setup

1. **Agree a run tag** (e.g. `jun9`). Branch `autostock/<tag>` must not exist.
2. **Create the branch**: `git checkout -b autostock/<tag>`.
3. **Read in-scope files**: `prepare.py` (read-only metric), `strategy.py` (you edit).
4. **Verify data**: ensure `~/.cache/autostock/prices.parquet` exists; else run
   `uv run prepare.py`.
5. **Init results.tsv** with just the header row (leave it untracked by git).
6. **Confirm and go.**

## The metric

The goal is the **highest out-of-sample test Sharpe** (TEST_START..TEST_END).
Higher is better. The engine enforces: a 1-day execution lag (no same-day
lookahead), turnover costs, gross leverage <= 1.0, per-name <= 0.5. You may NOT
modify `prepare.py` and you may NOT index future bars (`prices.shift(-1)` etc.).

## What you CAN / CANNOT do

- CAN: rewrite `generate_weights()` and tune its hyperparameters — momentum,
  mean-reversion, vol-targeting, cross-sectional ranking, regime filters, etc.
- CANNOT: modify `prepare.py`, add dependencies, peek at the lockbox during the
  loop, or use future data.

## Robustness over a single number

A high test Sharpe with a negative `roll_sharpe_min` or a wildly negative single
year in `annual_sharpe` is fragile (regime-fit), and a large `train_sharpe` vs
`sharpe` gap means overfit. Prefer strategies that are high AND stable. Simpler is
better (the autoresearch simplicity criterion).

## Output format

`uv run strategy.py > run.log 2>&1`, then read:
`grep "^sharpe:\|^train_sharpe:\|^max_drawdown:\|^turnover:" run.log`

## Logging results

Append to `results.tsv` (TAB-separated, untracked by git). Columns:

    commit	sharpe	train_sharpe	max_dd	turnover	status	description

status is `keep`, `discard`, or `crash`. Example:

    commit	sharpe	train_sharpe	max_dd	turnover	status	description
    a1b2c3d	0.812000	0.910000	-0.245	0.010	keep	baseline equal-weight
    b2c3d4e	1.050000	1.300000	-0.300	0.450	keep	126d xs-momentum top2/bottom2

## The experiment loop

LOOP FOREVER:
1. Look at the git state (current branch/commit).
2. Edit `strategy.py` with one experimental idea.
3. `git commit`.
4. `uv run strategy.py > run.log 2>&1`.
5. `grep "^sharpe:" run.log`. Empty => crashed; `tail -n 50 run.log`, fix if easy.
6. Record the row in `results.tsv`.
7. If test Sharpe improved (and isn't an obvious overfit/fragile spike), advance.
   Else `git reset` back to where you started.

**NEVER STOP** to ask whether to continue. Try momentum, mean-reversion, vol
scaling, combinations, different lookbacks. Only when finalizing a chosen
strategy do you run `uv run strategy.py --reveal-lockbox` once to sanity-check
the truly-untouched segment.
```

- [ ] **Step 2: Create README.md**

Create `autostock/README.md`:

```markdown
# autostock

Autonomous trading-strategy research, ported from
[autoresearch](https://github.com/karpathy/autoresearch) to a quant setting: an
agent edits one file (`strategy.py`) to maximize a cheat-proof out-of-sample
Sharpe over the Magnificent 7 (AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA).

## Files

- `prepare.py` — **read-only**: constants, yfinance data prep, and the fixed
  backtest engine + `evaluate()` metric (1-day execution lag, turnover costs,
  leverage caps, train/test/lockbox segments, rolling/annual Sharpe).
- `strategy.py` — **the agent edits this**: `generate_weights(prices)` + hyperparams.
- `program.md` — the human-edited autonomous research loop.

## Quick start

    cd ~/projects/autostock
    uv run prepare.py          # download + cache 15y of Mag-7 prices (one-time)
    uv run strategy.py         # run one backtest, print the summary block

Then point an agent at `program.md` to start the autonomous loop. The metric is
**OOS test Sharpe** (higher is better). The lockbox segment is withheld until you
run `uv run strategy.py --reveal-lockbox` when finalizing a strategy.

## Why a read-only metric

In a backtest the easy way to "win" is to cheat: peek at the future, ignore
costs, or pile on leverage. `prepare.py` makes those impossible — the engine
lags every position by a day, charges turnover, and caps gross/per-name weight —
so any Sharpe the loop reports is at least structurally honest. Survivorship in
the hand-picked Mag-7 still makes absolute levels optimistic; the point of the
demo is the autonomous *search loop*, not deployable alpha.
```

- [ ] **Step 3: Commit**

```bash
cd ~/projects
git add autostock/program.md autostock/README.md
git commit -m "docs(autostock): program.md research loop + README"
```

---

## Task 9: Short research run — find a baseline-beating strategy

This task exercises the loop manually (the demo's payoff). It runs a handful of
concrete experiments, keeps the best OOS strategy, logs to `results.tsv`, and
reveals the lockbox once at the end. Work on a branch.

**Files:**
- Modify: `autostock/strategy.py` (iterate `generate_weights`)
- Create: `autostock/results.tsv` (untracked)

- [ ] **Step 1: Branch + init results.tsv + record the baseline**

```bash
cd ~/projects/autostock
git checkout -b autostock/jun9
printf 'commit\tsharpe\ttrain_sharpe\tmax_dd\tturnover\tstatus\tdescription\n' > results.tsv
uv run strategy.py > run.log 2>&1
grep "^sharpe:\|^train_sharpe:\|^max_drawdown:\|^turnover:" run.log
```
Record the baseline row in `results.tsv` (status `keep`). **Quote the baseline summary.**

- [ ] **Step 2: Experiment A — cross-sectional momentum**

Replace `generate_weights` in `strategy.py` with:

```python
LOOKBACK = 126
TOP_K = 2
NAME_W = 0.25


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    mom = prices.pct_change(LOOKBACK, fill_method=None)
    rank = mom.rank(axis=1, ascending=True)            # 1 = worst
    n_valid = mom.notna().sum(axis=1)
    longs = rank.gt(n_valid - TOP_K, axis=0)           # top TOP_K
    shorts = rank.le(TOP_K)                            # bottom TOP_K
    return longs.astype(float) * NAME_W - shorts.astype(float) * NAME_W
```

Run and log:

```bash
cd ~/projects/autostock
git commit -am "exp: 126d cross-sectional momentum top2/bottom2"
uv run strategy.py > run.log 2>&1
grep "^sharpe:\|^train_sharpe:\|^max_drawdown:\|^turnover:" run.log
```
If test Sharpe beats the kept value (and rolling/annual look non-pathological),
keep; else `git reset --hard HEAD~1`. Append the row to `results.tsv`. **Quote the summary.**

- [ ] **Step 3: Experiment B — short-term mean reversion**

Replace `generate_weights` with:

```python
LOOKBACK = 5
TOP_K = 2
NAME_W = 0.25


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    ret = prices.pct_change(LOOKBACK, fill_method=None)
    rank = ret.rank(axis=1, ascending=True)            # 1 = biggest loser
    n_valid = ret.notna().sum(axis=1)
    longs = rank.le(TOP_K)                             # buy recent losers
    shorts = rank.gt(n_valid - TOP_K, axis=0)          # sell recent winners
    return longs.astype(float) * NAME_W - shorts.astype(float) * NAME_W
```

Run, compare, keep/reset, append row as in Step 2. **Quote the summary.**

- [ ] **Step 4: Experiment C — inverse-volatility long-only**

Replace `generate_weights` with:

```python
VOL_LB = 20


def generate_weights(prices: pd.DataFrame) -> pd.DataFrame:
    rets = prices.pct_change(fill_method=None)
    vol = rets.rolling(VOL_LB).std()
    inv = 1.0 / vol
    return inv.div(inv.sum(axis=1), axis=0)            # long-only, sums to 1
```

Run, compare, keep/reset, append row. **Quote the summary.**

- [ ] **Step 5: Finalize — set strategy.py to the best keeper, reveal lockbox once**

Restore `generate_weights` to whichever experiment had the best OOS test Sharpe
(with acceptable robustness), commit it, then:

```bash
cd ~/projects/autostock
uv run strategy.py --reveal-lockbox > run.log 2>&1
grep "^sharpe:\|^train_sharpe:\|^lockbox_sharpe:\|^max_drawdown:" run.log
```
**Quote** test Sharpe, train Sharpe, and the revealed lockbox Sharpe. Report the
train↔test↔lockbox gap honestly (a big drop on lockbox = the search overfit the
test period). Do NOT iterate further against the lockbox.

- [ ] **Step 6: Report**

Summarize in the task report: baseline test Sharpe, best strategy + its test
Sharpe, train↔test↔lockbox comparison, and the `results.tsv` contents. State
plainly whether the best strategy genuinely generalized or showed overfit.

---

## Self-Review (completed during planning)

- **Spec coverage:** file mapping (Task 1, 6, 7, 8) ✓; cheat-proof engine — lag
  (Task 4), cost (Task 4), constraints (Task 3), missing-asset (Task 3) ✓;
  train/test/lockbox segments + rolling + annual (Task 5) ✓; lockbox withholding +
  `--reveal-lockbox` (Task 5, 7) ✓; strategy.py interface + baseline + summary
  (Task 7) ✓; program.md loop + results.tsv schema (Task 8) ✓; validation: DL real
  data (Task 6), baseline Sharpe quoted (Task 7), no-lookahead test (Task 4), cost
  test (Task 4), short research run (Task 9) ✓; caveats documented in README/program.md ✓.
- **Placeholder scan:** no TBD/TODO; every code step has complete code.
- **Type consistency:** `enforce_constraints(weights, tradeable)`, `_net_returns`
  returns `(net, turnover)`, `evaluate(weights, prices, reveal_lockbox=False)`
  returning the documented metric keys, `generate_weights(prices) -> DataFrame` —
  names used consistently across Tasks 3–9.
- **Honesty note:** the lag prevents same-day lookahead, not explicit future
  indexing (forbidden by program.md) — stated in the File Structure section and
  Task 4 test framing so the claim isn't overstated.
```
