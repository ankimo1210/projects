"""API-equivalent cost of local Claude Code transcripts in a time window.

Usage: python3 api_cost.py START_UTC [END_UTC]   (ISO 8601, e.g. 2026-10-17T02:10:00Z)

Prices are USD per million tokens from
https://platform.claude.com/docs/en/about-claude/pricing (checked 2026-10-17):
(base input, 5m cache write, 1h cache write, cache read, output).
"""

import datetime as dt
import glob
import json
import os
import sys
from decimal import Decimal

PRICES = {
    "claude-fable-5-1": (10, 12.5, 20, 0.25, 50),
    "claude-fable-5": (10, 12.5, 20, 1, 50),
    "claude-opus-5-5": (4, 5, 8, 0.20, 20),
    "claude-opus-5": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-8": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-7": (5, 6.25, 10, 0.50, 25),
    "claude-opus-4-6": (5, 6.25, 10, 0.50, 25),
    "claude-sonnet-5-5": (2, 2.5, 4, 0.10, 10),
    "claude-sonnet-5": (2, 2.5, 4, 0.20, 10),
    "claude-sonnet-4-6": (3, 3.75, 6, 0.30, 15),
    "claude-haiku-4-5": (1, 1.25, 2, 0.10, 5),
}
# Haiku 5.5 is priced by prompt length: up to / over 100k prompt tokens.
HAIKU_5_5 = ((0.10, 0.125, 0.20, 0.01, 0.50), (0.50, 0.625, 1, 0.05, 2.50))

TRANSCRIPTS = os.path.expanduser("~/.claude/projects/**/*.jsonl")


def ts(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def rows(start, end):
    """Yield (time, model, usage, session_id) for each API response in [start, end)."""
    seen = set()
    for path in glob.glob(TRANSCRIPTS, recursive=True):
        if os.path.getmtime(path) < start.timestamp():
            continue
        with open(path, errors="ignore") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                m = r.get("message")
                if r.get("type") != "assistant" or not isinstance(m, dict) or "usage" not in m:
                    continue
                if not r.get("timestamp") or not (start <= ts(r["timestamp"]) < end):
                    continue
                # One API response is written as several lines (one per content block).
                key = (m.get("id"), r.get("requestId"))
                if key in seen:
                    continue
                seen.add(key)
                yield ts(r["timestamp"]), m.get("model"), m["usage"], r.get("sessionId")


def cost(model, u):
    """API list-price cost in USD of one response's usage, or None if the model is unpriced."""
    i = u.get("input_tokens", 0)
    o = u.get("output_tokens", 0)
    cr = u.get("cache_read_input_tokens", 0)
    cc = u.get("cache_creation") or {}
    w1h = cc.get("ephemeral_1h_input_tokens", 0)
    w5m = cc.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - w1h)
    if model == "claude-haiku-5-5":
        p = HAIKU_5_5[i + cr + w5m + w1h > 100_000]
    elif model in PRICES:
        p = PRICES[model]
    else:
        return None
    mult = Decimal("1.1") if u.get("inference_geo") == "us" else Decimal(1)
    if u.get("speed") == "fast":
        mult *= 2
    tokens = (i, w5m, w1h, cr, o)
    return (
        sum(Decimal(str(n)) * Decimal(str(r)) for n, r in zip(tokens, p, strict=True))
        / 1_000_000
        * mult
    )


def main():
    start = ts(sys.argv[1])
    end = ts(sys.argv[2]) if len(sys.argv) > 2 else dt.datetime.now(dt.UTC)
    total, n, sessions, by_model, unpriced = Decimal(0), 0, set(), {}, {}
    for _, model, u, sid in rows(start, end):
        c = cost(model, u)
        if c is None:
            unpriced[model] = unpriced.get(model, 0) + 1
            continue
        total += c
        n += 1
        sessions.add(sid)
        by_model[model] = by_model.get(model, Decimal(0)) + c
    print(
        json.dumps(
            {
                "start": str(start),
                "end": str(end),
                "responses": n,
                "sessions": len(sessions),
                "usd": float(round(total, 4)),
                "by_model": {k: float(round(v, 4)) for k, v in by_model.items()},
                "unpriced": unpriced,
            }
        )
    )


if __name__ == "__main__":
    main()
