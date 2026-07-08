# Verification Report

Generated after a structural and visual audit of the Markdown extraction package.

## Summary

The package is complete as a page-preserving Markdown/PNG extraction: every PDF page is represented by one Markdown file and one rendered page image. The page images are the authoritative source for figures, tables, formulas, and layout.

The package is not a fully verified semantic transcription: the underlying PDF is OCR-based, so the text layer contains OCR errors, especially for formulas and rotated/graphical tables.

## Checks performed

| Check | Result |
|---|---:|
| Source PDF page count | 73 |
| Page Markdown files | 73 |
| Rendered page PNGs | 73 |
| PNG dimensions | 1323 x 1871 for all pages |
| Empty page text blocks | 0 |
| ZIP integrity test | Passed |
| Broken page-image links in page Markdown | 0 |
| Rendered image hash comparison against source render folder | Passed |

## Accuracy notes

- Prose extraction is generally usable, but inherits OCR errors from the source PDF.
- Page 8 contains a rotated table. The OCR text for this page is poor, but the table is visually preserved. A readable rotated image was added at `assets/derived/page_008_table_rotated.png`, and a manual transcription was added at `tables/table_001.md`.
- The original `formula_candidates.md` is heuristic and contains false positives. A manually checked numbered-equation index was added at `verified_equations.md`.
- Table 2 was manually transcribed at `tables/table_002.md`.

## Conclusion

Use `full_document.md` and `pages/page_###.md` for navigation and prose. Use `assets/page_images/page_###.png` as the source of truth for visual fidelity. Use `verified_equations.md` and `tables/` for the most reliable formula/table transcriptions currently included.
