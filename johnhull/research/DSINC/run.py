"""DSINC runner: the frozen protocol as jobs, budgeted solver subprocesses, verdicts and exports.

``protocol.json`` fixes every setting, threshold and budget; ``build_roster`` turns it into the
jobs of the ``pilot`` and ``main`` phases.  ``execute_roster`` runs each job in its own
single-threaded subprocess (``launch_subprocess`` starts ``solve-job``, which ``solve_job``
answers) under a wall-time and peak-RSS limit and keeps one record per job: a failure, a time-out,
an exhausted budget or a skipped condition is a record with a status and a reason, never a
missing job.  ``evaluate`` applies the pure gates of ``gates.py`` to the records; the pilot's
summary and cost estimates become the freeze (``make_freeze_manifest``, ``verify_freeze``);
``write_results``, ``replay`` and ``export`` store, re-check and copy the outcome.  Nothing here
changes a threshold or a budget, clips a price or replaces a missing number: a job that gave no
usable result fails the checks that need it.

Commands: ``pilot --output DIR``, ``freeze --pilot DIR --output FILE``, ``main --freeze FILE
--output DIR``, ``solve-job --job FILE --out FILE`` (the child process), ``replay --results FILE``
and ``export --results FILE --to DIR``.  Prices are per unit strike (price/K) and spots are S/K.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import resource
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Literal

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SOURCE_FILES = (
    "johnhull/hullkit/src/hullkit/_dsinc_types.py",
    "johnhull/hullkit/src/hullkit/_dsinc_spectral.py",
    "johnhull/hullkit/src/hullkit/_dsinc_american.py",
    "johnhull/research/DSINC/heston_baseline.py",
    "johnhull/research/DSINC/reference_fd.py",
    "johnhull/research/DSINC/gates.py",
    "johnhull/research/DSINC/run.py",
    "johnhull/research/DSINC/protocol.json",
    "johnhull/research/DSINC/cases.json",
    "johnhull/research/DSINC/upstream_manifest.json",
)  # repo-relative; the freeze hashes them

LEVELS = ("S0", "S1", "S2")  # coarse to fine
CANDIDATES = ("S0", "S1")  # the levels that can be adopted; S2 only judges S1
QUANTITIES = ("european", "american", "eep")
LAUNCH_STATUSES = ("ok", "error", "timeout", "memory_exceeded", "nonfinite", "pricing_failure")
NOT_RUN = ("not_run_budget", "not_run_condition")
LIFTED = ("prices", "timing", "sizes", "diagnostics", "arrays")  # record fields taken from ``raw``
STDERR_TAIL = 2000  # characters of a failed child's stderr that the record keeps


def _dsinc(name: str):
    """Return ``hullkit._dsinc_<name>``, imported on first use.

    ``import hullkit`` takes about 0.4 s, which a child process that only runs a fixture job (or
    refuses to start) should not pay: the plan's own subprocess test gives such a job one second.
    """
    return importlib.import_module(f"hullkit._dsinc_{name}")


def _digest(*parts) -> str:
    """Return ``canonical_digest(*parts)`` of ``hullkit._dsinc_types``."""
    return _dsinc("types").canonical_digest(*parts)


def _sibling(name: str):
    """Return the research module ``name`` (gates, reference_fd, heston_baseline) loaded by path."""
    key = f"dsinc_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, HERE / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(key, None)
            raise
    return sys.modules[key]


def load_protocol() -> dict:
    """Return ``protocol.json``: every setting, threshold, roster rule and budget of the study."""
    return json.loads((HERE / "protocol.json").read_text())


def load_cases() -> dict:
    """Return ``cases.json``: the paper's printed values and the upstream Heston cases."""
    return json.loads((HERE / load_protocol()["cases_file"]).read_text())


def _native(value):
    """``json`` fallback: NumPy scalars and arrays as Python numbers and lists."""
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def _jsonable(value):
    """Return ``value`` as plain JSON data; a non-finite float becomes None (never written as NaN)."""
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, obj) -> None:
    """Write ``obj`` as compact JSON with sorted keys; NaN and infinity are a ValueError.

    The text goes to a temporary file next to ``path`` and replaces it, so an interrupted write
    never leaves half a file.
    """
    path = Path(path)
    text = json.dumps(obj, sort_keys=True, allow_nan=False, separators=(",", ":"), default=_native)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text + "\n")
    os.replace(temporary, path)


def _sha256(path: Path) -> str:
    """Return the sha256 hex digest of the bytes of the file at ``path``."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------------------------
# Roster: protocol.json -> jobs
# ---------------------------------------------------------------------------------------------


def _job_id(method: str, level, variant: str, expiry: float) -> str:
    """Return ``<method>-<level or grid>-<variant>-T<expiry>``."""
    return f"{method}-{level}-{variant}-T{expiry}"


def _spots(protocol: dict) -> list[float]:
    """Return the spots every solver job prices: the main ones, the Delta bumps, the boundary scan.

    Order: the main spots; then, for each bump, the main spots plus the bump and minus the bump;
    then the boundary-scan spots.
    """
    base = [float(spot) for spot in protocol["spots"]]
    bumped: list[float] = []
    for bump in protocol["delta_bumps"]:
        bumped += [round(spot + bump, 12) for spot in base] + [
            round(spot - bump, 12) for spot in base
        ]
    scan = protocol["boundary_scan_spots"]
    grid = np.linspace(scan["start"], scan["stop"], scan["count"])
    return base + bumped + [round(float(spot), 12) for spot in grid]


def _spectral_config(
    protocol: dict, level: str, expiry: float, sensitivity: str | None = None
) -> dict:
    """Return the ``SpectralConfig`` fields of a level, or of one single-axis variant of it.

    The panels are ``base_panels`` with the level's cutoff reached by appending doubled edges
    (S1 adds 1280, S2 adds 1280 and 2560).
    """
    spec = protocol["spectral"]
    shape = spec["levels"][level]
    panels = list(spec["base_panels"])
    while panels[-1] < shape["cutoff"]:
        panels.append(2 * panels[-1])
    if panels[-1] != shape["cutoff"]:
        raise ValueError(f"level {level}: the panels end at {panels[-1]}, not at {shape['cutoff']}")
    config = {
        "n_time": round(shape["steps_per_year"] * expiry),
        "n_var": shape["n_var"],
        "log_var_bounds": list(spec["log_var_bounds"]),
        "chi": spec["chi"],
        "panels": panels,
        "points_per_panel": shape["points_per_panel"],
    }
    if sensitivity is None:
        return config
    if sensitivity == "crossing_lower":
        config["crossing"] = "lower"
    elif sensitivity == "time_x2":
        config["n_time"] *= 2
    elif sensitivity == "time_x2_cutoff_x2":
        config["n_time"] *= 2
        panels.append(2 * panels[-1])
    elif sensitivity == "var_next":
        ladder = spec["var_ladder"]
        after = ladder.index(config["n_var"]) + 1
        if after == len(ladder):
            raise ValueError(f"level {level} has no next variance level in {ladder}")
        config["n_var"] = ladder[after]
    elif sensitivity == "points_plus4":
        config["points_per_panel"] += 4
    elif sensitivity == "cutoff_x2":
        panels.append(2 * panels[-1])
    elif sensitivity in ("chi_0.25", "chi_0.75"):
        config["chi"] = float(sensitivity.removeprefix("chi_"))
    elif sensitivity in ("domain_expand", "offset_plus_half", "offset_minus_half"):
        low, high = config["log_var_bounds"]
        step = (high - low) / (config["n_var"] - 1)
        if sensitivity == "domain_expand":
            # the same step, ceil(log 2 / step) nodes more on each side
            extra = math.ceil(math.log(2.0) / step)
            config["log_var_bounds"] = [low - extra * step, high + extra * step]
            config["n_var"] += 2 * extra
        else:
            shift = step / 2 if sensitivity == "offset_plus_half" else -step / 2
            config["log_var_bounds"] = [low + shift, high + shift]
    else:
        raise ValueError(f"unknown sensitivity {sensitivity!r}")
    return config


def _ladders(protocol: dict) -> dict[str, list[str]]:
    """Return the variants of the independent FD along each axis, coarse (``base``) to fine."""
    grid = protocol["fd"]["independent"]
    return {
        "x": ["base", *(f"x{n}" for n in grid["x"][1:])],
        "var": ["base", *(f"var{n}" for n in grid["var"][1:])],
        "time": ["base", *(f"time{n}" for n in grid["time"][1:])],
    }


def _independent_variants(protocol: dict) -> list[str]:
    """Return the nine independent FD variants: base, the axis refinements and the domain."""
    ladders = _ladders(protocol)
    return ["base", *ladders["x"][1:], *ladders["var"][1:], *ladders["time"][1:], "domain"]


def _fd_config(
    protocol: dict, group: str, variant: str, expiry: float, exercises: list[str] | None = None
) -> dict:
    """Return the ``FDConfig`` fields of an FD job of ``group`` (paper, independent, boundary).

    A grid is (n_x, n_var, steps per year) and ``n_time = round(steps * expiry)``.  The boundary
    jobs price American only and record the contact edge.
    """
    fd = protocol["fd"]
    spot_bounds = list(fd["log_spot_bounds"])
    if group == "paper":
        n_x, n_var, steps = fd["paper"]["grids"][("coarse", "fine").index(variant)]
        var_bounds = fd["paper"]["log_var_bounds"]
    elif group == "boundary":
        n_x, n_var, steps = fd["boundary"][variant]
        var_bounds = fd["boundary"]["log_var_bounds"]
    elif group == "independent":
        grid = fd["independent"]
        n_x, n_var, steps = grid["base"]
        var_bounds = grid["log_var_bounds"]
        if variant == "domain":
            spot_bounds, n_x = list(grid["domain"]["log_spot_bounds"]), grid["domain"]["n_x"]
        elif variant != "base":
            axis, size = re.fullmatch(r"(x|var|time)(\d+)", variant).groups()
            sizes = {"x": n_x, "var": n_var, "time": steps} | {axis: int(size)}
            n_x, n_var, steps = sizes["x"], sizes["var"], sizes["time"]
    else:
        raise ValueError(f"unknown FD group {group!r}")
    both = group != "boundary"
    return {
        "n_x": n_x,
        "n_var": n_var,
        "n_time": round(steps * expiry),
        "log_spot_bounds": spot_bounds,
        "log_var_bounds": list(var_bounds),
        "exercises": exercises or (["european", "american"] if both else ["american"]),
        "record_boundary": group == "boundary",
    }


def _job(phase, method, expiry, level, variant, role, config, spots, **fields) -> dict:
    """Return a job: the identity, what to solve, the spots, the condition and the repeat index."""
    return {
        "job_id": _job_id(method, level, variant, expiry),
        "phase": phase,
        "method": method,
        "expiry": expiry,
        "level": level,
        "variant": variant,
        "role": role,
        "config": config,
        "spots": list(spots),
        "condition": None,
        "repeat": None,
    } | fields


def _heston_job(case: dict, **fields) -> dict:
    """Return the pilot job of one upstream Heston case (priced at the case's own spot)."""
    return {
        "job_id": f"heston-{case['case_id']}",
        "phase": "pilot",
        "method": "heston_upstream",
        "expiry": case["T"],
        "level": None,
        "variant": case["case_id"],
        "role": "heston",
        "config": {"case_id": case["case_id"]},
        "spots": None,
        "condition": None,
        "repeat": None,
    } | fields


def build_roster(protocol: dict, phase: Literal["pilot", "main"]) -> list[dict]:
    """Return the jobs of ``phase`` in execution order (see the plan, Task 6).

    The pilot has 32 mandatory jobs followed by the 10 optional Heston cases.  The main run has the
    50 always-run jobs followed by the 38 conditional ones: the S1 sensitivities (only if S0 is
    not adopted at that expiry) and then the timing repeats of whichever candidate is adopted.
    """
    if phase not in ("pilot", "main"):
        raise ValueError(f"phase must be 'pilot' or 'main', got {phase!r}")
    spots = _spots(protocol)
    spec = protocol["spectral"]
    names = spec["sensitivities"]
    expiries = protocol["expiries"]

    def spectral(level, expiry, role, sensitivity=None, variant=None, **fields):
        config = _spectral_config(protocol, level, expiry, sensitivity)
        variant = variant or sensitivity or "base"
        return _job(phase, "spectral", expiry, level, variant, role, config, spots, **fields)

    def fd(group, variant, expiry, role, exercises=None):
        config = _fd_config(protocol, group, variant, expiry, exercises)
        return _job(phase, "fd", expiry, group, variant, role, config, spots)

    if phase == "pilot":
        short, long = expiries[0], expiries[-1]
        cases = load_cases()["heston_upstream"]["cases"]
        jobs = [_heston_job(cases[0])]
        jobs += [spectral("S0", expiry, "ladder") for expiry in (short, long)]
        jobs += [spectral("S0", short, "sensitivity", name) for name in names]
        jobs += [spectral("S1", short, "ladder"), spectral("S2", short, "ladder")]
        jobs += [fd("paper", "coarse", short, "paper_fd"), fd("paper", "fine", short, "paper_fd")]
        jobs += [fd("paper", "fine", long, "paper_fd", ["american"])]
        jobs += [fd("independent", v, short, "reference") for v in _independent_variants(protocol)]
        jobs += [
            fd("boundary", "check", short, "boundary"),
            fd("boundary", "primary", short, "boundary"),
        ]
        jobs += [fd("independent", _ladders(protocol)["x"][-1], long, "cost_probe")]
        jobs += [fd("boundary", "primary", long, "cost_probe")]
        return jobs + [_heston_job(case, optional=True) for case in cases[1:]]

    always, conditional = [], []
    fixed = [level for level in spec["candidates"] if level not in spec["conditional_candidates"]]
    for expiry in expiries:
        always += [spectral(level, expiry, "ladder") for level in LEVELS]
        always += [
            spectral(level, expiry, "sensitivity", name) for level in fixed for name in names
        ]
        always += [
            fd("independent", v, expiry, "reference") for v in _independent_variants(protocol)
        ]
        always += [fd("boundary", v, expiry, "boundary") for v in ("check", "primary")]
    for level in spec["conditional_candidates"]:
        for expiry in expiries:
            skip_if = f"S0_not_adopted:T{expiry}"
            conditional += [
                spectral(level, expiry, "sensitivity", name, condition=skip_if) for name in names
            ]
    runs = protocol["budget"]["timing_warmup"] + protocol["budget"]["timing_repeats"]
    for expiry in expiries:
        for level in spec["candidates"]:
            conditional += [
                spectral(
                    level,
                    expiry,
                    "timing",
                    variant=f"timing{i}",
                    repeat=i,
                    condition=f"adopted:{level}:T{expiry}",
                )
                for i in range(1, runs + 1)
            ]
    return always + conditional


def _identity(job: dict) -> str:
    """Return the canonical text of a job without its freeze estimate."""
    return json.dumps({k: v for k, v in job.items() if k != "estimate_seconds"}, sort_keys=True)


def check_job_in_roster(job: dict, roster: list[dict]) -> None:
    """Raise ValueError unless ``job`` is, field for field, an entry of ``roster``.

    The freeze estimate (``estimate_seconds``) is not part of a job's identity.
    """
    entry = next((item for item in roster if item["job_id"] == job.get("job_id")), None)
    if entry is None:
        raise ValueError(f"job {job.get('job_id')!r} is not in the roster")
    if _identity(job) != _identity(entry):
        raise ValueError(f"job {job['job_id']!r} differs from its entry in the roster")


def _job_sizes(job: dict) -> dict | None:
    """Return the sizes the cost estimates scale with (None for jobs that are not estimated)."""
    config = job["config"]
    if job["method"] == "spectral":
        spectral = _dsinc("types").SpectralConfig(**config)
        return {
            "n_omega": (len(spectral.panels) - 1) * spectral.points_per_panel,
            "n_var": spectral.n_var,
            "n_time": spectral.n_time,
            "scan_spacing": _dsinc("american").scan_spacing(spectral),
        }
    if job["method"] == "fd":
        return {
            "nodes": (config["n_x"] - 2) * config["n_var"],
            "bandwidth": config["n_var"],
            "n_time": config["n_time"],
        }
    return None


# ---------------------------------------------------------------------------------------------
# Execution: one budgeted subprocess per job
# ---------------------------------------------------------------------------------------------


def _price_check(prices) -> tuple[dict | None, str | None]:
    """Return ``(prices as lists, None)`` if every price is finite, else ``(None, reason)``."""
    if not isinstance(prices, dict) or not prices:
        return None, "the job reported no prices"
    arrays = {name: np.asarray(values, dtype=float) for name, values in prices.items()}
    bad = {name: int(np.count_nonzero(~np.isfinite(a))) for name, a in arrays.items()}
    bad = {name: count for name, count in bad.items() if count}
    if bad:
        return None, "non-finite prices: " + ", ".join(f"{n} in {k}" for k, n in bad.items())
    return {name: a.tolist() for name, a in arrays.items()}, None


def _unrun(job: dict, status: str, reason: str) -> dict:
    """Return the record of a job that was not started."""
    return job | {
        "status": status,
        "reason": reason,
        "prices": None,
        "raw": None,
        "timing": None,
        "sizes": None,
        "diagnostics": None,
        "arrays": None,
        "wall_seconds": None,
    }


def _record(job: dict, raw: dict, wall_seconds: float, budget: dict) -> dict:
    """Return the record of a job the launcher ran: its status, prices and the launcher's ``raw``.

    The launcher's status stands, except that an ``ok`` job is ``memory_exceeded`` if its reported
    peak RSS is over the limit and ``nonfinite`` if a price is not finite; prices are kept for
    ``ok`` jobs only.
    """
    status, reason = raw.get("status"), raw.get("reason")
    if status not in LAUNCH_STATUSES:
        status, reason = "error", f"the launcher reported the status {raw.get('status')!r}"
    prices = None
    if status == "ok":
        peak = raw.get("maxrss_bytes")
        if peak is not None and peak > budget["job_rss_bytes"]:
            status = "memory_exceeded"
            reason = f"peak RSS {peak} bytes is over the limit of {budget['job_rss_bytes']} bytes"
        else:
            prices, problem = _price_check(raw.get("prices"))
            if prices is None:
                status, reason = "nonfinite", problem
    clean = _jsonable(raw)
    return job | {
        "status": status,
        "reason": reason or (None if status == "ok" else f"the job reported {status}"),
        "prices": prices,
        "raw": clean,
        "timing": clean.get("timing"),
        "sizes": clean.get("sizes"),
        "diagnostics": clean.get("diagnostics"),
        "arrays": clean.get("arrays"),
        "wall_seconds": wall_seconds,
    }


def execute_roster(
    roster: list[dict],
    root: Path,
    budget: dict,
    *,
    launcher=None,
    clock=time.monotonic,
    should_run=None,
) -> list[dict]:
    """Run the jobs of ``roster`` in order and return one record per job.

    ``budget`` holds ``job_wall_seconds``, ``job_rss_bytes`` and ``total_seconds``.  ``root`` must
    be new or empty (else ValueError); ``<root>/records.json`` is rewritten after every job.
    With no budget left a job is ``not_run_budget``.  A job with a ``condition`` runs only if
    ``should_run(job, records)`` says so (else ``not_run_condition``) and its ``estimate_seconds``
    fits what is left (else ``not_run_budget``).  Otherwise ``launcher(job, root, timeout)`` runs
    it with ``timeout = min(job_wall_seconds, left)``; its return value is kept as ``raw`` and the
    record status follows ``_record``.  Nothing is retried and no budget is added.
    """
    root = Path(root)
    if root.exists() and any(root.iterdir()):
        raise ValueError(f"the output root {root} exists and is not empty")
    if should_run is None and any(job.get("condition") for job in roster):
        raise ValueError("the roster has conditional jobs, so should_run is needed")
    launcher = launcher or launch_subprocess
    root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    write_json(root / "records.json", records)
    started = clock()
    for job in roster:
        left = budget["total_seconds"] - (clock() - started)
        if left <= 0:
            records.append(_unrun(job, "not_run_budget", f"no budget left ({left:.1f} s)"))
        elif job.get("condition") and not should_run(job, records):
            records.append(
                _unrun(job, "not_run_condition", f"condition {job['condition']!r} is false")
            )
        elif job.get("condition") and job.get("estimate_seconds", 0.0) > left:
            reason = (
                f"the estimate of {job['estimate_seconds']:.1f} s exceeds the {left:.1f} s left"
            )
            records.append(_unrun(job, "not_run_budget", reason))
        else:
            began = clock()
            raw = launcher(job, root, min(budget["job_wall_seconds"], left))
            records.append(_record(job, raw, clock() - began, budget))
        write_json(root / "records.json", records)
    return records


def launch_subprocess(job: dict, root: Path, timeout: float) -> dict:
    """Run ``job`` in a fresh single-threaded ``solve-job`` process and return what it reported.

    The job goes to ``<root>/jobs/<id>.json`` and the child writes ``<root>/out/<id>.json``,
    which is returned.  Exceeding ``timeout`` gives ``timeout``; a non-zero exit gives ``error``
    with the exit code and the last ``STDERR_TAIL`` characters of stderr.
    """
    root = Path(root)
    job_file = root / "jobs" / f"{job['job_id']}.json"
    out_file = root / "out" / f"{job['job_id']}.json"
    job_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    write_json(job_file, job)
    env = os.environ | dict.fromkeys(load_protocol()["budget"]["thread_variables"], "1")
    command = [sys.executable, str(HERE / "run.py"), "solve-job"]
    command += ["--job", str(job_file), "--out", str(out_file)]
    try:
        done = subprocess.run(command, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "reason": f"exceeded {timeout:.6g} s"}
    tail = done.stderr[-STDERR_TAIL:]
    if done.returncode != 0:
        last = next((line for line in reversed(tail.splitlines()) if line.strip()), "")
        reason = f"exit code {done.returncode}: {last}"
        return {
            "status": "error",
            "reason": reason,
            "returncode": done.returncode,
            "stderr_tail": tail,
        }
    if not out_file.exists():
        reason = "the child exited with code 0 but wrote no output"
        return {"status": "error", "reason": reason, "returncode": 0, "stderr_tail": tail}
    result = json.loads(out_file.read_text())
    return result | {"stderr_tail": tail} if tail else result


def _save_arrays(root: Path, job_id: str, arrays: dict[str, np.ndarray]) -> dict:
    """Save ``arrays`` as ``<root>/arrays/<id>.npz`` and return the record's ``arrays`` entry.

    ``sha256`` hashes the file, ``content_sha256`` the arrays (the file carries a timestamp).
    """
    path = Path(root) / "arrays" / f"{job_id}.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, **arrays)
    return {
        "path": f"arrays/{job_id}.npz",
        "sha256": _sha256(path),
        "content_sha256": _digest(arrays),
        "bytes": path.stat().st_size,
    }


def _contract_and_model(job: dict) -> tuple:
    """Return the ``PutContract`` (expiry from the job) and the ``VarianceModel`` of the protocol."""
    types = _dsinc("types")
    protocol = load_protocol()
    contract = protocol["contract"]
    return (
        types.PutContract(
            contract["strike"], job["expiry"], contract["domestic_rate"], contract["foreign_rate"]
        ),
        types.VarianceModel(**protocol["model"]),
    )


def _solved(prices: dict, **parts) -> dict:
    """Return a solver's report: status ``ok``, or ``nonfinite`` with the prices dropped."""
    checked, problem = _price_check(prices)
    status = "ok" if checked is not None else "nonfinite"
    return {"status": status, "reason": problem, "prices": checked} | parts


def _solve_spectral(job: dict, root: Path) -> dict:
    """Solve a spectral job: propagators, then the American recursion; save the boundary arrays."""
    types, spectral, american = _dsinc("types"), _dsinc("spectral"), _dsinc("american")
    contract, model = _contract_and_model(job)
    config = types.SpectralConfig(**job["config"])
    spots = np.asarray(job["spots"], dtype=float)
    sizes = _job_sizes(job)
    started = time.perf_counter()
    propagators = spectral.build_propagators(contract, model, config)
    tag = {
        "coefficients_tag": propagators.coefficients_tag,
        "propagators_digest": propagators.digest,
    }
    sizes = sizes | {"propagator_bytes": propagators.nbytes}
    try:
        result = american.american_put(contract, model, spots, config, propagators=propagators)
    except types.PricingFailure as failure:
        details = dict(failure.details)
        arrays = {
            "log_boundary": details.pop("log_boundary"),
            "boundary_status": details.pop("boundary_status"),
            "log_variances": propagators.log_variances,
        }
        timing = {
            "setup_seconds": propagators.setup_seconds,
            "total_seconds": time.perf_counter() - started,
        }
        return {
            "status": "pricing_failure",
            "reason": str(failure),
            "prices": None,
            "details": {"code": failure.code} | details,
            "timing": timing,
            "sizes": sizes,
            "diagnostics": tag | {"max_root_residual": None},
            "arrays": _save_arrays(root, job["job_id"], arrays),
        }
    diagnostics = result.diagnostics
    timing = {
        "setup_seconds": diagnostics["setup_seconds"],
        "recursion_seconds": diagnostics["recursion_seconds"],
        "query_seconds": diagnostics["query_seconds"],
        "solve_seconds": diagnostics["recursion_seconds"] + diagnostics["query_seconds"],
        "total_seconds": time.perf_counter() - started,
    }
    arrays = {
        "log_boundary": result.log_boundary,
        "boundary_status": result.boundary_status,
        "log_variances": result.log_variances,
        "times": result.times,
    }
    prices = {
        "european": result.european,
        "american": result.american,
        "eep": result.early_exercise_premium,
    }
    return _solved(
        prices,
        timing=timing,
        sizes=sizes,
        diagnostics=diagnostics | tag,
        arrays=_save_arrays(root, job["job_id"], arrays),
    )


def _solve_fd(job: dict, root: Path) -> dict:
    """Solve a finite-difference job; the contact edge is saved when the job records it."""
    reference_fd = _sibling("reference_fd")
    contract, model = _contract_and_model(job)
    config = reference_fd.FDConfig(**job["config"])
    result = reference_fd.reference_put(contract, model, np.asarray(job["spots"]), config)
    prices = {
        name: getattr(result, name)
        for name in ("european", "american")
        if getattr(result, name) is not None
    }
    if len(prices) == 2:
        prices["eep"] = prices["american"] - prices["european"]
    timing = {
        "setup_seconds": result.setup_seconds,
        "solve_seconds": sum(result.solve_seconds.values()),
        "solve_seconds_by_style": result.solve_seconds,
    }
    arrays = None
    if result.contact_edge is not None:
        arrays = _save_arrays(
            root,
            job["job_id"],
            {"contact_edge": result.contact_edge, "log_variances": result.log_variances},
        )
    return _solved(
        prices,
        timing=timing,
        sizes=_job_sizes(job) | {"lu_nnz": result.lu_nnz},
        diagnostics={"complementarity": result.complementarity},
        arrays=arrays,
    )


def _solve_heston(job: dict, root: Path) -> dict:
    """Run one upstream Heston case through ``heston_baseline`` (a preparatory comparison)."""
    case_id = job["config"]["case_id"]
    case = next(c for c in load_cases()["heston_upstream"]["cases"] if c["case_id"] == case_id)
    report = _sibling("heston_baseline").run_heston_baseline(case)
    prices = {
        f"{solver}_{style}": [report[solver][style]]
        for solver in ("dsinc", "fd")
        for style in ("european", "american")
    } | {"dsinc_eep": [report["dsinc"]["eep"]]}
    seconds = {"dsinc": report["dsinc"]["seconds"], "fd": report["fd"]["seconds"]}
    return _solved(prices, timing=seconds, sizes=None, diagnostics=report, arrays=None)


def _solve_fixture(job: dict, root: Path) -> dict:
    """Run a test fixture: ``params`` may hold value, sleep, fail, nan and array_bytes."""
    params = job.get("params", {})
    time.sleep(params.get("sleep", 0.0))
    if params.get("fail"):
        raise RuntimeError(f"fixture job {job['job_id']} was told to fail")
    value = float("nan") if params.get("nan") else params.get("value", 0.0)
    arrays = None
    if params.get("array_bytes"):
        noise = np.frombuffer(np.random.default_rng(0).bytes(params["array_bytes"]), dtype=np.uint8)
        arrays = _save_arrays(root, job["job_id"], {"noise": noise})
    return _solved({"american": [value]}, timing=None, sizes=None, diagnostics=None, arrays=arrays)


def solve_job(job: dict, root: Path) -> dict:
    """Child side: solve ``job`` and return its report (status, prices, timing, sizes, ...).

    ``contract`` and ``model`` come from the protocol, the expiry, config and spots from the job.
    Arrays go to ``<root>/arrays/<id>.npz`` and are described in the report; a numerical
    ``PricingFailure`` is a ``pricing_failure`` report with its details and arrays; a non-finite
    price is a ``nonfinite`` report without prices.  ``maxrss_bytes`` is the process's peak RSS.
    """
    solvers = {
        "spectral": _solve_spectral,
        "fd": _solve_fd,
        "heston_upstream": _solve_heston,
        "fixture": _solve_fixture,
    }
    if job["method"] not in solvers:
        raise ValueError(f"unknown method {job['method']!r}; use one of {tuple(solvers)}")
    report = solvers[job["method"]](job, Path(root))
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024  # Linux reports KiB
    return report | {"maxrss_bytes": peak}


# ---------------------------------------------------------------------------------------------
# Evaluation: records -> verdicts
# ---------------------------------------------------------------------------------------------


def condition_met(condition: str, selections: dict[str, dict]) -> bool:
    """Read a job condition from the level selections, which are keyed by ``str(expiry)``.

    ``adopted:<S>:T<expiry>`` is true when S (S0 or S1) is adopted at that expiry and
    ``S0_not_adopted:T<expiry>`` when S0 is not.  Anything else is a ValueError.
    """
    parts = condition.split(":")
    if len(parts) == 3 and parts[0] == "adopted" and parts[1] in CANDIDATES:
        token, wanted = parts[2], parts[1]
    elif len(parts) == 2 and parts[0] == "S0_not_adopted":
        token, wanted = parts[1], None
    else:
        raise ValueError(f"unknown condition {condition!r}")
    if not token.startswith("T") or token[1:] not in selections:
        raise ValueError(f"condition {condition!r} names an expiry without a selection")
    adopted = selections[token[1:]]["adopted"]
    return adopted == wanted if wanted else adopted != "S0"


def _gap(first: dict | None, second: dict | None) -> float | None:
    """Largest |first - second| over the quantities and spots, or None if either is missing."""
    if first is None or second is None:
        return None
    return float(max(np.max(np.abs(first[q] - second[q])) for q in QUANTITIES))


def _estimate_problem(roster: list[dict], estimates: list[dict], budget: dict) -> str | None:
    """Return why ``estimates`` cannot be frozen for ``roster`` (None if they can).

    Every job needs a measured estimate, no job may be estimated above ``job_wall_seconds`` (the
    conditional ones included) and the jobs without a condition may add up to at most
    ``main_seconds`` (decision D-5: conditional jobs stay outside that gate).
    """
    ids = [job["job_id"] for job in roster]
    given = {entry["job_id"]: entry for entry in estimates}
    if len(given) != len(estimates) or set(given) != set(ids):
        missing, extra = sorted(set(ids) - set(given)), sorted(set(given) - set(ids))
        return (
            f"the estimates do not match the main roster: {len(missing)} missing {missing[:3]}, "
            f"{len(extra)} unexpected {extra[:3]}"
        )
    unmeasured = [
        i for i in ids if given[i]["status"] != "estimated" or given[i]["seconds"] is None
    ]
    if unmeasured:
        return f"{len(unmeasured)} job(s) are unmeasured: {unmeasured[:5]}"
    limit = budget["job_wall_seconds"]
    slow = [i for i in ids if given[i]["seconds"] > limit]
    if slow:
        return (
            f"{len(slow)} job(s) are estimated above the {limit:g} s limit of one job: {slow[:5]}"
        )
    always = sum(given[job["job_id"]]["seconds"] for job in roster if not job["condition"])
    if always > budget["main_seconds"]:
        return f"the always-run jobs are estimated at {always:.0f} s, above {budget['main_seconds']:g} s"
    return None


class _Evaluation:
    """The verdict pieces computed from a set of records.

    A job whose record is missing, not ``ok`` or without prices is simply unavailable: the checks
    that need it fail (or stay pending for a job that has not run), nothing is filled in.
    """

    def __init__(self, records: list[dict], root: Path, protocol: dict, cases: dict) -> None:
        self.by_id = {record["job_id"]: record for record in records}
        self.root = Path(root)
        self.protocol = protocol
        self.cases = cases
        self.gates = _sibling("gates")
        self.thresholds = protocol["thresholds"]
        self.n_main = len(protocol["spots"])
        self.atm = protocol["spots"].index(1.0)
        self.expiries = protocol["expiries"]

    def record(self, method: str, level, variant: str, expiry: float) -> dict | None:
        """Return the record of a job if it is ``ok`` and priced, else None."""
        found = self.by_id.get(_job_id(method, level, variant, expiry))
        return found if found and found["status"] == "ok" and found.get("prices") else None

    def main_prices(self, record: dict | None) -> dict | None:
        """Return european/american/eep at the main spots of an ok record, or None."""
        if record is None or any(q not in record["prices"] for q in QUANTITIES):
            return None
        return {q: np.asarray(record["prices"][q][: self.n_main], dtype=float) for q in QUANTITIES}

    def american(self, record: dict | None) -> np.ndarray | None:
        """Return the American prices at the main spots of an ok record, or None."""
        if record is None or "american" not in record["prices"]:
            return None
        return np.asarray(record["prices"]["american"][: self.n_main], dtype=float)

    def arrays(self, record: dict) -> dict[str, np.ndarray]:
        """Load the arrays a record saved."""
        with np.load(self.root / record["arrays"]["path"]) as stored:
            return {name: stored[name] for name in stored.files}

    def step(self, axis: str, record: dict) -> float:
        """Return the actual step size of an FD job along ``axis`` (x, var or time)."""
        config = record["config"]
        if axis == "x":
            low, high = config["log_spot_bounds"]
            return (high - low) / (config["n_x"] - 1)
        if axis == "var":
            low, high = config["log_var_bounds"]
            return (high - low) / (config["n_var"] - 1)
        return record["expiry"] / config["n_time"]

    def fd_reference(self, expiry: float) -> dict:
        """Build the independent FD reference of an expiry and judge its convergence (D-3)."""
        found = {
            variant: self.by_id.get(_job_id("fd", "independent", variant, expiry))
            for variant in _independent_variants(self.protocol)
        }
        prices = {
            v: self.main_prices(r if r and r["status"] == "ok" else None) for v, r in found.items()
        }
        missing = [
            _job_id("fd", "independent", v, expiry) for v, price in prices.items() if price is None
        ]
        if missing:
            reasons = [f"missing:{job}" for job in missing]
            return {"converged": False, "reasons": reasons, "axes": None, "prices": None}

        def flat(price: dict) -> np.ndarray:
            return np.concatenate([price[q] for q in QUANTITIES])

        axes = {}
        for axis, variants in _ladders(self.protocol).items():
            steps = np.array([self.step(axis, found[v]) for v in variants])
            values = np.array([flat(prices[v]) for v in variants])
            axes[axis] = self.gates.axis_convergence(steps, values, self.thresholds)
        domain = float(np.max(np.abs(flat(prices["domain"]) - flat(prices["base"]))))
        verdict = self.gates.reference_verdict(axes, domain, self.thresholds)
        finest = {axis: prices[variants[-1]] for axis, variants in _ladders(self.protocol).items()}
        reference = {
            q: self.gates.fd_reference(prices["base"][q], {a: finest[a][q] for a in finest})
            for q in QUANTITIES
        }
        return verdict | {"axes": axes, "domain_change": domain, "prices": reference}

    def sensitivity_inputs(self, level: str, expiry: float) -> dict | None:
        """Return the prices of a level's sensitivities for ``gates.select_level``.

        None if any of the variants has not run (``not_run_*`` or no record yet: the level's
        sensitivities are pending); a variant that ran but gave no prices is None inside the dict.
        """
        variants = {}
        for name in self.protocol["spectral"]["sensitivities"]:
            found = self.by_id.get(_job_id("spectral", level, name, expiry))
            if found is None or found["status"] in NOT_RUN:
                return None
            variants[name] = self.main_prices(found if found["status"] == "ok" else None)
        return variants

    def sensitivity_gaps(self, level: str, expiry: float) -> dict:
        """Return each sensitivity's largest price difference from the level's base solve (or None)."""
        base = self.main_prices(self.record("spectral", level, "base", expiry))
        return {
            name: _gap(self.main_prices(self.record("spectral", level, name, expiry)), base)
            for name in self.protocol["spectral"]["sensitivities"]
        }

    def bounds(self, level: str, expiry: float) -> dict | None:
        """Return the no-arbitrage margins of a level's base solve over every spot it priced."""
        found = self.record("spectral", level, "base", expiry)
        if found is None:
            return None
        contract = self.protocol["contract"] | {"expiry": expiry}
        prices = found["prices"]
        return self.gates.bounds_check(
            prices["european"],
            prices["american"],
            found["spots"],
            contract,
            self.thresholds["bounds"],
        )

    def boundary(self, level: str, expiry: float) -> dict:
        """Return the boundary gate of a level's base solve against the dedicated fine-time FD.

        The arrays of a ``pricing_failure`` base solve are judged too: its failed roots are what
        the gate's ``root_failure_in_window`` reports (its ``max_root_residual`` is None).
        """
        spectral = self.by_id.get(_job_id("spectral", level, "base", expiry))
        if spectral is not None and spectral["status"] not in ("ok", "pricing_failure"):
            spectral = None
        primary = self.record("fd", "boundary", "primary", expiry)
        check = self.record("fd", "boundary", "check", expiry)
        needed = {
            _job_id("spectral", level, "base", expiry): spectral,
            _job_id("fd", "boundary", "primary", expiry): primary,
            _job_id("fd", "boundary", "check", expiry): check,
        }
        missing = [job for job, found in needed.items() if found is None or not found.get("arrays")]
        if missing:
            return {
                "status": "unavailable",
                "level": level,
                "reasons": [f"missing:{j}" for j in missing],
            }
        mine, fine, coarse = self.arrays(spectral), self.arrays(primary), self.arrays(check)
        low, high = primary["config"]["log_spot_bounds"]
        dx = (high - low) / (primary["config"]["n_x"] - 1)
        rules = self.thresholds["boundary"]
        diagnostics = spectral["diagnostics"] or {}
        verdict = self.gates.boundary_gate(
            spectral_log_var=mine["log_variances"],
            spectral_boundary=mine["log_boundary"],
            spectral_status=mine["boundary_status"],
            fd_log_var=fine["log_variances"],
            fd_primary=fine["contact_edge"],
            fd_check=coarse["contact_edge"],
            fd_dx=dx,
            fd_x_bounds=(low, high),
            thresholds=rules,
            max_root_residual=diagnostics.get("max_root_residual"),
        )
        return verdict | {
            "level": level,
            "status_counts": diagnostics.get("status_counts"),
            "geometry": {
                "fd_dx": dx,
                "fd_x_bounds": [low, high],
                "edge_cells": rules["edge_cells"],
                "time_window": rules["time_window"],
                "variance_window": rules["variance_window"],
            },
            "arrays": {
                "spectral": spectral["arrays"]["path"],
                "fd_primary": primary["arrays"]["path"],
            },
        }

    def deltas(self, record: dict | None) -> dict | None:
        """Return the central-difference Deltas of a record at each bump (a diagnostic)."""
        if record is None:
            return None
        n = self.n_main
        result = {}
        for index, bump in enumerate(self.protocol["delta_bumps"]):
            first = n + 2 * n * index  # the spots plus the bump, then the spots minus the bump
            result[str(bump)] = {
                q: self.gates.deltas(
                    np.asarray(record["prices"][q][first : first + n]),
                    np.asarray(record["prices"][q][first + n : first + 2 * n]),
                    bump,
                ).tolist()
                for q in ("european", "american")
            }
        return result

    def paper(self) -> dict:
        """Compare the S0 prices with the paper's printed values (gate) and its other columns."""
        paper = self.cases["three_halves_paper"]

        def printed(name: str):
            section, column = name.rsplit(".", 1)  # the section name holds a dot: "T0.5.eep"
            return paper[section][column]

        short, long = self.expiries[0], self.expiries[-1]
        first = self.main_prices(self.record("spectral", "S0", "base", short))
        second = self.american(self.record("spectral", "S0", "base", long))
        values = {}
        if first is not None:
            values["T0.5.american_n100"] = first["american"].tolist()
            values["T0.5.european"] = first["european"].tolist()
        if second is not None:
            values["T1.american_atm"] = float(second[self.atm])
        roles = paper["roles"]
        anchors = {name: printed(name) for name in roles["gate"]}
        anchors |= {
            n: "not_available" for n in roles["diagnostic"] if printed(n) == "not_available"
        }
        match = self.gates.paper_match(values, anchors, self.thresholds["paper_match"])

        doubled = self.american(self.record("spectral", "S0", "time_x2", short))
        coarse = self.american(self.record("fd", "paper", "coarse", short))
        fine = self.american(self.record("fd", "paper", "fine", short))
        fine_long = self.american(self.record("fd", "paper", "fine", long))
        columns = {
            "T0.5.eep": None if first is None else first["eep"],
            "T0.5.american_n200": doubled,
            "T0.5.fd_coarse": coarse,
            "T0.5.fd_fine": fine,
            "T1.fd_fine_atm": None if fine_long is None else fine_long[self.atm],
        }
        diagnostics = {}
        for name, computed in columns.items():
            if computed is None:
                diagnostics[name] = None
                continue
            difference = np.asarray(computed) - np.asarray(printed(name))
            diagnostics[name] = {
                "printed": printed(name),
                "computed": np.asarray(computed).tolist(),
                "difference": difference.tolist(),
                "max_abs_difference": float(np.max(np.abs(difference))),
            }
        return {"match": match, "diagnostics": diagnostics}

    def basis(self, job: dict) -> dict | None:
        """Pick the measured pilot job a main job's cost is scaled from.

        The same method, level and variant at the same expiry, else at another expiry, else the
        base solve of the level at the same, else at another expiry; a timing repeat is the
        level's base solve.  Only pilot jobs that ran ``ok`` with timings are candidates.
        """
        variant = "base" if job["role"] == "timing" else job["variant"]
        wanted = (
            ((job["method"], job["level"], variant), True),
            ((job["method"], job["level"], variant), False),
            ((job["method"], job["level"], "base"), True),
            ((job["method"], job["level"], "base"), False),
        )
        measured = [
            r
            for r in self.by_id.values()
            if r["status"] == "ok" and r.get("timing") and r.get("sizes")
        ]
        for key, same_expiry in wanted:
            for candidate in measured:
                kind = (candidate["method"], candidate["level"], candidate["variant"])
                if kind == key and (candidate["expiry"] == job["expiry"]) == same_expiry:
                    return candidate
        return None

    def estimates(self) -> list[dict]:
        """Estimate the seconds of every main job from the pilot's measurements (factor included)."""
        factor = self.protocol["budget"]["estimate_factor"]
        result = []
        for job in build_roster(self.protocol, "main"):
            found = self.basis(job)
            measured = None
            if found is not None:
                keys = (
                    ("n_omega", "n_var", "n_time", "scan_spacing")
                    if job["method"] == "spectral"
                    else ("nodes", "bandwidth", "n_time")
                )
                measured = {
                    "setup_seconds": found["timing"]["setup_seconds"],
                    "solve_seconds": found["timing"]["solve_seconds"],
                } | {key: found["sizes"][key] for key in keys}
            estimate = self.gates.estimate_seconds(job["method"], measured, _job_sizes(job), factor)
            result.append(
                {
                    "job_id": job["job_id"],
                    "condition": job["condition"],
                    "basis": None if found is None else found["job_id"],
                }
                | estimate
            )
        return result

    def heston(self) -> dict:
        """Summarise the upstream Heston comparison (a diagnostic: the upstream is not certified)."""
        summary = {}
        for found in self.by_id.values():
            if found["method"] != "heston_upstream":
                continue
            entry = {
                "status": found["status"],
                "reason": found["reason"],
                "optional": bool(found.get("optional")),
            }
            if found["status"] == "ok":
                report = found["diagnostics"]
                entry |= {
                    "differences": report["differences"],
                    "dsinc_counts": report["dsinc"]["counts"],
                    "certified": report["certified"],
                }
            summary[found["variant"]] = entry
        return summary

    def costs(self, expiry: float, levels: dict, reference: dict | None) -> dict:
        """Return the cost table of an expiry: setup, solve and error of each solve, the timing repeats."""

        def row(found: dict, price: dict | None) -> dict:
            timing = found["timing"] or {}
            return {
                "error": _gap(price, reference),
                "setup_seconds": timing.get("setup_seconds"),
                "solve_seconds": timing.get("solve_seconds"),
                "wall_seconds": found["wall_seconds"],
                "maxrss_bytes": (found["raw"] or {}).get("maxrss_bytes"),
            }

        spectral = {}
        for level in LEVELS:
            found = self.record("spectral", level, "base", expiry)
            if found is not None:
                spectral[level] = row(found, levels[level])
        fd = {}
        for variant in [*_independent_variants(self.protocol), "check", "primary"]:
            group = "boundary" if variant in ("check", "primary") else "independent"
            found = self.record("fd", group, variant, expiry)
            if found is not None:
                fd[f"{group}-{variant}"] = row(found, self.main_prices(found))
        timing = {}
        warmup = self.protocol["budget"]["timing_warmup"]
        runs = warmup + self.protocol["budget"]["timing_repeats"]
        for level in CANDIDATES:
            rows = []
            for i in range(1, runs + 1):
                found = self.record("spectral", level, f"timing{i}", expiry)
                if found is not None:
                    rows.append({"repeat": i, "warmup": i <= warmup} | row(found, None))
            measured = [r for r in rows if not r["warmup"]]
            stats = {}
            for key in ("setup_seconds", "solve_seconds", "wall_seconds"):
                series = [r[key] for r in measured if r[key] is not None]
                if series:
                    stats[key] = {
                        "mean": sum(series) / len(series),
                        "min": min(series),
                        "max": max(series),
                    }
            if rows:
                timing[level] = {"runs": rows, "measured": len(measured), "stats": stats}
        return {"spectral": spectral, "fd": fd, "timing": timing}

    def pilot_verdicts(self) -> dict:
        """Return the pilot's verdicts, the main-job estimates and ``all_pass`` (see Task 7)."""
        th = self.thresholds
        short = self.expiries[0]
        key = str(short)
        paper = self.paper()
        reference = self.fd_reference(short)
        s0 = self.main_prices(self.record("spectral", "S0", "base", short))
        reference_prices = self.reference_arrays(reference)
        distance = _gap(s0, reference_prices)
        boundary = self.boundary("S0", short)
        sensitivities = self.sensitivity_gaps("S0", short)
        crossing = sensitivities["crossing_lower"]
        estimates = self.estimates()
        main_roster = build_roster(self.protocol, "main")
        problem = _estimate_problem(main_roster, estimates, self.protocol["budget"])
        seconds = {e["job_id"]: e["seconds"] for e in estimates if e["seconds"] is not None}
        mandatory = [
            j["job_id"] for j in build_roster(self.protocol, "pilot") if not j.get("optional")
        ]
        ran = [self.by_id[i]["status"] for i in mandatory if i in self.by_id]
        checks = {
            "mandatory_jobs_ok": len(ran) == len(mandatory) and set(ran) == {"ok"},
            "paper_match": bool(paper["match"]["pass"]),
            "fd_reference_converged": bool(reference["converged"]),
            "s0_within_independent_tolerance": distance is not None
            and distance <= th["independent"],
            "boundary_gate": boundary["status"] == "pass",
            "crossing_lower_within_tolerance": crossing is not None
            and crossing <= th["sensitivity"],
            "estimates_within_budget": problem is None,
        }
        return {
            "checks": checks,
            "all_pass": all(checks.values()),
            "protocol_digest": _digest(self.protocol),
            "paper_match": paper["match"],
            "paper_diagnostics": paper["diagnostics"],
            "fd_reference": {key: reference},
            "s0_vs_reference": {key: distance},
            "boundary": {key: boundary},
            "crossing_lower": {key: crossing},
            "sensitivities": {key: sensitivities},
            "bounds": {str(e): self.bounds("S0", e) for e in self.expiries},
            "heston": self.heston(),
            "estimates": estimates,
            "budget": {
                "always_run_seconds": sum(
                    seconds.get(j["job_id"], 0.0) for j in main_roster if not j["condition"]
                ),
                "longest_job_seconds": max(seconds.values(), default=None),
                "problem": problem,
            },
            "accounting": _accounting(list(self.by_id.values())),
            "exports": [],
        }

    def reference_arrays(self, reference: dict) -> dict | None:
        """Return the reference prices of ``fd_reference`` as arrays (None if it is unavailable)."""
        if reference["prices"] is None:
            return None
        return {q: np.asarray(reference["prices"][q]) for q in QUANTITIES}

    def main_verdicts(self) -> dict:
        """Return the main run's verdicts: selection, validation, boundary, label, costs, exports."""
        paper = self.paper()
        out: dict = {
            name: {}
            for name in (
                "selections",
                "fd_reference",
                "bounds",
                "boundary",
                "independent_validated",
                "nonmonotone_effect",
                "deltas",
                "costs",
            )
        }
        for expiry in self.expiries:
            key = str(expiry)
            reference = self.fd_reference(expiry)
            levels = {
                level: self.main_prices(self.record("spectral", level, "base", expiry))
                for level in LEVELS
            }
            selection = self.gates.select_level(
                levels,
                self.reference_arrays(reference),
                {level: self.sensitivity_inputs(level, expiry) for level in CANDIDATES},
                self.thresholds,
            )
            adopted = selection["adopted"]
            judged = adopted or CANDIDATES[0]  # S0 is the level shown when nothing is adopted
            bounds = {level: self.bounds(level, expiry) for level in LEVELS}
            boundary = self.boundary(judged, expiry)
            price = bool(adopted and reference["converged"] and (bounds[adopted] or {}).get("pass"))
            flagged = (self.record("spectral", judged, "base", expiry) or {}).get(
                "diagnostics"
            ) or {}
            if (flagged.get("generator") or {}).get("scheme_nonmonotone"):
                holds = price and boundary["status"] == "pass" and paper["match"]["pass"]
                effect = "confirmed" if holds else "unsupported"
            else:
                effect = "not_recorded"
            finest = _ladders(self.protocol)["x"][-1]
            out["selections"][key] = selection
            out["fd_reference"][key] = reference
            out["bounds"][key] = bounds
            out["boundary"][key] = boundary
            out["independent_validated"][key] = {"price": price, "boundary": boundary["status"]}
            out["nonmonotone_effect"][key] = effect
            out["deltas"][key] = {
                "spectral": {
                    "level": adopted,
                    "values": self.deltas(
                        adopted and self.record("spectral", adopted, "base", expiry)
                    ),
                },
                "fd": {
                    "job_id": _job_id("fd", "independent", finest, expiry),
                    "values": self.deltas(self.record("fd", "independent", finest, expiry)),
                },
            }
            out["costs"][key] = self.costs(expiry, levels, self.reference_arrays(reference))
        exports = sorted(
            {path for b in out["boundary"].values() for path in b.get("arrays", {}).values()}
        )
        return out | {
            "paper_match": paper["match"],
            "paper_diagnostics": paper["diagnostics"],
            "reproduction_label": self.gates.reproduction_label(
                paper["match"], out["independent_validated"]
            ),
            "accounting": _accounting(list(self.by_id.values())),
            "exports": exports,
        }


def _accounting(records: list[dict]) -> dict:
    """Return the job count by status and every job that did not finish ``ok``, with its reason."""
    return {
        "jobs": len(records),
        "status_counts": dict(Counter(r["status"] for r in records)),
        "wall_seconds": sum(r.get("wall_seconds") or 0.0 for r in records),
        "not_ok": [
            {"job_id": r["job_id"], "status": r["status"], "reason": r["reason"]}
            for r in records
            if r["status"] != "ok"
        ],
    }


def evaluate(phase: str, records: list[dict], root: Path, protocol: dict, cases: dict) -> dict:
    """Apply the gates to ``records`` and return the JSON-ready verdicts of ``phase``.

    ``pilot``: the paper match, the T=.5 FD reference, S0 against it, the T=.5 boundary gate, the
    ``crossing_lower`` sensitivity, diagnostics, the cost estimate of every main job, the
    ``protocol_digest`` and ``all_pass``.  ``main``: per expiry the level selection, the FD
    reference, bounds, boundary gate, ``independent_validated``, ``nonmonotone_effect`` and
    Deltas, then the paper match, ``reproduction_label``, the cost tables and ``exports`` (the
    relative paths of the arrays to publish).  ``fixture``: the job count by status and every
    array as an export.  Jobs without a record are unavailable, which makes this usable mid-run.
    """
    if phase == "fixture":
        verdicts = {
            "status_counts": dict(Counter(r["status"] for r in records)),
            "exports": sorted(r["arrays"]["path"] for r in records if r.get("arrays")),
        }
    elif phase in ("pilot", "main"):
        view = _Evaluation(records, root, protocol, cases)
        verdicts = view.pilot_verdicts() if phase == "pilot" else view.main_verdicts()
    else:
        raise ValueError(f"phase must be pilot, main or fixture, got {phase!r}")
    return _jsonable(verdicts)


# ---------------------------------------------------------------------------------------------
# Freeze
# ---------------------------------------------------------------------------------------------


def make_freeze_manifest(protocol: dict, pilot_summary: dict, estimates: list[dict]) -> dict:
    """Freeze the main run: the protocol, the source hashes, the roster with its estimates.

    ValueError unless the pilot passed (``all_pass``) with this protocol (``protocol_digest``),
    the estimates cover exactly the main roster, none is unmeasured, none is above
    ``job_wall_seconds`` and the always-run jobs add up to at most ``main_seconds``.  The manifest
    carries the sha256 of the protocol, the cases and every file of ``SOURCE_FILES``, copies of the
    thresholds and the budget, the roster (each job with ``estimate_seconds``), the estimates with
    their formulas and coefficients, the hash of the pilot summary and its own ``manifest_sha256``.
    """
    if not pilot_summary.get("all_pass"):
        raise ValueError("the pilot did not pass (all_pass is not true): nothing is frozen")
    if pilot_summary.get("protocol_digest") != _digest(protocol):
        raise ValueError("the pilot ran with a different protocol (protocol_digest differs)")
    roster = build_roster(protocol, "main")
    problem = _estimate_problem(roster, estimates, protocol["budget"])
    if problem:
        raise ValueError(problem)
    given = {entry["job_id"]: entry for entry in estimates}
    manifest = {
        "schema": "DSINC-freeze-v1",
        "protocol_sha256": _sha256(HERE / "protocol.json"),
        "cases_sha256": _sha256(HERE / protocol["cases_file"]),
        "source_sha256": {entry: _sha256(REPO / entry) for entry in SOURCE_FILES},
        "thresholds": protocol["thresholds"],
        "budget": protocol["budget"],
        "roster": [job | {"estimate_seconds": given[job["job_id"]]["seconds"]} for job in roster],
        "estimates": [given[job["job_id"]] for job in roster],
        "pilot_summary_sha256": _digest(pilot_summary),
    }
    return manifest | {"manifest_sha256": _digest(manifest)}


def verify_freeze(path: Path) -> dict:
    """Return the freeze manifest at ``path`` after checking it against the current files.

    ValueError (naming the freeze or the source) if the manifest was edited, if the protocol, the
    cases or a source file differs from the frozen hash, if the source list changed, if the
    thresholds or the budget differ from ``protocol.json`` or if the frozen roster is not the one
    the protocol builds.
    """
    manifest = json.loads(Path(path).read_text())
    body = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    if _digest(body) != manifest.get("manifest_sha256"):
        raise ValueError(f"the freeze manifest {path} does not match its manifest_sha256")
    protocol = load_protocol()
    if manifest["protocol_sha256"] != _sha256(HERE / "protocol.json"):
        raise ValueError("freeze mismatch: protocol.json changed after the freeze")
    if manifest["cases_sha256"] != _sha256(HERE / protocol["cases_file"]):
        raise ValueError("freeze mismatch: the cases file changed after the freeze")
    if set(manifest["source_sha256"]) != set(SOURCE_FILES):
        raise ValueError("freeze mismatch: the list of source files differs from SOURCE_FILES")
    for entry, digest in manifest["source_sha256"].items():
        if _sha256(REPO / entry) != digest:
            raise ValueError(f"freeze mismatch: the source file {entry} changed after the freeze")
    if manifest["thresholds"] != protocol["thresholds"] or manifest["budget"] != protocol["budget"]:
        raise ValueError(
            "freeze mismatch: the frozen thresholds or budget differ from protocol.json"
        )
    frozen = [
        {k: v for k, v in job.items() if k != "estimate_seconds"} for job in manifest["roster"]
    ]
    if frozen != build_roster(protocol, "main"):
        raise ValueError(
            "freeze mismatch: the frozen roster is not the roster protocol.json builds"
        )
    return manifest


# ---------------------------------------------------------------------------------------------
# Results, replay and export
# ---------------------------------------------------------------------------------------------


def _compact(record: dict) -> dict:
    """Return ``record`` as results.json stores it: ``raw`` without the entries already lifted.

    ``records.json`` in the run root keeps the launcher's whole return; results.json is published
    and stays under the file-size limit, so the prices, timings and diagnostics are not written
    twice.
    """
    raw = record.get("raw")
    if not isinstance(raw, dict):
        return record
    return record | {"raw": {key: value for key, value in raw.items() if key not in LIFTED}}


def write_results(root: Path, phase: str, records: list[dict], protocol: dict, cases: dict) -> Path:
    """Write ``<root>/results.json`` (records, verdicts, array index, exports) and return its path.

    The freeze hash is taken from ``<root>/freeze_manifest.json`` if the run copied it there.  The
    thresholds the gates used are copied in, so that the figures need nothing but this file.
    """
    root = Path(root)
    verdicts = evaluate(phase, records, root, protocol, cases)
    frozen = root / "freeze_manifest.json"
    results = {
        "schema": "DSINC-results-v1",
        "phase": phase,
        "protocol_sha256": _sha256(HERE / "protocol.json"),
        "freeze_sha256": json.loads(frozen.read_text())["manifest_sha256"]
        if frozen.exists()
        else None,
        "thresholds": protocol["thresholds"],
        "records": [_compact(record) for record in records],
        "verdicts": verdicts,
        "arrays": {r["job_id"]: r["arrays"] for r in records if r.get("arrays")},
        "exports": verdicts["exports"],
    }
    path = root / "results.json"
    write_json(path, results)
    return path


def _differences(path: str, saved, fresh) -> list[str]:
    """List where two JSON values differ, as ``path: saved ..., recomputed ...`` lines."""
    if isinstance(saved, dict) and isinstance(fresh, dict):
        found: list[str] = []
        for key in sorted(set(saved) | set(fresh)):
            if key not in saved or key not in fresh:
                where = "recomputed" if key not in saved else "saved"
                found.append(f"{path}.{key}: only in the {where} verdicts")
            else:
                found += _differences(f"{path}.{key}", saved[key], fresh[key])
        return found
    if isinstance(saved, list) and isinstance(fresh, list) and len(saved) == len(fresh):
        return [
            line
            for i, (a, b) in enumerate(zip(saved, fresh, strict=True))
            for line in _differences(f"{path}[{i}]", a, b)
        ]
    same = json.dumps(saved, sort_keys=True) == json.dumps(fresh, sort_keys=True)
    return [] if same else [f"{path}: saved {saved!r}, recomputed {fresh!r}"]


def replay(results_path: Path) -> dict:
    """Recompute the verdicts of a saved run from its records and arrays and compare.

    Returns ``{match, differences}``: ``match`` is true when the protocol hash and every array
    file agree with the index and the recomputed verdicts equal the saved ones as canonical JSON.
    """
    results_path = Path(results_path)
    saved = json.loads(results_path.read_text())
    root = results_path.parent
    differences = []
    if saved["protocol_sha256"] != _sha256(HERE / "protocol.json"):
        differences.append("protocol_sha256: protocol.json differs from the one used for the run")
    for job_id, array in saved["arrays"].items():
        file = root / array["path"]
        if not file.exists() or _sha256(file) != array["sha256"]:
            differences.append(f"arrays.{job_id}: {array['path']} is missing or changed")
    fresh = evaluate(saved["phase"], saved["records"], root, load_protocol(), load_cases())
    differences += _differences("verdicts", saved["verdicts"], fresh)
    return {"match": not differences, "differences": differences[:50]}


def export(results_path: Path, target: Path, limit_bytes: int) -> dict:
    """Copy results.json and the arrays it exports to ``target`` and write ``manifest.json``.

    Every file is measured first: if any is larger than ``limit_bytes`` the ValueError names the
    limit and nothing is copied.  The exported arrays must match the hashes in the results.  The
    target must be new or empty.  Returns the manifest (file -> sha256 and size).
    """
    results_path = Path(results_path)
    root = results_path.parent
    results = json.loads(results_path.read_text())
    sources = {"results.json": results_path} | {path: root / path for path in results["exports"]}
    sizes = {name: source.stat().st_size for name, source in sources.items()}
    large = {name: size for name, size in sizes.items() if size > limit_bytes}
    if large:
        raise ValueError(f"files over the limit of {limit_bytes} bytes: {large}")
    indexed = {array["path"]: array["sha256"] for array in results["arrays"].values()}
    for name, source in sources.items():
        if name in indexed and _sha256(source) != indexed[name]:
            raise ValueError(f"{name} does not match the hash in the results")
    target = Path(target)
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"the export target {target} exists and is not empty")
    for name, source in sources.items():
        (target / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target / name)
    manifest = {
        "schema": "DSINC-export-v1",
        "files": {
            name: {"sha256": _sha256(target / name), "bytes": sizes[name]} for name in sources
        },
    }
    write_json(target / "manifest.json", manifest)
    return manifest


# ---------------------------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------------------------


def _solve_command(args: argparse.Namespace) -> int:
    """Child process: refuse unless BLAS is single-threaded, then solve one job."""
    unset = [n for n in load_protocol()["budget"]["thread_variables"] if os.environ.get(n) != "1"]
    if unset:
        print(f"solve-job needs these variables set to 1: {', '.join(unset)}", file=sys.stderr)
        return 2
    job = json.loads(Path(args.job).read_text())
    if job.get("phase") in ("pilot", "main"):
        check_job_in_roster(job, build_roster(load_protocol(), job["phase"]))
    out = Path(args.out).resolve()
    write_json(out, _jsonable(solve_job(job, out.parent.parent)))  # <root>/out/<id>.json
    return 0


def _run_phase(
    phase: str, roster: list[dict], output: Path, budget: dict, should_run=None
) -> list[dict]:
    """Execute ``roster`` under ``budget`` into ``output`` and print how it went."""
    target, allowed = Path(output).resolve(), Path(load_protocol()["storage"]["run_root"]).resolve()
    if target.is_relative_to(REPO) and not target.is_relative_to(allowed):
        raise ValueError(f"run roots hold untracked data: {output} is inside the checkout {REPO}")
    started = time.monotonic()
    records = execute_roster(roster, output, budget, should_run=should_run)
    print(f"{phase}: {len(records)} jobs in {time.monotonic() - started:.0f} s")
    print(f"{phase}: status counts {dict(Counter(r['status'] for r in records))}")
    return records


def _report_size(root: Path, protocol: dict) -> None:
    """Print the size of the run root against the storage target."""
    size = sum(f.stat().st_size for f in Path(root).rglob("*") if f.is_file())
    print(
        f"run root {root}: {size / 2**20:.1f} MiB (target {protocol['storage']['target_bytes'] / 2**20:.0f} MiB)"
    )


def _pilot_command(args: argparse.Namespace) -> int:
    """Run the pilot, write results.json and pilot_summary.json, print the verdict."""
    protocol, cases = load_protocol(), load_cases()
    budget = protocol["budget"]
    limits = {
        "job_wall_seconds": budget["job_wall_seconds"],
        "job_rss_bytes": budget["job_rss_bytes"],
        "total_seconds": budget["pilot_seconds"],
    }
    records = _run_phase("pilot", build_roster(protocol, "pilot"), args.output, limits)
    write_results(args.output, "pilot", records, protocol, cases)
    summary = evaluate("pilot", records, args.output, protocol, cases)
    write_json(args.output / "pilot_summary.json", summary)
    failed = [name for name, passed in summary["checks"].items() if not passed]
    print(f"pilot all_pass: {summary['all_pass']}" + (f" (failed: {failed})" if failed else ""))
    _report_size(args.output, protocol)
    return 0


def _freeze_command(args: argparse.Namespace) -> int:
    """Freeze the main run from a passing pilot's summary."""
    summary = json.loads((args.pilot / "pilot_summary.json").read_text())
    manifest = make_freeze_manifest(load_protocol(), summary, summary["estimates"])
    write_json(args.output, manifest)
    print(f"freeze written to {args.output}: manifest_sha256 {manifest['manifest_sha256']}")
    return 0


def _main_command(args: argparse.Namespace) -> int:
    """Verify the freeze, run the frozen main roster and write its results."""
    manifest = verify_freeze(args.freeze)
    protocol, cases = load_protocol(), load_cases()
    budget = manifest["budget"]
    limits = {
        "job_wall_seconds": budget["job_wall_seconds"],
        "job_rss_bytes": budget["job_rss_bytes"],
        "total_seconds": budget["main_seconds"],
    }

    def should_run(job: dict, records: list[dict]) -> bool:
        selections = evaluate("main", records, args.output, protocol, cases)["selections"]
        return condition_met(job["condition"], selections)

    records = _run_phase("main", manifest["roster"], args.output, limits, should_run)
    shutil.copyfile(args.freeze, args.output / "freeze_manifest.json")
    results = write_results(args.output, "main", records, protocol, cases)
    verdicts = json.loads(results.read_text())["verdicts"]
    adopted = {k: v["adopted"] for k, v in verdicts["selections"].items()}
    print(f"main: adopted {adopted}, reproduction_label {verdicts['reproduction_label']}")
    _report_size(args.output, protocol)
    return 0


def _replay_command(args: argparse.Namespace) -> int:
    """Recompute the saved verdicts of a run and print whether they match."""
    outcome = replay(args.results)
    print(json.dumps(outcome))
    return 0 if outcome["match"] else 1


def _export_command(args: argparse.Namespace) -> int:
    """Copy the results and their arrays into the repository (limit from the protocol)."""
    manifest = export(args.results, args.to, load_protocol()["storage"]["export_file_bytes"])
    print(f"exported {len(manifest['files'])} files to {args.to}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: pilot, freeze, main, solve-job, replay or export."""
    parser = argparse.ArgumentParser(prog="run.py", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    arguments = {
        "pilot": [("--output", "new run root")],
        "freeze": [("--pilot", "pilot run root"), ("--output", "freeze manifest to write")],
        "main": [("--freeze", "freeze manifest"), ("--output", "new run root")],
        "solve-job": [("--job", "job file"), ("--out", "output file")],
        "replay": [("--results", "results.json of a run")],
        "export": [("--results", "results.json of a run"), ("--to", "target directory")],
    }
    for name, options in arguments.items():
        subparser = commands.add_parser(name)
        for option, help_text in options:
            subparser.add_argument(option, type=Path, required=True, help=help_text)
    args = parser.parse_args(argv)
    if args.command == "solve-job":  # uncaught errors give a traceback, which the parent records
        return _solve_command(args)
    handlers = {
        "pilot": _pilot_command,
        "freeze": _freeze_command,
        "main": _main_command,
        "replay": _replay_command,
        "export": _export_command,
    }
    try:
        return handlers[args.command](args)
    except ValueError as error:
        print(f"run.py {args.command}: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
