from __future__ import annotations

import unittest

from quantcurve.conventions import discount_from_zero, simple_deposit_rate, zero_from_discount


class TestBasicConventions(unittest.TestCase):
    def test_zero_discount_round_trip(self) -> None:
        for z in (-0.01, 0.0, 0.037):
            d = discount_from_zero(z, 7.25)
            self.assertAlmostEqual(zero_from_discount(d, 7.25), z, places=13)

    def test_negative_rates_keep_positive_discount(self) -> None:
        self.assertGreater(discount_from_zero(-0.02, 2.0), 1.0)

    def test_simple_deposit_rate(self) -> None:
        self.assertAlmostEqual(simple_deposit_rate(1 / 1.025, 1.0), 0.025)

    def test_invalid_discount_rejected(self) -> None:
        with self.assertRaises(ValueError):
            zero_from_discount(0.0, 1.0)


if __name__ == "__main__":
    unittest.main()
