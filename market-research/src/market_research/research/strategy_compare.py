"""Cost-matched single-asset strategy comparisons from OOS predictions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

import numpy as np
import pandas as pd

from market_research.backtest import BacktestResult, run_backtest

from .models import ModelEvaluation, evaluate_models
from .signals import SignalDataset


@dataclass(frozen=True, slots=True)
class StrategyComparison:
    evaluation: ModelEvaluation
    backtests: Mapping[str, BacktestResult]
    as_of: datetime
    commission_bps: float
    slippage_bps: float
    prediction_rule: str = "positive_one_step_return_long_else_cash"


def compare_model_strategies(
    dataset: SignalDataset,
    *,
    train_size: int,
    test_size: int,
    feature_names: tuple[str, ...] = ("momentum", "volatility"),
    embargo: int = 0,
    step: int | None = None,
    expanding: bool = False,
    lockbox_start: datetime | None = None,
    ridge_alpha: float = 1.0,
    commission_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> StrategyComparison:
    """Trade only after OOS one-step decisions, with identical return/cost inputs."""
    if not isinstance(dataset, SignalDataset):
        raise TypeError("a SignalDataset is required")
    if dataset.horizon != 1:
        raise ValueError("one-period labels are required for lag-one trading")
    evaluation = evaluate_models(
        dataset,
        train_size=train_size,
        test_size=test_size,
        feature_names=feature_names,
        embargo=embargo,
        step=step,
        expanding=expanding,
        lockbox_start=lockbox_start,
        ridge_alpha=ridge_alpha,
    )
    end_at = evaluation.table["label_available_at"].max()
    if lockbox_start is not None and end_at >= lockbox_start:
        raise ValueError("evaluation return crosses lockbox")
    if "close" not in dataset.table:
        raise ValueError("close prices are required")
    closes = dataset.table.loc[:end_at, "close"].astype(float)
    if not len(closes) or not np.isfinite(closes.to_numpy()).all() or (closes <= 0).any():
        raise ValueError("close prices must be positive and complete")
    if not evaluation.table.index.isin(closes.index).all() or end_at not in closes.index:
        raise ValueError("prediction times and label availability must match closes")
    asset = dataset.instrument_id
    returns = closes.pct_change(fill_method=None).to_frame(asset)
    backtests: dict[str, BacktestResult] = {}
    for model in ("zero", "mean", "ridge", "buy_hold"):
        targets = pd.DataFrame(0.0, index=closes.index, columns=[asset])
        if model == "buy_hold":
            targets.loc[evaluation.table.index.min() :, asset] = 1.0
        else:
            targets.loc[evaluation.table.index, asset] = (evaluation.table[model] > 0.0).astype(
                float
            )
        targets.attrs["timing"] = "decision_close"
        backtests[model] = run_backtest(
            targets,
            returns,
            base_currency=dataset.currency,
            return_currencies={asset: dataset.currency},
            commission_bps=commission_bps,
            slippage_bps=slippage_bps,
        )
    return StrategyComparison(
        evaluation,
        MappingProxyType(backtests),
        end_at.to_pydatetime(),
        commission_bps,
        slippage_bps,
    )
