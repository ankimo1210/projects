"""Protocol, common-noise slots and immutable source binding for RB-F06."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
SOURCES = (
    "hullkit/src/hullkit/sabr.py",
    "hullkit/src/hullkit/_sabr_identifiability.py",
    "research/RB-F06/protocol.py",
    "research/RB-F06/reference_methods.py",
    "research/RB-F06/build_reference.py",
    "research/RB-F06/analytics.py",
)


def json_digest(value):
    """Canonical JSON identity; not a floating-point numerical acceptance test."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def source_registry():
    """Portable project-relative financial implementation identities."""
    return {
        name: hashlib.sha256((PROJECT / name).read_bytes()).hexdigest()
        for name in SOURCES
        if (PROJECT / name).exists()
    }


def noise_for(protocol, phase, truth, rep):
    """Draw one reserved seven-quote master noise vector, shared by nested groups."""
    row = next(
        r
        for r in protocol["seed_ledger"]
        if (r["phase"], r["truth"], r["rep"]) == (phase, truth, rep)
    )
    return np.random.default_rng(row["seed"]).normal(
        0.0, protocol["noise_scale"], len(protocol["log_moneyness"])
    )


def validate_protocol(protocol, require_frozen=False):
    """Check original roster and, when frozen, complete contract/source binding."""
    if protocol["schema"] != "RB-F06-protocol-v1":
        raise ValueError("unknown protocol")
    seeds = [r["seed"] for r in protocol["seed_ledger"]]
    if len(seeds) != len(set(seeds)):
        raise ValueError("reserved seed collision")
    if protocol["noise_scale"] <= 0 or protocol["solver_call_cap"] != sum(
        protocol["solver_call_roster"].values()
    ):
        raise ValueError("invalid scale or cost roster")
    if require_frozen:
        frozen = protocol.get("frozen")
        content = {key: value for key, value in protocol.items() if key != "frozen"}
        if not frozen or frozen["digest"] != json_digest(content):
            raise ValueError("frozen numeric contract changed")
        registry = source_registry()
        if set(registry) != set(SOURCES) or set(frozen["source_registry"]) != set(SOURCES):
            raise ValueError("complete frozen financial source registry required")
        if frozen["source_registry"] != registry:
            raise ValueError("frozen financial source changed")
    return protocol


def load_protocol(path=None, require_frozen=False):
    """Load candidate or reviewed frozen conditions without drawing any noise."""
    path = Path(path) if path is not None else Path(__file__).with_name("protocol.json")
    return validate_protocol(json.loads(path.read_text()), require_frozen=require_frozen)


def freeze_protocol(protocol, review):
    """Bind an approved pilot to the exact roster and available financial sources."""
    if review.get("decision") != "approved":
        raise ValueError("approved independent pilot review required")
    registry = source_registry()
    if set(registry) != set(SOURCES):
        raise ValueError("complete financial source registry required")
    result = copy.deepcopy(protocol)
    result.pop("frozen", None)
    result["state"] = "frozen"
    result["frozen"] = {
        "digest": json_digest(result),
        "source_registry": registry,
        "pilot_review": review,
    }
    return result
