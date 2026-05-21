"""
Batch multi-street GTO computation for all canonical flop spots.

Pipeline per spot:
  1. GPU batch solve 58,800 river subgames (N=1000, ~13 min/spot at 50 iters)
  2. Aggregate river EVs → flop terminal values
  3. CPU solve flop with external EVs

Usage:
  uv run python -m gto.library.batch_multistreet \\
      --positions BTN,CO,SB --stacks 100 --iters-river 50 --iters-flop 300

Results stored in: _data/gto/solutions_ms/ (separate Parquet from single-street library)
"""

from __future__ import annotations

import argparse
import signal
import time
from pathlib import Path

import numpy as np
import pandas as pd

from gto.library.flop_canon import all_canonical_flops, board_texture
from gto.library.schema import spot_id
from gto.solver.multistreet_gpu import (
    solve_spot_multistreet, IDX_TO_STR,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOLUTIONS_MS_DIR = Path(__file__).parents[4] / "_data" / "gto" / "solutions_ms"

POSITIONS = ["BTN", "CO", "SB", "HJ", "UTG"]
OPPONENTS = {"BTN": "BB", "CO": "BB", "SB": "BB", "HJ": "BB", "UTG": "BB"}
FLOP_POT  = {"BTN": 6.5, "CO": 7.0, "SB": 5.0, "HJ": 7.0, "UTG": 7.0}
EFF_STACK = {"100": 97.0, "50": 47.0, "200": 197.0}

# ---------------------------------------------------------------------------
# Card index helpers
# ---------------------------------------------------------------------------

_RANKS = "AKQJT98765432"
_SUITS = "cdhs"

def card_idx(s: str) -> int:
    r = _RANKS.index(s[0])
    u = _SUITS.index(s[1])
    return r * 4 + u

# ---------------------------------------------------------------------------
# Parquet store helpers
# ---------------------------------------------------------------------------

def _write_spot_parquet(tag: str, results: list[dict]) -> None:
    SOLUTIONS_MS_DIR.mkdir(parents=True, exist_ok=True)
    import duckdb

    spots_rows = [{
        "spot_id": r["spot_id"], "position": r["position"], "opponent": r["opponent"],
        "stack_bb": r["stack_bb"], "pot_bb": r["pot_bb"], "board": r["board"],
        "street": r["street"], "iterations": r["iterations"],
        "exploitability": r["exploitability"],
    } for r in results]

    agg_rows = [
        {"spot_id": r["spot_id"], "action": e["action"], "freq": float(e["freq"])}
        for r in results for e in r["strategy"]
    ]

    report_rows = []
    for r in results:
        agg_map = {e["action"]: e["freq"] for e in r["strategy"]}
        report_rows.append({
            "position":    r["position"],
            "opponent":    r["opponent"],
            "stack_bb":    r["stack_bb"],
            "board":       r["board"],
            "texture":     r["texture"],
            "check_freq":  float(agg_map.get("Check", 0.0)),
            "bet_freq":    float(agg_map.get("Bet",   agg_map.get("Bet33", 0.0))),
        })

    con = duckdb.connect(":memory:")

    for path, rows in [
        (SOLUTIONS_MS_DIR / "spots"   / f"{tag}.parquet", spots_rows),
        (SOLUTIONS_MS_DIR / "agg"     / f"{tag}.parquet", agg_rows),
        (SOLUTIONS_MS_DIR / "reports" / f"{tag}.parquet", report_rows),
    ]:
        path.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        con.register("_df", df)
        con.execute(f"COPY (SELECT * FROM _df) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.unregister("_df")


def _done_spot_ids() -> set[str]:
    spots_dir = SOLUTIONS_MS_DIR / "spots"
    if not spots_dir.exists() or not list(spots_dir.glob("*.parquet")):
        return set()
    import duckdb
    con = duckdb.connect(":memory:")
    glob = str(spots_dir / "*.parquet")
    return {r[0] for r in con.execute(f"SELECT spot_id FROM read_parquet('{glob}')").fetchall()}


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------

def run_batch(
    positions:    list[str],
    stacks:       list[float],
    n_flops:      int | None,
    iters_river:  int,
    iters_flop:   int,
    batch_size:   int,
    resume:       bool,
) -> None:
    done = _done_spot_ids() if resume else set()

    all_flops = all_canonical_flops()
    if n_flops:
        all_flops = all_flops[:n_flops]

    tasks: list[tuple] = []
    for pos in positions:
        opp   = OPPONENTS[pos]
        for stack in stacks:
            for flop in all_flops:
                board_str = "".join(flop)
                sid       = spot_id(pos, opp, stack, board_str, "flop")
                if sid not in done:
                    tasks.append((pos, opp, stack, flop, sid))

    total = len(tasks)
    print(f"Spots to compute: {total}  (iters_river={iters_river}, iters_flop={iters_flop})", flush=True)
    if total == 0:
        print("Nothing to do.")
        return

    _stop = False

    def _shutdown(sig, frame):
        nonlocal _stop
        print("\nInterrupted.", flush=True)
        _stop = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    done_count = 0
    t_start = time.time()

    for pos, opp, stack, flop, sid in tasks:
        if _stop:
            break

        board_str  = "".join(flop)
        board_ints = [card_idx(c) for c in flop]
        pot_bb     = FLOP_POT.get(pos, 6.5)
        eff_bb     = EFF_STACK.get(str(int(stack)), 97.0)

        t0 = time.time()
        try:
            result = solve_spot_multistreet(
                pot_bb=pot_bb, eff_bb=eff_bb,
                flop_board=board_ints,
                iters_river=iters_river,
                iters_flop=iters_flop,
                batch_size=batch_size,
                verbose=False,
            )
        except Exception as e:
            print(f"  ERROR {sid}: {e}", flush=True)
            import traceback; traceback.print_exc()
            continue

        elapsed = time.time() - t0
        texture = board_texture(flop)

        record = {
            "spot_id":        sid,
            "position":       pos,
            "opponent":       opp,
            "stack_bb":       float(stack),
            "pot_bb":         pot_bb,
            "board":          board_str,
            "street":         "flop",
            "iterations":     iters_flop,
            "exploitability": result.get("exploitability", 0.0),
            "strategy":       result["strategy"],
            "texture":        texture,
        }
        tag = f"{int(t0)}_{pos}_{int(stack)}"
        _write_spot_parquet(tag, [record])

        done_count += 1
        elapsed_total = time.time() - t_start
        rate = done_count / elapsed_total
        eta  = (total - done_count) / rate if rate > 0 else 0
        print(
            f"  [{done_count:4d}/{total}] {pos} {board_str:8s} "
            f"{elapsed:.1f}s  rate={rate:.3f}/s  ETA={eta/3600:.1f}h",
            flush=True,
        )

    elapsed = time.time() - t_start
    print(f"\nDone. {done_count}/{total} spots in {elapsed/3600:.1f}h", flush=True)
    print(f"Solutions: {SOLUTIONS_MS_DIR}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Multi-street GTO batch (River-aware)")
    p.add_argument("--positions",    default="BTN,CO,SB")
    p.add_argument("--stacks",       default="100")
    p.add_argument("--spots",        type=int, default=None)
    p.add_argument("--iters-river",  type=int, default=50)
    p.add_argument("--iters-flop",   type=int, default=300)
    p.add_argument("--batch-size",   type=int, default=1000)
    p.add_argument("--no-resume",    action="store_true")
    args = p.parse_args()

    run_batch(
        positions   = args.positions.split(","),
        stacks      = [float(s) for s in args.stacks.split(",")],
        n_flops     = args.spots,
        iters_river = args.iters_river,
        iters_flop  = args.iters_flop,
        batch_size  = args.batch_size,
        resume      = not args.no_resume,
    )
