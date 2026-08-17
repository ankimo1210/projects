import json
from datetime import UTC, date, datetime
from pathlib import Path

from macrokit.catalog import load_catalog
from macrokit.ingest import default_catalog_root, ingest_one
from macrokit.status import compute_status, load_validated
from macrokit.store import connect

FIXTURES = Path(__file__).parent / "fixtures"


class FakeAdapter:
    source = "alfred"

    def fetch_raw(self, indicator, start):
        return (FIXTURES / "alfred_pcepilfe.json").read_bytes(), "https://example.invalid", 200

    def parse(self, indicator, raw, *, ingested_at):
        from macrokit.sources.alfred import AlfredAdapter

        return AlfredAdapter(api_key="dummy").parse(indicator, raw, ingested_at=ingested_at)


def test_an_indicator_with_no_snapshot_is_only_declared(tmp_path):
    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "declared"


def test_status_reaches_parsed_after_a_successful_ingest(tmp_path):
    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=FakeAdapter(),
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "parsed"


def test_status_is_fetching_when_snapshots_exist_but_no_rows_do(tmp_path):
    # This is the state that matters most for Japan: bytes are banked even
    # though nothing has been parsed yet.
    from macrokit.snapshot import save_snapshot

    catalog = load_catalog(default_catalog_root())
    con = connect(tmp_path / "t.duckdb")
    save_snapshot(
        tmp_path / "raw",
        "alfred",
        "us_core_pce",
        b"{}",
        ingested_at=datetime(2026, 8, 17, tzinfo=UTC),
        url="https://example.invalid",
        http_status=200,
    )
    got = compute_status(
        catalog["us_core_pce"], con=con, data_root=tmp_path / "raw", validated=set()
    )
    assert got == "fetching"


def test_validated_is_read_from_the_marker_file(tmp_path):
    (tmp_path / "validated.json").write_text(
        json.dumps({"indicators": ["us_core_pce"]}), encoding="utf-8"
    )
    assert load_validated(tmp_path) == {"us_core_pce"}
    assert load_validated(tmp_path / "missing") == set()
