from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from jhrmbs.exceptions import SourceFormatError
from jhrmbs.sources.dates import parse_japanese_date, parse_japanese_month
from jhrmbs.util import normalize_text, safe_float

PARSER_VERSION = "jhf-factor-workbook-v1"


@dataclass(frozen=True)
class ParsedWorkbook:
    issues: pd.DataFrame
    panel: pd.DataFrame
    skipped_sheets: tuple[str, ...]


def canonical_header(value: object) -> str | None:
    header = normalize_text(value)
    if header == "債券年月":
        return "payment_month"
    if "当初予定ファクター" in header:
        return "scheduled_factor"
    if "ファクター(実績)" in header:
        return "actual_factor"
    if header.startswith("加重平均金利"):
        return "wac_pct"
    if header.startswith("加重平均残存年数"):
        return "wam_years"
    if header.startswith("任意繰上償還率"):
        return "voluntary_cpr_pct"
    if header.startswith("リスケジュールファクター"):
        return "rescheduled_factor"
    if header.startswith("加重平均経過期間"):
        return "wala_months"
    if "差替・一部解約率" in header and "長期延滞以外" in header:
        return "other_cancellation_pct_monthly"
    if "差替・一部解約率" in header and "長期延滞" in header:
        return "long_delinquency_pct_monthly"
    return None


def issue_identity(issue_name: str) -> tuple[str, str]:
    normalized = normalize_text(issue_name).upper()
    patterns = (
        (r"E55第(\d+)回", "JHF-E55-{number:02d}", "e55"),
        (r"グリーン第(\d+)回", "JHF-GREEN-{number:02d}", "green"),
        (r"T種第(\d+)回", "JHF-T-{number:02d}", "t"),
        (r"S種第(\d+)回", "JHF-S-{number:02d}", "s"),
        (r"第(\d+)回", "JHF-{number:03d}", "monthly"),
    )
    for pattern, template, series_type in patterns:
        match = re.search(pattern, normalized)
        if match:
            return template.format(number=int(match.group(1))), series_type
    raise SourceFormatError(f"回号を解釈できません: {issue_name}")


def _find_header_row(frame: pd.DataFrame) -> int | None:
    for index in range(min(len(frame), 20)):
        if normalize_text(frame.iat[index, 0]) == "債券年月":
            return index
    return None


def _metadata(frame: pd.DataFrame, header_row: int) -> dict[str, object]:
    result: dict[str, object] = {}
    for index in range(header_row):
        key = normalize_text(frame.iat[index, 0])
        if key and frame.shape[1] > 1:
            result[key] = frame.iat[index, 1]
    return result


def _row_value(frame: pd.DataFrame, row: int, column_map: dict[str, int], name: str) -> object:
    column = column_map.get(name)
    return frame.iat[row, column] if column is not None else None


def parse_jhf_workbook(
    path: Path,
    *,
    source_filename: str,
    source_sha256: str,
) -> ParsedWorkbook:
    engine: Literal["xlrd", "openpyxl"] = "xlrd" if path.suffix.lower() == ".xls" else "openpyxl"
    try:
        workbook = pd.ExcelFile(path, engine=engine)
    except Exception as exc:
        raise SourceFormatError(f"Excelを開けません: {source_filename}: {exc}") from exc

    issue_rows: list[dict[str, object]] = []
    panel_rows: list[dict[str, object]] = []
    skipped: list[str] = []
    for sheet_name in workbook.sheet_names:
        sheet_label = str(sheet_name)
        try:
            frame = pd.read_excel(workbook, sheet_name=sheet_name, header=None, dtype=object)
        except Exception as exc:
            raise SourceFormatError(
                f"sheetを読めません: {source_filename}/{sheet_label}: {exc}"
            ) from exc
        header_row = _find_header_row(frame)
        if header_row is None:
            skipped.append(sheet_label)
            continue
        metadata = _metadata(frame, header_row)
        issue_name = str(metadata.get("回号", sheet_label)).strip()
        issue_id, series_type = issue_identity(issue_name)
        face_amount = safe_float(metadata.get("発行額面額"))
        coupon_pct = safe_float(metadata.get("利率"))
        try:
            issue_date = parse_japanese_date(metadata.get("発行日"))
        except ValueError as exc:
            raise SourceFormatError(f"発行日を解釈できません: {issue_name}") from exc
        if face_amount is None or face_amount <= 0 or coupon_pct is None:
            raise SourceFormatError(f"発行メタデータが不足しています: {issue_name}")

        column_map: dict[str, int] = {}
        for column in range(frame.shape[1]):
            canonical = canonical_header(frame.iat[header_row, column])
            if canonical:
                column_map[canonical] = column
        required = {"payment_month", "scheduled_factor", "actual_factor"}
        if not required.issubset(column_map):
            missing = ", ".join(sorted(required - column_map.keys()))
            raise SourceFormatError(f"必須列がありません: {issue_name}: {missing}")

        initial: dict[str, float | None] = {}
        for row in range(header_row + 1, len(frame)):
            raw_month = _row_value(frame, row, column_map, "payment_month")
            if normalize_text(raw_month) == "発行時":
                for name in (
                    "scheduled_factor",
                    "actual_factor",
                    "wac_pct",
                    "wam_years",
                    "wala_months",
                ):
                    initial[name] = safe_float(_row_value(frame, row, column_map, name))
                break

        issue_rows.append(
            {
                "issue_id": issue_id,
                "issue_name": issue_name,
                "series_type": series_type,
                "issue_date": issue_date,
                "vintage_year": int(issue_date.year),
                "face_amount_jpy": face_amount,
                "coupon_pct": coupon_pct,
                "initial_wac_pct": initial.get("wac_pct"),
                "initial_wam_years": initial.get("wam_years"),
                "initial_wala_months": initial.get("wala_months"),
                "source_filename": source_filename,
                "source_sha256": source_sha256,
                "parser_version": PARSER_VERSION,
            }
        )

        for row in range(header_row + 1, len(frame)):
            raw_month = _row_value(frame, row, column_map, "payment_month")
            if normalize_text(raw_month) in {"", "発行時"}:
                continue
            scheduled_factor = safe_float(_row_value(frame, row, column_map, "scheduled_factor"))
            if scheduled_factor is None:
                continue
            try:
                payment_month = parse_japanese_month(raw_month)
            except ValueError:
                continue
            values = {
                name: safe_float(_row_value(frame, row, column_map, name))
                for name in (
                    "actual_factor",
                    "wac_pct",
                    "wam_years",
                    "voluntary_cpr_pct",
                    "rescheduled_factor",
                    "wala_months",
                    "long_delinquency_pct_monthly",
                    "other_cancellation_pct_monthly",
                )
            }
            panel_rows.append(
                {
                    "issue_id": issue_id,
                    "issue_name": issue_name,
                    "series_type": series_type,
                    "issue_date": issue_date,
                    "vintage_year": int(issue_date.year),
                    "face_amount_jpy": face_amount,
                    "coupon_pct": coupon_pct,
                    "payment_month": payment_month,
                    "scheduled_factor": scheduled_factor,
                    **values,
                    "source_filename": source_filename,
                    "source_sha256": source_sha256,
                    "parser_version": PARSER_VERSION,
                }
            )

    return ParsedWorkbook(
        issues=pd.DataFrame(issue_rows),
        panel=pd.DataFrame(panel_rows),
        skipped_sheets=tuple(skipped),
    )
