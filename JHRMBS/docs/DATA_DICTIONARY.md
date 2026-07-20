# データ辞書

## 共通規約

- grain は明記し、日付は月初 `datetime64` で「支払月」を表す。
- `_pct` は百分率（例: `6.0` = 6%）、`smm` と `factor` は小数（例: `0.005` = 0.5%）。
- 金額は JPY、期間は列名どおり months / years。
- 欠損は未公表・対象外・解析不能を区別せず `null` とし、推測補完しない。モデル内の数値欠損は
  train sample の中央値で補完し、その値を model JSON に保存する。

## `processed/issues`

grain: 1行 / `issue_id`。

| 列 | 型・単位 | 定義 |
|---|---|---|
| `issue_id` | string | 安定 ID。通常回号は `JHF-220`、S/T/green/E55 は prefix 付き |
| `issue_name` | string | JHF 公表表記 |
| `series_type` | category | `monthly`, `s`, `t`, `green`, `e55` |
| `issue_date` | date | 発行日 |
| `vintage_year` | year | 発行暦年 |
| `face_amount_jpy` | JPY | 発行額面額 |
| `coupon_pct` | 年率 % | MBS 表面利率 |
| `initial_wac_pct` | 年率 % | 発行時プール WAC |
| `initial_wam_years` | years | 発行時加重平均残存年数 |
| `initial_wala_months` | months | 発行時加重平均経過期間 |
| `source_filename`, `source_sha256`, `parser_version` | lineage | 原本・parser の識別子 |

## `processed/issue_month_panel`

grain: 1行 / `issue_id` × `payment_month`。将来の予定 Factor 行も保持し、`is_observed` で区別する。

| 列 | 型・単位 | 定義 |
|---|---|---|
| `payment_month` | month | JHF の債券年月（MBS 支払月） |
| `scheduled_factor` | decimal | 当初予定 Factor |
| `actual_factor` | decimal | 実績 Factor。将来は null |
| `wac_pct` | 年率 % | 月次プール加重平均金利 |
| `wam_years` | years | 月次加重平均残存年数 |
| `wala_months` | months | 月次加重平均経過期間 |
| `voluntary_cpr_pct` | 年率 % | JHF 公表の任意期限前償還率 |
| `rescheduled_factor` | decimal | JHF 公表のリスケジュール Factor |
| `long_delinquency_pct_monthly` | 月率 % | 長期延滞による差替・一部解約率 |
| `other_cancellation_pct_monthly` | 月率 % | 長期延滞以外の差替・一部解約率 |
| `voluntary_smm` | 月率 decimal | 公表 CPR を $1-(1-CPR)^{1/12}$ で変換 |
| `published_psj_terminal_pct` | 年率 % | その月の CPR を標準 PSJ の終端 CPR に換算した診断値 |
| `implied_total_smm` | 月率 decimal | 予定 Factor 控除後に実績 Factor から逆算した総予定外減少 |
| `combined_published_decrement_smm` | 月率 decimal | 任意・長期延滞・その他を生存確率積で結合 |
| `reconciliation_bps` | bp / month | implied total と公表3成分結合値との差。厳密一致は仮定しない |
| `actual_balance_jpy` | JPY | 発行額面 × 実績 Factor |
| `is_observed` | bool | 実績 Factor が公表済みか |

## `features/model_features`

grain: 1行 / `issue_id` × 予測 `payment_month`。末尾 `lag1` はその回号の前支払月に既知の値。

| 列 | 型・単位 | 定義 |
|---|---|---|
| `target_smm` | decimal / month | 当月の任意期限前償還 SMM（目的変数） |
| `factor_lag1`, `scheduled_factor_lag1` | decimal | 前月実績／予定 Factor |
| `wac_pct_lag1`, `wam_years_lag1`, `wala_months_lag1` | % / years / months | 前月プール状態 |
| `prediction_wala_months` | months | 予測対象月の WALA proxy |
| `seasoning_ratio` | decimal | `clip(prediction_wala / 60, 0, 1)` |
| `burnout_lag1` | decimal | `(scheduled_factor_lag1-factor_lag1)/scheduled_factor_lag1` |
| `exposure_jpy` | JPY | 前月実績残高。学習・評価 weight |
| `month_sin`, `month_cos` | decimal | 支払月の12か月周期 Fourier 項 |
| `information_month` | month | 外部データを join する時点。既定は支払月の1か月前 |
| `refi_incentive_pct` | percentage point | `WAC_lag1 - FLAT35 modal rate` |
| `wac_minus_jgb_10y_pct` | percentage point | `WAC_lag1 - JGB 10y` proxy |
| `rate_feature_pct` | percentage point | 設定した mode に従い、全期間を refi incentive または JGB proxy の一方で統一 |
| `rate_feature_is_proxy` | bool | `rate_feature_mode=jgb_proxy` かつ値が存在するか |
| `rate_feature_mode` | string | `jgb_proxy` または `mortgage_rate`。定義の自動混在を禁止 |
| `housing_starts_yoy_pct`, `m3_yoy_pct` | % YoY | 1か月 publication lag を置いたマクロ特徴量 |

## model / prediction / cashflow

- `models/<run>/metrics`: split × model。CPR MAE/RMSE、残高加重誤差、累積元本誤差、観測窓内
  truncated WAL 誤差。
- `predictions/<issue>`: 支払月、予定 Factor、予測 SMM/CPR/Factor、金利仮定、model run。
- `cashflows/<issue>`: 月初残高、約定元本、任意期限前償還、clean-up 元本、利息、月末残高。
- `*_summary.json`: WAL、最終元本期日、PV、dirty price / 100、Macaulay / effective duration、
  convexity、評価利回り。
