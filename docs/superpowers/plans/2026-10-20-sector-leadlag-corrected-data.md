# Sector Lead-Lag Corrected-Data Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rerun every stage of the sector lead-lag study (G0's choice of pairing through the diagnostics) on the record's snapshot after rule-based corrections of the yfinance errors, and report the result beside the record without changing the verdict of record (`usable`).

**Architecture:** A new pure module `corrections.py` applies the rules C2, C1, C4, C5, C6, C3 and C7 to the panels that `load_study` builds and lists every change. `load_study(corrected=True)` returns a `Study` whose panels carry the corrected opens and dividends and a jump mask (`Panel.breaks`), whose signal side is rebuilt from the corrected closes and dividends on the days every listed ETF has a row, and whose US returns hide jumps. The stage modules are unchanged: the CLI runs them with `--data corrected` into `results/corrected/` under the record's gates plus three more (the same snapshot, PREREG §5 committed after the record's main B, a `corrections.json` equal to what the rules give), and `report --data corrected` puts the record beside the corrected results.

**Tech Stack:** Python 3.12, numpy 2.4, pandas 3.0, click, pytest 9, ruff. No new dependency.

**Spec:** `/home/kazumasa/projects/docs/superpowers/specs/2026-10-20-sector-leadlag-corrected-data-design.md` (approved section by section on 2026-10-20; C4 was revised with the user's approval while this plan was written, after the rules were applied to the snapshot to see what they change and before any stage ran on corrected data — the spec's §3 notes and §11). The record's spec and plan: `/home/kazumasa/projects/docs/superpowers/specs/2026-10-19-sector-leadlag-design.md`, `/home/kazumasa/projects/docs/superpowers/plans/2026-10-19-sector-leadlag.md`.

## Global Constraints

- Worktree `WT=/home/kazumasa/worktrees/sector-leadlag`. It now sits on the merged branch `claude/sector-leadlag-lab`, which stays. Task 1 cuts the new branch `claude/sector-leadlag-corrected` from `main` after this plan is committed there. Merge and push only with the user's approval (spec §10).
- The plan's git-ignored workspace: `WS=$WT/.superpowers/sdd/2026-10-20-sector-leadlag-corrected-data`. The record plan's workspace `$WT/.superpowers/sdd/2026-10-19-sector-leadlag/` stays as it is.
- Never run `sector-leadlag snapshot` or anything else that fetches. The corrected data must come from the record's snapshot (`inputs_digest` `25d13c1187bb5226556df83fc6b071569513467e5e452b648240eaf07934b49f`, 520 inputs; spec §4) in `/home/kazumasa/projects/_data/sector_leadlag_lab/raw/`, which is only read.
- Never change the record's files: `sector_leadlag_lab/results/*.json`, `results/main_b.lock`, `results/summary.md`, and PREREG.md §1–§4 (spec §1, §5). Corrected results go only to `sector_leadlag_lab/results/corrected/`.
- The stage modules stay as they are: `g0.py`, `g1.py`, `main.py`, `diagnostics.py`, `stages.py`, `signal.py`, `timing.py`, `strategy.py`, `evaluate.py`, `synthetic.py`, `pit.py`, `data/*` (spec §7).
- Without corrections every computation is the record's: `Panel.breaks` defaults to `None`, the new `Study` fields default to the record's behaviour, `render` writes the committed `results/summary.md` unchanged, and Task 5 compares 23 frames of the real record study before and after the change.
- Fixed values (spec §3): a jump is a close over twice, or under half, of the previous row's close (`JUMP = 2.0`); C6 looks at the recorded day and the ETF's 2 rows before it (`LOOKBACK = 2`); the panels start 2009-06-01 (`PANEL_START`); the rules run in the order C2, C1, C4, C5, C6, C3, C7.
- Python command (shared venv; `PYTHONPATH` makes the worktree code win; single-thread BLAS): `PY="env PYTHONPATH=$WT/sector_leadlag_lab/src:$WT/macrokit/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python -P"`. CLI: `SLL="$PY -m sector_leadlag.cli"`. Never run `uv sync` or `uv run` in the worktree. Nothing here changes a dependency, so the lock file is not touched; never write its name (or `.env`) as a shell argument, because the permission rules reject the whole command.
- Tests: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q` (`81 passed, 1 skipped` before Task 1). Tests never touch the network.
- Lint, always from `$WT`: `cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab`. Running ruff from inside the lab with `--config` treats `sector_leadlag` as first-party and rewrites the imports of every test file. Line length 100; B905: every `zip()` needs `strict=`; RUF043: a regex with metacharacters in `match=` is a raw string.
- Commit messages: English, imperative, no `feat:` prefix, ending with the executing session's attribution lines. Stage explicit paths only.
- `PREREG.md`, `README.md` and the knowledge note are Japanese; code, identifiers and commit messages are English.
- Stage order (spec §4), enforced by the CLI: `corrections` → commit PREREG §5 with `results/corrected/corrections.json` → `run g0 --data corrected` → `run g1 --data corrected` → write both into PREREG §5.6 and commit → `run main-a --data corrected` → commit `results/corrected/main_a.json` → `run main-b --data corrected` (once) → `run diagnostics --data corrected` → `report --data corrected`.

## Decisions this plan makes (the spec leaves them open)

PREREG §5 copies the ones that decide a value or a gate (D1, D4–D11) in Japanese.

- **D1 Where the rules apply.** On the panels `load_study` builds: each market's trading days from 2009-06-01, one column per series, a missing value where the series has no row. "The previous close" is the previous trading day's close (`close.shift(1)`); when the series had no row that day, a return from the previous close stays missing, as in the record. C1's "previous row" skips days without a row (`close.ffill().shift(1)`). C4's "previous dividend" is the series' latest positive dividend before d in the panel. A recorded split is a positive value in `splits`. "The stocks' median C2O with dividends" is the daily median of the stocks' C2O after C2 and C1 and before C4 and C5 (`market_move`).
- **D2 The jump mask.** `Panel.breaks` is a boolean frame like `close`, `None` by default. Where it is True, the returns from the previous close (C2O, C2C, price C2C and the new `opening_gap`) are missing; O2C and the price levels are unchanged. `None` gives the record's returns exactly.
- **D3 The corrected study.** `Study` gains `signal_jp` (the C7 frame on the signal days; `etf_c2c()` returns it when it is set), `us_breaks` (masks `us_returns()`) and `corrections` (the change records). `with_corrections(study, us_close, us_splits)` applies `corrections.correct` to a record study; `load_study(corrected=True)` builds the record study first and passes it the US closes and splits on the US days.
- **D4 C5's ratio.** "Divide D by the jump's size" multiplies D by close ÷ previous row's close of the series' latest jump before d, when that jump was down (1629.T: 1,385 × 50.70/25,670 = 2.7356). D becomes 0 when the latest jump was up, when there is none, or when the result is still above the previous close.
- **D5 C6's ties and gaps.** The candidates are the recorded day and the ETF's 2 previous rows (days on which that ETF has a close). A day's score is the mean, over the ETFs with trades and no jump that day, of the opening gap (open ÷ previous close − 1) less the stocks' median C2O. The lowest score wins; equal scores go to the earliest day; when no candidate has a score the dividend stays. A moved dividend is added to any dividend already on the target day.
- **D6 C3's carry.** The signal days are the Japanese trading days on which no listed ETF (first row to last row) lacks a row. The signal side is (close + dividend) ÷ previous signal day's close − 1 on those days; a dividend recorded on a dropped day is added to the next signal day, and a jump on a dropped day hides the next signal day's return. Days without trades keep their value (the record's adjusted-close C2C does the same); a jump day is missing.
- **D7 The known-error check** (spec §3 leaves its content to this plan). Twelve entries, each a rule, a kind (etf, stock or us), a series and a date where they apply, and the least number of changes: C1 1629.T on 2015-01-05, 2026-03-30 and 2026-04-01 (1 each); C5 1629.T 2015-07-15 (1); C3 ETFs on 2025-10-24 (16); C6 ETFs (238 = 14 years × 17 ETFs); C2 ETFs (53); C5 8303.T (12); C4 9861.T 2013-08-28, 5401.T 2025-09-29 and 8766.T 2026-09-29 (1 each); C1 8227.T 2026-02-18 (1).
- **D8 The change records.** `{rule, kind, series, date, field, before, after}`; `series` is the ticker (`1617.T`…`1633.T`, `7203.T`, `XLK`); `field` is `open` (C2), `returns` (C1, with the close ratio as `before`), `dividends` (C4, C5), `dividend_date` (C6, dates as strings) or `row` (C3). They are sorted by rule in the order C2, C1, C4, C5, C6, C3, then ETFs, stocks and US series, then column by column and day by day.
- **D9 The corrections gate.** `sector-leadlag corrections` writes `results/corrected/corrections.json` (`counts`, `missing_known`, `changes`) and exits non-zero naming every known error that no rule changed. Every corrected stage requires that file with an empty `missing_known` and a `changes` list equal, after a JSON round trip, to what the rules give now; its SHA-256 goes into the stage result's `meta.corrections_sha256`.
- **D10 Finding PREREG §5.** The PREREG.md of the latest PREREG commit (`git show <commit>:./PREREG.md`) must have a line that starts with `## 5.`, and that commit's committer date must be later than that of the record's `results/main_b.json` commit. A §5 that is written but not committed does not count.
- **D11 CLI.** `run STAGE --data corrected` and `report --data corrected` (default `record`), and the new `corrections` command; results under `results/corrected/` with the record's names and its own `main_b.lock`. A corrected result's meta adds `data: corrected`, `prereg_has_section_5`, `record_main_b_commit`, `record_main_b_committed_at` and `corrections_sha256`; its `main_a_commit` is that of `results/corrected/main_a.json`. The gates run in this order: the same snapshot, §5, the record's stage gates on `results/corrected/`, the main-B target, loading the corrected study, the corrections gate, the main-B lock, the stage. The study loads before the lock is taken, so a failed corrections gate leaves no lock.
- **D12 `sort=True`.** The column concatenations in `build_panel` and `load_study` pass `sort=True`. On the real snapshot pandas 3 sorts the union of the date indexes by default but warns (`Pandas4Warning`) that the default will become `sort=False`; `sort=True` keeps today's result and silences the warning. Every frame is reindexed to the trading days afterwards, so the values stay the record's (Task 5 compares them).
- **D13 The corrected summary.** `results/corrected/summary.md`: the reading of PREREG §5 (the label and one line); the corrections by rule and kind with the known-error result; a table of the record beside the corrected data (pairing; G0's AR, ETF coefficient and pass per pairing; G1; H1's coefficients and ratio interval; H2's means and p at 0, 2 and 5 bp; robustness; main B's coefficients and means; the ETF long-short in B1 and B2; H3; the session change before and after; the verdict); the decomposition as record／corrected per cell; then the corrected run's own sections. A missing value shows "—".

## Review Focus

- A stale or failed `corrections.json`, or stored inputs other than the record's snapshot: every corrected stage refuses and says why (Task 7 tests `test_corrected_stages_need_the_corrections_that_the_rules_make` and `test_corrected_data_must_come_from_the_records_snapshot`).
- A corrected run must neither write the record's files nor load the record's data: it writes only under `results/corrected/` and loads the corrected study (Task 7 test `test_a_corrected_run_writes_only_under_results_corrected`).
- The record's path must not change: a panel without a jump mask and a study without corrections give the record's returns, and the record's summary renders as committed (Task 1 test `test_a_jump_hides_the_returns_from_the_previous_close_only`, Task 5 test `test_the_corrected_study_applies_the_rules` and the 23-frame comparison of the real record study, Task 6 Step 5).
- A dividend or a jump on a day dropped from the signal rows (C3) is not lost: it moves to the next signal row (Task 2 test `test_a_dividend_or_a_jump_on_a_dropped_day_goes_to_the_next_row`).
- A split-day dividend on a day without trades, or of a series without an earlier dividend, stays as it is (Task 3 test `test_a_split_day_dividend_stays_without_trades_or_an_earlier_dividend`).

## File Structure

| Path (under `sector_leadlag_lab/`) | Change |
|---|---|
| `src/sector_leadlag/baskets.py` | `Panel.breaks`; the returns from the previous close look at it; `opening_gap` |
| `src/sector_leadlag/corrections.py` (new) | the rules C1–C7 as pure functions, `correct`, `KNOWN`, `missing_known`, `counts` |
| `src/sector_leadlag/study.py` | `Study.signal_jp`, `us_breaks`, `corrections`; `with_corrections`; `load_study(corrected=)` |
| `src/sector_leadlag/report.py` | `render_corrected` and `reading`; `render` unchanged in output |
| `src/sector_leadlag/cli.py` | `corrections`; `run --data`; `report --data`; the three gates; the corrected meta |
| `tests/test_baskets.py`, `tests/test_corrections.py` (new), `tests/test_study.py`, `tests/test_main.py`, `tests/test_report.py`, `tests/test_cli.py` | the tests of each |
| `PREREG.md` (§5), `README.md`, `results/corrected/` | the pre-registration, the write-up and the corrected results |

Outside the lab: `docs/knowledge/2026-10-19-yfinance-japan-data-errors.md` and its line in `docs/knowledge/README.md` (Task 11).

---
### Task 1: The branch, the jump mask and the record before any change

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/baskets.py`
- Test: `sector_leadlag_lab/tests/test_baskets.py`
- Create (git-ignored): `$WS/record_check.py`, `$WS/record_before.pkl`

**Interfaces:**
- Consumes: `baskets.Panel`, `traded`, `open_to_close`, `close_to_open`, `close_to_close`, `price_close_to_close` (existing); the `make_panel(open_, close, *, volume=None, dividends=None, splits=None, adj_close=None, sector=None)` fixture of `tests/conftest.py` (existing).
- Produces: `Panel.breaks: pd.DataFrame | None = None` (kept by `Panel.window`); `opening_gap(panel: Panel) -> pd.DataFrame` (open ÷ previous close − 1, without the dividend); `close_to_open`, `close_to_close`, `price_close_to_close` and `opening_gap` are missing where `breaks` is True and unchanged where it is `None`.

- [ ] **Step 1: Cut the branch**

```bash
cd $WT && git status --short && git switch -c claude/sector-leadlag-corrected main && git log --oneline -1
```

Expected: no status lines; `Switched to a new branch 'claude/sector-leadlag-corrected'`; the last commit is the one that added this plan on main.

- [ ] **Step 2: Write the record check**

It dumps 23 frames of the real record study (the US returns, the signal's Japanese side, s(d), and every field and return of both panels) and compares two dumps. Run `mkdir -p $WS` first.

File: `$WS/record_check.py` (create)

```python
"""Dump the record study's inputs and returns, or compare two dumps (Tasks 1 and 5)."""

import pickle
import sys
import warnings

warnings.simplefilter("ignore")
if sys.argv[1] == "compare":
    with open(sys.argv[2], "rb") as first, open(sys.argv[3], "rb") as second:
        a, b = pickle.load(first), pickle.load(second)
    different = sorted(set(a) ^ set(b)) + [key for key in a if key in b and not a[key].equals(b[key])]
    print(f"{len(a)} frames; different: {different}")
    sys.exit(1 if different else 0)

from sector_leadlag import baskets as bk
from sector_leadlag.study import load_study

study = load_study()
out = {"us_returns": study.us_returns(), "etf_c2c": study.etf_c2c(), "s_map": study.s_map}
for name in ("etf", "stocks"):
    panel = getattr(study, name)
    for field in ("open", "close", "adj_close", "volume", "dividends", "splits"):
        out[f"{name}.{field}"] = getattr(panel, field)
    for returns in (bk.open_to_close, bk.close_to_open, bk.close_to_close, bk.price_close_to_close):
        out[f"{name}.{returns.__name__}"] = returns(panel)
with open(sys.argv[2], "wb") as handle:
    pickle.dump(out, handle)
print(f"{len(out)} frames written")
```

- [ ] **Step 3: Dump the record study before any change**

```bash
cd $WT && $PY $WS/record_check.py dump $WS/record_before.pkl
```

Expected: `23 frames written` (under a minute; it reads the snapshot and fetches nothing).

- [ ] **Step 4: Write the failing test**

In `sector_leadlag_lab/tests/test_baskets.py`, replace:

```python
import numpy as np
```

with:

```python
from dataclasses import replace

import numpy as np
```

In `sector_leadlag_lab/tests/test_baskets.py`, replace:

```python
    open_to_close,
    price_close_to_close,
```

with:

```python
    open_to_close,
    opening_gap,
    price_close_to_close,
```

In `sector_leadlag_lab/tests/test_baskets.py`, replace:

```python
    assert np.isnan(close_to_open(panel)["a"].iloc[0])


def test_a_day_without_trades_has_no_return(make_panel):
```

with:

```python
    assert np.isnan(close_to_open(panel)["a"].iloc[0])


def test_a_jump_hides_the_returns_from_the_previous_close_only(make_panel):
    panel = make_panel(frame([100, 49, 50, 51]), frame([100, 50, 51, 52]))
    jumped = replace(panel, breaks=frame([0, 1, 0, 0]) > 0)
    for returns in (close_to_open, close_to_close, price_close_to_close, opening_gap):
        assert returns(jumped)["a"].isna().tolist() == [True, True, False, False]
        assert returns(panel)["a"].isna().tolist() == [True, False, False, False]
    pd.testing.assert_frame_equal(open_to_close(jumped), open_to_close(panel))
    assert jumped.window(DAYS[1], DAYS[2]).breaks["a"].tolist() == [True, False]


def test_a_day_without_trades_has_no_return(make_panel):
```

- [ ] **Step 5: Run it to see it fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_baskets.py -q
```

Expected: `ImportError: cannot import name 'opening_gap' from 'sector_leadlag.baskets'` and `Interrupted: 1 error during collection`.

- [ ] **Step 6: Add the mask and `opening_gap`**

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
    sector: pd.Series  # column -> sector code 1-17

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> Panel:
```

with:

```python
    sector: pd.Series  # column -> sector code 1-17
    breaks: pd.DataFrame | None = None  # corrected data: days after a jump in the close (C1)

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> Panel:
```

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
            self.sector,
        )
```

with:

```python
            self.sector,
            None if self.breaks is None else self.breaks.loc[rows],
        )
```

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
    return panel.volume.fillna(0.0) > 0


def open_to_close(panel: Panel) -> pd.DataFrame:
```

with:

```python
    return panel.volume.fillna(0.0) > 0


def _from_previous_close(panel: Panel, returns: pd.DataFrame) -> pd.DataFrame:
    """A return from the previous close: kept on days with trades and no jump (C1) before them."""
    valid = traded(panel) if panel.breaks is None else traded(panel) & ~panel.breaks
    return returns.where(valid)


def open_to_close(panel: Panel) -> pd.DataFrame:
```

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
    previous = panel.close.shift(1)
    return ((panel.open + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def close_to_close(panel: Panel) -> pd.DataFrame:
```

with:

```python
    previous = panel.close.shift(1)
    return _from_previous_close(panel, (panel.open + panel.dividends.fillna(0.0)) / previous - 1.0)


def close_to_close(panel: Panel) -> pd.DataFrame:
```

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
    previous = panel.close.shift(1)
    return ((panel.close + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def price_close_to_close(panel: Panel) -> pd.DataFrame:
```

with:

```python
    previous = panel.close.shift(1)
    return _from_previous_close(panel, (panel.close + panel.dividends.fillna(0.0)) / previous - 1.0)


def price_close_to_close(panel: Panel) -> pd.DataFrame:
```

In `sector_leadlag_lab/src/sector_leadlag/baskets.py`, replace:

```python
    """Close over the previous close, without the dividend: how a price index moves (design §9)."""
    return (panel.close / panel.close.shift(1) - 1.0).where(traded(panel))


def quoted(panel: Panel) -> tuple[pd.DataFrame, pd.DataFrame]:
```

with:

```python
    """Close over the previous close, without the dividend: how a price index moves (design §9)."""
    return _from_previous_close(panel, panel.close / panel.close.shift(1) - 1.0)


def opening_gap(panel: Panel) -> pd.DataFrame:
    """The open over the previous close, without the dividend (the corrected data's C4 and C6)."""
    return _from_previous_close(panel, panel.open / panel.close.shift(1) - 1.0)


def quoted(panel: Panel) -> tuple[pd.DataFrame, pd.DataFrame]:
```

- [ ] **Step 7: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_baskets.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `7 passed`, then `82 passed, 1 skipped`.

- [ ] **Step 8: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/baskets.py sector_leadlag_lab/tests/test_baskets.py && git commit -m "Hide the returns across a jump in the close when a panel marks it"
```

Expected: `All checks passed!`, every file already formatted, one commit.

---

### Task 2: The rules for opens, jumps and rows (C2, C1, C3) and the signal side (C7)

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/corrections.py`
- Test: `sector_leadlag_lab/tests/test_corrections.py` (create)

**Interfaces:**
- Consumes: `Panel.breaks` and `baskets.traded` (Task 1); the `make_panel` fixture.
- Produces: `JUMP = 2.0`; `Change(rule: str, column: object, day: pd.Timestamp, field: str, before, after)` (frozen); `_cells(mask: pd.DataFrame) -> list[tuple[pd.Timestamp, object]]`; `zero_opens(panel: Panel) -> tuple[Panel, list[Change]]` (C2); `close_ratio(close: pd.DataFrame) -> pd.DataFrame`; `scale_breaks(close: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame` (C1, booleans); `_jump_changes(close, breaks) -> list[Change]`; `with_breaks(panel: Panel) -> tuple[Panel, list[Change]]` (sets `breaks`); `missing_rows(close: pd.DataFrame) -> pd.DataFrame` (C3, booleans); `_onto(frame: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame`; `signal_returns(etf: Panel, days: pd.DatetimeIndex) -> pd.DataFrame` (C7; `etf.breaks` must be set).

- [ ] **Step 1: Write the failing tests**

File: `sector_leadlag_lab/tests/test_corrections.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag import baskets as bk
from sector_leadlag.corrections import (
    close_ratio,
    missing_rows,
    scale_breaks,
    signal_returns,
    with_breaks,
    zero_opens,
)

DAYS = pd.bdate_range("2026-01-05", periods=6)


def frame(*columns, names=None):
    names = names or [chr(ord("a") + i) for i in range(len(columns))]
    return pd.DataFrame(
        {
            name: np.asarray(values, dtype=float)
            for name, values in zip(names, columns, strict=True)
        },
        index=DAYS[: len(columns[0])],
    )


def test_an_open_of_zero_with_trades_becomes_missing(make_panel):
    panel = make_panel(
        frame([100, 0, 0, 101]), frame([100, 101, 101, 102]), volume=frame([5, 5, 0, 5])
    )
    fixed, changes = zero_opens(panel)
    assert fixed.open["a"].isna().tolist() == [False, True, False, False]  # day 3 had no trades
    assert bk.open_to_close(fixed)["a"].isna().tolist() == [False, True, True, False]
    assert [(c.rule, c.day, c.before, c.after) for c in changes] == [("C2", DAYS[1], 0.0, None)]


def test_a_jump_without_a_split_breaks_the_returns_across_it(make_panel):
    close = frame([100, 300, 301, 150, 140, 141], [100, 40, 41, 42, 43, 44])
    splits = frame([0, 0, 0, 0, 0, 0], [0, 2.5, 0, 0, 0, 0])
    breaks = scale_breaks(close, splits)
    assert breaks["a"].tolist() == [False, True, False, True, False, False]
    assert not breaks["b"].any()  # b's fall to 40% is a recorded split
    fixed, changes = with_breaks(make_panel(close, close, splits=splits))
    for returns in (bk.close_to_open, bk.close_to_close, bk.price_close_to_close):
        assert returns(fixed)["a"].isna().tolist() == [True, True, False, True, False, False]
    assert bk.open_to_close(fixed)["a"].notna().all()  # the levels stay as they are
    assert [(c.day, c.before) for c in changes] == [(DAYS[1], 3.0), (DAYS[3], 150 / 301)]


def test_a_jump_counts_from_the_series_previous_row():
    close = frame([100, np.nan, 300])
    assert close_ratio(close)["a"].iloc[2] == 3.0
    assert scale_breaks(close, close * 0)["a"].tolist() == [False, False, True]


def test_a_missing_row_inside_the_listed_span_drops_the_day_from_the_signal(make_panel):
    close = frame([100, 101, np.nan, 103, 104, 105], [np.nan, 50, 51, 52, 53, 54])
    gaps = missing_rows(close)
    assert gaps["a"].tolist() == [False, False, True, False, False, False]
    assert not gaps["b"].any()  # b was not listed yet on day 1
    panel, _ = with_breaks(make_panel(close, close))
    days = DAYS[~gaps.any(axis=1).to_numpy()]
    signal = signal_returns(panel, days)
    assert list(signal.index) == [DAYS[0], DAYS[1], DAYS[3], DAYS[4], DAYS[5]]
    assert signal.loc[DAYS[3], "a"] == pytest.approx(103 / 101 - 1)  # two days at once
    assert signal.loc[DAYS[3], "b"] == pytest.approx(52 / 50 - 1)


def test_a_dividend_or_a_jump_on_a_dropped_day_goes_to_the_next_row(make_panel):
    close = frame([100, 101, 50, 51, 52, 53], [100, 100, 100, 100, 100, 100])
    dividends = frame([0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 0, 0])
    panel, _ = with_breaks(make_panel(close, close, dividends=dividends))
    signal = signal_returns(panel, DAYS.delete(2))  # day 3 is out of the signal rows (C3)
    assert np.isnan(signal.loc[DAYS[3], "a"])  # a's jump on day 3 hides day 4's return
    assert signal.loc[DAYS[3], "b"] == pytest.approx(0.02)  # (100 + 2) / 100 - 1


def test_the_signal_side_adds_the_dividend_and_counts_days_without_trades(make_panel):
    close = frame([100, 98, 99, 300, 301, 302])
    panel, _ = with_breaks(
        make_panel(
            close, close, volume=frame([5, 5, 0, 5, 5, 5]), dividends=frame([0, 3, 0, 0, 0, 0])
        )
    )
    signal = signal_returns(panel, DAYS)
    assert signal["a"].iloc[1] == pytest.approx(0.01)  # (98 + 3) / 100 - 1
    assert signal["a"].iloc[2] == pytest.approx(99 / 98 - 1)  # no trades, as in the record
    assert signal["a"].isna().tolist() == [True, False, False, True, False, False]


def test_without_dividends_the_signal_side_is_the_records(make_panel):
    close = frame([100, 98, 99, 101, 100, 102])
    panel, _ = with_breaks(make_panel(close, close))
    record = close / close.shift(1) - 1
    pd.testing.assert_frame_equal(signal_returns(panel, DAYS), record, check_freq=False)
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q
```

Expected: `ModuleNotFoundError: No module named 'sector_leadlag.corrections'` and `Interrupted: 1 error during collection`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/corrections.py` (create)

```python
"""Rules that correct the yfinance errors for the rerun after the verdict (PREREG §5).

Design 2026-10-20 §3. Every rule is a pure function of the panels on their trading days, and
``correct`` applies them in the design's order (C2, C1, C4, C5, C6, C3, C7), listing each change.
``missing_known`` checks that every known error of the design's §2 was changed by its rule.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

from . import baskets as bk
from .baskets import Panel

JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close


@dataclass(frozen=True)
class Change:
    rule: str
    column: object  # the panel column: an ETF's sector code, a stock code or a US ticker
    day: pd.Timestamp
    field: str
    before: float | str | None
    after: float | str | None


def _cells(mask: pd.DataFrame) -> list[tuple[pd.Timestamp, object]]:
    """(day, column) of every True cell, column by column and day by day."""
    columns, rows = np.nonzero(mask.to_numpy(dtype=bool).T)
    return [(mask.index[r], mask.columns[c]) for c, r in zip(columns, rows, strict=True)]


def zero_opens(panel: Panel) -> tuple[Panel, list[Change]]:
    """C2: an open of 0 on a day with trades becomes missing (its O2C and C2O with it)."""
    bad = (panel.open == 0) & bk.traded(panel)
    changes = [Change("C2", column, day, "open", 0.0, None) for day, column in _cells(bad)]
    return replace(panel, open=panel.open.mask(bad)), changes


def close_ratio(close: pd.DataFrame) -> pd.DataFrame:
    """Each close over the series' previous close (across days on which it has no row)."""
    return close / close.ffill().shift(1)


def scale_breaks(close: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    """C1: a close over twice, or under half, the previous one on a day without a split."""
    ratio = close_ratio(close)
    jump = (ratio > JUMP) | (ratio < 1.0 / JUMP)
    return jump & ~(splits.fillna(0.0) > 0)


def _jump_changes(close: pd.DataFrame, breaks: pd.DataFrame) -> list[Change]:
    ratio = close_ratio(close)
    return [
        Change("C1", column, day, "returns", float(ratio.at[day, column]), None)
        for day, column in _cells(breaks)
    ]


def with_breaks(panel: Panel) -> tuple[Panel, list[Change]]:
    """C1 on a panel: the returns from the previous close across a jump become missing."""
    breaks = scale_breaks(panel.close, panel.splits)
    return replace(panel, breaks=breaks), _jump_changes(panel.close, breaks)


def missing_rows(close: pd.DataFrame) -> pd.DataFrame:
    """C3: a day inside a series' listed span (its first row to its last) without a row."""
    listed = close.ffill().notna() & close.bfill().notna()
    return listed & close.isna()


def _onto(frame: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Sums of the rows of ``frame`` on the first of ``days`` on or after each row's date."""
    position = days.searchsorted(frame.index, side="left")
    inside = position < len(days)
    sums = frame[inside].groupby(days[position[inside]]).sum()
    return sums.reindex(days, fill_value=0.0)


def signal_returns(etf: Panel, days: pd.DatetimeIndex) -> pd.DataFrame:
    """C7: the signal's Japanese side on ``days``: (close + dividend) over the previous close.

    Days without trades count, as with the adjusted close of the record; a jump (C1) makes the
    return missing. A dividend or a jump on a day left out of ``days`` (C3) goes to the next one.
    """
    close = etf.close.reindex(days)
    paid = _onto(etf.dividends.fillna(0.0), days)
    broken = _onto(etf.breaks.astype(float), days) > 0
    return ((close + paid) / close.shift(1) - 1.0).mask(broken)
```

- [ ] **Step 4: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `7 passed`, then `89 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/corrections.py sector_leadlag_lab/tests/test_corrections.py && git commit -m "Add the corrected-data rules for zero opens, jumps, missing rows and the signal side"
```

Expected: ruff clean, one commit.

---

### Task 3: The dividend rules (C4, C5, C6)

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/corrections.py`
- Test: `sector_leadlag_lab/tests/test_corrections.py`

**Interfaces:**
- Consumes: `Change`, `_cells`, `close_ratio`, `JUMP`, `with_breaks` (Task 2); `baskets.close_to_open`, `baskets.opening_gap` (Task 1).
- Produces: `LOOKBACK = 2`; `market_move(stocks: Panel) -> pd.Series` (the stocks' daily median C2O with dividends); `split_day_dividends(panel: Panel, market: pd.Series) -> tuple[Panel, list[Change]]` (C4; needs `breaks` set); `oversized_dividends(panel: Panel) -> tuple[Panel, list[Change]]` (C5; needs `breaks` set); `late_etf_dividends(etf: Panel, market: pd.Series, lookback: int = LOOKBACK) -> tuple[Panel, list[Change]]` (C6).

- [ ] **Step 1: Write the failing tests**

In `sector_leadlag_lab/tests/test_corrections.py`, replace:

```python
import numpy as np
```

with:

```python
from dataclasses import replace

import numpy as np
```

In `sector_leadlag_lab/tests/test_corrections.py`, replace:

```python
    close_ratio,
    missing_rows,
    scale_breaks,
    signal_returns,
    with_breaks,
```

with:

```python
    close_ratio,
    late_etf_dividends,
    market_move,
    missing_rows,
    oversized_dividends,
    scale_breaks,
    signal_returns,
    split_day_dividends,
    with_breaks,
```

In `sector_leadlag_lab/tests/test_corrections.py`, replace:

```python
    pd.testing.assert_frame_equal(signal_returns(panel, DAYS), record, check_freq=False)
```

with:

```python
    pd.testing.assert_frame_equal(signal_returns(panel, DAYS), record, check_freq=False)


def _split_day(make_panel, *, dividend, opening):
    """A stock with a 1:2 split on day 4 that also goes ex a dividend that day."""
    close = frame([1000, 1000, 1000, 1000, 1000, 1000])
    return make_panel(
        frame([1000, 1000, 1000, opening, 1000, 1000]),
        close,
        dividends=frame([0, 20, 0, dividend, 0, 0]),
        splits=frame([0, 0, 0, 2, 0, 0]),
    )


def test_a_split_day_dividend_left_in_pre_split_units_is_divided(make_panel):
    market = pd.Series(0.0, index=DAYS)
    # D = 40 is twice the previous dividend, and the open fell 2% (D/(kP)), not 4% (D/P)
    fixed, changes = split_day_dividends(_split_day(make_panel, dividend=40, opening=980), market)
    assert fixed.dividends["a"].iloc[3] == 20.0
    assert [(c.rule, c.before, c.after) for c in changes] == [("C4", 40.0, 20.0)]


@pytest.mark.parametrize(
    ("dividend", "opening"),
    [(20, 980), (40, 960)],  # the history says D is right; the drop says D is right
)
def test_a_split_day_dividend_stays_unless_history_and_drop_both_say_divide(
    make_panel, dividend, opening
):
    market = pd.Series(0.0, index=DAYS)
    panel = _split_day(make_panel, dividend=dividend, opening=opening)
    fixed, changes = split_day_dividends(panel, market)
    assert fixed.dividends["a"].iloc[3] == dividend and changes == []


def test_a_split_day_dividend_stays_without_trades_or_an_earlier_dividend(make_panel):
    market = pd.Series(0.0, index=DAYS)
    panel = _split_day(make_panel, dividend=40, opening=980)
    quiet = replace(panel, volume=frame([5, 5, 5, 0, 5, 5]))  # no drop to measure
    first = replace(panel, dividends=frame([0, 0, 0, 40, 0, 0]))  # no dividend before it
    for case in (quiet, first):
        fixed, changes = split_day_dividends(case, market)
        assert fixed.dividends["a"].iloc[3] == 40.0 and changes == []


def test_the_drop_of_a_split_day_dividend_is_measured_against_the_market(make_panel):
    # every stock opened 2% lower: the 2% fall is the market, so D/P = 4% no longer fits
    market = pd.Series(-0.02, index=DAYS)
    fixed, _ = split_day_dividends(_split_day(make_panel, dividend=40, opening=960), market)
    assert fixed.dividends["a"].iloc[3] == 20.0


def test_a_dividend_above_the_close_follows_the_last_down_jump(make_panel):
    close = frame(
        [30000, 60, 60, 60, 60, 60], [100, 100, 100, 100, 100, 100], [100, 300, 300, 300, 300, 300]
    )
    dividends = frame([0, 0, 0, 1500, 0, 0], [0, 0, 0, 5e8, 0, 0], [0, 0, 0, 500, 0, 0])
    panel, _ = with_breaks(make_panel(close, close, dividends=dividends))
    fixed, changes = oversized_dividends(panel)
    assert fixed.dividends.iloc[3].tolist() == [3.0, 0.0, 0.0]  # ÷500; no jump; the jump was up
    assert [(c.column, c.before, c.after) for c in changes] == [
        ("a", 1500.0, 3.0),
        ("b", 5e8, 0.0),
        ("c", 500.0, 0.0),
    ]


def test_a_dividend_still_above_the_close_after_the_jump_becomes_zero(make_panel):
    close = frame([200, 60, 60, 60])
    panel, _ = with_breaks(make_panel(close, close, dividends=frame([0, 0, 0, 900])))
    fixed, _ = oversized_dividends(panel)
    assert fixed.dividends["a"].iloc[3] == 0.0  # 900 × 60/200 = 270 is still above 60


def _etfs(make_panel, opens):
    close = pd.DataFrame(100.0, index=DAYS, columns=[1, 2])
    open_ = pd.DataFrame(opens, index=DAYS, columns=[1, 2], dtype=float)
    dividends = pd.DataFrame(0.0, index=DAYS, columns=[1, 2])
    dividends.iloc[4] = [3.0, 2.0]  # recorded on day 5
    return make_panel(open_, close, dividends=dividends)


def test_late_etf_dividends_move_to_the_lowest_opening_day(make_panel):
    opens = [[100, 100], [100, 100], [97, 98], [100, 100], [100, 100], [100, 100]]
    market = pd.Series(0.0, index=DAYS)
    fixed, changes = late_etf_dividends(_etfs(make_panel, opens), market)
    assert fixed.dividends.iloc[2].tolist() == [3.0, 2.0]  # both move to day 3
    assert fixed.dividends.iloc[4].tolist() == [0.0, 0.0]
    assert [(c.column, c.before, c.after) for c in changes] == [
        (1, "2026-01-09", "2026-01-07"),
        (2, "2026-01-09", "2026-01-07"),
    ]


def test_an_etf_dividend_stays_when_its_own_day_opens_lowest(make_panel):
    opens = [[100, 100], [100, 100], [99, 100], [100, 100], [97, 98], [100, 100]]
    market = pd.Series(0.0, index=DAYS)
    fixed, changes = late_etf_dividends(_etfs(make_panel, opens), market)
    assert fixed.dividends.iloc[4].tolist() == [3.0, 2.0] and changes == []


def test_the_market_move_is_the_median_overnight_return_with_dividends(make_panel):
    close = frame([100, 100], [100, 100], [100, 100])
    stocks = make_panel(
        frame([100, 98], [100, 99], [100, 101]), close, dividends=frame([0, 2], [0, 0], [0, 0])
    )
    assert market_move(stocks).iloc[1] == pytest.approx(0.0)  # 0%, -1% and +1%
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q
```

Expected: `ImportError: cannot import name 'late_etf_dividends' from 'sector_leadlag.corrections'` and `Interrupted: 1 error during collection`.

- [ ] **Step 3: Add the rules**

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
from __future__ import annotations

from dataclasses import dataclass, replace
```

with:

```python
from __future__ import annotations

import math
from dataclasses import dataclass, replace
```

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close


@dataclass(frozen=True)
```

with:

```python
JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close
LOOKBACK = 2  # C6: the recorded day and the ETF's two rows before it


@dataclass(frozen=True)
```

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
    return ((close + paid) / close.shift(1) - 1.0).mask(broken)
```

with:

```python
    return ((close + paid) / close.shift(1) - 1.0).mask(broken)


def market_move(stocks: Panel) -> pd.Series:
    """The stocks' median overnight return, dividends included (the yardstick of C4 and C6)."""
    return bk.close_to_open(stocks).median(axis=1)


def split_day_dividends(panel: Panel, market: pd.Series) -> tuple[Panel, list[Change]]:
    """C4: a dividend on the day of a split of ratio k, left in pre-split units.

    D becomes D/k when D/k is closer than D to the series' previous dividend (in logs) and D/(kP)
    is closer than D/P to the day's drop: the stocks' median overnight return less the series'
    opening gap (P is the previous close). A series without an earlier dividend keeps D.
    """
    dividends = panel.dividends.copy()
    previous = panel.close.shift(1)
    drop = -bk.opening_gap(panel).sub(market, axis=0)
    events = (panel.splits.fillna(0.0) > 0) & (dividends.fillna(0.0) > 0)
    changes = []
    for day, column in _cells(events):
        k, d, p = panel.splits.at[day, column], dividends.at[day, column], previous.at[day, column]
        paid = dividends[column]
        paid = paid[(paid.index < day) & (paid > 0)]
        if paid.empty:
            continue
        last, fall = paid.iloc[-1], drop.at[day, column]
        by_history = abs(math.log(d / k / last)) < abs(math.log(d / last))
        by_drop = abs(d / (k * p) - fall) < abs(d / p - fall)  # False when either is missing
        if by_history and by_drop:
            dividends.at[day, column] = d / k
            changes.append(Change("C4", column, day, "dividends", float(d), float(d / k)))
    return replace(panel, dividends=dividends), changes


def oversized_dividends(panel: Panel) -> tuple[Panel, list[Change]]:
    """C5: a dividend above the previous close.

    When the series' latest jump (C1) before it was down, D is divided by the jump's size (the
    previous close over the close: 506 for 1629.T in 2015). D becomes 0 when there is no such
    jump, or when the result is still above the previous close.
    """
    ratio = close_ratio(panel.close).where(panel.breaks)
    dividends = panel.dividends.copy()
    previous = panel.close.shift(1)
    changes = []
    for day, column in _cells(dividends.fillna(0.0) > previous):
        d, p = dividends.at[day, column], previous.at[day, column]
        jumps = ratio[column]
        jumps = jumps[(jumps.index < day) & jumps.notna()]
        after = 0.0
        if len(jumps) and jumps.iloc[-1] < 1.0 / JUMP:
            after = d * jumps.iloc[-1]
            after = 0.0 if after > p else after
        dividends.at[day, column] = after
        changes.append(Change("C5", column, day, "dividends", float(d), float(after)))
    return replace(panel, dividends=dividends), changes


def late_etf_dividends(
    etf: Panel, market: pd.Series, lookback: int = LOOKBACK
) -> tuple[Panel, list[Change]]:
    """C6: an ETF dividend moves to the day on which the ETFs opened lowest against the stocks.

    The candidates are the recorded day and the ETF's ``lookback`` rows before it; each day scores
    the mean, over the ETFs that traded, of the opening gap less the stocks' median overnight
    return. The earliest of equal scores wins; a recorded day without any score keeps it.
    """
    score = bk.opening_gap(etf).sub(market, axis=0).mean(axis=1)
    dividends = etf.dividends.copy()
    changes = []
    for day, column in _cells(etf.dividends.fillna(0.0) > 0):
        rows = etf.close.index[etf.close[column].notna().to_numpy()]
        here = rows.get_loc(day)
        scores = score.reindex(rows[max(0, here - lookback) : here + 1])
        if scores.isna().all():
            continue
        target = scores.idxmin()
        if target != day:
            amount = dividends.at[day, column]
            dividends.at[target, column] = np.nan_to_num(dividends.at[target, column]) + amount
            dividends.at[day, column] = 0.0
            changes.append(
                Change("C6", column, day, "dividend_date", str(day.date()), str(target.date()))
            )
    return replace(etf, dividends=dividends), changes
```

- [ ] **Step 4: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `17 passed`, then `99 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/corrections.py sector_leadlag_lab/tests/test_corrections.py && git commit -m "Add the corrected-data rules for split-day, oversized and late ETF dividends"
```

Expected: ruff clean, one commit.

---

### Task 4: Every rule in the design's order, and the known-error check

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/corrections.py`
- Test: `sector_leadlag_lab/tests/test_corrections.py`

**Interfaces:**
- Consumes: every rule of Tasks 2–3; `jpx.ETF_TICKERS` (sector code k → `ETF_TICKERS[k - 1]`) and `jpx.stock_ticker(code) -> str` (existing).
- Produces: `RULES = ("C2", "C1", "C4", "C5", "C6", "C3")`; `Corrected(etf: Panel, stocks: Panel, us_breaks: pd.DataFrame, signal_days: pd.DatetimeIndex, signal: pd.DataFrame, changes: list[dict])`; `correct(etf: Panel, stocks: Panel, us_close: pd.DataFrame, us_splits: pd.DataFrame) -> Corrected` (the change records of D8); `Known(label, rule, kind, series, date, count)`; `KNOWN: tuple[Known, ...]` (the 12 entries of D7); `missing_known(changes: list[dict], known=KNOWN) -> list[dict]` (`asdict(Known)` plus `found`, for every entry with too few changes); `counts(changes: list[dict]) -> dict[str, dict[str, int]]` (every rule of `RULES`, then kind → number).

- [ ] **Step 1: Write the failing tests**

In `sector_leadlag_lab/tests/test_corrections.py`, replace:

```python
from sector_leadlag.corrections import (
    close_ratio,
    late_etf_dividends,
    market_move,
    missing_rows,
```

with:

```python
from sector_leadlag.corrections import (
    KNOWN,
    close_ratio,
    correct,
    counts,
    late_etf_dividends,
    market_move,
    missing_known,
    missing_rows,
```

In `sector_leadlag_lab/tests/test_corrections.py`, replace:

```python
    assert market_move(stocks).iloc[1] == pytest.approx(0.0)  # 0%, -1% and +1%
```

with:

```python
    assert market_move(stocks).iloc[1] == pytest.approx(0.0)  # 0%, -1% and +1%


def test_the_rules_change_nothing_in_a_world_without_errors(decayed_world):
    w = decayed_world
    us = w.us_adj
    fixed = correct(w.etf, w.stocks, us, us * 0.0)
    assert fixed.changes == [] and fixed.signal_days.equals(w.jp_days)
    pd.testing.assert_frame_equal(fixed.signal, w.etf_c2c(), check_freq=False)
    for returns in (bk.close_to_open, bk.close_to_close, bk.open_to_close):
        pd.testing.assert_frame_equal(returns(fixed.stocks), returns(w.stocks))
        pd.testing.assert_frame_equal(returns(fixed.etf), returns(w.etf))
    assert counts(fixed.changes) == {rule: {} for rule in ("C2", "C1", "C4", "C5", "C6", "C3")}


def test_known_errors_that_no_rule_changed_are_reported():
    change = {"rule": "C1", "kind": "etf", "series": "1629.T", "date": "2015-01-05"}
    missing = missing_known([change])
    assert len(missing) == len(KNOWN) - 1
    assert missing[0]["label"].startswith("1629.T: prices at 1/500")
    assert missing[0]["found"] == 0
    complete = [
        {"rule": k.rule, "kind": k.kind, "series": k.series or "x", "date": k.date or "d"}
        for k in KNOWN
        for _ in range(k.count)
    ]
    assert missing_known(complete) == []


def test_the_rules_run_in_the_designs_order(make_panel):
    etf_close = pd.DataFrame({1: [100.0, 300.0, 300.0]}, index=DAYS[:3])
    etf = make_panel(pd.DataFrame({1: [100.0, 0.0, 300.0]}, index=DAYS[:3]), etf_close)
    stocks = make_panel(frame([100, 300, 300]), frame([100, 300, 300]))
    us = pd.DataFrame({"XLK": [10.0, 10.0, 10.0]}, index=DAYS[:3])
    fixed = correct(etf, stocks, us, us * 0.0)
    assert [(c["rule"], c["kind"], c["series"]) for c in fixed.changes] == [
        ("C2", "etf", "1617.T"),
        ("C1", "etf", "1617.T"),
        ("C1", "stock", "a.T"),
    ]
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q
```

Expected: `ImportError: cannot import name 'KNOWN' from 'sector_leadlag.corrections'` and `Interrupted: 1 error during collection`.

- [ ] **Step 3: Add `correct` and the check**

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
import math
from dataclasses import dataclass, replace

import numpy as np
```

with:

```python
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace

import numpy as np
```

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
from .baskets import Panel

JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close
LOOKBACK = 2  # C6: the recorded day and the ETF's two rows before it


@dataclass(frozen=True)
```

with:

```python
from .baskets import Panel
from .data import jpx

JUMP = 2.0  # C1: a close over twice, or under half, the previous row's close
LOOKBACK = 2  # C6: the recorded day and the ETF's two rows before it
RULES = ("C2", "C1", "C4", "C5", "C6", "C3")  # C7 changes how the signal is built, not a value


@dataclass(frozen=True)
```

In `sector_leadlag_lab/src/sector_leadlag/corrections.py`, replace:

```python
    return replace(etf, dividends=dividends), changes
```

with:

```python
    return replace(etf, dividends=dividends), changes


@dataclass(frozen=True)
class Corrected:
    etf: Panel
    stocks: Panel
    us_breaks: pd.DataFrame  # US days after a jump in the close (C1)
    signal_days: pd.DatetimeIndex  # the Japanese days the signal's rows may use (C3)
    signal: pd.DataFrame  # the signal's Japanese side on those days (C7)
    changes: list[dict]


def _record(change: Change, kind: str, name: Callable[[object], str]) -> dict:
    return {
        "rule": change.rule,
        "kind": kind,
        "series": name(change.column),
        "date": str(change.day.date()),
        "field": change.field,
        "before": change.before,
        "after": change.after,
    }


def correct(
    etf: Panel, stocks: Panel, us_close: pd.DataFrame, us_splits: pd.DataFrame
) -> Corrected:
    """Every rule in the design's order. ``us_close`` and ``us_splits`` are on the US days."""
    found: list[tuple[str, Change]] = []

    def kept(kind: str, result: tuple[Panel, list[Change]]) -> Panel:
        panel, changes = result
        found.extend((kind, change) for change in changes)
        return panel

    etf = kept("etf", zero_opens(etf))
    stocks = kept("stock", zero_opens(stocks))
    etf = kept("etf", with_breaks(etf))
    stocks = kept("stock", with_breaks(stocks))
    us_breaks = scale_breaks(us_close, us_splits)
    found.extend(("us", change) for change in _jump_changes(us_close, us_breaks))
    market = market_move(stocks)
    etf = kept("etf", split_day_dividends(etf, market))
    stocks = kept("stock", split_day_dividends(stocks, market))
    etf = kept("etf", oversized_dividends(etf))
    stocks = kept("stock", oversized_dividends(stocks))
    etf = kept("etf", late_etf_dividends(etf, market))
    gaps = missing_rows(etf.close)
    found.extend(("etf", Change("C3", c, day, "row", None, None)) for day, c in _cells(gaps))
    days = etf.close.index[~gaps.any(axis=1).to_numpy()]
    names = {
        "etf": lambda k: jpx.ETF_TICKERS[int(k) - 1],
        "stock": jpx.stock_ticker,
        "us": str,
    }
    order = {rule: i for i, rule in enumerate(RULES)}
    records = [
        _record(change, kind, names[kind])
        for kind, change in sorted(found, key=lambda item: order[item[1].rule])
    ]
    return Corrected(etf, stocks, us_breaks, days, signal_returns(etf, days), records)


@dataclass(frozen=True)
class Known:
    label: str  # the row of design §2
    rule: str
    kind: str
    series: str | None  # None: any series of the kind
    date: str | None  # None: any date
    count: int  # changes needed


KNOWN = (
    Known("1629.T: the unrecorded split of 2015-01-05", "C1", "etf", "1629.T", "2015-01-05", 1),
    Known("1629.T: prices at 1/500 from 2026-03-30", "C1", "etf", "1629.T", "2026-03-30", 1),
    Known("1629.T: prices back on 2026-04-01", "C1", "etf", "1629.T", "2026-04-01", 1),
    Known(
        "1629.T: the dividend of 2015-07-15 per pre-split unit",
        "C5",
        "etf",
        "1629.T",
        "2015-07-15",
        1,
    ),
    Known("16 ETFs without a row on 2025-10-24", "C3", "etf", None, "2025-10-24", 16),
    Known("ETF dividends dated late (17 ETFs, 2013-2026)", "C6", "etf", None, None, 238),
    Known("ETF opens of 0 in 2009", "C2", "etf", None, None, 53),
    Known("8303.T: dividends of 200-240 million yen", "C5", "stock", "8303.T", None, 12),
    Known("9861.T: the split-day dividend of 2013", "C4", "stock", "9861.T", "2013-08-28", 1),
    Known("5401.T: the split-day dividend of 2025", "C4", "stock", "5401.T", "2025-09-29", 1),
    Known("8766.T: the split-day dividend of 2026", "C4", "stock", "8766.T", "2026-09-29", 1),
    Known(
        "8227.T: the 1:3 split price before its record", "C1", "stock", "8227.T", "2026-02-18", 1
    ),
)


def missing_known(changes: list[dict], known: tuple[Known, ...] = KNOWN) -> list[dict]:
    """The known errors that their rule did not change (design §3: stop and report them)."""
    out = []
    for item in known:
        found = sum(
            change["rule"] == item.rule
            and change["kind"] == item.kind
            and item.series in (None, change["series"])
            and item.date in (None, change["date"])
            for change in changes
        )
        if found < item.count:
            out.append({**asdict(item), "found": found})
    return out


def counts(changes: list[dict]) -> dict[str, dict[str, int]]:
    """How many changes each rule made, by kind of series."""
    out: dict[str, dict[str, int]] = {rule: {} for rule in RULES}
    for change in changes:
        by_kind = out[change["rule"]]
        by_kind[change["kind"]] = by_kind.get(change["kind"], 0) + 1
    return out
```

- [ ] **Step 4: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_corrections.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `20 passed`, then `102 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/corrections.py sector_leadlag_lab/tests/test_corrections.py && git commit -m "Apply the corrected-data rules in the design's order and check the known errors"
```

Expected: ruff clean, one commit.

---

### Task 5: The corrected study, and the record study unchanged

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/study.py` (rewritten whole)
- Test: `sector_leadlag_lab/tests/test_study.py`, `sector_leadlag_lab/tests/test_main.py`
- Create (git-ignored): `$WS/record_after.pkl`

**Interfaces:**
- Consumes: `corrections.correct` and `Corrected` (Task 4); the fixtures `listing_bytes`, `yf_history`, `decayed_world` and the module fixture `decayed` of `tests/test_main.py` (existing).
- Produces: `Study.signal_jp: pd.DataFrame | None = None`, `Study.us_breaks: pd.DataFrame | None = None`, `Study.corrections: tuple[dict, ...] = ()`; `Study.us_returns()` masks `us_breaks`; `Study.etf_c2c()` returns `signal_jp` when it is set; `with_corrections(study: Study, us_close: pd.DataFrame, us_splits: pd.DataFrame) -> Study`; `load_study(root: Path = RAW_ROOT, *, corrected: bool = False) -> Study`.

- [ ] **Step 1: Write the failing tests**

In `sector_leadlag_lab/tests/test_study.py`, replace:

```python
        load_study(tmp_path)
```

with:

```python
        load_study(tmp_path)


def _store_closes(root, ticker, history, closes, dates=DATES):
    frame = history(dates, open_=closes, close=closes)
    content = yf.to_csv(frame, pd.Timestamp("2026-12-31").date())
    store_bytes(root, "yf", ticker, content, url=f"yfinance:{ticker}", filename=f"{ticker}.csv")


def test_the_corrected_study_applies_the_rules(tmp_path, listing_bytes, yf_history):
    rows = [("7203", 6, "TOPIX Core30")]
    store_bytes(tmp_path, "jpx", "data_j", listing_bytes(rows), url="u", filename="data_j.xlsx")
    for ticker in yf.US_SECTORS:
        _store_prices(tmp_path, ticker, yf_history, tz="America/New_York")
    for ticker in ETF_TICKERS[1:]:
        _store_prices(tmp_path, ticker, yf_history)
    _store_prices(tmp_path, ETF_TICKERS[0], yf_history, [*DATES[:2], *DATES[3:]])  # no 7th
    _store_closes(tmp_path, "7203.T", yf_history, [100.0, 100.0, 300.0, 300.0])  # no split
    record = load_study(tmp_path)
    study = load_study(tmp_path, corrected=True)
    assert record.signal_jp is None and record.us_breaks is None and record.corrections == ()
    assert [(c["rule"], c["series"], c["date"]) for c in study.corrections] == [
        ("C1", "7203.T", "2026-01-07"),
        ("C3", "1617.T", "2026-01-07"),
    ]
    assert list(study.etf_c2c().index) == [pd.Timestamp(d) for d in (DATES[0], DATES[1], DATES[3])]
    assert study.stocks.breaks.loc["2026-01-07", "7203"]
    pd.testing.assert_frame_equal(study.us_returns(), record.us_returns())
```

In `sector_leadlag_lab/tests/test_main.py`, replace:

```python
from sector_leadlag.main import ROBUSTNESS, SCENARIOS, run_main_a, run_main_b

G0 = {"selected": "lagged", "pass": True}
```

with:

```python
from sector_leadlag.main import ROBUSTNESS, SCENARIOS, run_main_a, run_main_b
from sector_leadlag.study import with_corrections

G0 = {"selected": "lagged", "pass": True}
```

In `sector_leadlag_lab/tests/test_main.py`, replace:

```python
    assert b["verdict"] == "etf_only"
```

with:

```python
    assert b["verdict"] == "etf_only"


def test_the_corrected_verdict_of_a_world_without_errors_is_the_records(decayed_world, decayed):
    w = decayed_world
    fixed = with_corrections(w, w.us_adj, w.us_adj * 0.0)
    assert fixed.corrections == ()
    a, b = _verdict(fixed)
    assert b["verdict"] == decayed[1]["verdict"] == "usable"
    assert a["h1"] == decayed[0]["h1"] and a["h2"] == decayed[0]["h2"]
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_study.py sector_leadlag_lab/tests/test_main.py -q
```

Expected: `ImportError: cannot import name 'with_corrections' from 'sector_leadlag.study'` while collecting `tests/test_main.py`, and `Interrupted: 1 error during collection`.

- [ ] **Step 3: Rewrite the study module**

File: `sector_leadlag_lab/src/sector_leadlag/study.py` (rewrite)

```python
"""Every input of the study in one object (design §4), and the periods of design §3.2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

from . import corrections, timing
from .baskets import SECTORS, Panel
from .data import jpx, yf
from .data.store import RAW_ROOT, indicators, read_latest

PANEL_START = pd.Timestamp("2009-06-01")  # C_full (2010-2014) needs a little history before it
A = (pd.Timestamp("2015-01-05"), pd.Timestamp("2026-03-18"))
B = (pd.Timestamp("2026-03-19"), pd.Timestamp("2026-10-05"))
B1 = (pd.Timestamp("2026-03-19"), pd.Timestamp("2026-07-23"))
B2 = (pd.Timestamp("2026-07-24"), pd.Timestamp("2026-10-05"))
C = (pd.Timestamp("2026-10-06"), pd.Timestamp("2099-12-31"))
ORIGINAL = (pd.Timestamp("2015-01-01"), pd.Timestamp("2025-12-31"))  # the strategy paper's span
LONGER_SESSION = pd.Timestamp("2024-11-05")  # the TSE close moved to 15:30
FIELDS = ("open", "close", "adj_close", "volume", "dividends", "splits")


@dataclass(frozen=True)
class Study:
    listing: jpx.Listing
    us_adj: pd.DataFrame  # dividend-adjusted closes of the 11 US sector ETFs on US trading days
    us_days: pd.DatetimeIndex
    jp_days: pd.DatetimeIndex
    s_map: pd.Series  # each Japanese day d -> s(d), the last US trading day before it
    etf: Panel  # the 17 NEXT FUNDS ETFs on Japanese days; columns are the sector codes 1-17
    stocks: Panel  # the TOPIX500 names with stored prices; columns are their codes
    missing: tuple[str, ...]  # TOPIX500 codes without stored prices
    signal_jp: pd.DataFrame | None = None  # corrected data: the signal's Japanese side (C7, C3)
    us_breaks: pd.DataFrame | None = None  # corrected data: US days after a jump in the close (C1)
    corrections: tuple[dict, ...] = ()  # corrected data: every change the rules made

    def us_returns(self) -> pd.DataFrame:
        returns = timing.close_to_close(self.us_adj, self.us_days)
        if self.us_breaks is None:
            return returns
        hidden = self.us_breaks.reindex(
            index=returns.index, columns=returns.columns, fill_value=False
        )
        return returns.mask(hidden)

    def etf_c2c(self) -> pd.DataFrame:
        """The Japanese side of the signal: ETF adjusted close to adjusted close (design §6).

        On the corrected data it is the C7 return on the days the signal's rows may use (C3).
        """
        if self.signal_jp is not None:
            return self.signal_jp
        return timing.close_to_close(self.etf.adj_close, self.jp_days)


def build_panel(frames: dict, days: pd.DatetimeIndex, sector: pd.Series) -> Panel:
    """One frame per field with a column per entry of ``frames``, on ``days``."""
    stacked = pd.concat(frames, axis=1, sort=True)
    parts = {
        field: stacked.xs(field, axis=1, level=1).reindex(days, columns=list(frames))
        for field in FIELDS
    }
    return Panel(**parts, sector=sector)


def with_corrections(study: Study, us_close: pd.DataFrame, us_splits: pd.DataFrame) -> Study:
    """``study`` after the rules of PREREG §5; the US closes and splits are on the US days."""
    fixed = corrections.correct(study.etf, study.stocks, us_close, us_splits)
    return replace(
        study,
        etf=fixed.etf,
        stocks=fixed.stocks,
        signal_jp=fixed.signal,
        us_breaks=fixed.us_breaks,
        corrections=tuple(fixed.changes),
    )


def load_study(root: Path = RAW_ROOT, *, corrected: bool = False) -> Study:
    """Every input from the snapshot store; with ``corrected``, after the rules of PREREG §5."""
    listing = jpx.parse_listing(read_latest(root, "jpx", "data_j"))
    stored = set(indicators(root, "yf"))

    def prices(ticker: str) -> pd.DataFrame:
        return yf.parse_csv(read_latest(root, "yf", ticker))

    members = jpx.topix500(listing)
    have = [code for code in members.index if jpx.stock_ticker(code) in stored]
    if not have:
        raise FileNotFoundError(f"no TOPIX500 prices under {root}; run `sector-leadlag snapshot`")
    stock_frames = {code: prices(jpx.stock_ticker(code)) for code in have}
    volume = pd.concat(
        {code: frame["volume"] for code, frame in stock_frames.items()}, axis=1, sort=True
    )
    jp_days = timing.jp_trading_days(volume.loc[PANEL_START:])
    us_frames = {ticker: prices(ticker) for ticker in yf.US_SECTORS}
    us_days = timing.us_trading_days(us_frames["XLK"]["volume"].loc[PANEL_START:])
    us_adj = pd.concat({t: f["adj_close"] for t, f in us_frames.items()}, axis=1, sort=True)
    etf_frames = {k: prices(ticker) for k, ticker in enumerate(jpx.ETF_TICKERS, start=1)}
    study = Study(
        listing=listing,
        us_adj=us_adj.reindex(us_days),
        us_days=us_days,
        jp_days=jp_days,
        s_map=timing.last_us_before(jp_days, us_days),
        etf=build_panel(etf_frames, jp_days, pd.Series(list(SECTORS), index=list(SECTORS))),
        stocks=build_panel(stock_frames, jp_days, members.loc[have, "sector"].astype(int)),
        missing=tuple(code for code in members.index if code not in set(have)),
    )
    if not corrected:
        return study
    us = {
        field: pd.concat({t: f[field] for t, f in us_frames.items()}, axis=1, sort=True)
        for field in ("close", "splits")
    }
    return with_corrections(study, us["close"].reindex(us_days), us["splits"].reindex(us_days))
```

- [ ] **Step 4: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_study.py sector_leadlag_lab/tests/test_main.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `7 passed`, then `104 passed, 1 skipped`.

- [ ] **Step 5: Compare the real record study with Task 1's dump**

```bash
cd $WT && $PY $WS/record_check.py dump $WS/record_after.pkl && $PY $WS/record_check.py compare $WS/record_before.pkl $WS/record_after.pkl
```

Expected: `23 frames written`, then `23 frames; different: []` and exit status 0. Any frame listed means the record's path changed: stop and find out why before going on. The two dumps (about 100 MB each) stay in `$WS` until the workspace is removed.

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/study.py sector_leadlag_lab/tests/test_study.py sector_leadlag_lab/tests/test_main.py && git commit -m "Load the study with the corrected-data rules applied"
```

Expected: ruff clean, one commit.

---

### Task 6: The corrected summary beside the record

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/report.py`
- Test: `sector_leadlag_lab/tests/test_report.py`

**Interfaces:**
- Consumes: the result files as the record's `report.py` reads them (`_load`, `_pct`, `_num`, `_fit`, `_g0` … `_diagnostics`, `SCENARIO_LABELS`, existing); `evaluate.ALPHA`, `timing.VARIANTS` (existing); the module fixture `results` of `tests/test_report.py` and `cli.write_result` (existing).
- Produces: `RULE_LABELS`, `STAGES`, `CONDITIONS`; `_sections(results: Path) -> list[str]`; `render(results: Path) -> str` (same output as before); `reading(record: dict, corrected: dict) -> tuple[str | None, str]` (`verdict_robust`, `verdict_data_dependent` or `None` without a corrected main B, and one line); `render_corrected(record: Path, corrected: Path) -> str`.

- [ ] **Step 1: Write the failing tests**

In `sector_leadlag_lab/tests/test_report.py`, replace:

```python
from sector_leadlag.main import run_main_a, run_main_b
from sector_leadlag.report import render


@pytest.fixture(scope="module")
```

with:

```python
from sector_leadlag.main import run_main_a, run_main_b
from sector_leadlag.report import render, render_corrected


@pytest.fixture(scope="module")
```

In `sector_leadlag_lab/tests/test_report.py`, replace:

```python
    assert "## G0 再現" in text and "## 本番 A" not in text
```

with:

```python
    assert "## G0 再現" in text and "## 本番 A" not in text


def test_the_corrected_summary_puts_the_record_beside_it(results):
    text = render_corrected(results, results)
    assert "**`verdict_robust`**：直したデータの判定も `usable`。" in text
    assert "| 判定 | `usable` | `usable` |" in text
    assert "## 記録と並べた表" in text and "### G0 再現" in text
    assert "nan" not in text.lower()


def test_a_corrected_run_that_stopped_at_g0_depends_on_the_data(tmp_path, results):
    g0 = json.loads((results / "g0.json").read_text(encoding="utf-8"))
    cli.write_result("g0", {**g0, "pass": False, "selected": None}, tmp_path, {})
    cli.write_result(
        "corrections",
        {"counts": {"C1": {"etf": 3}}, "missing_known": [], "changes": []},
        tmp_path,
        {},
    )
    text = render_corrected(results, tmp_path)
    assert "**`verdict_data_dependent`**：直したデータでは G0 で止まった" in text
    assert f"並べ方が {g0['selected']} から なし に変わった" in text
    assert (
        "| C1 桁の跳び | 3 | 0 | 0 |" in text and "既知の誤り（設計書 §2）：すべて直った。" in text
    )
    assert "| 判定 | `usable` | — |" in text and "nan" not in text.lower()


def test_a_changed_verdict_names_the_conditions_that_changed(tmp_path, results):
    for name in ("g0", "g1", "main_a", "diagnostics"):
        (tmp_path / f"{name}.json").write_text((results / f"{name}.json").read_text("utf-8"))
    b = json.loads((results / "main_b.json").read_text(encoding="utf-8"))
    evidence = {**b["evidence"], "b_mean_cash": -0.001}
    cli.write_result(
        "main_b", {**b, "verdict": "real_not_usable", "evidence": evidence}, tmp_path, {}
    )
    text = render_corrected(results, tmp_path)
    assert "直したデータの判定は `real_not_usable`（記録は `usable`）。" in text
    assert "変わった条件：④（本番 B で1と2が正）。" in text
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_report.py -q
```

Expected: `ImportError: cannot import name 'render_corrected' from 'sector_leadlag.report'` and `Interrupted: 1 error during collection`.

- [ ] **Step 3: Add the corrected summary**

In `sector_leadlag_lab/src/sector_leadlag/report.py`, replace:

```python
"""Markdown tables from the results JSON; README's result tables are copied from summary.md."""

from __future__ import annotations
```

with:

```python
"""Markdown tables from the results JSON; README's result tables are copied from summary.md.

``render_corrected`` writes the corrected data's summary with the record beside it (PREREG §5).
"""

from __future__ import annotations
```

In `sector_leadlag_lab/src/sector_leadlag/report.py`, replace:

```python
import json
from pathlib import Path

SCENARIO_LABELS = {
```

with:

```python
import json
from collections.abc import Callable
from pathlib import Path

from .evaluate import ALPHA
from .timing import VARIANTS

SCENARIO_LABELS = {
```

In `sector_leadlag_lab/src/sector_leadlag/report.py`, replace:

```python
}
SIGNAL_LABELS = {
```

with:

```python
}
RULE_LABELS = {
    "C2": "C2 始値0",
    "C1": "C1 桁の跳び",
    "C4": "C4 分割の日の配当",
    "C5": "C5 終値を超える配当",
    "C6": "C6 ETF の配当日",
    "C3": "C3 行の欠け",
}
STAGES = ("g0", "g1", "main_a", "main_b", "diagnostics")
CONDITIONS: tuple[tuple[str, Callable[[dict], bool]], ...] = (
    ("G0 の再現", lambda e: e["replicated"]),
    (
        "①（H1 が有意で、本番 B の係数が正）",
        lambda e: e["h1_p"] < ALPHA and e["beta_b_period_b"] > 0,
    ),
    ("②（H2 の1と2が有意）", lambda e: e["h2_p_cash"] < ALPHA and e["h2_p_spread"] < ALPHA),
    ("③（費用と元手を変えても符号が同じ）", lambda e: e["robust"]),
    ("④（本番 B で1と2が正）", lambda e: e["b_mean_cash"] > 0 and e["b_mean_spread"] > 0),
)
SIGNAL_LABELS = {
```

In `sector_leadlag_lab/src/sector_leadlag/report.py`, replace:

```python
    return lines


def render(results: Path) -> str:
    lines = ["# 日米業種リードラグ（候補12）の結果", ""]
    for name, part in (
```

with:

```python
    return lines


def _sections(results: Path) -> list[str]:
    lines: list[str] = []
    for name, part in (
```

In `sector_leadlag_lab/src/sector_leadlag/report.py`, replace:

```python
            lines += part(result)
    return "\n".join(lines).rstrip() + "\n"
```

with:

```python
            lines += part(result)
    return lines


def render(results: Path) -> str:
    lines = ["# 日米業種リードラグ（候補12）の結果", "", *_sections(results)]
    return "\n".join(lines).rstrip() + "\n"


def _at(result: dict | None, *keys):
    """result[k1][k2]...; None when any level is missing."""
    for key in keys:
        if not isinstance(result, dict) or key not in result:
            return None
        result = result[key]
    return result


def _mark(x: bool | None) -> str:
    return "—" if x is None else "○" if x else "×"


def _mean_p(part: dict | None) -> str:
    if part is None:
        return "—"
    return f"{_pct(part['mean_ann'])}（p={_num(part['p'], 4)}）"


def _interval(ci: list | None) -> str:
    return "—" if ci is None else f"{ci[0]:.2f}〜{ci[1]:.2f}"


def _g1_count(g1: dict | None) -> str:
    if g1 is None:
        return "—"
    return f"{g1['significant']} / {g1['count']}（合格 {_mark(g1['pass'])}）"


def _h3(h3: dict | None) -> str:
    if h3 is None:
        return "—"
    return f"`{h3['label']}`（0 より低い p={h3['p_below_zero']:.3f}）"


def _verdict(b: dict | None) -> str:
    return "—" if b is None else f"`{b['verdict']}`"


def _comparison_rows() -> list[tuple[str, Callable[[dict], str]]]:
    rows: list[tuple[str, Callable[[dict], str]]] = [
        ("並べ方", lambda r: _at(r["g0"], "selected") or "—")
    ]
    for v in VARIANTS:
        rows += [
            (
                f"G0 {v}：AR 2015–2025",
                lambda r, v=v: _pct(_at(r["g0"], "variants", v, "original", "ar")),
            ),
            (
                f"G0 {v}：本番 A の ETF の係数",
                lambda r, v=v: _fit(_at(r["g0"], "variants", v, "fit_a")),
            ),
            (f"G0 {v}：合格", lambda r, v=v: _mark(_at(r["g0"], "variants", v, "pass"))),
        ]
    rows += [
        ("G1：有意になった回数", lambda r: _g1_count(r["g1"])),
        ("H1：バスケットの係数（×1e-4）", lambda r: _fit(_at(r["main_a"], "h1", "basket"))),
        ("H1：ETF の係数", lambda r: _fit(_at(r["main_a"], "h1", "etf"))),
        ("比 β_B/β_ETF の95%区間", lambda r: _interval(_at(r["main_a"], "h1", "ratio_ci"))),
    ]
    for s in ("base", "cost_2bp", "cost_5bp"):
        rows += [
            (
                f"H2 {SCENARIO_LABELS[s]}：現物の買い 年率",
                lambda r, s=s: _mean_p(_at(r["main_a"], "h2", s, "cash")),
            ),
            (
                f"H2 {SCENARIO_LABELS[s]}：業種の選び方の差 年率",
                lambda r, s=s: _mean_p(_at(r["main_a"], "h2", s, "spread")),
            ),
        ]
    rows += [
        ("頑健性（③）", lambda r: _mark(_at(r["main_a"], "robust"))),
        ("本番 B：バスケットの係数", lambda r: _fit(_at(r["main_b"], "h1", "basket"))),
        ("本番 B：ETF の係数", lambda r: _fit(_at(r["main_b"], "h1", "etf"))),
        ("本番 B：現物の買い 年率", lambda r: _pct(_at(r["main_b"], "h2", "cash", "mean_ann"))),
        (
            "本番 B：業種の選び方の差 年率",
            lambda r: _pct(_at(r["main_b"], "h2", "spread", "mean_ann")),
        ),
        (
            "ETF のロング・ショート B1 年率",
            lambda r: _pct(_at(r["main_b"], "etf_long_short", "b1", "mean_ann")),
        ),
        (
            "ETF のロング・ショート B2 年率",
            lambda r: _pct(_at(r["main_b"], "etf_long_short", "b2", "mean_ann")),
        ),
        ("H3", lambda r: _h3(_at(r["main_b"], "h3"))),
    ]
    for name, label in (("basket", "バスケット"), ("etf", "ETF")):
        for when, word in (("before", "前"), ("after", "後")):
            rows.append(
                (
                    f"取引時間の延長の{word}（{label}）",
                    lambda r, n=name, w=when: _fit(_at(r["diagnostics"], "session_change", n, w)),
                )
            )
    rows.append(("判定", lambda r: _verdict(r["main_b"])))
    return rows


def reading(record: dict, corrected: dict) -> tuple[str | None, str]:
    """PREREG §5: the label, and one line on what the corrected data changed."""
    g0, g1, b = corrected["g0"], corrected["g1"], corrected["main_b"]
    pairing = ""
    if g0 is not None and g0["selected"] != _at(record["g0"], "selected"):
        pairing = (
            f"並べ方が {_at(record['g0'], 'selected')} から {g0['selected'] or 'なし'} に変わった。"
        )
    if g0 is not None and not g0["pass"]:
        return (
            "verdict_data_dependent",
            "直したデータでは G0 で止まった（`replication_failed`）。" + pairing,
        )
    if g1 is not None and not g1["pass"]:
        return "verdict_data_dependent", "直したデータでは G1 が不合格で止まった。" + pairing
    if b is None or record["main_b"] is None:
        return None, "直したデータの本番 B はまだない。" + pairing
    kept = record["main_b"]["verdict"]
    if b["verdict"] == kept:
        return "verdict_robust", f"直したデータの判定も `{kept}`。" + pairing
    changed = [
        label
        for label, holds in CONDITIONS
        if holds(record["main_b"]["evidence"]) != holds(b["evidence"])
    ]
    return (
        "verdict_data_dependent",
        f"直したデータの判定は `{b['verdict']}`（記録は `{kept}`）。"
        f"変わった条件：{'、'.join(changed) or 'なし'}。" + pairing,
    )


def _corrections(c: dict | None) -> list[str]:
    if c is None:
        return []
    lines = [
        "## 直したもの（corrections.json）",
        "",
        "| 規則 | ETF | 株 | 米国 |",
        "|---|---|---|---|",
    ]
    for rule, label in RULE_LABELS.items():
        n = c["counts"].get(rule, {})
        lines.append(f"| {label} | {n.get('etf', 0)} | {n.get('stock', 0)} | {n.get('us', 0)} |")
    missing = c["missing_known"]
    known = (
        "すべて直った" if not missing else "直っていない：" + "、".join(m["label"] for m in missing)
    )
    return [*lines, "", f"既知の誤り（設計書 §2）：{known}。", ""]


def _decomposition(record: dict | None, fixed: dict | None) -> list[str]:
    lines = [
        "## 分解（区間ごとのロング・ショートの年率。記録／直したデータ）",
        "",
        "| 価格 | 区間 | A | B1 | B2 |",
        "|---|---|---|---|---|",
    ]
    for name, label in (("etf", "ETF"), ("basket", "バスケット")):
        for leg in ("c2o", "o2c", "c2c"):
            cells = [
                f"{_pct(_at(record, 'decomposition', name, leg, p))}／"
                f"{_pct(_at(fixed, 'decomposition', name, leg, p))}"
                for p in ("a", "b1", "b2")
            ]
            lines.append(f"| {label} | {leg.upper()} | {' | '.join(cells)} |")
    return [*lines, ""]


def render_corrected(record: Path, corrected: Path) -> str:
    """The corrected data's summary: the reading of PREREG §5, the record beside it, every table."""
    kept = {name: _load(record, name) for name in STAGES}
    fixed = {name: _load(corrected, name) for name in STAGES}
    label, line = reading(kept, fixed)
    lines = [
        "# 日米業種リードラグ（候補12）：直したデータでの再計算",
        "",
        "PREREG §5 の確認で、判定のあとに回した。記録の判定（`results/main_b.json`）は変えない。",
        "",
        "## 読み方（PREREG §5）",
        "",
        f"**`{label}`**：{line}" if label else line,
        "",
        *_corrections(_load(corrected, "corrections")),
        "## 記録と並べた表",
        "",
        "| 項目 | 記録 | 直したデータ |",
        "|---|---|---|",
        *[f"| {name} | {cell(kept)} | {cell(fixed)} |" for name, cell in _comparison_rows()],
        "",
        *_decomposition(kept["diagnostics"], fixed["diagnostics"]),
        "## 直したデータの各段の結果",
        "",
        *[f"#{text}" if text.startswith("## ") else text for text in _sections(corrected)],
    ]
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run the tests**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_report.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
```

Expected: `5 passed`, then `107 passed, 1 skipped`.

- [ ] **Step 5: Check that the record's summary renders as committed**

```bash
cd $WT && $PY -c "
from pathlib import Path
from sector_leadlag.report import render
p = Path('sector_leadlag_lab/results')
assert render(p) == (p / 'summary.md').read_text(encoding='utf-8')
print('record summary unchanged')
"
```

Expected: `record summary unchanged` (nothing is written).

- [ ] **Step 6: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/report.py sector_leadlag_lab/tests/test_report.py && git commit -m "Render the corrected-data summary with the record beside it"
```

Expected: ruff clean, one commit.

---

### Task 7: The CLI: `corrections`, the corrected runs and their gates

**Files:**
- Modify: `sector_leadlag_lab/src/sector_leadlag/cli.py`
- Test: `sector_leadlag_lab/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_study(corrected=True)` (Task 5); `corrections.counts`, `missing_known`, `KNOWN` (Task 4); `report.render_corrected` (Task 6); `read_result`, `write_result`, `take_lock`, `check_ready`, `main_b_target`, `_json_default`, `_git`, `inputs_digest`, `StageError` (existing).
- Produces: `CORRECTED = RESULTS / "corrected"`, `DATA = ("record", "corrected")`; `meta(results: str = "results") -> dict`; `corrected_meta() -> dict`; `check_snapshot(run_meta: dict, record: Path) -> None`; `check_prereg_section(run_meta: dict) -> None`; `plain(value)`; `check_corrections(changes: tuple[dict, ...], results: Path) -> str` (the file's SHA-256); the commands `corrections`, `run STAGE [--rerun-reason TEXT] [--data record|corrected]` and `report [--data record|corrected]`.

- [ ] **Step 1: Write the failing tests**

In `sector_leadlag_lab/tests/test_cli.py`, replace:

```python
import subprocess

import numpy as np
```

with:

```python
import subprocess
from types import SimpleNamespace

import numpy as np
```

In `sector_leadlag_lab/tests/test_cli.py`, replace:

```python
import pytest
from sector_leadlag import cli
from sector_leadlag.data.store import store_bytes
```

with:

```python
import pytest
from click.testing import CliRunner
from sector_leadlag import cli
from sector_leadlag import g0 as g0_module
from sector_leadlag import study as study_module
from sector_leadlag.corrections import KNOWN
from sector_leadlag.data.store import store_bytes
```

In `sector_leadlag_lab/tests/test_cli.py`, replace:

```python
    assert first[1] == second[1] == 1 and first[0] != second[0]
```

with:

```python
    assert first[1] == second[1] == 1 and first[0] != second[0]


CHANGE = {
    "rule": "C1",
    "kind": "etf",
    "series": "1629.T",
    "date": "2015-01-05",
    "field": "returns",
    "before": 0.002,
    "after": None,
}
CORRECTED_META = {
    **META,
    "git_commit": "abc",
    "data": "corrected",
    "inputs_digest": "d",
    "prereg_has_section_5": True,
    "record_main_b_committed_at": "2026-10-19T12:00:00+09:00",
}


def test_corrected_data_must_come_from_the_records_snapshot(tmp_path):
    write(tmp_path, "main_b", {"meta": {"inputs_digest": "d"}})
    cli.check_snapshot({"inputs_digest": "d"}, tmp_path)
    with pytest.raises(cli.StageError, match="snapshot of the record"):
        cli.check_snapshot({"inputs_digest": "e"}, tmp_path)


def test_corrected_stages_need_section_5_committed_after_the_record():
    cli.check_prereg_section(CORRECTED_META)
    with pytest.raises(cli.StageError, match="§5"):
        cli.check_prereg_section({**CORRECTED_META, "prereg_has_section_5": False})
    with pytest.raises(cli.StageError, match="after the record"):
        late = {**CORRECTED_META, "record_main_b_committed_at": "2026-10-20T11:00:00+09:00"}
        cli.check_prereg_section(late)


def test_corrected_stages_need_the_corrections_that_the_rules_make(tmp_path):
    with pytest.raises(cli.StageError, match=r"corrections\.json is missing"):
        cli.check_corrections((CHANGE,), tmp_path)
    write(tmp_path, "corrections", {"missing_known": [{"label": "x"}], "changes": [CHANGE]})
    with pytest.raises(cli.StageError, match="known-error check"):
        cli.check_corrections((CHANGE,), tmp_path)
    write(tmp_path, "corrections", {"missing_known": [], "changes": [CHANGE]})
    with pytest.raises(cli.StageError, match="does not match the rules"):
        cli.check_corrections(({**CHANGE, "date": "2015-01-06"},), tmp_path)
    assert len(cli.check_corrections((CHANGE,), tmp_path)) == 64


def _corrected_lab(tmp_path, monkeypatch):
    record = tmp_path / "results"
    corrected = record / "corrected"
    corrected.mkdir(parents=True)
    write(record, "main_b", {"meta": {"inputs_digest": "d"}, "verdict": "usable"})
    monkeypatch.setattr(cli, "RESULTS", record)
    monkeypatch.setattr(cli, "CORRECTED", corrected)

    def load(corrected=False):
        assert corrected, "a corrected run must not load the record's data"
        return SimpleNamespace(corrections=(CHANGE,))

    monkeypatch.setattr(study_module, "load_study", load)
    return record, corrected


def test_the_corrections_command_lists_the_changes_and_stops_on_a_missed_error(
    tmp_path, monkeypatch
):
    _, corrected = _corrected_lab(tmp_path, monkeypatch)
    monkeypatch.setattr(cli, "meta", lambda results="results": {**META, "inputs_digest": "d"})
    out = CliRunner().invoke(cli.main, ["corrections"])
    assert out.exit_code == 1 and "no rule changed these known errors" in out.output
    stored = json.loads((corrected / "corrections.json").read_text(encoding="utf-8"))
    assert stored["meta"]["data"] == "corrected" and stored["changes"] == [CHANGE]
    assert stored["counts"]["C1"] == {"etf": 1} and len(stored["missing_known"]) == len(KNOWN) - 1


def test_a_corrected_run_writes_only_under_results_corrected(tmp_path, monkeypatch):
    record, corrected = _corrected_lab(tmp_path, monkeypatch)
    write(corrected, "corrections", {"missing_known": [], "changes": [CHANGE]})
    monkeypatch.setattr(cli, "corrected_meta", lambda: dict(CORRECTED_META))
    monkeypatch.setattr(g0_module, "run_g0", lambda study, prior: {"pass": True})
    before = sorted(path.name for path in record.iterdir())
    out = CliRunner().invoke(cli.main, ["run", "g0", "--data", "corrected"])
    assert out.exit_code == 0, out.output
    written = json.loads((corrected / "g0.json").read_text(encoding="utf-8"))
    assert written["pass"] and written["meta"]["data"] == "corrected"
    assert len(written["meta"]["corrections_sha256"]) == 64
    assert sorted(path.name for path in record.iterdir()) == before


def test_corrected_meta_reads_section_5_from_the_committed_prereg(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "results").mkdir(parents=True)
    git = ["git", "-C", str(lab), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(lab)], check=True)

    def commit(path: str, text: str) -> None:
        (lab / path).write_text(text)
        subprocess.run([*git, "add", path], check=True)
        subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-qm", path], check=True)

    commit("results/main_b.json", "{}")
    commit("PREREG.md", "## 4. x\n")
    monkeypatch.setattr(cli, "LAB", lab)
    monkeypatch.setattr(cli, "RAW_ROOT", tmp_path / "raw")
    first = cli.corrected_meta()
    assert first["data"] == "corrected" and not first["prereg_has_section_5"]
    assert first["record_main_b_commit"] and first["record_main_b_committed_at"][:4].isdigit()
    (lab / "PREREG.md").write_text("## 4. x\n## 5. y\n")
    assert not cli.corrected_meta()["prereg_has_section_5"]  # written, not committed
    commit("PREREG.md", "## 4. x\n## 5. y\n")
    assert cli.corrected_meta()["prereg_has_section_5"]
```

- [ ] **Step 2: Run them to see them fail**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_cli.py -q
```

Expected: `6 failed, 9 passed`; the six new tests fail on `AttributeError` (no `check_snapshot`, `check_prereg_section`, `check_corrections`, `CORRECTED` or `corrected_meta` in `sector_leadlag.cli`).

- [ ] **Step 3: Add the command, the option and the gates**

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
"""Command line: ``sector-leadlag snapshot``, ``run STAGE``, ``inputs`` and ``report``.

The stage order of design §3.5 is enforced here. Every stage needs a committed PREREG.md; main A
```

with:

```python
"""Command line: ``sector-leadlag snapshot``, ``run STAGE``, ``inputs``, ``corrections``, ``report``.

The stage order of design §3.5 is enforced here. Every stage needs a committed PREREG.md; main A
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
lock file); a rerun needs a reason and never replaces the verdict of record.
"""
```

with:

```python
lock file); a rerun needs a reason and never replaces the verdict of record.

``--data corrected`` reruns the stages on the corrected data of PREREG §5 (design 2026-10-20) into
results/corrected/, under the same gates and three more: the stored inputs are the record's
snapshot, PREREG.md has §5 committed after the record's main B, and results/corrected/
corrections.json passed the known-error check and lists exactly the changes the rules make.
"""
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
RESULTS = LAB / "results"
RUNNERS = {
```

with:

```python
RESULTS = LAB / "results"
CORRECTED = RESULTS / "corrected"
DATA = ("record", "corrected")
RUNNERS = {
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
    return hashlib.sha256(lines.encode()).hexdigest(), len(records)


def meta() -> dict:
    digest, count = inputs_digest(RAW_ROOT)
```

with:

```python
    return hashlib.sha256(lines.encode()).hexdigest(), len(records)


def meta(results: str = "results") -> dict:
    """What a result was computed from; ``results`` is its folder, relative to the lab."""
    digest, count = inputs_digest(RAW_ROOT)
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
        "prereg_committed_at": _git("log", "-1", "--format=%cI", "--", "PREREG.md"),
        "main_a_commit": _git("log", "-1", "--format=%H", "--", "results/main_a.json"),
        "inputs_digest": digest,
        "inputs_count": count,
    }
```

with:

```python
        "prereg_committed_at": _git("log", "-1", "--format=%cI", "--", "PREREG.md"),
        "main_a_commit": _git("log", "-1", "--format=%H", "--", f"{results}/main_a.json"),
        "inputs_digest": digest,
        "inputs_count": count,
    }


def corrected_meta() -> dict:
    """``meta`` of a result on the corrected data, with what its gates need."""
    run_meta = meta("results/corrected")
    prereg = (
        _git("show", f"{run_meta['prereg_commit']}:./PREREG.md")
        if run_meta["prereg_commit"]
        else ""
    )
    return {
        **run_meta,
        "data": "corrected",
        "prereg_has_section_5": any(line.startswith("## 5.") for line in prereg.splitlines()),
        "record_main_b_commit": _git("log", "-1", "--format=%H", "--", "results/main_b.json"),
        "record_main_b_committed_at": _git(
            "log", "-1", "--format=%cI", "--", "results/main_b.json"
        ),
    }
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
    return prior


def main_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
```

with:

```python
    return prior


def check_snapshot(run_meta: dict, record: Path) -> None:
    """The corrected data must come from the snapshot of the record's verdict (design §4)."""
    stored = read_result("main_b", record)["meta"]["inputs_digest"]
    if run_meta["inputs_digest"] != stored:
        raise StageError(
            "the stored inputs are not the snapshot of the record's main B; correct that snapshot"
        )


def check_prereg_section(run_meta: dict) -> None:
    """Every stage on corrected data needs PREREG §5, committed after the record's main B."""
    if not run_meta["prereg_has_section_5"]:
        raise StageError("write the corrected-data rules into PREREG.md §5 and commit it first")
    record = run_meta["record_main_b_committed_at"]
    prereg = datetime.fromisoformat(run_meta["prereg_committed_at"])
    if not record or prereg <= datetime.fromisoformat(record):
        raise StageError("commit PREREG.md §5 after the record's results/main_b.json")


def plain(value):
    """``value`` as it reads back from a results file."""
    return json.loads(json.dumps(value, default=_json_default))


def check_corrections(changes: tuple[dict, ...], results: Path) -> str:
    """corrections.json passed the known-error check and lists exactly ``changes``; its SHA-256."""
    path = results / "corrections.json"
    stored = read_result("corrections", results)
    if stored["missing_known"]:
        raise StageError(f"{path} failed the known-error check; fix the rules first")
    if stored["changes"] != plain(list(changes)):
        raise StageError(f"{path} does not match the rules; run `sector-leadlag corrections` again")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
@click.option("--rerun-reason", default=None, help="Required to run main-b a second time.")
def run(stage: str, rerun_reason: str | None) -> None:
    """Run one stage and write results/<stage>.json."""
    from .study import load_study

    run_meta = meta()
    prior = check_ready(stage, RESULTS, run_meta)
    name, extra = stage.replace("-", "_"), {}
    if stage == "main-b":
        name, extra = main_b_target(RESULTS, rerun_reason)
        if name == "main_b":
            take_lock(RESULTS, run_meta["git_commit"])
    module, function = RUNNERS[stage]
    runner = getattr(importlib.import_module(module), function)
    try:
        result = runner(load_study(), prior)
    except BaseException:
        if name == "main_b":
            (RESULTS / "main_b.lock").unlink(missing_ok=True)  # nothing was seen; allow a clean run
        raise
    click.echo(write_result(name, {**extra, **result}, RESULTS, run_meta))


@main.command()
```

with:

```python
@click.option("--rerun-reason", default=None, help="Required to run main-b a second time.")
@click.option(
    "--data",
    type=click.Choice(DATA),
    default="record",
    help="corrected: rerun on the corrected data of PREREG §5 into results/corrected/.",
)
def run(stage: str, rerun_reason: str | None, data: str) -> None:
    """Run one stage and write results/<stage>.json (or results/corrected/<stage>.json)."""
    from .study import load_study

    corrected = data == "corrected"
    results = CORRECTED if corrected else RESULTS
    run_meta = corrected_meta() if corrected else meta()
    if corrected:
        check_snapshot(run_meta, RESULTS)
        check_prereg_section(run_meta)
    prior = check_ready(stage, results, run_meta)
    name, extra = stage.replace("-", "_"), {}
    if stage == "main-b":
        name, extra = main_b_target(results, rerun_reason)
    study = load_study(corrected=corrected)
    if corrected:
        run_meta["corrections_sha256"] = check_corrections(study.corrections, CORRECTED)
    if name == "main_b":
        take_lock(results, run_meta["git_commit"])
    module, function = RUNNERS[stage]
    runner = getattr(importlib.import_module(module), function)
    try:
        result = runner(study, prior)
    except BaseException:
        if name == "main_b":
            (results / "main_b.lock").unlink(missing_ok=True)  # nothing was seen; allow a clean run
        raise
    click.echo(write_result(name, {**extra, **result}, results, run_meta))


@main.command()
def corrections() -> None:
    """Apply the rules of PREREG §5 and write results/corrected/corrections.json (no stage)."""
    from .corrections import counts, missing_known
    from .study import load_study

    run_meta = {**meta("results/corrected"), "data": "corrected"}
    check_snapshot(run_meta, RESULTS)
    changes = list(load_study(corrected=True).corrections)
    missing = missing_known(changes)
    result = {"counts": counts(changes), "missing_known": missing, "changes": changes}
    click.echo(write_result("corrections", result, CORRECTED, run_meta))
    if missing:
        labels = "; ".join(item["label"] for item in missing)
        raise StageError(f"no rule changed these known errors (design §3): {labels}")


@main.command()
```

In `sector_leadlag_lab/src/sector_leadlag/cli.py`, replace:

```python
@main.command()
def report() -> None:
    """Write results/summary.md from the results JSON."""
    from .report import render

    path = RESULTS / "summary.md"
    path.write_text(render(RESULTS), encoding="utf-8")
    click.echo(path)
```

with:

```python
@main.command()
@click.option("--data", type=click.Choice(DATA), default="record")
def report(data: str) -> None:
    """Write results/summary.md, or results/corrected/summary.md beside the record."""
    from .report import render, render_corrected

    if data == "corrected":
        path = CORRECTED / "summary.md"
        path.write_text(render_corrected(RESULTS, CORRECTED), encoding="utf-8")
    else:
        path = RESULTS / "summary.md"
        path.write_text(render(RESULTS), encoding="utf-8")
    click.echo(path)
```

- [ ] **Step 4: Run the tests and the help**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_cli.py -q && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q && $SLL --help && $SLL run --help
```

Expected: `15 passed`, then `113 passed, 1 skipped`; the command list shows `corrections`, `inputs`, `report`, `run`, `snapshot`; `run --help` shows `--data [record|corrected]`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab && git add sector_leadlag_lab/src/sector_leadlag/cli.py sector_leadlag_lab/tests/test_cli.py && git commit -m "Run the stages on the corrected data into results/corrected under three more gates"
```

Expected: ruff clean, one commit.

---
### Task 8: The corrections on the real data, and PREREG §5

**Files:**
- Create: `sector_leadlag_lab/results/corrected/corrections.json`
- Modify: `sector_leadlag_lab/PREREG.md` (append §5; §1–§4 unchanged)

**Interfaces:**
- Consumes: Tasks 1–7; the record's snapshot and `results/main_b.json`.
- Produces: `results/corrected/corrections.json` and the PREREG commit that every corrected stage requires (D9, D10).

- [ ] **Step 1: Apply the rules to the snapshot**

```bash
cd $WT && time $SLL corrections && $PY -c "
import json
c = json.load(open('sector_leadlag_lab/results/corrected/corrections.json'))
m = c['meta']
print('meta', m['inputs_digest'][:8], m['inputs_count'], m['dirty'], m['data'])
print('counts', c['counts'])
print('missing', c['missing_known'], 'changes', len(c['changes']))
for x in c['changes']:
    if x['rule'] == 'C1' or (x['rule'] == 'C5' and x['kind'] == 'etf'):
        print(x['rule'], x['series'], x['date'], x['before'], x['after'])
"
```

Expected (measured on this snapshot while the plan was written; no stage ran):

```text
meta 25d13c11 520 False corrected
counts {'C2': {'etf': 53}, 'C1': {'etf': 3, 'stock': 6}, 'C4': {'stock': 47}, 'C5': {'etf': 1, 'stock': 12}, 'C6': {'etf': 238}, 'C3': {'etf': 16}}
missing [] changes 376
C1 1629.T 2015-01-05 0.001975177278924815 None
C1 1629.T 2026-03-30 0.001966735966053051 None
C1 1629.T 2026-04-01 525.100078909843 None
C1 8227.T 2026-02-18 0.33635264963768113 None
C1 8303.T 2023-09-27 19771264.63902788 None
C1 8303.T 2025-12-18 3.253796186023972e-08 None
C1 9201.T 2010-01-13 0.1891891891891892 None
C1 9201.T 2010-01-20 0.4 None
C1 9201.T 2012-09-19 1915.0 None
C5 1629.T 2015-07-15 1385.0 2.7356205313108686
```

If `corrections` exits with `no rule changed these known errors`, or any count differs, stop and report to the user (spec §3): do not write §5 and run no stage.

- [ ] **Step 2: Note the file's SHA-256**

```bash
cd $WT && sha256sum sector_leadlag_lab/results/corrected/corrections.json
```

Expected: one hash; its first 12 characters go into §5.3. Every corrected stage records the whole hash as `meta.corrections_sha256`.

- [ ] **Step 3: Append PREREG §5**

Append the following to the end of `sector_leadlag_lab/PREREG.md`, after one blank line, with `[sha12]` replaced by the 12 characters of Step 2 and nothing else in the file changed:

```markdown
## 5. 直したデータでの再計算（判定のあとの確認。2026-10-20）

- 設計書：`/home/kazumasa/projects/docs/superpowers/specs/2026-10-20-sector-leadlag-corrected-data-design.md`
- 実装計画：`/home/kazumasa/projects/docs/superpowers/plans/2026-10-20-sector-leadlag-corrected-data.md`
- 目的：記録の判定 `usable` と主な数値が、yfinance のデータの誤り（§4 の最後の項と README の「限界」）に左右されたかを確かめる。同じ snapshot を規則で直し、§1〜§4 の手順をそのまま回して、記録と並べて報告する。
- 記録の判定（`results/main_b.json` の `usable`）、記録の結果ファイル、§1〜§4 は変えない。この節を commit してから、直したデータで G0 を回す。直したデータの G0 と G1 の結果を §5.6 に書き足して commit してから、直したデータで本番 A を回す。

### 5.1 直す規則

ETF・株・SPDR のすべての系列に、パネルの期間（2009-06-01 から）の各市場の営業日に並べた値で、次の順番で当てる。

- 「前日終値」はその系列の前の営業日の終値（その日に行がなければ、前日終値からのリターンは欠ける。記録と同じ）。C1 の「前の行」は、行のない日を飛ばした前の終値。「分割の記録」は yfinance の分割の値が正の日。
- 「株の中央値の配当込みの C2O」は、C2 と C1 を当てたあと、C4 と C5 を当てる前の、株の C2O のその日の中央値。

1. C2 始値0：出来高が正なのに始値が0の行は、始値を欠損にする（O2C・C2O が欠損になる）。
2. C1 桁の跳び：分割の記録のない日 d に、終値が前の行の終値の2倍超か1/2未満なら、d をまたぐ前日終値からのリターン（C2O・C2C・価格の C2C・シグナルの C2C）を欠損にする。O2C と価格の水準は変えない。米国の SPDR にも当て、そのリターン（記録と同じく配当込み終値の C2C）を欠損にする。
3. C4 分割の日の配当：分割の記録（比 k）と同じ日の配当 D は、次の2つがどちらも D/k を指すときだけ D/k にする。① D/k が D より、その系列の直前の配当（パネルの期間で d より前の、最も新しい正の配当）に近い（対数の差）。② 前日終値 P に対する D/(kP) が D/P より、その日の下落に近い。下落は、株の中央値の配当込みの C2O から、その系列の始値÷前日終値−1 を引いたもの。直前の配当がないか、その日の下落が測れない（出来高0、前日終値なし、C1 の日）なら D のまま。
4. C5 終値を超える配当：D が前日終値より大きいとき、その系列の d より前の最も新しい C1 の跳びが下げ（終値が前の行の1/2未満）なら、D をその跳びの大きさ（前の行の終値÷終値。1629.T の 2015 年は約506）で割る。割ってもまだ前日終値より大きいか、最も新しい跳びが上げか、跳びがなければ、D を0にする。
5. C6 ETF の配当日：NEXT FUNDS（1617〜1633.T）の配当を、記録の日と、その ETF の前の2つの行の日のうち、点数が一番低い日に移す。点数は、その日に出来高があり C1 の日でない ETF の「始値÷前日終値−1 から株の中央値の配当込みの C2O を引いたもの」の平均。同点なら早い日。どの候補の日にも点数がなければ動かさない。移した先の日に配当があれば足す。
6. C3 行の欠け：上場中（最初の行から最後の行まで）の ETF に行がない日本の営業日は、シグナルの行（窓と $C_\text{full}$）から外す。その日の配当と C1 の印は、次のシグナルの行に移す。株とバスケット、評価する日は変えない。
7. C7 シグナルの日本側：yfinance の配当込み終値をやめ、シグナルの行ごとに（終値＋配当）÷前のシグナルの行の終値−1 にする（配当は C4〜C6 のあと）。出来高ゼロの日も値を使う（記録と同じく、ほとんどは変化0）。C1 の印のある行は欠損。

直したものは、規則・系列・日付・項目・前後の値を `results/corrected/corrections.json` に一覧にする（規則の順、ETF・株・米国の順、系列ごとに日付の順）。

### 5.2 既知の誤りの確認

規則を当てたあと、次がそれぞれの規則で直ったかを確かめる（件数は最低限）。1つでも足りなければ `sector-leadlag corrections` が止まり、直したデータのどの段も回らない。

| 誤り（設計書 §2） | 規則 | 系列 | 日付 | 件数 |
|---|---|---|---|---|
| 1629.T の記録のない分割（約1:506） | C1 | 1629.T | 2015-01-05 | 1 |
| 1629.T の価格が約1/500になる | C1 | 1629.T | 2026-03-30 | 1 |
| 1629.T の価格が戻る | C1 | 1629.T | 2026-04-01 | 1 |
| 1629.T の分割前の1口あたりの配当 | C5 | 1629.T | 2015-07-15 | 1 |
| NEXT FUNDS 16本の行の欠け | C3 | ETF | 2025-10-24 | 16 |
| NEXT FUNDS の配当の日付の遅れ（17本、2013〜2026年） | C6 | ETF | — | 238 |
| NEXT FUNDS の始値0（2009年） | C2 | ETF | — | 53 |
| 8303 の1株2億〜2.4億円の配当 | C5 | 8303.T | — | 12 |
| 9861 の分割の日の配当 | C4 | 9861.T | 2013-08-28 | 1 |
| 5401 の分割の日の配当 | C4 | 5401.T | 2025-09-29 | 1 |
| 8766 の分割の日の配当 | C4 | 8766.T | 2026-09-29 | 1 |
| 8227 の分割の価格が先に出る | C1 | 8227.T | 2026-02-18 | 1 |

### 5.3 規則を当てた結果（2026-10-19 の snapshot。直したデータで段を回す前）

`results/corrected/corrections.json`（SHA-256 の先頭12文字 [sha12]）に一覧がある。計376件で、既知の誤りはすべて直った。

| 規則 | ETF | 株 | 米国 |
|---|---|---|---|
| C2 始値0 | 53 | 0 | 0 |
| C1 桁の跳び | 3 | 6 | 0 |
| C4 分割の日の配当 | 0 | 47 | 0 |
| C5 終値を超える配当 | 1 | 12 | 0 |
| C6 ETF の配当日 | 238 | 0 | 0 |
| C3 行の欠け | 16 | 0 | 0 |

- C1 の9件：1629.T の 2015-01-05・2026-03-30・2026-04-01、8227 の 2026-02-18、8303 の 2023-09-27（上場廃止の期間の最初の行。終値が前の行の約2,000万倍で、出来高0のまま 2025-12-17 まで続く）と 2025-12-18（再上場）、9201 の 2010-01-13・2010-01-20（株価1〜5円）と 2012-09-19（再上場）。
- C5：1629.T の 2015-07-15 の 1,385円を 2.74円にした（÷約506）。8303 の12回（2011〜2023年）は0にした。
- C6：2013〜2026年の毎年、17本すべての配当が同じ日に移った（2019年までは2営業日前、2020年からは1営業日前）。
- C4：分割と同じ日の配当320件のうち47件を割った（9861・5401・8766 のほか、8377・7282・9065・2433・5706 など）。D/P が4%を超える14件のうち11件を含む。割らなかった3件は、9101 と 9107 の 2022-09-29（実際に大きかった配当）と、8174 の 2026-09-29（その日の下落が D/P に近い）。
- C2 の53件は 2009-07-02〜10-14 の15本。C3 の16件は 2025-10-24 の 1629.T 以外の16本。

### 5.4 手順と関門

1. `sector-leadlag corrections`：規則を当て、`results/corrected/corrections.json` を書く（シグナルと価格の関係は何も計算しない）。既知の誤りの確認が通ってから、この節を commit する。
2. `run g0 --data corrected`（並べ方の選択を含む）、`run g1 --data corrected`。その結果を §5.6 に書き足して commit する。
3. `run main-a --data corrected`。その結果を commit する。
4. `run main-b --data corrected` を1回だけ回す（`results/corrected/main_b.lock`）。2回目は `--rerun-reason` が要り、読み方には最初の1回を使う。
5. `run diagnostics --data corrected`、`report --data corrected`（`results/corrected/summary.md`）。

直したデータのどの段も、記録の関門に次を足して求める。

- 生データの `inputs_digest` が、記録の `results/main_b.json` の `meta.inputs_digest`（`25d13c11…`、520本）と同じ。`corrections` も同じ。
- PREREG.md の最後の commit に §5 があり、その commit が記録の `results/main_b.json` の commit より新しい。
- `results/corrected/corrections.json` が既知の誤りの確認に通っていて、その一覧が、いま規則を当てて出る一覧と同じ。結果の `meta` に、その SHA-256 と `data: corrected` を入れる。
- 結果は `results/corrected/` にだけ書く。記録と同じく、G0 で並べ方が選ばれなければ止め、G1 が不合格なら止める。本番 A は G1 を回したあとの PREREG の commit を、本番 B は `results/corrected/main_a.json` の commit を求める。

### 5.5 読み方（計算の前に固定する）

- 主に見るのは、直したデータの判定（`results/corrected/main_b.json` の `verdict`。最初の1回）。
  - 記録と同じ `usable` なら `verdict_robust`。
  - 違えば `verdict_data_dependent`。判定のどの条件が変わったかを書く：G0 の再現、①（H1 が有意で、本番 B のバスケットの係数が正）、②（H2 の1と2がどちらも有意）、③（費用と元手を変えても本番 A の1と2の符号が同じ）、④（本番 B で1と2がどちらも正）。
  - 直したデータで G0 か G1 で止まった場合も `verdict_data_dependent`。並べ方が変わった場合は、そのことも書く。
- 並べて報告するだけにするもの：並べ方、G0 の AR と ETF の係数、G1、H1 の係数と t、比の区間、H2 の平均と p（基準・片道 2bp・5bp）、頑健性、本番 B の係数と平均、ETF のロング・ショートの B1 と B2、H3、取引時間の延長の前後、分解（株の C2O・C2C は直したデータで初めて読める）。
- 記録の判定は `usable` のまま変えない。README には両方を書く。

### 5.6 直したデータの G0 と G1 の結果（本番 A の前に書き足す）

- （直したデータで G1 を回したあとに書き足す。）

### 5.7 直さない誤りと限界

- 規則は、誤りを見たあとに決めた。閾値（2倍）は実データの分布を見て決めた。C4 は、規則を実データに当てて（何を直すかだけを見て）改めた（最初の案はその日の下落だけで決め、320件のうち193件を割った）。どの時点でも、直したデータで段は回していない。
- 2025-10-24 の16本の値そのものは直せない（C3 で、次の行の C2C を2日分にするだけ）。8303 の本当の配当額は分からないので0にした。
- 2015-12-25 と 2016-07-11 は東証が開いていたが、yfinance の株466銘柄のうち約450が出来高0・前日終値のままで、日本の営業日から外れている（ETF は取引あり）。規則では直さない。評価する日が2日少なく、次の営業日の ETF のシグナルの C2C と株の C2O・C2C が2日分になる（記録と同じ）。
- C1 は本当の値動きも外す（9201 の 2010 年の2日と 2012 年の再上場の日。どれも本番 A より前）。
- 8227 の分割は、記録の日（02-19）より前の価格が調整されていないので、H2 の株数を決める価格（分割を戻した値）が3倍になる。8227 は100株の金額が1銘柄の予算を超えるので、記録でも直したデータでも買わない。直さない。
- 規則が拾うのは、閾値を超える誤りと §5.1 の型の誤りだけ。小さな誤りは残りうる。
```

- [ ] **Step 4: Check that only §5 was added**

```bash
cd $WT && git diff --numstat -- sector_leadlag_lab/PREREG.md
```

Expected: one line, `<added lines>	0	sector_leadlag_lab/PREREG.md` (no line removed or changed).

- [ ] **Step 5: Commit**

```bash
cd $WT && git add sector_leadlag_lab/PREREG.md sector_leadlag_lab/results/corrected/corrections.json && git commit -m "Pre-register the corrected-data rerun in PREREG §5 with the list of corrections" && git log -1 --format=%cI -- sector_leadlag_lab/PREREG.md && git log -1 --format=%cI -- sector_leadlag_lab/results/main_b.json
```

Expected: one commit; the first date (now) is later than the second (`2026-10-19T15:03:44+09:00`, the record's main B), which every corrected stage checks.

---

### Task 9: The corrected G0 and G1, written into PREREG §5.6

**Files:**
- Create: `sector_leadlag_lab/results/corrected/g0.json`, `sector_leadlag_lab/results/corrected/g1.json`
- Modify: `sector_leadlag_lab/PREREG.md` (§5.6 only)

**Interfaces:**
- Consumes: the PREREG §5 commit and `corrections.json` (Task 8).
- Produces: `results/corrected/g0.json` (`selected`), `results/corrected/g1.json` (`pass`) and the PREREG commit made after G1 ran, which corrected main A requires.

- [ ] **Step 1: Run the corrected G0**

```bash
cd $WT && time $SLL run g0 --data corrected && $PY -c "
import json
g = json.load(open('sector_leadlag_lab/results/corrected/g0.json'))
m = g['meta']
print('selected', g['selected'], m['data'], m['prereg_has_section_5'], m['prereg_commit'][:7], m['corrections_sha256'][:12], m['dirty'])
for name, v in g['variants'].items():
    f = v['fit_a']
    print(name, round(v['original']['ar'], 4), round(f['beta_1e4'], 2), round(f['t'], 2), round(f['p'], 4), round(v['b1']['mean_ann'], 4), v['pass'])
"
```

Expected: `results/corrected/g0.json` is written with `data` `corrected`, `prereg_has_section_5` `True`, the §5 commit, the hash of Task 8 Step 2 and `dirty` `False`. If `selected` is `None`, the corrected data stop at G0 (`replication_failed`; the reading is `verdict_data_dependent`): skip Step 2, write §5.6 with the G0 lines and 「直したデータでは G0 で止まった（`replication_failed`）。本番 A・B と診断は回さない。」, commit as in Step 4, and go to Task 11.

- [ ] **Step 2: Run the corrected G1**

```bash
cd $WT && time $SLL run g1 --data corrected && $PY -c "
import json
g = json.load(open('sector_leadlag_lab/results/corrected/g1.json'))
print(g['variant'], g['significant'], g['count'], g['detected'], round(g['planted_beta_1e4'], 2), g['pass'])
"
```

Expected: `pass` is `True` (at most 2 of 20 rotated worlds significant). If it is `False`, the corrected data stop at G1 (`verdict_data_dependent`): write §5.6 with both results and 「直したデータでは G1 が不合格で止まった。本番 A・B と診断は回さない。」, commit as in Step 4, and go to Task 11.

- [ ] **Step 3: Write §5.6**

In `sector_leadlag_lab/PREREG.md`, replace the line 「- （直したデータで G1 を回したあとに書き足す。）」 with the following, filled from the two JSON files (rounded as shown; the record's values in brackets are from §4):

```markdown
- 直したデータの G0 で選んだ並べ方：`[g0.selected]`（記録は `same_date`。G0 の commit 時点の PREREG は [g0.meta.prereg_commit の先頭7文字]、corrections.json の SHA-256 の先頭12文字は [g0.meta.corrections_sha256 の先頭12文字]）。
- `same_date`：2015–2025 の AR [variants.same_date.original.ar を % で小数2桁]（記録 25.56%）、本番 A の ETF の係数 [fit_a.beta_1e4 小数2桁]×10⁻⁴（t=[fit_a.t 小数2桁]、p=[fit_a.p 小数4桁]。記録 3.99×10⁻⁴、t=7.23）、B1 の ETF のロング・ショートの年率 [b1.mean_ann を % で小数2桁]（記録 −125.38%）、合格 [pass を ○/×]。
- `lagged`：2015–2025 の AR [同じ形]（記録 28.38%）、本番 A の ETF の係数 [同じ形]（記録 4.49×10⁻⁴、t=8.21）、B1 の ETF のロング・ショートの年率 [同じ形]（記録 −113.66%）、合格 [○/×]。
- G1：有意になった回数 [g1.significant] / [g1.count]（合格 [g1.pass を ○/×]。記録 0 / 20）。検出力 [g1.detected] / [g1.count]（埋め込んだ係数 [g1.planted_beta_1e4 小数2桁]×10⁻⁴。記録 20 / 20、2.00×10⁻⁴）。
```

- [ ] **Step 4: Commit**

```bash
cd $WT && git add sector_leadlag_lab/PREREG.md sector_leadlag_lab/results/corrected/g0.json sector_leadlag_lab/results/corrected/g1.json && git commit -m "Record the corrected G0 and G1 and write them into PREREG §5"
```

Expected: one commit (with `g1.json` only when G1 ran), later than `g1.json`'s `meta.ran_at`, which `run main-a --data corrected` checks.

---

### Task 10: The corrected main A, main B (once) and diagnostics

**Files:**
- Create: `sector_leadlag_lab/results/corrected/main_a.json`, `sector_leadlag_lab/results/corrected/main_b.json`, `sector_leadlag_lab/results/corrected/main_b.lock`, `sector_leadlag_lab/results/corrected/diagnostics.json`

**Interfaces:**
- Consumes: Tasks 8–9.
- Produces: the corrected verdict (`results/corrected/main_b.json` → `verdict`, the first run), which PREREG §5.5 reads.

- [ ] **Step 1: Run the corrected main A and commit it before anything else**

```bash
cd $WT && time $SLL run main-a --data corrected && $PY -c "
import json
a = json.load(open('sector_leadlag_lab/results/corrected/main_a.json'))
print('H1', a['h1']['pass'], a['h1']['basket'], a['h1']['etf'], a['h1']['ratio_ci'])
print('H2', a['h2_pass'], {k: (round(v['cash']['mean_ann'], 4), round(v['cash']['p'], 4), round(v['spread']['mean_ann'], 4), round(v['spread']['p'], 4)) for k, v in a['h2'].items()})
print('robust', a['robust'], a['meta']['data'], a['meta']['corrections_sha256'][:12])
" && git add sector_leadlag_lab/results/corrected/main_a.json && git commit -m "Record the corrected main A"
```

Expected: `results/corrected/main_a.json` is written and committed.

- [ ] **Step 2: Run the corrected main B once and commit it with its lock**

```bash
cd $WT && time $SLL run main-b --data corrected && $PY -c "
import json
b = json.load(open('sector_leadlag_lab/results/corrected/main_b.json'))
print(b['verdict'], b['h3']['label'], b['h1']['basket'], b['evidence'], b['meta']['data'])
" && git add sector_leadlag_lab/results/corrected/main_b.json sector_leadlag_lab/results/corrected/main_b.lock && git commit -m "Record the corrected main B"
```

Expected: the verdict is one of `etf_only`, `real_then_decayed`, `usable`, `real_not_usable`. Do not run it again: a second run needs `--rerun-reason`, goes to `main_b_rerun_<n>.json`, and PREREG §5.5 reads the first one.

- [ ] **Step 3: Run the corrected diagnostics and commit them**

```bash
cd $WT && time $SLL run diagnostics --data corrected && git add sector_leadlag_lab/results/corrected/diagnostics.json && git commit -m "Record the corrected diagnostics"
```

Expected: `results/corrected/diagnostics.json` is written and committed.

---

### Task 11: The summary, the README, the knowledge note and every check

**Files:**
- Create: `sector_leadlag_lab/results/corrected/summary.md`
- Modify: `sector_leadlag_lab/README.md`, `docs/knowledge/2026-10-19-yfinance-japan-data-errors.md`, `docs/knowledge/README.md`

**Interfaces:**
- Consumes: every file under `results/corrected/` (Tasks 8–10) and `report.render_corrected` (Task 6).
- Produces: the write-up.

- [ ] **Step 1: Render the corrected summary and check the record's files**

```bash
cd $WT && $SLL report --data corrected && sed -n '1,220p' sector_leadlag_lab/results/corrected/summary.md && grep -ci nan sector_leadlag_lab/results/corrected/summary.md; git status --short sector_leadlag_lab && git diff --stat main -- sector_leadlag_lab/results ':(exclude)sector_leadlag_lab/results/corrected'
```

Expected: the reading line (`**`verdict_robust`**：…` or `**`verdict_data_dependent`**：…`; without a label only when the corrected data stopped before main B, where the line still says where it stopped), the corrections table with Task 8's counts, 「既知の誤り（設計書 §2）：すべて直った。」, the comparison table, the decomposition and the corrected sections; `0` lines with `nan`; the status lists only `?? sector_leadlag_lab/results/corrected/summary.md`; the diff of the record's results against main is empty.

- [ ] **Step 2: Write the README**

Edit `sector_leadlag_lab/README.md`. Copy every table and number from `results/corrected/summary.md`, and change nothing about the record's results. The text to insert is Japanese, as below.

1. Keep the opening conclusion paragraph (the one that starts 「**結論：判定は `usable`（本番 B の1回目、記録値）。**」). Under 「次の段階の前に確かめることが3つある」, the third bullet (the yfinance one) changes with the reading:
   - `verdict_robust`: delete that bullet, change 「3つ」 to 「2つ」, and add one paragraph after the bullets: 「yfinance の価格と配当の誤りと欠けを規則で直し、同じ snapshot で G0 の並べ方の選択から診断までを回し直しても（判定のあとの確認。PREREG §5）、判定は `usable` のままだった（`verdict_robust`）。」 followed by one or two sentences on how the pairing, H1's basket coefficient, H2's two means and main B's two means moved from the record, and a pointer to the section 「直したデータでの再計算」.
   - `verdict_data_dependent`: rewrite that bullet as 「yfinance の誤りと欠けを規則で直して回し直すと、判定は `[the corrected verdict, or where it stopped]` になった（`verdict_data_dependent`、PREREG §5）。変わった条件は [the conditions of the summary's reading line]。記録の判定は `usable` のまま変えない。」
2. In 「何を調べたか」, append to the last bullet (the spec, plan and PREREG one): 「直したデータでの再計算の設計書：`/home/kazumasa/projects/docs/superpowers/specs/2026-10-20-sector-leadlag-corrected-data-design.md`。実装計画：`/home/kazumasa/projects/docs/superpowers/plans/2026-10-20-sector-leadlag-corrected-data.md`。」
3. Between 「## 診断（判定には使わない）」 and 「## 限界」, add the section 「## 直したデータでの再計算（PREREG §5、判定のあと。判定は変えない）」 with:
   - one paragraph: 「G0 のデータの検査と最終レビューで見つかった yfinance の誤りと欠けを、規則で見つけて直し（PREREG §5.1 の C1〜C7）、同じ snapshot（`inputs_digest` が記録と同じ）で、G0 の並べ方の選択から診断までを回し直した。規則と読み方は、直したデータで何も計算する前に PREREG §5 に書いて commit した（[the first 7 characters of Task 8's commit]）。記録の判定と結果ファイルは変えていない。結果は `results/corrected/`。」
   - 「### 直したもの」: the summary's corrections table and its known-error line, and one line listing the nine C1 changes of PREREG §5.3.
   - 「### 読み方」: the summary's reading line as it is.
   - 「### 記録と並べた表」: the summary's comparison table as it is.
   - 「### 分解」: the summary's decomposition table as it is, with one sentence: 「記録の株の C2O・C2C は 8303 などの配当の誤りで読めず、直したデータで初めて読める。」
   - notes (bullets): 「規則は誤りを見たあとに決め、C4 は規則を実データに当てて改めた（どの時点でも、直したデータで段は回していない。PREREG §5.7）。」, 「2015-12-25 と 2016-07-11（営業日の欠け）は直していない。」, 「読み方は PREREG §5.5 のとおりで、記録の判定は `usable` のまま。」
4. In 「## 限界」:
   - change the first bullet's heading 「**yfinance の値の誤り（直していない）。**」 to 「**yfinance の値の誤り（記録では直していない）。**」, and append to the end of its list: 「判定のあとの確認（PREREG §5）では、これらを規則で直して手順を回し直した（「直したデータでの再計算」）。規則が見つけたほかの誤り（分割と同じ日の配当を分割前の1株あたりのまま記録した株が 9861・5401・8766 のほかにもあり、C4 で47件。8303 の上場廃止の期間（2023-09-27〜2025-12-17）の行と再上場（2025-12-18）。9201 の 2010 年の株価1〜5円の日と 2012 年の再上場）もそこに書いた。」
   - add a bullet: 「**日本の営業日の欠け。** 2015-12-25 と 2016-07-11 は東証が開いていたが、yfinance の株466銘柄のうち約450が出来高0・前日終値のままで、日本の営業日から外れている（ETF は取引あり）。本番 A が 2,735日で、減衰の論文の 2,737日より2日少ないのはこのため。次の営業日の ETF のシグナルの C2C と株の C2O・C2C が2日分になる。記録でも直したデータでも直していない。」
5. In 「## 再現手順」, add these lines to the code block after the `$SLL report` line, with each `[t]` replaced by the rounded `time` of Tasks 8–10, and change the test line's count to `113 passed, 1 skipped`:

```bash
# 直したデータでの再計算（PREREG §5。判定のあと。snapshot は取り直さない）
$SLL corrections                    # 約[t]秒。規則を当て、results/corrected/corrections.json を書く
# PREREG §5 と corrections.json を commit してから
$SLL run g0 --data corrected        # 約[t]秒。以下、記録と同じ順番でしか回らない
$SLL run g1 --data corrected        # 約[t]秒
# PREREG §5.6 に直した G0 と G1 を書き足し、g0.json・g1.json と一緒に commit してから
$SLL run main-a --data corrected    # 約[t]秒
# results/corrected/main_a.json を commit してから
$SLL run main-b --data corrected    # 約[t]秒。1回だけ（results/corrected/main_b.lock）
$SLL run diagnostics --data corrected   # 約[t]秒
$SLL report --data corrected        # results/corrected/summary.md
```

   and add a bullet below the block: 「直したデータのどの段も、生データが記録の本番 B と同じ snapshot であること、PREREG §5 が記録の本番 B のあとに commit されていること、`results/corrected/corrections.json` が既知の誤りの確認に通り、いまの規則の一覧と同じことを求める。」

- [ ] **Step 3: Update the knowledge note**

Edit `docs/knowledge/2026-10-19-yfinance-japan-data-errors.md` (Japanese):

1. After the first sentence of the opening paragraph (「確認日: 2026-10-19（日本時間）。」), insert 「追記: 2026-10-20（規則を当てて見つけた誤りと、直し方）。」
2. Append three rows to the table under 「## 見つかった誤り」:

```markdown
| TOPIX500 の株（8377・7282・9065・2433・5706 など） | 分割と同じ日の配当を、分割前の1株あたりのまま記録している（2009〜2026年の分割と同じ日の配当320件のうち47件。9861・5401・8766 もこの型） | その日の配当込みの C2O・C2C が大きすぎる |
| 8303 | 上場廃止の期間（2023-09-27〜2025-12-17）の行が、前の終値の約2,000万倍の価格・出来高0のまま並ぶ。再上場（2025-12-18）で戻る | 再上場の日の C2O・C2C が約 −100% |
| 東証の 2015-12-25・2016-07-11 | 株466銘柄のうち約450が出来高0・前日終値のまま（ETF は取引あり） | 出来高で営業日を決めると、その2日が営業日から外れる |
```

3. Append to 「## 見つけ方」: 「分割と同じ日の配当は、その系列の直前の配当と、その日の始値の下落（株の中央値の配当込みの C2O との差）の両方で見る。下落だけで決めると誤る。3月と9月は株がいっせいに権利落ちするので中央値の下落にふつうの配当が入り、1銘柄の朝の値動き（±1〜2%）が配当利回りの差より大きい（320件のうち193件を割ってしまう）。」
4. After the first bullet of 「## 扱い」, insert: 「判定のあとの確認（`sector_leadlag_lab/PREREG.md` §5、2026-10-20）では、規則（C1〜C7）で直し、同じ snapshot で手順をそっくり回し直した。直したのは376件。結果は [the summary's reading label and the corrected verdict]（`/home/kazumasa/projects/sector_leadlag_lab/results/corrected/summary.md`、README の「直したデータでの再計算」）。」

In `docs/knowledge/README.md`, change the end of the yfinance line from 「— NEXT FUNDS の配当の日付のずれ・1629.T の分割と価格の誤り・8303 の配当・行の欠けと、その見つけ方」 to 「— NEXT FUNDS の配当の日付のずれ・1629.T の分割と価格の誤り・8303 の配当・分割の日の配当・行と営業日の欠けと、その見つけ方と直し方」.

- [ ] **Step 4: Run every check**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
cd $WT && $PY -m pytest sector_leadlag_lab/tests -q
cd $WT && $PY -m pytest --collect-only -q 2>&1 | tail -3
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab
cd $WT && git diff --numstat main -- sector_leadlag_lab/PREREG.md
```

Expected: `113 passed, 1 skipped` with both the member config and the root config; the workspace collection ends without errors; ruff clean; PREREG.md shows `0` removed lines against main.

- [ ] **Step 5: Commit**

```bash
cd $WT && git add sector_leadlag_lab/README.md sector_leadlag_lab/results/corrected/summary.md docs/knowledge/2026-10-19-yfinance-japan-data-errors.md docs/knowledge/README.md && git commit -m "Write up the corrected-data rerun beside the record"
```

Do not merge or push. Report to the user: the reading label and the corrected verdict with the conditions that changed, the pairing, H1, H2, main B, H3 and the decomposition beside the record, the 376 corrections, and anything that differed from this plan. After the user approves the merge, run `uv sync` and `make test` in the main checkout `/home/kazumasa/projects` (never in the worktree), and check `git status --ignored` and `du -sh` of the worktree before removing anything.
