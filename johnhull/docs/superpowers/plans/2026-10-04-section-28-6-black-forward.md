# M31 Black Forward Model Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** §28.6全要求の5軸受入、P3 6/37。全37節の目標を継続。
**Architecture:** private Black/HoLee joint Gaussian + independent Q/T quad/rawMC/importance + §6E/4図 +30D1/全5軸。
**Tech Stack:** existing NumPy/SciPy/Plotly/nbformat/Book/Playwright/C-F stores、依存追加なし。
**Spec:** johnhull/docs/superpowers/specs/2026-10-04-section-28-6-black-forward.md

## Global Constraints

原典680–681式28.26–29/BF01–06、給付/forward同じT、Tlognormal仮定/可積分性、Q経路割引、forward/futures/spotvolの区別、consumption市場forwardを保持。source印刷pinなし。private/no public changes、old268/new11/279、202fig/90exotics/private35/152warningsはactual確認。30D1/両stores/31受入275未評価/P3 6/37、whole/1freshreview/重要RED→GREEN1pass/minor保留/mainpush。zero-hit stochasticMCはimportance route、保存MC joint再署名を消費時にfixedseed完全照合。

## Review Focus

1. T numeraire/同じ満期/28.26–29、forwardとfutures/spotvol、Q経路割引とT外側DFの同一価格。
2. Gaussian J/Y covariance・Brownian bridge・PSD端・negative rates/DF>1・T0、varianceの安定性と価格tails/tinyATM。
3. 型/temporal/混合bool/domain/emptybatch/leadingbroadcast、ゼロσ/Tと表現限界、既存公開Blackの契約保持。
4. zero-hit stochasticMCのimportance rawlikelihood/seed/SE、独立quad/tail/変異、joint保存改変の消費拒否、旧268/16表示/全30D1/currentproducerinventory/両stores/台帳前拒否。

### Task 1: private Black and independent numerical gate

**Files:** _forward_black.py/tests、build_forward_black_reference.py/verify_forward_black_numerics.py、section-28-6 JSON、MODEL_INDEX。
**Interfaces:** specの2signatures/10statskeys、7market42価格/provided3/limits12、density/mean/variance/price、fixedseed rawMC/importance。
- [ ] Step 1: pure math/API/type/batch/tail testsとteacher契約を先に実行。Expected: missing module/builder FAIL。
- [ ] Step 2: private実装、Gaussian covariance/PSD-safe variance/T0/Black境界、教師/数値/MC/負例を照合。Expected: 固定許容内PASS。
- [ ] Step 3: 保存source/results/seed/sample等を検査しmodel index更新、commit/task-done。Expected: 対象testsと--check/ruff PASS。

### Task 2: lesson and Book/portal

**Files:** private lesson/tests、builder/notebook/source契約、registry/browser/notebook verifiers、CSS。
**Interfaces:** Task1の全結果/source/digest/order/uncertaintyを検査し、独立再計算結果だけを表示。
- [ ] Step 1: lesson/4図/旧268保存を先にtests。Expected: missing lesson/registry/notebook FAIL。
- [ ] Step 2: 6E6小節/11cells/4sharedfigsを実装しfresh全文。Expected: 全279/旧268本文・出力・Plotly保存PASS。
- [ ] Step 3: registry/16状態/MathJax/700px/数値・SE・変異・目視、commit/task-done。Expected: 全PASS。

### Task 3: acceptance, regression, review and main

**Files:** integratedgate/updater/tests、30D1、acceptance/review/ledger/ROADMAP/P3_STATUS。
**Interfaces:** currentproducer必須hashを保存record自身から導出せず、BF01–06全5軸、更新前gate。
- [ ] Step 1: missing/stale/resigned/source/path/store/matrix/failure-before-write tests。Expected: missing gate FAIL。
- [ ] Step 2: cleancommitから30D1/currenthash/両stores、31/275/P3 6/37、whole/ruff/release。Expected: 全PASS。
- [ ] Step 3: sole fresh finalreview/重要RED→GREEN+whole/minorと全ruling保存。Expected: merge阻害なし。
- [ ] Step 4: mainFF/fresh/push/live/task-done、次M32。Expected: remote一致、wholeP3 active。

## Exact verification commands

Task 1 final: `python -m pytest johnhull/hullkit/tests/test_forward_black.py johnhull/hullkit/tests/test_forward_black_numerics.py johnhull/hullkit/tests/test_model_index.py -q`. Also run both `build_forward_black_reference.py --check` and `verify_forward_black_numerics.py --check`; ruff the changed Python files.

Task 2 final: Task 1 files plus `test_forward_black_lesson.py`, report `test_forward_black_registry.py`, `test_forward_black_notebook.py`, and previous notebook preservation tests.

Task 3 final: lesson, acceptance_record, ledger_update, section_ledger targeted files. Before final review and on main, `python -m pytest johnhull/hullkit/tests johnhull/report/tests -q`, all four section checks, ruff changed files, `verify_section_ledger.py --check-artifacts`, `verify_release.py --require-tracked`, full Book/portal builds, and actual live remote equality.

