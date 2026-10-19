"""G2: the R1 and R2 checks refuse inputs that carry future values (design §8)."""

import numpy as np
import pandas as pd
import pytest
from sector_leadlag.pit import LeakError, check_lookback, check_window
from sector_leadlag.signal import Spec, lead_lag_signal, prior_subspace, target
from sector_leadlag.timing import Rows

T = pd.Timestamp


def test_window_rows_must_be_dated_before_the_day():
    rows = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-06")])
    check_window(rows, rows, T("2026-01-06"), T("2026-01-07"))
    with pytest.raises(LeakError, match="dated 2026-01-07"):
        check_window(
            rows.append(pd.DatetimeIndex([T("2026-01-07")])), rows, T("2026-01-06"), T("2026-01-07")
        )


def test_window_us_returns_must_not_be_after_s_of_d():
    rows = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-06")])
    us = pd.DatetimeIndex([T("2026-01-05"), T("2026-01-07")])
    with pytest.raises(LeakError, match="after s"):
        check_window(rows, us, T("2026-01-06"), T("2026-01-07"))


def test_the_us_day_itself_must_be_before_the_day():
    rows = pd.DatetimeIndex([T("2026-01-05")])
    with pytest.raises(LeakError, match="is not before"):
        check_window(rows, rows, T("2026-01-07"), T("2026-01-07"))


def test_basket_inputs_must_be_read_before_the_day():
    index = pd.DatetimeIndex([T("2026-01-06"), T("2026-01-07")])
    check_lookback(pd.Series([T("2026-01-05"), T("2026-01-06")], index=index))
    with pytest.raises(LeakError, match="baskets of 2026-01-07 read 2026-01-07"):
        check_lookback(pd.Series([T("2026-01-05"), T("2026-01-07")], index=index))


def test_the_signal_refuses_rows_whose_us_returns_come_from_the_future():
    dates = pd.bdate_range("2026-01-05", periods=70)
    rng = np.random.default_rng(0)
    leaky = pd.DatetimeIndex([*dates[:-1], dates[-1] + pd.Timedelta(days=5)])
    rows = Rows(
        dates, leaky, rng.normal(size=(70, 2)), rng.normal(size=(70, 3)), ("XLK", "XLE"), (1, 2, 3)
    )
    us_ret = pd.DataFrame(rng.normal(size=(70, 2)), index=dates, columns=["XLK", "XLE"])
    day = dates[-1] + pd.Timedelta(days=1)
    s_map = pd.Series([dates[-1]], index=pd.DatetimeIndex([day]))
    c0 = target(np.eye(5), prior_subspace(["XLK", "XLE"], [1, 2, 3]))
    with pytest.raises(LeakError):
        lead_lag_signal(rows, us_ret, s_map, c0, pd.DatetimeIndex([day]), Spec())
