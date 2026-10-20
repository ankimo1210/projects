from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from sector_leadlag import baskets as bk
from sector_leadlag.corrections import (
    KNOWN,
    close_ratio,
    correct,
    counts,
    late_etf_dividends,
    market_move,
    missing_known,
    missing_rows,
    oversized_dividends,
    scale_breaks,
    signal_returns,
    split_day_dividends,
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


def _split_day(make_panel, *, dividend, opening):
    """A stock with a 1:2 split on day 4 that also goes ex a dividend that day."""
    close = frame([1000, 1000, 1000, 1000, 1000, 1000])
    return make_panel(
        frame([1000, 1000, 1000, opening, 1000, 1000]),
        close,
        dividends=frame([0, 20, 0, dividend, 0, 0]),
        splits=frame([0, 0, 0, 2, 0, 0]),
    )


def test_a_split_day_dividend_left_in_pre_split_units_is_divided(make_panel):
    market = pd.Series(0.0, index=DAYS)
    # D = 40 is twice the previous dividend, and the open fell 2% (D/(kP)), not 4% (D/P)
    fixed, changes = split_day_dividends(_split_day(make_panel, dividend=40, opening=980), market)
    assert fixed.dividends["a"].iloc[3] == 20.0
    assert [(c.rule, c.before, c.after) for c in changes] == [("C4", 40.0, 20.0)]


@pytest.mark.parametrize(
    ("dividend", "opening"),
    # D = 20 is the previous dividend, though the 1% fall fits D/(kP): only the drop says divide.
    # D = 40 is twice the previous dividend, though the 4% fall fits D/P: only the history does.
    [(20, 990), (40, 960)],
)
def test_a_split_day_dividend_stays_unless_history_and_drop_both_say_divide(
    make_panel, dividend, opening
):
    market = pd.Series(0.0, index=DAYS)
    panel = _split_day(make_panel, dividend=dividend, opening=opening)
    fixed, changes = split_day_dividends(panel, market)
    assert fixed.dividends["a"].iloc[3] == dividend and changes == []


def test_a_split_day_dividend_stays_without_trades_or_an_earlier_dividend(make_panel):
    market = pd.Series(0.0, index=DAYS)
    panel = _split_day(make_panel, dividend=40, opening=980)
    quiet = replace(panel, volume=frame([5, 5, 5, 0, 5, 5]))  # no drop to measure
    first = replace(panel, dividends=frame([0, 0, 0, 40, 0, 0]))  # no dividend before it
    for case in (quiet, first):
        fixed, changes = split_day_dividends(case, market)
        assert fixed.dividends["a"].iloc[3] == 40.0 and changes == []


def test_the_drop_of_a_split_day_dividend_is_measured_against_the_market(make_panel):
    # every stock opened 2% lower: the 2% fall is the market, so D/P = 4% no longer fits
    market = pd.Series(-0.02, index=DAYS)
    fixed, _ = split_day_dividends(_split_day(make_panel, dividend=40, opening=960), market)
    assert fixed.dividends["a"].iloc[3] == 20.0


def test_a_dividend_above_the_close_follows_the_last_down_jump(make_panel):
    close = frame(
        [30000, 60, 60, 60, 60, 60], [100, 100, 100, 100, 100, 100], [100, 300, 300, 300, 300, 300]
    )
    dividends = frame([0, 0, 0, 1500, 0, 0], [0, 0, 0, 5e8, 0, 0], [0, 0, 0, 500, 0, 0])
    panel, _ = with_breaks(make_panel(close, close, dividends=dividends))
    fixed, changes = oversized_dividends(panel)
    assert fixed.dividends.iloc[3].tolist() == [3.0, 0.0, 0.0]  # ÷500; no jump; the jump was up
    assert [(c.column, c.before, c.after) for c in changes] == [
        ("a", 1500.0, 3.0),
        ("b", 5e8, 0.0),
        ("c", 500.0, 0.0),
    ]


def test_a_dividend_still_above_the_close_after_the_jump_becomes_zero(make_panel):
    close = frame([200, 60, 60, 60])
    panel, _ = with_breaks(make_panel(close, close, dividends=frame([0, 0, 0, 900])))
    fixed, _ = oversized_dividends(panel)
    assert fixed.dividends["a"].iloc[3] == 0.0  # 900 × 60/200 = 270 is still above 60


def test_a_dividend_above_the_close_follows_the_latest_jump_before_it(make_panel):
    # a: a down jump on day 2 and an up jump on day 6, after the dividend on day 4
    # b: two down jumps, on days 2 and 3; the later one (÷100) applies
    close = frame([30000, 60, 60, 60, 60, 20000], [30000, 600, 6, 6, 6, 6])
    dividends = frame([0, 0, 0, 1500, 0, 0], [0, 0, 0, 500, 0, 0])
    panel, _ = with_breaks(make_panel(close, close, dividends=dividends))
    fixed, _ = oversized_dividends(panel)
    assert fixed.dividends.iloc[3].tolist() == [3.0, 5.0]  # 1500 × 60/30000; 500 × 6/600


def _etfs(make_panel, opens):
    close = pd.DataFrame(100.0, index=DAYS, columns=[1, 2])
    open_ = pd.DataFrame(opens, index=DAYS, columns=[1, 2], dtype=float)
    dividends = pd.DataFrame(0.0, index=DAYS, columns=[1, 2])
    dividends.iloc[4] = [3.0, 2.0]  # recorded on day 5
    return make_panel(open_, close, dividends=dividends)


def test_late_etf_dividends_move_to_the_lowest_opening_day(make_panel):
    opens = [[100, 100], [100, 100], [97, 98], [100, 100], [100, 100], [100, 100]]
    market = pd.Series(0.0, index=DAYS)
    fixed, changes = late_etf_dividends(_etfs(make_panel, opens), market)
    assert fixed.dividends.iloc[2].tolist() == [3.0, 2.0]  # both move to day 3
    assert fixed.dividends.iloc[4].tolist() == [0.0, 0.0]
    assert [(c.column, c.before, c.after) for c in changes] == [
        (1, "2026-01-09", "2026-01-07"),
        (2, "2026-01-09", "2026-01-07"),
    ]


def test_an_etf_dividend_stays_when_its_own_day_opens_lowest(make_panel):
    opens = [[100, 100], [100, 100], [99, 100], [100, 100], [97, 98], [100, 100]]
    market = pd.Series(0.0, index=DAYS)
    fixed, changes = late_etf_dividends(_etfs(make_panel, opens), market)
    assert fixed.dividends.iloc[4].tolist() == [3.0, 2.0] and changes == []


def test_the_market_move_is_the_median_overnight_return_with_dividends(make_panel):
    close = frame([100, 100], [100, 100], [100, 100])
    stocks = make_panel(
        frame([100, 98], [100, 99], [100, 101]), close, dividends=frame([0, 2], [0, 0], [0, 0])
    )
    assert market_move(stocks).iloc[1] == pytest.approx(0.0)  # 0%, -1% and +1%


def test_the_rules_change_nothing_in_a_world_without_errors(decayed_world):
    w = decayed_world
    us = w.us_adj
    fixed = correct(w.etf, w.stocks, us, us * 0.0)
    assert fixed.changes == [] and fixed.signal_days.equals(w.jp_days)
    pd.testing.assert_frame_equal(fixed.signal, w.etf_c2c(), check_freq=False)
    for returns in (bk.close_to_open, bk.close_to_close, bk.open_to_close):
        pd.testing.assert_frame_equal(returns(fixed.stocks), returns(w.stocks))
        pd.testing.assert_frame_equal(returns(fixed.etf), returns(w.etf))
    assert counts(fixed.changes) == {rule: {} for rule in ("C2", "C1", "C4", "C5", "C6", "C3")}


def test_known_errors_that_no_rule_changed_are_reported():
    change = {"rule": "C1", "kind": "etf", "series": "1629.T", "date": "2015-01-05"}
    missing = missing_known([change])
    assert len(missing) == len(KNOWN) - 1
    assert missing[0]["label"].startswith("1629.T: prices at 1/500")
    assert missing[0]["found"] == 0
    complete = [
        {"rule": k.rule, "kind": k.kind, "series": k.series or "x", "date": k.date or "d"}
        for k in KNOWN
        for _ in range(k.count)
    ]
    assert missing_known(complete) == []


def test_the_rules_run_in_the_designs_order(make_panel):
    etf_close = pd.DataFrame({1: [100.0, 300.0, 300.0]}, index=DAYS[:3])
    etf = make_panel(pd.DataFrame({1: [100.0, 0.0, 300.0]}, index=DAYS[:3]), etf_close)
    stocks = make_panel(frame([100, 300, 300]), frame([100, 300, 300]))
    us = pd.DataFrame({"XLK": [10.0, 10.0, 10.0]}, index=DAYS[:3])
    fixed = correct(etf, stocks, us, us * 0.0)
    assert [(c["rule"], c["kind"], c["series"]) for c in fixed.changes] == [
        ("C2", "etf", "1617.T"),
        ("C1", "etf", "1617.T"),
        ("C1", "stock", "a.T"),
    ]
