from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from macrokit.catalog import load_catalog
from macrokit.ingest import _sniff_suffix, default_catalog_root, ingest_one
from macrokit.pit import as_of, latest
from macrokit.store import connect

FIXTURES = Path(__file__).parent / "fixtures"


class FakeAdapter:
    """Serves the recorded ALFRED payload, so this test needs no network."""

    source = "alfred"

    def __init__(self, payload: bytes):
        self.payload = payload
        self.fetch_count = 0
        self.parse_count = 0

    def fetch_raw(self, indicator, start):
        self.fetch_count += 1
        return self.payload, "https://example.invalid/fred", 200

    def parse(self, indicator, raw, *, ingested_at):
        self.parse_count += 1
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
        raw_root=tmp_path / "raw",
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
        raw_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
    )

    ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 17, tzinfo=UTC), **kwargs)
    second = ingest_one(catalog["us_core_pce"], now=datetime(2026, 8, 18, tzinfo=UTC), **kwargs)

    assert second.changed is False
    assert second.rows_inserted == 0
    assert second.skipped_reason == "content unchanged"
    # Fetched twice, but parsed only once: the second ingest short-circuits on
    # the unchanged content hash before reaching the parser. Asserting
    # rows_inserted == 0 alone cannot show this -- INSERT OR IGNORE would also
    # report 0 if the parse ran and every row collided on the primary key.
    assert adapter.fetch_count == 2
    assert adapter.parse_count == 1


def test_point_in_time_query_works_after_ingest(tmp_path):
    catalog = load_catalog(default_catalog_root())
    adapter = FakeAdapter((FIXTURES / "alfred_pcepilfe.json").read_bytes())
    con = connect(tmp_path / "db" / "macrokit.duckdb")
    ingest_one(
        catalog["us_core_pce"],
        con=con,
        raw_root=tmp_path / "raw",
        adapter=adapter,
        start=date(2024, 1, 1),
        now=datetime(2026, 8, 17, tzinfo=UTC),
    )

    early = as_of(con, "us_core_pce", datetime(2024, 4, 10, tzinfo=UTC))
    current = latest(con, "us_core_pce")

    # The whole point of the platform: the value you would have seen in April
    # 2024 differs from today's value for the same month.
    assert early.loc[date(2024, 1, 1)] != current.loc[date(2024, 1, 1)]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"", "bin"),  # empty payload: neither format, don't guess
        (b"\xef\xbb\xbf", "bin"),  # BOM with nothing after it is still empty
        (b'\xef\xbb\xbf{"a": 1}', "json"),  # BOM-prefixed JSON
        (b"\xef\xbb\xbfdate,value\n2024-01-01,1", "csv"),  # BOM-prefixed CSV
        (b'{"a": 1}', "json"),
        (b"date,value\n2024-01-01,1", "csv"),
    ],
)
def test_sniff_suffix_strips_a_bom_before_guessing(content, expected):
    # bytes.lstrip() does not strip a UTF-8 BOM, and Japanese ministry CSVs
    # commonly carry one -- without stripping it first, both an empty
    # payload and a BOM-prefixed payload (even a JSON one) were
    # misclassified as "csv".
    assert _sniff_suffix(content) == expected
