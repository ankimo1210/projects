from __future__ import annotations

from typing import Any

import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

from lob_reproductions.fixtures.universal import UniversalMultiAssetEventFixture

from .paper_constrained import PaperConstrainedUniversalLSTM


def _flatten_events(
    fixture: UniversalMultiAssetEventFixture, asset_ids: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    features = fixture.features[asset_ids].reshape(-1, fixture.features.shape[-1])
    labels = fixture.labels[asset_ids].reshape(-1)
    assets = np.repeat(asset_ids, fixture.events_per_asset)
    return features, labels, assets


def run_synthetic_linear_comparison(
    fixture: UniversalMultiAssetEventFixture,
) -> dict[str, Any]:
    """Cheap protocol baseline; the LSTM itself is validated separately."""

    train_x, train_y, train_asset = _flatten_events(fixture, fixture.training_asset_ids)
    unseen_x, unseen_y, unseen_asset = _flatten_events(fixture, fixture.unseen_asset_ids)
    universal = LogisticRegression(C=1e6, max_iter=500, random_state=fixture.seed)
    universal.fit(train_x, train_y)
    universal_unseen_accuracy = accuracy_score(unseen_y, universal.predict(unseen_x))

    asset_specific: dict[str, float] = {}
    for asset in fixture.training_asset_ids:
        mask = train_asset == asset
        split = int(mask.sum() * 0.8)
        x = train_x[mask]
        y = train_y[mask]
        model = LogisticRegression(C=1e6, max_iter=500, random_state=fixture.seed)
        model.fit(x[:split], y[:split])
        asset_specific[str(int(asset))] = float(accuracy_score(y[split:], model.predict(x[split:])))

    per_unseen: dict[str, float] = {}
    prediction = universal.predict(unseen_x)
    for asset in fixture.unseen_asset_ids:
        mask = unseen_asset == asset
        per_unseen[str(int(asset))] = float(accuracy_score(unseen_y[mask], prediction[mask]))
    return {
        "asset_specific_linear_accuracy": asset_specific,
        "universal_pooled_linear_unseen_accuracy": float(universal_unseen_accuracy),
        "universal_pooled_linear_by_unseen_asset": per_unseen,
        "claim_limit": "synthetic protocol test only",
    }


def run_synthetic_lstm_comparison(
    fixture: UniversalMultiAssetEventFixture,
    *,
    history: int = 20,
    stride: int = 10,
    hidden_units: int = 8,
    epochs: int = 15,
    learning_rate: float = 0.02,
    optimizer_name: str = "Adam",
) -> dict[str, Any]:
    """Scaled CPU protocol for asset-specific, pooled, and unseen-asset LSTMs.

    The optimizer and dimensions are arguments because the paper leaves important
    lifecycle details unresolved. Results are plumbing checks, never paper evidence.
    """

    if epochs <= 0:
        raise ValueError("epochs must be positive")

    def train_model(features: np.ndarray, labels: np.ndarray, seed: int):
        torch.manual_seed(seed)
        model = PaperConstrainedUniversalLSTM(
            input_features=features.shape[-1], hidden_units=hidden_units
        )
        if optimizer_name == "Adam":
            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        elif optimizer_name == "SGD":
            optimizer = torch.optim.SGD(model.parameters(), lr=learning_rate)
        else:
            raise ValueError(f"unsupported optimizer: {optimizer_name}")
        tensor = torch.from_numpy(features).float()
        targets = torch.from_numpy(labels).long()
        model.train()
        for _ in range(epochs):
            optimizer.zero_grad(set_to_none=True)
            logits, _ = model(tensor)
            loss = torch.nn.functional.cross_entropy(logits, targets)
            loss.backward()
            optimizer.step()
        return model, float(loss.detach())

    def accuracy(model: PaperConstrainedUniversalLSTM, features: np.ndarray, labels: np.ndarray):
        model.eval()
        with torch.no_grad():
            logits, _ = model(torch.from_numpy(features).float())
        return float((logits.argmax(dim=1).numpy() == labels).mean())

    asset_specific: dict[str, float] = {}
    for asset in fixture.training_asset_ids:
        histories = fixture.histories(history=history, asset_ids=np.asarray([asset]), stride=stride)
        split = max(1, int(histories.labels.size * 0.8))
        model, _ = train_model(
            histories.features[:split], histories.labels[:split], fixture.seed + int(asset)
        )
        asset_specific[str(int(asset))] = accuracy(
            model, histories.features[split:], histories.labels[split:]
        )

    pooled = fixture.histories(history=history, asset_ids=fixture.training_asset_ids, stride=stride)
    unseen = fixture.histories(history=history, asset_ids=fixture.unseen_asset_ids, stride=stride)
    pooled_model, final_training_loss = train_model(pooled.features, pooled.labels, fixture.seed)
    return {
        "asset_specific_lstm_accuracy": asset_specific,
        "universal_pooled_lstm_unseen_accuracy": accuracy(
            pooled_model, unseen.features, unseen.labels
        ),
        "universal_pooled_final_training_loss": final_training_loss,
        "configuration": {
            "history": history,
            "stride": stride,
            "hidden_units": hidden_units,
            "epochs": epochs,
            "optimizer": optimizer_name,
            "learning_rate": learning_rate,
        },
        "claim_limit": "scaled synthetic LSTM protocol test only",
    }
