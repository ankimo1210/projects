"""Build, execute and export the visual-lab notebook."""

from __future__ import annotations

import argparse
from pathlib import Path

from rough_volatility.notebook import execute_and_export_notebook

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/quick.yaml"))
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    notebook, html = execute_and_export_notebook(args.root, args.config, timeout=args.timeout)
    print(notebook)
    print(html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
