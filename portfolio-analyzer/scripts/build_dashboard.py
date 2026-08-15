#!/usr/bin/env python3
"""Build the local portfolio dashboard from a private JSON snapshot."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer import (
    apply_proposal,
    build_artifact,
    load_analysis_reference,
    load_portfolio,
    validate_portfolio,
)

DEFAULT_REFERENCE = PROJECT_ROOT / "data/analysis_reference.private.json"


def find_delivery_script() -> Path:
    configured = os.environ.get("DATA_ANALYTICS_PLUGIN_ROOT")
    if configured:
        candidate = Path(configured) / "skills/build-report/scripts/deliver_portable_artifact.mjs"
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"portable builder not found under {configured}")

    cache_root = Path(
        "/mnt/c/Users/Kazumasa/.codex/plugins/cache/openai-curated-remote/data-analytics"
    )
    candidates = sorted(
        cache_root.glob("*/skills/build-report/scripts/deliver_portable_artifact.mjs"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            "Data Analytics portable builder was not found. Set DATA_ANALYTICS_PLUGIN_ROOT."
        )
    return candidates[0]


def apply_portable_scrollbar_fix(output: Path) -> None:
    """Prevent the shared reader's 100vw top bar from adding scrollbar-width overflow."""
    html = output.read_text(encoding="utf-8")
    marker = "</head>"
    if marker not in html:
        raise ValueError("portable HTML has no closing head tag")
    style = (
        '<style data-portfolio-scrollbar-fix="true">html,body{overflow-x:clip!important}</style>\n'
    )
    output.write_text(html.replace(marker, f"{style}{marker}", 1), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data/portfolio.private.json",
        help="portfolio JSON snapshot",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "dist/portfolio-dashboard.html",
        help="self-contained dashboard HTML",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=DEFAULT_REFERENCE,
        help="look-through, sensitivity, and valuation reference JSON",
    )
    parser.add_argument(
        "--proposal",
        type=Path,
        help="optional trade proposal JSON for before/after comparison",
    )
    parser.add_argument(
        "--no-analysis-reference",
        action="store_true",
        help="build only the basic allocation and stress dashboard",
    )
    parser.add_argument(
        "--artifact-only",
        action="store_true",
        help="write artifact.json without invoking the portable HTML builder",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    portfolio = load_portfolio(args.input)
    issues = validate_portfolio(portfolio)
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    artifact_path = output.parent / "artifact.json"
    try:
        source_path = args.input.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        source_path = "provided portfolio JSON"
    analysis_reference = None
    reference_source_path = "data/analysis_reference.private.json"
    if not args.no_analysis_reference:
        if args.reference.is_file():
            analysis_reference = load_analysis_reference(args.reference)
            try:
                reference_source_path = (
                    args.reference.resolve().relative_to(PROJECT_ROOT).as_posix()
                )
            except ValueError:
                reference_source_path = "provided analysis reference JSON"
        elif args.reference != DEFAULT_REFERENCE:
            print(f"ERROR: analysis reference not found: {args.reference}", file=sys.stderr)
            return 1
        else:
            print("WARNING: analysis reference not found; building basic dashboard")
    proposal = None
    proposal_source_path = "data/rebalancing-proposal.private.json"
    if args.proposal is not None:
        if not args.proposal.is_file():
            print(f"ERROR: proposal not found: {args.proposal}", file=sys.stderr)
            return 1
        proposal = apply_proposal(portfolio, args.proposal)
        try:
            proposal_source_path = args.proposal.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            proposal_source_path = "provided proposal JSON"
    artifact = build_artifact(
        portfolio,
        analysis_reference=analysis_reference,
        proposal=proposal,
        source_path=source_path,
        reference_source_path=reference_source_path,
        proposal_source_path=proposal_source_path,
    )
    artifact_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"artifact: {artifact_path}")

    if args.artifact_only:
        return 0

    try:
        delivery_script = find_delivery_script()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print(
            "Run again with --artifact-only to produce validated input without HTML packaging.",
            file=sys.stderr,
        )
        return 1
    portable_scripts = delivery_script.parent
    plugin_version = delivery_script.parents[3].name
    print(f"portable builder: data-analytics/{plugin_version}")
    build_result = subprocess.run(
        [
            "node",
            str(portable_scripts / "build_portable_artifact.mjs"),
            "--input",
            str(artifact_path),
            "--output",
            str(output),
        ],
        cwd=WORKSPACE_ROOT,
        check=False,
    )
    if build_result.returncode != 0:
        return build_result.returncode
    apply_portable_scrollbar_fix(output)
    verify_result = subprocess.run(
        [
            "node",
            str(portable_scripts / "verify_portable_artifact.mjs"),
            "--artifact",
            str(artifact_path),
            "--html",
            str(output),
        ],
        cwd=WORKSPACE_ROOT,
        check=False,
    )
    if verify_result.returncode != 0:
        return verify_result.returncode
    print(f"dashboard: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
