from __future__ import annotations

import unittest

import numpy as np

from quantcurve.curve import PiecewiseLinearZeroCurve, SplineZeroCurve
from quantcurve.diagnostics import forward_smoothness_check


class TestForwardSmoothnessCheck(unittest.TestCase):
    """f(t) = z(t) + t*z'(t): a kinked (piecewise-linear) zero curve must
    show a real forward-rate jump at the kink, while a natural-cubic-spline
    zero curve fit to the same points (smoother by construction) must not.
    This is the H2/H6 diagnostic distinguishing forward-rate error from
    zero-rate error -- it must not be silently satisfied by both curves
    reporting zero, nor by both reporting the same nonzero jump.
    """

    def setUp(self) -> None:
        # Deliberate sharp slope change at the knot t=2.0 (slope flips sign).
        self.knots = np.array([0.5, 1.0, 2.0, 3.0, 5.0, 10.0])
        self.zero_rates = np.array([0.01, 0.012, 0.020, 0.017, 0.021, 0.020])
        self.piecewise = PiecewiseLinearZeroCurve(self.knots, self.zero_rates)
        self.spline = SplineZeroCurve(self.knots, self.zero_rates)

    def test_piecewise_linear_shows_real_jump_at_kink(self) -> None:
        report = forward_smoothness_check(self.piecewise, self.spline, self.knots, eps=1e-4)
        self.assertGreater(report["baseline_max_jump_bp"], 50.0)

    def test_spline_stays_continuous_at_the_same_knot(self) -> None:
        report = forward_smoothness_check(self.piecewise, self.spline, self.knots, eps=1e-4)
        self.assertLess(report["advanced_max_jump_bp"], 1.0)

    def test_worst_baseline_knot_matches_the_deliberate_kink(self) -> None:
        report = forward_smoothness_check(self.piecewise, self.spline, self.knots, eps=1e-4)
        self.assertAlmostEqual(report["worst_baseline_knot"]["knot"], 2.0, places=6)

    def test_per_knot_rows_cover_every_internal_knot(self) -> None:
        report = forward_smoothness_check(self.piecewise, self.spline, self.knots, eps=1e-4)
        self.assertEqual(len(report["per_knot"]), len(self.knots) - 2)


if __name__ == "__main__":
    unittest.main()
