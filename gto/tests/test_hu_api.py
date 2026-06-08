"""/api/hu/river — exact HU river equilibrium endpoint."""

import pytest
from fastapi.testclient import TestClient

try:
    import gto_py

    HAS_BINDING = hasattr(gto_py, "solve_hu_river")
except ImportError:
    HAS_BINDING = False

from gto.api.main import app

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not HAS_BINDING, reason="gto_py.solve_hu_river not built in this venv"
)


def test_river_solve_returns_strategy_and_exploitability():
    r = client.post(
        "/api/hu/river",
        json={
            "board": ["Ah", "Kd", "7s", "2c", "9h"],
            "pot_bb": 20.0,
            "effective_stack_bb": 90.0,
            "iterations": 1000,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Root strategy is a valid distribution over the listed actions.
    assert body["actions"][0] == "check"
    total = sum(a["freq"] for a in body["strategy"])
    assert abs(total - 1.0) < 1e-6
    # Exploitability is reported and small after a real solve.
    assert body["exploitability"] < 0.05
    assert body["iterations"] == 1000
    assert body["elapsed_secs"] > 0
    # Per-combo strategies cover the in-range combos (1326 - blockers).
    assert len(body["combos"]) == 1081
    c0 = body["combos"][0]
    assert len(c0["freqs"]) == len(body["actions"])
    assert abs(sum(c0["freqs"]) - 1.0) < 1e-6


def test_river_rejects_non_five_card_board():
    r = client.post(
        "/api/hu/river",
        json={"board": ["Ah", "Kd", "7s"], "pot_bb": 20.0, "effective_stack_bb": 90.0},
    )
    assert r.status_code == 422


def test_river_rejects_duplicate_card():
    r = client.post(
        "/api/hu/river",
        json={
            "board": ["Ah", "Ah", "7s", "2c", "9h"],
            "pot_bb": 20.0,
            "effective_stack_bb": 90.0,
            "iterations": 200,
        },
    )
    assert r.status_code == 422


def test_river_rejects_out_of_range_iterations():
    r = client.post(
        "/api/hu/river",
        json={
            "board": ["Ah", "Kd", "7s", "2c", "9h"],
            "pot_bb": 20.0,
            "effective_stack_bb": 90.0,
            "iterations": 99,
        },
    )
    assert r.status_code == 422


def test_turn_river_solve_returns_strategy_and_exploitability():
    r = client.post(
        "/api/hu/turn-river",
        json={
            "board": ["Ah", "Kd", "7s", "2c"],
            "pot_bb": 20.0,
            "effective_stack_bb": 90.0,
            "iterations": 300,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["actions"][0] == "check"
    assert abs(sum(a["freq"] for a in body["strategy"]) - 1.0) < 1e-6
    # Exact exploitability is reported (enumerated BR) even at low iters.
    assert body["exploitability"] >= 0
    assert body["iterations"] == 300
    assert len(body["combos"]) > 0
    assert abs(sum(body["combos"][0]["freqs"]) - 1.0) < 1e-6


def test_turn_river_rejects_non_four_card_board():
    r = client.post(
        "/api/hu/turn-river",
        json={"board": ["Ah", "Kd", "7s", "2c", "9h"], "pot_bb": 20.0, "effective_stack_bb": 90.0},
    )
    assert r.status_code == 422
