"""Probe each implemented Google Health data type without writing DuckDB."""

from __future__ import annotations

import sys
from pathlib import Path

from health.auth import AuthError, GoogleHealthAuth
from health.client import HealthClient
from health.probe import run_probe

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_OUTPUT_DIR = DATA_DIR / "probe"


def main() -> int:
    try:
        auth = GoogleHealthAuth.from_env(DATA_DIR)
        run_probe(HealthClient(auth), DEFAULT_OUTPUT_DIR, report=print)
    except AuthError as exc:
        print(f"Google Health authentication error: {exc}", file=sys.stderr)
        return 2
    print(f"manifest: {DEFAULT_OUTPUT_DIR / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
