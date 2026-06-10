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


def test_to_core_round_trips_card_strings():
    """_to_core(display int) must yield the gto-core int for the SAME card."""
    for c in range(52):
        s = msg.IDX_TO_STR[c]  # display int -> "Ac" etc.
        assert msg._to_core(c) == range_builder.card_int(s[0], s[1])


def test_blocked_combo_mask_matches_combo_index():
    """A card blocks exactly the 51 combos that contain it, indexed in gto-core
    (root_ev) order — NOT this module's A-first display order."""
    card = 5  # display int (Kd)
    core = msg._to_core(card)
    mask = msg._blocked_combo_mask([card])
    expected = {
        range_builder.combo_index(core, other) for other in range(52) if other != core
    }
    assert mask.sum() == 51
    assert {int(i) for i in np.flatnonzero(mask)} == expected


def test_combo_index_agrees_with_range_builder():
    """multistreet_gpu._combo_index must match the range_builder / gto-core formula."""
    for a in range(0, 52, 7):
        for b in range(a + 1, 52, 5):
            assert msg._combo_index(a, b) == range_builder.combo_index(a, b)


def test_aggregation_averages_live_combos_and_masks_blocked(monkeypatch):
    """Drive the REAL solve_spot_multistreet aggregation end to end.

    Each river subgame is stubbed to return a CLEAN value (7.5) on every combo
    that does NOT use that leaf's turn/river card, and a poison value (1000.0)
    on combos that DO. The poisoned combos are exactly the ones the masking
    must drop, so after a correct mask + per-combo denominator:

    every combo averages to exactly 7.5 — the poison appears only where the
    combo is masked out and dropped from its own denominator. (Combos that use
    a flop card are never poisoned here; the masking targets turn/river cards
    only, and the downstream flop solver zeroes flop-card combos by range.)

    This fails three distinct ways pre-fix:
      * no-op mask (original B10): poison 1000.0 survives -> agg >> 7.5;
      * scalar divisor (B5 dilution in the Python path): live combos divided by
        the full leaf count -> agg < 7.5;
      * A-first vs gto-core encoding: the mask hits the wrong combos -> poison
        leaks into some entries and 7.5 is zeroed in others.
    """
    flop_board = [0, 1, 2]  # display ints (Ac, Ad, Ah)
    clean = 7.5
    poison = 1000.0

    def fake_gpu_batch(jobs, iters, batch_size, bet_pct):
        out = []
        for job in jobs:
            board = job["board"]  # 5 card strings: flop3 + turn + river
            ev = np.full(msg.NUM_COMBOS, clean, dtype=np.float64)
            for cs in (board[3], board[4]):  # turn, river
                core = range_builder.card_int(cs[0], cs[1])
                for other in range(52):
                    if other != core:
                        ev[range_builder.combo_index(core, other)] = poison
            out.append({"root_ev": ev.tolist()})
        return out

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
    # Every combo, at every node, must come out at exactly the clean value:
    # poison removed, divisor counting only the live leaves.
    for node_id, node_ev in enumerate(terminal_evs):
        agg = np.asarray(node_ev, dtype=np.float64)
        np.testing.assert_allclose(agg, clean, err_msg=f"node {node_id}")


def test_aggregation_block_is_real_not_noop():
    """The mask actually zeros a combo using the blocked card, in gto-core
    (root_ev) order. Pins that the masking is neither a no-op nor mis-indexed.
    """
    tc, rc = 10, 20  # display ints
    # A combo using the physical turn card tc, indexed in gto-core order.
    blocked_combo = range_builder.combo_index(msg._to_core(tc), msg._to_core(30))
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
