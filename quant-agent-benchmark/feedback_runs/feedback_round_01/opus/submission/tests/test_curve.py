from __future__ import annotations

import unittest

import numpy as np

from quantcurve.curve import (
    BumpedCurve,
    PiecewiseFlatForwardCurve,
    SplineForwardCurve,
    curve_frame,
)


class TestPiecewiseFlatForwardCurve(unittest.TestCase):
    def test_flat_curve_matches_closed_form(self) -> None:
        curve = PiecewiseFlatForwardCurve(np.array([1.0, 5.0]), np.array([0.02, 0.02]))
        grid = np.array([0.5, 1.0, 3.0, 5.0, 9.0])
        np.testing.assert_allclose(curve.discount(grid), np.exp(-0.02 * grid), rtol=1e-14)
        np.testing.assert_allclose(curve.zero(grid), np.full(grid.shape, 0.02), rtol=1e-12)

    def test_piecewise_integral(self) -> None:
        curve = PiecewiseFlatForwardCurve(np.array([1.0, 2.0]), np.array([0.01, 0.03]))
        self.assertAlmostEqual(float(curve.integrated_forward(np.array([1.5]))[0]),
                               0.01 * 1.0 + 0.03 * 0.5, places=14)
        self.assertAlmostEqual(float(curve.zero(np.array([2.0]))[0]),
                               (0.01 + 0.03) / 2.0, places=14)

    def test_flat_extrapolation_beyond_last_pillar(self) -> None:
        curve = PiecewiseFlatForwardCurve(np.array([1.0, 2.0]), np.array([0.01, 0.03]))
        self.assertAlmostEqual(float(curve.forward(np.array([50.0]))[0]), 0.03)

    def test_rejects_malformed_input(self) -> None:
        with self.assertRaises(ValueError):
            PiecewiseFlatForwardCurve(np.array([2.0, 1.0]), np.array([0.01, 0.02]))
        with self.assertRaises(ValueError):
            PiecewiseFlatForwardCurve(np.array([1.0]), np.array([0.01, 0.02]))
        with self.assertRaises(ValueError):
            PiecewiseFlatForwardCurve(np.array([0.0, 1.0]), np.array([0.01, 0.02]))


class TestSplineForwardCurve(unittest.TestCase):
    def test_constant_forward_is_reproduced_exactly(self) -> None:
        knots = np.array([0.25, 1.0, 5.0, 30.0])
        curve = SplineForwardCurve(knots, np.full(4, 0.017))
        grid = np.array([0.1, 0.25, 2.0, 12.5, 30.0, 45.0])
        np.testing.assert_allclose(curve.forward(grid), 0.017, rtol=1e-12)
        np.testing.assert_allclose(curve.discount(grid), np.exp(-0.017 * grid), rtol=1e-12)

    def test_linear_forward_integrates_analytically(self) -> None:
        knots = np.array([1.0, 2.0, 3.0])
        curve = SplineForwardCurve(knots, np.array([0.01, 0.02, 0.03]))
        # f is the straight line 0.01 * T on [1, 3]; integral from 0 to 3 is
        # 0.01 (flat below the first knot) + area of the trapezium.
        expected = 0.01 * 1.0 + 0.5 * (0.01 + 0.03) * 2.0
        self.assertAlmostEqual(
            float(curve.integrated_forward(np.array([3.0]))[0]), expected, places=12
        )

    def test_flat_forward_extrapolation_both_ends(self) -> None:
        curve = SplineForwardCurve(np.array([1.0, 5.0, 10.0]), np.array([0.01, 0.02, 0.03]))
        self.assertAlmostEqual(float(curve.forward(np.array([0.01]))[0]), 0.01, places=12)
        self.assertAlmostEqual(float(curve.forward(np.array([50.0]))[0]), 0.03, places=12)

    def test_forward_matches_minus_dlogd_dt(self) -> None:
        knots = np.array([0.25, 1.0, 3.0, 7.0, 15.0, 30.0])
        curve = SplineForwardCurve(knots, np.array([0.01, 0.015, 0.022, 0.026, 0.024, 0.02]))
        grid = np.linspace(0.4, 29.0, 60)
        h = 1e-5
        numeric = -(np.log(curve.discount(grid + h)) - np.log(curve.discount(grid - h))) / (2 * h)
        np.testing.assert_allclose(curve.forward(grid), numeric, atol=2e-8)

    def test_zero_and_discount_are_consistent(self) -> None:
        curve = SplineForwardCurve(np.array([0.5, 5.0, 30.0]), np.array([0.005, 0.02, 0.03]))
        grid = np.linspace(0.1, 40.0, 50)
        np.testing.assert_allclose(
            curve.discount(grid), np.exp(-curve.zero(grid) * grid), rtol=1e-12
        )

    def test_single_knot_is_flat(self) -> None:
        curve = SplineForwardCurve(np.array([1.0]), np.array([-0.004]))
        grid = np.array([0.1, 1.0, 20.0])
        np.testing.assert_allclose(curve.forward(grid), -0.004)
        np.testing.assert_allclose(curve.discount(grid), np.exp(0.004 * grid))


class TestNegativeRates(unittest.TestCase):
    def test_discount_factors_stay_positive_and_above_one(self) -> None:
        curve = SplineForwardCurve(
            np.array([0.25, 2.0, 10.0, 30.0]), np.array([-0.008, -0.006, -0.002, 0.001])
        )
        grid = np.linspace(0.05, 40.0, 200)
        discount = curve.discount(grid)
        self.assertTrue(np.all(discount > 0.0))
        self.assertTrue(np.all(np.isfinite(discount)))
        self.assertGreater(float(discount[0]), 1.0)
        self.assertTrue(np.all(curve.zero(grid) < 0.002))

    def test_curve_frame_accepts_negative_rates(self) -> None:
        curve = SplineForwardCurve(np.array([0.25, 30.0]), np.array([-0.01, -0.005]))
        frame = curve_frame(curve, np.linspace(1 / 12, 30.0, 361))
        self.assertTrue(np.all(frame["discount_factor"] > 0.0))
        self.assertTrue(np.all(frame["zero_rate"] < 0.0))


class TestBumpedCurve(unittest.TestCase):
    def test_parallel_bump_shifts_zero_rate_exactly(self) -> None:
        base = SplineForwardCurve(np.array([1.0, 10.0, 30.0]), np.array([0.02, 0.025, 0.02]))
        bumped = BumpedCurve(base, lambda t: np.full(np.asarray(t, float).shape, 1e-4))
        grid = np.array([0.5, 3.0, 17.0, 30.0])
        np.testing.assert_allclose(bumped.zero(grid), base.zero(grid) + 1e-4, atol=1e-15)
        np.testing.assert_allclose(
            bumped.discount(grid), base.discount(grid) * np.exp(-1e-4 * grid), rtol=1e-12
        )

    def test_bumped_curve_stays_positive(self) -> None:
        base = SplineForwardCurve(np.array([1.0, 30.0]), np.array([0.02, 0.02]))
        bumped = BumpedCurve(base, lambda t: np.full(np.asarray(t, float).shape, -0.10))
        self.assertTrue(np.all(bumped.discount(np.linspace(0.1, 30, 50)) > 0.0))


class TestCurveFrame(unittest.TestCase):
    def test_rejects_unordered_grid(self) -> None:
        curve = SplineForwardCurve(np.array([1.0, 30.0]), np.array([0.02, 0.02]))
        with self.assertRaises(ValueError):
            curve_frame(curve, np.array([2.0, 1.0]))
        with self.assertRaises(ValueError):
            curve_frame(curve, np.array([0.0, 1.0]))

    def test_frame_columns(self) -> None:
        curve = SplineForwardCurve(np.array([1.0, 30.0]), np.array([0.02, 0.02]))
        frame = curve_frame(curve, np.linspace(1 / 12, 30, 361))
        self.assertEqual(
            set(frame), {"maturity_years", "zero_rate", "discount_factor", "forward_rate"}
        )
        self.assertEqual(len(frame["maturity_years"]), 361)


if __name__ == "__main__":
    unittest.main()
