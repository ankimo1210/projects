"""Import reviewed MinerU regions into a compact, tracked gold-label inventory."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .gold import DEFAULT_MANIFEST_OUTPUT, GOLD_ROOT

DEFAULT_LAYOUT_LABELS_OUTPUT = GOLD_ROOT / "gold_layout_labels.json"
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$).*?(?<!\$)\$(?!\$)", re.DOTALL)


class _TableCellCounter(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in {"td", "th"}:
            self.count += 1


def table_cell_count(html: str) -> int:
    """Count structural HTML cells, including merged cells once."""

    parser = _TableCellCounter()
    parser.feed(html)
    return parser.count


def _content_list_path(mineru_root: Path, paper_id: str) -> Path:
    matches = sorted((mineru_root / paper_id).glob("*/**/*_content_list.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one MinerU content list for {paper_id}, found {len(matches)}")
    return matches[0]


def build_layout_labels(
    mineru_root: Path,
    *,
    reviewer: str,
    manifest_path: Path = DEFAULT_MANIFEST_OUTPUT,
) -> dict[str, Any]:
    """Build per-source-page counts after a reviewer audits layout overlays."""

    if not reviewer.strip():
        raise ValueError("reviewer is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selections: dict[str, list[int]] = defaultdict(list)
    for page in manifest["selected_pages"]:
        selections[str(page["paper_id"])].append(int(page["page_number"]))

    labels: list[dict[str, Any]] = []
    for paper_id, source_pages in sorted(selections.items()):
        items = json.loads(_content_list_path(mineru_root, paper_id).read_text(encoding="utf-8"))
        by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            by_page[int(item["page_idx"])].append(item)
        if set(by_page) != set(range(len(source_pages))):
            raise ValueError(f"MinerU page mapping is incomplete for {paper_id}")
        for page_idx, source_page in enumerate(source_pages):
            page_items = by_page[page_idx]
            equations = sum(item.get("type") == "equation" for item in page_items)
            inline = sum(
                len(INLINE_MATH_RE.findall(str(item.get("text") or "")))
                for item in page_items
                if item.get("type") == "text"
            )
            tables = [item for item in page_items if item.get("type") == "table"]
            labels.append(
                {
                    "gold_page_id": f"{paper_id}:p{source_page:04d}",
                    "paper_id": paper_id,
                    "page_number": source_page,
                    "display_equation_regions": equations,
                    "inline_equation_regions": inline,
                    "table_regions": len(tables),
                    "table_cell_regions": sum(
                        table_cell_count(str(item.get("table_body") or "")) for item in tables
                    ),
                    "layout_verification_status": "verified",
                    "reviewer": reviewer,
                }
            )

    totals = {
        "pages": len(labels),
        "display_equations": sum(item["display_equation_regions"] for item in labels),
        "inline_equations": sum(item["inline_equation_regions"] for item in labels),
        "tables": sum(item["table_regions"] for item in labels),
        "table_cells": sum(item["table_cell_regions"] for item in labels),
    }
    return {
        "gold_layout_labels_version": "1.0.0",
        "extractor": "MinerU 3.4.4 pipeline",
        "audit_basis": "reviewed layout overlays; semantic transcription is scored separately",
        "totals": totals,
        "pages": labels,
    }


def render_layout_labels(labels: dict[str, Any]) -> str:
    """Serialize stable gold labels."""

    return json.dumps(labels, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_layout_labels(
    labels: dict[str, Any], manifest_path: Path = DEFAULT_MANIFEST_OUTPUT
) -> None:
    """Validate identities, totals, target coverage, and reviewer evidence."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = {item["gold_page_id"] for item in manifest["selected_pages"]}
    pages = labels["pages"]
    identities = {item["gold_page_id"] for item in pages}
    if identities != selected or len(identities) != len(pages):
        raise ValueError("layout labels must cover every selected page exactly once")
    if any(item["layout_verification_status"] != "verified" for item in pages):
        raise ValueError("all tracked layout labels must be reviewer verified")
    if any(not str(item["reviewer"]).strip() for item in pages):
        raise ValueError("all tracked layout labels require a reviewer")
    expected_totals = {
        "pages": len(pages),
        "display_equations": sum(item["display_equation_regions"] for item in pages),
        "inline_equations": sum(item["inline_equation_regions"] for item in pages),
        "tables": sum(item["table_regions"] for item in pages),
        "table_cells": sum(item["table_cell_regions"] for item in pages),
    }
    if labels["totals"] != expected_totals:
        raise ValueError("gold layout totals do not match page labels")
    targets = manifest["targets"]
    if expected_totals["pages"] < targets["minimum_pages"]:
        raise ValueError("gold page target is not met")
    if expected_totals["display_equations"] < targets["minimum_display_equations"]:
        raise ValueError("gold display-equation target is not met")
    if expected_totals["inline_equations"] < targets["minimum_inline_equations"]:
        raise ValueError("gold inline-equation target is not met")
    if expected_totals["table_cells"] < targets["minimum_table_cells"]:
        raise ValueError("gold table-cell target is not met")
