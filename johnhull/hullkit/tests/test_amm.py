"""CPMM conservation, concentrated liquidity, and LVR diagnostics."""

import pytest
from hullkit import amm


def test_cpmm_swap_conserves_tokens_and_fee_increases_invariant():
    result = amm.cpmm_swap_x_for_y(100.0, 10_000.0, 10.0, fee_rate=0.003)
    assert result.reserve_x_after == pytest.approx(110.0)
    assert result.reserve_y_before - result.reserve_y_after == pytest.approx(result.amount_out)
    assert result.fee_amount == pytest.approx(0.03)
    assert result.invariant_after >= result.invariant_before


def test_reverse_swap_has_same_accounting_identity():
    result = amm.cpmm_swap_y_for_x(100.0, 10_000.0, 1_000.0, fee_rate=0.003)
    assert result.reserve_y_after == pytest.approx(11_000.0)
    assert result.reserve_x_before - result.reserve_x_after == pytest.approx(result.amount_out)
    assert result.invariant_after >= result.invariant_before


def test_lvr_is_non_negative_and_fee_compensation_is_not_relabelled():
    no_move = amm.loss_versus_rebalancing(100.0, 10_000.0, 100.0)
    assert no_move.gross_lvr == pytest.approx(0.0, abs=1e-12)
    moved = amm.loss_versus_rebalancing(100.0, 10_000.0, 144.0, fee_compensation=5.0)
    assert moved.gross_lvr > 0.0
    assert moved.fee_compensation == pytest.approx(5.0)
    assert moved.net_lvr == pytest.approx(moved.gross_lvr - 5.0)


def test_dynamic_fee_responds_to_volatility_and_inventory_but_is_capped():
    low = amm.dynamic_fee_rate(0.001, 0.001, inventory_skew=0.0)
    high = amm.dynamic_fee_rate(
        0.001,
        0.10,
        inventory_skew=0.8,
        volatility_sensitivity=2.0,
        inventory_sensitivity=0.05,
        max_fee=0.03,
    )
    assert high > low
    assert high == pytest.approx(0.03)


def test_concentrated_liquidity_changes_inventory_at_range_edges():
    low_x, low_y = amm.concentrated_liquidity_amounts(1_000.0, 81.0, 121.0, 80.0)
    mid_x, mid_y = amm.concentrated_liquidity_amounts(1_000.0, 81.0, 121.0, 100.0)
    high_x, high_y = amm.concentrated_liquidity_amounts(1_000.0, 81.0, 121.0, 122.0)
    assert low_x > 0.0 and low_y == 0.0
    assert mid_x > 0.0 and mid_y > 0.0
    assert high_x == 0.0 and high_y > 0.0
    assert amm.concentrated_liquidity_value(1_000.0, 81.0, 121.0, 100.0) == pytest.approx(
        mid_x * 100.0 + mid_y
    )


def test_concentrated_lvr_uses_same_inventory_baseline_and_keeps_fees_separate():
    unchanged = amm.concentrated_loss_versus_rebalancing(
        1_000.0,
        81.0,
        121.0,
        100.0,
        100.0,
    )
    assert unchanged.gross_lvr == pytest.approx(0.0, abs=1e-12)
    moved = amm.concentrated_loss_versus_rebalancing(
        1_000.0,
        81.0,
        121.0,
        100.0,
        110.0,
        fee_compensation=2.0,
    )
    assert moved.gross_lvr > 0.0
    assert moved.net_lvr == pytest.approx(moved.gross_lvr - 2.0)
