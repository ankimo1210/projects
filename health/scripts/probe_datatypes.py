"""Probe projections or all audited sources without writing DuckDB."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from health.auth import AuthError, GoogleHealthAuth
from health.client import HealthClient
from health.probe import run_probe, run_source_probe
from health.source_catalog import load_sources

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_OUTPUT_DIR = DATA_DIR / "probe"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-sources",
        action="store_true",
        help="audit every catalog source, preserving original response bytes",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=200,
        help="physical Health request cap for --all-sources (default: 200)",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    if args.max_requests < 0:
        parser.error("--max-requests must be nonnegative")
    result_code = 0
    try:
        auth = GoogleHealthAuth.from_env(DATA_DIR)
        if args.all_sources:
            manifest = run_source_probe(
                HealthClient(auth),
                args.output_dir,
                load_sources(),
                max_requests=args.max_requests,
                report=print,
            )
            if manifest["stopped_reason"] == "auth_error":
                result_code = 2
            elif manifest["stopped_reason"] or any(
                entry["status"] not in {"ok", "empty", "unsupported", "unknown_history"}
                for entry in manifest["sources"].values()
            ):
                result_code = 1
        else:
            run_probe(HealthClient(auth), args.output_dir, report=print)
    except AuthError:
        print(
            "Google Health authentication failed; reconnect with the required readonly scopes.",
            file=sys.stderr,
        )
        return 2
    except OSError:
        print(
            "Probe storage failed; received files were retained. Check the output filesystem.",
            file=sys.stderr,
        )
        return 1
    print(f"manifest: {args.output_dir / 'manifest.json'}")
    return result_code


if __name__ == "__main__":
    raise SystemExit(main())
