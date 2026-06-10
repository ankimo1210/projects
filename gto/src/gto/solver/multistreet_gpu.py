"""
GPU-accelerated multi-street GTO solver using Backward Induction.

Current pipeline (Phase 2, approximation):
  1. GPU batch solve all river subgames (5-card boards, correct)
  2. Average river root EVs over (turn_card × river_card) per flop NextStreet node
  3. CPU solve flop subgame with external terminal EVs (gto_py.solve_flop_with_ev)

Phase 3 upgrade:
  - Add proper turn solve between river and flop (currently skipped)
  - Modify gto_cuda to accept external terminal EVs (eliminates showdown approximation)
"""

from __future__ import annotations

import time

import gto_cuda
import gto_py
import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NUM_COMBOS = 1326

RANKS = "AKQJT98765432"
SUITS = "cdhs"
IDX_TO_STR: list[str] = [f"{RANKS[i // 4]}{SUITS[i % 4]}" for i in range(52)]


def _strs(indices: list[int]) -> list[str]:
    return [IDX_TO_STR[c] for c in indices]


def _combo_index(a: int, b: int) -> int:
    """Combo index for cards a, b (0..51). Matches gto-core range::combo_index."""
    lo, hi = (a, b) if a < b else (b, a)
    return lo * (103 - lo) // 2 + hi - lo - 1


def _blocked_combo_mask(cards: list[int]) -> np.ndarray:
    """Boolean[NUM_COMBOS] marking combos that use any of `cards` (0..51)."""
    mask = np.zeros(NUM_COMBOS, dtype=bool)
    for blocked in cards:
        for other in range(52):
            if other == blocked:
                continue
            mask[_combo_index(blocked, other)] = True
    return mask


# ---------------------------------------------------------------------------
# Flop tree NextStreet node parameters (computed from bet sizes)
#
# Tree structure (50% pot, max 1 raise at 2.5×):
#   Node 0: OOP Check / IP Check         → check-check terminal
#   Node 1: OOP Check / IP Bet / OOP Call → pot grows by 2×bet
#   Node 2: OOP Check / IP Bet / OOP Raise / IP Call → pot grows more
#   Node 3: OOP Bet / IP Call             → pot grows by 2×bet
#   Node 4: OOP Bet / IP Raise / OOP Call → pot grows more
# ---------------------------------------------------------------------------


def _flop_ns_params(pot_bb: float, eff_bb: float) -> list[dict]:
    """Return list of {pot_bb, eff_bb} for each flop NextStreet node."""
    p = pot_bb * 100.0
    s = eff_bb * 100.0
    bet = p * 0.50

    def node(pot_chips: float, stack_chips: float) -> dict:
        return {"pot_bb": pot_chips / 100.0, "eff_bb": max(stack_chips, 0.0) / 100.0}

    raise_ = bet * 2.5
    return [
        node(p, s),  # 0: check-check
        node(p + 2 * bet, s - bet),  # 1: check-bet-call
        node(p + raise_ + bet, s - raise_),  # 2: check-bet-raise-call
        node(p + 2 * bet, s - bet),  # 3: bet-call
        node(p + raise_ + bet, s - raise_),  # 4: bet-raise-call
    ]


def _turn_ns_params(pot_bb: float, eff_bb: float) -> list[dict]:
    """Return list of {pot_bb, eff_bb} for each turn NextStreet node (75% pot)."""
    p = pot_bb * 100.0
    s = eff_bb * 100.0
    bet = p * 0.75
    raise_ = bet * 2.5

    def node(pc: float, sc: float) -> dict:
        return {"pot_bb": pc / 100.0, "eff_bb": max(sc, 0.0) / 100.0}

    return [
        node(p, s),
        node(p + 2 * bet, s - bet),
        node(p + raise_ + bet, s - raise_),
        node(p + 2 * bet, s - bet),
        node(p + raise_ + bet, s - raise_),
    ]


# ---------------------------------------------------------------------------
# GPU batch solve helpers
# ---------------------------------------------------------------------------


def _gpu_batch(spots: list[dict], iters: int, batch_size: int, bet_pct: int) -> list[dict]:
    """River-tree GPU batch solve with single bet size matching gto-core tree."""
    results = []
    for i in range(0, len(spots), batch_size):
        chunk = spots[i : i + batch_size]
        # bet_pct=75 for river (matches gto-core Street::River)
        # max_bets=2 → bet + 1 raise per street
        results.extend(gto_cuda.batch_solve_fast(chunk, iters, 2, bet_pct))
    return results


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------


def solve_spot_multistreet(
    pot_bb: float,
    eff_bb: float,
    flop_board: list[int],  # 3 card indices
    iters_river: int = 50,
    iters_flop: int = 300,
    batch_size: int = 32,
    verbose: bool = False,
) -> dict:
    """
    Full river-aware multi-street GTO solve for a flop spot.

    Returns {
        "strategy":       list of {action, freq},
        "exploitability": float,
        "elapsed":        float (seconds),
    }
    """
    t0 = time.time()

    flop_set = set(flop_board)
    valid_turns = [c for c in range(52) if c not in flop_set]
    flop_ns = _flop_ns_params(pot_bb, eff_bb)

    # ------------------------------------------------------------------
    # Step 1: GPU batch solve ALL river subgames
    # ------------------------------------------------------------------
    # For each (flop_ns_id, turn_card, turn_ns_id, river_card) → board5
    river_jobs: list[dict] = []
    river_index: list[tuple] = []  # (fns_id, tc, tns_id, rc)

    for fns_id, fns in enumerate(flop_ns):
        turn_ns = _turn_ns_params(fns["pot_bb"], fns["eff_bb"])
        for tc in valid_turns:
            board4 = [*flop_board, tc]
            board4_set = set(board4)
            valid_rivers = [c for c in range(52) if c not in board4_set]
            for tns_id, tns in enumerate(turn_ns):
                for rc in valid_rivers:
                    river_jobs.append(
                        {
                            "board": _strs([*board4, rc]),
                            "pot_bb": tns["pot_bb"],
                            "effective_stack_bb": tns["eff_bb"],
                        }
                    )
                    river_index.append((fns_id, tc, tns_id, rc))

    n_river = len(river_jobs)
    if verbose:
        print(
            f"  River jobs: {n_river} | batch_size={batch_size} | iters={iters_river}", flush=True
        )

    t1 = time.time()
    # River uses 75% pot bet (matches gto-core Street::River.bet_pct() = 75)
    river_results = _gpu_batch(river_jobs, iters_river, batch_size, bet_pct=75)
    if verbose:
        print(f"  River solved in {time.time() - t1:.1f}s", flush=True)

    # river_ev[(fns_id, tc, tns_id, rc)] = np.array(NUM_COMBOS)
    river_ev = {
        key: np.array(res["root_ev"], dtype=np.float32)
        for key, res in zip(river_index, river_results, strict=False)
    }

    # ------------------------------------------------------------------
    # Step 2: Aggregate river EVs → flop terminal EVs
    # For each flop_ns_id:
    #   average over all (turn_card × turn_ns_id × river_card)
    # ------------------------------------------------------------------
    flop_terminal_evs: list[list[float]] = []  # 5 × NUM_COMBOS

    for fns_id, fns in enumerate(flop_ns):
        turn_ns = _turn_ns_params(fns["pot_bb"], fns["eff_bb"])
        agg = np.zeros(NUM_COMBOS, dtype=np.float64)
        count = 0

        for tc in valid_turns:
            board4 = [*flop_board, tc]
            board4_set = set(board4)
            valid_rivers = [c for c in range(52) if c not in board4_set]
            for tns_id in range(len(turn_ns)):
                for rc in valid_rivers:
                    ev = river_ev.get((fns_id, tc, tns_id, rc))
                    if ev is not None:
                        # Zero out combos blocked by the turn/river card: a combo
                        # that uses tc or rc is impossible at this leaf and must
                        # not contribute a phantom EV to the aggregate.
                        ev_masked = ev.copy()
                        ev_masked[_blocked_combo_mask([tc, rc])] = 0.0
                        agg += ev_masked
                        count += 1

        if count > 0:
            agg /= count
        flop_terminal_evs.append(agg.tolist())

    # ------------------------------------------------------------------
    # Step 3: CPU flop solve with external terminal EVs
    # ------------------------------------------------------------------
    if verbose:
        print(f"  Flop solve: iters={iters_flop}", flush=True)

    t3 = time.time()
    result = gto_py.solve_flop_with_ev(
        pot_bb,
        eff_bb,
        _strs(flop_board),
        flop_terminal_evs,
        iters_flop,
    )
    if verbose:
        print(f"  Flop done in {time.time() - t3:.1f}s", flush=True)

    return {
        "strategy": result["strategy"],
        "exploitability": result["exploitability"],
        "elapsed": time.time() - t0,
    }
