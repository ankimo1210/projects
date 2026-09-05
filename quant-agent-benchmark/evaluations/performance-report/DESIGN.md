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
| Overall | Who leads this rubric? Fable first, Opus close, Luna third. | Ranking / horizontal bar | model × score; 7 rows | scores |
| Categories | Where are deficits? Numerical error plus format-dependent deductions. | Matrix / heatmap | category × model; 7 rows, 7 measures, normalized 0–1 | scores |
| Accuracy | How large is main zero-rate error? Luna improves on Astra/Sol; Sonnet is highest. | Comparison / horizontal bar | model × zero RMSE bp; 7 rows | precision |
| Hidden scenarios | Does the pattern persist? Fable still lowest in 9/10. | Matrix / heatmap | model × scenario; 7 rows, 10 measures in bp (transposed to avoid the previously observed 10-row overflow) | precision |
| Time | How long was actual work? Terra shortest, Luna 33 minutes. | Comparison / horizontal bar | model × work minutes; 7 rows | usage |
| Tokens | Where is the volume? Input dominates, not output. | Composition / horizontalStackedBar | model × input/output; 14 rows | usage |
| Output | How much logged reasoning and normal output? Different response granularity. | Composition / horizontalStackedBar | model × normal/reasoning output; 14 rows | usage |

Repeated bars are intentional: seven runs are meaningful categories, not a sufficient
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

The frozen four-model generator `build_report.py` is historical; do not run it over
the current artifact. The seven-model updater is
`python3 evaluations/performance-report/update_report_seven.py`.
It expanded the then-current four-model artifact, preserved all existing IDs and
reading order, and backed it up under `versions/four-models-before-seven/`.
On an already-expanded artifact it checks that evidence and artifact hashes match
the validation record, rather than replaying structural changes or reverting edits.
Then run the installed Data Analytics `deliver_portable_artifact.mjs` with
`--input evaluations/performance-report/artifact.json --output evaluations/performance_report.html`.
Source SHA-256 values and calculation checks are saved in `validation.json`.
The final HTML contains its dataset and reader; supporting files are not runtime dependencies.

## Current seven-model QA outcome

7 charts and 16 native tables, 54 packaged blocks. The 5 wide metric lookup tables
retain original four-model columns and add an adjacent three-model panel. Data
fields contain all seven models, but no visible table exceeds 6 columns. No old
chart, table, dataset, caveat section or block ID was removed.

597 calculation, SQL, token, scope, schema and preservation checks passed, distinct
from 403 candidate-written pytest passes. The seven raw session logs were newly
recovered; eight work turns were selected. Added models were evaluated and tested
in isolated copies; old four evaluations/tests were reused only after exact
candidate and evaluator hash matches. `expanded-7-models/evaluation_audit.json`
records the distinction. Sonnet's shipped diagnostics equal the isolated rerun;
Terra's largest diagnostic difference is 0.00001096 (below displayed precision).

`seven_model_audit.ipynb` contains 4 standard-library code cells, all executed in
order with captured outputs. nbformat/nbclient were unavailable; notebook v4.5
cell structure was explicitly checked instead of installing packages. Exact source
SQL remains in `report_queries.sql` and canonical source metadata.

Correction: the prior bid/ask metric label incorrectly implied public-quote fit.
`evaluator/scoring.py` compares hidden `true_quote`, normalized by half-spread with
a floor. Numeric values are retained; labels, definitions and interpretation are
corrected. Added-model schema issues, Terra's passed missing-quote check, and the
four-name static-scan limitation are visible caveats, not manual score adjustments.

The packaged seven-model receipt passed artifact validation, exact payload equality
and structural verification. It could not discover a compatible headless browser;
new seven-model desktop/mobile layout, themes and source interaction are NOT
browser-verified. Earlier manual QA below covers only the four-model edition.
Automatic light/dark runtime and semantic no-script table fallbacks are retained.

## Seven-model re-review (2026-09-05, after update_report_seven.py)

`patch_report_seven_review.py` applies reviewed edits on top of the updater's output and
refreshes the validated artifact hash, so the updater's idempotent check still passes.
Edits: the Fable score-gap table now covers all six comparisons (Sonnet had been dropped
although the text quotes its 20.071-point core gap; 満点 folded into the row label to stay at
six columns); section 3 states the cross-model pattern that the two baseline-selecting
implementations (Sol, Sonnet) carry the two largest short-end errors; the limitations list
records that no isolation-preflight grant list is on record for any of the seven runs and
that Terra sits outside the benchmark tree. Manual browser QA of this edition in the
installed Chrome at 1280px (light theme): 7 charts, both 7-row heatmaps and all 16 tables
render without clipping or internal scroll. Dark theme and mobile width not re-verified.
Reproduction order: `update_report_seven.py` → `patch_report_seven_review.py` → packaged
`deliver_portable_artifact.mjs` (via `deliver_report.mjs`).

## Historical four-model QA outcome

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
