# 外部資料の検証記録：S001–S031

- 作成日：2026-09-27（各記録の `accessed_at` はすべて 2026-09-27）
- 対象：`docs/RESEARCH_HANDOFF_2026-09-27.md` §13 の S001–S031。記録様式は同文書 §11.2 に従う。
- 状態：**31件すべてに調査結果を記録**。支持・部分確認を区別し、未読の範囲と再現未実施を残す。調査記録の完了は全主張の検証完了ではない。
- 判定の集計：`verified_supports_claim` 10件、`verified_partial` 21件（各YAMLの全体判定から集計）。前者も実験性能の独立再現を意味しない。
- 来歴：中断前の担当の取得・書誌・実測記録を保持し、再開後にwebで一次資料を確認して未記入項目を補った。S002の2式は原PDF画像でも確認。
- 方法（中断前の取得記録を含む）：
  - arXiv：abs ページから題名・著者・版履歴・ライセンスを取得し、最新版 PDF を版を固定した URL（例：`https://arxiv.org/pdf/2512.05301v2`）で保存して `pdftotext` で本文を読んだ。arXiv API は HTTP 406 を返したため使っていない。
  - DOI：Crossref API（`https://api.crossref.org/works/<DOI>`）で題名・著者・巻号・頁・公開日・ライセンス欄を確認した。
  - HTML：中断前はWebFetchとcurl/BeautifulSoup、再開後はwebツールと公開APIも用いて本文を確認した。
  - 公的機関・運用会社の PDF：公式サイトから取得し `pdftotext` で読んだ。
- 制約：
  - 判定は abstract・序論・主要節など、実際に読んだ範囲（各 `locator` に記載）で行った。証明の検算・数値実験の再現はしていない。したがって `independent_validation_of_outcome` は原則 `unknown`。
  - Cloudflare 等で機械取得を拒否されたページは、ログイン・フォーム送信・有料壁の回避をせず、その旨を記録した。
  - 企業・取引所・運用会社の資料は、原文を確認しても「当事者の説明」という証拠の性格は変わらない。
- PDF の保存先：`/home/kazumasa/projects/tmp/johnhull-prep/papers/`（git 無視。公開 repo には入れない）。

## 要約表

| ID | 検証後の題名 | 著者・発行 | 日付（版） | 種別 | アクセス | 判定 | 保存した PDF | 訂正 |
|---|---|---|---|---|---|---|---|---|
| [S001](#s001) | Primal-Dual Simulation Algorithm for Pricing Multidimensional American Options | Leif Andersen, Mark Broadie | 2004-09-01 | paper | open_author_copy | verified_supports_claim | — | 詳細は各記録 |
| [S002](#s002) | Differential ML with a Difference | Paul Glasserman, Siddharth Hemant Karmarkar | 2026-04-22 | preprint | open | verified_partial | S002_differential-ml-with-a-difference.pdf（git 管理外） | 詳細は各記録 |
| [S003](#s003) | Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem | Marc Henrard | 2011-11-01 | research_note | open | verified_supports_claim | — | 詳細は各記録 |
| [S004](#s004) | Multilevel Monte Carlo Path Simulation | Michael B. Giles | 2008-05/06 | paper | open_author_copy | verified_supports_claim | — | 詳細は各記録 |
| [S005](#s005) | How the U.S. Treasury futures market and the basis trade could be affected by the Treasury clearing mandate: Part 1—A primer | Ketan B. Patel（senior policy advisor and head of financial markets risk analysis）, Federal Reserve Bank of Chicago | 2026-01（Chicago Fed Letter, January 2026, Number 516） | article | 各記録 | verified_partial | — | 詳細は各記録 |
| [S006](#s006) | How sensitive is the Treasury cash-futures basis trade to funding condition shifts? | Srini Ramaswamy, Hugo De Vere, Matthew McCormick, Seth Searls（Research Department, Federal Reserve Bank of Dallas） | 2025-07-15 | article | 各記録 | verified_partial | — | 詳細は各記録 |
| [S007](#s007) | Pricing the Term Structure with Linear Regressions | Tobias Adrian, Richard K. Crump, Emanuel Moench（Federal Reserve Bank of New York） | 2013-04（Revised April 2013。PDF の作成日も 2013-04-12 JST） | preprint | 各記録 | verified_partial | — | 詳細は各記録 |
| [S008](#s008) | Perpetual Futures Pricing | Damien Ackerer; Julien Hugonnier; Urban Jermann | 2024-09-03（確認した著者稿） | paper | open | verified_partial | — | 詳細は各記録 |
| [S009](#s009) | Multi-Curve Approach to Cross-Currency Basis Swaps Referencing Backward-Looking Term Rates | Yining Ding; Ruyi Liu; Marek Rutkowski | 2025-11-16 | preprint | open | verified_partial | S009_xccy-basis-swaps-backward-looking-rates.pdf | 詳細は各記録 |
| [S010](#s010) | The rise and risks of synthetic risk transfers | Prashant R Babu（Bank of England）, Michael Chui（BIS）, Costas Stephanou（BIS）。BIS Quarterly Review, March 2026 | 2026-03-16（記事ページの表示。WebFetch で確認） | article | 各記録 | verified_supports_claim | — | 詳細は各記録 |
| [S011](#s011) | 0DTEs Decoded: Positioning, Trends, and Market Impact（副題 Retail and Institutional Trends in SPX® 0DTE Options） | Mandy Xu（VP, Head of Derivatives Market Intelligence）, Cboe Exchange, Inc.。分析協力は Cboe Data and Analytics team | 2025-05-02 | article | 各記録 | verified_partial | — | 詳細は各記録 |
| [S012](#s012) | Box Spreads: What They Are and How to Use Them（HTML の title 要素は 'What Are Box Spreads? / Charles Schwab'） | Joe Mazzola, Charles Schwab & Co., Inc. | 2025-11-20 | article | 各記録 | verified_supports_claim | — | 詳細は各記録 |
| [S013](#s013) | Global X Nikkei 225 Covered Call ETF (option premium reinvestment type)（証券コード 2858、ISIN JP3049650009） | Global X Japan Co. Ltd.（大和証券グループ本社・大和アセットマネジメント・Global X Management Company の合弁） | 商品ページは 2026-09-25 時点のデータ、ファクトシートは 2026-08-31 時点（PDF 作成 2026-09-01） | product | 各記録 | verified_partial | — | 詳細は各記録 |
| [S014](#s014) | Neural Calibration of a Complete Market Model | Andrea Molent; Michel Vellekoop | 2026-08-31 | preprint | open | verified_partial | S014_neural-calibration-complete-market-model.pdf | 詳細は各記録 |
| [S015](#s015) | Microstructural Foundation of Rough Log-Normal Volatility Models | Paul P. Hager; Ulrich Horst; Thomas Wagenhofer; Wei Xu | 2026-03-13 | preprint | open | verified_partial | S015_microstructural-rough-lognormal-vol.pdf | 詳細は各記録 |
| [S016](#s016) | Cross-Currency Heath-Jarrow-Morton Framework in the Multiple-Curve Setting | Alessandro Gnoatto; Silvia Lavagnini | 2026-03-04 | preprint | open | verified_partial | S016_xccy-hjm-multiple-curve.pdf | 詳細は各記録 |
| [S017](#s017) | Electricity 2026 — Prices | International Energy Agency | 2026（日付は本ページでは未特定） | report | open | verified_partial | — | 詳細は各記録 |
| [S018](#s018) | Uncertainty-Aware Deep Hedging | Manan Poddar | 2026-03-10 | preprint | open | verified_partial | S018_uncertainty-aware-deep-hedging.pdf | 詳細は各記録 |
| [S019](#s019) | How Likely Is an Inflation Disaster? | Jens Hilscher（UC Davis）, Alon Raviv（Bar-Ilan University）, Ricardo Reis（LSE） | 受付 2022-04-27、編集判断 2025-01-26、Advance Access 2025-10-28（PDF の表記）。リポジトリの published_online は 2025-11-16 と記録されており、PDF 表記と一致しない | paper | 各記録 | verified_supports_claim | — | 詳細は各記録 |
| [S020](#s020) | Empirical Bernstein and betting confidence intervals for randomized quasi-Monte Carlo | Aadit Jain; Fred J. Hickernell; Art B. Owen; Aleksei G. Sorokin | 2026-03-06 | paper | abstract_only | verified_partial | — | 詳細は各記録 |
| [S021](#s021) | Empirical Bernstein and betting confidence intervals for randomized quasi-Monte Carlo | Aadit Jain; Fred J. Hickernell; Art B. Owen; Aleksei G. Sorokin | 2026-02-02 | preprint | open | verified_supports_claim | S021_rqmc-bernstein-betting-ci.pdf | 詳細は各記録 |
| [S022](#s022) | E-backtesting | Qiuqi Wang; Ruodu Wang; Johanna Ziegel | 2025-09-23 | paper | abstract_only | verified_partial | — | 詳細は各記録 |
| [S023](#s023) | E-backtesting | Qiuqi Wang; Ruodu Wang; Johanna Ziegel | 2026-04-15 | preprint | open | verified_supports_claim | S023_e-backtesting.pdf | 詳細は各記録 |
| [S024](#s024) | Rethinking Synthetic Scenario Realism: Compatibility, Not Fidelity, Drives Hedging Performance | Ryuji Hashimoto; Masanori Hirano; Ryota Ozaki; Kentaro Imajo | 2026-09-04 | preprint | open | verified_partial | S024_scenario-realism-hedging-compatibility.pdf | 詳細は各記録 |
| [S025](#s025) | GS Finance Corp. Autocallable Equity-Linked Notes — preliminary prospectus supplement | GS Finance Corp.; guarantor The Goldman Sachs Group, Inc. | 2026-02-04 | filing | open | verified_supports_claim | — | 詳細は各記録 |
| [S026](#s026) | Global Multi-Maturity SPX–VIX Calibration Beyond Markovian Stitching | Atithi Acharya; Yue Sun; Brandon Augustino; Shouvanik Chakrabarti; Shree Hari Sureshbabu; Charlie Che | 2026-09-03 | preprint | open | verified_partial | S026_spx-vix-multi-maturity-calibration.pdf | 詳細は各記録 |
| [S027](#s027) | Analytic Pricing of SOFR Futures Contracts with Smile and Skew | Aurelio Romero-Bermúdez; Colin Turfus | 2024-04-12 | preprint | open | verified_partial | S027_sofr-futures-smile-skew.pdf | 詳細は各記録 |
| [S028](#s028) | Real Options Valuation of Battery Energy Storage Systems in Continental Europe’s Day-Ahead and FCR Markets | Luis van Sandbergen; Richard Biegler-König | 2026 | conference_paper | metadata_only | verified_partial | — | 詳細は各記録 |
| [S029](#s029) | The VIX-Derived Volatility Model: A VIX-first Joint SPX-VIX Framework | Nicola F. Zaugg; Lech A. Grzelak | 2026-08-02 | preprint | open | verified_partial | S029_vix-derived-volatility-model.pdf | 詳細は各記録 |
| [S030](#s030) | Pricing and hedging for liquidity provision in Constant Function Market Making | Jimmy Risk; Shen-Ning Tung; Tai-Ho Wang | 2026-03-02 | preprint | open | verified_partial | S030_cfmm-lp-pricing-hedging.pdf | 詳細は各記録 |
| [S031](#s031) | web-inflationdistributions — Market-Based Risk-Neutral Probability Densities for Future Inflation | GitHub organization R2RsquaredLSE（README の著者表記は Jens Hilscher, Alon Raviv, Ricardo Reis） | 最終 push 2026-05-22T11:10:21Z | dataset | 各記録 | verified_supports_claim | — | 詳細は各記録 |

## 各資料の記録

<a id="s001"></a>
### S001

```yaml
source_id: S001
url_in_conversation: https://pubsonline.informs.org/doi/10.1287/mnsc.1040.0258
resolved_url: https://www.columbia.edu/~mnb2/broadie/Assets/primal_dual_ms_2004.pdf
claimed_title_and_date: Andersen–Broadie、American option の primal–dual 法、2004年
verified_title: Primal-Dual Simulation Algorithm for Pricing Multidimensional American Options
verified_authors_or_organization: Leif Andersen, Mark Broadie
publication_date: 2004-09-01
revision_date: null
version_or_commit: Management Science 50(9), 1222–1234; DOI 10.1287/mnsc.1040.0258
accessed_at: 2026-09-27
source_type: paper
verification_status: verified_supports_claim
claims:
  - claim: 行使方策の下界と双対上界を組み合わせられる
    support_status: verified_supports_claim
    locator: §2 pp.1224–1225、§3 pp.1225–1229
    quotation_or_paraphrase: 下界方策に対応する条件付き期待値を入れ子のシミュレーションで評価し、マルチンゲールの双対表現から上界を得る。
    assumptions_and_limits: 有限の行使日集合、必要な可積分性、適切な条件付き推定。連続行使への時間格子誤差は別。標本上の最大値だけでは双対上界にならない。
independent_validation_of_outcome: 未再現。本文と成立条件を確認した段階。
license_and_redistribution: 著者サイトで閲覧可能。©2004 INFORMS。再配布許諾は未確認のためリンクと短い要約のみ。
corrections_to_conversation: 論文の計算時間比は当該実装の結果で、RB-F02 の費用保証ではない。
access: open_author_copy
saved_pdf: null
```

<a id="s002"></a>
### S002

```yaml
source_id: S002
url_in_conversation: https://arxiv.org/abs/2512.05301
resolved_url: https://arxiv.org/html/2512.05301v2
claimed_title_and_date: Differential ML with a Difference、2026年改訂
verified_title: Differential ML with a Difference
verified_authors_or_organization: Paul Glasserman, Siddharth Hemant Karmarkar
publication_date: 2025-12-04
revision_date: 2026-04-22
version_or_commit: arXiv 2512.05301v2。本文は November 2025, revised April 2026。
accessed_at: 2026-09-27
source_type: preprint
verification_status: verified_partial
claims:
  - claim: 不連続 payoff の教師に LRM を使い DML を構成できる
    support_status: verified_supports_claim
    locator: §3 digital・basket・discrete barrier、§4 gamma
    quotation_or_paraphrase: デジタルの経路微分はほとんど至る所でゼロになり、LRM 教師と価格教師の併用を検討している。
    assumptions_and_limits: 教師の不偏性は密度の微分と積分の交換等が成立する場合。短期の LRM 分散と教師生成費用を含む比較が必要。著者のネットワーク実験は未再現。
  - claim: 論文の式をそのまま実装に転記できる
    support_status: contradicted
    locator: 原PDF p.3 式(3)、p.8 式(18)。両ページを画像化して目視確認。
    quotation_or_paraphrase: GBM 指数のドリフトに 1/2 がなく、対数正規密度の分母も終値 s ではなく初値 x になっている。抽出時の文字崩れではない。
    assumptions_and_limits: 後続の標準的な d2・LRM スコアとの不整合。数値実験まで誤っているかは著者コード未照合のため不明。
independent_validation_of_outcome: 教師式は標準的 GBM の密度から独立導出。論文の学習結果は未再現。
license_and_redistribution: arXiv non-exclusive license。第三者への一般的な再配布許諾ではない。本文・図をリポジトリに収録しない。
corrections_to_conversation: 最新確認版は v2。式の注意点を RB-F05 設計へ反映。
access: open
saved_pdf: S002_differential-ml-with-a-difference.pdf（git 管理外）
```

独立に使う式は $S_T=x\exp((r-\sigma^2/2)T+\sigma\sqrt{T}Z)$、
$p(s;x)=\phi(z)/(s\sigma\sqrt{T})$、$\partial_x\log p=Z/(x\sigma\sqrt{T})$。
密度を初値で微分する際は終値 $s$ を固定する。

<a id="s003"></a>
### S003

```yaml
source_id: S003
url_in_conversation: https://quant.opengamma.io/Adjoint-Algorithmic-Differentiation-OpenGamma.pdf
resolved_url: https://quant.opengamma.io/Adjoint-Algorithmic-Differentiation-OpenGamma.pdf
claimed_title_and_date: Henrard、較正を含む感応度、2011年
verified_title: "Adjoint Algorithmic Differentiation: Calibration and Implicit Function Theorem"
verified_authors_or_organization: Marc Henrard
publication_date: 2011-01-01
revision_date: 2011-11-01
version_or_commit: PDF 第1頁に記載の改訂版、全8頁
accessed_at: 2026-09-27
source_type: research_note
verification_status: verified_supports_claim
claims:
  - claim: 較正方程式を陰関数として微分し、ソルバーの反復自体の微分を避けられる
    support_status: verified_supports_claim
    locator: pp.2–5、§2–3、式(1)とその後の曲線・モデル感応度
    quotation_or_paraphrase: 残差のパラメータ微分が可逆で、各関数が微分可能な近傍で成立する。価格が曲線に直接依存する項も含む。
    assumptions_and_limits: 自由度と較正商品の数を揃える。過剰パラメータは構造的制約で自由度を減らす。非正方最小二乗への一般解法は示していない。
  - claim: 較正を含む感応度の計算費用を抑えられる
    support_status: verified_partial
    locator: §4、Table 1–2
    quotation_or_paraphrase: HW cash swaption と amortising LMM swaption の当該実装で比較している。
    assumptions_and_limits: 著者の実装・機器・商品での結果で、RB-F07 の速度保証ではない。
independent_validation_of_outcome: unknown
license_and_redistribution: このPDFに再配布許諾を確認できず。リンクと短い要約のみ、本文・図は収録しない。
corrections_to_conversation: 2011年は正しい。正方・局所可逆という条件を明記する。
access: open
saved_pdf: null
```

RB-F07 はこの成立条件を満たす v1 から始める。式の照合はできたが、論文の速度実験は再現していない。

<a id="s004"></a>
### S004

```yaml
source_id: S004
url_in_conversation: https://people.maths.ox.ac.uk/gilesm/files/OPRE_2008.pdf
resolved_url: https://people.maths.ox.ac.uk/gilesm/files/OPRE_2008.pdf
claimed_title_and_date: Giles、MLMC、2008年
verified_title: Multilevel Monte Carlo Path Simulation
verified_authors_or_organization: Michael B. Giles
publication_date: 2008-05/06
revision_date: null
version_or_commit: Operations Research 56(3), 607–617; DOI 10.1287/opre.1070.0496
accessed_at: 2026-09-27
source_type: paper
verification_status: verified_supports_claim
claims:
  - claim: 粗密差の分散を利用し必要な精度の計算費用を減らせる
    support_status: verified_supports_claim
    locator: Theorem 3.1 p.609、§4
    quotation_or_paraphrase: 独立なレベル推定量、弱誤差 h^alpha、差分分散 h^beta、経路費用 h^-1 を前提に費用を評価する。同一レベル内の粗密経路は Brownian 増分を共有する。
    assumptions_and_limits: Euler の Lipschitz payoff で beta=1 の例は費用 O(epsilon^-2 log² epsilon)。すべての payoff・離散化に共通の速度ではなく、digital 等は別に収束率を確かめる。
independent_validation_of_outcome: 著者の速度実験は未再現。RB-F08 で pilot と本計算を分けて確認する予定。
license_and_redistribution: 著者サイトで閲覧可能。INFORMS の著作物で再配布許諾未確認。
corrections_to_conversation: bias 推定の停止則と真の誤差保証を区別する。
access: open_author_copy
saved_pdf: null
```

<a id="s005"></a>
### S005

```yaml
source_id: "S005"
url_in_conversation: "https://www.chicagofed.org/publications/chicago-fed-letter/2026/516"
resolved_url: "https://www.chicagofed.org/publications/chicago-fed-letter/2026/516（PDF: https://www.chicagofed.org/-/media/publications/chicago-fed-letter/2026/cfl516.pdf?sc_lang=en）"
claimed_title_and_date: "Chicago Fed Letter：Treasury futures／basis tradeの解説（No.516）、2026年"
verified_title: "How the U.S. Treasury futures market and the basis trade could be affected by the Treasury clearing mandate: Part 1—A primer"
verified_authors_or_organization: "Ketan B. Patel（senior policy advisor and head of financial markets risk analysis）, Federal Reserve Bank of Chicago"
publication_date: "2026-01（Chicago Fed Letter, January 2026, Number 516）"
revision_date: null
version_or_commit: "DOI 10.21033/cfl-2026-516。PDF の CreationDate 2026-01-10、ModDate 2026-01-14（JST表示）"
accessed_at: "2026-09-27"
source_type: "article"
verification_status: verified_partial
claims:
  - claim: "Treasury futures の参加者（長期側＝asset managers、短期側＝leveraged funds）と、basis trade が asset managers の先物需要を現物の流動性へ変換する構造"
    support_status: verified_supports_claim
    locator: "PDF p.1–4（序論、'Who typically goes long/short on Treasury futures contracts?'、図1・図2）"
    quotation_or_paraphrase: "asset managers の先物ロングは 2008 年以降拡大し 1兆ドル超。leveraged funds（CFTC 定義で typically hedge funds and various types of money managers）が先物を売り、現物買いでヘッジする。"
    population_market_period: "CFTC Commitments of Traders（Bloomberg 経由、週次 2006-06-13〜2025-05-27）、米国債 ETF の AUM（月次 2006-05〜2025-05）"
    assumptions_and_limits: "basis trade の規模（2025年5月時点で名目1兆ドル超）は leveraged funds の先物ショートを代理変数にした筆者推計。両者の建玉は参加者の一部しか表さない。"
  - claim: "CTD、conversion factor、物理受渡し、満期での現物と先物の収束"
    support_status: verified_supports_claim
    locator: "PDF p.2（'What are Treasury futures?'）、注12"
    quotation_or_paraphrase: "受渡可能銘柄の中で conversion factor 調整後も最も安く渡せるものが CTD。受渡しがあるため満期で CTD と先物の価格は収束する（注12）。"
    population_market_period: null
    assumptions_and_limits: "delivery option（銘柄・時期の選択権）の評価には踏み込んでいない。"
  - claim: "basis trade のレバレッジと担保（本文は当初証拠金 1〜3% とレバレッジ 33:1〜99:1 を対応させるが、定義との計算不整合あり）"
    support_status: verified_partial
    locator: "PDF p.6（'How are leverage and collateral currently involved in the basis trading strategy?'）、注15・注16、図3（10年先物と CTD×CF、日次 2016-07-01〜2024-04-30）"
    quotation_or_paraphrase: "筆者は先物の当初証拠金を契約価値の 1〜3%、レバレッジを 33:1〜99:1 と記す。同一仲介業者が両脚を管理する場合、repo の haircut を求めないことがあると説明する。レバレッジの対応数値は下記の独立算術と一致しない。"
    population_market_period: "図3は Bloomberg の日次データ 2016-07-01〜2024-04-30"
    assumptions_and_limits: "注15の総建玉÷当初証拠金なら、比率 m=0.01〜0.03 に対し 1/m=33.33…〜100。純借入相当÷自己資本なら (1-m)/m=32.33…〜99。本文の33〜99は両定義を混ぜずには得られない。図3のCTD×CFという記述も標準の受渡価格式と逆向きで、元データ未取得のため図自体の正否は未判定。変動証拠金の定量分析とPart 2は本記録の範囲外。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "PDF末尾：非営利かつ出典明記なら全部または一部の転載可。その他の再配布・二次的著作物の作成は事前の書面許可が必要。© 2026 Federal Reserve Bank of Chicago。"
corrections_to_conversation:
  - "正式題名は清算義務化（SEC の Treasury clearing mandate）シリーズの第1部 'Part 1—A primer'。会話の説明名『Treasury futures／basis tradeの解説』は内容としては合っているが題名ではない。"
  - "公表は 2026年1月（会話記載『2026年』と矛盾しないが月まで特定できた）。"
  - "Part 2（cross-margining と当初証拠金の増加）が別号で続く構成。Part 2 の号数・URL は未確認。"
  - "図3の説明はPDF p.5とHTMLの両方でCTD終値にCFを掛けると記す。一方、CMEの公式受渡規約は先物決済値にCFを掛ける。原典の記述と独立に確認した規約を分け、図の元データ変換は未確認とする。"
```

実装者向けメモ：図3の説明を価格式へ転記しない。同一額面当たりの標準の受渡請求価格は `F×CF + AI`（AIは受渡時の経過利息）。gross basis は同一時点の clean CTD price と `F×CF` の差、先物価格単位なら `clean CTD price/CF − F` で比較する。通貨額には契約額面の倍率も必要。根拠は [CMEのconversion factor説明](https://www.cmegroup.com/trading/interest-rates/us-treasury-futures-conversion-factor-lookup-tables.html)。carry・クーポン・repoを含むnet basisは別計算。本文の図の元データを得るまでは、グラフ自体の誤りと断定しない。レバレッジ教材では総建玉と純借入相当の定義を分け、途中の変動証拠金による資金需要も別に扱う。

<a id="s006"></a>
### S006

```yaml
source_id: "S006"
url_in_conversation: "https://www.dallasfed.org/research/economics/2025/0715"
resolved_url: "https://www.dallasfed.org/research/economics/2025/0715"
claimed_title_and_date: "Dallas Fed：basis tradeと資金調達条件の分析、2025-07-15"
verified_title: "How sensitive is the Treasury cash-futures basis trade to funding condition shifts?"
verified_authors_or_organization: "Srini Ramaswamy, Hugo De Vere, Matthew McCormick, Seth Searls（Research Department, Federal Reserve Bank of Dallas）"
publication_date: "2025-07-15"
revision_date: null
version_or_commit: "Dallas Fed Economics（HTML記事。PDF版のリンクは本文中に見当たらない）"
accessed_at: "2026-09-27"
source_type: "article"
verification_status: verified_partial
claims:
  - claim: "最終損益と途中の証拠金・資金需要の違い"
    support_status: verified_partial
    locator: "本文 'We examine some key risk exposures embedded in the basis trade (excluding margin-related risks)…' の段落、および 'Risk factors in a Treasury cash-futures basis trade' 節"
    quotation_or_paraphrase: "記事は margin 関連のリスクを明示的に分析対象から外している。扱うのは資金調達金利と仲介能力への感応度。carry そのものはリターンに寄与せず（carry の変化は寄与しうる）、未ヘッジの資金調達リスクは受渡しまで最長3か月に限られる、と説明する。"
    population_market_period: "2020年3月（パンデミック）と 2025年4月（関税発表後）の二つの局面を対比"
    assumptions_and_limits: "途中の変動証拠金・追証による資金需要は本記事の範囲外。教材でこの論点を扱うなら別資料が必要。"
  - claim: "repo 金利ショックへの basis の感応度"
    support_status: verified_supports_claim
    locator: "本文 Chart 4 周辺の段落"
    quotation_or_paraphrase: "受渡しまで3か月の最長ケースでも、repo 金利が 40〜50bp 上がって basis が約3 tick（1/32 単位、想定元本の約10bp）動く程度。主要6限月の net basis の月次ボラティリティ（過去5年の日次変化の標準偏差を1か月に換算）も約3 tick。"
    population_market_period: "主要6つの Treasury 先物、過去5年"
    assumptions_and_limits: "3 tick が de-risking の引き金の下限という判断は著者の解釈。"
  - claim: "資金調達金利より仲介能力（dealer の balance sheet と repo 供給）の低下の方が basis 取引を不安定にする"
    support_status: verified_supports_claim
    locator: "本文 'Intermediation capacity matters more than financing rates' 節、Chart 5"
    quotation_or_paraphrase: "implied repo と実際の term repo の乖離を仲介制約の兆候とみなす。2020年3月には 6月限5年ノート先物で両者の差が 50bp 拡大した。2025年4月にはこの上昇が見られなかった。"
    population_market_period: "2020年3月、2025年4月"
    assumptions_and_limits: "『安定の理由』は 'likely' と書かれた解釈で、因果の識別はしていない。図の元データ（Chart data リンク）は開いていない＝図の出典・期間は未確認。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "本文テキストに転載条件の記載は見当たらない（未確認）。『views are those of the authors…』の免責あり。"
corrections_to_conversation:
  - "会話の用途『最終損益と途中の証拠金・資金需要の違い』のうち証拠金の部分は、記事自身が対象外と明記している。支持されるのは資金調達金利と仲介能力への感応度の部分だけ。"
```

実装者向けメモ：記事中の implied repo の定義式は「先物価格×CF＝CTD 現物価格−（経過利息−implied repo での資金コスト）」という形で示されている。教材で implied repo と実 repo の乖離を指標にするなら、CF・経過利息・受渡日の扱いを Hull 第6章の式と突き合わせてから使うこと（記事は説明のため CF=1 と置くよう読者に勧めている）。

<a id="s007"></a>
### S007

```yaml
source_id: "S007"
url_in_conversation: "https://www.newyorkfed.org/research/staff_reports/sr340.html"
resolved_url: "https://www.newyorkfed.org/research/staff_reports/sr340.html（PDF: https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr340.pdf）"
claimed_title_and_date: "NY Fed Staff Report 340：ACM term-premium研究（継続利用できる既存研究）"
verified_title: "Pricing the Term Structure with Linear Regressions"
verified_authors_or_organization: "Tobias Adrian, Richard K. Crump, Emanuel Moench（Federal Reserve Bank of New York）"
publication_date: "2008-08（Staff Report No. 340）"
revision_date: "2013-04（Revised April 2013。PDF の作成日も 2013-04-12 JST）"
version_or_commit: "改訂版 2013-04。掲載誌：Journal of Financial Economics 110(1), 2013-10, pp.110–138（NY Fed の書誌ページの記載。誌側の DOI は未照合）"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_partial
claims:
  - claim: "期待短期金利と term premium を分けるモデル（P と Q の違い）"
    support_status: verified_supports_claim
    locator: "PDF §2.2 Estimation（式14–17の3段階回帰）、§2.4 末尾（式25–26 で λ0=λ1=0 と置く）、§3.1 Data"
    quotation_or_paraphrase: "価格付け因子の VAR（第1段）、超過リターンを定数・前期因子・当期の因子イノベーションに回帰（第2段）、断面回帰で risk price λ0, λ1 を推定（第3段）。本文はλ0=λ1=0の再帰利回りをrisk-neutral yieldと呼び、平均期待短期金利に対応させる。ただし式25には凸性項が残り、両者の厳密な等号には下記の補正が必要。"
    population_market_period: "GSW（Gürkaynak–Sack–Wright 2007）ゼロクーポン利回り 3〜120か月、月次 1987:01–2011:12（T=300）。基準モデルは利回りの主成分5つ"
    assumptions_and_limits: "ガウス型アフィン期間構造。リスク価格をゼロにしても式25の B'ΣB/2 とリターン誤差分散 σ²/2 は残る。厳密なP測度の平均期待短期金利と区別し、分解の凸性・誤差の配分規約を固定する。現在公開されるACM系列と本論文の推定窓・仕様の同一性は未確認。"
  - claim: "データ配布ページ、更新日、vintage"
    support_status: not_yet_checked
    locator: "https://www.newyorkfed.org/research/data_indicators/term-premia-tabs（WebFetch では JavaScript 描画のため中身を取得できず）"
    quotation_or_paraphrase: null
    population_market_period: null
    assumptions_and_limits: "ダウンロードファイルの URL・更新頻度・過去値の改訂の有無は未確認。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "Staff Report の表紙：議論のための予備的成果として配布。明示的な再配布ライセンスの記載は確認していない。"
corrections_to_conversation:
  - "正式題名は 'Pricing the Term Structure with Linear Regressions'（会話の『ACM term-premium研究』は通称）。2008年初出、2013年4月改訂、JFE 2013年10月号掲載。"
  - "論文の 'risk-neutral yield' はリスク価格をゼロにした反実仮想の再帰利回りという命名。λをゼロにすると因子のPと価格付け動学は一致するが、対数債券価格から得る利回りにはJensenの凸性が残る。Pの平均期待短期金利と無条件に同一視しない。"
```

実装者向けメモ：第2段の回帰式は式14（`rx = a ι' + β' V̂ + c X_- + E`）、第3段の推定量は式16（λ0）と式17（λ1）。価格の再帰は式25–26 で、通常のアフィン再帰との違いは満期ごとのリターン誤差に由来する `σ²/2` の項だけ、と本文が述べている（§2.4）。短期金利の係数 δ0, δ1 は1か月 T-bill を因子に回帰して得る（§3.1）。再現するなら GSW のパラメータ（FEDS 2006-28 の配布ファイル）から 3〜120 か月の利回りを復元するところから始める。

独立確認：2期間・1因子、`r_t=0.03+x_t`、`x_(t+1)=0.9x_t+ε`、`x_t=0.02`、`Var(ε)=0.0001`、λとリターン誤差分散をゼロとすると、平均期待短期金利は `0.049`、式25–26の利回りは `0.048975`（差 −0.25bp）。式25の凸性に一致する。利回りから「平均期待短期金利」を取り出す教材では、この差を独立に検査する。

<a id="s008"></a>
### S008

```yaml
source_id: "S008"
url_in_conversation: "https://onlinelibrary.wiley.com/doi/10.1111/mafi.70018"
resolved_url: "https://finance.wharton.upenn.edu/~jermann/AHJ-main-10.pdf"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Perpetual Futures Pricing"
verified_authors_or_organization: "Damien Ackerer; Julien Hugonnier; Urban Jermann"
publication_date: "2025-11-20"
revision_date: "2024-09-03（確認した著者稿）"
version_or_commit: "VoR: Mathematical Finance 36(3), 481–499, July 2026。本文確認は2024-09-03著者稿。"
accessed_at: "2026-09-27"
source_type: "paper"
verification_status: "verified_partial"
claims:
  - claim: "linear/inverse/quanto perpetualのfundingと価格の関係"
    support_status: "verified_partial"
    locator: "著者稿p.1要旨、§1–2"
    quotation_or_paraphrase: "離散・連続時間でfundingに応じたリスク中立評価を導き、特定のfunding条件では現物との一致を示す。"
    assumptions_and_limits: "fundingの定義・決済通貨・no-bubble条件に依存。VoRと著者稿の全差分、実取引所の現在の規約は未確認。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "先行担当のCrossref記録ではVoRはCC BY 4.0。著者稿の再配布条件は未確認のため本文は収録しない。"
corrections_to_conversation: "初出/著者稿/オンライン公表/号発行を区別。2026年の全く新しいモデルとは呼ばない。"
access: "open"
saved_pdf: null
```

<a id="s009"></a>
### S009

```yaml
source_id: "S009"
url_in_conversation: "https://arxiv.org/abs/2410.08477"
resolved_url: "https://arxiv.org/html/2410.08477v3"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Multi-Curve Approach to Cross-Currency Basis Swaps Referencing Backward-Looking Term Rates"
verified_authors_or_organization: "Yining Ding; Ruyi Liu; Marek Rutkowski"
publication_date: "2024-10-11"
revision_date: "2025-11-16"
version_or_commit: "arXiv 2410.08477v3。本文Final revision 2025-10-30。"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "後決めRFRの担保付きCCSを価格付け・ヘッジする"
    support_status: "verified_partial"
    locator: "要旨、§2–4、§5–7の構成"
    quotation_or_paraphrase: "SOFR複利とAONIA平均の定額元本CCS、国内/外国通貨担保、金利・為替先物のヘッジを扱う。"
    assumptions_and_limits: "定額元本契約とモデル仮定の範囲。全数式・数値実験の独立検証、SIAM誌面との照合は未実施。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "arXiv non-exclusive license。本文・図を再配布しない。"
corrections_to_conversation: "absの短い題名とv3本文題名が異なる。採択日は著者記載2025-10-30で、出版社の公表日とは区別。"
access: "open"
saved_pdf: ["S009_xccy-basis-swaps-backward-looking-rates.pdf"]
```

<a id="s010"></a>
### S010

```yaml
source_id: "S010"
url_in_conversation: "https://www.bis.org/publications/qr-202603/rise-and-risks-synthetic-risk-transfers"
resolved_url: "https://www.bis.org/publications/qr-202603/rise-and-risks-synthetic-risk-transfers（PDF: https://www.bis.org/publications/rise-and-risks-synthetic-risk-transfers_1.pdf）"
claimed_title_and_date: "BIS Quarterly Review：Synthetic Risk Transfers、2026年3月"
verified_title: "The rise and risks of synthetic risk transfers"
verified_authors_or_organization: "Prashant R Babu（Bank of England）, Michael Chui（BIS）, Costas Stephanou（BIS）。BIS Quarterly Review, March 2026"
publication_date: "2026-03-16（記事ページの表示。WebFetch で確認）"
revision_date: null
version_or_commit: "PDF 19頁（誌面 pp.31–49）、CreationDate 2026-03-12 JST"
accessed_at: "2026-09-27"
source_type: "article"
verification_status: verified_supports_claim
claims:
  - claim: "銀行が貸出を保有したまま信用リスクだけを投資家へ移す仕組み"
    support_status: verified_supports_claim
    locator: "PDF p.32–34 'The economics of SRTs'、Graph 1"
    quotation_or_paraphrase: "SRT は信用デリバティブまたは金融保証でリスクを移すため、資産は銀行の貸借対照表に残る（true sale の証券化との違い）。形態は銀行発行 CLN、保証・CDS、SPV 発行 CLN の三つ。多くは現金・高品質証券の担保付き（funded）。"
    population_market_period: null
    assumptions_and_limits: "銀行発行 CLN は無担保の一般債務なので、投資家は銀行の信用リスクも負う（p.34）。"
  - claim: "銀行と投資家の損失分担（tranche）"
    support_status: verified_supports_claim
    locator: "PDF p.34（two-tranche と three-tranche の説明）、Annex A（Table A.1）"
    quotation_or_paraphrase: "two-tranche では junior（first-loss）を投資家へ、three-tranche では mezzanine（と場合により junior）を移す。損失は junior から順に充当。投資家の収益は保護料＋担保の変動金利収益。"
    population_market_period: "Annex A の例：€10億の貸出、リスクウェイト65%、tranche 1%／7%／92%"
    assumptions_and_limits: "例示の RWA・所要資本は会計・税・期待損失・資本の再配分を除いた単純化（Annex A 冒頭）。"
  - claim: "対象市場・期間と規模"
    support_status: verified_supports_claim
    locator: "PDF p.31–32（要旨・三つの発見）、p.35–36（Graph 2, 3）"
    quotation_or_paraphrase: "発行は2016年以降5倍、2024年末に約€8,000億の貸出を保護。EU・米・英・加の銀行貸出の約2%以下、SRT 発行行の CET1 押し上げは約43bp。"
    population_market_period: "IACPM の Global SRT Bank Survey 2016–2024（51行）、SCI、Pillar 3 開示（2024年末）、EBA transparency exercise（欧州106行）"
    assumptions_and_limits: "本文自身が『発行・価格・信用実績の横断的なデータ集積も一貫した規制報告も存在しない』と明記。数値は複数の民間・開示情報を組み合わせた推計。"
  - claim: "信用リスク移転と資本規制上の扱いの区別"
    support_status: verified_supports_claim
    locator: "PDF p.33（呼称の違い）、p.34（資本軽減と信用リスク管理の両目的）、Annex C（EU と米国の制度比較）"
    quotation_or_paraphrase: "Basel では synthetic securitisation、EU・英国の significant risk transfer は資本軽減を得る cash／synthetic 証券化の総称、米国では capital relief trade 等の呼称。資本軽減以外に与信枠の解放・集中の削減にも使う。"
    population_market_period: null
    assumptions_and_limits: null
independent_validation_of_outcome: "unknown"
license_and_redistribution: "記事 PDF に転載条件の記載はない。BIS サイト全体の利用条件は未確認。『views are those of the authors』の免責あり。"
corrections_to_conversation:
  - "正式題名は 'The rise and risks of synthetic risk transfers'。会話記載『2026年3月』は一致（2026-03-16 公表）。"
  - "資料側の誤植：Annex A の文章が 'reduces its RWA from €650 billion to €263 million' となっているが、本文 p.34 と計算からは €650 million が正しい。"
```

実装者向けメモ：Annex A の例は検算できる。事前 RWA＝€1,000m×65%＝€650m。事後 RWA＝senior €920m×15%＋first-loss €10m×1,250%＋mezzanine €70m×0%＝€138m＋€125m＝€263m。所要資本（CET1 12.5%）は €81.25m→€32.9m（本文は €82m→€33m と丸め）。保護料 7%×€70m＝€4.9m（本文は €5m）で、純利益/RWA は 30/650≈4.6%→25/263≈9.5%（本文は 5%→10%）。教材で tranche の損失分担を示すなら、この数値例をそのまま fixture にできる。

<a id="s011"></a>
### S011

```yaml
source_id: "S011"
url_in_conversation: "https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact/"
resolved_url: "https://www.cboe.com/insights/posts/0-dt-es-decoded-positioning-trends-and-market-impact/（本体 PDF: https://storage.pardot.com/77532/17461948884kPMLz2S/0DTEs_Decoded_Positioning_Trends_and_Market_Impact.pdf 。投稿ページの 'Download Full Report Here' は go.cboe.com の HTML ラッパー経由でこの PDF を埋め込む）"
claimed_title_and_date: "Cboe：0DTEs Decoded—Positioning Trends and Market Impact、2025-05-02"
verified_title: "0DTEs Decoded: Positioning, Trends, and Market Impact（副題 Retail and Institutional Trends in SPX® 0DTE Options）"
verified_authors_or_organization: "Mandy Xu（VP, Head of Derivatives Market Intelligence）, Cboe Exchange, Inc.。分析協力は Cboe Data and Analytics team"
publication_date: "2025-05-02"
revision_date: null
version_or_commit: "PDF 8頁、CreationDate 2025-05-02"
accessed_at: "2026-09-27"
source_type: "article"
verification_status: verified_partial
claims:
  - claim: "gross 出来高と net positioning を区別して読む（出来高が大きくても売買が均衡していれば dealer の gamma hedge は小さい）"
    support_status: verified_supports_claim
    locator: "PDF 'Could 0DTE Options Be Behind the Recent Market Volatility?' 節、Exhibit 10–11"
    quotation_or_paraphrase: "High volume doesn't equal high risk.（影響を決めるのは想定元本でなく売りと買いの釣り合い、という趣旨）"
    population_market_period: "SPX 0DTE、2025-04-04（SPX −6%）と 2025-04-09（+10%）の2日"
    assumptions_and_limits: "market maker net gamma は 4/4 に +21億〜−3.9億ドル、4/9 に +3億〜+7.7億ドル。SPX 先物の名目出来高（4/9 に8,500億ドル超、4/4 に9,400億ドル超）に対して最大 0.2%。gamma の推計方法は本レポートに記載がなく、前作 'Much Ado About 0DTEs' を参照とするのみ。"
  - claim: "spread（多脚取引）の比率と戦略構成"
    support_status: verified_supports_claim
    locator: "PDF 'Retail vs. Institutional Trading Characteristics' 節、Exhibit 4"
    quotation_or_paraphrase: "新規の顧客取引の約50〜52%が単独のコール・プット、残りが多脚。vertical spread は機関33%対個人28%。0DTE 取引の95%超が損失上限のある形式、ネイキッドの売りは4%。"
    population_market_period: "時点の明示は節ごとに異なる（2025年1–3月前後）"
    assumptions_and_limits: "個人と機関の区別は、注文の発注元・注文サイズ・頻度・最大損失などからの推定で、本文自身が 'these are just assumptions' と認めている。"
  - claim: "対象期間・データ・推定手順"
    support_status: verified_partial
    locator: "PDF p.1–2（Exhibit 1–3）"
    quotation_or_paraphrase: "0DTE の ADV は 2022年1Q の38.8万枚から 2025年1Q の198万枚。個人の推定比率は約50〜60%。"
    population_market_period: "2020年1Q〜2025年1Q（Exhibit 3）、2022年1Q〜2025年1Q（Exhibit 1）、2025年4月"
    assumptions_and_limits: "データは Cboe の取引所内部データ（proprietary exchange data を含む）で外部から再現できない。推定手順の詳細は非開示。"
independent_validation_of_outcome: "unknown（取引所自身の分析。第三者の独立検証は確認していない）"
license_and_redistribution: "© 2025 Cboe Exchange, Inc. All Rights Reserved。再配布の許諾表示はない。ローカル保存は閲覧用に限る。"
corrections_to_conversation:
  - "投稿ページ（URL）は要旨だけで、数値と図の本体は PDF 版にある。"
  - "要旨ページの『0.2% of the SPX daily liquidity』は、PDF 本文では『S&P futures notional volume』に対する比率として書かれている。"
```

実装者向けメモ：教材で「gross と net の違い」を示すなら、同じ出来高でも売買の偏りを変えた合成データで dealer の net gamma（Σ建玉×Γ×S²×1%）を計算し、先物の名目出来高で割る、という形にすると本レポートの 0.2% の比較と同じ尺度になる。ただし本レポートの gamma 推計そのものは再現できない（手順非開示・内部データ）。

<a id="s012"></a>
### S012

```yaml
source_id: "S012"
url_in_conversation: "https://www.schwab.com/learn/story/what-are-box-spreads"
resolved_url: "https://www.schwab.com/learn/story/what-are-box-spreads"
claimed_title_and_date: "Schwab：What Are Box Spreads?、2025-11-20"
verified_title: "Box Spreads: What They Are and How to Use Them（HTML の title 要素は 'What Are Box Spreads? | Charles Schwab'）"
verified_authors_or_organization: "Joe Mazzola, Charles Schwab & Co., Inc."
publication_date: "2025-11-20"
revision_date: null
version_or_commit: "ページ末尾の文書コード 1125-6GMS"
accessed_at: "2026-09-27"
source_type: "article"
verification_status: verified_supports_claim
claims:
  - claim: "box spread から合成の貸借金利を読む"
    support_status: verified_supports_claim
    locator: "本文 'Example of a short box spread' 節"
    quotation_or_paraphrase: "2025-10-16 に SPX（6,632）で 6,600/6,700 の short box（2026-03-20 満期）を組むと受取 9,830ドル、満期の支払は 10,000ドル。差額 170ドルが金利で、Rate = Interest/(Principal × Time) = 170/(9,830×5/12) ≈ 4.15%（年率、手数料・税除く）。"
    population_market_period: "SPX、2025-10-16 取引・2026-03-20 満期（thinkorswim paperMoney の画面を引用）"
    assumptions_and_limits: "期間 5/12 年は本文自身が 'rough approximation' と断っている。手数料・税・bid/ask の影響を除いた値。"
  - claim: "行使形式・決済・証拠金・bid/ask・費用の前提"
    support_status: verified_partial
    locator: "本文 'Box spread risks' 節、ページ末尾の開示"
    quotation_or_paraphrase: "American 型では short 脚の早期割当で構造が崩れる（金利・配当・借株・追証リスク）ため European 型を使う。SPX は cash-settled と説明。流動性の低い市場では4脚の約定価格がずれて利回りが悪化。値洗いで口座の純清算価値が一時的に減ることがある。Section 1256 の 60/40 課税に言及。"
    population_market_period: null
    assumptions_and_limits: "証拠金は『spread trading must be done in a margin account』という開示だけで、必要額の数値はない。bid/ask は定性的な説明のみ。"
independent_validation_of_outcome: "not_applicable（解説記事）"
license_and_redistribution: "© 2026 Charles Schwab & Co., Inc. All rights reserved。一般情報であり投資助言ではない旨の免責あり。再配布の許諾表示はない。"
corrections_to_conversation:
  - "正式題名は 'Box Spreads: What They Are and How to Use Them'。日付 2025-11-20 は会話記載と一致。"
  - "WebFetch では認可エラー（ボット対策）で本文が取れず、通常のブラウザ UA の curl で公開ページを取得した。"
```

実装者向けメモ：記事の 4.15% は単利・期間 5/12 年の概算。同じ数値で日数を実日数にすると、2025-10-16→2026-03-20 は 155 日で、単利 ACT/365 は 170/9,830×365/155 ≈ 4.07%、連続複利は ln(10,000/9,830)/(155/365) ≈ 4.04%（この二つは私の計算で、記事には無い）。教材では「期間の数え方で 0.1pt 変わる」ことを示す例に使える。

<a id="s013"></a>
### S013

```yaml
source_id: "S013"
url_in_conversation: "https://globalxetfs.co.jp/en/funds/2858/index.html"
resolved_url: "https://globalxetfs.co.jp/en/funds/2858/index.html（ファクトシート: https://globalxetfs.co.jp/en/funds/2858/2858_factsheet.pdf）"
claimed_title_and_date: "Global X Japan：カバードコールETFの公開商品資料（参照日・発行日は未確定）"
verified_title: "Global X Nikkei 225 Covered Call ETF (option premium reinvestment type)（証券コード 2858、ISIN JP3049650009）"
verified_authors_or_organization: "Global X Japan Co. Ltd.（大和証券グループ本社・大和アセットマネジメント・Global X Management Company の合弁）"
publication_date: "設定日 2022-07-27（ページの 'Inception Date'）"
revision_date: "商品ページは 2026-09-25 時点のデータ、ファクトシートは 2026-08-31 時点（PDF 作成 2026-09-01）"
version_or_commit: null
accessed_at: "2026-09-27"
source_type: "product"
verification_status: verified_partial
claims:
  - claim: "カバードコールの premium 受取"
    support_status: verified_partial
    locator: "ファクトシート p.2 'OPTION PREMIUMS'（月次・年次のプレミアム率）、商品ページ 'FUND SUMMARY'"
    quotation_or_paraphrase: "日経225構成銘柄に相当する資産を持ち、同じ指数のコールを売る。直近12か月の月次プレミアムは SQ 日ごとに 1.68%〜6.02%、年次は 2023年 21.10%、2024年 27.62%、2025年 27.48%、2026年（8月まで）31.45%。"
    population_market_period: "2025-09〜2026-08 の各 SQ 日"
    assumptions_and_limits: "このファンドは『オプションプレミアム再投資型』で、プレミアムは分配でなく基準価額に再投資される。プレミアム率の分母（指数水準か NAV か）はファクトシートに明記がない＝未確認。"
  - claim: "NAV と total return の分解"
    support_status: verified_partial
    locator: "ファクトシート p.1 'PERFORMANCE'・'TOP 10 HOLDINGS'、商品ページ 'FUND DETAILS'"
    quotation_or_paraphrase: "NAV（100口当たり）152,487円（2026-09-25）。設定来 NAV +52.49%、分配再投資ベース +59.36%、指数（Nikkei 225 Covered Call ATM Index, Total Return）+66.24%（2026-08-31 時点）。上位保有は iShares Core Nikkei 225 ETF 37.95% と iFree ETF Nikkei 225 37.86%（計 75.81%）。信託報酬 年0.3025%（税込）。"
    population_market_period: "2022-07-27〜2026-08-31"
    assumptions_and_limits: "株式エクスポージャーの残り（先物か現金か）とコール売りの時価はファクトシートでは分からない。"
  - claim: "ロール（行使価格・限月・カバー率）の規則"
    support_status: not_yet_checked
    locator: "指数名 'Nikkei 225 Covered Call ATM Index'（指数ティッカー NKYCCATR）までは確認。日経の指数算出要領は取得できず（推測した URL で HTTP 403）"
    quotation_or_paraphrase: null
    population_market_period: null
    assumptions_and_limits: "ATM という名称以外のロール規則は未確認。"
independent_validation_of_outcome: "not_applicable（商品資料）"
license_and_redistribution: "サイト・ファクトシートとも『許可なく複製・引用・転載・送信を禁ずる』。ローカル保存は閲覧用に限り、repo や教材に転載しない。"
corrections_to_conversation:
  - "URL の 2858 は『オプションプレミアム再投資型』（決算・分配は 4/24 と 10/24 の年2回）。毎月分配型のカバードコール ETF を意図していたなら別の銘柄であり、どの銘柄かは未確認。"
  - "商品名・戦略・分配・費用・基準価額の定義は確認できた。商品推奨とは切り離して扱う。"
```

実装者向けメモ：分解教材にするなら、(1) 指数（TR）とファンド NAV（再投資ベース）の差＝信託報酬＋運用の誤差、(2) 指数と日経平均 TR の差＝コール売りの損益（受取プレミアム−満期の本質価値）、の二段で分ける。(2) の月次の再現には SQ 日と ATM 行使価格の決め方が必要で、これは指数算出要領（未取得）を確認してから。

<a id="s014"></a>
### S014

```yaml
source_id: "S014"
url_in_conversation: "https://arxiv.org/abs/2608.30867"
resolved_url: "https://arxiv.org/html/2608.30867v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Neural Calibration of a Complete Market Model"
verified_authors_or_organization: "Andrea Molent; Michel Vellekoop"
publication_date: "2026-08-31"
revision_date: null
version_or_commit: "arXiv 2608.30867v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "ニューラル表現で完備な二項市場を較正できる"
    support_status: "verified_partial"
    locator: "§2 Proposition 2.1、式(2.3)、最適化の説明"
    quotation_or_paraphrase: "正の節点を再結合二項木で表現し、条件を満たす遷移確率で無裁定・完備性を得る。"
    assumptions_and_limits: "最適化中のp∈(0,1)はhard保証ではなくpenaltyと事後検査。満期間補間の全域無裁定まで保証したとは読めない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "arXiv non-exclusive license。リンクと短い要約のみ。"
corrections_to_conversation: "「構造により常に無裁定」と一般化しない。採否には節点と補間の検査が要る。"
access: "open"
saved_pdf: ["S014_neural-calibration-complete-market-model.pdf"]
```

<a id="s015"></a>
### S015

```yaml
source_id: "S015"
url_in_conversation: "https://arxiv.org/abs/2603.13170"
resolved_url: "https://arxiv.org/html/2603.13170v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Microstructural Foundation of Rough Log-Normal Volatility Models"
verified_authors_or_organization: "Paul P. Hager; Ulrich Horst; Thomas Wagenhofer; Wei Xu"
publication_date: "2026-03-13"
revision_date: null
version_or_commit: "arXiv 2603.13170v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "注文到来からrough lognormal volatilityの極限を説明する"
    support_status: "verified_partial"
    locator: "要旨、§1、§3–4の定理・証明構成"
    quotation_or_paraphrase: "Poisson注文と長く残る影響の市場列から、価格・分散過程の弱収束と弱誤差率を研究する。"
    assumptions_and_limits: "Poisson構造に依存する理論。全証明の検算、実市場への適合検証、既存rBergomiコードの正しさを裏付けるものではない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY-NC-ND 4.0。改変図・翻訳本文の配布は行わない。"
corrections_to_conversation: "roughの理論的根拠候補。R1の先読み・離散補償項を解決する代わりにはならない。"
access: "open"
saved_pdf: ["S015_microstructural-rough-lognormal-vol.pdf"]
```

<a id="s016"></a>
### S016

```yaml
source_id: "S016"
url_in_conversation: "https://arxiv.org/abs/2312.13057"
resolved_url: "https://arxiv.org/html/2312.13057v3"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Cross-Currency Heath-Jarrow-Morton Framework in the Multiple-Curve Setting"
verified_authors_or_organization: "Alessandro Gnoatto; Silvia Lavagnini"
publication_date: "2023-12-20"
revision_date: "2026-03-04"
version_or_commit: "arXiv 2312.13057v3"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "多通貨担保・複数曲線・fixing/payment調整を一つのHJM枠組みで扱う"
    support_status: "verified_partial"
    locator: "要旨、§1のZCB表現、付録B/Cの測度変更"
    quotation_or_paraphrase: "通貨と担保通貨の組ごとの割引債、担保金利とcross-currency basisのforward過程を用い、IBORと後決めRFRを包含する。"
    assumptions_and_limits: "一般的なモデル枠組み。日数規約・resettable元本・実市場データの実装済みを意味しない。証明・数値は未再現。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "arXiv non-exclusive license。リンクと短い要約のみ。"
corrections_to_conversation: "HTML本文にはDate August 24, 2026も表示される。版の識別は投稿履歴のv3/2026-03-04とし、表示日を投稿日に置換しない。"
access: "open"
saved_pdf: ["S016_xccy-hjm-multiple-curve.pdf"]
```

<a id="s017"></a>
### S017

```yaml
source_id: "S017"
url_in_conversation: "https://www.iea.org/reports/electricity-2026/prices"
resolved_url: "https://www.iea.org/reports/electricity-2026/prices"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Electricity 2026 — Prices"
verified_authors_or_organization: "International Energy Agency"
publication_date: "2026（日付は本ページでは未特定）"
revision_date: null
version_or_commit: "Electricity 2026, Prices章"
accessed_at: "2026-09-27"
source_type: "report"
verification_status: "verified_partial"
claims:
  - claim: "負の電力価格と地域差を教材に使う"
    support_status: "verified_partial"
    locator: "Negative pricesの本文・図、Wholesale electricity prices"
    quotation_or_paraphrase: "2025年の欧州の複数市場で負価格時間の増加を報告。一方で北欧・Californiaは減少など地域差がある。"
    assumptions_and_limits: "主に2025年の観測。卸価格と発電所のcapture priceは別。2026年1月時点の先物を実現値として扱わない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "報告CC BY 4.0。ASX由来データ等の第三者部分は別許諾条件で、自由転載としない。"
corrections_to_conversation: "先行担当の403はweb経由で解消。capture priceや投資収益の主張全体まで本ページで支持されたとはしない。"
access: "open"
saved_pdf: null
```

<a id="s018"></a>
### S018

```yaml
source_id: "S018"
url_in_conversation: "https://arxiv.org/abs/2603.10137"
resolved_url: "https://arxiv.org/html/2603.10137v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Uncertainty-Aware Deep Hedging"
verified_authors_or_organization: "Manan Poddar"
publication_date: "2026-03-10"
revision_date: null
version_or_commit: "arXiv 2603.10137v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "ensembleの不一致を利用してヘッジを混合する"
    support_status: "verified_partial"
    locator: "§3、§4、§5.4、§6.1/6.4"
    quotation_or_paraphrase: "Heston下の5本LSTMとBS deltaを比較。CVaR最適化はほぼ一定の混合比に落ち着き、不一致の高低による切替の効果とは分ける必要がある。"
    assumptions_and_limits: "合成Heston・半年ATM call・126step・5bp費用。真の瞬間分散を特徴に含む。WWはモデル不一致、ensemble SDは較正済み信頼確率ではない。実市場検証なし。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY-NC-SA 4.0。著者本文・図は収録しない。"
corrections_to_conversation: "見出しの優位を一般化しない。constant mix、観測可能情報を揃えたbaseline、独立testが必要。"
access: "open"
saved_pdf: ["S018_uncertainty-aware-deep-hedging.pdf"]
```

<a id="s019"></a>
### S019

```yaml
source_id: "S019"
url_in_conversation: "https://eprints.lse.ac.uk/127063/"
resolved_url: "https://researchonline.lse.ac.uk/id/eprint/127063/（302 リダイレクト。PDF: https://researchonline.lse.ac.uk/id/eprint/127063/3/hhaf058.pdf）"
claimed_title_and_date: "Hilscher–Raviv–Reis：How Likely Is an Inflation Disaster?、RFS 2026年3月号"
verified_title: "How Likely Is an Inflation Disaster?"
verified_authors_or_organization: "Jens Hilscher（UC Davis）, Alon Raviv（Bar-Ilan University）, Ricardo Reis（LSE）"
publication_date: "Review of Financial Studies 39(3), 744–782（リポジトリの発行日 2026-03-01）。DOI 10.1093/rfs/hhaf058"
revision_date: "受付 2022-04-27、編集判断 2025-01-26、Advance Access 2025-10-28（PDF の表記）。リポジトリの published_online は 2025-11-16 と記録されており、PDF 表記と一致しない"
version_or_commit: "LSE Research Online の Published Version（OUP の advance article を 2026-01-07 に取得したもの。頁は 1–39 で、号の頁 744–782 ではない）"
accessed_at: "2026-09-27"
source_type: "paper"
verification_status: verified_supports_claim
claims:
  - claim: "inflation option の価格からインフレの裾の確率を推定する"
    support_status: verified_supports_claim
    locator: "abstract、序論 p.2–4（式1）、§3.1 Data、§3.2（式8–11）"
    quotation_or_paraphrase: "式1の確率 Prob[π_{T,T+H}/H > π̄+d] 等を、インフレ cap/floor の価格から Breeden–Litzenberger 型の微分で得る。d=0.02（disaster）と 0.03（severe）。"
    population_market_period: "Bloomberg のインフレ option 価格。米国 2009-10〜2024-10、ユーロ圏 2011-01〜。行使価格 −2%〜6%（0.5% 刻み）、満期は最長15年のうち 5年と10年を使用。データ品質のため月次に集約"
    assumptions_and_limits: "OTC 市場で取引量が減っている点（§3.6）と、取引相手の信用リスク（注12）を本文自身が限界として挙げている。"
  - claim: "期間（平均インフレの区間）・測度・risk compensation の調整"
    support_status: verified_supports_claim
    locator: "序論 p.4–5（三つの調整と用途別の組合せ）、§3.2 Inflation adjustment、§3.3 Horizon adjustment（Proposition 1、§3.3.2 のインフレ持続性モデル）、§3.4 Risk adjustment"
    quotation_or_paraphrase: "(1) inflation 調整：名目の状態価格を実質価値に合わせる（Q を得る）。(2) horizon 調整：取引されるのは 0→T と 0→T+H の累積インフレなので、市場が織り込む持続性を推定して T→T+H の forward 確率へ変換。(3) risk 調整：災害時は限界効用が高いので Q は実確率を過大評価する。SDF の全動学を特定せず OTM option の価格を使って P へ。"
    population_market_period: "2021–23 年の米国で調整係数の中央値は inflation 1.24、horizon 0.38、risk 0.66。10年 option の素朴な読みで 14.0% の 5y5y 災害確率が、調整後の実確率では 4.2%"
    assumptions_and_limits: "どの調整を使うかは目的次第（序論）：Q の現在→遠い将来の確率なら inflation 調整だけ、P なら risk 調整を追加、forward の P なら horizon 調整も追加。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（© The Author(s) 2025, Published by OUP）。出典明記で再利用・再配布可。"
corrections_to_conversation:
  - "『RFS 2026年3月号』は一致（39(3), 744–782）。ただし保存した PDF は Advance Access 版で頁番号が号と異なる。"
  - "本文の注5 に、災害確率の時系列を公開するサイト https://r2rsquaredlse.github.io/web-inflationdisasters/ がある（S031 の repo 名 web-inflationdistributions とは別名。関係は S031 で確認）。"
```

実装者向けメモ：§3.2（印刷p.15）の記号は密度と累積分布を区別して実装する。gross inflation を `k=exp(π)`、option価格を `a(k)` とすると、式10の `exp(r)×k×a''(k)` は **kに関する実質リスク中立密度** `q_k(k)` であり、CDFではない。一方、式11の `1+exp(i)×a'(k)` は名目測度のCDF。log inflationの密度へ変えるにはJacobianを掛け、`q_π(π)=exp(π)×q_k(exp(π))` とする（金利は原式と同じ対象期間の積算表現）。合成lognormal例 `μ=0.02, σ=0.10` の中央値では `q_k≈3.91043`、QのCDFは `0.5`、`q_π≈3.98942` で、密度が1を超えても誤りではない。測度・変数・単位、密度の積分1とCDFの端点0/1を別々に検査する。

forward 化（§3.3、Proposition 1）は累積2本の分布だけでは決まらず持続性のモデルが要る。risk 調整（§3.4）は rare disaster の文献に基づく近似で、係数の不確実性は §3.5 で扱われている。

<a id="s020"></a>
### S020

```yaml
source_id: "S020"
url_in_conversation: "https://academic.oup.com/imaiai/article-abstract/15/1/iaag003/8509318"
resolved_url: "https://academic.oup.com/imaiai/article-abstract/15/1/iaag003/8509318"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Empirical Bernstein and betting confidence intervals for randomized quasi-Monte Carlo"
verified_authors_or_organization: "Aadit Jain; Fred J. Hickernell; Art B. Owen; Aleksei G. Sorokin"
publication_date: "2026-03-06"
revision_date: null
version_or_commit: "Information and Inference 15(1), March 2026, iaag003; DOI 10.1093/imaiai/iaag003"
accessed_at: "2026-09-27"
source_type: "paper"
verification_status: "verified_partial"
claims:
  - claim: "RQMCに有限標本の信頼区間を付ける"
    support_status: "verified_partial"
    locator: "出版社の書誌・要旨。本文の条件はS021を確認。"
    quotation_or_paraphrase: "既知の有界性がある被積分関数に、独立なrandomizationごとの推定値でEBCI/HBCIを構成する。"
    assumptions_and_limits: "出版社本文はアクセス不可。S021と同題同著者だがVoR全差分未照合。上限不明のcall payoffへ定理をそのまま適用しない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "OUP Standard Journals Publication Model、all rights reserved。"
corrections_to_conversation: "出版社の公表日は2026-03-06。先行Crossrefのpublished-print 02-19と区別。S021と独立な2研究と数えない。"
access: "abstract_only"
saved_pdf: null
```

<a id="s021"></a>
### S021

```yaml
source_id: "S021"
url_in_conversation: "https://arxiv.org/abs/2504.18677"
resolved_url: "https://arxiv.org/html/2504.18677v2"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Empirical Bernstein and betting confidence intervals for randomized quasi-Monte Carlo"
verified_authors_or_organization: "Aadit Jain; Fred J. Hickernell; Art B. Owen; Aleksei G. Sorokin"
publication_date: "2025-04-25"
revision_date: "2026-02-02"
version_or_commit: "arXiv 2504.18677v2。本文January 2026。"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_supports_claim"
claims:
  - claim: "RQMCの分散減少と有限標本の区間幅を区別する"
    support_status: "verified_supports_claim"
    locator: "§1–2、§3、§4"
    quotation_or_paraphrase: "R本の独立replicateと各n点、総費用N=Rnを区別する。既知の範囲内の関数で有限標本区間を比較する。"
    assumptions_and_limits: "replicate内の点を独立標本としてSEを計算しない。最適nの率は分散の漸近率等に依存。通常のt区間は同じ有限標本保証ではない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "arXiv non-exclusive license。リンクと短い要約のみ。"
corrections_to_conversation: "RB-F08はscramble単位のCIを先に作り、有界定理の利用は別条件とする。"
access: "open"
saved_pdf: ["S021_rqmc-bernstein-betting-ci.pdf"]
```

<a id="s022"></a>
### S022

```yaml
source_id: "S022"
url_in_conversation: "https://pubsonline.informs.org/doi/10.1287/mnsc.2023.01659"
resolved_url: "https://pubsonline.informs.org/doi/10.1287/mnsc.2023.01659"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "E-backtesting"
verified_authors_or_organization: "Qiuqi Wang; Ruodu Wang; Johanna Ziegel"
publication_date: "2025-09-23"
revision_date: null
version_or_commit: "Management Science 72(6), 4952–4973, June 2026; DOI 10.1287/mnsc.2023.01659"
accessed_at: "2026-09-27"
source_type: "paper"
verification_status: "verified_partial"
claims:
  - claim: "e-processによる逐次VaR/ESバックテスト"
    support_status: "verified_partial"
    locator: "出版社書誌・要旨、具体的条件はS023"
    quotation_or_paraphrase: "損失とリスク予測を順次受け取り、e-statisticを蓄積して過小予測を検出する方法。"
    assumptions_and_limits: "publisher全文の版差は未照合。規制当局が採用済みという意味ではない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "©2025 INFORMS。再配布許諾未確認。"
corrections_to_conversation: "オンライン公表2025-09-23、2026年6月号。DOIの2023は公表年ではない。S023は同じ研究系列。"
access: "abstract_only"
saved_pdf: null
```

<a id="s023"></a>
### S023

```yaml
source_id: "S023"
url_in_conversation: "https://arxiv.org/abs/2209.00991"
resolved_url: "https://arxiv.org/html/2209.00991v6"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "E-backtesting"
verified_authors_or_organization: "Qiuqi Wang; Ruodu Wang; Johanna Ziegel"
publication_date: "2022-08-27"
revision_date: "2026-04-15"
version_or_commit: "arXiv 2209.00991v6"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_supports_claim"
claims:
  - claim: "事前に選ぶ賭け率でanytime-validな検定を構成する"
    support_status: "verified_supports_claim"
    locator: "§3–4、Theorem 2、§4.2、§5"
    quotation_or_paraphrase: "帰無仮説の下で条件付きe-variableと予測可能な賭け率から非負supermartingaleを作り、1/alpha越えの確率をalpha以下に抑える。"
    assumptions_and_limits: "帰無仮説は条件付きのリスク予測に関するもの。ESでは補助VaRの条件も必要。全標本を見た賭け率選択や日次p値の反復とは異なる。閾値2/5/10は5%有意ではない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY-NC-SA 4.0。リンクと短い要約のみ。"
corrections_to_conversation: "HTML本文Date August 24, 2026と版日が異なる。版はv6を固定。現行規制の断定には用いない。"
access: "open"
saved_pdf: ["S023_e-backtesting.pdf"]
```

<a id="s024"></a>
### S024

```yaml
source_id: "S024"
url_in_conversation: "https://arxiv.org/abs/2608.20842"
resolved_url: "https://arxiv.org/html/2608.20842v2"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Rethinking Synthetic Scenario Realism: Compatibility, Not Fidelity, Drives Hedging Performance"
verified_authors_or_organization: "Ryuji Hashimoto; Masanori Hirano; Ryota Ozaki; Kentaro Imajo"
publication_date: "2026-08-21"
revision_date: "2026-09-04"
version_or_commit: "arXiv 2608.20842v2"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "統計的忠実度だけでヘッジ学習の適性を評価できない"
    support_status: "verified_partial"
    locator: "§4、§5 Data and Calibration、§6"
    quotation_or_paraphrase: "学習誤差とcompatibility gapを分け、生成器・hedger・契約の組み合わせで順位が変わると報告する。"
    assumptions_and_limits: "N225較正2018-01〜2022-12、test2023-01〜2026-02。VAEは同期間の他資産も使用。全モデルを同一データだけで学習した比較ではない。実験未再現。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "arXiv non-exclusive license。リンクと短い要約のみ。"
corrections_to_conversation: "生成器の市場統計と、同じ実現経路上のヘッジ成績を別々に検査する根拠。現行R3の経路混同を正当化しない。"
access: "open"
saved_pdf: ["S024_scenario-realism-hedging-compatibility.pdf"]
```

<a id="s025"></a>
### S025

```yaml
source_id: "S025"
url_in_conversation: "https://www.sec.gov/Archives/edgar/data/886982/000119312526037142/wogomen2_prelim.htm"
resolved_url: "https://www.sec.gov/Archives/edgar/data/886982/000119312526037142/wogomen2_prelim.htm"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "GS Finance Corp. Autocallable Equity-Linked Notes — preliminary prospectus supplement"
verified_authors_or_organization: "GS Finance Corp.; guarantor The Goldman Sachs Group, Inc."
publication_date: "2026-02-04"
revision_date: null
version_or_commit: "424B2、CUSIP 40058XEC4 / ISIN US40058XEC48、preliminary"
accessed_at: "2026-09-27"
source_type: "filing"
verification_status: "verified_supports_claim"
claims:
  - claim: "実在のautocallable条項を契約fixtureへ分解する"
    support_status: "verified_supports_claim"
    locator: "表紙、Terms and Conditions (S-3以降)"
    quotation_or_paraphrase: "GOOGL/META/NVDAの3銘柄。1回の予定観察日で全銘柄90%以上ならcall。未call満期はworst returnが正なら1.25倍参加、そうでなければ額面。無利息。"
    assumptions_and_limits: "予定日・未確定条件を含む予備目論見書。連続knock-in型の損失連動ノートではない。額面返済にも発行体信用リスクがある。最終発行条件は未確認。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "EDGARで公開閲覧可能。提出者文書の再配布許諾は未確認、短い要約とリンクのみ。"
corrections_to_conversation: "autocallableという名称だけで一般的なcoupon/barrier商品仕様を当てはめない。日付・観察・支払・比較演算を分ける。"
access: "open"
saved_pdf: null
```

<a id="s026"></a>
### S026

```yaml
source_id: "S026"
url_in_conversation: "https://arxiv.org/html/2609.04087v1"
resolved_url: "https://arxiv.org/html/2609.04087v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Global Multi-Maturity SPX–VIX Calibration Beyond Markovian Stitching"
verified_authors_or_organization: "Atithi Acharya; Yue Sun; Brandon Augustino; Shouvanik Chakrabarti; Shree Hari Sureshbabu; Charlie Che"
publication_date: "2026-09-03"
revision_date: null
version_or_commit: "arXiv 2609.04087v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "複数満期の周辺較正で履歴依存が特定されるとは限らない"
    support_status: "verified_partial"
    locator: "要旨、§1、有限状態例の説明"
    quotation_or_paraphrase: "各月ブロックを保つMarkov化と、捨てられる過去依存を区別。同じ月次較正でも複数期間payoffの価格が違いうる。"
    assumptions_and_limits: "smoothed SPX/VIX surfaceと有限離散化の結果。penalty残差は残り、全条件を厳密に充足したとの一般保証ではない。データ・数値の再現未実施。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY 4.0。原データの権利は別確認が必要。"
corrections_to_conversation: "「全満期fit＝全経路法則が決定」と読まない。RB-F04の有限quote一致と同じ注意を要する。"
access: "open"
saved_pdf: ["S026_spx-vix-multi-maturity-calibration.pdf"]
```

<a id="s027"></a>
### S027

```yaml
source_id: "S027"
url_in_conversation: "https://arxiv.org/abs/2401.15728"
resolved_url: "https://arxiv.org/html/2401.15728v2"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Analytic Pricing of SOFR Futures Contracts with Smile and Skew"
verified_authors_or_organization: "Aurelio Romero-Bermúdez; Colin Turfus"
publication_date: "2024-01-28"
revision_date: "2024-04-12"
version_or_commit: "arXiv 2401.15728v2"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "SOFR先物のconvexityにsmile/skewを加える"
    support_status: "verified_partial"
    locator: "要旨、§1–4"
    quotation_or_paraphrase: "HWを拡張したshort-rateモデルの後退PDEを時間順序指数の摂動で解き、後決め複利とsmile/skew効果を扱う。"
    assumptions_and_limits: "近似展開の有効域、較正と数値誤差の独立検証は未実施。単なるBlack vol差替えではない。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "公開プレプリント。再配布条件は未確認のため本文・図を収録しない。"
corrections_to_conversation: "初出は2024年。HTML Date August 24, 2026は投稿履歴と異なるためv2で識別する。"
access: "open"
saved_pdf: ["S027_sofr-futures-smile-skew.pdf"]
```

<a id="s028"></a>
### S028

```yaml
source_id: "S028"
url_in_conversation: "https://ewl.wiwi.uni-due.de/en/research/publications/publications/real-options-valuation-of-battery-energy-storage-systems-in-continental-europes-day-ahead-and-fcr-markets-17717/"
resolved_url: "https://ewl.wiwi.uni-due.de/en/research/publications/publications/real-options-valuation-of-battery-energy-storage-systems-in-continental-europes-day-ahead-and-fcr-markets-17717/"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Real Options Valuation of Battery Energy Storage Systems in Continental Europe’s Day-Ahead and FCR Markets"
verified_authors_or_organization: "Luis van Sandbergen; Richard Biegler-König"
publication_date: "2026"
revision_date: null
version_or_commit: "EEM 2026; DOI 10.1109/EEM68581.2026.11589740"
accessed_at: "2026-09-27"
source_type: "conference_paper"
verification_status: "verified_partial"
claims:
  - claim: "BESSをreal options/LSMC/ADPで評価する研究候補"
    support_status: "verified_partial"
    locator: "著者所属大学の公表一覧、キーワード"
    quotation_or_paraphrase: "題名、著者、EEM会議、DOI、LSMC/ADPのキーワードを確認した。"
    assumptions_and_limits: "IEEE本文は取得できず。価格期間・劣化・効率・同時市場参加の制約・性能を確認できていない。実装要件の根拠にはまだ不足。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "本文の権利・再配布条件未確認。書誌とリンクのみ。"
corrections_to_conversation: "大学ページの区分はArticle in Journalだが掲載先は会議EEM。成果の数値や優位は未検証。"
access: "metadata_only"
saved_pdf: null
```

<a id="s029"></a>
### S029

```yaml
source_id: "S029"
url_in_conversation: "https://arxiv.org/abs/2608.01479"
resolved_url: "https://arxiv.org/html/2608.01479v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "The VIX-Derived Volatility Model: A VIX-first Joint SPX-VIX Framework"
verified_authors_or_organization: "Nicola F. Zaugg; Lech A. Grzelak"
publication_date: "2026-08-02"
revision_date: null
version_or_commit: "arXiv 2608.01479v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "VIX側を先に較正しSPXの分散過程を結合する"
    support_status: "verified_partial"
    locator: "要旨、§1、rolling-window結合の説明"
    quotation_or_paraphrase: "VIX過程からrolling-window分散定義に整合する結合関数を導き、VIX dynamicsを保ったままSPX側を較正する枠組み。"
    assumptions_and_limits: "終端区間の結合関数、非多項式での近似に依存。数値実験のfitを全市場・全満期の保証に拡大しない。較正・正値性の独立検証は未実施。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY 4.0。市場データの権利は別確認。"
corrections_to_conversation: "既存vol21の合成joint targetと同じ完成度ではない。採用前にVIX二乗と将来積分分散の整合を検査する。"
access: "open"
saved_pdf: ["S029_vix-derived-volatility-model.pdf"]
```

<a id="s030"></a>
### S030

```yaml
source_id: "S030"
url_in_conversation: "https://arxiv.org/abs/2603.01344"
resolved_url: "https://arxiv.org/html/2603.01344v1"
claimed_title_and_date: "研究提案の同ID。下記の確認済み書誌・訂正を採用する。"
verified_title: "Pricing and hedging for liquidity provision in Constant Function Market Making"
verified_authors_or_organization: "Jimmy Risk; Shen-Ning Tung; Tai-Ho Wang"
publication_date: "2026-03-02"
revision_date: null
version_or_commit: "arXiv 2603.01344v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: "verified_partial"
claims:
  - claim: "流動性提供をvanilla option stripで価格付け・ヘッジする"
    support_status: "verified_partial"
    locator: "要旨、§2–4、実証と付録週次snapshot"
    quotation_or_paraphrase: "価格とintrinsic liquidityの座標でCFMMを表し、Carr–Madan展開でILをoption stripへ分解。Uniswap v3 ETH/USDCとDeribitの例を示す。"
    assumptions_and_limits: "本文図は2025-11-17、付録は10/27–12/1の追加週次snapshot。ILとLVR、fee収益、経路に沿う再均衡は区別。生データ・実験は未再現。"
independent_validation_of_outcome: "実験・著者コードは未再現。出典の主張とその条件を照合した記録。"
license_and_redistribution: "CC BY 4.0。取引所データの再配布許諾は別確認。"
corrections_to_conversation: "R6の現行gross不変という構造を、実市場で動的feeが無効との結論に置換しない。"
access: "open"
saved_pdf: ["S030_cfmm-lp-pricing-hedging.pdf"]
```

<a id="s031"></a>
### S031

```yaml
source_id: "S031"
url_in_conversation: "https://github.com/R2RsquaredLSE/web-inflationdistributions"
resolved_url: "https://github.com/R2RsquaredLSE/web-inflationdistributions（公開ページ: https://r2rsquaredlse.github.io/web-inflationdistributions/）"
claimed_title_and_date: "米国・ユーロ圏のインフレ分布公開データ、2026年5月更新、2026年4月まで収録"
verified_title: "web-inflationdistributions — Market-Based Risk-Neutral Probability Densities for Future Inflation"
verified_authors_or_organization: "GitHub organization R2RsquaredLSE（README の著者表記は Jens Hilscher, Alon Raviv, Ricardo Reis）"
publication_date: "repo 作成 2026-05-16（GitHub API）"
revision_date: "最終 push 2026-05-22T11:10:21Z"
version_or_commit: "617f3b0044f666a8e65eb99eb51a7f4779d911dd（2026-05-22、'Update README.md'）。README の vintage 表記：Vintage 1＝2026年5月初公開（2026年2月まで）、Vintage 2＝2026年5月更新（2026年4月まで）"
accessed_at: "2026-09-27"
source_type: "dataset"
verification_status: verified_supports_claim
claims:
  - claim: "5年・10年平均インフレのリスク中立密度（日本の実確率ではない）"
    support_status: verified_supports_claim
    locator: "README 'Probability densities' 節、data/*.csv（commit 617f3b0 で取得）"
    quotation_or_paraphrase: "地域×期間（米国・ユーロ圏 × 5年・10年）ごとに、月次スナップショットの Q 測度の密度を −3%〜+7% の 0.5pt 刻み 21 点で提供。README は『リスク補償を含み、投資家がリスク中立なら実確率と一致』と明記。"
    population_market_period: "CSV 実測：米国 2009-10-05〜2026-05-01（200か月。初日 2009-10-05 は全点空欄）、ユーロ圏 2010-01-13 の1点のあと 2011-01〜2026-05-07 が連続（計186か月）"
    assumptions_and_limits: "米国とユーロ圏のみ。日本のデータはない。値は各支持点の確率（列名 frequency、日付ごとの合計が1）で、連続密度の値ではない。"
  - claim: "最新 commit、対象期間、測度、データ辞書、ライセンス・再配布条件"
    support_status: verified_supports_claim
    locator: "GitHub API（repos／commits／license）、README 'Variables'・'Usage' 節、LICENSE"
    quotation_or_paraphrase: "列は date（スナップショット日）、support（年率・小数）、frequency。ライセンスは MIT（Copyright (c) 2026 R2RsquaredLSE）。README は研究者が自由に使えると書き、利用時の引用と訂正の連絡を求める。"
    population_market_period: null
    assumptions_and_limits: "README は『2026年4月まで』だが、CSV の最終スナップショットは米国 2026-05-01、ユーロ圏 2026-05-07。月の中のスナップショット日は一定しない（例：2026-04-09、2026-04-01）。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "MIT License（repo 全体）。README は引用を依頼。データの出所である Bloomberg の option 価格そのものは含まれず、推定済みの確率のみ。"
corrections_to_conversation:
  - "会話記載『2026年5月更新、2026年4月まで収録』は README の vintage 表記と一致。ただし CSV の最終日付は 2026年5月初旬。"
  - "README はユーロ圏の開始を 2010年1月と書くが、実データは 2010-01-13 の1点のあと 2011年1月まで空白（論文 S019 §3.1 はユーロ圏の標本開始を 2011年1月としている）。"
  - "災害確率（horizon・risk 調整後の実確率）は別 repo R2RsquaredLSE/web-inflationdisasters（MIT、最終 push 2026-05-22、commit 173db90）で公開されている。本 repo は Q 測度の密度だけ。"
```

実装者向けメモ：読み込みは long 形式の CSV を (date, support) でピボットする。米国の 2009-10-05 は全点空欄なので除外する。21点の値は確率質量であり、0.5pt（0.005）で割って描く場合は等幅binの密度近似と明記する。公開値は **inflation調整済みのQ** なので、同じ調整をもう一度掛けない。この5年・10年のQから研究するのはhorizon・risk調整であり、forward化には同時分布・持続性モデルが別途必要（S019 §3.3）。三つの調整すべてを再現するには、調整前の名目分布Nまたは元のoption価格を別に用意する。

## 保存した PDF

中断前の担当が保存したファイルを実測。外部原文はGitへ収録しない。表のhashは内容の同定であり、再配布許諾ではない。

| ファイル | bytes | SHA-256 |
|---|---:|---|
| S002_differential-ml-with-a-difference.pdf | 814288 | `7e98e0552e59997634d5b31704ffd19d882d02c046289f24a405872cec2be0b1` |
| S005_chicagofed-cfl516-treasury-futures-basis-primer.pdf | 983457 | `bf395e037f1cd17c4882cb78acb634ba819f20de44eb7a941045d6328ea15ecc` |
| S007_nyfed-sr340-acm-term-structure.pdf | 883958 | `dc2bd05335637a66f0e7e3c6196963bafaa366a86fd7964ad5d8a7609c22f927` |
| S009_xccy-basis-swaps-backward-looking-rates.pdf | 1612386 | `3f4eed4243abb8daf907505da90568d29279b1e81f20b9616c8ed398aca049f2` |
| S010_bis-qr2603-synthetic-risk-transfers.pdf | 559075 | `1d896cd6174f4262dbc6282ad181011945bb5fd39d61528f855052b72cb36a73` |
| S011_cboe-0dtes-decoded-full-report.pdf | 512694 | `1d70a52efc8855941f2fa25baa2b48bbe4a8b52c053e44900e19567e8818ace5` |
| S013_globalx-2858-factsheet-en.pdf | 490517 | `cafbb34f64f6cd380a5db256a08f6da5cc085100c5aac66067b1569841b85076` |
| S014_neural-calibration-complete-market-model.pdf | 6698130 | `7b3a5eb3814d92136a7ded6a25ffbfd0130b6c611ad2f78d4a3e8acbb487eaf6` |
| S015_microstructural-rough-lognormal-vol.pdf | 970000 | `f0d2855553300b4c5f86ec1d1ba8b0b8ec3ec426519c32cc6f2df93478581a44` |
| S016_xccy-hjm-multiple-curve.pdf | 907169 | `eece05257a904209950d3d02916ec6d09e7097eb870fc42fd188d7a94a55690c` |
| S018_uncertainty-aware-deep-hedging.pdf | 614429 | `ae151b5f307eaab5d8b524ca08cac27088ee271ac1114914da1dba90b1f0d5f6` |
| S019_hilscher-raviv-reis-inflation-disaster-rfs.pdf | 10924497 | `212b261c950a5d666775b96770e1fdf3308e4fe0a747203e5ed577113ece8c19` |
| S021_rqmc-bernstein-betting-ci.pdf | 527979 | `a38c7673712952cd918e987077c1a09e86d432c08d03779fcf61dc6d32fc8e00` |
| S023_e-backtesting.pdf | 1626450 | `b1ba2f8772232740cf788111b071cc138e53712ae883231274b61826711e1d7e` |
| S024_scenario-realism-hedging-compatibility.pdf | 771438 | `779c1a112c6169941334a9e60c032eeda174d78d8bc3ad6bb6742b31cb12cc24` |
| S026_spx-vix-multi-maturity-calibration.pdf | 593326 | `301be1ddb9814eb054d89d10f2d04b284bfbc2390b20b80ef6ee11dfea748a1a` |
| S027_sofr-futures-smile-skew.pdf | 558715 | `a46eab469006f3ba7a2a0938b7e70e1629475ab4daf30d0dba17189e6562ea78` |
| S029_vix-derived-volatility-model.pdf | 3843822 | `e55fb5dd28d338432de0de4fdc68e0d47e2be8b4766f7b4fccb196664894cfc8` |
| S030_cfmm-lp-pricing-hedging.pdf | 3619379 | `3f1a91f796060f3b4f24615bacdbde81b5c28b196cf25a192960752112bd5693` |

## 残る確認と利用上の制約

- S008：著者稿と出版版の全差分。S009：SIAM出版版の照合。
- S020・S022：出版社本文は未読。同題のS021・S023は同一研究系列で、独立な2研究と数えない。
- S028：所属大学の書誌は確認、IEEE本文の取得不可。数値・運用制約の検証は未了。
- S002：原PDFの式の不整合を記録。著者の実験コードへの影響は未確認。
- S005：CFを掛ける対象とレバレッジ算術に原文の不整合。図の元データ変換は未確認。S007：再帰利回りと平均期待短期金利には凸性の差が残る。
- S019・S031：密度とCDF、gross/log inflationの変換、調整済みQと未調整Nの違いを実装時に保持する。
- 各recordでpartialとした範囲、データ権利・版固定・原始データ・数値再現は採用時に確認する。未再現を性能の裏付けにしない。
