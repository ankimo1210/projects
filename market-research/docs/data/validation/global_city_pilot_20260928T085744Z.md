# 国際不動産データ先行調査：家賃データ試験（段階C）

> 移管注記（2026-09-29）：現行の実行パスと原本配置は[移管ガイド](../../REAL_ESTATE_BENCHMARK.md)を参照。本文中の旧アプリのパスは取得当時の記録。

日付: 2026-09-28。run: `20260928T085744Z`。段階A/Bは[前回の検証](global_city_pilot_20260928T060018Z.md)を参照。本資料は段階Cで追加したONSとNSWの取得・定義・計算を記録する。

## 成果物と再生成

- 原本とSHA-256: `data/market/raw/global_city_pilot/20260928T085744Z/manifest.json`。福岡・香港2本・UK HPI・ONS PIPR・NSWの計6本を別runに保存。ONS XLSXは18,640,156 byte、NSW XLSXは737,307 byte。
- 集計: `data/market/processed/global_city_pilot/20260928T085744Z/{observations.csv,coverage.csv,summary.json,report.html}`。
- 閲覧用HTML: [global_city_pilot_rents_2026-09-28.html](global_city_pilot_rents_2026-09-28.html)。CSS・SVGを内包し、外部通信なしで開ける。Windows側は `\\wsl.localhost\Ubuntu\home\kazumasa\re_invest_os_worktrees\fukuoka-rent-price\docs\data\validation\global_city_pilot_rents_2026-09-28.html`。
- 保存原本からの再生成: worktreeのルートで `.venv/bin/python scripts/analysis/global_city_pilot.py --run-id 20260928T085744Z`。新しいrunで公式URLから取得する場合は `--download --uk --ons --nsw` を付け、一意のrun IDを指定する。XLSXは標準ライブラリでストリーム読取し、本番依存は増やしていない。

## 英国：ONS PIPR

[ONSの配布ページ](https://www.ons.gov.uk/economy/inflationandpriceindices/datasets/priceindexofprivaterentsukmonthlypricestatistics)の2026年9月16日版。原本 `Table 1` の地域コード `E12000007`（London region）と `E08000003`（Manchester local authority）を固定して読む。原本49,980データ行から対象2地域の各140か月、計280か月観測を抽出。月次の非季節調整指数は2023年1月=100、月額家賃は英ポンド・月。既存契約と新規契約を含む民間賃貸住宅の平均値である。[ONS方法論](https://www.ons.gov.uk/economy/inflationandpriceindices/methodologies/priceindexofprivaterentsdetailedmethodology)も参照。

原本の直接照合（地域、2015-01指数/家賃、2023-01指数/家賃、2026-08指数/家賃）:

| 地域 | 2015-01 | 2023-01 | 2026-08 |
|---|---:|---:|---:|
| London region | 86.294082 / £1,580 | 100 / £1,830 | 127.395646 / £2,332 |
| Manchester local authority | 74.352197 / £780 | 100 / £1,049 | 130.879931 / £1,373 |

同一四半期の3か月指数を単純平均し、UK HPIの四半期平均とそれぞれ2015Q1=100に換算。双方がある四半期のみ `100 × (価格指数/価格基準値) ÷ (賃料指数/賃料基準値)` を計算する。2026Q3は家賃が7・8月、HPIは7月しかないため除外。両地域とも比較可能な46四半期（2015Q1〜2026Q2）。2026Q2のリベース値は London 価格127.28・家賃144.91・相対87.83、Manchester 価格192.82・家賃173.00・相対111.46。**相対指数は利回りではない。** 売買と賃貸で物件母集団が異なり、一棟NOIはない。地域の粒度もロンドン広域とマンチェスター市で異なる。

## NSW：Rental Bond Lodgements

[NSW公式配布ページ](https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data)の2026年8月ファイル。新しい賃貸借の開始時に登録されたボンド情報であり、全入居者の現行賃料や募集賃料ではない。原本27,604行、正の数値家賃27,333行、不明 `U` 256行、0円15行。住宅種類コードが定義外の6行は別に数えた。個別物件IDがないため同じ属性の行を重複と断定しない。

住宅種類 `F`（flat/unit）、寝室 `1` または `2`、週額家賃が正の行に絞った中央値:

| 範囲 | 登録件数 | 中央値 | 単位 |
|---|---:|---:|---|
| NSW州全体 | 10,931 | 750 | AUD/週 |
| postcode 2000 | 362 | 1,150 | AUD/週 |

postcode 2000はシドニー都市圏の境界ではない。都市圏系列の作成には公式の地域境界・postcode対応と複数月の取得が必要。寝室0はスタジオだけでなく駐車区画等を含み得るため今回の比較から外した。`O`/`U`の住宅種類や未知の家賃も中央値に入れない。単月の二つの集計値を価格指数や想定利回りへ接続しない。

[NSWの利用条件](https://www.nsw.gov.au/nsw-government/about-website/copyright)に基づく出典表示: © State of New South Wales. For current information go to www.nsw.gov.au. ONS/UK HPIは[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)に従う。元ファイルの利用条件が変わる可能性は、再配布・公開前に確認する。

## 検証と次段階

実行結果（2026-09-28）:

| 検証 | 結果 |
|---|---|
| `PYTHONPATH=scripts/analysis .venv/bin/python -m pytest scripts/analysis/tests/test_global_city_pilot.py scripts/analysis/tests/test_global_city_rents.py -q` | **19件通過**。XLSX列・地域コード・重複・不完全四半期・家賃不明/0円・対象外種類と原本保存を含む |
| `ruff check` / `ruff format --check`（対象4ファイル） | **問題なし** |
| 保存原本から `--download` なしで段階Cを再生成 | `observations.csv`・`coverage.csv`・`summary.json`・`report.html` のSHA-256が再実行前後で一致 |
| 段階Bの既存runを現行コードで再生成 | 同じ4ファイルのSHA-256が一致。保存済み段階B HTMLスナップショットとも一致 |
| Chromeで自己完結HTMLを描画 | Windows側のUNCファイルURLからPC幅1440px・狭幅390pxのスクリーンショットを目視確認。グラフ、表、日本語、出典を表示 |

次はGreater Sydneyの境界に対応したpostcode集合を定義してからNSWの月次履歴へ進む。UK PIPRとHPIは指数の相対推移までとし、一棟投資利回りには用いない。
