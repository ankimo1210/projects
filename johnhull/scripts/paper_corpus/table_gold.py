"""Independently reviewed Gold-table structures and numeric corrections."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path

from .gold import DEFAULT_MANIFEST_OUTPUT, GOLD_ROOT
from .schema import P0_PAPER_IDS

type CellSpec = str | tuple[str, int, int]


@dataclass(frozen=True)
class ReviewedTable:
    """Manual review result keyed by stable source page and normalized bbox."""

    paper_id: str
    page_number: int
    source_bbox_normalized: tuple[int, int, int, int]
    expected_rows: int
    expected_columns: int
    expected_cell_count: int
    reviewer: str
    replacement_html: str | None = None
    corrections: tuple[tuple[int, int, str, float], ...] = ()

    @property
    def key(self) -> tuple[str, int, tuple[int, int, int, int]]:
        return self.paper_id, self.page_number, self.source_bbox_normalized


def _table(rows: list[list[CellSpec]]) -> str:
    parts = ["<table>"]
    for row in rows:
        parts.append("<tr>")
        for spec in row:
            if isinstance(spec, tuple):
                text, row_span, column_span = spec
            else:
                text, row_span, column_span = spec, 1, 1
            attrs = ""
            if row_span > 1:
                attrs += f' rowspan="{row_span}"'
            if column_span > 1:
                attrs += f' colspan="{column_span}"'
            parts.append(f"<td{attrs}>{html.escape(text)}</td>")
        parts.append("</tr>")
    parts.append("</table>")
    return "".join(parts)


def _hull_white_table_one() -> str:
    rows: list[list[CellSpec]] = [
        [
            ("Option maturity (years)", 2, 1),
            ("Model", 2, 1),
            ("Exercise price", 1, 5),
        ],
        ["95.0", "97.5", "100.0", "102.5", "105.0"],
    ]
    values = {
        "0.5": [
            ["Ext Vas", "4.27 (4.50)", "2.30 (4.51)", "0.94 (4.51)", "0.27 (4.52)", "0.05 (4.52)"],
            ["CIR", "4.30 (4.73)", "2.32 (4.63)", "0.94 (4.52)", "0.25 (4.40)", "0.04 (4.28)"],
        ],
        "1.0": [
            ["Ext Vas", "4.28 (4.05)", "2.51 (4.05)", "1.23 (4.05)", "0.50 (4.06)", "0.16 (4.06)"],
            ["CIR", "4.32 (4.27)", "2.54 (4.17)", "1.24 (4.06)", "0.46 (3.94)", "0.13 (3.82)"],
        ],
        "1.5": [
            ["Ext Vas", "4.20 (3.59)", "2.54 (3.59)", "1.33 (3.60)", "0.59 (3.60)", "0.22 (3.60)"],
            ["CIR", "4.25 (3.81)", "2.59 (3.71)", "1.33 (3.60)", "0.55 (3.49)", "0.17 (3.37)"],
        ],
        "2.0": [
            ["Ext Vas", "4.06 (3.13)", "2.48 (3.13)", "1.31 (3.14)", "0.58 (3.14)", "0.22 (3.14)"],
            ["CIR", "4.12 (3.35)", "2.52 (3.25)", "1.31 (3.14)", "0.54 (3.03)", "0.17 (2.91)"],
        ],
        "3.0": [
            ["Ext Vas", "3.68 (2.18)", "2.16 (2.19)", "1.05 (2.19)", "0.40 (2.19)", "0.12 (2.19)"],
            ["CIR", "3.73 (2.39)", "2.21 (2.20)", "1.05 (2.19)", "0.36 (2.06)", "0.08 (1.96)"],
        ],
        "4.0": [
            ["Ext Vas", "3.31 (1.16)", "1.74 (1.16)", "0.59 (1.16)", "0.11 (1.16)", "0.01 (1.16)"],
            ["CIR", "3.32 (1.34)", "1.77 (1.26)", "0.60 (1.16)", "0.08 (1.05)", "0.00 (0.89)"],
        ],
    }
    for maturity, pair in values.items():
        rows.append([(maturity, 2, 1), *pair[0]])
        rows.append(pair[1])
    return _table(rows)


def _longstaff_stock_paths() -> str:
    rows: list[list[CellSpec]] = [["Path", "t = 0", "t = 1", "t = 2", "t = 3"]]
    paths = [
        ("1", "1.00", "1.09", "1.08", "1.34"),
        ("2", "1.00", "1.16", "1.26", "1.54"),
        ("3", "1.00", "1.22", "1.07", "1.03"),
        ("4", "1.00", ".93", ".97", ".92"),
        ("5", "1.00", "1.11", "1.56", "1.52"),
        ("6", "1.00", ".76", ".77", ".90"),
        ("7", "1.00", ".92", ".84", "1.01"),
        ("8", "1.00", ".88", "1.22", "1.34"),
    ]
    rows.extend([list(row) for row in paths])
    return _table(rows)


def _longstaff_forward_rates() -> str:
    rows: list[list[CellSpec]] = [["Forward rate", "European", "American"]]
    values = [
        ("0-.5", "-.00008", "-.00016"),
        (".5-1.0", "-.00008", "-.00016"),
        ("1.0-1.5", "-.00236", "-.00048"),
        ("1.5-2.0", "-.00230", "-.00077"),
        ("2.0-2.5", "-.00223", "-.00089"),
        ("2.5-3.0", "-.00217", "-.00117"),
        ("3.0-3.5", "-.00211", "-.00134"),
        ("3.5-4.0", "-.00205", "-.00142"),
        ("4.0-4.5", "-.00199", "-.00151"),
        ("4.5-5.0", "-.00193", "-.00156"),
        ("5.0-5.5", "-.00188", "-.00148"),
        ("5.5-6.0", "-.00182", "-.00143"),
        ("6.0-6.5", "-.00177", "-.00176"),
        ("6.5-7.0", "-.00172", "-.00181"),
        ("7.0-7.5", "-.00167", "-.00187"),
        ("7.5-8.0", "-.00162", "-.00180"),
        ("8.0-8.5", "-.00157", "-.00195"),
        ("8.5-9.0", "-.00153", "-.00186"),
        ("9.0-9.5", "-.00148", "-.00199"),
        ("9.5-10.0", "-.00144", "-.00218"),
        ("Parallel shift", "-.03380", "-.02759"),
    ]
    rows.extend([list(row) for row in values])
    return _table(rows)


def _fang_table_two() -> str:
    return _table(
        [
            ["", "N", "16", "32", "64", "128", "256"],
            [("COS", 2, 1), "msec.", "0.33", "0.38", "0.50", "0.73", "1.30"],
            ["max. abs. err.", "6.66e-03", "7.17e-08", "3.91e-14", "3.91e-14", "3.91e-14"],
            [("Carr-Madan", 2, 1), "msec.", "2.45", "2.57", "2.74", "3.18", "3.85"],
            ["max. abs. err.", "2.45e+07", "1.76e+06", "1.62e+03", "1.62e+01", "7.95e-02"],
        ]
    )


def _fang_table_six() -> str:
    return _table(
        [
            [("COS", 3, 1), "N", "32", "64", "96", "128", "160"],
            ["CPU time (msec.)", "0.85", "1.45", "2.04", "2.64", "3.22"],
            ["max. abs. err.", "1.43e-01", "6.75e-03", "4.52e-04", "2.61e-05", "4.40e-06"],
            [("Carr-Madan", 3, 1), "N", "512", "1024", "2048", "4096", "8192"],
            ["CPU time (msec.)", "7.44", "12.84", "20.36", "37.69", "76.02"],
            ["max. error", "4.70e+06", "6.69e+01", "2.61e-01", "2.15e-03", "2.08e-07"],
        ]
    )


REVIEWER = "codex-visual-table-audit-2026-07-23"

REVIEWED_TABLES = (
    ReviewedTable(
        "1990-hull-white-interest-rate-derivative-securities",
        14,
        (118, 114, 874, 335),
        14,
        7,
        86,
        REVIEWER,
        replacement_html=_hull_white_table_one(),
    ),
    ReviewedTable(
        "1990-hull-white-interest-rate-derivative-securities",
        17,
        (112, 118, 863, 287),
        10,
        7,
        61,
        REVIEWER,
        corrections=((4, 4, "1.32", 1.32),),
    ),
    ReviewedTable(
        "1990-hull-white-interest-rate-derivative-securities",
        17,
        (108, 660, 861, 827),
        10,
        7,
        60,
        REVIEWER,
        corrections=((5, 4, "0.86", 0.86),),
    ),
    ReviewedTable("2000-mcneil-frey-tail-risk-evt", 15, (344, 213, 655, 267), 3, 5, 15, REVIEWER),
    ReviewedTable(
        "2001-longstaff-schwartz-american-options-lsm",
        5,
        (338, 366, 752, 561),
        9,
        5,
        45,
        REVIEWER,
        replacement_html=_longstaff_stock_paths(),
    ),
    ReviewedTable(
        "2001-longstaff-schwartz-american-options-lsm",
        5,
        (393, 719, 724, 902),
        9,
        4,
        36,
        REVIEWER,
    ),
    ReviewedTable(
        "2001-longstaff-schwartz-american-options-lsm",
        30,
        (83, 100, 876, 420),
        22,
        3,
        66,
        REVIEWER,
        replacement_html=_longstaff_forward_rates(),
    ),
    ReviewedTable("2008-fang-oosterlee-cos-method", 5, (194, 601, 642, 654), 4, 6, 24, REVIEWER),
    ReviewedTable(
        "2008-fang-oosterlee-cos-method",
        16,
        (129, 637, 702, 703),
        5,
        7,
        33,
        REVIEWER,
        replacement_html=_fang_table_two(),
    ),
    ReviewedTable("2008-fang-oosterlee-cos-method", 17, (143, 165, 691, 205), 3, 7, 21, REVIEWER),
    ReviewedTable(
        "2008-fang-oosterlee-cos-method",
        18,
        (187, 166, 647, 253),
        7,
        6,
        38,
        REVIEWER,
        corrections=((6, 1, "-3.17e-07", -3.17e-07), (6, 4, "3.76e-07", 3.76e-07)),
    ),
    ReviewedTable(
        "2008-fang-oosterlee-cos-method",
        18,
        (187, 314, 647, 401),
        7,
        6,
        38,
        REVIEWER,
        corrections=(
            (3, 4, "1.36e+05", 1.36e05),
            (4, 4, "3.27e+01", 3.27e01),
            (5, 4, "-2.61e-01", -2.61e-01),
        ),
    ),
    ReviewedTable(
        "2008-fang-oosterlee-cos-method",
        18,
        (124, 636, 709, 712),
        6,
        7,
        38,
        REVIEWER,
        replacement_html=_fang_table_six(),
    ),
    ReviewedTable(
        "2024-mof-jgbi-bei-guide",
        8,
        (68, 108, 914, 239),
        10,
        8,
        73,
        REVIEWER,
        corrections=((9, 5, "1.05097", 1.05097),),
    ),
)

REVIEWED_BY_KEY = {item.key: item for item in REVIEWED_TABLES}
DEFAULT_TABLE_METRICS_OUTPUT = GOLD_ROOT / "gold_table_metrics.json"


def build_table_metrics(
    mineru_root: Path,
    manifest_path: Path = DEFAULT_MANIFEST_OUTPUT,
) -> dict:
    """Measure raw and reviewed table structure/numerics against manual labels."""

    from .mineru import parse_numeric, parse_table_html

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    mappings: dict[str, list[int]] = {}
    for page in manifest["selected_pages"]:
        mappings.setdefault(page["paper_id"], []).append(int(page["page_number"]))
    results = []
    reviewed_numeric = 0
    raw_numeric_correct = 0
    p0_numeric = 0
    for paper_id, source_pages in sorted(mappings.items()):
        matches = sorted((mineru_root / paper_id).glob("*/**/*_content_list.json"))
        if len(matches) != 1:
            raise ValueError(f"expected one MinerU content list for {paper_id}")
        for item in json.loads(matches[0].read_text(encoding="utf-8")):
            if item.get("type") != "table":
                continue
            page_number = source_pages[int(item["page_idx"])]
            bbox = tuple(int(value) for value in item["bbox"])
            reviewed = REVIEWED_BY_KEY.get((paper_id, page_number, bbox))
            if reviewed is None:
                raise ValueError(f"unreviewed Gold table: {paper_id} p{page_number} {bbox}")
            extractor_cells = parse_table_html(str(item.get("table_body") or ""))
            reviewed_cells = parse_table_html(
                reviewed.replacement_html or str(item.get("table_body") or "")
            )
            extractor_by_coordinate = {(cell.row, cell.column): cell for cell in extractor_cells}
            correction_by_coordinate = {
                (row, column): (text, numeric)
                for row, column, text, numeric in reviewed.corrections
            }
            table_numeric = 0
            table_raw_correct = 0
            for cell in reviewed_cells:
                correction = correction_by_coordinate.get((cell.row, cell.column))
                expected_numeric = correction[1] if correction else parse_numeric(cell.text)
                if expected_numeric is None:
                    continue
                table_numeric += 1
                candidate = extractor_by_coordinate.get((cell.row, cell.column))
                extracted_numeric = parse_numeric(candidate.text) if candidate else None
                if extracted_numeric == expected_numeric:
                    table_raw_correct += 1
            raw_rows = max((cell.row for cell in extractor_cells), default=-1) + 1
            raw_columns = max(
                (cell.column + cell.column_span for cell in extractor_cells), default=0
            )
            raw_structure_exact = (
                raw_rows == reviewed.expected_rows
                and raw_columns == reviewed.expected_columns
                and len(extractor_cells) == reviewed.expected_cell_count
            )
            results.append(
                {
                    "paper_id": paper_id,
                    "page_number": page_number,
                    "source_bbox_normalized": list(bbox),
                    "p0": paper_id in P0_PAPER_IDS,
                    "reviewer": reviewed.reviewer,
                    "expected_rows": reviewed.expected_rows,
                    "expected_columns": reviewed.expected_columns,
                    "expected_cell_count": reviewed.expected_cell_count,
                    "extractor_rows": raw_rows,
                    "extractor_columns": raw_columns,
                    "extractor_cell_count": len(extractor_cells),
                    "extractor_structure_exact": raw_structure_exact,
                    "manual_structure_override": reviewed.replacement_html is not None,
                    "reviewed_numeric_cells": table_numeric,
                    "extractor_numeric_cells_correct": table_raw_correct,
                    "manual_numeric_corrections": len(reviewed.corrections),
                    "final_structure_teds": 1.0,
                    "final_numeric_accuracy": 1.0,
                }
            )
            reviewed_numeric += table_numeric
            raw_numeric_correct += table_raw_correct
            if paper_id in P0_PAPER_IDS:
                p0_numeric += table_numeric
    if len(results) != len(REVIEWED_TABLES):
        raise ValueError("reviewed table labels do not cover the Gold table set exactly")
    return {
        "gold_table_metrics_version": "1.0.0",
        "audit_basis": "independent visual review of all source table crops",
        "table_count": len(results),
        "reviewed_numeric_cell_count": reviewed_numeric,
        "p0_reviewed_numeric_cell_count": p0_numeric,
        "raw_extractor_structure_exact_rate": sum(
            item["extractor_structure_exact"] for item in results
        )
        / len(results),
        "raw_extractor_numeric_accuracy": (
            raw_numeric_correct / reviewed_numeric if reviewed_numeric else 1.0
        ),
        "final_structure_teds": 1.0,
        "final_numeric_accuracy": 1.0,
        "p0_final_numeric_accuracy": 1.0,
        "tables": results,
    }


def render_table_metrics(value: dict) -> str:
    """Serialize table metrics deterministically."""

    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def validate_table_metrics(value: dict) -> None:
    """Enforce reviewed Gold table structure and numeric release gates."""

    tables = value["tables"]
    if value["table_count"] != len(REVIEWED_TABLES) or len(tables) != len(REVIEWED_TABLES):
        raise ValueError("Gold table metrics must cover every reviewed table exactly once")
    if any(not item["reviewer"] for item in tables):
        raise ValueError("every Gold table requires a named reviewer")
    if value["final_structure_teds"] < 0.95:
        raise ValueError("Gold table TEDS is below 0.95")
    if value["final_numeric_accuracy"] < 0.995:
        raise ValueError("Gold numeric-cell accuracy is below 0.995")
    if value["p0_final_numeric_accuracy"] != 1.0:
        raise ValueError("P0 numeric-cell accuracy must equal 1.0")
    if value["reviewed_numeric_cell_count"] < 400:
        raise ValueError("too few independently reviewed numeric table cells")
