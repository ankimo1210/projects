# johnhull Coverage Roadmap — Hull 11e + Beyond Hull

Spec: `docs/superpowers/specs/2026-06-07-johnhull-full-coverage-design.md`

| # | Volume | Chapters | Status |
|---|--------|----------|--------|
| — | `notebooks/bsm_chapter15.ipynb` | 15 | done |
| — | `interest_rate_models/ir_models.ipynb` | 31, 32, 33 | done |
| 1 | `volumes/01_foundations` | 13, 14 | done |
| 2 | `volumes/02_options_basics` | 10, 11, 12, 17, 18 | done |
| 3 | `volumes/03_greeks` | 19 | done |
| 4 | `volumes/04_futures_forwards_rates` | 2, 3, 4, 5, 6 | done |
| 5 | `volumes/05_vol_smile_estimation` | 20, 23 | done |
| 6 | `volumes/06_numerical_methods` | 21, 27 | done |
| 7 | `volumes/07_swaps` | 7, 34 | done |
| 8 | `volumes/08_risk_var` | 22 | done |
| 9 | `volumes/09_credit_xva` | 9, 24, 25 | done（数値例のある節は vol 28 と hullkit のテストで実装・固定。残りは `docs/SECTION_AUDIT_2026-09-14.md` §4.5） |
| 10 | `volumes/10_exotics_martingales` | 26, 28 | done |
| 11 | `volumes/11_ir_derivatives_market` | 29, 30 | done |
| 12 | `volumes/12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | done |

Shared module: `johnhull/hullkit` (uv workspace member) — 53 modules as of 2026-09-15; the catalogue is `MODEL_INDEX.md` (the original 14 were bsm, trees, mc, nbplot, payoffs, hedging, rates, volatility, fd, swaps, risk, credit, exotics, ir_options).

**Status (2026-06-08): all 14 rows done → every Hull 11e chapter has a volume.** Section-level
coverage is narrower: `docs/SECTION_AUDIT_2026-09-14.md` §1 lists the sections that still have
no computation as of the audit; §12 of that document is the per-ID current status, and the
section-audit milestone below summarizes the fixes since.

## 可視化 & 深掘り(A1–A4) — 完了 (2026-06-14)

全5巻(13–17)が build スクリプト生成・nbconvert 実行済み・book/portal 登録済み。
hullkit に 10 新モジュール(sde/heston/fourier/sabr/mc_advanced/fd_advanced/aad/xva/copula/plotly_viz)、
当時のポータル **38 図/7 テーマ**(`make hull-report`)、Jupyter Book 20 ページ(`make hull-book`)。全テスト緑。
追加可視化(深掘り外の既存 hullkit 関数): ガンマ曲面・ストップロス vs デルタ・二項木格子・GARCH(クラスタリング/期間構造)・Merton 構造模型・分散投資・イールドカーブ・債券コンベクシティ・スワップ par・バリア・アジアン。

Hull の射程の先(同じクオンツ系で Hull が浅い領域)を深掘りしつつ、既存 + 新規の全コンテンツを
インタラクティブ可視化する取り組み。すべて johnhull 内で完結。

- **可視化基盤**: `hullkit.plotly_viz`(既存の bsm/trees/hedging/risk/credit をラップする `plotly_*` ビルダー)。
- **HTML/ポータル**: `johnhull/report`(jinja2 + plotly, オフライン自己完結) → `make hull-report`。
  `johnhull/book`(全ボリュームを束ねる Jupyter Book) → `make hull-book`。

| # | Volume | テーマ(Hull の先) | Status |
|---|--------|------|--------|
| P1 | 既存全14ノートの可視化 | `plotly_viz` 6 図 + ポータル疎通(offline test 緑) | done |
| 13 | `volumes/13_stochastic_calculus` | A1 確率解析(伊藤・Girsanov・Feynman-Kac) | **done**(30セル・実行済・book登録) |
| 14 | `volumes/14_stoch_vol_fourier` | A2 確率ボラ & Fourier(Heston/SABR/COS) | **done**(35セル・実行済・book登録) |
| 15 | `volumes/15_advanced_numerics` | A3 高度な数値(分散減少/QMC/LSM/CN/AAD) | **done**(22セル・実行済・book登録) |
| 16 | `volumes/16_xva_credit` | A4 XVA/信用(EE/PFE/CVA/コピュラ) | **done**(22セル・実行済・book登録) |
| 17 | `volumes/17_capstone` | Heston×Fourier → Greeks → CVA 一気通貫 | **done**(18セル・実行済・book登録) |

## Hull の先 A5–A8 — G8 release 完了 (2026-07-18)

Design: `docs/superpowers/specs/2026-07-18-johnhull-beyond-hull-a5-design.md`

G0 decision: financial teachers and hard validation belong to torch-free `hullkit`;
the Phase 2 PyTorch engine and checkpoints belong to `deep_hedge_price`; teaching,
book, and portal integration belong to `johnhull`. Projects exchange only versioned
JSON+NPZ reference artifacts. Phase 1 and Phase 2 config/checkpoint namespaces are
separate. No production dependency was added for G0/G1 core implementation.

| Gate | # | Volume / contract | Status |
|---|---:|---|---|
| G0 | — | owner / dependency / artifact contract | done |
| G1 | 18 | `volumes/18_ml_surrogates` | done |
| G2 | 19 | `volumes/19_inverse_surfaces` | done |
| G3 | 20 | `volumes/20_surface_dynamics` | done |
| G4 | 21 | `volumes/21_spx_vix` | done |
| G4 | 22 | `volumes/22_zero_dte` | done |
| G5 | 23 | `volumes/23_rfr_post_libor` | done |
| G6 | 24 | `volumes/24_crypto_market_structure` | done |
| G7 | 25 | `volumes/25_climate_energy` | done |
| G8 | — | full integration and tracked release | **done** |

表の `done` は巻別実装、integration gate、G8 tracked release の完了を表す。
各巻に validation report、fingerprinted JSON/NPZ、artifact-only notebook、book
symlinkがあり、各巻の `integration_and_reproducibility` gate は PASS。これは
**model performance の承認ではない**。`release_manifest.json` の現行契約は portal
**86 図/12 テーマ**（Jupyter Book は `book/_toc.yml` の root + 30 entries = 31 ページで、ページ数自体は
manifest の契約値ではなく `book_name` の掲載のみが検証される）。G8 で fresh artifact/notebook/
report/book/test/lint を再検証し、最終結果と model risk を `johnhull/VALIDATION.md`
に固定した。strict tracked gate と専用 branch への remote push も完了し、その branch は
`main` へ merge 済み（release 履歴は `VALIDATION.md` の Release decision 表）。
research track は既定無効・core gate 非依存のままとする。

## Inflation-linked rates and JGBi — Phase 1–7 (2026-07-19)

Design plan: `docs/superpowers/plans/2026-07-19-johnhull-inflation-jgbi.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 26 | `volumes/26_inflation_jgbi` | inflation-linked rates and JGBi (beyond Hull ch.25) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | Shared nominal/real curve helpers | done |
| 2 | Hull–White 1F curve fit, exact transition, bond option, Jamshidian swaption | done |
| 3 | CPI lag/interpolation/rebasing, deterministic seasonality, ZCIS, YoY | done |
| 4 | JGBi tenth-day reference index, rounding, cash flow, settlement, real yield | done |
| 5 | Jarrow–Yildirim nominal/real numeraires and payment-forward measures | done |
| 6 | JGBi redemption-only deflation floor, analytic/MC value and risk | done |
| 7 | `volumes/26_inflation_jgbi` reproducible artifact-only notebook | done |

Phase 7 の `done` は synthetic-offline の integration/reproducibility gate を表し、
市場較正、production valuation、model performance の承認ではない。Portal（`rates_swaps`
テーマの `inflation_curves`・`inflation_swaps`・`jgbi_floor`・`jgbi_bei` 4 図）、
Jupyter Book 登録、full tracked release への収録はいずれも完了した。

## Advanced VaR/ES risk desk — Phase 1–6 (2026-07-20)

Design plan: `docs/superpowers/plans/2026-07-20-johnhull-27-risk-desk.md`

| Volume | Path | Topic | Status |
|---:|---|---|---|
| 27 | `volumes/27_risk_desk` | advanced daily VaR/ES risk desk (beyond Hull ch.22) | done |

| Phase | Scope | Status |
|---:|---|---|
| 1 | VaR backtesting: Kupiec POF, Christoffersen ind/CC, quantified Basel traffic light | done |
| 2 | Filtered historical simulation and EVT/GPD peaks-over-threshold tail VaR/ES | done |
| 3 | Euler risk decomposition: marginal/component/incremental VaR and simulation ES | done |
| 4 | P&L explain: factor exposures, delta-gamma-vega attribution, limits, desk report | done |
| 5 | `volumes/27_risk_desk` reference, `_volume27` acceptance, artifact-only notebook | done |
| 6 | Portal `risk_management` page, Jupyter Book page, full tracked release | done |

Phase 5 の `done` は synthetic-offline の integration/reproducibility gate（`_volume27`
の 14 恒等式チェックと byte 再現性）を表し、市場較正・model performance の承認ではない。
恒等式チェックは当初 11 個で、2026-07-20 の review-fix 運用で
`christoffersen_pvalue_matches_recomputation` と `cross_asset_factor_mapping` を追加した。
Phase 6 の portal 図（`var_traffic_light`・`fhs_vs_hs_coverage`・`gpd_tail_fit`・
`risk_allocation_bars`）、`risk_management` book page、Jupyter Book 登録、full tracked
release はすべて完了した（commit 691877f, 63f83ce）。

FRTB IMA（liquidity-horizon ES 集約、stressed ES scaling、NMRF、P&L attribution
eligibility test、IMA/SA 資本比較）は **vol 29 候補**として scope 外に記録する。

## vol 28 — 信用デスク（Hull Ch.24–25 の節単位の完全実装、2026-09-14）

Design: `docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`

| # | Volume | 内容 | Status |
|---|--------|------|--------|
| 28 | `volumes/28_credit_desk` | 24.4 債券/CDS ブートストラップ、24.7 ネッティング・担保・式 (24.5)、24.9 CreditMetrics、25.2 CDS レッグ/MTM/バイナリ、25.4 固定クーポン、25.5 フォワード/オプション、25.6+25.10 k-th-to-default、25.10 合成 CDO と コンパウンド/ベース相関、25.11 double-t・不均質再帰 | done |

vol 09 の設計書（2026-06-08）で「md/conceptual only」とした項目のうち、Hull 本文に数値例が
あるものをすべて hullkit（`credit_curve` / `cds` / `credit_portfolio` / `credit_metrics` / `xva` 追加分）
に実装し、印刷値に固定した。KMV EDF、ランダム回収率・ファクター負荷、implied copula、
動的モデルはコードを持たず、vol 28 notebook の「本巻で実装しない節」に Hull の説明と本巻の実装との
関係を置いた。`done` は integration・恒等式・再現性・教科書ピンの PASS を表し、
市場較正の承認ではない。

## 全節監査と是正 — 第 1〜4 便完了（2026-09-14〜15）

監査: `docs/SECTION_AUDIT_2026-09-14.md`（初回監査は §0–§10、修正の経緯は §11–§11.3、ID 別の現状は §12）。
レビュー: `docs/SECTION_AUDIT_2026-09-14_FEEDBACK.md`（初回レビューは `bd278948` の履歴）。実行記録: `VALIDATION.md`。

Hull GE 版の全 306 節と vol 13–28 を棚卸しし、実物で確認した欠陥 11 件（D1–D11）から順に直した。
各便とも、全ゲート PASS を確認してから `main` へ fast-forward し、push した。

| 便 | 終点 commit | 範囲 | hullkit+report tests | Status |
|---|---|---|---:|---|
| 1 | `90e903ea` | D1–D8・D10・D11（ゼロ曲線、期中スワップ評価、vol 22 のイベント分散、vol 21 の Greek 指標、vol 23 の Hagan グリッド、vol 26 のヘッジ分解、HJM/BGM の RMSE、ノート出力の照合、Ch.13 の GE 値、vol 28 の範囲外モデル） | 917 | done |
| 2 | `8485cc29` | vol 23–25・27・28 の acceptance を配列から再計算（tamper テスト）、Hull の印刷値ピン 71 件、文書の一括修正、R5・R9・R10 | 1055 | done |
| 3 | `83905890` | vol 18–22・26 の再計算化（tamper 契約を全 11 巻へ）、§4 の関数追加（現金配当・Black 近似、BL 密度、エキゾチックの put 側、分散スワップ、利回りの凸性調整）、BB-03・07・10・17、D9（core ノートの出力をコミットし静的 book に図を出す） | 1252 | done |
| 4 | `735197a6` | 進捗レビュー F1–F5（退化入力は FAIL 記録、core ノート出力の本文照合、vol 21 計測の来歴）、vol 18–28 の図の日本語フォント（字形欠落の警告 233 件）、文書の現状整理 | 1286 | done |

`done` は各便の integration・恒等式・再現性・印刷値ピンの PASS を表し、節単位の完全性や
model performance の承認ではない（deep_hedge_price の 206 tests も各便で PASS）。

到達点（2026-09-15、`735197a6`）:

- acceptance は vol 18–28 の 11 巻・118 チェックを、コミット済み配列から再計算する。
  選んだ改変が該当チェックと宣言した依存チェックだけを落とすことを tamper テストで固定。
- Jupyter Book は vol 01–16 と ir_models のコミット済み出力を表示する（ipympl は PNG、
  vol 13–16 は plotly.js 埋め込み）。コミット済み出力の本文は新規実行と照合する。
- vol 21 の timing には、計測したときの generator digest と環境が残る。

残り（`docs/SECTION_AUDIT_2026-09-14.md` §12・§7）:

| 区分 | 内容 |
|---|---|
| 保存値依存 | 根拠になる配列がない 8 チェック（vol 18・19・21・22・26）。原始データか実行時情報の保存が要る |
| 節カバレッジ | [節別台帳](docs/SECTION_LEDGER.md)へ306項目を登録。§26.9–§26.14の6項目受入、300項目未評価。最終統合判定は各受入ノートと統合記録を参照。完了率は確定値として使わない |
| 未再確認の監査報告 | R1（rBergomi の補償項）、R2（Log-HAR の再変換バイアス）、R3（予測からヘッジへの経路）、R4（vol 22 の共通乱数）、R6（dynamic fee の恒等式）、R11（Table 19.1 / 19.4 の乖離） |
| 未実装の節（§4） | Ch 26 の残り（EX-03・04）、金利ツリー・Bermudan・LMM（EX-13〜15）、Ch 2–7 の節単位実装（FR 系）、信用の残り（CR-05〜07・09〜11・13）、Ch 35–36 のツリー（CR-19・21・22）、深掘り巻の予告の回収（DD-04〜06）など |
| 判断事項（§7） | 既定 seed の統一（VN-20）、大物の置き場所（新しい節単位の巻を足すか）、FRTB IMA（vol 29 候補）、research track の扱い |
| ゲートの限界 | core は PNG と Plotly の中身を、frontier は stderr と図を比べない（字形欠落の警告とローカルパスだけをテストで検出） |

## 節単位の品質確認 — M1（2026-09-15）

[台帳](docs/SECTION_LEDGER.md) ／ [更新手順](docs/SECTION_LEDGER_GUIDE.md) ／
[実装計画](docs/superpowers/plans/2026-09-15-section-ledger-m1.md)。

M1は、原典outline由来の299節・7付録を台帳に登録し、要求・証跡・集計の整合性を検査する段階。
§26.9のB01–B09を受入済みとして登録し、残り305項目は未評価とした。
「未評価」は内容の再監査をしていないという状態で、実装がないという判定ではない。

| 段階 | 範囲 | 状態 |
|---|---|---|
| M1 | 全306項目のinventory、§26.9の要求と証跡、検査CLI、生成台帳 | 検証完了 |
| M2 | §26.10を原典の要求から説明・実装・独立検証・図・実画面まで確認 | D01–D06受入済み。教材・4図・独立検証・Book/portal確認、§26.9回帰検査を完了 |
| M3 | §26.11の要求抽出から教材・図・実画面まで確認 | M3b：L01–L06の本文6小節・共有4図・独立価格とBook/portal検査、全体1,695テストを完了。最終ブランチレビューも承認済み |
| M4 | §26.12を独立参照からツリー・本文・図・実画面まで確認 | M4b：S01–S06、42価格へのCRR収束、本文6小節・4図、Book/portal両面2幅を検証。Task1–3独立レビュー承認済み |
| M5 | §26.13の要求抽出・独立参照・既存近似の誤差測定から教材・図・実画面まで | 完了（accepted）。独立レビューのP2 6件とP3 1件に対応（F1–F7）。再レビューは利用者判断で省略。[レビュー結果](docs/SECTION_26_13_FEEDBACK_2026-09-16.md)・[受入ノート](docs/SECTION_26_13_ACCEPTANCE_2026-09-16.md) |
| M6 | §26.14 Options to Exchange One Asset for Another（pp.627–628）を要求整理から配布画面まで | 完了（accepted）。M6a：独立24価格（2求積が1.8e-14で一致）。M6b：API4関数・本文6小節・共有4図・Book/portal両面2幅。早期行使は同一格子で分離し、q_V=0で1.2e-13（格子残差2.7e-3）。[受入ノート](docs/SECTION_26_14_ACCEPTANCE_2026-09-17.md) |
| 以降 | 台帳を使って残る未評価節（§26.15–§26.17ほか）へ段階的に展開 | 未着手 |

M1のPASSは台帳と保存証跡の整合性を表す。数値モデルの再検証や全節の完成判定ではない。
M1と§26.9の試行は`ab825e03`としてmainへpush済み。
M2の現在地は[§26.10受入ノート](docs/SECTION_26_10_ACCEPTANCE_2026-09-15.md)、
M1実施時点の記録は[M1記録](docs/validation/section-ledger-m1/validation.json)。

現在地は[§26.14のM6b](docs/SECTION_26_14_ACCEPTANCE_2026-09-17.md)と
[統合記録](docs/validation/section-26-14/m6b-check.json)。台帳は受入6・未評価300。
`exchange_spread_volatility`・`exchange_option_american`・`better_of_two_assets`・`worse_of_two_assets`を追加し、
vol10 §4.4は6小節・4図になった。**早期行使プレミアムは同じ格子で行使判定を外した価格と比べて測る。**
閉形式と比べると離散化が混ざり、$q_V=0$でも2.3e-3の見かけのプレミアムが出る（実際は1.2e-13、格子残差2.7e-3）。
$r$非依存の図には「行使価格を今日の$U_0$に固定した誤読」という動く比較線を並べ、平坦な線が何と対比されるかを示した。
共有ソースの変更が及ぶ§26.9–§26.13は再検査して`m6b-recheck.json`に記録した。
再検査で82枚中5枚のスクリーンショットが変化した。4枚は文字のアンチエイリアス（最大12/255）で、
残る1枚はPlotlyのmodebarツールチップが完全に不透明な状態で写ったもの（最大86/255、差は右上の帯に限られる）。
図の中身の変化ではないため、コミット済み画像は復元した。

一つ前の現在地は[§26.13のM5b](docs/SECTION_26_13_ACCEPTANCE_2026-09-16.md)と
[統合記録](docs/validation/section-26-13/m5b-check.json)。
`asian_moments`・`asian_average_price`・`asian_seasoned_average_price`・`asian_average_strike`を追加し、
離散モーメントはO(m)で$r=q$でも定義される。vol10 §4.3は6小節・4図になり、Book/portal両面を1440/1000pxで検査した。
モーメント整合の近似誤差は144行中、参照価格0.5超の119行で+23.35%〜−6.85%（Example 26.3は外挿参照比で+0.99%）。全144行の範囲ではない。
実画面で図の欠陥を3件（半幅カード・タイトル切れ・2市場が同色）検出して直し、
実測と食い違っていた説明2件（歪度の向き・誤差の向き）を測定に合わせて書き換えた。
共有ソースの変更が及ぶ§26.9–§26.12は再検査して`m5b-recheck.json`に記録した。
2026-09-16の[独立レビュー](docs/SECTION_26_13_FEEDBACK_2026-09-16.md)は要修正（P2 6件・P3 1件）。
F1–F7すべてに対応した：$r=q$の可除特異点の説明、標準誤差に埋もれる5点の×印表示、
集計対象（119行／17行／0価格8行）の分離、反証済みの誤差方向の削除、既発契約の例の統一と表示表の独立照合、
観測数・幾何平均の一般化の限定、満期1観測の平均行使型を厳密に0にする修正。
独立再レビューは利用者の指示で省略し、acceptedへ変更した。修正後の状態を第三者が確認した受入ではない。

§26.14の[M6a](docs/SECTION_26_14_REVIEW_2026-09-16.md)時点では台帳はgaps_foundだった。
既存の`exchange_option`はMargrabe 1本で、教材は章対応表の1行とρの小表だけ、portalの図は0件だった。
独立24価格に加えて、原典が述べる4つの主張を測定した：r∈{0,8%,−2%}で価格が動かないこと（最大差1.8e-14）、
V/Uを原資産・行使1.0・金利qU・配当qVとする読み替え、better-of/worse-ofの分解（残差8.5e-14）、
Rubinsteinの米国型（qV=0で早期行使プレミアム1.9e-13、qV>0で最大4.2783）。
§26.14には印刷された例題が無いため、外部の正解に対するピンは存在しない。
M6bでE01–E06の本文・図・Book/portalの実画面確認まで揃い、acceptedへ変更した。
次は§26.15 Basket Options（p.628）。vol10 §4.5に式26.3・26.4の再掲だけがあり、独立検証も図も無い。

§26.12の現在地は[受入ノート](docs/SECTION_26_12_ACCEPTANCE_2026-09-16.md)と
[M4b統合記録](docs/validation/section-26-12/m4b-check.json)。
採用CRR N1024の42価格最大絶対残差は0.003793（許容差0.005）。境界は有限木の実ノード幅で、厳密な包含区間ではない。
portalは102図、vol10は92セル。putは原典外の独立拡張、r=qのlookbackは既存API未対応として欠測表示する。
§26.13では既存Asian実装の存在を受入判定へ流用せず、その誤差を測ってから教材に載せた。

M3b時点は[§26.11受入ノート](docs/SECTION_26_11_ACCEPTANCE_2026-09-16.md)と
[統合記録](docs/validation/section-26-11/m3b-check.json)。影響範囲407テストと、両配布面・2幅の検査を完了した。
台帳は受入済み3、不足あり0、未評価303。最終ブランチレビューも承認済み。
abs(r-q)<1e-8の価格API対応は今回の対象外で、教材に適用域を明示する。
[M3aの要求と残課題](docs/SECTION_26_11_REVIEW_2026-09-15.md)は実施時点の履歴として保持する。
