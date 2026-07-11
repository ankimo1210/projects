from __future__ import annotations

import argparse
import webbrowser

from .discovery import discover
from .exporting import export_dataset
from .pipeline import (
    deduplicate_questions,
    extract_sources,
    fetch_sources,
    normalize_and_classify,
    score_questions,
)
from .reporting import build_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wset-corpus")
    commands = parser.add_subparsers(dest="command", required=True)

    discover_parser = commands.add_parser("discover")
    discover_parser.add_argument("--use-api", action="store_true")
    for name in ("fetch", "extract", "normalize", "classify", "deduplicate", "score"):
        command = commands.add_parser(name)
        if name in {"fetch", "extract"}:
            command.add_argument("--source")
    export_parser = commands.add_parser("export")
    export_parser.add_argument("--mode", choices=("private", "public-safe"), default="private")
    report_parser = commands.add_parser("report")
    report_parser.add_argument("--open", action="store_true")
    pipeline = commands.add_parser("pipeline")
    pipeline.add_argument("--source")
    pipeline.add_argument("--language", choices=("ja", "en"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "discover":
        print(discover(use_api=args.use_api))
    elif args.command == "fetch":
        print(f"Fetched/checked {len(fetch_sources(args.source))} source URLs")
    elif args.command == "extract":
        print(f"Extracted {len(extract_sources(args.source))} candidates")
    elif args.command in {"normalize", "classify"}:
        print(f"Normalized/classified {len(normalize_and_classify())} candidates")
    elif args.command == "deduplicate":
        print(f"Wrote {len(deduplicate_questions())} duplicate rows")
    elif args.command == "score":
        print(f"Scored {len(score_questions())} candidates")
    elif args.command == "export":
        for path in export_dataset(args.mode):
            print(path)
    elif args.command == "report":
        path = build_report()
        print(path)
        if args.open:
            webbrowser.open(path.as_uri())
    elif args.command == "pipeline":
        fetch_sources(args.source)
        questions = extract_sources(args.source)
        if args.language:
            questions = [question for question in questions if question.language == args.language]
        normalize_and_classify()
        deduplicate_questions()
        score_questions()
        export_dataset("private")
        export_dataset("public-safe")
        print(build_report())


if __name__ == "__main__":
    main()
