# M30 Multiple-Factor Martingales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §28.5全要求を受入、P3 5/37へ。全37節の完了目標を継続。
**Architecture:** private correlated/independent Itô + independent quad/conditional/rawMC + §6D/4図 +29D1/5軸。
**Tech Stack:** existing NumPy/SciPy/Plotly/nbformat/Book/Playwright/C/F stores, no new dependency.
**Spec:** johnhull/docs/superpowers/specs/2026-10-04-section-28-5-multifactor.md

## Global Constraints

原典pp679–680/脚注7/MF01–06、同じbasis/ signedloadings/相対対数drift/true local distinctionを保持。相関PSD退化・C inverse不要。公開API/依存なし。数値合成/印刷pinsなし、旧257保存/16表示/29D1/30受入276未評価/P3 5/37。全suite/1freshreview/重要RED→GREEN/main push。

## Review Focus

1. 独立/相関座標のloadingとrisk-price、Itô cross covariance、PSD退化/基底回転の同じ給付価格。
2. 条件付きobserved ratio/将来増分/有限GBM可積分性、raw RN方向、確率numeraireとQ/G価格。
3. final factoraxisとbatch、非有限/temporal/型/不正domainのemptybatch回避、PSD/tolerance/overflow/positive underflow。
4. 独立参照/変異/保存値消費、旧257/fresh全文、16状態/全29D1/両保管庫/台帳更新前拒否。

### Task 1: factor calculus and independent numerical gate

**Files:** private module/tests、build_multifactor_reference.py/verify_multifactor_numerics.py、section-28-5 JSON。
**Interfaces:** Specの4private signatures、C singleNxN/loadingfinalN、observedratio/finiteconditionalh、独立11市場132状態と同一call Q/G/rotation。
- [x] Step 1: 独立教師を固定しinput/moment/covariance/rotation testsを先に実行。Expected: missing module FAIL。
- [x] Step 2: private実装/厳密GBM conditional moments、price同一給付/直接MCを照合。Expected: 閾値内PASS。
- [x] Step 3: API/保存変異拒否と63fixtureのような元要求数誤流用を防ぐsource manifest、commit/task-done。Expected: 全controls/対象tests PASS。

### Task 2: lesson and Book/portal

**Files:** private lesson/tests、builder/notebook/source contracts、registry/browser/notebook verifiers。
**Interfaces:** numeric recordのsource/result shape/digest/independentvalueを消費時検査。
- [x] Step 1: lesson/new4fig/旧257 tests。Expected: missing lesson FAIL。
- [x] Step 2: 6D6小節/11cellsと4図を実装しfresh全文。Expected: 旧source/output/Plotly保存。
- [x] Step 3: registrycount/16状態/MathJax/700px/目視、commit/task-done。Expected: 全PASS。

### Task 3: acceptance, regression, review and main

**Files:** integratedgate/updater/tests、29D1、acceptance/review/ledger/ROADMAP/P3_STATUS。
- [ ] Step 1: missing/stale/resigned-source/artifact/path/store/matrix fail-before-write tests。Expected: gate missing FAIL。
- [ ] Step 2: cleancommitから29D1/両保管庫、MF01–06全5軸、30/276/P3 5/37、全suite/ruff/release。Expected: 全PASS。
- [ ] Step 3: 1fresh finalreview/重要RED→GREEN+whole、minor/ruling保存。Expected: merge阻害なし。
- [ ] Step 4: mainFF/検証/push/task-done、次M31。Expected: live remote一致、全P3active。
