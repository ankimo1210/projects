# johnhull：収録内容・実装の深さ・拡張計画・研究検討用資料

- 作成日：2026-09-27（日本時間）
- 対象：`/home/kazumasa/projects/johnhull`
- 確認した最新のプロジェクト関連コミット：`163f7412`（M14のtracked release検証記録）
- 目的：このMarkdown単体をChatGPT等に渡し、既存内容との重複を避けながら、追加できる教材・モデル・研究・検証基盤を検討する。

> **現在は、Hull 11e Global Editionの全37章に対応する教材があり、Beyond Hullを含め30冊のノートブックを収録している。厳密な節単位の受入は306項目中14項目まで進んでいる。次の既定作業はM15・§27.6の数値的バリア評価である。**
>
> 本資料は現状整理であり、新しい実装の承認・着手を意味しない。掲載したテスト結果は既存の実行証跡に基づく。この資料の作成では、ファイル・台帳・コード定義・ノートブックの内容を調べ、価格計算・学習・全テスト・ブラウザ検査は再実行していない。新しい文献の外部検索も行っていない。

## 目次

1. プロジェクトの目的と状態の読み方
2. 規模・構成・利用形態
3. 既存教材の内容：Hull本編と基礎的な深掘り
4. 既存教材の内容：ML・市場構造・新領域
5. 節単位で受入済みの14項目
6. 既定の完了計画と直近の作業
7. 拡張・補完の候補と依存関係
8. 登録済みの研究トラックと構想
9. 残る検証課題・既知の限界
10. データと論文コーパス
11. 実行基盤・再現性・運用上の論点
12. ChatGPTに渡す検討依頼文
13. 根拠資料と読み方
14. 付録A：全306項目の目録と受入状態
15. 付録B：hullkit全73モジュール
16. 付録C：全30ノートブックの実ファイル
17. 付録D：ポータル全12テーマの図数

## 1. プロジェクトの目的と状態の読み方

### 1.1 何を作っているか

John C. Hull『Options, Futures, and Other Derivatives』第11版Global Editionを、日本語の説明、Python計算、対話的な図、独立した数値検証で学べる教材として整備している。さらに、原著の先にある確率解析、Fourier価格付け、XVA、ML、RFR、インフレ連動債、暗号資産、気候・エネルギー等へ広げている。

価格公式を置くだけでなく、前提・単位・測度・近似誤差・境界条件・印刷値との対応を説明し、ノートブック、Jupyter Book、オフラインHTMLポータルへ配布する。近年の追加では、同じ保存データからBookとポータルの図を作り、表示された値まで検証している。

### 1.2 混同してはいけない状態

| 表現 | このプロジェクトで意味すること | そこからは言えないこと |
|---|---|---|
| 章の教材がある／巻が`done` | その章・テーマの説明と所定の実装・配布がある | その章の全節・数値例・実務条件が実装済みとは限らない |
| 公開モジュールがある | `hullkit`から再利用できるコードがある | 全関数が原典の印刷値で独立検証済みとは限らない |
| ノートブック内に計算がある | 教材内の局所関数や計算セルがある | 共有APIとして切り出されているとは限らない |
| 節が`accepted` | 定義した要求について数値・説明・図・配布・証跡の受入を終えた | 市場較正、投資収益、あらゆるパラメータでの精度を保証しない |
| 節が`unreviewed` | 現行の節別受入手順による評価がまだない | 未実装という意味ではない |
| integration/reproducibilityがPASS | 所定の数値恒等式・再現性・成果物間の契約に合格した | 予測モデルがベースラインに勝った、実務運用可能、という意味ではない |
| research trackとして登録 | 比較研究の候補が設定に記載されている | モデル本体の実装・学習・評価が完了しているとは限らない |

**14/306＝約4.6%は節別受入の進捗であり、コード実装率ではない。** 2026-09-14監査では、計算対象243項目のうち107項目に共有コード、54項目にノートブック内の計算があると分類されていた。この内訳は監査当時の分類で、M1–M14後の現行実装率として再利用しない。

## 2. 規模・構成・利用形態

### 2.1 現在の規模

| 対象 | 現在値 | 数え方・注意 |
|---|---:|---|
| Hullの章 | 37 | 全章に教材の収録先がある |
| 節別台帳 | 306 | 本文299節＋付録7項目 |
| 受入状態 | accepted 14／unreviewed 292 | gaps_found・pending_validation・out_of_scopeは各0 |
| 番号付き巻 | 28 | vol 01–28 |
| ノートブック | 30 | 28巻＋旧配置のBSM・金利モデル各1冊 |
| Jupyter Book | 31ページ | ルート＋30ノートブック。ページ数はTOCからの集計 |
| hullkitモジュール | 公開59＋内部14 | `__init__.py`を除く。描画・教材補助も含み、73金融モデルという意味ではない |
| HTMLポータル | 12テーマ・134図 | 現行レジストリとrelease manifest。うちexoticsは34図 |
| 最新の全体テスト記録 | 2,810 passed／6 skipped | M14のhullkit＋report。既存非推奨警告2件 |
| 論文等のローカルPDF | 55資料・1,627ページ | 論文以外に公式コンベンション資料を含む |
| 明示的な研究トラック | 5領域・11候補名 | 既定無効、core gateから独立 |

### 2.2 ディレクトリと責務

| 場所（johnhullからの相対パス） | 役割 |
|---|---|
| `volumes/01_*`〜`volumes/28_*` | テーマごとのノートブックと、巻別の参照データ・検証資料 |
| `notebooks/bsm_chapter15.ipynb` | 第15章BSMの旧配置ノートブック |
| `interest_rate_models/ir_models.ipynb` | 第31–33章の金利モデル比較の旧配置ノートブック |
| `hullkit/src/hullkit/` | 価格、シミュレーション、リスク、曲線、描画等の共有Python実装 |
| `hullkit/tests/`・`report/tests/` | 数値検証、入力・境界検証、成果物契約、表示データ等のテスト |
| `report/` | Jinja2＋PlotlyのオフラインHTMLポータル |
| `book/` | 全巻をまとめるJupyter Bookの設定・入口 |
| `scripts/` | 教材・参照データの生成、独立参照、台帳・release検査、ブラウザ検査 |
| `references/` | 文献目録、ローカルPDF、抽出・検索用コーパス |
| `docs/` | 節別目録・台帳、監査、受入記録、データ由来、設計・計画 |
| `ROADMAP.md` | 現在地、段階別の完了計画、判断待ち事項 |
| `VALIDATION.md` | 時点別の実行結果と限界 |
| `MODEL_INDEX.md` | モジュール・モデル・教材の対応表 |
| `release_manifest.json`・`research_profiles.json` | 配布契約と研究候補の設定 |

### 2.3 隣接プロジェクトとの境界

- **johnhull／hullkit**：金融モデルのteacher、数値的な参照値、制約検査、教材、可視化、配布。`hullkit`はPyTorchに依存しない。
- **deep_hedge_price**：PyTorchの学習、checkpoint、walk-forward評価、学習方策や経済指標の実験。johnhullとは版管理したJSON＋NPZ成果物で連携する。
- **rough_volatility**：重いrough volatility／fBM等の実装を置く先として参照される。
- **optimal_execution**：執行・RLの領域を置く先として参照される。
- **quantkit**：汎用のポートフォリオ・バックテスト・データ接続等を置く先として参照される。

後半3件はjohnhullの既存設計で示された責務分担であり、本資料では隣接リポジトリの現在の内容を監査していない。追加案では「教材・金融teacherをjohnhullに置く」「学習や汎用基盤を適切な隣接プロジェクトに置く」を設計上の論点にする。

## 3. 既存教材の内容：Hull本編と基礎的な深掘り

以下の「今後の境界」は、現在の巻が何を扱っているかと、何まで完成したとは言えないかを示す。個別APIの名前は付録B、全節の正式な目録は付録Aを参照。

### 3.1 vol 01–06：オプション・市場・数値手法

| 巻・原著の主な章 | 収録内容・計算できること | 実装の深さ・今後の境界 |
|---|---|---|
| **01 Foundations**／Ch 13–14 | 1期間・多期間CRR、複製とリスク中立確率、米国型の早期行使、delta、BSMへの収束。指数・通貨・先物への拡張。Markov過程、Brown運動、一般化Wiener過程、Itô・GBM・対数正規分布 | ツリーと確率過程の入口。本文の全表・全ノードの受入は未完了 |
| **02 Options basics**／Ch 10–12・17–18 | オプション市場、価格の上下限、put–call parity、配当・早期行使、価格を動かす要因。元本保証型、spread、butterfly等の組合せ。指数の保険、Garman–Kohlhagen、Black 76、先物オプションのparity | 単一満期のpayoffと価格関係が中心。異なる満期の戦略や契約実務を網羅するエンジンではない |
| **03 Greeks**／Ch 19 | delta・gamma・theta・vega・rho、delta hedgeとstop-loss hedge、ヘッジコスト分布、gamma／vega中立化、theta–gamma関係、synthetic putによる保険 | 学習用シミュレーション。細かい時間刻みでHullのヘッジ表と合わないR11が未再確認 |
| **04 Futures／forwards／rates**／Ch 2–6 | 証拠金、先物市場、basis、最小分散・beta hedge、tailing。複利、債券価格・YTM・par yield、zero bootstrap、forward・FRA、duration・convexity。cost of carry、既知収入・FX・保管費、day count、clean/dirty、conversion factor・CTD、金利先物のヘッジ | 計算の一部はノートブック内。実日付・受渡し制度・OIS反復bootstrap・端数期間等を一貫して扱う実務APIは補完余地がある |
| **05 Volatility smile／estimation**／Ch 20・23 | IV逆算、smile・skew・surface、Breeden–Litzenberger密度、smileを考慮したヘッジ規約。historical volatility、EWMA、GARCHのMLE、分散予測・期間構造、相関 | モデル比較と推定教材。実データの品質管理、残差診断、共分散行列の修復、全面的な市場較正は別課題 |
| **06 Numerical methods**／Ch 21・27 | 二項・三項、control variate、MC分散減少、有限差分、米国型境界、LSM。追加済みの§27.1 CEV／Merton／VG、§27.2確率ボラ、§27.3 Dupire、§27.4転換社債、§27.5経路依存ツリー | §27.1–27.5は受入済み。次は数値的バリア、2資産の相関ツリー、米国型MCの節別受入。現在94セル |

### 3.2 vol 07–12：スワップ・リスク・信用・エキゾチック

| 巻・原著の主な章 | 収録内容・計算できること | 実装の深さ・今後の境界 |
|---|---|---|
| **07 Swaps**／Ch 7・34 | IRS、比較優位、債券差・FRA列による評価、FX swap、OIS／SOFRの説明、非標準スワップの類型、in-arrearsのconvexity、equity・cancelableの概要 | すべての非標準契約を価格付けするわけではない。可変元本・reset・CMS・callableは発展課題 |
| **08 Risk／VaR**／Ch 22 | VaR・ES、coherence、正規法・historical法、期間換算、stress・backtest、オプションのdelta–gammaリスク | 高度なbacktest・EVT・allocationはvol 27へ拡張済み。PCAやcash-flow mapping等の原著細目は受入が残る |
| **09 Credit／XVA**／Ch 9・24・25 | hazard・survival、実確率とリスク中立確率、Merton、copula、CDS、index・CDO、correlation smile、CVA・DVA・WWR等の概念 | 原著数値例の深掘りはvol 28。XVAの説明があることと、担保・ネッティング・WWRを網羅するシミュレーション基盤の完成は別 |
| **10 Exotics／martingales**／Ch 26・28 | digital、8種のbarrier、BGK補正、negative vega、lookback、one-shout、Asian、exchange、basket、variance／volatility swap、静的複製。市場リスク価格、martingale、numeraire、Girsanov | §26.9–26.17の9節を受入済み。Parisian等は説明にとどまる項目がある。§26.1–26.8の未実装商品群が残る。現在125セル |
| **11 IR derivatives market**／Ch 29–30 | Blackの債券オプション・cap/floor・swaption、spot vol stripping、convexity・timing・quanto調整、標準市場モデル間の不整合 | 市場公式と補正が中心。短期金利ツリー／Bermudan／LMMに基づく統一評価は未完成 |
| **12 Qualitative summary**／Ch 1・8・16・35–37 | 市場参加者、金融危機、ABS・CDO、従業員ストックオプション、エネルギーとSchwartz 1因子、real option、失敗事例・流動性・convergence arbitrage | 定性的説明が多いがABS/CDO等の数値計算もある。ESOのvesting・離職・行使行動、実物投資の複数選択肢、重い商品モデルは補完候補 |

### 3.3 旧配置の2冊

- **Ch 15 BSM（66セル）**：GBM、PDE、リスク中立評価、Black–Scholes–Merton公式、配当、IV、warrant／ESO、付録・演習を収録。一部の関数はノートブックの局所定義で、`hullkit`のAPIと同じものとして数えない。
- **Ch 31–33 金利モデル（55セル）**：Vasicek、CIR、Rendleman–Bartter、Ho–Lee、Hull–White、BDT、Black–Karasinski、HJM、BGMの比較と初期曲線への適合を説明する。モデル名が並ぶことは、9モデルすべてに完全なシミュレーション・較正・Bermudanエンジンがあることを意味しない。BGM／LMMの教材にはBlack capletによる説明があり、本格的なforward-rate simulationは今後の範囲。

### 3.4 vol 13–17：基礎から一段深い数理・数値計算

| 巻 | 収録内容 | 注意・発展余地 |
|---|---|---|
| **13 Stochastic calculus** | Brown運動の二次変分、Itô積分とisometry、Stratonovichとの関係、Itôの補題、Euler–Maruyama、Girsanov、Feynman–Kac、martingale representationと市場完備性 | 強／弱収束率の実測、Milstein、高次・多次元scheme等は補完候補 |
| **14 Stochastic volatility／Fourier** | Hestonの特性関数、COSによる密度・価格、smile、SABR Hagan近似、相関・vol-of-volに対するモデル感応度 | Hestonの完全な公開較正APIや全域の近似誤差保証とは別。§27.2で独立数値検証を追加済み |
| **15 Advanced numerics** | control variate、importance sampling、Sobol QMC、LSM、有限差分の安定性・Crank–Nicolson、pathwise／likelihood-ratio／bumpによるGreeks | `aad.py`という名前でもreverse-modeのadjoint tapeを実装したAADエンジンではない。RQMCの独立scrambleによるCIやLSM上界も発展余地 |
| **16 XVA／credit** | exposure、EE・PFE、CVA・DVA・FVA、copula、tail dependenceの説明、Vasicekの大規模ポートフォリオ損失 | 教育用の期待値・簡略化した枠組み。フルCSA、WWR、MVA/KVA等を含む実務XVA基盤ではない |
| **17 Capstone** | 価格計算→測度・モデル→数値効率→Greeks→CVAの接続、vol-of-volを0にする極限比較 | 部分ごとにHestonとGBMが混在する。全段階を同一Hestonモデルで整合させたend-to-end評価の完成とは言えない |

## 4. 既存教材の内容：ML・市場構造・新領域

vol 18–28は、版管理されたJSON／NPZを読み込む**artifact-only教材**である。ノートブックの実行時に学習、外部データ取得、GPU検出は行わない。保存結果の教材化と、学習・生成エンジンの実行を分けている。配布用の実験は小型のCPU quick profileが基本で、大規模な学習・探索を尽くしたモデル間の性能比較とは区別する。

### 4.1 vol 18：MLによる価格・Greeksの代理モデル

- **扱うもの**：解析BSMを基準にしたprice-only MLP、価格＋Greek headsのmultitask、Differential ML、残差学習の教材。MCの標準誤差・信頼区間、ハードな裁定制約とsoft penaltyの違い。
- **比較するもの**：価格／deltaの誤差、誤差面、latency、学習領域内とOODの差、制約違反。
- **現在の読み方**：学習モデルが解析式より有用とは承認されていない。OODでの劣化、強いベースラインに勝てない例、学習費用を回収するbreak-evenが示せない例を含む。OODの結果保存に関する旧R7は対応済み。
- **次の余地**：time-value residual等の比較を揃える、soft penaltyの重みを比較する、安価な解析式ではなく高コストteacherを使った費用対効果を測る。

### 4.2 vol 19：逆問題・ボラティリティ面

- **扱うもの**：Heston COS、SABR Hagan、rBergomiのteacher、SSVI、コール価格の凸性修復、multi-start較正、direct inverseのablation、IVとvarianceを同時に合わせるPareto比較。
- **現在の読み方**：現行の基準較正にはteacherを直接使う部分があり、「学習したforward surrogateを使う較正器」が全面的に実現したとは言えない。識別可能性と観測ノイズの問題は残る。
- **次の余地**：forward surrogateとdirect inverseの同条件比較、パラメータ回復・不確実性、noisy quote下の安定性。rBergomiの離散補償項R1を先に再確認する。

### 4.3 vol 20：surface dynamicsと予測・ヘッジ

- **扱うもの**：purged walk-forward、trainだけでfitするscaler／PCA、persistence、EWMA、GARCH、Log-HAR、PCA-ridge。HARNet、TCN、LSTM、Transformerをchallengerとして比較する構成。
- **評価**：QLIKE・RMSE・MAE、block bootstrap、診断的なfeature importance、ヘッジP&L・CVaR・turnoverの教材。
- **現在の読み方**：surface全体のlatent dynamics予測は完成していない。Phase 1の方策には`not_evaluated`があり、全モデルを同条件で比較した経済価値の立証は未完了。
- **次の余地**：Log-HARの再変換バイアスR2、予測でパスとヘッジの両方を作るR3を再確認する。共通の実現経路に各予測・方策を適用し、予測誤差がP&Lへ伝わる評価にする。

### 4.4 vol 21：SPX／VIXの同時モデル

- **扱うもの**：4因子PDV、AFV、rough Heston kernel、quintic OUの二乗による分散、SPXとVIXのjoint objective、nested MCのVIX teacher、二次surrogate、OOD・Greeks・latency。
- **現在の読み方**：合成ターゲットに対する目的関数の評価が中心で、実市場のSPX／VIX同時較正の達成を意味しない。代理モデルの悪い振る舞いをhard checkで見えるようにした点も成果。
- **次の余地**：合成パラメータの回復、モデル間比較、VIX nested MC誤差の分離、制約を満たすsurrogate。signature／perturbed optimal transportは研究候補。

### 4.5 vol 22：0DTEと日中リスク

- **扱うもの**：timezone・営業session・holiday・settlement、variance clock、予定イベント分散、日中jump、SV＋jump teacher、隣接満期との整合性、時間帯別の価格・誤差。
- **現在の読み方**：イベント分散の注入等の旧指摘は修正済み。Poisson乱数消費による共通乱数の対応崩れR4は未再確認。
- **次の余地**：乱数streamを分離した差分推定、イベント前後のOOD、短時間境界、DML／PIDE surrogate。dealer flowからの因果効果を立証した教材ではない。

### 4.6 vol 23：RFR／post-LIBOR

- **扱うもの**：lookback・lockout・observation shift、advance／arrears、日次複利、複数curveとbasis、政策金利jump、担保、先物convexity、Bachelierのquadrature／MC、normal／shifted SABR、Bartlett deltaとsticky-strike。
- **現在の読み方**：`free_boundary`を含む関数名があっても、現在は外生shiftによる補助であり、Antonov型の内生境界を持つ完全なfree-boundary SABRではない。Hagan近似のbias診断も扱う。
- **次の余地**：実日付とstub、厳密なconvention fixture、完全なfree-boundaryモデル、RFR市場のsmile較正、XVAへの接続。

### 4.7 vol 24：暗号資産の市場構造

- **扱うもの**：linear・inverse・quanto perpetual、index／mark／last、funding capと資金移転の保存、証拠金・bankruptcy、oracle risk、insurance fund・ADL・socialized loss。CPMM／concentrated liquidityとLVR・fee。
- **現在の読み方**：liquidation cascadeは単一口座の終端closeoutによる簡略化。dynamic fee比較はgross LVRが構成上同じになるR6が未再確認。
- **次の余地**：複数口座と価格impactの連鎖、feeを含む裁定終点、oracle遅延、fundingと清算の相互作用。perpetualの無限期間モデルやtoken optionは構想段階。

### 4.8 vol 25：気候・エネルギー

- **扱うもの**：carbonのBlack 76、GBM／SV／SV-jump、risk premium。気温の季節性・OU・fractional OU、HDD／CDD、station basis。固定pay-as-produced・floor・collarのPPA、価値・CFaR・CVaR・ヘッジ残差、発電量と価格の相関感応度。
- **現在の読み方**：不完備市場でどのrisk premiumを使うかが価格に効く。合成入力によるモデル比較で、実際の発電資産の評価・運用性能は検証していない。
- **次の余地**：storage real option、swing、複数因子の商品curve、気温・価格・発電量の共同モデル、実データを用いたbasis risk。

### 4.9 vol 26：インフレ連動金利とJGBi

- **扱うもの**：名目／実質curve、Hull–White 1因子の厳密OU遷移・初期curve fit・ZCB・債券オプション・Jamshidian swaption・較正。
- **インフレ部分**：CPI fixing／forecast、3か月lag、rebasing、決定論的月次季節性、ZC inflation swap、YoY、Jarrow–Yildirimの名目支払forward測度・quanto。
- **JGBi部分**：10日基準の指数補間、丸め、cash flow、settlement、real clean price／yield、償還元本だけにかかるdeflation floorの解析／MC、floorを含むBEI、PV01・CPI delta。
- **次の余地**：G2++／Bermudan、インフレcap/floorとYoY smile、確率的季節性、実際の市場・日付規約を使った較正。旧保存値依存3項目は2026-09-25に配列からの再計算へ移行済み。

### 4.10 vol 27：VaR／ESのリスクデスク

- **扱うもの**：Kupiec POF、Christoffersen独立性／conditional coverage、250日Basel traffic lightと乗数、検定のsize study。HS／FHS、EVTのGPD peaks-over-threshold、mean excess。
- **デスク部分**：Euler型のmarginal／component／incremental VaR・ES、delta–gamma–vega P&L explain、指数call・株式put・IRSのfull repricing、limit判定とdesk report。
- **次の余地**：多変量EVT、cross gamma・vanna・vommaを含むP&L explain、より広い商品とfactor mapping。FRTB IMAはvol 29の候補で、まだ収録されていない。

### 4.11 vol 28：信用デスク

- **扱うもの**：債券／CDSからのhazard bootstrap、CDS premium／protection leg・MTM・binary、固定couponとupfront、forward CDS、Blackのknock-out CDS option。
- **ポートフォリオ部分**：k-th-to-default、synthetic CDO、compound／base correlation、double-t・不均質ポートフォリオの再帰、CreditMetrics MC、netting・collateralとCVA。
- **資料**：Hullの数値例を固定するほか、S&P rating migration matrixやiTraxxの原典例の転記を用いる。すべてを架空市場データと一括りにしない。
- **明示的な除外**：KMV EDF、random recovery／loading、implied copula、dynamic credit、非knock-out CDS optionのfront-end protection等。多くの計算が実装済みでも、Ch 24–25の節別台帳はまだ未評価。

## 5. 節単位で受入済みの14項目

現行台帳の`accepted`は下表だけである。数値は各受入資料から抜粋した代表例で、誤差上限は検査した合成条件における実測値。単位が「価格」のものは各例の通貨単位、SEはMonte Carlo標準誤差を表す。

| M | 節・題材 | 受入で押さえた主な内容・数値 |
|---|---|---|
| M1 | §26.9 Barrier | 8種のin/out、touch、満期条件、negative vega、BGK。独立bridge積分48価格等で照合 |
| M2 | §26.10 Binary | cash-or-nothing／asset-or-nothing、call／put、複製・極限・Greeks、共有4図 |
| M3 | §26.11 Lookback | floating／fixedのcall／put、履歴極値、独立極値尾部積分128価格。`r≈q`は既存APIの未対応領域 |
| M4 | §26.12 Shout | one-shout callの分解・CRR判断・境界・比較。独立42価格、採用1024段の最大残差約0.003793。putは原著外の拡張 |
| M5 | §26.13 Asian | 離散平均の厳密モーメント、既発契約、平均行使価格。Example 26.3の5.62、12／52／250回平均の6.00／5.70／5.63。モーメント整合は近似 |
| M6 | §26.14 Exchange | Margrabe、独立積分・MC、better／worse・sumの関係、米国型の比率ツリー。独立24価格 |
| M7 | §26.15 Basket | 厳密モーメントとlognormal近似を区別。独立72価格。参照価格0.5以上の63行で相対近似誤差−1.9361%〜＋66.8378% |
| M8 | §26.16 Volatility／variance swaps | OTM option strip、variance notional、CIR-LaplaceとMC、VIX。Example 26.4のfair variance約0.0621・価値1.69、26.5のvol約0.2484・価値1.82 |
| M9 | §26.17 Static replication | up-and-out callの満期の異なるcall ladder。3／18／100点で0.730293／0.377569／0.324861、独立吸収境界価格0.313571。節点間に残差が残る |
| M10 | §27.1 Alternative models | CEV、Merton jump diffusion、Variance Gamma。Table 27.1／Figure 27.1、独立PDE・積分で照合 |
| M11 | §27.2 Stochastic volatility | 時間平均分散0.065・25.5%、Hull–White混合公式、Heston COSと独立積分、SABR近似の独立転記・MC |
| M12 | §27.3 IVF／Dupire | 独立解析式33点とlocal vol差最大5.46e-7。独立PDEの9コール価格で最大差0.00405。同じ欧州価格面でも二時点同時確率が異なる実験 |
| M13 | §27.4 Convertible bonds | default・recovery、call後の再転換、coupon。Example 27.1の10節点、初期値107.4418504343806→印刷107.44 |
| M14 | §27.5 Path-dependent derivatives | 算術平均CRRの代表状態と補間。20段×4平均で欧州7.17／米国7.77、60段×100平均で5.58／6.17。小規模全経路列挙10価格との差最大0.00048 |

### 5.1 現在の受入で重視していること

1. 原典の式・印刷値・例・図と、実装した範囲を結び付ける。
2. 公開実装と同じ関数を呼ぶだけの「参照値」を避け、別の積分・PDE・列挙・再帰等で比較する。
3. 解析的恒等式、境界・極限、有限格子の収束、MC標本誤差を区別する。
4. 価格だけでなく説明・保存出力・図の数値・操作状態を確認する。
5. Book／portalで表示を検査し、意図的な数値改変が検出されるかも試す。
6. 影響する既受入節を再検査し、過去の証跡は残す。

これが今後の標準的な品質目標である。ただし、定性節も同じ画面検査量にするかは未決定。

## 6. 既定の完了計画と直近の作業

### 6.1 完了条件

`ROADMAP.md`で定めた完了は、(1) 全306項目が`accepted`または判断を記録した`out_of_scope`になり、(2) 監査の残りP8が対応済み、または判断を記録済みになること。新テーマを無制限に追加することは、この完了条件には含まれない。

| 段階 | 範囲 | 項目数 | 受入済み | うち定性 | 現在の位置付け |
|---|---|---:|---:|---:|---|
| P0 | §26.9–§27.4、M1–M13 | 13 | 13 | 0 | 完了 |
| P1 | §27.5–§27.8 | 4 | 1 | 0 | 進行中。M14完了、次はM15 |
| P2 | §26.1–§26.8 | 8 | 0 | 0 | perpetual・Bermudan・forward start・cliquet・compound・chooser等 |
| P3 | Ch 28–34 | 37 | 0 | 3 | 金利モデル・金利商品。HW／BK tree、Bermudan、LMMが重い |
| P4 | Ch 10–21 | 112 | 0 | 19 | オプション中核。既存実装の印刷値・原典による固定が多い |
| P5 | Ch 22–25 | 36 | 0 | 4 | リスク・信用。vol 27・28を再利用可能 |
| P6 | Ch 1–9 | 80 | 0 | 31 | 市場・先物・金利・スワップの基礎 |
| P7 | Ch 35–37 | 16 | 0 | 6 | 商品・real option・失敗事例。原典に必要パラメータのない例もある |
| P8 | 監査・検証基盤の残り | 別枠 | — | — | R1–R4・R6・R11、保存値依存5項目、設計判断 |
| 合計 | P0–P7 | 306 | 14 | 63 | 未評価292 |

定性63は既存監査の分類であり、新規開発が必要な機能数ではない。

### 6.2 次の3節の具体像

- **M15・§27.6 Barrier Options**：解析バリアを扱った§26.9から、数値ツリーにおけるバリア位置・収束・Adaptive Mesh Methodへ進む。ここでのAMMはAdaptive Mesh Methodで、vol 24のAutomated Market Makerとは別。
- **§27.7 Options on Two Correlated Assets**：2資産の相関を組み込むツリー、Table 27.2／27.3等との対応。vol 10のexchange／basketの既存解析・近似・MCを比較基準にできる。
- **§27.8 Monte Carlo Simulation and American Options**：既存LSMを原典の小規模経路例、回帰・行使判断・価格まで固定する。8経路例の0.1144や境界による例の丸め差を整理し、上界評価は必要範囲を決める。

後半2節のマイルストーン番号や追加上界法の実装範囲は、本資料で新たに確定していない。

### 6.3 開発再開前に判断する事項

| ROADMAPのID | 判断 | 状態と影響 |
|---|---|---|
| D1 | 既受入節の再撮影・証跡をどこまで増やすか | 未決定。M13時点で1回約13MB。従来方式を306項目へ外挿した約45GBは概算で、実測総容量や確定予測ではない。共有ソースの影響範囲で絞る、画像の重複を避ける等が候補 |
| D2 | 後続節追加で昔のnotebook基点検査が落ちる問題 | **M14で対応済み**。現行HEAD用に節の範囲を受入commitと比較する検査を追加。昔の受入時点検査は履歴として保持 |
| D3 | 定性節・実装済み節の受入を軽くまとめるか | 未決定。定性節の本文照合経路、章単位の一括受入等が候補。古い「残り293」の日程概算は現在の292項目に対する新見積りではなく、確約しない |

## 7. 拡張・補完の候補と依存関係

### 7.1 分類

- **既定計画**：Hullの節別完了計画に含まれる。新テーマの提案として重複計上しない。
- **既存の発展候補**：監査・設計・ノートブックの限界欄で挙がっているが、着手順・詳細仕様は未確定。
- **評価の修復**：モデルを増やす前に、比較・参照・データの妥当性を直す仕事。
- **研究候補**：成功や採用を約束しない比較研究。coreへ入れるには昇格条件がある。

以下は既存資料の残課題を、検討しやすい粒度にまとめ直したもの。「検証の焦点」は本資料で整理した進め方であり、新たな承認済み仕様ではない。

### 7.2 Hull本編の補完

| 領域 | 追加・深化する内容 | 既存の土台／依存 | 検証の焦点・区分 |
|---|---|---|---|
| 市場・curve・先物 | OIS zero curveの反復bootstrap、実日付・day count、T-bill、32nds、conversion factor・CTD・受渡し、SOFR stub／月平均、stack-and-roll | vol 04、`rates`、`rfr` | 原典表とcalendar fixture。既定計画内の補完。一部は既にnb計算がありAPI化・受入が中心 |
| ヘッジ・BSM | 印刷ヘッジ表、配当を含む一貫したhedge simulation、複数満期戦略、満期／ゼロvol時のGreek規約 | vol 01–03、legacy BSM、`bsm`・`hedging`・`payoffs` | 金利・割引・配当規約を揃える。R11の原因切り分けが先。現在ValueErrorになる境界をどう扱うかは設計判断 |
| ESO | vesting、離職、行使倍率・行使行動を持つtree | vol 12、`trees` | 標準Americanとの極限、cash flowと失効の独立再帰。既定計画 |
| 数値ツリー・FD | 時間依存tree、cash dividend／S*調整、trinomialの再利用API、S格子FD・PSOR、barrierのadaptive mesh | vol 06、`trees`・`fd`・`fd_advanced` | 原典値・解析価格への収束、単調性、early exercise条件。既存機能と照合して不足だけ補う |
| American MC | LSMの原典経路例・行使判断、out-of-sample policy、Andersen–Broadie型上界 | vol 06・15、`mc_advanced` | 学習と評価経路の分離、下界と上界、CI。§27.8が既定、上界の深さは候補 |
| 初期エキゾチック | perpetual American、Bermudan、forward start、cliquet、Geske compound、chooser | vol 10、BSM・tree・MC | 解析極限・独立積分・契約分解。P2。Asian／basket／shoutを未実装として再提案しない |
| 金利の基礎モデル | Vasicek・CIR・Rendleman–Bartterの共有API化、実確率の推定とリスク中立較正の区別 | legacy金利、`hull_white`・`rates` | 初期curve fitとoption calibrationを混同しない。多因子Vasicek／HW2F／G2++は発展候補 |
| 金利treeとBermudan | HW／BK trinomial、American bond option、時間依存volの較正、Bermudan swaption | curve・HW1F→tree→行使→較正 | P3の主要依存列。ZCB再現、Jamshidianとの比較、収束、行使境界 |
| HJM／LMM | forward-rate simulation、measure・drift、cap／swaption較正、Rebonato・PCA、ratchet／sticky／flexi、MBS・OAS | 金利curve・市場公式・較正基盤 | P3。HJM/BGMの見出しがあるだけで実装済みとしない。高い計算費用と原典外の深掘り範囲を先に決める |
| 非標準スワップ | 可変元本、複利、cross-currency、equity reset、CMS・timing・quanto、accrual・cancelable | `swaps`・`ir_options`、金利tree | 単純契約への還元、日付・支払通貨・測度。cancelableはtreeに依存 |
| 推定とリスク | variance targeting、EWMA推定、Ljung–Box、PSD、vector IV、VaR quantile規約、cash-flow mapping、cross gamma・Cornish–Fisher・PCA | vol 05・08・27、`volatility`・`risk` | 学習期間と評価期間の分離、統計量の再計算、factor mapping |
| 信用・XVA | cure period、incremental CVA、WWR、MVA/KVA/FCA/FBA、tranche補間、random recovery／loading、implied copula、dynamic credit | vol 09・16・28、信用curve・portfolio・XVA | 既存CDO expected-loss APIは再利用。相関・recovery・担保の仮定、独立loss distribution、原典外部分の範囲 |
| 商品・real option | 平均回帰commodity tree、abandon／expand、Schwartz多因子、jump、swing、価格と気温の回帰ヘッジ | vol 12・25、`carbon`・`weather`・`ppa` | risk premiumと不完備性、exerciseの比較。必要パラメータ欠落の原典例は補助文献を要する |

### 7.3 Beyond Hullの既存テーマを深化する候補

| 領域 | 現状からの増分 | 先に必要なもの |
|---|---|---|
| 確率数値解析 | Milstein、強／弱収束、RQMC scramble CI、本当のreverse adjoint、MC Greeksの誤差・費用比較 | 共通の問題・誤差尺度・計算budget。`aad.py`の名称と中身を区別 |
| Surrogate | 高コストteacherでのresidual／DML、制約修復、latencyと全学習費用、OOD判定 | ベースライン、保存根拠配列、同じhardware／batch条件 |
| 逆問題 | learned forward surrogate、direct inverse、parameter uncertainty、quote noise・identifiability | rBergomi R1の確認、教師誤差と学習誤差の分離 |
| 予測→ヘッジ | surface latent forecast、共通の実現経路で予測とtrained policyを比較 | R2・R3、purged split、コスト、turnover、horizon別経済評価 |
| SPX／VIX | モデルごとのparameter recovery、joint calibration、surrogateの制約とOOD | 共通quote集合、nested MC誤差、hard check、実データなら利用条件 |
| 0DTE | 正しいCRN、イベント局所の精度、PIDE／DML、session境界 | R4、calendar・settlementのfixture、極短時間の基準価格 |
| RFR | 本格free-boundary SABR、stub・実日付、較正とhedgeの整合 | 検証可能な契約仕様とconvention、negative rate時の境界 |
| Crypto | 複数口座cascade、feeを含む裁定とLVR、oracle遅延・ADLの比較 | R6、価格impactと清算順序、資金保存、取引費用込み比較 |
| Climate／energy | storage、swing、共同price–generation–weatherモデル、basis risk | 不完備市場での評価規約、時系列・季節性、物理制約 |
| Inflation／JGBi | inflation option／YoY smile、確率的季節性、多因子rates、実市場較正 | fixingとforecastの区別、測度、floorの対象cash flow、日付規約 |
| Risk desk | 多変量EVT、cross gamma・vanna・vommaのP&L、広い商品群 | factorごとのfull repricing oracle、配賦合計、未説明P&L |
| Credit desk | dynamic credit、random recovery、非KO CDS option、incremental XVAとML | front-end protection等の契約定義、真の経路依存、信用・市場相関 |

### 7.4 基盤の改善という選択肢

- **正確な比較を支える基盤**：保存値だけの判定を原始配列からの再計算へ移す。教師誤差、離散化誤差、標本誤差、近似・学習誤差を別々に記録する。
- **再利用性**：ノートブックの局所関数を必要な範囲で共有APIにし、モデル名・関数名・原典式・教材・テスト・受入状態を結ぶ。全APIの網羅は現在のMODEL_INDEXガードの保証外。
- **学習経路**：大きくなったvol 06／10の見通し、演習・解答・段階別到達目標、モデル選択・誤差の読み方を改善する余地がある。ただし教材構成の変更案として別途評価する。
- **証跡の持続性**：変更の影響範囲に応じた再検査、同一画像の重複抑制、履歴と現行状態の明確な区別。D1・D3とまとめて判断する。
- **文献からコードへの追跡**：重要公式の手動検証を増やし、claim→式→実装→数値検査を結ぶ。現在のコーパスの量は、この対応の全面的完成を意味しない。

公開API変更、本番依存追加、大きな再構成は通常の小修正と区別して判断する。新しい全体アーキテクチャへの置換を、本資料から自動的に正当化しない。

## 8. 登録済みの研究トラックと構想

### 8.1 research_profiles.jsonの11候補

全体設定は`enabled_by_default=false`、`core_gate_dependency=false`、`network_download=false`。下表は**登録名**の一覧であり、学習済みモデルの一覧ではない。

| 領域 | 登録名 | 検討する方向 |
|---|---|---|
| surface_inverse | `direct_inverse` | surfaceから直接パラメータへ写す推定と、従来較正の比較 |
| surface_inverse | `vae` | surface／パラメータの潜在表現 |
| surface_inverse | `normalizing_flow` | 逆問題の分布・不確実性の表現 |
| surface_inverse | `simulation_based_inference` | simulatorによる推論・識別可能性 |
| surface_dynamics | `local_foundation_zero_shot` | ローカルで利用できる基盤時系列モデルのzero-shot比較 |
| surface_dynamics | `conditional_diffusion` | 条件付きsurface生成・時系列分布 |
| spx_vix | `signature_model` | 経路情報を使うSPX／VIXモデル |
| spx_vix | `perturbed_optimal_transport` | 分布・価格制約からのモデル化 |
| zero_dte | `differential_ml` | 極短期価格と微分量の同時学習 |
| zero_dte | `pide_surrogate` | jumpを含むPIDEの高速近似 |
| climate_energy | `storage_real_option` | 蓄電・貯蔵の運用選択を含む価値 |

**core昇格条件**：共通データで成熟したベースラインに勝ち、hard checkと再現性レビューを通ること。単に新しいモデルであること、training lossが下がること、図が作れることだけでは採用しない。

### 8.2 文書で挙がっているその他の構想

- Deep BSDE、PINN、DeepONet、Fourier Neural Operator、Differential PCA等。既存の安い解析解と比べるだけでなく、どの高次元・経路依存・逆問題に価値があるかを定める必要がある。
- 無限期間perpetualのBSDE、risk-based ADL、AMM token option等。vol 24の現在の簡略モデルとは区別する。
- **FRTB IMAをvol 29とする候補**：liquidity-horizon ES集約、stressed ES scaling、NMRF、P&L attribution eligibility、IMA／SA比較。ROADMAPにscope外の候補として記載されているが、作成・着手が承認済みの巻ではない。実装時はその時点の一次資料で制度の範囲を確かめる。

これらを新案として提案する場合は、「プロジェクト内で未言及の新規案」ではなく「既出候補の具体化」と表示する。

## 9. 残る検証課題・既知の限界

### 9.1 未再確認の監査報告6件

以下は2026-09-14監査に起源を持ち、現行ROADMAPでも残件とされる。**本資料では再現実験をしていないため、現在のコードで再確認済みの新しいバグ報告として扱わない。** 修正案の比較には基準となる現行出力と原因の再確認が必要。

| ID | 対象 | 報告されている問題 | 研究・実装への影響 |
|---|---|---|---|
| R1 | vol 19／rBergomi teacher | 離散kernelが右端点Riemann和なのに、補償項に連続時間の分散を使う | 期待分散にbiasが入り、teacherを前提とする較正・学習比較へ伝わる可能性 |
| R2 | vol 20／Log-HAR | log予測を単にexpで戻す再変換bias | 条件付き平均の予測評価が変わる。trainのみのsmearing等を比較する余地 |
| R3 | vol 20／hedge capstone | 予測volで実現経路とhedgeの両方を作り、予測誤差がP&Lへ伝わらない構成 | 予測の経済価値を比較する根拠として弱い。実現経路を固定する設計が必要 |
| R4 | vol 22／SV-jump | Poisson乱数の消費量で共通乱数の経路対応が崩れる | 差分Greeksやモデル比較の分散が増え、CRNを使ったとの説明が成立しにくい |
| R6 | vol 24／dynamic fee | 手数料なしの同じ裁定終点を使うためgross LVRが等しい | 「dynamic feeは効かない」という実証結果にできない。feeに応じた裁定行動のモデルが要る |
| R11 | vol 03／Hull Table 19.1・19.4 | 細かいhedge刻みの数値が印刷値と異なる。利息・割引の規約差もあるが原因未特定 | 規約・標本誤差・実装差を切り分ける。緩い許容差だけで受入しない |

R2・R3の実装先には`deep_hedge_price`が関係する。johnhullだけを変更して解決したことにしない。

### 9.2 根拠配列がなく保存値に依存する5項目

| 巻 | 残る項目 | 必要な追加証拠 |
|---|---|---|
| 18 | `residual_baseline` | residual比較を再計算できる出力・対応データ |
| 18 | `hard_violation_rate` | 各制約と判定対象を再評価できる原始配列 |
| 19 | `multi_start_calibration` | 各初期値・最適化結果・目的関数等の根拠 |
| 21 | timingフラグ | 実行条件と時間計測の根拠 |
| 22 | `calendar_violations` | 隣接満期の比較対象と違反判定を再計算できる配列 |

vol 26にあった3項目は既に再計算方式へ移行しているため、残件に戻さない。frontierの118チェックという既存の集計も、すべてが原始配列から独立再計算されるという意味ではない。

### 9.3 品質評価の読み違いを防ぐ例

- **モデルの近似誤差は残る**：basketのモーメント整合は受入済みでも、測定例では大きい相対誤差がある。受入は誤差を隠さず再現・説明できたことを含む。
- **欧州価格の一致だけでは経路を決められない**：M12は同じ欧州価格面を持つモデル間で二時点同時確率が異なることを示す。exoticやhedgeの追加にはjoint dynamicsの検証が必要。
- **有限格子は厳密解ではない**：static replicationの節点間残差、path-dependent treeの補間誤差、American境界の格子依存を残したまま明示する。
- **Greek境界**：lookbackの`r≈q`は未対応。6 skippedはこの系統の既存検査に由来する。新しいshoutまで同じ理由で未対応と広げない。
- **notebook検査の範囲**：汎用core検査は主にstdout／textで、すべてのPNG・Plotly payloadを一律比較しない。受入節には専用の図・ブラウザ検査がある。frontierにも汎用検査と専用検査の差がある。
- **表示環境**：portalはオフライン自己完結。Bookには既存のMathJax CDN依存が残る。実際のJupyter widget操作は、静的Bookのブラウザ確認だけでは全面的に保証できない。

### 9.4 既に解消した指摘を再び残件にしない

監査初期のD1–D11、R5・R7–R10には後続の是正がある。旧監査の冒頭だけを読むと現状と食い違う。監査§12の現状表、M1–M14の受入記録、最新ROADMAPを優先して読む。

直近ではM12／M13レビューのF1（後続節で基点検査が失敗する）とF2（Dupire入力価格のdocstring）はM14で対応済み。Dupireは**割引済みのコール価格面**を入力とすることを明記した。

## 10. データと論文コーパス

### 10.1 データの性格

主な計算・学習の参照データは固定seedの合成データ。Hullの印刷値やS&P rating matrix等、明示的に原典から転記した定数・表もある。したがって「実市場を使った継続的なOOS検証が済んでいる」とも「原典由来の値を一切含まない」とも言えない。

外部の市場データ取得は教材buildの前提にしない。実市場研究を追加する場合、入力の使用権、保存・再配布条件、取得時点、quote cleaning、calendar、train／test分割を定義し、現在のoffline coreと接続する方法を決める。

### 10.2 現時点で外部資料・入力が必要な例

| 対象 | 足りないもの・制約 | 取り得る方向 |
|---|---|---|
| 実市場のcalibration／forecast／hedge | 権利と品質が確認された時点付きデータ | ユーザー提供の非追跡データ、公開可能なfixture、合成実験との分離 |
| Hullのhistorical example | 4指数501日やGARCHの元時系列、T-bill関連の元入力等 | 印刷表の再現と、元データによる推定再現を区別 |
| Technical Notes | TN1・TN10・TN25等、手元の本文PDF外の資料 | 入手・参照範囲を確認してから仕様化 |
| KMV EDF | 実証的なdefault-frequency mapping | Mertonのdistance-to-defaultだけでEDF実装済みとはしない |
| ISDA標準CDS・fallback | 検証済みのoffline fixtureと契約定義が不足する箇所 | 利用可能な一次仕様・例を明示して整備。全仕様が有料だと一括断定しない |
| Schwartz–MoonのAmazon例 | Hull本文だけでは時間依存のσ(t)・η(t)等が揃わない | 補助文献から取得するか、変更した教育用例と明記 |
| 時系列foundation model | 重み・ライセンス・実行資源 | ローカル利用条件を調べ、core gateに混ぜない |
| 一部の参考論文 | Li／Vasicek等のlink-only資料、Andersen 2024の同定未解決 | 書誌を確定し、原文がない主張をverifiedへ昇格しない |

### 10.3 文献基盤の規模と使えるもの

`references/README.md`の文献一覧は61件を挙げる（2026-07-21時点：原論文PDF52、link-only 8、未解決1）。関連論文1件と公式コンベンション資料2件を含め、現在のv2コーパスのローカルPDFは55資料。

| v2コーパスの集計 | 件数 |
|---|---:|
| 資料／ページ | 55／1,627 |
| 抽出block | 18,747 |
| equation record | 17,288 |
| table／figure | 224／644 |
| claim／semantic chunk | 275／3,295 |
| 品質レポートのpass／例外 | 55／0 |
| gold対象 | 15資料・106ページ |
| 人手確認済みclaim／critical equation | 75／35 |
| 確認済み表 | 16表・463 scalar cells。構造の置換5件を含む |

抽出された17,288件の式すべてを人が数学的に検証したわけではない。品質PASSは抽出・構造・定義した品質条件の合格である。信頼状態を`verified`／`auto`／`unverified`／`failed`／`missing_source`等で分け、元PDFを一次資料として保持する。Gold内で自動抽出に失敗した式候補4件では画像fallbackを用いている。

利用できる情報は、論文Markdown、page/block、式、表、図、symbol、claim、chunk、元ページの位置・hash・provenance。P0の対応付けは10資料・9実装component・59symbolに対して35公式・4表assertion・50claimを結んでおり、全面的なcode-to-paper網羅ではない。主な対象はHull–White、Heston、Jarrow–Yildirim、JGBi、Hagan SABR、McNeil–Frey、RFR等。

検索は英語BM25＋日本語文字n-gramを使う。固定28queryの評価ではHit@5＝1.000という記録があるが、未知の質問すべてへの検索精度を保証しない。2回の独立buildで11,092相対ファイルがbyte一致した記録がある。抽出には任意のローカルツールMinerU 3.4.4を固定し、既定で外部LLM APIを必要としない。

### 10.4 研究への使い方

1. 追加案に関連する既存論文・原典式を検索する。
2. 主張の信頼状態を確認し、重要公式は原PDF・ページ画像に戻る。
3. 独立参照値を作り、実装・近似・学習それぞれの誤差を分ける。
4. 新しい論文を追加した場合も、書誌登録・抽出・重要箇所の確認・code対応を別々の完了条件にする。

Little Heston Trap、COS、MC Greeks、AAD等の重要箇所について、さらに式・実装対応を厚くする余地が既存資料にある。論文数を増やすことだけがコーパスの改善ではない。

## 11. 実行基盤・再現性・運用上の論点

### 11.1 技術構成

- Python 3.12以上、親リポジトリの単一uv workspaceと共有`.venv`。
- 主な計算・教材ライブラリ：NumPy、SciPy、Pandas、Matplotlib、japanize_matplotlib、Plotly、ipywidgets／ipympl、nbformat／nbclient／nbconvert。
- 配布：Jinja2＋Plotlyのportal、Jupyter Book／MyST。検査：pytest、ruff、Node／Playwright／Chromiumによるブラウザ検査。
- 既存の固定seed、fingerprint、JSON＋NPZ、`allow_pickle=False`、独立参照スクリプト、保存出力と再実行の比較を活用する。
- コード・識別子・commit messageは英語、教材・説明は日本語が基本。

### 11.2 入口となるコマンド

次は既存READMEにある代表的な入口。**実行場所は`/home/kazumasa/projects`（親workspace）**。本資料作成時に下記の重い一式を再実行したわけではない。

```bash
uv run --no-sync pytest johnhull/hullkit/tests johnhull/report/tests
make hull-artifacts-check
make hull-notebooks-check
make hull-core-notebooks-check
make hull-report
make hull-book
make hull-release-check

# release対象ファイルをcommitした後の追跡済みファイル検査
make hull-release-check HULL_RELEASE_FLAGS=--require-tracked
```

`make hull-release`はプロジェクトのテスト・lint・成果物検査・buildをまとめる入口。節別台帳の追加検査は`scripts/verify_section_ledger.py --check-artifacts`。現在のvol 06の既受入節には`scripts/verify_accepted_vol06_notebook.py --check`を使い、昔の基点固定スクリプトを現行HEADの包括的な合否判定として扱わない。

### 11.3 最新の証跡の範囲

- M14の記録：hullkit＋report **2,810 passed／6 skipped**、core notebook 19冊のfresh execution、既受入13節の個別テストとBook／portal再検査、M14の16状態・16画像、lint、台帳成果物、strict tracked releaseがPASS。
- `deep_hedge_price`の206 passedはM13レビューの記録。M14で再実行した結果に混ぜない。
- M14実装commitは`e4288dc0`、記録追記は`163f7412`。M14の検証文書にはremote未反映と記載されている。ローカルの確認済み内容と、remoteの配布状態は別に追跡する。
- 親workspace全体の`make test`が通ったことだけで、このプロジェクトの全検査・隣接学習エンジンの検査を代用しない。

## 12. ChatGPTに渡す検討依頼文

以下をこのファイルと一緒に渡せば、既存項目と重複しにくい検討を始められる。

```text
添付のMarkdownは、2026-09-27時点のjohnhullプロジェクトの収録内容、
実装の深さ、受入状態、既定計画、既知の限界です。
この内容を前提に、追加・深化できる教材や研究を検討してください。

最初に、現在の目的を「Hullの学習・原典再現」「数値モデルの理解」
「新しい研究の比較」「実市場への応用」の4軸で整理してください。
目的ごとに効果のある案を区別し、実市場データが必要な案には明示してください。

候補を次の4分類に分けてください。
1. 既定計画を具体化するもの
2. 既存機能の精度・検証・比較を改善するもの
3. 文書に既出の研究候補を深化するもの
4. 文書にまだない、新しい追加案

まず各分類の有望案を比較し、次に優先する5～10案を絞ってください。
モデル名だけを増やさず、各案について次の項目を示してください。
- 解く問い／学習者が得る理解
- 現状との差分と、流用できる巻・モジュール
- 最小の実験・教材・API・図の成果物
- 強い既存ベースラインと独立参照
- 価格／Greek／較正／予測／hedge等の評価指標と単位
- 離散化誤差・標本誤差・学習誤差の切り分け
- 必要データ・権利・ライブラリ・CPU/GPU・計算規模
- 依存する未解決問題、失敗条件、採用を見送る基準
- johnhullと隣接プロジェクトのどこに実装するか
- 最小構成と、その後の拡張を分けた手順

優先順位は、学習効果、既存の穴を埋める度合い、独立検証のしやすさ、
実装負担、データの入手性、既存基盤の再利用、研究上の新しさで比較してください。
点数を使う場合は主観的な評価であることを明記し、根拠を短く添えてください。

既存のAsian、basket、shout、local vol、転換社債、JGBi、信用デスク等を
未実装と扱わないでください。反対に、AAD、HJM/LMM、free-boundary SABR、
SPX/VIX joint calibration等は名前・説明があるだけで完成と扱わないでください。
accepted／PASSを市場性能の承認と解釈しないでください。

最近の論文や制度を提案の根拠にする場合は一次資料を検索し、日付とリンクを示し、
確認済みの事実と仮説を分けてください。文献名・実装効果・速度改善を推測で埋めないでください。
最後に、全節完了を優先する案と、研究テーマを1つ先行する案の2通りを比較してください。
この段階ではコード変更・依存追加・公開を行わず、検討結果を提示してください。
```

### 12.1 追加案の比較に使う記入枠

| 項目 | 記入内容 |
|---|---|
| 案名・分類 | 既定計画／検証改善／既出研究／新規案 |
| 中心となる問い | 何を理解・測定・改善したいか |
| 現状との差分 | 既存巻・API・検査では足りない点 |
| 最小成果物 | 例：1商品、独立参照、誤差図4枚、教材1節 |
| 比較相手 | 最も強い既存手法。単純だが不当に弱いbaselineは避ける |
| データ・計算 | 合成／実データ、規模、費用、権利、再現条件 |
| 成功／中止条件 | どの指標がどう変われば採用するか。負けた結果も保存 |
| 依存とリスク | R番号、金利tree、契約仕様、未入手資料等 |
| 置き場所 | johnhullの教材・teacherか、隣接プロジェクトの実験エンジンか |
| 優先理由 | 完了計画・学習効果・研究価値との関係 |

## 13. 根拠資料と読み方

パスはjohnhullを起点とする相対パス。親workspaceに置かれた設計書だけは`../docs/`で示す。別のChatGPTへ本ファイルだけを渡しても主要内容が分かるように要点を本文に含めた。元資料を開ける環境では、以下が確認先になる。

| 資料 | 何の根拠に使ったか |
|---|---|
| `README.md` | 目的、主要ディレクトリ、build・検査の入口 |
| `ROADMAP.md` | M14現在地、P0–P8、D1–D3、残件、FRTB候補 |
| `VALIDATION.md` | 時点別の検証結果、性能未承認、M14範囲 |
| `MODEL_INDEX.md` | モデル／API／巻の対応と限界 |
| `docs/section_inventory.json` | GE版の全306項目のID・正式題名・ページ |
| `docs/section_ledger.json`・`docs/SECTION_LEDGER.md` | 現在の受入状態。付録AはJSONから集計 |
| `docs/SECTION_AUDIT_2026-09-14.md` | 詳細な欠落、設計候補、未再確認報告。初期記述は§11–12の是正と合わせる |
| `docs/SECTION_27_5_ACCEPTANCE_2026-09-27.md`・`docs/SECTION_27_5_REVIEW_2026-09-27.md` | 最新のM14内容とレビュー |
| `docs/validation/section-27-5/m14-check.json` | M14統合証跡 |
| `docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md` | M12／M13レビュー。F1／F2はM14で対応済み |
| `docs/DATA_PROVENANCE.md` | 合成データ、転記資料、利用条件の扱い |
| `research_profiles.json` | 11研究候補名と昇格ルール |
| `release_manifest.json`・`book/_toc.yml` | 配布契約・Bookへの登録 |
| `references/README.md` | 文献目録と未入手資料 |
| `docs/PAPER_CORPUS_V2.md` | コーパス設計、信頼状態、gold・検索・再現性 |
| `references/processed/quality_report.json`・`references/processed/determinism_report.json` | コーパスの集計と再現性記録 |
| `../docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md` | Beyond Hullの責務分担・設計（親workspace側） |
| 各`.ipynb`のMarkdown／codeセル、`hullkit/src/hullkit/*.py` | 実際の収録見出しと関数・class定義 |

**本資料の確認範囲**：全30ノートブックの見出しと関連する範囲・限界説明、全73モジュールの定義目録、現行の台帳・計画・主要検証文書を突き合わせた。全関数の数理的な再レビュー、全ノートブックの新規実行、参考論文55本の再読を行った資料ではない。

---

## 付録A：全306項目の目録と受入状態

`section_inventory.json`と`section_ledger.json`から生成した完全目録。本文299節・付録7項目。原典の正式題名とページを保ち、**収録先があることと、個々の節の実装・受入が完了していることを区別する**。

`accepted`＝現行台帳で受入済み、`unreviewed`＝現行の節別受入では未評価。巻との対応は主な収録先であり、すべての節がその巻で完全実装されているという表ではない。ページはHull 11e Global Editionの印刷ページ。

### Ch 1 — vol 12（10項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 1.1 | Exchange-Traded Markets | 24 | unreviewed |
| 1.2 | Over-the-Counter Markets | 25 | unreviewed |
| 1.3 | Forward Contracts | 28 | unreviewed |
| 1.4 | Futures Contracts | 30 | unreviewed |
| 1.5 | Options | 31 | unreviewed |
| 1.6 | Types of Traders | 33 | unreviewed |
| 1.7 | Hedgers | 34 | unreviewed |
| 1.8 | Speculators | 36 | unreviewed |
| 1.9 | Arbitrageurs | 39 | unreviewed |
| 1.10 | Dangers | 39 | unreviewed |

### Ch 2 — vol 04（11項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 2.1 | Background | 46 | unreviewed |
| 2.2 | Specification of a Futures Contract | 48 | unreviewed |
| 2.3 | Convergence of Futures Price to Spot Price | 50 | unreviewed |
| 2.4 | The Operation of Margin Accounts | 51 | unreviewed |
| 2.5 | OTC Markets | 54 | unreviewed |
| 2.6 | Market Quotes | 57 | unreviewed |
| 2.7 | Delivery | 60 | unreviewed |
| 2.8 | Types of Traders and Types of Orders | 61 | unreviewed |
| 2.9 | Regulation | 62 | unreviewed |
| 2.10 | Accounting and Tax | 63 | unreviewed |
| 2.11 | Forward vs. Futures Contracts | 64 | unreviewed |

### Ch 3 — vol 04（7項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 3.1 | Basic Principles | 70 | unreviewed |
| 3.2 | Arguments for and Against Hedging | 72 | unreviewed |
| 3.3 | Basis Risk | 75 | unreviewed |
| 3.4 | Cross Hedging | 79 | unreviewed |
| 3.5 | Stock Index Futures | 84 | unreviewed |
| 3.6 | Stack and Roll | 89 | unreviewed |
| 3.appendix | Capital Asset Pricing Model | 96 | unreviewed |

### Ch 4 — vol 04（12項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 4.1 | Types of Rates | 98 | unreviewed |
| 4.2 | Reference Rates | 99 | unreviewed |
| 4.3 | The Risk-Free Rate | 101 | unreviewed |
| 4.4 | Measuring Interest Rates | 101 | unreviewed |
| 4.5 | Zero Rates | 104 | unreviewed |
| 4.6 | Bond Pricing | 105 | unreviewed |
| 4.7 | Determining Zero Rates | 106 | unreviewed |
| 4.8 | Forward Rates | 109 | unreviewed |
| 4.9 | Forward Rate Agreements | 110 | unreviewed |
| 4.10 | Duration | 112 | unreviewed |
| 4.11 | Convexity | 116 | unreviewed |
| 4.12 | Theories of the Term Structure of Interest Rates | 117 | unreviewed |

### Ch 5 — vol 04（14項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 5.1 | Investment Assets vs. Consumption Assets | 124 | unreviewed |
| 5.2 | Short Selling | 125 | unreviewed |
| 5.3 | Assumptions and Notation | 126 | unreviewed |
| 5.4 | Forward Price for an Investment Asset | 127 | unreviewed |
| 5.5 | Known Income | 130 | unreviewed |
| 5.6 | Known Yield | 132 | unreviewed |
| 5.7 | Valuing Forward Contracts | 133 | unreviewed |
| 5.8 | Are Forward Prices and Futures Prices Equal? | 135 | unreviewed |
| 5.9 | Futures Prices of Stock Indices | 135 | unreviewed |
| 5.10 | Forward and Futures Contracts on Currencies | 137 | unreviewed |
| 5.11 | Futures on Commodities | 141 | unreviewed |
| 5.12 | The Cost of Carry | 143 | unreviewed |
| 5.13 | Delivery Options | 144 | unreviewed |
| 5.14 | Futures Prices and Expected Future Spot Prices | 144 | unreviewed |

### Ch 6 — vol 04（5項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 6.1 | Day Count and Quotation Conventions | 152 | unreviewed |
| 6.2 | Treasury Bond Futures | 155 | unreviewed |
| 6.3 | Eurodollar and SOFR Futures | 160 | unreviewed |
| 6.4 | Duration-Based Hedging Strategies Using Futures | 165 | unreviewed |
| 6.5 | Hedging Portfolios of Assets and Liabilities | 167 | unreviewed |

### Ch 7 — vol 07（13項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 7.1 | Mechanics of Interest Rate Swaps | 172 | unreviewed |
| 7.2 | Determining Risk-Free Rates | 175 | unreviewed |
| 7.3 | Reasons for Trading Interest Rate Swaps | 176 | unreviewed |
| 7.4 | The Organization of Trading | 178 | unreviewed |
| 7.5 | The Comparative-Advantage Argument | 181 | unreviewed |
| 7.6 | Valuation of Interest Rate Swaps | 183 | unreviewed |
| 7.7 | How the Value Changes Through Time | 185 | unreviewed |
| 7.8 | Fixed-for-Fixed Currency Swaps | 186 | unreviewed |
| 7.9 | Valuation of Fixed-for-Fixed Currency Swaps | 190 | unreviewed |
| 7.10 | Other Currency Swaps | 192 | unreviewed |
| 7.11 | Credit Risk | 193 | unreviewed |
| 7.12 | Credit Default Swaps | 193 | unreviewed |
| 7.13 | Other Types of Swaps | 194 | unreviewed |

### Ch 8 — vol 12（4項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 8.1 | Securitization | 201 | unreviewed |
| 8.2 | The U.S. Housing Market | 205 | unreviewed |
| 8.3 | What went Wrong? | 209 | unreviewed |
| 8.4 | The Aftermath | 211 | unreviewed |

### Ch 9 — vol 09（4項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 9.1 | CVA and DVA | 216 | unreviewed |
| 9.2 | FVA and MVA | 219 | unreviewed |
| 9.3 | KVA | 222 | unreviewed |
| 9.4 | Calculation Issues | 223 | unreviewed |

### Ch 10 — vol 02（12項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 10.1 | Types of Options | 227 | unreviewed |
| 10.2 | Option Positions | 229 | unreviewed |
| 10.3 | Underlying Assets | 231 | unreviewed |
| 10.4 | Specification of Stock Options | 233 | unreviewed |
| 10.5 | Trading | 236 | unreviewed |
| 10.6 | Trading Costs | 237 | unreviewed |
| 10.7 | Margin Requirements | 237 | unreviewed |
| 10.8 | The Options Clearing Corporation | 239 | unreviewed |
| 10.9 | Regulation | 239 | unreviewed |
| 10.10 | Taxation | 240 | unreviewed |
| 10.11 | Warrants, Employee Stock Options, and Convertibles | 241 | unreviewed |
| 10.12 | Over-the-Counter Options Markets | 242 | unreviewed |

### Ch 11 — vol 02（7項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 11.1 | Factors Affecting Option Prices | 247 | unreviewed |
| 11.2 | Assumptions and Notation | 251 | unreviewed |
| 11.3 | Upper and Lower Bounds for Option Prices | 252 | unreviewed |
| 11.4 | Put–Call Parity | 255 | unreviewed |
| 11.5 | Calls on a Non-Dividend-Paying Stock | 257 | unreviewed |
| 11.6 | Puts on a Non-Dividend-Paying Stock | 260 | unreviewed |
| 11.7 | Effect of Dividends | 262 | unreviewed |

### Ch 12 — vol 02（5項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 12.1 | Principal-Protected Notes | 268 | unreviewed |
| 12.2 | Trading an Option and the Underlying Asset | 270 | unreviewed |
| 12.3 | Spreads | 272 | unreviewed |
| 12.4 | Combinations | 280 | unreviewed |
| 12.5 | Other Payoffs | 283 | unreviewed |

### Ch 13 — vol 01（12項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 13.1 | A One-Step Binomial Model and a No-Arbitrage Argument | 288 | unreviewed |
| 13.2 | Risk-Neutral Valuation | 292 | unreviewed |
| 13.3 | Two-Step Binomial Trees | 294 | unreviewed |
| 13.4 | A Put Example | 297 | unreviewed |
| 13.5 | American Options | 298 | unreviewed |
| 13.6 | Delta | 299 | unreviewed |
| 13.7 | Matching Volatility with u and d | 300 | unreviewed |
| 13.8 | The Binomial Tree Formulas | 302 | unreviewed |
| 13.9 | Increasing the Number of Steps | 302 | unreviewed |
| 13.10 | Using DerivaGem | 303 | unreviewed |
| 13.11 | Options on other Assets | 304 | unreviewed |
| 13.appendix | Derivation of the Black–Scholes–Merton Option-Pricing Formula from a Binomial Tree | 312 | unreviewed |

### Ch 14 — vol 01（9項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 14.1 | The Markov Property | 316 | unreviewed |
| 14.2 | Continuous-Time Stochastic Processes | 317 | unreviewed |
| 14.3 | The Process for a Stock Price | 322 | unreviewed |
| 14.4 | The Parameters | 325 | unreviewed |
| 14.5 | Correlated Processes | 326 | unreviewed |
| 14.6 | Itô’s Lemma | 327 | unreviewed |
| 14.7 | The Lognormal Property | 328 | unreviewed |
| 14.8 | Fractional Brownian Motion | 329 | unreviewed |
| 14.appendix | A Nonrigorous Derivation of Itô’s Lemma | 336 | unreviewed |

### Ch 15 — 旧配置BSM（13項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 15.1 | Lognormal Property of Stock Prices | 339 | unreviewed |
| 15.2 | The Distribution of the Rate of Return | 340 | unreviewed |
| 15.3 | The Expected Return | 341 | unreviewed |
| 15.4 | Volatility | 342 | unreviewed |
| 15.5 | The Idea Underlying the Black–Scholes–Merton Differential Equation | 346 | unreviewed |
| 15.6 | Derivation of the Black–Scholes–Merton Differential Equation | 348 | unreviewed |
| 15.7 | Risk-Neutral Valuation | 351 | unreviewed |
| 15.8 | Black–Scholes–Merton Pricing Formulas | 352 | unreviewed |
| 15.9 | Cumulative Normal Distribution Function | 355 | unreviewed |
| 15.10 | Warrants and Employee Stock Options | 356 | unreviewed |
| 15.11 | Implied Volatilities | 358 | unreviewed |
| 15.12 | Dividends | 360 | unreviewed |
| 15.appendix | Proof of the Black–Scholes–Merton Formula Using Risk-Neutral Valuation | 369 | unreviewed |

### Ch 16 — vol 12（5項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 16.1 | Contractual Arrangements | 371 | unreviewed |
| 16.2 | Do Options Align the Interests of Shareholders and Managers? | 373 | unreviewed |
| 16.3 | Accounting Issues | 374 | unreviewed |
| 16.4 | Valuation | 375 | unreviewed |
| 16.5 | The Backdating Scandal | 380 | unreviewed |

### Ch 17 — vol 02（6項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 17.1 | Options on Stock Indices | 384 | unreviewed |
| 17.2 | Currency Options | 386 | unreviewed |
| 17.3 | Options on Stocks Paying known Dividend Yields | 389 | unreviewed |
| 17.4 | Valuation of European Stock Index Options | 391 | unreviewed |
| 17.5 | Valuation of European Currency Options | 394 | unreviewed |
| 17.6 | American Options | 395 | unreviewed |

### Ch 18 — vol 02（11項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 18.1 | Nature of Futures Options | 401 | unreviewed |
| 18.2 | Reasons for the Popularity of Futures Options | 404 | unreviewed |
| 18.3 | European Spot and Futures Options | 404 | unreviewed |
| 18.4 | Put–Call Parity | 405 | unreviewed |
| 18.5 | Bounds for Futures Options | 406 | unreviewed |
| 18.6 | Drift of a Futures Price in a Risk-Neutral World | 407 | unreviewed |
| 18.7 | Black’s Model for Valuing Futures Options | 408 | unreviewed |
| 18.8 | Using Black’s model instead of Black–Scholes–Merton | 409 | unreviewed |
| 18.9 | Valuation of Futures Options Using Binomial Trees | 410 | unreviewed |
| 18.10 | American Futures Options vs. American Spot Options | 412 | unreviewed |
| 18.11 | Futures-Style Options | 413 | unreviewed |

### Ch 19 — vol 03（15項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 19.1 | Illustration | 417 | unreviewed |
| 19.2 | Naked and Covered Positions | 418 | unreviewed |
| 19.3 | Greek Letter Calculation | 420 | unreviewed |
| 19.4 | Delta Hedging | 421 | unreviewed |
| 19.5 | Theta | 427 | unreviewed |
| 19.6 | Gamma | 429 | unreviewed |
| 19.7 | Relationship between Delta, Theta, and Gamma | 433 | unreviewed |
| 19.8 | Vega | 434 | unreviewed |
| 19.9 | Rho | 436 | unreviewed |
| 19.10 | The Realities of Hedging | 437 | unreviewed |
| 19.11 | Scenario Analysis | 437 | unreviewed |
| 19.12 | Extension of Formulas | 439 | unreviewed |
| 19.13 | Portfolio Insurance | 441 | unreviewed |
| 19.14 | Application of Machine Learning to Hedging | 443 | unreviewed |
| 19.appendix | Taylor Series Expansions and Greek Letters | 450 | unreviewed |

### Ch 20 — vol 05（9項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 20.1 | Implied Volatilities of Calls and Puts | 451 | unreviewed |
| 20.2 | Volatility Smile for Foreign Currency Options | 453 | unreviewed |
| 20.3 | Volatility Smile for Equity Options | 456 | unreviewed |
| 20.4 | Alternative Ways of Characterizing the Volatility Smile | 458 | unreviewed |
| 20.5 | The Volatility Term Structure and Volatility Surfaces | 458 | unreviewed |
| 20.6 | Minimum Variance Delta | 460 | unreviewed |
| 20.7 | The Role of the Model | 460 | unreviewed |
| 20.8 | When a Single Large Jump is Anticipated | 460 | unreviewed |
| 20.appendix | Determining Implied Risk-Neutral Distributions from Volatility Smiles | 467 | unreviewed |

### Ch 21 — vol 06（8項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 21.1 | Binomial Trees | 470 | unreviewed |
| 21.2 | Using the Binomial Tree for Options on Indices, Currencies, and Futures Contracts | 478 | unreviewed |
| 21.3 | Binomial Model for a Dividend-Paying Stock | 480 | unreviewed |
| 21.4 | Alternative Procedures for Constructing Trees | 485 | unreviewed |
| 21.5 | Time-Dependent Parameters | 488 | unreviewed |
| 21.6 | Monte Carlo Simulation | 489 | unreviewed |
| 21.7 | Variance Reduction Procedures | 495 | unreviewed |
| 21.8 | Finite Difference Methods | 498 | unreviewed |

### Ch 22 — vol 08・27（9項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 22.1 | The VaR and ES Measures | 514 | unreviewed |
| 22.2 | Historical Simulation | 517 | unreviewed |
| 22.3 | Model-Building Approach | 521 | unreviewed |
| 22.4 | The Linear Model | 524 | unreviewed |
| 22.5 | The Quadratic Model | 530 | unreviewed |
| 22.6 | Monte Carlo Simulation | 533 | unreviewed |
| 22.7 | Comparison of Approaches | 533 | unreviewed |
| 22.8 | Back Testing | 534 | unreviewed |
| 22.9 | Principal Components Analysis | 534 | unreviewed |

### Ch 23 — vol 05（7項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 23.1 | Estimating Volatility | 542 | unreviewed |
| 23.2 | The Exponentially Weighted Moving Average Model | 544 | unreviewed |
| 23.3 | The Garch(1,1) Model | 546 | unreviewed |
| 23.4 | Choosing between the Models | 547 | unreviewed |
| 23.5 | Maximum Likelihood Methods | 548 | unreviewed |
| 23.6 | Using Garch(1,1) to Forecast Future Volatility | 553 | unreviewed |
| 23.7 | Correlations | 556 | unreviewed |

### Ch 24 — vol 09・16・28（9項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 24.1 | Credit Ratings | 562 | unreviewed |
| 24.2 | Historical Default Probabilities | 563 | unreviewed |
| 24.3 | Recovery Rates | 564 | unreviewed |
| 24.4 | Estimating Default Probabilities from Bond Yield Spreads | 564 | unreviewed |
| 24.5 | Comparison of Default Probability Estimates | 567 | unreviewed |
| 24.6 | Using Equity Prices to Estimate Default Probabilities | 570 | unreviewed |
| 24.7 | Credit Risk in Derivatives Transactions | 571 | unreviewed |
| 24.8 | Default Correlation | 577 | unreviewed |
| 24.9 | Credit VaR | 580 | unreviewed |

### Ch 25 — vol 09・16・28（11項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 25.1 | Credit Default Swaps | 588 | unreviewed |
| 25.2 | Valuation of Credit Default Swaps | 591 | unreviewed |
| 25.3 | Credit Indices | 595 | unreviewed |
| 25.4 | The Use of Fixed Coupons | 596 | unreviewed |
| 25.5 | CDS Forwards and Options | 597 | unreviewed |
| 25.6 | Basket Credit Default Swaps | 597 | unreviewed |
| 25.7 | Total Return Swaps | 597 | unreviewed |
| 25.8 | Collateralized Debt Obligations | 599 | unreviewed |
| 25.9 | Role of Correlation in a Basket CDS and CDO | 601 | unreviewed |
| 25.10 | Valuation of a Synthetic CDO | 601 | unreviewed |
| 25.11 | Alternatives to the Standard Market Model | 608 | unreviewed |

### Ch 26 — vol 10（17項目／受入9）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 26.1 | Packages | 614 | unreviewed |
| 26.2 | Perpetual American Call and Put Options | 615 | unreviewed |
| 26.3 | Nonstandard American Options | 616 | unreviewed |
| 26.4 | Gap Options | 617 | unreviewed |
| 26.5 | Forward Start Options | 618 | unreviewed |
| 26.6 | Cliquet Options | 618 | unreviewed |
| 26.7 | Compound Options | 618 | unreviewed |
| 26.8 | Chooser Options | 619 | unreviewed |
| 26.9 | Barrier Options | 620 | accepted |
| 26.10 | Binary Options | 622 | accepted |
| 26.11 | Lookback Options | 623 | accepted |
| 26.12 | Shout Options | 625 | accepted |
| 26.13 | Asian Options | 626 | accepted |
| 26.14 | Options to Exchange One Asset for Another | 627 | accepted |
| 26.15 | Options Involving Several Assets | 628 | accepted |
| 26.16 | Volatility and Variance Swaps | 629 | accepted |
| 26.17 | Static Options Replication | 632 | accepted |

### Ch 27 — vol 06（8項目／受入5）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 27.1 | Alternatives to Black–Scholes–Merton | 641 | accepted |
| 27.2 | Stochastic Volatility Models | 646 | accepted |
| 27.3 | The IVF Model | 649 | accepted |
| 27.4 | Convertible Bonds | 650 | accepted |
| 27.5 | Path-Dependent Derivatives | 653 | accepted |
| 27.6 | Barrier Options | 656 | unreviewed |
| 27.7 | Options on Two Correlated Assets | 658 | unreviewed |
| 27.8 | Monte Carlo Simulation and American Options | 660 | unreviewed |

### Ch 28 — vol 10・13（8項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 28.1 | The Market Price of Risk | 671 | unreviewed |
| 28.2 | Several State Variables | 674 | unreviewed |
| 28.3 | Martingales | 675 | unreviewed |
| 28.4 | Alternative Choices for the Numeraire | 676 | unreviewed |
| 28.5 | Extension to Several Factors | 679 | unreviewed |
| 28.6 | Black’s Model Revisited | 680 | unreviewed |
| 28.7 | Option to Exchange One Asset for Another | 681 | unreviewed |
| 28.8 | Change of Numeraire | 682 | unreviewed |

### Ch 29 — vol 11（4項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 29.1 | Bond Options | 688 | unreviewed |
| 29.2 | Interest Rate Caps and Floors | 693 | unreviewed |
| 29.3 | European Swap Options | 699 | unreviewed |
| 29.4 | Hedging Interest Rate Derivatives | 703 | unreviewed |

### Ch 30 — vol 11（4項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 30.1 | Convexity Adjustments | 707 | unreviewed |
| 30.2 | Timing Adjustments | 710 | unreviewed |
| 30.3 | Quantos | 711 | unreviewed |
| 30.appendix | Proof of the Convexity Adjustment Formula | 718 | unreviewed |

### Ch 31 — 旧配置金利モデル（5項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 31.1 | Background | 719 | unreviewed |
| 31.2 | One-Factor Models | 721 | unreviewed |
| 31.3 | Real-World vs. Risk-Neutral Processes | 726 | unreviewed |
| 31.4 | Estimating Parameters | 727 | unreviewed |
| 31.5 | More Sophisticated Models | 728 | unreviewed |

### Ch 32 — 旧配置金利モデル・vol 26（7項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 32.1 | Extensions of Equilibrium Models | 732 | unreviewed |
| 32.2 | Options on Bonds | 736 | unreviewed |
| 32.3 | Volatility Structures | 737 | unreviewed |
| 32.4 | Interest Rate Trees | 738 | unreviewed |
| 32.5 | A General Tree-Building Procedure | 740 | unreviewed |
| 32.6 | Calibration | 749 | unreviewed |
| 32.7 | Hedging Using a One-Factor Model | 751 | unreviewed |

### Ch 33 — 旧配置金利モデル（3項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 33.1 | The Heath, Jarrow, and Morton Model | 755 | unreviewed |
| 33.2 | The BGM Model | 758 | unreviewed |
| 33.3 | Agency Mortgage-Backed Securities | 768 | unreviewed |

### Ch 34 — vol 07（6項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 34.1 | Variations on the Vanilla Deal | 773 | unreviewed |
| 34.2 | Compounding Swaps | 775 | unreviewed |
| 34.3 | Currency and Nonstandard Swaps | 776 | unreviewed |
| 34.4 | Equity Swaps | 777 | unreviewed |
| 34.5 | Swaps with Embedded Options | 779 | unreviewed |
| 34.6 | Other Swaps | 781 | unreviewed |

### Ch 35 — vol 12・25（8項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 35.1 | Agricultural Commodities | 785 | unreviewed |
| 35.2 | Metals | 786 | unreviewed |
| 35.3 | Energy Products | 787 | unreviewed |
| 35.4 | Modeling Commodity Prices | 789 | unreviewed |
| 35.5 | Weather Derivatives | 795 | unreviewed |
| 35.6 | Insurance Derivatives | 796 | unreviewed |
| 35.7 | Pricing Weather and Insurance Derivatives | 797 | unreviewed |
| 35.8 | How an Energy Producer can Hedge Risks | 798 | unreviewed |

### Ch 36 — vol 12（5項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 36.1 | Capital Investment Appraisal | 802 | unreviewed |
| 36.2 | Extension of the Risk-Neutral Valuation Framework | 803 | unreviewed |
| 36.3 | Estimating the Market Price of Risk | 805 | unreviewed |
| 36.4 | Application to the Valuation of a Business | 806 | unreviewed |
| 36.5 | Evaluating Options in an Investment Opportunity | 806 | unreviewed |

### Ch 37 — vol 12（3項目／受入0）

| ID | 原典の題名 | 開始ページ | 状態 |
|---|---|---:|---|
| 37.1 | Lessons for All Users of Derivatives | 815 | unreviewed |
| 37.2 | Lessons for Financial Institutions | 819 | unreviewed |
| 37.3 | Lessons for Nonfinancial Corporations | 824 | unreviewed |

## 付録B：hullkit全73モジュール

対象ディレクトリ：`hullkit/src/hullkit/`。公開名の59モジュールと内部名の14モジュールを列挙する。パッケージ初期化用の`__init__.py`は数えない。役割欄はコードの先頭docstring、定義欄は先頭がunderscoreでないトップレベルの関数・class名を抽出したもの。importした名前、class method、aliasは含めない。この定義目録は各APIの検証完了表ではない。

### B.1 公開名のモジュール59件

| モジュール | コード上の役割説明 | 関数・classの定義 |
|---|---|---|
| `aad.py` | Pathwise, likelihood-ratio and bump Greeks (A3 deep-dive — toward AAD). | `pathwise_greeks`、`likelihood_ratio_greeks`、`bump_greeks` |
| `alternative_models.py` | CEV, Merton jump diffusion and variance gamma for Hull 11e GE §27.1. | `cev_price`、`merton_jump_price`、`variance_gamma_price` |
| `amm.py` | Constant-product and concentrated-liquidity AMM teaching primitives. | `cpmm_invariant`、`cpmm_spot_price`、`SwapResult`、`cpmm_swap_x_for_y`、`cpmm_swap_y_for_x`、`cpmm_reserves_at_price`、`LVRResult`、`loss_versus_rebalancing`、`dynamic_fee_rate`、`concentrated_liquidity_amounts`、`concentrated_liquidity_value`、`concentrated_loss_versus_rebalancing` |
| `bsm.py` | Black-Scholes-Merton analytic formulas (Hull 11e, Ch.15 / Ch.17). | `d1`、`d2`、`call_price`、`put_price`、`call_delta`、`put_delta`、`gamma`、`vega`、`call_theta`、`put_theta`、`call_rho`、`put_rho`、`vanna`、`vomma`、`pv_dividends`、`call_price_cash_dividends`、`put_price_cash_dividends`、`black_american_call_approx`、`call_early_exercise_thresholds`、`call_early_exercise_can_be_optimal`、`european_call_lower_bound`、`european_put_lower_bound`、`put_call_parity_residual`、`american_call_put_bounds` |
| `carbon.py` | Synthetic carbon-futures option models and risk-premium sensitivities. | `black76_price`、`CarbonDynamics`、`CarbonRiskPremia`、`simulate_terminal_futures`、`CarbonOptionEstimate`、`carbon_option_mc`、`CarbonPremiumSensitivity`、`risk_premium_sensitivity` |
| `cds.py` | Single-name CDS valuation (Hull 11e, §25.2–25.5). | `CDSLegs`、`cds_legs`、`cds_par_spread`、`cds_risky_duration`、`cds_mtm`、`binary_cds_spread`、`implied_hazard`、`bootstrap_from_cds`、`actual360_to_actual_actual`、`fixed_coupon_price`、`upfront_payment`、`cds_forward_spread`、`cds_option` |
| `convertible_bond.py` | Defaultable binomial valuation of a convertible bond (Hull GE §27.4). | `ConvertibleTree`、`defaultable_branch_probabilities`、`convertible_bond_tree` |
| `copula.py` | Gaussian copula and portfolio credit loss (A4 deep-dive). | `portfolio_loss_samples`、`vasicek_loss_cdf`、`conditional_default_prob`、`gaussian_copula_samples` |
| `credit.py` | Credit risk and credit derivatives (Hull 11e, Ch.24/25). | `survival_prob`、`default_prob`、`hazard_from_spread`、`cds_spread`、`merton_default_prob`、`gaussian_copula_conditional`、`vasicek_credit_var` |
| `credit_curve.py` | Hazard-rate curves and their calibration (Hull 11e, §24.4). | `HazardCurve`、`average_hazards_from_spreads`、`forward_hazards_from_average`、`bond_price_from_yield`、`risk_free_bond_price`、`forward_risk_free_value`、`expected_default_loss_pv`、`BondBootstrapResult`、`bootstrap_from_bonds` |
| `credit_metrics.py` | CreditMetrics: rating transitions and credit VaR (Hull 11e, §24.9). | `TransitionMatrix`、`rating_thresholds`、`migrate`、`simulate_rating_migrations`、`credit_loss_distribution`、`credit_var`、`expected_loss` |
| `credit_portfolio.py` | One-factor copula valuation of CDO tranches and basket CDS (Hull 11e, §25.6–25.11). | `gauss_hermite_factor`、`standardized_t_cdf`、`standardized_t_ppf`、`double_t_factor_quadrature`、`conditional_default_prob`、`double_t_threshold`、`double_t_conditional_prob`、`binomial_pmf`、`heterogeneous_default_pmf`、`smallest_integer_above`、`tranche_principal_by_defaults`、`TrancheValuation`、`cdo_tranche_valuation`、`cdo_tranche_spread`、`cdo_upfront`、`KthToDefaultValuation`、`kth_to_default_valuation`、`kth_to_default_spread`、`compound_correlation`、`BaseCorrelationResult`、`base_correlations`、`expected_loss_curve` |
| `exotics.py` | Closed-form exotic option pricers (Hull 11e, Ch.26). | `gap_call`、`gap_put`、`cash_or_nothing`、`asset_or_nothing`、`bgk_adjusted_barrier`、`barrier_call`、`barrier_put`、`lookback_floating_call`、`lookback_floating_put`、`lookback_fixed_call`、`lookback_fixed_put`、`asian_moments`、`asian_average_price`、`asian_call_turnbull_wakeman`、`asian_seasoned_average_price`、`asian_average_strike`、`exchange_spread_volatility`、`exchange_option`、`exchange_option_american`、`better_of_two_assets`、`worse_of_two_assets`、`basket_moments`、`basket_option_price` |
| `fd.py` | Finite-difference pricing on a uniform ln-S grid (Hull 11e, Ch.21). | `fd_vanilla` |
| `fd_advanced.py` | Explicit finite-difference scheme and its (conditional) stability (A3 deep-dive). | `fd_explicit`、`stability_factor` |
| `fourier.py` | Fourier option pricing: the COS method (A2 deep-dive). | `lognormal_cf`、`cos_price`、`cos_density` |
| `frontier_reference.py` | CPU-quick, API-backed reference payloads for beyond-Hull volumes 21--28. | `FrontierReference`、`volume21_reference`、`volume22_reference`、`volume23_reference`、`volume24_reference`、`volume25_reference`、`volume26_reference`、`volume27_reference`、`volume28_reference`、`build_frontier_reference` |
| `hedging.py` | Delta-hedging simulations (Hull 11e, Ch.19 §19.2/§19.4, Tables 19.1-19.4). | `simulate_delta_hedge`、`simulate_stop_loss_hedge` |
| `heston.py` | Heston stochastic-volatility model (A2 deep-dive — beyond Hull's local/flat vol). | `heston_cf`、`heston_mc_price` |
| `hull_white.py` | One-factor Hull–White pricing and exact Gaussian simulation. | `HullWhiteParams`、`HullWhiteSwaption`、`hw_b`、`hw_phi`、`hw_discount_bond`、`hw_exact_transition`、`simulate_hw_paths`、`hw_zcb_option`、`hw_jamshidian_swaption`、`calibrate_hw1f` |
| `inflation.py` | CPI conventions, deterministic seasonality, and inflation-swap cash flows. | `CPIObservationConvention`、`MonthlySeasonality`、`ZeroCouponInflationCurve`、`monthly_cpi_value`、`interpolated_cpi`、`cpi_observation`、`apply_cpi_rebase`、`seasonal_forward_index`、`zcis_cashflow`、`zcis_npv`、`zcis_par_rate`、`bootstrap_zc_inflation_curve`、`yoy_rate`、`yoy_swap_npv` |
| `ir_options.py` | Black's-model interest-rate derivatives (Hull 11e, Ch.29/30). | `bond_option_black`、`caplet_black`、`cap_black`、`swaption_black`、`convexity_adjustment`、`bond_yield_convexity` |
| `jarrow_yildirim.py` | One-factor Jarrow--Yildirim inflation model and measure-consistent pricing. | `JarrowYildirimParams`、`JYSimulation`、`jy_correlation_matrix`、`jy_cpi_forward`、`jy_cpi_log_covariance`、`jy_cpi_total_variance`、`jy_payment_forward_cpi`、`jy_expected_cpi_ratio`、`jy_cpi_option`、`jy_zcis_value`、`jy_yoy_value`、`simulate_jy_forward_levels`、`simulate_jy_paths` |
| `jgbi.py` | Japanese inflation-linked government bond conventions and valuation. | `JGBITerms`、`JGBICashflow`、`JGBIFloorMonteCarlo`、`JGBIFloorRisk`、`jgbi_reference_index`、`jgbi_indexation_coefficient`、`jgbi_cashflows`、`jgbi_accrued_interest`、`jgbi_real_clean_price`、`jgbi_nominal_settlement_amount`、`jgbi_real_yield`、`jgbi_nominal_present_value`、`jgbi_breakeven_inflation`、`jgbi_deflation_floor_black`、`jgbi_deflation_floor_jy`、`jgbi_deflation_floor_jy_mc`、`jgbi_floor_adjusted_price`、`jgbi_floor_risk` |
| `liquidation.py` | Margin, liquidation, oracle-risk, and loss-waterfall mechanics. | `MarginAccount`、`account_equity`、`margin_requirement`、`liquidation_triggered`、`bankruptcy_price`、`liquidation_price`、`OracleRisk`、`assess_oracle_risk`、`OracleShock`、`oracle_shock`、`execution_price`、`LiquidationLedger`、`liquidation_waterfall` |
| `local_volatility.py` | Dupire local volatility from a smooth European call surface (Hull GE §27.3). | `dupire_local_vol` |
| `mc.py` | GBM Monte Carlo simulation (Hull 11e, Ch.14). | `simulate_gbm_paths`、`gbm_theory`、`price_european_mc`、`price_american_lsm`、`lsm_exercise_boundary` |
| `mc_advanced.py` | Advanced Monte-Carlo: variance reduction and quasi-MC (A3 deep-dive). | `plain_price`、`control_variate_price`、`importance_sampling_price`、`qmc_price`、`error_vs_n` |
| `nbplot.py` | Shared notebook-plotting helpers for the johnhull volumes. | `setup`、`figure_canvases`、`enable_static_figures`、`kde_xy` |
| `path_dependent_tree.py` | Hull GE §27.5 tree with a representative arithmetic-average state. | `AveragePriceTree`、`arithmetic_average_call_tree` |
| `payoffs.py` | Terminal payoffs and option trading strategies (Hull 11e, Ch.10 / Ch.12). | `leg_payoff`、`strategy_payoff`、`box_spread_value` |
| `perpetuals.py` | Deterministic perpetual-futures mechanics for teaching and audit. | `MarketSnapshot`、`position_pnl`、`position_notional`、`FundingPolicy`、`funding_rate`、`funding_cashflow`、`completed_funding_intervals`、`settled_funding_cashflow`、`FundingLedger`、`matched_funding_ledger`、`BasisPath`、`simulate_basis_feedback` |
| `plotly_viz.py` | Interactive Plotly builders for the johnhull volumes (existing content). | `plotly_strategy_payoffs`、`plotly_delta_vs_spot`、`plotly_delta_hedge_cost`、`plotly_tree_convergence`、`plotly_var_es`、`plotly_credit_survival`、`plotly_quadratic_variation`、`plotly_ito_correction`、`plotly_girsanov`、`plotly_heston_smile`、`plotly_cos_density_convergence`、`plotly_sabr_smile`、`plotly_iv_surface`、`plotly_smile_model_risk`、`plotly_sabr_rho_nu_smile_greeks`、`plotly_sabr_greeks_by_param`、`plotly_sabr_param_greeks`、`plotly_mc_variance_reduction`、`plotly_qmc_vs_pseudo`、`plotly_american_boundary`、`plotly_exposure_profile`、`plotly_cva_sensitivity`、`plotly_portfolio_loss_correlation`、`plotly_copula_scatter`、`plotly_gamma_surface`、`plotly_greeks_map`、`plotly_bsm_greeks_sensitivity`、`plotly_stop_loss_vs_delta_hedge`、`plotly_binomial_lattice`、`plotly_garch_volatility`、`plotly_garch_term_structure`、`plotly_merton_structural`、`plotly_portfolio_diversification`、`plotly_yield_curve`、`plotly_bond_convexity`、`plotly_swap_value`、`plotly_barrier_knockout`、`plotly_asian_vs_european` |
| `pnl_explain.py` | P&L explain: factor exposure aggregation, delta-gamma-vega Taylor P&L | `aggregate_exposures`、`delta_gamma_vega_pnl`、`pnl_attribution`、`limit_utilization`、`desk_report` |
| `ppa.py` | Synthetic renewable-PPA payoffs, valuation, and cash-flow risk. | `ppa_settlement`、`PriceGenerationScenarios`、`simulate_price_generation`、`CashFlowRisk`、`cash_flow_risk`、`PPAValuation`、`evaluate_ppa`、`hedge_sensitivity` |
| `rates.py` | Interest-rate and bond utilities (Hull 11e, Ch.4). | `to_continuous`、`from_continuous`、`bond_price`、`bond_yield`、`macaulay_duration`、`convexity`、`forward_rate`、`fra_value`、`zero_interp`、`discount_factor`、`forward_discount`、`instantaneous_forward`、`bootstrap_zero_curve` |
| `rfr.py` | Risk-free-rate conventions, exact daily compounding and curve layers. | `BusinessCalendar`、`RFRConvention`、`DailyAccrual`、`CompoundedRFR`、`daily_accrual_schedule`、`compounded_rfr`、`rfr_coupon`、`continuous_compounding_approximation`、`RfrCurve`、`MultiCurveScenario`、`curve_basis_spread`、`futures_forward_from_covariance`、`PolicyJump`、`policy_jump_path`、`collateralized_present_value` |
| `rfr_options.py` | Bachelier and compounded-RFR option teachers for post-LIBOR markets. | `bachelier_price`、`bachelier_delta`、`gaussian_quadrature_price`、`CompoundedOptionResult`、`compounded_rate_option_mc` |
| `risk.py` | Value at Risk and Expected Shortfall (Hull 11e, Ch.22). | `historical_var_es`、`normal_var`、`normal_es`、`portfolio_sigma` |
| `risk_allocation.py` | Risk decomposition: analytic-normal marginal/component VaR, historical | `marginal_var_normal`、`component_var_normal`、`incremental_var`、`euler_es_components` |
| `sabr.py` | SABR model — Hagan's implied-volatility expansion (A2 deep-dive). | `sabr_implied_vol`、`sticky_strike_delta`、`sabr_smile_delta`、`sabr_greeks`、`calibrate_sabr` |
| `sabr_normal.py` | Normal, shifted and free-boundary SABR diagnostics for RFR options. | `normal_sabr_implied_vol`、`normal_sabr_price`、`shifted_sabr_implied_vol`、`free_boundary_sabr_implied_vol`、`shifted_sabr_price`、`free_boundary_sabr_price`、`sticky_strike_delta`、`bartlett_delta`、`NormalSabrTeacherResult`、`ConditionalNormalSabrTeacherResult`、`ShiftedSabrTeacherResult`、`normal_sabr_mc_price`、`normal_sabr_conditional_mc_price`、`shifted_sabr_mc_price`、`StaticArbitrageDiagnostics`、`call_grid_arbitrage_diagnostics`、`HaganErrorDiagnostics`、`hagan_error_diagnostics`、`HedgeComparison`、`compare_delta_hedges` |
| `sde.py` | Stochastic-calculus primitives (A1 deep-dive — beyond Hull's tool-level use). | `brownian_paths`、`quadratic_variation`、`running_quadratic_variation`、`ito_riemann_sum`、`euler_maruyama`、`girsanov_weights` |
| `spx_vix.py` | Teaching utilities for joint SPX/VIX models (beyond-Hull volume 21). | `PDVParameters`、`PDVPath`、`four_factor_pdv`、`affine_forward_variance`、`rough_heston_fractional_kernel`、`quintic_ou_variance`、`JointMarketTargets`、`JointObjective`、`joint_spx_vix_objective`、`VixTeacherResult`、`nested_vix_teacher`、`finite_difference_greeks`、`out_of_domain_flags`、`PolynomialSurrogate`、`fit_polynomial_surrogate`、`SurrogateComparison`、`compare_teacher_surrogate` |
| `static_replication.py` | Static call ladders for barrier hedging (Hull 11e GE §26.17, pp.632–634). | `StaticCallHedge`、`up_and_out_call_hedge` |
| `stochastic_volatility.py` | Stochastic-volatility building blocks for Hull 11e GE §27.2 (pp.646–649). | `average_variance_rate`、`time_dependent_bsm_price`、`expected_average_variance`、`simulate_average_variance`、`mixing_price`、`heston_price` |
| `surrogate_data.py` | Uncertainty-aware analytic, COS, and Monte-Carlo surrogate teachers. | `MonteCarloEstimate`、`MonteCarloCallEstimates`、`analytic_bsm_rows`、`mc_black_scholes_call_estimates`、`mc_black_scholes_call`、`mc_bsm_rows`、`heston_cos_price`、`rbergomi_call_price`、`forward_surface_teacher` |
| `surrogate_validation.py` | Torch-free hard financial checks for pricing surrogates. | `CheckResult`、`HardValidationReport`、`check_price_bounds`、`check_put_call_parity`、`check_strike_monotonicity`、`check_spot_monotonicity`、`check_strike_convexity`、`check_calendar_monotonicity`、`check_nonnegative_gamma`、`check_greek_consistency`、`validation_report` |
| `swaps.py` | Interest-rate and currency swap valuation (Hull 11e, Ch.7). | `discount`、`swap_rate`、`irs_value_bonds`、`irs_value_fras`、`currency_swap_value` |
| `tail_risk.py` | Filtered historical simulation and extreme value theory (POT/GPD) tail risk. | `filtered_historical_var_es`、`GPDFit`、`fit_gpd_pot`、`evt_var_es`、`mean_excess` |
| `teaching.py` | hullkit.teaching — markdown scaffolds for the johnhull notebooks. | `scaffold`、`practice_box`、`caption` |
| `trees.py` | CRR binomial trees (Hull 11e, Ch.13). | `crr_params`、`risk_neutral_p`、`binomial_tree`、`crr_price`、`tree_delta` |
| `var_backtest.py` | VaR backtesting statistics: Kupiec POF, Christoffersen tests, Basel traffic light. | `exceedance_series`、`kupiec_pof`、`christoffersen_independence`、`christoffersen_cc`、`BaselZone`、`basel_traffic_light` |
| `variance_swaps.py` | Variance and volatility swaps by static replication (Hull 11e GE §26.16, pp.629-632). | `realized_variance`、`realized_volatility`、`variance_notional`、`default_s_star`、`strike_spacing`、`otm_option_prices`、`fair_variance`、`vix_cumulative_variance`、`vix_index`、`fair_variance_from_implied_vols`、`variance_swap_value`、`expected_volatility`、`volatility_swap_value` |
| `vol_surface.py` | Arbitrage-aware total-variance surfaces and convex call projection. | `SSVIParameters`、`SurfaceConstraintComparison`、`ssvi_butterfly_margins`、`ssvi_is_butterfly_safe`、`ssvi_total_variance`、`fit_ssvi_slice`、`project_convex_call_prices`、`variance_term_rmse`、`compare_surface_constraints` |
| `volatility.py` | Implied volatility and volatility estimation (Hull 11e, Ch.20 / Ch.23). | `implied_vol`、`breeden_litzenberger_density`、`forward_moneyness`、`strike_from_forward_moneyness`、`delta_from_strike`、`strike_from_delta`、`ewma_variance`、`ewma_covariance`、`garch11_variance`、`garch11_long_run`、`garch11_forecast`、`garch11_fit` |
| `weather.py` | Synthetic temperature dynamics, weather premia, and station basis risk. | `seasonal_temperature_mean`、`simulate_ou_temperature`、`fractional_noise_autocovariance`、`simulate_fractional_ou_temperature`、`degree_day_index`、`weather_contract_premium`、`station_index`、`BasisRiskReport`、`optimal_basis_hedge` |
| `xva.py` | Counterparty credit exposure and XVA (A4 deep-dive). | `forward_exposure`、`expected_exposure`、`expected_negative_exposure`、`pfe`、`cva`、`dva`、`fva`、`default_probs_from_spreads`、`netting_set_exposure`、`collateralized_exposure`、`cva_single_payoff` |
| `zero_dte.py` | Calendar, variance-clock and SV+jump teaching tools for 0DTE options. | `TradingSession`、`trading_seconds_to_settlement`、`variance_clock_fraction`、`time_of_day_bucket`、`intraday_jump_intensity`、`scheduled_jump_intensity`、`TotalVarianceCheck`、`total_variance_consistency`、`ScheduledJump`、`scheduled_variance`、`EventSplitMetrics`、`event_non_event_metrics`、`SVJumpTeacherResult`、`sv_jump_teacher` |

### B.2 内部モジュール14件

節ごとの共有図を作る内部builderと、one-shoutの内部価格エンジン。内部関数名を公開API契約として扱わない。

| モジュール | コード上の役割説明 |
|---|---|
| `_alternative_models_lesson.py` | Four saved-data Plotly figures for Hull 11e GE §27.1. |
| `_asian_lesson.py` | Private artifact-only Plotly lessons for Hull 11e GE §26.13. |
| `_basket_lesson.py` | Private saved-data Plotly lessons for Hull 11e GE §26.15. |
| `_binary_lesson.py` | Shared Plotly lesson figures for Hull 11e GE §26.10 binary options. |
| `_convertible_bond_lesson.py` | Four shared Book and portal figures for Hull GE §27.4. |
| `_exchange_lesson.py` | Private artifact-only Plotly lessons for Hull 11e GE §26.14. |
| `_local_volatility_lesson.py` | Four shared Book and portal figures for Hull 11e GE §27.3. |
| `_lookback_lesson.py` | Shared Plotly lesson figures for Hull 11e GE §26.11 lookback options. |
| `_path_dependent_lesson.py` | Four shared Book and portal figures for Hull GE §27.5. |
| `_shout.py` | Private teaching CRR engine for one optimal shout (Hull 11e GE §26.12). |
| `_shout_lesson.py` | Private artifact-only Plotly lessons for Hull 11e GE §26.12. |
| `_static_replication_lesson.py` | Saved-data Plotly lesson for Hull 11e GE §26.17 static options replication. |
| `_stochastic_volatility_lesson.py` | Four saved-data Plotly figures for Hull 11e GE §27.2. |
| `_variance_swap_lesson.py` | Private saved-data Plotly lessons for Hull 11e GE §26.16 (volatility and variance swaps). |

## 付録C：全30ノートブックの実ファイル

セル数は保存済みipynbの全セルを数えたもの。多いほど実装・検証が深いという尺度ではない。各巻の詳細は本文§3–4を参照。

| 区分 | johnhullからの相対パス | セル数 |
|---|---|---:|
| vol 01 | `volumes/01_foundations/foundations.ipynb` | 49 |
| vol 02 | `volumes/02_options_basics/options_basics.ipynb` | 44 |
| vol 03 | `volumes/03_greeks/greeks.ipynb` | 41 |
| vol 04 | `volumes/04_futures_forwards_rates/futures_rates.ipynb` | 48 |
| vol 05 | `volumes/05_vol_smile_estimation/vol_smile.ipynb` | 39 |
| vol 06 | `volumes/06_numerical_methods/numerical.ipynb` | 94 |
| vol 07 | `volumes/07_swaps/swaps.ipynb` | 33 |
| vol 08 | `volumes/08_risk_var/risk_var.ipynb` | 32 |
| vol 09 | `volumes/09_credit_xva/credit_xva.ipynb` | 34 |
| vol 10 | `volumes/10_exotics_martingales/exotics.ipynb` | 125 |
| vol 11 | `volumes/11_ir_derivatives_market/ir_options.ipynb` | 36 |
| vol 12 | `volumes/12_qualitative_summary/qualitative_summary.ipynb` | 33 |
| vol 13 | `volumes/13_stochastic_calculus/stochastic_calculus.ipynb` | 30 |
| vol 14 | `volumes/14_stoch_vol_fourier/stoch_vol_fourier.ipynb` | 35 |
| vol 15 | `volumes/15_advanced_numerics/advanced_numerics.ipynb` | 22 |
| vol 16 | `volumes/16_xva_credit/xva_credit.ipynb` | 22 |
| vol 17 | `volumes/17_capstone/capstone.ipynb` | 18 |
| vol 18 | `volumes/18_ml_surrogates/ml_surrogates.ipynb` | 23 |
| vol 19 | `volumes/19_inverse_surfaces/inverse_surfaces.ipynb` | 24 |
| vol 20 | `volumes/20_surface_dynamics/surface_dynamics.ipynb` | 24 |
| vol 21 | `volumes/21_spx_vix/spx_vix.ipynb` | 23 |
| vol 22 | `volumes/22_zero_dte/zero_dte.ipynb` | 23 |
| vol 23 | `volumes/23_rfr_post_libor/rfr_post_libor.ipynb` | 23 |
| vol 24 | `volumes/24_crypto_market_structure/crypto_market_structure.ipynb` | 23 |
| vol 25 | `volumes/25_climate_energy/climate_energy.ipynb` | 25 |
| vol 26 | `volumes/26_inflation_jgbi/inflation_jgbi.ipynb` | 39 |
| vol 27 | `volumes/27_risk_desk/risk_desk.ipynb` | 46 |
| vol 28 | `volumes/28_credit_desk/credit_desk.ipynb` | 47 |
| 旧BSM | `notebooks/bsm_chapter15.ipynb` | 66 |
| 旧金利モデル | `interest_rate_models/ir_models.ipynb` | 55 |

## 付録D：ポータル全12テーマの図数

現行レジストリから集計。図にはmenuや複数traceを含むものがあり、134という値は操作状態数や独立検証数とは異なる。

| テーマID | 表示名 | 図数 |
|---|---|---:|
| `options_core` | オプションの設計図 | 7 |
| `numerics` | 数値手法の収束 | 25 |
| `risk_credit` | リスクと信用 | 12 |
| `stochastic` | 確率解析 | 3 |
| `volatility` | 確率ボラティリティ | 10 |
| `rates_swaps` | 金利とスワップ | 11 |
| `exotics` | エキゾチック | 34 |
| `ml_derivatives` | MLとデリバティブ | 12 |
| `volatility_frontiers` | ボラ最前線 | 8 |
| `crypto_market` | Crypto市場構造 | 4 |
| `climate_energy` | 気候とエネルギー | 4 |
| `risk_management` | リスク管理デスク | 4 |
| 合計 | 12テーマ | 134 |

---

この資料は2026-09-27のスナップショット。将来の更新ではROADMAP、節別台帳、実際のコード・成果物を優先し、古い受入時点の記録と現行HEADの検証を分けて読む。
