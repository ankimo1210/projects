"""Required CLI contract. The research workflow is intentionally unfinished."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantcurve")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--valuation-date", required=True)
    run.add_argument("--config", type=Path, help="optional JSON configuration overrides")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        from .config import Config
        from .workflow import run_workflow
        try:
            overrides = json.loads(args.config.read_text()) if args.config else {}
            result = run_workflow(args.market_data, args.output_dir, args.valuation_date, Config(**overrides))
        except (ValueError, OSError, RuntimeError, TypeError) as exc:
            print(f"quantcurve: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
