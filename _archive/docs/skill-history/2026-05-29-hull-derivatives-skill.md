# Hull Derivatives Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `hull-derivatives` Claude skill at `~/.claude/skills/hull-derivatives/`, paraphrasing Hull 11e (37 chapters + glossary) into chapter files, topic files, a formulas index, and a glossary, with three verified Python reference implementations.

**Architecture:** Single skill, progressive disclosure. `SKILL.md` is the trigger + index. `references/chapters/` holds 37 chapter summaries (primary extraction). `references/topics/` holds 17 cross-chapter quick references. `formulas_index.md` and `glossary.md` are consolidated lookups. Source: `/home/kazumasa/projects/options, futures and other derivatives 11th.pdf` (880 pp).

**Tech Stack:** Markdown + LaTeX (`$$…$$`). Python 3 with `numpy` / `scipy` for reference implementations. `pypdf` for page reads (via `uv run --with pypdf`). pytest for verification of curated formulas.

---

## File Structure

```
~/.claude/skills/hull-derivatives/
├── SKILL.md
├── EXTRACTION_PROGRESS.md
├── references/
│   ├── chapters/
│   │   ├── ch01_introduction.md  …  ch37_mishaps.md     (37 files)
│   │   ├── _template.md                                  (chapter template)
│   ├── topics/
│   │   ├── futures_forwards.md
│   │   ├── hedging.md
│   │   ├── interest_rates.md
│   │   ├── swaps.md
│   │   ├── options_basics.md
│   │   ├── binomial.md
│   │   ├── stochastic_calculus.md
│   │   ├── bsm.md
│   │   ├── employee_stock_options.md
│   │   ├── greeks.md
│   │   ├── vol_smile_surface.md
│   │   ├── numerical_methods.md
│   │   ├── risk_management.md
│   │   ├── credit.md
│   │   ├── exotics.md
│   │   ├── ir_derivatives.md
│   │   ├── commodity_energy.md
│   │   └── real_options.md
│   │   ├── _template.md                                  (topic template)
│   ├── formulas_index.md
│   └── glossary.md
└── scripts/
    └── verify_formula.py
```

`_template.md` files are stripped before "finalize" (or kept as developer aids — decide at finalize step). The plan keeps them through Task 4, removes them in Task 7.

---

## Constants

- **PDF path** (with spaces, always quote in shell): `"/home/kazumasa/projects/options, futures and other derivatives 11th.pdf"`
- **Skill root**: `~/.claude/skills/hull-derivatives/` → expanded: `/home/kazumasa/.claude/skills/hull-derivatives/`
- **Spec**: `/home/kazumasa/projects/docs/superpowers/specs/2026-05-29-hull-derivatives-skill-design.md`

### Chapter → page range table (PDF pages, 1-indexed)

| ch | title                                                 | pages   | topic(s)                                  |
|----|-------------------------------------------------------|---------|--------------------------------------------|
| 1  | Introduction                                          | 23-45   | (chapters/ only)                           |
| 2  | Futures Markets and Central Counterparties            | 46-69   | futures_forwards                            |
| 3  | Hedging Strategies Using Futures                      | 70-97   | hedging                                    |
| 4  | Interest Rates                                        | 98-123  | interest_rates                              |
| 5  | Determination of Forward and Futures Prices           | 124-151 | futures_forwards                            |
| 6  | Interest Rate Futures                                 | 152-171 | futures_forwards, interest_rates            |
| 7  | Swaps                                                 | 172-200 | swaps                                       |
| 8  | Securitization and the Financial Crisis of 2007-8     | 201-215 | credit                                      |
| 9  | XVAs                                                  | 216-226 | credit                                      |
| 10 | Mechanics of Options Markets                          | 227-246 | options_basics                              |
| 11 | Properties of Stock Options                           | 247-267 | options_basics                              |
| 12 | Trading Strategies Involving Options                  | 268-287 | options_basics                              |
| 13 | Binomial Trees                                        | 288-315 | binomial                                    |
| 14 | Wiener Processes and Itô's Lemma                      | 316-337 | stochastic_calculus                         |
| 15 | The Black-Scholes-Merton Model                        | 338-370 | bsm                                         |
| 16 | Employee Stock Options                                | 371-383 | employee_stock_options                      |
| 17 | Options on Stock Indices and Currencies               | 384-400 | options_basics                              |
| 18 | Futures Options and Black's Model                     | 401-416 | options_basics                              |
| 19 | The Greek Letters                                     | 417-450 | greeks                                      |
| 20 | Volatility Smiles and Volatility Surfaces             | 451-469 | vol_smile_surface                           |
| 21 | Basic Numerical Procedures                            | 470-513 | binomial, numerical_methods                 |
| 22 | Value at Risk and Expected Shortfall                  | 514-541 | risk_management                             |
| 23 | Estimating Volatilities and Correlations              | 542-561 | risk_management                             |
| 24 | Credit Risk                                           | 562-586 | credit                                      |
| 25 | Credit Derivatives                                    | 587-613 | credit                                      |
| 26 | Exotic Options                                        | 614-639 | exotics                                     |
| 27 | More on Models and Numerical Procedures               | 640-669 | numerical_methods                           |
| 28 | Martingales and Measures                              | 670-687 | stochastic_calculus                         |
| 29 | Interest Rate Derivatives: The Standard Market Models | 688-706 | ir_derivatives                              |
| 30 | Convexity, Timing, and Quanto Adjustments             | 707-718 | ir_derivatives                              |
| 31 | Equilibrium Models of the Short Rate                  | 719-731 | ir_derivatives                              |
| 32 | No-Arbitrage Models of the Short Rate                 | 732-754 | ir_derivatives                              |
| 33 | Modeling Forward Rates                                | 755-772 | ir_derivatives                              |
| 34 | Swaps Revisited                                       | 773-784 | swaps                                       |
| 35 | Energy and Commodity Derivatives                      | 785-801 | commodity_energy                            |
| 36 | Real Options                                          | 802-814 | real_options                                |
| 37 | Derivatives Mishaps and What We Can Learn from Them   | 815-826 | (chapters/ only)                           |
| G  | Glossary of Terms                                     | 827-880 | → references/glossary.md                    |

---

## Task 1: Scaffold the skill directory

**Files:**
- Create: `~/.claude/skills/hull-derivatives/SKILL.md` (skeleton)
- Create: `~/.claude/skills/hull-derivatives/EXTRACTION_PROGRESS.md`
- Create: `~/.claude/skills/hull-derivatives/references/chapters/_template.md`
- Create: `~/.claude/skills/hull-derivatives/references/topics/_template.md`
- Create empty dirs: `references/chapters/`, `references/topics/`, `scripts/`

- [ ] **Step 1.1: Create directories**

```bash
mkdir -p ~/.claude/skills/hull-derivatives/references/chapters
mkdir -p ~/.claude/skills/hull-derivatives/references/topics
mkdir -p ~/.claude/skills/hull-derivatives/scripts
```

- [ ] **Step 1.2: Write `SKILL.md` skeleton**

Path: `~/.claude/skills/hull-derivatives/SKILL.md`

```markdown
---
name: hull-derivatives
description: Reference and implementation guide for John Hull's "Options, Futures, and Other Derivatives" (11e). Use when implementing or reasoning about derivatives pricing (Black-Scholes, binomial trees, Greeks), volatility models (smile/surface, local vol, Heston, SABR), interest rate derivatives (HJM, Hull-White, LMM), swaps, futures/forwards, credit/XVA, VaR/ES, or when looking up a derivatives concept/formula/algorithm.
---

# Hull Derivatives Skill

Paraphrased summaries, formulas, algorithms, and short Python reference implementations from Hull "Options, Futures, and Other Derivatives" 11th edition. For personal local use.

## When to use
- Implementing a pricing or risk model (BSM, binomial, MC, Greeks, vol models, IR models)
- Looking up a definition, formula, or algorithm
- Sanity-checking an approach against a textbook standard

## How to read this skill
- For a **concept lookup** → start at `references/topics/<topic>.md`
- For **chapter-level detail** → `references/chapters/chXX_*.md`
- For a **specific formula** → `references/formulas_index.md`
- For a **term definition** → `references/glossary.md`

## Topic index
- (filled in at Task 6)

## Chapter index
- (filled in at Task 6)
```

- [ ] **Step 1.3: Write `EXTRACTION_PROGRESS.md`**

Path: `~/.claude/skills/hull-derivatives/EXTRACTION_PROGRESS.md`

```markdown
# Extraction Progress

Tracks extraction state for the hull-derivatives skill. Updated after each chapter.

Status legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[v]` verified

## Chapters

- [ ] ch01 Introduction (pp. 23-45)
- [ ] ch02 Futures Markets and Central Counterparties (pp. 46-69)
- [ ] ch03 Hedging Strategies Using Futures (pp. 70-97)
- [ ] ch04 Interest Rates (pp. 98-123)
- [ ] ch05 Determination of Forward and Futures Prices (pp. 124-151)
- [ ] ch06 Interest Rate Futures (pp. 152-171)
- [ ] ch07 Swaps (pp. 172-200)
- [ ] ch08 Securitization and the Financial Crisis of 2007-8 (pp. 201-215)
- [ ] ch09 XVAs (pp. 216-226)
- [ ] ch10 Mechanics of Options Markets (pp. 227-246)
- [ ] ch11 Properties of Stock Options (pp. 247-267)
- [ ] ch12 Trading Strategies Involving Options (pp. 268-287)
- [ ] ch13 Binomial Trees (pp. 288-315)
- [ ] ch14 Wiener Processes and Itô's Lemma (pp. 316-337)
- [ ] ch15 The Black-Scholes-Merton Model (pp. 338-370)
- [ ] ch16 Employee Stock Options (pp. 371-383)
- [ ] ch17 Options on Stock Indices and Currencies (pp. 384-400)
- [ ] ch18 Futures Options and Black's Model (pp. 401-416)
- [ ] ch19 The Greek Letters (pp. 417-450)
- [ ] ch20 Volatility Smiles and Volatility Surfaces (pp. 451-469)
- [ ] ch21 Basic Numerical Procedures (pp. 470-513)
- [ ] ch22 Value at Risk and Expected Shortfall (pp. 514-541)
- [ ] ch23 Estimating Volatilities and Correlations (pp. 542-561)
- [ ] ch24 Credit Risk (pp. 562-586)
- [ ] ch25 Credit Derivatives (pp. 587-613)
- [ ] ch26 Exotic Options (pp. 614-639)
- [ ] ch27 More on Models and Numerical Procedures (pp. 640-669)
- [ ] ch28 Martingales and Measures (pp. 670-687)
- [ ] ch29 Interest Rate Derivatives: The Standard Market Models (pp. 688-706)
- [ ] ch30 Convexity, Timing, and Quanto Adjustments (pp. 707-718)
- [ ] ch31 Equilibrium Models of the Short Rate (pp. 719-731)
- [ ] ch32 No-Arbitrage Models of the Short Rate (pp. 732-754)
- [ ] ch33 Modeling Forward Rates (pp. 755-772)
- [ ] ch34 Swaps Revisited (pp. 773-784)
- [ ] ch35 Energy and Commodity Derivatives (pp. 785-801)
- [ ] ch36 Real Options (pp. 802-814)
- [ ] ch37 Derivatives Mishaps and What We Can Learn from Them (pp. 815-826)

## Topics (built after chapters)

- [ ] futures_forwards (ch2, 5, 6)
- [ ] hedging (ch3)
- [ ] interest_rates (ch4, 6)
- [ ] swaps (ch7, 34)
- [ ] options_basics (ch10, 11, 12, 17, 18)
- [ ] binomial (ch13, 21)
- [ ] stochastic_calculus (ch14, 28)
- [ ] bsm (ch15)
- [ ] employee_stock_options (ch16)
- [ ] greeks (ch19)
- [ ] vol_smile_surface (ch20)
- [ ] numerical_methods (ch21, 27)
- [ ] risk_management (ch22, 23)
- [ ] credit (ch8, 9, 24, 25)
- [ ] exotics (ch26)
- [ ] ir_derivatives (ch29, 30, 31, 32, 33)
- [ ] commodity_energy (ch35)
- [ ] real_options (ch36)

## Aggregates

- [ ] formulas_index.md
- [ ] glossary.md
- [ ] SKILL.md finalize
- [ ] Verification (BSM, binomial, Vasicek/HW)
```

- [ ] **Step 1.4: Write chapter template**

Path: `~/.claude/skills/hull-derivatives/references/chapters/_template.md`

```markdown
# Ch.XX <Title>

> **Source**: Hull 11e, Chapter XX (pp. nnn-mmm). Paraphrased summary for personal use.

## 1. 要点
- 3-5 short bullets summarizing the chapter's central ideas

## 2. キー用語
- **term**: short definition (one line)

## 3. 主要公式

### Formula name
$$ \text{formula in LaTeX} $$
- $S$: spot price
- $K$: strike
- (etc.)

## 4. アルゴリズム / 手順
1. step
2. step

## 5. Python reference

```python
import numpy as np
from scipy.stats import norm

def func(...):
    """One-liner."""
    ...
    return ...

# Example
print(func(...))
```

## 6. 注意点 / 典型的なミス
- pitfall and why it matters

## 7. 関連トピック
- See: [topics/<topic>.md](../topics/<topic>.md), Ch.YY, Ch.ZZ
```

- [ ] **Step 1.5: Write topic template**

Path: `~/.claude/skills/hull-derivatives/references/topics/_template.md`

```markdown
# Topic: <Title>

## 対応章
- Ch.XX <title> — [chapters/chXX_*.md](../chapters/chXX_*.md)

## クイック公式

### Formula name
$$ \text{formula} $$
- symbol definitions
- See: chXX §X.X

## 実装スニペット

```python
# Consolidated reusable implementation
```

## デシジョンガイド
- When to use X vs Y
- Common pitfalls when crossing chapters
```

- [ ] **Step 1.6: Commit scaffold**

```bash
cd /home/kazumasa/.claude/skills/hull-derivatives && git init -q 2>/dev/null; true
# Note: This skill dir is not normally a git repo. Commits happen in
# /home/kazumasa/projects (workspace) — the skill itself is shipped via
# the user's ~/.claude. So instead: log progress only.
echo "Scaffold ready: $(date -Iseconds)" >> EXTRACTION_PROGRESS.md
```

Expected: directory exists with SKILL.md, EXTRACTION_PROGRESS.md, and two `_template.md` files. Verify:

```bash
find ~/.claude/skills/hull-derivatives -type f | sort
```

Expected output (5 files):
```
/home/kazumasa/.claude/skills/hull-derivatives/EXTRACTION_PROGRESS.md
/home/kazumasa/.claude/skills/hull-derivatives/SKILL.md
/home/kazumasa/.claude/skills/hull-derivatives/references/chapters/_template.md
/home/kazumasa/.claude/skills/hull-derivatives/references/topics/_template.md
```

(The `Scaffold ready: …` append makes 4 files; the find returns these.)

---

## Task 2 (template): Per-chapter extraction

This task is repeated 37 times, one per chapter. **Do not change the template — substitute the per-chapter variables shown in the table above.**

For chapter XX with title T and pages P_start - P_end:

**Files:**
- Create: `~/.claude/skills/hull-derivatives/references/chapters/chXX_<slug>.md`
- Modify: `~/.claude/skills/hull-derivatives/EXTRACTION_PROGRESS.md` (mark `[~]` then `[x]`)

- [ ] **Step 2.1: Mark in progress**

Edit `EXTRACTION_PROGRESS.md` line for chXX: `- [ ]` → `- [~]`

- [ ] **Step 2.2: Read the chapter pages**

Use the `Read` tool with `pages="P_start-P_end"` on
`/home/kazumasa/projects/options, futures and other derivatives 11th.pdf`.

If the page range exceeds 20 (Read tool max per call), split into two calls:
e.g. ch15 (pp. 338-370) → `pages="338-357"` then `pages="358-370"`.

- [ ] **Step 2.3: Draft `chXX_<slug>.md` from the chapter template**

Path: `~/.claude/skills/hull-derivatives/references/chapters/chXX_<slug>.md`

Use the template at `references/chapters/_template.md` and fill in:
- Title with chapter number and title
- Source line with chapter number and page range
- §1 要点: 3-5 bullets paraphrasing the chapter's main claims
- §2 キー用語: every bold/italicized term introduced in the chapter, 1-line each
- §3 主要公式: every numbered equation in the chapter (Hull numbers them e.g. "(15.20)"). Include the Hull equation number in a comment line: `<!-- Hull eq. (15.20) -->`
- §4 アルゴリズム / 手順: if the chapter presents a procedure (binomial tree build, MC scheme, finite-difference grid), step-list it. If none, write "N/A — conceptual chapter".
- §5 Python reference: short numpy/scipy snippet implementing the chapter's central computation (e.g. ch15 → `bs_call`, `bs_put`; ch13 → `binomial_european`; ch19 → `delta`, `gamma`, `vega`, …). If the chapter is conceptual (ch1, ch8, ch37), write "N/A — conceptual chapter".
- §6 注意点 / 典型的なミス: 2-4 bullets on pitfalls Hull explicitly warns about
- §7 関連トピック: link to the topic file(s) from the table and 2-3 related chapter files

**Paraphrasing rules:**
- Never copy a paragraph verbatim. Express ideas in your own words.
- Mathematical formulas are facts — transcribe them faithfully in LaTeX.
- Examples (numerical worked examples) may be referenced but not reproduced wholesale; instead, summarize the setup and answer.

- [ ] **Step 2.4: Mark done**

Edit `EXTRACTION_PROGRESS.md` line for chXX: `- [~]` → `- [x]`

- [ ] **Step 2.5: Spot-check**

Verify file exists and contains all 7 sections:

```bash
grep -c "^## " ~/.claude/skills/hull-derivatives/references/chapters/chXX_*.md
```

Expected: `7` (sections 1-7).

### Chapter checklist (apply the template above to each)

- [ ] ch01 introduction (pp. 23-45) → `ch01_introduction.md`
- [ ] ch02 futures_markets (pp. 46-69) → `ch02_futures_markets.md`
- [ ] ch03 hedging (pp. 70-97) → `ch03_hedging.md`
- [ ] ch04 interest_rates (pp. 98-123) → `ch04_interest_rates.md`
- [ ] ch05 forward_futures_pricing (pp. 124-151) → `ch05_forward_futures_pricing.md`
- [ ] ch06 ir_futures (pp. 152-171) → `ch06_ir_futures.md`
- [ ] ch07 swaps (pp. 172-200) → `ch07_swaps.md`
- [ ] ch08 securitization (pp. 201-215) → `ch08_securitization.md`
- [ ] ch09 xvas (pp. 216-226) → `ch09_xvas.md`
- [ ] ch10 options_mechanics (pp. 227-246) → `ch10_options_mechanics.md`
- [ ] ch11 option_properties (pp. 247-267) → `ch11_option_properties.md`
- [ ] ch12 option_strategies (pp. 268-287) → `ch12_option_strategies.md`
- [ ] ch13 binomial_trees (pp. 288-315) → `ch13_binomial_trees.md`
- [ ] ch14 wiener_ito (pp. 316-337) → `ch14_wiener_ito.md`
- [ ] ch15 bsm (pp. 338-370) → `ch15_bsm.md`
- [ ] ch16 employee_stock_options (pp. 371-383) → `ch16_employee_stock_options.md`
- [ ] ch17 index_currency_options (pp. 384-400) → `ch17_index_currency_options.md`
- [ ] ch18 futures_options_black (pp. 401-416) → `ch18_futures_options_black.md`
- [ ] ch19 greeks (pp. 417-450) → `ch19_greeks.md`
- [ ] ch20 vol_smile (pp. 451-469) → `ch20_vol_smile.md`
- [ ] ch21 basic_numerical (pp. 470-513) → `ch21_basic_numerical.md`
- [ ] ch22 var_es (pp. 514-541) → `ch22_var_es.md`
- [ ] ch23 vol_corr_estimation (pp. 542-561) → `ch23_vol_corr_estimation.md`
- [ ] ch24 credit_risk (pp. 562-586) → `ch24_credit_risk.md`
- [ ] ch25 credit_derivatives (pp. 587-613) → `ch25_credit_derivatives.md`
- [ ] ch26 exotics (pp. 614-639) → `ch26_exotics.md`
- [ ] ch27 more_models_numerical (pp. 640-669) → `ch27_more_models_numerical.md`
- [ ] ch28 martingales_measures (pp. 670-687) → `ch28_martingales_measures.md`
- [ ] ch29 ir_std_models (pp. 688-706) → `ch29_ir_std_models.md`
- [ ] ch30 convexity_timing_quanto (pp. 707-718) → `ch30_convexity_timing_quanto.md`
- [ ] ch31 equilibrium_short_rate (pp. 719-731) → `ch31_equilibrium_short_rate.md`
- [ ] ch32 noarb_short_rate (pp. 732-754) → `ch32_noarb_short_rate.md`
- [ ] ch33 forward_rate_models (pp. 755-772) → `ch33_forward_rate_models.md`
- [ ] ch34 swaps_revisited (pp. 773-784) → `ch34_swaps_revisited.md`
- [ ] ch35 commodity_energy (pp. 785-801) → `ch35_commodity_energy.md`
- [ ] ch36 real_options (pp. 802-814) → `ch36_real_options.md`
- [ ] ch37 mishaps (pp. 815-826) → `ch37_mishaps.md`

### Commit cadence

After every 5 chapters, commit the workspace spec/plan and any progress notes:

```bash
cd /home/kazumasa/projects
git add docs/superpowers/plans/2026-05-29-hull-derivatives-skill.md
git -c commit.gpgsign=false commit -m "wip(hull-derivatives): extract chXX-chYY" || true
```

(The skill files themselves live outside the workspace repo. Commits to `~/.claude/skills/` are only meaningful if that dir is its own repo. If not, skip — progress is tracked in `EXTRACTION_PROGRESS.md`.)

---

## Task 3 (template): Topic file build

Repeated 17 times, one per topic. Each topic file is derived from its source chapter files (see table above for chapter-to-topic mapping).

**Files:**
- Create: `~/.claude/skills/hull-derivatives/references/topics/<topic>.md`
- Modify: `EXTRACTION_PROGRESS.md` (mark `[x]`)

- [ ] **Step 3.1: Read source chapter files**

Use `Read` on each `chapters/chXX_*.md` listed for the topic.

- [ ] **Step 3.2: Write topic file from topic template**

Path: `~/.claude/skills/hull-derivatives/references/topics/<topic>.md`

Apply `references/topics/_template.md`:
- §対応章: list each source chapter with relative link
- §クイック公式: 3-8 most important formulas across the chapters, with chapter back-links and section refs
- §実装スニペット: 1-3 consolidated, runnable Python functions covering the topic's core computations. May reuse code from chapter files; consolidate, do not duplicate.
- §デシジョンガイド: 2-5 "when X vs Y" bullets for the topic (e.g. "binomial vs trinomial: trinomial for smoother convergence and barrier options; binomial for first-pass")

- [ ] **Step 3.3: Mark done**

Edit `EXTRACTION_PROGRESS.md` for `<topic>`: `[ ]` → `[x]`.

### Topic checklist

- [ ] futures_forwards.md
- [ ] hedging.md
- [ ] interest_rates.md
- [ ] swaps.md
- [ ] options_basics.md
- [ ] binomial.md
- [ ] stochastic_calculus.md
- [ ] bsm.md
- [ ] employee_stock_options.md
- [ ] greeks.md
- [ ] vol_smile_surface.md
- [ ] numerical_methods.md
- [ ] risk_management.md
- [ ] credit.md
- [ ] exotics.md
- [ ] ir_derivatives.md
- [ ] commodity_energy.md
- [ ] real_options.md

---

## Task 4: Build `formulas_index.md`

**Files:**
- Create: `~/.claude/skills/hull-derivatives/references/formulas_index.md`

- [ ] **Step 4.1: Scan all chapter files for `## 3. 主要公式` sections**

```bash
grep -l "^## 3. 主要公式" ~/.claude/skills/hull-derivatives/references/chapters/*.md | sort
```

Expected: 37 paths (one per chapter file).

- [ ] **Step 4.2: Compose `formulas_index.md`**

Path: `~/.claude/skills/hull-derivatives/references/formulas_index.md`

```markdown
# Formulas Index

Every formula listed in any chapter file, grouped by topic. Each entry links back to its source chapter.

## Black-Scholes-Merton
- BS European call: see [ch15 §3](chapters/ch15_bsm.md#3-主要公式) — `<!-- Hull eq. (15.20) -->`
- BS European put: see [ch15 §3](chapters/ch15_bsm.md#3-主要公式) — `<!-- Hull eq. (15.21) -->`
- (etc.)

## Greeks
- Delta: see [ch19 §3](chapters/ch19_greeks.md#3-主要公式)
- (etc.)

## Binomial / lattice
…

## Stochastic calculus
…

## Volatility models
…

## Interest rate models
…

## Risk metrics
…

## Credit
…

## Exotics
…

## Energy / commodity
…
```

Each section enumerates the formulas found in chapter files for that area. Use the topic taxonomy from the table at the top of this plan.

- [ ] **Step 4.3: Mark done**

Edit `EXTRACTION_PROGRESS.md`: `formulas_index.md` → `[x]`.

---

## Task 5: Build `glossary.md`

**Files:**
- Create: `~/.claude/skills/hull-derivatives/references/glossary.md`

- [ ] **Step 5.1: Read Hull's glossary**

Use `Read` with `pages="827-846"` then `pages="847-866"` then `pages="867-880"` on the PDF.

- [ ] **Step 5.2: Write paraphrased glossary**

Path: `~/.claude/skills/hull-derivatives/references/glossary.md`

```markdown
# Glossary

Paraphrased one-line definitions for Hull 11e glossary terms. For longer treatments, follow the link to the topic or chapter file.

## A
- **American option**: An option that can be exercised at any time up to expiration. → See [topics/options_basics.md](topics/options_basics.md), Ch.10.
- **Arbitrage**: A strategy producing a riskless profit from a zero net investment. → Ch.1, Ch.5.

## B
- **Basis**: Spot minus futures price (or the reverse, depending on convention). → Ch.3.
- **Black-Scholes-Merton model**: A continuous-time model for pricing European options on a non-dividend lognormal stock. → [topics/bsm.md](topics/bsm.md), Ch.15.

(…and so on through Z.)
```

Rule: **one line per term, paraphrased**. Cross-link to topic and chapter files.

- [ ] **Step 5.3: Mark done**

Edit `EXTRACTION_PROGRESS.md`: `glossary.md` → `[x]`.

---

## Task 6: Finalize `SKILL.md`

**Files:**
- Modify: `~/.claude/skills/hull-derivatives/SKILL.md` (replace placeholders in §Topic index and §Chapter index)

- [ ] **Step 6.1: Replace `## Topic index` placeholder**

Replace:
```
## Topic index
- (filled in at Task 6)
```

With:
```
## Topic index
- **Futures & forwards** — [topics/futures_forwards.md](references/topics/futures_forwards.md) (ch2, 5, 6)
- **Hedging** — [topics/hedging.md](references/topics/hedging.md) (ch3)
- **Interest rates** — [topics/interest_rates.md](references/topics/interest_rates.md) (ch4, 6)
- **Swaps** — [topics/swaps.md](references/topics/swaps.md) (ch7, 34)
- **Options basics** — [topics/options_basics.md](references/topics/options_basics.md) (ch10, 11, 12, 17, 18)
- **Binomial trees** — [topics/binomial.md](references/topics/binomial.md) (ch13, 21)
- **Stochastic calculus** — [topics/stochastic_calculus.md](references/topics/stochastic_calculus.md) (ch14, 28)
- **Black-Scholes-Merton** — [topics/bsm.md](references/topics/bsm.md) (ch15)
- **Employee stock options** — [topics/employee_stock_options.md](references/topics/employee_stock_options.md) (ch16)
- **Greeks** — [topics/greeks.md](references/topics/greeks.md) (ch19)
- **Vol smile & surface** — [topics/vol_smile_surface.md](references/topics/vol_smile_surface.md) (ch20)
- **Numerical methods** — [topics/numerical_methods.md](references/topics/numerical_methods.md) (ch21, 27)
- **Risk management** — [topics/risk_management.md](references/topics/risk_management.md) (ch22, 23)
- **Credit** — [topics/credit.md](references/topics/credit.md) (ch8, 9, 24, 25)
- **Exotics** — [topics/exotics.md](references/topics/exotics.md) (ch26)
- **IR derivatives** — [topics/ir_derivatives.md](references/topics/ir_derivatives.md) (ch29, 30, 31, 32, 33)
- **Commodity & energy** — [topics/commodity_energy.md](references/topics/commodity_energy.md) (ch35)
- **Real options** — [topics/real_options.md](references/topics/real_options.md) (ch36)
```

- [ ] **Step 6.2: Replace `## Chapter index` placeholder**

Replace:
```
## Chapter index
- (filled in at Task 6)
```

With a 37-line list:
```
## Chapter index
- Ch.1 [Introduction](references/chapters/ch01_introduction.md)
- Ch.2 [Futures Markets & CCPs](references/chapters/ch02_futures_markets.md)
- Ch.3 [Hedging Strategies Using Futures](references/chapters/ch03_hedging.md)
- Ch.4 [Interest Rates](references/chapters/ch04_interest_rates.md)
- Ch.5 [Forward and Futures Prices](references/chapters/ch05_forward_futures_pricing.md)
- Ch.6 [Interest Rate Futures](references/chapters/ch06_ir_futures.md)
- Ch.7 [Swaps](references/chapters/ch07_swaps.md)
- Ch.8 [Securitization & the Financial Crisis](references/chapters/ch08_securitization.md)
- Ch.9 [XVAs](references/chapters/ch09_xvas.md)
- Ch.10 [Mechanics of Options Markets](references/chapters/ch10_options_mechanics.md)
- Ch.11 [Properties of Stock Options](references/chapters/ch11_option_properties.md)
- Ch.12 [Trading Strategies Involving Options](references/chapters/ch12_option_strategies.md)
- Ch.13 [Binomial Trees](references/chapters/ch13_binomial_trees.md)
- Ch.14 [Wiener Processes and Itô's Lemma](references/chapters/ch14_wiener_ito.md)
- Ch.15 [Black-Scholes-Merton](references/chapters/ch15_bsm.md)
- Ch.16 [Employee Stock Options](references/chapters/ch16_employee_stock_options.md)
- Ch.17 [Options on Stock Indices and Currencies](references/chapters/ch17_index_currency_options.md)
- Ch.18 [Futures Options and Black's Model](references/chapters/ch18_futures_options_black.md)
- Ch.19 [The Greek Letters](references/chapters/ch19_greeks.md)
- Ch.20 [Volatility Smiles and Surfaces](references/chapters/ch20_vol_smile.md)
- Ch.21 [Basic Numerical Procedures](references/chapters/ch21_basic_numerical.md)
- Ch.22 [Value at Risk and Expected Shortfall](references/chapters/ch22_var_es.md)
- Ch.23 [Estimating Volatilities and Correlations](references/chapters/ch23_vol_corr_estimation.md)
- Ch.24 [Credit Risk](references/chapters/ch24_credit_risk.md)
- Ch.25 [Credit Derivatives](references/chapters/ch25_credit_derivatives.md)
- Ch.26 [Exotic Options](references/chapters/ch26_exotics.md)
- Ch.27 [More on Models and Numerical Procedures](references/chapters/ch27_more_models_numerical.md)
- Ch.28 [Martingales and Measures](references/chapters/ch28_martingales_measures.md)
- Ch.29 [IR Derivatives: Standard Market Models](references/chapters/ch29_ir_std_models.md)
- Ch.30 [Convexity, Timing, Quanto Adjustments](references/chapters/ch30_convexity_timing_quanto.md)
- Ch.31 [Equilibrium Models of the Short Rate](references/chapters/ch31_equilibrium_short_rate.md)
- Ch.32 [No-Arbitrage Models of the Short Rate](references/chapters/ch32_noarb_short_rate.md)
- Ch.33 [Modeling Forward Rates](references/chapters/ch33_forward_rate_models.md)
- Ch.34 [Swaps Revisited](references/chapters/ch34_swaps_revisited.md)
- Ch.35 [Energy and Commodity Derivatives](references/chapters/ch35_commodity_energy.md)
- Ch.36 [Real Options](references/chapters/ch36_real_options.md)
- Ch.37 [Derivatives Mishaps](references/chapters/ch37_mishaps.md)
```

- [ ] **Step 6.3: Add `## Formulas index` and `## Glossary` links**

Append after the chapter index:
```
## Other references
- [Formulas index](references/formulas_index.md) — every formula, with chapter back-links
- [Glossary](references/glossary.md) — one-line term definitions
```

- [ ] **Step 6.4: Mark done**

Edit `EXTRACTION_PROGRESS.md`: `SKILL.md finalize` → `[x]`.

---

## Task 7: Cleanup `_template.md` files

**Files:**
- Delete: `references/chapters/_template.md`, `references/topics/_template.md`

- [ ] **Step 7.1: Decide whether to keep templates**

If the user wants to keep templates as developer aids, skip this task. Otherwise:

```bash
rm ~/.claude/skills/hull-derivatives/references/chapters/_template.md
rm ~/.claude/skills/hull-derivatives/references/topics/_template.md
```

Default: keep (they document the chapter/topic schema and cost nothing).

---

## Task 8: Verification

**Files:**
- Create: `~/.claude/skills/hull-derivatives/scripts/verify_formula.py`

- [ ] **Step 8.1: Write `verify_formula.py`**

Path: `~/.claude/skills/hull-derivatives/scripts/verify_formula.py`

```python
"""Numerical sanity checks for hull-derivatives chapter references.

Run with: uv run --with numpy --with scipy python verify_formula.py
"""
import math
import numpy as np
from scipy.stats import norm


# --- ch15: Black-Scholes-Merton -------------------------------------------------

def bs_call(S, K, r, q, sigma, T):
    """European call on a continuous-dividend lognormal stock."""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)


def bs_put(S, K, r, q, sigma, T):
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)


def test_bsm_put_call_parity():
    """C - P = S*e^{-qT} - K*e^{-rT}."""
    S, K, r, q, sigma, T = 100.0, 100.0, 0.05, 0.02, 0.20, 1.0
    c = bs_call(S, K, r, q, sigma, T)
    p = bs_put(S, K, r, q, sigma, T)
    lhs = c - p
    rhs = S * np.exp(-q * T) - K * np.exp(-r * T)
    assert abs(lhs - rhs) < 1e-10, f"parity violated: {lhs} vs {rhs}"
    print(f"[ch15] BSM put-call parity OK   C={c:.4f} P={p:.4f} C-P={lhs:.6f} ~ {rhs:.6f}")


# --- ch13: Binomial tree ------------------------------------------------------

def binomial_european_call(S, K, r, sigma, T, N):
    dt = T / N
    u = math.exp(sigma * math.sqrt(dt))
    d = 1 / u
    p = (math.exp(r * dt) - d) / (u - d)
    disc = math.exp(-r * dt)
    # terminal prices
    j = np.arange(N + 1)
    ST = S * (u ** (N - j)) * (d ** j)
    V = np.maximum(ST - K, 0.0)
    for _ in range(N):
        V = disc * (p * V[:-1] + (1 - p) * V[1:])
    return V[0]


def test_binomial_converges_to_bsm():
    S, K, r, sigma, T = 100.0, 100.0, 0.05, 0.20, 1.0
    bsm = bs_call(S, K, r, 0.0, sigma, T)
    binom = binomial_european_call(S, K, r, sigma, T, N=500)
    err = abs(binom - bsm)
    assert err < 0.05, f"binomial too far from BSM: {err:.4f}"
    print(f"[ch13] Binomial → BSM   BSM={bsm:.4f} Binomial(N=500)={binom:.4f} err={err:.4f}")


# --- ch31: Vasicek bond price -------------------------------------------------

def vasicek_bond_price(r0, a, b, sigma, t, T):
    """Zero-coupon bond price under dr = a(b - r) dt + sigma dW.

    P(t,T) = A(t,T) * exp(-B(t,T) * r0).
    """
    tau = T - t
    B = (1 - math.exp(-a * tau)) / a
    A = math.exp(
        (B - tau) * (a**2 * b - sigma**2 / 2) / a**2
        - (sigma**2 * B**2) / (4 * a)
    )
    return A * math.exp(-B * r0)


def test_vasicek_at_t_equals_T():
    """At t=T the bond pays 1."""
    p = vasicek_bond_price(0.03, 0.1, 0.04, 0.01, t=1.0, T=1.0)
    assert abs(p - 1.0) < 1e-10, f"P(T,T) != 1: {p}"
    p1 = vasicek_bond_price(0.03, 0.1, 0.04, 0.01, t=0.0, T=1.0)
    assert 0.9 < p1 < 1.0, f"1Y Vasicek bond out of expected range: {p1}"
    print(f"[ch31] Vasicek P(T,T)=1 OK; P(0,1)={p1:.4f}")


if __name__ == "__main__":
    test_bsm_put_call_parity()
    test_binomial_converges_to_bsm()
    test_vasicek_at_t_equals_T()
    print("All Hull reference checks passed.")
```

- [ ] **Step 8.2: Run verification**

```bash
cd ~/.claude/skills/hull-derivatives/scripts && uv run --with numpy --with scipy python verify_formula.py
```

Expected output (last 4 lines, approximate values):
```
[ch15] BSM put-call parity OK   C=9.2270 P=6.3000 C-P=2.927… ~ 2.927…
[ch13] Binomial → BSM   BSM=10.4506 Binomial(N=500)≈10.45 err<0.05
[ch31] Vasicek P(T,T)=1 OK; P(0,1)=0.97…
All Hull reference checks passed.
```

(Exact numbers may shift slightly; the pass/fail condition is in the asserts.)

- [ ] **Step 8.3: Mark verified**

Edit `EXTRACTION_PROGRESS.md`: `Verification (...)` → `[v]`.

---

## Task 9: Final commit

- [ ] **Step 9.1: Commit plan + spec to workspace**

The skill files live in `~/.claude/skills/`, not the workspace. Only the design + plan documents are committed to the workspace repo.

```bash
cd /home/kazumasa/projects
git add docs/superpowers/specs/ docs/superpowers/plans/
git status --short
# Should show the spec and plan as added/modified.
git -c commit.gpgsign=false commit -m "$(cat <<'EOF'
docs(superpowers): hull-derivatives skill plan + final progress

EOF
)" || echo "nothing to commit"
```

- [ ] **Step 9.2: Smoke test the skill (manual)**

Open a new Claude Code session in another project (e.g. `stock/` or `johnhull/`). Ask: "How do I price a European put with continuous dividend yield?". The skill should activate (you'll see "Using hull-derivatives…" or equivalent in the SKILL tool invocation) and Claude should reference the `topics/bsm.md` or `chapters/ch15_bsm.md` file.

If it doesn't activate, refine the `description:` field in SKILL.md.

---

## Self-Review

Performed at write-time:

**1. Spec coverage**
- Purpose 1 (implementation support): Task 2 §5 Python references + Task 3 §実装スニペット ✓
- Purpose 2 (concept/term reference): Task 5 glossary, Task 4 formulas index ✓
- Purpose 3 (chapter-level study notes): Task 2 chapter files ✓
- Copyright constraint (paraphrase): Task 2 step 2.3 paraphrasing rules ✓
- 37 chapters uniform depth: Chapter checklist in Task 2 ✓
- Approach C directory structure: Task 1 ✓
- 17 topics: Topic checklist in Task 3 (matches spec, with `employee_stock_options` included) ✓
- DoD (BSM parity, binomial, Vasicek): Task 8 ✓
- SKILL.md trigger test: Task 9.2 ✓

**2. Placeholder scan**
- No "TBD", no "TODO" without resolution.
- "Add appropriate error handling" — not present.
- "Implement later" — not present.
- Each step has either exact code or exact bash + expected output.

**3. Type consistency**
- `bs_call(S, K, r, q, sigma, T)` is consistent across Task 2 (ch15) and Task 8 verification.
- `binomial_european_call` signature in Task 8 is internal; Task 2 ch13 reference may use a slightly different signature (allowed — chapter file is a separate snippet from the verification harness).
- Function names in verification script (`bs_call`, `bs_put`, `binomial_european_call`, `vasicek_bond_price`) are introduced in Task 8 itself, no upstream mismatch.

**4. Ambiguity**
- "If the chapter is conceptual (ch1, ch8, ch37), write 'N/A — conceptual chapter'" — explicit list given.
- "Every 5 chapters, commit" — explicit cadence.
- Per-chapter file naming (`chXX_<slug>.md`) — slug enumerated in the chapter checklist.
- Section count check (`grep -c "^## "` → 7) — explicit pass condition.

Plan is internally consistent and traces to the spec.

---

## Execution

After saving, dispatch with `superpowers:executing-plans` (inline) or `superpowers:subagent-driven-development` (subagent-per-task). Given the size (37 chapter tasks + 17 topic tasks + aggregates), **subagent-driven is strongly preferred** to keep main-session context manageable.
