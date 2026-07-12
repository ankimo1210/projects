"""Run transaction-cost and risk-objective experiments."""

from __future__ import annotations

import argparse
from pathlib import Path

from deep_hedge_price.config import load_config
from deep_hedge_price.experiments import prepare_experiment_artifacts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/quick.yaml")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    prepare_experiment_artifacts(
        load_config(config_path), config_path.parent.parent, force=args.force
    )


if __name__ == "__main__":
    main()
