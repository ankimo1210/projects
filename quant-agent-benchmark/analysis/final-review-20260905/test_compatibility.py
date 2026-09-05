import unittest
import numpy as np
import pandas as pd

from evaluate_compatible import ROOT, scoring, ORIGINAL_RISK_AGREEMENT, compatible_risk_agreement


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.truth = pd.DataFrame([dict(instrument_id="x", instrument_type="deposit",
            maturity_years=1.0, payment_frequency=1, coupon_rate=0.0, true_quote=2.0)])
        self.curve = pd.DataFrame({"maturity_years": [0.01, 30.0], "zero_rate": [0.02, 0.02]})
        row = self.truth.iloc[0]
        dv = (scoring.trade_pv(row, self.curve, 2.0, -1e-4) - scoring.trade_pv(row, self.curve, 2.0, 1e-4))/2
        self.risk = pd.DataFrame([dict(instrument_id="x", dv01=dv, key_2y=dv,
                                      key_5y=0.0, key_10y=0.0, key_30y=0.0)])

    def test_reproduces_original_collision(self):
        with self.assertRaises(KeyError):
            ORIGINAL_RISK_AGREEMENT(self.curve, self.risk.assign(instrument_type="deposit"), self.truth)

    def test_required_columns_unchanged(self):
        self.assertEqual(ORIGINAL_RISK_AGREEMENT(self.curve, self.risk, self.truth),
                         compatible_risk_agreement(self.curve, self.risk, self.truth))

    def test_optional_fields_cannot_override_truth(self):
        enriched = self.risk.assign(instrument_type="wrong", maturity_years=-900, true_quote=999)
        self.assertEqual(ORIGINAL_RISK_AGREEMENT(self.curve, self.risk, self.truth),
                         compatible_risk_agreement(self.curve, enriched, self.truth))

    def test_all_final_submissions_match_required_only_baseline(self):
        truth = pd.read_csv(ROOT / "evaluator/ground_truth/all_instruments_truth.csv")
        for path in ("results/astra", "output/sol", "results/opus", "results/fable"):
            with self.subTest(candidate=path):
                curve = scoring.normalize_curve(pd.read_csv(ROOT / path / "outputs/curves/curve.csv"))
                risk = pd.read_csv(ROOT / path / "outputs/diagnostics/risk.csv")
                expected = ORIGINAL_RISK_AGREEMENT(curve, risk[list(scoring.RISK_COLUMNS)], truth)
                np.testing.assert_allclose(compatible_risk_agreement(curve, risk, truth), expected)


if __name__ == "__main__":
    unittest.main()
