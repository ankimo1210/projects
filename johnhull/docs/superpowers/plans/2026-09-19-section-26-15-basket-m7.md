# Section 26.15 Basket Options M7 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. No worker spawns subagents; controller owns independent reviews.

**Goal:** Accept Hull GE §26.15 after independent price measurements, tested long-basket API, complete teaching, four shared figures and verified Book/portal rendering.

**Architecture:** An independent offline reference generator freezes exact moments, two-asset conditional quadrature and correlated terminal MC. The library uses moment matching into Black for positive baskets. Offline lesson JSON feeds four Plotly figures on both surfaces; notebook/report builds perform no simulation.

**Tech Stack:** Existing Python NumPy/SciPy/pytest, Plotly, Jupyter Book, Node Playwright. No new dependencies.

**Spec:** `johnhull/docs/superpowers/specs/2026-09-19-section-26-15-basket-design.md` (approved design), Hull GE pp.628–629.

## Global constraints

- Worktree `/home/kazumasa/.codex/worktrees/johnhull-basket-m7`, branch `codex/johnhull-basket-m7`, base `9b7a75c7`. Only edit johnhull. The user's other projects and original main remain intact.
- API accepts aligned numerical sequences, nonnegative weights, positive spots/strike/expiry, nonnegative volatilities, PSD symmetric correlation with diagonal 1. Reject nonfinite invalid data. Inputs and units follow the spec. No torch, no production dependencies.
- M1 and M2 are exact under constant correlated GBM. A lognormal basket price is an approximation except one-asset and proportional perfect-correlation anchors. Put-call parity holds to floating precision.
- No printed Hull price anchor exists for §26.15. Do not fabricate one. Reference generator never imports the new basket price code. MC errors are sampled; report standard errors and a declared price floor in relative-error summaries.
- Preserve current numbered sections outside §4.5. Book/portal build from saved artifacts. Historical validation JSON/screenshots remain untouched; new M7 recheck names for affected accepted sections.
- Python `/home/kazumasa/projects/.venv/bin/python`; `PYTHONPATH=$PWD/johnhull/hullkit/src:$PWD/johnhull/report` in worktree. Windows exec workdir `C:\Users\Kazumasa`, WSL calls use `wsl.exe --exec sh -lc` with escalation.
- Baseline before edits: `2515 passed, 6 skipped, 2 warnings` in 58.11 s. Run a fresh full suite after integration. Ledger accepted count changes only after acceptance evidence exists. Independent reviews required for numerical and final delivery.

## Task 1: M7a independent reference and requirements

**Files:** create `johnhull/scripts/build_basket_reference.py`, `johnhull/hullkit/tests/test_basket_reference.py`, `johnhull/docs/SECTION_26_15_REVIEW_2026-09-19.md`, `johnhull/docs/validation/section-26-15/{prices,numerical-check}.json`; update `docs/section_ledger.json`, `docs/SECTION_LEDGER.md`, `ROADMAP.md` as M7a `gaps_found` only.

**Interface:** `prices.json` has rows with named market, spots, weights, volatilities, dividends, correlation, r, T, K, kind, exact M1/M2, conditional price when n=2/nondegenerate, MC price, standard error and seed. Expose reference functions `moments_direct(...)`, `conditional_two_asset(...)`, `simulate(...)` in the script for later tests. Status record identifies sample sizes, tolerances and empirical error floor. Contract table uses requirement IDs BSK01–BSK06.

- [ ] Write reference tests before generator logic. Exact one-asset moment example `F=100*exp(.03)` and `M2=F**2*exp(.04)`; compare two-asset conditional quadrature against an independent deterministic special case, verify MC converges within four standard errors and put-call parity for identical random paths.
```python
def test_one_asset_exact_moments():
    from build_basket_reference import moments_direct
    m1, m2 = moments_direct([100.0], [1.0], .05, [.02], [.2], [[1.0]], 1.0)
    want = 100.0 * math.exp(.03)
    assert m1 == pytest.approx(want)
    assert m2 == pytest.approx(want * want * math.exp(.04))
```
- [ ] Run this one test first: expect import/function failure, then implement direct-loop moment calculation and verify GREEN.
- [ ] Add a two-asset conditional-integral test with a fixed literal or exact degenerate anchor; run RED, implement the single remaining Gaussian integral, run GREEN. Treat `|rho|=1` with an analytic anchor or skip conditional integral there; never silently divide by zero.
- [ ] Add fixed-seed correlated terminal MC with chunking, standard error, and a first-moment control variate; test its sampled payoff/SE against two-asset quadrature under at least two markets. Generate deterministic JSON for six varied two-asset markets×three strikes×call/put and two three-asset markets×three strikes×call/put, plus exact anchors. Include rho, yields, short/long maturity, high volatility and a negative rate.
- [ ] Compare approximate moment-match price (implemented *independently in this script*, not imported from hullkit) with every reference, state observed absolute/relative errors and a price floor. Do not label a <4SE discrepancy's sign established. Include a reproducibility check that regenerates byte-identical numerical content after excluding timestamp fields or use no timestamp.
- [ ] Read pp.628–629 and existing §4.5 to define BSK01 contract/units, BSK02 exact moments, BSK03 approximation versus MC, BSK04 correlation effect, BSK05 error/domain, BSK06 both-surface teaching. Update only this section's ledger row to `gaps_found`. Run focused tests, ruff and ledger check; commit assigned files.

## Task 2: Public pricing API

**Files:** modify `johnhull/hullkit/src/hullkit/exotics.py`, `johnhull/MODEL_INDEX.md`; create `johnhull/hullkit/tests/test_basket_pricing.py`.

**Interface:** `basket_moments(spots,weights,rate,dividends,volatilities,correlations,expiry)->(float,float)` and `basket_option_price(spots,weights,strike,rate,dividends,volatilities,correlations,expiry,kind="call")->float`. Reference data is an input to tests, never imported at runtime by pricing code.

- [ ] Write a failing import test plus real behavior tests for one-asset BSM equality, two-/three-asset direct moments and saved independent two-asset prices, call-put parity, a rho=1 proportional anchor and invalid matrix/length/weight/strike. Run RED before implementation.
```python
def test_single_asset_basket_is_bsm():
    got = exotics.basket_option_price([100.], [1.], 100., .05, [.02], [.2], [[1.]], 1.)
    assert got == pytest.approx(bsm.call_price(100., 100., .05, .2, 1., q=.02), abs=1e-11)
```
- [ ] Implement validation, exact moments and Black forward approximation with a stable zero matched-variance branch. Treat `kind="put"` directly, test parity. Use existing NumPy/SciPy; no new dependency. Ensure invalid matrices fail rather than being silently projected to PSD.
- [ ] Run focused tests, source docstring/index guard, ruff and self-review. Commit assigned files. Report each measured library-reference residual, especially tiny option prices where a percentage is unstable.

## Task 3: Four saved-data figures

**Files:** create `johnhull/scripts/build_basket_lesson_data.py`, `johnhull/hullkit/src/hullkit/_basket_lesson.py`, `johnhull/hullkit/tests/test_basket_lesson.py`, `johnhull/docs/validation/section-26-15/lesson-data.json`; update private-module MODEL_INDEX entry.

**Interface:** `_figures()` returns ordered keys `basket_payoff`, `basket_correlation`, `basket_comparison`, `basket_error`; each has `layout.meta.section="26.15"`, figure key and menu state. Traces have semantic `meta.role`. JSON pins exact source hashes of API, reference generator, frozen prices, numerical record and lesson generator. The plot builder rejects deleted, missing or stale mandatory hashes.

- [ ] Test required key list and figure values/menu traces before code; run RED. Payoff values use a literal two-asset terminal state; a nonzero weight and an out-of-the-money state must differ.
- [ ] Generate lesson JSON offline from frozen independent prices/moments. Correlation chart shows rho and both covariance/matched volatility; comparison shows approximation plus independent point and MC uncertainty; error chart marks a gap buried inside standard error without declaring its sign. Test independent semantics and source-hash missing/deleted negative cases.
- [ ] Ensure no runtime calls to conditional integration or MC in `_figures()`. Run tests/ruff, commit assigned files. Report exact menu states and data layout for delivery.

## Task 4: Teaching and two delivery surfaces

**Files:** modify vol10 builder and saved notebook, `report/report_builder/figures.py`, `report/assets/style.css`, `report/tests/test_report_build.py`, `release_manifest.json`, readmes; create `scripts/build_basket_browser_reference.py`, `scripts/verify_basket_lesson_browser.cjs`, `scripts/verify_basket_notebook.py`; generated section-26-15 browser/notebook record and screenshots.

- [ ] Add a failing registry test asserting four new figure keys and metadata, run RED; wire the four shared figures and make basket cards readable at 1000 and 1440 width, run GREEN.
- [ ] Expand §4.5 into six subsections without altering §4.4, variance swaps or later cells. Show payoff, exact M1/M2, Black approximation, correlation, MC reference and observed error/domain. Identify the CBOT delivery-option example as rainbow context, not a printed basket price example.
- [ ] Build/save vol10 outputs and check source cells outside §4.5 against base commit. Compare fresh deterministic text/MIME/output types and exact four saved Plotly data/layout against current builder; timing cells type only.
- [ ] Build Book and portal with no heavy solve. Browser verifier uses a separately generated reference set, checks payoff/moments/prices/error and every menu state at both widths/surfaces, math text/typesetting, chart layout, JS/network errors and one deliberate numeric mutation that must be rejected then restored. Capture four figures×two widths×two surfaces plus Book formula/example×two widths (18 images). Visually inspect 1000 width.
- [ ] Rerun existing six accepted sections' relevant browser and test checks on final builds; create new M7 recheck records, preserve old dated files. Run lint, semantic, notebook and release checks. Commit assigned source/delivery files, report results and limits.

## Controller integration and final gate

- [ ] Check each task's requirements and independent review; fix load-bearing findings. Compare current main and branch; keep other projects untouched.
- [ ] Verify the original source PDF, 1-asset/degenerate anchors, price error versus MC uncertainty, signed call-put parity and displayed chart values. Ensure original M7a reference files remain frozen unless a measured reference defect is independently demonstrated.
- [ ] Write `docs/SECTION_26_15_ACCEPTANCE_2026-09-19.md` with BSK01–BSK06 mapping, actual measurements, figure/browser scopes, limits and review result. Update ledger to `accepted` only if complete; regenerate summary and artifact hashes. Update ROADMAP, VALIDATION and vol10 PROGRESS as current status.
- [ ] Run a fresh full `pytest johnhull/hullkit/tests johnhull/report/tests`, `ruff check` on changed Python, `verify_section_ledger.py --check-artifacts`, `verify_release.py`, `git diff --check`. Get an independent final review, resolve substantive findings, then verify branch again. A green test suite alone does not establish learning coverage.
- [ ] Finish by integrating reviewed changes into main only after its current state and user changes are checked. External push requires the exact prior user authorization to apply; never force-push or overwrite unrelated work.
