"""Bounded offline DSINC experiments, immutable rosters and evidence replay."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import resource
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
from hullkit._dsinc_types import PricingFailure, PutContract, SpectralConfig, VarianceModel

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
DATA_ROOT = Path("/home/kazumasa/projects/_data/johnhull/DSINC")
THRESHOLDS = {"paper": 6e-6, "price": 2e-5, "refinement": 5e-6, "root": 1e-8, "coverage": 0.9}
BUDGETS = {
    "job_seconds": 180,
    "job_bytes": 2 * 1024**3,
    "pilot_seconds": 600,
    "main_seconds": 1800,
    "output_bytes": 50 * 1024**2,
    "safety_factor": 2,
}
SENSITIVITIES = (
    "time",
    "variance",
    "panel",
    "cutoff",
    "chi_low",
    "chi_high",
    "domain",
    "offset_low",
    "offset_high",
)
THREADS = ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")


def json_safe(value):
    """Encode failures as null while retaining their status and reason."""
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            json_safe(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def file_sha256(path):
    """Hash small source/result bytes without relying on a stored flag."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, value):
    path.write_text(json.dumps(json_safe(value), indent=2, allow_nan=False) + "\n")


def load_cases():
    """Return pinned paper anchors and original case slots."""
    return json.loads((ROOT / "cases.json").read_text())


def source_hashes():
    """Bind every executed solver, runner, plotter and upstream source."""
    for name in ("_dsinc_types", "_dsinc_spectral", "_dsinc_american"):
        module = importlib.import_module("hullkit." + name)
        expected = REPO / "johnhull/hullkit/src/hullkit" / (name + ".py")
        if Path(module.__file__).resolve() != expected.resolve():
            raise ValueError(f"imported source path mismatch: {name}")
    paths = [
        ROOT / name
        for name in (
            "run.py",
            "plot.py",
            "reference_fd.py",
            "heston_baseline.py",
            "cases.json",
            "upstream_manifest.json",
        )
    ]
    paths += [
        ROOT / "upstream" / name
        for name in ("dsinc_pricer.py", "fd_adi_pricer.py", "benchmark.py", "LICENSE")
    ]
    paths += [
        REPO / "johnhull/hullkit/src/hullkit" / name
        for name in ("_dsinc_types.py", "_dsinc_spectral.py", "_dsinc_american.py")
    ]
    return {str(p.relative_to(REPO)): file_sha256(p) for p in paths}


def runtime_fingerprint():
    """Freeze numerical-library versions and the worker's enforced thread policy."""
    import scipy

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "thread_policy": {name: "1" for name in THREADS},
        "float_bytes": 8,
        "complex_bytes": 16,
    }


def _spectral(t, stage=0):
    nv, rate, cutoff, points = ((160, 200, 640, 12), (240, 400, 1280, 12), (320, 800, 2560, 16))[
        stage
    ]
    panels = [0, 2, 5, 10, 20, 40, 80, 160, 320, 640]
    while panels[-1] < cutoff:
        panels.append(panels[-1] * 2)
    return SpectralConfig(
        int(rate * t),
        nv,
        (np.log(0.0002), np.log(2)),
        0.5,
        tuple(panels),
        points,
        root_residual_tol=THRESHOLDS["root"],
    )


def _sensitivity(config, name):
    h = (config.log_var_bounds[1] - config.log_var_bounds[0]) / (config.n_var - 1)
    if name == "time":
        return replace(config, n_time=config.n_time * 2)
    if name == "variance":
        return replace(config, n_var={160: 240, 240: 320}[config.n_var])
    if name == "panel":
        return replace(config, points_per_panel=config.points_per_panel + 4)
    if name == "cutoff":
        return replace(config, panels=(*config.panels, config.panels[-1] * 2))
    if name in ("chi_low", "chi_high"):
        return replace(config, chi=0.25 if name == "chi_low" else 0.75)
    if name == "domain":
        extra = int(np.ceil(np.log(2) / h))
        return replace(
            config,
            n_var=config.n_var + 2 * extra,
            log_var_bounds=(
                config.log_var_bounds[0] - extra * h,
                config.log_var_bounds[1] + extra * h,
            ),
        )
    offset = -0.5 * h if name == "offset_low" else 0.5 * h
    return replace(config, log_var_bounds=tuple(z + offset for z in config.log_var_bounds))


def build_roster(phase):
    """Predeclare jobs; no extra ladder levels or spot-wise stage selection."""
    if phase not in ("pilot", "main"):
        raise ValueError("invalid phase")
    jobs = []
    conditional = []
    if phase == "pilot":
        jobs.append({"id": "heston:first", "method": "heston", "case_index": 0, "settings": {}})
    for case in load_cases()["primary_groups"]:
        t = case["contract"]["expiry"]
        prefix = f"T{t:g}"

        def add(tag, method, settings, *, case=case, prefix=prefix, **extra):
            jobs.append(
                {
                    "id": f"{prefix}:{tag}",
                    "method": method,
                    "case_id": case["id"],
                    "contract": case["contract"],
                    "model": case["model"],
                    "spots": case["spots"],
                    "settings": json_safe(settings),
                    **extra,
                }
            )

        add("S0", "spectral", asdict(_spectral(t)))
        if phase == "main":
            for stage in (1, 2):
                add(f"S{stage}", "spectral", asdict(_spectral(t, stage)))
        candidates = (0, 1) if phase == "main" else ((0,) if t == 0.5 else ())
        for stage in candidates:
            for name in SENSITIVITIES:
                add(f"S{stage}:{name}", "spectral", asdict(_sensitivity(_spectral(t, stage), name)))
            if phase == "main":
                for repeat in range(4):
                    conditional.append(
                        {
                            "id": f"{prefix}:S{stage}:timing{repeat}",
                            "method": "spectral",
                            "case_id": case["id"],
                            "contract": case["contract"],
                            "model": case["model"],
                            "spots": case["spots"],
                            "settings": json_safe(asdict(_spectral(t, stage))),
                            "condition": f"selected:S{stage}",
                            "timing_role": "warmup" if repeat == 0 else "measurement",
                        }
                    )
        if phase == "pilot" and t == 1:
            add(
                "paper:fine:american",
                "fd",
                _fd_settings(481, 201, int(600 * t), "american", paper=True),
            )
            continue
        for style in ("european", "american"):
            # Middle balanced grid is the axis anchor; no simultaneous third level.
            base = _fd_settings(481, 151, int(600 * t), style)
            add(f"ref:{style}:base", "fd", base)
            for axis, levels in (
                ("n_x", (241, 961)),
                ("n_var", (101, 201)),
                ("n_time", (int(300 * t), int(1200 * t))),
            ):
                for count in levels:
                    add(f"ref:{style}:{axis}:{count}", "fd", {**base, axis: count})
            add(f"ref:{style}:domain", "fd", {**base, "n_x": 961, "log_spot_bounds": [-2.4, 2.4]})
            for label, nx, nv, nt in (
                ("coarse", 241, 101, int(300 * t)),
                ("fine", 481, 201, int(600 * t)),
            ):
                add(f"paper:{label}:{style}", "fd", _fd_settings(nx, nv, nt, style, paper=True))
    return jobs + conditional


def _fd_settings(nx, nv, nt, style, *, paper=False):
    return {
        "n_x": nx,
        "n_var": nv,
        "n_time": nt,
        "log_spot_bounds": [-1.2, 1.2],
        "log_var_bounds": [np.log(0.0002 if paper else 1e-5), np.log(2 if paper else 8)],
        "exercise": style,
    }


def original_slots(records, *, reason="no_selected_validated_stage", selected=None):
    """Account for all six original spots, including unavailable paper values."""
    by_id = {r["id"]: r for r in records}
    slots = []
    for case in load_cases()["primary_groups"]:
        t = case["contract"]["expiry"]
        stage = (selected or {}).get(f"T{t:g}", "S0")
        record = by_id.get(f"T{t:g}:{stage}", {})
        for i, spot in enumerate(case["spots"]):
            row = {
                "case_id": f"{case['id']}:S{spot:g}",
                "expiry": t,
                "spot": spot,
                "status": record.get("status", "not_run"),
                "reason": record.get("message", reason),
                "american": record.get("values", {}).get("american", [None] * 3)[i],
                "european": record.get("values", {}).get("european", [None] * 3)[i],
                "paper_american_status": "available"
                if case["paper_anchors"]["american"][i] is not None
                else "not_available",
                "independent_validated": bool(
                    selected and f"T{t:g}" in selected and record.get("status") == "completed"
                ),
            }
            slots.append(row)
    return slots


def paper_gate(records):
    """Require every printed S0 American/European anchor independently."""
    by_id = {r["id"]: r for r in records}
    rows = []
    for case in load_cases()["primary_groups"]:
        record = by_id.get(f"T{case['contract']['expiry']:g}:S0", {})
        for kind in ("american", "european"):
            for i, anchor in enumerate(case["paper_anchors"][kind]):
                value = record.get("values", {}).get(kind, [None] * 3)[i]
                difference = (
                    None
                    if value is None or anchor is None
                    else abs(value / case["contract"]["strike"] - anchor)
                )
                status = (
                    "not_available"
                    if anchor is None
                    else (
                        "pass"
                        if difference is not None and difference <= THRESHOLDS["paper"]
                        else "fail"
                    )
                )
                rows.append(
                    {
                        "case_id": case["id"],
                        "spot": case["spots"][i],
                        "kind": kind,
                        "anchor": anchor,
                        "value": value,
                        "difference_over_K": difference,
                        "status": status,
                    }
                )
    return {"passed": all(r["status"] in ("pass", "not_available") for r in rows), "rows": rows}


def reproduction_status(paper_passed, independent_passed):
    """Only both scientific gates allow a reproduction claim."""
    return "reproduced" if paper_passed and independent_passed else "not_reproduced"


def independent_price_gate(record, european_reference, american_reference):
    """Check both prices, absolute EEP error and financial inequalities in price/K."""
    if record.get("status") != "completed":
        return {"accepted": False, "reason": "solver_failed"}
    contract = record["contract"]
    strike = contract["strike"]
    tol = THRESHOLDS["price"]
    arrays = [
        np.asarray(record["values"][kind], dtype=float) / strike
        for kind in ("european", "american", "eep")
    ]
    if any(a.shape != (3,) or not np.all(np.isfinite(a)) for a in arrays):
        return {"accepted": False, "reason": "nonfinite_or_incomplete"}
    eu, am, eep = arrays
    eu_ref = np.asarray(european_reference) / strike
    am_ref = np.asarray(american_reference) / strike
    spots = np.asarray(record["spots"]) / strike
    lower = np.maximum(
        np.exp(-contract["domestic_rate"] * contract["expiry"])
        - spots * np.exp(-contract["foreign_rate"] * contract["expiry"]),
        0,
    )
    errors = {
        "european": float(np.max(abs(eu - eu_ref))),
        "american": float(np.max(abs(am - am_ref))),
        "eep": float(np.max(abs(eep - (am_ref - eu_ref)))),
    }
    financial = bool(
        np.all(am >= eu - tol)
        and np.all(am >= np.maximum(1 - spots, 0) - tol)
        and np.all(am <= 1 + tol)
        and np.all(eu >= lower - tol)
        and np.all(eu <= np.exp(-contract["domestic_rate"] * contract["expiry"]) + tol)
        and np.max(abs(am - eu - eep)) <= 1e-12
    )
    return {
        "accepted": financial and all(e <= tol for e in errors.values()),
        "financial_bounds": financial,
        "errors_over_K": errors,
    }


def select_stage(stages, sensitivities, reference, *, reference_supported, boundary_accepted):
    """Adopt the first qualifying pair's coarse side, jointly for three spots."""
    reasons = []
    if not reference_supported or not boundary_accepted:
        return {"stage": None, "reasons": ["independent_reference_or_boundary_unsupported"]}
    for stage, next_stage in (("S0", "S1"), ("S1", "S2")):
        base, upper = stages.get(stage), stages.get(next_stage)
        if base is None or upper is None:
            reasons.append(f"{stage}:missing_stage")
            continue
        base, upper = np.asarray(base), np.asarray(upper)
        tests = sensitivities.get(stage, {})
        stable = all(
            name in tests
            and np.all(np.isfinite(tests[name]))
            and np.max(np.abs(np.asarray(tests[name]) - base)) <= THRESHOLDS["refinement"]
            for name in SENSITIVITIES
        )
        if (
            np.all(np.isfinite(base))
            and np.all(np.isfinite(upper))
            and np.max(np.abs(upper - base)) <= THRESHOLDS["refinement"]
            and np.max(np.abs(base - reference)) <= THRESHOLDS["price"]
            and stable
        ):
            return {"stage": stage, "reasons": reasons}
        reasons.append(f"{stage}:accuracy_or_sensitivity_failed")
    return {"stage": None, "reasons": reasons}


def cost_accounting(records):
    """Charge setup, solve and query plus process wall time, including failures."""
    timings = [r.get("timings", {}) for r in records]
    return {
        "solver_seconds": sum(
            sum(t.get(k) or 0 for k in ("setup_seconds", "solve_seconds", "query_seconds"))
            for t in timings
        ),
        "charged_wall_seconds": sum(r.get("wall_seconds", 0) for r in records),
        "query_only_seconds": sum(t.get("query_seconds") or 0 for t in timings),
        "failed_jobs": sum(r.get("status") != "completed" for r in records),
    }


def _refinement(records, t):
    lookup = {r["id"]: r for r in records}
    checks = []
    for style in ("european", "american"):
        stem = f"T{t:g}:ref:{style}:"
        base = lookup.get(stem + "base")
        for axis, levels in (
            ("n_x", (241, 961)),
            ("n_var", (101, 201)),
            ("n_time", (int(300 * t), int(1200 * t))),
        ):
            rows = [
                lookup.get(stem + f"{axis}:{levels[0]}"),
                base,
                lookup.get(stem + f"{axis}:{levels[1]}"),
            ]
            if any(r is None or r["status"] != "completed" for r in rows):
                checks.append(
                    {
                        "style": style,
                        "axis": axis,
                        "supported": False,
                        "reason": "missing_or_failed",
                    }
                )
                continue
            values = [np.array(r["values"][style]) / r["contract"]["strike"] for r in rows]
            differences = [float(np.max(abs(values[j + 1] - values[j]))) for j in (0, 1)]
            checks.append(
                {
                    "style": style,
                    "axis": axis,
                    "changes": differences,
                    "supported": differences[1] <= THRESHOLDS["refinement"]
                    and differences[1] < differences[0],
                }
            )
        expanded = lookup.get(stem + "domain")
        difference = None
        if base and expanded and base["status"] == expanded["status"] == "completed":
            difference = float(
                np.max(abs(np.array(base["values"][style]) - expanded["values"][style]))
                / base["contract"]["strike"]
            )
        checks.append(
            {
                "style": style,
                "axis": "domain",
                "change": difference,
                "supported": difference is not None and difference <= THRESHOLDS["refinement"],
            }
        )
    return {
        "supported": all(c["supported"] for c in checks),
        "checks": checks,
        "interpretation": "axis-wise empirical changes; not rigorous error bounds",
    }


def _cost_prediction(records):
    spectral = [r for r in records if r.get("method") == "spectral" and r["status"] == "completed"]
    fd = [r for r in records if r.get("method") == "fd" and r["status"] == "completed"]
    if not spectral or not fd:
        return {
            "measured": False,
            "jobs": [],
            "total_seconds": None,
            "reason": "coefficients_unmeasured",
        }

    def dimensions(r):
        cfg = r["settings"]
        n = cfg["n_var"]
        nt = cfg["n_time"]
        if r["method"] == "spectral":
            w = (len(cfg["panels"]) - 1) * cfg["points_per_panel"]
            scan = max(65, np.ceil(2 * cfg["panels"][-1] * 0.6 / np.pi) + 1)
            return w * n**3, nt * w * n**2 * scan
        states = (cfg["n_x"] - 2) * n
        band = min(cfg["n_x"] - 2, n)
        return states * band**2, nt * states * band

    coefficients = {}
    for method, rows in (("spectral", spectral), ("fd", fd)):
        coefficients[method] = [
            max((r["timings"][label] or 0) / dimensions(r)[i] for r in rows)
            for i, label in enumerate(("setup_seconds", "solve_seconds"))
        ]
    predictions = []
    for job in build_roster("main"):
        setup, solve = dimensions(job)
        c = coefficients[job["method"]]
        seconds = 2 * (setup * c[0] + solve * c[1] + 0.75)
        predictions.append({"id": job["id"], "seconds": seconds})
    return {
        "measured": True,
        "coefficients": coefficients,
        "jobs": predictions,
        "total_seconds": sum(r["seconds"] for r in predictions),
        "formulas": "spectral setup=Nw*Nv^3; solve=Nt*Nw*Nv^2*scan; FD LU=states*band^2, step=Nt*states*band; 2x safety",
    }


def preflight(records):
    """Recompute pilot eligibility; numerical failures cannot disappear in means."""
    lookup = {r["id"]: r for r in records}
    reasons = []
    paper = paper_gate(records)
    reference = _refinement(records, 0.5)
    cost = _cost_prediction(records)
    if not paper["passed"]:
        reasons.append("paper_mismatch_or_missing")
    if not reference["supported"]:
        reasons.append("reference_not_converged")
    if not lookup.get("T0.5:S0", {}).get("boundary_comparison", {}).get("accepted", False):
        reasons.append("boundary_not_validated")
    failures = [r["id"] for r in records if r["status"] != "completed"]
    if failures:
        reasons.append("solver_failures")
    if not cost["measured"]:
        reasons.append("coefficients_unmeasured")
    elif cost["total_seconds"] > BUDGETS["main_seconds"] or any(
        j["seconds"] > BUDGETS["job_seconds"] for j in cost["jobs"]
    ):
        reasons.append("predicted_budget_exceeded")
    expected = {j["id"] for j in build_roster("pilot")}
    if expected != set(lookup):
        reasons.append("pilot_roster_incomplete")
    return {
        "eligible": not reasons,
        "reasons": reasons,
        "failed_job_ids": failures,
        "reference": reference,
        "cost_prediction": cost,
    }


def verify_artifacts(output, artifacts):
    """Reject altered or escaped artifact paths before replay."""
    output = Path(output).resolve()
    for name, digest in artifacts.items():
        path = (output / name).resolve()
        if not path.is_relative_to(output) or not path.is_file() or file_sha256(path) != digest:
            raise ValueError(f"artifact hash mismatch: {name}")
    return True


def replay(output):
    """Recompute stored gates from small prices/boundaries, with source checks."""
    output = Path(output)
    report = json.loads((output / "results.json").read_text())
    if report["sources"] != source_hashes():
        raise ValueError("source hash mismatch")
    verify_artifacts(output, report["artifacts"])
    for record in report["records"]:
        name = report.get("record_files", {}).get(record["id"])
        if name and json.loads((output / name).read_text()) != record:
            raise ValueError("result record replay mismatch")
    reconstructed = json.loads(json.dumps(report["records"]))
    _attach_boundary_checks(reconstructed, output)
    if reconstructed != report["records"]:
        raise ValueError("boundary replay mismatch")
    if report["phase"] == "main":
        roster = validate_freeze(json.loads((output / "freeze_manifest.json").read_text()))
    else:
        roster = build_roster("pilot")
    verify_record_roster(report["records"], roster)
    derived = _derived_report(report["records"], report["phase"], report.get("elapsed_seconds", 0))
    for key, value in derived.items():
        if report.get(key) != json_safe(value):
            raise ValueError(f"{key} replay mismatch")
    return report


def verify_record_roster(records, roster):
    """Reject missing, duplicated or mutated jobs even if result flags were edited."""
    expected = {j["id"]: j for j in roster}
    if len(records) != len(roster) or len({r["id"] for r in records}) != len(records):
        raise ValueError("record roster count mismatch")
    for record in records:
        job = expected.get(record["id"])
        if (
            job is None
            or any(record.get(k) != v for k, v in job.items())
            or record.get("input_sha256") != _digest(job)
        ):
            raise ValueError("record roster settings/hash mismatch")
    return True


def make_freeze(pilot, output):
    """Record an eligible or explicitly ineligible frozen continuation contract."""
    path = Path(output) / "results.json"
    frozen = {
        "schema": 1,
        "eligible": pilot["preflight"]["eligible"],
        "pilot_path": str(Path(output).resolve()),
        "pilot_sha256": file_sha256(path) if path.exists() else None,
        "sources": source_hashes(),
        "runtime": runtime_fingerprint(),
        "thresholds": THRESHOLDS,
        "budgets": BUDGETS,
        "roster": build_roster("main"),
        "selection": "first qualifying adjacent pair, coarse side, three spots jointly",
        "preflight": pilot["preflight"],
    }
    frozen["digest"] = _digest(frozen)
    return frozen


def validate_freeze(frozen):
    """Require unchanged evidence, jobs and thresholds before any main subprocess."""
    if not frozen:
        raise ValueError("main requires a freeze manifest")
    if frozen.get("digest") != _digest({k: v for k, v in frozen.items() if k != "digest"}):
        raise ValueError("freeze hash mismatch")
    if not frozen["eligible"]:
        raise ValueError("pilot freeze is ineligible; main refused")
    if (
        frozen["sources"] != source_hashes()
        or frozen.get("runtime") != runtime_fingerprint()
        or frozen["thresholds"] != THRESHOLDS
        or frozen["budgets"] != BUDGETS
        or frozen["roster"] != build_roster("main")
    ):
        raise ValueError("freeze source/roster/policy mismatch")
    path = Path(frozen["pilot_path"])
    if file_sha256(path / "results.json") != frozen["pilot_sha256"]:
        raise ValueError("pilot hash mismatch")
    if not replay(path)["preflight"]["eligible"]:
        raise ValueError("replayed pilot is ineligible")
    return frozen["roster"]


def _slug(identifier):
    return identifier.replace(":", "_")


def run_bounded(command, output, identifier, *, wall_limit=180, memory_limit=2 * 1024**3):
    """Run one solver process with external wall/RSS enforcement, including setup."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    stem = _slug(identifier)
    result_path = output / (stem + ".worker.json")
    started = time.monotonic()
    peak = 0
    reason = None
    env = os.environ.copy()
    env.update({name: "1" for name in THREADS})
    with (
        (output / (stem + ".stdout")).open("w") as stdout,
        (output / (stem + ".stderr")).open("w") as stderr,
    ):
        process = subprocess.Popen(command, cwd=REPO, env=env, stdout=stdout, stderr=stderr)
        while process.poll() is None:
            try:
                for line in Path(f"/proc/{process.pid}/status").read_text().splitlines():
                    if line.startswith("VmRSS:"):
                        peak = max(peak, int(line.split()[1]) * 1024)
            except FileNotFoundError:
                pass
            if time.monotonic() - started >= wall_limit:
                reason = "time_budget_exceeded"
            elif peak > memory_limit:
                reason = "memory_budget_exceeded"
            if reason:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                break
            time.sleep(0.02)
    record = {
        "id": identifier,
        "status": reason or "worker_error",
        "values": {"american": [None] * 3, "european": [None] * 3, "eep": [None] * 3},
    }
    if not reason and process.returncode == 0 and result_path.is_file():
        record = json.loads(result_path.read_text())
        if record.get("id") != identifier:
            raise ValueError("worker identity mismatch")
    elif not reason:
        record["message"] = (output / (stem + ".stderr")).read_text()[-2000:]
    elapsed = time.monotonic() - started
    measured_peak = max(peak, record.get("peak_rss_bytes", 0))
    final_reason = reason or (
        "memory_budget_exceeded"
        if measured_peak > memory_limit
        else "time_budget_exceeded"
        if elapsed > wall_limit
        else None
    )
    if final_reason:
        record.update(
            underlying_status=record["status"],
            status=final_reason,
            raw_values=record.get("values"),
            values={"american": [None] * 3, "european": [None] * 3, "eep": [None] * 3},
        )
    record.update(
        wall_seconds=elapsed,
        peak_rss_bytes=measured_peak,
        returncode=process.returncode,
        wall_limit_seconds=wall_limit,
        memory_limit_bytes=memory_limit,
    )
    return record


def _research_module(name):
    spec = importlib.util.spec_from_file_location("_dsinc_research_" + name, ROOT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _queries(spots, strike):
    arrays = [np.asarray(spots)]
    for bump in (1e-3, 5e-4, 2.5e-4):
        arrays.extend((np.asarray(spots) + strike * bump, np.asarray(spots) - strike * bump))
    return np.concatenate(arrays)


def _encode_statuses(statuses, n):
    values = np.asarray(statuses)
    if (
        values.ndim != 2
        or not 0 <= n < len(values) - 1
        or not np.all(values[:n] == "not_run")
        or not np.all(values[n + 1 : -1] == "ok")
        or not np.all(values[-1] == "maturity_limit")
    ):
        raise ValueError("status array cannot be encoded losslessly")
    result = {
        "index_convention": "half_open",
        "shape": list(values.shape),
        "earlier_rows": {"start": 0, "stop": n, "value": "not_run"},
        "failed_row": {"index": n, "values": values[n].tolist()},
        "later_rows": {"start": n + 1, "stop": len(values) - 1, "value": "ok"},
        "terminal_row": {"index": len(values) - 1, "values": values[-1].tolist()},
    }
    if _decode_statuses(result) != values.tolist():
        raise ValueError("status encoding mismatch")
    return result


def _decode_statuses(encoded):
    if encoded["index_convention"] != "half_open":
        raise ValueError("unknown status indexing")
    values = np.full(encoded["shape"], "", dtype="U32")
    for name in ("earlier_rows", "later_rows"):
        row = encoded[name]
        values[row["start"] : row["stop"]] = row["value"]
    for name in ("failed_row", "terminal_row"):
        row = encoded[name]
        values[row["index"]] = row["values"]
    return values.tolist()


def _deltas(values, strike):
    return {
        str(bump): (
            (values[3 + 6 * i : 6 + 6 * i] - values[6 + 6 * i : 9 + 6 * i]) / (2 * bump * strike)
        ).tolist()
        for i, bump in enumerate((1e-3, 5e-4, 2.5e-4))
    }


def _worker(request_path):
    import scipy
    from hullkit._dsinc_american import (
        _advance_history,
        _boundary_residual,
        payoff_transform,
        prepare_american,
    )
    from hullkit._dsinc_spectral import _apply, build_propagators, european_put

    request_path = Path(request_path)
    request = json.loads(request_path.read_text())
    job = request["job"]
    output = request_path.parent
    stem = _slug(job["id"])
    start = time.perf_counter()
    if request["sources"] != source_hashes():
        raise ValueError("worker source hash mismatch")
    if any(os.environ.get(name) != "1" for name in THREADS):
        raise ValueError("worker thread policy mismatch")
    record = {
        **job,
        "status": "completed",
        "input_sha256": _digest(job),
        "values": {"european": [None] * 3, "american": [None] * 3, "eep": [None] * 3},
        "timings": {"setup_seconds": 0.0, "solve_seconds": 0.0, "query_seconds": None},
        "artifacts": {},
    }
    arrays = {}
    prop = None
    if job["method"] == "heston":
        baseline = _research_module("heston_baseline")
        case = load_cases()["heston_baselines"][0]
        record["observation"] = baseline.run_heston_baseline(
            PutContract(**case["contract"]),
            VarianceModel(**case["model"]),
            np.array(case["spots"]),
            dsinc_settings={},
            fd_settings={},
        )
        record["accepted"] = False
    else:
        contract = PutContract(**job["contract"])
        model = VarianceModel(**job["model"])
        spots = _queries(job["spots"], contract.strike)
        try:
            if job["method"] == "spectral":
                config = SpectralConfig(**job["settings"])
                prop = build_propagators(contract, model, config)
                prepared = prepare_american(contract, model, config, propagators=prop)
                result = prepared.price(spots)
                record["values"] = {
                    name: getattr(result, name)[:3].tolist() for name in ("european", "american")
                }
                record["values"]["eep"] = result.early_exercise_premium[:3].tolist()
                record["deltas"] = {
                    "american": _deltas(result.american, contract.strike),
                    "european": _deltas(result.european, contract.strike),
                }
                record["diagnostics"] = result.diagnostics
                warm = prepared.price(np.asarray(job["spots"]))
                record["timings"] = {
                    key: result.diagnostics[key] for key in ("setup_seconds", "solve_seconds")
                }
                record["timings"]["setup_seconds"] += prop.setup_seconds
                record["timings"]["query_seconds"] = warm.diagnostics["query_seconds"]
                arrays = {
                    "times": result.times,
                    "log_variances": result.log_variances,
                    "log_boundary": result.log_boundary,
                }
            else:
                fd = _research_module("reference_fd")
                config = fd.FDConfig(**job["settings"])
                result = fd.reference_put(contract, model, spots, config)
                record["values"][config.exercise] = result.prices[:3].tolist()
                record["deltas"] = {config.exercise: _deltas(result.prices, contract.strike)}
                record["diagnostics"] = result.diagnostics
                record["timings"] = {
                    key: result.diagnostics[key]
                    for key in ("setup_seconds", "solve_seconds", "query_seconds")
                }
                arrays = {
                    "prices": result.prices,
                    "times": result.times,
                    "x": result.x,
                    "log_variances": result.log_variances,
                    "boundary_brackets": result.boundary_brackets,
                    "boundary_valid": result.boundary_valid,
                }
        except PricingFailure as error:
            details = dict(error.details)
            full_status = details.pop("statuses", None)
            if full_status is not None:
                n = details["time_index"]
                details["status_array_encoding"] = _encode_statuses(full_status, n)
            record.update(status=error.code, message=str(error), failure=details)
            if prop is not None:
                record["timings"]["setup_seconds"] = prop.setup_seconds + details.get(
                    "setup_seconds", 0
                )
                record["timings"]["solve_seconds"] = details.get("solve_seconds", 0)
                # Independently report EU even when no American price exists.
                eu = european_put(contract, model, spots, config, propagators=prop)
                record["values"]["european"] = eu[:3].tolist()
                record["deltas"] = {"european": _deltas(eu, contract.strike)}
                if details.get("time_index") == config.n_time - 1:
                    g = _apply(prop, np.ones((len(prop.omega), config.n_var), dtype=complex))
                    q, d = _advance_history(
                        prop,
                        np.zeros_like(g),
                        0.0,
                        payoff_transform(prop.omega, config.chi, np.zeros(config.n_var), contract),
                        prop.dt / 2,
                        contract.domestic_rate,
                    )
                    residual = _boundary_residual(contract, prop, config, g, q, d, tau=prop.dt)
                    indices = sorted({0, config.n_var // 2, config.n_var - 1})
                    scan = np.linspace(-0.1, 0, 257)
                    arrays = {
                        "log_variances": prop.log_variances,
                        "x_scan": scan,
                        "node_indices": np.array(indices),
                        "residual_scan": np.array([residual(scan, i) for i in indices]),
                    }
    if arrays:
        artifact = output / (stem + ".npz")
        np.savez_compressed(artifact, **arrays)
        record["artifacts"][artifact.name] = file_sha256(artifact)
    record.update(
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        solver_elapsed_seconds=time.perf_counter() - start,
        versions={
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
    )
    _write(output / (stem + ".worker.json"), record)


def _attach_boundary_checks(records, output):
    fd = _research_module("reference_fd")
    lookup = {r["id"]: r for r in records}
    for case in load_cases()["primary_groups"]:
        prefix = f"T{case['contract']['expiry']:g}"
        ref_record = lookup.get(prefix + ":ref:american:base")
        if not ref_record or ref_record["status"] != "completed":
            continue
        config = fd.FDConfig(**ref_record["settings"])
        with np.load(output / (_slug(ref_record["id"]) + ".npz"), allow_pickle=False) as values:
            ref = fd.FDResult(
                values["prices"],
                values["x"],
                values["log_variances"],
                values["times"],
                values["boundary_brackets"],
                values["boundary_valid"],
                ref_record["diagnostics"],
                config,
                PutContract(**case["contract"]),
                ref_record["input_sha256"],
            )
        for record in records:
            if (
                record.get("method") != "spectral"
                or not record["id"].startswith(prefix + ":")
                or record["status"] != "completed"
            ):
                continue
            with np.load(output / (_slug(record["id"]) + ".npz"), allow_pickle=False) as values:
                record["boundary_comparison"] = json_safe(
                    fd.boundary_comparison(
                        values["times"],
                        values["log_variances"],
                        values["log_boundary"],
                        ref,
                        coverage_threshold=THRESHOLDS["coverage"],
                    )
                )


def _main_selection(records):
    lookup = {r["id"]: r for r in records}
    decisions = {}
    for case in load_cases()["primary_groups"]:
        t = case["contract"]["expiry"]
        prefix = f"T{t:g}"
        stages = {}
        sensitivities = {}
        for stage in ("S0", "S1", "S2"):
            record = lookup.get(prefix + ":" + stage, {})
            if record.get("status") == "completed":
                stages[stage] = _price_stack(record)
            sensitivities[stage] = {
                name: _price_stack(lookup[prefix + ":" + stage + ":" + name])
                for name in SENSITIVITIES
                if lookup.get(prefix + ":" + stage + ":" + name, {}).get("status") == "completed"
            }
        reference = lookup.get(prefix + ":ref:american:base", {})
        decision = {"stage": None, "reasons": ["missing_reference"]}
        if reference.get("status") == "completed":
            # Each candidate's own boundary comparison is required.
            for candidate in ("S0", "S1"):
                # Keep adjacent upper side; suppress S0 when testing S1.
                if candidate == "S0":
                    candidate_stages = stages
                else:
                    candidate_stages = {k: v for k, v in stages.items() if k != "S0"}
                trial = select_stage(
                    candidate_stages,
                    sensitivities,
                    _reference_stack(lookup, prefix, case["contract"]["strike"]),
                    reference_supported=_refinement(records, t)["supported"],
                    boundary_accepted=lookup.get(prefix + ":" + candidate, {})
                    .get("boundary_comparison", {})
                    .get("accepted", False),
                )
                if trial["stage"] == candidate:
                    european_reference = lookup.get(prefix + ":ref:european:base", {})
                    if european_reference.get("status") == "completed":
                        price_gate = independent_price_gate(
                            lookup[prefix + ":" + candidate],
                            european_reference["values"]["european"],
                            reference["values"]["american"],
                        )
                        if price_gate["accepted"]:
                            decision = {**trial, "price_gate": price_gate}
                            break
        decisions[prefix] = decision
    return decisions


def _price_stack(record):
    return (
        np.array([record["values"][kind] for kind in ("european", "american", "eep")], dtype=float)
        / record["contract"]["strike"]
    )


def _reference_stack(lookup, prefix, strike):
    eu = np.array(
        lookup.get(prefix + ":ref:european:base", {})
        .get("values", {})
        .get("european", [np.nan] * 3),
        dtype=float,
    )
    am = np.array(
        lookup.get(prefix + ":ref:american:base", {})
        .get("values", {})
        .get("american", [np.nan] * 3),
        dtype=float,
    )
    return np.array([eu, am, am - eu]) / strike


def _derived_report(records, phase, elapsed):
    paper = paper_gate(records)
    derived = {
        "paper_match": paper,
        "costs": cost_accounting(records),
        "slots": original_slots(records),
        "main_slots": original_slots([], reason="main_not_run_in_pilot"),
        "reproduction_status": "not_reproduced",
    }
    if phase == "pilot":
        derived["preflight"] = preflight(records)
    elif phase == "main":
        selection = _main_selection(records)
        selected = {k: v["stage"] for k, v in selection.items() if v["stage"]}
        derived["selection"] = selection
        derived["slots"] = original_slots(records, selected=selected)
        derived["main_slots"] = derived["slots"]
        all_jobs = all(
            r["status"] == "completed"
            or (r.get("condition") and r.get("message") == "unselected_conditional_timing")
            for r in records
        )
        within_budget = (
            max(elapsed, derived["costs"]["charged_wall_seconds"]) <= BUDGETS["main_seconds"]
        )
        derived["reproduction_status"] = reproduction_status(
            paper["passed"], len(selected) == 2 and all_jobs and within_budget
        )
    else:
        raise ValueError("unknown replay phase")
    return derived


def run_phase(phase, output, *, manifest=None):
    """Execute a declared pilot or an eligible frozen main; never expand on failure."""
    output = Path(output).resolve()
    if not output.is_relative_to(DATA_ROOT.resolve()):
        raise ValueError(f"output must be under {DATA_ROOT}")
    roster = build_roster("pilot") if phase == "pilot" else validate_freeze(manifest)
    if output.exists() and any(output.iterdir()):
        raise ValueError("output must be a new empty run directory")
    output.mkdir(parents=True, exist_ok=True)
    sources = source_hashes()
    records = []
    started = time.monotonic()
    limit = BUDGETS[phase + "_seconds"]
    stop_reason = None
    if phase == "main":
        _write(output / "freeze_manifest.json", manifest)
    for job in roster:
        elapsed = time.monotonic() - started
        reason = stop_reason or ("phase_budget_exceeded" if elapsed >= limit else None)
        if "condition" in job and not reason:
            _attach_boundary_checks(records, output)
            decision = _main_selection(records).get(f"T{job['contract']['expiry']:g}", {})
            if job["condition"] != "selected:" + str(decision.get("stage")):
                reason = "unselected_conditional_timing"
        if reason:
            record = {
                **job,
                "status": "not_run",
                "message": reason,
                "values": {"american": [None] * 3, "european": [None] * 3, "eep": [None] * 3},
                "wall_seconds": 0,
            }
        else:
            request_path = output / (_slug(job["id"]) + ".job.json")
            _write(request_path, {"job": job, "sources": sources})
            record = run_bounded(
                [sys.executable, "-B", str(ROOT / "run.py"), "--worker", str(request_path)],
                output,
                job["id"],
                wall_limit=min(BUDGETS["job_seconds"], max(0.01, limit - elapsed)),
                memory_limit=BUDGETS["job_bytes"],
            )
            record = {**job, **record}
        records.append(record)
        record.setdefault("input_sha256", _digest(job))
        if not stop_reason:
            stored_bytes = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
            if stored_bytes > BUDGETS["output_bytes"]:
                stop_reason = "output_budget_exceeded"
                record.update(
                    status=stop_reason,
                    message="small-artifact budget exceeded",
                    stored_bytes=stored_bytes,
                    raw_values=record.get("values"),
                    values={"american": [None] * 3, "european": [None] * 3, "eep": [None] * 3},
                )
        print(
            json.dumps(
                {
                    "id": job["id"],
                    "status": record["status"],
                    "wall_seconds": record.get("wall_seconds", 0),
                }
            ),
            flush=True,
        )
    _attach_boundary_checks(records, output)
    for record in records:
        _write(output / (_slug(record["id"]) + ".record.json"), record)
    report = {
        "schema": 1,
        "phase": phase,
        "sources": sources,
        "records": records,
        "paper_match": paper_gate(records),
        "slots": original_slots(records),
        "main_slots": original_slots([], reason="pilot_ineligible"),
        "costs": cost_accounting(records),
        "elapsed_seconds": time.monotonic() - started,
        "artifacts": {
            p.name: file_sha256(p) for p in output.iterdir() if p.suffix in (".npz", ".json")
        },
        "record_files": {r["id"]: _slug(r["id"]) + ".record.json" for r in records},
    }
    report.update(_derived_report(records, phase, report["elapsed_seconds"]))
    report["stored_bytes_before_results"] = sum(
        p.stat().st_size for p in output.iterdir() if p.is_file()
    )
    _write(output / "results.json", report)
    if phase == "pilot":
        frozen = make_freeze(report, output)
        _write(output / "freeze_manifest.json", frozen)
    return report


def main():
    """Offline CLI; main requires an explicit eligible pilot manifest."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("pilot", "main"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.worker:
        _worker(args.worker)
        return
    if args.replay:
        report = replay(args.replay)
        print(json.dumps({"replay": "pass", "status": report.get("reproduction_status")}))
        return
    if args.phase is None or args.output is None:
        parser.error("--phase and --output are required")
    manifest = json.loads(args.manifest.read_text()) if args.manifest else None
    report = run_phase(args.phase, args.output, manifest=manifest)
    print(json.dumps({"status": report["reproduction_status"], "costs": report["costs"]}))


if __name__ == "__main__":
    main()
