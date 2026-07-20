import numpy as np
import pytest
import torch

from deep_hedge_price.research_models import (
    DirectInverseNetwork,
    LocalFoundationAdapter,
    conditional_diffusion_scenarios,
    scenario_hard_check_rate,
)


def test_direct_inverse_is_explicit_research_ablation():
    model = DirectInverseNetwork(8, 3)
    assert model.research_only
    assert model(torch.ones(4, 8)).shape == (4, 3)


def test_foundation_adapter_requires_explicit_local_model():
    with pytest.raises(RuntimeError, match="disabled"):
        LocalFoundationAdapter(None)
    adapter = LocalFoundationAdapter(lambda x: x[:, -1])
    np.testing.assert_array_equal(
        adapter.predict(np.arange(12).reshape(3, 4)), np.array([3, 7, 11])
    )


def test_diffusion_scenarios_are_seeded_and_hard_checked():
    history = np.linspace(0.02, 0.04, 30)
    first = conditional_diffusion_scenarios(history, horizon=5, n_scenarios=10, seed=9)
    second = conditional_diffusion_scenarios(history, horizon=5, n_scenarios=10, seed=9)
    np.testing.assert_array_equal(first, second)
    assert scenario_hard_check_rate(first, lambda path: np.all(np.isfinite(path))) == 1.0
