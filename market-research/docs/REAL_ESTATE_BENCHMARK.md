# 不動産市場の国際比較・地価調査

更新日: 2026-09-30。福岡・東京の地価と、香港、英国、豪州、ベルリン、シンガポールの公的系列を比較する探索用資料。住宅価格指数、土地価格、募集・契約賃料を別の指標として扱い、NOI利回りや一棟の期待収益率として混用しない。

## 配置

| 内容 | リポジトリ内の場所 |
|---|---|
| 収集・集計スクリプト | `market-research/scripts/analysis/` の `global_city_*`、`fukuoka_land_price_history.py`、`fukuoka_continuing_sites.py`、`tokyo_land_vs_sp500_2006_2026.py` |
| テスト | `market-research/scripts/analysis/tests/`（ルートの `testpaths` に登録済みで、`make test` でも回る） |
| 固定レポートと検証ノート | `market-research/docs/data/validation/` |
| 計画（移管前の記録） | ルートの `docs/superpowers/plans/2026-09-28-global-city-*.md` |
| 原本と加工データ | `_data/market-research/market/{raw,processed}/`（Git無視、同じリポジトリの内部） |
| 福岡の国土数値情報ZIPの記録 | `_data/market-research/market/raw/land_price_history_fukuoka/manifest.json` |
| HTMLの共通スタイル | `docs/templates/claude-report/tokens.css` |

元の `re_invest_os` 作業ツリーから、調査コード・レポートをこのリポジトリへ移し、原本・加工データをリポジトリ内へ複製した。既存の検証ノートにある `re_invest_os` の絶対パスや実行例は取得当時の記録であり、現在は上の配置を使う。

## オフライン再計算

以下は `/home/kazumasa/projects/market-research` から実行する。Python環境は親の単一uvワークスペースの `.venv` を使い、分析スクリプトが使う `requests` と `matplotlib` はプロジェクトの直接依存として宣言している。通信は `--download` を付けた収集時だけ行う。

```bash
../.venv/bin/python scripts/analysis/fukuoka_land_price_history.py
../.venv/bin/python scripts/analysis/fukuoka_continuing_sites.py --check
../.venv/bin/python scripts/analysis/global_city_berlin_history.py
../.venv/bin/python scripts/analysis/global_city_singapore_indices.py
../.venv/bin/python scripts/analysis/global_city_nsw_history.py
../.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T060018Z
../.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T085744Z
```

- 福岡の集計は、最初にZIP 44本を `manifest.json` と照合する。
- `fukuoka_continuing_sites.py --check` は、継続159地点の表と関連する数値を検証ノートの本文と照合する。
- 国際比較の2 runは、各runの原本に加えて福岡のZIPも照合して読む。run時点の福岡CSVには前年地点コードの列がないため。
- 固定HTML 2本は、各runの `report.html` を `docs/data/validation/` に写したもの。
  - `global_city_pilot_2026-09-28.html` は run `20260928T060018Z`。
  - `global_city_pilot_rents_2026-09-28.html` は run `20260928T085744Z`。

テストはリポジトリルートから次で実行する。

```bash
uv run --no-sync pytest market-research/tests market-research/scripts/analysis/tests -q
```

### 再計算の照合結果

**2026-09-29：** 保存原本から再計算し、次のSHA-256が移管前と一致した。
- 福岡CSV
- ベルリン年次CSV
- シンガポール指数CSV
- NSW月次CSV

**2026-09-30：** [移管レビュー](data/validation/real_estate_benchmark_migration_review_2026-09-29.md)への対応で、次の出力は意図して変わった。
- 福岡CSV：前年地点コードと選定状況の2列を追加。
- 福岡の図用JSON：連鎖指数を追加。
- 国際比較2 runの `summary.json`・`report.html` と、固定HTML 2本。変更点は次の3つ。
  - 福岡の連鎖指数を前年地点コードで作り直した。
  - 原典の表示から絶対パスを除いた。
  - ONSの帰属表示を加えた。

次は変わっていない。
- 2 runの `observations.csv`・`coverage.csv`
- ベルリン・シンガポール・NSWの出力

## 再取得できる系列とできない系列

原本はGitに含めない。別の環境で作り直すときは、下の表で取得経路と記録の有無を確かめる。

| 系列 | 取得コード | 原本の記録 | 別環境での再取得 |
|---|---|---|---|
| 福岡の地価公示（国土数値情報L01、福岡県ZIP 1983–2026年） | `fukuoka_land_price_history.py --download` | `land_price_history_fukuoka/manifest.json`：ファイル名、URL、サイズ、SHA-256 | **できる。** 欠けたZIPだけを取得し、記録済みのハッシュと照合する。国交省が同じURLのファイルを差し替えていれば、不一致で止まる。 |
| 香港RVD、UK HPI、ONS PIPR、NSWの月次ファイル（国際比較run） | `global_city_pilot.py --download [--uk --ons --nsw] --run-id <新しいID>` | 各runの `manifest.json`：URL、SHA-256、取得時刻 | **新しいrunとしてできる。** 当時と同じバイト列は保証されない。香港のCSVは同じURLのまま更新される。英国とNSWは公表版ごとのURLで、記録したハッシュと照合できる。 |
| NSWの月次履歴、ベルリン、シンガポール | 各スクリプトの `--download` | 各runの `manifest.json`：URL、SHA-256、サイズ | **できる。** 保存済みの原本は、各スクリプトが `manifest.json` のハッシュと照合して読む。取り直した原本も同じハッシュと比べれば、公開元による差し替えの有無がわかる。 |
| 東京23区の地価（`processed/land_prices_y{year}_pref13_pc0.parquet`） | このリポジトリにはない | 加工済みParquetの複製だけ。取得時の応答やmanifestはない | **できない。** 物件DD側の非公開パイプラインが、APIキーを使って不動産情報ライブラリAPIから取得・加工したもの。 |
| S&P 500（東京対S&P） | スクリプトがYahooの非公式APIを直接呼ぶ | 応答原本なし（年次CSVだけ） | **同じ値を再現できない。** |

## 主な入口

- [国際比較HTML](data/validation/global_city_pilot_rents_2026-09-28.html)：福岡の地価、香港の価格・賃料指数、英国の価格・賃料、NSWの一部賃料。
- [NSW月次HTML](data/validation/global_city_nsw_history_2026-09-28.html)：賃貸ボンド登録からの新規契約賃料。
- [ベルリン25年](data/validation/global_city_berlin_annual_2026-09-29.md)：同一ゾーン比較と断面中央値を分ける。
- [シンガポール](data/validation/global_city_singapore_indices_2026-09-29.md)：住宅価格・賃料指数。同一物件の実現利回りではない。
- [福岡地価1983–2026](data/validation/fukuoka_land_price_history_1983_2026.md)：断面平均と、前年地点コードでつないだ連鎖指数（1983年=100で2026年189.3）を分ける。

## 東京対S&P 500

[比較ノート](data/validation/tokyo_land_vs_sp500_2006_2026.md)は、20年間の価格指数の比較であり、総収益ではない。表の年率は、価格指数の年率変化で、配当を含まない。

- **再生成して一致するとは主張しない。** S&P 500の取得元はYahooの非公式APIで、当時の応答原本も保存されていない。
- **PNGは2026-09-28の生成物のまま。** ラベルの修正はスクリプトにだけ反映した。
- **比較結論の再利用は保留する。** 公式系列と原本の保存を整えるまで。

## 次に必要な検証

海外・日本の一棟投資収益を比べるには、次の定義を揃える。
- 対象資産
- 成約価格
- 実効賃料
- 空室
- 運営費
- 修繕費
- NOI

現在の公的価格指数から、Cap RateやIRRを直接出さない。東京対S&P 500は、上記の取得元と原本の問題を先に解く。公開前の利用条件と帰属文言の確認は、[STATUS](STATUS.md)の不動産節で管理する。
