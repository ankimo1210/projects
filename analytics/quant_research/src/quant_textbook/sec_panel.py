"""Offline SEC fundamentals panel construction for the B9 Core project.

The builder consumes only a local cache produced by
``tools/fetch_sec_b9_cache.py``.  It never calls the network and never uses a
current SEC Frame.  A panel row is one CIK and one adjacent pair of quarter
ends; ``known_at`` is the previous fact's availability date, while
``target_available_date`` is retained only for evaluation splitting.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from math import isfinite, log
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd

from .sec_cache_integrity import B9BatchCacheIntegrity, validate_sec_b9_batch_cache
from .sec_pit import (
    ALLOWED_FILING_FORMS,
    FundamentalsErrorMetrics,
    PITSplitAudit,
    PITUniverseSelection,
    PITUniverseSpec,
    audit_split_counts,
    build_filing_index,
    fundamentals_error_metrics,
    resolve_first_reported_vintages,
    select_fixed_anchor_cohort,
)

PANEL_COLUMNS = (
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
_SAFE_ARCHIVE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.json$")


class _IssuerContractExclusionError(ValueError):
    """A valid cache issuer that is outside B9 Core's declared concept/unit."""

    def __init__(self, *, cik: int, reason: str) -> None:
        self.cik = cik
        self.reason = reason
        super().__init__(f"CIK {cik:010d} is outside the B9 contract: {reason}")


@dataclass(frozen=True)
class B9PanelQuality:
    """Grain, completeness, and period-gap diagnostics for a panel."""

    source_cache_count: int
    excluded_issuer_ciks_by_reason: dict[str, tuple[int, ...]]
    row_count: int
    company_count: int
    duplicate_keys: int
    missing_by_column: dict[str, int]
    nonpositive_asset_rows: int
    excluded_nonpositive_asset_pair_count: int
    excluded_non_increasing_availability_pair_count: int
    availability_affected_company_count: int
    invalid_gap_rows: int
    gap_affected_company_count: int
    maximum_gap_days: int
    accepted: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class B9Panel:
    """An immutable contract around the derived panel frame."""

    frame: pd.DataFrame
    universe: PITUniverseSelection
    quality: B9PanelQuality
    cache_integrity: B9BatchCacheIntegrity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        missing = [column for column in PANEL_COLUMNS if column not in self.frame]
        if missing:
            raise ValueError(f"panel is missing columns: {missing}")


@dataclass(frozen=True)
class BaselineSplitResult:
    """Metric table for one pre-registered holdout split."""

    name: str
    n: int
    training_n: int
    holdout_company_count: int
    holdout_target_available_date_count: int
    training_company_count: int
    training_target_available_date_count: int
    metrics: dict[str, FundamentalsErrorMetrics]
    accepted: bool


@dataclass(frozen=True)
class B9BaselineAudit:
    """Baseline ladder results and the strict sample-size decision."""

    time_cutoff: date
    company_modulus: int
    company_remainder: int
    minimum_required: int
    split_counts: PITSplitAudit
    splits: tuple[BaselineSplitResult, ...]
    accepted: bool


def _cache_dirs(cache_root: Path) -> tuple[tuple[Path, ...], B9BatchCacheIntegrity | None]:
    root = cache_root.expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"SEC cache directory does not exist: {root}")
    batch_manifest_path = root / "batch_manifest.json"
    if batch_manifest_path.exists():
        integrity = validate_sec_b9_batch_cache(root)
        if not integrity.accepted:
            raise ValueError(
                "SEC batch cache integrity validation failed: " + "; ".join(integrity.errors)
            )
        directories = list(integrity.success_cik_dirs)
    else:
        directories = sorted(path for path in root.glob("CIK*") if path.is_dir())
        integrity = None
    if not directories:
        raise FileNotFoundError(f"no CIK cache directories below {root}")
    return tuple(directories), integrity


def _single_cache_file(cache_dir: Path, prefix: str) -> Path:
    matches = sorted(cache_dir.glob(f"{prefix}*.json"))
    matches = [path for path in matches if path.name != "manifest.json"]
    if len(matches) != 1:
        raise ValueError(f"expected one {prefix} JSON in {cache_dir}, found {matches}")
    return matches[0]


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"cache payload must be an object: {path}")
    return payload


def _cik_from_dir(cache_dir: Path) -> int:
    digits = cache_dir.name[3:]
    if not digits.isdigit() or int(digits) <= 0:
        raise ValueError(f"invalid CIK cache directory: {cache_dir.name}")
    return int(digits)


def _assets_facts(payload: Mapping[str, Any], *, cik: int) -> list[dict[str, Any]]:
    facts_root = payload.get("facts")
    if not isinstance(facts_root, Mapping):
        raise ValueError("Company Facts payload has an invalid facts object")
    us_gaap = facts_root.get("us-gaap")
    if us_gaap is None:
        raise _IssuerContractExclusionError(cik=cik, reason="missing_us_gaap_assets_usd")
    if not isinstance(us_gaap, Mapping):
        raise ValueError("Company Facts payload has an invalid us-gaap facts object")
    assets = us_gaap.get("Assets")
    if assets is None:
        raise _IssuerContractExclusionError(cik=cik, reason="missing_us_gaap_assets_usd")
    if not isinstance(assets, Mapping):
        raise ValueError("Company Facts payload has an invalid us-gaap/Assets concept")
    units = assets.get("units")
    if units is None or not isinstance(units, Mapping) or "USD" not in units:
        raise _IssuerContractExclusionError(cik=cik, reason="missing_us_gaap_assets_usd")
    if not isinstance(units["USD"], list):
        raise ValueError("us-gaap/Assets USD unit series must be a list")
    rows: list[dict[str, Any]] = []
    for item in units["USD"]:
        if not isinstance(item, Mapping):
            raise ValueError("Company Facts unit item must be an object")
        required = ("accn", "end", "val")
        missing = [field for field in required if item.get(field) in (None, "")]
        if missing:
            raise ValueError(f"Assets fact is missing required fields: {missing}")
        rows.append(
            {
                "cik": cik,
                "concept": "us-gaap/Assets",
                "unit": "USD",
                "start": item.get("start"),
                "end": item["end"],
                "val": item["val"],
                "accn": item["accn"],
            }
        )
    if not rows:
        raise _IssuerContractExclusionError(cik=cik, reason="missing_us_gaap_assets_usd")
    return rows


def _validate_payload_cik(payload: Mapping[str, Any], *, cik: int, label: str) -> None:
    """Reject a cached entity payload that contradicts its trusted CIK directory."""

    value = payload.get("cik")
    if value is None:
        return
    if isinstance(value, bool):
        raise ValueError(f"{label} CIK must be a positive integer when present")
    digits = str(value).strip().lstrip("0") or "0"
    if not digits.isdigit() or int(digits) <= 0:
        raise ValueError(f"{label} CIK must be a positive integer when present")
    if int(digits) != cik:
        raise ValueError(f"{label} CIK does not match its cache directory: {value!r} != {cik}")


def _advertised_archive_names(submissions: Mapping[str, Any]) -> tuple[str, ...]:
    filings = submissions.get("filings")
    if not isinstance(filings, Mapping):
        raise ValueError("submissions payload lacks a filings object")
    files = filings.get("files", [])
    if not isinstance(files, list):
        raise ValueError("submissions payload filings.files must be a list")
    names: list[str] = []
    for index, metadata in enumerate(files):
        if not isinstance(metadata, Mapping):
            raise ValueError(f"submissions archive metadata {index} must be an object")
        name = metadata.get("name")
        if not isinstance(name, str) or not _SAFE_ARCHIVE_NAME.fullmatch(name):
            raise ValueError(f"submissions archive metadata {index} has an unsafe name: {name!r}")
        names.append(name)
    if len(set(names)) != len(names):
        raise ValueError("submissions payload filings.files has duplicate archive names")
    return tuple(sorted(names))


def _validate_archives_for_cache(
    cache_dir: Path, submissions: Mapping[str, Any]
) -> tuple[Path, ...]:
    """Require exact parity between a submissions response and its cached archives."""

    expected_names = set(_advertised_archive_names(submissions))
    archive_paths = tuple(sorted(cache_dir.glob("*-submissions-*.json")))
    actual_names = {path.name for path in archive_paths}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise ValueError(
            "cached submissions archives do not match filings.files "
            f"(missing={missing}, extra={extra})"
        )
    child_manifest = _read_json(cache_dir / "manifest.json")
    records = child_manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("CIK cache manifest files must be a list")
    listed_names = {
        record.get("name")
        for record in records
        if isinstance(record, Mapping) and isinstance(record.get("name"), str)
    }
    if not expected_names.issubset(listed_names):
        missing_from_manifest = sorted(expected_names - listed_names)
        raise ValueError(
            f"CIK cache manifest does not hash every advertised archive: {missing_from_manifest}"
        )
    return archive_paths


def _vintages_for_cache(
    cache_dir: Path,
    *,
    holiday_dates: tuple[date, ...] | None,
) -> tuple[dict[str, Any], ...]:
    cik = _cik_from_dir(cache_dir)
    submissions_path = _single_cache_file(cache_dir, "submissions_CIK")
    facts_path = _single_cache_file(cache_dir, "companyfacts_CIK")
    submissions = _read_json(submissions_path)
    _validate_payload_cik(submissions, cik=cik, label="submissions payload")
    filings = submissions.get("filings")
    if not isinstance(filings, Mapping) or not isinstance(filings.get("recent"), Mapping):
        raise ValueError(f"submissions payload lacks filings.recent: {submissions_path}")
    archive_paths = _validate_archives_for_cache(cache_dir, submissions)
    archives = [_read_json(path) for path in archive_paths]
    index = build_filing_index(filings["recent"], archives, cik=cik)
    company_facts = _read_json(facts_path)
    _validate_payload_cik(company_facts, cik=cik, label="Company Facts payload")
    facts = _assets_facts(company_facts, cik=cik)
    return resolve_first_reported_vintages(
        facts,
        index,
        holiday_dates=holiday_dates,
        allowed_forms=ALLOWED_FILING_FORMS,
    )


def _date_value(value: Any, *, name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError(f"{name} must be a valid date")
    return timestamp.normalize()


def _panel_quality(
    frame: pd.DataFrame,
    *,
    source_cache_count: int,
    excluded_issuer_ciks_by_reason: dict[str, tuple[int, ...]],
    invalid_gap_rows: int,
    gap_affected_ciks: set[int],
    maximum_gap_days: int,
    excluded_nonpositive_asset_pair_count: int,
    excluded_non_increasing_availability_pair_count: int,
    availability_affected_ciks: set[int],
) -> B9PanelQuality:
    missing_by_column = {
        column: int(frame[column].isna().sum()) for column in PANEL_COLUMNS if column in frame
    }
    duplicate_keys = int(
        frame.duplicated(subset=["cik", "previous_period_end", "target_period_end"]).sum()
    )
    nonpositive = int(
        ((frame["previous_assets_usd"] <= 0.0) | (frame["target_assets_usd"] <= 0.0)).sum()
    )
    warnings: list[str] = []
    if frame.empty:
        warnings.append("panel contains no adjacent positive Assets observations")
    if duplicate_keys:
        warnings.append("panel grain has duplicate CIK and adjacent-period keys")
    if invalid_gap_rows:
        warnings.append(
            "some non-adjacent observations were excluded by the 60--120 day quarter contract"
        )
    if excluded_issuer_ciks_by_reason:
        warnings.append(
            "some cached issuers are outside the declared us-gaap/Assets/USD B9 Core contract"
        )
    if excluded_nonpositive_asset_pair_count:
        warnings.append("some non-positive Assets pairs were excluded from the panel")
    if excluded_non_increasing_availability_pair_count:
        warnings.append(
            "some adjacent periods shared a filing availability date and were excluded from prediction"
        )
    accepted = bool(
        not frame.empty
        and duplicate_keys == 0
        and not any(missing_by_column.values())
        and nonpositive == 0
    )
    return B9PanelQuality(
        source_cache_count=source_cache_count,
        excluded_issuer_ciks_by_reason=excluded_issuer_ciks_by_reason,
        row_count=len(frame),
        company_count=int(frame["cik"].nunique()) if "cik" in frame else 0,
        duplicate_keys=duplicate_keys,
        missing_by_column=missing_by_column,
        nonpositive_asset_rows=nonpositive,
        excluded_nonpositive_asset_pair_count=excluded_nonpositive_asset_pair_count,
        excluded_non_increasing_availability_pair_count=(
            excluded_non_increasing_availability_pair_count
        ),
        availability_affected_company_count=len(availability_affected_ciks),
        invalid_gap_rows=invalid_gap_rows,
        gap_affected_company_count=len(gap_affected_ciks),
        maximum_gap_days=maximum_gap_days,
        accepted=accepted,
        warnings=tuple(warnings),
    )


def build_b9_panel(
    cache_root: Path,
    spec: PITUniverseSpec,
    *,
    minimum_gap_days: int = 60,
    maximum_gap_days: int = 120,
    holiday_dates: tuple[date, ...] | None = None,
) -> B9Panel:
    """Build a fixed-anchor Assets growth panel from offline CIK caches."""

    if not 1 <= minimum_gap_days <= maximum_gap_days:
        raise ValueError("period gap bounds must be positive and ordered")
    cache_dirs, cache_integrity = _cache_dirs(cache_root)
    vintages: list[dict[str, Any]] = []
    exclusions: dict[str, list[int]] = {}
    for cache_dir in cache_dirs:
        try:
            vintages.extend(_vintages_for_cache(cache_dir, holiday_dates=holiday_dates))
        except _IssuerContractExclusionError as error:
            exclusions.setdefault(error.reason, []).append(error.cik)
    excluded_issuer_ciks_by_reason = {
        reason: tuple(sorted(ciks)) for reason, ciks in sorted(exclusions.items())
    }
    universe = select_fixed_anchor_cohort(vintages, spec)
    selected = set(universe.eligible_ciks)
    if not selected:
        empty = pd.DataFrame(columns=PANEL_COLUMNS)
        return B9Panel(
            frame=empty,
            universe=universe,
            quality=_panel_quality(
                empty,
                source_cache_count=len(cache_dirs),
                excluded_issuer_ciks_by_reason=excluded_issuer_ciks_by_reason,
                invalid_gap_rows=0,
                gap_affected_ciks=set(),
                maximum_gap_days=0,
                excluded_nonpositive_asset_pair_count=0,
                excluded_non_increasing_availability_pair_count=0,
                availability_affected_ciks=set(),
            ),
            cache_integrity=cache_integrity,
        )

    by_cik: dict[int, list[dict[str, Any]]] = {}
    for row in vintages:
        if int(row["cik"]) in selected:
            by_cik.setdefault(int(row["cik"]), []).append(row)
    panel_rows: list[dict[str, Any]] = []
    invalid_gap_rows = 0
    gap_affected_ciks: set[int] = set()
    maximum_gap = 0
    excluded_nonpositive_asset_pair_count = 0
    excluded_non_increasing_availability_pair_count = 0
    availability_affected_ciks: set[int] = set()
    analysis_start = pd.Timestamp(spec.analysis_start)
    for cik, rows in sorted(by_cik.items()):
        ordered = sorted(
            rows, key=lambda row: (_date_value(row["end"], name="period end"), row["accn"])
        )
        by_period: dict[pd.Timestamp, dict[str, Any]] = {}
        for row in ordered:
            period_end = _date_value(row["end"], name="period end")
            if period_end in by_period:
                raise ValueError(
                    f"duplicate first-reported Assets period for CIK {cik}: {period_end.date()}"
                )
            by_period[period_end] = row
        observations = [(period, by_period[period]) for period in sorted(by_period)]
        for (previous_period, previous), (target_period, target) in pairwise(observations):
            gap_days = int((target_period - previous_period).days)
            maximum_gap = max(maximum_gap, gap_days)
            if not minimum_gap_days <= gap_days <= maximum_gap_days:
                invalid_gap_rows += 1
                gap_affected_ciks.add(cik)
                continue
            if target_period < analysis_start:
                continue
            previous_value = float(previous["value"])
            target_value = float(target["value"])
            if previous_value <= 0.0 or target_value <= 0.0:
                excluded_nonpositive_asset_pair_count += 1
                continue
            previous_available = pd.Timestamp(previous["availability_date"])
            target_available = pd.Timestamp(target["availability_date"])
            if previous_available <= previous_period:
                raise ValueError(
                    f"previous availability must follow its period end for CIK {cik} "
                    f"and period {previous_period.date()}"
                )
            if target_available <= target_period:
                raise ValueError(
                    f"target availability must follow its period end for CIK {cik} "
                    f"and period {target_period.date()}"
                )
            if target_available <= previous_available:
                excluded_non_increasing_availability_pair_count += 1
                availability_affected_ciks.add(cik)
                continue
            if not isfinite(previous_value) or not isfinite(target_value):
                raise ValueError("Assets values must be finite")
            panel_rows.append(
                {
                    "cik": cik,
                    "previous_period_end": previous_period.date().isoformat(),
                    "target_period_end": target_period.date().isoformat(),
                    "previous_assets_usd": previous_value,
                    "target_assets_usd": target_value,
                    "target_log_change": log(target_value / previous_value),
                    "previous_available_date": previous_available.date().isoformat(),
                    "target_available_date": target_available.date().isoformat(),
                    "known_at": previous_available.date().isoformat(),
                }
            )
    frame = pd.DataFrame(panel_rows, columns=PANEL_COLUMNS)
    if not frame.empty:
        frame = frame.sort_values(
            ["target_available_date", "cik", "target_period_end"]
        ).reset_index(drop=True)
        for column in (
            "previous_period_end",
            "target_period_end",
            "previous_available_date",
            "target_available_date",
            "known_at",
        ):
            frame[column] = pd.to_datetime(frame[column], errors="raise")
    quality = _panel_quality(
        frame,
        source_cache_count=len(cache_dirs),
        excluded_issuer_ciks_by_reason=excluded_issuer_ciks_by_reason,
        invalid_gap_rows=invalid_gap_rows,
        gap_affected_ciks=gap_affected_ciks,
        maximum_gap_days=maximum_gap,
        excluded_nonpositive_asset_pair_count=excluded_nonpositive_asset_pair_count,
        excluded_non_increasing_availability_pair_count=(
            excluded_non_increasing_availability_pair_count
        ),
        availability_affected_ciks=availability_affected_ciks,
    )
    return B9Panel(
        frame=frame,
        universe=universe,
        quality=quality,
        cache_integrity=cache_integrity,
    )


def _as_panel_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(frame, pd.DataFrame):
        raise TypeError("panel must be a pandas DataFrame")
    missing = [column for column in PANEL_COLUMNS if column not in frame]
    if missing:
        raise ValueError(f"panel is missing columns: {missing}")
    result = frame.copy()
    for column in (
        "previous_period_end",
        "target_period_end",
        "previous_available_date",
        "target_available_date",
        "known_at",
    ):
        result[column] = pd.to_datetime(result[column], errors="raise")
        if result[column].isna().any():
            raise ValueError(f"{column} must not be missing")
    if result.empty:
        raise ValueError("panel must contain at least one row")
    numeric_columns = ("cik", "previous_assets_usd", "target_assets_usd", "target_log_change")
    for column in numeric_columns:
        values = result[column].to_numpy(dtype=float)
        if not np.all(np.isfinite(values)):
            raise ValueError(f"{column} must be finite")
    if (result[["previous_assets_usd", "target_assets_usd"]] <= 0.0).any().any():
        raise ValueError("Assets values must be positive")
    if result.duplicated(subset=["cik", "previous_period_end", "target_period_end"]).any():
        raise ValueError("panel grain must be unique by CIK and adjacent periods")
    if not (result["previous_period_end"] < result["target_period_end"]).all():
        raise ValueError("target period must follow previous period")
    if not (result["target_available_date"] > result["known_at"]).all():
        raise ValueError("target availability must follow known_at")
    return result.sort_values(["target_available_date", "cik", "target_period_end"]).reset_index(
        drop=True
    )


def _known_training_rows(train: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    return train.loc[train["target_available_date"] < row["known_at"]]


def _predict_baseline(
    train: pd.DataFrame,
    evaluation: pd.DataFrame,
    name: Literal["zero", "pooled_drift", "seasonal", "company_mean"],
) -> np.ndarray:
    predictions: list[float] = []
    for _, row in evaluation.iterrows():
        known = _known_training_rows(train, row)
        if name == "zero" or known.empty:
            predictions.append(0.0)
            continue
        if name == "pooled_drift":
            predictions.append(float(known["target_log_change"].mean()))
            continue
        if name == "company_mean":
            company = known.loc[known["cik"] == row["cik"], "target_log_change"]
            predictions.append(
                float(company.mean())
                if not company.empty
                else float(known["target_log_change"].mean())
            )
            continue
        previous_period = row["target_period_end"] - pd.DateOffset(years=1)
        seasonal = known.loc[
            (known["cik"] == row["cik"]) & (known["target_period_end"] == previous_period),
            "target_log_change",
        ]
        predictions.append(float(seasonal.iloc[-1]) if not seasonal.empty else 0.0)
    return np.asarray(predictions, dtype=float)


def evaluate_b9_baselines(
    panel: pd.DataFrame,
    *,
    time_cutoff: date,
    company_modulus: int = 3,
    company_remainder: int = 0,
    minimum_required: int = 200,
) -> B9BaselineAudit:
    """Evaluate the four B9 baselines without using future targets."""

    frame = _as_panel_frame(panel)
    time_cutoff_timestamp = pd.Timestamp(time_cutoff)
    time_holdout = frame["target_available_date"] >= time_cutoff_timestamp
    company_holdout = frame["cik"].astype(int) % company_modulus == company_remainder
    split_definitions = (
        ("time", time_holdout, ~time_holdout),
        ("company", company_holdout, ~company_holdout),
        ("both", time_holdout & company_holdout, ~time_holdout & ~company_holdout),
    )
    split_rows: list[BaselineSplitResult] = []
    for name, holdout, train_mask in split_definitions:
        evaluation = frame.loc[holdout]
        train = frame.loc[train_mask]
        metrics: dict[str, FundamentalsErrorMetrics] = {}
        if not evaluation.empty:
            actual = evaluation["target_log_change"].to_numpy(dtype=float)
            for baseline_name in ("zero", "pooled_drift", "seasonal", "company_mean"):
                prediction = _predict_baseline(train, evaluation, baseline_name)
                metrics[baseline_name] = fundamentals_error_metrics(actual, prediction)
        split_rows.append(
            BaselineSplitResult(
                name=name,
                n=len(evaluation),
                training_n=len(train),
                holdout_company_count=int(evaluation["cik"].nunique()),
                holdout_target_available_date_count=int(
                    evaluation["target_available_date"].nunique()
                ),
                training_company_count=int(train["cik"].nunique()),
                training_target_available_date_count=int(train["target_available_date"].nunique()),
                metrics=metrics,
                accepted=len(evaluation) >= minimum_required and not train.empty,
            )
        )
    audit_rows = frame.loc[:, ["cik", "target_available_date"]].assign(
        target_avail=frame["target_available_date"].dt.date
    )[["cik", "target_avail"]]
    split_counts = audit_split_counts(
        audit_rows.to_dict("records"),
        time_cutoff=time_cutoff_timestamp.date(),
        company_modulus=company_modulus,
        company_remainder=company_remainder,
        minimum_required=minimum_required,
    )
    return B9BaselineAudit(
        time_cutoff=time_cutoff_timestamp.date(),
        company_modulus=company_modulus,
        company_remainder=company_remainder,
        minimum_required=minimum_required,
        split_counts=split_counts,
        splits=tuple(split_rows),
        accepted=next(result for result in split_rows if result.name == "both").accepted,
    )


__all__ = [
    "PANEL_COLUMNS",
    "B9BaselineAudit",
    "B9Panel",
    "B9PanelQuality",
    "BaselineSplitResult",
    "build_b9_panel",
    "evaluate_b9_baselines",
]
