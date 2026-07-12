from __future__ import annotations

import math

import numpy as np
import torch

from deep_hedge_price.risks import cvar_objective, entropic_risk, mse_risk


def test_mse_matches_numpy():
    values = np.array([-2.0, 0.5, 3.0])
    actual = mse_risk(torch.tensor(values)).item()
    assert np.isclose(actual, np.mean(values**2))


def test_entropic_risk_is_stable_and_correct():
    values = torch.tensor([1000.0, 1001.0, 999.0], dtype=torch.float64)
    gamma = 3.0
    actual = entropic_risk(values, gamma).item()
    maximum = gamma * values.max().item()
    expected = (
        maximum + math.log(np.exp(gamma * values.numpy() - maximum).sum()) - math.log(3)
    ) / gamma
    assert np.isfinite(actual)
    assert np.isclose(actual, expected)


def test_cvar_hand_checked_sample_and_gradient():
    losses = torch.tensor([0.0, 1.0, 2.0, 3.0])
    q = torch.tensor(2.0, requires_grad=True)
    objective = cvar_objective(losses, q, alpha=0.5)
    assert torch.isclose(objective, torch.tensor(2.5))
    objective.backward()
    assert q.grad is not None and torch.isfinite(q.grad)
