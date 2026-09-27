# Stage 2 Data Feasibility Spike — 実測レポート

作成日: 2026-08-10
対象: `analytics/quant_research/docs/plans/2026-08-10-stage-2-real-data-first.md` §4
実施者: Claude（GPT の Stage 2 実装とは独立、リポジトリ内ファイルは未変更）
成果物の置き場: 本ノートのみ。プロジェクト内 `docs/` は触っていない。

## 結論

**Treasury・SEC EDGAR とも 5 gate を通過する。**ただし両ソースに、素直に実装すると
静かに結果を壊す罠が計3件ある。いずれも実データで再現を確認したので、Stage 2 では
罠そのものを教材化できる。

| Gate | Treasury daily curve | SEC EDGAR |
|---|---|---|
| Access | 通過（ただし bulk CSV は 403） | 通過 |
| Semantics | 通過（構造変化6回・罠2件を特定） | 通過（`filed` が PIT key・罠1件を特定） |
| Sample | 通過（9,157営業日 / 完全パネル4,901日） | 通過（frames 1本で 6,428社） |
| Baseline | 通過（no-change vs AR(1) 実行済み） | **未実測** |
| Teaching fit | 通過 | 通過 |

計画 §4 の「1つでも通らないsourceは合成データで補わず候補から外す」に照らし、
**除外すべきソースは無い**。SEC の Baseline gate だけ残っている。

---

## 1. Treasury daily par yield curve

### Access

| 項目 | 結果 |
|---|---|
| 年次 XML feed | HTTP 200、230–360 KB/年、約9秒/年、認証なし・APIキー不要 |
| **bulk CSV endpoint** | **HTTP 403 Access Denied** |
| 全履歴の取得コスト | 37リクエスト（1990–2026）、約6分、計11 MB |
| feed の `updated` | `2026-08-07T15:56:16Z` |

`daily-treasury-rates.csv/all/all?...&_format=csv` は 403 を返す。**再現可能な取得経路は
年次 XML feed のみ**で、downloader は年単位ループ＋レート制限前提で書く必要がある。

```
https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml
  ?data=daily_treasury_yield_curve&field_tdr_date_value=<YYYY>
```

### Semantics — テナー集合は37年で6回変わる

| テナー | 初出 | 備考 |
|---|---|---|
| 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 30Y | 1990-01-02 | 起点 |
| 20Y | 1993-10-01 | |
| 1M | 2001-07-31 | |
| 2M | 2018-10-16 | |
| 4M | 2022-10-19 | |
| 1.5M | 2025-02-18 | |

**「1990年からの constant-maturity パネル」は存在しない。** universe 規則を時点整合に
書かないと、後年のテナーを遡及適用することになる。

### 罠1: 30年債は2002–2006年に存在しない

- 最終観測 **2002-02-15**、再開 **2006-02-09**
- **2003・2004・2005年の30Y観測数は 0**

長期端を含む panel を `dropna()` すると4年分が丸ごと消え、`ffill` すると4年間の定数系列に
なる。どちらも黙って起きる。

### 罠2: 休場日に phantom row が出る

`2010-10-11`（Columbus Day）は entry が存在するが、**全テナーが null で
`BC_30YEARDISPLAY` だけ `'0.00'`**。

```
{'NEW_DATE': '2010-10-11T00:00:00', 'BC_30YEARDISPLAY': '0.00'}
```

`BC_30YEARDISPLAY` は `BC_30YEAR` と別に存在する15番目の列で、これを拾うパーサは
**休場日に「30年金利 0.00%」という実在しない観測を得る**。列選択を明示し、
全テナー null の行を落とす必要がある。

### 罠3: ゼロ金利期の個別欠損

2008年12月、`BC_3MONTH` が **2008-12-10 / 12-18 / 12-24** の3日だけ欠測。前後は 0.03 → 0.01 で、
同時期の 1M は 0.00。市場ストレス下でテナー単位に穴が開くため、
「欠損は休場日のみ」という前提は成立しない。

その他の intra-year 欠損: 1993 20Y(188)、2001 1M(145)、2002 30Y(218)、2006 30Y(26)、
2018 2M(198)、2022 4M(199)、2025 1.5M(31) — いずれも新規導入・廃止の年で説明がつく。

### Sample と Baseline

- 全観測 **9,157営業日**（1990-01-02 .. 2026-08-07）
- コア5テナー（3M/2Y/5Y/10Y/30Y）が完全に揃う期間 = **2007-01-02 以降 4,901日 × 5**

10Y 日次変化、時系列順 70/30 分割（test n=1,470、2020-09-21..2026-08-07）:

| モデル | RMSE (bp) |
|---|---:|
| no-change（ランダムウォーク） | **5.931** |
| AR(1)（train のみで係数推定） | 5.940 |

AR(1) は no-change を **0.16% 下回る**。B5 の「強い単純 baseline を先に置く」に
そのまま使える結果で、教材として都合がよい方向に転んでいない。

### 未検証

改訂（revision）の有無は、同一年を**日を空けて2回取得**しないと測れない。今回は単発取得
なので未実施。`updated` フィールドの監視と content hash の保存で検出する設計にすべき。

---

## 2. SEC EDGAR

### Access

| endpoint | 結果 |
|---|---|
| `data.sec.gov/submissions/CIK##########.json` | HTTP 200、0.26s、164 KB |
| `data.sec.gov/api/xbrl/companyfacts/CIK##########.json` | HTTP 200、0.28s、3.79 MB |
| `data.sec.gov/api/xbrl/frames/...` | HTTP 200、856 KB |
| `www.sec.gov/files/company_tickers.json` | 10,398 ticker→CIK |
| bulk `companyfacts.zip` | HTTP 200、**1.3 GB** |
| bulk `submissions.zip` | HTTP 200、**1.4 GB** |

User-Agent に連絡先の申告が必要（SEC の要求）。今回は
`quant-research-textbook feasibility spike kikeuchi1210@gmail.com` を使用。

bulk 合計 2.7 GB はリポジトリに置けない。計画 §3 の「downloader、manifest、local cache契約」が
そのまま必要になる。

### Semantics — 時刻フィールドが3層ある

| フィールド | 意味 |
|---|---|
| `reportDate` | 対象期間の末日 |
| `filingDate` | 提出日（営業日ベース） |
| `acceptanceDateTime` | 受理時刻 |
| XBRL fact の `filed` | **その数値が公開された日 = availability_time** |

AAPL の直近1,000 filing のうち **86件（8.6%）で `acceptanceDateTime` の日付と
`filingDate` が一致しない**。しかも両方向にずれる。

```
10-Q      accepted 2024-08-01 22:03:34  -> filingDate 2024-08-02   (翌日)
4         accepted 2023-10-04 01:09:17  -> filingDate 2023-10-03   (前日)
```

**`filingDate` を availability time として使ってはいけない。**
なお `acceptanceDateTime` は `Z` 接尾辞を持つが実際のタイムゾーン規約は一次資料で
要確認（本スパイクでは未確定）。

### 罠: frames API は point-in-time ではない

`companyfacts` は同一 (concept, start, end) を**複数の vintage** で保持する。AAPL 集計:

| 指標 | 値 |
|---|---:|
| us-gaap concepts | 503 |
| concept-unit series | 506 |
| facts 総数 | 25,046 |
| distinct (start, end) 期間 | 12,366 |
| **2回以上報告された期間** | **7,139 (57.7%)** |
| **値が異なる期間（restatement）** | **426 (3.4%)** |

`AccountsPayableCurrent` の 2017-09-30:

```
filed 2017-11-03  10-K   49,049,000,000   <- 当時公開された値
filed 2018-02-02  10-Q   49,049,000,000
filed 2018-05-02  10-Q   49,049,000,000
filed 2018-08-01  10-Q   49,049,000,000
filed 2018-11-05  10-K   44,242,000,000   <- 修正後
```

ここで **frames API** に `CY2017Q3I` を問い合わせると:

```
{'accn': '0000320193-18-000145', 'cik': 320193, 'end': '2017-09-30', 'val': 44242000000}
```

返るのは **2018-11-05 提出の修正値**（accn が一致）。つまり
**frames API は期末の13か月後に確定した値を、期末時点の断面として返す。**
差は 4,807 百万ドル（−9.8%）。

符号が反転する例もある — `AccumulatedOtherComprehensiveIncomeLossNetOfTax` の 2008-09-27 は
`+8,000,000`（filed 2009-10-27）→ `-9,000,000`（filed 2010-01-25、10-K/A）。

**断面研究で frames API を使うと、検出不能な look-ahead が入る。**
point-in-time には `companyfacts` を取得し、`filed <= 評価時点` でフィルタする経路しかない。

### Sample

- frames `us-gaap/Assets/USD/CY2023Q4I` = **6,428社**
- `submissions` の `recent` は **1,000件で打ち切り**、それ以前は別ファイルに分割
  （AAPL: recent 1,000 + `CIK0000320193-submissions-001.json` に 1,238件、1994-01-26 以降）

1,000件上限は実装時に見落としやすい。古い企業ほど `files` 配列の追跡が必須。

### 未検証

**Baseline gate 未実施。** SEC 側で単純 baseline（例: 前期値持ち越しで将来 fundamentals を
予測）を走らせていない。計画 §5 の B9 を確定する前に必要。

---

## 3. Stage 2 roadmap への含意

計画 §5 の暫定 roadmap に対する、実測に基づく修正提案。

1. **B5–B8 の Treasury track は開始してよい。** 完全パネルの起点を **2007-01-02** に固定し、
   1990年代を使う場合はテナー導入日を universe 規則として明示する。30Y を含む長期端の
   分析は 2002-02-15..2006-02-09 の空白を明示的に扱う。
2. **B9 の SEC track は `companyfacts` + `filed` フィルタを唯一の経路とする。**
   frames API は「便利だが look-ahead を注入する反例」として教材に載せる価値がある。
   罠として使うのは有益だが、Project の本経路にしてはいけない。
3. **B10 の再現パッケージ課題に実データがある。** bulk 2.7 GB は再配布不可の規模で、
   downloader + manifest + content hash + local cache が必然になる。作り物でない要件。
4. **`availability_time` の教材例が実データで揃った。** SEC の 8.6% 日付不一致と 3.4%
   restatement は、point-in-time join を「概念」でなく「やらないと数字が変わる」形で
   示せる。
5. **Treasury の取得経路を年次 XML に固定する。** bulk CSV の 403 を前提に downloader を
   設計する。

## 4. 残作業

- SEC 側の Baseline gate 実測
- Treasury の改訂検出（日を空けた再取得による longitudinal 比較）
- `acceptanceDateTime` のタイムゾーン規約を SEC 一次資料で確定
- Binance（Optional C）は未着手。計画上も「選択時のみ」

## 5. 再現手順

```bash
UA='quant-research-textbook feasibility spike <contact>'

# Treasury: 年次 XML（bulk CSV は 403）
curl -A "$UA" "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value=2026"

# SEC: submissions / companyfacts / frames
curl -A "$UA" 'https://data.sec.gov/submissions/CIK0000320193.json'
curl -A "$UA" 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'
curl -A "$UA" 'https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2017Q3I.json'
```

取得済みデータと解析スクリプトは以下に残してある（セッション用の一時領域なので永続しない）。

```
/tmp/claude-1000/-home-kazumasa-projects/318f8fd7-dcfa-49ff-9a45-dcfd382eeef9/scratchpad/spike/
```
