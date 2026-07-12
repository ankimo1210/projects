"""Deterministic, order-independent named random streams."""

from __future__ import annotations

import zlib

import numpy as np

STREAM_NAMES = frozenset(
    {
        "asset_z",
        "asset_zperp",
        "volterra_residual",
        "fbm_a",
        "hurst_b",
        "ou_c",
        "fou_c",
        "heston_z",
        "hawkes_poisson",
        "hawkes_stable",
        "hawkes_critical",
        "noise_g",
        "microstructure_noise",
    }
)


def child_seed(seed: int, name: str) -> np.random.SeedSequence:
    """Derive a stable child seed from ``seed`` and a semantic stream name.

    A CRC32 key is used as the one-element ``spawn_key``.  Unlike sequential
    ``SeedSequence.spawn`` calls, this mapping does not depend on call order.
    """
    if not isinstance(seed, (int, np.integer)) or int(seed) < 0:
        raise ValueError("seed must be a non-negative integer")
    if not isinstance(name, str) or not name:
        raise ValueError("random-stream name must be a non-empty string")
    key = zlib.crc32(name.encode("utf-8")) & 0xFFFFFFFF
    return np.random.SeedSequence(int(seed), spawn_key=(key,))


def stream(seed: int, name: str) -> np.random.Generator:
    """Create a fresh NumPy generator for a named deterministic stream."""
    return np.random.default_rng(child_seed(seed, name))
