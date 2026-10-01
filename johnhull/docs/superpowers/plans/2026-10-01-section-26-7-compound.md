# M24 Compound Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §26.7の欧州型4契約を臨界株価・Geske公式・独立求積・実画面で照合し、台帳受入24節へ進める。

**Architecture:** 専用compound_priceが根探索と決定的二変量正規から4公式を評価。独立T1密度求積と条件付きMCを保存し、4図をnotebook/portalで共有する。旧23節はD1で再検査する。

**Tech Stack:** Python 3.12, NumPy, SciPy, Plotly, nbformat/nbclient, Jupyter Book, Playwright, shared venv.

**Spec:** johnhull/docs/superpowers/specs/2026-10-01-section-26-7-compound.md

## Global Constraints

- compound_price(S,K1,K2,r,sigma,T1,T2,q=0,*,kind="call_on_call")。4kindを選択、float/ndarray、市場broadcast。
- S,K2>0、K1≥0、sigma≥0、0<T1<T2、全入力有限実数、無効/非有限結果はValueError。
- 内側vanillaをT1で評価する。K1=0/zero sigma/putの根なし領域は明示的分岐。
- 既存pricing・hullkit.__init__・production依存を維持。旧191セルを保持、11セルを追加。
- 原典pp.618–619に印刷数値なし、全数値合成。API/恒等式1e−8、根1e−9、MC6SE。
- /home/kazumasa/worktrees/m18、cb3665fd基点。Git/buildはWSL、共有venvを使う。

## Review Focus

1. K1が内側put上限以上の契約を、根探索の失敗として拒否しないか。
2. 内側putの行使領域と相関の符号、aとbに使うstrikeを混同しないか。
3. T1がT2に近いとき二変量積分が再現可能で、誤った価格/非有限を返さないか。
4. zero sigma/K1=0が配列の一部に混じり、complex/object-complex/極大整数・overflowが一部にあると正しく分岐/拒否するか。
5. D1必須hashが欠けた記録、NaN API変異、不完全browser、stale sourceを台帳更新前に拒否するか。

### Task 1: 4価格APIと独立参照

**Files:** hullkit/src/hullkit/compound.py; hullkit/tests/test_compound.py/test_compound_reference.py/test_compound_numerics.py; scripts/build_compound_reference.py/verify_compound_numerics.py; docs/validation/section-26-7/reference.json/numerical-check.json.

**Interfaces:** compound_price as above; private _critical_spot(K1,K2,r,sigma,tau,q,inner)→float/None, _bivariate_normal(a,b,rho)→float. Independent integrate_compound(S,K1,K2,r,sigma,T1,T2,q=0,kind="call_on_call")→(price,error), vanilla(s,k,r,sigma,t,q,inner)→float, build()→cases/example/mc/figure.

- [ ] Step 1: APIの4合成価格・2根・parity/同次性・K1=0・zero sigma・put根なし/境界・broadcast/無効値テストを先に作り実行。`assert compound_price(100,10,100,.05,.2,.5,1,.02)==pytest.approx(3.25682701977442,abs=1e-9)`。Expected: module missingでFAIL。
- [ ] Step 2: 正規CDF相関角度の積分とlog spot根探索、4公式、境界分岐を実装。`M=Phi(a)*Phi(b)+quad(density_angle,0,asin(rho))/(2*pi)`。Expected: API tests PASS。
- [ ] Step 3: 独立erfc vanilla/T1密度求積104ケースと524288経路×4のMC、閾値/strike/timingデータを要求するtestsを先に実行。`assert len(build()["cases"])==104`。Expected: reference missingでFAIL。求積は臨界点で区間を分け、正の外側給付をexp(−rT1)で割り引く。Expected: reference tests PASS。
- [ ] Step 4: 数値gateに保存参照再計算・API差/有限値・parity/同次性/根・MCと4保存改変/4API変異拒否を追加する前にtestsを実行。`monkeypatch.setattr(compound,"compound_price",lambda *a,**k:float("nan"))`でverifyがValueError。Expected: gate missingでFAIL→PASS、参照/数値--check PASS。
- [ ] Step 5: `git add`でTask1のみを選び、`git commit -m "Implement Hull European compound options"`。task-doneは上記3tests。Expected:全PASS。

### Task 2: 4共有図・保存notebook

**Files:** hullkit/src/hullkit/_compound_lesson.py; lesson tests; vol10 builder/notebook; scripts/verify_compound_notebook.py; report/tests/test_compound_notebook.py/test_cliquet_notebook.py/test_forward_start_notebook.py.

**Interfaces:** _figures()→compound_threshold/compound_strikes/compound_timing/compound_validation。区間### 4.14から## 5まで。現在notebook202セル。

- [ ] Step 1: 4key・根/給付/curve/MC誤差棒・source欠落拒否testsを作り実行。`assert set(_figures())==KEYS`。Expected: module missingでFAIL。
- [ ] Step 2: 6見出し/11セルで契約4式・根/例外・4図・MC/範囲を教える。旧191セルをそのまま保持して新11セルを実行。Expected:202セル、4shared figures。
- [ ] Step 3: 旧本文・新見出し・保存図・末尾見出しの4改変拒否、fresh全文実行と保存図一致を検証。`assert not compare(current,base,fresh)`。M22/M23の歴史比較は後続4.14だけを除き、全巻保存をM24が担う。Expected:notebook tests/--check PASS。
- [ ] Step 4: `git commit -m "Teach Hull compound exercise thresholds and four contracts"`。task-doneはlesson/new notebook/歴史notebook tests。Expected:全PASS。

### Task 3: Portal・Book・browser

**Files:** report registry/tests; release_manifest/MODEL_INDEX/README; scripts/evidence_dependencies.json/verify_compound_browser.cjs; browser evidence。

**Interfaces:** 4カードをcliquet_limits直後に追加。174図/exotics62図。browserは16状態/16画像、両surfaceの全trace/誤差棒/根、数式/文字切れ/数値改変拒否、source/artifact hashes。

- [ ] Step 1: 4registry keyを要求するtestを先に実行。`assert KEYS <= {fig.key for fig in FIGURES}`。Expected:未登録でFAIL。
- [ ] Step 2: registry/件数/API索引/§26.7依存（compound,bsm,_compound_lesson）を追加。Expected: registry/build tests PASS。
- [ ] Step 3: `jupyter-book build johnhull/book`と`python -m report_builder.build`を実行、node browser検査で全16状態/画像を確認。1000px閾値/検証図を目視。Expected:全PASS。
- [ ] Step 4: `git commit -m "Verify Hull compound lesson on Book and portal"`。task-doneはregistryとreport build tests。Expected:全PASS。

### Task 4: D1回帰・受入・レビュー

**Files:** scripts/build_compound_acceptance_record.py/update_compound_ledger.py; 対応report tests; D1 records; §26.7 acceptance/review; ledger/summary; ROADMAP/VALIDATION/EVIDENCE_POLICY。

**Interfaces:** m24-check.jsonが旧23節の採用パス/SHAと必須source/artifact集合を固定。CO01–CO06の5軸、accepted24/unreviewed282/P2 7/8。

- [ ] Step 1: stale source/browser状態欠落/mirror欠落/必須D1hash個別削除/採用パス改変/missing gate時台帳不変testsを先に実行。`del changed[category][name]`でcheck_d1_payloadがValueError。Expected: gate/updater missingでFAIL。
- [ ] Step 2: クリーンTask3commitから、D1旧22節のredrawn基点直接reuseと§26.6初回redrawを実行。`--records-dir docs/validation/d1-recheck`とC:/F:環境を指定。Expected:23browser/runtime/pytest/復元PASS。
- [ ] Step 3: gateの必須集合を現行宣言/閉包から再構成し、統合記録/台帳/現在地/検証結果を更新。Expected:4--check、台帳--check-artifacts、ruff、全hullkit+report pytest PASS。
- [ ] Step 4: whole branchの独立最終レビュー1本。Important/Criticalは再現test RED→GREENと全suiteで一度修正、Minorは保留記録、判断保留項目は理由/コスト付きRuling。Expected:重要指摘解消、全PASS。
- [ ] Step 5: `git commit -m "Accept Hull compound options with D1 regression evidence"`、コミット後release --require-trackedとclean tree、task-done全suite。Expected:24/282、全PASS。完成workspaceだけを削除し統合3選択肢を提示。
