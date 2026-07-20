from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class UniversalHistories:
    features: np.ndarray
    labels: np.ndarray
    asset_id: np.ndarray
    day_id: np.ndarray
    endpoint_index: np.ndarray
    unseen_asset: np.ndarray


class UniversalMultiAssetEventFixture:
    """Shared nonlinear price map plus weak stock-specific dynamics.

    This fixture validates the pooled/unseen-asset protocol only. It is not
    evidence for the paper's empirical universal-feature conclusion.
    """

    feature_names = (
        "queue_imbalance",
        "order_flow",
        "spread",
        "log_depth",
        "recent_direction",
        "relative_price",
        "event_intensity",
        "stock_specific_state",
    )

    def __init__(
        self,
        *,
        assets: int = 6,
        training_assets: int = 4,
        events_per_asset: int = 600,
        events_per_day: int = 200,
        seed: int = 7,
        universal_mapping: bool = True,
    ) -> None:
        if not 1 < training_assets < assets:
            raise ValueError("training_assets must leave at least one unseen asset")
        self.assets = assets
        self.training_assets = training_assets
        self.events_per_asset = events_per_asset
        self.events_per_day = events_per_day
        self.seed = seed
        self.universal_mapping = universal_mapping
        self.sector = np.arange(assets, dtype=np.int8) % 3
        self.features, self.labels, self.mid_prices = self._build()

    def _build(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        rng = np.random.default_rng(self.seed)
        features = np.zeros((self.assets, self.events_per_asset, 8), dtype=np.float32)
        labels = np.zeros((self.assets, self.events_per_asset), dtype=np.int64)
        mids = np.zeros((self.assets, self.events_per_asset + 1), dtype=np.float64)
        for asset in range(self.assets):
            mids[asset, 0] = 50.0 + 5.0 * asset
            flow = 0.0
            previous_direction = 0.0
            asset_bias = (asset - (self.assets - 1) / 2) * 0.025
            phase = asset * 0.41
            for event in range(self.events_per_asset):
                queue = np.tanh(0.85 * np.sin(event * 0.071 + phase) + 0.3 * rng.normal())
                flow = 0.74 * flow + 0.26 * rng.normal()
                spread = 0.01 * (1 + (asset % 3))
                depth = 4.0 + 0.4 * asset + abs(rng.normal())
                intensity = 1.0 + 0.2 * np.cos(event * 0.033 + phase)
                relative_price = (mids[asset, event] - mids[asset, 0]) / mids[asset, 0]
                stock_state = np.sin(event * (0.01 + asset * 0.001) + phase)
                features[asset, event] = (
                    queue,
                    flow,
                    spread,
                    np.log1p(depth),
                    previous_direction,
                    relative_price,
                    intensity,
                    stock_state,
                )
                if self.universal_mapping:
                    score = 1.7 * queue + 0.8 * flow - 3.0 * spread + 0.15 * stock_state
                else:
                    sign = 1.0 if asset % 2 == 0 else -1.0
                    score = sign * (1.7 * queue + 0.8 * flow) + 0.15 * stock_state
                score += asset_bias + 0.35 * rng.normal()
                direction = 1 if score > 0 else -1
                labels[asset, event] = int(direction > 0)
                mids[asset, event + 1] = mids[asset, event] + direction * 0.01
                previous_direction = float(direction)
        return features, labels, mids

    @property
    def training_asset_ids(self) -> np.ndarray:
        return np.arange(self.training_assets, dtype=np.int64)

    @property
    def unseen_asset_ids(self) -> np.ndarray:
        return np.arange(self.training_assets, self.assets, dtype=np.int64)

    @property
    def latent_truth(self) -> dict[str, object]:
        return {
            "universal_mapping": self.universal_mapping,
            "training_assets": self.training_asset_ids.tolist(),
            "unseen_assets": self.unseen_asset_ids.tolist(),
            "sectors": self.sector.tolist(),
            "feature_names": self.feature_names,
        }

    def histories(
        self,
        *,
        history: int = 100,
        asset_ids: np.ndarray | None = None,
        stride: int = 25,
    ) -> UniversalHistories:
        if history <= 0 or history > self.events_per_day:
            raise ValueError("history must fit inside one synthetic day")
        selected_assets = (
            np.arange(self.assets, dtype=np.int64) if asset_ids is None else np.asarray(asset_ids)
        )
        windows: list[np.ndarray] = []
        targets: list[int] = []
        assets: list[int] = []
        days: list[int] = []
        endpoints: list[int] = []
        for asset in selected_assets:
            for end in range(history - 1, self.events_per_asset, stride):
                start = end - history + 1
                if start // self.events_per_day != end // self.events_per_day:
                    continue
                windows.append(self.features[asset, start : end + 1])
                targets.append(int(self.labels[asset, end]))
                assets.append(int(asset))
                days.append(end // self.events_per_day)
                endpoints.append(end)
        if not windows:
            raise ValueError("no histories generated")
        asset_array = np.asarray(assets, dtype=np.int64)
        return UniversalHistories(
            features=np.stack(windows),
            labels=np.asarray(targets, dtype=np.int64),
            asset_id=asset_array,
            day_id=np.asarray(days, dtype=np.int64),
            endpoint_index=np.asarray(endpoints, dtype=np.int64),
            unseen_asset=asset_array >= self.training_assets,
        )
