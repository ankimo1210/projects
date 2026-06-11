"""GameSpec endpoint: capabilities, 422 matrix, envelope shape, deprecation."""

import pytest
from fastapi.testclient import TestClient
from gto.api.main import app

client = TestClient(app)

try:
    import gto_py

    HAS_BINDING = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS_BINDING = False


def _spec(**over):
    base = {
        "stack_bb": 90.0,
        "config": {
            "pot_bb": 20.0,
            "board": ["Ah", "Kd", "7s", "2c", "9h"],
        },
    }
    base.update(over)
    return base


def test_capabilities_shape():
    r = client.get("/api/solve/capabilities")
    assert r.status_code == 200
    caps = r.json()
    assert caps["variant"] == ["nlhe"]
    assert caps["streets"]["flop"]["cost"] == "async"


@pytest.mark.parametrize(
    "over",
    [
        {"variant": "plo"},
        {"table": "6max"},
        {"game": "tournament"},
        {"spot": "preflop"},
    ],
)
def test_unsupported_axes_422_with_pointer(over):
    r = client.post("/api/solve", json=_spec(**over))
    assert r.status_code == 422
    detail = r.json()["detail"]
    if isinstance(detail, dict):
        assert detail["see"] == "/api/solve/capabilities"


def test_flop_board_is_m1b_422():
    s = _spec()
    s["config"]["board"] = ["Ah", "Kd", "7s"]
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_river_solve_envelope():
    s = _spec(iterations=200)
    s["rake"] = {"model": "site"}
    s["config"]["ranges"] = {"oop": "QQ,JJ", "ip": "preset"}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["equilibrium_claim"] is True
    assert body["meta"]["rake"] == {"pct": 0.05, "cap_bb": 3.0}
    assert body["exploitability"]["nashconv_bb"] == pytest.approx(
        body["exploitability"]["br_gain_ip"] + body["exploitability"]["br_gain_oop"]
    )
    assert 0.0 < body["equity"]["ip"] < 1.0
    # OOP range was QQ+JJ -> 12 combos in the export
    assert len(body["combo_strategies"]) == 12
    # rake leaks value
    assert body["ev"]["ip"] + body["ev"]["oop"] < 0.0


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_hu_endpoints_carry_deprecation_headers():
    r = client.post(
        "/api/hu/river",
        json={"board": ["Ah", "Kd", "7s", "2c", "9h"], "iterations": 100},
    )
    assert r.status_code == 200
    assert r.headers.get("deprecation") == "true"
