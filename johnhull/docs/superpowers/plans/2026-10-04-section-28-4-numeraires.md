# M29 Numeraire Choices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** P3全37節を完了する工程で§28.4を受け入れ、P3 4/37へ進める。
**Architecture:** 原典12要点・Q OU状態整合・private exact joint Gaussian・独立求積/MC・6C/4図・28D1・5軸台帳。
**Tech Stack:** 既存NumPy/SciPy/Plotly/nbformat/Book/Playwright/両保管庫。追加依存なし。
**Spec:** johnhull/docs/superpowers/specs/2026-10-04-section-28-4-numeraires.md

## Global Constraints

- 原典式28.16–28.25/脚注5,6、path discount、futures vs forward、term fixing/payment、overnight realizing/payment、V projection/A OISを全て保持。印刷価格pinはなし、合成fixtureを明示。
- 既存HWのdocumented Q zero-mean OU状態を守り-B*c(t)を独立条件付きintegral/towerで照合。公開signature/依存を変更しない。
- 旧246本文/出力/Plotly、16新表示状態、28D1/両保管庫、29/277/P3 4/37、全suite/1fresh review/重要RED→GREEN/main push。

## Review Focus

1. Q OU stateとforward中心state、HW bondとintegrated rateの整合、既存価格APIへの影響。
2. 同じ給付・確率割引・tilted Gaussian、futures/forwardとfixing/payment/overnightの時点規約。
3. annuityのnumeraireとprojection V/discount A、条件付き多時刻/状態・sigma0・負rate・有限実数/temporal型/単位・退化Gaussian。
4. 独立参照/API変異/保存結果の消費検査、旧246保存、全28D1/両保管庫/16状態/台帳更新前拒否。

### Task 1: documented HW stateと条件付き債券の整合

**Files:** hullkit/src/hullkit/hull_white.py、hullkit/tests/test_numeraire_hw_state.py、既存test_hull_white.py。
**Interfaces:** hw_discount_bondのsignature/ Q zero-mean OU xを保持。phi=f0+c, c=σ²(1-exp(-at))²/(2a²)。
- [x] Step 1: 定数曲線4%、a=.2/σ=.02、(.25,2,-.015)/(.75,4,0)/(2,5,.01)の独立integral priceとQ tower tests。Expected: 現行式FAIL。
- [x] Step 2: bond exponentへ-B*c(t)を追加し、Q状態のdocstringとcurve-fitを照合。Expected: 新4+既存HW tests PASS。
- [x] Step 3: Jamshidian/ZCB option/較正の独立整合と既存利用箇所への影響を確認。Expected: 既存のdocumented Q契約を維持。
- [x] Step 4: commitとtask-done。Expected: 対象tests PASS、M29未受入を明示。

### Task 2: 独立joint Gaussian・測度数値gate

**Files:** private _numeraire_choices.py/tests、build_numeraire_reference.py/verify_numeraire_numerics.pyとsection-28-4 JSON。
**Interfaces:** 状態/積分率/stock driverのmoments、tilted mean/cov、same payoffとconditional payment/annuity mixtures。詳細API/fixture/許容差はTask1結果とsource designからpre-flightで確定し記録。
- [x] Step 1: 独立source12要求/求積fixture、入力/単位/退化/条件付き・wrongmeasure tests。Expected: missing module FAIL。
- [x] Step 2: exact moments/private APIs/Q・T・payment・annuity数値照合。Expected: synthetic独立求積/MCとAPI許容差PASS。
- [x] Step 3: 実API/保存変異拒否、commit/task-done。Expected: 全controls PASS。

### Task 3: 6C教材・4共有図・Book/portal

**Files:** private lesson、builder/notebook、保存/消費/registry/browsertests、source declarations。
- [ ] Step 1: source12要点を6小節へ割当、消費結果/旧246保持tests。Expected: 新lesson未存在FAIL。
- [ ] Step 2: 新教材/4図とfresh全文、既存sectiontests適応。Expected: source/output/plot保持。
- [ ] Step 3: registry/count/Book/portal/16状態/MathJax/700px/目視。Expected: 全PASS。
- [ ] Step 4: commit/task-done。Expected: 全PASS。

### Task 4: 28D1・台帳・最終レビュー・統合

**Files:** 統合gate/ledger updaterとtests、28D1、受入/review/ROADMAP/P3_STATUS。
- [ ] Step 1: fail-before-write/source/artifact/両保管庫/path/matrix tests。Expected: gate未存在FAIL。
- [ ] Step 2: cleancommitから28D1、source12要点をNC01–06/5軸へ照合、全suite。Expected: 29/277/P3 4/37。
- [ ] Step 3: 1fresh finalreview、重要RED→GREEN+全suite、minor/ruling保存。Expected: merge阻害なし。
- [ ] Step 4: main統合後検証/push、次§28.5へ。Expected: live remote一致、P3全体active。
