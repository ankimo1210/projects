from __future__ import annotations

import numpy as np
import pytest

from quantcurve.conventions import discount_from_simple_rate, discount_from_zero, ois_accruals, schedule_times


def test_forward_rule_integer_periods():
    np.testing.assert_allclose(schedule_times(3.0, 2, "forward"), [0.5, 1.0, 1.5, 2.0, 2.5, 3.0])
    np.testing.assert_allclose(schedule_times(2.0, 1, "forward"), [1.0, 2.0])
    np.testing.assert_allclose(schedule_times(1.0, 1, "forward"), [1.0])


def test_forward_rule_non_integer_periods():
    np.testing.assert_allclose(schedule_times(1.25, 1, "forward"), [1.25])
    np.testing.assert_allclose(schedule_times(1.5, 1, "forward"), [1.0, 1.5])
    np.testing.assert_allclose(schedule_times(6.11, 2, "forward"), list(np.arange(1, 12) / 2) + [6.11])
    np.testing.assert_allclose(schedule_times(6.966, 2, "forward"), list(np.arange(1, 14) / 2) + [6.966])


def test_other_rules():
    np.testing.assert_allclose(schedule_times(1.5, 1, "round"), [0.5, 1.5])
    np.testing.assert_allclose(schedule_times(1.5, 1, "linspace"), [0.75, 1.5])
    np.testing.assert_allclose(schedule_times(1.25, 1, "ceil"), [0.25, 1.25])
    np.testing.assert_allclose(schedule_times(1.5, 1, "ceil"), [0.5, 1.5])


def test_every_rule_ends_at_maturity_and_is_increasing():
    for rule in ("forward", "round", "linspace", "ceil"):
        for T in (0.3, 1.25, 1.5, 4.066, 13.73, 29.78):
            for f in (1, 2, 4):
                t = schedule_times(T, f, rule)
                assert t[-1] == pytest.approx(T)
                assert np.all(np.diff(t) > 0)
                assert t[0] > 0


def test_accruals_are_level():
    t = schedule_times(1.5, 1, "forward")
    np.testing.assert_allclose(ois_accruals(t, 1), [1.0, 1.0])
    np.testing.assert_allclose(ois_accruals(schedule_times(2.5, 2), 2), np.full(5, 0.5))


def test_invalid_inputs():
    with pytest.raises(ValueError):
        schedule_times(0.0, 1)
    with pytest.raises(ValueError):
        schedule_times(1.0, 0)
    with pytest.raises(ValueError):
        discount_from_simple_rate(-2.0, 1.0)


def test_negative_rate_discount_positive():
    assert discount_from_zero(-0.015, 30.0) > 1.0
    assert discount_from_simple_rate(-0.005, 0.5) > 1.0
