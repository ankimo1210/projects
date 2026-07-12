"""Command-line interface for training, evaluation, sensitivity and reports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import load_config
from .experiments import prepare_experiment_artifacts
from .notebook import execute_and_export_notebook
from .plotting import generate_static_figures
from .report import build_standalone_report
from .training import train_policy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="deep-hedge-price")
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("train", "evaluate", "sensitivity", "report", "demo"):
        command = subparsers.add_parser(name)
        command.add_argument("--config", default="configs/quick.yaml")
        command.add_argument("--force", action="store_true")
    return parser


def _root_from_config(config_path: str | Path) -> Path:
    path = Path(config_path).resolve()
    if path.parent.name == "configs":
        return path.parent.parent
    return Path.cwd().resolve()


def main(argv: list[str] | None = None) -> int:
    """Run one CLI command and return a process exit code."""
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config_path = Path(args.config)
    config = load_config(config_path)
    root = _root_from_config(config_path)
    if args.command == "train":
        result = train_policy(config, root, force=args.force)
        logging.info("checkpoint=%s reused=%s", result.checkpoint_path, result.reused)
        return 0
    if args.command == "sensitivity":
        manifest = prepare_experiment_artifacts(config, root, force=args.force)
        logging.info("sensitivity=%s", manifest["sensitivity_summary"])
        return 0
    manifest = prepare_experiment_artifacts(config, root, force=args.force)
    if args.command == "evaluate":
        logging.info("metrics=%s", manifest["summary_metrics"])
        return 0
    generate_static_figures(config, root, manifest)
    report = build_standalone_report(config, root, manifest)
    if args.command == "report":
        logging.info("report=%s", report)
        return 0
    notebook, notebook_html = execute_and_export_notebook(root)
    logging.info("report=%s notebook=%s notebook_html=%s", report, notebook, notebook_html)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
