from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lob_reproductions.fixtures.queue_imbalance import QueueObservations


@dataclass(frozen=True)
class ObservationSplit:
    train_index: np.ndarray
    test_index: np.ndarray


def split_observations(
    observations: QueueObservations,
    *,
    train_fraction: float = 0.8,
    strategy: str = "random",
    seed: int = 7,
) -> ObservationSplit:
    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be in (0,1)")
    count = observations.response.size
    train_count = int(np.floor(count * train_fraction))
    if strategy == "random":
        order = np.random.default_rng(seed).permutation(count)
    elif strategy == "chronological":
        order = np.lexsort((observations.sampled_time, observations.day))
    else:
        raise ValueError(f"unknown split strategy: {strategy}")
    return ObservationSplit(train_index=order[:train_count], test_index=order[train_count:])
