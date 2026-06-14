"""Per-user fixed-window rate limiter (E1) — in-memory, single process.

Two windows (per-minute, per-day). The container is a single process, so an
in-memory dict is correct; multi-instance scaling would need shared counters
and is explicitly deferred (YAGNI). Counters reset on restart — acceptable
at this scale.

Disabled (no-op) outside PUBLIC_DEPLOY so local dev is never throttled.
"""

from __future__ import annotations

import time

from fastapi import Depends, HTTPException

from gto.api import config
from gto.api.auth import require_user

# user_id -> {window_key: (window_start, count)}
_counters: dict[str, dict[str, tuple[float, int]]] = {}

_WINDOWS = {"minute": 60.0, "day": 86400.0}

# Bound memory: sweep fully-expired users at most this often (seconds).
_PRUNE_EVERY = 60.0
_last_prune = 0.0


def _prune(now: float) -> None:
    """Drop users whose every window has fully expired so _counters cannot grow
    without bound on a public deploy with many distinct authenticated users."""
    dead = [
        user
        for user, wins in _counters.items()
        if all(now - start >= _WINDOWS.get(name, 0.0) for name, (start, _c) in wins.items())
    ]
    for user in dead:
        del _counters[user]


def _check_window(user: str, name: str, span: float, limit: int) -> None:
    now = time.monotonic()
    user_counters = _counters.setdefault(user, {})
    start, count = user_counters.get(name, (now, 0))
    if now - start >= span:
        start, count = now, 0
    if count >= limit:
        retry = int(span - (now - start)) + 1
        raise HTTPException(
            429,
            detail=f"rate limit: {limit}/{name} exceeded",
            headers={"Retry-After": str(retry)},
        )
    user_counters[name] = (start, count + 1)


def check(user: str) -> None:
    if not config.settings.public_deploy:
        return
    global _last_prune
    now = time.monotonic()
    if now - _last_prune >= _PRUNE_EVERY:
        _last_prune = now
        _prune(now)
    _check_window(user, "minute", _WINDOWS["minute"], config.settings.rate_per_min)
    _check_window(user, "day", _WINDOWS["day"], config.settings.rate_per_day)


def reset() -> None:
    """Test hook: clear all counters."""
    global _last_prune
    _counters.clear()
    _last_prune = 0.0


async def rate_limited_user(user: str = Depends(require_user)) -> str:
    """FastAPI dependency: auth + rate limit in one (the E1 gate)."""
    check(user)
    return user
