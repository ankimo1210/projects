from __future__ import annotations

import math
import unittest

import numpy as np

from quantcurve.curve import PiecewiseLinearZeroCurve, ShiftedCurve, SplineZeroCurve

KNOTS = np.array([1 / 12, 1.0, 2.0, 5.0, 10.0, 30.0])


class TestPiecewiseLinearZeroCurve(unittest.TestCase):
    def setUp(self) -> None:
        self.curve = PiecewiseLinearZeroCurve(KNOTS, np.array([0.01, 0.015, 0.02, 0.022, 0.02, 0.018]))

    def test_discount_matches_definition(self) -> None:
        for t in (0.2, 1.0, 3.3, 15.0):
            z = self.curve.zero_rate(t)
            self.assertAlmostEqual(self.curve.discount(t), math.exp(-z * t), places=12)

    def test_discount_always_positive_for_negative_rates(self) -> None:
        curve = PiecewiseLinearZeroCurve(KNOTS, np.array([-0.03, -0.02, -0.01, 0.0, 0.01, 0.02]))
        grid = np.linspace(KNOTS[0], KNOTS[-1], 500)
        self.assertTrue(np.all(curve.discount(grid) > 0))

    def test_flat_extrapolation(self) -> None:
        self.assertAlmostEqual(self.curve.zero_rate(0.001), self.curve.zero_rate(KNOTS[0]))
        self.assertAlmostEqual(self.curve.zero_rate(50.0), self.curve.zero_rate(KNOTS[-1]))

    def test_rejects_non_increasing_knots(self) -> None:
        with self.assertRaises(ValueError):
            PiecewiseLinearZeroCurve(np.array([1.0, 1.0, 2.0]), np.array([0.01, 0.01, 0.02]))


class TestSplineZeroCurve(unittest.TestCase):
    def setUp(self) -> None:
        self.curve = SplineZeroCurve(KNOTS, np.array([0.01, 0.015, 0.02, 0.022, 0.02, 0.018]))

    def test_discount_matches_definition(self) -> None:
        for t in (0.2, 1.0, 3.3, 15.0):
            z = self.curve.zero_rate(t)
            self.assertAlmostEqual(self.curve.discount(t), math.exp(-z * t), places=10)

    def test_discount_always_positive_for_negative_rates(self) -> None:
        curve = SplineZeroCurve(KNOTS, np.array([-0.03, -0.02, -0.01, 0.0, 0.01, 0.02]))
        grid = np.linspace(KNOTS[0], KNOTS[-1], 500)
        self.assertTrue(np.all(curve.discount(grid) > 0))

    def test_forward_rate_integrates_back_to_discount(self) -> None:
        # exp(-integral(f dt)) should reproduce D(T) for the smooth spline curve.
        T = 8.0
        grid = np.linspace(0.0, T, 20000)
        grid = np.clip(grid, KNOTS[0], None)
        f = self.curve.forward_rate(grid)
        integral = np.trapezoid(f, grid) + self.curve.forward_rate(KNOTS[0]) * KNOTS[0]
        self.assertAlmostEqual(math.exp(-integral), self.curve.discount(T), places=3)


class TestShiftedCurve(unittest.TestCase):
    def test_parallel_shift_adds_to_zero_rate(self) -> None:
        base = PiecewiseLinearZeroCurve(KNOTS, np.array([0.01, 0.015, 0.02, 0.022, 0.02, 0.018]))
        bumped = ShiftedCurve(base, lambda t: np.full_like(np.atleast_1d(np.asarray(t, dtype=float)), 0.0001))
        for t in (0.5, 4.0, 20.0):
            self.assertAlmostEqual(bumped.zero_rate(t), base.zero_rate(t) + 0.0001, places=12)


if __name__ == "__main__":
    unittest.main()
