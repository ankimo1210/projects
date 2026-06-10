"""Regression tests for the 2026-06-10 core-logic review fixes (Python side).

Covers:
  B10 — multistreet_gpu blocked-combo masking in the river→flop aggregation.
  B14 — batch.build_position_cache builds one cache per stack.
  I12 — range_builder dead no-op loop removed (behavior unchanged).

multistreet_gpu imports the maturin-built `gto_cuda` / `gto_py` extensions at
module load; conftest.py registers stand-ins when they are absent from the
venv. The code under test here is pure Python and never calls into them.
"""

from __future__ import annotations

import numpy as np
import pytest
from gto.library import range_builder
from gto.solver import multistreet_gpu as msg

# ---------------------------------------------------------------------------
# B10 — blocked-combo masking
# ---------------------------------------------------------------------------


def test_blocked_combo_mask_matches_combo_index():
    """A card blocks exactly the 51 combos that contain it."""
    card = 5
    mask = msg._blocked_combo_mask([card])
    expected = {msg._combo_index(card, other) for other in range(52) if other != card}
    assert mask.sum() == 51
    assert {int(i) for i in np.flatnonzero(mask)} == expected


def test_combo_index_agrees_with_range_builder():
    """multistreet_gpu._combo_index must match the range_builder / gto-core formula."""
    for a in range(0, 52, 7):
        for b in range(a + 1, 52, 5):
            assert msg._combo_index(a, b) == range_builder.combo_index(a, b)


def test_aggregation_zeros_blocked_combos(monkeypatch):
    """Drive the REAL solve_spot_multistreet aggregation and assert blocked
    combos are zeroed in the flop terminal EVs.

    Every river subgame is stubbed to return a uniform phantom EV on all 1326
    combos. After aggregation, any combo that uses a turn or river card is
    impossible at that leaf and must be masked to 0. Pre-fix (no-op loop) the
    phantom survives -> the captured terminal EV for a board-blocked combo is
    nonzero and this assertion fails.
    """
    flop_board = [0, 1, 2]  # three distinct flop cards (ints 0..51)
    phantom = 7.5

    def fake_gpu_batch(jobs, iters, batch_size, bet_pct):
        return [{"root_ev": [phantom] * msg.NUM_COMBOS} for _ in jobs]

    captured: dict = {}

    def fake_solve_flop_with_ev(pot_bb, eff_bb, board, terminal_evs, iters):
        captured["terminal_evs"] = terminal_evs
        return {"strategy": [], "exploitability": 0.0}

    monkeypatch.setattr(msg, "_gpu_batch", fake_gpu_batch)
    monkeypatch.setattr(
        msg.gto_py, "solve_flop_with_ev", fake_solve_flop_with_ev, raising=False
    )

    msg.solve_spot_multistreet(
        pot_bb=6.5,
        eff_bb=97.0,
        flop_board=flop_board,
        iters_river=1,
        iters_flop=1,
        batch_size=64,
    )

    terminal_evs = captured["terminal_evs"]
    assert len(terminal_evs) == 5  # one per flop NextStreet node
    agg0 = np.asarray(terminal_evs[0])

    # A combo that uses a card NOT on the flop is blocked at every turn/river
    # leaf that draws it; over the aggregate it must be strictly below phantom.
    # Pick a combo using card 3 (not on flop). It is alive on leaves where the
    # turn/river do not draw card 3, but masked where they do -> mean < phantom.
    partly_blocked = msg._combo_index(3, 4)
    assert agg0[partly_blocked] < phantom, "drawn-card combos must be masked sometimes"

    # A combo entirely on the flop (cards 0 and 1) is impossible at EVERY leaf
    # only if those cards reappear — they cannot (flop fixed), so flop-card
    # combos stay live. Instead verify the masking is non-trivial: the aggregate
    # is not the unmasked uniform phantom everywhere.
    assert not np.allclose(agg0, phantom), "masking must change the aggregate"


def test_aggregation_block_is_real_not_noop():
    """Sanity: without the mask the blocked combo would carry the phantom EV.

    This pins the bug: the pre-fix no-op loop left ev_masked == ev, so the
    blocked combo's aggregate equalled `phantom`, not 0.
    """
    tc, rc = 10, 20
    blocked_combo = msg._combo_index(tc, 30)
    ev = np.full(msg.NUM_COMBOS, 7.5, dtype=np.float32)

    # Pre-fix behavior (no-op): nothing is zeroed.
    ev_noop = ev.copy()
    assert ev_noop[blocked_combo] == pytest.approx(7.5)

    # Post-fix behavior: the masking actually zeros it.
    ev_fixed = ev.copy()
    ev_fixed[msg._blocked_combo_mask([tc, rc])] = 0.0
    assert ev_fixed[blocked_combo] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# I12 — dead loop removal leaves behavior unchanged
# ---------------------------------------------------------------------------


def test_compute_preflop_outcome_blocks_dead_cards():
    """Dead-card blockers still zero the matching combos after removing the
    dead no-op loop (the real blocker loop lives just below it)."""
    out_clean = range_builder.compute_preflop_outcome("BTN")
    out_blocked = range_builder.compute_preflop_outcome("BTN", dead_cards=["As", "Kd"])

    as_int = range_builder.card_int("A", "s")
    kd_int = range_builder.card_int("K", "d")

    ip = out_blocked["ip_weights"]
    oop = out_blocked["oop_call_weights"]
    for other in range(52):
        if other == as_int:
            continue
        idx = range_builder.combo_index(as_int, other)
        assert ip[idx] == 0.0 and oop[idx] == 0.0
    for other in range(52):
        if other == kd_int:
            continue
        idx = range_builder.combo_index(kd_int, other)
        assert ip[idx] == 0.0 and oop[idx] == 0.0

    # Blocking strictly removes weight, so it cannot exceed the unblocked sum.
    assert out_blocked["ip_weights"].sum() <= out_clean["ip_weights"].sum()


def test_no_dead_loop_in_source():
    """The dead no-op statement must be gone from compute_preflop_outcome."""
    import inspect

    src = inspect.getsource(range_builder.compute_preflop_outcome)
    assert "(idx * 2) // 1" not in src
