from __future__ import annotations

import unittest

import numpy as np

from quantcurve.conventions import BASIS_POINT
from quantcurve.curve import SplineForwardCurve
from quantcurve.instruments import Instrument
from quantcurve.pricing import instrument_pv, swap_par_rate
from quantcurve.conventions import swap_schedule
from quantcurve.risk import (
    KEY_TENORS,
    analytic_dv01,
    dv01,
    instrument_risk,
    key_rate_sensitivities,
    parallel_bump,
    tent_bump,
    verify_dv01,
)
from synthetic import NelsonSiegel, NelsonSiegelCurve, bond_quote, deposit_quote, swap_quote


def make(kind: str, maturity: float, quote: float, coupon=None, frequency=1) -> Instrument:
    return Instrument(
        obs_id="OBS0001",
        instrument_id="INS0001",
        instrument_type=kind,
        maturity_years=maturity,
        coupon_rate=coupon,
        payment_frequency=frequency,
        quote=quote,
        half_spread=0.001,
        liquidity_score=1.0,
        weight=1.0,
        source="VENUE_A",
        timestamp="2026-01-15T15:00:00Z",
    )


TRUTH = NelsonSiegel()
CURVE = NelsonSiegelCurve(TRUTH)

PORTFOLIO = [
    make("deposit", 0.25, deposit_quote(TRUTH, 0.25)),
    make("deposit", 1.0, deposit_quote(TRUTH, 1.0)),
    make("ois_swap", 2.0, swap_quote(TRUTH, 2.0), frequency=1),
    make("ois_swap", 5.0, swap_quote(TRUTH, 5.0), frequency=2),
    make("ois_swap", 10.0, swap_quote(TRUTH, 10.0), frequency=2),
    make("ois_swap", 30.0, swap_quote(TRUTH, 30.0), frequency=2),
    make("bond", 4.6, bond_quote(TRUTH, 4.6, 0.028, 2), coupon=0.028, frequency=2),
    make("bond", 26.4, bond_quote(TRUTH, 26.4, 0.030, 2), coupon=0.030, frequency=2),
]


class TestBumpShapes(unittest.TestCase):
    def test_parallel_bump_is_constant(self) -> None:
        bump = parallel_bump(1e-4)
        np.testing.assert_allclose(bump(np.array([0.1, 5.0, 40.0])), 1e-4)

    def test_tents_form_a_partition_of_unity(self) -> None:
        grid = np.linspace(0.01, 45.0, 900)
        total = sum(tent_bump(k, 1.0)(grid) for k in range(len(KEY_TENORS)))
        np.testing.assert_allclose(total, 1.0, atol=1e-12)

    def test_each_tent_peaks_at_its_own_tenor(self) -> None:
        for index, tenor in enumerate(KEY_TENORS):
            shape = tent_bump(index, 1.0)
            self.assertAlmostEqual(float(shape(np.array([tenor]))[0]), 1.0, places=12)
            for other_index, other in enumerate(KEY_TENORS):
                if other_index != index:
                    self.assertAlmostEqual(float(shape(np.array([other]))[0]), 0.0, places=12)

    def test_first_and_last_tents_are_flat_outside_the_range(self) -> None:
        self.assertAlmostEqual(float(tent_bump(0, 1.0)(np.array([0.01]))[0]), 1.0)
        self.assertAlmostEqual(float(tent_bump(3, 1.0)(np.array([45.0]))[0]), 1.0)

    def test_out_of_range_index_rejected(self) -> None:
        with self.assertRaises(IndexError):
            tent_bump(4, 1e-4)


class TestDV01(unittest.TestCase):
    def test_finite_difference_matches_the_analytic_derivative(self) -> None:
        for inst in PORTFOLIO:
            check = verify_dv01(CURVE, inst)
            self.assertLess(
                abs(check["relative_difference"]),
                1e-5,
                f"{inst.instrument_type} {inst.maturity_years}Y: {check}",
            )

    def test_receiver_dv01_is_positive(self) -> None:
        for inst in PORTFOLIO:
            self.assertGreater(dv01(CURVE, inst), 0.0)

    def test_dv01_grows_with_maturity(self) -> None:
        swaps = [i for i in PORTFOLIO if i.instrument_type == "ois_swap"]
        values = [dv01(CURVE, i) for i in swaps]
        self.assertEqual(values, sorted(values))

    def test_one_year_swap_dv01_is_about_one_bp_of_notional(self) -> None:
        inst = make("ois_swap", 1.0, swap_quote(TRUTH, 1.0), frequency=1)
        self.assertAlmostEqual(dv01(CURVE, inst), 100.0, delta=1.0)

    def test_bond_dv01_uses_face_100(self) -> None:
        bond = [i for i in PORTFOLIO if i.instrument_type == "bond"][0]
        self.assertLess(dv01(CURVE, bond), 1.0)
        self.assertGreater(dv01(CURVE, bond), 0.0)

    def test_definition_is_the_documented_central_difference(self) -> None:
        inst = PORTFOLIO[3]
        down = instrument_pv(CURVE.bumped(parallel_bump(-BASIS_POINT)), inst)
        up = instrument_pv(CURVE.bumped(parallel_bump(+BASIS_POINT)), inst)
        self.assertAlmostEqual(dv01(CURVE, inst), 0.5 * (down - up), places=12)


class TestKeyRates(unittest.TestCase):
    def test_key_rates_sum_to_the_parallel_dv01(self) -> None:
        for inst in PORTFOLIO:
            record = instrument_risk(CURVE, inst)
            self.assertLess(
                abs(record.key_sum_error),
                1e-4,
                f"{inst.instrument_type} {inst.maturity_years}Y: "
                f"{record.key_rate_sum} vs {record.dv01}",
            )

    def test_short_instruments_load_on_the_two_year_bucket(self) -> None:
        inst = make("ois_swap", 2.0, swap_quote(TRUTH, 2.0), frequency=1)
        keys = key_rate_sensitivities(CURVE, inst)
        self.assertGreater(keys["key_2y"], 0.9 * dv01(CURVE, inst))
        self.assertAlmostEqual(keys["key_10y"], 0.0, places=8)
        self.assertAlmostEqual(keys["key_30y"], 0.0, places=8)

    def test_thirty_year_swap_loads_mostly_on_the_thirty_year_bucket(self) -> None:
        inst = make("ois_swap", 30.0, swap_quote(TRUTH, 30.0), frequency=2)
        keys = key_rate_sensitivities(CURVE, inst)
        self.assertEqual(max(keys, key=lambda k: keys[k]), "key_30y")

    def test_all_key_rates_finite(self) -> None:
        for inst in PORTFOLIO:
            keys = key_rate_sensitivities(CURVE, inst)
            self.assertTrue(all(np.isfinite(v) for v in keys.values()))


class TestAnalyticDerivative(unittest.TestCase):
    def test_deposit_analytic_matches_closed_form(self) -> None:
        inst = make("deposit", 0.5, deposit_quote(TRUTH, 0.5))
        discount = float(CURVE.discount(np.array([0.5]))[0])
        expected = 0.5 * 1_000_000.0 * (1.0 + inst.quote / 100.0 * 0.5) * discount * 1e-4
        self.assertAlmostEqual(analytic_dv01(CURVE, inst), expected, places=9)

    def test_par_swap_dv01_equals_the_annuity(self) -> None:
        # At par the receiver DV01 is the PV01 of the fixed leg plus the float
        # leg's own sensitivity; both are captured by the analytic formula.
        inst = make("ois_swap", 10.0, swap_quote(TRUTH, 10.0), frequency=2)
        times, accrual = swap_schedule(10.0, 2)
        par = swap_par_rate(CURVE, times, accrual)
        self.assertAlmostEqual(inst.quote / 100.0, par, places=12)
        discounts = np.asarray(CURVE.discount(times))
        expected = 1_000_000.0 * 1e-4 * (
            par * accrual * float(np.sum(times * discounts))
            + float(times[-1] * discounts[-1])
        )
        self.assertAlmostEqual(analytic_dv01(CURVE, inst), expected, places=8)

    def test_unsupported_type_rejected(self) -> None:
        inst = make("future", 1.0, 1.0)
        with self.assertRaises(ValueError):
            analytic_dv01(CURVE, inst)


class TestRiskOnAFittedCurve(unittest.TestCase):
    def test_works_on_a_spline_curve_too(self) -> None:
        knots = np.array([0.1, 1.0, 5.0, 15.0, 30.0])
        curve = SplineForwardCurve(knots, np.array([0.012, 0.018, 0.024, 0.022, 0.02]))
        for inst in PORTFOLIO:
            record = instrument_risk(curve, inst)
            self.assertGreater(record.dv01, 0.0)
            self.assertLess(abs(record.key_sum_error), 1e-4)
            self.assertLess(abs(record.analytic_error), 1e-5)

    def test_works_with_negative_rates(self) -> None:
        curve = SplineForwardCurve(np.array([0.1, 30.0]), np.array([-0.01, -0.005]))
        for inst in PORTFOLIO:
            record = instrument_risk(curve, inst)
            self.assertTrue(np.isfinite(record.dv01))
            self.assertLess(abs(record.key_sum_error), 1e-4)


if __name__ == "__main__":
    unittest.main()
