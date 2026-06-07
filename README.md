# projects workspace

個人開発のマルチプロジェクト・ワークスペース。各サブディレクトリが独立したプロジェクトで、トップレベルで一括して git 管理しています。

## プロジェクト一覧

| ディレクトリ | 概要 | スタック |
|---|---|---|
| [`land_price_api_app/`](land_price_api_app/) | 国土交通省「不動産情報ライブラリ」API を使った地価公示・取引価格データのローカル取得・分析・可視化アプリ | Python / FastAPI / DuckDB |
| [`gto/`](gto/) | テキサスホールデムの GTO 分析・ソリューション参照・GPU 計算を統合した Web アプリ | Rust / FastAPI / Next.js |
| [`stock/`](stock/) | 日本株・米株の価格・財務・マクロを取得し Jupyter / Dash で分析する `stockkit` ツールキット | Python / DuckDB / Dash |
| [`market-viz/`](market-viz/) | 個人用マーケット可視化・分析アプリ | Streamlit / Plotly / DuckDB |
| [`nbody-gpu/`](nbody-gpu/) | GPU 加速 N 体シミュレーション + リアルタイム 3D 可視化 | CuPy / VisPy |
| [`line_backup/`](line_backup/) | iPhone ローカルバックアップから LINE データを完全オフラインで解析する CLI | Python |
| [`akinator/`](akinator/) | Wikidata をエンティティ源とするローカル・アキネーター風推測ゲーム（確率的候補更新エンジン） | Python / FastAPI |
| [`johnhull/`](johnhull/) | Hull『Options, Futures, and Other Derivatives』11e の章別学習ボリューム + `hullkit` 共有パッケージ | Python / Jupyter |
| [`rates_volatility_model/`](rates_volatility_model/) | 金利ボラティリティ・モデリングのリサーチノート | Python / Jupyter |
| [`aisan_lbo_case/`](aisan_lbo_case/) | アイサンテクノロジー (4667.T) 非公開化 LBO ケーススタディ（公開情報ベース、HTML レポート出力） | Python / Jupyter |
| [`notebooks/`](notebooks/) | 単発の分析ノートブック置き場（債券、ETF、不動産シミュ等） | Jupyter |
| [`csharp_calc/`](csharp_calc/) | WinForms 四則演算電卓サンプル（エンジンは UI 非依存・ユニットテスト付き） | C# / .NET 9 |

> `re_invest_os`（不動産買付前 DD Web アプリ）は独立リポジトリへ移管済み:
> ローカル `~/re_invest_os` / GitHub `ankimo1210/re_invest_os`

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
- Python は **ルート単一の uv workspace** で管理（`.venv` は repo root に1個）
  - workspace メンバー: `gto`, `market-viz`, `stock`, `nbody-gpu`, `line_backup`, `land_price_api_app`, `akinator`, `johnhull/hullkit`
  - 例外: `aisan_lbo_case` は `requirements.txt`、`csharp_calc` は .NET、`rates_volatility_model` / `notebooks` は env 管理なし
- AI コラボ前提（Claude Code / Copilot）。エージェント向け規約は `CLAUDE.md` と `AGENTS.md` を参照

## セットアップ

```bash
uv sync --all-packages   # ルートに .venv が作られ、全メンバーが editable install
make help                # 横断ターゲット一覧
```

ワークスペース内のクロスインポートはそのまま動きます。例: `johnhull` のノートブックから `from hullkit import ...` が可能（`hullkit` パッケージは `johnhull/hullkit` 由来、workspace で自動リンク）。

## このリポジトリで作業するときは

1. まず該当プロジェクトの `README.md` を読む（あれば `CLAUDE.md` / `AGENTS.md` も）
2. 横断的なチェックは `Makefile` 経由で行う
3. リポジトリ全体を grep しない（`CLAUDE.md` の Workspace Policy 参照）
