from __future__ import annotations

from dataclasses import replace

import numpy as np

from deep_hedge_price.pricing_artifacts import assert_disjoint_splits
from deep_hedge_price.pricing_config import PricingConfig
from deep_hedge_price.pricing_data import (
    FEATURE_NAMES,
    black_scholes_labels,
    generate_black_scholes_splits,
)


def _config():
    base = PricingConfig()
    return replace(
        base,
        profile="test",
        data=replace(base.data, train_size=64, validation_size=32, test_size=32, ood_size=32),
    )


def test_splits_are_reproducible_disjoint_and_ood_is_explicit():
    config = _config()
    first = generate_black_scholes_splits(config)
    second = generate_black_scholes_splits(config)
    rows = {name: split["inputs"] for name, split in first.items()}
    assert_disjoint_splits(rows)
    assert all(np.array_equal(first[name]["inputs"], second[name]["inputs"]) for name in first)
    bounds = np.asarray([config.data.bounds[name] for name in FEATURE_NAMES])
    ood = first["ood"]["inputs"]
    assert np.all(np.any((ood < bounds[:, 0]) | (ood > bounds[:, 1]), axis=1))


def test_dimensionless_labels_match_hullkit_reference():
    from hullkit import bsm

    inputs = np.array([[1.1, 0.7, 0.03, 0.01, 0.25]])
    labels = black_scholes_labels(inputs)
    assert labels["price"][0] == bsm.call_price(1.1, 1.0, 0.03, 0.25, 0.7, 0.01)
    assert labels["delta"][0] == bsm.call_delta(1.1, 1.0, 0.03, 0.25, 0.7, 0.01)
    assert labels["gamma"][0] == bsm.gamma(1.1, 1.0, 0.03, 0.25, 0.7, 0.01)
