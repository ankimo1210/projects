"""Write or verify reviewed paper-table metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.table_gold import (
    DEFAULT_TABLE_METRICS_OUTPUT,
    build_table_metrics,
    render_table_metrics,
    validate_table_metrics,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--mineru-root", type=Path)
    return parser.parse_args()


def main() -> int:
    """Write or verify the deterministic table metrics."""

    args = parse_args()
    if args.write:
        if args.mineru_root is None:
            raise SystemExit("--write requires --mineru-root")
        value = build_table_metrics(args.mineru_root)
        validate_table_metrics(value)
        expected = render_table_metrics(value)
        DEFAULT_TABLE_METRICS_OUTPUT.write_text(expected, encoding="utf-8")
        print(DEFAULT_TABLE_METRICS_OUTPUT)
        return 0
    if not DEFAULT_TABLE_METRICS_OUTPUT.is_file():
        print(f"Gold table metrics are missing: {DEFAULT_TABLE_METRICS_OUTPUT}")
        return 1
    tracked = DEFAULT_TABLE_METRICS_OUTPUT.read_text(encoding="utf-8")
    value = json.loads(tracked)
    validate_table_metrics(value)
    if args.mineru_root is not None:
        expected = render_table_metrics(build_table_metrics(args.mineru_root))
        if tracked != expected:
            print(f"Gold table metrics are stale: {DEFAULT_TABLE_METRICS_OUTPUT}")
            return 1
    print("Gold table metrics are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
