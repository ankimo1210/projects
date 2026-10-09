"""Reserved conditions, split geometry and reviewed source freeze for short DML.

The seed ledger reserves logical streams; it is not evidence that draws ran.
Main geometry is generated only after the actual pilot is numerically checked.
Hashes bind immutable provenance. Financial comparisons use tolerances in the
pilot and study checkers, not these identities.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from hullkit.zero_dte import TradingSession, variance_clock_fraction

ROOT = Path(__file__).resolve().parents[4]
DIRECTORY = Path(__file__).resolve().parent
SPLITS = {"train": 512, "validation": 128, "test": 336}
SOURCES = (
    "johnhull/hullkit/src/hullkit/_short_maturity_teachers.py",
    "deep_hedge_price/src/deep_hedge_price/_short_maturity_dml.py",
    "johnhull/research/RB-F05/short_maturity/reference_methods.py",
    "johnhull/research/RB-F05/short_maturity/protocol.py",
    "johnhull/research/RB-F05/short_maturity/pilot.py",
    "johnhull/research/RB-F05/short_maturity/build_reference.py",
    "johnhull/research/RB-F05/short_maturity/analytics.py",
    "johnhull/hullkit/src/hullkit/zero_dte.py",
    "johnhull/hullkit/src/hullkit/alternative_models.py",
    "johnhull/hullkit/src/hullkit/bsm.py",
)


def json_digest(value):
    """Canonical record identity solely for provenance binding."""
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def arrays_digest(arrays):
    """Bind non-object numeric arrays, including dtype, shape and names."""
    digest = hashlib.sha256()
    for name in sorted(arrays):
        a = np.asarray(arrays[name])
        if a.dtype.hasobject:
            raise ValueError("object arrays cannot bind pilot evidence")
        digest.update(json.dumps([name, a.dtype.str, list(a.shape)]).encode())
        digest.update(np.ascontiguousarray(a).tobytes())
    return digest.hexdigest()


def source_registry(*, require_complete=True):
    """Return portable identities and reject an incomplete financial registry."""
    missing = [name for name in SOURCES if not (ROOT / name).is_file()]
    if missing and require_complete:
        raise ValueError(f"complete financial source registry required: {missing}")
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in SOURCES
        if (ROOT / name).is_file()
    }


def _pilot_cases():
    rows = []
    for minutes in [1, 5, 30, 58.5, 331.5, 390]:
        for event in [0, 1]:
            for coordinate, distance in [
                *(("scaled", x) for x in [-4.0, -2.0, 0.0, 2.0, 4.0]),
                ("fixed", -0.05),
                ("fixed", 0.05),
            ]:
                rows.append(
                    {
                        "id": f"p{len(rows):03d}",
                        "minutes": minutes,
                        "event": event,
                        "coordinate": coordinate,
                        "distance": distance,
                    }
                )
    return rows


def build_seed_ledger(p):
    """Reserve disjoint scenario, count, mark, fit and fresh physical streams."""
    ids = []
    for phase in ["pilot", "main"]:
        for split, n in SPLITS.items():
            ids.append(f"{phase}/scenario/{split}")
            if split != "test":
                for i in range(n):
                    for kind in ["count", "jump"]:
                        ids.append(f"{phase}/teacher/{split}/{i}/{kind}")
    for c in p["pilot"]["cases"]:
        for rep in range(p["pilot"]["streams"]):
            for kind in ["count", "jump"]:
                ids.append(f"pilot/selection/{c['id']}/{rep}/{kind}")
            for kind in ["count", "jump", "brown"]:
                ids.append(f"pilot/raw/{c['id']}/{rep}/{kind}")
    ids.extend(["pilot/init/0", "pilot/batch/0"])
    ids.extend(f"main/batch/{seed}" for seed in p["fit"]["paired_seeds"])
    for i in range(12):
        ids.extend(f"fresh/raw/{i}/{kind}" for kind in ["count", "jump", "brown"])
    rows = [
        {
            "id": name,
            "seed": int(
                np.random.SeedSequence(p["master_seed"], spawn_key=(i,)).generate_state(
                    1, dtype=np.uint64
                )[0]
            ),
        }
        for i, name in enumerate(sorted(ids))
    ]
    rows += [{"id": f"main/init/{seed}", "seed": seed} for seed in p["fit"]["paired_seeds"]]
    return sorted(rows, key=lambda row: row["id"])


def candidate_protocol():
    """Return a fresh candidate, never a saved protocol of unknown lifecycle."""
    p = {
        "schema": "RB-F05-short-protocol-v1",
        "state": "candidate",
        "master_seed": 2026100905,
        "contract": {
            "strike": 100.0,
            "expiry": "2026-10-08T16:00:00-04:00",
            "timezone": "America/New_York",
            "session_open": "09:30",
            "session_close": "16:00",
            "rate": 0.03,
            "dividend": 0.0,
            "jump_mean": -0.05,
            "jump_std": 0.10,
            "pulse_minutes": 30.0,
            "pulse_variance": 0.00035,
            "pulse_full_mean_count": 0.028,
            "synthetic": True,
        },
        "clock": {
            "volatility": 0.20,
            "annual_sessions": 252,
            "carry_days": 365,
            "weights": [2.0, 0.5, 2.0],
            "edges": [0.0, 0.15, 0.85, 1.0],
        },
        "splits": dict(SPLITS),
        "remaining_minutes": [1, 5, 15, 30, 60, 120, 240, 390],
        "test_scaled_distance": list(np.linspace(-4, 4, 17)),
        "test_fixed_distance": [-0.05, -0.025, 0.025, 0.05],
        "geometry": {"atm_probability": 0.70, "fixed_distance_bounds": [-0.05, 0.05]},
        "normal_draw_policy": "active_only",
        "teacher_sample_count": None,
        "reference_nmax": 8,
        "pilot": {
            "cases": _pilot_cases(),
            "streams": 3,
            "sample_candidates": [16384, 65536, 262144, 1048576],
            "raw_sample_count": 65536,
            "minimum_active_count": 100,
            "max_price_se": 0.002,
            "max_delta_se": 0.0005,
            "max_scaled_gamma_se_fraction": 0.01,
            "se_multiple": 6.0,
            "absolute_reference_tolerance": [1e-7, 1e-9, 1e-9],
            "relative_reference_tolerance": [1e-10, 1e-10, 1e-9],
            "quadrature_budget_fraction": 0.25,
            "crn_scaled_bumps": [0.02, 0.05, 0.10],
        },
        "fit": {
            "paired_seeds": [11, 29, 47],
            "max_updates": 512,
            "batch_size": 128,
            "learning_rate": 0.003,
            "budget_s": 120.0,
            "widths": [3, 32, 32, 1],
            "gamma_loss": False,
            "output": "unconstrained_total_price_train_only_shift_scale",
        },
        "hermite": {
            "spot_nodes": 65,
            "time_nodes": 33,
            "include_minutes": [30.0, 58.5, 331.5],
            "degree": 5,
            "spot_continuity": 2,
            "time_blend": "linear",
        },
        "accuracy": {
            "price_abs": 0.01,
            "delta_abs": 0.005,
            "scaled_gamma_abs": 0.05,
            "scaled_gamma_relative": 0.05,
        },
        "timing": {
            "batches": [1, 32],
            "warmup": 1,
            "repetitions": 7,
            "threads": 1,
            "scope": "whole price/Greek/route call",
        },
        "runtime_versions": {
            name: importlib.metadata.version(name) for name in ["numpy", "scipy", "torch"]
        },
    }
    p["seed_ledger"] = build_seed_ledger(p)
    return p


def seed_for(p, key):
    """Look up one reserved stream without drawing or inventing a fallback seed."""
    matches = [r["seed"] for r in p["seed_ledger"] if r["id"] == key]
    if len(matches) != 1:
        raise ValueError(f"unique reserved seed required: {key}")
    return matches[0]


def validate_protocol(p, *, require_frozen=False):
    """Check original rosters and frozen evidence/source/condition identities."""
    if p.get("schema") != "RB-F05-short-protocol-v1":
        raise ValueError("unknown short protocol")
    if p.get("splits") != SPLITS or len(p["pilot"]["cases"]) != 84:
        raise ValueError("original scenario roster changed")
    rows = p["seed_ledger"]
    if (
        len({r["id"] for r in rows}) != len(rows)
        or len({r["seed"] for r in rows}) != len(rows)
        or rows != build_seed_ledger(p)
    ):
        raise ValueError("reserved seed roster changed or duplicate")
    if p["normal_draw_policy"] != "active_only":
        raise ValueError("normal draw policy changed")
    if require_frozen:
        f = p.get("frozen")
        content = {k: v for k, v in p.items() if k != "frozen"}
        if p.get("state") != "frozen" or not f or f["digest"] != json_digest(content):
            raise ValueError("reviewed frozen numeric contract required")
        if f["source_registry"] != source_registry():
            raise ValueError("frozen financial source changed")
        n = p["teacher_sample_count"]
        if (
            n not in p["pilot"]["sample_candidates"]
            or n != f["pilot_validation"]["selected_sample_count"]
        ):
            raise ValueError("frozen allocation disagrees with verified pilot")
        candidate = copy.deepcopy(content)
        candidate["state"] = "candidate"
        candidate["teacher_sample_count"] = None
        _validate_review(candidate, f["pilot_review"], f["pilot_binding"])
    elif p["state"] == "candidate" and p["teacher_sample_count"] is not None:
        raise ValueError("candidate allocation must await full pilot")
    return p


def _variance(p, seconds):
    expiry = datetime.fromisoformat(p["contract"]["expiry"]).astimezone(
        ZoneInfo(p["contract"]["timezone"])
    )
    start = expiry - timedelta(seconds=float(seconds))
    fraction = variance_clock_fraction(
        start, TradingSession(), weights=tuple(p["clock"]["weights"])
    )
    return p["clock"]["volatility"] ** 2 / p["clock"]["annual_sessions"] * (1 - fraction)


def scenario_inputs(p, split, *, phase):
    """Generate fixed split geometry only after the corresponding lifecycle gate."""
    if phase not in ["pilot", "main"] or split not in SPLITS:
        raise ValueError("known phase/split required")
    if phase == "main":
        validate_protocol(p, require_frozen=True)
        verify_frozen_evidence(p)
    else:
        validate_protocol(p)
    k = p["contract"]["strike"]
    if split == "test":
        rows = []
        for minutes in p["remaining_minutes"]:
            variance = _variance(p, minutes * 60)
            for event in [0, 1]:
                for x in [
                    *(d * np.sqrt(variance) for d in p["test_scaled_distance"]),
                    *p["test_fixed_distance"],
                ]:
                    rows.append([k * np.exp(x), minutes * 60, event])
        return np.asarray(rows)
    rng = np.random.default_rng(seed_for(p, f"{phase}/scenario/{split}"))
    n = SPLITS[split]
    seconds = np.exp(rng.uniform(np.log(60), np.log(390 * 60), n))
    near = rng.random(n) < p["geometry"]["atm_probability"]
    scaled_distance = rng.uniform(-4, 4, n)
    fixed_distance = rng.uniform(*p["geometry"]["fixed_distance_bounds"], n)
    root_w = np.sqrt(np.array([_variance(p, sec) for sec in seconds]))
    x = np.where(near, scaled_distance * root_w, fixed_distance)
    events = np.tile([0, 1], n // 2)
    return np.column_stack([k * np.exp(x), seconds, events])


def _module(name):
    spec = importlib.util.spec_from_file_location(
        f"short_protocol_{name}", DIRECTORY / f"{name}.py"
    )
    result = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = result
    spec.loader.exec_module(result)
    return result


def pilot_bindings(candidate, record, arrays):
    """Identify candidate, actual raw pilot and complete financial sources."""
    return {
        "protocol_digest": json_digest(candidate),
        "pilot_record_digest": json_digest(record),
        "pilot_arrays_digest": arrays_digest(arrays),
        "source_registry": source_registry(),
    }


def _validate_review(candidate, review, bindings):
    if (
        review.get("schema") != "RB-F05-short-pilot-review-v1"
        or review.get("decision") != "approved"
        or review.get("approved") is not True
        or review.get("critical_findings")
        or review.get("important_findings")
    ):
        raise ValueError("typed independently approved pilot review required")
    required = {"protocol_digest", "pilot_record_digest", "pilot_arrays_digest", "source_registry"}
    if set(bindings) != required or bindings["protocol_digest"] != json_digest(candidate):
        raise ValueError("complete candidate/pilot review binding required")
    if any(review.get(k) != bindings[k] for k in required):
        raise ValueError("review evidence binding changed")
    if bindings["source_registry"] != source_registry():
        raise ValueError("review financial source changed")


def _validate_pilot(candidate, record, arrays, review):
    if (
        record.get("schema") != "RB-F05-short-pilot-v1"
        or record.get("phase") != "pilot"
        or record.get("complete") is not True
        or record.get("smoke") is not False
        or record.get("protocol") != candidate
        or record.get("protocol_digest") != json_digest(candidate)
        or record.get("source_registry") != source_registry()
    ):
        raise ValueError("full saved candidate pilot evidence required")
    checked = _module("pilot").check_record(record, arrays)
    if not checked.get("passed") or checked.get("selected_sample_count") is None:
        raise ValueError("full numeric pilot not ready; cannot freeze")
    bindings = pilot_bindings(candidate, record, arrays)
    _validate_review(candidate, review, bindings)
    return bindings, checked


def freeze_protocol(candidate, review, *, pilot_record, pilot_arrays):
    """Freeze only a complete numerically ready pilot and its explicit approval."""
    registry = source_registry()
    validate_protocol(candidate)
    if (
        candidate["state"] != "candidate"
        or candidate.get("fixture")
        or review.get("decision") != "approved"
        or review.get("approved") is not True
    ):
        raise ValueError("candidate and approved independent review required")
    bindings, checked = _validate_pilot(candidate, pilot_record, pilot_arrays, review)
    result = copy.deepcopy(candidate)
    result["state"] = "frozen"
    result["teacher_sample_count"] = checked["selected_sample_count"]
    result["frozen"] = {
        "digest": json_digest(result),
        "source_registry": registry,
        "pilot_binding": bindings,
        "pilot_validation": checked,
        "pilot_review": copy.deepcopy(review),
    }
    return validate_protocol(result, require_frozen=True)


def verify_frozen_evidence(p):
    """Load and numerically recheck the actual saved pilot before main draws."""
    validate_protocol(p, require_frozen=True)
    candidate = copy.deepcopy(p)
    f = candidate.pop("frozen")
    candidate["state"] = "candidate"
    candidate["teacher_sample_count"] = None
    record, arrays = _module("pilot").load_result(DIRECTORY / "pilot")
    bindings, checked = _validate_pilot(candidate, record, arrays, f["pilot_review"])
    if bindings != f["pilot_binding"] or checked != f["pilot_validation"]:
        raise ValueError("saved pilot no longer matches frozen approval")
    return checked


def load_protocol(path=None, *, require_frozen=False):
    """Load explicit saved conditions; fixture code should use candidate_protocol."""
    path = Path(path) if path is not None else DIRECTORY / "protocol.json"
    p = validate_protocol(json.loads(path.read_text()), require_frozen=require_frozen)
    if require_frozen:
        verify_frozen_evidence(p)
    return p
