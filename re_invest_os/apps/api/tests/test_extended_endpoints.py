"""max_offer / sensitivity / cross_asset エンドポイントのテスト。"""

from __future__ import annotations

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def _sample_assumptions_dict() -> dict:
    r = client.get("/sample/nishi-shinjuku")
    return r.json()["analysis"]["assumptions"]


def test_max_offer_default_targets() -> None:
    a = _sample_assumptions_dict()
    r = client.post("/max_offer", json={"assumptions": a})
    assert r.status_code == 200
    body = r.json()
    assert "max_price_yen" in body
    assert "binding_constraints" in body


def test_max_offer_with_targets() -> None:
    a = _sample_assumptions_dict()
    targets = {
        "min_dscr": 1.0,
        "min_irr": -0.10,
        "min_first_year_atcf_yen": -1_000_000,
    }
    r = client.post("/max_offer", json={"assumptions": a, "targets": targets})
    assert r.status_code == 200
    body = r.json()
    assert body["max_price_yen"] > 0


def test_sensitivity() -> None:
    a = _sample_assumptions_dict()
    r = client.post("/sensitivity", json={"assumptions": a})
    assert r.status_code == 200
    body = r.json()
    assert "base" in body
    assert len(body["scenarios"]) == 7


def test_cross_asset_default_benchmarks() -> None:
    r = client.post("/cross_asset", json={"re_after_tax_irr": 0.04})
    assert r.status_code == 200
    body = r.json()
    assert len(body["rows"]) >= 5
    assert "disclaimer" in body
    assert "推奨" in body["disclaimer"]


def test_cross_asset_with_none_irr() -> None:
    r = client.post("/cross_asset", json={"re_after_tax_irr": None})
    assert r.status_code == 200


def test_max_offer_validation_rejects_extras() -> None:
    """extra='forbid' により未知フィールドはエラー。"""
    r = client.post(
        "/max_offer",
        json={"assumptions": _sample_assumptions_dict(), "unknown": "x"},
    )
    assert r.status_code == 422
