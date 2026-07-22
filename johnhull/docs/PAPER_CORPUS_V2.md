# Paper corpus v2 quality contract

This document is the source of truth for AI-readable paper artifacts under
`johnhull/references/processed/`.

## Intended use

The corpus supports discovery, page-cited reading, and verification of financial-model
implementations. It must not turn uncertain OCR, formulas, tables, or summaries into
apparently authoritative text.

## Trust model

The original PDF is authoritative. Derived records are evidence pointers with an explicit
verification state:

- `verified`: checked by a deterministic gold assertion or human review.
- `auto`: generated and passed automated gates, but not manually reviewed.
- `unverified`: retained for navigation; not safe as an implementation source.
- `failed`: a known extraction or validation failure.
- `missing_source`: the cited source is not locally available.

Every derived record must include `paper_id`, `page_number`, `source_pdf_sha256`, and a
stable record ID. Spatial records also include a PDF-coordinate bounding box. Model-based
records include extractor name, version, model hash, and confidence when available.

## Component statuses

`quality.json` reports `text_status`, `layout_status`, `formula_status`, `table_status`,
`claims_status`, `retrieval_status`, and `overall_status`. The overall status is the worst
component status; it is never inferred from average characters per page.

## Critical-source policy

Formulas, tables, or claims used to justify `hullkit` implementations are P0. They require
manual verification against the source page even when automated metrics pass. P0 currently
covers Hull--White, Heston, Jarrow--Yildirim when acquired, Japanese JGBi conventions,
Hagan et al. SABR, McNeil--Frey VaR/ES, and Lyashenko--Mercurio RFR material.

## Fail-closed rules

1. Unparseable or low-confidence formulas remain source images marked `unverified`.
2. A table with missing cells, ambiguous structure, or failed numeric validation is not
   emitted as trusted CSV.
3. A claim without page/block evidence is rejected.
4. A numeric claim must reference a verified equation or table cell.
5. Missing sources are reported and cannot receive a passing semantic status.
6. Original PDFs are never overwritten by repair or OCR operations.
7. Remote LLM/API processing is opt-in; the default pipeline is local and auditable.

## Required release evidence

- source and page integrity report;
- schema and referential-integrity tests;
- gold-set text, formula, table, and reading-order metrics;
- P0 manual-review manifest;
- retrieval evaluation with expected evidence;
- two-run deterministic rebuild comparison;
- JohnHull release checks.

The detailed implementation phases and numeric gates are recorded in
`docs/superpowers/plans/2026-07-22-johnhull-paper-corpus-v2.md`.

## Extractor boundary

MinerU 3.4.4 `pipeline` is the selected local structured-output backend. It is
run as an optional pinned tool rather than a workspace dependency. The tracked
`references/gold/extractor_bakeoff.json` records the comparison, operational
constraints, and license review. Selection does not imply semantic trust:
MinerU output starts as `auto` or `unverified`, and only an independently
reviewed assertion can produce a `verified` formula or table cell.

The v2 adapter consumes MinerU's `*_content_list.json` and emits:

- ordered `blocks.jsonl` with raw/normalized text and PDF-point bounding boxes;
- `equations.jsonl` with display/inline LaTeX, equation numbers, source crops,
  syntax status, and reviewed overrides;
- structural `tables.jsonl` plus per-table JSON, HTML, CSV, and source crops;
- `figures.jsonl`, `pages.jsonl`, `symbols.json`, `paper.md`, provenance metadata,
  and component-level `quality.json`.

The adapter fails if source pages are missing, page indices are non-contiguous,
assets disappear, or a reviewed assertion no longer resolves to its exact
source region. Japanese reading order is always routed to review. Low text
coverage versus the source PDF is a text failure rather than an empty success.

## Formula and table gates

Every emitted LaTeX string must compile to well-formed MathML. A failed automatic
candidate is moved to `latex_candidate` and the equation remains available only as
its source-image fallback; it is not counted as an emitted LaTeX representation.
Reviewed formulas additionally render to a deterministic PNG and retain the
manual source-comparison result. The Gold set currently has 100% display/inline
detection recall, 100% compile success for emitted LaTeX, and 100% render success
for reviewed assertions. The three failed Japanese formula candidates remain
explicit image fallbacks.

All 14 Gold table crops were independently reviewed. Five malformed extractor
structures have manual structural replacements, while known numeric OCR errors
retain both `extractor_raw_text` and the reviewed value. The resulting Gold table
score is 1.0 structural TEDS and 100% numeric accuracy across 427 scalar cells,
including 176 P0 cells. These scores apply to the reviewed Gold set only; an
unreviewed table in the full corpus remains `unverified`.
