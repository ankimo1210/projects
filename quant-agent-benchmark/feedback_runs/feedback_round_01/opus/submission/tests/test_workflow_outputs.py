from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from quantcurve.io import MarketDataError
from quantcurve.models import FitConfig
from quantcurve.outputs import (
    CLEANING_COLUMNS,
    CURVE_COLUMNS,
    REPRICING_COLUMNS,
    RISK_COLUMNS,
    write_outputs,
)
from quantcurve.workflow import WorkflowConfig, run_workflow
from synthetic import VALUATION_DATE, clean_frame, dirty_frame, negative_rate_frame, write_frame

FAST = WorkflowConfig(
    fit=FitConfig(lambda_grid=(1.0e-5, 1.0e-3), penalty_power_grid=(1.0,), cv_folds=3),
)


def run_on(frame, tmp: Path, config: WorkflowConfig = FAST):
    path = write_frame(frame, tmp / "market.csv")
    return run_workflow(path, VALUATION_DATE, config)


class TestWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.result = run_on(dirty_frame(), cls.tmp)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_every_input_row_appears_exactly_once_in_the_cleaning_audit(self) -> None:
        frame = dirty_frame()
        audit = self.result.cleaning.audit
        self.assertEqual(len(audit), len(frame))
        self.assertEqual(sorted(audit["obs_id"]), sorted(frame["obs_id"]))

    def test_cleaning_actions_are_from_the_documented_vocabulary(self) -> None:
        allowed = {"keep", "correct", "downweight", "exclude"}
        self.assertTrue(set(self.result.cleaning.audit["action"]) <= allowed)

    def test_every_audit_row_carries_a_reason(self) -> None:
        reasons = self.result.cleaning.audit["reason"].astype(str)
        self.assertTrue(all(len(r.strip()) > 0 for r in reasons))

    def test_calibrating_instruments_are_exactly_the_non_excluded_rows(self) -> None:
        audit = self.result.cleaning.audit
        kept = set(audit.loc[audit["action"] != "exclude", "obs_id"])
        self.assertEqual({i.obs_id for i in self.result.instruments}, kept)

    def test_curve_table_meets_the_output_contract(self) -> None:
        table = self.result.curve_table
        self.assertGreaterEqual(len(table), 361)
        self.assertLessEqual(table["maturity_years"].iloc[0], 1.0 / 12.0 + 1e-12)
        self.assertGreaterEqual(table["maturity_years"].iloc[-1], 30.0 - 1e-12)
        self.assertTrue(table["maturity_years"].is_monotonic_increasing)
        self.assertTrue((table["discount_factor"] > 0).all())
        self.assertTrue(np.isfinite(table[list(CURVE_COLUMNS)].to_numpy()).all())

    def test_zero_rate_and_discount_factor_are_mutually_consistent(self) -> None:
        table = self.result.curve_table
        implied = np.exp(-table["zero_rate"] * table["maturity_years"])
        np.testing.assert_allclose(implied, table["discount_factor"], rtol=1e-12)

    def test_forward_rate_integrates_back_to_the_zero_rate(self) -> None:
        """z(T) = (1/T) * integral of f, checked on the published columns alone.

        The tolerance is the trapezoid rule's own error on the published grid
        (0.006bp at its worst, in the uniform segment around 3Y), not a slack
        allowance: a real inconsistency between the three columns would be orders
        of magnitude larger.
        """
        table = self.result.curve_table
        t = table["maturity_years"].to_numpy()
        f = table["forward_rate"].to_numpy()
        # The grid starts at 1/12Y; the missing [0, t0] piece is flat-forward.
        integral = f[0] * t[0] + np.concatenate(
            [[0.0], np.cumsum(np.diff(t) * 0.5 * (f[1:] + f[:-1]))]
        )
        np.testing.assert_allclose(
            integral / t, table["zero_rate"].to_numpy(), atol=1e-6
        )

    def test_the_grid_is_fine_enough_that_a_consumer_can_interpolate(self) -> None:
        """The published rows must resolve the curve, not just span it.

        A uniform grid is far too coarse at the front: linear interpolation of
        ``zero_rate`` between uniformly spaced rows costs 0.55bp inside the first
        six months, which is bigger than every money-market repricing residual in
        the file and is purely an artefact of publication.
        """
        table = self.result.curve_table
        t = table["maturity_years"].to_numpy()
        z = table["zero_rate"].to_numpy()
        curve = self.result.curve
        mid = 0.5 * (t[:-1] + t[1:])
        linear = 0.5 * (z[:-1] + z[1:])
        error_bp = np.abs(linear - np.asarray(curve.zero(mid))) * 1.0e4
        self.assertLess(float(error_bp.max()), 0.05)
        front = mid < 0.5
        self.assertLess(float(error_bp[front].max()), 0.01)

    def test_repricing_covers_every_calibrating_instrument(self) -> None:
        self.assertEqual(len(self.result.repricing), len(self.result.instruments))
        self.assertEqual(
            set(self.result.repricing["instrument_id"]),
            {i.instrument_id for i in self.result.instruments},
        )

    def test_repricing_residual_is_market_minus_model_in_input_units(self) -> None:
        frame = self.result.repricing
        np.testing.assert_allclose(
            frame["residual"], frame["market_quote"] - frame["model_quote"], rtol=1e-12
        )

    def test_risk_covers_every_calibrating_instrument(self) -> None:
        self.assertEqual(
            set(self.result.risk["instrument_id"]),
            {i.instrument_id for i in self.result.instruments},
        )
        self.assertTrue((self.result.risk["dv01"] > 0).all())

    def test_key_rates_sum_to_dv01_in_the_published_table(self) -> None:
        risk = self.result.risk
        total = risk[["key_2y", "key_5y", "key_10y", "key_30y"]].sum(axis=1)
        np.testing.assert_allclose(total, risk["dv01"], rtol=2e-3, atol=1e-6)

    def test_sensitivity_reports_at_least_three_named_checks(self) -> None:
        checks = self.result.sensitivity["checks"]
        self.assertGreaterEqual(len(checks), 3)
        self.assertEqual(len({c["name"] for c in checks}), len(checks))
        for check in checks:
            self.assertTrue(check["name"])
            self.assertGreater(len(check["description"]), 30)
            self.assertTrue(check["metric"])
            self.assertTrue(np.isfinite(check["value"]), check["name"])
            self.assertIsInstance(check["detail"], dict)

    def test_model_comparison_records_the_selection_and_its_rule(self) -> None:
        payload = self.result.model_comparison
        self.assertIn(payload["model_selected"], {"baseline", "advanced"})
        self.assertIn("selection_rule", payload)
        self.assertGreater(len(payload["selection_rationale"]), 40)
        self.assertIn("holdout", payload)

    def test_the_injected_defects_are_all_caught(self) -> None:
        frame = dirty_frame()
        audit = self.result.cleaning.audit.set_index("obs_id")

        def action_for(instrument_type: str, maturity: float) -> tuple[str, str]:
            rows = frame[
                (frame["instrument_type"] == instrument_type)
                & (np.isclose(frame["maturity_years"], maturity))
            ]
            self.assertGreaterEqual(len(rows), 1)
            obs = rows["obs_id"].iloc[0]
            return str(audit.loc[obs, "action"]), str(audit.loc[obs, "reason"])

        # Each of the seven injected defects must produce a non-"keep" action
        # carrying a reason that names it.
        for kind, maturity, marker in (
            ("deposit", 0.25, "scale"),      # decimal instead of percent
            ("ois_swap", 5.0, "mid"),        # missing quote rebuilt from bid/ask
            ("ois_swap", 10.0, "cross"),     # crossed bid/ask
            ("ois_swap", 20.0, "width"),     # wide and illiquid
        ):
            action, reason = action_for(kind, maturity)
            self.assertNotEqual(action, "keep", f"{kind} {maturity}Y")
            self.assertIn(marker, reason.lower(), f"{kind} {maturity}Y: {reason}")

        self.assertNotEqual(str(audit.loc["DUP0001", "action"]), "keep")
        self.assertIn("duplicate", str(audit.loc["DUP0001", "reason"]).lower())

        stale = frame[frame["source"] == "VENUE_B"]
        stale = stale[np.isclose(stale["maturity_years"], 3.0)]["obs_id"].iloc[0]
        self.assertNotEqual(str(audit.loc[stale, "action"]), "keep")
        self.assertIn("stale", str(audit.loc[stale, "reason"]).lower())

        excluded = audit[audit["action"] == "exclude"]
        self.assertTrue(
            any("outlier" in str(r).lower() for r in excluded["reason"]),
            "the 40bp 7Y swap was never excluded as an outlier",
        )

    def test_negative_rate_dataset_produces_positive_discount_factors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_on(negative_rate_frame(), Path(tmp))
        table = result.curve_table
        self.assertTrue((table["discount_factor"] > 0).all())
        self.assertLess(table["zero_rate"].max(), 0.0)
        self.assertGreater(table["discount_factor"].min(), 1.0)

    def test_a_file_with_no_usable_rows_raises_an_actionable_error(self) -> None:
        frame = clean_frame()
        frame["quote_value"] = ""
        frame["bid"] = ""
        frame["ask"] = ""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MarketDataError) as ctx:
                run_on(frame, Path(tmp))
        message = str(ctx.exception)
        self.assertIn("rejected by validation", message)
        self.assertIn("quote_value", message)

    def test_a_file_with_a_single_usable_row_names_the_audit_trail(self) -> None:
        frame = clean_frame()
        for column in ("quote_value", "bid", "ask"):
            frame[column] = frame[column].astype(object)
            frame.loc[frame.index[1:], column] = ""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(MarketDataError) as ctx:
                run_on(frame, Path(tmp))
        self.assertIn("cleaning.csv", str(ctx.exception))

    def test_grid_configuration_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                run_on(clean_frame(), Path(tmp), WorkflowConfig(grid_points=100))
            with self.assertRaises(ValueError):
                run_on(clean_frame(), Path(tmp), WorkflowConfig(grid_max_years=0.01))


class TestWriteOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.result = run_on(dirty_frame(), cls.tmp)
        cls.paths = write_outputs(cls.result, cls.tmp / "outputs")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_all_contract_files_exist_and_are_non_empty(self) -> None:
        expected = {
            "curves/curve.csv",
            "diagnostics/cleaning.csv",
            "diagnostics/repricing.csv",
            "diagnostics/risk.csv",
            "diagnostics/model_comparison.json",
            "diagnostics/sensitivity.json",
        }
        root = self.tmp / "outputs"
        for relative in expected:
            path = root / relative
            self.assertTrue(path.exists(), relative)
            self.assertGreater(path.stat().st_size, 0, relative)

    def test_required_columns_come_first_and_in_order(self) -> None:
        root = self.tmp / "outputs"
        for name, required in (
            ("curves/curve.csv", CURVE_COLUMNS),
            ("diagnostics/cleaning.csv", CLEANING_COLUMNS),
            ("diagnostics/repricing.csv", REPRICING_COLUMNS),
            ("diagnostics/risk.csv", RISK_COLUMNS),
        ):
            columns = pd.read_csv(root / name, nrows=0).columns.tolist()
            self.assertEqual(columns[: len(required)], list(required), name)

    def test_json_outputs_are_sorted_and_reloadable(self) -> None:
        for name in ("model_comparison.json", "sensitivity.json"):
            text = (self.tmp / "outputs" / "diagnostics" / name).read_text()
            payload = json.loads(text)
            self.assertEqual(text, json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def test_writing_twice_is_byte_identical(self) -> None:
        second = write_outputs(self.result, self.tmp / "outputs_again")
        for key, path in self.paths.items():
            self.assertEqual(
                path.read_bytes(), second[key].read_bytes(), f"{key} is not reproducible"
            )

    def test_a_short_grid_is_rejected_by_the_contract_check(self) -> None:
        result = self.result
        trimmed = result.curve_table.iloc[:100].copy()
        original, result.curve_table = result.curve_table, trimmed
        try:
            with self.assertRaises(ValueError):
                write_outputs(result, self.tmp / "outputs_short")
        finally:
            result.curve_table = original

    def test_a_negative_discount_factor_is_rejected_by_the_contract_check(self) -> None:
        result = self.result
        broken = result.curve_table.copy()
        broken.loc[broken.index[10], "discount_factor"] = -1.0
        original, result.curve_table = result.curve_table, broken
        try:
            with self.assertRaises(ValueError):
                write_outputs(result, self.tmp / "outputs_negative")
        finally:
            result.curve_table = original

    def test_floats_are_written_with_enough_precision_to_round_trip(self) -> None:
        table = pd.read_csv(self.tmp / "outputs" / "curves" / "curve.csv")
        np.testing.assert_allclose(
            table["discount_factor"],
            np.exp(-table["zero_rate"] * table["maturity_years"]),
            rtol=1e-9,
        )
        self.assertTrue(
            all(math.isfinite(v) for v in table["forward_rate"].to_numpy())
        )


if __name__ == "__main__":
    unittest.main()
