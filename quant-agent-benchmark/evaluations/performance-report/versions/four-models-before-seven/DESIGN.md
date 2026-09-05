---
name: Quant agent performance report
description: Source-backed Japanese executive report with technical evidence.
colors: Native identity bars; sequential blue matrices; two blue tones for composition.
typography: Shared system sans and tabular numerical typography; Japanese narrative.
spacing: Shared portable reader spacing; no HTML-specific overrides.
rounded: Shared reader tokens only.
surfaces: Automatic light and dark; responsive desktop and narrow reader.
components: Markdown sections, metric cards, native charts, exact-lookup tables, source affordances.
implementation: Canonical artifact.json and packaged deliver_portable_artifact.mjs only.
---

# Overview

Audience: benchmark owner choosing the next evaluation and model candidates.
Delivery: explicit HTML, local and self-contained; no publication or external connection.
Answer-first summary; separate capability, elapsed time, and processed tokens.
One run/model. No generalized model-family ranking, unmeasured cost, or causal attribution.

# Colors

Single-root preferred: blue matrices and ungrouped ranks with direct model labels.
Composition: exactly two blue tones from the shared stacked palette, with named legends.
No redundant model color encoding. Canonical palette intent is declared in each chart.
The shared renderer currently owns final paint tokens; it exposes no canonical custom
per-series color map. Do not work around this with legacy series or custom HTML.
Native light/dark token behavior is kept intact. Tables are neutral, not red/green graded.
For sequential matrices, captions explicitly distinguish high attainment from high error.

# Typography

System fonts from the portable reader. Native axis and tabular numerals.
Japanese body; technical identifiers preserved. Three score decimals and exact token
counts in lookup tables, compact M/k in volume charts. No long raw paths in narrative.

# Layout

Full-width, single-column report blocks; all charts full width, mobile stacked.
Executive Summary is separate and immediately follows the title. Three headline cards
follow the summary. Exact-value tables complement, rather than replace, visual findings.

# Elevation & Depth

Shared reader surfaces only. No decorative wrapper shells or bespoke CSS.

# Shapes

Native bars and matrices. No radar, 3D, dual axes, or truncated absolute-value axes.

# Components

| Section | Question / takeaway | Family / native type | Fields / grain | Source |
|---|---|---|---|---|
| Overall | Who leads this rubric? Fable first, Opus close. | Ranking / horizontal bar | model × score; 4 rows | scores |
| Categories | Where are deficits? Core numerical/model plus Astra report. | Matrix / heatmap | category × model; 7 rows, 4 measures, normalized 0–1 | scores |
| Accuracy | How large is main zero-rate error? Two lower-error runs. | Comparison / horizontal bar | model × zero RMSE bp; 4 rows | precision |
| Hidden scenarios | Does the pattern persist? Fable lowest in 9/10. | Matrix / heatmap | model × scenario; 4 rows, 10 measures in bp (transposed: the shared card renderer fixes heatmap height and a 10-row matrix overflowed into an internal scroll) | precision |
| Time | How long was actual work? Sol shortest. | Comparison / horizontal bar | model × work minutes; 4 rows | usage |
| Tokens | Where is the volume? Input dominates, not output. | Composition / horizontalStackedBar | model × input/output; 8 rows | usage |
| Output | How much logged reasoning and normal output? Different response granularity. | Composition / horizontalStackedBar | model × normal/reasoning output; 8 rows | usage |

Repeated bars are intentional: four runs are meaningful categories, not a sufficient
population for a scatter-based relationship claim. Ten hidden scenarios form a matrix,
not a time series or ten independent model reruns. Turn chronology uses exact interval
tables; sparse resumptions do not justify a fabricated temporal trend.

Every chart has an adjacent interpretation and a source with file identities and metric
definitions. Supporting dataset rows retain adjacent measures and denominators where
available. Canonical snapshot is bounded and contains no conversation/thinking text.

# Do's and Don'ts

- Do reconcile categories, token components, turns, API counts, test counts and hashes.
- Do separate selected work from session totals, Opus idle from work, and self-report from logs.
- Do preserve raw scores and make rubric flaws explicit; do not silently correct ranks.
- Do distinguish main diagnostics, hidden scenarios, and candidate-written test results.
- Do keep local absolute paths out of artifact source metadata; preserve root-relative identities.
- Do use the packaged builder's verification receipt for browser QA. No duplicate automation
  or routine screenshots after a passed receipt.
- Do not estimate dollars, energy, statistical significance, or causal contributions.

## Reproduction

From the benchmark root, run `python3 evaluations/performance-report/build_report.py`.
Then run the installed Data Analytics `deliver_portable_artifact.mjs` with
`--input evaluations/performance-report/artifact.json --output evaluations/performance_report.html`.
Source SHA-256 values and calculation checks are saved in `validation.json`.
The final HTML contains its dataset and reader; supporting files are not runtime dependencies.

## QA outcome

Calculation/source checks passed (356 report checks, distinct from the 329 candidate
pytest passes). SQL derives category attainment, recomputes selected-turn totals from
14 user turns, ranks scenario errors, and reconciles evaluator/test counts. The installed
widget validator unexpectedly requires SQL on all numerical assets; file-only qualitative
reviews remain sourced markdown, and real executed SQL plus original file provenance are
preserved for the numerical assets. The report has 7 charts and 11 native tables.

Analysis revisions (2026-09-05 review): the token narrative and input-token table carry a
cache-read-excluded volume (uncached + cache creation + output), because cache reads are
92-98% of every total and turned a 1.2x Opus/Fable gap into a 5.5x headline; the gap
section states that 18 of the 20 "model quality" points re-score the same main-curve RMSE
as numerical correctness (verified against `evaluator/scoring.py`); the rubric-limitations
list records that all four candidates failed `data.missing_handling` for the same reason
(the rubric accepts only `exclude`, all four reconstructed the quote from the bid/ask mid);
the scope note verifies from file mtimes that Sol's excluded correction turn changed only
its self-report summary; a scenario forward-RMSE table backs the Opus s09 claim and the
risk table gains the bid/ask-normalized quote-reproduction error.

Table layout rule learned in browser QA: the shared reader clips any table wider than its
768px column and macOS hides the horizontal scrollbar, so clipped columns are simply
invisible. Lookup tables therefore put metrics in rows and the four models in columns
(category scores, accuracy diagnostics, token breakdown, response granularity, scenario
forward RMSE) and stay at six columns or fewer; `density: "dense"` does not help because it
stops header wrapping. Row order is carried by numbered labels ("1. ...") so no sort
column is needed.

The packaged default delivery passed artifact validation, payload equality, and structural
verification. No installed headless-shell was auto-discovered. The installed Google Chrome
was explicitly tried with two bounded budgets; extraction timed out at 11.2 and 28.7 seconds.
No browser was installed, no user browser profile was used, no plugin code was changed,
and no custom renderer or independent browser automation was substituted.

Manual browser QA (2026-09-05, installed Google Chrome, 1280px desktop) later covered
every chart and table in the light theme and in a dark theme emulated by applying the
page's `prefers-color-scheme: dark` rules. It found the 10-row scenario heatmap clipped
behind an internal scroll (fixed by transposing to model × scenario) and confirmed that
chart subtitles are hidden unless `showDescription` is set (enabled for both heatmaps,
whose subtitles state which direction is good). Mobile-width layout and the source
dialog remain unverified; the packaged receipt is still structural-only.
The final delivery uses the enhanced reader plus its semantic, table-backed fallback.
This limitation must be disclosed in handoff. The final structural receipt is saved in
`delivery-receipt.json`.
