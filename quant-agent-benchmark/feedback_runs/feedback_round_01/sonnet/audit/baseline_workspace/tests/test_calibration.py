from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from quantcurve.calibration import (
    active_knots,
    build_holdout_split,
    fit_baseline,
    model_quote,
)
from quantcurve.curve import PiecewiseLinearZeroCurve

TRUE_KNOTS = np.array([1 / 12, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
TRUE_ZERO = np.array([0.015, 0.017, 0.019, 0.021, 0.023, 0.022, 0.020, 0.019])
TRUE_CURVE = PiecewiseLinearZeroCurve(TRUE_KNOTS, TRUE_ZERO)


def _synthetic_usable_frame(n_per_maturity: int = 1) -> pd.DataFrame:
    rows = []
    deposit_mats = [1 / 12, 0.25, 0.5, 1.0]
    swap_mats = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0]
    for i, t in enumerate(deposit_mats):
        rate = (1.0 / TRUE_CURVE.discount(t) - 1.0) / t
        rows.append(
            dict(obs_id=f"D{i}", instrument_id=f"DEP{i}", instrument_type="deposit", maturity_years=t,
                 coupon_rate=None, payment_frequency=1, normalized_quote=rate * 100.0, weight=1.0, action="keep")
        )
    from quantcurve.cashflows import payment_times, year_fractions

    for i, t in enumerate(swap_mats):
        freq = 1 if t <= 2 else 2
        times = payment_times(t, freq)
        alphas = year_fractions(times)
        discounts = np.array([TRUE_CURVE.discount(x) for x in times])
        annuity = float(np.sum(alphas * discounts))
        par = (1.0 - discounts[-1]) / annuity
        rows.append(
            dict(obs_id=f"S{i}", instrument_id=f"SWP{i}", instrument_type="ois_swap", maturity_years=t,
                 coupon_rate=None, payment_frequency=freq, normalized_quote=par * 100.0, weight=1.0, action="keep")
        )
    return pd.DataFrame(rows)


class TestHoldoutSplit(unittest.TestCase):
    def test_swap_buckets_never_split_across_train_and_holdout(self) -> None:
        df = _synthetic_usable_frame()
        # duplicate every swap maturity bucket 3x with independent instrument ids
        extra = []
        for _, row in df[df.instrument_type == "ois_swap"].iterrows():
            for k in range(2):
                clone = row.copy()
                clone["instrument_id"] = f"{row['instrument_id']}_dup{k}"
                clone["obs_id"] = f"{row['obs_id']}_dup{k}"
                extra.append(clone)
        df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

        split, holdout_mats = build_holdout_split(df)
        df = df.assign(split=split)
        swaps = df[df.instrument_type == "ois_swap"]
        for maturity, sub in swaps.groupby(swaps["maturity_years"].round(6)):
            self.assertEqual(sub["split"].nunique(), 1, msg=f"maturity {maturity} split across train/holdout")

    def test_active_knots_drops_only_excluded_maturities(self) -> None:
        knots = np.array([1.0, 2.0, 3.0, 5.0])
        pruned = active_knots(knots, {2.0})
        self.assertEqual(list(pruned), [1.0, 3.0, 5.0])
        unchanged = active_knots(knots, set())
        self.assertEqual(list(unchanged), list(knots))


class TestBaselineFit(unittest.TestCase):
    def test_recovers_known_curve_reasonably(self) -> None:
        df = _synthetic_usable_frame()
        knots = np.array([1 / 12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        fit = fit_baseline(df, knots=knots)
        probe = np.array([0.5, 2.0, 5.0, 10.0, 20.0])
        recovered = fit.curve.zero_rate(probe)
        truth = TRUE_CURVE.zero_rate(probe)
        np.testing.assert_allclose(recovered, truth, atol=5e-4)

    def test_deterministic_refit(self) -> None:
        df = _synthetic_usable_frame()
        knots = np.array([1 / 12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        fit1 = fit_baseline(df, knots=knots)
        fit2 = fit_baseline(df, knots=knots)
        np.testing.assert_allclose(fit1.curve.zero_rates, fit2.curve.zero_rates, atol=1e-12)

    def test_supports_negative_rate_environment(self) -> None:
        shocked = _synthetic_usable_frame().copy()
        shocked["normalized_quote"] = shocked["normalized_quote"] - 4.0  # push deep negative
        knots = np.array([1 / 12, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 15.0, 20.0, 25.0, 30.0])
        fit = fit_baseline(shocked, knots=knots)
        grid = np.linspace(knots[0], knots[-1], 500)
        self.assertTrue(np.any(fit.curve.zero_rate(grid) < 0))
        self.assertTrue(np.all(fit.curve.discount(grid) > 0))


if __name__ == "__main__":
    unittest.main()
