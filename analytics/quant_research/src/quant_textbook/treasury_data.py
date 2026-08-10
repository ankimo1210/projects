"""Point-in-time-aware helpers for the official U.S. Treasury yield snapshot.

The bundled dataset contains daily par yield curve rates, expressed in percent.
It is a factual snapshot for reproducible textbook experiments, not transaction
data, a zero-coupon curve, or an executable market quote.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from typing import Final
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

TREASURY_XML_URL: Final = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value={year}"
)
TREASURY_METHOD_BREAK: Final = pd.Timestamp("2021-12-06")
DEFAULT_TENORS: Final = ("3m", "2y", "5y", "10y", "30y")
_XML_FIELDS: Final = {
    "BC_3MONTH": "3m",
    "BC_2YEAR": "2y",
    "BC_5YEAR": "5y",
    "BC_10YEAR": "10y",
    "BC_30YEAR": "30y",
}
_XML_NAMESPACES: Final = {
    "atom": "http://www.w3.org/2005/Atom",
    "metadata": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
}


@dataclass(frozen=True)
class TreasurySnapshotMetadata:
    """Provenance and interpretation contract for a frozen data snapshot."""

    source_name: str
    source_page: str
    source_feed_template: str
    source_terms_pages: tuple[str, ...]
    terms_reviewed_at: str
    redistribution_decision: str
    retrieval_user_agent: str
    retrieved_at_utc: str
    start_date: str
    end_date: str
    row_count: int
    tenors: tuple[str, ...]
    value_unit: str
    quote_convention: str
    observation_contract: str
    availability_contract: str
    methodology_break_date: str
    snapshot_sha256: str


@dataclass(frozen=True)
class TreasuryDataQuality:
    """High-signal quality diagnostics at the date-by-tenor grain."""

    row_count: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    duplicate_dates: int
    missing_by_tenor: dict[str, int]
    nonfinite_by_tenor: dict[str, int]
    maximum_calendar_gap_days: int
    methodology_break_present: bool
    accepted: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class TreasuryDataset:
    """Bundled yield observations and their immutable metadata."""

    frame: pd.DataFrame
    metadata: TreasurySnapshotMetadata
    quality: TreasuryDataQuality


def _resource_path(name: str) -> Path:
    resource = files("quant_textbook").joinpath("resources", name)
    return Path(str(resource))


def parse_treasury_xml(xml_bytes: bytes) -> pd.DataFrame:
    """Parse one official Atom/XML response into a date-by-tenor frame."""
    if not isinstance(xml_bytes, bytes) or not xml_bytes:
        raise ValueError("xml_bytes must be non-empty bytes")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as error:
        raise ValueError("Treasury XML is not well formed") from error

    rows: list[dict[str, object]] = []
    for entry in root.findall("atom:entry", _XML_NAMESPACES):
        properties = entry.find("atom:content/metadata:properties", _XML_NAMESPACES)
        if properties is None:
            continue
        row: dict[str, object] = {}
        for element in properties:
            field = element.tag.rsplit("}", 1)[-1]
            if field == "NEW_DATE" and element.text:
                row["date"] = element.text[:10]
            elif field in _XML_FIELDS:
                row[_XML_FIELDS[field]] = (
                    float(element.text) if element.text not in (None, "") else np.nan
                )
        if "date" in row:
            rows.append(row)

    if not rows:
        raise ValueError("Treasury XML contains no dated observations")
    frame = pd.DataFrame(rows)
    for tenor in DEFAULT_TENORS:
        if tenor not in frame:
            frame[tenor] = np.nan
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    frame = frame.loc[:, ["date", *DEFAULT_TENORS]]
    # Some historical feeds contain holiday entries with only display fields,
    # notably BC_30YEARDISPLAY="0.00".  Display fields are deliberately not
    # mapped above, and an entry with no actual tenor observation is not a
    # market-data row.
    frame = frame.loc[frame.loc[:, DEFAULT_TENORS].notna().any(axis=1)]
    if frame.empty:
        raise ValueError("Treasury XML contains no usable tenor observations")
    return frame.sort_values("date").reset_index(drop=True)


def fetch_treasury_year(
    year: int,
    *,
    user_agent: str = "quant-research-textbook/0.1 (educational data audit)",
    timeout_seconds: float = 60.0,
) -> tuple[bytes, pd.DataFrame]:
    """Fetch one year from the official XML feed with bounded network use."""
    if isinstance(year, bool) or not isinstance(year, int) or not 1990 <= year <= 2100:
        raise ValueError("year must be an integer between 1990 and 2100")
    if not isinstance(user_agent, str) or not user_agent.strip():
        raise ValueError("user_agent must be a non-empty string")
    if not np.isfinite(timeout_seconds) or timeout_seconds <= 0.0:
        raise ValueError("timeout_seconds must be strictly positive")

    request = Request(
        TREASURY_XML_URL.format(year=year),
        headers={"User-Agent": user_agent.strip()},
    )
    with urlopen(request, timeout=float(timeout_seconds)) as response:
        payload = response.read()
    return payload, parse_treasury_xml(payload)


def audit_treasury_data(
    frame: pd.DataFrame,
    *,
    required_tenors: tuple[str, ...] = DEFAULT_TENORS,
    allow_missing: bool = False,
) -> TreasuryDataQuality:
    """Validate the snapshot at its intended date-by-tenor analytical grain."""
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("frame must be a pandas DataFrame")
    if "date" not in frame:
        raise ValueError("frame must contain a date column")
    if not required_tenors or len(set(required_tenors)) != len(required_tenors):
        raise ValueError("required_tenors must be non-empty and unique")
    missing_columns = [tenor for tenor in required_tenors if tenor not in frame]
    if missing_columns:
        raise ValueError(f"missing required tenor columns: {missing_columns}")
    if frame.empty:
        raise ValueError("frame must contain at least one observation")

    dates = pd.to_datetime(frame["date"], errors="raise")
    duplicate_dates = int(dates.duplicated().sum())
    ordered_dates = dates.sort_values().reset_index(drop=True)
    maximum_gap = int(ordered_dates.diff().dt.days.fillna(0).max())

    missing_by_tenor: dict[str, int] = {}
    nonfinite_by_tenor: dict[str, int] = {}
    for tenor in required_tenors:
        numeric = pd.to_numeric(frame[tenor], errors="coerce").to_numpy(dtype=float)
        missing_by_tenor[tenor] = int(np.isnan(numeric).sum())
        nonfinite_by_tenor[tenor] = int((~np.isfinite(numeric) & ~np.isnan(numeric)).sum())

    warnings: list[str] = []
    if (
        TREASURY_METHOD_BREAK >= ordered_dates.min()
        and TREASURY_METHOD_BREAK <= ordered_dates.max()
    ):
        warnings.append(
            "official curve methodology changes from HS to monotone convex on 2021-12-06"
        )
    if maximum_gap > 5:
        warnings.append("calendar gap above five days requires a market-calendar audit")

    missing_total = sum(missing_by_tenor.values())
    nonfinite_total = sum(nonfinite_by_tenor.values())
    accepted = bool(
        duplicate_dates == 0
        and nonfinite_total == 0
        and (allow_missing or missing_total == 0)
        and dates.is_monotonic_increasing
    )
    return TreasuryDataQuality(
        row_count=len(frame),
        start_date=ordered_dates.iloc[0],
        end_date=ordered_dates.iloc[-1],
        duplicate_dates=duplicate_dates,
        missing_by_tenor=missing_by_tenor,
        nonfinite_by_tenor=nonfinite_by_tenor,
        maximum_calendar_gap_days=maximum_gap,
        methodology_break_present=bool(
            TREASURY_METHOD_BREAK >= ordered_dates.min()
            and TREASURY_METHOD_BREAK <= ordered_dates.max()
        ),
        accepted=accepted,
        warnings=tuple(warnings),
    )


def load_treasury_snapshot() -> TreasuryDataset:
    """Load the bundled 2015--2025 snapshot without a network dependency."""
    snapshot_path = _resource_path("treasury_yields_2015_2025.json")
    manifest_path = _resource_path("treasury_yields_2015_2025.manifest.json")
    if not snapshot_path.exists() or not manifest_path.exists():
        raise FileNotFoundError(
            "bundled Treasury snapshot is missing; run tools/fetch_treasury_snapshot.py"
        )

    snapshot_bytes = snapshot_path.read_bytes()
    payload = json.loads(snapshot_bytes)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_hash = sha256(snapshot_bytes).hexdigest()
    if actual_hash != manifest["snapshot_sha256"]:
        raise ValueError("Treasury snapshot hash does not match its manifest")

    frame = pd.DataFrame(payload["data"], columns=payload["columns"])
    frame["date"] = pd.to_datetime(frame["date"], errors="raise")
    for tenor in manifest["tenors"]:
        frame[tenor] = pd.to_numeric(frame[tenor], errors="raise")
    quality = audit_treasury_data(frame, required_tenors=tuple(manifest["tenors"]))
    if not quality.accepted:
        raise ValueError("bundled Treasury snapshot failed its quality contract")

    metadata = TreasurySnapshotMetadata(
        source_name=manifest["source_name"],
        source_page=manifest["source_page"],
        source_feed_template=manifest["source_feed_template"],
        source_terms_pages=tuple(manifest["source_terms_pages"]),
        terms_reviewed_at=manifest["terms_reviewed_at"],
        redistribution_decision=manifest["redistribution_decision"],
        retrieval_user_agent=manifest["retrieval_user_agent"],
        retrieved_at_utc=manifest["retrieved_at_utc"],
        start_date=manifest["start_date"],
        end_date=manifest["end_date"],
        row_count=int(manifest["row_count"]),
        tenors=tuple(manifest["tenors"]),
        value_unit=manifest["value_unit"],
        quote_convention=manifest["quote_convention"],
        observation_contract=manifest["observation_contract"],
        availability_contract=manifest["availability_contract"],
        methodology_break_date=manifest["methodology_break_date"],
        snapshot_sha256=manifest["snapshot_sha256"],
    )
    if metadata.row_count != len(frame):
        raise ValueError("Treasury snapshot row count does not match its manifest")
    return TreasuryDataset(frame=frame.copy(), metadata=metadata, quality=quality)


__all__ = [
    "DEFAULT_TENORS",
    "TREASURY_METHOD_BREAK",
    "TREASURY_XML_URL",
    "TreasuryDataQuality",
    "TreasuryDataset",
    "TreasurySnapshotMetadata",
    "audit_treasury_data",
    "fetch_treasury_year",
    "load_treasury_snapshot",
    "parse_treasury_xml",
]
