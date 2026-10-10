"""Reserved, pretest-fixed independent fresh-reference producer.

Actual independent math runs only after immutable source/plan/artifact bindings
are checked. Raw samples, failed original paths, precision unknowns and costs
are saved. This producer grants neither execution readiness nor financial
qualification; the saved checker verifies numerical semantics and artifact bytes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter, process_time

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if __name__ == "__main__":
    sys.path[:0] = [str(ROOT / "johnhull/hullkit/src"), str(ROOT / "deep_hedge_price/src")]


def _canonical_digest(value):
    import hashlib

    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _production_teacher_replay(
    parameters, surface, row, *, wall_cap_seconds=None, deadline_wall=None
):
    """Replay actual selected production paths with full-N failed/cap closure."""
    from hullkit._dynamic_hedging_conditional import primitive_labels
    from hullkit._heston_local_surface import HestonParameters
    from reference_methods import (
        _cap_receipt,
        _deadline,
        _expired,
        _normal_digest,
        _parameters,
        _sample_summary,
        _timing,
    )
    from run_pilot import _merge_primitives
    from run_reference import payload_digest, teacher_restart

    started, cpu_started = perf_counter(), process_time()
    deadline = _deadline(wall_cap_seconds, started, deadline_wall=deadline_wall)
    original = row["original_teacher"]
    old, n = original["primitives"], row["original_n"]
    if (
        old["original_path_count"] != n
        or old["memory_count"] != row["memory_count"]
        or old["model"] != row["model"]
        or old["spot"] != row["spot"]
        or not np.isclose(old["calendar_times"][0], row["date"], atol=1e-12, rtol=0)
        or original["labels"]["N"] != n
    ):
        raise ValueError("original teacher anchor differs from fixed restart inputs/N")
    level = 768
    times = np.arange(level + 1) / level
    start_step = round(row["date"] * level)
    if old["calendar_times"].shape != times[start_step:].shape or not np.allclose(
        old["calendar_times"], times[start_step:], atol=1e-12, rtol=0
    ):
        raise ValueError("fresh teacher preserves original 768 calendar")
    chunk = row["chunk_paths"]
    if chunk % 16 or chunk < 16 or chunk * level * 2 * 8 * 3 + 16 * 1024**2 > 256 * 1024**2:
        raise ValueError("teacher replay requires bounded chunks divisible by 16")
    params = HestonParameters(**_parameters(parameters))
    chunks, expenses = [], []
    keys = ["b", "c", "mu", "sigma", "aux_logG_prefix", "aux_last_loading"]
    fresh = np.full((n, len(keys)), np.nan)
    statuses = np.full(n, "unmeasured_cap", dtype="U96")
    first_failure = np.full(n, np.nan)
    executed = 0
    for index, first in enumerate(range(0, n, chunk)):
        if _expired(deadline):
            break
        last = min(first + chunk, n)
        wall, cpu = perf_counter(), process_time()
        child = int(np.random.SeedSequence([row["seed"], 7291, index]).generate_state(1)[0])
        normals = np.random.default_rng(child).standard_normal((last - first, level, 2))
        driver = {
            "reserved_parent_seed": row["seed"],
            "child_seed": child,
            "mapping": "SeedSequence[parent_seed,7291,chunk_index]; full-calendar path-major",
            "path_range": [first, last],
            "global_steps": level,
            "start_step": start_step,
            "fine_normal_sha256": _normal_digest(normals),
        }
        raw = teacher_restart(
            row["model"],
            params,
            surface,
            normals,
            times,
            start_index=start_step,
            spot=row["spot"],
            state=old["state"],
            thresholds=original["thresholds"],
        )
        primitive = raw["primitives"]
        chunks.append({"path_range": [first, last], "driver": driver, "replay": raw})
        fresh[first:last] = np.column_stack(
            [np.broadcast_to(primitive[k], (last - first,)) for k in keys]
        )
        mask = primitive["path_mask"]
        statuses[first:last] = np.where(mask, "supported", primitive["failure_reasons"])
        codes = np.asarray(primitive["local_step_status"])
        labels = np.asarray(primitive["local_step_status_labels"]).astype(str)
        for path in np.flatnonzero(~mask):
            executed_steps = np.flatnonzero(codes[path] != 0)
            if len(executed_steps):
                unsupported = np.flatnonzero(np.char.startswith(labels[codes[path]], "unsupported"))
                j = int(unsupported[0] if len(unsupported) else executed_steps[-1])
                at = start_step + j
                first_failure[first + path] = (
                    (times[at] + times[at + 1]) / 2 if len(unsupported) else times[at + 1]
                )
        expenses.append(
            {
                "job_id": f"fresh-production-teacher-{row['id']}-{first}",
                "scope": "production_teacher_replay",
                "original_path_count": n,
                "processed_path_count": last - first,
                "path_steps": (last - first) * (level - start_step),
                "driver_path_steps": (last - first) * level,
                **_timing(wall, cpu, deadline),
            }
        )
        executed = last
    expected = np.column_stack([np.broadcast_to(old[k], (n,)) for k in keys])
    a, b = _sample_summary(fresh), _sample_summary(expected)
    combined = np.sqrt(a["standard_errors"] ** 2 + b["standard_errors"] ** 2)
    merged = global_labels = None
    if executed == n:
        parts = [c["replay"]["primitives"] for c in chunks]
        merged_id = payload_digest([c["replay"]["primitives"]["shared_driver_id"] for c in chunks])
        merged = _merge_primitives(parts, n, merged_id)
        global_labels = primitive_labels(merged, original["thresholds"], blocks=16)
    return {
        "schema": "rb-f04-production-teacher-fresh-v1",
        "chunks": chunks,
        "original_path_count": n,
        "original_record_identity": row["original_record_identity"],
        "original_teacher": original,
        "primitive_keys": keys,
        "primitive_samples": fresh,
        "path_indices": np.arange(n),
        "path_status": statuses,
        "first_failure_date": first_failure,
        "executed_path_count": executed,
        "unexecuted_path_count": n - executed,
        "global_primitives": merged,
        "global_labels": global_labels,
        "aggregate_driver_identity_kind": "ordered_chunk_fingerprints_not_full_normal_cube_sha",
        "comparison": {
            "method": "independent_reserved_stream_all_original_paths",
            "fresh_mean": a["mean"],
            "original_mean": b["mean"],
            "difference": a["mean"] - b["mean"],
            "combined_standard_errors": combined,
            "fresh_statistical_status": a["statistical_status"],
            "original_statistical_status": b["statistical_status"],
            "financial_qualification": "unknown",
        },
        "cap_evidence": _cap_receipt(
            wall_cap_seconds,
            started,
            np.where(statuses == "unmeasured_cap", 0, 1),
            ["unmeasured_cap", "executed"],
            deadline_wall=deadline,
        ),
        "expenses": expenses,
        "cost": _timing(started, cpu_started, deadline),
    }


def _surface_descriptor(surface):
    from reference_methods import _field_binding

    return _field_binding(surface)[0]


def _validate_inputs(
    *, plan, frozen, candidate, source, original_artifact_identity, parameters, surface
):
    """Pure pretest provenance/input guard, shared by saved-only verification."""
    from reference_methods import _parameters
    from run_reference import execution_source_identity, payload_digest

    from deep_hedge_price import _dynamic_hedging_execution as execution

    if plan.get("schema") != "rb-f04-fresh-plan-v1" or not plan.get("cases"):
        raise ValueError("a nonempty pretest fixed fresh plan is required")
    if candidate != execution.execution_candidate():
        raise ValueError("fresh requires the exact original execution candidate")
    if frozen.get("candidate") != candidate or frozen.get("source") != source:
        raise ValueError("fresh candidate/source differs from the frozen identity")
    if frozen.get("frozen_sha256") != _canonical_digest(
        {k: v for k, v in frozen.items() if k != "frozen_sha256"}
    ):
        raise ValueError("fresh execution freeze identity is stale")
    if (
        execution.freeze_execution(
            candidate,
            source,
            frozen["pilot"],
            frozen["review"],
            frozen["selection"],
            frozen["domains"],
        )
        != frozen
    ):
        raise ValueError("fresh execution freeze failed its unchanged guard")
    if execution_source_identity(ROOT)["protocol_source"] != source:
        raise ValueError("fresh source bytes differ from the exact bound closure")
    if frozen.get("selection", {}).get("fresh_plan_sha256") != payload_digest(plan):
        raise ValueError("fresh roster must be fixed in selection before test")
    if (
        not original_artifact_identity
        or plan.get("original_artifact_identity") != original_artifact_identity
        or plan.get("source_sha256") != _canonical_digest(source)
    ):
        raise ValueError("fresh plan/artifact/source binding is incomplete")
    if plan.get("surface_sha256") != payload_digest(_surface_descriptor(surface)):
        raise ValueError("fresh surface bytes differ from the pretest bound field")
    original = candidate["original_candidate"]
    market = original["market"]
    p = market["heston"]
    expected_parameters = dict(
        spot=market["spot"],
        rate=market["rate"],
        dividend_yield=market["dividend_yield"],
        v0=p["v0"],
        kappa=p["kappa"],
        theta=p["mean_variance"],
        xi=p["xi"],
        rho=p["rho"],
    )
    if _parameters(parameters) != expected_parameters:
        raise ValueError("fresh parameters differ from the original market")
    if surface is not None:
        from hullkit._heston_local_surface import LocalVarianceGrid

        if (
            type(surface) is not LocalVarianceGrid
            or _parameters(surface.parameters) != expected_parameters
        ):
            raise ValueError("fresh field evaluator type/parameters differ from the fixed market")

    seeds = original["seeds"]["fresh"]
    cases = plan["cases"]
    ids = [row["id"] for row in cases]
    if len(set(ids)) != len(ids) or ids != plan.get("required_case_ids"):
        raise ValueError("fresh cases differ from the fixed selected restart roster")
    phase_cap = plan.get("wall_cap_seconds")
    if not isinstance(phase_cap, (int, float)) or not np.isfinite(phase_cap) or phase_cap <= 0:
        raise ValueError("fresh requires an explicit positive pretest phase wall cap")
    for row in cases:
        caps = row.get("wall_caps", {})
        if set(caps) != {"call_table", "oracle", "teacher_replay"} or any(
            not isinstance(c, (int, float)) or not np.isfinite(c) or c <= 0 for c in caps.values()
        ):
            raise ValueError("fresh requires all explicit pretest job wall caps")
        slot = row["stream_slot"]
        if slot not in range(len(seeds)) or row["seed"] != seeds[slot]:
            raise ValueError("fresh cases require the reserved original seed slots")
        if (
            row["original_n"] not in original["teacher"]["n_candidates"]
            or row["steps_per_year"] != original["sde"]["independent_level"]
            or not row.get("original_record_identity")
            or not row.get("original_teacher")
        ):
            raise ValueError("fresh restart needs original N/grid/artifact record binding")
    return original, phase_cap, cases


def run_fresh(
    *,
    plan,
    frozen,
    candidate,
    source,
    original_artifact_identity,
    parameters,
    surface,
):
    """Run every locked selected restart, preserving bound raw evidence and N.

    The plan digest must already be in the frozen selection. Every case binds
    its original artifact anchor and reserved fresh seed slot. Original artifact
    byte authentication and raw financial checks remain caller/checker duties.
    No posttest case choice, implicit stream substitution or successful-path
    filtering is implemented.
    """
    wall, cpu = perf_counter(), process_time()
    from reference_methods import _timing, independent_call_table, quote_positions_oracle
    from run_reference import payload_digest

    _original, phase_cap, cases = _validate_inputs(
        plan=plan,
        frozen=frozen,
        candidate=candidate,
        source=source,
        original_artifact_identity=original_artifact_identity,
        parameters=parameters,
        surface=surface,
    )
    phase_deadline = wall + phase_cap
    records = []
    for row in cases:
        model = row["model"]
        if model not in {"heston", "local"}:
            raise ValueError("fresh model explicitly maps Heston to heston or local to local")
        jobs = []
        table = None
        begin, job_cpu = perf_counter(), process_time()
        planned = row["wall_caps"]["call_table"]
        effective = min(planned, max(0.0, phase_deadline - begin))
        if row["memory_count"] < 12 and row["memory_sum"] < 1200:
            spots = sorted(
                {row["spot"]}
                | {
                    row["spot"] + sign * row["spot_bump"] * w
                    for sign in [1, -1]
                    for w in [1.0, 0.5, 2.0]
                }
            )
            table = independent_call_table(
                parameters,
                surface,
                model=model,
                dates=[row["date"]],
                query_spots=spots,
                state_nodes=row["state_nodes"],
                controls=row["call_controls"],
                wall_cap_seconds=effective,
                deadline_wall=begin + effective,
            )
        jobs.append(
            {
                "id": "call_table",
                "planned_wall_cap_seconds": planned,
                "effective_wall_cap_seconds": effective,
                "phase_deadline_wall": phase_deadline,
                "not_required": table is None,
                **_timing(begin, job_cpu, begin + effective),
            }
        )
        begin, job_cpu = perf_counter(), process_time()
        planned = row["wall_caps"]["oracle"]
        effective = min(planned, max(0.0, phase_deadline - begin))
        raw = quote_positions_oracle(
            parameters,
            surface,
            model=model,
            date=row["date"],
            spot=row["spot"],
            quote=row["quote"],
            memory_sum=row["memory_sum"],
            memory_count=row["memory_count"],
            seed=row["seed"],
            n_paths=row["original_n"],
            call_table=table,
            steps_per_year=row["steps_per_year"],
            spot_bump=row["spot_bump"],
            quote_bump=row["quote_bump"],
            chunk_paths=row["chunk_paths"],
            wall_cap_seconds=effective,
            deadline_wall=begin + effective,
        )
        jobs.append(
            {
                "id": "oracle",
                "planned_wall_cap_seconds": planned,
                "effective_wall_cap_seconds": effective,
                "phase_deadline_wall": phase_deadline,
                "not_required": False,
                **_timing(begin, job_cpu, begin + effective),
            }
        )
        begin, job_cpu = perf_counter(), process_time()
        planned = row["wall_caps"]["teacher_replay"]
        effective = min(planned, max(0.0, phase_deadline - begin))
        teacher = _production_teacher_replay(
            parameters, surface, row, wall_cap_seconds=effective, deadline_wall=begin + effective
        )
        jobs.append(
            {
                "id": "teacher_replay",
                "planned_wall_cap_seconds": planned,
                "effective_wall_cap_seconds": effective,
                "phase_deadline_wall": phase_deadline,
                "not_required": False,
                **_timing(begin, job_cpu, begin + effective),
            }
        )
        records.append(
            {
                "teacher_replay": teacher,
                "id": row["id"],
                "original_record_identity": row["original_record_identity"],
                "stream_slot": row["stream_slot"],
                "raw": raw,
                "jobs": jobs,
            }
        )
    result = {
        "schema": "rb-f04-fresh-evidence-v1",
        "plan": plan,
        "plan_sha256": payload_digest(plan),
        "frozen_sha256": frozen["frozen_sha256"],
        "candidate_sha256": _canonical_digest(candidate),
        "source": source,
        "source_sha256": _canonical_digest(source),
        "original_artifact_identity": original_artifact_identity,
        "records": records,
        "surface_sha256": plan["surface_sha256"],
        "financial_qualification": "unknown",
        "scope": "all_locked_selected_restarts",
        "premium_record": plan.get("premium_record"),
        "phase_wall_cap_seconds": phase_cap,
        "cost": _timing(wall, cpu, phase_deadline),
    }
    result["raw_sha256"] = payload_digest(result)
    return result


def main():
    """Load bound inputs, execute reserved fresh math and save raw JSON+NPZ."""
    from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid
    from run_reference import load_bundle, save_bundle

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload, _inputs_receipt = load_bundle(args.inputs)
    parameters = HestonParameters(**payload["parameters"])
    descriptor = payload.get("surface")
    surface = (
        None
        if descriptor is None
        else LocalVarianceGrid(
            times=descriptor["times"],
            z_nodes=descriptor["z_nodes"],
            values=descriptor["values"],
            parameters=HestonParameters(**descriptor["parameters"])
            if "parameters" in descriptor
            else parameters,
            wing_boundaries=descriptor.get("wing_boundaries"),
        )
    )
    result = run_fresh(
        plan=payload["plan"],
        frozen=payload["frozen"],
        candidate=payload["candidate"],
        source=payload["source"],
        original_artifact_identity=payload["original_artifact_identity"],
        parameters=parameters,
        surface=surface,
    )
    save_bundle(args.output, result)


if __name__ == "__main__":
    main()
