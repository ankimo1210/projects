# 2026-08-10 — Stage 2 Data Feasibility follow-up

## 結論

独立に取得したU.S. TreasuryとSEC EDGARのbounded sampleを再計算し、Stage 2の実データ方針へ反映した。
TreasuryはB5–B8の日次rates教材に使用できる。SECはAccess・Semantics・Teaching fitを満たし、
revisionとFrames APIのlook-aheadも実測できた。後続のbounded baselineで単純比較は実行できたが、
strict company×time splitの標本数とarchive/PIT再構築が未完了なので、**正式な5 gate通過とはしない**。
B9は条件付き候補のまま保留する。

このfollow-upは一時領域のraw dataをsource of truthにしない。再計算コード、source URL、content hash、
集計値、意思決定だけをrepositoryへ残す。大量raw data、SEC bulk archive、個人の連絡先はcommitしない。

## Datasetとgrain

| Source | Bounded sample | Grain | As of |
|---|---|---|---|
| U.S. Treasury annual XML | 1990–2026、37年次file | 公表日 × tenor | 2026-08-07 |
| SEC Submissions | AAPL recent filings | filing / accession number | 2026-08-10取得session |
| SEC Company Facts | AAPL US-GAAP facts | concept × unit × period × vintage | 2026-08-10取得session |
| SEC Frames | Assets CY2023Q4I、AccountsPayableCurrent CY2017Q3I | entity × calendrical frame | 2026-08-10取得session |

公式source:

- [Treasury Daily Interest Rate XML Feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)
- [SEC EDGAR Application Programming Interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
- [SEC Developer Resources / Fair Access](https://www.sec.gov/about/developer-resources)
- [SEC Webmaster FAQ](https://www.sec.gov/about/webmaster-frequently-asked-questions)

## 再計算方法とprovenance

再計算script:

```bash
cd ~/projects
uv run --no-sync python \
  analytics/quant_research/tools/audit_stage2_feasibility.py \
  /path/to/bounded-raw-cache > /tmp/stage2-feasibility-audit.json
```

期待するcache名は`treasury_YYYY.xml`、`sec_aapl_sub.json`、`sec_aapl_facts.json`、
`sec_frame.json`、`sec_frame_2017.json`、`sec_tickers.json`である。scriptはnetworkへ接続せず、
入力を変更しない。

| Artifact | SHA-256 |
|---|---|
| 37 Treasury XML fileの`filename:sha256` manifest | `a3e311425b37249a948a87b430eb168b64ba762e2dc612a9fdd8b6a694929cd4` |
| `sec_aapl_sub.json` | `d0967903f34d70967ff6fdb2e75ef8cf9632b43c557fa38001d8b70945007d74` |
| `sec_aapl_facts.json` | `73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43` |
| `sec_frame.json` | `751a0eb9da96a02319327fe0e31de7c27e16f2b12650418234790d6dff396ba1` |
| `sec_frame_2017.json` | `33d144e1febc9dc6cc04267986654e1c4e4398bc62797ff056a5c7432d71f22a` |
| `sec_tickers.json` | `6dd9c4363c5a95d43f4d8e8f8279f9ae6538d10d295bbdeebe5a433ec954bf6d` |

## Treasury findings

### 品質・shape

| Check | Result | Impact |
|---|---:|---|
| XML entries | 9,157 | 1990-01-02–2026-08-07 |
| Core 5-tenor complete panel | 4,901 | 2007-01-02以降 |
| 30Y gap | 2002-02-15 → 2006-02-09 | 長期端への`ffill`禁止 |
| Display-only phantom row | 2010-10-11、1件 | `BC_30YEARDISPLAY`をactual 30Yとして読まない |
| Missing 3M in Dec-2008 | 3件 | stress期の個別tenor欠損を休場日と混同しない |

tenor universeは時点で変わる。20Yは1993-10-01、1Mは2001-07-31、2Mは2018-10-16、
4Mは2022-10-19、1.5Mは2025-02-18に初出した。後年のtenor集合を1990年へ遡及適用しない。

10Yを時系列70/30に分けたspot checkでは、test 1,470日でno-change RMSEが5.9308 bp、
AR(1)が5.9409 bpだった。AR(1)はno-changeを0.17%改善せず、単純baselineを先に置く設計を支持する。

### 実装への反映

- B5–B6の固定snapshotは2015–2025のまま変更しない。
- XML parserはactual tenorを列挙し、全actual tenorが欠損したrowを除外する。
- 2010-10-11型のphantom rowを小さな回帰fixtureとして保存する。
- B7–B8 Coreも同じ2015–2025 snapshotを使う。
- 2007–2025拡張は別manifestのAdvanced historical robustnessに限定し、model選択へ戻さない。
- revisionは単発取得では測れない。再取得時は年次XML hashの差を保存する。

## SEC findings

### 品質・point-in-time risk

| Check | Result | Impact |
|---|---:|---|
| AAPL recent submissions | 1,000 | 古い履歴は`filings.files`も追う |
| acceptance dateとfiling dateの不一致 | 86件、8.6% | `filingDate`をavailability timestampにしない |
| US-GAAP facts | 25,046 | concept-unit series 506 |
| period groups | 12,366 | 同一periodに複数vintageを保持 |
| repeated period groups | 7,139、57.7% | last observationだけへのcollapse禁止 |
| value-changed period groups | 426、3.4% | revisionをpoint-in-time filterで管理 |
| Assets CY2023Q4I frame | 6,428 entities | sample sizeは有望だがPIT universeではない |

`AccountsPayableCurrent`の2017-09-30について、Company Factsは2017-11-03提出の
49,049,000,000と、2018-11-05提出の44,242,000,000を別vintageとして保持していた。
FramesのCY2017Q3Iは後者を返した。SEC公式仕様もFramesを「last filed」に近いfactを各entityから
集約するAPIと説明しているため、historical point-in-time研究のprimary経路には使わない。

### B9で固定するPIT contract（2026-08-11 revised）

1. Company Factsの各factを`accn`でSubmissionsへ結合する。`recent`だけでは不十分なので、
   `filings.files`の分割archiveを全て追い、未解決accessionはエラーにする。
2. rawの`acceptanceDateTime`とtimezone解釈を保持する。
3. SECはfiling acceptanceから公開までのlagを保証しないため、`America/New_York`へ変換した
   acceptance日と`filingDate`の遅い方を基準に、日次Coreでは**次の米国連邦営業日**から利用可能とする。
   `filed`単独へfallbackしない。holiday manifestまたは使用したcalendar versionを保存する。
4. 評価時点以前に利用可能なvintageだけを残す。amendmentやlater filingで書き換えない。
5. Framesはlook-ahead反例とcross-sectional sample診断に限定する。
6. 現在のFrameや指数構成銘柄を過去へ遡及適用しない。B9 v1 Coreは
   `us-gaap/Assets/USD` の`2015-12-31` anchor factを`2016-04-01`以下で観測でき、
   前四半期Assetsが**1億ドル以上**の固定cohortとし、分析対象はanchor後に限定する。
   dynamic historical universeはarchive再構築後のAdvancedへ分離する。
7. downloaderは申告済みUser-Agent、SECのrate limit、local cache、content hashを必須にする。

## Gate判定

| Gate | Treasury | SEC |
|---|---|---|
| Access | pass | pass |
| Semantics | pass | conditional pass。保守的availability規則を採用 |
| Sample | pass | conditional。bounded sampleは有望だがstrict company×time splitは`n=84` |
| Baseline | pass | provisional。numeric-only baselineは実行可能だがarchiveを含む再取得が必要 |
| Teaching fit | pass | pass |

したがって、TreasuryはB7–B8へ進める。SECは「5 gate通過」ではなく、B9候補を維持するための
条件付き結果である。fixed-anchor cohort、`filings.files` join、strict split `n>=200`、
offline再現性が完了するまでB9本文やmodel tournamentは実装しない。

## B9前の残作業（baseline review反映）

- archiveを含む`accn` joinとfixed-anchor point-in-time企業universeをfixtureで固定する。
- 前期値持ち越し等のnumeric-only baselineを、企業・時間holdoutで実行する。
- primary=MAE、secondary=medAE、reference=RMSE、pooled driftを含むbaseline ladder、
  strict company×time splitの最小標本数`n>=200`を固定する。
- bounded sampleの約150社拡張を実際に行い、strict splitが`n>=200`になることを確認する。
- `America/New_York`と米国連邦holidayのcalendar/versionをmanifestへ保存する。
- metric、失敗条件、missing taxonomy、amendment処理を固定する。
- `tools/fetch_sec_b9_cache.py` と `sec_pit.py` を小規模fixtureでtestし、bulk archiveをrepositoryへ置かない。
- 利用条件と再配布境界をB9のmanifestで再確認する。

これらが完了するまでB9のNotebook本文やmodel tournamentは実装しない。実装した
PIT・metric・split監査の最小部品は`src/quant_textbook/sec_pit.py`にあり、
詳細なgate statusは[SEC B9 baseline gate follow-up](2026-08-11-sec-baseline-gate.md)に記録する。
