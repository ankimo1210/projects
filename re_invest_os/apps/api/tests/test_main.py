"""API エンドポイントのテスト。"""

from __future__ import annotations

from api.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version() -> None:
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert "api" in body
    assert "engine" in body
    assert body["engine"] == "0.2.0"


def test_analyze_returns_assumption_score(base_assumptions) -> None:
    resp = client.post(
        "/analyze", json={"assumptions": base_assumptions.model_dump(by_alias=True)}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "assumption_score" in body
    assert "score" not in body
    s = body["assumption_score"]
    assert s["overall_risk"] in ("low", "medium", "high", "unknown")
    assert len(s["items"]) == 9
    dcy = body["analysis"]["kpi"]["dead_cross_year"]
    assert dcy is None or isinstance(dcy, int)


def test_sample_analysis() -> None:
    r = client.get("/sample/nishi-shinjuku")
    assert r.status_code == 200
    body = r.json()
    assert "analysis" in body
    assert "assumption_score" in body
    assert body["assumption_score"]["overall_risk"] in ("low", "medium", "high", "unknown")
    assert len(body["analysis"]["yearly_cashflows"]) == 10


def test_analyze_post_uses_request_data() -> None:
    """POST /analyze で渡したAssumptionsで分析されること。"""
    r = client.get("/sample/nishi-shinjuku")
    sample = r.json()["analysis"]["assumptions"]
    r2 = client.post("/analyze", json={"assumptions": sample})
    assert r2.status_code == 200
    body = r2.json()
    assert body["analysis"]["kpi"]["ltv"] == r.json()["analysis"]["kpi"]["ltv"]
