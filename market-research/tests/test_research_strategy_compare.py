"""Out-of-sample predictions use one lag and identical trading costs."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from market_research.research.signals import SignalDataset

T0 = datetime(2026, 9, 1, 21, tzinfo=UTC)
ASSET = "XNYS:IBM"


def _dataset(count=10, horizon=1):
    times = pd.DatetimeIndex(T0 + timedelta(days=i) for i in range(count))
    close = np.asarray([100.0 * 1.1**i for i in range(count)])
    feature = np.asarray([float("nan"), float("nan"), *([0.1] * (count - 2))])
    labels = np.asarray([0.1] * (count - horizon) + [float("nan")] * horizon)
    available = pd.Series(pd.NaT, index=times, dtype="datetime64[ns, UTC]")
    available.iloc[:-horizon] = times[horizon:]
    table = pd.DataFrame(
        {
            "close": close,
            "momentum": feature,
            "volatility": np.zeros(count),
            "label": labels,
            "label_available_at": available,
        },
        index=times,
    )
    return SignalDataset(table, ASSET, ("saved-snapshot",), "USD", "raw", horizon)


def test_strategy_comparison_applies_one_lag_and_turnover_cost_once():
    from market_research.research.strategy_compare import compare_model_strategies

    result = compare_model_strategies(
        _dataset(),
        train_size=4,
        test_size=1,
        feature_names=("momentum",),
        commission_bps=10.0,
    )
    zero = result.backtests["zero"]
    mean = result.backtests["mean"]
    ridge = result.backtests["ridge"]
    hold = result.backtests["buy_hold"]
    assert mean.held_weights.loc[T0 + timedelta(days=5), ASSET] == 0.0
    assert mean.held_weights.loc[T0 + timedelta(days=6), ASSET] == 1.0
    assert mean.costs.loc[T0 + timedelta(days=6)] == pytest.approx(0.001)
    assert mean.net_returns.loc[T0 + timedelta(days=6)] == pytest.approx(0.099)
    assert zero.net_returns.loc[T0 + timedelta(days=6)] == 0.0
    pd.testing.assert_series_equal(mean.net_returns, ridge.net_returns)
    pd.testing.assert_series_equal(mean.net_returns, hold.net_returns)
    assert result.prediction_rule == "positive_one_step_return_long_else_cash"


def test_strategy_comparison_excludes_lockbox_returns():
    from market_research.research.strategy_compare import compare_model_strategies

    lockbox = T0 + timedelta(days=8)
    result = compare_model_strategies(
        _dataset(),
        train_size=4,
        test_size=1,
        feature_names=("momentum",),
        lockbox_start=lockbox,
    )
    assert all(backtest.net_returns.index.max() < lockbox for backtest in result.backtests.values())
    assert (result.evaluation.table["label_available_at"] < lockbox).all()


def test_strategy_comparison_refuses_multi_period_label_and_missing_close():
    from market_research.research.strategy_compare import compare_model_strategies

    with pytest.raises(ValueError, match="one-period"):
        compare_model_strategies(
            _dataset(horizon=2),
            train_size=4,
            test_size=1,
            feature_names=("momentum",),
        )
    original = _dataset()
    table = original.table.copy()
    table.loc[T0 + timedelta(days=6), "close"] = float("nan")
    with pytest.raises(ValueError, match="close"):
        compare_model_strategies(
            replace(original, table=table),
            train_size=4,
            test_size=1,
            feature_names=("momentum",),
        )
