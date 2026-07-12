from __future__ import annotations

import argparse
from pathlib import Path

from optimal_execution.config import load_config
from optimal_execution.notebook import execute_notebooks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/quick.yaml"))
    args = parser.parse_args()
    cfg = load_config(args.config)
    for locale, path in execute_notebooks(cfg, args.config).items():
        print(f"[{locale}] {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
