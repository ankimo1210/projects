"""Deterministic random-stream management and common random numbers (CRN).

Every stochastic component draws from a named stream derived from the master
seed via :func:`stream_rng`, so results are reproducible and streams are
independent. Strategy comparisons use *common random numbers*: each scenario
(episode) has a scenario seed shared by every strategy, so all strategies face
the same exogenous randomness (price innovations, market flow, liquidity).
"""

from __future__ import annotations

import zlib

import numpy as np


def _label_key(label: str) -> int:
    """Stable 32-bit key for a stream label (crc32 is deterministic across runs)."""
    return zlib.crc32(label.encode("utf-8"))


def stream_rng(seed: int, *labels: str | int) -> np.random.Generator:
    """Independent Generator for a named stream under a master seed."""
    keys = [(_label_key(x) if isinstance(x, str) else int(x)) for x in labels]
    return np.random.default_rng(np.random.SeedSequence([int(seed), *keys]))


def scenario_seeds(seed: int, purpose: str, n: int) -> np.ndarray:
    """CRN scenario seed list for a purpose in {train, val, test, ...}.

    Different purposes yield disjoint streams; the same (seed, purpose, n
    prefix) always yields the same scenario seeds, and every strategy
    evaluated on a purpose uses the identical list.
    """
    rng = stream_rng(seed, "scenarios", purpose)
    return rng.integers(0, 2**63 - 1, size=n, dtype=np.int64)


def scenario_rng(scenario_seed: int, *labels: str | int) -> np.random.Generator:
    """Generator for one component of one scenario (e.g. 'price', 'flow')."""
    keys = [(_label_key(x) if isinstance(x, str) else int(x)) for x in labels]
    return np.random.default_rng(np.random.SeedSequence([int(scenario_seed), *keys]))
