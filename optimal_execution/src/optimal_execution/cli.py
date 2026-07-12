"""Command-line interface for the reproducible experiment pipeline."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .config import Config, load_config
from .experiments import (
    build_manifest,
    evaluate,
    run_all,
    run_classical,
    run_lob,
    train_rl,
)
from .report import build_report, build_reports


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="optimal-execution",
        description="Synthetic market-microstructure and optimal-execution visual lab",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(name: str, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.add_argument(
            "--config",
            type=Path,
            default=Path("configs/quick.yaml"),
            help="YAML profile (default: configs/quick.yaml)",
        )
        return command

    add_config("classical", "run classical schedule-world experiments A--E")
    add_config("lob", "run reactive LOB experiments F--G")
    train = add_config("train-rl", "train residual/free PPO and ablations")
    train.add_argument("--force", action="store_true", help="retrain even when checkpoints exist")
    evaluate_cmd = add_config("evaluate", "run OOS, stress, ablation, and shift evaluation H--J")
    evaluate_cmd.add_argument("--force-train", action="store_true", help="retrain policies first")
    report = add_config("report", "build a standalone offline HTML report")
    report.add_argument("--locale", choices=("en", "ja", "all"), default="en")
    add_config("notebook", "execute and export the visual-lab notebook")
    all_cmd = add_config("all", "run all stages, both reports, and the notebook")
    all_cmd.add_argument("--force-train", action="store_true", help="retrain policies first")
    return parser


def _load(path: Path) -> Config:
    if not path.exists():
        raise FileNotFoundError(f"configuration not found: {path.resolve()}")
    return load_config(path)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    cfg = _load(args.config)

    if args.command == "classical":
        run_classical(cfg)
    elif args.command == "lob":
        run_lob(cfg)
    elif args.command == "train-rl":
        train_rl(cfg, force=args.force)
    elif args.command == "evaluate":
        evaluate(cfg, force_train=args.force_train)
    elif args.command == "report":
        outputs = (
            build_reports(cfg)
            if args.locale == "all"
            else {args.locale: build_report(cfg, args.locale)}
        )
        for locale, path in outputs.items():
            print(f"[{locale}] {path}")
        build_manifest(cfg)
    elif args.command == "notebook":
        from .notebook import execute_notebook

        output = execute_notebook(cfg, args.config)
        print(output)
        build_manifest(cfg)
    elif args.command == "all":
        run_all(cfg, force_train=args.force_train)
        outputs = build_reports(cfg)
        from .notebook import execute_notebook

        notebook = execute_notebook(cfg, args.config)
        build_manifest(cfg)
        print(f"English report: {outputs['en']}")
        print(f"Japanese report: {outputs['ja']}")
        print(f"Notebook HTML: {notebook}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
