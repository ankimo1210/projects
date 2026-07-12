"""Command-line entry points for experiments, figures and reports."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from rough_volatility.config import load_config
from rough_volatility.experiments import (
    load_artifact_manifest,
    run_all,
    run_microstructure_experiments,
    run_option_experiments,
    run_path_experiments,
)
from rough_volatility.plotting import generate_static_figures
from rough_volatility.report import build_standalone_report

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rough-volatility",
        description="Synthetic rough-volatility and microstructure visual lab",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="enable informative progress logging"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    help_text = {
        "paths": "run experiments A-C (fBM, estimators, OU/fOU)",
        "options": "run experiments D-E (rBergomi, Heston, smiles, skew)",
        "microstructure": "run experiments F-G (Hawkes and noise fragility)",
        "all": "run experiments A-G and export all static figures",
        "report": "build static figures and the standalone offline HTML report",
    }
    for name, description in help_text.items():
        command = subparsers.add_parser(name, help=description, description=description)
        command.add_argument(
            "--config",
            type=Path,
            default=Path("configs/quick.yaml"),
            help="YAML profile path (default: configs/quick.yaml)",
        )
        command.add_argument(
            "--root",
            type=Path,
            default=PROJECT_ROOT,
            help="project output root (defaults to the installed project root)",
        )
        command.add_argument(
            "--force", action="store_true", help="recompute rather than reuse matching artifacts"
        )
        if name == "report":
            command.add_argument(
                "--locale",
                choices=("en", "ja", "all"),
                default="all",
                help="report language(s) to build (default: all)",
            )
    return parser


def _resolve_config(path: Path, root: Path) -> Path:
    if path.is_absolute() or path.exists():
        return path.resolve()
    candidate = root / path
    return candidate.resolve()


def main(argv: Sequence[str] | None = None) -> int:
    """Run a selected experiment/report command and return a process status."""
    parser = _parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    root = args.root.resolve()
    config_path = _resolve_config(args.config, root)
    config = load_config(config_path)
    LOGGER.info("profile=%s fingerprint=%s", config.profile, config.fingerprint())

    if args.command == "paths":
        artifacts = run_path_experiments(config, root, force=args.force)
    elif args.command == "options":
        artifacts = run_option_experiments(config, root, force=args.force)
    elif args.command == "microstructure":
        artifacts = run_microstructure_experiments(config, root, force=args.force)
    elif args.command == "all":
        artifacts = run_all(config, root, force=args.force)
        figures = generate_static_figures(config, root, artifacts)
        LOGGER.info("exported %d static files", len(figures))
    else:
        if args.force:
            artifacts = run_all(config, root, force=True)
        else:
            try:
                artifacts = load_artifact_manifest(config, root)
            except (FileNotFoundError, ValueError):
                artifacts = run_all(config, root, force=False)
        figures = generate_static_figures(config, root, artifacts)
        from rough_volatility.report import build_reports

        if args.locale == "all":
            reports = build_reports(config, root, artifacts)
        else:
            reports = {
                args.locale: build_standalone_report(
                    config, root, artifacts, locale=args.locale
                )
            }
        LOGGER.info("reports=%s static_files=%d", list(reports), len(figures))
    LOGGER.info("artifacts=%d", len(artifacts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
