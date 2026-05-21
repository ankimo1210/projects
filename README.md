# projects workspace

個人開発のマルチプロジェクト・ワークスペース。各サブディレクトリが独立したプロジェクトで、トップレベルで一括して git 管理しています。

## プロジェクト一覧

| ディレクトリ | 概要 | スタック |
|---|---|---|
| [`land_price_api_app/`](land_price_api_app/) | 国土交通省「不動産情報ライブラリ」API を使った地価公示・取引価格データのローカル取得・分析・可視化アプリ | Python / FastAPI / DuckDB |
| [`re_invest_os/`](re_invest_os/) | 不動産買付前のDD・監査を支援する AI 駆動 Web アプリ（個人投資家向け） | Next.js / FastAPI / Supabase |
| [`gto/`](gto/) | テキサスホールデムの GTO 分析・ソリューション参照・GPU 計算を統合した Web アプリ | Rust / FastAPI / Next.js |
| [`stock/`](stock/) | 日本株・米株の価格・財務・マクロを取得し Jupyter / Dash で分析する `stockkit` ツールキット | Python / DuckDB / Dash |
| [`market-viz/`](market-viz/) | 個人用マーケット可視化・分析アプリ | Streamlit / Plotly / DuckDB |
| [`nbody-gpu/`](nbody-gpu/) | GPU 加速 N 体シミュレーション + リアルタイム 3D 可視化 | CuPy / VisPy |
| [`line_backup/`](line_backup/) | iPhone ローカルバックアップから LINE データを完全オフラインで解析する CLI | Python |
| [`johnhull/`](johnhull/) | John Hull 教材ベースの金利モデル研究ノート | Python / Jupyter |
| [`rates_volatility_model/`](rates_volatility_model/) | 金利ボラティリティ・モデリングのリサーチノート | Python / Jupyter |
| [`notebooks/`](notebooks/) | 単発の分析ノートブック置き場（債券、ETF、不動産シミュ等） | Jupyter |

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

- Windows 11 + WSL2 (Ubuntu)
- Python は各プロジェクトで `uv` / `venv` を個別管理
- AI コラボ前提（Claude Code / Copilot）。エージェント向け規約は `CLAUDE.md` と `AGENTS.md` を参照

## このリポジトリで作業するときは

1. まず該当プロジェクトの `README.md` を読む（あれば `CLAUDE.md` / `AGENTS.md` も）
2. 横断的なチェックは `Makefile` 経由で行う
3. リポジトリ全体を grep しない（`CLAUDE.md` の Workspace Policy 参照）
