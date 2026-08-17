# macrokit Foundation (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the macrokit package skeleton, catalog loader, DuckDB point-in-time store, raw snapshot layer, and the ALFRED adapter, with US core PCE flowing end-to-end from the live API to a point-in-time query.

**Architecture:** A catalog of YAML-declared indicators drives thin per-source adapters. Every fetch writes an immutable, content-hash-deduplicated raw snapshot before anything is parsed, so ingestion works before parsing exists. Parsed rows land in a DuckDB `observations` table where each row is one vintage, and `as_of()` reconstructs what was knowable on a given date.

**Tech Stack:** Python 3.12+, hatchling, pydantic v2, duckdb, pandas, httpx, tenacity, click, pyyaml, pytest, ruff. No new workspace dependencies — all are already installed.

**Spec:** `docs/superpowers/specs/2026-08-17-macrokit-design.md`

## Global Constraints

- Python `requires-python = ">=3.12"`; ruff `line-length = 100`, `target-version = "py312"`, `select = ["E","W","F","I","B","UP","N","RUF"]`, `ignore = ["E501","N803","N806"]` — copy this config verbatim from `market_nn/pyproject.toml`.
- Build backend is `hatchling`; `src/` layout; package at `macrokit/src/macrokit/`.
- pytest `addopts = "-ra --strict-markers --import-mode=importlib"`.
- **No new production dependencies.** Only httpx, requests, pyyaml, pydantic, duckdb, pandas, tenacity, click — all already in the shared `.venv`.
- Run `uv` from the repo root only. Running it inside a member directory creates a stray venv.
- Commit messages in English, imperative sentence style with no `feat:`/`fix:` prefix — match the existing log (`Add the macrokit design spec`, `Refresh the workspace green baseline`).
- **Secrets:** read API keys from the environment only. Never write a key value into a file, a test, a commit, or terminal output.
- `vintage_kind` is one of exactly `actual` | `snapshot` | `estimated`. Japanese sources are always `snapshot`.
- Docs are Japanese-first; code, identifiers, and commit messages are English.

---

### Task 1: Package skeleton and workspace integration

**Files:**
- Create: `macrokit/pyproject.toml`
- Create: `macrokit/README.md`
- Create: `macrokit/src/macrokit/__init__.py`
- Create: `macrokit/tests/test_package.py`
- Create: `macrokit/.gitignore`
- Modify: `pyproject.toml` (root — `[tool.uv.workspace] members`, `[tool.pytest.ini_options] testpaths`)
- Modify: `conftest.py` (root — add `import macrokit`)
- Modify: `.agentignore`

**Interfaces:**
- Consumes: nothing.
- Produces: importable package `macrokit` exposing `__version__: str`.

- [ ] **Step 1: Write the failing test**

Create `macrokit/tests/test_package.py`:

```python
"""The package must be importable under its own name.

The workspace runs one pytest over every member. Because this project's
directory name equals its package name, pytest 9 will synthesize a namespace
module for `macrokit` and shadow the real package unless the root conftest
imports it first. This test fails loudly if that regresses.
"""

import macrokit


def test_package_exposes_a_version():
    assert isinstance(macrokit.__version__, str)
    assert macrokit.__version__


def test_package_is_the_real_one_not_a_namespace_shadow():
    # A namespace shadow has no __file__; the installed package does.
    assert macrokit.__file__ is not None
    assert macrokit.__file__.endswith("src/macrokit/__init__.py")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_package.py -v`
Expected: FAIL — collection error, `ModuleNotFoundError: No module named 'macrokit'`.

- [ ] **Step 3: Create the package files**

Create `macrokit/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "macrokit"
version = "0.1.0"
description = "Point-in-time research platform for Japanese and US macroeconomic indicators"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "MIT" }
authors = [{ name = "Kazumasa" }]
dependencies = [
    "click>=8.1",
    "duckdb>=1.0",
    "httpx>=0.27",
    "pandas>=2.2",
    "pydantic>=2.7",
    "pyyaml>=6",
    "tenacity>=8.3",
]

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "ruff>=0.6",
]

[project.scripts]
macrokit = "macrokit.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["src/macrokit"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers --import-mode=importlib"
markers = [
    "live: hits a real external API; requires network and API keys",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "N", "RUF"]
ignore = ["E501", "N803", "N806"]
```

Create `macrokit/src/macrokit/__init__.py`:

```python
"""Point-in-time research platform for Japanese and US macroeconomic indicators.

Design note: US series carry real vintages (ALFRED exposes every revision with
its release date). Japanese series do not -- e-Stat has no vintage parameter at
all -- so their history is reconstructed from snapshots this package takes from
today onward, and is unrecoverable for the past. Every observation therefore
records whether its release_date is `actual` or merely a `snapshot` timestamp.
"""

__version__ = "0.1.0"
```

Create `macrokit/README.md`:

```markdown
# macrokit — 日米マクロ経済指標のリサーチ基盤

日米の経済指標をポイントインタイムで蓄積し、マクロ計量モデルの土台にする。

設計書: [`docs/superpowers/specs/2026-08-17-macrokit-design.md`](../docs/superpowers/specs/2026-08-17-macrokit-design.md)

## なぜスナップショットを取り続けるのか

**日本の統計には vintage（改定前の値）が存在しない。** e-Stat API には
realtime / vintage / 公表時点を指定するパラメータがなく、日銀・内閣府・財務省の
CSV も上書き公表される。したがって「速報 → 1 次改定 → 2 次改定」を追うには
公表時点のファイルを自分で保存し続けるしかなく、**過去分は原理的に復元できない**。

米国は ALFRED があり全 vintage を遡れる。この非対称が設計の中心にある。

## 使い方

```bash
uv run --no-sync macrokit status          # 指標の実装状態を一覧
uv run --no-sync macrokit catalog list    # カタログの内容
```

## テスト

```bash
uv run --no-sync pytest macrokit/tests           # ネットワーク不要
uv run --no-sync pytest macrokit/tests -m live   # 実 API を叩く（要 FRED_API_KEY）
```
```

Create `macrokit/.gitignore`:

```gitignore
data/
```

- [ ] **Step 4: Register the member in the root pyproject**

In the root `pyproject.toml`, add `"macrokit"` to the end of the `[tool.uv.workspace] members` list, and add `"macrokit/tests"` to the end of the `[tool.pytest.ini_options] testpaths` list.

- [ ] **Step 5: Add the import to the root conftest**

In the root `conftest.py`, add `import macrokit  # noqa: F401` to the import block, keeping the list alphabetically sorted (it goes between `jp_llm_lab` and `optimal_execution`). Then extend the docstring's parenthetical list of projects that need this to include `macrokit`.

- [ ] **Step 6: Add the data directory to .agentignore**

Append `macrokit/data/` to `.agentignore`.

- [ ] **Step 7: Install the package into the shared venv**

Run: `uv pip install -e macrokit --no-deps`
Expected: `Successfully installed macrokit-0.1.0`.

Use `--no-deps` because every dependency is already present in the shared venv; a full resolve is unnecessary and slow. (This matches how `analytics/machine_learning` was added.)

- [ ] **Step 8: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_package.py -v`
Expected: 2 passed.

- [ ] **Step 9: Verify the full-workspace run still collects**

Run: `uv run --no-sync pytest --collect-only -q 2>&1 | tail -5`
Expected: a collected-count line with no errors, and no `(unknown location)` in the output. `(unknown location)` is the signature of the namespace-shadow bug — if it appears, Step 5 was not applied correctly.

- [ ] **Step 10: Commit**

```bash
git add macrokit/pyproject.toml macrokit/README.md macrokit/.gitignore \
        macrokit/src/macrokit/__init__.py macrokit/tests/test_package.py \
        pyproject.toml conftest.py .agentignore
git commit -m "Add the macrokit package skeleton"
```

---

### Task 2: Catalog schema and loader

**Files:**
- Create: `macrokit/src/macrokit/catalog.py`
- Create: `macrokit/tests/test_catalog.py`
- Create: `macrokit/tests/fixtures/catalog_ok/us/prices.yaml`
- Create: `macrokit/tests/fixtures/catalog_ok/jp/labor.yaml`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `class ReleaseRule(BaseModel)` with fields `kind: Literal["nth_business_day","fixed_day","nth_weekday","manual"]`, `n: int | None`, `day: int | None`, `weekday: int | None`, `time: str`, `tz: str`, `calendar: Literal["jp","us"]`
  - `class Chain(BaseModel)` with `upstream: list[str]`, `downstream: list[str]`
  - `class Indicator(BaseModel)` with `name, country, block, title_ja, source, source_ref: dict, freq, unit, sa, release_lag_days, release_rule: ReleaseRule | None, vintage, chain: Chain, caveats: list[str]`
  - `def load_catalog(root: Path) -> dict[str, Indicator]`
  - `class CatalogError(Exception)`

- [ ] **Step 1: Write the fixture catalogs**

Create `macrokit/tests/fixtures/catalog_ok/us/prices.yaml`:

```yaml
- name: us_core_pce
  country: US
  block: prices
  title_ja: コア PCE デフレーター（食品・エネルギー除く）
  source: alfred
  source_ref:
    series_id: PCEPILFE
  freq: M
  unit: index_2017_100
  sa: sa
  release_lag_days: 30
  vintage: alfred
  chain:
    downstream: [us_core_pce_yoy]
  caveats:
    - Fed の公式ターゲットはヘッドライン PCE の 2%。コアは基調を見るための指標

- name: us_core_pce_yoy
  country: US
  block: prices
  title_ja: コア PCE 前年比
  source: alfred
  source_ref:
    series_id: PCEPILFE
  freq: M
  unit: percent
  sa: sa
  release_lag_days: 30
  vintage: alfred
  chain:
    upstream: [us_core_pce]
```

Create `macrokit/tests/fixtures/catalog_ok/jp/labor.yaml`:

```yaml
- name: jp_scheduled_earnings
  country: JP
  block: labor
  title_ja: 所定内給与（一般労働者・共通事業所）
  source: estat
  source_ref:
    stats_id: "0003084821"
  freq: M
  unit: yen
  sa: nsa
  release_lag_days: 35
  release_rule:
    kind: nth_business_day
    n: 5
    time: "08:30"
    tz: Asia/Tokyo
    calendar: jp
  vintage: snapshot
  chain: {}
  caveats:
    - サンプル入替で断層が出る。前年比は「共通事業所」ベースを使う
```

- [ ] **Step 2: Write the failing test**

Create `macrokit/tests/test_catalog.py`:

```python
from pathlib import Path

import pytest

from macrokit.catalog import CatalogError, Indicator, load_catalog

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_every_indicator_across_country_directories():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert set(catalog) == {"us_core_pce", "us_core_pce_yoy", "jp_scheduled_earnings"}
    assert isinstance(catalog["us_core_pce"], Indicator)


def test_keeps_source_specific_fields_verbatim():
    # source_ref is deliberately untyped: each source has its own identifier
    # shape (series_id vs stats_id vs tenor), and the adapter owns that meaning.
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert catalog["us_core_pce"].source_ref == {"series_id": "PCEPILFE"}
    assert catalog["jp_scheduled_earnings"].source_ref == {"stats_id": "0003084821"}


def test_japanese_indicators_declare_snapshot_vintage():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    assert catalog["jp_scheduled_earnings"].vintage == "snapshot"
    assert catalog["us_core_pce"].vintage == "alfred"


def test_release_rule_is_parsed_when_present_and_none_when_absent():
    catalog = load_catalog(FIXTURES / "catalog_ok")
    rule = catalog["jp_scheduled_earnings"].release_rule
    assert rule is not None
    assert rule.kind == "nth_business_day"
    assert rule.n == 5
    assert rule.tz == "Asia/Tokyo"
    # US indicators get their calendar from the FRED releases API, not a rule.
    assert catalog["us_core_pce"].release_rule is None


def test_rejects_duplicate_names(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: dup, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred}\n",
        encoding="utf-8",
    )
    (tmp_path / "us" / "b.yaml").write_text(
        "- {name: dup, country: US, block: prices, title_ja: B, source: alfred,\n"
        "   source_ref: {series_id: Y}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="duplicate indicator name: dup"):
        load_catalog(tmp_path)


def test_rejects_chain_reference_to_a_missing_indicator(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: real, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred,\n"
        "   chain: {downstream: [ghost]}}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="real.downstream refers to unknown indicator: ghost"):
        load_catalog(tmp_path)


def test_rejects_a_cycle_in_the_chain_graph(tmp_path):
    (tmp_path / "jp").mkdir()
    (tmp_path / "jp" / "a.yaml").write_text(
        "- {name: a, country: JP, block: prices, title_ja: A, source: estat,\n"
        "   source_ref: {stats_id: '1'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [b]}}\n"
        "- {name: b, country: JP, block: prices, title_ja: B, source: estat,\n"
        "   source_ref: {stats_id: '2'}, freq: M, unit: u, sa: nsa,\n"
        "   release_lag_days: 1, vintage: snapshot, chain: {downstream: [a]}}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="cycle in chain graph"):
        load_catalog(tmp_path)


def test_rejects_an_unknown_field_so_typos_do_not_pass_silently(tmp_path):
    (tmp_path / "us").mkdir()
    (tmp_path / "us" / "a.yaml").write_text(
        "- {name: a, country: US, block: prices, title_ja: A, source: alfred,\n"
        "   source_ref: {series_id: X}, freq: M, unit: u, sa: sa,\n"
        "   release_lag_days: 1, vintage: alfred, viantge: typo}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogError, match="viantge"):
        load_catalog(tmp_path)
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_catalog.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.catalog'`.

- [ ] **Step 4: Implement the catalog module**

Create `macrokit/src/macrokit/catalog.py`:

```python
"""Indicator catalog: one YAML entry per indicator.

The catalog is the single source of truth for what exists and where it comes
from. It deliberately does NOT record implementation status -- status is derived
from reality (adapters, snapshots, database rows) in `status.py`, because a
hand-written status field always rots.

`source_ref` is an untyped dict on purpose: every source identifies series
differently (`series_id` for FRED, `stats_id` for e-Stat, a tenor for MoF), and
the owning adapter is what gives those keys meaning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CatalogError(Exception):
    """A catalog file is malformed or internally inconsistent."""


class ReleaseRule(BaseModel):
    """When a Japanese statistic is published.

    US indicators leave this unset: their calendar comes from the FRED
    `releases/dates` endpoint, which is authoritative and free.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["nth_business_day", "fixed_day", "nth_weekday", "manual"]
    n: int | None = None
    day: int | None = None
    weekday: int | None = None
    time: str = "00:00"
    tz: str = "Asia/Tokyo"
    calendar: Literal["jp", "us"] = "jp"


class Chain(BaseModel):
    """Causal links to other indicators, e.g. shunto -> earnings -> real wage."""

    model_config = ConfigDict(extra="forbid")

    upstream: list[str] = Field(default_factory=list)
    downstream: list[str] = Field(default_factory=list)


class Indicator(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    country: Literal["JP", "US"]
    block: Literal[
        "prices", "labor", "activity", "demand", "capex", "external", "policy", "market"
    ]
    title_ja: str
    source: str
    source_ref: dict
    freq: Literal["D", "W", "M", "Q", "A"]
    unit: str
    sa: Literal["sa", "nsa"]
    release_lag_days: int
    release_rule: ReleaseRule | None = None
    vintage: Literal["alfred", "snapshot", "none"]
    chain: Chain = Field(default_factory=Chain)
    caveats: list[str] = Field(default_factory=list)


def load_catalog(root: Path) -> dict[str, Indicator]:
    """Load every ``*.yaml`` under ``root`` and validate the catalog as a whole."""
    catalog: dict[str, Indicator] = {}
    for path in sorted(root.rglob("*.yaml")):
        entries = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for entry in entries:
            try:
                indicator = Indicator(**entry)
            except ValidationError as exc:
                raise CatalogError(f"{path}: {exc}") from exc
            if indicator.name in catalog:
                raise CatalogError(f"duplicate indicator name: {indicator.name} ({path})")
            catalog[indicator.name] = indicator

    _check_chain_references(catalog)
    _check_no_cycles(catalog)
    return catalog


def _check_chain_references(catalog: dict[str, Indicator]) -> None:
    for name, indicator in catalog.items():
        for direction in ("upstream", "downstream"):
            for target in getattr(indicator.chain, direction):
                if target not in catalog:
                    raise CatalogError(
                        f"{name}.{direction} refers to unknown indicator: {target}"
                    )


def _check_no_cycles(catalog: dict[str, Indicator]) -> None:
    """Depth-first search over downstream edges, tracking the active path."""
    WHITE, GREY, BLACK = 0, 1, 2
    colour = dict.fromkeys(catalog, WHITE)

    def visit(name: str, path: list[str]) -> None:
        colour[name] = GREY
        for target in catalog[name].chain.downstream:
            if colour[target] == GREY:
                raise CatalogError(f"cycle in chain graph: {' -> '.join([*path, name, target])}")
            if colour[target] == WHITE:
                visit(target, [*path, name])
        colour[name] = BLACK

    for name in catalog:
        if colour[name] == WHITE:
            visit(name, [])
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_catalog.py -v`
Expected: 8 passed.

- [ ] **Step 6: Lint**

Run: `uv run --no-sync ruff check macrokit && uv run --no-sync ruff format --check macrokit`
Expected: `All checks passed!`. If `format --check` reports files, run `uv run --no-sync ruff format macrokit` and re-run.

- [ ] **Step 7: Commit**

```bash
git add macrokit/src/macrokit/catalog.py macrokit/tests/test_catalog.py macrokit/tests/fixtures
git commit -m "Add the indicator catalog schema and loader"
```

---

### Task 3: Holiday calendar and release-rule resolution

**Files:**
- Create: `macrokit/src/macrokit/holidays.py`
- Create: `macrokit/src/macrokit/release.py`
- Create: `macrokit/tests/test_release.py`
- Create: `macrokit/tests/fixtures/syukujitsu_sample.csv`

**Interfaces:**
- Consumes: `ReleaseRule` from `macrokit.catalog`.
- Produces:
  - `def parse_holiday_csv(raw: bytes) -> set[date]`
  - `def load_holidays(cache_dir: Path, *, fetch: bool = True) -> set[date]`
  - `HOLIDAY_CSV_URL: str`
  - `def nth_business_day(year: int, month: int, n: int, holidays: set[date]) -> date`
  - `def resolve_release(rule: ReleaseRule, period_end: date, holidays: set[date]) -> datetime | None` (timezone-aware; `None` for `kind="manual"`)

- [ ] **Step 1: Create the holiday fixture**

Create `macrokit/tests/fixtures/syukujitsu_sample.csv` with **cp932 encoding**. Generate it with this command so the encoding is correct:

```bash
python3 - <<'PY'
from pathlib import Path
rows = [
    "国民の祝日・休日月日,国民の祝日・休日名称",
    "2026/1/1,元日",
    "2026/1/12,成人の日",
    "2026/2/11,建国記念の日",
    "2026/2/23,天皇誕生日",
    "2026/5/3,憲法記念日",
    "2026/5/4,みどりの日",
    "2026/5/5,こどもの日",
    "2026/5/6,休日",
]
p = Path("macrokit/tests/fixtures/syukujitsu_sample.csv")
p.write_bytes(("\r\n".join(rows) + "\r\n").encode("cp932"))
print("wrote", p, p.stat().st_size, "bytes")
PY
```

- [ ] **Step 2: Write the failing test**

Create `macrokit/tests/test_release.py`:

```python
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from macrokit.catalog import ReleaseRule
from macrokit.holidays import load_holidays, parse_holiday_csv
from macrokit.release import nth_business_day, resolve_release

FIXTURES = Path(__file__).parent / "fixtures"


def test_parses_the_cabinet_office_csv_which_is_cp932_not_utf8():
    raw = (FIXTURES / "syukujitsu_sample.csv").read_bytes()
    # Guard the premise: if this ever decodes as UTF-8 the fixture is wrong.
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")

    holidays = parse_holiday_csv(raw)
    assert date(2026, 1, 1) in holidays
    assert date(2026, 5, 6) in holidays  # 振替休日 also appears, named 休日
    assert date(2026, 1, 2) not in holidays


def test_load_holidays_reads_the_cache_without_network(tmp_path):
    # tmp_path, not the fixtures directory: a test must never leave a cache
    # behind in the repo.
    (tmp_path / "syukujitsu.csv").write_bytes((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    holidays = load_holidays(tmp_path, fetch=False)
    assert date(2026, 5, 5) in holidays


def test_load_holidays_refuses_to_fetch_when_told_not_to(tmp_path):
    with pytest.raises(FileNotFoundError, match="fetch=False"):
        load_holidays(tmp_path, fetch=False)


def test_nth_business_day_skips_weekends_and_holidays():
    holidays = parse_holiday_csv((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    # 2026-01: 1(Thu) is 元日, 2(Fri) and 5(Mon) are business days,
    # 3-4 weekend, so business days run 2, 5, 6, 7, 8, ...
    assert nth_business_day(2026, 1, 1, holidays) == date(2026, 1, 2)
    assert nth_business_day(2026, 1, 2, holidays) == date(2026, 1, 5)
    assert nth_business_day(2026, 1, 5, holidays) == date(2026, 1, 8)


def test_nth_business_day_raises_when_the_month_is_too_short():
    with pytest.raises(ValueError, match="month 2026-02 has no 25th business day"):
        nth_business_day(2026, 2, 25, set())


def test_resolve_release_for_nth_business_day_returns_an_aware_datetime():
    holidays = parse_holiday_csv((FIXTURES / "syukujitsu_sample.csv").read_bytes())
    rule = ReleaseRule(kind="nth_business_day", n=5, time="14:00", tz="Asia/Tokyo", calendar="jp")
    # Period ending 2025-12-31 is published in the month after the period ends.
    got = resolve_release(rule, date(2025, 12, 31), holidays)
    assert got == datetime(2026, 1, 8, 14, 0, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_for_fixed_day():
    rule = ReleaseRule(kind="fixed_day", day=19, time="08:30", tz="Asia/Tokyo", calendar="jp")
    got = resolve_release(rule, date(2026, 1, 31), set())
    assert got == datetime(2026, 2, 19, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_for_nth_weekday():
    # 3rd Friday of the month after the period. 2026-02: Fridays are 6, 13, 20.
    rule = ReleaseRule(
        kind="nth_weekday", n=3, weekday=4, time="08:30", tz="Asia/Tokyo", calendar="jp"
    )
    got = resolve_release(rule, date(2026, 1, 31), set())
    assert got == datetime(2026, 2, 20, 8, 30, tzinfo=ZoneInfo("Asia/Tokyo"))


def test_resolve_release_returns_none_for_manual_rules():
    rule = ReleaseRule(kind="manual", tz="Asia/Tokyo", calendar="jp")
    assert resolve_release(rule, date(2026, 1, 31), set()) is None
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_release.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.holidays'`.

- [ ] **Step 4: Implement the holidays module**

Create `macrokit/src/macrokit/holidays.py`:

```python
"""Japanese public holidays, taken from the Cabinet Office's official CSV.

Using the government file rather than a third-party package keeps the production
dependency count at zero and makes holidays just another government data source,
consistent with everything else this package fetches.

The file is cp932 (Shift-JIS), not UTF-8, and covers 1955 through the following
year. Rows look like `2026/1/1,元日`; substitute holidays appear under the name
`休日` and count as holidays too, so every dated row is taken.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from pathlib import Path

import httpx

HOLIDAY_CSV_URL = "https://www8.cao.go.jp/chosei/shukujitsu/syukujitsu.csv"


def parse_holiday_csv(raw: bytes) -> set[date]:
    """Parse the Cabinet Office holiday CSV into a set of dates."""
    text = raw.decode("cp932")
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # header: 国民の祝日・休日月日,国民の祝日・休日名称
    holidays: set[date] = set()
    for row in reader:
        if not row or not row[0].strip():
            continue
        year, month, day = (int(part) for part in row[0].strip().split("/"))
        holidays.add(date(year, month, day))
    return holidays


def load_holidays(cache_dir: Path, *, fetch: bool = True) -> set[date]:
    """Return Japanese holidays, downloading and caching the CSV if needed.

    ``fetch=False`` makes this offline-only, which is what tests and any
    no-network run want.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / "syukujitsu.csv"
    if not cached.exists():
        if not fetch:
            raise FileNotFoundError(f"no cached holiday CSV at {cached} and fetch=False")
        response = httpx.get(HOLIDAY_CSV_URL, timeout=30.0)
        response.raise_for_status()
        cached.write_bytes(response.content)
    return parse_holiday_csv(cached.read_bytes())
```

- [ ] **Step 5: Implement the release module**

Create `macrokit/src/macrokit/release.py`:

```python
"""Resolve a catalog ReleaseRule into a concrete publication datetime.

Japanese agencies publish on regular rules ("5th business day", "the 19th",
"3rd Friday"), so declaring the rule in YAML avoids scraping the schedule pages.
US indicators do not use this at all -- FRED's releases/dates endpoint gives
their calendar directly, including future dates.

Every rule is relative to the month AFTER the period ends, which is how monthly
Japanese statistics are published.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .catalog import ReleaseRule


def nth_business_day(year: int, month: int, n: int, holidays: set[date]) -> date:
    """The nth business day of a month (1-indexed), skipping weekends and holidays."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    days_in_month = calendar.monthrange(year, month)[1]
    seen = 0
    for day in range(1, days_in_month + 1):
        candidate = date(year, month, day)
        if candidate.weekday() >= 5 or candidate in holidays:
            continue
        seen += 1
        if seen == n:
            return candidate
    raise ValueError(f"month {year}-{month:02d} has no {n}th business day")


def nth_weekday(year: int, month: int, n: int, weekday: int) -> date:
    """The nth occurrence of a weekday in a month. ``weekday`` is Mon=0 .. Sun=6."""
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    days_in_month = calendar.monthrange(year, month)[1]
    seen = 0
    for day in range(1, days_in_month + 1):
        candidate = date(year, month, day)
        if candidate.weekday() != weekday:
            continue
        seen += 1
        if seen == n:
            return candidate
    raise ValueError(f"month {year}-{month:02d} has no {n}th weekday {weekday}")


def _month_after(period_end: date) -> tuple[int, int]:
    first_of_next = (period_end.replace(day=1) + timedelta(days=32)).replace(day=1)
    return first_of_next.year, first_of_next.month


def resolve_release(
    rule: ReleaseRule, period_end: date, holidays: set[date]
) -> datetime | None:
    """Publication datetime for the period ending ``period_end``.

    Returns ``None`` for ``kind="manual"``: the schedule is not expressible as a
    rule and must be supplied by hand.
    """
    if rule.kind == "manual":
        return None

    year, month = _month_after(period_end)
    if rule.kind == "nth_business_day":
        if rule.n is None:
            raise ValueError("nth_business_day requires n")
        day = nth_business_day(year, month, rule.n, holidays)
    elif rule.kind == "fixed_day":
        if rule.day is None:
            raise ValueError("fixed_day requires day")
        day = date(year, month, rule.day)
    elif rule.kind == "nth_weekday":
        if rule.n is None or rule.weekday is None:
            raise ValueError("nth_weekday requires n and weekday")
        day = nth_weekday(year, month, rule.n, rule.weekday)
    else:  # pragma: no cover - Literal keeps this unreachable
        raise ValueError(f"unknown release rule kind: {rule.kind}")

    hour, minute = (int(part) for part in rule.time.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=ZoneInfo(rule.tz))
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_release.py -v`
Expected: 9 passed.

- [ ] **Step 7: Verify the real CSV parses too**

Run:

```bash
uv run --no-sync python -c "
from pathlib import Path
from macrokit.holidays import load_holidays
h = load_holidays(Path('macrokit/data/cache'))
print('holidays:', len(h), 'min:', min(h), 'max:', max(h))
"
```

Expected: over 1000 holidays, min `1955-01-01`, max in 2027 or later. This is the one network call in this task; it writes to the gitignored `macrokit/data/cache/`.

- [ ] **Step 8: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/holidays.py macrokit/src/macrokit/release.py \
        macrokit/tests/test_release.py macrokit/tests/fixtures/syukujitsu_sample.csv
git commit -m "Resolve Japanese release schedules from declared rules"
```

---

### Task 4: DuckDB schema and observation store

**Files:**
- Create: `macrokit/src/macrokit/periods.py`
- Create: `macrokit/src/macrokit/store.py`
- Create: `macrokit/tests/test_store.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `def period_end_for(period_start: date, freq: str) -> date`
  - `@dataclass(frozen=True) class Observation` with fields `indicator: str, period_start: date, period_end: date, release_date: datetime, vintage_seq: int, value: float, unit: str, sa: str, freq: str, source: str, source_url: str, ingested_at: datetime, vintage_kind: str`
  - `VINTAGE_KINDS: frozenset[str]` = `{"actual", "snapshot", "estimated"}`
  - `def connect(db_path: Path) -> duckdb.DuckDBPyConnection`
  - `def insert_observations(con, rows: list[Observation]) -> int`

- [ ] **Step 1: Write the failing test**

Create `macrokit/tests/test_store.py`:

```python
from datetime import date, datetime, timezone

import pytest

from macrokit.periods import period_end_for
from macrokit.store import Observation, connect, insert_observations

UTC = timezone.utc


def _obs(**kw) -> Observation:
    base = dict(
        indicator="us_core_pce",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        release_date=datetime(2024, 4, 1, tzinfo=UTC),
        vintage_seq=1,
        value=120.849,
        unit="index_2017_100",
        sa="sa",
        freq="M",
        source="alfred",
        source_url="https://api.stlouisfed.org/fred/series/observations",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        vintage_kind="actual",
    )
    return Observation(**{**base, **kw})


@pytest.mark.parametrize(
    ("start", "freq", "expected"),
    [
        (date(2024, 1, 1), "M", date(2024, 1, 31)),
        (date(2024, 2, 1), "M", date(2024, 2, 29)),  # leap year
        (date(2024, 1, 1), "Q", date(2024, 3, 31)),
        (date(2024, 10, 1), "Q", date(2024, 12, 31)),
        (date(2024, 1, 1), "A", date(2024, 12, 31)),
        (date(2024, 1, 3), "D", date(2024, 1, 3)),
        (date(2024, 1, 1), "W", date(2024, 1, 7)),
    ],
)
def test_period_end_is_derived_from_frequency(start, freq, expected):
    assert period_end_for(start, freq) == expected


def test_round_trips_an_observation(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    assert insert_observations(con, [_obs()]) == 1
    got = con.execute(
        "SELECT indicator, period_start, value, vintage_kind FROM observations"
    ).fetchall()
    assert got == [("us_core_pce", date(2024, 1, 1), 120.849, "actual")]


def test_inserting_the_same_vintage_twice_does_not_duplicate(tmp_path):
    # Re-ingesting an unchanged series must be idempotent, otherwise a daily
    # cron run would multiply every row it has already seen.
    con = connect(tmp_path / "t.duckdb")
    insert_observations(con, [_obs()])
    insert_observations(con, [_obs()])
    assert con.execute("SELECT count(*) FROM observations").fetchone()[0] == 1


def test_rejects_an_unknown_vintage_kind(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    with pytest.raises(ValueError, match="unknown vintage_kind: guessed"):
        insert_observations(con, [_obs(vintage_kind="guessed")])


def test_rejects_a_snapshot_released_after_it_was_ingested(tmp_path):
    # A snapshot's release_date is reconstructed from when WE fetched it, so a
    # release_date in the future of ingested_at means the reconstruction is wrong.
    con = connect(tmp_path / "t.duckdb")
    bad = _obs(
        vintage_kind="snapshot",
        release_date=datetime(2026, 9, 1, tzinfo=UTC),
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    with pytest.raises(ValueError, match="release_date after ingested_at"):
        insert_observations(con, [bad])


def test_allows_an_actual_release_date_before_ingestion(tmp_path):
    # ALFRED legitimately reports release dates years before we fetched them.
    con = connect(tmp_path / "t.duckdb")
    assert insert_observations(con, [_obs(release_date=datetime(2020, 1, 1, tzinfo=UTC))]) == 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_store.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.periods'`.

- [ ] **Step 3: Implement the periods module**

Create `macrokit/src/macrokit/periods.py`:

```python
"""Map a period start plus a frequency onto the period end.

Sources report the period by its first day (FRED returns `2024-01-01` for
January 2024). Storing the end as well makes "what period does this cover"
answerable without knowing the frequency at query time.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta


def period_end_for(period_start: date, freq: str) -> date:
    if freq == "D":
        return period_start
    if freq == "W":
        return period_start + timedelta(days=6)
    if freq == "M":
        return period_start.replace(day=calendar.monthrange(period_start.year, period_start.month)[1])
    if freq == "Q":
        end_month = period_start.month + 2
        return date(period_start.year, end_month, calendar.monthrange(period_start.year, end_month)[1])
    if freq == "A":
        return date(period_start.year, 12, 31)
    raise ValueError(f"unknown frequency: {freq}")
```

- [ ] **Step 4: Implement the store module**

Create `macrokit/src/macrokit/store.py`:

```python
"""DuckDB store. One row per observation *vintage*, never one row per period.

The whole point of this table is that a period can hold several values -- the
flash estimate and each revision -- each tagged with when it was released. Code
that wants "the current value" asks `pit.latest`; code that wants "what was
knowable then" asks `pit.as_of`.

`vintage_kind` records how much to trust `release_date`:
  actual    -- the source published the release date (ALFRED, US Treasury)
  snapshot  -- reconstructed from when we fetched it (every Japanese source)
  estimated -- inferred from a publication lag; weakest of the three
"""

from __future__ import annotations

from dataclasses import astuple, dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

VINTAGE_KINDS = frozenset({"actual", "snapshot", "estimated"})

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS observations (
  indicator     VARCHAR   NOT NULL,
  period_start  DATE      NOT NULL,
  period_end    DATE      NOT NULL,
  release_date  TIMESTAMPTZ NOT NULL,
  vintage_seq   INTEGER   NOT NULL,
  value         DOUBLE    NOT NULL,
  unit          VARCHAR   NOT NULL,
  sa            VARCHAR   NOT NULL,
  freq          VARCHAR   NOT NULL,
  source        VARCHAR   NOT NULL,
  source_url    VARCHAR   NOT NULL,
  ingested_at   TIMESTAMPTZ NOT NULL,
  vintage_kind  VARCHAR   NOT NULL,
  PRIMARY KEY (indicator, period_start, release_date)
);

CREATE TABLE IF NOT EXISTS components (
  indicator      VARCHAR NOT NULL,
  component_code VARCHAR NOT NULL,
  component_name VARCHAR NOT NULL,
  weight         DOUBLE,
  period_start   DATE    NOT NULL,
  release_date   TIMESTAMPTZ NOT NULL,
  value          DOUBLE,
  PRIMARY KEY (indicator, component_code, period_start, release_date)
);
"""


@dataclass(frozen=True)
class Observation:
    indicator: str
    period_start: date
    period_end: date
    release_date: datetime
    vintage_seq: int
    value: float
    unit: str
    sa: str
    freq: str
    source: str
    source_url: str
    ingested_at: datetime
    vintage_kind: str


def connect(db_path: Path) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the database and ensure the schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    con.execute(SCHEMA_SQL)
    return con


def _validate(row: Observation) -> None:
    if row.vintage_kind not in VINTAGE_KINDS:
        raise ValueError(f"unknown vintage_kind: {row.vintage_kind}")
    if row.vintage_kind == "snapshot" and row.release_date > row.ingested_at:
        raise ValueError(
            f"{row.indicator} {row.period_start}: snapshot has release_date after "
            f"ingested_at ({row.release_date} > {row.ingested_at})"
        )


def insert_observations(con: duckdb.DuckDBPyConnection, rows: list[Observation]) -> int:
    """Insert rows, ignoring ones already present. Returns the number inserted."""
    for row in rows:
        _validate(row)
    before = con.execute("SELECT count(*) FROM observations").fetchone()[0]
    con.executemany(
        "INSERT OR IGNORE INTO observations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [astuple(row) for row in rows],
    )
    after = con.execute("SELECT count(*) FROM observations").fetchone()[0]
    return after - before
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_store.py -v`
Expected: 12 passed (7 parametrized cases plus 5 tests).

- [ ] **Step 6: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/periods.py macrokit/src/macrokit/store.py macrokit/tests/test_store.py
git commit -m "Store observations as one row per vintage"
```

---

### Task 5: Point-in-time queries and their invariants

**Files:**
- Create: `macrokit/src/macrokit/pit.py`
- Create: `macrokit/tests/test_pit.py`

**Interfaces:**
- Consumes: `connect`, `insert_observations`, `Observation` from `macrokit.store`.
- Produces:
  - `def as_of(con, indicator: str, when: datetime) -> pd.Series` (indexed by `period_start`, named `value`)
  - `def latest(con, indicator: str) -> pd.Series`
  - `def revisions(con, indicator: str, period_start: date) -> pd.DataFrame` (columns `release_date`, `value`, `vintage_seq`, `vintage_kind`)

- [ ] **Step 1: Write the failing test**

Create `macrokit/tests/test_pit.py`:

```python
from datetime import date, datetime, timezone

import pandas as pd

from macrokit.pit import as_of, latest, revisions
from macrokit.store import Observation, connect, insert_observations

UTC = timezone.utc


def _seed(con) -> None:
    """Two periods. January was revised twice; February was released once.

    January:  2024-04-01 -> 120.849, then 2024-04-26 -> 120.909
    February: 2024-04-26 -> 121.100
    """
    common = dict(
        indicator="us_core_pce",
        unit="index_2017_100",
        sa="sa",
        freq="M",
        source="alfred",
        source_url="https://example.invalid",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        vintage_kind="actual",
    )
    insert_observations(
        con,
        [
            Observation(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                release_date=datetime(2024, 4, 1, tzinfo=UTC),
                vintage_seq=1,
                value=120.849,
                **common,
            ),
            Observation(
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                release_date=datetime(2024, 4, 26, tzinfo=UTC),
                vintage_seq=2,
                value=120.909,
                **common,
            ),
            Observation(
                period_start=date(2024, 2, 1),
                period_end=date(2024, 2, 29),
                release_date=datetime(2024, 4, 26, tzinfo=UTC),
                vintage_seq=1,
                value=121.100,
                **common,
            ),
        ],
    )


def test_as_of_returns_the_latest_vintage_released_on_or_before_the_date(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    assert got.loc[date(2024, 1, 1)] == 120.849  # the revision has not happened yet


def test_as_of_never_includes_a_release_in_the_future_of_the_query(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    # February was only released on 2024-04-26, so it must be absent entirely.
    assert date(2024, 2, 1) not in got.index


def test_as_of_does_not_forward_fill(tmp_path):
    # A period with no release on or before the date is ABSENT, not carried
    # forward from a neighbour. Forward-filling here would invent data that no
    # analyst could have seen.
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    assert list(got.index) == [date(2024, 1, 1)]
    assert not got.isna().any()


def test_as_of_before_any_release_is_empty(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = as_of(con, "us_core_pce", datetime(2024, 1, 1, tzinfo=UTC))
    assert got.empty


def test_as_of_today_equals_latest(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    pd.testing.assert_series_equal(
        as_of(con, "us_core_pce", datetime(2030, 1, 1, tzinfo=UTC)),
        latest(con, "us_core_pce"),
    )


def test_latest_takes_the_most_recent_revision(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = latest(con, "us_core_pce")
    assert got.loc[date(2024, 1, 1)] == 120.909
    assert got.loc[date(2024, 2, 1)] == 121.100


def test_revisions_lists_every_vintage_for_one_period_in_order(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    got = revisions(con, "us_core_pce", date(2024, 1, 1))
    assert list(got["value"]) == [120.849, 120.909]
    assert list(got["vintage_seq"]) == [1, 2]
    assert list(got.columns) == ["release_date", "value", "vintage_seq", "vintage_kind"]


def test_vintage_seq_is_dense_and_starts_at_one_per_period(tmp_path):
    con = connect(tmp_path / "t.duckdb")
    _seed(con)
    rows = con.execute(
        "SELECT period_start, list(vintage_seq ORDER BY release_date) "
        "FROM observations WHERE indicator = 'us_core_pce' GROUP BY period_start"
    ).fetchall()
    for _period, seqs in rows:
        assert seqs == list(range(1, len(seqs) + 1))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_pit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.pit'`.

- [ ] **Step 3: Implement the pit module**

Create `macrokit/src/macrokit/pit.py`:

```python
"""Point-in-time access. The single guard against look-ahead via revised data.

`as_of(con, indicator, when)` answers "what could an analyst actually have known
on this date": for each period, the latest vintage whose release_date is at or
before `when`. Periods first released after `when` are absent -- this function
never forward-fills, because inventing a value for a period nobody had yet is
exactly the bug it exists to prevent.
"""

from __future__ import annotations

from datetime import date, datetime

import duckdb
import pandas as pd

_AS_OF_SQL = """
SELECT period_start, value
FROM (
  SELECT period_start, value,
         row_number() OVER (PARTITION BY period_start ORDER BY release_date DESC) AS rn
  FROM observations
  WHERE indicator = ? AND release_date <= ?
)
WHERE rn = 1
ORDER BY period_start
"""

_LATEST_SQL = """
SELECT period_start, value
FROM (
  SELECT period_start, value,
         row_number() OVER (PARTITION BY period_start ORDER BY release_date DESC) AS rn
  FROM observations
  WHERE indicator = ?
)
WHERE rn = 1
ORDER BY period_start
"""

_REVISIONS_SQL = """
SELECT release_date, value, vintage_seq, vintage_kind
FROM observations
WHERE indicator = ? AND period_start = ?
ORDER BY release_date
"""


def _to_series(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype="float64", name="value")
    series = frame.set_index("period_start")["value"]
    series.name = "value"
    series.index.name = "period_start"
    return series


def as_of(con: duckdb.DuckDBPyConnection, indicator: str, when: datetime) -> pd.Series:
    """Values visible at ``when``, indexed by period_start. Never forward-filled."""
    return _to_series(con.execute(_AS_OF_SQL, [indicator, when]).df())


def latest(con: duckdb.DuckDBPyConnection, indicator: str) -> pd.Series:
    """Latest-vintage values, revisions included."""
    return _to_series(con.execute(_LATEST_SQL, [indicator]).df())


def revisions(
    con: duckdb.DuckDBPyConnection, indicator: str, period_start: date
) -> pd.DataFrame:
    """Every vintage recorded for one period, oldest release first."""
    return con.execute(_REVISIONS_SQL, [indicator, period_start]).df()
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_pit.py -v`
Expected: 8 passed.

If `test_as_of_today_equals_latest` fails on dtype, it means one branch returned an empty series; check that `_seed` inserted all three rows.

- [ ] **Step 5: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/pit.py macrokit/tests/test_pit.py
git commit -m "Reconstruct what was knowable on a date"
```

---

### Task 6: Raw snapshot layer with content-hash deduplication

**Files:**
- Create: `macrokit/src/macrokit/snapshot.py`
- Create: `macrokit/tests/test_snapshot.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass(frozen=True) class SnapshotResult` with `path: Path | None, sha256: str, changed: bool, size: int`
  - `def save_snapshot(root: Path, source: str, indicator: str, content: bytes, *, ingested_at: datetime, url: str, http_status: int, filename: str = "payload") -> SnapshotResult`
  - `def last_sha(root: Path, source: str, indicator: str) -> str | None`
  - `def manifest_path(root: Path) -> Path`

- [ ] **Step 1: Write the failing test**

Create `macrokit/tests/test_snapshot.py`:

```python
import json
from datetime import datetime, timezone

from macrokit.snapshot import last_sha, manifest_path, save_snapshot

UTC = timezone.utc


def _save(root, content, *, day, indicator="jp_cpi_core"):
    return save_snapshot(
        root,
        "estat",
        indicator,
        content,
        ingested_at=datetime(2026, 8, day, 9, 0, tzinfo=UTC),
        url="https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData",
        http_status=200,
        filename="payload.json",
    )


def test_first_save_writes_the_file_and_reports_a_change(tmp_path):
    result = _save(tmp_path, b'{"a": 1}', day=17)
    assert result.changed is True
    assert result.path is not None
    assert result.path.read_bytes() == b'{"a": 1}'
    assert result.size == 8


def test_identical_content_on_a_later_day_is_not_stored_again(tmp_path):
    # Publishing is idempotent between revisions: fetching the same file every
    # day must not fill the disk with copies. Only a CHANGE is worth storing.
    _save(tmp_path, b'{"a": 1}', day=17)
    second = _save(tmp_path, b'{"a": 1}', day=18)
    assert second.changed is False
    assert second.path is None
    stored = list(tmp_path.rglob("payload.json"))
    assert len(stored) == 1


def test_changed_content_is_stored_alongside_the_original(tmp_path):
    # A change IS the revision event -- this is where RevisionShock comes from.
    _save(tmp_path, b'{"a": 1}', day=17)
    second = _save(tmp_path, b'{"a": 2}', day=18)
    assert second.changed is True
    stored = sorted(p.parent.name for p in tmp_path.rglob("payload.json"))
    assert stored == ["2026-08-17", "2026-08-18"]


def test_every_attempt_is_recorded_in_the_manifest_even_when_unchanged(tmp_path):
    _save(tmp_path, b'{"a": 1}', day=17)
    _save(tmp_path, b'{"a": 1}', day=18)
    lines = manifest_path(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert [r["changed"] for r in records] == [True, False]
    assert records[0]["source"] == "estat"
    assert records[0]["indicator"] == "jp_cpi_core"
    assert records[0]["http_status"] == 200
    assert len(records[0]["sha256"]) == 64


def test_last_sha_tracks_indicators_independently(tmp_path):
    _save(tmp_path, b"one", day=17, indicator="a")
    _save(tmp_path, b"two", day=17, indicator="b")
    assert last_sha(tmp_path, "estat", "a") != last_sha(tmp_path, "estat", "b")
    assert last_sha(tmp_path, "estat", "never_fetched") is None


def test_stored_snapshots_are_never_overwritten(tmp_path):
    # Immutability is the whole guarantee: the Japanese vintage record is only
    # as trustworthy as the promise that a stored file is never rewritten.
    first = _save(tmp_path, b"original", day=17)
    assert first.path is not None
    _save(tmp_path, b"different", day=17)
    assert first.path.read_bytes() == b"original"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_snapshot.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.snapshot'`.

- [ ] **Step 3: Implement the snapshot module**

Create `macrokit/src/macrokit/snapshot.py`:

```python
"""Immutable raw snapshots, deduplicated by content hash.

This layer is the entire reason Japanese vintages can exist at all. e-Stat and
the ministry CSVs publish by overwriting, so the only record of "what the value
was before the revision" is a copy we took at the time. Nothing here is ever
rewritten.

Deduplication is not just a disk optimisation. Because a stored file appears
only when the bytes changed, the set of stored dates IS the set of revision
dates -- RevisionShock detection falls out of the storage layer for free.

Layout::

    {root}/{source}/{indicator}/{ingested_date}/{filename}
    {root}/manifest.jsonl
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class SnapshotResult:
    path: Path | None  # None when the content was unchanged and not stored
    sha256: str
    changed: bool
    size: int


def manifest_path(root: Path) -> Path:
    return root / "manifest.jsonl"


def last_sha(root: Path, source: str, indicator: str) -> str | None:
    """SHA-256 of the most recent *stored* payload, or None if never stored."""
    manifest = manifest_path(root)
    if not manifest.exists():
        return None
    newest: str | None = None
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record["source"] == source and record["indicator"] == indicator:
            newest = record["sha256"]
    return newest


def save_snapshot(
    root: Path,
    source: str,
    indicator: str,
    content: bytes,
    *,
    ingested_at: datetime,
    url: str,
    http_status: int,
    filename: str = "payload",
) -> SnapshotResult:
    """Store ``content`` unless it matches the last stored payload.

    Every attempt is appended to the manifest, changed or not, so the fetch
    history stays complete even when nothing was written.
    """
    digest = hashlib.sha256(content).hexdigest()
    changed = digest != last_sha(root, source, indicator)

    target: Path | None = None
    if changed:
        directory = root / source / indicator / ingested_at.date().isoformat()
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / filename
        if not target.exists():
            target.write_bytes(content)

    root.mkdir(parents=True, exist_ok=True)
    record = {
        "ingested_at": ingested_at.isoformat(),
        "source": source,
        "indicator": indicator,
        "url": url,
        "sha256": digest,
        "bytes": len(content),
        "changed": changed,
        "http_status": http_status,
        "path": str(target.relative_to(root)) if target else None,
    }
    with manifest_path(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    return SnapshotResult(path=target, sha256=digest, changed=changed, size=len(content))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_snapshot.py -v`
Expected: 6 passed.

- [ ] **Step 5: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/snapshot.py macrokit/tests/test_snapshot.py
git commit -m "Keep immutable raw snapshots deduplicated by content hash"
```

---

### Task 7: ALFRED adapter

**Files:**
- Create: `macrokit/src/macrokit/sources/__init__.py`
- Create: `macrokit/src/macrokit/sources/alfred.py`
- Create: `macrokit/tests/test_alfred.py`
- Create: `macrokit/tests/fixtures/alfred_pcepilfe.json`

**Interfaces:**
- Consumes: `Indicator` from `macrokit.catalog`; `Observation` from `macrokit.store`; `period_end_for` from `macrokit.periods`.
- Produces:
  - `class AlfredAdapter` with `source = "alfred"`, `probe(self, indicator: Indicator) -> str | None`, `fetch_raw(self, indicator: Indicator, start: date) -> tuple[bytes, str, int]` returning `(content, url, http_status)`, `parse(self, indicator: Indicator, raw: bytes, *, ingested_at: datetime) -> list[Observation]`
  - `AlfredAdapter.__init__(self, api_key=_UNSET, *, client: httpx.Client | None = None)` — the module-level `_UNSET = object()` sentinel means `AlfredAdapter()` reads `FRED_API_KEY` from the environment while `AlfredAdapter(api_key=None)` deliberately has no key. Do not replace the sentinel with a `None` default: the two cases must stay distinguishable or the missing-key test passes only on machines without the key set.

- [ ] **Step 1: Record the fixture from the live API**

Run this once. It reads the key from the environment and **must not print it**:

```bash
set -a; . stock/.env; set +a
curl -sS "https://api.stlouisfed.org/fred/series/observations?series_id=PCEPILFE&api_key=${FRED_API_KEY}&file_type=json&observation_start=2024-01-01&observation_end=2024-02-01&realtime_start=2024-04-01&realtime_end=2024-12-31" \
  | python3 -m json.tool > macrokit/tests/fixtures/alfred_pcepilfe.json
grep -c api_key macrokit/tests/fixtures/alfred_pcepilfe.json
```

Expected: the `grep -c` prints `0`. **If it prints anything else, the key leaked into the fixture — delete the file and stop.** FRED does not echo the key, so `0` is the expected result.

Then confirm the shape:

```bash
python3 -c "
import json; d=json.load(open('macrokit/tests/fixtures/alfred_pcepilfe.json'))
print('count', d['count']); print(d['observations'][0])"
```

Expected: several observations for `date` `2024-01-01`, each with a distinct `realtime_start`, e.g. `{'realtime_start': '2024-04-01', 'realtime_end': '2024-04-25', 'date': '2024-01-01', 'value': '120.849'}`.

- [ ] **Step 2: Write the failing test**

Create `macrokit/tests/test_alfred.py`:

```python
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from macrokit.catalog import Indicator
from macrokit.sources.alfred import AlfredAdapter

UTC = timezone.utc
FIXTURES = Path(__file__).parent / "fixtures"

INDICATOR = Indicator(
    name="us_core_pce",
    country="US",
    block="prices",
    title_ja="コア PCE デフレーター",
    source="alfred",
    source_ref={"series_id": "PCEPILFE"},
    freq="M",
    unit="index_2017_100",
    sa="sa",
    release_lag_days=30,
    vintage="alfred",
)


def _parse():
    adapter = AlfredAdapter(api_key="dummy")
    raw = (FIXTURES / "alfred_pcepilfe.json").read_bytes()
    return adapter.parse(INDICATOR, raw, ingested_at=datetime(2026, 8, 17, tzinfo=UTC))


def test_each_realtime_start_becomes_one_vintage_row():
    rows = _parse()
    january = [r for r in rows if r.period_start == date(2024, 1, 1)]
    assert len(january) > 1, "core PCE for 2024-01 was revised more than once"
    assert len({r.release_date for r in january}) == len(january)


def test_realtime_start_is_used_as_the_release_date():
    rows = _parse()
    first = min(
        (r for r in rows if r.period_start == date(2024, 1, 1)), key=lambda r: r.release_date
    )
    assert first.release_date == datetime(2024, 4, 1, tzinfo=UTC)
    assert first.value == pytest.approx(120.849)


def test_vintage_seq_is_dense_from_one_per_period():
    rows = _parse()
    january = sorted(
        (r for r in rows if r.period_start == date(2024, 1, 1)), key=lambda r: r.release_date
    )
    assert [r.vintage_seq for r in january] == list(range(1, len(january) + 1))


def test_us_rows_are_actual_vintages_not_snapshots():
    # ALFRED publishes the real release date, which is exactly what Japanese
    # sources cannot do. Mislabelling this would erase the distinction.
    assert all(r.vintage_kind == "actual" for r in _parse())


def test_period_end_is_filled_in_from_the_frequency():
    rows = _parse()
    january = next(r for r in rows if r.period_start == date(2024, 1, 1))
    assert january.period_end == date(2024, 1, 31)


def test_missing_values_are_dropped_not_stored_as_zero():
    # FRED encodes "no value" as the string ".", which float() would reject and
    # a careless parser might coerce to 0.0.
    adapter = AlfredAdapter(api_key="dummy")
    payload = json.dumps(
        {
            "observations": [
                {
                    "realtime_start": "2024-04-01",
                    "realtime_end": "9999-12-31",
                    "date": "2024-01-01",
                    "value": ".",
                },
                {
                    "realtime_start": "2024-04-01",
                    "realtime_end": "9999-12-31",
                    "date": "2024-02-01",
                    "value": "121.1",
                },
            ]
        }
    ).encode()
    rows = adapter.parse(INDICATOR, payload, ingested_at=datetime(2026, 8, 17, tzinfo=UTC))
    assert [r.period_start for r in rows] == [date(2024, 2, 1)]


def test_missing_api_key_fails_with_a_clear_message():
    adapter = AlfredAdapter(api_key=None)
    with pytest.raises(RuntimeError, match="FRED_API_KEY is not set"):
        adapter.fetch_raw(INDICATOR, date(2024, 1, 1))


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("FRED_API_KEY"), reason="FRED_API_KEY is not set")
def test_live_fetch_returns_multiple_vintages_for_a_revised_month():
    adapter = AlfredAdapter()
    raw, url, status = adapter.fetch_raw(INDICATOR, date(2024, 1, 1))
    assert status == 200
    assert "api.stlouisfed.org" in url
    rows = adapter.parse(INDICATOR, raw, ingested_at=datetime.now(UTC))
    january = [r for r in rows if r.period_start == date(2024, 1, 1)]
    assert len(january) > 1


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("FRED_API_KEY"), reason="FRED_API_KEY is not set")
def test_live_probe_returns_the_most_recent_vintage_date():
    # probe() is the cheap "did anything change" check that Plan 2 leans on for
    # every source; it is exercised here so it does not ship untested.
    latest_vintage = AlfredAdapter().probe(INDICATOR)
    assert latest_vintage is not None
    assert date.fromisoformat(latest_vintage) > date(2024, 1, 1)
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_alfred.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.sources'`.

- [ ] **Step 4: Implement the adapter**

Create `macrokit/src/macrokit/sources/__init__.py`:

```python
"""Per-source adapters.

Each adapter implements three methods and nothing else:

  probe(indicator)     -- cheapest possible check for "has anything changed"
  fetch_raw(indicator) -- the bytes, exactly as the source served them
  parse(indicator)     -- those bytes as Observation rows

They are deliberately separable. An adapter with `fetch_raw` but no working
`parse` still reaches the `fetching` state, which is enough to start banking
snapshots -- and for Japanese sources, snapshots taken today are the only
vintages that will ever exist for today.
"""
```

Create `macrokit/src/macrokit/sources/alfred.py`:

```python
"""FRED / ALFRED adapter.

ALFRED is the archival face of FRED: with `realtime_start`/`realtime_end` set to
a range, one observation date returns several rows, one per vintage, and
`realtime_start` is that vintage's release date. That is why US indicators get
`vintage_kind="actual"` while every Japanese source gets "snapshot".

FRED also mirrors BLS, BEA and Census, so CPI, PCE, GDP, NFP and JOLTS all
arrive here with revision history attached -- which is why this project does not
hold API keys for those three agencies.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timezone
from itertools import groupby

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..catalog import Indicator
from ..periods import period_end_for
from ..store import Observation

BASE = "https://api.stlouisfed.org/fred"
FAR_FUTURE = "9999-12-31"
_UNSET = object()


class AlfredAdapter:
    source = "alfred"

    def __init__(self, api_key: str | None | object = _UNSET, *, client: httpx.Client | None = None):
        # The sentinel distinguishes "caller passed nothing, read the env" from
        # "caller passed None on purpose", which is how the missing-key test
        # forces the error path even on a machine where FRED_API_KEY is set.
        self.api_key = os.environ.get("FRED_API_KEY") if api_key is _UNSET else api_key
        self._client = client

    def _require_key(self) -> str:
        if not self.api_key:
            raise RuntimeError("FRED_API_KEY is not set (free key from fred.stlouisfed.org)")
        return self.api_key

    def _get(self, path: str, params: dict) -> httpx.Response:
        client = self._client or httpx.Client(timeout=60.0)
        try:
            return self._request(client, path, params)
        finally:
            if self._client is None:
                client.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
    def _request(self, client: httpx.Client, path: str, params: dict) -> httpx.Response:
        response = client.get(f"{BASE}/{path}", params=params)
        response.raise_for_status()
        return response

    def probe(self, indicator: Indicator) -> str | None:
        """Latest vintage date for the series, or None if it has never been revised.

        `series/vintagedates` omits release dates on which the values did not
        change, so a stable tail here means there is genuinely nothing new.
        """
        response = self._get(
            "series/vintagedates",
            {
                "series_id": indicator.source_ref["series_id"],
                "api_key": self._require_key(),
                "file_type": "json",
            },
        )
        dates = response.json().get("vintage_dates", [])
        return dates[-1] if dates else None

    def fetch_raw(self, indicator: Indicator, start: date) -> tuple[bytes, str, int]:
        """All vintages from ``start`` onward. Returns (content, url, status)."""
        response = self._get(
            "series/observations",
            {
                "series_id": indicator.source_ref["series_id"],
                "api_key": self._require_key(),
                "file_type": "json",
                "observation_start": start.isoformat(),
                "realtime_start": "1776-07-04",  # FRED's documented earliest realtime
                "realtime_end": FAR_FUTURE,
            },
        )
        # Strip the key before the URL is recorded anywhere.
        url = str(response.url).split("&api_key=")[0]
        return response.content, url, response.status_code

    def parse(
        self, indicator: Indicator, raw: bytes, *, ingested_at: datetime
    ) -> list[Observation]:
        payload = json.loads(raw)
        parsed = []
        for item in payload.get("observations", []):
            if item["value"] == ".":  # FRED's missing-value marker
                continue
            parsed.append(
                (
                    date.fromisoformat(item["date"]),
                    datetime.fromisoformat(item["realtime_start"]).replace(tzinfo=timezone.utc),
                    float(item["value"]),
                )
            )

        rows: list[Observation] = []
        parsed.sort(key=lambda triple: (triple[0], triple[1]))
        for period_start, group in groupby(parsed, key=lambda triple: triple[0]):
            for seq, (_period, release_date, value) in enumerate(group, start=1):
                rows.append(
                    Observation(
                        indicator=indicator.name,
                        period_start=period_start,
                        period_end=period_end_for(period_start, indicator.freq),
                        release_date=release_date,
                        vintage_seq=seq,
                        value=value,
                        unit=indicator.unit,
                        sa=indicator.sa,
                        freq=indicator.freq,
                        source=self.source,
                        source_url=f"{BASE}/series/observations",
                        ingested_at=ingested_at,
                        vintage_kind="actual",
                    )
                )
        return rows
```

- [ ] **Step 5: Run the offline tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_alfred.py -v -m "not live"`
Expected: 7 passed, 2 deselected.

- [ ] **Step 6: Run the live tests**

Run: `set -a; . stock/.env; set +a; uv run --no-sync pytest macrokit/tests/test_alfred.py -v -m live`
Expected: 2 passed.

- [ ] **Step 7: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/sources macrokit/tests/test_alfred.py \
        macrokit/tests/fixtures/alfred_pcepilfe.json
git commit -m "Read every ALFRED vintage as its own observation"
```

---

### Task 8: Wire core PCE end to end

**Files:**
- Create: `macrokit/catalog/us/prices.yaml`
- Create: `macrokit/src/macrokit/ingest.py`
- Create: `macrokit/tests/test_ingest.py`

**Interfaces:**
- Consumes: `load_catalog`, `AlfredAdapter`, `save_snapshot`, `connect`, `insert_observations`, `as_of`.
- Produces:
  - `def default_catalog_root() -> Path`
  - `ADAPTERS: dict[str, type]` mapping `"alfred"` to `AlfredAdapter`
  - `@dataclass(frozen=True) class IngestReport` with `indicator: str, changed: bool, rows_inserted: int, skipped_reason: str | None`
  - `def ingest_one(indicator: Indicator, *, con, data_root: Path, adapter, start: date, now: datetime) -> IngestReport`

- [ ] **Step 1: Write the production catalog entry**

Create `macrokit/catalog/us/prices.yaml`:

```yaml
- name: us_core_pce
  country: US
  block: prices
  title_ja: コア PCE デフレーター（食品・エネルギー除く、2017=100）
  source: alfred
  source_ref:
    series_id: PCEPILFE
  freq: M
  unit: index_2017_100
  sa: sa
  release_lag_days: 30
  vintage: alfred
  chain: {}
  caveats:
    - Fed の公式ターゲットはヘッドライン PCE の 2%。コアは基調を見るための指標
    - BEA 原統計だが FRED 経由で取得する。直接 API と違い vintage が付くため
```

- [ ] **Step 2: Write the failing test**

Create `macrokit/tests/test_ingest.py`:

```python
from datetime import date, datetime, timezone
from pathlib import Path

from macrokit.catalog import load_catalog
from macrokit.ingest import default_catalog_root, ingest_one
from macrokit.pit import as_of, latest
from macrokit.store import connect

UTC = timezone.utc
FIXTURES = Path(__file__).parent / "fixtures"


class FakeAdapter:
    """Serves the recorded ALFRED payload, so this test needs no network."""

    source = "alfred"

    def __init__(self, payload: bytes):
        self.payload = payload
        self.fetch_count = 0

    def fetch_raw(self, indicator, start):
        self.fetch_count += 1
        return self.payload, "https://example.invalid/fred", 200

    def parse(self, indicator, raw, *, ingested_at):
        from macrokit.sources.alfred import AlfredAdapter

        return AlfredAdapter(api_key="dummy").parse(indicator, raw, ingested_at=ingested_at)


def test_the_production_catalog_loads_and_contains_core_pce():
    catalog = load_catalog(default_catalog_root())
    assert "us_core_pce" in catalog
    assert catalog["us_core_pce"].source_ref["series_id"] == "PCEPILFE"


def test_ingest_stores_a_snapshot_and_inserts_rows(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")

    report = ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )

    assert report.changed is True
    assert report.rows_inserted > 0
    assert list((tmp_path / "raw").rglob("payload.json"))


def test_a_second_unchanged_ingest_inserts_nothing_new(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")
    kwargs = dict(
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
    )

    ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 17, tzinfo=UTC), **kwargs)
    second = ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 18, tzinfo=UTC), **kwargs)

    assert second.changed is False
    assert second.rows_inserted == 0
    assert second.skipped_reason == "content unchanged"
    # The payload must NOT be parsed again when nothing changed.
    assert adapter.fetch_count == 2


def test_point_in_time_query_works_after_ingest(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")
    ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )

    early = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    current = latest(con, "us_core_pce")

    # The whole point of the platform: the value you would have seen in April
    # 2024 differs from today's value for the same month.
    assert early.loc[date(2024, 1, 1)] != current.loc[date(2024, 1, 1)]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run --no-sync pytest macrokit/tests/test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.ingest'`.

- [ ] **Step 4: Implement the ingest module**

Create `macrokit/src/macrokit/ingest.py`:

```python
"""Ingestion: snapshot first, parse second.

The order matters. `save_snapshot` runs before anything is parsed, so a source
whose parser is unwritten or broken still banks its bytes. For Japanese sources
that is not a nicety -- a day not snapshotted is a vintage that can never be
recovered.

Parsing is skipped entirely when the content hash is unchanged, which is the
common case on a daily schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from .catalog import Indicator
from .snapshot import save_snapshot
from .sources.alfred import AlfredAdapter
from .store import insert_observations

ADAPTERS: dict[str, type] = {"alfred": AlfredAdapter}


def default_catalog_root() -> Path:
    """The catalog shipped with the package (``macrokit/catalog``)."""
    return Path(__file__).resolve().parents[2] / "catalog"


@dataclass(frozen=True)
class IngestReport:
    indicator: str
    changed: bool
    rows_inserted: int
    skipped_reason: str | None = None


def ingest_one(
    indicator: Indicator,
    *,
    con: duckdb.DuckDBPyConnection,
    data_root: Path,
    adapter,
    start: date,
    now: datetime,
) -> IngestReport:
    content, url, status = adapter.fetch_raw(indicator, start)

    suffix = "json" if content.lstrip()[:1] in (b"{", b"[") else "csv"
    result = save_snapshot(
        data_root,
        adapter.source,
        indicator.name,
        content,
        ingested_at=now,
        url=url,
        http_status=status,
        filename=f"payload.{suffix}",
    )

    if not result.changed:
        return IngestReport(indicator.name, False, 0, "content unchanged")

    rows = adapter.parse(indicator, content, ingested_at=now)
    inserted = insert_observations(con, rows)
    return IngestReport(indicator.name, True, inserted)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run --no-sync pytest macrokit/tests/test_ingest.py -v`
Expected: 4 passed.

`test_point_in_time_query_works_after_ingest` is the one that proves the platform works: the January 2024 value seen in April 2024 differs from today's. If it fails with equal values, the fixture was recorded with too narrow a realtime window — re-record it with `realtime_start=2024-04-01&realtime_end=2024-12-31`.

- [ ] **Step 6: Lint and commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/catalog macrokit/src/macrokit/ingest.py macrokit/tests/test_ingest.py
git commit -m "Ingest core PCE from ALFRED into the point-in-time store"
```

---

### Task 9: Status derivation and CLI

**Files:**
- Create: `macrokit/src/macrokit/status.py`
- Create: `macrokit/src/macrokit/cli.py`
- Create: `macrokit/tests/test_status.py`
- Create: `macrokit/tests/test_cli.py`

**Interfaces:**
- Consumes: `load_catalog`, `default_catalog_root`, `ADAPTERS`, `connect`, `manifest_path`.
- Produces:
  - `STATUS_ORDER: tuple[str, ...]` = `("declared", "fetching", "parsed", "validated")`
  - `def compute_status(indicator: Indicator, *, con, data_root: Path, validated: set[str]) -> str`
  - `def load_validated(data_root: Path) -> set[str]`
  - `def main() -> None` (click group with `status` and `catalog list` subcommands)

- [ ] **Step 1: Write the failing test**

Create `macrokit/tests/test_status.py`:

```python
import json
from datetime import date, datetime, timezone
from pathlib import Path

from macrokit.catalog import load_catalog
from macrokit.ingest import default_catalog_root, ingest_one
from macrokit.status import compute_status, load_validated
from macrokit.store import connect

UTC = timezone.utc
FIXTURES = Path(__file__).parent / "fixtures"


class FakeAdapter:
    source = "alfred"

    def fetch_raw(self, indicator, start):
        return (FIXTURES / "alfred_pcepilfe.json").read_bytes(), "https://example.invalid", 200

    def parse(self, indicator, raw, *, ingested_at):
        from macrokit.sources.alfred import AlfredAdapter

        return AlfredAdapter(api_key="dummy").parse(indicator, raw, ingested_at=ingested_at)


def test_an_indicator_with_no_snapshot_is_only_declared(tmp_path):
    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "declared"


def test_status_reaches_parsed_after_a_successful_ingest(tmp_path):
    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=FakeAdapter(),
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "parsed"


def test_status_is_fetching_when_snapshots_exist_but_no_rows_do(tmp_path):
    # This is the state that matters most for Japan: bytes are banked even
    # though nothing has been parsed yet.
    from macrokit.snapshot import save_snapshot

    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    save_snapshot(
        tmp_path / "raw",
        "alfred",
        "us_core_pce",
        b"{}",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        url="https://example.invalid",
        http_status=200,
    )
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "fetching"


def test_validated_is_read_from_the_marker_file(tmp_path):
    (tmp_path / "validated.json").write_text(
        json.dumps({"indicators": ["us_core_pce"]}), encoding="utf-8"
    )
    assert load_validated(tmp_path) == {"us_core_pce"}
    assert load_validated(tmp_path / "missing") == set()
```

Create `macrokit/tests/test_cli.py`:

```python
from click.testing import CliRunner

from macrokit.cli import main


def test_catalog_list_prints_every_indicator():
    result = CliRunner().invoke(main, ["catalog", "list"])
    assert result.exit_code == 0
    assert "us_core_pce" in result.output


def test_status_runs_against_an_empty_database(tmp_path):
    result = CliRunner().invoke(main, ["--data-root", str(tmp_path), "status"])
    assert result.exit_code == 0
    assert "us_core_pce" in result.output
    assert "declared" in result.output
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --no-sync pytest macrokit/tests/test_status.py macrokit/tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'macrokit.status'`.

- [ ] **Step 3: Implement the status module**

Create `macrokit/src/macrokit/status.py`:

```python
"""Derive each indicator's implementation state from reality, never from YAML.

A hand-written `status:` field in the catalog rots the moment someone implements
an adapter and forgets to update it. So status is computed:

  declared  -- present in the catalog
  fetching  -- the manifest records at least one fetch
  parsed    -- the observations table holds rows for it
  validated -- listed in data/validated.json, written by the validation run

`fetching` is the load-bearing rung. Reaching it means snapshots are accruing,
which for Japanese sources is the only way their vintages will ever exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

from .catalog import Indicator
from .snapshot import manifest_path

STATUS_ORDER: tuple[str, ...] = ("declared", "fetching", "parsed", "validated")


def load_validated(data_root: Path) -> set[str]:
    marker = data_root / "validated.json"
    if not marker.exists():
        return set()
    return set(json.loads(marker.read_text(encoding="utf-8")).get("indicators", []))


def _has_snapshot(data_root: Path, indicator: str) -> bool:
    manifest = manifest_path(data_root)
    if not manifest.exists():
        return False
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if line.strip() and json.loads(line)["indicator"] == indicator:
            return True
    return False


def compute_status(
    indicator: Indicator,
    *,
    con: duckdb.DuckDBPyConnection,
    data_root: Path,
    validated: set[str],
) -> str:
    if indicator.name in validated:
        return "validated"
    rows = con.execute(
        "SELECT count(*) FROM observations WHERE indicator = ?", [indicator.name]
    ).fetchone()[0]
    if rows:
        return "parsed"
    if _has_snapshot(data_root, indicator.name):
        return "fetching"
    return "declared"
```

- [ ] **Step 4: Implement the CLI**

Create `macrokit/src/macrokit/cli.py`:

```python
"""Command line entry point."""

from __future__ import annotations

from pathlib import Path

import click

from .catalog import load_catalog
from .ingest import default_catalog_root
from .status import compute_status, load_validated
from .store import connect


@click.group()
@click.option(
    "--data-root",
    type=click.Path(path_type=Path),
    default=Path("macrokit/data"),
    show_default=True,
    help="Where snapshots and the DuckDB file live.",
)
@click.pass_context
def main(ctx: click.Context, data_root: Path) -> None:
    """macrokit -- point-in-time macro indicators for Japan and the US."""
    ctx.ensure_object(dict)
    ctx.obj["data_root"] = data_root
    ctx.obj["catalog"] = load_catalog(default_catalog_root())


@main.group("catalog")
def catalog_group() -> None:
    """Inspect the indicator catalog."""


@catalog_group.command("list")
@click.pass_context
def catalog_list(ctx: click.Context) -> None:
    for name, indicator in sorted(ctx.obj["catalog"].items()):
        click.echo(f"{name:<28} {indicator.country}  {indicator.block:<10} {indicator.title_ja}")


@main.command("status")
@click.pass_context
def status_command(ctx: click.Context) -> None:
    """Show each indicator's derived implementation state."""
    data_root: Path = ctx.obj["data_root"]
    con = connect(data_root / "macrokit.duckdb")
    validated = load_validated(data_root)
    raw_root = data_root / "raw"

    counts: dict[str, int] = {}
    for name, indicator in sorted(ctx.obj["catalog"].items()):
        state = compute_status(indicator, con=con, data_root=raw_root, validated=validated)
        counts[state] = counts.get(state, 0) + 1
        click.echo(f"{name:<28} {state}")

    click.echo("")
    click.echo("  ".join(f"{state}={counts.get(state, 0)}" for state in ("declared", "fetching", "parsed", "validated")))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run --no-sync pytest macrokit/tests/test_status.py macrokit/tests/test_cli.py -v`
Expected: 6 passed.

- [ ] **Step 6: Verify the installed console script works**

Run: `uv run --no-sync macrokit catalog list`
Expected: one line for `us_core_pce`.

Run: `uv run --no-sync macrokit status`
Expected: `us_core_pce  declared` and a summary line (unless a real ingest has run).

- [ ] **Step 7: Run the whole project suite**

Run: `uv run --no-sync pytest macrokit/tests -v -m "not live"`
Expected: 62 passed, 2 deselected (2 package + 8 catalog + 9 release + 12 store + 8 pit + 6 snapshot + 7 alfred + 4 ingest + 6 status/cli).

- [ ] **Step 8: Verify the full workspace is still green**

Run: `uv run --no-sync pytest -q 2>&1 | tail -5`
Expected: the pass count is the prior baseline (3050 passed, 45 skipped) **plus** macrokit's tests, with 0 failures. A failure here means Task 1's conftest change regressed — check for `(unknown location)` in the output.

Run: `make lint`
Expected: `All checks passed!`.

- [ ] **Step 9: Commit**

```bash
uv run --no-sync ruff check macrokit && uv run --no-sync ruff format macrokit
git add macrokit/src/macrokit/status.py macrokit/src/macrokit/cli.py \
        macrokit/tests/test_status.py macrokit/tests/test_cli.py
git commit -m "Derive indicator status from reality and expose it on the CLI"
```

---

## Done when

- `uv run --no-sync macrokit status` reports `us_core_pce`.
- A live ingest of core PCE produces a raw snapshot, rows in `observations`, and `as_of(2024-04-10)` differing from `latest()` for January 2024.
- `uv run --no-sync pytest macrokit/tests -m "not live"` is green with no network.
- The full-workspace `pytest` and `make lint` are green.

## Not in this plan

Two pieces of spec §5 are deliberately deferred, because with a single indicator
they would have nothing to do:

- **Layers 1 and 2 of the three-layer diff detection** (spec §5.3). Plan 1
  implements layer 3 only — fetch, then compare the content hash. The calendar
  check and the `probe()`-based metadata check exist as building blocks
  (`resolve_release`, `AlfredAdapter.probe`) but nothing calls them yet, and
  `macrokit ingest --due-only` does not exist. They earn their keep in Plan 2,
  where 50 series make a daily full fetch actually expensive.
- **Rate limiting** (spec §5.4). Task 7 has retry with exponential backoff via
  `tenacity`, but no request-per-minute throttle. One indicator cannot trip a
  limit; the throttle belongs with multi-source ingestion.

Phases 2–6 of the spec, in later plans:

- **Plan 2 (Phases 2–3):** the remaining ~50 catalog entries, and `fetch_raw` for e-Stat / BoJ / MoF / Cabinet Office / METI / Treasury so every series reaches `fetching` and Japanese vintage accrual starts. **This is the schedule-critical plan** — every day it slips is a Japanese vintage that cannot be recovered.
- **Plan 3 (Phases 4–5):** `parse` per source, cross-source validation against FRED's Japanese mirrors, transforms (MoM / YoY / 3m and 6m annualised / contribution / breadth), the `components` table, and the FRED release calendar.
- **Plan 4 (Phase 6):** confirmation notebook, `macrokit calendar`, and the cron discussion.
