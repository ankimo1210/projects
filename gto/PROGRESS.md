# GTO Poker Suite — 進捗 & TODO

最終更新: 2026-05-17

---

## 完了済み

### Phase 0: モノレポ基盤
- [x] Rust workspace → `gto-core`, `gto-py`, `gto-cuda`（5→3クレートに統合済み）
- [x] Python uv + FastAPI (`src/gto/api/`)
- [x] Next.js 16 + Tailwind (`web/`)
- [x] ~~Docker Compose (Postgres + Redis)~~ → 撤去済み（不使用）
- [x] localhost.run トンネル（SSH鍵登録済み）

### Phase 1: コア計算
- [x] Rust ハンド評価器 → `gto-core::card`
- [x] Rust モンテカルロエクイティ → `gto-core::equity`
- [x] pyo3バインディング（`gto-py`）
- [x] FastAPI `/api/equity` エンドポイント

### Phase 2: プリフロップ・トレーナー
- [x] 6-max 100bb GTO準拠プリフロップデータ（`src/gto/trainer/preflop_data.py`）
- [x] クイズエンジン（出題・採点・EV損失計算）
- [x] FastAPI `/api/trainer/quiz`, `/api/trainer/answer`
- [x] Neon UIトレーナー画面（`web/app/neon/page.tsx`）— 採用確定、A〜H サンプルは削除済み

### Phase 3: ポストフロップ・ソルバー (DCFR)
- [x] Rust CPU CFR (`gto-core::cfr`, `gto-core::tree`)
- [x] Rust GPU CFR (`gto-cuda`) — CUDA Driver API + NVRTC JIT
- [x] pyo3バインディング `gto_cuda.batch_solve_rust()`
- [x] Python GPU CFR → 削除済み（Rust GPU に一本化）
- [x] ベンチマーク: 1スポット 300iter → Rust GPU **14.4s** (Python GPU 18.2s比 1.3x)

### Phase A: ソリューションライブラリ
- [x] フロップ正規化（22,100 → 1,755テクスチャ）
- [x] Parquet ストア（`src/gto/library/store.py`）— staging DB・merge 廃止
- [x] バッチ計算 (`src/gto/library/batch.py`) — Rust GPU 単一パス、N=32
- [x] ライブラリ参照 API (`/api/library/flop`, `/api/library/flop/combos`, `/api/library/report`)
- [x] Library UI (`web/app/library/page.tsx`) — レンジヒートマップ、コンボ詳細
- [x] 集約 JSON キャッシュ (`/solutions/cache/{pos}_{stack}.json`) — フロント直読

**バッチ計算状況**: BTN+CO+SB vs BB, 100bb, 全5265スポット（1755フロップ×3ポジション）
- 完了: **1,256 / 5,265**（24%）
- 残り: **4,009スポット**
- ETA（Rust GPU）: **約40分**

---

## TODO（優先順）

### 🔥 すぐやる
1. **バッチ再開** — 残り 4,009 スポットを計算
   ```bash
   nohup uv run python -m gto.library.batch \
     --positions BTN,CO,SB --stacks 100 --iters 300 --batch-size 32 \
     > /tmp/batch.log 2>&1 &
   tail -f /tmp/batch.log
   ```

### Phase B: Neon UI 全機能統合
- [x] Library画面とTrainer画面を共通 Neon レイアウトに統合（NeonShell）
- [x] フロップ集計レポート画面（1755フロップのヒートマップ、/solutions rewrite追加）
- [x] ソルバー画面（/solver — カスタムスポット → ライブ GPU 計算、1.6s/100iter）
- [ ] ハンド履歴レビュー（PokerStars等パーサ）

### Phase C: GPU完全最適化
- [ ] D2Dコピー（ホスト経由を廃止）
- [ ] CUDAストリームによる GPU/CPU 非同期オーバーラップ
- [ ] GPU使用率 47% → 80%+ 目標

### Phase D: 追加スタック・ポジション
- [ ] 50bb, 200bb のバッチ計算
- [ ] HJ vs BB, UTG vs BB
- [ ] ターン・リバー多ストリート対応

### Phase E: 商用化
- [ ] Supabase 認証（ユーザ管理）
- [ ] Stripe サブスクリプション
- [ ] Cloud Run / Fly.io デプロイ
- [ ] カスタムドメイン

---

## 起動コマンド

```bash
# バックエンド
uv run uvicorn gto.api.main:app --host 0.0.0.0 --port 8000

# フロントエンド
cd web && pnpm exec next dev

# Rust拡張リビルド（変更時のみ）
source ~/.cargo/env
uv run maturin develop --manifest-path crates/gto-py/Cargo.toml --release
uv run maturin develop --manifest-path crates/gto-cuda/Cargo.toml --release

# 外部公開
ssh -i ~/.ssh/id_ed25519 -o ServerAliveInterval=20 -R 80:localhost:3000 ssh.localhost.run

# バッチ計算（残り4009スポット）
nohup uv run python -m gto.library.batch \
  --positions BTN,CO,SB --stacks 100 --iters 300 --batch-size 32 \
  > /tmp/batch.log 2>&1 &

# キャッシュ再構築（バッチ完了後は自動、手動でも可）
uv run python -m gto.library.batch --rebuild-cache
```

---

## パフォーマンス実績

| 処理 | CPU Rust | Python GPU | Rust GPU |
|---|---|---|---|
| 1スポット 300iter | 53s | 18.2s | **14.4s** |
| showdown kernel | ~200ms | 1.7ms (118x) | 1.7ms |
| GPU使用率 | — | 28% | 47%（ピーク97%）|
| 5265スポット ETA | ~4.7h | ~2.3h | **~40分** |

## アーキテクチャ（現在）

```
gto/
├── crates/
│   ├── gto-core/    Rust: カード・エクイティ・CFR（3クレートを統合）
│   ├── gto-cuda/    Rust: CUDA JIT + Rust DCFR (GPU)
│   └── gto-py/      pyo3バインディング
├── src/gto/
│   ├── api/         FastAPI
│   ├── trainer/     プリフロップ出題エンジン（Python）
│   └── library/     バッチ計算 + Parquet ストア
├── web/             Next.js 16 + Tailwind（/neon, /library）
└── data/solutions/  Parquet（spots/ agg/ combos/ reports/ cache/）
```
