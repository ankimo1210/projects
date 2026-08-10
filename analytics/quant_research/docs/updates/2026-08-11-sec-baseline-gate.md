# 2026-08-11 — SEC B9 baseline gate follow-up

## 結論

SEC EDGAR の bounded baseline は、企業・時間 holdout、固定 metric、単純
baseline を実行できることを確認した。一方、**B9 の実装開始ゲートはまだ保留**とする。
厳格な company × time split が $n=84$ で、事前に定めた $n\ge 200$ を満たしていない。
また、`CY2015Q4I` の現在 Frame を 2008 年以降の企業選定に使うと、過去へ現在の
universe を遡及する look-ahead / survivorship risk が残る。

このノートは Opus review の再計算結果を永続化したものである。raw SEC response、
bulk archive、User-Agent の連絡先は保存しない。raw を再取得できる正式な downloader と
manifest が揃うまでは、数値は feasibility evidence として扱い、B9 の実証結論とは呼ばない。

## 再計算された baseline evidence

Assets の前四半期が 1 億ドル以上という size floor を適用した bounded sample は
1,500 行・38 社だった。`pooled_mean` は zero baseline より改善したが、これは
「平均的な資産成長」を学ぶ単純 drift baseline であり、候補モデルの採用前に必ず含める。

| split | n | zero MAE | pooled MAE |
|---|---:|---:|---:|
| time holdout | 287 | 0.04873 | 0.04769 |
| company holdout | 450 | 0.05086 | 0.05037 |
| both | 84 | 0.04788 | 0.04686 |

この値は raw cache がないため、この checkout 上での完全な再実行結果ではない。
正式な B9 gate の判定は、archive を含む再取得後に同じ manifest から再計算する。

## B9 v1 Core contract

### Point-in-time filing join

- Company Facts の対象 fact は `accn` を必須とする。
- `accn` は Submissions の `recent` と `filings.files` の全 archive を結合して解決する。
- acceptance metadata が見つからない accession は失敗として扱い、`filed` 単独へ fallback しない。
- `acceptanceDateTime` の timezone を保持し、`America/New_York` の日付と `filingDate` の遅い方を基準にする。
- その基準日の次の米国連邦営業日を `availability_date` とする。holiday manifest を固定した場合は、
  その manifest を provenance に含める。
- 同一 period の value は first-reported vintage を使い、後続 amendment で過去の観測を上書きしない。

### Universe and analysis horizon

現在の Frame を過去へ適用しない。v1 Core は次の固定 anchor cohort を使う。

- concept/unit: `us-gaap/Assets/USD`
- anchor period end: `2015-12-31`
- anchor as-of: `2016-04-01` 以下で利用可能な fact のみ
- size floor: 前四半期 Assets $\ge 100\,\mathrm{M}$
- target observation: anchor 後（$analysis\_start\ge 2016\text{-}04\text{-}01$）に限定
- dynamic historical universe は、archive reconstruction が完了した後の Advanced とする

これにより、2008 年の target を 2015 年時点で選ばれた企業へ遡及することを禁止する。
実装上は `PITUniverseSpec` と `select_fixed_anchor_cohort` がこの境界を保持する。

### Baseline and acceptance gate

- primary metric: MAE
- secondary metric: median absolute error（medAE）
- reference metric: RMSE
- baseline ladder: zero / pooled drift / seasonal / company expanding mean
- candidate gate: primary を 1% 以上改善し、secondary を悪化させない
- strict failure: company × time split の有効標本が $n<200$ なら結論を出さない

実装上は `fundamentals_error_metrics` が3 metricと `n` を保存し、
`audit_split_counts` が最も厳しい split の gate を判定する。

## 実装した再現可能な最小部品

- `src/quant_textbook/sec_pit.py`
  - Submissions `recent` + `filings.files` archive の accession index
  - acceptanceDateTime 必須の availability 計算
  - first-reported vintage join
  - fixed anchor cohort selection
  - split count audit
  - MAE / medAE / RMSE
- `tests/test_sec_pit.py`
  - archive 由来 accession、欠落 acceptance、unresolved accession、holiday、
    anchor look-ahead、split gate、metricの fixture test
- `tools/fetch_sec_b9_cache.py`
  - 明示的なUser-Agent、rate limit、`recent` + `filings.files`全archive取得、content hash manifest

実SECへの取得は連絡先入りUser-Agentを指定して明示的に実行する。raw dataはrepositoryへ
commitしない。大規模panel builderと実データでの150社拡張はまだ残っており、次段階で
offline fixtureを追加してから実測する。その際、strict split $n\ge200$ を確認する。

## Gate status

| gate | 状態 | 備考 |
|---|---|---|
| Access | pass | 公式 SEC API の bounded取得は確認済み |
| Semantics | conditional pass | 上記 availability/PIT contract を採用 |
| Sample | hold | 38社/strict split $n=84$。150社程度へ拡張が必要 |
| Baseline | provisional pass | baseline は比較可能だが、archive再取得が未完了 |
| Teaching fit | pass | PIT、baseline、split監査へ接続可能 |

従って、B9 Notebook本文・model tournament・実証的な企業ファンダメンタルズ結論は、
archive join、anchor cohort、標本数、offline再現性の4点が完了するまで実装しない。
