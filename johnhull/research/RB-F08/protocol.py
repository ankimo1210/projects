"""Fixed F08 research conditions, collision-audited seeds and pilot freeze.

Seed hashes bind provenance and integer metadata. They do not establish any
pricing claim: freeze also requires the independent pilot evidence validator.
Large ledgers live in typed NPZ columns, never pickled objects or tracked JSON.
"""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import platform
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
SCHEMA = "RB-F08-mlmc-rqmc-v1"
PHASES = ("pilot", "main", "coverage", "fresh_review", "timing", "method_order", "bootstrap")
METHODS = ("mlmc", "plain_euler", "exact_plain", "exact_cv")
SOURCE_FILES = (
    "hullkit/src/hullkit/_multilevel_mc.py",
    "hullkit/src/hullkit/_rqmc_ci.py",
    "hullkit/src/hullkit/_numerical_mc.py",
    "hullkit/src/hullkit/_stochastic_foundations.py",
    "hullkit/src/hullkit/bsm.py",
    "research/RB-F08/reference_methods.py",
    "research/RB-F08/protocol.py",
    "research/RB-F08/pilot.py",
    "research/RB-F08/analytics.py",
    "research/RB-F08/build_reference.py",
)
_OPTIONAL_INTS = ("case", "budget", "run", "method_ordinal", "level", "scramble")
_RAGGED = ("entropy", "logical_spawn_key", "spawn_key", "candidate_seeds")
_COST = {
    "level_zero": {"updates": "M0*N", "normals": "M0*N", "payoffs": "N", "coarse_aggregation": "0"},
    "level_positive": {
        "updates": "(M_l+M_l/2)*N",
        "normals": "M_l*N",
        "payoffs": "2*N",
        "coarse_aggregation": "M_l/2*N",
    },
    "wall_scope": "RNG+path+payoff+summary; import setup separate",
    "expense_rule": "sum unique expense_id once; method cold includes required shared expenses",
    "euler_pilot_rule": "all candidate levels, not selected prefix only",
    "exact_pilot_rule": "own necessary pilot/CV cost, no mandatory Euler-only pilot",
}


def json_digest(value: dict) -> str:
    """Hash canonical JSON provenance, rejecting unsupported/nonfinite metadata."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def arrays_digest(arrays: dict[str, np.ndarray]) -> str:
    """Bind typed saved columns for provenance; not a numerical accuracy check."""
    digest = hashlib.sha256()
    for name in sorted(arrays):
        array = np.asarray(arrays[name])
        if array.dtype.kind == "O":
            raise ValueError("object arrays are not permitted in saved evidence")
        header = json.dumps([name, array.dtype.str, list(array.shape)], separators=(",", ":"))
        digest.update(header.encode())
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def candidate_protocol() -> dict:
    """Return all pre-observation candidate conditions without generating seeds."""
    lower, upper = np.nextafter(0.0, 1.0), np.nextafter(1.0, 0.0)
    return {
        "schema": SCHEMA,
        "revision": 1,
        "state": "candidate",
        "parameters": {
            "spot": 100.0,
            "strike": 100.0,
            "rate": 0.03,
            "sigma": 0.2,
            "maturity": 1.0,
            "yield_rate": 0.0,
        },
        "product": {"kind": "european_call", "payment": "expiry", "units": "currency/year"},
        "scheme": "ordinary_euler",
        "base_steps": 4,
        "epsilon": [0.4, 0.2, 0.1],
        "pilot": {
            "levels": list(range(9)),
            "streams": 3,
            "paths_per_stream": 16384,
            "exact_cv_paths_per_stream": 16384,
            "bias_confidence": 0.99,
            "minimum_main_level": 2,
            "alpha_signal_multiplier": 3.0,
            "alpha_consecutive_levels": 3,
            "negative_path_rate_cap": 1e-5,
        },
        "allocation": {
            "minimum_paths": 32,
            "variance_floor": 1e-12,
            "sampling_variance_fraction": 0.5,
            "bias_fraction_sqrt": 0.5,
            "cost_basis": "isolated_median_seconds_per_pair",
            "rounding": "ceil",
        },
        "caps": {"paths_per_run": 2000000, "steps_per_run": 100000000},
        "main": {
            "outer_runs": 256,
            "methods": list(METHODS),
            "confidence": 0.95,
            "levels_reserved": list(range(9)),
            "mlmc_df": "Satterthwaite",
            "failed_path_rule": "retain negative; nonfinite fails original run",
            "cv_control": "exp(-rT)*ST",
            "cv_expectation": "S0*exp(-qT)",
            "cv_beta": "independent pilot only",
            "selected_allocations": None,
        },
        "rqmc": {
            "strikes": [80.0, 100.0, 120.0],
            "powers": [8, 10],
            "scrambles": [8, 16, 32],
            "outer_runs": 512,
            "confidence": 0.95,
            "dimensions": 1,
            "scheme": "exact_terminal",
            "interval": "approximate Student",
            "sampling_unit": "independent scramble estimates",
            "df": "R-1",
            "sobol": "scipy LMS+shift; random_base2; retain point zero",
            "clip": {
                "lower": float(lower),
                "upper": float(upper),
                "lower_hex": float(lower).hex(),
                "upper_hex": float(upper).hex(),
            },
            "truths": ["BSM", "independent_clipped_integral"],
            "coverage_uncertainty": "Wilson 95%",
        },
        "fresh_review": {
            "strikes": [80.0, 100.0, 120.0],
            "runs_per_case": 1,
            "paths_per_level": 256,
            "coverage_replay_runs": [0, 255, 511],
            "rqmc_reserved_runs": 1,
        },
        "timing": {
            "pairs_per_level": 4096,
            "warmup_repetitions": 1,
            "measured_repetitions": 7,
            "statistics": ["median", "p95"],
        },
        "bootstrap": {"resamples": 2000, "confidence": 0.95, "unit": "paired main run ratios"},
        "method_order": "seeded balanced permutations per epsilon",
        "phase_roots": dict(zip(PHASES, range(83101, 83702, 100), strict=True)),
        "seed_rule": "phase/case/budget/run/method/level/scramble fixed ordinals; uint32 retry child",
        "seed_independence": "unique physical seeds prevent reuse; do not prove independence",
        "block_size": 2048,
        "single_process": True,
        "threads": {"OPENBLAS_NUM_THREADS": 1, "OMP_NUM_THREADS": 1, "MKL_NUM_THREADS": 1},
        "cost_definition": copy.deepcopy(_COST),
        "amortizations": [1, 10, 100],
        "acceptance": {
            "teaching": "valid coupling/full roster/recomputation/4 figures/independent review",
            "speedup_epsilon_cells": 2,
            "rmse_rule": "rmse<=epsilon",
            "main_ratio_median_cap": 1.0,
            "bootstrap_ratio_upper_cap": 1.0,
            "exact_terminal_win_required": False,
            "report_cold_disadvantage": True,
        },
        "constraints": {
            "cpu": True,
            "torch": False,
            "public_api_changes": False,
            "production_dependencies": False,
            "external_data": False,
        },
        "seed_ledger_meta": None,
    }


def _integer(value, minimum: int, label: str, maximum: int | None = None) -> None:
    """Reject invalid integral dimensions, including boolean stand-ins."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, np.integer))
        or value < minimum
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(label + ": integer outside contract")


def _positive(value, label: str, *, zero=False) -> None:
    """Require a finite positive physical parameter, optionally allowing zero."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or not np.isfinite(value)
        or (value < 0 if zero else value <= 0)
    ):
        raise ValueError(label + ": finite positive contract required")


def protocol_conditions(p: dict) -> dict:
    """Copy every experimental condition, excluding hydrated rows and freeze evidence."""
    return copy.deepcopy(
        {k: v for k, v in p.items() if k not in {"seed_ledger", "frozen", "state"}}
    )


def _candidate_seed(logical_row: dict, retry: int) -> int:
    """Produce a logical child's next uint32 candidate before observing any result."""
    return int(
        np.random.SeedSequence(
            logical_row["entropy"], spawn_key=(*logical_row["logical_spawn_key"], retry)
        ).generate_state(1)[0]
    )


def resolve_seed_roster(
    logical_rows: list[dict], *, candidate_seed_fn=_candidate_seed
) -> list[dict]:
    """Resolve physical uint32 collisions in supplied fixed order and retain audit."""
    used, logical_ids, children = set(), set(), set()
    result = []
    for logical in logical_rows:
        logical_id = logical["logical_id"]
        child = (tuple(logical["entropy"]), tuple(logical["logical_spawn_key"]))
        if logical_id in logical_ids or child in children:
            raise ValueError("duplicate logical_id or entropy/logical_spawn_key")
        logical_ids.add(logical_id)
        children.add(child)
        candidates = []
        for retry in range(10000):
            seed = candidate_seed_fn(logical, retry)
            _integer(seed, 0, "physical seed", 2**32 - 1)
            candidates.append(seed)
            if seed not in used:
                used.add(seed)
                result.append(
                    {
                        **copy.deepcopy(logical),
                        "raw_seed": candidates[0],
                        "seed": seed,
                        "candidate_seeds": candidates,
                        "retry_count": retry,
                        "spawn_key": [*logical["logical_spawn_key"], retry],
                    }
                )
                break
        else:
            raise ValueError("seed collision retry limit exhausted before observations")
    return result


def _logical_rows(p: dict) -> list[dict]:
    """Enumerate logical slots in fixed phase and axis order before resolution."""
    rows = []

    def append(phase, case, budget, run, method, method_ordinal, level=-1, scramble=-1):
        axes = [case, budget, run, method_ordinal, level + 1, scramble + 1]
        logical_id = ".".join(map(str, [phase, case, budget, run, method, level, scramble]))
        rows.append(
            {
                "logical_id": logical_id,
                "phase": phase,
                "entropy": [p["phase_roots"][phase]],
                "logical_spawn_key": axes,
                "case": case,
                "budget": budget,
                "run": run,
                "method": method,
                "method_ordinal": method_ordinal,
                "level": level,
                "scramble": scramble,
            }
        )

    for run in range(p["pilot"]["streams"]):
        for level in p["pilot"]["levels"]:
            append("pilot", 0, 0, run, "mlmc", 0, level)
        append("pilot", 0, 0, run, "exact_cv", 3)
    for budget in range(len(p["epsilon"])):
        for run in range(p["main"]["outer_runs"]):
            for method_index, method in enumerate(METHODS):
                levels = p["main"]["levels_reserved"] if method == "mlmc" else [-1]
                for level in levels:
                    append("main", 0, budget, run, method, method_index, level)
    for case in range(len(p["rqmc"]["strikes"])):
        for budget in range(len(p["rqmc"]["powers"])):
            for run in range(p["rqmc"]["outer_runs"]):
                for method_index, scrambles in enumerate(p["rqmc"]["scrambles"]):
                    for scramble in range(scrambles):
                        append(
                            "coverage",
                            case,
                            budget,
                            run,
                            "rqmc_r" + str(scrambles),
                            method_index,
                            scramble=scramble,
                        )
    for case in range(len(p["fresh_review"]["strikes"])):
        for run in range(p["fresh_review"]["runs_per_case"]):
            for method_index, method in enumerate(METHODS):
                levels = p["main"]["levels_reserved"] if method == "mlmc" else [-1]
                for level in levels:
                    append("fresh_review", case, 0, run, method, method_index, level)
        for budget in range(len(p["rqmc"]["powers"])):
            for run in range(p["fresh_review"]["rqmc_reserved_runs"]):
                for r_index, scrambles in enumerate(p["rqmc"]["scrambles"]):
                    for scramble in range(scrambles):
                        append(
                            "fresh_review",
                            case,
                            budget,
                            run,
                            "rqmc_r" + str(scrambles),
                            len(METHODS) + r_index,
                            scramble=scramble,
                        )
    for level in p["pilot"]["levels"]:
        for run in range(p["timing"]["warmup_repetitions"] + p["timing"]["measured_repetitions"]):
            append("timing", 0, 0, run, "mlmc", 0, level)
    for phase in ("method_order", "bootstrap"):
        for budget in range(len(p["epsilon"])):
            append(phase, 0, budget, 0, phase, 0)
    # Phase order is fixed; ordinal axes determine order within every phase.
    rank = {phase: index for index, phase in enumerate(PHASES)}
    return sorted(
        rows,
        key=lambda r: (
            rank[r["phase"]],
            r["case"],
            r["budget"],
            r["run"],
            r["method_ordinal"],
            r["level"],
            r["scramble"],
        ),
    )


def build_seed_ledger(p: dict) -> list[dict]:
    """Reserve every pilot/main/coverage/fresh/timing/order/bootstrap candidate slot."""
    validate_protocol(p)
    if p["state"] != "candidate":
        raise ValueError("cannot generate or resolve a frozen seed ledger")
    return resolve_seed_roster(_logical_rows(p))


def seed_roster(p: dict, phase: str) -> list[dict]:
    """Read stored phase rows without spawning, retrying or modifying any seeds."""
    if phase not in PHASES:
        raise ValueError("unknown seed phase")
    if "seed_ledger" not in p:
        raise ValueError("hydrate seed ledger before using any phase")
    return [copy.deepcopy(row) for row in p["seed_ledger"] if row["phase"] == phase]


def validate_seed_ledger(rows: list[dict], *, candidate_seed_fn=_candidate_seed) -> None:
    """Verify uniqueness, candidate replay and the first-unused collision audit."""
    seeds, logical_ids, children = set(), set(), set()
    for row in rows:
        child = (tuple(row["entropy"]), tuple(row["logical_spawn_key"]))
        if row["logical_id"] in logical_ids or child in children or row["seed"] in seeds:
            raise ValueError("duplicate seed/logical_id/child in ledger")
        logical_ids.add(row["logical_id"])
        children.add(child)
        _integer(row["retry_count"], 0, "retry count", 9999)
        candidates = row["candidate_seeds"]
        if (
            len(candidates) != row["retry_count"] + 1
            or row["raw_seed"] != candidates[0]
            or row["seed"] != candidates[-1]
            or row["spawn_key"] != [*row["logical_spawn_key"], row["retry_count"]]
        ):
            raise ValueError("seed collision audit raw/retry/spawn mismatch")
        for retry, candidate in enumerate(candidates):
            _integer(candidate, 0, "seed candidate", 2**32 - 1)
            if candidate != candidate_seed_fn(row, retry):
                raise ValueError("seed candidate differs from logical spawn replay")
            if retry < len(candidates) - 1 and candidate not in seeds:
                raise ValueError("retry skipped an unused seed candidate")
        if candidates[-1] in seeds:
            raise ValueError("accepted physical seed already used")
        seeds.add(row["seed"])


def pack_seed_ledger(rows: list[dict]) -> dict[str, np.ndarray]:
    """Pack all logical and collision-audit fields into non-object NPZ columns."""
    if not rows:
        raise ValueError("nonempty seed ledger required")
    arrays = {
        "seed_ledger_" + name: np.asarray([row[name] for row in rows], dtype=np.str_)
        for name in ("logical_id", "phase")
    }
    arrays.update(
        {
            "seed_ledger_" + name: np.asarray([row[name] for row in rows], dtype=np.uint32)
            for name in ("raw_seed", "seed", "retry_count")
        }
    )
    arrays["seed_ledger_method"] = np.asarray(
        [row.get("method", "") for row in rows], dtype=np.str_
    )
    arrays["seed_ledger_method_present"] = np.asarray(
        ["method" in row for row in rows], dtype=np.bool_
    )
    for name in _OPTIONAL_INTS:
        arrays["seed_ledger_" + name] = np.asarray(
            [row.get(name, -1) for row in rows], dtype=np.int32
        )
        arrays["seed_ledger_" + name + "_present"] = np.asarray(
            [name in row for row in rows], dtype=np.bool_
        )
    for name in _RAGGED:
        lengths = np.asarray([len(row[name]) for row in rows], dtype=np.int64)
        arrays["seed_ledger_" + name + "_offsets"] = np.r_[0, np.cumsum(lengths)]
        arrays["seed_ledger_" + name + "_values"] = np.asarray(
            [item for row in rows for item in row[name]], dtype=np.uint32
        )
    return arrays


def unpack_seed_ledger(arrays: dict[str, np.ndarray]) -> list[dict]:
    """Restore logical rows from typed columns, rejecting malformed lengths/types."""
    names = {
        "seed_ledger_" + name
        for name in (
            "logical_id",
            "phase",
            "raw_seed",
            "seed",
            "retry_count",
            "method",
            "method_present",
        )
    }
    names.update(
        "seed_ledger_" + name + ending for name in _OPTIONAL_INTS for ending in ("", "_present")
    )
    names.update(
        "seed_ledger_" + name + ending for name in _RAGGED for ending in ("_values", "_offsets")
    )
    found = {name for name in arrays if name.startswith("seed_ledger_")}
    if found != names:
        raise ValueError("seed ledger typed column registry mismatch")
    values = {name: np.asarray(arrays[name]) for name in names}
    n = len(values["seed_ledger_seed"])
    if n == 0 or any(value.dtype.kind == "O" or value.ndim != 1 for value in values.values()):
        raise ValueError("nonempty 1D non-object seed ledger columns required")
    for name, value in values.items():
        field = name.removeprefix("seed_ledger_")
        kind = (
            "US"
            if field in {"logical_id", "phase", "method"}
            else "b"
            if field.endswith("_present")
            else "iu"
        )
        if value.dtype.kind not in kind:
            raise ValueError("seed ledger typed dtype mismatch: " + name)
    ragged_names = {
        "seed_ledger_" + name + ending for name in _RAGGED for ending in ("_values", "_offsets")
    }
    if any(len(value) != n for name, value in values.items() if name not in ragged_names):
        raise ValueError("seed ledger row count mismatch")
    for name in _RAGGED:
        offsets = values["seed_ledger_" + name + "_offsets"]
        flat = values["seed_ledger_" + name + "_values"]
        if (
            offsets.dtype.kind not in "iu"
            or flat.dtype.kind not in "iu"
            or len(offsets) != n + 1
            or offsets[0] != 0
            or offsets[-1] != len(flat)
            or np.any(np.diff(offsets) < 0)
        ):
            raise ValueError("seed ledger ragged offsets are invalid")
    result = []
    for i in range(n):
        row = {name: str(values["seed_ledger_" + name][i]) for name in ("logical_id", "phase")}
        row.update(
            {
                name: int(values["seed_ledger_" + name][i])
                for name in ("raw_seed", "seed", "retry_count")
            }
        )
        if values["seed_ledger_method_present"][i]:
            row["method"] = str(values["seed_ledger_method"][i])
        for name in _OPTIONAL_INTS:
            if values["seed_ledger_" + name + "_present"][i]:
                row[name] = int(values["seed_ledger_" + name][i])
        for name in _RAGGED:
            offsets = values["seed_ledger_" + name + "_offsets"]
            row[name] = (
                values["seed_ledger_" + name + "_values"][offsets[i] : offsets[i + 1]]
                .astype(int)
                .tolist()
            )
        result.append(row)
    return result


def _ledger_meta(arrays: dict[str, np.ndarray]) -> dict:
    """Describe typed columns with count and content provenance digest."""
    return {
        "digest": arrays_digest(arrays),
        "count": len(arrays["seed_ledger_seed"]),
        "columns": {
            name: {"dtype": value.dtype.str, "shape": list(value.shape)}
            for name, value in sorted(arrays.items())
        },
    }


def attach_seed_ledger(p: dict, rows: list[dict]) -> dict:
    """Copy a candidate and attach one resolved ledger plus its storage registry."""
    if p["state"] != "candidate":
        raise ValueError("cannot replace a frozen seed ledger")
    result = copy.deepcopy(p)
    result["seed_ledger"] = copy.deepcopy(rows)
    result["seed_ledger_meta"] = _ledger_meta(pack_seed_ledger(rows))
    return result


def protocol_for_json(p: dict) -> dict:
    """Copy protocol metadata for compact JSON; retain ledger digest, not rows."""
    return copy.deepcopy({name: value for name, value in p.items() if name != "seed_ledger"})


def hydrate_protocol(saved: dict, arrays: dict[str, np.ndarray]) -> dict:
    """Bind saved JSON to typed NPZ ledger before exposing any stored seed row."""
    ledger = {
        name: np.asarray(value) for name, value in arrays.items() if name.startswith("seed_ledger_")
    }
    if _ledger_meta(ledger) != saved.get("seed_ledger_meta"):
        raise ValueError("seed ledger digest/count/column registry differs from saved protocol")
    result = copy.deepcopy(saved)
    result["seed_ledger"] = unpack_seed_ledger(ledger)
    validate_protocol(result, require_frozen=result["state"] == "frozen")
    return result


def source_fingerprint(paths: list[Path]) -> dict:
    """Record file hashes and Python/NumPy/SciPy versions for provenance binding."""
    files = {}
    for path in paths:
        path = Path(path).resolve()
        key = str(path).split("/johnhull/", 1)[-1] if "/johnhull/" in str(path) else path.name
        if key in files:
            raise ValueError("duplicate source registry path")
        files[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        "files": files,
        "dependencies": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    }
    result["digest"] = json_digest(result)
    return result


def _validate_source(source: dict) -> None:
    """Require the complete fixed source registry and self-consistent digest."""
    if (
        set(source) != {"files", "dependencies", "digest"}
        or set(source["files"]) != set(SOURCE_FILES)
        or set(source["dependencies"]) != {"python", "numpy", "scipy"}
        or any(not isinstance(value, str) or len(value) != 64 for value in source["files"].values())
        or any(not isinstance(value, str) or not value for value in source["dependencies"].values())
        or source["digest"] != json_digest({k: v for k, v in source.items() if k != "digest"})
    ):
        raise ValueError("complete fixed source/dependency fingerprint required")


def validate_pilot_evidence(record: dict, arrays: dict, p: dict) -> dict:
    """Call the real saved-observation pilot checker; no hash-only acceptance."""
    path = HERE / "pilot.py"
    spec = importlib.util.spec_from_file_location("rbf08_protocol_pilot", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.validate_pilot(record, arrays, p)


def _freeze_digest(p: dict) -> str:
    """Bind every frozen metadata field without hashing the digest itself."""
    value = protocol_for_json(p)
    value["frozen"].pop("digest", None)
    return json_digest(value)


def freeze_protocol(
    candidate: dict, pilot_record: dict, pilot_arrays: dict, review: dict, *, source: dict
) -> dict:
    """Freeze every approved condition only after full pilot and source checks."""
    validate_protocol(candidate)
    if candidate["state"] != "candidate" or "seed_ledger" not in candidate:
        raise ValueError("full candidate and hydrated pilot ledger required for freeze")
    _validate_source(source)
    conditions = protocol_conditions(candidate)
    expected = {
        "pilot_record_digest": json_digest(pilot_record),
        "pilot_arrays_digest": arrays_digest(pilot_arrays),
        "protocol_digest": json_digest(conditions),
        "seed_ledger_digest": candidate["seed_ledger_meta"]["digest"],
        "source_fingerprint": source["digest"],
    }
    if pilot_record.get("schema") != "RB-F08-pilot-v1" or pilot_record.get("mode") != "full":
        raise ValueError("full pilot required; smoke cannot freeze")
    if review.get("decision") != "approved" or any(review.get(k) != v for k, v in expected.items()):
        raise ValueError("approved review/pilot/source fingerprint mismatch")
    for key in ("protocol_digest", "seed_ledger_digest", "source_fingerprint"):
        if pilot_record.get(key) != expected[key]:
            raise ValueError("pilot input/source/ledger fingerprint mismatch")
    if (
        review.get("approved_conditions") != conditions
        or review.get("approved_allocations") != pilot_record.get("allocations")
        or review.get("approved_cv_beta") != pilot_record.get("cv_beta")
    ):
        raise ValueError("review did not approve every condition/allocation/beta")
    ledger_columns = {k: v for k, v in pilot_arrays.items() if k.startswith("seed_ledger_")}
    if _ledger_meta(ledger_columns) != candidate["seed_ledger_meta"]:
        raise ValueError("pilot typed seed ledger differs from candidate")
    checked = validate_pilot_evidence(pilot_record, pilot_arrays, candidate)
    if not isinstance(checked, dict) or checked.get("passed") is not True:
        raise ValueError("full numerical pilot validation failed")
    result = copy.deepcopy(candidate)
    result["state"] = "frozen"
    result["frozen"] = {
        **expected,
        "review_digest": json_digest(review),
        "source": copy.deepcopy(source),
        "conditions": conditions,
        "allocations": copy.deepcopy(pilot_record["allocations"]),
        "cv_beta": pilot_record["cv_beta"],
        "pilot_validation": copy.deepcopy(checked),
    }
    result["frozen"]["digest"] = _freeze_digest(result)
    validate_protocol(result, require_frozen=True)
    return result


def verify_frozen_source(p: dict, source: dict) -> None:
    """Reject main execution with changed source/dependencies after pilot freeze."""
    validate_protocol(p, require_frozen=True)
    _validate_source(source)
    if source != p["frozen"]["source"]:
        raise ValueError("current source/dependency fingerprint differs from frozen pilot")


def verify_frozen_evidence(
    p: dict, pilot_record: dict, pilot_arrays: dict, review: dict, *, source: dict
) -> None:
    """Recheck saved pilot/review and rebuild the identical frozen approval."""
    validate_protocol(p, require_frozen=True)
    candidate = copy.deepcopy(p)
    candidate["state"] = "candidate"
    candidate.pop("frozen")
    reconstructed = freeze_protocol(candidate, pilot_record, pilot_arrays, review, source=source)
    if protocol_for_json(reconstructed) != protocol_for_json(p):
        raise ValueError("saved full pilot/review evidence differs from frozen protocol")


def validate_protocol(p: dict, *, require_frozen: bool = False) -> None:
    """Validate physical inputs, fixed roster metadata and complete frozen binding."""
    if p.get("schema") != SCHEMA or p.get("state") not in {"candidate", "frozen"}:
        raise ValueError("unknown protocol schema/state")
    if require_frozen and p["state"] != "frozen":
        raise ValueError("main requires independently reviewed frozen protocol")
    _integer(p["revision"], 1, "revision")
    parameters = p["parameters"]
    for key in ("spot", "strike", "maturity"):
        _positive(parameters[key], key)
    _positive(parameters["sigma"], "sigma", zero=True)
    for key in ("rate", "yield_rate"):
        if isinstance(parameters[key], bool) or not np.isfinite(parameters[key]):
            raise ValueError("finite rate/yield required")
    if p["scheme"] != "ordinary_euler" or p["product"]["kind"] != "european_call":
        raise ValueError("ordinary Euler European call contract required")
    if p["constraints"] != candidate_protocol()["constraints"]:
        raise ValueError("fixed CPU/torch-free/private API constraints required")
    _integer(p["base_steps"], 1, "base_steps")
    eps = p["epsilon"]
    if (
        not eps
        or any(not np.isfinite(e) or e <= 0 for e in eps)
        or any(a <= b for a, b in pairwise(eps))
    ):
        raise ValueError("positive strictly descending epsilon roster required")
    roots = p["phase_roots"]
    if set(roots) != set(PHASES) or len(set(roots.values())) != len(PHASES):
        raise ValueError("distinct complete phase roots required")
    for value in roots.values():
        _integer(value, 0, "phase root", 2**32 - 1)
    pilot = p["pilot"]
    levels = pilot["levels"]
    if not levels or levels != list(range(len(levels))) or len(levels) < 3:
        raise ValueError("contiguous pilot levels starting at zero required")
    for level in levels:
        _integer(level, 0, "pilot level", 20)
    for key in (
        "streams",
        "paths_per_stream",
        "exact_cv_paths_per_stream",
        "alpha_consecutive_levels",
    ):
        _integer(pilot[key], 2 if "paths" in key else 1, "pilot " + key)
    _integer(pilot["minimum_main_level"], 2, "minimum main level", levels[-1])
    for key in ("alpha_signal_multiplier", "negative_path_rate_cap"):
        _positive(pilot[key], key)
    if not 0 < pilot["bias_confidence"] < 1:
        raise ValueError("bias confidence must be inside (0,1)")
    for key in ("paths_per_run", "steps_per_run"):
        _integer(p["caps"][key], 1, "cap " + key)
    allocation = p["allocation"]
    _integer(allocation["minimum_paths"], 2, "minimum paths")
    _positive(allocation["variance_floor"], "variance floor", zero=True)
    if allocation["sampling_variance_fraction"] != 0.5 or allocation["bias_fraction_sqrt"] != 0.5:
        raise ValueError("fixed equal sampling/bias squared budget required")
    main = p["main"]
    _integer(main["outer_runs"], 1, "main outer_runs")
    if main["methods"] != list(METHODS) or main["levels_reserved"] != levels:
        raise ValueError("complete main methods and candidate level reservations required")
    if main["cv_expectation"] != "S0*exp(-qT)" or main["cv_beta"] != "independent pilot only":
        raise ValueError("fixed pilot CV and dividend-aware control expectation required")
    rqmc = p["rqmc"]
    _integer(rqmc["outer_runs"], 1, "coverage outer_runs")
    for name, minimum, maximum in (("powers", 0, 20), ("scrambles", 2, 1024)):
        values = rqmc[name]
        if not values or values != sorted(set(values)):
            raise ValueError("ordered unique " + name + " roster required")
        for value in values:
            _integer(value, minimum, name, maximum)
    strikes = rqmc["strikes"]
    if not strikes or strikes != sorted(set(strikes)):
        raise ValueError("positive ordered strike roster required")
    for strike in strikes:
        _positive(strike, "strike")
    for confidence in (main["confidence"], rqmc["confidence"], p["bootstrap"]["confidence"]):
        if not 0 < confidence < 1:
            raise ValueError("CI confidence must lie inside (0,1)")
    expected_clip = candidate_protocol()["rqmc"]["clip"]
    if rqmc["clip"] != expected_clip:
        raise ValueError("fixed nextafter clip values and hex metadata required")
    for key in ("pairs_per_level", "warmup_repetitions", "measured_repetitions"):
        _integer(p["timing"][key], 1, "timing " + key)
    for key in ("runs_per_case", "paths_per_level", "rqmc_reserved_runs"):
        _integer(p["fresh_review"][key], 1, "fresh_review " + key)
    if p["fresh_review"]["strikes"] != rqmc["strikes"]:
        raise ValueError("fresh diagnostic strikes must match fixed case roster")
    replay = p["fresh_review"]["coverage_replay_runs"]
    if not replay or replay != sorted(set(replay)):
        raise ValueError("fresh coverage replay requires ordered unique run indices")
    for run in replay:
        _integer(run, 0, "fresh coverage replay run", rqmc["outer_runs"] - 1)
    _integer(p["bootstrap"]["resamples"], 1, "bootstrap resamples")
    _integer(p["block_size"], 1, "block_size")
    if p["threads"] != candidate_protocol()["threads"] or p["single_process"] is not True:
        raise ValueError("single process and one BLAS thread required")
    if p["cost_definition"] != _COST:
        raise ValueError("complete physical cost definition and unique expense accounting required")
    if "seed_ledger" in p:
        rows = p["seed_ledger"]
        meta = _ledger_meta(pack_seed_ledger(rows))
        if meta != p["seed_ledger_meta"]:
            raise ValueError("seed ledger digest/count/registry mismatch")
        validate_seed_ledger(rows)
        logical = _logical_rows(p)
        if len(logical) != len(rows) or any(
            any(row.get(key) != value for key, value in intended.items())
            for row, intended in zip(rows, logical, strict=True)
        ):
            raise ValueError("full fixed phase/case/roster reservation differs from stored ledger")
    elif p.get("seed_ledger_meta") is not None:
        raise ValueError("typed seed ledger must be hydrated before protocol validation")
    if p["state"] == "frozen":
        frozen = p.get("frozen")
        if not frozen or "seed_ledger" not in p or "conditions" not in frozen:
            raise ValueError("frozen pilot/review/source fingerprint evidence missing")
        _validate_source(frozen["source"])
        if frozen["conditions"] != protocol_conditions(p) or frozen[
            "protocol_digest"
        ] != json_digest(protocol_conditions(p)):
            raise ValueError("frozen condition fingerprint mismatch")
        if frozen.get("digest") != _freeze_digest(p):
            raise ValueError("frozen pilot/review/roster fingerprint mismatch")
        if (
            not frozen.get("review_digest")
            or frozen.get("pilot_validation", {}).get("passed") is not True
        ):
            raise ValueError("full numerical pilot and approved review required")
