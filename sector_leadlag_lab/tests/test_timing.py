import numpy as np
import pandas as pd
import pytest
from sector_leadlag.timing import (
    close_to_close,
    jp_trading_days,
    last_us_before,
    pair_rows,
    us_trading_days,
)


def days(*text: str) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.to_datetime(list(text)))


def test_a_day_counts_when_half_of_the_listed_stocks_traded():
    volume = pd.DataFrame(
        {"a": [10, 0, 5, 7], "b": [10, 0, np.nan, 4], "c": [0, 3, np.nan, 2]},
        index=days("2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"),
    )
    # 2/3 and 1/3 traded on the 5th and 6th; the 7th is a holiday with a stray row for "a"
    # only (1 of the 3 listed names traded); 3/3 on the 8th
    assert list(jp_trading_days(volume)) == list(days("2026-01-05", "2026-01-08"))
    delisted = pd.DataFrame(
        {"a": [10, 10], "b": [0, np.nan]}, index=days("2026-01-05", "2026-01-06")
    )
    # b's last row is the 5th, so on the 6th only a is listed
    assert list(jp_trading_days(delisted)) == list(days("2026-01-05", "2026-01-06"))
    assert list(us_trading_days(pd.Series([1.0, 0.0], index=days("2026-01-05", "2026-01-06")))) == [
        pd.Timestamp("2026-01-05")
    ]


def test_s_of_d_skips_us_holidays_and_follows_japanese_ones():
    us = days("2026-01-15", "2026-01-16", "2026-01-20", "2026-01-21")  # Mon 19th: MLK day
    jp = days("2026-01-16", "2026-01-19", "2026-01-20", "2026-01-21", "2026-01-23")
    s = last_us_before(jp, us)
    assert list(s.index) == list(jp)
    assert list(s) == list(
        days("2026-01-15", "2026-01-16", "2026-01-16", "2026-01-20", "2026-01-21")
    )
    early = last_us_before(days("2026-01-15"), us)  # no US day before it
    assert early.empty


def test_close_to_close_runs_on_the_given_calendar():
    prices = pd.DataFrame(
        {"x": [100.0, 110.0, 99.0]}, index=days("2026-01-05", "2026-01-06", "2026-01-08")
    )
    r = close_to_close(prices, days("2026-01-05", "2026-01-06", "2026-01-08"))
    assert np.isnan(r["x"].iloc[0])
    assert r["x"].iloc[1:].round(6).tolist() == [0.1, -0.1]


def test_pairings():
    us_days = days("2026-01-15", "2026-01-16", "2026-01-20")
    jp_days = days("2026-01-16", "2026-01-19", "2026-01-20")
    us_ret = pd.DataFrame({"XLK": [1.0, 2.0, 3.0]}, index=us_days)
    jp_ret = pd.DataFrame({1: [10.0, 20.0, 30.0]}, index=jp_days)
    s = last_us_before(jp_days, us_days)
    same = pair_rows("same_date", us_ret, jp_ret, s)
    assert list(same.dates) == list(days("2026-01-16", "2026-01-20"))
    assert same.us[:, 0].tolist() == [2.0, 3.0] and same.jp[:, 0].tolist() == [10.0, 30.0]
    lagged = pair_rows("lagged", us_ret, jp_ret, s)
    assert list(lagged.dates) == list(jp_days)
    assert list(lagged.us_dates) == list(days("2026-01-15", "2026-01-16", "2026-01-16"))
    assert lagged.us[:, 0].tolist() == [1.0, 2.0, 2.0]
    assert lagged.jp[:, 0].tolist() == [10.0, 20.0, 30.0]
    assert lagged.us_names == ("XLK",) and lagged.jp_names == (1,)
    with pytest.raises(ValueError, match="unknown pairing"):
        pair_rows("other", us_ret, jp_ret, s)
