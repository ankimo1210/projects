# Accuracy and Completeness Audit

Source PDF: `winprob_eu_ocr.pdf`  
Audit timestamp: 2026-06-20 19:44 JST

## Executive conclusion

The package is complete as a page-preserving Markdown + PNG extraction. Every PDF page has a Markdown page and a rendered page image. The rendered page images preserve the visual source of truth for text, figures, tables, equations, and layout.

It is not a fully clean, manually proofread Markdown transcription of the whole PDF. The source PDF is OCR-based, so the extracted prose in `full_document.md` and `pages/page_###.md` inherits OCR errors. The most important equation/table items have been separately corrected or indexed in `verified_equations.md` and `tables/`.

## Automated checks

| Check | Result |
|---|---:|
| Source PDF page count | 73 |
| Page Markdown files | 73 |
| Rendered page PNGs | 73 |
| Page numbering continuity | Passed, pages 001-073 |
| PNG dimensions | 1323 x 1871 on all 73 pages |
| Empty extracted text pages | 0 |
| Markdown extracted-text blocks matching PDF OCR text layer | 73 / 73 |
| Broken image links in page Markdown | 0 |
| ZIP integrity test | Passed |
| ZIP entries | 158 |

## Visual fidelity check

I independently re-rendered all 73 PDF pages at the same dimensions and compared them to the packaged page PNGs.

| Metric | Result |
|---|---:|
| Dimension mismatches | 0 |
| Average mean absolute pixel difference | 0.849 / 255 |
| Worst-page mean absolute pixel difference | 1.680 / 255 |
| Average share of pixels differing by more than 10 levels | 3.50% |
| Worst-page share of pixels differing by more than 10 levels | 7.32% |

Interpretation: the PNGs are visually faithful. Exact pixel hashes differ because the independent audit used a different rendering path/anti-aliasing profile, but differences are small and consistent with renderer anti-aliasing rather than missing content.

## Figures and tables

| Item type | Result |
|---|---:|
| Figures identified from OCR captions | Figure 1 through Figure 37 |
| Tables identified visually / by OCR | Table 1 and Table 2 |
| Figure visuals preserved | Yes, in page PNGs |
| Table 1 structured transcription | `tables/table_001.md` |
| Table 2 structured transcription | `tables/table_002.md` |
| Rotated visual copy of Table 1 | `assets/derived/page_008_table_rotated.png` |

Note: `figure_table_index.md` is OCR-generated and misses/garbles some caption boundaries. `figure_table_index_verified.md` should be used for the audited summary.

## Equations

The document's numbered equations (1) through (16) are indexed in `verified_equations.md`. These were checked against the rendered page images for the major formula pages.

## Known limitations

- `full_document.md` and `pages/page_###.md` are faithful to the PDF OCR text layer, not to a human-proofread transcription.
- OCR errors remain in prose, especially around Greek letters, subscripts/superscripts, hyphenation, references, and figure/table captions.
- Figures are preserved as page images; the charts/diagrams are not recreated as editable vector graphics or extracted as underlying data.
- Only the two visually identified tables are manually transcribed as structured Markdown tables.
- Formula extraction in `formula_candidates.md` is heuristic; use `verified_equations.md` for numbered equations.

## Recommended use

- Use `assets/page_images/page_###.png` as the visual source of truth.
- Use `full_document.md` / `pages/page_###.md` for navigation and searchable prose.
- Use `verified_equations.md` for formulas.
- Use `tables/` for structured table content.

## Final assessment

Completeness: high for page-level preservation and navigation.  
Visual accuracy: high.  
OCR text accuracy: medium; searchable and mostly usable, but not clean enough to treat as a fully proofread Markdown transcription.  
Structured equation/table accuracy: materially improved for the numbered equations and two main tables.
