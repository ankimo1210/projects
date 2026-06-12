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
    # flop is now available (M1b): no "not yet" status, abstraction defaults present
    assert "status" not in caps["streets"]["flop"]
    assert caps["streets"]["flop"]["abstraction"]["buckets_river_default"] == 128


@pytest.mark.parametrize(
    "over",
    [
        {"variant": "plo"},
        {"table": "9max"},
        {"spot": "preflop"},
        # table=6max and game=tournament became SUPPORTED in M2
    ],
)
def test_unsupported_axes_422_with_pointer(over):
    r = client.post("/api/solve", json=_spec(**over))
    assert r.status_code == 422
    detail = r.json()["detail"]
    if isinstance(detail, dict):
        assert detail["see"] == "/api/solve/capabilities"


def test_flop_rake_rejected_422():
    # FlopSolver has no rake path; a raked flop spec must 422 (not submit).
    s = _spec()
    s["config"]["board"] = ["Ah", "Kd", "7s"]
    s["rake"] = {"model": "site"}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422
    assert "rake" in r.json()["detail"].lower()


def test_flop_infeasible_table_rejected_at_submit_422():
    # Exact (no bucketing) 100bb SRP flop is ~105 GB -> reject immediately.
    s = _spec()
    s["config"]["board"] = ["Ah", "Kd", "7s"]
    s["config"]["pot_bb"] = 5.0
    s["stack_bb"] = 97.5
    s["config"]["abstraction"] = {"buckets_river": 0, "max_table_gb": 12.0}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_flop_submit_poll_result_flow():
    s = _spec(iterations=40)
    s["config"]["board"] = ["Ah", "Kd", "7s"]
    s["config"]["pot_bb"] = 18.0
    s["stack_bb"] = 41.0
    s["config"]["pot_type"] = "3bet"
    s["config"]["abstraction"] = {"buckets_river": 16, "max_table_gb": 12.0}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 202, r.text
    handle = r.json()
    job_id = handle["job_id"]
    assert handle["kind"] == "flop"

    import time

    envelope = None
    for _ in range(600):  # up to ~60s for a tiny 40-iter flop solve
        st = client.get(f"/api/solve/jobs/{job_id}")
        assert st.status_code == 200
        body = st.json()
        if body["status"] == "done":
            envelope = body["result"]
            break
        if body["status"] == "error":
            raise AssertionError(f"flop job errored: {body['error']}")
        time.sleep(0.1)
    assert envelope is not None, "flop job did not finish in time"
    assert envelope["meta"]["street"] == "flop"
    assert envelope["meta"]["abstraction"] == {"buckets_river": 16, "buckets_turn": 0}
    assert envelope["meta"]["equilibrium_claim"] is True
    assert envelope["equity"] is None  # no flop equity
    assert sum(a["freq"] for a in envelope["strategy"]) == pytest.approx(1.0)


def test_job_status_unknown_404():
    assert client.get("/api/solve/jobs/deadbeef").status_code == 404
    assert client.delete("/api/solve/jobs/deadbeef").status_code == 404


# ----- M2: 6max position pairs (chart ranges) + tournament ------------------


def test_6max_bad_positions_422():
    s = _spec(table="6max")
    s["config"]["positions"] = ["UTG", "SB"]  # no BB
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422
    s["config"]["positions"] = ["HJ", "BB"]
    s["config"]["pot_type"] = "4bet"  # charts cover srp/3bet only
    assert client.post("/api/solve", json=s).status_code == 422


def test_chart_range_requires_6max():
    s = _spec()
    s["config"]["ranges"] = {"ip": "chart"}
    r = client.post("/api/solve", json=s)
    assert r.status_code == 422
    assert "6max" in r.json()["detail"]


def test_tournament_rejects_rake():
    s = _spec(game="tournament")
    s["rake"] = {"model": "site"}
    assert client.post("/api/solve", json=s).status_code == 422


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_6max_chart_solve_uses_chart_ranges():
    # BTN vs BB SRP river: OOP (BB defend-call range) excludes AA (BB 3bets
    # AA pre, so it never reaches an SRP river). The combo export is the
    # root actor's (OOP) range -> no AA combos.
    s = _spec(table="6max", iterations=200)
    s["config"]["positions"] = ["BTN", "BB"]
    s["config"]["pot_type"] = "srp"
    s["config"]["pot_bb"] = 5.5
    r = client.post("/api/solve", json=s)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["meta"]["equilibrium_claim"] is True
    combos = {(c["card_a"][0], c["card_b"][0]) for c in body["combo_strategies"]}
    assert ("A", "A") not in combos  # AA is 3bet pre, not in the call range
    # chart ranges echoed into the game spec (presets resolved server-side);
    # QQ calls its non-3bet remainder (30%) vs the BTN open
    assert "QQ:0.3" in body["meta"]["game_spec"]["config"]["ranges"]["oop"]


@pytest.mark.skipif(not HAS_BINDING, reason="gto_py not built")
def test_tournament_hu_shallow_solve():
    s = _spec(iterations=200, game="tournament", stack_bb=15.0)
    s["config"]["pot_bb"] = 5.0  # 2bb blinds + 1bb BB-ante folded into the pot
    r = client.post("/api/solve", json=s)
    assert r.status_code == 200, r.text
    assert r.json()["meta"]["game_spec"]["game"] == "tournament"


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
