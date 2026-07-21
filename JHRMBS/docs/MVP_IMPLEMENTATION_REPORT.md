# JHRMBS MVP 実装・検証ノート

## 1. この文書の位置づけ

本書は、公開データだけで完結する JHRMBS MVP について、実装範囲、データ定義、モデル、
キャッシュフロー、実データ検証結果、再現手順、既知の制約、次段階を一か所にまとめた
引き継ぎ用の実装ノートである。

仕様の正本は個別のデータ辞書・モデル仕様・ADR とし、本書はそれらを横断する実装時点の
スナップショットとして扱う。数値結果は将来のデータ更新で変わるため、必ず manifest ID と
model run ID を併記する。

| 項目 | 値 |
|---|---|
| 文書作成日 | 2026-07-22 |
| 実データ snapshot | `20260720T071835Z` |
| model run | `20260720T120427Z` |
| 最新観測支払月 | 2026-07-01 |
| 検証対象コード | `origin/main@9295079`（文書追加前） |
| JHRMBS の主要実装履歴 | `148d090` → `bde63ca` → `e5c0b0f` |

> 数値は調査・教育用の検証結果であり、投資判断、公式価格、会計・規制報告には使用しない。

## 2. 結論

公開データ MVP は、取得から回号別レポートまで end-to-end で動作する状態にある。

- JHF と4種類の公式外部系列を retry・cache・provenance 付きで取得できる。
- 回号マスター、回号×支払月 panel、時点整合した特徴量を Parquet と監査用 CSV に保存できる。
- CPR、SMM、標準 PSJ、Factor 逆算総減少率、公表3成分の結合率を再計算・照合できる。
- 固定 PSJ、seasoning、rate、full の4モデルを時系列・vintage OOS で比較できる。
- champion または明示モデルから将来 CPR / Factor、元利金、WAL、Duration、Convexity、
  dirty price を生成できる。
- 実行設定、乱数 seed、入力 hash、係数、予測、評価結果、レポートを run 単位で追跡できる。
- 51件のテスト、Ruff、strict mypy、lock 整合、実行済み Notebook の検査が通過している。

一方、借手別データ、統一定義の長期住宅ローン金利、確率的金利パスは公開情報から得られない。
したがって、現 MVP の `rate` は JGB proxy を用いたプールレベル予測モデルであり、借換え行動の
因果モデルでも OAS モデルでもない。

## 3. 実装範囲

### 3.1 要求との対応

| 要求 | MVP 状態 | 実装内容・残課題 |
|---|---|---|
| JHF Excel・CSV・PDF の取得 | 完了（PDF は除外判断） | JHF 年度別 XLS/XLSX と公式外部データを取得。フラット35過去 PDF は脆弱な座標抽出を避けた |
| 回号別月次 panel | 完了 | `issue_id × payment_month`、将来予定行も保持 |
| CPR / SMM / PSJ / Factor | 完了 | 単位検査、変換、Factor reconciliation を実装 |
| WAC / WAM / WALA | 完了 | 発行時・月次値を標準化し、lag feature を生成 |
| 任意・長期延滞・その他解約 | 部分完了 | 別列保存と total-decrement scenario は可能。因果的 competing risk 推定は未実装 |
| 金利・住宅・マクロ系列 | MVP 完了 | JGB、現行フラット35 snapshot、住宅着工、M3。統一的なフラット35過去系列は未収録 |
| 特徴量 | 完了 | seasoning、金利 proxy、burnout、季節性、vintage、住宅着工、M3 |
| 期限前償還モデル | ベースライン完了 | fractional logit 3種 + 固定 PSJ。GAM / mixed effects / boosting は拡張候補 |
| OOS 評価 | 完了 | 最新12支払月と最新2 vintage 年で再学習・評価 |
| 将来 cashflow | 完了 | model / PSJ、任意 total decrement、明示 clean-up call |
| WAL / Duration / Convexity / 価格 | MVP 完了 | deterministic path とフラット年複利 yield による dirty price |
| OAS | 境界のみ | rate-path provider と path-dependent prepayment の実装が必要 |
| 可視化 | 完了 | 実行済み Notebook と self-contained HTML 回号別レポート |
| CLI・設定・テスト・文書 | 完了 | 6 CLI、YAML、51 tests、Notebook、データ辞書、モデル仕様、ADR |

### 3.2 意図的な非対象

- 借手・loan 単位の属性推定、借換確率、信用モデル
- 有料ベンダーデータの同梱または利用必須化
- PDF グラフ座標からの精密な金利時系列復元
- 契約条項を推測した clean-up call の自動適用
- clean price、経過利息、休日規則、settlement convention の銘柄別確定
- 金利シミュレーション、モンテカルロ、OAS
- 本番取引・会計・規制システムへの直接接続

## 4. アーキテクチャ

### 4.1 データフロー

```text
official public sources
        │
        ▼
raw/objects + raw/manifests
        │  immutable bytes, URL, retrieval time, SHA-256, HTTP validators
        ▼
processed/issues + processed/issue_month_panel + external monthly series
        │  standardized grain, units, parser lineage, data-quality findings
        ▼
features/model_features
        │  lagged pool state, publication lag, rate mode, model eligibility
        ▼
models/<run_id>
        │  split models, OOS rows, metrics, champion rule, full-sample models
        ▼
predictions/<issue_id>
        │  future CPR/SMM/Factor under explicit assumptions
        ▼
cashflows/<issue_id>
        │  scheduled principal, prepayment, interest, risk summary
        ▼
reports/<issue_id>
           self-contained HTML + metadata
```

計算用表は Parquet、同じ粒度の監査用表は UTF-8 CSV として保存する。表 artifact ごとに列、行数、
SHA-256、生成日時を metadata JSON に残す。重いデータと生成物は `_data/jhrmbs` に置き、Git には
含めない。

### 4.2 主なモジュール責務

| モジュール | 責務 |
|---|---|
| `ingest.py` / `util.py` | HTTP 制約、retry、cache、content-addressed 保存、snapshot manifest |
| `sources/jhf.py` | JHF workbook の sheet / header 探索、列 alias、回号 ID、日付解析 |
| `sources/external.py` | JGB、フラット35、住宅着工、M3 の標準化・定義検査 |
| `dataset.py` | issue master、月次 panel、外部系列、lineage artifact の構築 |
| `quality.py` | grain、重複、範囲、単調性、鮮度、特徴量の critical 検査 |
| `features.py` | lag、seasoning、burnout、季節性、vintage、macro、rate mode |
| `models/fractional_logit.py` | L2 付き fractional logit の fit / predict / serialization |
| `models/training.py` | OOS split、指標、champion 選定、全量再学習、run metadata |
| `forecast.py` | 予定 Factor 終了までの再帰的 CPR / Factor 予測 |
| `cashflow.py` | deterministic cashflow の純粋関数 |
| `cashflow_service.py` / `risk.py` | scenario 接続、WAL、PV、Duration、Convexity |
| `report.py` | 品質、モデル安定性、感応度、制約を含む回号別 HTML |
| `artifacts.py` | Parquet / CSV / JSON と hash metadata の共通保存 |

## 5. データ取得と provenance

### 5.1 公式ソース

| source ID | 提供元 | 形式 | 利用 |
|---|---|---|---|
| `jhf_monthly` | 住宅金融支援機構 | 年度別 XLS/XLSX + index HTML | 回号情報、予定／実績 Factor、WAC、WAM、CPR、WALA、解約率 |
| `mof_jgb` | 財務省 | 全期間 CSV | 月末営業日の JGB 10年 |
| `flat35_current` | 住宅金融支援機構 | HTML | 21–35年・融資率9割以下の金利 snapshot |
| `mlit_housing_starts` | 国土交通省 | XLS | 新設住宅着工と前年比 |
| `boj_m3` | 日本銀行 | code API CSV | M3 と前年比 |
| `psj` | 日本証券業協会 | 定義文書 | 60か月 ramp の固定 PSJ baseline |

取得 URL と定義は [SOURCES.md](SOURCES.md) および `config/default.yml` で管理する。

### 5.2 取得契約

- 設定済み HTTPS host だけを許可し、redirect 後の host も再検査する。
- timeout、最大 byte 数、指数 backoff、最大 retry 回数を設定する。
- retry は一時障害として定義した status に限定し、404、host 違反、oversize 等は fail fast する。
- ETag / Last-Modified があれば条件付き GET を使い、304 は既存 bytes を再利用する。
- raw object は SHA-256 の content address で保存し、同一 bytes を重複保存しない。
- `ingest --source` の部分更新では、未選択 source を直前 snapshot から引き継ぎ、latest manifest を
  完全な source set に保つ。
- format drift は黙って補完せず `SourceFormatError` として停止する。

各 manifest record は最低限、source / final URL、UTC 取得日時、元ファイル名、SHA-256、byte 数、
media type、対象期間、データ定義、HTTP validator、変換履歴、設定 hash を保持する。

### 5.3 PDF の判断

フラット35の公式な過去推移は PDF グラフ中心であり、必要な精度と定義を保った公式 CSV / XLS の
代替を確認できなかった。MVP は PDF 座標抽出を実装せず、現行 HTML を月次 snapshot として蓄積する。
過去学習期間は全行を JGB proxy に統一し、異なる定義を一つの係数へ混在させない。

## 6. JHF workbook の標準化

JHF の掲載ページから `.xls` / `.xlsx` link を発見するため、固定ファイル名には依存しない。

1. 各 sheet の先頭20行から正規化後の `債券年月` header を探す。
2. 列位置ではなく日本語 header alias で列を対応付ける。
3. 支払月、当初予定 Factor、実績 Factor を必須列とする。
4. 通常、S、T、グリーン、E55 を安定した `issue_id` と `series_type` に正規化する。
5. 和暦・日本語年月を月初の `payment_month` に変換する。
6. 回号 sheet でない sheet は理由と原本を品質 report に記録して skip する。
7. 各行に `source_filename`、`source_sha256`、`parser_version` を残す。

実データ snapshot では `5016_ext_99_18.xls` の `支払償還状況表` だけが非回号 sheet として記録され、
想定どおり skip された。

## 7. データ定義と計算

### 7.1 単位

- `_pct` は百分率で、`6.0` は 6% を表す。
- `factor`、`smm`、cashflow 内部 rate は小数で、`0.005` は 0.5% を表す。
- 金額は JPY、期間は列名に従って months または years とする。
- 日付は月初 `datetime64` で、JHF の「債券年月」を `payment_month` として表す。
- 欠損は推測で埋めず `null` とする。モデル内補完値は train sample だけから計算して保存する。

### 7.2 CPR と SMM

公表 CPR は年率、内部の SMM は月率として次で変換する。

$$
SMM_t=1-(1-CPR_t)^{1/12},
\qquad
CPR_t=1-(1-SMM_t)^{12}.
$$

入力は内部計算時に小数へ直し、出力列名の `_pct` で百分率へ戻す。範囲外 rate は例外にする。

### 7.3 標準 PSJ

終端 CPR を $C^*$、WALA を月数 $a_t$ とすると、標準 PSJ は次である。

$$
CPR_t^{PSJ}=C^*\min\left(\frac{a_t}{60},1\right).
$$

WALA 0か月で 0%、60か月で終端 CPR に到達し、以後一定とする。米国 PSA の30か月 ramp とは
区別する。固定 baseline の既定終端 CPR は 6% である。

### 7.4 Factor からの総予定外減少

前月・当月の実績 Factor を $AF_{t-1},AF_t$、予定 Factor を $SF_{t-1},SF_t$ とすると、予定元本後の
期待 Factor と総予定外減少率を次で診断する。

$$
AF_t^{sched}=AF_{t-1}\frac{SF_t}{SF_{t-1}},
\qquad
SMM_t^{implied}=1-\frac{AF_t}{AF_t^{sched}}.
$$

これは公表任意期限前償還 SMM そのものではない。長期延滞、その他解約、差替え、リスケジュール、
丸め、回収月と支払月の lag を含み得るため、等式制約ではなく reconciliation 診断として保存する。

### 7.5 公表 decrement の分離

任意期限前償還、長期延滞、その他解約は別列で保持する。明示した total-decrement scenario では、
月率 $s_k$ を条件付き独立な decrement とみなす仮定の下で次の生存確率積を使う。

$$
s_{total}=1-\prod_k(1-s_k).
$$

長期延滞・その他解約には予測モデルを置かず、直近12か月平均を将来一定とする。これは scenario
仮定であり、借手レベル competing risks の推定ではない。

## 8. 特徴量と時点整合

panel の target は支払月 $t$ の任意期限前償還 SMM である。pool state は同じ回号の $t-1$ 支払月、
外部系列は既定で $t-1$ 月を使用し、`information_month` に明示する。

| 特徴量 | 定義 |
|---|---|
| `seasoning_ratio` | `clip(prediction_wala_months / 60, 0, 1)` |
| `burnout_lag1` | `(scheduled_factor_lag1 - factor_lag1) / scheduled_factor_lag1` |
| `month_sin`, `month_cos` | 支払月の12か月 Fourier 項 |
| `vintage_year_numeric` | 発行暦年 |
| `housing_starts_yoy_pct` | publication lag 後の住宅着工前年比 |
| `m3_yoy_pct` | publication lag 後の M3 前年比 |
| `exposure_jpy` | `face_amount_jpy × factor_lag1` |

同月の実績 CPR / Factor は feature にしない。発行時に前月値がない各回号の先頭行だけ、発行時
WAC / WAM / WALA と Factor 1.0 を使う。中途欠損 lag は埋めず、学習対象から除外する。この条件は
leakage に近い不整合を防ぐため回帰テストで固定されている。

### 8.1 金利特徴量の設計判断

借換インセンティブの本来の候補は次である。

$$
RefiIncentive_{j,t}=WAC_{j,t-1}-MortgageRate_{t-1}.
$$

ただし、同一定義の公式 mortgage rate 履歴が十分でないため、既定 `jgb_proxy` run は全期間で

$$
RateFeature_{j,t}=WAC_{j,t-1}-JGB10Y_{t-1}
$$

を使う。フラット35 snapshot と JGB proxy を同じ係数へ混在させない。`mortgage_rate` mode は、
`mortgage_rate_definition` で識別した単一定義が学習対象行の90%以上を覆う場合だけ実行できる。
予測時の rate-feature 平行シフトは感応度診断であり、将来金利パスではない。

## 9. モデル

### 9.1 比較対象

| model | 説明変数 | 位置づけ |
|---|---|---|
| `fixed_psj` | WALA、終端 CPR 6% | 推定を伴わない市場 baseline |
| `seasoning` | seasoning | 最小の推定 baseline |
| `rate` | seasoning + rate feature | 金利 proxy の増分を検証 |
| `full` | 上記 + burnout + 季節性 + vintage + 住宅着工 + M3 | 公開 pool データでの高度 baseline |

推定3モデルは logit link の Bernoulli quasi-likelihood と L2 penalty を使う fractional logit である。

$$
E[SMM_{j,t}\mid x_{j,t}]
=\Lambda(\beta_0+x_{j,t}'\beta),
\qquad
\Lambda(z)=\frac{1}{1+e^{-z}}.
$$

予測を $[0,1]$ に保ち、pool 月次 fraction を自然に扱え、係数監査が容易で、依存追加が小さいことを
採用理由とした。これは個々の loan の二値 prepayment likelihood ではない。

### 9.2 重み・補完・再現性

- exposure weight は予測直前の pool 残高とする。
- weight は平均1に正規化し、単一大型 pool の支配を避けるため20で cap する。
- 数値欠損は train 内中央値だけで補完し、train 内平均・標準偏差で標準化する。
- 補完値、標準化値、係数、feature 順序、L2、seed を model JSON / run metadata に保存する。
- 既定 seed は `20260720` である。
- 学習母集団は `series_type=monthly` の通常回号だけとする。S・T・グリーン・E55 は外挿警告と
  `outside_training_population=true` を残す。

### 9.3 Out-of-sample 設計

ランダム split は使わず、各 split・model で再推定する。

1. `time`: 2025-08 以降の最新12支払月を holdout。
2. `vintage`: 2025年以降発行の最新2 vintage 年を holdout。

主指標は前月残高加重 CPR RMSE である。併せて unweighted MAE / RMSE、加重 MAE、回号別 holdout
累積元本誤差、観測窓内 truncated WAL 誤差を保存する。truncated WAL は債券全期間 WAL ではない。

champion は推定3モデルの split 内加重 RMSE 順位を平均し、最小のモデルを選ぶ。同順位は平均 RMSE、
worst split RMSE、model 名の順で決着する。固定 PSJ は比較対象だが champion 候補には含めない。

## 10. 2026-07-20 実データ検証

### 10.1 取得・品質

| 項目 | 結果 |
|---|---:|
| snapshot ID | `20260720T071835Z` |
| manifest records | 25 |
| JHF records | 21 |
| 外部 source records | 4 |
| SHA-256 再照合 | 25 / 25 一致 |
| panel rows | 92,592 |
| issues | 226 |
| observed target rows | 23,326 |
| model training rows | 22,581 |
| training issues | 212 |
| latest observed payment month | 2026-07-01 |
| panel critical findings | 0 |
| duplicate feature rows | 0 |
| invalid target rows | 0 |
| rate feature missing share | 0% |
| rate proxy share | 100% |

25 records の内訳は JHF 21件、JGB・フラット35・住宅着工・M3 が各1件である。品質 report は
`staleness_months=0`、`status=pass` を記録した。

### 10.2 OOS 指標

単位は、加重 MAE / RMSE が CPR percentage point、累積元本 MAE が opening balance 比の percentage、
truncated WAL MAE が years である。

| split | model | weighted MAE | weighted RMSE | cumulative principal MAE | truncated WAL MAE |
|---|---|---:|---:|---:|---:|
| time | rate | 0.982570 | 1.325477 | 1.200491 | 0.021762 |
| time | full | 1.018773 | 1.363989 | 1.256885 | 0.013776 |
| time | fixed_psj | 3.251779 | 3.518973 | 2.219167 | 0.015061 |
| time | seasoning | 3.469382 | 3.746650 | 2.339893 | 0.014433 |
| vintage | seasoning | 0.903082 | 1.148406 | 0.270985 | 0.017655 |
| vintage | fixed_psj | 1.084945 | 1.451182 | 1.005760 | 0.024475 |
| vintage | rate | 1.128215 | 1.490222 | 1.052434 | 0.022465 |
| vintage | full | 1.298777 | 1.673968 | 1.232585 | 0.018463 |

champion は `rate` である。推定3モデルの平均 split rank は `rate=1.5`、`seasoning=2.0`、`full=2.5`。
ただし、time split の最良は `rate`、vintage split の最良は `seasoning` で、勝者が反転している。
したがって `rate` を普遍的に優位な構造モデルとは解釈せず、安定性上の警告を維持する。

### 10.3 JHF-220 予測

champion `rate`、run `20260720T120427Z` の予測は次のとおり。

| 項目 | 結果 |
|---|---:|
| current observation | 2026-07-01 |
| first forecast payment month | 2026-08-01 |
| last forecast payment month | 2060-07-01 |
| forecast rows | 408 |
| rate feature mode | `jgb_proxy` |
| frozen rate feature | -1.571 percentage points |
| outside training population | false |

予定 Factor path は JHF 公表値を使用し、pool Factor と burnout は一段ずつ再帰更新する。外部金利・
macro は将来モデルを持たず、直近既知値を固定する。

### 10.4 JHF-220 cashflow と risk

評価日は 2026-07-01、年複利フラット yield は 2.0%、clean-up call なし、現在残高は
40,337,640,000円である。

| scenario | WAL | dirty price / 100 | Macaulay duration | effective duration | convexity |
|---|---:|---:|---:|---:|---:|
| model `rate` | 14.913468 | 101.197709 | 12.241200 | 12.001186 | 230.874158 |
| model `rate` + published decrements | 14.299276 | 101.153391 | 11.792674 | 11.561453 | 217.596152 |
| fixed PSJ 6% | 10.173673 | 100.854526 | 8.758193 | 8.586468 | 128.571097 |

published-decrements scenario は、直近12か月平均の長期延滞 SMM `0.000229248` とその他解約 SMM
`0.000111801` を将来一定として任意 SMM に結合した診断である。契約上の将来実績を予測したものではない。

## 11. キャッシュフローと評価の契約

前月残高 $B_{t-1}$ と連続する予定 Factor から、約定元本を先に計算し、その後に任意 SMM を適用する。

$$
B_t^{sched}=B_{t-1}\frac{SF_t}{SF_{t-1}},
\qquad
P_t^{sched}=B_{t-1}-B_t^{sched},
$$

$$
P_t^{prep}=B_t^{sched}s_t,
\qquad
B_t=B_t^{sched}(1-s_t),
\qquad
I_t=B_{t-1}\frac{coupon}{12}.
$$

この順序により、予定元本と任意期限前償還の二重計上を避ける。engine は immutable dataclass を
入力する純粋関数で、日付昇順、rate 範囲、予定 Factor 単調性、元本完済を検査する。

clean-up call は既定で無効である。明示時だけ current / future factor が threshold 以下になった時点から
指定 lag 後に残高を償還する。現在既に threshold 以下の場合も countdown を開始する。

WAL は元本支払時点の加重平均、PV は評価日から ACT/365.25 の年数と年複利フラット yield を使う。
dirty price は `PV / current balance × 100`。Macaulay / effective duration と convexity は、同じ
期限前償還 path を固定した yield 平行シフトである。rate-dependent prepayment を再推定しないため OAS
duration ではない。

## 12. 再現手順

すべてリポジトリルートで実行する。

```bash
uv sync --package jhrmbs

uv run --no-sync jhrmbs ingest
uv run --no-sync jhrmbs build-dataset
uv run --no-sync jhrmbs train

uv run --no-sync jhrmbs predict --issue JHF-220
uv run --no-sync jhrmbs cashflow --issue JHF-220 --scenario model
uv run --no-sync jhrmbs cashflow --issue JHF-220 \
  --scenario psj --psj-terminal-cpr-pct 6
uv run --no-sync jhrmbs cashflow --issue JHF-220 \
  --include-other-decrements
uv run --no-sync jhrmbs report --issue JHF-220
```

過去 run を固定する場合は `--run-id`、推定モデルを固定する場合は `--model seasoning|rate|full`、
金利仮定を上書きする場合は run の rate mode と一致する引数を使う。CLI override と scenario は
prediction / cashflow / report metadata に残る。

### 12.1 主な artifact

| artifact | 場所 |
|---|---|
| latest raw manifest | `_data/jhrmbs/raw/manifests/<snapshot_id>.json` |
| issue master / panel | `_data/jhrmbs/processed/` |
| quality / lineage | `_data/jhrmbs/processed/data_quality_report.json` 等 |
| model feature | `_data/jhrmbs/features/` |
| run metadata / metrics | `_data/jhrmbs/models/<run_id>/` |
| latest run pointer | `_data/jhrmbs/models/latest_run.json` |
| issue forecast | `_data/jhrmbs/predictions/<issue_id>/` |
| cashflow / risk | `_data/jhrmbs/cashflows/<issue_id>/` |
| HTML report | `_data/jhrmbs/reports/<issue_id>/` |
| execution log | `_data/jhrmbs/logs/` |

## 13. 検証記録

### 13.1 2026-07-22 のコード検証

文書追加前の `origin/main@9295079` に対して次を実行した。

```bash
uv lock --check
uv run --no-sync pytest JHRMBS/tests -q
uv run --no-sync ruff check JHRMBS
uv run --no-sync mypy --config-file JHRMBS/pyproject.toml JHRMBS/src/jhrmbs
```

結果:

- `uv lock --check`: success
- `pytest`: 51 passed
- `ruff`: all checks passed
- `mypy --strict`: 26 source files、issue 0
- Notebook 静的実行状態: code cell 9 / 9 に execution count、error output 0
- snapshot raw object: 25 / 25 で manifest SHA-256 と一致

2026-07-22 には live ingest と model 再学習を行っていない。10章の実データ数値は 2026-07-20 に
取得・生成された snapshot / run の再照合結果である。

### 13.2 回帰テストで固定した重要挙動

- CPR / SMM / PSJ と competing monthly rates の数値変換
- scheduled principal → voluntary prepayment → cleanup の計算順序
- current factor が cleanup threshold 以下の場合の countdown
- header drift、非回号 sheet、和暦・年月、source lineage
- retry 対象 status と deterministic failure の fail-fast
- 部分 ingest での manifest carry-forward
- 中途欠損 lag を発行時値で誤補完しないこと
- feature / panel critical finding で build を停止すること
- mortgage-rate 単一定義90% gate
- 特殊 series の外挿 warning / metadata
- forecast の WALA fallback と non-finite JSON の `null` 化
- total-decrement scenario、無関係 CLI 引数の warning
- report の base forecast 再利用、split rank reversal、rate sensitivity 表

## 14. 既知の制約とリスク

### 14.1 データ

- 公開 pool 月次データだけでは、loan 内の属性分布や借手別 burnout を識別できない。
- フラット35の同一定義・長期・機械可読な公式履歴が不足している。
- `payment_month` は JHF の債券年月であり、loan 回収月との正確な lag は商品資料で未確定である。
- Factor 逆算 decrement と公表3成分は、丸め・差替え・リスケジュール等により一致しないことがある。
- JHF の掲載 workbook 集合に依存するため、過去回号の取り下げによる survivorship bias を継続監視する。
- source format、列名、sheet 構成、API 定義の drift は将来起こり得る。現在は silent fallback せず停止する。
- `null` は未公表、対象外、解析不能を完全には区別しない。必要なら reason code の追加が必要である。

### 14.2 モデル

- JGB proxy の係数を住宅ローン借換金利の因果効果として解釈できない。
- vintage holdout は153行・17回号で、time holdout より小さい。rank reversal もあり不確実性が大きい。
- issue random effect を持たず、pool 間の未観測異質性を固定効果で十分には表現しない。
- 将来の rate / macro は直近値固定で、金利変動に応じた prepayment path 更新を行わない。
- clean-up、長期延滞、その他解約は scenario 仮定で、将来発生モデルではない。
- OOS 指標は過去 snapshot に対する結果であり、将来精度を保証しない。

### 14.3 Cashflow / valuation

- clean-up call の有無、threshold、lag を銘柄別契約から自動確定していない。
- 経過利息、clean price、休日、営業日、settlement、税、手数料は扱わない。
- coupon は月初残高に対する単純な年率 / 12 で、商品固有 day-count を確定していない。
- duration / convexity は prepayment path 固定で、金利と期限前償還の相互作用を含まない。
- dirty price はフラット yield の research metric であり、市場価格・公式評価ではない。

## 15. 優先ロードマップ

### P0: 運用とデータ信頼性

1. 月次 ingest の定期実行、snapshot 差分、鮮度、schema drift の通知。
2. 同一定義の公式 mortgage-rate history を手作業で検証し、source note と hash を付けて蓄積。
3. JHF 商品資料で回収月／支払月 lag、clean-up 条項、day-count、最終償還を回号別に確認。
4. raw manifest と processed artifact の hash 再照合を CI / 運用 check に組み込む。
5. 欠損 reason、source revision、retired issue の inventory を追加し survivorship bias を監視。

### P1: モデル高度化

1. GAM、issue / vintage random effects、gradient boosting を同じ OOS contract で比較。
2. calibration curve、残差の season / vintage / WALA / rate bucket 診断を追加。
3. 予測区間または bootstrap による parameter / vintage uncertainty を追加。
4. 長期延滞・その他解約の定義と母数を再確認し、妥当なら competing-risk model を実装。
5. 返済額差、PV 差、借換費用を明示した refinance economics を provider interface で追加。

高度モデルは weighted RMSE だけでなく、time / vintage の双方、cashflow・WAL 誤差、calibration、
proxy 依存、安定性を満たす場合だけ champion 候補にする。

### P2: OAS

1. zero curve / volatility / spread data provider を有料・無料 source から独立した interface にする。
2. 金利 path ごとに mortgage-rate proxy と期限前償還特徴量を更新する。
3. 各 path で cashflow を再生成し、discount factor と option-adjusted spread を解く。
4. deterministic MVP と同じ issue / scenario / artifact lineage を維持する。
5. OAS duration、key-rate risk、model risk、parameter uncertainty を別々に報告する。

## 16. 保守時の判断基準

- 生データは上書きせず、新 snapshot と hash を作る。
- 単位変換、日付 lag、target 定義を変更する場合は schema version と ADR を更新する。
- 同じ係数に異なる rate definition を混ぜない。
- 同月 target 情報を feature に入れない。補完は train 内だけで行う。
- 固定 PSJ を削除せず、すべての高度モデルを同じ OOS split で比較する。
- 実績 Factor と公表任意 CPR の差を誤差として消さず、reconciliation として残す。
- 商品契約を確認できない機能は自動推測せず、明示 scenario と metadata にする。
- 価格・risk 指標には valuation date、yield convention、prepayment path、単位を必ず残す。
- 失敗を silent fallback で隠さず、原本、sheet、列、source、run ID を含む診断を出す。

## 17. 関連文書

- [実装計画](IMPLEMENTATION_PLAN.md)
- [公開データソース](SOURCES.md)
- [データ辞書](DATA_DICTIONARY.md)
- [期限前償還モデル仕様](MODEL_SPEC.md)
- [ADR 0001: 公開プールデータ MVP と fractional logit](decisions/0001-public-data-mvp.md)
- [ADR 0002: 支払月基準の時点整合と deterministic cashflow](decisions/0002-timing-and-cashflow.md)
