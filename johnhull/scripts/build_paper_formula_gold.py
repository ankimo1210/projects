"""Write or verify reviewed paper-formula metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.formula_gold import (
    DEFAULT_FORMULA_METRICS_OUTPUT,
    build_formula_metrics,
    render_formula_metrics,
    validate_formula_metrics,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--gold-output-root", type=Path)
    return parser.parse_args()


def main() -> int:
    """Write or validate formula metrics, optionally recomputing them."""

    args = parse_args()
    if args.write:
        if args.gold_output_root is None:
            raise SystemExit("--write requires --gold-output-root")
        value = build_formula_metrics(args.gold_output_root)
        validate_formula_metrics(value)
        DEFAULT_FORMULA_METRICS_OUTPUT.write_text(render_formula_metrics(value), encoding="utf-8")
        print(DEFAULT_FORMULA_METRICS_OUTPUT)
        return 0
    if not DEFAULT_FORMULA_METRICS_OUTPUT.is_file():
        print(f"Gold formula metrics are missing: {DEFAULT_FORMULA_METRICS_OUTPUT}")
        return 1
    tracked = DEFAULT_FORMULA_METRICS_OUTPUT.read_text(encoding="utf-8")
    validate_formula_metrics(json.loads(tracked))
    if args.gold_output_root is not None:
        expected = render_formula_metrics(build_formula_metrics(args.gold_output_root))
        if tracked != expected:
            print(f"Gold formula metrics are stale: {DEFAULT_FORMULA_METRICS_OUTPUT}")
            return 1
    print("Gold formula metrics are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
