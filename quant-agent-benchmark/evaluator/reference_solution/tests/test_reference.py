from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from quantcurve.cli import Curve, NODES, model_quote, payment_times


class TestReferencePrimitives(unittest.TestCase):
    def setUp(self) -> None:
        self.curve = Curve(np.linspace(-0.002, 0.03, len(NODES)))

    def test_discount_positive_with_negative_rates(self) -> None:
        self.assertTrue(np.all(self.curve.discount(np.linspace(0.01, 30, 100)) > 0))

    def test_payment_schedule(self) -> None:
        np.testing.assert_allclose(payment_times(2.0, 2), [0.5, 1.0, 1.5, 2.0])

    def test_deposit_quote_finite(self) -> None:
        row = pd.Series({"maturity_years": 0.25, "payment_frequency": 1, "instrument_type": "deposit", "coupon_rate": np.nan})
        self.assertTrue(np.isfinite(model_quote(row, self.curve)))

    def test_swap_quote_finite(self) -> None:
        row = pd.Series({"maturity_years": 10.0, "payment_frequency": 2, "instrument_type": "ois_swap", "coupon_rate": np.nan})
        self.assertTrue(np.isfinite(model_quote(row, self.curve)))

    def test_zero_discount_identity(self) -> None:
        t = np.linspace(0.1, 30, 50)
        np.testing.assert_allclose(self.curve.discount(t), np.exp(-self.curve.zero(t) * t))


if __name__ == "__main__":
    unittest.main()
