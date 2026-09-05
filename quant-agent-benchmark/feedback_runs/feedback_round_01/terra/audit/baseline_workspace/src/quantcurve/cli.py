"""Command line entrypoint for a reproducible zero-curve workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

from .curve import run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantcurve")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--valuation-date", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        try:
            summary = run_workflow(args.market_data, args.output_dir, args.valuation_date)
        except (FileNotFoundError, ValueError, RuntimeError) as error:
            parser = build_parser()
            parser.error(str(error))
        print(
            f"completed: {summary['selected_model']} model; "
            f"{summary['usable_observations']}/{summary['raw_observations']} usable observations; "
            f"{summary['curve_rows']} curve rows"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
