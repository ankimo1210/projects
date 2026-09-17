# 賃貸・借上社宅・購入 比較モデル — 成果物パッケージ

更新日: 2026-09-17

## 目的

東京のマンションを想定し、次の3ケースを同じ資金制約のもとで比較するためのモデルです。

1. 通常賃貸
2. 会社の借上社宅制度を利用した賃貸
3. 住宅ローンを使った購入

主なアウトプットは、購入と各賃貸ケースの最終純資産が一致する **住宅価格上昇率の損益分岐点 `g*`** です。

## まず開くファイル

`report/housing_rent_corporate_buy_report_v2.html`

単一HTMLで完結しており、ブラウザで開けばシミュレーターとして動作します。サーバーは不要です。

## フォルダ構成

- `report/housing_rent_corporate_buy_report_v2.html` — 最新版・主成果物
- `report/housing_rent_corporate_buy_report_v1_archive.html` — 旧版アーカイブ
- `docs/assumptions_and_parameters.md` — 静的・動的パラメータ一覧と基準値
- `docs/model_specification.md` — 比較ロジック・主要数式・解釈
- `data/parameter_catalog.csv` — パラメータ一覧のCSV
- `data/baseline_sensitivity_snapshot.csv` — 基準ケースと代表感応度のスナップショット
- `source/full_source.html` — v2のソーススナップショット
- `source/extracted_styles.css` — HTML内CSSを読みやすく抽出
- `source/extracted_scripts.js` — HTML内JavaScriptを読みやすく抽出

## 基準ケース

- 年収: 5,000万円
- 社宅家賃: 75万円/月
- 購入価格: 2.5億円
- LTV: 90%
- ローン: 35年・元利均等・年1.5%
- 比較期間: 10年
- 金融資産の税引後運用利回り: 年3%
- 所有コスト: 250万円/年
- 購入諸費用: 購入価格の7%
- 売却費用: 売却価格の3.5%

この基準ケースでは、計算上の住宅価格上昇率 `g*` は概ね:

- vs 通常賃貸: **+0.14%/年**
- vs 借上社宅: **+2.46%/年**

です。

## 重要な注意

社宅制度の税務・社会保険上の取り扱いは会社規程・給与処理によって異なります。本モデルでは、ユーザーが説明した「額面5,000万円から年900万円の家賃相当額を控除し、残額を給与明細上の報酬として課税する」仕組みを基準ケースとしてモデル化しています。実行判断には実際の給与明細・社宅規程・税務確認が必要です。
