"""Hull §25.8 dollar waterfall, independently allocated by seniority."""

import numpy as np
import pytest
from hullkit import _credit_portfolio_extensions as e


def test_source_100m_capital_structure_and_two_six_million_losses():
    result = e.loss_waterfall(
        [0, 2_000_000, 6_000_000], 100_000_000, [0, 0.05, 0.20, 1], spreads=[0.1, 0.01, 0.001]
    )
    assert result["initial"] == pytest.approx([5_000_000, 15_000_000, 80_000_000])
    assert result["remaining"][1] == pytest.approx([3_000_000, 15_000_000, 80_000_000])
    assert result["remaining"][2] == pytest.approx([0, 14_000_000, 80_000_000])
    assert result["annual_premium"][2] == pytest.approx([0, 140_000, 80_000])
    assert result["allocated_loss"][2] == pytest.approx([5_000_000, 1_000_000, 0])


def test_arbitrary_losses_against_sequential_cash_allocation_and_conservation():
    losses = [0, 1.234, 5, 5.0001, 20, 53.72, 100]
    result = e.loss_waterfall(losses, 100, [0, 0.05, 0.20, 1])
    expected = []
    for loss in losses:
        allocation = []
        remaining = loss
        for initial in (5, 15, 80):
            paid = min(initial, remaining)
            allocation.append(paid)
            remaining -= paid
        expected.append(allocation)
    assert result["allocated_loss"] == pytest.approx(np.array(expected))
    assert result["allocated_loss"].sum(axis=-1) == pytest.approx(losses)
    assert result["remaining"].sum(axis=-1) == pytest.approx(100 - np.array(losses))
    with pytest.raises(ValueError):
        e.loss_waterfall(101, 100, [0, 0.05, 0.20, 1])
