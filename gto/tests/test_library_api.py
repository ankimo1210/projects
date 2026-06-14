"""/api/library/flop board validation (#10): malformed boards are 422, not 500."""

from __future__ import annotations

from fastapi.testclient import TestClient
from gto.api.main import app

client = TestClient(app)


def test_flop_malformed_odd_length_board_returns_422():
    # 'Kh7d2' -> ['Kh','7d','2']; the 1-char '2' slipped past the count check
    # and crashed deep in canonicalize() as a 500 before the fix.
    r = client.get("/api/library/flop", params={"board": "Kh7d2", "position": "BTN"})
    assert r.status_code == 422


def test_flop_wrong_card_count_returns_422():
    r = client.get("/api/library/flop", params={"board": "KhQd", "position": "BTN"})
    assert r.status_code == 422
