from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from quantcurve.curve import PiecewiseZeroCurve, _key_basis, _payment_schedule, calculate_risk, model_quote


class TestCurveEngine(unittest.TestCase):
    def test_schedule_has_positive_accruals_and_final_maturity(self) -> None:
        times, accruals = _payment_schedule(1.508434, 2)
        self.assertAlmostEqual(float(times[-1]), 1.508434)
        self.assertTrue(np.all(accruals > 0))
        self.assertAlmostEqual(float(accruals.sum()), 1.508434)

    def test_curve_supports_negative_rates_with_positive_discount(self) -> None:
        curve = PiecewiseZeroCurve(np.array([0.0, 1.0, 30.0]), np.array([-0.02, -0.02, 0.01]))
        self.assertGreater(curve.discount(0.5), 1.0)
        grid = curve.grid()
        self.assertTrue(np.all(grid["discount_factor"] > 0))

    def test_analytical_forward_matches_piecewise_zero_derivative(self) -> None:
        curve = PiecewiseZeroCurve(np.array([0.0, 1.0, 3.0]), np.array([0.01, 0.02, 0.03]))
        expected = 0.0225 + 1.5 * (0.03 - 0.02) / 2.0
        self.assertAlmostEqual(float(curve.forward(1.5)), expected, places=12)
        self.assertAlmostEqual(float(curve.forward(1.0)), 0.02 + 1.0 * 0.5 * (0.01 + 0.005), places=12)
        grid = curve.grid(start=0.25, end=2.75, count=51)
        self.assertTrue(np.all(np.isfinite(grid["forward_rate"])))

    def test_key_basis_is_partition_of_unity(self) -> None:
        basis = _key_basis(np.linspace(0.1, 30.0, 101))
        self.assertTrue(np.allclose(basis.sum(axis=1), 1.0))
        self.assertTrue(np.all(basis >= 0.0))

    def test_swap_quote_is_close_to_par_for_flat_curve(self) -> None:
        curve = PiecewiseZeroCurve(np.array([0.0, 30.0]), np.array([0.02, 0.02]))
        row = pd.Series({"instrument_type": "ois_swap", "maturity_years": 5.0, "payment_frequency": 2})
        times = np.arange(0.5, 5.0 + 0.25, 0.5)
        expected = (1.0 - np.exp(-0.02 * 5.0)) / np.sum(0.5 * np.exp(-0.02 * times))
        self.assertAlmostEqual(model_quote(row, curve), expected, places=12)

    def test_key_rate_risk_has_parallel_sign_and_partition_check(self) -> None:
        curve = PiecewiseZeroCurve(np.array([0.0, 30.0]), np.array([0.02, 0.02]))
        frame = pd.DataFrame([{
            "instrument_id": "B1", "instrument_type": "bond", "maturity_years": 5.0,
            "payment_frequency": 2, "coupon_rate": 0.02, "normalized_quote": 100.0,
            "action": "keep", "normalized_bid": 99.9, "normalized_ask": 100.1,
        }])
        risk = calculate_risk(frame, curve).iloc[0]
        self.assertGreater(risk["dv01"], 0.0)
        self.assertLess(risk["key_sum_relative_error"], 1e-4)


if __name__ == "__main__":
    unittest.main()
