"""Build the reproducible corpus snapshots (spec §4.1).

Usage:
  uv run --no-sync python jp_llm_lab/scripts/fetch_snapshots.py --source wikipedia
  uv run --no-sync python jp_llm_lab/scripts/fetch_snapshots.py --source fineweb2ja [--main-chars 170000000]
"""

from __future__ import annotations

import argparse
import os
import sys

from jp_llm_lab.data.snapshots import build_fineweb2ja_snapshots, build_wikipedia_snapshot


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=["fineweb2ja", "wikipedia", "all"], default="all")
    ap.add_argument("--main-chars", type=int, default=170_000_000)
    args = ap.parse_args()
    if args.source in ("wikipedia", "all"):
        build_wikipedia_snapshot()
    if args.source in ("fineweb2ja", "all"):
        build_fineweb2ja_snapshots(main_chars=args.main_chars)


if __name__ == "__main__":
    main()
    # datasets/pyarrow streaming threads crash Python during finalization
    # (PyGILState_Release after data is fully written). Skip finalization —
    # all outputs are flushed and saved inside main().
    sys.stdout.flush()
    os._exit(0)
