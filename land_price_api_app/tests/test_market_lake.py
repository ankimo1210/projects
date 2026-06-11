"""market_lake.py / db._market_lake のテスト（ネットワーク非依存・一時 DuckDB）。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import db  # noqa: E402
import market_lake as ml  # noqa: E402


# ── パース ───────────────────────────────────────────────────────────────────


def test_parse_price_ja():
    assert ml.parse_price_ja("3,900万円") == 39_000_000.0
    assert ml.parse_price_ja("1億2,000万円") == 120_000_000.0
    assert ml.parse_price_ja("710,000(円/㎡)") == 710_000.0
    assert ml.parse_price_ja("") is None
    assert ml.parse_price_ja("非公開") is None


def test_parse_year_quarter():
    assert ml.parse_year_quarter("2024年第4四半期") == (2024, 4)
    assert ml.parse_year_quarter("1995年") == (1995, None)
    assert ml.parse_year_quarter(None) == (None, None)


# ── エリア・タイル ───────────────────────────────────────────────────────────


def test_area_bboxes_groups():
    boxes = ml.area_bboxes(["kanto", "okinawa"])
    assert "pref13" in boxes and "okinawa_main" in boxes
    with pytest.raises(ValueError):
        ml.area_bboxes(["mars"])


def test_target_tiles_dedup_and_sorted():
    # 関東の県 bbox は重なる → set で dedup される
    tiles = ml.target_tiles(["kanto"], 13)
    assert len(tiles) == len(set(tiles))
    assert tiles == sorted(tiles)
    assert len(tiles) > 100  # 関東で最低でも数百枚


def test_build_worklist_counts():
    work = ml.build_worklist(["xpt001", "xkt002"], ["okinawa"], [2023, 2024], 13)
    tiles = ml.target_tiles(["okinawa"], 13)
    xpt = [w for w in work if w.layer == "xpt001"]
    gis = [w for w in work if w.layer == "xkt002"]
    assert len(xpt) == len(tiles) * 2  # 年ごと
    assert len(gis) == len(tiles)  # window なし
    assert {w.window for w in xpt} == {"2023", "2024"}
    assert {w.window for w in gis} == {"-"}


# ── 正規化 ───────────────────────────────────────────────────────────────────


def _tx_feature(price="4,000万円", area="40㎡", when="2024年第2四半期"):
    return {
        "geometry": {"type": "Point", "coordinates": [127.68, 26.21]},
        "properties": {
            "u_transaction_price_total_ja": price,
            "u_area_ja": area,
            "point_in_time_name_ja": when,
            "land_type_name_ja": "中古マンション等",
            "district_name_ja": "おもろまち",
            "city_code": "47201",
            "u_construction_year_ja": "2010年",
        },
    }


def test_normalize_tx_features():
    rows = ml.normalize_tx_features([_tx_feature(), {"geometry": None, "properties": {}}])
    assert len(rows) == 1
    r = rows[0]
    assert r["price_yen"] == 40_000_000.0
    assert r["price_per_sqm"] == pytest.approx(1_000_000.0)  # 単価欄なし → price/area
    assert (r["year"], r["quarter"]) == (2024, 2)
    assert r["city_code"] == "47201"
    assert "u_transaction_price_total_ja" in r["raw_properties"]  # 生 JSON 保持


def test_normalize_pop_features():
    feat = {
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[127.6, 26.2], [127.61, 26.2], [127.61, 26.21], [127.6, 26.21], [127.6, 26.2]]],
        },
        "properties": {"PT00_2025": 1200.5, "PT00_2050": 1100.0, "PT12_2030": 99.0, "HITOKU": ""},
    }
    rows = ml.normalize_pop_features([feat])
    assert {(r["year"], r["population"]) for r in rows} == {(2025, 1200.5), (2050, 1100.0)}


def test_normalize_gis_features():
    feat = {
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
        "properties": {"use_area_ja": "近隣商業地域"},
    }
    rows = ml.normalize_gis_features([feat, {"geometry": None}])
    assert len(rows) == 1
    assert "近隣商業地域" in rows[0]["properties"]


# ── DB ラウンドトリップ + resume ─────────────────────────────────────────────


@pytest.fixture
def lake_conn(tmp_path):
    conn = db.get_connection(db_path=tmp_path / "lake_test.duckdb")
    db.create_market_lake_tables(conn)
    yield conn
    conn.close()


def test_replace_lake_tx_idempotent(lake_conn):
    rows = ml.normalize_tx_features([_tx_feature(), _tx_feature(price="5,000万円")])
    db.replace_lake_tx(lake_conn, 13, 7000, 3400, "2024", rows)
    db.replace_lake_tx(lake_conn, 13, 7000, 3400, "2024", rows)  # 再実行で重複しない
    n = lake_conn.execute("SELECT COUNT(*) FROM lake_tx_points").fetchone()[0]
    assert n == 2


def test_mark_and_resume_keys(lake_conn):
    db.mark_lake_synced(lake_conn, "xpt001", 13, 7000, 3400, "2024", 2)
    db.mark_lake_synced(lake_conn, "xpt001", 13, 7000, 3400, "2024", 3)  # 再記録も1行
    keys = db.lake_synced_keys(lake_conn)
    assert ("xpt001", 13, 7000, 3400, "2024") in keys
    n = lake_conn.execute("SELECT COUNT(*) FROM lake_tile_state").fetchone()[0]
    assert n == 1


def test_run_sync_offline_and_resume(lake_conn, monkeypatch):
    calls = {"n": 0}

    def fake_fetch(layer, z, x, y, window):
        calls["n"] += 1
        if layer == "xpt001":
            return {"features": [_tx_feature()]}
        if layer == "xkt013":
            return {"features": []}
        return {"features": []}

    monkeypatch.setattr(ml, "fetch_tile", fake_fetch)

    stats1 = ml.run_sync(
        lake_conn, ["xpt001"], ["okinawa"], [2024], z=13, workers=2, limit_tiles=10
    )
    assert stats1["ok"] == 10
    assert calls["n"] == 10
    # resume: 同じ 10 タイルはスキップされ、次の 10 件に進む
    stats2 = ml.run_sync(
        lake_conn, ["xpt001"], ["okinawa"], [2024], z=13, workers=2, limit_tiles=10
    )
    assert stats2["ok"] == 10
    keys = db.lake_synced_keys(lake_conn)
    assert len(keys) == 20

    s = db.lake_stats(lake_conn)
    assert s["tx_points"] == 20
    assert s["tiles_synced"]["xpt001"] == 20
