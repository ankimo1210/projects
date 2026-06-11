"""Regression tests for the 2026-06-10 core-logic review fixes (Python side).

B14 is covered in test_batch_position_cache.py. The B10 multistreet_gpu tests
were removed with the approximation-multistreet tier (M1a decommission,
docs/superpowers/specs/2026-06-11-mode-matrix-roadmap-design.md section 2).

Covers:
  I12 — range_builder dead no-op loop removed (behavior unchanged).
"""

from __future__ import annotations

from gto.library import range_builder


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
