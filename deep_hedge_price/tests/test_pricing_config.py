from __future__ import annotations

from pathlib import Path

import pytest

from deep_hedge_price.config import ProjectConfig
from deep_hedge_price.pricing_config import PricingConfig, load_pricing_config


def test_pricing_profiles_are_separate_and_valid():
    root = Path(__file__).parents[1]
    fingerprints = set()
    for name in ("quick", "default", "full"):
        config = load_pricing_config(root / "configs" / f"pricing_{name}.yaml")
        assert isinstance(config, PricingConfig)
        assert not isinstance(config, ProjectConfig)
        assert config.profile == name
        fingerprints.add(config.fingerprint())
    assert len(fingerprints) == 3


def test_pricing_config_rejects_unsafe_namespace(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("output:\n  namespace: ../hedge\n", encoding="utf-8")
    with pytest.raises(ValueError, match="namespace"):
        load_pricing_config(path)
