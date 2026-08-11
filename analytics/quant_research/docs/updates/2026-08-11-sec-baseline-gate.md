# 2026-08-11 — SEC B9 baseline gate follow-up

## 結論

M6 の historical SEC cohort は、B9 の **実装開始ゲートを通過**した。固定した
company × time holdout は \(n=413\) で、事前登録した \(n\ge200\) を満たす。したがって、
B9 の Notebook 本文と candidate model の設計には進める。ただし、これは **B9 の実証結果でも
model 選定でもない**。現時点で確認したのは、実データを再取得・PIT 再構成・baseline 比較できる
再現可能な土台だけである。

この Core は [SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
の Company Facts / Submissions を用いる。取得は明示的な連絡先付き User-Agent と低い rate で行い、
[SEC の Fair Access 方針](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
に従う。raw response、連絡先、cache は repository に保存しない。

## M6 の historical cohort と実測結果

現在の構成銘柄や現在 Frame を過去に遡及しないため、2016年Q1 EDGAR master index の
`10-K` 提出者を seed にした。これは CIK-rank 上の deterministic feasibility cohort であり、
米国上場企業全体や任意の産業への代表性は主張しない。

| 段階 | 実測 | 扱い |
|---|---:|---|
| historical seed universe | 5,338 unique CIK | 2016 Q1 の exact `10-K`、CIK-rank evenly-spaced selection |
| requested seed | 300 CIK | protocol 固定 |
| SEC cache success / failure | 261 / 39 | 39件はすべて HTTP 404。失敗 CIK は panel へ入れない |
| Core concept exclusion | 1 CIK | `us-gaap/Assets/USD` がないため、別 taxonomy へ fallback せず除外 |
| fixed-anchor cohort | 164 CIK | `2015-12-31` Assets が `2016-04-01` 以下で利用可能、かつ \(\ge\$100\mathrm{M}\) |
| valid panel | 4,631 rows / 163 CIK | 1行 = CIK × 隣接四半期 pair |
| strict both holdout | 413 rows / 38 CIK / 183 availability dates | \(n\ge200\) を通過 |
| strict both training partition | 2,195 rows / 102 CIK / 534 availability dates | 空でないことを gate に含める |

source からは 166 個の非隣接四半期 transition（140 CIK、最大 2,419 日）と、同じ filing
availability date を共有する 12 pair（9 CIK）を除外した。出力 panel に残った gap は
60–98 日である。これらは補間せず、理由と件数を quality artifact に残す。

### Holdout coverage と baseline

time cutoff は B5–B8 と同じ `2023-10-23`、company split は `cik % 3 == 0`、minimum
holdout は 200 行で固定した。各予測では `known_at` より前に利用可能だった target だけを
training に使う。

| split | holdout rows | holdout CIK | holdout dates | training rows | training CIK | training dates |
|---|---:|---:|---:|---:|---:|---:|
| time | 1,078 | 96 | 247 | 3,553 | 163 | 633 |
| company | 1,771 | 61 | 662 | 2,860 | 102 | 733 |
| both | 413 | 38 | 183 | 2,195 | 102 | 534 |

strict `both` の log-Assets growth baseline は次のとおりである。company holdout では
company mean が利用できないため、事前に定めた pooled fallback を使う。

| baseline | MAE | medAE | RMSE |
|---|---:|---:|---:|
| zero | 0.042028 | 0.018403 | 0.143149 |
| pooled drift | 0.042017 | 0.020048 | 0.141582 |
| seasonal | 0.042028 | 0.018403 | 0.143149 |
| company expanding mean | 0.042017 | 0.020048 | 0.141582 |

これは candidate model の比較基準である。candidate が MAE を 1%以上改善し medAE を悪化させない
かは、B9 の pre-analysis specification と locked evaluation を実装してから別に判定する。

## 再現性 fingerprint

M6 の実測は raw data ではなく、次の manifest / derived artifact の連鎖で固定する。

| artifact | SHA-256 / contract |
|---|---|
| 2016 Q1 master index | `43ccb67ed90ad4229b02b99094846a291c6d1672eb25a1ee89dcb0636c2a264e` |
| selected 300-CIK canonical list | `79b873f2c74357486afbf008ac9bde36ab17165609dc051ab88c6e8c076fd02a` |
| seed manifest | `3ad7504baae4ed5f108c2b143df46cf2b4c6960c3a965d7c7c9ef3d2a25d3a9b` |
| batch manifest | `3cf4f63bff3ad48d6b86e2b3f755312609e9cd2efcf0f56085887234c9ce16f3` |
| M6 protocol | [`b9-m6-protocol.json`](../contracts/b9-m6-protocol.json) / `d2aab034e801a114d1d9a3c9a1b1543063ad37bbd963e2c653e1ff0c83c57995` |
| holiday manifest | `bcc920ceeefc77a2ec2394018526995104c5f1a74bf066a583996277a5c13314` / `pandas.USFederalHolidayCalendar`、1990-01-01–2036-01-14 |
| derived panel artifact | `6c6008c2f28c30299e15e37613cfb0b3b22e8fd283858f5b459227c7e4a412a8` |
| detached audit report | `3ac26319c60540c62956fc3045a29297174c5a9043bbc6ee50e216f271118a1b` |

`tools/prepare_sec_b9_seed_cohort.py`、`tools/prepare_us_federal_holiday_manifest.py`、
`tools/fetch_sec_b9_cache.py`、`tools/build_b9_panel.py`、
`tools/audit_sec_b9_panel.py` の順に実行する。最後の detached audit は raw SEC payload とraw
batch manifestを再読せず、derived artifact、seed manifest、holiday manifest、protocol、artifact内の
batch/cache-integrity summary を使って grain、PIT ordering、split、baseline、provenance を再計算する。
raw file の hash・child manifest・advertised archive の完全性はpanel buildの前後で fail-closed に検証する。

正式なM6判定では `audit_sec_b9_panel.py --require-modeling-gate` を使う。この実行では
`strict_provenance_accepted`、`strict_protocol_accepted`、`strict_sample_gate_accepted`、
`modeling_gate_accepted` がすべて `true` で、report の全 `checks` は `true` だった。

## B9 v1 Core contract

### Point-in-time filing join

- Company Facts の対象 fact は `accn` を必須とする。`accn` は Submissions `recent` と
  `filings.files` の **全 advertised archive** で解決し、cache 内の archive 集合と manifest hash を
  fail-closed で照合する。
- acceptance metadata が見つからない accession、CIK の不一致、壊れた payload は失敗とする。
  `filed` 単独への fallback はしない。
- `availability_date` は `America/New_York` の acceptance 日と `filingDate` の遅い方の次の
  米国連邦営業日である。holiday manifest は hash と coverage を artifact に保存する。
- 同一 period の value は availability が最も早い first-reported vintage を使う。後続 amendment や
  later availability は過去の観測を上書きしない。
- `us-gaap/Assets/USD` のない issuer は `missing_us_gaap_assets_usd` として理由付き除外する。
  IFRS や custom tag への自動代替はしない。

### Universe、行の grain、評価

- universe は `2015-12-31` の `us-gaap/Assets/USD` が `2016-04-01` 以下で利用可能で、
  **anchor 時点** Assets \(\ge\$100\mathrm{M}\) の fixed cohort である。各 row の前四半期 Assets に
  floor を再適用する仕様ではない。
- target period は `2016-04-01` 以後、行は CIK × 60–120日 gap の adjacent quarter pair とする。
  non-positive Assets、非隣接 period、previous/target availability が同日以下の pair は補間せず除外する。
- panel row は `previous_available_date > previous_period_end`、
  `target_available_date > target_period_end`、`target_available_date > known_at` を満たす。
- primary metric は MAE、secondary は medAE、reference は RMSE。baseline ladder は zero / pooled
  drift / seasonal / company expanding mean とする。
- strict gate は `both` holdout \(n\ge200\) **かつ** corresponding training partition が空でないこと。
  protocol の cutoff、company split、metric role は builder と audit の両方で固定値照合する。

## Gate status と残る境界

| gate | 状態 | 備考 |
|---|---|---|
| Access / cache integrity | pass | 261 success cache の child/raw hash と archive parity を検証 |
| PIT semantics | pass (Core) | availability、first-vintage、physical date orderを fail-closed にする |
| Sample | pass | strict both \(n=413\)、training 2,195 行 |
| Baseline | pass | 比較可能な baseline を固定。candidate model は未評価 |
| Teaching fit | pass | real-data source、PIT、quality、offline audit を教材へ接続できる |

残る境界は明示する。calendar-date anchor に適合する issuer だけの deterministic feasibility cohort であり、
cross-section の代表性を主張しない。derived artifact の detached audit は availability **順序**と
manifest を再検証するが、個々の raw `filingDate` / `acceptanceDateTime` からの再計算は build 時の
cache integrity と fixture test に依存する。network の transient 429/5xx に対する retry/backoff、
dynamic historical universe、raw filing text を用いる feature contract は B9 実装段階の別タスクである。

したがって次の作業は、B9 の estimand・feature availability・text retrieval scope・candidate set・
locked evaluation を pre-register し、この M6 artifact を変更せずに model tournament を開始することである。
