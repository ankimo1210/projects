"""/api/trainer/answer input validation (#9): malformed input is 422, not 500."""

from __future__ import annotations

from fastapi.testclient import TestClient
from gto.api.main import app

client = TestClient(app)


def test_answer_bad_input_returns_422():
    r = client.post(
        "/api/trainer/answer",
        json={"hand": "ZZ", "position": "NOPE", "spot_type": "RFI", "chosen": "Raise"},
    )
    assert r.status_code == 422


def test_answer_valid_quiz_round_trips():
    q = client.get("/api/trainer/quiz").json()
    r = client.post(
        "/api/trainer/answer",
        json={
            "hand": q["hand"],
            "position": q["position"],
            "spot_type": q["spot_type"],
            "chosen": "Raise",
        },
    )
    assert r.status_code == 200
