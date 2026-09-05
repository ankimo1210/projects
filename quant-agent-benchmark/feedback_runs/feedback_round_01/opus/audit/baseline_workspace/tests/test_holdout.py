from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np

from quantcurve.cleaning import clean
from quantcurve.curve import PiecewiseFlatForwardCurve, SplineForwardCurve
from quantcurve.holdout import (
    HoldoutConfig,
    build_split,
    compare_models,
    forward_admissibility,
    maturity_blocks,
)
from quantcurve.io import load_market_data_with_audit
from quantcurve.models import FitConfig, fit_baseline, fit_metrics
from quantcurve.validation import validate
from synthetic import VALUATION_DATE, clean_frame, write_frame

FAST = FitConfig(lambda_grid=(1.0e-5, 1.0e-3), penalty_power_grid=(1.0,), cv_folds=3)


def instruments_from(frame, tmp):
    path = write_frame(frame, Path(tmp) / "market.csv")
    loaded = load_market_data_with_audit(path)
    report = validate(loaded, VALUATION_DATE)
    return clean(loaded, report, VALUATION_DATE).instruments


class TestMaturityBlocks(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_blocks_partition_every_instrument_exactly_once(self) -> None:
        blocks = maturity_blocks(self.instruments)
        flat = [i for block in blocks for i in block]
        self.assertEqual(sorted(flat), list(range(len(self.instruments))))

    def test_blocks_are_maturity_ordered(self) -> None:
        blocks = maturity_blocks(self.instruments)
        ends = [max(self.instruments[i].maturity_years for i in b) for b in blocks]
        starts = [min(self.instruments[i].maturity_years for i in b) for b in blocks]
        self.assertEqual(starts, sorted(starts))
        for end, start in zip(ends, starts[1:]):
            self.assertLess(end, start)

    def test_near_duplicate_maturities_share_a_block(self) -> None:
        # Two quotes 0.01Y apart must never end up on opposite sides of the split.
        config = HoldoutConfig(block_abs_gap_years=0.15, block_rel_gap=0.02)
        blocks = maturity_blocks(self.instruments, config)
        owner = {i: b for b, block in enumerate(blocks) for i in block}
        for a in range(len(self.instruments)):
            for b in range(a + 1, len(self.instruments)):
                gap = abs(
                    self.instruments[a].maturity_years - self.instruments[b].maturity_years
                )
                if gap <= 0.01:
                    self.assertEqual(owner[a], owner[b])


class TestSplit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)
        self.split = build_split(self.instruments)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_split_is_usable_and_disjoint(self) -> None:
        self.assertTrue(self.split.usable)
        train_ids = {i.obs_id for i in self.split.train}
        hold_ids = {i.obs_id for i in self.split.holdout}
        self.assertEqual(train_ids & hold_ids, set())
        self.assertEqual(
            len(train_ids) + len(hold_ids), len({i.obs_id for i in self.instruments})
        )

    def test_no_training_instrument_sits_next_to_a_holdout_one(self) -> None:
        """The anti-leakage property the whole design exists for."""
        config = HoldoutConfig()
        for held in self.split.holdout:
            threshold = max(
                config.block_abs_gap_years, config.block_rel_gap * held.maturity_years
            )
            nearest = min(
                abs(t.maturity_years - held.maturity_years) for t in self.split.train
            )
            self.assertGreater(nearest, threshold)

    def test_holdout_is_interior_so_the_metric_tests_interpolation(self) -> None:
        train_min = min(i.maturity_years for i in self.split.train)
        train_max = max(i.maturity_years for i in self.split.train)
        for held in self.split.holdout:
            self.assertGreater(held.maturity_years, train_min)
            self.assertLess(held.maturity_years, train_max)

    def test_first_and_last_blocks_are_never_withheld(self) -> None:
        self.assertNotIn(0, self.split.holdout_blocks)
        self.assertNotIn(len(self.split.blocks) - 1, self.split.holdout_blocks)

    def test_split_is_deterministic(self) -> None:
        again = build_split(self.instruments)
        self.assertEqual(
            [i.obs_id for i in self.split.holdout], [i.obs_id for i in again.holdout]
        )
        shuffled = list(reversed(self.instruments))
        third = build_split(shuffled)
        self.assertEqual(
            sorted(i.obs_id for i in self.split.holdout),
            sorted(i.obs_id for i in third.holdout),
        )

    def test_holdout_is_a_meaningful_fraction(self) -> None:
        share = len(self.split.holdout) / len(self.instruments)
        self.assertGreater(share, 0.05)
        self.assertLess(share, 0.45)

    def test_too_few_blocks_degrades_gracefully(self) -> None:
        split = build_split(self.instruments[:2])
        self.assertFalse(split.usable)
        self.assertEqual(split.method, "none")
        self.assertTrue(split.notes)
        self.assertEqual(len(split.train), 2)

    def test_few_blocks_hold_out_a_single_interior_block(self) -> None:
        config = HoldoutConfig(min_blocks=100)
        split = build_split(self.instruments, config)
        self.assertEqual(len(split.holdout_blocks), 1)
        self.assertTrue(any("single interior block" in n for n in split.notes))


class TestForwardAdmissibility(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.instruments = instruments_from(clean_frame(), self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_a_smooth_curve_inside_the_quoted_range_is_admissible(self) -> None:
        curve = SplineForwardCurve(np.array([0.1, 5.0, 30.0]), np.array([0.02, 0.025, 0.026]))
        check = forward_admissibility(curve, self.instruments, 30.0)
        self.assertTrue(check["admissible"])
        self.assertEqual(check["breach_percent"], 0.0)

    def test_a_sawtooth_forward_curve_is_rejected(self) -> None:
        pillars = np.array([1.0, 1.05, 2.0, 5.0, 30.0])
        forwards = np.array([0.02, -0.25, 0.30, 0.02, 0.02])
        curve = PiecewiseFlatForwardCurve(pillars, forwards)
        check = forward_admissibility(curve, self.instruments, 30.0)
        self.assertFalse(check["admissible"])
        self.assertGreater(check["breach_percent"], 2.0)

    def test_bounds_come_from_the_quoted_rates_plus_the_tolerance(self) -> None:
        curve = SplineForwardCurve(np.array([0.1, 30.0]), np.array([0.02, 0.02]))
        check = forward_admissibility(curve, self.instruments, 30.0, tolerance_percent=1.5)
        lo, hi = check["quoted_rate_range_percent"]
        self.assertAlmostEqual(check["lower_bound_percent"], lo - 1.5, places=12)
        self.assertAlmostEqual(check["upper_bound_percent"], hi + 1.5, places=12)

    def test_negative_forwards_are_admissible_when_the_quotes_are_negative(self) -> None:
        curve = SplineForwardCurve(np.array([0.1, 30.0]), np.array([-0.004, -0.003]))
        priced = [i.with_weight(i.weight) for i in self.instruments]
        for inst in priced:
            object.__setattr__(inst, "quote", -0.4)
        check = forward_admissibility(curve, priced, 30.0)
        self.assertTrue(check["admissible"])


class TestModelComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.instruments = instruments_from(clean_frame(), cls._tmp.name)
        cls.comparison = compare_models(cls.instruments, FAST)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_selection_is_one_of_the_two_models_with_a_rationale(self) -> None:
        self.assertIn(self.comparison.selected, {"baseline", "advanced"})
        self.assertGreater(len(self.comparison.rationale), 40)
        self.assertIsNotNone(self.comparison.selected_curve)

    def test_metrics_cover_train_holdout_and_full_sample(self) -> None:
        metrics = self.comparison.metrics
        for section in ("train", "holdout", "full_sample"):
            self.assertIn("baseline", metrics[section])
            self.assertIn("advanced", metrics[section])
            for model in ("baseline", "advanced"):
                self.assertTrue(np.isfinite(metrics[section][model]["weighted_rmse_bp"]))

    def test_holdout_models_never_saw_the_holdout_instruments(self) -> None:
        # The scored fits are the *train* fits, not the full-sample ones.
        self.assertIsNotNone(self.comparison.baseline_train)
        self.assertIsNotNone(self.comparison.advanced_train)
        train_ids = {i.obs_id for i in self.comparison.split.train}
        self.assertEqual(
            train_ids & {i.obs_id for i in self.comparison.split.holdout}, set()
        )

    def test_blocked_holdout_is_harder_than_a_random_split(self) -> None:
        """The reason the split is maturity-blocked rather than random.

        Give every maturity a second venue quote 0.5bp away.  Under a random
        split a withheld quote almost always leaves its near-identical sibling
        in the training set, so the "validation" error collapses to quote
        dispersion and would flatter any interpolating estimator.  The blocked
        split moves the whole pillar across together, so it measures what it
        claims to measure.
        """
        universe = list(self.instruments)
        for k, inst in enumerate(self.instruments):
            bump = 0.005 * (1.0 if k % 2 else -1.0)  # +/- 0.5bp on a rate quote
            universe.append(
                replace(
                    inst,
                    obs_id=f"DUP{k:04d}",
                    instrument_id=f"{inst.instrument_id}_B",
                    quote=inst.quote + (bump if inst.is_rate_quote else 0.02 * bump),
                    source="VENUE_Z",
                )
            )
        blocked = build_split(universe)
        self.assertTrue(blocked.usable)
        blocked_error = fit_metrics(
            fit_baseline(blocked.train, FAST).curve, blocked.holdout
        )["weighted_rmse_bp"]

        rng = np.random.default_rng(20260115)
        order = rng.permutation(len(universe))
        held = set(order[: len(blocked.holdout)].tolist())
        random_train = [i for k, i in enumerate(universe) if k not in held]
        random_hold = [i for k, i in enumerate(universe) if k in held]
        random_error = fit_metrics(
            fit_baseline(random_train, FAST).curve, random_hold
        )["weighted_rmse_bp"]

        self.assertGreater(
            blocked_error,
            3.0 * random_error,
            f"blocked {blocked_error:.3f}bp vs random {random_error:.3f}bp",
        )

    def test_the_spline_forward_curve_is_smoother_than_the_bootstrap(self) -> None:
        roughness = self.comparison.metrics["forward_roughness"]
        self.assertLess(roughness["advanced"], roughness["baseline"])

    def test_admissibility_is_recorded_for_both_models(self) -> None:
        gate = self.comparison.metrics["forward_admissibility"]
        for model in ("baseline", "advanced"):
            self.assertIn("admissible", gate[model])
            self.assertIn("breach_percent", gate[model])

    def test_when_both_are_admissible_the_margin_rule_decides(self) -> None:
        # Clean, smooth data: both forward curves pass the gate, so selection
        # falls to the maturity-blocked holdout plus the parsimony margin.
        gate = self.comparison.metrics["forward_admissibility"]
        self.assertTrue(gate["baseline"]["admissible"])
        self.assertTrue(gate["advanced"]["admissible"])
        holdout = self.comparison.metrics["holdout"]
        improvement = (
            holdout["baseline"]["weighted_rmse_bp"]
            - holdout["advanced"]["weighted_rmse_bp"]
        ) / holdout["baseline"]["weighted_rmse_bp"]
        self.assertGreater(improvement, HoldoutConfig().selection_margin)
        self.assertEqual(self.comparison.selected, "advanced")
        self.assertIn("margin", self.comparison.rationale)

    def test_a_prohibitive_margin_keeps_the_simpler_estimator(self) -> None:
        # The parsimony margin is a real constraint, not decoration: raise it
        # beyond any achievable improvement and the bootstrap must be retained.
        strict = compare_models(
            self.instruments, FAST, HoldoutConfig(selection_margin=0.999)
        )
        self.assertEqual(strict.selected, "baseline")
        self.assertIn("simpler", strict.rationale)

    def test_an_inadmissible_curve_is_rejected_whatever_it_reprices(self) -> None:
        # The gate has to be able to overturn the accuracy ranking; tighten it
        # below what either curve can satisfy and the rationale must say so.
        strict = compare_models(
            self.instruments, FAST, HoldoutConfig(forward_tolerance_percent=0.0)
        )
        gate = strict.metrics["forward_admissibility"]
        self.assertFalse(gate["baseline"]["admissible"])
        self.assertFalse(gate["advanced"]["admissible"])
        self.assertIn(strict.selected, {"baseline", "advanced"})
        self.assertGreater(gate["baseline"]["breach_percent"], 0.0)
        self.assertGreater(gate["advanced"]["breach_percent"], 0.0)

    def test_deterministic(self) -> None:
        again = compare_models(self.instruments, FAST)
        self.assertEqual(again.selected, self.comparison.selected)
        np.testing.assert_allclose(
            again.metrics["full_sample"]["advanced"]["weighted_rmse_bp"],
            self.comparison.metrics["full_sample"]["advanced"]["weighted_rmse_bp"],
            rtol=0,
            atol=0,
        )


if __name__ == "__main__":
    unittest.main()
