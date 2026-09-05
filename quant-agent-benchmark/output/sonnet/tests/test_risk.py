from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np

from quantcurve.curve import PiecewiseLinearZeroCurve
from quantcurve.grids import KEY_RATE_POINTS
from quantcurve.risk import dv01, key_rate_bump_shape, key_rate_sensitivities

KNOTS = np.array([1 / 12, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0])
CURVE = PiecewiseLinearZeroCurve(KNOTS, np.array([0.015, 0.017, 0.019, 0.021, 0.023, 0.022, 0.020, 0.019]))


class TestKeyRateBumpShape(unittest.TestCase):
    def test_partition_of_unity(self) -> None:
        grid = np.linspace(KNOTS[0], KNOTS[-1], 500)
        total = sum(key_rate_bump_shape(grid, i, KEY_RATE_POINTS) for i in range(len(KEY_RATE_POINTS)))
        np.testing.assert_allclose(total, np.ones_like(grid), atol=1e-10)

    def test_shape_is_one_at_its_own_key_rate(self) -> None:
        for i, k in enumerate(KEY_RATE_POINTS):
            shape = key_rate_bump_shape(np.array([k]), i, KEY_RATE_POINTS)
            self.assertAlmostEqual(shape[0], 1.0, places=10)

    def test_front_key_rate_is_flat_below_itself(self) -> None:
        shape = key_rate_bump_shape(np.array([0.1, 1.0, 1.9]), 0, KEY_RATE_POINTS)
        np.testing.assert_allclose(shape, np.ones(3))


def _instrument(instrument_type: str, maturity_years: float, quote: float, coupon: float = 0.02, freq: int = 2):
    return SimpleNamespace(
        instrument_type=instrument_type, maturity_years=maturity_years, normalized_quote=quote,
        coupon_rate=coupon, payment_frequency=freq,
    )


class TestDV01AndKeyRates(unittest.TestCase):
    def test_key_rate_sum_reconciles_with_parallel_dv01(self) -> None:
        for row in (
            _instrument("deposit", 0.5, 1.9),
            _instrument("ois_swap", 7.0, 2.1),
            _instrument("bond", 15.0, 101.0),
        ):
            parallel = dv01(row, CURVE)
            krs = key_rate_sensitivities(row, CURVE)
            self.assertAlmostEqual(sum(krs.values()), parallel, delta=abs(parallel) * 0.01 + 1e-6)

    def test_dv01_is_finite_and_nonzero_for_normal_instrument(self) -> None:
        row = _instrument("ois_swap", 10.0, 2.2)
        value = dv01(row, CURVE)
        self.assertTrue(np.isfinite(value))
        self.assertNotEqual(value, 0.0)


if __name__ == "__main__":
    unittest.main()
