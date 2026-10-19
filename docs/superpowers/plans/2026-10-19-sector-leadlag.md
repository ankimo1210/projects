# US–Japan Sector Lead-Lag Falsification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide whether the published PCA SUB lead-lag signal (US sector ETFs → the next Japanese session) predicts the open-to-close returns of tradable TOPIX500 sector baskets, and whether a cash-only long version beats cash and the all-sector basket, following the falsification-first design of 2026-10-19.

**Architecture:** A new workspace member `sector_leadlag_lab` (package `sector_leadlag`). Data modules snapshot the JPX listed-issues file and yfinance daily histories (11 Select Sector SPDRs, 17 NEXT FUNDS TOPIX-17 ETFs, the TOPIX500 stocks) into a raw store. `timing`, `pit`, `signal`, `baskets`, `strategy`, `evaluate` and `synthetic` implement the design's calendars and pairings, the R1/R2 checks, PCA SUB, the baskets, the strategies, the tests and the synthetic worlds as small pure modules. `study` assembles the panels, `stages` holds the shared builders, and `g0`, `g1`, `main` and `diagnostics` run the stages; each stage writes one JSON file under `sector_leadlag_lab/results/`. The CLI enforces the stage order, the PREREG commits and the one-shot main-B lock.

**Tech Stack:** Python 3.12, numpy 2.4, pandas 3.0, scipy 1.17, yfinance 1.5, httpx, openpyxl, click, macrokit (workspace), pytest 9, ruff.

**Spec:** `/home/kazumasa/projects/docs/superpowers/specs/2026-10-19-sector-leadlag-design.md` (approved section by section on 2026-10-19; §5.2 was revised while this plan was written, before anything relating the signal to prices was computed — see the spec's §15 and decision D1).

## Global Constraints

- Worktree `WT=/home/kazumasa/worktrees/sector-leadlag`, branch `claude/sector-leadlag-lab`, created from `main` after this plan is committed. The spec and this plan live on `main`. Merge and push only with the user's approval.
- New workspace member `sector_leadlag_lab`, Python package `sector_leadlag`. Dependencies: macrokit (workspace), click, httpx, numpy, openpyxl, pandas, scipy, yfinance — all already in the workspace lock (spec §10). No new third-party package.
- Raw data outside Git: `/home/kazumasa/projects/_data/sector_leadlag_lab/raw/` (override with `SECTOR_LEADLAG_RAW`), written only through macrokit `save_snapshot` (manifest with SHA-256, URL, fetch time). Every result comes from that snapshot (spec §4).
- Git keeps code, `PREREG.md`, `README.md`, `results/*.json`, `results/main_b.lock` and `results/summary.md`. No intermediate arrays are saved; they are rebuilt from the snapshot and fixed seeds.
- Units: daily simple returns as decimals; annualised means ×252 (`mean_ann`); the strategy paper's AR is monthly compounded returns ×12 (`ar`); panel coefficients are reported ×1e-4 (`beta_1e4`), as in the decay paper; money in yen.
- Fixed values (spec §3, §6, §7, §8): λ = 0.9, K = 3, window 60 rows, q = 0.3, C_full 2010-01-01..2014-12-31; H1 basket weights = median traded value over the 60 trading days before d; H1 secondary = top 10 equal weights; H2 = top 5 sectors × 3 names, lot 100, capital 5,000,000 yen (3,000,000 and 10,000,000 for robustness), budget capital/15 per name, costs 0 bp (2 bp robustness, 5 bp reported); stationary bootstrap mean block 20, 10,000 draws, seed 20261019; one-sided 5 %; G1 20 rotations of at least 60 days, pass ≤ 2/20; power plant 0.5 β_ETF. Periods: A 2015-01-05..2026-03-18, B 2026-03-19..2026-10-05 (B1 to 07-23, B2 from 07-24), C from 2026-10-06; AR comparison span 2015-01-01..2025-12-31.
- Python command (the shared venv; `PYTHONPATH` makes the worktree code win; single-thread BLAS): `PY="env PYTHONPATH=$WT/sector_leadlag_lab/src:$WT/macrokit/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python -P"`. CLI: `SLL="$PY -m sector_leadlag.cli"`. Never run `uv sync` or `uv run` in the worktree; run `uv lock` only from `$WT`.
- Never write the lock file's name (or `.env`) as a shell argument: the permission rules reject the whole command. Stage it with `git add -u` inside the worktree and inspect it with a bare `git diff --stat`.
- Tests: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`. Tests never touch the network; the one network test runs only with `SECTOR_LEADLAG_NETWORK=1`.
- Lint: `cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab` (root ruff config: line length 100, `select = ["E","W","F","I","B","UP","N","RUF"]`; Task 1 adds `N803`, `N806`, `N816`, `E741` ignores for `sector_leadlag_lab/**/*.py`). B905: every `zip()` needs `strict=`. RUF043: a regex with metacharacters in `match=` must be a raw string. Run `ruff check --fix` and `ruff format` before each commit.
- Commit messages: English, imperative, no `feat:` prefix, ending with the executing session's attribution lines.
- Docs (`PREREG.md`, `README.md`) are Japanese; code, identifiers and commit messages are English.
- Stage order (spec §3.5), enforced by the CLI: `snapshot` → commit `PREREG.md` → `g0` → `g1` (must pass) → write the chosen pairing and the G1 result into `PREREG.md` and commit → `main-a` → commit `results/main_a.json` → `main-b` (once; a rerun needs `--rerun-reason` and never replaces the verdict of record) → `diagnostics` → `report`.
- Before main A, nothing may relate the true signal to stock returns. G0 uses stock prices only for the data checks; G1 uses them only with rotated US returns.

## Decisions this plan makes (the spec leaves them open)

PREREG §3 copies these in Japanese.

- **D1 Pairings** (spec §5.2 as revised): `same_date` (rows are the days both markets traded, each paired with itself) and `lagged` (each Japanese day d′ paired with the US day s(d′)). G0 computes both; of those that pass (ETF β in A > 0 at one-sided 5 %, and the B1 ETF long-short mean < 0) it takes the one whose 2015-01..2025-12 monthly AR is closest to 23.79 %; a tie goes to `same_date`. If neither passes, G0 writes `replication_failed` and every later stage refuses to run.
- **D2 Evaluation days:** every Japanese trading day d with s(d) and a full window. By the yfinance calendar A has 2,735 days (the decay paper: 2,737; common days only: 2,642) and B1 has 85 (as in the decay paper).
- **D3 Calendars:** a Japanese trading day is one on which at least half of the TOPIX500 names listed at the time (first row to last row) traded; a US trading day is one on which XLK traded. Each market's C2C runs from its own previous trading day.
- **D4 Unusable columns:** a window column with a missing value or zero variance (an ETF before its launch) gets z = 0 and correlation 0 in that window, and its z_U,s(d) is 0.
- **D5 Prices:** the signal's Japanese side is the ETF C2C from Adj Close. O2C, C2O and C2C of ETFs and stocks use the split-adjusted Open and Close plus the dividend going ex (spec §7.3). A day without trades has no return.
- **D6 Ranking:** n = ⌊0.3·|J_d| + 1e-9⌋ per side; equal signals rank the lower sector code first; a day whose signal is equal across sectors takes no position (long-short and H2). The ETF J_d is the ETFs that traded that day (the paper's rule); for the baskets J_d is all 17.
- **D7 Panel regression:** fixed effects removed by alternating projections; standard errors clustered by day with G/(G−1)·(N−1)/(N−K), K = regressors + sectors − 1; one-sided p from t with G−1 degrees of freedom; sz standardised over the 17 sectors with ddof = 0; an ETF without trades that day drops out as an observation.
- **D8 Ratio interval:** the per-day sums of x·y and x² after the fixed effects, resampled on the days both fits share by the stationary bootstrap; the 2.5 % and 97.5 % points of the ratio of the two resampled slopes; the fixed effects stay at their estimates.
- **D9 Mean tests:** centred stationary bootstrap, p = (1 + #{m* − m ≥ m}) / (B + 1); draws in chunks of 500.
- **D10 Cash strategy:** share counts from the previous day's quoted close (yfinance's split adjustment undone); profit from the quoted open and close; a name that does not trade on d is not bought; unspent money earns 0; costs are cost_bp of the traded value on each leg.
- **D11 Robustness ③:** the means of H2 1 and H2 2 keep the base run's sign in three runs that each change one thing: 2 bp, 3 million yen, 10 million yen.
- **D12 H3:** t tests on the daily returns as they are (no autocorrelation correction), as spec §3.3 says.
- **D13 G1:** rotate the rows of the US C2C frame by k US trading days, k drawn uniformly from [60, n − 60) with seed 20261019 (20 values); rebuild the whole signal, C_full included. Power: add 0.5 × β_ETF (A, chosen pairing, from G0) × sz of the rotated signal to the basket O2C.
- **D14 G0 data checks:** zero-volume days summarised per ETF (days, share, share that kept the previous close) instead of a day-by-day list; outliers (|O2C| or |C2O| > 20 %) counted with the 100 largest listed, never removed; a split whose ex-date C2O exceeds 20 % in absolute value is flagged.
- **D15 Stale-open diagnostic:** a replaced name's O2C becomes its price C2C (no dividend); random 10 % and 20 % of the names each day, and the 10 % (rounded up) with the largest |C2O|.
- **D16 Placebo (h = 85):** pseudo dates τ inside A from the 251st day to the last that leaves 85 days; statistic mean(τ..τ+84) − mean(before τ); the actual one is mean(first 85 days of B1) − mean(A).
- **D17 Main B** needs `results/main_a.json` committed (spec §3.5 "記録してから").

## Review Focus

- A TOPIX500 stock whose download fails, or whose code has letters (285A): the snapshot lists it and goes on, and the study runs without it and names it as missing; a failing sector ETF stops the snapshot (Task 2 test `test_parse_keeps_stocks_with_a_sector_and_their_size`, Task 3 test `test_a_failing_stock_is_listed_and_a_failing_etf_stops_the_snapshot`, Task 10 test `test_the_study_puts_every_series_on_the_japanese_days`).
- A Japanese holiday on which yfinance still returns a row for one stock, and a stock delisted partway: neither changes the trading calendar (Task 4 test `test_a_day_counts_when_half_of_the_listed_stocks_traded`).
- Running a stage before PREREG is committed, main A before the chosen pairing and G1 are in a newer PREREG commit, main B before main A's result is committed, or main B twice: refused with a message that says why (Task 15 tests `test_every_stage_needs_a_committed_prereg`, `test_main_a_needs_a_passed_g1_and_a_prereg_commit_after_it`, `test_main_b_needs_main_a_committed`, `test_main_b_runs_once_without_a_reason`).
- ETF values after 2026-07-23 must not change anything G0 writes (Task 11 test `test_g0_reads_no_etf_value_after_b1`).
- A period or check with nothing in it — no dividend events, a reference period C of a few days, a sector whose lots do not fit the budget: the summary shows "—", the money stays cash, never `nan` or a crash (Task 7 test `test_cash_long_skips_a_name_whose_lot_does_not_fit`, Task 10 test `test_a_period_without_enough_days_gets_no_regression`, Task 16 test `test_the_summary_has_every_section`).

## File Structure

| Path (under `sector_leadlag_lab/`) | Responsibility |
|---|---|
| `pyproject.toml` | member metadata, `sector-leadlag` script, pytest config |
| `src/sector_leadlag/data/store.py` | raw store root, `fetch`, `store_bytes`, `read_latest`, manifest records |
| `src/sector_leadlag/data/jpx.py` | JPX `data_j.xlsx`: 17 sectors, size classes, TOPIX500, ETF tickers |
| `src/sector_leadlag/data/yf.py` | yfinance history → CSV without an unfinished day; retries |
| `src/sector_leadlag/data/snapshot.py` | fetch the listing and every history into the store |
| `src/sector_leadlag/timing.py` | trading days, s(d), close-to-close on a calendar, the two pairings |
| `src/sector_leadlag/pit.py` | R1 and R2 checks (G2) |
| `src/sector_leadlag/signal.py` | prior subspace, C_full, C0, PCA SUB, momentum, sz, long-short, top sectors |
| `src/sector_leadlag/baskets.py` | `Panel`, O2C/C2O/C2C, quoted prices, trailing value, H1 weights, H2 picks, basket returns |
| `src/sector_leadlag/strategy.py` | the paper's long-short returns, the cash-only strategy, the selection spread |
| `src/sector_leadlag/evaluate.py` | panel regression, stationary bootstrap, ratio interval, mean test, metrics, H3, verdict |
| `src/sector_leadlag/synthetic.py` | G1 rotations, the planted effect, stale opens |
| `src/sector_leadlag/study.py` | periods; loads every input into a `Study` |
| `src/sector_leadlag/stages.py` | shared builders: signal of a pairing, returns, baskets, long-shorts, fits, H2 series |
| `src/sector_leadlag/g0.py` | G0: data checks and the ETF replication that picks the pairing |
| `src/sector_leadlag/g1.py` | G1: rotated worlds and power |
| `src/sector_leadlag/main.py` | main A (H1, H2, robustness) and main B (period B, H3, verdict) |
| `src/sector_leadlag/diagnostics.py` | spec §9 diagnostics |
| `src/sector_leadlag/cli.py` | `snapshot`, `run <stage>`, `inputs`, `report`; stage order and the main-B lock |
| `src/sector_leadlag/report.py` | markdown tables from the results JSON |
| `tests/conftest.py`, `tests/test_*.py` | fixtures (listing workbook, yfinance frames, panels, synthetic worlds) and one test file per module, network-free |
| `PREREG.md`, `README.md`, `results/` | pre-registration, write-up, results |

Root files touched: `/home/kazumasa/projects/pyproject.toml` (workspace member, testpaths, ruff per-file ignores) and the workspace lock file.

---
### Task 1: Worktree, member scaffold and the raw store

**Files:**
- Create: `sector_leadlag_lab/pyproject.toml`, `sector_leadlag_lab/src/sector_leadlag/__init__.py`, `sector_leadlag_lab/src/sector_leadlag/data/__init__.py`, `sector_leadlag_lab/src/sector_leadlag/data/store.py`
- Modify: `pyproject.toml` (root: `[tool.uv.workspace] members`, `[tool.ruff.lint.per-file-ignores]`, `[tool.pytest.ini_options] testpaths`), the workspace lock file
- Test: `sector_leadlag_lab/tests/test_store.py`

**Interfaces:**
- Consumes: `macrokit.snapshot.save_snapshot(root, source, indicator, content, *, ingested_at, url, http_status, filename) -> SnapshotResult`, `macrokit.snapshot.latest_payload(root, source, indicator) -> Path | None`.
- Produces: `sector_leadlag.data.store.RAW_ROOT: Path`, `USER_AGENT: str`, `FetchError(RuntimeError)`, `fetch(url: str, *, timeout: float = 120.0) -> bytes`, `store_bytes(root: Path, source: str, indicator: str, content: bytes, *, url: str, filename: str) -> SnapshotResult`, `read_latest(root: Path, source: str, indicator: str) -> bytes` (FileNotFoundError naming `sector-leadlag snapshot`), `manifest_records(root: Path) -> dict[str, dict]` (key `"source/indicator"` → `sha256`, `ingested_at`, `url`, `path` of the newest stored record, sorted by key), `indicators(root: Path, source: str) -> list[str]`.

- [ ] **Step 1: Create the worktree**

```bash
cd /home/kazumasa/projects && git status --short && git worktree add /home/kazumasa/worktrees/sector-leadlag -b claude/sector-leadlag-lab main
```

Expected: `Preparing worktree (new branch 'claude/sector-leadlag-lab')`. Other sessions' uncommitted files in the main checkout stay where they are; the worktree starts clean.

- [ ] **Step 2: Write the member metadata and package markers**

File: `sector_leadlag_lab/pyproject.toml` (create)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "sector-leadlag-lab"
version = "0.1.0"
description = "Falsification test of the US-Japan sector lead-lag (PCA SUB) on tradable stock baskets"
requires-python = ">=3.12"
dependencies = [
    "macrokit",
    "click>=8.1",
    "httpx>=0.27",
    "numpy>=1.26",
    "openpyxl>=3.1",
    "pandas>=2.2",
    "scipy>=1.13",
    "yfinance>=0.2.50",
]

[project.scripts]
sector-leadlag = "sector_leadlag.cli:main"

[tool.uv.sources]
macrokit = { workspace = true }

[tool.hatch.build.targets.wheel]
packages = ["src/sector_leadlag"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --import-mode=importlib"
```

File: `sector_leadlag_lab/src/sector_leadlag/__init__.py` (create)

```python
"""US-Japan sector lead-lag: does PCA SUB predict tradable stock baskets? (design 2026-10-19)."""
```

File: `sector_leadlag_lab/src/sector_leadlag/data/__init__.py` (create)

```python
"""Raw inputs: the TSE listed-issues file and daily prices from yfinance."""
```

- [ ] **Step 3: Write the failing test**

File: `sector_leadlag_lab/tests/test_store.py` (create)

```python
from pathlib import Path

import pytest
from sector_leadlag.data.store import indicators, manifest_records, read_latest, store_bytes


def test_store_and_read_back(tmp_path: Path):
    store_bytes(tmp_path, "yf", "XLK", b"a,b\n", url="yfinance:XLK", filename="XLK.csv")
    store_bytes(tmp_path, "yf", "1617.T", b"c\n", url="yfinance:1617.T", filename="1617.T.csv")
    store_bytes(tmp_path, "jpx", "data_j", b"x", url="https://example.invalid", filename="d.xlsx")
    assert read_latest(tmp_path, "yf", "XLK") == b"a,b\n"
    assert indicators(tmp_path, "yf") == ["1617.T", "XLK"]
    assert indicators(tmp_path, "etf") == []
    records = manifest_records(tmp_path)
    assert list(records) == ["jpx/data_j", "yf/1617.T", "yf/XLK"]
    assert len(records["yf/XLK"]["sha256"]) == 64


def test_read_latest_names_the_missing_snapshot(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="sector-leadlag snapshot"):
        read_latest(tmp_path, "yf", "XLK")
```

- [ ] **Step 4: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_store.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.data.store'`.

- [ ] **Step 5: Write the store**

File: `sector_leadlag_lab/src/sector_leadlag/data/store.py` (create)

```python
"""Where raw snapshots live, and how they are fetched and read back (design §4)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
from macrokit.snapshot import SnapshotResult, latest_payload, save_snapshot

RAW_ROOT = Path(
    os.environ.get("SECTOR_LEADLAG_RAW", "/home/kazumasa/projects/_data/sector_leadlag_lab/raw")
)
USER_AGENT = "Mozilla/5.0 (compatible; macrokit research)"


class FetchError(RuntimeError):
    """A remote file could not be fetched."""


def fetch(url: str, *, timeout: float = 120.0) -> bytes:
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
            f"no stored snapshot for {source}/{indicator} under {root}; run `sector-leadlag snapshot`"
        )
    return path.read_bytes()


def manifest_records(root: Path) -> dict[str, dict]:
    """The newest stored record of every indicator, keyed ``source/indicator``."""
    manifest = root / "manifest.jsonl"
    records: dict[str, dict] = {}
    if not manifest.exists():
        return records
    for line in manifest.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a blank or truncated line, as in macrokit.snapshot
        if record.get("path"):
            records[f"{record['source']}/{record['indicator']}"] = {
                name: record.get(name) for name in ("sha256", "ingested_at", "url", "path")
            }
    return dict(sorted(records.items()))


def indicators(root: Path, source: str) -> list[str]:
    """Indicators of ``source`` with at least one stored payload."""
    prefix = f"{source}/"
    return [key[len(prefix) :] for key in manifest_records(root) if key.startswith(prefix)]
```

- [ ] **Step 6: Run the test to see it pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_store.py -q`
Expected: `2 passed`.

- [ ] **Step 7: Register the member in the workspace and relock**

In `$WT/pyproject.toml`: add `"sector_leadlag_lab",` right after `"bond_timing_lab",` in `[tool.uv.workspace] members`; under `[tool.ruff.lint.per-file-ignores]` add, right after the `bond_timing_lab` line,

```toml
"sector_leadlag_lab/**/*.py" = ["N803", "N806", "N816", "E741"]
```

and add `"sector_leadlag_lab/tests",` right after `"bond_timing_lab/tests",` in `[tool.pytest.ini_options] testpaths`. Then:

```bash
cd $WT && uv lock && git diff --stat
```

Expected: `pyproject.toml` changes by 3 lines and the lock file gains the `sector-leadlag-lab` entry only (a few lines). If `uv lock` wants to change any other package's version, stop and report.

- [ ] **Step 8: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git add -u && git commit -m "Add the sector_leadlag_lab workspace member and its raw store"
```

---

### Task 2: The JPX listing and yfinance histories

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/data/jpx.py`, `sector_leadlag_lab/src/sector_leadlag/data/yf.py`, `sector_leadlag_lab/tests/conftest.py`
- Test: `sector_leadlag_lab/tests/test_jpx.py`, `sector_leadlag_lab/tests/test_yf.py`

**Interfaces:**
- Consumes: `store.FetchError` (Task 1).
- Produces:
  - `sector_leadlag.data.jpx`: `URL: str`, `COLUMNS: tuple[str, ...]` (the 10 workbook columns), `SECTORS: tuple[str, ...]` (17 names; code k is `SECTORS[k - 1]`), `ETF_TICKERS = ("1617.T", …, "1633.T")`, `TOPIX500 = ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400")`, `Listing(as_of: date, stocks: pd.DataFrame)` (index `code` as str; columns `name`, `sector` int 1–17, `size`), `parse_listing(content: bytes) -> Listing` (ValueError on a missing column or a code whose name does not match), `topix500(listing: Listing) -> pd.DataFrame`, `stock_ticker(code: str) -> str`.
  - `sector_leadlag.data.yf`: `US_SECTORS` (the 11 SPDR tickers in alphabetical order), `COLUMNS = ("open", "high", "low", "close", "adj_close", "volume", "dividends", "splits")`, `COMPLETE_AFTER = time(18, 0)`, `market_of(ticker: str) -> str` (`"jp"` for `.T`, else `"us"`), `complete_through(fetched_at: datetime, market: str) -> date`, `to_csv(history: pd.DataFrame, through: date) -> bytes`, `download(ticker: str, *, fetched_at: datetime | None = None, attempts: int = 4, history=..., sleep=...) -> bytes` (FetchError naming the ticker after the last attempt), `parse_csv(content: bytes) -> pd.DataFrame` (float columns `COLUMNS`, DatetimeIndex `date`).
  - Fixtures in `tests/conftest.py`: `listing_bytes(rows: list[tuple[str, int, str]], stamp: str = "20260930") -> bytes` (a workbook in the JPX layout; a row is (code, sector or 0 for a non-stock, size)) and `yf_history(dates, *, open_, close, volume=None, dividends=None, splits=None, adj_close=None, tz="Asia/Tokyo") -> pd.DataFrame` (the yfinance `history(auto_adjust=False, actions=True)` layout).

Facts behind these modules (checked 2026-10-19): `data_j.xlsx` dated 20260930 has 4,447 rows, 3,897 with a 17-sector code, and 491 TOPIX500 names (31 + 68 + 392), at least 4 per sector; three codes have letters (e.g. 285A). yfinance's OHLC and volume are split-adjusted backward (7203's 1:5 split on 2021-09-29: the 2021-09-28 close shows 2,077, quoted 10,385), `Dividends` sit on the ex-date, and the index is tz-aware in the exchange's zone.

- [ ] **Step 1: Write the fixtures and the failing tests**

File: `sector_leadlag_lab/tests/conftest.py` (create)

```python
"""Shared builders for the tests. Nothing here touches the network."""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.data.jpx import COLUMNS, SECTORS


def _listing_bytes(rows: list[tuple[str, int, str]], stamp: str = "20260930") -> bytes:
    """A listed-issues workbook in the JPX layout; ``rows`` are (code, sector or 0, size)."""
    records = []
    for code, sector, size in rows:
        records.append(
            {
                "日付": stamp,
                "コード": code,
                "銘柄名": f"name {code}",
                "市場・商品区分": "プライム（内国株式）" if sector else "ETF・ETN",
                "33業種コード": "50" if sector else "-",
                "33業種区分": "水産・農林業" if sector else "-",
                "17業種コード": str(sector) if sector else "-",
                "17業種区分": SECTORS[sector - 1] if sector else "-",
                "規模コード": "1" if sector else "-",
                "規模区分": size if sector else "-",
            }
        )
    buffer = io.BytesIO()
    pd.DataFrame(records, columns=list(COLUMNS)).to_excel(buffer, index=False)
    return buffer.getvalue()


@pytest.fixture
def listing_bytes():
    return _listing_bytes


def _history(
    dates,
    *,
    open_,
    close,
    volume=None,
    dividends=None,
    splits=None,
    adj_close=None,
    tz: str = "Asia/Tokyo",
) -> pd.DataFrame:
    """A frame in the yfinance ``history(auto_adjust=False, actions=True)`` layout."""
    index = pd.DatetimeIndex(pd.to_datetime(list(dates))).tz_localize(tz)
    n = len(index)
    open_ = np.asarray(open_, dtype=float)
    close = np.asarray(close, dtype=float)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": np.maximum(open_, close),
            "Low": np.minimum(open_, close),
            "Close": close,
            "Adj Close": close if adj_close is None else np.asarray(adj_close, dtype=float),
            "Volume": np.full(n, 1000.0) if volume is None else np.asarray(volume, dtype=float),
            "Dividends": np.zeros(n) if dividends is None else np.asarray(dividends, dtype=float),
            "Stock Splits": np.zeros(n) if splits is None else np.asarray(splits, dtype=float),
            "Capital Gains": np.zeros(n),
        },
        index=index,
    )


@pytest.fixture
def yf_history():
    return _history
```

File: `sector_leadlag_lab/tests/test_jpx.py` (create)

```python
import io
from datetime import date

import pandas as pd
import pytest
from sector_leadlag.data.jpx import ETF_TICKERS, parse_listing, stock_ticker, topix500


def test_parse_keeps_stocks_with_a_sector_and_their_size(listing_bytes):
    content = listing_bytes(
        [
            ("1301", 1, "TOPIX Small 1"),
            ("7203", 6, "TOPIX Core30"),
            ("285A", 9, "TOPIX Mid400"),
            ("1617", 0, ""),
        ]
    )
    listing = parse_listing(content)
    assert listing.as_of == date(2026, 9, 30)
    assert list(listing.stocks.index) == ["1301", "7203", "285A"]
    assert listing.stocks.loc["7203", "sector"] == 6
    assert list(topix500(listing).index) == ["7203", "285A"]
    assert stock_ticker("285A") == "285A.T"


def test_etf_tickers_follow_the_sector_codes():
    assert (ETF_TICKERS[0], ETF_TICKERS[16], len(ETF_TICKERS)) == ("1617.T", "1633.T", 17)


def test_a_reshuffled_sector_code_is_refused(listing_bytes):
    frame = pd.read_excel(io.BytesIO(listing_bytes([("7203", 6, "TOPIX Core30")])), dtype=str)
    frame.loc[0, "17業種区分"] = "食品"
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    with pytest.raises(ValueError, match="17-sector code 6"):
        parse_listing(buffer.getvalue())
```

File: `sector_leadlag_lab/tests/test_yf.py` (create)

```python
from datetime import UTC, date, datetime

import pandas as pd
import pytest
from sector_leadlag.data.store import FetchError
from sector_leadlag.data.yf import complete_through, download, parse_csv, to_csv


def test_complete_through_waits_for_the_evening_of_each_market():
    morning_tokyo = datetime(2026, 10, 19, 1, 0, tzinfo=UTC)  # 10:00 JST, 21:00 EDT on the 18th
    assert complete_through(morning_tokyo, "jp") == date(2026, 10, 18)
    assert complete_through(morning_tokyo, "us") == date(2026, 10, 18)
    evening_tokyo = datetime(2026, 10, 19, 10, 0, tzinfo=UTC)  # 19:00 JST, 06:00 EDT
    assert complete_through(evening_tokyo, "jp") == date(2026, 10, 19)
    assert complete_through(evening_tokyo, "us") == date(2026, 10, 18)


def test_csv_keeps_the_local_date_and_drops_an_unfinished_day(yf_history):
    history = yf_history(
        ["2026-10-15", "2026-10-16", "2026-10-19"],
        open_=[100, 101, 102],
        close=[101, 102, 103],
        dividends=[0, 5, 0],
        splits=[0, 0, 2],
    )
    frame = parse_csv(to_csv(history, date(2026, 10, 16)))
    assert list(frame.index) == [pd.Timestamp("2026-10-15"), pd.Timestamp("2026-10-16")]
    assert list(frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "dividends",
        "splits",
    ]
    assert frame.loc["2026-10-16", "dividends"] == 5.0


def test_download_retries_then_names_the_ticker(yf_history):
    calls: list[str] = []

    def empty(ticker: str) -> pd.DataFrame:
        calls.append(ticker)
        return pd.DataFrame()

    with pytest.raises(FetchError, match=r"1617\.T"):
        download("1617.T", attempts=3, history=empty, sleep=lambda _: None)
    assert calls == ["1617.T"] * 3

    good = yf_history(["2026-10-15"], open_=[1.0], close=[2.0], tz="America/New_York")
    content = download(
        "XLK",
        fetched_at=datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        history=lambda _: good,
        sleep=lambda _: None,
    )
    assert parse_csv(content)["close"].tolist() == [2.0]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_jpx.py sector_leadlag_lab/tests/test_yf.py -q`
Expected: ERROR — `ImportError while loading conftest` (`No module named 'sector_leadlag.data.jpx'`).

- [ ] **Step 3: Write the two modules**

File: `sector_leadlag_lab/src/sector_leadlag/data/jpx.py` (create)

```python
"""The TSE listed-issues file (JPX ``data_j.xlsx``): 17-sector and size classes (design §4)."""

from __future__ import annotations

import io
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime

import pandas as pd

URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xlsx"
COLUMNS = (
    "日付",
    "コード",
    "銘柄名",
    "市場・商品区分",
    "33業種コード",
    "33業種区分",
    "17業種コード",
    "17業種区分",
    "規模コード",
    "規模区分",
)
# JPX 17-sector code k (1-17) is SECTORS[k - 1]; its NEXT FUNDS ETF is 1616 + k.
SECTORS = (
    "食品",
    "エネルギー資源",
    "建設・資材",
    "素材・化学",
    "医薬品",
    "自動車・輸送機",
    "鉄鋼・非鉄",
    "機械",
    "電機・精密",
    "情報通信・サービスその他",
    "電力・ガス",
    "運輸・物流",
    "商社・卸売",
    "小売",
    "銀行",
    "金融（除く銀行）",
    "不動産",
)
ETF_TICKERS = tuple(f"{1616 + k}.T" for k in range(1, 18))
TOPIX500 = ("TOPIX Core30", "TOPIX Large70", "TOPIX Mid400")


def _norm(text: str) -> str:
    return unicodedata.normalize("NFKC", str(text)).strip()


@dataclass(frozen=True)
class Listing:
    as_of: date
    stocks: pd.DataFrame  # index: code (str); columns: name, sector (1-17), size


def parse_listing(content: bytes) -> Listing:
    frame = pd.read_excel(io.BytesIO(content), dtype=str)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"the listed-issues file lacks columns {missing}")
    as_of = datetime.strptime(frame["日付"].dropna().iloc[0].strip(), "%Y%m%d").date()
    rows = frame[frame["17業種コード"].fillna("").str.strip().str.fullmatch(r"\d{1,2}")]
    sector = rows["17業種コード"].str.strip().astype(int).to_numpy()
    expected = {k + 1: _norm(name) for k, name in enumerate(SECTORS)}
    for k, name in zip(sector, rows["17業種区分"], strict=True):
        if expected.get(int(k)) != _norm(name):
            raise ValueError(f"17-sector code {k} is {name!r}, expected {expected.get(int(k))!r}")
    stocks = pd.DataFrame(
        {
            "name": rows["銘柄名"].str.strip().to_numpy(),
            "sector": sector,
            "size": rows["規模区分"].fillna("").str.strip().to_numpy(),
        },
        index=pd.Index(rows["コード"].str.strip().to_numpy(), name="code"),
    )
    return Listing(as_of, stocks)


def topix500(listing: Listing) -> pd.DataFrame:
    return listing.stocks[listing.stocks["size"].isin(TOPIX500)]


def stock_ticker(code: str) -> str:
    return f"{code}.T"
```

File: `sector_leadlag_lab/src/sector_leadlag/data/yf.py` (create)

```python
"""Daily prices from yfinance, kept as CSV in the snapshot store (design §4).

yfinance's ``history(auto_adjust=False, actions=True)`` gives OHLC and volume adjusted for
splits (not for dividends), the dividend-adjusted close, and the dividends and split ratios on
their ex-dates. Close times volume is therefore the traded value in yen or dollars.
"""

from __future__ import annotations

import io
import time as clock
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from .store import FetchError

US_SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
COLUMNS = ("open", "high", "low", "close", "adj_close", "volume", "dividends", "splits")
RENAME = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividends",
    "Stock Splits": "splits",
}
ZONES = {"jp": ZoneInfo("Asia/Tokyo"), "us": ZoneInfo("America/New_York")}
COMPLETE_AFTER = time(18, 0)  # a day's bar is taken as final after 18:00 local time


def market_of(ticker: str) -> str:
    return "jp" if ticker.endswith(".T") else "us"


def complete_through(fetched_at: datetime, market: str) -> date:
    """The last local date whose daily bar was final when the data was fetched."""
    local = fetched_at.astimezone(ZONES[market])
    return local.date() if local.time() >= COMPLETE_AFTER else local.date() - timedelta(days=1)


def to_csv(history: pd.DataFrame, through: date) -> bytes:
    frame = history.rename(columns=RENAME)
    missing = [column for column in COLUMNS if column not in frame.columns]
    if missing:
        raise FetchError(f"the yfinance history lacks {missing}")
    frame = frame[list(COLUMNS)]
    index = pd.DatetimeIndex(frame.index)
    if index.tz is not None:
        index = index.tz_localize(None)  # keeps the exchange's local date
    frame = frame.set_axis(pd.DatetimeIndex(index.normalize(), name="date"))
    frame = frame[(frame.index <= pd.Timestamp(through)) & frame["close"].notna()]
    return frame.to_csv(float_format="%.10g").encode()


def _yfinance_history(ticker: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.Ticker(ticker).history(period="max", auto_adjust=False, actions=True)


def download(
    ticker: str,
    *,
    fetched_at: datetime | None = None,
    attempts: int = 4,
    history: Callable[[str], pd.DataFrame] = _yfinance_history,
    sleep: Callable[[float], None] = clock.sleep,
) -> bytes:
    """The full daily history of ``ticker`` as CSV bytes, without a day that was still trading."""
    stamp = fetched_at or datetime.now(UTC)
    last_error: Exception | None = None
    for attempt in range(attempts):
        frame = None
        try:
            frame = history(ticker)
        except Exception as error:  # yfinance raises several types when throttled
            last_error = error
        if frame is not None and not frame.empty:
            return to_csv(frame, complete_through(stamp, market_of(ticker)))
        if attempt + 1 < attempts:
            sleep(5.0 * 3**attempt)
    raise FetchError(f"yfinance returned no history for {ticker} ({last_error})")


def parse_csv(content: bytes) -> pd.DataFrame:
    frame = pd.read_csv(io.BytesIO(content), index_col="date", parse_dates=["date"])
    return frame.astype(float)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `8 passed`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Parse the JPX listed-issues file and yfinance daily histories"
```

---

### Task 3: The snapshot of every input

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/data/snapshot.py`
- Test: `sector_leadlag_lab/tests/test_snapshot.py`

**Interfaces:**
- Consumes: `store.RAW_ROOT`, `store.FetchError`, `store.fetch`, `store.store_bytes` (Task 1); `jpx.URL`, `jpx.parse_listing`, `jpx.topix500`, `jpx.ETF_TICKERS`, `jpx.stock_ticker`, `yf.US_SECTORS`, `yf.download` (Task 2).
- Produces: `sector_leadlag.data.snapshot.snapshot_all(root: Path = RAW_ROOT, *, fetch_listing=fetch, download=yf.download, pause: float = 0.3, sleep=time.sleep, now: datetime | None = None) -> list[str]`. It parses the listing before storing it, stores `jpx/data_j`, then `yf/<ticker>` for the 11 SPDRs and 17 ETFs (a failure raises `FetchError`) and for every TOPIX500 stock (a failure adds the line `yf/<ticker>: failed` and goes on). Other lines read `"<source>/<indicator>: stored|unchanged, <n> bytes"`.

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_snapshot.py` (create)

```python
import os
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
import pytest
from sector_leadlag.data import jpx, yf
from sector_leadlag.data.snapshot import snapshot_all
from sector_leadlag.data.store import FetchError, indicators, read_latest


def _fake_download(failing: set[str]):
    def download(ticker: str, *, fetched_at: datetime) -> bytes:
        if ticker in failing:
            raise FetchError(f"no history for {ticker}")
        return f"date,close\n2026-10-16,{len(ticker)}\n".encode()

    return download


def test_snapshot_stores_the_listing_every_etf_and_the_topix500_stocks(
    tmp_path: Path, listing_bytes
):
    content = listing_bytes([("7203", 6, "TOPIX Core30"), ("1301", 1, "TOPIX Small 1")])
    lines = snapshot_all(
        tmp_path,
        fetch_listing=lambda url: content,
        download=_fake_download({"9999.T"}),
        sleep=lambda _: None,
        now=datetime(2026, 10, 19, 10, 0, tzinfo=UTC),
    )
    stored = indicators(tmp_path, "yf")
    assert set(stored) == {*yf.US_SECTORS, *jpx.ETF_TICKERS, "7203.T"}
    assert jpx.parse_listing(read_latest(tmp_path, "jpx", "data_j")).as_of == date(2026, 9, 30)
    assert lines[0].startswith("jpx/data_j: stored")


def test_a_failing_stock_is_listed_and_a_failing_etf_stops_the_snapshot(
    tmp_path: Path, listing_bytes
):
    content = listing_bytes([("7203", 6, "TOPIX Core30"), ("6758", 9, "TOPIX Core30")])
    lines = snapshot_all(
        tmp_path,
        fetch_listing=lambda url: content,
        download=_fake_download({"6758.T"}),
        sleep=lambda _: None,
    )
    assert "yf/6758.T: failed" in lines
    with pytest.raises(FetchError, match=r"1617\.T"):
        snapshot_all(
            tmp_path / "other",
            fetch_listing=lambda url: content,
            download=_fake_download({"1617.T"}),
            sleep=lambda _: None,
        )


@pytest.mark.skipif(os.environ.get("SECTOR_LEADLAG_NETWORK") != "1", reason="network test")
def test_the_real_listing_and_one_history_download():
    from sector_leadlag.data.store import fetch

    listing = jpx.parse_listing(fetch(jpx.URL))
    assert len(jpx.topix500(listing)) > 450
    frame = yf.parse_csv(yf.download("1617.T"))
    assert frame.index[0] < pd.Timestamp("2009-01-01") and (frame["volume"] >= 0).all()
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_snapshot.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.data.snapshot'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/data/snapshot.py` (create)

```python
"""Fetch every raw input into the store: the listed-issues file and the yfinance histories (design §4).

The US sector ETFs and the Japanese sector ETFs must all download; a stock that fails is listed
and left out (the study reports how many TOPIX500 names have prices).
"""

from __future__ import annotations

import time as clock
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from . import jpx, yf
from .store import RAW_ROOT, FetchError, fetch, store_bytes


def snapshot_all(
    root: Path = RAW_ROOT,
    *,
    fetch_listing: Callable[[str], bytes] = fetch,
    download: Callable[..., bytes] = yf.download,
    pause: float = 0.3,
    sleep: Callable[[float], None] = clock.sleep,
    now: datetime | None = None,
) -> list[str]:
    lines: list[str] = []

    def keep(source: str, indicator: str, content: bytes, url: str, filename: str) -> None:
        result = store_bytes(root, source, indicator, content, url=url, filename=filename)
        state = "stored" if result.changed else "unchanged"
        lines.append(f"{source}/{indicator}: {state}, {result.size:,} bytes")

    content = fetch_listing(jpx.URL)
    listing = jpx.parse_listing(content)  # refuse a file in an unexpected layout before storing
    keep("jpx", "data_j", content, jpx.URL, "data_j.xlsx")
    fetched_at = now or datetime.now(UTC)
    required = [*yf.US_SECTORS, *jpx.ETF_TICKERS]
    stocks = [jpx.stock_ticker(code) for code in jpx.topix500(listing).index]
    for ticker in required + stocks:
        try:
            payload = download(ticker, fetched_at=fetched_at)
        except FetchError:
            if ticker in required:
                raise
            lines.append(f"yf/{ticker}: failed")
            continue
        keep("yf", ticker, payload, f"yfinance:{ticker}", f"{ticker}.csv")
        sleep(pause)
    return lines
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `10 passed, 1 skipped` (the network test).

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Snapshot the listing and every price history"
```

---

### Task 4: Trading days, s(d) and the two pairings

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/timing.py`
- Test: `sector_leadlag_lab/tests/test_timing.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `sector_leadlag.timing.VARIANTS = ("same_date", "lagged")`, `MIN_TRADED_SHARE = 0.5`, `jp_trading_days(volume: pd.DataFrame) -> pd.DatetimeIndex` (D3), `us_trading_days(volume: pd.Series) -> pd.DatetimeIndex`, `last_us_before(jp_days: pd.DatetimeIndex, us_days: pd.DatetimeIndex) -> pd.Series` (s(d), indexed by the Japanese days that have one), `close_to_close(prices: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame`, `Rows(dates: DatetimeIndex, us_dates: DatetimeIndex, us: ndarray (rows, 11), jp: ndarray (rows, 17), us_names: tuple[str, ...], jp_names: tuple[int, ...])`, `pair_rows(variant: str, us_ret: pd.DataFrame, jp_ret: pd.DataFrame, s_map: pd.Series) -> Rows` (ValueError `unknown pairing` otherwise).

The module is called `timing`, not `calendar`, so that it never shadows the standard library's `calendar` (spec §10 as revised).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_timing.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.timing import (
    close_to_close,
    jp_trading_days,
    last_us_before,
    pair_rows,
    us_trading_days,
)


def days(*text: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(list(text)))


def test_a_day_counts_when_half_of_the_listed_stocks_traded():
    volume = pd.DataFrame(
        {"a": [10, 0, 5, 7], "b": [10, 0, np.nan, 4], "c": [0, 3, np.nan, 2]},
        index=days("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"),
    )
    # 2/3 and 1/3 traded on the 5th and 6th; the 7th is a holiday with a stray row for "a"
    # only (1 of the 3 listed names traded); 3/3 on the 8th
    assert list(jp_trading_days(volume)) == list(days("2026-01-05", "2026-01-08"))
    delisted = pd.DataFrame(
        {"a": [10, 10], "b": [0, np.nan]}, index=days("2026-01-05", "2026-01-06")
    )
    # b's last row is the 5th, so on the 6th only a is listed
    assert list(jp_trading_days(delisted)) == list(days("2026-01-05", "2026-01-06"))
    assert list(us_trading_days(pd.Series([1.0, 0.0], index=days("2026-01-05", "2026-01-06")))) == [
        pd.Timestamp("2026-01-05")
    ]


def test_s_of_d_skips_us_holidays_and_follows_japanese_ones():
    us = days("2026-01-15", "2026-01-16", "2026-01-20", "2026-01-21")  # Mon 19th: MLK day
    jp = days("2026-01-16", "2026-01-19", "2026-01-20", "2026-01-21", "2026-01-23")
    s = last_us_before(jp, us)
    assert list(s.index) == list(jp)
    assert list(s) == list(
        days("2026-01-15", "2026-01-16", "2026-01-16", "2026-01-20", "2026-01-21")
    )
    early = last_us_before(days("2026-01-15"), us)  # no US day before it
    assert early.empty


def test_close_to_close_runs_on_the_given_calendar():
    prices = pd.DataFrame(
        {"x": [100.0, 110.0, 99.0]}, index=days("2026-01-05", "2026-01-06", "2026-01-08")
    )
    r = close_to_close(prices, days("2026-01-05", "2026-01-06", "2026-01-08"))
    assert np.isnan(r["x"].iloc[0])
    assert r["x"].iloc[1:].round(6).tolist() == [0.1, -0.1]


def test_pairings():
    us_days = days("2026-01-15", "2026-01-16", "2026-01-20")
    jp_days = days("2026-01-16", "2026-01-19", "2026-01-20")
    us_ret = pd.DataFrame({"XLK": [1.0, 2.0, 3.0]}, index=us_days)
    jp_ret = pd.DataFrame({1: [10.0, 20.0, 30.0]}, index=jp_days)
    s = last_us_before(jp_days, us_days)
    same = pair_rows("same_date", us_ret, jp_ret, s)
    assert list(same.dates) == list(days("2026-01-16", "2026-01-20"))
    assert same.us[:, 0].tolist() == [2.0, 3.0] and same.jp[:, 0].tolist() == [10.0, 30.0]
    lagged = pair_rows("lagged", us_ret, jp_ret, s)
    assert list(lagged.dates) == list(jp_days)
    assert list(lagged.us_dates) == list(days("2026-01-15", "2026-01-16", "2026-01-16"))
    assert lagged.us[:, 0].tolist() == [1.0, 2.0, 2.0]
    assert lagged.jp[:, 0].tolist() == [10.0, 20.0, 30.0]
    assert lagged.us_names == ("XLK",) and lagged.jp_names == (1,)
    with pytest.raises(ValueError, match="unknown pairing"):
        pair_rows("other", us_ret, jp_ret, s)
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_timing.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.timing'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/timing.py` (create)

```python
"""Trading days, the US day each Japanese day uses, and the paired rows of the windows (design §5).

Two readings of how the papers pair US and Japanese returns inside a window (design §5.2):

- ``same_date``: only days on which both markets traded, each paired with itself. Both papers
  write the window with one date index for every asset ("the close of business day d'"), and
  the strategy paper says it uses "only business days observable in both markets".
- ``lagged``: every Japanese day d' paired with the US day s(d') before it, the information
  timing of the trade itself.

Each market's close-to-close return runs from its own previous trading day.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

VARIANTS = ("same_date", "lagged")
MIN_TRADED_SHARE = 0.5


def jp_trading_days(volume: pd.DataFrame) -> pd.DatetimeIndex:
    """Dates on which at least half of the stocks listed at the time traded (design §4).

    A stock counts as listed from its first row to its last, so a stray row on a holiday does
    not make the holiday a trading day.
    """
    dates = volume.index.to_numpy()
    first = volume.apply(pd.Series.first_valid_index).to_numpy(dtype="datetime64[ns]")
    last = volume.apply(pd.Series.last_valid_index).to_numpy(dtype="datetime64[ns]")
    listed = ((dates[:, None] >= first) & (dates[:, None] <= last)).sum(axis=1)
    traded = (volume > 0).sum(axis=1).to_numpy()
    share = np.divide(traded, listed, out=np.zeros(len(dates)), where=listed > 0)
    return pd.DatetimeIndex(volume.index[share >= MIN_TRADED_SHARE], name="date")


def us_trading_days(volume: pd.Series) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(volume.index[volume > 0], name="date")


def last_us_before(jp_days: pd.DatetimeIndex, us_days: pd.DatetimeIndex) -> pd.Series:
    """s(d): the last US trading day strictly before each Japanese day d (design §5.1)."""
    position = us_days.searchsorted(jp_days, side="left") - 1
    keep = position >= 0
    return pd.Series(us_days[position[keep]], index=jp_days[keep], name="us_day")


def close_to_close(prices: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Returns from each day's previous row on ``days`` (one market's own calendar)."""
    p = prices.reindex(days)
    return p / p.shift(1) - 1.0


@dataclass(frozen=True)
class Rows:
    """The paired US and Japanese returns that every correlation window is cut from."""

    dates: pd.DatetimeIndex  # the row's date: a common day, or the Japanese day d'
    us_dates: pd.DatetimeIndex  # the US day of the row's US returns
    us: np.ndarray  # (rows, 11)
    jp: np.ndarray  # (rows, 17)
    us_names: tuple[str, ...]
    jp_names: tuple[int, ...]


def pair_rows(variant: str, us_ret: pd.DataFrame, jp_ret: pd.DataFrame, s_map: pd.Series) -> Rows:
    names = (tuple(us_ret.columns), tuple(jp_ret.columns))
    if variant == "same_date":
        common = jp_ret.index.intersection(us_ret.index)
        us = us_ret.reindex(common).to_numpy()
        return Rows(common, common, us, jp_ret.reindex(common).to_numpy(), *names)
    if variant == "lagged":
        jp_days = s_map.index.intersection(jp_ret.index)
        us_days = pd.DatetimeIndex(s_map.reindex(jp_days).to_numpy())
        us = us_ret.reindex(us_days).to_numpy()
        return Rows(jp_days, us_days, us, jp_ret.reindex(jp_days).to_numpy(), *names)
    raise ValueError(f"unknown pairing {variant!r}; expected one of {VARIANTS}")
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `14 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add trading days, s(d) and the two window pairings"
```

---

### Task 5: The PCA SUB signal and the point-in-time checks (G2)

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/pit.py`, `sector_leadlag_lab/src/sector_leadlag/signal.py`
- Test: `sector_leadlag_lab/tests/test_pit.py`, `sector_leadlag_lab/tests/test_signal.py`

**Interfaces:**
- Consumes: `timing.Rows`, `timing.pair_rows`, `timing.last_us_before` (Task 4).
- Produces:
  - `sector_leadlag.pit`: `LeakError(AssertionError)`, `check_window(row_dates, row_us_dates, us_day, day) -> None` (R1), `check_lookback(last_read: pd.Series) -> None` (R2).
  - `sector_leadlag.signal`: `LAMBDA = 0.9`, `K = 3`, `WINDOW = 60`, `Q = 0.3`, `FULL = (2010-01-01, 2014-12-31)`, the cyclical/defensive tuples, `Spec(lam: float = 0.9, k: int = 3, window: int = 60, kind: str = "pca" | "momentum")`, `prior_subspace(us_names, jp_names) -> ndarray (28, 3)`, `standardize(block) -> (mu, sd, usable, z)`, `correlation(z, usable) -> ndarray`, `full_correlation(rows: Rows, span=FULL) -> (ndarray, list)` (C_full and the labels it could not use), `target(c_full, v0) -> ndarray` (C0), `propagate(vectors, n_us, z_us) -> ndarray`, `lead_lag_signal(rows, us_ret, s_map, c0, days, spec=Spec()) -> pd.DataFrame` (columns = `rows.jp_names`; one row per day with a full window; calls `pit.check_window` for every day), `cross_standardize(signal) -> pd.DataFrame` (sz), `long_short(signal, available, q=Q) -> pd.DataFrame` (weights ±1/n), `top_sectors(signal, n) -> pd.DataFrame` (bool).

The G2 check of spec §8 is `test_pit.py`: each check function raises `LeakError` on an input carrying a future value, and so does `lead_lag_signal` when a window row holds US returns dated after s(d).

- [ ] **Step 1: Write the failing tests**

File: `sector_leadlag_lab/tests/test_pit.py` (create)

```python
"""G2: the R1 and R2 checks refuse inputs that carry future values (design §8)."""

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.pit import LeakError, check_lookback, check_window
from sector_leadlag.signal import Spec, lead_lag_signal, prior_subspace, target
from sector_leadlag.timing import Rows

T = pd.Timestamp


def test_window_rows_must_be_dated_before_the_day():
    rows = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-06")])
    check_window(rows, rows, T("2026-01-06"), T("2026-01-07"))
    with pytest.raises(LeakError, match="dated 2026-01-07"):
        check_window(
            rows.append(pd.DatetimeIndex([T("2026-01-07")])), rows, T("2026-01-06"), T("2026-01-07")
        )


def test_window_us_returns_must_not_be_after_s_of_d():
    rows = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-06")])
    us = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-07")])
    with pytest.raises(LeakError, match="after s"):
        check_window(rows, us, T("2026-01-06"), T("2026-01-07"))


def test_the_us_day_itself_must_be_before_the_day():
    rows = pd.DatetimeIndex([T("2026-01-05")])
    with pytest.raises(LeakError, match="is not before"):
        check_window(rows, rows, T("2026-01-07"), T("2026-01-07"))


def test_basket_inputs_must_be_read_before_the_day():
    index = pd.DatetimeIndex([T("2026-01-06"), T("2026-01-07")])
    check_lookback(pd.Series([T("2026-01-05"), T("2026-01-06")], index=index))
    with pytest.raises(LeakError, match="baskets of 2026-01-07 read 2026-01-07"):
        check_lookback(pd.Series([T("2026-01-05"), T("2026-01-07")], index=index))


def test_the_signal_refuses_rows_whose_us_returns_come_from_the_future():
    dates = pd.bdate_range("2026-01-05", periods=70)
    rng = np.random.default_rng(0)
    leaky = pd.DatetimeIndex([*dates[:-1], dates[-1] + pd.Timedelta(days=5)])
    rows = Rows(
        dates, leaky, rng.normal(size=(70, 2)), rng.normal(size=(70, 3)), ("XLK", "XLE"), (1, 2, 3)
    )
    us_ret = pd.DataFrame(rng.normal(size=(70, 2)), index=dates, columns=["XLK", "XLE"])
    day = dates[-1] + pd.Timedelta(days=1)
    s_map = pd.Series([dates[-1]], index=pd.DatetimeIndex([day]))
    c0 = target(np.eye(5), prior_subspace(["XLK", "XLE"], [1, 2, 3]))
    with pytest.raises(LeakError):
        lead_lag_signal(rows, us_ret, s_map, c0, pd.DatetimeIndex([day]), Spec())
```

File: `sector_leadlag_lab/tests/test_signal.py` (create)

```python
import numpy as np
import pandas as pd
from sector_leadlag.signal import (
    Spec,
    correlation,
    cross_standardize,
    full_correlation,
    lead_lag_signal,
    long_short,
    prior_subspace,
    propagate,
    standardize,
    target,
    top_sectors,
)
from sector_leadlag.timing import last_us_before, pair_rows

US = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
JP = tuple(range(1, 18))


def test_prior_subspace_is_orthonormal_and_points_where_the_paper_says():
    v0 = prior_subspace(US, JP)
    assert v0.shape == (28, 3)
    assert np.allclose(v0.T @ v0, np.eye(3))
    assert np.allclose(v0[:, 0], 1 / np.sqrt(28))
    assert (v0[:11, 1] > 0).all() and (v0[11:, 1] < 0).all()
    # cyclical XLE (US) and banks (sector 15) load above defensive XLU and retail (sector 14)
    assert v0[US.index("XLE"), 2] > v0[US.index("XLU"), 2]
    assert v0[11 + 14, 2] > v0[11 + 13, 2]


def test_target_is_a_correlation_matrix():
    rng = np.random.default_rng(1)
    _, _, usable, z = standardize(rng.normal(size=(400, 28)))
    c0 = target(correlation(z, usable), prior_subspace(US, JP))
    assert np.allclose(c0, c0.T) and np.allclose(np.diag(c0), 1.0)
    assert np.all(np.linalg.eigvalsh(c0) > -1e-12)


def test_an_unlaunched_column_gets_no_correlation_and_a_zero_score():
    rng = np.random.default_rng(2)
    block = rng.normal(size=(60, 4))
    block[:30, 2] = np.nan  # launched halfway through the window
    _, _, usable, z = standardize(block)
    assert usable.tolist() == [True, True, False, True]
    assert (z[:, 2] == 0).all()
    c = correlation(z, usable)
    assert c[2, 2] == 1.0 and (np.delete(c[2], 2) == 0).all()


def test_flipping_eigenvector_signs_leaves_the_signal_unchanged():
    rng = np.random.default_rng(3)
    vectors = np.linalg.qr(rng.normal(size=(28, 3)))[0]
    z_us = rng.normal(size=11)
    flipped = vectors * np.array([-1.0, 1.0, -1.0])
    assert np.allclose(propagate(vectors, 11, z_us), propagate(flipped, 11, z_us))


def _factor_world(n: int, seed: int):
    """US shocks g_t at t, the same g_t in Japan on the next day (strategy paper, eq. 23-24)."""
    rng = np.random.default_rng(seed)
    v_us = np.linalg.qr(rng.normal(size=(11, 3)))[0]
    v_jp = np.linalg.qr(rng.normal(size=(17, 3)))[0]
    g = rng.normal(size=(n, 3)) * np.array([3.0, 2.5, 2.0])
    us = g @ v_us.T + 0.3 * rng.normal(size=(n, 11))
    jp = np.vstack([np.zeros((1, 17)), g[:-1] @ v_jp.T]) + 0.3 * rng.normal(size=(n, 17))
    dates = pd.bdate_range("2020-01-01", periods=n)
    us_ret = pd.DataFrame(us, index=dates, columns=list(US))
    jp_ret = pd.DataFrame(jp, index=dates, columns=list(JP))  # row t answers US t-1
    return us_ret, jp_ret, v_us, v_jp


def test_plain_pca_recovers_the_best_linear_predictor():
    us_ret, jp_ret, v_us, v_jp = _factor_world(1600, 4)
    s_map = last_us_before(jp_ret.index, us_ret.index)
    rows = pair_rows("lagged", us_ret, jp_ret, s_map)
    c0 = np.eye(28)
    days = jp_ret.index[-300:]
    signal = lead_lag_signal(rows, us_ret, s_map, c0, days, Spec(lam=0.0, window=1200))
    mu = us_ret.iloc[-1500:].mean()
    sd = us_ret.iloc[-1500:].std(ddof=0)
    us_days = pd.DatetimeIndex(s_map.reindex(signal.index).to_numpy())
    z_us = ((us_ret.reindex(us_days) - mu) / sd).to_numpy()
    best = z_us @ v_us @ v_jp.T
    assert np.corrcoef(signal.to_numpy().ravel(), best.ravel())[0, 1] > 0.9


def test_lambda_zero_is_plain_pca_and_lambda_one_is_the_target():
    rng = np.random.default_rng(5)
    dates = pd.bdate_range("2024-01-01", periods=80)
    us_ret = pd.DataFrame(rng.normal(size=(80, 11)), index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(80, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    c0 = target(full_correlation(rows, (dates[0], dates[-1]))[0], prior_subspace(US, JP))
    day = dates[-1:]
    plain = lead_lag_signal(rows, us_ret, s_map, c0, day, Spec(lam=0.0))
    mu, sd, usable, z = standardize(np.hstack([rows.us, rows.jp])[-61:-1])
    values, vectors = np.linalg.eigh(correlation(z, usable))
    top = vectors[:, np.argsort(values)[::-1][:3]]
    z_us = (us_ret.loc[s_map.iloc[-1]].to_numpy() - mu[:11]) / sd[:11]
    assert np.allclose(plain.to_numpy()[0], propagate(top, 11, z_us))
    pure = lead_lag_signal(rows, us_ret, s_map, c0, day, Spec(lam=1.0))
    values, vectors = np.linalg.eigh(c0)
    top = vectors[:, np.argsort(values)[::-1][:3]]
    assert np.allclose(pure.to_numpy()[0], propagate(top, 11, z_us))


def test_a_column_before_launch_does_not_move_the_signal():
    rng = np.random.default_rng(6)
    dates = pd.bdate_range("2024-01-01", periods=80)
    us = rng.normal(size=(80, 11))
    us[:, US.index("XLC")] = np.nan
    us_ret = pd.DataFrame(us, index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(80, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    c_full, unusable = full_correlation(rows, (dates[0], dates[-1]))
    assert unusable == ["XLC"]
    c0 = target(c_full, prior_subspace(US, JP))
    base = lead_lag_signal(rows, us_ret, s_map, c0, dates[-5:])
    bumped = us_ret.copy()
    bumped.loc[dates[-6] :, "XLC"] = 0.5  # values that are not part of a full window
    moved = lead_lag_signal(rows, bumped, s_map, c0, dates[-5:])
    pd.testing.assert_frame_equal(base, moved)


def test_momentum_is_the_window_mean_of_japan():
    dates = pd.bdate_range("2024-01-01", periods=70)
    rng = np.random.default_rng(7)
    us_ret = pd.DataFrame(rng.normal(size=(70, 11)), index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(70, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    signal = lead_lag_signal(rows, us_ret, s_map, np.eye(28), dates[-1:], Spec(kind="momentum"))
    assert np.allclose(signal.to_numpy()[0], jp_ret.iloc[-61:-1].mean().to_numpy())


def test_long_short_weights_and_the_top_sectors():
    signal = pd.DataFrame([np.arange(17.0), np.arange(17.0)[::-1]], columns=list(JP))
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    available.iloc[1, :7] = False  # 10 sectors traded: n = 3
    w = long_short(signal, available)
    assert np.allclose(w.sum(axis=1), 0) and np.allclose(w.abs().sum(axis=1), 2)
    assert w.iloc[0][w.iloc[0] > 0].index.tolist() == [13, 14, 15, 16, 17]
    assert w.iloc[1][w.iloc[1] > 0].index.tolist() == [8, 9, 10]
    assert w.iloc[1][w.iloc[1] < 0].index.tolist() == [15, 16, 17]
    top = top_sectors(signal, 5)
    assert top.iloc[0][top.iloc[0]].index.tolist() == [13, 14, 15, 16, 17]
    sz = cross_standardize(signal)
    assert np.allclose(sz.mean(axis=1), 0) and np.allclose(sz.std(axis=1, ddof=0), 1)


def test_a_flat_signal_takes_no_position():
    signal = pd.DataFrame([np.zeros(17)], columns=list(JP))
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    assert (long_short(signal, available) == 0).all().all()
    assert not top_sectors(signal, 5).any().any()
    assert cross_standardize(signal).isna().all().all()
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_pit.py sector_leadlag_lab/tests/test_signal.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.pit'` (and `'sector_leadlag.signal'`).

- [ ] **Step 3: Write the two modules**

File: `sector_leadlag_lab/src/sector_leadlag/pit.py` (create)

```python
"""Point-in-time checks R1 and R2 (design §5.1). G2 feeds them future values on purpose."""

from __future__ import annotations

import pandas as pd


class LeakError(AssertionError):
    """An input was observed later than the decision it feeds."""


def check_window(
    row_dates: pd.DatetimeIndex,
    row_us_dates: pd.DatetimeIndex,
    us_day: pd.Timestamp,
    day: pd.Timestamp,
) -> None:
    """R1: the signal of Japanese day d reads rows dated before d, and US returns up to s(d) < d."""
    if not us_day < day:
        raise LeakError(f"the US day {us_day.date()} of {day.date()} is not before it")
    if len(row_dates) and row_dates.max() >= day:
        raise LeakError(f"a window row of {day.date()} is dated {row_dates.max().date()}")
    if len(row_us_dates) and row_us_dates.max() > us_day:
        raise LeakError(
            f"a window row of {day.date()} holds US returns of {row_us_dates.max().date()},"
            f" after s(d) = {us_day.date()}"
        )


def check_lookback(last_read: pd.Series) -> None:
    """R2: what decides the baskets and share counts of day d was read on a day before d.

    ``last_read`` maps each day d to the last date its inputs came from.
    """
    known = last_read.dropna()
    late = known[pd.DatetimeIndex(known.to_numpy()) >= pd.DatetimeIndex(known.index)]
    if len(late):
        raise LeakError(f"the baskets of {late.index[0].date()} read {late.iloc[0].date()}")
```

File: `sector_leadlag_lab/src/sector_leadlag/signal.py` (create)

```python
"""PCA SUB: the subspace-regularised lead-lag signal, and the baseline signals (design §6).

Every value comes from the strategy paper (Nakagawa et al., SIG-FIN-036-13); nothing is tuned
here. Japanese sectors are the JPX 17-sector codes 1-17; NEXT FUNDS ETF 1616+k tracks sector k.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import pit
from .timing import Rows

LAMBDA = 0.9
K = 3
WINDOW = 60
Q = 0.3
FULL = (pd.Timestamp("2010-01-01"), pd.Timestamp("2014-12-31"))
US_CYCLICAL = ("XLB", "XLE", "XLF", "XLRE")
US_DEFENSIVE = ("XLK", "XLP", "XLU", "XLV")
JP_CYCLICAL = (2, 9, 13, 15)  # 1618 energy, 1625 electric & precision, 1629 trading, 1631 banks
JP_DEFENSIVE = (1, 5, 11, 14)  # 1617 foods, 1621 pharma, 1627 power & gas, 1630 retail


@dataclass(frozen=True)
class Spec:
    lam: float = LAMBDA
    k: int = K
    window: int = WINDOW
    kind: str = "pca"  # "pca", or "momentum" (the window mean of each Japanese sector)


def prior_subspace(us_names: Sequence[str], jp_names: Sequence[int]) -> np.ndarray:
    """V0 = [v1, v2, v3]: market, US minus Japan, cyclical minus defensive; orthonormal columns."""
    labels = [*us_names, *jp_names]
    cyclical = {*US_CYCLICAL, *JP_CYCLICAL}
    defensive = {*US_DEFENSIVE, *JP_DEFENSIVE}
    v1 = np.ones(len(labels))
    v2 = np.r_[np.ones(len(us_names)), -np.ones(len(jp_names))]
    v3 = np.array([1.0 if x in cyclical else -1.0 if x in defensive else 0.0 for x in labels])
    basis: list[np.ndarray] = []
    for v in (v1, v2, v3):
        for u in basis:
            v = v - (u @ v) * u
        basis.append(v / np.linalg.norm(v))
    return np.column_stack(basis)


def standardize(block: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Column means and standard deviations (1/L), which columns are usable, and the z-scores.

    A column is usable when it has no missing value in the block and is not constant. The others
    (an ETF before its launch, design §4) get z = 0 and no correlation with anything.
    """
    finite = np.isfinite(block)
    filled = np.where(finite, block, 0.0)
    mu = filled.mean(axis=0)
    sd = filled.std(axis=0)
    usable = finite.all(axis=0) & (sd > 0)
    safe = np.where(usable, sd, 1.0)
    z = np.where(usable, (filled - mu) / safe, 0.0)
    return mu, safe, usable, z


def correlation(z: np.ndarray, usable: np.ndarray) -> np.ndarray:
    c = z.T @ z / len(z)
    c[~usable, :] = 0.0
    c[:, ~usable] = 0.0
    np.fill_diagonal(c, 1.0)
    return c


def full_correlation(
    rows: Rows, span: tuple[pd.Timestamp, pd.Timestamp] = FULL
) -> tuple[np.ndarray, list]:
    """C_full over the estimation span, and the columns it could not use."""
    mask = (rows.dates >= span[0]) & (rows.dates <= span[1])
    block = np.hstack([rows.us[mask], rows.jp[mask]])
    _, _, usable, z = standardize(block)
    labels = [*rows.us_names, *rows.jp_names]
    return correlation(z, usable), [labels[i] for i in np.flatnonzero(~usable)]


def target(c_full: np.ndarray, v0: np.ndarray) -> np.ndarray:
    """C0: V0 diag(V0' C_full V0) V0', rescaled to a correlation matrix with a unit diagonal."""
    d0 = np.diag(np.diag(v0.T @ c_full @ v0))
    raw = v0 @ d0 @ v0.T
    scale = np.sqrt(np.diag(raw))
    c0 = raw / np.outer(scale, scale)
    np.fill_diagonal(c0, 1.0)
    return c0


def propagate(vectors: np.ndarray, n_us: int, z_us: np.ndarray) -> np.ndarray:
    """V_J V_U' z_U: project the US shock on the leading modes and map it to Japan."""
    return vectors[n_us:] @ (vectors[:n_us].T @ z_us)


def lead_lag_signal(
    rows: Rows,
    us_ret: pd.DataFrame,
    s_map: pd.Series,
    c0: np.ndarray,
    days: pd.DatetimeIndex,
    spec: Spec = Spec(),
) -> pd.DataFrame:
    """The signal of each Japanese day d in ``days`` that has a full window (design §6).

    The window of d is the last ``spec.window`` rows dated before d. z_U,s(d) is the US return of
    s(d) standardised with the window's US means and standard deviations.
    """
    n_us = rows.us.shape[1]
    block = np.hstack([rows.us, rows.jp])
    days = pd.DatetimeIndex(days).intersection(s_map.index)
    us_days = pd.DatetimeIndex(s_map.reindex(days).to_numpy())
    us_now = us_ret.reindex(us_days).to_numpy()
    ends = rows.dates.searchsorted(days, side="left")
    out = np.full((len(days), rows.jp.shape[1]), np.nan)
    for i, end in enumerate(ends):
        if end < spec.window:
            continue
        lo = end - spec.window
        pit.check_window(rows.dates[lo:end], rows.us_dates[lo:end], us_days[i], days[i])
        mu, sd, usable, z = standardize(block[lo:end])
        if spec.kind == "momentum":
            out[i] = np.where(usable[n_us:], mu[n_us:], np.nan)
            continue
        c_reg = (1.0 - spec.lam) * correlation(z, usable) + spec.lam * c0
        values, vectors = np.linalg.eigh(c_reg)
        top = vectors[:, np.argsort(values)[::-1][: spec.k]]
        x = us_now[i]
        live = usable[:n_us] & np.isfinite(x)
        z_us = np.where(live, (np.where(live, x, 0.0) - mu[:n_us]) / sd[:n_us], 0.0)
        out[i] = propagate(top, n_us, z_us)
    frame = pd.DataFrame(out, index=days, columns=list(rows.jp_names))
    return frame.dropna(how="all")


def cross_standardize(signal: pd.DataFrame) -> pd.DataFrame:
    """sz_{j,d}: each day's signal across the sectors, mean 0 and standard deviation 1."""
    mean = signal.mean(axis=1)
    sd = signal.std(axis=1, ddof=0)
    return signal.sub(mean, axis=0).div(sd.where(sd > 0), axis=0)


def _descending(values: np.ndarray, idx: np.ndarray) -> np.ndarray:
    return idx[np.argsort(-values[idx], kind="stable")]  # ties keep the lower sector code first


def long_short(signal: pd.DataFrame, available: pd.DataFrame, q: float = Q) -> pd.DataFrame:
    """+1/n on the top ⌊q·|J_d|⌋ available sectors and −1/n on the bottom ones (design §6)."""
    values = signal.to_numpy()
    ok = available.reindex(index=signal.index, columns=signal.columns, fill_value=False)
    ok = ok.to_numpy(dtype=bool) & np.isfinite(values)
    weights = np.zeros(values.shape)
    for i in range(len(values)):
        idx = np.flatnonzero(ok[i])
        n = int(np.floor(q * len(idx) + 1e-9))
        if n == 0 or np.ptp(values[i, idx]) == 0:
            continue
        order = _descending(values[i], idx)
        weights[i, order[:n]] = 1.0 / n
        weights[i, order[-n:]] = -1.0 / n
    return pd.DataFrame(weights, index=signal.index, columns=signal.columns)


def top_sectors(signal: pd.DataFrame, n: int) -> pd.DataFrame:
    """The n sectors with the highest signal each day."""
    values = signal.to_numpy()
    chosen = np.zeros(values.shape, dtype=bool)
    for i in range(len(values)):
        idx = np.flatnonzero(np.isfinite(values[i]))
        if len(idx) < n or np.ptp(values[i, idx]) == 0:
            continue
        chosen[i, _descending(values[i], idx)[:n]] = True
    return pd.DataFrame(chosen, index=signal.index, columns=signal.columns)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `29 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add the PCA SUB signal and the point-in-time checks (G2)"
```

---
### Task 6: Sector baskets and their returns

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/baskets.py`
- Modify: `sector_leadlag_lab/tests/conftest.py` (append the `make_panel` fixture)
- Test: `sector_leadlag_lab/tests/test_baskets.py`

**Interfaces:**
- Consumes: `pit.check_lookback` (Task 5).
- Produces: `sector_leadlag.baskets.LOOKBACK = 60`, `TOP_SECONDARY = 10`, `PER_SECTOR = 3`, `LOT = 100`, `SECTORS = (1, …, 17)`; `Panel(open, close, adj_close, volume, dividends, splits: pd.DataFrame, sector: pd.Series)` (frozen; columns are names, `sector` maps a column to 1–17) with `.window(start, end) -> Panel`; `traded(panel) -> DataFrame[bool]`; `open_to_close`, `close_to_open`, `close_to_close`, `price_close_to_close(panel) -> DataFrame` (NaN on days without trades); `quoted(panel) -> (open, close)` as quoted on the day; `trailing_value(panel, lookback=60) -> DataFrame` (median close×volume of the 60 rows before each day); `liquidity_weights(median, sector)`; `top_equal_weights(median, sector, n=10)`; `h2_picks(median, quoted_close, sector, budget, per_sector=3) -> DataFrame[bool]` (lot priced at the previous quoted close, `<=` budget); `basket_returns(weights, returns, sector) -> DataFrame` (columns 1–17, weights renormalised over the names that traded).
- Fixture: `make_panel(open_, close, *, volume=None, dividends=None, splits=None, adj_close=None, sector=None) -> Panel` (volume 1,000, no actions, sector 1 by default).

- [ ] **Step 1: Add the fixture and write the failing test**

Append to `sector_leadlag_lab/tests/conftest.py`, two blank lines after the `yf_history` fixture:

```python
def _panel(open_, close, *, volume=None, dividends=None, splits=None, adj_close=None, sector=None):
    """A ``baskets.Panel`` from frames that share an index and columns."""
    from sector_leadlag.baskets import Panel

    zeros = close * 0.0
    return Panel(
        open=open_,
        close=close,
        adj_close=close if adj_close is None else adj_close,
        volume=zeros + 1000.0 if volume is None else volume,
        dividends=zeros if dividends is None else dividends,
        splits=zeros if splits is None else splits,
        sector=pd.Series(1, index=close.columns) if sector is None else sector,
    )


@pytest.fixture
def make_panel():
    return _panel
```

File: `sector_leadlag_lab/tests/test_baskets.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.baskets import (
    basket_returns,
    close_to_close,
    close_to_open,
    h2_picks,
    liquidity_weights,
    open_to_close,
    price_close_to_close,
    quoted,
    top_equal_weights,
    trailing_value,
)

DAYS = pd.bdate_range("2026-01-05", periods=4)


def frame(values, columns=("a",)):
    return pd.DataFrame(
        np.asarray(values, dtype=float).reshape(len(DAYS), -1), index=DAYS, columns=list(columns)
    )


def test_a_split_day_does_not_move_open_to_close(make_panel):
    # yfinance divides prices before a 1:5 split (ex-date: day 3) by 5
    panel = make_panel(
        frame([200, 202, 204, 206]),
        frame([201, 203, 205, 207]),
        splits=frame([0, 0, 5, 0]),
    )
    quoted_open, quoted_close = quoted(panel)
    assert quoted_close["a"].tolist() == [1005.0, 1015.0, 205.0, 207.0]
    same_day = quoted_close / quoted_open - 1
    pd.testing.assert_frame_equal(open_to_close(panel), same_day)


def test_overnight_and_daily_returns_add_the_dividend_going_ex(make_panel):
    panel = make_panel(
        frame([100, 97, 98, 99]),
        frame([100, 98, 99, 100]),
        dividends=frame([0, 3, 0, 0]),
    )
    assert close_to_open(panel)["a"].iloc[1] == pytest.approx(0.0)
    assert close_to_close(panel)["a"].iloc[1] == pytest.approx(0.01)
    assert price_close_to_close(panel)["a"].iloc[1] == pytest.approx(-0.02)
    assert np.isnan(close_to_open(panel)["a"].iloc[0])


def test_a_day_without_trades_has_no_return(make_panel):
    panel = make_panel(
        frame([100, 100, 100, 101]), frame([101, 100, 100, 102]), volume=frame([5, 0, 5, 5])
    )
    assert open_to_close(panel)["a"].isna().tolist() == [False, True, False, False]


def test_trailing_value_uses_only_earlier_days(make_panel):
    days = pd.bdate_range("2026-01-05", periods=5)
    close = pd.DataFrame({"a": [10.0, 10, 10, 10, 10]}, index=days)
    volume = pd.DataFrame({"a": [1.0, 2, 3, 4, 100]}, index=days)
    panel = make_panel(close, close, volume=volume)
    median = trailing_value(panel, lookback=3)
    assert median["a"].isna().tolist() == [True, True, True, False, False]
    assert median["a"].iloc[3:].tolist() == [20.0, 30.0]  # day 5's own 1,000 is not used


def test_weights_and_picks_within_each_sector():
    median = pd.DataFrame([[4.0, 3.0, 2.0, 1.0, 9.0]], index=DAYS[:1], columns=list("abcde"))
    sector = pd.Series([1, 1, 1, 1, 2], index=list("abcde"))
    weights = liquidity_weights(median, sector)
    assert weights.loc[DAYS[0], ["a", "b", "c", "d"]].sum() == pytest.approx(1.0)
    assert weights.loc[DAYS[0], "a"] == pytest.approx(0.4) and weights.loc[DAYS[0], "e"] == 1.0
    top = top_equal_weights(median, sector, n=2)
    assert top.loc[DAYS[0]].tolist() == [0.5, 0.5, 0.0, 0.0, 1.0]
    close = pd.DataFrame(
        [[1000.0, 200.0, 300.0, 400.0, 500.0], [1000.0, 200.0, 300.0, 400.0, 500.0]],
        index=DAYS[:2],
        columns=list("abcde"),
    )
    picks = h2_picks(
        pd.concat([median, median.set_axis(DAYS[1:2])]), close, sector, budget=50_000.0
    )
    # a's lot costs 100,000 yen and is left out; e's costs exactly the budget and is kept
    assert picks.loc[DAYS[1]].tolist() == [False, True, True, True, True]
    assert not picks.loc[DAYS[0]].any()  # the first day has no previous close


def test_basket_return_renormalises_over_the_names_that_traded():
    returns = pd.DataFrame([[0.01, np.nan, 0.03]], index=DAYS[:1], columns=list("abc"))
    weights = pd.DataFrame([[0.5, 0.25, 0.25]], index=DAYS[:1], columns=list("abc"))
    sector = pd.Series([1, 1, 2], index=list("abc"))
    out = basket_returns(weights, returns, sector)
    assert out.loc[DAYS[0], 1] == pytest.approx(0.01)
    assert out.loc[DAYS[0], 2] == pytest.approx(0.03)
    assert out.columns.tolist() == list(range(1, 18)) and np.isnan(out.loc[DAYS[0], 3])
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_baskets.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.baskets'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/baskets.py` (create)

```python
"""Sector baskets of stocks, their weights and returns (design §7).

Prices come from yfinance with splits adjusted (``data.yf``), so close times volume is the traded
value, and same-day ratios such as open-to-close need no adjustment. Share counts for the H2
strategy need the prices that were actually quoted, so ``quoted`` undoes the split adjustment.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import pit

LOOKBACK = 60
TOP_SECONDARY = 10
PER_SECTOR = 3
LOT = 100
SECTORS = tuple(range(1, 18))


@dataclass(frozen=True)
class Panel:
    """Daily data on the Japanese trading days; one column per stock (or per ETF sector)."""

    open: pd.DataFrame
    close: pd.DataFrame
    adj_close: pd.DataFrame
    volume: pd.DataFrame
    dividends: pd.DataFrame
    splits: pd.DataFrame
    sector: pd.Series  # column -> sector code 1-17

    def window(self, start: pd.Timestamp, end: pd.Timestamp) -> Panel:
        rows = slice(start, end)
        return Panel(
            self.open.loc[rows],
            self.close.loc[rows],
            self.adj_close.loc[rows],
            self.volume.loc[rows],
            self.dividends.loc[rows],
            self.splits.loc[rows],
            self.sector,
        )


def traded(panel: Panel) -> pd.DataFrame:
    return panel.volume.fillna(0.0) > 0


def open_to_close(panel: Panel) -> pd.DataFrame:
    return (panel.close / panel.open - 1.0).where(traded(panel))


def close_to_open(panel: Panel) -> pd.DataFrame:
    """Overnight: today's open plus a dividend going ex today, over the previous close."""
    previous = panel.close.shift(1)
    return ((panel.open + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def close_to_close(panel: Panel) -> pd.DataFrame:
    previous = panel.close.shift(1)
    return ((panel.close + panel.dividends.fillna(0.0)) / previous - 1.0).where(traded(panel))


def price_close_to_close(panel: Panel) -> pd.DataFrame:
    """Close over the previous close, without the dividend: how a price index moves (design §9)."""
    return (panel.close / panel.close.shift(1) - 1.0).where(traded(panel))


def quoted(panel: Panel) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Open and close as quoted on the day: yfinance's backward split adjustment undone."""
    ratio = panel.splits.where(panel.splits > 0, 1.0).fillna(1.0)
    after = ratio.iloc[::-1].cumprod().iloc[::-1].shift(-1, fill_value=1.0)
    return panel.open * after, panel.close * after


def trailing_value(panel: Panel, lookback: int = LOOKBACK) -> pd.DataFrame:
    """Median traded value over the ``lookback`` trading days before each day (R2)."""
    value = panel.close * panel.volume.fillna(0.0)
    median = value.rolling(lookback, min_periods=lookback).median().shift(1)
    dates = value.index.to_series()
    pit.check_lookback(pd.Series(dates.shift(1).to_numpy(), index=value.index))
    return median


def _sector_totals(frame: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """Per-day sums of the columns of each sector, spread back onto the columns."""
    codes = sector.reindex(frame.columns).to_numpy()
    totals = frame.T.groupby(codes).sum().T
    return pd.DataFrame(
        totals.reindex(columns=codes).to_numpy(), index=frame.index, columns=frame.columns
    )


def liquidity_weights(median: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """H1 main basket: every name, weighted by its trailing median traded value (§7.1)."""
    value = median.where(median > 0).fillna(0.0)
    totals = _sector_totals(value, sector)
    return (value / totals.where(totals > 0)).fillna(0.0)


def _rank_in_sector(score: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    codes = sector.reindex(score.columns).to_numpy()
    return score.T.groupby(codes).rank(ascending=False, method="first").T


def top_equal_weights(
    median: pd.DataFrame, sector: pd.Series, n: int = TOP_SECONDARY
) -> pd.DataFrame:
    """H1 secondary basket: the n most traded names of each sector, equally weighted (§7.1)."""
    chosen = (_rank_in_sector(median.where(median > 0), sector) <= n).astype(float)
    totals = _sector_totals(chosen, sector)
    return (chosen / totals.where(totals > 0)).fillna(0.0)


def h2_picks(
    median: pd.DataFrame,
    quoted_close: pd.DataFrame,
    sector: pd.Series,
    budget: float,
    per_sector: int = PER_SECTOR,
) -> pd.DataFrame:
    """H2: per sector, the most traded names whose 100-share lot fits the budget (§7.2).

    The lot is priced at the previous day's quoted close, so the picks of day d use d-1 only.
    """
    previous = quoted_close.shift(1)
    affordable = (previous * LOT <= budget) & (median > 0)
    rank = _rank_in_sector(median.where(affordable), sector)
    return rank <= per_sector


def basket_returns(weights: pd.DataFrame, returns: pd.DataFrame, sector: pd.Series) -> pd.DataFrame:
    """Weighted mean return of each sector's names that traded; weights renormalised to 1."""
    weights = weights.reindex(index=returns.index, columns=returns.columns, fill_value=0.0)
    live = weights.where(returns.notna() & (weights > 0), 0.0)
    codes = sector.reindex(returns.columns).to_numpy()
    num = (live * returns.fillna(0.0)).T.groupby(codes).sum().T
    den = live.T.groupby(codes).sum().T
    out = num / den.where(den > 0)
    return out.reindex(columns=list(SECTORS))
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `35 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Build the sector baskets and their returns"
```

---

### Task 7: The paper's long-short and the cash-only strategy

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/strategy.py`
- Test: `sector_leadlag_lab/tests/test_strategy.py`

**Interfaces:**
- Consumes: `baskets.LOT`, `baskets.PER_SECTOR` (Task 6); `signal.top_sectors` (Task 5).
- Produces: `sector_leadlag.strategy.TOP = 5`, `CAPITAL = 5_000_000.0`, `long_short_returns(weights, returns) -> pd.Series` (Σ w·r per day; a held sector without a return counts 0), `CashLong(returns: Series, names: Series, invested: Series)`, `cash_long(signal, picks, quoted_open, quoted_close, traded, sector, *, capital=CAPITAL, cost_bp=0.0, top=TOP, per_sector=PER_SECTOR) -> CashLong` (D10), `selection_spread(signal, pick_returns, top=TOP) -> pd.Series` (mean of the top sectors minus mean of all 17).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_strategy.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.strategy import cash_long, long_short_returns, selection_spread

DAYS = pd.bdate_range("2026-01-05", periods=3)
SECTORS = list(range(1, 18))


def test_long_short_returns():
    weights = pd.DataFrame(0.0, index=DAYS, columns=SECTORS)
    weights.loc[DAYS[0], [1, 2]] = [0.5, -0.5]
    returns = pd.DataFrame(0.01, index=DAYS, columns=SECTORS)
    returns.loc[DAYS[0], 2] = -0.01
    out = long_short_returns(weights, returns)
    assert out.tolist() == pytest.approx([0.01, 0.0, 0.0])


def _signal(order: list[int]) -> pd.DataFrame:
    """A signal whose top five sectors are ``order``."""
    values = np.zeros(17)
    for rank, code in enumerate(order):
        values[code - 1] = 10.0 - rank
    return pd.DataFrame([values], index=DAYS[1:2], columns=SECTORS)


def test_cash_long_buys_whole_lots_of_the_top_sectors_and_pays_costs_both_ways():
    columns = ["a", "b", "c"]
    sector = pd.Series([1, 1, 3], index=columns)
    picks = pd.DataFrame(True, index=DAYS, columns=columns)
    traded = pd.DataFrame(True, index=DAYS, columns=columns)
    traded.loc[DAYS[1], "b"] = False
    quoted_close = pd.DataFrame(
        [[1000.0, 3000.0, 500.0], [1010.0, 3000.0, 505.0], [1000.0, 3000.0, 500.0]],
        index=DAYS,
        columns=columns,
    )
    quoted_open = quoted_close.copy()
    quoted_open.loc[DAYS[1]] = [1000.0, 3000.0, 500.0]
    signal = _signal([1, 2, 4, 5, 6])  # sector 3 (name c) is not among the top five
    out = cash_long(
        signal, picks, quoted_open, quoted_close, traded, sector, capital=1_500_000.0, cost_bp=10.0
    )
    # budget 100,000 yen per name: a buys 100 shares at 1,000 (previous close 1,000)
    pnl = 100 * (1010 - 1000) - 0.001 * 100 * (1000 + 1010)
    assert out.returns.iloc[0] == pytest.approx(pnl / 1_500_000)
    assert out.names.iloc[0] == 1  # b did not trade, c's sector was not chosen
    assert out.invested.iloc[0] == pytest.approx(100 * 1000 / 1_500_000)


def test_cash_long_skips_a_name_whose_lot_does_not_fit():
    columns = ["a"]
    sector = pd.Series([1], index=columns)
    picks = pd.DataFrame(True, index=DAYS, columns=columns)
    traded = pd.DataFrame(True, index=DAYS, columns=columns)
    price = pd.DataFrame(5000.0, index=DAYS, columns=columns)
    out = cash_long(
        _signal([1, 2, 3, 4, 5]), picks, price, price, traded, sector, capital=1_500_000.0
    )
    assert out.names.iloc[0] == 0 and out.returns.iloc[0] == 0.0


def test_selection_spread_is_the_top_five_minus_all():
    returns = pd.DataFrame([np.arange(17) / 100.0], index=DAYS[1:2], columns=SECTORS)
    spread = selection_spread(_signal([17, 16, 15, 14, 13]), returns)
    assert spread.iloc[0] == pytest.approx(np.mean([0.16, 0.15, 0.14, 0.13, 0.12]) - 0.08)
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_strategy.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.strategy'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/strategy.py` (create)

```python
"""Portfolio returns: the paper's long-short and the cash-only long version (design §3.1, §7.2)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .baskets import LOT, PER_SECTOR
from .signal import top_sectors

TOP = 5
CAPITAL = 5_000_000.0


def long_short_returns(weights: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """The sum of w_{j,d} r_{j,d} on each day with a signal; a day without positions earns 0."""
    r = returns.reindex(index=weights.index, columns=weights.columns)
    return (weights * r).where(weights != 0).sum(axis=1)


@dataclass(frozen=True)
class CashLong:
    returns: pd.Series  # profit and loss over the capital, after costs
    names: pd.Series  # names bought at the open
    invested: pd.Series  # money paid at the open over the capital


def cash_long(
    signal: pd.DataFrame,
    picks: pd.DataFrame,
    quoted_open: pd.DataFrame,
    quoted_close: pd.DataFrame,
    traded: pd.DataFrame,
    sector: pd.Series,
    *,
    capital: float = CAPITAL,
    cost_bp: float = 0.0,
    top: int = TOP,
    per_sector: int = PER_SECTOR,
) -> CashLong:
    """Buy the picks of the top sectors at the open, sell them at the close (design §3.1, §7.2).

    Each name gets capital / (top x per_sector); shares are that budget over 100 x the previous
    quoted close, rounded down to whole lots. Costs are ``cost_bp`` of the traded value on the
    buy and on the sell. Unspent money earns nothing.
    """
    days = signal.index
    budget = capital / (top * per_sector)
    columns = picks.columns
    codes = sector.reindex(columns).to_numpy()
    chosen = top_sectors(signal, top).to_numpy()[:, codes - 1]
    hold = (
        picks.reindex(index=days, columns=columns, fill_value=False).to_numpy(dtype=bool)
        & chosen
        & traded.reindex(index=days, columns=columns, fill_value=False).to_numpy(dtype=bool)
    )
    previous = quoted_close.shift(1).reindex(index=days, columns=columns).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        lots = np.floor(budget / (LOT * previous))
    shares = np.where(hold & np.isfinite(lots), lots * LOT, 0.0)
    o = quoted_open.reindex(index=days, columns=columns).to_numpy()
    c = quoted_close.reindex(index=days, columns=columns).to_numpy()
    cost = cost_bp / 1e4
    pnl = np.where(shares > 0, shares * (c - o) - cost * shares * (o + c), 0.0)
    paid = np.where(shares > 0, shares * o, 0.0)
    return CashLong(
        pd.Series(pnl.sum(axis=1) / capital, index=days),
        pd.Series((shares > 0).sum(axis=1), index=days),
        pd.Series(paid.sum(axis=1) / capital, index=days),
    )


def selection_spread(signal: pd.DataFrame, pick_returns: pd.DataFrame, top: int = TOP) -> pd.Series:
    """H2 2: the top sectors' pick baskets minus all 17 (equal weights, no lots, no costs)."""
    chosen = top_sectors(signal, top)
    r = pick_returns.reindex(index=signal.index, columns=signal.columns)
    return (r.where(chosen).mean(axis=1) - r.mean(axis=1)).dropna()
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `39 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add the paper's long-short and the cash-only strategy"
```

---

### Task 8: Panel regression, bootstraps, H3 and the verdict

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/evaluate.py`
- Test: `sector_leadlag_lab/tests/test_evaluate.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `sector_leadlag.evaluate.N_BOOT = 10_000`, `MEAN_BLOCK = 20`, `SEED = 20261019`, `ALPHA = 0.05`, `GAMMA = 5.0`, `YEAR = 252`, `CHUNK = 500`; `two_way_demean(values, day, sector, *, tol=1e-12) -> ndarray`; `PanelFit(beta: tuple, se: tuple, t: float, p: float, n_obs: int, n_days: int, days: DatetimeIndex, score: ndarray, weight: ndarray)` with `.summary()`; `panel_fit(returns, signal, controls=()) -> PanelFit` (D7; `beta[0]` is the signal's); `stationary_indices(n, n_boot, mean_block, rng) -> ndarray`; `ratio_interval(numerator, denominator, *, n_boot=N_BOOT, mean_block=MEAN_BLOCK, seed=SEED, level=0.95) -> (float, float)` (D8); `MeanTest(mean, p, days)`; `mean_test(x, *, n_boot=N_BOOT, mean_block=MEAN_BLOCK, seed=SEED) -> MeanTest` (D9); `describe(daily) -> {"mean_ann", "vol_ann", "sharpe", "cer", "cumulative", "days"}`; `monthly_metrics(daily) -> {"ar", "risk", "rr", "mdd", "months"}`; `h3_label(b2, a, alpha=ALPHA) -> {"label", "p_below_zero", "p_below_a", "mean_b2_ann", "mean_a_ann", "days_b2"}`; `Evidence(replicated, h1_p, beta_b_period_b, h2_p_cash, h2_p_spread, robust, b_mean_cash, b_mean_spread)`; `verdict(e, alpha=ALPHA) -> str` (spec §3.4).

The within estimator is checked against OLS with explicit day and sector dummies on an unbalanced panel, and its clustered standard error against the same hand computation (spec §11).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_evaluate.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.evaluate import (
    Evidence,
    describe,
    h3_label,
    mean_test,
    monthly_metrics,
    panel_fit,
    ratio_interval,
    two_way_demean,
    verdict,
)


def _panel(seed: int, days: int = 60, sectors: int = 5, beta: float = 0.5, holes: float = 0.2):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2026-01-05", periods=days)
    x = pd.DataFrame(rng.normal(size=(days, sectors)), index=index, columns=range(1, sectors + 1))
    day_effect = rng.normal(size=(days, 1))
    sector_effect = rng.normal(size=(1, sectors))
    y = beta * x + day_effect + sector_effect + rng.normal(size=(days, sectors))
    y = y.mask(rng.random((days, sectors)) < holes)
    return y, x


def _dummy_ols(y: pd.DataFrame, x: pd.DataFrame):
    """The same regression with explicit dummies, and its day-clustered standard error."""
    stack = pd.DataFrame({"y": y.stack(), "x": x.stack()}).dropna()
    day = stack.index.get_level_values(0)
    sector = stack.index.get_level_values(1)
    dummies = pd.get_dummies(pd.Series(day), drop_first=False).to_numpy(float)
    sector_dummies = pd.get_dummies(pd.Series(sector), drop_first=True).to_numpy(float)
    design = np.column_stack([stack["x"].to_numpy(), dummies, sector_dummies])
    coef, *_ = np.linalg.lstsq(design, stack["y"].to_numpy(), rcond=None)
    resid = stack["y"].to_numpy() - design @ coef
    bread = np.linalg.pinv(design.T @ design)
    codes = pd.factorize(day)[0]
    scores = np.zeros((codes.max() + 1, design.shape[1]))
    np.add.at(scores, codes, design * resid[:, None])
    g, n = codes.max() + 1, len(resid)
    k = 1 + len(np.unique(sector)) - 1
    cov = g / (g - 1) * (n - 1) / (n - k) * bread @ scores.T @ scores @ bread
    return coef[0], np.sqrt(cov[0, 0])


def test_the_within_estimator_matches_ols_with_dummies():
    y, x = _panel(1)
    fit = panel_fit(y, x)
    beta, se = _dummy_ols(y, x)
    assert fit.beta[0] == pytest.approx(beta, rel=1e-9)
    assert fit.se[0] == pytest.approx(se, rel=1e-6)
    assert fit.days.equals(y.index[y.notna().any(axis=1)])
    assert fit.score.sum() / fit.weight.sum() == pytest.approx(fit.beta[0], rel=1e-9)


def test_a_true_effect_is_found_and_a_null_one_is_not():
    y, x = _panel(2, days=400, beta=0.3)
    assert panel_fit(y, x).p < 0.01
    y, x = _panel(3, days=400, beta=0.0)
    assert panel_fit(y, x).p > 0.01


def test_a_control_enters_the_same_regression():
    y, x = _panel(4, days=200)
    control = x * 0.0 + np.random.default_rng(5).normal(size=x.shape)
    fit = panel_fit(y + 2.0 * control, x, [control])
    assert fit.beta[1] == pytest.approx(2.0, abs=0.2)


def test_demeaning_a_balanced_panel_takes_both_means_out():
    rng = np.random.default_rng(6)
    values = rng.normal(size=(12, 3))
    stacked = values.ravel()
    day = np.repeat(np.arange(12), 3)
    sector = np.tile(np.arange(3), 12)
    out = two_way_demean(stacked, day, sector)[:, 0].reshape(12, 3)
    expected = values - values.mean(axis=1, keepdims=True) - values.mean(axis=0) + values.mean()
    assert np.allclose(out, expected)


def test_ratio_interval_is_reproducible_and_holds_the_estimate():
    y, x = _panel(7, days=300, beta=0.4)
    y2, _ = _panel(8, days=300, beta=0.8)
    numerator, denominator = panel_fit(y, x), panel_fit(y2, x)
    first = ratio_interval(numerator, denominator, n_boot=400)
    assert first == ratio_interval(numerator, denominator, n_boot=400)
    assert first[0] < numerator.beta[0] / denominator.beta[0] < first[1]


def test_mean_test():
    rng = np.random.default_rng(9)
    days = pd.bdate_range("2020-01-01", periods=1500)
    assert (
        mean_test(pd.Series(0.002 + 0.01 * rng.normal(size=1500), index=days), n_boot=500).p < 0.01
    )
    flat = mean_test(pd.Series(0.0, index=days), n_boot=200)
    assert flat.p == 1.0 and flat.days == 1500


def test_describe_and_the_papers_monthly_metrics():
    days = pd.bdate_range("2026-01-01", "2026-03-31")
    r = pd.Series(0.001, index=days)
    stats = describe(r)
    assert stats["mean_ann"] == pytest.approx(0.252) and stats["sharpe"] == 0.0
    assert stats["cumulative"] == pytest.approx(1.001 ** len(days) - 1)
    r.loc["2026-02"] = -0.002
    m = monthly_metrics(r)
    assert m["months"] == 3 and m["mdd"] == pytest.approx(1 - 0.998 ** len(r.loc["2026-02"]))


def test_h3_labels():
    a = pd.Series(np.tile([0.006, -0.004], 1000))  # mean 0.001
    falling = pd.Series(np.tile([-0.001, -0.007], 24))  # mean -0.004, clearly below 0
    assert h3_label(falling, a)["label"] == "decay_continued"
    recovered = pd.Series(np.tile([0.007, -0.003], 24))  # mean 0.002, not below A
    assert h3_label(recovered, a)["label"] == "decay_faded"
    noisy = pd.Series(np.tile([0.019, -0.021], 24))  # mean -0.001, not significant
    assert h3_label(noisy, a)["label"] == "unclear"
    high_a = pd.Series(np.tile([0.011, 0.009], 1000))  # mean 0.01
    flat = pd.Series(np.tile([0.0011, -0.0009], 24))  # mean 0.0001: >= 0 but far below A
    out = h3_label(flat, high_a)
    assert out["label"] == "unclear" and out["days_b2"] == 48


def test_verdict_branches():
    good = Evidence(True, 0.001, 1e-4, 0.01, 0.01, True, 1e-4, 1e-4)
    assert verdict(good) == "usable"
    assert verdict(Evidence(False, *[0.0] * 7)) == "replication_failed"
    assert verdict(Evidence(True, 0.2, 1e-4, 0.01, 0.01, True, 1e-4, 1e-4)) == "etf_only"
    assert (
        verdict(Evidence(True, 0.001, -1e-4, 0.01, 0.01, True, 1e-4, 1e-4)) == "real_then_decayed"
    )
    assert verdict(Evidence(True, 0.001, 1e-4, 0.2, 0.01, True, 1e-4, 1e-4)) == "real_not_usable"
    assert verdict(Evidence(True, 0.001, 1e-4, 0.01, 0.01, False, 1e-4, 1e-4)) == "real_not_usable"
    assert verdict(Evidence(True, 0.001, 1e-4, 0.01, 0.01, True, -1e-4, 1e-4)) == "real_not_usable"
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_evaluate.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.evaluate'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/evaluate.py` (create)

```python
"""Panel regressions, bootstraps, the H3 label and the verdict (design §3.3, §3.4).

The panel regression is the decay paper's eq. (9) without its post-publication terms:
r_{j,d} = a_j + d_d + b sz_{j,d} + e, with sector and day fixed effects removed by alternating
projections and standard errors clustered by day (the day effects are nested in the clusters, so
only the sector effects count as parameters in the small-sample factor).
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

N_BOOT = 10_000
MEAN_BLOCK = 20
SEED = 20261019
ALPHA = 0.05
GAMMA = 5.0
YEAR = 252
CHUNK = 500


def two_way_demean(
    values: np.ndarray, day: np.ndarray, sector: np.ndarray, *, tol: float = 1e-12
) -> np.ndarray:
    """Remove day and sector means from every column (alternating projections)."""
    x = np.array(values, dtype=float, copy=True).reshape(len(day), -1)
    n_day, n_sector = int(day.max()) + 1, int(sector.max()) + 1
    per_day = np.maximum(np.bincount(day, minlength=n_day), 1)
    per_sector = np.maximum(np.bincount(sector, minlength=n_sector), 1)
    for column in range(x.shape[1]):
        v = x[:, column]
        scale = max(1.0, float(np.abs(v).max()))
        for _ in range(10_000):
            by_day = np.bincount(day, v, n_day) / per_day
            v = v - by_day[day]
            by_sector = np.bincount(sector, v, n_sector) / per_sector
            v = v - by_sector[sector]
            if max(np.abs(by_day).max(), np.abs(by_sector).max()) < tol * scale:
                break
        x[:, column] = v
    return x


@dataclass(frozen=True)
class PanelFit:
    beta: tuple[float, ...]  # the signal first, then the controls
    se: tuple[float, ...]
    t: float  # of the signal
    p: float  # one-sided: the signal's coefficient is positive
    n_obs: int
    n_days: int
    days: pd.DatetimeIndex
    score: np.ndarray  # per day: sum of x*y over sectors, after the fixed effects
    weight: np.ndarray  # per day: sum of x*x

    def summary(self) -> dict:
        return {
            "beta": self.beta[0],
            "se": self.se[0],
            "t": self.t,
            "p": self.p,
            "obs": self.n_obs,
            "days": self.n_days,
        }


def panel_fit(
    returns: pd.DataFrame, signal: pd.DataFrame, controls: Sequence[pd.DataFrame] = ()
) -> PanelFit:
    index = returns.index.intersection(signal.index)
    columns = [c for c in returns.columns if c in signal.columns]
    arrays = [
        frame.reindex(index=index, columns=columns).to_numpy(dtype=float)
        for frame in (returns, signal, *controls)
    ]
    mask = np.logical_and.reduce([np.isfinite(a) for a in arrays])
    rows, cols = np.nonzero(mask)
    used_days, day = np.unique(rows, return_inverse=True)
    used_sectors, sector = np.unique(cols, return_inverse=True)
    data = two_way_demean(np.column_stack([a[mask] for a in arrays]), day, sector)
    y, x = data[:, 0], data[:, 1:]
    xtx = x.T @ x
    beta = np.linalg.solve(xtx, x.T @ y)
    resid = y - x @ beta
    n, g, k = len(y), len(used_days), x.shape[1] + len(used_sectors) - 1
    scores = np.column_stack([np.bincount(day, x[:, j] * resid, g) for j in range(x.shape[1])])
    bread = np.linalg.inv(xtx)
    factor = g / (g - 1) * (n - 1) / (n - k)
    se = np.sqrt(np.diag(factor * bread @ (scores.T @ scores) @ bread))
    t = float(beta[0] / se[0])
    return PanelFit(
        tuple(float(b) for b in beta),
        tuple(float(s) for s in se),
        t,
        float(stats.t.sf(t, g - 1)),
        n,
        g,
        index[used_days],
        np.bincount(day, x[:, 0] * y, g),
        np.bincount(day, x[:, 0] ** 2, g),
    )


def stationary_indices(
    n: int, n_boot: int, mean_block: int, rng: np.random.Generator
) -> np.ndarray:
    """Politis-Romano stationary bootstrap: blocks of geometric length with the given mean."""
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    restart = rng.random((n_boot, n)) < 1.0 / mean_block
    jumps = rng.integers(0, n, (n_boot, n))
    for t in range(1, n):
        idx[:, t] = np.where(restart[:, t], jumps[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _draws(n: int, n_boot: int, mean_block: int, seed: int) -> Iterator[np.ndarray]:
    rng = np.random.default_rng(seed)
    done = 0
    while done < n_boot:
        size = min(CHUNK, n_boot - done)
        yield stationary_indices(n, size, mean_block, rng)
        done += size


def ratio_interval(
    numerator: PanelFit,
    denominator: PanelFit,
    *,
    n_boot: int = N_BOOT,
    mean_block: int = MEAN_BLOCK,
    seed: int = SEED,
    level: float = 0.95,
) -> tuple[float, float]:
    """Interval of b_num / b_den from resampled days (the sector effects stay at their estimates)."""
    days = numerator.days.intersection(denominator.days)
    parts = [
        pd.Series(values, index=fit.days).reindex(days).to_numpy()
        for fit in (numerator, denominator)
        for values in (fit.score, fit.weight)
    ]
    ratios = []
    for idx in _draws(len(days), n_boot, mean_block, seed):
        top = parts[0][idx].sum(axis=1) / parts[1][idx].sum(axis=1)
        bottom = parts[2][idx].sum(axis=1) / parts[3][idx].sum(axis=1)
        ratios.append(top / bottom)
    low, high = np.quantile(np.concatenate(ratios), [(1 - level) / 2, (1 + level) / 2])
    return float(low), float(high)


@dataclass(frozen=True)
class MeanTest:
    mean: float  # daily
    p: float  # one-sided: the mean is positive
    days: int


def mean_test(
    x: pd.Series, *, n_boot: int = N_BOOT, mean_block: int = MEAN_BLOCK, seed: int = SEED
) -> MeanTest:
    """Centred stationary bootstrap: p = (1 + #{m* - m >= m}) / (B + 1)."""
    v = x.dropna().to_numpy(dtype=float)
    m = float(v.mean())
    star = np.concatenate([v[idx].mean(axis=1) for idx in _draws(len(v), n_boot, mean_block, seed)])
    return MeanTest(m, float((1 + np.sum(star - m >= m)) / (n_boot + 1)), len(v))


def describe(daily: pd.Series) -> dict:
    r = daily.dropna()
    sd = float(r.std(ddof=1)) if len(r) > 1 else 0.0
    mean = float(r.mean()) if len(r) else float("nan")
    return {
        "mean_ann": YEAR * mean,
        "vol_ann": float(np.sqrt(YEAR) * sd),
        "sharpe": float(np.sqrt(YEAR) * mean / sd) if sd > 0 else 0.0,
        "cer": YEAR * (mean - GAMMA / 2 * sd**2),
        "cumulative": float((1 + r).prod() - 1),
        "days": len(r),
    }


def monthly_metrics(daily: pd.Series) -> dict:
    """The strategy paper's AR, RISK, R/R and maximum drawdown, from monthly compounded returns."""
    r = daily.dropna()
    monthly = (1 + r).groupby(r.index.to_period("M")).prod() - 1
    wealth = (1 + monthly).cumprod()
    ar = float(12 * monthly.mean())
    risk = float(np.sqrt(12) * monthly.std(ddof=1))
    return {
        "ar": ar,
        "risk": risk,
        "rr": ar / risk if risk > 0 else 0.0,
        "mdd": float((1 - wealth / wealth.cummax()).max()),
        "months": len(monthly),
    }


def h3_label(b2: pd.Series, a: pd.Series, alpha: float = ALPHA) -> dict:
    """Did the ETF long-short keep losing after the decay paper's sample (design §3.3)?"""
    x, y = b2.dropna().to_numpy(), a.dropna().to_numpy()
    p_zero = float(stats.ttest_1samp(x, 0.0, alternative="less").pvalue)
    p_drop = float(stats.ttest_ind(x, y, equal_var=False, alternative="less").pvalue)
    if p_zero < alpha:
        label = "decay_continued"
    elif x.mean() >= 0 and p_drop >= alpha:
        label = "decay_faded"
    else:
        label = "unclear"
    return {
        "label": label,
        "p_below_zero": p_zero,
        "p_below_a": p_drop,
        "mean_b2_ann": YEAR * float(x.mean()),
        "mean_a_ann": YEAR * float(y.mean()),
        "days_b2": len(x),
    }


@dataclass(frozen=True)
class Evidence:
    replicated: bool  # G0: some pairing reproduced the ETF result
    h1_p: float  # period A, basket coefficient > 0
    beta_b_period_b: float  # the basket coefficient in period B
    h2_p_cash: float  # period A, the cash-only strategy beats doing nothing
    h2_p_spread: float  # period A, the chosen sectors beat all 17
    robust: bool  # the signs of both stay at 2 bp, at 3 and at 10 million yen
    b_mean_cash: float  # period B means of the two
    b_mean_spread: float


def verdict(e: Evidence, alpha: float = ALPHA) -> str:
    if not e.replicated:
        return "replication_failed"
    if not e.h1_p < alpha:
        return "etf_only"
    if not e.beta_b_period_b > 0:
        return "real_then_decayed"
    if (
        e.h2_p_cash < alpha
        and e.h2_p_spread < alpha
        and e.robust
        and e.b_mean_cash > 0
        and e.b_mean_spread > 0
    ):
        return "usable"
    return "real_not_usable"
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `48 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add the panel regression, bootstraps, H3 and the verdict"
```

---

### Task 9: Rotated worlds, the planted effect and stale opens

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/synthetic.py`
- Test: `sector_leadlag_lab/tests/test_synthetic.py`

**Interfaces:**
- Consumes: `evaluate.SEED` (Task 8).
- Produces: `sector_leadlag.synthetic.SHIFTS = 20`, `MIN_SHIFT = 60`, `shift_amounts(n, count=SHIFTS, *, seed=SEED, min_shift=MIN_SHIFT) -> list[int]` (D13), `circular_shift(frame, k) -> pd.DataFrame` (values rotated down k rows, dates kept), `plant(returns, sz, beta) -> pd.DataFrame`, `stale_returns(o2c, price_c2c, c2o, fraction, *, mode: "random" | "largest_gap", seed=SEED) -> pd.DataFrame` (D15; ValueError `unknown mode` otherwise).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_synthetic.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.synthetic import circular_shift, plant, shift_amounts, stale_returns


def test_shifts_stay_away_from_the_original_alignment():
    shifts = shift_amounts(1000)
    assert len(shifts) == 20 and all(60 <= k < 940 for k in shifts)
    assert shifts == shift_amounts(1000)


def test_circular_shift_moves_values_not_dates():
    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0]}, index=pd.bdate_range("2026-01-05", periods=4))
    out = circular_shift(frame, 1)
    assert out.index.equals(frame.index) and out["x"].tolist() == [4.0, 1.0, 2.0, 3.0]


def test_plant_adds_beta_times_the_signal_where_returns_exist():
    returns = pd.DataFrame([[0.01, np.nan]], columns=[1, 2])
    sz = pd.DataFrame([[1.0, -1.0]], columns=[1, 2])
    out = plant(returns, sz, 0.002)
    assert out.iloc[0, 0] == pytest.approx(0.012) and np.isnan(out.iloc[0, 1])


def test_stale_opens_replace_the_largest_gaps_first():
    o2c = pd.DataFrame([[0.01, 0.02, 0.03, 0.04]], columns=list("abcd"))
    c2c = pd.DataFrame([[0.11, 0.12, 0.13, 0.14]], columns=list("abcd"))
    c2o = pd.DataFrame([[0.001, -0.05, 0.002, 0.003]], columns=list("abcd"))
    out = stale_returns(o2c, c2c, c2o, 0.25, mode="largest_gap")
    assert out.iloc[0].tolist() == [0.01, 0.12, 0.03, 0.04]
    rng_out = stale_returns(o2c, c2c, c2o, 1.0, mode="random")
    assert rng_out.iloc[0].tolist() == c2c.iloc[0].tolist()
    with pytest.raises(ValueError, match="unknown mode"):
        stale_returns(o2c, c2c, c2o, 0.1, mode="other")
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_synthetic.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.synthetic'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/synthetic.py` (create)

```python
"""G1's broken worlds, the planted effect of the power report, and the stale-open diagnostic.

G1 (design §8) rotates the US returns against Japan so that no US day lines up with the
Japanese day it used to precede; the signal is then rebuilt from the rotated returns. The
stale-open diagnostic (design §9) imitates an index whose opening value still carries the
previous close of the names that have not opened yet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .evaluate import SEED

SHIFTS = 20
MIN_SHIFT = 60


def shift_amounts(
    n: int, count: int = SHIFTS, *, seed: int = SEED, min_shift: int = MIN_SHIFT
) -> list[int]:
    rng = np.random.default_rng(seed)
    return [int(k) for k in rng.integers(min_shift, n - min_shift, size=count)]


def circular_shift(frame: pd.DataFrame, k: int) -> pd.DataFrame:
    """Rows rotated down by k positions; the dates stay where they are."""
    return pd.DataFrame(
        np.roll(frame.to_numpy(), k, axis=0), index=frame.index, columns=frame.columns
    )


def plant(returns: pd.DataFrame, sz: pd.DataFrame, beta: float) -> pd.DataFrame:
    """Returns plus beta times the standardised signal, where both exist."""
    signal = sz.reindex(index=returns.index, columns=returns.columns)
    return returns + beta * signal.fillna(0.0).where(returns.notna())


def stale_returns(
    o2c: pd.DataFrame,
    price_c2c: pd.DataFrame,
    c2o: pd.DataFrame,
    fraction: float,
    *,
    mode: str,
    seed: int = SEED,
) -> pd.DataFrame:
    """Each name's return from an opening value that, for a share of names, is the previous close.

    ``mode`` "random" marks a random ``fraction`` of the names each day; "largest_gap" marks the
    names with the largest overnight moves, which are the ones that open late (design §2.3).
    """
    live = o2c.notna() & price_c2c.notna()
    if mode == "random":
        rng = np.random.default_rng(seed)
        stale = pd.DataFrame(rng.random(o2c.shape) < fraction, index=o2c.index, columns=o2c.columns)
    elif mode == "largest_gap":
        gap = c2o.abs().where(live)
        rank = gap.rank(axis=1, ascending=False, method="first")
        stale = rank.le(np.ceil(fraction * live.sum(axis=1)), axis=0)
    else:
        raise ValueError(f"unknown mode {mode!r}")
    return o2c.where(~(stale & live), price_c2c)
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `52 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add G1's rotated worlds, the planted effect and stale opens"
```

---

### Task 10: The study and the shared stage builders

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/study.py`, `sector_leadlag_lab/src/sector_leadlag/stages.py`
- Modify: `sector_leadlag_lab/tests/conftest.py` (append the synthetic worlds)
- Test: `sector_leadlag_lab/tests/test_study.py`, `sector_leadlag_lab/tests/test_stages.py`

**Interfaces:**
- Consumes: `store.RAW_ROOT`, `store.indicators`, `store.read_latest` (Task 1); `jpx`, `yf.US_SECTORS`, `yf.parse_csv` (Task 2); `timing` (Task 4); `signal` (Task 5); `baskets` (Task 6); `strategy` (Task 7); `evaluate.panel_fit`, `evaluate.describe`, `evaluate.PanelFit` (Task 8).
- Produces:
  - `sector_leadlag.study`: `PANEL_START = 2009-06-01`, `A`, `B`, `B1`, `B2`, `C = (2026-10-06, 2099-12-31)`, `ORIGINAL = (2015-01-01, 2025-12-31)`, `LONGER_SESSION = 2024-11-05`, `FIELDS`; `Study(listing, us_adj, us_days, jp_days, s_map, etf: Panel, stocks: Panel, missing: tuple[str, ...])` (frozen) with `.us_returns() -> DataFrame` and `.etf_c2c() -> DataFrame` (ETF Adj Close C2C on the Japanese days; columns 1–17); `build_panel(frames: dict, days, sector) -> Panel`; `load_study(root: Path = RAW_ROOT) -> Study` (FileNotFoundError naming `sector-leadlag snapshot` when no TOPIX500 prices are stored).
  - `sector_leadlag.stages`: `SCALE = 1e-4`, `MIN_DAYS = 5`, `cut(frame, period)`, `build_signal(study, variant, *, us_ret=None, jp_c2c=None, spec=Spec()) -> DataFrame` (C_full and C0 from the same pairing), `Returns(o2c, c2o, c2c)`, `etf_returns(study) -> Returns`, `basket_series(study, weights) -> Returns`, `Baskets(median, main, top10)`, `h1_baskets(study) -> Baskets`, `etf_long_short(signal, study, returns) -> Series`, `basket_long_short(signal, returns) -> Series`, `fit_summary(fit) -> {"beta_1e4", "se_1e4", "t", "p", "obs", "days"}`, `fit_in(returns, sz, period, controls=()) -> dict | None` (None below `MIN_DAYS` days), `h2_series(study, signal, median, *, capital=CAPITAL, cost_bp=0.0) -> (CashLong, Series)` (H2 1 and H2 2 on the days of `signal`), `cash_summary(cash) -> dict` (`describe` plus `mean_names` and `invested`).
  - Fixtures: `decayed_world` (session; the lead is real in the stocks and turns negative in the ETFs from period B on) and `etf_only_world` (session; the lead is in the ETFs only). Both are `Study` objects on synthetic prices 2009-06..2026-10 with 2 names per sector; the signal comes from close-to-close returns alone, and the opens are then set so that O2C = lead × 0.002 × sz + noise.

- [ ] **Step 1: Add the worlds and write the failing tests**

Append to `sector_leadlag_lab/tests/conftest.py`, two blank lines after the `make_panel` fixture:

```python
def _world(*, seed: int = 0, etf_lead=(1.0, -1.0), stock_lead=(1.0, 1.0), names: int = 2):
    """A study on synthetic prices, 2009-06 to 2026-10.

    The close-to-close returns carry no lead, so the signal (built from them alone) is known
    before the opens are made. Each open is then set so that the open-to-close return is
    lead x 0.002 x sz + noise: the first value of ``etf_lead`` and ``stock_lead`` before
    本番 B, the second from B on.
    """
    from dataclasses import replace
    from datetime import date

    from sector_leadlag.baskets import SECTORS, Panel
    from sector_leadlag.data.jpx import Listing
    from sector_leadlag.data.yf import US_SECTORS
    from sector_leadlag.signal import cross_standardize
    from sector_leadlag.stages import build_signal
    from sector_leadlag.study import B, Study
    from sector_leadlag.timing import last_us_before

    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2009-06-01", "2026-10-16")
    jp_days = pd.DatetimeIndex(days[rng.random(len(days)) > 0.04], name="date")
    us_days = pd.DatetimeIndex(days[rng.random(len(days)) > 0.04], name="date")
    us_ret = 1 + 0.01 * rng.normal(size=(len(us_days), 11))
    us = pd.DataFrame(100 * np.cumprod(us_ret, axis=0), index=us_days, columns=list(US_SECTORS))
    us.loc[:"2015-10-07", "XLRE"] = np.nan
    us.loc[:"2018-06-18", "XLC"] = np.nan
    market = 0.008 * rng.normal(size=(len(jp_days), 1))
    etf_c2c = market + 0.006 * rng.normal(size=(len(jp_days), 17))
    etf_close = pd.DataFrame(
        1000 * np.cumprod(1 + etf_c2c, axis=0), index=jp_days, columns=list(SECTORS)
    )
    codes = [f"{1000 + 10 * k + i}" for k in SECTORS for i in range(names)]
    sector = pd.Series([k for k in SECTORS for _ in range(names)], index=codes)
    noise = 0.01 * rng.normal(size=(len(jp_days), len(codes)))
    stock_c2c = etf_c2c[:, sector.to_numpy() - 1] + noise
    start = rng.uniform(500, 2500, size=len(codes))
    stock_close = pd.DataFrame(
        start * np.cumprod(1 + stock_c2c, axis=0), index=jp_days, columns=codes
    )

    def panel(close: pd.DataFrame, codes_sector: pd.Series, zero_share: float) -> Panel:
        volume = pd.DataFrame(
            rng.uniform(1e4, 1e5, size=close.shape), index=close.index, columns=close.columns
        )
        volume = volume.mask(rng.random(close.shape) < zero_share, 0.0)
        zeros = close * 0.0
        return Panel(close.copy(), close, close.copy(), volume, zeros, zeros, codes_sector)

    listing = Listing(
        date(2026, 9, 30),
        pd.DataFrame(
            {"name": codes, "sector": sector.to_numpy(), "size": "TOPIX Mid400"},
            index=pd.Index(codes, name="code"),
        ),
    )
    etf_sector = pd.Series(list(SECTORS), index=list(SECTORS))
    study = Study(
        listing,
        us,
        us_days,
        jp_days,
        last_us_before(jp_days, us_days),
        panel(etf_close, etf_sector, 0.05),
        panel(stock_close, sector, 0.01),
        (),
    )
    sz = cross_standardize(build_signal(study, "lagged")).reindex(jp_days).to_numpy()
    in_b = (jp_days >= B[0])[:, None]

    def opened(p: Panel, lead, column_sector: np.ndarray) -> Panel:
        size = 0.002 * np.where(in_b, lead[1], lead[0])
        o2c = np.nan_to_num(size * sz[:, column_sector - 1]) + 0.004 * rng.normal(
            size=p.close.shape
        )
        return replace(p, open=p.close / (1 + o2c))

    return replace(
        study,
        etf=opened(study.etf, etf_lead, np.arange(1, 18)),
        stocks=opened(study.stocks, stock_lead, sector.to_numpy()),
    )


@pytest.fixture(scope="session")
def decayed_world():
    """The lead is real in the stocks; in the ETFs it turns negative from 本番 B on."""
    return _world()


@pytest.fixture(scope="session")
def etf_only_world():
    """The lead is in the ETFs only."""
    return _world(seed=1, stock_lead=(0.0, 0.0))
```

File: `sector_leadlag_lab/tests/test_study.py` (create)

```python
import pandas as pd
import pytest
from sector_leadlag.data import yf
from sector_leadlag.data.jpx import ETF_TICKERS
from sector_leadlag.data.store import store_bytes
from sector_leadlag.study import load_study

DATES = ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"]


def _store_prices(root, ticker, history, dates=DATES, **columns):
    frame = history(dates, open_=[100.0] * len(dates), close=[101.0] * len(dates), **columns)
    content = yf.to_csv(frame, pd.Timestamp("2026-12-31").date())
    store_bytes(root, "yf", ticker, content, url=f"yfinance:{ticker}", filename=f"{ticker}.csv")


def test_the_study_puts_every_series_on_the_japanese_days(tmp_path, listing_bytes, yf_history):
    rows = [("7203", 6, "TOPIX Core30"), ("6758", 9, "TOPIX Core30"), ("9999", 9, "TOPIX Small 1")]
    store_bytes(tmp_path, "jpx", "data_j", listing_bytes(rows), url="u", filename="data_j.xlsx")
    for ticker in yf.US_SECTORS:  # the 6th is a US holiday
        _store_prices(tmp_path, ticker, yf_history, [*DATES[:1], *DATES[2:]], tz="America/New_York")
    for ticker in ETF_TICKERS:
        _store_prices(tmp_path, ticker, yf_history)
    _store_prices(tmp_path, "7203.T", yf_history, volume=[10, 10, 0, 10])
    study = load_study(tmp_path)
    assert study.missing == ("6758",)  # 9999 is not in TOPIX500; 6758 has no prices
    assert list(study.stocks.close.columns) == ["7203"]
    assert study.stocks.sector.to_dict() == {"7203": 6}
    # the 7th: the only listed stock did not trade
    assert [str(d.date()) for d in study.jp_days] == ["2026-01-05", "2026-01-06", "2026-01-08"]
    assert list(study.etf.close.columns) == list(range(1, 18))
    assert study.s_map.to_dict() == {
        pd.Timestamp("2026-01-06"): pd.Timestamp("2026-01-05"),
        pd.Timestamp("2026-01-08"): pd.Timestamp("2026-01-07"),
    }
    assert study.us_returns().shape == (3, 11)


def test_a_store_without_stock_prices_is_refused(tmp_path, listing_bytes):
    store_bytes(
        tmp_path,
        "jpx",
        "data_j",
        listing_bytes([("7203", 6, "TOPIX Core30")]),
        url="u",
        filename="data_j.xlsx",
    )
    with pytest.raises(FileNotFoundError, match="sector-leadlag snapshot"):
        load_study(tmp_path)
```

File: `sector_leadlag_lab/tests/test_stages.py` (create)

```python
import numpy as np
import pandas as pd
from sector_leadlag.stages import (
    basket_long_short,
    build_signal,
    cut,
    fit_in,
    h1_baskets,
    h2_series,
)
from sector_leadlag.study import A, B


def test_the_signal_covers_the_japanese_days_after_the_first_window(decayed_world):
    signal = build_signal(decayed_world, "same_date")
    assert list(signal.columns) == list(range(1, 18))
    assert signal.index.isin(decayed_world.jp_days).all()
    assert signal.index[0] < A[0] and signal.index[-1] == decayed_world.jp_days[-1]


def test_baskets_and_the_cash_strategy_use_only_the_days_asked_for(decayed_world):
    baskets = h1_baskets(decayed_world)
    weights = baskets.main.loc[A[0] :]
    sums = weights.T.groupby(decayed_world.stocks.sector).sum().T
    assert np.allclose(sums.to_numpy(), 1.0)
    signal = cut(build_signal(decayed_world, "lagged"), B)
    cash, spread = h2_series(decayed_world, signal, baskets.median)
    assert cash.returns.index.equals(signal.index)
    assert spread.index.isin(signal.index).all()
    assert (cash.names <= 15).all() and (cash.invested <= 1.0).all()


def test_a_period_without_enough_days_gets_no_regression():
    days = pd.bdate_range("2026-01-05", periods=3)
    frame = pd.DataFrame(
        np.random.default_rng(0).normal(size=(3, 17)), index=days, columns=range(1, 18)
    )
    assert fit_in(frame, frame, (days[0], days[-1])) is None


def test_the_basket_long_short_is_flat_on_a_flat_signal():
    days = pd.bdate_range("2026-01-05", periods=2)
    signal = pd.DataFrame(1.0, index=days, columns=range(1, 18))
    returns = pd.DataFrame(0.01, index=days, columns=range(1, 18))
    assert basket_long_short(signal, returns).tolist() == [0.0, 0.0]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_study.py sector_leadlag_lab/tests/test_stages.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.study'` (and `'sector_leadlag.stages'`).

- [ ] **Step 3: Write the two modules**

File: `sector_leadlag_lab/src/sector_leadlag/study.py` (create)

```python
"""Every input of the study in one object (design §4), and the periods of design §3.2."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import timing
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

    def us_returns(self) -> pd.DataFrame:
        return timing.close_to_close(self.us_adj, self.us_days)

    def etf_c2c(self) -> pd.DataFrame:
        """The Japanese side of the signal: ETF adjusted close to adjusted close (design §6)."""
        return timing.close_to_close(self.etf.adj_close, self.jp_days)


def build_panel(frames: dict, days: pd.DatetimeIndex, sector: pd.Series) -> Panel:
    """One frame per field with a column per entry of ``frames``, on ``days``."""
    stacked = pd.concat(frames, axis=1)
    parts = {
        field: stacked.xs(field, axis=1, level=1).reindex(days, columns=list(frames))
        for field in FIELDS
    }
    return Panel(**parts, sector=sector)


def load_study(root: Path = RAW_ROOT) -> Study:
    listing = jpx.parse_listing(read_latest(root, "jpx", "data_j"))
    stored = set(indicators(root, "yf"))

    def prices(ticker: str) -> pd.DataFrame:
        return yf.parse_csv(read_latest(root, "yf", ticker))

    members = jpx.topix500(listing)
    have = [code for code in members.index if jpx.stock_ticker(code) in stored]
    if not have:
        raise FileNotFoundError(f"no TOPIX500 prices under {root}; run `sector-leadlag snapshot`")
    stock_frames = {code: prices(jpx.stock_ticker(code)) for code in have}
    volume = pd.concat({code: frame["volume"] for code, frame in stock_frames.items()}, axis=1)
    jp_days = timing.jp_trading_days(volume.loc[PANEL_START:])
    us_frames = {ticker: prices(ticker) for ticker in yf.US_SECTORS}
    us_days = timing.us_trading_days(us_frames["XLK"]["volume"].loc[PANEL_START:])
    us_adj = pd.concat({t: f["adj_close"] for t, f in us_frames.items()}, axis=1)
    etf_frames = {k: prices(ticker) for k, ticker in enumerate(jpx.ETF_TICKERS, start=1)}
    return Study(
        listing=listing,
        us_adj=us_adj.reindex(us_days),
        us_days=us_days,
        jp_days=jp_days,
        s_map=timing.last_us_before(jp_days, us_days),
        etf=build_panel(etf_frames, jp_days, pd.Series(list(SECTORS), index=list(SECTORS))),
        stocks=build_panel(stock_frames, jp_days, members.loc[have, "sector"].astype(int)),
        missing=tuple(code for code in members.index if code not in set(have)),
    )
```

File: `sector_leadlag_lab/src/sector_leadlag/stages.py` (create)

```python
"""Shared builders of the stages: the signal of a pairing, the baskets and the strategies.

Every stage runner takes ``(study, prior)`` and returns a JSON-ready dict; ``prior`` holds the
results of the stages it depends on (see ``cli.REQUIRES``).
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import (
    Spec,
    full_correlation,
    lead_lag_signal,
    long_short,
    prior_subspace,
    target,
)
from .strategy import CAPITAL, TOP, CashLong, cash_long, long_short_returns, selection_spread
from .study import Study
from .timing import pair_rows

SCALE = 1e-4  # coefficients are reported in units of 1e-4, as in the decay paper
MIN_DAYS = 5  # a period with fewer days gets no regression


def cut(frame, period):
    return frame.loc[period[0] : period[1]]


def build_signal(
    study: Study,
    variant: str,
    *,
    us_ret: pd.DataFrame | None = None,
    jp_c2c: pd.DataFrame | None = None,
    spec: Spec = Spec(),
) -> pd.DataFrame:
    """ẑ_J for every Japanese day with a full window, under one pairing (design §5.2, §6)."""
    us_ret = study.us_returns() if us_ret is None else us_ret
    jp_c2c = study.etf_c2c() if jp_c2c is None else jp_c2c
    rows = pair_rows(variant, us_ret, jp_c2c, study.s_map)
    c_full, _ = full_correlation(rows)
    c0 = target(c_full, prior_subspace(rows.us_names, rows.jp_names))
    return lead_lag_signal(rows, us_ret, study.s_map, c0, study.jp_days, spec)


@dataclass(frozen=True)
class Returns:
    """Per-sector returns of one price series."""

    o2c: pd.DataFrame
    c2o: pd.DataFrame
    c2c: pd.DataFrame


def etf_returns(study: Study) -> Returns:
    p = study.etf
    return Returns(bk.open_to_close(p), bk.close_to_open(p), bk.close_to_close(p))


def basket_series(study: Study, weights: pd.DataFrame) -> Returns:
    p, sector = study.stocks, study.stocks.sector
    parts = (bk.open_to_close(p), bk.close_to_open(p), bk.close_to_close(p))
    return Returns(*(bk.basket_returns(weights, r, sector) for r in parts))


@dataclass(frozen=True)
class Baskets:
    median: pd.DataFrame  # trailing median traded value of every name (design §7.1)
    main: pd.DataFrame  # H1: all names, weighted by the median
    top10: pd.DataFrame  # H1 secondary: the 10 most traded names, equal weights


def h1_baskets(study: Study) -> Baskets:
    median = bk.trailing_value(study.stocks)
    sector = study.stocks.sector
    return Baskets(
        median, bk.liquidity_weights(median, sector), bk.top_equal_weights(median, sector)
    )


def etf_long_short(signal: pd.DataFrame, study: Study, returns: pd.DataFrame) -> pd.Series:
    """The paper's long-short on the ETFs that traded that day."""
    return long_short_returns(long_short(signal, bk.traded(study.etf)), returns)


def basket_long_short(signal: pd.DataFrame, returns: pd.DataFrame) -> pd.Series:
    """The same long-short on the baskets; every sector can be chosen (design §6)."""
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    return long_short_returns(long_short(signal, available), returns)


def fit_summary(fit: ev.PanelFit) -> dict:
    return {
        "beta_1e4": fit.beta[0] / SCALE,
        "se_1e4": fit.se[0] / SCALE,
        "t": fit.t,
        "p": fit.p,
        "obs": fit.n_obs,
        "days": fit.n_days,
    }


def fit_in(returns: pd.DataFrame, sz: pd.DataFrame, period, controls=()) -> dict | None:
    """The panel regression over ``period``, or None when it has too few days."""
    y, x = cut(returns, period), cut(sz, period)
    days = y.index.intersection(x.index)
    if len(days) < MIN_DAYS:
        return None
    return fit_summary(ev.panel_fit(y, x, [cut(c, period) for c in controls]))


def h2_series(
    study: Study,
    signal: pd.DataFrame,
    median: pd.DataFrame,
    *,
    capital: float = CAPITAL,
    cost_bp: float = 0.0,
) -> tuple[CashLong, pd.Series]:
    """H2 1 (the cash-only strategy) and H2 2 (the selection spread) on the days of ``signal``."""
    p, sector = study.stocks, study.stocks.sector
    quoted_open, quoted_close = bk.quoted(p)
    budget = capital / (TOP * bk.PER_SECTOR)
    picks = bk.h2_picks(median, quoted_close, sector, budget)
    cash = cash_long(
        signal,
        picks,
        quoted_open,
        quoted_close,
        bk.traded(p),
        sector,
        capital=capital,
        cost_bp=cost_bp,
    )
    pick_returns = bk.basket_returns(picks.astype(float), bk.open_to_close(p), sector)
    return cash, selection_spread(signal, pick_returns)


def cash_summary(cash: CashLong) -> dict:
    return {
        **ev.describe(cash.returns),
        "mean_names": float(cash.names.mean()) if len(cash.names) else 0.0,
        "invested": float(cash.invested.mean()) if len(cash.invested) else 0.0,
    }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `58 passed, 1 skipped` (the worlds take about 1 s each to build).

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Assemble the study and the shared stage builders"
```

---
### Task 11: G0 — data checks and the ETF replication that picks the pairing

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/g0.py`
- Test: `sector_leadlag_lab/tests/test_g0.py`

**Interfaces:**
- Consumes: `stages.build_signal`, `stages.cut`, `stages.etf_long_short`, `stages.etf_returns`, `stages.fit_summary`, `stages.h1_baskets` (Task 10); `study.A`, `study.B1`, `study.ORIGINAL` (Task 10); `timing.VARIANTS` (Task 4); `evaluate.panel_fit`, `describe`, `monthly_metrics`, `ALPHA` (Task 8); `baskets` (Task 6).
- Produces: `sector_leadlag.g0.PUBLISHED` (the papers' values), `OUTLIER = 0.2`, `LIST_MAX = 100`, `END = B1[1]`, `replicate(study, variant) -> dict` (`original` = `monthly_metrics` over 2015–2025, `a`/`b1` = `describe`, `c2o_a`, `c2o_b1`, `fit_a`, `fit_b1` = `fit_summary`, `pass`), `choose(variants) -> str | None` (D1), `zero_volume(panel, period)`, `outliers(frames)`, `split_events(panel, period)`, `dividend_events(panel, period)`, `coverage(study, weights, period)`, `data_checks(study)`, `run_g0(study, prior) -> {"published", "variants", "selected", "pass", "verdict", "checks"}`. Later stages read `g0["selected"]`, `g0["pass"]` and `g0["variants"][selected]["fit_a"]["beta_1e4"]`.

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_g0.py` (create)

```python
import json

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.g0 import (
    PUBLISHED,
    choose,
    dividend_events,
    run_g0,
    split_events,
    zero_volume,
)


def _row(ar: float, passed: bool) -> dict:
    return {"original": {"ar": ar}, "pass": passed}


def test_the_passing_pairing_closest_to_the_papers_ar_is_chosen():
    assert choose({"same_date": _row(0.10, True), "lagged": _row(0.30, True)}) == "lagged"
    assert choose({"same_date": _row(0.20, True), "lagged": _row(0.24, False)}) == "same_date"
    assert choose({"same_date": _row(0.20, False), "lagged": _row(0.24, False)}) is None
    tie = PUBLISHED["ar"]
    assert choose({"same_date": _row(tie - 0.01, True), "lagged": _row(tie + 0.01, True)}) == (
        "same_date"
    )


DAYS = pd.bdate_range("2026-01-05", periods=4)


def test_zero_volume_days_and_stale_closes_are_counted(make_panel):
    close = pd.DataFrame({1: [100.0, 100.0, 101.0, 101.0]}, index=DAYS)
    volume = pd.DataFrame({1: [5.0, 0.0, 0.0, 5.0]}, index=DAYS)
    out = zero_volume(make_panel(close, close, volume=volume), (DAYS[0], DAYS[-1]))
    assert out["1"] == {"days": 4, "zero": 2, "share": 0.5, "stale": 0.5}


def test_an_unadjusted_split_is_flagged(make_panel):
    close = pd.DataFrame({"a": [500.0, 505.0, 101.0, 102.0], "b": [100.0] * 4}, index=DAYS)
    splits = pd.DataFrame({"a": [0.0, 0.0, 5.0, 0.0], "b": [0.0, 5.0, 0.0, 0.0]}, index=DAYS)
    out = split_events(make_panel(close, close, splits=splits), (DAYS[0], DAYS[-1]))
    assert out["events"] == 2 and out["flagged_count"] == 1
    assert out["flagged"][0]["name"] == "a" and out["flagged"][0]["c2o"] == pytest.approx(-0.8)


def test_dividends_bring_the_ex_date_gap_back_towards_zero(make_panel):
    close = pd.DataFrame({"a": [100.0, 98.0, 98.0, 98.0]}, index=DAYS)
    open_ = pd.DataFrame({"a": [100.0, 97.5, 98.0, 98.0]}, index=DAYS)
    dividends = pd.DataFrame({"a": [0.0, 2.5, 0.0, 0.0]}, index=DAYS)
    out = dividend_events(make_panel(open_, close, dividends=dividends), (DAYS[0], DAYS[-1]))
    assert out["events"] == 1
    assert out["mean_abs_c2o_with"] == pytest.approx(0.0)
    assert out["mean_abs_c2o_without"] == pytest.approx(0.025)


def test_g0_reproduces_the_decay_and_picks_a_pairing(decayed_world):
    out = run_g0(decayed_world, {})
    assert out["pass"] and out["selected"] in ("same_date", "lagged")
    chosen = out["variants"][out["selected"]]
    assert chosen["fit_a"]["p"] < 0.05 and chosen["b1"]["mean_ann"] < 0
    assert out["checks"]["names"]["with_prices"] == 34
    assert set(out["checks"]["etf_zero_volume"]) == {str(k) for k in range(1, 18)}
    assert len(out["checks"]["coverage"]["1"]) == 12  # 2015 to 2026
    assert np.isfinite(chosen["original"]["ar"])


def test_g0_reads_no_etf_value_after_b1(decayed_world):
    from dataclasses import replace

    from sector_leadlag.study import B2

    def scramble(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        out.loc[B2[0] :] = 1.0
        return out

    etf = decayed_world.etf
    fields = ("open", "close", "adj_close", "volume")
    late = replace(etf, **{name: scramble(getattr(etf, name)) for name in fields})
    scrambled = replace(decayed_world, etf=late)
    same = [json.dumps(run_g0(world, {}), default=str) for world in (scrambled, decayed_world)]
    assert same[0] == same[1]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_g0.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.g0'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/g0.py` (create)

```python
"""G0: data checks, and the ETF-only replication that picks the pairing (design §8).

Nothing here reads an ETF value after B1 (2026-07-23), and nothing relates the signal to stock
returns: stock prices enter only the data checks.
"""

from __future__ import annotations

import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import cross_standardize
from .stages import (
    build_signal,
    cut,
    etf_long_short,
    etf_returns,
    fit_summary,
    h1_baskets,
)
from .study import B1, ORIGINAL, A, Study
from .timing import VARIANTS

PUBLISHED = {
    "ar": 0.2379,  # strategy paper, PCA SUB, monthly x 12
    "risk": 0.1070,
    "rr": 2.22,
    "mdd": 0.0958,
    "mean_a": 0.3018,  # decay paper, ETF open to close, daily x 252
    "mean_b1": -1.0707,
    "cumulative_b1": -0.3079,
    "c2o_a": 0.3515,
    "c2o_b1": 1.1682,
    "beta_a_1e4": 4.75,
    "beta_b1_1e4": -18.31,
    "days_a": 2737,
    "days_b1": 85,
}
OUTLIER = 0.2  # |O2C| or |C2O| above this is listed (never removed)
LIST_MAX = 100
END = B1[1]


def replicate(study: Study, variant: str) -> dict:
    """The paper's ETF long-short and the ETF panel regression under one pairing."""
    signal = build_signal(study, variant).loc[:END]
    sz = cross_standardize(signal)
    etf = etf_returns(study)
    o2c = etf_long_short(signal, study, etf.o2c)
    c2o = etf_long_short(signal, study, etf.c2o)
    fit_a = ev.panel_fit(cut(etf.o2c, A), cut(sz, A))
    b1 = ev.describe(cut(o2c, B1))
    return {
        "original": ev.monthly_metrics(cut(o2c, ORIGINAL)),
        "a": ev.describe(cut(o2c, A)),
        "b1": b1,
        "c2o_a": ev.describe(cut(c2o, A))["mean_ann"],
        "c2o_b1": ev.describe(cut(c2o, B1))["mean_ann"],
        "fit_a": fit_summary(fit_a),
        "fit_b1": fit_summary(ev.panel_fit(cut(etf.o2c, B1), cut(sz, B1))),
        "pass": bool(fit_a.p < ev.ALPHA and b1["mean_ann"] < 0),
    }


def choose(variants: dict[str, dict]) -> str | None:
    """Of the pairings that pass, the one whose 2015-2025 AR is closest to the paper's 23.79%."""
    passing = [name for name in VARIANTS if variants[name]["pass"]]
    if not passing:
        return None
    return min(passing, key=lambda name: abs(variants[name]["original"]["ar"] - PUBLISHED["ar"]))


def zero_volume(panel: bk.Panel, period) -> dict:
    """Per ETF: days with a price, days without trades, and how often such a day kept the
    previous close."""
    zero = (panel.volume.fillna(0.0) == 0) & panel.close.notna()
    same = panel.close.eq(panel.close.shift(1))
    zero, same, close = cut(zero, period), cut(same, period), cut(panel.close, period)
    out = {}
    for column in panel.close.columns:
        priced, flat = int(close[column].notna().sum()), int(zero[column].sum())
        out[str(column)] = {
            "days": priced,
            "zero": flat,
            "share": flat / priced if priced else 0.0,
            "stale": float(same[column][zero[column]].mean()) if flat else 0.0,
        }
    return out


def outliers(frames: dict[str, pd.DataFrame]) -> dict:
    rows = []
    for kind, frame in frames.items():
        stacked = frame.stack()
        for (day, name), value in stacked[stacked.abs() > OUTLIER].items():
            rows.append({"kind": kind, "date": str(day.date()), "name": str(name), "value": value})
    rows.sort(key=lambda row: -abs(row["value"]))
    return {"count": len(rows), "largest": rows[:LIST_MAX]}


def split_events(panel: bk.Panel, period) -> dict:
    """Every split: the adjusted close-to-open of its ex-date should look like any other day."""
    c2o = cut(bk.close_to_open(panel), period)
    events = cut(panel.splits, period).where(lambda s: s > 0).stack().dropna()
    rows = [
        {"name": str(name), "date": str(day.date()), "ratio": ratio, "c2o": c2o.at[day, name]}
        for (day, name), ratio in events.items()
    ]
    flagged = [row for row in rows if not abs(row["c2o"]) <= OUTLIER]  # a NaN is flagged too
    return {"events": len(rows), "flagged_count": len(flagged), "flagged": flagged[:LIST_MAX]}


def dividend_events(panel: bk.Panel, period) -> dict:
    """Ex-dates: adding the dividend back should bring the overnight return closer to 0."""
    with_dividend = cut(bk.close_to_open(panel), period)
    without = cut((panel.open / panel.close.shift(1) - 1.0).where(bk.traded(panel)), period)
    ex = cut(panel.dividends, period) > 0

    def mean_abs(frame: pd.DataFrame) -> float | None:
        values = frame[ex].stack().dropna()
        return float(values.abs().mean()) if len(values) else None

    return {
        "events": int(ex.to_numpy().sum()),
        "mean_abs_c2o_with": mean_abs(with_dividend),
        "mean_abs_c2o_without": mean_abs(without),
    }


def coverage(study: Study, weights: pd.DataFrame, period) -> dict:
    """Correlation of the ETF and the H1 basket close-to-close returns, by sector and year."""
    etf = cut(bk.close_to_close(study.etf), period)
    basket = cut(
        bk.basket_returns(weights, bk.close_to_close(study.stocks), study.stocks.sector), period
    )
    out = {}
    for sector in bk.SECTORS:
        both = pd.concat([etf[sector], basket[sector]], axis=1).dropna()
        by_year = both.groupby(both.index.year)
        out[str(sector)] = {
            str(year): float(f.iloc[:, 0].corr(f.iloc[:, 1])) for year, f in by_year if len(f) > 2
        }
    return out


def data_checks(study: Study) -> dict:
    period = (A[0], END)
    baskets = h1_baskets(study)
    first = cut(baskets.median, period).iloc[0]
    counts = (first > 0).groupby(study.stocks.sector).sum()
    return {
        "names": {
            "topix500": len(study.stocks.sector) + len(study.missing),
            "with_prices": len(study.stocks.sector),
            "missing": list(study.missing),
            "per_sector_on_first_a_day": {str(k): int(v) for k, v in counts.items()},
        },
        "etf_zero_volume": zero_volume(study.etf, period),
        "outliers": outliers(
            {
                "etf_o2c": cut(bk.open_to_close(study.etf), period),
                "etf_c2o": cut(bk.close_to_open(study.etf), period),
                "stock_o2c": cut(bk.open_to_close(study.stocks), period),
                "stock_c2o": cut(bk.close_to_open(study.stocks), period),
            }
        ),
        "splits": split_events(study.stocks, period),
        "dividends": dividend_events(study.stocks, period),
        "coverage": coverage(study, baskets.main, period),
    }


def run_g0(study: Study, prior: dict) -> dict:
    variants = {name: replicate(study, name) for name in VARIANTS}
    selected = choose(variants)
    return {
        "published": PUBLISHED,
        "variants": variants,
        "selected": selected,
        "pass": selected is not None,
        "verdict": None if selected else "replication_failed",
        "checks": data_checks(study),
    }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `64 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add G0: data checks and the ETF replication that picks the pairing"
```

---

### Task 12: G1 — rotated US returns and the power of H1

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/g1.py`
- Test: `sector_leadlag_lab/tests/test_g1.py`

**Interfaces:**
- Consumes: `prior["g0"]["selected"]` and `prior["g0"]["variants"][selected]["fit_a"]["beta_1e4"]` (Task 11); `stages.SCALE`, `basket_series`, `build_signal`, `cut`, `h1_baskets` (Task 10); `synthetic.SHIFTS`, `circular_shift`, `plant`, `shift_amounts` (Task 9); `evaluate.panel_fit`, `ALPHA` (Task 8).
- Produces: `sector_leadlag.g1.MAX_SIGNIFICANT = 2`, `POWER_SHARE = 0.5`, `run_g1(study, prior, *, count=SHIFTS) -> {"variant", "count", "significant", "detected", "planted_beta_1e4", "pass", "worlds"}`.

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_g1.py` (create)

```python
from sector_leadlag.g1 import run_g1


def test_rotated_worlds_lose_the_lead_and_a_planted_one_is_found(decayed_world):
    prior = {"g0": {"selected": "lagged", "variants": {"lagged": {"fit_a": {"beta_1e4": 20.0}}}}}
    out = run_g1(decayed_world, prior, count=3)
    assert out["count"] == 3 and len(out["worlds"]) == 3
    assert out["significant"] <= 1 and out["pass"]
    assert out["detected"] == 3 and out["planted_beta_1e4"] == 10.0
    assert all(world["shift"] >= 60 for world in out["worlds"])
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_g1.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.g1'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/g1.py` (create)

```python
"""G1: the US returns rotated against Japan, so that no lead-lag is left, and the power of H1.

Each world rotates the US returns by a fixed random number of US trading days (at least 60) and
rebuilds the whole signal, C_full included, from the rotated returns (design §8). The power
check adds 0.5 x beta_ETF x sz of the rotated signal to the basket returns and counts how often
the H1 test finds it.
"""

from __future__ import annotations

from . import evaluate as ev
from .signal import cross_standardize
from .stages import SCALE, basket_series, build_signal, cut, h1_baskets
from .study import A, Study
from .synthetic import SHIFTS, circular_shift, plant, shift_amounts

MAX_SIGNIFICANT = 2
POWER_SHARE = 0.5


def run_g1(study: Study, prior: dict, *, count: int = SHIFTS) -> dict:
    variant = prior["g0"]["selected"]
    beta = POWER_SHARE * prior["g0"]["variants"][variant]["fit_a"]["beta_1e4"] * SCALE
    us_ret = study.us_returns()
    o2c = cut(basket_series(study, h1_baskets(study).main).o2c, A)
    worlds = []
    for k in shift_amounts(len(us_ret), count):
        signal = build_signal(study, variant, us_ret=circular_shift(us_ret, k))
        sz = cut(cross_standardize(signal), A)
        null = ev.panel_fit(o2c, sz)
        planted = ev.panel_fit(plant(o2c, sz, beta), sz)
        worlds.append(
            {
                "shift": k,
                "beta_1e4": null.beta[0] / SCALE,
                "p": null.p,
                "planted_beta_1e4": planted.beta[0] / SCALE,
                "planted_p": planted.p,
            }
        )
    significant = sum(world["p"] < ev.ALPHA for world in worlds)
    return {
        "variant": variant,
        "count": count,
        "significant": significant,
        "detected": sum(world["planted_p"] < ev.ALPHA for world in worlds),
        "planted_beta_1e4": beta / SCALE,
        "pass": significant <= MAX_SIGNIFICANT,
        "worlds": worlds,
    }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `65 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add G1: rotated US returns and the power of H1"
```

---

### Task 13: Main A and main B with the verdict

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/main.py`
- Test: `sector_leadlag_lab/tests/test_main.py`

**Interfaces:**
- Consumes: `prior["g0"]["selected"]`, `prior["g0"]["pass"]` (Task 11); `stages.basket_series`, `build_signal`, `cash_summary`, `cut`, `etf_long_short`, `etf_returns`, `fit_summary`, `h1_baskets`, `h2_series` (Task 10); `strategy.CAPITAL` (Task 7); `evaluate` (Task 8); `study.A`, `B`, `B1`, `B2` (Task 10).
- Produces: `sector_leadlag.main.SCENARIOS` (`base`, `cost_2bp`, `capital_3m`, `capital_10m`, `cost_5bp` → (capital, cost_bp)), `ROBUSTNESS = ("cost_2bp", "capital_3m", "capital_10m")`, `run_main_a(study, prior, *, n_boot=N_BOOT) -> {"variant", "h1": {"basket", "etf", "ratio_ci", "pass"}, "h2": {scenario: {"capital", "cost_bp", "cash": {…, "p"}, "spread": {…, "p"}}}, "h2_pass", "robust"}` (period A only), `run_main_b(study, prior) -> {"variant", "h1": {"basket", "etf"}, "h2": {"cash", "spread"}, "etf_long_short": {"b1", "b2"}, "h3", "evidence", "verdict"}` (reads `prior["main_a"]`).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_main.py` (create)

```python
import pytest
from sector_leadlag.main import ROBUSTNESS, SCENARIOS, run_main_a, run_main_b

G0 = {"selected": "lagged", "pass": True}


def _verdict(world) -> tuple[dict, dict]:
    a = run_main_a(world, {"g0": G0}, n_boot=300)
    b = run_main_b(world, {"g0": G0, "main_a": a})
    return a, b


@pytest.fixture(scope="module")
def decayed(decayed_world):
    return _verdict(decayed_world)


def test_a_real_lead_in_the_stocks_is_usable(decayed):
    a, b = decayed
    assert a["h1"]["pass"] and a["h2_pass"] and a["robust"]
    assert set(a["h2"]) == set(SCENARIOS) and set(ROBUSTNESS) < set(a["h2"])
    low, high = a["h1"]["ratio_ci"]
    assert low < a["h1"]["basket"]["beta_1e4"] / a["h1"]["etf"]["beta_1e4"] < high
    assert b["verdict"] == "usable"
    assert b["h1"]["etf"]["beta_1e4"] < 0 < b["h1"]["basket"]["beta_1e4"]
    assert b["h3"]["label"] == "decay_continued"


def test_costs_lower_the_cash_strategy_but_not_the_spread(decayed):
    a, _ = decayed
    base, costly = a["h2"]["base"], a["h2"]["cost_5bp"]
    assert costly["cash"]["mean_ann"] < base["cash"]["mean_ann"]
    assert costly["spread"]["mean_ann"] == base["spread"]["mean_ann"]


def test_a_lead_in_the_etfs_only_is_etf_only(etf_only_world):
    _, b = _verdict(etf_only_world)
    assert b["verdict"] == "etf_only"
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_main.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.main'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/main.py` (create)

```python
"""本番 A and 本番 B: H1, H2, H3 and the verdict (design §3).

``run_main_a`` reads period A only. ``run_main_b`` runs once, after main A is recorded, and
gives the verdict from the two (design §3.5).
"""

from __future__ import annotations

from dataclasses import asdict

from . import evaluate as ev
from .signal import cross_standardize
from .stages import (
    basket_series,
    build_signal,
    cash_summary,
    cut,
    etf_long_short,
    etf_returns,
    fit_summary,
    h1_baskets,
    h2_series,
)
from .strategy import CAPITAL
from .study import B1, B2, A, B, Study

SCENARIOS = {
    "base": (CAPITAL, 0.0),
    "cost_2bp": (CAPITAL, 2.0),
    "capital_3m": (3_000_000.0, 0.0),
    "capital_10m": (10_000_000.0, 0.0),
    "cost_5bp": (CAPITAL, 5.0),  # reported only (design §3.4)
}
ROBUSTNESS = ("cost_2bp", "capital_3m", "capital_10m")


def _sign(x: float) -> int:
    return (x > 0) - (x < 0)


def run_main_a(study: Study, prior: dict, *, n_boot: int = ev.N_BOOT) -> dict:
    variant = prior["g0"]["selected"]
    signal = cut(build_signal(study, variant), A)
    sz = cross_standardize(signal)
    baskets = h1_baskets(study)
    basket = cut(basket_series(study, baskets.main).o2c, A)
    fit_b = ev.panel_fit(basket, sz)
    fit_e = ev.panel_fit(cut(etf_returns(study).o2c, A), sz)
    low, high = ev.ratio_interval(fit_b, fit_e, n_boot=n_boot)
    h2 = {}
    for name, (capital, cost_bp) in SCENARIOS.items():
        cash, spread = h2_series(study, signal, baskets.median, capital=capital, cost_bp=cost_bp)
        h2[name] = {
            "capital": capital,
            "cost_bp": cost_bp,
            "cash": {**cash_summary(cash), "p": ev.mean_test(cash.returns, n_boot=n_boot).p},
            "spread": {**ev.describe(spread), "p": ev.mean_test(spread, n_boot=n_boot).p},
        }
    base = h2["base"]
    robust = all(
        _sign(h2[name][part]["mean_ann"]) == _sign(base[part]["mean_ann"])
        for name in ROBUSTNESS
        for part in ("cash", "spread")
    )
    return {
        "variant": variant,
        "h1": {
            "basket": fit_summary(fit_b),
            "etf": fit_summary(fit_e),
            "ratio_ci": [low, high],
            "pass": fit_b.p < ev.ALPHA,
        },
        "h2": h2,
        "h2_pass": base["cash"]["p"] < ev.ALPHA and base["spread"]["p"] < ev.ALPHA,
        "robust": robust,
    }


def run_main_b(study: Study, prior: dict) -> dict:
    variant = prior["g0"]["selected"]
    signal = build_signal(study, variant)
    sz = cut(cross_standardize(signal), B)
    baskets = h1_baskets(study)
    etf = etf_returns(study)
    fit_b = ev.panel_fit(cut(basket_series(study, baskets.main).o2c, B), sz)
    fit_e = ev.panel_fit(cut(etf.o2c, B), sz)
    cash, spread = h2_series(study, cut(signal, B), baskets.median)
    ls = etf_long_short(cut(signal, (A[0], B[1])), study, etf.o2c)
    a = prior["main_a"]
    evidence = ev.Evidence(
        replicated=bool(prior["g0"]["pass"]),
        h1_p=a["h1"]["basket"]["p"],
        beta_b_period_b=fit_b.beta[0],
        h2_p_cash=a["h2"]["base"]["cash"]["p"],
        h2_p_spread=a["h2"]["base"]["spread"]["p"],
        robust=bool(a["robust"]),
        b_mean_cash=float(cash.returns.mean()),
        b_mean_spread=float(spread.mean()),
    )
    return {
        "variant": variant,
        "h1": {"basket": fit_summary(fit_b), "etf": fit_summary(fit_e)},
        "h2": {"cash": cash_summary(cash), "spread": ev.describe(spread)},
        "etf_long_short": {"b1": ev.describe(cut(ls, B1)), "b2": ev.describe(cut(ls, B2))},
        "h3": ev.h3_label(cut(ls, B2), cut(ls, A)),
        "evidence": asdict(evidence),
        "verdict": ev.verdict(evidence),
    }
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `68 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add main A and main B with the verdict"
```

---

### Task 14: The post-verdict diagnostics

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/diagnostics.py`
- Test: `sector_leadlag_lab/tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `prior["g0"]["selected"]` (Task 11); `stages` builders and `fit_in` (Task 10); `synthetic.stale_returns` (Task 9); `signal.Spec`, `cross_standardize` (Task 5); `baskets` (Task 6); `evaluate` (Task 8); `study` periods (Task 10).
- Produces: `sector_leadlag.diagnostics.STALE`, `PLACEBO_DAYS = 85`, `PLACEBO_MIN_PRE = 250`, `PERIODS`, `BASELINES` (`pca_lambda0`, `momentum`, `k1`), `placebo(daily, h=85, min_pre=250) -> {"actual_ann", "pseudo_min_ann", "share_at_or_below", "pseudo_dates", "post_days"}` (D16), `stale_opens(study, sz, weights)`, `decomposition(signal, study, etf, basket)`, `run_diagnostics(study, prior) -> {"variant", "stale_opens", "placebo", "decomposition", "c2o_control", "session_change", "other_signals", "top10_basket", "reference_c"}` (spec §9; `other_signals` also holds `variant_b`).

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_diagnostics.py` (create)

```python
import numpy as np
import pandas as pd
import pytest
from sector_leadlag.diagnostics import placebo, run_diagnostics
from sector_leadlag.study import B1, A


def test_placebo_compares_the_real_change_with_pseudo_dates():
    days_a = pd.bdate_range(A[0], A[1])
    days_b = pd.bdate_range(B1[0], B1[1])
    a = pd.Series(np.tile([0.002, 0.0], len(days_a) // 2 + 1)[: len(days_a)], index=days_a)
    b = pd.Series(-0.01, index=days_b)
    out = placebo(pd.concat([a, b]), h=20, min_pre=100)
    assert out["post_days"] == 20
    assert out["actual_ann"] == pytest.approx(252 * (-0.01 - a.mean()))
    assert out["share_at_or_below"] == 0.0 and out["pseudo_min_ann"] > out["actual_ann"]
    assert out["pseudo_dates"] == len(days_a) - 20 - 100 + 1


def test_the_diagnostics_cover_design_section_9(decayed_world):
    out = run_diagnostics(decayed_world, {"g0": {"selected": "lagged"}})
    assert set(out["stale_opens"]) == {"o2c", "random_10", "random_20", "largest_gap_10"}
    assert set(out["other_signals"]) == {"pca_lambda0", "momentum", "k1", "variant_b"}
    assert (
        out["decomposition"]["etf"]["o2c"]["b1"] < 0 < out["decomposition"]["basket"]["o2c"]["b1"]
    )
    assert out["placebo"]["etf"]["share_at_or_below"] < 0.05
    assert out["reference_c"]["days"] > 0
    assert out["session_change"]["basket"]["after"]["p"] < 0.05
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_diagnostics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.diagnostics'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/diagnostics.py` (create)

```python
"""Diagnostics after the verdict (design §9). None of them changes it."""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import baskets as bk
from . import evaluate as ev
from .signal import Spec, cross_standardize
from .stages import (
    Returns,
    basket_long_short,
    basket_series,
    build_signal,
    cash_summary,
    cut,
    etf_long_short,
    etf_returns,
    fit_in,
    h1_baskets,
    h2_series,
)
from .study import B1, B2, LONGER_SESSION, ORIGINAL, A, B, C, Study
from .synthetic import stale_returns

STALE = (("random", 0.1), ("random", 0.2), ("largest_gap", 0.1))
PLACEBO_DAYS = 85  # h, the decay paper's post-publication sample
PLACEBO_MIN_PRE = 250
PERIODS = {"a": A, "b1": B1, "b2": B2}
BASELINES = {"pca_lambda0": Spec(lam=0.0), "momentum": Spec(kind="momentum"), "k1": Spec(k=1)}


def placebo(daily: pd.Series, h: int = PLACEBO_DAYS, min_pre: int = PLACEBO_MIN_PRE) -> dict:
    """The decay paper's §4.2 in mean form: the change from A to the first h days of B1, against
    the same change at every pseudo publication date inside A."""
    a = cut(daily, A).dropna().to_numpy()
    post = cut(daily, B1).dropna().to_numpy()[:h]
    actual = float(post.mean() - a.mean())
    total = np.r_[0.0, np.cumsum(a)]
    starts = np.arange(min_pre, len(a) - h + 1)
    pseudo = (total[starts + h] - total[starts]) / h - total[starts] / starts
    return {
        "actual_ann": ev.YEAR * actual,
        "pseudo_min_ann": ev.YEAR * float(pseudo.min()),
        "share_at_or_below": float((pseudo <= actual).mean()),
        "pseudo_dates": len(pseudo),
        "post_days": len(post),
    }


def stale_opens(study: Study, sz: pd.DataFrame, weights: pd.DataFrame) -> dict:
    """H1 on baskets whose opening values are partly the previous close (design §2.3, §9)."""
    p, sector = study.stocks, study.stocks.sector
    o2c, c2o, price_c2c = bk.open_to_close(p), bk.close_to_open(p), bk.price_close_to_close(p)
    out = {}
    for mode, fraction in STALE:
        stale = stale_returns(o2c, price_c2c, c2o, fraction, mode=mode)
        out[f"{mode}_{round(100 * fraction)}"] = fit_in(
            bk.basket_returns(weights, stale, sector), sz, A
        )
    return out


def decomposition(signal: pd.DataFrame, study: Study, etf: Returns, basket: Returns) -> dict:
    """Annualised long-short means on each leg of the day (the decay paper's table 4)."""
    out: dict[str, dict] = {"etf": {}, "basket": {}}
    for leg in ("c2o", "o2c", "c2c"):
        series = {
            "etf": etf_long_short(signal, study, getattr(etf, leg)),
            "basket": basket_long_short(signal, getattr(basket, leg)),
        }
        for name, daily in series.items():
            out[name][leg] = {
                key: ev.describe(cut(daily, period))["mean_ann"] for key, period in PERIODS.items()
            }
    return out


def run_diagnostics(study: Study, prior: dict) -> dict:
    variant = prior["g0"]["selected"]
    signal = build_signal(study, variant)
    sz = cross_standardize(signal)
    baskets = h1_baskets(study)
    etf, basket = etf_returns(study), basket_series(study, baskets.main)
    top10 = basket_series(study, baskets.top10)
    out: dict = {"variant": variant}
    out["stale_opens"] = {"o2c": fit_in(basket.o2c, sz, A), **stale_opens(study, sz, baskets.main)}
    out["placebo"] = {
        "etf": placebo(etf_long_short(signal, study, etf.o2c)),
        "basket": placebo(basket_long_short(signal, basket.o2c)),
    }
    out["decomposition"] = decomposition(signal, study, etf, basket)
    out["c2o_control"] = {
        "etf": fit_in(etf.o2c, sz, A, [etf.c2o]),
        "basket": fit_in(basket.o2c, sz, A, [basket.c2o]),
    }
    before = (A[0], LONGER_SESSION - pd.Timedelta(days=1))
    after = (LONGER_SESSION, A[1])
    out["session_change"] = {
        name: {"before": fit_in(r.o2c, sz, before), "after": fit_in(r.o2c, sz, after)}
        for name, r in (("etf", etf), ("basket", basket))
    }
    others = {name: build_signal(study, variant, spec=spec) for name, spec in BASELINES.items()}
    others["variant_b"] = build_signal(study, variant, jp_c2c=basket.c2c)
    out["other_signals"] = {
        name: {
            "basket": fit_in(basket.o2c, cross_standardize(other), A),
            "etf": fit_in(etf.o2c, cross_standardize(other), A),
            "etf_original": ev.monthly_metrics(
                cut(etf_long_short(other, study, etf.o2c), ORIGINAL)
            ),
        }
        for name, other in others.items()
    }
    out["top10_basket"] = {"a": fit_in(top10.o2c, sz, A), "b": fit_in(top10.o2c, sz, B)}
    cash, spread = h2_series(study, cut(signal, C), baskets.median)
    out["reference_c"] = {
        "days": len(cut(signal, C)),
        "basket": fit_in(basket.o2c, sz, C),
        "etf": fit_in(etf.o2c, sz, C),
        "etf_long_short": ev.describe(cut(etf_long_short(signal, study, etf.o2c), C)),
        "cash": cash_summary(cash),
        "spread": ev.describe(spread),
    }
    return out
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `70 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add the post-verdict diagnostics"
```

---

### Task 15: The CLI, the stage order and the main-B lock

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/cli.py`
- Test: `sector_leadlag_lab/tests/test_cli.py`

**Interfaces:**
- Consumes: `store.RAW_ROOT`, `store.manifest_records` (Task 1); `snapshot.snapshot_all` (Task 3); `study.load_study` (Task 10); the runners `g0.run_g0`, `g1.run_g1`, `main.run_main_a`, `main.run_main_b`, `diagnostics.run_diagnostics` (Tasks 11–14), each called as `runner(study, prior)`; `report.render` (Task 16, imported only by the `report` command).
- Produces: `sector_leadlag.cli.LAB`, `RESULTS`, `RUNNERS`, `REQUIRES`, `StageError(click.ClickException)`, `inputs_digest(root) -> (str, int)`, `meta() -> {"ran_at", "git_commit", "dirty", "prereg_commit", "prereg_committed_at", "main_a_commit", "inputs_digest", "inputs_count"}`, `read_result(name, results=RESULTS) -> dict`, `write_result(name, result, results, run_meta) -> Path`, `check_ready(stage, results, run_meta) -> dict[str, dict]`, `main_b_target(results, rerun_reason) -> (name, extra)`, `take_lock(results, commit)`, and the click group `main` with `snapshot`, `run STAGE [--rerun-reason TEXT]`, `inputs`, `report`. Stage names: `g0`, `g1`, `main-a`, `main-b`, `diagnostics`; result files `results/<stage with _>.json`.

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_cli.py` (create)

```python
import json
import subprocess

import numpy as np
import pandas as pd
import pytest
from sector_leadlag import cli
from sector_leadlag.data.store import store_bytes

META = {
    "prereg_commit": "abc",
    "prereg_committed_at": "2026-10-20T10:00:00+09:00",
    "main_a_commit": "def",
}


def write(results, name: str, payload: dict) -> None:
    (results / f"{name}.json").write_text(json.dumps(payload))


def test_every_stage_needs_a_committed_prereg(tmp_path):
    with pytest.raises(cli.StageError, match="PREREG"):
        cli.check_ready("g0", tmp_path, {**META, "prereg_commit": ""})
    assert cli.check_ready("g0", tmp_path, META) == {}


def test_a_failed_replication_stops_every_later_stage(tmp_path):
    with pytest.raises(cli.StageError, match=r"g0\.json"):
        cli.check_ready("g1", tmp_path, META)
    write(tmp_path, "g0", {"pass": False})
    with pytest.raises(cli.StageError, match="replication_failed"):
        cli.check_ready("g1", tmp_path, META)


def test_main_a_needs_a_passed_g1_and_a_prereg_commit_after_it(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "g1", {"pass": False, "meta": {"ran_at": "2026-10-20T00:00:00+00:00"}})
    with pytest.raises(cli.StageError, match="G1 did not pass"):
        cli.check_ready("main-a", tmp_path, META)
    write(tmp_path, "g1", {"pass": True, "meta": {"ran_at": "2026-10-20T02:00:00+00:00"}})
    with pytest.raises(cli.StageError, match="commit it before main A"):
        cli.check_ready("main-a", tmp_path, META)  # PREREG 01:00 UTC, G1 02:00 UTC
    write(tmp_path, "g1", {"pass": True, "meta": {"ran_at": "2026-10-20T00:30:00+00:00"}})
    assert set(cli.check_ready("main-a", tmp_path, META)) == {"g0", "g1"}


def test_main_b_needs_main_a_committed(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "main_a", {"robust": True})
    with pytest.raises(cli.StageError, match=r"commit results/main_a\.json"):
        cli.check_ready("main-b", tmp_path, {**META, "main_a_commit": ""})
    assert set(cli.check_ready("main-b", tmp_path, META)) == {"g0", "main_a"}


def test_main_b_runs_once_without_a_reason(tmp_path):
    assert cli.main_b_target(tmp_path, None) == ("main_b", {})
    cli.take_lock(tmp_path, "abc123")
    with pytest.raises(cli.StageError, match="already ran"):
        cli.main_b_target(tmp_path, None)
    write(tmp_path, "main_b", {"verdict": "etf_only"})
    name, extra = cli.main_b_target(tmp_path, "fixed a data error")
    assert name == "main_b_rerun_1"
    assert extra == {"rerun_reason": "fixed a data error", "verdict_of_record": "etf_only"}


def test_diagnostics_wait_for_the_verdict(tmp_path):
    write(tmp_path, "g0", {"pass": True})
    write(tmp_path, "main_a", {})
    with pytest.raises(cli.StageError, match=r"main_b\.json"):
        cli.check_ready("diagnostics", tmp_path, META)


def test_results_serialise_numpy_values_and_dates(tmp_path):
    result = {
        "a": np.float64(1.5),
        "b": pd.Timestamp("2026-03-18"),
        "c": (1, 2),
        "d": np.bool_(True),
        "e": np.int64(3),
    }
    path = cli.write_result("x", result, tmp_path, {"git_commit": "abc"})
    assert json.loads(path.read_text()) == {
        "meta": {"git_commit": "abc"},
        "a": 1.5,
        "b": "2026-03-18",
        "c": [1, 2],
        "d": True,
        "e": 3,
    }


def test_meta_ignores_result_files_and_dates_the_prereg(tmp_path, monkeypatch):
    lab = tmp_path / "lab"
    (lab / "results").mkdir(parents=True)
    git = ["git", "-C", str(lab), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q", str(lab)], check=True)
    (lab / "PREREG.md").write_text("x\n")
    subprocess.run([*git, "add", "PREREG.md"], check=True)
    subprocess.run([*git, "-c", "commit.gpgsign=false", "commit", "-qm", "init"], check=True)
    monkeypatch.setattr(cli, "LAB", lab)
    monkeypatch.setattr(cli, "RAW_ROOT", tmp_path / "raw")
    (lab / "results" / "g0.json").write_text("{}")
    first = cli.meta()
    assert first["dirty"] is False and first["prereg_commit"] and first["inputs_count"] == 0
    assert first["prereg_committed_at"][:4].isdigit()
    (lab / "PREREG.md").write_text("y\n")
    assert cli.meta()["dirty"] is True


def test_the_inputs_digest_follows_the_newest_payloads(tmp_path):
    store_bytes(tmp_path, "yf", "XLK", b"old", url="u", filename="XLK.csv")
    first = cli.inputs_digest(tmp_path)
    store_bytes(tmp_path, "yf", "XLK", b"new", url="u", filename="XLK.csv")
    second = cli.inputs_digest(tmp_path)
    assert first[1] == second[1] == 1 and first[0] != second[0]
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.cli'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/cli.py` (create)

```python
"""Command line: ``sector-leadlag snapshot``, ``run STAGE``, ``inputs`` and ``report``.

The stage order of design §3.5 is enforced here. Every stage needs a committed PREREG.md; main A
also needs passed G0 and G1 and a PREREG commit made after G1 ran (the chosen pairing and the
G1 result are written into it first). Main B needs main A's result committed, and runs once (a
lock file); a rerun needs a reason and never replaces the verdict of record.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import click
import numpy as np
import pandas as pd

from .data.store import RAW_ROOT, manifest_records

LAB = Path(__file__).resolve().parents[2]
RESULTS = LAB / "results"
RUNNERS = {
    "g0": ("sector_leadlag.g0", "run_g0"),
    "g1": ("sector_leadlag.g1", "run_g1"),
    "main-a": ("sector_leadlag.main", "run_main_a"),
    "main-b": ("sector_leadlag.main", "run_main_b"),
    "diagnostics": ("sector_leadlag.diagnostics", "run_diagnostics"),
}
REQUIRES = {
    "g0": (),
    "g1": ("g0",),
    "main-a": ("g0", "g1"),
    "main-b": ("g0", "main_a"),
    "diagnostics": ("g0", "main_a", "main_b"),
}


class StageError(click.ClickException):
    """A stage was asked to run before the stages it depends on, or a second time."""


def _json_default(value):
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"cannot serialise {type(value).__name__}")


def _git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(LAB), *args], capture_output=True, text=True, check=False
    )
    return done.stdout.strip()


def inputs_digest(root: Path) -> tuple[str, int]:
    """One SHA-256 over the stored payload of every input, and how many inputs there are."""
    records = manifest_records(root)
    lines = "".join(f"{key} {record['sha256']}\n" for key, record in records.items())
    return hashlib.sha256(lines.encode()).hexdigest(), len(records)


def meta() -> dict:
    digest, count = inputs_digest(RAW_ROOT)
    return {
        "ran_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain", "--", ".", ":(exclude)results")),
        "prereg_commit": _git("log", "-1", "--format=%H", "--", "PREREG.md"),
        "prereg_committed_at": _git("log", "-1", "--format=%cI", "--", "PREREG.md"),
        "main_a_commit": _git("log", "-1", "--format=%H", "--", "results/main_a.json"),
        "inputs_digest": digest,
        "inputs_count": count,
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


def check_ready(stage: str, results: Path, run_meta: dict) -> dict[str, dict]:
    if not run_meta["prereg_commit"]:
        raise StageError("commit PREREG.md before running any stage (design §3.5)")
    prior = {name: read_result(name, results) for name in REQUIRES[stage]}
    if "g0" in prior and not prior["g0"]["pass"]:
        raise StageError("G0 found no pairing that reproduces the ETF result (replication_failed)")
    if stage == "main-a":
        if not prior["g1"]["pass"]:
            raise StageError("G1 did not pass; fix the tools before running main A")
        ran = datetime.fromisoformat(prior["g1"]["meta"]["ran_at"])
        if datetime.fromisoformat(run_meta["prereg_committed_at"]) <= ran:
            raise StageError(
                "write the chosen pairing and the G1 result into PREREG.md and commit it"
                " before main A"
            )
    if stage == "main-b" and not run_meta["main_a_commit"]:
        raise StageError("commit results/main_a.json before main B (design §3.5)")
    return prior


def main_b_target(results: Path, rerun_reason: str | None) -> tuple[str, dict]:
    lock = results / "main_b.lock"
    if not lock.exists():
        return "main_b", {}
    if not rerun_reason:
        raise StageError(
            f"main B already ran ({lock.read_text().strip()}); pass --rerun-reason to run it again"
        )
    n = 1
    while (results / f"main_b_rerun_{n}.json").exists():
        n += 1
    record = read_result("main_b", results)["verdict"]
    return f"main_b_rerun_{n}", {"rerun_reason": rerun_reason, "verdict_of_record": record}


def take_lock(results: Path, commit: str) -> None:
    results.mkdir(parents=True, exist_ok=True)
    with (results / "main_b.lock").open("x", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(UTC).isoformat(timespec='seconds')} {commit}\n")


@click.group()
def main() -> None:
    """US-Japan sector lead-lag study (design 2026-10-19)."""


@main.command()
def snapshot() -> None:
    """Fetch the listed-issues file and every price history into the snapshot store."""
    from .data.snapshot import snapshot_all

    for line in snapshot_all():
        click.echo(line)


@main.command()
@click.argument("stage", type=click.Choice(list(RUNNERS)))
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
def inputs() -> None:
    """Write results/inputs.json: the stored payload (SHA-256, fetch time, URL) of every input."""
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / "inputs.json"
    path.write_text(json.dumps(manifest_records(RAW_ROOT), indent=1) + "\n", encoding="utf-8")
    click.echo(path)


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

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `79 passed, 1 skipped`.

- [ ] **Step 5: Lint and commit**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Add the CLI with the stage order and the main-B lock"
```

---

### Task 16: The results tables

**Files:**
- Create: `sector_leadlag_lab/src/sector_leadlag/report.py`
- Test: `sector_leadlag_lab/tests/test_report.py`

**Interfaces:**
- Consumes: every stage's result keys (Tasks 11–14) and `cli.write_result` (Task 15).
- Produces: `sector_leadlag.report.render(results: Path) -> str` (Japanese markdown; a stage without its JSON is skipped; a missing or NaN number prints as "—").

- [ ] **Step 1: Write the failing test**

File: `sector_leadlag_lab/tests/test_report.py` (create)

```python
import json

import pytest
from sector_leadlag import cli
from sector_leadlag.diagnostics import run_diagnostics
from sector_leadlag.g0 import run_g0
from sector_leadlag.g1 import run_g1
from sector_leadlag.main import run_main_a, run_main_b
from sector_leadlag.report import render


@pytest.fixture(scope="module")
def results(decayed_world, tmp_path_factory):
    """Every stage on the decayed world, written and read back as the CLI does."""
    root = tmp_path_factory.mktemp("results")

    def stage(name: str, result: dict) -> dict:
        cli.write_result(name, result, root, {"git_commit": "abc"})
        return json.loads((root / f"{name}.json").read_text(encoding="utf-8"))

    g0 = stage("g0", run_g0(decayed_world, {}))
    stage("g1", run_g1(decayed_world, {"g0": g0}, count=2))
    a = stage("main_a", run_main_a(decayed_world, {"g0": g0}, n_boot=200))
    b = stage("main_b", run_main_b(decayed_world, {"g0": g0, "main_a": a}))
    stage("diagnostics", run_diagnostics(decayed_world, {"g0": g0, "main_a": a, "main_b": b}))
    return root


def test_the_summary_has_every_section(results):
    text = render(results)
    for heading in ("## G0 再現", "## G1 合成データ", "## 本番 A", "## 本番 B", "## 診断"):
        assert heading in text
    assert "**判定：`usable`**" in text
    assert "| 公開値 | 23.79% |" in text
    assert "nan" not in text.lower()


def test_the_summary_skips_stages_that_have_not_run(tmp_path, results):
    (tmp_path / "g0.json").write_text((results / "g0.json").read_text(encoding="utf-8"))
    text = render(tmp_path)
    assert "## G0 再現" in text and "## 本番 A" not in text
```

- [ ] **Step 2: Run it to see it fail**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests/test_report.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sector_leadlag.report'`.

- [ ] **Step 3: Write the module**

File: `sector_leadlag_lab/src/sector_leadlag/report.py` (create)

```python
"""Markdown tables from the results JSON; README's result tables are copied from summary.md."""

from __future__ import annotations

import json
from pathlib import Path

SCENARIO_LABELS = {
    "base": "基準（500万円・0bp）",
    "cost_2bp": "片道 2bp",
    "capital_3m": "300万円",
    "capital_10m": "1,000万円",
    "cost_5bp": "片道 5bp（報告だけ）",
}
SIGNAL_LABELS = {
    "pca_lambda0": "正則化なしの PCA（λ=0）",
    "momentum": "モメンタム",
    "k1": "PCA SUB（K=1）",
    "variant_b": "副の型B（日本側をバスケットに）",
}


def _load(results: Path, name: str) -> dict | None:
    path = results / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _missing(x: float | None) -> bool:
    return x is None or x != x  # None, or NaN (an empty period)


def _pct(x: float | None) -> str:
    return "—" if _missing(x) else f"{100 * x:.2f}%"


def _num(x: float | None, digits: int = 2) -> str:
    return "—" if _missing(x) else f"{x:.{digits}f}"


def _fit(fit: dict | None) -> str:
    if fit is None:
        return "—"
    return f"{fit['beta_1e4']:.2f}（t={fit['t']:.2f}、p={fit['p']:.3f}）"


def _g0(g0: dict) -> list[str]:
    p = g0["published"]
    lines = [
        "## G0 再現（ETF だけ、2026-07-23 まで）",
        "",
        "| 並べ方 | AR 2015–2025 | RISK | R/R | MDD | A 年率 | B1 年率 | B1 累積 | C2O A→B1 "
        "| 係数 A（×1e-4） | 係数 B1 | A の日数 | 合格 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        f"| 公開値 | {_pct(p['ar'])} | {_pct(p['risk'])} | {p['rr']:.2f} | {_pct(p['mdd'])} "
        f"| {_pct(p['mean_a'])} | {_pct(p['mean_b1'])} | {_pct(p['cumulative_b1'])} "
        f"| {_pct(p['c2o_a'])}→{_pct(p['c2o_b1'])} | {p['beta_a_1e4']:.2f} "
        f"| {p['beta_b1_1e4']:.2f} | {p['days_a']} | |",
    ]
    for name, row in g0["variants"].items():
        o = row["original"]
        lines.append(
            f"| {name} | {_pct(o['ar'])} | {_pct(o['risk'])} | {o['rr']:.2f} | {_pct(o['mdd'])} "
            f"| {_pct(row['a']['mean_ann'])} | {_pct(row['b1']['mean_ann'])} "
            f"| {_pct(row['b1']['cumulative'])} | {_pct(row['c2o_a'])}→{_pct(row['c2o_b1'])} "
            f"| {_fit(row['fit_a'])} | {_fit(row['fit_b1'])} | {row['a']['days']} "
            f"| {'○' if row['pass'] else '×'} |"
        )
    chosen = g0["selected"] or "なし（replication_failed）"
    names = g0["checks"]["names"]
    lines += [
        "",
        f"選んだ並べ方：{chosen}。",
        "",
        f"銘柄：TOPIX500 {names['topix500']}、価格あり {names['with_prices']}、"
        f"なし {len(names['missing'])}（{', '.join(names['missing']) or 'なし'}）。",
        "",
        "| ETF（業種） | 日数 | 出来高ゼロ | 割合 | うち前日終値のまま |",
        "|---|---|---|---|---|",
    ]
    for sector, row in g0["checks"]["etf_zero_volume"].items():
        lines.append(
            f"| {sector} | {row['days']} | {row['zero']} | {_pct(row['share'])} "
            f"| {_pct(row['stale'])} |"
        )
    checks = g0["checks"]
    lines += [
        "",
        f"外れ値（|O2C| か |C2O| が 20% 超、除外しない）：{checks['outliers']['count']} 件。"
        f"分割 {checks['splits']['events']} 件のうち権利落ち日の C2O が外れたもの "
        f"{checks['splits']['flagged_count']} 件。配当 {checks['dividends']['events']} 件"
        f"（権利落ち日の |C2O| の平均：配当込み {_pct(checks['dividends']['mean_abs_c2o_with'])}、"
        f"配当なし {_pct(checks['dividends']['mean_abs_c2o_without'])}）。",
        "",
    ]
    cells = [
        (corr, sector, year)
        for sector, years in checks["coverage"].items()
        for year, corr in years.items()
        if not _missing(corr)
    ]
    lowest = sorted(cells)[:10]
    lines += [
        "ETF と H1 のバスケットの C2C の相関が低い業種と年（下位10）：",
        "",
        "| 業種 | 年 | 相関 |",
        "|---|---|---|",
        *[f"| {sector} | {year} | {corr:.3f} |" for corr, sector, year in lowest],
        "",
    ]
    return lines


def _g1(g1: dict) -> list[str]:
    return [
        "## G1 合成データ（米国を循環的にずらした世界）",
        "",
        f"H1 の検定が有意になった回数：{g1['significant']} / {g1['count']}"
        f"（合格の条件は2回以下）。合格：{'○' if g1['pass'] else '×'}。",
        f"検出力：係数 {g1['planted_beta_1e4']:.2f}×1e-4（0.5 β_ETF）を埋め込んで検出できた回数 "
        f"{g1['detected']} / {g1['count']}。",
        "",
    ]


def _main_a(a: dict) -> list[str]:
    low, high = a["h1"]["ratio_ci"]
    lines = [
        f"## 本番 A（2015-01-05〜2026-03-18、並べ方 {a['variant']}）",
        "",
        "| 価格 | 係数（×1e-4） |",
        "|---|---|",
        f"| H1 のバスケット | {_fit(a['h1']['basket'])} |",
        f"| ETF | {_fit(a['h1']['etf'])} |",
        "",
        f"比 β_B/β_ETF の95%区間：{low:.2f}〜{high:.2f}。H1：{'有意' if a['h1']['pass'] else '有意でない'}。",
        "",
        "| 設定 | 現物の買い 年率 | シャープ | CER | p | 平均の銘柄数 | 使った元手 "
        "| 業種の選び方の差 年率 | p |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for name, row in a["h2"].items():
        cash, spread = row["cash"], row["spread"]
        lines.append(
            f"| {SCENARIO_LABELS.get(name, name)} | {_pct(cash['mean_ann'])} "
            f"| {_num(cash['sharpe'])} | {_pct(cash['cer'])} | {_num(cash['p'], 4)} "
            f"| {_num(cash['mean_names'], 1)} | {_pct(cash['invested'])} "
            f"| {_pct(spread['mean_ann'])} | {_num(spread['p'], 4)} |"
        )
    lines += [
        "",
        f"H2：{'両方有意' if a['h2_pass'] else '有意でない'}。頑健性（2bp・300万円・1,000万円で符号が同じ）："
        f"{'○' if a['robust'] else '×'}。",
        "",
    ]
    return lines


def _main_b(b: dict) -> list[str]:
    h3 = b["h3"]
    return [
        "## 本番 B（2026-03-19〜2026-10-05）と判定",
        "",
        f"- H1 のバスケットの係数：{_fit(b['h1']['basket'])}。ETF：{_fit(b['h1']['etf'])}。",
        f"- 現物の買い：年率 {_pct(b['h2']['cash']['mean_ann'])}（{b['h2']['cash']['days']}日）。"
        f"業種の選び方の差：年率 {_pct(b['h2']['spread']['mean_ann'])}。",
        f"- ETF のロング・ショート：B1 年率 {_pct(b['etf_long_short']['b1']['mean_ann'])}"
        f"（累積 {_pct(b['etf_long_short']['b1']['cumulative'])}）、"
        f"B2 年率 {_pct(b['etf_long_short']['b2']['mean_ann'])}"
        f"（累積 {_pct(b['etf_long_short']['b2']['cumulative'])}、{h3['days_b2']}日）。",
        f"- H3：`{h3['label']}`（0 より低い p={h3['p_below_zero']:.3f}、"
        f"A より低い p={h3['p_below_a']:.3f}）。",
        "",
        f"**判定：`{b['verdict']}`**",
        "",
    ]


def _diagnostics(d: dict) -> list[str]:
    lines = [
        "## 診断（判定には使わない）",
        "",
        "| 始値の置き換え | 係数（×1e-4） |",
        "|---|---|",
    ]
    lines += [f"| {name} | {_fit(fit)} |" for name, fit in d["stale_opens"].items()]
    lines += [
        "",
        "| プラセボ | 実際の変化 年率 | 疑似の最小 | 疑似のうち実際以下 |",
        "|---|---|---|---|",
    ]
    for name, row in d["placebo"].items():
        lines.append(
            f"| {name} | {_pct(row['actual_ann'])} | {_pct(row['pseudo_min_ann'])} "
            f"| {_pct(row['share_at_or_below'])} |"
        )
    lines += ["", "| 分解 | 区間 | A | B1 | B2 |", "|---|---|---|---|---|"]
    for name, legs in d["decomposition"].items():
        for leg, row in legs.items():
            lines.append(
                f"| {name} | {leg} | {_pct(row['a'])} | {_pct(row['b1'])} | {_pct(row['b2'])} |"
            )
    lines += [
        "",
        f"- C2O を加えた回帰：ETF {_fit(d['c2o_control']['etf'])}、"
        f"バスケット {_fit(d['c2o_control']['basket'])}。",
        f"- 取引時間の延長の前後（バスケット）：{_fit(d['session_change']['basket']['before'])} → "
        f"{_fit(d['session_change']['basket']['after'])}。ETF：{_fit(d['session_change']['etf']['before'])} → "
        f"{_fit(d['session_change']['etf']['after'])}。",
        f"- 上位10銘柄のバスケット：A {_fit(d['top10_basket']['a'])}、B {_fit(d['top10_basket']['b'])}。",
        "",
        "| 別のシグナル | バスケットの係数 | ETF の係数 | ETF の AR 2015–2025 |",
        "|---|---|---|---|",
    ]
    for name, row in d["other_signals"].items():
        lines.append(
            f"| {SIGNAL_LABELS.get(name, name)} | {_fit(row['basket'])} | {_fit(row['etf'])} "
            f"| {_pct(row['etf_original']['ar'])} |"
        )
    c = d["reference_c"]
    lines += [
        "",
        f"参考 C（{c['days']}日）：バスケット {_fit(c['basket'])}、ETF {_fit(c['etf'])}、"
        f"ETF のロング・ショート 年率 {_pct(c['etf_long_short']['mean_ann'])}、"
        f"現物の買い 年率 {_pct(c['cash']['mean_ann'])}。",
        "",
    ]
    return lines


def render(results: Path) -> str:
    lines = ["# 日米業種リードラグ（候補12）の結果", ""]
    for name, part in (
        ("g0", _g0),
        ("g1", _g1),
        ("main_a", _main_a),
        ("main_b", _main_b),
        ("diagnostics", _diagnostics),
    ):
        result = _load(results, name)
        if result is not None:
            lines += part(result)
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 4: Run the tests to see them pass**

Run: `cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q`
Expected: `81 passed, 1 skipped` (about 25 s).

- [ ] **Step 5: Run the whole suite under the root config, lint and commit**

```bash
cd $WT && $PY -m pytest sector_leadlag_lab/tests -q && /home/kazumasa/projects/.venv/bin/ruff check --fix sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format sector_leadlag_lab && git add sector_leadlag_lab && git commit -m "Render the results tables"
```

Expected: `81 passed, 1 skipped` with the root `conftest.py` loaded too.

---
### Task 17: Snapshot the real data and pre-register

**Files:**
- Create: `sector_leadlag_lab/PREREG.md`, `sector_leadlag_lab/results/inputs.json`
- Data (outside Git): `/home/kazumasa/projects/_data/sector_leadlag_lab/raw/`

**Interfaces:**
- Consumes: `sector-leadlag snapshot` and `inputs` (Task 15).
- Produces: the PREREG commit that every result records as `meta.prereg_commit` (G0 and G1 run after it).

- [ ] **Step 1: Take the snapshot**

Run it after 18:00 Japan time so that the last Japanese day is final (an earlier run simply stops at the previous day). It fetches about 520 histories with a pause between them (10–20 minutes).

```bash
cd $WT && $SLL snapshot | grep -v -e ': stored' -e ': unchanged'
```

Expected: no output, or a few lines `yf/<code>.T: failed`. If any stock failed, run the same command once more (stored payloads are kept and only changed ones are written); names that still fail stay missing and G0 lists them. A failing SPDR or sector ETF stops the command with `FetchError`: rerun it later.

- [ ] **Step 2: Record what was stored**

```bash
cd $WT && $SLL inputs && $PY -c "import json; r = json.load(open('sector_leadlag_lab/results/inputs.json')); print(len(r), sum(k.startswith('yf/') for k in r))"
```

Expected: `<1 + 28 + stocks> <28 + stocks>`, with stocks = 491 minus the names that failed.

- [ ] **Step 3: Write PREREG.md**

File: `sector_leadlag_lab/PREREG.md` (create). Everything is fixed text; §4 stays a placeholder line until Task 18.

```markdown
# 事前登録：日米業種リードラグの反証と売買への利用（候補12）

- 設計書：`/home/kazumasa/projects/docs/superpowers/specs/2026-10-19-sector-leadlag-design.md`
- 実装計画：`/home/kazumasa/projects/docs/superpowers/plans/2026-10-19-sector-leadlag.md`
- この文書を commit してから G0 を初めて回す。G0 と G1 の結果を §4 に書き足して commit してから、本番 A を回す。以下を変えたら、結果の JSON と README に、変えたこと・理由・変える前に見ていた結果を書く。

## 1. 判定（設計書 §3 のまま）

- H1：本番 A（2015-01-05〜2026-03-18）で、H1 のバスケット（業種ごとに TOPIX500 の全銘柄を、d−1 までの60営業日の売買代金の中央値で加重）の寄付→引けのリターンを、業種と日の固定効果つきでシグナル sz に回帰した係数が正。標準誤差は日付クラスタ、片側5%。
- H2：本番 A で、次の2つがどちらも片側5%で正。検定は定常ブートストラップ（平均ブロック20営業日、1万回、種 20261019）。
  1. 現物の買いだけ（上位5業種×3銘柄を寄付の成行で買い、引けの成行で売る。元手500万円、1銘柄の予算は元手÷15、100株単位、費用は片道0bp）の、元手に対する日次リターンの平均。
  2. 上位5業種の3銘柄のバスケットの平均から、全17業種の同じバスケットの平均を引いた差の平均。
- H3（判定とは別に報告）：B2（2026-07-24〜10-05）の ETF のロング・ショートの日次の平均を、0 と比べ（t 検定）、本番 A の平均と比べる（Welch の t 検定）。どちらも片側5%。`decay_continued`・`decay_faded`・`unclear`。
- 判定：`replication_failed`・`etf_only`・`real_then_decayed`・`usable`・`real_not_usable`（設計書 §3.4 の条件のまま）。`usable` の③は、費用を片道 2bp にした場合、元手を300万円にした場合、1,000万円にした場合の3通りで、本番 A の1と2の平均の符号が基準と同じこと。④は、本番 B（2026-03-19〜10-05）で1と2の平均がどちらも正。片道 5bp は報告だけ。

## 2. 並べ方の選び方（G0。ETF の結果だけを使う）

- 並べ方は2通り。`same_date`：日米がともに開いている日だけを行にし、同じ日付の日米のリターンを並べる。`lagged`：日本の各営業日 d′ を行にし、米国の s(d′) のリターンを並べる。
- G0 の合格：本番 A の ETF の係数が正（片側5%）で、B1（2026-03-19〜07-23）の ETF のロング・ショートの平均が負。
- 合格したもののうち、2015-01〜2025-12 の ETF のロング・ショートの年率リターン（月次の複利リターンの平均×12）が原論文の 23.79% に最も近いものを使う。差が同じなら `same_date`。どちらも合格しなければ `replication_failed` で止め、原因を調べる。
- G0 では、2026-07-23 より後の ETF の値を使わない。株の価格はデータの検査にだけ使う。G1 で株の価格を使うのは、米国のリターンを循環的にずらした世界だけ。

## 3. 設計書が決めていない点の決定（実装計画の D1〜D17）

1. 評価する日は、s(d) があり窓が埋まっている日本の営業日すべて（yfinance の日付で本番 A は 2,735 日、B1 は 85 日）。
2. 日本の営業日は、その時点で上場している（最初の行から最後の行まで）TOPIX500 の銘柄の半数以上に出来高がある日。米国の営業日は XLK に出来高がある日。各市場の C2C は、その市場の前の営業日の終値から。
3. 窓は d より前の日付の行の直近60行。窓の中に欠損があるか値が一定の列（設定前の XLRE・XLC など）は、その窓では標準化リターン0・相関0とし、その列の z_{U,s(d)} も0とする。z_{U,s(d)} は窓の米国の平均と標準偏差（1/L）で標準化する。
4. 日本の ETF の C2C（シグナルの日本側）は配当込み終値から作る。O2C・C2O・C2C は、分割を調整した始値・終値と、その日が権利落ちの配当から作る。出来高ゼロの日のリターンは欠損とする。
5. ロング・ショートの片側の業種数は ⌊0.3·|J_d| + 10⁻⁹⌋。シグナルが同じ業種は、コードの小さい方を上にする。シグナルが全業種で同じ日は、ロング・ショートも現物の買いもしない。ETF の J_d はその日に出来高のあった ETF、バスケットの J_d は17業種すべて。
6. sz は、出来高ゼロの ETF の業種も含めて17業種で標準化する（標準偏差は 1/17 で割る）。ETF の回帰では、出来高ゼロの業種のその日の観測を外す。
7. パネル回帰は、業種と日の固定効果を交互射影で除く。標準誤差は日付クラスタで、補正は G/(G−1)·(N−1)/(N−K)（K は説明変数の数＋業種の数−1）。p は自由度 G−1 の t 分布の片側。係数は ×10⁻⁴ で報告する。
8. 比 β_B/β_ETF の95%区間：固定効果を除いたあとの日ごとの Σx·y と Σx² を、両方の回帰に共通の日で、日付の定常ブートストラップで引き直し、2つの傾きの比の 2.5% と 97.5% の点を取る。固定効果は推定値のまま。
9. H2 の平均の検定は中心化する：p = (1 + #{m* − m ≥ m}) / (B + 1)。乱数は500回ずつ引く（値は種で決まる）。
10. 現物の買い：株数は前日の実際の終値（yfinance の分割の調整を戻した値）で決め、損益は実際の始値と終値で計算する。その日に出来高のない銘柄は買わない。余った現金の利息は0。費用は、売買した額の片道 cost_bp。
11. H2 の2：業種ごとの3銘柄の等加重の O2C（出来高ゼロの銘柄は外して重みを戻す）の、上位5業種の平均から17業種の平均を引く。株数の切り捨てと費用は入れない。
12. H1 のバスケットと H2 の銘柄は、d−1 までの60営業日の売買代金（終値×出来高、出来高ゼロの日は0）の中央値で決める。60日分のない銘柄は入れない。
13. H3 の t 検定は、日次のリターンそのものに当てる（自己相関の補正はしない）。
14. G1：米国の C2C の行を k 営業日だけ循環的にずらし（k は60以上 n−60 未満、種 20261019 で20個）、C_full を含めてシグナルを作り直す。合格は、H1 の検定（本番 A、H1 のバスケット）が有意になるのが20回中2回以下。検出力は、G0 で選んだ並べ方の本番 A の ETF の係数の半分×ずらしたシグナルの sz をバスケットの O2C に足し、検出できた回数を数える（合否には使わない）。
15. G0 のデータの検査：出来高ゼロの日は、ETF ごとに日数・割合・前日終値のままだった割合にまとめる。|O2C| か |C2O| が 20% を超える日は、件数と大きい順の100件を一覧にする（除外しない）。分割は、権利落ち日の C2O の絶対値が 20% を超えるものを一覧にする。
16. 診断の始値の置き換え：置き換えた銘柄の O2C を、配当を入れない前日終値→終値のリターンにする。毎日ランダムに10%と20%、それに C2O の絶対値の大きい順に10%（切り上げ）。
17. 診断のプラセボ（h=85）：本番 A の中の疑似の公開日 τ（251日目から、あとに85日が残る日まで）ごとに「τ からの85日の平均 − τ より前の平均」を作り、実際の「B1 の最初の85日の平均 − 本番 A の平均」と比べる。
18. 本番 B は、`results/main_a.json` を commit してから1回だけ回す。

## 4. G0 と G1 の結果（本番 A の前に書き足す）

- （G0 と G1 を回したあとに書き足す。）
```

- [ ] **Step 4: Commit it and record the hash**

```bash
cd $WT && git add sector_leadlag_lab/PREREG.md sector_leadlag_lab/results/inputs.json && git commit -m "Pre-register the sector lead-lag tests before G0" && git log -1 --format=%H -- sector_leadlag_lab/PREREG.md
```

Expected: the printed hash is the `meta.prereg_commit` of G0 and G1.

---

### Task 18: G0 and G1 on the real data; write the choice into PREREG

**Files:**
- Create: `sector_leadlag_lab/results/g0.json`, `sector_leadlag_lab/results/g1.json`
- Modify: `sector_leadlag_lab/PREREG.md` (§4)

**Interfaces:**
- Consumes: the snapshot and the PREREG commit (Task 17).
- Produces: `results/g0.json` (`selected`) and `results/g1.json` (`pass`), and the PREREG commit that main A requires (made after G1 ran).

- [ ] **Step 1: Run G0**

```bash
cd $WT && $SLL run g0 && $PY -c "
import json
g = json.load(open('sector_leadlag_lab/results/g0.json'))
print('selected', g['selected'], 'missing', len(g['checks']['names']['missing']))
for name, v in g['variants'].items():
    print(name, round(v['original']['ar'], 4), round(v['fit_a']['beta_1e4'], 2), round(v['fit_a']['p'], 4), round(v['b1']['mean_ann'], 4), v['pass'])
"
```

Expected: `results/g0.json` is written and a pairing is selected. If `selected` is `None`, the verdict is `replication_failed` (spec §3.4): stop here, commit `g0.json`, and report the G0 table (`$SLL report` renders it) to the user without running anything else.

- [ ] **Step 2: Run G1**

```bash
cd $WT && $SLL run g1 && $PY -c "
import json
g = json.load(open('sector_leadlag_lab/results/g1.json'))
print(g['variant'], g['significant'], g['detected'], g['pass'])
"
```

Expected: `pass` is `True` (at most 2 of 20 rotated worlds significant); `detected` is the power at 0.5 β_ETF and decides nothing. If `pass` is `False`, stop: commit both JSON files and report to the user (spec §3.5, the tools must pass before main A).

- [ ] **Step 3: Write the G0 choice and the G1 result into PREREG.md**

Replace the placeholder line under `## 4.` with the following, filled from the two JSON files (values rounded as shown; nothing else in PREREG changes):

```markdown
- G0 で選んだ並べ方：`[g0.selected]`（G0 の commit 時点の PREREG は [g0.meta.prereg_commit の先頭7文字]）。
- `same_date`：2015–2025 の AR [variants.same_date.original.ar を % で小数2桁]、本番 A の ETF の係数 [fit_a.beta_1e4 小数2桁]×10⁻⁴（t=[fit_a.t 小数2桁]、p=[fit_a.p 小数4桁]）、B1 の ETF のロング・ショートの年率 [b1.mean_ann を %]、合格 [pass を ○/×]。
- `lagged`：同じ形。
- 価格のある TOPIX500 の銘柄：[checks.names.with_prices] / [checks.names.topix500]（価格なし：[checks.names.missing をカンマ区切り、なければ「なし」]）。
- G1：有意になった回数 [g1.significant] / [g1.count]（合格 [g1.pass を ○/×]）。検出力 [g1.detected] / [g1.count]（埋め込んだ係数 [g1.planted_beta_1e4 小数2桁]×10⁻⁴）。
```

- [ ] **Step 4: Commit**

```bash
cd $WT && git add sector_leadlag_lab/PREREG.md sector_leadlag_lab/results/g0.json sector_leadlag_lab/results/g1.json && git commit -m "Record G0 and G1 and write the chosen pairing into PREREG"
```

Expected: this commit is later than `g1.json`'s `meta.ran_at`, which `run main-a` checks.

---

### Task 19: Main A, main B (once) and the diagnostics

**Files:**
- Create: `sector_leadlag_lab/results/main_a.json`, `sector_leadlag_lab/results/main_b.json`, `sector_leadlag_lab/results/main_b.lock`, `sector_leadlag_lab/results/diagnostics.json`

**Interfaces:**
- Consumes: Tasks 17–18 (snapshot, PREREG commits, `g0.json`, `g1.json`).
- Produces: the verdict of record (`main_b.json` → `verdict`).

- [ ] **Step 1: Run main A and commit it before anything else**

```bash
cd $WT && $SLL run main-a && $PY -c "
import json
a = json.load(open('sector_leadlag_lab/results/main_a.json'))
print('H1', a['h1']['pass'], a['h1']['basket'], a['h1']['etf'], a['h1']['ratio_ci'])
print('H2', a['h2_pass'], {k: (round(v['cash']['mean_ann'], 4), round(v['cash']['p'], 4), round(v['spread']['mean_ann'], 4), round(v['spread']['p'], 4)) for k, v in a['h2'].items()})
print('robust', a['robust'])
" && git add sector_leadlag_lab/results/main_a.json && git commit -m "Record main A"
```

Expected: `results/main_a.json` written and committed (about a minute).

- [ ] **Step 2: Run main B once and commit it with its lock**

```bash
cd $WT && $SLL run main-b && $PY -c "
import json
b = json.load(open('sector_leadlag_lab/results/main_b.json'))
print(b['verdict'], b['h3']['label'], b['h1']['basket'], b['evidence'])
" && git add sector_leadlag_lab/results/main_b.json sector_leadlag_lab/results/main_b.lock && git commit -m "Record main B and the verdict"
```

Expected: the verdict is one of `etf_only`, `real_then_decayed`, `usable`, `real_not_usable`. Do not run `main-b` again; a later change of method goes into `main_b_rerun_<n>.json` with `--rerun-reason`, and the verdict of record stays this one (spec §3.5).

- [ ] **Step 3: Run the diagnostics and commit them**

```bash
cd $WT && $SLL run diagnostics && git add sector_leadlag_lab/results/diagnostics.json && git commit -m "Record the post-verdict diagnostics"
```

Expected: `results/diagnostics.json` written (a minute or two).

---

### Task 20: README, summary and the workspace checks

**Files:**
- Create: `sector_leadlag_lab/README.md`, `sector_leadlag_lab/results/summary.md`

**Interfaces:**
- Consumes: every `results/*.json` (Tasks 17–19) and `report.render` (Task 16).
- Produces: the write-up.

- [ ] **Step 1: Render the summary**

```bash
cd $WT && $SLL report && sed -n '1,240p' sector_leadlag_lab/results/summary.md
```

Expected: the five sections and the verdict line; no `nan`.

- [ ] **Step 2: Write the README**

File: `sector_leadlag_lab/README.md` (create), in Japanese, with these sections in this order and the tables copied from `results/summary.md`:

1. タイトルと一行の結論（`main_b.json` の判定をそのまま書く。`usable` のときだけ、設計書 §13 の次の段階を設計することを書く）。
2. 何を調べたか：2本の論文（SIG-FIN-036-13 と 037-10）、設計書 §2.3 の疑う点、問い（ETF の崩れは実装の問題か、予測力そのものが見かけか。本物なら、現物の買いだけで使えるか）。
3. データと期間：yfinance（SPDR 11本・NEXT FUNDS 17本・TOPIX500）と JPX の銘柄一覧（2026-09-30 時点）、推定・本番 A・B（B1・B2）・参考 C の期間、raw の場所 `/home/kazumasa/projects/_data/sector_leadlag_lab/raw/` と `results/inputs.json`。
4. 手順：時点のルール R1–R4、並べ方の選び方、PREREG の commit（`meta.prereg_commit` の値、G0 の前と本番 A の前の2つ）、G0–G2、H1–H3、判定の表。
5. 結果：G0（並べ方ごとの表と公開値）、G1（有意の回数と検出力）、本番 A（H1、比の区間、H2 と頑健性）、本番 B と判定、H3。
6. 診断：始値の置き換え、プラセボ、C2O と O2C の分解、C2O を加えた回帰、取引時間の延長の前後、別のシグナルと副の型B、上位10銘柄のバスケット、参考 C。どれも判定には使っていないと書く。
7. 限界：生存バイアス（2026-09-30 の一覧に残った銘柄だけ）、yfinance の値と snapshot、株の始値の時点、本番 B と B2 の短さ、買付余力の拘束、市場全体の日中の動き、取引時間の延長、G0 で ETF と相関の低かった業種と年（summary の下位10）、設計書 §5.2 を計画のときに改めたこと。
8. 再現手順：`$SLL snapshot`、`$SLL inputs`、`$SLL run g0`〜`diagnostics` の順番と PREREG の2つの commit、所要時間の目安、テストのコマンド。

- [ ] **Step 3: Run every check**

```bash
cd $WT && $PY -m pytest -c sector_leadlag_lab/pyproject.toml sector_leadlag_lab/tests -q
cd $WT && $PY -m pytest sector_leadlag_lab/tests -q
cd $WT && $PY -m pytest --collect-only -q 2>&1 | tail -3
cd $WT && /home/kazumasa/projects/.venv/bin/ruff check sector_leadlag_lab && /home/kazumasa/projects/.venv/bin/ruff format --check sector_leadlag_lab
```

Expected: `81 passed, 1 skipped` with both the member config and the root config; the workspace collection ends without errors; ruff clean.

- [ ] **Step 4: Commit**

```bash
cd $WT && git add sector_leadlag_lab/README.md sector_leadlag_lab/results/summary.md && git commit -m "Write up the sector lead-lag study with its result tables"
```

Do not merge or push. Report to the user: the branch, the verdict, the key numbers (G0's chosen pairing against the published values, H1's two coefficients and the ratio interval, H2's two means and p-values, period B, H3) and the open items. After the user approves the merge, run `uv sync` and `make test` in the main checkout `/home/kazumasa/projects` (never in the worktree), and check `git status --ignored` and the size of the worktree before removing it.
