"""Environment diagnostics CLI — prints a readable table and saves JSON.

Usage: uv run --no-sync python jp_llm_lab/scripts/diagnose_env.py [--out PATH]
"""

from __future__ import annotations

import argparse
from dataclasses import asdict

from jp_llm_lab.utils.env import collect_env_report, recommend_setup
from jp_llm_lab.utils.io import repo_root, save_json


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="output JSON path")
    args = parser.parse_args()

    report = collect_env_report()
    setup = recommend_setup(report)

    print("=== Environment report ===")
    for key, value in asdict(report).items():
        print(f"{key:20s} {value}")
    print("\n=== Recommended setup (coarse prior — M3 benchmarks the real optimum) ===")
    for key, value in setup.as_dict().items():
        print(f"{key:24s} {value}")

    out = args.out or repo_root() / "reports" / "env" / "env_report.json"
    save_json({"report": asdict(report), "recommendation": setup.as_dict()}, out)
    print(f"\nsaved: {out}")


if __name__ == "__main__":
    main()
