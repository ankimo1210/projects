# Stage 1整合性フォローアップとStage 2実データ優先計画

- 決定日: 2026-08-10（B9 contract revised 2026-08-11）
- 状態: Stage 1整合性修正とStage 2B / B5–B8を実装済み。B9 M6 real-data gateはhistorical PIT cohort・archive join・strict splitを通過し、次はpre-analysis specificationとmodel tournament
- 対象: Stage 1の残存整合性修正、Stage 2（B5–B11）のデータ・テーマ設計

## 結論

Stage 2の実証分析とBlock Projectは、取得可能性と利用条件を確認した**実データを既定**とする。
JGB価格や中央銀行イベントの必要データが確保できない場合、金融らしい合成データで代替せず、
公式データで検証可能なテーマへ変更する。

合成データは廃止しない。解析解との照合、既知の真値を持つsimulation、edge case、property test、
Monte Carloそのものを学ぶ章では引き続き使用する。ただし、合成市場データから実証的な市場・政策の
結論を主張しない。

> 2026-08-10 update: Treasury spikeはgateを通過し、B5–B6を実装した。実測と検証結果は
> [Stage 2A / B5–B6実装ノート](../updates/2026-08-10-stage-2a-b5-b6.md)を参照。
> B7–B8も同じTreasury snapshotとouter testで実装し、複雑な候補がrandom walkを超えない
> `no model selected`を結論とした。詳細は
> [Stage 2B / B7–B8実装ノート](../updates/2026-08-10-stage-2b-b7-b8.md)を参照。
> 独立したEDGAR spikeでAccess・Sample・Teaching fitは通過し、revisionとFrames APIの
> look-aheadを実測した。baseline未実施時点ではavailability contractも未確定だったため、
> SECは5 gate中4 gate相当の条件付き候補としてB9を未着手にした。詳細は
> [Stage 2 Data Feasibility follow-up](../updates/2026-08-10-stage-2-data-feasibility-follow-up.md)を参照。
> 2026-08-11 M6 update: 2016年Q1のexact `10-K`をseedにする固定PIT cohortで、cache integrityを
> 通過した261 CIKから4,631行 / 163 CIKのpanelを再構成した。company×time strict holdoutは
> `n=413`、対応するtraining partitionは2,195行で、事前登録した`n>=200`かつtraining非空の
> gateを通過した。これはB9のmodel選定や母集団への実証結論ではなく、pre-analysis specificationと
> locked model tournamentへ進むためのdata gateである。詳細は
> [SEC B9 baseline gate follow-up](../updates/2026-08-11-sec-baseline-gate.md)を参照。

## 1. Stage 1で先に閉じる整合性項目

原典整合性レビューの最終追記で、次の2件が未対応と確認された。

1. B1/B2のNotebook本文に、4成果物と75点gateが反映されていない。
2. B2 Overviewに、`curriculum_map.yml`で定義したplacement診断6項目がない。

次の4 builderに、B3/B4と同じ規約を最小差分で追加する。

| Builder | 追加内容 |
|---|---|
| `tools/build_nb00.py` | B1の4成果物、配点、75点とExit Criteriaの独立gate |
| `tools/build_nb05.py` | B1 Projectの成果物対応表と提出check |
| `tools/build_nb06.py` | B2 placement診断、4成果物、配点、圧縮しても免除されない要件 |
| `tools/build_nb11.py` | B2 Projectの成果物対応表と提出check |

B2 placementでは、conditional expectation、LLNとCLT、martingale、optional stopping、
Itô lemma、Monte Carlo confidence intervalの構成・診断を確認する。placementは学習時間だけを
変え、成果物、採点、Exit Criteria、再現性・検証要件を免除しない。

### Stage 1修正の受入条件

- 対象4 builderと生成Notebookのsourceが一致する。
- 対象4冊を上から実行し、error outputがない。
- `tools/build_notebooks.py --check` が24冊すべてで通る。
- `analytics/quant_research/tests` がすべて通る。
- Jupyter Bookを`-W --keep-going`でbuildし、warningがない。
- README、`curriculum_map.yml`、Notebook本文の評価・placement規約が一致する。

## 2. Stage 1の合成Projectの位置づけ

完成済みのStage 1を、直ちに別データで全面再実装しない。既存Projectは次の**方法検証lab**として
位置づけ、実証研究と区別する。

| 現在のProject | 教材上の位置づけ | 主張しないこと |
|---|---|---|
| JGB Curve Fitter v0 | Discount Curve Numerical Lab | 実JGB市場への適合、取引可能性 |
| BOJ Announcement Study | Announcement-Study Methodology Lab | BOJ政策の実証結果、因果効果 |
| Constrained Curve Fitter | Constrained Optimization Lab | 実市場での汎化、流動性改善 |

B2のMonte Carloはsimulation自体が対象なので、この制限とは矛盾しない。Stage 1のtitleやTOCを
変更する必要性は、Stage 2のデータspike後に別途判断する。

## 3. Stage 2のデータ原則

### 実証Projectで必須とする記録

- 公式source URLとdataset名
- 利用条件・再配布条件を確認した日付
- retrieval timestampとcontent hash
- raw schema、単位、timezone、calendar
- `observation_time`と`availability_time`
- revision・correction policy
- 欠損、重複、外れ値、系列改廃の診断
- universe選択規則とsurvivorship biasの監査
- train/validation/test cutoffとleakage check
- raw dataを再配布できない場合のdownloader、manifest、local cache契約

教材HTMLに掲載する結論は、取得済みの固定snapshotと変更履歴を残したlocked evaluationから生成する。
実装時に既に観察したsnapshotへhistorical pre-registrationを遡及して主張しない。
取得不能なデータを、都合のよい合成市場系列で穴埋めしない。

## 4. Phase 2.0 — Data Feasibility Spike

カリキュラム本文やモデルAPIを実装する前に、取得可能性・意味・標本数を小規模に実測する。

### Primary A: U.S. Treasury daily yield curve

公式のDaily Treasury RatesとXML feedを候補とする。

- [Daily Treasury Par Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?page=1&type=daily_treasury_yield_curve)
- [Treasury Daily Interest Rate XML Feed](https://home.treasury.gov/treasury-daily-interest-rate-xml-feed)

spikeでは、tenorの開始・終了、欠損、休場日、系列定義、改訂、安定して使える履歴期間を確認する。
これは日次の公表curveであり、bid/ask、出来高、約定、intraday executionを表さない。そのため
予測・期間構造・risk analysisには使うが、流動性や取引収益の証拠とはしない。

### Primary B: SEC EDGAR filings and XBRL

公式のfiling submissions、XBRL company facts、bulk archiveを候補とする。

- [SEC EDGAR Application Programming Interfaces](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

spikeでは、filing acceptance time、amendment、taxonomy差、同一factの重複、企業・年度ごとの利用可能な
target数を確認する。現在の指数構成銘柄を遡及適用せず、時点整合したuniverse規則を使う。

2026-08-10の独立spikeでは、Submissions、Company Facts、Framesの取得、AAPLの複数vintage、
6,428社のAssets frameを実測した。Framesは各periodでlast-filed factを返すため、B9の分析経路には使わない。
Company Factsの`accn`をSubmissionsへ結合し、timezone付き`acceptanceDateTime`を保持する。SECは公開遅延を
保証しないため、日次Core分析では受理日の**次の営業日**から利用可能とする保守的規則を既定にする。
`filed`単独を正確なavailability timestampとはみなさない。

### Optional C: intraday market track

intraday・market microstructureを扱う場合だけ、公開trade/bar archiveを持つ暗号資産市場を候補にする。

- [Binance Public Data](https://github.com/binance/binance-public-data/blob/master/README.md)

klines、trades、aggregated trades、checksum、訂正履歴を確認する。exchange固有dataであり、単純archiveを
full limit-order-bookと呼ばない。暗号資産を教材の専門trackに採用するかはspike後の明示的な判断事項とする。

### Defaultから外すsource

- FRED/ALFREDは技術的にはvintage管理に有用だが、現行Terms of UseのML/AI利用制限を解消できない限り
  Core datasetにしない。[FRED Terms of Use](https://fred.stlouisfed.org/legal/terms/)
- JGBの日次constant-maturity yieldは補助比較には使えるが、bond price、bid/ask、volume、intradayの
  代替にはしない。
- BOJ文書は出典・事例として参照できるが、必要なtimestamp・market data・識別情報が揃わない状態で
  Coreの実証Projectにしない。

### Spikeのdecision gate

| Gate | 通過条件 |
|---|---|
| Access | 自動取得を再現でき、利用条件と再配布境界を記録できる |
| Semantics | 単位、時点、改訂、targetの意味を説明できる |
| Sample | 時系列・企業groupを保ったholdoutに十分な有効標本がある |
| Baseline | 単純baselineを実行でき、metricと失敗条件を固定できる |
| Teaching fit | 数学、実装、実験、memoの4成果物へ自然に接続できる |

1つでも通らないsourceは、合成データで補わず候補から外す。

## 5. Stage 2暫定roadmap

データspikeに合格した場合の第一候補は次のとおり。

| Block | 暫定Project | 実データ | 主な検証 |
|---|---|---|---|
| B5 | Daily Treasury Curve Forecasting Baseline | Treasury daily curve | no-change/AR/ridge、expanding window、regime別誤差 |
| B6 | Treasury Forecast Model Tournament | B5と同一snapshot | nested temporal validation、calibration、計算予算 |
| B7 | Dynamic Treasury Curve Forecasting Audit（実装済み） | Treasury daily curve | factor/state-space、filtered vs smoothed、multi-step forecast |
| B8 | Treasury Predictive Uncertainty and Latent-State Audit（実装済み） | Treasury factors | prior/posterior predictive check、coverage、latent-state境界 |
| B9 | SEC Filing Change & Fundamentals Forecast | Company Facts + Submissions | numeric-only/TF-IDF baseline、`accn` PIT join、企業・時間split、future fundamentals |
| B10 | Reproducible Public-Data Research Package | B7またはB9 | downloader、cache、availability time、schema、offline fixture |
| B11 | Rates research またはoptional intraday track | Treasury/SEC、選択時のみ公開trade data | pre-analysis plan、cost/claim boundary、replication package |

B5/B6ではMLPをAdvancedに置き、単純baselineと同じouter testで比較する。B9は価格dataを別途
適法に確保できない限りabnormal returnをtargetにせず、将来のXBRL fundamentalsなどEDGAR内で
時点整合して構築できるoutcomeを使う。

### B7–B8のデータ・評価契約

- CoreはB5–B6と同じ2015-01-02–2025-12-31の固定snapshotとouter testを再利用する。
- 2007–2025の完全5テナーパネルは、別version・別manifestのAdvanced historical robustnessに限定する。
  2007–2014をmodel/hyperparameter選択へ戻さず、B5–B6の結果も遡及変更しない。
- B7のprimary taskは5公表日先のlevel / slope / curvatureまたはcurve変化の予測とし、random walkと
  last filtered stateをbaselineにする。予測時点ではfiltered stateだけを使い、smoothed stateは事後診断に限定する。
- B8は同じtargetについてBayesian posterior predictiveとHMM parameter-conditional predictiveを区別し、
  RMSE・MAEとinterval coverage・widthを分離する。
- 1公表日・20公表日のhorizonはsecondaryとし、primary結果を見てから入れ替えない。

## 6. 実装順序

1. Stage 1のB1/B2評価・placement漏れを修正する。**完了**
2. READMEとProject本文で、Stage 1の合成Projectを方法検証labとして明記する。**完了**
3. TreasuryのData Feasibility Spikeを実行する。**完了**
4. Treasuryのaccess・semantics・schema・sample・baseline reportを作る。**完了**
5. gate通過結果に基づいてB5–B6のtarget、split、metric、dependencyを確定する。**完了**
6. `curriculum_map.yml`へB5–B6を追加し、12章と共通libraryを実装する。**完了**
7. SECのAccess・Semantics・Sample・Teaching fit spikeを実行する。**完了。ただしavailability contractを保守的規則へ限定**
8. `curriculum_map.yml`へB7–B8を追加し、12章と共通libraryを同じTreasury contractで実装する。**完了**
9. B7/B8 outer testのnegative result、filtered-only、uncertainty contractを更新ノートへ固定する。**完了**
10. B9着手前にSECの単純baseline、metric、企業・時間holdout、失敗条件を固定して実行する。**完了。M6 strict both holdout `n=413`、training 2,195行でgate通過**
11. B9着手前に`filings.files`を含む`accn` join、fixed-anchor PIT cohort、calendar manifest、
    cache fetcherを実装する。**完了。batch cache integrity、archive allowlist、holiday manifest、
    offline panel builder、derived artifact、raw SEC payloadを再読しないdetached audit、PIT/grain/split fixtureを含む**

12. 実SEC cacheを固定anchor cohortへbatch取得し、`tools/build_b9_panel.py`でoffline artifactを生成する。
    source terms、retrieval、content hash、CIK数、欠損・重複・PIT・split gateを監査し、strict gateを満たす場合のみ
    B9 Notebook本文とmodel tournamentを開始する。**完了。300 requested / 261 cache success / 163 panel CIK、
    4,631 rows、strict both `n=413`をartifactと、raw cacheを再読しないdetached auditで固定**

13. B9 の estimand、feature availability、text retrieval scope、candidate set、locked evaluationを
    pre-registerする。**完了。[B9 pre-analysis specification](2026-08-11-b9-preanalysis.md)に固定**

14. M6 target rowを変えずにprevious filing provenanceをmaterializeし、staging / retry / atomic publishを
    持つtext downloader、retrieval manifest、coverage・duplicate-family・target-text exclusion auditを
    実装する。gate通過後にB9 Notebook本文とmodel tournamentを開始する。**sidecar・downloader・raw
    integrity audit、visible-text正規化、normalized duplicate auditは実装済み。実文書取得と90% coverage /
    normalized duplicate gateの実行が次。**

## 7. 未決事項

- B11を日次rates研究に統一するか、実intraday dataを使う選択trackを設けるか。
- Stage 1のNotebook title/filenameからJGB・BOJを将来外すか、方法検証labという注記だけに留めるか。
- 実データsnapshotをrepositoryで再配布できるか、manifestとdownloaderだけを追跡するか。
- SEC B9のdynamic historical universeは未確定。v1 Coreのfixed-anchor cohort（2015-12-31 / 2016-04-01 / Assets ≥ $100M）を先に検証し、dynamic版はAdvancedへ分離する。

これらは推測で決めず、Phase 2.0の取得・利用条件・標本診断を見て確定する。
