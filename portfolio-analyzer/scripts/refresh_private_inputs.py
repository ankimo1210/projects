"""Refresh the WSL copy of shared Drive inputs without copying model settings."""

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
    args = parser.parse_args()
    try:
        source = _external(PROJECT_ROOT, data_dir(PROJECT_ROOT))
        cache = _external(PROJECT_ROOT, args.cache_dir)
        connection = args.connection_root
        if connection is None:
            if os.name != "nt":
                raise ValueError("Specify the Drive connection point on this platform")
            connection = Path(source.anchor)
        online = refresh_inputs(source, cache, connection_root=connection)
    except (ValueError, OSError):
        print(
            "Private input refresh stopped: check Drive, missing files or local edits.",
            file=sys.stderr,
        )
        return 2
    print(json.dumps({"source_available": online, "verified_local_inputs": len(INPUT_FILES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
