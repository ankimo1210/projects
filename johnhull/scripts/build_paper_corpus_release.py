"""Build or check full paper-corpus v2 release evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.baseline import DEFAULT_OUTPUT as DEFAULT_BASELINE
from paper_corpus.release import (
    build_determinism_report,
    build_release_report,
    release_index,
    render_release_markdown,
    validate_release_report,
    write_determinism_report,
    write_release_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--comparison-root", type=Path)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    return parser.parse_args()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    args = parse_args()
    if args.write:
        report = write_release_artifacts(args.corpus_root, args.baseline)
        if args.comparison_root is not None:
            write_release_artifacts(args.comparison_root, args.baseline)
            determinism = write_determinism_report(args.corpus_root, args.comparison_root)
            print(f"determinism={determinism['status']} files={determinism['compared_file_count']}")
        print(
            f"release={report['status']} papers={report['inventory']['actual_papers']} "
            f"pages={report['inventory']['actual_pages']}"
        )
        return 0

    report = build_release_report(args.corpus_root, args.baseline)
    validate_release_report(report)
    expected = {
        "index.json": _json(release_index(report)),
        "quality_report.json": _json(report),
        "quality_report.md": render_release_markdown(report),
    }
    stale = [
        name
        for name, rendered in expected.items()
        if not (args.corpus_root / name).is_file()
        or (args.corpus_root / name).read_text(encoding="utf-8") != rendered
    ]
    if stale:
        for name in stale:
            print(f"release artifact is missing or stale: {name}")
        return 1
    if args.comparison_root is not None:
        determinism = build_determinism_report(args.corpus_root, args.comparison_root)
        if determinism["status"] != "pass":
            print("full-corpus builds are not byte-identical")
            return 1
    print("full-corpus release evidence is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
