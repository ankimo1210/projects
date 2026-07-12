"""Reactive order-book tests (spec §21.5)."""

from __future__ import annotations

import numpy as np
import pytest

from optimal_execution.order_book import OrderBook, inverse_poisson
from optimal_execution.random import scenario_rng


def make_book(cfg, seed=7, reactive=True):
    rng = scenario_rng(seed, "lob")
    n_sub = cfg.n_decision_steps * cfg.lob.sub_steps_per_decision
    return OrderBook(cfg, rng, n_sub, reactive=reactive)


def test_bid_below_ask_and_positive_depths(cfg):
    book = make_book(cfg)
    for _ in range(200):
        book.evolve_substep(None)
        assert book.best_bid < book.best_ask
        assert book.bid_depth > 0 and book.ask_depth > 0
        assert -1.0 <= book.imbalance <= 1.0
        assert np.isfinite(book.mid) and np.isfinite(book.spread)


def test_market_order_consumes_depth_and_widens_spread(cfg):
    book = make_book(cfg)
    d0 = book.bid_depth
    s0 = book.spread
    q = 0.8 * d0
    _, cash, detail = book.market_order(q)
    assert book.bid_depth == pytest.approx(d0 - q)
    assert book.spread >= s0  # depletion widens (or keeps) the spread
    assert detail["spread"] > 0
    assert cash < q * (book.mid + 1.0)  # sanity: sold below mid-ish levels


def test_oversized_order_walks_the_book(cfg):
    book = make_book(cfg)
    depth = book.bid_depth
    touch = book.best_bid
    q_small = 0.5 * depth
    _, cash_small, _ = book.market_order(q_small)
    p_small = cash_small / q_small

    book2 = make_book(cfg)  # identical fresh book
    q_big = 5.0 * depth
    _, cash_big, detail_big = book2.market_order(q_big)
    p_big = cash_big / q_big
    assert p_small == pytest.approx(touch)  # inside L1: executes at touch
    assert p_big < touch  # walked deeper levels
    assert detail_big["walk"] > 0


def test_agent_action_changes_future_state_reactive_only(cfg):
    """The reactive book diverges after an agent trade; the replay book does not."""
    q = 5000.0

    def run(reactive: bool, trade: bool):
        book = make_book(cfg, seed=11, reactive=reactive)
        for _ in range(5):
            book.evolve_substep(None)
        if trade:
            book.market_order(q)
        out = []
        for _ in range(20):
            book.evolve_substep(None)
            out.append((book.mid, book.spread, book.bid_depth))
        return np.array(out)

    react_no = run(True, False)
    react_yes = run(True, True)
    replay_no = run(False, False)
    replay_yes = run(False, True)
    assert not np.allclose(react_no, react_yes)  # trade leaves a trace
    np.testing.assert_allclose(replay_no, replay_yes)  # replay ignores the agent


def test_transient_state_decays_after_trade(cfg):
    book = make_book(cfg)
    book.market_order(5000.0)
    d1 = book.D
    assert d1 > 0
    for _ in range(30):
        book.evolve_substep(None)
    assert book.D < d1 * 0.5


def test_permanent_impact_shifts_mid(cfg):
    book = make_book(cfg, seed=13)
    mid0 = book.mid
    s0_before = book.s0
    book.market_order(10000.0)
    # unaffected price untouched by the agent's trade itself
    assert book.s0 == s0_before
    # impacted mid moved against the seller
    assert book.mid < mid0


def test_intensities_finite_under_extreme_state(cfg):
    book = make_book(cfg)
    book.recent_return = 10.0  # absurd 10-currency EMA move
    book.eps_alpha = 5.0
    lam = book._intensity(cfg.mo_rate_per_side, 1e9)
    assert lam <= cfg.lob.intensity_cap_mult * cfg.mo_rate_per_side
    for _ in range(50):
        flow = book.evolve_substep(None)
        assert np.isfinite(flow.buy_mo_volume + flow.sell_mo_volume)


def test_inverse_poisson_matches_numpy_moments():
    rng = np.random.default_rng(0)
    lam = 0.8
    draws = np.array([inverse_poisson(u, lam) for u in rng.random(20000)])
    assert draws.mean() == pytest.approx(lam, rel=0.05)
    assert draws.var() == pytest.approx(lam, rel=0.1)


def test_buy_side_symmetry(cfg):
    buy_cfg = cfg.with_overrides({"side": "buy"})
    book = make_book(buy_cfg)
    d0 = book.ask_depth
    touch = book.best_ask
    _, cash, _ = book.market_order(1000.0)
    assert book.ask_depth == pytest.approx(d0 - 1000.0)  # buys consume the ask
    assert cash / 1000.0 == pytest.approx(touch)
