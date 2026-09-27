# projects workspace

個人開発のマルチプロジェクト・ワークスペース。各サブディレクトリが独立したプロジェクトで、トップレベルで一括して git 管理しています。

## プロジェクト一覧

46件の現役プロジェクトを目的別に案内します（2026-09-28確認）。「状態」は各 README と
[整理計画](docs/superpowers/plans/2026-09-27-workspace-cleanup.md) に基づく位置づけで、
今回すべてを実行検証したという意味ではありません。
個人データを扱うものも、ここではツールの目的と公開文書だけを案内します。

### 市場・投資・意思決定（10件）

| プロジェクト | 目的 | 入口 | 状態 | 後継・関連 | スタック |
|---|---|---|---|---|---|
| market-research | 市場データ・時点管理・研究計算の統合先 | [README](market-research/README.md) | 保存データの7画面・分析CLI | quantkit / macrokit / [旧stock](_archive/market/stock/README.md) / [旧market-viz](_archive/market/market-viz/README.md) / [旧autostock](_archive/market/autostock/README.md) | Python / Streamlit / Plotly |
| quantkit | 高度モデル・税・多資産研究を含む独立ライブラリ | [README](quantkit/README.md) | 高度研究を独立継続 | market-research / [旧stock](_archive/market/stock/README.md) | Python / DuckDB / Plotly |
| macrokit | 公表時点を再現するマクロ指標ストア | [README](macrokit/README.md) | PIT蓄積を独立継続 | market-research / [旧stock](_archive/market/stock/README.md) | Python / DuckDB |
| portfolio-analyzer | 資産配分・集中度などを確認するローカル分析 | [README](portfolio-analyzer/README.md) | 独立継続 | market-research の読取adapterを追加 | Python / Portable HTML |
| JHRMBS | JHF MBS の償還・CF・価格リスク分析 | [README](JHRMBS/README.md) | 分析基盤 | 金利研究教材 | Python / Pandas / SciPy |
| aisan_lbo_case | 公開情報に基づく LBO ケーススタディ | [README](aisan_lbo_case/README.md) | 調査成果 | small_ma_search（関連テーマ） | Python / Jupyter |
| labor_ai_quadrant | 人手不足と AI 代替可能性の業種分析 | [README](labor_ai_quadrant/README.md) | 分析レポート | 市場分析基盤（接続候補） | Python / Plotly |
| timesfm_lab | 時系列基盤モデルと古典手法の比較 | [README](timesfm_lab/README.md) | 研究ベンチ | quantkit（関連テーマ） | Python / PyTorch |
| small_ma_search | 小型 M&A の調査・実行計画 | [README](small_ma_search/README.md) | 意思決定資料 | aisan_lbo_case | Markdown / HTML |
| housing-buy-vs-rent | 住宅購入・賃貸・借上社宅の比較 | [README](housing-buy-vs-rent/README.md) | HTML シミュレーター | re_invest_os（別用途の不動産分析） | HTML / JavaScript / Node.js (stdlib) |

### 定量・数学の教材と研究（7件）

| プロジェクト | 目的 | 入口 | 状態 | 後継・関連 | スタック |
|---|---|---|---|---|---|
| johnhull | Hull の章別教材・現代デリバティブ研究・hullkit | [README](johnhull/README.md) | 継続開発 | 金利・ボラ・ヘッジ研究群 | Python / Jupyter |
| rates_volatility_model | 金利ボラモデルの教材と ratesvol | [README](rates_volatility_model/README.md) | 教材・合成データ | johnhull（独立照合を維持） | Python / Jupyter |
| rough_volatility | ラフボラと Hawkes 過程の可視化 | [README](rough_volatility/README.md) | 独立した研究ラボ | johnhull | Python / Jupyter |
| deep_hedge_price | Deep Hedging と別系統のニューラル価格近似 | [README](deep_hedge_price/README.md) | 独立した研究ラボ | johnhull の参照計算 | Python / PyTorch |
| optimal_execution | 最適執行・板モデル・強化学習の比較 | [README](optimal_execution/README.md) | 独立した研究ラボ | johnhull / market_nn | Python / Jupyter |
| market_nn | LOB 予測論文の構造再現 | [README](market_nn/README.md) | 研究・合成データ検証 | optimal_execution（関連テーマ） | Python / PyTorch |
| analytics | 数学・統計・ML の体験型教材群 | [README](analytics/README.md)・[統合ポータル](analytics/report/README.md) | 教材シリーズ | 10冊の Python メンバーと SDE Web 教材 | Python / Jupyter Book / Plotly / TypeScript |

### ゲーム・シミュレーター・体験アプリ（13件）

| プロジェクト | 目的 | 入口 | 状態 | 後継・関連 | スタック |
|---|---|---|---|---|---|
| gto | ポーカーの GTO 分析・計算 | [README](gto/README.md) | Web アプリ | 独立 | Rust / FastAPI / Next.js |
| akinator | 確率更新による人物・キャラクター推測 | [README](akinator/README.md) | オフライン seed 付き試作 | Wikidata 取得機能 | Python / FastAPI |
| pokemon | オリジナル 3D モンスター収集ゲーム | [README](pokemon/README.md) | Web 試作 | 独立 | Vite / React Three Fiber |
| monster_gate | カードと MP を使うローグライク | [README](monster_gate/README.md) | Web ゲーム | 独立 | TypeScript / pnpm / Vite |
| EitanQuest | iPhone 向け英単語クイズ | [README](EitanQuest/README.md) | iOS MVP | Xcode が必要 | Swift / SwiftUI / SwiftData |
| NeonThread | 発光ラインを操作する無限ランゲーム | [README](NeonThread/README.md) | iOS アプリ | Xcode が必要 | Swift / SwiftUI + SpriteKit |
| WSET | CruNote: WSET のオフライン学習 | [README](WSET/README.md) | iOS アプリ | Xcode・独立 uv の問題コーパス | Swift / SwiftUI（問題コーパス生成は Python） |
| My Tianjin | HSK の語彙・語順・読解・産出学習 | [README](My%20Tianjin/README.md) | iOS アプリ | Xcode が必要 | Swift / SwiftUI |
| b737-ops-sim | Boeing 737 の運航手順を学ぶ | [README](b737-ops-sim/README.md) | ローカル訓練用試作 | FlightGear / mock、認定訓練装置ではない | TypeScript / pnpm / React / Babylon.js / Fastify |
| eagle | Apollo AGC と月着陸のシミュレーション | [README](eagle/README.md) | プレイ可能な Alpha | yaAGC / Rust / Web | Rust / TypeScript / yaAGC |
| komorebi-3d | 喫茶店ジオラマの 3D 制作 | [README](komorebi-3d/README.md) | Blender 描画確認・UE 確認待ち | Blender / Unreal Engine | Blender / Unreal Engine / Python |
| tokyo_subway_3d | 地下鉄の標高を再現する 3D ビューア | [README](tokyo_subway_3d/README.md) | 可視化作品 | 独立 | Python / deck.gl / MapLibre |
| nbody-gpu | GPU による N 体計算と 3D 可視化 | [README](nbody-gpu/README.md) | Phase 0–2 実装済み | NVIDIA CUDA が必要 | CuPy / VisPy |

### 個人データ・開発環境・AI 評価（6件）

| プロジェクト | 目的 | 入口 | 状態 | 後継・関連 | スタック |
|---|---|---|---|---|---|
| health | 本人の健康データをローカルで保存・閲覧 | [README](health/README.md) | Python CLI + Next.js ポータル | 独立 | Python / Next.js / TypeScript |
| genequest | 検査結果のローカル保存・検証 | [README](genequest/README.md) | 個人利用 | 独立 | CSV / JSON / Markdown / Python |
| line_backup | バックアップをオフラインで解析する CLI | [README](line_backup/README.md) | ローカル専用 | 独立 | Python |
| agent-profiler | エージェント実行の観測・保存・分析 | [README](agent-profiler/README.md) | TUI / CLI | Codex CLI / Claude Code | Python / Textual |
| agentic-setup | エージェント・端末設定の復元用バックアップ | [README](agentic-setup/README.md) | 稼働設定と差分あり・同期待ち | 共有知識は docs/knowledge | Markdown / Shell / JSON / TOML |
| quant-agent-benchmark | 定量研究・開発エージェントの評価 | [README](quant-agent-benchmark/README.md) | ベンチ・評価結果を保存 | agent-profiler（関連テーマ） | Python |

### 学習ラボ・単発の成果（10件）

完成した小さな作品も成果として見える位置に残します。更新日だけではアーカイブしません。

| プロジェクト | 目的 | 入口 | 状態 | 後継・関連 | スタック |
|---|---|---|---|---|---|
| jp_llm_lab | 日本語小型 LLM の内部・学習過程を学ぶ | [README](jp_llm_lab/README.md) | 教育ラボ | analytics（関連教材） | Python / PyTorch |
| cpp_algo_lab | C++ / CUDA のアルゴリズム実装と計測 | [README](cpp_algo_lab/README.md) | Phase 1–4 の学習成果 | shortest_path | C++20 / CUDA / make / doctest |
| shortest_path | 最短経路探索の実装と可視化 | [README](shortest_path/README.md) | 学習成果 | cpp_algo_lab | Python / Jupyter / HTML |
| csharp_calc | WinForms 電卓 | [README](csharp_calc/README.md) | 学習サンプル | CsharpApp / .NET | C# / .NET 9 |
| CsharpApp | WPF / MVVM の価格ティッカー | [README](CsharpApp/README.md) | 学習サンプル | csharp_calc / .NET | C# / WPF / .NET 9 |
| ts-rosetta | 同じタスクアプリで TS 技術を比較 | [README](ts-rosetta/README.md) | 学習ラボ | 独立 | TypeScript / pnpm |
| kaggle | コンペの分析・実験記録 | [README](kaggle/README.md) | 実験成果 | 独立 | Python |
| notebooks | 単発の金融・不動産分析など | [README](notebooks/README.md) | 探索・試作 | [旧stock](_archive/market/stock/README.md) / gto / re_invest_os | Jupyter |
| interactive-email-demo | メール内で切り替える指標レポート | [README](interactive-email-demo/README.md) | 検証サンプル | AMP for Email | Python (stdlib) / AMP for Email |
| rates-ui-lab | 金利データを題材に UI を比較 | [README](rates-ui-lab/README.md) | 合成データの UI 実験 | 市場分析の UI 候補 | TypeScript / Next.js / React / pnpm |

### 成果物・資料

| 場所 | 役割 | 扱い |
|---|---|---|
| [models/](models/) | 教科書翻訳パイプラインの成果物 | 現行配置を維持。サイズのみを理由に移さない |
| [reports/](reports/) | 共有の分析レポート | 生成物と原本を区別して参照 |
| [papers/](papers/) | 論文・教科書などの参照資料 | 個々のライセンス・再配布条件に従う |

### 共通知識・作業用ディレクトリ

| 場所 | 役割 |
|---|---|
| [docs/knowledge/](docs/knowledge/README.md) | 共有する環境設定・トラブル解決の正本 |
| [docs/decisions/](docs/decisions/) | ワークスペースの判断理由（ADR） |
| [docs/superpowers/](docs/superpowers/) | 計画・仕様。今回の [整理計画](docs/superpowers/plans/2026-09-27-workspace-cleanup.md) |
| [docs/templates/](docs/templates/) | レポート等の共通テンプレート |
| [_scratch/](_scratch/README.md) | 試行・実験の作業場所。4月の比較ノートは退避済み |
| [_docs/](_docs/README.md) | 一時的な作業ログ・引き継ぎ。現在の仕様の正本ではない |
| [_archive/](_archive/README.md) | 退避済みの7群。理由・後継・実行可能性は索引参照 |

### 外部リポジトリ

不動産買付前 DD アプリは [re_invest_os](https://github.com/ankimo1210/re_invest_os)
で開発します。ローカル配置は `~/re_invest_os`（このリポジトリの外）です。
旧地価アプリのデータ取得基盤は同リポジトリの `packages/market-data` へ移管済みです。
履歴は [アーカイブ索引](_archive/README.md)、探索用ノートは [notebooks](notebooks/README.md) を参照してください。

## ディレクトリ構成

```
projects/
├── <各プロジェクト>/        # 上記の独立プロジェクト
├── _docs/                   # 一時的な作業ログ・引き継ぎ（正本ではない）
├── _scratch/                # 使い捨ての試行（gitignore 一部対象）
├── _archive/                # 過去成果物・旧プロンプト・旧 capability_index
├── _data/                   # 重データ（gitignore 対象、`_data/<project>/` 規約）
├── _logs/                   # 実行ログ（gitignore 対象）
├── reports/                 # 共有レポート（自作の分析成果物 PDF 等）
├── papers/                  # 再配布可能なライセンスの論文・教科書 PDF（gitignore の例外）
├── docs/                    # 共通知識（knowledge/）+ ADR（decisions/）+ スキル生成物（superpowers/）
├── Makefile                 # ワークスペース横断の lint / test / install / clean
├── .pre-commit-config.yaml  # 共通フック (ruff, large file check, ...)
├── AGENTS.md                # AI エージェント向けワークスペース規約（正）
├── CLAUDE.md                # Claude Code 向け: AGENTS.md へのポインタ + 補足
└── .github/copilot-instructions.md
```

## ワークスペース横断コマンド

ルートで実行できる `Makefile` ターゲット:

```bash
make help      # ターゲット一覧
make install   # uv 管理プロジェクトを一括 sync
make lint      # ruff check を全体に
make fmt       # ruff format --check を全体に
make test      # testpaths の33件を pytest で実行 + npm があれば sde-check
make clean     # __pycache__ / .pytest_cache などを掃除
make tree      # ヘビーディレクトリを除外したツリー表示
```

`make test` の Python 対象は [pyproject.toml](pyproject.toml) の `testpaths` に登録した
33ディレクトリです（2026-09-28 確認）。全プロジェクトを検証するものではありません。
`johnhull/report/tests` は登録済み、`deep_hedge_price/tests` は未登録です。
対象プロジェクトのテストを個別に実行してください。`npm` がなければ `sde-check` は省略されます。

## 環境前提

- 対応プラットフォーム: **WSL2 (Ubuntu) を主**とし、ネイティブ Windows (PowerShell) と macOS でも動作（差分は下記セットアップ参照）
- Python は **ルート単一の uv workspace** で管理（`.venv` は repo root に1個）
  - workspace メンバー（正は root `pyproject.toml` の `[tool.uv.workspace]`）: `agent-profiler`, `JHRMBS`, `gto`, `market-research`, `nbody-gpu`, `line_backup`, `akinator`, `health`, `quantkit`, `deep_hedge_price`, `optimal_execution`, `rough_volatility`, `rates_volatility_model`, `jp_llm_lab`, `labor_ai_quadrant`, `macrokit`, `timesfm_lab`, `market_nn`, `portfolio-analyzer`, `johnhull/hullkit`、`analytics/{linear_algebra,neural_net,bayesian,fourier,laplace,machine_learning,statistics,quant_research}` と `analytics/differential_equation/{ode-book,pde-book}`（`analytics/report` のみメンバー外）
  - 例外: `aisan_lbo_case` は `requirements.txt`、`csharp_calc` / `CsharpApp` は .NET、`EitanQuest` / `NeonThread` / `WSET` / `My Tianjin` は Xcode (Swift)、`ts-rosetta` / `b737-ops-sim` / `monster_gate` は pnpm、`pokemon` は npm、`eagle` は Rust (cargo) + npm、`notebooks` / `models` / `kaggle` は env 管理なし、`shortest_path` / `interactive-email-demo` は依存なし（前者は `PYTHONPATH=shortest_path/src` で実行）
  - `WSET/wset_l3_question_corpus` は**ワークスペース外の独立 uv プロジェクト**（自前の `pyproject.toml` / `uv.lock`）。root の `uv sync --all-packages` では依存が入らないので、そのディレクトリで個別に sync する（詳細は同 README）
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
| Node.js 20+ | `gto/web`（Next.js）, `pokemon`（Vite）, `b737-ops-sim` / `ts-rosetta` / `monster_gate`（pnpm）, `eagle/client`（Vite） | WSL/Linux: nvm or apt ／ macOS: `brew install node` ／ Windows: `winget install OpenJS.NodeJS` |
| Rust (cargo) | `gto`（Rust エンジン、maturin でビルド）, `eagle/runtime`（yaAGC ブリッジ） | 全環境 `rustup`（<https://rustup.rs>） |
| .NET 9 SDK | `csharp_calc`, `CsharpApp` | macOS: `brew install dotnet` ／ Windows: `winget install Microsoft.DotNet.SDK.9` ／ WSL: 公式 apt リポジトリ |
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
3. リポジトリ全体を grep しない（`AGENTS.md` の Workspace Policy 参照）
