# M25 Chooser Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline, task-by-task. Steps use checkbox syntax.

**Goal:** §26.8を独立計算・教材・実画面・D1で受入、25/281・P2完了。
**Architecture:** BSMのcallと配当調整putを専用APIで複製し、独立条件付き求積/MCを4図に共有。
**Tech Stack:** Python 3.12, NumPy/SciPy/Plotly, nbformat/nbclient, Jupyter Book, Playwright, shared venv.
**Spec:** johnhull/docs/superpowers/specs/2026-10-03-section-26-8-chooser.md

## Global Constraints

- chooser_price(S,K,r,sigma,T1,T2,q=0); finite real S,K>0,σ≥0,0≤T1≤T2; broadcast float/ndarray; ValueError for invalid/unrepresentable.
- T1は選択、T2は給付決済。H=K exp(−(r−q)τ)、w=exp(−qτ)。原典pp.619–620、数値は合成。
- 基点5013f2d4、/home/kazumasa/worktrees/m25、shared venv。既存pricing/exports/依存、旧202セルを保持。
- 独立64例、MC524288×4、誤差1e−8/6SE。213セル、178図/exotics66、16browser states。D1旧24節。

## Review Focus

1. 配当調整のput枚数とstrike、T1選択とT2決済を混同しないか。
2. T1=0/T1=T2/σ=0/T2=0、近接満期、負のr/qを正確に扱うか。
3. mixed broadcast、complex/object-complex/巨大整数、overflow、空配列の挙動は一貫するか。
4. 独立参照がAPI/複製公式に依存せず、狭いinner vanilla遷移を求積が取り逃さないか。
5. 欠損D1必須hash、非有限API、stale source、不完全browser、片側保管庫欠損を台帳更新前に拒否するか。

### Task 1: 価格API・独立求積・数値ゲート

**Files:** chooser.py; test_chooser.py/test_chooser_reference.py/test_chooser_numerics.py; build_chooser_reference.py/verify_chooser_numerics.py; section-26-8/reference.json/numerical-check.json.
**Interfaces:** chooser_price above; integrate_chooser(S,K,r,sigma,T1,T2,q=0)→(price,error); vanilla(s,k,r,sigma,t,q,kind)→float; build()→cases/example/mc/figure(choice/package/timing).

- [ ] Step 1: pins .1→10.483695744000126/.5→13.344280448069238/.9→15.168232237397923/.999999→15.55708234558728、境界/同次性/bounds/broadcast/無効値testsを先に実行。`assert chooser_price(100,100,.05,.2,.5,1,.02)==pytest.approx(13.344280448069238,abs=1e-9)`。Expected: missing APIでFAIL。
- [ ] Step 2: validated broadcastとBSM複製、正確な境界を実装。`price=call(S,K,T2)+exp(-q*tau)*put(S,H,T1)`。Expected:API tests PASS。
- [ ] Step 3: 64例・4MC・near expiry splitを求めるtestを先に実行し、erfc vanillaとT1密度求積を実装。`assert len(build()["cases"])==64`。Expected:missing reference FAIL→PASS。
- [ ] Step 4: 保存改変、配当drop/選択日変更/微小bias/NaNの実API変異を先に実行し、再計算/finite/比較/同次性/bounds/複製/MCゲートを実装。`with pytest.raises(ValueError): verify(mutated)`。Expected:gate missing FAIL→PASS、両--check PASS。
- [ ] Step 5: Task1だけcommit `Implement Hull simple chooser pricing and independent references`。task-done:上記3testsとindependence tests。Expected:全PASS。

### Task 2: 4共有図・213セル教材

**Files:** _chooser_lesson.py/test_chooser_lesson.py; vol10 builder/notebook; verify_chooser_notebook.py; report/tests/test_chooser_notebook.py/test_compound_notebook.py.
**Interfaces:** _figures()→chooser_choice/chooser_package/chooser_timing/chooser_validation。### 4.15から## 5まで11セル、旧202保存。

- [ ] Step 1: 4key/境界/複製/curve/誤差棒/hash欠落拒否testsを先に実行。`assert set(_figures())==KEYS`。Expected:missing lesson FAIL。
- [ ] Step 2: §4.15.1–6の契約/導出/価格例/選択時期/独立検証/限界を11セルで挿入し新セルを実行。Expected:213cellsと保存4図、旧202不変。
- [ ] Step 3: old prose/new heading/saved figure/post headingの4改変、fresh全文出力一致を先にテストしgate実装。歴史M24 pytestは後続4.15だけ除く。`assert not compare(current,base,fresh)`。Expected:notebook tests/--check PASS。
- [ ] Step 4: commit `Teach Hull chooser replication and decision timing`。task-done:lesson/new/historical notebook tests。Expected:全PASS。

### Task 3: Portal・Book・16実画面

**Files:** report registry/tests; release_manifest/MODEL_INDEX/READMEs; evidence_dependencies.json/verify_chooser_browser.cjs; browser evidence。
**Interfaces:** compound_validation直後4card、178figures/exotics66、section26.8閉包chooser/bsm/_chooser_lesson、両画面全trace/境界/誤差棒照合。

- [ ] Step 1: 新4key要求testを先に実行。`assert KEYS <= {fig.id for fig in FIGURES}`。Expected:未登録FAIL。
- [ ] Step 2: registry/counts/API索引/依存を更新。Expected:registry/build tests PASS。
- [ ] Step 3: `jupyter-book build johnhull/book`、`python -m report_builder.build`、`node johnhull/scripts/verify_chooser_browser.cjs`、1000px choice/validationを目視。Expected:16states/16images、全trace/数式/配置/改変拒否PASS。
- [ ] Step 4: commit `Verify chooser lesson on Book and offline portal`。task-done:registry/build tests。Expected:全PASS。

### Task 4: D1・台帳受入・最終レビュー

**Files:** build_chooser_acceptance_record.py/update_chooser_ledger.py/tests; D1記録; SECTION_26_8_ACCEPTANCE/REVIEW_2026-10-03.md; ledger/summary/ROADMAP/VALIDATION/EVIDENCE_POLICY。
**Interfaces:** m25-check.jsonに旧24採用path/hashと現在依存から導いた必須集合、CH01–CH06の5軸、25/281、P2 8/8。

- [ ] Step 1: stale source/browser欠落/mirror欠落/D1必須hash個別削除/採用path改変/missing gateで台帳不変を先にテスト。`del changed[category][name]`。Expected:missing gate/updater FAIL。
- [ ] Step 2: clean Task3 commitからD1旧23節direct redrawn reuseと§26.7初回redraw。`--records-dir docs/validation/d1-recheck`、C:/F:環境を指定。Expected:24browser/runtime/pytest/復元PASS。
- [ ] Step 3: 必須hash再構成、ゲート/台帳/状況docsを更新、ruff/全suite/4--check/台帳--check-artifacts。Expected:25/281/P2complete、全PASS。
- [ ] Step 4: commit `Accept Hull chooser options and complete P2`、task-done全suite。fresh最終review一本、Important/Criticalは一度RED→GREEN+全suite、Minor保留、DeclinedすべてRuling。Expected:重要指摘解消。
- [ ] Step 5: reviewを保存commit、release--require-tracked/clean treeを確認しown workspaceだけ削除。Expected:本branchで完了、統合3選択肢を提示。
