"""Re-audit a derived B9 SEC panel artifact without reading raw SEC data.

The input is the JSON written by ``build_b9_panel.py``.  This command checks
the derived rows and independently recomputes the split counts and baseline
metrics.  It never opens the SEC cache recorded in artifact provenance.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar

_ARTIFACT_SCHEMA = "b9-sec-panel-v1"
_REPORT_SCHEMA = "b9-sec-panel-quality-audit-v1"
_PROTOCOL_SCHEMA = "b9-m6-protocol-v1"
_SEED_SCHEMA = "b9-historical-seed-v1"
_BATCH_SCHEMA = "b9-sec-batch-v1"
_HOLIDAY_SCHEMA = "b9-us-federal-holidays-v1"
_MINIMUM_GAP_DAYS = 60
_MAXIMUM_GAP_DAYS = 120
_M6_TIME_CUTOFF = date(2023, 10, 23)
_M6_COMPANY_MODULUS = 3
_M6_COMPANY_REMAINDER = 0
_M6_MINIMUM_REQUIRED = 200
_M6_ANCHOR_PERIOD_END = date(2015, 12, 31)
_M6_ANCHOR_AS_OF = date(2016, 4, 1)
_M6_ANALYSIS_START = date(2016, 4, 1)
_M6_MINIMUM_ASSETS_USD = 100_000_000.0
_M6_SEED_SOURCE_URL = "https://www.sec.gov/Archives/edgar/full-index/2016/QTR1/master.idx"
_M6_SEED_FORMS = ("10-K",)
_M6_SEED_FILED_START = date(2016, 1, 1)
_M6_SEED_FILED_END = date(2016, 3, 31)
_M6_SEED_SELECTION_METHOD = "evenly_spaced_cik_rank"
_M6_SEED_CIK_COUNT = 300
_M6_HOLIDAY_COVERAGE_START = date(1990, 1, 1)
_M6_HOLIDAY_COVERAGE_END = date(2035, 12, 31)
_M6_EXCLUSION_REASONS = frozenset({"missing_us_gaap_assets_usd"})
_STRICT_PROVENANCE_SCOPE = (
    "derived artifact plus external seed/holiday manifests and embedded batch/cache-integrity "
    "summaries; raw SEC payloads and the raw batch manifest are not reread"
)
_PANEL_COLUMNS = (
    "cik",
    "previous_period_end",
    "target_period_end",
    "previous_assets_usd",
    "target_assets_usd",
    "target_log_change",
    "previous_available_date",
    "target_available_date",
    "known_at",
)
_DATE_COLUMNS = (
    "previous_period_end",
    "target_period_end",
    "previous_available_date",
    "target_available_date",
    "known_at",
)
_NUMERIC_COLUMNS = (
    "previous_assets_usd",
    "target_assets_usd",
    "target_log_change",
)
_SPLIT_NAMES = ("time", "company", "both")
_BASELINE_NAMES = ("zero", "pooled_drift", "seasonal", "company_mean")
_METRIC_NAMES = ("n", "mae", "median_absolute_error", "rmse")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ArtifactAuditError(ValueError):
    """The derived JSON does not satisfy the B9 artifact schema."""


@dataclass(frozen=True)
class _BaselineRow:
    cik: int
    target_period_end: date
    target_available_date: date
    known_at: date
    target_log_change: float


def _require_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ArtifactAuditError(f"{name} must be a JSON object")
    return value


def _require_list(value: Any, *, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ArtifactAuditError(f"{name} must be a JSON array")
    return value


def _required(mapping: Mapping[str, Any], key: str, *, name: str) -> Any:
    if key not in mapping:
        raise ArtifactAuditError(f"{name} is missing required field {key!r}")
    return mapping[key]


def _strict_integer(value: Any, *, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ArtifactAuditError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise ArtifactAuditError(f"{name} must be at least {minimum}")
    return value


def _strict_bool(value: Any, *, name: str) -> bool:
    if not isinstance(value, bool):
        raise ArtifactAuditError(f"{name} must be a boolean")
    return value


def _strict_number(value: Any, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ArtifactAuditError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ArtifactAuditError(f"{name} must be finite")
    return result


def _strict_text(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ArtifactAuditError(f"{name} must be a non-empty string")
    return value.strip()


def _strict_text_list(value: Any, *, name: str) -> list[str]:
    values = _require_list(value, name=name)
    if not values:
        raise ArtifactAuditError(f"{name} must not be empty")
    return [_strict_text(item, name=f"{name}[{index}]") for index, item in enumerate(values)]


def _strict_sha256(value: Any, *, name: str) -> str:
    digest = _strict_text(value, name=name).lower()
    if not _SHA256_PATTERN.fullmatch(digest):
        raise ArtifactAuditError(f"{name} must be a 64-character SHA-256 digest")
    return digest


def _strict_date(value: Any, *, name: str) -> date:
    if not isinstance(value, str):
        raise ArtifactAuditError(f"{name} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ArtifactAuditError(f"{name} must be an ISO date (YYYY-MM-DD)") from error


def _try_integer(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return value


def _try_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if math.isfinite(result) else None


def _try_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _load_artifact(path: Path) -> tuple[Path, bytes, Mapping[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"derived B9 artifact does not exist: {resolved}")
    payload = resolved.read_bytes()
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactAuditError(
            f"derived B9 artifact is not valid UTF-8 JSON: {resolved}"
        ) from error
    artifact = _require_mapping(decoded, name="artifact")
    schema = _required(artifact, "schema_version", name="artifact")
    if schema != _ARTIFACT_SCHEMA:
        raise ArtifactAuditError(
            f"artifact schema_version must be {_ARTIFACT_SCHEMA!r}, found {schema!r}"
        )
    _strict_bool(_required(artifact, "network_access", name="artifact"), name="network_access")
    _require_mapping(_required(artifact, "panel", name="artifact"), name="panel")
    _require_mapping(_required(artifact, "baseline", name="artifact"), name="baseline")
    return resolved, payload, artifact


def _profile_panel(panel: Mapping[str, Any]) -> tuple[dict[str, Any], list[_BaselineRow]]:
    columns = _require_list(_required(panel, "columns", name="panel"), name="panel.columns")
    if any(not isinstance(column, str) for column in columns):
        raise ArtifactAuditError("panel.columns entries must be strings")
    rows = _require_list(_required(panel, "rows", name="panel"), name="panel.rows")
    row_objects = [
        _require_mapping(row, name=f"panel.rows[{index}]") for index, row in enumerate(rows)
    ]

    null_by_column = {
        column: sum(row.get(column) is None for row in row_objects) for column in _PANEL_COLUMNS
    }
    invalid_cik_rows = 0
    invalid_date_rows = 0
    invalid_numeric_rows = 0
    nonpositive_asset_rows = 0
    period_order_violations = 0
    known_at_mismatch_rows = 0
    availability_order_violations = 0
    previous_availability_order_violations = 0
    target_availability_order_violations = 0
    invalid_gap_rows = 0
    target_log_change_mismatch_rows = 0
    grain_keys: list[tuple[int, date, date]] = []
    target_keys: list[tuple[int, date]] = []
    valid_ciks: set[int] = set()
    observed_gaps: list[int] = []
    baseline_rows: list[_BaselineRow] = []

    for row in row_objects:
        cik = _try_integer(row.get("cik"))
        if cik is None:
            invalid_cik_rows += 1
        else:
            valid_ciks.add(cik)

        dates = {column: _try_date(row.get(column)) for column in _DATE_COLUMNS}
        if any(value is None for value in dates.values()):
            invalid_date_rows += 1

        numbers = {column: _try_number(row.get(column)) for column in _NUMERIC_COLUMNS}
        if any(value is None for value in numbers.values()):
            invalid_numeric_rows += 1

        previous_period = dates["previous_period_end"]
        target_period = dates["target_period_end"]
        previous_available = dates["previous_available_date"]
        target_available = dates["target_available_date"]
        known_at = dates["known_at"]
        previous_assets = numbers["previous_assets_usd"]
        target_assets = numbers["target_assets_usd"]
        target_log_change = numbers["target_log_change"]

        if previous_assets is not None and target_assets is not None:
            if previous_assets <= 0.0 or target_assets <= 0.0:
                nonpositive_asset_rows += 1
            elif target_log_change is not None:
                expected_change = math.log(target_assets / previous_assets)
                if not math.isclose(
                    target_log_change,
                    expected_change,
                    rel_tol=1e-12,
                    abs_tol=1e-15,
                ):
                    target_log_change_mismatch_rows += 1

        if previous_period is not None and target_period is not None:
            gap = (target_period - previous_period).days
            observed_gaps.append(gap)
            period_order_violations += int(target_period <= previous_period)
            invalid_gap_rows += int(not _MINIMUM_GAP_DAYS <= gap <= _MAXIMUM_GAP_DAYS)
            if cik is not None:
                grain_keys.append((cik, previous_period, target_period))
                target_keys.append((cik, target_period))

        if previous_available is not None and known_at is not None:
            known_at_mismatch_rows += int(known_at != previous_available)
        if target_available is not None and known_at is not None:
            availability_order_violations += int(target_available <= known_at)
        if previous_available is not None and previous_period is not None:
            previous_availability_order_violations += int(previous_available <= previous_period)
        if target_available is not None and target_period is not None:
            target_availability_order_violations += int(target_available <= target_period)

        if (
            cik is not None
            and target_period is not None
            and target_available is not None
            and known_at is not None
            and target_log_change is not None
        ):
            baseline_rows.append(
                _BaselineRow(
                    cik=cik,
                    target_period_end=target_period,
                    target_available_date=target_available,
                    known_at=known_at,
                    target_log_change=target_log_change,
                )
            )

    grain_counts = Counter(grain_keys)
    target_counts = Counter(target_keys)
    duplicate_keys = sum(count - 1 for count in grain_counts.values() if count > 1)
    duplicate_target_keys = sum(count - 1 for count in target_counts.values() if count > 1)
    profile = {
        "expected_grain": "one row per CIK and adjacent-quarter pair",
        "columns_match_contract": columns == list(_PANEL_COLUMNS),
        "row_count": len(row_objects),
        "company_count": len(valid_ciks),
        "null_by_column": null_by_column,
        "null_cells": sum(null_by_column.values()),
        "invalid_cik_rows": invalid_cik_rows,
        "invalid_date_rows": invalid_date_rows,
        "invalid_numeric_rows": invalid_numeric_rows,
        "duplicate_keys": duplicate_keys,
        "duplicate_target_keys": duplicate_target_keys,
        "nonpositive_asset_rows": nonpositive_asset_rows,
        "target_log_change_mismatch_rows": target_log_change_mismatch_rows,
        "period_order_violations": period_order_violations,
        "known_at_mismatch_rows": known_at_mismatch_rows,
        "availability_order_violations": availability_order_violations,
        "previous_availability_order_violations": previous_availability_order_violations,
        "target_availability_order_violations": target_availability_order_violations,
        "baseline_unusable_rows": len(row_objects) - len(baseline_rows),
        "valid_ciks": sorted(valid_ciks),
        "gap": {
            "required_minimum_days": _MINIMUM_GAP_DAYS,
            "required_maximum_days": _MAXIMUM_GAP_DAYS,
            "invalid_rows": invalid_gap_rows,
            "observed_minimum_days": min(observed_gaps) if observed_gaps else None,
            "observed_maximum_days": max(observed_gaps) if observed_gaps else None,
        },
    }
    return profile, baseline_rows


def _audit_universe(panel: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    universe = _require_mapping(_required(panel, "universe", name="panel"), name="panel.universe")
    eligible_values = _require_list(
        _required(universe, "eligible_ciks", name="panel.universe"),
        name="panel.universe.eligible_ciks",
    )
    eligible = [
        _strict_integer(value, name=f"eligible_ciks[{index}]", minimum=1)
        for index, value in enumerate(eligible_values)
    ]
    candidate_rows = _strict_integer(
        _required(universe, "candidate_rows", name="panel.universe"),
        name="panel.universe.candidate_rows",
        minimum=0,
    )
    selected_rows = _strict_integer(
        _required(universe, "selected_rows", name="panel.universe"),
        name="panel.universe.selected_rows",
        minimum=0,
    )
    row_ciks = set(profile["valid_ciks"])
    eligible_set = set(eligible)
    return {
        "eligible_cik_count": len(eligible),
        "candidate_rows": candidate_rows,
        "selected_rows": selected_rows,
        "eligible_ciks_unique": len(eligible) == len(eligible_set),
        "selected_rows_match": selected_rows == len(eligible),
        "candidate_rows_cover_selection": candidate_rows >= selected_rows,
        "panel_ciks_within_cohort": row_ciks <= eligible_set,
    }


def _audit_stored_quality(panel: Mapping[str, Any], profile: Mapping[str, Any]) -> dict[str, Any]:
    quality = _require_mapping(_required(panel, "quality", name="panel"), name="panel.quality")
    stored_missing = _require_mapping(
        _required(quality, "missing_by_column", name="panel.quality"),
        name="panel.quality.missing_by_column",
    )
    normalized_missing = {
        column: _strict_integer(
            _required(stored_missing, column, name="panel.quality.missing_by_column"),
            name=f"panel.quality.missing_by_column.{column}",
            minimum=0,
        )
        for column in _PANEL_COLUMNS
    }
    stored = {
        "row_count": _strict_integer(
            _required(quality, "row_count", name="panel.quality"),
            name="panel.quality.row_count",
            minimum=0,
        ),
        "company_count": _strict_integer(
            _required(quality, "company_count", name="panel.quality"),
            name="panel.quality.company_count",
            minimum=0,
        ),
        "duplicate_keys": _strict_integer(
            _required(quality, "duplicate_keys", name="panel.quality"),
            name="panel.quality.duplicate_keys",
            minimum=0,
        ),
        "missing_by_column": normalized_missing,
        "nonpositive_asset_rows": _strict_integer(
            _required(quality, "nonpositive_asset_rows", name="panel.quality"),
            name="panel.quality.nonpositive_asset_rows",
            minimum=0,
        ),
        "accepted": _strict_bool(
            _required(quality, "accepted", name="panel.quality"),
            name="panel.quality.accepted",
        ),
    }
    recomputed_accepted = bool(
        profile["row_count"] > 0
        and profile["duplicate_keys"] == 0
        and profile["null_cells"] == 0
        and profile["nonpositive_asset_rows"] == 0
    )
    expected = {
        "row_count": profile["row_count"],
        "company_count": profile["company_count"],
        "duplicate_keys": profile["duplicate_keys"],
        "missing_by_column": profile["null_by_column"],
        "nonpositive_asset_rows": profile["nonpositive_asset_rows"],
        "accepted": recomputed_accepted,
    }
    mismatched_fields = [name for name in expected if stored[name] != expected[name]]
    return {
        "matches_artifact": not mismatched_fields,
        "mismatched_fields": mismatched_fields,
        "source_excluded_invalid_gap_rows": _strict_integer(
            _required(quality, "invalid_gap_rows", name="panel.quality"),
            name="panel.quality.invalid_gap_rows",
            minimum=0,
        ),
        "source_gap_affected_company_count": _strict_integer(
            _required(quality, "gap_affected_company_count", name="panel.quality"),
            name="panel.quality.gap_affected_company_count",
            minimum=0,
        ),
        "source_maximum_gap_days": _strict_integer(
            _required(quality, "maximum_gap_days", name="panel.quality"),
            name="panel.quality.maximum_gap_days",
            minimum=0,
        ),
    }


def _normalized_cik(value: Any, *, name: str) -> str:
    if isinstance(value, bool):
        raise ArtifactAuditError(f"{name} must be a positive SEC CIK")
    text = str(value).strip()
    if not text.isdigit() or not 1 <= int(text) <= 9_999_999_999:
        raise ArtifactAuditError(f"{name} must be a positive SEC CIK")
    return text.zfill(10)


def _cik_digest(values: Sequence[Any], *, name: str) -> tuple[int, str]:
    normalized = sorted(
        {_normalized_cik(value, name=f"{name}[{index}]") for index, value in enumerate(values)}
    )
    payload = ("\n".join(normalized) + "\n").encode("utf-8")
    return len(normalized), sha256(payload).hexdigest()


def _seed_file_audit(
    path_text: str, expected: Mapping[str, Any]
) -> tuple[dict[str, Any], set[int]]:
    path = Path(path_text).expanduser().resolve()
    result: dict[str, Any] = {
        "path": str(path),
        "exists": path.is_file(),
        "sha256_matches": False,
        "metadata_matches": False,
        "selected_cik_hash_matches": False,
        "error": None,
    }
    if not path.is_file():
        result["error"] = "historical seed manifest file is missing"
        return result, set()
    selected_cik_values: set[int] = set()
    try:
        payload = path.read_bytes()
        result["sha256_matches"] = sha256(payload).hexdigest() == expected["sha256"]
        decoded = json.loads(payload)
        manifest = _require_mapping(decoded, name="historical seed manifest")
        selected_records = _require_list(
            _required(manifest, "selected_records", name="historical seed manifest"),
            name="historical seed manifest.selected_records",
        )
        selected_ciks = [
            _required(
                _require_mapping(record, name=f"selected_records[{index}]"),
                "cik",
                name=f"selected_records[{index}]",
            )
            for index, record in enumerate(selected_records)
        ]
        selected_count, selected_digest = _cik_digest(
            selected_ciks, name="historical seed manifest selected CIK"
        )
        selected_cik_values = {
            int(_normalized_cik(value, name="selected CIK")) for value in selected_ciks
        }
        result["selected_cik_hash_matches"] = bool(
            selected_count == expected["selected_cik_count"]
            and selected_digest == expected["selected_cik_sha256"]
        )
        result["metadata_matches"] = bool(
            manifest.get("schema_version") == _SEED_SCHEMA
            and manifest.get("master_index_sha256") == expected["master_index_sha256"]
            and manifest.get("source_url") == expected["source_url"]
            and manifest.get("forms") == expected["forms"]
            and manifest.get("filed_start") == expected["filed_start"]
            and manifest.get("filed_end") == expected["filed_end"]
            and manifest.get("selection_method") == expected["selection_method"]
            and manifest.get("selected_cik_count") == expected["selected_cik_count"]
            and manifest.get("selected_cik_sha256") == expected["selected_cik_sha256"]
        )
    except (ArtifactAuditError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        result["error"] = str(error)
    return result, selected_cik_values


def _holiday_manifest_audit(value: Any) -> dict[str, Any]:
    if value is None:
        return {
            "matches_artifact": False,
            "path": None,
            "sha256": None,
            "schema_version": None,
            "calendar": None,
            "start": None,
            "end": None,
            "holiday_count": None,
            "file_audit": {
                "exists": False,
                "sha256_matches": False,
                "metadata_matches": False,
                "dates_sorted_unique": False,
                "dates_within_manifest_bounds": False,
                "calendar_dates_match_runtime": False,
                "pandas_version_matches_runtime": False,
                "observed_holiday_count": None,
                "observed_first_holiday": None,
                "observed_last_holiday": None,
                "error": "holiday manifest provenance is missing",
            },
        }

    provenance = _require_mapping(value, name="input_provenance.holiday_manifest")
    summary = {
        "path": _strict_text(
            _required(provenance, "path", name="holiday_manifest"),
            name="holiday_manifest.path",
        ),
        "sha256": _strict_sha256(
            _required(provenance, "sha256", name="holiday_manifest"),
            name="holiday_manifest.sha256",
        ),
        "schema_version": _strict_text(
            _required(provenance, "schema_version", name="holiday_manifest"),
            name="holiday_manifest.schema_version",
        ),
        "calendar": _strict_text(
            _required(provenance, "calendar", name="holiday_manifest"),
            name="holiday_manifest.calendar",
        ),
        "start": _strict_date(
            _required(provenance, "start", name="holiday_manifest"),
            name="holiday_manifest.start",
        ),
        "end": _strict_date(
            _required(provenance, "end", name="holiday_manifest"),
            name="holiday_manifest.end",
        ),
        "holiday_count": _strict_integer(
            _required(provenance, "holiday_count", name="holiday_manifest"),
            name="holiday_manifest.holiday_count",
            minimum=1,
        ),
    }
    path = Path(summary["path"]).expanduser().resolve()
    file_audit: dict[str, Any] = {
        "exists": path.is_file(),
        "sha256_matches": False,
        "metadata_matches": False,
        "dates_sorted_unique": False,
        "dates_within_manifest_bounds": False,
        "calendar_dates_match_runtime": False,
        "pandas_version_matches_runtime": False,
        "observed_holiday_count": None,
        "observed_first_holiday": None,
        "observed_last_holiday": None,
        "error": None,
    }
    if not path.is_file():
        file_audit["error"] = "holiday manifest file is missing"
    else:
        try:
            payload = path.read_bytes()
            file_audit["sha256_matches"] = sha256(payload).hexdigest() == summary["sha256"]
            decoded = json.loads(payload)
            manifest = _require_mapping(decoded, name="holiday manifest")
            date_values = _require_list(
                _required(manifest, "holiday_dates", name="holiday manifest"),
                name="holiday manifest.holiday_dates",
            )
            if not date_values:
                raise ArtifactAuditError("holiday manifest.holiday_dates must not be empty")
            parsed_dates = [
                _strict_date(item, name=f"holiday manifest.holiday_dates[{index}]")
                for index, item in enumerate(date_values)
            ]
            file_audit["dates_sorted_unique"] = parsed_dates == sorted(set(parsed_dates))
            file_audit["dates_within_manifest_bounds"] = bool(
                summary["start"] <= summary["end"]
                and all(summary["start"] <= item <= summary["end"] for item in parsed_dates)
            )
            file_audit["observed_holiday_count"] = len(parsed_dates)
            file_audit["observed_first_holiday"] = min(parsed_dates).isoformat()
            file_audit["observed_last_holiday"] = max(parsed_dates).isoformat()
            manifest_pandas_version = _strict_text(
                _required(manifest, "pandas_version", name="holiday manifest"),
                name="holiday manifest.pandas_version",
            )
            expected_dates = [
                value.date()
                for value in USFederalHolidayCalendar().holidays(
                    start=summary["start"], end=summary["end"]
                )
            ]
            file_audit["calendar_dates_match_runtime"] = parsed_dates == expected_dates
            file_audit["pandas_version_matches_runtime"] = manifest_pandas_version == pd.__version__
            file_audit["manifest_pandas_version"] = manifest_pandas_version
            file_audit["runtime_pandas_version"] = pd.__version__
            file_audit["metadata_matches"] = bool(
                manifest.get("schema_version") == summary["schema_version"] == _HOLIDAY_SCHEMA
                and manifest.get("calendar")
                == summary["calendar"]
                == "pandas.USFederalHolidayCalendar"
                and manifest.get("start") == summary["start"].isoformat()
                and manifest.get("end") == summary["end"].isoformat()
                and len(parsed_dates) == summary["holiday_count"]
            )
        except (ArtifactAuditError, OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            file_audit["error"] = str(error)

    matches = bool(
        summary["start"] <= summary["end"]
        and all(
            file_audit[name]
            for name in (
                "exists",
                "sha256_matches",
                "metadata_matches",
                "dates_sorted_unique",
                "dates_within_manifest_bounds",
                "calendar_dates_match_runtime",
                "pandas_version_matches_runtime",
            )
        )
    )
    return {
        "matches_artifact": matches,
        **{
            name: value.isoformat() if isinstance(value, date) else value
            for name, value in summary.items()
        },
        "file_audit": file_audit,
    }


def _cache_integrity_audit(
    value: Any,
    *,
    source_cache_count: int,
    panel_ciks: set[int],
    excluded_ciks: set[int],
    selected_seed_ciks: set[int],
) -> dict[str, Any]:
    if value is None:
        return {
            "matches_artifact": False,
            "accepted": False,
            "success_cik_count": None,
            "success_cik_sha256": None,
            "success_ciks_present": False,
            "success_ciks_unique": None,
            "success_cik_count_matches": False,
            "success_cik_hash_matches": None,
            "panel_ciks_within_successes": None,
            "excluded_ciks_within_successes": None,
            "success_ciks_within_seed": None,
            "errors": ["cache_integrity provenance is missing"],
        }
    integrity = _require_mapping(value, name="input_provenance.cache_integrity")
    accepted = _strict_bool(
        _required(integrity, "accepted", name="cache_integrity"),
        name="cache_integrity.accepted",
    )
    success_count = _strict_integer(
        _required(integrity, "success_cik_count", name="cache_integrity"),
        name="cache_integrity.success_cik_count",
        minimum=0,
    )
    error_values = _require_list(
        _required(integrity, "errors", name="cache_integrity"),
        name="cache_integrity.errors",
    )
    errors = [
        _strict_text(item, name=f"cache_integrity.errors[{index}]")
        for index, item in enumerate(error_values)
    ]
    success_values = integrity.get("success_ciks")
    success_digest_value = integrity.get("success_cik_sha256")
    detailed_fields_complete = (success_values is None) == (success_digest_value is None)
    success_ciks_present = success_values is not None and success_digest_value is not None
    success_digest: str | None = None
    success_ciks_unique: bool | None = None
    success_count_matches = success_count == source_cache_count
    success_hash_matches: bool | None = None
    panel_ciks_within_successes: bool | None = None
    excluded_ciks_within_successes: bool | None = None
    success_ciks_within_seed: bool | None = None
    if success_ciks_present:
        entries = _require_list(success_values, name="cache_integrity.success_ciks")
        normalized = [
            int(_normalized_cik(item, name=f"cache_integrity.success_ciks[{index}]"))
            for index, item in enumerate(entries)
        ]
        success_set = set(normalized)
        success_ciks_unique = len(normalized) == len(success_set)
        observed_count, observed_digest = _cik_digest(
            normalized, name="cache_integrity.success_ciks"
        )
        success_digest = _strict_sha256(
            success_digest_value, name="cache_integrity.success_cik_sha256"
        )
        success_count_matches = bool(
            success_count == source_cache_count == observed_count == len(entries)
        )
        success_hash_matches = observed_digest == success_digest
        panel_ciks_within_successes = panel_ciks <= success_set
        excluded_ciks_within_successes = excluded_ciks <= success_set
        success_ciks_within_seed = success_set <= selected_seed_ciks
    covered_ciks_within_source_count = len(panel_ciks | excluded_ciks) <= source_cache_count
    matches = bool(
        accepted
        and not errors
        and detailed_fields_complete
        and success_ciks_present
        and success_count_matches
        and covered_ciks_within_source_count
        and bool(
            success_ciks_unique
            and success_hash_matches
            and panel_ciks_within_successes
            and excluded_ciks_within_successes
            and success_ciks_within_seed
        )
    )
    return {
        "matches_artifact": matches,
        "accepted": accepted,
        "success_cik_count": success_count,
        "success_cik_sha256": success_digest,
        "success_ciks_present": success_ciks_present,
        "success_ciks_unique": success_ciks_unique,
        "success_cik_count_matches": success_count_matches,
        "success_cik_hash_matches": success_hash_matches,
        "panel_ciks_within_successes": panel_ciks_within_successes,
        "excluded_ciks_within_successes": excluded_ciks_within_successes,
        "success_ciks_within_seed": success_ciks_within_seed,
        "covered_cik_count": len(panel_ciks | excluded_ciks),
        "covered_ciks_within_source_count": covered_ciks_within_source_count,
        "errors": errors,
    }


def _audit_source_provenance(
    artifact: Mapping[str, Any],
    panel: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    provenance = _require_mapping(
        _required(artifact, "input_provenance", name="artifact"),
        name="input_provenance",
    )
    holiday_manifest = _holiday_manifest_audit(provenance.get("holiday_manifest"))
    seed_value = provenance.get("historical_seed_manifest")
    batch_value = provenance.get("batch_manifest")
    if seed_value is None and batch_value is None:
        return {
            "mode": "legacy_without_seed_or_batch_manifest",
            "strict_scope": _STRICT_PROVENANCE_SCOPE,
            "matches_artifact": True,
            "strict_gate_accepted": False,
            "seed_manifest": None,
            "batch_manifest": None,
            "holiday_manifest": holiday_manifest,
            "cache_integrity": None,
            "source_quality": None,
        }
    if seed_value is None or batch_value is None:
        return {
            "mode": "incomplete_manifest_chain",
            "strict_scope": _STRICT_PROVENANCE_SCOPE,
            "matches_artifact": False,
            "strict_gate_accepted": False,
            "seed_manifest": None,
            "batch_manifest": None,
            "holiday_manifest": holiday_manifest,
            "cache_integrity": None,
            "source_quality": None,
        }

    seed = _require_mapping(seed_value, name="input_provenance.historical_seed_manifest")
    batch = _require_mapping(batch_value, name="input_provenance.batch_manifest")
    seed_summary = {
        "path": _strict_text(
            _required(seed, "path", name="historical_seed_manifest"),
            name="historical_seed_manifest.path",
        ),
        "sha256": _strict_sha256(
            _required(seed, "sha256", name="historical_seed_manifest"),
            name="historical_seed_manifest.sha256",
        ),
        "schema_version": _strict_text(
            _required(seed, "schema_version", name="historical_seed_manifest"),
            name="historical_seed_manifest.schema_version",
        ),
        "master_index_sha256": _strict_sha256(
            _required(seed, "master_index_sha256", name="historical_seed_manifest"),
            name="historical_seed_manifest.master_index_sha256",
        ),
        "source_url": _strict_text(
            _required(seed, "source_url", name="historical_seed_manifest"),
            name="historical_seed_manifest.source_url",
        ),
        "forms": _strict_text_list(
            _required(seed, "forms", name="historical_seed_manifest"),
            name="historical_seed_manifest.forms",
        ),
        "filed_start": _strict_date(
            _required(seed, "filed_start", name="historical_seed_manifest"),
            name="historical_seed_manifest.filed_start",
        ).isoformat(),
        "filed_end": _strict_date(
            _required(seed, "filed_end", name="historical_seed_manifest"),
            name="historical_seed_manifest.filed_end",
        ).isoformat(),
        "selection_method": _strict_text(
            _required(seed, "selection_method", name="historical_seed_manifest"),
            name="historical_seed_manifest.selection_method",
        ),
        "selected_cik_count": _strict_integer(
            _required(seed, "selected_cik_count", name="historical_seed_manifest"),
            name="historical_seed_manifest.selected_cik_count",
            minimum=1,
        ),
        "selected_cik_sha256": _strict_sha256(
            _required(seed, "selected_cik_sha256", name="historical_seed_manifest"),
            name="historical_seed_manifest.selected_cik_sha256",
        ),
    }
    batch_summary = {
        "path": _strict_text(
            _required(batch, "path", name="batch_manifest"), name="batch_manifest.path"
        ),
        "sha256": _strict_sha256(
            _required(batch, "sha256", name="batch_manifest"),
            name="batch_manifest.sha256",
        ),
        "schema_version": _strict_text(
            _required(batch, "schema_version", name="batch_manifest"),
            name="batch_manifest.schema_version",
        ),
        "requested_cik_count": _strict_integer(
            _required(batch, "requested_cik_count", name="batch_manifest"),
            name="batch_manifest.requested_cik_count",
            minimum=1,
        ),
        "success_count": _strict_integer(
            _required(batch, "success_count", name="batch_manifest"),
            name="batch_manifest.success_count",
            minimum=0,
        ),
        "failure_count": _strict_integer(
            _required(batch, "failure_count", name="batch_manifest"),
            name="batch_manifest.failure_count",
            minimum=0,
        ),
        "observed_requested_cik_count": _strict_integer(
            _required(batch, "observed_requested_cik_count", name="batch_manifest"),
            name="batch_manifest.observed_requested_cik_count",
            minimum=1,
        ),
        "observed_requested_cik_sha256": _strict_sha256(
            _required(batch, "observed_requested_cik_sha256", name="batch_manifest"),
            name="batch_manifest.observed_requested_cik_sha256",
        ),
    }
    seed_file, selected_seed_ciks = _seed_file_audit(seed_summary["path"], seed_summary)
    seed_to_requested_matches = bool(
        seed_summary["selected_cik_count"] == batch_summary["observed_requested_cik_count"]
        and seed_summary["selected_cik_sha256"] == batch_summary["observed_requested_cik_sha256"]
    )
    observed_batch_counts_match = bool(
        batch_summary["requested_cik_count"]
        == batch_summary["observed_requested_cik_count"]
        == batch_summary["success_count"] + batch_summary["failure_count"]
    )

    quality = _require_mapping(_required(panel, "quality", name="panel"), name="panel.quality")
    source_cache_count = _strict_integer(
        _required(quality, "source_cache_count", name="panel.quality"),
        name="panel.quality.source_cache_count",
        minimum=0,
    )
    excluded_nonpositive_asset_pair_count = _strict_integer(
        _required(quality, "excluded_nonpositive_asset_pair_count", name="panel.quality"),
        name="panel.quality.excluded_nonpositive_asset_pair_count",
        minimum=0,
    )
    exclusion_value = _require_mapping(
        _required(quality, "excluded_issuer_ciks_by_reason", name="panel.quality"),
        name="panel.quality.excluded_issuer_ciks_by_reason",
    )
    exclusions: dict[str, list[int]] = {}
    all_excluded: list[int] = []
    for reason, values in exclusion_value.items():
        normalized_reason = _strict_text(reason, name="issuer exclusion reason")
        entries = _require_list(
            values,
            name=f"panel.quality.excluded_issuer_ciks_by_reason.{normalized_reason}",
        )
        ciks = [
            int(_normalized_cik(value, name=f"excluded CIK {normalized_reason}[{index}]"))
            for index, value in enumerate(entries)
        ]
        exclusions[normalized_reason] = ciks
        all_excluded.extend(ciks)
    exclusions_unique = len(all_excluded) == len(set(all_excluded))
    exclusions_absent_from_panel = set(all_excluded).isdisjoint(profile["valid_ciks"])
    exclusions_within_seed = set(all_excluded) <= selected_seed_ciks
    panel_ciks_within_seed = set(profile["valid_ciks"]) <= selected_seed_ciks
    covered_ciks_within_source_count = (
        len(set(profile["valid_ciks"]) | set(all_excluded)) <= source_cache_count
    )
    cache_integrity = _cache_integrity_audit(
        provenance.get("cache_integrity"),
        source_cache_count=source_cache_count,
        panel_ciks=set(profile["valid_ciks"]),
        excluded_ciks=set(all_excluded),
        selected_seed_ciks=selected_seed_ciks,
    )
    unexpected_exclusion_reasons = sorted(set(exclusions).difference(_M6_EXCLUSION_REASONS))
    source_quality = {
        "source_cache_count": source_cache_count,
        "excluded_issuer_count": len(all_excluded),
        "excluded_issuer_ciks_by_reason": exclusions,
        "excluded_nonpositive_asset_pair_count": excluded_nonpositive_asset_pair_count,
        "source_cache_count_matches_batch_success": (
            source_cache_count == batch_summary["success_count"]
        ),
        "exclusions_unique": exclusions_unique,
        "exclusions_absent_from_panel": exclusions_absent_from_panel,
        "exclusions_within_seed": exclusions_within_seed,
        "panel_ciks_within_seed": panel_ciks_within_seed,
        "exclusions_within_source_count": len(all_excluded) <= source_cache_count,
        "covered_ciks_within_source_count": covered_ciks_within_source_count,
        "unexpected_exclusion_reasons": unexpected_exclusion_reasons,
    }
    source_quality_matches = (
        all(
            source_quality[name]
            for name in (
                "source_cache_count_matches_batch_success",
                "exclusions_unique",
                "exclusions_absent_from_panel",
                "exclusions_within_seed",
                "panel_ciks_within_seed",
                "exclusions_within_source_count",
                "covered_ciks_within_source_count",
            )
        )
        and not unexpected_exclusion_reasons
    )
    seed_file_matches = all(
        seed_file[name]
        for name in ("exists", "sha256_matches", "metadata_matches", "selected_cik_hash_matches")
    )
    matches = bool(
        seed_file_matches
        and seed_summary["schema_version"] == _SEED_SCHEMA
        and batch_summary["schema_version"] == _BATCH_SCHEMA
        and holiday_manifest["matches_artifact"]
        and cache_integrity["matches_artifact"]
        and seed_to_requested_matches
        and observed_batch_counts_match
        and source_quality_matches
    )
    return {
        "mode": "historical_seed_and_observed_batch",
        "strict_scope": _STRICT_PROVENANCE_SCOPE,
        "matches_artifact": matches,
        "strict_gate_accepted": matches,
        "seed_manifest": {
            **seed_summary,
            "file_audit": seed_file,
            "matches_observed_requested_ciks": seed_to_requested_matches,
        },
        "batch_manifest": {
            **batch_summary,
            "observed_counts_match": observed_batch_counts_match,
        },
        "holiday_manifest": holiday_manifest,
        "cache_integrity": cache_integrity,
        "source_quality": source_quality,
    }


def _load_protocol(path: Path) -> tuple[Path, bytes, Mapping[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"B9 M6 protocol does not exist: {resolved}")
    payload = resolved.read_bytes()
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactAuditError(f"B9 M6 protocol is not valid UTF-8 JSON: {resolved}") from error
    protocol = _require_mapping(decoded, name="B9 M6 protocol")
    schema = _required(protocol, "schema_version", name="B9 M6 protocol")
    if schema != _PROTOCOL_SCHEMA:
        raise ArtifactAuditError(
            f"B9 M6 protocol schema_version must be {_PROTOCOL_SCHEMA!r}, found {schema!r}"
        )
    return resolved, payload, protocol


def _protocol_provenance_summary(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    provenance = _require_mapping(value, name="input_provenance.protocol")
    return {
        "path": _strict_text(
            _required(provenance, "path", name="input_provenance.protocol"),
            name="input_provenance.protocol.path",
        ),
        "sha256": _strict_sha256(
            _required(provenance, "sha256", name="input_provenance.protocol"),
            name="input_provenance.protocol.sha256",
        ),
        "schema_version": _strict_text(
            _required(provenance, "schema_version", name="input_provenance.protocol"),
            name="input_provenance.protocol.schema_version",
        ),
    }


def _audit_protocol(
    artifact: Mapping[str, Any],
    panel: Mapping[str, Any],
    baseline: Mapping[str, Any],
    source_provenance: Mapping[str, Any],
    protocol_path: Path | None,
) -> dict[str, Any]:
    input_provenance = _require_mapping(
        _required(artifact, "input_provenance", name="artifact"),
        name="input_provenance",
    )
    recorded = _protocol_provenance_summary(input_provenance.get("protocol"))
    if protocol_path is None:
        supported_record = recorded is None or recorded["schema_version"] == _PROTOCOL_SCHEMA
        return {
            "mode": "not_supplied" if recorded is not None else "legacy_without_protocol",
            "matches_artifact": supported_record,
            "strict_gate_accepted": False,
            "external_protocol": None,
            "artifact_provenance": recorded,
            "preregistered_checks": None,
            "artifact_match_checks": None,
            "mismatches": [],
        }

    resolved, payload, protocol = _load_protocol(protocol_path)
    universe_contract = _require_mapping(
        _required(protocol, "universe", name="B9 M6 protocol"),
        name="B9 M6 protocol.universe",
    )
    panel_contract = _require_mapping(
        _required(protocol, "panel", name="B9 M6 protocol"),
        name="B9 M6 protocol.panel",
    )
    evaluation_contract = _require_mapping(
        _required(protocol, "evaluation", name="B9 M6 protocol"),
        name="B9 M6 protocol.evaluation",
    )
    seed_contract = _require_mapping(
        _required(protocol, "historical_seed", name="B9 M6 protocol"),
        name="B9 M6 protocol.historical_seed",
    )
    metric_roles = _require_mapping(
        _required(evaluation_contract, "metrics", name="B9 M6 protocol.evaluation"),
        name="B9 M6 protocol.evaluation.metrics",
    )

    protocol_values = {
        "anchor_period_end": _strict_date(
            _required(universe_contract, "anchor_period_end", name="protocol universe"),
            name="protocol universe.anchor_period_end",
        ).isoformat(),
        "anchor_as_of": _strict_date(
            _required(universe_contract, "anchor_as_of", name="protocol universe"),
            name="protocol universe.anchor_as_of",
        ).isoformat(),
        "analysis_start": _strict_date(
            _required(universe_contract, "analysis_start", name="protocol universe"),
            name="protocol universe.analysis_start",
        ).isoformat(),
        "minimum_assets_usd": _strict_number(
            _required(universe_contract, "minimum_assets_usd", name="protocol universe"),
            name="protocol universe.minimum_assets_usd",
        ),
        "concept": _strict_text(
            _required(universe_contract, "concept", name="protocol universe"),
            name="protocol universe.concept",
        ),
        "unit": _strict_text(
            _required(universe_contract, "unit", name="protocol universe"),
            name="protocol universe.unit",
        ),
        "minimum_gap_days": _strict_integer(
            _required(panel_contract, "minimum_gap_days", name="protocol panel"),
            name="protocol panel.minimum_gap_days",
            minimum=1,
        ),
        "maximum_gap_days": _strict_integer(
            _required(panel_contract, "maximum_gap_days", name="protocol panel"),
            name="protocol panel.maximum_gap_days",
            minimum=1,
        ),
        "availability_calendar": _strict_text(
            _required(panel_contract, "availability_calendar", name="protocol panel"),
            name="protocol panel.availability_calendar",
        ),
        "holiday_manifest_start": _strict_date(
            _required(panel_contract, "holiday_manifest_start", name="protocol panel"),
            name="protocol panel.holiday_manifest_start",
        ).isoformat(),
        "holiday_manifest_end": _strict_date(
            _required(panel_contract, "holiday_manifest_end", name="protocol panel"),
            name="protocol panel.holiday_manifest_end",
        ).isoformat(),
        "time_cutoff": _strict_date(
            _required(evaluation_contract, "time_cutoff", name="protocol evaluation"),
            name="protocol evaluation.time_cutoff",
        ).isoformat(),
        "company_modulus": _strict_integer(
            _required(evaluation_contract, "company_modulus", name="protocol evaluation"),
            name="protocol evaluation.company_modulus",
            minimum=2,
        ),
        "company_remainder": _strict_integer(
            _required(evaluation_contract, "company_remainder", name="protocol evaluation"),
            name="protocol evaluation.company_remainder",
            minimum=0,
        ),
        "minimum_required": _strict_integer(
            _required(evaluation_contract, "minimum_required", name="protocol evaluation"),
            name="protocol evaluation.minimum_required",
            minimum=1,
        ),
        "metric_primary": _strict_text(
            _required(metric_roles, "primary", name="protocol evaluation.metrics"),
            name="protocol evaluation.metrics.primary",
        ),
        "metric_secondary": _strict_text(
            _required(metric_roles, "secondary", name="protocol evaluation.metrics"),
            name="protocol evaluation.metrics.secondary",
        ),
        "metric_reference": _strict_text(
            _required(metric_roles, "reference", name="protocol evaluation.metrics"),
            name="protocol evaluation.metrics.reference",
        ),
    }
    if protocol_values["company_remainder"] >= protocol_values["company_modulus"]:
        raise ArtifactAuditError("protocol company_remainder must be below company_modulus")
    seed_values = {
        "source_url": _strict_text(
            _required(seed_contract, "source_url", name="protocol historical_seed"),
            name="protocol historical_seed.source_url",
        ),
        "forms": _strict_text_list(
            _required(seed_contract, "forms", name="protocol historical_seed"),
            name="protocol historical_seed.forms",
        ),
        "filed_start": _strict_date(
            _required(seed_contract, "filed_start", name="protocol historical_seed"),
            name="protocol historical_seed.filed_start",
        ).isoformat(),
        "filed_end": _strict_date(
            _required(seed_contract, "filed_end", name="protocol historical_seed"),
            name="protocol historical_seed.filed_end",
        ).isoformat(),
        "selection_method": _strict_text(
            _required(seed_contract, "selection_method", name="protocol historical_seed"),
            name="protocol historical_seed.selection_method",
        ),
        "requested_cik_count": _strict_integer(
            _required(seed_contract, "requested_cik_count", name="protocol historical_seed"),
            name="protocol historical_seed.requested_cik_count",
            minimum=1,
        ),
    }

    preregistered_checks = {
        "universe": (
            protocol_values["anchor_period_end"] == _M6_ANCHOR_PERIOD_END.isoformat()
            and protocol_values["anchor_as_of"] == _M6_ANCHOR_AS_OF.isoformat()
            and protocol_values["analysis_start"] == _M6_ANALYSIS_START.isoformat()
            and protocol_values["minimum_assets_usd"] == _M6_MINIMUM_ASSETS_USD
        ),
        "time_cutoff": protocol_values["time_cutoff"] == _M6_TIME_CUTOFF.isoformat(),
        "company_split": (
            protocol_values["company_modulus"] == _M6_COMPANY_MODULUS
            and protocol_values["company_remainder"] == _M6_COMPANY_REMAINDER
        ),
        "minimum_required": protocol_values["minimum_required"] == _M6_MINIMUM_REQUIRED,
        "metric_roles": (
            protocol_values["metric_primary"] == "mae"
            and protocol_values["metric_secondary"] == "median_absolute_error"
            and protocol_values["metric_reference"] == "rmse"
        ),
        "adjacent_quarter_contract": (
            protocol_values["minimum_gap_days"] == _MINIMUM_GAP_DAYS
            and protocol_values["maximum_gap_days"] == _MAXIMUM_GAP_DAYS
        ),
        "availability_calendar": (
            protocol_values["availability_calendar"] == "us_federal_holidays"
        ),
        "holiday_manifest_coverage": (
            protocol_values["holiday_manifest_start"] == _M6_HOLIDAY_COVERAGE_START.isoformat()
            and protocol_values["holiday_manifest_end"] == _M6_HOLIDAY_COVERAGE_END.isoformat()
        ),
        "assets_contract": (
            protocol_values["concept"] == "us-gaap/Assets" and protocol_values["unit"] == "USD"
        ),
        "historical_seed": (
            seed_values["source_url"] == _M6_SEED_SOURCE_URL
            and tuple(seed_values["forms"]) == _M6_SEED_FORMS
            and seed_values["filed_start"] == _M6_SEED_FILED_START.isoformat()
            and seed_values["filed_end"] == _M6_SEED_FILED_END.isoformat()
            and seed_values["selection_method"] == _M6_SEED_SELECTION_METHOD
            and seed_values["requested_cik_count"] == _M6_SEED_CIK_COUNT
        ),
    }

    artifact_panel_contract = _require_mapping(
        _required(artifact, "panel_contract", name="artifact"), name="panel_contract"
    )
    artifact_universe = _require_mapping(
        _required(panel, "universe", name="panel"), name="panel.universe"
    )
    artifact_spec = _require_mapping(
        _required(artifact_universe, "spec", name="panel.universe"),
        name="panel.universe.spec",
    )
    holiday = source_provenance.get("holiday_manifest")
    seed_summary = source_provenance.get("seed_manifest")
    seed_matches = False
    if isinstance(seed_summary, Mapping):
        seed_matches = all(
            seed_summary.get(name) == expected
            for name, expected in {
                "source_url": seed_values["source_url"],
                "forms": seed_values["forms"],
                "filed_start": seed_values["filed_start"],
                "filed_end": seed_values["filed_end"],
                "selection_method": seed_values["selection_method"],
                "selected_cik_count": seed_values["requested_cik_count"],
            }.items()
        )
    baseline_parameters = _require_mapping(
        _required(baseline, "parameters", name="baseline audit"),
        name="baseline audit.parameters",
    )
    required_holiday_start = date.fromisoformat(protocol_values["holiday_manifest_start"])
    required_holiday_end = date.fromisoformat(protocol_values["holiday_manifest_end"])
    holiday_coverage = {
        "required_start": required_holiday_start.isoformat(),
        "required_end": required_holiday_end.isoformat(),
        "manifest_start": holiday.get("start") if isinstance(holiday, Mapping) else None,
        "manifest_end": holiday.get("end") if isinstance(holiday, Mapping) else None,
        "covers_protocol": False,
        "panel_dates_within_manifest": False,
        "observed_panel_date_minimum": None,
        "observed_panel_date_maximum": None,
    }
    manifest_start: date | None = None
    manifest_end: date | None = None
    if isinstance(holiday, Mapping) and holiday.get("matches_artifact"):
        try:
            manifest_start = date.fromisoformat(str(holiday.get("start")))
            manifest_end = date.fromisoformat(str(holiday.get("end")))
        except ValueError:
            pass
        else:
            holiday_coverage["covers_protocol"] = bool(
                required_holiday_start <= required_holiday_end
                and manifest_start <= required_holiday_start
                and manifest_end >= required_holiday_end
            )
    required_analysis_start = date.fromisoformat(protocol_values["analysis_start"])
    panel_rows = _require_list(_required(panel, "rows", name="panel"), name="panel.rows")
    panel_dates = [
        parsed
        for row_index, row_value in enumerate(panel_rows)
        for column in _DATE_COLUMNS
        if (
            parsed := _try_date(
                _require_mapping(row_value, name=f"panel.rows[{row_index}]").get(column)
            )
        )
        is not None
    ]
    if panel_dates:
        holiday_coverage["observed_panel_date_minimum"] = min(panel_dates).isoformat()
        holiday_coverage["observed_panel_date_maximum"] = max(panel_dates).isoformat()
        holiday_coverage["panel_dates_within_manifest"] = bool(
            manifest_start is not None
            and manifest_end is not None
            and all(manifest_start <= value <= manifest_end for value in panel_dates)
        )
    analysis_start_violations = sum(
        target_period < required_analysis_start
        for row_index, row_value in enumerate(panel_rows)
        if (
            target_period := _try_date(
                _require_mapping(row_value, name=f"panel.rows[{row_index}]").get(
                    "target_period_end"
                )
            )
        )
        is not None
    )
    artifact_match_checks = {
        "baseline_parameters": all(
            baseline_parameters.get(name) == expected
            for name, expected in {
                "time_cutoff": protocol_values["time_cutoff"],
                "company_modulus": protocol_values["company_modulus"],
                "company_remainder": protocol_values["company_remainder"],
                "minimum_required": protocol_values["minimum_required"],
            }.items()
        ),
        "panel_contract": (
            artifact_panel_contract.get("minimum_gap_days") == protocol_values["minimum_gap_days"]
            and artifact_panel_contract.get("maximum_gap_days")
            == protocol_values["maximum_gap_days"]
        ),
        "universe_contract": (
            artifact_spec.get("anchor_period_end") == protocol_values["anchor_period_end"]
            and artifact_spec.get("anchor_as_of") == protocol_values["anchor_as_of"]
            and artifact_spec.get("analysis_start") == protocol_values["analysis_start"]
            and isinstance(artifact_spec.get("minimum_assets_usd"), (int, float))
            and not isinstance(artifact_spec.get("minimum_assets_usd"), bool)
            and math.isclose(
                float(artifact_spec["minimum_assets_usd"]),
                protocol_values["minimum_assets_usd"],
                rel_tol=1e-12,
                abs_tol=1e-9,
            )
        ),
        "panel_analysis_window": analysis_start_violations == 0,
        "historical_seed": seed_matches,
        "holiday_manifest_coverage": (
            holiday_coverage["covers_protocol"] and holiday_coverage["panel_dates_within_manifest"]
        ),
    }
    digest = sha256(payload).hexdigest()
    provenance_matches = bool(
        recorded is not None
        and recorded["sha256"] == digest
        and recorded["schema_version"] == _PROTOCOL_SCHEMA
    )
    strict = bool(
        provenance_matches
        and all(preregistered_checks.values())
        and all(artifact_match_checks.values())
    )
    mismatches = [
        *(f"preregistered.{name}" for name, passed in preregistered_checks.items() if not passed),
        *(f"artifact.{name}" for name, passed in artifact_match_checks.items() if not passed),
    ]
    if not provenance_matches:
        mismatches.append("artifact.protocol_provenance")
    return {
        "mode": "external_protocol",
        "matches_artifact": strict,
        "strict_gate_accepted": strict,
        "external_protocol": {
            "path": str(resolved),
            "sha256": digest,
            "schema_version": protocol["schema_version"],
        },
        "artifact_provenance": (
            {
                **recorded,
                "path_matches_external": (
                    Path(recorded["path"]).expanduser().resolve() == resolved
                ),
                "content_identity_matches": provenance_matches,
            }
            if recorded is not None
            else None
        ),
        "preregistered_checks": preregistered_checks,
        "artifact_match_checks": artifact_match_checks,
        "analysis_window": {
            "required_analysis_start": required_analysis_start.isoformat(),
            "rows_before_analysis_start": analysis_start_violations,
        },
        "holiday_coverage": holiday_coverage,
        "mismatches": sorted(mismatches),
    }


def _minus_one_year(value: date) -> date:
    try:
        return value.replace(year=value.year - 1)
    except ValueError:
        return value.replace(year=value.year - 1, day=28)


def _metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, Any]:
    errors = [
        actual_value - predicted_value
        for actual_value, predicted_value in zip(actual, predicted, strict=True)
    ]
    absolute = [abs(value) for value in errors]
    count = len(errors)
    return {
        "n": count,
        "mae": math.fsum(absolute) / count,
        "median_absolute_error": float(statistics.median(absolute)),
        "rmse": math.sqrt(math.fsum(value * value for value in errors) / count),
    }


def _baseline_predictions(
    train: Sequence[_BaselineRow],
    evaluation: Sequence[_BaselineRow],
    name: str,
) -> list[float]:
    predictions: list[float] = []
    for row in evaluation:
        known = [candidate for candidate in train if candidate.target_available_date < row.known_at]
        if name == "zero" or not known:
            predictions.append(0.0)
        elif name == "pooled_drift":
            predictions.append(
                math.fsum(candidate.target_log_change for candidate in known) / len(known)
            )
        elif name == "company_mean":
            company = [candidate for candidate in known if candidate.cik == row.cik]
            reference = company or known
            predictions.append(
                math.fsum(candidate.target_log_change for candidate in reference) / len(reference)
            )
        elif name == "seasonal":
            prior_period = _minus_one_year(row.target_period_end)
            seasonal = [
                candidate
                for candidate in known
                if candidate.cik == row.cik and candidate.target_period_end == prior_period
            ]
            predictions.append(seasonal[-1].target_log_change if seasonal else 0.0)
        else:  # pragma: no cover - names are fixed above
            raise RuntimeError(f"unknown baseline {name!r}")
    return predictions


def _stored_splits(baseline: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    values = _require_list(_required(baseline, "splits", name="baseline"), name="baseline.splits")
    result: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(values):
        split = _require_mapping(value, name=f"baseline.splits[{index}]")
        name = _required(split, "name", name=f"baseline.splits[{index}]")
        if name not in _SPLIT_NAMES:
            raise ArtifactAuditError(f"unknown baseline split name: {name!r}")
        if name in result:
            raise ArtifactAuditError(f"duplicate baseline split name: {name!r}")
        result[name] = split
    missing = sorted(set(_SPLIT_NAMES).difference(result))
    if missing:
        raise ArtifactAuditError(f"baseline.splits is missing required splits: {missing}")
    return result


def _metric_matches(stored: Mapping[str, Any], expected: Mapping[str, Any], *, name: str) -> bool:
    stored_n = _strict_integer(_required(stored, "n", name=name), name=f"{name}.n", minimum=0)
    if stored_n != expected["n"]:
        return False
    for metric_name in _METRIC_NAMES[1:]:
        stored_value = _strict_number(
            _required(stored, metric_name, name=name), name=f"{name}.{metric_name}"
        )
        if not math.isclose(
            stored_value,
            float(expected[metric_name]),
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            return False
    return True


def _audit_baselines(
    baseline: Mapping[str, Any],
    rows: Sequence[_BaselineRow],
    *,
    total_panel_rows: int,
) -> tuple[dict[str, Any], bool]:
    cutoff = _strict_date(
        _required(baseline, "time_cutoff", name="baseline"), name="baseline.time_cutoff"
    )
    modulus = _strict_integer(
        _required(baseline, "company_modulus", name="baseline"),
        name="baseline.company_modulus",
        minimum=2,
    )
    remainder = _strict_integer(
        _required(baseline, "company_remainder", name="baseline"),
        name="baseline.company_remainder",
        minimum=0,
    )
    if remainder >= modulus:
        raise ArtifactAuditError("baseline.company_remainder must be below company_modulus")
    minimum_required = _strict_integer(
        _required(baseline, "minimum_required", name="baseline"),
        name="baseline.minimum_required",
        minimum=1,
    )
    stored_counts = _require_mapping(
        _required(baseline, "split_counts", name="baseline"), name="baseline.split_counts"
    )
    stored_split_map = _stored_splits(baseline)
    ordered = sorted(
        rows, key=lambda row: (row.target_available_date, row.cik, row.target_period_end)
    )
    recomputable = len(ordered) == total_panel_rows

    time_rows = [row for row in ordered if row.target_available_date >= cutoff]
    company_rows = [row for row in ordered if row.cik % modulus == remainder]
    both_rows = [
        row
        for row in ordered
        if row.target_available_date >= cutoff and row.cik % modulus == remainder
    ]
    counts = {
        "total_rows": total_panel_rows,
        "time_holdout_rows": len(time_rows),
        "company_holdout_rows": len(company_rows),
        "both_holdout_rows": len(both_rows),
        "minimum_required": minimum_required,
        "accepted": recomputable and len(both_rows) >= minimum_required,
    }
    stored_count_values = {
        key: (
            _strict_bool(
                _required(stored_counts, key, name="baseline.split_counts"),
                name=f"baseline.split_counts.{key}",
            )
            if key == "accepted"
            else _strict_integer(
                _required(stored_counts, key, name="baseline.split_counts"),
                name=f"baseline.split_counts.{key}",
                minimum=0,
            )
        )
        for key in counts
    }
    split_count_mismatches = [key for key in counts if counts[key] != stored_count_values[key]]
    stored_top_accepted = _strict_bool(
        _required(baseline, "accepted", name="baseline"), name="baseline.accepted"
    )

    split_definitions = {
        "time": (
            time_rows,
            [row for row in ordered if row.target_available_date < cutoff],
        ),
        "company": (
            company_rows,
            [row for row in ordered if row.cik % modulus != remainder],
        ),
        "both": (
            both_rows,
            [
                row
                for row in ordered
                if row.target_available_date < cutoff and row.cik % modulus != remainder
            ],
        ),
    }
    split_reports: dict[str, Any] = {}
    mismatched_metrics: list[str] = []
    split_metadata_mismatches: list[str] = []
    split_coverage_mismatches: list[str] = []
    for split_name in _SPLIT_NAMES:
        evaluation, train = split_definitions[split_name]
        expected_metrics: dict[str, Any] = {}
        if recomputable and evaluation:
            actual = [row.target_log_change for row in evaluation]
            for baseline_name in _BASELINE_NAMES:
                prediction = _baseline_predictions(train, evaluation, baseline_name)
                expected_metrics[baseline_name] = _metrics(actual, prediction)

        stored_split = stored_split_map[split_name]
        stored_n = _strict_integer(
            _required(stored_split, "n", name=f"baseline split {split_name}"),
            name=f"baseline split {split_name}.n",
            minimum=0,
        )
        stored_accepted = _strict_bool(
            _required(stored_split, "accepted", name=f"baseline split {split_name}"),
            name=f"baseline split {split_name}.accepted",
        )
        expected_coverage = {
            "training_n": len(train),
            "holdout_company_count": len({row.cik for row in evaluation}),
            "holdout_target_available_date_count": len(
                {row.target_available_date for row in evaluation}
            ),
            "training_company_count": len({row.cik for row in train}),
            "training_target_available_date_count": len(
                {row.target_available_date for row in train}
            ),
        }
        stored_coverage = {
            name: _strict_integer(
                _required(stored_split, name, name=f"baseline split {split_name}"),
                name=f"baseline split {split_name}.{name}",
                minimum=0,
            )
            for name in expected_coverage
        }
        split_coverage_mismatches.extend(
            f"{split_name}.{name}"
            for name in expected_coverage
            if stored_coverage[name] != expected_coverage[name]
        )
        expected_accepted = bool(
            recomputable and len(evaluation) >= minimum_required and len(train) > 0
        )
        if stored_n != len(evaluation) or stored_accepted != expected_accepted:
            split_metadata_mismatches.append(split_name)

        stored_metrics = _require_mapping(
            _required(stored_split, "metrics", name=f"baseline split {split_name}"),
            name=f"baseline split {split_name}.metrics",
        )
        if set(stored_metrics) != set(expected_metrics):
            mismatched_metrics.append(f"{split_name}.*")
        else:
            for baseline_name, expected in expected_metrics.items():
                stored_metric = _require_mapping(
                    stored_metrics[baseline_name],
                    name=f"baseline split {split_name}.{baseline_name}",
                )
                if not _metric_matches(
                    stored_metric,
                    expected,
                    name=f"baseline split {split_name}.{baseline_name}",
                ):
                    mismatched_metrics.append(f"{split_name}.{baseline_name}")
        split_reports[split_name] = {
            "n": len(evaluation),
            **expected_coverage,
            "accepted": expected_accepted,
            "metrics": expected_metrics,
        }

    strict_both_gate = bool(split_reports["both"]["accepted"])
    if stored_top_accepted != strict_both_gate:
        split_count_mismatches.append("baseline.accepted")
    matches = bool(
        recomputable
        and not split_count_mismatches
        and not split_metadata_mismatches
        and not split_coverage_mismatches
        and not mismatched_metrics
    )
    return (
        {
            "parameters": {
                "time_cutoff": cutoff.isoformat(),
                "company_modulus": modulus,
                "company_remainder": remainder,
                "minimum_required": minimum_required,
            },
            "recomputable": recomputable,
            "unclassifiable_rows": total_panel_rows - len(ordered),
            "split_counts": counts,
            "splits": split_reports,
            "matches_artifact": matches,
            "split_count_mismatches": split_count_mismatches,
            "split_metadata_mismatches": split_metadata_mismatches,
            "split_coverage_mismatches": split_coverage_mismatches,
            "mismatched_metrics": mismatched_metrics,
        },
        strict_both_gate,
    )


def audit_artifact(path: Path, *, protocol_path: Path | None = None) -> dict[str, Any]:
    """Return a deterministic quality report for one derived B9 artifact."""

    resolved, payload, artifact = _load_artifact(path)
    panel = _require_mapping(artifact["panel"], name="panel")
    profile, baseline_rows = _profile_panel(panel)
    universe = _audit_universe(panel, profile)
    stored_quality = _audit_stored_quality(panel, profile)
    source_provenance = _audit_source_provenance(artifact, panel, profile)
    baseline, strict_sample_gate = _audit_baselines(
        _require_mapping(artifact["baseline"], name="baseline"),
        baseline_rows,
        total_panel_rows=profile["row_count"],
    )
    protocol = _audit_protocol(
        artifact,
        panel,
        baseline,
        source_provenance,
        protocol_path,
    )
    network_free = artifact["network_access"] is False
    checks = {
        "network_free_artifact": network_free,
        "panel_columns": profile["columns_match_contract"],
        "panel_nonempty": profile["row_count"] > 0,
        "panel_complete": profile["null_cells"] == 0,
        "valid_cik": profile["invalid_cik_rows"] == 0,
        "valid_dates": profile["invalid_date_rows"] == 0,
        "finite_numeric_values": profile["invalid_numeric_rows"] == 0,
        "unique_grain": (profile["duplicate_keys"] == 0 and profile["duplicate_target_keys"] == 0),
        "positive_assets": profile["nonpositive_asset_rows"] == 0,
        "target_log_change_consistent": profile["target_log_change_mismatch_rows"] == 0,
        "adjacent_quarter_gap": profile["gap"]["invalid_rows"] == 0,
        "period_order": profile["period_order_violations"] == 0,
        "pit_order": (
            profile["known_at_mismatch_rows"] == 0
            and profile["availability_order_violations"] == 0
            and profile["previous_availability_order_violations"] == 0
            and profile["target_availability_order_violations"] == 0
        ),
        "universe_consistent": all(
            universe[name]
            for name in (
                "eligible_ciks_unique",
                "selected_rows_match",
                "candidate_rows_cover_selection",
                "panel_ciks_within_cohort",
            )
        ),
        "source_provenance_consistent": source_provenance["matches_artifact"],
        "protocol_consistent": protocol["matches_artifact"],
        "stored_panel_quality_consistent": stored_quality["matches_artifact"],
        "split_and_baseline_recomputation": baseline["matches_artifact"],
    }
    accepted = all(checks.values())
    warnings: list[str] = []
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        warnings.append(f"failed integrity checks: {', '.join(failed)}")
    if stored_quality["source_excluded_invalid_gap_rows"]:
        warnings.append(
            "the source builder excluded non-adjacent observations; inspect its gap diagnostics"
        )
    if not source_provenance["strict_gate_accepted"]:
        warnings.append("strict historical-seed provenance gate is not met")
    if not protocol["strict_gate_accepted"]:
        warnings.append("strict pre-registered M6 protocol gate is not met")
    if not strict_sample_gate:
        warnings.append("strict company-by-time sample-size gate is not met")
    return {
        "schema_version": _REPORT_SCHEMA,
        "source": {
            "path": str(resolved),
            "sha256": sha256(payload).hexdigest(),
            "artifact_schema_version": artifact["schema_version"],
        },
        "panel": profile,
        "universe": universe,
        "source_provenance": source_provenance,
        "protocol": protocol,
        "stored_quality": stored_quality,
        "baseline": baseline,
        "checks": checks,
        "accepted": accepted,
        "strict_provenance_accepted": source_provenance["strict_gate_accepted"],
        "strict_protocol_accepted": protocol["strict_gate_accepted"],
        "strict_sample_gate_accepted": strict_sample_gate,
        "modeling_gate_accepted": bool(
            accepted
            and source_provenance["strict_gate_accepted"]
            and protocol["strict_gate_accepted"]
            and strict_sample_gate
        ),
        "warnings": warnings,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="derived b9-sec-panel-v1 JSON artifact")
    parser.add_argument(
        "--protocol",
        type=Path,
        help="trusted pre-registered b9-m6-protocol-v1 JSON used for the strict M6 gate",
    )
    parser.add_argument(
        "--output",
        "--json-output",
        dest="output",
        type=Path,
        help="optional path for the compact quality report",
    )
    parser.add_argument(
        "--require-modeling-gate",
        action="store_true",
        help="return exit status 1 unless integrity, provenance, protocol, and sample gates pass",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = audit_artifact(args.artifact, protocol_path=args.protocol)
    except (ArtifactAuditError, FileNotFoundError, OSError) as error:
        print(f"B9 artifact audit error: {error}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if args.require_modeling_gate and not report["modeling_gate_accepted"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
