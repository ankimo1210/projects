# JGB Term Premium Re-test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-test the BoJ Review 2026-E-10 claim that expected short rates and the term premium contributed roughly equally to the rise in 10-year JGB yields from end-July 2024 to end-June 2026, using four pre-registered models whose implementations pass validation gates before any Japanese result is computed.

**Architecture:** macrokit gains two data sources (BoJ call rate into DuckDB; US validation files as raw snapshots) and a `termstructure` subpackage: a Svensson curve builder that turns MoF par yields into a monthly zero panel, three model families (ACM with optional Kilian bias correction, Wu-Xia shadow rate, DNS-VAR) that all return the same `Decomposition`, and synthetic data generators for the gates. Research scripts under `macrokit/research/2026-10-jgb-term-premium/` run the gates, freeze the configuration with a hash, then run the Japanese estimation once.

**Tech Stack:** Python 3.12, numpy, scipy (optimize, special), duckdb, httpx, click, xlrd (legacy .xls), openpyxl (.xlsx), pytest, ruff.

**Spec:** `/home/kazumasa/projects/docs/superpowers/specs/2026-10-17-jgb-term-premium-design.md` (approved 2026-10-17; §9 records the pre-gate changes made after verifying the external data).

## Global Constraints

- Worktree: `WT=/home/kazumasa/worktrees/jgb-term-premium`, branch `macrokit-term-premium`, created from `main`. Never create untracked files inside `$WT` other than ones you will commit; data lives in `/home/kazumasa/projects/macrokit/data` (absolute path, main checkout, gitignored).
- Python command (use it for every run; the editable install points at the main checkout, `PYTHONPATH` makes the worktree code win, single-thread BLAS is required):
  `PY="env PYTHONPATH=$WT/macrokit/src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/kazumasa/projects/.venv/bin/python"`
  CLI: `MK="env PYTHONPATH=$WT/macrokit/src /home/kazumasa/projects/.venv/bin/macrokit --data-root /home/kazumasa/projects/macrokit/data"`
- Tests: `cd $WT && $PY -m pytest macrokit/tests -q`. The whole macrokit suite must stay under ~30 s of added time.
- Lint/format: `cd $WT && /home/kazumasa/projects/.venv/bin/ruff check macrokit && /home/kazumasa/projects/.venv/bin/ruff format --check macrokit`. ruff config is macrokit's (`line-length = 100`, `select = ["E","W","F","I","B","UP","N","RUF"]`); B905 means every `zip()` needs `strict=`; no function calls in argument defaults (B008); no closures over loop variables (B023).
- Run `uv` only from the repo/worktree root (`cd $WT && uv lock`). Never `uv sync` inside a member directory.
- Dependencies: `scipy`, `xlrd` and `openpyxl` (all approved by the user on 2026-10-17; all already locked for other workspace members).
- Units: zero yields are continuously compounded **annual percent**; one period is one month; maturities are integer months. ACM works in log prices with the one-month rate in decimal per month (`y/1200`). The shadow-rate model works in annual percent with the convexity factor `1/1200`.
- Fixed settings come from the spec and must not change after Japanese results exist: window t0 = last data day of July 2024, t1 = last data day of June 2026; estimation 1986-08..2026-06; verdict band [0.35, 0.65]; ACM K = 5, factor maturities 3..120 step 3, return maturities {6, 12, 24, 36, …, 120}; Kilian 1,000 draws; shadow r_L = −0.10 %, forward maturities {3, 6, 12, 24, 60, 84, 120}, 20 starts; DNS λ = 0.0609; intervals 90 % from 1,000 bootstrap draws (500 parameter draws for the shadow model); G1 20,000 months, |ŝ − s| ≤ 0.05 and TP RMSE ≤ 0.10 pt; G2 corr ≥ 0.95, RMSE ≤ 0.25 pt, change gap ≤ 0.15 pt; G3 equality within 1 bp, Wu-Xia corr ≥ 0.9; G4 median par error ≤ 3 bp.
- Commit messages: English, imperative, no `feat:` prefix (match `git log -- macrokit`), ending with the attribution lines from the session (`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and the `Claude-Session:` line).
- Docs are Japanese; code, identifiers and commit messages are English.
- Do not push and do not merge into `main` without the user's explicit approval.

## Review Focus

- A month-end on which MoF has yields but BoJ has no call-rate value that day (holiday mismatch): the anchor must be the last daily value earlier in the same month, never a value from the next month (Task 3 test `test_overnight_uses_the_last_daily_value_in_the_month`).
- Early months with only 1–10 year tenors (1986-08..11) and pre-1999 months without 30/40 years: the Svensson fit must run on whatever tenors exist (Task 3 test `test_fit_runs_with_only_short_tenors`).
- Optimizer steps into non-stationary P-dynamics or a singular innovation covariance: the shadow likelihood returns a finite penalty instead of raising (Task 9 test `test_loglik_penalises_non_stationary_dynamics`).
- OLS VAR estimate already non-stationary before bias correction: Kilian correction must return it unchanged (Task 7 test `test_kilian_leaves_a_non_stationary_estimate_alone`).
- A window with essentially no change in the 10-year yield: the share must raise, not return ±inf (Task 5 test `test_share_refuses_a_flat_window`).

---

### Task 1: Worktree, dependencies, and reading back stored snapshots

**Files:**
- Modify: `macrokit/pyproject.toml` (dependencies)
- Modify: `uv.lock` (via `uv lock`)
- Modify: `macrokit/src/macrokit/snapshot.py` (add `latest_payload`)
- Test: `macrokit/tests/test_snapshot.py`

**Interfaces:**
- Consumes: `save_snapshot`, `manifest_path` (existing).
- Produces: `macrokit.snapshot.latest_payload(root: Path, source: str, indicator: str) -> Path | None`.

- [ ] **Step 1: Create the worktree and confirm the dependency approval**

```bash
cd /home/kazumasa/projects && git status --short && git worktree add /home/kazumasa/worktrees/jgb-term-premium -b macrokit-term-premium main
```

The user approved `scipy`, `xlrd` and `openpyxl` on 2026-10-17.

- [ ] **Step 2: Add the dependencies and relock**

In `$WT/macrokit/pyproject.toml`, replace the `dependencies` list with (alphabetical):

```toml
dependencies = [
    "click>=8.1",
    "duckdb>=1.0",
    "httpx>=0.27",
    "numpy>=1.26",
    "openpyxl>=3.1",
    "pandas>=2.2",
    "pydantic>=2.7",
    "pyyaml>=6",
    "scipy>=1.13",
    "tenacity>=8.3",
    "xlrd>=2.0",
]
```

Run: `cd $WT && uv lock`
Expected: the lock gains macrokit edges to `openpyxl`, `scipy`, `xlrd`; no new packages are downloaded (all three are already locked for other members). Check with `git -C $WT diff --stat uv.lock` (a few lines).

- [ ] **Step 3: Write the failing test**

Append to `$WT/macrokit/tests/test_snapshot.py` (it already imports `datetime`, `UTC` and `save_snapshot`; add `latest_payload` to the `from macrokit.snapshot import ...` line):

```python
def test_latest_payload_is_the_last_stored_file_even_after_unchanged_fetches(tmp_path):
    root = tmp_path / "raw"
    when = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
    save_snapshot(root, "us_term", "gsw", b"one", ingested_at=when, url="u", http_status=200)
    second = save_snapshot(root, "us_term", "gsw", b"two", ingested_at=when, url="u", http_status=200)
    unchanged = save_snapshot(root, "us_term", "gsw", b"two", ingested_at=when, url="u", http_status=200)

    assert unchanged.path is None
    assert latest_payload(root, "us_term", "gsw") == second.path
    assert latest_payload(root, "us_term", "acm") is None
    assert latest_payload(tmp_path / "missing", "us_term", "gsw") is None
```

- [ ] **Step 4: Run it to verify it fails**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_snapshot.py -q`
Expected: FAIL with `ImportError: cannot import name 'latest_payload'`.

- [ ] **Step 5: Implement**

Add to `$WT/macrokit/src/macrokit/snapshot.py` after `last_sha`:

```python
def latest_payload(root: Path, source: str, indicator: str) -> Path | None:
    """Path of the most recently *stored* payload, or None if nothing was stored.

    An unchanged fetch records ``path: null``; the bytes it saw are the last
    stored file, so that file is still the current content.
    """
    manifest = manifest_path(root)
    if not manifest.exists():
        return None
    newest: str | None = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a truncated final line, as in last_sha
        if (
            record.get("source") == source
            and record.get("indicator") == indicator
            and record.get("path")
        ):
            newest = record["path"]
    return root / newest if newest else None
```

- [ ] **Step 6: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_snapshot.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd $WT && git add macrokit/pyproject.toml uv.lock macrokit/src/macrokit/snapshot.py macrokit/tests/test_snapshot.py && git commit -m "Add scipy and the spreadsheet readers to macrokit, and read back the newest snapshot"
```

---

### Task 2: BoJ overnight call rate source and `macrokit callrate`

**Files:**
- Create: `macrokit/src/macrokit/sources/boj_api.py`
- Modify: `macrokit/src/macrokit/cli.py` (new command)
- Create: `macrokit/tests/fixtures/boj_call_daily.json`, `macrokit/tests/fixtures/boj_call_mavg.json`
- Test: `macrokit/tests/test_boj_api.py`, `macrokit/tests/test_cli.py` (help parametrize)

**Interfaces:**
- Consumes: `store.RateObservation`, `store.insert_rates`, `snapshot.save_snapshot`.
- Produces: constants `DAILY_CURVE = "jp_call_on"`, `MONTHLY_CURVE = "jp_call_on_mavg"`, `OVERNIGHT_TENOR_Y = 1 / 365`; `parse_series(content, *, curve, source_url, ingested_at) -> list[RateObservation]`; `BojCallRateAdapter.fetch_raw() -> list[tuple[bytes, str, int, str]]` and `.parse(payloads, *, ingested_at)`. Monthly rows carry `obs_date` = first day of the month.

- [ ] **Step 1: Write the fixtures**

`$WT/macrokit/tests/fixtures/boj_call_daily.json` — a verbatim response fetched 2026-10-17 (June 2026):

```json
{
"STATUS":200,
"MESSAGEID":"M181000I",
"MESSAGE":"Successfully completed",
"DATE":"2026-10-17T17:25:05.995+09:00",
"PARAMETER":{"FORMAT":"JSON","LANG":"EN","DB":"FM01","STARTDATE":"202606","ENDDATE":"202606","STARTPOSITION":""},
"NEXTPOSITION":null,
"RESULTSET":[
{
"SERIES_CODE":"STRDCLUCON",
"NAME_OF_TIME_SERIES":"Call Rate, Uncollateralized Overnight, Average (Daily)",
"UNIT":"percent per annum",
"FREQUENCY":"DAILY",
"CATEGORY":"Call Rate",
"LAST_UPDATE":20261016,
"VALUES":{
"SURVEY_DATES":[20260601,20260602,20260603,20260604,20260605,20260606,20260607,20260608,20260609,20260610,20260611,20260612,20260613,20260614,20260615,20260616,20260617,20260618,20260619,20260620,20260621,20260622,20260623,20260624,20260625,20260626,20260627,20260628,20260629,20260630],
"VALUES":[0.726,0.727,0.727,0.726,0.727,null,null,0.727,0.727,0.727,0.727,0.727,null,null,0.727,0.727,0.978,0.977,0.977,null,null,0.977,0.976,0.977,0.978,0.977,null,null,0.978,0.976]
}
}
]
}
```

`$WT/macrokit/tests/fixtures/boj_call_mavg.json` — same structure as the live monthly response (verified 2026-10-17: `SURVEY_DATES` are `YYYYMM`); the first value is real (1985-07), the others are illustrative:

```json
{
"STATUS":200,
"MESSAGEID":"M181000I",
"MESSAGE":"Successfully completed",
"DATE":"2026-10-17T17:30:00.000+09:00",
"PARAMETER":{"FORMAT":"JSON","LANG":"EN","DB":"FM02","STARTDATE":"198501","ENDDATE":"","STARTPOSITION":""},
"NEXTPOSITION":null,
"RESULTSET":[
{
"SERIES_CODE":"STRACLUCON",
"NAME_OF_TIME_SERIES":"Call Rate, Uncollateralized Overnight/Average",
"UNIT":"percent per annum",
"FREQUENCY":"MONTHLY",
"CATEGORY":"Call Rate",
"LAST_UPDATE":20261016,
"VALUES":{"SURVEY_DATES":[198506,198507,198508],"VALUES":[null,6.4167,6.5]}
}
]
}
```

- [ ] **Step 2: Write the failing tests**

`$WT/macrokit/tests/test_boj_api.py`:

```python
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.sources import boj_api

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)


def _parse(name, curve):
    content = (FIXTURES / name).read_bytes()
    return boj_api.parse_series(content, curve=curve, source_url="u", ingested_at=NOW)


def test_daily_rows_skip_nulls_and_keep_the_mid_month_hike():
    rows = _parse("boj_call_daily.json", boj_api.DAILY_CURVE)
    by_day = {r.obs_date: r.yield_pct for r in rows}
    assert len(rows) == 22  # 30 calendar days, 8 nulls (weekends)
    assert date(2026, 6, 6) not in by_day
    assert by_day[date(2026, 6, 16)] == 0.727
    assert by_day[date(2026, 6, 17)] == 0.978
    assert by_day[date(2026, 6, 30)] == 0.976
    assert {r.curve for r in rows} == {"jp_call_on"}
    assert {r.tenor_y for r in rows} == {1 / 365}


def test_monthly_rows_are_dated_on_the_first_of_the_month():
    rows = _parse("boj_call_mavg.json", boj_api.MONTHLY_CURVE)
    assert [(r.obs_date, r.yield_pct) for r in rows] == [
        (date(1985, 7, 1), 6.4167),
        (date(1985, 8, 1), 6.5),
    ]


def test_an_error_status_is_raised_with_the_message():
    content = b'{"STATUS":400,"MESSAGEID":"M181005E","MESSAGE":"Invalid DB","RESULTSET":[]}'
    with pytest.raises(boj_api.BojApiError, match="M181005E"):
        boj_api.parse_series(content, curve="x", source_url="u", ingested_at=NOW)


def test_a_paged_response_is_refused():
    content = (FIXTURES / "boj_call_daily.json").read_text().replace(
        '"NEXTPOSITION":null', '"NEXTPOSITION":2'
    )
    with pytest.raises(boj_api.BojApiError, match="NEXTPOSITION"):
        boj_api.parse_series(content.encode(), curve="x", source_url="u", ingested_at=NOW)


def test_adapter_parse_keeps_each_payloads_curve():
    daily = (FIXTURES / "boj_call_daily.json").read_bytes()
    monthly = (FIXTURES / "boj_call_mavg.json").read_bytes()
    rows = boj_api.BojCallRateAdapter().parse(
        [(daily, "u1", 200, boj_api.DAILY_CURVE), (monthly, "u2", 200, boj_api.MONTHLY_CURVE)],
        ingested_at=NOW,
    )
    assert {r.curve for r in rows} == {"jp_call_on", "jp_call_on_mavg"}
    assert len(rows) == 24
```

In `$WT/macrokit/tests/test_cli.py`, add `["callrate", "--help"],` and `["us-term", "--help"],` to the `test_help_exits_zero_for_every_command` parametrize list (the `us-term` entry turns green in Task 4).

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_boj_api.py -q`
Expected: FAIL with `ImportError: cannot import name 'boj_api'`.

- [ ] **Step 4: Implement the source**

`$WT/macrokit/src/macrokit/sources/boj_api.py`:

```python
"""BoJ Time-Series Data Search API: the uncollateralized overnight call rate.

Verified 2026-10-17: ``GET https://www.stat-search.boj.or.jp/api/v1/getDataCode``
with ``format=json&lang=en&db=...&code=...&startDate=YYYYMM`` needs no key and
returns ``RESULTSET[0].VALUES.{SURVEY_DATES, VALUES}``, with ``null`` on days
without a value and ``NEXTPOSITION`` set when the answer is paged (60,000 points
per request; the full daily history is about 15,000).

The daily series (FM01 STRDCLUCON) starts 1998-01-05. The monthly average
(FM02 STRACLUCON) starts 1985-07 and is the curve anchor before 1998 (design
2026-10-17 §3.2). Monthly rows are dated on the first of the month. The current
month's average is incomplete when fetched and ``INSERT OR IGNORE`` never
updates it; only months before 1998 are used, so that row does not matter.
"""

from __future__ import annotations

import json
from datetime import date, datetime

import httpx

from ..store import RateObservation

API_URL = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"
DAILY = ("FM01", "STRDCLUCON", "199801")
MONTHLY_AVERAGE = ("FM02", "STRACLUCON", "198501")
DAILY_CURVE = "jp_call_on"
MONTHLY_CURVE = "jp_call_on_mavg"
OVERNIGHT_TENOR_Y = 1 / 365


class BojApiError(RuntimeError):
    """The BoJ API payload could not be fetched or parsed."""


def _survey_date(code: int) -> date:
    text = str(code)
    if len(text) == 8:
        return date(int(text[:4]), int(text[4:6]), int(text[6:]))
    if len(text) == 6:
        return date(int(text[:4]), int(text[4:]), 1)
    raise BojApiError(f"unexpected SURVEY_DATES entry {code!r}")


def parse_series(
    content: bytes, *, curve: str, source_url: str, ingested_at: datetime
) -> list[RateObservation]:
    """Rows of one single-series ``getDataCode`` response; nulls are skipped."""
    payload = json.loads(content)
    if payload.get("STATUS") != 200:
        raise BojApiError(
            f"{source_url}: {payload.get('MESSAGEID')} {payload.get('MESSAGE')}"
        )
    if payload.get("NEXTPOSITION") is not None:
        raise BojApiError(f"{source_url}: paged response (NEXTPOSITION); narrow startDate")
    results = payload.get("RESULTSET") or []
    if len(results) != 1:
        raise BojApiError(f"{source_url}: expected one series, got {len(results)}")
    values = results[0]["VALUES"]
    rows: list[RateObservation] = []
    for code, value in zip(values["SURVEY_DATES"], values["VALUES"], strict=True):
        if value is None:
            continue
        rows.append(
            RateObservation(
                curve=curve,
                obs_date=_survey_date(code),
                tenor_y=OVERNIGHT_TENOR_Y,
                yield_pct=float(value),
                source="boj_api",
                source_url=source_url,
                ingested_at=ingested_at,
            )
        )
    return rows


class BojCallRateAdapter:
    source = "boj_api"

    def __init__(self, *, timeout: float = 60.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> list[tuple[bytes, str, int, str]]:
        """(content, url, status, curve) for the daily and the monthly-average series."""
        payloads: list[tuple[bytes, str, int, str]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for (db, code, start), curve in (
                (DAILY, DAILY_CURVE),
                (MONTHLY_AVERAGE, MONTHLY_CURVE),
            ):
                params = {"format": "json", "lang": "en", "db": db, "code": code, "startDate": start}
                response = client.get(API_URL, params=params)
                if response.status_code != 200:
                    raise BojApiError(f"GET {response.url} returned {response.status_code}")
                payloads.append((response.content, str(response.url), response.status_code, curve))
        return payloads

    def parse(
        self, payloads: list[tuple[bytes, str, int, str]], *, ingested_at: datetime
    ) -> list[RateObservation]:
        rows: list[RateObservation] = []
        for content, url, _status, curve in payloads:
            rows.extend(parse_series(content, curve=curve, source_url=url, ingested_at=ingested_at))
        return rows
```

- [ ] **Step 5: Add the CLI command**

In `$WT/macrokit/src/macrokit/cli.py` add the import `from .sources.boj_api import BojCallRateAdapter` (keep the import block sorted) and, after `rates_command`:

```python
@main.command("callrate")
@click.pass_context
def callrate_command(ctx: click.Context) -> None:
    """Ingest the BoJ uncollateralized overnight call rate (daily and monthly average)."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    now = datetime.now(UTC)
    adapter = BojCallRateAdapter()

    payloads = adapter.fetch_raw()
    for content, url, status, curve in payloads:
        save_snapshot(
            data_root / "raw",
            adapter.source,
            curve,
            content,
            ingested_at=now,
            url=url,
            http_status=status,
            filename=f"{curve}.json",
        )
    rows = adapter.parse(payloads, ingested_at=now)
    inserted = insert_rates(con, rows)
    click.echo(f"callrate: {len(rows)} rows parsed, {inserted} inserted")
```

- [ ] **Step 6: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_boj_api.py macrokit/tests/test_cli.py -q -k "boj or callrate or help"`
Expected: PASS except the `us-term` help case (FAIL until Task 4).

- [ ] **Step 7: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/sources/boj_api.py macrokit/src/macrokit/cli.py macrokit/tests/test_boj_api.py macrokit/tests/test_cli.py macrokit/tests/fixtures/boj_call_daily.json macrokit/tests/fixtures/boj_call_mavg.json && git commit -m "Ingest the BoJ overnight call rate as the curve's short end"
```

---

### Task 3: Svensson curves and the monthly zero panel

**Files:**
- Create: `macrokit/src/macrokit/termstructure/__init__.py` (empty docstring module)
- Create: `macrokit/src/macrokit/termstructure/curve.py`
- Test: `macrokit/tests/test_curve.py`

**Interfaces:**
- Consumes: `store.connect`, `store.insert_rates`, `store.RateObservation`; curves `jgb`, `jp_call_on`, `jp_call_on_mavg`.
- Produces:
  - `svensson_zero(params: np.ndarray, t_years: np.ndarray) -> np.ndarray` (annual %, continuous)
  - `par_yields(params, maturities_years) -> np.ndarray` (annual %, semiannual coupons; maturities multiples of 0.5 up to 40)
  - `CurveFit(obs_date, params, tenors, observed, fitted, overnight)` with `.errors_bp`
  - `fit_svensson(tenors, par, overnight, previous=None, *, obs_date) -> CurveFit`
  - `overnight_at(con, day) -> float | None`
  - `fit_month_ends(con, start: date, end: date) -> list[CurveFit]`
  - `ZeroPanel(dates, months, yields)` with `.column(n)`, `.columns(ns)`, `.window(start, end)`
  - `zero_panel(fits, max_months=360) -> ZeroPanel`

- [ ] **Step 1: Write the failing tests**

`$WT/macrokit/tests/test_curve.py`:

```python
from datetime import UTC, date, datetime

import numpy as np
import pytest

from macrokit import store
from macrokit.termstructure import curve

NOW = datetime(2026, 10, 17, 9, 0, tzinfo=UTC)
TRUE = np.array([3.0, -2.9, -1.0, 1.5, 1.0, 10.0])
TENORS = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 40], dtype=float)


def test_short_end_is_beta0_plus_beta1():
    assert curve.svensson_zero(TRUE, np.array([1e-9]))[0] == pytest.approx(0.1, abs=1e-6)


def test_flat_continuous_curve_has_the_semiannual_equivalent_par_yield():
    flat = np.array([2.0, 0.0, 0.0, 0.0, 1.0, 5.0])
    expected = 200 * (np.exp(0.01) - 1)
    np.testing.assert_allclose(curve.par_yields(flat, np.array([1.0, 10.0, 40.0])), expected)


def test_a_par_bond_prices_at_par():
    coupon = curve.par_yields(TRUE, np.array([7.0]))[0]
    times = np.arange(1, 15) / 2.0
    disc = np.exp(-curve.svensson_zero(TRUE, times) / 100 * times)
    assert (coupon / 2 * disc).sum() + disc[-1] * 100 == pytest.approx(100.0, abs=1e-10)


def test_fit_recovers_an_exact_svensson_curve():
    par = curve.par_yields(TRUE, TENORS)
    overnight = curve.svensson_zero(TRUE, np.array([curve.OVERNIGHT_T]))[0]
    fit = curve.fit_svensson(TENORS, par, overnight, obs_date=date(2024, 7, 31))
    assert np.abs(fit.errors_bp).max() < 0.01
    months = np.arange(12, 361) / 12
    np.testing.assert_allclose(
        curve.svensson_zero(fit.params, months), curve.svensson_zero(TRUE, months), atol=0.005
    )


def test_fit_runs_with_only_short_tenors():
    short = TENORS[:10]
    fit = curve.fit_svensson(short, curve.par_yields(TRUE, short), None, obs_date=date(1986, 8, 30))
    assert np.abs(fit.errors_bp).max() < 0.5
    assert np.isfinite(curve.svensson_zero(fit.params, np.arange(1, 361) / 12)).all()


def _rate(curve_name, day, tenor, value):
    return store.RateObservation(curve_name, day, tenor, value, "test", "u", NOW)


@pytest.fixture
def market(tmp_path):
    con = store.connect(tmp_path / "t.duckdb")
    rows = []
    for day in (date(2024, 7, 30), date(2024, 7, 31), date(2024, 8, 30), date(1997, 3, 31)):
        par = curve.par_yields(TRUE, TENORS)
        rows += [_rate("jgb", day, t, float(v)) for t, v in zip(TENORS, par, strict=True)]
    rows.append(_rate("jp_call_on", date(2024, 7, 29), 1 / 365, 0.077))
    rows.append(_rate("jp_call_on", date(2024, 8, 1), 1 / 365, 0.227))
    rows.append(_rate("jp_call_on_mavg", date(1997, 3, 1), 1 / 365, 0.48))
    store.insert_rates(con, rows)
    return con


def test_overnight_uses_the_last_daily_value_in_the_month(market):
    assert curve.overnight_at(market, date(2024, 7, 31)) == 0.077  # not 0.227 from August
    assert curve.overnight_at(market, date(2024, 8, 30)) == 0.227


def test_overnight_falls_back_to_the_monthly_average_and_then_to_none(market):
    assert curve.overnight_at(market, date(1997, 3, 31)) == 0.48
    assert curve.overnight_at(market, date(1996, 1, 31)) is None


def test_fit_month_ends_picks_the_last_day_of_each_month(market):
    fits = curve.fit_month_ends(market, date(2024, 7, 1), date(2024, 8, 31))
    assert [f.obs_date for f in fits] == [date(2024, 7, 31), date(2024, 8, 30)]
    assert [f.overnight for f in fits] == [0.077, 0.227]


def test_zero_panel_columns_and_window():
    fits = [
        curve.CurveFit(date(2024, 7, 31), TRUE, TENORS, TENORS, TENORS, None),
        curve.CurveFit(date(2024, 8, 30), TRUE + [0.1, 0, 0, 0, 0, 0], TENORS, TENORS, TENORS, None),
    ]
    panel = curve.zero_panel(fits)
    assert panel.yields.shape == (2, 360)
    assert panel.column(120)[1] - panel.column(120)[0] == pytest.approx(0.1)
    assert panel.columns(np.array([1, 120])).shape == (2, 2)
    assert panel.window(date(2024, 8, 1), date(2024, 8, 31)).dates == (date(2024, 8, 30),)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_curve.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'macrokit.termstructure'`.

- [ ] **Step 3: Implement**

`$WT/macrokit/src/macrokit/termstructure/__init__.py`:

```python
"""Term-structure models for the JGB term-premium re-test (design 2026-10-17)."""
```

`$WT/macrokit/src/macrokit/termstructure/curve.py`:

```python
"""Svensson curves fitted to MoF par yields plus the overnight call rate (design §3.3).

MoF publishes semiannual-compounding yields of fixed-coupon JGBs splined across
issues; they are treated as par yields of semiannual-pay bonds. The overnight
call rate anchors the short end because MoF has nothing under one year.
"""

from __future__ import annotations

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
from scipy.optimize import least_squares

OVERNIGHT_T = 1.0 / 365.0
HALF_YEARS = np.arange(1, 81) / 2.0  # coupon dates up to 40 years
TAU_GRID = (0.5, 1.0, 2.0, 5.0, 10.0)
TAU_BOUNDS = (0.05, 30.0)
MAX_MONTHS = 360


def svensson_zero(params: np.ndarray, t_years: np.ndarray) -> np.ndarray:
    """Continuously compounded zero yield (annual %) at maturities ``t_years``."""
    b0, b1, b2, b3, tau1, tau2 = params
    t = np.asarray(t_years, dtype=float)
    x1 = t / tau1
    x2 = t / tau2
    f1 = -np.expm1(-x1) / x1
    f2 = -np.expm1(-x2) / x2
    return b0 + b1 * f1 + b2 * (f1 - np.exp(-x1)) + b3 * (f2 - np.exp(-x2))


def par_yields(params: np.ndarray, maturities_years: np.ndarray) -> np.ndarray:
    """Annual % coupon pricing a semiannual-pay bond at par: c = 200 (1 - P(T)) / sum P(t_i)."""
    maturities = np.asarray(maturities_years, dtype=float)
    index = np.rint(maturities * 2).astype(int) - 1
    if (np.abs((index + 1) / 2 - maturities) > 1e-9).any() or index.max() >= len(HALF_YEARS):
        raise ValueError("par_yields needs maturities that are multiples of 0.5 up to 40 years")
    disc = np.exp(-svensson_zero(params, HALF_YEARS) / 100 * HALF_YEARS)
    annuity = np.cumsum(disc)
    return 200 * (1 - disc[index]) / annuity[index]


@dataclass(frozen=True)
class CurveFit:
    obs_date: date
    params: np.ndarray
    tenors: np.ndarray
    observed: np.ndarray  # par yields, annual %
    fitted: np.ndarray
    overnight: float | None

    @property
    def errors_bp(self) -> np.ndarray:
        return (self.fitted - self.observed) * 100.0


def fit_svensson(
    tenors: np.ndarray,
    par: np.ndarray,
    overnight: float | None,
    previous: np.ndarray | None = None,
    *,
    obs_date: date,
) -> CurveFit:
    """Least-squares Svensson fit to par yields (equal weights) and the overnight point.

    Solved from the previous month's parameters and a fixed grid of (tau1, tau2)
    starts; the lowest cost wins, so the result is deterministic.
    """
    tenors = np.asarray(tenors, dtype=float)
    par = np.asarray(par, dtype=float)

    def residuals(p: np.ndarray) -> np.ndarray:
        res = par_yields(p, tenors) - par
        if overnight is not None:
            res = np.append(res, svensson_zero(p, np.array([OVERNIGHT_T]))[0] - overnight)
        return res

    level = float(par[-1])
    short = float(overnight if overnight is not None else par[0])
    starts = [] if previous is None else [np.asarray(previous, dtype=float)]
    starts += [
        np.array([level, short - level, 0.0, 0.0, tau1, tau2])
        for tau1 in TAU_GRID
        for tau2 in TAU_GRID
        if tau2 > tau1
    ]
    lower = [-np.inf] * 4 + [TAU_BOUNDS[0]] * 2
    upper = [np.inf] * 4 + [TAU_BOUNDS[1]] * 2
    best = None
    for x0 in starts:
        x0 = np.clip(x0, lower, upper)
        sol = least_squares(residuals, x0, bounds=(lower, upper), x_scale="jac", max_nfev=2000)
        if best is None or sol.cost < best.cost:
            best = sol
    return CurveFit(obs_date, best.x, tenors, par, par_yields(best.x, tenors), overnight)


def overnight_at(con: duckdb.DuckDBPyConnection, day: date) -> float | None:
    """Last daily call rate on or before ``day`` in the same month, else that month's average."""
    first = day.replace(day=1)
    row = con.execute(
        "SELECT yield_pct FROM market_rates WHERE curve = 'jp_call_on' "
        "AND obs_date <= ? AND obs_date >= ? ORDER BY obs_date DESC LIMIT 1",
        [day, first],
    ).fetchone()
    if row is not None:
        return float(row[0])
    row = con.execute(
        "SELECT yield_pct FROM market_rates WHERE curve = 'jp_call_on_mavg' AND obs_date = ?",
        [first],
    ).fetchone()
    return None if row is None else float(row[0])


def fit_month_ends(con: duckdb.DuckDBPyConnection, start: date, end: date) -> list[CurveFit]:
    """One fit per calendar month: the last day in the month that has JGB rows."""
    rows = con.execute(
        "SELECT obs_date, tenor_y, yield_pct FROM market_rates WHERE curve = 'jgb' "
        "AND obs_date BETWEEN ? AND ? ORDER BY obs_date, tenor_y",
        [start, end],
    ).fetchall()
    by_day: dict[date, list[tuple[float, float]]] = {}
    for obs_date, tenor, value in rows:
        by_day.setdefault(obs_date, []).append((tenor, value))
    month_end: dict[tuple[int, int], date] = {}
    for day in by_day:
        month_end[(day.year, day.month)] = day  # days arrive sorted, the last one wins
    fits: list[CurveFit] = []
    previous = None
    for day in sorted(month_end.values()):
        tenors, par = (np.array(v) for v in zip(*by_day[day], strict=True))
        fit = fit_svensson(tenors, par, overnight_at(con, day), previous, obs_date=day)
        fits.append(fit)
        previous = fit.params
    return fits


@dataclass(frozen=True)
class ZeroPanel:
    dates: tuple[date, ...]
    months: np.ndarray  # 1..M, contiguous
    yields: np.ndarray  # (T, M) continuously compounded annual %

    def __post_init__(self) -> None:
        if not np.array_equal(self.months, np.arange(1, len(self.months) + 1)):
            raise ValueError("ZeroPanel.months must be 1..M")
        if self.yields.shape != (len(self.dates), len(self.months)):
            raise ValueError("ZeroPanel.yields must be (len(dates), len(months))")

    def column(self, n: int) -> np.ndarray:
        return self.yields[:, n - 1]

    def columns(self, ns: np.ndarray) -> np.ndarray:
        return self.yields[:, np.asarray(ns) - 1]

    def window(self, start: date, end: date) -> ZeroPanel:
        keep = [i for i, d in enumerate(self.dates) if start <= d <= end]
        return ZeroPanel(tuple(self.dates[i] for i in keep), self.months, self.yields[keep])


def zero_panel(fits: Sequence[CurveFit], max_months: int = MAX_MONTHS) -> ZeroPanel:
    months = np.arange(1, max_months + 1)
    yields = np.vstack([svensson_zero(f.params, months / 12.0) for f in fits])
    return ZeroPanel(tuple(f.obs_date for f in fits), months, yields)


def month_ends(n: int, start_year: int = 2000) -> tuple[date, ...]:
    """Calendar month-ends for synthetic panels (n months from January ``start_year``)."""
    out = []
    for i in range(n):
        year, month = start_year + i // 12, i % 12 + 1
        out.append(date(year, month, calendar.monthrange(year, month)[1]))
    return tuple(out)
```

- [ ] **Step 4: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_curve.py -q`
Expected: PASS. If `test_fit_recovers_an_exact_svensson_curve` fails only on the zero-curve tolerance, print the max difference; the start grid contains the true (1.0, 10.0) taus, so a failure means a bug in `par_yields` or the residual, not the optimizer.

- [ ] **Step 5: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure macrokit/tests/test_curve.py && git commit -m "Fit Svensson curves to MoF par yields anchored by the call rate"
```

---

### Task 4: US validation files and `macrokit us-term`

**Files:**
- Create: `macrokit/src/macrokit/sources/us_term.py`
- Modify: `macrokit/src/macrokit/cli.py`
- Create: `macrokit/tests/fixtures/gsw_sample.csv`
- Test: `macrokit/tests/test_us_term.py`

**Interfaces:**
- Consumes: `termstructure.curve.svensson_zero`, `snapshot.save_snapshot`.
- Produces: `SOURCE = "us_term"`, `INDICATORS = {"gsw": url, "acm": url, "wuxia": url}`, `FILENAMES`; `GswDay(obs_date, params)`; `parse_gsw(content) -> list[GswDay]`; `gsw_zero(day, months) -> np.ndarray`; `parse_acm_rows(rows) -> dict[tuple[int, int], dict[str, float]]`; `parse_acm(content)`; `parse_wuxia(content) -> dict[tuple[int, int], float]`; `fetch(url) -> tuple[bytes, int]`.

- [ ] **Step 1: Write the fixture**

`$WT/macrokit/tests/fixtures/gsw_sample.csv` (structure verified 2026-10-17; the 2024-07-15 row is illustrative, the others are real):

```text
"Note: This is not an official Federal Reserve statistical release. Because this is a staff research product and not an official statistical release, it is subject to delay, revision, or methodological changes without advance notice."

Series,Compounding Convention,Mnemonic(s)
Zero-coupon yield,Continuously Compounded,SVENYXX
Par yield,Coupon-Equivalent,SVENPYXX
Instantaneous forward rate,Continuously Compounded,SVENFXX
One-year forward rate,Coupon-Equivalent,SVEN1FXX
Parameters,N/A,BETA0 to TAU2

Date,BETA0,BETA1,BETA2,BETA3,SVENY10,TAU1,TAU2
1961-06-30,4.03014932657583,-1.28678479652187,-1.9466741636327,0,NA,0.493864153178246,-999.99
1961-07-03,NA,NA,NA,NA,NA,NA,NA
2024-07-15,2.5,3.0,0.0,6.0,4.0,1.1,18.0
2024-07-31,2.51475012853092,3.00895987378684,-1.44656249632585e-05,6.28688390241322,4.078,1.14031042499237,17.9148552668668
2026-06-30,1.77427629201524e-10,4.06996715176281,-461.953317384163,472.557563149139,4.491,12.2529188743714,12.4384407166791
```

- [ ] **Step 2: Write the failing tests**

`$WT/macrokit/tests/test_us_term.py`:

```python
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from macrokit.sources import us_term

FIXTURES = Path(__file__).parent / "fixtures"


def _days():
    return us_term.parse_gsw((FIXTURES / "gsw_sample.csv").read_bytes())


def test_gsw_skips_na_rows_and_reproduces_the_published_10y():
    days = {d.obs_date: d for d in _days()}
    assert date(1961, 7, 3) not in days
    assert us_term.gsw_zero(days[date(2024, 7, 31)], np.array([120]))[0] == pytest.approx(
        4.078, abs=5e-4
    )
    assert us_term.gsw_zero(days[date(2026, 6, 30)], np.array([120]))[0] == pytest.approx(
        4.491, abs=5e-4
    )


def test_a_nelson_siegel_day_drops_the_second_hump():
    day = next(d for d in _days() if d.obs_date == date(1961, 6, 30))
    assert day.params[3] == 0.0 and day.params[5] == 1.0
    assert np.isfinite(us_term.gsw_zero(day, np.arange(1, 121))).all()


def test_month_ends_keep_the_last_day_of_each_month():
    ends = us_term.month_end_days(_days())
    assert [d.obs_date for d in ends] == [date(1961, 6, 30), date(2024, 7, 31), date(2026, 6, 30)]


def test_acm_rows_are_keyed_by_year_and_month():
    rows = [
        ["DATE", "ACMY10", "ACMTP10"],
        ["30-Jun-1961", 3.8675066636819664, -0.08],
        ["31-Jul-2024", 4.1, 0.2],
        ["", "", ""],
    ]
    parsed = us_term.parse_acm_rows(rows)
    assert parsed[(1961, 6)]["ACMY10"] == pytest.approx(3.8675066636819664)
    assert parsed[(2024, 7)]["ACMTP10"] == 0.2
    assert len(parsed) == 2


def test_acm_rows_refuse_an_unexpected_header():
    with pytest.raises(us_term.UsTermError, match="DATE"):
        us_term.parse_acm_rows([["Date", "ACMTP10"]])


def test_wuxia_reads_the_shadow_column_and_skips_blank_months():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Data"
    sheet.append([None, "Effective federal funds rate", "Wu-Xia shadow federal funds rate"])
    sheet.append([datetime(2008, 12, 1), 0.16, None])
    sheet.append([datetime(2009, 1, 1), 0.15, -0.5])
    sheet.append([datetime(2022, 2, 1), 0.08, 0.206380642030308])
    buffer = BytesIO()
    book.save(buffer)
    assert us_term.parse_wuxia(buffer.getvalue()) == {
        (2009, 1): -0.5,
        (2022, 2): pytest.approx(0.206380642030308),
    }
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_us_term.py -q`
Expected: FAIL with `ImportError: cannot import name 'us_term'`.

- [ ] **Step 4: Implement the source**

`$WT/macrokit/src/macrokit/sources/us_term.py`:

```python
"""US validation data for the JGB term-premium re-test (design 2026-10-17 §3.5).

Verified 2026-10-17:
- GSW zero curve (FRB): a text preamble, then a ``Date,BETA0,...`` header. ``NA``
  marks missing values; a Nelson-Siegel day has ``BETA3 = 0`` and ``TAU2 = -999.99``.
- NY Fed ACM term premia: legacy BIFF ``.xls`` (xlrd). Sheet ``ACM Monthly``,
  ``DATE`` as text such as ``30-Jun-1961``, columns ACMY01..10, ACMTP01..10, ACMRNY01..10.
- Wu-Xia shadow rate (Atlanta Fed): ``.xlsx`` (openpyxl). Sheet ``Data``; column A
  is the first of the month, column C the shadow rate. Updates stopped after 2022-02.

These files are stored as raw snapshots only; nothing here writes to DuckDB.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

import httpx
import numpy as np
import openpyxl
import xlrd

from ..termstructure.curve import svensson_zero

SOURCE = "us_term"
INDICATORS = {
    "gsw": "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv",
    "acm": "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls",
    "wuxia": (
        "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/datafiles/cqer/"
        "research/wu-xia-shadow-federal-funds-rate/WuXiaShadowRate.xlsx"
    ),
}
FILENAMES = {"gsw": "feds200628.csv", "acm": "ACMTermPremium.xls", "wuxia": "WuXiaShadowRate.xlsx"}
_MISSING = ("", "NA", None)
_PARAMS = ("BETA0", "BETA1", "BETA2", "BETA3", "TAU1", "TAU2")


class UsTermError(RuntimeError):
    """A US validation file could not be fetched or parsed."""


@dataclass(frozen=True)
class GswDay:
    obs_date: date
    params: tuple[float, float, float, float, float, float]  # beta0..beta3, tau1, tau2


def parse_gsw(content: bytes) -> list[GswDay]:
    lines = content.decode("utf-8", errors="replace").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    except StopIteration as exc:
        raise UsTermError("GSW payload has no 'Date,' header row") from exc
    days: list[GswDay] = []
    for row in csv.DictReader(lines[start:]):
        values = [row.get(name) for name in _PARAMS]
        if any(v in _MISSING for v in values[:5]):
            continue
        b0, b1, b2, b3, tau1 = (float(v) for v in values[:5])
        tau2 = -999.99 if values[5] in _MISSING else float(values[5])
        if b3 == 0.0 or tau2 <= 0:
            b3, tau2 = 0.0, 1.0  # Nelson-Siegel day: no second hump
        days.append(GswDay(date.fromisoformat(row["Date"]), (b0, b1, b2, b3, tau1, tau2)))
    return days


def month_end_days(days: Sequence[GswDay]) -> list[GswDay]:
    last: dict[tuple[int, int], GswDay] = {}
    for day in sorted(days, key=lambda d: d.obs_date):
        last[(day.obs_date.year, day.obs_date.month)] = day
    return [last[key] for key in sorted(last)]


def gsw_zero(day: GswDay, months: np.ndarray) -> np.ndarray:
    return svensson_zero(np.array(day.params), np.asarray(months, dtype=float) / 12.0)


def parse_acm_rows(rows: Sequence[Sequence]) -> dict[tuple[int, int], dict[str, float]]:
    header = [str(cell) for cell in rows[0]]
    if not header or header[0] != "DATE":
        raise UsTermError(f"ACM sheet header must start with DATE, got {header[:2]}")
    out: dict[tuple[int, int], dict[str, float]] = {}
    for row in rows[1:]:
        if not row or row[0] in _MISSING:
            continue
        day = datetime.strptime(str(row[0]), "%d-%b-%Y").date()
        out[(day.year, day.month)] = {
            name: float(value)
            for name, value in zip(header[1:], row[1:], strict=True)
            if value not in _MISSING
        }
    return out


def parse_acm(content: bytes) -> dict[tuple[int, int], dict[str, float]]:
    sheet = xlrd.open_workbook(file_contents=content).sheet_by_name("ACM Monthly")
    return parse_acm_rows([sheet.row_values(i) for i in range(sheet.nrows)])


def parse_wuxia(content: bytes) -> dict[tuple[int, int], float]:
    book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    out: dict[tuple[int, int], float] = {}
    for row in book["Data"].iter_rows(min_row=2, values_only=True):
        if not row or not isinstance(row[0], datetime) or row[2] is None:
            continue
        out[(row[0].year, row[0].month)] = float(row[2])
    return out


def fetch(url: str, *, timeout: float = 180.0) -> tuple[bytes, int]:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; macrokit research)"}
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(url)
    if response.status_code != 200:
        raise UsTermError(f"GET {url} returned {response.status_code}")
    return response.content, response.status_code
```

- [ ] **Step 5: Add the CLI command**

In `$WT/macrokit/src/macrokit/cli.py` add `from .sources import us_term` (sorted) and, after `callrate_command`:

```python
@main.command("us-term")
@click.pass_context
def us_term_command(ctx: click.Context) -> None:
    """Snapshot the US validation files (GSW curve, NY Fed ACM, Wu-Xia shadow rate)."""
    data_root: Path = ctx.obj["data_root"]
    now = datetime.now(UTC)
    for indicator, url in us_term.INDICATORS.items():
        content, status = us_term.fetch(url)
        result = save_snapshot(
            data_root / "raw",
            us_term.SOURCE,
            indicator,
            content,
            ingested_at=now,
            url=url,
            http_status=status,
            filename=us_term.FILENAMES[indicator],
        )
        click.echo(f"us-term {indicator}: {len(content)} bytes, {'stored' if result.changed else 'unchanged'}")
```

- [ ] **Step 6: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_us_term.py macrokit/tests/test_cli.py -q`
Expected: PASS (including the `us-term --help` case from Task 2).

- [ ] **Step 7: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/sources/us_term.py macrokit/src/macrokit/cli.py macrokit/tests/test_us_term.py macrokit/tests/fixtures/gsw_sample.csv && git commit -m "Snapshot the US curve, ACM and Wu-Xia files used to validate the models"
```

---

### Task 5: VAR helpers and the shared decomposition

**Files:**
- Create: `macrokit/src/macrokit/termstructure/var.py`
- Create: `macrokit/src/macrokit/termstructure/decompose.py`
- Test: `macrokit/tests/test_var.py`, `macrokit/tests/test_decompose.py`

**Interfaces:**
- Produces (`var.py`): `Var1(mu, phi, resid)` with `.sigma`; `fit_var1(x) -> Var1`; `fit_var1_batch(x: (B,T,K)) -> tuple[mu (B,K), phi (B,K,K)]`; `simulate_var1_batch(mu, phi, resid, x0, n_paths, rng) -> (n_paths, len(resid)+1, K)`; `expected_average(mu, phi, delta0, delta1, x, horizon) -> (..., T)`; `max_abs_eig(phi) -> float`.
- Produces (`decompose.py`): `GRID_MONTHS = np.arange(3, 121, 3)`; `Decomposition(model, dates, yield_pct, expected_pct)` with `.term_premium_pct`, `.share(t0, t1)`; `share_of(expected, yields, i0, i1)`; `month_end_in(dates, year, month) -> date`; `verdict(shares) -> str`; `VERDICT_BAND = (0.35, 0.65)`, `MIN_MODELS = 3`; `interval(samples, level=0.90) -> tuple[float, float]`; `largest_rise_window(y, length) -> tuple[int, int]`.

- [ ] **Step 1: Write the failing tests**

`$WT/macrokit/tests/test_var.py`:

```python
import numpy as np
import pytest

from macrokit.termstructure import var


def _ar_path(rng, n=4000):
    mu = np.array([0.1, -0.2])
    phi = np.array([[0.9, 0.05], [0.0, 0.7]])
    x = np.zeros((n, 2))
    for t in range(1, n):
        x[t] = mu + phi @ x[t - 1] + rng.normal(scale=0.1, size=2)
    return mu, phi, x


def test_fit_var1_recovers_a_long_path():
    mu, phi, x = _ar_path(np.random.default_rng(1))
    fit = var.fit_var1(x)
    np.testing.assert_allclose(fit.phi, phi, atol=0.03)
    np.testing.assert_allclose(fit.sigma, 0.01 * np.eye(2), atol=0.002)


def test_batch_fit_matches_one_at_a_time():
    rng = np.random.default_rng(2)
    paths = np.stack([_ar_path(rng, 300)[2] for _ in range(3)])
    mus, phis = var.fit_var1_batch(paths)
    for b in range(3):
        single = var.fit_var1(paths[b])
        np.testing.assert_allclose(mus[b], single.mu, atol=1e-10)
        np.testing.assert_allclose(phis[b], single.phi, atol=1e-10)


def test_simulation_starts_at_x0_and_is_reproducible():
    mu, phi, x = _ar_path(np.random.default_rng(3), 200)
    fit = var.fit_var1(x)
    a = var.simulate_var1_batch(fit.mu, fit.phi, fit.resid, x[0], 4, np.random.default_rng(9))
    b = var.simulate_var1_batch(fit.mu, fit.phi, fit.resid, x[0], 4, np.random.default_rng(9))
    assert a.shape == (4, 200, 2)
    np.testing.assert_array_equal(a, b)
    np.testing.assert_array_equal(a[:, 0], np.broadcast_to(x[0], (4, 2)))


def test_expected_average_matches_matrix_powers():
    mu = np.array([0.01, 0.02])
    phi = np.array([[0.95, 0.1], [0.0, 0.8]])
    d0, d1 = 0.5, np.array([1.0, 2.0])
    x = np.array([[0.3, -0.1], [0.0, 0.2]])
    horizon = 7
    expected = np.zeros(2)
    for t in range(2):
        state = x[t].copy()
        for _ in range(horizon):
            expected[t] += d0 + d1 @ state
            state = mu + phi @ state
    np.testing.assert_allclose(var.expected_average(mu, phi, d0, d1, x, horizon), expected / horizon)
    batch = var.expected_average(np.stack([mu, mu]), np.stack([phi, phi]), d0, d1, x, horizon)
    assert batch.shape == (2, 2)
    np.testing.assert_allclose(batch[1], expected / horizon)


def test_max_abs_eig():
    assert var.max_abs_eig(np.diag([0.5, -0.99])) == pytest.approx(0.99)
```

`$WT/macrokit/tests/test_decompose.py`:

```python
from datetime import date

import numpy as np
import pytest

from macrokit.termstructure import decompose as dc

DATES = (date(2024, 7, 31), date(2024, 8, 30), date(2026, 6, 30))


def test_share_and_term_premium():
    d = dc.Decomposition("acm", DATES, np.array([1.0, 1.2, 2.0]), np.array([0.5, 0.6, 1.0]))
    assert d.share(DATES[0], DATES[2]) == pytest.approx(0.5)
    np.testing.assert_allclose(d.term_premium_pct, [0.5, 0.6, 1.0])


def test_share_refuses_a_flat_window():
    d = dc.Decomposition("acm", DATES, np.array([1.0, 1.2, 1.0]), np.zeros(3))
    with pytest.raises(ValueError, match="flat"):
        d.share(DATES[0], DATES[2])


def test_share_of_handles_bootstrap_rows():
    expected = np.array([[0.0, 1.0], [0.0, 2.0]])
    np.testing.assert_allclose(dc.share_of(expected, np.array([0.0, 2.0]), 0, 1), [0.5, 1.0])


def test_month_end_in_finds_the_dated_month():
    assert dc.month_end_in(DATES, 2024, 8) == date(2024, 8, 30)
    with pytest.raises(KeyError):
        dc.month_end_in(DATES, 2025, 1)


@pytest.mark.parametrize(
    ("shares", "label"),
    [
        ({"a": 0.35, "b": 0.65, "c": 0.5, "d": 0.4}, "robust_half"),
        ({"a": 0.7, "b": 0.9, "c": 0.66}, "expectations_dominant"),
        ({"a": 0.1, "b": 0.34, "c": -0.2}, "term_premium_dominant"),
        ({"a": 0.5, "b": 0.9, "c": 0.4}, "model_dependent"),
        ({"a": 0.5, "b": 0.5}, "undetermined"),
    ],
)
def test_verdict_table(shares, label):
    assert dc.verdict(shares) == label


def test_interval_is_the_5_to_95_percentile():
    lo, hi = dc.interval(np.arange(101.0))
    assert (lo, hi) == (5.0, 95.0)


def test_largest_rise_window():
    y = np.array([0.0, 1.0, 0.5, 3.0, 2.0])
    assert dc.largest_rise_window(y, 2) == (1, 3)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_var.py macrokit/tests/test_decompose.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

`$WT/macrokit/src/macrokit/termstructure/var.py`:

```python
"""VAR(1) estimation, residual bootstrap, and expected short-rate averages."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Var1:
    mu: np.ndarray  # (K,)
    phi: np.ndarray  # (K, K)
    resid: np.ndarray  # (T-1, K), mean zero because of the intercept

    @property
    def sigma(self) -> np.ndarray:
        return self.resid.T @ self.resid / len(self.resid)


def fit_var1(x: np.ndarray) -> Var1:
    """OLS of x_{t+1} = mu + phi x_t + v_{t+1}."""
    z = np.column_stack([np.ones(len(x) - 1), x[:-1]])
    coef, *_ = np.linalg.lstsq(z, x[1:], rcond=None)
    return Var1(mu=coef[0], phi=coef[1:].T, resid=x[1:] - z @ coef)


def fit_var1_batch(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """OLS VAR(1) for every path of a (B, T, K) array: mu (B, K), phi (B, K, K)."""
    lagged, lead = x[:, :-1], x[:, 1:]
    z = np.concatenate([np.ones((*lagged.shape[:2], 1)), lagged], axis=2)
    zz = np.einsum("btj,btk->bjk", z, z)
    zy = np.einsum("btj,btk->bjk", z, lead)
    coef = np.linalg.solve(zz, zy)
    return coef[:, 0], np.swapaxes(coef[:, 1:], 1, 2)


def simulate_var1_batch(
    mu: np.ndarray,
    phi: np.ndarray,
    resid: np.ndarray,
    x0: np.ndarray,
    n_paths: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Residual-bootstrap paths of length len(resid) + 1 starting at x0: (n_paths, T, K)."""
    steps = len(resid)
    draws = resid[rng.integers(0, steps, size=(n_paths, steps))]
    out = np.empty((n_paths, steps + 1, len(x0)))
    out[:, 0] = x0
    for t in range(1, steps + 1):
        out[:, t] = mu + out[:, t - 1] @ phi.T + draws[:, t - 1]
    return out


def expected_average(
    mu: np.ndarray,
    phi: np.ndarray,
    delta0: float,
    delta1: np.ndarray,
    x: np.ndarray,
    horizon: int,
) -> np.ndarray:
    """Mean over h = 0..horizon-1 of delta0 + delta1 . E_t[x_{t+h}] under x' = mu + phi x.

    ``mu`` (..., K) and ``phi`` (..., K, K) may carry a leading batch axis; ``x`` is
    the (T, K) history. Returns (..., T) in the units of ``delta0``.
    """
    mu = np.asarray(mu)
    phi = np.asarray(phi)
    state = np.broadcast_to(x, mu.shape[:-1] + x.shape).copy()
    total = np.zeros(state.shape[:-1])
    phi_t = np.swapaxes(phi, -1, -2)
    for _ in range(horizon):
        total += delta0 + state @ delta1
        state = mu[..., None, :] + state @ phi_t
    return total / horizon


def max_abs_eig(phi: np.ndarray) -> float:
    return float(np.abs(np.linalg.eigvals(phi)).max())
```

`$WT/macrokit/src/macrokit/termstructure/decompose.py`:

```python
"""The shared result type, the share s, and the pre-registered verdict (design §2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

GRID_MONTHS = np.arange(3, 121, 3)
VERDICT_BAND = (0.35, 0.65)
MIN_MODELS = 3


@dataclass(frozen=True)
class Decomposition:
    model: str
    dates: tuple[date, ...]
    yield_pct: np.ndarray  # observed zero yield from the fitted curve, common to all models
    expected_pct: np.ndarray  # average expected one-month rate over the maturity

    def __post_init__(self) -> None:
        if not len(self.dates) == len(self.yield_pct) == len(self.expected_pct):
            raise ValueError("Decomposition arrays must match the dates")

    @property
    def term_premium_pct(self) -> np.ndarray:
        return self.yield_pct - self.expected_pct

    def share(self, t0: date, t1: date) -> float:
        i0, i1 = self.dates.index(t0), self.dates.index(t1)
        return float(share_of(self.expected_pct, self.yield_pct, i0, i1))


def share_of(expected: np.ndarray, yields: np.ndarray, i0: int, i1: int) -> np.ndarray:
    """(E[i1] - E[i0]) / (Y[i1] - Y[i0]); ``expected`` may have leading bootstrap rows."""
    dy = yields[i1] - yields[i0]
    if abs(dy) < 1e-8:
        raise ValueError("the window is flat: the yield did not change, so s is undefined")
    return (expected[..., i1] - expected[..., i0]) / dy


def month_end_in(dates: Sequence[date], year: int, month: int) -> date:
    for day in dates:
        if (day.year, day.month) == (year, month):
            return day
    raise KeyError(f"no date in {year}-{month:02d}")


def verdict(shares: Mapping[str, float]) -> str:
    """Design §2.3: robust only if every gate-passing model lies inside the band."""
    if len(shares) < MIN_MODELS:
        return "undetermined"
    lower, upper = VERDICT_BAND
    values = list(shares.values())
    if all(lower <= s <= upper for s in values):
        return "robust_half"
    if all(s > upper for s in values):
        return "expectations_dominant"
    if all(s < lower for s in values):
        return "term_premium_dominant"
    return "model_dependent"


def interval(samples: np.ndarray, level: float = 0.90) -> tuple[float, float]:
    tail = (1 - level) / 2 * 100
    lo, hi = np.percentile(samples, [tail, 100 - tail])
    return float(lo), float(hi)


def largest_rise_window(y: np.ndarray, length: int) -> tuple[int, int]:
    """(i, i + length) maximizing y[i + length] - y[i]."""
    rises = y[length:] - y[:-length]
    start = int(np.argmax(rises))
    return start, start + length
```

- [ ] **Step 4: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_var.py macrokit/tests/test_decompose.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure/var.py macrokit/src/macrokit/termstructure/decompose.py macrokit/tests/test_var.py macrokit/tests/test_decompose.py && git commit -m "Add the VAR helpers and the pre-registered verdict"
```

---

### Task 6: ACM model and the affine synthetic curve

**Files:**
- Create: `macrokit/src/macrokit/termstructure/acm.py`
- Create: `macrokit/src/macrokit/termstructure/synthetic.py`
- Test: `macrokit/tests/test_acm.py`

**Interfaces:**
- Consumes: `ZeroPanel`, `month_ends` (curve); `Var1`, `fit_var1`, `expected_average` (var); `Decomposition`, `GRID_MONTHS` (decompose).
- Produces (`acm.py`): `FACTOR_MONTHS`, `RETURN_MONTHS`, `LONG_FACTOR_MONTHS`, `LONG_RETURN_MONTHS`; `pricing_recursion(mu, phi, sigma, sigma2, delta0, delta1, n_max) -> tuple[a (n_max+1,), b (n_max+1, K)]`; `AcmFit(dates, factors, var, lambda0, lambda1, delta0, delta1, sigma2)` with `.fitted_yield(n, risk_neutral=False)` and `.expected(horizon, mu=None, phi=None)`; `fit_acm(panel, k=5, factor_months=FACTOR_MONTHS, return_months=RETURN_MONTHS) -> AcmFit`; `decompose_acm(panel, fit, maturity=120, mu=None, phi=None, model="acm") -> Decomposition`.
- Produces (`synthetic.py`): `AffineParams(mu, phi, chol, lambda0, lambda1, delta0, delta1, sigma2=0.0)` with `.from_fit(fit)`; `SyntheticCurve(panel, expected_pct, short_pct)`; `simulate_affine(params, n_months, rng, *, max_months=120, noise_pct=0.02, burn_in=500, horizon=120) -> SyntheticCurve`; `AFFINE_TRUE`; `affine_dgp(n_months, rng) -> SyntheticCurve`.

- [ ] **Step 1: Write the failing tests**

`$WT/macrokit/tests/test_acm.py`:

```python
import numpy as np
import pytest

from macrokit.termstructure import acm, synthetic


def test_pricing_recursion_matches_monte_carlo():
    rng = np.random.default_rng(5)
    mu = np.array([0.0001, 0.0])
    phi = np.array([[0.97, 0.02], [0.0, 0.9]])
    chol = np.diag([0.0005, 0.0004])
    d0, d1 = 0.002, np.array([1.0, 1.0])
    x0 = np.array([0.001, -0.0005])
    a, b = acm.pricing_recursion(mu, phi, chol @ chol.T, 0.0, d0, d1, 12)
    paths = 200_000
    x = np.broadcast_to(x0, (paths, 2)).copy()
    discount = np.zeros(paths)
    for _ in range(12):
        discount += d0 + x @ d1
        x = mu + x @ phi.T + rng.standard_normal((paths, 2)) @ chol.T
    mc = np.log(np.exp(-discount).mean())
    assert a[12] + b[12] @ x0 == pytest.approx(mc, abs=2e-4)  # ~5 Monte Carlo standard errors


def test_without_risk_prices_the_premium_is_a_constant_convexity_term():
    syn = synthetic.affine_dgp(600, np.random.default_rng(6))
    fit = acm.fit_acm(syn.panel, k=3)
    neutral = acm.AcmFit(
        fit.dates, fit.factors, fit.var, np.zeros(3), np.zeros((3, 3)),
        fit.delta0, fit.delta1, fit.sigma2,
    )
    np.testing.assert_allclose(neutral.fitted_yield(120), neutral.fitted_yield(120, risk_neutral=True))
    gap = neutral.fitted_yield(120, risk_neutral=True) - neutral.expected(120)
    assert gap.std() < 1e-10


def test_acm_recovers_the_affine_curve_on_a_long_sample():
    syn = synthetic.affine_dgp(5000, np.random.default_rng(7))
    fit = acm.fit_acm(syn.panel, k=3)
    assert np.abs(fit.fitted_yield(120) - syn.panel.column(120)).mean() < 0.03
    rmse = np.sqrt(((fit.expected(120) - syn.expected_pct) ** 2).mean())
    assert rmse < 0.2


def test_decompose_uses_the_observed_yield():
    syn = synthetic.affine_dgp(600, np.random.default_rng(8))
    fit = acm.fit_acm(syn.panel, k=3)
    dec = acm.decompose_acm(syn.panel, fit)
    np.testing.assert_array_equal(dec.yield_pct, syn.panel.column(120))
    assert dec.model == "acm"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_acm.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `acm.py`**

`$WT/macrokit/src/macrokit/termstructure/acm.py`:

```python
"""Adrian, Crump and Moench (2013) term structure by linear regression (design §4.1).

Log prices ln P^(n) = A_n + B_n' X_t with monthly periods and the one-month rate
r_t = y^(1)/1200. Validated against the NY Fed series on US data (gate G2; the
2026-10-17 prototype reproduced it with correlation 0.99985).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .curve import ZeroPanel
from .decompose import GRID_MONTHS, Decomposition
from .var import Var1, expected_average, fit_var1

FACTOR_MONTHS = GRID_MONTHS
RETURN_MONTHS = np.array([6, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120])
LONG_FACTOR_MONTHS = np.arange(3, 361, 3)
LONG_RETURN_MONTHS = np.concatenate([RETURN_MONTHS, [180, 240, 300, 360]])


def pricing_recursion(
    mu: np.ndarray,
    phi: np.ndarray,
    sigma: np.ndarray,
    sigma2: float,
    delta0: float,
    delta1: np.ndarray,
    n_max: int,
) -> tuple[np.ndarray, np.ndarray]:
    """ACM eq. (11) with (mu, phi) the pricing drift: risk-neutral uses mu - lambda0, phi - lambda1."""
    k = len(mu)
    a = np.zeros(n_max + 1)
    b = np.zeros((n_max + 1, k))
    for n in range(1, n_max + 1):
        a[n] = a[n - 1] + b[n - 1] @ mu + 0.5 * (b[n - 1] @ sigma @ b[n - 1] + sigma2) - delta0
        b[n] = b[n - 1] @ phi - delta1
    return a, b


@dataclass(frozen=True)
class AcmFit:
    dates: tuple[date, ...]
    factors: np.ndarray  # (T, K) principal components of the yields
    var: Var1
    lambda0: np.ndarray
    lambda1: np.ndarray
    delta0: float
    delta1: np.ndarray
    sigma2: float

    def fitted_yield(self, n: int, risk_neutral: bool = False) -> np.ndarray:
        """Model yield (annual %). ``risk_neutral=True`` prices with zero risk prices (P drift)."""
        mu, phi = self.var.mu, self.var.phi
        if not risk_neutral:
            mu, phi = mu - self.lambda0, phi - self.lambda1
        a, b = pricing_recursion(mu, phi, self.var.sigma, self.sigma2, self.delta0, self.delta1, n)
        return -1200.0 / n * (a[n] + self.factors @ b[n])

    def expected(
        self, horizon: int, mu: np.ndarray | None = None, phi: np.ndarray | None = None
    ) -> np.ndarray:
        """Design §2.1 E_t (annual %): mean expected one-month rate, optionally with other P dynamics."""
        mu = self.var.mu if mu is None else mu
        phi = self.var.phi if phi is None else phi
        return 1200.0 * expected_average(mu, phi, self.delta0, self.delta1, self.factors, horizon)


def fit_acm(
    panel: ZeroPanel,
    k: int = 5,
    factor_months: np.ndarray = FACTOR_MONTHS,
    return_months: np.ndarray = RETURN_MONTHS,
) -> AcmFit:
    log_price = -(panel.months / 12.0) * panel.yields / 100.0
    short = panel.column(1) / 1200.0
    selected = panel.columns(factor_months)
    centered = selected - selected.mean(axis=0)
    _, vectors = np.linalg.eigh(np.cov(centered.T))
    factors = centered @ vectors[:, ::-1][:, :k]
    var = fit_var1(factors)
    steps = len(factors) - 1
    excess = np.column_stack(
        [log_price[1:, n - 2] - log_price[:-1, n - 1] - short[:-1] for n in return_months]
    )
    z = np.column_stack([np.ones(steps), var.resid, factors[:-1]])
    coef, *_ = np.linalg.lstsq(z, excess, rcond=None)
    a, beta, c = coef[0], coef[1 : 1 + k], coef[1 + k :].T
    errors = excess - z @ coef
    sigma2 = float((errors**2).sum() / errors.size)
    b_star = np.array([np.outer(beta[:, i], beta[:, i]).ravel() for i in range(beta.shape[1])])
    bb = beta @ beta.T
    lambda1 = np.linalg.solve(bb, beta @ c)
    lambda0 = np.linalg.solve(bb, beta @ (a + 0.5 * (b_star @ var.sigma.ravel() + sigma2)))
    zs = np.column_stack([np.ones(len(factors)), factors])
    d, *_ = np.linalg.lstsq(zs, short, rcond=None)
    return AcmFit(panel.dates, factors, var, lambda0, lambda1, float(d[0]), d[1:], sigma2)


def decompose_acm(
    panel: ZeroPanel,
    fit: AcmFit,
    maturity: int = 120,
    mu: np.ndarray | None = None,
    phi: np.ndarray | None = None,
    model: str = "acm",
) -> Decomposition:
    return Decomposition(model, panel.dates, panel.column(maturity), fit.expected(maturity, mu, phi))
```

- [ ] **Step 4: Implement `synthetic.py` (affine part)**

`$WT/macrokit/src/macrokit/termstructure/synthetic.py`:

```python
"""Known data-generating processes for gate G1 and the small-sample study (design §5).

Parameters are fixed constants here; none is calibrated to Japanese data.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .acm import AcmFit, pricing_recursion
from .curve import ZeroPanel, month_ends
from .var import expected_average


@dataclass(frozen=True)
class AffineParams:
    """Gaussian affine model: x' = mu + phi x + chol e, r = delta0 + delta1'x (decimal per month)."""

    mu: np.ndarray
    phi: np.ndarray
    chol: np.ndarray
    lambda0: np.ndarray
    lambda1: np.ndarray
    delta0: float
    delta1: np.ndarray
    sigma2: float = 0.0

    @classmethod
    def from_fit(cls, fit: AcmFit) -> AffineParams:
        return cls(
            fit.var.mu, fit.var.phi, np.linalg.cholesky(fit.var.sigma), fit.lambda0,
            fit.lambda1, fit.delta0, fit.delta1, fit.sigma2,
        )


@dataclass(frozen=True)
class SyntheticCurve:
    panel: ZeroPanel
    expected_pct: np.ndarray  # true design-§2.1 E_t for the 120-month horizon
    short_pct: np.ndarray  # true one-month rate (annual %), the bracket-2 expectation


def simulate_affine(
    params: AffineParams,
    n_months: int,
    rng: np.random.Generator,
    *,
    max_months: int = 120,
    noise_pct: float = 0.02,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticCurve:
    k = len(params.mu)
    x = np.linalg.solve(np.eye(k) - params.phi, params.mu)
    shocks = rng.standard_normal((burn_in + n_months, k)) @ params.chol.T
    path = np.empty((n_months, k))
    for t in range(burn_in + n_months):
        x = params.mu + params.phi @ x + shocks[t]
        if t >= burn_in:
            path[t - burn_in] = x
    a, b = pricing_recursion(
        params.mu - params.lambda0,
        params.phi - params.lambda1,
        params.chol @ params.chol.T,
        params.sigma2,
        params.delta0,
        params.delta1,
        max_months,
    )
    months = np.arange(1, max_months + 1)
    yields = -1200.0 / months * (a[1:] + path @ b[1:].T)
    yields = yields + noise_pct * rng.standard_normal(yields.shape)
    expected = 1200.0 * expected_average(
        params.mu, params.phi, params.delta0, params.delta1, path, horizon
    )
    short = 1200.0 * (params.delta0 + path @ params.delta1)
    return SyntheticCurve(ZeroPanel(month_ends(n_months), months, yields), expected, short)


_PHI = np.diag([0.99, 0.95, 0.90])
_PHI_Q = np.diag([0.995, 0.93, 0.85])
AFFINE_TRUE = AffineParams(
    mu=np.zeros(3),
    phi=_PHI,
    chol=np.diag([0.25, 0.15, 0.10]) / 1200.0,
    lambda0=-np.array([0.5 * (1 - 0.995), 0.0, 0.0]) / 1200.0,
    lambda1=_PHI - _PHI_Q,
    delta0=2.0 / 1200.0,
    delta1=np.ones(3),
)


def affine_dgp(n_months: int, rng: np.random.Generator) -> SyntheticCurve:
    return simulate_affine(AFFINE_TRUE, n_months, rng)
```

- [ ] **Step 5: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_acm.py -q`
Expected: PASS. If the Monte Carlo test misses, print both numbers: a sign error in `b[n-1] @ mu` or the `0.5 * (...)` term shows up as an error proportional to n.

- [ ] **Step 6: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure/acm.py macrokit/src/macrokit/termstructure/synthetic.py macrokit/tests/test_acm.py && git commit -m "Implement the ACM regression model and an affine synthetic curve"
```

---

### Task 7: Kilian bias correction and ACM bootstrap intervals

**Files:**
- Modify: `macrokit/src/macrokit/termstructure/acm.py`
- Test: `macrokit/tests/test_acm.py`

**Interfaces:**
- Consumes: `Var1`, `fit_var1`, `fit_var1_batch`, `simulate_var1_batch`, `expected_average`, `max_abs_eig`.
- Produces: `BiasCorrected(mu, phi, shrink)`; `shrink_to_stationary(phi, bias) -> tuple[np.ndarray, float]`; `kilian_correct(x, var, n_boot, rng, max_floats=5_000_000) -> BiasCorrected`; `bootstrap_expected(fit, horizon, n_boot, rng, correction_boot=0) -> np.ndarray (n_boot, T)`.

- [ ] **Step 1: Write the failing tests**

Append to `$WT/macrokit/tests/test_acm.py`:

```python
from macrokit.termstructure import var


def test_kilian_moves_an_ar1_estimate_toward_the_truth():
    rng = np.random.default_rng(11)
    raw, corrected = [], []
    for _ in range(100):
        x = np.zeros((200, 1))
        for t in range(1, 200):
            x[t] = 0.98 * x[t - 1] + rng.normal()
        fit = var.fit_var1(x)
        raw.append(fit.phi[0, 0])
        corrected.append(acm.kilian_correct(x, fit, 300, rng).phi[0, 0])
    assert abs(np.mean(corrected) - 0.98) < 0.5 * abs(np.mean(raw) - 0.98)


def test_shrink_stops_at_the_first_stationary_step():
    phi, shrink = acm.shrink_to_stationary(np.array([[0.99]]), np.array([[-0.045]]))
    assert shrink == pytest.approx(0.22)
    assert phi[0, 0] < 1.0


def test_kilian_leaves_a_non_stationary_estimate_alone():
    x = np.cumsum(np.ones((50, 1)), axis=0)
    fit = var.Var1(mu=np.array([1.0]), phi=np.array([[1.01]]), resid=np.zeros((49, 1)))
    out = acm.kilian_correct(x, fit, 10, np.random.default_rng(0))
    assert out.shrink == 0.0
    np.testing.assert_array_equal(out.phi, fit.phi)


def test_bootstrap_expected_is_centred_on_the_point_estimate():
    syn = synthetic.affine_dgp(400, np.random.default_rng(12))
    fit = acm.fit_acm(syn.panel, k=3)
    draws = acm.bootstrap_expected(fit, 120, 200, np.random.default_rng(13))
    assert draws.shape == (200, 400)
    assert abs(np.median(draws[:, -1]) - fit.expected(120)[-1]) < 0.5
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_acm.py -q -k "kilian or shrink or bootstrap"`
Expected: FAIL with `AttributeError: module ... has no attribute 'kilian_correct'`.

- [ ] **Step 3: Implement**

Add to the imports of `acm.py`: `from .var import Var1, expected_average, fit_var1, fit_var1_batch, max_abs_eig, simulate_var1_batch`. Append:

```python
@dataclass(frozen=True)
class BiasCorrected:
    mu: np.ndarray
    phi: np.ndarray
    shrink: float  # share of the estimated bias removed (1 = all, 0 = none)


def shrink_to_stationary(phi: np.ndarray, bias: np.ndarray) -> tuple[np.ndarray, float]:
    """Kilian (1998): remove the bias, shrinking it in 0.01 steps until stationary."""
    for step in range(100, -1, -1):
        shrink = step / 100.0
        corrected = phi - shrink * bias
        if max_abs_eig(corrected) < 1.0:
            return corrected, shrink
    return phi, 0.0


def kilian_correct(
    x: np.ndarray,
    var: Var1,
    n_boot: int,
    rng: np.random.Generator,
    max_floats: int = 5_000_000,
) -> BiasCorrected:
    """Bootstrap bias correction of phi; mu keeps the sample mean (design §4.2)."""
    if max_abs_eig(var.phi) >= 1.0:
        return BiasCorrected(var.mu, var.phi, 0.0)
    chunk = max(1, max_floats // (len(x) * x.shape[1]))
    total = np.zeros_like(var.phi)
    done = 0
    while done < n_boot:
        size = min(chunk, n_boot - done)
        paths = simulate_var1_batch(var.mu, var.phi, var.resid, x[0], size, rng)
        total += fit_var1_batch(paths)[1].sum(axis=0)
        done += size
    bias = total / n_boot - var.phi
    phi, shrink = shrink_to_stationary(var.phi, bias)
    mu = (np.eye(len(var.mu)) - phi) @ x.mean(axis=0)
    return BiasCorrected(mu, phi, shrink)


def bootstrap_expected(
    fit: AcmFit,
    horizon: int,
    n_boot: int,
    rng: np.random.Generator,
    correction_boot: int = 0,
) -> np.ndarray:
    """E_t (annual %) under re-estimated P dynamics, Q held fixed (design §4.1–4.2).

    Residual-bootstrap factor paths, re-estimate (mu, phi), recompute E on the
    actual factor history. With ``correction_boot`` the bootstrap DGP is the
    bias-corrected VAR and every re-estimate is bias-corrected again.
    """
    if correction_boot:
        dgp = kilian_correct(fit.factors, fit.var, correction_boot, rng)
        dgp_mu, dgp_phi = dgp.mu, dgp.phi
    else:
        dgp_mu, dgp_phi = fit.var.mu, fit.var.phi
    paths = simulate_var1_batch(dgp_mu, dgp_phi, fit.var.resid, fit.factors[0], n_boot, rng)
    mus, phis = fit_var1_batch(paths)
    if correction_boot:
        for b in range(n_boot):
            corrected = kilian_correct(paths[b], fit_var1(paths[b]), correction_boot, rng)
            mus[b], phis[b] = corrected.mu, corrected.phi
    return 1200.0 * expected_average(mus, phis, fit.delta0, fit.delta1, fit.factors, horizon)
```

- [ ] **Step 4: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_acm.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure/acm.py macrokit/tests/test_acm.py && git commit -m "Add Kilian bias correction and bootstrap intervals to ACM"
```

---

### Task 8: DNS-VAR and its synthetic curve

**Files:**
- Create: `macrokit/src/macrokit/termstructure/dns.py`
- Modify: `macrokit/src/macrokit/termstructure/synthetic.py`
- Test: `macrokit/tests/test_dns.py`

**Interfaces:**
- Consumes: `ZeroPanel`, `GRID_MONTHS`, `Decomposition`, `Var1`, `fit_var1`, `fit_var1_batch`, `simulate_var1_batch`, `expected_average`, `SyntheticCurve`, `month_ends`.
- Produces: `LAMBDA = 0.0609`; `ns_loadings(months, lam=LAMBDA) -> (M, 3)`; `DnsFit(dates, factors, var, lam)` with `.short_loading` and `.expected(horizon, mu=None, phi=None)`; `fit_dns(panel, lam=LAMBDA, months=GRID_MONTHS) -> DnsFit`; `decompose_dns(panel, fit, maturity=120) -> Decomposition`; `bootstrap_expected_dns(fit, horizon, n_boot, rng) -> (n_boot, T)`; `synthetic.dns_dgp(n_months, rng) -> SyntheticCurve`.

- [ ] **Step 1: Write the failing tests**

`$WT/macrokit/tests/test_dns.py`:

```python
import numpy as np

from macrokit.termstructure import dns, synthetic


def test_loadings_at_the_short_and_long_end():
    load = dns.ns_loadings(np.array([1e-6, 1e6]))
    np.testing.assert_allclose(load[0], [1.0, 1.0, 0.0], atol=1e-5)
    np.testing.assert_allclose(load[1], [1.0, 0.0, 0.0], atol=1e-4)


def test_dns_recovers_its_own_curve():
    syn = synthetic.dns_dgp(5000, np.random.default_rng(21))
    fit = dns.fit_dns(syn.panel)
    rmse = np.sqrt(((fit.expected(120) - syn.expected_pct) ** 2).mean())
    assert rmse < 0.1


def test_bootstrap_shape_and_centre():
    syn = synthetic.dns_dgp(400, np.random.default_rng(22))
    fit = dns.fit_dns(syn.panel)
    draws = dns.bootstrap_expected_dns(fit, 120, 100, np.random.default_rng(23))
    assert draws.shape == (100, 400)
    assert abs(np.median(draws[:, -1]) - fit.expected(120)[-1]) < 0.5


def test_decompose_labels_the_model():
    syn = synthetic.dns_dgp(300, np.random.default_rng(24))
    dec = dns.decompose_dns(syn.panel, dns.fit_dns(syn.panel), maturity=60)
    assert dec.model == "dns"
    np.testing.assert_array_equal(dec.yield_pct, syn.panel.column(60))
    assert dec.expected_pct.shape == (300,)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_dns.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement `dns.py`**

`$WT/macrokit/src/macrokit/termstructure/dns.py`:

```python
"""Diebold-Li dynamic Nelson-Siegel with a VAR(1) on the factors (design §4.4).

Not arbitrage-free; it is the baseline. Factors are in annual %.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np

from .curve import ZeroPanel
from .decompose import GRID_MONTHS, Decomposition
from .var import Var1, expected_average, fit_var1, fit_var1_batch, simulate_var1_batch

LAMBDA = 0.0609  # per month, Diebold and Li (2006)


def ns_loadings(months: np.ndarray, lam: float = LAMBDA) -> np.ndarray:
    m = np.asarray(months, dtype=float)
    x = lam * m
    slope = -np.expm1(-x) / x
    return np.column_stack([np.ones_like(m), slope, slope - np.exp(-x)])


@dataclass(frozen=True)
class DnsFit:
    dates: tuple[date, ...]
    factors: np.ndarray  # (T, 3) level, slope, curvature
    var: Var1
    lam: float

    @property
    def short_loading(self) -> np.ndarray:
        return ns_loadings(np.array([1.0]), self.lam)[0]

    def expected(
        self, horizon: int, mu: np.ndarray | None = None, phi: np.ndarray | None = None
    ) -> np.ndarray:
        mu = self.var.mu if mu is None else mu
        phi = self.var.phi if phi is None else phi
        return expected_average(mu, phi, 0.0, self.short_loading, self.factors, horizon)


def fit_dns(panel: ZeroPanel, lam: float = LAMBDA, months: np.ndarray = GRID_MONTHS) -> DnsFit:
    load = ns_loadings(months, lam)
    factors = np.linalg.lstsq(load, panel.columns(months).T, rcond=None)[0].T
    return DnsFit(panel.dates, factors, fit_var1(factors), lam)


def decompose_dns(panel: ZeroPanel, fit: DnsFit, maturity: int = 120) -> Decomposition:
    return Decomposition("dns", panel.dates, panel.column(maturity), fit.expected(maturity))


def bootstrap_expected_dns(
    fit: DnsFit, horizon: int, n_boot: int, rng: np.random.Generator
) -> np.ndarray:
    paths = simulate_var1_batch(fit.var.mu, fit.var.phi, fit.var.resid, fit.factors[0], n_boot, rng)
    mus, phis = fit_var1_batch(paths)
    return expected_average(mus, phis, 0.0, fit.short_loading, fit.factors, horizon)
```

- [ ] **Step 4: Append the DNS generator to `synthetic.py`**

Add `from .dns import ns_loadings` to the imports and append:

```python
DNS_MEAN = np.array([4.0, -2.0, 0.0])
DNS_PHI = np.diag([0.99, 0.95, 0.90])
DNS_SHOCK = np.array([0.25, 0.30, 0.50])


def dns_dgp(
    n_months: int,
    rng: np.random.Generator,
    *,
    max_months: int = 120,
    noise_pct: float = 0.02,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticCurve:
    mu = (np.eye(3) - DNS_PHI) @ DNS_MEAN
    f = DNS_MEAN.copy()
    path = np.empty((n_months, 3))
    shocks = rng.standard_normal((burn_in + n_months, 3)) * DNS_SHOCK
    for t in range(burn_in + n_months):
        f = mu + DNS_PHI @ f + shocks[t]
        if t >= burn_in:
            path[t - burn_in] = f
    months = np.arange(1, max_months + 1)
    yields = path @ ns_loadings(months).T + noise_pct * rng.standard_normal((n_months, max_months))
    short_loading = ns_loadings(np.array([1.0]))[0]
    expected = expected_average(mu, DNS_PHI, 0.0, short_loading, path, horizon)
    return SyntheticCurve(
        ZeroPanel(month_ends(n_months), months, yields), expected, path @ short_loading
    )
```

- [ ] **Step 5: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_dns.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure/dns.py macrokit/src/macrokit/termstructure/synthetic.py macrokit/tests/test_dns.py && git commit -m "Add the DNS-VAR baseline and its synthetic curve"
```

---

### Task 9: Shadow-rate model core (forwards, batched EKF, expectations)

**Files:**
- Create: `macrokit/src/macrokit/termstructure/shadow.py`
- Test: `macrokit/tests/test_shadow.py`

**Interfaces:**
- Consumes: `ZeroPanel`; `acm.pricing_recursion` (test only); `var.expected_average`.
- Produces: `FORWARD_MONTHS`, `N_PARAMS = 23`, `PENALTY`; `ShadowParams` (batched fields `rho_q (B,3)`, `delta0 (B,)`, `sigma (B,3,3)`, `mu (B,3)`, `rho (B,3,3)`, `omega (B,)`); `pack(rho_q, delta0, sigma, mu, rho, omega) -> (23,)`; `unpack(theta) -> ShadowParams`; `forward_loadings(params, months) -> tuple[a (B,M), b (B,M,3), sd (B,M)]`; `shadow_forwards(theta, states, r_lower, months) -> (T, M)`; `loglik(theta, forwards, r_lower, months=FORWARD_MONTHS, return_states=False)`; `filtered_states(theta, forwards, r_lower) -> (T, 3)`; `shadow_rate(theta, states) -> (T,)`; `expected_short_average(theta, states, r_lower, horizon) -> (T,) or (B, T)`; `expected_gaussian_average(theta, states, horizon) -> (T,)`; `panel_forwards(panel, months=FORWARD_MONTHS) -> (T, M)`.

- [ ] **Step 1: Write the failing tests**

`$WT/macrokit/tests/test_shadow.py`:

```python
import numpy as np
import pytest

from macrokit.termstructure import acm, shadow

THETA = shadow.pack(
    rho_q=(0.997, 0.95, 0.8),
    delta0=1.0,
    sigma=np.array([[0.15, 0.0, 0.0], [0.05, 0.2, 0.0], [0.0, -0.05, 0.25]]),
    mu=np.zeros(3),
    rho=np.diag([0.99, 0.94, 0.8]),
    omega=0.05,
)


def test_pack_and_unpack_round_trip():
    p = shadow.unpack(THETA)
    np.testing.assert_allclose(p.rho_q[0], [0.997, 0.95, 0.8])
    np.testing.assert_allclose(p.sigma[0, 1, 0], 0.05)
    np.testing.assert_allclose(p.omega, [0.05])
    np.testing.assert_allclose(shadow.pack(p.rho_q[0], p.delta0[0], p.sigma[0], p.mu[0], p.rho[0], p.omega[0]), THETA)


def test_far_from_the_bound_forwards_are_the_gaussian_affine_forwards():
    p = shadow.unpack(THETA)
    x = np.array([[0.4, -0.3, 0.2]])
    months = np.array([3, 24, 120])
    approx = shadow.shadow_forwards(THETA, x, -100.0, months)[0]
    # Independent check: price the shadow bond with the ACM recursion in decimal per month.
    a, b = acm.pricing_recursion(
        np.zeros(3), np.diag(p.rho_q[0]), (p.sigma[0] @ p.sigma[0].T) / 1200**2, 0.0,
        p.delta0[0] / 1200, np.ones(3), 121,
    )
    xd = x[0] / 1200
    exact = [1200 * (a[n] - a[n + 1] + (b[n] - b[n + 1]) @ xd) for n in months]
    np.testing.assert_allclose(approx, exact, atol=1e-8)


def test_expected_short_average_matches_simulation():
    rng = np.random.default_rng(31)
    p = shadow.unpack(THETA)
    x0 = np.array([-0.8, 0.1, 0.0])
    horizon, paths = 24, 100_000
    x = np.broadcast_to(x0, (paths, 3)).copy()
    total = np.zeros(paths)
    for _ in range(horizon):
        total += np.maximum(0.0, p.delta0[0] + x.sum(axis=1))
        x = p.mu[0] + x @ p.rho[0].T + rng.standard_normal((paths, 3)) @ p.sigma[0].T
    simulated = (total / horizon).mean()
    closed = shadow.expected_short_average(THETA, x0[None], 0.0, horizon)[0]
    assert closed == pytest.approx(simulated, abs=5e-3)  # ~4 Monte Carlo standard errors


def test_very_low_bound_reduces_to_the_gaussian_expectation():
    states = np.array([[0.4, -0.3, 0.2], [-1.0, 0.5, 0.0]])
    low = shadow.expected_short_average(THETA, states, -10.0, 120)
    np.testing.assert_allclose(low, shadow.expected_gaussian_average(THETA, states, 120), atol=1e-4)
    near = shadow.expected_short_average(THETA, states, 0.0, 120)
    assert np.abs(near - shadow.expected_gaussian_average(THETA, states, 120)).max() > 0.01


def _simulated_forwards(n, rng):
    p = shadow.unpack(THETA)
    x = np.zeros(3)
    states = np.empty((n, 3))
    for t in range(n):
        x = p.mu[0] + p.rho[0] @ x + p.sigma[0] @ rng.standard_normal(3)
        states[t] = x
    clean = shadow.shadow_forwards(THETA, states, 0.0, shadow.FORWARD_MONTHS)
    return clean + 0.05 * rng.standard_normal(clean.shape), states


def test_loglik_prefers_the_true_parameters():
    forwards, _ = _simulated_forwards(600, np.random.default_rng(32))
    bumped = THETA + 0.05
    values = shadow.loglik(np.vstack([THETA, bumped]), forwards, 0.0)
    assert values[0] > values[1]


def test_filtered_states_track_the_true_states():
    forwards, states = _simulated_forwards(600, np.random.default_rng(33))
    filtered = shadow.filtered_states(THETA, forwards, 0.0)
    true_rate = shadow.shadow_rate(THETA, states)
    assert np.corrcoef(shadow.shadow_rate(THETA, filtered), true_rate)[0, 1] > 0.95


def test_loglik_penalises_non_stationary_dynamics():
    p = shadow.unpack(THETA)
    explosive = shadow.pack(p.rho_q[0], p.delta0[0], p.sigma[0], p.mu[0], 1.01 * np.eye(3), 0.05)
    forwards, _ = _simulated_forwards(50, np.random.default_rng(34))
    values = shadow.loglik(np.vstack([THETA, explosive]), forwards, 0.0)
    assert values[1] == -shadow.PENALTY
    assert np.isfinite(values[0]) and values[0] > -shadow.PENALTY
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_shadow.py -q`
Expected: FAIL with `ImportError`.

- [ ] **Step 3: Implement**

`$WT/macrokit/src/macrokit/termstructure/shadow.py`:

```python
"""Wu and Xia (2016) three-factor shadow-rate term structure model (design §4.3).

Units: annual percent, one period = one month. Shadow rate s_t = delta0 + 1'X_t,
short rate max(r_L, s_t). Under Q, X' = rho_Q X + Sigma e with rho_Q diagonal and
mu_Q = 0 (Wu-Xia normalization); under P, X' = mu + rho X + Sigma e. One-month
forward from month n to n+1: f_n = r_L + sd_n g((a_n + b_n'X - r_L) / sd_n),
g(z) = z Phi(z) + phi(z), with
  b_n = rho_Q^n,  a_n = delta0 - (1/2400) s_n' Omega s_n,  s_n = (1 - rho_Q^n)/(1 - rho_Q),
  sd_n^2 = sum_{j<n} (rho_Q^j)' Omega rho_Q^j,  Omega = Sigma Sigma'.

The likelihood is evaluated for a batch of parameter vectors at once, so one
call returns a value and its finite-difference gradient. The state covariance
is symmetrized after every predict and update step; the 2026-10-17 prototype
broke down numerically after ~70 periods without it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.special import ndtr

from .curve import ZeroPanel
from .var import expected_average

FORWARD_MONTHS = np.array([3, 6, 12, 24, 60, 84, 120])
N_PARAMS = 23
CONVEXITY = 1.0 / 1200.0
PENALTY = 1e12
_SQRT_2PI = np.sqrt(2.0 * np.pi)
_LOG_2PI = np.log(2.0 * np.pi)
_TRIL = ((0, 0), (1, 0), (1, 1), (2, 0), (2, 1), (2, 2))
_DIAG = frozenset({0, 2, 5})


@dataclass(frozen=True)
class ShadowParams:
    """Every field carries a leading batch axis B."""

    rho_q: np.ndarray  # (B, 3), 1 > rho_q1 > rho_q2 > rho_q3 > 0
    delta0: np.ndarray  # (B,)
    sigma: np.ndarray  # (B, 3, 3) lower triangular
    mu: np.ndarray  # (B, 3)
    rho: np.ndarray  # (B, 3, 3)
    omega: np.ndarray  # (B,) measurement error sd, annual %


def _logistic(u: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-u))


def _logit(p: float) -> float:
    return float(np.log(p) - np.log1p(-p))


def pack(rho_q, delta0, sigma, mu, rho, omega) -> np.ndarray:
    """Unconstrained 23-vector: ordered rho_Q, delta0, chol(Sigma) (log diag), mu, rho, log omega."""
    r1, r2, r3 = (float(v) for v in rho_q)
    sigma = np.asarray(sigma, dtype=float)
    tri = [
        np.log(sigma[r, c]) if j in _DIAG else sigma[r, c] for j, (r, c) in enumerate(_TRIL)
    ]
    return np.concatenate(
        [
            [_logit(r1), _logit(r2 / r1), _logit(r3 / r2), float(delta0)],
            tri,
            np.asarray(mu, dtype=float),
            np.asarray(rho, dtype=float).ravel(),
            [np.log(float(omega))],
        ]
    )


def unpack(theta: np.ndarray) -> ShadowParams:
    theta = np.atleast_2d(theta)
    size = theta.shape[0]
    r1 = _logistic(theta[:, 0])
    r2 = r1 * _logistic(theta[:, 1])
    r3 = r2 * _logistic(theta[:, 2])
    sigma = np.zeros((size, 3, 3))
    for j, (r, c) in enumerate(_TRIL):
        value = theta[:, 4 + j]
        sigma[:, r, c] = np.exp(value) if j in _DIAG else value
    return ShadowParams(
        rho_q=np.column_stack([r1, r2, r3]),
        delta0=theta[:, 3].copy(),
        sigma=sigma,
        mu=theta[:, 10:13].copy(),
        rho=theta[:, 13:22].reshape(size, 3, 3).copy(),
        omega=np.exp(theta[:, 22]),
    )


def forward_loadings(p: ShadowParams, months: np.ndarray):
    """a (B, M), b (B, M, 3), sd (B, M) of the shadow one-month forwards."""
    rq = p.rho_q[:, None, :]
    n = np.asarray(months, dtype=float)[None, :, None]
    b = rq**n
    s = (1.0 - rq**n) / (1.0 - rq)
    omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
    a = p.delta0[:, None] - 0.5 * CONVEXITY * np.einsum("bmk,bkl,bml->bm", s, omega, s)
    prod = p.rho_q[:, :, None] * p.rho_q[:, None, :]
    geo = (1.0 - prod[:, None] ** n[..., None]) / (1.0 - prod[:, None])
    sd = np.sqrt(np.einsum("bkl,bmkl->bm", omega, geo))
    return a, b, sd


def _g(z: np.ndarray) -> np.ndarray:
    return z * ndtr(z) + np.exp(-0.5 * z * z) / _SQRT_2PI


def shadow_forwards(
    theta: np.ndarray, states: np.ndarray, r_lower: float, months: np.ndarray
) -> np.ndarray:
    """Model one-month forwards (annual %) for one parameter vector: (T, M)."""
    a, b, sd = forward_loadings(unpack(theta), months)
    z = (a[0] + states @ b[0].T - r_lower) / sd[0]
    return r_lower + sd[0] * _g(z)


def loglik(
    theta: np.ndarray,
    forwards: np.ndarray,
    r_lower: float,
    months: np.ndarray = FORWARD_MONTHS,
    return_states: bool = False,
):
    """Extended-Kalman-filter log-likelihood for each row of ``theta`` (B, 23) or (23,).

    Members with non-stationary P dynamics, a non-positive innovation covariance, or
    non-finite values get ``-PENALTY`` instead of raising.
    """
    theta = np.atleast_2d(theta)
    size, n_obs = theta.shape[0], len(months)
    with np.errstate(all="ignore"):
        p = unpack(theta)
        a, b, sd = forward_loadings(p, months)
        omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
        finite = np.isfinite(theta).all(axis=1)
        raw_rho = np.where(finite[:, None, None], p.rho, 0.0)  # eigvals raises on NaN
        ok = finite & (np.abs(np.linalg.eigvals(raw_rho)).max(axis=1) < 1.0)
        rho = np.where(ok[:, None, None], p.rho, 0.0)
        rho_t = np.swapaxes(rho, 1, 2)
        kron = np.einsum("bij,bkl->bikjl", rho, rho).reshape(size, 9, 9)
        cov = np.linalg.solve(np.eye(9) - kron, omega.reshape(size, 9, 1)).reshape(size, 3, 3)
        cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
        x = np.linalg.solve(np.eye(3) - rho, p.mu[..., None])[..., 0]
        meas = (p.omega**2)[:, None, None] * np.eye(n_obs)
        total = np.zeros(size)
        states = np.empty((size, len(forwards), 3)) if return_states else None
        try:
            for t in range(len(forwards)):
                if t > 0:
                    x = p.mu + np.einsum("bij,bj->bi", rho, x)
                    cov = rho @ cov @ rho_t + omega
                    cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
                z = (a + np.einsum("bmk,bk->bm", b, x) - r_lower) / sd
                resid = forwards[t] - (r_lower + sd * _g(z))
                jac_cov = (ndtr(z)[..., None] * b) @ cov  # H P, (B, M, 3)
                innov = jac_cov @ np.swapaxes(ndtr(z)[..., None] * b, 1, 2) + meas
                sign, logdet = np.linalg.slogdet(innov)
                solved = np.linalg.solve(innov, np.concatenate([resid[..., None], jac_cov], axis=2))
                x = x + np.einsum("bmk,bm->bk", jac_cov, solved[..., 0])
                cov = cov - np.swapaxes(jac_cov, 1, 2) @ solved[..., 1:]
                cov = 0.5 * (cov + np.swapaxes(cov, 1, 2))
                total += -0.5 * (logdet + np.einsum("bm,bm->b", resid, solved[..., 0]) + n_obs * _LOG_2PI)
                ok &= sign > 0
                if states is not None:
                    states[:, t] = x
        except np.linalg.LinAlgError:
            ok[:] = False
        total = np.where(ok & np.isfinite(total), total, -PENALTY)
    return (total, states) if return_states else total


def filtered_states(theta: np.ndarray, forwards: np.ndarray, r_lower: float) -> np.ndarray:
    _, states = loglik(theta, forwards, r_lower, return_states=True)
    return states[0]


def shadow_rate(theta: np.ndarray, states: np.ndarray) -> np.ndarray:
    return unpack(theta).delta0[0] + states.sum(axis=1)


def expected_short_average(
    theta: np.ndarray, states: np.ndarray, r_lower: float, horizon: int
) -> np.ndarray:
    """Mean over h = 0..horizon-1 of E_t[max(r_L, s_{t+h})] under P (closed form).

    ``theta`` (23,) with ``states`` (T, 3) returns (T,); ``theta`` (B, 23) with
    ``states`` (B, T, 3) returns (B, T).
    """
    single = np.ndim(theta) == 1
    theta = np.atleast_2d(theta)
    states = states[None] if states.ndim == 2 else states
    p = unpack(theta)
    omega = p.sigma @ np.swapaxes(p.sigma, 1, 2)
    rho_t = np.swapaxes(p.rho, 1, 2)
    mean_x = states.copy()
    var_x = np.zeros((len(theta), 3, 3))
    total = np.zeros(states.shape[:2])
    for _ in range(horizon):
        m = p.delta0[:, None] + mean_x.sum(axis=2)
        sd = np.sqrt(np.maximum(var_x.sum(axis=(1, 2)), 0.0))[:, None]
        with np.errstate(divide="ignore", invalid="ignore"):
            d = (m - r_lower) / sd
            smooth = r_lower + (m - r_lower) * ndtr(d) + sd * np.exp(-0.5 * d * d) / _SQRT_2PI
        total += np.where(sd > 0, smooth, np.maximum(r_lower, m))
        mean_x = p.mu[:, None, :] + mean_x @ rho_t
        var_x = p.rho @ var_x @ rho_t + omega
    out = total / horizon
    return out[0] if single else out


def expected_gaussian_average(theta: np.ndarray, states: np.ndarray, horizon: int) -> np.ndarray:
    """The same average without the bound (for gate G3 ①)."""
    p = unpack(theta)
    return expected_average(p.mu[0], p.rho[0], p.delta0[0], np.ones(3), states, horizon)


def panel_forwards(panel: ZeroPanel, months: np.ndarray = FORWARD_MONTHS) -> np.ndarray:
    """One-month forwards (annual %) from zero yields: (n+1) y_{n+1} - n y_n."""
    n = np.asarray(months)
    return (n + 1) * panel.columns(n + 1) - n * panel.columns(n)
```

- [ ] **Step 4: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_shadow.py -q`
Expected: PASS. If the forward test fails, compare `a` alone (X = 0): a mismatch growing with n means the convexity sign or the `1/2400` factor is wrong.

- [ ] **Step 5: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure/shadow.py macrokit/tests/test_shadow.py && git commit -m "Implement the Wu-Xia shadow-rate filter with batched likelihoods"
```

---

### Task 10: Shadow-rate estimation, parameter draws, and its synthetic curve

**Files:**
- Modify: `macrokit/src/macrokit/termstructure/shadow.py`
- Modify: `macrokit/src/macrokit/termstructure/synthetic.py`
- Test: `macrokit/tests/test_shadow.py`

**Interfaces:**
- Produces: `RHO_Q_STARTS`, `SIGMA_DIAG_STARTS`, `SIGMA_OFFDIAG_STARTS`, `OMEGA_START`, `FD_STEP = 1e-5`; `default_starts(forwards) -> (20, 23)`; `ShadowFit(theta, negloglik, start_theta, start_negloglik, r_lower)`; `fit_shadow(forwards, r_lower, starts, processes=1, maxiter=500) -> ShadowFit`; `hessian(theta, forwards, r_lower, step=1e-4) -> (23, 23)`; `parameter_draws(theta, hess, n_draws, rng) -> tuple[(n_draws, 23), int]`; `draw_expected(fit, forwards, horizon, n_draws, rng) -> tuple[(n_ok, T), int, int]`; `decompose_shadow(fit, forwards, panel, maturity=120) -> Decomposition`; `synthetic.SHADOW_TRUE`, `synthetic.SyntheticShadow(dates, forwards, yield_pct, expected_pct, short_pct, states)`, `synthetic.shadow_dgp(n_months, rng, *, r_lower=0.0) -> SyntheticShadow`.

- [ ] **Step 1: Write the failing tests**

Append to `$WT/macrokit/tests/test_shadow.py`:

```python
from macrokit.termstructure import synthetic


def test_default_starts_are_twenty_and_start_at_p_equals_q():
    starts = shadow.default_starts(np.full((10, 7), 1.5))
    assert starts.shape == (20, shadow.N_PARAMS)
    p = shadow.unpack(starts)
    np.testing.assert_allclose(p.delta0, 1.5)
    np.testing.assert_allclose(p.rho[:, 0, 0], p.rho_q[:, 0])


def test_optimizer_improves_on_a_perturbed_start():
    syn = synthetic.shadow_dgp(400, np.random.default_rng(41))
    start = synthetic.SHADOW_TRUE + 0.05
    fit = shadow.fit_shadow(syn.forwards, 0.0, start[None], maxiter=30)
    before = -shadow.loglik(start, syn.forwards, 0.0)[0]
    assert fit.negloglik < before
    assert fit.start_negloglik.shape == (1,)


def test_parameter_draws_follow_the_inverse_hessian_and_floor_bad_directions():
    hess = np.diag([4.0, 1.0, -1.0])
    draws, floored = shadow.parameter_draws(np.zeros(3), hess, 20_000, np.random.default_rng(42))
    assert floored == 1
    np.testing.assert_allclose(draws[:, :2].var(axis=0), [0.25, 1.0], rtol=0.05)


def test_shadow_dgp_shapes_and_bound():
    syn = synthetic.shadow_dgp(300, np.random.default_rng(43))
    assert syn.forwards.shape == (300, 7)
    assert syn.short_pct.min() >= 0.0
    assert (syn.short_pct == 0.0).any()  # the bound binds somewhere
    assert syn.expected_pct.shape == syn.yield_pct.shape == (300,)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_shadow.py -q -k "starts or optimizer or draws or dgp"`
Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Implement estimation in `shadow.py`**

Add imports `from concurrent.futures import ProcessPoolExecutor`, `from scipy.optimize import minimize`, `from .decompose import Decomposition`. Append:

```python
RHO_Q_STARTS = (
    (0.999, 0.97, 0.85),
    (0.997, 0.95, 0.7),
    (0.995, 0.9, 0.5),
    (0.99, 0.85, 0.6),
    (0.998, 0.98, 0.9),
)
SIGMA_DIAG_STARTS = (0.1, 0.3)
SIGMA_OFFDIAG_STARTS = (0.0, -0.05)
OMEGA_START = 0.1
FD_STEP = 1e-5


def default_starts(forwards: np.ndarray) -> np.ndarray:
    """The 20 fixed starts of design §4.3: P = Q dynamics, delta0 = mean 3-month forward."""
    delta0 = float(np.mean(forwards[:, 0]))
    starts = []
    for rq in RHO_Q_STARTS:
        for diag in SIGMA_DIAG_STARTS:
            for off in SIGMA_OFFDIAG_STARTS:
                sigma = np.diag([diag, diag, diag])
                sigma[1, 0] = sigma[2, 0] = sigma[2, 1] = off
                starts.append(pack(rq, delta0, sigma, np.zeros(3), np.diag(rq), OMEGA_START))
    return np.array(starts)


def _objective(theta: np.ndarray, forwards: np.ndarray, r_lower: float) -> tuple[float, np.ndarray]:
    """Mean negative log-likelihood and its forward-difference gradient, in one batch."""
    batch = np.vstack([theta, theta + FD_STEP * np.eye(len(theta))])
    values = -loglik(batch, forwards, r_lower) / len(forwards)
    return float(values[0]), (values[1:] - values[0]) / FD_STEP


def _solve(job: tuple[np.ndarray, np.ndarray, float, int]) -> tuple[np.ndarray, float]:
    theta0, forwards, r_lower, maxiter = job
    result = minimize(
        _objective, theta0, args=(forwards, r_lower), jac=True, method="L-BFGS-B",
        options={"maxiter": maxiter},
    )
    return result.x, float(result.fun) * len(forwards)


@dataclass(frozen=True)
class ShadowFit:
    theta: np.ndarray
    negloglik: float  # total over observations
    start_theta: np.ndarray  # (S, 23) optimum reached from each start
    start_negloglik: np.ndarray  # (S,)
    r_lower: float


def fit_shadow(
    forwards: np.ndarray,
    r_lower: float,
    starts: np.ndarray,
    processes: int = 1,
    maxiter: int = 500,
) -> ShadowFit:
    jobs = [(start, forwards, r_lower, maxiter) for start in starts]
    if processes > 1:
        with ProcessPoolExecutor(max_workers=processes) as pool:
            results = list(pool.map(_solve, jobs))
    else:
        results = [_solve(job) for job in jobs]
    thetas = np.array([r[0] for r in results])
    values = np.array([r[1] for r in results])
    best = int(np.argmin(values))
    return ShadowFit(thetas[best], float(values[best]), thetas, values, r_lower)


def hessian(theta: np.ndarray, forwards: np.ndarray, r_lower: float, step: float = 1e-4) -> np.ndarray:
    """Central-difference Hessian of the negative log-likelihood, all points in one batch."""
    size = len(theta)
    eye = np.eye(size) * step
    signs = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    pairs = [(i, j) for i in range(size) for j in range(i, size)]
    points = np.array(
        [theta + si * eye[i] + sj * eye[j] for i, j in pairs for si, sj in signs]
    )
    values = -loglik(points, forwards, r_lower).reshape(len(pairs), 4)
    hess = np.empty((size, size))
    for (i, j), v in zip(pairs, values, strict=True):
        hess[i, j] = hess[j, i] = (v[0] - v[1] - v[2] + v[3]) / (4 * step * step)
    return hess


def parameter_draws(
    theta: np.ndarray, hess: np.ndarray, n_draws: int, rng: np.random.Generator
) -> tuple[np.ndarray, int]:
    """Normal draws with covariance inv(H); eigenvalues below 1e-8 * max are floored (counted)."""
    w, v = np.linalg.eigh(0.5 * (hess + hess.T))
    floor = 1e-8 * w.max()
    floored = int((w < floor).sum())
    cov = (v / np.maximum(w, floor)) @ v.T
    return rng.multivariate_normal(theta, cov, size=n_draws, method="eigh"), floored


def draw_expected(
    fit: ShadowFit, forwards: np.ndarray, horizon: int, n_draws: int, rng: np.random.Generator
) -> tuple[np.ndarray, int, int]:
    """E_t for each accepted parameter draw: (expected (n_ok, T), n_rejected, n_floored)."""
    draws, floored = parameter_draws(fit.theta, hessian(fit.theta, forwards, fit.r_lower), n_draws, rng)
    values, states = loglik(draws, forwards, fit.r_lower, return_states=True)
    ok = values > -PENALTY
    expected = expected_short_average(draws[ok], states[ok], fit.r_lower, horizon)
    return expected, int((~ok).sum()), floored


def decompose_shadow(
    fit: ShadowFit, forwards: np.ndarray, panel: ZeroPanel, maturity: int = 120
) -> Decomposition:
    states = filtered_states(fit.theta, forwards, fit.r_lower)
    expected = expected_short_average(fit.theta, states, fit.r_lower, maturity)
    return Decomposition("shadow", panel.dates, panel.column(maturity), expected)
```

- [ ] **Step 4: Append the shadow generator to `synthetic.py`**

Add `from datetime import date` and `from .shadow import FORWARD_MONTHS, expected_short_average, pack, shadow_forwards, unpack` to the imports and append:

```python
SHADOW_TRUE = pack(
    rho_q=(0.997, 0.95, 0.8),
    delta0=1.0,
    sigma=np.array([[0.15, 0.0, 0.0], [0.05, 0.2, 0.0], [0.0, -0.05, 0.25]]),
    mu=np.zeros(3),
    rho=np.diag([0.99, 0.94, 0.8]),
    omega=0.05,
)


@dataclass(frozen=True)
class SyntheticShadow:
    dates: tuple[date, ...]
    forwards: np.ndarray  # (T, 7) observed one-month forwards at FORWARD_MONTHS
    yield_pct: np.ndarray  # observed 10-year zero yield
    expected_pct: np.ndarray  # true E_t, 120 months
    short_pct: np.ndarray  # true short rate max(r_L, s)
    states: np.ndarray


def shadow_dgp(
    n_months: int,
    rng: np.random.Generator,
    *,
    r_lower: float = 0.0,
    theta: np.ndarray = SHADOW_TRUE,
    burn_in: int = 500,
    horizon: int = 120,
) -> SyntheticShadow:
    p = unpack(theta)
    mu, rho, chol, omega = p.mu[0], p.rho[0], p.sigma[0], p.omega[0]
    x = np.linalg.solve(np.eye(3) - rho, mu)
    shocks = rng.standard_normal((burn_in + n_months, 3)) @ chol.T
    states = np.empty((n_months, 3))
    for t in range(burn_in + n_months):
        x = mu + rho @ x + shocks[t]
        if t >= burn_in:
            states[t - burn_in] = x
    forwards = shadow_forwards(theta, states, r_lower, np.arange(1, horizon + 1))  # n = 1..horizon
    short = np.maximum(r_lower, p.delta0[0] + states.sum(axis=1))
    zero = (short + forwards[:, : horizon - 1].sum(axis=1)) / horizon  # mean of n = 0..horizon-1
    observed = forwards[:, FORWARD_MONTHS - 1] + omega * rng.standard_normal((n_months, 7))
    return SyntheticShadow(
        month_ends(n_months),
        observed,
        zero + omega * rng.standard_normal(n_months),
        expected_short_average(theta, states, r_lower, horizon),
        short,
        states,
    )
```

- [ ] **Step 5: Run the tests**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_shadow.py -q`
Expected: PASS.

- [ ] **Step 6: Run the whole macrokit suite and lint**

Run: `cd $WT && $PY -m pytest macrokit/tests -q && /home/kazumasa/projects/.venv/bin/ruff check macrokit && /home/kazumasa/projects/.venv/bin/ruff format --check macrokit`
Expected: all pass; the new tests add well under 30 s (`--durations=10` to check). Run `ruff format macrokit` if the format check fails, then re-run.

- [ ] **Step 7: Commit**

```bash
cd $WT && git add macrokit/src/macrokit/termstructure macrokit/tests/test_shadow.py && git commit -m "Estimate the shadow-rate model from fixed starts and draw its parameters"
```

---

### Task 11: Gates G1–G4

**Files:**
- Create: `macrokit/research/2026-10-jgb-term-premium/gates.py`
- Create (output): `macrokit/research/2026-10-jgb-term-premium/gates.json`
- Test: `macrokit/tests/test_term_premium_research.py`

**Interfaces:**
- Consumes: everything in `termstructure`, `sources.us_term`, `snapshot.latest_payload`, `store.connect`.
- Produces: `gates.json` with keys `code_commit`, `g1`, `g2`, `g3`, `g4`, `passed_models`; function `passed_models(report: dict) -> list[str]`.

- [ ] **Step 1: Refresh the data (network; about 20 minutes, mostly `rates`)**

```bash
cd $WT && $MK rates && $MK callrate && $MK us-term
```

Expected: `rates` adds the rows after 2026-08-17; `callrate` parses ~15,750 rows; `us-term` stores three files (~16 MB, ~10 MB, ~57 KB). Then `du -sh /home/kazumasa/projects/macrokit/data` (expect well under 100 MB).

- [ ] **Step 2: Write the failing test for the gate bookkeeping**

`$WT/macrokit/tests/test_term_premium_research.py`:

```python
import importlib.util
from pathlib import Path

import pytest

RESEARCH = Path(__file__).resolve().parents[1] / "research/2026-10-jgb-term-premium"


def _load(name):
    spec = importlib.util.spec_from_file_location(f"tp_{name}", RESEARCH / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gates():
    return _load("gates")


def _report(**overrides):
    report = {
        "g1": {m: {"pass": True} for m in ("acm", "acm_bc", "dns", "shadow")},
        "g2": {"pass": True},
        "g3": {"pass": True},
        "g4": {"pass": True},
    }
    report.update(overrides)
    return report


def test_all_gates_pass_all_models(gates):
    assert gates.passed_models(_report()) == ["acm", "acm_bc", "shadow", "dns"]


def test_g2_failure_removes_both_acm_variants(gates):
    assert gates.passed_models(_report(g2={"pass": False})) == ["shadow", "dns"]


def test_g3_failure_removes_the_shadow_model(gates):
    assert gates.passed_models(_report(g3={"pass": False})) == ["acm", "acm_bc", "dns"]


def test_a_data_failure_stops_everything(gates):
    assert gates.passed_models(_report(g4={"pass": False})) == []
```

- [ ] **Step 3: Run it to verify it fails**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_term_premium_research.py -q`
Expected: FAIL with `FileNotFoundError` (no gates.py).

- [ ] **Step 4: Implement `gates.py`**

`$WT/macrokit/research/2026-10-jgb-term-premium/gates.py`:

```python
"""Gates G1-G4 of the JGB term-premium re-test (design 2026-10-17 §5).

Computes no Japanese decomposition: G4 only checks the Japanese curve fits.

    $PY macrokit/research/2026-10-jgb-term-premium/gates.py \
        --data-root /home/kazumasa/projects/macrokit/data --processes 20
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from datetime import date
from pathlib import Path

import numpy as np

from macrokit.snapshot import latest_payload
from macrokit.sources import us_term
from macrokit.store import connect
from macrokit.termstructure import acm, dns, shadow, synthetic
from macrokit.termstructure.curve import ZeroPanel, fit_month_ends
from macrokit.termstructure.decompose import largest_rise_window, share_of

HERE = Path(__file__).resolve().parent
SEED = 20261017
G1_MONTHS = 20_000
WINDOW = 23  # end-July 2024 -> end-June 2026
TOL_SHARE, TOL_RMSE = 0.05, 0.10
MODELS = ("acm", "acm_bc", "shadow", "dns")


def _commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=HERE, capture_output=True, text=True, check=True
    ).stdout.strip()


def _score(expected, true_expected, yields, i0, i1) -> dict:
    s_hat = float(share_of(expected, yields, i0, i1))
    s_true = float(share_of(true_expected, yields, i0, i1))
    rmse = float(np.sqrt(((expected - true_expected) ** 2).mean()))
    return {
        "share": s_hat,
        "true_share": s_true,
        "share_error": abs(s_hat - s_true),
        "tp_rmse": rmse,
        "pass": abs(s_hat - s_true) <= TOL_SHARE and rmse <= TOL_RMSE,
    }


def g1(processes: int) -> dict:
    out: dict = {}
    syn = synthetic.affine_dgp(G1_MONTHS, np.random.default_rng(SEED))
    y = syn.panel.column(120)
    i0, i1 = largest_rise_window(y, WINDOW)
    fit = acm.fit_acm(syn.panel)
    corrected = acm.kilian_correct(fit.factors, fit.var, 1000, np.random.default_rng(SEED + 1))
    out["acm"] = _score(fit.expected(120), syn.expected_pct, y, i0, i1)
    out["acm_bc"] = _score(fit.expected(120, corrected.mu, corrected.phi), syn.expected_pct, y, i0, i1)
    out["acm_control"] = _score(syn.short_pct, syn.expected_pct, y, i0, i1)

    syn = synthetic.dns_dgp(G1_MONTHS, np.random.default_rng(SEED + 2))
    y = syn.panel.column(120)
    i0, i1 = largest_rise_window(y, WINDOW)
    out["dns"] = _score(dns.fit_dns(syn.panel).expected(120), syn.expected_pct, y, i0, i1)
    out["dns_control"] = _score(syn.short_pct, syn.expected_pct, y, i0, i1)

    sh = synthetic.shadow_dgp(G1_MONTHS, np.random.default_rng(SEED + 3), r_lower=0.0)
    i0, i1 = largest_rise_window(sh.yield_pct, WINDOW)
    started = time.perf_counter()
    fit_sh = shadow.fit_shadow(sh.forwards, 0.0, shadow.default_starts(sh.forwards), processes)
    states = shadow.filtered_states(fit_sh.theta, sh.forwards, 0.0)
    expected = shadow.expected_short_average(fit_sh.theta, states, 0.0, 120)
    out["shadow"] = _score(expected, sh.expected_pct, sh.yield_pct, i0, i1)
    out["shadow"]["seconds"] = round(time.perf_counter() - started, 1)
    out["shadow_control"] = _score(sh.short_pct, sh.expected_pct, sh.yield_pct, i0, i1)
    for model in ("acm", "dns", "shadow"):
        out[f"{model}_control"]["fails_as_required"] = not out[f"{model}_control"]["pass"]
    return out


def _us_panel(raw_root: Path, start: date, end: date, max_months: int) -> ZeroPanel:
    days = us_term.parse_gsw(latest_payload(raw_root, us_term.SOURCE, "gsw").read_bytes())
    ends = [d for d in us_term.month_end_days(days) if start <= d.obs_date <= end]
    months = np.arange(1, max_months + 1)
    yields = np.vstack([us_term.gsw_zero(d, months) for d in ends])
    return ZeroPanel(tuple(d.obs_date for d in ends), months, yields)


def _g2_once(panel: ZeroPanel, reference: dict) -> dict:
    def premium(p: ZeroPanel, k: int) -> np.ndarray:
        fit = acm.fit_acm(p, k=k)
        return fit.fitted_yield(120) - fit.fitted_yield(120, risk_neutral=True)

    keys = [(d.year, d.month) for d in panel.dates]
    have = [i for i, key in enumerate(keys) if key in reference]
    ref = np.array([reference[keys[i]]["ACMTP10"] for i in have])
    ours = premium(panel, 5)[have]
    i0, i1 = keys.index((2024, 7)), keys.index((2026, 6))
    delta_gap = abs((ours[have.index(i1)] - ours[have.index(i0)]) - (reference[(2026, 6)]["ACMTP10"] - reference[(2024, 7)]["ACMTP10"]))
    corr = float(np.corrcoef(ours, ref)[0, 1])
    rmse = float(np.sqrt(((ours - ref) ** 2).mean()))
    one_factor = float(np.corrcoef(premium(panel, 1)[have], ref)[0, 1])
    order = np.random.default_rng(SEED).permutation(len(panel.dates))
    shuffled = ZeroPanel(panel.dates, panel.months, panel.yields[order])
    by_date = dict(zip(order, premium(shuffled, 5), strict=True))
    shuffled_corr = float(np.corrcoef([by_date[i] for i in have], ref)[0, 1])
    return {
        "start": panel.dates[0].isoformat(),
        "corr": corr,
        "rmse": rmse,
        "delta_gap": float(delta_gap),
        "pass": corr >= 0.95 and rmse <= 0.25 and delta_gap <= 0.15,
        "control_one_factor_corr": one_factor,
        "control_shuffled_corr": shuffled_corr,
        "controls_fail_as_required": one_factor < 0.95 and shuffled_corr < 0.95,
    }


def g2(raw_root: Path) -> dict:
    reference = us_term.parse_acm(latest_payload(raw_root, us_term.SOURCE, "acm").read_bytes())
    first = _g2_once(_us_panel(raw_root, date(1961, 6, 1), date(2026, 6, 30), 120), reference)
    attempts = [first]
    if not first["pass"]:
        attempts.append(_g2_once(_us_panel(raw_root, date(1971, 8, 1), date(2026, 6, 30), 120), reference))
    passed = [a for a in attempts if a["pass"] and a["controls_fail_as_required"]]
    return {"attempts": attempts, "pass": bool(passed)}


def g3(raw_root: Path, processes: int) -> dict:
    panel = _us_panel(raw_root, date(1990, 1, 1), date(2022, 2, 28), 121)
    forwards = shadow.panel_forwards(panel)
    fit = shadow.fit_shadow(forwards, 0.25, shadow.default_starts(forwards), processes)
    states = shadow.filtered_states(fit.theta, forwards, 0.25)
    gaussian = shadow.expected_gaussian_average(fit.theta, states, 120)
    low_gap = float(np.abs(shadow.expected_short_average(fit.theta, states, -10.0, 120) - gaussian).max())
    zero_gap = float(np.abs(shadow.expected_short_average(fit.theta, states, 0.0, 120) - gaussian).max())
    equality = {"max_gap_low_bound": low_gap, "pass": low_gap <= 0.01, "control_gap_zero_bound": zero_gap, "control_fails_as_required": zero_gap > 0.01}
    path = latest_payload(raw_root, us_term.SOURCE, "wuxia")
    published = us_term.parse_wuxia(path.read_bytes()) if path else {}
    windows = ((date(2009, 1, 1), date(2015, 11, 30)), (date(2020, 4, 1), date(2022, 2, 28)))
    rate = shadow.shadow_rate(fit.theta, states)
    pairs = [
        (rate[i], published[(d.year, d.month)])
        for i, d in enumerate(panel.dates)
        if (d.year, d.month) in published and any(a <= d <= b for a, b in windows)
    ]
    comparison = None
    if pairs:
        ours, theirs = (np.array(v) for v in zip(*pairs, strict=True))
        corr = float(np.corrcoef(ours, theirs)[0, 1])
        comparison = {"months": len(pairs), "corr": corr, "pass": corr >= 0.9}
    passed = equality["pass"] and equality["control_fails_as_required"] and (comparison is None or comparison["pass"])
    return {
        "equality": equality,
        "wuxia": comparison,
        "negloglik_by_start": sorted(float(v) for v in fit.start_negloglik),
        "pass": passed,
    }


def g4(data_root: Path) -> dict:
    con = connect(data_root / "macrokit.duckdb")
    fits = fit_month_ends(con, date(1986, 8, 1), date(2026, 6, 30))
    errors = np.concatenate([np.abs(f.errors_bp) for f in fits])
    worst = [
        {"date": f.obs_date.isoformat(), "max_bp": float(np.abs(f.errors_bp).max())}
        for f in fits
        if np.abs(f.errors_bp).max() > 10
    ]
    missing = [f.obs_date.isoformat() for f in fits if f.overnight is None]
    median = float(np.median(errors))
    return {
        "months": len(fits),
        "first": fits[0].obs_date.isoformat(),
        "last": fits[-1].obs_date.isoformat(),
        "median_abs_error_bp": median,
        "months_over_10bp": worst,
        "months_without_overnight": missing,
        "pass": median <= 3.0 and not missing and len(fits) == 479,
    }


def passed_models(report: dict) -> list[str]:
    if not report["g4"]["pass"]:
        return []
    ok = {
        "acm": report["g1"]["acm"]["pass"] and report["g2"]["pass"],
        "acm_bc": report["g1"]["acm_bc"]["pass"] and report["g2"]["pass"],
        "shadow": report["g1"]["shadow"]["pass"] and report["g3"]["pass"],
        "dns": report["g1"]["dns"]["pass"],
    }
    return [m for m in MODELS if ok[m]]


def _plain(value):
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--processes", type=int, default=20)
    args = parser.parse_args()
    raw = args.data_root / "raw"
    report = {"code_commit": _commit(), "g4": g4(args.data_root)}
    print("G4", json.dumps(_plain(report["g4"]))[:300], flush=True)
    report["g2"] = g2(raw)
    print("G2", report["g2"]["pass"], flush=True)
    report["g3"] = g3(raw, args.processes)
    print("G3", report["g3"]["pass"], flush=True)
    report["g1"] = g1(args.processes)
    print("G1", {k: v.get("pass") for k, v in report["g1"].items()}, flush=True)
    report["passed_models"] = passed_models(report)
    (HERE / "gates.json").write_text(json.dumps(_plain(report), indent=2) + "\n", encoding="utf-8")
    print("passed:", report["passed_models"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the bookkeeping test and lint**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_term_premium_research.py -q && /home/kazumasa/projects/.venv/bin/ruff check macrokit && /home/kazumasa/projects/.venv/bin/ruff format macrokit`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit the gate code (gates must run on committed code)**

```bash
cd $WT && git add macrokit/research/2026-10-jgb-term-premium/gates.py macrokit/tests/test_term_premium_research.py && git commit -m "Add the validation gates for the term-premium re-test"
```

- [ ] **Step 7: Run the gates (about 30–60 minutes wall, 20 processes)**

Run: `cd $WT && $PY macrokit/research/2026-10-jgb-term-premium/gates.py --data-root /home/kazumasa/projects/macrokit/data --processes 20 2>&1 | tee /tmp/claude-1000/-home-kazumasa-projects/df1bf6ad-598d-44e3-a3ed-6b1df2d7d491/scratchpad/gates.log`
Expected: `gates.json` written; G2 close to the prototype (corr ≈ 0.9998, RMSE ≈ 0.15). Each control row must show `fails_as_required: true`; if one does not, the gate is uninformative — fix the generator (design §5 G1) and record the change in spec §9 before re-running.

If a gate fails: diagnose and fix the bug, commit, and re-run. Changing a fixed setting (Global Constraints) requires a spec §9 entry with the reason *before* Japanese results exist. Do not lower a tolerance to make a gate pass.

- [ ] **Step 8: Commit the gate results**

```bash
cd $WT && git add macrokit/research/2026-10-jgb-term-premium/gates.json && git commit -m "Record the gate results for the term-premium re-test"
```

---

### Task 12: Small-sample bias study (design §5.1, reference only)

**Files:**
- Create: `macrokit/research/2026-10-jgb-term-premium/small_sample.py`
- Create (output): `macrokit/research/2026-10-jgb-term-premium/small_sample.json`

**Interfaces:**
- Consumes: `gates._us_panel` pattern (re-implemented locally to keep scripts independent), `acm.fit_acm`, `acm.kilian_correct`, `dns.fit_dns`, `synthetic.AffineParams.from_fit`, `synthetic.simulate_affine`, `decompose.largest_rise_window`, `decompose.share_of`.
- Produces: `small_sample.json` with per-model `mean_error`, `sd_error`, `q05`, `q50`, `q95` of ŝ − s over 500 samples of 479 months.

- [ ] **Step 1: Implement**

`$WT/macrokit/research/2026-10-jgb-term-premium/small_sample.py`:

```python
"""How far each model's share drifts in a 479-month sample (design §5.1, not a gate).

The DGP is the ACM model estimated on US GSW data (1961-06..2026-06), so no
Japanese estimate is used. The shadow-rate model is excluded (cost; spec §9).

    $PY macrokit/research/2026-10-jgb-term-premium/small_sample.py \
        --data-root /home/kazumasa/projects/macrokit/data
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import numpy as np

from macrokit.snapshot import latest_payload
from macrokit.sources import us_term
from macrokit.termstructure import acm, dns, synthetic
from macrokit.termstructure.curve import ZeroPanel
from macrokit.termstructure.decompose import largest_rise_window, share_of

HERE = Path(__file__).resolve().parent
SEED = 20261117
SAMPLES, MONTHS, WINDOW = 500, 479, 23


def us_params(raw_root: Path) -> synthetic.AffineParams:
    days = us_term.parse_gsw(latest_payload(raw_root, us_term.SOURCE, "gsw").read_bytes())
    ends = [d for d in us_term.month_end_days(days) if date(1961, 6, 1) <= d.obs_date <= date(2026, 6, 30)]
    months = np.arange(1, 121)
    panel = ZeroPanel(tuple(d.obs_date for d in ends), months, np.vstack([us_term.gsw_zero(d, months) for d in ends]))
    return synthetic.AffineParams.from_fit(acm.fit_acm(panel))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", type=Path, required=True)
    args = parser.parse_args()
    params = us_params(args.data_root / "raw")
    rng = np.random.default_rng(SEED)
    errors: dict[str, list[float]] = {"acm": [], "acm_bc": [], "dns": []}
    for _ in range(SAMPLES):
        syn = synthetic.simulate_affine(params, MONTHS, rng)
        y = syn.panel.column(120)
        i0, i1 = largest_rise_window(y, WINDOW)
        truth = float(share_of(syn.expected_pct, y, i0, i1))
        fit = acm.fit_acm(syn.panel)
        bc = acm.kilian_correct(fit.factors, fit.var, 1000, rng)
        estimates = {
            "acm": fit.expected(120),
            "acm_bc": fit.expected(120, bc.mu, bc.phi),
            "dns": dns.fit_dns(syn.panel).expected(120),
        }
        for model, expected in estimates.items():
            errors[model].append(float(share_of(expected, y, i0, i1)) - truth)
    summary = {
        model: {
            "mean_error": float(np.mean(v)),
            "sd_error": float(np.std(v)),
            "q05": float(np.quantile(v, 0.05)),
            "q50": float(np.quantile(v, 0.50)),
            "q95": float(np.quantile(v, 0.95)),
        }
        for model, v in errors.items()
    }
    out = {"samples": SAMPLES, "months": MONTHS, "seed": SEED, "dgp": "US ACM K=5, GSW 1961-06..2026-06", "share_error": summary}
    (HERE / "small_sample.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Lint, commit the script, run it (a few minutes), commit the result**

```bash
cd $WT && /home/kazumasa/projects/.venv/bin/ruff format macrokit && /home/kazumasa/projects/.venv/bin/ruff check macrokit && git add macrokit/research/2026-10-jgb-term-premium/small_sample.py && git commit -m "Add the small-sample bias study"
cd $WT && $PY macrokit/research/2026-10-jgb-term-premium/small_sample.py --data-root /home/kazumasa/projects/macrokit/data && git add macrokit/research/2026-10-jgb-term-premium/small_sample.json && git commit -m "Record the small-sample bias study"
```

Expected: three model summaries; ACM without correction typically shows a negative `mean_error` (too little persistence → expectations revert too fast).

---

### Task 13: Freeze the configuration and run the Japanese estimation once

**Files:**
- Create: `macrokit/research/2026-10-jgb-term-premium/config.json`
- Create: `macrokit/research/2026-10-jgb-term-premium/run_japan.py`
- Create (output): `macrokit/research/2026-10-jgb-term-premium/results.json`
- Test: `macrokit/tests/test_term_premium_research.py`

**Interfaces:**
- Consumes: all models; `gates.json` (`passed_models`, `code_commit`).
- Produces: `canonical(config) -> bytes`; `config_hash(config) -> str`; `check_hash(config) -> None` (raises `ValueError`); `freeze()`; `results.json`.

- [ ] **Step 1: Write the config**

`$WT/macrokit/research/2026-10-jgb-term-premium/config.json`:

```json
{
  "schema_version": 1,
  "spec": "docs/superpowers/specs/2026-10-17-jgb-term-premium-design.md",
  "t0_month": "2024-07",
  "t1_month": "2026-06",
  "estimation_start": "1986-08-01",
  "estimation_end": "2026-06-30",
  "maturity_months": 120,
  "supplementary_maturities": [60],
  "verdict_band": [0.35, 0.65],
  "models": ["acm", "acm_bc", "shadow", "dns"],
  "acm": {"k": 5, "factor_months": "3..120 step 3", "return_months": [6, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120]},
  "bias_correction": {"n_boot": 1000},
  "shadow": {"r_lower_pct": -0.10, "forward_months": [3, 6, 12, 24, 60, 84, 120], "starts": 20, "maxiter": 500},
  "dns": {"lambda": 0.0609},
  "intervals": {"level": 0.90, "n_boot": 1000, "n_draws": 500},
  "supplementary": {"windows": ["2004-01-01", "2009-01-01"], "acm_k3": true, "long_acm_start": "1999-09-01", "t0_alt_month": "2024-08"},
  "seeds": {"acm": 20261017, "acm_bc": 20261018, "dns": 20261019, "shadow": 20261020},
  "code_commit": null,
  "gates_commit": null,
  "sha256": null
}
```

- [ ] **Step 2: Write the failing tests**

Append to `$WT/macrokit/tests/test_term_premium_research.py`:

```python
import json


@pytest.fixture(scope="module")
def run_japan():
    return _load("run_japan")


def test_canonical_ignores_the_hash_field(run_japan):
    config = {"b": 1, "a": [1, 2], "sha256": "x"}
    assert run_japan.canonical(config) == b'{"a":[1,2],"b":1}'


def test_check_hash_accepts_a_frozen_config_and_rejects_an_edit(run_japan):
    config = json.loads((RESEARCH / "config.json").read_text())
    config["sha256"] = run_japan.config_hash(config)
    run_japan.check_hash(config)
    config["verdict_band"] = [0.3, 0.7]
    with pytest.raises(ValueError, match="sha256"):
        run_japan.check_hash(config)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_term_premium_research.py -q -k "canonical or check_hash"`
Expected: FAIL with `FileNotFoundError` (no run_japan.py).

- [ ] **Step 4: Implement `run_japan.py`**

`$WT/macrokit/research/2026-10-jgb-term-premium/run_japan.py`:

```python
"""Run the Japanese decomposition once, from a frozen configuration (design §2.4).

    $PY run_japan.py --freeze          # after the gates: record commits and the hash
    $PY run_japan.py --data-root /home/kazumasa/projects/macrokit/data --processes 20
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path

import numpy as np

from macrokit.store import connect
from macrokit.termstructure import acm, dns, shadow
from macrokit.termstructure.curve import ZeroPanel, fit_month_ends, zero_panel
from macrokit.termstructure.decompose import (
    Decomposition,
    interval,
    month_end_in,
    share_of,
    verdict,
)

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
GATES = HERE / "gates.json"
CODE_PATHS = ("macrokit/src", "macrokit/research/2026-10-jgb-term-premium/run_japan.py")


def canonical(config: dict) -> bytes:
    body = {k: v for k, v in config.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def config_hash(config: dict) -> str:
    return hashlib.sha256(canonical(config)).hexdigest()


def check_hash(config: dict) -> None:
    if config.get("sha256") != config_hash(config):
        raise ValueError("config.json sha256 does not match its content; re-freeze is not allowed after results")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()


def _code_unchanged(since: str, paths: tuple[str, ...] = CODE_PATHS) -> bool:
    top = _git("rev-parse", "--show-toplevel")
    return subprocess.run(["git", "diff", "--quiet", since, "HEAD", "--", *paths], cwd=top).returncode == 0


def freeze() -> None:
    if _git("status", "--porcelain", "--", "macrokit"):
        raise SystemExit("commit everything under macrokit/ before freezing")
    config = json.loads(CONFIG.read_text())
    gates = json.loads(GATES.read_text())
    if not _code_unchanged(gates["code_commit"], ("macrokit/src",)):
        raise SystemExit("macrokit/src changed after the gates ran; re-run the gates first")
    config["code_commit"] = _git("rev-parse", "HEAD")
    config["gates_commit"] = gates["code_commit"]
    config["sha256"] = config_hash(config)
    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print("frozen:", config["sha256"])


def _month(text: str) -> tuple[int, int]:
    year, month = text.split("-")[:2]
    return int(year), int(month)


def _estimate(panel: ZeroPanel, cfg: dict, processes: int, maturities: list[int], intervals: bool) -> dict:
    """Point estimates (and optionally interval draws) for the four models."""
    seeds = cfg["seeds"]
    fit_a = acm.fit_acm(panel, k=cfg["acm"]["k"])
    bc = acm.kilian_correct(fit_a.factors, fit_a.var, cfg["bias_correction"]["n_boot"], np.random.default_rng(seeds["acm_bc"]))
    fit_d = dns.fit_dns(panel, lam=cfg["dns"]["lambda"])
    forwards = shadow.panel_forwards(panel, np.array(cfg["shadow"]["forward_months"]))
    fit_s = shadow.fit_shadow(forwards, cfg["shadow"]["r_lower_pct"], shadow.default_starts(forwards), processes, cfg["shadow"]["maxiter"])
    out: dict = {"decomposition": {}, "draws": {}, "fits": {"acm_bc_shrink": bc.shrink, "shadow": fit_s}}
    for n in maturities:
        out["decomposition"][n] = {
            "acm": acm.decompose_acm(panel, fit_a, n),
            "acm_bc": acm.decompose_acm(panel, fit_a, n, bc.mu, bc.phi, model="acm_bc"),
            "shadow": shadow.decompose_shadow(fit_s, forwards, panel, n),
            "dns": dns.decompose_dns(panel, fit_d, n),
        }
    if intervals:
        n_boot, horizon = cfg["intervals"]["n_boot"], cfg["maturity_months"]
        out["draws"] = {
            "acm": acm.bootstrap_expected(fit_a, horizon, n_boot, np.random.default_rng(seeds["acm"])),
            "acm_bc": acm.bootstrap_expected(fit_a, horizon, n_boot, np.random.default_rng(seeds["acm_bc"] + 1), correction_boot=cfg["bias_correction"]["n_boot"]),
            "dns": dns.bootstrap_expected_dns(fit_d, horizon, n_boot, np.random.default_rng(seeds["dns"])),
        }
        expected, rejected, floored = shadow.draw_expected(fit_s, forwards, horizon, cfg["intervals"]["n_draws"], np.random.default_rng(seeds["shadow"]))
        out["draws"]["shadow"] = expected
        out["fits"]["shadow_draws"] = {"rejected": rejected, "floored_eigenvalues": floored}
    return out


def _shares(decs: dict, t0: date, t1: date, models: list[str]) -> dict:
    return {m: decs[m].share(t0, t1) for m in models}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--processes", type=int, default=20)
    args = parser.parse_args()
    if args.freeze:
        freeze()
        return
    cfg = json.loads(CONFIG.read_text())
    check_hash(cfg)
    if not _code_unchanged(cfg["code_commit"]) or _git("status", "--porcelain", "--", *CODE_PATHS):
        raise SystemExit("code differs from the frozen commit")
    gates = json.loads(GATES.read_text())
    models = [m for m in cfg["models"] if m in gates["passed_models"]]

    con = connect(args.data_root / "macrokit.duckdb")
    full = zero_panel(fit_month_ends(con, date.fromisoformat(cfg["estimation_start"]), date.today()))
    panel = full.window(full.dates[0], date.fromisoformat(cfg["estimation_end"]))
    t0 = month_end_in(panel.dates, *_month(cfg["t0_month"]))
    t1 = month_end_in(panel.dates, *_month(cfg["t1_month"]))
    i0, i1 = panel.dates.index(t0), panel.dates.index(t1)
    horizon = cfg["maturity_months"]

    main_run = _estimate(panel, cfg, args.processes, [horizon, *cfg["supplementary_maturities"]], intervals=True)
    decs = main_run["decomposition"][horizon]
    y = panel.column(horizon)
    results: dict = {
        "config_sha256": cfg["sha256"],
        "code_commit": cfg["code_commit"],
        "t0": t0.isoformat(),
        "t1": t1.isoformat(),
        "delta_yield_pct": float(y[i1] - y[i0]),
        "models_used": models,
        "main": {},
    }
    for m in cfg["models"]:
        s = decs[m].share(t0, t1)
        lo, hi = interval(share_of(main_run["draws"][m], y, i0, i1), cfg["intervals"]["level"])
        results["main"][m] = {
            "share": s,
            "interval": [lo, hi],
            "contains_half": lo <= 0.5 <= hi,
            "delta_expected_pct": float(decs[m].expected_pct[i1] - decs[m].expected_pct[i0]),
            "passed_gates": m in models,
        }
    results["verdict"] = verdict({m: results["main"][m]["share"] for m in models})
    rw = Decomposition("random_walk", panel.dates, y, panel.column(1))
    results["brackets"] = {"constant_premium": 1.0, "random_walk": rw.share(t0, t1)}

    fit_s = main_run["fits"]["shadow"]
    forwards = shadow.panel_forwards(panel, np.array(cfg["shadow"]["forward_months"]))
    by_start = []
    for value, theta in zip(fit_s.start_negloglik, fit_s.start_theta, strict=True):
        states = shadow.filtered_states(theta, forwards, fit_s.r_lower)
        e = shadow.expected_short_average(theta, states, fit_s.r_lower, horizon)
        by_start.append({"negloglik": float(value), "share": float(share_of(e, y, i0, i1))})
    results["shadow_starts"] = sorted(by_start, key=lambda r: r["negloglik"])
    results["shadow_draws"] = main_run["fits"].get("shadow_draws")
    results["acm_bc_shrink"] = main_run["fits"]["acm_bc_shrink"]

    supp: dict = {}
    for n in cfg["supplementary_maturities"]:
        supp[f"maturity_{n}"] = _shares(main_run["decomposition"][n], t0, t1, cfg["models"])
    t0_alt = month_end_in(panel.dates, *_month(cfg["supplementary"]["t0_alt_month"]))
    supp["t0_alt"] = {"t0": t0_alt.isoformat(), "shares": _shares(decs, t0_alt, t1, cfg["models"])}
    for start in cfg["supplementary"]["windows"]:
        sub = panel.window(date.fromisoformat(start), panel.dates[-1])
        run = _estimate(sub, cfg, args.processes, [horizon], intervals=False)
        supp[f"window_{start}"] = _shares(run["decomposition"][horizon], t0, t1, cfg["models"])
    latest = _estimate(full, cfg, args.processes, [horizon], intervals=False)
    supp["t1_latest"] = {"t1": full.dates[-1].isoformat(), "shares": _shares(latest["decomposition"][horizon], t0, full.dates[-1], cfg["models"])}
    k3 = acm.fit_acm(panel, k=3)
    supp["acm_k3"] = acm.decompose_acm(panel, k3, horizon).share(t0, t1)
    long_panel = panel.window(date.fromisoformat(cfg["supplementary"]["long_acm_start"]), panel.dates[-1])
    long_fit = acm.fit_acm(long_panel, k=cfg["acm"]["k"], factor_months=acm.LONG_FACTOR_MONTHS, return_months=acm.LONG_RETURN_MONTHS)
    supp["long_acm"] = {f"maturity_{n}": acm.decompose_acm(long_panel, long_fit, n).share(t0, t1) for n in (120, 240, 360)}
    results["supplementary"] = supp

    (HERE / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verdict": results["verdict"], "main": results["main"]}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests and lint**

Run: `cd $WT && $PY -m pytest macrokit/tests/test_term_premium_research.py -q && /home/kazumasa/projects/.venv/bin/ruff format macrokit && /home/kazumasa/projects/.venv/bin/ruff check macrokit`
Expected: PASS (6 tests); lint clean.

- [ ] **Step 6: Commit, freeze, commit the frozen config**

```bash
cd $WT && git add macrokit/research/2026-10-jgb-term-premium/config.json macrokit/research/2026-10-jgb-term-premium/run_japan.py macrokit/tests/test_term_premium_research.py && git commit -m "Add the frozen-config runner for the Japanese decomposition"
cd $WT && $PY macrokit/research/2026-10-jgb-term-premium/run_japan.py --freeze && git add macrokit/research/2026-10-jgb-term-premium/config.json && git commit -m "Freeze the term-premium configuration before the Japanese run"
```

Expected: `frozen: <sha256>`. `freeze` refuses if macrokit code changed after the gates (then re-run Task 11 Step 7 first).

- [ ] **Step 7: Run once (about 10 minutes) and commit the results**

```bash
cd $WT && $PY macrokit/research/2026-10-jgb-term-premium/run_japan.py --data-root /home/kazumasa/projects/macrokit/data --processes 20 && git add macrokit/research/2026-10-jgb-term-premium/results.json && git commit -m "Record the Japanese term-premium decomposition"
```

Expected: a verdict label and four shares with intervals. Do not change any setting after this point; any follow-up is a new study with its own spec (design §2.4).

---

### Task 14: Write-up, docs, and hand-back

**Files:**
- Create: `macrokit/research/2026-10-jgb-term-premium/README.md`
- Modify: `macrokit/README.md`, `macrokit/docs/known-limitations.md`
- Modify: `docs/superpowers/specs/2026-10-17-jgb-term-premium-design.md` (§9, only if anything changed during Tasks 11–13)
- Modify (outside Git): `/home/kazumasa/.claude/projects/-home-kazumasa-projects/memory/project_macrokit.md` and its `MEMORY.md` line

- [ ] **Step 1: Write the research README in Japanese from `results.json`, `gates.json`, `small_sample.json`**

Sections: 問い（日銀レビューの記述の引用1文）／判定（ラベルと一文）／主表（モデル・s・90%区間・0.5を含むか・ゲート合否）／目安（タームプレミアム一定・据え置き予想）／ゲート結果（G1–G4 の数値と負の対照）／小標本バイアス（モデル別の平均誤差）／補足（5年、20・30年、推定期間、t0/t1 の別定義、K=3、シャドーレートの初期値別の s）／限界（設計書 §8 の4点と、実際に出た問題）／再現手順（Tasks 11–13 のコマンド）。Copy every number from the JSON files; do not round differently in different places (two decimals for shares, bp for errors).

- [ ] **Step 2: Update macrokit docs**

`macrokit/README.md`: add a section 「タームプレミアム分解（2026-10）」 with the three new CLI commands (`callrate`, `us-term`) and a link to the research README. `macrokit/docs/known-limitations.md`: add (1) call-rate anchor uses the monthly average before 1998; (2) GSW long maturities before 1971 are extrapolated by the Svensson parameters; (3) the Wu-Xia series stops at 2022-02; (4) `us-term` stores ~26 MB per refresh when files change.

- [ ] **Step 3: Full verification**

Run: `cd $WT && $PY -m pytest macrokit/tests -q && /home/kazumasa/projects/.venv/bin/ruff check macrokit && /home/kazumasa/projects/.venv/bin/ruff format --check macrokit && git status --short --ignored macrokit && du -sh /home/kazumasa/projects/macrokit/data`
Expected: tests pass; lint clean; no ignored files inside `$WT/macrokit` other than `__pycache__`; data well under 100 MB.

- [ ] **Step 4: Commit**

```bash
cd $WT && git add macrokit/research/2026-10-jgb-term-premium/README.md macrokit/README.md macrokit/docs/known-limitations.md docs/superpowers/specs/2026-10-17-jgb-term-premium-design.md && git commit -m "Write up the JGB term-premium re-test"
```

- [ ] **Step 5: Update memory and hand back**

Update `project_macrokit.md` with the verdict, the data facts that are not in the repo (none beyond the README — keep the memory to a pointer and the one-line verdict), and the `MEMORY.md` hook. Then report to the user: verdict, the four shares, gate outcomes, changed files, and ask for approval to merge `macrokit-term-premium` into `main` and push. Do not remove the worktree until the branch is merged and `git -C $WT status --ignored --short` shows nothing needed.
