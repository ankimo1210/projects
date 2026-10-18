# Bond-Timing ML Signal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide, under strict point-in-time rules and net of costs, whether a monthly hold-or-cash signal for a TLT-like synthetic bond (machine learning or a simple rule) beats buy-and-hold and simple rules, following the falsification-first design of 2026-10-19.

**Architecture:** A new workspace member `bond_timing_lab` (package `bond_timing`). Data modules turn raw snapshots (GSW from the macrokit store; DTB3, FRED-MD vintages, Liu–Wu and ETF prices from the bond-timing store) into monthly panels; `returns`, `pit`, `features`, `models`, `backtest`, `evaluate` and `synthetic` implement the design's rules, ladder, tests and synthetic worlds as small pure modules; `study` assembles the panels; `stages` holds the shared stage helpers and runs G0 and dev, and one module per later stage (`g1`, `oos_a`, `decomposition`, `g3`, `oos_b`) runs G1, OOS-A, the V0–V3 decomposition, G3 and OOS-B. Each stage writes one JSON file under `bond_timing_lab/results/`. The CLI enforces the stage order and the one-shot OOS-B lock.

**Tech Stack:** Python 3.12, numpy, pandas (monthly `Period[M]` indexes), scipy, scikit-learn 1.9 (ElasticNet, ExtraTrees, HistGradientBoosting, MLPRegressor), threadpoolctl, httpx, openpyxl, yfinance 1.5, click, macrokit (workspace), pytest, ruff.

**Spec:** `/home/kazumasa/projects/docs/superpowers/specs/2026-10-19-bond-timing-ml-design.md` (approved section by section on 2026-10-19; the user asked to start implementing as soon as the design was done).

## Global Constraints

- Worktree `WT=/home/kazumasa/worktrees/bond-timing`, branch `claude/bond-timing-lab`, created from `main` after this plan is committed. The spec and this plan live on `main`. Merge and push only with the user's approval.
- New workspace member `bond_timing_lab`, Python package `bond_timing`. Dependencies: macrokit (workspace), numpy, pandas, scipy, scikit-learn, httpx, openpyxl, yfinance (spec §9), plus click and threadpoolctl (already locked through macrokit and scikit-learn). No torch, no GPU (spec §11).
- Raw data outside Git: `/home/kazumasa/projects/_data/bond_timing_lab/raw/`, written only through macrokit `save_snapshot` (manifest with SHA-256, URL, fetch time). GSW is read from the macrokit store `/home/kazumasa/projects/macrokit/data/raw/` (`us_term/gsw`), never re-fetched here (spec §4.1, §4.5).
- Git keeps code, `PREREG.md`, `README.md` and the summary JSON in `bond_timing_lab/results/`. No intermediate arrays (bootstrap draws, per-refit predictions beyond the monthly signals) are saved; they are rebuilt from fixed seeds (spec §4.5).
- Units: zero yields are decimal, continuously compounded, annual; maturities are integer months; months are pandas `Period[M]`. A decision at the end of month t sets the position held over return month t+1. DEV, OOS-A and OOS-B are counted in decision months (OOS-A = decisions 2000-01..2018-12 = 228 months).
- Fixed values (spec §3, §6, §8): cost 2 bp per switch (1 bp per leg), sensitivity 4 bp; γ = 5; stationary bootstrap mean block 12, 10,000 draws, seed 20261019; one-sided 5 % after Holm (5 hypotheses for H_A, 2 for H_B); fewer than 60 completed pairs → cash; validation = last 15 % with an h-month embargo; refits every January; macro vintages for decision t = t−1; TLT-like n = 17 years (204 months), IEF-like 7.5 years (90 months); targets rx12(10) (primary) and the next-month log excess return of the 10-year zero (secondary); EN l1_ratio {0.1, 0.5, 0.9} × 20 log alphas; ET 500 trees, max_depth {2, 4, 6}, min_samples_leaf {5, 20}, max_features {0.3, 1.0}; HGB learning_rate {0.03, 0.1}, max_depth {2, 3}, max_iter {100, 300}, l2 {0, 1}; NN-F (3,), NN-FM (32, 16), alpha {1e-4, 1e-3, 1e-2}, adam, 500 iterations, 20 seeds averaged; G0 corr ≥ 0.95; G1 20 worlds each, W0 ≤ 2/20 significant per strategy, W2 P3 and P4 ≥ 18/20 with a planted size giving ≥ 4 %/yr oracle CER gain; G3 200 worlds, 5 seeds, p = (1 + #{sim ≥ real}) / 201.
- Python command (the shared venv; `PYTHONPATH` makes the worktree code win; single-thread BLAS): `PY="env PYTHONPATH=$WT/bond_timing_lab/src:$WT/macrokit/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python -P"`. CLI: `BT="$PY -m bond_timing.cli"`. Never run `uv sync` or `uv run` in the worktree; run `uv lock` only from `$WT`.
- Tests: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests -q`. Tests never touch the network; the one network test runs only with `BOND_TIMING_NETWORK=1`.
- Lint: `cd $WT && /home/kazumasa/projects/.venv/bin/ruff check bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format --check bond_timing_lab` (root ruff config: line length 100, `select = ["E","W","F","I","B","UP","N","RUF"]`; Task 1 adds `N803`, `N806`, `N816`, `E741` ignores for `bond_timing_lab/**/*.py`). B905: every `zip()` needs `strict=`. Run `ruff check --fix` and `ruff format` before each commit.
- Commit messages: English, imperative, no `feat:` prefix, ending with the session attribution lines (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and the `Claude-Session:` line).
- Docs (`PREREG.md`, `README.md`) are Japanese; code, identifiers and commit messages are English.
- Stage order (spec §3.6), enforced by the CLI: `g0` → `dev` → commit `PREREG.md` → `g1` (must pass) → `oos-a` → `decompose` → `g3` → `oos-b` (once; a rerun needs `--rerun-reason` and never replaces the verdict of record).

## Review Focus

- A FRED-MD vintage whose newest row is mostly blank, and a series that exists at the January refit but is missing from a later monthly vintage: the prediction must take the latest earlier value or, failing that, NaN that cleaning turns into 0; columns must never shift (Task 6 test `test_edge_falls_back_and_marks_missing_series`, Task 8 test `test_macro_cleaner_turns_missing_edge_values_into_zero`).
- A refit year with fewer than 60 completed pairs, or a month with no forecast: that month is cash, never a crash and never a silent hold (Task 11 tests `test_build_tasks_skips_thin_years` and `test_signal_weights_hold_cash_without_a_forecast`).
- Always-cash or identical strategies: Sharpe 0 instead of NaN, and a bootstrap p-value of exactly 1 for identical series (Task 10 tests `test_sharpe_of_a_flat_series_is_zero` and `test_identical_strategies_have_p_one`).
- Hyperparameters that went through JSON (tuples become lists) and come back as fixed parameters for G3: the estimator must be configured exactly as before (Task 11 test `test_fixed_params_survive_a_json_round_trip`).
- Running OOS-A before PREREG is committed or before G1 passed, or running OOS-B a second time: refused with a message that says why (Task 13 test `test_oos_a_requires_prereg_and_a_passed_g1`, Task 13 test `test_oos_b_runs_once_without_a_reason`).

## File Structure

| Path (under `bond_timing_lab/`) | Responsibility |
|---|---|
| `pyproject.toml` | member metadata, `bond-timing` script, pytest config |
| `src/bond_timing/data/store.py` | store roots, `fetch`, `store_bytes`, `read_latest`, `indicators` |
| `src/bond_timing/data/gsw.py` | GSW parameters + published range → month-end and daily zero yields |
| `src/bond_timing/data/fred.py` | DTB3/TB3MS CSV, month-end values, bond-equivalent yield, cash returns |
| `src/bond_timing/data/fredmd.py` | vintage archive members, vintage parsing, tcode transforms, macro sources (real-time, final, panel) |
| `src/bond_timing/data/liuwu.py` | Liu–Wu monthly workbook |
| `src/bond_timing/data/etf.py` | yfinance download to CSV, monthly and daily total returns |
| `src/bond_timing/data/snapshot.py` | fetch every source into the store |
| `src/bond_timing/returns.py` | holding returns, rx12, outcomes, daily synthetic returns, delayed-switch legs |
| `src/bond_timing/pit.py` | R1–R4 checks, training starts, validation split |
| `src/bond_timing/features.py` | forwards, PCA, standardizer, macro cleaner, input transforms, slope and trend signals |
| `src/bond_timing/models.py` | model specs, grids, estimators, seed-averaged fit/predict |
| `src/bond_timing/backtest.py` | rules (V0–V3), refit tasks, selection, parallel forecasts, weights, returns, delay |
| `src/bond_timing/evaluate.py` | CER, Sharpe, R²oos, prevailing mean, stationary bootstrap, Holm, verdict |
| `src/bond_timing/synthetic.py` | W0/W2 worlds, planted-size calibration, spanning-null VAR worlds |
| `src/bond_timing/study.py` | loads every input into a `Study`; W2's macro factor |
| `src/bond_timing/stages.py` | shared stage helpers (forecast, weights, summaries, primary tests); G0 and dev runners |
| `src/bond_timing/g1.py` | G1: W0 and W2 worlds, detection counts, pass rule |
| `src/bond_timing/oos_a.py` | OOS-A: pre-registered tests, robustness, supplementary tables |
| `src/bond_timing/decomposition.py` | V0–V3 decomposition of R²oos |
| `src/bond_timing/g3.py` | G3: spanning-null statistic and p-values |
| `src/bond_timing/oos_b.py` | OOS-B and the verdict |
| `src/bond_timing/report.py` | markdown tables from the results JSON |
| `src/bond_timing/cli.py` | `snapshot`, `run <stage>`, `report`; stage order and OOS-B lock |
| `tests/test_*.py` | one file per module, network-free |
| `PREREG.md`, `README.md`, `results/*.json`, `results/summary.md` | pre-registration, write-up, results |

Root files touched: `/home/kazumasa/projects/pyproject.toml` (workspace member, testpaths, ruff per-file ignores) and `uv.lock`.

---

### Task 1: Worktree, member scaffold and the raw store

**Files:**
- Create: `bond_timing_lab/pyproject.toml`, `bond_timing_lab/src/bond_timing/__init__.py`, `bond_timing_lab/src/bond_timing/data/__init__.py`, `bond_timing_lab/src/bond_timing/data/store.py`
- Modify: `pyproject.toml` (root: `[tool.uv.workspace] members`, `[tool.pytest.ini_options] testpaths`, `[tool.ruff.lint.per-file-ignores]`), `uv.lock`
- Test: `bond_timing_lab/tests/test_store.py`

**Interfaces:**
- Consumes: `macrokit.snapshot.save_snapshot(root, source, indicator, content, *, ingested_at, url, http_status, filename) -> SnapshotResult`, `macrokit.snapshot.latest_payload(root, source, indicator) -> Path | None`.
- Produces: `bond_timing.data.store.RAW_ROOT: Path`, `MACROKIT_RAW: Path`, `FetchError`, `fetch(url: str, *, timeout: float = 300.0) -> bytes`, `store_bytes(root: Path, source: str, indicator: str, content: bytes, *, url: str, filename: str) -> SnapshotResult`, `read_latest(root: Path, source: str, indicator: str) -> bytes`, `indicators(root: Path, source: str) -> list[str]`.

- [ ] **Step 1: Create the worktree**

```bash
cd /home/kazumasa/projects && git status --short && git worktree add /home/kazumasa/worktrees/bond-timing -b claude/bond-timing-lab main
```

Expected: `Preparing worktree (new branch 'claude/bond-timing-lab')`.

- [ ] **Step 2: Write the member metadata and package markers**

File: `bond_timing_lab/pyproject.toml` (create)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bond-timing-lab"
version = "0.1.0"
description = "Point-in-time test of ML bond-timing signals (TLT/IEF vs cash) after Bianchi-Buechner-Tamoni (2021)"
requires-python = ">=3.12"
dependencies = [
    "macrokit",
    "click>=8.1",
    "httpx>=0.27",
    "numpy>=1.26",
    "openpyxl>=3.1",
    "pandas>=2.2",
    "scikit-learn>=1.5",
    "scipy>=1.13",
    "threadpoolctl>=3.1",
    "yfinance>=0.2.50",
]

[project.scripts]
bond-timing = "bond_timing.cli:main"

[tool.uv.sources]
macrokit = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/bond_timing"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --import-mode=importlib"
```

File: `bond_timing_lab/src/bond_timing/__init__.py` (create)

```python
"""Point-in-time test of ML bond-timing signals (design 2026-10-19)."""
```

File: `bond_timing_lab/src/bond_timing/data/__init__.py` (create)

```python
"""Raw inputs: GSW, FRED, FRED-MD vintages, Liu-Wu and ETF prices."""
```

- [ ] **Step 3: Write the failing test**

File: `bond_timing_lab/tests/test_store.py` (create)

```python
from pathlib import Path

import pytest
from bond_timing.data.store import indicators, read_latest, store_bytes


def test_store_and_read_back(tmp_path: Path):
    store_bytes(tmp_path, "fred", "DTB3", b"a,b\n", url="https://example.invalid/a", filename="DTB3.csv")
    store_bytes(
        tmp_path, "fredmd", "monthly_2026-01", b"x", url="https://example.invalid/b", filename="x.csv"
    )
    assert read_latest(tmp_path, "fred", "DTB3") == b"a,b\n"
    assert indicators(tmp_path, "fredmd") == ["monthly_2026-01"]
    assert indicators(tmp_path, "etf") == []


def test_read_latest_names_the_missing_snapshot(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="bond-timing snapshot"):
        read_latest(tmp_path, "fred", "DTB3")
```

- [ ] **Step 4: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_store.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.data.store'`.

- [ ] **Step 5: Write the store**

File: `bond_timing_lab/src/bond_timing/data/store.py` (create)

```python
"""Where raw snapshots live, and how they are fetched and read back (design §4.5)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from macrokit.snapshot import SnapshotResult, latest_payload, save_snapshot

RAW_ROOT = Path(
    os.environ.get("BOND_TIMING_RAW", "/home/kazumasa/projects/_data/bond_timing_lab/raw")
)
MACROKIT_RAW = Path(
    os.environ.get("BOND_TIMING_MACROKIT_RAW", "/home/kazumasa/projects/macrokit/data/raw")
)
USER_AGENT = "Mozilla/5.0 (compatible; macrokit research)"


class FetchError(RuntimeError):
    """A remote file could not be fetched."""


def fetch(url: str, *, timeout: float = 300.0) -> bytes:
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise FetchError(f"GET {url} returned {response.status_code}")
    return response.content


def store_bytes(
    root: Path, source: str, indicator: str, content: bytes, *, url: str, filename: str
) -> SnapshotResult:
    return save_snapshot(
        root,
        source,
        indicator,
        content,
        ingested_at=datetime.now(UTC),
        url=url,
        http_status=200,
        filename=filename,
    )


def read_latest(root: Path, source: str, indicator: str) -> bytes:
    path = latest_payload(root, source, indicator)
    if path is None:
        raise FileNotFoundError(
            f"no stored snapshot for {source}/{indicator} under {root}; run `bond-timing snapshot`"
        )
    return path.read_bytes()


def indicators(root: Path, source: str) -> list[str]:
    """Indicators of ``source`` with at least one stored payload."""
    manifest = root / "manifest.jsonl"
    if not manifest.exists():
        return []
    seen: set[str] = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a truncated final line, as in macrokit.snapshot
        if record.get("source") == source and record.get("path"):
            seen.add(record["indicator"])
    return sorted(seen)
```

- [ ] **Step 6: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_store.py -q`
Expected: `2 passed`.

- [ ] **Step 7: Register the member in the workspace and relock**

In `$WT/pyproject.toml`: add `"bond_timing_lab",` as the last entry of `[tool.uv.workspace] members` (after `"rates_volatility_model",`); add `"bond_timing_lab/tests",` as the last entry of `[tool.pytest.ini_options] testpaths`; under `[tool.ruff.lint.per-file-ignores]` add

```toml
"bond_timing_lab/**/*.py" = ["N803", "N806", "N816", "E741"]
```

Then:

```bash
cd $WT && uv lock && git diff --stat uv.lock
```

Expected: `uv.lock` gains the `bond-timing-lab` package entry only (no version changes of other packages; if `uv lock` wants to upgrade anything else, stop and report).

- [ ] **Step 8: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab pyproject.toml uv.lock && git commit -m "Add the bond_timing_lab workspace member and its raw store"
```

---

### Task 2: GSW zero curve within the published range

**Files:**
- Create: `bond_timing_lab/src/bond_timing/data/gsw.py`
- Test: `bond_timing_lab/tests/test_gsw.py`

**Interfaces:**
- Consumes: `macrokit.sources.us_term.GswDay` (`obs_date: date`, `params: (b0, b1, b2, b3, tau1, tau2)`), `parse_gsw(content) -> list[GswDay]`, `month_end_days(days) -> list[GswDay]`, `gsw_zero(day, months) -> np.ndarray` (annual %); `store.read_latest`, `store.MACROKIT_RAW`.
- Produces: `published_max_years(content: bytes) -> dict[date, int]`; `GswCurve(days: tuple[GswDay, ...], max_years: dict[date, int])` with `.zeros(days, months) -> np.ndarray` (decimal, NaN beyond the published range), `.month_ends() -> list[GswDay]` (no month in progress), `.days_by_month() -> dict[pd.Period, list[GswDay]]`; `parse_curve(content) -> GswCurve`; `load_curve(root=MACROKIT_RAW) -> GswCurve`; `month_end_zeros(curve, months: Sequence[int]) -> pd.DataFrame` (contiguous monthly `PeriodIndex`, integer-month columns).

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_gsw.py` (create)

```python
from datetime import date

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.gsw import month_end_zeros, parse_curve, published_max_years

HEADER = "Date,BETA0,BETA1,BETA2,BETA3,SVENY01,SVENY02,SVENY03,SVENY08,SVENY10,TAU1,TAU2"
ROWS = (
    "1971-07-30,5,0,0,0,5,5,5,NA,NA,1,NA",
    "1971-08-31,6,-2,0,0,4.4,4.8,5.0,5.6,5.7,2,NA",
    "1971-09-10,5,0,0,0,5,5,5,5,5,1,NA",
)


def payload(rows=ROWS) -> bytes:
    return ("A note line\n\n" + HEADER + "\n" + "\n".join(rows) + "\n").encode()


def test_published_max_years_reads_the_longest_published_column():
    assert published_max_years(payload()) == {
        date(1971, 7, 30): 3,
        date(1971, 8, 31): 10,
        date(1971, 9, 10): 10,
    }


def test_month_end_zeros_cut_at_the_published_range_and_drop_a_month_in_progress():
    frame = month_end_zeros(parse_curve(payload()), [12, 36, 120])
    assert list(frame.index.astype(str)) == ["1971-07", "1971-08"]
    july, august = pd.Period("1971-07", "M"), pd.Period("1971-08", "M")
    assert frame.loc[july, 12] == pytest.approx(0.05)
    assert np.isnan(frame.loc[july, 120])
    # Nelson-Siegel day (TAU2 = NA): 6 - 2 (1 - e^{-1/2}) / (1/2) percent at one year, tau1 = 2
    assert frame.loc[august, 12] == pytest.approx((6 - 2 * (1 - np.exp(-0.5)) / 0.5) / 100)
    assert np.isfinite(frame.loc[august, 120])


def test_days_by_month_groups_every_observation():
    grouped = parse_curve(payload()).days_by_month()
    assert [len(v) for v in grouped.values()] == [1, 1, 1]
    assert pd.Period("1971-09", "M") in grouped
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_gsw.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.data.gsw'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/data/gsw.py` (create)

```python
"""GSW zero curve from the macrokit snapshot, cut at the longest published maturity (design §4.1).

GSW publishes SVENYnn only up to the longest maturity its bond sample supports on each day
(1-7 years from 1961-06, 10 years from 1971-08-16, 15 from 1971-11-15, 20 from 1981-07-02,
30 from 1985-11-25; verified 2026-10-19). The Svensson parameters extrapolate beyond that;
those values are never used.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from macrokit.sources.us_term import GswDay, gsw_zero, month_end_days, parse_gsw

from .store import MACROKIT_RAW, read_latest

_MISSING = ("", "NA", None)


def published_max_years(content: bytes) -> dict[date, int]:
    """Longest maturity, in whole years, with a published SVENYnn value on each day."""
    lines = content.decode("utf-8", errors="replace").splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    out: dict[date, int] = {}
    for row in csv.DictReader(lines[start:]):
        published = [n for n in range(1, 31) if row.get(f"SVENY{n:02d}") not in _MISSING]
        out[date.fromisoformat(row["Date"])] = max(published, default=0)
    return out


@dataclass(frozen=True)
class GswCurve:
    days: tuple[GswDay, ...]
    max_years: dict[date, int]

    def zeros(self, days: Sequence[GswDay], months: Sequence[float]) -> np.ndarray:
        """Decimal continuously compounded zero yields; NaN beyond the published range."""
        grid = np.asarray(months, dtype=float)
        out = np.full((len(days), len(grid)), np.nan)
        for i, day in enumerate(days):
            inside = grid <= 12 * self.max_years.get(day.obs_date, 0) + 1e-9
            if inside.any():
                out[i, inside] = gsw_zero(day, grid[inside]) / 100.0
        return out

    def month_ends(self) -> list[GswDay]:
        """Last observation of each month, without a final month that is still in progress."""
        ends = month_end_days(self.days)
        if ends:
            last = pd.Timestamp(ends[-1].obs_date)
            if last != pd.offsets.BMonthEnd().rollforward(last):
                ends = ends[:-1]
        return ends

    def days_by_month(self) -> dict[pd.Period, list[GswDay]]:
        grouped: dict[pd.Period, list[GswDay]] = defaultdict(list)
        for day in sorted(self.days, key=lambda d: d.obs_date):
            grouped[pd.Period(day.obs_date, freq="M")].append(day)
        return dict(grouped)


def parse_curve(content: bytes) -> GswCurve:
    return GswCurve(tuple(parse_gsw(content)), published_max_years(content))


def load_curve(root: Path = MACROKIT_RAW) -> GswCurve:
    return parse_curve(read_latest(root, "us_term", "gsw"))


def month_end_zeros(curve: GswCurve, months: Sequence[int]) -> pd.DataFrame:
    ends = curve.month_ends()
    index = pd.PeriodIndex([pd.Period(d.obs_date, freq="M") for d in ends], freq="M")
    frame = pd.DataFrame(curve.zeros(ends, months), index=index, columns=list(months))
    return frame.reindex(pd.period_range(index[0], index[-1], freq="M"))
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_gsw.py -q`
Expected: `3 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Read GSW zero yields only inside the published maturity range"
```

---

### Task 3: DTB3 cash rate

**Files:**
- Create: `bond_timing_lab/src/bond_timing/data/fred.py`
- Test: `bond_timing_lab/tests/test_fred.py`

**Interfaces:**
- Consumes: `store.read_latest`, `store.RAW_ROOT`, `store.fetch` (network test only).
- Produces: `URL: str` (format with `series=`), `SERIES = ("DTB3", "TB3MS")`, `parse_fred_csv(content) -> pd.Series` (DatetimeIndex, NaN for blanks), `month_end_last(series) -> pd.Series` (contiguous monthly PeriodIndex), `missing_months(month_end) -> list[str]`, `bill_bey(discount_pct) -> pd.Series` (decimal), `bey_to_cc(bey) -> pd.Series`, `cash_returns(bey) -> pd.Series` (value at return month p = BEY(p−1)/12), `load_dtb3_bey(root=RAW_ROOT) -> pd.Series`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_fred.py` (create)

```python
import os

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fred import (
    URL,
    bey_to_cc,
    bill_bey,
    cash_returns,
    missing_months,
    month_end_last,
    parse_fred_csv,
)

CSV = (
    b"observation_date,DTB3\n2020-01-30,1.50\n2020-01-31,\n2020-02-27,1.40\n"
    b"2020-02-28,1.45\n2020-04-01,.\n2020-04-30,1.00\n"
)


def test_month_end_last_takes_the_last_valid_day_and_lists_gaps():
    month_end = month_end_last(parse_fred_csv(CSV))
    assert month_end[pd.Period("2020-01", "M")] == 1.50
    assert month_end[pd.Period("2020-02", "M")] == 1.45
    assert np.isnan(month_end[pd.Period("2020-03", "M")])
    assert month_end[pd.Period("2020-04", "M")] == 1.00
    assert missing_months(month_end) == ["2020-03"]


def test_bond_equivalent_yield_and_cash_alignment():
    index = pd.period_range("2020-01", periods=2, freq="M")
    bey = bill_bey(pd.Series([5.0, 4.0], index=index))
    assert bey.iloc[0] == pytest.approx(365 * 0.05 / (360 - 91 * 0.05))
    cash = cash_returns(bey)
    assert np.isnan(cash.iloc[0])
    assert cash.iloc[1] == pytest.approx(bey.iloc[0] / 12)


def test_bey_to_cc_matches_the_91_day_compounding():
    assert bey_to_cc(pd.Series([0.05])).iloc[0] == pytest.approx(
        np.log(1 + 0.05 * 91 / 365) * 365 / 91
    )


@pytest.mark.skipif(os.environ.get("BOND_TIMING_NETWORK") != "1", reason="network test")
def test_dtb3_endpoint_returns_the_expected_header():
    from bond_timing.data.store import fetch

    assert fetch(URL.format(series="DTB3")).startswith(b"observation_date,DTB3")
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_fred.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.data.fred'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/data/fred.py` (create)

```python
"""FRED series through the keyless CSV endpoint (design §4.2).

DTB3 is the 3-month bill on a discount basis (daily). The month-end value of month t sets
the cash return of month t+1. TB3MS is stored as a backup but never fills DTB3 gaps.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd

from .store import RAW_ROOT, read_latest

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES = ("DTB3", "TB3MS")


def parse_fred_csv(content: bytes) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(content), na_values=[".", ""])
    name = frame.columns[1]
    values = pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype=float)
    return pd.Series(values, index=pd.DatetimeIndex(pd.to_datetime(frame.iloc[:, 0])), name=name)


def month_end_last(series: pd.Series) -> pd.Series:
    """Last valid daily value of each calendar month (a holiday month-end takes an earlier day)."""
    valid = series.dropna()
    out = valid.groupby(valid.index.to_period("M")).last()
    return out.reindex(pd.period_range(out.index[0], out.index[-1], freq="M"))


def missing_months(month_end: pd.Series) -> list[str]:
    return [str(month) for month in month_end.index[month_end.isna()]]


def bill_bey(discount_pct: pd.Series) -> pd.Series:
    """Bond-equivalent yield (decimal) of a 91-day bill quoted on a discount basis."""
    d = discount_pct / 100.0
    return 365.0 * d / (360.0 - 91.0 * d)


def bey_to_cc(bey: pd.Series) -> pd.Series:
    """Continuously compounded annual rate equivalent to a 91-day bond-equivalent yield."""
    return np.log1p(bey * 91.0 / 365.0) * 365.0 / 91.0


def cash_returns(bey: pd.Series) -> pd.Series:
    """Simple cash return of return month p: the bill yield at the end of p-1, over 12."""
    return (bey / 12.0).shift(1)


def load_dtb3_bey(root: Path = RAW_ROOT) -> pd.Series:
    return bill_bey(month_end_last(parse_fred_csv(read_latest(root, "fred", "DTB3"))))
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_fred.py -q`
Expected: `3 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Turn DTB3 month-end discount yields into next-month cash returns"
```

---

### Task 4: Synthetic bond returns, targets and delayed-switch legs

**Files:**
- Create: `bond_timing_lab/src/bond_timing/returns.py`
- Test: `bond_timing_lab/tests/test_returns.py`

**Interfaces:**
- Consumes: `GswCurve` (`.zeros`, `.month_ends`, `.days_by_month`, `.days`) from Task 2; `macrokit.sources.us_term.GswDay`.
- Produces: constants `TLT_MONTHS = 204`, `IEF_MONTHS = 90`, `TEN_MONTHS = 120`, `INSTRUMENTS = {"tlt": 204, "ief": 90, "z10": 120}`, `DURATION = {"tlt": 17.0, "ief": 7.5, "z10": 10.0}`, `RX_YEARS = (2, ..., 10)`; `grid_months() -> list[int]`; `holding_log_return(zeros, n_months) -> pd.Series` (return months); `excess_simple(log_return, cash)`, `excess_log(log_return, cash)`; `rx12(zeros, n_years) -> pd.Series` (purchase months); `rolling_forward_sum(monthly, horizon=12)`; `Outcomes(rx12: DataFrame, xr1: Series, excess: DataFrame, monthly_log_excess: DataFrame)` with `.rxbar`; `real_outcomes(zeros, cash) -> Outcomes`; `world_outcomes(log_excess, excess) -> Outcomes`; `daily_synthetic_returns(curve, n_months, start: date) -> pd.Series`; `delayed_switch_excess(curve, n_months, cash, trading_day=5) -> pd.DataFrame` (columns `in`, `out`, return months).

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_returns.py` (create)

```python
from datetime import date

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.gsw import GswCurve
from bond_timing.returns import (
    delayed_switch_excess,
    grid_months,
    holding_log_return,
    real_outcomes,
    rolling_forward_sum,
    rx12,
)
from macrokit.sources.us_term import GswDay


def flat(rate: float = 0.05, periods: int = 30) -> pd.DataFrame:
    index = pd.period_range("2000-01", periods=periods, freq="M")
    return pd.DataFrame(rate, index=index, columns=grid_months())


def test_grid_has_every_maturity_the_returns_need():
    grid = set(grid_months())
    assert {12, 23, 24, 108, 119, 120, 89, 90, 203, 204} <= grid


def test_flat_curve_has_no_term_premium():
    zeros = flat()
    assert np.allclose(rx12(zeros, 10).dropna(), 0.0)
    assert np.allclose(holding_log_return(zeros, 120).dropna(), 0.05 / 12)


def test_rx12_matches_a_hand_calculation():
    zeros = flat()
    s = pd.Period("2001-01", "M")
    zeros.loc[s, 120], zeros.loc[s, 12], zeros.loc[s + 12, 108] = 0.06, 0.04, 0.07
    assert rx12(zeros, 10)[s] == pytest.approx(10 * 0.06 - 9 * 0.07 - 0.04)


def test_holding_return_buys_at_the_end_of_the_previous_month():
    zeros = flat()
    p = pd.Period("2000-06", "M")
    zeros.loc[p - 1, 120], zeros.loc[p, 119] = 0.06, 0.055
    assert holding_log_return(zeros, 120)[p] == pytest.approx(10 * 0.06 - 119 / 12 * 0.055)


def test_rolling_forward_sum_adds_the_next_twelve_months():
    index = pd.period_range("2000-01", periods=30, freq="M")
    monthly = pd.DataFrame({10: np.arange(1.0, 31.0)}, index=index)
    out = rolling_forward_sum(monthly, 12)
    assert out[10].iloc[0] == sum(range(2, 14))
    assert out[10].iloc[17] == sum(range(19, 31))
    assert np.isnan(out[10].iloc[18])


def test_real_outcomes_align_targets_and_instruments():
    zeros = flat()
    cash = pd.Series(0.004, index=zeros.index)
    out = real_outcomes(zeros, cash)
    s = pd.Period("2000-05", "M")
    assert out.xr1[s] == pytest.approx(out.monthly_log_excess[10][s + 1])
    assert out.excess["tlt"][s] == pytest.approx(np.expm1(0.05 / 12) - 0.004)
    assert list(out.rx12.columns) == list(range(2, 11))
    assert out.rxbar[s] == pytest.approx(0.0)


def test_delayed_switch_legs_on_a_flat_curve():
    days = tuple(
        GswDay(ts.date(), (6.0, 0.0, 0.0, 0.0, 1.0, 1.0))
        for ts in pd.bdate_range("2020-01-01", "2020-03-31")
    )
    curve = GswCurve(days, {d.obs_date: 30 for d in days})
    cash = pd.Series(0.0, index=pd.period_range("2020-01", "2020-03", freq="M"))
    legs = delayed_switch_excess(curve, 204, cash)
    february = pd.Period("2020-02", "M")
    t_old = (date(2020, 2, 7) - date(2020, 1, 31)).days / 365.25
    t_new = (date(2020, 2, 28) - date(2020, 2, 7)).days / 365.25
    assert legs.loc[february, "out"] == pytest.approx(np.expm1(0.06 * t_old))
    assert legs.loc[february, "in"] == pytest.approx(np.expm1(0.06 * t_new))
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_returns.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.returns'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/returns.py` (create)

```python
"""Synthetic zero-coupon bond returns and excess returns (design §4.3).

Yields are decimal, continuously compounded and annual; maturities are integer months. A
return month p is the holding period from the end of p-1 to the end of p. A purchase month
s indexes a target whose holding period starts at the end of s.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import pairwise

import numpy as np
import pandas as pd

from .data.gsw import GswCurve

TLT_MONTHS = 204  # 17 years, close to TLT's effective duration
IEF_MONTHS = 90  # 7.5 years
TEN_MONTHS = 120
INSTRUMENTS = {"tlt": TLT_MONTHS, "ief": IEF_MONTHS, "z10": TEN_MONTHS}
DURATION = {"tlt": 17.0, "ief": 7.5, "z10": 10.0}
RX_YEARS = tuple(range(2, 11))


def grid_months() -> list[int]:
    months = {m for n in range(1, 11) for m in (12 * n, 12 * n - 1)}
    months |= {IEF_MONTHS, IEF_MONTHS - 1, TLT_MONTHS, TLT_MONTHS - 1}
    return sorted(months)


def holding_log_return(zeros: pd.DataFrame, n_months: int) -> pd.Series:
    """Log return over month p of an n-month zero bought at the end of p-1 and sold at the end of p."""
    bought = zeros[n_months].shift(1) * (n_months / 12.0)
    sold = zeros[n_months - 1] * ((n_months - 1) / 12.0)
    return (bought - sold).rename(n_months)


def excess_simple(log_return: pd.Series, cash: pd.Series) -> pd.Series:
    return np.expm1(log_return) - cash


def excess_log(log_return: pd.Series, cash: pd.Series) -> pd.Series:
    return log_return - np.log1p(cash)


def rx12(zeros: pd.DataFrame, n_years: int) -> pd.Series:
    """One-year log excess return of an n-year zero bought at the end of s (the paper's target)."""
    n = n_years
    return (n * zeros[12 * n] - (n - 1) * zeros[12 * (n - 1)].shift(-12) - zeros[12]).rename(n)


def rolling_forward_sum(monthly: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
    """Value at s = sum of the monthly values of s+1 .. s+horizon."""
    return monthly.rolling(horizon).sum().shift(-horizon)


@dataclass(frozen=True)
class Outcomes:
    rx12: pd.DataFrame  # purchase month x maturity in years (2..10), log excess
    xr1: pd.Series  # purchase month: next-month log excess return of the 10-year zero
    excess: pd.DataFrame  # return month x instrument (tlt, ief, z10): simple excess over cash
    monthly_log_excess: pd.DataFrame  # return month x maturity in years (2..10)

    @property
    def rxbar(self) -> pd.Series:
        return self.rx12.mean(axis=1, skipna=False)


def real_outcomes(zeros: pd.DataFrame, cash: pd.Series) -> Outcomes:
    log_excess = pd.concat(
        {n: excess_log(holding_log_return(zeros, 12 * n), cash) for n in RX_YEARS}, axis=1
    )
    excess = pd.concat(
        {name: excess_simple(holding_log_return(zeros, m), cash) for name, m in INSTRUMENTS.items()},
        axis=1,
    )
    targets = pd.concat({n: rx12(zeros, n) for n in RX_YEARS}, axis=1)
    return Outcomes(targets, log_excess[10].shift(-1), excess, log_excess)


def world_outcomes(log_excess: pd.DataFrame, excess: pd.DataFrame) -> Outcomes:
    """Outcomes of a synthetic world; rx12 is the sum of the next twelve monthly log excess returns."""
    return Outcomes(rolling_forward_sum(log_excess, 12), log_excess[10].shift(-1), excess, log_excess)


def daily_synthetic_returns(curve: GswCurve, n_months: int, start: date) -> pd.Series:
    """Simple daily return of a constant-maturity n-month zero between GSW observation days."""
    days = [d for d in sorted(curve.days, key=lambda d: d.obs_date) if d.obs_date >= start]
    years = n_months / 12.0
    values, index = [], []
    for prev, day in pairwise(days):
        tau = (day.obs_date - prev.obs_date).days / 365.25
        bought = curve.zeros([prev], [n_months])[0, 0]
        sold = curve.zeros([day], [12.0 * (years - tau)])[0, 0]
        values.append(np.expm1(years * bought - (years - tau) * sold))
        index.append(pd.Timestamp(day.obs_date))
    return pd.Series(values, index=pd.DatetimeIndex(index), dtype=float)


def delayed_switch_excess(
    curve: GswCurve, n_months: int, cash: pd.Series, trading_day: int = 5
) -> pd.DataFrame:
    """Excess return of month p when a switch decided at the end of p-1 executes at the close of
    the ``trading_day``-th GSW observation day of p (design R5).

    ``in``: cash until that day, then a fresh n-month zero. ``out``: the zero bought at the end
    of p-1 until that day, then cash. Cash accrues linearly in calendar days.
    """
    ends = {pd.Period(d.obs_date, freq="M"): d for d in curve.month_ends()}
    by_month = curve.days_by_month()
    years = n_months / 12.0
    rows: dict[pd.Period, tuple[float, float]] = {}
    for p in sorted(ends):
        start, days, rf = ends.get(p - 1), by_month.get(p, []), cash.get(p, np.nan)
        if start is None or len(days) <= trading_day or not np.isfinite(rf):
            continue
        end, switch = ends[p], days[trading_day - 1]
        t_old = (switch.obs_date - start.obs_date).days / 365.25
        t_new = (end.obs_date - switch.obs_date).days / 365.25
        bought = curve.zeros([start], [n_months])[0, 0]
        aged, fresh = curve.zeros([switch], [12.0 * (years - t_old), n_months])[0]
        sold = curve.zeros([end], [12.0 * (years - t_new)])[0, 0]
        old_leg = years * bought - (years - t_old) * aged
        new_leg = years * fresh - (years - t_new) * sold
        share = t_old / (t_old + t_new)
        out_total = np.exp(old_leg) * (1.0 + rf * (1.0 - share)) - 1.0
        in_total = (1.0 + rf * share) * np.exp(new_leg) - 1.0
        rows[p] = (in_total - rf, out_total - rf)
    frame = pd.DataFrame.from_dict(rows, orient="index", columns=["in", "out"])
    frame.index = pd.PeriodIndex(frame.index, freq="M")
    return frame
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_returns.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Build synthetic zero-coupon returns, rx12 targets and delayed-switch legs"
```

---

### Task 5: Point-in-time rules R1–R4 (G2)

**Files:**
- Create: `bond_timing_lab/src/bond_timing/pit.py`
- Test: `bond_timing_lab/tests/test_pit.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `LookaheadError(RuntimeError)`; `check_observed(months, t)`; `check_vintage(vintage, t)`; `check_targets_complete(starts, t, horizon)`; `training_starts(starts: pd.PeriodIndex, t, horizon, *, complete=True) -> pd.PeriodIndex`; `check_embargo(core, validation, horizon)`; `Split(core: np.ndarray, validation: np.ndarray)` (positions); `validation_split(starts, horizon, *, fraction=0.15, embargo=True) -> Split`; `check_fit_window(months: pd.PeriodIndex, end)`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_pit.py` (create)

```python
import pandas as pd
import pytest
from bond_timing.pit import (
    LookaheadError,
    check_embargo,
    check_fit_window,
    check_observed,
    check_targets_complete,
    check_vintage,
    training_starts,
    validation_split,
)


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def test_r1_rejects_rows_after_the_decision():
    check_observed([month("2000-01"), month("2000-02")], month("2000-02"))
    with pytest.raises(LookaheadError):
        check_observed([month("2000-01"), month("2000-03")], month("2000-02"))


def test_r1_rejects_a_vintage_not_yet_published():
    check_vintage(month("2000-05"), month("2000-06"))
    for vintage in (month("2000-06"), month("2000-07")):
        with pytest.raises(LookaheadError):
            check_vintage(vintage, month("2000-06"))


def test_r2_keeps_only_completed_targets():
    starts = pd.period_range("1990-01", "2000-12", freq="M")
    assert training_starts(starts, month("2000-12"), 12).max() == month("1999-12")
    assert training_starts(starts, month("2000-12"), 1).max() == month("2000-11")


def test_r2_check_rejects_an_unrealized_target():
    with pytest.raises(LookaheadError):
        check_targets_complete(pd.PeriodIndex([month("2000-01")]), month("2000-06"), 12)


def test_v0_mode_keeps_unrealized_targets():
    starts = pd.period_range("1990-01", "2000-12", freq="M")
    assert training_starts(starts, month("2000-12"), 12, complete=False).max() == month("2000-11")


def test_r3_embargo_leaves_h_months_between_fitting_and_validation():
    starts = pd.period_range("1990-01", periods=100, freq="M")
    split = validation_split(starts, 12)
    assert len(split.validation) == 15
    assert len(split.core) == 74  # positions 0..73: s + 12 <= the first validation start
    assert starts[split.core].max() + 12 <= starts[split.validation].min()


def test_r3_without_embargo_uses_every_earlier_row():
    starts = pd.period_range("1990-01", periods=100, freq="M")
    assert len(validation_split(starts, 12, embargo=False).core) == 85


def test_r3_check_rejects_an_overlap():
    with pytest.raises(LookaheadError):
        check_embargo(pd.PeriodIndex([month("1999-01")]), pd.PeriodIndex([month("1999-06")]), 12)


def test_r4_rejects_a_transform_fitted_past_the_window():
    check_fit_window(pd.PeriodIndex([month("1999-01")]), month("1999-01"))
    with pytest.raises(LookaheadError):
        check_fit_window(pd.PeriodIndex([month("1999-01"), month("1999-03")]), month("1999-02"))
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_pit.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.pit'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/pit.py` (create)

```python
"""Point-in-time rules R1-R4 as checks that raise (design §5; G2 tests them).

R1  a decision at month t uses data observed by t; macro comes from vintage t-1.
R2  training pairs (x_s, y_{s->s+h}) need s + h <= t.
R3  validation is the last 15 % of the pairs, with an h-month gap before it.
R4  transforms are fitted on the training window only.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd


class LookaheadError(RuntimeError):
    """An input would let the decision at month t use information from after t."""


def check_observed(months: Iterable[pd.Period], t: pd.Period) -> None:
    late = [m for m in months if m > t]
    if late:
        raise LookaheadError(f"data for {late[0]} used at the decision of {t}")


def check_vintage(vintage: pd.Period, t: pd.Period) -> None:
    if vintage >= t:
        raise LookaheadError(f"vintage {vintage} is not certainly published by the end of {t}")


def check_targets_complete(starts: pd.PeriodIndex, t: pd.Period, horizon: int) -> None:
    if len(starts) and starts.max() + horizon > t:
        raise LookaheadError(f"the target starting {starts.max()} ends after the refit at {t}")


def training_starts(
    starts: pd.PeriodIndex, t: pd.Period, horizon: int, *, complete: bool = True
) -> pd.PeriodIndex:
    """Purchase months a refit at t may train on: s + h <= t, or s <= t - 1 for V0 (complete=False)."""
    limit = t - horizon if complete else t - 1
    chosen = starts[starts <= limit]
    if complete:
        check_targets_complete(chosen, t, horizon)
    return chosen


def check_embargo(core: pd.PeriodIndex, validation: pd.PeriodIndex, horizon: int) -> None:
    if len(core) and len(validation) and core.max() + horizon > validation.min():
        raise LookaheadError(
            f"the fitting target from {core.max()} overlaps validation from {validation.min()}"
        )


@dataclass(frozen=True)
class Split:
    core: np.ndarray  # positions of the rows that fit the candidates
    validation: np.ndarray  # positions of the rows that score them


def validation_split(
    starts: pd.PeriodIndex, horizon: int, *, fraction: float = 0.15, embargo: bool = True
) -> Split:
    order = np.argsort(starts.asi8, kind="stable")
    n_val = int(np.ceil(fraction * len(order)))
    validation = order[len(order) - n_val :]
    core = order[: len(order) - n_val]
    if embargo:
        first = starts[validation].min()
        core = core[np.asarray(starts[core] <= first - horizon)]
        check_embargo(starts[core], starts[validation], horizon)
    return Split(core, validation)


def check_fit_window(months: pd.PeriodIndex, end: pd.Period) -> None:
    if len(months) and months.max() > end:
        raise LookaheadError(f"a transform was fitted on {months.max()}, after the window end {end}")
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_pit.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Encode the point-in-time rules R1-R4 as checks that raise"
```

---

### Task 6: FRED-MD vintages and the macro sources

**Files:**
- Create: `bond_timing_lab/src/bond_timing/data/fredmd.py`
- Test: `bond_timing_lab/tests/test_fredmd.py`

**Interfaces:**
- Consumes: `pit.check_vintage` (Task 5).
- Produces: `BASE`, `HISTORICAL: dict[str, str]` (`hist_1999_2014`, `hist_2015_2025`), `FIRST_MONTHLY = Period("2026-01")`, `monthly_urls(month) -> list[str]`, `member_vintage(name) -> pd.Period | None`, `zip_vintages(content) -> dict[pd.Period, bytes]`, `Vintage(vintage, levels, tcodes)` with cached `.transformed`, `parse_vintage(vintage, content) -> Vintage`, `transform(x, tcode) -> pd.Series`, `MAX_LAG = 6`, `MacroView(names: tuple[str, ...], lags: tuple[int, ...])`, `lagged_values(frame, view, rows) -> np.ndarray`, `latest_values(frame, view, t) -> np.ndarray`, and three sources with the same three methods — `view(t) -> MacroView`, `history(t, view, rows: pd.PeriodIndex) -> np.ndarray (rows x J)`, `edge(t, view) -> np.ndarray (J,)`: `RealTimeMacro(vintage: Callable[[pd.Period], Vintage])`, `FinalMacro(vintage: Vintage)`, `PanelMacro(frame: pd.DataFrame, lag: int = 2)`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_fredmd.py` (create)

```python
import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fredmd import (
    FinalMacro,
    PanelMacro,
    RealTimeMacro,
    member_vintage,
    parse_vintage,
    transform,
    zip_vintages,
)
from bond_timing.pit import LookaheadError

VINTAGE = b"""sasdate,AAA,BBB,CCC,DDD,EEE,FFF,GGG
Transform:,1,2,4,5,6,7,3
1/1/2000,1,10,100,100,100,100,1
2/1/2000,2,12,110,110,121,110,4
3/1/2000,4,15,121,121,144,132,9
4/1/2000,,19,133.1,,169,,16
"""
LATER = b"""sasdate,BBB
Transform:,2
1/1/2000,10
2/1/2000,12
3/1/2000,15
4/1/2000,19
5/1/2000,
"""


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def test_parse_reads_codes_dates_and_blanks():
    v = parse_vintage(month("2000-05"), VINTAGE)
    assert v.tcodes == {"AAA": 1, "BBB": 2, "CCC": 4, "DDD": 5, "EEE": 6, "FFF": 7, "GGG": 3}
    assert list(v.levels.index.astype(str)) == ["2000-01", "2000-02", "2000-03", "2000-04"]
    assert np.isnan(v.levels.loc[month("2000-04"), "AAA"])


def test_every_tcode_matches_a_hand_calculation():
    t = parse_vintage(month("2000-05"), VINTAGE).transformed
    np.testing.assert_allclose(t["AAA"], [1, 2, 4, np.nan])
    np.testing.assert_allclose(t["BBB"], [np.nan, 2, 3, 4])
    np.testing.assert_allclose(t["CCC"], np.log([100, 110, 121, 133.1]))
    np.testing.assert_allclose(t["DDD"], [np.nan, np.log(1.1), np.log(1.1), np.nan])
    second = [np.nan, np.nan, np.log(144 / 121) - np.log(1.21), np.log(169 / 144) - np.log(144 / 121)]
    np.testing.assert_allclose(t["EEE"], second)
    np.testing.assert_allclose(t["FFF"], [np.nan, np.nan, 0.1, np.nan])
    np.testing.assert_allclose(t["GGG"], [np.nan, np.nan, 2, 2])
    with pytest.raises(ValueError):
        transform(pd.Series([1.0]), 9)


def test_member_names_from_both_archives():
    assert member_vintage("Historical FRED-MD Vintages Final/1999-08.csv") == month("1999-08")
    assert member_vintage("FRED-MD_2024m03.csv") == month("2024-03")
    assert member_vintage("FRED-MD-2025m05.csv") == month("2025-05")
    assert member_vintage("2017-02.csv") == month("2017-02")
    assert member_vintage("Historical FRED-MD Vintages Final/ReadMe.pdf") is None


def test_zip_vintages_keys_every_csv_member():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("Final/2000-05.csv", VINTAGE)
        archive.writestr("FRED-MD_2024m03.csv", LATER)
        archive.writestr("Final/ReadMe.pdf", b"%PDF")
    assert sorted(zip_vintages(buffer.getvalue())) == [month("2000-05"), month("2024-03")]


def test_real_time_view_keeps_each_series_lag():
    source = RealTimeMacro({month("2000-05"): parse_vintage(month("2000-05"), VINTAGE)}.__getitem__)
    view = source.view(month("2000-06"))
    lags = dict(zip(view.names, view.lags, strict=True))
    assert lags == {"AAA": 3, "BBB": 2, "CCC": 2, "DDD": 3, "EEE": 2, "FFF": 3, "GGG": 2}
    rows = pd.PeriodIndex([month("2000-05"), month("2000-06")])
    history = source.history(month("2000-06"), view, rows)
    np.testing.assert_allclose(history[:, view.names.index("BBB")], [3, 4])
    assert source.edge(month("2000-06"), view)[view.names.index("AAA")] == 4


def test_series_lagging_more_than_six_months_are_left_out():
    source = RealTimeMacro({month("2000-09"): parse_vintage(month("2000-09"), VINTAGE)}.__getitem__)
    assert source.view(month("2000-10")).names == ("BBB", "CCC", "EEE", "GGG")  # lag 6 kept, 7 not
    source = RealTimeMacro({month("2000-10"): parse_vintage(month("2000-10"), VINTAGE)}.__getitem__)
    assert source.view(month("2000-11")).names == ()


def test_edge_falls_back_and_marks_missing_series():
    vintages = {
        month("2000-05"): parse_vintage(month("2000-05"), VINTAGE),
        month("2000-06"): parse_vintage(month("2000-06"), LATER),
    }
    source = RealTimeMacro(vintages.__getitem__)
    view = source.view(month("2000-06"))
    edge = source.edge(month("2000-07"), view)
    assert np.isnan(edge[view.names.index("AAA")])
    assert edge[view.names.index("BBB")] == 4  # 2000-05 is blank; 2000-04 is the latest
    assert edge.shape == (len(view.names),)


def test_real_time_source_never_reads_the_decision_month_vintage():
    source = RealTimeMacro({}.__getitem__)
    with pytest.raises(KeyError):
        source.view(month("2000-06"))
    with pytest.raises(LookaheadError):
        source._frame_at(month("2000-06"), month("2000-06"))


def test_final_and_panel_sources():
    final = FinalMacro(parse_vintage(month("2019-02"), VINTAGE))
    view = final.view(month("2000-03"))
    assert set(view.lags) == {0}
    assert final.edge(month("2000-03"), view)[view.names.index("BBB")] == 3
    panel = PanelMacro(pd.DataFrame({"x": [1.0, 2.0, 3.0]}, index=pd.period_range("2000-01", periods=3, freq="M")))
    pview = panel.view(month("2000-03"))
    assert pview.lags == (2,)
    assert panel.edge(month("2000-03"), pview)[0] == 1.0
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_fredmd.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.data.fredmd'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/data/fredmd.py` (create)

```python
"""FRED-MD vintages: archive members, parsing, tcode transforms and macro sources (design §4.4).

Verified 2026-10-19: vintage v holds data through v-1; the first row is the header
(``sasdate``), the second the ``Transform:`` codes; dates are ``M/D/YYYY``; the newest row is
ragged (several series blank). Archive members are ``.../1999-08.csv``, ``2017-02.csv``,
``FRED-MD_2024m03.csv`` or ``FRED-MD-2025m05.csv``. Monthly files from 2026 are
``monthly/YYYY-MM-md.csv`` (2026-08 was published as ``monthly/2026-rev-08-md.csv``).
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property

import numpy as np
import pandas as pd

from ..pit import check_vintage

BASE = "https://www.stlouisfed.org/-/media/project/frbstl/stlouisfed/research/fred-md"
HISTORICAL = {
    "hist_1999_2014": f"{BASE}/historical_fred-md.zip",
    "hist_2015_2025": f"{BASE}/historical-vintages-of-fred-md-2015-01-to-2025-12.zip",
}
FIRST_MONTHLY = pd.Period("2026-01", "M")
MAX_LAG = 6
_MEMBER = re.compile(r"(\d{4})(?:-|m)(\d{2})\.csv$")
_NA = {"", "NA", "NaN", "nan", "."}


def monthly_urls(month: pd.Period) -> list[str]:
    return [
        f"{BASE}/monthly/{month.year:04d}-{month.month:02d}-md.csv",
        f"{BASE}/monthly/{month.year:04d}-rev-{month.month:02d}-md.csv",
    ]


def member_vintage(name: str) -> pd.Period | None:
    match = _MEMBER.search(name.rsplit("/", 1)[-1])
    return pd.Period(f"{match.group(1)}-{match.group(2)}", "M") if match else None


def zip_vintages(content: bytes) -> dict[pd.Period, bytes]:
    out: dict[pd.Period, bytes] = {}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        for name in archive.namelist():
            vintage = member_vintage(name)
            if vintage is None:
                continue
            if vintage in out:
                raise ValueError(f"vintage {vintage} appears twice in the archive")
            out[vintage] = archive.read(name)
    return out


def transform(x: pd.Series, tcode: int) -> pd.Series:
    """McCracken-Ng codes: 1 level, 2 diff, 3 diff2, 4 log, 5 dlog, 6 d2log, 7 d(x/x[-1] - 1)."""
    if tcode == 1:
        return x
    if tcode == 2:
        return x.diff()
    if tcode == 3:
        return x.diff().diff()
    if tcode in (4, 5, 6):
        logged = np.log(x.where(x > 0))
        if tcode == 4:
            return logged
        return logged.diff() if tcode == 5 else logged.diff().diff()
    if tcode == 7:
        return (x / x.shift(1) - 1.0).diff()
    raise ValueError(f"unknown FRED-MD tcode {tcode}")


@dataclass(frozen=True)
class Vintage:
    vintage: pd.Period
    levels: pd.DataFrame  # data month x series, contiguous monthly index
    tcodes: dict[str, int]

    @cached_property
    def transformed(self) -> pd.DataFrame:
        return pd.DataFrame(
            {name: transform(self.levels[name], code) for name, code in self.tcodes.items()},
            index=self.levels.index,
        )


def parse_vintage(vintage: pd.Period, content: bytes) -> Vintage:
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig", errors="replace"))))
    header = [cell.strip() for cell in rows[0]]
    if header[0].lower() != "sasdate":
        raise ValueError(f"vintage {vintage}: the first header cell is {header[0]!r}")
    if not rows[1] or not rows[1][0].strip().lower().startswith("transform"):
        raise ValueError(f"vintage {vintage}: the second row is not the Transform: row")
    names = header[1:]
    codes: dict[str, int] = {}
    for name, code in zip(names, rows[1][1:], strict=False):
        if name and name not in codes and code.strip() not in _NA:
            codes[name] = int(float(code))
    months, values = [], []
    for row in rows[2:]:
        if not row or not row[0].strip():
            continue
        months.append(pd.Period(datetime.strptime(row[0].strip(), "%m/%d/%Y"), freq="M"))
        cells = [cell.strip() for cell in row[1 : 1 + len(names)]]
        cells += [""] * (len(names) - len(cells))
        values.append([np.nan if cell in _NA else float(cell) for cell in cells])
    frame = pd.DataFrame(values, index=pd.PeriodIndex(months, freq="M"), columns=names)
    frame = frame.loc[:, ~frame.columns.duplicated()]
    frame = frame.loc[:, [name for name in frame.columns if name in codes]]
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    frame = frame.reindex(pd.period_range(frame.index[0], frame.index[-1], freq="M"))
    return Vintage(vintage, frame, {name: codes[name] for name in frame.columns})


@dataclass(frozen=True)
class MacroView:
    """The series one refit uses and the publication lag (months) each keeps all year."""

    names: tuple[str, ...]
    lags: tuple[int, ...]


def lagged_values(frame: pd.DataFrame, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
    """x_j(s - lag_j) for every row s; NaN where the series or the month is absent."""
    out = np.full((len(rows), len(view.names)), np.nan)
    for j, (name, lag) in enumerate(zip(view.names, view.lags, strict=True)):
        if name in frame.columns:
            out[:, j] = frame[name].reindex(rows - lag).to_numpy(dtype=float)
    return out


def latest_values(frame: pd.DataFrame, view: MacroView, t: pd.Period) -> np.ndarray:
    """The latest value at or before t - lag_j of each series; NaN if the series is absent."""
    out = np.full(len(view.names), np.nan)
    for j, (name, lag) in enumerate(zip(view.names, view.lags, strict=True)):
        if name in frame.columns:
            column = frame[name].loc[: t - lag].dropna()
            if len(column):
                out[j] = column.iloc[-1]
    return out


class RealTimeMacro:
    """Decision t sees vintage t-1 (R1). A series' lag is t minus its last valid month there."""

    def __init__(self, vintage: Callable[[pd.Period], Vintage]):
        self._vintage = vintage

    def _frame_at(self, vintage: pd.Period, t: pd.Period) -> pd.DataFrame:
        check_vintage(vintage, t)
        return self._vintage(vintage).transformed

    def view(self, t: pd.Period) -> MacroView:
        frame = self._frame_at(t - 1, t)
        names, lags = [], []
        for name in frame.columns:
            last = frame[name].last_valid_index()
            if last is not None and (t - last).n <= MAX_LAG:
                names.append(name)
                lags.append((t - last).n)
        return MacroView(tuple(names), tuple(lags))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame_at(t - 1, t), view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame_at(t - 1, t), view, t)


class FinalMacro:
    """One vintage for every decision, publication lag ignored (design §7, V0-V2)."""

    def __init__(self, vintage: Vintage):
        self._frame = vintage.transformed

    def view(self, t: pd.Period) -> MacroView:
        return MacroView(tuple(self._frame.columns), (0,) * len(self._frame.columns))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame, view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame, view, t)


class PanelMacro:
    """A single panel seen with one lag for every series (the simulated macro of G3)."""

    def __init__(self, frame: pd.DataFrame, lag: int = 2):
        self._frame, self._lag = frame, lag

    def view(self, t: pd.Period) -> MacroView:
        return MacroView(tuple(self._frame.columns), (self._lag,) * len(self._frame.columns))

    def history(self, t: pd.Period, view: MacroView, rows: pd.PeriodIndex) -> np.ndarray:
        return lagged_values(self._frame, view, rows)

    def edge(self, t: pd.Period, view: MacroView) -> np.ndarray:
        return latest_values(self._frame, view, t)
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_fredmd.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Parse every real vintage once (smoke check against the probe archives)**

```bash
cd $WT && $PY - <<'EOF'
from pathlib import Path
from bond_timing.data.fredmd import parse_vintage, zip_vintages
probe = Path("/tmp/claude-1000/-home-kazumasa-projects/df1bf6ad-598d-44e3-a3ed-6b1df2d7d491/scratchpad/probe/fredmd")
payloads = {}
for name in ("hist1.zip", "hist2.zip"):
    payloads.update(zip_vintages((probe / name).read_bytes()))
bad = []
for v, content in sorted(payloads.items()):
    try:
        parsed = parse_vintage(v, content)
        assert parsed.levels.index[-1] == v - 1, (v, parsed.levels.index[-1])
        parsed.transformed
    except Exception as exc:  # report every failure, then stop
        bad.append((str(v), repr(exc)[:200]))
print(len(payloads), "vintages;", len(bad), "failures"); print(bad[:10])
EOF
```

Expected: `317 vintages; 0 failures` (185 + 132). A vintage whose last row is not v−1 is a finding: list it, keep the parser, and record the exception in the ledger.

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Parse FRED-MD vintages and serve real-time, final and panel macro views"
```

---

### Task 7: Liu–Wu, ETF prices and the snapshot command

**Files:**
- Create: `bond_timing_lab/src/bond_timing/data/liuwu.py`, `bond_timing_lab/src/bond_timing/data/etf.py`, `bond_timing_lab/src/bond_timing/data/snapshot.py`
- Test: `bond_timing_lab/tests/test_liuwu.py`, `bond_timing_lab/tests/test_etf.py`, `bond_timing_lab/tests/test_snapshot.py`

**Interfaces:**
- Consumes: `store.fetch`, `store.store_bytes`, `store.read_latest`, `store.FetchError`, `store.RAW_ROOT`, `store.MACROKIT_RAW` (Task 1); `fred.URL`, `fred.SERIES` (Task 3); `fredmd.HISTORICAL`, `fredmd.FIRST_MONTHLY`, `fredmd.monthly_urls` (Task 6); `macrokit.snapshot.latest_payload`.
- Produces: `liuwu.URLS`, `liuwu.parse_liuwu(content) -> pd.DataFrame` (contiguous monthly index, integer-month columns 1..360, decimal), `liuwu.load_liuwu(root=RAW_ROOT)`; `etf.TICKERS`, `etf.download_csv(ticker) -> bytes` (`date,close`), `etf.parse_prices(content) -> pd.Series`, `etf.monthly_total_returns(prices) -> pd.Series` (return months, no month in progress), `etf.daily_returns(prices)`, `etf.load_prices(ticker, root=RAW_ROOT)`; `snapshot.snapshot_all(root=RAW_ROOT, macrokit_root=MACROKIT_RAW, *, today: pd.Period | None = None) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

File: `bond_timing_lab/tests/test_liuwu.py` (create)

```python
import numpy as np
import openpyxl
import pandas as pd
import pytest
from bond_timing.data.liuwu import parse_liuwu


def workbook(tmp_path) -> bytes:
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(['Data source: Yan Liu and Jing Cynthia Wu, "Reconstructing the Yield Curve"'])
    sheet.append(['Date (first column) in "YYYYMM"'])
    sheet.append(["Data: Annualized continuously-compounded zero-coupon yields in percentage points."])
    sheet.append([None])
    sheet.append([None, "  1 m", "  2 m", " 12 m"])
    sheet.append([196106, 2.0, 2.1, 3.0])
    sheet.append([196108, 2.2, None, 3.1])
    path = tmp_path / "liuwu.xlsx"
    book.save(path)
    return path.read_bytes()


def test_parse_liuwu_reads_months_maturities_and_blanks(tmp_path):
    frame = parse_liuwu(workbook(tmp_path))
    assert list(frame.columns) == [1, 2, 12]
    assert list(frame.index.astype(str)) == ["1961-06", "1961-07", "1961-08"]
    assert frame.loc[pd.Period("1961-06", "M"), 12] == pytest.approx(0.03)
    assert np.isnan(frame.loc[pd.Period("1961-08", "M"), 2])
    assert frame.loc[pd.Period("1961-07", "M")].isna().all()
```

File: `bond_timing_lab/tests/test_etf.py` (create)

```python
import pandas as pd
import pytest
from bond_timing.data.etf import daily_returns, monthly_total_returns, parse_prices


def test_parse_prices_round_trip():
    prices = parse_prices(b"date,close\n2020-01-30,100\n2020-01-31,101\n")
    assert prices.index[1] == pd.Timestamp("2020-01-31") and prices.iloc[1] == 101.0


def test_monthly_total_returns_drop_a_month_in_progress():
    index = pd.to_datetime(["2020-01-30", "2020-01-31", "2020-02-28", "2020-03-10"])
    prices = pd.Series([100.0, 101.0, 103.02, 104.0], index=index)
    returns = monthly_total_returns(prices)
    assert list(returns.index.astype(str)) == ["2020-02"]
    assert returns.iloc[0] == pytest.approx(103.02 / 101.0 - 1)
    assert daily_returns(prices).iloc[0] == pytest.approx(0.01)
```

File: `bond_timing_lab/tests/test_snapshot.py` (create)

```python
import io
import zipfile

import pandas as pd
from bond_timing.data import snapshot
from bond_timing.data.store import FetchError, indicators, store_bytes


def archive(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        for name, content in members.items():
            handle.writestr(name, content)
    return buffer.getvalue()


def test_snapshot_stores_every_source_and_lists_unpublished_months(tmp_path, monkeypatch):
    vintages = archive({"1999-08.csv": b"sasdate,A\nTransform:,1\n1/1/1999,1\n"})

    def fake_fetch(url: str) -> bytes:
        if url.endswith(".zip"):
            return vintages
        if url.endswith("monthly/2026-01-md.csv"):
            return b"sasdate,A\nTransform:,1\n12/1/2025,1\n"
        if "fredgraph" in url:
            return b"observation_date,X\n2020-01-02,1\n"
        if url.startswith("https://docs.google.com"):
            return b"PK not really a workbook"
        raise FetchError(f"GET {url} returned 404")

    monkeypatch.setattr(snapshot, "fetch", fake_fetch)
    monkeypatch.setattr(snapshot.etf, "download_csv", lambda ticker: b"date,close\n2020-01-02,1\n")
    gsw_root = tmp_path / "macrokit"
    store_bytes(gsw_root, "us_term", "gsw", b"Date,", url="https://example.invalid", filename="g.csv")
    raw = tmp_path / "raw"
    lines = snapshot.snapshot_all(raw, gsw_root, today=pd.Period("2026-02", "M"))
    assert indicators(raw, "fredmd") == ["hist_1999_2014", "hist_2015_2025", "monthly_2026-01"]
    assert indicators(raw, "fred") == ["DTB3", "TB3MS"]
    assert indicators(raw, "etf") == ["BIL", "IEF", "TLT"]
    assert indicators(raw, "liuwu") == ["monthly"]
    assert "fredmd/monthly_2026-02: not published" in lines
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_liuwu.py bond_timing_lab/tests/test_etf.py bond_timing_lab/tests/test_snapshot.py -q`
Expected: FAIL with `ModuleNotFoundError` for `bond_timing.data.liuwu`, `bond_timing.data.etf` and `bond_timing.data.snapshot`.

- [ ] **Step 3: Write the three modules**

File: `bond_timing_lab/src/bond_timing/data/liuwu.py` (create)

```python
"""Liu-Wu monthly zero curve (design §4.1).

Verified 2026-10-19: one sheet; a few note rows, then a header row whose cells read
``'  1 m'`` .. ``'360 m'``; data rows start with an integer ``YYYYMM``; yields are annual
percent, continuously compounded; long maturities are blank early in the sample. The author's
page links the file as a Google Drive spreadsheet (sample 1961-06..2025-12 at download).
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from .store import RAW_ROOT, read_latest

FILE_ID = "1-wmStGZHLx55dSYi3gQK2vb3F8dMw_Nb"
URLS = (
    f"https://docs.google.com/spreadsheets/d/{FILE_ID}/export?format=xlsx",
    f"https://drive.google.com/uc?export=download&id={FILE_ID}",
)


def parse_liuwu(content: bytes) -> pd.DataFrame:
    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = list(book.worksheets[0].iter_rows(values_only=True))
    header_at = next(
        i
        for i, row in enumerate(rows)
        if len(row) > 1 and isinstance(row[1], str) and row[1].strip() == "1 m"
    )
    labels = [cell for cell in rows[header_at][1:] if cell is not None]
    maturities = [int(str(label).split()[0]) for label in labels]
    months, values = [], []
    for row in rows[header_at + 1 :]:
        if not row or row[0] is None:
            continue
        code = int(row[0])
        months.append(pd.Period(year=code // 100, month=code % 100, freq="M"))
        cells = list(row[1 : 1 + len(maturities)])
        cells += [None] * (len(maturities) - len(cells))
        values.append([np.nan if cell is None else float(cell) / 100.0 for cell in cells])
    frame = pd.DataFrame(values, index=pd.PeriodIndex(months, freq="M"), columns=maturities)
    return frame.reindex(pd.period_range(frame.index[0], frame.index[-1], freq="M"))


def load_liuwu(root: Path = RAW_ROOT) -> pd.DataFrame:
    return parse_liuwu(read_latest(root, "liuwu", "monthly"))
```

File: `bond_timing_lab/src/bond_timing/data/etf.py` (create)

```python
"""TLT, IEF and BIL total-return prices from yfinance (design §4.3; G0 and supplementary tables)."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from .store import RAW_ROOT, read_latest

TICKERS = ("TLT", "IEF", "BIL")
START = "2002-01-01"


def download_csv(ticker: str) -> bytes:
    """Dividend-adjusted daily closes as ``date,close`` CSV bytes."""
    import yfinance as yf

    frame = yf.download(
        ticker, start=START, auto_adjust=True, actions=False, progress=False, threads=False
    )
    close = frame["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    index = pd.DatetimeIndex(close.index)
    if index.tz is not None:
        index = index.tz_localize(None)
    out = pd.DataFrame(
        {"close": close.to_numpy(dtype=float)}, index=pd.DatetimeIndex(index, name="date")
    )
    return out.to_csv(float_format="%.10g").encode()


def parse_prices(content: bytes) -> pd.Series:
    frame = pd.read_csv(io.BytesIO(content), index_col="date", parse_dates=["date"])
    return frame["close"].astype(float)


def monthly_total_returns(prices: pd.Series) -> pd.Series:
    """Month-end to month-end returns, without a final month that is still in progress."""
    month_end = prices.groupby(prices.index.to_period("M")).last()
    last = prices.index[-1]
    if last != pd.offsets.BMonthEnd().rollforward(last):
        month_end = month_end.iloc[:-1]
    return (month_end / month_end.shift(1) - 1.0).iloc[1:]


def daily_returns(prices: pd.Series) -> pd.Series:
    return (prices / prices.shift(1) - 1.0).iloc[1:]


def load_prices(ticker: str, root: Path = RAW_ROOT) -> pd.Series:
    return parse_prices(read_latest(root, "etf", ticker))
```

File: `bond_timing_lab/src/bond_timing/data/snapshot.py` (create)

```python
"""Fetch every raw input into the bond-timing store (design §4.5).

GSW is not fetched here: it is read from the macrokit store (`macrokit us-term`).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
from macrokit.snapshot import latest_payload

from . import etf, fred, fredmd, liuwu
from .store import MACROKIT_RAW, RAW_ROOT, FetchError, fetch, store_bytes


def snapshot_all(
    root: Path = RAW_ROOT, macrokit_root: Path = MACROKIT_RAW, *, today: pd.Period | None = None
) -> list[str]:
    lines: list[str] = []

    def keep(source: str, indicator: str, content: bytes, url: str, filename: str) -> None:
        result = store_bytes(root, source, indicator, content, url=url, filename=filename)
        state = "stored" if result.changed else "unchanged"
        lines.append(
            f"{source}/{indicator}: {state}, {result.size:,} bytes, sha256 {result.sha256[:12]}"
        )

    for series in fred.SERIES:
        url = fred.URL.format(series=series)
        keep("fred", series, fetch(url), url, f"{series}.csv")
    for indicator, url in fredmd.HISTORICAL.items():
        content = fetch(url)
        if content[:2] != b"PK":
            raise FetchError(f"{url} did not return a zip archive")
        keep("fredmd", indicator, content, url, f"{indicator}.zip")
    month = fredmd.FIRST_MONTHLY
    last = today if today is not None else pd.Period(date.today(), freq="M")
    while month <= last:
        for url in fredmd.monthly_urls(month):
            try:
                content = fetch(url)
            except FetchError:
                continue
            if content.lstrip()[:7].lower() == b"sasdate":
                keep("fredmd", f"monthly_{month}", content, url, f"{month}-md.csv")
                break
        else:
            lines.append(f"fredmd/monthly_{month}: not published")
        month += 1
    for url in liuwu.URLS:
        try:
            content = fetch(url)
        except FetchError:
            continue
        if content[:2] == b"PK":
            keep("liuwu", "monthly", content, url, "liuwu_monthly.xlsx")
            break
    else:
        raise FetchError("the Liu-Wu monthly workbook could not be downloaded")
    for ticker in etf.TICKERS:
        keep("etf", ticker, etf.download_csv(ticker), f"yfinance:{ticker}", f"{ticker}.csv")
    if latest_payload(macrokit_root, "us_term", "gsw") is None:
        raise FileNotFoundError(f"no GSW snapshot under {macrokit_root}; run `macrokit us-term`")
    lines.append(f"us_term/gsw: read from {macrokit_root}")
    return lines
```

- [ ] **Step 4: Run them to see them pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_liuwu.py bond_timing_lab/tests/test_etf.py bond_timing_lab/tests/test_snapshot.py -q`
Expected: `4 passed`.

- [ ] **Step 5: Parse the probe workbook (format check against the real file)**

```bash
cd $WT && $PY - <<'EOF'
from pathlib import Path
from bond_timing.data.liuwu import parse_liuwu
frame = parse_liuwu(Path("/tmp/claude-1000/-home-kazumasa-projects/df1bf6ad-598d-44e3-a3ed-6b1df2d7d491/scratchpad/probe/liuwu/liuwu_monthly.xlsx").read_bytes())
print(frame.shape, frame.index[0], frame.index[-1], frame.columns[:3].tolist(), frame.columns[-1])
print(frame.loc["1971-08", [12, 120]].to_dict())
EOF
```

Expected: `(775, 360) 1961-06 2025-12 [1, 2, 3] 360` and finite 1- and 10-year yields near 0.05–0.07 for 1971-08.

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Read Liu-Wu and ETF prices, and snapshot every raw source"
```

---

### Task 8: Features and in-window transforms

**Files:**
- Create: `bond_timing_lab/src/bond_timing/features.py`
- Test: `bond_timing_lab/tests/test_features.py`

**Interfaces:**
- Consumes: `fred.bey_to_cc` (Task 3).
- Produces: `YIELD_MONTHS = (12, 24, ..., 120)`, `N_YIELD_PCS = 3`, `N_MACRO_PCS = 8`, `OUTLIER_IQR = 10.0`, `MAX_NAN_SHARE = 0.20`; `forwards(Y) -> np.ndarray`; `Standardizer` (`fit`, `transform`, `mean_`, `std_`); `Pca(k)` (`fit`, `transform`, `mean_`, `components_` of shape k × features, sign fixed so the largest-magnitude loading is positive); `MacroCleaner` (`fit`, `transform`, `keep_`); `InputSpec(yields: str, macro: str)`; `INPUTS = {"P", "PM", "F", "FM"}`; `InputTransform(spec)` (`fit(Y, M)`, `transform(Y, M) -> np.ndarray`); `slope(zeros, bey) -> pd.Series`; `trailing_sum(excess, window=12) -> pd.Series`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_features.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from bond_timing.features import (
    INPUTS,
    YIELD_MONTHS,
    InputTransform,
    MacroCleaner,
    Pca,
    Standardizer,
    forwards,
    slope,
    trailing_sum,
)


def test_forwards_of_a_linear_curve():
    n = np.arange(1.0, 11.0)
    Y = np.vstack([0.02 + 0.001 * n, 0.03 + 0.002 * n])
    F = forwards(Y)
    np.testing.assert_allclose(F[:, 0], Y[:, 0])
    np.testing.assert_allclose(F[0, 1:], 0.02 + 0.001 * (2 * n[1:] - 1))


def test_standardizer_and_pca():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(200, 5)) @ np.diag([5.0, 3.0, 1.0, 0.5, 0.1])
    np.testing.assert_allclose(Standardizer().fit(X).transform(X).std(axis=0), 1.0)
    pca = Pca(2).fit(X)
    assert pca.transform(X).shape == (200, 2)
    top = pca.components_[np.arange(2), np.abs(pca.components_).argmax(axis=1)]
    assert (top > 0).all()
    assert Standardizer().fit(np.ones((5, 2))).transform(np.ones((1, 2))).tolist() == [[0.0, 0.0]]


def test_macro_cleaner_drops_sparse_series_and_removes_outliers():
    rng = np.random.default_rng(1)
    M = rng.normal(size=(100, 10))
    M[:30, 0] = np.nan  # 30 % missing: dropped
    M[5, 1] = np.nan
    M[7, 2] = 1e6  # outlier: missing, then 0
    cleaner = MacroCleaner().fit(M)
    assert not cleaner.keep_[0] and cleaner.keep_[1:].all()
    Z = cleaner.transform(M)
    assert Z.shape == (100, 9)
    assert Z[5, 0] == 0.0 and Z[7, 1] == 0.0
    assert np.abs(Z.mean(axis=0)).max() < 0.05


def test_macro_cleaner_turns_missing_edge_values_into_zero():
    cleaner = MacroCleaner().fit(np.random.default_rng(2).normal(size=(80, 9)))
    edge = np.full((1, 9), np.nan)
    edge[0, 3] = 1.0
    out = cleaner.transform(edge)
    assert out.shape == (1, 9) and np.isfinite(out).all()
    assert (out[0, np.arange(9) != 3] == 0.0).all()


def test_input_transforms_have_the_design_widths():
    rng = np.random.default_rng(3)
    Y = 0.05 + np.cumsum(rng.normal(0, 0.001, size=(120, 10)), axis=0)
    M = rng.normal(size=(120, 12))
    widths = {
        name: InputTransform(spec).fit(Y, M).transform(Y[:3], M[:3]).shape[1]
        for name, spec in INPUTS.items()
    }
    assert widths == {"P": 3, "PM": 11, "F": 10, "FM": 22}
    with pytest.raises(ValueError):
        InputTransform(INPUTS["FM"]).fit(Y, None)


def test_slope_and_trend_signals():
    index = pd.period_range("2000-01", periods=14, freq="M")
    zeros = pd.DataFrame({m: 0.05 for m in YIELD_MONTHS}, index=index)
    assert (slope(zeros, pd.Series(0.06, index=index)) < 0).all()
    excess = pd.Series(np.r_[np.full(12, 0.01), [-0.5, 0.01]], index=index)
    trend = trailing_sum(excess)
    assert np.isnan(trend.iloc[10]) and trend.iloc[11] == pytest.approx(0.12)
    assert trend.iloc[12] < 0
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_features.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.features'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/features.py` (create)

```python
"""Features F, P, CP inputs, M and X, and the transforms fitted inside the window (design §6.1, R4).

F   the one-year yield and one-year forwards f(n) = n y(n) - (n-1) y(n-1), n = 2..10, standardized
P   three principal components of the demeaned 1..10-year yields
M   FRED-MD transformed series: outliers (|x - median| > 10 IQR) to missing, standardized,
    series with more than 20 % missing dropped, remaining gaps set to 0; linear models use 8 PCs
X   only the L1 rules use it: the 10-year minus 3-month slope and the trailing 12-month excess return
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data.fred import bey_to_cc

YIELD_MONTHS = tuple(12 * n for n in range(1, 11))
N_YIELD_PCS = 3
N_MACRO_PCS = 8
OUTLIER_IQR = 10.0
MAX_NAN_SHARE = 0.20


def forwards(Y: np.ndarray) -> np.ndarray:
    n = np.arange(1.0, 11.0)
    out = np.array(Y, dtype=float, copy=True)
    out[:, 1:] = n[1:] * Y[:, 1:] - n[:-1] * Y[:, :-1]
    return out


class Standardizer:
    def fit(self, X: np.ndarray) -> Standardizer:
        self.mean_ = X.mean(axis=0)
        std = X.std(axis=0)
        self.std_ = np.where(std > 0, std, 1.0)
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean_) / self.std_


class Pca:
    def __init__(self, k: int):
        self.k = k

    def fit(self, X: np.ndarray) -> Pca:
        self.mean_ = X.mean(axis=0)
        _, _, vt = np.linalg.svd(X - self.mean_, full_matrices=False)
        components = vt[: self.k]
        signs = np.sign(components[np.arange(len(components)), np.abs(components).argmax(axis=1)])
        self.components_ = components * signs[:, None]
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        return (X - self.mean_) @ self.components_.T


class MacroCleaner:
    def fit(self, M: np.ndarray) -> MacroCleaner:
        with warnings.catch_warnings(), np.errstate(invalid="ignore"):
            warnings.simplefilter("ignore", RuntimeWarning)
            self.median_ = np.nanmedian(M, axis=0)
            q75, q25 = np.nanpercentile(M, [75, 25], axis=0)
            self.iqr_ = q75 - q25
            clean = self._outliers(M)
            share = np.isnan(clean).mean(axis=0)
            mean = np.nanmean(clean, axis=0)
            std = np.nanstd(clean, axis=0)
        self.keep_ = (share <= MAX_NAN_SHARE) & np.isfinite(std) & (std > 0)
        self.mean_, self.std_ = mean[self.keep_], std[self.keep_]
        return self

    def _outliers(self, M: np.ndarray) -> np.ndarray:
        with np.errstate(invalid="ignore"):
            far = (np.abs(M - self.median_) > OUTLIER_IQR * self.iqr_) & (self.iqr_ > 0)
        return np.where(far, np.nan, M)

    def transform(self, M: np.ndarray) -> np.ndarray:
        z = (self._outliers(M)[:, self.keep_] - self.mean_) / self.std_
        return np.nan_to_num(z, nan=0.0)


@dataclass(frozen=True)
class InputSpec:
    yields: str  # "P" (principal components) or "F" (standardized forwards)
    macro: str  # "" (none), "PC" (8 components of M) or "M" (all of M)


INPUTS = {
    "P": InputSpec("P", ""),
    "PM": InputSpec("P", "PC"),
    "F": InputSpec("F", ""),
    "FM": InputSpec("F", "M"),
}


class InputTransform:
    def __init__(self, spec: InputSpec):
        self.spec = spec

    def fit(self, Y: np.ndarray, M: np.ndarray | None) -> InputTransform:
        if self.spec.yields == "P":
            self.yields_ = Pca(N_YIELD_PCS).fit(Y)
        else:
            self.yields_ = Standardizer().fit(forwards(Y))
        if self.spec.macro:
            if M is None:
                raise ValueError(f"inputs {self.spec} need macro data")
            self.macro_ = MacroCleaner().fit(M)
            if self.spec.macro == "PC":
                self.macro_pca_ = Pca(N_MACRO_PCS).fit(self.macro_.transform(M))
        return self

    def transform(self, Y: np.ndarray, M: np.ndarray | None) -> np.ndarray:
        parts = [self.yields_.transform(Y if self.spec.yields == "P" else forwards(Y))]
        if self.spec.macro:
            cleaned = self.macro_.transform(M)
            parts.append(self.macro_pca_.transform(cleaned) if self.spec.macro == "PC" else cleaned)
        return np.hstack(parts)


def slope(zeros: pd.DataFrame, bey: pd.Series) -> pd.Series:
    """GSW 10-year zero minus the 3-month bill, both continuously compounded (decision months)."""
    return zeros[120] - bey_to_cc(bey)


def trailing_sum(excess: pd.Series, window: int = 12) -> pd.Series:
    """Sum of the last ``window`` monthly excess returns; month t is observed at decision t."""
    return excess.rolling(window).sum()
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_features.py -q`
Expected: `6 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Add the forward, PCA and macro-cleaning features fitted inside the window"
```

---

### Task 9: Model ladder and seed-averaged estimators

**Files:**
- Create: `bond_timing_lab/src/bond_timing/models.py`
- Test: `bond_timing_lab/tests/test_models.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (scikit-learn only).
- Produces: `Params = tuple[tuple[str, object], ...]`; `grid(**axes) -> tuple[Params, ...]`; `ModelSpec(name, inputs, kind, grid=((),), n_seeds=1)`; `EN_L1_RATIOS`, `EN_POINTS = 20`, `ET_GRID`, `HGB_GRID`, `NN_ALPHAS`, `NN_SEEDS = 20`; `ladder(nn_seeds=20) -> dict[str, ModelSpec]` with keys `ols_p, ols_pm, cp, en, et, hgb, nn_f, nn_fm`; `en_grid(X, z) -> tuple[Params, ...]`; `estimator(kind, params, seed)`; `fit_predict(kind, params, n_seeds, X, y, X_new) -> np.ndarray` (rows of `X_new` × targets, in target units).

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_models.py` (create)

```python
import numpy as np
import pytest
from bond_timing.models import EN_POINTS, en_grid, estimator, fit_predict, grid, ladder


def test_grid_is_a_sorted_cartesian_product():
    assert grid(b=(1, 2), a=(3,)) == ((("a", 3), ("b", 1)), (("a", 3), ("b", 2)))


def test_ladder_matches_the_design():
    specs = ladder()
    assert specs["nn_fm"].n_seeds == 20 and specs["nn_f"].n_seeds == 20
    assert len(specs["et"].grid) == 12 and len(specs["hgb"].grid) == 16
    assert len(specs["nn_fm"].grid) == 3 and len(specs["nn_f"].grid) == 3
    assert dict(specs["nn_fm"].grid[0])["hidden_layer_sizes"] == (32, 16)
    assert dict(specs["nn_f"].grid[0])["hidden_layer_sizes"] == (3,)
    assert {name: spec.inputs for name, spec in specs.items()} == {
        "ols_p": "P",
        "ols_pm": "PM",
        "cp": "F",
        "en": "FM",
        "et": "FM",
        "hgb": "FM",
        "nn_f": "F",
        "nn_fm": "FM",
    }
    assert ladder(5)["nn_fm"].n_seeds == 5


def test_en_grid_has_twenty_decreasing_alphas_per_l1_ratio():
    rng = np.random.default_rng(0)
    candidates = en_grid(rng.normal(size=(50, 4)), rng.normal(size=(50, 1)))
    assert len(candidates) == 3 * EN_POINTS
    alphas = [dict(c)["alpha"] for c in candidates[:EN_POINTS]]
    assert alphas == sorted(alphas, reverse=True)
    assert alphas[0] / alphas[-1] == pytest.approx(1000.0)


def test_ols_recovers_a_linear_rule():
    rng = np.random.default_rng(1)
    X, beta = rng.normal(size=(100, 3)), np.array([1.0, -2.0, 0.5])
    X_new = rng.normal(size=(5, 3))
    out = fit_predict("ols", (), 1, X, X @ beta + 1.0, X_new)
    np.testing.assert_allclose(out[:, 0], X_new @ beta + 1.0)


def test_models_predict_in_target_units_and_are_deterministic():
    rng = np.random.default_rng(2)
    X = rng.normal(size=(120, 4))
    y = 1000.0 + X[:, 0] + rng.normal(0, 0.1, 120)
    params = (("max_depth", 2), ("max_features", 1.0), ("min_samples_leaf", 5))
    first = fit_predict("et", params, 1, X, y, X[:10])
    assert abs(first.mean() - 1000.0) < 2.0
    np.testing.assert_array_equal(first, fit_predict("et", params, 1, X, y, X[:10]))


def test_seed_average_differs_from_one_seed_and_repeats():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(80, 3))
    y = X[:, 0] + rng.normal(0, 0.1, 80)
    params = (("alpha", 1e-3), ("hidden_layer_sizes", (3,)))
    one = fit_predict("mlp", params, 1, X, y, X[:5])
    two = fit_predict("mlp", params, 2, X, y, X[:5])
    assert not np.allclose(one, two)
    np.testing.assert_array_equal(two, fit_predict("mlp", params, 2, X, y, X[:5]))


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError):
        estimator("svm", (), 0)
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.models'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/models.py` (create)

```python
"""Model ladder L2-L3, hyperparameter grids and seed-averaged fitting (design §6.2-6.3).

Non-OLS models learn standardized targets and return forecasts in target units. The OLS
models (P2, P3 and the CP regression) fit raw targets.
"""

from __future__ import annotations

import itertools
import warnings
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet, LinearRegression
from sklearn.neural_network import MLPRegressor

Params = tuple[tuple[str, object], ...]


def grid(**axes: tuple) -> tuple[Params, ...]:
    names = sorted(axes)
    return tuple(
        tuple(zip(names, values, strict=True))
        for values in itertools.product(*(axes[name] for name in names))
    )


@dataclass(frozen=True)
class ModelSpec:
    name: str
    inputs: str  # key of features.INPUTS
    kind: str  # "ols", "en", "et", "hgb" or "mlp"
    grid: tuple[Params, ...] = ((),)
    n_seeds: int = 1


EN_L1_RATIOS = (0.1, 0.5, 0.9)
EN_POINTS = 20
ET_GRID = grid(max_depth=(2, 4, 6), min_samples_leaf=(5, 20), max_features=(0.3, 1.0))
HGB_GRID = grid(
    learning_rate=(0.03, 0.1), max_depth=(2, 3), max_iter=(100, 300), l2_regularization=(0.0, 1.0)
)
NN_ALPHAS = (1e-4, 1e-3, 1e-2)
NN_SEEDS = 20


def ladder(nn_seeds: int = NN_SEEDS) -> dict[str, ModelSpec]:
    return {
        "ols_p": ModelSpec("ols_p", "P", "ols"),
        "ols_pm": ModelSpec("ols_pm", "PM", "ols"),
        "cp": ModelSpec("cp", "F", "ols"),
        "en": ModelSpec("en", "FM", "en"),
        "et": ModelSpec("et", "FM", "et", ET_GRID),
        "hgb": ModelSpec("hgb", "FM", "hgb", HGB_GRID),
        "nn_f": ModelSpec(
            "nn_f", "F", "mlp", grid(hidden_layer_sizes=((3,),), alpha=NN_ALPHAS), nn_seeds
        ),
        "nn_fm": ModelSpec(
            "nn_fm", "FM", "mlp", grid(hidden_layer_sizes=((32, 16),), alpha=NN_ALPHAS), nn_seeds
        ),
    }


def en_grid(X: np.ndarray, z: np.ndarray) -> tuple[Params, ...]:
    """Twenty log-spaced alphas from alpha_max down to alpha_max / 1000 for each l1_ratio."""
    reach = float(np.abs(X.T @ np.asarray(z).reshape(len(X), -1)).max()) / len(X)
    out: list[Params] = []
    for l1_ratio in EN_L1_RATIOS:
        top = max(reach / l1_ratio, 1e-12)
        out.extend(
            (("alpha", float(alpha)), ("l1_ratio", l1_ratio))
            for alpha in top * np.logspace(0.0, -3.0, EN_POINTS)
        )
    return tuple(out)


def estimator(kind: str, params: Params, seed: int):
    kw = dict(params)
    if kind == "ols":
        return LinearRegression()
    if kind == "en":
        return ElasticNet(max_iter=20_000, **kw)
    if kind == "et":
        return ExtraTreesRegressor(n_estimators=500, n_jobs=1, random_state=seed, **kw)
    if kind == "hgb":
        return HistGradientBoostingRegressor(early_stopping=False, random_state=seed, **kw)
    if kind == "mlp":
        return MLPRegressor(solver="adam", max_iter=500, random_state=seed, **kw)
    raise ValueError(f"unknown model kind {kind!r}")


def fit_predict(
    kind: str, params: Params, n_seeds: int, X: np.ndarray, y: np.ndarray, X_new: np.ndarray
) -> np.ndarray:
    y = np.asarray(y, dtype=float).reshape(len(X), -1)
    if kind == "ols":
        return LinearRegression().fit(X, y).predict(X_new).reshape(len(X_new), -1)
    mean = y.mean(axis=0)
    std = y.std(axis=0)
    std = np.where(std > 0, std, 1.0)
    z = (y - mean) / std
    target = z[:, 0] if z.shape[1] == 1 else z
    total = np.zeros((len(X_new), y.shape[1]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        for seed in range(n_seeds):
            model = estimator(kind, params, seed).fit(X, target)
            total += model.predict(X_new).reshape(len(X_new), -1)
    return total / n_seeds * std + mean
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_models.py -q`
Expected: `7 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Define the model ladder, its grids and seed-averaged estimators"
```

---

### Task 10: Metrics, the stationary bootstrap, Holm and the verdict

**Files:**
- Create: `bond_timing_lab/src/bond_timing/evaluate.py`
- Test: `bond_timing_lab/tests/test_evaluate.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `GAMMA = 5.0`, `N_BOOT = 10_000`, `MEAN_BLOCK = 12`, `SEED = 20261019`, `ALPHA = 0.05`; `cer(r, gamma=GAMMA) -> float`; `sharpe(r) -> float`; `stationary_indices(n, n_boot, mean_block, rng, length=None) -> np.ndarray`; `DiffTest(delta_cer, delta_sharpe, p_cer, p_sharpe, months)`; `diff_test(a, b, *, n_boot, mean_block, seed, gamma) -> DiffTest`; `holm(pvalues: Mapping[str, float]) -> dict[str, float]`; `r2_oos(y, forecast, benchmark) -> float`; `prevailing_mean(targets, decisions, horizon, *, complete=True) -> pd.Series`; `Evidence(p_vs_hold, robust_vs_hold, oos_b_vs_hold, p_vs_p1=None, robust_vs_p1=None, oos_b_vs_p1=None, g3_p=None)`; `verdict(evidence: Mapping[str, Evidence], alpha=ALPHA) -> str`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_evaluate.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from bond_timing.evaluate import (
    Evidence,
    cer,
    diff_test,
    holm,
    prevailing_mean,
    r2_oos,
    sharpe,
    stationary_indices,
    verdict,
)


def test_cer_follows_the_design_formula():
    assert cer([0.01, 0.03]) == pytest.approx(12 * (0.02 - 2.5 * 0.0002))


def test_sharpe_of_a_flat_series_is_zero():
    assert sharpe(np.zeros(24)) == 0.0
    assert sharpe([0.01, 0.03]) == pytest.approx(np.sqrt(12) * 0.02 / np.std([0.01, 0.03], ddof=1))


def test_stationary_indices_are_reproducible_and_in_range():
    a = stationary_indices(50, 200, 12, np.random.default_rng(7))
    np.testing.assert_array_equal(a, stationary_indices(50, 200, 12, np.random.default_rng(7)))
    assert a.min() >= 0 and a.max() < 50 and a.shape == (200, 50)
    restarts = (np.diff(a, axis=1) != 1) & ~((a[:, :-1] == 49) & (a[:, 1:] == 0))
    assert 8 < 1 / restarts.mean() < 16  # mean block length near 12
    assert stationary_indices(10, 3, 12, np.random.default_rng(0), length=25).shape == (3, 25)


def test_identical_strategies_have_p_one():
    r = pd.Series(np.random.default_rng(0).normal(0.004, 0.02, 120))
    result = diff_test(r, r, n_boot=500)
    assert result.delta_cer == 0.0 and result.p_cer == 1.0 and result.p_sharpe == 1.0


def test_a_clearly_better_strategy_is_significant():
    base = pd.Series(np.random.default_rng(1).normal(0.0, 0.02, 228))
    result = diff_test(base + 0.01, base, n_boot=2000)
    assert result.delta_cer == pytest.approx(0.12)
    assert result.p_cer < 0.01 and result.months == 228


def test_holm_matches_a_worked_example():
    adjusted = holm({"a": 0.01, "b": 0.04, "c": 0.03, "d": 0.005})
    assert adjusted == pytest.approx({"d": 0.02, "a": 0.03, "c": 0.06, "b": 0.06})


def test_r2_oos_and_prevailing_mean():
    index = pd.period_range("2000-01", periods=40, freq="M")
    y = pd.Series(np.arange(40.0), index=index)
    decisions = index[20:30]
    bench = prevailing_mean(y, decisions, 12)
    assert bench.iloc[0] == pytest.approx(np.mean(np.arange(9.0)))  # s <= t - 12
    loose = prevailing_mean(y, decisions, 12, complete=False)
    assert loose.iloc[0] == pytest.approx(np.mean(np.arange(20.0)))  # s <= t - 1
    assert r2_oos(y.reindex(decisions), y.reindex(decisions), bench) == 1.0


def ml(**changes) -> Evidence:
    values = {
        "p_vs_hold": 0.01,
        "robust_vs_hold": True,
        "oos_b_vs_hold": 0.01,
        "p_vs_p1": 0.01,
        "robust_vs_p1": True,
        "oos_b_vs_p1": 0.01,
        "g3_p": 0.01,
    }
    values.update(changes)
    return Evidence(**values)


def evidence(**changes) -> dict[str, Evidence]:
    weak = Evidence(p_vs_hold=0.2, robust_vs_hold=True, oos_b_vs_hold=0.01)
    base = {"P1": weak, "P2": weak, "P3": weak, "P4": ml(), "P5": ml(p_vs_hold=0.2)}
    base.update(changes)
    return base


def test_verdict_branches():
    assert verdict(evidence()) == "ml_signal_usable"
    no_g3 = ml(g3_p=0.2)
    assert verdict(evidence(P4=no_g3)) == "no_usable_signal"
    assert verdict(evidence(P4=ml(oos_b_vs_p1=-0.001))) == "no_usable_signal"
    assert verdict(evidence(P4=ml(robust_vs_p1=False))) == "no_usable_signal"
    simple = Evidence(p_vs_hold=0.01, robust_vs_hold=True, oos_b_vs_hold=0.002)
    assert verdict(evidence(P4=no_g3, P2=simple)) == "simple_rule_usable"
    fragile = Evidence(p_vs_hold=0.01, robust_vs_hold=False, oos_b_vs_hold=0.002)
    assert verdict(evidence(P4=no_g3, P2=fragile)) == "no_usable_signal"
    late_loss = Evidence(p_vs_hold=0.01, robust_vs_hold=True, oos_b_vs_hold=-0.001)
    assert verdict(evidence(P4=no_g3, P2=late_loss)) == "no_usable_signal"
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_evaluate.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.evaluate'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/evaluate.py` (create)

```python
"""Certainty equivalent, Sharpe, R2oos, the stationary bootstrap, Holm and the verdict (design §3).

The test of "a beats b" uses the monthly returns of the same months, resampled with the same
stationary-bootstrap indices (Politis-Romano, mean block 12), centred:
p = (1 + #{D* - D >= D}) / (B + 1), where D is the observed CER (or Sharpe) difference.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

GAMMA = 5.0
N_BOOT = 10_000
MEAN_BLOCK = 12
SEED = 20261019
ALPHA = 0.05


def cer(r: Sequence[float] | np.ndarray | pd.Series, gamma: float = GAMMA) -> float:
    x = np.asarray(r, dtype=float)
    return float(12.0 * (x.mean() - gamma / 2.0 * x.var(ddof=1)))


def sharpe(r: Sequence[float] | np.ndarray | pd.Series) -> float:
    x = np.asarray(r, dtype=float)
    sd = x.std(ddof=1)
    return float(np.sqrt(12.0) * x.mean() / sd) if sd > 0 else 0.0


def stationary_indices(
    n: int, n_boot: int, mean_block: int, rng: np.random.Generator, length: int | None = None
) -> np.ndarray:
    length = n if length is None else length
    idx = np.empty((n_boot, length), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    restart = rng.random((n_boot, length)) < 1.0 / mean_block
    jumps = rng.integers(0, n, (n_boot, length))
    for t in range(1, length):
        idx[:, t] = np.where(restart[:, t], jumps[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _cer_rows(X: np.ndarray, gamma: float) -> np.ndarray:
    return 12.0 * (X.mean(axis=1) - gamma / 2.0 * X.var(axis=1, ddof=1))


def _sharpe_rows(X: np.ndarray) -> np.ndarray:
    sd = X.std(axis=1, ddof=1)
    ratio = np.divide(X.mean(axis=1), sd, out=np.zeros(len(X)), where=sd > 0)
    return np.sqrt(12.0) * ratio


@dataclass(frozen=True)
class DiffTest:
    delta_cer: float
    delta_sharpe: float
    p_cer: float
    p_sharpe: float
    months: int


def diff_test(
    a: pd.Series,
    b: pd.Series,
    *,
    n_boot: int = N_BOOT,
    mean_block: int = MEAN_BLOCK,
    seed: int = SEED,
    gamma: float = GAMMA,
) -> DiffTest:
    """One-sided test that strategy a has a higher CER (and Sharpe) than b."""
    joint = pd.concat([a, b], axis=1).dropna()
    x, y = joint.iloc[:, 0].to_numpy(), joint.iloc[:, 1].to_numpy()
    idx = stationary_indices(len(x), n_boot, mean_block, np.random.default_rng(seed))
    d_cer = cer(x, gamma) - cer(y, gamma)
    d_sharpe = sharpe(x) - sharpe(y)
    star_cer = _cer_rows(x[idx], gamma) - _cer_rows(y[idx], gamma)
    star_sharpe = _sharpe_rows(x[idx]) - _sharpe_rows(y[idx])
    p_cer = (1 + np.sum(star_cer - d_cer >= d_cer)) / (n_boot + 1)
    p_sharpe = (1 + np.sum(star_sharpe - d_sharpe >= d_sharpe)) / (n_boot + 1)
    return DiffTest(float(d_cer), float(d_sharpe), float(p_cer), float(p_sharpe), len(x))


def holm(pvalues: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(pvalues.items(), key=lambda item: item[1])
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (len(ordered) - rank) * p))
        adjusted[name] = running
    return adjusted


def r2_oos(y: pd.Series, forecast: pd.Series, benchmark: pd.Series) -> float:
    """Campbell-Thompson out-of-sample R2 against the prevailing mean."""
    joint = pd.concat([y, forecast, benchmark], axis=1).dropna()
    model = ((joint.iloc[:, 0] - joint.iloc[:, 1]) ** 2).sum()
    bench = ((joint.iloc[:, 0] - joint.iloc[:, 2]) ** 2).sum()
    return float(1.0 - model / bench)


def prevailing_mean(
    targets: pd.Series, decisions: pd.PeriodIndex, horizon: int, *, complete: bool = True
) -> pd.Series:
    """Mean of the targets a decision at t may use: s + h <= t, or s <= t - 1 when not complete."""
    valid = targets.dropna()
    running = valid.expanding().mean()
    span = pd.period_range(valid.index[0], max(valid.index[-1], decisions.max()), freq="M")
    running = running.reindex(span).ffill()
    limits = decisions - horizon if complete else decisions - 1
    return pd.Series(running.reindex(limits).to_numpy(), index=decisions)


@dataclass(frozen=True)
class Evidence:
    p_vs_hold: float  # H_A, Holm-adjusted over P1-P5
    robust_vs_hold: bool  # the OOS-A difference vs L0 stays positive at 4 bp and with the delay
    oos_b_vs_hold: float  # OOS-B CER difference vs L0
    p_vs_p1: float | None = None  # H_B, Holm-adjusted over P4-P5
    robust_vs_p1: bool | None = None
    oos_b_vs_p1: float | None = None
    g3_p: float | None = None  # Bauer-Hamilton style p-value (P4, P5)


def verdict(evidence: Mapping[str, Evidence], alpha: float = ALPHA) -> str:
    for name in ("P4", "P5"):
        e = evidence[name]
        if (
            e.p_vs_hold < alpha
            and e.p_vs_p1 is not None
            and e.p_vs_p1 < alpha
            and e.oos_b_vs_hold > 0
            and (e.oos_b_vs_p1 or 0.0) > 0
            and e.robust_vs_hold
            and bool(e.robust_vs_p1)
            and e.g3_p is not None
            and e.g3_p < alpha
        ):
            return "ml_signal_usable"
    for name in ("P1", "P2", "P3"):
        e = evidence[name]
        if e.p_vs_hold < alpha and e.oos_b_vs_hold > 0 and e.robust_vs_hold:
            return "simple_rule_usable"
    return "no_usable_signal"
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_evaluate.py -q`
Expected: `8 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Add CER, the stationary-bootstrap test, Holm and the pre-registered verdict"
```

---

### Task 11: Refit tasks, forecasts, weights, costs and the delay

**Files:**
- Create: `bond_timing_lab/src/bond_timing/backtest.py`
- Test: `bond_timing_lab/tests/test_backtest.py`

**Interfaces:**
- Consumes: `features.INPUTS`, `features.InputTransform`, `features.YIELD_MONTHS` (Task 8); `models.ModelSpec`, `Params`, `en_grid`, `fit_predict`, `ladder`, `grid` (Task 9); `pit.check_fit_window`, `check_observed`, `check_targets_complete`, `training_starts`, `validation_split`, `LookaheadError` (Task 5); macro sources with `view/history/edge` (Task 6).
- Produces: `TRAIN_START = Period("1971-08")`, `MIN_PAIRS = 60`; `Rules(complete_targets, embargo, in_window, real_time_macro)`, `REAL_TIME`, `V0`, `V1`, `V2`, `V3`; `RefitTask(refit, decisions, starts, Y, M, y, Y_pred, M_pred, horizon, rules, Y_full=None, M_full=None)`; `build_tasks(yields, targets, macro, *, refit_years, window, horizon, rules, train_start=TRAIN_START, full_end=None) -> list[RefitTask]`; `TaskResult`; `fit_task(task, spec, fixed=None) -> TaskResult`; `Forecasts(predictions: dict[str, pd.DataFrame], params: dict[str, dict[str, dict]])`; `as_params(params) -> Params | None`; `run_forecasts(tasks, specs, *, workers=1, fixed=None) -> Forecasts`; `signal_weights(signal, decisions) -> pd.Series`; `strategy_returns(weights, excess, cost_bp=2.0) -> pd.Series` (return months); `delayed_returns(weights, excess, legs, cost_bp=2.0)`; `fractional_weights(forecast, excess, decisions, *, gamma=5.0, window=60, min_months=36)`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_backtest.py` (create)

```python
import json

import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import (
    REAL_TIME,
    V0,
    RefitTask,
    build_tasks,
    delayed_returns,
    fit_task,
    fractional_weights,
    run_forecasts,
    signal_weights,
    strategy_returns,
)
from bond_timing.features import YIELD_MONTHS
from bond_timing.models import ModelSpec, grid, ladder
from bond_timing.pit import LookaheadError


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def panel(seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = pd.period_range("1971-08", "1990-12", freq="M")
    rng = np.random.default_rng(seed)
    level = 0.06 + np.cumsum(rng.normal(0, 0.001, len(index)))
    tilt = rng.normal(0, 0.005, len(index))
    yields = pd.DataFrame(
        {m: level + tilt * m / 120 + rng.normal(0, 1e-5, len(index)) for m in YIELD_MONTHS},
        index=index,
    )
    targets = pd.DataFrame({0: 3.0 * tilt + rng.normal(0, 0.0005, len(index))}, index=index)
    return yields, targets


def test_cost_is_charged_only_in_switch_months():
    decisions = pd.period_range("2000-01", periods=6, freq="M")
    weights = pd.Series([1, 1, 0, 0, 1, 1], index=decisions, dtype=float)
    excess = pd.Series(0.01, index=pd.period_range("2000-02", periods=6, freq="M"))
    r = strategy_returns(weights, excess, cost_bp=2.0)
    np.testing.assert_allclose(r.to_numpy(), [0.01, 0.01, -0.0002, 0.0, 0.0098, 0.01])
    assert r.index[0] == month("2000-02")


def test_always_hold_equals_the_instrument():
    decisions = pd.period_range("2000-01", periods=5, freq="M")
    excess = pd.Series(np.arange(1.0, 6.0) / 100, index=decisions + 1)
    r = strategy_returns(pd.Series(1.0, index=decisions), excess)
    pd.testing.assert_series_equal(r, excess, check_names=False)


def test_delayed_returns_use_the_legs_only_when_switching():
    decisions = pd.period_range("2000-01", periods=4, freq="M")
    weights = pd.Series([1, 1, 0, 1], index=decisions, dtype=float)
    months = decisions + 1
    excess = pd.Series(0.01, index=months)
    legs = pd.DataFrame({"in": 0.004, "out": 0.003}, index=months)
    r = delayed_returns(weights, excess, legs, cost_bp=2.0)
    np.testing.assert_allclose(r.to_numpy(), [0.01, 0.01, 0.003 - 0.0002, 0.004 - 0.0002])
    with pytest.raises(ValueError):
        delayed_returns(weights * 0.5, excess, legs)


def test_signal_weights_hold_cash_without_a_forecast():
    decisions = pd.period_range("2000-01", periods=3, freq="M")
    signal = pd.Series([0.2, np.nan], index=decisions[:2])
    assert signal_weights(signal, decisions).tolist() == [1.0, 0.0, 0.0]


def test_fractional_weights_are_clipped():
    index = pd.period_range("1995-01", periods=80, freq="M")
    excess = pd.Series(np.random.default_rng(0).normal(0, 0.02, 80), index=index)
    forecast = pd.Series(1.0, index=index)
    assert (fractional_weights(forecast, excess, index[-5:]) == 1.0).all()
    assert (fractional_weights(-forecast, excess, index[-5:]) == 0.0).all()


def test_build_tasks_skips_thin_years():
    yields, targets = panel()
    window = (month("1975-01"), month("1980-12"))
    tasks = build_tasks(
        yields, targets, None, refit_years=range(1975, 1981), window=window, horizon=12, rules=REAL_TIME
    )
    assert [str(t.refit) for t in tasks] == ["1978-01", "1979-01", "1980-01"]
    assert tasks[0].starts.max() == month("1977-01") and len(tasks[0].starts) == 66
    with pytest.raises(ValueError):
        build_tasks(yields, targets, None, refit_years=[1980], window=window, horizon=12, rules=V0)


def test_forecasts_recover_a_linear_signal():
    yields, targets = panel()
    tasks = build_tasks(
        yields,
        targets,
        None,
        refit_years=range(1980, 1991),
        window=(month("1980-01"), month("1990-12")),
        horizon=12,
        rules=REAL_TIME,
    )
    out = run_forecasts(tasks, [ladder()["ols_p"]])
    prediction = out.predictions["ols_p"][0]
    assert len(prediction) == 132
    assert np.corrcoef(prediction, targets[0].reindex(prediction.index))[0, 1] > 0.95
    assert set(out.params["ols_p"]) == {f"{year}-01" for year in range(1980, 1991)}


def test_fixed_params_survive_a_json_round_trip():
    yields, targets = panel()
    tasks = build_tasks(
        yields, targets, None, refit_years=[1985], window=(month("1985-01"), month("1985-12")), horizon=12,
        rules=REAL_TIME,
    )
    spec = ModelSpec("tiny", "P", "mlp", grid(hidden_layer_sizes=((3,),), alpha=(1e-4, 1e-2)), 1)
    first = run_forecasts(tasks, [spec])
    again = run_forecasts(tasks, [spec], fixed=json.loads(json.dumps(first.params)))
    assert again.params == first.params
    np.testing.assert_array_equal(
        again.predictions["tiny"].to_numpy(), first.predictions["tiny"].to_numpy()
    )


def test_fit_task_refuses_a_target_that_ends_after_the_refit():
    yields, targets = panel()
    starts = pd.period_range("1974-01", "1979-07", freq="M")
    decisions = pd.period_range("1980-01", periods=2, freq="M")
    task = RefitTask(
        refit=month("1980-01"),
        decisions=decisions,
        starts=starts,
        Y=yields.reindex(starts).to_numpy(),
        M=None,
        y=targets.reindex(starts).to_numpy(),
        Y_pred=yields.reindex(decisions).to_numpy(),
        M_pred=None,
        horizon=12,
        rules=REAL_TIME,
    )
    with pytest.raises(LookaheadError):
        fit_task(task, ladder()["ols_p"])
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_backtest.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.backtest'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/backtest.py` (create)

```python
"""Annual refits, monthly allocations, costs and the execution delay (design §3.1, §5, §6.3).

A refit at the end of January of year Y trains on every pair the rules allow at that date and
serves the decisions of January..December of Y. A decision with no forecast holds cash.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .features import INPUTS, InputTransform
from .models import ModelSpec, Params, en_grid, fit_predict
from .pit import (
    check_fit_window,
    check_observed,
    check_targets_complete,
    training_starts,
    validation_split,
)

TRAIN_START = pd.Period("1971-08", "M")
MIN_PAIRS = 60


@dataclass(frozen=True)
class Rules:
    complete_targets: bool = True  # R2
    embargo: bool = True  # R3
    in_window: bool = True  # R4
    real_time_macro: bool = True  # R1 for macro: vintage t-1 and publication lags


REAL_TIME = Rules()
V0 = Rules(False, False, False, False)
V1 = Rules(True, False, False, False)
V2 = Rules(True, True, True, False)
V3 = REAL_TIME


@dataclass(frozen=True)
class RefitTask:
    refit: pd.Period
    decisions: pd.PeriodIndex
    starts: pd.PeriodIndex
    Y: np.ndarray  # training rows x 10 yields
    M: np.ndarray | None  # training rows x macro series
    y: np.ndarray  # training rows x targets
    Y_pred: np.ndarray  # decisions x 10 yields
    M_pred: np.ndarray | None
    horizon: int
    rules: Rules
    Y_full: np.ndarray | None = None  # rows for full-sample transforms (R4 off)
    M_full: np.ndarray | None = None


def build_tasks(
    yields: pd.DataFrame,
    targets: pd.DataFrame,
    macro,
    *,
    refit_years: Iterable[int],
    window: tuple[pd.Period, pd.Period],
    horizon: int,
    rules: Rules,
    train_start: pd.Period = TRAIN_START,
    full_end: pd.Period | None = None,
) -> list[RefitTask]:
    if not rules.in_window and full_end is None:
        raise ValueError("full-sample transforms (R4 off) need full_end")
    usable = targets.dropna().index.intersection(yields.dropna().index)
    usable = usable[usable >= train_start].sort_values()
    full_rows = None
    if not rules.in_window:
        full_rows = yields.dropna().index
        full_rows = full_rows[(full_rows >= train_start) & (full_rows <= full_end)]
    tasks = []
    for year in refit_years:
        t = pd.Period(f"{year}-01", "M")
        decisions = pd.period_range(t, t + 11, freq="M")
        decisions = decisions[(decisions >= window[0]) & (decisions <= window[1])]
        decisions = decisions[yields.reindex(decisions).notna().all(axis=1).to_numpy()]
        if len(decisions) == 0:
            continue
        starts = training_starts(usable, t, horizon, complete=rules.complete_targets)
        if len(starts) < MIN_PAIRS:
            continue
        check_observed(starts, t)
        M = M_pred = M_full = None
        if macro is not None:
            view = macro.view(t)
            M = macro.history(t, view, starts)
            M_pred = np.vstack([macro.edge(d, view) for d in decisions])
            if full_rows is not None:
                M_full = macro.history(t, view, full_rows)
        tasks.append(
            RefitTask(
                refit=t,
                decisions=decisions,
                starts=starts,
                Y=yields.reindex(starts).to_numpy(dtype=float),
                M=M,
                y=targets.reindex(starts).to_numpy(dtype=float),
                Y_pred=yields.reindex(decisions).to_numpy(dtype=float),
                M_pred=M_pred,
                horizon=horizon,
                rules=rules,
                Y_full=None if full_rows is None else yields.reindex(full_rows).to_numpy(dtype=float),
                M_full=M_full,
            )
        )
    return tasks


@dataclass(frozen=True)
class TaskResult:
    model: str
    refit: pd.Period
    decisions: pd.PeriodIndex
    prediction: np.ndarray
    params: dict


def _rows(matrix: np.ndarray | None, rows: np.ndarray) -> np.ndarray | None:
    return None if matrix is None else matrix[rows]


def _fit_transform(spec: ModelSpec, task: RefitTask, rows: np.ndarray | None = None) -> InputTransform:
    transform = InputTransform(INPUTS[spec.inputs])
    if not task.rules.in_window:
        return transform.fit(task.Y_full, task.M_full)
    if rows is None:
        return transform.fit(task.Y, task.M)
    return transform.fit(task.Y[rows], _rows(task.M, rows))


def _select(task: RefitTask, spec: ModelSpec) -> Params:
    """Pick the candidate with the lowest validation MSE (each target scaled by its variance)."""
    if spec.kind != "en" and len(spec.grid) == 1:
        return spec.grid[0]
    split = validation_split(task.starts, task.horizon, embargo=task.rules.embargo)
    transform = _fit_transform(spec, task, split.core)
    X_core = transform.transform(task.Y[split.core], _rows(task.M, split.core))
    X_val = transform.transform(task.Y[split.validation], _rows(task.M, split.validation))
    y_core, y_val = task.y[split.core], task.y[split.validation]
    candidates = spec.grid
    if spec.kind == "en":
        sd = y_core.std(axis=0)
        candidates = en_grid(X_core, (y_core - y_core.mean(axis=0)) / np.where(sd > 0, sd, 1.0))
    scale = y_core.var(axis=0)
    scale = np.where(scale > 0, scale, 1.0)
    best, best_loss = candidates[0], np.inf
    for params in candidates:
        prediction = fit_predict(spec.kind, params, spec.n_seeds, X_core, y_core, X_val)
        loss = float(np.mean((prediction - y_val) ** 2 / scale))
        if loss < best_loss:
            best, best_loss = params, loss
    return best


def fit_task(task: RefitTask, spec: ModelSpec, fixed: Params | None = None) -> TaskResult:
    if task.rules.complete_targets:
        check_targets_complete(task.starts, task.refit, task.horizon)
    if task.rules.in_window:
        end = task.refit - task.horizon if task.rules.complete_targets else task.refit - 1
        check_fit_window(task.starts, end)
    params = fixed if fixed is not None else _select(task, spec)
    transform = _fit_transform(spec, task)
    X = transform.transform(task.Y, task.M)
    X_new = transform.transform(task.Y_pred, task.M_pred)
    prediction = fit_predict(spec.kind, params, spec.n_seeds, X, task.y, X_new)
    return TaskResult(spec.name, task.refit, task.decisions, prediction, dict(params))


@dataclass(frozen=True)
class Forecasts:
    predictions: dict[str, pd.DataFrame]  # model -> decision month x target column
    params: dict[str, dict[str, dict]]  # model -> refit month -> chosen hyperparameters


def as_params(params: Mapping | None) -> Params | None:
    """Hyperparameters back from JSON: sorted items, with lists turned back into tuples."""
    if params is None:
        return None
    return tuple(
        sorted((key, tuple(value) if isinstance(value, list) else value) for key, value in params.items())
    )


def _single_thread() -> None:
    threadpool_limits(1)


def _run_job(job: tuple[RefitTask, ModelSpec, Params | None]) -> TaskResult:
    task, spec, fixed = job
    return fit_task(task, spec, fixed)


def run_forecasts(
    tasks: Sequence[RefitTask],
    specs: Sequence[ModelSpec],
    *,
    workers: int = 1,
    fixed: Mapping[str, Mapping[str, Mapping]] | None = None,
) -> Forecasts:
    fixed = fixed or {}
    jobs = [
        (task, spec, as_params(fixed.get(spec.name, {}).get(str(task.refit))))
        for spec in specs
        for task in tasks
    ]
    if workers > 1 and len(jobs) > 1:
        with ProcessPoolExecutor(max_workers=min(workers, len(jobs)), initializer=_single_thread) as pool:
            results = list(pool.map(_run_job, jobs, chunksize=1))
    else:
        with threadpool_limits(1):
            results = [_run_job(job) for job in jobs]
    frames: dict[str, list[pd.DataFrame]] = {}
    params: dict[str, dict[str, dict]] = {}
    for result in results:
        frames.setdefault(result.model, []).append(
            pd.DataFrame(result.prediction, index=result.decisions)
        )
        params.setdefault(result.model, {})[str(result.refit)] = result.params
    return Forecasts({model: pd.concat(f).sort_index() for model, f in frames.items()}, params)


def signal_weights(signal: pd.Series, decisions: pd.PeriodIndex) -> pd.Series:
    """1 (hold) where the signal is positive; 0 (cash) where it is not or does not exist."""
    return (signal.reindex(decisions) > 0).astype(float)


def strategy_returns(weights: pd.Series, excess: pd.Series, cost_bp: float = 2.0) -> pd.Series:
    """r[t+1] = w_t * excess[t+1] - cost * |w_t - w_{t-1}|; the first month pays no cost."""
    w = weights.astype(float).to_numpy()
    turnover = np.abs(np.diff(w, prepend=w[:1]))
    months = weights.index + 1
    r = w * excess.reindex(months).to_numpy(dtype=float) - cost_bp * 1e-4 * turnover
    return pd.Series(r, index=months)


def delayed_returns(
    weights: pd.Series, excess: pd.Series, legs: pd.DataFrame, cost_bp: float = 2.0
) -> pd.Series:
    """As strategy_returns, but a switch executes on the 5th trading day (R5): the switch month
    earns the ``in`` or ``out`` leg instead of the month-end-to-month-end return."""
    w = weights.astype(float).to_numpy()
    if not np.isin(w, (0.0, 1.0)).all():
        raise ValueError("the delayed execution is defined for hold-or-cash weights only")
    prev = np.concatenate([w[:1], w[:-1]])
    months = weights.index + 1
    ex = excess.reindex(months).to_numpy(dtype=float)
    leg_in = legs["in"].reindex(months).to_numpy(dtype=float)
    leg_out = legs["out"].reindex(months).to_numpy(dtype=float)
    held = np.where(w == prev, w * ex, np.where(w > prev, leg_in, leg_out))
    return pd.Series(held - cost_bp * 1e-4 * np.abs(w - prev), index=months)


def fractional_weights(
    forecast: pd.Series,
    excess: pd.Series,
    decisions: pd.PeriodIndex,
    *,
    gamma: float = 5.0,
    window: int = 60,
    min_months: int = 36,
) -> pd.Series:
    """Secondary 0-100 % weights: clip((12-month forecast / 12) / (gamma * monthly variance), 0, 1)."""
    variance = excess.rolling(window, min_periods=min_months).var()
    weight = (forecast.reindex(decisions) / 12.0) / (gamma * variance.reindex(decisions))
    return weight.clip(0.0, 1.0).fillna(0.0)
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_backtest.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Run annual refits in parallel and turn forecasts into costed hold-or-cash returns"
```

---

### Task 12: Synthetic worlds for G1 and G3

**Files:**
- Create: `bond_timing_lab/src/bond_timing/synthetic.py`
- Test: `bond_timing_lab/tests/test_synthetic.py`

**Interfaces:**
- Consumes: `returns.Outcomes`, `returns.world_outcomes`, `returns.DURATION` (Task 4); `evaluate.MEAN_BLOCK`, `evaluate.cer`, `evaluate.stationary_indices` (Task 10); `backtest.strategy_returns` (Task 11); `features.Pca` (Task 8).
- Produces: `resample_rows(frame, index, seed, mean_block=12) -> pd.DataFrame`; `w0_world(real: Outcomes, index, seed) -> Outcomes`; `plant(world, z, k) -> Outcomes`; `calibrate_k(excess, z, decisions, *, duration=17.0, gain=0.04, cost_bp=2.0) -> float`; `SpanningNull` (with `.max_eigenvalue`); `fit_spanning_null(zeros, macro, *, n_factors=3, n_macro=8) -> SpanningNull`; `simulate(null, seed) -> tuple[pd.DataFrame, pd.DataFrame]` (zeros on the same maturities, macro on the same series).

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_synthetic.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import strategy_returns
from bond_timing.evaluate import cer
from bond_timing.returns import Outcomes, world_outcomes
from bond_timing.synthetic import (
    calibrate_k,
    fit_spanning_null,
    plant,
    resample_rows,
    simulate,
    w0_world,
)


def outcomes(seed: int = 0, periods: int = 120) -> Outcomes:
    index = pd.period_range("2000-01", periods=periods, freq="M")
    rng = np.random.default_rng(seed)
    log_excess = pd.DataFrame(
        {n: rng.normal(0.001 * n, 0.003 * n, periods) for n in range(2, 11)}, index=index
    )
    excess = pd.DataFrame(
        {
            "tlt": rng.normal(0.003, 0.03, periods),
            "ief": rng.normal(0.002, 0.015, periods),
            "z10": rng.normal(0.0025, 0.02, periods),
        },
        index=index,
    )
    return world_outcomes(log_excess, excess)


def test_resample_rows_draws_whole_rows():
    index = pd.period_range("2000-01", periods=10, freq="M")
    frame = pd.DataFrame({"a": np.arange(10.0), "b": np.arange(10.0) * 10}, index=index)
    target = pd.period_range("2001-01", periods=25, freq="M")
    out = resample_rows(frame, target, seed=3)
    assert out.index.equals(target)
    np.testing.assert_allclose(out["b"], out["a"] * 10)
    assert set(out["a"]) <= set(frame["a"])


def test_w0_world_rebuilds_rx12_from_the_drawn_months():
    real = outcomes()
    index = pd.period_range("2010-01", periods=60, freq="M")
    world = w0_world(real, index, seed=5)
    s = index[10]
    assert world.rx12[10][s] == pytest.approx(world.monthly_log_excess[10].loc[s + 1 : s + 12].sum())
    assert world.excess.index.equals(index)
    again = w0_world(real, index, seed=5)
    np.testing.assert_array_equal(again.excess.to_numpy(), world.excess.to_numpy())


def test_plant_adds_the_lagged_component_scaled_by_duration():
    world = outcomes()
    planted = plant(world, pd.Series(1.0, index=world.excess.index), k=0.002)
    p, first = world.excess.index[5], world.excess.index[0]
    assert planted.excess.loc[p, "tlt"] - world.excess.loc[p, "tlt"] == pytest.approx(0.002 * 1.7)
    assert planted.monthly_log_excess.loc[p, 5] - world.monthly_log_excess.loc[p, 5] == pytest.approx(
        0.001
    )
    assert planted.excess.loc[first, "tlt"] == world.excess.loc[first, "tlt"]


def test_calibrate_k_finds_the_smallest_size_with_the_target_gain():
    index = pd.period_range("2000-01", periods=229, freq="M")
    rng = np.random.default_rng(4)
    excess = pd.Series(rng.normal(0.003, 0.03, 229), index=index)
    z = pd.Series(rng.normal(size=229), index=index)
    decisions = index[:-1]
    k = calibrate_k(excess, z, decisions)

    def gain(size: float) -> float:
        shifted = excess + size * 1.7 * z.shift(1).reindex(index).fillna(0.0)
        oracle = strategy_returns((z.reindex(decisions) > 0).astype(float), shifted).dropna()
        hold = strategy_returns(pd.Series(1.0, index=decisions), shifted).dropna()
        return cer(oracle) - cer(hold)

    assert k > 0 and gain(k) >= 0.04 and gain(0.98 * k) < 0.04


def test_spanning_null_worlds_have_the_right_shape_and_are_reproducible():
    index = pd.period_range("1980-01", periods=240, freq="M")
    rng = np.random.default_rng(6)
    factors = np.zeros((240, 3))
    for t in range(1, 240):
        factors[t] = 0.95 * factors[t - 1] + rng.normal(0, 0.002, 3)
    loadings = rng.normal(size=(19, 3))
    zeros = pd.DataFrame(
        0.05 + factors @ loadings.T + rng.normal(0, 1e-4, (240, 19)), index=index, columns=range(19)
    )
    macro = pd.DataFrame(rng.normal(size=(240, 12)), index=index, columns=[f"m{j}" for j in range(12)])
    null = fit_spanning_null(zeros, macro)
    y1, m1 = simulate(null, seed=1)
    y2, _ = simulate(null, seed=1)
    assert y1.shape == (240, 19) and m1.shape == (240, 12)
    pd.testing.assert_frame_equal(y1, y2)
    assert not y1.equals(simulate(null, seed=2)[0])
    np.testing.assert_allclose(y1.iloc[0], zeros.iloc[0])
    assert abs(y1.to_numpy().mean() - zeros.to_numpy().mean()) < 0.02
    assert 0.0 < null.max_eigenvalue < 1.0
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_synthetic.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.synthetic'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/synthetic.py` (create)

```python
"""Synthetic worlds for G1 (W0 and W2) and G3 (the spanning null) (design §8).

W0  the monthly excess returns of every maturity and instrument, redrawn jointly by a stationary
    bootstrap (mean block 12): no feature can predict them; rx12 is rebuilt from the drawn months.
W2  W0 plus k * (duration / 10) * z_{p-1} in every return of month p.
G3  yields from a VAR(1) on three yield factors plus measurement errors, macro from an
    independent VAR(1) on eight macro factors plus idiosyncratic parts; the residuals of one
    month are drawn together (iid), as in Bauer and Hamilton (2018).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import strategy_returns
from .evaluate import MEAN_BLOCK, cer, stationary_indices
from .features import Pca
from .returns import DURATION, Outcomes, world_outcomes


def resample_rows(
    frame: pd.DataFrame, index: pd.PeriodIndex, seed: int, mean_block: int = MEAN_BLOCK
) -> pd.DataFrame:
    source = frame.dropna()
    rng = np.random.default_rng(seed)
    order = stationary_indices(len(source), 1, mean_block, rng, length=len(index))[0]
    return pd.DataFrame(source.to_numpy()[order], index=index, columns=frame.columns)


def w0_world(real: Outcomes, index: pd.PeriodIndex, seed: int) -> Outcomes:
    joint = pd.concat({"log": real.monthly_log_excess, "simple": real.excess}, axis=1)
    drawn = resample_rows(joint, index, seed)
    return world_outcomes(drawn["log"], drawn["simple"])


def _next_month(z: pd.Series) -> pd.Series:
    """z by decision month, moved to the return month it affects (the last decision included)."""
    return pd.Series(z.to_numpy(), index=z.index + 1)


def plant(world: Outcomes, z: pd.Series, k: float) -> Outcomes:
    log_excess, excess = world.monthly_log_excess.copy(), world.excess.copy()
    lagged = _next_month(z)
    component = lagged.reindex(log_excess.index).fillna(0.0).to_numpy()
    for n in log_excess.columns:
        log_excess[n] = log_excess[n] + k * (n / 10.0) * component
    component = lagged.reindex(excess.index).fillna(0.0).to_numpy()
    for name in excess.columns:
        excess[name] = excess[name] + k * (DURATION[name] / 10.0) * component
    return world_outcomes(log_excess, excess)


def calibrate_k(
    excess: pd.Series,
    z: pd.Series,
    decisions: pd.PeriodIndex,
    *,
    duration: float = DURATION["tlt"],
    gain: float = 0.04,
    cost_bp: float = 2.0,
) -> float:
    """Smallest k whose hold-when-z>0 oracle beats always-hold by ``gain`` CER per year."""
    component = _next_month(z).reindex(excess.index).fillna(0.0)
    oracle = (z.reindex(decisions) > 0).astype(float)
    hold = pd.Series(1.0, index=decisions)

    def advantage(k: float) -> float:
        shifted = excess + k * (duration / 10.0) * component
        a = strategy_returns(oracle, shifted, cost_bp).dropna()
        b = strategy_returns(hold, shifted, cost_bp).dropna()
        return cer(a) - cer(b)

    high = 1e-4
    while advantage(high) < gain:
        high *= 2.0
        if high > 1.0:
            raise ValueError("no planted size reaches the target gain")
    low = 0.0
    for _ in range(60):
        middle = (low + high) / 2.0
        if advantage(middle) >= gain:
            high = middle
        else:
            low = middle
    return high


@dataclass(frozen=True)
class SpanningNull:
    months: pd.PeriodIndex
    maturities: tuple
    yield_mean: np.ndarray
    yield_loadings: np.ndarray  # maturities x factors
    factor_c: np.ndarray
    factor_a: np.ndarray
    macro_names: tuple[str, ...]
    macro_mean: np.ndarray
    macro_loadings: np.ndarray  # series x macro factors
    macro_c: np.ndarray
    macro_a: np.ndarray
    residuals: np.ndarray  # (months - 1) x (factors + maturities + macro factors + series)
    first_yields: np.ndarray
    first_macro: np.ndarray
    first_factors: np.ndarray
    first_macro_factors: np.ndarray

    @property
    def max_eigenvalue(self) -> float:
        return float(np.abs(np.linalg.eigvals(self.factor_a)).max())


def _var1(F: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.hstack([np.ones((len(F) - 1, 1)), F[:-1]])
    coef, *_ = np.linalg.lstsq(X, F[1:], rcond=None)
    return coef[0], coef[1:].T, F[1:] - X @ coef


def fit_spanning_null(
    zeros: pd.DataFrame, macro: pd.DataFrame, *, n_factors: int = 3, n_macro: int = 8
) -> SpanningNull:
    months = zeros.dropna().index.intersection(macro.dropna().index)
    if len(months) != len(pd.period_range(months[0], months[-1], freq="M")):
        raise ValueError("the spanning-null fit needs contiguous months")
    Y = zeros.reindex(months).to_numpy(dtype=float)
    M = macro.reindex(months).to_numpy(dtype=float)
    yield_pca = Pca(n_factors).fit(Y)
    F = yield_pca.transform(Y)
    errors = Y - (yield_pca.mean_ + F @ yield_pca.components_)
    macro_pca = Pca(n_macro).fit(M)
    G = macro_pca.transform(M)
    idiosyncratic = M - (macro_pca.mean_ + G @ macro_pca.components_)
    c, a, shocks = _var1(F)
    cg, ag, macro_shocks = _var1(G)
    return SpanningNull(
        months=months,
        maturities=tuple(zeros.columns),
        yield_mean=yield_pca.mean_,
        yield_loadings=yield_pca.components_.T,
        factor_c=c,
        factor_a=a,
        macro_names=tuple(macro.columns),
        macro_mean=macro_pca.mean_,
        macro_loadings=macro_pca.components_.T,
        macro_c=cg,
        macro_a=ag,
        residuals=np.hstack([shocks, errors[1:], macro_shocks, idiosyncratic[1:]]),
        first_yields=Y[0],
        first_macro=M[0],
        first_factors=F[0],
        first_macro_factors=G[0],
    )


def simulate(null: SpanningNull, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    T, k, km, ny = len(null.months), len(null.factor_c), len(null.macro_c), len(null.maturities)
    draws = null.residuals[rng.integers(0, len(null.residuals), T - 1)]
    shocks, errors, macro_shocks, idiosyncratic = np.split(draws, [k, k + ny, k + ny + km], axis=1)
    F, G = np.empty((T, k)), np.empty((T, km))
    F[0], G[0] = null.first_factors, null.first_macro_factors
    for t in range(1, T):
        F[t] = null.factor_c + null.factor_a @ F[t - 1] + shocks[t - 1]
        G[t] = null.macro_c + null.macro_a @ G[t - 1] + macro_shocks[t - 1]
    Y = null.yield_mean + F @ null.yield_loadings.T
    Y[1:] += errors
    Y[0] = null.first_yields
    M = null.macro_mean + G @ null.macro_loadings.T
    M[1:] += idiosyncratic
    M[0] = null.first_macro
    return (
        pd.DataFrame(Y, index=null.months, columns=list(null.maturities)),
        pd.DataFrame(M, index=null.months, columns=list(null.macro_names)),
    )
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_synthetic.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Generate the W0, W2 and spanning-null worlds for G1 and G3"
```

---

### Task 13: Study assembly, G0, the dev-period P1 and the CLI; snapshot the real data

**Files:**
- Create: `bond_timing_lab/src/bond_timing/study.py`, `bond_timing_lab/src/bond_timing/stages.py`, `bond_timing_lab/src/bond_timing/cli.py`
- Test: `bond_timing_lab/tests/test_study.py`, `bond_timing_lab/tests/test_stages.py`, `bond_timing_lab/tests/test_cli.py`
- Produce (committed): `bond_timing_lab/results/g0.json`, `bond_timing_lab/results/dev.json`

**Interfaces:**
- Consumes: everything from Tasks 1–12.
- Produces: `study.TRAIN_START`, `DEV = (1971-08, 1999-12)`, `OOS_A = (2000-01, 2018-12)`, `OOS_B_START = 2019-01`, `FINAL_VINTAGE = 2019-02`; `Study` (`curve`, `zeros`, `bey`, `cash`, `outcomes`, `vintage_payloads`, `raw_root`, `.yields`, `.vintage(month)`, `.realtime_macro()`, `.final_macro()`, `.last_decision()`); `load_vintage_payloads(root)`; `load_study(raw_root=RAW_ROOT, macrokit_root=MACROKIT_RAW)`; `macro_pc1(vintage, start, end, *, lag=2, anchor="INDPRO") -> pd.Series`. `stages.PRIMARY = {"P2": "ols_p", "P3": "ols_pm", "P4": "nn_fm", "P5": "et"}`, `RULES`, `COST_BP = 2.0`, `COST_HIGH_BP = 4.0`; `window(first, last)`, `as_frame(series)`, `summary(returns, weights) -> dict`, `forecast(study, targets, models, *, decisions, horizon, macro, rules=REAL_TIME, nn_seeds=20, workers=1, fixed=None, yields=None, full_end=None) -> Forecasts`, `first_column(forecasts, model)`, `rule_signals(study, outcomes, instrument, cp)`, `strategy_weights(study, outcomes, decisions, forecasts, cp, instrument) -> dict[str, pd.Series]`, `primary_names(p1)`, `primary_tests(returns, p1, *, seed=SEED) -> dict`; stage runners all take `(study, workers, prior: Mapping[str, dict]) -> dict`: `run_g0`, `run_dev`. `cli.main` (click group: `snapshot`, `run STAGE [--workers N] [--rerun-reason TEXT]`, `report`), `cli.StageError`, `cli.check_ready(stage, results, prereg_commit) -> dict[str, dict]`, `cli.oos_b_target(results, rerun_reason) -> tuple[str, dict]`, `cli.take_lock(results, commit)`, `cli.write_result(name, result, results, meta) -> Path`, `cli.read_result(name, results) -> dict`.

- [ ] **Step 1: Write the failing tests**

File: `bond_timing_lab/tests/test_study.py` (create)

```python
import io
import zipfile

import numpy as np
import pandas as pd
import pytest
from bond_timing.data.fredmd import Vintage
from bond_timing.data.store import store_bytes
from bond_timing.study import load_vintage_payloads, macro_pc1


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def archive(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as handle:
        for name, content in members.items():
            handle.writestr(name, content)
    return buffer.getvalue()


def test_vintage_payloads_merge_both_archives_and_monthly_files(tmp_path):
    store_bytes(tmp_path, "fredmd", "hist_1999_2014", archive({"Final/1999-08.csv": b"a"}), url="u", filename="a.zip")
    store_bytes(tmp_path, "fredmd", "hist_2015_2025", archive({"FRED-MD_2024m03.csv": b"b"}), url="u", filename="b.zip")
    store_bytes(tmp_path, "fredmd", "monthly_2026-01", b"c", url="u", filename="c.csv")
    payloads = load_vintage_payloads(tmp_path)
    assert list(payloads) == [month("1999-08"), month("2024-03"), month("2026-01")]
    assert payloads[month("2026-01")] == b"c"


def test_macro_pc1_is_lagged_signed_and_scaled():
    index = pd.period_range("1990-01", periods=60, freq="M")
    rng = np.random.default_rng(0)
    common = rng.normal(size=60)
    levels = pd.DataFrame(
        {
            "INDPRO": common + rng.normal(0, 0.1, 60),
            **{f"S{j}": -common + rng.normal(0, 0.3, 60) for j in range(9)},
        },
        index=index,
    )
    vintage = Vintage(month("1995-01"), levels, {name: 1 for name in levels.columns})
    z = macro_pc1(vintage, index[2], index[-1])
    assert z.index[0] == index[2] and z.index[-1] == index[-1]
    lead = z.shift(-2).dropna()
    assert np.corrcoef(lead, levels["INDPRO"].reindex(lead.index))[0, 1] > 0.9
    assert z.std() == pytest.approx(1.0, abs=0.1)
```

File: `bond_timing_lab/tests/test_stages.py` (create)

```python
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from bond_timing.backtest import Forecasts, strategy_returns
from bond_timing.stages import primary_tests, strategy_weights, summary


def test_primary_tests_apply_holm_over_five_and_two():
    rng = np.random.default_rng(0)
    months = pd.period_range("2000-02", periods=228, freq="M")
    hold = pd.Series(rng.normal(0.003, 0.02, 228), index=months)
    returns = {
        "hold": hold,
        "slope": hold * 0.5,
        "ols_p": hold + 0.004,
        "ols_pm": hold,
        "nn_fm": hold + 0.004,
        "et": hold - 0.001,
    }
    tests = primary_tests(returns, "slope")
    assert set(tests["vs_hold"]) == {"P1", "P2", "P3", "P4", "P5"}
    assert set(tests["vs_p1"]) == {"P4", "P5"}
    assert tests["vs_hold"]["P2"]["p_holm"] < 0.05
    assert tests["vs_hold"]["P3"]["p_holm"] == 1.0
    assert all(t["p_holm"] >= t["p_cer"] for t in tests["vs_hold"].values())


def test_summary_counts_switches_and_hold_share():
    decisions = pd.period_range("2000-01", periods=6, freq="M")
    weights = pd.Series([1, 1, 0, 0, 1, 1], index=decisions, dtype=float)
    out = summary(strategy_returns(weights, pd.Series(0.01, index=decisions + 1)), weights)
    assert out["switches"] == 2 and out["months"] == 6
    assert out["hold_share"] == pytest.approx(4 / 6)


def test_strategy_weights_cover_rules_models_and_benchmarks():
    index = pd.period_range("1999-01", "2001-12", freq="M")
    study = SimpleNamespace(
        zeros=pd.DataFrame({120: 0.05}, index=index), bey=pd.Series(0.04, index=index)
    )
    outcomes = SimpleNamespace(excess=pd.DataFrame({"tlt": 0.01}, index=index))
    decisions = pd.period_range("2000-01", "2000-12", freq="M")
    forecasts = Forecasts({"et": pd.DataFrame({0: -0.01}, index=decisions)}, {})
    w = strategy_weights(study, outcomes, decisions, forecasts, None, "tlt")
    assert set(w) == {"hold", "cash", "slope", "trend", "cp", "et"}
    assert w["slope"].eq(1.0).all() and w["trend"].eq(1.0).all()
    assert w["cp"].eq(0.0).all() and w["et"].eq(0.0).all() and w["cash"].eq(0.0).all()
```

File: `bond_timing_lab/tests/test_cli.py` (create)

```python
import json

import numpy as np
import pandas as pd
import pytest
from bond_timing import cli


def write(results, name: str, payload: dict) -> None:
    (results / f"{name}.json").write_text(json.dumps(payload))


def test_stage_order_is_enforced(tmp_path):
    with pytest.raises(cli.StageError, match=r"dev\.json"):
        cli.check_ready("g1", tmp_path, prereg_commit="abc")
    write(tmp_path, "dev", {"p1": "slope"})
    with pytest.raises(cli.StageError, match="PREREG"):
        cli.check_ready("g1", tmp_path, prereg_commit="")
    assert cli.check_ready("g1", tmp_path, prereg_commit="abc")["dev"]["p1"] == "slope"
    assert cli.check_ready("g0", tmp_path, prereg_commit="") == {}


def test_oos_a_requires_prereg_and_a_passed_g1(tmp_path):
    write(tmp_path, "dev", {"p1": "slope"})
    write(tmp_path, "g1", {"pass": False})
    with pytest.raises(cli.StageError, match="G1 did not pass"):
        cli.check_ready("oos-a", tmp_path, prereg_commit="abc")
    write(tmp_path, "g1", {"pass": True})
    assert set(cli.check_ready("oos-a", tmp_path, prereg_commit="abc")) == {"dev", "g1"}


def test_oos_b_runs_once_without_a_reason(tmp_path):
    assert cli.oos_b_target(tmp_path, None) == ("oos_b", {})
    cli.take_lock(tmp_path, "abc123")
    with pytest.raises(cli.StageError, match="already ran"):
        cli.oos_b_target(tmp_path, None)
    write(tmp_path, "oos_b", {"verdict": "no_usable_signal"})
    name, extra = cli.oos_b_target(tmp_path, "fixed a data error")
    assert name == "oos_b_rerun_1"
    assert extra == {"rerun_reason": "fixed a data error", "verdict_of_record": "no_usable_signal"}


def test_results_serialise_numpy_values_and_periods(tmp_path):
    result = {"a": np.float64(1.5), "b": pd.Period("2000-01", "M"), "c": (1, 2), "d": np.bool_(True)}
    path = cli.write_result("x", result, tmp_path, {"git_commit": "abc"})
    assert json.loads(path.read_text()) == {
        "meta": {"git_commit": "abc"},
        "a": 1.5,
        "b": "2000-01",
        "c": [1, 2],
        "d": True,
    }
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_study.py bond_timing_lab/tests/test_stages.py bond_timing_lab/tests/test_cli.py -q`
Expected: FAIL with `ModuleNotFoundError` for `bond_timing.study`, `bond_timing.stages` and `bond_timing.cli`.

- [ ] **Step 3: Write `study.py`**

File: `bond_timing_lab/src/bond_timing/study.py` (create)

```python
"""Every input of the study in one object (design §4), and W2's planted macro factor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import TRAIN_START
from .data import fred, fredmd, gsw
from .data.store import MACROKIT_RAW, RAW_ROOT, indicators, read_latest
from .features import YIELD_MONTHS, MacroCleaner, Pca
from .returns import Outcomes, grid_months, real_outcomes

__all__ = ["DEV", "FINAL_VINTAGE", "OOS_A", "OOS_B_START", "TRAIN_START", "Study", "load_study"]

DEV = (pd.Period("1971-08", "M"), pd.Period("1999-12", "M"))
OOS_A = (pd.Period("2000-01", "M"), pd.Period("2018-12", "M"))
OOS_B_START = pd.Period("2019-01", "M")
FINAL_VINTAGE = pd.Period("2019-02", "M")


@dataclass
class Study:
    curve: gsw.GswCurve
    zeros: pd.DataFrame
    bey: pd.Series
    cash: pd.Series
    outcomes: Outcomes
    vintage_payloads: dict[pd.Period, bytes]
    raw_root: Path
    _vintages: dict[pd.Period, fredmd.Vintage] = field(default_factory=dict, repr=False)

    @property
    def yields(self) -> pd.DataFrame:
        return self.zeros[list(YIELD_MONTHS)]

    def vintage(self, month: pd.Period) -> fredmd.Vintage:
        if month not in self._vintages:
            self._vintages[month] = fredmd.parse_vintage(month, self.vintage_payloads[month])
        return self._vintages[month]

    def realtime_macro(self) -> fredmd.RealTimeMacro:
        return fredmd.RealTimeMacro(self.vintage)

    def final_macro(self) -> fredmd.FinalMacro:
        return fredmd.FinalMacro(self.vintage(FINAL_VINTAGE))

    def last_decision(self) -> pd.Period:
        return self.outcomes.excess["tlt"].dropna().index[-1] - 1


def load_vintage_payloads(root: Path) -> dict[pd.Period, bytes]:
    payloads: dict[pd.Period, bytes] = {}
    for indicator in fredmd.HISTORICAL:
        payloads.update(fredmd.zip_vintages(read_latest(root, "fredmd", indicator)))
    for indicator in indicators(root, "fredmd"):
        if indicator.startswith("monthly_"):
            month = pd.Period(indicator.removeprefix("monthly_"), "M")
            payloads[month] = read_latest(root, "fredmd", indicator)
    return dict(sorted(payloads.items()))


def load_study(raw_root: Path = RAW_ROOT, macrokit_root: Path = MACROKIT_RAW) -> Study:
    curve = gsw.load_curve(macrokit_root)
    zeros = gsw.month_end_zeros(curve, grid_months())
    bey = fred.load_dtb3_bey(raw_root).reindex(zeros.index)
    cash = fred.cash_returns(bey)
    return Study(
        curve, zeros, bey, cash, real_outcomes(zeros, cash), load_vintage_payloads(raw_root), raw_root
    )


def macro_pc1(
    vintage: fredmd.Vintage, start: pd.Period, end: pd.Period, *, lag: int = 2, anchor: str = "INDPRO"
) -> pd.Series:
    """First PC of a cleaned vintage, seen ``lag`` months late at each decision, unit variance."""
    rows = pd.period_range(start - lag, end, freq="M")
    data = vintage.transformed.reindex(rows).to_numpy(dtype=float)
    cleaner = MacroCleaner().fit(data)
    cleaned = cleaner.transform(data)
    score = Pca(1).fit(cleaned).transform(cleaned)[:, 0]
    kept = list(vintage.transformed.columns[cleaner.keep_])
    if anchor in kept and np.corrcoef(score, cleaned[:, kept.index(anchor)])[0, 1] < 0:
        score = -score
    factor = pd.Series(score / score.std(), index=rows)
    return factor.shift(lag).reindex(pd.period_range(start, end, freq="M"))
```

- [ ] **Step 4: Write `stages.py` (shared helpers, G0 and dev)**

File: `bond_timing_lab/src/bond_timing/stages.py` (create)

```python
"""Shared stage helpers and the first two stages: G0 data checks and the dev-period P1 (design §3, §8).

Every stage runner takes ``(study, workers, prior)`` and returns a JSON-ready dict; ``prior``
holds the results of the stages it depends on (see ``cli.REQUIRES``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict

import numpy as np
import pandas as pd

from . import evaluate as ev
from .backtest import REAL_TIME, Forecasts, Rules, build_tasks, run_forecasts, signal_weights
from .backtest import strategy_returns
from .data import etf, liuwu
from .features import slope, trailing_sum
from .models import ladder
from .returns import INSTRUMENTS, daily_synthetic_returns, holding_log_return
from .study import DEV, TRAIN_START, Study

PRIMARY = {"P2": "ols_p", "P3": "ols_pm", "P4": "nn_fm", "P5": "et"}
RULES = ("slope", "trend", "cp")
COST_BP = 2.0
COST_HIGH_BP = 4.0
G0_MIN_CORR = 0.95


def window(first: pd.Period, last: pd.Period) -> pd.PeriodIndex:
    return pd.period_range(first, last, freq="M")


def as_frame(series: pd.Series) -> pd.DataFrame:
    return series.to_frame(name=0)


def summary(returns: pd.Series, weights: pd.Series) -> dict:
    r = returns.dropna()
    w = weights.reindex(r.index - 1)
    return {
        "cer": ev.cer(r),
        "sharpe": ev.sharpe(r),
        "mean": float(12 * r.mean()),
        "vol": float(np.sqrt(12) * r.std(ddof=1)),
        "months": len(r),
        "switches": int((w.diff().abs() > 0).sum()),
        "hold_share": float(w.mean()),
    }


def forecast(
    study: Study,
    targets: pd.DataFrame,
    models: Sequence[str],
    *,
    decisions: pd.PeriodIndex,
    horizon: int,
    macro,
    rules: Rules = REAL_TIME,
    nn_seeds: int = 20,
    workers: int = 1,
    fixed: Mapping | None = None,
    yields: pd.DataFrame | None = None,
    full_end: pd.Period | None = None,
) -> Forecasts:
    specs = ladder(nn_seeds)
    tasks = build_tasks(
        study.yields if yields is None else yields,
        targets,
        macro,
        refit_years=range(decisions[0].year, decisions[-1].year + 1),
        window=(decisions[0], decisions[-1]),
        horizon=horizon,
        rules=rules,
        full_end=full_end,
    )
    return run_forecasts(tasks, [specs[name] for name in models], workers=workers, fixed=fixed)


def first_column(forecasts: Forecasts | None, model: str) -> pd.Series | None:
    if forecasts is None or model not in forecasts.predictions:
        return None
    return forecasts.predictions[model][0]


def rule_signals(study, outcomes, instrument: str, cp: pd.Series | None) -> dict[str, pd.Series]:
    """L1: the slope (10-year zero minus the bill), the trailing 12-month excess return, and CP."""
    return {
        "slope": slope(study.zeros, study.bey),
        "trend": trailing_sum(outcomes.excess[instrument]),
        "cp": cp if cp is not None else pd.Series(np.nan, index=study.zeros.index),
    }


def strategy_weights(
    study, outcomes, decisions: pd.PeriodIndex, forecasts: Forecasts | None, cp: Forecasts | None,
    instrument: str,
) -> dict[str, pd.Series]:
    weights = {"hold": pd.Series(1.0, index=decisions), "cash": pd.Series(0.0, index=decisions)}
    for name, signal in rule_signals(study, outcomes, instrument, first_column(cp, "cp")).items():
        weights[name] = signal_weights(signal, decisions)
    if forecasts is not None:
        for model, frame in forecasts.predictions.items():
            weights[model] = signal_weights(frame[0], decisions)
    return weights


def primary_names(p1: str) -> dict[str, str]:
    return {"P1": p1, **PRIMARY}


def primary_tests(returns: Mapping[str, pd.Series], p1: str, *, seed: int = ev.SEED) -> dict:
    """H_A: P1-P5 against always-hold (Holm over 5); H_B: P4, P5 against P1 (Holm over 2)."""
    names = primary_names(p1)
    vs_hold = {k: ev.diff_test(returns[v], returns["hold"], seed=seed) for k, v in names.items()}
    vs_p1 = {k: ev.diff_test(returns[names[k]], returns[p1], seed=seed) for k in ("P4", "P5")}
    holm_hold = ev.holm({k: t.p_cer for k, t in vs_hold.items()})
    holm_p1 = ev.holm({k: t.p_cer for k, t in vs_p1.items()})
    return {
        "vs_hold": {k: {**asdict(t), "p_holm": holm_hold[k]} for k, t in vs_hold.items()},
        "vs_p1": {k: {**asdict(t), "p_holm": holm_p1[k]} for k, t in vs_p1.items()},
    }


def run_g0(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    out: dict = {"etf": {}, "daily_outliers": {}, "gsw_vs_liuwu_bp": {}}
    for instrument, ticker in (("tlt", "TLT"), ("ief", "IEF")):
        prices = etf.load_prices(ticker, study.raw_root)
        synthetic = np.expm1(holding_log_return(study.zeros, INSTRUMENTS[instrument]))
        joint = pd.concat(
            {"synthetic": synthetic, "etf": etf.monthly_total_returns(prices)}, axis=1
        ).dropna()
        corr = float(joint.corr().iloc[0, 1])
        gap = joint["synthetic"] - joint["etf"]
        out["etf"][instrument] = {
            "first": str(joint.index[0]),
            "last": str(joint.index[-1]),
            "months": len(joint),
            "corr": corr,
            "pass": corr >= G0_MIN_CORR,
            "mean_gap_annual": float(12 * gap.mean()),
            "tracking_error_annual": float(np.sqrt(12) * gap.std(ddof=1)),
        }
        daily = pd.concat(
            {
                "synthetic": daily_synthetic_returns(
                    study.curve, INSTRUMENTS[instrument], prices.index[0].date()
                ),
                "etf": etf.daily_returns(prices),
            },
            axis=1,
        ).dropna()
        diff = daily["etf"] - daily["synthetic"]
        far = diff[diff.abs() > 5 * diff.std(ddof=1)]
        out["daily_outliers"][instrument] = {
            "days": len(daily),
            "count": len(far),
            "largest": [
                {
                    "date": str(day.date()),
                    "etf": float(daily.loc[day, "etf"]),
                    "synthetic": float(daily.loc[day, "synthetic"]),
                }
                for day in far.abs().sort_values(ascending=False).index[:20]
            ],
        }
    lw = liuwu.load_liuwu(study.raw_root)
    for n in range(1, 11):
        gap = ((study.zeros[12 * n] - lw[12 * n]) * 1e4).dropna()
        gap = gap[gap.index >= TRAIN_START]
        out["gsw_vs_liuwu_bp"][str(n)] = {
            "months": len(gap),
            "mean": float(gap.mean()),
            "sd": float(gap.std(ddof=1)),
            "max_abs": float(gap.abs().max()),
            "at": str(gap.abs().idxmax()),
        }
    bil = etf.monthly_total_returns(etf.load_prices("BIL", study.raw_root))
    cash = pd.concat({"bil": bil, "dtb3": study.cash}, axis=1).dropna()
    out["cash_bil_vs_dtb3"] = {
        "months": len(cash),
        "corr": float(cash.corr().iloc[0, 1]),
        "mean_gap_annual": float(12 * (cash["bil"] - cash["dtb3"]).mean()),
    }
    months = study.bey.index[study.bey.index >= TRAIN_START]
    out["dtb3_missing_months"] = [str(m) for m in months[study.bey.reindex(months).isna().to_numpy()]]
    out["pass"] = all(row["pass"] for row in out["etf"].values())
    return out


def run_dev(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    """Pick P1: the best L1 rule by TLT-like CER (2 bp) over the dev months all three rules share."""
    decisions = window(*DEV)
    cp = forecast(
        study, as_frame(study.outcomes.rxbar), ["cp"], decisions=decisions, horizon=12, macro=None,
        workers=workers,
    )
    out: dict = {"window": [str(decisions[0]), str(decisions[-1])], "instruments": {}}
    for instrument in ("tlt", "ief"):
        signals = rule_signals(study, study.outcomes, instrument, first_column(cp, "cp"))
        excess = study.outcomes.excess[instrument]
        defined = pd.concat([s.reindex(decisions) for s in signals.values()], axis=1).notna().all(axis=1)
        defined &= excess.reindex(decisions + 1).notna().to_numpy()
        common = decisions[defined.to_numpy()]
        table = {}
        for name, signal in signals.items():
            weights = signal_weights(signal, common)
            table[name] = summary(strategy_returns(weights, excess, COST_BP), weights)
        hold = pd.Series(1.0, index=common)
        table["hold"] = summary(strategy_returns(hold, excess, COST_BP), hold)
        out["instruments"][instrument] = {
            "common": [str(common[0]), str(common[-1]), len(common)],
            "rules": table,
        }
    tlt = out["instruments"]["tlt"]["rules"]
    out["p1"] = max(RULES, key=lambda name: tlt[name]["cer"])
    out["cp_refits"] = sorted(cp.params.get("cp", {}))
    return out
```

- [ ] **Step 5: Write `cli.py`**

File: `bond_timing_lab/src/bond_timing/cli.py` (create)

```python
"""Command line: ``bond-timing snapshot``, ``run STAGE`` and ``report`` (design §3.6, §9).

The stage order is enforced here: PREREG.md must be committed before G1 and every
out-of-sample stage, OOS-A needs a passed G1, and OOS-B runs once (a lock file); a rerun
needs a reason and never replaces the verdict of record.
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd

LAB = Path(__file__).resolve().parents[2]
RESULTS = LAB / "results"
RUNNERS = {
    "g0": ("bond_timing.stages", "run_g0"),
    "dev": ("bond_timing.stages", "run_dev"),
    "g1": ("bond_timing.g1", "run_g1"),
    "oos-a": ("bond_timing.oos_a", "run_oos_a"),
    "decompose": ("bond_timing.decomposition", "run_decomposition"),
    "g3": ("bond_timing.g3", "run_g3"),
    "oos-b": ("bond_timing.oos_b", "run_oos_b"),
}
REQUIRES = {
    "g0": (),
    "dev": (),
    "g1": ("dev",),
    "oos-a": ("dev", "g1"),
    "decompose": ("oos_a",),
    "g3": ("oos_a",),
    "oos-b": ("dev", "oos_a", "g3"),
}
NEEDS_PREREG = ("g1", "oos-a", "decompose", "g3", "oos-b")


class StageError(click.ClickException):
    """A stage was asked to run before the stages it depends on, or a second time."""


def _json_default(value):
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, (pd.Period, pd.Timestamp)):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(LAB), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def meta() -> dict:
    return {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain", "--", ".")),
        "prereg_commit": _git("log", "-1", "--format=%H", "--", "PREREG.md"),
    }


def read_result(name: str, results: Path = RESULTS) -> dict:
    path = results / f"{name}.json"
    if not path.exists():
        raise StageError(f"{path} is missing; run its stage first")
    return json.loads(path.read_text(encoding="utf-8"))


def write_result(name: str, result: dict, results: Path, run_meta: dict) -> Path:
    results.mkdir(parents=True, exist_ok=True)
    path = results / f"{name}.json"
    text = json.dumps(
        {"meta": run_meta, **result}, indent=1, ensure_ascii=False, default=_json_default
    )
    path.write_text(text + "\n", encoding="utf-8")
    return path


def check_ready(stage: str, results: Path, prereg_commit: str) -> dict[str, dict]:
    prior = {name: read_result(name, results) for name in REQUIRES[stage]}
    if stage in NEEDS_PREREG and not prereg_commit:
        raise StageError("PREREG.md must be committed before G1 and the out-of-sample stages")
    if stage == "oos-a" and not prior["g1"].get("pass"):
        raise StageError("G1 did not pass; fix the tools before running OOS-A")
    return prior


def oos_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
    lock = results / "oos_b.lock"
    if not lock.exists():
        return "oos_b", {}
    if not rerun_reason:
        raise StageError(
            f"OOS-B already ran ({lock.read_text().strip()}); pass --rerun-reason to run it again"
        )
    n = 1
    while (results / f"oos_b_rerun_{n}.json").exists():
        n += 1
    record = read_result("oos_b", results)["verdict"]
    return f"oos_b_rerun_{n}", {"rerun_reason": rerun_reason, "verdict_of_record": record}


def take_lock(results: Path, commit: str) -> None:
    results.mkdir(parents=True, exist_ok=True)
    with (results / "oos_b.lock").open("x", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {commit}\n")


@click.group()
def main() -> None:
    """Bond-timing study (design 2026-10-19)."""


@main.command()
def snapshot() -> None:
    """Fetch every raw input into the snapshot store."""
    from .data.snapshot import snapshot_all

    for line in snapshot_all():
        click.echo(line)


@main.command()
@click.argument("stage", type=click.Choice(list(RUNNERS)))
@click.option("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2), show_default=True)
@click.option("--rerun-reason", default=None, help="Required to run oos-b a second time.")
def run(stage: str, workers: int, rerun_reason: str | None) -> None:
    """Run one stage and write results/<stage>.json."""
    from .study import load_study

    run_meta = meta()
    prior = check_ready(stage, RESULTS, run_meta["prereg_commit"])
    name, extra = (stage.replace("-", "_"), {})
    if stage == "oos-b":
        name, extra = oos_b_target(RESULTS, rerun_reason)
        if name == "oos_b":
            take_lock(RESULTS, run_meta["git_commit"])
    module, function = RUNNERS[stage]
    runner = getattr(importlib.import_module(module), function)
    try:
        result = runner(load_study(), workers, prior)
    except BaseException:
        if name == "oos_b":
            (RESULTS / "oos_b.lock").unlink(missing_ok=True)  # nothing was seen; allow a clean run
        raise
    click.echo(write_result(name, {**extra, **result}, RESULTS, run_meta))


@main.command()
def report() -> None:
    """Write results/summary.md from the results JSON."""
    from .report import render

    path = RESULTS / "summary.md"
    path.write_text(render(RESULTS), encoding="utf-8")
    click.echo(path)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests -q`
Expected: all tests pass (`81 passed, 1 skipped` with the counts of Tasks 1–13).

- [ ] **Step 7: Snapshot the real data**

```bash
cd $WT && $BT snapshot
```

Expected lines for `fred/DTB3`, `fred/TB3MS`, both FRED-MD archives (about 46 MB and 36 MB), `fredmd/monthly_2026-01` … `2026-09` stored, `fredmd/monthly_2026-10: not published` (unless it has appeared), `liuwu/monthly`, `etf/TLT`, `etf/IEF`, `etf/BIL`, and `us_term/gsw: read from …`. Then confirm every month 1999-08..2026-09 has a vintage:

```bash
cd $WT && $PY - <<'EOF'
import pandas as pd
from bond_timing.study import load_vintage_payloads
from bond_timing.data.store import RAW_ROOT
p = load_vintage_payloads(RAW_ROOT)
need = pd.period_range("1999-08", "2026-09", freq="M")
print(len(p), "vintages; missing:", [str(m) for m in need if m not in p])
EOF
```

Expected: `missing: []`. A missing month stops the plan: it breaks R1 for every decision that needs it.

- [ ] **Step 8: Run G0 and dev**

```bash
cd $WT && $BT run g0 && $BT run dev && $PY - <<'EOF'
import json
g0 = json.load(open("bond_timing_lab/results/g0.json")); dev = json.load(open("bond_timing_lab/results/dev.json"))
print({k: (round(v["corr"], 4), v["pass"]) for k, v in g0["etf"].items()}, "pass:", g0["pass"])
print("P1 =", dev["p1"], {k: round(v["cer"], 4) for k, v in dev["instruments"]["tlt"]["rules"].items()}, dev["instruments"]["tlt"]["common"])
EOF
```

Expected: G0 correlations at or above 0.95 for both; a P1 name from `slope`, `trend`, `cp`; common months 1982-07..1999-12. If a correlation is below 0.95, record it: the spec then uses actual ETF returns for that type from 2002-08; stop and report before PREREG, because the verdict instrument changes.

- [ ] **Step 9: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Assemble the study, run the G0 data checks and choose P1 in the dev period"
```

---

### Task 14: Pre-registration

**Files:**
- Create: `bond_timing_lab/PREREG.md`

**Interfaces:**
- Consumes: `results/g0.json`, `results/dev.json` (Task 13).
- Produces: the commit whose hash every later result records as `meta.prereg_commit`.

- [ ] **Step 1: Write PREREG.md**

File: `bond_timing_lab/PREREG.md` (create). Fill the two bracketed values from `results/dev.json` (`p1`, `instruments.tlt.common`) and `results/g0.json` (`etf.*.corr`) before saving; everything else is fixed text.

```markdown
# 事前登録：債券タイミングの売買シグナル（候補9）

- 設計書：`/home/kazumasa/projects/docs/superpowers/specs/2026-10-19-bond-timing-ml-design.md`
- 実装計画：`/home/kazumasa/projects/docs/superpowers/plans/2026-10-19-bond-timing-ml.md`
- この文書の commit のあとで、G1 と本番 A（判断 2000-01〜2018-12）を初めて回す。以下を変えたら、結果の JSON と README に、変えたこと・理由・変える前に見ていた結果を書く。

## 1. 判定（設計書 §3 のまま）

- 売買：月末 t の終値で、翌月を TLT 型（17年ゼロ）100% か現金 100% にする。費用は切り替え1回 2bp（感度 4bp）。
- 主な戦略5本：P1（開発期間で選んだ単純ルール）、P2（利回りの主成分3つの OLS）、P3（P2＋実時間のマクロ因子8つ）、P4（NN、フォワード＋マクロ、初期値20通り）、P5（Extra Trees、フォワード＋マクロ）。
- 仮説：H_A（P1〜P5 が L0＝ずっと保有に CER で勝つ、Holm 5本）、H_B（P4・P5 が P1 に勝つ、Holm 2本）。片側5%。
- 検定：同じ月の差の系列に定常ブートストラップ（平均ブロック12か月、1万回、種 20261019）。
- 判定：`ml_signal_usable`、`simple_rule_usable`、`no_usable_signal`（設計書 §3.5 の条件をそのまま使う）。

## 2. 開発期間の結果（本番 A の前に確定）

- P1 = [results/dev.json の p1]（TLT 型、費用 2bp、3つのルールがそろう判断月 [common の最初]〜[common の最後]）。
- G0：合成と実際の ETF の月次リターンの相関は TLT [g0 の値]、IEF [g0 の値]。

## 3. 設計書が決めていない点の決定

1. 期間は判断の月で数える。判断 t のリターンは t+1 の月に実現する。本番 A は判断 2000-01〜2018-12（リターン 2000-02〜2019-01、228か月）、本番 B は判断 2019-01 から、リターンが確定している最後の月まで。
2. 現金は DTB3 の月末値を債券換算利回り BEY = 365d/(360−91d) にし、翌月の現金のリターンを BEY/12（単利）とする。傾きのルールでは BEY を 91日複利から連続複利に直して 10年ゼロと比べる。
3. 戦略の超過リターンは r(t+1) = w(t)・(合成債の単利リターン − 現金) − 費用・|w(t) − w(t−1)|。費用は新しいポジションの最初の月から引く。評価期間の最初の月には費用を引かない。
4. CER と Sharpe の分散は不偏（ddof=1）。ばらつきが0の系列の Sharpe は0。
5. ブートストラップの p 値は中心化：p = (1 + #{D* − D ≥ D}) / (B + 1)。すべての比較で同じ種を使う。
6. 実時間のマクロ：判断 t はビンテージ t−1。系列 j の公表の遅れ ℓ(j) は、t から「ビンテージ t−1 で値がある最後の月」を引いた月数。ℓ(j) が6か月を超える系列は使わない。学習の行 s には、同じビンテージの x_j(s − ℓ(j)) を入れる。1月の再推定で決めた系列と ℓ(j) を、その年の予測に使う。予測の月のビンテージに値がなければ、それより前の最新の値を使い、系列がなければ欠損（前処理で0）とする。
7. マクロの前処理（毎回、学習の行だけで推定）：変換後の値で |x − 中央値| > 10 IQR を欠損にし、標準化し、欠損が20%を超える系列を外し、残りの欠損を0にする。
8. P は 1〜10年金利（中心化だけ）の主成分3つ。F は標準化する。P3 のマクロ因子8つは前処理後のマクロの主成分。
9. CP 因子は、満期2〜10年の rx12 の平均を F に回帰した予測値。
10. Elastic Net の α は、l1_ratio ごとに α_max = max|X'z|/(n・l1_ratio)（z は標準化した目的変数）から α_max/1000 まで、対数で等間隔の20点。
11. NN-F にも、NN-FM と同じ L2 の候補 {1e-4, 1e-3, 1e-2} を使う。
12. OLS 以外のモデルは、窓の中で標準化した目的変数を学習し、予測を元の単位に戻す。候補の選択の損失は、各目的変数を（検証より前の学習の行の）分散で割った平均二乗誤差。
13. 比率型（副、判定に使わない）：w = clip((rx12 の予測/12) / (γ・過去60か月の月次超過リターンの分散), 0, 1)。分散は36か月以上ある月だけ。
14. X のうち実現ボラティリティは、どの戦略も使わない（設計書 §6.2 のモデルの入力は F と M だけ）。
15. 5営業日遅れ：判断 t の切り替えを、t+1 の月の GSW の5番目の観測日の終値で行う。切り替えた月だけ、日次の GSW のパラメーターから2区間に分けて計算する（年数は実日数/365.25、現金は日数で按分）。切り替えのない月は月末執行と同じ。
16. G1 の W0：満期2〜10年の10年ゼロまでの月次の対数超過リターンと、TLT 型・IEF 型・10年ゼロの単利超過リターンを、同じ並びの定常ブートストラップ（平均ブロック12）で 1971-08〜2019-01 に並べ直す。元にする月は、すべてがそろう 1981-08〜2019-01。rx12 は月次の対数超過リターンの12か月の和で作り直す。種は 1000〜1019。
17. G1 の W2：W0 に k・(D/10)・z(t) を足す（D は年限、TLT 型は17、z(t) はビンテージ 2019-02 の変換後のマクロ（前処理は 1971-06〜2018-12 で推定）の第1主成分を2か月遅らせ、分散を1にしたもの。符号は INDPRO と正の相関になる向き）。k は、本番 A の判断で「z(t) > 0 なら保有」の CER が L0 より年4%以上よくなる最小の値で、実データの TLT 型で1回だけ決める。種は 2000〜2019。G1 の NN は初期値5通り（候補の値の選択は本番と同じ）。
18. G3：GSW の19年限（12, 23, 24, 35, 36, …, 119, 120 か月）の主成分3つの VAR(1)＋測定誤差と、ビンテージ 2019-02 のマクロ（前処理後）の因子8つの VAR(1)＋固有成分。各月の残差の組を、まとめて iid に引く。シミュレーションのマクロは、すべての系列が2か月遅れで観測されるとして扱う。対象は10年ゼロ、現金は y(1年)/12。実データの統計量も同じ対象と現金で、実時間のマクロで計算する。初期値5通り、候補の値は本番 A の各年の選択に固定。種は 3000〜3199。
19. 実際の ETF（補足）：シグナルは合成と同じものを使い、月次の配当込みリターンから DTB3 の現金を引いて評価する。
20. G1 の W2 が通らないときは、本番 A を回さずに止め、結果と原因の見立てを記録して相談する（設計書 §3.6 の「確認を通してから本番」）。
```

- [ ] **Step 2: Commit it and record the hash**

```bash
cd $WT && git add bond_timing_lab/PREREG.md && git commit -m "Pre-register the bond-timing tests before G1 and OOS-A" && git log -1 --format=%H -- bond_timing_lab/PREREG.md
```

Expected: the printed hash is what `meta.prereg_commit` shows in every later result.

---

### Task 15: G1 synthetic-world checks

**Files:**
- Create: `bond_timing_lab/src/bond_timing/g1.py`
- Test: `bond_timing_lab/tests/test_g1.py`
- Produce (committed): `bond_timing_lab/results/g1.json`

**Interfaces:**
- Consumes: `stages.forecast`, `as_frame`, `primary_names`, `primary_tests`, `strategy_weights`, `window`, `COST_BP`; `study.FINAL_VINTAGE`, `OOS_A`, `TRAIN_START`, `macro_pc1`; `synthetic.w0_world`, `plant`, `calibrate_k`; `backtest.strategy_returns`.
- Produces: `count_significant(runs, names) -> dict[str, int]`, `g1_passed(counts) -> bool`, `run_g1(study, workers, prior) -> dict` with keys `p1`, `k`, `nn_seeds`, `counts`, `pass`, `worlds`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_g1.py` (create)

```python
from bond_timing.g1 import count_significant, g1_passed


def test_count_significant_uses_the_holm_p_values():
    runs = [{"p_holm": {"P1": 0.01, "P2": 0.5}}, {"p_holm": {"P1": 0.04, "P2": 0.05}}]
    assert count_significant(runs, ["P1", "P2"]) == {"P1": 2, "P2": 0}


def test_g1_pass_rule():
    w0 = {"P1": 2, "P2": 0, "P3": 1, "P4": 2, "P5": 0}
    w2 = {"P1": 0, "P2": 3, "P3": 18, "P4": 19, "P5": 5}
    assert g1_passed({"W0": w0, "W2": w2})
    assert not g1_passed({"W0": {**w0, "P5": 3}, "W2": w2})
    assert not g1_passed({"W0": w0, "W2": {**w2, "P3": 17}})
    assert not g1_passed({"W0": w0, "W2": {**w2, "P4": 17}})
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_g1.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.g1'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/g1.py` (create)

```python
"""G1: worlds with no signal (W0) and with a planted macro signal (W2) (design §8, PREREG 16-17).

Pass: in W0 no primary strategy is significant (H_A, Holm) in more than 2 of 20 worlds; in W2
P3 and P4 are each significant in at least 18 of 20.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

import pandas as pd

from . import evaluate as ev
from .backtest import strategy_returns
from .stages import COST_BP, as_frame, forecast, primary_names, primary_tests, strategy_weights
from .stages import window
from .study import FINAL_VINTAGE, OOS_A, TRAIN_START, Study, macro_pc1
from .synthetic import calibrate_k, plant, w0_world

REPS = 20
NN_SEEDS = 5
MAX_FALSE = 2
MIN_DETECT = 18
MODELS = ["ols_p", "ols_pm", "nn_fm", "et"]
SEEDS = {"W0": 1000, "W2": 2000}


def count_significant(runs: Sequence[Mapping], names: Sequence[str]) -> dict[str, int]:
    return {name: sum(run["p_holm"][name] < ev.ALPHA for run in runs) for name in names}


def g1_passed(counts: Mapping[str, Mapping[str, int]]) -> bool:
    return (
        all(count <= MAX_FALSE for count in counts["W0"].values())
        and counts["W2"]["P3"] >= MIN_DETECT
        and counts["W2"]["P4"] >= MIN_DETECT
    )


def run_g1(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(*OOS_A)
    end = OOS_A[1] + 1
    source = replace(
        study.outcomes,
        excess=study.outcomes.excess.loc[:end],
        monthly_log_excess=study.outcomes.monthly_log_excess.loc[:end],
    )
    index = pd.period_range(TRAIN_START, end, freq="M")
    z = macro_pc1(study.vintage(FINAL_VINTAGE), TRAIN_START, OOS_A[1])
    k = calibrate_k(study.outcomes.excess["tlt"], z, decisions)
    macro = study.realtime_macro()
    worlds: dict[str, list[dict]] = {"W0": [], "W2": []}
    for family, base in SEEDS.items():
        for rep in range(REPS):
            seed = base + rep
            world = w0_world(source, index, seed)
            if family == "W2":
                world = plant(world, z, k)
            fc = forecast(
                study, as_frame(world.rx12[10]), MODELS, decisions=decisions, horizon=12,
                macro=macro, nn_seeds=NN_SEEDS, workers=workers,
            )
            cp = None
            if p1 == "cp":
                cp = forecast(
                    study, as_frame(world.rxbar), ["cp"], decisions=decisions, horizon=12,
                    macro=None, workers=workers,
                )
            weights = strategy_weights(study, world, decisions, fc, cp, "tlt")
            returns = {
                name: strategy_returns(w, world.excess["tlt"], COST_BP) for name, w in weights.items()
            }
            tests = primary_tests(returns, p1, seed=ev.SEED + seed)
            worlds[family].append(
                {
                    "seed": seed,
                    "p_holm": {s: t["p_holm"] for s, t in tests["vs_hold"].items()},
                    "delta_cer": {s: t["delta_cer"] for s, t in tests["vs_hold"].items()},
                }
            )
    names = list(primary_names(p1))
    counts = {family: count_significant(runs, names) for family, runs in worlds.items()}
    return {
        "p1": p1,
        "k": k,
        "nn_seeds": NN_SEEDS,
        "counts": counts,
        "pass": g1_passed(counts),
        "worlds": worlds,
    }
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_g1.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Run G1 on the real features (about 20–40 minutes on 18 workers)**

```bash
cd $WT && $BT run g1 && $PY -c "import json; g=json.load(open('bond_timing_lab/results/g1.json')); print(g['counts'], 'pass:', g['pass'], 'k:', g['k'])"
```

Expected: `pass: True`. If W0 fails, a tool is biased: find it before anything else. If only W2 fails, follow PREREG item 20: commit `g1.json`, stop, and report the counts with the diagnosis (for example, how often the models' 12-month forecasts are negative in W2 worlds) instead of running OOS-A.

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Run G1 on no-signal and planted-signal worlds"
```

---

### Task 16: OOS-A and the V0–V3 decomposition

**Files:**
- Create: `bond_timing_lab/src/bond_timing/oos_a.py`, `bond_timing_lab/src/bond_timing/decomposition.py`
- Test: `bond_timing_lab/tests/test_oos_a.py`, `bond_timing_lab/tests/test_decomposition.py`
- Produce (committed): `bond_timing_lab/results/oos_a.json`, `bond_timing_lab/results/decompose.json`

**Interfaces:**
- Consumes: `stages.*` helpers; `backtest.delayed_returns`, `fractional_weights`, `signal_weights`, `strategy_returns`, `Forecasts`, `V0`, `V1`, `V2`, `V3`; `returns.delayed_switch_excess`, `INSTRUMENTS`, `RX_YEARS`, `rx12`; `data.etf`, `data.liuwu`; `evaluate.*`.
- Produces: `oos_a.MODELS`, `oos_a.evaluate_instrument(study, outcomes, decisions, primary, cp, p1, instrument, legs) -> dict` (keys `summary`, `summary_4bp`, `tests`, `robust`, and `summary_delay` when legs are given), `oos_a.run_oos_a(study, workers, prior) -> dict` (keys `window`, `p1`, `instruments`, `secondary`, `fractional`, `r2_oos`, `etf`, `weights`, `params`, `params_secondary`); `decomposition.SETTINGS`, `decomposition.r2_table(targets, forecasts, decisions, *, complete) -> dict`, `decomposition.run_decomposition(study, workers, prior) -> dict`.

- [ ] **Step 1: Write the failing tests**

File: `bond_timing_lab/tests/test_oos_a.py` (create)

```python
from types import SimpleNamespace

import numpy as np
import pandas as pd
from bond_timing.backtest import Forecasts
from bond_timing.oos_a import evaluate_instrument


def test_evaluate_instrument_reports_tests_and_robustness():
    index = pd.period_range("1998-01", "2004-12", freq="M")
    rng = np.random.default_rng(0)
    study = SimpleNamespace(
        zeros=pd.DataFrame({120: 0.05 + rng.normal(0, 0.002, len(index))}, index=index),
        bey=pd.Series(0.05, index=index),
    )
    outcomes = SimpleNamespace(
        excess=pd.DataFrame({"tlt": rng.normal(0.003, 0.03, len(index))}, index=index)
    )
    decisions = pd.period_range("2000-01", "2003-12", freq="M")
    predictions = {
        model: pd.DataFrame({0: rng.normal(0.01, 0.02, len(decisions))}, index=decisions)
        for model in ("ols_p", "ols_pm", "nn_fm", "et")
    }
    legs = pd.DataFrame({"in": 0.001, "out": -0.001}, index=decisions + 1)
    entry = evaluate_instrument(
        study, outcomes, decisions, Forecasts(predictions, {}), None, "slope", "tlt", legs
    )
    assert set(entry["robust"]) == {"P1", "P2", "P3", "P4", "P5"}
    assert set(entry["robust"]["P4"]) == {"vs_hold_4bp", "vs_p1_4bp", "vs_hold_delay", "vs_p1_delay"}
    assert entry["tests"]["vs_hold"]["P2"]["months"] == 48
    assert "summary_delay" in entry and "hold" in entry["summary_4bp"]
```

File: `bond_timing_lab/tests/test_decomposition.py` (create)

```python
import numpy as np
import pandas as pd
from bond_timing.backtest import Forecasts
from bond_timing.decomposition import SETTINGS, r2_table


def test_r2_table_scores_each_maturity_and_the_average():
    index = pd.period_range("1980-01", "1995-12", freq="M")
    rng = np.random.default_rng(1)
    targets = pd.DataFrame({2: rng.normal(size=len(index)), 3: rng.normal(size=len(index))}, index=index)
    decisions = pd.period_range("1990-01", "1993-12", freq="M")
    perfect = Forecasts({"ols_p": targets.reindex(decisions).set_axis([0, 1], axis=1)}, {})
    assert r2_table(targets, perfect, decisions, complete=True) == {
        "ols_p": {"2": 1.0, "3": 1.0, "avg": 1.0}
    }


def test_settings_add_one_rule_at_a_time():
    rules = {name: setting[2] for name, setting in SETTINGS.items()}
    assert not any(vars(rules["V0_gsw"]).values())
    assert rules["V1"].complete_targets and not rules["V1"].embargo
    assert rules["V2"].embargo and rules["V2"].in_window and not rules["V2"].real_time_macro
    assert all(vars(rules["V3"]).values())
    assert SETTINGS["V3"][1] == "realtime" and SETTINGS["V2"][1] == "final"
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_oos_a.py bond_timing_lab/tests/test_decomposition.py -q`
Expected: FAIL with `ModuleNotFoundError` for `bond_timing.oos_a` and `bond_timing.decomposition`.

- [ ] **Step 3: Write `oos_a.py`**

File: `bond_timing_lab/src/bond_timing/oos_a.py` (create)

```python
"""OOS-A: the pre-registered test on decisions 2000-01..2018-12 (design §3.4-3.5, PREREG §1).

Reported beside the verdict inputs: IEF-like and 10-year-zero results, the secondary target,
0-100 % weights, R2oos, and the same signals on actual TLT/IEF returns.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from . import evaluate as ev
from .backtest import Forecasts, delayed_returns, fractional_weights, signal_weights
from .backtest import strategy_returns
from .data import etf
from .returns import INSTRUMENTS, delayed_switch_excess
from .stages import COST_BP, COST_HIGH_BP, as_frame, forecast, primary_names, primary_tests
from .stages import strategy_weights, summary, window
from .study import OOS_A, Study

MODELS = ["ols_p", "ols_pm", "en", "et", "hgb", "nn_f", "nn_fm"]


def _cer(r: pd.Series) -> float:
    return ev.cer(r.dropna())


def evaluate_instrument(
    study, outcomes, decisions: pd.PeriodIndex, primary: Forecasts, cp: Forecasts | None, p1: str,
    instrument: str, legs: pd.DataFrame | None,
) -> dict:
    weights = strategy_weights(study, outcomes, decisions, primary, cp, instrument)
    excess = outcomes.excess[instrument]
    base = {name: strategy_returns(w, excess, COST_BP) for name, w in weights.items()}
    high = {name: strategy_returns(w, excess, COST_HIGH_BP) for name, w in weights.items()}
    entry = {
        "summary": {name: summary(base[name], weights[name]) for name in weights},
        "summary_4bp": {name: summary(high[name], weights[name]) for name in weights},
        "tests": primary_tests(base, p1),
    }
    names = primary_names(p1)
    robust = {
        k: {
            "vs_hold_4bp": _cer(high[v]) - _cer(high["hold"]),
            "vs_p1_4bp": _cer(high[v]) - _cer(high[p1]),
        }
        for k, v in names.items()
    }
    if legs is not None:
        delayed = {name: delayed_returns(w, excess, legs, COST_BP) for name, w in weights.items()}
        entry["summary_delay"] = {name: summary(delayed[name], weights[name]) for name in weights}
        for k, v in names.items():
            robust[k]["vs_hold_delay"] = _cer(delayed[v]) - _cer(delayed["hold"])
            robust[k]["vs_p1_delay"] = _cer(delayed[v]) - _cer(delayed[p1])
    entry["robust"] = robust
    return entry


def run_oos_a(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(*OOS_A)
    macro = study.realtime_macro()
    primary = forecast(
        study, as_frame(study.outcomes.rx12[10]), MODELS, decisions=decisions, horizon=12,
        macro=macro, workers=workers,
    )
    secondary = forecast(
        study, as_frame(study.outcomes.xr1), MODELS, decisions=decisions, horizon=1, macro=macro,
        workers=workers,
    )
    cp = forecast(
        study, as_frame(study.outcomes.rxbar), ["cp"], decisions=decisions, horizon=12, macro=None,
        workers=workers,
    )
    out: dict = {"window": [str(decisions[0]), str(decisions[-1])], "p1": p1, "instruments": {}}
    for instrument in ("tlt", "ief", "z10"):
        legs = None
        if instrument != "z10":
            legs = delayed_switch_excess(study.curve, INSTRUMENTS[instrument], study.cash)
        out["instruments"][instrument] = evaluate_instrument(
            study, study.outcomes, decisions, primary, cp, p1, instrument, legs
        )
    out["secondary"] = _secondary(study, decisions, secondary)
    out["fractional"] = _fractional(study, decisions, primary)
    out["r2_oos"] = _r2(study, decisions, primary, secondary)
    out["etf"] = _etf(study, decisions, primary, cp, p1)
    tlt = strategy_weights(study, study.outcomes, decisions, primary, cp, "tlt")
    out["weights"] = {
        "decisions": [str(d) for d in decisions],
        **{k: tlt[v].astype(int).tolist() for k, v in primary_names(p1).items()},
    }
    out["params"] = primary.params
    out["params_secondary"] = secondary.params
    return out


def _secondary(study: Study, decisions: pd.PeriodIndex, secondary: Forecasts) -> dict:
    out = {}
    for instrument in ("tlt", "ief"):
        excess = study.outcomes.excess[instrument]
        weights = {m: signal_weights(f[0], decisions) for m, f in secondary.predictions.items()}
        out[instrument] = {m: summary(strategy_returns(w, excess, COST_BP), w) for m, w in weights.items()}
    return out


def _fractional(study: Study, decisions: pd.PeriodIndex, primary: Forecasts) -> dict:
    out: dict = {}
    for instrument in ("tlt", "ief"):
        excess = study.outcomes.excess[instrument]
        out[instrument] = {}
        for model, frame in primary.predictions.items():
            w = fractional_weights(frame[0], excess, decisions)
            out[instrument][model] = summary(strategy_returns(w, excess, COST_BP), w)
    return out


def _r2(study: Study, decisions: pd.PeriodIndex, primary: Forecasts, secondary: Forecasts) -> dict:
    rx, xr = study.outcomes.rx12[10], study.outcomes.xr1
    rx_bench = ev.prevailing_mean(rx, decisions, 12)
    xr_bench = ev.prevailing_mean(xr, decisions, 1)
    return {
        "rx12_10": {
            m: ev.r2_oos(rx.reindex(decisions), f[0].reindex(decisions), rx_bench)
            for m, f in primary.predictions.items()
        },
        "xr1_10": {
            m: ev.r2_oos(xr.reindex(decisions), f[0].reindex(decisions), xr_bench)
            for m, f in secondary.predictions.items()
        },
    }


def _etf(study: Study, decisions: pd.PeriodIndex, primary: Forecasts, cp: Forecasts, p1: str) -> dict:
    out = {}
    for instrument, ticker in (("tlt", "TLT"), ("ief", "IEF")):
        actual = etf.monthly_total_returns(etf.load_prices(ticker, study.raw_root))
        excess = (actual - study.cash).dropna()
        span = decisions[np.asarray((decisions + 1).isin(excess.index))]
        weights = strategy_weights(study, study.outcomes, span, primary, cp, instrument)
        base = {name: strategy_returns(w, excess, COST_BP) for name, w in weights.items()}
        out[instrument] = {
            "window": [str(span[0]), str(span[-1])],
            "summary": {name: summary(base[name], weights[name]) for name in weights},
            "tests": primary_tests(base, p1),
        }
    return out
```

- [ ] **Step 4: Write `decomposition.py`**

File: `bond_timing_lab/src/bond_timing/decomposition.py` (create)

```python
"""Apparent predictability, one point-in-time rule at a time (design §7; reported, not judged).

V0  paper-like: final vintage 2019-02 with the publication lag ignored, unrealized targets in
    training (s <= t-1), no embargo, transforms on the full 1971-08..2018-12 sample; Liu-Wu and GSW
V1  V0 + R2;  V2  V1 + R3 + R4;  V3  V2 + R1 (real-time vintages), 2000-01..2018-12 only.
Targets rx12 for 2..10 years (one multi-output model) and their average; R2oos is against the
prevailing mean the same setting could compute.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from . import evaluate as ev
from .backtest import V0, V1, V2, V3, Forecasts, Rules
from .data import liuwu
from .features import YIELD_MONTHS
from .returns import RX_YEARS, rx12
from .stages import forecast, window
from .study import OOS_A, Study

MODELS = ["ols_p", "en", "et", "nn_fm"]
FULL_END = pd.Period("2018-12", "M")
EARLY = (pd.Period("1990-01", "M"), pd.Period("2018-12", "M"))
SETTINGS: dict[str, tuple[str, str, Rules, tuple[pd.Period, pd.Period]]] = {
    "V0_liuwu": ("liuwu", "final", V0, EARLY),
    "V0_gsw": ("gsw", "final", V0, EARLY),
    "V1": ("gsw", "final", V1, EARLY),
    "V2": ("gsw", "final", V2, EARLY),
    "V3": ("gsw", "realtime", V3, OOS_A),
}


def r2_table(
    targets: pd.DataFrame, forecasts: Forecasts, decisions: pd.PeriodIndex, *, complete: bool
) -> dict:
    average = targets.mean(axis=1, skipna=False)
    average_bench = ev.prevailing_mean(average, decisions, 12, complete=complete)
    table = {}
    for model, frame in forecasts.predictions.items():
        prediction = frame.reindex(decisions)
        prediction.columns = list(targets.columns)
        row = {}
        for n in targets.columns:
            bench = ev.prevailing_mean(targets[n], decisions, 12, complete=complete)
            row[str(n)] = ev.r2_oos(targets[n].reindex(decisions), prediction[n], bench)
        row["avg"] = ev.r2_oos(average.reindex(decisions), prediction.mean(axis=1), average_bench)
        table[model] = row
    return table


def run_decomposition(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    curves = {"gsw": study.zeros, "liuwu": liuwu.load_liuwu(study.raw_root)}
    out: dict = {}
    for name, (curve, macro_kind, rules, span) in SETTINGS.items():
        zeros = curves[curve]
        targets = pd.concat({n: rx12(zeros, n) for n in RX_YEARS}, axis=1)
        macro = study.final_macro() if macro_kind == "final" else study.realtime_macro()
        decisions = window(*span)
        fc = forecast(
            study, targets, MODELS, decisions=decisions, horizon=12, macro=macro, rules=rules,
            workers=workers, yields=zeros[list(YIELD_MONTHS)], full_end=FULL_END,
        )
        out[name] = r2_table(targets, fc, decisions, complete=rules.complete_targets)
        if name == "V2":
            out["V2_from_2000"] = r2_table(
                targets, fc, decisions[decisions >= OOS_A[0]], complete=True
            )
    return out
```

- [ ] **Step 5: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_oos_a.py bond_timing_lab/tests/test_decomposition.py -q`
Expected: `3 passed`.

- [ ] **Step 6: Run OOS-A, then the decomposition**

```bash
cd $WT && $BT run oos-a && $PY - <<'EOF'
import json
r = json.load(open("bond_timing_lab/results/oos_a.json")); t = r["instruments"]["tlt"]
for k, v in t["tests"]["vs_hold"].items(): print(k, round(v["delta_cer"], 4), round(v["p_holm"], 3))
for k, v in t["tests"]["vs_p1"].items(): print(k, "vs P1", round(v["delta_cer"], 4), round(v["p_holm"], 3))
print({k: {m: round(x, 4) for m, x in v.items()} for k, v in t["robust"].items()})
EOF
cd $WT && $BT run decompose && $PY -c "import json; d=json.load(open('bond_timing_lab/results/decompose.json')); print({s: {m: round(r['avg'], 3) for m, r in t.items()} for s, t in d.items() if s != 'meta'})"
```

Expected: `oos_a.json` and `decompose.json` written with the prereg commit in `meta`. No expectation about the numbers.

- [ ] **Step 7: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Run the pre-registered OOS-A test and the V0-V3 decomposition"
```

---

### Task 17: G3 spanning-null check

**Files:**
- Create: `bond_timing_lab/src/bond_timing/g3.py`
- Test: `bond_timing_lab/tests/test_g3.py`
- Produce (committed): `bond_timing_lab/results/g3.json`

**Interfaces:**
- Consumes: `backtest.build_tasks`, `run_forecasts`, `signal_weights`, `strategy_returns`, `REAL_TIME`; `data.fredmd.PanelMacro`; `features.MacroCleaner`, `YIELD_MONTHS`; `models.ladder`; `returns.excess_simple`, `holding_log_return`, `rx12`; `synthetic.fit_spanning_null`, `simulate`; `results/oos_a.json` `params` (nn_fm, et per refit).
- Produces: `g3.MONTHS` (19 maturities), `g3.statistic(zeros, macro, decisions, fixed, workers) -> dict[str, float]`, `g3.run_g3(study, workers, prior) -> dict` with keys `real`, `p`, `worlds`, `nn_seeds`, `factor_max_eigenvalue`, `simulated`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_g3.py` (create)

```python
import numpy as np
import pandas as pd
from bond_timing.data.fredmd import PanelMacro
from bond_timing.g3 import MONTHS, statistic


def test_g3_uses_nineteen_maturities():
    assert len(MONTHS) == 19 and {12, 108, 119, 120} <= set(MONTHS) and 11 not in MONTHS


def test_statistic_runs_on_a_small_world():
    index = pd.period_range("1971-08", "1983-12", freq="M")
    rng = np.random.default_rng(2)
    level = 0.06 + np.cumsum(rng.normal(0, 0.002, len(index)))
    zeros = pd.DataFrame(
        {m: level + 0.0001 * m + rng.normal(0, 1e-4, len(index)) for m in MONTHS}, index=index
    )
    panel = pd.DataFrame(rng.normal(size=(len(index), 10)), index=index, columns=[f"m{j}" for j in range(10)])
    decisions = pd.period_range("1980-01", "1981-12", freq="M")
    nn = {"alpha": 0.001, "hidden_layer_sizes": [32, 16]}
    et = {"max_depth": 2, "max_features": 0.3, "min_samples_leaf": 5}
    fixed = {"nn_fm": {"1980-01": nn, "1981-01": nn}, "et": {"1980-01": et, "1981-01": et}}
    out = statistic(zeros, PanelMacro(panel), decisions, fixed, workers=1)
    assert set(out) == {"P4", "P5"} and all(np.isfinite(v) for v in out.values())
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_g3.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.g3'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/g3.py` (create)

```python
"""G3: is the macro contribution larger than a world where macro cannot help? (design §8, PREREG 18)

Statistic: CER(P4) - CER(P2) and CER(P5) - CER(P2) on OOS-A decisions, holding the 10-year zero
against cash y(1)/12 at 2 bp, with P4/P5 hyperparameters fixed to their OOS-A choices and 5 NN
seeds. p = (1 + #{simulated >= real}) / 201.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from . import evaluate as ev
from .backtest import REAL_TIME, build_tasks, run_forecasts, signal_weights, strategy_returns
from .data.fredmd import PanelMacro
from .features import YIELD_MONTHS, MacroCleaner
from .models import ladder
from .returns import excess_simple, holding_log_return, rx12
from .stages import COST_BP, as_frame, window
from .study import FINAL_VINTAGE, OOS_A, TRAIN_START, Study
from .synthetic import fit_spanning_null, simulate

WORLDS = 200
NN_SEEDS = 5
SEED = 3000
MONTHS = tuple(sorted({m for n in range(1, 11) for m in (12 * n, 12 * n - 1)} - {11}))
MODELS = ("ols_p", "nn_fm", "et")


def statistic(
    zeros: pd.DataFrame, macro, decisions: pd.PeriodIndex, fixed: Mapping, workers: int
) -> dict[str, float]:
    cash = (zeros[12] / 12.0).shift(1)
    excess = excess_simple(holding_log_return(zeros, 120), cash)
    tasks = build_tasks(
        zeros[list(YIELD_MONTHS)],
        as_frame(rx12(zeros, 10)),
        macro,
        refit_years=range(decisions[0].year, decisions[-1].year + 1),
        window=(decisions[0], decisions[-1]),
        horizon=12,
        rules=REAL_TIME,
    )
    specs = ladder(NN_SEEDS)
    fc = run_forecasts(tasks, [specs[m] for m in MODELS], workers=workers, fixed=fixed)
    cer = {
        m: ev.cer(strategy_returns(signal_weights(fc.predictions[m][0], decisions), excess, COST_BP).dropna())
        for m in MODELS
    }
    return {"P4": cer["nn_fm"] - cer["ols_p"], "P5": cer["et"] - cer["ols_p"]}


def run_g3(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    decisions = window(*OOS_A)
    months = pd.period_range(TRAIN_START, OOS_A[1] + 1, freq="M")
    fixed = {m: prior["oos_a"]["params"][m] for m in ("nn_fm", "et")}
    zeros = study.zeros[list(MONTHS)].reindex(months)
    real = statistic(zeros, study.realtime_macro(), decisions, fixed, workers)
    final = study.vintage(FINAL_VINTAGE).transformed.reindex(months).to_numpy(dtype=float)
    cleaner = MacroCleaner().fit(final)
    columns = study.vintage(FINAL_VINTAGE).transformed.columns[cleaner.keep_]
    panel = pd.DataFrame(cleaner.transform(final), index=months, columns=columns)
    null = fit_spanning_null(zeros, panel)
    simulated = []
    for b in range(WORLDS):
        sim_zeros, sim_macro = simulate(null, SEED + b)
        simulated.append(statistic(sim_zeros, PanelMacro(sim_macro, lag=2), decisions, fixed, workers))
    p = {k: (1 + sum(s[k] >= real[k] for s in simulated)) / (WORLDS + 1) for k in ("P4", "P5")}
    return {
        "real": real,
        "p": p,
        "worlds": WORLDS,
        "nn_seeds": NN_SEEDS,
        "factor_max_eigenvalue": null.max_eigenvalue,
        "simulated": simulated,
    }
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_g3.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Run G3 (about 20–40 minutes on 18 workers)**

```bash
cd $WT && $BT run g3 && $PY -c "import json; g=json.load(open('bond_timing_lab/results/g3.json')); print(g['real'], g['p'], round(g['factor_max_eigenvalue'], 4))"
```

Expected: `g3.json` with two p-values in (0, 1]; a factor VAR eigenvalue below 1 (an explosive estimate is a finding to report, not to fix silently).

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Run the G3 spanning-null check of the macro contribution"
```

---

### Task 18: OOS-B (once) and the verdict

**Files:**
- Create: `bond_timing_lab/src/bond_timing/oos_b.py`
- Test: `bond_timing_lab/tests/test_oos_b.py`
- Produce (committed): `bond_timing_lab/results/oos_b.json`, `bond_timing_lab/results/oos_b.lock`

**Interfaces:**
- Consumes: `stages.*`; `evaluate.Evidence`, `verdict`; `results/dev.json`, `oos_a.json`, `g3.json`.
- Produces: `oos_b.build_evidence(oos_a, g3, oos_b_diffs) -> dict[str, Evidence]`, `oos_b.run_oos_b(study, workers, prior) -> dict` with keys `window`, `p1`, `summary`, `diffs`, `evidence`, `verdict`, `params`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_oos_b.py` (create)

```python
from bond_timing import evaluate as ev
from bond_timing.oos_b import build_evidence

NAMES = ["P1", "P2", "P3", "P4", "P5"]


def inputs():
    oos_a = {
        "instruments": {
            "tlt": {
                "tests": {
                    "vs_hold": {k: {"p_holm": 0.01 if k == "P4" else 0.5} for k in NAMES},
                    "vs_p1": {k: {"p_holm": 0.02} for k in ("P4", "P5")},
                },
                "robust": {
                    k: {"vs_hold_4bp": 0.01, "vs_hold_delay": 0.01, "vs_p1_4bp": 0.01, "vs_p1_delay": 0.01}
                    for k in NAMES
                },
            }
        }
    }
    g3 = {"p": {"P4": 0.01, "P5": 0.5}}
    oos_b = {k: {"vs_hold": 0.001, "vs_p1": 0.001} for k in NAMES}
    return oos_a, g3, oos_b


def test_build_evidence_feeds_the_verdict():
    oos_a, g3, oos_b = inputs()
    evidence = build_evidence(oos_a, g3, oos_b)
    assert evidence["P4"].g3_p == 0.01 and evidence["P1"].p_vs_p1 is None
    assert ev.verdict(evidence) == "ml_signal_usable"
    oos_b["P4"]["vs_p1"] = -0.001
    assert ev.verdict(build_evidence(oos_a, g3, oos_b)) == "no_usable_signal"


def test_a_delay_loss_breaks_robustness():
    oos_a, g3, oos_b = inputs()
    oos_a["instruments"]["tlt"]["robust"]["P4"]["vs_hold_delay"] = -0.001
    assert not build_evidence(oos_a, g3, oos_b)["P4"].robust_vs_hold
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_oos_b.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.oos_b'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/oos_b.py` (create)

```python
"""OOS-B: decisions from 2019-01, run once after OOS-A and G3, and the verdict (design §3.5-3.6)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict

from . import evaluate as ev
from .backtest import strategy_returns
from .stages import COST_BP, PRIMARY, as_frame, forecast, primary_names, strategy_weights
from .stages import summary, window
from .study import OOS_B_START, Study


def build_evidence(oos_a: dict, g3: dict, oos_b: Mapping[str, Mapping[str, float]]) -> dict[str, ev.Evidence]:
    tlt = oos_a["instruments"]["tlt"]
    out = {}
    for k in ("P1", "P2", "P3", "P4", "P5"):
        robust = tlt["robust"][k]
        common = {
            "p_vs_hold": tlt["tests"]["vs_hold"][k]["p_holm"],
            "robust_vs_hold": robust["vs_hold_4bp"] > 0 and robust["vs_hold_delay"] > 0,
            "oos_b_vs_hold": oos_b[k]["vs_hold"],
        }
        if k in ("P4", "P5"):
            out[k] = ev.Evidence(
                **common,
                p_vs_p1=tlt["tests"]["vs_p1"][k]["p_holm"],
                robust_vs_p1=robust["vs_p1_4bp"] > 0 and robust["vs_p1_delay"] > 0,
                oos_b_vs_p1=oos_b[k]["vs_p1"],
                g3_p=g3["p"][k],
            )
        else:
            out[k] = ev.Evidence(**common)
    return out


def run_oos_b(study: Study, workers: int, prior: Mapping[str, dict]) -> dict:
    p1 = prior["dev"]["p1"]
    decisions = window(OOS_B_START, study.last_decision())
    fc = forecast(
        study, as_frame(study.outcomes.rx12[10]), list(PRIMARY.values()), decisions=decisions,
        horizon=12, macro=study.realtime_macro(), workers=workers,
    )
    cp = None
    if p1 == "cp":
        cp = forecast(
            study, as_frame(study.outcomes.rxbar), ["cp"], decisions=decisions, horizon=12,
            macro=None, workers=workers,
        )
    weights = strategy_weights(study, study.outcomes, decisions, fc, cp, "tlt")
    returns = {
        name: strategy_returns(w, study.outcomes.excess["tlt"], COST_BP) for name, w in weights.items()
    }
    cer = {name: ev.cer(r.dropna()) for name, r in returns.items()}
    diffs = {
        k: {"vs_hold": cer[v] - cer["hold"], "vs_p1": cer[v] - cer[p1]}
        for k, v in primary_names(p1).items()
    }
    evidence = build_evidence(prior["oos_a"], prior["g3"], diffs)
    return {
        "window": [str(decisions[0]), str(decisions[-1])],
        "p1": p1,
        "summary": {name: summary(returns[name], weights[name]) for name in weights},
        "diffs": diffs,
        "evidence": {k: asdict(e) for k, e in evidence.items()},
        "verdict": ev.verdict(evidence),
        "params": fc.params,
    }
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_oos_b.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Run OOS-B once**

```bash
cd $WT && $BT run oos-b && $PY -c "import json; r=json.load(open('bond_timing_lab/results/oos_b.json')); print(r['window'], r['verdict']); print(r['diffs'])" && cat bond_timing_lab/results/oos_b.lock
```

Expected: the verdict of record. A second `run oos-b` without `--rerun-reason` must now fail with `already ran`.

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format bond_timing_lab && git add bond_timing_lab && git commit -m "Run OOS-B once and record the verdict"
```

---

### Task 19: Report, README and the workspace checks

**Files:**
- Create: `bond_timing_lab/src/bond_timing/report.py`, `bond_timing_lab/README.md`, `bond_timing_lab/results/summary.md`
- Test: `bond_timing_lab/tests/test_report.py`

**Interfaces:**
- Consumes: every `results/*.json`.
- Produces: `report.render(results: Path) -> str`.

- [ ] **Step 1: Write the failing test**

File: `bond_timing_lab/tests/test_report.py` (create)

```python
import json

from bond_timing.report import render


def test_render_skips_missing_stages_and_shows_the_verdict(tmp_path):
    assert render(tmp_path).startswith("# 結果の表")
    (tmp_path / "g0.json").write_text(
        json.dumps({"etf": {"tlt": {"months": 290, "corr": 0.97, "pass": True}}, "pass": True})
    )
    (tmp_path / "oos_b.json").write_text(
        json.dumps({"window": ["2019-01", "2026-08"], "verdict": "no_usable_signal", "diffs": {"P1": {"vs_hold": -0.01, "vs_p1": 0.0}}})
    )
    text = render(tmp_path)
    assert "## G0" in text and "0.9700" in text
    assert "no_usable_signal" in text and "-1.00%" in text
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_report.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'bond_timing.report'`.

- [ ] **Step 3: Write the module**

File: `bond_timing_lab/src/bond_timing/report.py` (create)

```python
"""Markdown tables from the results JSON; README's result tables are copied from summary.md."""

from __future__ import annotations

import json
from pathlib import Path

LABELS = {
    "P1": "P1 単純ルール",
    "P2": "P2 主成分3つの OLS",
    "P3": "P3 主成分＋マクロ8つの OLS",
    "P4": "P4 NN（フォワード＋マクロ）",
    "P5": "P5 Extra Trees（フォワード＋マクロ）",
}


def _load(results: Path, name: str) -> dict | None:
    path = results / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _pct(x: float) -> str:
    return f"{100 * x:.2f}%"


def _g0(g0: dict) -> list[str]:
    lines = ["## G0 データ", "", "| 型 | 月数 | 合成と ETF の相関 | 合格 |", "|---|---|---|---|"]
    for name, row in g0["etf"].items():
        lines.append(f"| {name} | {row['months']} | {row['corr']:.4f} | {'○' if row['pass'] else '×'} |")
    return [*lines, ""]


def _dev(dev: dict) -> list[str]:
    lines = [f"## 開発期間（P1 = {dev['p1']}）", "", "| ルール | CER | シャープ | 切り替え |", "|---|---|---|---|"]
    for name, row in dev["instruments"]["tlt"]["rules"].items():
        lines.append(f"| {name} | {_pct(row['cer'])} | {row['sharpe']:.2f} | {row['switches']} |")
    return [*lines, ""]


def _g1(g1: dict) -> list[str]:
    lines = ["## G1 合成データ（20回中、有意になった回数）", "", "| 戦略 | W0 | W2 |", "|---|---|---|"]
    for name in g1["counts"]["W0"]:
        lines.append(f"| {name} | {g1['counts']['W0'][name]} | {g1['counts']['W2'][name]} |")
    return [*lines, "", f"合格：{'○' if g1['pass'] else '×'}（W2 の k = {g1['k']:.5f}）", ""]


def _oos_a(oos_a: dict) -> list[str]:
    tlt = oos_a["instruments"]["tlt"]
    names = {"P1": oos_a["p1"], "P2": "ols_p", "P3": "ols_pm", "P4": "nn_fm", "P5": "et"}
    hold = tlt["summary"]["hold"]
    lines = [
        "## 本番 A（判断 2000-01〜2018-12、TLT 型、費用 2bp）",
        "",
        "| 戦略 | CER | シャープ | 保有の割合 | L0 との差 | p（Holm） | P1 との差 | p（Holm） |",
        "|---|---|---|---|---|---|---|---|",
        f"| L0 ずっと保有 | {_pct(hold['cer'])} | {hold['sharpe']:.2f} | 100% | | | | |",
    ]
    for k, model in names.items():
        row, vs = tlt["summary"][model], tlt["tests"]["vs_hold"][k]
        p1 = tlt["tests"]["vs_p1"].get(k)
        tail = f"{_pct(p1['delta_cer'])} | {p1['p_holm']:.3f}" if p1 else " | "
        lines.append(
            f"| {LABELS[k]} | {_pct(row['cer'])} | {row['sharpe']:.2f} | {_pct(row['hold_share'])} "
            f"| {_pct(vs['delta_cer'])} | {vs['p_holm']:.3f} | {tail} |"
        )
    lines += ["", "| 戦略 | L0 との差（4bp） | L0 との差（5営業日遅れ） | P1 との差（4bp） | P1 との差（遅れ） |", "|---|---|---|---|---|"]
    for k, row in tlt["robust"].items():
        lines.append(
            f"| {k} | {_pct(row['vs_hold_4bp'])} | {_pct(row['vs_hold_delay'])} "
            f"| {_pct(row['vs_p1_4bp'])} | {_pct(row['vs_p1_delay'])} |"
        )
    r2 = oos_a["r2_oos"]["rx12_10"]
    lines += ["", "R²oos（10年ゼロの rx12、過去平均に対して）：" + "、".join(f"{m} {_pct(v)}" for m, v in r2.items()), ""]
    return lines


def _decompose(decompose: dict) -> list[str]:
    settings = [name for name in decompose if name != "meta"]
    models = list(decompose[settings[0]])
    lines = ["## 見かけの予測力の分解（満期平均の R²oos）", "", "| 設定 | " + " | ".join(models) + " |", "|---" * (len(models) + 1) + "|"]
    for name in settings:
        lines.append(f"| {name} | " + " | ".join(_pct(decompose[name][m]["avg"]) for m in models) + " |")
    return [*lines, ""]


def _g3(g3: dict) -> list[str]:
    return [
        "## G3（マクロが効かない世界との比較）",
        "",
        f"実データ：P4−P2 {_pct(g3['real']['P4'])}、P5−P2 {_pct(g3['real']['P5'])}。"
        f"p 値：P4 {g3['p']['P4']:.3f}、P5 {g3['p']['P5']:.3f}（{g3['worlds']}回）。",
        "",
    ]


def _oos_b(oos_b: dict) -> list[str]:
    lines = [
        f"## 本番 B（判断 {oos_b['window'][0]}〜{oos_b['window'][1]}、1回だけ）",
        "",
        "| 戦略 | L0 との CER 差 | P1 との CER 差 |",
        "|---|---|---|",
    ]
    for k, row in oos_b["diffs"].items():
        lines.append(f"| {k} | {_pct(row['vs_hold'])} | {_pct(row['vs_p1'])} |")
    return [*lines, "", f"判定：`{oos_b['verdict']}`", ""]


def render(results: Path) -> str:
    lines = ["# 結果の表（`bond-timing report` が生成）", ""]
    for name, section in (
        ("g0", _g0), ("dev", _dev), ("g1", _g1), ("oos_a", _oos_a),
        ("decompose", _decompose), ("g3", _g3), ("oos_b", _oos_b),
    ):
        data = _load(results, name)
        if data:
            lines += section(data)
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests/test_report.py -q`
Expected: `1 passed`.

- [ ] **Step 5: Render the summary and write the README**

```bash
cd $WT && $BT report && sed -n '1,200p' bond_timing_lab/results/summary.md
```

File: `bond_timing_lab/README.md` (create), in Japanese, with these sections in this order and the tables copied from `results/summary.md`:

1. タイトルと一行の結論（`oos_b.json` の判定をそのまま書く）。
2. 何を調べたか：Bianchi–Büchner–Tamoni（2021）と訂正論文、問い（TLT/IEF を月末に持つか現金かのシグナルが、時点の規則と費用のもとで、ずっと保有と単純なルールに勝つか）。
3. データと期間：GSW・DTB3・FRED-MD ビンテージ・Liu–Wu・ETF、開発／本番 A／本番 B の月、raw の場所 `/home/kazumasa/projects/_data/bond_timing_lab/raw/`。
4. 手順：時点の規則 R1–R5、階段 L0–L3、主な5本と検定（Holm）、G0–G3、PREREG の commit（`meta.prereg_commit` の値）。
5. 結果：G0、P1、G1、本番 A（主の表と頑健性）、G3、本番 B と判定。
6. 見かけの予測力の分解（V0–V3）：表と、どの規則で R²oos がどれだけ落ちたか。
7. 限界：合成の TLT 型と実際の TLT の差、2000〜2018年の債券の上昇相場、本番 B の検出力、訂正論文の中身が未確認であること、FRED-MD の公開日を仮定（ビンテージ t−1）したこと。
8. 再現手順：`$BT snapshot`、`$BT run <stage>` の順番、所要時間の目安、テストのコマンド。

- [ ] **Step 6: Run every check**

```bash
cd $WT && $PY -m pytest -c bond_timing_lab/pyproject.toml bond_timing_lab/tests -q
cd $WT && $PY -m pytest bond_timing_lab/tests -q
cd $WT && $PY -m pytest --collect-only -q 2>&1 | tail -3
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check bond_timing_lab && /home/kazumasa/projects/.venv/bin/ruff format --check bond_timing_lab
```

Expected: all bond_timing tests pass with both the member config and the root config (root `conftest.py` loaded); the workspace collection ends without errors; ruff clean.

- [ ] **Step 7: Commit**

```bash
cd $WT && git add bond_timing_lab && git commit -m "Write up the bond-timing study with its result tables"
```

Do not merge or push. Report the branch, the verdict, the key numbers and the open items to the user.
