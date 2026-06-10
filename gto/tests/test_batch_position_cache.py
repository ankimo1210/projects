"""B14 regression: batch.run_batch must build a position cache per stack.

Pre-fix, the cache-rebuild tail of run_batch did

    store.build_position_cache(stack_bb=stacks[0] if len(stacks) == 1 else 100.0)

so any multi-stack run produced a single cache at the hardcoded 100.0 stack and
silently dropped the rest. These tests pin both the call-site contract and the
end-to-end JSON output.

batch.py imports the maturin-built `gto_cuda` at load time; conftest.py
registers a stand-in when it is absent from the venv (the tested code never
calls into it).
"""

from __future__ import annotations

import json

import pandas as pd
import pytest
from gto.library import batch, store


def _redirect_store(tmp_path, monkeypatch):
    """Point the Parquet store + cache dir at tmp_path."""
    sol = tmp_path / "solutions"
    dirs = {
        "spots": sol / "spots",
        "aggregate_strategies": sol / "agg",
        "combo_strategies": sol / "combos",
        "flop_reports": sol / "reports",
    }
    cache = sol / "cache"
    monkeypatch.setattr(store, "SOLUTIONS_DIR", sol)
    monkeypatch.setattr(store, "CACHE_DIR", cache)
    monkeypatch.setattr(store, "_DIRS", dirs)
    return dirs, cache


def _write_spot(stack: float):
    """Build minimal single-spot DataFrames for a given stack."""
    sid = f"BTN-BB-{int(stack)}-AcKdQh-flop"
    spots_df = pd.DataFrame(
        [
            {
                "spot_id": sid,
                "position": "BTN",
                "opponent": "BB",
                "stack_bb": float(stack),
                "pot_bb": 6.5,
                "board": "AcKdQh",
                "street": "flop",
                "iterations": 100,
                "exploitability": 0.01,
            }
        ]
    )
    agg_df = pd.DataFrame([{"spot_id": sid, "action": "Check", "freq": 1.0}])
    combos_df = pd.DataFrame(
        columns=["spot_id", "card_a", "card_b", "action", "freq"]
    )
    reports_df = pd.DataFrame(
        [
            {
                "position": "BTN",
                "opponent": "BB",
                "stack_bb": float(stack),
                "board": "AcKdQh",
                "texture": "dry",
                "check_freq": 1.0,
                "bet33_freq": 0.0,
                "bet75_freq": 0.0,
                "bet100_freq": 0.0,
            }
        ]
    )
    return spots_df, agg_df, combos_df, reports_df


def test_build_position_cache_per_stack_end_to_end(tmp_path, monkeypatch):
    """build_position_cache writes one JSON per stack from real Parquet data."""
    _dirs, cache = _redirect_store(tmp_path, monkeypatch)

    store.write_batch("s100", *_write_spot(100.0))
    store.write_batch("s50", *_write_spot(50.0))

    store.build_position_cache(stack_bb=100.0)
    store.build_position_cache(stack_bb=50.0)

    assert (cache / "BTN_100.json").exists()
    assert (cache / "BTN_50.json").exists()
    c50 = json.loads((cache / "BTN_50.json").read_text())
    assert c50["stack_bb"] == 50.0
    assert "AcKdQh" in c50["spots"]


def test_run_batch_caches_every_stack(tmp_path, monkeypatch):
    """run_batch must call build_position_cache once for each stack.

    Pre-fix this collapsed to a single call at stack 100.0 whenever
    len(stacks) != 1 -> asserting the 50.0 cache request fails pre-fix.
    """
    _redirect_store(tmp_path, monkeypatch)

    calls: list[float] = []

    def fake_cache(stack_bb: float = 100.0, position=None):
        calls.append(stack_bb)

    monkeypatch.setattr(store, "build_position_cache", fake_cache)

    # Stub out the heavy solve loop: no pending flops, but force done_count > 0
    # by writing a real batch so the cache-rebuild branch is taken.
    monkeypatch.setattr(batch.store, "done_spot_ids", lambda: set())
    # One canonical flop is enough; the GPU call is stubbed to a trivial result.
    monkeypatch.setattr(batch, "all_canonical_flops", lambda: [("Ac", "Kd", "Qh")])

    def fake_batch_solve_rust(spots_input, iters, max_bets):
        return [
            {
                "exploitability": 0.0,
                "strategy": [{"action": "Check", "freq": 1.0}],
                "combo_strategies": [],
            }
            for _ in spots_input
        ]

    monkeypatch.setattr(batch.gto_cuda, "batch_solve_rust", fake_batch_solve_rust, raising=False)

    batch.run_batch(
        positions=["BTN"],
        stacks=[100.0, 50.0],
        n_flops=1,
        iters=10,
        max_bets=2,
        resume=False,
        batch_size=32,
    )

    assert sorted(calls) == [50.0, 100.0], f"expected one cache per stack, got {calls}"


def test_run_batch_caches_single_stack(tmp_path, monkeypatch):
    """Single-stack runs still cache that stack (regression guard)."""
    _redirect_store(tmp_path, monkeypatch)

    calls: list[float] = []
    monkeypatch.setattr(
        store, "build_position_cache", lambda stack_bb=100.0, position=None: calls.append(stack_bb)
    )
    monkeypatch.setattr(batch.store, "done_spot_ids", lambda: set())
    monkeypatch.setattr(batch, "all_canonical_flops", lambda: [("Ac", "Kd", "Qh")])
    monkeypatch.setattr(
        batch.gto_cuda,
        "batch_solve_rust",
        lambda spots_input, iters, max_bets: [
            {"exploitability": 0.0, "strategy": [{"action": "Check", "freq": 1.0}], "combo_strategies": []}
            for _ in spots_input
        ],
        raising=False,
    )

    batch.run_batch(
        positions=["BTN"],
        stacks=[50.0],
        n_flops=1,
        iters=10,
        max_bets=2,
        resume=False,
        batch_size=32,
    )

    assert calls == [50.0]
