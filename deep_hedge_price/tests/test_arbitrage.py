from __future__ import annotations

import pytest
import torch

from deep_hedge_price.arbitrage import price_bound_penalty, structured_surface_penalty


def test_reference_surface_has_zero_penalties_and_broken_surface_positive():
    inputs = torch.tensor([[1.0, 1.0, 0.0, 0.0, 0.2]], dtype=torch.float64)
    assert price_bound_penalty(torch.tensor([0.1]), inputs).item() == 0.0
    assert price_bound_penalty(torch.tensor([2.0]), inputs).item() > 0
    strikes = torch.tensor([90.0, 100.0, 110.0])
    good = torch.tensor([15.0, 10.0, 7.0])
    bad = torch.tensor([15.0, 10.0, 12.0])
    assert structured_surface_penalty(good, strikes=strikes).item() == 0.0
    assert structured_surface_penalty(bad, strikes=strikes).item() > 0


def test_structured_penalty_does_not_sort():
    with pytest.raises(ValueError, match="strictly increasing"):
        structured_surface_penalty(torch.tensor([1.0, 2.0]), strikes=torch.tensor([2.0, 1.0]))
