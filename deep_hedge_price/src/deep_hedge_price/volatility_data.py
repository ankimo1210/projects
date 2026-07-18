"""Leakage-safe volatility targets and purged walk-forward splits."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WalkForwardSplit:
    train: np.ndarray
    test: np.ndarray
    horizon: int
    embargo: int


@dataclass(frozen=True)
class VolatilityTargets:
    """Separated forecast targets with unavailable tails kept explicit.

    ``log_realized_variance`` and ``future_realized_variance`` are keyed by
    forecast horizon.  ``surface_latent`` contains the future latent vector at
    the same horizons; it is deliberately not folded into a realized-variance
    target because the two prediction problems have different units and loss
    functions.
    """

    log_realized_variance: dict[int, np.ndarray]
    future_realized_variance: dict[int, np.ndarray]
    surface_latent: dict[int, np.ndarray]


def purged_walk_forward_splits(
    n_samples: int,
    *,
    min_train: int,
    test_size: int,
    horizon: int,
    step: int | None = None,
    embargo: int = 0,
    max_train: int | None = None,
) -> tuple[WalkForwardSplit, ...]:
    """Create expanding/rolling splits whose target horizons cannot overlap."""
    if min(n_samples, min_train, test_size, horizon) <= 0 or embargo < 0:
        raise ValueError("sample counts/horizon must be positive and embargo non-negative")
    if max_train is not None and max_train < 1:
        raise ValueError("max_train must be positive when supplied")
    stride = test_size if step is None else step
    if stride <= 0:
        raise ValueError("step must be positive")
    splits: list[WalkForwardSplit] = []
    test_start = min_train + horizon + embargo
    while test_start + test_size <= n_samples:
        train_end = test_start - horizon - embargo
        train_start = 0 if max_train is None else max(0, train_end - max_train)
        train = np.arange(train_start, train_end, dtype=int)
        test = np.arange(test_start, test_start + test_size, dtype=int)
        split = WalkForwardSplit(train=train, test=test, horizon=horizon, embargo=embargo)
        assert_horizon_disjoint(split)
        splits.append(split)
        test_start += stride
    if not splits:
        raise ValueError("configuration produces no walk-forward split")
    return tuple(splits)


def assert_horizon_disjoint(split: WalkForwardSplit) -> None:
    """Reject a split when a train target window reaches the test feature window."""
    if split.horizon <= 0 or split.embargo < 0:
        raise ValueError("horizon must be positive and embargo non-negative")
    if (
        split.train.ndim != 1
        or split.test.ndim != 1
        or len(split.train) == 0
        or len(split.test) == 0
    ):
        raise ValueError("train/test indices must be non-empty one-dimensional arrays")
    if np.any(split.train < 0) or np.any(split.test < 0):
        raise ValueError("train/test indices cannot be negative")
    if np.any(np.diff(split.train) <= 0) or np.any(np.diff(split.test) <= 0):
        raise ValueError("train/test indices must be strictly increasing")
    if len(np.intersect1d(split.train, split.test)):
        raise ValueError("train/test row overlap")
    if int(split.train.max()) + split.horizon + split.embargo >= int(split.test.min()):
        raise ValueError("forecast horizons overlap across train/test")


def realized_variance_targets(
    returns: np.ndarray,
    horizons: tuple[int, ...] = (1, 5, 21),
) -> dict[int, np.ndarray]:
    """Build future log-realized-variance targets with explicit NaN tails.

    The target at row ``t`` uses returns ``t+1`` through ``t+h``.  It never
    reuses a contemporaneous return that may already be among row ``t``'s
    features, and the final ``h`` targets are unavailable.
    """
    values = np.asarray(returns, dtype=float)
    if (
        values.ndim != 1
        or values.size == 0
        or np.any(~np.isfinite(values))
        or not horizons
        or any(horizon <= 0 for horizon in horizons)
        or len(set(horizons)) != len(horizons)
    ):
        raise ValueError("returns must be finite and horizons unique/positive")
    squared = values**2
    targets: dict[int, np.ndarray] = {}
    for horizon in horizons:
        result = np.full(len(values), np.nan)
        if horizon < len(values):
            cumulative = np.concatenate([[0.0], np.cumsum(squared)])
            starts = np.arange(1, len(values) - horizon + 1)
            sums = cumulative[starts + horizon] - cumulative[starts]
            result[: len(sums)] = np.log(np.maximum(sums, np.finfo(float).tiny))
        targets[horizon] = result
    return targets


def build_volatility_targets(
    returns: np.ndarray,
    surface_latents: np.ndarray,
    horizons: tuple[int, ...] = (1, 5, 21),
) -> VolatilityTargets:
    """Build disjoint RV and future-surface target families.

    At row ``t`` the RV target uses returns ``t+1`` through ``t+h`` and the
    surface target is the latent vector observed at ``t+h``.  Missing future
    values remain ``NaN`` instead of being silently imputed into a training
    set.
    """

    values = np.asarray(returns, dtype=float)
    latents = np.asarray(surface_latents, dtype=float)
    if (
        values.ndim != 1
        or latents.ndim != 2
        or len(latents) != len(values)
        or latents.shape[1] < 1
        or np.any(~np.isfinite(latents))
    ):
        raise ValueError("surface_latents must be a finite matrix aligned with returns")
    log_rv = realized_variance_targets(values, horizons)
    future_rv = {horizon: np.exp(target) for horizon, target in log_rv.items()}
    future_latents: dict[int, np.ndarray] = {}
    for horizon in horizons:
        target = np.full(latents.shape, np.nan)
        if horizon < len(latents):
            target[:-horizon] = latents[horizon:]
        future_latents[horizon] = target
    return VolatilityTargets(
        log_realized_variance=log_rv,
        future_realized_variance=future_rv,
        surface_latent=future_latents,
    )


@dataclass(frozen=True)
class TrainWindowStandardizer:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, features: np.ndarray, train_indices: np.ndarray) -> TrainWindowStandardizer:
        values = np.asarray(features, dtype=float)
        indices = np.asarray(train_indices, dtype=int)
        if values.ndim != 2 or indices.ndim != 1 or len(indices) == 0:
            raise ValueError("features must be 2-D with non-empty train indices")
        if np.any(~np.isfinite(values)):
            raise ValueError("features must be finite")
        if (
            np.any(indices < 0)
            or np.any(indices >= len(values))
            or len(np.unique(indices)) != len(indices)
        ):
            raise ValueError("train indices must be unique and in bounds")
        train = values[indices]
        scale = train.std(axis=0)
        return cls(mean=train.mean(axis=0), scale=np.where(scale > 0, scale, 1.0))

    def transform(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim != 2 or values.shape[1:] != self.mean.shape:
            raise ValueError("features must match the fitted feature dimension")
        if np.any(~np.isfinite(values)):
            raise ValueError("features must be finite")
        return (values - self.mean) / self.scale


@dataclass(frozen=True)
class TrainWindowPCA:
    """PCA fitted only on one walk-forward training window."""

    mean: np.ndarray
    components: np.ndarray
    explained_variance: np.ndarray

    @classmethod
    def fit(
        cls,
        features: np.ndarray,
        train_indices: np.ndarray,
        *,
        n_components: int,
    ) -> TrainWindowPCA:
        values = np.asarray(features, dtype=float)
        indices = np.asarray(train_indices, dtype=int)
        if values.ndim != 2 or np.any(~np.isfinite(values)):
            raise ValueError("features must be a finite 2-D matrix")
        if (
            indices.ndim != 1
            or len(indices) < 2
            or np.any(indices < 0)
            or np.any(indices >= len(values))
            or len(np.unique(indices)) != len(indices)
        ):
            raise ValueError("train indices must be unique, in bounds, and contain two rows")
        maximum = min(len(indices), values.shape[1])
        if not isinstance(n_components, int) or not 1 <= n_components <= maximum:
            raise ValueError("n_components exceeds the training-window rank bound")
        train = values[indices]
        mean = train.mean(axis=0)
        _, singular_values, right_vectors = np.linalg.svd(train - mean, full_matrices=False)
        explained = singular_values[:n_components] ** 2 / (len(train) - 1)
        return cls(
            mean=mean,
            components=right_vectors[:n_components],
            explained_variance=explained,
        )

    def transform(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=float)
        if values.ndim != 2 or values.shape[1] != self.mean.size:
            raise ValueError("features must match the fitted feature dimension")
        if np.any(~np.isfinite(values)):
            raise ValueError("features must be finite")
        return (values - self.mean) @ self.components.T
