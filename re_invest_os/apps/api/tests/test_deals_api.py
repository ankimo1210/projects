"""deals + analysis_runs + bid_ranges + assumption_risks API テスト (Plan F2)。"""

from __future__ import annotations

import asyncio
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from fastapi.testclient import TestClient


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


@pytest.fixture(scope="function", autouse=True)
def setup_test_db(monkeypatch):
    import api.db as db_module
    from api.db import _build_engine, init_db

    test_engine = _build_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(db_module, "_engine", test_engine)
    monkeypatch.setattr(db_module, "_Session", None)
    _run(init_db())


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


def _sample_assumptions() -> dict:
    return {
        "property": {
            "property_type": "kuubun",
            "purchase_price_yen": 39_800_000,
            "land_value_yen": 8_000_000,
            "building_value_yen": 31_800_000,
            "structure": "rc",
            "building_completion_ym": "2011-04",
            "acquisition_year": 2026,
            "building_area_sqm": 38.4,
            "location_pref": "13",
        },
        "income": {"gpi_monthly_yen": 145_000, "vacancy_rate": 0.05},
        "opex": {
            "management_fee_rate": 0.05,
            "building_mgmt_yen": 240_000,
            "fixed_property_tax_yen": 120_000,
            "insurance_yen": 20_000,
        },
        "loan": {"loan_amount_yen": 27_860_000, "interest_rate": 0.020, "term_years": 30},
        "acquisition": {"equity_yen": 12_000_000, "acquisition_cost_rate": 0.07},
    }


# ────────────────────────────────────────
# deals CRUD
# ────────────────────────────────────────


def test_create_and_get_deal(client):
    res = client.post(
        "/deals",
        json={"title": "西新宿 504", "source_type": "manual"},
    )
    assert res.status_code == 201, res.text
    deal = res.json()
    assert deal["status"] == "analyzing"
    assert deal["title"] == "西新宿 504"

    got = client.get(f"/deals/{deal['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == deal["id"]
    assert got.json()["latest_analysis_run_id"] is None


def test_list_deals(client):
    client.post("/deals", json={"title": "A", "source_type": "manual"})
    client.post("/deals", json={"title": "B", "source_type": "url", "source_url": "https://x"})
    res = client.get("/deals")
    body = res.json()
    assert body["count"] == 2
    titles = {d["title"] for d in body["items"]}
    assert titles == {"A", "B"}


def test_patch_deal_status(client):
    deal = client.post("/deals", json={"title": "X", "source_type": "manual"}).json()
    res = client.patch(f"/deals/{deal['id']}", json={"status": "ready_to_bid"})
    assert res.status_code == 200
    assert res.json()["status"] == "ready_to_bid"


def test_invalid_status_rejected(client):
    deal = client.post("/deals", json={"title": "X", "source_type": "manual"}).json()
    res = client.patch(f"/deals/{deal['id']}", json={"status": "no_such_status"})
    assert res.status_code == 400


def test_delete_deal(client):
    deal = client.post("/deals", json={"title": "Z", "source_type": "manual"}).json()
    res = client.delete(f"/deals/{deal['id']}")
    assert res.status_code == 204
    assert client.get(f"/deals/{deal['id']}").status_code == 404


# ────────────────────────────────────────
# analysis_runs
# ────────────────────────────────────────


def test_create_analysis_run(client):
    deal = client.post("/deals", json={"title": "Run-test", "source_type": "manual"}).json()
    res = client.post(
        f"/deals/{deal['id']}/analysis_runs",
        json={"assumptions": _sample_assumptions()},
    )
    assert res.status_code == 201, res.text
    run = res.json()
    assert run["deal_id"] == deal["id"]
    assert run["engine_version"]
    assert "kpi" in run["metrics_json"]["analysis"]
    # 親 deal の latest が更新されている
    got_deal = client.get(f"/deals/{deal['id']}").json()
    assert got_deal["latest_analysis_run_id"] == run["id"]


def test_invalid_assumptions_returns_422(client):
    deal = client.post("/deals", json={"title": "Run-x", "source_type": "manual"}).json()
    res = client.post(
        f"/deals/{deal['id']}/analysis_runs",
        json={"assumptions": {"property": {}}},
    )
    assert res.status_code == 422


# ────────────────────────────────────────
# bid_ranges API
# ────────────────────────────────────────


def _create_run(client) -> str:
    deal = client.post("/deals", json={"title": "BR", "source_type": "manual"}).json()
    run = client.post(
        f"/deals/{deal['id']}/analysis_runs",
        json={"assumptions": _sample_assumptions()},
    ).json()
    return run["id"]


def test_generate_and_get_bid_ranges(client):
    run_id = _create_run(client)
    gen = client.post(f"/analysis_runs/{run_id}/bid_ranges")
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["asking_price_yen"] == 39_800_000
    assert body["current_case_price"] is not None
    assert body["base_stress_price"] is not None
    assert body["conservative_stress_price"] is not None
    # 単調性
    assert (
        body["conservative_stress_price"]
        <= body["base_stress_price"]
        <= body["current_case_price"]
    )
    # gap 計算
    assert (
        body["gap_to_base_stress_price_yen"]
        == body["base_stress_price"] - body["asking_price_yen"]
    )

    got = client.get(f"/analysis_runs/{run_id}/bid_ranges")
    assert got.status_code == 200
    assert got.json()["current_case_price"] == body["current_case_price"]


def test_bid_ranges_replaces_previous(client):
    run_id = _create_run(client)
    first = client.post(f"/analysis_runs/{run_id}/bid_ranges").json()
    second = client.post(f"/analysis_runs/{run_id}/bid_ranges").json()
    # 新 id (古いものは消えている)
    assert first["id"] != second["id"]


def test_bid_ranges_404_for_missing_run(client):
    res = client.post("/analysis_runs/no-such-id/bid_ranges")
    assert res.status_code == 404


# ────────────────────────────────────────
# assumption_risks API
# ────────────────────────────────────────


def test_generate_assumption_risks(client):
    run_id = _create_run(client)
    res = client.post(f"/analysis_runs/{run_id}/assumption_risks", json={})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["analysis_run_id"] == run_id
    categories = {item["category"] for item in body["items"]}
    assert categories == {
        "rent", "vacancy", "opex", "repair", "interest_rate", "exit_price",
        "tax", "sale_year", "acquisition_cost",
    }
    # 全項目に reason と confidence
    for item in body["items"]:
        assert item["confidence"] in ("A", "B", "C", "D")
        assert item["risk_level"] in ("low", "medium", "high", "unknown")
        assert item["reason"]
    assert body["summary"]


def test_get_assumption_risks(client):
    run_id = _create_run(client)
    client.post(f"/analysis_runs/{run_id}/assumption_risks", json={})
    res = client.get(f"/analysis_runs/{run_id}/assumption_risks")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 9


def test_assumption_risks_replaces(client):
    run_id = _create_run(client)
    first = client.post(f"/analysis_runs/{run_id}/assumption_risks", json={}).json()
    second = client.post(f"/analysis_runs/{run_id}/assumption_risks", json={}).json()
    # 同じ category だが id は新規
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_assumption_risks_market_high_rent(client):
    """市場ベンチマーク上限超で rent risk が high になる。"""
    run_id = _create_run(client)
    market = {
        "rent_per_sqm_monthly_p75": 2000,  # 145000 / 38.4 ≒ 3776 >> 2000 → high
    }
    res = client.post(
        f"/analysis_runs/{run_id}/assumption_risks", json={"market": market}
    )
    rent = next(item for item in res.json()["items"] if item["category"] == "rent")
    assert rent["risk_level"] == "high"
