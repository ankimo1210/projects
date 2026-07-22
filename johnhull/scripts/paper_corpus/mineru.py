"""Convert MinerU content lists into fail-closed paper-corpus v2 records."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .baseline import REFERENCES_ROOT, read_json
from .formula import validate_equation_record
from .gold import DEFAULT_ASSERTIONS_OUTPUT
from .schema import (
    BlockRecord,
    BoundingBox,
    EquationRecord,
    Provenance,
    TableCell,
    TableRecord,
    stable_record_id,
)
from .table_gold import REVIEWED_BY_KEY

MINERU_VERSION = "3.4.4"
MINERU_MODEL_REVISION = "ed6b654c018d742e65a17671e379c5e6ecc87ec9"
DISPLAY_DELIMITER_RE = re.compile(r"^\s*\$\$\s*(.*?)\s*\$\$\s*$", re.DOTALL)
EQUATION_TAG_RE = re.compile(r"\\tag\s*\{\s*([^}]+?)\s*\}")
INLINE_MATH_RE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
STRICT_NUMBER_RE = re.compile(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?$")
WHITESPACE_RE = re.compile(r"\s+")

TYPE_MAP = {
    "text": "paragraph",
    "aside_text": "paragraph",
    "list": "list",
    "equation": "equation",
    "table": "table",
    "image": "figure",
    "chart": "figure",
    "page_footnote": "footnote",
    "header": "header",
    "footer": "footer",
    "page_number": "footer",
    "code": "other",
}


@dataclass(frozen=True)
class MinerUInput:
    """Resolved MinerU files for one paper."""

    paper_id: str
    content_list: Path
    asset_root: Path


@dataclass(frozen=True)
class TableHtmlCell:
    """Parsed HTML table cell before schema conversion."""

    row: int
    column: int
    text: str
    row_span: int
    column_span: int
    tag: str


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.row = -1
        self.column = 0
        self.occupied: set[tuple[int, int]] = set()
        self.cells: list[TableHtmlCell] = []
        self._active: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.row += 1
            self.column = 0
            return
        if tag not in {"td", "th"} or self.row < 0:
            return
        while (self.row, self.column) in self.occupied:
            self.column += 1
        values = dict(attrs)
        row_span = _positive_int(values.get("rowspan"), default=1)
        column_span = _positive_int(values.get("colspan"), default=1)
        self._active = {
            "row": self.row,
            "column": self.column,
            "row_span": row_span,
            "column_span": column_span,
            "tag": tag,
            "parts": [],
        }
        for row in range(self.row, self.row + row_span):
            for column in range(self.column, self.column + column_span):
                self.occupied.add((row, column))

    def handle_data(self, data: str) -> None:
        if self._active is not None:
            self._active["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag not in {"td", "th"} or self._active is None:
            return
        active = self._active
        text = normalize_text("".join(active["parts"]))
        self.cells.append(
            TableHtmlCell(
                row=active["row"],
                column=active["column"],
                text=text,
                row_span=active["row_span"],
                column_span=active["column_span"],
                tag=active["tag"],
            )
        )
        self.column = active["column"] + active["column_span"]
        self._active = None


def _positive_int(value: str | None, *, default: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace without changing mathematical content."""

    value = unicodedata.normalize("NFC", value.replace("\u00ad", ""))
    return WHITESPACE_RE.sub(" ", value).strip()


def parse_numeric(value: str) -> float | None:
    """Parse only unambiguous scalar cells; leave all other text untyped."""

    candidate = value.strip().replace(",", "")
    if not STRICT_NUMBER_RE.fullmatch(candidate):
        return None
    scale = 0.01 if candidate.endswith("%") else 1.0
    if candidate.endswith("%"):
        candidate = candidate[:-1]
    return float(candidate) * scale


def parse_table_html(value: str) -> list[TableHtmlCell]:
    """Parse structural HTML while retaining merged-header spans."""

    parser = _TableParser()
    parser.feed(value)
    parser.close()
    return parser.cells


def strip_display_delimiters(value: str) -> str:
    """Return the LaTeX body without outer display delimiters."""

    match = DISPLAY_DELIMITER_RE.match(value)
    return (match.group(1) if match else value).strip()


def equation_number(value: str) -> str | None:
    """Extract and normalize a ``\\tag{...}`` equation number."""

    match = EQUATION_TAG_RE.search(value)
    return normalize_text(match.group(1)).replace(" ", "") if match else None


def latex_syntax_status(value: str | None) -> str:
    """Run a conservative delimiter check; this is not a render/compile pass."""

    if not value or "\x00" in value:
        return "failed"
    depth = 0
    escaped = False
    for char in value:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth < 0:
                return "failed"
    return "passed" if depth == 0 else "failed"


def resolve_mineru_input(root: Path, paper_id: str) -> MinerUInput:
    """Resolve one and only one MinerU content list below a paper directory."""

    matches = sorted((root / paper_id).glob("*/**/*_content_list.json"))
    if len(matches) != 1:
        raise ValueError(f"expected one MinerU content list for {paper_id}, found {len(matches)}")
    return MinerUInput(paper_id=paper_id, content_list=matches[0], asset_root=matches[0].parent)


def normalized_bbox_to_pdf(raw: Iterable[float], width: float, height: float) -> BoundingBox:
    """Scale MinerU's 0--1000 coordinates to PDF points."""

    values = [float(value) for value in raw]
    if len(values) != 4:
        raise ValueError("MinerU bbox must have four coordinates")
    x0, y0, x1, y1 = values
    x0 = min(max(x0, 0.0), 1000.0) * width / 1000.0
    x1 = min(max(x1, 0.0), 1000.0) * width / 1000.0
    y0 = min(max(y0, 0.0), 1000.0) * height / 1000.0
    y1 = min(max(y1, 0.0), 1000.0) * height / 1000.0
    bbox = BoundingBox(x0=x0, y0=y0, x1=x1, y1=y1)
    bbox.validate()
    return bbox


def _jsonl(records: Iterable[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
        for record in records
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _asset_relative_path(kind: str, record_id: str, source: Path) -> Path:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    safe_id = record_id.replace(":", "-")
    return Path("assets") / kind / f"{safe_id}-{digest}{source.suffix.lower()}"


def _copy_asset(source: Path, output_dir: Path, kind: str, record_id: str) -> str:
    if not source.is_file():
        raise FileNotFoundError(f"MinerU source asset is missing: {source}")
    relative = _asset_relative_path(kind, record_id, source)
    destination = output_dir / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return relative.as_posix()


def _render_pdf_crop(
    source_pdf: Path,
    output_dir: Path,
    record_id: str,
    page_number: int,
    bbox: BoundingBox,
) -> str:
    """Render one PDF-coordinate region with Poppler for inline-math evidence."""

    scale = 2.0  # 144 dpi / 72 PDF points per inch
    x = math.floor(bbox.x0 * scale)
    y = math.floor(bbox.y0 * scale)
    width = max(1, math.ceil(bbox.x1 * scale) - x)
    height = max(1, math.ceil(bbox.y1 * scale) - y)
    safe_id = record_id.replace(":", "-")
    relative_base = Path("assets") / "inline" / safe_id
    output_base = output_dir / relative_base
    output_base.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftocairo",
            "-png",
            "-singlefile",
            "-f",
            str(page_number),
            "-l",
            str(page_number),
            "-r",
            "144",
            "-x",
            str(x),
            "-y",
            str(y),
            "-W",
            str(width),
            "-H",
            str(height),
            source_pdf.as_posix(),
            output_base.as_posix(),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    rendered = output_base.with_suffix(".png")
    if not rendered.is_file():
        raise RuntimeError(f"Poppler did not produce inline source crop: {rendered}")
    return rendered.relative_to(output_dir).as_posix()


def _item_text(item: dict[str, Any]) -> str:
    item_type = str(item.get("type"))
    if item_type == "list":
        return "\n".join(str(value) for value in item.get("list_items") or [])
    if item_type == "code":
        return str(item.get("code_body") or "")
    if item_type == "table":
        return " ".join(str(value) for value in item.get("table_caption") or [])
    if item_type in {"image", "chart"}:
        key = "chart_caption" if item_type == "chart" else "image_caption"
        return " ".join(str(value) for value in item.get(key) or [])
    return str(item.get("text") or "")


def _block_type(item: dict[str, Any]) -> str:
    if item.get("type") == "text" and item.get("text_level") is not None:
        return "title" if int(item["text_level"]) == 1 else "heading"
    return TYPE_MAP.get(str(item.get("type")), "other")


def _load_assertions(path: Path = DEFAULT_ASSERTIONS_OUTPUT) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _page_profiles(paper_id: str, preflight_path: Path) -> dict[int, dict[str, Any]]:
    preflight = read_json(preflight_path)
    paper = next(item for item in preflight["papers"] if item["paper_id"] == paper_id)
    return {int(item["page_number"]): item for item in paper["pages"]}


def _assertion_bbox(assertion: dict[str, Any], width: float, height: float) -> BoundingBox:
    raw = assertion.get("source_bbox_normalized")
    if not raw:
        raise ValueError(f"verified assertion lacks source bbox: {assertion['assertion_id']}")
    return normalized_bbox_to_pdf(raw, width, height)


def _provenance(source_sha256: str) -> Provenance:
    return Provenance(
        source_pdf_sha256=source_sha256,
        extractor_name="MinerU pipeline",
        extractor_version=MINERU_VERSION,
        model_hash=MINERU_MODEL_REVISION,
    )


def _write_table_exports(
    output_dir: Path,
    table_id: str,
    raw_html: str,
    cells: list[dict[str, Any]],
) -> tuple[str, str, str]:
    safe_id = table_id.replace(":", "-")
    table_dir = output_dir / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    json_path = Path("tables") / f"{safe_id}.json"
    html_path = Path("tables") / f"{safe_id}.html"
    csv_path = Path("tables") / f"{safe_id}.csv"
    (output_dir / json_path).write_text(_json({"cells": cells}), encoding="utf-8")
    (output_dir / html_path).write_text(raw_html.strip() + "\n", encoding="utf-8")
    max_row = max((cell["row"] for cell in cells), default=-1)
    max_column = max((cell["column"] + cell["column_span"] - 1 for cell in cells), default=-1)
    grid = [["" for _ in range(max_column + 1)] for _ in range(max_row + 1)]
    for cell in cells:
        grid[cell["row"]][cell["column"]] = cell["raw_text"]
    with (output_dir / csv_path).open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream, lineterminator="\n").writerows(grid)
    return json_path.as_posix(), html_path.as_posix(), csv_path.as_posix()


def convert_mineru_paper(
    *,
    paper_id: str,
    source_pdf: Path,
    mineru_root: Path,
    output_dir: Path,
    page_mapping: list[int] | None = None,
    preflight_path: Path = REFERENCES_ROOT / "corpus_preflight.json",
    assertions_path: Path = DEFAULT_ASSERTIONS_OUTPUT,
) -> dict[str, Any]:
    """Convert one MinerU result directory to deterministic corpus-v2 artifacts."""

    mineru = resolve_mineru_input(mineru_root, paper_id)
    source_sha256 = hashlib.sha256(source_pdf.read_bytes()).hexdigest()
    provenance = _provenance(source_sha256)
    profiles = _page_profiles(paper_id, preflight_path)
    assertions = [
        item for item in _load_assertions(assertions_path) if item["paper_id"] == paper_id
    ]
    equation_assertions = [item for item in assertions if item["kind"] == "display_formula"]
    table_assertions = [item for item in assertions if item["kind"] == "table_cell"]
    items = json.loads(mineru.content_list.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise TypeError("MinerU content list must be a JSON array")
    seen_input_pages = sorted({int(item["page_idx"]) for item in items})
    expected_input_pages = list(range(len(page_mapping) if page_mapping else len(profiles)))
    if seen_input_pages != expected_input_pages:
        raise ValueError("MinerU page indices are incomplete or non-contiguous")
    page_number_for = {
        index: page_mapping[index] if page_mapping else index + 1 for index in expected_input_pages
    }

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    blocks: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    pages: dict[int, dict[str, Any]] = {}
    ordinals: dict[tuple[int, str], int] = defaultdict(int)
    item_by_page_bbox: dict[tuple[int, tuple[int, ...]], dict[str, Any]] = {}

    for item in items:
        input_page = int(item["page_idx"])
        page_number = page_number_for[input_page]
        profile = profiles[page_number]
        width, height = float(profile["width"]), float(profile["height"])
        bbox = normalized_bbox_to_pdf(item["bbox"], width, height)
        kind = _block_type(item)
        ordinals[(page_number, "block")] += 1
        block_id = stable_record_id(
            paper_id, page_number, "block", ordinals[(page_number, "block")]
        )
        raw_text = _item_text(item)
        normalized_text = normalize_text(raw_text)
        asset_path: str | None = None
        item_type = str(item.get("type"))
        if item_type in {"equation", "table", "image", "chart"}:
            source_asset = mineru.asset_root / str(item["img_path"])
            asset_kind = {
                "equation": "equations",
                "table": "tables",
                "image": "figures",
                "chart": "figures",
            }[item_type]
            asset_path = _copy_asset(source_asset, output_dir, asset_kind, block_id)
        block = BlockRecord(
            block_id=block_id,
            paper_id=paper_id,
            page_number=page_number,
            block_type=kind,  # type: ignore[arg-type]
            bbox=bbox,
            reading_order=ordinals[(page_number, "block")] - 1,
            raw_text=raw_text,
            normalized_text=normalized_text,
            verification_status="unverified" if item_type in {"equation", "table"} else "auto",
            provenance=provenance,
            asset_path=asset_path,
        ).to_dict()
        block["source_bbox_normalized"] = [int(value) for value in item["bbox"]]
        blocks.append(block)
        pages.setdefault(
            page_number,
            {
                "paper_id": paper_id,
                "page_number": page_number,
                "source_pdf_sha256": source_sha256,
                "route": profile["route"],
                "ocr_language": profile["ocr_language"],
                "reading_order_status": ("review" if profile["ocr_language"] == "jpn" else "auto"),
                "block_ids": [],
            },
        )["block_ids"].append(block_id)
        item_by_page_bbox[(page_number, tuple(int(value) for value in item["bbox"]))] = item

        if item_type == "equation":
            ordinals[(page_number, "equation")] += 1
            equation_id = stable_record_id(
                paper_id, page_number, "equation", ordinals[(page_number, "equation")]
            )
            latex = strip_display_delimiters(str(item.get("text") or "")) or None
            record = EquationRecord(
                equation_id=equation_id,
                paper_id=paper_id,
                page_number=page_number,
                bbox=bbox,
                source_asset=asset_path or "",
                latex=latex,
                equation_number=equation_number(latex or ""),
                verification_status="unverified",
                provenance=provenance,
            ).to_dict()
            record.update(
                {
                    "equation_kind": "display",
                    "source_block_id": block_id,
                    "source_bbox_normalized": [int(value) for value in item["bbox"]],
                    "latex_syntax_status": latex_syntax_status(latex),
                }
            )
            equations.append(validate_equation_record(record, output_dir=output_dir))
        elif item_type == "text":
            inline_matches = list(INLINE_MATH_RE.finditer(raw_text))
            if inline_matches:
                asset_path = _render_pdf_crop(source_pdf, output_dir, block_id, page_number, bbox)
                block["asset_path"] = asset_path
            for inline_match in inline_matches:
                ordinals[(page_number, "equation")] += 1
                equation_id = stable_record_id(
                    paper_id, page_number, "equation", ordinals[(page_number, "equation")]
                )
                equations.append(
                    validate_equation_record(
                        {
                            **EquationRecord(
                                equation_id=equation_id,
                                paper_id=paper_id,
                                page_number=page_number,
                                bbox=bbox,
                                source_asset=asset_path or "",
                                latex=inline_match.group(1).strip(),
                                equation_number=None,
                                verification_status="unverified",
                                provenance=provenance,
                            ).to_dict(),
                            "equation_kind": "inline",
                            "crop_scope": "containing_block",
                            "source_block_id": block_id,
                            "source_bbox_normalized": [int(value) for value in item["bbox"]],
                            "latex_syntax_status": latex_syntax_status(inline_match.group(1)),
                        },
                        output_dir=output_dir,
                    )
                )
        elif item_type == "table":
            ordinals[(page_number, "table")] += 1
            table_id = stable_record_id(
                paper_id, page_number, "table", ordinals[(page_number, "table")]
            )
            extractor_html = str(item.get("table_body") or "")
            raw_bbox = tuple(int(value) for value in item["bbox"])
            reviewed_table = REVIEWED_BY_KEY.get((paper_id, page_number, raw_bbox))
            html_body = (
                reviewed_table.replacement_html
                if reviewed_table and reviewed_table.replacement_html
                else extractor_html
            )
            parsed = parse_table_html(html_body)
            extractor_cells = {
                (cell.row, cell.column): cell for cell in parse_table_html(extractor_html)
            }
            if reviewed_table:
                actual_rows = max((cell.row for cell in parsed), default=-1) + 1
                actual_columns = max((cell.column + cell.column_span for cell in parsed), default=0)
                if (
                    actual_rows != reviewed_table.expected_rows
                    or actual_columns != reviewed_table.expected_columns
                    or len(parsed) != reviewed_table.expected_cell_count
                ):
                    raise ValueError(
                        f"reviewed table structure changed: {paper_id} p{page_number} {raw_bbox}"
                    )
            cell_records: list[dict[str, Any]] = []
            matching_assertions = [
                assertion
                for assertion in table_assertions
                if assertion["page_number"] == page_number
                and assertion.get("source_bbox_normalized") == [int(v) for v in item["bbox"]]
            ]
            assertion_by_coordinate = {
                (int(assertion["row_index"]), int(assertion["column_index"])): assertion
                for assertion in matching_assertions
            }
            correction_by_coordinate = {
                (row, column): (text, numeric)
                for row, column, text, numeric in (
                    reviewed_table.corrections if reviewed_table else ()
                )
            }
            for cell in parsed:
                assertion = assertion_by_coordinate.get((cell.row, cell.column))
                correction = correction_by_coordinate.get((cell.row, cell.column))
                reviewed_text = correction[0] if correction else cell.text
                numeric = (
                    float(assertion["expected_numeric"])
                    if assertion is not None
                    else correction[1]
                    if correction is not None
                    else parse_numeric(reviewed_text)
                )
                extractor_cell = extractor_cells.get((cell.row, cell.column))
                cell_records.append(
                    {
                        **TableCell(
                            row=cell.row,
                            column=cell.column,
                            raw_text=reviewed_text,
                            normalized_text=reviewed_text,
                            row_span=cell.row_span,
                            column_span=cell.column_span,
                            numeric_value=numeric,
                        ).to_dict(),
                        "cell_type": "header" if cell.tag == "th" else "data",
                        "verification_status": "verified" if reviewed_table else "unverified",
                        "assertion_id": assertion["assertion_id"] if assertion else None,
                        "extractor_raw_text": extractor_cell.text if extractor_cell else None,
                        "extractor_numeric_value": (
                            parse_numeric(extractor_cell.text) if extractor_cell else None
                        ),
                        "manual_correction": correction is not None or assertion is not None,
                    }
                )
            json_path, html_path, csv_path = _write_table_exports(
                output_dir, table_id, html_body, cell_records
            )
            record = TableRecord(
                table_id=table_id,
                paper_id=paper_id,
                page_number=page_number,
                bbox=bbox,
                source_asset=asset_path or "",
                cells=tuple(
                    TableCell(
                        row=cell["row"],
                        column=cell["column"],
                        raw_text=cell["raw_text"],
                        normalized_text=cell["normalized_text"],
                        row_span=cell["row_span"],
                        column_span=cell["column_span"],
                        numeric_value=cell["numeric_value"],
                    )
                    for cell in cell_records
                ),
                caption=normalize_text(" ".join(item.get("table_caption") or [])) or None,
                verification_status="verified" if reviewed_table else "unverified",
                provenance=provenance,
                csv_path=csv_path,
                html_path=html_path,
            ).to_dict()
            record.update(
                {
                    "json_path": json_path,
                    "source_block_id": block_id,
                    "source_bbox_normalized": list(raw_bbox),
                    "cells": cell_records,
                    "verified_cell_count": (
                        len(cell_records) if reviewed_table else len(matching_assertions)
                    ),
                    "numeric_validation_status": "verified" if reviewed_table else "not_run",
                    "render_overlay_status": (
                        "manual_review_pass" if reviewed_table else "not_run"
                    ),
                    "reviewer": reviewed_table.reviewer if reviewed_table else None,
                    "extractor_html_sha256": hashlib.sha256(
                        extractor_html.encode("utf-8")
                    ).hexdigest(),
                    "manual_structure_override": bool(
                        reviewed_table and reviewed_table.replacement_html
                    ),
                }
            )
            tables.append(record)
        elif item_type in {"image", "chart"}:
            ordinals[(page_number, "figure")] += 1
            figure_id = stable_record_id(
                paper_id, page_number, "figure", ordinals[(page_number, "figure")]
            )
            figures.append(
                {
                    "figure_id": figure_id,
                    "paper_id": paper_id,
                    "page_number": page_number,
                    "bbox": bbox.to_list(),
                    "source_bbox_normalized": [int(value) for value in item["bbox"]],
                    "source_asset": asset_path,
                    "source_block_id": block_id,
                    "caption": normalized_text or None,
                    "verification_status": "unverified",
                    "provenance": provenance.to_dict(),
                }
            )

    # Independently reviewed formulas are emitted as explicit overrides, never inferred
    # from extractor agreement. Multiple assertions may cite the same source crop.
    for assertion in equation_assertions:
        page_number = int(assertion["page_number"])
        profile = profiles[page_number]
        bbox = _assertion_bbox(assertion, float(profile["width"]), float(profile["height"]))
        raw_bbox = tuple(int(value) for value in assertion["source_bbox_normalized"])
        source_item = item_by_page_bbox.get((page_number, raw_bbox))
        if source_item is None:
            raise ValueError(
                f"verified assertion source region not found: {assertion['assertion_id']}"
            )
        source_name = Path(str(source_item["img_path"])).name
        if source_name != assertion.get("source_asset_name"):
            raise ValueError(
                f"verified assertion source asset changed: {assertion['assertion_id']}"
            )
        ordinals[(page_number, "equation")] += 1
        equation_id = stable_record_id(
            paper_id, page_number, "equation", ordinals[(page_number, "equation")]
        )
        source = mineru.asset_root / str(source_item["img_path"])
        asset_path = _copy_asset(source, output_dir, "equations", equation_id)
        latex = str(assertion["expected_latex"])
        equations.append(
            validate_equation_record(
                {
                    **EquationRecord(
                        equation_id=equation_id,
                        paper_id=paper_id,
                        page_number=page_number,
                        bbox=bbox,
                        source_asset=asset_path,
                        latex=latex,
                        equation_number=assertion.get("equation_number"),
                        verification_status="verified",
                        provenance=provenance,
                    ).to_dict(),
                    "equation_kind": "display",
                    "source_bbox_normalized": list(raw_bbox),
                    "latex_syntax_status": latex_syntax_status(latex),
                    "assertion_id": assertion["assertion_id"],
                    "reviewer": assertion["reviewer"],
                    "override_basis": "independent visual source-page review",
                },
                output_dir=output_dir,
            )
        )

    page_records = [pages[number] for number in sorted(pages)]
    by_block_id = {block["block_id"]: block for block in blocks}
    text_chars_by_page: dict[int, int] = defaultdict(int)
    for block in blocks:
        if block["block_type"] not in {"header", "footer"}:
            text_chars_by_page[int(block["page_number"])] += len(block["normalized_text"])
    low_text_pages = [
        page["page_number"]
        for page in page_records
        if int(profiles[page["page_number"]]["text_characters"]) >= 200
        and text_chars_by_page[page["page_number"]]
        < int(profiles[page["page_number"]]["text_characters"]) * 0.25
    ]
    markdown_parts = [f"# {paper_id}", ""]
    for page in page_records:
        markdown_parts.extend([f"<!-- page: {page['page_number']} -->", ""])
        for block_id in page["block_ids"]:
            block = by_block_id[block_id]
            if block["block_type"] in {"header", "footer"}:
                continue
            if block["block_type"] == "equation":
                markdown_parts.extend([block["raw_text"].strip(), ""])
            elif block["block_type"] == "table":
                markdown_parts.extend(
                    [
                        f"[Table source crop]({block['asset_path']})",
                        block["normalized_text"],
                        "",
                    ]
                )
            elif block["block_type"] == "figure":
                markdown_parts.extend([f"![{block['normalized_text']}]({block['asset_path']})", ""])
            elif block["normalized_text"]:
                prefix = "## " if block["block_type"] in {"title", "heading"} else ""
                markdown_parts.extend([prefix + block["normalized_text"], ""])

    symbol_counts: dict[str, int] = defaultdict(int)
    symbol_re = re.compile(r"\\[A-Za-z]+|(?<![A-Za-z])[A-Za-z](?![A-Za-z])")
    for equation in equations:
        for symbol in symbol_re.findall(str(equation.get("latex") or "")):
            symbol_counts[symbol] += 1
    symbols = [
        {
            "symbol": symbol,
            "occurrence_count": count,
            "definition": None,
            "verification_status": "unverified",
        }
        for symbol, count in sorted(symbol_counts.items())
    ]

    metadata = {
        "schema_version": "2.0.0",
        "paper_id": paper_id,
        "source_pdf": source_pdf.as_posix(),
        "source_pdf_sha256": source_sha256,
        "source_page_count": len(profiles),
        "converted_page_numbers": [page["page_number"] for page in page_records],
        "extractor": provenance.to_dict(),
        "input_content_list_sha256": hashlib.sha256(mineru.content_list.read_bytes()).hexdigest(),
    }
    for equation in equations:
        number = str(equation.get("equation_number") or "").strip()
        if not number:
            equation["referenced_by_block_ids"] = []
            continue
        reference = re.compile(rf"\(\s*{re.escape(number)}\s*\)")
        equation["referenced_by_block_ids"] = [
            block["block_id"]
            for block in blocks
            if block["block_id"] != equation.get("source_block_id")
            and reference.search(block["normalized_text"])
        ]
    quality = {
        "paper_id": paper_id,
        "text_status": "fail" if low_text_pages else "review",
        "layout_status": (
            "review"
            if any(page["reading_order_status"] == "review" for page in page_records)
            else "auto"
        ),
        "formula_status": (
            "fail"
            if any(
                eq["verification_status"] == "verified"
                and (
                    eq["latex_compile_status"] != "passed"
                    or eq["render_validation_status"] != "passed"
                )
                for eq in equations
            )
            else "review"
            if any(eq["verification_status"] != "verified" for eq in equations)
            else "pass"
        ),
        "table_status": (
            "pass"
            if not tables or all(table["verification_status"] == "verified" for table in tables)
            else "review"
        ),
        "claims_status": "missing",
        "retrieval_status": "missing",
        "overall_status": "missing",
        "counts": {
            "pages": len(page_records),
            "blocks": len(blocks),
            "display_equations": sum(eq["equation_kind"] == "display" for eq in equations),
            "inline_equations": sum(eq["equation_kind"] == "inline" for eq in equations),
            "verified_equations": sum(eq["verification_status"] == "verified" for eq in equations),
            "latex_equations": sum(eq.get("latex") is not None for eq in equations),
            "compiled_equations": sum(
                eq.get("latex") is not None and eq["latex_compile_status"] == "passed"
                for eq in equations
            ),
            "source_image_formula_fallbacks": sum(
                eq["representation_status"] == "source_image_fallback" for eq in equations
            ),
            "rendered_verified_equations": sum(
                eq["verification_status"] == "verified"
                and eq["render_validation_status"] == "passed"
                for eq in equations
            ),
            "tables": len(tables),
            "verified_table_cells": sum(table["verified_cell_count"] for table in tables),
            "figures": len(figures),
        },
        "low_text_coverage_pages": low_text_pages,
        "exceptions": [
            "Unverified LaTeX compiles to MathML but is not source-verified.",
            "Automatic table cells are unverified except explicit reviewed overrides.",
            "Claims and retrieval artifacts have not been generated.",
        ]
        + ([f"Low text coverage on source pages: {low_text_pages}."] if low_text_pages else []),
    }
    (output_dir / "metadata.json").write_text(_json(metadata), encoding="utf-8")
    (output_dir / "pages.jsonl").write_text(_jsonl(page_records), encoding="utf-8")
    (output_dir / "blocks.jsonl").write_text(_jsonl(blocks), encoding="utf-8")
    (output_dir / "equations.jsonl").write_text(_jsonl(equations), encoding="utf-8")
    (output_dir / "tables.jsonl").write_text(_jsonl(tables), encoding="utf-8")
    (output_dir / "figures.jsonl").write_text(_jsonl(figures), encoding="utf-8")
    (output_dir / "symbols.json").write_text(_json(symbols), encoding="utf-8")
    (output_dir / "paper.md").write_text(
        "\n".join(markdown_parts).rstrip() + "\n", encoding="utf-8"
    )
    (output_dir / "quality.json").write_text(_json(quality), encoding="utf-8")
    return {"metadata": metadata, "quality": quality}
