# JP GDP Release / Rate-Response Dataset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a panel that pairs every Japanese real-GDP release since 2008 Q4 with the JGB curve move on the release day, so the rate response to a GDP surprise can be estimated.

**Architecture:** Four new adapters feed three new DuckDB tables alongside macrokit's existing point-in-time `observations` store. The MoF adapter loads the daily JGB curve, the ESRI calendar adapter loads observed release timestamps, the ESRI GDP adapter reconstructs true vintages by fetching each release's own statistical table, and an expectations layer computes four independent definitions of "what was expected". The event panel is a query, not a table, so the surprise normalisation and the change window stay changeable.

**Tech Stack:** Python 3.12+, DuckDB, pandas, httpx, pydantic, click, pytest. No new production dependencies — `xml.etree.ElementTree` and `csv` are stdlib. Task 8 needs a PDF reader and is gated on approval.

**Spec:** [`docs/superpowers/specs/2026-08-18-macrokit-gdp-release-study-design.md`](../specs/2026-08-18-macrokit-gdp-release-study-design.md)

## Global Constraints

- Run everything from the repo root: `uv run --no-sync pytest macrokit/tests`. Running `uv` inside `macrokit/` creates a stray venv.
- **No test may touch the network.** Every adapter is tested against a fixture under `macrokit/tests/fixtures/`. Live tests carry `@pytest.mark.live` and are skipped by default.
- **`release_date` is always timezone-aware `Asia/Tokyo`.** `store.py` rejects naive datetimes; do not work around it.
- Existing `observations` primary key is `(indicator, period_start, release_date)` and does **not** include `source`. Follow that convention: new tables carry `source`, `source_url`, `ingested_at` as provenance columns, not as key columns.
- `vintage_kind` ∈ `{"actual", "snapshot", "estimated"}`. GDP rows from the ESRI archive are `"actual"`.
- **Never forward-fill.** A missing observation stays missing.
- **Leak rule:** any expectation for a release at `T` may only read vintages with `release_date < T`. Use `pit.as_of()`; never read the release's own table for the prior quarter.
- Both MoF and ESRI CSVs are **CP932**. The ESRI calendar XML is **UTF-8 with CRLF**.
- Docs and comments in Japanese where the repo already uses Japanese; code, identifiers, and commit messages in English.
- Do not add a production dependency without asking.

---

## File Structure

| Path | Responsibility |
|---|---|
| `macrokit/src/macrokit/store.py` | *(modify)* DDL + insert helpers for `releases`, `market_rates`, `expectations` |
| `macrokit/src/macrokit/sources/mof_jgb.py` | *(new)* Fetch and parse the MoF JGB yield CSVs |
| `macrokit/src/macrokit/sources/esri_calendar.py` | *(new)* Parse the ESRI/e-Stat release-date XML |
| `macrokit/src/macrokit/sources/esri_gdp.py` | *(new)* Resolve a release's menu page, pick the series link, parse the CSV |
| `macrokit/src/macrokit/sources/esp.py` | *(new, Task 8)* ESP forecast consensus |
| `macrokit/src/macrokit/expectations.py` | *(new)* The four expectation methods and the `expectations` writer |
| `macrokit/src/macrokit/panel.py` | *(new)* The event-panel query |
| `macrokit/src/macrokit/release.py` | *(modify)* `month_offset` on release rules |
| `macrokit/src/macrokit/catalog.py` | *(modify)* `ReleaseRule.month_offset`, `release_lag_days` optional |
| `macrokit/catalog/jp/activity.yaml` | *(new)* The `jp_real_gdp_qoq_saar` entry |
| `macrokit/src/macrokit/cli.py` | *(modify)* `rates`, `releases`, `gdp`, `panel` commands |

Each source module owns exactly one upstream and exposes `fetch_raw` / `parse`, matching `sources/alfred.py`. Table DDL stays in `store.py` because `connect()` is the single place the schema is created.

---

## Task 1: MoF JGB yield adapter and the `market_rates` table

**Files:**
- Create: `macrokit/src/macrokit/sources/mof_jgb.py`
- Create: `macrokit/tests/test_mof_jgb.py`
- Create: `macrokit/tests/fixtures/mof_jgbcm_all.csv`
- Create: `macrokit/tests/fixtures/mof_jgbcm_current.csv`
- Modify: `macrokit/src/macrokit/store.py` (append DDL, add `RateObservation` + `insert_rates`)

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `store.RateObservation(curve: str, obs_date: date, tenor_y: float, yield_pct: float, source: str, source_url: str, ingested_at: datetime)`
  - `store.insert_rates(con, rows: list[RateObservation]) -> int`
  - `mof_jgb.parse_wareki(token: str) -> date`
  - `mof_jgb.parse_jgb_csv(content: bytes, *, source_url: str, ingested_at: datetime) -> list[RateObservation]`
  - `mof_jgb.MofJgbAdapter` with `source = "mof_jgb"`, `HISTORY_URL`, `CURRENT_URL`, `fetch_raw() -> list[tuple[bytes, str, int]]`, `parse(payloads, *, ingested_at) -> list[RateObservation]`

**Context:** The MoF publishes the JGB constant-maturity curve as two CSVs. `jgbcm_all.csv` holds history through the **end of the previous month** (13,272 rows on 2026-08-18, starting 1974-09-24). `jgbcm.csv` holds the **current month only** (13 lines when checked). Both are CP932, use Japanese era dates, and mark missing tenors with `-`. Tenor columns start at different dates — 10y from 1986-07-05, 30y from 1999-09-02, 25y from 2004-03-22, 40y from 2007-11-06 — so `-` means "this tenor did not exist yet", not "bad data".

- [ ] **Step 1: Write the fixtures**

`macrokit/tests/fixtures/mof_jgbcm_all.csv` — save as CP932, CRLF not required:

```
国債金利情報,,,,,,,,,,,,,,,(単位 : %)
基準日,1年,2年,3年,4年,5年,6年,7年,8年,9年,10年,15年,20年,25年,30年,40年
S49.9.24,10.327,9.362,8.83,8.515,8.348,8.29,8.24,8.121,8.127,-,-,-,-,-,-
H1.1.4,4.593,4.708,4.755,4.79,4.815,4.84,4.86,4.875,4.885,4.9,5.11,5.29,-,-,-
R8.7.31,1.255,1.507,1.658,1.876,2.044,2.19,2.343,2.517,2.658,2.801,3.382,3.69,3.987,3.982,3.967
```

`macrokit/tests/fixtures/mof_jgbcm_current.csv` — note the blank line and the trailing notice, both of which the real file has:

```
国債金利情報 (令和8年8月),,,,,,,,,,,,,,,(単位 : %)
基準日,1年,2年,3年,4年,5年,6年,7年,8年,9年,10年,15年,20年,25年,30年,40年
R8.8.14,1.412,1.657,1.818,2.011,2.151,2.294,2.432,2.599,2.736,2.878,3.431,3.75,4.024,4.002,4.006
R8.8.17,1.425,1.697,1.86,2.05,2.19,2.33,2.47,2.64,2.78,2.93,3.47,3.79,4.06,4.04,4.04
,,,,,,,,,,,,,,,
※最新のcsvデータがダウンロードできない場合、ご利用のブラウザにおいてキャッシュの削除を実施し再度ダウンロードください。,,,,,,,,,,,,,,,
```

Write them with a short script so the encoding is unambiguous:

```python
from pathlib import Path
Path("macrokit/tests/fixtures/mof_jgbcm_all.csv").write_text(TEXT, encoding="cp932")
```

- [ ] **Step 2: Write the failing tests**

`macrokit/tests/test_mof_jgb.py`:

```python
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.sources import mof_jgb

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("S49.9.24", date(1974, 9, 24)),
        ("H1.1.4", date(1989, 1, 4)),
        ("R8.7.31", date(2026, 7, 31)),
    ],
)
def test_parse_wareki_covers_every_era_in_the_file(token, expected):
    assert mof_jgb.parse_wareki(token) == expected


def test_parse_skips_the_title_row_and_reads_every_tenor():
    content = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    latest = {r.tenor_y: r.yield_pct for r in rows if r.obs_date == date(2026, 7, 31)}
    assert len(latest) == 15
    assert latest[10.0] == 2.801
    assert latest[40.0] == 3.967


def test_a_missing_tenor_produces_no_row_rather_than_a_zero():
    content = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    oldest = {r.tenor_y for r in rows if r.obs_date == date(1974, 9, 24)}
    assert oldest == {1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0}
    assert 10.0 not in oldest


def test_the_current_month_trailer_and_blank_line_are_not_parsed_as_data():
    content = (FIXTURES / "mof_jgbcm_current.csv").read_bytes()
    rows = mof_jgb.parse_jgb_csv(content, source_url="u", ingested_at=NOW)

    assert {r.obs_date for r in rows} == {date(2026, 8, 14), date(2026, 8, 17)}


def test_the_two_files_are_unioned_without_duplicating_a_date():
    history = (FIXTURES / "mof_jgbcm_all.csv").read_bytes()
    current = (FIXTURES / "mof_jgbcm_current.csv").read_bytes()
    adapter = mof_jgb.MofJgbAdapter()

    rows = adapter.parse(
        [(history, "history-url", 200), (current, "current-url", 200)],
        ingested_at=NOW,
    )

    keys = [(r.obs_date, r.tenor_y) for r in rows]
    assert len(keys) == len(set(keys))
    assert date(2026, 8, 17) in {r.obs_date for r in rows}
    assert date(1974, 9, 24) in {r.obs_date for r in rows}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_mof_jgb.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.sources.mof_jgb'`

- [ ] **Step 4: Add the table and row type to `store.py`**

Append to `SCHEMA_SQL` in `macrokit/src/macrokit/store.py`:

```sql
CREATE TABLE IF NOT EXISTS market_rates (
  curve       VARCHAR NOT NULL,
  obs_date    DATE    NOT NULL,
  tenor_y     DOUBLE  NOT NULL,
  yield_pct   DOUBLE  NOT NULL,
  source      VARCHAR NOT NULL,
  source_url  VARCHAR NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (curve, obs_date, tenor_y)
);
```

Add alongside `Observation`:

```python
@dataclass(frozen=True)
class RateObservation:
    curve: str
    obs_date: date
    tenor_y: float
    yield_pct: float
    source: str
    source_url: str
    ingested_at: datetime


def insert_rates(con: duckdb.DuckDBPyConnection, rows: list[RateObservation]) -> int:
    """Insert rate observations, ignoring rows whose key is already present."""
    if not rows:
        return 0
    for row in rows:
        if _is_naive(row.ingested_at):
            raise ValueError(
                f"insert_rates: ingested_at must be timezone-aware, got {row.ingested_at!r}"
            )
    before = con.execute("SELECT count(*) FROM market_rates").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO market_rates VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (r.curve, r.obs_date, r.tenor_y, r.yield_pct, r.source, r.source_url, r.ingested_at)
            for r in rows
        ],
    )
    after = con.execute("SELECT count(*) FROM market_rates").fetchone()[0]
    return after - before
```

- [ ] **Step 5: Write the adapter**

`macrokit/src/macrokit/sources/mof_jgb.py`:

```python
"""MoF JGB constant-maturity yields from two public CSVs (no API key).

The ministry splits the curve across two files: ``jgbcm_all.csv`` ends at the
previous month-end and ``jgbcm.csv`` carries the current month. Both must be
read and unioned, or the most recent weeks are silently absent.

Yields are not revised, so these rows carry no vintage key -- see the spec's
data-model section for why they live outside ``observations``.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime

import httpx

from ..store import RateObservation

BASE = "https://www.mof.go.jp/jgbs/reference/interest_rate"
HISTORY_URL = f"{BASE}/data/jgbcm_all.csv"
CURRENT_URL = f"{BASE}/jgbcm.csv"

# Gregorian year = era offset + era year. 1925 + 49 = 1974 (Showa 49).
ERA_OFFSET = {"S": 1925, "H": 1988, "R": 2018}

MISSING = "-"


class MofJgbError(RuntimeError):
    """The MoF payload could not be fetched or parsed."""


def parse_wareki(token: str) -> date:
    """``R8.7.31`` -> ``date(2026, 7, 31)``."""
    token = token.strip()
    era = token[:1]
    if era not in ERA_OFFSET:
        raise MofJgbError(f"unknown era prefix in date {token!r}; known: {sorted(ERA_OFFSET)}")
    try:
        year, month, day = (int(part) for part in token[1:].split("."))
    except ValueError as exc:
        raise MofJgbError(f"malformed wareki date: {token!r}") from exc
    return date(ERA_OFFSET[era] + year, month, day)


def _tenor_of(header_cell: str) -> float:
    """``10年`` -> ``10.0``."""
    return float(header_cell.strip().removesuffix("年"))


def parse_jgb_csv(
    content: bytes, *, source_url: str, ingested_at: datetime
) -> list[RateObservation]:
    text = content.decode("cp932")
    reader = list(csv.reader(io.StringIO(text)))
    if len(reader) < 2:
        raise MofJgbError(f"payload from {source_url} has no header row")

    # Row 0 is a title banner; row 1 is the real header.
    tenors = [_tenor_of(cell) for cell in reader[1][1:] if cell.strip()]

    rows: list[RateObservation] = []
    for record in reader[2:]:
        if not record or not record[0].strip():
            continue  # blank separator line before the trailing notice
        if not record[0][:1] in ERA_OFFSET:
            continue  # the trailing "※..." notice line
        obs_date = parse_wareki(record[0])
        for tenor, cell in zip(tenors, record[1:], strict=False):
            value = cell.strip()
            if value == MISSING or not value:
                continue  # this tenor did not exist on this date
            rows.append(
                RateObservation(
                    curve="jgb",
                    obs_date=obs_date,
                    tenor_y=tenor,
                    yield_pct=float(value),
                    source="mof_jgb",
                    source_url=source_url,
                    ingested_at=ingested_at,
                )
            )
    return rows


class MofJgbAdapter:
    source = "mof_jgb"
    HISTORY_URL = HISTORY_URL
    CURRENT_URL = CURRENT_URL

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> list[tuple[bytes, str, int]]:
        payloads: list[tuple[bytes, str, int]] = []
        with httpx.Client(timeout=self._timeout) as client:
            for url in (self.HISTORY_URL, self.CURRENT_URL):
                response = client.get(url)
                if response.status_code != 200:
                    raise MofJgbError(f"GET {url} returned {response.status_code}")
                payloads.append((response.content, url, response.status_code))
        return payloads

    def parse(
        self, payloads: list[tuple[bytes, str, int]], *, ingested_at: datetime
    ) -> list[RateObservation]:
        """Union the payloads, keeping the first row seen for a (date, tenor)."""
        seen: dict[tuple[date, float], RateObservation] = {}
        for content, url, _status in payloads:
            for row in parse_jgb_csv(content, source_url=url, ingested_at=ingested_at):
                seen.setdefault((row.obs_date, row.tenor_y), row)
        return sorted(seen.values(), key=lambda r: (r.obs_date, r.tenor_y))
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_mof_jgb.py macrokit/tests/test_store.py -q`
Expected: PASS

- [ ] **Step 7: Confirm the real feed still matches the fixture's shape**

This is the spec's open item 3 (the MoF update lag). Run once, by hand, and record the answer in a comment at the top of the test file:

```bash
uv run --no-sync python -c "
import httpx
from datetime import UTC, datetime
from macrokit.sources.mof_jgb import MofJgbAdapter
rows = MofJgbAdapter().parse(MofJgbAdapter().fetch_raw(), ingested_at=datetime.now(UTC))
print('rows:', len(rows), 'latest:', max(r.obs_date for r in rows))
"
```

Expected: `latest` is within a few business days of today. If it lags by more than a week, note it — a daily batch cannot assume same-day data.

- [ ] **Step 8: Commit**

```bash
git add macrokit/src/macrokit/sources/mof_jgb.py macrokit/src/macrokit/store.py \
        macrokit/tests/test_mof_jgb.py macrokit/tests/fixtures/mof_jgbcm_all.csv \
        macrokit/tests/fixtures/mof_jgbcm_current.csv
git commit -m "Load the JGB constant-maturity curve from the MoF's two CSVs"
```

---

## Task 2: Release-rule month offset and the JP GDP catalog entry

**Files:**
- Modify: `macrokit/src/macrokit/catalog.py` (`ReleaseRule`, `Indicator`)
- Modify: `macrokit/src/macrokit/release.py` (`_month_after` → offset-aware)
- Modify: `macrokit/tests/test_release.py`, `macrokit/tests/test_catalog.py`
- Create: `macrokit/catalog/jp/activity.yaml`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `ReleaseRule.month_offset: int = 1`
  - `Indicator.release_lag_days: int | None = None`
  - catalog entry `jp_real_gdp_qoq_saar`, consumed by Tasks 3–7.

**Context:** This closes `macrokit/docs/known-limitations.md` §3. `release._month_after` is hard-coded to the month after the period ends, so Japan's GDP first preliminary (about 1.5 months later), 法人企業統計 (about 2 months) and 日銀短観 are inexpressible. Separately, `release_lag_days` is a required catalog field with **zero readers anywhere in the code**, which forces every entry to carry a value nothing consults.

**Ruling carried into this task:** GDP itself does **not** use a computed rule. Its 148 exact timestamps come from the XML in Task 3, so its catalog entry uses `kind: manual`. `month_offset` is still added and tested here because it is the documented blocker for the rest of Phase 2's JP catalog, and because leaving a known-wrong schema in place while adding JP entries on top of it is what the limitation warned against.

- [ ] **Step 1: Write the failing tests**

Append to `macrokit/tests/test_release.py`:

```python
def test_month_offset_two_expresses_a_two_month_publication_lag():
    """法人企業統計 publishes about two months after the quarter ends."""
    rule = ReleaseRule(kind="fixed_day", day=1, month_offset=2)
    assert resolve_release(rule, date(2026, 6, 30), holidays=set()).date() == date(2026, 8, 1)


def test_month_offset_defaults_to_one_so_existing_rules_are_unchanged():
    rule = ReleaseRule(kind="fixed_day", day=10)
    assert resolve_release(rule, date(2026, 6, 30), holidays=set()).date() == date(2026, 7, 10)


def test_month_offset_rolls_over_the_year_boundary():
    rule = ReleaseRule(kind="fixed_day", day=15, month_offset=2)
    assert resolve_release(rule, date(2026, 12, 31), holidays=set()).date() == date(2027, 2, 15)


def test_month_offset_must_be_positive():
    with pytest.raises(ValidationError):
        ReleaseRule(kind="fixed_day", day=1, month_offset=0)
```

Append to `macrokit/tests/test_catalog.py`:

```python
def test_release_lag_days_is_optional_now_that_release_rule_carries_the_schedule():
    indicator = Indicator(
        name="x", country="JP", block="activity", title_ja="x", source="s",
        source_ref={}, freq="Q", unit="u", sa="sa", vintage="snapshot",
        release_rule=ReleaseRule(kind="manual"),
    )
    assert indicator.release_lag_days is None


def test_an_indicator_must_carry_at_least_one_schedule_hint():
    with pytest.raises(ValidationError):
        Indicator(
            name="x", country="JP", block="activity", title_ja="x", source="s",
            source_ref={}, freq="Q", unit="u", sa="sa", vintage="snapshot",
        )


def test_the_jp_gdp_entry_loads_from_the_shipped_catalog():
    catalog = load_catalog(Path(__file__).parents[1] / "catalog")
    entry = catalog["jp_real_gdp_qoq_saar"]
    assert entry.country == "JP"
    assert entry.freq == "Q"
    assert entry.unit == "percent_saar"
    assert entry.release_rule is not None
    assert entry.release_rule.kind == "manual"
    assert entry.release_rule.time == "08:50"
```

Add the imports each test file needs (`pytest`, `ValidationError` from `pydantic`, `Indicator`/`ReleaseRule`/`load_catalog` from `macrokit.catalog`, `Path`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_release.py macrokit/tests/test_catalog.py -q`
Expected: FAIL — `ValidationError: Extra inputs are not permitted [month_offset]`, and `KeyError: 'jp_real_gdp_qoq_saar'`.

- [ ] **Step 3: Extend `ReleaseRule` and `Indicator`**

In `macrokit/src/macrokit/catalog.py`, add to `ReleaseRule`:

```python
    month_offset: int = Field(
        default=1,
        ge=1,
        description=(
            "Months between the end of the reference period and the publication "
            "month. 1 = the month after (most monthly statistics); 2 = Japan's "
            "quarterly GDP first preliminary and 法人企業統計."
        ),
    )
```

Change `Indicator.release_lag_days` to `int | None = None` and add a model validator:

```python
    @model_validator(mode="after")
    def _require_a_schedule_hint(self) -> "Indicator":
        if self.release_lag_days is None and self.release_rule is None:
            raise ValueError(
                f"{self.name}: set release_rule (preferred) or release_lag_days. "
                "Neither is set, so nothing describes when this indicator publishes."
            )
        return self
```

Import `model_validator` from `pydantic`.

- [ ] **Step 4: Use the offset in `release.py`**

Replace `_month_after` and its call site:

```python
def _publication_month(period_end: date, month_offset: int) -> tuple[int, int]:
    """The (year, month) ``month_offset`` months after the month ``period_end`` falls in."""
    zero_based = period_end.month - 1 + month_offset
    return period_end.year + zero_based // 12, zero_based % 12 + 1
```

and in `resolve_release`, replace `year, month = _month_after(period_end)` with:

```python
    year, month = _publication_month(period_end, rule.month_offset)
```

- [ ] **Step 5: Write the catalog entry**

`macrokit/catalog/jp/activity.yaml`:

```yaml
- name: jp_real_gdp_qoq_saar
  country: JP
  block: activity
  title_ja: 実質GDP 前期比年率（季節調整済、1次・2次速報）
  source: esri_gdp
  source_ref:
    series_label: 年率換算の実質季節調整系列(前期比)
    stem_prefix: nritu
    column: 国内総生産(支出側)
  freq: Q
  unit: percent_saar
  sa: sa
  release_rule:
    kind: manual
    time: "08:50"
    month_offset: 2
  vintage: snapshot
  caveats:
    - 公表日は内閣府の e-stat_sna.xml から実測値を取り込む。month_offset は目安で、resolve_release は manual なので None を返す
    - メニューページに同じラベルのリンクが2本ある。語幹が knritu のものは参考系列なので選んではならない
    - 各リリースの表はその時点の全期間を含む。1回の取り込みで1994年以降の系列が1つの vintage として入る
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests -q`
Expected: PASS. The existing US entry keeps `release_lag_days: 30` and still validates.

- [ ] **Step 7: Close the limitation entry**

In `macrokit/docs/known-limitations.md`, replace section 3's body with a note that `month_offset` now exists, that `release_lag_days` is optional, and that the remaining open piece is `ReleaseRule.calendar` (§2). Keep the heading numbering intact.

- [ ] **Step 8: Commit**

```bash
git add macrokit/src/macrokit/catalog.py macrokit/src/macrokit/release.py \
        macrokit/catalog/jp/activity.yaml macrokit/tests/test_release.py \
        macrokit/tests/test_catalog.py macrokit/docs/known-limitations.md
git commit -m "Let a release rule publish more than one month after its period"
```

---

## Task 3: ESRI release-calendar XML and the `releases` table

**Files:**
- Create: `macrokit/src/macrokit/sources/esri_calendar.py`
- Create: `macrokit/tests/test_esri_calendar.py`
- Create: `macrokit/tests/fixtures/esri_sna_calendar.xml`
- Modify: `macrokit/src/macrokit/store.py`

**Interfaces:**
- Consumes: catalog entry `jp_real_gdp_qoq_saar` (Task 2).
- Produces:
  - `store.ReleaseEvent(indicator, period_start, period_end, release_kind, release_date, scheduled, source, source_url, ingested_at)`
  - `store.insert_releases(con, rows: list[ReleaseEvent]) -> int`
  - `esri_calendar.parse_period_name(name: str) -> tuple[date, date]`
  - `esri_calendar.parse_calendar_xml(content, *, indicator, source_url, ingested_at) -> list[ReleaseEvent]`
  - `esri_calendar.EsriCalendarAdapter` with `source = "esri_calendar"`, `XML_URL`, `fetch_raw()`, `parse()`

**Context — measured facts about the real XML (2026-08-18):**

| Fact | Value |
|---|---|
| URL | `https://www.esri.cao.go.jp/jp/sna/e-stat_sna.xml` |
| Sibling files | `e-stat_sna2.xml`…`e-stat_sna4.xml` exist but hold **no** GDP entries — do not fetch them |
| Encoding | UTF-8, CRLF line endings |
| Path | `e-stat/os_code/class_1/class_2/class_3/class_4/class_5/release_*` |
| GDP entries | 148 |
| `class_1/@name` | `四半期別ＧＤＰ速報` — **ＧＤＰ is full-width** |
| `class_3/@name` | `1次速報` ×73, `2次速報` ×73, `2次速報（改定値）` ×2 |
| `class_2/@name` | `平成N年N-N月期` ×82 and `N年N-N月期` ×66; the switch happens at the 2019-05-20 release and **no 令和 form ever appears** |
| Date parts | five separate elements, not zero-padded (`<release_month>2</release_month>`) |
| Time | `8:50` on all 148 |
| Range | 2009-02-16 … 2027-03-09 (the tail is scheduled, not released) |

- [ ] **Step 1: Write the fixture**

`macrokit/tests/fixtures/esri_sna_calendar.xml`, UTF-8. It carries one entry of every shape that exists in the real file — both period-name forms, all three kinds, and a future-dated row:

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<e-stat>
<os_code id="00100409" name="国民経済計算" count_number="3">
<update_year>2026</update_year><update_month>8</update_month><update_day>17</update_day>
<class_1 name="四半期別ＧＤＰ速報">
<class_2 name="平成20年10-12月期">
<class_3 name="1次速報"><class_4 name=""><class_5 name="">
<release_year>2009</release_year><release_month>2</release_month><release_day>16</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
<class_3 name="2次速報"><class_4 name=""><class_5 name="">
<release_year>2009</release_year><release_month>3</release_month><release_day>12</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
</class_2>
<class_2 name="2020年1-3月期">
<class_3 name="2次速報（改定値）"><class_4 name=""><class_5 name="">
<release_year>2020</release_year><release_month>8</release_month><release_day>3</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
</class_2>
<class_2 name="2026年4-6月期">
<class_3 name="1次速報"><class_4 name=""><class_5 name="">
<release_year>2026</release_year><release_month>8</release_month><release_day>17</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
</class_2>
<class_2 name="2026年10-12月期">
<class_3 name="2次速報"><class_4 name=""><class_5 name="">
<release_year>2027</release_year><release_month>3</release_month><release_day>9</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
</class_2>
</class_1>
<class_1 name="民間企業資本ストック速報">
<class_2 name="平成20年1-3月期">
<class_3 name=""><class_4 name=""><class_5 name="">
<release_year>2008</release_year><release_month>6</release_month><release_day>10</release_day>
<release_hour>8</release_hour><release_minute>50</release_minute>
</class_5></class_4></class_3>
</class_2>
</class_1>
</os_code>
</e-stat>
```

- [ ] **Step 2: Write the failing tests**

`macrokit/tests/test_esri_calendar.py`:

```python
from datetime import UTC, date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from macrokit.sources import esri_calendar

FIXTURES = Path(__file__).parent / "fixtures"
JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _events():
    content = (FIXTURES / "esri_sna_calendar.xml").read_bytes()
    return esri_calendar.parse_calendar_xml(
        content, indicator="jp_real_gdp_qoq_saar", source_url="u", ingested_at=NOW
    )


@pytest.mark.parametrize(
    ("name", "start", "end"),
    [
        ("平成20年10-12月期", date(2008, 10, 1), date(2008, 12, 31)),
        ("2026年4-6月期", date(2026, 4, 1), date(2026, 6, 30)),
        ("2026年10-12月期", date(2026, 10, 1), date(2026, 12, 31)),
    ],
)
def test_parse_period_name_handles_both_era_and_western_forms(name, start, end):
    assert esri_calendar.parse_period_name(name) == (start, end)


def test_only_the_quarterly_gdp_branch_is_read():
    """民間企業資本ストック速報 shares the file and must not leak into releases."""
    assert len(_events()) == 5


def test_the_three_release_kinds_are_mapped():
    kinds = sorted({e.release_kind for e in _events()})
    assert kinds == ["1st_prelim", "2nd_prelim", "2nd_prelim_revised"]


def test_release_datetimes_are_jst_aware_at_0850():
    event = next(e for e in _events() if e.period_start == date(2026, 4, 1))
    assert event.release_date == datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    assert event.release_kind == "1st_prelim"


def test_a_future_dated_row_is_marked_scheduled():
    future = next(e for e in _events() if e.period_start == date(2026, 10, 1))
    past = next(e for e in _events() if e.period_start == date(2026, 4, 1))
    assert future.scheduled is True
    assert past.scheduled is False


def test_a_half_width_gdp_name_finds_nothing():
    """The statistic is named with a full-width ＧＤＰ; guard the constant."""
    assert "ＧＤＰ" in esri_calendar.GDP_CLASS_1
    assert "GDP" not in esri_calendar.GDP_CLASS_1
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_esri_calendar.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.sources.esri_calendar'`

- [ ] **Step 4: Add the table and row type to `store.py`**

Append to `SCHEMA_SQL`:

```sql
CREATE TABLE IF NOT EXISTS releases (
  indicator     VARCHAR     NOT NULL,
  period_start  DATE        NOT NULL,
  period_end    DATE        NOT NULL,
  release_kind  VARCHAR     NOT NULL,
  release_date  TIMESTAMPTZ NOT NULL,
  scheduled     BOOLEAN     NOT NULL,
  source        VARCHAR     NOT NULL,
  source_url    VARCHAR     NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (indicator, period_start, release_kind)
);
```

Add `RELEASE_KINDS = frozenset({"1st_prelim", "2nd_prelim", "2nd_prelim_revised"})`, the `ReleaseEvent` dataclass with the fields listed in **Interfaces**, and `insert_releases`, mirroring `insert_rates`: reject naive `release_date` and `ingested_at`, reject a `release_kind` outside `RELEASE_KINDS`, then `INSERT OR IGNORE` and return the row-count delta.

- [ ] **Step 5: Write the adapter**

`macrokit/src/macrokit/sources/esri_calendar.py`:

```python
"""Observed publication timestamps for Japan's quarterly GDP, from ESRI's e-Stat feed.

This is the *observed* calendar, not a rule: ``release.resolve_release`` predicts
future dates from a ``ReleaseRule``, whereas this module records what actually
happened. GDP's rule is ``manual`` precisely because these 148 exact timestamps
exist.

The feed carries scheduled and released rows in an identical shape with nothing
to distinguish them, so ``scheduled`` can only mean "still in the future when we
read it".
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx

from ..store import ReleaseEvent

XML_URL = "https://www.esri.cao.go.jp/jp/sna/e-stat_sna.xml"

# The ministry writes the statistic's name with a full-width ＧＤＰ. A half-width
# "GDP" matches nothing, and the mismatch is invisible in most editors.
GDP_CLASS_1 = "四半期別ＧＤＰ速報"

KIND_MAP = {
    "1次速報": "1st_prelim",
    "2次速報": "2nd_prelim",
    "2次速報（改定値）": "2nd_prelim_revised",
}

JST = ZoneInfo("Asia/Tokyo")

# 平成20年10-12月期 / 2026年4-6月期. Era years appear up to the 2019-05-20
# release and 令和 never appears at all -- they switched straight to western
# years -- so only 平成 needs an offset.
_PERIOD_RE = re.compile(r"^(?:(平成)(\d+)|(\d{4}))年(\d+)-(\d+)月期$")
_HEISEI_OFFSET = 1988

_QUARTER_END_DAY = {3: 31, 6: 30, 9: 30, 12: 31}


class EsriCalendarError(RuntimeError):
    """The calendar payload could not be fetched or parsed."""


def parse_period_name(name: str) -> tuple[date, date]:
    """``平成20年10-12月期`` -> ``(2008-10-01, 2008-12-31)``."""
    match = _PERIOD_RE.match(name.strip())
    if match is None:
        raise EsriCalendarError(f"unrecognised reference-period name: {name!r}")
    era, era_year, western, start_month, end_month = match.groups()
    year = _HEISEI_OFFSET + int(era_year) if era else int(western)
    start = date(year, int(start_month), 1)
    end_month_i = int(end_month)
    if end_month_i not in _QUARTER_END_DAY:
        raise EsriCalendarError(f"period {name!r} does not end on a quarter boundary")
    return start, date(year, end_month_i, _QUARTER_END_DAY[end_month_i])


def parse_calendar_xml(
    content: bytes, *, indicator: str, source_url: str, ingested_at: datetime
) -> list[ReleaseEvent]:
    root = ET.fromstring(content)
    events: list[ReleaseEvent] = []
    for class_1 in root.iter("class_1"):
        if class_1.get("name") != GDP_CLASS_1:
            continue
        for class_2 in class_1.findall("class_2"):
            period_start, period_end = parse_period_name(class_2.get("name", ""))
            for class_3 in class_2.findall("class_3"):
                raw_kind = class_3.get("name", "")
                if raw_kind not in KIND_MAP:
                    raise EsriCalendarError(
                        f"unknown release kind {raw_kind!r} for {class_2.get('name')!r}; "
                        f"known: {sorted(KIND_MAP)}"
                    )
                for class_5 in class_3.iter("class_5"):
                    release_date = _release_datetime(class_5)
                    events.append(
                        ReleaseEvent(
                            indicator=indicator,
                            period_start=period_start,
                            period_end=period_end,
                            release_kind=KIND_MAP[raw_kind],
                            release_date=release_date,
                            scheduled=release_date > ingested_at,
                            source="esri_calendar",
                            source_url=source_url,
                            ingested_at=ingested_at,
                        )
                    )
    return events


def _release_datetime(class_5: ET.Element) -> datetime:
    def part(tag: str) -> int:
        text = class_5.findtext(tag)
        if text is None or not text.strip():
            raise EsriCalendarError(f"release entry is missing <{tag}>")
        return int(text)

    return datetime(
        part("release_year"), part("release_month"), part("release_day"),
        part("release_hour"), part("release_minute"), tzinfo=JST,
    )


class EsriCalendarAdapter:
    source = "esri_calendar"
    XML_URL = XML_URL

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_raw(self) -> tuple[bytes, str, int]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(self.XML_URL)
        if response.status_code != 200:
            raise EsriCalendarError(f"GET {self.XML_URL} returned {response.status_code}")
        return response.content, self.XML_URL, response.status_code

    def parse(
        self, content: bytes, *, indicator: str, source_url: str, ingested_at: datetime
    ) -> list[ReleaseEvent]:
        return parse_calendar_xml(
            content, indicator=indicator, source_url=source_url, ingested_at=ingested_at
        )
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_esri_calendar.py macrokit/tests/test_store.py -q`
Expected: PASS

- [ ] **Step 7: Add a live test pinning the real counts**

Append to `macrokit/tests/test_esri_calendar.py`:

```python
@pytest.mark.live
def test_the_live_feed_still_has_the_counts_the_spec_measured():
    adapter = esri_calendar.EsriCalendarAdapter()
    content, url, _ = adapter.fetch_raw()
    events = adapter.parse(
        content, indicator="jp_real_gdp_qoq_saar", source_url=url,
        ingested_at=datetime.now(UTC),
    )
    kinds = Counter(e.release_kind for e in events)
    assert kinds["1st_prelim"] >= 73
    assert kinds["2nd_prelim"] >= 73
    assert kinds["2nd_prelim_revised"] == 2
    assert min(e.release_date.date() for e in events) == date(2009, 2, 16)
```

Import `Counter` from `collections`. The `>=` guards let the feed grow; the `== 2` catches a new off-cycle revision, which is exactly the event worth being told about.

- [ ] **Step 8: Commit**

```bash
git add macrokit/src/macrokit/sources/esri_calendar.py macrokit/src/macrokit/store.py \
        macrokit/tests/test_esri_calendar.py macrokit/tests/fixtures/esri_sna_calendar.xml
git commit -m "Record the observed GDP publication timestamps from ESRI's feed"
```

---

## Task 4: ESRI GDP vintage adapter

**Files:**
- Create: `macrokit/src/macrokit/sources/esri_gdp.py`
- Create: `macrokit/tests/test_esri_gdp.py`
- Create: `macrokit/tests/fixtures/esri_gdemenuja.html`
- Create: `macrokit/tests/fixtures/esri_nritu_jk.csv`

**Interfaces:**
- Consumes: `store.ReleaseEvent` (Task 3), catalog entry `jp_real_gdp_qoq_saar` (Task 2).
- Produces:
  - `esri_gdp.menu_url(period_start: date, release_kind: str) -> str`
  - `esri_gdp.select_series_url(menu_html: bytes, menu_url: str, *, series_label: str, stem_prefix: str) -> str`
  - `esri_gdp.parse_nritu_csv(content: bytes, *, column: str) -> dict[date, float]`
  - `esri_gdp.EsriGdpAdapter.fetch_release(event) -> tuple[bytes, str, int]`
  - `esri_gdp.EsriGdpAdapter.parse(event, content, *, indicator, source_url, ingested_at) -> list[Observation]`

**Context — measured facts (2026-08-18):**

The **menu page** URL is stable across the whole range. Verified to resolve for 2008 Q4, 2009 Q1, 2019 Q1 second preliminary, 2025 Q4 and 2026 Q2:

```
https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/{period_year}/qe{YY}{Q}{suffix}/gdemenuja.html
    period_year = the period's year, NOT the release year
    YY          = last two digits of the period's year, zero-padded
    Q           = quarter 1..4
    suffix      = "" for 1st_prelim, "_2" for 2nd_prelim
```

The **data CSV URL is not stable and must never be constructed**:

| Era | Observed path |
|---|---|
| 2009 | `/jp/sna/content/20120227_nritu_jk0911.csv` |
| 2026 | `tables/nritu-jk2621.csv` |

**Two traps in selecting the link.** Both eras publish *two* links whose label is `年率換算の実質季節調整系列(前期比)` — one with basename stem `nritu`, one with `knritu`. The `knritu` file is a reference series with different numbers. Match the label **and** require the stem to start with `nritu`. And take the column by its header text `国内総生産(支出側)`, never by position.

**CSV shape** (measured on 2026 Q2 first preliminary): CP932, 138 lines, header rows 0–6, data from row 7 starting at 1994 Q1, one trailing note line. Reference-period labels are `1994/ 1- 3.` then `4- 6.`, `7- 9.`, `10-12.` — **the year appears only on Q1 and carries forward**. Missing values are `***`; numbers carry a trailing space.

- [ ] **Step 1: Write the fixtures**

`macrokit/tests/fixtures/esri_gdemenuja.html` — reproduces the duplicate-label trap:

```html
<html><body>
<a href="tables/gaku-jk2621.csv">実質季節調整系列（CSV形式：42KB）</a>
<a href="tables/nritu-jk2621.csv">年率換算の実質季節調整系列(前期比)（CSV形式：17KB）</a>
<a href="tables/nritu-mk2621.csv">年率換算の名目季節調整系列(前期比)（CSV形式：17KB）</a>
<a href="tables/knritu-jk2621.csv">年率換算の実質季節調整系列(前期比)（CSV形式：7KB）</a>
</body></html>
```

`macrokit/tests/fixtures/esri_nritu_jk.csv` — CP932, keeping the real header depth, the carried-forward year, `***`, and the trailing note:

```
実質季節調整系列(年率),,,,,(単位:％)
"Real, Seasonally Adjusted Series (Quarter-to-Quarter Percent Change, Annualized)",,,,,(%)
,国内総生産(支出側),民間最終消費支出,,民間企業設備,公的在庫変動
,,,家計最終消費支出,,
,,,,,
,GDP(Expenditure Approach),PrivateConsumption,Consumption ofHouseholds,Private Non-Resi.Investment,Public Inventories
,,,,,
1994/ 1- 3.,,,,,
4- 6.,-3.0 ,1.9 ,1.8 ,-5.1 ,***
7- 9.,4.1 ,3.1 ,3.2 ,-2.4 ,***
10-12.,-1.5 ,0.3 ,0.2 ,4.6 ,***
1995/ 1- 3.,3.9 ,3.1 ,3.1 ,5.5 ,***
2026/ 1- 3.,1.9 ,1.9 ,1.8 ,-3.8 ,***
4- 6.,1.1 ,-0.1 ,-0.3 ,-4.6 ,***
＊年率表示の成長率は、実質季節調整値を用いて次式により算出した。,,,,,
```

- [ ] **Step 2: Write the failing tests**

`macrokit/tests/test_esri_gdp.py`:

```python
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.sources import esri_gdp

FIXTURES = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
MENU = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262/gdemenuja.html"


@pytest.mark.parametrize(
    ("period_start", "kind", "tail"),
    [
        (date(2026, 4, 1), "1st_prelim", "files/2026/qe262/gdemenuja.html"),
        (date(2026, 1, 1), "2nd_prelim", "files/2026/qe261_2/gdemenuja.html"),
        (date(2008, 10, 1), "1st_prelim", "files/2008/qe084/gdemenuja.html"),
        (date(2025, 10, 1), "1st_prelim", "files/2025/qe254/gdemenuja.html"),
    ],
)
def test_menu_url_keys_on_the_period_year_not_the_release_year(period_start, kind, tail):
    assert esri_gdp.menu_url(period_start, kind).endswith(tail)


def test_a_revised_second_preliminary_has_no_derivable_menu_url():
    with pytest.raises(esri_gdp.EsriGdpError, match="2nd_prelim_revised"):
        esri_gdp.menu_url(date(2020, 1, 1), "2nd_prelim_revised")


def test_the_reference_series_with_the_same_label_is_not_selected():
    html = (FIXTURES / "esri_gdemenuja.html").read_bytes()
    url = esri_gdp.select_series_url(
        html, MENU,
        series_label="年率換算の実質季節調整系列(前期比)",
        stem_prefix="nritu",
    )
    assert url.endswith("/tables/nritu-jk2621.csv")
    assert "knritu" not in url


def test_a_relative_href_is_resolved_against_the_menu_url():
    html = (FIXTURES / "esri_gdemenuja.html").read_bytes()
    url = esri_gdp.select_series_url(
        html, MENU,
        series_label="年率換算の実質季節調整系列(前期比)",
        stem_prefix="nritu",
    )
    assert url.startswith("https://www.esri.cao.go.jp/")


def test_the_carried_forward_year_is_applied_to_later_quarters():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    series = esri_gdp.parse_nritu_csv(content, column="国内総生産(支出側)")

    assert series[date(1994, 4, 1)] == -3.0
    assert series[date(1994, 10, 1)] == -1.5
    assert series[date(2026, 1, 1)] == 1.9
    assert series[date(2026, 4, 1)] == 1.1


def test_an_empty_first_quarter_produces_no_entry():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    series = esri_gdp.parse_nritu_csv(content, column="国内総生産(支出側)")
    assert date(1994, 1, 1) not in series


def test_the_column_is_chosen_by_header_text_not_position():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    capex = esri_gdp.parse_nritu_csv(content, column="民間企業設備")
    assert capex[date(2026, 4, 1)] == -4.6


def test_an_unknown_column_names_the_ones_that_exist():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    with pytest.raises(esri_gdp.EsriGdpError, match="国内総生産"):
        esri_gdp.parse_nritu_csv(content, column="存在しない列")


def test_triple_asterisk_is_missing_not_zero():
    content = (FIXTURES / "esri_nritu_jk.csv").read_bytes()
    public = esri_gdp.parse_nritu_csv(content, column="公的在庫変動")
    assert public == {}
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_esri_gdp.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.sources.esri_gdp'`

- [ ] **Step 4: Write the adapter**

`macrokit/src/macrokit/sources/esri_gdp.py`:

```python
"""Japan's quarterly GDP as each release published it -- the true vintage history.

The foundation spec's organising claim is that Japanese revision history cannot
be recovered. That is true of the e-Stat *API*, which has no realtime parameter.
It is not true of this archive: ESRI keeps every release's own statistical
table, so fetching them one at a time rebuilds the vintages the API will not
serve.

Menu-page URLs follow a stable pattern; the CSV behind them does not. A 2009
release serves ``/jp/sna/content/20120227_nritu_jk0911.csv`` and a 2026 one
serves ``tables/nritu-jk2621.csv``. Never construct the data URL -- read the
menu and pick by label.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from ..store import Observation

MENU_BASE = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files"

MISSING = "***"

_QUARTER_START_MONTH = {"1- 3": 1, "4- 6": 4, "7- 9": 7, "10-12": 10}

# "1994/ 1- 3." or "4- 6." -- the year is printed only on the first quarter of
# each year and carries forward to the next three rows.
_LABEL_RE = re.compile(r"^(?:(\d{4})/)?\s*(\d{1,2}-\s?\d{1,2})\.?$")

_KIND_SUFFIX = {"1st_prelim": "", "2nd_prelim": "_2"}


class EsriGdpError(RuntimeError):
    """A release's archive page or table could not be located or parsed."""


def menu_url(period_start: date, release_kind: str) -> str:
    """The release's menu page. Keyed on the *period's* year, not the release's."""
    if release_kind not in _KIND_SUFFIX:
        raise EsriGdpError(
            f"no menu-page URL pattern is known for release_kind={release_kind!r}. "
            "Only 1st_prelim and 2nd_prelim follow the qe{YY}{Q}[_2] scheme; "
            "2nd_prelim_revised is an off-cycle correction and must be located by hand."
        )
    quarter = (period_start.month - 1) // 3 + 1
    stem = f"qe{period_start.year % 100:02d}{quarter}{_KIND_SUFFIX[release_kind]}"
    return f"{MENU_BASE}/{period_start.year}/{stem}/gdemenuja.html"


class _LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text).strip()))
            self._href = None


def select_series_url(
    menu_html: bytes, menu_url_: str, *, series_label: str, stem_prefix: str
) -> str:
    """Resolve the one link that is both labelled ``series_label`` and not a reference series.

    Both eras publish two links carrying the identical label -- ``nritu`` and
    ``knritu``. The ``k`` variant is a reference series with different numbers, so
    matching on the label alone silently loads the wrong data.
    """
    parser = _LinkCollector()
    parser.feed(menu_html.decode("utf-8", errors="replace"))

    matches = [
        href
        for href, label in parser.links
        if series_label in label and href.rsplit("/", 1)[-1].startswith(stem_prefix)
    ]
    if not matches:
        raise EsriGdpError(
            f"{menu_url_}: no link labelled {series_label!r} with a basename starting "
            f"{stem_prefix!r}. The page layout or the file naming changed."
        )
    if len(matches) > 1:
        raise EsriGdpError(
            f"{menu_url_}: {len(matches)} links match {series_label!r}/{stem_prefix!r}: "
            f"{matches}. Refusing to guess which is the headline series."
        )
    return urljoin(menu_url_, matches[0])


def parse_nritu_csv(content: bytes, *, column: str) -> dict[date, float]:
    """Map each reference period's start date to the annualised QoQ percent change."""
    reader = list(csv.reader(io.StringIO(content.decode("cp932"))))

    header_index = next(
        (i for i, row in enumerate(reader) if column in [c.strip() for c in row]), None
    )
    if header_index is None:
        available = sorted(
            {c.strip() for row in reader[:8] for c in row if c.strip() and "," not in c}
        )
        raise EsriGdpError(f"column {column!r} not found; header cells seen: {available}")
    col = [c.strip() for c in reader[header_index]].index(column)

    series: dict[date, float] = {}
    year: int | None = None
    for record in reader[header_index + 1 :]:
        if not record or not record[0].strip():
            continue
        match = _LABEL_RE.match(record[0].strip())
        if match is None:
            continue  # English header rows and the trailing formula note
        label_year, quarter = match.groups()
        if label_year:
            year = int(label_year)
        if year is None:
            raise EsriGdpError(f"quarter {quarter!r} appears before any year label")
        month = _QUARTER_START_MONTH.get(quarter.replace(" ", "").replace("-", "- ")[:5])
        if month is None:
            month = _QUARTER_START_MONTH[_normalise_quarter(quarter)]
        if col >= len(record):
            continue
        cell = record[col].strip()
        if not cell or cell == MISSING:
            continue
        series[date(year, month, 1)] = float(cell)
    return series


def _normalise_quarter(token: str) -> str:
    """``1-3`` / ``1- 3`` / ``10-12`` -> the canonical key used by _QUARTER_START_MONTH."""
    left, right = (part.strip() for part in token.split("-"))
    return f"{left:>2}-{right:>2}".replace("  ", " ") if len(left) == 1 else f"{left}-{right}"
```

**Note on `_normalise_quarter`:** the keys in `_QUARTER_START_MONTH` mirror the exact spacing the ministry uses (`1- 3`, `10-12`). Simplify the two-branch lookup above into a single normalisation if the tests stay green — the tests, not the shape of this helper, are the contract.

Then add the adapter class:

```python
class EsriGdpAdapter:
    source = "esri_gdp"

    def __init__(self, *, timeout: float = 30.0) -> None:
        self._timeout = timeout

    def fetch_release(self, event, *, series_label: str, stem_prefix: str):
        """Return ``(csv_bytes, csv_url, status)`` for one release."""
        page = menu_url(event.period_start, event.release_kind)
        with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
            menu = client.get(page)
            if menu.status_code != 200:
                raise EsriGdpError(f"GET {page} returned {menu.status_code}")
            data_url = select_series_url(
                menu.content, page, series_label=series_label, stem_prefix=stem_prefix
            )
            data = client.get(data_url)
            if data.status_code != 200:
                raise EsriGdpError(f"GET {data_url} returned {data.status_code}")
        return data.content, data_url, data.status_code

    def parse(
        self, event, content: bytes, *, indicator: str, column: str,
        source_url: str, ingested_at: datetime,
    ) -> list[Observation]:
        series = parse_nritu_csv(content, column=column)
        return [
            Observation(
                indicator=indicator,
                period_start=period_start,
                period_end=_quarter_end(period_start),
                release_date=event.release_date,
                vintage_seq=1 if event.release_kind == "1st_prelim" else 2,
                value=value,
                unit="percent_saar",
                sa="sa",
                freq="Q",
                source=self.source,
                source_url=source_url,
                ingested_at=ingested_at,
                vintage_kind="actual",
            )
            for period_start, value in sorted(series.items())
        ]


def _quarter_end(period_start: date) -> date:
    end_month = period_start.month + 2
    last_day = 31 if end_month in (3, 12) else 30
    return date(period_start.year, end_month, last_day)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_esri_gdp.py -q`
Expected: PASS

- [ ] **Step 6: Add the live test that proves the vintage claim**

This is the measurement the whole design rests on. Append to `macrokit/tests/test_esri_gdp.py`:

```python
@pytest.mark.live
def test_the_same_quarter_reads_differently_across_two_releases():
    """2026 Q1 is +2.1 in its own 2nd preliminary and +1.9 one release later."""
    adapter = esri_gdp.EsriGdpAdapter()
    kwargs = {"series_label": "年率換算の実質季節調整系列(前期比)", "stem_prefix": "nritu"}

    own = adapter.fetch_release(_event(date(2026, 1, 1), "2nd_prelim"), **kwargs)[0]
    later = adapter.fetch_release(_event(date(2026, 4, 1), "1st_prelim"), **kwargs)[0]

    assert esri_gdp.parse_nritu_csv(own, column="国内総生産(支出側)")[date(2026, 1, 1)] == 2.1
    assert esri_gdp.parse_nritu_csv(later, column="国内総生産(支出側)")[date(2026, 1, 1)] == 1.9
    assert esri_gdp.parse_nritu_csv(later, column="国内総生産(支出側)")[date(2026, 4, 1)] == 1.1
```

Add a small `_event(period_start, kind)` helper in the test module that builds a `ReleaseEvent` with an arbitrary tz-aware `release_date`; `fetch_release` reads only `period_start` and `release_kind`.

- [ ] **Step 7: Commit**

```bash
git add macrokit/src/macrokit/sources/esri_gdp.py macrokit/tests/test_esri_gdp.py \
        macrokit/tests/fixtures/esri_gdemenuja.html macrokit/tests/fixtures/esri_nritu_jk.csv
git commit -m "Rebuild Japanese GDP vintages from each release's own table"
```

---

## Task 5: The `expectations` table, `prior_vintage` and `random_walk`

**Files:**
- Create: `macrokit/src/macrokit/expectations.py`
- Create: `macrokit/tests/test_expectations.py`
- Modify: `macrokit/src/macrokit/store.py`

**Interfaces:**
- Consumes: `pit.as_of`, `store.ReleaseEvent`, `observations` rows (Tasks 3–4).
- Produces:
  - `store.Expectation(indicator, period_start, release_kind, method, expected, as_of, source, source_url, ingested_at)`
  - `store.insert_expectations(con, rows) -> int`
  - `expectations.previous_business_day(con, when: date) -> date | None`
  - `expectations.prior_vintage(con, event) -> Expectation | None`
  - `expectations.random_walk(con, event) -> Expectation | None`
  - `expectations.compute(con, events, *, methods, ingested_at) -> list[Expectation]`

**Context:** This is where the leak rule bites. `random_walk`'s expectation for a release at `T` is the previous quarter's value **as it stood before `T`** — measured at +2.1 for 2026 Q1, versus the +1.9 that the 2026-08-17 release itself published. Reading the release's own table would put same-day information into the expectation.

Business days come from `market_rates`, not from a holiday calendar: the Phase 1 calendar is missing the year-end government and bank holidays (`known-limitations.md` §2), so `market_rates` row presence is the more reliable definition.

- [ ] **Step 1: Write the failing tests**

`macrokit/tests/test_expectations.py`:

```python
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from macrokit import expectations, store

JST = ZoneInfo("Asia/Tokyo")
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def _obs(con, period_start, release_date, value, seq):
    store.insert_observations(con, [store.Observation(
        indicator="jp_real_gdp_qoq_saar", period_start=period_start,
        period_end=date(period_start.year, period_start.month + 2, 30),
        release_date=release_date, vintage_seq=seq, value=value,
        unit="percent_saar", sa="sa", freq="Q", source="esri_gdp",
        source_url="u", ingested_at=NOW, vintage_kind="actual",
    )])


def _event(period_start, kind, release_date):
    return store.ReleaseEvent(
        indicator="jp_real_gdp_qoq_saar", period_start=period_start,
        period_end=date(period_start.year, period_start.month + 2, 30),
        release_kind=kind, release_date=release_date, scheduled=False,
        source="esri_calendar", source_url="u", ingested_at=NOW,
    )


@pytest.fixture
def con(tmp_path):
    return store.connect(tmp_path / "t.duckdb")


def _rates(con, *days):
    store.insert_rates(con, [store.RateObservation(
        curve="jgb", obs_date=d, tenor_y=10.0, yield_pct=2.9,
        source="mof_jgb", source_url="u", ingested_at=NOW,
    ) for d in days])


def test_random_walk_takes_the_prior_quarter_as_it_stood_before_the_release(con):
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    _obs(con, date(2026, 1, 1), june, 2.1, 2)      # the value knowable on 8/14
    _obs(con, date(2026, 1, 1), august, 1.9, 1)    # revised ON the release day
    _obs(con, date(2026, 4, 1), august, 1.1, 1)
    _rates(con, date(2026, 8, 14), date(2026, 8, 17))

    result = expectations.random_walk(con, _event(date(2026, 4, 1), "1st_prelim", august))

    assert result.expected == 2.1
    assert result.as_of == date(2026, 8, 14)


def test_random_walk_has_no_expectation_for_the_oldest_release(con):
    first = datetime(2009, 2, 16, 8, 50, tzinfo=JST)
    _obs(con, date(2008, 10, 1), first, 1.0, 1)
    _rates(con, date(2009, 2, 13), date(2009, 2, 16))

    assert expectations.random_walk(con, _event(date(2008, 10, 1), "1st_prelim", first)) is None


def test_prior_vintage_anchors_the_second_preliminary_on_the_first(con):
    may = datetime(2026, 5, 18, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    _obs(con, date(2026, 1, 1), may, 2.4, 1)
    _obs(con, date(2026, 1, 1), june, 2.1, 2)
    _rates(con, date(2026, 6, 5), date(2026, 6, 8))

    result = expectations.prior_vintage(con, _event(date(2026, 1, 1), "2nd_prelim", june))

    assert result.expected == 2.4
    assert result.method == "prior_vintage"


def test_prior_vintage_does_not_apply_to_a_first_preliminary(con):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    _obs(con, date(2026, 4, 1), august, 1.1, 1)
    _rates(con, date(2026, 8, 14), date(2026, 8, 17))

    assert expectations.prior_vintage(con, _event(date(2026, 4, 1), "1st_prelim", august)) is None


def test_previous_business_day_uses_market_rates_not_a_holiday_calendar(con):
    _rates(con, date(2026, 8, 13), date(2026, 8, 14), date(2026, 8, 17))
    assert expectations.previous_business_day(con, date(2026, 8, 17)) == date(2026, 8, 14)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_expectations.py -q`
Expected: FAIL — `ImportError: cannot import name 'expectations'`

- [ ] **Step 3: Add the table and row type to `store.py`**

Append to `SCHEMA_SQL`:

```sql
CREATE TABLE IF NOT EXISTS expectations (
  indicator     VARCHAR NOT NULL,
  period_start  DATE    NOT NULL,
  release_kind  VARCHAR NOT NULL,
  method        VARCHAR NOT NULL,
  expected      DOUBLE  NOT NULL,
  as_of         DATE    NOT NULL,
  source        VARCHAR NOT NULL,
  source_url    VARCHAR NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (indicator, period_start, release_kind, method)
);
```

Add `EXPECTATION_METHODS = frozenset({"prior_vintage", "random_walk", "ar_model", "esp"})`, the `Expectation` dataclass, and `insert_expectations` mirroring `insert_rates` (naive-datetime rejection, method-membership check, `INSERT OR IGNORE`, row-count delta).

- [ ] **Step 4: Write `expectations.py`**

```python
"""What the market could have known before each release.

Every method here obeys one rule: an expectation for a release at ``T`` may only
read vintages whose ``release_date`` is strictly before ``T``. The measured cost
of breaking it: 2026 Q1 stood at +2.1 before the 2026-08-17 release and at +1.9
after it, because that release revised the quarter it was not reporting on.

Business days come from ``market_rates`` rather than the holiday calendar, which
is missing the year-end government and bank holidays.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import duckdb

from . import pit
from .store import Expectation, ReleaseEvent

SOURCE_URL = "computed://macrokit/expectations"


def previous_business_day(con: duckdb.DuckDBPyConnection, when: date) -> date | None:
    row = con.execute(
        "SELECT max(obs_date) FROM market_rates WHERE obs_date < ?", [when]
    ).fetchone()
    return row[0] if row and row[0] is not None else None


def _knowable_before(con: duckdb.DuckDBPyConnection, event: ReleaseEvent):
    """The series and the as-of date visible on the last business day before the release."""
    as_of_date = previous_business_day(con, event.release_date.date())
    if as_of_date is None:
        return None, None
    cutoff = datetime.combine(
        as_of_date + timedelta(days=1), datetime.min.time(), tzinfo=event.release_date.tzinfo
    )
    return pit.as_of(con, event.indicator, cutoff), as_of_date


def _previous_quarter(period_start: date) -> date:
    month = period_start.month - 3
    return date(period_start.year - 1, month + 12, 1) if month < 1 else date(period_start.year, month, 1)


def _expectation(event: ReleaseEvent, method: str, value: float, as_of: date) -> Expectation:
    return Expectation(
        indicator=event.indicator,
        period_start=event.period_start,
        release_kind=event.release_kind,
        method=method,
        expected=value,
        as_of=as_of,
        source="macrokit",
        source_url=SOURCE_URL,
        ingested_at=event.ingested_at,
    )


def random_walk(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """Expect this quarter to repeat the previous quarter's last-knowable value."""
    series, as_of_date = _knowable_before(con, event)
    if series is None or series.empty:
        return None
    previous = _previous_quarter(event.period_start)
    if previous not in series.index:
        return None
    return _expectation(event, "random_walk", float(series[previous]), as_of_date)


def prior_vintage(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """A second preliminary's anchor is the first preliminary's published value."""
    if event.release_kind != "2nd_prelim":
        return None
    series, as_of_date = _knowable_before(con, event)
    if series is None or event.period_start not in series.index:
        return None
    return _expectation(event, "prior_vintage", float(series[event.period_start]), as_of_date)


METHODS = {"random_walk": random_walk, "prior_vintage": prior_vintage}


def compute(
    con: duckdb.DuckDBPyConnection,
    events: list[ReleaseEvent],
    *,
    methods: tuple[str, ...] = ("random_walk", "prior_vintage"),
) -> list[Expectation]:
    rows: list[Expectation] = []
    for event in events:
        for method in methods:
            result = METHODS[method](con, event)
            if result is not None:
                rows.append(result)
    return rows
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_expectations.py -q`
Expected: PASS

- [ ] **Step 6: Add the leak-guard test the spec requires**

The spec makes this an acceptance criterion. Append:

```python
def test_no_expectation_reads_a_vintage_released_at_or_after_its_event(con):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    june = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    _obs(con, date(2026, 1, 1), june, 2.1, 2)
    _obs(con, date(2026, 1, 1), august, 1.9, 1)
    _obs(con, date(2026, 4, 1), august, 1.1, 1)
    _rates(con, date(2026, 8, 14), date(2026, 8, 17))

    for row in expectations.compute(con, [_event(date(2026, 4, 1), "1st_prelim", august)]):
        assert row.as_of < august.date()
        assert row.expected != 1.9  # the value that release itself published
```

- [ ] **Step 7: Commit**

```bash
git add macrokit/src/macrokit/expectations.py macrokit/src/macrokit/store.py \
        macrokit/tests/test_expectations.py
git commit -m "Compute pre-release expectations without reading the release"
```

---

## Task 6: The `ar_model` expectation

**Files:**
- Modify: `macrokit/src/macrokit/expectations.py`
- Modify: `macrokit/tests/test_expectations.py`

**Interfaces:**
- Consumes: `expectations._knowable_before` (Task 5).
- Produces: `expectations.ar_model(con, event) -> Expectation | None`, registered in `METHODS`.

**Context:** AR order is **fixed at 4** — one year of quarterly data. Choosing the order from the data is itself a leak path. The estimation window is expanding: everything knowable at `as_of`. Fewer than `p + 8 = 12` usable observations produces no row rather than a fragile one.

Starting the panel in 2009 costs no estimation history: each release's table carries the series back to 1994, so the first ingested release already supplies ~60 quarters.

- [ ] **Step 1: Write the failing tests**

```python
def test_ar_model_forecasts_a_constant_series_as_that_constant(con):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    earlier = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    start = date(2010, 1, 1)
    for i in range(20):
        month = (i % 4) * 3 + 1
        _obs(con, date(start.year + i // 4, month, 1), earlier, 2.0, 2)
    _rates(con, date(2026, 8, 14), date(2026, 8, 17))

    result = expectations.ar_model(con, _event(date(2026, 4, 1), "1st_prelim", august))

    assert result is not None
    assert result.expected == pytest.approx(2.0, abs=1e-6)
    assert result.as_of == date(2026, 8, 14)


def test_ar_model_declines_when_the_history_is_shorter_than_p_plus_eight(con):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    earlier = datetime(2026, 6, 8, 8, 50, tzinfo=JST)
    for i in range(11):
        month = (i % 4) * 3 + 1
        _obs(con, date(2020 + i // 4, month, 1), earlier, float(i), 2)
    _rates(con, date(2026, 8, 14), date(2026, 8, 17))

    assert expectations.ar_model(con, _event(date(2026, 4, 1), "1st_prelim", august)) is None


def test_ar_order_is_pinned_at_four():
    assert expectations.AR_ORDER == 4
    assert expectations.AR_MIN_OBSERVATIONS == 12
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_expectations.py -q`
Expected: FAIL — `AttributeError: module 'macrokit.expectations' has no attribute 'ar_model'`

- [ ] **Step 3: Implement `ar_model`**

Add to `macrokit/src/macrokit/expectations.py`:

```python
import numpy as np

AR_ORDER = 4
AR_MIN_OBSERVATIONS = AR_ORDER + 8


def ar_model(con: duckdb.DuckDBPyConnection, event: ReleaseEvent) -> Expectation | None:
    """One-step-ahead AR(4) forecast fitted by OLS on everything knowable at as_of.

    The order is fixed rather than selected: choosing p from the data would let
    the selection see information the forecast is not allowed to use, and the
    resulting surprise would be smaller than any trader could have achieved.
    """
    series, as_of_date = _knowable_before(con, event)
    if series is None:
        return None
    history = series.sort_index()
    history = history[history.index < event.period_start]
    if len(history) < AR_MIN_OBSERVATIONS:
        return None

    values = history.to_numpy(dtype=float)
    rows = len(values) - AR_ORDER
    design = np.column_stack(
        [np.ones(rows)] + [values[AR_ORDER - lag : len(values) - lag] for lag in range(1, AR_ORDER + 1)]
    )
    target = values[AR_ORDER:]
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)

    latest = np.concatenate([[1.0], values[-1 : -AR_ORDER - 1 : -1]])
    return _expectation(event, "ar_model", float(latest @ coefficients), as_of_date)


METHODS["ar_model"] = ar_model
```

Move the `METHODS` dict definition below `ar_model` (or keep the explicit registration line) so the mapping holds all three. `numpy` is already an installed transitive dependency of pandas — confirm with `uv run --no-sync python -c "import numpy"` before relying on it, and declare it in `macrokit/pyproject.toml` if it is not already listed, because the shared root `.venv` hides undeclared imports.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_expectations.py -q`
Expected: PASS

- [ ] **Step 5: Update the default method tuple**

Change `compute`'s default to `("random_walk", "prior_vintage", "ar_model")` and add a test asserting a single event yields both `random_walk` and `ar_model` rows when the history is long enough.

- [ ] **Step 6: Commit**

```bash
git add macrokit/src/macrokit/expectations.py macrokit/tests/test_expectations.py \
        macrokit/pyproject.toml
git commit -m "Add a fixed-order AR forecast as a second expectation baseline"
```

---

## Task 7: The event panel and the CLI

**Files:**
- Create: `macrokit/src/macrokit/panel.py`
- Create: `macrokit/tests/test_panel.py`
- Modify: `macrokit/src/macrokit/cli.py`, `macrokit/tests/test_cli.py`

**Interfaces:**
- Consumes: `releases`, `market_rates`, `expectations`, `observations`.
- Produces:
  - `panel.event_panel(con, *, indicator, tenors, include_revised=False, z_min_observations=20) -> pd.DataFrame`
  - CLI: `macrokit rates ingest`, `macrokit releases ingest`, `macrokit gdp ingest`, `macrokit expectations compute`, `macrokit panel export --out PATH`

**Context:** The panel is a query so the normalisation and the change window stay changeable. `surprise_z` divides by the **expanding** standard deviation of prior surprises for the same method — using the full-sample standard deviation would quietly put future information into every early row. Rows with fewer than 20 prior surprises get `NULL`, so `surprise_z` starts around 2014 while `surprise` is populated from the start.

Tenor columns are `NULL` before that tenor existed (25y before 2004-03-22, 40y before 2007-11-06). That is missing, not zero.

- [ ] **Step 1: Write the failing tests**

`macrokit/tests/test_panel.py` — reuse the `_obs`/`_event`/`_rates` helpers from `test_expectations.py` by importing them, or copy them; the fixture data is:

```python
def test_the_panel_pairs_a_release_with_that_days_move(con):
    august = datetime(2026, 8, 17, 8, 50, tzinfo=JST)
    _seed_2026_q2(con)  # helper defined in the test module

    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(2.0, 10.0))
    row = frame[frame["method"] == "random_walk"].iloc[0]

    assert row["release_date"].date() == date(2026, 8, 17)
    assert row["actual"] == 1.1
    assert row["expected"] == 2.1
    assert row["surprise"] == pytest.approx(-1.0)
    assert row["d1_bp_10y"] == pytest.approx(5.2, abs=0.1)
    assert row["d1_bp_2y"] == pytest.approx(4.0, abs=0.1)


def test_surprise_z_is_null_until_twenty_prior_surprises_exist(con):
    _seed_2026_q2(con)
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    assert frame["surprise_z"].isna().all()


def test_a_tenor_that_did_not_exist_yet_is_null_not_zero(con):
    _seed_2026_q2(con)  # seeds 2y and 10y only
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0, 40.0))
    assert frame["d1_bp_40y"].isna().all()
    assert frame["d1_bp_10y"].notna().all()


def test_the_off_cycle_revision_is_excluded_by_default(con):
    _seed_2026_q2(con)
    _seed_revised_event(con)  # a 2nd_prelim_revised event with rates and expectations

    default = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    opted_in = panel.event_panel(
        con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,), include_revised=True
    )

    assert "2nd_prelim_revised" not in set(default["release_kind"])
    assert "2nd_prelim_revised" in set(opted_in["release_kind"])


def test_a_release_with_no_rate_row_is_dropped_and_counted(con):
    _seed_future_release(con)  # a scheduled 2027 release, no market_rates
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    assert (frame["release_date"].dt.year == 2027).sum() == 0
```

`_seed_2026_q2` inserts: the 2026 Q2 first-preliminary release event at 2026-08-17 08:50 JST; observations giving `actual = 1.1` for 2026 Q2 and the two 2026 Q1 vintages (2.1 then 1.9); `market_rates` for 2026-08-14 (2y 1.657, 10y 2.878) and 2026-08-17 (2y 1.697, 10y 2.930); and the expectations produced by `expectations.compute`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_panel.py -q`
Expected: FAIL — `ImportError: cannot import name 'panel'`

- [ ] **Step 3: Write `panel.py`**

```python
"""The event panel: one row per (release, expectation method), built as a query.

Deliberately not a table. The surprise normalisation and the change window are
the two things most likely to need revisiting, and materialising them would
freeze both.

Reading a single row is not meaningful. The only free JGB data is the daily
close, which cannot separate an 08:50 release from everything else that day --
on 2026-08-17 the curve sold off on BoJ and fiscal repricing while the GDP print
itself had undershot. Read the panel as a statistic over ~142 events.
"""

from __future__ import annotations

import duckdb
import pandas as pd

DEFAULT_TENORS = (2.0, 5.0, 10.0, 20.0, 30.0)


def event_panel(
    con: duckdb.DuckDBPyConnection,
    *,
    indicator: str,
    tenors: tuple[float, ...] = DEFAULT_TENORS,
    include_revised: bool = False,
    z_min_observations: int = 20,
) -> pd.DataFrame:
    kinds = ("1st_prelim", "2nd_prelim", "2nd_prelim_revised") if include_revised else (
        "1st_prelim", "2nd_prelim"
    )
    frame = con.execute(
        """
        SELECT r.release_date, r.period_start, r.period_end, r.release_kind,
               o.value AS actual, e.method, e.expected, e.as_of,
               o.value - e.expected AS surprise
        FROM releases r
        JOIN observations o
          ON o.indicator = r.indicator
         AND o.period_start = r.period_start
         AND o.release_date = r.release_date
        JOIN expectations e
          ON e.indicator = r.indicator
         AND e.period_start = r.period_start
         AND e.release_kind = r.release_kind
        WHERE r.indicator = ?
          AND list_contains(?::VARCHAR[], r.release_kind)
        ORDER BY r.release_date, e.method
        """,
        [indicator, list(kinds)],
    ).df()
    if frame.empty:
        return frame

    frame = _attach_rate_changes(con, frame, tenors)
    frame = frame[frame[f"d1_bp_{_label(tenors[0])}"].notna() | _any_tenor_present(frame, tenors)]
    frame["surprise_z"] = _expanding_z(frame, z_min_observations)
    return frame.reset_index(drop=True)


def _label(tenor: float) -> str:
    return f"{int(tenor)}y"


def _any_tenor_present(frame: pd.DataFrame, tenors: tuple[float, ...]) -> pd.Series:
    columns = [f"d1_bp_{_label(t)}" for t in tenors]
    return frame[columns].notna().any(axis=1)


def _attach_rate_changes(
    con: duckdb.DuckDBPyConnection, frame: pd.DataFrame, tenors: tuple[float, ...]
) -> pd.DataFrame:
    curve = con.execute(
        "SELECT obs_date, tenor_y, yield_pct FROM market_rates WHERE curve = 'jgb' "
        "ORDER BY obs_date"
    ).df()
    if curve.empty:
        for tenor in tenors:
            frame[f"d1_bp_{_label(tenor)}"] = pd.NA
            frame[f"d2_bp_{_label(tenor)}"] = pd.NA
        return frame

    wide = curve.pivot(index="obs_date", columns="tenor_y", values="yield_pct").sort_index()
    sessions = list(wide.index)
    position = {day: i for i, day in enumerate(sessions)}

    for tenor in tenors:
        d1, d2 = [], []
        for release_date in frame["release_date"]:
            day = release_date.date()
            index = position.get(day)
            if index is None or index == 0 or tenor not in wide.columns:
                d1.append(pd.NA)
                d2.append(pd.NA)
                continue
            base = wide[tenor].iloc[index - 1]
            d1.append(_bp(wide[tenor].iloc[index], base))
            forward = index + 1
            d2.append(_bp(wide[tenor].iloc[forward], base) if forward < len(sessions) else pd.NA)
        frame[f"d1_bp_{_label(tenor)}"] = d1
        frame[f"d2_bp_{_label(tenor)}"] = d2
    return frame


def _bp(value, base):
    if pd.isna(value) or pd.isna(base):
        return pd.NA
    return (float(value) - float(base)) * 100.0


def _expanding_z(frame: pd.DataFrame, minimum: int) -> pd.Series:
    """Divide by the standard deviation of *prior* surprises for the same method.

    Expanding, not full-sample: a full-sample sigma would let every early row see
    the dispersion of surprises that had not happened yet.
    """
    result = pd.Series(pd.NA, index=frame.index, dtype="float64")
    for method, group in frame.groupby("method", sort=False):
        surprises = group["surprise"].astype(float)
        sigma = surprises.shift(1).expanding(min_periods=minimum).std()
        result.loc[group.index] = surprises / sigma
    return result
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_panel.py -q`
Expected: PASS

- [ ] **Step 5: Wire up the CLI**

Add to `macrokit/src/macrokit/cli.py`, following the existing `catalog`/`status` command style. Each ingest command opens the store under `--data-root`, runs the adapter through `snapshot.save_snapshot`, and prints a one-line summary:

```python
@main.command("rates")
@click.pass_context
def rates_command(ctx: click.Context) -> None:
    """Ingest the MoF JGB constant-maturity curve."""


@main.group("gdp")
def gdp_group() -> None:
    """Japanese GDP releases, vintages, expectations and the event panel."""


@gdp_group.command("releases")
@gdp_group.command("vintages")
@gdp_group.command("expectations")
@gdp_group.command("panel")
@click.option("--out", type=click.Path(path_type=Path), required=True)
@click.option("--include-revised", is_flag=True, default=False)
```

`panel` writes CSV to `--out` and prints the row count and the date range. Add a `test_cli.py` case per command asserting `--help` exits 0 and that `gdp panel --out` on an empty store exits 0 with a "no events" message rather than a traceback.

- [ ] **Step 6: Run the full suite**

Run: `uv run --no-sync pytest macrokit/tests -q && make lint`
Expected: PASS, `All checks passed!`

- [ ] **Step 7: End-to-end acceptance run**

The spec's acceptance criterion for this task. Run against live sources once:

```bash
uv run --no-sync macrokit --data-root macrokit/data rates
uv run --no-sync macrokit --data-root macrokit/data gdp releases
uv run --no-sync macrokit --data-root macrokit/data gdp vintages
uv run --no-sync macrokit --data-root macrokit/data gdp expectations
uv run --no-sync macrokit --data-root macrokit/data gdp panel --out /tmp/panel.csv
```

Verify the 2026 Q2 first-preliminary row:

| Column | Expected | Source of the expectation |
|---|---|---|
| `release_date` | 2026-08-17 08:50+09:00 | ESRI XML |
| `actual` | 1.1 | measured in `nritu-jk2621.csv` |
| `d1_bp_10y` | +5 ± 1 | 8/14 close 2.878% → 8/17 2.930% |
| `expected` (`random_walk`) | 2.1 | 2026 Q1 as published in qe261, **not** the 1.9 that this release published |

If `d1_bp_10y` is null, the MoF feed had not yet published 8/17 — see Task 1 Step 7.

- [ ] **Step 8: Commit**

```bash
git add macrokit/src/macrokit/panel.py macrokit/src/macrokit/cli.py \
        macrokit/tests/test_panel.py macrokit/tests/test_cli.py
git commit -m "Assemble the release/rate-move panel and expose it on the CLI"
```

---

## Task 8: ESP forecast consensus

**Files:**
- Create: `macrokit/src/macrokit/sources/esp.py`
- Create: `macrokit/tests/test_esp.py`

**Interfaces:**
- Consumes: `store.Expectation` (Task 5).
- Produces: `esp.EspAdapter`, and `method="esp"` rows in `expectations`.

**Context and why this is last:** ESP is the expectation closest to what the market actually held, and it is the most fragile to acquire. The listing page must be scraped (download URLs carry encrypted `?f=<base64>&post_id=` parameters and cannot be constructed), the numbers live in a PDF, and the archive is only confirmed back to 2018. Every other method already works without it.

It also matters most. ESP's July survey put 2026 Q2 at **+0.80%** annualised against an actual of **+1.1%** — a 0.3pp *beat* — while the pre-release consensus of +2.0–2.2% made the same print a ~1pp *miss*. ESP closes its responses at the start of the month and cannot see the quarter's final monthly statistics, so it is a two-weeks-early expectation, not the eve-of-release consensus. `as_of` must carry the survey's response deadline, never the publication date.

**Three unknowns to resolve before writing code** (spec §11-1, §11-2):

1. Does the free 結果概要 PDF contain a quarterly real-GDP forecast table? If not, try 今月のポイント.
2. How far back does the listing go behind "過去の調査結果はこちら"?
3. Which PDF reader is acceptable? **This needs a new production dependency (`pypdf` or similar) — stop and ask before adding it.**

- [ ] **Step 1: Resolve the three unknowns and report**

Fetch the listing page, download one 結果概要 PDF, and check whether a quarterly GDP figure is machine-extractable. Write the findings into `macrokit/docs/known-limitations.md` as a new section regardless of the outcome.

If the numbers are not extractable, **stop here and report** — the panel is complete without `esp`, and a hand-maintained CSV of ESP consensus values is a better fallback than a brittle PDF parser. That fallback still needs `as_of` per row.

- [ ] **Step 2: Ask before adding the dependency**

If extraction is viable, present the dependency and the archive depth, and wait for approval before continuing.

- [ ] **Step 3: Implement against a fixture**

Save one real PDF (or its extracted text, if the PDF itself is too large for a fixture) under `macrokit/tests/fixtures/`. Test that the parser pulls the quarterly figure and the response deadline, and that `as_of` equals the deadline rather than the publication date.

- [ ] **Step 4: Add the sign-flip regression test**

```python
def test_esp_and_the_pre_release_consensus_disagree_on_the_sign(con):
    """The 2026 Q2 print beat ESP by 0.3pp while missing the market by ~1pp."""
    frame = panel.event_panel(con, indicator="jp_real_gdp_qoq_saar", tenors=(10.0,))
    q2 = frame[frame["period_start"] == date(2026, 4, 1)]
    assert q2[q2["method"] == "esp"]["surprise"].iloc[0] > 0
    assert q2[q2["method"] == "random_walk"]["surprise"].iloc[0] < 0
```

- [ ] **Step 5: Run the full suite and commit**

```bash
uv run --no-sync pytest macrokit/tests -q && make lint
git add macrokit/src/macrokit/sources/esp.py macrokit/tests/test_esp.py \
        macrokit/tests/fixtures/ macrokit/docs/known-limitations.md
git commit -m "Add the ESP survey as the market-proximate expectation"
```

---

## Self-Review

**Spec coverage.**

| Spec section | Task |
|---|---|
| §3.1 scope, 2008 Q4 onward | 3 (calendar bounds the panel) |
| §3.2 non-scope | Honoured — no intraday, no components, no nominal/deflator |
| §4.1 MoF JGB, both files, era dates, per-tenor starts | 1 |
| §4.2 calendar XML, three traps | 3 |
| §4.3 menu-stable / CSV-unstable, `nritu` vs `knritu` | 4 |
| §4.4 ESP | 8 |
| §5.1 `observations` usage, `vintage_kind="actual"` | 4 |
| §5.2 `releases` | 3 |
| §5.3 `market_rates` | 1 |
| §5.4 `expectations` | 5 |
| §5.5 panel as a query, NULL tenors | 7 |
| §6 four methods, AR(4) fixed | 5, 6, 8 |
| §6.1 prior quarter is revised | 4 (live test), 5 (unit test) |
| §6.2 expanding z, min 20 | 7 |
| §6.3 oldest release has no expectation | 5 |
| §7 Δy definition, business days from `market_rates` | 5, 7 |
| §8 leak prevention, three sites | 5 (guard test), 6 |
| §10.2 known-limitations §3 | 2 |

**Gap found and closed:** the spec's §10.1 (correcting the foundation's "Japanese vintages are unrecoverable" claim) had no task. It is now the module docstring in Task 4 plus the Task 8 Step 1 instruction to update `known-limitations.md`. The foundation spec itself is a separate document; correcting it is a one-line follow-up, not a task here.

**Placeholder scan:** clean. Task 8 is deliberately gated rather than specified in full, and says so — it needs a dependency decision and three factual unknowns resolved first. Every other task carries runnable code, real fixture content, and exact commands.

**Type consistency:** `ReleaseEvent`, `RateObservation`, and `Expectation` are defined in `store.py` (Tasks 1, 3, 5) and imported by the source modules, so no module defines a second copy. `release_kind` strings are `1st_prelim` / `2nd_prelim` / `2nd_prelim_revised` in the DDL, the `KIND_MAP`, `menu_url`, and the panel filter. `method` strings are `random_walk` / `prior_vintage` / `ar_model` / `esp` in `EXPECTATION_METHODS`, `METHODS`, and every test. Tenor column labels are `d1_bp_{int}y` in both `panel._label` and the tests.

**One known rough edge:** `esri_gdp._normalise_quarter` in Task 4 Step 4 is written twice over (a `.get` with a fallback). The step says so and instructs the implementer to collapse it once the tests are green. Flagged rather than left silent.
