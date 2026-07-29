"""Build or verify the selected-page and assertion gold artifacts."""

from __future__ import annotations

import argparse

from paper_corpus.gold import (
    DEFAULT_ASSERTIONS_OUTPUT,
    DEFAULT_MANIFEST_OUTPUT,
    build_gold_manifest,
    render_assertions,
    render_json,
)


def parse_args() -> argparse.Namespace:
    """Parse the gold-artifact CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Write or verify both gold artifacts."""

    args = parse_args()
    manifest = render_json(build_gold_manifest())
    assertions = render_assertions()
    if args.write:
        DEFAULT_MANIFEST_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_MANIFEST_OUTPUT.write_text(manifest, encoding="utf-8")
        DEFAULT_ASSERTIONS_OUTPUT.write_text(assertions, encoding="utf-8")
        print(DEFAULT_MANIFEST_OUTPUT)
        print(DEFAULT_ASSERTIONS_OUTPUT)
        return 0
    stale = []
    for path, expected in (
        (DEFAULT_MANIFEST_OUTPUT, manifest),
        (DEFAULT_ASSERTIONS_OUTPUT, assertions),
    ):
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    if stale:
        for path in stale:
            print(f"gold artifact is missing or stale: {path}")
        return 1
    print("paper-corpus gold artifacts are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
