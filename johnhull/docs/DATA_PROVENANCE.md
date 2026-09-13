# Beyond-Hull (vol 18–27) Data Provenance and Licensing

## Release policy

vol 18–27 の committed reference artifact は、リポジトリ内の数式・数値モデルから固定seedで生成した
小型の **synthetic data** だけである。市場データ、取引所データ、顧客データ、checkpoint、生のMonte Carlo
pathは含めない。vol 18–27 のnotebook実行、book build、新規volume page、portalはnetwork accessを
必要としない。A1–A4で使うRequireJSもMITライセンスの固定版を`book/_static/`へ同梱した。
同梱版はRequireJS 2.3.4で、原文licenseとSHA-256は`release_manifest.json`に固定している。

既存vol 1–17の数式pageは、従来からJupyter Book既定のMathJax CDNを閲覧時に使う。このlegacy依存は
`release_manifest.json`で明示的にallowlistし、vol 18–27へ新しいremote runtime依存を持ち込まない。
したがって「全legacy pageを完全offlineで数式描画できる」という主張はしない。

各reference JSONは `data_policy: synthetic-offline`、generator名、schema version、対応NPZのSHA-256を持つ。
数値は教育・再現性検証用であり、収益性、市場予測力、production readinessの根拠にはしない。
後段の Volume 26・27 の節は、この Release policy を前提とした追加の provenance 記述である。

## Optional market-data track

実市場で再検証する場合、利用者が契約・ライセンスを持つデータをignored directoryへ配置し、配布可能性を
データ提供者の条件に従って個別に確認する。Cboe、CME、ICE、取引所、vendor等のデータを本releaseから
再配布しない。optional trackの結果やcacheをcommitしない。

## Research maturity

未査読preprint由来のPDV/AFV、0DTE、signature、optimal transport、foundation model、diffusion等は
`research` trackとして扱う。core releaseは古典baseline、synthetic fixture、hard checkだけで再現でき、
research trackの失敗や未導入dependencyから独立する。

無効化されたtrackの正本は`johnhull/research_profiles.json`と、`deep_hedge_price/configs/research_*.yaml`である。
既定ではnetwork downloadもlocal checkpoint探索も行わない。

## Volume 26 inflation/JGBi reference

vol 26 の `metrics.json` と `inflation_scenarios.npz` も同じ
`synthetic-offline` 方針に従う。名目・実質curve、CPI fixing、月次seasonality、
ZCIS/YoY quote、JGBi cash flow、Jarrow–Yildirim option/Monte Carlo sample はすべて
公開 `hullkit` API と固定seedから生成し、実際の総務省CPI、財務省銘柄データ、
broker quote、顧客portfolioを含めない。

JGBi convention 実装は Japan CPI excluding fresh food を入力とするが、reference
artifact の index level は架空値である。実市場へ適用する利用者は、指数系列の
vintage/rebase、銘柄固有のbase reference date、reopening/odd coupon条件、settlement
calendar、データライセンスを別途検証する必要がある。vol 26 notebook は committed
JSON/NPZだけを読み、network access、download、training、GPU検出を行わない。

## Volume 27 risk-desk reference

vol 27 の `metrics.json` と `risk_desk_scenarios.npz` も同じ
`synthetic-offline` 方針に従う。VaR backtest 用の iid/クラスタ型 exceedance 系列、
400 回の Kupiec size study、GARCH(1,1) の日次リターンと EWMA 条件付き σ、
plain-HS/FHS の VaR forecast と violation 系列、peaks-over-threshold GPD の損失
標本と fit、5 資産の Euler 分解入力と 2000×5 の P&L 行列、Black–Scholes による
P&L explain capstone はすべて公開 `hullkit` API（`var_backtest`・`tail_risk`・
`risk_allocation`・`pnl_explain`・`risk`・`volatility`・`bsm`）と固定 seed
`20260745` から生成し、実際の市場リターン、取引所データ、顧客 portfolio、broker
quote を含めない。

reference の VaR/ES・被覆率・尾部指標は教育と integration 検証のための架空値であり、
市場較正・model performance・production risk 運用の承認ではない。実市場へ適用する
利用者は、リターン系列の分布、規制上の liquidity horizon、Basel の 250 日
multiplier schedule、限度枠設定を別途検証する必要がある。FRTB IMA（liquidity-horizon
ES 集約、stressed ES、NMRF、P&L attribution eligibility test、IMA/SA 比較）は
vol 29 候補として scope 外。vol 27 notebook は committed JSON/NPZ だけを読み、
network access、download、training、GPU 検出を行わない。

## Volume 28 credit-desk reference

vol 28 の `metrics.json` と `credit_scenarios.npz` も同じ `synthetic-offline` 方針に
従う。ハザード曲線、CDS レッグ、固定クーポン価格、CDS オプション、Gauss–Hermite
求積による CDO トランシェ、k-th-to-default、コンパウンド/ベース相関、double-t
コピュラ、CreditMetrics の格付推移 MC（100 社 × 5000 path）、ネッティング・担保・
CVA の各ブロックはすべて公開 `hullkit` API（`credit_curve`・`cds`・`credit_portfolio`・
`credit_metrics`・`xva`）と固定 seed `20260746` から生成し、実際の市場気配、
取引所データ、顧客 portfolio、broker quote を含めない。乱数を使うのは
CreditMetrics ブロックだけで、それ以外は決定的である。

Hull 11e Table 24.4（S&P 1981–2019 の 1 年格付推移行列）と Table 25.6（Creditex
の iTraxx Europe 5 年トランシェ mid 気配、2007-01-31）は教科書に印刷された
定数を転記した fixture であり、ダウンロードや再配布したベンダーデータではない。
これらは Hull の印刷値（閾値 1.2719/2.4089/2.8070、Table 25.8 の相関）を
再現するためのピンとしてだけ使う。

reference のスプレッド・相関・信用 VaR は教育と integration 検証のための値であり、
市場較正・model performance・production valuation の承認ではない。§25.11 の
double-t コピュラと不均質再帰は極限（ν→∞、均質）でのみ検証し、Hull に数値例が
ないため印刷値ピンを持たない。vol 28 notebook は committed JSON/NPZ だけを読み、
network access、download、training、GPU 検出を行わない。
