import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import QuantLib as ql  # noqa: N813 — upstream's conventional Python alias

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "owner"))
from datasets import GRID, create_suite, outside_git, rates
from evaluate_curves import evaluate, score_frame
from prepare_run import KIT, hashes, prepare
from pricing import pv, quote, schedule
from quantlib_baseline import NODE_DAYS, NODE_TIMES, DiscountCurve, fit


class PricingTests(unittest.TestCase):
    def test_stub_schedule(self):
        for t, m, expected in (
            (1.25, 1, [1, 1.25]),
            (0.1, 2, [0.1]),
            (2.0, 2, [0.5, 1, 1.5, 2]),
            (10.2, 2, [*np.arange(0.5, 10.1, 0.5), 10.2]),
        ):
            times, alpha = schedule(t, m)
            np.testing.assert_allclose(times, expected)
            self.assertAlmostEqual(sum(alpha), t)
            self.assertTrue(np.all(alpha > 0))

    def test_invalid_schedule(self):
        for t, m in ((0, 2), (np.nan, 1), (-1, 2), (1, 0), (1, 1.5), (1, 999999)):
            with self.assertRaises(ValueError):
                schedule(t, m)

    def test_independent_quantlib_flat_pricing(self):
        # Independent loops, no shared schedule/quote function on expected side.
        for rate in (-0.01, 0.0, 0.03):
            flat = ql.FlatForward(ql.Date(15, 1, 2026), rate, ql.Actual365Fixed(), ql.Continuous)
            for t in (0.1, 1.25, 2.0, 10.2, 30.0):
                for kind in ("deposit", "ois_swap", "bond"):
                    m = 1 if kind == "deposit" or (kind == "ois_swap" and t <= 2) else 2
                    row = dict(
                        maturity_years=t,
                        payment_frequency=m,
                        coupon_rate=0.027,
                        instrument_type=kind,
                    )
                    annuity, previous = 0.0, 0.0
                    for k in range(1, math.ceil(t * m) + 1):
                        pay = min(k / m, t)
                        annuity += (pay - previous) * flat.discount(pay)
                        previous = pay
                    dt = flat.discount(t)
                    expected = (
                        100 * (1 / dt - 1) / t
                        if kind == "deposit"
                        else (
                            100 * (1 - dt) / annuity
                            if kind == "ois_swap"
                            else 100 * (0.027 * annuity + dt)
                        )
                    )

                    def df(x, rate=rate):
                        return np.exp(-rate * np.asarray(x))

                    self.assertAlmostEqual(quote(row, df), expected, places=10)
                    self.assertAlmostEqual(pv(row, df, expected), 0, places=7)

    def test_legacy_mismatch_is_detectable(self):
        t, m, c, r = 10.2, 2, 0.027, 0.03
        legacy_times = np.arange(1, round(t * m) + 1) / m
        legacy = 100 * c / m * np.exp(-r * legacy_times).sum() + 100 * np.exp(-r * legacy_times[-1])
        new = quote(
            dict(maturity_years=t, payment_frequency=m, coupon_rate=c, instrument_type="bond"),
            lambda x: np.exp(-r * np.asarray(x)),
        )
        self.assertGreater(abs(legacy - new), 0.01)

    def test_zero_coupon_and_dv01(self):
        row = dict(
            maturity_years=10.2, payment_frequency=2, coupon_rate=0.0, instrument_type="bond"
        )
        for r in (-0.01, 0.03):

            def df(x, r=r):
                return np.exp(-r * np.asarray(x))

            self.assertAlmostEqual(quote(row, df), 100 * np.exp(-r * 10.2))

            def down(x, r=r):
                return np.exp(-(r - 0.0001) * np.asarray(x))

            def up(x, r=r):
                return np.exp(-(r + 0.0001) * np.asarray(x))

            self.assertGreater((pv(row, down, 100) - pv(row, up, 100)) / 2, 0)

    def test_quantlib_loglinear_interpolation(self):
        z = np.linspace(-0.01, 0.03, len(NODE_DAYS) - 1)
        curve = DiscountCurve(z)
        logdf = np.r_[0, -NODE_TIMES[1:] * z]
        expected = np.exp(np.interp(GRID, NODE_TIMES, logdf))
        np.testing.assert_allclose(curve.discount(GRID), expected, rtol=1e-13)

    def test_fit_clean_flat(self):
        rows = []

        def df(x):
            return np.exp(-0.023 * np.asarray(x))

        # Identify every node; a sparse short end cannot uniquely recover a
        # flat curve without adding a prior. Do not test an unidentified truth.
        for t in np.unique(np.r_[NODE_TIMES[1:], np.linspace(0.1, 30, 40)]):
            row = dict(
                maturity_years=t,
                payment_frequency=1 if t <= 2 else 2,
                coupon_rate=0.03,
                instrument_type="ois_swap",
            )
            q = quote(row, df)
            row.update(quote_value=q, bid=q - 0.01, ask=q + 0.01)
            rows.append(row)
        curve, info = fit(pd.DataFrame(rows))
        self.assertTrue(info["converged"])
        self.assertLess(np.max(np.abs(curve.frame().zero_rate - 0.023)), 1e-6)


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="quant-round2-test-")
        cls.root = Path(cls.temp.name)
        cls.suite = create_suite(cls.root / "suite", seed=8123)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_reproducibility_and_new_truth(self):
        second = create_suite(self.root / "same", seed=8123)
        third = create_suite(self.root / "different", seed=8124)
        first = json.loads((self.suite / "manifest.json").read_text())["hashes"]
        self.assertEqual(first, json.loads((second / "manifest.json").read_text())["hashes"])
        self.assertNotEqual(
            first["case_01/truth_curve.csv"],
            json.loads((third / "manifest.json").read_text())["hashes"]["case_01/truth_curve.csv"],
        )

    def test_quality_and_holdout_separation(self):
        manifest = json.loads((self.suite / "manifest.json").read_text())
        self.assertEqual(len(manifest["cases"]), 13)
        for case in manifest["cases"]:
            directory = self.suite / case["case_id"]
            market = pd.read_csv(directory / "market_observations.csv")
            holdout = pd.read_csv(directory / "holdout.csv")
            self.assertTrue(market.obs_id.is_unique)
            self.assertGreater(market.instrument_id.duplicated().sum(), 0)
            self.assertTrue(set(market.instrument_id).isdisjoint(holdout.instrument_id))
            self.assertNotIn("true_quote", market.columns)
            truth = pd.read_csv(directory / "truth_curve.csv")
            self.assertTrue(np.isfinite(truth.to_numpy()).all())
            self.assertTrue((truth.discount_factor > 0).all())

    def test_analytic_forward(self):
        p = json.loads((self.suite / "case_01/parameters.json").read_text())
        h = 1e-5
        finite = ((GRID + h) * rates(GRID + h, p)[0] - (GRID - h) * rates(GRID - h, p)[0]) / (2 * h)
        np.testing.assert_allclose(finite, rates(GRID, p)[1], atol=1e-9)

    def test_private_location_and_overwrite(self):
        with self.assertRaises(ValueError):
            outside_git(KIT / "private")
        with self.assertRaises(FileExistsError):
            create_suite(self.suite)

    def test_truth_scores_and_invalid_outputs(self):
        truth = pd.read_csv(self.suite / "case_01/truth_curve.csv")
        holdout = pd.read_csv(self.suite / "case_01/holdout.csv")
        result = score_frame(truth, truth, holdout)
        self.assertAlmostEqual(result["zero_rmse_bp"], 0)
        self.assertAlmostEqual(result["forward_rmse_bp"], 0)
        for changed in (
            truth.iloc[:20],
            truth.iloc[::-1],
            truth.assign(discount_factor=-1),
            truth.assign(zero_rate=np.nan),
        ):
            with self.assertRaises(ValueError):
                score_frame(changed, truth, holdout)

    def test_missing_case_not_dropped(self):
        result = evaluate(self.suite, self.root / "missing_predictions")
        self.assertEqual(result["failed_fraction"], 1)
        self.assertIsNone(result["macro_mean"])
        self.assertFalse(result["comparable"])


if __name__ == "__main__":
    unittest.main()
