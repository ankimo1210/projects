# projects workspace

個人開発のマルチプロジェクト・ワークスペース。各サブディレクトリが独立したプロジェクトで、トップレベルで一括して git 管理しています。

## プロジェクト一覧

| ディレクトリ | 概要 | スタック |
|---|---|---|
| [`gto/`](gto/) | テキサスホールデムの GTO 分析・ソリューション参照・GPU 計算を統合した Web アプリ | Rust / FastAPI / Next.js |
| [`stock/`](stock/) | 日本株・米株の価格・財務・マクロを取得し Jupyter / Dash で分析する `stockkit` ツールキット | Python / DuckDB / Dash |
| [`market-viz/`](market-viz/) | 個人用マーケット可視化・分析アプリ | Streamlit / Plotly / DuckDB |
| [`nbody-gpu/`](nbody-gpu/) | GPU 加速 N 体シミュレーション + リアルタイム 3D 可視化 | CuPy / VisPy |
| [`line_backup/`](line_backup/) | iPhone ローカルバックアップから LINE データを完全オフラインで解析する CLI | Python |
| [`akinator/`](akinator/) | Wikidata をエンティティ源とするローカル・アキネーター風推測ゲーム（確率的候補更新エンジン） | Python / FastAPI |
| [`pokemon/`](pokemon/) | Quokka Wilds: オリジナル 3D モンスター収集ゲーム | Vite / React Three Fiber |
| [`analytics/`](analytics/) | 体験型インタラクティブ教科書シリーズ（線形代数・NN・ベイズ・フーリエ・ラプラス・微分方程式・機械学習）+ 統合オフラインポータル。索引: [`analytics/README.md`](analytics/README.md) | Python / Jupyter Book / Plotly |
| [`johnhull/`](johnhull/) | Hull『Options, Futures, and Other Derivatives』11e の章別学習ボリューム + `hullkit` 共有パッケージ + Jupyter Book / オフラインポータル | Python / Jupyter |
| [`autostock/`](autostock/) | Mag7 株ストラテジーの自律探索デモ（read-only バックテスト + OOS 評価） | Python |
| [`rates_volatility_model/`](rates_volatility_model/) | 金利ボラティリティ・モデリングのリサーチノート | Python / Jupyter |
| [`aisan_lbo_case/`](aisan_lbo_case/) | アイサンテクノロジー (4667.T) 非公開化 LBO ケーススタディ（公開情報ベース、HTML レポート出力） | Python / Jupyter |
| [`notebooks/`](notebooks/) | 単発の分析ノートブック置き場（債券、ETF、不動産シミュ等） | Jupyter |
| [`csharp_calc/`](csharp_calc/) | WinForms 四則演算電卓サンプル（エンジンは UI 非依存・ユニットテスト付き） | C# / .NET 9 |

> `re_invest_os`（不動産買付前 DD Web アプリ）は独立リポジトリへ移管済み:
> ローカル `~/re_invest_os` / GitHub `ankimo1210/re_invest_os`
>
> `land_price_api_app`（地価公示 Streamlit PoC）は `_archive/land_price_api_app/` へ退避済み
> （market-data エンジンは `~/re_invest_os/packages/market-data` へ移植）。

## ディレクトリ構成

```
projects/
├── <各プロジェクト>/        # 上記の独立プロジェクト
├── _docs/                   # 横断ドキュメント（recipes / ai 系メモ）
├── _scratch/                # 使い捨ての試行（gitignore 一部対象）
├── _archive/                # 過去成果物・旧プロンプト・旧 capability_index
├── _data/                   # 重データ（gitignore 対象、`_data/<project>/` 規約）
├── _logs/                   # 実行ログ（gitignore 対象）
├── reports/                 # 共有レポート（PDF 等）
├── Makefile                 # ワークスペース横断の lint / test / install / clean
├── .pre-commit-config.yaml  # 共通フック (ruff, large file check, ...)
├── CLAUDE.md, AGENTS.md     # AI エージェント向けガイド
└── copilot-instructions.md
```

## ワークスペース横断コマンド

ルートで実行できる `Makefile` ターゲット:

```bash
make help      # ターゲット一覧
make install   # uv 管理プロジェクトを一括 sync
make lint      # ruff check を全体に
make fmt       # ruff format --check を全体に
make test      # pytest -q を全体に
make clean     # __pycache__ / .pytest_cache などを掃除
make tree      # ヘビーディレクトリを除外したツリー表示
```

## 環境前提

- 対応プラットフォーム: **WSL2 (Ubuntu) を主**とし、ネイティブ Windows (PowerShell) と macOS でも動作（差分は下記セットアップ参照）
- Python は **ルート単一の uv workspace** で管理（`.venv` は repo root に1個）
  - workspace メンバー: `gto`, `market-viz`, `stock`, `nbody-gpu`, `line_backup`, `akinator`, `autostock`, `johnhull/hullkit`、`analytics/{linear_algebra,neural_net,bayesian,fourier,laplace,machine_learning}` と `analytics/differential_equation/{ode-book,pde-book}`（`analytics/report` のみメンバー外）
  - 例外: `aisan_lbo_case` は `requirements.txt`、`csharp_calc` は .NET、`rates_volatility_model` / `notebooks` は env 管理なし
- AI コラボ前提（Claude Code / Copilot）。エージェント向け規約は `CLAUDE.md` と `AGENTS.md` を参照

## セットアップ

コアは **Python ≥3.12 を uv の単一ワークスペースで管理**するだけです。Node / Rust / .NET は
それらを使うプロジェクトで作業するときだけ追加で入れます。

### 1. uv を入れる

| 環境 | コマンド |
|---|---|
| WSL2 (Ubuntu) / Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| macOS | `brew install uv`（または上の curl スクリプト） |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"`（または `winget install astral-sh.uv`） |

uv が Python 3.12 自体も自動取得するので、別途 Python を入れる必要はありません。

### 2. Python ワークスペースを sync

```bash
uv sync --all-packages   # ルートに .venv が1個作られ、全メンバーが editable install
make help                # 横断ターゲット一覧
```

ワークスペース内のクロスインポートはそのまま動きます。例: `johnhull` のノートブックから
`from hullkit import ...`（`hullkit` は `johnhull/hullkit` 由来、workspace で自動リンク）。

> **macOS の注意**: torch が CUDA (cu128) インデックスに固定されている（`gto` と
> `analytics/neural_net` が依存）ため、Mac では `--all-packages` が **失敗します**。torch 非依存の
> メンバーだけを sync してください。例:
> `uv sync --package la-book --package bayes-textbook --package ml-textbook`
> （`gto` / `nn-textbook` を Mac で使う場合は CPU/MPS 版 torch への差し替えが別途必要）。

### 3. プロジェクト別ツールチェーン（必要な分だけ）

| ツール | 必要なプロジェクト | 入れ方 |
|---|---|---|
| Node.js 20+ | `gto/web`（Next.js）, `pokemon`（Vite） | WSL/Linux: nvm or apt ／ macOS: `brew install node` ／ Windows: `winget install OpenJS.NodeJS` |
| Rust (cargo) | `gto`（Rust エンジン、maturin でビルド） | 全環境 `rustup`（<https://rustup.rs>） |
| .NET 9 SDK | `csharp_calc` | macOS: `brew install dotnet` ／ Windows: `winget install Microsoft.DotNet.SDK.9` ／ WSL: 公式 apt リポジトリ |
| NVIDIA CUDA | `nbody-gpu`（CuPy）, `gto` の GPU 機能（preview） | NVIDIA GPU + ドライバ必須。**macOS 非対応** |

`gto` は Rust + FastAPI + Next.js で構成が重いので、起動・ビルド手順は `gto/README.md` を参照してください。

### プラットフォーム別の注意

- **WSL2 (Ubuntu)** — 主環境。上記の `make` ターゲットがそのまま使えます。リポジトリは WSL 側の
  Linux パスに置く（`/mnt/c/...` 越しは避ける）と高速・安定です。
- **macOS** — uv / Node / Rust / .NET は問題なし。ただし上記の torch (cu128) 制約と、GPU プロジェクト
  （`nbody-gpu`, `gto-cuda`）は NVIDIA 前提なので動きません。
- **Windows ネイティブ (PowerShell)** — `uv` と Python はそのまま動きますが、`make` と一部 shell
  スクリプトは未対応です。`make test` → `uv run pytest`、`make lint` → `uv run ruff check .` のように
  個別コマンドを直接実行してください。WSL/macOS と同じ手順を踏みたい場合は **WSL2 を推奨**します
  （GPU 利用時も WSL2 のほうが CUDA 統合が安定）。

## このリポジトリで作業するときは

1. まず該当プロジェクトの `README.md` を読む（あれば `CLAUDE.md` / `AGENTS.md` も）
2. 横断的なチェックは `Makefile` 経由で行う
3. リポジトリ全体を grep しない（`CLAUDE.md` の Workspace Policy 参照）
