#!/usr/bin/env python3
"""Evaluate a candidate without modifying its files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evaluator"))

from scoring import evaluate_candidate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--metadata", type=Path, help="optional external run metadata JSON")
    parser.add_argument("--json-out", type=Path, help="write full machine-readable result")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8")) if args.metadata else None
    result = evaluate_candidate(args.candidate, metadata)
    def json_default(value):
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"not JSON serializable: {type(value).__name__}")

    payload = json.dumps(result, indent=2, sort_keys=True, default=json_default)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    print("Summary", file=sys.stderr)
    print(f"Total: {result['total_score']:.3f}/100", file=sys.stderr)
    for name, score in result["category_scores"].items():
        print(f"  {name}: {score:.3f}", file=sys.stderr)
    failed = result["failed_test_identifiers"]
    print(f"Hidden checks: {len(result['hidden_tests']['passed'])} passed, {len(failed)} failed", file=sys.stderr)
    if failed:
        print("Failed: " + ", ".join(failed), file=sys.stderr)
    if result["warnings"]:
        print("Warnings:", file=sys.stderr)
        for warning in result["warnings"]:
            print(f"  - {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
