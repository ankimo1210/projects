"""Passive fill-model tests (spec §21.6)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.fills import match_passive, passive_fill_probability
from optimal_execution.order_book import AgentLimitOrder, OrderBook
from optimal_execution.random import scenario_rng


def make_book(cfg, seed=7):
    rng = scenario_rng(seed, "lob")
    return OrderBook(cfg, rng, cfg.n_decision_steps * cfg.lob.sub_steps_per_decision)


def test_fill_probability_in_unit_interval():
    for qa in (0, 500, 5000):
        for rate in (0.01, 0.1, 1.0):
            p = passive_fill_probability(qa, 1000, rate, 250, 60)
            assert 0.0 <= p <= 1.0


def test_more_queue_ahead_lowers_fill_probability():
    p_front = passive_fill_probability(0, 1000, 0.1, 250, 60)
    p_back = passive_fill_probability(5000, 1000, 0.1, 250, 60)
    assert p_front > p_back


def test_stronger_opposite_flow_raises_fill_probability():
    p_slow = passive_fill_probability(1000, 1000, 0.05, 250, 60)
    p_fast = passive_fill_probability(1000, 1000, 0.5, 250, 60)
    assert p_fast > p_slow


def test_fifo_queue_mechanics(cfg):
    book = make_book(cfg)
    order = AgentLimitOrder(price=book.best_ask, qty=1000.0, queue_ahead=500.0)
    # flow smaller than queue ahead: no fill, queue shrinks
    fill, crossed = match_passive(book, order, 300.0)
    assert fill == 0.0 and not crossed
    assert order.queue_ahead == pytest.approx(500.0 * 0.98 - 300.0)
    # flow eats the rest of the queue and part of our order; the queue erodes
    # by the cancellation factor once more inside the call
    q_before = order.queue_ahead
    flow = q_before + 400.0
    fill, _ = match_passive(book, order, flow)
    expected = flow - q_before * 0.98
    assert fill == pytest.approx(expected)
    assert order.filled == pytest.approx(expected)


def test_no_double_filling(cfg):
    book = make_book(cfg)
    order = AgentLimitOrder(price=book.best_ask, qty=1000.0, queue_ahead=0.0)
    total = 0.0
    for _ in range(10):
        fill, _ = match_passive(book, order, 400.0)
        total += fill
    assert total == pytest.approx(1000.0)
    assert order.filled <= order.qty + 1e-9


def test_crossed_fill_is_adverse_selection(cfg):
    """If the market trades through the limit price the order fills fully —
    exactly when holding it would have been profitable (price moved against)."""
    book = make_book(cfg)
    order = AgentLimitOrder(price=book.best_ask, qty=1000.0, queue_ahead=2000.0)
    # push the market up through our sell order's price
    book.s0 += 2 * book.spread
    fill, crossed = match_passive(book, order, 0.0)
    assert crossed and fill == pytest.approx(1000.0)
    # the fill price is now below the prevailing mid: adverse for the seller
    assert order.price < book.mid


def test_away_from_market_no_fill(cfg):
    book = make_book(cfg)
    order = AgentLimitOrder(price=book.best_ask + 10 * cfg.tick_size, qty=1000.0, queue_ahead=0.0)
    fill, crossed = match_passive(book, order, 10000.0)
    assert fill == 0.0 and not crossed


def test_statistical_adverse_selection(cfg):
    """With the latent alpha driving both order flow and drift, sub-steps in
    which a resting sell order fills see a more positive mid move than
    sub-steps without fills. Amplified alpha parameters give the test power;
    the default profile uses the same mechanism at lower signal-to-noise."""
    strong = cfg.with_overrides(
        {
            "lob": {
                "adverse_alpha_to_drift": 3.0,
                "adverse_alpha_to_flow": 2.0,
                "adverse_alpha_sigma_bps": 3.0,
            }
        }
    )
    fill_moves, nofill_moves = [], []
    for seed in range(400):
        book = make_book(strong, seed=seed)
        order = AgentLimitOrder(price=book.best_ask, qty=200.0, queue_ahead=0.0)
        for _ in range(30):
            if order.qty - order.filled <= 0:
                break
            mid_before = book.mid
            flow = book.evolve_substep(order)
            move = book.mid - mid_before
            if flow.agent_limit_fill > 0:
                fill_moves.append(move)
            else:
                nofill_moves.append(move)
            # keep re-arming the order at the current touch
            order.price = book.best_ask
            order.queue_ahead = 0.0
    assert len(fill_moves) > 50 and len(nofill_moves) > 50
    assert np.mean(fill_moves) > np.mean(nofill_moves)
