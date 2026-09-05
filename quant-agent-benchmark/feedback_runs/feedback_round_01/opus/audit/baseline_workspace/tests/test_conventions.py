from __future__ import annotations

import math
import unittest

import numpy as np

from quantcurve.conventions import (
    annual_frequency_for_swap,
    bond_schedule,
    period_count,
    schedule_backward,
    swap_schedule,
)


class TestPeriodCount(unittest.TestCase):
    def test_whole_periods(self) -> None:
        self.assertEqual(period_count(5.0, 2), 10)
        self.assertEqual(period_count(1.0, 1), 1)
        self.assertEqual(period_count(30.0, 2), 60)

    def test_stub_rounds_to_nearest(self) -> None:
        # 1.25Y annual: one period.  2.44Y semiannual: five periods.  These are
        # the two cases that pin the convention down against the supplied quotes.
        self.assertEqual(period_count(1.25, 1), 1)
        self.assertEqual(period_count(2.440754, 2), 5)
        self.assertEqual(period_count(1.508434, 2), 3)

    def test_rounds_half_away_from_zero(self) -> None:
        self.assertEqual(period_count(1.5, 1), 2)
        self.assertEqual(period_count(2.5, 1), 3)

    def test_floor_of_one_period(self) -> None:
        self.assertEqual(period_count(0.08333333, 1), 1)

    def test_invalid_inputs_rejected(self) -> None:
        with self.assertRaises(ValueError):
            period_count(0.0, 2)
        with self.assertRaises(ValueError):
            period_count(5.0, 0)
        with self.assertRaises(ValueError):
            period_count(float("nan"), 2)


class TestSchedules(unittest.TestCase):
    def test_backward_from_maturity(self) -> None:
        times = schedule_backward(2.5, 2)
        np.testing.assert_allclose(times, [0.5, 1.0, 1.5, 2.0, 2.5])

    def test_last_payment_is_maturity(self) -> None:
        for maturity in (0.75, 1.25, 1.508434, 7.0, 29.783214):
            for frequency in (1, 2, 4):
                times = schedule_backward(maturity, frequency)
                self.assertAlmostEqual(float(times[-1]), maturity, places=12)
                self.assertTrue(np.all(times > 0.0))
                self.assertTrue(np.all(np.diff(times) > 0.0))

    def test_stub_schedule_has_one_payment(self) -> None:
        np.testing.assert_allclose(schedule_backward(1.25, 1), [1.25])

    def test_swap_schedule_returns_accrual(self) -> None:
        times, accrual = swap_schedule(3.0, 2)
        self.assertAlmostEqual(accrual, 0.5)
        self.assertEqual(len(times), 6)

    def test_bond_schedule_matches_backward(self) -> None:
        np.testing.assert_allclose(bond_schedule(4.25, 2), schedule_backward(4.25, 2))

    def test_documented_ois_frequency(self) -> None:
        self.assertEqual(annual_frequency_for_swap(1.0), 1)
        self.assertEqual(annual_frequency_for_swap(2.0), 1)
        self.assertEqual(annual_frequency_for_swap(2.5), 2)
        self.assertEqual(annual_frequency_for_swap(30.0), 2)


class TestConventionsAgainstSuppliedQuotes(unittest.TestCase):
    """The rounding rule is not a free choice; the supplied quotes select it."""

    def test_ceil_and_floor_are_both_rejected(self) -> None:
        # ceil would give the 1.25Y annual swap two periods, floor would give the
        # 2.44Y semiannual bond four.  round satisfies both simultaneously.
        self.assertEqual(math.ceil(1.25 * 1), 2)
        self.assertEqual(math.floor(2.440754 * 2), 4)
        self.assertEqual(period_count(1.25, 1), 1)
        self.assertEqual(period_count(2.440754, 2), 5)


if __name__ == "__main__":
    unittest.main()
