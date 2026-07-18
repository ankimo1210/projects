"""Command-line interface for training, evaluation, sensitivity and reports."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import load_config
from .experiments import prepare_experiment_artifacts
from .notebook import execute_and_export_notebook
from .plotting import generate_static_figures
from .pricing_ablation import run_pricing_ablation
from .pricing_config import load_pricing_config, pricing_run_directory
from .pricing_data import generate_black_scholes_dataset
from .pricing_evaluation import evaluate_pricing_run
from .pricing_notebook import execute_pricing_notebook
from .pricing_report import build_pricing_report
from .pricing_training import train_pricing_model
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
    for name in (
        "pricing-generate",
        "pricing-train",
        "pricing-evaluate",
        "pricing-report",
        "pricing-ablation",
        "pricing-demo",
    ):
        command = subparsers.add_parser(name)
        command.add_argument("--config", default="configs/pricing_quick.yaml")
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
    if args.command.startswith("pricing-"):
        return _run_pricing(args.command, config_path, force=args.force)
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


def _require(path: Path, command: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"missing pricing artifact {path}; run `{command}` first")
    return path


def _run_pricing(command: str, config_path: Path, *, force: bool) -> int:
    config = load_pricing_config(config_path)
    root = _root_from_config(config_path)
    run = pricing_run_directory(config, root)
    manifest = run / "pricing_dataset.json"
    checkpoint = run / "pricing_best.pt"
    polynomial = run / "polynomial_baseline.npz"
    evaluation = run / "pricing_evaluation.json"

    if command == "pricing-ablation":
        _require(
            manifest, f"python -m deep_hedge_price.cli pricing-generate --config {config_path}"
        )
        output = (
            root / config.output.reports_dir / f"pricing_ablation_{config.output.namespace}.json"
        )
        run_pricing_ablation(config, manifest, output)
        logging.info("pricing_ablation=%s", output)
        return 0

    if command in {"pricing-generate", "pricing-demo"}:
        if force or not manifest.exists():
            generate_black_scholes_dataset(config, run)
        logging.info("pricing_dataset=%s", manifest)
        if command == "pricing-generate":
            return 0
    if command in {"pricing-train", "pricing-demo"}:
        _require(
            manifest, f"python -m deep_hedge_price.cli pricing-generate --config {config_path}"
        )
        result = train_pricing_model(config, manifest, root, force=force)
        logging.info("pricing_checkpoint=%s reused=%s", result.checkpoint_path, result.reused)
        if command == "pricing-train":
            return 0
    if command in {"pricing-evaluate", "pricing-demo"}:
        _require(
            manifest, f"python -m deep_hedge_price.cli pricing-generate --config {config_path}"
        )
        _require(checkpoint, f"python -m deep_hedge_price.cli pricing-train --config {config_path}")
        _require(polynomial, f"python -m deep_hedge_price.cli pricing-train --config {config_path}")
        evaluate_pricing_run(config, manifest, checkpoint, polynomial, root)
        logging.info("pricing_evaluation=%s", evaluation)
        if command == "pricing-evaluate":
            return 0
    if command in {"pricing-report", "pricing-demo"}:
        _require(
            evaluation, f"python -m deep_hedge_price.cli pricing-evaluate --config {config_path}"
        )
        report = (
            root
            / config.output.reports_dir
            / f"neural_pricing_report_{config.output.namespace}.html"
        )
        build_pricing_report(
            evaluation, history_path=run / "pricing_history.json", output_path=report
        )
        notebook, notebook_html = execute_pricing_notebook(root)
        logging.info(
            "pricing_report=%s pricing_notebook=%s pricing_notebook_html=%s",
            report,
            notebook,
            notebook_html,
        )
        return 0
    raise ValueError(f"unsupported pricing command {command}")


if __name__ == "__main__":
    raise SystemExit(main())
