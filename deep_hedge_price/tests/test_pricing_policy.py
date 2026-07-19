from __future__ import annotations

import numpy as np
import torch

from deep_hedge_price.pricing_config import PricingModelConfig
from deep_hedge_price.pricing_policy import PolynomialRidge, PricingMLP


def test_polynomial_fit_predict_and_round_trip(tmp_path):
    rng = np.random.default_rng(1)
    inputs = rng.normal(size=(100, 5))
    target = 0.2 + inputs @ np.array([1.0, -0.5, 0.3, 0.2, -0.1]) + 0.4 * inputs[:, 0] ** 2
    model = PolynomialRidge(degree=2, alpha=1e-12).fit(inputs, target)
    assert np.max(np.abs(model.predict(inputs) - target)) < 1e-9
    path = model.save(tmp_path / "polynomial.npz")
    assert np.array_equal(PolynomialRidge.load(path).predict(inputs), model.predict(inputs))


def test_mlp_normalization_is_part_of_state_dict():
    model = PricingMLP(PricingModelConfig(hidden_layers=1, hidden_units=8))
    model.set_normalization(np.arange(5), np.arange(1, 6))
    state = model.state_dict()
    assert torch.equal(state["feature_mean"], torch.arange(5, dtype=torch.float64))
    assert torch.equal(state["feature_scale"], torch.arange(1, 6, dtype=torch.float64))
    assert model(torch.ones((3, 5), dtype=torch.float64)).shape == (3,)


def test_time_value_variant_respects_discounted_intrinsic():
    model = PricingMLP(
        PricingModelConfig(hidden_layers=1, hidden_units=8, output_mode="time_value")
    )
    inputs = torch.tensor([[1.2, 1.0, 0.03, 0.01, 0.2]], dtype=torch.float64)
    price = model(inputs)
    lower = inputs[:, 0] * torch.exp(-inputs[:, 3] * inputs[:, 1]) - torch.exp(
        -inputs[:, 2] * inputs[:, 1]
    )
    assert torch.all(price >= lower)
