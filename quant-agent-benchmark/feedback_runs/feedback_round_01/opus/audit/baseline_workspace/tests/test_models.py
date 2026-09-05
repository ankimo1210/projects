from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from quantcurve.cleaning import clean
from quantcurve.io import load_market_data_with_audit
from quantcurve.models import (
    FitConfig,
    consensus_pillars,
    fit_advanced,
    fit_baseline,
    fit_metrics,
    local_residuals,
    residuals_bp,
    screen_outliers,
    select_knots,
)
from quantcurve.validation import validate
from synthetic import (
    VALUATION_DATE,
    NelsonSiegel,
    clean_frame,
    dirty_frame,
    negative_rate_frame,
    write_frame,
)

FAST = FitConfig(lambda_grid=(1.0e-5, 1.0e-3), penalty_power_grid=(1.0,), cv_folds=3)


def instruments_from(frame, tmp):
    path = write_frame(frame, Path(tmp) / "market.csv")
    loaded = load_market_data_with_audit(path)
    report = validate(loaded, VALUATION_DATE)
    return clean(loaded, report, VALUATION_DATE).instruments


class TestKnotSelection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_knots_are_sorted_positive_and_bounded_by_the_data(self) -> None:
        knots = select_knots(self.instruments, FAST)
        maturities = [i.maturity_years for i in self.instruments]
        self.assertTrue(np.all(np.diff(knots) > 0))
        self.assertGreater(knots[0], 0.0)
        self.assertAlmostEqual(float(knots[0]), min(maturities), places=9)
        self.assertAlmostEqual(float(knots[-1]), max(maturities), places=9)

    def test_front_end_receives_knots(self) -> None:
        # Log-uniform placement must not starve the money-market end, which is
        # where the curve is steepest and where a maturity-quantile rule fails:
        # only 5 of 20 instruments mature inside a year, so quantile knots would
        # put a single knot there.
        knots = select_knots(self.instruments, FAST)
        self.assertGreaterEqual(int(np.sum(knots <= 1.0)), 2)
        generous = select_knots(self.instruments, FitConfig(observations_per_knot=1.0))
        self.assertGreaterEqual(int(np.sum(generous <= 1.0)), 4)
        self.assertGreater(
            float(np.sum(generous <= 1.0)) / generous.size,
            5.0 / len(self.instruments),
        )

    def test_knot_count_is_capped(self) -> None:
        config = FitConfig(max_knots=6)
        self.assertLessEqual(select_knots(self.instruments, config).size, 8)

    def test_two_instruments_give_two_knots(self) -> None:
        knots = select_knots(self.instruments[:2], FAST)
        self.assertEqual(knots.size, 2)


class TestBaselineBootstrap(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)
        self.fit = fit_baseline(self.instruments, FAST)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_every_pillar_is_repriced_exactly(self) -> None:
        residual = residuals_bp(self.fit.curve, self.instruments)
        self.assertLess(float(np.max(np.abs(residual))), 0.02)

    def test_no_pillar_is_skipped_on_clean_data(self) -> None:
        self.assertEqual(self.fit.skipped, [])

    def test_recovers_the_generating_curve(self) -> None:
        # Piecewise-constant forwards interpolate crudely across the 20Y-30Y gap,
        # so the bootstrap's recovery bound is deliberately looser than the
        # spline's; TestAdvancedFit pins the comparison.
        truth = NelsonSiegel()
        grid = np.linspace(0.2, 29.0, 200)
        error_bp = np.abs(self.fit.curve.zero(grid) - truth.zero(grid)) * 1e4
        self.assertLess(float(np.max(error_bp)), 8.0)

    def test_discount_factors_are_positive(self) -> None:
        grid = np.linspace(0.01, 40.0, 400)
        self.assertTrue(np.all(self.fit.curve.discount(grid) > 0.0))

    def test_consensus_merges_near_coincident_pillars(self) -> None:
        pillars = consensus_pillars(self.instruments, FitConfig(min_pillar_gap_years=5.0))
        maturities = [p.maturity_years for p in pillars]
        self.assertTrue(all(b - a >= 5.0 for a, b in zip(maturities, maturities[1:])))


class TestAdvancedFit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_recovers_the_generating_curve(self) -> None:
        fit = fit_advanced(self.instruments, FAST, lam=1e-5, power=1.0)
        truth = NelsonSiegel()
        grid = np.linspace(0.2, 29.0, 200)
        error_bp = np.abs(fit.curve.zero(grid) - truth.zero(grid)) * 1e4
        self.assertLess(float(np.max(error_bp)), 3.0)

    def test_reprices_clean_quotes_tightly(self) -> None:
        fit = fit_advanced(self.instruments, FAST, lam=1e-5, power=1.0)
        metrics = fit_metrics(fit.curve, self.instruments)
        self.assertLess(metrics["weighted_rmse_bp"], 1.5)

    def test_more_smoothing_produces_a_smoother_forward(self) -> None:
        soft = fit_advanced(self.instruments, FAST, lam=1e-6, power=1.0)
        stiff = fit_advanced(self.instruments, FAST, lam=1e2, power=1.0)
        grid = np.linspace(0.2, 29.0, 400)
        roughness = lambda c: float(np.mean(np.diff(np.asarray(c.forward(grid)), 2) ** 2))
        self.assertLess(roughness(stiff.curve), roughness(soft.curve))

    def test_cross_validation_selects_from_the_grid(self) -> None:
        fit = fit_advanced(self.instruments, FAST)
        self.assertIn(fit.smoothing_lambda, FAST.lambda_grid)
        self.assertIn(fit.penalty_power, FAST.penalty_power_grid)
        self.assertTrue(fit.cv_scores)

    def test_beats_the_bootstrap_on_a_smooth_generating_curve(self) -> None:
        truth = NelsonSiegel()
        grid = np.linspace(0.2, 29.0, 200)
        advanced = fit_advanced(self.instruments, FAST, lam=1e-5, power=1.0).curve
        baseline = fit_baseline(self.instruments, FAST).curve
        worst = lambda c: float(np.max(np.abs(c.zero(grid) - truth.zero(grid))) * 1e4)
        self.assertLess(worst(advanced), worst(baseline))

    def test_deterministic(self) -> None:
        a = fit_advanced(self.instruments, FAST, lam=1e-4, power=1.0)
        b = fit_advanced(self.instruments, FAST, lam=1e-4, power=1.0)
        np.testing.assert_array_equal(a.curve.forwards, b.curve.forwards)

    def test_single_instrument_is_handled(self) -> None:
        fit = fit_advanced(self.instruments[:1], FAST, lam=1.0, power=1.0)
        self.assertTrue(np.all(np.isfinite(fit.curve.forwards)))


class TestRobustness(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(dirty_frame(), self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_screen_finds_the_injected_outlier(self) -> None:
        reasons, _ = screen_outliers(self.instruments, FAST)
        outlier_ids = {
            i.obs_id
            for i in self.instruments
            if i.instrument_type == "ois_swap" and i.maturity_years == 7.0
        }
        flagged = set(reasons) & outlier_ids
        self.assertEqual(len(flagged), 1, f"expected exactly one 7Y outlier, got {reasons}")

    def test_screen_does_not_delete_a_whole_pillar(self) -> None:
        reasons, _ = screen_outliers(self.instruments, FAST)
        survivors = [i for i in self.instruments if i.obs_id not in reasons]
        maturities = {round(i.maturity_years, 6) for i in survivors}
        for original in {round(i.maturity_years, 6) for i in self.instruments}:
            self.assertIn(original, maturities)

    def test_screen_respects_the_exclusion_budget(self) -> None:
        config = FitConfig(
            lambda_grid=FAST.lambda_grid,
            penalty_power_grid=FAST.penalty_power_grid,
            cv_folds=FAST.cv_folds,
            max_exclusion_fraction=0.05,
        )
        reasons, _ = screen_outliers(self.instruments, config)
        self.assertLessEqual(len(reasons), int(0.05 * len(self.instruments)))

    def test_outlier_barely_moves_the_robust_fit(self) -> None:
        reasons, _ = screen_outliers(self.instruments, FAST)
        with_outlier = fit_advanced(self.instruments, FAST, lam=1e-4, power=1.0)
        without = fit_advanced(
            [i for i in self.instruments if i.obs_id not in reasons],
            FAST, lam=1e-4, power=1.0,
        )
        grid = np.linspace(0.2, 29.0, 200)
        shift = np.abs(with_outlier.curve.zero(grid) - without.curve.zero(grid)) * 1e4
        self.assertLess(float(np.max(shift)), 5.0)

    def test_local_residuals_remove_a_shared_pillar_bias(self) -> None:
        residuals = np.zeros(len(self.instruments))
        pillar = [
            k for k, i in enumerate(self.instruments)
            if i.instrument_type == "ois_swap" and i.maturity_years == 7.0
        ]
        self.assertGreaterEqual(len(pillar), 3)
        for k in pillar:
            residuals[k] = 8.0
        local = local_residuals(self.instruments, residuals)
        for k in pillar:
            self.assertAlmostEqual(local[k], 0.0, places=9)

    def test_local_residuals_expose_a_contaminated_minority(self) -> None:
        residuals = np.zeros(len(self.instruments))
        pillar = [
            k for k, i in enumerate(self.instruments)
            if i.instrument_type == "ois_swap" and i.maturity_years == 7.0
        ]
        residuals[pillar[0]] = -150.0
        local = local_residuals(self.instruments, residuals)
        self.assertLess(local[pillar[0]], -100.0)
        for k in pillar[1:]:
            self.assertLess(abs(local[k]), 1.0)


class TestNegativeRateDataset(unittest.TestCase):
    def test_both_estimators_keep_discount_factors_positive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            instruments = instruments_from(negative_rate_frame(), tmp)
        grid = np.linspace(0.05, 35.0, 300)
        for curve in (
            fit_baseline(instruments, FAST).curve,
            fit_advanced(instruments, FAST, lam=1e-4, power=1.0).curve,
        ):
            discount = np.asarray(curve.discount(grid))
            self.assertTrue(np.all(discount > 0.0))
            self.assertTrue(np.all(np.isfinite(discount)))
            self.assertLess(float(np.max(curve.zero(grid))), 0.0)
            self.assertGreater(float(discount[0]), 1.0)


if __name__ == "__main__":
    unittest.main()
