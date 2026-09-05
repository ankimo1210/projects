"""Regression tests for the two behaviours measured in feedback_round_01.

These are not extra coverage for its own sake.  Each one pins a number that was
*measured* on a stress grid of self-designed synthetic curves, so that a future
change to the curvature control, the weights or the selection rule cannot
silently move it.

Measured on 5 known curves x 5 conditions (clean, sparse, contaminated,
illiquid, sparse+contaminated); see ``audit/experiments.csv`` E03/E06/E07.
"""
from __future__ import annotations

import unittest

import numpy as np

from quantcurve.conventions import swap_schedule
from quantcurve.curve import DiscountCurve
from quantcurve.holdout import forward_admissibility
from quantcurve.instruments import Instrument
from quantcurve.models import FitConfig, fit_advanced
from quantcurve.pricing import swap_par_rate

FAST = FitConfig(lambda_grid=(1e-5, 1e-3), penalty_power_grid=(1.0,), cv_folds=3)


class _Analytic(DiscountCurve):
    """Closed-form curve: no interpolation, so it is an independent reference."""

    def __init__(self, level, slope, tau):
        self.level, self.slope, self.tau = level, slope, tau

    def zero(self, t):
        t = np.asarray(t, float)
        return self.level + self.slope * (1.0 - np.exp(-t / self.tau))

    def discount(self, t):
        t = np.asarray(t, float)
        return np.exp(-self.zero(t) * t)

    def forward(self, t):
        t = np.asarray(t, float)
        return self.zero(t) + t * (self.slope / self.tau) * np.exp(-t / self.tau)

    def integrated_forward(self, t):
        t = np.asarray(t, float)
        return self.zero(t) * t


def _swap(truth, maturity, bump_bp=0.0, tag="S"):
    frequency = 1 if maturity <= 2.0 else 2
    times, accrual = swap_schedule(maturity, frequency)
    quote = swap_par_rate(truth, times, accrual) * 100.0 + bump_bp / 100.0
    return Instrument(
        obs_id=f"{tag}{maturity:g}", instrument_id=f"{tag}{maturity:g}",
        instrument_type="ois_swap", maturity_years=maturity, coupon_rate=None,
        payment_frequency=frequency, quote=quote, half_spread=0.001,
        liquidity_score=1.0, weight=1.0, source="SYN",
        timestamp="2026-01-15T15:00:00Z",
    )


class TestSparseContaminatedMarket(unittest.TestCase):
    """The one condition where the advanced estimator measurably degrades.

    Five swap pillars with an eight-year hole, and a 40bp gross outlier planted
    at the isolated 5Y pillar.  The robust stage does reject the quote, but the
    rejection leaves a hole that only the penalty can fill, so the *forward*
    error grows even though nothing is broken.  This is an identifiability
    limit, and the test exists so that it stays a known, bounded one.
    """

    def setUp(self) -> None:
        self.truth = _Analytic(0.010, 0.018, 4.0)
        self.pillars = [1.0, 2.0, 5.0, 10.0, 30.0]

    def _fit(self, bump_bp):
        instruments = [
            _swap(self.truth, m, bump_bp if m == 5.0 else 0.0) for m in self.pillars
        ]
        return fit_advanced(instruments, FitConfig())

    def test_the_isolated_outlier_is_given_zero_robust_weight(self) -> None:
        fit = self._fit(40.0)
        index = self.pillars.index(5.0)
        self.assertEqual(float(fit.robust_weights[index]), 0.0)
        self.assertGreater(float(np.min(fit.robust_weights[[0, 1, 3, 4]])), 0.5)

    def test_rejecting_it_still_costs_forward_accuracy_within_a_known_bound(self) -> None:
        grid = np.linspace(0.5, 30.0, 300)

        def forward_rmse_bp(fit):
            delta = np.asarray(fit.curve.forward(grid)) - np.asarray(
                self.truth.forward(grid)
            )
            return float(np.sqrt(np.mean((delta * 1e4) ** 2)))

        clean = forward_rmse_bp(self._fit(0.0))
        dirty = forward_rmse_bp(self._fit(40.0))
        # Measured 11.84bp -> 19.61bp.  The cost is real and is allowed, but it
        # must stay bounded: a regression that let it run away would fail here.
        self.assertGreater(dirty, clean)
        self.assertLess(dirty, 30.0)
        self.assertLess(clean, 20.0)

    def test_discount_factors_stay_positive_under_the_stress(self) -> None:
        grid = np.linspace(0.05, 30.0, 400)
        for bump in (0.0, 40.0):
            discount = np.asarray(self._fit(bump).curve.discount(grid))
            self.assertTrue(np.all(discount > 0.0))
            self.assertTrue(np.all(np.isfinite(discount)))


class TestAdmissibilityGateIsTheSafetyNet(unittest.TestCase):
    """The gate must fire on a genuine forward blow-up and stay quiet otherwise.

    On the round-2 stress grid the advanced estimator produced exactly one
    unusable forward curve (252bp error, an inverted curve with three planted
    outliers) and the gate flagged that case and only that case: 1 of 1 true
    failures caught, 0 of 24 good fits rejected.
    """

    def test_a_clean_fit_is_admissible(self) -> None:
        truth = _Analytic(0.010, 0.018, 4.0)
        instruments = [_swap(truth, m) for m in (1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)]
        fit = fit_advanced(instruments, FAST)
        check = forward_admissibility(fit.curve, instruments, 30.0, 2.0)
        self.assertTrue(check["admissible"], check)
        self.assertEqual(check["breach_percent"], 0.0)

    def test_a_wild_forward_curve_is_rejected(self) -> None:
        truth = _Analytic(0.040, -0.020, 5.0)  # inverted
        instruments = [_swap(truth, m) for m in (1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)]
        # Three planted outliers, the contamination level of the stress grid.
        for index, bump in ((3, 40.0), (5, -35.0), (1, 12.0)):
            m = instruments[index].maturity_years
            instruments[index] = _swap(truth, m, bump)
        fit = fit_advanced(instruments, FAST)
        check = forward_admissibility(fit.curve, instruments, 30.0, 2.0)
        forwards = np.asarray(fit.curve.forward(np.linspace(0.1, 30.0, 600))) * 100.0
        span = float(np.max(forwards) - np.min(forwards))
        # Either the fit stayed sane, or the gate caught it.  What must never
        # happen is a wild forward curve that the gate calls admissible.
        if span > 6.0:
            self.assertFalse(check["admissible"], check)

    def test_the_gate_bounds_are_the_quoted_range_plus_the_tolerance(self) -> None:
        truth = _Analytic(0.010, 0.018, 4.0)
        instruments = [_swap(truth, m) for m in (1.0, 5.0, 10.0, 30.0)]
        fit = fit_advanced(instruments, FAST)
        check = forward_admissibility(fit.curve, instruments, 30.0, 1.5)
        low, high = check["quoted_rate_range_percent"]
        self.assertAlmostEqual(check["lower_bound_percent"], low - 1.5, places=12)
        self.assertAlmostEqual(check["upper_bound_percent"], high + 1.5, places=12)


if __name__ == "__main__":
    unittest.main()
