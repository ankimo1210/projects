"""Point-in-time selection, quality audit and run roots for the AI bubble study."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest
from portfolio_analyzer.ai_bubble.inputs import (
    REQUIRED_FIELDS,
    audit_inputs,
    reconcile,
    select_as_of,
)
from portfolio_analyzer.ai_bubble.runs import (
    new_run,
    record_outputs,
    record_prereg_amendment,
    recorded_inputs,
)


def row(**over):
    base = {
        "issuer_id": "A",
        "metric": "revenue",
        "value": 100.0,
        "unit": "USD",
        "period_start": "2025-10-01",
        "period_end": "2025-12-31",
        "published_at": "2026-01-10T21:00:00Z",
        "available_at": "2026-01-10T21:00:00Z",
        "retrieved_at": "2026-10-21T01:00:00Z",
        "source_url": "https://example.test/10-Q",
        "document_id": "acc-1",
        "accounting_basis": "US-GAAP",
        "quality": "ok",
    }
    base.update(over)
    return base


def restated():
    return row(
        value=120.0,
        published_at="2026-02-10T21:00:00Z",
        available_at="2026-02-10T21:00:00Z",
        document_id="acc-2",
    )


def test_restatement_is_used_only_after_it_becomes_available():
    rows = [row(), restated()]
    assert [r["value"] for r in select_as_of(rows, "2026-01-31T00:00:00Z")] == [100.0]
    assert [r["value"] for r in select_as_of(rows, "2026-02-28T00:00:00Z")] == [120.0]


def test_selection_does_not_depend_on_input_order():
    rows = [restated(), row()]
    assert [r["value"] for r in select_as_of(rows, "2026-01-31T00:00:00Z")] == [100.0]


def test_rows_not_yet_available_are_not_selected():
    assert select_as_of([row(available_at="2026-03-01T00:00:00Z")], "2026-02-28T00:00:00Z") == []


def test_quarter_and_year_to_date_are_separate_keys():
    ytd = row(period_start="2025-01-01", value=400.0, document_id="acc-3")
    picked = select_as_of([row(), ytd], "2026-02-28T00:00:00Z")
    assert sorted(r["value"] for r in picked) == [100.0, 400.0]


def test_conflicting_values_at_the_same_time_raise():
    with pytest.raises(ValueError, match="conflict"):
        select_as_of([row(), row(value=101.0, document_id="acc-9")], "2026-02-28T00:00:00Z")


def test_identical_values_at_the_same_time_collapse():
    picked = select_as_of([row(), row(document_id="acc-9")], "2026-02-28T00:00:00Z")
    assert [r["document_id"] for r in picked] == ["acc-1"]


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_missing_required_field_raises(field):
    bad = row()
    del bad[field]
    with pytest.raises(ValueError, match=field):
        select_as_of([bad], "2026-02-28T00:00:00Z")


def test_naive_available_at_raises():
    with pytest.raises(ValueError, match="timezone"):
        select_as_of([row(available_at="2026-01-10T21:00:00")], "2026-02-28T00:00:00Z")


def test_naive_as_of_raises():
    with pytest.raises(ValueError, match="timezone"):
        select_as_of([row()], "2026-02-28T00:00:00")


def test_audit_accepts_clean_rows():
    out = audit_inputs([row(), restated()])
    assert out["ok"] is True
    assert out["errors"] == []
    assert out["issuers"] == ["A"]
    assert out["sources"] == ["https://example.test/10-Q"]


def test_audit_reports_blank_unit_and_unexplained_gap_as_errors():
    out = audit_inputs([row(unit=""), row(metric="capex", value=None)])
    assert out["ok"] is False
    assert [(e["index"], e["reason"]) for e in out["errors"]] == [
        (0, "unit missing"),
        (1, "value missing without a reason"),
    ]


def test_audit_keeps_explained_gaps_as_missing_not_zero():
    out = audit_inputs([row(metric="capex", value=None, quality="missing:not_disclosed")])
    assert out["ok"] is True
    assert out["missing"] == [
        {"issuer_id": "A", "metric": "capex", "period_end": "2025-12-31", "reason": "not_disclosed"}
    ]


def test_audit_rejects_rows_available_before_publication():
    out = audit_inputs([row(available_at="2026-01-09T00:00:00Z")])
    assert [e["reason"] for e in out["errors"]] == ["available before published"]


def test_audit_rejects_naive_timestamps_instead_of_raising():
    out = audit_inputs([row(published_at="2026-01-10")])
    assert [e["reason"] for e in out["errors"]] == ["published_at needs a timezone"]


def test_new_run_records_prereg_hash_and_git_state(tmp_path):
    prereg = tmp_path / "prereg.json"
    prereg.write_bytes(b'{"a": 1}\n')
    root = tmp_path / "runs"
    run = new_run(
        root,
        "2026-10-21T00:00:00Z",
        prereg,
        now=lambda: datetime(2026, 10, 21, 2, 0, tzinfo=UTC),
        git=lambda: ("abc123", True),
    )
    manifest = json.loads((run / "manifest.json").read_text())
    assert run == root / "20261021T0000Z-r20261021T020000Z"
    assert manifest["as_of_utc"] == "2026-10-21T00:00:00Z"
    assert manifest["prereg_sha256"] == hashlib.sha256(b'{"a": 1}\n').hexdigest()
    assert manifest["git_commit"] == "abc123"
    assert manifest["git_dirty"] is True
    assert manifest["created_at"] == "2026-10-21T02:00:00Z"


def test_new_run_never_overwrites_an_existing_root(tmp_path):
    prereg = tmp_path / "prereg.json"
    prereg.write_text("{}")
    args = (tmp_path / "runs", "2026-10-21T00:00:00Z", prereg)
    clock = dict(now=lambda: datetime(2026, 10, 21, 2, 0, tzinfo=UTC), git=lambda: ("x", False))
    new_run(*args, **clock)
    with pytest.raises(FileExistsError):
        new_run(*args, **clock)


def _run_with_inputs(tmp_path, entries):
    prereg = tmp_path / "prereg.json"
    prereg.write_text("{}")
    clock = dict(now=lambda: datetime(2026, 10, 21, 2, 0, tzinfo=UTC), git=lambda: ("x", False))
    run = new_run(tmp_path / "runs", "2026-10-21T00:00:00Z", prereg, **clock)
    manifest = json.loads((run / "manifest.json").read_text())
    for rel, body, retrieved in entries:
        path = run / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        manifest["inputs"].append(
            {
                "path": rel,
                "url": f"https://example.test/{rel}",
                "sha256": hashlib.sha256(body).hexdigest(),
                "bytes": len(body),
                "retrieved_at": retrieved,
            }
        )
    (run / "manifest.json").write_text(json.dumps(manifest))
    return run


def test_recorded_inputs_keeps_the_record_of_the_file_now_on_disk(tmp_path):
    run = _run_with_inputs(
        tmp_path,
        [
            ("public/raw/jp/X/a.pdf", b"old", "2026-10-21T03:00:00Z"),
            ("public/raw/sec/NVDA.json", b"{}", "2026-10-21T01:00:00Z"),
        ],
    )
    (run / "public/raw/jp/X/a.pdf").write_bytes(b"new")
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["inputs"].append(
        {
            "path": "public/raw/jp/X/a.pdf",
            "url": "https://example.test/a",
            "sha256": hashlib.sha256(b"new").hexdigest(),
            "bytes": 3,
            "retrieved_at": "2026-10-21T04:00:00Z",
        }
    )
    (run / "manifest.json").write_text(json.dumps(manifest))
    got = recorded_inputs(run, "public/raw/jp/X/")
    assert list(got) == ["public/raw/jp/X/a.pdf"]
    assert got["public/raw/jp/X/a.pdf"]["retrieved_at"] == "2026-10-21T04:00:00Z"


def test_recorded_inputs_refuses_a_file_changed_since_it_was_recorded(tmp_path):
    run = _run_with_inputs(tmp_path, [("public/raw/jp/X/a.pdf", b"old", "2026-10-21T03:00:00Z")])
    (run / "public/raw/jp/X/a.pdf").write_bytes(b"edited")
    with pytest.raises(ValueError, match="sha256"):
        recorded_inputs(run, "public/raw/jp/X/")


def ref(**over):
    base = {
        "issuer_id": "A",
        "metric": "revenue",
        "period_start": "2025-10-01",
        "period_end": "2025-12-31",
        "value": 100.0,
        "rounding": 1.0,
        "source_url": "https://example.test/press-release",
    }
    base.update(over)
    return base


def test_reconcile_matches_within_the_printed_rounding():
    rows = [row(value=96_221_400_000.0)]
    out = reconcile(rows, [ref(value=96_221e6, rounding=1e6)], "2026-10-21T00:00:00Z")
    assert out[0]["match"] is True
    assert out[0]["parsed"] == 96_221_400_000.0
    assert out[0]["document_id"] == "acc-1"


def test_reconcile_flags_a_difference_beyond_rounding():
    out = reconcile([row(value=102.0)], [ref(value=100.0, rounding=1.0)], "2026-10-21T00:00:00Z")
    assert out[0]["match"] is False
    assert out[0]["difference"] == 2.0


def test_reconcile_uses_the_version_available_at_the_as_of():
    out = reconcile([row(), restated()], [ref(value=100.0)], "2026-01-31T00:00:00Z")
    assert out[0]["match"] is True
    later = reconcile([row(), restated()], [ref(value=100.0)], "2026-02-28T00:00:00Z")
    assert later[0]["match"] is False


def test_reconcile_without_a_row_is_a_failed_check():
    out = reconcile([row()], [ref(metric="capex")], "2026-10-21T00:00:00Z")
    assert out[0]["match"] is False
    assert out[0]["parsed"] is None
    assert out[0]["reason"] == "no row"


def test_record_outputs_lists_derived_files_with_hashes_but_not_raw_inputs(tmp_path):
    run = _run_with_inputs(tmp_path, [("public/raw/sec/NVDA.json", b"{}", "2026-10-21T01:00:00Z")])
    (run / "public" / "rows").mkdir(parents=True)
    (run / "public" / "rows" / "NVDA.jsonl").write_bytes(b"row\n")
    (run / "public" / "universe.json").write_bytes(b"{}\n")
    record_outputs(run)
    record_outputs(run)  # idempotent
    outputs = json.loads((run / "manifest.json").read_text())["outputs"]
    assert [o["path"] for o in outputs] == ["public/rows/NVDA.jsonl", "public/universe.json"]
    assert outputs[0]["sha256"] == hashlib.sha256(b"row\n").hexdigest()
    assert outputs[0]["bytes"] == 4


def test_prereg_amendment_is_appended_with_both_hashes(tmp_path):
    run = _run_with_inputs(tmp_path, [])
    prereg = tmp_path / "prereg.json"
    before = json.loads((run / "manifest.json").read_text())["prereg_sha256"]
    prereg.write_text('{"selected": ["A"]}')
    record_prereg_amendment(
        run, prereg, "selected filled", now=lambda: datetime(2026, 10, 21, 3, 0, tzinfo=UTC)
    )
    manifest = json.loads((run / "manifest.json").read_text())
    assert manifest["prereg_sha256"] == before
    assert manifest["prereg_amendments"] == [
        {
            "at": "2026-10-21T03:00:00Z",
            "previous_sha256": before,
            "sha256": hashlib.sha256(b'{"selected": ["A"]}').hexdigest(),
            "reason": "selected filled",
        }
    ]
