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
| 6 | `volumes/06_numerical_methods` | 21, 27 | done（§27.1–§27.5 は節単位で受入済み） |
| 7 | `volumes/07_swaps` | 7, 34 | done |
| 8 | `volumes/08_risk_var` | 22 | done |
| 9 | `volumes/09_credit_xva` | 9, 24, 25 | done（数値例のある節は vol 28 と hullkit のテストで実装・固定。残りは `docs/SECTION_AUDIT_2026-09-14.md` §4.5） |
| 10 | `volumes/10_exotics_martingales` | 26, 28 | done（§26.9–§26.17 は節単位で受入済み） |
| 11 | `volumes/11_ir_derivatives_market` | 29, 30 | done |
| 12 | `volumes/12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | done |

Shared module: `johnhull/hullkit` (uv workspace member) — 59 public + 14 private modules as of 2026-09-27; the catalogue is `MODEL_INDEX.md` (the original 14 were bsm, trees, mc, nbplot, payoffs, hedging, rates, volatility, fd, swaps, risk, credit, exotics, ir_options).

## 現在地（2026-09-27、M14受入・実装再開前の準備文書完成）

| 層 | 状態 | 詳細 |
|---|---|---|
| 章単位（Hull 11e 全 37 章） | 上表の 14 行すべて done（2026-06-08） | 章に巻があるという意味。節単位の完全性ではない |
| Beyond Hull（vol 13–28） | すべて done | A1–A4（vol 13–17）、A5–A8 G8 release（vol 18–25）、vol 26・27・28 |
| 全節監査の是正 | 第 1〜5 便完了 | 残りは下の「全節監査と是正」の表 |
| 節単位の受入 | M14（§27.5）まで。台帳は受入 14・未評価 292（4.6%） | 次は D1-preflight、その後 M15（§27.6）。全体計画は下の「完了までの計画」 |
| 実装再開前の準備 | [準備資料](docs/prep/README.md)完成。未評価292/292節、65/65出典、設計・再確認9本 | 件数・参照・YAML・台帳検査PASS、独立レビュー指摘を反映。文書と独立試算の成果であり、受入・製品実装は進めていない |
| 証跡の増加方針 D1 | [方針決定](docs/EVIDENCE_POLICY.md)。影響のある節を再描画し、不変の画像実体をハッシュで参照 | D1-preflight 実施中（段階1・2 完了：保管庫 C:/F:、依存指紋、schema 2 記録と台帳検査）。M15 はその完了後 |
| テスト | hullkit+report 2810 passed・6 skipped（M14、2026-09-27） | 実行結果は `VALIDATION.md` |

`done`・`accepted`・PASS は定義した integration・数値恒等式・再現性の PASS を表す。印刷値がある節ではそのピンも検証する。
データはすべて synthetic で、市場較正や model performance の承認ではない。

## 完了までの計画（2026-09-27 策定）

**更新ルール：** 節の受入、段階の着手・完了、判断事項の決定、計画の変更があったら、作業したエージェント
（Claude・Codex・Sol ほか誰でも）が**同じコミットで**この節と上の「現在地」を更新する。
件数は `docs/SECTION_LEDGER.md` の生成値に合わせ、手で数えない。規約は `AGENTS.md`／`CLAUDE.md` の「ROADMAP の更新」。

**完了の定義：** (1) 節別台帳の 306 項目がすべて `accepted` か `out_of_scope`、
(2) 下の P8（監査の残り）が対応済みか、判断を記録済み。

### 段階

「定性」は計算対象がない節の数（`docs/SECTION_AUDIT_2026-09-14.md` §1.2 の分類）。
「未評価」は再監査していないという意味で、実装がないという判定ではない
（監査時点で計算対象 243 節のうち code 107・nb 54 節には何らかの計算がある）。

| 段階 | 範囲 | 台帳の項目 | 受入済み | うち定性 | 主な課題 | 状態 |
|---|---|---:|---:|---:|---|---|
| P0 | §26.9–§27.4（M1–M13） | 13 | 13 | 0 | — | 完了 |
| P1 | Ch 27 の残り（§27.5–§27.8） | 4 | 1 | 0 | — | 進行中。D1-preflight 後に M15 §27.6 |
| P2 | Ch 26 の残り（§26.1–§26.8） | 8 | 0 | 0 | perpetual・Bermudan・forward start・cliquet・compound・chooser はコードがない（EX-03） | 下調べ済み・節受入未着手 |
| P3 | 金利（Ch 28–34） | 37 | 0 | 3 | HW/BK 三項ツリー・Bermudan・LMM がない（EX-13〜15）。最も重い | 下調べ・設計済み、節受入未着手 |
| P4 | オプションの中核（Ch 10–21） | 112 | 0 | 19 | 件数が最大。多くは実装済みで、印刷値での固定が中心 | 下調べ済み・節受入未着手 |
| P5 | リスク・信用（Ch 22–25） | 36 | 0 | 4 | vol 27・28 の資産を流用できる | 下調べ済み・節受入未着手 |
| P6 | 先物・金利の基礎（Ch 1–9） | 80 | 0 | 31 | 軽いが件数が多い。定性が多い | 下調べ済み・節受入未着手 |
| P7 | Ch 35–37 | 16 | 0 | 6 | §36.4 は本文にパラメータ σ(t)・η(t) がない（CR-23） | 下調べ済み・節受入未着手 |
| P8 | 監査の残り | — | — | — | 下の「全節監査と是正」の残り表（R1–R4・R6・R11、保存値依存 5 項目、§7 の判断事項） | [再確認済み](docs/prep/design/P8_RECHECK.md)、製品の修正は未着手 |
| **計** | | **306** | **14** | **63** | | **4.6%** |

### 先に決めること

| # | 事項 | 現状と影響 | 状態 |
|---|---|---|---|
| D1 | 再検査の証跡の増え方 | 1 マイルストーンの約 13MB の大半は、受入済みの全節を撮り直した再検査画像（節自身の証跡は §27.3 で 916KB、§27.4 で 472KB）。再検査量は受入済みの節数に比例して増えた（M7 7.7MB → M13 13.0MB）。この方式のまま 306 節まで進めると、証跡は合計**約 45GB**になる（実測の傾向からの外挿）。決定：依存の変わった節を再描画し、不変の実体を保持した参照とする（[D1方針](docs/EVIDENCE_POLICY.md)） | **方針決定・実装待ち**。M15 前に D1-preflight |
| D2 | 節ごとの notebook 検査の規約 | 次の節が同じ巻に入ると、前の節の検査が HEAD で FAIL していた（[レビュー F1](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。M14 で、現行 HEAD 用の `verify_accepted_vol06_notebook.py` が各節を受入 commit と照合する方式に変更 | M14 で対応済み |
| D3 | ペースと受入の軽量化 | 従来の概算は5〜10か月。現行台帳では説明とrenderedが必須で、画面検査を省略できない。[準備案](docs/prep/design/D3_LIGHT_ACCEPTANCE.md)は定性節のN/Aに理由を付け、buildと画面検査を章内で共有する。旧監査の定性63節は今回の混在分類と同一ではない | **案を作成・規約変更は未承認** |

### D1-preflight（M15 の前提）

[証跡方針](docs/EVIDENCE_POLICY.md) の順に、依存指紋と画像参照・保存復元器、
既存検証器の互換対応、1節での全再描画との比較、変更伝播と欠損・破損の負のテストを行う。
2コピーからの復元と既存 gate が通るまで、過去の証跡や台帳の参照を移さない。
数値・意味・release 検査と受入件数は変えず、D3 の軽量化は別判断とする。
[実装計画](docs/prep/design/D1_PREFLIGHT_PLAN.md)に依存指紋、旧形式互換、全再描画との比較、負の検査、復元の順序を具体化した。計画作成はpreflightのPASSではない。

| 段階 | 内容 | 状態 |
|---|---|---|
| 1 | 不変 blob の保存・復元器（`scripts/evidence_store.py`）と保管庫の実接続 | **完了（2026-09-28）**。C: `%USERPROFILE%\ProjectArtifacts\projects`（primary）と F: `F:\ProjectArtifacts\projects-backup`（mirror）を作成。§27.3 の画像2枚を両方に保存し、それぞれ別に復元してバイト一致。path traversal・欠損・1 byte 破損・切詰め・既存ファイル衝突・symlink 逸脱の拒否をテスト（47件） |
| 2 | 依存指紋と v2 record、台帳検査の互換対応 | **完了（2026-09-28）**。`scripts/evidence_fingerprint.py`（節スライス・Book の section・portal の図カード・ページ資産・hullkit の import 閉包・データ・検証器・環境）と `scripts/evidence_dependencies.json`（§27.3 を宣言）。§27.3 の notebook スライスの指紋は M12・M13・M14 の3 commit で同一（ファイル全体のハッシュは毎回変化）。`scripts/evidence_record.py` の schema 2 記録（redrawn / reused、再利用は redrawn の基準へ直接参照し連鎖を拒否）を `verify_section_ledger.py` が検査。schema 1 の既存記録は従来どおり（実台帳は通常・`--check-artifacts` とも PASS） |
| 3 | §27.3 で全再描画と基準再利用を比較 | 未着手 |
| 4 | 変更伝播の負の対照 | 未着手 |
| 5 | 小群の保管・既存 gate・統合記録 | 未着手 |

保管庫は環境変数 `PROJECTS_ARTIFACT_STORE`・`PROJECTS_ARTIFACT_MIRROR` で渡す（WSL では `/mnt/c/Users/<user>/ProjectArtifacts/projects`・`/mnt/f/ProjectArtifacts/projects-backup`）。未設定・未接続・marker なしは明示的なエラーで、空のフォルダーを自動作成しない。

### 本編の外の研究・拡張（完了条件に含めない）

[研究バックログ計画](docs/superpowers/plans/2026-09-27-research-backlog.md)（2026-09-27）は、
外部の[提案書](docs/RESEARCH_HANDOFF_2026-09-27.md)にある 94 件を次の4つに振り分けた：
本編に畳む（RB-F02→P1、RB-F03→P3、R11・§19.14・RB-H16→P4）、章の受入後のコラム、研究トラック（同時1本）、johnhull の外。
研究トラック #1 は RB-F07。研究の置き場は `research/<RB-ID>/`、計算は hullkit の非公開モジュールに決定した（2026-09-27 本人承認。公開 API 昇格は別承認）。
**実装再開は、johnhull に必要な保管庫と作業分離が整った時点**とし、ワークスペース全工程の完了は待たない。
M15 と RB-F07 は D1-preflight の検証完了後に着手する。[準備文書](docs/prep/README.md)は292節・65出典・設計等9本を完成し、構造検査と独立レビューを終えた。出典は支持23件・部分確認42件で、性能の独立再現とは区別する。受入件数は変わらない。
金利編は [P3設計](docs/prep/design/P3_DESIGN.md)でHW/BKの本文範囲と独立参照の条件を整理した。R11の原典成績は利息・割引を除外する規約で再現でき、現行の資金繰り計算を誤りとみなして置換しない。

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
**134 図/12 テーマ**で、監査第 4 便の 82 図に節単位受入 M2–M14 の共有 4 図×13 節が加わった（2026-09-27）。
Jupyter Book は `book/_toc.yml` の root + 30 entries = 31 ページで、ページ数自体は
manifest の契約値ではなく `book_name` の掲載のみが検証される。G8 で fresh artifact/notebook/
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

## 全節監査と是正 — 第 1〜5 便完了（2026-09-14〜25）

監査: `docs/SECTION_AUDIT_2026-09-14.md`（初回監査は §0–§10、修正の経緯は §11–§11.4、ID 別の現状は §12）。
レビュー: `docs/SECTION_AUDIT_2026-09-14_FEEDBACK.md`（初回レビューは `bd278948` の履歴）。実行記録: `VALIDATION.md`。

Hull GE 版の全 306 節と vol 13–28 を棚卸しし、実物で確認した欠陥 11 件（D1–D11）から順に直した。
各便とも、全ゲート PASS を確認してから `main` へ fast-forward し、push した。

| 便 | 終点 commit | 範囲 | hullkit+report tests | Status |
|---|---|---|---:|---|
| 1 | `90e903ea` | D1–D8・D10・D11（ゼロ曲線、期中スワップ評価、vol 22 のイベント分散、vol 21 の Greek 指標、vol 23 の Hagan グリッド、vol 26 のヘッジ分解、HJM/BGM の RMSE、ノート出力の照合、Ch.13 の GE 値、vol 28 の範囲外モデル） | 917 | done |
| 2 | `8485cc29` | vol 23–25・27・28 の acceptance を配列から再計算（tamper テスト）、Hull の印刷値ピン 71 件、文書の一括修正、R5・R9・R10 | 1055 | done |
| 3 | `83905890` | vol 18–22・26 の再計算化（tamper 契約を全 11 巻へ）、§4 の関数追加（現金配当・Black 近似、BL 密度、エキゾチックの put 側、分散スワップ、利回りの凸性調整）、BB-03・07・10・17、D9（core ノートの出力をコミットし静的 book に図を出す） | 1252 | done |
| 4 | `735197a6` | 進捗レビュー F1–F5（退化入力は FAIL 記録、core ノート出力の本文照合、vol 21 計測の来歴）、vol 18–28 の図の日本語フォント（字形欠落の警告 233 件）、文書の現状整理 | 1286 | done |
| 5 | `7d04851e` | vol 26 の保存値依存 3 項目を配列からの再計算へ（改竄テスト 8 件、reference 配列 7 本追加。監査文書 §11.4） | 2630（`johnhull/tests` を含む） | done |

`done` は各便の integration・恒等式・再現性・印刷値ピンの PASS を表し、節単位の完全性や
model performance の承認ではない（deep_hedge_price の 206 tests も各便で PASS）。

到達点（第 4 便、2026-09-15、`735197a6`）:

- acceptance は vol 18–28 の 11 巻・118 チェックを、コミット済み配列から再計算する。
  選んだ改変が該当チェックと宣言した依存チェックだけを落とすことを tamper テストで固定。
- Jupyter Book は vol 01–16 と ir_models のコミット済み出力を表示する（ipympl は PNG、
  vol 13–16 は plotly.js 埋め込み）。コミット済み出力の本文は新規実行と照合する。
- vol 21 の timing には、計測したときの generator digest と環境が残る。

残り（`docs/SECTION_AUDIT_2026-09-14.md` §12・§7）:

| 区分 | 内容 |
|---|---|
| 保存値依存 | 根拠になる配列がない 5 項目（vol 18・19・21・22）。原始データか実行時情報の保存が要る。vol 26 の 3 項目は 2026-09-25 に配列からの再計算へ移した（監査文書 §11.4） |
| 節カバレッジ | [節別台帳](docs/SECTION_LEDGER.md)へ306項目を登録。§26.9–§27.5の14項目受入、292項目未評価。最終統合判定は各受入ノートと統合記録を参照。完了率は確定値として使わない |
| 再確認済み・製品対応待ち | [P8再確認](docs/prep/design/P8_RECHECK.md)：R1（分散更新・補償項）、R2（Log-HAR再変換）、R3（予測→ヘッジ未接続）、R4（共通乱数のずれ）、R6（gross/netの分離）。R11はTables19.1/19.4の利息・割引規約差を特定し、P4の受入fixture化待ち |
| 未実装の節（§4） | Ch 26 の残り（EX-03 のうち §26.2–§26.8 の perpetual American・Bermudan・forward start・cliquet・compound・chooser。EX-04 は M5–M7 の公開 API で、§26.12 の shout は M4 の非公開モジュールで対応）、金利ツリー・Bermudan・LMM（EX-13〜15）、Ch 2–7 の節単位実装（FR 系）、信用の残り（CR-05〜07・09〜11・13）、Ch 35–36 のツリー（CR-19・21・22）、深掘り巻の予告の回収（DD-04〜06）など |
| 判断事項（§7） | 既定 seed の統一（VN-20）、大物の置き場所（新しい節単位の巻を足すか）、FRTB IMA（vol 29 候補）は継続。research trackは[研究計画](docs/superpowers/plans/2026-09-27-research-backlog.md)で置き場・順番・範囲・実装再開条件を決定 |
| ゲートの限界 | core は PNG と Plotly の中身を、frontier は stderr と図を比べない（字形欠落の警告とローカルパスだけをテストで検出） |

## 節単位の品質確認 — M1–M14（2026-09-15〜27）

[台帳](docs/SECTION_LEDGER.md) ／ [更新手順](docs/SECTION_LEDGER_GUIDE.md) ／
[実装計画](docs/superpowers/plans/2026-09-15-section-ledger-m1.md)。

M1は、原典outline由来の299節・7付録を台帳に登録し、要求・証跡・集計の整合性を検査する段階。
「未評価」は内容の再監査をしていないという状態で、実装がないという判定ではない。
M1のPASSは台帳と保存証跡の整合性を表し、数値モデルの再検証や全節の完成判定ではない
（M1と§26.9の試行は`ab825e03`、[M1記録](docs/validation/section-ledger-m1/validation.json)）。

M2以降は1節ずつ、原典の要求抽出 → 独立参照 → 公開API → 本文6小節・共有4図 →
Book/portal両面2幅の実画面 → 受入ノート、の順で受け入れる。数値・レビュー指摘と対応・
既受入節の再検査記録は各受入ノートが正本で、下表は1行要約に留める。

| 段階 | 節 | 状態 |
|---|---|---|
| M1 | 全306項目のinventory、§26.9 B01–B09の要求と証跡、検査CLI、生成台帳 | 検証完了 |
| M2 | §26.10（D01–D06） | 受入。[受入ノート](docs/SECTION_26_10_ACCEPTANCE_2026-09-15.md) |
| M3 | §26.11（L01–L06） | 受入。最終ブランチレビュー承認。[受入ノート](docs/SECTION_26_11_ACCEPTANCE_2026-09-16.md) |
| M4 | §26.12（S01–S06、CRR N1024で42価格） | 受入。Task1–3独立レビュー承認。[受入ノート](docs/SECTION_26_12_ACCEPTANCE_2026-09-16.md) |
| M5 | §26.13 Asian | 受入。独立レビューP2 6件・P3 1件に対応（F1–F7）、**再レビューは利用者判断で省略**。[受入ノート](docs/SECTION_26_13_ACCEPTANCE_2026-09-16.md)・[レビュー](docs/SECTION_26_13_FEEDBACK_2026-09-16.md) |
| M6 | §26.14 Exchange options（pp.627–628） | 受入。独立24価格、早期行使は同一格子で分離。[受入ノート](docs/SECTION_26_14_ACCEPTANCE_2026-09-17.md) |
| M7 | §26.15 Basket options（pp.628–629） | 受入。独立72価格、近似誤差の範囲を明示。[受入ノート](docs/SECTION_26_15_ACCEPTANCE_2026-09-19.md) |
| M8 | §26.16 Volatility and variance swaps（pp.629–632） | 受入。Example 26.4/26.5を再現、独立レビュー2本＋再レビュー。[受入ノート](docs/SECTION_26_16_ACCEPTANCE_2026-09-25.md)・[指摘と対応](docs/SECTION_26_16_FEEDBACK_2026-09-25.md) |
| M9 | §26.17 Static options replication（pp.632–634） | 受入。Table 26.1と3/18/100点を独立再計算。[受入ノート](docs/SECTION_26_17_ACCEPTANCE_2026-09-25.md) |
| M10 | §27.1 Alternatives to BSM（pp.641–646） | 受入。CEV・Merton・VG、Table 27.1とFigure 27.1。[受入ノート](docs/SECTION_27_1_ACCEPTANCE_2026-09-25.md) |
| M11 | §27.2 Stochastic volatility models（pp.646–649） | 受入。式27.1・Hull–White混合公式・Heston COS・SABRを独立参照で照合。[受入ノート](docs/SECTION_27_2_ACCEPTANCE_2026-09-26.md) |
| M12 | §27.3 The IVF Model（pp.649–650） | 受入。式27.4を独立解析式33点・後退PDE9価格・二時点paired MCで照合。[受入ノート](docs/SECTION_27_3_ACCEPTANCE_2026-09-27.md)・[レビュー](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)（P3 2件） |
| M13 | §27.4 Convertible Bonds（pp.650–653） | 受入。Example 27.1／Figure 27.2の10節点、コール後再転換、信用・回収・利払いを照合。[受入ノート](docs/SECTION_27_4_ACCEPTANCE_2026-09-27.md)・[レビュー](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)（Example 27.1 を独立に再計算して一致） |
| M14 | §27.5 Path-Dependent Derivatives（pp.653–656） | 受入。Figure 27.3のX/Y/Z、20段・60段の欧州型/米国型4価格、独立全経路列挙を照合。[受入ノート](docs/SECTION_27_5_ACCEPTANCE_2026-09-27.md) |
| 以降 | §27.6 から台帳の未評価節へ順に展開 | 未着手 |

現在地（2026-09-27）：M14まで受入、台帳は受入14・未評価292。M12・M13のレビューP3 2件はM14着手時に対応。統合記録は`docs/validation/section-27-5/m14-check.json`。次はM15 §27.6。
各段階で、共有ソースを変えたときは既受入節の個別テストと両画面を再検査し、台帳の現行証跡へ接続している。

受入を通じて決まった進め方と、残している制限:

- 既存のhullkit実装や説明なしのコードセルは受入の根拠にしない。NumPy/SciPyだけの独立参照を先に作り、既存実装はその誤差を測ってから教材に載せる（M5・M8）。
- 早期行使プレミアムは閉形式ではなく、同じ格子で行使判定を外した価格と比べて測る。閉形式と比べると離散化誤差が混ざる（M6）。
- 再検査のスクリーンショット差分は、文字のアンチエイリアスやmodebarツールチップと図の中身の変化を分けて判定する。前者ならコミット済み画像を戻す（M6b）。
- 適用域の制限：§26.11の価格APIは$|r-q|<10^{-8}$に未対応（教材に適用域として明示）、§26.12のlookbackは$r=q$を欠測表示、putは原典外の独立拡張。
- M5は修正後の状態を第三者が確認していない受入である。
- 節ごとの notebook 検査は受入時点の基点との比較として保持する。現行HEADでは `verify_accepted_vol06_notebook.py --check` が§27.1–§27.4の自節セルを各受入commitと比較し、共有図と巻全体を再実行する。M14の§27.5は直前M13基点の節外保持検査を持つ。後続節の追加時に現行HEAD用検査の対象を増やす（[レビュー F1 対応](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。
