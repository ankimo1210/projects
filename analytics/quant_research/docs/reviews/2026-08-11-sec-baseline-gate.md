# SEC EDGAR Baseline Gate — 実測レポート

作成日: 2026-08-11
対象: `analytics/quant_research/docs/updates/2026-08-10-stage-2-data-feasibility-follow-up.md`
の「Gate判定」表で **Baseline = incomplete** とされていた唯一の未通過項目
実施者: Claude（リポジトリ内ファイルは未変更）

## 結論

**Baseline gate は通過する。** PIT パネルを構築し、numeric-only baseline を
企業 holdout × 時間 holdout で実行できた。metric と失敗条件も固定できる。
これで SEC は 5/5 gate 相当になる。

ただし B9 の設計に**必ず反映すべき実測結果が4件**ある。特に (1) と (2) は、
入れないと結果が意味を失う。

## 1. 実験の契約

follow-up ノートの PIT contract 7項目に沿って構成した。

| 項目 | 固定値 |
|---|---|
| Universe | `us-gaap/Assets/USD` frame `CY2015Q4I` の filer **7,018社** から決定的に60社抽出（cik 昇順で等間隔） |
| Concept | `us-gaap/Assets/USD`、form は 10-K / 10-Q / 10-K/A / 10-Q/A のみ |
| Value | 各 period end の **first-reported vintage**（`filed` 最小）。改訂値は使わない |
| Availability | `max(filed, acceptanceDateTime の日付)` の **翌営業日**（contract 項目3） |
| Target | 連続四半期（period end 間隔 60–120日）の Assets 対数変化 |
| 情報集合 | 前四半期が公開された時点（`known_at`）まで |
| Time holdout | `target_avail >= 2023-01-01` |
| Company holdout | `cik % 3 == 0`（学習側と素な企業集合） |

Baseline は4本、すべて PIT:
`zero`（水準のランダムウォーク）/ `seasonal`（4四半期前の成長率）/
`company_mean`（当該企業の過去成長率の expanding mean）/
`pooled_mean`（**公開済み**ターゲットのみを使う全企業 expanding mean）。

## 2. Gate 判定

| Gate | 判定 | 根拠 |
|---|---|---|
| Access | pass | 既報（follow-up ノート） |
| Semantics | pass | 既報 + 本レポート §4 |
| Sample | pass | filter 後 1,500行 / 38社 / 2008-09-30–2026-06-30 |
| **Baseline** | **pass** | 下表のとおり実行・比較・失敗条件の固定ができた |
| Teaching fit | pass | 既報 |

size floor 適用後（前四半期 Assets ≥ 1億ドル）の結果:

| Split | n | zero | seasonal | company_mean | pooled_mean |
|---|---:|---:|---:|---:|---:|
| time holdout（MAE） | 287 | 0.04873 | 0.06264 | 0.05622 | **0.04769** |
| company holdout（MAE） | 450 | 0.05086 | 0.07054 | 0.05687 | **0.05037** |
| both（MAE） | 84 | 0.04788 | 0.05480 | 0.05125 | **0.04686** |

## 3. B9 設計へ必ず入れるべき4件

### (1) size floor が無いと metric が壊れる

filter 無しの全パネル（2,400行）では、対数変化の分布が極端に裾が重い。

| 分位 | \|y\| |
|---|---:|
| p50 | 0.0368 |
| p90 | 0.4158 |
| p99 | 3.0992 |
| max | **11.2339** |

`max |y| = 11.23` は資産が約7.5万倍になった1行。zero-baseline の RMSE は
**0.6980** で、その大半が数行の外れ値由来である（winsorize(1,99) すると 0.3931）。

前四半期 Assets に下限を置くと解消する。

| 下限 | n | zero RMSE | medAE | max\|y\| |
|---|---:|---:|---:|---:|
| なし | 2,400 | 0.6980 | 0.0368 | 11.23 |
| ≥ $1M | 1,982 | 0.4163 | 0.0302 | 11.23 |
| ≥ $10M | 1,843 | 0.3507 | 0.0283 | 11.23 |
| **≥ $100M** | **1,500** | **0.2156** | 0.0244 | 6.92 |

shell company / reverse merger / SPAC が universe に残ると、モデル比較が
数行の外れ値の取り合いになる。**universe 規則に size floor を含める。**

### (2) RMSE を primary metric にしない

size floor 後も裾は残る。primary は **MAE**、secondary に **medAE**、RMSE は
参考値に留めるべきである。B5–B8 が RMSE を primary にしているのは、
Treasury の日次金利変化が概ね対称・薄裾だからで、fundamentals には引き継げない。

### (3) baseline ladder に pooled drift を入れる

**`pooled_mean` が `zero` を安定して上回った。**

| Split | MAE 改善 | medAE 改善 | B5/B6 と同じ 1% gate |
|---|---:|---:|---|
| time holdout | **+2.14%** | +6.19% | **PASS** |
| both | **+2.13%** | +3.05% | **PASS** |

内容は「資産は平均的に増える」という drift 項にすぎない。これを baseline に
含めないと、任意のモデルがこの自明な drift を学んだだけで採用 gate を通ってしまう。
`seasonal`（−28.55%）と `company_mean`（−15.36%）は明確に劣り、
**単純 baseline が強いという Stage 2 の傾向はここでも維持される。**

### (4) accn の 12.2% が submissions の `recent` に無い

PIT contract 項目1 は「Company Facts の各 fact を `accn` で Submissions へ結合する」
と定めている。実測すると:

```
10-K/10-Q 系 form の facts : 5,218
うち accn が recent に無い : 637 (12.2%)
```

`submissions/CIK##########.json` の `recent` は1,000件で打ち切られるため、
**8件に1件は `filings.files` の分割アーカイブを追わないと acceptance 時刻が取れない。**
現状は `filed` へフォールバックしており、8.6% の日付不一致がそのまま availability
の誤差になる。downloader に分割アーカイブ取得を必須で入れる。

## 4. 改訂による look-ahead は「時期依存」

follow-up ノートの Frames 非 PIT の指摘は正しい。ただし**その影響の大きさは
評価期間で変わる**ことが分かった。

target 行のうち PIT 値と改訂後値が異なるのは全体の **9.67%**（最大 |差| は
対数変化で 9.24）。ただし era 別では:

| 期間 | rows | 改訂で変わる行 |
|---|---:|---:|
| 2008–2014 | 709 | 102 (14.4%) |
| 2015–2019 | 898 | 99 (11.0%) |
| 2020–2022 | 385 | 16 (4.2%) |
| 2023–2026 | 408 | 15 (3.7%) |

推奨する 2023+ holdout の内側では、287行のうち差が出るのは13行、最大 |差| は
0.0317 で、MAE・medAE は小数点4桁まで変わらなかった。

つまり **Frames を使ってはいけないという結論は歴史的パネルで正しく、
直近テスト窓だけを見ると数値はほとんど動かない。** B9 では「look-ahead は
常に結果を変える」ではなく「長期パネルでは変え、直近窓では小さい」と
正確に教えるべきである。この区別を書かないと、学習者が
「差が出なかったから PIT は不要」と誤って一般化する。

## 5. 提案する B9 の固定契約

```
universe      : CY2015Q4I の Assets filer、かつ前四半期 Assets >= $100M
concept       : us-gaap/Assets/USD、form 10-K/10-Q(/A)
value         : first-reported vintage のみ
availability  : max(filed, acceptanceDate) の翌営業日
                accn は filings.files まで追って解決する
target        : 連続四半期の Assets 対数変化
splits        : company holdout (cik % 3) × time holdout (target_avail >= 2023-01-01)
primary       : MAE       secondary: medAE      参考: RMSE
baseline ladder: zero / pooled drift / seasonal / company mean
採用 gate     : primary を 1% 以上改善し、secondary を悪化させない
失敗条件      : 最も厳しい split の n < 200 なら結論を出さない
```

**最後の1行が現状は満たせていない。** 60社では最も厳しい split
（未知企業かつ将来期間）が **n=84** しかない。n≥200 には**約150社**必要。
B9 実装時は universe を拡大すること。

## 6. 再現手順

```bash
UA='quant-research-textbook feasibility spike <contact>'
curl -A "$UA" 'https://data.sec.gov/api/xbrl/frames/us-gaap/Assets/USD/CY2015Q4I.json'
# 上位 frame から決定的に CIK を抽出し、各社について:
curl -A "$UA" "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json"
curl -A "$UA" "https://data.sec.gov/submissions/CIK0000320193.json"
```

解析スクリプト（`pit_panel.py` / `pit_baseline.py`）と取得済みキャッシュは
セッション用一時領域にある。永続しないので、B9 実装時は
`tools/audit_stage2_feasibility.py` と同じ形式で
リポジトリ内に再計算スクリプトを置くこと。raw data と個人の連絡先は commit しない。

```
/tmp/claude-1000/-home-kazumasa-projects/318f8fd7-dcfa-49ff-9a45-dcfd382eeef9/scratchpad/spike/
```
