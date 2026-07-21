# JohnHull 引用論文インベントリ

調査日: 2026-07-21

この一覧は、`MODEL_INDEX.md`、`scripts/build_frontier_notebooks.py`、`hullkit` の
モジュール文書、および JohnHull の設計 spec
`docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-options.md` に明示された
学術論文を重複排除してまとめたものです。論文名を特定できない一般的な
「literature」表記、教科書、規制・商品コンベンション資料は論文数に含めていません。

## 取得状況

| 区分 | 件数 | 説明 |
|---|---:|---|
| 明示引用された論文 | 59 | 実装・教材・設計 spec の引用を重複排除 |
| 原文 PDF 取得済み | 49 | 著者・機関リポジトリ、出版社の公開コピー、arXiv/SSRN 相当を優先 |
| 原文リンクのみ | 9 | 公開 PDF を安全に取得できない、または購読・ログインが必要 |
| 書誌未解決 | 1 | `Andersen et al. (2024)` は記述だけでは一意に特定できない |
| 関連論文（引用外） | 1 | Bartlett (2006) の後続理論論文を補助資料として保存 |

PDF は `papers/` にあります。リポジトリ全体の `*.pdf` ignore 規則に従い、PDF は
ローカル資料であり Git の追跡対象外です。再配布許諾を確認できない論文もあるため、
このフォルダをそのまま公開・配布しないでください。

凡例: **PDF** = ローカル保存済み、**link** = 原文ページのみ、**unresolved** =
引用情報の修正が必要。

## 1. 実装・教材で引用された論文

### オプション評価、ボラティリティ、数値計算

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 1973 | Fischer Black; Myron Scholes | [The Pricing of Options and Corporate Liabilities](https://doi.org/10.1086/260062) | [PDF](papers/1973-black-scholes-options-corporate-liabilities.pdf) |
| 1979 | John C. Cox; Stephen A. Ross; Mark Rubinstein | [Option Pricing: A Simplified Approach](https://doi.org/10.1016/0304-405X(79)90015-1) | [PDF](papers/1979-cox-ross-rubinstein-option-pricing.pdf) |
| 2001 | Francis A. Longstaff; Eduardo S. Schwartz | [Valuing American Options by Simulation: A Simple Least-Squares Approach](https://escholarship.org/uc/item/43n1k4jb) | [PDF](papers/2001-longstaff-schwartz-american-options-lsm.pdf) |
| 1993 | Steven L. Heston | [A Closed-Form Solution for Options with Stochastic Volatility with Applications to Bond and Currency Options](https://doi.org/10.1093/rfs/6.2.327) | [PDF](papers/1993-heston-closed-form-stochastic-volatility.pdf) |
| 2008 | Fang Fang; Cornelis W. Oosterlee | [A Novel Pricing Method for European Options Based on Fourier-Cosine Series Expansions](https://doi.org/10.1137/080718061) | [PDF](papers/2008-fang-oosterlee-cos-method.pdf) |
| 2002 | Patrick S. Hagan; Deep Kumar; Andrew S. Lesniewski; Diana E. Woodward | [Managing Smile Risk](https://www.wilmott.com/managing-smile-risk/) | [PDF](papers/2002-hagan-et-al-managing-smile-risk.pdf) |
| 2015 | Alexandre Antonov; Michael Konikov; Michael Spector | [The Free Boundary SABR: Natural Extension to Negative Rates](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2557046) | [PDF](papers/2015-antonov-et-al-free-boundary-sabr.pdf) |
| 2007 | Hansjörg Albrecher; Philipp Mayer; Wim Schoutens; Jurgen Tistaert | [The Little Heston Trap](https://wwwf.imperial.ac.uk/~ajacquie/IC_Num_Methods/IC_Num_Methods_Docs/Literature/albrecher.pdf) | [PDF](papers/2007-albrecher-et-al-little-heston-trap.pdf) |
| 2010 | Roger Lord; Remmert Koekkoek; Dick van Dijk | [A Comparison of Biased Simulation Schemes for Stochastic Volatility Models](https://doi.org/10.1080/14697680802392496) | [PDF](papers/2010-lord-koekkoek-van-dijk-heston-simulation.pdf) |
| 1996 | Mark Broadie; Paul Glasserman | [Estimating Security Price Derivatives Using Simulation](https://doi.org/10.1287/mnsc.42.2.269) | [PDF](papers/1996-broadie-glasserman-security-price-derivatives.pdf) |
| 2006 | Mike Giles; Paul Glasserman | [Smoking Adjoints: Fast Monte Carlo Greeks](https://ora.ox.ac.uk/objects/uuid:f536b1a8-c988-4bda-9c5f-a322652139fd) | [PDF](papers/2006-giles-glasserman-smoking-adjoints.pdf) |
| 1976 | Fischer Black | [The Pricing of Commodity Contracts](https://doi.org/10.1016/0304-405X(76)90024-6) | **link** |
| 1900 | Louis Bachelier | [Théorie de la spéculation](https://archive.numdam.org/articles/10.24033/asens.476/) | [PDF](papers/1900-bachelier-theorie-de-la-speculation.pdf) |
| 1991 | Stuart M. Turnbull; Lee Macdonald Wakeman | [A Quick Algorithm for Pricing European Average Options](https://doi.org/10.2307/2331213) | **link** |
| 1978 | William Margrabe | [The Value of an Option to Exchange One Asset for Another](https://doi.org/10.1111/j.1540-6261.1978.tb03386.x) | [PDF](papers/1978-margrabe-exchange-option.pdf) |
| 2006 | Bruce Bartlett | [Hedging Under SABR Model](https://www.wilmott.com/hedging-under-sabr-model-wilmott-magazine-article-bruce-bartlett/) | **link**; 公開 PDF の接続がタイムアウト |

### 金利、RFR、インフレーション

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 2019 | Andrei Lyashenko; Fabio Mercurio | [Looking Forward to Backward-Looking Rates: A Modeling Framework for Term Rates Replacing LIBOR](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3330240) | [PDF](papers/2019-lyashenko-mercurio-backward-looking-rates.pdf) |
| 1990 | John Hull; Alan White | [Pricing Interest-Rate-Derivative Securities](https://doi.org/10.1093/rfs/3.4.573) | [PDF](papers/1990-hull-white-interest-rate-derivative-securities.pdf) |
| 2003 | Robert Jarrow; Yildiray Yildirim | [Pricing Treasury Inflation Protected Securities and Related Derivatives Using an HJM Model](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=585828) | **link**; Cornell 公開コピーは現在 DNS 解決不可 |

### VaR、ES、信用リスク

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 1995 | Paul H. Kupiec | [Techniques for Verifying the Accuracy of Risk Measurement Models](https://fraser.stlouisfed.org/title/finance-economics-discussion-series-1491/techniques-verifying-accuracy-risk-measurement-models-717921) | [PDF](papers/1995-kupiec-var-model-verification.pdf) |
| 1998 | Peter F. Christoffersen | [Evaluating Interval Forecasts](https://doi.org/10.2307/2527341) | **link** |
| 1999 | Giovanni Barone-Adesi; Kostas Giannopoulos; Les Vosper | [VaR Without Correlations for Portfolios of Derivative Securities](https://doc.rero.ch/record/306980) | [PDF](papers/1999-barone-adesi-giannopoulos-vosper-var-without-correlations.pdf) |
| 2000 | Alexander J. McNeil; Rüdiger Frey | [Estimation of Tail-Related Risk Measures for Heteroscedastic Financial Time Series](https://doi.org/10.1016/S0927-5398(00)00012-8) | [PDF](papers/2000-mcneil-frey-tail-risk-evt.pdf) |
| 1999/2000 | Dirk Tasche | [Risk Contributions and Performance Measurement](https://www.researchgate.net/publication/2378752_Risk_Contributions_and_Performance_Measurement) | **link** |
| 2008/2009 | Dirk Tasche | [Capital Allocation for Credit Portfolios with Kernel Estimators](https://arxiv.org/abs/math/0612470) | [PDF](papers/2008-tasche-capital-allocation-kernel-estimators.pdf) |
| 1974 | Robert C. Merton | [On the Pricing of Corporate Debt: The Risk Structure of Interest Rates](https://doi.org/10.1111/j.1540-6261.1974.tb03058.x) | [PDF: MIT 1973 working-paper版](papers/1973-merton-corporate-debt-working-paper.pdf) |
| 2002 | Oldřich Vašíček | [The Distribution of Loan Portfolio Value](https://www.risk.net/ja/node/1530287) | **link** |
| 2000 | David X. Li | [On Default Correlation: A Copula Function Approach](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=187289) | **link** |

### MLサロゲート、サーフェス、ボラティリティ予測

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 2020 | Brian Huge; Antoine Savine | [Differential Machine Learning](https://arxiv.org/abs/2005.02347) | [PDF](papers/2020-huge-savine-differential-machine-learning.pdf) |
| 2009 | Charles Dugas et al. | [Incorporating Functional Knowledge in Neural Networks](https://www.jmlr.org/papers/v10/dugas09a.html) | [PDF](papers/2009-dugas-et-al-functional-knowledge-neural-networks.pdf) |
| 2014 | Jim Gatheral; Antoine Jacquier | [Arbitrage-Free SVI Volatility Surfaces](https://arxiv.org/abs/1204.0646) | [PDF](papers/2014-gatheral-jacquier-arbitrage-free-svi.pdf) |
| 2003 | Yacine Aït-Sahalia; Jefferson Duarte | [Nonparametric Option Pricing Under Shape Restrictions](https://doi.org/10.1016/S0304-4076(03)00102-7) | [PDF](papers/2003-ait-sahalia-duarte-nonparametric-option-pricing.pdf) |
| 2019 | Christian Bayer et al. | [On Deep Calibration of (Rough) Stochastic Volatility Models](https://arxiv.org/abs/1908.08806) | [PDF](papers/2019-bayer-et-al-deep-calibration.pdf) |
| 2019 | Blanka Horvath; Aitor Muguruza; Mehdi Tomas | [Deep Learning Volatility](https://arxiv.org/abs/1901.09647) | [PDF](papers/2019-horvath-et-al-deep-learning-volatility.pdf) |
| 2016 | Christian Bayer; Peter K. Friz; Jim Gatheral | [Pricing Under Rough Volatility](https://doi.org/10.1080/14697688.2015.1099717) | [PDF](papers/2016-bayer-friz-gatheral-pricing-rough-volatility.pdf) |
| 2009 | Fulvio Corsi | [A Simple Approximate Long-Memory Model of Realized Volatility](https://doi.org/10.1093/jjfinec/nbp001) | [PDF](papers/2009-corsi-har-realized-volatility.pdf) |
| 2022 | Rafael Reisenhofer; Xandro Bayer; Nikolaus Hautsch | [HARNet: A Convolutional Neural Network for Realized Volatility Forecasting](https://arxiv.org/abs/2205.07719) | [PDF](papers/2022-reisenhofer-et-al-harnet.pdf) |
| 2011 | Andrew J. Patton | [Volatility Forecast Comparison Using Imperfect Volatility Proxies](https://doi.org/10.1016/j.jeconom.2010.03.034) | [PDF](papers/2011-patton-volatility-forecast-comparison.pdf) |
| 2019 | Sarthak Jain; Byron C. Wallace | [Attention Is Not Explanation](https://aclanthology.org/N19-1357/) | [PDF](papers/2019-jain-wallace-attention-not-explanation.pdf) |
| 2019 | Hans Bühler; Lukas Gonon; Josef Teichmann; Ben Wood | [Deep Hedging](https://arxiv.org/abs/1802.03042) | [PDF](papers/2019-buehler-et-al-deep-hedging.pdf) |

### SPX/VIX、暗号資産、気候・エネルギー、0DTE

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 2023 | Julien Guyon; Jordan Lekeufack | [Volatility Is (Mostly) Path-Dependent](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4174589) | **link** |
| 2018 | Jim Gatheral; Thibault Jaisson; Mathieu Rosenbaum | [Volatility Is Rough](https://arxiv.org/abs/1410.3394) | [PDF](papers/2018-gatheral-jaisson-rosenbaum-volatility-is-rough.pdf) |
| 2019 | Omar El Euch; Mathieu Rosenbaum | [The Characteristic Function of Rough Heston Models](https://arxiv.org/abs/1609.02108) | [PDF](papers/2019-el-euch-rosenbaum-rough-heston-characteristic-function.pdf) |
| 2022 | Eduardo Abi Jaber; Camille Illand; Shaun Li | [The Quintic Ornstein-Uhlenbeck Volatility Model That Jointly Calibrates SPX & VIX Smiles](https://arxiv.org/abs/2212.10917) | [PDF](papers/2022-abi-jaber-et-al-quintic-ou.pdf) |
| 2025 | Jaehyun Kim; Hyungbin Park | [Designing Funding Rates for Perpetual Futures in Cryptocurrency Markets](https://arxiv.org/abs/2506.08573) | [PDF](papers/2025-kim-park-perpetual-funding-rates.pdf) |
| 2022 | Jason Milionis et al. | [Automated Market Making and Loss-Versus-Rebalancing](https://arxiv.org/abs/2208.06046) | [PDF](papers/2022-milionis-et-al-amm-lvr.pdf) |
| 2002 | Peter Alaton; Boualem Djehiche; David Stillberger | [On Modelling and Pricing Weather Derivatives](https://www.math.kth.se/matstat/fofu/reports/weather.pdf) | [PDF](papers/2002-alaton-et-al-weather-derivatives.pdf) |
| 2025 | Simone Serafini; Giacomo Bormetti | [Pricing Carbon Allowance Options on Futures: Insights from High-Frequency Data](https://arxiv.org/abs/2501.17490) | [PDF](papers/2025-serafini-bormetti-carbon-options.pdf) |
| 2024 | Andersen et al. | “ultra-short-dated options” | **unresolved**; 著者・題名・識別子が不足。Andersen–Fusari–Todorov の既知論文は 2015/2017 で年が一致しない |

## 2. 設計 spec の研究候補

以下は実装の根拠として直接引用されたものではなく、JohnHull 拡張設計の研究候補です。
上の一覧と重複する候補は再掲していません。

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 2017 | Weinan E; Jiequn Han; Arnulf Jentzen | [Deep Learning-Based Numerical Methods for High-Dimensional Parabolic Partial Differential Equations and Backward Stochastic Differential Equations](https://arxiv.org/abs/1706.04702) | [PDF](papers/2017-han-jentzen-e-deep-bsde.pdf) |
| 2021 | Brian Ning et al. | [Arbitrage-Free Implied Volatility Surface Generation with Variational Autoencoders](https://arxiv.org/abs/2108.04941) | [PDF](papers/2021-ning-et-al-arbitrage-free-iv-vae.pdf) |
| 2025 | Brian Huge; Antoine Savine | [Axes That Matter: PCA with a Difference](https://arxiv.org/abs/2503.06707) | [PDF](papers/2025-huge-savine-axes-that-matter.pdf) |
| 2023 | Christa Cuchiero et al. | [Joint Calibration to SPX and VIX Options with Signature-Based Models](https://arxiv.org/abs/2301.13235) | [PDF](papers/2023-cuchiero-et-al-signature-spx-vix.pdf) |
| 2025 | Elisa Alòs et al. | [Volatility Modeling with Rough Paths: A Signature-Based Alternative to Classical Expansions](https://arxiv.org/abs/2507.23392) | [PDF](papers/2025-alos-et-al-volatility-rough-paths.pdf) |
| 2025 | Pascal François et al. | [Deep Hedging with Options Using the Implied Volatility Surface](https://arxiv.org/abs/2504.06208) | [PDF](papers/2025-francois-et-al-deep-hedging-iv-surface.pdf) |
| 2026 | Takayuki Sakuma | [Differential Machine Learning for 0DTE Options with Stochastic Volatility and Jumps](https://arxiv.org/abs/2603.07600) | [PDF](papers/2026-sakuma-dml-0dte.pdf) |
| 2026 | Alessio Brini | [Forecasting Realized Volatility with Time Series Foundation Models: A Comparison with Econometric Benchmarks](https://arxiv.org/abs/2607.05291) | [PDF](papers/2026-brini-volatility-foundation-models.pdf) |
| 2026 | Charlie Che et al. | [SPX-VIX Risk Computations Via Perturbed Optimal Transport](https://arxiv.org/abs/2603.10857) | [PDF](papers/2026-che-et-al-spx-vix-transport.pdf) |
| 2026 | Philip Z. Maymin | [Option Pricing on Automated Market Maker Tokens](https://arxiv.org/abs/2603.29763) | [PDF](papers/2026-maymin-amm-token-options.pdf) |

## 3. 補助資料

`Bartlett (2006)` の原文とは別に、同じデルタを理論的に扱う後続論文を保存しています。

| 年 | 著者 | 論文 | 状態 |
|---:|---|---|---|
| 2017 | Patrick S. Hagan; Andrew Lesniewski | [Bartlett's Delta in the SABR Model](https://arxiv.org/abs/1704.03110) | [PDF](papers/2017-hagan-lesniewski-bartlett-delta.pdf) |

## 4. 論文一覧から除外した参考資料

次はレポ内で参照されていますが、学術論文ではないため上の 59 件には含めていません。

- 教科書・専門書: Hull; Glasserman; Gatheral; Bergomi; Benth & Benth;
  McNeil–Frey–Embrechts; López de Prado; Kloeden & Platen; Wilmott; Duffy;
  Green; Gregory
- 規制・市場資料: BCBS (1996); RiskMetrics; ARRC RFR conventions;
  ISDA fallbacks; Ministry of Finance Japan JGBi conventions
- 一般的な引用だけで一意に特定できないもの: scheduled-jump literature;
  perpetual-swap funding literature; energy PPA literature

## 5. 既知の書誌上の注意

1. `Andersen et al. (2024), ultra-short-dated options` は一致する論文を特定できません。
   著者フルネーム、題名、DOI/SSRN のいずれかをコード側に追加する必要があります。
2. `Bartlett (2006)` は Bruce Bartlett の *Hedging Under SABR Model* です。
   Hagan & Lesniewski (2017) *Bartlett's Delta in the SABR Model* とは別論文です。
3. `Bayer–Friz–Gatheral (2016)` は *Pricing Under Rough Volatility* です。
   arXiv:1507.03004 *Hybrid Scheme for Brownian Semistationary Processes* ではありません。
4. Merton のローカル PDF は、1974 年の雑誌版に先行する同題の MIT 1973 working paper です。

## 6. AI向け変換

代表的な5論文を Markdown、ページ単位 JSONL、検索用チャンクへ変換するには、
workspace root で次を実行します。PyMuPDF4LLM は一時依存として実行され、
`pyproject.toml` や lockfile は変更しません。

```bash
uv run --no-project --with pymupdf4llm \
  python johnhull/scripts/build_paper_corpus.py --sample
```

品質レポートを確認してから全PDFを変換します。

```bash
uv run --no-project --with pymupdf4llm \
  python johnhull/scripts/build_paper_corpus.py --all
```

中断後の再開や書誌情報だけを更新した場合は、検証済みの個別成果物を再利用して
全体インデックスを再構築できます。元PDF、変換器バージョン、変換条件、書誌情報の
いずれかが変わった論文だけが再変換されます。

```bash
uv run --no-project --with pymupdf4llm \
  python johnhull/scripts/build_paper_corpus.py --all --resume
```

生成物は `references/processed/` に保存されます。各論文には `paper.md`、
`metadata.json`、`pages.jsonl`、`chunks.jsonl`、`quality.json`、図表画像が含まれ、
全体には `index.json`、`corpus.jsonl`、`quality_report.md` が生成されます。
`references/processed/` は検索・引用にすぐ利用できるようGit管理しています。論文本文と
図表の派生物を含むため、公開・再配布時は各原論文のライセンスを確認してください。

### 全件変換結果（2026-07-22）

ローカル保存済みの50 PDFを全件変換し、1,536ページ、780検索用チャンクを生成しました。
元PDFと抽出ページ数は全件一致し、空ページ、変換失敗、重複チャンクIDはありません。

品質ゲートは `pass` 1件、`review` 49件、`fail` 0件です。`review` の主因は数式が
LaTeXではなく参照可能な画像として抽出されることです。本文検索とページ引用には利用
できますが、数式を厳密に扱う場合は画像を読めるマルチモーダルモデルを使用するか、
Marker等による数式OCRを追加してください。

McNeil–Frey (2000)、Aït-Sahalia–Duarte (2003)、Antonov et al. (2015)、
Huge–Savine (2025) は、元PDFの埋め込みフォントに由来する置換文字率が高いため、
本文を引用する際に原ページ画像との照合が必要です。PyMuPDF4LLMの強制OCRでは改善
しなかったため、別OCRエンジンによる補正を後続課題とします。
