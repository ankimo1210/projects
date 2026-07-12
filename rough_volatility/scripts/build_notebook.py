"""Build the unexecuted visual-lab notebook."""

from __future__ import annotations

import argparse
from pathlib import Path

from rough_volatility.notebook import build_notebook

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/quick.yaml"))
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    print(build_notebook(args.root, args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
