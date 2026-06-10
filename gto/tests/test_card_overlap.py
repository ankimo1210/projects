"""B6 regression: card-overlap validation in gto_py and the equity API.

When hero, villain, or board share a physical card the matchup is impossible.
gto-core's `monte_carlo` only dedups the remaining deck, so an overlap used to
sail through and return nonsense equities with HTTP 200. The binding now
rejects any duplicate across the combined card set with a `ValueError`, which
the FastAPI equity router maps to a 4xx response.
"""

import pytest
from fastapi.testclient import TestClient

try:
    import gto_py

    HAS_BINDING = hasattr(gto_py, "equity")
except ImportError:
    HAS_BINDING = False

from gto.api.main import app

client = TestClient(app)

pytestmark = pytest.mark.skipif(
    not HAS_BINDING, reason="gto_py.equity not built in this venv"
)


def test_equity_binding_rejects_hero_villain_overlap():
    # Both players holding the ace of hearts is physically impossible.
    with pytest.raises(ValueError):
        gto_py.equity("Ah Kd", "Ah Qc", "", 2000)


def test_equity_binding_rejects_board_overlap():
    # Hero card also on the board.
    with pytest.raises(ValueError):
        gto_py.equity("Ah Kd", "Qs Jc", "Ah 7d 2c", 2000)


def test_equity_binding_accepts_disjoint_cards():
    # Sanity check: a clean, disjoint matchup still solves.
    result = gto_py.equity("Ah Kd", "Qs Jc", "7d 2c 9h", 2000)
    assert 0.0 <= result["hero_equity"] <= 1.0
    assert 0.0 <= result["villain_equity"] <= 1.0


def test_equity_api_rejects_overlap_with_4xx():
    r = client.get(
        "/api/equity",
        params={"hero": "Ah Kd", "villain": "Ah Qc", "iterations": 2000},
    )
    assert 400 <= r.status_code < 500, r.text


def test_equity_api_accepts_disjoint_cards():
    r = client.get(
        "/api/equity",
        params={
            "hero": "Ah Kd",
            "villain": "Qs Jc",
            "board": "7d 2c 9h",
            "iterations": 2000,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert abs(body["hero_equity"] + body["villain_equity"] + body["tie"] - 1.0) < 1e-6
