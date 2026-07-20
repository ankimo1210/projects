from __future__ import annotations

from dataclasses import dataclass

import numpy as np

FI2010_INSTRUMENTS = ("KESBV", "OUT1V", "SAMPO", "RTRKS", "WRT1V")
FI2010_HORIZONS = (10, 20, 30, 50, 100)
FI2010_LABEL_ROWS = {horizon: 144 + index for index, horizon in enumerate(FI2010_HORIZONS)}
FI2010_CLASS_NAMES = ("up", "stationary", "down")


def raw_feature_names() -> tuple[str, ...]:
    names: list[str] = []
    for level in range(1, 11):
        names.extend(
            (
                f"ask_price_l{level}",
                f"ask_volume_l{level}",
                f"bid_price_l{level}",
                f"bid_volume_l{level}",
            )
        )
    return tuple(names)


@dataclass(frozen=True)
class FI2010Matrix:
    values: np.ndarray
    asset_id: np.ndarray
    day_id: np.ndarray
    instrument_order: tuple[str, ...] = FI2010_INSTRUMENTS

    def __post_init__(self) -> None:
        values = np.asarray(self.values)
        if values.ndim != 2 or values.shape[0] != 149:
            raise ValueError(f"FI-2010 matrix must have shape [149, N], got {values.shape}")
        if self.asset_id.shape != (values.shape[1],) or self.day_id.shape != (values.shape[1],):
            raise ValueError("asset_id and day_id must align to observations")
        labels = values[144:149]
        if not np.all(np.isin(labels, (1, 2, 3))):
            raise ValueError("FI-2010 source labels must be in {1,2,3}")

    @property
    def n_observations(self) -> int:
        return self.values.shape[1]

    def features(self, *, all_features: bool) -> np.ndarray:
        stop = 144 if all_features else 40
        return self.values[:stop].T.astype(np.float32, copy=False)

    def labels(self, horizon: int, *, zero_based: bool = True) -> np.ndarray:
        try:
            row = FI2010_LABEL_ROWS[horizon]
        except KeyError as exc:
            raise ValueError(f"unsupported FI-2010 horizon: {horizon}") from exc
        labels = self.values[row].astype(np.int64, copy=True)
        return labels - 1 if zero_based else labels

    def boundary_id(self) -> np.ndarray:
        return self.asset_id.astype(np.int64) * 10_000 + self.day_id.astype(np.int64)


@dataclass(frozen=True)
class WindowedLOB:
    features: np.ndarray
    labels: np.ndarray
    endpoint_index: np.ndarray
    asset_id: np.ndarray
    day_id: np.ndarray
    horizon: int
    feature_count: int


def build_windows(
    matrix: FI2010Matrix,
    *,
    sequence_length: int,
    horizon: int,
    all_features: bool,
    stride: int = 1,
) -> WindowedLOB:
    if sequence_length <= 0 or stride <= 0:
        raise ValueError("sequence_length and stride must be positive")
    features = matrix.features(all_features=all_features)
    labels = matrix.labels(horizon)
    boundary = matrix.boundary_id()
    windows: list[np.ndarray] = []
    endpoints: list[int] = []
    for end in range(sequence_length - 1, matrix.n_observations, stride):
        start = end - sequence_length + 1
        if boundary[start] != boundary[end]:
            continue
        if not np.all(boundary[start : end + 1] == boundary[end]):
            continue
        windows.append(features[start : end + 1])
        endpoints.append(end)
    if not windows:
        raise ValueError("no valid windows for the requested sequence length")
    endpoint_array = np.asarray(endpoints, dtype=np.int64)
    return WindowedLOB(
        features=np.stack(windows).astype(np.float32, copy=False),
        labels=labels[endpoint_array],
        endpoint_index=endpoint_array,
        asset_id=matrix.asset_id[endpoint_array],
        day_id=matrix.day_id[endpoint_array],
        horizon=horizon,
        feature_count=features.shape[1],
    )
