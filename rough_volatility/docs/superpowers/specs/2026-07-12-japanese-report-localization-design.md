# Design: Japanese localization of the rough_volatility report

**Date:** 2026-07-12
**Status:** Approved design (pending spec review)
**Scope:** Add a Japanese (`ja`) rendering of the standalone offline HTML report,
alongside the existing English (`en`) report, by porting the proven i18n layer
from the sibling `optimal_execution` project.

## Goal

Produce `rough_volatility_report_ja.html` in addition to
`rough_volatility_report_en.html`, from the **same** figures, data, and numeric
results, so the two reports are quantitatively identical and differ only in
prose language.

## Translation policy (approved)

Hybrid. The report is math-first; LaTeX is language-neutral and never changes.

| Element | Language |
|---|---|
| Section headings | Japanese |
| Narrative body / callouts (`_narratives`) | Japanese |
| Executive summary / intro / page chrome (title, subtitle) | Japanese |
| Figure captions (`_style_figure` title & subtitle) | Japanese |
| Equations / LaTeX / MathJax | unchanged |
| Mathematical-derivation paragraphs | English (retained) |
| Metric-card labels, config/validation table headers | English (retained) |
| Figure **axis** titles (`update_xaxes/yaxes(title=...)`) | English (retained) |

**Design rule:** only prose that *differs* between locales is routed through the
`Translator`. English-retained technical labels and axis titles stay as literals
in `report.py` (no locale key), minimizing churn and keeping the diff focused.

## Chosen approach: port the `optimal_execution` i18n layer

Rejected alternatives:
- **Duplicate `report.py` into a JA variant** — content drifts out of sync, no
  parity guarantee. Rejected.
- **Post-hoc string replacement on generated EN HTML** — brittle against
  MathJax/HTML structure. Rejected.

## Architecture

New units:

- `rough_volatility/locales/en.json`, `rough_volatility/locales/ja.json`
  — flat `{key: string}` maps. `en.json` holds the current English strings
  (extracted verbatim); `ja.json` holds Japanese for the translated surface and
  the identical English string for any retained-English key that must still pass
  through the layer (none expected under the design rule above).
- `src/rough_volatility/i18n.py` — port of `optimal_execution/i18n.py`:
  `load_locale`, `validate_locales` (key-set parity), `Translator` with
  `__call__(key, **values)` doing `str.format(**values)` for interpolated
  strings. `SUPPORTED_LOCALES = ("en", "ja")`. A `REQUIRED_KEYS` set enumerates
  every key the report consumes, so a missing translation fails fast.

Key-naming scheme:

- `report_title`, `report_subtitle`, `report_intro` — page chrome.
- `section.<slug>` — the 26 `Section.title` strings (slugs already exist in
  `notebook.py`, e.g. `executive-summary`, `iv-smiles`).
- `callout.<slug>` — the 25 `_narratives` entries. Entries currently built with
  f-strings become `{placeholder}` templates resolved via
  `Translator(key, **values)`.
- `figure.<key>.title` / `figure.<key>.subtitle` — figure captions. A figure
  that heads a section reuses the localized `section.<slug>` for its title (no
  separate key); a standalone figure whose title is a literal distinct from any
  section heading (e.g. "Hawkes event raster" / "First 100 time units…") gets its
  own `figure.<key>.title` and `.subtitle` keys. The exact figure→key mapping is
  enumerated in the implementation plan.

## Changed units

- `notebook.py` — **unchanged.** `SECTIONS` stays English (the notebook is a
  single-language artifact). The report localizes headings by looking up
  `section.<slug>` at render time, keyed on the existing `Section.slug`.
- `report.py` —
  - `build_standalone_report(config, root, artifacts, *, locale="en")` gains a
    `locale` parameter; constructs a `Translator(locale)`.
  - `_narratives(...)`, `_style_figure(...)`, section-heading rendering, and page
    chrome take the translator (or pre-resolved strings) instead of literals for
    the translated surface. Axis titles, metric labels, and derivation
    paragraphs stay literal.
  - Output filename becomes `rough_volatility_report_{locale}.html`.
- `cli.py` — the `report` command gains `--locale {en,ja,all}` (default `all` to
  match `optimal_execution`; `all` builds both). Loops locales, calling
  `build_standalone_report(..., locale=locale)` per language.
- Build entry (`make demo`/`make full` path and any `scripts/`): builds both
  languages, mirroring `optimal_execution/scripts/build_reports.py`.
- `.gitignore` already excludes `reports/*.html`; both new filenames are covered.

## Output & naming (approved)

- Rename existing `rough_volatility_report.html` → `rough_volatility_report_en.html`.
- Add `rough_volatility_report_ja.html`.
- Both are gitignored and regenerated; no committed artifact churn.

## Data flow

`experiments → artifacts (data/figures, language-neutral) → build_standalone_report(locale)`
renders once per locale over the **same** loaded frames and figures. Figures,
numbers, and MathJax are produced identically; only the `Translator`-sourced
prose differs.

## Error handling

- `load_locale` raises on unsupported locale, non-flat JSON, or missing required
  keys (fail fast at build).
- `validate_locales()` asserts `en`/`ja` have identical key sets; run in tests
  and at build start.
- Interpolated callouts raise `KeyError` on a missing `{placeholder}` value.

## Testing

Port `optimal_execution`'s report tests to `rough_volatility`:

1. `test_i18n.py` — every `REQUIRED_KEYS` present in both locales; key-set
   parity; interpolation placeholders resolve; no locale drift.
2. `test_report.py` (extend) — build both locales; assert
   **quantitative fingerprint parity**: the numeric/data-bearing content (metric
   values, figure data payloads, validation numbers) is byte-identical across
   `en` and `ja`; only prose fragments differ. Mirror
   `optimal_execution`'s `bilingual_report_check` approach (hash the
   language-neutral content).
3. Offline self-containment check already in `test_report.py` runs for both
   outputs (attribute-level `(src|href)=["']https?://` absence; note the known
   inline-Plotly harmless-`https`-string caveat).

## Out of scope

- Translating the notebook (`01_rough_volatility_visual_lab.ipynb`) — English.
- Translating axis titles, metric labels, and dense math-derivation paragraphs.
- Any change to experiments, estimators, or numeric methods.

## Acceptance criteria

- `make demo` (or the report command with `--locale all`) emits both
  `_en` and `_ja` HTML, self-contained and offline.
- `ja` report: headings, narrative, captions, intro in Japanese; equations,
  axis titles, metric labels, derivation paragraphs in English.
- Fingerprint-parity test passes (numbers identical across languages).
- Full `rough_volatility` test suite green.
