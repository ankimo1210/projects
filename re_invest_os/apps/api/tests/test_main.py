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
    assert body["engine"] == "0.1.0"


def test_sample_analysis() -> None:
    r = client.get("/sample/nishi-shinjuku")
    assert r.status_code == 200
    body = r.json()
    assert "analysis" in body
    assert "score" in body
    assert 0 <= body["score"]["total"] <= 100
    assert len(body["analysis"]["yearly_cashflows"]) == 10


def test_analyze_post_uses_request_data() -> None:
    """POST /analyze で渡したAssumptionsで分析されること。"""
    r = client.get("/sample/nishi-shinjuku")
    sample = r.json()["analysis"]["assumptions"]
    r2 = client.post("/analyze", json={"assumptions": sample})
    assert r2.status_code == 200
    body = r2.json()
    assert body["analysis"]["kpi"]["ltv"] == r.json()["analysis"]["kpi"]["ltv"]
