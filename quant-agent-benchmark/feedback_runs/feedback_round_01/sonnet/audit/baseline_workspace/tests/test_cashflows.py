from __future__ import annotations

import math
import unittest

from quantcurve.cashflows import (
    bond_cashflows,
    bond_model_price,
    bond_ytm,
    deposit_model_rate,
    payment_times,
    swap_model_par_rate,
    year_fractions,
)


def flat_discount(zero_rate: float):
    return lambda t: math.exp(-zero_rate * t)


class TestPaymentSchedules(unittest.TestCase):
    def test_deposit_like_single_period(self) -> None:
        times = payment_times(1.0, frequency=1)
        self.assertEqual(list(times), [1.0])

    def test_stub_when_not_exact_multiple(self) -> None:
        times = payment_times(1.25, frequency=1)
        self.assertEqual(len(times), 2)
        self.assertAlmostEqual(times[0], 1.0)
        self.assertAlmostEqual(times[-1], 1.25)
        alphas = year_fractions(times)
        self.assertAlmostEqual(sum(alphas), 1.25)

    def test_semiannual_no_stub(self) -> None:
        times = payment_times(2.5, frequency=2)
        self.assertEqual(len(times), 5)
        self.assertAlmostEqual(times[-1], 2.5)
        alphas = year_fractions(times)
        for a in alphas:
            self.assertAlmostEqual(a, 0.5)

    def test_rejects_non_positive_inputs(self) -> None:
        with self.assertRaises(ValueError):
            payment_times(0.0, 1)
        with self.assertRaises(ValueError):
            payment_times(1.0, 0)


class TestInstrumentPricing(unittest.TestCase):
    def test_deposit_model_rate_matches_flat_curve_definition(self) -> None:
        z = 0.02
        discount_fn = flat_discount(z)
        T = 0.5
        rate = deposit_model_rate(discount_fn, T)
        implied_discount = 1.0 / (1.0 + rate * T)
        self.assertAlmostEqual(implied_discount, discount_fn(T), places=10)

    def test_swap_par_rate_reprices_to_par(self) -> None:
        discount_fn = flat_discount(0.025)
        par_rate = swap_model_par_rate(discount_fn, 5.0, frequency=2)
        # Reconstruct the annuity/PV identity directly.
        times = payment_times(5.0, 2)
        alphas = year_fractions(times)
        annuity = sum(a * discount_fn(t) for a, t in zip(alphas, times))
        self.assertAlmostEqual(par_rate * annuity, 1.0 - discount_fn(5.0), places=10)

    def test_bond_price_matches_manual_sum(self) -> None:
        discount_fn = flat_discount(0.02)
        price = bond_model_price(discount_fn, 3.0, coupon_rate=0.03, frequency=2)
        times, amounts = bond_cashflows(3.0, 0.03, 2)
        expected = sum(a * discount_fn(t) for a, t in zip(amounts, times))
        self.assertAlmostEqual(price, expected, places=10)

    def test_bond_ytm_round_trip(self) -> None:
        true_yield = 0.035
        times, amounts = bond_cashflows(7.0, coupon_rate=0.04, frequency=2)
        price = sum(a * (1.0 + true_yield / 2) ** (-2 * t) for a, t in zip(amounts, times))
        solved = bond_ytm(7.0, coupon_rate=0.04, frequency=2, price=price)
        self.assertAlmostEqual(solved, true_yield, places=8)

    def test_bond_ytm_handles_negative_yield(self) -> None:
        true_yield = -0.01
        times, amounts = bond_cashflows(2.0, coupon_rate=0.02, frequency=2)
        price = sum(a * (1.0 + true_yield / 2) ** (-2 * t) for a, t in zip(amounts, times))
        solved = bond_ytm(2.0, coupon_rate=0.02, frequency=2, price=price)
        self.assertAlmostEqual(solved, true_yield, places=8)


if __name__ == "__main__":
    unittest.main()
