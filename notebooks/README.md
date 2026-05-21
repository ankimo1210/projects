# notebooks

単発の分析・実験ノートブック置き場。明確なプロダクト境界を持たないアドホックな分析がここに入ります。

製品レベルに育ったものは個別プロジェクト（例: `re_invest_os/`, `stock/`, `gto/`）に昇格させます。

## 構成

| サブディレクトリ | 用途 |
|---|---|
| `finance/` | 債券・ETF・コンベキシティなど金融分析の単発ノート |
| `real_estate/` | 不動産データ収集・投資シミュレーション。製品化したものは `re_invest_os/` / `land_price_api_app/` を参照 |
| `scrapers/` | 価格スクレイパーと取得 CSV |
| `vector_analogy/` | ベクトル類似度の可視化実験（自己完結ミニプロジェクト） |
| `launch_streamlit_from_notebook.ipynb` | ノートブックから Streamlit を起動するパターンメモ |

## 過去世代のノート

旧世代の不動産投資シミュ（`real_estate_investment_sim_0..2`, `_simulator`, `_gen_re_sim*.py` 生成スクリプト）と、ここで試作されていた `real_estate_app/` Streamlit ミニアプリは `_archive/notebooks/old_real_estate_sim/` に退避済み。

## 派生データ

旧 `notebooks/output/` は `_data/notebooks/output/` に移動（gitignore 対象）。新たに派生データを保存するノートも `_data/notebooks/` 配下を使ってください。

## 注意

- `.ipynb` を直接編集するより、対応する生成スクリプトがあればそちらを編集して再生成するのが望ましい
- 大きな出力（CSV / Parquet / DuckDB）はノート横ではなく `_data/notebooks/` か該当プロジェクトの `_data/<project>/` へ
