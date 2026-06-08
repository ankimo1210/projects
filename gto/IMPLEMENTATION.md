# GTO Poker Suite — 実装まとめ

最終更新: 2026-06-08
（README.md / ARCHITECTURE.md / PROGRESS.md / CLAUDE.md と実データから作成した実装スナップショット）

---

## 1. プロジェクト概要

テキサスホールデムの GTO（Game Theory Optimal）分析 Web アプリ。
プリフロップトレーナー・事前計算ソリューションライブラリ・ライブ GPU ソルバー・
レンジシミュレーションを 1 つの Neon/Cyberpunk テーマの UI に統合している。
個人開発・将来商用化（GTOWizard 同等機能）想定。

| ページ | URL | 機能 |
|---|---|---|
| TRAINER | `/neon` | プリフロップクイズ（出題 → 回答 → GTO 頻度との差分・EV損失表示） |
| LIBRARY | `/library` | 事前計算済みフロップソリューション参照（1755 テクスチャ × 3 ポジション） |
| REPORT | `/report` | 1755 フロップのヒートマップ（dominant action / check%） |
| SOLVER | `/solver` | カスタムスポットのライブ GPU CFR 計算（約 1.6s / 100iter） |
| SIMULATE | `/simulation` | プリフロップ fold equity + BB ディフェンスレンジ + ポストフロップ solve |
| REVIEW | `/review` | PokerStars ハンド履歴の貼り付け → パース → ストリート別リプレイ + プリフロップ GTO 逸脱フラグ |
| HU·GTO | `/hu` | gto-hu 厳密均衡をライブ計算（RIVER / TURN+RIVER タブ、exact exploitability 表示）。単一ストリート近似の /solver とは別系統。flop/blueprint は重量級のため CLI 専用 |

---

## 2. 技術スタック

```
[Frontend]  Next.js 16 + React 19 + TypeScript + Tailwind v4
[Backend]   FastAPI + Pydantic
[Solver]    Rust workspace（4クレート）
            ├─ gto-core   CPU: CFR/DCFR・マルチストリート木・ハンド評価器
            ├─ gto-cuda   GPU: NVRTC JIT カーネル（RTX 5080 / sm_120）
            ├─ gto-hu     CPU: 抽象 HU NLHE 均衡ソルバー（exploitability 付き）
            └─ gto-py     pyo3 バインディング
[Data]      Parquet（spots / agg / combos / reports）+ JSON キャッシュ
[管理]      uv（ワークスペース共有 .venv）/ cargo / pnpm
```

---

## 3. レイヤ別の実装

### 3.1 Rust ソルバーコア — `crates/gto-core/`（CPU）

| ファイル | 内容 |
|---|---|
| `card.rs` | カード型・パース（`card = rank*4 + suit`） |
| `eval.rs` | 7-card ハンド評価器（rank-indexed lookup table） |
| `equity.rs` | Monte Carlo エクイティ |
| `range.rs` | `Range = weights[1326]` + blocker 処理 |
| `tree.rs` | マルチストリートゲーム木（Flop→Turn→River） |
| `cfr.rs` | 単一スポット CFR |
| `multistreet.rs` | Backward Induction（River→Turn→Flop）。**正しい多ストリート solve はここのみ** |

### 3.2 GPU ソルバー — `crates/gto-cuda/`

RTX 5080（Blackwell / sm_120）が当時の PyTorch 非対応だったため、
**CUDA Driver API + NVRTC JIT を直接呼ぶ**構成。

| ファイル | 内容 |
|---|---|
| `cuda_ffi.rs` | CUDA Driver API の FFI バインド（HtoD/DtoH/DtoD） |
| `kernels.rs` | NVRTC で JIT コンパイルする `.cu` ソース（showdown / regret） |
| `cfr.rs` | `BatchCfrSolver` — CPU 走査 + GPU showdown のハイブリッド。ライブラリのバッチで採用 |
| `fast_cfr.rs` | `FastCfrSolver` — 全 GPU 反復。Phase C でホットパスの alloc/free・HtoD を排除（0.080s/spot、util 67%） |
| `lib.rs` | pyo3 公開関数 `batch_solve_rust()` / `batch_solve_fast()` |

### 3.2b 抽象 HU 均衡ソルバー — `crates/gto-hu/`（CPU）

**equilibrium を名乗れるのは gto-hu のみ**（exploitability 数値添付が条件）。

| モジュール | 内容 |
|---|---|
| `game/` | 厳密チップ会計（i64 centi-bb）、`BettingState`、ペイオフ |
| `tree/` | config 駆動アクション木（river / turn+river / flop+turn+river） |
| `solver/` | スカラー参照 CFR + exact-combo ベクトル CFR（CFR+/DCFR）、public chance sampling、`FlopSolver`（lazy slab + リバー戦略空間バケッティング `--buckets-river`: 105GB→10.5GB@K=128、expl に抽象化損失が含まれる）、`PreflopSolver`（簡易価値モデル）、MC エクイティ表（rayon） |
| `games/` | Kuhn / Leduc / TinyRiver / TinyTurnRiver / TinyFlopTurnRiver / TinyPreflop（差分テスト用参照ゲーム） |
| `validation/` | 厳密 Best Response・exploitability（bb/hand、常に列挙） |
| `bin/` | `solve-hu-river` / `solve-hu-turn-river` / `solve-hu-flop` / `solve-hu-preflop` / `solve-hu-blueprint` CLI |

### 3.3 Python バインディング — `crates/gto-py/`

pyo3 で `solve_spot` / `solve_spot_multistreet` / `equity` / `solve_hu_river`・`solve_hu_turn_river`（gto-hu 厳密均衡、exact exploitability 付き）を公開。
ビルドは `maturin develop --release`（gto-py / gto-cuda それぞれ）。

### 3.4 バックエンド API — `src/gto/api/`

FastAPI。`main.py` で CORS + `/solutions` の StaticFiles マウント。

| ルーター | エンドポイント |
|---|---|
| `health.py` | `/health` |
| `equity.py` | `/api/equity` |
| `trainer.py` | `/api/trainer/quiz`, `/api/trainer/answer` |
| `solver.py` | `/api/solver/solve`（ライブ単一スポット） |
| `library.py` | `/api/library/flop`, `/api/library/flop/combos`, `/api/library/report` |
| `simulation.py` | `/api/simulation/run`（preflop + postflop 連結） |
| `review.py` | `/api/review/parse`（PokerStars ハンド履歴 → 構造化 JSON + 逸脱フラグ） |
| `hu.py` | `/api/hu/river`・`/api/hu/turn-river`（gto-hu 厳密均衡 + exact exploitability + per-combo 戦略。turn+river は ~30-40s） |

### 3.5 ソリューションライブラリ — `src/gto/library/`

| ファイル | 内容 |
|---|---|
| `flop_canon.py` | フロップ正規化：22,100 → **1,755 テクスチャ** |
| `schema.py` | `spot_id` 生成 |
| `store.py` | Parquet 読み書き + フロント直読用 cache JSON 生成 |
| `batch.py` | バッチ事前計算 CLI（Rust GPU 単一パス、batch-size 32） |
| `range_builder.py` | preflop 頻度表 → combo weights[1326] 変換 |
| `sample_flops.py` | blueprint 用 M-flop 選定（canonical 頻度重み付きサンプリング） |

### 3.6 トレーナー — `src/gto/trainer/`

`preflop_data.py` に 6-max 100bb の GTO 準拠頻度表（RFI / FACING）を
**ハードコード**。クイズエンジンが出題・採点・EV 損失計算を行う。
（CFR で解いたものではない近似テーブル — 既知の制限 §6 参照）

### 3.7 フロントエンド — `web/`

Next.js App Router。`next.config.ts` の rewrite で `/api/*` と `/solutions/*`
を FastAPI :8000 へプロキシ（CORS 回避・1 ポート開発）。

- ページ: `app/{neon,library,report,solver,simulation}/page.tsx`
- 共通 UI: `components/layout/NeonShell.tsx`（ヘッダ+ナビ）、`components/ui/RangeHeatmap.tsx`（13×13 グリッド）
- API クライアント: `lib/{api,trainer-api,library-api,solver-api,simulation-api}.ts`
- 状態管理は React `useState` のみ（規模的に十分と判断）

---

## 4. アルゴリズム

- **CFR variant**: Discounted CFR（Brown & Sandholm 2019）— α=1.5, β=0
- **ベットサイズ**:
  - `gto-core`（multistreet）: Flop 50% / Turn 75% / River 75%、レイズ 2.5x（max 1 raise）
  - `gto-cuda`（single-street）: 33% / 75% / 100% pot を同時評価、max 2 bets/street
- **カードエンコーディング**: `card = rank*4 + suit`（As = 51）、
  `combo_index(lo,hi) = lo*51 - lo*(lo-1)/2 + hi - lo - 1`、全 1326 コンボ
- **ハンド評価**: rank-indexed lookup table（5/7-card）

### データフロー（3 系統）

1. **ライブソルブ**: UI → `POST /api/solver/solve` → `batch_solve_rust()` → NVRTC カーネル → 戦略+EV を JSON 返却
2. **バッチ事前計算**: `batch.py` が 1755 フロップ × 3 ポジション = 5265 スポットを 32 件ずつ GPU solve → Parquet 追記 → cache JSON 構築
3. **シミュレーション**: `range_builder` が preflop 表から fold equity と両者の weights[1326] を計算 → GPU でポストフロップ solve

---

## 5. パフォーマンス実績

| 処理 | Rust CPU | Rust GPU hybrid（ライブラリ採用） | Rust GPU fast（Phase C 後） |
|---|---|---|---|
| 1 スポット 300iter（N=32 バッチ） | 53s | 0.18s/spot | **0.080s/spot** |
| showdown kernel | ~200ms | 1.7ms（118x） | 1.7ms |
| GPU 使用率（active-mean） | — | ~40% | **67%（max 77%）** |
| 5,265 スポット全計算 | ~4.7h | **15.8 分** | （未移行） |

Python GPU 実装（CuPy/NVRTC）は Rust GPU に一本化して削除済み。
fast と hybrid は混合戦略が異なる（CFR 均衡の非一意性。根戦略差 max ~0.11）。

---

## 6. データストア

- 正規パス: `~/projects/_data/gto/solutions/`（gitignored、`gto/` 配下には置かない方針）
- 構成: `spots/ agg/ combos/ reports/`（Parquet）+ `cache/{POS}_{stack}.json`（フロント直読）
- **現状: 19,305 distinct スポット**（2026-06-07 に修正済み評価器で全計算）:
  BTN/CO/SB × {50, 100, 200}bb + HJ/UTG × 100bb（各 1,755 フロップ）。
  cache JSON 11 ファイル。旧評価器の Parquet は
  `solutions_legacy_backup_20260607/` に退避済み
- 再生成は 1 バッチ（5,265 spot）あたり GPU 約 16 分。明示的な指示なしに削除しない

---

## 7. 既知の制限

1. **GPU ソルバーは single-street**: フロップで Call → 即 Showdown 扱い。Turn/River を考慮しない（River solve は正しい）。正確な均衡は `gto-hu`（exploitability 付き）、多ストリート近似は `gto-core::multistreet`（CPU）
2. **プリフロップはハードコード表**: 真の preflop CFR 未実装
3. **3bet 以降の preflop tree 未実装**: BB 3bet 時の BTN 応答が無い
4. **gto-hu フル SRP 100bb は要バケッティング**: exact-combo 密 105 GB は CLI が拒否、`--buckets-river 128`（10.49 GB）で可。リバー戦略がバケット共有になる分の損失は exploitability に含まれて報告される
5. **review の逸脱フラグは preflop のみ**: 対応スポットも trainer 表の範囲（RFI / BB_vs_BTN / BB_vs_CO）。それ以外は `missing_data`

---

## 8. 進捗とロードマップ

| Phase | 内容 | 状態 |
|---|---|---|
| 0 | モノレポ基盤（Rust workspace / FastAPI / Next.js） | ✅ 完了 |
| 1 | コア計算（評価器・エクイティ・pyo3・/api/equity） | ✅ 完了 |
| 2 | プリフロップトレーナー（頻度表・クイズ・Neon UI） | ✅ 完了 |
| 3 | ポストフロップ DCFR（CPU + GPU、ベンチ済み） | ✅ 完了 |
| A | ソリューションライブラリ（正規化・Parquet・バッチ・UI） | ✅ 完了 |
| B | Neon UI 全機能統合（/report /solver /review 含む） | ✅ 完了（2026-06-07 ハンド履歴レビュー実装） |
| C | GPU 最適化（ホットパス alloc/HtoD 排除、util 39→67%） | ✅ 完了（80%+ は今後） |
| D | スタック/ポジション拡張（50/200bb・HJ/UTG → 19,305 スポット） | ✅ 完了 |
| HU | 抽象均衡ソルバー（river → turn+river → flop → preflop → M-flop blueprint） | ✅ Phase 6 v0 完了（M 拡大は将来） |
| E | 商用化（Supabase 認証・Stripe・Cloud Run・独自ドメイン） | ⬜ 未着手 |

---

## 9. 起動・開発コマンド

```bash
# 依存インストール（ワークスペースルートで一括）
cd ~/projects && make install

# Rust 拡張ビルド（Rust 変更時のみ）
cd ~/projects/gto && source ~/.cargo/env
uv run --no-sync maturin develop --manifest-path crates/gto-py/Cargo.toml   --release
uv run --no-sync maturin develop --manifest-path crates/gto-cuda/Cargo.toml --release

# バックエンド :8000 / フロントエンド :3000
uv run --no-sync uvicorn gto.api.main:app --host 0.0.0.0 --port 8000
cd web && pnpm exec next dev

# テスト
uv run --no-sync pytest gto/tests
cargo test --manifest-path gto/Cargo.toml
```

---

## 10. 関連ドキュメント

- [README.md](./README.md) — 概要・クイックスタート
- [ARCHITECTURE.md](./ARCHITECTURE.md) — 構成図・データフロー・設計判断
- [PROGRESS.md](./PROGRESS.md) — 進捗・TODO（※バッチ進捗 24% の記載は古い。実際は完了済み）
- [CLAUDE.md](./CLAUDE.md) — 開発規約・Gotchas
