# Japanese Report Localization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit `rough_volatility_report_ja.html` beside `rough_volatility_report_en.html` from the same figures/data, differing only in prose language, by porting the `optimal_execution` i18n layer.

**Architecture:** Add a flat-JSON locale layer (`locales/{en,ja}.json`) plus a small `i18n.py` `Translator` (copied from `optimal_execution`). Thread a `locale` parameter through `build_standalone_report`, replacing hardcoded prose with translator lookups for the translated surface only (headings, callouts, captions, page chrome). Keep equations, axis titles, metric labels, and math-derivation paragraphs in English. A language-neutral SHA-256 fingerprint embedded in both HTML files guarantees numeric parity.

**Tech Stack:** Python 3.11+, plotly, pandas, pytest. No new dependencies (`json`, `hashlib`, `pathlib` are stdlib).

## Global Constraints

- Python floor: 3.11 (`from __future__ import annotations` already used project-wide).
- No new third-party dependencies.
- `SUPPORTED_LOCALES = ("en", "ja")`; `en` is the reference locale.
- `en.json` and `ja.json` MUST always have identical key sets (`validate_locales` enforces this) — every task that adds a key adds it to BOTH files.
- Retained-English surface (NEVER translated): LaTeX/MathJax, `update_xaxes/yaxes(title=...)` axis titles, `_metric_cards` labels, `_configuration_table`/`_validation_table` headers, dense math-derivation sentences inside callouts.
- Reports remain fully offline/self-contained: no `https?://` in `(src|href)` attributes (existing `tests/test_report.py` check must keep passing for both locales).
- `Section` fields are `.anchor` (str, e.g. `"iv-smiles"`), `.title` (str), `.figure_key` (str | None). `SECTIONS` has exactly 26 entries. Narrative dict keys equal `section.anchor`.
- `build_standalone_report(config, root, manifest, *, output_path=None)` is the current signature; `manifest` is the artifact-path dict. `config.fingerprint()` and `config.output.reports_dir` exist.
- Commit after every task. Branch: `feat/rough-vol-ja-report` (already checked out).
- Run tests with: `uv run --no-sync pytest rough_volatility/tests -q` from `/home/kazumasa/projects`.

---

## File Structure

- Create `rough_volatility/src/rough_volatility/i18n.py` — locale loading + `Translator`.
- Create `rough_volatility/locales/en.json`, `rough_volatility/locales/ja.json` — flat string maps.
- Create `rough_volatility/tests/test_i18n.py` — locale parity + translator behavior.
- Create `rough_volatility/scripts/build_reports.py` — thin `--locale all` entry (mirrors `optimal_execution`).
- Modify `rough_volatility/src/rough_volatility/report.py` — thread `locale`, replace translated prose, add fingerprint + `build_reports`.
- Modify `rough_volatility/src/rough_volatility/cli.py` — `--locale {en,ja,all}` on the `report` command.
- Modify `rough_volatility/tests/test_report.py` — bilingual parity test; keep offline check for both.
- `notebook.py` — UNCHANGED (single-language source of `SECTIONS`).

---

### Task 1: i18n layer + locale scaffold (page chrome)

**Files:**
- Create: `rough_volatility/src/rough_volatility/i18n.py`
- Create: `rough_volatility/locales/en.json`, `rough_volatility/locales/ja.json`
- Test: `rough_volatility/tests/test_i18n.py`

**Interfaces:**
- Produces: `load_locale(locale: str) -> dict[str, str]`, `validate_locales() -> None`, `Translator(locale)` with `__call__(key, **values) -> str` (does `str.format(**values)`), and module constants `SUPPORTED_LOCALES = ("en", "ja")`, `REQUIRED_KEYS: set[str]`.

- [ ] **Step 1: Write the failing test** — `rough_volatility/tests/test_i18n.py`

```python
from __future__ import annotations

from rough_volatility.i18n import REQUIRED_KEYS, Translator, load_locale, validate_locales


def test_locale_key_sets_and_required_content_match() -> None:
    validate_locales()
    en = load_locale("en")
    ja = load_locale("ja")
    assert set(en) == set(ja)
    assert REQUIRED_KEYS <= set(en)


def test_translator_formats_placeholders() -> None:
    ja = Translator("ja")
    text = ja("report_subtitle", seed=1210, fingerprint="abcd1234")
    assert "1210" in text
    assert "abcd1234" in text


def test_japanese_chrome_is_actually_japanese() -> None:
    ja = load_locale("ja")
    joined = " ".join(ja.values())
    assert "ラフ" in joined  # "rough" appears in the JA title/subtitle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_i18n.py -q`
Expected: FAIL — `ModuleNotFoundError: rough_volatility.i18n`.

- [ ] **Step 3: Write `i18n.py`** (port of `optimal_execution/i18n.py`; `LOCALE_DIR` resolved from package location since there is no `provenance` module)

```python
"""Structured English/Japanese report localization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCALE_DIR = Path(__file__).resolve().parents[2] / "locales"
SUPPORTED_LOCALES = ("en", "ja")

REQUIRED_KEYS = {
    "document_title",
    "brand",
    "report_title",
    "report_subtitle",
    "badge",
    "footer",
}


def load_locale(locale: str) -> dict[str, str]:
    if locale not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale {locale!r}; choose from {SUPPORTED_LOCALES}")
    path = LOCALE_DIR / f"{locale}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in payload.items()
    ):
        raise ValueError(f"locale file must be a flat string mapping: {path}")
    missing = REQUIRED_KEYS - payload.keys()
    if missing:
        raise KeyError(f"locale {locale} is missing keys: {sorted(missing)}")
    return payload


def validate_locales() -> None:
    payloads = {locale: load_locale(locale) for locale in SUPPORTED_LOCALES}
    reference = set(payloads[SUPPORTED_LOCALES[0]])
    for locale, payload in payloads.items():
        keys = set(payload)
        if keys != reference:
            missing = sorted(reference - keys)
            extra = sorted(keys - reference)
            raise ValueError(f"locale key mismatch for {locale}: missing={missing}, extra={extra}")


class Translator:
    def __init__(self, locale: str):
        self.locale = locale
        self.messages = load_locale(locale)

    def __call__(self, key: str, **values: Any) -> str:
        try:
            text = self.messages[key]
        except KeyError as exc:
            raise KeyError(f"missing translation {key!r} for {self.locale}") from exc
        return text.format(**values) if values else text
```

- [ ] **Step 4: Write `locales/en.json`** (page chrome, English verbatim from current `report.py`)

```json
{
  "document_title": "Rough Volatility Visual Lab — Technical Report",
  "brand": "Synthetic research lab",
  "report_title": "Rough Volatility Visual Lab",
  "report_subtitle": "Technical report · synthetic data only · seed {seed} · configuration {fingerprint}",
  "badge": "SELF-CONTAINED · OFFLINE · {profile}",
  "footer": "Generated locally from saved, provenance-stamped experiment artifacts. No market data, remote scripts, or external services are used."
}
```

- [ ] **Step 5: Write `locales/ja.json`** (Japanese page chrome; keep `{placeholders}`; keep "OFFLINE" badge tokens recognizable)

```json
{
  "document_title": "ラフボラティリティ・ビジュアルラボ — テクニカルレポート",
  "brand": "合成データ研究ラボ",
  "report_title": "ラフボラティリティ・ビジュアルラボ",
  "report_subtitle": "テクニカルレポート · 合成データのみ · seed {seed} · 設定 {fingerprint}",
  "badge": "自己完結 · オフライン · {profile}",
  "footer": "保存済みの来歴付き実験アーティファクトからローカル生成。市場データ・外部スクリプト・外部サービスは一切使用していません。"
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests/test_i18n.py -q`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit**

```bash
git add rough_volatility/src/rough_volatility/i18n.py rough_volatility/locales/en.json rough_volatility/locales/ja.json rough_volatility/tests/test_i18n.py
git commit -m "feat(rough_volatility): add i18n layer and page-chrome locales"
```

---

### Task 2: Thread `locale` through the report + localize page chrome

**Files:**
- Modify: `rough_volatility/src/rough_volatility/report.py` (`build_standalone_report`, ~885-940)
- Test: `rough_volatility/tests/test_report.py`

**Interfaces:**
- Consumes: `Translator`, `load_locale` from Task 1.
- Produces: `build_standalone_report(config, root, manifest, *, locale="en", output_path=None) -> Path` writing `rough_volatility_report_{locale}.html`, with `<html lang="{locale}">`.

- [ ] **Step 1: Write the failing test** — add to `rough_volatility/tests/test_report.py`

```python
def test_locale_controls_language_and_filename(tmp_path):
    config = load_config(Path("configs/quick.yaml"))  # match existing fixture style
    manifest = ...  # reuse the module's existing manifest fixture/helper
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja")
    assert ja.name == "rough_volatility_report_ja.html"
    text = ja.read_text(encoding="utf-8")
    assert '<html lang="ja">' in text
    assert "ラフボラティリティ・ビジュアルラボ" in text
```

> Implementer note: use the SAME config/manifest construction the existing `test_report_is_self_contained_interactive_and_complete` uses (read that test first and mirror its fixture wiring; do not invent new fixtures).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py::test_locale_controls_language_and_filename -q`
Expected: FAIL — `build_standalone_report() got an unexpected keyword argument 'locale'`.

- [ ] **Step 3: Modify `build_standalone_report`** — add import and thread `locale`

At the top of `report.py`, add:

```python
from rough_volatility.i18n import Translator
```

Change the signature (line ~885) to:

```python
def build_standalone_report(
    config: ProjectConfig,
    root: str | Path,
    manifest: dict[str, Path],
    *,
    locale: str = "en",
    output_path: str | Path | None = None,
) -> Path:
```

Immediately after `config.validate()`, add:

```python
    t = Translator(locale)
```

Replace the default output path (line ~932-936) with:

```python
    output = (
        Path(output_path)
        if output_path is not None
        else Path(root).resolve()
        / config.output.reports_dir
        / f"rough_volatility_report_{locale}.html"
    )
```

Replace the document f-string (line ~938) chrome with translator lookups. New `document`:

```python
    document = (
        f'<!doctype html><html lang="{locale}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="color-scheme" content="light">'
        f"<title>{html.escape(t('document_title'))}</title><style>{css}</style></head>"
        '<body><div class="layout"><nav class="sidebar" aria-label="Report sections">'
        f'<div class="brand">{html.escape(t("brand"))}</div>'
        f'<h1>{html.escape(t("report_title"))}</h1><ol>{toc}</ol></nav>'
        '<main class="content"><header>'
        f'<div class="badge">{html.escape(t("badge", profile=config.profile.upper()))}</div>'
        f'<h1>{html.escape(t("report_title"))}</h1>'
        f'<p>{html.escape(t("report_subtitle", seed=config.seed, fingerprint=config.fingerprint()))}</p>'
        f'</header>{"".join(sections_html)}'
        f'<div class="footer">{html.escape(t("footer"))}</div>'
        "</main></div></body></html>"
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py -q`
Expected: PASS (new test + existing offline test; existing test reads the returned path so the filename change is transparent).

- [ ] **Step 5: Commit**

```bash
git add rough_volatility/src/rough_volatility/report.py rough_volatility/tests/test_report.py
git commit -m "feat(rough_volatility): thread locale through report and localize page chrome"
```

---

### Task 3: Localize the 26 section headings

**Files:**
- Modify: `rough_volatility/locales/en.json`, `rough_volatility/locales/ja.json`, `rough_volatility/src/rough_volatility/i18n.py` (`REQUIRED_KEYS`), `rough_volatility/src/rough_volatility/report.py`
- Test: `rough_volatility/tests/test_report.py`

**Interfaces:**
- Produces: locale keys `section.<anchor>` for all 26 anchors; report renders headings via `t(f"section.{section.anchor}")`.

- [ ] **Step 1: Write the failing test** — add to `test_report.py`

```python
def test_section_headings_are_localized(tmp_path):
    config = load_config(Path("configs/quick.yaml"))
    manifest = ...  # existing fixture wiring
    en = build_standalone_report(config, tmp_path, manifest, locale="en").read_text("utf-8")
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text("utf-8")
    assert "From rough paths to option skew and order flow" in en
    assert "ラフパスからオプション・スキューと注文フローへ" in ja
    assert "From rough paths to option skew and order flow" not in ja
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py::test_section_headings_are_localized -q`
Expected: FAIL — JA heading absent (headings still English via `section.title`).

- [ ] **Step 3: Add the 26 `section.<anchor>` keys** to `en.json` (verbatim from `SECTIONS` titles in `notebook.py`) and `ja.json` (translated). The 26 anchors are: `executive-summary, conceptual-map, mathematical-definitions, configuration, fbm-path-comparison, local-zoom, fgn-increments, increment-acf, structure-functions, hurst-recovery, estimator-bias, ou-versus-fou, rough-bergomi-paths, heston-comparison, terminal-distributions, iv-smiles, iv-surface, atm-skew-term, skew-scaling, hawkes-events, order-flow-price, volatility-proxy, noise-bias, establishes, does-not-establish, limitations-next-steps`.

English values are the exact `Section.title` strings (read them from `notebook.py`). Japanese translations follow the hybrid policy: translate prose, keep model names (`Almgren–Chriss`, `Heston`, `rBergomi`, `Hawkes`, `OU/fOU`) and math symbols (`H`, `β`) as-is. Worked examples (establish the tone; produce the rest in the same register):

```json
  "section.executive-summary": "Technical summary",            // EN
  "section.conceptual-map": "From rough paths to option skew and order flow",
  "section.iv-smiles": "Smile shape varies jointly with model and maturity",
```
```json
  "section.executive-summary": "テクニカル・サマリー",           // JA
  "section.conceptual-map": "ラフパスからオプション・スキューと注文フローへ",
  "section.iv-smiles": "スマイル形状はモデルと満期に応じて共に変化する",
```

- [ ] **Step 4: Add all 26 keys to `REQUIRED_KEYS`** in `i18n.py`:

```python
    *(f"section.{anchor}" for anchor in _SECTION_ANCHORS),
```
where `_SECTION_ANCHORS` is a module-level tuple listing the 26 anchors above. (Keep it a literal tuple to avoid importing `report`/`notebook` into `i18n`.)

- [ ] **Step 5: Localize headings in `report.py`** — in `build_standalone_report`, replace `html.escape(section.title)` in BOTH the `toc` comprehension (line ~903) and the section `<h2>` (line ~917) with `html.escape(t(f"section.{section.anchor}"))`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py rough_volatility/tests/test_i18n.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rough_volatility/locales/*.json rough_volatility/src/rough_volatility/i18n.py rough_volatility/src/rough_volatility/report.py rough_volatility/tests/test_report.py
git commit -m "feat(rough_volatility): localize section headings"
```

---

### Task 4: Localize the 25 narrative callouts

**Files:**
- Modify: `rough_volatility/locales/*.json`, `i18n.py` (`REQUIRED_KEYS`), `report.py` (`_narratives`)
- Test: `rough_volatility/tests/test_report.py`

**Interfaces:**
- Produces: locale keys `callout.<anchor>` for the 25 `_narratives` entries; `_narratives(config, frames, t)` returns `{anchor: t(f"callout.{anchor}", **values)}`.

- [ ] **Step 1: Write the failing test**

```python
def test_callouts_are_localized_and_interpolated(tmp_path):
    config = load_config(Path("configs/quick.yaml"))
    manifest = ...  # existing fixture wiring
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text("utf-8")
    assert "合成ラボは市場データを用いずに" in ja       # executive-summary callout prose
    assert f"β={...:.3f}".split("=")[0] in ja or "β=" in ja  # interpolated skew value survives
    assert "H changes path regularity" not in ja       # EN callout replaced
```

> Implementer note: assert on a stable JA substring you actually put in `ja.json`, and assert the interpolated numeric (e.g. the `β=` value) still appears.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py::test_callouts_are_localized_and_interpolated -q`
Expected: FAIL — English callouts still present.

- [ ] **Step 3: Move the 25 callout strings into locales.** Copy each current value from `_narratives` (lines 836-868) verbatim into `en.json` under `callout.<anchor>`. Two entries are interpolated (`executive-summary`) — replace the f-string parts with named placeholders:

`en.json`:
```json
  "callout.executive-summary": "<p><strong>The synthetic lab reproduces the intended rough-volatility signatures without using market data.</strong> For H={h:g}, the fitted ATM-skew exponent is β={beta:.3f} versus the finite-asymptotic reference H−1/2={h_minus_half:.2f}. The exact-grid Volterra construction passes forward-variance and spot-martingale checks, while common random numbers make the Heston comparison interpretable.</p><p><strong>The microstructure result is diagnostic, not identifying.</strong> Near-critical Hawkes flow creates clustered activity and a rough-looking realized-variance proxy, but the noise experiment shows that estimated H changes materially with sampling and preprocessing.</p>"
```

The remaining 24 callouts are static strings copied verbatim (keys `callout.conceptual-map` … `callout.limitations-next-steps`).

`ja.json` provides the Japanese for all 25. Policy: translate narrative sentences; keep math-derivation clauses, symbols (`H`, `β`, `ξ₀(t)`, `T^(H−1/2)`, `E[V(t)]`), inequalities (`H&lt;1/2`), and model names in English/symbolic form; keep the `<p>/<strong>/<ul>/<ol>/<div class="flow">` HTML structure and all `{placeholders}` unchanged. Worked example (`callout.executive-summary`, JA):
```json
  "callout.executive-summary": "<p><strong>合成ラボは市場データを用いずに、狙ったラフボラティリティの特徴を再現する。</strong> H={h:g} のとき、当てはめた ATM スキュー指数は β={beta:.3f} で、有限漸近の参照値 H−1/2={h_minus_half:.2f} と比較できる。exact-grid の Volterra 構成は forward-variance と spot-martingale のチェックを通過し、共通乱数により Heston との比較が解釈可能になる。</p><p><strong>マイクロ構造の結果は診断的であって同定的ではない。</strong> near-critical な Hawkes フローはクラスター化した活動とラフに見える実現分散プロキシを生むが、ノイズ実験は推定 H がサンプリングと前処理で大きく変わることを示す。</p>"
```

- [ ] **Step 4: Add the 25 keys to `REQUIRED_KEYS`** in `i18n.py` (mirror the `_SECTION_ANCHORS` pattern with `callout.` prefix over the same 25 narrative anchors — note `establishes`/`does-not-establish`/`limitations-next-steps` are narratives too).

- [ ] **Step 5: Rewrite `_narratives`** to pull from the translator:

```python
def _narratives(
    config: ProjectConfig, frames: dict[str, pd.DataFrame], t: Translator
) -> dict[str, str]:
    powers = frames["skew_power_law"]
    target = powers.iloc[(powers["h"] - config.bergomi.h).abs().argmin()]
    values = {
        "executive-summary": {
            "h": config.bergomi.h,
            "beta": float(target["beta"]),
            "h_minus_half": config.bergomi.h - 0.5,
        },
    }
    anchors = [f"callout.{a}".removeprefix("callout.") for a in _NARRATIVE_ANCHORS]
    return {a: t(f"callout.{a}", **values.get(a, {})) for a in _NARRATIVE_ANCHORS}
```
where `_NARRATIVE_ANCHORS` is a module-level tuple of the 25 anchors. Update the call site (line ~898) to `narratives = _narratives(config, frames, t)`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rough_volatility/locales/*.json rough_volatility/src/rough_volatility/i18n.py rough_volatility/src/rough_volatility/report.py rough_volatility/tests/test_report.py
git commit -m "feat(rough_volatility): localize narrative callouts"
```

---

### Task 5: Localize figure captions, evidence note, and section-extra heading

**Files:**
- Modify: `rough_volatility/locales/*.json`, `i18n.py`, `report.py` (`_build_figures`/`_style_figure` call sites, `_section_extra`, evidence note)
- Test: `rough_volatility/tests/test_report.py`

**Interfaces:**
- Produces: keys `evidence_note` (template: `{profile}`, `{seed}`, `{fingerprint}`), `validation_gates_heading`, and `figure.<key>.title` / `figure.<key>.subtitle` for standalone figure captions not covered by a section heading (identify these by reading `_build_figures`, lines 655-699 — e.g. the Hawkes raster `title="Hawkes event raster"`, `subtitle="First 100 time units; use the scenario selector"`).

- [ ] **Step 1: Write the failing test**

```python
def test_captions_and_evidence_note_localized(tmp_path):
    config = load_config(Path("configs/quick.yaml"))
    manifest = ...  # existing fixture wiring
    ja = build_standalone_report(config, tmp_path, manifest, locale="ja").read_text("utf-8")
    assert "根拠:" in ja                       # evidence note prefix, JA
    assert "Evidence: locally generated" not in ja
    assert "検証ゲート" in ja                    # validation_gates_heading, JA
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py::test_captions_and_evidence_note_localized -q`
Expected: FAIL — evidence note / gates heading still English.

- [ ] **Step 3: Add keys** to both locales and `REQUIRED_KEYS`:

`en.json`:
```json
  "evidence_note": "Evidence: locally generated synthetic data; profile {profile}, seed {seed}, fingerprint {fingerprint}.",
  "validation_gates_heading": "Validation gates"
```
`ja.json`:
```json
  "evidence_note": "根拠: ローカル生成の合成データ。プロファイル {profile}、seed {seed}、fingerprint {fingerprint}。",
  "validation_gates_heading": "検証ゲート"
```
Add `figure.<key>.title`/`.subtitle` pairs for any standalone figure caption strings found in `_build_figures` (translate title/subtitle prose; keep axis titles English — those are `update_xaxes/yaxes(title=...)` and are NOT moved).

- [ ] **Step 4: Localize the call sites in `report.py`:**
  - Evidence note (line ~909-911): replace the literal with `t("evidence_note", profile=config.profile, seed=config.seed, fingerprint=config.fingerprint())` (drop the inner `html.escape` on the interpolated pieces only if the current code escapes them; keep escaping the final string once). Preserve the `<p class="evidence-note">…</p>` wrapper.
  - `_section_extra` (line ~881): replace `"<h3>Validation gates</h3>"` with `f"<h3>{html.escape(t('validation_gates_heading'))}</h3>"`. Give `_section_extra` a `t: Translator` parameter and pass `t` at its call site (line ~918).
  - `_build_figures`/`_style_figure`: pass `t` down and replace only the standalone caption `title=`/`subtitle=` literals with `t("figure.<key>.title")`/`t("figure.<key>.subtitle")`. Do NOT touch `update_xaxes/yaxes(title=...)`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add rough_volatility/locales/*.json rough_volatility/src/rough_volatility/i18n.py rough_volatility/src/rough_volatility/report.py rough_volatility/tests/test_report.py
git commit -m "feat(rough_volatility): localize captions, evidence note, and gates heading"
```

---

### Task 6: Embed language-neutral fingerprint + `build_reports` (both locales)

**Files:**
- Modify: `rough_volatility/src/rough_volatility/report.py`
- Test: `rough_volatility/tests/test_report.py`

**Interfaces:**
- Produces: `build_reports(config, root, manifest) -> dict[str, Path]` returning `{"en": path, "ja": path}`; each HTML embeds `<script type="application/json" id="quantitative-fingerprint">{"sha256": "<hex>"}</script>` computed over language-neutral content only.

- [ ] **Step 1: Write the failing test**

```python
import re

def test_bilingual_numeric_parity(tmp_path):
    config = load_config(Path("configs/quick.yaml"))
    manifest = ...  # existing fixture wiring
    from rough_volatility.report import build_reports
    outputs = build_reports(config, tmp_path, manifest)
    assert set(outputs) == {"en", "ja"}
    texts = {loc: p.read_text("utf-8") for loc, p in outputs.items()}
    assert "Rough Volatility Visual Lab" in texts["en"]
    assert "ラフボラティリティ・ビジュアルラボ" in texts["ja"]
    hashes = [re.search(r'"sha256": "([0-9a-f]+)"', t).group(1) for t in texts.values()]
    assert len(set(hashes)) == 1                      # numbers identical across languages
    for t in texts.values():
        assert not re.search(r'(?:src|href)=["\']https?://', t, re.IGNORECASE)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_report.py::test_bilingual_numeric_parity -q`
Expected: FAIL — `cannot import name 'build_reports'`.

- [ ] **Step 3: Add the fingerprint helper + embed it.** At the top of `report.py` add `import hashlib`. Add:

```python
def _quantitative_fingerprint(
    fragments: dict[str, str], metric_cards: str, config: ProjectConfig
) -> str:
    """SHA-256 over language-neutral content (figures, metric values, config).

    Axis titles, metric labels, and figure data are English/neutral, so this is
    identical across locales; only prose differs and is excluded from the hash.
    """
    payload = " ".join(
        [config.fingerprint(), metric_cards, *(fragments[k] for k in sorted(fragments))]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

In `build_standalone_report`, after `metric_cards` is computed (line ~920), build the fingerprint and inject the script tag into the document `<head>` (before `</head>`):

```python
    fingerprint_hex = _quantitative_fingerprint(fragments, metric_cards, config)
    fingerprint_tag = (
        '<script type="application/json" id="quantitative-fingerprint">'
        f'{{"sha256": "{fingerprint_hex}"}}</script>'
    )
```
and add `{fingerprint_tag}` immediately before `</head>` in the `document` string.

- [ ] **Step 4: Add `build_reports`:**

```python
def build_reports(
    config: ProjectConfig, root: str | Path, manifest: dict[str, Path]
) -> dict[str, Path]:
    """Build the English and Japanese reports from the same artifacts."""
    return {
        locale: build_standalone_report(config, root, manifest, locale=locale)
        for locale in ("en", "ja")
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run --no-sync pytest rough_volatility/tests -q`
Expected: PASS (parity hashes equal; both offline).

- [ ] **Step 6: Commit**

```bash
git add rough_volatility/src/rough_volatility/report.py rough_volatility/tests/test_report.py
git commit -m "feat(rough_volatility): embed neutral fingerprint and add build_reports"
```

---

### Task 7: CLI `--locale` + build entry + end-to-end run

**Files:**
- Modify: `rough_volatility/src/rough_volatility/cli.py`
- Create: `rough_volatility/scripts/build_reports.py`
- Test: `rough_volatility/tests/test_report.py` (or a small `tests/test_cli.py`)

**Interfaces:**
- Consumes: `build_reports`, `build_standalone_report`.
- Produces: `report` subcommand accepts `--locale {en,ja,all}` (default `all`); `all` writes both files.

- [ ] **Step 1: Write the failing test** — add `tests/test_cli.py`

```python
from __future__ import annotations

from pathlib import Path

from rough_volatility.cli import main


def test_report_cli_builds_both_locales(tmp_path):
    rc = main(["report", "--root", str(tmp_path), "--locale", "all", "--force"])
    assert rc == 0
    reports = tmp_path / "reports"  # adjust to config.output.reports_dir
    assert (reports / "rough_volatility_report_en.html").exists()
    assert (reports / "rough_volatility_report_ja.html").exists()
```

> Implementer note: `--force` regenerates artifacts under `tmp_path`; if the quick profile is too slow for CI, mark this test `@pytest.mark.slow` to match the project's existing fast/slow split (see `pyproject.toml`/`conftest.py`).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --no-sync pytest rough_volatility/tests/test_cli.py -q`
Expected: FAIL — `--locale` unrecognized.

- [ ] **Step 3: Add `--locale` to the `report` parser and branch.** In `cli.py` `_parser`, after adding the shared args, add a `--locale` argument to the `report` subparser only:

```python
        if name == "report":
            command.add_argument(
                "--locale",
                choices=("en", "ja", "all"),
                default="all",
                help="report language(s) to build (default: all)",
            )
```
In `main`, replace the `build_standalone_report(config, root, artifacts)` call (line ~100) with:

```python
        from rough_volatility.report import build_reports

        if args.locale == "all":
            reports = build_reports(config, root, artifacts)
        else:
            reports = {
                args.locale: build_standalone_report(
                    config, root, artifacts, locale=args.locale
                )
            }
        LOGGER.info("reports=%s static_files=%d", list(reports), len(figures))
```

- [ ] **Step 4: Create `scripts/build_reports.py`** (mirror `optimal_execution`):

```python
from rough_volatility.cli import main

raise SystemExit(main(["report", "--locale", "all", *__import__("sys").argv[1:]]))
```

- [ ] **Step 5: Run the full suite + a real end-to-end build**

Run: `uv run --no-sync pytest rough_volatility/tests -q`
Expected: PASS (all tests, both locales).

Run (end-to-end, real artifacts):
`cd rough_volatility && make demo`
Expected: exit 0; `reports/rough_volatility_report_en.html` and `reports/rough_volatility_report_ja.html` both exist and are self-contained. If `make demo` builds only one report, update its report step (or the Makefile target) to invoke `--locale all` / `scripts/build_reports.py`.

- [ ] **Step 6: Verify the JA report visually**

Run: `explorer.exe "$(wslpath -w /home/kazumasa/projects/rough_volatility/reports/rough_volatility_report_ja.html)"`
Confirm: headings/narrative/captions Japanese; equations, axis titles, metric labels English; numbers match the EN report.

- [ ] **Step 7: Commit**

```bash
git add rough_volatility/src/rough_volatility/cli.py rough_volatility/scripts/build_reports.py rough_volatility/tests/test_cli.py
git commit -m "feat(rough_volatility): --locale CLI flag and bilingual build entry"
```

---

## Self-Review

**Spec coverage:**
- i18n layer ported → Task 1. ✔
- `section.<slug>` headings JA → Task 3. ✔
- `callout.<slug>` narrative JA (with interpolation) → Task 4. ✔
- Figure captions + intro/chrome JA → Tasks 2, 5. ✔
- Axis titles / metric labels / derivations kept EN → enforced by only moving specific literals (Tasks 4-5) and Global Constraints. ✔
- `_en`/`_ja` filenames, existing → `_en` → Task 2 (default filename now suffixed). ✔
- Fingerprint parity test → Task 6. ✔
- `test_i18n` key parity → Task 1. ✔
- Offline self-contained for both → Tasks 6-7. ✔
- CLI `--locale {en,ja,all}` + build both → Task 7. ✔
- Notebook untranslated → never modified. ✔

**Placeholder scan:** Test bodies contain `manifest = ...` fixtures deliberately deferred to the existing test wiring (flagged with implementer notes to mirror `test_report_is_self_contained_interactive_and_complete`), not code placeholders. All production code steps show full code. JA translations: chrome/headings fully provided; the 25 callouts give verbatim EN source + policy + one fully-worked JA example — the executor (an LLM) produces the remaining faithful translations, reviewed at the Task 4 gate.

**Type consistency:** `Translator.__call__(key, **values)`, `build_standalone_report(..., locale="en", ...)`, `build_reports(config, root, manifest) -> dict[str, Path]`, `_narratives(config, frames, t)`, `_section_extra(anchor, config, validation, t)`, `_quantitative_fingerprint(fragments, metric_cards, config)` — names/signatures are consistent across tasks. `REQUIRED_KEYS` grows monotonically (chrome → sections → callouts → captions) with locale files kept in key-parity at every task.

## Execution Handoff

(To be offered after user acknowledges the plan.)
