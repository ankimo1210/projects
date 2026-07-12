from __future__ import annotations

from dataclasses import replace

import pytest

from deep_hedge_price.config import ProjectConfig


@pytest.fixture
def tiny_config() -> ProjectConfig:
    base = ProjectConfig()
    return replace(
        base,
        profile="test",
        market=replace(
            base.market,
            maturity_years=5 / 252,
            n_steps=5,
            antithetic_sampling=True,
        ),
        policy=replace(base.policy, hidden_layers=2, hidden_units=16),
        training=replace(
            base.training,
            device="cpu",
            batch_size=512,
            epochs=18,
            validation_paths=1024,
            test_paths=2048,
            early_stopping_patience=18,
            evaluation_chunk_size=512,
        ),
    )
