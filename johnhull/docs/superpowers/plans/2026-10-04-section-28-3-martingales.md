# M28 Martingale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** P3全37節を完了する工程で§28.3を受け入れP3 3/37へ進める。
**Architecture:** private比過程の計算、独立math参照、条件付きMC、hash保護の共有4図、新6B、D1/台帳/実画面gate。
**Tech Stack:** 既存uv runtime/NumPy/SciPy/Plotly/nbformat/Jupyter Book/Playwright/C:/F:。追加依存なし。
**Spec:** johnhull/docs/superpowers/specs/2026-10-04-section-28-3-martingales.md

## Global Constraints

- 符号付き同一Wienerのa=mu_f−mu_g+s_g(s_g−s_f)、有限時間GBMの条件付きmeanと第二モーメント。零drift一般化/時点0だけの証明を禁止。
- 非正ratio/負horizonはbroadcast前拒否。有限実数/empty batch/broadcast/float or ndarray、complex/非有限/overflow/正値平均underflow拒否。公開API/依存を不変。
- 6市場/9条件付きfixture/262144×9MC/同一callのQ/G直接求積。API1e−12、求積1e−9、MC5SE、保存4/実API4変異拒否。
- 旧235セル保持、新11/計246、6B.1–6B.6/4図、190図/exotics78、16状態/図幅700px。
- 27D1/両保管庫/MT01–06の5軸、28/278/P3 3/37。P3残りの全要件は引き続き対象。

## Review Focus

1. 比のItô補正の符号、λ=s_gと金利r、signed係数をvolatility絶対値と混同していないか。
2. 条件付き検査が複数時刻/状態と可積分性を持ち、零driftや時点0平均のみから一般martingaleを主張していないか。
3. 同じcall給付を両測度で評価し、random G_Tの分母/measure drift/自己正規化を誤っていないか。
4. empty batchにより負horizon/非正ratioが隠れず、complex/overflowを拒否するか。
5. 保存結果改変/不完全hash/旧235本文出力/27D1と片側保管庫欠損を受入更新前に拒否するか。

### Task 1: 比のAPI・独立参照・数値gate

**Files:** _martingales.py/test_martingales.py、build_martingale_reference.py/verify_martingale_numerics.pyとtests、section-28-3/reference/numerical-check。
**Interfaces:** ratio_drift/ratio_conditional_mean/numeraire_drifts、cases/conditional/pricing/figure、APIとMC結果hash。
- [x] Step 1: `ratio_drift(-.02,.08,.3,-.2)==approx(0)`、誤measure/条件付きstate/batch/不正値/空batch拒否tests。Expected: missing module FAIL。
- [x] Step 2: 3計算を実装。Expected: 全API tests PASS。
- [x] Step 3: math参照/9MC/2求積/結果hash、保存/実API変異検査。Expected: 数値/独立buildertestsと2--check PASS。
- [x] Step 4: commit `Implement conditional GBM martingale checks`、task-done。Expected: 対象tests PASS。

### Task 2: 共有教材と旧235セル保持

**Files:** _martingale_lesson.py/tests、build_exotics_notebook.py/exotics.ipynb、verify_martingale_notebook.py/tests、歴史notebook tests、依存宣言。
**Interfaces:** 4martingale_*keys、START##6B/END##7、親6B/6小節、246cells。
- [ ] Step 1: 4図/結果改変hash/旧235保持tests。Expected: missing lesson/gate FAIL。
- [ ] Step 2: 6B.1定義/追加条件、6B.2Itô導出、6B.3条件付き解析、6B.4条件付きMC、6B.5価格恒等式、6B.6限界/後続の11cellsと共有4図。Expected: 旧235保持/保存4図一致。
- [ ] Step 3: fresh全文実行/notebook4改変/旧節pytest除去は新6Bのみ。Expected: lesson/notebook/歴史tests PASS。
- [ ] Step 4: commit `Teach conditional martingales and numeraire identity`、task-done。Expected: 全PASS。

### Task 3: Book・portal・実画面

**Files:** registry/count/index/README/manifest、verify_martingale_browser.cjs、16画像。
**Interfaces:** 新4cards、190図/exotics78、全trace/MathJax/16matrix。
- [ ] Step 1: 4図registry test。Expected: 未登録FAIL。
- [ ] Step 2: 登録/件数、4図full rowと幅保証。Expected: registry/build tests PASS。
- [ ] Step 3: Book/portal build、browser16状態、1000px目視。Expected: 全PASS。
- [ ] Step 4: commit `Verify martingale lessons on both surfaces`、task-done。Expected: 全PASS。

### Task 4: 27D1・台帳・最終レビュー・統合

**Files:** build_martingale_acceptance_record.py/update_martingale_ledger.py/tests、27D1、SECTION_28_3_ACCEPTANCE/REVIEW、ROADMAP/VALIDATION/EVIDENCE_POLICY/台帳。
**Interfaces:** m28-check、27採用D1path/hash、MT01–MT06/28件。
- [ ] Step 1: mandatory source/artifact/hash/両保管庫/path/更新失敗台帳不変tests。Expected: missing gate FAIL。
- [ ] Step 2: cleanTask3から27D1再検査、直接redrawn基準reuse、28.2初回redraw。Expected: runtime/browser/pytest/復元PASS。
- [ ] Step 3: 現行hashの統合gateと台帳/受入/docs更新、4--check/ruff/全suite/台帳成果物。Expected: 28/278/全PASS。
- [ ] Step 4: commit受入/task-done、1名fresh review、重要指摘RED→GREEN+全suite、minor/ruling記録。Expected: mergeを止める指摘なし。
- [ ] Step 5: 記録保存、tracked release/main統合後検証/push、P3次§28.4へ継続。Expected: live remote一致、P3目標active、末尾P0–P8。
