# GTO Poker Suite

GTO (Game Theory Optimal) ポーカー分析アプリ。テキサスホールデムのプリフロップ判定・フロップソリューション参照・ライブGPU計算・全レンジシミュレーションを統合した Web アプリ。

将来商用化（GTOWizard 同等機能）を見据えた個人開発プロジェクト。

---

## ✨ 機能

| ページ | URL | 内容 |
|---|---|---|
| **TRAINER** | `/neon` | プリフロップクイズ。出題 → 回答 → GTO頻度との差分表示 |
| **LIBRARY** | `/library` | 事前計算済みフロップソリューション参照（1755テクスチャ × 3ポジション） |
| **REPORT** | `/report` | 1755フロップのヒートマップ（dominant action / check%） |
| **SOLVER** | `/solver` | カスタムスポット → ライブ GPU CFR 計算（~3秒/300iter） |
| **SIMULATE** | `/simulation` | プリフロップ fold equity + BBディフェンスレンジ + ポストフロップ |

---

## 🛠 スタック

```
[Frontend]  Next.js 16 + React 19 + TypeScript + Tailwind v4
            └─ Neon/Cyberpunk テーマ統一

[Backend]   FastAPI + Pydantic + DuckDB

[Solver]    Rust workspace
            ├─ gto-core   CFR/DCFR コア・ハンド評価器・マルチストリート (CPU)
            ├─ gto-cuda   GPU加速ソルバー (NVRTC JIT, RTX 5080 sm_120)
            ├─ gto-py     pyo3 バインディング
            └─ gto-hu    HU NLHE abstract equilibrium solver (CPU, exact BR)

[Data]      Parquet（spots / agg / combos / reports / cache）
```

**性能実績** (1スポット 300iter):
- Rust CPU: 53秒
- Rust GPU: 14.4秒 (118倍 showdown kernel)

---

## 🚀 クイックスタート

### 前提

- Linux / WSL2 (Ubuntu 22+)
- CUDA Driver 12.6+ (sm_120 = Blackwell, RTX 5080 で動作確認)
- Python 3.12+
- Rust (rustup 経由)
- pnpm
- [uv](https://docs.astral.sh/uv/)

### セットアップ

このプロジェクトはワークスペース（`~/projects/`）の uv メンバーです。Python 依存はワークスペースルートで一括管理。

```bash
# ワークスペースルートで Python 依存をインストール
cd ~/projects && make install      # = uv sync --all-packages

# Rust 拡張ビルド (初回 + Rust 変更時。gto/ ディレクトリで実行)
cd ~/projects/gto
source ~/.cargo/env
uv run maturin develop --manifest-path crates/gto-py/Cargo.toml --release
uv run maturin develop --manifest-path crates/gto-cuda/Cargo.toml --release

# フロントエンド
cd web && pnpm install
```

### 起動

```bash
# バックエンド (port 8000)
uv run uvicorn gto.api.main:app --host 0.0.0.0 --port 8000

# フロントエンド (port 3000)
cd web && pnpm exec next dev
```

ブラウザで http://localhost:3000 を開く。API docs は http://localhost:8000/docs。

### バッチ計算（事前に1度だけ）

LIBRARY/REPORT を使うには全フロップを事前計算する必要があります（~24分、Rust GPU）。

```bash
nohup uv run python -m gto.library.batch \
  --positions BTN,CO,SB --stacks 100 --iters 300 --batch-size 32 \
  > /tmp/batch.log 2>&1 &
tail -f /tmp/batch.log
```

---

## 📐 ディレクトリ

```
gto/
├── crates/                  Rust workspace
│   ├── gto-core/            CFR/DCFR コア (CPU)
│   ├── gto-cuda/            GPU ソルバー (NVRTC JIT)
│   └── gto-py/              pyo3 バインディング
├── src/gto/
│   ├── api/                 FastAPI ルーター (equity/trainer/solver/library/simulation)
│   ├── trainer/             プリフロップ出題エンジン + GTO頻度テーブル
│   └── library/             バッチ計算 + Parquet ストア + レンジビルダー
├── web/
│   ├── app/                 Next.js ページ (neon/library/report/solver/simulation)
│   ├── components/          共通UI (NeonShell, RangeHeatmap, ...)
│   └── lib/                 API クライアント・ユーティリティ
└── (../_data/gto/solutions/) Parquet 出力先 (gitignored, ワークスペース直下)
```

詳細は [ARCHITECTURE.md](./ARCHITECTURE.md) を参照。

---

## 🧮 GTOソルバーの中身

- **アルゴリズム**: Discounted CFR (Brown & Sandholm 2019) — DCFR α=1.5, β=0
- **ベットサイズ**: 33% / 75% / 100% pot (3種)
- **GPU 実装**: PyTorch 非対応の Blackwell sm_120 のため CUDA Driver API + NVRTC JIT を ctypes で直接実装
- **ハンド評価**: rank-indexed lookup table (5/7-card evaluator)

### ⚠️ 現状の制限（要改善）

1. **single-street solve**: GPU ソルバーはフロップで Call → 即 Showdown。ターン/リバーを考慮しない（リバー solve は正しい）
2. **プリフロップは hardcoded table**: 真の preflop CFR ではなく GTO 近似テーブル
3. **3bet 以降の preflop tree 未実装**: BB 3bet 時の BTN 応答が無い
4. ~~**2c phantom card バグ**~~: 修正済み（`eval::showdown_strengths`）。ただし既存 Parquet ライブラリは旧評価器で計算されたもの — 再生成までフロップ/ターンの数値は要注意

→ 詳細とロードマップは [PROGRESS.md](./PROGRESS.md)

---

## 📖 関連ドキュメント

### このプロジェクト
- [ARCHITECTURE.md](./ARCHITECTURE.md) — システム構成・データフロー・図
- [PROGRESS.md](./PROGRESS.md) — 進捗・TODO・既知の制限
- [DEV.md](./DEV.md) — 開発起動の簡易メモ

### ワークスペース全体
- [`~/projects/README.md`](../README.md) — ワークスペース概要
- [`~/projects/AGENTS.md`](../AGENTS.md) — マルチプロジェクト構成
- [`~/projects/CLAUDE.md`](../CLAUDE.md) — Claude Code 共通ルール
- [`~/projects/Makefile`](../Makefile) — `make install / lint / fmt / test`
- [`~/projects/_docs/`](../_docs/) — レシピ・ワークログ

---

## 📝 ライセンス

未定（個人プロジェクト・将来商用化想定）

---

## 🤖 Built with Claude Code

このプロジェクトは [Claude Code](https://claude.com/claude-code) と協働で開発されています。
