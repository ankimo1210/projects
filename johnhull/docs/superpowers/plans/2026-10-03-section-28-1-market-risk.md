# M26 Market Price of Risk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §28.1の原典要求・数値・教材・両配布画面を受け入れ、P3の1/37節を完了する。

**Architecture:** 専用risk_premium API、hullkit非依存の参照、hash検査付き共有lesson、notebook/ブラウザ/受入gate。既存213セルを保持し、共通のpipelineで旧25節も再検査する。

**Tech Stack:** 共有uv venv、NumPy/SciPy、Plotly/nbformat、Jupyter Book、Playwright Chromium、C:/F:保管庫。追加production依存なし。

**Spec:** johnhull/docs/superpowers/specs/2026-10-03-section-28-1-market-risk.md

## Global Constraints

- 専用 `hullkit.risk_premium.market_price_of_risk(mu,r,loading)` と `required_return(r,risk_price,loading)`。有限実数、市場broadcast、scalar float/ndarray。負loading/負λ/負rを許可する。
- λの逆算ではloading=0をValueError（μ=rでもλを特定できない）。required_returnではloading=0ならr。無効・表現不能な計算はValueError。空batchでも不正な有限/非実数入力を検査する。
- 既存API/root exports/production依存を変更しない。MCは既存sde.girsanov_weightsを|s|で使用し、負sのBrownian座標の向きを説明する。
- source pp.671–674、印刷値0.2/−0.15/1.5%、単因子・無配当取引証券。消費財spotへの機械適用・多因子・推定は範囲外。
- 独立参照はAPI非依存。12市場/6power給付、262144標本×4、seed281、決定的差1e−8/MC6SE、重み非正規化。
- 旧213セル完全保持、新11セル/224セル、6.1–6.6、4共有図、16表示状態/16画像、182図/exotics70。
- RP01–RP06の5軸、25D1、必須hash再構成、両保管庫復元、受入26/未評価280/P3 1/37。

## Review Focus

1. signed loading/年率単位を正のvolatilityと混同せず、負係数でもλを回復するか。
2. object内NumPy complex・巨大整数・空batch/zero loading/overflowをAPIが拒否するか。
3. P→QのRN符号、負sのBrownian座標、非正規化重み、ペア差SEが正しいか。
4. 消費財spot、金額weights/株数、局所無リスク/長期間無リスクを混同しないか。
5. 旧213セル、欠損必須hash、stale source、破損browser/片側保管庫欠損を台帳更新前に拒否するか。

### Task 1: API・独立参照・数値gate

**Files:** hullkit/src/hullkit/risk_premium.py; hullkit/tests/test_risk_premium{,_reference,_numerics}.py; scripts/build_risk_premium_reference.py/verify_risk_premium_numerics.py; docs/validation/section-28-1/reference.json/numerical-check.json。
**Interfaces:** market_price_of_risk(mu,r,loading)とrequired_return(r,risk_price,loading)、参照figure keys loading/hedge/densityとmc、数値source hash。

- [x] Step 1: 印刷ピン/負s/座標反転/empty-zero/complex/overflowのテストを先に実行。`assert market_price_of_risk(.03,.06,.2)==approx(-.15)`、`with raises(ValueError): market_price_of_risk([], .06, 0)`。Expected:missing API FAIL。
- [x] Step 2: 有限実数変換、入力のzeroをbroadcast前に検査し、`(mu-r)/loading` と `r+risk_price*loading` をerrstateで計算。Expected:API tests PASS。
- [x] Step 3: 参照・数値gateの失敗を確認。power給付の独立求積/Itô、非正規化RNとQ直接MCを実装。保存改変4件、実API変異（abs loading/drop λ/bias/NaN）を拒否。Expected:reference/numeric/AST独立性testsと2--check PASS。
- [x] Step 4: commit `Implement Hull market price of risk and independent references`、task-done:3新tests+test_reference_builders_independent.py。Expected:全PASS。

### Task 2: 共有教材・旧213セル保持

**Files:** hullkit/src/hullkit/_risk_premium_lesson.py/tests; volumes/10_exotics_martingales/build_exotics_notebook.py/exotics.ipynb; scripts/verify_risk_premium_notebook.py; report/tests/test_risk_premium_notebook.pyと歴史notebook tests。
**Interfaces:** risk_premium_loading/hedge/density/validation、START='### 6.1 ', END='## 7. '、224セル、保存4図、旧213セル。

- [x] Step 1: figure keys/数値/hash拒否とnotebook旧213保存/本文4改変testsを先に実行。`assert set(_figures())==KEYS`。Expected:missing lesson FAIL。
- [x] Step 2: 6.1 signed係数、6.2 portfolio、6.3印刷例、6.4密度、6.5独立検査、6.6限界の11セルを追加し、その新セルだけ実行。Expected:224セル、旧213不変。
- [x] Step 3: `compare(current,base,fresh)`、旧本文/新見出し/保存図/末尾見出し4改変、fresh全文の出力一致を検査。歴史pytestから新6.1だけを除く。Expected:notebook/legacy tests/--check PASS。
- [x] Step 4: commit `Teach signed risk loadings and measure changes`、task-done:lesson/notebook/歴史6ファイル。Expected:全PASS。

### Task 3: Book・portal・16実画面

**Files:** registry/tests/counts/manifest/MODEL_INDEX/README; scripts/evidence_dependencies.json/verify_risk_premium_browser.cjs; browser証跡。
**Interfaces:** chooser_validation直後4cards、182図/exotics70、28.1閉包risk_premium/sde/_risk_premium_lesson、fulltrace/密度/portfolio/印刷値/誤差棒。

- [x] Step 1: `assert KEYS <= {f.id for f in FIGURES}` の登録testを先に実行。Expected:未登録FAIL。
- [x] Step 2: registry/counts/dependency/API索引を更新。Expected:registry/report build tests PASS。
- [x] Step 3: `jupyter-book build johnhull/book`、`python -m report_builder.build`、`node johnhull/scripts/verify_risk_premium_browser.cjs`、1000px density/validationを目視。Expected:16states/16images、MathJax/数値/配置/改変拒否PASS。
- [x] Step 4: commit `Verify market risk lesson on Book and offline portal`、task-done:registry/report build tests。Expected:全PASS。

### Task 4: D1・台帳・レビュー

**Files:** build_risk_premium_acceptance_record.py/update_risk_premium_ledger.py/tests; 25D1; SECTION_28_1_ACCEPTANCE/REVIEW_2026-10-03.md; ledger/summary/ROADMAP/VALIDATION/EVIDENCE_POLICY。
**Interfaces:** m26-check.json、25採用D1path/hash、RP01–RP06、26/280/P3 1/37。

- [x] Step 1: gate/台帳不変、stale source/不完全browser/mirror欠落/必須hash個別削除/採用path改変testsを先に実行。`del changed[category][name]`。Expected:missing gate FAIL。
- [x] Step 2: clean Task3 commitから25節をD1再検査。旧24節はdirect redrawnを基準、26.8は初回redraw。`--records-dir docs/validation/d1-recheck`、C:/F:接続。Expected:browser/runtime/pytest/復元PASS。
- [x] Step 3: 現行依存から必須集合を導き、gate/台帳/状況docsを更新。4--check、ruff、全suite、台帳--check-artifacts。Expected:受入26/280、全PASS。
- [x] Step 4: commit `Accept Hull market price of risk and start P3`、task-done全suite。fresh最終review一本、重要指摘は一度RED→GREEN+全suite、Minor保留、Declinedを全件Ruling。Expected:重要指摘解消。
- [x] Step 5: review/実行台帳を保存commit、release--require-trackedとclean treeを確認しown workspaceだけ削除。Expected:統合3選択肢とターン末尾のP0–P8ロードマップ。
