# 2026-08-10 — Stage 2 Data Feasibility follow-up

## 結論

独立に取得したU.S. TreasuryとSEC EDGARのbounded sampleを再計算し、Stage 2の実データ方針へ反映した。
TreasuryはB5–B8の日次rates教材に使用できる。SECはAccess・Sample・Teaching fitを満たし、
revisionとFrames APIのlook-aheadも実測できたが、**Baselineが未実施**なので5 gate通過とはしない。
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

### B9で固定するPIT contract

1. Company Factsの各factを`accn`でSubmissionsへ結合する。
2. rawの`acceptanceDateTime`とtimezone解釈を保持する。
3. SECはfiling acceptanceから公開までのlagを保証しないため、日次Coreでは**受理日の次の営業日**から
   利用可能とする。`filed`単独をavailability timestampとは呼ばない。
4. 評価時点以前に利用可能なvintageだけを残す。amendmentやlater filingで書き換えない。
5. Framesはlook-ahead反例とcross-sectional sample診断に限定する。
6. 現在の指数構成銘柄を過去へ遡及適用しない。企業universeはfiling時点の情報で定義する。
7. downloaderは申告済みUser-Agent、SECのrate limit、local cache、content hashを必須にする。

## Gate判定

| Gate | Treasury | SEC |
|---|---|---|
| Access | pass | pass |
| Semantics | pass | conditional pass。保守的availability規則を採用 |
| Sample | pass | pass |
| Baseline | pass | **incomplete** |
| Teaching fit | pass | pass |

したがって、TreasuryはB7–B8へ進める。SECは「5 gate通過」ではなく、B9候補を維持するための
4/5 gate相当の結果である。

## B9前の残作業

- primary fundamental targetとpoint-in-time企業universeを固定する。
- 前期値持ち越し等のnumeric-only baselineを、企業・時間holdoutで実行する。
- metric、失敗条件、missing taxonomy、amendment処理を固定する。
- downloader/cacheを小規模fixtureでtestし、bulk archiveをrepositoryへ置かない。
- 利用条件と再配布境界をB9のmanifestで再確認する。

これらが完了するまでB9のNotebook本文やmodel tournamentは実装しない。
