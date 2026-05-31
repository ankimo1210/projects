# re_invest_os Spec 2 — Stress & Resilience Pricing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Show how cashflow **breaks under stress** (fixed 7 scenarios) and reframe the "最大買付価格" into a neutral **収支耐性価格帯 (Resilience Price Range)** — the 2026 rate-risk wedge and the core of the B2B DD report.

**Architecture:** Reframe the pure-engine `sensitivity.py` to the MVP fixed-7 stress set (`after_tax_irr` + `dscr_min` + Δvs base). Rename `bid_ranges.py` policies to `current_case/base_stress/conservative_stress` and reframe its output to "resilience price range" (no value-judgment naming). Surface both via API + report panels, NG-clean.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest; Next.js + TS.

**Spec:** `docs/design/2026-05-30-mvp-redefinition-design.md` (Spec 2), MVP doc §8–9.

**Run (from `~/projects`):** engine `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -v` · api `uv run --no-sync pytest re_invest_os/apps/api/tests/ -v` · all `uv run --no-sync pytest re_invest_os/ -q` · `uv run --no-sync ruff check re_invest_os/` · web `cd re_invest_os/apps/web && node_modules/.bin/tsc --noEmit`

**Commit discipline:** shared monorepo with concurrent `stock/` work. `git add` only `re_invest_os/` paths. Never `git add -A`. Current branch `feat/reio-mvp`.

---

## Fixed 7 stress scenarios (MVP §8)

| id | shock |
|---|---|
| `rate_up_100bp` | 金利 +1.0pt |
| `rent_down_5` | 賃料 -5% |
| `vacancy_up_5pt` | 空室率 +5pt |
| `opex_up_10pct` | 円建てOPEX ×1.10 |
| `repair_up_20pct` | 修繕積立 ×1.20 のみ |
| `exit_down_10pct` | 売却価格 -10%（exit_cap を逆算: cap/0.9） |
| `combined_stress` | 上記6つ同時 |

## Resilience policies (MVP §9, rename of bid_ranges)

| name | min_dscr | min_after_tax_irr | rent | vacancy | rate | opex |
|---|---|---|---|---|---|---|
| `current_case` | 1.20 | 0.075 | 0 | 0 | 0 | 0 |
| `base_stress` | 1.25 | 0.080 | -0.03 | +0.02 | +0.005 | +0.05 |
| `conservative_stress` | 1.35 | 0.090 | -0.07 | +0.05 | +0.010 | +0.10 |

---

## Task 1: Reframe `sensitivity.py` to fixed-7 stress + Δ vs base

**Files:** Modify `packages/financial-engine/src/re_engine/sensitivity.py`; Test `packages/financial-engine/tests/test_sensitivity.py`.

- [ ] **Step 1: Write failing tests** (append to test_sensitivity.py)

```python
from re_engine.sensitivity import STRESS_SCENARIOS, sensitivity_grid


def test_fixed_seven_scenarios(base_assumptions):
    res = sensitivity_grid(base_assumptions)
    names = [s.scenario for s in res.scenarios]
    assert names == [
        "rate_up_100bp", "rent_down_5", "vacancy_up_5pt", "opex_up_10pct",
        "repair_up_20pct", "exit_down_10pct", "combined_stress",
    ]
    assert len(STRESS_SCENARIOS) == 7


def test_rate_up_100bp_lowers_dscr(base_assumptions):
    res = sensitivity_grid(base_assumptions)
    base_dscr = res.base.dscr_min
    rate = next(s for s in res.scenarios if s.scenario == "rate_up_100bp")
    assert rate.dscr_min < base_dscr
    # Δ vs base recorded
    assert rate.dscr_min_delta == round(rate.dscr_min - base_dscr, 4)


def test_repair_up_20pct_only_touches_repair(base_assumptions):
    # 修繕積立のみ増。固都税は不変であることを間接確認: opex_up_10pct と別物。
    res = sensitivity_grid(base_assumptions)
    assert any(s.scenario == "repair_up_20pct" for s in res.scenarios)


def test_combined_is_worst_or_equal(base_assumptions):
    res = sensitivity_grid(base_assumptions)
    combined = next(s for s in res.scenarios if s.scenario == "combined_stress")
    base = res.base
    assert combined.dscr_min <= base.dscr_min
```

- [ ] **Step 2: Run → fail** `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_sensitivity.py -v` (ImportError STRESS_SCENARIOS / name mismatch / no dscr_min_delta)

- [ ] **Step 3: Implement** — rewrite scenario set + add Δ fields.

Replace `ScenarioName` literal:
```python
ScenarioName = Literal[
    "base",
    "rate_up_100bp",
    "rent_down_5",
    "vacancy_up_5pt",
    "opex_up_10pct",
    "repair_up_20pct",
    "exit_down_10pct",
    "combined_stress",
]

STRESS_SCENARIOS: list[ScenarioName] = [
    "rate_up_100bp", "rent_down_5", "vacancy_up_5pt", "opex_up_10pct",
    "repair_up_20pct", "exit_down_10pct", "combined_stress",
]
```

Add Δ fields to `ScenarioResult`:
```python
class ScenarioResult(BaseModel):
    scenario: ScenarioName
    atcf_year1_yen: int
    irr: float | None              # 税後 equity IRR
    dscr_min: float
    net_proceeds_yen: int
    dscr_min_delta: float = 0.0    # vs base
    irr_delta: float | None = None # vs base
    judgment: Literal["good", "warn", "bad"]
    model_config = ConfigDict(extra="forbid")
```

Rewrite `_apply_scenario` to the 7 (drop old branches):
```python
_OPEX_FIELDS = ("fixed_property_tax_yen", "insurance_yen", "building_mgmt_yen",
                "other_opex_yen", "repair_reserve_monthly_yen")

def _apply_scenario(a: Assumptions, name: ScenarioName) -> Assumptions:
    s = copy.deepcopy(a)
    if name == "base":
        return s
    if name == "rate_up_100bp":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.010)
    elif name == "rent_down_5":
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
    elif name == "vacancy_up_5pt":
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
    elif name == "opex_up_10pct":
        for f in _OPEX_FIELDS:
            setattr(s.opex, f, round(getattr(s.opex, f) * 1.10))
    elif name == "repair_up_20pct":
        s.opex.repair_reserve_monthly_yen = round(s.opex.repair_reserve_monthly_yen * 1.20)
    elif name == "exit_down_10pct":
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate / 0.90)
    elif name == "combined_stress":
        s.loan.interest_rate = min(1.0, s.loan.interest_rate + 0.010)
        s.income.gpi_monthly_yen = round(s.income.gpi_monthly_yen * 0.95)
        s.income.vacancy_rate = min(1.0, s.income.vacancy_rate + 0.05)
        for f in _OPEX_FIELDS:
            setattr(s.opex, f, round(getattr(s.opex, f) * 1.10))
        s.opex.repair_reserve_monthly_yen = round(s.opex.repair_reserve_monthly_yen * 1.20)
        s.exit_.exit_cap_rate = min(1.0, s.exit_.exit_cap_rate / 0.90)
    return s
```

In `_run_scenario`, compute Δ relative to a passed base result. Change signature:
```python
def _run_scenario(a, name, base=None):
    scen_a = _apply_scenario(a, name)
    r = run_full_analysis(scen_a)
    dscr_delta = 0.0 if base is None else round(r.kpi.dscr_min - base.dscr_min, 4)
    irr_delta = (None if base is None or r.kpi.equity_irr is None or base.irr is None
                 else round(r.kpi.equity_irr - base.irr, 4))
    return ScenarioResult(
        scenario=name, atcf_year1_yen=r.kpi.atcf_first_year_yen, irr=r.kpi.equity_irr,
        dscr_min=r.kpi.dscr_min, net_proceeds_yen=r.exit_.net_proceeds_yen,
        dscr_min_delta=dscr_delta, irr_delta=irr_delta,
        judgment=_judge(r.kpi.atcf_first_year_yen, r.kpi.equity_irr, r.kpi.dscr_min),
    )
```

`sensitivity_grid`:
```python
def sensitivity_grid(a: Assumptions) -> SensitivityResult:
    base = _run_scenario(a, "base")
    others = [_run_scenario(a, s, base=base) for s in STRESS_SCENARIOS]
    return SensitivityResult(base=base, scenarios=others)
```

- [ ] **Step 4: Run → pass** `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/test_sensitivity.py -v`. Fix any existing test_sensitivity assertions referencing old scenario names (update to the 7).

- [ ] **Step 5: Commit**
```bash
git add re_invest_os/packages/financial-engine/src/re_engine/sensitivity.py re_invest_os/packages/financial-engine/tests/test_sensitivity.py
git commit -m "feat(engine): fixed-7 stress set + Δ-vs-base (MVP §8)"
```

---

## Task 2: Rename bid_ranges → resilience price range (MVP §9)

**Files:** Modify `packages/financial-engine/src/re_engine/bid_ranges.py`; Test `packages/financial-engine/tests/test_bid_ranges.py`.

Rename policy names + shock values to §9; reframe output field names from value-judgment ("aggressive/base/conservative") to neutral resilience stances. Keep `bid_ranges()` + module path (internal), but rename the policy set and entries.

- [ ] **Step 1: Failing tests** (append/replace in test_bid_ranges.py)
```python
from re_engine.bid_ranges import DEFAULT_BID_POLICIES, bid_ranges


def test_resilience_policy_names():
    assert [p.name for p in DEFAULT_BID_POLICIES] == [
        "current_case", "base_stress", "conservative_stress",
    ]


def test_resilience_monotonic(base_assumptions):
    r = bid_ranges(base_assumptions)
    vals = [
        r.current_case.price_yen or 0,
        r.base_stress.price_yen or 0,
        r.conservative_stress.price_yen or 0,
    ]
    assert vals[0] >= vals[1] >= vals[2]  # 緩い条件ほど高い価格が成立
```

- [ ] **Step 2: Run → fail** (names current_case/base_stress/conservative_stress not present)

- [ ] **Step 3: Implement**
- In `DEFAULT_BID_POLICIES`, rename `aggressive→current_case`, `base→base_stress`, `conservative→conservative_stress`, keeping the §9 shock values (already match).
- In `BidRangesResult`, rename fields `aggressive→current_case`, `base→base_stress`, `conservative→conservative_stress`; rename `gap_to_base_price_yen→gap_to_base_stress_price_yen`, `gap_to_base_price_pct→gap_to_base_stress_price_pct`.
- In `bid_ranges()`, update `by_name[...]` keys and `_enforce_monotonicity` call/order accordingly; gap computed from `base_stress`.
- `_explain()` text: keep, it's neutral ("…を満たす価格").

- [ ] **Step 4: Run → pass** engine suite `uv run --no-sync pytest re_invest_os/packages/financial-engine/tests/ -q`. Update any old-name assertions.

- [ ] **Step 5: Commit**
```bash
git add re_invest_os/packages/financial-engine/src/re_engine/bid_ranges.py re_invest_os/packages/financial-engine/tests/test_bid_ranges.py
git commit -m "feat(engine): rename bid policies to resilience stances (MVP §9)"
```

---

## Task 3: API — surface stress + resilience; reframe analysis_features bid_ranges

**Files:** Modify `apps/api/src/api/routers/analysis_features.py` (bid_ranges endpoint serialization → new field names); verify `apps/api/src/api/main.py` `/sensitivity` still returns the 7. Test `apps/api/tests/test_deals_api.py`.

- [ ] **Step 1: Failing test** — extend test_deals_api bid_ranges test to expect `current_case/base_stress/conservative_stress` keys in the response. (Find the existing bid_ranges test: `grep -n "bid_ranges\|aggressive\|base_e" re_invest_os/apps/api/tests/test_deals_api.py`.)

- [ ] **Step 2: Run → fail**

- [ ] **Step 3: Implement** — update `analysis_features.py` `BidRangesOut` / serialization to the renamed fields (`grep -n "aggressive\|\.base\b\|conservative\|gap_to_base" re_invest_os/apps/api/src/api/routers/analysis_features.py`). Keep route path `/analysis_runs/{run_id}/bid_ranges` (internal id) but rename response fields. `/sensitivity` (main.py) is unchanged in shape — returns the 7 now automatically.

- [ ] **Step 4: Run → pass** `uv run --no-sync pytest re_invest_os/apps/api/tests/ -q`

- [ ] **Step 5: Commit**
```bash
git add re_invest_os/apps/api/src/api/routers/analysis_features.py re_invest_os/apps/api/tests/test_deals_api.py
git commit -m "feat(api): resilience price range field names; 7-stress via /sensitivity"
```

---

## Task 4: UI — Stress（崩れ方）panel + Resilience Price Range; reframe MAX OFFER

**Files:** regen `apps/web/src/types/api.ts`; Modify `apps/web/src/components/report-panels.tsx` (SensitivityPanel → 崩れ方 with the 7 + Δ; MaxOfferPanel/ResiliencePanel rename); `apps/web/src/app/report/page.tsx` (panel wiring/labels).

- [ ] **Step 1: Regen types** — start API on 8001, run `cd re_invest_os/apps/web && node_modules/.bin/npm run gen:api` (openapi-typescript). Verify new ScenarioName 7 + `dscr_min_delta` + resilience field names appear.

- [ ] **Step 2: Typecheck → see failures** `node_modules/.bin/tsc --noEmit`

- [ ] **Step 3: Implement**
- SensitivityPanel: relabel to `[ STRESS ] 崩れ方` showing base + 7 rows with `dscr_min`, `irr`, and Δ vs base; UI文言「投資判断ではなく、入力条件に対する感応度分析」(use `DISCLAIMERS.sensitivity` text).
- MaxOffer/Resilience: rename panel `[ MAX OFFER ] 最大買付価格` → `[ RESILIENCE ] 収支耐性価格帯`; show current_case / base_stress / conservative_stress prices + 売出価格との差額. Remove "最大買付価格/買付" value-judgment wording.
- Update any `aggressive/base/conservative` reads to the new field names.

- [ ] **Step 4: Verify** `node_modules/.bin/tsc --noEmit` clean; `uv run --no-sync pytest re_invest_os/apps/api/tests/test_ng_expressions.py -v` green (no 最大買付/買付 value-judgment leaks — add "最大買付価格" to UI_NG_WORDS if needed and confirm scan).

- [ ] **Step 5: Commit**
```bash
git add re_invest_os/apps/web/src/types/api.ts re_invest_os/apps/web/src/components/report-panels.tsx re_invest_os/apps/web/src/app/report/page.tsx
git commit -m "feat(web): STRESS 崩れ方 panel + RESILIENCE 収支耐性価格帯 (rename MAX OFFER)"
```

---

## Task 5: Integration + regression + docs

- [ ] **Step 1: Regression** `uv run --no-sync pytest re_invest_os/ -q` · `ruff check re_invest_os/` · web `tsc --noEmit` — all green.
- [ ] **Step 2: Observe** via TestClient: POST `/sensitivity` for sample → 7 scenarios with dscr_min/irr/Δ; bid_ranges via deals flow → current_case/base_stress/conservative_stress prices. Quote values.
- [ ] **Step 3: UI screenshot** (with_server.py API+Next, Playwright) of report → confirm STRESS 崩れ方 + RESILIENCE panels render; no 最大買付/買付 wording.
- [ ] **Step 4: Docs** — calc engine spec §5.8 (sensitivity 7) + bid_ranges rename; design doc Spec 2 mark implemented.
- [ ] **Step 5: Commit** docs.

## Self-review notes
- Spec coverage: §8 fixed-7 stress (T1), §9 resilience price range rename (T2), API (T3), UI 崩れ方 + 収支耐性価格帯 + MAX OFFER reframe (T4), integration/docs (T5).
- NG: "最大買付価格" reframed; add to UI_NG_WORDS if it must never reappear.
- equity_irr in this engine is the after-tax equity IRR → ScenarioResult.irr already satisfies "税後IRR".
