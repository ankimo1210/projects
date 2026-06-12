"""Supabase JWT verification (E1) — stdlib HS256, no new dependencies.

Supabase signs access tokens with the project's JWT secret (HS256). We verify
signature + `exp` + `aud == "authenticated"` and return the `sub` claim as
the user id. The id NEVER comes from anything client-supplied other than the
verified token.

In local dev (PUBLIC_DEPLOY unset) auth is a no-op returning "local-dev" so
every gated route keeps working without a Supabase project.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Header, HTTPException

from gto.api import config

EXPECTED_AUD = "authenticated"


def _b64url_decode(seg: str) -> bytes:
    pad = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + pad)


def verify_jwt(token: str, secret: str) -> dict:
    """Validate an HS256 JWT; return its claims. Raises ValueError on any
    failure (malformed / bad signature / expired / wrong audience)."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("malformed token")
    header_b64, payload_b64, sig_b64 = parts
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
        sig = _b64url_decode(sig_b64)
    except Exception as e:
        raise ValueError("undecodable token") from e
    if header.get("alg") != "HS256":
        raise ValueError(f"unsupported alg {header.get('alg')!r}")
    expected = hmac.new(
        secret.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256
    ).digest()
    if not hmac.compare_digest(sig, expected):
        raise ValueError("bad signature")
    exp = payload.get("exp")
    if exp is None or time.time() >= float(exp):
        raise ValueError("token expired")
    aud = payload.get("aud")
    if aud != EXPECTED_AUD and (not isinstance(aud, list) or EXPECTED_AUD not in aud):
        raise ValueError(f"wrong audience {aud!r}")
    if not payload.get("sub"):
        raise ValueError("no sub claim")
    return payload


async def require_user(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: verified Supabase user id, or 401.

    No-op in local dev (PUBLIC_DEPLOY unset) so the gated routes stay usable
    without a Supabase project.
    """
    if not config.settings.public_deploy:
        return "local-dev"
    if not config.settings.supabase_jwt_secret:
        raise HTTPException(500, "server misconfigured: SUPABASE_JWT_SECRET unset")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "login required")
    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = verify_jwt(token, config.settings.supabase_jwt_secret)
    except ValueError as e:
        raise HTTPException(401, f"invalid token: {e}") from e
    return str(claims["sub"])


async def require_local() -> None:
    """FastAPI dependency: 503 on public deploys (GPU / heavy-RAM routes)."""
    if config.settings.public_deploy:
        raise HTTPException(503, "this feature runs on the local GPU build only")
