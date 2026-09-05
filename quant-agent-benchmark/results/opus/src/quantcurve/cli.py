"""Command-line entry point.

The mandated invocation is::

    PYTHONPATH=src python -m quantcurve.cli run \\
      --market-data /absolute/path/to/market_observations.csv \\
      --output-dir /absolute/path/to/output_directory \\
      --valuation-date 2026-01-15

It is deterministic, needs no network access and works on any conforming data set
without source edits.  Unrecoverable input problems exit non-zero with a message
that names the file and says what to do about it.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from .charts import write_charts
from .cleaning import CleaningConfig
from .holdout import HoldoutConfig
from .io import MarketDataError
from .models import FitConfig
from .outputs import write_outputs
from .report import write_report
from .validation import ValidationConfig
from .workflow import WorkflowConfig, run_workflow

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quantcurve",
        description="Zero-curve research and engineering workflow.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True,
                     help="path to a market_observations.csv file")
    run.add_argument("--output-dir", type=Path, required=True,
                     help="directory to write curves/, diagnostics/ and charts/ into")
    run.add_argument("--valuation-date", required=True,
                     help="ISO-8601 valuation date, e.g. 2026-01-15")
    run.add_argument("--report-path", type=Path, default=None,
                     help="where to write the HTML research report "
                          "(default: <output-dir>/reports/research_report.html)")
    run.add_argument("--grid-points", type=int, default=601,
                     help="rows in curves/curve.csv (minimum 361, default 601)")
    run.add_argument("--grid-max-years", type=float, default=30.0,
                     help="longest grid maturity in years (default 30)")
    run.add_argument("--compact-report", action="store_true",
                     help="shorten the tabular sections of the HTML report")
    run.add_argument("--no-report", action="store_true",
                     help="skip HTML report generation")
    run.add_argument("--no-charts", action="store_true",
                     help="skip chart generation (implies --no-report)")
    run.add_argument("--no-sensitivity", action="store_true",
                     help="skip the sensitivity and stability refits")
    run.add_argument("--quiet", action="store_true", help="suppress progress output")
    return parser


def _run(args: argparse.Namespace) -> int:
    config = WorkflowConfig(
        grid_points=args.grid_points,
        grid_max_years=args.grid_max_years,
        validation=ValidationConfig(),
        cleaning=CleaningConfig(),
        fit=FitConfig(),
        holdout=HoldoutConfig(),
        run_sensitivity=not args.no_sensitivity,
    )
    result = run_workflow(args.market_data, args.valuation_date, config)
    output_dir = Path(args.output_dir)
    paths = write_outputs(result, output_dir)

    charts: dict[str, bytes] = {}
    if not args.no_charts:
        charts = write_charts(result, output_dir / "charts")
    if not args.no_report and not args.no_charts:
        report_path = args.report_path or (output_dir / "reports" / "research_report.html")
        write_report(result, charts, report_path, compact=args.compact_report)
        paths["report"] = Path(report_path)

    if not args.quiet:
        selected = result.model_comparison["model_selected"]
        holdout = result.model_comparison[selected].get("holdout_metrics") or {}
        print(f"valuation date        : {result.valuation_date.date().isoformat()}")
        print(f"observations          : {len(result.cleaning.audit)}")
        print(f"calibrating instruments: {len(result.instruments)}")
        print(f"model selected        : {selected}")
        if holdout:
            print(
                "holdout weighted RMSE : "
                f"{holdout.get('weighted_rmse_bp', float('nan')):.3f} bp "
                f"on {holdout.get('n_instruments', 0)} withheld instruments"
            )
        print(f"curve rows            : {len(result.curve_table)}")
        for name, path in paths.items():
            print(f"  {name:<17}: {path}")
        for warning in result.warnings:
            print(f"  warning          : {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":  # pragma: no cover - argparse enforces this
        return 2
    try:
        return _run(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            "hint: --market-data must point at an existing CSV file with the "
            "documented column set.",
            file=sys.stderr,
        )
        return 2
    except MarketDataError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print(
            "hint: inspect the input file's schema, units, timestamps and quote "
            "values; diagnostics/cleaning.csv records why each row was rejected "
            "when the workflow gets far enough to write it.",
            file=sys.stderr,
        )
        return 2
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except PermissionError as exc:
        print(f"error: cannot write to the output directory: {exc}", file=sys.stderr)
        return 3
    except Exception:  # pragma: no cover - unexpected failure path
        traceback.print_exc()
        print(
            "error: the workflow failed unexpectedly; the traceback above names "
            "the failing stage.",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
