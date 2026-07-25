import stat
from datetime import date

import pandas as pd
import pytest
from health.export import EXPORT_TABLES, export_tables
from health.store import Store

try:
    import pyarrow

    HAS_PYARROW = pyarrow is not None
except ImportError:
    HAS_PYARROW = False


@pytest.fixture
def store(tmp_path):
    created = Store(tmp_path / "health.duckdb")
    created.upsert_daily([("steps", date(2026, 1, 1), 1000.0)])
    yield created
    created.close()


def test_export_writes_one_file_per_table(store, tmp_path):
    out_dir = tmp_path / "export"

    written = export_tables(store, out_dir, "parquet")

    assert [path.name for path in written] == [f"{t}.parquet" for t in EXPORT_TABLES]
    assert all(path.exists() and path.stat().st_size > 0 for path in written)
    if HAS_PYARROW:
        daily = pd.read_parquet(out_dir / "daily_series.parquet")
        row = daily.iloc[0]
        assert row["metric"] == "steps"
        assert row["date"] == date(2026, 1, 1)
        assert row["value"] == 1000.0


def test_exported_csv_contains_the_stored_row(store, tmp_path):
    out_dir = tmp_path / "export"

    export_tables(store, out_dir, "csv")

    daily = pd.read_csv(out_dir / "daily_series.csv", parse_dates=["date"])
    row = daily.iloc[0]
    assert row["metric"] == "steps"
    assert row["date"].date() == date(2026, 1, 1)
    assert row["value"] == 1000.0


def test_exported_files_are_private(store, tmp_path):
    out_dir = tmp_path / "export"

    written = export_tables(store, out_dir, "csv")

    assert stat.S_IMODE(out_dir.stat().st_mode) == 0o700
    for path in written:
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_unknown_format_is_rejected(store, tmp_path):
    with pytest.raises(ValueError, match="unsupported export format"):
        export_tables(store, tmp_path / "export", "sqlite")


def test_export_handles_a_single_quote_in_the_output_path(store, tmp_path):
    out_dir = tmp_path / "kazu's export"

    written = export_tables(store, out_dir, "csv")

    daily = pd.read_csv(out_dir / "daily_series.csv", parse_dates=["date"])
    row = daily.iloc[0]
    assert row["metric"] == "steps"
    assert row["date"].date() == date(2026, 1, 1)
    assert row["value"] == 1000.0
    assert all(path.exists() and path.stat().st_size > 0 for path in written)
