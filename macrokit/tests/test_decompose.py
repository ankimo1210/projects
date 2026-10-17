from datetime import date

import numpy as np
import pytest

from macrokit.termstructure import decompose as dc

DATES = (date(2024, 7, 31), date(2024, 8, 30), date(2026, 6, 30))


def test_share_and_term_premium():
    d = dc.Decomposition("acm", DATES, np.array([1.0, 1.2, 2.0]), np.array([0.5, 0.6, 1.0]))
    assert d.share(DATES[0], DATES[2]) == pytest.approx(0.5)
    np.testing.assert_allclose(d.term_premium_pct, [0.5, 0.6, 1.0])


def test_share_refuses_a_flat_window():
    d = dc.Decomposition("acm", DATES, np.array([1.0, 1.2, 1.0]), np.zeros(3))
    with pytest.raises(ValueError, match="flat"):
        d.share(DATES[0], DATES[2])


def test_share_of_handles_bootstrap_rows():
    expected = np.array([[0.0, 1.0], [0.0, 2.0]])
    np.testing.assert_allclose(dc.share_of(expected, np.array([0.0, 2.0]), 0, 1), [0.5, 1.0])


def test_month_end_in_finds_the_dated_month():
    assert dc.month_end_in(DATES, 2024, 8) == date(2024, 8, 30)
    with pytest.raises(KeyError):
        dc.month_end_in(DATES, 2025, 1)


@pytest.mark.parametrize(
    ("shares", "label"),
    [
        ({"a": 0.35, "b": 0.65, "c": 0.5, "d": 0.4}, "robust_half"),
        ({"a": 0.7, "b": 0.9, "c": 0.66}, "expectations_dominant"),
        ({"a": 0.1, "b": 0.34, "c": -0.2}, "term_premium_dominant"),
        ({"a": 0.5, "b": 0.9, "c": 0.4}, "model_dependent"),
        ({"a": 0.5, "b": 0.5}, "undetermined"),
    ],
)
def test_verdict_table(shares, label):
    assert dc.verdict(shares) == label


def test_interval_is_the_5_to_95_percentile():
    lo, hi = dc.interval(np.arange(101.0))
    assert (lo, hi) == (5.0, 95.0)


def test_largest_rise_window():
    y = np.array([0.0, 1.0, 0.5, 3.0, 2.0])
    assert dc.largest_rise_window(y, 2) == (1, 3)
