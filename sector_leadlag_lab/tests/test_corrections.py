import numpy as np
import pandas as pd
import pytest
from sector_leadlag import baskets as bk
from sector_leadlag.corrections import (
    close_ratio,
    missing_rows,
    scale_breaks,
    signal_returns,
    with_breaks,
    zero_opens,
)

DAYS = pd.bdate_range("2026-01-05", periods=6)


def frame(*columns, names=None):
    names = names or [chr(ord("a") + i) for i in range(len(columns))]
    return pd.DataFrame(
        {
            name: np.asarray(values, dtype=float)
            for name, values in zip(names, columns, strict=True)
        },
        index=DAYS[: len(columns[0])],
    )


def test_an_open_of_zero_with_trades_becomes_missing(make_panel):
    panel = make_panel(
        frame([100, 0, 0, 101]), frame([100, 101, 101, 102]), volume=frame([5, 5, 0, 5])
    )
    fixed, changes = zero_opens(panel)
    assert fixed.open["a"].isna().tolist() == [False, True, False, False]  # day 3 had no trades
    assert bk.open_to_close(fixed)["a"].isna().tolist() == [False, True, True, False]
    assert [(c.rule, c.day, c.before, c.after) for c in changes] == [("C2", DAYS[1], 0.0, None)]


def test_a_jump_without_a_split_breaks_the_returns_across_it(make_panel):
    close = frame([100, 300, 301, 150, 140, 141], [100, 40, 41, 42, 43, 44])
    splits = frame([0, 0, 0, 0, 0, 0], [0, 2.5, 0, 0, 0, 0])
    breaks = scale_breaks(close, splits)
    assert breaks["a"].tolist() == [False, True, False, True, False, False]
    assert not breaks["b"].any()  # b's fall to 40% is a recorded split
    fixed, changes = with_breaks(make_panel(close, close, splits=splits))
    for returns in (bk.close_to_open, bk.close_to_close, bk.price_close_to_close):
        assert returns(fixed)["a"].isna().tolist() == [True, True, False, True, False, False]
    assert bk.open_to_close(fixed)["a"].notna().all()  # the levels stay as they are
    assert [(c.day, c.before) for c in changes] == [(DAYS[1], 3.0), (DAYS[3], 150 / 301)]


def test_a_jump_counts_from_the_series_previous_row():
    close = frame([100, np.nan, 300])
    assert close_ratio(close)["a"].iloc[2] == 3.0
    assert scale_breaks(close, close * 0)["a"].tolist() == [False, False, True]


def test_a_missing_row_inside_the_listed_span_drops_the_day_from_the_signal(make_panel):
    close = frame([100, 101, np.nan, 103, 104, 105], [np.nan, 50, 51, 52, 53, 54])
    gaps = missing_rows(close)
    assert gaps["a"].tolist() == [False, False, True, False, False, False]
    assert not gaps["b"].any()  # b was not listed yet on day 1
    panel, _ = with_breaks(make_panel(close, close))
    days = DAYS[~gaps.any(axis=1).to_numpy()]
    signal = signal_returns(panel, days)
    assert list(signal.index) == [DAYS[0], DAYS[1], DAYS[3], DAYS[4], DAYS[5]]
    assert signal.loc[DAYS[3], "a"] == pytest.approx(103 / 101 - 1)  # two days at once
    assert signal.loc[DAYS[3], "b"] == pytest.approx(52 / 50 - 1)


def test_a_dividend_or_a_jump_on_a_dropped_day_goes_to_the_next_row(make_panel):
    close = frame([100, 101, 50, 51, 52, 53], [100, 100, 100, 100, 100, 100])
    dividends = frame([0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 0, 0])
    panel, _ = with_breaks(make_panel(close, close, dividends=dividends))
    signal = signal_returns(panel, DAYS.delete(2))  # day 3 is out of the signal rows (C3)
    assert np.isnan(signal.loc[DAYS[3], "a"])  # a's jump on day 3 hides day 4's return
    assert signal.loc[DAYS[3], "b"] == pytest.approx(0.02)  # (100 + 2) / 100 - 1


def test_the_signal_side_adds_the_dividend_and_counts_days_without_trades(make_panel):
    close = frame([100, 98, 99, 300, 301, 302])
    panel, _ = with_breaks(
        make_panel(
            close, close, volume=frame([5, 5, 0, 5, 5, 5]), dividends=frame([0, 3, 0, 0, 0, 0])
        )
    )
    signal = signal_returns(panel, DAYS)
    assert signal["a"].iloc[1] == pytest.approx(0.01)  # (98 + 3) / 100 - 1
    assert signal["a"].iloc[2] == pytest.approx(99 / 98 - 1)  # no trades, as in the record
    assert signal["a"].isna().tolist() == [True, False, False, True, False, False]


def test_without_dividends_the_signal_side_is_the_records(make_panel):
    close = frame([100, 98, 99, 101, 100, 102])
    panel, _ = with_breaks(make_panel(close, close))
    record = close / close.shift(1) - 1
    pd.testing.assert_frame_equal(signal_returns(panel, DAYS), record, check_freq=False)
