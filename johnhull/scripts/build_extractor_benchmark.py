"""Write or verify the tracked paper-extractor bake-off."""

from __future__ import annotations

import argparse

from paper_corpus.benchmark import (
    DEFAULT_BAKEOFF_OUTPUT,
    build_bakeoff,
    render_bakeoff,
    validate_bakeoff,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true")
    action.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Write or verify the deterministic benchmark artifact."""

    args = parse_args()
    value = build_bakeoff()
    validate_bakeoff(value)
    expected = render_bakeoff(value)
    if args.write:
        DEFAULT_BAKEOFF_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_BAKEOFF_OUTPUT.write_text(expected, encoding="utf-8")
        print(DEFAULT_BAKEOFF_OUTPUT)
        return 0
    if not DEFAULT_BAKEOFF_OUTPUT.is_file():
        print(f"extractor bake-off is missing: {DEFAULT_BAKEOFF_OUTPUT}")
        return 1
    if DEFAULT_BAKEOFF_OUTPUT.read_text(encoding="utf-8") != expected:
        print(f"extractor bake-off is stale: {DEFAULT_BAKEOFF_OUTPUT}")
        return 1
    print("paper-extractor bake-off is current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
