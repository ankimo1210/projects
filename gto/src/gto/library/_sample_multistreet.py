"""Sample multi-street solve for 3 diverse BTN vs BB flops (verification)."""
from __future__ import annotations
import time
from pathlib import Path

import pandas as pd
import duckdb

from gto.library.flop_canon import board_texture
from gto.library.schema import spot_id
from gto.solver.multistreet_gpu import solve_spot_multistreet

SOLUTIONS_MS_DIR = Path(__file__).parents[4] / "_data" / "gto" / "solutions_ms"
_RANKS = "AKQJT98765432"
_SUITS = "cdhs"


def card_idx(s: str) -> int:
    return _RANKS.index(s[0]) * 4 + _SUITS.index(s[1])


def parse_board(b: str) -> list[str]:
    return [b[i:i+2] for i in range(0, 6, 2)]


SAMPLES = [
    ("AcAdKc", "paired_two_tone"),
    ("AcKdQh", "connected_rainbow"),
    ("AcJc8d", "disconnected_two_tone"),
]
POS, OPP = "BTN", "BB"
STACK, POT, EFF = 100.0, 6.5, 97.0
ITERS_RIVER, ITERS_FLOP, BATCH = 50, 300, 1000


def write_parquet(tag: str, record: dict) -> None:
    SOLUTIONS_MS_DIR.mkdir(parents=True, exist_ok=True)
    agg_map = {e["action"]: e["freq"] for e in record["strategy"]}
    report = {
        "position": record["position"], "opponent": record["opponent"],
        "stack_bb": record["stack_bb"], "board": record["board"],
        "texture": record["texture"],
        "check_freq": float(agg_map.get("Check", 0.0)),
        "bet_freq": float(agg_map.get("Bet", agg_map.get("Bet33", 0.0))),
    }
    spot = {k: record[k] for k in ("spot_id", "position", "opponent",
            "stack_bb", "pot_bb", "board", "street", "iterations", "exploitability")}
    agg_rows = [{"spot_id": record["spot_id"], "action": e["action"], "freq": float(e["freq"])}
                for e in record["strategy"]]

    con = duckdb.connect(":memory:")
    for sub, rows in [("spots", [spot]), ("agg", agg_rows), ("reports", [report])]:
        out = SOLUTIONS_MS_DIR / sub / f"{tag}.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(rows)
        con.register("_df", df)
        con.execute(f"COPY (SELECT * FROM _df) TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.unregister("_df")


def main() -> None:
    print(f"Sample multistreet solve: {len(SAMPLES)} spots (BTN vs BB 100bb)", flush=True)
    t_start = time.time()

    for i, (board, expected_texture) in enumerate(SAMPLES, 1):
        cards = parse_board(board)
        board_ints = [card_idx(c) for c in cards]
        sid = spot_id(POS, OPP, STACK, board, "flop")

        print(f"\n[{i}/{len(SAMPLES)}] {board}  ({expected_texture})", flush=True)
        t0 = time.time()
        result = solve_spot_multistreet(
            pot_bb=POT, eff_bb=EFF, flop_board=board_ints,
            iters_river=ITERS_RIVER, iters_flop=ITERS_FLOP,
            batch_size=BATCH, verbose=True,
        )
        elapsed = time.time() - t0
        print(f"  elapsed: {elapsed/60:.1f} min", flush=True)
        print(f"  exploitability: {result.get('exploitability', 0.0):.6f}", flush=True)
        for e in result["strategy"]:
            print(f"    {e['action']:8s} {e['freq']*100:.2f}%", flush=True)

        record = {
            "spot_id": sid, "position": POS, "opponent": OPP,
            "stack_bb": STACK, "pot_bb": POT, "board": board, "street": "flop",
            "iterations": ITERS_FLOP, "exploitability": result.get("exploitability", 0.0),
            "strategy": result["strategy"],
            "texture": board_texture(tuple(cards)),
        }
        write_parquet(f"sample_{int(t0)}_{POS}_{board}", record)

    print(f"\nTotal: {(time.time()-t_start)/60:.1f} min", flush=True)
    print(f"Output: {SOLUTIONS_MS_DIR}", flush=True)


if __name__ == "__main__":
    main()
