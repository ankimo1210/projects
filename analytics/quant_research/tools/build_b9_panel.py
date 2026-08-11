"""Build an auditable B9 panel from an offline SEC cache.

The command is deliberately network-free.  It converts the raw cache into a
compact derived artifact containing the fixed-anchor cohort, point-in-time
panel rows, quality diagnostics, and the pre-registered baseline split audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd

TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parent
sys.path.insert(0, str(PROJECT / "src"))

from quant_textbook.sec_cache_integrity import (
    B9BatchCacheIntegrity,
    validate_sec_b9_batch_cache,
)
from quant_textbook.sec_panel import (
    B9BaselineAudit,
    B9Panel,
    build_b9_panel,
    evaluate_b9_baselines,
)
from quant_textbook.sec_pit import PITUniverseSpec

_DATE_COLUMNS = (
    "previous_period_end",
    "target_period_end",
    "previous_available_date",
    "target_available_date",
    "known_at",
)


def _iso_date(value: str, *, name: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"{name} must be an ISO date (YYYY-MM-DD)") from error


def _spec_payload(spec: PITUniverseSpec) -> dict[str, Any]:
    return {
        "anchor_period_end": spec.anchor_period_end.isoformat(),
        "anchor_as_of": spec.anchor_as_of.isoformat(),
        "analysis_start": spec.analysis_start.isoformat(),
        "minimum_assets_usd": spec.minimum_assets_usd,
    }


def _panel_payload(panel: B9Panel) -> dict[str, Any]:
    frame = panel.frame.copy()
    for column in _DATE_COLUMNS:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="raise").dt.strftime("%Y-%m-%d")
    return {
        "columns": list(frame.columns),
        "rows": frame.to_dict(orient="records"),
        "quality": asdict(panel.quality),
        "universe": {
            "spec": _spec_payload(panel.universe.spec),
            "eligible_ciks": list(panel.universe.eligible_ciks),
            "candidate_rows": panel.universe.candidate_rows,
            "selected_rows": panel.universe.selected_rows,
        },
    }


def _baseline_payload(audit: B9BaselineAudit) -> dict[str, Any]:
    return {
        "time_cutoff": audit.time_cutoff.isoformat(),
        "company_modulus": audit.company_modulus,
        "company_remainder": audit.company_remainder,
        "minimum_required": audit.minimum_required,
        "accepted": audit.accepted,
        "split_counts": asdict(audit.split_counts),
        "splits": [
            {
                "name": split.name,
                "n": split.n,
                "training_n": split.training_n,
                "holdout_company_count": split.holdout_company_count,
                "holdout_target_available_date_count": split.holdout_target_available_date_count,
                "training_company_count": split.training_company_count,
                "training_target_available_date_count": split.training_target_available_date_count,
                "accepted": split.accepted,
                "metrics": {name: asdict(metric) for name, metric in split.metrics.items()},
            }
            for split in audit.splits
        ],
    }


def _normalize_cik(value: Any) -> str:
    digits = str(value).strip().lstrip("0") or "0"
    if not digits.isdigit() or not 1 <= int(digits) <= 9_999_999_999:
        raise ValueError(f"invalid CIK in provenance: {value!r}")
    return digits.zfill(10)


def _canonical_cik_sha256(ciks: list[str]) -> str:
    normalized = tuple(sorted({_normalize_cik(cik) for cik in ciks}))
    if not normalized:
        raise ValueError("provenance must contain at least one CIK")
    return sha256(("\n".join(normalized) + "\n").encode("ascii")).hexdigest()


def _read_json_object(path: Path, *, name: str) -> tuple[bytes, dict[str, Any]]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{name} does not exist: {resolved}")
    payload = resolved.read_bytes()
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} must be valid JSON: {resolved}") from error
    if not isinstance(decoded, dict):
        raise ValueError(f"{name} must be a JSON object: {resolved}")
    return payload, decoded


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _required(value: Mapping[str, Any], key: str, *, name: str) -> Any:
    if key not in value:
        raise ValueError(f"{name} is missing required field {key!r}")
    return value[key]


def _holiday_manifest_provenance(
    path: Path | None,
) -> tuple[tuple[date, ...] | None, dict[str, Any] | None]:
    if path is None:
        return None, None
    payload, decoded = _read_json_object(path, name="holiday manifest")
    if decoded.get("schema_version") != "b9-us-federal-holidays-v1":
        raise ValueError("holiday manifest has an unsupported schema_version")
    dates = _required(decoded, "holiday_dates", name="holiday manifest")
    if not isinstance(dates, list) or not dates:
        raise ValueError("holiday manifest holiday_dates must be a non-empty list")
    try:
        parsed = tuple(sorted({date.fromisoformat(str(value)) for value in dates}))
    except ValueError as error:
        raise ValueError("holiday manifest contains an invalid ISO date") from error
    if len(parsed) != len(dates):
        raise ValueError("holiday manifest holiday_dates must be sorted and unique")
    resolved = path.expanduser().resolve()
    return parsed, {
        "path": str(resolved),
        "sha256": sha256(payload).hexdigest(),
        "schema_version": decoded["schema_version"],
        "calendar": decoded.get("calendar"),
        "start": decoded.get("start"),
        "end": decoded.get("end"),
        "holiday_count": len(parsed),
    }


def _historical_seed_provenance(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload, decoded = _read_json_object(path, name="historical seed manifest")
    if decoded.get("schema_version") != "b9-historical-seed-v1":
        raise ValueError("historical seed manifest has an unsupported schema_version")
    records = _required(decoded, "selected_records", name="historical seed manifest")
    if not isinstance(records, list) or not records:
        raise ValueError("historical seed manifest selected_records must be a non-empty list")
    ciks: list[str] = []
    for index, record in enumerate(records):
        record_object = _mapping(record, name=f"historical seed manifest selected_records[{index}]")
        ciks.append(_normalize_cik(_required(record_object, "cik", name="selected record")))
    digest = _canonical_cik_sha256(ciks)
    selected_count = _required(decoded, "selected_cik_count", name="historical seed manifest")
    if (
        not isinstance(selected_count, int)
        or selected_count != len(ciks)
        or len(set(ciks)) != len(ciks)
    ):
        raise ValueError("historical seed manifest has inconsistent selected CIK records")
    persisted_digest = decoded.get("selected_cik_sha256")
    if persisted_digest != digest:
        raise ValueError("historical seed manifest selected CIK digest does not match records")
    resolved = path.expanduser().resolve()
    return {
        "path": str(resolved),
        "sha256": sha256(payload).hexdigest(),
        "schema_version": decoded["schema_version"],
        "master_index_sha256": _required(
            decoded, "master_index_sha256", name="historical seed manifest"
        ),
        "source_url": _required(decoded, "source_url", name="historical seed manifest"),
        "forms": _required(decoded, "forms", name="historical seed manifest"),
        "filed_start": _required(decoded, "filed_start", name="historical seed manifest"),
        "filed_end": _required(decoded, "filed_end", name="historical seed manifest"),
        "selection_method": _required(decoded, "selection_method", name="historical seed manifest"),
        "selected_cik_count": selected_count,
        "selected_cik_sha256": digest,
    }


def _protocol_provenance(path: Path | None) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if path is None:
        return None, None
    payload, decoded = _read_json_object(path, name="B9 M6 protocol")
    if decoded.get("schema_version") != "b9-m6-protocol-v1":
        raise ValueError("B9 M6 protocol has an unsupported schema_version")
    resolved = path.expanduser().resolve()
    return decoded, {
        "path": str(resolved),
        "sha256": sha256(payload).hexdigest(),
        "schema_version": decoded["schema_version"],
    }


def _cache_provenance(cache_root: Path) -> dict[str, Any]:
    """Record only local cache-manifest metadata, never raw SEC payloads."""

    root = cache_root.expanduser().resolve()
    batch_manifest = root / "batch_manifest.json"
    result: dict[str, Any] = {"cache_root": str(root), "batch_manifest": None}
    if not batch_manifest.is_file():
        return result
    payload, decoded = _read_json_object(batch_manifest, name="batch manifest")
    caches = _required(decoded, "caches", name="batch manifest")
    failures = _required(decoded, "failures", name="batch manifest")
    if not isinstance(caches, list) or not isinstance(failures, list):
        raise ValueError("batch manifest caches and failures must be lists")
    requested_ciks: list[str] = []
    for index, entry in enumerate([*caches, *failures]):
        entry_object = _mapping(entry, name=f"batch manifest entry {index}")
        requested_ciks.append(_normalize_cik(_required(entry_object, "cik", name="batch entry")))
    observed_digest = _canonical_cik_sha256(requested_ciks)
    if len(set(requested_ciks)) != len(requested_ciks):
        raise ValueError("batch manifest must not repeat a requested CIK")
    if decoded.get("requested_cik_count") != len(requested_ciks):
        raise ValueError("batch manifest requested_cik_count does not match caches and failures")
    persisted_digest = decoded.get("requested_cik_sha256")
    if persisted_digest is not None and persisted_digest != observed_digest:
        raise ValueError("batch manifest requested CIK digest does not match caches and failures")
    result["batch_manifest"] = {
        "path": str(batch_manifest),
        "sha256": sha256(payload).hexdigest(),
        "schema_version": decoded.get("schema_version"),
        "requested_cik_count": decoded.get("requested_cik_count"),
        "success_count": decoded.get("success_count"),
        "failure_count": decoded.get("failure_count"),
        "observed_requested_cik_count": len(requested_ciks),
        "observed_requested_cik_sha256": observed_digest,
    }
    return result


def _cache_integrity_payload(result: B9BatchCacheIntegrity | None) -> dict[str, Any] | None:
    if result is None:
        return None
    success_ciks = [int(path.name.removeprefix("CIK")) for path in result.success_cik_dirs]
    return {
        "accepted": result.accepted,
        "success_cik_count": result.success_cik_count,
        "success_cik_sha256": _canonical_cik_sha256([str(cik) for cik in success_ciks]),
        "success_ciks": success_ciks,
        "errors": list(result.errors),
    }


def _validate_protocol(
    protocol: Mapping[str, Any],
    *,
    spec: PITUniverseSpec,
    minimum_gap_days: int,
    maximum_gap_days: int,
    time_cutoff: date,
    company_modulus: int,
    company_remainder: int,
    minimum_required: int,
    seed_provenance: Mapping[str, Any] | None,
    holiday_provenance: Mapping[str, Any] | None,
    cache_provenance: Mapping[str, Any],
) -> None:
    """Reject an M6 run whose inputs differ from the reviewed protocol."""

    universe = _mapping(_required(protocol, "universe", name="B9 M6 protocol"), name="universe")
    expected_universe = {
        "anchor_period_end": spec.anchor_period_end.isoformat(),
        "anchor_as_of": spec.anchor_as_of.isoformat(),
        "analysis_start": spec.analysis_start.isoformat(),
        "minimum_assets_usd": spec.minimum_assets_usd,
    }
    for key, actual in expected_universe.items():
        if _required(universe, key, name="B9 M6 protocol universe") != actual:
            raise ValueError(f"B9 M6 protocol universe {key} does not match the command")
    if _required(universe, "concept", name="B9 M6 protocol universe") != "us-gaap/Assets":
        raise ValueError("B9 M6 protocol must use us-gaap/Assets")
    if _required(universe, "unit", name="B9 M6 protocol universe") != "USD":
        raise ValueError("B9 M6 protocol must use USD Assets")

    panel = _mapping(_required(protocol, "panel", name="B9 M6 protocol"), name="panel")
    if _required(panel, "minimum_gap_days", name="B9 M6 protocol panel") != minimum_gap_days:
        raise ValueError("B9 M6 protocol minimum_gap_days does not match the command")
    if _required(panel, "maximum_gap_days", name="B9 M6 protocol panel") != maximum_gap_days:
        raise ValueError("B9 M6 protocol maximum_gap_days does not match the command")
    if (
        _required(panel, "availability_calendar", name="B9 M6 protocol panel")
        != "us_federal_holidays"
    ):
        raise ValueError("B9 M6 protocol must use the U.S. federal holiday calendar")

    evaluation = _mapping(
        _required(protocol, "evaluation", name="B9 M6 protocol"), name="evaluation"
    )
    expected_evaluation = {
        "time_cutoff": time_cutoff.isoformat(),
        "company_modulus": company_modulus,
        "company_remainder": company_remainder,
        "minimum_required": minimum_required,
    }
    for key, actual in expected_evaluation.items():
        if _required(evaluation, key, name="B9 M6 protocol evaluation") != actual:
            raise ValueError(f"B9 M6 protocol evaluation {key} does not match the command")

    if seed_provenance is None or holiday_provenance is None:
        raise ValueError("B9 M6 protocol runs require seed and holiday manifests")
    seed = _mapping(_required(protocol, "historical_seed", name="B9 M6 protocol"), name="seed")
    expected_seed = {
        "source_url": seed_provenance["source_url"],
        "forms": seed_provenance["forms"],
        "filed_start": seed_provenance["filed_start"],
        "filed_end": seed_provenance["filed_end"],
        "selection_method": seed_provenance["selection_method"],
        "requested_cik_count": seed_provenance["selected_cik_count"],
    }
    for key, actual in expected_seed.items():
        if _required(seed, key, name="B9 M6 protocol historical_seed") != actual:
            raise ValueError(
                f"B9 M6 protocol historical_seed {key} does not match the seed manifest"
            )
    if holiday_provenance.get("calendar") != "pandas.USFederalHolidayCalendar":
        raise ValueError("holiday manifest must declare pandas.USFederalHolidayCalendar")
    try:
        manifest_start = date.fromisoformat(str(holiday_provenance["start"]))
        manifest_end = date.fromisoformat(str(holiday_provenance["end"]))
        required_start = date.fromisoformat(
            str(_required(panel, "holiday_manifest_start", name="B9 M6 protocol panel"))
        )
        required_end = date.fromisoformat(
            str(_required(panel, "holiday_manifest_end", name="B9 M6 protocol panel"))
        )
    except ValueError as error:
        raise ValueError("B9 M6 protocol and holiday manifest need ISO coverage dates") from error
    if manifest_start > required_start or manifest_end < required_end:
        raise ValueError("holiday manifest does not cover the B9 M6 protocol range")

    batch = cache_provenance.get("batch_manifest")
    if not isinstance(batch, Mapping):
        raise ValueError("B9 M6 protocol runs require a batch manifest")
    if batch.get("schema_version") != "b9-sec-batch-v1":
        raise ValueError("B9 M6 protocol run has an unsupported batch manifest")
    requested = batch.get("requested_cik_count")
    success = batch.get("success_count")
    failures = batch.get("failure_count")
    observed = batch.get("observed_requested_cik_count")
    if (
        not all(isinstance(value, int) for value in (requested, success, failures, observed))
        or requested != success + failures
        or requested != observed
    ):
        raise ValueError("batch manifest counts are inconsistent")
    if seed_provenance["selected_cik_count"] != observed or seed_provenance[
        "selected_cik_sha256"
    ] != batch.get("observed_requested_cik_sha256"):
        raise ValueError("historical seed cohort does not match the batch cache input")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--anchor-period-end",
        required=True,
        type=lambda value: _iso_date(value, name="anchor-period-end"),
    )
    parser.add_argument(
        "--anchor-as-of", required=True, type=lambda value: _iso_date(value, name="anchor-as-of")
    )
    parser.add_argument(
        "--analysis-start",
        required=True,
        type=lambda value: _iso_date(value, name="analysis-start"),
    )
    parser.add_argument("--minimum-assets-usd", type=float, default=100_000_000.0)
    parser.add_argument(
        "--time-cutoff", required=True, type=lambda value: _iso_date(value, name="time-cutoff")
    )
    parser.add_argument("--company-modulus", type=int, default=3)
    parser.add_argument("--company-remainder", type=int, default=0)
    parser.add_argument("--minimum-required", type=int, default=200)
    parser.add_argument("--minimum-gap-days", type=int, default=60)
    parser.add_argument("--maximum-gap-days", type=int, default=120)
    parser.add_argument(
        "--seed-manifest",
        type=Path,
        help="historical seed manifest; required together with --protocol for an M6 batch run",
    )
    parser.add_argument(
        "--holiday-manifest",
        type=Path,
        help="locked U.S. federal holiday manifest used for availability dates",
    )
    parser.add_argument(
        "--protocol",
        type=Path,
        help="reviewed B9 M6 protocol; batch-cache runs require this explicit contract",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    spec = PITUniverseSpec(
        anchor_period_end=args.anchor_period_end,
        anchor_as_of=args.anchor_as_of,
        analysis_start=args.analysis_start,
        minimum_assets_usd=args.minimum_assets_usd,
    )
    holiday_dates, holiday_provenance = _holiday_manifest_provenance(args.holiday_manifest)
    seed_provenance = _historical_seed_provenance(args.seed_manifest)
    protocol, protocol_provenance = _protocol_provenance(args.protocol)
    has_batch_manifest = (args.cache_root.expanduser().resolve() / "batch_manifest.json").is_file()
    cache_provenance = _cache_provenance(args.cache_root)
    if has_batch_manifest and protocol is None:
        raise ValueError("batch-cache runs require an explicit B9 M6 protocol")
    if protocol is not None:
        _validate_protocol(
            protocol,
            spec=spec,
            minimum_gap_days=args.minimum_gap_days,
            maximum_gap_days=args.maximum_gap_days,
            time_cutoff=args.time_cutoff,
            company_modulus=args.company_modulus,
            company_remainder=args.company_remainder,
            minimum_required=args.minimum_required,
            seed_provenance=seed_provenance,
            holiday_provenance=holiday_provenance,
            cache_provenance=cache_provenance,
        )
    panel = build_b9_panel(
        args.cache_root,
        spec,
        minimum_gap_days=args.minimum_gap_days,
        maximum_gap_days=args.maximum_gap_days,
        holiday_dates=holiday_dates,
    )
    baseline = evaluate_b9_baselines(
        panel.frame,
        time_cutoff=args.time_cutoff,
        company_modulus=args.company_modulus,
        company_remainder=args.company_remainder,
        minimum_required=args.minimum_required,
    )
    post_build_cache_provenance = _cache_provenance(args.cache_root)
    if post_build_cache_provenance != cache_provenance:
        raise ValueError("SEC batch provenance changed while the panel was being built")
    cache_integrity = panel.cache_integrity
    if has_batch_manifest:
        post_build_integrity = validate_sec_b9_batch_cache(args.cache_root)
        if not post_build_integrity.accepted:
            raise ValueError(
                "SEC batch cache integrity failed after the panel build: "
                + "; ".join(post_build_integrity.errors)
            )
        if _cache_integrity_payload(panel.cache_integrity) != _cache_integrity_payload(
            post_build_integrity
        ):
            raise ValueError("SEC batch cache integrity changed while the panel was being built")
        cache_integrity = post_build_integrity
    artifact = {
        "schema_version": "b9-sec-panel-v1",
        "network_access": False,
        "input_provenance": {
            **post_build_cache_provenance,
            "historical_seed_manifest": seed_provenance,
            "holiday_manifest": holiday_provenance,
            "protocol": protocol_provenance,
            "cache_integrity": _cache_integrity_payload(cache_integrity),
        },
        "panel_contract": {
            "minimum_gap_days": args.minimum_gap_days,
            "maximum_gap_days": args.maximum_gap_days,
        },
        "panel": _panel_payload(panel),
        "baseline": _baseline_payload(baseline),
    }
    output = args.output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output),
                "panel_rows": panel.quality.row_count,
                "eligible_ciks": list(panel.universe.eligible_ciks),
                "panel_accepted": panel.quality.accepted,
                "baseline_accepted": baseline.accepted,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
