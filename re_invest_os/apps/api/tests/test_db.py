"""DB (SQLite) の CRUD テスト。asyncio を直接使い pytest-asyncio を回避。"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from api.db import _build_engine, get_analysis, init_db, save_analysis

# テスト専用のインメモリ DB を使う


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(scope="function", autouse=True)
def setup_test_db(monkeypatch):
    """テスト用インメモリ DB を init する。"""
    import api.db as db_module

    test_engine = _build_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(db_module, "_engine", test_engine)
    monkeypatch.setattr(db_module, "_Session", None)
    _run(init_db())


def test_save_and_get() -> None:
    analysis_id = _run(
        save_analysis(
            source_type="manual",
            source_ref=None,
            engine_version="0.1.0",
            prompt_versions={"classify_document": "v1", "property_brochure": "v4"},
            extracted=None,
            assumptions={"property": {"purchase_price_yen": 39_800_000}},
            analysis_result={"kpi": {"cap_rate": 0.03}},
            score_total=36.5,
            score_result={"total": 36.5, "evaluation": "要注意"},
            noi_cap=0.03,
            dscr_y1=0.96,
            atcf_y1=-45_362,
        )
    )

    assert len(analysis_id) > 0

    data = _run(get_analysis(analysis_id))
    assert data is not None
    assert data["id"] == analysis_id
    assert data["score_total"] == 36.5
    assert data["noi_cap"] == pytest.approx(0.03)
    assert data["dscr_y1"] == pytest.approx(0.96)
    assert data["atcf_y1"] == -45_362
    assert data["assumptions"]["property"]["purchase_price_yen"] == 39_800_000
    assert data["score_result"]["evaluation"] == "要注意"


def test_get_not_found() -> None:
    data = _run(get_analysis("nonexistent-id"))
    assert data is None
