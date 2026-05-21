"""Solution library schema helpers."""

from pathlib import Path

import duckdb

# Legacy DuckDB path — kept for --migrate support only
DB_PATH = Path(__file__).parents[4] / "_data" / "gto" / "solutions.duckdb"


def get_db(**_kwargs) -> duckdb.DuckDBPyConnection:
    """Return in-memory DuckDB with views over the Parquet solution store."""
    from gto.library.store import reader

    return reader()


def spot_id(position: str, opponent: str, stack_bb: float, board: str, street: str) -> str:
    return f"{position}_vs_{opponent}_{int(stack_bb)}bb_{board}_{street}"
