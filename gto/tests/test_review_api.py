"""Tests for the review API router (POST /api/review/parse)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _build_app():
    """Use the full app when available; otherwise mount only the review router.

    gto.api.main imports routers that need the gto_py Rust extension. These
    tests are pure Python, so they must not abort collection when the
    extension is not built in the current venv.
    """
    try:
        from gto.api.main import app
    except ModuleNotFoundError:
        from fastapi import FastAPI
        from gto.api.routers import review

        app = FastAPI()
        app.include_router(review.router, prefix="/api")
    return app


FIXTURES = Path(__file__).parent / "fixtures"

client = TestClient(_build_app())


def load(name: str) -> str:
    return (FIXTURES / name).read_text()


def post_parse(text: str):
    return client.post("/api/review/parse", json={"text": text})


# ---------------------------------------------------------------------------
# Happy path: single fixture hand
# ---------------------------------------------------------------------------


def test_parse_single_hand() -> None:
    res = post_parse(load("ps_6max_preflop_fold.txt"))
    assert res.status_code == 200
    body = res.json()
    assert body["errors"] == []
    assert len(body["hands"]) == 1

    hand = body["hands"][0]
    assert hand["hand_id"] == "243598731121"
    assert hand["stakes"] == {"small_blind": 0.5, "big_blind": 1.0, "currency": "USD"}
    assert hand["table_name"] == "Aenna III"
    assert hand["max_players"] == 6
    assert hand["button_seat"] == 3
    assert hand["zoom"] is False
    assert hand["hero_name"] == "Hero"
    assert hand["hero_cards"] == ["7h", "2s"]
    assert len(hand["players"]) == 6
    assert hand["positions"]["Hero"] == "HJ"

    pre = hand["actions"]["preflop"]
    assert [(a["actor"], a["action"]) for a in pre[:2]] == [
        ("frank_tank", "fold"),
        ("Hero", "fold"),
    ]
    assert hand["actions"]["flop"] == []
    assert hand["winners"] == [{"player": "carol99", "amount": 2.5, "pot": "pot"}]
    assert hand["total_pot"] == pytest.approx(2.5)


def test_parse_attaches_deviation_flag() -> None:
    res = post_parse(load("ps_6max_preflop_fold.txt"))
    assert res.status_code == 200
    dev = res.json()["hands"][0]["preflop_deviation"]
    assert dev is not None
    assert dev["flag"] == "ok"
    assert dev["hand"] == "72o"
    assert dev["spot_type"] == "RFI"
    assert dev["position"] == "HJ"
    assert dev["hero_action"] == "F"
    assert dev["gto_action"] == "F"
    assert dev["gto_frequencies"] == {"R": 0, "F": 100}


def test_parse_multiple_hands() -> None:
    text = "\n\n".join(
        load(n)
        for n in (
            "ps_6max_preflop_fold.txt",
            "ps_zoom_multistreet_showdown.txt",
            "ps_3handed_allin_uncalled.txt",
        )
    )
    res = post_parse(text)
    assert res.status_code == 200
    body = res.json()
    assert body["errors"] == []
    assert [h["hand_id"] for h in body["hands"]] == [
        "243598731121",
        "244112233445",
        "245000111222",
    ]
    # zoom showdown hand keeps full street/board/showdown detail through JSON
    zoom = body["hands"][1]
    assert zoom["zoom"] is True
    assert zoom["board"] == ["Kc", "7d", "2c", "5h", "9s"]
    assert zoom["preflop_deviation"]["flag"] == "tight"


# ---------------------------------------------------------------------------
# Malformed / partial input
# ---------------------------------------------------------------------------


def test_garbage_text_returns_errors_list() -> None:
    res = post_parse("totally not a hand\nfoo bar baz\n")
    assert res.status_code == 200
    body = res.json()
    assert body["hands"] == []
    assert len(body["errors"]) == 1
    err = body["errors"][0]
    assert err["index"] == 0
    assert err["message"]
    assert err["snippet"]


def test_mixed_good_and_garbage() -> None:
    text = (
        load("ps_6max_preflop_fold.txt")
        + "\n\nPokerStars Hand #999: garbage that should not parse\njunk line\n"
    )
    res = post_parse(text)
    assert res.status_code == 200
    body = res.json()
    assert len(body["hands"]) == 1
    assert body["hands"][0]["hand_id"] == "243598731121"
    assert len(body["errors"]) == 1
    assert "999" in body["errors"][0]["snippet"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_empty_text_returns_422() -> None:
    res = post_parse("")
    assert res.status_code == 422


def test_whitespace_only_text_returns_422() -> None:
    res = post_parse("   \n\t  ")
    assert res.status_code == 422


def test_missing_text_field_returns_422() -> None:
    res = client.post("/api/review/parse", json={})
    assert res.status_code == 422


def test_oversized_text_returns_422() -> None:
    # Regression: unbounded input used to be parsed in full (500+ MB peak
    # memory for a ~20 MB paste). Anything past MAX_TEXT_CHARS is rejected.
    from gto.api.routers.review import MAX_TEXT_CHARS

    res = post_parse("x" * (MAX_TEXT_CHARS + 1))
    assert res.status_code == 422


def test_text_at_limit_is_accepted() -> None:
    text = load("ps_6max_preflop_fold.txt")
    from gto.api.routers.review import MAX_TEXT_CHARS

    padded = text + " " * (MAX_TEXT_CHARS - len(text))
    assert len(padded) == MAX_TEXT_CHARS
    res = post_parse(padded)
    assert res.status_code == 200
    assert len(res.json()["hands"]) == 1
