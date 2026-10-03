# M27 Factor Risk Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §28.2の原典・API・独立参照・教材・両配布画面を受け入れ、P3を2/37へ進める。
**Architecture:** 新factor_risk専用API、独立math.fsum参照、hash保護の共有lesson、旧224セルを保持するnotebookとD1/台帳/実画面gate。
**Tech Stack:** 共有uv venv、NumPy/SciPy、Plotly、nbformat、Jupyter Book、Playwright、C:/F:保管庫。追加production依存なし。
**Spec:** johnhull/docs/superpowers/specs/2026-10-03-section-28-2-factor-risk.md

## Global Constraints

- 最終因子軸は同じ正整数、先行batchのみbroadcast。3関数factor_contributions/factor_excess_return/factor_required_return。
- 入力は有限実数、signed係数、empty batch可、scalar因子/空因子/因子数不一致/非実数/overflow不可。既存APIと依存は不変。
- 印刷6%は超過収益、r=4%の総収益10%は教材追加の合成例。CAPMの結論はCAPM仮定付き。
- 12市場/3証券2因子hedge/4回転、独立参照との差1e−12、保存と実API変異を拒否。
- 旧224セル保持、11セル追加235セル、6A.1–6A.6、4共有図、16状態、186図/exotics74。
- FR01–FR06、26D1、両保管庫、現行必須hash、受入27/未評価279/P3 2/37。

## Review Focus

1. 因子軸長1が長3へ暗黙broadcastされず、rとbatch軸が混同されないか。
2. 超過6%と総期待収益、負寄与と低い総収益、signed係数と正volatilityを混同しないか。
3. 相関の二重適用、直交回転、CAPM以外の無相関リスク無価格への一般化がないか。
4. 旧224セルと§28.1依存境界、全trace・MathJax・small viewportが保護されるか。
5. 欠損/stale source/採用D1path・片側保管庫欠損を更新前に拒否するか。

### Task 1: API・独立参照・数値gate

**Files:** hullkit/src/hullkit/factor_risk.py、hullkit/tests/test_factor_risk{,_reference,_numerics}.py、scripts/build_factor_risk_reference.py/verify_factor_risk_numerics.py、section-28-2 reference/numerical-check。
**Interfaces:** 3factor APIと参照printed_pins/cases/hedge/rotations/figure、数値hash。
- [x] Step 1: `assert factor_excess_return([.2,-.1,.4],[.05,.1,.15])==approx(.06)`、因子不一致、complex/overflow/空因子/batch testsを作る。Run `pytest johnhull/hullkit/tests/test_factor_risk.py -q`。Expected: missing API FAIL。
- [x] Step 2: `_real_inputs`で検査しfactor長を一致、最後の軸の積を返し、np.sum(axis=-1)、rを加える。Expected: API tests PASS。
- [x] Step 3: `math.fsum`と独立参照12例・3証券hedge・4回転を保存、数値gateはAPIとSVD局所hedgeを検査する。Expected: reference/numeric/AST独立性tests、2--check PASS。
- [x] Step 4: commit `Implement multi-factor signed risk premiums`、task-done 3tests+reference independence。Expected: 全PASS。

### Task 2: 共有教材・旧224セル保持

**Files:** _factor_risk_lesson.py/test、build_exotics_notebook.py/exotics.ipynb、verify_factor_risk_notebook.py/report test、歴史notebook tests。
**Interfaces:** 4factor_risk figures、START='## 6A. ',END='## 7. '、235セル。
- [x] Step 1: `assert set(_figures())==KEYS`とhash/保存図不変tests。Expected: missing lesson FAIL。
- [x] Step 2: 6A.1式/単位、6A.2印刷例、6A.3正負loading、6A.4局所hedge、6A.5基底/独立検査、6A.6CAPM/限界の11セルを挿入し新セルのみ実行。Expected: 235セル、旧224一致。
- [x] Step 3: 4notebook改変を拒否、fresh全文出力を照合。歴史pytestは新6A範囲を除く。Expected: notebook/lesson/歴史tests、--check PASS。
- [x] Step 4: commit `Teach factor contributions and local risk cancellation`、task-done対象tests。Expected: 全PASS。

### Task 3: Book・portal・実画面

**Files:** registry/counts/manifest/index/README、evidence_dependencies.json、verify_factor_risk_browser.cjs、16画像。
**Interfaces:** risk_premium_validation直後4cards、186図/exotics74、28.2親6A全体の依存宣言。
- [x] Step 1: `assert KEYS <= {s.id for s in FIGURES}`登録test。Expected: 未登録FAIL。
- [x] Step 2: 4FigureSpec登録と件数/閉包を更新。Expected: registry/build tests PASS。
- [x] Step 3: `jupyter-book build johnhull/book`、`python -m report_builder.build`、`node johnhull/scripts/verify_factor_risk_browser.cjs`、1000px画像目視。Expected: 16状態/MathJax/全trace/配置/改変拒否PASS。
- [x] Step 4: commit `Verify factor risk on Book and offline portal`、task-done registry/build tests。Expected: 全PASS。

### Task 4: D1・台帳・最終レビュー・統合

**Files:** build_factor_risk_acceptance_record.py/update_factor_risk_ledger.py/tests、26D1、SECTION_28_2_ACCEPTANCE/REVIEW、台帳/ROADMAP/VALIDATION/EVIDENCE_POLICY。
**Interfaces:** m27-check.json、26採用D1path/SHA、FR01–FR06、27/279。
- [x] Step 1: stale/欠損hash/不完全browser/片側保管庫/採用path/更新失敗時台帳不変tests。Expected: missing gate FAIL。
- [x] Step 2: clean Task3 commitから26D1、既存は直接redrawnへreuse、28.1初回redraw。Expected: browser/runtime/pytest/復元PASS。
- [x] Step 3: mandatory hash再構成、台帳とdocs更新、4--check/ruff/全suite/台帳--check-artifacts。Expected: 27/279、全PASS。
- [x] Step 4: commit `Accept Hull multi-factor risk premiums`、task-done全suite、fresh最終review一度、重要指摘はRED→GREENと全suite、Minor記録。Expected: 受入を止める指摘なし。
- [ ] Step 5: review/実行台帳をcommit、tracked release、clean tree、mainへ統合後検証とpush。Expected: live remote一致、末尾にP0–P8。
