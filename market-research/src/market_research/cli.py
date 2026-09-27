"""Local command-line entry point."""

from __future__ import annotations

import argparse
import json

from .services import build_demo_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="market-research")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo", help="Run the offline synthetic workflow")
    demo.add_argument("--json", action="store_true", help="Print machine-readable summary")
    args = parser.parse_args(argv)
    if args.command == "demo":
        run = build_demo_run()
        summary = {
            "mode": run.mode,
            "run_id": run.run_id,
            "input_hash": run.input_hash,
            "observations": len(run.prices),
            "assets": list(run.prices.columns),
            "last_equity": round(float(run.backtest.equity.iloc[-1]), 8),
        }
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
        else:
            print(f"合成デモ {run.run_id}: {len(run.prices)}観測、終値ベースの研究近似")
        return 0
    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
