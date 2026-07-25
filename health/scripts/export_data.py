"""Export the local DuckDB tables to parquet or csv."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from health.export import export_tables
from health.store import Store


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export local health tables.")
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--format", choices=("parquet", "csv"), default="parquet")
    args = parser.parse_args(argv)

    # Store() creates a fresh, empty database if --db-path does not exist, so a
    # typo'd path would otherwise export four empty files while reporting
    # success -- exactly the failure mode this check exists to catch.
    if not args.db_path.exists():
        raise SystemExit(f"no database at {args.db_path}")

    store = Store(args.db_path)
    try:
        written = export_tables(store, args.out_dir, args.format)
    finally:
        store.close()
    for path in written:
        print(f"wrote: {path}")


if __name__ == "__main__":
    main()
