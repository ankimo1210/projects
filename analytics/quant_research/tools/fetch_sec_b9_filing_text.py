"""Fetch B9 previous-filing primary documents into an external raw cache."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_textbook.sec_filing_text import download_previous_filing_documents


def _read_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.expanduser().resolve().read_text(encoding="utf-8"))
    if payload.get("schema_version") != "b9-previous-filing-provenance-v1":
        raise ValueError("provenance sidecar has an unsupported schema")
    if payload.get("quality", {}).get("accepted") is not True:
        raise ValueError("provenance sidecar quality gate did not pass")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("provenance sidecar lacks rows")
    return rows


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--user-agent",
        required=True,
        help="descriptive application name and contact email; never persisted",
    )
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--maximum-attempts", type=int, default=4)
    parser.add_argument("--sleep-seconds", type=float, default=0.2)
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    manifest = download_previous_filing_documents(
        _read_rows(args.provenance),
        args.output_root,
        user_agent=args.user_agent,
        timeout_seconds=args.timeout_seconds,
        maximum_attempts=args.maximum_attempts,
        sleep_seconds=args.sleep_seconds,
        refresh=args.refresh,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["failure_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
