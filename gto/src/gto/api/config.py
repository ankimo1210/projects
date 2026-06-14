"""Env-driven deployment settings (E1).

Everything defaults to the local-dev posture: no auth, no rate limits, CORS
open, GPU routes enabled. Setting PUBLIC_DEPLOY=1 flips the public posture:
gated routes require a Supabase JWT, heavy/GPU routes 503, CORS locks to
ALLOWED_ORIGINS. Nothing secret is committed — secrets arrive via env.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> list[str]:
    v = os.environ.get(name, "")
    return [s.strip() for s in v.split(",") if s.strip()]


@dataclass
class Settings:
    public_deploy: bool = field(default_factory=lambda: _env_bool("PUBLIC_DEPLOY"))
    supabase_jwt_secret: str = field(
        default_factory=lambda: os.environ.get("SUPABASE_JWT_SECRET", "")
    )
    allowed_origins: list[str] = field(default_factory=lambda: _env_list("ALLOWED_ORIGINS"))
    rate_per_min: int = field(default_factory=lambda: int(os.environ.get("RATE_PER_MIN", "30")))
    rate_per_day: int = field(default_factory=lambda: int(os.environ.get("RATE_PER_DAY", "500")))


# Module-level singleton, re-readable in tests via reload_settings().
settings = Settings()


def reload_settings() -> Settings:
    """Re-read env (tests flip PUBLIC_DEPLOY / secrets at runtime)."""
    global settings
    settings = Settings()
    return settings


def validate_settings(s: Settings | None = None) -> None:
    """Fail fast on an inconsistent public-deploy posture.

    The whole security posture (auth, rate limits, CORS lock, GPU-route 503) is
    gated on PUBLIC_DEPLOY. A deploy that sets PUBLIC_DEPLOY but forgets the JWT
    secret or the origin allow-list would otherwise fail OPEN at request time
    (auth returns 500 per call, CORS stays "*"); crash at boot instead so a
    half-configured public deploy never serves traffic.
    """
    s = s if s is not None else settings
    if not s.public_deploy:
        return
    missing = []
    if not s.supabase_jwt_secret:
        missing.append("SUPABASE_JWT_SECRET")
    if not s.allowed_origins:
        missing.append("ALLOWED_ORIGINS")
    if missing:
        raise RuntimeError(
            "PUBLIC_DEPLOY is set but required settings are missing: " + ", ".join(missing)
        )
