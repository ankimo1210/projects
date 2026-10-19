from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.baskets import (
    basket_returns,
    close_to_close,
    close_to_open,
    h2_picks,
    liquidity_weights,
    open_to_close,
    opening_gap,
    price_close_to_close,
    quoted,
    top_equal_weights,
    trailing_value,
)

DAYS = pd.bdate_range("2026-01-05", periods=4)


def frame(values, columns=("a",)):
    return pd.DataFrame(
        np.asarray(values, dtype=float).reshape(len(DAYS), -1), index=DAYS, columns=list(columns)
    )


def test_a_split_day_does_not_move_open_to_close(make_panel):
    # yfinance divides prices before a 1:5 split (ex-date: day 3) by 5
    panel = make_panel(
        frame([200, 202, 204, 206]),
        frame([201, 203, 205, 207]),
        splits=frame([0, 0, 5, 0]),
    )
    quoted_open, quoted_close = quoted(panel)
    assert quoted_close["a"].tolist() == [1005.0, 1015.0, 205.0, 207.0]
    same_day = quoted_close / quoted_open - 1
    pd.testing.assert_frame_equal(open_to_close(panel), same_day)


def test_overnight_and_daily_returns_add_the_dividend_going_ex(make_panel):
    panel = make_panel(
        frame([100, 97, 98, 99]),
        frame([100, 98, 99, 100]),
        dividends=frame([0, 3, 0, 0]),
    )
    assert close_to_open(panel)["a"].iloc[1] == pytest.approx(0.0)
    assert close_to_close(panel)["a"].iloc[1] == pytest.approx(0.01)
    assert price_close_to_close(panel)["a"].iloc[1] == pytest.approx(-0.02)
    assert np.isnan(close_to_open(panel)["a"].iloc[0])


def test_a_jump_hides_the_returns_from_the_previous_close_only(make_panel):
    panel = make_panel(frame([100, 49, 50, 51]), frame([100, 50, 51, 52]))
    jumped = replace(panel, breaks=frame([0, 1, 0, 0]) > 0)
    for returns in (close_to_open, close_to_close, price_close_to_close, opening_gap):
        assert returns(jumped)["a"].isna().tolist() == [True, True, False, False]
        assert returns(panel)["a"].isna().tolist() == [True, False, False, False]
    pd.testing.assert_frame_equal(open_to_close(jumped), open_to_close(panel))
    assert jumped.window(DAYS[1], DAYS[2]).breaks["a"].tolist() == [True, False]


def test_a_day_without_trades_has_no_return(make_panel):
    panel = make_panel(
        frame([100, 100, 100, 101]), frame([101, 100, 100, 102]), volume=frame([5, 0, 5, 5])
    )
    assert open_to_close(panel)["a"].isna().tolist() == [False, True, False, False]


def test_trailing_value_uses_only_earlier_days(make_panel):
    days = pd.bdate_range("2026-01-05", periods=5)
    close = pd.DataFrame({"a": [10.0, 10, 10, 10, 10]}, index=days)
    volume = pd.DataFrame({"a": [1.0, 2, 3, 4, 100]}, index=days)
    panel = make_panel(close, close, volume=volume)
    median = trailing_value(panel, lookback=3)
    assert median["a"].isna().tolist() == [True, True, True, False, False]
    assert median["a"].iloc[3:].tolist() == [20.0, 30.0]  # day 5's own 1,000 is not used


def test_weights_and_picks_within_each_sector():
    median = pd.DataFrame([[4.0, 3.0, 2.0, 1.0, 9.0]], index=DAYS[:1], columns=list("abcde"))
    sector = pd.Series([1, 1, 1, 1, 2], index=list("abcde"))
    weights = liquidity_weights(median, sector)
    assert weights.loc[DAYS[0], ["a", "b", "c", "d"]].sum() == pytest.approx(1.0)
    assert weights.loc[DAYS[0], "a"] == pytest.approx(0.4) and weights.loc[DAYS[0], "e"] == 1.0
    top = top_equal_weights(median, sector, n=2)
    assert top.loc[DAYS[0]].tolist() == [0.5, 0.5, 0.0, 0.0, 1.0]
    close = pd.DataFrame(
        [[1000.0, 200.0, 300.0, 400.0, 500.0], [1000.0, 200.0, 300.0, 400.0, 500.0]],
        index=DAYS[:2],
        columns=list("abcde"),
    )
    picks = h2_picks(
        pd.concat([median, median.set_axis(DAYS[1:2])]), close, sector, budget=50_000.0
    )
    # a's lot costs 100,000 yen and is left out; e's costs exactly the budget and is kept
    assert picks.loc[DAYS[1]].tolist() == [False, True, True, True, True]
    assert not picks.loc[DAYS[0]].any()  # the first day has no previous close


def test_basket_return_renormalises_over_the_names_that_traded():
    returns = pd.DataFrame([[0.01, np.nan, 0.03]], index=DAYS[:1], columns=list("abc"))
    weights = pd.DataFrame([[0.5, 0.25, 0.25]], index=DAYS[:1], columns=list("abc"))
    sector = pd.Series([1, 1, 2], index=list("abc"))
    out = basket_returns(weights, returns, sector)
    assert out.loc[DAYS[0], 1] == pytest.approx(0.01)
    assert out.loc[DAYS[0], 2] == pytest.approx(0.03)
    assert out.columns.tolist() == list(range(1, 18)) and np.isnan(out.loc[DAYS[0], 3])
