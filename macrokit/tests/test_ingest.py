from datetime import UTC, date, datetime
from pathlib import Path

from macrokit.catalog import load_catalog
from macrokit.ingest import default_catalog_root, ingest_one
from macrokit.pit import as_of, latest
from macrokit.store import connect

FIXTURES = Path(__file__).parent / "fixtures"


class FakeAdapter:
    """Serves the recorded ALFRED payload, so this test needs no network."""

    source = "alfred"

    def __init__(self, payload: bytes):
        self.payload = payload
        self.fetch_count = 0

    def fetch_raw(self, indicator, start):
        self.fetch_count += 1
        return self.payload, "https://example.invalid/fred", 200

    def parse(self, indicator, raw, *, ingested_at):
        from macrokit.sources.alfred import AlfredAdapter

        return AlfredAdapter(api_key="dummy").parse(indicator, raw, ingested_at=ingested_at)


def test_the_production_catalog_loads_and_contains_core_pce():
    catalog = load_catalog(default_catalog_root())
    assert "us_core_pce" in catalog
    assert catalog["us_core_pce"].source_ref["series_id"] == "PCEPILFE"


def test_ingest_stores_a_snapshot_and_inserts_rows(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")

    report = ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )

    assert report.changed is True
    assert report.rows_inserted > 0
    assert list((tmp_path / "raw").rglob("*payload.json"))


def test_a_second_unchanged_ingest_inserts_nothing_new(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")
    kwargs = dict(
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
    )

    ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 17, tzinfo=UTC), **kwargs)
    second = ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 18, tzinfo=UTC), **kwargs)

    assert second.changed is False
    assert second.rows_inserted == 0
    assert second.skipped_reason == "content unchanged"
    # The payload must NOT be parsed again when nothing changed.
    assert adapter.fetch_count == 2


def test_point_in_time_query_works_after_ingest(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")
    ingest_one(
        catalog["us_core_pce"],
        con=con,
        data_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )

    early = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    current = latest(con, "us_core_pce")

    # The whole point of the platform: the value you would have seen in April
    # 2024 differs from today's value for the same month.
    assert early.loc[date(2024, 1, 1)] != current.loc[date(2024, 1, 1)]
