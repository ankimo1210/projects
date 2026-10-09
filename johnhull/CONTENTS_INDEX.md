# johnhull — 目次・収録モデル索引

更新日：2026-10-09。Hull *Options, Futures, and Other Derivatives* 第11版 Global Edition。

**本編37章・306節を宣言した範囲で受入済み。全28巻と旧2冊、研究2件と統合研究1件を以下に整理する。**
Jupyter Book の登録は概要1ページ＋教材30ページ。研究資料は Book とは別の置き場にある。

この索引は、巻・章別補足教材に収録した主要モデル、商品、分析手法を探すための入口。
巻別表には後から加えた章別補足教材の計算も含み、元の notebook の各セルとの一対一対応は示さない。
全モジュール・関数・テスト・検証条件は [実装詳細索引](MODEL_INDEX.md) を参照。
定性の説明だけの節と、数値計算を実装した節は [節別台帳](docs/SECTION_LEDGER.md) で確認できる。

## 使い方

- **教材から探す：** 下の巻名を開く。リンク先は保存済み notebook。
- **モデル名から探す：** このファイル内を検索する。実装の関数名・テストは [MODEL_INDEX.md](MODEL_INDEX.md) にある。
- **追加した章別教材を探す：** [章別補足教材](#章別補足教材) と段階別の状態文書を参照。
- **完成範囲・制限を確認する：** [全体ロードマップ](ROADMAP.md)、[最終統合記録](docs/FINAL_INTEGRATION_2026-10-08.md)、[この索引の制限](#収録範囲と制限) を参照。

## 1. コア教材 — vol 01–12

| 巻 | 教材 | Hull 章 | 主要な収録モデル・商品・分析手法 |
|---|---|---|---|
| 01 | [二項木・確率過程の基礎](volumes/01_foundations/foundations.ipynb) | 13・14 | Cox–Ross–Rubinstein（CRR）二項木、リスク中立評価、Wiener 過程、幾何ブラウン運動（GBM）、相関ブラウン運動、伊藤の補題 |
| 02 | [オプションの基礎・戦略](volumes/02_options_basics/options_basics.ipynb) | 10–12・17・18 | Black–Scholes–Merton（BSM）、既知配当・配当利回り・株価指数・通貨への拡張、Black の米国型コール近似、put–call parity、スプレッド・ストラドル・ボックス等の payoff |
| 03 | [Greeks とヘッジ](volumes/03_greeks/greeks.ipynb) | 19 | BSM の delta・gamma・vega・theta・rho・vanna・vomma、デルタヘッジ、ストップロス、ポートフォリオ保険、ヘッジ損益・資金繰り |
| 04 | [先物・フォワード・金利](volumes/04_futures_forwards_rates/futures_rates.ipynb) | 2–6 | Cost of carry、FX フォワード、先物ヘッジ・最小分散ヘッジ比率、ゼロ曲線 bootstrap、債券価格、FRA、duration・convexity |
| 05 | [ボラティリティ・スマイル・推定](volumes/05_vol_smile_estimation/vol_smile.ipynb) | 20・23 | インプライド・ボラティリティ逆算、Breeden–Litzenberger 密度、moneyness・delta 軸、スマイル／期間構造、EWMA、GARCH(1,1)、共分散・予測 |
| 06 | [数値計算・高度な価格モデル](volumes/06_numerical_methods/numerical.ipynb) | 21・27 | 二項木・三項木・MC・有限差分、Longstaff–Schwartz／境界方策による米国型 MC、CEV、Merton jump diffusion、variance gamma、時間依存ボラ・Hull–White 混合・Heston、SABR、IVF／Dupire local volatility、転換社債、算術平均経路依存木、バリア木、2資産木 |
| 07 | [スワップ](volumes/07_swaps/swaps.ipynb) | 7・34 | 金利・通貨・株式・商品スワップ、債券／FRA 分解、非標準 leg、複利スワップ、RFR leg、取り消し可能スワップ |
| 08 | [市場リスク・VaR](volumes/08_risk_var/risk_var.ipynb) | 22 | Historical VaR／ES、正規 VaR／ES、delta-normal・delta-gamma、Cornish–Fisher、PCA、バックテスト |
| 09 | [信用リスク・XVA](volumes/09_credit_xva/credit_xva.ipynb) | 9・24・25 | Merton 構造モデル、hazard／default probability、CDS、Vasicek 信用損失、Gaussian copula、CDO tranche、CVA・DVA・資金調達の影響。数値例は vol 28 とも共有 |
| 10 | [エキゾチック・マルチンゲール](volumes/10_exotics_martingales/exotics.ipynb) | 26・28 | デジタル・gap・バリア・ルックバック・shout・Asian・basket、Margrabe 交換オプション、永久米国型、非標準行使、forward-start・cliquet・compound・chooser、variance／volatility swap、静的複製、リスク価格・マルチンゲール・numeraire／測度変更 |
| 11 | [金利デリバティブの市場モデル](volumes/11_ir_derivatives_market/ir_options.ipynb) | 29・30 | Black–76、債券オプション、cap／floor・caplet stripping、swaption、金利／ボラヘッジ、convexity・timing・quanto 調整 |
| 12 | [制度・商品・実物オプション・教訓](volumes/12_qualitative_summary/qualitative_summary.ipynb) | 1・8・16・35–37 | 市場制度、ABS／CDO waterfall、従業員オプション、商品価格の平均回帰・jump、HDD／CDD、再保険・CAT、Schwartz–Moon 企業価値、撤退／拡張リアルオプション、分散投資・リスク統制 |

### 旧2冊 — Book にも登録

| 教材 | Hull 章 | 収録モデル・関連計算 |
|---|---|---|
| [BSM Chapter 15](notebooks/bsm_chapter15.ipynb) | 15 | Black–Scholes–Merton の価格・Greeks と可視化。元の notebook は hullkit を import しない |
| [Interest Rate Models](interest_rate_models/ir_models.ipynb) | 31–33 | 旧金利教材。関連する章別補足も合わせると、Vasicek・CIR・Ho–Lee・Hull–White・Black–Karasinski、2因子 Gaussian、Jamshidian、初期曲線に較正した金利木、HJM、LMM／BGM、住宅ローン／CMO／OAS を扱う。元の notebook は hullkit を import しない |

## 2. 深掘り — vol 13–17

| 巻 | 教材 | 主要な収録モデル・分析手法 |
|---|---|---|
| 13 | [確率解析](volumes/13_stochastic_calculus/stochastic_calculus.ipynb) | Brownian motion、二次変分、伊藤積分・伊藤補正、Euler–Maruyama、Girsanov 測度変更、Feynman–Kac の説明 |
| 14 | [確率ボラティリティ・Fourier](volumes/14_stoch_vol_fourier/stoch_vol_fourier.ipynb) | Heston の特性関数と MC、SABR／Hagan smile、COS による価格・密度、解析／MC／Fourier の比較 |
| 15 | [高度な数値手法](volumes/15_advanced_numerics/advanced_numerics.ipynb) | Control variates、importance sampling、Sobol QMC、LSM、有限差分・Crank–Nicolson、pathwise／likelihood-ratio／bump Greeks。AAD tape の実装は含まない |
| 16 | [XVA・信用](volumes/16_xva_credit/xva_credit.ipynb) | EE・PFE、CVA・DVA・FVA、Gaussian copula、信用エクスポージャーと相関 |
| 17 | [統合演習](volumes/17_capstone/capstone.ipynb) | Heston＋COS 価格 → Greeks → エクスポージャー → CVA の計算連携 |

## 3. Beyond Hull — vol 18–28

| 巻 | 教材 | 主要な収録モデル・分析手法 |
|---|---|---|
| 18 | [ML 価格代理モデル・DML](volumes/18_ml_surrogates/ml_surrogates.ipynb) | BSM・Heston・有限格子 rBergomi 教師、MLP・Polynomial Ridge、価格／Greek の同時学習・differential ML、autodiff Greeks、裁定制約、seed 比較 |
| 19 | [逆問題・裁定を考慮した曲面](volumes/19_inverse_surfaces/inverse_surfaces.ipynb) | SSVI、convex call-price projection、Heston／SABR／rBergomi 教師曲面、forward surrogate＋optimizer の2段階較正、Direct Inverse Ridge、多始点・repricing 診断 |
| 20 | [曲面動学・予測・ヘッジ判断](volumes/20_surface_dynamics/surface_dynamics.ipynb) | Persistence・EWMA・GARCH・Log-HAR、HARNet・TCN・LSTM・Transformer、purged walk-forward、train-only 変換、bootstrap CI、共通経路によるヘッジ損益／CVaR／turnover 比較 |
| 21 | [SPX／VIX・経路依存ボラ](volumes/21_spx_vix/spx_vix.ipynb) | 4-factor PDV、affine forward variance、quintic OU、rough Heston の fractional kernel、nested VIX 教師、SPX／VIX 同時較正の目的関数、CPU quadratic surrogate・OOD 判定 |
| 22 | [0DTE・日中時計・イベント](volumes/22_zero_dte/zero_dte.ipynb) | Intraday variance clock、予定イベントの分散、jump intensity、Bates 型確率ボラ＋jump 教師、イベント別誤差・paired payoff 比較 |
| 23 | [RFR・LIBOR 後の金利](volumes/23_rfr_post_libor/rfr_post_libor.ipynb) | 日次 RFR 複利・営業日／観測／支払規約、多曲線シナリオ、Bachelier、normal／shifted SABR、明示 shift 境界を使う free-boundary 近似、Bartlett delta |
| 24 | [暗号資産の市場構造](volumes/24_crypto_market_structure/crypto_market_structure.ipynb) | Perpetual funding・basis feedback、清算 waterfall・保険基金・ADL、constant-product／concentrated AMM、LVR、取引損益と費用 |
| 25 | [気候・エネルギー](volumes/25_climate_energy/climate_energy.ipynb) | 炭素価格の Black–76・確率ボラ・jump、温度 OU／fractional OU、HDD／CDD、basis hedge、再エネ PPA、Cash Flow at Risk（CFaR） |
| 26 | [インフレ・物価連動国債](volumes/26_inflation_jgbi/inflation_jgbi.ipynb) | Hull–White 1因子、Jarrow–Yildirim、CPI 季節性・lag・補間、ZCIS／YoY swap、JGBi 実質利回り・指数化・償還元本 floor |
| 27 | [リスク管理デスク](volumes/27_risk_desk/risk_desk.ipynb) | Kupiec・Christoffersen、Filtered Historical Simulation、EVT／POT／GPD、Euler リスク配分、delta・gamma・vega 損益 attribution |
| 28 | [信用デスク](volumes/28_credit_desk/credit_desk.ipynb) | 債券／CDS hazard bootstrap、CDS legs・MTM・forward／option、CreditMetrics rating transition、Gaussian double-t copula、kth-to-default、synthetic CDO・base correlation、netting／collateral CVA |

## 4. 章別補足教材

通常の `make hull-report` で補足教材を生成する。ポータルの入口から **Ch1–25・Ch29–37 の34章**に到達できる。
Ch26–28 は既存巻の節別教材を利用する。全 Book 本文をこの補足教材で置換したわけではない。

| 範囲 | 主な補完内容 | 詳細・節別計算 |
|---|---|---|
| Ch1–9 | 市場・ヘッジ・先物／フォワード・金利・スワップ・証券化 | [P6 状態](docs/P6_STATUS.md) |
| Ch10–21 | オプション境界・配当・戦略・CRR・BSM・従業員オプション・Greeks・smile・数値手法 | [P4 状態](docs/P4_STATUS.md) |
| Ch22–25 | VaR／ES・ボラ推定・信用・CDS／CDO・XVA | [P5 状態](docs/P5_STATUS.md) |
| Ch28–34 | 測度変更、金利市場モデル、短期金利、較正木、HJM／BGM、住宅ローン、非標準スワップ | [P3 状態](docs/P3_STATUS.md) |
| Ch35–37 | 商品・天候・再保険・企業価値・リアルオプション・リスク管理の教訓 | [P7 状態](docs/P7_STATUS.md) |

これらの文書は途中の履歴も保持している。現在の統合・main 反映は [ROADMAP](ROADMAP.md) と [最終統合記録](docs/FINAL_INTEGRATION_2026-10-08.md) を正本とする。

## 5. 研究教材 — 本編受入件数とは別

| 研究 | 収録したモデル・分析 | 状態・結果 |
|---|---|---|
| [RB-F07：較正を通した市場クオート感応度](research/RB-F07/README.md) | 単一曲線の預金／FRA／par swap 較正、解析 Jacobian、減衰 Newton、随伴 quote sensitivity、再 bootstrap bump、座標／残差不変性、補間変更・情報不足の増幅診断 | **v1 完了**。6か月の柱リスクが0でも、同じ満期の預金クオートリスクは +106.30/bp。補間変更は別モデルで、不変性を主張しない。v2／v3 は今後の範囲 |
| [RB-F05：不連続 payoff の微分教師と DML](research/RB-F05/README.md) | GBM cash-or-nothing digital、LRM、厳密条件付き期待値、CRN bump、ramp 対照、price-only／DML、train-only 正規化、解析・Hermite 補間との精度／費用比較 | **digital v1 完了**。3 seed で DML の価格・delta が改善。解析・補間より速くならず、標準価格器への速度採用はしない。離散バリアはprivate教師・独立参照に着手（研究受入は未完了）。0DTE・rough は未着手の後続範囲 |

計算の正本は非公開の [quote risk](hullkit/src/hullkit/_quote_risk.py)、[digital 教師](hullkit/src/hullkit/_digital_teachers.py)、[digital DML](../deep_hedge_price/src/deep_hedge_price/_digital_dml.py)。
研究 backlog 全体は [研究計画](docs/superpowers/plans/2026-09-27-research-backlog.md) を参照。

**統合研究：** [較正込み市場クオートGreeksのDML](research/RB-F07/quote_dml/README.md)はv1完了・main統合済み。30NN＋4回帰、310計時、288費用対照、独立再計算・両復元・3図・独立最終レビューを完了。統合後の関連3suiteは6,919 passed／6 skipped、release gate PASS。金利shock残余改善、価格/spot/35shock混合残余悪化を記録し、標準価格/Greek器への昇格は不採用。[設計](docs/superpowers/specs/2026-10-09-calibrated-quote-dml-design.md)／[実施計画](docs/superpowers/plans/2026-10-09-calibrated-quote-dml.md)。

## 6. モデル名からの短い案内

| 探したいもの | 入口 |
|---|---|
| BSM・CRR・米国型・Greeks | vol 01–03・06、旧 BSM、Ch10–21 補足 |
| Heston・SABR・Dupire・CEV・Merton jump・VG | vol 06・14、曲面／代理モデルは vol 18–19 |
| Asian・barrier・lookback・basket・compound・chooser | vol 10、経路依存／バリア／2資産の木は vol 06 |
| VaR・ES・EWMA・GARCH・バックテスト | vol 05・08・27、予測比較は vol 20 |
| Merton credit・CDS・CDO・CreditMetrics・copula・XVA | vol 09・16・28、CVA 統合演習は vol 17 |
| Vasicek・CIR・Ho–Lee・Hull–White・BK・HJM・BGM | 旧 IR＋Ch31–33 補足、HW／インフレは vol 26 |
| Black–76・cap／floor・swaption・quanto・RFR | vol 11・23、Ch29–34 補足 |
| rBergomi・rough kernel・PDV・SPX／VIX・0DTE | vol 18–22。各モデルの実装範囲は下記の制限を参照 |
| Neural surrogate・DML・予測 NN・deep hedging | vol 18–20、RB-F05。torch 計算は別プロジェクト deep_hedge_price |
| AMM・LVR・funding・清算 | vol 24 |
| Carbon・温度・HDD／CDD・PPA | vol 25、基礎と契約例は Ch35 補足 |
| Jarrow–Yildirim・CPI・JGBi | vol 26 |
| Schwartz–Moon・撤退／拡張 option | Ch36 補足、vol 12 のテーマ |
| 曲線の市場クオートリスク・adjoint | RB-F07 |

## 7. 収録範囲と制限

- **受入と性能は別。** accepted／PASS は宣言した計算・独立比較・再現性・配布整合性の範囲。合成データによる教材の検証であり、市場予測力や実運用収益を証明しない。
- **部分実装のモデル名を完全実装と読まない。** vol 21 の rough Heston は kernel、SPX／VIX 同時較正は目的関数・教師。rBergomi は有限格子教師。vol 23 の free-boundary SABR は明示 shift 境界を使い、Antonov 型の内生境界ではない。vol 15 は AAD tape を持たない。
- **§33.2 BGM は入力条件を指定した検証。** 単一曲線 LMM、cap cashflows、frozen swaption、PCA factor を実装。原典 flexicap の strike・日付・MC 規約と sticky の K0 が不足し、印刷値 3.43／3.58／3.61 等の無条件再現はしていない。
- **§36.4 Schwartz–Moon は原著価格未再現。** 四半期 OU・会計 CF・税・default を独立検証したが、原著の会計／ESO 時点が不足。原著 5457M／27.9%／12.42 は未再現で、指定した会計条件での値と区別する。
- **§36.5 の共同 option は原典脚注と差がある。** 単独の撤退／拡張価格は一致。共同値 3.217896M は独立方策でも確認したが、原典の「相互作用なし」は再現できない。
- **Book と受入表示の範囲は同一ではない。** 章別 fast-v1 補足 HTML を含めて受け入れた。全 Book 本文・全画像・別画面幅・全306節の両保管庫からの復元を最終統合で再実行したとは主張しない。
- **研究の後続は未完了。** RB-F07 v2／v3、RB-F05 の離散バリア・0DTE・rough は今回の完成範囲に含まれない。

## 8. 全体ロードマップ

| 段階 | 範囲 | 受入済み節 | 状態 |
|---|---|---:|---|
| P0 | §26.9–§27.4 | 13 | 完了 |
| P1 | §27.5–§27.8 | 4 | 完了 |
| P2 | §26.1–§26.8 | 8 | 完了 |
| P3 | Ch28–34 金利・測度変更 | 37 | 完了。原典入力不足の制限あり |
| P4 | Ch10–21 オプション | 112 | 完了 |
| P5 | Ch22–25 リスク・信用 | 36 | 完了 |
| P6 | Ch1–9 基礎 | 80 | 完了 |
| P7 | Ch35–37 | 16 | 完了。企業価値・原典差の制限あり |
| P8 | 監査是正・最終統合 | — | 完了 |
| **計** | **Hull 11e 全37章** | **306／306** | **未評価0・main 反映済み** |

巻の状態・章対応は [ROADMAP](ROADMAP.md)、件数は [生成台帳](docs/SECTION_LEDGER.md)、Book の登録は [_toc.yml](book/_toc.yml)、関数と検証範囲は [MODEL_INDEX](MODEL_INDEX.md) を照合した。
今後、巻・研究の追加や実装範囲の変更時は、この索引の該当行と更新日を合わせて更新する。
