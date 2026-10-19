import numpy as np
import pandas as pd
from sector_leadlag.stages import (
    basket_long_short,
    build_signal,
    cut,
    fit_in,
    h1_baskets,
    h2_series,
)
from sector_leadlag.study import A, B


def test_the_signal_covers_the_japanese_days_after_the_first_window(decayed_world):
    signal = build_signal(decayed_world, "same_date")
    assert list(signal.columns) == list(range(1, 18))
    assert signal.index.isin(decayed_world.jp_days).all()
    assert signal.index[0] < A[0] and signal.index[-1] == decayed_world.jp_days[-1]


def test_baskets_and_the_cash_strategy_use_only_the_days_asked_for(decayed_world):
    baskets = h1_baskets(decayed_world)
    weights = baskets.main.loc[A[0] :]
    sums = weights.T.groupby(decayed_world.stocks.sector).sum().T
    assert np.allclose(sums.to_numpy(), 1.0)
    signal = cut(build_signal(decayed_world, "lagged"), B)
    cash, spread = h2_series(decayed_world, signal, baskets.median)
    assert cash.returns.index.equals(signal.index)
    assert spread.index.isin(signal.index).all()
    assert (cash.names <= 15).all() and (cash.invested <= 1.0).all()


def test_a_period_without_enough_days_gets_no_regression():
    days = pd.bdate_range("2026-01-05", periods=3)
    frame = pd.DataFrame(
        np.random.default_rng(0).normal(size=(3, 17)), index=days, columns=range(1, 18)
    )
    assert fit_in(frame, frame, (days[0], days[-1])) is None


def test_the_basket_long_short_is_flat_on_a_flat_signal():
    days = pd.bdate_range("2026-01-05", periods=2)
    signal = pd.DataFrame(1.0, index=days, columns=range(1, 18))
    returns = pd.DataFrame(0.01, index=days, columns=range(1, 18))
    assert basket_long_short(signal, returns).tolist() == [0.0, 0.0]
