"""E1: JWT verification, rate limiting, and public-deploy gating."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi.testclient import TestClient
from gto.api import config, ratelimit
from gto.api.auth import verify_jwt
from gto.api.main import app

client = TestClient(app)

SECRET = "test-secret"


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def make_jwt(
    sub: str = "user-1",
    secret: str = SECRET,
    exp_offset: float = 3600,
    aud: str = "authenticated",
    alg: str = "HS256",
) -> str:
    header = _b64url(json.dumps({"alg": alg, "typ": "JWT"}).encode())
    payload = _b64url(
        json.dumps({"sub": sub, "aud": aud, "exp": time.time() + exp_offset}).encode()
    )
    sig = _b64url(
        hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    )
    return f"{header}.{payload}.{sig}"


@pytest.fixture
def public_deploy(monkeypatch):
    """Flip the app into the public posture for one test."""
    monkeypatch.setenv("PUBLIC_DEPLOY", "1")
    monkeypatch.setenv("SUPABASE_JWT_SECRET", SECRET)
    monkeypatch.setenv("RATE_PER_MIN", "3")
    monkeypatch.setenv("RATE_PER_DAY", "5")
    config.reload_settings()
    ratelimit.reset()
    yield
    monkeypatch.delenv("PUBLIC_DEPLOY")
    config.reload_settings()
    ratelimit.reset()


# ----- verify_jwt unit -------------------------------------------------------


def test_valid_jwt_returns_claims():
    claims = verify_jwt(make_jwt(sub="abc"), SECRET)
    assert claims["sub"] == "abc"


@pytest.mark.parametrize(
    "token",
    [
        "garbage",
        make_jwt(secret="wrong-secret"),
        make_jwt(exp_offset=-10),
        make_jwt(aud="anon"),
        make_jwt(alg="none"),
    ],
)
def test_bad_jwts_rejected(token):
    with pytest.raises(ValueError):
        verify_jwt(token, SECRET)


def test_tampered_payload_rejected():
    h, _p, s = make_jwt(sub="user-1").split(".")
    evil = _b64url(
        json.dumps({"sub": "admin", "aud": "authenticated", "exp": time.time() + 3600}).encode()
    )
    with pytest.raises(ValueError):
        verify_jwt(f"{h}.{evil}.{s}", SECRET)


# ----- gating ---------------------------------------------------------------


def test_local_dev_has_no_gates():
    # PUBLIC_DEPLOY unset: gated routes work with no token.
    r = client.get("/api/equity", params={"hero": "Ah As", "villain": "Kd Kc", "iterations": 1000})
    assert r.status_code == 200


def test_public_deploy_requires_token(public_deploy):
    r = client.get("/api/equity", params={"hero": "Ah As", "villain": "Kd Kc", "iterations": 1000})
    assert r.status_code == 401
    r = client.get(
        "/api/equity",
        params={"hero": "Ah As", "villain": "Kd Kc", "iterations": 1000},
        headers={"Authorization": f"Bearer {make_jwt()}"},
    )
    assert r.status_code == 200


def test_public_routes_need_no_token(public_deploy):
    assert client.get("/api/health").status_code == 200
    # library + trainer are the anonymous acquisition funnel
    assert client.get("/api/trainer/quiz").status_code in (200, 404)


def test_rate_limit_429_with_retry_after(public_deploy):
    headers = {"Authorization": f"Bearer {make_jwt(sub='limited')}"}
    params = {"hero": "Ah As", "villain": "Kd Kc", "iterations": 1000}
    for _ in range(3):  # RATE_PER_MIN=3
        assert client.get("/api/equity", params=params, headers=headers).status_code == 200
    r = client.get("/api/equity", params=params, headers=headers)
    assert r.status_code == 429
    assert "retry-after" in {k.lower() for k in r.headers}
    # another user is unaffected (per-user isolation)
    other = {"Authorization": f"Bearer {make_jwt(sub='other')}"}
    assert client.get("/api/equity", params=params, headers=other).status_code == 200


def test_validate_settings_rejects_half_configured_public_deploy(monkeypatch):
    # PUBLIC_DEPLOY set but no JWT secret -> fail fast at boot, not fail-open.
    monkeypatch.setenv("PUBLIC_DEPLOY", "1")
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com")
    with pytest.raises(RuntimeError):
        config.validate_settings(config.Settings())


def test_validate_settings_ok_for_local_dev(monkeypatch):
    monkeypatch.delenv("PUBLIC_DEPLOY", raising=False)
    config.validate_settings(config.Settings())  # no raise


def test_ratelimit_prunes_fully_expired_users():
    ratelimit.reset()
    # start times in monotonic seconds; "stale" is far in the past, "fresh" future.
    ratelimit._counters["stale"] = {"minute": (0.0, 1), "day": (0.0, 1)}
    ratelimit._counters["fresh"] = {"minute": (1e18, 1), "day": (1e18, 1)}
    ratelimit._prune(now=1e9)
    assert "stale" not in ratelimit._counters
    assert "fresh" in ratelimit._counters
    ratelimit.reset()


def test_flop_async_tier_503_in_public_deploy(public_deploy):
    spec = {
        "stack_bb": 41.0,
        "config": {"pot_bb": 18.0, "board": ["Ah", "Kd", "7s"], "pot_type": "3bet"},
    }
    r = client.post(
        "/api/solve", json=spec, headers={"Authorization": f"Bearer {make_jwt()}"}
    )
    assert r.status_code == 503
    assert client.get("/api/solve/jobs/x", headers={"Authorization": f"Bearer {make_jwt()}"}).status_code == 503


def test_solver_flop_preview_503_in_public_deploy(public_deploy):
    r = client.post(
        "/api/solver/solve",
        json={"pot_bb": 6.5, "effective_stack_bb": 97.0, "board": ["Ah", "Kd", "7s"]},
        headers={"Authorization": f"Bearer {make_jwt()}"},
    )
    assert r.status_code == 503
