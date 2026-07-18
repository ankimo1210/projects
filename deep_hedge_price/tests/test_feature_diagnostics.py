import numpy as np
import pytest
import torch
from torch import nn

from deep_hedge_price.feature_diagnostics import (
    diagnostic_rank_stability,
    integrated_gradients,
    occlusion_importance,
    permutation_importance,
)


def test_permutation_occlusion_and_integrated_gradients_are_diagnostics():
    rng = np.random.default_rng(2)
    x = rng.normal(size=(100, 3))
    y = 3 * x[:, 0] + 0.1 * x[:, 1]

    def predict(values):
        return 3 * values[:, 0] + 0.1 * values[:, 1]

    permutation = permutation_importance(predict, x, y, seed=2)
    occlusion = occlusion_importance(predict, x, y)
    assert np.argmax(permutation) == 0
    assert np.argmax(occlusion) == 0
    assert diagnostic_rank_stability(permutation, occlusion) > 0

    model = nn.Linear(3, 1, bias=False).double()
    with torch.no_grad():
        model.weight.copy_(torch.tensor([[3.0, 0.1, 0.0]], dtype=torch.float64))
    inputs = torch.tensor(x[:4], dtype=torch.float64)
    attribution = integrated_gradients(model, inputs, steps=16)
    assert attribution.shape == inputs.shape
    expected = inputs * torch.tensor([3.0, 0.1, 0.0], dtype=torch.float64)
    torch.testing.assert_close(attribution, expected)


def test_diagnostics_reject_prediction_broadcasting():
    features = np.ones((4, 2))
    targets = np.ones(4)
    with pytest.raises(ValueError, match="one finite value"):
        permutation_importance(lambda _features: np.array([1.0]), features, targets)
