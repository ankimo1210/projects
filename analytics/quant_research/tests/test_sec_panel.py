from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from quant_textbook.sec_panel import build_b9_panel, evaluate_b9_baselines
from quant_textbook.sec_pit import PITUniverseSpec, UnresolvedAccessionError


def _load_panel_builder() -> Any:
    path = Path(__file__).parents[1] / "tools" / "build_b9_panel.py"
    spec = importlib.util.spec_from_file_location("build_b9_panel", path)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load B9 panel builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _submission_table(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    return {
        column: [row[column] for row in rows]
        for column in ("accessionNumber", "filingDate", "acceptanceDateTime", "form")
    }


def _write_cache(root: Path, cik: int, *, include_archive: bool = True) -> None:
    normalized = f"{cik:010d}"
    cache_dir = root / f"CIK{normalized}"
    cache_dir.mkdir(parents=True)
    periods = (
        ("2015-12-31", "000001"),
        ("2016-03-31", "000002"),
        ("2016-06-30", "000003"),
        ("2016-09-30", "000004"),
        ("2016-12-31", "000005"),
        ("2017-03-31", "000006"),
        ("2017-06-30", "000007"),
    )
    all_rows: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    for index, (period_end, serial) in enumerate(periods):
        accession = f"{normalized}-{16 + index:02d}-{serial}"
        filed = date(2016 + (index // 4), 2 + (index % 4) * 3, 10)
        if index == 0:
            filed = date(2016, 2, 10)
        form = "10-K" if period_end.endswith("12-31") else "10-Q"
        row = {
            "accessionNumber": accession,
            "filingDate": filed.isoformat(),
            "acceptanceDateTime": f"{filed.isoformat()}T17:00:00-05:00",
            "form": form,
        }
        all_rows.append(row)
        facts.append(
            {
                "accn": accession,
                "end": period_end,
                "val": float(150_000_000 + cik * 1_000_000 + index * 5_000_000),
            }
        )
    archive_name = f"CIK{normalized}-submissions-001.json"
    recent_rows = all_rows[1:]
    submissions = {
        "filings": {
            "recent": _submission_table(recent_rows),
            "files": [{"name": archive_name}] if include_archive else [],
        }
    }
    (cache_dir / f"submissions_CIK{normalized}.json").write_text(
        json.dumps(submissions), encoding="utf-8"
    )
    if include_archive:
        (cache_dir / archive_name).write_text(
            json.dumps(_submission_table(all_rows[:1])), encoding="utf-8"
        )
    companyfacts = {"facts": {"us-gaap": {"Assets": {"units": {"USD": facts}}}}}
    (cache_dir / f"companyfacts_CIK{normalized}.json").write_text(
        json.dumps(companyfacts), encoding="utf-8"
    )
    raw_files = sorted(path for path in cache_dir.glob("*.json") if path.name != "manifest.json")
    records = [
        {
            "name": path.name,
            "bytes": len(path.read_bytes()),
            "sha256": sha256(path.read_bytes()).hexdigest(),
        }
        for path in raw_files
    ]
    (cache_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "b9-sec-cache-v1",
                "cik": normalized,
                "archive_count_advertised": int(include_archive),
                "file_count": len(records),
                "files": records,
            }
        ),
        encoding="utf-8",
    )


def _batch_cache_entry(root: Path, cik: int) -> dict[str, Any]:
    normalized = f"{cik:010d}"
    manifest_path = root / f"CIK{normalized}" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "cik": normalized,
        "directory": f"CIK{normalized}",
        "file_count": manifest["file_count"],
        "archive_count_advertised": manifest["archive_count_advertised"],
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
    }


def _spec() -> PITUniverseSpec:
    return PITUniverseSpec(
        anchor_period_end=date(2015, 12, 31),
        anchor_as_of=date(2016, 4, 1),
        analysis_start=date(2016, 4, 1),
    )


def test_build_panel_joins_archive_and_enforces_pit_grain(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    _write_cache(tmp_path, 2)

    panel = build_b9_panel(tmp_path, _spec())

    assert panel.quality.accepted
    assert panel.universe.eligible_ciks == (1, 2)
    assert panel.quality.row_count == 10
    assert not panel.frame.duplicated(
        subset=["cik", "previous_period_end", "target_period_end"]
    ).any()
    assert (panel.frame["target_available_date"] > panel.frame["known_at"]).all()
    assert (panel.frame["target_period_end"] >= pd.Timestamp("2016-04-01")).all()
    assert panel.frame["known_at"].min() == pd.Timestamp("2016-05-11")

    audit = evaluate_b9_baselines(
        panel.frame,
        time_cutoff=date(2017, 1, 1),
        company_modulus=3,
        company_remainder=1,
        minimum_required=1,
    )
    assert audit.accepted
    assert audit.split_counts.both_holdout_rows == 3
    assert {result.name for result in audit.splits} == {"time", "company", "both"}
    for result in audit.splits:
        assert result.accepted
        assert result.holdout_company_count >= 1
        assert result.holdout_target_available_date_count >= 1
        assert result.training_company_count >= 1
        assert result.training_target_available_date_count >= 1
        assert set(result.metrics) == {"zero", "pooled_drift", "seasonal", "company_mean"}
        assert all(metric.n == result.n for metric in result.metrics.values())


def test_build_panel_requires_historical_archive_for_anchor(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1, include_archive=False)
    with pytest.raises(UnresolvedAccessionError, match="accession metadata is missing"):
        build_b9_panel(tmp_path, _spec())


def test_build_panel_rejects_an_advertised_archive_missing_from_cache(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    archive_path = tmp_path / "CIK0000000001" / "CIK0000000001-submissions-001.json"
    archive_path.unlink()

    with pytest.raises(ValueError, match=r"archives do not match filings\.files"):
        build_b9_panel(tmp_path, _spec())


def test_batch_manifest_excludes_partial_or_failed_cache_directories(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    _write_cache(tmp_path, 2)
    (tmp_path / "batch_manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "b9-sec-batch-v1",
                "requested_cik_count": 2,
                "success_count": 1,
                "failure_count": 1,
                "caches": [_batch_cache_entry(tmp_path, 1)],
                "failures": [{"cik": "0000000002", "error_type": "HTTPError"}],
            }
        ),
        encoding="utf-8",
    )

    panel = build_b9_panel(tmp_path, _spec())

    assert panel.universe.eligible_ciks == (1,)
    assert panel.quality.row_count == 5


def test_panel_excludes_nonadjacent_pair_but_reports_coverage_warning(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    facts_path = tmp_path / "CIK0000000001" / "companyfacts_CIK0000000001.json"
    facts_payload = json.loads(facts_path.read_text(encoding="utf-8"))
    facts = facts_payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]
    facts_payload["facts"]["us-gaap"]["Assets"]["units"]["USD"] = [
        fact for fact in facts if fact["end"] != "2016-09-30"
    ]
    facts_path.write_text(json.dumps(facts_payload), encoding="utf-8")

    panel = build_b9_panel(tmp_path, _spec())

    assert panel.quality.accepted
    assert panel.quality.invalid_gap_rows == 1
    assert panel.quality.gap_affected_company_count == 1
    assert panel.quality.row_count == 3
    assert any("non-adjacent" in warning for warning in panel.quality.warnings)


def test_panel_records_expected_concept_exclusions_without_falling_back(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    _write_cache(tmp_path, 2)
    facts_path = tmp_path / "CIK0000000002" / "companyfacts_CIK0000000002.json"
    facts_payload = json.loads(facts_path.read_text(encoding="utf-8"))
    facts_payload["facts"] = {}
    facts_path.write_text(json.dumps(facts_payload), encoding="utf-8")

    panel = build_b9_panel(tmp_path, _spec())

    assert panel.quality.accepted
    assert panel.quality.source_cache_count == 2
    assert panel.quality.excluded_issuer_ciks_by_reason == {"missing_us_gaap_assets_usd": (2,)}
    assert panel.universe.eligible_ciks == (1,)
    assert any("outside the declared" in warning for warning in panel.quality.warnings)


def test_panel_records_nonpositive_and_same_availability_pair_exclusions(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    _write_cache(tmp_path, 2)
    facts_path = tmp_path / "CIK0000000001" / "companyfacts_CIK0000000001.json"
    facts_payload = json.loads(facts_path.read_text(encoding="utf-8"))
    facts = facts_payload["facts"]["us-gaap"]["Assets"]["units"]["USD"]
    next(fact for fact in facts if fact["end"] == "2016-06-30")["val"] = -1.0
    facts_path.write_text(json.dumps(facts_payload), encoding="utf-8")

    submissions_path = tmp_path / "CIK0000000002" / "submissions_CIK0000000002.json"
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    recent = submissions["filings"]["recent"]
    recent["filingDate"][0:2] = ["2016-08-10", "2016-08-10"]
    recent["acceptanceDateTime"][0:2] = [
        "2016-08-10T17:00:00-05:00",
        "2016-08-10T17:00:00-05:00",
    ]
    submissions_path.write_text(json.dumps(submissions), encoding="utf-8")

    panel = build_b9_panel(tmp_path, _spec())

    assert panel.quality.accepted
    assert panel.quality.excluded_nonpositive_asset_pair_count == 2
    assert panel.quality.excluded_non_increasing_availability_pair_count == 1
    assert panel.quality.availability_affected_company_count == 1
    assert any("non-positive" in warning for warning in panel.quality.warnings)
    assert any("shared a filing" in warning for warning in panel.quality.warnings)


def test_panel_rejects_an_availability_date_before_its_period_end(tmp_path: Path) -> None:
    _write_cache(tmp_path, 1)
    submissions_path = tmp_path / "CIK0000000001" / "submissions_CIK0000000001.json"
    submissions = json.loads(submissions_path.read_text(encoding="utf-8"))
    recent = submissions["filings"]["recent"]
    recent["filingDate"][0] = "2016-01-10"
    recent["acceptanceDateTime"][0] = "2016-01-10T17:00:00-05:00"
    submissions_path.write_text(json.dumps(submissions), encoding="utf-8")

    with pytest.raises(ValueError, match="availability must follow its period end"):
        build_b9_panel(tmp_path, _spec())


def test_panel_quality_rejects_missing_and_duplicate_grain() -> None:
    columns = [
        "cik",
        "previous_period_end",
        "target_period_end",
        "previous_assets_usd",
        "target_assets_usd",
        "target_log_change",
        "previous_available_date",
        "target_available_date",
        "known_at",
    ]
    row = {
        "cik": 1,
        "previous_period_end": "2016-03-31",
        "target_period_end": "2016-06-30",
        "previous_assets_usd": 100.0,
        "target_assets_usd": 110.0,
        "target_log_change": 0.0953,
        "previous_available_date": "2016-05-01",
        "target_available_date": "2016-08-01",
        "known_at": "2016-05-01",
    }
    frame = pd.DataFrame([row, row], columns=columns)
    with pytest.raises(ValueError, match="grain"):
        evaluate_b9_baselines(frame, time_cutoff=date(2017, 1, 1), minimum_required=1)
    missing = frame.drop(columns=["known_at"])
    with pytest.raises(ValueError, match="missing columns"):
        evaluate_b9_baselines(missing, time_cutoff=date(2017, 1, 1), minimum_required=1)


def test_strict_baseline_gate_requires_nonempty_both_training_partition() -> None:
    rows = pd.DataFrame(
        [
            {
                "cik": cik,
                "previous_period_end": "2020-03-31",
                "target_period_end": "2020-06-30",
                "previous_assets_usd": 100.0,
                "target_assets_usd": 110.0,
                "target_log_change": 0.0953101798,
                "previous_available_date": "2020-05-01",
                "target_available_date": "2020-08-01",
                "known_at": "2020-05-01",
            }
            for cik in (1, 4)
        ]
    )

    audit = evaluate_b9_baselines(
        rows,
        time_cutoff=date(2020, 1, 1),
        company_modulus=3,
        company_remainder=1,
        minimum_required=1,
    )
    both = next(result for result in audit.splits if result.name == "both")

    assert audit.split_counts.accepted
    assert both.n == 2
    assert both.training_n == 0
    assert not both.accepted
    assert not audit.accepted


def test_offline_panel_builder_writes_derived_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_cache(tmp_path / "cache", 1)
    _write_cache(tmp_path / "cache", 2)
    output = tmp_path / "derived" / "b9_panel.json"
    module = _load_panel_builder()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_b9_panel.py",
            "--cache-root",
            str(tmp_path / "cache"),
            "--output",
            str(output),
            "--anchor-period-end",
            "2015-12-31",
            "--anchor-as-of",
            "2016-04-01",
            "--analysis-start",
            "2016-04-01",
            "--time-cutoff",
            "2017-01-01",
            "--company-modulus",
            "3",
            "--company-remainder",
            "1",
            "--minimum-required",
            "1",
        ],
    )
    assert module.main() == 0
    artifact = json.loads(output.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "b9-sec-panel-v1"
    assert artifact["network_access"] is False
    assert artifact["input_provenance"]["batch_manifest"] is None
    assert artifact["panel"]["quality"]["accepted"] is True
    assert artifact["baseline"]["accepted"] is True
