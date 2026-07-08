# Opt-Var Markdown Export

- Source: `optvar_ocr.pdf`
- Page count: 136
- This export is Markdown-first: text is kept in Markdown/code blocks, while every page is included as an image so formulas, diagrams, charts, and tables are visually preserved.
- OCR text can be noisy, especially for formulas. Use page images as the visual source of truth.

## Structure

- `document.md`: all pages concatenated.
- `pages/page_XXX.md`: page-by-page Markdown.
- `assets/page_images/`: full-page images covering all figures/tables/equations.
- `raw_text/`: OCR text files, including `document_layout.txt` from `pdftotext -layout`.
- `figure_index.md`, `table_index.md`, `equation_candidates.md`: generated indexes with links to page images.

---
