from __future__ import annotations

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from quantcurve.cleaning import (
    ACTIONS,
    CleaningConfig,
    apply_exclusions,
    clean,
    estimate_model_error,
    reweight_instruments,
)
from quantcurve.io import MarketDataError, load_market_data_with_audit
from quantcurve.validation import (
    FLAG_COLUMNS,
    ValidationConfig,
    parse_valuation_date,
    peer_scale_factor,
    validate,
)
from synthetic import VALUATION_DATE, clean_frame, dirty_frame, write_frame


def load(frame: pd.DataFrame, tmp: str):
    path = write_frame(frame, Path(tmp) / "market.csv")
    return load_market_data_with_audit(path)


class TestValuationDateParsing(unittest.TestCase):
    def test_iso_date(self) -> None:
        self.assertEqual(parse_valuation_date("2026-01-15").date().isoformat(), "2026-01-15")

    def test_rejects_nonsense(self) -> None:
        for text in ("", "   ", "15/01/2026", "not-a-date"):
            with self.assertRaises(MarketDataError):
                parse_valuation_date(text)


class TestCleanDataPassesValidation(unittest.TestCase):
    def test_no_flags_on_clean_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load(clean_frame(), tmp)
            report = validate(loaded, VALUATION_DATE)
        raised = {name: count for name, count in report.summary.items() if count}
        self.assertEqual(raised, {}, f"unexpected flags on clean data: {raised}")

    def test_every_row_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load(clean_frame(), tmp)
            report = validate(loaded, VALUATION_DATE)
            result = clean(loaded, report, VALUATION_DATE)
        self.assertEqual(result.summary["keep"], len(loaded.frame))
        self.assertEqual(len(result.instruments), len(loaded.frame))


class TestDefectDetection(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.loaded = load(dirty_frame(), self._tmp.name)
        self.report = validate(self.loaded, VALUATION_DATE)
        self.result = clean(self.loaded, self.report, VALUATION_DATE)
        self.audit = self.result.audit.set_index("obs_id")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _row_for(self, instrument_type: str, maturity: float) -> pd.Series:
        frame = self.loaded.frame
        mask = (frame["instrument_type"] == instrument_type) & np.isclose(
            frame["maturity_years"], maturity
        )
        obs = frame.loc[mask, "obs_id"].tolist()
        return self.audit.loc[obs[0]]

    def test_unit_error_is_detected_and_corrected(self) -> None:
        self.assertTrue(self.report.flags["suspect_unit_scale"].any())
        row = self._row_for("deposit", 0.25)
        self.assertEqual(row["action"], "correct")
        self.assertIn("rescaled", row["reason"])
        self.assertAlmostEqual(row["normalized_quote"], row["raw_quote"] * 100.0, places=9)

    def test_missing_quote_is_rebuilt_from_the_mid(self) -> None:
        self.assertEqual(int(self.report.flags["missing_quote"].sum()), 1)
        row = self._row_for("ois_swap", 5.0)
        self.assertEqual(row["action"], "correct")
        self.assertIn("bid/ask mid", row["reason"])
        self.assertTrue(np.isfinite(row["normalized_quote"]))

    def test_crossed_market_is_uncrossed(self) -> None:
        self.assertEqual(int(self.report.flags["crossed_market"].sum()), 1)
        row = self._row_for("ois_swap", 10.0)
        self.assertEqual(row["action"], "correct")
        self.assertIn("crossed", row["reason"])
        self.assertLess(row["normalized_bid"], row["normalized_ask"])

    def test_wide_and_illiquid_market_is_downweighted(self) -> None:
        row = self._row_for("ois_swap", 20.0)
        self.assertEqual(row["action"], "downweight")
        weights = [i.weight for i in self.result.instruments]
        target = [i.weight for i in self.result.instruments
                  if i.instrument_type == "ois_swap" and i.maturity_years == 20.0][0]
        self.assertLess(target, float(np.median(weights)))

    def test_duplicate_is_superseded_by_the_fresher_quote(self) -> None:
        self.assertEqual(self.audit.loc["DUP0001", "action"], "exclude")
        self.assertIn("duplicate", self.audit.loc["DUP0001", "reason"])
        self.assertNotIn("DUP0001", {i.obs_id for i in self.result.instruments})

    def test_stale_observation_is_excluded(self) -> None:
        stale = self.audit[self.audit["reason"].str.contains("stale quote")]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale.iloc[0]["action"], "exclude")

    def test_every_action_is_from_the_mandated_vocabulary(self) -> None:
        self.assertTrue(set(self.result.audit["action"]).issubset(set(ACTIONS)))

    def test_every_row_has_a_reason(self) -> None:
        self.assertTrue((self.result.audit["reason"].str.len() > 0).all())

    def test_audit_covers_every_input_row(self) -> None:
        self.assertEqual(len(self.result.audit), len(self.loaded.frame))
        self.assertEqual(
            sorted(self.result.audit["obs_id"]), sorted(self.loaded.frame["obs_id"])
        )

    def test_excluded_rows_carry_zero_weight(self) -> None:
        excluded = self.result.audit[self.result.audit["action"] == "exclude"]
        self.assertTrue((excluded["weight"] == 0.0).all())

    def test_kept_rows_carry_positive_weight(self) -> None:
        kept = self.result.audit[self.result.audit["action"] != "exclude"]
        self.assertTrue((kept["weight"] > 0.0).all())


class TestValidationRangeChecks(unittest.TestCase):
    def _flags(self, mutate) -> pd.DataFrame:
        frame = clean_frame()
        mutate(frame)
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load(frame, tmp)
            return validate(loaded, VALUATION_DATE).flags

    def test_unknown_instrument_type(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("instrument_type",
                                                    f["instrument_type"].mask(
                                                        f.index == 0, "future")))
        self.assertTrue(flags["unknown_instrument_type"].iloc[0])

    def test_non_positive_maturity(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("maturity_years",
                                                    f["maturity_years"].mask(f.index == 1, -1.0)))
        self.assertTrue(flags["bad_maturity"].iloc[1])

    def test_unparseable_number(self) -> None:
        def mutate(frame):
            frame["quote_value"] = frame["quote_value"].astype(object)
            frame.loc[2, "quote_value"] = "abc"
        flags = self._flags(mutate)
        self.assertTrue(flags["unparseable_number"].iloc[2])

    def test_forward_starting_is_flagged(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("start_years",
                                                    f["start_years"].mask(f.index == 3, 1.0)))
        self.assertTrue(flags["forward_starting"].iloc[3])

    def test_bad_frequency(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("payment_frequency",
                                                    f["payment_frequency"].mask(f.index == 4, 7)))
        self.assertTrue(flags["bad_frequency"].iloc[4])

    def test_liquidity_out_of_range(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("liquidity_score",
                                                    f["liquidity_score"].mask(f.index == 0, 1.5)))
        self.assertTrue(flags["bad_liquidity"].iloc[0])

    def test_future_timestamp(self) -> None:
        stamp = (VALUATION_DATE + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        flags = self._flags(lambda f: f.__setitem__("timestamp",
                                                    f["timestamp"].mask(f.index == 0, stamp)))
        self.assertTrue(flags["future_timestamp"].iloc[0])

    def test_bond_without_coupon(self) -> None:
        def mutate(frame):
            bonds = frame.index[frame["instrument_type"] == "bond"]
            frame.loc[bonds[0], "coupon_rate"] = ""
        flags = self._flags(mutate)
        self.assertTrue(flags["missing_coupon"].any())

    def test_quote_type_mismatch(self) -> None:
        flags = self._flags(lambda f: f.__setitem__("quote_type",
                                                    f["quote_type"].mask(f.index == 0, "par_rate")))
        self.assertTrue(flags["unexpected_quote_type"].iloc[0])

    def test_all_flag_columns_exist(self) -> None:
        flags = self._flags(lambda f: None)
        self.assertEqual(tuple(flags.columns), FLAG_COLUMNS)


class TestUnitScaleDetection(unittest.TestCase):
    def test_steep_curve_is_not_misdiagnosed(self) -> None:
        """A 1M rate two orders below a 30Y rate must not be 'rescaled'."""
        frame = pd.DataFrame(
            {
                "instrument_type": ["deposit"] * 4 + ["ois_swap"] * 4,
                "maturity_years": [0.083, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
            }
        )
        quotes = pd.Series([0.02, 0.06, 0.15, 0.40, 0.9, 1.8, 2.4, 3.0])
        factors = peer_scale_factor(frame, frame["instrument_type"], quotes)
        np.testing.assert_allclose(factors, 1.0)

    def test_genuine_decimal_slip_is_caught(self) -> None:
        frame = pd.DataFrame(
            {
                "instrument_type": ["ois_swap"] * 6,
                "maturity_years": [2.0, 2.0, 2.0, 5.0, 5.0, 5.0],
            }
        )
        quotes = pd.Series([2.30, 2.31, 0.0229, 2.28, 2.29, 2.30])
        factors = peer_scale_factor(frame, frame["instrument_type"], quotes)
        self.assertAlmostEqual(factors[2], 100.0)
        self.assertTrue(np.all(np.delete(factors, 2) == 1.0))


class TestWeightingAndErrorModel(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        loaded = load(dirty_frame(), self._tmp.name)
        report = validate(loaded, VALUATION_DATE)
        self.result = clean(loaded, report, VALUATION_DATE)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_weights_are_finite_and_positive(self) -> None:
        weights = np.array([i.weight for i in self.result.instruments])
        self.assertTrue(np.all(np.isfinite(weights)))
        self.assertTrue(np.all(weights > 0.0))

    def test_tighter_market_earns_more_weight(self) -> None:
        wide = [i for i in self.result.instruments
                if i.instrument_type == "ois_swap" and i.maturity_years == 20.0][0]
        tight = [i for i in self.result.instruments
                 if i.instrument_type == "ois_swap" and i.maturity_years == 15.0][0]
        self.assertLess(wide.weight, tight.weight)

    def test_model_error_reflects_residual_dispersion(self) -> None:
        residuals = np.zeros(len(self.result.instruments))
        bonds = [k for k, i in enumerate(self.result.instruments)
                 if i.instrument_type == "bond"]
        residuals[bonds] = np.linspace(-6.0, 6.0, len(bonds))
        errors = estimate_model_error(self.result.instruments, residuals)
        self.assertGreater(errors["bond"], errors["ois_swap"])
        self.assertGreaterEqual(errors["ois_swap"], CleaningConfig().min_model_error_bp)

    def test_reweighting_penalises_the_noisier_type(self) -> None:
        errors = {"deposit": 0.25, "ois_swap": 0.25, "bond": 5.0}
        reweighted = reweight_instruments(self.result.instruments, errors)
        bond = np.median([i.weight for i in reweighted if i.instrument_type == "bond"])
        swap = np.median([i.weight for i in reweighted if i.instrument_type == "ois_swap"])
        self.assertLess(bond, swap / 5.0)

    def test_apply_exclusions_is_recorded(self) -> None:
        victim = self.result.instruments[0].obs_id
        updated = apply_exclusions(self.result, {victim: "test exclusion"})
        row = updated.audit.set_index("obs_id").loc[victim]
        self.assertEqual(row["action"], "exclude")
        self.assertEqual(row["weight"], 0.0)
        self.assertIn("test exclusion", row["reason"])
        self.assertNotIn(victim, {i.obs_id for i in updated.instruments})


class TestUnusableInput(unittest.TestCase):
    def test_all_rows_rejected_raises(self) -> None:
        frame = clean_frame()
        frame["maturity_years"] = -1.0
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load(frame, tmp)
            report = validate(loaded, VALUATION_DATE)
            with self.assertRaises(MarketDataError):
                clean(loaded, report, VALUATION_DATE)

    def test_unsupported_types_only_raises(self) -> None:
        frame = clean_frame()
        frame["instrument_type"] = "future"
        with tempfile.TemporaryDirectory() as tmp:
            loaded = load(frame, tmp)
            with self.assertRaises(MarketDataError):
                validate(loaded, VALUATION_DATE)

    def test_empty_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.csv"
            clean_frame().head(0).to_csv(path, index=False)
            with self.assertRaises(MarketDataError):
                load_market_data_with_audit(path)


if __name__ == "__main__":
    unittest.main()
