from __future__ import annotations

import numpy as np
import pytest
from hullkit import bsm
from hullkit.surrogate_validation import (
    check_calendar_monotonicity,
    check_greek_consistency,
    check_nonnegative_gamma,
    check_price_bounds,
    check_put_call_parity,
    check_spot_monotonicity,
    check_strike_convexity,
    check_strike_monotonicity,
    validation_report,
)


def test_bsm_reference_grid_passes_all_hard_checks():
    strikes = np.linspace(70, 130, 121)
    call = bsm.call_price(100, strikes, 0.02, 0.25, 1.0, 0.0)
    put = bsm.put_price(100, strikes, 0.02, 0.25, 1.0, 0.0)
    maturities = np.linspace(0.05, 2.0, 80)
    calendar = bsm.call_price(100, 100, 0.02, 0.25, maturities, 0.0)
    spots = np.linspace(70, 130, 601)
    spot_price = bsm.call_price(spots, 100, 0.02, 0.25, 1.0, 0.0)
    checks = (
        check_price_bounds(call, 100, strikes, 0.02, 1.0, tolerance=1e-10),
        check_put_call_parity(call, put, 100, strikes, 0.02, 1.0, tolerance=1e-10),
        check_strike_monotonicity(call, strikes, tolerance=1e-10),
        check_strike_convexity(call, strikes, tolerance=1e-10),
        check_calendar_monotonicity(calendar, maturities, tolerance=1e-10),
        check_spot_monotonicity(spot_price, spots, tolerance=1e-10),
        check_nonnegative_gamma(bsm.gamma(spots, 100, 0.02, 0.25, 1.0), tolerance=1e-10),
        check_greek_consistency(
            spots,
            spot_price,
            bsm.call_delta(spots, 100, 0.02, 0.25, 1.0),
            bsm.gamma(spots, 100, 0.02, 0.25, 1.0),
            tolerance=2e-4,
        ),
    )
    report = validation_report(*checks)
    assert report.arbitrage_free
    assert all(check.n_violations == 0 for check in checks)


def test_broken_quotes_are_detected_with_magnitudes():
    strikes = np.array([90.0, 100.0, 110.0, 120.0])
    price = np.array([15.0, 10.0, 12.0, 1.0])
    monotonic = check_strike_monotonicity(price, strikes, tolerance=1e-12)
    convex = check_strike_convexity(price, strikes, tolerance=1e-12)
    bounds = check_price_bounds(np.array([101.0]), 100, 100, 0.0, 1.0, tolerance=1e-12)
    calendar = check_calendar_monotonicity([5.0, 4.0], [0.5, 1.0], tolerance=1e-12)
    parity = check_put_call_parity([10.0], [1.0], 100, 100, 0.0, 1.0, tolerance=1e-12)
    spot = check_spot_monotonicity([2.0, 1.0], [90.0, 100.0], tolerance=1e-12)
    gamma = check_nonnegative_gamma([0.1, -0.2], tolerance=1e-12)
    report = validation_report(monotonic, convex, bounds, calendar, parity, spot, gamma)
    assert not report.arbitrage_free
    assert all(check.n_violations >= 1 and check.max_violation > 0 for check in report.checks)
    assert all(
        set(check.to_dict()) >= {"n_checked", "n_violations", "max_violation", "tolerance"}
        for check in report.checks
    )


def test_grids_are_not_silently_sorted():
    with pytest.raises(ValueError, match="strictly increasing"):
        check_strike_monotonicity([1, 2, 3], [90, 110, 100])


def test_aggregate_requires_every_declared_applicable_check():
    spot = check_spot_monotonicity([1.0, 2.0], [90.0, 100.0])
    gamma = check_nonnegative_gamma([0.1, 0.2])
    expected = ("spot_monotonicity", "nonnegative_gamma")

    incomplete = validation_report(spot, applicable_checks=expected)
    complete = validation_report(spot, gamma, applicable_checks=expected)

    assert not incomplete.check_set_complete
    assert not incomplete.arbitrage_free
    assert complete.check_set_complete
    assert complete.arbitrage_free
