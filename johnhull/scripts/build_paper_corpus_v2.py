"""Build corpus-v2 records from pinned MinerU pipeline output."""

from __future__ import annotations

import argparse
from pathlib import Path

from paper_corpus.baseline import REFERENCES_ROOT
from paper_corpus.gold import GOLD_PAGE_SELECTIONS
from paper_corpus.mineru import convert_mineru_paper


def parse_args() -> argparse.Namespace:
    """Parse conversion arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-id", action="append", required=True)
    parser.add_argument("--mineru-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=REFERENCES_ROOT / "processed-v2")
    parser.add_argument(
        "--gold-page-mapping",
        action="store_true",
        help="map selected-page MinerU inputs back to their source PDF page numbers",
    )
    return parser.parse_args()


def main() -> int:
    """Convert selected full-PDF MinerU outputs."""

    args = parse_args()
    for paper_id in args.paper_id:
        result = convert_mineru_paper(
            paper_id=paper_id,
            source_pdf=REFERENCES_ROOT / "papers" / f"{paper_id}.pdf",
            mineru_root=args.mineru_root,
            output_dir=args.output_root / paper_id,
            page_mapping=(list(GOLD_PAGE_SELECTIONS[paper_id]) if args.gold_page_mapping else None),
        )
        counts = result["quality"]["counts"]
        print(
            f"{paper_id}: pages={counts['pages']} blocks={counts['blocks']} "
            f"equations={counts['display_equations'] + counts['inline_equations']} "
            f"tables={counts['tables']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
