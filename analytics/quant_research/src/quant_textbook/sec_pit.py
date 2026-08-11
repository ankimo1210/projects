"""Small, strict helpers for SEC point-in-time fundamentals research.

The helpers in this module deliberately do not download SEC responses or keep
raw filings.  A caller supplies the ``recent`` table and any historical
``filings.files`` tables, then receives deterministic, point-in-time records.
Missing accession metadata is an error: falling back to ``filed`` silently
would make availability look earlier than the information set used by B9.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from math import isfinite, sqrt
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

ALLOWED_FILING_FORMS = frozenset({"10-K", "10-Q", "10-K/A", "10-Q/A"})
"""Forms admitted by the B9 fundamentals contract."""

_EASTERN = ZoneInfo("America/New_York")


class UnresolvedAccessionError(ValueError):
    """Raised when a fact cannot be joined to a filing record."""

    def __init__(self, accessions: Iterable[str]) -> None:
        normalized = tuple(sorted(set(accessions)))
        self.accessions = normalized
        super().__init__(
            "SEC accession metadata is missing; fetch filings.files archives "
            f"before building a PIT panel: {normalized}"
        )


@dataclass(frozen=True)
class FilingRecord:
    """The filing metadata needed to define an observable date."""

    accession_number: str
    cik: int
    form: str
    filing_date: date
    acceptance_datetime: datetime

    def __post_init__(self) -> None:
        if not self.accession_number:
            raise ValueError("accession_number must be non-empty")
        if self.cik <= 0:
            raise ValueError("cik must be positive")
        if not self.form.strip():
            raise ValueError("form must be non-empty")
        if self.acceptance_datetime.tzinfo is None:
            raise ValueError("acceptance_datetime must be timezone-aware")

    def availability_date(
        self,
        *,
        holiday_dates: Iterable[date] | None = None,
    ) -> date:
        """Return the conservative next-business-day availability date.

        ``filingDate`` and the Eastern-calendar date of ``acceptanceDateTime``
        are both retained; the later date is advanced by one U.S. federal
        business day.  ``holiday_dates`` can be supplied from a locked holiday
        manifest.  When omitted, pandas' USFederalHolidayCalendar is used.
        """

        acceptance_date = self.acceptance_datetime.astimezone(_EASTERN).date()
        return next_us_business_day(
            max(self.filing_date, acceptance_date), holiday_dates=holiday_dates
        )


@dataclass(frozen=True)
class FundamentalsErrorMetrics:
    """Metrics fixed by the B9 contract, with sample size included."""

    n: int
    mae: float
    median_absolute_error: float
    rmse: float


@dataclass(frozen=True)
class PITUniverseSpec:
    """An anchored cohort specification that cannot use a current Frame."""

    anchor_period_end: date
    anchor_as_of: date
    analysis_start: date
    minimum_assets_usd: float = 100_000_000.0

    def __post_init__(self) -> None:
        if self.analysis_start < self.anchor_as_of:
            raise ValueError("analysis_start must be on or after anchor_as_of")
        if self.minimum_assets_usd <= 0.0 or not isfinite(self.minimum_assets_usd):
            raise ValueError("minimum_assets_usd must be finite and positive")


@dataclass(frozen=True)
class PITUniverseSelection:
    """Auditable output of a fixed, point-in-time cohort selection."""

    spec: PITUniverseSpec
    eligible_ciks: tuple[int, ...]
    candidate_rows: int
    selected_rows: int


@dataclass(frozen=True)
class PITSplitAudit:
    """Counts for the time, company, and intersection holdouts."""

    total_rows: int
    time_holdout_rows: int
    company_holdout_rows: int
    both_holdout_rows: int
    minimum_required: int
    accepted: bool


def _as_date(value: date | datetime | str, *, name: str) -> date:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{name} datetime must be timezone-aware")
        return value.astimezone(_EASTERN).date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO date") from error


def _parse_acceptance_datetime(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("acceptanceDateTime is required; do not fall back to filingDate")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"invalid acceptanceDateTime: {value!r}") from error
    if parsed.tzinfo is None:
        raise ValueError("acceptanceDateTime must include a timezone offset")
    return parsed


def normalize_accession(value: Any) -> str:
    """Normalize an SEC accession number to ``##########-##-######``."""

    if not isinstance(value, str) or not value.strip():
        raise ValueError("accession number must be a non-empty string")
    digits = value.replace("-", "").strip()
    if len(digits) != 18 or not digits.isdigit():
        raise ValueError(f"invalid SEC accession number: {value!r}")
    return f"{digits[:10]}-{digits[10:12]}-{digits[12:]}"


def _unwrap_submission_table(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if "filings" in payload and isinstance(payload["filings"], Mapping):
        nested = payload["filings"]
        if "recent" in nested and isinstance(nested["recent"], Mapping):
            return nested["recent"]
    return payload


def _column_rows(table: Mapping[str, Any], *, cik: int | None) -> list[dict[str, Any]]:
    """Turn SEC's column-oriented recent/archive table into rows."""

    table = _unwrap_submission_table(table)
    required = ("accessionNumber", "filingDate", "acceptanceDateTime", "form")
    missing = [name for name in required if name not in table]
    if missing:
        raise ValueError(f"submission table is missing required columns: {missing}")
    lengths = {len(table[name]) for name in required}
    if len(lengths) != 1:
        raise ValueError("submission columns have inconsistent lengths")
    count = lengths.pop()
    cik_values = table.get("cik")
    if cik_values is not None and len(cik_values) != count:
        raise ValueError("submission cik column has an inconsistent length")
    if cik is None and cik_values is None:
        raise ValueError("cik is required when submission rows have no cik column")

    rows: list[dict[str, Any]] = []
    for index in range(count):
        row_cik = cik_values[index] if cik_values is not None else cik
        if row_cik is None:
            raise ValueError("submission row has no cik")
        rows.append(
            {
                "accession_number": normalize_accession(table["accessionNumber"][index]),
                "cik": int(str(row_cik).lstrip("0") or "0"),
                "form": str(table["form"][index]),
                "filing_date": _as_date(table["filingDate"][index], name="filingDate"),
                "acceptance_datetime": _parse_acceptance_datetime(
                    table["acceptanceDateTime"][index]
                ),
            }
        )
    return rows


def build_filing_index(
    recent: Mapping[str, Any],
    archives: Iterable[Mapping[str, Any]] = (),
    *,
    cik: int | None = None,
) -> dict[str, FilingRecord]:
    """Merge ``recent`` and every fetched ``filings.files`` archive.

    Duplicate accessions are accepted only when their normalized metadata is
    identical.  Any conflict is rejected instead of choosing the newer API
    response silently.
    """

    rows = _column_rows(recent, cik=cik)
    for archive in archives:
        rows.extend(_column_rows(archive, cik=cik))
    result: dict[str, FilingRecord] = {}
    for row in rows:
        record = FilingRecord(**row)
        existing = result.get(record.accession_number)
        if existing is not None and existing != record:
            raise ValueError(f"conflicting metadata for accession {record.accession_number}")
        result[record.accession_number] = record
    return dict(sorted(result.items()))


def next_us_business_day(
    value: date | datetime | str,
    *,
    holiday_dates: Iterable[date] | None = None,
) -> date:
    """Advance strictly after ``value`` using weekends and U.S. federal holidays."""

    current = _as_date(value, name="value") + timedelta(days=1)
    if holiday_dates is None:
        calendar = USFederalHolidayCalendar()
        start = pd.Timestamp(current)
        end = start + pd.Timedelta(days=14)
        holidays = {timestamp.date() for timestamp in calendar.holidays(start, end)}
    else:
        holidays = {_as_date(item, name="holiday") for item in holiday_dates}
    while current.weekday() >= 5 or current in holidays:
        current += timedelta(days=1)
    return current


def resolve_first_reported_vintages(
    facts: Iterable[Mapping[str, Any]],
    filing_index: Mapping[str, FilingRecord],
    *,
    holiday_dates: Iterable[date] | None = None,
    allowed_forms: Iterable[str] = ALLOWED_FILING_FORMS,
) -> tuple[dict[str, Any], ...]:
    """Join facts to filings and retain the earliest reported value per period.

    The returned dictionaries are intentionally simple so they can be written
    to a small audit JSON without serializing a DataFrame or raw SEC response.
    """

    forms = frozenset(allowed_forms)
    candidates: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    unresolved: list[str] = []
    for fact in facts:
        accession_raw = fact.get("accn")
        if accession_raw in (None, ""):
            raise ValueError("every admitted Company Facts row must contain accn")
        accession = normalize_accession(str(accession_raw))
        record = filing_index.get(accession)
        if record is None:
            unresolved.append(accession)
            continue
        if record.form not in forms:
            continue
        value = float(fact.get("val"))
        if not isfinite(value):
            raise ValueError(f"fact value must be finite for {accession}")
        fact_cik = fact.get("cik")
        if fact_cik is not None and int(str(fact_cik).lstrip("0") or "0") != record.cik:
            raise ValueError(f"fact and filing CIK disagree for {accession}")
        key = (
            record.cik,
            fact.get("concept"),
            fact.get("unit"),
            fact.get("start"),
            fact.get("end"),
        )
        candidates.setdefault(key, []).append(
            {
                "cik": record.cik,
                "concept": fact.get("concept"),
                "unit": fact.get("unit"),
                "start": fact.get("start"),
                "end": fact.get("end"),
                "value": value,
                "accn": accession,
                "form": record.form,
                "filed": record.filing_date.isoformat(),
                "acceptance_datetime": record.acceptance_datetime.isoformat(),
                "availability_date": record.availability_date(
                    holiday_dates=holiday_dates
                ).isoformat(),
            }
        )
    if unresolved:
        raise UnresolvedAccessionError(unresolved)

    output: list[dict[str, Any]] = []
    for rows in candidates.values():
        rows.sort(
            key=lambda row: (
                row["availability_date"],
                row["acceptance_datetime"],
                row["filed"],
                row["accn"],
            )
        )
        first = rows[0]
        if any(row["value"] != first["value"] and row["accn"] == first["accn"] for row in rows):
            raise ValueError(f"conflicting fact values for first filing {first['accn']}")
        output.append({**first, "first_reported": True})
    return tuple(
        sorted(
            output,
            key=lambda row: (
                row["cik"],
                str(row["concept"]),
                str(row["unit"]),
                str(row["end"]),
            ),
        )
    )


def select_fixed_anchor_cohort(
    vintages: Iterable[Mapping[str, Any]],
    spec: PITUniverseSpec,
    *,
    concept: str = "us-gaap/Assets",
    unit: str = "USD",
) -> PITUniverseSelection:
    """Select firms using only facts observable by an explicit anchor date.

    This is the safe Core fallback when a dynamic historical universe is not
    yet available.  Observations before ``spec.analysis_start`` must be
    excluded by the downstream panel builder.
    """

    candidates: dict[int, Mapping[str, Any]] = {}
    candidate_rows = 0
    for row in vintages:
        if row.get("concept") != concept or row.get("unit") != unit:
            continue
        if _as_date(row.get("end"), name="period end") != spec.anchor_period_end:
            continue
        if _as_date(row.get("availability_date"), name="availability_date") > spec.anchor_as_of:
            continue
        if float(row.get("value")) < spec.minimum_assets_usd:
            continue
        candidate_rows += 1
        cik = int(row["cik"])
        candidates.setdefault(cik, row)
    ciks = tuple(sorted(candidates))
    return PITUniverseSelection(
        spec=spec,
        eligible_ciks=ciks,
        candidate_rows=candidate_rows,
        selected_rows=len(ciks),
    )


def audit_split_counts(
    rows: Iterable[Mapping[str, Any]],
    *,
    time_cutoff: date,
    company_modulus: int = 3,
    company_remainder: int = 0,
    minimum_required: int = 200,
) -> PITSplitAudit:
    """Audit B9's two holdouts and the strict intersection sample size."""

    if company_modulus < 2 or not 0 <= company_remainder < company_modulus:
        raise ValueError("company holdout must be a valid modulus and remainder")
    if minimum_required < 1:
        raise ValueError("minimum_required must be positive")
    total = time_count = company_count = both_count = 0
    for row in rows:
        target_date = _as_date(row.get("target_avail"), name="target_avail")
        cik = int(row["cik"])
        is_time = target_date >= time_cutoff
        is_company = cik % company_modulus == company_remainder
        total += 1
        time_count += int(is_time)
        company_count += int(is_company)
        both_count += int(is_time and is_company)
    return PITSplitAudit(
        total_rows=total,
        time_holdout_rows=time_count,
        company_holdout_rows=company_count,
        both_holdout_rows=both_count,
        minimum_required=minimum_required,
        accepted=both_count >= minimum_required,
    )


def fundamentals_error_metrics(
    actual: Sequence[float], predicted: Sequence[float]
) -> FundamentalsErrorMetrics:
    """Compute the B9 primary/secondary/reference error metrics."""

    actual_array = np.asarray(actual, dtype=float)
    predicted_array = np.asarray(predicted, dtype=float)
    if (
        actual_array.ndim != 1
        or predicted_array.shape != actual_array.shape
        or actual_array.size == 0
    ):
        raise ValueError("actual and predicted must be equally sized one-dimensional arrays")
    if not np.all(np.isfinite(actual_array)) or not np.all(np.isfinite(predicted_array)):
        raise ValueError("actual and predicted must be finite")
    absolute = np.abs(actual_array - predicted_array)
    return FundamentalsErrorMetrics(
        n=int(actual_array.size),
        mae=float(np.mean(absolute)),
        median_absolute_error=float(np.median(absolute)),
        rmse=float(sqrt(np.mean(np.square(actual_array - predicted_array)))),
    )


__all__ = [
    "ALLOWED_FILING_FORMS",
    "FilingRecord",
    "FundamentalsErrorMetrics",
    "PITSplitAudit",
    "PITUniverseSelection",
    "PITUniverseSpec",
    "UnresolvedAccessionError",
    "audit_split_counts",
    "build_filing_index",
    "fundamentals_error_metrics",
    "next_us_business_day",
    "normalize_accession",
    "resolve_first_reported_vintages",
    "select_fixed_anchor_cohort",
]
