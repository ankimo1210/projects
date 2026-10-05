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
| 6 | `volumes/06_numerical_methods` | 21, 27 | done（§27.1–§27.8 は節単位で受入済み） |
| 7 | `volumes/07_swaps` | 7, 34 | done |
| 8 | `volumes/08_risk_var` | 22 | done |
| 9 | `volumes/09_credit_xva` | 9, 24, 25 | done（数値例のある節は vol 28 と hullkit のテストで実装・固定。残りは `docs/SECTION_AUDIT_2026-09-14.md` §4.5） |
| 10 | `volumes/10_exotics_martingales` | 26, 28 | done（§26.1–§26.17 は節単位で受入済み） |
| 11 | `volumes/11_ir_derivatives_market` | 29, 30 | done |
| 12 | `volumes/12_qualitative_summary` | 1, 8, 16, 35, 36, 37 | done |

Shared module: `johnhull/hullkit` (uv workspace member) — 72 public + 37 private modules on main as of 2026-10-05 (later P3 logic is on `codex/p3-logic`); the catalogue is `MODEL_INDEX.md` (the original 14 were bsm, trees, mc, nbplot, payoffs, hedging, rates, volatility, fd, swaps, risk, credit, exotics, ir_options).

## 現在地（2026-10-05、受入保留・P4ロジック実装）

| 層 | 状態 | 詳細 |
|---|---|---|
| 章単位（Hull 11e 全37章） | 上表14行すべてdone | 巻があるという意味。節単位の完全性ではない |
| Beyond Hull（vol13–28） | すべてdone | A1–A4、A5–A8 G8 release、vol26/27/28 |
| 全節監査の是正 | 第1–5便完了 | 残りは「全節監査と是正」の表 |
| 節単位の受入 | Ch28まで受入33・未評価273（10.8%） | P0/P1/P2完了、P3正式8/37・ロジック36/37。§33.2は入力不足で保留。受入を一時停止し、次段階P4の計算を先行する。[P3状態](docs/P3_STATUS.md) |
| ロジック先行 | P3 36/37、P4 26節実装 | 受入はCh28を区切りに保留。codex/p4-logicでCh10–13の計算を先行、対象tests/ruffを節ごと確認。[P4状態](docs/P4_STATUS.md) |
| 実装再開前の準備 | [準備資料](docs/prep/README.md)完成 | 下調べ292/292節・65/65出典・設計/再確認9本。準備時点の件数で、製品の節受入とは区別 |
| 証跡D1 | [方針](docs/EVIDENCE_POLICY.md)。Ch28：依存変更2節を再検査 | §28.2/28.5のbrowser/runtime/pytest・両保管庫PASS。他28節は完全指紋とruntimeが同じ直接のredrawn基点を再利用。新6図/24表示状態と基点画像の両コピー復元PASS。[章記録](docs/validation/chapter-28/acceptance-check.json) |
| テスト・レビュー | Ch28全suite1回4,436 passed・6 skipped・3 failed、修正対象70 tests PASS | 3件は索引/図件数/台帳の更新漏れ。初回＋修正対象で4,439件を確認（全suite再実行なし）。台帳成果物/章check/release PASS。数式レビューはClaudeが後追い。[全suite記録](docs/validation/chapter-28/full-suite.json) |

`done`・`accepted`・PASS は定義した integration・数値恒等式・再現性の PASS を表す。印刷値がある節ではそのピンも検証する。
データはすべて synthetic で、市場較正や model performance の承認ではない。

## 完了までの計画（2026-09-27 策定）

**更新ルール：** 節の受入、段階の着手・完了、判断事項の決定、計画の変更があったら、作業したエージェント
（Claude・Codex・Sol ほか誰でも）が**同じコミットで**この節と上の「現在地」を更新する。
件数は `docs/SECTION_LEDGER.md` の生成値に合わせ、手で数えない。規約は `AGENTS.md`／`CLAUDE.md` の「ROADMAP の更新」。

ユーザー指定（2026-10-03）：各ターンの最終応答の末尾に、P0–P8の全体ロードマップと現在の作業を表示する。

**完了の定義：** (1) 節別台帳の 306 項目がすべて `accepted` か `out_of_scope`、
(2) 下の P8（監査の残り）が対応済みか、判断を記録済み。

### 段階

「定性」は計算対象がない節の数（`docs/SECTION_AUDIT_2026-09-14.md` §1.2 の分類）。
「未評価」は再監査していないという意味で、実装がないという判定ではない
（監査時点で計算対象 243 節のうち code 107・nb 54 節には何らかの計算がある）。

| 段階 | 範囲 | 台帳の項目 | 受入済み | うち定性 | 主な課題 | 状態 |
|---|---|---:|---:|---:|---|---|
| P0 | §26.9–§27.4（M1–M13） | 13 | 13 | 0 | — | 完了 |
| P1 | Ch 27 の残り（§27.5–§27.8） | 4 | 4 | 0 | — | 完了（M14–M17） |
| P2 | Ch 26 の残り（§26.1–§26.8） | 8 | 8 | 0 | — | 完了（M18–M25）。chooser EX-03を受入 |
| P3 | 金利（Ch 28–34） | 37 | 8 | 3 | ロジック36/37、§33.2は原典入力不足 | Ch28全8節受入、Ch29–34受入29節を保留。本人指示2026-10-05でP4実装へ |
| P4 | オプションの中核（Ch 10–21） | 112 | 0 | 19 | 既存実装を利用し、本文数値・不足計算をprivateで補う | codex/p4-logicで計算26節を実装。次は§13.10（段数・DerivaGemの数値部分）。教材・正式受入は保留 |
| P5 | リスク・信用（Ch 22–25） | 36 | 0 | 4 | vol 27・28 の資産を流用できる | 下調べ済み・節受入未着手 |
| P6 | 先物・金利の基礎（Ch 1–9） | 80 | 0 | 31 | 軽いが件数が多い。定性が多い | 下調べ済み・節受入未着手 |
| P7 | Ch 35–37 | 16 | 0 | 6 | §36.4 は本文にパラメータ σ(t)・η(t) がない（CR-23） | 下調べ済み・節受入未着手 |
| P8 | 監査の残り | — | — | — | 下の「全節監査と是正」の残り表（R1–R4・R6・R11、保存値依存 5 項目、§7 の判断事項） | [再確認済み](docs/prep/design/P8_RECHECK.md)、製品の修正は未着手 |
| **計** | | **306** | **33** | **63** | | **10.8%** |

### 先に決めること

| # | 事項 | 現状と影響 | 状態 |
|---|---|---|---|
| D1 | 再検査の証跡の増え方 | 1 マイルストーンの約 13MB の大半は、受入済みの全節を撮り直した再検査画像（節自身の証跡は §27.3 で 916KB、§27.4 で 472KB）。再検査量は受入済みの節数に比例して増えた（M7 7.7MB → M13 13.0MB）。この方式のまま 306 節まで進めると、証跡は合計**約 45GB**になる（実測の傾向からの外挿）。決定：依存の変わった節を再描画し、不変の実体を保持した参照とする（[D1方針](docs/EVIDENCE_POLICY.md)） | **M15 で本運用**（下の「節単位の品質確認」） |
| D2 | 節ごとの notebook 検査の規約 | 次の節が同じ巻に入ると、前の節の検査が HEAD で FAIL していた（[レビュー F1](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。M14 で、現行 HEAD 用の `verify_accepted_vol06_notebook.py` が各節を受入 commit と照合する方式に変更 | M14 で対応済み |
| D3 | ペースと受入の軽量化 | 従来の概算は5〜10か月。現行台帳では説明とrenderedが必須で、画面検査を省略できない。[準備案](docs/prep/design/D3_LIGHT_ACCEPTANCE.md)は定性節のN/Aに理由を付け、buildと画面検査を章内で共有する。旧監査の定性63節は今回の混在分類と同一ではない | **2026-10-03本人承認済み（PR #11反映案）。2026-10-04、章末まとめ受入で運用する指示** |

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
| 3 | §27.3 で全再描画と基準再利用を比較 | **完了（2026-09-28）**。`scripts/d1_preflight_compare.py` が既存の検証器を書き換えずに（宣言した見出し番号2か所の置換のみ、`scripts/run_browser_verifier.cjs`）overlay の root で実行し、既存の証跡には書き込まない。A（全再描画）: 16 状態の数値・配置検査と pytest 14 件が PASS、画像 16 枚・413,577 B を C:/F: に保存し各コピーから復元一致。B（基準再利用）: 同じ 16 状態・同じ検査が PASS、新規保存 0 B、A の画像へ直接参照し両コピーから復元・閲覧できた。新しい撮影は 16/16 が A・M14 再検査・受入時の画像とバイト一致。実行時の Chromium 145.0.7632.6・MathJax 3.2.2・実フォント（Liberation Sans と Droid Sans Fallback。fc-match の Noto Sans とは異なる）も記録し、再利用の条件にした。記録は `docs/validation/d1-preflight/section-27-3/` |
| 4 | 変更伝播の負の対照 | **完了（2026-09-28）**。`scripts/d1_preflight_negative.py` が実際の §27.3 の入力を overlay 上でだけ書き換えて判定（プロジェクトには書き込まない）。17 件すべて期待どおり：§27.3 の前に節を足す（notebook の id・実行番号・図の UUID、Book の自動 id、portal のカード）→ 再利用可・検証器 PASS。本文1文字・portal の値・参照データ・共有 CSS・Book のテーマ JS・plotly.js・hullkit のソース・fc-match のフォント・正規化の版・未宣言の節・未構築のページ → 再描画。値と参照データの変更では既存の検証器も FAIL（例 `ivf_local values 0[0]: 32.82 != 32.32`）。実行時の Chromium・MathJax JS・実フォントの変化、C: の blob 欠損、F: の 1 byte 破損 → 再利用を拒否。途中で overlay が節ディレクトリ内の差し替えを無視するバグを負の対照が検出し、修正した |
| 5 | 小群の保管・既存 gate・統合記録 | **完了（2026-09-28）**。[実証記録](docs/validation/d1-preflight/README.md)に §27.3 の16画像・413,577 bytesの2コピー復元、再利用時の新規保存0、負の対照17件、全体 pytest 2,995 passed / 6 skipped、台帳の source / artifact 検査、release・独立数値検証の PASS を記録。Book は初回生成後の全ページ再ビルドで既存ハッシュに一致 |

保管庫は環境変数 `PROJECTS_ARTIFACT_STORE`・`PROJECTS_ARTIFACT_MIRROR` で渡す（WSL では `/mnt/c/Users/<user>/ProjectArtifacts/projects`・`/mnt/f/ProjectArtifacts/projects-backup`）。未設定・未接続・marker なしは明示的なエラーで、空のフォルダーを自動作成しない。

### 本編の外の研究・拡張（完了条件に含めない）

[研究バックログ計画](docs/superpowers/plans/2026-09-27-research-backlog.md)（2026-09-27）は、
外部の[提案書](docs/RESEARCH_HANDOFF_2026-09-27.md)にある 94 件を次の4つに振り分けた：
本編に畳む（RB-F02→P1、RB-F03→P3、R11・§19.14・RB-H16→P4）、章の受入後のコラム、研究トラック（同時1本）、johnhull の外。
研究トラック #1 は RB-F07。研究の置き場は `research/<RB-ID>/`、計算は hullkit の非公開モジュールに決定した（2026-09-27 本人承認。公開 API 昇格は別承認）。
**実装再開は、johnhull に必要な保管庫と作業分離が整った時点**とし、ワークスペース全工程の完了は待たない。
M15 は D1-preflight の完了後に実施し、2026-09-28 に受入。M16（§27.7）も同日に受入。M17（§27.8）は2026-09-29 に受入し、P1 を完了した（RB-F02 の推定経路と評価経路の分離を含む。上界の実装は拡張のまま）。M18（§26.1 Packages）で P2 に入り、M19（§26.2 永久アメリカン）も同日に受入。M20（§26.3 非標準アメリカン）は2026-09-30に受入。M21（§26.4 ギャップ）とM22（§26.5 フォワード・スタート）、M23（§26.6 Cliquet）、M24（§26.7 Compound）は2026-10-01に受入。M25（§26.8 Chooser）は2026-10-03に受入しP2を完了。M26（§28.1 市場リスクの価格）は同日受入・main統合済み。M27（§28.2 複数状態変数）も同日に受入しP3は2/37、独立最終レビューと修正後検証、main統合/push済み。M28（§28.3）は2026-10-04受入、P3 3/37。独立最終レビューI1修正済み、main統合/push済み。M29（§28.4）は受入、P3 4/37、独立レビューCritical0/Important0、Minor3記録。main統合・push済み。M30 §28.5はmain統合/push済み、P3 5/37。本人の2026-10-04指示で§28.6以降はロジック先行、章末まとめ受入。ロジック36/37をcodex/p3-logicへpush済み、§33.2は原典入力不足で保留。Ch28の§28.6–28.8をD3共通設定ツールで受入しP3 8/37、受入を保留しP4（Ch10–21）のロジックを先行する。RB-F07 は未着手。[準備文書](docs/prep/README.md)は292節・65出典・設計等9本を完成し、構造検査と独立レビューを終えた。出典は支持23件・部分確認42件で、性能の独立再現とは区別する。
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
**204 図/12 テーマ**。監査第4便82図＋M2–M25共有4図×24節＋M26–M30共有4図×5節＋Ch28章末共有6図（2026-10-05）。
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
| 節カバレッジ | [節別台帳](docs/SECTION_LEDGER.md)の306項目。§26.1–§26.17、§27.1–§27.8、§28.1–§28.5の30項目受入、276項目未評価。最終判定は各受入ノートと統合記録を参照 |
| 再確認済み・製品対応待ち | [P8再確認](docs/prep/design/P8_RECHECK.md)：R1（分散更新・補償項）、R2（Log-HAR再変換）、R3（予測→ヘッジ未接続）、R4（共通乱数のずれ）、R6（gross/netの分離）。R11はTables19.1/19.4の利息・割引規約差を特定し、P4の受入fixture化待ち |
| 未実装の節（§4） | Ch26 EX-03/04はM4–M7・M21–M25で対応済み。残りは金利ツリー・Bermudan・LMM（EX-13〜15）、Ch 2–7 の節単位実装（FR 系）、信用の残り（CR-05〜07・09〜11・13）、Ch 35–36 のツリー（CR-19・21・22）、深掘り巻の予告の回収（DD-04〜06）など |
| 判断事項（§7） | 既定 seed の統一（VN-20）、大物の置き場所（新しい節単位の巻を足すか）、FRTB IMA（vol 29 候補）は継続。research trackは[研究計画](docs/superpowers/plans/2026-09-27-research-backlog.md)で置き場・順番・範囲・実装再開条件を決定 |
| ゲートの限界 | core は PNG と Plotly の中身を、frontier は stderr と図を比べない（字形欠落の警告とローカルパスだけをテストで検出） |

## 節単位の品質確認 — M1–M33（2026-09-15〜2026-10-05）

[台帳](docs/SECTION_LEDGER.md) ／ [更新手順](docs/SECTION_LEDGER_GUIDE.md) ／
[実装計画](docs/superpowers/plans/2026-09-15-section-ledger-m1.md)。

M1は、原典outline由来の299節・7付録を台帳に登録し、要求・証跡・集計の整合性を検査する段階。
「未評価」は内容の再監査をしていないという状態で、実装がないという判定ではない。
M1のPASSは台帳と保存証跡の整合性を表し、数値モデルの再検証や全節の完成判定ではない
（M1と§26.9の試行は`ab825e03`、[M1記録](docs/validation/section-ledger-m1/validation.json)）。

M2–M30は節単位で、原典の要求抽出 → 独立参照 → API → 教材・共有図 →
Book/portal両面2幅の実画面 → 受入ノート、の順で受け入れた。M31以降は本人指示に従い
private計算を先行し、D3の共通設定ツールで説明とrenderedを含む5軸を章末にまとめて受け入れる。数値・レビュー指摘と対応・
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
| M15 | §27.6 Barrier Options（pp.656–658） | 受入。素朴な二項・三項、内側・外側バリアと補間、バリア上のノード（Figures 27.4–27.5）を解析値・PDE・前向き格子で照合。D1 の本運用初回。[受入ノート](docs/SECTION_27_6_ACCEPTANCE_2026-09-28.md)・[レビュー](docs/SECTION_27_6_REVIEW_2026-09-28.md) |
| M16 | §27.7 Options on Two Correlated Assets（pp.658–661） | 受入。変数変換・Rubinstein の非矩形ツリー・確率の調整（Tables 27.2–27.3）を Stulz・Margrabe の式、1次元に帰着した米国型、前向き格子で照合。[受入ノート](docs/SECTION_27_7_ACCEPTANCE_2026-09-28.md)・[レビュー](docs/SECTION_27_7_REVIEW_2026-09-28.md) |
| M17 | §27.8 Monte Carlo Simulation and American Options（pp.660–665） | 受入。最小二乗法と行使境界のパラメータ化（Tables 27.4–27.7）を原典の8経路で再現し、推定と評価の分離による偏りを数値積分の厳密値と比較。P1 完了。[受入ノート](docs/SECTION_27_8_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_27_8_REVIEW_2026-09-28.md) |
| M18 | §26.1 Packages（pp.614–615） | 受入。レンジ先渡しのゼロコスト条件（§17.2 の K2=1.3414・p(1.30)=0.0273）、後払いとブレークフォワード、費用ゼロでも違うリスク（買う側）を独立参照（求積・二分法・モンテカルロ）で照合。P2 の初回。[受入ノート](docs/SECTION_26_1_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_26_1_REVIEW_2026-09-29.md) |
| M19 | §26.2 Perpetual American options（pp.615–616） | 受入。コール・プットの初回到達価値、行使境界、価値一致と滑らかな接続、$q=0$ のコール極限を独立参照と有限満期CRRで照合。P2 の2節目。[受入ノート](docs/SECTION_26_2_ACCEPTANCE_2026-09-29.md)・[レビュー](docs/SECTION_26_2_REVIEW_2026-09-29.md) |
| M20 | §26.3 Nonstandard American options（p.616） | 受入。行使可能日・ロックアウト・可変行使価格・7年ワラントの契約例を独立全経路計算とCRR後退帰納で照合。原典に印刷価格はなく、価格例は合成市場。P2 の3節目。[受入ノート](docs/SECTION_26_3_ACCEPTANCE_2026-09-30.md)・[レビュー](docs/SECTION_26_3_REVIEW_2026-09-30.md) |
| M21 | §26.4 Gap options（p.617） | 受入。符号付き給付・トリガーと決済額・バニラ＋現金バイナリ分解を独立求積で照合。Example26.1の3436・1896ドル、約45%減、保険会社支出と契約者手取りを分離。P2の4節目。[受入ノート](docs/SECTION_26_4_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_4_REVIEW_2026-10-01.md) |
| M22 | §26.5 Forward start options（p.618） | 受入。ATM欧州型の二時点契約・一次同次性・配当調整、期間固定/満期固定を独立求積36例とMC3例で照合。P2の5節目。[受入ノート](docs/SECTION_26_5_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_5_REVIEW_2026-10-01.md) |
| M23 | §26.6 Cliquet options（p.618） | 受入。単純ATM call/put列と各期支払を独立求積60例・多時点MC4例で照合、制約型はMC診断。P2の6節目。[受入ノート](docs/SECTION_26_6_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_6_REVIEW_2026-10-01.md) |
| M24 | §26.7 Compound options（pp.618–619） | 受入。欧州型4契約、臨界株価と内側put根なし領域、独立条件付き求積104例・MC4例。独立レビューI1修正・M1保留、全体検査PASS。P2の7節目。[受入ノート](docs/SECTION_26_7_ACCEPTANCE_2026-10-01.md)・[レビュー](docs/SECTION_26_7_REVIEW_2026-10-01.md) |
| M25 | §26.8 Chooser options（pp.619–620） | 受入。配当調整複製・選択/決済時点・端点、独立求積64例・MC4例・16表示状態。独立レビューI1修正・M1保留、全体検査PASS。P2完了。[受入ノート](docs/SECTION_26_8_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_26_8_REVIEW_2026-10-03.md) |
| M26 | §28.1 The Market Price of Risk（pp.671–674） | 受入。単因子signed係数・局所portfolio・印刷値・P→Q、独立12市場/6power/4MC・16表示状態・25D1。全suiteと独立最終レビューを完了。[受入ノート](docs/SECTION_28_1_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_28_1_REVIEW_2026-10-03.md) |
| M27 | §28.2 Several State Variables（pp.674–675） | 受入/main統合済み。[受入](docs/SECTION_28_2_ACCEPTANCE_2026-10-03.md)・[レビュー](docs/SECTION_28_2_REVIEW_2026-10-03.md) |
| M28 | §28.3 Martingales（pp.675–676） | 受入。条件付き定義/signed Itô/同一給付Q・G価格、9条件付きMC/旧235保持/16状態/27D1。[受入](docs/SECTION_28_3_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_3_REVIEW_2026-10-04.md) |
| M29 | §28.4 Alternative Choices for the Numeraire（pp.676–679） | 受入。HW Q状態/同一給付Q・T/支払・annuity、63独立fixture/旧246保持/16状態/28D1。[受入](docs/SECTION_28_4_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_4_REVIEW_2026-10-04.md) |
| M30 | §28.5 Extension to Several Factors（pp.679–680） | 受入/main統合push済み。MF01–06/11市場132状態/旧257/16状態/29D1。Important1を4回帰RED→GREENで修正、Minor2保留。[受入](docs/SECTION_28_5_ACCEPTANCE_2026-10-04.md)・[レビュー](docs/SECTION_28_5_REVIEW_2026-10-04.md) |
| M31 | §28.6 Black’s Model Revisited（pp.680–681） | Ch28まとめで正式受入・main統合済み。独立7市場42価格・zero-hit importance検証済み |
| 以降 | Ch29–34の未受入29節から未評価節へ展開 | ロジックは28節完了、§33.2は原典入力不足。正式受入を保留しP4の実装へ |

現在地（2026-10-05）：Ch28章末受入、台帳33/273、P3正式8/37。codex/p3-logicはロジック36/37、§33.2のflexicap strike/reset・payment日とsticky K0を保留。Ch28の全suiteは1回（4,436 PASS/6skip/3FAIL）、更新漏れ3件を修正して対象70 tests PASS。章check/台帳成果物/release/24表示状態/2D1/両保管庫PASS。受入はCh28で区切り、P4のCh10–13の計算26節を実装、次は§13.10（段数・DerivaGemの数値部分）。
各段階で、共有ソースを変えたときは既受入節の個別テストと両画面を再検査し、台帳の現行証跡へ接続している。

受入を通じて決まった進め方と、残している制限:

- §28.1のM1保留：MC検証図がゼロ始まりの価格棒のため、微小な推定差/95%区間を比較しにくい。数値は正しい。差分図/拡大パネルは将来対応。[レビュー](docs/SECTION_28_1_REVIEW_2026-10-03.md)。
- §26.8のM1保留：空batchと不正な有限市場条件の組でValueErrorにならず空配列を返す。価格の誤返却はない。[レビュー](docs/SECTION_26_8_REVIEW_2026-10-03.md)。

- 既存のhullkit実装や説明なしのコードセルは受入の根拠にしない。NumPy/SciPyだけの独立参照を先に作り、既存実装はその誤差を測ってから教材に載せる（M5・M8）。
- 早期行使プレミアムは閉形式ではなく、同じ格子で行使判定を外した価格と比べて測る。閉形式と比べると離散化誤差が混ざる（M6）。
- 再検査のスクリーンショット差分は、文字のアンチエイリアスやmodebarツールチップと図の中身の変化を分けて判定する。前者ならコミット済み画像を戻す（M6b）。
- 適用域の制限：§26.11の価格APIは$|r-q|<10^{-8}$に未対応（教材に適用域として明示）、§26.12のlookbackは$r=q$を欠測表示、putは原典外の独立拡張。
- M5は修正後の状態を第三者が確認していない受入である。
- 固定シードの1回の実行で偶然成り立つ統計的な主張は「この実行では」と書き、理論から導ける主張（新しい経路での評価は期待値で厳密値以下など）を別に検査する。同じ経路で評価した方策どうしはペア差で比べる（M17）。
- 不等号の向きは、単調性と境界の値から導いて検査する。§26.1 の独立レビューで、$c(K_2)=p(K_1)>p(F)=c(F)$（$c$ は行使価格の減少関数なので $K_2<F$ になる向き）が本文に残っていた。正しい式があり逆向きの式がないことを本文の検査にした（M18）。
- D1 driver は `--records-dir docs/validation/d1-recheck` を必ず付ける。既定の `docs/validation/d1-preflight` に書かれると記録の置き場所が変わるので、付け忘れたら移してやり直す（M18）。
- Book の html ハッシュは build の履歴に依存する。M17 のコミットを新しい worktree で作り直した Book は、M17 の記録が持つ `06_numerical.html`・`10_exotics.html` のハッシュと一致せず、`verify_section_ledger.py --check-artifacts` は M17 の時点でも新規 build では通らなかった。M18 は §27.1–§27.8 の `notebook_check` を現行の統合記録（`section-26-1/m18-check.json`）へ付け替えて通した（原因の特定は未了）。
- 節ごとの notebook 検査は受入時点の基点との比較として保持する。現行HEADでは `verify_accepted_vol06_notebook.py --check` が§27.1–§27.7の自節セルを各受入commitと比較し、共有図と巻全体を再実行する（§27.7 はM17で追加）。M17の§27.8は直前M16基点の節外保持検査を持つ。M18の§26.1は直前M17基点`811b1792`に対する vol10 の節外125セルの保持検査を持つ（vol10 は §4.8 の追加のみ）。後続節の追加時に現行HEAD用検査の対象を増やす（[レビュー F1 対応](docs/SECTION_27_3_27_4_FEEDBACK_2026-09-27.md)）。

- §28.4 Minor3保留：portal案内の状態不一致、δ≈1e−12年で金利の桁落ち、a*h=1e16でsampler X分散消失。通常教材fixtureへの影響なし。[レビュー](docs/SECTION_28_4_REVIEW_2026-10-04.md)。

- §28.5 Minor2保留：独立条件付き求積の自動判定接続、missing-RN変異の追加。現在の数値は正しい。Importantの再署名MCガードは4回帰RED→lesson20GREENで修正。[レビュー](docs/SECTION_28_5_REVIEW_2026-10-04.md)。
