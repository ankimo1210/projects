# re_invest_os Spec 1 — Analysis Core Redefinition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote the per-assumption "甘さスコア" (confidence + risk) to the analysis centerpiece, retire the 100-point property-quality score (健全/要警戒), add a dead-cross-year KPI, and make NG-expression checks enforced by tests — turning re_invest_os into a neutral DD engine.

**Architecture:** The pure engine (`re_engine`) gains `KPI.dead_cross_year`. The existing pure-logic `risk_engine.py` gains an `AssumptionScore` aggregate wrapper (`overall_risk` + `summary` + `items`), a DSCR-coupling pass, an exit-dependency rule, and two new categories. `re_engine/score.py` (property-quality score) and its tests are deleted; every consumer (API `/analyze`, deals router, summarizer LLM context, save/history, frontend panels) is switched to `assumption_score`. NG enforcement expands the wordlist, isolates disclaimers, and adds a test that scans UI/prompt/fixture surfaces.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, SQLAlchemy async + aiosqlite, pytest. Frontend: Next.js (App Router) + TypeScript.

**Spec:** `docs/design/2026-05-30-mvp-redefinition-design.md` (Spec 1 section)

**Run commands (from workspace root `~/projects`):**
- Engine tests: `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -v`
- API tests: `uv run --no-sync pytest re_invest_os/apps/api/tests/ -v`
- Full reio suite: `uv run --no-sync pytest re_invest_os/ -q`
- Typecheck: `cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`
- Lint: `uv run --no-sync ruff check re_invest_os/`

**Commit scope discipline:** This workspace is one git repo containing other projects (`stock/` etc.) with unrelated uncommitted changes. Only `git add` paths under `re_invest_os/`. Never `git add -A`.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `packages/financial-engine/src/re_engine/models.py` | `KPI.dead_cross_year` field | Modify |
| `packages/financial-engine/src/re_engine/analyze.py` | `first_dead_cross_year()` + populate KPI | Modify |
| `packages/financial-engine/src/re_engine/__init__.py` | `ENGINE_VERSION` 0.2.0 | Modify |
| `packages/financial-engine/tests/test_analyze.py` | dead-cross tests | Modify |
| `packages/financial-engine/src/re_engine/score.py` | property-quality score | **Delete** |
| `packages/financial-engine/tests/test_score.py` | score tests | **Delete** |
| `apps/api/src/api/services/risk_engine.py` | `AssumptionScore`, overall_risk, DSCR coupling, exit-share, 2 new categories | Modify |
| `apps/api/tests/test_assumption_score.py` | 甘さスコア tests | **Create** |
| `apps/api/src/api/main.py` | `/analyze` + `/sample` → `assumption_score`; drop score imports | Modify |
| `apps/api/src/api/routers/deals.py` | metrics use `assumption_score` | Modify |
| `apps/api/src/api/services/summarizer.py` | LLM context from `assumption_score` | Modify |
| `apps/api/src/api/constants.py` | `DISCLAIMERS` constant | **Create** |
| `apps/api/src/api/services/ng_filter.py` | expanded `NG_WORDS` | Modify |
| `apps/api/tests/test_ng_expressions.py` | NG surface scanner test | **Create** |
| `apps/web/src/types/api.ts` | `AssumptionScore` type; drop `ScoreResult` | Modify |
| `apps/web/src/components/report-panels.tsx` | remove score panel; promote 甘さ panel | Modify |
| `apps/web/src/components/deal/DealSummaryCard.tsx` | remove SCORE/evaluation cell | Modify |
| `apps/web/src/app/report/page.tsx` | pass `assumption_score`; drop score plumbing | Modify |

---

## Task 1: Add `dead_cross_year` KPI + bump engine version

**Files:**
- Modify: `packages/financial-engine/src/re_engine/models.py` (KPI class, ~line 133)
- Modify: `packages/financial-engine/src/re_engine/analyze.py`
- Modify: `packages/financial-engine/src/re_engine/__init__.py:7`
- Test: `packages/financial-engine/tests/test_analyze.py`

Dead cross = first hold year where straight-line depreciation drops below loan principal repayment (non-deductible cash outflow), i.e. `depreciation_yen < principal_payment_yen`. Returns `None` if it never happens in the projection.

- [ ] **Step 1: Write the failing tests**

Append to `packages/financial-engine/tests/test_analyze.py`:

```python
from re_engine import ENGINE_VERSION
from re_engine.analyze import first_dead_cross_year, run_full_analysis
from re_engine.models import YearlyCashflow


def _row(year: int, depreciation: int, principal: int) -> YearlyCashflow:
    return YearlyCashflow(
        year=year, gpi_yen=0, vacancy_loss_yen=0, bad_debt_yen=0, egi_yen=0,
        opex_yen=0, noi_yen=0, debt_service_yen=0, btcf_yen=0,
        depreciation_yen=depreciation, interest_expense_yen=0,
        principal_payment_yen=principal, taxable_income_yen=0, tax_yen=0,
        atcf_yen=0, loan_balance_end_yen=0,
    )


def test_first_dead_cross_year_detects_crossover():
    # dep > principal in y1-2, dep < principal from y3
    rows = [_row(1, 100, 50), _row(2, 100, 90), _row(3, 100, 110), _row(4, 100, 130)]
    assert first_dead_cross_year(rows) == 3


def test_first_dead_cross_year_none_when_never_crosses():
    rows = [_row(1, 100, 50), _row(2, 100, 60)]
    assert first_dead_cross_year(rows) is None


def test_analysis_populates_dead_cross_year_consistently(base_assumptions):
    result = run_full_analysis(base_assumptions)
    expected = first_dead_cross_year(result.yearly_cashflows)
    assert result.kpi.dead_cross_year == expected
    assert result.kpi.dead_cross_year is None or isinstance(result.kpi.dead_cross_year, int)


def test_engine_version_bumped():
    assert ENGINE_VERSION == "0.2.0"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_analyze.py -v`
Expected: FAIL — `ImportError: cannot import name 'first_dead_cross_year'` and `KPI` has no `dead_cross_year` / version mismatch.

- [ ] **Step 3: Implement**

In `packages/financial-engine/src/re_engine/__init__.py` change line 7:
```python
ENGINE_VERSION = "0.2.0"
```

In `packages/financial-engine/src/re_engine/models.py`, add a field to `KPI` (after `atcf_first_year_yen`):
```python
    dead_cross_year: int | None = None
```

In `packages/financial-engine/src/re_engine/analyze.py`, add the helper (top-level, after imports) and populate the KPI:
```python
from re_engine.models import KPI, AnalysisResult, Assumptions, YearlyCashflow


def first_dead_cross_year(cashflows: list[YearlyCashflow]) -> int | None:
    """初めて減価償却 < 元金返済 となる年（デッドクロス）。無ければ None。"""
    for cf in cashflows:
        if cf.depreciation_yen < cf.principal_payment_yen:
            return cf.year
    return None
```
Then in `run_full_analysis`, add `dead_cross_year=first_dead_cross_year(cfs)` to the `KPI(...)` constructor.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_analyze.py -v`
Expected: PASS (4 new tests + existing).

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/packages/financial-engine/src/re_engine/models.py \
        re_invest_os/packages/financial-engine/src/re_engine/analyze.py \
        re_invest_os/packages/financial-engine/src/re_engine/__init__.py \
        re_invest_os/packages/financial-engine/tests/test_analyze.py
git commit -m "feat(engine): add dead_cross_year KPI; bump engine_version 0.2.0"
```

---

## Task 2: `AssumptionScore` aggregate + `overall_risk`

**Files:**
- Modify: `apps/api/src/api/services/risk_engine.py`
- Test: `apps/api/tests/test_assumption_score.py` (create)

- [ ] **Step 1: Write the failing test**

Create `apps/api/tests/test_assumption_score.py`:

```python
from re_engine.analyze import run_full_analysis
from re_engine.normalized import NormalizedProperty

from api.services.risk_engine import (
    AssumptionScore,
    aggregate_overall_risk,
    assess_assumption_score,
)


def _score(assumptions):
    result = run_full_analysis(assumptions)
    return assess_assumption_score(assumptions, result, NormalizedProperty.all_user_input())


def test_aggregate_overall_risk_priority():
    assert aggregate_overall_risk(["low", "medium", "high"]) == "high"
    assert aggregate_overall_risk(["low", "medium", "low"]) == "medium"
    assert aggregate_overall_risk(["low", "low"]) == "low"
    assert aggregate_overall_risk(["unknown", "unknown"]) == "unknown"


def test_assumption_score_shape(base_assumptions):
    s = _score(base_assumptions)
    assert isinstance(s, AssumptionScore)
    assert s.overall_risk in ("low", "medium", "high", "unknown")
    assert s.items, "items must not be empty"
    assert isinstance(s.summary, str) and s.summary
```

Note: `base_assumptions` fixture must be visible to api tests. If `apps/api/tests/conftest.py` does not already provide it, add the same fixture used in `packages/financial-engine/tests/conftest.py` (copy the `base_assumptions` fixture verbatim) to `apps/api/tests/conftest.py`. Verify first with: `grep -rn "def base_assumptions" re_invest_os/apps/api/tests/`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_assumption_score.py -v`
Expected: FAIL — `ImportError: cannot import name 'AssumptionScore'`.

- [ ] **Step 3: Implement**

In `apps/api/src/api/services/risk_engine.py`, after the `AssumptionRisk` class add:

```python
_RISK_ORDER = {"high": 3, "medium": 2, "low": 1, "unknown": 0}


def aggregate_overall_risk(levels: list[RiskLevel]) -> RiskLevel:
    """high が1つでも→high / 次点 medium / 全 unknown→unknown / それ以外 low。"""
    if not levels:
        return "unknown"
    if "high" in levels:
        return "high"
    if "medium" in levels:
        return "medium"
    if all(x == "unknown" for x in levels):
        return "unknown"
    return "low"


class AssumptionScore(BaseModel):
    overall_risk: RiskLevel
    summary: str
    items: list[AssumptionRisk]
    model_config = ConfigDict(extra="forbid")
```

At the end of the file, add the wrapper (uses `assess_assumption_risks` + `summarize_risks`, both already defined):

```python
def assess_assumption_score(
    assumptions: Assumptions,
    result: AnalysisResult,
    normalized: NormalizedProperty | None = None,
    market: MarketBenchmark | None = None,
) -> AssumptionScore:
    items = assess_assumption_risks(assumptions, result, normalized, market)
    overall = aggregate_overall_risk([i.risk_level for i in items])
    return AssumptionScore(
        overall_risk=overall, summary=summarize_risks(items), items=items
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_assumption_score.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/risk_engine.py \
        re_invest_os/apps/api/tests/test_assumption_score.py \
        re_invest_os/apps/api/tests/conftest.py
git commit -m "feat(risk): AssumptionScore aggregate with overall_risk"
```

---

## Task 3: DSCR coupling + exit-dependency rule + 2 new categories

**Files:**
- Modify: `apps/api/src/api/services/risk_engine.py`
- Test: `apps/api/tests/test_assumption_score.py`

Adds: (a) `_apply_dscr_coupling` bumping rent/interest_rate/opex to ≥medium when `1.00 ≤ dscr_min ≤ 1.15`; (b) exit-share rule in `_exit_price_risk`; (c) `sale_year` + `acquisition_cost` categories.

- [ ] **Step 1: Write the failing tests**

Append to `apps/api/tests/test_assumption_score.py`:

```python
import copy


def test_dscr_coupling_bumps_to_medium(base_assumptions):
    # Engineer dscr_min into [1.00, 1.15] by loading the property heavily.
    a = copy.deepcopy(base_assumptions)
    a = a.model_copy(update={})
    # Raise loan + rate so DSCR is thin.
    a.loan.loan_amount_yen = 35_000_000
    a.loan.interest_rate = 0.030
    s = _score(a)
    dscr_min = run_full_analysis(a).kpi.dscr_min
    assert 1.00 <= dscr_min <= 1.15, f"setup precondition; got {dscr_min}"
    by_cat = {i.category: i.risk_level for i in s.items}
    order = {"high": 3, "medium": 2, "low": 1, "unknown": 0}
    for cat in ("rent", "interest_rate", "opex"):
        assert order[by_cat[cat]] >= order["medium"], cat


def test_exit_share_marks_exit_price_high(base_assumptions):
    s = _score(base_assumptions)
    result = run_full_analysis(base_assumptions)
    net = result.exit_.net_proceeds_yen
    share = net / (sum(cf.atcf_yen for cf in result.yearly_cashflows) + net)
    exit_item = next(i for i in s.items if i.category == "exit_price")
    if share > 0.60:
        assert exit_item.risk_level == "high"


def test_new_categories_present(base_assumptions):
    s = _score(base_assumptions)
    cats = {i.category for i in s.items}
    assert "sale_year" in cats
    assert "acquisition_cost" in cats
    assert len(s.items) == 9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_assumption_score.py -v`
Expected: FAIL — `sale_year`/`acquisition_cost` not in categories (len==7); coupling not applied.

- [ ] **Step 3: Implement**

In `risk_engine.py` extend the `Category` literal:
```python
Category = Literal[
    "rent", "vacancy", "opex", "repair", "interest_rate", "exit_price",
    "tax", "sale_year", "acquisition_cost",
]
```

Add the exit-share branch inside `_exit_price_risk` (before the final `risk = _bump_for_low_confidence(...)` line):
```python
    atcf_sum = sum(cf.atcf_yen for cf in result.yearly_cashflows)
    denom = atcf_sum + result.exit_.net_proceeds_yen
    if denom != 0:
        exit_share = result.exit_.net_proceeds_yen / denom
        if exit_share > 0.60:
            risk = "high"
            reasons.append(
                f"投資リターンの {exit_share * 100:.0f}% が売却時手取りに依存"
            )
```

Add two category functions (after `_tax_risk`):
```python
def _sale_year_risk(
    a: Assumptions, result: AnalysisResult, norm: NormalizedProperty
) -> AssumptionRisk:
    conf = norm.confidence_for("exit.hold_period_years", default="D")
    atcf_sum = sum(cf.atcf_yen for cf in result.yearly_cashflows)
    denom = atcf_sum + result.exit_.net_proceeds_yen
    exit_share = result.exit_.net_proceeds_yen / denom if denom else 0.0
    risk: RiskLevel = "low"
    if conf in ("C", "D") and exit_share > 0.5:
        risk = "medium"
    risk = _bump_for_low_confidence(risk, conf)
    return AssumptionRisk(
        category="sale_year",
        confidence=conf,
        risk_level=risk,
        reason="保有年数の前提が出口依存度に影響する" if risk != "low"
        else "保有年数は標準的レンジ",
        value_json={"hold_period_years": a.exit_.hold_period_years},
    )


def _acquisition_cost_risk(a: Assumptions, norm: NormalizedProperty) -> AssumptionRisk:
    conf = norm.confidence_for("acquisition.acquisition_cost_rate", default="D")
    risk: RiskLevel = "medium" if conf == "D" else "low"
    return AssumptionRisk(
        category="acquisition_cost",
        confidence=conf,
        risk_level=risk,
        reason="諸費用率がデフォルト仮定。過小評価で初期投下資本を見誤る" if risk != "low"
        else "諸費用率は資料/入力に基づく",
        value_json={"acquisition_cost_rate": a.acquisition.acquisition_cost_rate},
    )
```

Add a coupling pass (top-level function):
```python
def _apply_dscr_coupling(
    result: AnalysisResult, risks: list[AssumptionRisk]
) -> list[AssumptionRisk]:
    dscr_min = result.kpi.dscr_min
    if not (1.00 <= dscr_min <= 1.15):
        return risks
    targets = {"rent", "interest_rate", "opex"}
    out: list[AssumptionRisk] = []
    for r in risks:
        if r.category in targets and r.risk_level in ("low", "unknown"):
            note = f"; DSCR最小 {dscr_min:.2f} の薄い返済余力下では前提悪化が直ちに返済を圧迫"
            out.append(r.model_copy(update={
                "risk_level": "medium", "reason": r.reason + note,
            }))
        else:
            out.append(r)
    return out
```

Wire the two new categories into `assess_assumption_risks` return list:
```python
    return [
        _rent_risk(assumptions, norm, market),
        _vacancy_risk(assumptions, norm, market),
        _opex_risk(assumptions, norm),
        _repair_risk(assumptions, norm),
        _interest_rate_risk(assumptions, norm),
        _exit_price_risk(assumptions, result, norm, market),
        _tax_risk(assumptions, norm),
        _sale_year_risk(assumptions, result, norm),
        _acquisition_cost_risk(assumptions, norm),
    ]
```

And apply coupling in `assess_assumption_score` (Task 2 wrapper):
```python
    items = assess_assumption_risks(assumptions, result, normalized, market)
    items = _apply_dscr_coupling(result, items)
    overall = aggregate_overall_risk([i.risk_level for i in items])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_assumption_score.py -v`
Expected: PASS. If `test_dscr_coupling_bumps_to_medium` precondition assert fails, adjust the loan/rate in the test until `1.00 ≤ dscr_min ≤ 1.15` holds, then re-run.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/risk_engine.py \
        re_invest_os/apps/api/tests/test_assumption_score.py
git commit -m "feat(risk): DSCR coupling, exit-share rule, sale_year+acquisition_cost categories"
```

---

## Task 4: Delete `score.py`; switch `/analyze`, `/sample`, deals router to `assumption_score`

**Files:**
- Delete: `packages/financial-engine/src/re_engine/score.py`, `packages/financial-engine/tests/test_score.py`
- Modify: `apps/api/src/api/main.py`
- Modify: `apps/api/src/api/routers/deals.py`
- Test: `apps/api/tests/test_main.py`

- [ ] **Step 1: Write the failing test**

Append to `apps/api/tests/test_main.py` (it already uses a FastAPI `TestClient`; reuse the existing `client` fixture/pattern in that file):

```python
def test_analyze_returns_assumption_score(client, base_assumptions):
    resp = client.post("/analyze", json={"assumptions": base_assumptions.model_dump(by_alias=True)})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "assumption_score" in body
    assert "score" not in body
    s = body["assumption_score"]
    assert s["overall_risk"] in ("low", "medium", "high", "unknown")
    assert len(s["items"]) == 9
    assert body["analysis"]["kpi"]["dead_cross_year"] is None or isinstance(
        body["analysis"]["kpi"]["dead_cross_year"], int
    )
```

If `test_main.py` builds the client differently, match its existing fixture. Confirm with: `grep -n "TestClient\|client" re_invest_os/apps/api/tests/test_main.py | head`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_main.py::test_analyze_returns_assumption_score -v`
Expected: FAIL — response has `score`, not `assumption_score`.

- [ ] **Step 3: Implement**

Delete the two files:
```bash
git rm re_invest_os/packages/financial-engine/src/re_engine/score.py \
       re_invest_os/packages/financial-engine/tests/test_score.py
```

In `apps/api/src/api/main.py`:
- Remove line 46 `from re_engine.score import DataQuality, MarketContext, ScoreResult, total_score`.
- Add `from api.services.risk_engine import AssumptionScore, assess_assumption_score`.
- Replace `AnalyzeRequest` (remove score-only fields):
  ```python
  class AnalyzeRequest(BaseModel):
      assumptions: Assumptions
      normalized_property: dict | None = None
      model_config = ConfigDict(extra="forbid")
  ```
- Replace `AnalyzeResponse`:
  ```python
  class AnalyzeResponse(BaseModel):
      analysis: AnalysisResult
      assumption_score: AssumptionScore
      model_config = ConfigDict(extra="forbid")
  ```
- Replace `analyze()` body:
  ```python
  @app.post("/analyze", response_model=AnalyzeResponse)
  def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
      result = run_full_analysis(req.assumptions)
      norm = (
          NormalizedProperty.model_validate(req.normalized_property)
          if req.normalized_property else NormalizedProperty.all_user_input()
      )
      score = assess_assumption_score(req.assumptions, result, norm)
      return AnalyzeResponse(analysis=result, assumption_score=score)
  ```
  Add import at top: `from re_engine.normalized import NormalizedProperty`.
- Replace `sample_nishi_shinjuku()` body's score lines:
  ```python
      a = _sample_assumptions()
      result = run_full_analysis(a)
      score = assess_assumption_score(a, result, NormalizedProperty.all_user_input())
      return AnalyzeResponse(analysis=result, assumption_score=score)
  ```

In `apps/api/src/api/routers/deals.py`:
- Remove `from re_engine.score import total_score` (line 25).
- Add `from api.services.risk_engine import assess_assumption_score`.
- Replace the metrics block (around line 293):
  ```python
      analysis = run_full_analysis(assumptions)
      normalized = req.normalized_property or {"field_sources": {}}
      from re_engine.normalized import NormalizedProperty
      norm_obj = NormalizedProperty.model_validate(normalized)
      score = assess_assumption_score(assumptions, analysis, norm_obj)
      metrics = {
          "analysis": analysis.model_dump(mode="json", by_alias=True),
          "assumption_score": score.model_dump(mode="json"),
      }
  ```
  (Keep the rest of the deals handler unchanged. If later code in this handler reads `metrics["score"]`, update those reads to `metrics["assumption_score"]` — grep: `grep -n 'metrics\["score"\]\|\.score' re_invest_os/apps/api/src/api/routers/deals.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run:
```
uv run --no-sync pytest re_invest_os/apps/api/tests/test_main.py -v
uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -q
```
Expected: new test PASS; engine suite PASS (test_score.py gone). Fix any other `from re_engine.score import` references surfaced by: `grep -rn "re_engine.score\|total_score\|ScoreResult" re_invest_os/ --include=*.py | grep -v __pycache__`.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/main.py \
        re_invest_os/apps/api/src/api/routers/deals.py \
        re_invest_os/apps/api/tests/test_main.py \
        re_invest_os/packages/financial-engine/src/re_engine/score.py \
        re_invest_os/packages/financial-engine/tests/test_score.py
git commit -m "feat(api): replace property score with assumption_score; delete score.py"
```

---

## Task 5: Adapt summarizer LLM context to `assumption_score`

**Files:**
- Modify: `apps/api/src/api/services/summarizer.py`
- Modify: `apps/api/src/api/main.py` (`/summarize`, `/critique` request shapes)
- Test: `apps/api/tests/test_extended_endpoints.py` (or wherever summarize/critique is tested — confirm with `grep -rln "summarize\|critique" re_invest_os/apps/api/tests/`)

The three functions read `score_result["total"]` / `["evaluation"]`. Switch them to read an `assumption_score` dict (`overall_risk`, `items`). LLM-output NG filtering stays.

- [ ] **Step 1: Write the failing test**

Add to the summarizer/critique test file (LLM is monkeypatched there already — match the existing monkeypatch of `chat_json`; confirm pattern first). Minimal new assertion:

```python
def test_build_summary_user_uses_overall_risk():
    from api.services.summarizer import _build_summary_user
    analysis = {"kpi": {"cap_rate": 0.05, "dscr_min": 1.1, "dscr_year1": 1.2,
                        "equity_irr": 0.07, "atcf_first_year_yen": -45000},
                "exit": {"net_proceeds_yen": 1000000}}
    assumption_score = {"overall_risk": "high", "summary": "x", "items": []}
    msg = _build_summary_user(analysis, assumption_score)
    assert "high" in msg
    assert "/100" not in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/ -k build_summary_user -v`
Expected: FAIL — current `_build_summary_user` signature/content references `total`/`/100`.

- [ ] **Step 3: Implement**

In `summarizer.py`, rename the `score_result` parameter to `assumption_score` in `_build_summary_user`, `generate_summary`, `generate_inquiry`, `generate_critique`. Replace the score reads:

`_build_summary_user`: replace lines reading `score`/`evaluation` and the `analysis_json` build:
```python
    overall = assumption_score.get("overall_risk", "unknown")
    analysis_json = (
        f'{{"overall_risk": "{overall}", '
        f'"cap_rate_pct": "{cap_pct}", "dscr_min": {dscr_min}, "dscr_y1": {dscr_y1}, '
        f'"equity_irr": "{irr_str}", "atcf_y1_yen": {atcf}, '
        f'"exit_net_proceeds_yen": {net_proc}}}'
    )
```

`generate_inquiry`: replace `score_total`/`evaluation` block:
```python
    overall = assumption_score.get("overall_risk", "unknown")
    dscr_min = kpi.get("dscr_min", "—")
    atcf_y1 = kpi.get("atcf_first_year_yen", 0)
    atcf_str = f"¥{atcf_y1:,}" if isinstance(atcf_y1, int) else str(atcf_y1)
    missing = ", ".join(needs_confirmation or []) or "なし"
    analysis_summary = (
        f"総合前提リスク: {overall}\n"
        f"DSCR最小: {dscr_min}\n"
        f"ATCF Y1: {atcf_str}\n"
        f"資料不足: {missing}"
    )
```

`generate_critique`: replace the `summary` build that uses `score_result`:
```python
    overall = assumption_score.get("overall_risk", "unknown")
    summary = (
        f"総合前提リスク: {overall}\n"
        f"DSCR最小: {kpi.get('dscr_min', '—')}  Cap: {kpi.get('cap_rate', '—'):.3f}"
        if isinstance(kpi.get("cap_rate"), float)
        else f"総合前提リスク: {overall}"
    )
```

In `apps/api/src/api/main.py`: rename the request field `score_result` → `assumption_score` in `SummarizeRequest` and `CritiqueRequest`, and pass `req.assumption_score` to `generate_summary`/`generate_inquiry`/`generate_critique`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/ -k "summary or critique or inquiry" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/services/summarizer.py \
        re_invest_os/apps/api/src/api/main.py \
        re_invest_os/apps/api/tests/
git commit -m "feat(api): summarizer/inquiry/critique context from assumption_score"
```

---

## Task 6: Persistence — `/analyses` save + history use assumption_score (no DB migration)

**Files:**
- Modify: `apps/api/src/api/main.py` (`SaveAnalysisRequest`, `post_save_analysis`, `list_analyses`)
- Test: `apps/api/tests/test_db.py` or `test_main.py` (match existing save test)

`analyses.score_total` is a non-null float and `score_result` is a generic JSON Text column. To avoid a destructive migration: keep both columns; set `score_total` to the **count of high-risk items** (a non-quality integer-valued float) and store the full `assumption_score` JSON in `score_result`.

- [ ] **Step 1: Write the failing test**

Add to `apps/api/tests/test_db.py` (it already exercises `save_analysis`; match its async style):

```python
import pytest


@pytest.mark.asyncio
async def test_save_analysis_accepts_assumption_score(tmp_path, monkeypatch):
    # Reuse the file's existing DB-setup helper/fixture. Save with assumption_score
    # JSON and assert score_result round-trips and score_total == high-risk count.
    ...
```

If `test_db.py` has a reusable fixture for an initialized DB, use it; otherwise mirror the existing save test in that file exactly, substituting an `assumption_score` payload `{"overall_risk":"high","summary":"x","items":[{"category":"rent","confidence":"C","risk_level":"high","reason":"r","source":null,"value_json":null}]}` and asserting the stored `score_result` equals it and `score_total == 1.0`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_db.py -k assumption_score -v`
Expected: FAIL.

- [ ] **Step 3: Implement**

In `apps/api/src/api/main.py`:
- `SaveAnalysisRequest`: rename `score_result: dict` → `assumption_score: dict`.
- `post_save_analysis`:
  ```python
      items = req.assumption_score.get("items", [])
      high_count = float(sum(1 for i in items if i.get("risk_level") == "high"))
      kpi = req.analysis_result.get("kpi", {})
      analysis_id = await save_analysis(
          ...
          score_total=high_count,
          score_result=req.assumption_score,
          ...
      )
  ```
  (Keep `save_analysis`'s parameter names; we are only changing the values passed.)
- `list_analyses`: rename the emitted `"score_total"` key to `"high_risk_count"` in the response dict (value `r.score_total`). This keeps the DB column but reframes the API field. Note the frontend history page must read `high_risk_count` (handled in Task 8 grep sweep).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_db.py re_invest_os/apps/api/tests/test_main.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/main.py re_invest_os/apps/api/tests/
git commit -m "feat(api): persist assumption_score; reframe history field as high_risk_count"
```

---

## Task 7: NG-expression enforcement (wordlist + DISCLAIMERS + scan test)

**Files:**
- Create: `apps/api/src/api/constants.py`
- Modify: `apps/api/src/api/services/ng_filter.py`
- Create: `apps/api/tests/test_ng_expressions.py`

- [ ] **Step 1: Write the failing tests**

Create `apps/api/tests/test_ng_expressions.py`:

```python
from pathlib import Path

from api.services.ng_filter import find_ng, has_ng

_REPO = Path(__file__).resolve().parents[3]  # re_invest_os/


def test_ng_detects_new_phrases():
    assert has_ng("推奨買付価格は3300万円です")
    assert has_ng("この物件は良いです")
    assert has_ng("購入すべきです")
    assert has_ng("見送り推奨")


def test_ng_allows_legitimate_buy_terms():
    # 裸の「買い」を誤検出しない
    assert not has_ng("買い手側のDDツール")
    assert not has_ng("買付前の収支耐性を検証")
    assert not has_ng("買い増しの検討")


def test_disclaimers_are_clean_of_ng_by_design():
    from api.constants import DISCLAIMERS
    # Disclaimers legitimately contain 推奨/購入; they are excluded from scan,
    # but must not contain assertive value-judgment phrases.
    for d in DISCLAIMERS.values():
        assert "この物件は良い" not in d
        assert "この物件は悪い" not in d


def test_ui_and_prompt_surfaces_have_no_ng():
    from api.constants import DISCLAIMERS
    disclaimer_texts = set(DISCLAIMERS.values())
    globs = [
        _REPO / "apps/web/src",          # *.tsx/*.ts UI labels
        _REPO / "docs/prompts",          # *.md prompt templates
    ]
    offenders: list[str] = []
    for root in globs:
        for path in list(root.rglob("*.tsx")) + list(root.rglob("*.ts")) + list(root.rglob("*.md")):
            if "node_modules" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            # Strip lines that are exactly a known disclaimer block.
            for d in disclaimer_texts:
                text = text.replace(d, "")
            if has_ng(text):
                offenders.append(f"{path}: {find_ng(text)}")
    assert not offenders, "NG expressions found:\n" + "\n".join(offenders)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_ng_expressions.py -v`
Expected: FAIL — new phrases not in wordlist; `api.constants` missing; existing UI strings (e.g. `report-panels.tsx` "健全性スコア" / "買い推奨ではありません") trip the scan.

- [ ] **Step 3: Implement**

Create `apps/api/src/api/constants.py`:
```python
"""法務文言の単一ソース。NG スキャンの allowlist 対象。"""

DISCLAIMERS: dict[str, str] = {
    "report": (
        "本レポートは、ユーザー入力情報および公開情報に基づく収支シミュレーションです。"
        "特定の不動産の購入、売却、保有、融資利用を推奨するものではありません。"
        "実際の投資判断にあたっては、宅地建物取引士、税理士、弁護士、金融機関等の"
        "専門家に確認してください。"
    ),
    "sensitivity": "以下は投資判断ではなく、入力条件に対する感応度分析です。",
}
```

In `ng_filter.py`, extend `NG_WORDS` (curated phrases — NO bare 買い):
```python
    # 買付・価格判断
    "推奨買付価格",
    "買いです",
    "買いだ",
    "買いと判断",
    "購入すべき",
    "見送り推奨",
    # 物件価値の断定
    "この物件は良い",
    "この物件は悪い",
    "健全性スコア",
```
(Keep existing entries. `割安` / `おすすめ` / `儲かる` / `確実` / `保証` already present.)

Then make the offending UI/prompt strings clean as part of this task's red→green (these are also touched in Task 8, but the scan must pass now):
- In `apps/web/src/components/report-panels.tsx` change the line "分析上の健全性スコア。買い推奨ではありません。前提を変えれば変動します。" to "前提リスクの検証結果です。投資判断ではありません。前提を変えれば変動します。"
- Sweep any other hits reported by the failing test and rephrase using §2.2 allowed vocabulary.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest re_invest_os/apps/api/tests/test_ng_expressions.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/api/src/api/constants.py \
        re_invest_os/apps/api/src/api/services/ng_filter.py \
        re_invest_os/apps/api/tests/test_ng_expressions.py \
        re_invest_os/apps/web/src/components/report-panels.tsx
git commit -m "feat(legal): expand NG wordlist + DISCLAIMERS + enforced surface scan"
```

---

## Task 8: Frontend — remove property score, promote 甘さスコア, regen types

**Files:**
- Modify: `apps/web/src/types/api.ts`
- Modify: `apps/web/src/components/report-panels.tsx`
- Modify: `apps/web/src/components/deal/DealSummaryCard.tsx`
- Modify: `apps/web/src/app/report/page.tsx`

- [ ] **Step 1: Establish the failing check (typecheck)**

There is no JS test runner wired for these components; the gate is `tsc --noEmit` plus the NG scan (Task 7) and the manual integration check (Task 9). First make the type change that forces the consumers to update:

In `apps/web/src/types/api.ts`: remove the `ScoreResult` type and add:
```typescript
export type RiskLevel = "low" | "medium" | "high" | "unknown";
export type Confidence = "A" | "B" | "C" | "D";

export interface AssumptionRiskItem {
  category: string;
  confidence: Confidence;
  risk_level: RiskLevel;
  reason: string;
  source?: string | null;
  value_json?: Record<string, unknown> | null;
}

export interface AssumptionScore {
  overall_risk: RiskLevel;
  summary: string;
  items: AssumptionRiskItem[];
}
```
Update `AnalyzeResponse` (or equivalent) to use `assumption_score: AssumptionScore` and drop the `score` field.

- [ ] **Step 2: Run typecheck to see failures**

Run: `cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`
Expected: FAIL where `report-panels.tsx`, `DealSummaryCard.tsx`, `report/page.tsx` reference the removed `score`/`evaluation`/`components`.

- [ ] **Step 3: Implement**

- `DealSummaryCard.tsx`: remove the `score` prop usage — delete the `meta={score.evaluation ...}` and the `KpiCell name="SCORE"` cell. Replace with an `OVERALL RISK` cell reading `assumption_score.overall_risk` (uppercased), or drop entirely if the parent now renders the risk panel.
- `report-panels.tsx`: delete the 100-point score panel (the `data.score.components.map(...)` block and surrounding Panel). Keep/rename the existing assumption-risk ("ASSUMPTION CRITIQUE") panel to a primary "前提リスク検証 / ASSUMPTION RISK" panel that renders `assumption_score.overall_risk` + `items` (category, confidence, risk_level, reason). Remove the "MAX OFFER 最大買付価格" panel's value-judgment copy only if present (full rename is Spec 2 — leave the panel itself).
- `report/page.tsx`: replace every `score_result: parsed.score` with `assumption_score: parsed.assumption_score`; replace `score_total: data.score.total` reads; remove the `/api/max_offer` dependence on score if any. Where it POSTs to `/api/summarize`, `/api/critique`, `/api/save`, send `assumption_score` (matching the renamed request fields from Tasks 5–6).
- History page: if it reads `score_total`, switch to `high_risk_count` (grep: `grep -rn "score_total\|\.score\b\|evaluation" re_invest_os/apps/web/src`).

- [ ] **Step 4: Run typecheck + NG scan to verify pass**

Run:
```
cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit
cd ~/projects && uv run --no-sync pytest re_invest_os/apps/api/tests/test_ng_expressions.py -v
```
Expected: typecheck clean; NG scan PASS.

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/apps/web/src/types/api.ts \
        re_invest_os/apps/web/src/components/report-panels.tsx \
        re_invest_os/apps/web/src/components/deal/DealSummaryCard.tsx \
        re_invest_os/apps/web/src/app/report/page.tsx
git commit -m "feat(web): replace property score UI with assumption_score; regen types"
```

---

## Task 9: Integration verification + regression

**Files:** none (verification only); fix-ups as needed.

- [ ] **Step 1: Full regression**

Run:
```
uv run --no-sync pytest re_invest_os/ -q
uv run --no-sync ruff check re_invest_os/
cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit
```
Expected: all green. Fix any stragglers (e.g., other `score`/`evaluation`/`ScoreResult` references) until green.

- [ ] **Step 2: Observe real output (sample property)**

Start API: `cd re_invest_os && uv run --no-sync uvicorn api.main:app --host 127.0.0.1 --port 8001 --app-dir apps/api/src` (background), then:
```
curl -s http://127.0.0.1:8001/sample/nishi-shinjuku | python -m json.tool | head -60
```
Confirm in output: `assumption_score.overall_risk` present, `items` has 9 entries with `category`/`confidence`/`risk_level`/`reason`, `analysis.kpi.dead_cross_year` present, and **no** `score`/`健全`/`要警戒` keys. Quote the observed overall_risk + one item + dead_cross_year in the completion report.

- [ ] **Step 3: UI wired check**

Start web (`cd re_invest_os/apps/web && node_modules/.bin/next dev --port 3001`) with API running. Use the webapp-testing skill (Playwright) to load `/sample` → report and screenshot. Confirm the report shows the 前提リスク panel as primary with overall_risk + items, and that "健全"/"要警戒"/"SCORE" are absent. Capture the screenshot path in the report.

- [ ] **Step 4: Update docs**

In `re_invest_os/README.md` add a short "MVP redefinition (2026-05-30)" note pointing to `docs/design/2026-05-30-mvp-redefinition-design.md`, and update `docs/architecture/calculation_engine_spec.md` to note `score.py` removed and `dead_cross_year` added (engine 0.2.0).

- [ ] **Step 5: Commit**

```bash
git add re_invest_os/README.md re_invest_os/docs/architecture/calculation_engine_spec.md
git commit -m "docs(reio): record MVP redefinition; engine 0.2.0 (dead_cross_year, score removed)"
```

---

## Self-Review notes

- **Spec coverage:** dead_cross (T1), 甘さスコア集約+overall_risk (T2), DSCR coupling/exit-share/2 categories (T3), score撤去+API (T4), summarizer reframe (T5), persistence reframe (T6), NG enforcement (T7), frontend (T8), integration+docs (T9). schema凍結/再現性: `analysis_runs` already persists `input_snapshot_json`+`normalized_property_json`; engine_version pinned to 0.2.0 (T1). confidence-A 昇格 hook and market照合 are explicitly Later (out of Spec 1).
- **Type consistency:** `AssumptionScore`/`AssumptionRisk`/`RiskLevel`/`Confidence`/`Category` names match across Python (risk_engine.py) and TS (api.ts). `assess_assumption_score(assumptions, result, normalized, market)` signature is stable across T2/T3/T4.
- **Non-destructive DB:** no column drops/migrations; `score_total` repurposed to high-risk count (non-null float), `score_result` JSON holds assumption_score.
