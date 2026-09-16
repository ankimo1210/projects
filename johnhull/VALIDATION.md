# johnhull Beyond-Hull vol 18–28 — Final Validation

- Date: 2026-07-18 (A5–A8 / vol 18–25)、2026-07-20 (vol 26–27 review-fix run)、2026-09-02 (vol 27 Kupiec-flag recomputation)、2026-09-14 (vol 28 credit-desk run、section-audit fixes)、2026-09-15 (section-audit fourth run)
- Overall gate: **PASS**
- Model performance approved: **NO**
- Scope: integration, numerical identities, reproducibility, and offline delivery
- Data policy: fixed-seed synthetic references; no market-performance claim

`PASS` は vol 18–28 の教材・実装・成果物が再現可能で、定義した数値恒等式と
integration gate を満たすことだけを表す。実市場での予測力、収益性、較正品質、
または production readiness の承認ではない。

## Section 26.11 M3b — 2026-09-16

[受入ノート](docs/SECTION_26_11_ACCEPTANCE_2026-09-16.md)と
[統合記録](docs/validation/section-26-11/m3b-check.json)へ、L01–L06の教材・図・配布検査を集約する。
実装・全体pytest・Task 2独立レビューは完了。最終ブランチレビューも承認済み。

- 本文6小節、4給付・履歴・fixed/floating複製・観測頻度の共有4図をBook/portalへ接続。
- vol10は64セル。別の新規実行と出力型・MIMEキー・正規化テキストが一致（計時セルは型のみ）。保存した4図のdata/layoutは共有builderとも一致。lookbackより前とAsian以降のbuilder・notebook sourceは開始時点を保持。
- portalは12テーマ90図（exotics 10図）。Bookは31 notebookページのbuildに成功し、40警告を報告（Plotly MIME 34、既存の見出し順5、報告総数の未分類1）。PlotlyのHTML fallbackは実ブラウザで別途確認。
- Chromium 141でBook/portalの各面・各幅（1440/1000）で全11状態のレイアウトを検査。18枚のlookback画像を保存。各面で経路内部48点の極値を独立照合し、call/put両方で総額を保つlegの誤配分も拒否した。
- 影響範囲のpytestは**407 passed**（8.55秒：lookback 144、binary 92、barrier 171）。テスト専用oracleの相対importを修正し、project rootからの収集にも対応。
- §26.9・§26.10も今回のBook/portalで再検証。現行証跡は[barrier再検査](docs/validation/section-26-9/m3b-recheck.json)と[binary再検査](docs/validation/section-26-10/m3b-recheck.json)へ更新し、日付付きM2b/M3a記録は履歴として保持する。
- abs(r-q)<1e-8は既存価格APIで未対応のまま。L05では可除特異点と実装境界を説明し、新しい極限価格エンジンは今回の実装対象外とする。価格API・依存関係は変更していない。
- 全体pytestは**1,695 passed**（79.36秒、既存deprecation warning 2件）。台帳39テストと、成果物ハッシュを含む台帳CLI検査も成功。
- 台帳は受入済み3、不足あり0、未評価303。最終ブランチレビューも承認済み。未評価項目の完成を意味しない。portalは外部要求0、BookのMathJax CDN依存は残る。

以下は各実施時点の履歴。

## Section 26.11 M3a — 2026-09-15

[要求と残課題](docs/SECTION_26_11_REVIEW_2026-09-15.md)と
[統合記録](docs/validation/section-26-11/m3a-check.json)。L01–L06を抽出し、状態はgaps_found。
既存4価格関数を直接の極値尾部積分で検証し、教材・図・描画を未完了として区別した。

- 独立128価格（floating32、fixed96）、Example 26.2のcall/putの丸め値2件、恒等式を保つ価格誤差の検出2件：132テスト成功。
- 最大絶対誤差4.065e-12未満。8合成市場、新規/既発、fixedの3行使価格。微小なdeep OTM価格に相対精度は主張しない。
- abs(r-q)<1e-8は既存APIで未対応。0/±5e-9の12境界診断を記録し、極限の実装完了と区別する。
- 価格コード・notebook・portal/Bookソースと配布物は変更していない。既存2節の画面確認はM2b時点の証跡を保持し、今回の再描画検査と表現しない。
- 台帳の集計fixtureのみ2受入/1不足/303未評価へ更新し、台帳39テストを再実行。M2b記録にはこのメタデータ変更の追記を残した。
- 全体pytest：**1,681 passed**（74.32秒、既存deprecation warning 2件）。ruff・format・release契約・台帳両モードもPASS。独立レビューの結果は統合記録を参照。
- M3a時点の台帳：受入済み2、不足あり1、未評価303。

## Section 26.10 M2b — 2026-09-15

[受入ノート](docs/SECTION_26_10_ACCEPTANCE_2026-09-15.md)と
[統合記録](docs/validation/section-26-10/m2b-check.json)。D01–D06を受入済み。
本文6小節と共有4図、4価格の個別照合、call/put両複製、正規化spread/butterfly、正の残存期間のdeltaを確認した。

- §26.10：92テスト成功。新12件は境界・個別給付・図・独立積分価格の数値微分を含む。
- vol10：55セル。出力型・MIMEキー・正規化テキストが別実行と一致（計時セルは型のみ、画像・Plotly payloadの値は対象外）。図の値は別途semantic/browser検査。§3以降のbuilder・notebook sourceは開始コミットと完全一致。
- portal：12テーマ86図。Book：全31ページbuild成功、36警告を報告（新4図のPlotly MIME警告を含む）。
- Chromium：Book/portal各4図、幅1440/1000、両複製選択、各価格ラベル、52箇所の数式、文字の欠け・重なりを確認。数式/JSエラー0。
- portalは外部通信遮断下で外部要求0。BookはMathJax CDN依存を維持。
- §26.9：171テスト、両面各8契約、静的5図、数式93箇所を再検証。新m2b-recheckを現行の台帳へ結んだ。
- 独立レビューで図の注記・凡例・軸の重なりと、put側のN(-d1)の事象表記を修正。
- 全pytest：**1,549 passed**（76.84秒、既存deprecation warning 2件）。ruff、release契約、台帳両モードもPASS。
- 台帳：受入済み2、不足あり0、未評価304。最終統合レビューの結果は統合記録を参照。

以下は各実施時点の検証記録。

## Section 26.10 M2a — 2026-09-15

[要求と残課題](docs/SECTION_26_10_REVIEW_2026-09-15.md)。§26.10は`gaps_found`。
原典pp.622–623からD01–D06を整理し、cash/asset × call/putの価格を独立積分64ケースで確認した。
バニラ分解16ケースと合わせて80テスト成功。最大絶対誤差4.974×10⁻¹⁴。
合計を保つ誤配分など3つの改変を独立検査が拒否した。
[数値記録](docs/validation/section-26-10/numerical-check.json)。

全`pytest johnhull -q`：**1,535 passed**（69.27秒、既存deprecation warning 2件）。
台帳の両モード、119件の関連テスト、ruff、証跡の改変検出も成功。
[M2a統合検証記録](docs/validation/section-26-10/m2a-check.json)。

教材の誤説明の修正、4給付・プット分解の図、Book/portalの確認は残る。
価格コード・既存notebookは変更していない。受入済み1節、不足あり1節、未評価304項目。
M1と§26.9の試行は`ab825e03`としてmainへpush済み。以下は各実施時点の検証記録。

## Section ledger M1 — 2026-09-15

[節別台帳](docs/SECTION_LEDGER.md)と[更新手順](docs/SECTION_LEDGER_GUIDE.md)。
原典outlineから299節・7付録を登録。§26.9のB01–B09のみ受入済み、305項目は未評価。

- 台帳のID・状態・証拠・ソースの鮮度・生成Markdownを検査。
- `--check-artifacts`では保存記録にある配布HTML/JS/CSSの存在とハッシュも照合。
- ID欠落、証拠改変、不十分なaccepted、生成文書改変を失敗として検出。
- `pytest johnhull -q`：**1,455 passed**（71.86秒、既存deprecation warning 2件）。台帳の39テストを含む。
- ruff、通常CLI、`--check-artifacts`、実台帳への9種の改変プローブを確認。独立レビューで見つかった4点を修正し、再レビューで未解決指摘なし。
- 検証記録：[validation.json](docs/validation/section-ledger-m1/validation.json)。
- 数値価格・教材の画面は既存の§26.9証跡を再利用。M1で価格コードや配布画面は変更していない。
- 未コミット作業ツリー。全節の内容監査、M2、strict tracked release、push・公開は未実施。

## §26.9 section acceptance pilot — 2026-09-15

vol10 のバリア・オプションを、GE pp.620–622 の要求から再検証した。
[節別の受入表・数値結果・画面証跡](docs/SECTION_26_9_ACCEPTANCE_2026-09-15.md)。
開始コミットは `735197a66d9793e880961d6d9974dd40e941642f`、以下はその上の未コミット作業ツリーの結果。

- 教材：8種類と全分岐、経路上の payoff 分解、BGK、負のベガ、Parisian の連続/累積滞在。
- 再確認でBGKの厳密ゼロ境界の不具合を修正し、境界24ケースと図の独立価格検査2ケース（64点）を追加。
  誤った曲線への入力改変をPython・実ブラウザの両方が拒否。
- 独立積分48ケースの最大絶対誤差：1.7764×10⁻¹⁴（許容2×10⁻⁸）。
- 全 pytest：**1,378 passed**（44.04秒、既存 deprecation warning 2件）。関連部分171件、ruff PASS。
- vol10：45 cells、出力再生成と別の fresh run による出力比較 PASS。
- portal / Book build、通常 release contract：PASS。
- 実ブラウザ：Book / portal で各8種類の操作、Book の5図と数式93箇所、JSエラー0。
  カード幅変更時の図の見切れと、Book の重複 Thebe 宣言を修正した。
- portal は通信遮断下で動作。**Book の数式表示は MathJax CDN に依存**する。
  初回全ページビルドの32警告は、vol10の Plotly MIME 1件（HTML表現で動作確認済み）と他巻の MIME/見出し31件。今回の差分ビルドは vol10 の MIME 警告1件。
- この判定は§26.9の教材に限定する。全節・全ブラウザの完成判定ではない。
  全19コア notebook・全artifactの再構築と strict tracked check は今回再実行していない。
  コミット・push・公開は未実施。

## Gate matrix

| Gate | Evidence | Result |
|---|---|:---:|
| G0 | owner boundary、JSON+NPZ schema、split audit、torch-free `hullkit`、checkpoint/data policy | PASS |
| G1 / vol 18 | 8 hard checks、BS price/delta、pathwise MC uncertainty、CPU report | PASS |
| G2 / vol 19 | Heston/COS・SABR/Hagan・rBergomi teacher、multi-start two-step calibration、hard surface checks、actual variance refits | PASS |
| G3 / vol 20 | 1/5/21-day purged folds、train-only scaler/PCA、10-model ladder、regime/bootstrap diagnostics、common-path hedge | PASS |
| G4 / vol 21–22 | four-family SPX/VIX joint objective、teacher/Greek/OOD/timing、0DTE clock/event/expiry checks | PASS |
| G5 / vol 23 | RFR conventions、multi-curve/policy/collateral、Bachelier/SABR/MC ladder、Bartlett hedge | PASS |
| G6 / vol 24 | perpetual payoff/funding、margin/liquidation waterfall、oracle、CPMM/LVR identities | PASS |
| G7 / vol 25 | carbon model ladder、risk premia、OU/fOU weather basis、PPA CFaR/CVaR sensitivity | PASS |
| G8 | artifact/notebook/report/book/release integration and isolated full-workspace audit | PASS (tracked release) |
| vol 26 | Hull–White 1F curve fit、CPI lag/seasonality、ZCIS/YoY、JGBi tenth-day reference index、Jarrow–Yildirim measures、redemption-only deflation floor | PASS (tracked release) |
| vol 27 | Kupiec/Christoffersen/Basel backtests、FHS、EVT/GPD tail、Euler risk decomposition、P&L explain、cross-asset capstone | PASS (tracked release) |
| vol 28 | Hull Ch.24–25 credit desk: bond/CDS bootstraps, CDS legs/MTM/fixed coupon/options, quadrature CDO and kth-to-default, compound/base correlation, double-t/ASB, CreditMetrics, netting/collateral CVA | PASS (tracked release) |

vol 26–28 は G0–G8 とは別の Phase 計画（`docs/superpowers/plans/`）で実装した。gate の
内容と PASS の意味は同じで、各巻の notebook 上の gate ラベルは G8 / G9 / G10（vol 26 の
G8 は上の統合 gate G8 と番号が重なる）。

Canonical reference acceptance is recomputed by `johnhull/scripts/frontier_acceptance.py`;
it is not trusted as a copied JSON flag. Current contract (after the section-audit third
and fourth runs below): for all 11 volumes, the tamper suite
(`report/tests/test_frontier_acceptance_tamper.py`) checks that each selected alteration of
a committed array or metric fails the check that recomputes it, plus only the dependent
checks declared for that input (`DEPENDENT_FAILURES`). Where a check can be rebuilt from
the arrays, the stored scalar must also equal the rebuild. Checks without raw array or
run-time evidence still read a stored value and are listed separately (third run, below).
Degenerate inputs (zeros, a fit parameter at a pole) yield a failing record rather than
an exception. The tamper cases are selected alterations, not an exhaustive proof of
independence from every stored value.

| Volume | Acceptance checks | Integration | Performance approval |
|---:|---:|:---:|:---:|
| 18 | 8 | PASS | NO |
| 19 | 11 | PASS | NO |
| 20 | 12 | PASS | NO |
| 21 | 9 | PASS | NO |
| 22 | 7 | PASS | NO |
| 23 | 9 | PASS | NO |
| 24 | 10 | PASS | NO |
| 25 | 10 | PASS | NO |
| 26 | 11 | PASS | NO |
| 27 | 14 | PASS | NO |
| 28 | 17 | PASS | NO |

## Numerical evidence

- vol 18: normalized price MAE `5.593846268355811e-4`; delta MAE
  `1.7494819891811248e-3`; split overlap `0`; all 8 hard-check violations `0`.
  Price/delta/vega 20-seed CI coverage is `0.9/1.0/0.9`; the 4x-path standard-error
  ratios are `0.503652/0.500068/0.501859`.
- vol 19: all 4 SABR calibration starts succeed; repricing RMSE
  `5.2012449229271927e-11`; three distinct actual Heston variance refits; hard surface
  report passes all four applicable checks. A separate validation-only CPU benchmark
  measured median `1743.168745 ms` over 3 repeats after 1 warm-up (4 starts,
  74 objective evaluations); wall time is excluded from the byte-stable artifact.
- vol 20: horizons `1/5/21`, 3 folds each, 10 models each, and low/middle/high
  train-tercile regimes have QLIKE/RMSE/MAE block-bootstrap intervals. The stored
  default uses 512 common hedge paths and a common premium/cost convention.
- vol 21: all four SPX/VIX/VIX-option/variance objective components are finite;
  measured CPU timings are positive and preserved as a benchmark sample; the nested
  teacher has `0` futures-option bound and `0` scale-monotonicity violations, and
  the surrogate's counts are recomputed from the committed arrays.
- vol 22: calendar and adjacent-expiry violations are both `0`; the event/non-event
  sample is `7/6` with open/midday/close diagnostics; the jump variance injected
  for the FOMC event equals its scheduled `3.5e-4` (the earlier injection added
  `3.5e-4` expected jumps, about `1/80` of that variance); the 14:00 announcement
  intensity ramp enters only rows whose window still contains the event, so the
  non-event teacher/baseline RMSE is `0` by construction (it was `0.0225`, larger
  than the event RMSE, while the ramp leaked into post-event rows).
- vol 23: daily-compounding and zero-rate hand-check errors are `0`; quadrature
  hand-check error is `6.938893903907228e-18`; all four Hagan static checks pass at
  tolerance `1e-10` on each alpha slice of the 3 x 3 alpha-by-maturity grid, whose
  long-maturity and high-vol RMSEs (`21.4948 bp` / `19.4385 bp`) now come from
  different cells (the earlier zipped grid gave both `26.2144 bp`).
- vol 24: funding/cash-flow/solvency/insurance and both liquidation-method
  conservation identities pass within `1e-12`; stale and dislocated oracle states
  are explicitly represented.
- vol 25: Black-76/GBM/Heston/SV+jump prices and MC standard errors are aligned;
  fractional-OU lag-1 autocorrelation exceeds OU in the fixed fixture; weather basis
  and PPA risk sensitivities are finite.
- vol 26: Hull–White initial-curve and ZCIS repricing errors are `0.0`; annual
  seasonality normalization is `1.734723475976807e-18`; the Jarrow–Yildirim
  payment-forward and JGBi-floor analytic/MC comparisons peak at z-scores
  `1.4888912714624325` and `1.1974973083142517`; the floor payoff decomposition
  (floored = unfloored + face x max(1 - R, 0) on the final ratio `0.93346`) and the
  redemption-only principal check are exact, and raw vs floor-adjusted BEI differ by
  `2.785788824835045e-4`. The 5y linker + floor hedge (nominal zero bond and ZCIS,
  solved on nominal PV01 and CPI delta) is revalued: residual PV01/CPI delta `0`,
  real PV01 `-0.0451` -> `1.81e-7`, and scenario P&L shrinks to at most `66.6%` of
  unhedged (nominal +50bp, bond convexity). Earlier the hedge arrays were literal
  `[1, 1]` / `[0, 0]` and the decomposition error compared an expression with itself.
- vol 27: FHS constant-volatility identity, EVT VaR/ES identity, and Euler normal
  additivity are all `0.0`; simulated Euler ES additivity is
  `1.4210854715202004e-14`; marginal-VaR finite-difference agreement is
  `3.1713464233488086e-10`; GPD parameter recovery is `4.567805084324694e-2`; the
  clustered Christoffersen p-value is `1.6575957546647315e-3` and matches its
  recomputation to `1.5178830414797062e-18`; the delta-gamma-vega P&L residual
  `0.11443482486811263` is far below the delta-only residual `16.597194327066063`,
  leaving an unexplained share of `2.6301205095678685e-5`. The capstone book holds a
  short commodity sleeve correlated `0.55` with the long equity book, so its component
  VaR is negative (`-5.31`) and its limit utilization is below zero: a risk-reducing
  position consumes no limit. Limit measures are the *signed* component VaRs; taking
  their absolute value would let a diversifier breach its limit.
- vol 28: every printed Hull 11e number in the scope is reproduced from the committed
  arrays by numpy-only recomputation. CDS par spread `123.0026 bp` (Hull 123 bp) with
  mark-to-market `0.0111094` at 150 bp; bond-bootstrap hazards within `2e-4` of
  2.46/3.48/3.74 % (loss PVs within `0.002` of 1.50/3.53/5.61); fixed-coupon price
  `100.2706` (Hull 100.27); mezzanine tranche `347.574 bp` (Hull 348 bp) with A/B/C
  within `0.002` of 4.2846/0.0187/0.1496 and an independent numpy repricing agreeing to
  `1e-6 bp`; third-to-default `152.966 bp` (Hull 153 bp); compound/base correlations
  within `3.4e-4` of Table 25.8 and repricing the Table 25.6 quotes to `2.6e-14`; the
  0–X % expected-loss slope is strictly decreasing; the ν→∞ double-t spread is within
  `0.0062 bp` of the Gaussian spread; the ASB recursion matches the binomial pmf to
  `5.6e-16`; CreditMetrics thresholds are within `5.0e-5` of Hull's 1.2719/2.4089/2.8070
  and −3.7190/−3.0618/−1.7866 with the BBB default boundary 2.9290; Example 24.4
  collateral exposures are exactly 5/0/0/5 and the eq. 24.5 special-case CVA matches the
  general CVA to `1.5e-10`.

## Fresh validation record

Environment:

```text
Python 3.12.3
Linux 6.18.33.1-microsoft-standard-WSL2 x86_64
NumPy 2.4.6 / SciPy 1.17.1 / PyTorch 2.11.0+cu128
Pricing and release benchmarks: CPU
```

| Check | Command / evidence | Result |
|---|---|:---:|
| Deep pricing tests | `uv run --no-sync --package deep-hedge-price pytest -s -q deep_hedge_price/tests` — 88 passed | PASS |
| Notebook builder regression | `pytest .../test_pricing_report.py` — 3 passed | PASS |
| Phase-2 HTML export | direct artifact-only execute/export smoke; Notebook 02 and quick report both have 0 remote runtime dependencies | PASS |
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -s -q johnhull/hullkit/tests johnhull/report/tests` — 294 passed, 2 dependency deprecation warnings | PASS |
| Scoped lint/format | Ruff over deep pricing, hullkit, release scripts, portal, tests, and Notebook 02 | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–25 semantic match and second-build byte identity | PASS |
| Notebook execution | `make hull-notebooks-check` — vol 18–27 artifact-only execution | PASS |
| Portal | `make hull-report` — 11 themes / 70 figures; exact generated HTML set; no external URL | PASS |
| Jupyter Book | clean `make hull-book` — 28 pages | PASS with legacy warnings |
| Release contract | `make hull-release-check` | PASS |
| Full-workspace test | final one-shot: 1388 passed, 41 skipped, 6 isolated failures, 33 warnings | ACCEPTED WITH EXCEPTIONS |
| Tracked release | `make hull-release-check HULL_RELEASE_FLAGS=--require-tracked` | PASS |

The clean Book build completed with 29 pre-existing legacy warnings/errors located in
vol 13–17/legacy chapter 15 sources (header levels, old Plotly MIME outputs, and one
transition diagnostic). No warning originates in vol 18–27. The new pages use vendored
RequireJS and add no remote runtime asset. Legacy pages retain the explicitly allowlisted
MathJax CDN dependency; therefore the repository does not claim that every legacy page is
fully offline.

### Full-workspace exception isolation

The one required full-workspace run was executed last and was not repeated. Its six
failures do not invalidate the scoped release candidate:

| Project | Failures | Isolation |
|---|---:|---|
| `gto` | 4 | API tests reached `gto_py.equity` / `flop_dense_table_gb`, but the Rust extension is not built in this workspace environment. The same run skipped 29 other binding-dependent GTO tests for that reason. |
| `johnhull/hullkit` | 1 | The order-dependent test inspected global `sys.modules` after earlier projects had already imported PyTorch. The fresh-process hullkit/report run passed 294 tests, and the release verifier independently imports hullkit and asserts that this import does not pull in torch. |
| `rough_volatility` | 1 | Its notebook kernel inherited Windows TEMP under WSL; Jupyter rejected NTFS mode `0o677` instead of `0o600`. The failure is outside johnhull and occurs before notebook code execution. |

There were no functional failures in the scoped `deep_hedge_price`, `hullkit`, portal,
artifact, or vol 18–25 notebook gates. These exceptions are recorded rather than hidden
or used to claim a green workspace-wide suite.

## 2026-07-20 review-fix run (vol 26/27 input contracts and cross-asset capstone)

Scope: the eight defects listed in
`docs/superpowers/plans/2026-07-20-johnhull-vol27-review-fixes.md`. Every one was
reproduced before the fix and re-run after it. The common shape of the set was a
SILENT failure in the passing direction — bad input produced a plausible number
rather than an error — so each fix turns a quietly wrong number into a raise.

| Check | Command / evidence | Result |
|---|---|:---:|
| Boundary-value regressions | `pytest johnhull/hullkit/tests/test_var_backtest.py test_tail_risk.py test_bsm.py` — 102 passed (40 + 43 + 19), 25 of them new | PASS |
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -q --confcutdir=johnhull johnhull/hullkit/tests johnhull/report/tests` — 784 passed | PASS |
| Deep pricing tests | `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests` — 206 passed | PASS |
| vol 27 acceptance | `frontier_acceptance.evaluate_acceptance(27, ...)` — 14/14 PASS (was 11; added `christoffersen_pvalue_matches_recomputation`, `cross_asset_factor_mapping`, and `kupiec_size_flags_match_recomputation`) | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–27 semantic match and second-build byte identity | PASS |
| Notebook execution | `make hull-notebooks-check` — vol 18–27 artifact-only execution | PASS |
| Portal | `make hull-report` — 12 themes / 78 figures | PASS |
| Jupyter Book | `make hull-book` — 30 pages | PASS with legacy warnings |
| Release contract | `make hull-release-check` | PASS |
| Scoped lint | Ruff over hullkit src/tests, release scripts, portal builder and tests | PASS |

Artifacts regenerated as intentional schema changes: vol 27 (nine new capstone arrays
for the position x factor mapping, plus the acceptance record embedded in
`metrics.json`) and vol 21 (its benchmark contract embeds the SHA-256 of
`frontier_reference.py`, which this run edited).

Two findings from this run are worth carrying forward:

- Routing every `bsm.call_price`/`put_price` call through a broadcast element-wise
  path — rather than only the mixed-boundary calls — shifted vol 19's calibrated
  parameters by ~1e-7 and broke artifact reproducibility. `np.exp`/`np.log` round
  differently in their SIMD and scalar paths, and a downstream optimizer amplifies
  the last ulp. Uniform inputs therefore keep the original whole-array expressions.
- `christoffersen_detects_clustering` had been reading its p-value out of the
  committed JSON, so a single edited number could flip the gate. It now recomputes
  from the exceedance arrays via `erfc(sqrt(LR/2))`, which equals `chi2.sf(LR, 1)`
  exactly and needs no scipy inside the gate.

The scope of PASS is unchanged: integration, numerical identity and reproducibility on
synthetic data. Nothing here approves model performance or market predictive power.

## 2026-09-14 vol 28 credit-desk run

Branch `worktree-johnhull-vol28-credit-desk`; design
`docs/superpowers/specs/2026-09-14-johnhull-vol28-credit-desk-design.md`, plan
`docs/superpowers/plans/2026-09-14-johnhull-vol28-credit-desk.md`. Environment:
Python 3.12.3 / NumPy 2.4.6 / SciPy 1.17.1 on Linux 6.18.33.2-microsoft-standard-WSL2
(CPU only; `hullkit` stays torch-free).

| Check | Command / evidence | Result |
|---|---|:---:|
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests` — 901 passed, 2 dependency deprecation warnings (was 832; +54 hullkit credit tests, +3 vol 28 reference tests, +1 acceptance independence test, report suite 15) | PASS |
| Scoped lint/format | `ruff check` / `ruff format --check` over `johnhull/hullkit/src`, `johnhull/hullkit/tests`, `johnhull/scripts`, `johnhull/report/report_builder`, `johnhull/report/tests` — all checks passed, 159 files formatted | PASS |
| vol 28 acceptance | `frontier_acceptance.evaluate_acceptance(28, ...)` — 17/17 PASS, recomputed from the committed arrays with numpy-only helpers (independent Gauss–Hermite tranche pricer, ASB recursion, bisection normal quantile); tampering tests confirm the stored CDO metric and compound correlations are not trusted | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–28 semantic match and second-build byte identity; vol 21 `benchmark.sources` digest refreshed for the edited `frontier_reference.py` (one-line change, same practice as `0b3fa109`) | PASS |
| Notebook execution | `make hull-notebooks-check` — vol 18–28 artifact-only execution, 46 cells and 0 errors in `credit_desk.ipynb` | PASS |
| Portal | `make hull-report` — 12 themes / 82 figures (`risk_credit` 8 → 12); no external URL | PASS |
| Jupyter Book | clean `make hull-book` — 31 notebook pages, build succeeded with 29 pre-existing legacy warnings (vol 13–17 / legacy ch15), 0 originating in `28_credit_desk` | PASS with legacy warnings |
| Release contract | `make hull-release-check` — `[PASS] johnhull A5--A8 release contract` with volumes 18..28 | PASS |
| Untouched core | `git diff --stat main -- johnhull/hullkit/src/hullkit/credit.py johnhull/hullkit/src/hullkit/copula.py johnhull/volumes/09_credit_xva` — empty | PASS |
| Tracked release | `make hull-release-check HULL_RELEASE_FLAGS=--require-tracked` after the evidence commit | PASS |

The vol 28 data policy remains `synthetic-offline`: the only external numbers are the
Hull-printed Table 24.4 transition matrix and Table 25.6 iTraxx quotes, transcribed as
fixtures and used solely as textbook pins (`docs/DATA_PROVENANCE.md`).

## 2026-09-14 section-audit follow-up run (acceptance recomputation, printed-value pins, documentation)

Branch `worktree-johnhull-audit-next` (base `bd278948`), following
`docs/SECTION_AUDIT_2026-09-14.md` §9 steps 3–5 plus the small items R5 / R9 / R10.
Environment: Python 3.12.3 / NumPy 2.4.6 / SciPy 1.17.1 on Linux
6.18.33.2-microsoft-standard-WSL2 (CPU only; `hullkit` stays torch-free).

| Check | Command / evidence | Result |
|---|---|:---:|
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests` — 1055 passed (was 917; +71 printed-value pins in `test_hull_pins_*.py`, +66 acceptance tamper cases, +1 vol 22 / mean-excess tests) | PASS |
| Scoped lint/format | `ruff check` / `ruff format --check` over `johnhull/hullkit`, `johnhull/scripts`, `johnhull/report` — all checks passed, 165 files formatted | PASS |
| Acceptance tamper contract | `report/tests/test_frontier_acceptance_tamper.py` — vol 23 (7 cases), 24 (11), 25 (10), 27 (14), 28 (17): each tampered array/metric flips exactly the check that recomputes it (documented dependent checks aside); committed artifacts still pass every check | PASS |
| vol 27 / 28 recomputation | Kupiec exact size 0.0709 at n=500 (z = 1.63, was compared with the nominal 5%); FHS/HS forecasts rebuilt from `garch_returns` / `conditional_sigma`; GPD MLE local-optimum check; EVT VaR and Euler VaR rebuilt from the fit and z_alpha; book exposures == weights @ mapping; vol 28 CDS/CDO/CVA checks rebuilt from hazards, recovery, rate and copula rather than stored PVs. Observed values unchanged except float noise | PASS |
| vol 22 event ramp | 14:00 announcement ramp scoped to event rows; non-event teacher/baseline RMSE 0 by construction (was 0.0225); `mean_excess` rejects NaN / 2-D input | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–28 semantic match and second-build byte identity; vol 21 digest refreshed for each `frontier_reference.py` edit (timings preserved) | PASS |
| Notebook execution | `make hull-notebooks-check` (vol 18–28) and `make hull-core-notebooks-check` (19 core notebooks; vol 01/02/05–12 regenerated from their builders, vol 16/17 markdown patched in place with outputs kept) | PASS |
| Portal / Book | `make hull-report` (12 themes / 82 figures); `make hull-book` (31 pages, build succeeded with the 29 pre-existing legacy warnings) | PASS |
| Release contract | `make hull-release-check` and `verify_release.py --require-tracked` — `[PASS] johnhull A5--A8 release contract` | PASS |

Printed-value pins that disagree with the Global Edition print are pinned at the
computed value and documented in the test docstrings (Table 20.3 K=56 49.0 → 49.9; MSFT
10-day ES 1,687,000 → 1,685,629, reproducible from the rounded Y; p.521 cumulative weight
0.004833 → 0.003776; Table 22.8 variance from rounded covariances at rel 2e-4). No hullkit
source semantics changed in this run apart from the vol 22 ramp scoping and the
`mean_excess` input validation.

Still open after this run (`docs/SECTION_AUDIT_2026-09-14.md` §11): vol 18–22 and 26
acceptance still mix array checks with stored-value comparisons; D9 (core notebooks without
outputs) is a pending decision; §4 items other than the 13 pinned here remain as listed.
(The acceptance recomputation and D9 were addressed by the third run below.)

## 2026-09-14 section-audit third run (vol 18–22/26 gates, Hull §4 APIs, static book outputs)

Branch `worktree-johnhull-audit-third` (base `8485cc29`), following
`docs/SECTION_AUDIT_2026-09-14.md` §11.2. Same environment as the previous run; vol 18's
reference is re-exported from the local checkpoint `2d4ba8e38acfa5cc` (torch, CPU).

| Check | Command / evidence | Result |
|---|---|:---:|
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests` — 1252 passed (was 1055) | PASS |
| deep_hedge_price tests | `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests` — 206 passed | PASS |
| Scoped lint/format | `ruff check johnhull deep_hedge_price/scripts`; `ruff format --check` over `johnhull/hullkit`, `johnhull/scripts`, `johnhull/report`, `deep_hedge_price/scripts` | PASS |
| Acceptance tamper contract | all 11 volumes: 18 (8 cases), 19 (9), 20 (7), 21 (6), 22 (7), 23 (7), 24 (11), 25 (14), 26 (6), 27 (14), 28 (17); each case fails its recomputing check plus only the declared dependent checks; a stored scalar that can be rebuilt from the NPZ must equal the rebuild (the stored-value exceptions are listed under this table) | PASS |
| vol 18 re-export | `export_johnhull_pricing_reference.py` adds per-row test/OOD errors, split row digests and the teacher intervals/standard errors; the evaluation MAEs reproduce to rel 1e-12 and two exports are byte-identical. OOD shell (outside the gate): price MAE 1.606, median 0.00103, worst 261.9 (σ = 1e-4 rows below the 0.05 training floor), 20.9% of rows above 0.01 | PASS |
| vol 25 correlation sensitivity | ρ ∈ −0.9..0.6 on common random numbers: merchant revenue within 3 SE of N·P·g·(1 + ρσ_Sσ_G) (max z 1.79); pay-as-produced fair value 29.48 → −23.85; hedged CVaR spread 76.2–86.3 is sampling noise (hedged cash flow = K·generation) | PASS |
| Reference rebuild | `make hull-artifacts-check` — vol 19–28 semantic match and second-build byte identity | PASS |
| Notebook execution | `make hull-notebooks-check` (vol 18–28); `make hull-core-notebooks-check` (19 notebooks; the 17 output notebooks are executed with `HULLKIT_STATIC_FIGURES=1` / `PLOTLY_RENDERER=plotly_mimetype+notebook` and their output types compared with the committed copies; this run compared types only, text values were added in the fourth run) | PASS |
| Static book outputs (D9) | `verify_core_notebooks.py --write-outputs` — vol 01–12 and ir_models carry ipympl figures as PNG (86 figures), vol 13–16 and ir_models embed plotly.js; Plotly's hard-coded MathJax 2 CDN script is stripped (no figure uses LaTeX; the book stays offline); outputs are byte-stable across runs except vol 06's measured LSM time; notebooks total 35.7 MB (vol 13–16 ≈ 23 MB, ir_models 7.1 MB) | PASS |
| Portal / Book | `make hull-report` (12 themes / 82 figures); `make hull-book` (build succeeded) | PASS |
| Release contract | `make hull-release-check` and `verify_release.py --require-tracked` | PASS |

Checks that still read a stored value because no array evidence exists: vol 18
`residual_baseline` (Heston residual MAEs from the evaluation run) and `hard_violation_rate`;
vol 19 `multi_start_calibration` (optimizer success flags); vol 21 timing method flags;
vol 22 `calendar_violations` (holiday/session booleans); vol 26
`principal_floor_redemption_only`, `coupon_floor_max_error` and `measure_treatment`.

## 2026-09-15 section-audit fourth run (progress review F1–F5)

Branch `worktree-johnhull-astra-feedback` (base `06266ae3`), answering the progress review
`docs/SECTION_AUDIT_2026-09-14_FEEDBACK.md` (written against `83905890`); the change table is
`docs/SECTION_AUDIT_2026-09-14.md` §11.3 and the per-ID status is §12. Same machine as the
previous runs (Intel Core Ultra 9 285K, WSL2, Python 3.12.3).

| Check | Command / evidence | Result |
|---|---|:---:|
| hullkit + portal tests | `uv run --no-sync --package hullkit pytest -q johnhull/hullkit/tests johnhull/report/tests` — 1286 passed (was 1252) | PASS |
| deep_hedge_price tests | `uv run --no-sync --package deep-hedge-price pytest -q deep_hedge_price/tests` — 206 passed | PASS |
| Scoped lint/format | `ruff check johnhull deep_hedge_price/scripts`; `ruff format --check` over `johnhull/hullkit`, `johnhull/scripts`, `johnhull/report`, `deep_hedge_price/scripts` | PASS |
| Degenerate acceptance inputs (F5) | zeroing every numeric array and metric of vol 18–28 one at a time: 18 inputs used to raise (vol 27 `gpd_losses` and `gpd_xi_hat`, 16 more in vol 23/27/28); all now return a failing record (`gate_evaluation`, or the GPD/EVT checks for no exceedance / an invalid fit). Committed references evaluate unchanged: 118 checks, all PASS | PASS |
| Core output text (F4) | `make hull-core-notebooks-check` compares stream text and `text/plain` / `text/markdown` / `text/latex` values with the committed copies (addresses, kernel cell files, site-packages and repository paths masked; wall-clock cells by type). A committed `print(1)` output against a fresh `2` is now reported as StaleOutputs. 19 notebooks clean; ir_models' outputs rewritten after its `r₀` / `F₀` labels moved to mathtext | PASS |
| vol 21 timing provenance (F3) | `benchmark.measurement` records the generator digests and environment of the measuring run; re-measured with `--refresh-timing` (speedup at batch 1024 786.95, was 781.91); an ordinary rebuild preserves the sample byte-identically; `make hull-artifacts-check` prints `[NOTE] vol 21: timing sample measured on the current generator` | PASS |
| Frontier notebook figures | vol 18–28 notebooks rebuilt with `japanize_matplotlib`; 233 missing-glyph warnings (Japanese labels drawn as boxes, with past worktree paths in the warning text) removed; no committed notebook carries a glyph warning or a `/home/` path | PASS |
| Reference rebuild / notebook freshness | `make hull-artifacts-check` (vol 19–28 semantic match, second-build byte identity); `make hull-notebooks-check` (stdout / `text/plain` of vol 18–28 against fresh runs, VALIDATION.md regeneration) | PASS |
| Portal / Book | `make hull-report` (82 figures); `make hull-book` (build succeeded) | PASS |
| Release contract | `make hull-release-check` and `verify_release.py --require-tracked` | PASS |

Still open: the stored-value checks listed under the third run (no raw evidence);
the section ledger (all 306 sections have not been reclassified since the audit); the core
gate does not compare PNG or Plotly payloads, and the frontier gate still ignores stderr and
figures (the new hygiene test covers only glyph warnings and local paths).

## Negative results and residual model risk

- vol 18: the quick soft penalty did not reduce the hard-check count, and no neural
  CPU break-even batch was observed.
- vol 19: the soft-constrained stress surface remains hard-arbitrage violating; the
  hard repair is a feasible cumulative projection rather than a joint-L2 optimum;
  rBergomi uses only a small antithetic MC sample.
- vol 20: PCA-ridge QLIKE `0.522245` does not beat EWMA `0.457612` at the compatibility
  5-day view. Real Phase-1 checkpoint positions were not supplied, so the policy status
  is correctly `not_evaluated`. Attention/permutation/occlusion/IG are non-causal
  diagnostics, and all forecast data are synthetic.
- vol 21: polynomial-surrogate delta RMSE is `5.04308` and gamma RMSE `35.5073`
  (the pooled `25.3594` was a gamma-only number: the teacher's bump gamma is ~0);
  the surrogate breaks the futures-option price bounds on `18/24` evaluation rows
  and scale monotonicity on `32` grid steps; the manufactured target has SPX RMSE
  `0.0364061` and VIX RMSE `4.13935`. This is not a Greek-performance pass.
- vol 22: the intraday teacher and event schedule are synthetic, not causal dealer-flow
  evidence. The disabled research tracks are those in `research_profiles.json`
  (VAE/flow/SBI, foundation zero-shot/diffusion, signature/optimal transport, DML/PIDE,
  storage real option).
- vol 23: Hagan worst quick-grid error is `65.7763 bp`; the free-boundary fixture is an
  explicit shift boundary, not an endogenous boundary solve; MC SE omits time-step bias.
- vol 24: the cascade is synthetic, not an event reconstruction. Dynamic fees do not
  reduce gross LVR in this fixture; fee compensation is reported separately.
- vol 25: weather and PPA values depend on the selected premium principle because the
  market is incomplete. Real-market calibration, out-of-sample tests, and storage real
  options remain outside the core gate.
- vol 26: all curves, CPI fixings, option quotes, and hedge ratios are synthetic rather
  than market calibrated. The v1 model uses deterministic seasonality and one-factor
  nominal/real Gaussian rates; production ISDA disruption fallbacks and live JGBi
  settlement operations are out of scope.
- vol 27: all P&L, exceedance, and tail samples are synthetic fixed-seed draws. FHS uses
  the committed EWMA conditional-volatility path with no live calibration, and its
  default rescaling target is the last observed conditional volatility rather than a
  post-shock next-day forecast. The Basel multiplier schedule is the documented 250-day
  BCBS table, not a re-derivation. Cross-gamma, vanna, and vomma P&L-explain terms are
  out of scope.
- vol 28: Hull Table 24.4 (S&P 1981–2019) and Table 25.6 (Creditex iTraxx quotes,
  2007-01-31) are transcribed textbook constants, not downloaded market data; no
  calibration to live quotes is claimed. The Table 25.8 implied correlations agree with
  Hull to one decimal place, and the residual reflects DerivaGem's integration grid rather
  than calibration quality. The double-t copula and the heterogeneous ASB recursion are
  validated only by limits (ν→∞, homogeneous pool) because Hull prints no §25.11 numeric
  example. Random recovery / random factor loadings, the implied copula, dynamic models,
  and KMV EDF mappings have no code; the vol 28 notebook section 「本巻で実装しない節」
  summarizes Hull's description of each. CDS options use the Black-type formula on the
  survival-weighted forward risky duration (pre-expiry default knocks the option out);
  the spread volatility is an input assumption, the lognormal-spread assumption is not
  tested, and no non-knock-out variant exists (Hull defers these to Hull and White 2003).
  Example 24.8 (worst-case default rate `0.128`, credit VaR `$5.13M`) is pinned in
  `test_credit.py`. Only the CreditMetrics block draws random numbers (seed `20260746`).

Foundation models, diffusion/VAE/flow/SBI, signature/POT, and other cited frontier work
remain optional research tracks. Preprints are identified as such in the design/spec and
cannot fail or silently substitute for the core reference implementation.

## Release decision

The implementation and integration evidence are complete, with the workspace-wide
exceptions isolated above. After explicit authorization, the release files were committed
and the strict tracked-file release check passed.

| Release | Branch | Landed on `main` |
|---|---|---|
| vol 18–25 (G8) | `codex/johnhull-beyond-hull-g8` | merge `c4cfa7e4` |
| vol 26 inflation/JGBi + vol 27 risk desk | `codex/johnhull-inflation-jgbi` | merge `66e5f355`（portal/book 収録は `691877f`・`63f83ce`） |
| vol 27 review fixes | `codex/johnhull-vol27-review-fixes` | merge `eaa5a9a9` |

The release branches other than `codex/johnhull-inflation-jgbi` have been deleted after
merging, so `main` — not the branch refs — is the reproducible record.

`PASS` denotes the tracked integration and reproducibility release; it does not approve
model performance or production readiness.
