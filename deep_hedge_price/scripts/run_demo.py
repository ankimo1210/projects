"""Run the practical quick end-to-end workflow."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from deep_hedge_price.config import load_config
from deep_hedge_price.experiments import prepare_experiment_artifacts
from deep_hedge_price.notebook import execute_and_export_notebook
from deep_hedge_price.plotting import generate_static_figures
from deep_hedge_price.report import build_standalone_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/quick.yaml")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config_path = Path(args.config).resolve()
    root = config_path.parent.parent
    config = load_config(config_path)
    manifest = prepare_experiment_artifacts(config, root, force=args.force)
    generate_static_figures(config, root, manifest)
    report = build_standalone_report(config, root, manifest)
    notebook, notebook_html = execute_and_export_notebook(root)
    logging.info("Standalone report: %s", report)
    logging.info("Executed notebook: %s", notebook)
    logging.info("Notebook HTML: %s", notebook_html)


if __name__ == "__main__":
    main()
