"""Parquet-backed solution store.

Layout:
    data/solutions/
        spots/    -- one .parquet per batch
        agg/      -- aggregate_strategies
        combos/   -- combo_strategies (largest)
        reports/  -- flop_reports
        cache/    -- pre-computed JSON caches for frontend direct fetch

DuckDB is used as a query engine only (no DuckDB file storage).
"""

from __future__ import annotations
import json
from pathlib import Path

import duckdb
import pandas as pd

SOLUTIONS_DIR = Path(__file__).parents[4] / "data" / "solutions"

CACHE_DIR = SOLUTIONS_DIR / "cache"

_DIRS = {
    "spots":                SOLUTIONS_DIR / "spots",
    "aggregate_strategies": SOLUTIONS_DIR / "agg",
    "combo_strategies":     SOLUTIONS_DIR / "combos",
    "flop_reports":         SOLUTIONS_DIR / "reports",
}

# Empty-table DDL used when no Parquet files exist yet
_EMPTY_SCHEMAS = {
    "spots": """(
        spot_id VARCHAR, position VARCHAR, opponent VARCHAR,
        stack_bb DOUBLE, pot_bb DOUBLE, board VARCHAR,
        street VARCHAR, iterations INTEGER, exploitability DOUBLE
    )""",
    "aggregate_strategies": "(spot_id VARCHAR, action VARCHAR, freq FLOAT)",
    "combo_strategies":     "(spot_id VARCHAR, card_a TINYINT, card_b TINYINT, action VARCHAR, freq FLOAT)",
    "flop_reports": """(
        position VARCHAR, opponent VARCHAR, stack_bb DOUBLE,
        board VARCHAR, texture VARCHAR,
        check_freq FLOAT, bet33_freq FLOAT, bet75_freq FLOAT, bet100_freq FLOAT
    )""",
}


def reader() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with views over existing Parquet files (read-only)."""
    con = duckdb.connect(":memory:")
    for table, dir_path in _DIRS.items():
        files = list(dir_path.glob("*.parquet")) if dir_path.exists() else []
        if files:
            glob = str(dir_path / "*.parquet")
            con.execute(f"CREATE VIEW {table} AS SELECT * FROM read_parquet('{glob}')")
        else:
            con.execute(f"CREATE TABLE {table} {_EMPTY_SCHEMAS[table]}")
    return con


def done_spot_ids() -> set[str]:
    """Return set of already-computed spot_ids from the Parquet store."""
    spots_dir = _DIRS["spots"]
    if not spots_dir.exists() or not list(spots_dir.glob("*.parquet")):
        return set()
    con = duckdb.connect(":memory:")
    glob = str(spots_dir / "*.parquet")
    return {row[0] for row in con.execute(f"SELECT spot_id FROM read_parquet('{glob}')").fetchall()}


def write_batch(
    tag: str,
    spots_df: pd.DataFrame,
    agg_df: pd.DataFrame,
    combos_df: pd.DataFrame,
    reports_df: pd.DataFrame,
) -> None:
    """Write one batch of results as four Parquet files (append-only, never overwrites)."""
    for dir_path in _DIRS.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    fname = f"{tag}.parquet"
    con = duckdb.connect(":memory:")

    for table, df in [
        ("spots",                spots_df),
        ("aggregate_strategies", agg_df),
        ("combo_strategies",     combos_df),
        ("flop_reports",         reports_df),
    ]:
        path = _DIRS[table] / fname
        con.register("_df", df)
        con.execute(f"COPY (SELECT * FROM _df) TO '{path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.unregister("_df")


def build_position_cache(position: str | None = None, stack_bb: float = 100.0) -> None:
    """Pre-compute aggregate JSON cache for frontend direct fetch.

    Output: data/solutions/cache/{POS}_{stack}.json
    Schema: { position, stack_bb, spots: { board: { texture, exploitability, strategy: {action: freq} } } }
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = reader()

    positions_query = (
        f"SELECT DISTINCT position FROM spots WHERE stack_bb = {stack_bb} ORDER BY position"
    )
    all_positions = [row[0] for row in con.execute(positions_query).fetchall()]
    targets = [position] if position else all_positions
    if not targets:
        print("  No spots found in store yet.")
        return

    for pos in targets:
        rows = con.execute("""
            SELECT s.board, r.texture, s.exploitability, a.action, a.freq
            FROM spots s
            LEFT JOIN flop_reports r
              ON r.board = s.board AND r.position = s.position AND r.stack_bb = s.stack_bb
            JOIN aggregate_strategies a ON a.spot_id = s.spot_id
            WHERE s.position = ? AND s.stack_bb = ?
            ORDER BY s.board, a.action
        """, [pos, stack_bb]).fetchall()

        spots: dict = {}
        for board, texture, expl, action, freq in rows:
            if board not in spots:
                spots[board] = {
                    "texture": texture or "",
                    "exploitability": expl,
                    "strategy": {},
                }
            spots[board]["strategy"][action] = round(float(freq), 6)

        cache = {"position": pos, "stack_bb": stack_bb, "spots": spots}
        out = CACHE_DIR / f"{pos}_{int(stack_bb)}.json"
        out.write_text(json.dumps(cache, separators=(",", ":")))
        print(f"  cache: {out.name}  ({len(spots)} spots)")
