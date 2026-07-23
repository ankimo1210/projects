"""Build or verify evidence-backed claims and semantic paper chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.claim_gold import (
    DEFAULT_CLAIM_METRICS_OUTPUT,
    DEFAULT_CLAIM_SPECS_OUTPUT,
    render_claim_specs,
)
from paper_corpus.semantic import (
    build_claim_metrics,
    render_claim_metrics,
    validate_claim_metrics,
    write_paper_semantics,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--corpus-root", type=Path)
    parser.add_argument(
        "--metrics-output",
        type=Path,
        default=DEFAULT_CLAIM_METRICS_OUTPUT,
        help="claim metrics destination; use a corpus-local path for full-corpus audits",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected_specs = render_claim_specs()
    if args.write:
        if args.corpus_root is None:
            raise SystemExit("--write requires --corpus-root")
        DEFAULT_CLAIM_SPECS_OUTPUT.write_text(expected_specs, encoding="utf-8")
        paper_dirs = sorted(
            path for path in args.corpus_root.iterdir() if (path / "metadata.json").is_file()
        )
        if not paper_dirs:
            raise SystemExit("corpus root contains no paper outputs")
        for paper_dir in paper_dirs:
            result = write_paper_semantics(paper_dir)
            print(
                f"{paper_dir.name}: claims={len(result['claims'])} chunks={len(result['chunks'])}"
            )
        metrics = build_claim_metrics(args.corpus_root)
        validate_claim_metrics(metrics)
        args.metrics_output.write_text(render_claim_metrics(metrics), encoding="utf-8")
        print(args.metrics_output)
        return 0
    if not DEFAULT_CLAIM_SPECS_OUTPUT.is_file() or not DEFAULT_CLAIM_METRICS_OUTPUT.is_file():
        print("Gold claim specifications or metrics are missing")
        return 1
    if DEFAULT_CLAIM_SPECS_OUTPUT.read_text(encoding="utf-8") != expected_specs:
        print(f"Gold claim specifications are stale: {DEFAULT_CLAIM_SPECS_OUTPUT}")
        return 1
    tracked_metrics = json.loads(DEFAULT_CLAIM_METRICS_OUTPUT.read_text(encoding="utf-8"))
    validate_claim_metrics(tracked_metrics)
    if args.corpus_root is not None:
        expected_metrics = render_claim_metrics(build_claim_metrics(args.corpus_root))
        if DEFAULT_CLAIM_METRICS_OUTPUT.read_text(encoding="utf-8") != expected_metrics:
            print(f"Gold claim metrics are stale: {DEFAULT_CLAIM_METRICS_OUTPUT}")
            return 1
    print("Gold claim specifications and metrics are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
