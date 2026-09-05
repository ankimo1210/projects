from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quantcurve.cashflows import payment_times, year_fractions
from quantcurve.cli import main

VALUATION_DATE = "2026-01-15"


def _flat_discount(z: float):
    return lambda t: math.exp(-z * t)


def _build_synthetic_csv(path: Path) -> None:
    discount = _flat_discount(0.02)
    rows = []
    obs = 0

    def next_id(prefix: str) -> tuple[str, str]:
        nonlocal obs
        obs += 1
        return f"OBS{obs:04d}", f"{prefix}{obs:04d}"

    for t in (1 / 12, 0.25, 0.5, 0.75, 1.0):
        rate = (1.0 / discount(t) - 1.0) / t
        obs_id, inst_id = next_id("DEP")
        rows.append(
            dict(
                obs_id=obs_id, instrument_id=inst_id, source="VENUE_A", timestamp="2026-01-15T15:00:00Z",
                currency="USD", instrument_type="deposit", maturity_date="2027-01-15", maturity_years=t,
                start_years=0, coupon_rate="", payment_frequency=1, day_count="ACT/365F",
                quote_type="simple_rate", quote_value=rate * 100.0, quote_unit="PERCENT",
                bid=rate * 100.0 - 0.01, ask=rate * 100.0 + 0.01, liquidity_score=0.9, settlement_days=2,
            )
        )

    for t in (1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0):
        freq = 1 if t <= 2 else 2
        times = payment_times(t, freq)
        alphas = year_fractions(times)
        discounts = [discount(x) for x in times]
        annuity = sum(a * d for a, d in zip(alphas, discounts))
        par = (1.0 - discounts[-1]) / annuity
        for _ in range(2):
            obs_id, inst_id = next_id("SWP")
            rows.append(
                dict(
                    obs_id=obs_id, instrument_id=inst_id, source="VENUE_B", timestamp="2026-01-15T15:00:00Z",
                    currency="USD", instrument_type="ois_swap", maturity_date="2027-01-15", maturity_years=t,
                    start_years=0, coupon_rate="", payment_frequency=freq, day_count="ACT/365F",
                    quote_type="par_rate", quote_value=par * 100.0, quote_unit="PERCENT",
                    bid=par * 100.0 - 0.01, ask=par * 100.0 + 0.01, liquidity_score=0.85, settlement_days=2,
                )
            )

    for t, coupon in ((2.5, 0.02), (5.5, 0.025), (9.5, 0.02), (14.5, 0.03), (22.0, 0.02)):
        freq = 2
        times = payment_times(t, freq)
        amounts = [coupon / freq * 100.0] * len(times)
        amounts[-1] += 100.0
        price = sum(a * discount(x) for a, x in zip(amounts, times))
        obs_id, inst_id = next_id("BND")
        rows.append(
            dict(
                obs_id=obs_id, instrument_id=inst_id, source="COMPOSITE", timestamp="2026-01-15T15:00:00Z",
                currency="USD", instrument_type="bond", maturity_date="2027-01-15", maturity_years=t,
                start_years=0, coupon_rate=coupon, payment_frequency=freq, day_count="ACT/365F",
                quote_type="clean_price", quote_value=price, quote_unit="PRICE_POINTS",
                bid=price - 0.05, ask=price + 0.05, liquidity_score=0.8, settlement_days=2,
            )
        )

    pd.DataFrame(rows).to_csv(path, index=False)


class TestCliEndToEnd(unittest.TestCase):
    def test_full_workflow_produces_the_required_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            market_data = tmp_path / "market_observations.csv"
            _build_synthetic_csv(market_data)
            output_dir = tmp_path / "outputs"
            report_dir = tmp_path / "reports"

            exit_code = main(
                [
                    "run",
                    "--market-data", str(market_data),
                    "--output-dir", str(output_dir),
                    "--valuation-date", VALUATION_DATE,
                    "--report-dir", str(report_dir),
                ]
            )
            self.assertEqual(exit_code, 0)

            curve = pd.read_csv(output_dir / "curves" / "curve.csv")
            self.assertGreaterEqual(len(curve), 361)
            self.assertGreaterEqual(curve["maturity_years"].min(), 1 / 12 - 1e-9)
            self.assertLessEqual(curve["maturity_years"].max(), 30.0 + 1e-9)
            self.assertTrue((curve["discount_factor"] > 0).all())
            self.assertFalse(curve.isna().any().any())

            cleaning = pd.read_csv(output_dir / "diagnostics" / "cleaning.csv")
            self.assertTrue(set(cleaning["action"]).issubset({"keep", "correct", "downweight", "exclude"}))

            repricing = pd.read_csv(output_dir / "diagnostics" / "repricing.csv")
            for col in ("instrument_id", "instrument_type", "market_quote", "model_quote", "residual", "weight"):
                self.assertIn(col, repricing.columns)

            risk = pd.read_csv(output_dir / "diagnostics" / "risk.csv")
            for col in ("instrument_id", "dv01", "key_2y", "key_5y", "key_10y", "key_30y"):
                self.assertIn(col, risk.columns)
            self.assertFalse(risk.isna().any().any())

            with open(output_dir / "diagnostics" / "model_comparison.json") as fh:
                comparison = json.load(fh)
            self.assertIn(comparison["model_selected"], {"baseline", "advanced"})

            with open(output_dir / "diagnostics" / "sensitivity.json") as fh:
                sensitivity = json.load(fh)
            self.assertGreaterEqual(len(sensitivity), 3)

            for chart in ("curve.png", "forward_rate.png", "repricing.png", "model_comparison.png"):
                chart_path = output_dir / "charts" / chart
                self.assertTrue(chart_path.exists())
                self.assertGreater(chart_path.stat().st_size, 0)

            report_path = report_dir / "research_report.html"
            self.assertTrue(report_path.exists())
            self.assertIn("<title>", report_path.read_text(encoding="utf-8"))

    def test_missing_market_data_file_is_actionable_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            exit_code = main(
                [
                    "run",
                    "--market-data", str(Path(tmp) / "does-not-exist.csv"),
                    "--output-dir", str(Path(tmp) / "outputs"),
                    "--valuation-date", VALUATION_DATE,
                ]
            )
            self.assertNotEqual(exit_code, 0)

    def test_invalid_valuation_date_is_actionable_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            market_data = tmp_path / "market_observations.csv"
            _build_synthetic_csv(market_data)
            exit_code = main(
                [
                    "run",
                    "--market-data", str(market_data),
                    "--output-dir", str(tmp_path / "outputs"),
                    "--valuation-date", "not-a-date",
                ]
            )
            self.assertNotEqual(exit_code, 0)

    def test_missing_columns_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            market_data = tmp_path / "bad.csv"
            pd.DataFrame({"obs_id": ["x"]}).to_csv(market_data, index=False)
            exit_code = main(
                [
                    "run",
                    "--market-data", str(market_data),
                    "--output-dir", str(tmp_path / "outputs"),
                    "--valuation-date", VALUATION_DATE,
                ]
            )
            self.assertNotEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
