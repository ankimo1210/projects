# JHRMBS MVP 実装計画

## 1. 調査結果と制約

中核データは JHF が毎月25日（休日の場合は前営業日）に更新する年度別 Excel とする。
各回号シートには発行額・表面利率・発行日、および月次の当初予定 Factor、実績 Factor、
WAC、WAM、任意期限前償還 CPR、WALA、長期延滞とその他解約率が含まれる。

補助系列は次を採用する。

- 財務省「国債金利情報」全期間 CSV（JGB コンスタントマチュリティ）
- フラット35 の現行金利 HTML（21年以上35年以下・融資率9割以下）
- 国土交通省「建築着工統計調査報告」時系列 Excel
- 日本銀行「時系列統計データ検索サイト」コード API

フラット35 の公式な過去系列は PDF グラフのみで、機械可読な代替公式系列を確認できない。
MVP は現行 HTML を月次スナップショットとして将来蓄積し、過去期間のモデルでは JGB 10年との
スプレッドを「借換インセンティブ」ではなく明示的な金利 proxy として使用する。任意の月次
住宅ローン金利 CSV を差し込める境界を設ける。

## 2. データレイヤー

```text
raw/          immutable object store + acquisition manifests
processed/    issue master, issue-month panel, external monthly series
features/     lagged, leakage-controlled modeling table
models/       run metadata, fitted coefficients, OOS metrics
predictions/  issue-level CPR/Factor forecasts
cashflows/    issue/scenario monthly cash flows and risk summaries
reports/      issue-level technical HTML reports and report metadata
```

Raw manifest には取得元 URL、取得日時、元ファイル名、SHA-256、対象期間、データ定義、
HTTP validator、加工履歴を保存する。実体は content-addressed に保存し、同一内容を重複させない。

## 3. 計算定義

- 公開 CPR は年率百分率、SMM は月率小数で内部計算する。
- `SMM = 1 - (1 - CPR)^(1/12)` を使用する。
- 標準 PSJ は JSDA ガイドに従い、WALA 0か月で CPR 0%、60か月で指定終端 CPR に達し、
  以後一定とする。米国 PSA の30か月 seasoning とは区別する。
- Factor から計算する総予定外減少率は、公開される「任意期限前償還 CPR」と一致するとは
  仮定しない。長期延滞・その他解約、差替え、丸め、回収月と支払月のラグを別途表示する。
- 予測特徴量は原則1か月ラグとし、同月の実績 Factor/CPR を説明変数に使わない。

## 4. モデルと評価

最初の推定モデルはプール月次データに適した fractional logit とする。比較対象は次の4つ。

1. 固定 PSJ
2. seasoning のみ
3. seasoning + WAC/JGB 金利 proxy
4. seasoning + 金利 proxy + lagged burnout + 季節性 + vintage + 公開マクロ

各モデルを暦月 holdout と最新 vintage holdout で再推定・評価する。MAE、RMSE、残高加重誤差、
累積元本キャッシュフロー誤差、観測窓内の truncated WAL 誤差を保存する。最終モデルは全学習可能
データで再推定する。高度な GAM、mixed effects、gradient boosting、competing risks は同じ予測
インターフェースへ追加する。

## 5. キャッシュフローと価格

JHF の将来予定 Factor の月次比率で約定元本を減らし、その後に予測 SMM を適用する純粋関数を
中核とする。利息は月初残高 × 年率 coupon / 12。任意の 10% clean-up call は明示的なシナリオ
引数とし、実際の公告・契約条件を自動推測しない。

WAL、現在価値、effective duration、convexity は生成済みキャッシュフローから計算する。
MVP の価格はフラット利回りによる dirty price で、OAS・金利パス依存 prepayment は拡張境界に残す。

## 6. CLI と成果物

```bash
jhrmbs ingest
jhrmbs build-dataset
jhrmbs train
jhrmbs predict --issue JHF-220
jhrmbs cashflow --issue JHF-220
jhrmbs report --issue JHF-220
```

設定、README、データ辞書、ソース一覧、モデル仕様、ADR、実行可能 Notebook、単体テストと
データ品質テストを含める。

## 7. MVP 受入条件

- live ingest が取得失敗時に再試行し、manifest と SHA-256 を残す
- JHF workbook の列順・余分な sheet・列名の軽微変更を header 検索と alias で吸収する
- panel の粒度、必須値、重複、範囲、Factor 単調性、鮮度を自動検証する
- 4モデルが2種類の OOS split で比較され、seed・設定・学習期間が保存される
- PSJ と推定モデルの少なくとも2シナリオで将来 CF と WAL を生成できる
- 回号別技術レポートに定義、根拠、予測、リスク、限界、出典が含まれる
- `pytest`、`ruff`、型検査、Notebook top-to-bottom、CLI smoke test が通る
