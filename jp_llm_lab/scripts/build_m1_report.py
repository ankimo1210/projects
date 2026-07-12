"""Build the Milestone-1 static HTML report from saved run artifacts.

Usage: uv run --no-sync python jp_llm_lab/scripts/build_m1_report.py
"""

from __future__ import annotations

from jp_llm_lab.reporting.report_m1 import build_m1_report


def main() -> None:
    path = build_m1_report()
    print(f"report: {path}")


if __name__ == "__main__":
    main()
