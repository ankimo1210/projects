# 市場研究ノート（合成デモ）

5本は番号順に読む構成ですが、それぞれ単独で最初から再実行できます。
共通サービスと研究APIを使い、実データの取得、口座ファイルの読取、外部通信は行いません。
結果は架空データの動作例であり、実市場の成績や過去のPIT保存を示しません。

| ノート | 内容 | 使用する共通API |
|---|---|---|
| [01_data.ipynb](01_data.ipynb) | 合成価格の来歴・時刻・品質 | build_demo_run |
| [02_signals.ipynb](02_signals.ipynb) | 観測時刻付きsnapshotからのPIT信号 | ResearchStore、build_pit_signal_table |
| [03_compare.ipynb](03_compare.ipynb) | zero / mean / ridge / tree / buy-and-holdの同費用比較 | build_pit_signal_table、compare_model_strategies |
| [04_risk.ipynb](04_risk.ipynb) | retrospective仮想配分のリスク寄与 | virtual_risk_report |
| [05_html.ipynb](05_html.ipynb) | 同一合成runの自己完結HTML | render_demo_report |

## 実行条件

WSL Ubuntu側のリポジトリルートでmarket-researchを同期し、Jupyter互換のPython環境で
ノートを開いてください。market-research本体にはノート実行基盤を追加していません。
Jupyterのセル実行にはノート実行環境が必要です。ノートの計算コードは
market-research本体の既存依存だけで動作するようにしてあります。

~~~bash
uv sync --package market-research --group dev
~~~

01〜04の図は既存依存のPlotlyを用います。02と03が作るDuckDB snapshotは
一時ディレクトリに置き、セル終了後に削除します。05のHTMLはWSLの一時領域に保存します。
いずれもGit管理下へデータを作りません。コミット時はセル出力を消しておきます。

## 読み方と境界

- 時刻はUTC、価格はUSDのraw終値です。足終端から1時間後が判断時刻です。
- 02と03では各判断時点の1本だけを観測時刻付きsnapshotにして保存し、
  lockbox開始前のsnapshot IDだけを信号APIに渡します。未来ラベルは評価専用です。
- 03では目標ウェイトをバックテストが1期遅らせ、手数料3bpsと
  スリッページ2bpsを全戦略に同じ条件で適用します。zeroはcashの比較基準です。
- 04は現在の仮想構成を過去の窓へ当てるretrospectiveリスク計算です。
  02・03のPIT検証や実口座のリスクとは意味が異なります。
- 05のHTMLはbuild_demo_runの2銘柄戦略を描画します。03の単一銘柄OOS比較と
  数値を直接比較しないでください。

実データの取得手順は[データ取得ガイド](../docs/DATA.md)、契約と制約は
[設計仕様](../../docs/superpowers/specs/2026-09-27-market-research-design.md)を参照してください。
