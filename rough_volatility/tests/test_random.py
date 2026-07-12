"""Tests for the named, seed-derived random stream helpers."""

import numpy as np
from rough_volatility.random import STREAM_NAMES, child_seed, stream


def test_same_seed_and_name_reproduces_stream() -> None:
    a = stream(1210, "asset_z").standard_normal(8)
    b = stream(1210, "asset_z").standard_normal(8)
    np.testing.assert_array_equal(a, b)


def test_different_names_give_different_streams() -> None:
    a = stream(1210, "asset_z").standard_normal(8)
    b = stream(1210, "asset_zperp").standard_normal(8)
    assert not np.allclose(a, b)


def test_different_seeds_give_different_streams() -> None:
    a = stream(1210, "asset_z").standard_normal(8)
    b = stream(1211, "asset_z").standard_normal(8)
    assert not np.allclose(a, b)


def test_streams_are_order_independent() -> None:
    first_then_second = [
        stream(7, "fbm_a").standard_normal(4),
        stream(7, "hurst_b").standard_normal(4),
    ]
    second_then_first = [
        stream(7, "hurst_b").standard_normal(4),
        stream(7, "fbm_a").standard_normal(4),
    ]
    np.testing.assert_array_equal(first_then_second[0], second_then_first[1])
    np.testing.assert_array_equal(first_then_second[1], second_then_first[0])


def test_child_seed_is_seed_sequence_with_name_key() -> None:
    ss = child_seed(1210, "asset_z")
    assert isinstance(ss, np.random.SeedSequence)
    assert ss.entropy == 1210
    assert len(ss.spawn_key) == 1


def test_canonical_stream_names_registered() -> None:
    for name in ("asset_z", "asset_zperp", "volterra_residual", "fbm_a", "hurst_b", "fou_c"):
        assert name in STREAM_NAMES


def test_empty_name_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        stream(1, "")
