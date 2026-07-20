from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from jhrmbs.cashflow_service import create_issue_cashflow
from jhrmbs.config import load_config
from jhrmbs.dataset import build_dataset
from jhrmbs.exceptions import JHRMBSError
from jhrmbs.forecast import forecast_issue
from jhrmbs.ingest import ingest
from jhrmbs.logging_utils import configure_logging
from jhrmbs.models.training import train_models
from jhrmbs.report import generate_issue_report

LOGGER = logging.getLogger("jhrmbs.cli")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jhrmbs",
        description="JHF MBS public-data prepayment and cash-flow analytics",
    )
    parser.add_argument("--config", type=Path, help="YAML configuration path")
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    commands = parser.add_subparsers(dest="command", required=True)

    ingest_parser = commands.add_parser("ingest", help="download public source snapshots")
    ingest_parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="source id to ingest; repeat to select several",
    )

    dataset_parser = commands.add_parser(
        "build-dataset", help="build issue-month panel and leakage-safe features"
    )
    dataset_parser.add_argument("--manifest", type=Path, help="raw manifest path")

    commands.add_parser("train", help="fit baseline models and run OOS evaluation")

    predict_parser = commands.add_parser("predict", help="forecast one issue")
    predict_parser.add_argument("--issue", required=True, dest="issue_id")
    predict_parser.add_argument("--model", default="champion", dest="model_name")
    predict_parser.add_argument("--run-id")
    predict_parser.add_argument("--mortgage-rate-pct", type=float)
    predict_parser.add_argument("--jgb-10y-pct", type=float)
    predict_parser.add_argument("--rate-feature-shift-pct", type=float, default=0.0)

    cashflow_parser = commands.add_parser("cashflow", help="generate issue cash flows")
    cashflow_parser.add_argument("--issue", required=True, dest="issue_id")
    cashflow_parser.add_argument("--scenario", choices=("model", "psj"), default="model")
    cashflow_parser.add_argument("--model", default="champion", dest="model_name")
    cashflow_parser.add_argument("--run-id")
    cashflow_parser.add_argument("--psj-terminal-cpr-pct", type=float, default=None)
    cashflow_parser.add_argument("--valuation-yield-pct", type=float)
    cashflow_parser.add_argument("--cleanup-call", action="store_true")
    cashflow_parser.add_argument("--include-other-decrements", action="store_true")
    cashflow_parser.add_argument("--rate-feature-shift-pct", type=float, default=0.0)

    report_parser = commands.add_parser("report", help="build a self-contained issue report")
    report_parser.add_argument("--issue", required=True, dest="issue_id")
    report_parser.add_argument("--model", default="champion", dest="model_name")
    report_parser.add_argument("--run-id")
    report_parser.add_argument("--psj-terminal-cpr-pct", type=float, default=6.0)
    report_parser.add_argument("--valuation-yield-pct", type=float)
    report_parser.add_argument("--cleanup-call", action="store_true")
    return parser


def _print(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        log_path = configure_logging(config.data_root / "logs", verbose=args.verbose)
        if args.command == "ingest":
            path = ingest(config, set(args.sources) if args.sources else None)
            _print({"manifest": path, "log": log_path})
        elif args.command == "build-dataset":
            outputs = build_dataset(config, args.manifest)
            _print({name: path for name, path in outputs.items()})
        elif args.command == "train":
            run_directory = train_models(config)
            _print({"run_directory": run_directory})
        elif args.command == "predict":
            forecast = forecast_issue(
                config,
                args.issue_id,
                model_name=args.model_name,
                run_id=args.run_id,
                mortgage_rate_pct=args.mortgage_rate_pct,
                jgb_10y_pct=args.jgb_10y_pct,
                rate_feature_shift_pct=args.rate_feature_shift_pct,
            )
            _print(
                {
                    "issue_id": args.issue_id,
                    "rows": len(forecast),
                    "first_payment_month": forecast["payment_month"].min(),
                    "last_payment_month": forecast["payment_month"].max(),
                }
            )
        elif args.command == "cashflow":
            if args.scenario == "model" and args.psj_terminal_cpr_pct is not None:
                LOGGER.warning("--psj-terminal-cpr-pct is ignored for --scenario model")
            if args.scenario == "psj":
                if args.model_name != "champion":
                    LOGGER.warning("--model is ignored for --scenario psj")
                if args.run_id:
                    LOGGER.warning("--run-id is ignored for --scenario psj")
                if args.rate_feature_shift_pct:
                    LOGGER.warning("--rate-feature-shift-pct is ignored for --scenario psj")
            frame, summary = create_issue_cashflow(
                config,
                args.issue_id,
                scenario=args.scenario,
                model_name=args.model_name,
                run_id=args.run_id,
                psj_terminal_cpr_pct=(
                    args.psj_terminal_cpr_pct if args.psj_terminal_cpr_pct is not None else 6.0
                ),
                valuation_yield_pct=args.valuation_yield_pct,
                cleanup_call=args.cleanup_call,
                include_published_decrements=args.include_other_decrements,
                rate_feature_shift_pct=args.rate_feature_shift_pct,
            )
            _print({"rows": len(frame), **summary})
        elif args.command == "report":
            report_path = generate_issue_report(
                config,
                args.issue_id,
                model_name=args.model_name,
                run_id=args.run_id,
                psj_terminal_cpr_pct=args.psj_terminal_cpr_pct,
                valuation_yield_pct=args.valuation_yield_pct,
                cleanup_call=args.cleanup_call,
            )
            _print({"report": report_path})
        return 0
    except (JHRMBSError, FileNotFoundError, ValueError, KeyError) as exc:
        LOGGER.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
