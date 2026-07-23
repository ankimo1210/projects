"""Build or verify the paper-corpus source and v1 quality baseline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from paper_corpus.baseline import (
    DEFAULT_OUTPUT,
    REFERENCES_ROOT,
    build_baseline,
    render_baseline,
    validate_frozen_baseline,
)
from paper_corpus.profiles import (
    DEFAULT_OUTPUT as DEFAULT_PROFILE_OUTPUT,
)
from paper_corpus.profiles import (
    build_profiles,
    render_profiles,
)


def parse_args() -> argparse.Namespace:
    """Parse the audit CLI arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="write the baseline manifest")
    action.add_argument("--check", action="store_true", help="verify the tracked manifest")
    parser.add_argument("--references-root", type=Path, default=REFERENCES_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--include-page-profiles",
        action="store_true",
        help="also build or check the tracked page-routing profile",
    )
    parser.add_argument("--profile-output", type=Path, default=DEFAULT_PROFILE_OUTPUT)
    return parser.parse_args()


def main() -> int:
    """Run the requested baseline operation."""

    args = parse_args()
    profile_rendered = (
        render_profiles(build_profiles(args.references_root))
        if args.include_page_profiles
        else None
    )
    if args.write:
        rendered = render_baseline(build_baseline(args.references_root))
        args.output.write_text(rendered, encoding="utf-8")
        print(args.output)
        if profile_rendered is not None:
            args.profile_output.write_text(profile_rendered, encoding="utf-8")
            print(args.profile_output)
        return 0
    if not args.output.is_file():
        print(f"missing baseline manifest: {args.output}")
        return 1
    tracked = args.output.read_text(encoding="utf-8")
    manifest = json.loads(tracked)
    try:
        validate_frozen_baseline(manifest, args.references_root)
    except ValueError as exc:
        print(f"baseline source integrity failed: {exc}")
        return 1
    if tracked != render_baseline(manifest):
        print(f"baseline manifest is not canonically serialized: {args.output}")
        return 1
    if profile_rendered is not None:
        if not args.profile_output.is_file():
            print(f"missing page profile: {args.profile_output}")
            return 1
        if args.profile_output.read_text(encoding="utf-8") != profile_rendered:
            print(f"page profile is stale: {args.profile_output}")
            return 1
    print(f"baseline manifest is current: {args.output}")
    if profile_rendered is not None:
        print(f"page profile is current: {args.profile_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
