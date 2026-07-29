"""Build or verify P0 implementation-to-paper evidence mappings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.implementation_gold import (
    DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT,
    DEFAULT_IMPLEMENTATION_METRICS_OUTPUT,
    build_implementation_evidence,
    render_json,
    validate_implementation_evidence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--corpus-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.write:
        if args.corpus_root is None:
            raise SystemExit("--write requires --corpus-root")
        evidence, metrics = build_implementation_evidence(args.corpus_root)
        validate_implementation_evidence(evidence, metrics)
        expected_evidence = render_json(evidence)
        expected_metrics = render_json(metrics)
        DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT.write_text(expected_evidence, encoding="utf-8")
        DEFAULT_IMPLEMENTATION_METRICS_OUTPUT.write_text(expected_metrics, encoding="utf-8")
        print(DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT)
        print(DEFAULT_IMPLEMENTATION_METRICS_OUTPUT)
        return 0
    if not DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT.is_file() or not (
        DEFAULT_IMPLEMENTATION_METRICS_OUTPUT.is_file()
    ):
        print("P0 implementation evidence artifacts are missing")
        return 1
    tracked_evidence = json.loads(
        DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT.read_text(encoding="utf-8")
    )
    tracked_metrics = json.loads(DEFAULT_IMPLEMENTATION_METRICS_OUTPUT.read_text(encoding="utf-8"))
    validate_implementation_evidence(tracked_evidence, tracked_metrics)
    if args.corpus_root is None:
        print("P0 implementation evidence is valid")
        return 0
    evidence, metrics = build_implementation_evidence(args.corpus_root)
    validate_implementation_evidence(evidence, metrics)
    expected_evidence = render_json(evidence)
    expected_metrics = render_json(metrics)
    stale = []
    for path, expected in (
        (DEFAULT_IMPLEMENTATION_EVIDENCE_OUTPUT, expected_evidence),
        (DEFAULT_IMPLEMENTATION_METRICS_OUTPUT, expected_metrics),
    ):
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    if stale:
        for path in stale:
            print(f"P0 implementation evidence is missing or stale: {path}")
        return 1
    print("P0 implementation evidence is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
