from __future__ import annotations

import sys
from pathlib import Path

import pytest
from health.auth import GoogleHealthAuth
from streamlit.testing.v1 import AppTest

HEALTH_DIR = Path(__file__).resolve().parents[1]
APP_DIR = HEALTH_DIR / "app"
for path in (HEALTH_DIR, APP_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.seed_demo import seed  # noqa: E402


def app_source(data_dir: Path, body: str) -> str:
    return f"""
import os
from pathlib import Path
os.environ["GOOGLE_CLIENT_ID"] = "ui-test-client"
os.environ["GOOGLE_CLIENT_SECRET"] = "ui-test-secret"
import common
common.DATA_DIR = Path({str(data_dir)!r})
common.get_store.clear()
common.load_daily.clear()
common.load_sleep.clear()
common.load_intraday.clear()
{body}
"""


@pytest.fixture
def seeded_data_dir(tmp_path):
    seed(tmp_path / "health.duckdb")
    return tmp_path


def test_all_seeded_pages_render_without_exception(seeded_data_dir):
    pages = [
        ("overview_view", "overview_page", "概要"),
        ("sleep_view", "sleep_page", "睡眠"),
        ("activity_view", "activity_page", "活動"),
        ("heart_view", "heart_page", "心拍"),
        ("body_view", "body_page", "身体"),
        ("sync_view", "sync_page", "同期"),
        ("inventory_view", "inventory_page", "データ棚卸し"),
    ]
    for module, function, title in pages:
        source = app_source(
            seeded_data_dir,
            f"from views.{module} import {function}\n{function}()",
        )

        app = AppTest.from_string(source, default_timeout=20).run()

        assert not app.exception, function
        assert [item.value for item in app.title] == [title]


def test_main_renders_before_and_after_connection(tmp_path):
    for connected in (False, True):
        data_dir = tmp_path / ("connected" if connected else "disconnected")
        data_dir.mkdir()
        seed(data_dir / "health.duckdb")
        if connected:
            GoogleHealthAuth("ui-test-client", "ui-test-secret", data_dir)._store_tokens(
                {
                    "access_token": "demo-access",
                    "refresh_token": "demo-refresh",
                    "expires_in": 3600,
                    "scope": "demo",
                },
                existing=None,
            )
        source = app_source(data_dir, "from main import main\nmain()")

        app = AppTest.from_string(source, default_timeout=20).run()

        assert not app.exception, connected
        expected_title = "概要" if connected else "Health ダッシュボード"
        assert [item.value for item in app.title] == [expected_title]
