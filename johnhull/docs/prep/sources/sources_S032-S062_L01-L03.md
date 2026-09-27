# 出典確認記録：S032–S062 と追加リード L01–L03

- **確認日：** 2026-09-27（Asia/Tokyo）
- **対象：** `docs/RESEARCH_HANDOFF_2026-09-27.md` §13 の S032–S062（31件）と §14 の L01–L03（3件）
- **書式：** 各出典は同文書 §11.2 の YAML 雛形に従う。補助項目として `access`・`saved_pdf`・必要に応じて `additional_primary_urls` を追加した。
- **記録完成：** 34/34件。出典全体の判定は `verified_supports_claim` 13件、`verified_partial` 21件。
- **判定の範囲：** 記録の完成は全主張の検証完了を意味しない。部分的な取得不能・主張の不支持・独立再現なしは各レコードと末尾に残す。`supported` は記した条件の下での支持であり、商用品質・投資成果の保証ではない。

## 方法

1. 会話に記録された URL を開き、転送先も記録した。HTML は WebFetch・Web読取り・curl/urllib、PDF は直接取得と `pdftotext -layout` 等で照合した。arXiv は abs の版履歴・ライセンスとPDFまたは版を固定したHTML本文を読んだ。arXiv API（export.arxiv.org）は HTTP 406 を返したため使っていない。L02/L03は著者名・題材・製品名から検索し、公式本文へ戻って同定した。
2. 雑誌論文は Crossref API（api.crossref.org/works/<DOI>）の書誌と出版社ページの両方で照合した。
3. 保存済み研究論文PDF9件は `/home/kazumasa/projects/tmp/johnhull-prep/papers/`、今回のBIS PDF1件は担当scratchに置き、全10件の実ファイルサイズ・SHA-256を再確認した。企業ページとL02のPDFは保存していない。末尾一覧はこの文書に対応する保存物であり、workspace全体のPDF一覧ではない。
4. 企業の発表・事例・インタビュー・製品ページに書かれた効果（時間短縮など）は、原文の表現と条件のまま記録し、`当事者報告` と明記した。独立した検証として扱っていない。
5. 実装者向けメモは、本文を読んだ範囲の要約（言い換え）である。

## 限界

- 論文は abstract だけでなく本文の該当節（データ・分割・比較対象・結果表）を読んだが、証明や付録の全行は精読していない。読んだ範囲は各節の「読んだもの」に書いた。
- 出版版（雑誌版）がある論文でも、有料の出版社版本文は開いていない。書誌は Crossref で確認した。
- 同一研究の abstract・HTML・PDF・出版版は独立した実証ではない。独立の再現研究は探していない（`independent_validation_of_outcome` は原則 `unknown`）。
- ページの内容は 2026-09-27 時点のもの。製品ページは予告なく変わる。

## 一覧

| ID | 検証後の題名 | 著者・発行 | 日付（版） | 種別 | アクセス | 判定 | 保存した PDF | 訂正 |
|---|---|---|---|---|---|---|---|---|
| S032 | FactSet Brings AI-Powered Fixed Income Data to Investors, First to Add MarketAxess CP+ to the Desktop | FactSet | 2025-09-09 | company_announcement | open | verified_supports_claim | — | 公式発表のみ。価格精度・データ利用権は未検証 |
| S033 | Robust Yield Curve Estimation for Mortgage Bonds Using Neural Networks | Molavipour, Javid, Ye, Löfdahl, Nechaev（SEB Group） | 2025-10-24（v1のみ） | preprint（ICAIF 2025 併設 workshop 論文） | open | verified_supports_claim | S033_robust-yield-curve-mortgage-nn.pdf | 発表の場を追記。データは SEB 社内・非公開 |
| S034 | DeepONet-based surrogate modeling for bond option pricing | Lee, Huh（成均館大）, Jeong（全南大） / AIMS Mathematics 11(3) | 2026-03-09 公開（受理 2026-03-02） | paper（査読誌） | open（CC BY 4.0） | verified_supports_claim | S034_deeponet-bond-option-aims2026.pdf | 対象はゼロクーポン債の欧州コール。Bermudan・利付債ではない |
| S035 | A deep BSDE approach for the simultaneous pricing and delta-gamma hedging of large portfolios consisting of high-dimensional multi-asset Bermudan options | Negyesi, Oosterlee | 2025-02-17（v1のみ） | preprint | open（CC BY 4.0） | verified_supports_claim | S035_deep-bsde-bermudan-delta-gamma.pdf | 正式題名に置換。計算時間の報告なし |
| S036 | Deep reinforcement learning for market making in corporate bonds: beating the curse of dimensionality | Guéant, Manziuk | arXiv 2019-10-29（v1のみ）／Applied Mathematical Finance 26(5):387–452 | preprint＋雑誌版あり | arXiv は open、雑誌版は未確認 | verified_supports_claim | S036_gueant-manziuk-drl-bond-mm.pdf | 雑誌版の書誌を追加 |
| S037 | Deep Learning of Robust Market Making under Regime-Switching Order Flow | Moret, Lillo（Scuola Normale Superiore） | 2026-09-10（v1のみ） | preprint | open（CC BY 4.0） | verified_supports_claim | S037_robust-mm-regime-switching.pdf | 模擬板は AMZN（株式）で較正。債券ではない |
| S038 | Enhancing Deep Hedging of Options with Implied Volatility Surface Feedback Information | François, Gauthier, Godin, Pérez-Mendoza | v1 2024-07-30、v2 2025-08-12 | preprint | open（CC BY 4.0） | verified_supports_claim | S038_deep-hedging-iv-surface-feedback-v2.pdf | 訂正なし。backtest 期間を追記 |
| S039 | Diffusion models for dynamic volatility surface generation and data-driven hedging | Han, Zhang, Torres, Acero, Xu（Stanford／J.P. Morgan） | v1 2026-09-11、v2 09-15、v3 09-17 | preprint | open（CC BY 4.0） | verified_supports_claim | S039_diffusion-vol-surface-hedging-v3.pdf | v2（09-15）が抜けていた。数値は v1–v3 で同一 |
| S040 | 同上（arXiv HTML v3） | 同上 | v3 = 2026-09-17 | preprint の特定版 | open | verified_supports_claim | S039 の PDF と同一版（別保存なし） | 会話の「09-17改訂」は v3 に対応 |
| S041 | Chronos-2: From Univariate to Universal Forecasting | Ansari ほか23名（AWS・Amazon ほか） | 2025-10-17（v1のみ） | preprint（technical report） | open | verified_partial | S041_chronos-2.pdf | コード・重みApache-2.0確認。金融性能未実証 |
| S042 | AI4Contracts: LLM & RAG-Powered Encoding of Financial Derivative Contracts | Mridul, Sloyan, Gupta, Seneviratne（RPI／South Cardinal） | 2025-06-01（v1のみ） | preprint | open（CC BY 4.0） | verified_partial | S042_ai4contracts-cdmizer.pdf | 評価は LLM 採点の網羅率。重要条件の完全一致は測っていない |
| S043 | Harnessing artificial intelligence for monitoring financial markets | Aquilinaほか / BIS | 2025-09-24 / WP1291 | working_paper | open | verified_partial | S043_work1291.pdf（scratch） | ARのRMSEが良い。Gemini学習期限が公式と不整合 |
| S044 | How Balyasny Asset Management built an AI research engine | OpenAI / Balyasny | 2026-03-06 | company_case_study | open | verified_partial | — | 調査基盤の事例、alpha実証なし |
| S045 | Claude for Financial Services | Anthropic / Bridgewater | 2025-07-15 | company_announcement | open | verified_partial | — | 研究支援。別のベンチマークをBridgewater成果にしない |
| S046 | Morgan Stanley uses AI evals to shape the future of financial services | OpenAI / Morgan Stanley WM | 2024-12-04（公式関連記事表示） | company_case_study | open | verified_partial | — | WM検索・会議支援。顧客同意と人の確認 |
| S047 | Hebbia’s deep research automates 90% of finance and legal work, powered by OpenAI | OpenAI / Hebbia | 本文に発行日なし | company_case_study | open | verified_partial | — | 独自評価・時間短縮は当事者報告 |
| S048 | Endex builds the future of financial analysis, powered by OpenAI’s reasoning models | OpenAI / Endex | 本文に発行日なし | company_case_study | open | verified_partial | — | 出典追跡。70%は選好率 |
| S049 | Model ML is helping financial firms rebuild with AI from the ground up | OpenAI / Chaz Englander | 2025-07-23 | company_interview | open | verified_partial | — | 現状説明と将来構想を区別 |
| S050 | Pictet turns weeks of work into hours with Claude Code | Anthropic / Pictet / Artefact | 発行日なし、導入2026年初 | company_case_study | open | verified_partial | — | 試作と本番、個別業務の短縮を区別 |
| S051 | Figma transforms ideas into interactive software with Claude | Anthropic / Figma | 発行日なし | company_case_study | open | verified_partial | — | UI試作、金融計算の検証なし |
| S052 | What AI Can (and Can't Yet) Do for Alpha | Fang、Moore / Man Group | 2025-11-13 | company_research_article | open（HTML） | verified_partial | — | 監督付き研究。live alpha・探索補正詳細なし |
| S053 | Aiden VWAP | RBC Capital Markets / Borealis AI | 日付なし、補足2024-04-23 | product | open | verified_partial | — | VWAP執行支援、独立TCAなし |
| S054 | Adaptive Auto-X | MarketAxess | 日付なし、補足2023-06-22 | product | 一部本文取得不能 | verified_partial | — | 動的本文抽出できず、公式pilot発表で補足 |
| S055 | Fluence、Mosaicによるサン・ホームの系統用蓄電池の運用最適化を開始 | Fluence / PR TIMES | 2026-03-11 | press_release | open | verified_partial | — | 2025年12月接続・2026年2月運用、成果比較なし |
| S056 | Introducing ChatGPT for Financial Services | OpenAI | 2026-09-10、関連規約09-16 | product_announcement | open | verified_partial | — | Partner Dataは別契約・制限 |
| S057 | Claude for Financial Advisors | Anthropic | 2026-09-14 | product_announcement | open | verified_partial | — | 製品と参照実装を区別 |
| S058 | Claude for Financial Advisors — reference plugin | Anthropic | commit 96fbcb4、2026-09-16 | source_repository | open | verified_supports_claim | — | Apache-2.0、非継続保守の参照コード |
| S059 | Introducing Workspace MCP: agentic financial workflows, governed by design | OpenBB | 2026-05-26 | product_announcement | open | verified_partial | — | governanceは数値正確性の証明ではない |
| S060 | LLM and agent-driven analytics | Perspective | docs版未固定、release v5.5.1 | official_documentation | open | verified_partial | — | Apache-2.0、guideとtag同一性未検証 |
| S061 | Case study: a multi-billion row tick history in a browser tab with DuckLake and DuckDB-WASM | Perspective | docs版未固定、測定DuckDB-WASM 1.4.3 | official_documentation | open | verified_partial | — | 必要部分の取得。全件のメモリ保持やPIT保証ではない |
| S062 | Manim Community | Manim Community | docs v0.21.0 | official_documentation | open | verified_partial | — | MIT、導入・日本語・レンダー未検証 |
| L01 | MarketQuoteSensitivityCalculator / JacobianCalibrationMatrix | OpenGamma Strata | docs版未固定、main 2.12.75-SNAPSHOT | official_api_documentation | open | verified_supports_claim | — | APIとJacobianの向き確認、Java実行なし |
| L02 | The Price of Liquidity: Implied Volatility of Automated Market Maker Fees | Bichuch、Feinstein | 2025-09-27 / arXiv v1 | preprint | open | verified_supports_claim | — | S030とは別研究、fee swapは提案段階 |
| L03 | Remotion — The fundamentals / renderer / Remotion License | Remotion AG / remotion-dev | v4.0.529、2026-09-25 | official_documentation_and_repository | open | verified_supports_claim | — | 独自ライセンス・組織条件、実行未検証 |

---

## S032：FactSet：MarketAxess CP+のWorkstation提供発表

```yaml
source_id: S032
url_in_conversation: https://investor.factset.com/node/18521/pdf
resolved_url: https://investor.factset.com/node/18521/pdf
claimed_title_and_date: FactSetのCP+統合、2025-09-09
verified_title: FactSet Brings AI-Powered Fixed Income Data to Investors, First to Add MarketAxess CP+ to the Desktop
verified_authors_or_organization: FactSet（企業発表）
publication_date: 2025-09-09
revision_date: null
version_or_commit: 2頁の公式ニュースリリース
accessed_at: 2026-09-27
source_type: company_announcement
verification_status: verified_supports_claim
claims:
  - claim: MarketAxess CP+がFactSet Workstationに統合された
    support_status: verified_supports_claim
    locator: PDF p.1
    quotation_or_paraphrase: 約4万銘柄のcredit/ratesの価格データへのアクセスを提供すると発表。WorkstationとAPI経由のdata feedsを挙げる。
    assumptions_and_limits: 当事者報告。価格精度・投資収益・利用可能地域の独立検証はない。発表の存在は利用権・無料データ提供を意味しない。
independent_validation_of_outcome: unknown（サービスやデータは利用していない）
license_and_redistribution: ニュースリリースは公開。CP+データの契約・保存・再配布条件は未確認。
corrections_to_conversation: 実務接続候補の存在は支持。johnhullの無償公開データ源や性能の根拠にはしない。
access: open_announcement
saved_pdf: null
```

---

## S033：Robust Yield Curve Estimation for Mortgage Bonds Using Neural Networks

**読んだもの：** arXiv abs ページ（版履歴・ライセンス）と PDF v1 全8ページの本文（§2–§5、表1–3）。

```yaml
source_id: "S033"
url_in_conversation: "https://arxiv.org/abs/2510.21347"
resolved_url: "https://arxiv.org/abs/2510.21347"
claimed_title_and_date: "Robust Yield Curve Estimation for Mortgage Bonds Using Neural Networks／会話記載 2025-10-24"
verified_title: "Robust Yield Curve Estimation for Mortgage Bonds Using Neural Networks"
verified_authors_or_organization: "Sina Molavipour, Alireza M. Javid, Cassie Ye, Björn Löfdahl, Mikhail Nechaev（SEB Group, Stockholm）"
publication_date: "2025-10-24（arXiv v1）"
revision_date: null  # 2026-09-27 時点で v1 のみ
version_or_commit: "arXiv:2510.21347v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "スウェーデンのモーゲージ債で、疎でノイズのある価格からの曲線推定を NSS／Kernel Ridge と比較した"
    support_status: supported
    locator: "Abstract; §4.1 Data & models; §4.3–4.5; Table 3"
    quotation_or_paraphrase: "SEB 市場リスク部署が集めた1日約60銘柄（残存数週間〜15年超）を日ごとに独立推定し、NSS と KR（Filipović–Pelger–Ye の kernel ridge）と比較。"
    population_market_period: "スウェーデンのモーゲージ債（covered bond）。事例日は 2020-06-03、2022-06-01、2024-06-03。日次安定性は『過去1年』だが、どの年かは本文に書かれていない。"
    assumptions_and_limits: "データは SEB 社内で非公開。時系列の train/test 分割はなく、日ごとの当てはめと、3日分の leave-one-out（10回の MC 平均）で評価。"
  - claim: "NN は NSS／KR より頑健で安定な曲線を出す"
    support_status: partially_supported
    locator: "§4.3（価格摂動・銘柄除去）, §4.4（前日比 RMSE と Hit Rate）, Table 3（LOO RMSE_ytm）"
    quotation_or_paraphrase: "摂動・銘柄除去・前日比の安定性では NN が有利と報告。一方、LOO の利回り誤差（Table 3）では KR が多くの区分で NN より小さい（例：Flat 日の Full で KR 0.0180、NN 0.1564）。著者も『滑らかさの代償に精度を失う』と書いている。"
    population_market_period: "同上"
    assumptions_and_limits: "『頑健・安定』は精度の優越ではない。NSS／KR 側のハイパーパラメータ探索の予算は記述なし（KR の重み ω_j の選び方のみ記載）。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "arXiv non-exclusive distribution license 1.0（arXiv 以外での再配布の許諾なし）。私的な研究用コピーのみ保存。"
corrections_to_conversation:
  - "発表の場：PDF の脚注に Workshop on AI Meets Quantitative Finance（ICAIF 2025 併設、シンガポール、2025年11月）とある。"
  - "Table 3 の見出し（Flat 3/6/2020・Rising 1/6/2022・Falling 3/6/2024）と本文（rising market 2020-06-03、flat market 2022-06-01）で、2020年と2022年の相場の呼び方が入れ替わっている。論文内部の不整合。"
access: "open"
saved_pdf: "S033_robust-yield-curve-mortgage-nn.pdf"
```

**実装者向けメモ：** 曲線 $y(t)$ を1隠れ層・tanh・3ニューロンの NN で表し、損失は価格誤差＋平滑さ罰則（格子上の二階差の最大値）＋ベンチマーク（SEKOIS）との傾向罰則、$L = L_\text{error} + \gamma_1 L_\text{smooth} + \gamma_2 L_\text{trend}$（§3.1, 式(15)）。採用値は LR $10^{-8}$、1000 epoch、$\gamma_1=10^3$、$\gamma_2=10^4$（§4.2）。評価の型（価格の3/5/10%摂動、1/5/10銘柄の除去、前日比 RMSE と 10bp 未満の Hit Rate、LOO）は合成 curve でそのまま再現できる。データは使えないので A01 では合成データで再構成する。

---

## S034：DeepONet-based surrogate modeling for bond option pricing

**読んだもの：** 出版社の記事ページ（WebFetch）、Crossref の書誌、PDF 全44ページのうち §1、§3.4、§4.1–4.5（表1–5）。

```yaml
source_id: "S034"
url_in_conversation: "https://www.aimspress.com/article/doi/10.3934/math.2026242"
resolved_url: "https://www.aimspress.com/article/doi/10.3934/math.2026242"
claimed_title_and_date: "DeepONet-based surrogate modeling for bond option pricing／会話記載 2026-03-09、AIMS Mathematics"
verified_title: "DeepONet-based surrogate modeling for bond option pricing"
verified_authors_or_organization: "Sanghyun Lee, Jeonggyu Huh（Sungkyunkwan University）, Seungwon Jeong（Chonnam National University、責任著者）"
publication_date: "2026-03-09（Published）。Received 2025-12-26、Revised 2026-02-13、Accepted 2026-03-02"
revision_date: null
version_or_commit: "AIMS Mathematics 11(3): 5853–5896, DOI 10.3934/math.2026242"
accessed_at: "2026-09-27"
source_type: "paper"
verification_status: verified_supports_claim
claims:
  - claim: "HW1F／G2++ の債券オプションで DeepONet・PINN・Deep BSDE を価格・vega・OOD で比較した"
    support_status: supported
    locator: "Abstract; §4.1.1 Table 1; §4.2 Table 2; §4.3 Table 3; §4.4 Table 4; §4.5 Table 5"
    quotation_or_paraphrase: "ゼロクーポン債の欧州コールを HW1F と G2++ で評価。基準値は閉形式の価格と解析 vega。DeepONet は価格ラベルで教師あり学習、PINN と DeepBSDE は PDE／BSDE 制約だけで学習。"
    population_market_period: "米国債利回り曲線の日次データ 2010–2024（3,752営業日、13年限、三次平滑化スプライン）。1日20件のオプション条件を一様乱数で生成し計75,040件。"
    assumptions_and_limits: "対象は欧州型のみ。曲線は実データだがオプション価格は閉形式の合成値。"
  - claim: "教師あり／なしの予算差、OOD 条件、データ期間"
    support_status: supported
    locator: "§4.1.3; §4.4; §4.5 Table 5"
    quotation_or_paraphrase: "分割は日付でなく銘柄単位のランダム 70/15/15（著者も時系列分割はしていないと明記）。OOD はボラ母数だけを動かす：HW は σ∈[0.01,0.10] で学習し (0.10,0.15] で評価、G2++ は (σ,η)∈[0.01,0.07]² で学習し (0.07,0.10]² で評価。RTX 3090 での学習時間は HW で DeepONet 6.58分、PINN 77.85分、DeepBSDE 34.87分。"
    population_market_period: "同上"
    assumptions_and_limits: "同じ日の曲線が学習と評価の両方に入り得る（日付ブロック分割でないため）。OOD は曲線の分布外ではない。教師ラベルの生成費用は閉形式なので計時に入っていない。価格 MSE での比較は教師ありの DeepONet に有利な設計であることを著者自身が認めている（§4.2）。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（出版社ページ表示）。コード・データの公開記述は本文に見当たらない。"
corrections_to_conversation:
  - "種別は『研究論文候補』でなく査読誌の論文と確認。"
  - "対象はゼロクーポン債の欧州コール。Bermudan や利付債オプションは扱っていない。"
  - "Table 2 の G2++・PINN の MSE（1.399×10⁻⁴）は同じ表の R²（0.6267）と整合しない。他の行から逆算した評価集合の分散を使うと、R²=0.6267 に対応する MSE は約1.399×10⁻³。誤植の可能性がある（私の計算で、原著者には未確認）。"
access: "open"
saved_pdf: "S034_deeponet-bond-option-aims2026.pdf"
```

**実装者向けメモ：** DeepONet は branch に離散化した利回り曲線、trunk に（オプション満期・債券満期・行使価格の moneyness・モデル母数）を入れる（§3.1）。母数の抽出範囲は Table 1（例：HW の $a\sim U(0.05,0.5)$、$\sigma\sim U(0.01,0.15)$、moneyness $U(0.9,1.1)$）。A02 で再現するなら、(1) 日付ブロック分割を追加して曲線の漏れを除く、(2) 教師ラベルの費用を含めた比較にする、(3) Table 2 の G2++・PINN 行は再計算で確かめる。HW1F の閉形式価格・vega は hullkit 側で独立に計算できる。

---

## S035：Negyesi–Oosterlee：Deep BSDEによるBermudanポートフォリオの価格・Greeks

**読んだもの：** arXiv abs ページと PDF v1（27ページ）の §1、§5.1–5.3（Example 1–3）、実装条件の段落、参考文献。

```yaml
source_id: "S035"
url_in_conversation: "https://arxiv.org/abs/2502.11706"
resolved_url: "https://arxiv.org/abs/2502.11706"
claimed_title_and_date: "Negyesi–Oosterlee：Deep BSDEによるBermudanポートフォリオの価格・Greeks／会話記載 2025-02-17"
verified_title: "A deep BSDE approach for the simultaneous pricing and delta-gamma hedging of large portfolios consisting of high-dimensional multi-asset Bermudan options"
verified_authors_or_organization: "Balint Negyesi, Cornelis W. Oosterlee"
publication_date: "2025-02-17（arXiv v1）"
revision_date: null  # 2026-09-27 時点で v1 のみ
version_or_commit: "arXiv:2502.11706v1（27 pages, 10 figures, 8 tables）"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "多資産 Bermudan の価格と delta／gamma を deep BSDE で同時に求める"
    support_status: supported
    locator: "Abstract; §4; §5.1–5.3"
    quotation_or_paraphrase: "離散反射 BSDE を One Step Malliavin（OSM）法で離散化し、Γ過程（2次感応度、cross-gamma を含む）を NN 回帰 MC で解く。"
    population_market_period: "合成のみ。Example 1：Heston 2因子（T=0.25、行使日10回）。Example 2：d 資産の幾何平均バスケット Bermudan コール（d は最大100、行使日 R=5/20/100）。Example 3：20資産上の25契約のポートフォリオ（T=1年）。"
    assumptions_and_limits: "主な評価は hedge P&L 分布（分散・VaR・ES）。価格誤差表が主役ではない。"
  - claim: "参照値の独立性と費用"
    support_status: partially_supported
    locator: "§5.1（Example 1 の参照値）, §5.2（幾何バスケットの1次元化）, 実装条件の段落（p.13）"
    quotation_or_paraphrase: "Example 1 のヘッジ手段の参照価格・Greeks は著者自身の algorithm 1 で計算しており独立でない。Example 2 の幾何バスケットは1次元問題に帰着できるため独立参照を作れる。比較相手は Huré–Pham–Warin の DBDP／RDBDP と Chen–Wan（2021）。"
    population_market_period: "同上"
    assumptions_and_limits: "計算時間・費用の表は見当たらない（本文検索で runtime／wall-clock の記述なし）。環境は RTX 3090、TensorFlow 2.15、4隠れ層×50ニューロン。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（arXiv 表示）"
corrections_to_conversation:
  - "正式題名に置換（会話の名称は説明名）。"
  - "計算費用の比較は本文にない。『費用』を確認項目にしていたが、論文からは取れない。"
access: "open"
saved_pdf: "S035_deep-bsde-bermudan-delta-gamma.pdf"
```

**実装者向けメモ：** 幾何平均バスケットは $d$ 次元でも1次元の参照解が作れる（§5.2、母数は Chen–Wan 2021：$T=2$、$X_0=100$、$r=0$、$q=0.02$、相関0.75）ため、F03／A02 の「行使 oracle」を独立に検証する教材に使える。cross-gamma を消すヘッジ手段として、対角は欧州プット、非対角は Margrabe の交換オプション（閉形式）を使う設計（§5.2）はそのまま流用できる。コードは本文が github.com/balintnegyesi/OSM-delta-gamma-hedging を「公開予定」としている（存在確認は下の実装者メモ集約を参照）。

---

## S036：Guéant–Manziuk：深層強化学習による社債マーケットメイク

**読んだもの：** arXiv abs ページ、PDF v1（70ページ）の §1–§4 の要所（RFQ モデル・目的関数・数値例の設定）、Crossref の雑誌版書誌。

```yaml
source_id: "S036"
url_in_conversation: "https://arxiv.org/abs/1910.13205"
resolved_url: "https://arxiv.org/abs/1910.13205"
claimed_title_and_date: "Guéant–Manziuk：深層強化学習による社債マーケットメイク／会話記載 2019年"
verified_title: "Deep reinforcement learning for market making in corporate bonds: beating the curse of dimensionality"
verified_authors_or_organization: "Olivier Guéant, Iuliia Manziuk（Université Paris 1 Panthéon-Sorbonne）。J.P. Morgan の支援と Institut Louis Bachelier の枠組みで実施と脚注に記載"
publication_date: "2019-10-29（arXiv v1）。雑誌版：Applied Mathematical Finance 26(5):387–452、号の日付 2019-09-03、オンライン 2020-02-10（Crossref）"
revision_date: null
version_or_commit: "arXiv:1910.13205v1; DOI 10.1080/1350486X.2020.1714455"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "多数銘柄・在庫を含む社債マーケットメイクを深層強化学習で解く"
    support_status: supported
    locator: "Abstract; §2（モデル）; §3.2（actor-critic）; §4（数値結果）"
    quotation_or_paraphrase: "Avellaneda–Stoikov 型モデルの多銘柄版を、モデルベースの actor-critic 型アルゴリズムで近似。"
    population_market_period: "欧州社債20銘柄（守秘のため番号で匿名化）。RFQ 到着率・平均サイズ・約定確率の母数を表で提示。"
    assumptions_and_limits: "すべてモデルからのシミュレーション。実運用の成績は報告していない。"
  - claim: "RFQ モデル・約定過程・目的関数"
    support_status: supported
    locator: "§2.1–2.2; §4.1 Table 1–2"
    quotation_or_paraphrase: "銘柄・売買側ごとに RFQ はポアソン到着。提示との距離 δ に対する約定確率 f(δ) は減少関数（数値例は SU Johnson 型の母数化）。目的は割引付き無限期間の期待 P&L から在庫罰則 ψ(q) を引いたもの。ψ は ½γq'Σq（分散）または γ√(q'Σq)（標準偏差）。"
    population_market_period: "同上"
    assumptions_and_limits: "差分法との照合は1–2銘柄のみ。8・20銘柄は参照解がなく、相関を無視した戦略との平均報酬比較で評価。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "arXiv non-exclusive distribution license 1.0。雑誌版（Taylor & Francis）のアクセス条件は未確認。"
corrections_to_conversation:
  - "雑誌版の書誌を追加（Applied Mathematical Finance 26(5):387–452, DOI 10.1080/1350486X.2020.1714455）。S037 の参考文献にも同じ書誌がある。"
access: "open（arXiv）。雑誌版は未確認"
saved_pdf: "S036_gueant-manziuk-drl-bond-mm.pdf"
```

**実装者向けメモ：** A03 の最小 simulator は §2 の構成（銘柄×売買側のポアソン RFQ、約定確率 $f(\delta)$、在庫罰則 $\tfrac12\gamma q^\top\Sigma q$）をそのまま使える。1–2銘柄なら差分法（HJB）で参照解を作れるので、RL 方策の独立テストはこの規模で行う。数値例の母数（Table 1–2、20銘柄）は論文に全部載っている。

---

## S037：Deep Learning of Robust Market Making under Regime-Switching Order Flow

**読んだもの：** arXiv abs ページと PDF v1（40ページ）の §1–§2（模擬板と較正）、限界・結論の段落。

```yaml
source_id: "S037"
url_in_conversation: "https://arxiv.org/abs/2609.11614"
resolved_url: "https://arxiv.org/abs/2609.11614"
claimed_title_and_date: "Deep Learning of Robust Market Making under Regime-Switching Order Flow／会話記載 2026-09-10"
verified_title: "Deep Learning of Robust Market Making under Regime-Switching Order Flow"
verified_authors_or_organization: "Felipe Moret, Fabrizio Lillo（Scuola Normale Superiore di Pisa）"
publication_date: "2026-09-10（arXiv v1）"
revision_date: null  # 2026-09-27 時点で v1 のみ
version_or_commit: "arXiv:2609.11614v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "模擬指値注文板で、持続的な一方向フローと在庫リスクを扱うマーケットメイク"
    support_status: supported
    locator: "Abstract; §1 contributions; §2 Market model / Data and calibration; Limitations"
    quotation_or_paraphrase: "zero-intelligence（Santa Fe）型の事象駆動 LOB simulator 上で、分布型 DQN（C51）の MM を GLFT と比較。持続的な方向性フローで在庫飽和による大きな drawdown が出ることを示し、ベイズ変化点フィルタと待ち行列調整の露出不均衡を状態に加え、低収益 regime を重み付ける scenario-bandit で改善。"
    population_market_period: "Santa Fe 母数（λ=0.06、μ=0.10、θ_cxl=0.02）は LOBSTER の AMZN Level-3 データ（2025-08-01〜2025-09-10 の28営業日、寄付・引け前後60分を除外、約2.9×10⁷メッセージ）で較正。"
    assumptions_and_limits: "著者の限界：評価はすべて模擬データ、1単位・各側1注文のみ、regime 幅は固定。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（arXiv 表示）。コード・学習済みモデルは github.com/felipemoret77/robust-deep-market-making と本文に記載。"
corrections_to_conversation:
  - "模擬板の較正対象は米国株（AMZN）。債券 RFQ ではない（会話の注意書きどおり）。"
access: "open"
saved_pdf: "S037_robust-mm-regime-switching.pdf"
```

**実装者向けメモ：** A03 の stress 設計（買い成行確率を区分定数にし、持続時間 $\tau_r$ を伸ばす）は §2 末尾〜§5 の構成を借りられる。GLFT 側の約定強度 $\Lambda(\delta)=Ae^{-\kappa\delta}$ は、模擬板上で打ち切り待ち時間から推定している（Laruelle ら・Guéant–Lehalle の方法）。比較は1000エピソード×5000事象の paired-seed で、Wilcoxon 検定を付けている。

---

## S038：Enhancing Deep Hedging of Options with Implied Volatility Surface Feedback Information

**読んだもの：** arXiv abs ページ（版履歴）と PDF v2（50ページ）の §2（目的関数）、§3（JIVR）、§4.1–4.2（設定・比較対象）、§5（backtest）。

```yaml
source_id: "S038"
url_in_conversation: "https://arxiv.org/abs/2407.21138"
resolved_url: "https://arxiv.org/abs/2407.21138"
claimed_title_and_date: "Enhancing Deep Hedging of Options with Implied Volatility Surface Feedback Information／会話記載 2024年初稿、2025-08-12改訂"
verified_title: "Enhancing Deep Hedging of Options with Implied Volatility Surface Feedback Information"
verified_authors_or_organization: "Pascal François, Geneviève Gauthier（HEC Montréal）, Frédéric Godin, Carlos Octavio Pérez-Mendoza（Concordia University）"
publication_date: "2024-07-30（arXiv v1）"
revision_date: "2025-08-12（arXiv v2。PDF 表紙の日付は 2025-08-14）"
version_or_commit: "arXiv:2407.21138v2"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "S&P 500 オプションで IV surface の情報を使う費用込みの hedge"
    support_status: supported
    locator: "Abstract; §2.1（自己資金条件と比例費用 κ）; §4.1.2; §5"
    quotation_or_paraphrase: "方策勾配型の深層 RL。状態に IV surface の係数（JIVR モデル）を入れると、実務 BS delta・Leland delta・smile-implied delta より良い。取引費用があると差が大きい。"
    population_market_period: "JIVR は 1996-01-04〜2020-12-31 の OptionMetrics データで推定。学習は模擬経路40万本、評価は模擬経路10万本。backtest は 2020-12-31〜2023-10-31 の実取引価格、残存63営業日の ATM 近辺（±10%）欧州コールの売り 4,134件。"
    assumptions_and_limits: "費用は比例費用 κ∈{0, 0.05%, 0.5%, 1%}。backtest では IV 係数を除いた RL も比較対象に入れている。"
  - claim: "対象期間・同一実現経路・費用・方策 baseline・データ利用権"
    support_status: partially_supported
    locator: "§4.1.1–4.2; §5; 表紙脚注（Data availability statement）"
    quotation_or_paraphrase: "期間・費用・baseline は上記のとおり確認。backtest は全戦略を同じ4,134契約で比較。生データは OptionMetrics から入手（有償）、推定母数はコードに同梱。"
    population_market_period: "同上"
    assumptions_and_limits: "模擬評価で全戦略が同じ10万本の経路を共有するかは、本文の記述から明示的には確認していない。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "論文は CC BY 4.0。コードは github.com/cpmendoza/DeepHedging_JIVR（本文記載）。OptionMetrics の生データは再配布不可の商用データ。"
corrections_to_conversation: []
access: "open"
saved_pdf: "S038_deep-hedging-iv-surface-feedback-v2.pdf"
```

**実装者向けメモ：** 状態は $(\tau_t, S_t, \{\beta_{t,i}\}_{i=1}^5, h_{t,R}, \delta_t)$（費用ありのとき現在保有 $\delta_t$ を追加、§5）。罰則は MSE・SMSE（損だけ罰する半二乗）・CVaR95/99 の3種で、RNN と FNN を組み合わせた構造。A04 の最小版では JIVR の代わりに合成 surface 因子を使い、比較対象（DH、DH-L、SI）と罰則3種の組み合わせだけを再現するのが現実的。

---

## S039：Diffusion models for dynamic volatility surface generation and data-driven hedging

**読んだもの：** arXiv abs ページ（版履歴）、PDF v3（19ページ）の §1–§4（データ・学習・静的裁定・hedging・Table 1）。v1・v2 の PDF も取得して、本文の数値と日付を v3 と比較した（v1・v2 は保存していない）。

```yaml
source_id: "S039"
url_in_conversation: "https://arxiv.org/abs/2609.13402"
resolved_url: "https://arxiv.org/abs/2609.13402"
claimed_title_and_date: "Diffusion models for dynamic volatility surface generation and data-driven hedging／会話記載 2026-09-11初稿、09-17改訂"
verified_title: "Diffusion models for dynamic volatility surface generation and data-driven hedging"
verified_authors_or_organization: "Yinbin Han, Jack Yuxiang Zhang, Renyuan Xu（Stanford University）, Manuel Torres, Fernando Acero（J.P. Morgan QTR AI Research）。J.P. Morgan AI Faculty Research Award の支援"
publication_date: "2026-09-11（arXiv v1）"
revision_date: "v2 2026-09-15、v3 2026-09-17（PDF 表紙の日付は 2026-09-18）"
version_or_commit: "arXiv:2609.13402v3"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "現物リターンと IV surface を同時に生成し、data-driven hedging で経済的な有用性を評価"
    support_status: supported
    locator: "Abstract; §2（AD-Seq-Vol, AD-Seq-Vol-FT）; §3（式(12)）; §4 Table 1"
    quotation_or_paraphrase: "条件付き拡散モデル（AD-Seq-Vol）で21日の履歴から翌日の（SPX 対数リターン、対数 IV surface）を生成。静的裁定（calendar・call spread・butterfly）の罰則を報酬にした LoRA 微調整版（-FT）も作る。"
    population_market_period: "OptionMetrics の SPX 日次オプション 2000-01-03〜2023-02-28。学習 2000-01-03〜2018-06-16、評価 2018-07-01〜2023-02-28。"
    assumptions_and_limits: "2018-06-17〜06-30 はどちらにも使われていない（理由の記述なし）。surface は 11 moneyness × 9 満期の格子に Nadaraya–Watson で平滑化したもの。"
  - claim: "無裁定 penalty の限界"
    support_status: supported
    locator: "§2（式(4)の罰則 L）; §4（静的裁定の評価）"
    quotation_or_paraphrase: "-FT は違反を『ほぼゼロ』に減らすと書いており、ゼロの保証ではない。罰則は離散格子上の条件だけを見る。"
    population_market_period: "同上"
    assumptions_and_limits: "静的裁定の検査は格子点上の不等式。格子外・動的裁定は対象外。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（arXiv 表示）。コードは github.com/yinbinhan/volatility-surface-simulation（本文記載）。OptionMetrics データは再配布不可の商用データ。"
corrections_to_conversation:
  - "版は3つある：v1 2026-09-11、v2 2026-09-15、v3 2026-09-17。会話は v2 に触れていない。"
  - "v1→v2 は引用形式（番号→著者年）の変更で18→19ページ。v2→v3 は謝辞脚注の位置の変更。本文中の小数の数値（Table 1 を含む）とデータ期間は v1・v2・v3 で同一（私が抽出して比較）。"
access: "open"
saved_pdf: "S039_diffusion-vol-surface-hedging-v3.pdf"
```

**実装者向けメモ：** hedging は Cont–Vuletić（2025）の一期間問題（式(12)）：生成した $N$ 個の翌日シナリオ上で、目標の価格変化を切片＋ヘッジ手段の線形和で近似し、保有変更に費用罰則（半 bid–ask を単価に使う）を付ける。目標は moneyness $m_0\in\{0.75,0.8,0.9,1.1,1.2,1.25\}$ の long straddle、評価は実現した翌日の1期間 tracking error $\varepsilon_t$（USD）。COVID 期間（2020-02-13〜07-21）を除いた集計もある。比較対象の VolGAN は著者が独自実装したもの（原著者の報告値より良いと注記）。A05 で使うなら、生成器を FHS／block bootstrap に差し替えて同じ式(12)で比べる構成が最小。

---

## S040：同上：会話で参照されたHTML v3

**読んだもの：** https://arxiv.org/html/2609.13402v3 を取得（HTTP 200）し、題名とデータ期間の記述を確認した。

```yaml
source_id: "S040"
url_in_conversation: "https://arxiv.org/html/2609.13402v3"
resolved_url: "https://arxiv.org/html/2609.13402v3"
claimed_title_and_date: "S039 の HTML v3／会話の改訂日と v3 の対応は未確認"
verified_title: "Diffusion models for dynamic volatility surface generation and data-driven hedging"
verified_authors_or_organization: "S039 と同じ"
publication_date: "2026-09-11（v1）"
revision_date: "2026-09-17（v3）"
version_or_commit: "arXiv:2609.13402v3（HTML 版）"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_supports_claim
claims:
  - claim: "S039 の本文の参照先（v3）"
    support_status: supported
    locator: "HTML 本文のデータ前処理段落"
    quotation_or_paraphrase: "HTML v3 にも 2000–2023 年、学習の終わり 2018-06-16、評価の始まり 2018-07-01 の記述がある。"
    population_market_period: "S039 と同じ"
    assumptions_and_limits: "S039 と同一研究の別表示であり独立の証拠ではない。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0"
corrections_to_conversation:
  - "会話の『09-17改訂』は v3 に対応する。v1–v3 で結果の数値は同一なので、版の混在による実験結果の食い違いは起きない。"
access: "open"
saved_pdf: "なし（S039 の v3 PDF と同じ版）"
```

---

## S041：Chronos-2

**読んだもの：** arXiv abs ページと PDF v1（31ページ）の §1、§4（学習データ）、§5（fev-bench・GIFT-Eval・Chronos Benchmark II・事例・ablation）。

```yaml
source_id: "S041"
url_in_conversation: "https://arxiv.org/abs/2510.15821"
resolved_url: "https://arxiv.org/abs/2510.15821"
claimed_title_and_date: "Chronos-2／会話記載 2025年"
verified_title: "Chronos-2: From Univariate to Universal Forecasting"
verified_authors_or_organization: "Abdul Fatir Ansari, Oleksandr Shchur ほか計23名（Amazon Web Services、Amazon、Freiburg 大、JKU Linz ほか）。表紙の表記は Technical Report"
publication_date: "2025-10-17（arXiv v1）"
revision_date: null  # 2026-09-27 時点で v1 のみ
version_or_commit: "arXiv:2510.15821v1"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_partial
claims:
  - claim: "多変量・共変量付き時系列の zero-shot 予測"
    support_status: supported
    locator: "Abstract; §3（group attention）; §5.1–5.3"
    quotation_or_paraphrase: "group attention で複数系列の情報を共有する in-context learning。fev-bench（100 task）・GIFT-Eval（97 task／55 dataset）・Chronos Benchmark II で最良と報告。"
    population_market_period: "公開ベンチマーク。事例はエネルギー（例：ドイツの電力価格 EPF-DE）と小売（Rossmann）。金融市場の事例はない。"
    assumptions_and_limits: "基本モデル 120M パラメータ、小型 28M。推論は A10G 1枚で毎秒300系列（1,024系列・文脈長2048・予測長64の条件）。"
  - claim: "学習データの重複"
    support_status: supported
    locator: "§4.1–4.2; §5.2 GIFT-Eval 段落; §5.4"
    quotation_or_paraphrase: "学習コーパスは GIFT-Eval の評価部分とは重ならないようにしたが、GIFT-Eval の一部 dataset の学習部分とは一部重なると著者が明記。厳密な zero-shot は合成データだけで学習した版（§5.4）を参照せよとしている。多変量・共変量の学習は全部合成データ。"
    population_market_period: "同上"
    assumptions_and_limits: "fev-bench の表には他モデルの leakage（%）列がある（Chronos-2 は 0%）。"
  - claim: "重みの公開とライセンス"
    support_status: verified_supports_claim
    locator: "https://huggingface.co/amazon/chronos-2 の公式model card、https://github.com/amazon-science/chronos-forecasting/blob/main/LICENSE"
    quotation_or_paraphrase: "Amazonのmodel cardはapache-2.0、公式コードrepoのLICENSEもApache License 2.0と表示。2026-09-27に確認。"
    population_market_period: null
    assumptions_and_limits: "重み・コードは未取得、commit未固定。利用前にversionとモデルファイルのhashを固定し、学習データの権利・重複は別に確認する。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "論文は arXiv non-exclusive distribution license 1.0。公式コードとamazon/chronos-2 model cardはApache-2.0。データの権利を一括して許諾するものではない。"
corrections_to_conversation:
  - "正式題名『Chronos-2: From Univariate to Universal Forecasting』。査読付きの正式版は abs ページに記載がない（technical report）。"
access: "open"
saved_pdf: "S041_chronos-2.pdf"
```

**実装者向けメモ：** A06 で使うときは、(1) 合成データのみで学習した版と通常版の差を見る、(2) 評価期間が公開コーパスに含まれ得るので「完全未見」と呼ばない、(3) ベースラインは同論文の表にもある AutoARIMA／AutoETS／SeasonalNaive に加え、対象別の HAR 等を置く。論文の強みは共変量付き task（エネルギー・小売）であり、金融リターンでの優位は示していない。

---

## S042：AI4Contracts: LLM & RAG-Powered Encoding of Financial Derivative Contracts

**読んだもの：** arXiv abs ページと PDF v1（8ページ）全体（§4 データ、§5 baseline、§6 CDMizer、§7 評価、Table 1–2）。

```yaml
source_id: "S042"
url_in_conversation: "https://arxiv.org/abs/2506.01063"
resolved_url: "https://arxiv.org/abs/2506.01063"
claimed_title_and_date: "AI4Contracts: LLM & RAG-Powered Encoding of Financial Derivative Contracts／会話記載 2025-06-01"
verified_title: "AI4Contracts: LLM & RAG-Powered Encoding of Financial Derivative Contracts"
verified_authors_or_organization: "Maruf Ahmed Mridul, Aparna Gupta, Oshani Seneviratne（Rensselaer Polytechnic Institute）, Ian Sloyan（South Cardinal）"
publication_date: "2025-06-01（arXiv v1）"
revision_date: null  # 2026-09-27 時点で v1 のみ
version_or_commit: "arXiv:2506.01063v1（8 pages, 3 figures, 2 tables）"
accessed_at: "2026-09-27"
source_type: "preprint"
verification_status: verified_partial
claims:
  - claim: "契約記述から CDM への変換を、合成30契約で評価した"
    support_status: supported
    locator: "§4 Data Collection and Synthesis; §7 Experimental Evaluation; Table 1"
    quotation_or_paraphrase: "FINOS CDM リポジトリの CDM 例858件から LLM で自然文の契約記述を合成（実 term sheet 2件＝RBC Capital Markets と J.P. Morgan を参考入力に使用）。6契約種別×5件＝30件を、Baseline／CDMizer × RAG 有無の4構成で評価。"
    population_market_period: "IRS、Equity Swap、Equity Option、Commodity Option、FX Derivatives、CDS の6種別。すべて合成記述。"
    assumptions_and_limits: "fine-tuning は token 制限等のため評価構成から外した。主モデルは Llama-3.1-8B-Instruct（比較に Mistral-7B-Instruct-v0.3、Llama-3.2-3B-Instruct）。"
  - claim: "重要条件の完全一致・意味検証の範囲"
    support_status: not_supported
    locator: "§7.1 Evaluation Framework; §7.2"
    quotation_or_paraphrase: "評価は (1) 生成キーがスキーマに存在する割合、(2) スキーマ適合、(3) LLM が抽出した情報を『捕捉・未捕捉・余計』に分けて重み付けした網羅率（μ=0.3、ε=0.1）。CDMizer の構文・スキーマ 100% はテンプレート方式による当然の結果と著者が書いている。"
    population_market_period: "同上"
    assumptions_and_limits: "正解 CDM とのフィールド単位の完全一致、日付・CF・価格の再計算による意味検証はしていない。網羅率も LLM 採点。"
independent_validation_of_outcome: "unknown"
license_and_redistribution: "CC BY 4.0（arXiv 表示）。コード公開の記述は本文に見当たらない。使用した CDM の版番号も本文に記載がない。"
corrections_to_conversation:
  - "『重要条件完全一致』はこの論文の評価指標ではない。A07 の受入基準は論文から借りられないので、自前の gold と mutation test で作る必要がある。"
access: "open"
saved_pdf: "S042_ai4contracts-cdmizer.pdf"
```

**実装者向けメモ：** CDMizer の要点は、CDM スキーマから決定的にテンプレート（JSON 木）を作り、深さ $d$（論文は4）以下の部分木ごとに LLM へ埋めさせることで、構文とスキーマ適合を構造的に保証する点（§6）。A07 ではこの「スキーマ由来テンプレート＋部分木単位の充填」を採り、評価は論文の LLM 採点でなく、手で作った正解との critical field 一致と CF・価格の再計算で行う。

---

<a id="s043"></a>
## S043：BIS の市場機能監視

**読んだもの：** BIS書誌ページと39頁のPDF（印刷pp8–19、Table 1–3、Graph 2・4・5、Appendix A.3）。Graph 2は画像でも確認した。Googleのモデルカードは学習期限の照合にのみ使用。

```yaml
source_id: S043
url_in_conversation: https://www.bis.org/publ/work1291.htm
resolved_url: https://www.bis.org/publications/working-paper-1291-harnessing-artificial-intelligence-monitoring-financial-markets
claimed_title_and_date: Harnessing artificial intelligence for monitoring financial markets、2025-09-24
verified_title: Harnessing artificial intelligence for monitoring financial markets
verified_authors_or_organization: Matteo Aquilina, Douglas Araujo, Gaston Gelos, Taejin Park, Fernando Pérez-Cruz / BIS
publication_date: 2025-09-24
revision_date: null
version_or_commit: BIS Working Papers No 1291、September 2025。改訂表示なし。
accessed_at: 2026-09-27
source_type: working_paper
verification_status: verified_partial
claims:
  - claim: RNNの市場機能悪化予測と、重要入力を使ったLLMニュース検索
    support_status: supported
    locator: §4.1–4.2、§5.1–5.4、Table 3、Appendix A.3
    quotation_or_paraphrase: LSTMが125市場系列等からEUR/JPYの対USD三角裁定乖離の20営業日平均を60営業日先から予測。入力重みをニュース探索に利用する。Table 3の予測損失はARより0.0007大きく、ARへの誤差優越は示していない。
    population_market_period: LSEG Tick Historyの1分気配を日次化、Bloomberg等。学習は2020年末まで、2021–2024年をpseudo out-of-sample。開始・終了の厳密な日付は未同定（Graph 2は約2006–2024年）。
    assumptions_and_limits: 重みは予測への寄与であり因果効果ではない。系列の取得時点・全ハイパーパラメータ選択過程・データ契約は未検証。
  - claim: LLMは対象イベントを事前学習していない
    support_status: not_supported
    locator: §5.4・Graph 5（印刷pp18–19）；Google Gemini 2.5 Pro Model Card（2025-06-27改訂、PDF p7）
    quotation_or_paraphrase: 論文は2023年7月前半の約1000記事をGemini 2.5 Proへ渡し、同年10月の監視候補を得る。学習期限を2023年初とするが、Google公式カードは2025年1月と記載する。
    population_market_period: LLM部分は2023年の一事例。RNNの時系列分割とは別。
    assumptions_and_limits: 論文のモデルIDは固定されておらず、後年の知識の影響を除外できない。実際に未来情報を使ったと断定するものではない。
independent_validation_of_outcome: unknown（論文の結果を再実行していない）
license_and_redistribution: PDFはBIS ©2025 All rights reserved。出典付きの短い抜粋・翻訳を許可。LSEG/Bloombergの原データは別契約で、再配布許諾は未確認。
corrections_to_conversation:
  - 研究の存在と構成は支持。ARより高精度、因果説明、LLMの完全未見検証の根拠にはしない。
access: open（旧URLは転送。新PDFを直接取得）
saved_pdf: /home/kazumasa/projects/tmp/johnhull-prep/scratch/codex_ch26_37/S043_work1291.pdf
additional_primary_urls:
  - https://www.bis.org/publications/working-paper-1291-harnessing-artificial-intelligence-monitoring-financial-markets.pdf
  - https://storage.googleapis.com/deepmind-media/Model-Cards/Gemini-2-5-Pro-Model-Card.pdf
```

<a id="s044"></a>
## S044：Balyasny Asset Management

**読んだもの：** OpenAIの事例記事本文（研究基盤・モデル選定・中央銀行発言・M&A分析・人の判断）。

```yaml
source_id: S044
url_in_conversation: https://openai.com/index/balyasny-asset-management/
resolved_url: https://openai.com/index/balyasny-asset-management/
claimed_title_and_date: BalyasnyのAI研究基盤、2026-03-06
verified_title: How Balyasny Asset Management built an AI research engine
verified_authors_or_organization: OpenAI、Balyasny Asset Managementの担当者
publication_date: 2026-03-06
revision_date: null
version_or_commit: 公開事例ページ。確認本文はGPT-5.4を記載、更新履歴なし。
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: 投資調査基盤が中央銀行発言やM&A成立確率の更新を支援
    support_status: supported
    locator: 本文のCentral Bank Speech Analyst、M&A workflow、evaluationの段落
    quotation_or_paraphrase: 文書・ニュースと社内ツールを接続し、M&Aの新情報を反映。中央銀行発言の比較は2日から約30分へ短縮したとする。独自評価とチームからのフィードバックを用いる。
    population_market_period: 約180投資チームの企業事例。結果の測定期間・標本数は非開示。
    assumptions_and_limits: 当事者報告。成立確率の校正、取引後損益、比較実験は示されず、人が判断する研究支援。
independent_validation_of_outcome: unknown（利用・性能再現なし）
license_and_redistribution: 公開記事。社内基盤・評価データの公開ライセンスは確認できず、社内文書や配信データの利用権は別途必要。
corrections_to_conversation: 導入構成と用途を支持する事例。AIによる自律運用やalpha改善の実証とは扱わない。
access: open
saved_pdf: null
```

<a id="s045"></a>
## S045：Claude for Financial Services と Bridgewater

**読んだもの：** 2025年のAnthropic発表本文とBridgewater AIA Labs担当者の発言。

```yaml
source_id: S045
url_in_conversation: https://www.anthropic.com/news/claude-for-financial-services
resolved_url: https://www.anthropic.com/news/claude-for-financial-services
claimed_title_and_date: Claude for Financial Services、2025-07-15
verified_title: Claude for Financial Services
verified_authors_or_organization: Anthropic、Bridgewater AIA Labs CTO Aaron Linsky
publication_date: 2025-07-15
revision_date: null
version_or_commit: 発表ページ、Claude 4の時点。更新履歴・個別buildは未固定。
accessed_at: 2026-09-27
source_type: company_announcement
verification_status: verified_partial
claims:
  - claim: BridgewaterのInvestment Analyst AssistantがPython・可視化・反復分析を支援
    support_status: supported
    locator: Bridgewater AIA Labsの引用段落；What this means for your team
    quotation_or_paraphrase: 2023年以来の開発を説明し、AssistantがPythonコードや図を作り、対話しながら調査を進めるとする。発表全体は出典リンク付き調査と金融データ接続を紹介。
    population_market_period: Bridgewaterの研究補助事例。定量的な利用期間・評価標本は未記載。
    assumptions_and_limits: 当事者報告。記事中の83% Excel等の別ベンチマークをBridgewaterの成果へ転用しない。接続機能には当日提供と数週間内の予告が混在。
independent_validation_of_outcome: unknown（モデル・業務成果を再現していない）
license_and_redistribution: 発表は公開。商用データ接続は顧客契約・使用制限に従い、記事の公開はデータやAssistantの再配布許可ではない。
corrections_to_conversation: 開発・研究支援の事例として支持。2025年発表だけで2026年の全提供範囲や投資収益は確定しない。
access: open
saved_pdf: null
```

<a id="s046"></a>
## S046：Morgan Stanley Wealth Management

**読んだもの：** OpenAI本文の社内検索、評価方法、Debriefの顧客同意・アドバイザー確認。日付は同社Endexページの関連記事リンクでも照合。

```yaml
source_id: S046
url_in_conversation: https://openai.com/index/morgan-stanley/
resolved_url: https://openai.com/index/morgan-stanley/
claimed_title_and_date: Morgan Stanleyの検索・Debrief、日付未固定
verified_title: Morgan Stanley uses AI evals to shape the future of financial services
verified_authors_or_organization: OpenAI、Morgan Stanley Wealth Management
publication_date: 2024-12-04（OpenAIの関連記事リンク表示。記事本文の日付欄はなし）
revision_date: null
version_or_commit: 公開事例ページ、版表示なし
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: WMの社内知識検索と評価・顧客同意を伴う会議支援
    support_status: supported
    locator: Fine-tuning AI with evals；Automating administrative tasks with AI Morgan Stanley Debrief
    quotation_or_paraphrase: 専門家の評価集合と日々の回帰評価で検索・要約を確認する。Debriefは顧客同意のある録音からメモや追跡メールを下書きし、アドバイザーが確認・修正する。
    population_market_period: Wealth Management、GPT-4/Whisperを用いる記述。98%超のチーム採用は当事者報告で、測定期間・分母の詳細は非開示。
    assumptions_and_limits: 採用率は回答正確性ではない。金利トレーディング部門のP&L・リスク計算の検証ではない。
independent_validation_of_outcome: unknown（独立した性能・業務成果の検証なし）
license_and_redistribution: 記事は公開。社内知識、録音、評価集合、顧客データの公開・再利用許諾はない。記事のzero retentionは当該契約構成の説明。
corrections_to_conversation: 検索と評価、同意・人の確認の事例として支持。全社・全APIに同一の権限や保持条件があるとはしない。
access: open（HTMLの直接取得は403、Web読取りで本文確認）
saved_pdf: null
additional_primary_urls:
  - https://openai.com/index/endex/
```

<a id="s047"></a>
## S047：Hebbia Matrix

**読んだもの：** OpenAI事例のMatrix、モデルの使い分け、出典付き成果物、独自比較の説明。

```yaml
source_id: S047
url_in_conversation: https://openai.com/index/hebbia/
resolved_url: https://openai.com/index/hebbia/
claimed_title_and_date: Hebbia Matrixの文書分析、2025年
verified_title: Hebbia’s deep research automates 90% of finance and legal work, powered by OpenAI
verified_authors_or_organization: OpenAI、Hebbia
publication_date: null
revision_date: null
version_or_commit: 公開事例ページ。本文はo3-mini・o1・GPT-4oを記載。公開年・版は一次本文で未同定。
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: 複数文書の比較と根拠を追跡できる金融・法務調査を支援
    support_status: supported
    locator: Matrixの並列エージェント、model routing、引用付き回答の本文段落
    quotation_or_paraphrase: 長い文書を横断して項目を比較し、融資条件や投資メモを作る構成を説明する。独自評価92%対RAG68%、案件あたり時間短縮等を報告する。
    population_market_period: 金融・法務の顧客事例。評価集合・期間・サンプル数・採点者は十分に公開されない。
    assumptions_and_limits: 当事者報告。表題の90%は普遍的な自動化率や正確性の証明ではなく、独自ベンチマークも追試できていない。
independent_validation_of_outcome: unknown
license_and_redistribution: 公開記事。製品・評価集合・入力文書の利用権と再配布条件は別途確認が必要。
corrections_to_conversation: 構成・用途を支持。2025年という日付は本文に表示がなく、直接HTML取得も403のため未確認として残す。
access: open（Web読取り）
saved_pdf: null
```

<a id="s048"></a>
## S048：Endex

**読んだもの：** OpenAI事例の財務データ照合、出典への追跡、FARベンチマーク、金融専門家の選好評価。

```yaml
source_id: S048
url_in_conversation: https://openai.com/index/endex/
resolved_url: https://openai.com/index/endex/
claimed_title_and_date: Endexの出典付き財務分析、日付未固定
verified_title: Endex builds the future of financial analysis, powered by OpenAI’s reasoning models
verified_authors_or_organization: OpenAI、Endex（Tarun Amasa、Pratham Soni）
publication_date: null
revision_date: null
version_or_commit: 本文見出しを採用（ページtitleはBuilding an autonomous financial analyst with o1 and o3-mini）。版表示なし。
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: 公開開示と社内資料の不整合を検出し、結論から根拠へ戻れる
    support_status: supported
    locator: Bringing analyst-level precision；Achieving higher accuracy；Developing financial agents with expert evaluations
    quotation_or_paraphrase: 財務注記の修正・不整合を特定箇所の引用とともに示し、表計算・文書・スライド等を作る。専門家による盲検選好でo1の回答が70%選ばれたとする。
    population_market_period: 財務開示、データルーム、社内資料。選好試験の標本数・期間は非開示。
    assumptions_and_limits: 当事者報告。70%は数値一致率ではない。出典リンクも算術・会計解釈の正しさを保証しない。
independent_validation_of_outcome: unknown
license_and_redistribution: 記事は公開。FARのデータ・評価コード、商用データ、顧客内部資料の再配布許諾は未確認。
corrections_to_conversation: 財務分析支援を支持。本文の日付表示なし、直接HTML取得403のため日付は固定できていない。
access: open（Web読取り）
saved_pdf: null
```

<a id="s049"></a>
## S049：Model ML のインタビュー

**読んだもの：** OpenAI Executive FunctionのCEOインタビュー全文。現状の説明と「今後12か月」の見通しを区別した。

```yaml
source_id: S049
url_in_conversation: https://openai.com/index/model-ml-chaz-englander/
resolved_url: https://openai.com/index/model-ml-chaz-englander/
claimed_title_and_date: Model MLの業務連鎖自動化、2025-07-23
verified_title: Model ML is helping financial firms rebuild with AI from the ground up
verified_authors_or_organization: OpenAI、Chaz Englander（Model ML CEO兼共同創業者）
publication_date: 2025-07-23
revision_date: null
version_or_commit: 公開インタビュー。GPT-4.1・o3・Agents SDK等の記載。
accessed_at: 2026-09-27
source_type: company_interview
verification_status: verified_partial
claims:
  - claim: 決算資料収集からスライド作成・SharePoint配置までを連鎖実行
    support_status: supported
    locator: What are you seeing change inside financial services firms?；Looking ahead 12 months
    quotation_or_paraphrase: CEOは決算要約の取得・整形・PowerPoint配置を人の介入なしで行う例を語る。後半の自律チーム・イベント駆動化には将来構想が含まれる。
    population_market_period: 顧客名・案件数・測定期間を示さないインタビュー事例。
    assumptions_and_limits: 当事者報告。本文は人手承認が常にあると述べていない。数値照合、承認点、アクセス制御の実装詳細や外部監査は未確認。
independent_validation_of_outcome: unknown
license_and_redistribution: 記事は公開。プラットフォーム・顧客データ・接続先商用データの利用・再配布権は別契約で未確認。
corrections_to_conversation: 連鎖自動化の設計例として扱い、全工程の検証済み本番導入や、人の承認が保証された仕組みとは記さない。
access: open
saved_pdf: null
```

<a id="s050"></a>
## S050：Pictet の Claude Code 利用

**読んだもの：** Anthropic事例本文の段階導入、研修、試作、運用・コンプライアンス支援の各段落。

```yaml
source_id: S050
url_in_conversation: https://claude.com/customers/pictet
resolved_url: https://claude.com/customers/pictet
claimed_title_and_date: Pictetで2026年初に展開、試作2週間から2時間
verified_title: Pictet turns weeks of work into hours with Claude Code
verified_authors_or_organization: Anthropic、Pictet（Steve Blanchet、Xavier Meyer）、Artefact
publication_date: null
revision_date: null
version_or_commit: 公開事例ページ。本文中の展開開始は2026年初、記事発行日・更新日は表示なし。
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: Claude Codeで試作・アラート・情報整理等の社内業務を短縮
    support_status: supported
    locator: With Claude, Pictet；A hackathon as the springboard；Work that wasn't feasible now takes hours
    quotation_or_paraphrase: 約700人へのアクセス、500人超の研修を報告。試作2週間→2時間の要約値、アクセス申請支援、集中アラート、AI関連週報等の例がある。
    population_market_period: 2026年初に1500人の技術部門から始めた段階導入。全員への配備完了を意味しない。
    assumptions_and_limits: 当事者報告。試作と本番リリースを区別する。50超の内規を比べる作業も2週間想定→数時間とされるが、別事例であり精度監査の結果はない。
independent_validation_of_outcome: unknown
license_and_redistribution: 記事は公開。EU・スイス内処理や専用gatewayは当該構成の説明であり、全利用者への保証ではない。銀行のコード・情報の公開許諾なし。
corrections_to_conversation: 2026年初は導入開始時点。時間短縮は試作・特定業務の報告で、運用収益や全社の平均効果へ一般化しない。
access: open
saved_pdf: null
```

<a id="s051"></a>
## S051：Figma Make の試作

**読んだもの：** AnthropicのFigma事例本文（Sites/Makeの区別、モデル評価、実装例、更新モデルの説明）。

```yaml
source_id: S051
url_in_conversation: https://claude.com/customers/figma
resolved_url: https://claude.com/customers/figma
claimed_title_and_date: Figma Makeによる対話型試作、日付未固定
verified_title: Figma transforms ideas into interactive software with Claude
verified_authors_or_organization: Anthropic、Figmaの製品担当者・経営者
publication_date: null
revision_date: null
version_or_commit: 公開事例ページ。Sonnet 4.5・Opus 4.6の記述が混在する更新型ページ、履歴なし。
accessed_at: 2026-09-27
source_type: company_case_study
verification_status: verified_partial
claims:
  - claim: 言語指示やFigmaのデザインから対話可能な試作を作る
    support_status: supported
    locator: Interactivity via natural language；New models accelerate the vision
    quotation_or_paraphrase: Makeは既存デザインや記述から試作・アプリを生成し、Sitesはウェブデザインへ対話動作を加える。担当者による短時間の試作例とモデル選択の評価がある。
    population_market_period: デザイン・ソフトウェア制作の事例。効果測定の期間・標本数なし。
    assumptions_and_limits: 当事者報告。金融計算、数式表示、アクセシビリティ、データ保護、本番品質の検証を含まない。
independent_validation_of_outcome: unknown（作成・実行・品質試験なし）
license_and_redistribution: 公開記事。Figma・Claudeの製品条件と、入力デザイン・アセット・生成物の権利は別確認。記事から再配布許諾は導けない。
corrections_to_conversation: 対話画面を早く試す参考事例として支持。金融機能の正しさの根拠にはしない。
access: open
saved_pdf: null
```

<a id="s052"></a>
## S052：Man Group AlphaGPT

**読んだもの：** 本文の7問すべて（役割分担、p-hacking、人の審査、対象資産、今後の展望）。発行日は公式記事検索表示と同記事のPDFリンク名で照合した。

```yaml
source_id: S052
url_in_conversation: https://www.man.com/insights/what-ai-can-do-for-alpha
resolved_url: https://www.man.com/insights/what-ai-can-do-for-alpha
claimed_title_and_date: What AI Can (and Can't Yet) Do for Alpha、2025-11-13
verified_title: What AI Can (and Can't Yet) Do for Alpha
verified_authors_or_organization: Ziang Fang、Jason Moore / Man Group
publication_date: 2025-11-13（公式記事検索の日付、PDFリンクの13-11-2025とも一致）
revision_date: null
version_or_commit: 公開記事、更新履歴なし
accessed_at: 2026-09-27
source_type: company_research_article
verification_status: verified_partial
claims:
  - claim: 仮説生成・Python実装・評価を分け、人が監督する研究業務
    support_status: supported
    locator: 本文§1、§3–4、§6–7
    quotation_or_paraphrase: Idea Person、Implementer、Evaluatorの分担とログ、投資委員会・技術チームの二系統審査を説明。多重検定と仮説・コードの不一致を課題に挙げ、現状は主に系統的株式研究とする。
    population_market_period: Man Group社内の開発中ワークフロー。対象期間、銘柄集合、費用控除後損益は公開されていない。
    assumptions_and_limits: 当事者報告。合格したシグナルがあるという記述は、実運用alphaや統計的再現性の検証ではない。p-hackingの具体的補正、PITデータ管理、探索予算も未開示。
independent_validation_of_outcome: unknown
license_and_redistribution: 公開記事。独自データベース・コード・研究結果の公開ライセンスは確認できない。
corrections_to_conversation: 主張は監督付き研究プロセスまで支持。完全無人の投資判断や、費用・漏洩を管理したlive成績が示されたとはしない。
access: open（HTML本文。PDFはWeb取得エラーで本文未確認）
saved_pdf: null
```

<a id="s053"></a>
## S053：Aiden VWAP

```yaml
source_id: S053
url_in_conversation: https://www.rbccm.com/en/expertise/global-markets/electronic-trading/aiden/vwap
resolved_url: https://www.rbccm.com/en/expertise/global-markets/electronic-trading/aiden/vwap
claimed_title_and_date: Aiden VWAP（提案書の同ID。日時の訂正は下記）
verified_title: Aiden VWAP
verified_authors_or_organization: RBC Capital Markets
publication_date: null
revision_date: null
version_or_commit: 取得時の製品ページ。補足記事2024-04-23。
accessed_at: '2026-09-27'
source_type: product
verification_status: verified_partial
claims:
- claim: VWAP執行に深層強化学習を使い、数量裁量と価格に応じた積極性を調整する
  support_status: supported
  locator: 製品ページ冒頭、Volume discretion、Price actions、Explainability
  quotation_or_paraphrase: RBCは200以上の入力、VWAPからのslippage低減を目的とする報酬、執行後の説明レポートを説明する。
  assumptions_and_limits: 提供会社の説明。VWAPの計測時間帯、手数料、注文選択、母集団・対照群を固定したTCAデータはこのページにない。
- claim: 対象市場と成績が独立に確認できる
  support_status: partial
  locator: RBC補足記事「A New Era of AI Trading in Europe」2024-04-23
  quotation_or_paraphrase: 記事は2020年の北米登場、2024年時点の英国・欧州展開を説明。Arrival Priceは別アルゴリズムでありVWAPと混ぜない。
  assumptions_and_limits: 2026年の全取引所・顧客資格・契約条件は未確定。原始注文/TCAと独立監査結果は確認できない。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 閲覧できるが再配布許諾は未確認。リンクと短い要約のみ。
corrections_to_conversation:
- 製品の存在と方式の説明は確認。slippage改善の独立実証や現行の利用可能市場の全一覧までは支持しない。
access: open
saved_pdf: null
additional_primary_urls:
- https://www.rbccm.com/en/insights/2024/04/rbcs-aiden-vwap-a-new-era-of-ai-trading-in-europe
```

<a id="s054"></a>
## S054：Adaptive Auto-X

```yaml
source_id: S054
url_in_conversation: https://www.marketaxess.com/lp/autox/landing
resolved_url: https://www.marketaxess.com/lp/autox/landing
claimed_title_and_date: Adaptive Auto-X（提案書の同ID。日時の訂正は下記）
verified_title: Adaptive Auto-X
verified_authors_or_organization: MarketAxess Holdings Inc.
publication_date: null
revision_date: null
version_or_commit: landingは本文抽出不可。公式2023-06-22発表を補足確認。
accessed_at: '2026-09-27'
source_type: product
verification_status: verified_partial
claims:
- claim: 予測分析と複数protocolの自動routingを組み合わせる
  support_status: supported
  locator: 公式IR「First Client Algo Trade Using Adaptive Auto-X」2023-06-22、第1–5段落
  quotation_or_paraphrase: RFQ・order book・matchingへ単一注文から接続するpilotを発表。独自データと予測AI、CP+ Peg、利用者による数量・表示・価格条件の変更を説明する。
  assumptions_and_limits: 当時のpilotについての当事者発表。2026年の全機能・全市場の検証ではない。
- claim: 現行機能・人へのfallback・独立成績を確認する
  support_status: partial
  locator: 元landing/ending/takeページの抽出結果、公式IR本文
  quotation_or_paraphrase: 元ページはfooterのみ取得できた。検索索引にはpause/stop/override等があるが、現行本文として再確認できず保留。
  assumptions_and_limits: 2023年発表の取引量はautomation全体でありAdaptive Auto-X固有の性能ではない。原始TCA・障害時運用は未検証。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 閲覧できるが再配布許諾は未確認。リンクと短い要約のみ。
corrections_to_conversation:
- 製品の実在は公式IRで確認した。動的製品ページの本文取得が不完全なので、現行仕様の全確認済みとはしない。
access: open
saved_pdf: null
additional_primary_urls:
- https://investor.marketaxess.com/news/news-details/2023/MarketAxess-Announces-First-Client-Algo-Trade-Using-Adaptive-Auto-X/default.aspx
```

<a id="s055"></a>
## S055：Fluence、Mosaicによるサン・ホームの系統用蓄電池の運用最適化を開始

```yaml
source_id: S055
url_in_conversation: https://prtimes.jp/main/html/rd/p/000000004.000156207.html
resolved_url: https://prtimes.jp/main/html/rd/p/000000004.000156207.html
claimed_title_and_date: Fluence、Mosaicによるサン・ホームの系統用蓄電池の運用最適化を開始（提案書の同ID。日時の訂正は下記）
verified_title: Fluence、Mosaicによるサン・ホームの系統用蓄電池の運用最適化を開始
verified_authors_or_organization: Fluence Energy, Inc.（発表主体。PR TIMESは配信）
publication_date: '2026-03-11'
revision_date: null
version_or_commit: 発表時刻10:00 JST。版表示なし。
accessed_at: '2026-09-27'
source_type: press_release
verification_status: verified_partial
claims:
- claim: 上倉永蓄電所で2026年2月に運用開始
  support_status: supported
  locator: 冒頭第1–2段落
  quotation_or_paraphrase: サン・ホーム、宮崎県宮崎市の上倉永蓄電所、2025年12月系統接続、2026年2月本格運用と記載。
  assumptions_and_limits: 発表主体の報告。設備容量、取引データ、接続契約・市場資格の検証はしていない。
- claim: AI予測・複数市場入札・充放電最適化による効果
  support_status: partial
  locator: 「オプティマイザーに運用を任せるという選択」
  quotation_or_paraphrase: AI価格予測、複数市場/商品の同時最適化、24時間計画とSOC管理、aggregator連携を説明する。
  assumptions_and_limits: 収益の対照実験・費用控除・劣化条件・市場別成績は公表されていない。導入確認と利益改善の実証を分ける。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 閲覧できるが再配布許諾は未確認。リンクと短い要約のみ。
corrections_to_conversation:
- 地名・運用月・公表日は提案書と一致。日本市場一般の参加要件や利益保証の根拠には使わない。
access: open
saved_pdf: null
additional_primary_urls: []
```

<a id="s056"></a>
## S056：Introducing ChatGPT for Financial Services

```yaml
source_id: S056
url_in_conversation: https://openai.com/index/introducing-chatgpt-financial-services/
resolved_url: https://openai.com/index/introducing-chatgpt-financial-services/
claimed_title_and_date: Introducing ChatGPT for Financial Services（提案書の同ID。日時の訂正は下記）
verified_title: Introducing ChatGPT for Financial Services
verified_authors_or_organization: OpenAI
publication_date: '2026-09-10'
revision_date: null
version_or_commit: 発表本文を確認。関連Financial Services Termsは2026-09-16更新。
accessed_at: '2026-09-27'
source_type: product_announcement
verification_status: verified_partial
claims:
- claim: 出典付き金融分析、対話図、Office成果物を提供し、投資銀行・株式調査から始める
  support_status: supported
  locator: Frontier research、Data、Put GPT-6 Astra to work、Turn the analysis into work
  quotation_or_paraphrase: ChatGPT Workの金融向け製品として、組込みデータ・既存契約接続・根拠への引用・文書/表計算/スライド・対話図を説明。初期の重点はinvestment banking/equity
    research。
  assumptions_and_limits: 発表された機能。個別口座のアクセスや全データ契約を確認したものではない。
- claim: 提供範囲とデータ利用条件
  support_status: supported
  locator: Availability、公式Financial Services Terms §§1–3
  quotation_or_paraphrase: 対象はeligible financial institutionsで営業窓口へ問い合わせる形式。既存契約の権利連携には開発中の説明もある。Partner Dataには保存・学習・派生物・再配布等の個別制限が適用される。
  assumptions_and_limits: 価格や個人プランへの付帯を推測しない。export機能だけでデータ再配布権は得られず、時刻・遅延もデータごとに異なる。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 公式発表はリンクと要約のみ。Partner Dataの権利は個別条件に従い、出力の所有と同一視しない。
corrections_to_conversation:
- 2026-09-10の実在と日付は確認。利用者の現在の契約で全機能が使えるとは判断していない。金融計算の独立正確性は別検証。
access: open
saved_pdf: null
additional_primary_urls:
- https://openai.com/policies/financial-services-terms/
```

<a id="s057"></a>
## S057：Claude for Financial Advisors

```yaml
source_id: S057
url_in_conversation: https://claude.com/blog/claude-for-financial-advisors
resolved_url: https://claude.com/blog/claude-for-financial-advisors
claimed_title_and_date: Claude for Financial Advisors（提案書の同ID。日時の訂正は下記）
verified_title: Claude for Financial Advisors
verified_authors_or_organization: Anthropic
publication_date: '2026-09-14'
revision_date: null
version_or_commit: 製品発表本文。参照コードはS058。
accessed_at: '2026-09-27'
source_type: product_announcement
verification_status: verified_partial
claims:
- claim: 面談準備・portfolio点検等を接続先データとskillsで支援する
  support_status: supported
  locator: 冒頭、Connectors to the tools advisors already use、Getting started
  quotation_or_paraphrase: custodian、portfolio、CRM、planning等の接続を列挙し、meeting prep、portfolio analysis、compliance checksを説明。Cowork
    pluginの提供と、記録用audit logのあるEnterprise推奨を記載。
  assumptions_and_limits: データ提供者との契約・権限が前提。口座での接続実行や監査log内容の検証はしていない。
- claim: 製品発表が参照コードの継続保守を保証する
  support_status: not_supported
  locator: S058 READMEのMaintenance status
  quotation_or_paraphrase: 公開参照repoは継続保守・監視をしないと明記する。発表とrepoのサポート条件は別。
  assumptions_and_limits: 顧客業務の成果は当事者説明であり、投資助言や計算精度の独立評価ではない。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 閲覧できるが再配布許諾は未確認。リンクと短い要約のみ。
corrections_to_conversation:
- 日付は一致。業務手順の参考であり、顧客データの取得権、製品性能の承認、repo保守保証には読み替えない。
access: open
saved_pdf: null
additional_primary_urls:
- https://github.com/anthropics/claude-for-financial-advisors
```

<a id="s058"></a>
## S058：Claude for Financial Advisors — reference plugin

```yaml
source_id: S058
url_in_conversation: https://github.com/anthropics/claude-for-financial-advisors
resolved_url: https://github.com/anthropics/claude-for-financial-advisors
claimed_title_and_date: Claude for Financial Advisors — reference plugin（提案書の同ID。日時の訂正は下記）
verified_title: Claude for Financial Advisors — reference plugin
verified_authors_or_organization: Anthropic
publication_date: null
revision_date: null
version_or_commit: main HEAD 96fbcb4797758186786c50dd1a09ce2feac6e18c（GitHub API取得、committer date 2026-09-16T23:30:10Z）
accessed_at: '2026-09-27'
source_type: source_repository
verification_status: verified_supports_claim
claims:
- claim: Markdown/JSONによるskillsとthird-party connectorsの参照実装
  support_status: supported
  locator: README冒頭、Skills、Installation
  quotation_or_paraphrase: plugin自体は顧客データを保持せず、接続先から必要情報を読むと説明。外部への書込みはadvisorの明示承認を要し、判断はadvisorが行う。
  assumptions_and_limits: READMEの設計説明。全skillの権限・実行ログ・顧客環境を監査したものではない。
- claim: 継続保守・監視を保証しない
  support_status: supported
  locator: README Maintenance status、Contributing、LICENSE
  quotation_or_paraphrase: 参照実装、非継続保守・非監視、contribution受付なし、issue/PRは応答されない可能性、AS ISと明記。LICENSE本文はApache-2.0。
  assumptions_and_limits: forkする場合の保守責任や接続先データの権利をコードlicenseで代用しない。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: Apache-2.0（LICENSE本文確認）。接続先データには別条件。
corrections_to_conversation:
- 会話の保守状態の説明は支持された。日付・commitを記録したが、製品をインストールしたわけではない。
access: open
saved_pdf: null
additional_primary_urls:
- https://github.com/anthropics/claude-for-financial-advisors/blob/96fbcb4797758186786c50dd1a09ce2feac6e18c/README.md
- https://github.com/anthropics/claude-for-financial-advisors/blob/main/LICENSE
```

<a id="s059"></a>
## S059：Introducing Workspace MCP: agentic financial workflows, governed by design

```yaml
source_id: S059
url_in_conversation: https://openbb.co/blog/introducing-workspace-mcp
resolved_url: https://openbb.co/blog/introducing-workspace-mcp
claimed_title_and_date: 'Introducing Workspace MCP: agentic financial workflows, governed by design（提案書の同ID。日時の訂正は下記）'
verified_title: 'Introducing Workspace MCP: agentic financial workflows, governed by design'
verified_authors_or_organization: Didier Lopes / OpenBB
publication_date: '2026-05-26'
revision_date: null
version_or_commit: 現行blogと公式MCP Quickstart。API版は未固定。
accessed_at: '2026-09-27'
source_type: product_announcement
verification_status: verified_partial
claims:
- claim: agentがデータを読み、再利用可能なwidget/dashboard/appを作る
  support_status: supported
  locator: What Workspace MCP actually does、Governed by design、公式Quickstart
  quotation_or_paraphrase: 利用者のentitlement、credentials vault、生成物のaccess control/lineageを使う構成を説明。現行Quickstartは開いたWorkspace
    browser bridgeとHTTP MCPを前提とする。
  assumptions_and_limits: 契約/API実行・権限の負の試験は未実施。無人の常駐サーバーだけで動く仕組みとみなさない。
- claim: governanceが成果物の数値レビューを不要にする
  support_status: not_supported
  locator: blog Governed by design、Quickstart Validate the connection
  quotation_or_paraphrase: blogはレビュー工程を除くと宣伝するが、接続成功例はdashboard状態取得であり金融計算の正しさを試験していない。
  assumptions_and_limits: 権限管理・lineageと、計算・モデル・意思決定の検証は別。料金・現行配布コードのlicense・deployment契約は別途確認。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: 閲覧できるが再配布許諾は未確認。リンクと短い要約のみ。
corrections_to_conversation:
- 2026-05-26は一致。デモと運用上の権限仕様を分け、johnhullへ接続や依存を追加しない。
access: open
saved_pdf: null
additional_primary_urls:
- https://docs.openbb.co/agents/workspace-mcp-quickstart
- https://docs.openbb.co/agents/workspace-mcp
```

<a id="s060"></a>
## S060：LLM and agent-driven analytics

```yaml
source_id: S060
url_in_conversation: https://perspective-dev.github.io/guide/use_cases/agent.html
resolved_url: https://perspective-dev.github.io/guide/use_cases/agent.html
claimed_title_and_date: LLM and agent-driven analytics（提案書の同ID。日時の訂正は下記）
verified_title: LLM and agent-driven analytics
verified_authors_or_organization: Perspective project
publication_date: null
revision_date: null
version_or_commit: 版未固定のguide。公式GitHub latest releaseはv5.5.1、2026-09-18。guideとtagの同一性は未検証。
accessed_at: '2026-09-27'
source_type: official_documentation
verification_status: verified_partial
claims:
- claim: LLMが表示設定を作り、集計はデータengineが行う
  support_status: supported
  locator: 冒頭、Why an agent fits Perspective、Any model
  quotation_or_paraphrase: viewer.agentConfigでopt-inし、schema・設定からgroup/filter/expressions/chart等を作る。数値はengineが計算し、普通のviewer設定として確認・保存できる。
  assumptions_and_limits: 公式docsではagent toolはrowsを読まないと説明するが、schemaや質問・設定も機密になり得る。通信・権限の実地検証は未実施。
- claim: 現行APIと互換性・安全性の全検証
  support_status: partial
  locator: 同guide、公式homepage/footer、release metadata
  quotation_or_paraphrase: OpenAI chat-completions形式、複数provider・local serverへの接続を説明。コードlicenseはApache-2.0。
  assumptions_and_limits: 未固定guideの例をv5.5.1で実行したわけではない。実装時にtagとschemaを固定し、生成設定を検証する。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: Apache-2.0（公式homepageとrepo表記）。使用データ・モデルprovider条件は別。
corrections_to_conversation:
- 設計上の責務分離は確認。LLMが出した設定の意味の正しさや、任意のデータが外へ出ないことまでは実証していない。
access: open
saved_pdf: null
additional_primary_urls:
- https://perspective-dev.github.io/
- https://github.com/perspective-dev/perspective/releases/tag/v5.5.1
```

<a id="s061"></a>
## S061：Case study: a multi-billion row tick history in a browser tab with DuckLake and DuckDB-WASM

```yaml
source_id: S061
url_in_conversation: https://perspective-dev.github.io/guide/use_cases/ducklake.html
resolved_url: https://perspective-dev.github.io/guide/use_cases/ducklake.html
claimed_title_and_date: 'Case study: a multi-billion row tick history in a browser tab with DuckLake and DuckDB-WASM（提案書の同ID。日時の訂正は下記）'
verified_title: 'Case study: a multi-billion row tick history in a browser tab with DuckLake and DuckDB-WASM'
verified_authors_or_organization: Perspective project
publication_date: null
revision_date: null
version_or_commit: 版未固定guide。測定はDuckDB-WASM 1.4.3と記載。
accessed_at: '2026-09-27'
source_type: official_documentation
verification_status: verified_partial
claims:
- claim: snapshot比較をUIに出せる
  support_status: supported
  locator: §3 Time travel as a user feature、Publishing your own
  quotation_or_paraphrase: snapshots()とAT(VERSION)、SNAPSHOT_VERSION/TIMEを示し、訂正前後を同じ設定の2panelで比べる構成を説明。catalog writerとbrowser
    readerの版互換も条件。
  assumptions_and_limits: 保存snapshotの存在は、公表時刻・取得遅延・当時の利用可能性の正しさを保証しない（本調査の判断）。PIT設計では別列・検査が必要。
- claim: 巨大tick履歴を対話的に扱う性能
  support_status: partial
  locator: §2の性能表、How big can a slice be、Guardrails
  quotation_or_paraphrase: remote lakeから対象sliceをmaterializeし、局所集計する。測定は1機・1network・1回で丸めた値、巨大local tableの別試験はsynthetic。
  assumptions_and_limits: 30億行全体を毎操作即時集計する主張ではない。filter必須・byte予算・memory制限・Range/CORSが必要。独立再現は未実施。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: PerspectiveコードはApache-2.0。DuckDB/DuckLake・tickデータは個別の条件を実装時に確認。
corrections_to_conversation:
- versioned dataは訂正比較の参考。point-in-time整合や実市場データの再配布権を自動的に得る機能ではない。
access: open
saved_pdf: null
additional_primary_urls:
- https://perspective-dev.github.io/
```

<a id="s062"></a>
## S062：Manim Community

```yaml
source_id: S062
url_in_conversation: https://www.manim.community/
resolved_url: https://www.manim.community/
claimed_title_and_date: Manim Community（提案書の同ID。日時の訂正は下記）
verified_title: Manim Community
verified_authors_or_organization: The Manim Community Dev Team
publication_date: null
revision_date: null
version_or_commit: 公式stable docs v0.21.0（取得日）。導入・renderは未実施。
accessed_at: '2026-09-27'
source_type: official_documentation
verification_status: verified_partial
claims:
- claim: Pythonで数理アニメーションを作る
  support_status: supported
  locator: homepageコード例、公式Installation、Rendering Text and Formulas
  quotation_or_paraphrase: Sceneから図形・数式のアニメーションを作るCommunity版。Grant Sandersonの別系列と区別する。公式はMIT licenseと明記。
  assumptions_and_limits: 動画の描画は価格・Greekの検証にならない。johnhullの検証済み数値を別入力として与える設計が必要。
- claim: 版・render環境・フォント・依存
  support_status: partial
  locator: Installing Manim locally Steps1–3、Rendering Text and Formulas
  quotation_or_paraphrase: Python環境を管理し、数式には任意のLaTeX追加、LinuxではC compiler・Python/Pango/Cairo headers・pkg-configを説明。plain
    TextとTeXの経路を区別する。
  assumptions_and_limits: このWSLでの依存充足、日本語フォント、TeX template、video出力は未検証。制作時に版・renderer・fontを固定する。新規依存は今回追加しない。
independent_validation_of_outcome: unknown。資料の読取りのみ。製品実行・性能再現・権限の実地検証はしていない。
license_and_redistribution: MIT（公式homepage）。フォント・音声・引用図の利用条件は別。
corrections_to_conversation:
- 実在とMIT、取得したdocsのv0.21.0を確認。環境へ導入済み・動画を再現済みとは扱わない。
access: open
saved_pdf: null
additional_primary_urls:
- https://docs.manim.community/en/stable/installation/uv.html
- https://docs.manim.community/en/stable/guides/using_text.html
```

<a id="l01"></a>
## L01：OpenGamma Strata の market quote sensitivity

```yaml
source_id: L01
url_in_conversation: null
resolved_url: https://strata.opengamma.io/apidocs/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculator.html
claimed_title_and_date: Strata の Jacobian／market quote sensitivity（版未指定）
verified_title: MarketQuoteSensitivityCalculator / JacobianCalibrationMatrix
verified_authors_or_organization: OpenGamma
publication_date: null
revision_date: null
version_or_commit: 公式API文書は版表示なし。公式mainのpomは2.12.75-SNAPSHOT。commit未固定。
accessed_at: 2026-09-27
source_type: official_api_documentation
verification_status: verified_supports_claim
claims:
  - claim: パラメータ感応度から市場クオート感応度へ変換するAPIがある
    support_status: verified_supports_claim
    locator: MarketQuoteSensitivityCalculator.sensitivity(CurrencyParameterSensitivities, RatesProvider)
    quotation_or_paraphrase: 較正時のJacobian情報を保持したproviderが必要。LegalEntityDiscountingProviderとCreditRatesProviderのoverloadもある。
  - claim: JacobianCalibrationMatrixの向き
    support_status: verified_supports_claim
    locator: JacobianCalibrationMatrix.of / getJacobianMatrix の説明
    quotation_or_paraphrase: 格納するのは市場クオートに対する曲線パラメータの微分であり、残差のパラメータ微分そのものではない。曲線順序も保存する。
independent_validation_of_outcome: unknown（Javaの実行はしていない）
license_and_redistribution: 公式repo LICENSE.txtとpomにApache-2.0。API文書の利用とコード移植を区別し、今回は参照のみ。
corrections_to_conversation: API名と行列の向きを同定。実行比較の前にtagまたはcommitを固定する。
access: open
saved_pdf: null
```

確認先：[行列の定義](https://strata.opengamma.io/apidocs/com/opengamma/strata/market/curve/JacobianCalibrationMatrix.html)、
[公式 pom](https://github.com/OpenGamma/Strata/blob/main/pom.xml)、[LICENSE](https://github.com/OpenGamma/Strata/blob/main/LICENSE.txt)、
[公式テスト](https://github.com/OpenGamma/Strata/blob/main/modules/pricer/src/test/java/com/opengamma/strata/pricer/sensitivity/MarketQuoteSensitivityCalculatorTest.java)。
最後のテストは行列の掛け方の例で、較正込みの rates テストとして `CalibrationDiscountingSimpleEur3Test` を参照している。
RB-F07 には Java 依存を加えず、規約・単位・行列の向きの照合に使う。

<a id="l02"></a>
## L02：AMM手数料からのインプライド・ボラティリティ

**読んだもの：** 著者名・日付・研究内容で検索し、arXiv書誌（版履歴・ライセンス）とHTML v1の§2、§4–7（前提、Theorem 4.2・5.1、Corollary 5.3、実証・結論）を照合。付録の証明全行は未検証。

```yaml
source_id: L02
url_in_conversation: null
resolved_url: https://arxiv.org/abs/2509.23222
claimed_title_and_date: Bichuch–FeinsteinのAMM fee streamとvolatility/correlation価格、2025-09-27
verified_title: "The Price of Liquidity: Implied Volatility of Automated Market Maker Fees"
verified_authors_or_organization: Maxim Bichuch、Zachary Feinstein
publication_date: 2025-09-27
revision_date: null
version_or_commit: arXiv:2509.23222v1（2025-09-27 10:01:53 UTC、版履歴はv1のみ）
accessed_at: 2026-09-27
source_type: preprint
verification_status: verified_supports_claim
claims:
  - claim: AMMの手数料スワップを用いてボラティリティと相関を価格から導く研究
    support_status: supported
    locator: §4 Assumption 4.1・Theorem 4.2；§5 Theorem 5.1・Corollary 5.3；§7
    quotation_or_paraphrase: 相関付きrisk-neutral GBMと連続的な手数料の下で、LPが退出時刻に無差別となる手数料をLVRに対応付ける。前払い固定額と将来手数料の交換を提案する。
    population_market_period: 理論モデル。片側をmoney market accountとするボラ推定、両側のボラを既知とした相関推定。
    assumptions_and_limits: 一つの手数料価格から二つのボラと相関を同時同定するものではない。smart contract実装と市場のスワップ価格による検証は将来課題。
  - claim: 実証の対象と、実現手数料からの尺度の意味
    support_status: supported
    locator: §2；§6.1–6.3、Figures 2–4；§7
    quotation_or_paraphrase: WETH/USDCのUniswap v3（5bp、2023–24年、全価格帯LP）と、SPY/GLDの2023年気配からの模擬AMMを検討。実現手数料の尺度は実現ボラと関連すると報告する。
    population_market_period: 30日重複窓。SPY/GLDは1秒気配・30bp・裁定取引だけを模擬、比較計算はr=0。
    assumptions_and_limits: 実現手数料は後ろ向きで、市場が付ける将来のIVではない。取引所・データの利用権と全コードは未確認。
independent_validation_of_outcome: unknown（数値再現・実証追試なし）
license_and_redistribution: arXiv non-exclusive distribution license 1.0。一般の再配布許諾ではない。今回は公開HTMLを読み、PDFは保存していない。
corrections_to_conversation:
  - 正式題名・URL・v1を同定した。S030のRisk–Tung–WangによるAMMオプション複製とは別研究。
  - 提案商品の存在やforward-looking IVの実市場での有効性まで実証済みとはしない。
access: open
saved_pdf: null
additional_primary_urls:
  - https://arxiv.org/html/2509.23222v1
  - https://arxiv.org/licenses/nonexclusive-distrib/1.0/license.html
```

<a id="l03"></a>
## L03：Remotion

**読んだもの：** 公式fundamentals、renderer、ensureBrowser、導入説明、GitHub release、固定commitのLICENSE.md。導入・動画生成はしていない。

```yaml
source_id: L03
url_in_conversation: null
resolved_url: https://www.remotion.dev/docs/the-fundamentals
claimed_title_and_date: Reactによるprogrammatic video、版・URL未確定
verified_title: Remotion — The fundamentals / renderer / Remotion License
verified_authors_or_organization: Remotion AG / remotion-dev
publication_date: null
revision_date: 2026-09-27（取得したdocsの更新表示。初公開日とは区別）
version_or_commit: 最新releaseはv4.0.529、2026-09-25T08:00:18Z（GitHub API確認）。LICENSEはmain commit f1cd5fd98c51cb8b4aefd94773703d1ee1dba41bで確認。
accessed_at: 2026-09-27
source_type: official_documentation_and_repository
verification_status: verified_supports_claim
claims:
  - claim: Reactのフレーム依存描画から動画を生成できる
    support_status: supported
    locator: The fundamentalsのReact components・Compositions；@remotion/renderer；ensureBrowser()；導入ページSystem requirements
    quotation_or_paraphrase: React compositionを登録しrenderMedia等で出力する。公式要件はNode 16以上またはBun 1.0.3以上、Linuxはlibc 2.35以上と追加パッケージ。サーバー描画用のChrome確保APIを提供する。
    population_market_period: ソフトウェア機能、v4系。金融モデルの検証結果ではない。
    assumptions_and_limits: WSL環境との適合、依存、ブラウザ、フォント、音声、決定的なレンダーは未試験。Alpine Linux・nixOSは公式に非対応。
  - claim: 商用・組織利用条件
    support_status: supported
    locator: 固定commitのLICENSE.md、Free License / Company License
    quotation_or_paraphrase: 個人、従業員3人までの営利組織、非営利組織、非商用の評価が無料の対象。対象外はCompany Licenseが必要。派生版を販売等する目的のコード複製・改変は禁止される。
    population_market_period: 確認したv4系の独自ライセンス。開発者席数だけで無料判定しない。
    assumptions_and_limits: mainにはv5で変更予定との注記がある。v5条件をv4へ混ぜず、採用時点の版・組織・用途で再確認する。
independent_validation_of_outcome: unknown（インストール・レンダー・日本語表示の試験なし）
license_and_redistribution: Remotion独自のFree/Company License。MIT等の無条件なオープンソース許諾とは記さない。生成物中の第三者素材の権利は別。
corrections_to_conversation: 公式URL・v4.0.529・組織利用条件を同定。今回は候補調査であり、依存追加や動作確認はしていない。
access: open
saved_pdf: null
additional_primary_urls:
  - https://www.remotion.dev/docs/renderer
  - https://www.remotion.dev/docs/renderer/ensure-browser
  - https://www.remotion.dev/docs/
  - https://github.com/remotion-dev/remotion/releases/tag/v4.0.529
  - https://api.github.com/repos/remotion-dev/remotion/releases/latest
  - https://raw.githubusercontent.com/remotion-dev/remotion/f1cd5fd98c51cb8b4aefd94773703d1ee1dba41b/LICENSE.md
```

---

## 保存した PDF

保存先：S033–S042の9件は `/home/kazumasa/projects/tmp/johnhull-prep/papers/`、S043は下記の絶対パス（すべてgit管理外）。2026-09-27に全10件のsize/hashを実ファイルから照合した。

| ファイル | 版 | サイズ（bytes） | SHA-256 |
|---|---|---:|---|
| S033_robust-yield-curve-mortgage-nn.pdf | arXiv 2510.21347v1 | 4,870,422 | 8eaac0d5ae9c1ec891571648b353bea0c8372b74849594d33c0842df2f515f47 |
| S034_deeponet-bond-option-aims2026.pdf | AIMS Mathematics 11(3) 出版社 PDF | 22,325,854 | 5c07a8d12f1eb28a70e89a4aefb1b1165e3f3f06caee639026c8b3adb78d43b8 |
| S035_deep-bsde-bermudan-delta-gamma.pdf | arXiv 2502.11706v1 | 1,779,000 | 1c98f0e863309484a9848be76b1a134ceccb7854252f9c429070478520bd4585 |
| S036_gueant-manziuk-drl-bond-mm.pdf | arXiv 1910.13205v1 | 9,038,803 | 7048d64e66beca2418f66d40f5f38b49d7ec0b54bdf25a35ade9d58cef44bd26 |
| S037_robust-mm-regime-switching.pdf | arXiv 2609.11614v1 | 4,050,829 | d9d3b265968b35c44d9f68d204abe8fcf08db043ee70039601b0510f9b309ce5 |
| S038_deep-hedging-iv-surface-feedback-v2.pdf | arXiv 2407.21138v2 | 1,153,566 | 9d24484751764ff763d3d3913f058de02e1f784233d9fbd8f5e05588c486e149 |
| S039_diffusion-vol-surface-hedging-v3.pdf | arXiv 2609.13402v3 | 3,577,971 | ae069983296f5b6b433111a83f38fca9554c451691b296de6564714d9de9d2e7 |
| S041_chronos-2.pdf | arXiv 2510.15821v1 | 1,521,734 | 73a0da2cbfafa5eda8e28041249ff889273a386acaffd35be13a688af1364edd |
| S042_ai4contracts-cdmizer.pdf | arXiv 2506.01063v1 | 723,073 | 1fca3f4d3caf98a8c22d83d74796409d448847abaf6cf8c3fe32c62730f46fd0 |
| /home/kazumasa/projects/tmp/johnhull-prep/scratch/codex_ch26_37/S043_work1291.pdf | BIS Working Papers No 1291、September 2025 | 2,197,745 | 74a0a7e568d751ab7d3a5bed5da7924a420373336a2dfac905063345b10ad01d |

## 残った取得不能・未確認の範囲

34件すべてに調査経路と判定を記録した。下記は保留条件であり、未調査のレコードではない。

| 対象 | 取得・照合できなかった範囲 | 今回の判断と再開条件 |
|---|---|---|
| S032 | CP+の実データ・利用契約・価格精度 | 公式提供発表のみ支持。取得可能なデータと時点・銘柄を固定して別評価 |
| S033–S040 | 非公開・商用生データ、独立再現。S036の有料雑誌本文 | 公開稿と出版書誌まで。データ取得権と再現環境が必要 |
| S041 | 重みファイル・固定commit・金融市場での性能 | コード/model cardのApache-2.0確認済み。重み取得・学習データの独立監査は未実施 |
| S042 | 重要条件の完全一致、CF・価格の意味検証、CDM版・公開コード | 合成30件の構文・網羅率評価まで。完全一致は論文の評価にない |
| S043 | 正確なGemini model ID・情報時点保証、学習期間の厳密な端点、再現 | 新URLからPDF取得。公式カードとの不整合によりLLM未見性は支持しない。RNNは別評価 |
| S044–S052 | 成果のraw data・独立対照試験・利用契約。S047/S048/S050/S051の発行日 | 当事者説明まで。S046–S048の直接HTMLは403だがWeb読取りで本文確認。日付・更新履歴は推測で埋めない |
| S052 | 同記事PDF本文 | Web取得エラー。HTML本文は取得済み。日付は公式検索とPDFリンク名で照合 |
| S053 | 行動空間の詳細、訓練・TCA標本、独立評価 | 製品説明・欧州展開記事まで。執行ログ等が必要 |
| S054 | 動的な現行本文・実行仕様 | 取得はfooter中心。公式2023年pilot発表で補足し、現行全仕様とは同一視しない |
| S055–S057 | 蓄電池成果の対照比較、金融製品の独立性能、個別契約 | 発表と適用条件を確認。収益性・正確性の保証に転用しない |
| S058–S062 | コード・API・大規模データ・動画の実行再現 | 公開README/docs/licenseまで。S058はcommit、S060はreleaseを記録。保守・許諾・性能は別確認 |
| L01 | API docsのrelease対応とJava実行 | APIの意味を確認済み。比較実装前にtag/commit固定 |
| L02 | fee swapの実市場データ、実装・実証の追試 | 書誌・本文同定済み。商品実装が将来課題という条件を保持 |
| L03 | WSLの依存・Chrome・日本語・音声・レンダー動作 | 公式版・機能・許諾条件を同定済み。今回は導入なし |

企業の時間短縮・精度・価格改善は原則として当事者報告である。同じ発表の転載や提供者による事例紹介を独立した再現と数えない。未公開データ、動的本文、版履歴のない日付などは、追加の具体的な一次資料がない限り推定で埋めない。
