# GTO Poker Suite — 進捗 & TODO

最終更新: 2026-06-07

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
- [ ] ハンド履歴レビュー（PokerStars等パーサ）← Phase B 唯一の未着手項目

### 評価器バグ修正（2026-06-06, gto-core）
- [x] **2c phantom card バグ修正** — ボード3〜4枚時に評価へ 2c が混入していた問題。
      評価器を書き換え（`eval::showdown_strengths`）、showdown strength をキャッシュ化
- [x] 6〜7枚フラッシュスーツでストレートフラッシュを見逃すバグ修正
- [x] high-card / flush のキッカー順バグ修正
- [x] カード重複・combo index 整合性の strict テスト追加
- ⚠️ **旧評価器で計算した legacy Parquet が `_data/gto/solutions/` に残存**。
  フロップ/ターンの数値を信頼する前に再生成が必要（GPU 約24〜40分）

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
- テスト: 17ファイル・80テスト（betting / payoff / tree / regret / Kuhn /
  Leduc / TinyRiver / differential / BR / reports /
  turn tree / turn chance / turn solver / turn differential / turn reports）

---

## TODO（優先順）

### 🔥 すぐやる
1. **legacy Parquet 再生成** — 評価器修正前に計算した 5,265 スポットを
   新評価器で再計算（GPU 約24〜40分）。完了までライブラリのフロップ/ターン数値は参考値
   ```bash
   nohup uv run --no-sync python -m gto.library.batch \
     --positions BTN,CO,SB --stacks 100 --iters 300 --batch-size 32 \
     > /tmp/batch.log 2>&1 &
   ```

### Phase HU 続き（gto-hu ロードマップ）
- [ ] フロップ木（Flop→Turn→River のフル SRP）
- [ ] プリフロップ（limp 含む）
- [ ] フルブループリント

### Phase B 残り
- [ ] ハンド履歴レビュー（PokerStars等パーサ）

### Phase C: GPU完全最適化
- [ ] D2Dコピー（ホスト経由を廃止）
- [ ] CUDAストリームによる GPU/CPU 非同期オーバーラップ
- [ ] GPU使用率 47% → 80%+ 目標

### Phase D: 追加スタック・ポジション
- [ ] 50bb, 200bb のバッチ計算
- [ ] HJ vs BB, UTG vs BB

### Phase E: 商用化
- [ ] Supabase 認証（ユーザ管理）
- [ ] Stripe サブスクリプション
- [ ] Cloud Run / Fly.io デプロイ
- [ ] カスタムドメイン

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

# HU リバーソルバー / ターン+リバーソルバー
cargo run --release -p gto-hu --bin solve-hu-river -- \
  --board AhKd7s2c9h --pot 20 --stack 90 --iterations 10000
cargo run --release -p gto-hu --bin solve-hu-turn-river -- \
  --board AhKd7s2c --pot 20 --stack 90 --iterations 10000

# 外部公開
ssh -i ~/.ssh/id_ed25519 -o ServerAliveInterval=20 -R 80:localhost:3000 ssh.localhost.run
```

---

## パフォーマンス実績

| 処理 | CPU Rust | Python GPU（廃止） | Rust GPU（現行） |
|---|---|---|---|
| 1スポット 300iter | 53s | 18.2s | **14.4s** |
| showdown kernel | ~200ms | 1.7ms (118x) | 1.7ms |
| GPU使用率 | — | 28% | 47%（ピーク97%）|
| 5265スポット全計算 | ~4.7h | ~2.3h | **~40分** |

## アーキテクチャ（現在）

```
gto/
├── crates/
│   ├── gto-core/    Rust CPU: 評価器・エクイティ・CFR・multistreet
│   ├── gto-cuda/    Rust GPU: CUDA Driver API + NVRTC JIT バッチ CFR
│   ├── gto-hu/      Rust: 抽象 HU NLHE 均衡ソルバー（CFR+/DCFR、厳密 BR）
│   └── gto-py/      pyo3バインディング
├── src/gto/
│   ├── api/         FastAPI（equity/trainer/solver/library/simulation）
│   ├── trainer/     プリフロップ出題エンジン（Python）
│   └── library/     バッチ計算 + Parquet ストア
├── web/             Next.js 16（/neon /library /report /solver /simulation）
├── docs/superpowers/  設計スペック・実装プラン（HU ソルバー）
└── _data/gto/       solutions/（Parquet+cache）, hu/（CSV/JSON）※ワークスペース直下
```

詳細な実装スナップショットは [IMPLEMENTATION.md](./IMPLEMENTATION.md) を参照。
