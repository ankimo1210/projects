from __future__ import annotations

import math
from dataclasses import replace

import torch

from deep_hedge_price.config import MarketConfig
from deep_hedge_price.pnl import account_hedge, reporting_premium


def test_exact_one_step_short_call_accounting():
    config = MarketConfig(
        maturity_years=1.0,
        n_steps=1,
        risk_free_rate=0.0,
        transaction_cost_bps=10.0,
    )
    paths = torch.tensor([[100.0, 110.0]])
    deltas = torch.tensor([[0.5]])
    result = account_hedge(paths, deltas, config)
    assert torch.allclose(result.gross_trading_gain, torch.tensor([5.0]))
    assert torch.allclose(result.transaction_cost, torch.tensor([0.05]))
    assert torch.allclose(result.net_trading_gain, torch.tensor([4.95]))
    assert torch.allclose(result.payoff, torch.tensor([10.0]))
    assert torch.allclose(result.loss_excluding_premium, torch.tensor([5.05]), atol=1e-6)
    expected_pnl = reporting_premium(config) - 5.05
    assert torch.allclose(result.pnl_including_premium, torch.tensor([expected_pnl]), atol=1e-5)


def test_zero_position_has_payoff_loss_and_no_cost():
    config = MarketConfig(maturity_years=1, n_steps=1)
    result = account_hedge(torch.tensor([[100.0, 120.0]]), torch.zeros((1, 1)), config)
    assert result.net_trading_gain.item() == 0
    assert result.transaction_cost.item() == 0
    assert result.loss_excluding_premium.item() == 20
    assert math.isclose(result.pnl_including_premium.item(), result.premium - 20, abs_tol=1e-6)


def test_transaction_cost_can_only_reduce_pnl():
    paths = torch.tensor([[100.0, 105.0, 103.0]])
    deltas = torch.tensor([[0.4, 0.8]])
    free = MarketConfig(maturity_years=1, n_steps=2, transaction_cost_bps=0)
    costly = replace(free, transaction_cost_bps=25)
    free_result = account_hedge(paths, deltas, free)
    costly_result = account_hedge(paths, deltas, costly)
    assert costly_result.transaction_cost.item() > 0
    assert costly_result.pnl_including_premium.item() < free_result.pnl_including_premium.item()


def test_discounted_accounting_matches_hand_calculation():
    rate = 0.10
    config = MarketConfig(
        maturity_years=1,
        n_steps=1,
        risk_free_rate=rate,
        transaction_cost_bps=0,
    )
    paths = torch.tensor([[100.0, 110.0]])
    result = account_hedge(paths, torch.tensor([[0.5]]), config)
    discounted_terminal = 110 * math.exp(-rate)
    expected_gain = 0.5 * (discounted_terminal - 100)
    expected_payoff = 10 * math.exp(-rate)
    assert math.isclose(result.net_trading_gain.item(), expected_gain, abs_tol=1e-5)
    assert math.isclose(result.payoff.item(), expected_payoff, abs_tol=1e-5)
    assert math.isclose(
        result.loss_excluding_premium.item(), expected_payoff - expected_gain, abs_tol=1e-5
    )


def test_no_terminal_liquidation_is_charged():
    config = MarketConfig(maturity_years=1, n_steps=1, transaction_cost_bps=10)
    result = account_hedge(torch.tensor([[100.0, 100.0]]), torch.tensor([[1.0]]), config)
    assert torch.allclose(result.turnover, torch.tensor([1.0]))
    assert torch.allclose(result.transaction_cost, torch.tensor([0.1]))
