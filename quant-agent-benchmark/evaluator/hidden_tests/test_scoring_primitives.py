from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from evaluator.scoring import bounded_score, curve_discount, locate_project, model_quote, normalize_curve, rmse


class TestScoringPrimitives(unittest.TestCase):
    def test_bounded_score(self) -> None:
        self.assertEqual(bounded_score(1, 1, 3), 1)
        self.assertEqual(bounded_score(3, 1, 3), 0)
        self.assertAlmostEqual(bounded_score(2, 1, 3), 0.5)

    def test_rmse(self) -> None:
        self.assertAlmostEqual(rmse(np.array([3.0, 4.0])), np.sqrt(12.5))

    def test_normalize_curve_orders_and_deduplicates(self) -> None:
        frame = pd.DataFrame({"maturity_years": [2, 1, 1], "zero_rate": [.02, .01, .011], "discount_factor": [.96, .99, .989], "forward_rate": [.02, .01, .011]})
        result = normalize_curve(frame)
        self.assertEqual(result["maturity_years"].tolist(), [1, 2])
        self.assertEqual(result["zero_rate"].iloc[0], .011)

    def test_discount_positive_under_negative_rate(self) -> None:
        curve = pd.DataFrame({"maturity_years": [0.1, 30], "zero_rate": [-.01, .02], "discount_factor": [1, .5], "forward_rate": [0, 0]})
        self.assertTrue((curve_discount(curve, np.linspace(.1, 30, 20)) > 0).all())

    def test_model_quote_deposit(self) -> None:
        curve = pd.DataFrame({"maturity_years": [0.1, 30], "zero_rate": [.02, .02], "discount_factor": [.998, .55], "forward_rate": [.02, .02]})
        row = pd.Series({"maturity_years": 1.0, "instrument_type": "deposit", "payment_frequency": 1, "coupon_rate": np.nan})
        self.assertTrue(np.isfinite(model_quote(row, curve)))

    def test_locate_project_rejects_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(locate_project(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
