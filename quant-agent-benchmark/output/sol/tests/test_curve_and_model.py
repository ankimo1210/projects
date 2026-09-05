from __future__ import annotations

import numpy as np

from quantcurve.cleaning import clean_market_data
from quantcurve.conventions import discount_array_from_zero
from quantcurve.curve import ZeroCurve
from quantcurve.modeling import fit_advanced, fit_baseline

from helpers import make_market_frame


def test_positive_discount_and_negative_rate_support() -> None:
    curve = ZeroCurve(np.array([0.0, 2.0, 30.0]), np.array([-0.01, -0.005, 0.02]))
    grid = np.linspace(0, 30, 1001)
    assert np.all(curve.discount(grid) > 0)
    assert curve.discount(1.0) > 1.0


def test_zero_discount_forward_transform_consistency() -> None:
    curve = ZeroCurve(np.array([0.0, 2.0, 5.0, 30.0]), np.array([0.01, 0.02, 0.015, 0.025]))
    grid = np.linspace(0.05, 29.95, 2000)
    zero = np.asarray(curve.zero(grid))
    discount = discount_array_from_zero(zero, grid)
    assert np.max(np.abs(-np.log(discount) / grid - zero)) < 1e-13
    numerical_forward = -np.gradient(np.log(discount), grid, edge_order=2)
    assert np.max(np.abs(numerical_forward[2:-2] - curve.forward(grid)[2:-2])) < 2e-5


def test_curve_continuity_at_knots() -> None:
    curve = ZeroCurve(np.array([0.0, 1.0, 5.0, 30.0]), np.array([0.01, 0.03, 0.015, 0.025]))
    for knot in (1.0, 5.0):
        assert abs(curve.zero(knot - 1e-8) - curve.zero(knot + 1e-8)) < 1e-8


def test_advanced_fit_is_reproducible_and_numerically_stable() -> None:
    cleaned = clean_market_data(make_market_frame(), "2026-01-15")
    rows = cleaned.usable.reset_index(drop=True)
    baseline = fit_baseline(rows)
    first = fit_advanced(rows, initial_curve=baseline.curve)
    second = fit_advanced(rows, initial_curve=baseline.curve)
    assert first.success and second.success
    assert np.array_equal(first.curve.rates, second.curve.rates)
    grid = np.linspace(0, 30, 500)
    assert np.isfinite(first.curve.zero(grid)).all()
    assert np.isfinite(first.curve.forward(grid)).all()
    assert np.all(first.curve.discount(grid) > 0)
