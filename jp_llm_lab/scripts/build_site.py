"""Build the multi-page static learning site (spec §23).

Usage: uv run --no-sync python jp_llm_lab/scripts/build_site.py
"""

from __future__ import annotations

from jp_llm_lab.reporting.site import build_site


def main() -> None:
    path = build_site()
    print(f"site: {path}")


if __name__ == "__main__":
    main()
