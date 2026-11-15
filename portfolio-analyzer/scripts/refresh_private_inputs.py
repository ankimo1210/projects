"""Refresh shared inputs or publish generated reports between Windows and WSL."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer.private_storage import (  # noqa: E402
    INPUT_FILES,
    _external,
    data_dir,
    publish_reports,
    refresh_inputs,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".local/share/repo-private/projects/portfolio-analyzer/data",
    )
    parser.add_argument(
        "--connection-root",
        type=Path,
        help="Drive mount point; Windows defaults to the source volume root",
    )
    parser.add_argument(
        "--reports", action="store_true", help="publish generated local reports to Drive"
    )
    args = parser.parse_args()
    try:
        source = _external(PROJECT_ROOT, data_dir(PROJECT_ROOT))
        cache = _external(PROJECT_ROOT, args.cache_dir)
        connection = args.connection_root
        if connection is None:
            if os.name != "nt":
                raise ValueError("Specify the Drive connection point on this platform")
            connection = Path(source.anchor)
        sync = publish_reports if args.reports else refresh_inputs
        online = sync(source, cache, connection_root=connection)
    except (ValueError, OSError):
        print(
            "Private sync stopped: check Drive, missing files or newer/local edits.",
            file=sys.stderr,
        )
        return 2
    details = (
        {"reports_published": online}
        if args.reports
        else {"source_available": online, "verified_local_inputs": len(INPUT_FILES)}
    )
    print(json.dumps(details))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
