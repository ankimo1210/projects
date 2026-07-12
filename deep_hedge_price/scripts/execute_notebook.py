"""Execute and export the Deep Hedging notebook."""

from __future__ import annotations

import argparse
from pathlib import Path

from deep_hedge_price.config import load_config
from deep_hedge_price.experiments import prepare_experiment_artifacts
from deep_hedge_price.notebook import execute_and_export_notebook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/quick.yaml")
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    root = config_path.parent.parent
    config = load_config(config_path)
    prepare_experiment_artifacts(config, root, force=False)
    execute_and_export_notebook(root)


if __name__ == "__main__":
    main()
