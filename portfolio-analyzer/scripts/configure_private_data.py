"""Select this machine's private portfolio data directory once."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from portfolio_analyzer.private_storage import configure  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        path = configure(PROJECT_ROOT, args.data_dir)
    except (ValueError, OSError) as error:
        print(f"Private data setup: {error}", file=sys.stderr)
        return 2
    print(f"Private input path configured: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
