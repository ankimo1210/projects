from __future__ import annotations

import json
from dataclasses import replace

import torch

from deep_hedge_price.pricing_config import PricingConfig, pricing_run_directory
from deep_hedge_price.pricing_data import generate_black_scholes_dataset
from deep_hedge_price.pricing_training import load_pricing_model, train_pricing_model


def tiny_pricing_config():
    base = PricingConfig()
    return replace(
        base,
        profile="test",
        data=replace(base.data, train_size=512, validation_size=128, test_size=128, ood_size=128),
        model=replace(base.model, hidden_layers=2, hidden_units=32),
        training=replace(
            base.training,
            batch_size=128,
            epochs=35,
            early_stopping_patience=12,
            differential_weight=0.0,
            penalty_weight=0.0,
        ),
        output=replace(base.output, namespace="test"),
    )


def test_pricing_training_reloads_best_checkpoint(tmp_path):
    config = tiny_pricing_config()
    run = pricing_run_directory(config, tmp_path)
    manifest, _ = generate_black_scholes_dataset(config, run)
    result = train_pricing_model(config, manifest, tmp_path, force=True)
    history = json.loads(result.history_path.read_text())
    assert result.checkpoint_path.exists() and result.polynomial_path.exists()
    assert min(row["validation_price_mae"] for row in history) < 0.04
    loaded, payload = load_pricing_model(result.checkpoint_path)
    assert payload["artifact_kind"] == "pricing_checkpoint"
    assert all(
        torch.equal(a, b)
        for a, b in zip(
            result.model.state_dict().values(), loaded.state_dict().values(), strict=True
        )
    )
    reused = train_pricing_model(config, manifest, tmp_path)
    assert reused.reused
