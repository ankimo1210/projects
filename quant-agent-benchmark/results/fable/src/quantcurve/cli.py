"""Command-line interface.

    PYTHONPATH=src python -m quantcurve.cli run --market-data <csv> --output-dir <dir> --valuation-date YYYY-MM-DD

Exit codes: 0 success, 2 unrecoverable input error (message on stderr), 1 unexpected failure.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

from .conventions import DEFAULT_STUB_RULE
from .io import parse_valuation_date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantcurve", description="Robust zero-curve construction, validation, risk and reporting.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="fit and validate a curve")
    run.add_argument("--market-data", type=Path, required=True, help="CSV of market observations")
    run.add_argument("--output-dir", type=Path, required=True, help="directory for curves/, diagnostics/, charts/ (created)")
    run.add_argument("--valuation-date", required=True, help="YYYY-MM-DD")
    run.add_argument("--report-dir", type=Path, default=None, help="directory for research_report.html (default: <output-dir>/reports)")
    run.add_argument("--stub-rule", choices=["forward", "round", "linspace", "ceil"], default=DEFAULT_STUB_RULE, help="schedule rule for non-integer tenors")
    run.add_argument("--lambda", dest="lambda_fixed", type=float, default=None, help="fix the smoothing parameter instead of cross-validating it")
    run.add_argument("--grid-step", type=float, default=1.0 / 24.0, help="grid spacing in years (default 1/24)")
    run.add_argument("--grid-end", type=float, default=30.0, help="last grid maturity in years (default 30; extended to the longest instrument)")
    run.add_argument("--folds", type=int, default=5, help="number of maturity-grouped CV folds")
    run.add_argument("--max-stale-days", type=int, default=0, help="quotes older than this many days before the valuation date are excluded")
    run.add_argument("--noise-replications", type=int, default=20, help="replications for the quote-noise bootstrap")
    run.add_argument("--seed", type=int, default=20260115, help="seed for the quote-noise bootstrap")
    run.add_argument("--skip-sensitivity", action="store_true", help="skip the sensitivity refits (faster)")
    run.add_argument("--quiet", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command != "run":  # pragma: no cover - argparse enforces the subcommand
        return 2
    try:
        valuation_date = parse_valuation_date(args.valuation_date)
        if args.folds < 2:
            raise ValueError("--folds must be at least 2")
        if args.grid_step <= 0 or args.grid_end <= 0:
            raise ValueError("--grid-step and --grid-end must be positive")
        from .workflow import WorkflowOptions, run_workflow

        opts = WorkflowOptions(
            market_data=args.market_data.resolve(),
            output_dir=args.output_dir.resolve(),
            valuation_date=valuation_date,
            report_dir=args.report_dir.resolve() if args.report_dir else None,
            stub_rule=args.stub_rule,
            lambda_fixed=args.lambda_fixed,
            grid_step=args.grid_step,
            grid_end=args.grid_end,
            n_folds=args.folds,
            max_stale_days=args.max_stale_days,
            skip_sensitivity=args.skip_sensitivity,
            noise_replications=args.noise_replications,
            seed=args.seed,
        )
        result = run_workflow(opts)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover - defensive
        print(f"unexpected failure: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        return 1
    if not args.quiet:
        h = result.holdout.metrics
        print(f"quantcurve run complete in {result.timings['total']:.1f}s")
        print(f"  observations: {result.cleaning.summary['n_observations']}  usable instruments: {len(result.table)}  actions: {result.cleaning.summary['actions']}")
        print(f"  selected model: {result.selected_model}  lambda={result.adv.lam:.4g}  penalty power={result.adv.power:g}")
        print(f"  holdout RMSE (bp): advanced {h['advanced']['overall']['rmse_bp']:.3f}  baseline {h['baseline']['overall']['rmse_bp']:.3f}")
        print(f"  outputs: {result.options.output_dir}")
        print(f"  report:  {result.files.get('report')}")
        for w in result.warnings:
            print(f"  warning: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
