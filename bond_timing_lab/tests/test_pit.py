import pandas as pd
import pytest
from bond_timing.pit import (
    LookaheadError,
    check_embargo,
    check_fit_window,
    check_observed,
    check_targets_complete,
    check_vintage,
    training_starts,
    validation_split,
)


def month(text: str) -> pd.Period:
    return pd.Period(text, "M")


def test_r1_rejects_rows_after_the_decision():
    check_observed([month("2000-01"), month("2000-02")], month("2000-02"))
    with pytest.raises(LookaheadError):
        check_observed([month("2000-01"), month("2000-03")], month("2000-02"))


def test_r1_rejects_a_vintage_not_yet_published():
    check_vintage(month("2000-05"), month("2000-06"))
    for vintage in (month("2000-06"), month("2000-07")):
        with pytest.raises(LookaheadError):
            check_vintage(vintage, month("2000-06"))


def test_r2_keeps_only_completed_targets():
    starts = pd.period_range("1990-01", "2000-12", freq="M")
    assert training_starts(starts, month("2000-12"), 12).max() == month("1999-12")
    assert training_starts(starts, month("2000-12"), 1).max() == month("2000-11")


def test_r2_check_rejects_an_unrealized_target():
    with pytest.raises(LookaheadError):
        check_targets_complete(pd.PeriodIndex([month("2000-01")]), month("2000-06"), 12)


def test_v0_mode_keeps_unrealized_targets():
    starts = pd.period_range("1990-01", "2000-12", freq="M")
    assert training_starts(starts, month("2000-12"), 12, complete=False).max() == month("2000-11")


def test_r3_embargo_leaves_h_months_between_fitting_and_validation():
    starts = pd.period_range("1990-01", periods=100, freq="M")
    split = validation_split(starts, 12)
    assert len(split.validation) == 15
    assert len(split.core) == 74  # positions 0..73: s + 12 <= the first validation start
    assert starts[split.core].max() + 12 <= starts[split.validation].min()


def test_r3_without_embargo_uses_every_earlier_row():
    starts = pd.period_range("1990-01", periods=100, freq="M")
    assert len(validation_split(starts, 12, embargo=False).core) == 85


def test_r3_check_rejects_an_overlap():
    with pytest.raises(LookaheadError):
        check_embargo(pd.PeriodIndex([month("1999-01")]), pd.PeriodIndex([month("1999-06")]), 12)


def test_r4_rejects_a_transform_fitted_past_the_window():
    check_fit_window(pd.PeriodIndex([month("1999-01")]), month("1999-01"))
    with pytest.raises(LookaheadError):
        check_fit_window(pd.PeriodIndex([month("1999-01"), month("1999-03")]), month("1999-02"))
