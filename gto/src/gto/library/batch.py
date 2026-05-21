"""
Batch precomputation of GTO flop solutions (Rust GPU accelerated).

Usage:
  uv run python -m gto.library.batch [--spots N] [--iters N] [--batch-size N]
  uv run python -m gto.library.batch --positions BTN,CO --stacks 100 --iters 500
  uv run python -m gto.library.batch --migrate   # one-time: DuckDB → Parquet
"""

from __future__ import annotations

import argparse
import signal
import time

import gto_cuda
import numpy as np
import pandas as pd

from gto.library import store
from gto.library.flop_canon import all_canonical_flops, board_texture
from gto.library.schema import spot_id

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

POSITIONS = ["BTN", "CO", "SB", "HJ", "UTG"]
OPPONENTS = {"BTN": "BB", "CO": "BB", "SB": "BB", "HJ": "BB", "UTG": "BB"}

FLOP_POT = {"BTN": 6.5, "CO": 7.0, "SB": 5.0, "HJ": 7.0, "UTG": 7.0}
EFF_STACK = {"100": 97.0, "50": 47.0, "200": 197.0}

# ---------------------------------------------------------------------------
# Build DataFrames from a list of solved results
# ---------------------------------------------------------------------------


def _build_dfs(
    results: list[dict],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    spots_rows = [
        {
            "spot_id": r["spot_id"],
            "position": r["position"],
            "opponent": r["opponent"],
            "stack_bb": r["stack_bb"],
            "pot_bb": r["pot_bb"],
            "board": r["board"],
            "street": r["street"],
            "iterations": r["iterations"],
            "exploitability": r["exploitability"],
        }
        for r in results
    ]

    agg_rows = [
        {"spot_id": r["spot_id"], "action": e["action"], "freq": float(e["freq"])}
        for r in results
        for e in r["strategy"]
    ]

    combo_rows = [
        (r["spot_id"], cs["card_a"], cs["card_b"], cs["action"], float(cs["freq"]))
        for r in results
        for cs in r["combo_strats"]
    ]

    report_rows = []
    for r in results:
        agg = {e["action"]: e["freq"] for e in r["strategy"]}
        report_rows.append(
            {
                "position": r["position"],
                "opponent": r["opponent"],
                "stack_bb": r["stack_bb"],
                "board": r["board"],
                "texture": r["texture"],
                "check_freq": float(agg.get("Check", 0.0)),
                "bet33_freq": float(agg.get("Bet33", agg.get("Bet(0)", 0.0))),
                "bet75_freq": float(agg.get("Bet75", agg.get("Bet(1)", 0.0))),
                "bet100_freq": float(agg.get("Bet100", agg.get("Bet(2)", 0.0))),
            }
        )

    spots_df = pd.DataFrame(spots_rows)

    agg_df = (
        pd.DataFrame(agg_rows) if agg_rows else pd.DataFrame(columns=["spot_id", "action", "freq"])
    )

    if combo_rows:
        spot_ids, card_as, card_bs, actions, freqs = zip(*combo_rows, strict=False)
        combos_df = pd.DataFrame(
            {
                "spot_id": list(spot_ids),
                "card_a": np.array(card_as, dtype=np.int8),
                "card_b": np.array(card_bs, dtype=np.int8),
                "action": list(actions),
                "freq": np.array(freqs, dtype=np.float32),
            }
        )
    else:
        combos_df = pd.DataFrame(columns=["spot_id", "card_a", "card_b", "action", "freq"])

    reports_df = (
        pd.DataFrame(report_rows)
        if report_rows
        else pd.DataFrame(
            columns=[
                "position",
                "opponent",
                "stack_bb",
                "board",
                "texture",
                "check_freq",
                "bet33_freq",
                "bet75_freq",
                "bet100_freq",
            ]
        )
    )

    return spots_df, agg_df, combos_df, reports_df


# ---------------------------------------------------------------------------
# Main batch runner
# ---------------------------------------------------------------------------


def run_batch(
    positions: list[str],
    stacks: list[float],
    n_flops: int | None,
    iters: int,
    max_bets: int,
    resume: bool,
    batch_size: int = 32,
) -> None:

    done = store.done_spot_ids() if resume else set()

    all_flops = all_canonical_flops()
    if n_flops:
        all_flops = all_flops[:n_flops]

    groups: list[tuple[str, str, float, list]] = []
    for pos in positions:
        opp = OPPONENTS[pos]
        for stack in stacks:
            pending = [
                flop
                for flop in all_flops
                if spot_id(pos, opp, stack, "".join(flop), "flop") not in done
            ]
            if pending:
                groups.append((pos, opp, stack, pending))

    total = sum(len(g[3]) for g in groups)
    print(f"Spots to compute: {total}  (Rust GPU N={batch_size}, iters={iters})", flush=True)
    if total == 0:
        print("Nothing to do.")
        return

    _stop = False

    def _shutdown(sig, frame):
        nonlocal _stop
        print("\nInterrupted. Stopping after current batch...", flush=True)
        _stop = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    done_count = 0
    t_start = time.time()

    for pos, opp, stack, flops in groups:
        if _stop:
            break
        pot = FLOP_POT.get(pos, 6.5)
        eff = EFF_STACK.get(str(int(stack)), 97.0)

        for i in range(0, len(flops), batch_size):
            if _stop:
                break
            chunk = flops[i : i + batch_size]
            spots_input = [
                {"board": list(f), "pot_bb": pot, "effective_stack_bb": eff} for f in chunk
            ]

            t0 = time.time()
            try:
                gpu_results = gto_cuda.batch_solve_rust(spots_input, iters, max_bets)
            except Exception as e:
                print(f"  BATCH ERROR ({pos} chunk {i // batch_size}): {e}", flush=True)
                import traceback

                traceback.print_exc()
                continue
            elapsed_batch = time.time() - t0

            batch_results = []
            for flop, result in zip(chunk, gpu_results, strict=False):
                board_str = "".join(flop)
                sid = spot_id(pos, opp, stack, board_str, "flop")
                batch_results.append(
                    {
                        "spot_id": sid,
                        "position": pos,
                        "opponent": opp,
                        "stack_bb": float(stack),
                        "pot_bb": pot,
                        "board": board_str,
                        "street": "flop",
                        "iterations": iters,
                        "exploitability": result["exploitability"],
                        "strategy": result["strategy"],
                        "combo_strats": result["combo_strategies"],
                        "texture": board_texture(flop),
                        "elapsed": elapsed_batch / len(chunk),
                    }
                )

            tag = f"{int(t0)}_{pos}_{int(stack)}"
            store.write_batch(tag, *_build_dfs(batch_results))

            done_count += len(chunk)
            elapsed_total = time.time() - t_start
            rate = done_count / elapsed_total
            eta = (total - done_count) / rate if rate > 0 else 0
            print(
                f"  [{done_count:4d}/{total}] {pos} batch={len(chunk)} "
                f"{elapsed_batch:.1f}s ({elapsed_batch / len(chunk):.2f}s/spot)  "
                f"rate={rate:.2f}/s  ETA={eta / 60:.1f}min",
                flush=True,
            )

    elapsed = time.time() - t_start
    print(f"\nDone. {done_count}/{total} spots in {elapsed / 60:.1f} min", flush=True)
    print(f"Solutions: {store.SOLUTIONS_DIR}")

    if done_count > 0:
        print("Rebuilding aggregate cache...", flush=True)
        store.build_position_cache(stack_bb=stacks[0] if len(stacks) == 1 else 100.0)


# ---------------------------------------------------------------------------
# One-time migration: existing solutions.duckdb → Parquet
# ---------------------------------------------------------------------------


def migrate_duckdb() -> None:
    from gto.library.schema import DB_PATH

    if not DB_PATH.exists():
        print(f"No DuckDB file found at {DB_PATH}. Nothing to migrate.")
        return

    import duckdb

    con = duckdb.connect(str(DB_PATH), read_only=True)

    print(f"Reading {DB_PATH}...")
    spots_df = con.execute(
        "SELECT spot_id, position, opponent, stack_bb, pot_bb, board, street, iterations, exploitability FROM spots"
    ).df()
    agg_df = con.execute("SELECT spot_id, action, freq FROM aggregate_strategies").df()
    combos_df = con.execute(
        "SELECT spot_id, card_a, card_b, action, freq FROM combo_strategies"
    ).df()
    reports_df = con.execute(
        "SELECT position, opponent, stack_bb, board, texture, check_freq, bet33_freq, bet75_freq, bet100_freq FROM flop_reports"
    ).df()
    con.close()

    n = len(spots_df)
    print(f"Migrating {n} spots → Parquet...")
    store.write_batch("migrated", spots_df, agg_df, combos_df, reports_df)
    print(f"Done. {store.SOLUTIONS_DIR}")
    print("You can now delete solutions.duckdb and solutions_staging.duckdb.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="GTO flop batch computation (Rust GPU)")
    p.add_argument("--migrate", action="store_true", help="One-time: DuckDB → Parquet migration")
    p.add_argument(
        "--rebuild-cache", action="store_true", help="Rebuild aggregate JSON cache for frontend"
    )
    p.add_argument("--positions", default="BTN,CO,SB")
    p.add_argument("--stacks", default="100")
    p.add_argument("--spots", type=int, default=None, help="Limit flop count")
    p.add_argument("--iters", type=int, default=300)
    p.add_argument("--max-bets", type=int, default=2)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Spots per GPU batch (default: 32, optimal for RTX 5080)",
    )
    args = p.parse_args()

    if args.migrate:
        migrate_duckdb()
    elif args.rebuild_cache:
        store.build_position_cache()
    else:
        run_batch(
            positions=args.positions.split(","),
            stacks=[float(s) for s in args.stacks.split(",")],
            n_flops=args.spots,
            iters=args.iters,
            max_bets=args.max_bets,
            resume=not args.no_resume,
            batch_size=args.batch_size,
        )
