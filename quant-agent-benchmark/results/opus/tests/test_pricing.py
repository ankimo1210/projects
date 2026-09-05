from __future__ import annotations

import unittest

import numpy as np

from quantcurve.conventions import bond_schedule, swap_schedule
from quantcurve.curve import SplineForwardCurve
from quantcurve.instruments import Instrument
from quantcurve.pricing import (
    CalibrationSet,
    bond_cashflows,
    bond_price,
    deposit_pv,
    deposit_simple_rate,
    model_quote,
    residual_bp,
    swap_par_rate,
    swap_receiver_pv,
)
from synthetic import NelsonSiegel, NelsonSiegelCurve, bond_quote, deposit_quote, swap_quote


def flat_curve(rate: float) -> SplineForwardCurve:
    return SplineForwardCurve(np.array([0.05, 30.0]), np.array([rate, rate]))


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


class TestDeposits(unittest.TestCase):
    def test_simple_rate_inverts_the_documented_formula(self) -> None:
        curve = flat_curve(0.03)
        rate = deposit_simple_rate(curve, 0.5)
        discount = float(curve.discount(np.array([0.5]))[0])
        self.assertAlmostEqual(discount, 1.0 / (1.0 + rate * 0.5), places=14)

    def test_pv_is_zero_at_the_market_rate(self) -> None:
        curve = flat_curve(0.025)
        rate = deposit_simple_rate(curve, 0.75)
        self.assertAlmostEqual(deposit_pv(curve, 0.75, rate, 1_000_000.0), 0.0, places=6)

    def test_pv_rises_when_the_fixed_rate_rises(self) -> None:
        curve = flat_curve(0.025)
        rate = deposit_simple_rate(curve, 1.0)
        self.assertGreater(deposit_pv(curve, 1.0, rate + 1e-4, 1_000_000.0), 0.0)


class TestSwaps(unittest.TestCase):
    def test_par_rate_makes_the_receiver_pv_vanish(self) -> None:
        curve = flat_curve(0.021)
        times, accrual = swap_schedule(7.0, 2)
        par = swap_par_rate(curve, times, accrual)
        self.assertAlmostEqual(
            swap_receiver_pv(curve, times, accrual, par, 1_000_000.0), 0.0, places=6
        )

    def test_one_year_swap_matches_the_one_year_deposit(self) -> None:
        # With a single annual payment r = (1 - D) / D, which is exactly the
        # simple one-year deposit rate.
        curve = flat_curve(0.019)
        times, accrual = swap_schedule(1.0, 1)
        self.assertAlmostEqual(
            swap_par_rate(curve, times, accrual), deposit_simple_rate(curve, 1.0), places=14
        )

    def test_receiver_gains_when_rates_fall(self) -> None:
        curve = flat_curve(0.02)
        lower = flat_curve(0.019)
        times, accrual = swap_schedule(10.0, 2)
        par = swap_par_rate(curve, times, accrual)
        self.assertGreater(
            swap_receiver_pv(lower, times, accrual, par, 1_000_000.0), 0.0
        )


class TestBonds(unittest.TestCase):
    def test_par_coupon_prices_at_par_on_a_flat_curve(self) -> None:
        # On a flat continuously compounded curve the coupon that prices at 100
        # is the semiannual-compounded equivalent of the zero rate.
        rate = 0.03
        curve = flat_curve(rate)
        coupon = 2.0 * (np.exp(rate / 2.0) - 1.0)
        times = bond_schedule(10.0, 2)
        self.assertAlmostEqual(bond_price(curve, times, coupon, 2), 100.0, places=8)

    def test_cashflows_include_principal_once(self) -> None:
        times = bond_schedule(3.0, 2)
        flows = bond_cashflows(times, 0.04, 2)
        self.assertEqual(len(flows), 6)
        np.testing.assert_allclose(flows[:-1], 2.0)
        self.assertAlmostEqual(float(flows[-1]), 102.0)

    def test_zero_coupon_bond_is_the_discount_factor(self) -> None:
        curve = flat_curve(0.02)
        times = bond_schedule(5.0, 2)
        self.assertAlmostEqual(
            bond_price(curve, times, 0.0, 2),
            100.0 * float(curve.discount(np.array([5.0]))[0]),
            places=10,
        )


class TestRoundTripAgainstAKnownCurve(unittest.TestCase):
    """Quotes generated from a curve must reprice on that curve to zero."""

    def setUp(self) -> None:
        self.truth = NelsonSiegel()
        self.curve = NelsonSiegelCurve(self.truth)

    def test_deposit_round_trip(self) -> None:
        for tenor in (1 / 12, 0.5, 1.0):
            inst = make("deposit", tenor, deposit_quote(self.truth, tenor))
            self.assertLess(abs(residual_bp(self.curve, inst)), 1e-8)

    def test_swap_round_trip(self) -> None:
        for tenor in (1.0, 2.0, 5.0, 30.0):
            frequency = 1 if tenor <= 2 else 2
            inst = make("ois_swap", tenor, swap_quote(self.truth, tenor), frequency=frequency)
            self.assertLess(abs(residual_bp(self.curve, inst)), 1e-8)

    def test_bond_round_trip(self) -> None:
        for maturity, coupon in ((2.4, 0.021), (12.7, 0.026), (26.4, 0.030)):
            inst = make("bond", maturity, bond_quote(self.truth, maturity, coupon, 2),
                        coupon=coupon, frequency=2)
            self.assertLess(abs(residual_bp(self.curve, inst)), 1e-6)


class TestSplineApproximatesAKnownCurve(unittest.TestCase):
    def test_dense_spline_reproduces_nelson_siegel(self) -> None:
        truth = NelsonSiegel()
        knots = np.exp(np.linspace(np.log(0.001), np.log(30.0), 60))
        spline = SplineForwardCurve(knots, truth.forward(knots))
        grid = np.linspace(0.02, 30.0, 300)
        error_bp = np.abs(spline.zero(grid) - truth.zero(grid)) * 1e4
        self.assertLess(float(np.max(error_bp)), 0.02)

    def test_front_extrapolation_error_is_bounded_and_understood(self) -> None:
        # Below the first knot the forward is held flat, which costs
        # approximately f'(0) * t0^2 / (2 T) in the zero rate.  The bound matters
        # because the shortest deposit sits exactly at the first knot.
        truth = NelsonSiegel()
        for first in (0.01, 0.001):
            knots = np.exp(np.linspace(np.log(first), np.log(30.0), 60))
            spline = SplineForwardCurve(knots, truth.forward(knots))
            grid = np.array([2.0 * first])
            error = float(np.abs(spline.zero(grid) - truth.zero(grid))[0])
            slope = float(
                (truth.forward(np.array([first])) - truth.forward(np.array([0.0])))[0]
            ) / first
            self.assertLess(error, 1.5 * slope * first**2 / (2.0 * grid[0]))


class TestCalibrationSet(unittest.TestCase):
    def setUp(self) -> None:
        truth = NelsonSiegel()
        self.instruments = [
            make("deposit", 0.5, deposit_quote(truth, 0.5)),
            make("ois_swap", 5.0, swap_quote(truth, 5.0), frequency=2),
            make("bond", 8.3, bond_quote(truth, 8.3, 0.019, 2), coupon=0.019, frequency=2),
        ]
        self.curve = flat_curve(0.022)

    def test_vectorised_quotes_match_the_scalar_implementation(self) -> None:
        calset = CalibrationSet(self.instruments)
        vector = calset.model_quotes(self.curve)
        scalar = np.array([model_quote(self.curve, i) for i in self.instruments])
        np.testing.assert_allclose(vector, scalar, rtol=1e-13, atol=1e-13)

    def test_vectorised_residuals_match_the_scalar_implementation(self) -> None:
        calset = CalibrationSet(self.instruments)
        vector = calset.residuals_bp(self.curve)
        scalar = np.array([residual_bp(self.curve, i) for i in self.instruments])
        np.testing.assert_allclose(vector, scalar, rtol=1e-12, atol=1e-12)

    def test_bond_residual_sign_is_yield_equivalent(self) -> None:
        # A market price above the model price means the market yield is *lower*.
        truth = NelsonSiegel()
        rich = make("bond", 8.3, bond_quote(truth, 8.3, 0.019, 2) + 1.0,
                    coupon=0.019, frequency=2)
        self.assertLess(residual_bp(self.curve, rich), residual_bp(self.curve,
                        make("bond", 8.3, bond_quote(truth, 8.3, 0.019, 2),
                             coupon=0.019, frequency=2)))

    def test_empty_set_is_handled(self) -> None:
        calset = CalibrationSet([])
        self.assertEqual(calset.n, 0)
        self.assertEqual(calset.residuals_bp(self.curve).size, 0)


if __name__ == "__main__":
    unittest.main()
