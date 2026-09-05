from __future__ import annotations

import unittest

import pandas as pd

from quantcurve.cleaning import clean_market_data

VALUATION_DATE = pd.Timestamp("2026-01-15", tz="UTC")


def _row(**overrides):
    base = dict(
        obs_id="OBS", instrument_id="INS", source="VENUE_A",
        timestamp="2026-01-15T15:00:00Z", currency="USD", instrument_type="deposit",
        maturity_date="2026-07-15", maturity_years=0.5, start_years=0, coupon_rate=None,
        payment_frequency=1, day_count="ACT/365F", quote_type="simple_rate",
        quote_value=1.5, quote_unit="PERCENT", bid=1.495, ask=1.505, liquidity_score=0.9,
        settlement_days=2,
    )
    base.update(overrides)
    return base


def build_synthetic_frame() -> pd.DataFrame:
    rows = [
        # A clean 6M deposit bucket: three quotes agree, one is a x100 decimal/percent scale error.
        _row(obs_id="D1", instrument_id="DEP1", quote_value=1.500, bid=1.495, ask=1.505),
        _row(obs_id="D2", instrument_id="DEP2", quote_value=1.510, bid=1.505, ask=1.515),
        _row(obs_id="D3", instrument_id="DEP3", quote_value=0.0149, bid=0.0148, ask=0.0150),  # needs x100
        # Duplicate instrument: stale backup feed outside its own bid/ask vs a fresh, in-spread quote.
        _row(obs_id="D4a", instrument_id="DEP4", source="BACKUP_FEED", timestamp="2026-01-14T09:00:00Z",
             quote_value=1.560, bid=1.500, ask=1.510),
        _row(obs_id="D4b", instrument_id="DEP4", source="VENUE_B", timestamp="2026-01-15T15:30:00Z",
             quote_value=1.505, bid=1.500, ask=1.510),
        # Missing quote_value, recoverable from bid/ask midpoint.
        _row(obs_id="D5", instrument_id="DEP5", quote_value=None, bid=1.498, ask=1.502),
        # Crossed bid/ask that becomes consistent once reordered.
        _row(obs_id="D6", instrument_id="DEP6", quote_value=1.503, bid=1.506, ask=1.500),
        # Wide bid/ask spread + low liquidity vs. its peers -> downweight, not exclude.
        _row(obs_id="D7", instrument_id="DEP7", quote_value=1.500, bid=1.20, ask=1.80, liquidity_score=0.1),
        # An uncorrectable garbage quote: no candidate factor reconciles it with peers.
        _row(obs_id="D8", instrument_id="DEP8", quote_value=0.55, bid=0.548, ask=0.552),
        # OIS swaps at a shared 5Y maturity, one with a x100 scale defect.
        _row(obs_id="S1", instrument_id="SWP1", instrument_type="ois_swap", maturity_years=5.0,
             payment_frequency=2, quote_type="par_rate", quote_value=2.30, bid=2.295, ask=2.305),
        _row(obs_id="S2", instrument_id="SWP2", instrument_type="ois_swap", maturity_years=5.0,
             payment_frequency=2, quote_type="par_rate", quote_value=2.31, bid=2.305, ask=2.315),
        _row(obs_id="S3", instrument_id="SWP3", instrument_type="ois_swap", maturity_years=5.0,
             payment_frequency=2, quote_type="par_rate", quote_value=0.0229, bid=0.0228, ask=0.0230),
        # Bonds forming a smooth YTM neighbourhood (enough clean peers that the
        # window is not dominated by the two problem bonds -- mirrors the real
        # ~45-bond dataset, where contamination per window is a small minority,
        # not the ~50% a 4-bond fixture would imply), one x100 price defect,
        # and one genuinely mispriced/uncorrectable outlier.
        _row(obs_id="B1", instrument_id="BND1", instrument_type="bond", maturity_years=1.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=100.0, bid=99.9, ask=100.1),
        _row(obs_id="B2", instrument_id="BND2", instrument_type="bond", maturity_years=2.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=100.2, bid=100.1, ask=100.3),
        _row(obs_id="B3", instrument_id="BND3", instrument_type="bond", maturity_years=3.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=1.004, bid=1.003, ask=1.005),  # needs x100
        _row(obs_id="B4", instrument_id="BND4", instrument_type="bond", maturity_years=4.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=60.0, bid=59.9, ask=60.1),  # genuinely mispriced, uncorrectable
        _row(obs_id="B5", instrument_id="BND5", instrument_type="bond", maturity_years=5.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=100.1, bid=100.0, ask=100.2),
        _row(obs_id="B6", instrument_id="BND6", instrument_type="bond", maturity_years=6.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=99.9, bid=99.8, ask=100.0),
        _row(obs_id="B7", instrument_id="BND7", instrument_type="bond", maturity_years=7.0,
             coupon_rate=0.02, payment_frequency=2, quote_type="clean_price", quote_unit="PRICE_POINTS",
             quote_value=100.0, bid=99.9, ask=100.1),
    ]
    return pd.DataFrame(rows)


class TestCleaningPipeline(unittest.TestCase):
    def setUp(self) -> None:
        self.df = clean_market_data(build_synthetic_frame(), valuation_date=VALUATION_DATE)
        self.by_obs = self.df.set_index("obs_id")

    def test_action_domain(self) -> None:
        self.assertTrue(set(self.df["action"]).issubset({"keep", "correct", "downweight", "exclude"}))

    def test_scale_error_corrected(self) -> None:
        row = self.by_obs.loc["D3"]
        self.assertEqual(row["action"], "correct")
        self.assertAlmostEqual(row["normalized_quote"], 1.49, places=6)

    def test_stale_duplicate_excluded_fresh_kept(self) -> None:
        self.assertEqual(self.by_obs.loc["D4a", "action"], "exclude")
        self.assertIn(self.by_obs.loc["D4b", "action"], {"keep", "correct", "downweight"})

    def test_missing_quote_imputed(self) -> None:
        row = self.by_obs.loc["D5"]
        self.assertEqual(row["action"], "correct")
        self.assertAlmostEqual(row["normalized_quote"], 1.500, places=6)

    def test_crossed_bid_ask_reordered(self) -> None:
        self.assertEqual(self.by_obs.loc["D6", "action"], "correct")

    def test_wide_spread_downweighted_not_excluded(self) -> None:
        row = self.by_obs.loc["D7"]
        self.assertEqual(row["action"], "downweight")
        self.assertLess(row["weight"], 0.5)

    def test_uncorrectable_outlier_excluded(self) -> None:
        self.assertEqual(self.by_obs.loc["D8", "action"], "exclude")
        self.assertEqual(self.by_obs.loc["B4", "action"], "exclude")

    def test_swap_scale_error_corrected(self) -> None:
        row = self.by_obs.loc["S3"]
        self.assertEqual(row["action"], "correct")
        self.assertAlmostEqual(row["normalized_quote"], 2.29, places=6)

    def test_bond_scale_error_corrected_via_ytm(self) -> None:
        row = self.by_obs.loc["B3"]
        self.assertEqual(row["action"], "correct")
        self.assertAlmostEqual(row["normalized_quote"], 100.4, places=6)

    def test_excluded_rows_have_zero_weight(self) -> None:
        excluded = self.df[self.df["action"] == "exclude"]
        self.assertTrue((excluded["weight"] == 0.0).all())

    def test_every_row_has_a_reason_unless_untouched_keep(self) -> None:
        for _, row in self.df.iterrows():
            if row["action"] != "keep":
                self.assertTrue(len(row["reason"]) > 0, msg=row["obs_id"])


if __name__ == "__main__":
    unittest.main()
