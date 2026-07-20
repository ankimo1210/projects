from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from jhrmbs.artifacts import write_table
from jhrmbs.config import AppConfig
from jhrmbs.exceptions import SourceFormatError
from jhrmbs.features import build_features
from jhrmbs.ingest import historical_records, latest_manifest_path, load_manifest
from jhrmbs.metrics import (
    combine_competing_monthly_rates,
    cpr_to_psj_terminal,
    cpr_to_smm,
    factor_implied_total_smm,
)
from jhrmbs.paths import DataPaths
from jhrmbs.quality import validate_features, validate_panel
from jhrmbs.sources.external import (
    parse_boj_m3,
    parse_flat35_current,
    parse_mlit_housing_starts,
    parse_mof_jgb,
)
from jhrmbs.sources.jhf import parse_jhf_workbook
from jhrmbs.util import atomic_write_json, read_json, utc_now

LOGGER = logging.getLogger("jhrmbs.dataset")


def _object_path(config: AppConfig, record: dict[str, Any]) -> Path:
    path = config.data_root / str(record["object_path"])
    if not path.is_file():
        raise SourceFormatError(f"Raw object がありません: {path}")
    return path


def enrich_panel_metrics(panel: pd.DataFrame, *, seasoning_months: int = 60) -> pd.DataFrame:
    frame = panel.sort_values(["issue_id", "payment_month"]).copy()
    grouped = frame.groupby("issue_id", sort=False)
    previous_actual = grouped["actual_factor"].shift(1)
    previous_scheduled = grouped["scheduled_factor"].shift(1)
    first_in_issue = grouped.cumcount() == 0
    previous_actual = previous_actual.mask(first_in_issue, 1.0)
    previous_scheduled = previous_scheduled.mask(first_in_issue, 1.0)

    cpr_decimal = pd.to_numeric(frame["voluntary_cpr_pct"], errors="coerce") / 100.0
    voluntary_smm = cpr_to_smm(cpr_decimal.to_numpy())
    frame["voluntary_smm"] = voluntary_smm
    frame.loc[cpr_decimal.isna(), "voluntary_smm"] = np.nan
    frame["published_psj_terminal_pct"] = (
        cpr_to_psj_terminal(
            cpr_decimal.to_numpy(),
            pd.to_numeric(frame["wala_months"], errors="coerce").to_numpy(),
            seasoning_months=seasoning_months,
        )
        * 100.0
    )
    frame["implied_total_smm"] = factor_implied_total_smm(
        previous_actual.to_numpy(),
        pd.to_numeric(frame["actual_factor"], errors="coerce").to_numpy(),
        previous_scheduled.to_numpy(),
        pd.to_numeric(frame["scheduled_factor"], errors="coerce").to_numpy(),
    )
    long_rate = pd.to_numeric(frame["long_delinquency_pct_monthly"], errors="coerce") / 100.0
    other_rate = pd.to_numeric(frame["other_cancellation_pct_monthly"], errors="coerce") / 100.0
    combined = combine_competing_monthly_rates(
        frame["voluntary_smm"].fillna(0.0).to_numpy(),
        long_rate.fillna(0.0).to_numpy(),
        other_rate.fillna(0.0).to_numpy(),
    )
    all_components_known = frame["voluntary_smm"].notna() & long_rate.notna() & other_rate.notna()
    frame["combined_published_decrement_smm"] = combined
    frame.loc[~all_components_known, "combined_published_decrement_smm"] = np.nan
    frame["reconciliation_bps"] = (
        frame["implied_total_smm"] - frame["combined_published_decrement_smm"]
    ) * 10_000.0
    frame["actual_balance_jpy"] = frame["face_amount_jpy"] * frame["actual_factor"]
    frame["is_observed"] = frame["actual_factor"].notna()
    return frame.reset_index(drop=True)


def _latest_record(manifest: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    records = [
        record
        for record in manifest["records"]
        if record.get("source_id") == source_id and record.get("role") == "data"
    ]
    return records[-1] if records else None


def _parse_optional(
    config: AppConfig,
    manifest: dict[str, Any],
    source_id: str,
    parser: Callable[[Path], pd.DataFrame],
) -> pd.DataFrame:
    record = _latest_record(manifest, source_id)
    if record is None:
        LOGGER.warning("source not present in manifest: %s", source_id)
        return pd.DataFrame()
    return parser(_object_path(config, record))


def _parse_flat35_history(config: AppConfig) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for record in historical_records(config.data_root, "flat35_current"):
        try:
            parsed = parse_flat35_current(_object_path(config, record))
            parsed["source_sha256"] = record["sha256"]
            frames.append(parsed)
        except SourceFormatError as exc:
            LOGGER.warning("skipping FLAT35 snapshot: %s", exc)
    if not frames:
        return pd.DataFrame()
    official = pd.concat(frames, ignore_index=True).drop_duplicates("month", keep="last")
    manual_path = config.data_root / "raw" / "manual" / "mortgage_rates.csv"
    if manual_path.is_file():
        manual = pd.read_csv(manual_path)
        required = {"month", "mortgage_rate_mode_pct"}
        if not required.issubset(manual.columns):
            raise SourceFormatError(f"manual mortgage CSV requires: {sorted(required)}")
        manual["month"] = pd.to_datetime(manual["month"]).dt.to_period("M").dt.to_timestamp()
        if "mortgage_rate_definition" not in manual.columns:
            manual["mortgage_rate_definition"] = (
                manual["source_note"].astype(str)
                if "source_note" in manual.columns
                else "manual mortgage_rates.csv"
            )
        official = pd.concat([official, manual], ignore_index=True).drop_duplicates(
            "month", keep="last"
        )
    return official.sort_values("month").reset_index(drop=True)


def build_dataset(config: AppConfig, manifest_path: Path | None = None) -> dict[str, Path]:
    paths = DataPaths(config.data_root)
    paths.ensure()
    selected_manifest = manifest_path or latest_manifest_path(config.data_root)
    manifest = load_manifest(selected_manifest)

    issue_frames: list[pd.DataFrame] = []
    panel_frames: list[pd.DataFrame] = []
    skipped_sheets: list[dict[str, str]] = []
    for record in manifest["records"]:
        if record.get("source_id") != "jhf_monthly" or record.get("role") != "data":
            continue
        object_path = _object_path(config, record)
        if object_path.suffix.lower() not in {".xls", ".xlsx"}:
            continue
        parsed = parse_jhf_workbook(
            object_path,
            source_filename=str(record["original_filename"]),
            source_sha256=str(record["sha256"]),
        )
        if not parsed.issues.empty:
            issue_frames.append(parsed.issues)
            panel_frames.append(parsed.panel)
        for sheet in parsed.skipped_sheets:
            skipped_sheets.append({"file": str(record["original_filename"]), "sheet": sheet})
    if not issue_frames or not panel_frames:
        raise SourceFormatError("JHF回号シートを1件も解析できませんでした")

    issues = pd.concat(issue_frames, ignore_index=True).sort_values("issue_id")
    duplicate_issues = issues.duplicated("issue_id", keep=False)
    if duplicate_issues.any():
        conflicting = issues.loc[duplicate_issues, "issue_id"].unique().tolist()
        raise SourceFormatError(f"duplicate issue metadata: {conflicting[:10]}")
    panel = enrich_panel_metrics(
        pd.concat(panel_frames, ignore_index=True),
        seasoning_months=config.features.psj_seasoning_months,
    )
    panel_quality = validate_panel(panel)

    jgb = _parse_optional(config, manifest, "mof_jgb", parse_mof_jgb)
    mortgage = _parse_flat35_history(config)
    housing = _parse_optional(config, manifest, "mlit_housing_starts", parse_mlit_housing_starts)
    m3 = _parse_optional(config, manifest, "boj_m3", parse_boj_m3)
    features = build_features(
        panel,
        issues,
        jgb=jgb,
        mortgage_rates=mortgage,
        housing=housing,
        m3=m3,
        config=config.features,
    )
    feature_quality = validate_features(features)

    outputs = {
        "issues": paths.processed / "issues.parquet",
        "panel": paths.processed / "issue_month_panel.parquet",
        "jgb": paths.processed / "jgb_monthly.parquet",
        "mortgage_rates": paths.processed / "mortgage_rates_monthly.parquet",
        "housing": paths.processed / "housing_starts_monthly.parquet",
        "m3": paths.processed / "boj_m3_monthly.parquet",
        "features": paths.features / "model_features.parquet",
    }
    metadata: dict[str, Any] = {}
    for name, frame in (
        ("issues", issues),
        ("panel", panel),
        ("jgb", jgb),
        ("mortgage_rates", mortgage),
        ("housing", housing),
        ("m3", m3),
        ("features", features),
    ):
        metadata[name] = write_table(frame, outputs[name])

    quality_path = paths.processed / "data_quality_report.json"
    atomic_write_json(
        quality_path,
        {
            "generated_at": utc_now().isoformat(),
            "source_manifest": str(selected_manifest),
            "panel": panel_quality,
            "features": feature_quality,
            "skipped_sheets": skipped_sheets,
        },
    )
    lineage_path = paths.processed / "lineage.json"
    atomic_write_json(
        lineage_path,
        {
            "generated_at": utc_now().isoformat(),
            "source_manifest": str(selected_manifest),
            "source_snapshot_id": read_json(selected_manifest, {}).get("snapshot_id"),
            "feature_configuration": asdict(config.features),
            "artifacts": metadata,
            "transformations": [
                "discover header rows and canonicalize JHF column aliases",
                "normalize issue identifiers and Japanese dates",
                "preserve percent and factor units explicitly in column names",
                "derive SMM, instantaneous PSJ, factor-implied total decrement and reconciliation",
                "join external data at the configured publication lag",
                "lag all pool-state model features by one issue-month",
            ],
        },
    )
    outputs["quality"] = quality_path
    outputs["lineage"] = lineage_path
    LOGGER.info("built panel rows=%d issues=%d", len(panel), len(issues))
    return outputs
