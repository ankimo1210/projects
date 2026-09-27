"""Compare simple models on the same point-in-time walk."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest
from market_research.research.signals import SignalDataset

T0 = datetime(2026, 9, 1, 21, tzinfo=UTC)


def _dataset() -> SignalDataset:
    times = pd.DatetimeIndex(T0 + timedelta(days=i) for i in range(16))
    momentum = np.arange(16, dtype=float)
    momentum[:2] = np.nan  # trailing feature warmup is not filled
    labels = 0.02 + 0.01 * np.arange(16, dtype=float)
    labels[-1] = np.nan
    available = pd.Series(pd.NaT, index=times, dtype="datetime64[ns, UTC]")
    available.iloc[:-1] = times[1:]
    table = pd.DataFrame(
        {
            "momentum": momentum,
            "volatility": np.ones(16),
            "label": labels,
            "label_available_at": available,
        },
        index=times,
    )
    return SignalDataset(table, "XNYS:IBM", ("saved-snapshot",), "USD", "raw", 1)


def test_models_share_walk_and_fit_only_eligible_training_rows():
    from market_research.research.models import evaluate_models

    result = evaluate_models(
        _dataset(),
        train_size=5,
        test_size=2,
        feature_names=("momentum",),
        ridge_alpha=0.0,
    )
    first = result.table.iloc[:2]
    assert first.index.tolist() == [T0 + timedelta(days=6), T0 + timedelta(days=7)]
    assert first["zero"].tolist() == [0.0, 0.0]
    assert first["mean"].tolist() == pytest.approx([0.05, 0.05])
    assert first["ridge"].tolist() == pytest.approx([0.08, 0.09])
    assert first["label"].tolist() == pytest.approx([0.08, 0.09])
    assert first["train_rows"].tolist() == [3, 3]
    assert result.snapshot_ids == ("saved-snapshot",)
    assert result.currency == "USD"


def test_tree_depth_and_leaf_size_bound_train_only_splits():
    from market_research.research.models import evaluate_models

    original = _dataset()
    table = original.table.copy()
    table.loc[:, "momentum"] = np.arange(len(table), dtype=float)
    table.loc[table.index[:8], "label"] = [0.0, 0.0, 0.1, 0.1, 0.1, 0.2, 0.2, 0.2]
    table.loc[table.index[9], "momentum"] = 3.0
    dataset = replace(original, table=table)
    kwargs = dict(train_size=8, test_size=1, feature_names=("momentum",))

    shallow = evaluate_models(dataset, **kwargs, tree_max_depth=1)
    deeper = evaluate_models(dataset, **kwargs, tree_max_depth=2)
    wide_leaf = evaluate_models(dataset, **kwargs, tree_max_depth=2, tree_min_leaf=3)

    assert shallow.table.iloc[0]["tree"] == pytest.approx(0.06)
    assert deeper.table.iloc[0]["tree"] == pytest.approx(0.1)
    assert wide_leaf.table.iloc[0]["tree"] == pytest.approx(0.06)
    assert deeper.table.iloc[0]["train_rows"] == 8


@pytest.mark.parametrize(
    ("parameter", "value"),
    [
        ("tree_max_depth", 0),
        ("tree_max_depth", True),
        ("tree_max_depth", 1.5),
        ("tree_min_leaf", 0),
        ("tree_min_leaf", True),
        ("tree_min_leaf", 1.5),
    ],
)
def test_tree_requires_positive_integer_bounds(parameter, value):
    from market_research.research.models import evaluate_models

    with pytest.raises(ValueError, match=parameter):
        evaluate_models(_dataset(), train_size=5, test_size=2, **{parameter: value})


def test_future_label_change_does_not_change_past_predictions():
    from market_research.research.models import evaluate_models

    original = _dataset()
    altered_table = original.table.copy()
    altered_table.loc[T0 + timedelta(days=10), "label"] = 999.0
    changed = replace(original, table=altered_table)
    kwargs = dict(train_size=5, test_size=2, feature_names=("momentum",))
    before = evaluate_models(original, **kwargs).table.iloc[:2]
    after = evaluate_models(changed, **kwargs).table.iloc[:2]
    pd.testing.assert_frame_equal(before, after)


def test_incomplete_test_features_are_rejected_without_filling():
    from market_research.research.models import evaluate_models

    original = _dataset()
    table = original.table.copy()
    table.loc[T0 + timedelta(days=6), "momentum"] = float("nan")
    with pytest.raises(ValueError, match="test features"):
        evaluate_models(
            replace(original, table=table),
            train_size=5,
            test_size=2,
            feature_names=("momentum",),
        )


def test_lockbox_is_excluded_from_model_predictions():
    from market_research.research.models import evaluate_models

    result = evaluate_models(
        _dataset(),
        train_size=5,
        test_size=2,
        feature_names=("momentum",),
        lockbox_start=T0 + timedelta(days=10),
    )
    assert list(result.table.index) == [
        T0 + timedelta(days=6),
        T0 + timedelta(days=7),
    ]
    assert (result.table["label_available_at"] < T0 + timedelta(days=10)).all()


def test_future_label_cannot_be_selected_as_model_feature():
    from market_research.research.models import evaluate_models

    with pytest.raises(ValueError, match="causal feature"):
        evaluate_models(_dataset(), train_size=5, test_size=2, feature_names=("label",))
