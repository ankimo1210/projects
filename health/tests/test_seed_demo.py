from __future__ import annotations

import sys
from pathlib import Path

import pytest

HEALTH_DIR = Path(__file__).resolve().parents[1]
if str(HEALTH_DIR) not in sys.path:
    sys.path.insert(0, str(HEALTH_DIR))

from scripts.seed_demo import main  # noqa: E402


def test_db_path_is_required():
    with pytest.raises(SystemExit):
        main([])


def test_refuses_to_overwrite_an_existing_database(tmp_path):
    target = tmp_path / "health.duckdb"
    target.write_bytes(b"pretend this is real health data")

    with pytest.raises(SystemExit, match="refusing to overwrite"):
        main(["--db-path", str(target)])

    assert target.read_bytes() == b"pretend this is real health data"


def test_force_allows_overwriting(tmp_path):
    target = tmp_path / "health.duckdb"
    target.write_bytes(b"pretend this is real health data")

    main(["--db-path", str(target), "--force"])

    assert target.stat().st_size > 0
    assert target.read_bytes() != b"pretend this is real health data"
