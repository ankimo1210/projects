# Hull "Options, Futures, and Other Derivatives" 11e — Agentic Skill Design

- **Date**: 2026-05-29
- **Owner**: kazumasa
- **Source PDF**: `/home/kazumasa/projects/options, futures and other derivatives 11th.pdf` (880 pages, John C. Hull, 11/e Global Edition)
- **Skill name**: `hull-derivatives`
- **Install path**: `~/.claude/skills/hull-derivatives/`

## 1. Purpose

Convert the Hull 11e textbook into a Claude-agent-friendly skill that supports three concurrent use cases:

1. **Implementation support** — Claude references formulas, algorithms, and short Python implementations when writing derivatives code (in `johnhull/`, `stock/`, `rates_volatility_model/`, etc.).
2. **Concept/term reference** — Quick lookup of definitions and key results during conversations.
3. **Chapter-level study notes** — Structured summaries of each chapter for human study.

Out of scope: solving end-of-chapter practice questions; verbatim reproduction of the book.

## 2. Constraints

- **Copyright**: Hull 11e is commercial. Skill contents must be **paraphrased summaries + formulas + algorithms**, not verbatim text. For personal local use only; not redistributed.
- **Budget**: Generation is done by Claude Code reading the PDF chapter-by-chapter (manual sequential). Tokens are a real cost — keep per-chapter output focused.
- **Scope**: All 37 chapters + glossary, treated at uniform depth. No chapter is omitted; none is given disproportionate attention.

## 3. Architecture

### 3.1 Directory layout

```
~/.claude/skills/hull-derivatives/
├── SKILL.md                          # entry point: trigger + how-to-read + topic index
├── references/
│   ├── chapters/                     # 37 chapter summaries (primary extraction output)
│   │   ├── ch01_introduction.md
│   │   ├── ch02_futures_markets.md
│   │   ├── ...
│   │   └── ch37_mishaps.md
│   ├── topics/                       # cross-chapter quick references
│   │   ├── futures_forwards.md       # ch2, 5, 6
│   │   ├── hedging.md                # ch3
│   │   ├── interest_rates.md         # ch4
│   │   ├── swaps.md                  # ch7, 34
│   │   ├── options_basics.md         # ch10, 11, 12, 17, 18
│   │   ├── binomial.md               # ch13, 21
│   │   ├── stochastic_calculus.md    # ch14, 28
│   │   ├── bsm.md                    # ch15
│   │   ├── employee_stock_options.md # ch16
│   │   ├── greeks.md                 # ch19
│   │   ├── vol_smile_surface.md      # ch20
│   │   ├── numerical_methods.md      # ch21, 27
│   │   ├── risk_management.md        # ch22, 23
│   │   ├── credit.md                 # ch8, 9, 24, 25
│   │   ├── exotics.md                # ch26
│   │   ├── ir_derivatives.md         # ch29, 30, 31, 32, 33
│   │   ├── commodity_energy.md       # ch35
│   │   └── real_options.md           # ch36
│   ├── formulas_index.md             # canonical formula list, linked back to chapters/topics
│   └── glossary.md                   # consolidated glossary (Hull's + paraphrased)
├── EXTRACTION_PROGRESS.md            # progress tracker (kept after deploy as audit trail)
└── scripts/
    └── verify_formula.py             # optional: numerical sanity check harness
```

Progressive disclosure: `SKILL.md` is small. Claude loads it on trigger, then follows links into `references/topics/*` (most common) or `references/chapters/*` (deeper context).

### 3.2 SKILL.md frontmatter

```yaml
---
name: hull-derivatives
description: Reference and implementation guide for John Hull's "Options, Futures, and Other Derivatives" (11e). Use when implementing or reasoning about derivatives pricing (Black-Scholes, binomial trees, Greeks), volatility models (smile/surface, local vol, Heston, SABR), interest rate derivatives (HJM, Hull-White, LMM), swaps, futures/forwards, credit/XVA, VaR/ES, or when looking up a derivatives concept/formula/algorithm.
---
```

### 3.3 Chapter file template (`references/chapters/chXX_*.md`)

```markdown
# Ch.XX <Title>

> **Source**: Hull 11e, Chapter XX (pp. nnn-mmm). Paraphrased summary for personal use.

## 1. 要点 (3-5 lines)
## 2. キー用語
- term: short definition

## 3. 主要公式
$$ \text{formula in LaTeX} $$
- symbol definitions

## 4. アルゴリズム / 手順
1. step 1
2. step 2

## 5. Python reference
```python
# numpy/scipy, < 30 lines, runnable
```

## 6. 注意点 / 典型的なミス
- pitfall and why

## 7. 関連トピック
- See: [topics/bsm.md](../topics/bsm.md), Ch.13, Ch.19
```

### 3.4 Topic file template (`references/topics/<topic>.md`)

```markdown
# Topic: <Title>

## 対応章
ch15, ch19, ch20

## クイック公式
- key formula(s) extracted from chapter files (with back-links)

## 実装スニペット
- consolidated reusable Python functions

## デシジョンガイド
- "when to use which" guidance
```

## 4. Data Flow

```
PDF (880 pages)
   │
   ▼  (Claude Code, sequential, ~1 chapter per turn)
chapters/chXX_*.md  ←── primary extraction
   │
   ▼  (after all chapters drafted)
topics/*.md          ←── consolidation, cross-references
formulas_index.md    ←── derived from chapter formula sections
glossary.md          ←── Hull's glossary + cross-references
   │
   ▼
SKILL.md             ←── finalized index + trigger description
```

`EXTRACTION_PROGRESS.md` is updated after each chapter with: status (done/wip/skip), page range read, and any notes about formulas/code that need verification.

## 5. Extraction Workflow

For each chapter:

1. Identify page range from the PDF outline.
2. Read those pages via the `Read` tool with `pages=` parameter.
3. Draft `chXX_*.md` following the template. Constraints:
   - Paraphrase prose; do not copy paragraphs verbatim.
   - All formulas in LaTeX with explicit symbol definitions.
   - Python reference must `import` cleanly and produce a result for at least one example.
4. Update `EXTRACTION_PROGRESS.md`.
5. Commit (optional but recommended every 3-5 chapters).

After all 37 chapters are drafted:

6. Build topic files by reading their listed chapter files and consolidating.
7. Build `formulas_index.md` by scanning chapter `## 3. 主要公式` sections.
8. Build `glossary.md` from Hull's end-of-book glossary, paraphrased.
9. Finalize `SKILL.md` (write the topic index + how-to-use section).

## 6. Definition of Done

Per CLAUDE.md "Definition of Done":

- All 37 chapter files exist and follow the template.
- All topic files exist and link back to chapter files.
- `formulas_index.md` includes every formula listed in chapter `## 3.` sections, with chapter back-links.
- Every Python reference imports and runs (verify with `scripts/verify_formula.py` or ad-hoc).
- At least three Python references are verified against a hand-computed answer:
  - BSM call/put price + put-call parity (ch15).
  - 2-step binomial European call (ch13).
  - Vasicek bond price (ch31) or Hull-White (ch32).
- `SKILL.md` description is tested by running a second Claude Code session with a derivatives prompt and confirming the skill activates.
- `EXTRACTION_PROGRESS.md` shows all chapters complete.

## 7. Risks / Open Questions

- **Token budget**: 37 chapters × ~30 pages each could be expensive if Claude reads full pages every turn. Mitigation: read pages once per chapter, write the summary, do not re-read for adjacent chapters.
- **Formula transcription errors**: Easy to mis-type LaTeX. Mitigation: numerical verification of a curated subset (see DoD).
- **Topic-chapter mismatch**: Chapter-to-topic mapping above is a first guess; some chapters may want to live in multiple topics or none. Adjustments allowed during the consolidation phase.
- **Glossary scope**: Hull's glossary is long. Decision: include all entries but paraphrase to one-line definitions; longer concepts live in topic files.

## 8. Non-goals

- Solving practice questions
- Verbatim text reproduction
- Diagrams / figures (we use formulas + prose only)
- Multi-language code samples (Python only; Rust/etc. can be derived as needed)
- A redistributable package — local use only

## 9. Next Steps

After this spec is approved, invoke the `writing-plans` skill to produce a chapter-by-chapter implementation plan with milestones and review checkpoints.
