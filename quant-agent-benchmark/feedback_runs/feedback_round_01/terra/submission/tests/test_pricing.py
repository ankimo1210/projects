from __future__ import annotations

import math
import unittest

import numpy as np

from quantcurve.pricing import bond_clean_price, bond_payment_schedule, deposit_simple_rate, ois_par_rate, ois_payment_schedule


class ExponentialDiscount:
    def __init__(self, rate: float) -> None:
        self.rate = rate

    def discount(self, maturity: float | np.ndarray) -> np.ndarray:
        return np.exp(-self.rate * np.asarray(maturity, dtype=float))


class TestDirectDiscountPricing(unittest.TestCase):
    def test_deposit_matches_closed_form_simple_rate(self) -> None:
        curve = ExponentialDiscount(0.02)
        expected = (math.exp(0.02 * 0.75) - 1.0) / 0.75
        self.assertAlmostEqual(deposit_simple_rate(curve, 0.75), expected, places=13)

    def test_fractional_ois_matches_explicit_cashflow_formula(self) -> None:
        curve = ExponentialDiscount(0.015)
        times, accruals = ois_payment_schedule(1.25, 1)
        np.testing.assert_allclose(times, [1.0, 1.25])
        np.testing.assert_allclose(accruals, [1.0, 0.25])
        expected = (1.0 - math.exp(-0.015 * 1.25)) / (math.exp(-0.015) + 0.25 * math.exp(-0.015 * 1.25))
        self.assertAlmostEqual(ois_par_rate(curve, 1.25, 1), expected, places=13)

    def test_fractional_bond_matches_independent_explicit_cashflows(self) -> None:
        curve = ExponentialDiscount(0.03)
        times, accruals = bond_payment_schedule(1.3, 2)
        np.testing.assert_allclose(times, [0.3, 0.8, 1.3])
        np.testing.assert_allclose(accruals, [0.3, 0.5, 0.5])
        expected = 1.2 * math.exp(-0.03 * 0.3) + 2.0 * math.exp(-0.03 * 0.8) + 102.0 * math.exp(-0.03 * 1.3)
        self.assertAlmostEqual(bond_clean_price(curve, 1.3, 0.04, 2), expected, places=12)

    def test_negative_rates_keep_discount_and_prices_finite(self) -> None:
        curve = ExponentialDiscount(-0.01)
        self.assertGreater(float(curve.discount(10.0)), 0.0)
        self.assertTrue(math.isfinite(ois_par_rate(curve, 5.0, 2)))
        self.assertTrue(math.isfinite(bond_clean_price(curve, 5.3, 0.02, 2)))


if __name__ == "__main__":
    unittest.main()
