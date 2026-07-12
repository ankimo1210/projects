"""Fetch the Milestone-1 sample corpus (Aozora Bunko, public domain).

Usage: uv run --no-sync python jp_llm_lab/scripts/fetch_sample_corpus.py [--force]
"""

from __future__ import annotations

import argparse

from jp_llm_lab.data.sample_corpus import fetch_sample_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()
    manifest = fetch_sample_corpus(force=args.force)
    for name, entry in manifest["sources"].items():
        tag = "SYNTHETIC" if entry["synthetic"] else "real"
        print(f"{name:16s} {tag:9s} {entry['n_chars']:>8,} chars  {entry['title']} / {entry['author']}")


if __name__ == "__main__":
    main()
