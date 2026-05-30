# Market Grounding v1 Implementation Plan

> **⚠️ SUPERSEDED / DEFERRED (2026-05-30):** MVP再定義により "Later" へ棚上げ。実装着手しない。
> 現行優先は `docs/design/2026-05-30-mvp-redefinition-design.md`（Spec 1: 分析コア再定義）。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive re_invest_os score/risk with real market data (官公庁API + 自律リサーチ) via a provider-registry service, with provenance, area cache, and snapshot freezing — and stop the "no market data ⇒ full marks" inflation.

**Architecture:** A new `apps/api/src/api/services/market/` subsystem: `MarketSnapshot` (provenance + confidence per metric) is produced by a `MarketDataService` that merges pluggable providers (Official land price = sync, Rent research = slow/injectable), caches by area key, and freezes into `analysis_runs`. The pure `re_engine` only consumes adapted Pydantic inputs; `score.py` gains coverage-aware market components.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, SQLAlchemy async + aiosqlite, httpx, existing `services/llm_client.py`. Frontend: Next.js (App Router) + TypeScript.

**Spec:** `docs/design/2026-05-30-market-grounding-v1-design.md`

**Design corrections vs spec (honest):**
1. `market_cap_rate` is sourced from `RentResearchProvider` (investment listing yields, confidence C), NOT a transaction "cap proxy" — official transaction data lacks rent. Official provider supplies `land_price_per_sqm` + `transaction_price_per_sqm`.
2. App runtime cannot call Claude Code's WebSearch. `RentResearchProvider` depends on an injectable `WebResearchClient` (httpx + existing LLM extraction). Concrete live source (search API key or fixed source pages) is a deployment decision; provider degrades gracefully (returns `None`, confidence lowered) when unconfigured.
3. v1 cache uses **whole-snapshot TTL** (`built_at` + `ttl_days = min(metric TTLs)`); per-metric partial refresh is deferred.

---

## File Structure

**Create:**
- `apps/api/src/api/services/market/__init__.py` — public exports
- `apps/api/src/api/services/market/snapshot.py` — `MetricValue`, `MarketSnapshot`, adapters
- `apps/api/src/api/services/market/providers/__init__.py` — provider registry
- `apps/api/src/api/services/market/providers/base.py` — `MarketDataProvider` protocol, `ProviderResult`
- `apps/api/src/api/services/market/providers/official.py` — `OfficialLandPriceProvider`
- `apps/api/src/api/services/market/providers/rent_research.py` — `RentResearchProvider`, `WebResearchClient` protocol
- `apps/api/src/api/services/market/cache.py` — `MarketSnapshotCache` (SQLAlchemy)
- `apps/api/src/api/services/market/service.py` — `MarketDataService`
- `apps/api/tests/test_market_snapshot.py`
- `apps/api/tests/test_market_service.py`
- `apps/api/tests/test_market_provider_official.py`
- `apps/api/tests/test_market_provider_rent.py`
- `apps/api/tests/fixtures/market/xpt002_shinjuku.json`
- `apps/api/tests/fixtures/market/rent_shinjuku.json`
- `infra/migrations/v3_market_snapshots.sql`
- `apps/web/src/app/api/market/route.ts` — Next.js proxy
- `apps/web/src/components/market-context-panel.tsx`

**Modify:**
- `packages/financial-engine/src/re_engine/score.py` — `covered` field, `market_coverage`, coverage fix
- `packages/financial-engine/tests/test_score.py` — new coverage tests
- `apps/api/src/api/routers/deals.py` — wire snapshot into `create_analysis_run`
- `apps/api/src/api/db.py` — apply v3 migration (follow v2 pattern)
- `apps/api/src/api/services/market_context.py` — DELETE (replaced by `market/`)
- `apps/web/src/app/report/page.tsx` — mount `MarketContextPanel`
- `docs/architecture/calculation_engine_spec.md` — §5.6 score coverage note

---

## Task 1: `score.py` coverage fix (pure engine, no deps)

Do this first: it's pure, has no new dependencies, and locks the contract the service feeds.

**Files:**
- Modify: `packages/financial-engine/src/re_engine/score.py`
- Test: `packages/financial-engine/tests/test_score.py`

- [ ] **Step 1: Write failing tests**

Append to `packages/financial-engine/tests/test_score.py`:

```python
def test_missing_market_is_not_full_marks(base_assumptions: Assumptions) -> None:
    """市場データ無しのとき price/rent は満点でなく中立配点 (50%)。"""
    result = run_full_analysis(base_assumptions)
    s = total_score(result)  # market_context=None
    price = next(c for c in s.components if c.name == "price")
    rent = next(c for c in s.components if c.name == "rent")
    assert price.covered is False
    assert rent.covered is False
    assert price.score == price.max_score * 0.5
    assert rent.score == rent.max_score * 0.5


def test_market_coverage_zero_without_market(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    s = total_score(result)
    assert s.market_coverage == 0.0


def test_market_coverage_full_with_market(base_assumptions: Assumptions) -> None:
    result = run_full_analysis(base_assumptions)
    ctx = MarketContext(
        market_cap_rate=0.05,
        market_rent_per_sqm_yen=3000,
        property_rent_per_sqm_yen=3000,
    )
    s = total_score(result, market_context=ctx)
    price = next(c for c in s.components if c.name == "price")
    rent = next(c for c in s.components if c.name == "rent")
    assert price.covered is True
    assert rent.covered is True
    assert s.market_coverage == 1.0
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_score.py -k "coverage or full_marks" -v`
Expected: FAIL — `ScoreComponent` has no `covered`; `ScoreResult` has no `market_coverage`.

- [ ] **Step 3: Add fields**

In `score.py`, add `covered` to `ScoreComponent` and `market_coverage` to `ScoreResult`:

```python
class ScoreComponent(BaseModel):
    name: str
    score: float  # 配点 (0 〜 max)
    max_score: float
    detail: str
    covered: bool = True  # 市場依存項目が実データで賄えたか
    model_config = ConfigDict(extra="forbid")


class ScoreResult(BaseModel):
    total: float  # 0〜100
    components: list[ScoreComponent]
    evaluation: str  # "健全" / "中立" / "要警戒"
    market_coverage: float = 1.0  # 市場依存配点のうち実データで賄えた割合 (0.0–1.0)
    model_config = ConfigDict(extra="forbid")
```

- [ ] **Step 4: Fix `_price_score` missing-market branch**

Replace the `if ctx.market_cap_rate is None:` block inside `_price_score`:

```python
    if ctx.market_cap_rate is None:
        # 市場Cap未取得 → 満点を与えず中立配点 (買い手側 critique 原則)
        return ScoreComponent(
            name="price",
            score=max_score * 0.5,
            max_score=max_score,
            detail=f"Cap {cap * 100:.2f}% (市場Cap未取得・中立配点)",
            covered=False,
        )
```

(The `else:` branch that compares against `ctx.market_cap_rate` is unchanged and returns `covered=True` by default.)

- [ ] **Step 5: Fix `_rent_score` missing-market branch**

Replace the early `return` when market rent is missing:

```python
    if (
        ctx.market_rent_per_sqm_yen is None
        or ctx.property_rent_per_sqm_yen is None
        or ctx.market_rent_per_sqm_yen <= 0
    ):
        return ScoreComponent(
            name="rent",
            score=max_score * 0.5,
            max_score=max_score,
            detail="賃料相場未取得・中立配点",
            covered=False,
        )
```

- [ ] **Step 6: Compute `market_coverage` in `total_score`**

In `total_score`, after building `components` and before building `ScoreResult`:

```python
    market_names = {"price", "rent"}
    md = [c for c in components if c.name in market_names]
    denom = sum(c.max_score for c in md)
    covered_max = sum(c.max_score for c in md if c.covered)
    market_coverage = (covered_max / denom) if denom > 0 else 1.0
```

And add `market_coverage=market_coverage` to the returned `ScoreResult(...)`.

- [ ] **Step 7: Bump score spec version comment**

At the top of `score.py`, change the docstring first line to:

```python
"""100点スコア (score_spec_version 0.2.0)。

market データ欠落時は満点でなく中立配点 (coverage 調整)。
仕様: docs/architecture/calculation_engine_spec.md §5.6
...
```

- [ ] **Step 8: Run all score tests**

Run: `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_score.py -v`
Expected: PASS (new + existing; existing tests pass `market_context` for price specifics so are unaffected).

- [ ] **Step 9: Run full engine suite (no regressions)**

Run: `uv run --no-sync pytest re_invest_os/packages/financial-engine/ -q`
Expected: all pass.

- [ ] **Step 10: Update calc spec doc**

In `docs/architecture/calculation_engine_spec.md` §5.6, add a paragraph: missing market data ⇒ 中立配点 (max×0.5), `covered=False`, `market_coverage` reported. Note `score_spec_version 0.2.0`.

- [ ] **Step 11: Commit**

```bash
git add re_invest_os/packages/financial-engine/src/re_engine/score.py \
        re_invest_os/packages/financial-engine/tests/test_score.py \
        re_invest_os/docs/architecture/calculation_engine_spec.md
git commit -m "feat(re_engine): coverage-aware market score (no full marks without market data)"
```

---

## Task 2: `MarketSnapshot` model + adapters (pure, mockable)

**Files:**
- Create: `apps/api/src/api/services/market/__init__.py`
- Create: `apps/api/src/api/services/market/snapshot.py`
- Test: `apps/api/tests/test_market_snapshot.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_market_snapshot.py`:

```python
from datetime import datetime, timezone

from api.services.market.snapshot import (
    MarketSnapshot,
    MetricValue,
    to_market_benchmark,
    to_market_context,
)


def _mv(value: float, **kw) -> MetricValue:
    base = dict(
        value=value,
        unit="ratio",
        method="web_research",
        source="test",
        sample_count=10,
        confidence="C",
        fetched_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
    )
    base.update(kw)
    return MetricValue(**base)


def _snapshot() -> MarketSnapshot:
    return MarketSnapshot(
        area_key="13-shinjuku",
        geo={"lat": 35.69, "lng": 139.70},
        land_price_per_sqm=_mv(900000.0, unit="yen_per_sqm", method="official_api", confidence="A"),
        market_cap_rate=_mv(0.045, p50=0.045),
        rent_per_sqm_monthly=_mv(3000.0, p25=2700, p50=3000, p75=3300, unit="yen_per_sqm"),
        vacancy_rate=_mv(0.08, p50=0.08),
        provider_versions={"official": "1.0", "rent_research": "1.0"},
        built_at=datetime(2026, 5, 30, tzinfo=timezone.utc),
        ttl_days=30,
    )


def test_to_market_context_maps_market_values() -> None:
    ctx = to_market_context(_snapshot(), property_rent_per_sqm_yen=3300)
    assert ctx.market_cap_rate == 0.045
    assert ctx.market_rent_per_sqm_yen == 3000
    assert ctx.property_rent_per_sqm_yen == 3300


def test_to_market_context_none_metrics_yield_none() -> None:
    s = _snapshot()
    s = s.model_copy(update={"market_cap_rate": None, "rent_per_sqm_monthly": None})
    ctx = to_market_context(s, property_rent_per_sqm_yen=3300)
    assert ctx.market_cap_rate is None
    assert ctx.market_rent_per_sqm_yen is None


def test_to_market_benchmark_maps_percentiles() -> None:
    b = to_market_benchmark(_snapshot())
    assert b.rent_per_sqm_monthly_p25 == 2700
    assert b.rent_per_sqm_monthly_p50 == 3000
    assert b.rent_per_sqm_monthly_p75 == 3300
    assert b.area_vacancy_rate_p50 == 0.08
    assert b.market_cap_rate_p50 == 0.045


def test_sanity_bounds_reject_out_of_range_rent() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        _mv(999999.0, unit="yen_per_sqm")  # rent far above bound when unit=yen_per_sqm rent
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_snapshot.py -v`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement `snapshot.py`**

Create `apps/api/src/api/services/market/snapshot.py`:

```python
"""MarketSnapshot: 市場データの出所・信頼度付きスナップショット。

re_engine は純粋なので、ここで score.MarketContext / risk_engine.MarketBenchmark に変換する。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator
from re_engine.score import MarketContext

from api.services.risk_engine import MarketBenchmark

Confidence = Literal["A", "B", "C", "D"]
Method = Literal["official_api", "web_research", "stat", "proxy"]

# sanity bounds: (min, max) per unit-ish metric. unit はメトリック種別の代理。
_BOUNDS: dict[str, tuple[float, float]] = {
    "rent_yen_per_sqm": (500.0, 20000.0),
    "cap_ratio": (0.01, 0.15),
    "vacancy_ratio": (0.0, 0.40),
    "land_yen_per_sqm": (1000.0, 50_000_000.0),
}


class MetricValue(BaseModel):
    value: float | None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    unit: str  # "yen_per_sqm" | "ratio"
    method: Method
    source: str
    source_url: str | None = None
    sample_count: int = 0
    confidence: Confidence
    fetched_at: datetime
    model_config = ConfigDict(extra="forbid")


class MarketSnapshot(BaseModel):
    area_key: str
    geo: dict | None = None
    land_price_per_sqm: MetricValue | None = None
    market_cap_rate: MetricValue | None = None
    rent_per_sqm_monthly: MetricValue | None = None
    vacancy_rate: MetricValue | None = None
    provider_versions: dict[str, str]
    built_at: datetime
    ttl_days: int
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _sanity(self) -> "MarketSnapshot":
        def chk(mv: MetricValue | None, key: str) -> None:
            if mv is None or mv.value is None:
                return
            lo, hi = _BOUNDS[key]
            if not (lo <= mv.value <= hi):
                raise ValueError(f"{key} out of bounds: {mv.value}")

        chk(self.rent_per_sqm_monthly, "rent_yen_per_sqm")
        chk(self.market_cap_rate, "cap_ratio")
        chk(self.vacancy_rate, "vacancy_ratio")
        chk(self.land_price_per_sqm, "land_yen_per_sqm")
        return self


def _v(mv: MetricValue | None) -> float | None:
    if mv is None:
        return None
    return mv.p50 if mv.p50 is not None else mv.value


def to_market_context(s: MarketSnapshot, property_rent_per_sqm_yen: int | None) -> MarketContext:
    rent = _v(s.rent_per_sqm_monthly)
    return MarketContext(
        market_cap_rate=_v(s.market_cap_rate),
        market_rent_per_sqm_yen=int(rent) if rent is not None else None,
        property_rent_per_sqm_yen=property_rent_per_sqm_yen,
        appraisal_price_yen=None,
    )


def to_market_benchmark(s: MarketSnapshot) -> MarketBenchmark:
    r = s.rent_per_sqm_monthly
    return MarketBenchmark(
        rent_per_sqm_monthly_p25=(r.p25 if r else None),
        rent_per_sqm_monthly_p50=(r.p50 if r else None),
        rent_per_sqm_monthly_p75=(r.p75 if r else None),
        area_vacancy_rate_p50=_v(s.vacancy_rate),
        market_cap_rate_p50=_v(s.market_cap_rate),
    )
```

Note: the last test uses `unit="yen_per_sqm"` on a bare `MetricValue` (no snapshot), so it does NOT trip snapshot-level bounds. Adjust that test to construct a `MarketSnapshot` with an out-of-range rent instead — see Step 4.

- [ ] **Step 4: Correct the bounds test to snapshot level**

Replace `test_sanity_bounds_reject_out_of_range_rent` body:

```python
def test_sanity_bounds_reject_out_of_range_rent() -> None:
    import pytest
    from pydantic import ValidationError

    s = _snapshot()
    bad = _mv(999999.0, unit="yen_per_sqm")
    with pytest.raises(ValidationError):
        s.model_copy(update={"rent_per_sqm_monthly": bad}).model_validate(
            s.model_copy(update={"rent_per_sqm_monthly": bad}).model_dump()
        )
```

(`model_copy` skips validation; re-validating via `model_validate(model_dump())` triggers the `model_validator`.)

- [ ] **Step 5: Create package `__init__.py`**

Create `apps/api/src/api/services/market/__init__.py`:

```python
from api.services.market.snapshot import (
    MarketSnapshot,
    MetricValue,
    to_market_benchmark,
    to_market_context,
)

__all__ = [
    "MarketSnapshot",
    "MetricValue",
    "to_market_benchmark",
    "to_market_context",
]
```

- [ ] **Step 6: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_snapshot.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/market/ \
        re_invest_os/apps/api/tests/test_market_snapshot.py
git commit -m "feat(api): MarketSnapshot model + engine adapters with sanity bounds"
```

---

## Task 3: Provider protocol + `MarketDataService` merge (mockable)

**Files:**
- Create: `apps/api/src/api/services/market/providers/__init__.py`
- Create: `apps/api/src/api/services/market/providers/base.py`
- Create: `apps/api/src/api/services/market/service.py`
- Test: `apps/api/tests/test_market_service.py`

- [ ] **Step 1: Write failing test (merge from fake providers)**

Create `apps/api/tests/test_market_service.py`:

```python
from datetime import datetime, timezone

from api.services.market.providers.base import MarketDataProvider, ProviderResult
from api.services.market.service import MarketDataService
from api.services.market.snapshot import MetricValue


def _mv(value, unit, method, conf, **kw) -> MetricValue:
    return MetricValue(
        value=value, unit=unit, method=method, source="fake",
        confidence=conf, sample_count=5,
        fetched_at=datetime(2026, 5, 30, tzinfo=timezone.utc), **kw,
    )


class FakeOfficial(MarketDataProvider):
    name = "official"
    version = "1.0"

    def gather(self, area_key, geo):
        return ProviderResult(
            land_price_per_sqm=_mv(900000.0, "yen_per_sqm", "official_api", "A"),
            ttl_days=365,
        )


class FakeRent(MarketDataProvider):
    name = "rent_research"
    version = "1.0"

    def gather(self, area_key, geo):
        return ProviderResult(
            rent_per_sqm_monthly=_mv(3000.0, "yen_per_sqm", "web_research", "C",
                                     p25=2700, p50=3000, p75=3300),
            vacancy_rate=_mv(0.08, "ratio", "web_research", "C", p50=0.08),
            market_cap_rate=_mv(0.045, "ratio", "web_research", "C", p50=0.045),
            ttl_days=30,
        )


def test_service_merges_providers_into_snapshot() -> None:
    svc = MarketDataService(providers=[FakeOfficial(), FakeRent()], cache=None)
    snap = svc.build_snapshot("13-shinjuku", {"lat": 35.69, "lng": 139.70})
    assert snap.land_price_per_sqm.confidence == "A"
    assert snap.rent_per_sqm_monthly.p50 == 3000
    assert snap.market_cap_rate.value == 0.045
    assert snap.provider_versions == {"official": "1.0", "rent_research": "1.0"}
    assert snap.ttl_days == 30  # min of provider TTLs


def test_service_tolerates_provider_returning_nothing() -> None:
    class Empty(MarketDataProvider):
        name = "empty"
        version = "0.0"

        def gather(self, area_key, geo):
            return ProviderResult()

    svc = MarketDataService(providers=[Empty()], cache=None)
    snap = svc.build_snapshot("13-shinjuku", None)
    assert snap.rent_per_sqm_monthly is None
    assert snap.land_price_per_sqm is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_service.py -v`
Expected: FAIL — modules missing.

- [ ] **Step 3: Implement `providers/base.py`**

```python
"""MarketDataProvider プロトコルと ProviderResult。"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict

from api.services.market.snapshot import MetricValue


class ProviderResult(BaseModel):
    land_price_per_sqm: MetricValue | None = None
    market_cap_rate: MetricValue | None = None
    rent_per_sqm_monthly: MetricValue | None = None
    vacancy_rate: MetricValue | None = None
    ttl_days: int = 365
    model_config = ConfigDict(extra="forbid")


class MarketDataProvider(Protocol):
    name: str
    version: str

    def gather(self, area_key: str, geo: dict | None) -> ProviderResult: ...
```

- [ ] **Step 4: Implement `service.py` (merge only; cache added in Task 4)**

```python
"""MarketDataService: プロバイダを束ね、MarketSnapshot を構築する。"""

from __future__ import annotations

from datetime import datetime, timezone

from api.services.market.providers.base import MarketDataProvider, ProviderResult
from api.services.market.snapshot import MarketSnapshot, MetricValue


class MarketDataService:
    def __init__(self, providers: list[MarketDataProvider], cache=None) -> None:
        self._providers = providers
        self._cache = cache

    def build_snapshot(self, area_key: str, geo: dict | None) -> MarketSnapshot:
        results: list[tuple[MarketDataProvider, ProviderResult]] = []
        for p in self._providers:
            try:
                results.append((p, p.gather(area_key, geo)))
            except Exception:  # noqa: BLE001 — provider 失敗は degrade
                results.append((p, ProviderResult()))

        def pick(attr: str) -> MetricValue | None:
            # 最初に値を返したプロバイダを採用 (registry 順 = 信頼度順に並べる)
            for _p, r in results:
                v = getattr(r, attr)
                if v is not None:
                    return v
            return None

        ttls = [r.ttl_days for _p, r in results] or [365]
        return MarketSnapshot(
            area_key=area_key,
            geo=geo,
            land_price_per_sqm=pick("land_price_per_sqm"),
            market_cap_rate=pick("market_cap_rate"),
            rent_per_sqm_monthly=pick("rent_per_sqm_monthly"),
            vacancy_rate=pick("vacancy_rate"),
            provider_versions={p.name: p.version for p, _r in results},
            built_at=datetime.now(timezone.utc),
            ttl_days=min(ttls),
        )
```

- [ ] **Step 5: Create `providers/__init__.py`**

```python
from api.services.market.providers.base import MarketDataProvider, ProviderResult

__all__ = ["MarketDataProvider", "ProviderResult"]
```

- [ ] **Step 6: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_service.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/market/providers/ \
        re_invest_os/apps/api/src/api/services/market/service.py \
        re_invest_os/apps/api/tests/test_market_service.py
git commit -m "feat(api): MarketDataService provider registry + snapshot merge"
```

---

## Task 4: Area cache + whole-snapshot TTL + DB

**Files:**
- Create: `apps/api/src/api/services/market/cache.py`
- Create: `infra/migrations/v3_market_snapshots.sql`
- Modify: `apps/api/src/api/db.py` (apply v3; follow how v2 is applied)
- Modify: `apps/api/src/api/services/market/service.py` (use cache in `get_snapshot`)
- Test: `apps/api/tests/test_market_service.py` (add cache cases)

- [ ] **Step 1: Write migration**

Create `infra/migrations/v3_market_snapshots.sql`:

```sql
-- v3: market grounding (area-keyed cache + freeze column)
-- 既存テーブルは破壊しない。追加のみ。
-- 対応 DB: PostgreSQL 15+ / SQLite 3.35+

CREATE TABLE IF NOT EXISTS market_snapshots (
    area_key   TEXT     PRIMARY KEY,
    snapshot_json TEXT  NOT NULL,
    built_at   DATETIME NOT NULL,
    ttl_days   INTEGER  NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_built ON market_snapshots (built_at DESC);

-- analysis_runs にスナップショット凍結カラムを追加 (nullable, 既存行は NULL のまま)
ALTER TABLE analysis_runs ADD COLUMN market_snapshot_json TEXT NULL;
```

- [ ] **Step 2: Wire migration application**

Open `apps/api/src/api/db.py`, find where `v2_deal_workspace.sql` is read/executed at init, and add `v3_market_snapshots.sql` to the same ordered list/loop. Use `ALTER TABLE ... ADD COLUMN` idempotency: wrap the ALTER so a duplicate-column error is ignored (SQLite raises `OperationalError: duplicate column name`). Example helper to add next to the migration loop:

```python
# 既存の migration 適用箇所に追記。ALTER は重複時に無視する。
try:
    await conn.exec_driver_sql(
        "ALTER TABLE analysis_runs ADD COLUMN market_snapshot_json TEXT NULL"
    )
except Exception:  # noqa: BLE001 — duplicate column on re-init
    pass
```

If `db.py` executes whole `.sql` files via `executescript`, instead split the ALTER out of `v3_*.sql` into this guarded call and keep only `CREATE TABLE ...` in the SQL file. Verify by reading `db.py` first.

- [ ] **Step 3: Write failing cache tests**

Add to `apps/api/tests/test_market_service.py`:

```python
import pytest

from api.services.market.cache import MarketSnapshotCache


@pytest.mark.asyncio
async def test_cache_round_trip(tmp_path) -> None:
    cache = MarketSnapshotCache(db_path=str(tmp_path / "c.db"))
    await cache.init()
    svc = MarketDataService(providers=[FakeOfficial(), FakeRent()], cache=cache)
    snap1 = await svc.get_snapshot("13-shinjuku", {"lat": 35.69, "lng": 139.70})
    cached = await cache.get("13-shinjuku")
    assert cached is not None
    assert cached.rent_per_sqm_monthly.p50 == snap1.rent_per_sqm_monthly.p50


@pytest.mark.asyncio
async def test_cache_hit_skips_providers(tmp_path) -> None:
    calls = {"n": 0}

    class Counting(FakeRent):
        def gather(self, area_key, geo):
            calls["n"] += 1
            return super().gather(area_key, geo)

    cache = MarketSnapshotCache(db_path=str(tmp_path / "c.db"))
    await cache.init()
    svc = MarketDataService(providers=[Counting()], cache=cache)
    await svc.get_snapshot("13-shinjuku", None)
    await svc.get_snapshot("13-shinjuku", None)  # 2nd should hit cache
    assert calls["n"] == 1
```

- [ ] **Step 4: Implement `cache.py`**

```python
"""MarketSnapshotCache: area_key キーの永続キャッシュ (SQLAlchemy core)。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from api.services.market.snapshot import MarketSnapshot


class MarketSnapshotCache:
    def __init__(self, db_path: str) -> None:
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    async def init(self) -> None:
        async with self._engine.begin() as conn:
            await conn.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS market_snapshots ("
                "area_key TEXT PRIMARY KEY, snapshot_json TEXT NOT NULL, "
                "built_at DATETIME NOT NULL, ttl_days INTEGER NOT NULL)"
            )

    async def get(self, area_key: str) -> MarketSnapshot | None:
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    text("SELECT snapshot_json, built_at, ttl_days "
                         "FROM market_snapshots WHERE area_key = :k"),
                    {"k": area_key},
                )
            ).first()
        if row is None:
            return None
        snap = MarketSnapshot.model_validate_json(row[0])
        if self._is_stale(snap):
            return None
        return snap

    async def put(self, snap: MarketSnapshot) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO market_snapshots (area_key, snapshot_json, built_at, ttl_days) "
                     "VALUES (:k, :j, :b, :t) "
                     "ON CONFLICT(area_key) DO UPDATE SET "
                     "snapshot_json=excluded.snapshot_json, built_at=excluded.built_at, "
                     "ttl_days=excluded.ttl_days"),
                {"k": snap.area_key, "j": snap.model_dump_json(),
                 "b": snap.built_at.isoformat(), "t": snap.ttl_days},
            )

    @staticmethod
    def _is_stale(snap: MarketSnapshot) -> bool:
        age_days = (datetime.now(timezone.utc) - snap.built_at).total_seconds() / 86400
        return age_days > snap.ttl_days
```

- [ ] **Step 5: Add `get_snapshot` to `service.py`**

Append to `MarketDataService`:

```python
    async def get_snapshot(self, area_key: str, geo: dict | None) -> MarketSnapshot:
        if self._cache is not None:
            cached = await self._cache.get(area_key)
            if cached is not None:
                return cached
        snap = self.build_snapshot(area_key, geo)
        if self._cache is not None:
            await self._cache.put(snap)
        return snap
```

Add `from __future__ import annotations` is already present; no new imports needed.

- [ ] **Step 6: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_service.py -v`
Expected: PASS (sync merge + async cache). Ensure `pytest-asyncio` is configured (check `pyproject.toml` `[tool.pytest.ini_options] asyncio_mode = "auto"`; existing async API tests confirm it is — if `@pytest.mark.asyncio` is required, keep the markers as written).

- [ ] **Step 7: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/market/cache.py \
        re_invest_os/apps/api/src/api/services/market/service.py \
        re_invest_os/infra/migrations/v3_market_snapshots.sql \
        re_invest_os/apps/api/src/api/db.py \
        re_invest_os/apps/api/tests/test_market_service.py
git commit -m "feat(api): area-keyed market snapshot cache + analysis_runs freeze column"
```

---

## Task 5: `OfficialLandPriceProvider` (fixture-tested)

**Files:**
- Create: `apps/api/src/api/services/market/providers/official.py`
- Create: `apps/api/tests/fixtures/market/xpt002_shinjuku.json`
- Test: `apps/api/tests/test_market_provider_official.py`

- [ ] **Step 1: Create fixture**

Create `apps/api/tests/fixtures/market/xpt002_shinjuku.json` (minimal shape mirroring 不動産情報ライブラリ XPT002 geojson):

```json
{
  "features": [
    {"properties": {"u_current_years_price_ja": "900,000(円/㎡)", "ward_town_village_name_ja": "新宿区"}},
    {"properties": {"u_current_years_price_ja": "1,100,000(円/㎡)", "ward_town_village_name_ja": "新宿区"}},
    {"properties": {"u_current_years_price_ja": "700,000(円/㎡)", "ward_town_village_name_ja": "新宿区"}}
  ]
}
```

- [ ] **Step 2: Write failing test**

Create `apps/api/tests/test_market_provider_official.py`:

```python
import json
from pathlib import Path

from api.services.market.providers.official import (
    OfficialLandPriceProvider,
    parse_land_price_per_sqm,
)

FIX = Path(__file__).parent / "fixtures" / "market" / "xpt002_shinjuku.json"


def test_parse_price_string() -> None:
    assert parse_land_price_per_sqm("900,000(円/㎡)") == 900000.0
    assert parse_land_price_per_sqm("不明") is None


def test_provider_builds_metric_from_fixture() -> None:
    data = json.loads(FIX.read_text(encoding="utf-8"))

    class FakeClient:
        def fetch_public_notice(self, area_key, geo):
            return data

    p = OfficialLandPriceProvider(client=FakeClient())
    res = p.gather("13-shinjuku", {"lat": 35.69, "lng": 139.70})
    assert res.land_price_per_sqm is not None
    assert res.land_price_per_sqm.p50 == 900000.0   # median of 700k/900k/1.1M
    assert res.land_price_per_sqm.confidence == "A"
    assert res.land_price_per_sqm.method == "official_api"
    assert res.ttl_days == 365


def test_provider_degrades_when_client_returns_empty() -> None:
    class EmptyClient:
        def fetch_public_notice(self, area_key, geo):
            return {"features": []}

    p = OfficialLandPriceProvider(client=EmptyClient())
    res = p.gather("13-shinjuku", None)
    assert res.land_price_per_sqm is None
```

- [ ] **Step 3: Implement `official.py`**

```python
"""OfficialLandPriceProvider: 国交省 不動産情報ライブラリ XPT002 (公示地価)。

client は HTTP を抽象化 (テストで fixture を注入)。本番 client は httpx で
XPT002 を呼ぶ (要 API キー)。PoC 知見: response_format/z/x/y/year/priceClassification
はクエリで渡す。価格は u_current_years_price_ja ("900,000(円/㎡)") をパース。
"""

from __future__ import annotations

import re
import statistics
from datetime import datetime, timezone
from typing import Protocol

from api.services.market.providers.base import ProviderResult
from api.services.market.snapshot import MetricValue

_PRICE_RE = re.compile(r"([\d,]+)")


def parse_land_price_per_sqm(s: str | None) -> float | None:
    if not s:
        return None
    m = _PRICE_RE.search(s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


class OfficialClient(Protocol):
    def fetch_public_notice(self, area_key: str, geo: dict | None) -> dict: ...


class OfficialLandPriceProvider:
    name = "official"
    version = "1.0"

    def __init__(self, client: OfficialClient) -> None:
        self._client = client

    def gather(self, area_key: str, geo: dict | None) -> ProviderResult:
        try:
            data = self._client.fetch_public_notice(area_key, geo)
        except Exception:  # noqa: BLE001
            return ProviderResult()
        prices: list[float] = []
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            v = parse_land_price_per_sqm(props.get("u_current_years_price_ja"))
            if v is not None:
                prices.append(v)
        if not prices:
            return ProviderResult()
        prices.sort()
        mv = MetricValue(
            value=statistics.median(prices),
            p25=_percentile(prices, 0.25),
            p50=statistics.median(prices),
            p75=_percentile(prices, 0.75),
            unit="yen_per_sqm",
            method="official_api",
            source="国交省 不動産情報ライブラリ XPT002 (公示地価)",
            sample_count=len(prices),
            confidence="A",
            fetched_at=datetime.now(timezone.utc),
        )
        return ProviderResult(land_price_per_sqm=mv, ttl_days=365)


def _percentile(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return sorted_vals[idx]
```

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_provider_official.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/market/providers/official.py \
        re_invest_os/apps/api/tests/test_market_provider_official.py \
        re_invest_os/apps/api/tests/fixtures/market/xpt002_shinjuku.json
git commit -m "feat(api): OfficialLandPriceProvider (XPT002 公示地価, fixture-tested)"
```

> **Production note (not a code step):** the real `OfficialClient` (httpx) and its API key go in a follow-up. Until configured, the provider is simply not registered, and the snapshot degrades (land price `None`, lower coverage). This is intentional v1 scope.

---

## Task 6: `RentResearchProvider` (fixture-tested, injectable research client)

**Files:**
- Create: `apps/api/src/api/services/market/providers/rent_research.py`
- Create: `apps/api/tests/fixtures/market/rent_shinjuku.json`
- Test: `apps/api/tests/test_market_provider_rent.py`

- [ ] **Step 1: Create fixture**

Create `apps/api/tests/fixtures/market/rent_shinjuku.json` (the *structured* output a `WebResearchClient` returns after fetch+LLM-extract):

```json
{
  "rent_per_sqm_monthly": {"p25": 2700, "p50": 3000, "p75": 3300, "sample_count": 42},
  "vacancy_rate": {"p50": 0.08, "sample_count": 12},
  "market_cap_rate": {"p50": 0.045, "sample_count": 30},
  "source_url": "https://example.test/area/shinjuku"
}
```

- [ ] **Step 2: Write failing test**

Create `apps/api/tests/test_market_provider_rent.py`:

```python
import json
from pathlib import Path

from api.services.market.providers.rent_research import RentResearchProvider

FIX = Path(__file__).parent / "fixtures" / "market" / "rent_shinjuku.json"


def test_rent_provider_builds_metrics_from_research() -> None:
    data = json.loads(FIX.read_text(encoding="utf-8"))

    class FakeResearch:
        def research_area(self, area_key, geo):
            return data

    p = RentResearchProvider(client=FakeResearch())
    res = p.gather("13-shinjuku", None)
    assert res.rent_per_sqm_monthly.p50 == 3000
    assert res.rent_per_sqm_monthly.confidence == "C"
    assert res.vacancy_rate.p50 == 0.08
    assert res.market_cap_rate.p50 == 0.045
    assert res.ttl_days == 30


def test_rent_provider_drops_out_of_range_then_degrades() -> None:
    class BadResearch:
        def research_area(self, area_key, geo):
            return {"rent_per_sqm_monthly": {"p50": 999999, "sample_count": 3},
                    "source_url": "x"}

    p = RentResearchProvider(client=BadResearch())
    res = p.gather("13-shinjuku", None)
    assert res.rent_per_sqm_monthly is None  # out of bounds -> dropped


def test_rent_provider_handles_no_client() -> None:
    p = RentResearchProvider(client=None)
    res = p.gather("13-shinjuku", None)
    assert res.rent_per_sqm_monthly is None
    assert res.market_cap_rate is None
```

- [ ] **Step 3: Implement `rent_research.py`**

```python
"""RentResearchProvider: 自律 Web リサーチで賃料・空室・cap相場を取得。

client (WebResearchClient) は httpx fetch + 既存 services.llm_client で構造化抽出する
実装に差し替え可能。テストでは fixture を返す fake を注入。
sanity bounds 外の値は捨て、confidence は web_research = C。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from api.services.market.providers.base import ProviderResult
from api.services.market.snapshot import MetricValue

_RENT_BOUNDS = (500.0, 20000.0)
_CAP_BOUNDS = (0.01, 0.15)
_VAC_BOUNDS = (0.0, 0.40)


class WebResearchClient(Protocol):
    def research_area(self, area_key: str, geo: dict | None) -> dict: ...


class RentResearchProvider:
    name = "rent_research"
    version = "1.0"

    def __init__(self, client: WebResearchClient | None) -> None:
        self._client = client

    def gather(self, area_key: str, geo: dict | None) -> ProviderResult:
        if self._client is None:
            return ProviderResult(ttl_days=30)
        try:
            data = self._client.research_area(area_key, geo)
        except Exception:  # noqa: BLE001
            return ProviderResult(ttl_days=30)
        src = data.get("source_url")
        now = datetime.now(timezone.utc)

        def metric(key: str, unit: str, bounds: tuple[float, float]) -> MetricValue | None:
            d = data.get(key)
            if not d:
                return None
            p50 = d.get("p50")
            if p50 is None or not (bounds[0] <= p50 <= bounds[1]):
                return None
            return MetricValue(
                value=p50, p25=d.get("p25"), p50=p50, p75=d.get("p75"),
                unit=unit, method="web_research",
                source="web research (area aggregate)", source_url=src,
                sample_count=int(d.get("sample_count", 0)), confidence="C",
                fetched_at=now,
            )

        return ProviderResult(
            rent_per_sqm_monthly=metric("rent_per_sqm_monthly", "yen_per_sqm", _RENT_BOUNDS),
            vacancy_rate=metric("vacancy_rate", "ratio", _VAC_BOUNDS),
            market_cap_rate=metric("market_cap_rate", "ratio", _CAP_BOUNDS),
            ttl_days=30,
        )
```

- [ ] **Step 4: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_market_provider_rent.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/market/providers/rent_research.py \
        re_invest_os/apps/api/tests/test_market_provider_rent.py \
        re_invest_os/apps/api/tests/fixtures/market/rent_shinjuku.json
git commit -m "feat(api): RentResearchProvider (injectable research client, sanity bounds)"
```

> **Production note:** the concrete `WebResearchClient` (search API key OR fixed source pages + `services/llm_client` extraction) is a deployment decision flagged in the spec §9/§11. Provider degrades gracefully when `client=None`.

---

## Task 7: Wire snapshot into analysis flow + freeze + delete stub

**Files:**
- Modify: `apps/api/src/api/routers/deals.py` (`create_analysis_run`)
- Delete: `apps/api/src/api/services/market_context.py`
- Test: `apps/api/tests/test_deals_api.py` (add a wiring assertion)

- [ ] **Step 1: Write failing API test**

Add to `apps/api/tests/test_deals_api.py` (follow the file's existing async client fixture/pattern):

```python
@pytest.mark.asyncio
async def test_analysis_run_includes_market_score_fields(client) -> None:
    # 既存テストの deal 作成ヘルパ・assumptions fixture を流用すること
    deal = (await client.post("/deals", json={"title": "t", "source_type": "manual"})).json()
    payload = {"assumptions": MINIMAL_ASSUMPTIONS}  # 既存テストの定数を再利用
    r = await client.post(f"/deals/{deal['id']}/analysis_runs", json=payload)
    assert r.status_code == 201
    body = r.json()
    # market_coverage がレスポンスの score に含まれる
    assert "market_coverage" in body["metrics"]["score"]
```

If `test_deals_api.py` does not expose `metrics` in `AnalysisRunOut`, assert on the persisted row via a follow-up GET instead — inspect the file's existing response shape first and match it.

- [ ] **Step 2: Run to verify failure**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_deals_api.py -k market -v`
Expected: FAIL — `market_coverage` absent (score currently computed without it being surfaced) OR shape mismatch to fix.

- [ ] **Step 3: Build a default MarketDataService factory**

Add to `apps/api/src/api/services/market/service.py`:

```python
def default_market_service(cache=None) -> "MarketDataService":
    """本番/dev のデフォルト構成。client 未設定のプロバイダは degrade する。

    レジストリ順 = 信頼度順 (official が land price を、rent_research が rent/cap/vacancy を埋める)。
    """
    from api.services.market.providers.rent_research import RentResearchProvider

    # OfficialLandPriceProvider は client 必須。未設定の dev では rent_research のみ。
    providers = [RentResearchProvider(client=None)]
    return MarketDataService(providers=providers, cache=cache)
```

- [ ] **Step 4: Wire into `create_analysis_run`**

In `deals.py`, replace the `score = total_score(analysis)` region with snapshot-aware computation. Add imports at top:

```python
from re_engine.score import total_score  # 既存
from api.services.market.service import default_market_service
from api.services.market.snapshot import to_market_context
```

Then:

```python
    analysis = run_full_analysis(assumptions)

    # area_key: assumptions に明示が無い dev では prefecture 単位 fallback
    area_key = _area_key_for(assumptions)
    svc = default_market_service(cache=None)  # cache 接続は後続タスクで
    snapshot = await svc.get_snapshot(area_key, None)

    prop_rent_per_sqm = None
    if assumptions.property.building_area_sqm > 0:
        prop_rent_per_sqm = round(
            assumptions.income.gpi_monthly_yen / assumptions.property.building_area_sqm
        )
    ctx = to_market_context(snapshot, prop_rent_per_sqm)
    score = total_score(analysis, market_context=ctx)

    metrics = {
        "analysis": analysis.model_dump(mode="json", by_alias=True),
        "score": score.model_dump(mode="json"),
        "market_snapshot": snapshot.model_dump(mode="json"),
    }
```

And add a small helper in `deals.py`:

```python
def _area_key_for(a: Assumptions) -> str:
    # v1: prefecture コードが取れなければ汎用キー。住所粒度の改善は後続。
    pref = getattr(a.property, "pref_code", None)
    return f"{pref}-area" if pref else "unknown-area"
```

(If `Assumptions.property` has no `pref_code`, keep `"unknown-area"`; area resolution improvement is deferred per spec §5.)

- [ ] **Step 5: Persist freeze column**

In the same function, when building `AnalysisRunRecord`, add:

```python
        market_snapshot_json=json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False),
```

Ensure `AnalysisRunRecord` model maps `market_snapshot_json` (add the column attribute to the SQLAlchemy model if it is declared in code, mirroring `sensitivity_json`).

- [ ] **Step 6: Delete the stub**

```bash
git rm re_invest_os/apps/api/src/api/services/market_context.py
```

Then grep to confirm no imports remain:

Run: `grep -rn "services.market_context\|from api.services.market_context" re_invest_os/apps`
Expected: no results.

- [ ] **Step 7: Run tests**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_deals_api.py -v`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add -A re_invest_os/apps/api
git commit -m "feat(api): wire market snapshot into analysis_runs (score+freeze), drop stub"
```

---

## Task 8: Market Context UI panel

**Files:**
- Create: `apps/web/src/app/api/market/route.ts`
- Create: `apps/web/src/components/market-context-panel.tsx`
- Modify: `apps/web/src/app/report/page.tsx`

- [ ] **Step 1: Add Next.js proxy route**

Create `apps/web/src/app/api/market/route.ts`, mirroring an existing proxy (`apps/web/src/app/api/sensitivity/route.ts`):

```typescript
import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  const body = await req.text();
  const res = await fetch(`${API_BASE}/deals/market_snapshot`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
```

(If the report already carries `metrics.market_snapshot` from the analysis_run response, the panel can read it directly without this route. Prefer reading from the existing analysis payload; add the route only if a standalone refresh action is needed. Inspect `report/page.tsx` data flow first and choose the simpler path.)

- [ ] **Step 2: Build the panel component**

Create `apps/web/src/components/market-context-panel.tsx` (Bloomberg-basic style, match existing `report-panels.tsx` styling tokens):

```tsx
"use client";

type Metric = {
  value: number | null;
  p25?: number | null;
  p50?: number | null;
  p75?: number | null;
  unit: string;
  source: string;
  source_url?: string | null;
  confidence: "A" | "B" | "C" | "D";
  fetched_at: string;
};

type Snapshot = {
  area_key: string;
  land_price_per_sqm: Metric | null;
  market_cap_rate: Metric | null;
  rent_per_sqm_monthly: Metric | null;
  vacancy_rate: Metric | null;
};

export function MarketContextPanel({
  snapshot,
  marketCoverage,
}: {
  snapshot: Snapshot | null;
  marketCoverage: number;
}) {
  if (!snapshot) return null;
  const provisional = marketCoverage < 0.5;
  const rows: Array<[string, Metric | null]> = [
    ["賃料 (円/㎡・月)", snapshot.rent_per_sqm_monthly],
    ["市場Cap", snapshot.market_cap_rate],
    ["空室率", snapshot.vacancy_rate],
    ["地価 (円/㎡)", snapshot.land_price_per_sqm],
  ];
  return (
    <section className="market-context-panel">
      <header>
        <h3>Market Context</h3>
        {provisional && <span className="badge badge-warn">市場データ不足のため暫定</span>}
        <span className="muted">coverage {(marketCoverage * 100).toFixed(0)}%</span>
      </header>
      <table>
        <thead>
          <tr><th>指標</th><th>p25</th><th>p50</th><th>p75</th><th>出所</th></tr>
        </thead>
        <tbody>
          {rows.map(([label, m]) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{m?.p25 ?? "—"}</td>
              <td>{m?.p50 ?? m?.value ?? "—"}</td>
              <td>{m?.p75 ?? "—"}</td>
              <td>
                {m ? (
                  <span title={m.fetched_at}>
                    {m.source} <span className={`conf conf-${m.confidence}`}>{m.confidence}</span>
                  </span>
                ) : "未取得"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
```

- [ ] **Step 3: Mount in report page**

In `apps/web/src/app/report/page.tsx`, import and render the panel where the existing panels render, feeding `snapshot={metrics.market_snapshot}` and `marketCoverage={metrics.score.market_coverage}` from the analysis payload.

```tsx
import { MarketContextPanel } from "@/components/market-context-panel";
// ...inside the panels region:
<MarketContextPanel
  snapshot={metrics?.market_snapshot ?? null}
  marketCoverage={metrics?.score?.market_coverage ?? 1}
/>
```

- [ ] **Step 4: Typecheck**

Run: `cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/web/src/components/market-context-panel.tsx \
        re_invest_os/apps/web/src/app/report/page.tsx \
        re_invest_os/apps/web/src/app/api/market/route.ts
git commit -m "feat(web): Market Context panel (provenance + coverage badge)"
```

---

## Task 9: Integration verification (observe real output)

**Files:** none (verification only)

- [ ] **Step 1: Full backend regression**

Run: `uv run --no-sync pytest re_invest_os/ -q`
Expected: all pass. Record the count (e.g., "N passed").

- [ ] **Step 2: Frontend typecheck**

Run: `cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Start API + Web, run sample property end-to-end**

Start API: `uv run --no-sync uvicorn api.main:app --reload --port 8000 --app-dir re_invest_os/apps/api/src`
Start web: `cd re_invest_os/apps/web && node_modules/.bin/next dev --port 3001`
Create a deal + analysis_run for サンプル物件「西新宿レジデンス 504号」 (price 39.8M, RC, 38.4㎡, 145,000円/月).

- [ ] **Step 4: Observe known input → output**

Confirm via the API response (quote actual JSON in the report):
- `metrics.score.market_coverage` is present and `< 1.0` when only rent_research (no client) is registered (i.e., 0.0 in dev), proving the coverage path is live.
- `metrics.score.components` has `price.covered == false` and `rent.covered == false` in dev (no market client), and `price.score == 10.0`, `rent.score == 7.5` (50% of 20 / 15).
- `metrics.market_snapshot` is present and persisted (`market_snapshot_json` non-null on the row).

- [ ] **Step 5: Observe UI (webapp-testing)**

Use the `webapp-testing` skill to load `/report` for the analysis and screenshot the Market Context panel; confirm the "暫定" badge + coverage % render. Save the screenshot.

- [ ] **Step 6: Honest completion report**

Write the Definition-of-Done report: quote the pytest summary line, the observed JSON fields, and attach the screenshot. Mark explicitly what is NOT verified (live OfficialClient/WebResearchClient not wired — providers degrade by design).

- [ ] **Step 7: Commit any doc updates**

```bash
git add -A re_invest_os/docs
git commit -m "docs(re_invest_os): market grounding v1 verification notes"
```

---

## Self-Review

- **Spec coverage:**
  - §2 goal 1 (real data drives score/risk) → Tasks 5,6,7.
  - §2 goal 2 (hybrid path) → Official (T5) + Rent research (T6).
  - §2 goal 3 (provenance/confidence/freeze) → MetricValue (T2), freeze column (T4,T7).
  - §2 goal 4 (no full marks) → T1.
  - §2 goal 5 (Market Context panel) → T8.
  - §6 (coverage fix + score_spec_version) → T1.
  - §8 (cache + freeze, nullable column, no row rewrite) → T4.
  - §9 (sanity bounds, confidence, LLM boundary) → T2,T6.
  - §10 (tests, integration) → every task + T9.
  - §11 prerequisites (API key, degrade) → T5/T6 production notes.
  - Non-goals (bid_range coupling, comps UI, batch, worker) → excluded. ✅
- **Placeholder scan:** all code steps contain real code; commands have expected output; no TBD/TODO. Two "inspect first" notes (db.py migration application, deals test response shape, report data flow) are guarded with concrete fallbacks, not placeholders.
- **Type consistency:** `MetricValue`/`MarketSnapshot` fields identical across T2–T7. `ProviderResult` attrs (`land_price_per_sqm`, `market_cap_rate`, `rent_per_sqm_monthly`, `vacancy_rate`, `ttl_days`) consistent in base/official/rent/service. `MarketDataService(providers=, cache=)` + `build_snapshot`/`get_snapshot` consistent. `ScoreComponent.covered` / `ScoreResult.market_coverage` consistent T1↔T7↔T8.
