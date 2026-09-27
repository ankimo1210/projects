"""Walk-forward splits keep labels and lockbox out of earlier training."""

from datetime import UTC, datetime, timedelta

import pandas as pd
import pytest

T0 = datetime(2026, 9, 1, 21, tzinfo=UTC)


def _table(count=12, horizon=2):
    times = pd.DatetimeIndex(T0 + timedelta(days=i) for i in range(count))
    available = pd.Series(pd.NaT, index=times, dtype="datetime64[ns, UTC]")
    available.iloc[:-horizon] = times[horizon:]
    return pd.DataFrame(
        {
            "momentum": range(count),
            "volatility": range(count),
            "label": [0.1] * (count - horizon) + [float("nan")] * horizon,
            "label_available_at": available,
        },
        index=times,
    )


def _dataset(table, horizon=2):
    from market_research.research.signals import SignalDataset

    return SignalDataset(table, "XNYS:IBM", ("snapshot-1",), "USD", "raw", horizon)


def test_walk_forward_purges_horizon_and_embargo_and_supports_rolling():
    from market_research.research.splits import walk_forward_splits

    splits = walk_forward_splits(
        _dataset(_table()),
        train_size=3,
        test_size=2,
        embargo=1,
    )
    assert splits[0].train_indices == (0, 1, 2)
    assert splits[0].test_indices == (6, 7)
    assert splits[1].train_indices == (2, 3, 4)
    assert splits[1].test_indices == (8, 9)
    for split in splits:
        assert max(split.train_indices) + 2 + 1 < min(split.test_indices)
        assert all(
            _table().iloc[i]["label_available_at"] < split.test_start_at
            for i in split.train_indices
        )


def test_expanding_and_lockbox_exclude_future_evaluation():
    from market_research.research.splits import walk_forward_splits

    splits = walk_forward_splits(
        _dataset(_table(horizon=1), 1),
        train_size=3,
        test_size=2,
        expanding=True,
        lockbox_start=T0 + timedelta(days=8),
    )
    assert splits[0].train_indices == (0, 1, 2)
    assert splits[0].test_indices == (4, 5)
    assert splits[1].train_indices == (0, 1, 2, 3, 4)
    assert splits[1].test_indices == (6, 7)
    assert len(splits) == 2


def test_splitter_rejects_mislabeled_or_short_data():
    from market_research.research.splits import walk_forward_splits

    frame = _table(6, horizon=2)
    with pytest.raises(ValueError, match="short"):
        walk_forward_splits(_dataset(frame), train_size=3, test_size=2, embargo=1)
    late = _table(6, horizon=1)
    late.loc[T0, "label_available_at"] = T0 + timedelta(days=100)
    with pytest.raises(ValueError, match="label availability"):
        walk_forward_splits(_dataset(late, 1), train_size=2, test_size=2)
    with pytest.raises(ValueError, match="timezone"):
        walk_forward_splits(
            _dataset(frame.rename(index=lambda x: x.tz_localize(None))), train_size=2, test_size=2
        )
    duplicate = _table()
    duplicate_index = list(duplicate.index)
    duplicate_index[1] = duplicate_index[0]
    duplicate.index = pd.DatetimeIndex(duplicate_index)
    with pytest.raises(ValueError, match="unique and ordered"):
        walk_forward_splits(_dataset(duplicate), train_size=2, test_size=2)


def test_test_windows_cannot_overlap():
    from market_research.research.splits import walk_forward_splits

    with pytest.raises(ValueError, match="step"):
        walk_forward_splits(_dataset(_table()), train_size=3, test_size=2, step=1)


def test_label_metadata_cannot_claim_future_close_was_available_early():
    from market_research.research.splits import walk_forward_splits

    frame = _table(horizon=2)
    frame.loc[T0, "label_available_at"] = T0
    with pytest.raises(ValueError, match="future close"):
        walk_forward_splits(_dataset(frame), train_size=3, test_size=2)


def test_splitter_rejects_incomplete_test_labels():
    from market_research.research.splits import walk_forward_splits

    frame = _table()
    frame.loc[T0 + timedelta(days=6), "label"] = float("nan")
    with pytest.raises(ValueError, match="test label"):
        walk_forward_splits(_dataset(frame), train_size=3, test_size=2, embargo=1, step=6)


def test_splitter_excludes_tail_without_mature_labels():
    from market_research.research.splits import walk_forward_splits

    splits = walk_forward_splits(_dataset(_table()), train_size=3, test_size=2, embargo=1)
    assert tuple(split.test_indices for split in splits) == ((6, 7), (8, 9))


def test_splitter_uses_pit_dataset_horizon_without_duplicate_argument():
    from market_research.research.signals import SignalDataset
    from market_research.research.splits import walk_forward_splits

    dataset = SignalDataset(_table(), "XNYS:IBM", ("snapshot-1",), "USD", "raw", 2)
    splits = walk_forward_splits(dataset, train_size=3, test_size=2, embargo=1)
    assert tuple(split.test_indices for split in splits) == ((6, 7), (8, 9))


def test_splitter_rejects_display_history_without_pit_provenance():
    from market_research.research.splits import walk_forward_splits

    with pytest.raises(TypeError, match="SignalDataset"):
        walk_forward_splits(_table(), train_size=3, test_size=2, embargo=1)


@pytest.mark.parametrize(
    "changes",
    [{"mode": "retrospective"}, {"snapshot_ids": ()}],
)
def test_splitter_rejects_dataset_without_pit_provenance(changes):
    from dataclasses import replace

    from market_research.research.splits import walk_forward_splits

    dataset = replace(_dataset(_table()), **changes)
    with pytest.raises(ValueError, match="point-in-time snapshot provenance"):
        walk_forward_splits(dataset, train_size=3, test_size=2, embargo=1)
