from __future__ import annotations

import importlib.util
import json
import math
import sys
from copy import deepcopy
from dataclasses import asdict
from datetime import date, timedelta
from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from types import ModuleType

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from quant_textbook.sec_panel import evaluate_b9_baselines


def _load_tool() -> ModuleType:
    path = Path(__file__).parents[1] / "tools" / "audit_sec_b9_panel.py"
    spec = importlib.util.spec_from_file_location("audit_sec_b9_panel", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load B9 panel audit tool")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _artifact(
    *,
    ciks: tuple[int, ...] = (1, 2, 3),
    periods: tuple[date, ...] = (
        date(2016, 3, 31),
        date(2016, 6, 30),
        date(2016, 9, 30),
        date(2016, 12, 31),
        date(2017, 3, 31),
        date(2017, 6, 30),
    ),
    cutoff: date = date(2017, 2, 1),
    company_modulus: int = 2,
    company_remainder: int = 0,
    minimum_required: int = 1,
) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for company_index, cik in enumerate(ciks, start=1):
        assets = [100_000_000.0 + 5_000_000.0 * company_index]
        for index in range(1, len(periods)):
            assets.append(assets[-1] * (1.0 + 0.001 * company_index + 0.002 * index))
        for index, (previous_period, target_period) in enumerate(pairwise(periods)):
            previous_available = previous_period + timedelta(days=40 + cik % 5)
            target_available = target_period + timedelta(days=40 + cik % 5)
            rows.append(
                {
                    "cik": cik,
                    "previous_period_end": previous_period.isoformat(),
                    "target_period_end": target_period.isoformat(),
                    "previous_assets_usd": assets[index],
                    "target_assets_usd": assets[index + 1],
                    "target_log_change": math.log(assets[index + 1] / assets[index]),
                    "previous_available_date": previous_available.isoformat(),
                    "target_available_date": target_available.isoformat(),
                    "known_at": previous_available.isoformat(),
                }
            )
    rows.sort(key=lambda row: (row["target_available_date"], row["cik"]))
    baseline = evaluate_b9_baselines(
        pd.DataFrame(rows),
        time_cutoff=cutoff,
        company_modulus=company_modulus,
        company_remainder=company_remainder,
        minimum_required=minimum_required,
    )
    columns = list(rows[0])
    return {
        "schema_version": "b9-sec-panel-v1",
        "network_access": False,
        "input_provenance": {"cache_root": "/not/read/by/auditor"},
        "panel_contract": {"minimum_gap_days": 60, "maximum_gap_days": 120},
        "panel": {
            "columns": columns,
            "rows": rows,
            "quality": {
                "row_count": len(rows),
                "company_count": len(ciks),
                "duplicate_keys": 0,
                "missing_by_column": {column: 0 for column in columns},
                "nonpositive_asset_rows": 0,
                "invalid_gap_rows": 0,
                "gap_affected_company_count": 0,
                "maximum_gap_days": max(
                    (target - previous).days for previous, target in pairwise(periods)
                ),
                "accepted": True,
                "warnings": [],
            },
            "universe": {
                "spec": {
                    "anchor_period_end": "2015-12-31",
                    "anchor_as_of": "2016-04-01",
                    "analysis_start": "2016-04-01",
                    "minimum_assets_usd": 100_000_000.0,
                },
                "eligible_ciks": list(ciks),
                "candidate_rows": len(ciks),
                "selected_rows": len(ciks),
            },
        },
        "baseline": {
            "time_cutoff": cutoff.isoformat(),
            "company_modulus": company_modulus,
            "company_remainder": company_remainder,
            "minimum_required": minimum_required,
            "accepted": baseline.accepted,
            "split_counts": asdict(baseline.split_counts),
            "splits": [
                {
                    "name": split.name,
                    "n": split.n,
                    "training_n": split.training_n,
                    "holdout_company_count": split.holdout_company_count,
                    "holdout_target_available_date_count": (
                        split.holdout_target_available_date_count
                    ),
                    "training_company_count": split.training_company_count,
                    "training_target_available_date_count": (
                        split.training_target_available_date_count
                    ),
                    "accepted": split.accepted,
                    "metrics": {name: asdict(metric) for name, metric in split.metrics.items()},
                }
                for split in baseline.splits
            ],
        },
    }


def _write_artifact(path: Path, artifact: dict[str, object] | None = None) -> Path:
    value = _artifact() if artifact is None else artifact
    ciks = value["panel"]["universe"]["eligible_ciks"]
    normalized_ciks = sorted({str(cik).zfill(10) for cik in ciks})
    cik_payload = ("\n".join(normalized_ciks) + "\n").encode()
    selected_digest = sha256(cik_payload).hexdigest()
    seed_manifest = {
        "schema_version": "b9-historical-seed-v1",
        "master_index_sha256": "a" * 64,
        "source_url": "https://www.sec.gov/Archives/edgar/full-index/2016/QTR1/master.idx",
        "forms": ["10-K"],
        "filed_start": "2016-01-01",
        "filed_end": "2016-03-31",
        "selection_method": "evenly_spaced_cik_rank",
        "selected_cik_count": len(normalized_ciks),
        "selected_cik_sha256": selected_digest,
        "selected_records": [{"cik": cik} for cik in normalized_ciks],
    }
    seed_payload = (json.dumps(seed_manifest, indent=2, sort_keys=True) + "\n").encode()
    seed_path = path.with_name(f"{path.stem}_seed.json")
    seed_path.write_bytes(seed_payload)
    holiday_start = date(1990, 1, 1)
    holiday_end = date(2036, 1, 14)
    holiday_manifest = {
        "schema_version": "b9-us-federal-holidays-v1",
        "calendar": "pandas.USFederalHolidayCalendar",
        "start": holiday_start.isoformat(),
        "end": holiday_end.isoformat(),
        "pandas_version": pd.__version__,
        "holiday_dates": [
            value.date().isoformat()
            for value in USFederalHolidayCalendar().holidays(start=holiday_start, end=holiday_end)
        ],
    }
    holiday_payload = (json.dumps(holiday_manifest, indent=2, sort_keys=True) + "\n").encode()
    holiday_path = path.with_name(f"{path.stem}_holidays.json")
    holiday_path.write_bytes(holiday_payload)
    protocol = {
        "schema_version": "b9-m6-protocol-v1",
        "universe": {
            **value["panel"]["universe"]["spec"],
            "concept": "us-gaap/Assets",
            "unit": "USD",
        },
        "panel": {
            **value["panel_contract"],
            "availability_calendar": "us_federal_holidays",
            "holiday_manifest_start": "1990-01-01",
            "holiday_manifest_end": "2035-12-31",
        },
        "evaluation": {
            "time_cutoff": value["baseline"]["time_cutoff"],
            "company_modulus": value["baseline"]["company_modulus"],
            "company_remainder": value["baseline"]["company_remainder"],
            "minimum_required": value["baseline"]["minimum_required"],
            "metrics": {
                "primary": "mae",
                "secondary": "median_absolute_error",
                "reference": "rmse",
            },
        },
        "historical_seed": {
            "source_url": seed_manifest["source_url"],
            "forms": seed_manifest["forms"],
            "filed_start": seed_manifest["filed_start"],
            "filed_end": seed_manifest["filed_end"],
            "selection_method": seed_manifest["selection_method"],
            "requested_cik_count": seed_manifest["selected_cik_count"],
        },
    }
    protocol_payload = (json.dumps(protocol, indent=2, sort_keys=True) + "\n").encode()
    protocol_path = path.with_name(f"{path.stem}_protocol.json")
    protocol_path.write_bytes(protocol_payload)
    value["input_provenance"] = {
        "cache_root": "/not/read/by/auditor",
        "historical_seed_manifest": {
            "path": str(seed_path),
            "sha256": sha256(seed_payload).hexdigest(),
            "schema_version": "b9-historical-seed-v1",
            "master_index_sha256": "a" * 64,
            "source_url": seed_manifest["source_url"],
            "forms": seed_manifest["forms"],
            "filed_start": seed_manifest["filed_start"],
            "filed_end": seed_manifest["filed_end"],
            "selection_method": "evenly_spaced_cik_rank",
            "selected_cik_count": len(normalized_ciks),
            "selected_cik_sha256": selected_digest,
        },
        "batch_manifest": {
            "path": "/not/read/by/auditor/batch_manifest.json",
            "sha256": "b" * 64,
            "schema_version": "b9-sec-batch-v1",
            "requested_cik_count": len(normalized_ciks),
            "success_count": len(normalized_ciks),
            "failure_count": 0,
            "observed_requested_cik_count": len(normalized_ciks),
            "observed_requested_cik_sha256": selected_digest,
        },
        "holiday_manifest": {
            "path": str(holiday_path),
            "sha256": sha256(holiday_payload).hexdigest(),
            "schema_version": "b9-us-federal-holidays-v1",
            "calendar": "pandas.USFederalHolidayCalendar",
            "start": holiday_manifest["start"],
            "end": holiday_manifest["end"],
            "holiday_count": len(holiday_manifest["holiday_dates"]),
        },
        "cache_integrity": {
            "accepted": True,
            "success_cik_count": len(normalized_ciks),
            "success_cik_sha256": selected_digest,
            "success_ciks": [int(cik) for cik in normalized_ciks],
            "errors": [],
        },
        "protocol": {
            "path": str(protocol_path),
            "sha256": sha256(protocol_payload).hexdigest(),
            "schema_version": "b9-m6-protocol-v1",
        },
    }
    value["panel"]["quality"]["source_cache_count"] = len(normalized_ciks)
    value["panel"]["quality"]["excluded_issuer_ciks_by_reason"] = {}
    value["panel"]["quality"]["excluded_nonpositive_asset_pair_count"] = 0
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _protocol_path(artifact_path: Path) -> Path:
    return artifact_path.with_name(f"{artifact_path.stem}_protocol.json")


def _holiday_path(artifact_path: Path) -> Path:
    return artifact_path.with_name(f"{artifact_path.stem}_holidays.json")


def test_valid_artifact_recomputes_quality_splits_and_baseline_metrics(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_tool()
    artifact = _artifact()
    artifact["panel"]["quality"]["issuer_exclusions_by_reason"] = {"missing_us_gaap": 2}
    artifact_path = _write_artifact(tmp_path / "panel.json", artifact)
    report_path = tmp_path / "reports" / "quality.json"

    report = module.audit_artifact(artifact_path)

    assert report["schema_version"] == "b9-sec-panel-quality-audit-v1"
    assert report["accepted"]
    assert report["strict_provenance_accepted"]
    assert not report["strict_protocol_accepted"]
    assert report["strict_sample_gate_accepted"]
    assert not report["modeling_gate_accepted"]
    assert report["panel"]["row_count"] == 15
    assert report["panel"]["company_count"] == 3
    assert report["panel"]["duplicate_keys"] == 0
    assert report["panel"]["gap"]["invalid_rows"] == 0
    assert report["stored_quality"]["matches_artifact"]
    assert report["baseline"]["matches_artifact"]
    assert report["baseline"]["mismatched_metrics"] == []
    assert report["warnings"] == ["strict pre-registered M6 protocol gate is not met"]
    assert module.main([str(artifact_path), "--output", str(report_path)]) == 0
    printed = json.loads(capsys.readouterr().out)
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert printed == persisted == report


def test_panel_corruption_is_reported_without_reading_provenance_cache(tmp_path: Path) -> None:
    module = _load_tool()
    artifact = _artifact()
    rows = artifact["panel"]["rows"]
    rows.append(deepcopy(rows[0]))
    rows[1]["previous_assets_usd"] = None
    rows[2]["target_assets_usd"] = 0.0
    rows[3]["known_at"] = rows[3]["target_available_date"]
    rows[4]["target_period_end"] = "2018-12-31"
    path = _write_artifact(tmp_path / "corrupt.json", artifact)

    report = module.audit_artifact(path)

    assert not report["accepted"]
    assert not report["modeling_gate_accepted"]
    assert report["panel"]["null_by_column"]["previous_assets_usd"] == 1
    assert report["panel"]["duplicate_keys"] == 1
    assert report["panel"]["nonpositive_asset_rows"] == 1
    assert report["panel"]["known_at_mismatch_rows"] == 1
    assert report["panel"]["availability_order_violations"] == 1
    assert report["panel"]["gap"]["invalid_rows"] == 1
    assert not report["stored_quality"]["matches_artifact"]
    assert not report["baseline"]["matches_artifact"]
    assert "failed integrity checks" in report["warnings"][0]


def test_stored_metric_and_split_tampering_are_detected(tmp_path: Path) -> None:
    module = _load_tool()
    artifact = _artifact()
    artifact["baseline"]["split_counts"]["both_holdout_rows"] += 1
    artifact["baseline"]["splits"][0]["metrics"]["zero"]["mae"] += 0.1
    artifact["baseline"]["splits"][1]["training_n"] += 1
    path = _write_artifact(tmp_path / "tampered.json", artifact)

    report = module.audit_artifact(path)

    assert not report["accepted"]
    assert report["baseline"]["split_count_mismatches"] == ["both_holdout_rows"]
    assert report["baseline"]["mismatched_metrics"] == ["time.zero"]
    assert report["baseline"]["split_coverage_mismatches"] == ["company.training_n"]


def test_sample_gate_failure_is_not_mislabeled_as_artifact_corruption(tmp_path: Path) -> None:
    module = _load_tool()
    artifact = _artifact()
    artifact["baseline"]["minimum_required"] = 999
    artifact["baseline"]["accepted"] = False
    artifact["baseline"]["split_counts"]["minimum_required"] = 999
    artifact["baseline"]["split_counts"]["accepted"] = False
    for split in artifact["baseline"]["splits"]:
        split["accepted"] = False
    path = _write_artifact(tmp_path / "small_sample.json", artifact)

    report = module.audit_artifact(path)

    assert report["accepted"]
    assert not report["strict_sample_gate_accepted"]
    assert not report["modeling_gate_accepted"]
    assert report["warnings"] == [
        "strict pre-registered M6 protocol gate is not met",
        "strict company-by-time sample-size gate is not met",
    ]


def test_strict_m6_protocol_and_source_chain_accept_a_preregistered_artifact(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_tool()
    artifact = _artifact(
        ciks=tuple(range(1, 301)),
        periods=(
            date(2023, 3, 31),
            date(2023, 6, 30),
            date(2023, 9, 30),
            date(2023, 12, 31),
            date(2024, 3, 31),
        ),
        cutoff=date(2023, 10, 23),
        company_modulus=3,
        company_remainder=0,
        minimum_required=200,
    )
    artifact_path = _write_artifact(tmp_path / "m6-panel.json", artifact)
    protocol_path = _protocol_path(artifact_path)

    report = module.audit_artifact(artifact_path, protocol_path=protocol_path)

    assert report["accepted"]
    assert report["strict_provenance_accepted"]
    assert report["strict_protocol_accepted"]
    assert report["strict_sample_gate_accepted"]
    assert report["modeling_gate_accepted"]
    assert report["protocol"]["mismatches"] == []
    assert report["protocol"]["holiday_coverage"]["panel_dates_within_manifest"]
    assert report["baseline"]["splits"]["both"]["training_n"] == 200
    assert report["baseline"]["splits"]["both"]["holdout_company_count"] == 100
    assert report["baseline"]["split_coverage_mismatches"] == []
    assert report["source_provenance"]["source_quality"] == {
        "source_cache_count": 300,
        "excluded_issuer_count": 0,
        "excluded_issuer_ciks_by_reason": {},
        "excluded_nonpositive_asset_pair_count": 0,
        "source_cache_count_matches_batch_success": True,
        "exclusions_unique": True,
        "exclusions_absent_from_panel": True,
        "exclusions_within_seed": True,
        "panel_ciks_within_seed": True,
        "exclusions_within_source_count": True,
        "covered_ciks_within_source_count": True,
        "unexpected_exclusion_reasons": [],
    }
    assert (
        module.main(
            [
                str(artifact_path),
                "--protocol",
                str(protocol_path),
                "--require-modeling-gate",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == report


def test_seed_protocol_and_source_count_tampering_fail_strict_gates(tmp_path: Path) -> None:
    module = _load_tool()
    artifact = _artifact(
        cutoff=date(2023, 10, 23),
        company_modulus=3,
        minimum_required=200,
    )
    artifact_path = _write_artifact(tmp_path / "tampered-provenance.json", artifact)
    stored = json.loads(artifact_path.read_text(encoding="utf-8"))
    stored["input_provenance"]["batch_manifest"]["observed_requested_cik_sha256"] = "d" * 64
    stored["panel"]["quality"]["source_cache_count"] = 2
    artifact_path.write_text(json.dumps(stored), encoding="utf-8")
    seed_path = Path(stored["input_provenance"]["historical_seed_manifest"]["path"])
    seed_path.write_text(seed_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    protocol_path = _protocol_path(artifact_path)
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["evaluation"]["company_remainder"] = 1
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")

    report = module.audit_artifact(artifact_path, protocol_path=protocol_path)

    assert not report["accepted"]
    assert not report["strict_provenance_accepted"]
    assert not report["strict_protocol_accepted"]
    assert not report["modeling_gate_accepted"]
    assert not report["source_provenance"]["seed_manifest"]["matches_observed_requested_ciks"]
    assert not report["source_provenance"]["seed_manifest"]["file_audit"]["sha256_matches"]
    assert not report["source_provenance"]["source_quality"][
        "source_cache_count_matches_batch_success"
    ]
    assert not report["source_provenance"]["source_quality"]["covered_ciks_within_source_count"]
    assert "artifact.protocol_provenance" in report["protocol"]["mismatches"]
    assert "preregistered.company_split" in report["protocol"]["mismatches"]


def test_holiday_manifest_tampering_missing_file_and_short_coverage_fail_gates(
    tmp_path: Path,
) -> None:
    module = _load_tool()
    for mode in ("tampered", "missing"):
        artifact_path = _write_artifact(tmp_path / f"holiday-{mode}.json")
        holiday_path = _holiday_path(artifact_path)
        if mode == "tampered":
            manifest = json.loads(holiday_path.read_text(encoding="utf-8"))
            manifest["holiday_dates"].reverse()
            holiday_path.write_text(json.dumps(manifest), encoding="utf-8")
        else:
            holiday_path.unlink()

        report = module.audit_artifact(artifact_path)

        assert not report["accepted"]
        assert not report["strict_provenance_accepted"]
        assert not report["modeling_gate_accepted"]
        file_audit = report["source_provenance"]["holiday_manifest"]["file_audit"]
        if mode == "tampered":
            assert file_audit["exists"]
            assert not file_audit["sha256_matches"]
            assert not file_audit["dates_sorted_unique"]
        else:
            assert not file_audit["exists"]
            assert file_audit["error"] == "holiday manifest file is missing"

    coverage_artifact_path = _write_artifact(tmp_path / "holiday-coverage.json")
    coverage_protocol_path = _protocol_path(coverage_artifact_path)
    protocol = json.loads(coverage_protocol_path.read_text(encoding="utf-8"))
    protocol["panel"]["holiday_manifest_end"] = "2040-12-31"
    protocol_payload = (json.dumps(protocol, indent=2, sort_keys=True) + "\n").encode()
    coverage_protocol_path.write_bytes(protocol_payload)
    stored = json.loads(coverage_artifact_path.read_text(encoding="utf-8"))
    stored["input_provenance"]["protocol"]["sha256"] = sha256(protocol_payload).hexdigest()
    coverage_artifact_path.write_text(json.dumps(stored), encoding="utf-8")

    report = module.audit_artifact(coverage_artifact_path, protocol_path=coverage_protocol_path)

    assert report["strict_provenance_accepted"]
    assert not report["strict_protocol_accepted"]
    assert not report["protocol"]["holiday_coverage"]["covers_protocol"]
    assert "artifact.holiday_manifest_coverage" in report["protocol"]["mismatches"]


def test_cache_integrity_success_ciks_and_hard_coded_protocol_are_independent_gates(
    tmp_path: Path,
) -> None:
    module = _load_tool()
    artifact_path = _write_artifact(tmp_path / "cache-integrity.json")
    stored = json.loads(artifact_path.read_text(encoding="utf-8"))
    integrity = stored["input_provenance"]["cache_integrity"]
    integrity["success_ciks"] = [1, 2, 4]
    integrity["success_cik_sha256"] = sha256(b"0000000001\n0000000002\n0000000004\n").hexdigest()
    artifact_path.write_text(json.dumps(stored), encoding="utf-8")

    report = module.audit_artifact(artifact_path)

    assert not report["strict_provenance_accepted"]
    assert not report["source_provenance"]["cache_integrity"]["panel_ciks_within_successes"]
    assert "raw SEC payloads" in report["source_provenance"]["strict_scope"]

    protocol_artifact_path = _write_artifact(tmp_path / "mutual-protocol-change.json")
    protocol_path = _protocol_path(protocol_artifact_path)
    protocol_artifact = json.loads(protocol_artifact_path.read_text(encoding="utf-8"))
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol_artifact["panel"]["universe"]["spec"]["anchor_period_end"] = "2014-12-31"
    protocol["universe"]["anchor_period_end"] = "2014-12-31"
    protocol_payload = (json.dumps(protocol, indent=2, sort_keys=True) + "\n").encode()
    protocol_path.write_bytes(protocol_payload)
    protocol_artifact["input_provenance"]["protocol"]["sha256"] = sha256(
        protocol_payload
    ).hexdigest()
    protocol_artifact_path.write_text(json.dumps(protocol_artifact), encoding="utf-8")

    report = module.audit_artifact(protocol_artifact_path, protocol_path=protocol_path)

    assert report["protocol"]["artifact_match_checks"]["universe_contract"]
    assert not report["protocol"]["preregistered_checks"]["universe"]
    assert "preregistered.universe" in report["protocol"]["mismatches"]


def test_training_and_analysis_window_are_required_for_strict_modeling_gate(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_tool()
    no_training = _artifact(
        ciks=(2,),
        periods=(date(2017, 3, 31), date(2017, 6, 30)),
        cutoff=date(2017, 2, 1),
        company_modulus=2,
        company_remainder=0,
        minimum_required=1,
    )
    no_training_path = _write_artifact(tmp_path / "no-training.json", no_training)

    report = module.audit_artifact(no_training_path)

    assert report["accepted"]
    assert report["baseline"]["split_counts"]["both_holdout_rows"] == 1
    assert report["baseline"]["splits"]["both"]["training_n"] == 0
    assert not report["strict_sample_gate_accepted"]
    assert not report["modeling_gate_accepted"]
    assert module.main([str(no_training_path), "--require-modeling-gate"]) == 1
    capsys.readouterr()

    early_row_path = _write_artifact(tmp_path / "early-row.json")
    early_artifact = json.loads(early_row_path.read_text(encoding="utf-8"))
    early_artifact["panel"]["rows"][0]["previous_period_end"] = "2015-12-31"
    early_artifact["panel"]["rows"][0]["target_period_end"] = "2016-03-31"
    early_row_path.write_text(json.dumps(early_artifact), encoding="utf-8")

    report = module.audit_artifact(early_row_path, protocol_path=_protocol_path(early_row_path))

    assert report["protocol"]["analysis_window"]["rows_before_analysis_start"] == 1
    assert not report["protocol"]["artifact_match_checks"]["panel_analysis_window"]

    late_row_path = _write_artifact(tmp_path / "late-row.json")
    late_artifact = json.loads(late_row_path.read_text(encoding="utf-8"))
    late_artifact["panel"]["rows"][-1]["target_period_end"] = "2040-03-31"
    late_artifact["panel"]["rows"][-1]["target_available_date"] = "2040-05-15"
    late_row_path.write_text(json.dumps(late_artifact), encoding="utf-8")

    report = module.audit_artifact(late_row_path, protocol_path=_protocol_path(late_row_path))

    assert not report["protocol"]["holiday_coverage"]["panel_dates_within_manifest"]
    assert not report["protocol"]["artifact_match_checks"]["holiday_manifest_coverage"]


def test_missing_and_invalid_artifacts_fail_with_explicit_cli_errors(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_tool()
    missing = tmp_path / "missing.json"
    assert module.main([str(missing)]) == 2
    assert "does not exist" in capsys.readouterr().err

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{not-json", encoding="utf-8")
    assert module.main([str(invalid)]) == 2
    assert "not valid UTF-8 JSON" in capsys.readouterr().err

    wrong_schema = tmp_path / "wrong-schema.json"
    wrong_schema.write_text(json.dumps({"schema_version": "wrong"}), encoding="utf-8")
    assert module.main([str(wrong_schema)]) == 2
    assert "schema_version" in capsys.readouterr().err
