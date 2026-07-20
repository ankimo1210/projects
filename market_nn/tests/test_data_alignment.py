from __future__ import annotations

import numpy as np
import pytest

from lob_reproductions.data.fi2010 import (
    FI2010_CLASS_NAMES,
    FI2010_HORIZONS,
    FI2010_INSTRUMENTS,
    FI2010_LABEL_ROWS,
    build_windows,
    raw_feature_names,
)
from lob_reproductions.data.fi2010_public import fetch_fi2010
from lob_reproductions.fixtures.fi2010 import (
    DeepLOBWindowFixture,
    FI2010MatrixFixture,
    TLOBWindowFixture,
)
from lob_reproductions.fixtures.queue_imbalance import QueueImbalanceFixture
from lob_reproductions.provenance.profiles import load_profile
from lob_reproductions.queue_imbalance.sampling import split_observations


def test_fi2010_canonical_rows_horizons_classes_and_instrument_order() -> None:
    fixture = FI2010MatrixFixture(observations_per_day=140, days_per_instrument=2)
    matrix = fixture.matrix
    assert matrix.values.shape == (149, 1400)
    assert raw_feature_names()[:8] == (
        "ask_price_l1",
        "ask_volume_l1",
        "bid_price_l1",
        "bid_volume_l1",
        "ask_price_l2",
        "ask_volume_l2",
        "bid_price_l2",
        "bid_volume_l2",
    )
    assert FI2010_LABEL_ROWS == {10: 144, 20: 145, 30: 146, 50: 147, 100: 148}
    assert FI2010_HORIZONS == (10, 20, 30, 50, 100)
    assert FI2010_CLASS_NAMES == ("up", "stationary", "down")
    assert matrix.instrument_order == FI2010_INSTRUMENTS
    np.testing.assert_array_equal(matrix.labels(100), matrix.values[148].astype(int) - 1)
    observation = 17
    np.testing.assert_allclose(
        matrix.features(all_features=False)[observation, :4],
        [
            observation,
            1_000_000 + observation + 0.01,
            2_000_000 + observation + 0.02,
            3_000_000 + observation + 0.03,
        ],
    )


def test_windows_align_target_to_endpoint_and_never_cross_asset_or_day() -> None:
    matrix = FI2010MatrixFixture(observations_per_day=140, days_per_instrument=2).matrix
    windows = build_windows(
        matrix,
        sequence_length=100,
        horizon=100,
        all_features=False,
        stride=7,
    )
    boundary = matrix.boundary_id()
    for window, label, endpoint in zip(
        windows.features, windows.labels, windows.endpoint_index, strict=True
    ):
        start = endpoint - 99
        assert np.all(boundary[start : endpoint + 1] == boundary[endpoint])
        assert label == matrix.labels(100)[endpoint]
        # Raw row zero encodes the source observation index, exposing an endpoint shift.
        np.testing.assert_array_equal(window[:, 0], np.arange(start, endpoint + 1))
        assert window[-1, 0] == endpoint


def test_named_deeplob_and_tlob_layouts_are_explicit() -> None:
    deep = DeepLOBWindowFixture.generate(sequence_length=100, stride=40)
    tlob = TLOBWindowFixture.generate(sequence_length=128, stride=64)
    assert deep.features.shape[1:] == (100, 40)
    assert deep.tensorflow_layout().shape[1:] == (100, 40, 1)
    assert deep.pytorch_layout().shape[1:] == (1, 100, 40)
    assert tlob.features.shape[1:] == (128, 144)


def test_queue_samples_are_open_interval_causal_and_repeatable() -> None:
    fixture = QueueImbalanceFixture(days=3, intervals_per_day=120, seed=11)
    first = fixture.sample_paper_observations(observations_per_day=100, seed=13)
    second = fixture.sample_paper_observations(observations_per_day=100, seed=13)
    first.assert_aligned()
    assert np.all(first.sampled_time > first.interval_start)
    assert np.all(first.sampled_time < first.interval_end)
    assert np.all(first.source_event_time <= first.sampled_time)
    np.testing.assert_array_equal(first.imbalance, second.imbalance)
    np.testing.assert_array_equal(first.response, second.response)


def test_exact_random_and_audit_chronological_splits_follow_profiles() -> None:
    observations = QueueImbalanceFixture(days=3, intervals_per_day=120).sample_paper_observations(
        observations_per_day=100
    )
    exact = load_profile("gould_bonart_2015_paper")
    audit = load_profile("gould_bonart_2015_chronological_audit")
    random_split = split_observations(
        observations,
        strategy=exact["split"]["strategy"],
        train_fraction=exact["split"]["train_fraction"],
        seed=exact["random_seed"],
    )
    chronological = split_observations(
        observations,
        strategy=audit["split"]["strategy"],
        train_fraction=audit["split"]["train_fraction"],
        seed=audit["random_seed"],
    )
    expected_random = np.random.default_rng(7).permutation(300)
    expected_chronological = np.lexsort((observations.sampled_time, observations.day))
    np.testing.assert_array_equal(random_split.train_index, expected_random[:240])
    np.testing.assert_array_equal(chronological.train_index, expected_chronological[:240])
    assert not np.array_equal(random_split.train_index, chronological.train_index)


def test_public_data_fetch_requires_explicit_terms_acceptance() -> None:
    with pytest.raises(PermissionError, match="accept-terms"):
        fetch_fi2010(accept_terms=False)
