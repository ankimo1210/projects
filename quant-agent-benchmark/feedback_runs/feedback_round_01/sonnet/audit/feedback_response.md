# Feedback response — feedback_round_01 / sonnet

Full experiment log: `experiments.csv`. Full protocol and decision criteria
fixed before running anything: `protocol.md`. This document answers the
sonnet-specific feedback item and the common feedback themes point by
point, each as SUPPORTED / NOT SUPPORTED / PARTIALLY SUPPORTED /
UNVERIFIED, with the evidence and, where a change was made, exactly what
changed and why.

## Sonnet-specific item, addressed clause by clause

> 初回は短期ゼロ金利とフォワードの誤差が目立った。処理完了・テスト合格とは別の問題である。

**PARTIALLY SUPPORTED.** Split into two separate claims and tested
separately (see H1/H6 below) because they turned out to have different
answers. Confirms the premise that test-pass/completion says nothing about
this — no test in the phase-1 suite checked forward-curve smoothness or
maturity-band-specific residuals; both required new, dedicated analysis.

> 基準モデルの区分線形ゼロ金利と解析的フォワードについて、節点・端点・格子上の差分との関係を確認する。

**Done — H2, `exp_F_forward_consistency.py`.** The analytic forward
`f(t)=z(t)+t·z'(t)` matches a central finite difference exactly inside any
linear segment for any step size, and shows a *fixed* (not
step-size-shrinking) discrepancy only when the finite-difference stencil
straddles a knot — this is the expected behaviour of evaluating a
derivative near a genuine kink in a C0 (not C1) curve, not a bug. **NOT A
BUG**, but it does mean forward rates are unreliable right at and near
knots, which matters more in a noisy region (see H6).

> 預金をすべて学習に残す設計、OISの検証候補を局所的な滑らかさで選別する設計が、難しい箇所の検証を欠いていないか調べる。

**CONFIRMED — H3.** `T<=2y` has **zero holdout coverage** across every
instrument type on the supplied dataset (0/19 deposits, 0/16 swaps, 0/2
bonds — all in training). `T>=15y` OIS also has zero coverage (0/13), a
gap not in the original hypothesis text but found by the same analysis.
The reported holdout RMSE is real but only certifies the bands/types that
are actually held out; it says nothing about the short end or the long OIS
end. Documented in `MODEL_RISKS.md` (Validation gaps). **Not
redesigned this round** — changing which points are holdout-eligible would
change the model-selection inputs and requires re-validating the selection
outcome, which the remaining time budget did not allow doing safely.

> 基準モデルが内部検証で勝ったことと、未知の真値に近いことは別である。高度モデルとの人工データ比較...

**SUPPORTED, with nuance — H4/H6.** On 3 synthetic curves with known
truth: flat and monotone-upward are recovered ~exactly by both models
(baseline marginally better, expected since those truths are literally
piecewise-linear/near-linear); on a **humped** truth, advanced is closer
(0.076bp vs 0.665bp overall zero-rate RMSE). Separately, on the *real*
dataset, the baseline's forward curve has an **811.9bp jump at the 1.25y
knot** (mean 154.0bp across all knots) versus **0.037bp max / 0.008bp
mean** for advanced — a real, large difference in forward-curve quality
that the holdout-RMSE-based selection (which picked baseline) does not
see. This is real, converging evidence that holdout-RMSE-only selection
can miss forward-curve quality — but a 3-shape synthetic test with no
walk-forward and no hidden-truth check is **not, by itself, conclusive
enough to override the existing empirical selection rule**. Per the
adoption rule, model selection was **left unchanged** (baseline remains
selected); the finding is reported as an explicit, quantified,
actionable-for-a-future-round item rather than acted on by force.

> ...商品別重み、中程度の異常値・鮮度の処理を点検する。

**UNVERIFIED this round.** Per-type weighting and moderate-outlier/staleness
handling were reviewed by reading `cleaning.py`/`calibration.py` again but
no new experiment was run against them specifically — time was prioritised
on the pricing-convention (H5) and forward-smoothness (H6) lines, which
produced the largest, most concrete findings. Not claiming these are fine;
just not re-verified in this round.

## Common feedback themes

- **Completion/tests are not sufficient evidence of quality:** agreed and
  acted on — every finding above required a new, independent check; none
  came from the existing 49/49-passing test suite.
- **Payment-convention / benchmark-generation inconsistency (H5):** a real
  **documentation bug** was found and fixed — `MODEL_RISKS.md` previously
  described the bond stub as "counted backward from maturity" (front-stub)
  while the code (verified via independent, non-circular reference pricers
  in `exp_B_pricing_diagnostics.py`) actually generates a forward/end-stub
  schedule, identical to swaps. The prose was corrected to match the code.
  Separately, whether *this* convention or the backward-from-maturity
  alternative is what actually generated the (possibly hidden) benchmark
  data is **undecidable from this side of the fence**: a symmetric A/B test
  (`exp_E_bond_convention_fix_check.py`) shows either mismatch direction
  produces the same ~1.1-1.4bp zero-rate RMSE bias on synthetic ground
  truth. The convention was **not changed**, per the protocol's explicit
  rule against inferring "correctness" from how well a convention fits real
  data; the sensitivity is instead quantified and documented as an
  assumption risk.
- **Forward-error amplification from slope (H6):** confirmed both
  theoretically (correlation 0.82 between |local slope| and |forward −
  zero| across all real knots) and operationally (a new
  `forward_smoothness_check` diagnostic, shipped in `submission/`, shows
  baseline vs. advanced differ by ~20,000x at the worst knot). This is now
  a permanent, reported metric distinct from zero-rate repricing RMSE.
- **Baseline-or-advanced adoption alone is not success:** selection was
  left as baseline (unchanged from phase 1) — this round adds evidence and
  a new diagnostic, not a forced model switch.

## What actually changed in `submission/` vs. the phase-1 baseline

1. `src/quantcurve/diagnostics.py` — new `forward_smoothness_check()`
   (additive function).
2. `src/quantcurve/cli.py` — wires the new check into
   `diagnostics/sensitivity.json` as a 5th top-level key.
3. `src/quantcurve/report.py` — one new panel in report §5 reporting the
   real-data numbers.
4. `src/quantcurve/diagnostics.py::model_comparison_payload` — added a
   `selected_model` key (duplicate of the existing `model_selected`) so
   both the original CLI-contract test and this round's schema wording are
   satisfied; nothing removed.
5. `tests/test_diagnostics.py` — new (4 tests) for the new function.
6. `MODEL_RISKS.md` — corrected the bond-stub documentation bug, and added
   two new, quantified "feedback round 01" limitation entries (schedule-
   convention sensitivity; holdout-coverage gap + forward-smoothness gap).
7. Nothing else. `curve.csv`, `repricing.csv`, `risk.csv`, `cleaning.csv`,
   and `model_comparison.json`'s numerical content are **byte-identical**
   to a fresh phase-1 baseline reproduction (verified by diff, see
   `audit/logs/`) — the fitted curve, model selection, and every other
   numerical output are unchanged. Full test suite: 53/53 passing (49
   original + 4 new). Full CLI: exit 0, same "model selected = baseline".
