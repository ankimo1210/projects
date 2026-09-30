"""Stream read-only XLSX cells needed by public statistical workbooks."""

from __future__ import annotations

import io
import posixpath
from collections.abc import Iterator
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
from zipfile import BadZipFile, ZipFile

MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def excel_date(value: str) -> str:
    """Return ISO date for Excel's standard 1900 date system."""
    try:
        return (datetime(1899, 12, 30) + timedelta(days=float(value))).date().isoformat()
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"Invalid Excel date: {value}") from exc


def xlsx_rows(payload: bytes, sheet_name: str) -> Iterator[tuple[int, dict[str, str]]]:
    """Yield sparse worksheet rows without loading a large sheet XML into memory."""
    try:
        with ZipFile(io.BytesIO(payload)) as archive:
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheets = workbook.find(MAIN + "sheets")
            match = (
                next((s for s in sheets if s.get("name") == sheet_name), None)
                if sheets is not None
                else None
            )
            if match is None:
                raise ValueError(f"XLSX sheet not found: {sheet_name}")
            rel_id = match.get(REL + "id")
            relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relation = next((r for r in relationships if r.get("Id") == rel_id), None)
            if relation is None:
                raise ValueError(f"XLSX sheet relationship not found: {sheet_name}")
            target = relation.get("Target", "")
            sheet_path = (
                target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
            )
            if not sheet_path.startswith("xl/worksheets/"):
                raise ValueError(f"Unexpected XLSX sheet path: {sheet_path}")
            try:
                shared_xml = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                strings = [
                    "".join(t.text or "" for t in item.iter(MAIN + "t")) for item in shared_xml
                ]
            except KeyError:
                strings = []
            with archive.open(sheet_path) as stream:
                events = ET.iterparse(stream, events=("start", "end"))
                _, root = next(events)
                for event, element in events:
                    if event != "end" or element.tag != MAIN + "row":
                        continue
                    fields: dict[str, str] = {}
                    for cell in element:
                        if cell.tag != MAIN + "c":
                            continue
                        column = "".join(char for char in cell.get("r", "") if char.isalpha())
                        value = cell.find(MAIN + "v")
                        if value is not None and value.text is not None:
                            text = value.text
                            if cell.get("t") == "s":
                                text = strings[int(text)]
                        else:
                            text = "".join(t.text or "" for t in cell.iter(MAIN + "t"))
                        fields[column] = text
                    yield int(element.get("r", "0")), fields
                    root.clear()
    except (BadZipFile, KeyError, ET.ParseError) as exc:
        raise ValueError("Invalid XLSX workbook") from exc
