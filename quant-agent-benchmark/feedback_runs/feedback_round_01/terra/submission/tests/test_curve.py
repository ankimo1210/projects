from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from quantcurve.curve import (
    LogDiscountCurve,
    _curve_from_params,
    build_risk,
    key_shape,
    model_quote,
    payment_schedule,
    validate_and_clean,
)


def _row(obs_id: str, instrument_id: str, maturity: float, quote: float) -> dict[str, object]:
    return {
        "obs_id": obs_id, "instrument_id": instrument_id, "source": "test",
        "timestamp": "2026-01-15T12:00:00Z", "currency": "USD", "instrument_type": "deposit",
        "maturity_date": "2026-02-14", "maturity_years": maturity, "start_years": 0.0,
        "coupon_rate": np.nan, "payment_frequency": 1, "day_count": "ACT/365F",
        "quote_type": "simple_rate", "quote_value": quote, "quote_unit": "PERCENT",
        "bid": quote - 0.01, "ask": quote + 0.01, "liquidity_score": 0.9, "settlement_days": 2,
    }


class TestCurveFunctions(unittest.TestCase):
    def test_schedule_includes_final_stub(self) -> None:
        times, accruals = payment_schedule(1.3, 2)
        self.assertAlmostEqual(times[-1], 1.3)
        self.assertAlmostEqual(float(accruals.sum()), 1.3)

    def test_bond_schedule_rolls_back_from_maturity(self) -> None:
        times, accruals = payment_schedule(1.3, 2, anchored_to_maturity=True)
        np.testing.assert_allclose(times, [0.3, 0.8, 1.3])
        np.testing.assert_allclose(accruals, [0.3, 0.5, 0.5])

    def test_deposit_pricing_in_log_discount_space(self) -> None:
        curve = LogDiscountCurve(np.array([0.0, 1.0, 30.0]), np.array([0.0, -np.log(1.02), -0.6]), "baseline")
        row = pd.Series({"instrument_type": "deposit", "maturity_years": 1.0, "payment_frequency": 1})
        self.assertAlmostEqual(model_quote(curve, row), 0.02, places=12)
        self.assertGreater(float(curve.discount(1.0)), 0.0)

    def test_cleaning_normalizes_percent_and_deduplicates(self) -> None:
        frame = pd.DataFrame([
            _row("old", "same", 0.25, 2.0),
            _row("new", "same", 0.25, 2.0),
            *[_row(f"x{i}", f"i{i}", 0.5 + 0.1 * i, 2.0) for i in range(11)],
        ])
        frame.loc[1, "timestamp"] = "2026-01-15T13:00:00Z"
        usable, audit = validate_and_clean(frame, "2026-01-15")
        self.assertEqual(len(usable), 12)
        self.assertAlmostEqual(float(usable.loc[usable.obs_id == "new", "normalized_quote"].iloc[0]), 0.02)
        self.assertEqual(audit.loc[audit.obs_id == "old", "action"].iloc[0], "exclude")
        self.assertEqual(audit.loc[audit.obs_id == "new", "unit_normalization"].iloc[0], "PERCENT_to_annual_decimal")

    def test_cleaning_records_bid_ask_inversion_separately_from_final_action(self) -> None:
        frame = pd.DataFrame([_row(f"x{i}", f"i{i}", 0.2 + 0.1 * i, 2.0) for i in range(12)])
        frame.loc[0, ["bid", "ask"]] = [2.01, 1.99]
        _, audit = validate_and_clean(frame, "2026-01-15")
        row = audit.loc[audit.obs_id == "x0"].iloc[0]
        self.assertTrue(bool(row["bid_ask_inverted"]))
        self.assertAlmostEqual(float(row["normalized_quote"]), 0.02)

    def test_key_shapes_sum_to_parallel(self) -> None:
        t = np.linspace(0.01, 30.0, 501)
        total = sum((key_shape(key)(t) for key in (2.0, 5.0, 10.0, 30.0)), np.zeros_like(t))
        np.testing.assert_allclose(total, np.ones_like(t), atol=1e-12)

    def test_risk_has_all_key_columns(self) -> None:
        parameters = -0.02 * np.array([1 / 12, .25, .5, .75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 25, 30])
        curve = _curve_from_params(parameters, "advanced")
        rows = [_row("a", "a", 1.0, 2.0), *[_row(str(i), str(i), .2 + i / 10, 2.0) for i in range(11)]]
        usable, _ = validate_and_clean(pd.DataFrame(rows), "2026-01-15")
        risk = build_risk(curve, usable.iloc[:1])
        self.assertTrue({"dv01", "key_2y", "key_5y", "key_10y", "key_30y"}.issubset(risk.columns))


if __name__ == "__main__":
    unittest.main()
