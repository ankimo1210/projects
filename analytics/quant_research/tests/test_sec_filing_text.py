from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

import pytest
from quant_textbook.sec_filing_text import (
    audit_filing_retrieval,
    audit_normalized_filing_text,
    build_previous_filing_sidecar,
    download_previous_filing_documents,
    fetch_primary_document,
    normalize_retrieved_documents,
    normalize_visible_filing_text,
    primary_document_url,
)
from quant_textbook.sec_panel import build_b9_panel
from quant_textbook.sec_pit import PITUniverseSpec


def _table(rows: list[dict[str, Any]]) -> dict[str, list[Any]]:
    return {
        column: [row[column] for row in rows]
        for column in (
            "accessionNumber",
            "filingDate",
            "acceptanceDateTime",
            "form",
            "primaryDocument",
        )
    }


def _write_cache(root: Path, *, missing_primary: bool = False) -> None:
    cik = 1
    normalized = f"{cik:010d}"
    cache_dir = root / f"CIK{normalized}"
    cache_dir.mkdir(parents=True)
    specifications = (
        ("2015-12-31", "2016-02-10", "10-K", "000001"),
        ("2016-03-31", "2016-05-10", "10-Q", "000002"),
        ("2016-06-30", "2016-08-10", "10-Q", "000003"),
    )
    rows: list[dict[str, Any]] = []
    facts: list[dict[str, Any]] = []
    for index, (period, filed, form, serial) in enumerate(specifications):
        accession = f"{normalized}-{16 + index:02d}-{serial}"
        rows.append(
            {
                "accessionNumber": accession,
                "filingDate": filed,
                "acceptanceDateTime": f"{filed}T17:00:00-05:00",
                "form": form,
                "primaryDocument": "" if missing_primary and index == 1 else f"form{index}.htm",
            }
        )
        facts.append({"accn": accession, "end": period, "val": 200_000_000 + index})
    archive_name = f"CIK{normalized}-submissions-001.json"
    submissions = {
        "cik": normalized,
        "filings": {
            "recent": _table(rows[1:]),
            "files": [{"name": archive_name}],
        },
    }
    (cache_dir / f"submissions_CIK{normalized}.json").write_text(
        json.dumps(submissions), encoding="utf-8"
    )
    (cache_dir / archive_name).write_text(json.dumps(_table(rows[:1])), encoding="utf-8")
    (cache_dir / f"companyfacts_CIK{normalized}.json").write_text(
        json.dumps(
            {"cik": normalized, "facts": {"us-gaap": {"Assets": {"units": {"USD": facts}}}}}
        ),
        encoding="utf-8",
    )
    raw_files = sorted(path for path in cache_dir.glob("*.json"))
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
                "archive_count_advertised": 1,
                "file_count": len(records),
                "files": records,
            }
        ),
        encoding="utf-8",
    )


def _spec() -> PITUniverseSpec:
    return PITUniverseSpec(
        anchor_period_end=date(2015, 12, 31),
        anchor_as_of=date(2016, 4, 1),
        analysis_start=date(2016, 4, 1),
    )


def test_sidecar_preserves_locked_panel_and_materializes_previous_filing(tmp_path: Path) -> None:
    _write_cache(tmp_path)
    panel = build_b9_panel(tmp_path, _spec())
    before = panel.frame.to_json(date_format="iso", orient="records")

    sidecar = build_previous_filing_sidecar(panel.frame, tmp_path)

    assert sidecar.quality.accepted
    assert sidecar.quality.panel_row_count == 1
    assert sidecar.quality.unique_previous_document_count == 1
    assert sidecar.rows[0]["previous_primary_document"] == "form1.htm"
    assert sidecar.rows[0]["previous_accession"] != sidecar.rows[0]["target_accession"]
    assert panel.frame.to_json(date_format="iso", orient="records") == before


def test_sidecar_fails_gate_when_previous_primary_document_is_missing(tmp_path: Path) -> None:
    _write_cache(tmp_path, missing_primary=True)
    panel = build_b9_panel(tmp_path, _spec())

    sidecar = build_previous_filing_sidecar(panel.frame, tmp_path)

    assert not sidecar.quality.accepted
    assert sidecar.quality.missing_primary_document_rows == 1


class _Response(BytesIO):
    status = 200

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def test_fetch_retries_429_then_succeeds_and_does_not_retry_404() -> None:
    attempts: list[int] = []
    sleeps: list[float] = []

    def transient_then_success(*_: Any, **__: Any) -> _Response:
        attempts.append(1)
        if len(attempts) == 1:
            raise HTTPError("https://example.test", 429, "rate limited", {"Retry-After": "0"}, None)
        return _Response(b"<html>ok</html>")

    payload, attempt_count, status = fetch_primary_document(
        "https://example.test/document.htm",
        user_agent="Research textbook contact@example.com",
        opener=transient_then_success,
        sleep=sleeps.append,
    )
    assert payload == b"<html>ok</html>"
    assert attempt_count == 2
    assert status == 200
    assert sleeps == [0.0]

    permanent_attempts = 0

    def permanent(*_: Any, **__: Any) -> _Response:
        nonlocal permanent_attempts
        permanent_attempts += 1
        raise HTTPError("https://example.test", 404, "not found", {}, None)

    with pytest.raises(HTTPError):
        fetch_primary_document(
            "https://example.test/missing.htm",
            user_agent="Research textbook contact@example.com",
            opener=permanent,
            sleep=lambda _: None,
        )
    assert permanent_attempts == 1


def _sidecar_row(*, cik: int = 1, target_date: str = "2023-01-01") -> dict[str, Any]:
    accession = f"{cik:010d}-22-000001"
    return {
        "cik": cik,
        "previous_period_end": "2022-06-30",
        "target_period_end": "2022-09-30",
        "target_available_date": target_date,
        "previous_accession": accession,
        "previous_form": "10-Q",
        "previous_filing_date": "2022-08-01",
        "previous_acceptance_datetime": "2022-08-01T17:00:00-04:00",
        "previous_available_date": "2022-08-02",
        "previous_primary_document": "q2.htm",
        "previous_document_sha256": None,
        "target_accession": f"{cik:010d}-22-000002",
    }


def test_downloader_atomic_manifest_and_retrieval_audit(tmp_path: Path) -> None:
    row = _sidecar_row()

    def fetcher(*_: Any, **__: Any) -> tuple[bytes, int, int]:
        return b"<html>filing</html>", 2, 200

    manifest = download_previous_filing_documents(
        [row],
        tmp_path,
        provenance_sha256="a" * 64,
        user_agent="Research textbook contact@example.com",
        sleep_seconds=0,
        fetcher=fetcher,
    )
    assert manifest["success_count"] == 1
    assert manifest["failure_count"] == 0
    assert "contact@example.com" not in json.dumps(manifest)
    assert not list(tmp_path.rglob("*.tmp"))
    result = audit_filing_retrieval(
        [row],
        manifest,
        tmp_path,
        provenance_sha256="a" * 64,
        outer_time_cutoff=date(2023, 10, 23),
        company_modulus=3,
        company_remainder=0,
    )
    assert result.accepted
    assert result.row_coverage == 1.0
    normalized_root = tmp_path / "normalized"
    normalized_manifest = normalize_retrieved_documents(manifest, tmp_path, normalized_root)
    normalized_audit = audit_normalized_filing_text(
        [row],
        normalized_manifest,
        normalized_root,
        retrieval_manifest=manifest,
        outer_time_cutoff=date(2023, 10, 23),
        company_modulus=3,
        company_remainder=0,
    )
    assert normalized_audit.accepted
    assert normalized_audit.row_coverage == 1.0


def test_refresh_failure_preserves_last_atomically_published_document(tmp_path: Path) -> None:
    row = _sidecar_row()

    def success(*_: Any, **__: Any) -> tuple[bytes, int, int]:
        return b"known-good", 1, 200

    first = download_previous_filing_documents(
        [row],
        tmp_path,
        provenance_sha256="a" * 64,
        user_agent="Research textbook contact@example.com",
        sleep_seconds=0,
        fetcher=success,
    )
    document_path = tmp_path / first["documents"][0]["path"]

    def failure(*_: Any, **__: Any) -> tuple[bytes, int, int]:
        raise TimeoutError("transient failure")

    second = download_previous_filing_documents(
        [row],
        tmp_path,
        provenance_sha256="a" * 64,
        user_agent="Research textbook contact@example.com",
        sleep_seconds=0,
        refresh=True,
        fetcher=failure,
    )

    assert second["success_count"] == 0
    assert second["failure_count"] == 1
    assert document_path.read_bytes() == b"known-good"


def test_audit_rejects_cross_partition_duplicate_and_target_text(tmp_path: Path) -> None:
    development = _sidecar_row(cik=1, target_date="2023-01-01")
    outer = _sidecar_row(cik=3, target_date="2024-01-01")
    outer["target_accession"] = outer["previous_accession"]
    payload = b"identical"
    documents: list[dict[str, Any]] = []
    for row in (development, outer):
        relative = (
            Path(f"CIK{row['cik']:010d}")
            / str(row["previous_accession"]).replace("-", "")
            / "q2.htm"
        )
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(payload)
        documents.append(
            {
                "cik": row["cik"],
                "accession": row["previous_accession"],
                "primary_document": "q2.htm",
                "path": relative.as_posix(),
                "raw_sha256": sha256(payload).hexdigest(),
                "byte_count": len(payload),
            }
        )
    manifest = {
        "schema_version": "b9-sec-primary-documents-v1",
        "source_provenance_sha256": "a" * 64,
        "success_count": 2,
        "failure_count": 0,
        "documents": documents,
        "failures": [],
    }

    result = audit_filing_retrieval(
        [development, outer],
        manifest,
        tmp_path,
        provenance_sha256="a" * 64,
        outer_time_cutoff=date(2023, 10, 23),
        company_modulus=3,
        company_remainder=0,
    )

    assert not result.accepted
    assert result.cross_partition_duplicate_family_count == 1
    assert result.target_accession_leakage_rows == 1


def test_primary_document_url_rejects_paths() -> None:
    assert primary_document_url(320193, "0000320193-25-000079", "aapl-20250329.htm").endswith(
        "/320193/000032019325000079/aapl-20250329.htm"
    )
    with pytest.raises(ValueError, match="safe SEC-relative path"):
        primary_document_url(320193, "0000320193-25-000079", "../secret.htm")


def test_visible_text_normalizer_removes_hidden_markup_and_keeps_visible_table_text() -> None:
    payload = b"""
    <html><body>
      <h1>Risk Factors</h1>
      <script>secret script</script><style>.x{display:none}</style>
      <p>Visible&nbsp;paragraph  123</p>
      <table><tr><td>tabular fact</td></tr></table>
      <ix:hidden>hidden xbrl</ix:hidden>
      <div aria-hidden="true">aria secret</div>
      <h2>Outlook</h2><p>Second paragraph</p>
    </body></html>
    """

    text = normalize_visible_filing_text(payload)

    assert text.splitlines() == [
        "Risk Factors",
        "Visible paragraph 123",
        "tabular fact",
        "Outlook",
        "Second paragraph",
    ]
    assert "secret" not in text


def test_normalized_audit_catches_duplicates_that_raw_hashes_miss(tmp_path: Path) -> None:
    first = _sidecar_row(cik=1, target_date="2023-01-01")
    second = _sidecar_row(cik=3, target_date="2024-01-01")
    raw_payloads = (b"<p>Same text</p>", b"<div> Same   text </div>")
    documents: list[dict[str, Any]] = []
    for row, payload in zip((first, second), raw_payloads, strict=True):
        relative = (
            Path(f"CIK{row['cik']:010d}")
            / str(row["previous_accession"]).replace("-", "")
            / "q2.htm"
        )
        path = tmp_path / relative
        path.parent.mkdir(parents=True)
        path.write_bytes(payload)
        documents.append(
            {
                "cik": row["cik"],
                "accession": row["previous_accession"],
                "form": row["previous_form"],
                "filing_date": row["previous_filing_date"],
                "acceptance_datetime": row["previous_acceptance_datetime"],
                "availability_date": row["previous_available_date"],
                "primary_document": row["previous_primary_document"],
                "retrieved_at_utc": "2026-08-11T00:00:00+00:00",
                "path": relative.as_posix(),
                "raw_sha256": sha256(payload).hexdigest(),
                "byte_count": len(payload),
            }
        )
    retrieval = {
        "schema_version": "b9-sec-primary-documents-v1",
        "documents": documents,
    }
    normalized_root = tmp_path / "normalized"
    normalized = normalize_retrieved_documents(retrieval, tmp_path, normalized_root)

    result = audit_normalized_filing_text(
        [first, second],
        normalized,
        normalized_root,
        retrieval_manifest=retrieval,
        outer_time_cutoff=date(2023, 10, 23),
        company_modulus=3,
        company_remainder=0,
    )

    assert not result.accepted
    assert result.duplicate_family_count == 1
    assert result.cross_partition_duplicate_family_count == 1
