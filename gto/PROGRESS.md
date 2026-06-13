# GTO Poker Suite — 進捗 & TODO

最終更新: 2026-06-12（M1b flop 非同期ソルブ + M2 6max 行列 v1 を実装）

---

## 完了済み

### M2 — 6max ポジションペア行列 v1 + Tournament-HU + 移行 (2026-06-12)
モードマトリクス・ロードマップ §3 M2 を実装（BB-as-sole-defender スコープ）。
- **チャート 8 枚追加**（`src/gto/trainer/preflop_data.py`）: BB ディフェンド
  BB_vs_UTG/HJ/SB + opener-vs-BB-3bet 5 枚（UTG/HJ/CO/BTN/SB、4B/C/F）。
  `_face2`/`_vs3` ヘルパー（mixed-3bet 残りはコール、部分コール対応）。
  既存 BB_vs_BTN/CO も `_face2` 化（**旧 `_face` のチャートバグ修正**: QQ が
  BTN オープンに 30% フォールドしていた等。旧 `_face` は削除）。
- **整合性バリデータ**（`src/gto/trainer/chart_validator.py`）: 頻度和=100 /
  vs-3bet の継続ハンドは opener の RFI 支持内 / ディフェンド⇄レスポンスのペア /
  継続頻度 [30%,75%] サニティバンド。**初回実行で実バグを 5 件検出**
  （継続レンジが MDF 比で過小）→ 修正済み。出荷時 violations 0。
  実測: BB 3bet 2.9%(UTG)〜9.1%(BTN)、opener 継続 30.2%(CO)〜43.4%(UTG)。
- **チャート由来レンジ**（`src/gto/library/chart_ranges.py`）: SRP =
  opener RFI × BB ディフェンドコール、3bet pot = BB 3bet × opener
  (open×call) 条件付きレンジ。**SB opener は 6max ではポストフロップ OOP**
  （HU 慣行と逆）を `opener_is_ip` で処理。
- **GameSpec 拡張**: `table=6max`（5 ポジションペア × srp/3bet、レンジ既定 =
  チャート、明示 notation/weights で上書き）+ `game=tournament`
  （F2: HU ICM≡chip EV。ante は pot_bb に折込み、rake は 422、
  シャロー stack presets を capabilities に記載）。
- **/solver・/simulation の gto-hu 移行**: board 4/5 枚 → gto-hu 均衡
  （exact expl、`equilibrium_claim=true`）、3 枚 → gto-cuda instant-preview
  （`equilibrium_claim=false`、gto_cuda 不在時は 503）。
  **gto-core 単一ストリート CFR を退役**（cfr.rs / tree.rs / solve() /
  gto_py.solve_spot 削除 — 旧 CPU フォールバック 2 箇所が唯一の利用者だった）。
- **gto-cuda ライブラリ preview 降格**: `/api/library/*` 全行に
  `equilibrium_claim=false` + `tier="instant-preview"`。/library・/report に
  「PREVIEW — approximation」ラベル（uniform レンジの事実も tooltip 記載）。
- review パーサ副次効果: BB_vs_UTG/HJ/SB が deviation 判定でカバー済みに
  （旧 missing_data テストは「カバー済み」検証に更新）。
- 検証: pytest **115 passed**、cargo フルスイート green、Playwright 実描画
  （/library・/report ラベル、/solver river の EQUILIBRIUM バッジ）、
  実 HTTP（solver river=gto-hu / simulation turn=gto-hu / library flags）。
- 残: 残り 14 ペア（20 チャート）= M3、intra-solve CPU 並列化実験（未着手）、
  flop preview の chart 重み再生成判断。

### M1b — Flop 非同期カスタムソルブ (2026-06-12)
モードマトリクス・ロードマップ（`docs/superpowers/specs/2026-06-11-mode-matrix-
roadmap-design.md` §4.4、受け入れ 6–7）の M1b を実装。
- **`solve_hu_flop` pyo3 バインディング**（従来 CLI のみ・バインディング不在）—
  board 3 枚 / ranges(1326重み or 記法) / bet sizes / pot_type(srp,3bet) /
  `Abstraction{buckets_river,buckets_turn}` / max_table_gb / mode(sample,enumerate)。
  `py.allow_threads` + 重複カード + メモリガード（dense > max_table_gb で fail-loud）。
  FlopSolver に `root_combo_evs` を追加（river と同形）。equity は flop では非計算（null）。
- **`flop_dense_table_gb` バインディング** — 解かずに dense テーブル size を見積もり、
  submit 時に過大構成を即 422 + メモリ予約を正確化。
- **In-process ジョブ基盤**（`src/gto/api/jobs.py`、外部ブローカーなし）—
  submit/status/result/cancel + TTL + **メモリ会計付き入場制御**。
  予約が予算を超えるジョブは queue（この箱 ~22GB free・flop 予約 ~dense GB →
  flop は同時 1 本、2 本目は queue で OOM しない）。skip-and-continue 入場。
  running ジョブの cancel は best-effort（Rust 側に中断フックなし＝結果破棄・
  スロットはスレッド終了時に解放、と明記）。
- **`POST /api/solve` flop 非同期ルーティング** — flop(3枚) は 202 + ジョブハンドル、
  river/turn は従来同期。`GET /api/solve/jobs/{id}`（done 時 result 同梱）/
  `DELETE`（cancel）。capabilities の flop を「async・srp/3bet・rake none・
  abstraction 既定」に更新。flop の rake!=none / pot_type=4bet は 422。
  envelope は flop で meta.abstraction を埋め equity=null。
- **Web /solver Custom Solve** — board 3 枚で flop UI（abstraction 入力・rake 無効化・
  4bet 無効化・iterations 欄）、submit→ポーリング→結果、ジョブ status 行 + cancel、
  ABSTRACTION バッジ + expl ラベル。Playwright 実描画検証（localhost、Next16 の
  allowedDevOrigins により 127.0.0.1 では HMR 遮断でハイドレーション不全＝localhost 必須）。
- 検証: pytest **94 passed**（M1a 79 + jobs 7 + flop binding 5 + flop API 3）、
  cargo gto-hu フルスイート green。実 HTTP で submit→queued/running/done→envelope 確認
  （AhKd7s 3bet 18/41, K_r=16, 40→clamp100 iters, ~11s, expl 9.74bb, table 0.2GB）。
- **残（M2）**: 6max ポジションペア行列、/solver・/simulation の gto-hu 移行、
  gto-cuda ライブラリ preview 降格。flop の rake 対応は将来（FlopSolver に rake path なし）。

### M1a — Custom Solve 基盤 (2026-06-11)
モードマトリクス・ロードマップ（`docs/superpowers/specs/2026-06-11-mode-matrix-
roadmap-design.md`）の M1a を subagent-driven で実装（plan: `docs/superpowers/
plans/2026-06-11-m1a-custom-solve-foundation.md`、branch `feat/m1a-custom-solve`）。
- **近似 multistreet 層を廃止**（gto-core multistreet.rs / solve_spot_multistreet・
  solve_flop_with_ev バインディング / multistreet_gpu.py / batch_multistreet.py /
  _sample_multistreet.py）。API・ページから到達不能を検証済み。
- **Rake + 一般和 exploitability**: `RakeModel`（none/site/live）を gto-hu の river・
  turn+river 終端に適用（fold は **matched pot** = `2*min(contrib)` で課金、未コール
  ベットは非課金）。`ExplReport` を per-player BR gain（NashConv）化。無 rake 時は
  `br0+br1` 厳密恒等式でビット同一維持。退化ツリー手計算検証（強制チェックダウン
  −1bb / 全チョップ −0.5bb / 非対称レンジ 9・−10bb）。terminal.rs は zero-sum 据置。
- **PokerVariant thin seam**: gto-core に trait（combo_count/combo_cards/blocker_mask/
  showdown_strengths）+ Nlhe 実装、gto-hu の vector ソルバを `nlhe()` 経由に配線
  （`[f64;N]` 配列は M4 PLO まで据置、既存スイートとビット同一）。
- **gto-py 拡張**: solve_hu_river / solve_hu_turn_river に ranges（1326 重み or 記法）/
  bet sizes / pot type / rake 入力 + equity・per-combo EV・NashConv 出力。combo
  エクスポートのフィルタを ranges[1]（root actor=BB）に修正（潜在バグ）。
- **GameSpec API**: `POST /api/solve`（cash×nlhe×hu×postflop、未対応軸は 422 +
  capabilities ポインタ）+ `GET /api/solve/capabilities` + 統一 SolveResult。
  `/api/hu/*` に Deprecation ヘッダ。`gto.library.range_notation` 記法パーサ。
- **Web**: /solver に Custom Solve フォーム（gto-hu 均衡 + exact exploitability
  バナー）。Playwright で実描画検証（expl 0.0012bb / EV ±0.702 / 2000 iters）。
- 検証: pytest 79 passed、cargo フルスイート green。
- **残（M1b）**: solve_hu_flop バインディング + 非同期ジョブ基盤 + flop カスタムソルブ
  → **2026-06-12 実装完了**（上記 M1b セクション）。

### Core-logic 修正適用 (2026-06-11)
2026-06-10 の包括レビュー（`docs/reviews/2026-06-10-core-logic-review.md`）の
確定 30 件を実装・マージ・検証済み（commits 0022df5, 0a4273f, 9128d7a,
0c58900, 6f95e60, 295fb60）。
- gto-cuda: B1 per-spot pot（`group_spots`）/ B2 ブロック済みコンボ /
  B3 node-pot showdown / B9 cuCtxSetCurrent。`showdown_diff` 5 本が
  RTX 5080 実機で CPU 参照と一致を検証。
- gto-py: B4 GIL 解放（2 並列 solve が 1.01× で重なる）/ B6 カード重複 422。
- gto-core: B5 希釈 / B8 DCFR 平均 / B11 reach binding。
- gto-hu: B7 lazy discount（CFR+ ビット同一）/ I1・I2・I5 / B13 1bb floor。
- Python: B10 multistreet マスク（A-first→gto-core 変換 + per-combo 分母）/
  B14 stack 毎キャッシュ / I12 dead loop 削除。
- **ライブラリ再生成**（batch_solve_rust, B2/B3 経路）: 19,305 spots / 53 分。
  事前バックアップ `_data/gto/solutions_backup_20260611`。drift: 戦略頻度
  平均|Δ|=0.114（全 spot が何らかのアクションで >0.10 移動）、BTN-100 Check
  集約が +~0.10（B2 のファントム勝ち除去）。combo 単位はボード依存（正）、
  range 集約は粗バケット（55 値/1755 ボード、新旧共通 = I11 系の既存仕様）。
- cargo 全 green / pytest 59 passed。
- 残: I3/I4/I6/I7/I8/I11、FastCfrSolver EV 視点、SubgameSolver opp_reach 重み、
  集約戦略のボードバケット（I11 系）、B12 json smoke。

### Phase 0: モノレポ基盤
- [x] Rust workspace → `gto-core`, `gto-py`, `gto-cuda`, `gto-hu`
- [x] Python uv + FastAPI (`src/gto/api/`)
- [x] Next.js 16 + Tailwind (`web/`)
- [x] ~~Docker Compose (Postgres + Redis)~~ → 撤去済み（不使用）
- [x] localhost.run トンネル（SSH鍵登録済み）

### Phase 1: コア計算
- [x] Rust ハンド評価器 → `gto-core::eval`（rank-indexed lookup table）
- [x] Rust モンテカルロエクイティ → `gto-core::equity`
- [x] pyo3バインディング（`gto-py`）
- [x] FastAPI `/api/equity` エンドポイント

### Phase 2: プリフロップ・トレーナー
- [x] 6-max 100bb GTO準拠プリフロップデータ（`src/gto/trainer/preflop_data.py`）
- [x] クイズエンジン（出題・採点・EV損失計算）
- [x] FastAPI `/api/trainer/quiz`, `/api/trainer/answer`
- [x] Neon UIトレーナー画面（`web/app/neon/page.tsx`）

### Phase 3: ポストフロップ・ソルバー (DCFR)
- [x] Rust CPU CFR (`gto-core::cfr`, `gto-core::tree`, `gto-core::multistreet`)
- [x] Rust GPU CFR (`gto-cuda`) — CUDA Driver API + NVRTC JIT（RTX 5080 / sm_120）
- [x] pyo3バインディング `gto_cuda.batch_solve_rust()`
- [x] Python GPU CFR → 削除済み（Rust GPU に一本化）
- [x] ベンチマーク: 1スポット 300iter → Rust GPU **14.4s**

### Phase A: ソリューションライブラリ
- [x] フロップ正規化（22,100 → 1,755テクスチャ）
- [x] Parquet ストア（`src/gto/library/store.py`）
- [x] バッチ計算 (`src/gto/library/batch.py`) — Rust GPU 単一パス、N=32
- [x] ライブラリ参照 API (`/api/library/flop`, `/api/library/flop/combos`, `/api/library/report`)
- [x] Library UI (`web/app/library/page.tsx`) — レンジヒートマップ、コンボ詳細
- [x] 集約 JSON キャッシュ (`/solutions/cache/{pos}_{stack}.json`) — フロント直読
- [x] **バッチ計算 全 5,265 / 5,265 スポット完了**（BTN+CO+SB vs BB, 100bb, 300iter。
      2026-06-06 に Parquet の distinct spot_id 数で確認、cache JSON 生成済み）

### Phase B: Neon UI 全機能統合
- [x] Library / Trainer を共通 Neon レイアウトに統合（NeonShell）
- [x] フロップ集計レポート画面（/report — 1755フロップのヒートマップ）
- [x] ソルバー画面（/solver — カスタムスポット → ライブ GPU 計算、約1.6s/100iter）
- [x] シミュレーション画面（/simulation — preflop fold equity + ポストフロップ solve）
- [x] **ハンド履歴レビュー（2026-06-07 完了）** — PokerStars 形式パーサ
      （`src/gto/review/`: cash 2-9 handed・Zoom・ante・all-in・side pot・
      uncalled bet 対応、per-hand try/except で不正入力に頑健）、
      `POST /api/review/parse`、`/review` ページ（Neon、ナビ追加済み）。
      プリフロップ GTO 逸脱フラグ（trainer 頻度表と照合、ok/loose/tight）。
      敵対的レビューで発見した 6 件（dead SB のポジション誤判定、EUR 通貨、
      pot 進行の uncalled bet 未控除、API サイズ無制限等）を修正済み。
      テスト: pytest 34 本（プロジェクト初の Python テスト）+ pot.ts node テスト

### 評価器バグ修正（2026-06-06, gto-core）
- [x] **2c phantom card バグ修正** — ボード3〜4枚時に評価へ 2c が混入していた問題。
      評価器を書き換え（`eval::showdown_strengths`）、showdown strength をキャッシュ化
- [x] 6〜7枚フラッシュスーツでストレートフラッシュを見逃すバグ修正
- [x] high-card / flush のキッカー順バグ修正
- [x] カード重複・combo index 整合性の strict テスト追加
- [x] **legacy Parquet 再生成完了（2026-06-07）** — 旧シャードを
      `_data/gto/solutions_legacy_backup_20260607/` に退避し、新評価器で
      5,265 スポットを再計算（GPU 15.8 分）。distinct spot_id で検証済み

### Phase D: 追加スタック・ポジション（2026-06-07 完了）
- [x] 50bb / 200bb バッチ（BTN+CO+SB vs BB、各 5,265 スポット）
- [x] HJ vs BB / UTG vs BB（100bb、3,510 スポット）
- 合計 **19,305 distinct スポット**（11 グループ × 1,755 フロップ）、
  cache JSON 11 ファイル生成済み。`/api/library/flop?position=HJ` 等で配信確認済み

### Phase C: GPU 最適化（2026-06-07 完了）
- [x] `FastCfrSolver`（gto-cuda）のホットパス浄化 — 毎 iteration の
      `cuMemAlloc`/`cuMemFree`（暗黙同期）と、ターミナル毎の half-pot
      HtoD 転送を排除（永続スクラッチ + ノード定数の事前アップロード）
- 実測（32 spots × 300 iters、`batch_solve_fast`）:
  4.18s → **2.55s**（0.131 → 0.080 s/spot、1.64×）、
  GPU util active-mean 39% → **67%**（max 47% → 77%）
- 最適化前後で戦略・EV は**完全一致**（決定的カーネル）
- 注: ライブラリのバッチ（`batch_solve_rust`、CPU 走査+GPU showdown の
  ハイブリッド）は据え置き — 19,305 スポットの数値互換性を維持するため。
  fast 系と hybrid 系は混合戦略が異なる（同一スポットで根戦略差 max ~0.11、
  CFR の混合均衡は一意でないため想定内。どちらも exploitability 未添付の近似）
- 80%+ には未到達。残りはカーネル融合 / CUDA Graphs / バッチ拡大が候補

### Phase HU: gto-hu — 抽象 HU NLHE 均衡ソルバー（2026-06-06〜06-07）

GTOWizard 同等の「正しい均衡」を出せる初のソルバー。
**equilibrium を名乗れるのは gto-hu のみ**（exploitability 数値添付が条件）。
gto-core/gto-cuda は single-street 近似のまま（river-only は正しい）。

- [x] 設計スペック（`docs/superpowers/specs/2026-06-06-hu-abstract-solver-design.md`）
- [x] Phase 1: 基盤 — config-driven リバーアクション木、厳密ベッティング状態・
      ターミナルペイオフ、closed-street ガード、AllIn 契約
- [x] Phase 2a: スカラー CFR エンジン（vanilla / CFR+ / DCFR）
  - 厳密 Best Response（未解決 infoset で fail-loud、手計算アンカー）
  - **Kuhn poker / Leduc poker で検証済み**（infoset 数ピン留め、BR 両側ブラケット）
  - DCFR 割引を per-iteration 適用に修正（per-visit だった）
- [x] Phase 2b: exact-combo ベクトル CFR リバーソルバー
  - blocker-exact O(N) showdown、厳密 best response
  - スカラー参照実装（TinyRiver）とベクトル実装の差分テストで固定
  - 全コンボのリグレットを毎 iteration 更新（ゲーム値不変条件で検証）
- [x] `solve-hu-river` CLI — exploitability (bb/hand) レポート、
      strategy.csv / summary.json を `~/projects/_data/gto/hu/` へ出力
  ```bash
  cargo run --release -p gto-hu --bin solve-hu-river -- \
    --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000
  ```
- [x] tree/solver 統計と CSV/JSON ストラテジーエクスポート
- [x] **Turn+River ソルバー（Phase 3, 2026-06-07）** — リバーを public chance node として
      ターン+リバーを解く `TurnRiverSolver`
  - チャンス重み 1/44 厳密列挙 + シード付き public chance sampling（48/44 補正で不偏）
  - オールイン後はチャンス → 即ショーダウン（ベッティングなし）
  - exploitability / ゲーム値は学習モードに関わらず常に厳密列挙で計算
  - TinyTurnRiver スカラー参照ゲームとの差分テストで検証
    （ゲーム値 5.4353 vs 5.4196、予算 0.0901 内で一致）
  - `solve-hu-turn-river` CLI（実測: 10k sampled iters ≈ 38s、expl 0.329 bb、
    テーブル 172 MB @ pot 20bb / stack 90bb）
  ```bash
  cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
    --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
  ```
- ゲーム範囲: HU NLHE cash、SRP ターン+リバー
  （ターン: check / b50 / b100、vs bet: fold / call / raise 3x-or-jam。
  リバー: check / bet 75% / bet 150% / all-in、vs bet: fold / call / raise-jam）
- [x] **フロップ木（Phase 4, 2026-06-07）** — `FlopSolver`: フロップ固定ボード、
      ターン+リバーを入れ子 public chance node として解く
  - チャンス重み 1/45（ターン）・1/44（リバー）厳密列挙 +
    シード付きサンプリング（49/45 補正で不偏）。
    **サンプリングはターンのみ・リバーは常に列挙** — 二段同時サンプリング
    だとリバー文脈（49×48=2,352）あたりの更新が乏しく停滞する
    （実測: 10k iter で expl 5.9bb のまま）
  - オールイン・フロップは Chance→Chance→Showdown（ベッティングなし）。
    全 Showdown は River ストリート（ショートカット禁止をテストで保証）
  - exploitability / ゲーム値は常に両段厳密列挙（avg 戦略は行列化で高速化）
  - **lazy slab 格納** — 密テーブルは河ノードあたり 2,352 文脈で爆発するため
    訪問時確保。CLI は密サイズを事前見積もりして `--max-table-gb`（既定 8）
    超過なら fail-loud（**フル SRP 100bb は 105.35 GB → 拒否**。
    Phase 6 のバケッティング待ち）
  - `RaiseRule::ToFactorThenJam` 追加（spec §6 SRP フロップ
    「vs raise: fold/call/jam」を深い SPR でも保証）、
    `FlopTreeConfig::srp()` / `threebet()` プリセット
  - TinyFlopTurnRiver スカラー参照ゲームとの差分テストで検証
    （ゲーム値 2.9860 vs 2.9988、予算 0.2756 内で一致）
  - `solve-hu-flop` CLI — 実測（3BP AhKd7s, pot 18bb / stack 41bb,
    sampled 5k iters）: 433 ノード・テーブル 10.62 GB、学習 18.1 分、
    expl **0.616 bb/hand**（ターン文脈あたり ~100 更新。要追加 iteration）。
    strategy_flop.csv / strategy_turn_agg.csv / summary.json を
    `_data/gto/hu/` へ出力
  ```bash
  cargo run --release -p gto-hu --bin solve-hu-flop -- \
    --board AhKd7s --pot-type 3bp --pot 18 --stack 41 \
    --iterations 5000 --max-table-gb 12
  ```
- [x] **プリフロップ木（Phase 5, 2026-06-08）** — spec §6 の固定アクション台帳
      （limp ライン含む: SB fold/limp/r2.5 → BB check/r4/r6 …、vs jam は
      fold/call）を `build_preflop_tree` で実装
  - `NodeKind::NextStreet { pot_type }` 追加 — 非フォールドのクローズは
    pot type（limped/srp/3bp/4bp/allin_preflop）タグ付き葉。
    リンプ特例（レイズ前の SB コールはストリートを閉じない）を
    `BettingState` に実装。ショートスタックではサイズが all-in にキャップ
  - **簡易ポストフロップ価値モデル**（spec §13 の "simplified postflop
    value model for debugging"）: 葉のペイオフ = `eq(c,o)×pot − contrib`。
    eq はシード付き MC 全コンボペア表（`EquityTable::monte_carlo`）で、
    モデル内では厳密な BR / exploitability を計算。
    **フルゲーム均衡ではない**（Phase 6 で実ポストフロップ部分木に置換）
  - TinyPreflop スカラー参照との差分テスト（共有トイ equity 表、
    scalar expl 0.0648 / vector 0.00035、ゲーム値予算内一致）
  - アンカーテスト: AA はオープンフォールドしない（<2%）、
    AA は 4bet-jam にほぼ純粋コール（>95%）。
    MC 表検証: AA vs KK 0.79–0.84、AKs vs QQ 0.42–0.50、ゼロサム鏡像
  - `solve-hu-preflop` CLI — 実測（100bb, 800 iters, samples 200）:
    expl **0.0008 bb/hand（モデル内）**、学習 25 秒。
    SB ルート fold 19.1% / limp 42.8% / open 38.1%（ポジション優位の
    無いモデルでは limp 過多が整合的。AA はトラップ limp ≈100%、72o フォールド）。
    MC エクイティ表構築は単線程 644 秒 — rayon 並列化が改善候補。
    strategy_preflop.csv / strategy_root_classes.csv（169 クラス集約）/
    summary.json（モデル明記）を `_data/gto/hu/` へ出力
- [x] **リバー・バケッティング（Phase 6 前提, 2026-06-08）** —
      戦略空間のみの strength-percentile バケット共有
      （設計: `docs/superpowers/specs/2026-06-08-river-bucketing-design.md`）
  - 走査・ブロッカー・チャンス重み・ショーダウンは 1326 コンボ厳密のまま、
    リバーノードの regret/strategy 行のみ K_r バケットで共有。
    per-combo 厳密 BR がそのまま使えるため **exploitability に抽象化損失が
    測定値として含まれる**（主張は弱まらない）
  - 密テーブル: フル SRP 100bb で 105.35 GB → **K=128 で 10.49 GB**
    （K=64 で 5.42 GB）。`solve-hu-flop --buckets-river K`
  - **敵対的スペックレビュー（3 レンズ）がブロッカーを出荷前に検出**:
    重みなしリグレット集約はボードブロック・コンボ（SD 値 0、fold 値負）が
    共有行を汚染し expl 70× 悪化。修正: トラバーサーのディール確率
    （レンジ × ボードマスク）で重み付け。実測 K=2: 2.59→0.42、
    K=256: 0.267→**0.0119**（exact 0.0172 同等）。
    あわせて K=N の無言 exact フォールバック（差分テストを無意味化）も排除
  - スート同型化の旧見積もり（3-5×）は誤りと判明（レインボーフロップでは
    フロップ固定の自己同型が自明のみ）— スペック §1 に記録
  - MC エクイティ表を rayon 並列化（644 秒 → 数十秒、ペア毎シードで決定的）
  - **フル SRP 100bb 初ソルブ実測**（AhKd7s, pot 5bb / stack 97.5bb,
    K=128, sampled 3000 iters, uniform レンジ）: 学習 48.7 分 +厳密 BR、
    expl **1.174 bb/hand**（ターン文脈 ~61 訪問の浅い収束 + 抽象化損失込み。
    要追加 iteration）。BB ルート: check 77.2% / b33 15.8% / b75 7.0%
  - **ターンバケッティング追加（同日）** — mean-river-percentile スコアの
    tier-grouped ビン（`Abstraction{buckets_river, buckets_turn}`、
    CLI `--buckets-turn`）。K_t=1326 で exact と全桁一致、
    ダイヤル K_t=2: 0.337 → K_t=256: 0.027
  ```bash
  cargo run --release -p gto-hu --bin solve-hu-flop -- \
    --board AhKd7s --pot 5 --stack 97.5 --buckets-river 128 \
    --max-table-gb 12 --iterations 3000
  ```
- [x] **フルブループリント（Phase 6, 2026-06-08）** — プリフロップ木の
      NextStreet 葉を実ポストフロップ部分木に接続した合成ゲームを
      単一 CFR で解く `BlueprintSolver` + `solve-hu-blueprint` CLI
      （設計 v2: `docs/superpowers/specs/2026-06-08-blueprint-design.md`。
      敵対的レビューがフロップディール測度のブロッカーを設計段階で検出）
  - **M-flop 抽象ゲーム**: joint measure μ ∝ w0·w1·w_m·legal。
    Z(c,o) 補正はプリフロップ層に集約（fold 端末・正規化子）、
    ポストフロップ走査は O(N) 不変。8 部分木家族（葉ノード id キー、
    (24,88) limp-3bet 2 ラインは別管理）、`FlopTreeConfig::fourbet()` 新設
  - オールイン葉は厳密 M-flop ランアウト・エクイティ
    （showdown_strengths ベース、~1 秒/flop。evaluate 毎ペア方式は
    実測 ~60× 遅く差し替え）
  - テスト 4/4: 退化合成 M=1 が standalone FlopSolver と**厳密一致**
    （value/expl/戦略 < 1e-9）、敵対的オールイン・フィクスチャ
    （naive 実装は必ず落ちる設計）、K=N handoff 全桁一致、
    フル台帳 M=3 スモーク（expl 0.348→0.079）
  - 出力規律: 「M-flop 抽象ゲーム上の厳密 exploitability 付き CFR
    プロファイル」— equilibrium とは呼ばない。フル NLHE の expl ではない
  - **(leaf, m) サブゲーム並列化（rayon, 3 フェーズ走査）** —
    逐次版とビット同一（assert_eq テストで固定）。実測 11.9 → **1.54 s/iter
    （7.7×）**、1500 iters が 5h → 40 分に
  - **フルラン実測（2026-06-09, M=3 AhKd7s/QsJh2c/8d8h3s）** — expl は
    iteration / バケット細分 / 適切な重みで素直に下がる:
    | iters | K_r | weights | expl (bb) | SB fold/limp/open | 学習 |
    |---|---|---|---|---|---|
    | 1500 | 16 | uniform | 1.506 | 35.9 / 55.6 / 8.5% | 40.5 分 |
    | 8000 | 16 | uniform | 0.283 | 18.6 / 61.9 / 19.5% | 3.5 時間 |
    | 15000 | 32 | 0.4/0.4/0.2 | **0.147** | 18.0 / 57.2 / 24.8% | 6.8 時間 |
    初回比 **10× 改善**。BR は SB 0.266 / BB 0.028（BB 側はほぼ不可剥離、
    残差は SB の多分岐に集中）。SB open も実ポーカーに接近（8.5→24.8%）。
    残 0.147 bb は抽象化損失（K_r=32・M=3）+ 残収束で、3-flop 抽象ゲーム内の
    厳密値（フル NLHE の expl ではない）。テーブル 32.3 GB
  - `gto.library.sample_flops` — canonical 頻度から --flops/--weights を
    生成（diverse/frequency/random、pytest 37 本）
- テスト: 27ファイル・156 本（betting / payoff / tree / regret / Kuhn /
  Leduc / TinyRiver / differential / BR / reports /
  turn・flop・preflop の tree / chance / solver / differential / reports /
  flop bucketing / blueprint）

---

## TODO（優先順）

開発計画の全体像（WP1–WP6・ゲート・見積もり）は
[docs/development-plan.md](./docs/development-plan.md) を参照。

### 次（M2 — WP4）
- [ ] 6max ポジションペア行列 v1（BB-as-sole-defender、不足 8 チャート）
- [ ] /solver・/simulation を gto-cuda single-street から gto-hu `/api/solve` へ移行
- [ ] gto-cuda ライブラリを `equilibrium_claim=false` の preview tier に降格
- [ ] Tournament-HU（ante/BB-ante + 10–40bb シャロー）
- [ ] 実験: intra-solve CPU 並列化（rayon over 44–48 リバー文脈）

### Phase HU 続き（gto-hu ロードマップ）
- [~] ブループリント品質ラン（WP2、G2 の入力）— 2026-06-12 の初回は
      **OOM kill**（M2 開発の同時負荷で dense 31.98GB が 48GB を超過、結果なし）。
      **2026-06-13 02:48 UTC 再実行**（K_r=24/K_t=16/M=3/15k iters、dense
      23.95GB、単独実行、~09:48 UTC 完了見込み）。所見: **K_t はメモリをほぼ
      減らさず、dense を支配するのは K_r**（K_t 32→16 で 31.98→31.91GB）。
      結果は `_data/gto/hu/blueprint_quality_20260613/`。
- [ ] 将来: f32 テーブル（×2）、ボードバケッティング、ディスクバック
      （M を実用規模に上げる前提技術）

### Phase C 続き（任意）
- [ ] GPU util 67% → 80%+（カーネル融合 / CUDA Graphs / バッチ拡大）
- [ ] ライブラリバッチの `batch_solve_fast` 移行判断
      （2.3× 高速だが数値が変わるため再計算 75 分とセット。
      combo_strategies 出力の追加実装も必要）

### Phase E: 商用化
- [ ] Supabase 認証（ユーザ管理）
- [ ] Stripe サブスクリプション
- [ ] Cloud Run / Fly.io デプロイ
- [ ] カスタムドメイン

### 留意事項
- ワークスペース `uv sync`（`--no-sync` なしの `uv run` を含む）は
  maturin 製の `gto_py` / `gto_cuda` を venv から消す。消えたら
  `maturin develop --uv` で再ビルド（本日 2 回発生）

---

## 起動コマンド

```bash
# 依存インストール（ワークスペースルートで一括）
cd ~/projects && make install

# Rust拡張リビルド（Rust 変更時のみ）
cd ~/projects/gto && source ~/.cargo/env
uv run --no-sync maturin develop --manifest-path crates/gto-py/Cargo.toml   --release
uv run --no-sync maturin develop --manifest-path crates/gto-cuda/Cargo.toml --release

# バックエンド :8000 / フロントエンド :3000
uv run --no-sync uvicorn gto.api.main:app --host 0.0.0.0 --port 8000
cd web && pnpm exec next dev

# テスト
uv run --no-sync pytest gto/tests
cargo test --manifest-path gto/Cargo.toml

# HU リバー / ターン+リバー / フロップ ソルバー
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000
cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
  --board AhKd7s2c --pot 20 --stack 90 --iterations 10000
cargo run --release -p gto-hu --bin solve-hu-flop -- \
  --board AhKd7s --pot-type 3bp --pot 18 --stack 41 \
  --iterations 5000 --max-table-gb 12
cargo run --release -p gto-hu --bin solve-hu-preflop -- \
  --stack 100 --iterations 800 --samples 200   # 簡易価値モデル（均衡ではない）

# バッチ計算（追加スタック・ポジション例）
uv run --no-sync python -m gto.library.batch --positions HJ,UTG --stacks 100 --iters 300 --batch-size 32

# 外部公開
ssh -i ~/.ssh/id_ed25519 -o ServerAliveInterval=20 -R 80:localhost:3000 ssh.localhost.run
```

---

## パフォーマンス実績

| 処理 | CPU Rust | Python GPU（廃止） | Rust GPU hybrid | Rust GPU fast（Phase C 後） |
|---|---|---|---|---|
| 1スポット 300iter（バッチ N=32） | 53s | 18.2s | 0.18s/spot | **0.080s/spot** |
| showdown kernel | ~200ms | 1.7ms (118x) | 1.7ms | 1.7ms |
| GPU使用率（active-mean） | — | 28% | ~40% | **67%（max 77%）** |
| 5,265スポット全計算 | ~4.7h | ~2.3h | **15.8分** | （未移行・将来 ~7分） |

- hybrid = `batch_solve_rust`（CPU 走査 + GPU showdown）— ライブラリ採用中
- fast = `batch_solve_fast`（全 GPU 反復、Phase C でホットパス浄化済み）

## アーキテクチャ（現在）

```
gto/
├── crates/
│   ├── gto-core/    Rust CPU: 評価器・エクイティ・CFR・multistreet
│   ├── gto-cuda/    Rust GPU: CUDA Driver API + NVRTC JIT バッチ CFR
│   ├── gto-hu/      Rust: 抽象 HU NLHE 均衡ソルバー（CFR+/DCFR、厳密 BR、
│   │                river / turn+river / flop の 3 CLI）
│   └── gto-py/      pyo3バインディング
├── src/gto/
│   ├── api/         FastAPI（equity/trainer/solver/library/simulation/review）
│   ├── trainer/     プリフロップ出題エンジン（Python）
│   ├── review/      PokerStars ハンド履歴パーサ + GTO 逸脱フラグ
│   └── library/     バッチ計算 + Parquet ストア
├── tests/           pytest（review パーサ / API、fixtures 付き）
├── web/             Next.js 16（/neon /library /report /solver /simulation /review）
├── docs/superpowers/  設計スペック・実装プラン（HU ソルバー）
└── _data/gto/       solutions/（Parquet+cache）, hu/（CSV/JSON）※ワークスペース直下
```

詳細な実装スナップショットは [IMPLEMENTATION.md](./IMPLEMENTATION.md) を参照。
