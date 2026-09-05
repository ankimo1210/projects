"""Required CLI contract. The research workflow is intentionally unfinished."""

from __future__ import annotations

import argparse
from pathlib import Path


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
        raise NotImplementedError("implement the end-to-end curve workflow")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
