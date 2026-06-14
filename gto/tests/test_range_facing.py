"""Preflop range builder: position-specific facing ranges (#2) and dead-card
blocker removal in the aggregate (#3)."""

from __future__ import annotations

import numpy as np
from gto.library.range_builder import build_oop_call_range_weights, compute_preflop_outcome


def test_facing_range_is_position_specific():
    """BB defends a different range vs a tight UTG open than vs a wide BTN open.
    Before the fix UTG/HJ/SB silently fell back to the BTN facing table."""
    btn = build_oop_call_range_weights("BTN")
    utg = build_oop_call_range_weights("UTG")
    sb = build_oop_call_range_weights("SB")
    hj = build_oop_call_range_weights("HJ")
    assert not np.array_equal(btn, utg)
    assert not np.array_equal(btn, sb)
    assert not np.array_equal(btn, hj)


def test_dead_cards_block_fold_hands_in_aggregate():
    """With every deuce dead, no 'x2' hand can be held, so none may appear in
    the aggregated BB hand list. Before the fix the `or fold_freq > 0`
    short-circuit counted blocked fold hands (e.g. 72o) at full weight."""
    out = compute_preflop_outcome("BTN", dead_cards=["2c", "2d", "2h", "2s"])
    present = {h["hand"] for h in out["bb_hands"]}
    blocked_x2 = {h for h in present if "2" in h[:2]}
    assert blocked_x2 == set(), f"blocked hands still counted: {sorted(blocked_x2)}"
