# M22 Forward Start Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** §26.5を原典・独立参照・教材・実画面で照合し、台帳を受入22節へ進める。

**Architecture:** 専用APIがnormalized BSMからATM forward-startを価格付けする。二時点密度求積とMCを独立参照にし、保存データの4図をnotebook/portalで共有する。M21の受入ゲートを踏襲する。

**Tech Stack:** Python 3.12、NumPy、SciPy、Plotly、nbformat/nbclient、Jupyter Book、Playwright、既存共有venv。

**Spec:** `johnhull/docs/superpowers/specs/2026-10-01-section-26-5-forward-start.md`

## Global Constraints

- 既存pricingコードと公開関数のシグネチャは維持する。新しいproduction依存は追加しない。
- 定数r,q,σのGBMとATM欧州型コール。原典に印刷値はない。put・汎用moneyness・cliquetは追加しない。
- M21基点e2706e43の旧169セルと既受入21節を保持する。
- Git/buildはWSL、Pythonは`/home/kazumasa/projects/.venv/bin/python`、作業は`/home/kazumasa/worktrees/m18`。

## Review Focus

1. T2をτと取り違える実装を、T1>0・q≠0の市場で検出できるか。
2. 行使価格をS0に固定する実装と、支払をT1で割り引く実装を二時点参照で拒否できるか。
3. 配列にゼロ長契約・ゼロσが混在しても正しく、無効な一要素を黙って許さないか。
4. τ固定とT2固定の掃引を混同せず、MCの誤差帯を決定的参照の誤差と区別するか。
5. 保存参照・ブラウザ・D1の必須ハッシュやミラーが欠けたら台帳更新が閉じるか。

### Task 1: 価格API・独立参照・数値ゲート

**Files:** `hullkit/src/hullkit/forward_start.py`, `hullkit/tests/test_forward_start.py`, `scripts/build_forward_start_reference.py`, `scripts/verify_forward_start_numerics.py`, 対応hullkit tests、`docs/validation/section-26-5/`。

**Interfaces:** `forward_start_call(S,r,sigma,T1,T2,q=0)` → float/ndarray。参照`integrate_forward_start(S,r,sigma,T1,T2,q=0)` → (price,error)、`build()` → cases/example/mc/figure。`verify(data)` → 数値結果。

- [x] Step 1: T1=0、q=0の遅延不変、一次同次性、零長・零σ混在、無効要素・shapeのテストを先に追加する。`forward_start_call(100,.05,.2,0,1)`の期待値は10.450583572185565。Expected: 関数がなくFAIL。
- [x] Step 2: 正規化したspot=strike=1のBSM価格にS exp(−qT1)を掛ける。τ=0要素は計算を避ける。公開APIを直接importする。Expected: API tests PASS。
- [x] Step 3: 二つの独立GBM増分の密度を積分し、満期T2で割り引く参照を作る。固定seed・524288経路の二時点MCを3例作り、標準誤差と95%区間を保存する。Expected: 36ケースと全図用配列が再計算一致。
- [x] Step 4: 求積/API差、MCの6標準誤差内、同次性・q=0・T1=0・零境界を確認し、価格・tenor・fixing・割引の4改変を拒否する。APIを誤ったtenor/配当因子へ変異させるtestも実行。Expected: `--check`と関連tests PASS。
- [x] Step 5: ローカルcommit `Implement Hull ATM forward-start call and independent reference`。

### Task 2: 共有4図と保存notebook

**Files:** `_forward_start_lesson.py`, lesson tests、vol10 builder/notebook、`verify_forward_start_notebook.py`、対応report tests。

**Interfaces:** 保存参照から`_figures()` → `forward_contract`, `forward_homogeneity`, `forward_start_delay`, `forward_fixed_expiry`。notebook区間`### 4.12 `から`## 5. `まで。

- [x] Step 1: 経路のstrike fixing、同次性、q=0の定長曲線と零長終点を検査するtestsを追加。Expected: 新教材モジュールがなくFAIL。
- [x] Step 2: 4図と6小節・11セルを追加する。定長と固定満期の違い、MC error bar、ESOとの関係、合成例の前提を明示。旧169セルを保持して実行する。
- [x] Step 3: 自節の保存図、旧本文、見出し、終端見出しの4改変をnotebookゲートで拒否し、共有図と実行出力を確認。Expected: notebookゲートとtests PASS。
- [x] Step 4: ローカルcommit `Teach Hull forward-start fixing and valuation`。

### Task 3: Portal・Book・ブラウザ

**Files:** registry・対応tests・release manifest・MODEL_INDEX・依存宣言・`verify_forward_start_browser.cjs`。

**Interfaces:** 4図を§26.4直後に登録。合計166図/exotics54図。browser-checkは両画面×2幅×4図、16状態・16画像と現行ハッシュ。

- [x] Step 1: 4カードを要求するregistry testを先に実行。Expected: 未登録でFAIL。
- [x] Step 2: 図登録と件数・公開APIの索引・§26.5のD1依存宣言を更新する。
- [x] Step 3: Book/portalをbuildし、Playwrightで本文・数式・全trace配列・MC誤差帯・配置・数値改変拒否を確認する。1000pxの契約図と固定満期図を目視する。Expected: 16状態PASS。
- [x] Step 4: ローカルcommit `Verify Hull forward-start lesson on Book and portal`。

### Task 4: D1回帰・統合記録・台帳

**Files:** `build_forward_start_acceptance_record.py`, `update_forward_start_ledger.py`, tests、§26.5受入/レビュー、節台帳/summary、ROADMAP/VALIDATION/README/EVIDENCE_POLICY。

**Interfaces:** 既受入21節のD1記録と新節の検査を`m22-check.json`で固定。台帳accepted22/unreviewed284、FS01–FS06の5軸。

- [ ] Step 1: 古い入力・不完全なブラウザ状態・ミラー欠落・ゲート欠落時の台帳不変を先にテスト。Expected: 新ゲートがなくFAIL。
- [ ] Step 2: クリーンcommit上でD1を実行。旧20節はM21で採用したredrawn基点を使いreuseを要求する（reuseの連鎖は作らない）。§26.4は初回D1描画。`--records-dir docs/validation/d1-recheck`を必ず指定。
- [ ] Step 3: 統合ゲートで数値・notebook・browser・D1両保管庫を照合し、選択した記録パスとSHA-256を固定する。台帳・ROADMAPを更新する。
- [ ] Step 4: 全hullkit+report pytest、ruff、4本の`--check`、台帳`--check-artifacts`、releaseを実行。独立最終レビューを1本依頼し、重要指摘はRED→GREENで修正する。
- [ ] Step 5: 受入をローカルcommitし、`verify_release.py --require-tracked`とclean treeを確認する。Expected: 22/284、全ゲートPASS。
