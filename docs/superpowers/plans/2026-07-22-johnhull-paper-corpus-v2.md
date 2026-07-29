# JohnHull paper corpus v2 implementation plan

**Date:** 2026-07-22

**Project:** `johnhull`

**Base:** `origin/main` at `ffa72f70`
**Goal:** make the referenced-paper corpus safe for AI-assisted financial-model
implementation by preserving prose, formulas, tables, and evidence-backed key claims.

## 1. Current evidence

- 50 tracked source PDFs, 1,536 pages, and 780 retrieval chunks.
- 3,330 extracted image regions but only 3 LaTeX math markers.
- 49 papers have `review` status and only one has `pass` status.
- Four papers exceed the current replacement-character warning threshold.
- Formula-heavy spot checks show corrupted symbols and subscripts in text output.
- Hull--White Table 4 loses the `0.35` and `0.34` cells in Markdown.
- The Jarrow--Yildirim paper is catalogued as a link but has no local PDF or corpus entry.

The existing output is useful for discovery and page navigation, but it is not a
semantic source of truth for equations or numerical tables.

## 2. Scope and non-goals

### In scope

1. Versioned page/block/equation/table/claim schemas with source provenance.
2. PDF preflight, page classification, language-aware OCR, and damaged-page fallback.
3. A JohnHull-specific manually verified gold set.
4. A measured extractor bake-off before selecting a heavy document model.
5. Machine-readable LaTeX, structured tables, evidence-backed claims, and semantic chunks.
6. Deterministic regeneration, quality reports, retrieval tests, and release integration.

### Out of scope

- Changing any `hullkit` pricing model or financial convention.
- Treating implementation code as ground truth for the papers.
- Importing torch or document-model dependencies into `hullkit`.
- Sending source documents to a remote LLM by default.
- Overwriting or repairing source PDFs in place.

## 3. Priority sources

P0 sources require complete manual verification of every formula, table, and claim used
by the implementation:

1. Hull--White interest-rate derivatives.
2. Heston stochastic volatility.
3. Jarrow--Yildirim inflation model.
4. Official Japanese JGBi convention sources.
5. Hagan et al. SABR.
6. McNeil--Frey VaR/ES and EVT.
7. Lyashenko--Mercurio backward-looking RFRs.

All other sources must meet automated corpus gates and receive a stratified manual audit.

## 4. Output contract

The v2 output adds these records while preserving the current `paper.md`, `pages.jsonl`,
`chunks.jsonl`, and aggregate index during migration:

```text
references/processed/{paper_id}/
├── metadata.json
├── pages.jsonl
├── blocks.jsonl
├── equations.jsonl
├── tables.jsonl
├── figures.jsonl
├── claims.jsonl
├── symbols.json
├── chunks.jsonl
├── paper.md
├── quality.json
├── assets/{equations,tables,figures,formula-renders,source-pages}/
└── tables/{table_id}.{json,csv,html}
```

Every derived record carries the source PDF SHA-256, page number, bounding box,
extractor/model identity, confidence, and verification status. A low-confidence result is
stored as `unverified`; it must never silently become trusted text.

## 5. Implementation phases

### Phase 0 -- contract and baseline

- Commit this plan and the durable project quality contract.
- Generate a machine-readable baseline manifest from the current corpus.
- Record source hashes, page counts, qpdf status, current quality metrics, and P0 coverage.

### Phase 1 -- schema and regression harness

- Split the monolithic converter into private modules under
  `johnhull/scripts/paper_corpus/` while retaining the CLI wrapper.
- Add dataclass-backed schema validation with no new production dependency.
- Add fixtures for Hull--White formulas/Table 4, Heston formulas, McNeil--Frey damaged
  content, Bachelier language/layout, and one modern born-digital paper.

### Phase 2 -- preflight and routing

- Classify every page as born-digital, scan, hybrid, damaged, math-dense, or table-dense.
- Detect language, rotation, page boxes, text density, and PDF structural errors.
- Route damaged pages to rendered-image OCR without modifying the original PDF.
- Persist the chosen route and transformation provenance.

### Phase 3 -- gold set

- Annotate at least 60 pages across 10--12 representative papers.
- Include at least 150 display equations, 200 inline equations, 500 table cells, and
  5--10 evidence-backed claims per paper.
- Fully review P0 formulas/tables used by JohnHull implementations.

### Phase 4 -- extractor bake-off

- Evaluate PyMuPDF4LLM, MinerU, Docling, and Marker in isolated environments.
- Score text edit distance, formula CDM/token error, table TEDS/numeric accuracy, reading
  order, runtime, memory, reproducibility, and licensing.
- Do not pin a heavy dependency until the benchmark and license gate are accepted.

### Phase 5 -- prose and layout

- Emit ordered page blocks with stable IDs and bounding boxes.
- Keep raw and normalized text separately.
- Remove repeated furniture without losing footnotes or citations.
- Use language-aware OCR and extractor disagreement to flag review pages.

### Phase 6 -- equations and symbols

- Detect display and inline formulas, crop the source region, and produce LaTeX.
- Link equation numbers and textual references.
- Compile and render LaTeX, then compare it with the source crop.
- Generate a per-paper symbol table and retain unverified image fallbacks.

### Phase 7 -- tables and figures

- Emit tables as structural JSON, HTML, and CSV with raw and typed cell values.
- Preserve merged headers, units, captions, footnotes, and source bounding boxes.
- Add numeric-cell and rendered-overlay validation.
- Keep figures and captions without inventing axis values or descriptions.

### Phase 8 -- evidence-backed claims

- Extract research question, assumptions, dynamics, measure/numeraire, payoff, pricing
  equations, calibration inputs, numerical methods, results, limitations, and warnings.
- Require every claim to cite source blocks and related equations/tables.
- Add finance-specific checks for measures, nominal/real rates, drift, correlations,
  seasonality, lag/interpolation, floors, confidence levels, and holding periods.

### Phase 9 -- semantic chunks and retrieval

- Chunk by sections and blocks instead of raw character count.
- Keep equations with their definitions and tables with captions/explanations.
- Add fixed retrieval questions for Hull--White, Heston, inflation/JGBi, SABR, RFR,
  and VaR/ES, with expected page/equation/table evidence.

### Phase 10 -- migration and release

- Regenerate the complete corpus in a temporary directory twice.
- Run schema, gold, retrieval, determinism, and source-integrity gates.
- Review every remaining exception, then replace v1 outputs atomically.
- Integrate the corpus checks into the JohnHull release workflow and documentation.

## 6. Release gates

| Dimension | Required gate |
|---|---|
| Source/page integrity | 100% source hashes and pages accounted for |
| Page blocks | no missing/duplicate IDs or unresolved assets |
| Born-digital text | gold CER below 1% |
| Legacy/scanned text | gold CER below 3% or explicit reviewed exception |
| Formula detection | at least 98% gold recall |
| Formula representation | 100% compile; at least 95 formula CDM |
| P0 formulas | 100% manually verified |
| Table structure | at least 95 TEDS on gold |
| Numeric cells | at least 99.5% overall and 100% for P0 tables |
| Claims | 100% evidence coverage; at least 95% audited accuracy |
| P0 claims | 100% manually verified |
| Retrieval | at least 95% Hit@5 and 100% for P0 questions |
| Determinism | byte-identical output for fixed source/tool/model hashes |

No aggregate `pass` is allowed when a component gate is `review`, `fail`, or
`missing_source`.

## 7. Proposed commit boundaries

1. `docs(johnhull): define paper corpus v2 quality contract`
2. `test(johnhull): add paper corpus gold fixtures`
3. `feat(johnhull): add PDF preflight and block schema`
4. `feat(johnhull): adopt structured document extractor`
5. `feat(johnhull): extract and verify formulas`
6. `feat(johnhull): structure tables and figures`
7. `feat(johnhull): add evidence-backed research claims`
8. `feat(johnhull): rebuild semantic paper chunks`
9. `data(johnhull): regenerate verified paper corpus`
10. `docs(johnhull): publish corpus v2 validation`

## 8. Completion rule

The work is complete only when all source, schema, formula, table, claim, retrieval,
determinism, and JohnHull release gates pass, P0 material is manually verified, and no
required source is silently absent. Jarrow--Yildirim, Wu, Canty, and the official JGBi
sources are now locally present and hash-accounted; any future missing source must remain
an explicit `missing_source` and cannot receive a passing semantic status.

## 9. Implementation checkpoint (2026-07-23)

- Phase 0--7 gates are implemented; the Gold set is 106 pages with 248 display
  equations, 589 inline equations, 16 reviewed tables, and 651 structural cells.
- Thirty-five implementation-critical formulas have exact reviewed LaTeX, successful
  independent renders, and manual source-page comparison.
- Phase 8 has 75 source-backed Gold claims and 100% P0 manual verification.
- Phase 9 has 225 section-aware Gold chunks and a fixed 28-question suite with 100%
  Hit@5, including 100% on P0 questions.
- The P0 implementation evidence gate resolves 59 symbols across nine components to
  every reviewed P0 formula/table assertion and all 50 P0 claims, with 100% coverage of
  the 10 P0 papers.
- Phase 10 is complete: 55 papers and all 1,627 pages were regenerated twice; all 55
  quality records pass every component gate with zero unresolved exceptions; 11,092
  relative files are byte-identical; v1 was atomically replaced by v2; and the corpus
  gate is integrated into `hull-release`.
