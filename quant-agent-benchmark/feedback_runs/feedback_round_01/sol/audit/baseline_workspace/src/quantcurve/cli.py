"""Command-line entry point for the deterministic research workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import CurveConfig
from .workflow import run_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantcurve")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--valuation-date", required=True)
    run.add_argument("--report-path", type=Path, default=None, help="optional report destination")
    run.add_argument("--config", type=Path, default=None, help="optional JSON model configuration")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        try:
            config = CurveConfig()
            if args.config is not None:
                config = CurveConfig.from_mapping(json.loads(args.config.read_text(encoding="utf-8")))
            summary = run_workflow(
                market_data=args.market_data,
                output_dir=args.output_dir,
                valuation_date=args.valuation_date,
                report_path=args.report_path,
                config=config,
            )
        except Exception as exc:
            print(f"quantcurve run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
