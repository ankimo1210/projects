# Math Foundations Implementation Plan

> **For agentic workers:** Use the approved scope below, preserve concurrent work, and verify each deliverable before completion.

**Goal:** 高校数学を一度学んだ読者が、数学の必要性と面白さを再発見できるHTML教科書の代表3章を完成させる。

**Architecture:** `analytics/math_foundations/` に本文HTML断片、共通テンプレート、CSS、ブラウザ内の数学実験を置く。Python標準ライブラリのビルダーで入口と3章を生成し、CSSとJSを埋め込んでローカルファイルでも動くようにする。既存教材は変更せず、読み進む先としてリンクする。

**Tech Stack:** Python standard library, HTML, MathML, SVG, plain JavaScript, Node built-in test runner. New dependencies: none.

**Spec:** この文書の「承認された設計」と [review handoff](2026-11-07-math-curriculum-review-handoff.md)。ユーザーはHTML中心・任意のノートブック・代表3章の試作を了承し、実装開始を指示した。

## 承認された設計

- 読者の主画面はHTML。Python環境やJupyterを学習の前提にしない。
- 代表章は「数の拡張」「連続性と中間値の定理」「回転と行列・複素数のつながり」。
- 問い、動かせる図、定義の必要性、短い証明、成立条件・反例、コラム、演習・段階ヒント・解答を揃える。
- 面白さと理由は本文に含める。長い形式的議論は任意の補足に置く。
- コラムは本文の概念に接続する。未確認の歴史逸話は採用しない。
- 初回はローカル閲覧。公開、外部送信、新しい本番依存関係の追加は行わない。
- 本文と数学実験は各1つの原本を管理し、HTMLを再生成する。

## Global Constraints

- Japanese prose; English identifiers and code comments.
- Confine implementation to `analytics/math_foundations/`, its entry in `analytics/README.md`, and `analytics/docs/`.
- Preserve the pre-existing untracked review handoff.
- Embed workspace `docs/templates/claude-report/tokens.css`; use its colors without changing it.
- Generated HTML is ignored and rebuildable. No large arrays, images, or new package installation.
- Work in the existing checkout and new directory to preserve other running sessions; do not switch its branch or create/remove worktrees.

## Review Focus

- `file:` opening must work without fetching source JSON, modules, fonts, or math libraries.
- A shrinking bracket alone must not claim a root for a discontinuous step or pole.
- Rotation must preserve length; labels and SVG must remain readable on a 390px screen.
- All math required for an exercise must appear in the chapter; visual experiments are observations rather than proofs.
- Navigation and hint/answer controls must work by keyboard, including with browser JavaScript disabled for prose.

## Tasks

### Task 1 Mathematical experiments

**Files:** `assets/math.js`, `assets/experiments.js`, `tests/math.test.cjs`.
**Interfaces:** Create full accessible labs inside `[data-lab="numbers"]`, `[data-lab="continuity"]`, `[data-lab="rotation"]`. Expose pure math helpers to Node tests and the browser; browser scripts are classic inline scripts.

- [x] Write meaningful tests for known products and quarter-turns, bisection bounds and discontinuity counterexamples, rotation composition/length, invalid input. Run and observe failure before implementation.
- [x] Implement pure helpers and three SVG labs with labelled controls, reset, numeric readouts, clear conditions, no network dependencies.
- [x] Run `node --test analytics/math_foundations/tests/math.test.cjs` and report evidence.

### Task 2 Educational chapters

**Files:** `chapters/numbers.html`, `chapters/continuity.html`, `chapters/rotation.html`.
**Interfaces:** HTML body fragments with section IDs, h2/h3 headings, native MathML, one corresponding `data-lab` host, semantic details/summary for hints and answers. Shell owns h1/nav/footer.

- [x] Write complete readable trial chapters, each with a motivating question, definitions, short proof, conditions/counterexample, optional column, at least 3 exercises with hints and answers, and a final explanation prompt.
- [x] Verify mathematical statements, prerequisites, and column sources. Do not put historical claims without verifying their sources.

### Task 3 Reader shell and reproducible delivery

**Files:** `build.py`, `template.html`, `assets/style.css`, `README.md`, `.gitignore`, `tests/test_build.py`, `analytics/docs/STATUS.md`, `analytics/README.md`.
**Interfaces:** `build(output: Path | None = None) -> list[Path]`; default output `site/`. Four pages: `index.html`, `numbers.html`, `continuity.html`, `rotation.html`. Build reads source fragments and scripts and produces self-contained pages.

- [x] Write and run failing integration tests for complete output, navigation/assets and repeatable build before builder implementation.
- [x] Implement responsive reading shell, chapter navigation and learning map; embed token CSS and labs; no dependency installation.
- [x] Build and run Python/Node checks. Open pages in a browser and verify all labs, hints, navigation, mobile layout, and light/dark appearance. Browser QA used local HTTP; direct file-URL automation was unavailable.
- [x] Obtain an independent review of prose, mathematical behavior and delivery; resolve material findings.
- [x] Record verification and remaining curriculum milestones in STATUS. Deliver a clickable local entry point.
