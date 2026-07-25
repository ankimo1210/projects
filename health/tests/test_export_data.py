from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

HEALTH_DIR = Path(__file__).resolve().parents[1]
if str(HEALTH_DIR) not in sys.path:
    sys.path.insert(0, str(HEALTH_DIR))

from health.store import Store  # noqa: E402
from scripts.export_data import main  # noqa: E402


def test_missing_db_path_is_rejected_instead_of_silently_creating_one(tmp_path):
    """A typo'd --db-path must not create a fresh empty database and export
    four empty files while reporting success."""
    missing = tmp_path / "typo.duckdb"
    out_dir = tmp_path / "export"

    with pytest.raises(SystemExit, match="no database"):
        main(["--db-path", str(missing), "--out-dir", str(out_dir)])

    assert not missing.exists()
    assert not out_dir.exists()


def test_existing_db_path_exports_successfully(tmp_path, capsys):
    db_path = tmp_path / "health.duckdb"
    store = Store(db_path)
    store.upsert_daily([("steps", date(2026, 1, 1), 1000.0)])
    store.close()
    out_dir = tmp_path / "export"

    main(["--db-path", str(db_path), "--out-dir", str(out_dir), "--format", "csv"])

    assert (out_dir / "daily_series.csv").exists()
    assert "wrote:" in capsys.readouterr().out
