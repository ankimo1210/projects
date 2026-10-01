# M23 Cliquet Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §26.6を各期cashflow・価格分解・独立参照・実画面で照合し、台帳を受入23節へ進める。

**Architecture:** 専用call/put APIが各期のATM価値を正しい支払日で割り引いて足す。独立密度求積と多時点MCを保存参照にし、内部4図をnotebook/portalで共有。既存受入22節はD1で再検査する。

**Tech Stack:** Python 3.12、NumPy、SciPy、Plotly、nbformat/nbclient、Jupyter Book、Playwright、既存共有venv。

**Spec:** johnhull/docs/superpowers/specs/2026-10-01-section-26-6-cliquet.md

## Global Constraints

- 定数GBM、各期stockの正負変化を通貨で支払う単純型call/put。固定notional returnの和と区別する。
- scalar APIはfloat、broadcast市場はndarray。payment_timesは固定の非空1次元・正・厳密増加。無効/表現範囲外計算はValueError。
- 既存pricingコードとhullkit.__init__を維持。production依存を追加しない。
- M22基点14c94ac2の旧180セルを保持する。原典p.618に印刷値なし、全数値は合成。
- 作業は/home/kazumasa/worktrees/m18、Git/buildはWSL、Pythonは/home/kazumasa/projects/.venv/bin/python。

## Review Focus

1. 非等間隔scheduleで各給付を各tiから割り引き、全給付のtn一括割引を拒否するか。
2. reset時点の株価をstrikeにし、S0固定strikeや固定notional returnへ変わる実装を検出できるか。
3. 市場配列のゼロσと正σが混在しても正しく、無効な一要素やobject-complex/極大整数をValueErrorで拒否するか。
4. global cap/floorと各期cap、範囲終了を混同せず、MCの支払規約r=q=0と誤差棒を正しく示すか。
5. 全必須source/artifactハッシュ・D1ミラー・採用記録が欠ければ台帳更新が閉じるか。

### Task 1: 単純cliquet価格APIと独立参照

**Files:** hullkit/src/hullkit/cliquet.py、hullkit/tests/test_cliquet.py、scripts/build_cliquet_reference.py、scripts/verify_cliquet_numerics.py、対応hullkit tests、docs/validation/section-26-6/。

**Interfaces:** cliquet_call(S,r,sigma,payment_times,q=0)、cliquet_put（同シグネチャ）→float/ndarray。integrate_period(S,r,sigma,T1,T2,q=0,kind="call")→(price,error)、integrate_cliquet(S,r,sigma,payment_times,q=0,kind="call")→(price,error,components)。build()→cases/example/mc/complex/figure。

- [x] Step 1: 1期vanilla（call10.450583572185565）、2期q3%（call17.04933624301734、put13.262906618476658）、非等間隔、zeroσ、broadcast、invalid市場/schedule/shapeのテストを追加。Expected: APIがなくFAIL。
- [x] Step 2: callはforward_start_callの各期和、putはS exp(−q start) normalized BSM putの和。入力変換例外と合計overflowもValueErrorで拒否する。Expected: API tests PASS。
- [x] Step 3: 独立二増分密度求積60ケース、各期割引MC524288経路×4例、制約診断の共通経路MCを作る。Expected: 参照testsと--check PASS。
- [x] Step 4: API/求積差1e−9、MC6SE以内、成分和・同次性・call-put差を照合。参照のprice/reset/discount/cap改変4件、実装の固定strike/一括割引/return変更3件を拒否する。Expected: testsと数値--check PASS。
- [x] Step 5: ローカルcommit Implement Hull simple cliquet calls and puts。

### Task 2: 共有4図と保存notebook

**Files:** _cliquet_lesson.py、lesson tests、vol10 builder/notebook、verify_cliquet_notebook.py、対応report tests。

**Interfaces:** _figures()→cliquet_reset/cliquet_components/cliquet_frequency/cliquet_limits。notebook区間### 4.13から## 5まで。

- [x] Step 1: fixing/strike、成分価格、n=1、制約MC誤差棒と市場明記を要求するtestsを追加。Expected: 新教材moduleがなくFAIL。
- [x] Step 2: 6小節・11セル・4図を追加。各図の市場・日付、通貨給付とreturnの違い、global/local制約・終了・MC標本誤差を明記。旧180セルを保持し新11セルを実行。Expected: 191cells、共有4図。
- [x] Step 3: 新図改変・旧本文・新見出し・終端見出しの4改変を拒否し、保存出力とfresh実行を照合。Expected: gate/tests PASS。
- [x] Step 4: ローカルcommit Teach Hull cliquet resets and payment timing。

### Task 3: Portal・Book・browser

**Files:** registry/対応tests、release manifest、MODEL_INDEX、D1依存宣言、verify_cliquet_browser.cjs。

**Interfaces:** 4図をforward_fixed_expiry直後に登録。全170図/exotics58図。browser-checkは16状態/16画像、現行source/artifact hashes。

- [x] Step 1: 4カードを要求するtestを追加。Expected: 未登録でFAIL。
- [x] Step 2: registry・件数・API索引・§26.6依存宣言を追加。依存moduleはcliquet/forward_start/bsm/_cliquet_lesson。
- [x] Step 3: Book/portalをbuildし、16状態の数値・MC誤差棒・customdata・文字切れ・数式・価格改変拒否を検査。1000pxのreset/制約図を目視。Expected: browser PASS。
- [x] Step 4: ローカルcommit Verify Hull cliquet lesson on Book and portal。

### Task 4: D1回帰と受入台帳

**Files:** build_cliquet_acceptance_record.py、update_cliquet_ledger.py、対応tests、§26.6受入/レビュー、台帳/summary、ROADMAP/VALIDATION/README/EVIDENCE_POLICY。

**Interfaces:** 既受入22節のD1をm23-check.jsonで固定。台帳accepted23/unreviewed283、CQ01–CQ06の5軸。

- [x] Step 1: stale source、不完全browser、mirror欠落、gate欠落時の台帳不変、採用D1変更を先にテスト。Expected: 新gateがなくFAIL。
- [x] Step 2: クリーンcommitでD1旧21節のredrawn基点直接reuseと§26.5初回redrawを実行。--records-dir docs/validation/d1-recheckを指定。Expected: browser/runtime/pytest/両保管庫PASS。
- [x] Step 3: 統合gateで全必須ハッシュとD1の現行成果物/両保管庫を照合し、採用パス/SHAを固定。台帳と現在地を更新する。
- [x] Step 4: 全hullkit+report pytest、ruff、4本--check、台帳--check-artifacts、releaseを実行。独立最終レビュー1本、重要指摘はRED→GREENと全suiteで修正。Expected: 全PASS。
- [x] Step 5: 受入をローカルcommit、post-commit --require-trackedとclean treeを確認。Expected: 23/283、全gate PASS。
