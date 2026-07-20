# johnhull Model-Library Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make johnhull + deep_hedge_price a searchable model library: 100% public-API docstrings, a MODEL_INDEX.md catalog, an agent-facing CLAUDE.md, and freshness tests that keep all three honest.

**Architecture:** Docstring completion is enforced by per-module parametrized AST tests (write test → fill → green). MODEL_INDEX.md is a hand-written English catalog whose completeness (every module listed) and correctness (every `pkg.module:symbol` reference resolves via importlib) are enforced by two test files — the hullkit-side test stays torch-free, the deep_hedge_price-side test owns torch-dependent references.

**Tech Stack:** Python 3.12, pytest, `ast`/`importlib`/`re` (stdlib only), uv workspace, ruff.

## Global Constraints

- Branch: `codex/johnhull-beyond-hull-g8` (continue on it; do NOT switch).
- Source-module diffs are **docstring insertions only** — no logic, signature, or import changes.
- `hullkit` stays torch-free: its tests must not import torch or `deep_hedge_price`.
- MODEL_INDEX.md is English; johnhull/CLAUDE.md is Japanese prose with English identifiers.
- All pytest/uv commands run from repo root `/home/kazumasa/projects`.
- Reference notation in MODEL_INDEX.md: backticked `` `package.module:symbol` `` (regex-extracted by tests).
- Every commit message ends with:
  `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_012iwnv6G8KbG523M1gRCEbZ`
- Spec: `docs/superpowers/specs/2026-07-19-johnhull-model-library-index-design.md`.

---

### Task 1: hullkit docstring guard + fill (58 missing in 14 modules)

**Files:**
- Test: `johnhull/hullkit/tests/test_docstrings.py` (create)
- Modify (docstrings only): `johnhull/hullkit/src/hullkit/{amm,bsm,carbon,liquidation,perpetuals,ppa,rfr,spx_vix,surrogate_data,surrogate_validation,vol_surface,weather,zero_dte}.py`

**Interfaces:**
- Produces: `_undocumented(path) -> list[str]` pattern reused verbatim in Task 3's test.

- [ ] **Step 1: Write the failing test**

```python
"""Guard: every public hullkit API carries a docstring (model-library contract)."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src" / "hullkit"
MODULES = sorted(p for p in SRC.glob("*.py") if p.name != "__init__.py")


def _undocumented(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    missing: list[str] = []
    if not ast.get_docstring(tree):
        missing.append("<module>")

    def visit(body: list[ast.stmt], prefix: str) -> None:
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if node.name.startswith("_"):
                    continue
                if not ast.get_docstring(node):
                    missing.append(prefix + node.name)
                if isinstance(node, ast.ClassDef):
                    visit(node.body, prefix + node.name + ".")

    visit(tree.body, "")
    return missing


@pytest.mark.parametrize("path", MODULES, ids=lambda p: p.stem)
def test_public_api_documented(path: Path) -> None:
    missing = _undocumented(path)
    assert not missing, f"{path.name}: undocumented public API: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_docstrings.py`
Expected: 14 failed (amm, bsm, carbon, liquidation, perpetuals, ppa, rfr, spx_vix, surrogate_data, surrogate_validation, vol_surface, weather, zero_dte), 27 passed. Failure messages list the exact undocumented names.

- [ ] **Step 3: Fill the 58 docstrings**

For each failing module, read the module, then add a one-line imperative docstring to each listed symbol. Add Args/Returns only when the signature is not self-explanatory. Name the model/theory when the symbol implements one. Style example (match surrounding code):

```python
def funding_rate(mark: float, index: float, clamp: float = 0.0005) -> float:
    """Clamped premium-minus-index funding rate per interval (linear perpetual)."""
```

```python
class HaganNormalSmile:
    """Bachelier-vol SABR smile via Hagan et al. (2002) normal expansion."""
```

Do not touch any executable line.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_docstrings.py`
Expected: 40 passed.

- [ ] **Step 5: Full hullkit suite + ruff, then commit**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests`
Expected: 334 passed (294 + 40).
Run: `uv run --no-sync ruff check johnhull/hullkit && uv run --no-sync ruff format --check johnhull/hullkit`
Expected: clean.

```bash
git add johnhull/hullkit
git commit -m "docs(hullkit): complete public-API docstrings with guard test"
```

---

### Task 2: deep_hedge_price docstrings, group 1 — hedging core (45 in 10 modules)

**Files:**
- Modify (docstrings only): `deep_hedge_price/src/deep_hedge_price/{arbitrage,config,experiments,feature_diagnostics,greeks,hedge_capstone,plotting,policy,risks,training}.py`

**Interfaces:**
- Consumes: docstring style from Task 1 Step 3.
- Produces: group-1 modules at zero missing, verified by audit snippet below.

- [ ] **Step 1: Confirm the starting gap**

Run (from repo root):

```bash
python3 - <<'EOF'
import ast, pathlib
GROUP = {"arbitrage","config","experiments","feature_diagnostics","greeks",
         "hedge_capstone","plotting","policy","risks","training"}
src = pathlib.Path("deep_hedge_price/src/deep_hedge_price")
total = 0
for f in sorted(src.glob("*.py")):
    if f.stem not in GROUP: continue
    tree = ast.parse(f.read_text())
    def visit(body, prefix=""):
        global total
        for n in body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and not n.name.startswith("_"):
                if not ast.get_docstring(n):
                    total += 1; print(f.stem, prefix+n.name)
                if isinstance(n, ast.ClassDef): visit(n.body, n.name+".")
    visit(tree.body)
print("missing:", total)
EOF
```

Expected: `missing: 45` with the symbol list (config 20, plotting 12, policy 3, feature_diagnostics 3, experiments 2, arbitrage 1, greeks 1, hedge_capstone 1, risks 1, training 1).

- [ ] **Step 2: Fill all 45, rerun audit**

Same style rules as Task 1 Step 3. Rerun the Step 1 snippet.
Expected: `missing: 0`.

- [ ] **Step 3: Suite + ruff, then commit**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests`
Expected: 88 passed.
Run: `uv run --no-sync ruff check deep_hedge_price && uv run --no-sync ruff format --check deep_hedge_price`
Expected: clean.

```bash
git add deep_hedge_price
git commit -m "docs(deep_hedge_price): docstrings for hedging-core modules (group 1)"
```

---

### Task 3: deep_hedge_price docstrings, group 2 + guard test (59 in 16 modules)

**Files:**
- Test: `deep_hedge_price/tests/test_docstrings.py` (create)
- Modify (docstrings only): `deep_hedge_price/src/deep_hedge_price/{pricing_ablation,pricing_artifacts,pricing_calibration,pricing_config,pricing_evaluation,pricing_losses,pricing_plotting,pricing_policy,pricing_report,pricing_training,research_models,surface_data,surface_hedge_pipeline,volatility_data,walk_forward,risks}.py` (risks only if Task 2 left strays)

**Interfaces:**
- Consumes: `_undocumented` implementation from Task 1 Step 1 — copy it verbatim, change only `SRC`:

```python
SRC = Path(__file__).resolve().parents[1] / "src" / "deep_hedge_price"
```

- [ ] **Step 1: Create `deep_hedge_price/tests/test_docstrings.py`** — identical to Task 1 Step 1 except the `SRC` line above and the module docstring first line: `"""Guard: every public deep_hedge_price API carries a docstring."""`

- [ ] **Step 2: Run test to verify it fails on exactly group 2**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests/test_docstrings.py`
Expected: 15 failed (pricing_ablation, pricing_artifacts, pricing_calibration, pricing_config, pricing_evaluation, pricing_losses, pricing_plotting, pricing_policy, pricing_report, pricing_training, research_models, surface_data, surface_hedge_pipeline, volatility_data, walk_forward), 23 passed.

- [ ] **Step 3: Fill the 59 docstrings** — same style rules; torch `forward` overrides get one-liners like `"""Score the lag window and return the variance forecast."""`

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests/test_docstrings.py`
Expected: 38 passed.

- [ ] **Step 5: Full suite + ruff, then commit**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests`
Expected: 126 passed (88 + 38).
Run: `uv run --no-sync ruff check deep_hedge_price && uv run --no-sync ruff format --check deep_hedge_price`
Expected: clean.

```bash
git add deep_hedge_price
git commit -m "docs(deep_hedge_price): complete public-API docstrings with guard test"
```

---

### Task 4: MODEL_INDEX.md with full hullkit coverage + hullkit index test

**Files:**
- Create: `johnhull/MODEL_INDEX.md`
- Test: `johnhull/hullkit/tests/test_model_index.py` (create)

**Interfaces:**
- Produces: MODEL_INDEX.md with all 15 section headers (spec §2.1) and every `hullkit.*` module referenced; the `` `package.module:symbol` `` notation consumed by both index tests; section skeleton that Task 5 extends with `deep_hedge_price.*` rows.

- [ ] **Step 1: Write the failing test**

```python
"""Guard: MODEL_INDEX.md lists every hullkit module and its references resolve."""
from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

INDEX = Path(__file__).resolve().parents[2] / "MODEL_INDEX.md"
SRC = Path(__file__).resolve().parents[1] / "src" / "hullkit"
MODULES = sorted(p.stem for p in SRC.glob("*.py") if p.name != "__init__.py")
TEXT = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
REFS = sorted(set(re.findall(r"`(hullkit\.[A-Za-z0-9_.]+):([A-Za-z0-9_]+)`", TEXT)))


def test_index_exists() -> None:
    assert INDEX.exists(), "johnhull/MODEL_INDEX.md is missing"


@pytest.mark.parametrize("module", MODULES)
def test_module_listed(module: str) -> None:
    assert f"hullkit.{module}" in TEXT, f"hullkit.{module} missing from MODEL_INDEX.md"


@pytest.mark.parametrize("ref", REFS, ids=lambda r: f"{r[0]}:{r[1]}")
def test_reference_resolves(ref: tuple[str, str]) -> None:
    module, symbol = ref
    obj = importlib.import_module(module)
    assert hasattr(obj, symbol), f"{module}:{symbol} does not resolve"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_model_index.py`
Expected: `test_index_exists` fails, all 40 `test_module_listed` cases fail.

- [ ] **Step 3: Write `johnhull/MODEL_INDEX.md`**

Header block (verbatim):

```markdown
# MODEL_INDEX — johnhull model library

How to use this index (for agents):

1. Search this file first for a model, method, or market term.
2. `package.module:symbol` names an implementation; open it with
   `johnhull/hullkit/src/hullkit/<module>.py` or
   `deep_hedge_price/src/deep_hedge_price/<module>.py`.
3. Tests are relative to each package's `tests/` directory; notebooks are
   `johnhull/volumes/<vol>/`. Companion docs: `ROADMAP.md` (volume <-> Hull
   chapters), `release_manifest.json` (vol 18-25 wiring),
   `VALIDATION.md` (what PASS does and does not mean).
4. Freshness is test-enforced: every module below must stay listed
   (`test_model_index.py` in both packages).
```

Then the 15 sections from spec §2.1 with one table each, columns:
`| Model | Theory | Implementation | Tests | Notebook | Validation |`

Fill every hullkit module into its home section (dhp rows come in Task 5):
sections 1–7 host the classic 25 modules (bsm, trees, mc, payoffs, hedging,
volatility, heston, sabr, sabr_normal, fourier, sde, fd, fd_advanced,
mc_advanced, aad, rates, swaps, ir_options, rfr, rfr_options, risk, credit,
xva, copula, exotics); section 8 hosts surrogate_data, surrogate_validation;
section 9 hosts vol_surface, frontier_reference; section 11 hosts spx_vix;
section 12 hosts zero_dte; section 13 hosts amm, liquidation, perpetuals;
section 14 hosts carbon, weather, ppa; section 15 hosts nbplot, plotly_viz,
teaching as one-line role entries. Multiple rows per module where it
implements several named models. Worked example rows (copy style, not
content, for the rest):

```markdown
| Black-Scholes-Merton European pricing | Hull 11e ch.15 | `hullkit.bsm:bs_price`, `hullkit.bsm:bs_greeks` | `test_bsm.py` | vol 02, legacy ch.15 | Greeks pinned to Hull examples; put-call parity asserted |
| SABR lognormal smile | Hagan et al. (2002); Hull 11e ch.20 | `hullkit.sabr:hagan_lognormal_vol` | `test_sabr.py` | vol 05, 23 | Hagan limit checks; wing/negative-rate caveats in vol 23 |
| Perpetual funding cash flows | Kim & Park (2025), arXiv:2506.08573 | `hullkit.perpetuals:funding_cashflow` | `test_perpetuals.py` | vol 24 | conservation identities < 1e-12 |
```

Theory column: reuse the verified citation links/names already recorded in
`docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-options.md` §8; for
textbook material cite `Hull 11e ch.N` (GE edition). Symbol names MUST be
copied from each module's `__all__`/source, never guessed — the resolution
test rejects typos but not wrong-but-existing symbols, so copy carefully.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_model_index.py`
Expected: all pass (1 + 40 + ~60-80 resolution cases).

- [ ] **Step 5: Commit**

```bash
git add johnhull/MODEL_INDEX.md johnhull/hullkit/tests/test_model_index.py
git commit -m "docs(johnhull): MODEL_INDEX catalog with hullkit coverage guard"
```

---

### Task 5: MODEL_INDEX deep_hedge_price coverage + cross-project pointers + dhp index test

**Files:**
- Modify: `johnhull/MODEL_INDEX.md` (extend sections 8, 9, 10, 15; append cross-project section)
- Test: `deep_hedge_price/tests/test_model_index.py` (create)

**Interfaces:**
- Consumes: MODEL_INDEX.md section skeleton and reference notation from Task 4.

- [ ] **Step 1: Write the failing test** — copy Task 4 Step 1 verbatim with three changes:

```python
INDEX = Path(__file__).resolve().parents[2] / "johnhull" / "MODEL_INDEX.md"
SRC = Path(__file__).resolve().parents[1] / "src" / "deep_hedge_price"
REFS = sorted(set(re.findall(r"`(deep_hedge_price\.[A-Za-z0-9_.]+):([A-Za-z0-9_]+)`", TEXT)))
```

and `MODULES`/messages referencing `deep_hedge_price.` instead of `hullkit.`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests/test_model_index.py`
Expected: 38 `test_module_listed` failures.

- [ ] **Step 3: Extend MODEL_INDEX.md**

- Section 8 (ML surrogates & DML): pricing_data, pricing_policy, pricing_training, pricing_losses (differential/Sobolev loss), pricing_evaluation, pricing_ablation, pricing_residuals, greeks, arbitrage, research_models.
- Section 9 (calibration & surfaces): pricing_calibration, pricing_benchmark, frontier_reference, surface_data.
- Section 10 (forecasting & hedging): volatility_data, walk_forward (HAR/HARNet/TCN/LSTM/transformer challengers), feature_diagnostics, surface_hedge_pipeline, hedge_capstone, policy, training, baselines, simulation, pnl, black_scholes, evaluation, risks, experiments.
- Section 15: cli, config, pricing_config, notebook, pricing_notebook, plotting, pricing_plotting, report, pricing_report, pricing_artifacts as one-line role entries.
- Append final section (verbatim heading): `## Cross-project pointers (canonical implementations elsewhere)` with rows for exact rBergomi / hybrid fBM / Hawkes (`~/projects/rough_volatility`), Almgren-Chriss / Obizhaeva-Wang / reactive LOB / PPO execution (`~/projects/optimal_execution`), portfolio construction / backtesting / signals (`~/projects/quantkit`), plain-text paths only (no `module:symbol` notation, so the resolution tests ignore them).

- [ ] **Step 4: Run both index tests**

Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests/test_model_index.py && uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests/test_model_index.py`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add johnhull/MODEL_INDEX.md deep_hedge_price/tests/test_model_index.py
git commit -m "docs(johnhull): index deep_hedge_price models and cross-project pointers"
```

---

### Task 6: johnhull/CLAUDE.md

**Files:**
- Create: `johnhull/CLAUDE.md`

- [ ] **Step 1: Write `johnhull/CLAUDE.md`** — Japanese prose, English identifiers, three sections from spec §2.2:

1. ナビゲーション: モデル探索は `MODEL_INDEX.md` が唯一の入口 → 巻↔章対応は `ROADMAP.md` → vol 18–25 の成果物配線は `release_manifest.json` → 検証範囲の意味は `VALIDATION.md`（PASS = integration のみ、performance 承認ではない）。
2. 実行・検証コマンド（repo root から）: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests` / `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests` / `make hull-report` / `make hull-book` / `make hull-artifacts-check` / `make hull-notebooks-check` / `make hull-release-check`。
3. 規約と落とし穴: hullkit は torch-free（torch 依存は deep_hedge_price 側）; notebook は artifact-only 実行（build 中の学習・DL・GPU 検出禁止）; artifact は fingerprint 付き JSON+NPZ で acceptance は `johnhull/scripts/frontier_acceptance.py` が再計算; PDF は 11e Global Edition（節・図番号が US 版とズレる）; 深掘り巻の plotly は mimetype-only 出力（静的 book に非表示、対話面はポータル）; build スクリプトは決定的 cell-id・`build_*_notebook.py` は ruff exclude; docstring/index は guard test（`test_docstrings.py` / `test_model_index.py`）が強制。

- [ ] **Step 2: Verify content accuracy** — every command listed must be run once (or have been run in Tasks 1–5) and match its Makefile/pyproject definition.

- [ ] **Step 3: Commit**

```bash
git add johnhull/CLAUDE.md
git commit -m "docs(johnhull): agent guide (CLAUDE.md) for the model library"
```

---

### Task 7: Full gates

**Files:** none (verification only; fix fallout inline if any)

- [ ] **Step 1: Scoped suites**

Run: `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests`
Expected: 334+ passed (294 + 40 docstring + index cases).
Run: `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests`
Expected: 126+ passed.

- [ ] **Step 2: Lint**

Run: `uv run --no-sync ruff check johnhull deep_hedge_price && uv run --no-sync ruff format --check johnhull/hullkit deep_hedge_price`
Expected: clean (notebook build scripts are excluded by repo config).

- [ ] **Step 3: Release contract unaffected**

Run: `make hull-release-check`
Expected: `[PASS] johnhull A5--A8 release contract`.

- [ ] **Step 4: Docstring numbers re-audit** — rerun the audit snippet from Task 2 Step 1 without the GROUP filter over both packages.
Expected: `missing: 0` for both.

- [ ] **Step 5: Commit only if fixes were needed; otherwise nothing to commit.**

## Self-Review Notes

- Spec coverage: §2.1→Task 4/5, §2.2→Task 6, §2.3→Tasks 1–3, §2.4→Tasks 1, 3, 4, 5, §4→Task 7. No gaps.
- Counts (58/45/59, expected test totals) measured on 2026-07-19; if drift occurs, trust the guard tests over the numbers.
- Type consistency: `_undocumented` and the index-test regex are defined once and copied with stated diffs only.
