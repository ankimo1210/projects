"""Build or verify the fixed paper-corpus retrieval evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.retrieval import (
    attach_retrieval_status,
    evaluate_retrieval,
    render_retrieval_metrics,
    validate_retrieval_metrics,
)
from paper_corpus.retrieval_gold import (
    DEFAULT_RETRIEVAL_METRICS_OUTPUT,
    DEFAULT_RETRIEVAL_QUERIES_OUTPUT,
    render_retrieval_queries,
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
        default=DEFAULT_RETRIEVAL_METRICS_OUTPUT,
        help="metrics destination; use a corpus-local path for full-corpus audits",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    expected_queries = render_retrieval_queries()
    if args.write:
        if args.corpus_root is None:
            raise SystemExit("--write requires --corpus-root")
        DEFAULT_RETRIEVAL_QUERIES_OUTPUT.write_text(expected_queries, encoding="utf-8")
        metrics = evaluate_retrieval(args.corpus_root)
        validate_retrieval_metrics(metrics)
        rendered = render_retrieval_metrics(metrics)
        args.metrics_output.write_text(rendered, encoding="utf-8")
        (args.corpus_root / "retrieval_evaluation.json").write_text(rendered, encoding="utf-8")
        attach_retrieval_status(args.corpus_root, metrics)
        print(
            f"Hit@5={metrics['hit_at_5']:.3f} "
            f"P0 Hit@5={metrics['p0_hit_at_5']:.3f} "
            f"queries={metrics['query_count']}"
        )
        return 0
    if (
        not DEFAULT_RETRIEVAL_QUERIES_OUTPUT.is_file()
        or not DEFAULT_RETRIEVAL_METRICS_OUTPUT.is_file()
    ):
        print("Gold retrieval questions or metrics are missing")
        return 1
    if DEFAULT_RETRIEVAL_QUERIES_OUTPUT.read_text(encoding="utf-8") != expected_queries:
        print(f"Gold retrieval questions are stale: {DEFAULT_RETRIEVAL_QUERIES_OUTPUT}")
        return 1
    tracked_metrics = json.loads(DEFAULT_RETRIEVAL_METRICS_OUTPUT.read_text(encoding="utf-8"))
    validate_retrieval_metrics(tracked_metrics)
    if args.corpus_root is not None:
        expected_metrics = render_retrieval_metrics(evaluate_retrieval(args.corpus_root))
        if DEFAULT_RETRIEVAL_METRICS_OUTPUT.read_text(encoding="utf-8") != expected_metrics:
            print(f"Gold retrieval metrics are stale: {DEFAULT_RETRIEVAL_METRICS_OUTPUT}")
            return 1
    print("Gold retrieval questions and metrics are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
