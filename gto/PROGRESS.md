# GTO Poker Suite — 進捗 & TODO

最終更新: 2026-06-07（夜: 再生成・Phase B/C/D・HU フロップ木を完了）

---

## 完了済み

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
  - **初回フルラン完了（2026-06-09）** — M=3 AhKd7s/QsJh2c/8d8h3s 均等重み,
    K_r=16/K_t=32, 1500 sampled iters, 学習 40.5 分 + 厳密 BR:
    **expl 1.5059 bb/hand（3-flop 抽象ゲーム内・厳密）**, ゲーム値 SB
    +0.2241 bb。SB ルート: fold 35.9% / limp 55.6% / open 8.5% —
    実 GTO から遠い（浅い収束 ~30 visits/turn-ctx + 粗い盤面抽象 +
    デモ用均等重み）。パイプライン実証が目的の初値であり、品質は
    iteration 増（並列化で 15k≈7h が可能に）と M/バケット拡大が前提
  - `gto.library.sample_flops` — canonical 頻度から --flops/--weights を
    生成（diverse/frequency/random、pytest 37 本）
- テスト: 27ファイル・156 本（betting / payoff / tree / regret / Kuhn /
  Leduc / TinyRiver / differential / BR / reports /
  turn・flop・preflop の tree / chance / solver / differential / reports /
  flop bucketing / blueprint）

---

## TODO（優先順）

### Phase HU 続き（gto-hu ロードマップ）
- [ ] ブループリント品質ラン — sample_flops の頻度重み + 15k iters（~7h）で
      expl がどこまで下がるか計測。K_r/K_t の感度も
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
