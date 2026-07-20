from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lob_reproductions.data.fi2010 import (
    FI2010_HORIZONS,
    FI2010_INSTRUMENTS,
    FI2010Matrix,
    build_windows,
)


class FI2010MatrixFixture:
    """Exact-row-layout FI-2010 fixture with visible transpose mistakes.

    Generation is fully deterministic (no RNG), so there is no seed parameter:
    every instantiation produces the identical matrix.
    """

    def __init__(
        self,
        *,
        observations_per_day: int = 180,
        days_per_instrument: int = 2,
    ) -> None:
        if observations_per_day < 128:
            raise ValueError("fixture needs at least 128 observations per day")
        self.observations_per_day = observations_per_day
        self.days_per_instrument = days_per_instrument
        self.matrix = self._build()

    def _build(self) -> FI2010Matrix:
        n_assets = len(FI2010_INSTRUMENTS)
        n = n_assets * self.days_per_instrument * self.observations_per_day
        column = np.arange(n, dtype=np.float64)
        values = np.empty((149, n), dtype=np.float64)
        # Every row and observation has a unique decimal signature. The four raw fields
        # retain the canonical ask-price, ask-volume, bid-price, bid-volume row order.
        for row in range(144):
            values[row] = row * 1_000_000.0 + column + (row % 4) * 0.01
        for label_index, _horizon in enumerate(FI2010_HORIZONS):
            values[144 + label_index] = ((column.astype(np.int64) + label_index) % 3) + 1

        asset_id = np.repeat(
            np.arange(n_assets, dtype=np.int16),
            self.days_per_instrument * self.observations_per_day,
        )
        day_pattern = np.repeat(
            np.arange(self.days_per_instrument, dtype=np.int16), self.observations_per_day
        )
        day_id = np.tile(day_pattern, n_assets)
        return FI2010Matrix(values=values, asset_id=asset_id, day_id=day_id)

    @property
    def latent_truth(self) -> dict[str, object]:
        return {
            "shape": self.matrix.values.shape,
            "raw_rows": (0, 40),
            "engineered_rows": (40, 144),
            "label_rows": {horizon: 144 + i for i, horizon in enumerate(FI2010_HORIZONS)},
            "instrument_order": FI2010_INSTRUMENTS,
            "day_boundaries": np.flatnonzero(np.diff(self.matrix.boundary_id()) != 0) + 1,
        }


@dataclass(frozen=True)
class DeepLOBWindowFixture:
    features: np.ndarray
    labels: np.ndarray
    endpoint_index: np.ndarray
    asset_id: np.ndarray
    day_id: np.ndarray

    @classmethod
    def generate(
        cls,
        *,
        sequence_length: int = 100,
        horizon: int = 100,
        stride: int = 20,
    ) -> DeepLOBWindowFixture:
        source = FI2010MatrixFixture().matrix
        windows = build_windows(
            source,
            sequence_length=sequence_length,
            horizon=horizon,
            all_features=False,
            stride=stride,
        )
        return cls(
            features=windows.features,
            labels=windows.labels,
            endpoint_index=windows.endpoint_index,
            asset_id=windows.asset_id,
            day_id=windows.day_id,
        )

    def tensorflow_layout(self) -> np.ndarray:
        return self.features[..., np.newaxis]

    def pytorch_layout(self) -> np.ndarray:
        return self.features[:, np.newaxis, :, :]


@dataclass(frozen=True)
class TLOBWindowFixture:
    features: np.ndarray
    labels: np.ndarray
    endpoint_index: np.ndarray
    asset_id: np.ndarray
    day_id: np.ndarray

    @classmethod
    def generate(
        cls,
        *,
        sequence_length: int = 128,
        horizon: int = 100,
        stride: int = 32,
    ) -> TLOBWindowFixture:
        source = FI2010MatrixFixture().matrix
        windows = build_windows(
            source,
            sequence_length=sequence_length,
            horizon=horizon,
            all_features=True,
            stride=stride,
        )
        return cls(
            features=windows.features,
            labels=windows.labels,
            endpoint_index=windows.endpoint_index,
            asset_id=windows.asset_id,
            day_id=windows.day_id,
        )
