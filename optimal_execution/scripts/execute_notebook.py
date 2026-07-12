from __future__ import annotations

import argparse
from pathlib import Path

from optimal_execution.config import load_config
from optimal_execution.notebook import execute_notebook


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/quick.yaml"))
    args = parser.parse_args()
    cfg = load_config(args.config)
    print(execute_notebook(cfg, args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
