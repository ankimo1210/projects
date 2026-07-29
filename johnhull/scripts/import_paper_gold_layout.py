"""Import or validate reviewer-audited MinerU layout labels for the gold set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.gold_import import (
    DEFAULT_LAYOUT_LABELS_OUTPUT,
    build_layout_labels,
    render_layout_labels,
    validate_layout_labels,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--mineru-root", type=Path)
    parser.add_argument("--reviewer")
    parser.add_argument("--output", type=Path, default=DEFAULT_LAYOUT_LABELS_OUTPUT)
    args = parser.parse_args()
    if args.write and (args.mineru_root is None or not args.reviewer):
        parser.error("--write requires --mineru-root and --reviewer")
    return args


def main() -> int:
    args = parse_args()
    if args.write:
        labels = build_layout_labels(args.mineru_root, reviewer=args.reviewer)
        validate_layout_labels(labels)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_layout_labels(labels), encoding="utf-8")
        print(args.output)
        return 0
    labels = json.loads(args.output.read_text(encoding="utf-8"))
    validate_layout_labels(labels)
    print("paper-corpus gold layout labels are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
