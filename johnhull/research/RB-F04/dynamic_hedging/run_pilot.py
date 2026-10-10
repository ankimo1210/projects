"""Actual pilot workers and immutable lifecycle; no synthetic financial approval.

The full locked roster is mandatory for lifecycle execution. Small calls to
run_teacher_job are source probes, never execution readiness. Earlier SDE
correctness remains an independent fresh/code-review obligation.
"""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path
from time import perf_counter, perf_counter_ns, process_time, process_time_ns

if __name__ == "__main__":
    _CLI_ROOT = Path(__file__).resolve().parents[4]
    sys.path[:0] = [
        str(_CLI_ROOT / "johnhull/hullkit/src"),
        str(_CLI_ROOT / "deep_hedge_price/src"),
    ]

import _teacher_storage as teacher_storage
import numpy as np
import run_reference as runner
from hullkit._dynamic_hedging_conditional import primitive_labels, teacher_primitives
from hullkit._heston_local_surface import LocalVarianceGrid

from deep_hedge_price import _dynamic_hedging_execution as execution
from deep_hedge_price import _dynamic_hedging_protocol as protocol
from deep_hedge_price import _dynamic_hedging_study as study

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = "rb-f04-pilot-raw-v1"
PART_SCHEMA = "rb-f04-pilot-array-parts-v1"
PACK_SCHEMA = "rb-f04-pilot-array-packs-v2"
_PATH_KEYS = (
    "b",
    "c",
    "mu",
    "sigma",
    "last_z",
    "last_left_spot",
    "last_left_variance",
    "last_left_coefficient",
    "aux_logG_prefix",
    "path_mask",
    "primitive_status",
    "failure_reasons",
    "local_step_status",
)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _expense(identifier, wall, cpu, *, failed=None, parent=None, cap=None):
    return {
        "id": identifier,
        "scope": "formal_pilot",
        "status": "failed" if failed else "complete",
        "timing": {
            "wall_seconds": wall,
            "cpu_seconds": cpu,
            "overrun_seconds": 0.0 if cap is None else max(0.0, wall - cap),
        },
        "includes_children": True,
        "parent_id": parent,
        "reason": failed,
    }


def failed_job_record(identifier, reason, *, defect=True, raw=None, cap_evidence=None):
    """Keep defects unclosed; a reason alone never validates structural rejection."""
    return {
        "id": identifier,
        "status": "unclosed_source_or_solver_defect" if defect else "failed_at_declared_cap",
        "reason": reason,
        "raw": raw,
        "cap_evidence": None if defect else cap_evidence,
        "financial_qualification": "unknown",
    }


def _merge_primitives(parts, original_n, slice_sha):
    first = parts[0]
    result = {k: v for k, v in first.items() if k not in _PATH_KEYS}
    for key in _PATH_KEYS:
        if key != "local_step_status":
            result[key] = np.concatenate([part[key] for part in parts], axis=0)
    # Compact dictionaries may be discovered in different orders per chunk.
    labels = [""]
    mapped = []
    for part in parts:
        names = part["local_step_status_labels"].tolist()
        mapping = []
        for name in names:
            if name not in labels:
                labels.append(name)
            mapping.append(labels.index(name))
        mapped.append(np.asarray(mapping, dtype=np.uint8)[part["local_step_status"]])
    result["local_step_status"] = np.concatenate(mapped, axis=0)
    result["local_step_status_labels"] = np.asarray(labels, dtype="<U64")
    result.update(N=original_n, original_path_count=original_n, shared_driver_id=slice_sha)
    return result


def bound_artifact_path(path, artifact_context=None):
    """Rebase an authenticated original container into its restored copy."""
    path = Path(path)
    if artifact_context is None:
        return path
    original = Path(artifact_context["original_root"]).resolve()
    restored = Path(artifact_context["restored_root"]).resolve()
    relative = path.resolve().relative_to(original)
    result = (restored / relative).resolve()
    _require(result.is_relative_to(restored), "restored raw reference escaped container")
    return result


def _validate_teacher_reference(reference, seed, original_n):
    if reference is None:
        return
    _require(
        isinstance(reference, dict)
        and set(reference) == {"reference_rule", "stream_namespace", "seed"}
        and original_n == 65536
        and reference["reference_rule"] == "independent_reserved_stream_grid_max"
        and reference["stream_namespace"] == "oracle"
        and reference["seed"] == seed
        and seed in protocol.candidate_protocol()["seeds"]["oracle"],
        "maximum teacher reference needs original reserved independent stream",
    )


def run_teacher_driver_job(
    *,
    seed,
    original_n,
    calendar_times,
    chunk_paths,
    work_directory,
    wall_cap_seconds=None,
    teacher_reference=None,
):
    """Save one original fine driver, reused by grid/date/node without duplicated arrays."""
    _validate_teacher_reference(teacher_reference, seed, original_n)
    times = np.asarray(calendar_times, dtype=float)
    n = original_n
    steps = len(times) - 1
    _require(
        n >= 16
        and n % 16 == 0
        and chunk_paths > 0
        and times.ndim == 1
        and times[0] == 0
        and times[-1] == 1
        and np.all(np.diff(times) > 0),
        "original teacher driver geometry required",
    )
    _require(
        chunk_paths * steps * 16 < 128 * 1024**2 and chunk_paths * steps <= 1_000_000_000,
        "original driver child cap exceeded",
    )
    _require(
        wall_cap_seconds is None or (np.isfinite(wall_cap_seconds) and wall_cap_seconds > 0),
        "invalid driver wall cap",
    )
    generator = np.random.default_rng(seed)
    rows = []
    digest = hashlib.sha256()
    begin, cpu = perf_counter(), process_time()
    done = 0
    for lo in range(0, n, chunk_paths):
        if wall_cap_seconds is not None and perf_counter() - begin >= wall_cap_seconds:
            break
        hi = min(n, lo + chunk_paths)
        normal = generator.standard_normal((hi - lo, steps, 2))
        digest.update(normal.tobytes())
        raw = {
            "normal": normal,
            "path_ids": np.arange(lo, hi),
            "cluster_ids": np.arange(lo, hi) // (n // 16),
            "path_start": lo,
            "path_stop": hi,
        }
        name = f"driver{len(rows):06d}"
        write_pilot_artifact(Path(work_directory) / name, raw)
        rows.append(
            {
                "path": name,
                "path_start": lo,
                "path_stop": hi,
                "raw_sha256": runner.payload_digest(raw),
                "normal_sha256": hashlib.sha256(normal.tobytes()).hexdigest(),
                "path_steps": (hi - lo) * steps,
            }
        )
        done = hi
    elapsed = perf_counter() - begin
    return {
        "kind": "teacher_driver",
        "teacher_reference": copy.deepcopy(teacher_reference),
        "seed": seed,
        "original_n": n,
        "calendar_times": times.copy(),
        "ordering": "path_step_factor",
        "chunk_paths": chunk_paths,
        "directory": str(Path(work_directory).resolve()),
        "path_ids": np.arange(n),
        "cluster_ids": np.arange(n) // (n // 16),
        "chunks": rows,
        "global_driver_id": digest.hexdigest() if done == n else None,
        "executed_driver_sha256": digest.hexdigest(),
        "processed_n": done,
        "unexecuted_n": n - done,
        "status": "executed" if done == n else "failed_at_declared_cap",
        "cap_evidence": None
        if done == n
        else {"metric": "wall_seconds", "limit": wall_cap_seconds, "consumed": elapsed},
        "expense": _expense(
            "teacher_driver_worker",
            elapsed,
            process_time() - cpu,
            failed=None if done == n else "original driver cap",
            cap=wall_cap_seconds,
        ),
        "financial_qualification": "unknown",
    }


def read_teacher_driver_chunks(driver, *, artifact_context=None):
    """Authenticate original raw driver; never regenerate a financial RNG."""
    n = driver["original_n"]
    _validate_teacher_reference(driver.get("teacher_reference"), driver["seed"], n)
    steps = len(driver["calendar_times"]) - 1
    _require(
        driver["ordering"] == "path_step_factor" and n % 16 == 0,
        "original teacher driver ordering/clusters changed",
    )
    _require(
        np.array_equal(driver["path_ids"], np.arange(n))
        and np.array_equal(driver["cluster_ids"], np.arange(n) // (n // 16)),
        "original teacher driver IDs changed",
    )
    directory = bound_artifact_path(driver["directory"], artifact_context)
    digest = hashlib.sha256()
    stop = 0
    for descriptor in driver["chunks"]:
        _require(
            Path(descriptor["path"]).name == descriptor["path"],
            "driver chunk escaped immutable store",
        )
        raw, _ = read_pilot_artifact(directory / descriptor["path"])
        lo, hi = descriptor["path_start"], descriptor["path_stop"]
        _require(
            lo == stop and lo < hi <= n and raw["path_start"] == lo and raw["path_stop"] == hi,
            "original shared driver chunk gap/reorder",
        )
        normal = np.asarray(raw["normal"])
        _require(
            normal.shape == (hi - lo, steps, 2)
            and normal.dtype == np.float64
            and np.isfinite(normal).all()
            and np.array_equal(raw["path_ids"], np.arange(lo, hi))
            and np.array_equal(raw["cluster_ids"], np.arange(lo, hi) // (n // 16))
            and descriptor["path_steps"] == (hi - lo) * steps
            and runner.payload_digest(raw) == descriptor["raw_sha256"]
            and hashlib.sha256(normal.tobytes()).hexdigest() == descriptor["normal_sha256"],
            "original shared driver raw bytes/shape/path binding differs",
        )
        digest.update(normal.tobytes())
        stop = hi
        yield raw
    _require(
        stop == driver["processed_n"]
        and driver["unexecuted_n"] == n - stop
        and digest.hexdigest() == driver["executed_driver_sha256"],
        "original shared driver prefix accounting differs",
    )
    _require(
        driver["global_driver_id"] == (digest.hexdigest() if stop == n else None),
        "original full driver SHA cannot name a partial prefix",
    )


def run_teacher_job(
    parameters,
    surface,
    *,
    model,
    seed,
    original_n,
    chunk_paths,
    calendar_times,
    start_index,
    spot,
    state,
    thresholds,
    wall_cap_seconds=None,
    driver=None,
):
    """Run real conditional paths, merging once before global 16-block moments.

    Each node restarts the same local Generator, so date/node sharing and
    original-N prefixes have one path/step/factor order. No global RNG is used.
    """
    times = np.asarray(calendar_times, dtype=float)
    n = int(original_n)
    chunk = int(chunk_paths)
    start = int(start_index)
    _require(n == original_n and n >= 16 and n % 16 == 0, "original N must form 16 clusters")
    _require(chunk == chunk_paths and chunk > 0, "invalid chunk paths")
    _require(
        times.ndim == 1
        and times.size > 1
        and times[0] == 0
        and times[-1] == 1
        and np.all(np.diff(times) > 0),
        "full teacher calendar required",
    )
    _require(0 <= start < len(times) - 1, "invalid restart index")
    _require(model in ("Heston", "local"), "unknown teacher model")
    intervals = len(times) - 1
    _require(
        chunk * intervals <= protocol.candidate_protocol()["limits"]["job_path_steps"],
        "job path-step cap exceeded",
    )
    _require(chunk * intervals * 16 < 192 * 1024**2, "normal chunk byte cap exceeded")
    fixings = []
    for date in np.arange(1, 13) / 12:
        if date > times[start] + 1e-12:
            indices = np.flatnonzero(np.isclose(times, date, atol=1e-12, rtol=0))
            _require(len(indices) == 1, "calendar does not contain each monthly fixing")
            fixings.append(int(indices[0]) - start)
    _require(
        wall_cap_seconds is None or (np.isfinite(wall_cap_seconds) and wall_cap_seconds > 0),
        "invalid teacher wall cap",
    )
    if driver is not None:
        _require(
            driver["status"] == "executed"
            and driver["seed"] == seed
            and driver["original_n"] == n
            and driver["chunk_paths"] == chunk
            and np.array_equal(driver["calendar_times"], times),
            "original shared teacher driver differs",
        )
    generator = np.random.default_rng(seed) if driver is None else None
    driver_chunks = None if driver is None else iter(read_teacher_driver_chunks(driver))
    restart = {
        "spot": spot,
        "state": state,
        "start_index": start,
        "calendar_times": times.copy(),
        "fixing_indices": np.asarray(fixings, dtype=int),
    }
    full_digest, slice_digest = hashlib.sha256(), hashlib.sha256()
    parts, mappings, expenses = [], [], []
    t0, c0 = perf_counter(), process_time()
    for lo in range(0, n, chunk):
        if wall_cap_seconds is not None and perf_counter() - t0 >= wall_cap_seconds:
            done = lo
            return {
                "kind": "teacher",
                "driver": driver,
                "restart": restart,
                "model": model,
                "seed": seed,
                "original_n": n,
                "status": "failed_at_declared_cap",
                "path_ids": np.arange(n),
                "cluster_ids": np.arange(n) // (n // 16),
                "executed_path_ids": np.arange(done),
                "unexecuted_path_count": n - done,
                "path_status": np.r_[
                    np.full(done, "executed_raw"), np.full(n - done, "not_executed_at_declared_cap")
                ],
                "raw_chunks": parts,
                "chunks": mappings,
                "labels": None,
                "financial_qualification": "unknown",
                "cap_evidence": {
                    "metric": "wall_seconds",
                    "limit": wall_cap_seconds,
                    "consumed": perf_counter() - t0,
                },
                "expenses": [
                    _expense(
                        "teacher_worker",
                        perf_counter() - t0,
                        process_time() - c0,
                        failed="declared teacher wall cap reached",
                    ),
                    *expenses,
                ],
            }
        hi = min(n, lo + chunk)
        begin, cpu = perf_counter(), process_time()
        if driver_chunks is None:
            normals = generator.standard_normal((hi - lo, intervals, 2))
        else:
            chunk_raw = next(driver_chunks)
            _require(
                chunk_raw["path_start"] == lo and chunk_raw["path_stop"] == hi,
                "shared teacher chunk coverage differs",
            )
            normals = chunk_raw["normal"]
        full_digest.update(np.ascontiguousarray(normals).tobytes())
        sliced = normals[:, start:]
        slice_digest.update(np.ascontiguousarray(sliced).tobytes())
        try:
            primitive = teacher_primitives(
                model.lower(),
                parameters,
                sliced,
                calendar_times=times[start:],
                fixing_indices=np.asarray(fixings, dtype=int),
                spot=spot,
                state=state,
                memory_count=12 - len(fixings),
                surface=surface,
                compact_status=True,
            )
        except (ValueError, KeyError, FloatingPointError, RuntimeError) as error:
            elapsed = perf_counter() - t0
            return {
                "kind": "teacher",
                "driver": driver,
                "restart": restart,
                "model": model,
                "seed": seed,
                "original_n": n,
                "status": "unclosed_source_or_solver_defect",
                "reason": f"{type(error).__name__}: {error}",
                "path_ids": np.arange(n),
                "cluster_ids": np.arange(n) // (n // 16),
                "executed_path_ids": np.arange(lo),
                "unexecuted_path_count": n - lo,
                "path_status": np.r_[
                    np.full(lo, "executed_raw"), np.full(n - lo, "unexecuted_solver_defect")
                ],
                "raw_chunks": parts,
                "chunks": mappings,
                "labels": None,
                "cap_evidence": None,
                "failed_driver": {
                    "path_start": lo,
                    "path_stop": hi,
                    "normals": normals,
                    "normal_sha256": hashlib.sha256(normals.tobytes()).hexdigest(),
                },
                "expenses": [
                    _expense("teacher_worker", elapsed, process_time() - c0, failed=str(error)),
                    *expenses,
                    _expense(
                        f"failed_chunk:{lo}:{hi}",
                        perf_counter() - begin,
                        process_time() - cpu,
                        failed=str(error),
                        parent="teacher_worker",
                    ),
                ],
                "financial_qualification": "unknown",
            }
        parts.append(primitive)
        mappings.append(
            {
                "path_start": lo,
                "path_stop": hi,
                "global_steps": intervals,
                "start_step": start,
                "stop_step": intervals,
                "normal_sha256": hashlib.sha256(normals.tobytes()).hexdigest(),
                "slice_sha256": primitive["shared_driver_id"],
                "path_steps": (hi - lo) * intervals,
                "normal_expanded_bytes": normals.nbytes,
            }
        )
        expenses.append(
            _expense(
                f"chunk:{lo}:{hi}",
                perf_counter() - begin,
                process_time() - cpu,
                parent="teacher_worker",
            )
        )
    if driver_chunks is not None:
        _require(next(driver_chunks, None) is None, "extra original shared teacher chunk")
    merged = _merge_primitives(parts, n, slice_digest.hexdigest())
    labels = primitive_labels(merged, np.asarray(thresholds), blocks=16)
    labels["shared_driver_id"] = full_digest.hexdigest()
    labels["date_index"] = int(np.floor(times[start] * 12 + 1e-9))
    return {
        "kind": "teacher",
        "driver": driver,
        "restart": restart,
        "model": model,
        "seed": seed,
        "original_n": n,
        "path_ids": np.arange(n),
        "cluster_ids": np.arange(n) // (n // 16),
        "stream_identity": runner.payload_digest(
            {"seed": seed, "calendar_times": times, "ordering": "path_step_factor"}
        ),
        "global_driver_id": full_digest.hexdigest(),
        "chunks": mappings,
        "driver_mapping": {
            "global_steps": intervals,
            "start_step": start,
            "stop_step": intervals,
            "original_n": n,
            "aggregation_factor": 1,
            "slice_sha256": merged["shared_driver_id"],
        },
        "primitives": merged,
        "thresholds": np.asarray(thresholds).copy(),
        "labels": labels,
        "date_index": labels["date_index"],
        "expenses": [
            _expense("teacher_worker", perf_counter() - t0, process_time() - c0),
            *expenses,
        ],
        "financial_qualification": "unknown",
    }


def run_stream_receipts_job(*, markets, roles, seed_namespace):
    """Bind actual completed original market bytes; no prior invented global IDs."""
    values = {}
    digests = {}
    for role, by_model in roles.items():
        _require(
            role in ("train", "validation", "primary", "precision"),
            "declared pilot stream role required",
        )
        values[role] = {}
        for model, keys in by_model.items():
            _require(model in ("Heston", "local"), "original stream model required")
            multiple = isinstance(keys, list)
            selected = keys if multiple else [keys]
            rows = []
            for slot, key in enumerate(selected):
                market = markets[key]
                n = market["original_n"]
                mi = 0 if model == "Heston" else 1
                expected = (
                    seed_namespace["refinement"][slot]
                    if role == "precision"
                    else seed_namespace["pilot"][
                        mi + {"train": 0, "validation": 2, "primary": 4}[role]
                    ]
                )
                _require(
                    market["status"] == "executed"
                    and market["model"] == model
                    and market["seed"] == expected
                    and market["processed_n"] == n,
                    "actual stream must match original namespace/model/N",
                )
                digest = hashlib.sha256()
                stop = 0
                for index, driver in enumerate(market["driver_map"]):
                    normal = market["raw_chunks"][1][index]["primitives"]["normals"]
                    _require(
                        driver["path_start"] == stop
                        and normal.shape == (driver["path_stop"] - stop, 1536, 2)
                        and hashlib.sha256(normal.tobytes()).hexdigest() == driver["fine_sha256"],
                        "actual stream raw order/normal binding changed",
                    )
                    digest.update(normal.tobytes())
                    stop = driver["path_stop"]
                _require(
                    stop == n and np.array_equal(market["path_ids"], np.arange(n)),
                    "stream original denominator/path order changed",
                )
                bound = runner.payload_digest(market)
                digests[key] = bound
                rows.append(
                    {
                        "seed": expected,
                        "original_n": n,
                        "global_driver_id": digest.hexdigest(),
                        "producer_raw_sha256": bound,
                        "ordering": "path_step_factor",
                        "driver_steps": 1536,
                    }
                )
            values[role][model] = rows if multiple else rows[0]
    _require(set(markets) == set(digests), "unused or missing actual stream producer")
    return {
        "kind": "stream_receipts",
        "roles": roles,
        "seed_namespace": seed_namespace,
        "market_raw_sha256": digests,
        "value": values,
        "financial_qualification": "unknown",
    }


def run_frequency_cache_job(*, caches, dates):
    """Exact-date read view: missing Asian sheets remain full-shape unknown.

    Original monthly cache is retained byte-for-byte, including all raw groups,
    original N, axes, failures and block curves. This extends date lookup only;
    no price interpolation or new financial support is inferred.
    """
    from hullkit._dynamic_hedging_surfaces import build_asian_cache

    dates = np.asarray(dates, float)
    _require(
        dates.ndim == 1
        and len(dates) > 1
        and dates[0] == 0
        and dates[-1] < 1
        and np.all(np.diff(dates) > 0),
        "exact Asian lookup dates required",
    )
    result = {}
    maps = {}
    for model, item in caches.items():
        original = item["asian"]
        old = np.asarray(original["dates"])
        mapping = []
        for date in dates:
            found = np.flatnonzero(np.isclose(old, date, rtol=0, atol=1e-12))
            mapping.append(int(found[0]) if len(found) == 1 else None)
        _require(
            set(i for i in mapping if i is not None) == set(range(len(old))),
            "frequency view must retain all original monthly dates",
        )
        f = np.full((len(dates), *original["f"].shape[1:]), np.nan)
        blocks = np.full((len(dates), *original["block_means"].shape[1:]), np.nan)
        threshold = []
        domains = []
        for j, index in enumerate(mapping):
            n = int(np.floor(dates[j] * 12 + 1e-9))
            threshold.append(original["threshold_nodes"][n])
            if index is not None:
                f[j] = original["f"][index]
                blocks[j] = original["block_means"][index]
                if original.get("evaluation_domains") is not None:
                    domains.append(original["evaluation_domains"][index])
                else:
                    domain = {
                        "state": [0, len(original["state_nodes"])],
                        "threshold": [0, len(original["threshold_nodes"][index])],
                    }
                    if model == "local":
                        sheet = original.get("t0_sheet") if dates[j] == 0 else None
                        domain["spot"] = [
                            0,
                            len(
                                sheet["spot_nodes"] if sheet is not None else original["spot_nodes"]
                            ),
                        ]
                    domains.append(domain)
            else:
                domains.append(None)
        axes = {
            "dates": dates,
            "state": original["state_nodes"],
            "threshold": np.asarray(threshold),
        }
        if model == "local":
            axes["spot"] = original["spot_nodes"]
            if original.get("t0_sheet") is not None:
                axes["t0_spot"] = original["t0_sheet"]["spot_nodes"]
        primitive = {
            "N": original["original_N"],
            "parameters": original["primitive_groups"]["parameters"],
            "f": f,
            "block_means": blocks,
        }
        if original.get("t0_sheet") is not None:
            primitive.update(
                t0_f=original["t0_sheet"]["f"], t0_block_means=original["t0_sheet"]["block_means"]
            )
        view = build_asian_cache(
            primitive,
            model=model,
            axes=axes,
            evaluation_domains=domains if original.get("evaluation_domains") is not None else None,
        )
        view.update(
            original_monthly_cache=original,
            exact_date_lookup_map=mapping,
            missing_exact_date_mask=np.asarray([i is None for i in mapping]),
            unknown_sheet_reason="not provided at this exact date; no interpolation",
            shared_driver_ids=original["shared_driver_ids"],
        )
        result[model] = {"call": item["call"], "asian": view}
        maps[model] = mapping
    return {
        "kind": "frequency_cache",
        "arguments": {"caches": caches, "dates": dates},
        "value": result,
        "date_maps": maps,
        "financial_qualification": "unknown",
    }


def run_quote_risk_job(
    parameters, surface, dataset, caches, *, chunk_paths=256, wall_cap_seconds=None
):
    """Keep quote_risk contract while using the actual bounded original-path worker."""
    from run_main import run_risk_job

    arguments = {
        "parameters": parameters,
        "surface": surface,
        "dataset": dataset,
        "caches": caches,
        "chunk_paths": chunk_paths,
        "wall_cap_seconds": wall_cap_seconds,
    }
    actual = run_risk_job(**arguments)
    return {
        "kind": "quote_risk",
        "arguments": pack_inputs(arguments),
        "value": actual["risk"],
        "chunked_worker": actual,
        "original_n": dataset["original_n"],
        "status": actual["status"],
        "reason": actual["reason"],
        "cap_evidence": actual["cap_evidence"],
        "financial_qualification": "unknown",
    }


def paired_policy_rollout(dataset, risk, *, selection=None, **arguments):
    """Recompute the selected policy; a failed band remains None and unknown."""
    if selection is not None:
        model = arguments["model"]
        _require(
            selection["universe"] == arguments["universe"], "paired selection universe differs"
        )
        selected = selection["selected_bands"][model]
        rows = [r for r in selection["candidates"] if r["id"].startswith("band:" + model + ":")]
        expected = protocol.candidate_protocol()["hedging"]["band_width_candidates"]
        _require(
            len(rows) == len(expected)
            and {r["id"] for r in rows} == {f"band:{model}:width{w:g}" for w in expected},
            "paired selection original width roster differs",
        )
        if selected is None:
            _require(
                arguments["width"] is None
                and all(r["status"] != "completed" and r["reason"] for r in rows),
                "failed original band selection cannot become numeric width",
            )
            return study._unknown_rollout(
                dataset, "all original width candidates failed or unqualified"
            )
        _require(
            any(r["id"] == selected and r["status"] == "completed" for r in rows),
            "paired selection lacks a completed original candidate",
        )
        width = float(selected.split(":width")[1])
        _require(arguments["width"] == width, "paired selected width differs")
    return study.policy_rollout(dataset, risk, **arguments)


def cell_policy_arguments(identity, validation, fits):
    """Resolve only the original roster selection, including explicit failed None."""
    _require(
        identity in protocol.study_roster()["primary_cells"],
        "original paired cell identity required",
    )
    _require(
        validation["generator"] == identity["generator"]
        and validation["universe"] == identity["universe"],
        "original validation selection identity differs",
    )
    policy = "none" if identity["policy"] == "no_hedge" else identity["policy"]
    args = {"universe": identity["universe"], "policy": policy}
    if policy in ("greek", "band"):
        args["model"] = identity["valuation"]
    if policy == "band":
        selected = validation["selected_bands"][identity["valuation"]]
        args.update(
            selection=validation,
            width=None if selected is None else float(selected.split(":width")[1]),
        )
    if policy == "nn":
        identifier = (
            f"fit:{identity['training_generator']}:{identity['universe']}:"
            f"init{identity['initialization']}"
        )
        rows = [r for r in fits if r["id"] == identifier]
        _require(len(rows) <= 1, "original NN fit slot repeated")
        args["fit"] = rows[0]["raw_fit"] if rows else None
    return args


def run_cell_pair_job(
    *,
    base_dataset,
    refined_dataset,
    base_risk,
    refined_risk,
    identity,
    validation,
    fits,
    refinement_kind,
    shared_market=None,
    dataset_indices=(0, 1),
    base_risk_source=None,
    refined_risk_source=None,
    refined_risk_width_index=None,
):
    """Typed original cell, preserving failed band/NN selections and every path."""
    args = cell_policy_arguments(identity, validation, fits)
    raw = run_paired_pnl_job(
        base={"dataset": base_dataset, "risk": base_risk, **args},
        refined={"dataset": refined_dataset, "risk": refined_risk, **args},
        identity=identity,
        refinement_kind=refinement_kind,
        shared_market=shared_market,
        dataset_indices=dataset_indices,
        base_risk_source=base_risk_source,
        refined_risk_source=refined_risk_source,
        comparison_quantity="cash_vs_independent_gain" if refinement_kind == "pnl" else "cash",
    )
    raw["refined_risk_width_index"] = refined_risk_width_index
    raw["selection_inputs"] = {"validation": validation, "fits": fits, "identity": identity}
    return raw


def run_paired_pnl_job(
    *,
    base,
    refined,
    identity=None,
    refinement_kind=None,
    shared_market=None,
    dataset_indices=(0, 1),
    base_risk_source=None,
    refined_risk_source=None,
    comparison_quantity="cash",
):
    """Execute both original policies and preserve full cash inputs and pairing."""
    _require(
        comparison_quantity in ("cash", "cash_vs_independent_gain"),
        "original paired quantity unsupported",
    )
    _require(
        comparison_quantity == "cash" or refinement_kind == "pnl",
        "independent gain quantity belongs to P&L reconstruction",
    )
    a = paired_policy_rollout(**base)
    b = paired_policy_rollout(**refined)
    n = base["dataset"]["original_n"]
    _require(refined["dataset"]["original_n"] == n, "paired original N differs")
    return {
        "kind": "paired_pnl",
        "original_n": n,
        "path_ids": np.arange(n),
        "base": np.asarray(a["discounted_pnl"]).copy(),
        "refined": np.asarray(
            b["discounted_gain_pnl"]
            if comparison_quantity == "cash_vs_independent_gain"
            else b["discounted_pnl"]
        ).copy(),
        "comparison_quantity": comparison_quantity,
        "base_dataset": base["dataset"],
        "refined_dataset": refined["dataset"],
        "base_rollout": a,
        "refined_rollout": b,
        "identity": identity,
        "refinement_kind": refinement_kind,
        "shared_market": shared_market,
        "dataset_indices": list(dataset_indices),
        "base_risk_source": base_risk_source,
        "refined_risk_source": refined_risk_source,
        "shared_driver_binding": None
        if shared_market is None
        else runner.payload_digest(
            {
                k: shared_market[k]
                for k in ("seed", "driver_map", "original_n", "levels", "frequencies")
            }
        ),
        "base_risk": base.get("risk"),
        "refined_risk": refined.get("risk"),
        "base_arguments": {k: v for k, v in base.items() if k not in ("dataset", "risk")},
        "refined_arguments": {k: v for k, v in refined.items() if k not in ("dataset", "risk")},
        "financial_qualification": "unknown",
    }


def run_quotes_job(parameters, surface, *, controls, wall_cap_seconds=None):
    """Execute all original 37 quotes with current independent CF and actual PDE.

    Every raw solver receipt and original quote slot is retained. A cap stops
    at the next solver boundary; unsupported PDE/CF results stay NaN.
    """
    from check_initial_quotes import _roster
    from hullkit._heston_local_surface import fourier_surface
    from reference_methods import independent_heston_call, pde_call

    roster = _roster()
    stages = controls["pde_stages"]
    _require(
        stages and len({x["id"] for x in stages}) == len(stages),
        "distinct planned PDE stages required",
    )
    results = {
        "kind": "quotes",
        "original_n": 37,
        "quote_ids": np.arange(37),
        "parameters": vars(parameters),
        "groups": [],
        "truth250": np.full(37, np.nan),
        "truth500": np.full(37, np.nan),
        "truth500_error": np.full(37, np.nan),
        "production": np.full((3, 37), np.nan),
        "pde_prices": np.full((len(stages), 37), np.nan),
        "pde_stages": stages,
        "expenses": [],
        "financial_qualification": "unknown",
    }
    start, cpu = perf_counter(), process_time()
    offset = 0
    for group_index, (role, t, strikes) in enumerate(roster):
        if wall_cap_seconds is not None and perf_counter() - start >= wall_cap_seconds:
            results.update(
                status="failed_at_declared_cap",
                cap_evidence={
                    "metric": "wall_seconds",
                    "limit": wall_cap_seconds,
                    "consumed": perf_counter() - start,
                },
            )
            break
        begin, cp = perf_counter(), process_time()
        low = independent_heston_call(strikes, t, parameters, upper=250, return_receipt=True)
        high = independent_heston_call(strikes, t, parameters, upper=500, return_receipt=True)
        production = []
        for order, cutoff in ((1024, 512), (2048, 512), (2048, 1024)):
            production.append(
                fourier_surface(strikes, t, parameters, order=order, max_frequency=cutoff)
            )
        pdes = []
        for stage in stages:
            if wall_cap_seconds is not None and perf_counter() - start >= wall_cap_seconds:
                break
            pdes.append(
                pde_call(
                    parameters.spot,
                    strikes,
                    t,
                    surface.evaluate,
                    parameters.rate,
                    parameters.dividend_yield,
                    space_nodes=stage["space_nodes"],
                    time_steps=stage["time_steps"],
                    log_half_width=stage["log_half_width"],
                )
            )
        stop = offset + len(strikes)
        results["truth250"][offset:stop] = low["price"]
        results["truth500"][offset:stop] = high["price"]
        results["truth500_error"][offset:stop] = high["price_unit_error"]
        results["production"][:, offset:stop] = [v["price"] for v in production]
        for j, value in enumerate(pdes):
            results["pde_prices"][j, offset:stop] = value["price"]
        results["groups"].append(
            {
                "group_index": group_index,
                "role": role,
                "date": t,
                "strikes": strikes,
                "quote_ids": np.arange(offset, stop),
                "low": low,
                "high": high,
                "production": production,
                "pdes": pdes,
            }
        )
        results["expenses"].append(
            _expense(
                f"quote-group:{group_index}",
                perf_counter() - begin,
                process_time() - cp,
                parent="quotes_worker",
            )
        )
        offset = stop
    complete = len(results["groups"]) == 8 and all(
        len(g["pdes"]) == len(stages) for g in results["groups"]
    )
    if not complete:
        results.update(
            status="failed_at_declared_cap",
            cap_evidence={
                "metric": "wall_seconds",
                "limit": wall_cap_seconds,
                "consumed": perf_counter() - start,
            },
        )
    results.setdefault("status", "executed")
    results["expenses"].insert(
        0,
        _expense(
            "quotes_worker",
            perf_counter() - start,
            process_time() - cpu,
            failed=results.get("reason"),
            cap=wall_cap_seconds,
        ),
    )
    return results


def run_field_job(
    parameters,
    *,
    times,
    z_nodes,
    order=2048,
    cutoff=1024,
    frequency_scale=None,
    density_floor=1e-10,
    wall_cap_seconds=None,
):
    """Construct the actual Heston marginal field, keeping every unsupported cell."""
    from hullkit._heston_local_surface import fourier_surface

    times, z = np.asarray(times), np.asarray(z_nodes)
    _require(np.all(times > 0), "field positive times required")
    _require(
        frequency_scale is None or (np.isfinite(frequency_scale) and frequency_scale > 0),
        "field positive frequency scale required",
    )
    controls = {
        "order": order,
        "cutoff": cutoff,
        "frequency_scale": frequency_scale,
        "density_floor": density_floor,
        "frequency_rule": "fixed_cutoff" if frequency_scale is None else "scale_over_sqrt_time",
    }
    raw = np.full((len(times), len(z)), np.nan)
    support = np.zeros(raw.shape, dtype=bool)
    rows, bounds = [], []
    begin, cpu = perf_counter(), process_time()
    for j, t in enumerate(times):
        if wall_cap_seconds is not None and perf_counter() - begin >= wall_cap_seconds:
            return {
                **controls,
                "kind": "field",
                "status": "failed_at_declared_cap",
                "times": times,
                "z_nodes": z,
                "raw_values": raw,
                "support_mask": support,
                "rows": rows,
                "field": None,
                "cap_evidence": {
                    "metric": "wall_seconds",
                    "limit": wall_cap_seconds,
                    "consumed": perf_counter() - begin,
                },
            }
        integrated = (
            parameters.theta * t
            + (parameters.v0 - parameters.theta)
            * (-np.expm1(-parameters.kappa * t))
            / parameters.kappa
        )
        strikes = parameters.spot * np.exp(
            (parameters.rate - parameters.dividend_yield) * t + z * np.sqrt(integrated)
        )
        row_cutoff = cutoff if frequency_scale is None else frequency_scale / np.sqrt(t)
        result = fourier_surface(
            strikes,
            t,
            parameters,
            order=order,
            max_frequency=row_cutoff,
            density_floor=density_floor,
        )
        raw[j] = result["local_variance"]
        support[j] = result["supported"]
        rows.append(
            {
                "date": t,
                "strikes": strikes,
                "surface": result,
                "order": order,
                "max_frequency": row_cutoff,
                "density_floor": density_floor,
            }
        )
        center = int(np.argmin(abs(z)))
        if not support[j, center]:
            return {
                **controls,
                "kind": "field",
                "status": "unavailable",
                "reason": "unsupported central field node",
                "times": times,
                "z_nodes": z,
                "raw_values": raw,
                "support_mask": support,
                "rows": rows,
                "field": None,
            }
        lo = hi = center
        while lo > 0 and support[j, lo - 1]:
            lo -= 1
        while hi + 1 < len(z) and support[j, hi + 1]:
            hi += 1
        if hi <= lo:
            return {
                **controls,
                "kind": "field",
                "status": "unavailable",
                "reason": "no contiguous field interior",
                "times": times,
                "z_nodes": z,
                "raw_values": raw,
                "support_mask": support,
                "rows": rows,
                "field": None,
            }
        bounds.append([lo, hi])
    field = LocalVarianceGrid(times, z, raw, parameters, np.asarray(bounds))
    return {
        **controls,
        "kind": "field",
        "status": "executed",
        "times": times,
        "z_nodes": z,
        "raw_values": raw,
        "support_mask": support,
        "rows": rows,
        "field": {
            "times": field.times,
            "z_nodes": field.z_nodes,
            "values": field.values,
            "wing_boundaries": field.wing_boundaries,
            "parameters": parameters,
        },
        "order": order,
        "cutoff": cutoff,
        "expense": _expense("field_worker", perf_counter() - begin, process_time() - cpu),
        "financial_qualification": "unknown",
    }


def materialize_field(record):
    """Use only the actual retained field, preserving explicit wings and support."""
    _require(
        record["status"] == "executed" and record["field"] is not None, "actual field unavailable"
    )
    field = record["field"]
    return LocalVarianceGrid(
        field["times"],
        field["z_nodes"],
        field["values"],
        field["parameters"],
        field["wing_boundaries"],
    )


def run_cache_job(parameters, *, rows, axes, model, evaluation_domains):
    from hullkit._dynamic_hedging_surfaces import build_asian_cache

    groups = {
        "groups": [row["labels"] for row in rows],
        "parameters": parameters,
        "N": rows[0]["original_n"],
    }
    cache = build_asian_cache(
        groups, model=model.lower(), axes=axes, evaluation_domains=evaluation_domains
    )
    return {
        "kind": "asian_cache",
        "model": model,
        "axes": axes,
        "evaluation_domains": evaluation_domains,
        "rows": rows,
        "cache": cache,
        "original_n": rows[0]["original_n"],
        "financial_qualification": "unknown",
    }


def run_state_job(
    parameters,
    surface,
    *,
    model,
    call_cache,
    asian_cache,
    date_index,
    spot,
    quote,
    memory_sum,
    memory_count,
    oracle,
):
    from hullkit._dynamic_hedging_risk import quote_positions
    from hullkit._dynamic_hedging_surfaces import evaluate_asian, evaluate_call, fit_quote_state

    call = dict(call_cache)
    call["asian_state_bounds"] = [
        float(asian_cache["state_nodes"][0]),
        float(asian_cache["state_nodes"][-1]),
    ]
    fit = fit_quote_state(
        call, date_index, spot, quote, state_scale=0.04 if model == "Heston" else 1.0
    )
    claim = evaluate_asian(asian_cache, date_index, spot, fit["state"], memory_sum, memory_count)
    traded = evaluate_call(call, date_index, spot, fit["state"])
    positions = quote_positions(
        claim["spot_derivative"],
        claim["state_derivative"],
        traded["spot_derivative"],
        traded["state_derivative"],
    )
    return {
        "kind": "state",
        "model": model,
        "call_cache": call,
        "asian_cache": asian_cache,
        "date_index": date_index,
        "spot": spot,
        "quote": quote,
        "memory_sum": memory_sum,
        "memory_count": memory_count,
        "fit": fit,
        "claim": claim,
        "traded": traded,
        "positions": positions,
        "oracle": oracle,
        "original_n": asian_cache["original_N"],
        "oracle_original_n": oracle["original_path_count"],
        "financial_qualification": "unknown",
    }


def teacher_axes(grid, model):
    """The original coarse/high boxes; a selected patch never changes full axes."""
    _require(grid in ("coarse", "high") and model in ("Heston", "local"), "invalid original grid")
    high = grid == "high"
    coarse = np.array([1e-5, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.5])
    states = np.sort(np.r_[coarse, 0.0025, 0.0075, 0.03, 0.06]) if high else coarse
    thresholds = []
    for j in range(12):
        m = 12 - j
        scale = 0.15 * np.sqrt(m)
        intervals = 32 if high else 16
        left = m - scale * np.sinh(np.linspace(np.arcsinh(m / scale), 0, intervals + 1))
        right = m + scale * np.sinh(np.linspace(0, np.arcsinh((24 - m) / scale), intervals + 1))[1:]
        axis = np.r_[left, right]
        axis[0] = 0.0
        axis[intervals] = float(m)
        axis[-1] = 24.0
        thresholds.append(axis)
    axes = {
        "dates": np.arange(12) / 12,
        "state": states
        if model == "Heston"
        else np.array([0.25, 0.5, 0.75, 1, 1.5, 2, 4] if high else [0.25, 0.5, 1, 2, 4]),
        "threshold": np.array(thresholds),
    }
    if model == "local":
        axes.update(
            spot=np.geomspace(50, 200, 17 if high else 9),
            t0_spot=np.array([99.5, 99.75, 100.0, 100.25, 100.5]),
        )
    return axes


def run_teacher_grid_job(
    parameters,
    surface,
    *,
    model,
    grid,
    original_n,
    seed,
    chunk_paths,
    evaluation_domains,
    work_directory,
    wall_cap_seconds=None,
    driver=None,
    teacher_reference=None,
):
    """Execute one declared grid/N, never the entire N×grid×frequency product."""
    from deep_hedge_price import _dynamic_hedging_replay as saved_replay

    _validate_teacher_reference(teacher_reference, seed, original_n)
    _require(
        driver is None or driver.get("teacher_reference") == teacher_reference,
        "principal/reference teacher driver purpose differs",
    )
    axes = teacher_axes(grid, model)
    planned = []
    for j, _date in enumerate(axes["dates"]):
        spots = (axes["t0_spot"] if j == 0 else axes["spot"]) if model == "local" else [100.0]
        for spot in spots:
            for state in axes["state"]:
                planned.append({"date_index": j, "spot": float(spot), "state": float(state)})
    nodes = []
    start, cpu = perf_counter(), process_time()
    for i, node in enumerate(planned):
        if wall_cap_seconds is not None and perf_counter() - start >= wall_cap_seconds:
            break
        remaining = (
            None if wall_cap_seconds is None else wall_cap_seconds - (perf_counter() - start)
        )
        raw = run_teacher_job(
            parameters,
            surface,
            model=model,
            seed=seed,
            original_n=original_n,
            chunk_paths=chunk_paths,
            calendar_times=np.arange(769) / 768,
            start_index=64 * node["date_index"],
            spot=node["spot"],
            state=node["state"],
            thresholds=axes["threshold"][node["date_index"]],
            wall_cap_seconds=remaining,
            driver=driver,
        )
        path = Path(work_directory) / f"node{i:04d}"
        write_pilot_artifact(path, raw)
        binding = _teacher_node_binding(path, raw)
        nodes.append(node | {"path": str(path), "raw_binding": binding})
        if raw.get("status") in ("failed_at_declared_cap", "unclosed_source_or_solver_defect"):
            break
    defect = (
        bool(nodes)
        and read_pilot_artifact(nodes[-1]["path"])[0].get("status")
        == "unclosed_source_or_solver_defect"
    )
    complete = len(nodes) == len(planned) and all(
        read_pilot_artifact(n["path"])[0].get("status") is None for n in nodes
    )

    def rows():
        for node in nodes:
            row, _ = read_pilot_artifact(node["path"])
            row["surface"] = surface
            yield row

    cache = None
    if complete:
        cache = saved_replay.rebuild_asian_cache(
            rows(), parameters, axes, model=model.lower(), evaluation_domains=evaluation_domains
        )["cache"]
    elapsed = perf_counter() - start
    return {
        "kind": "teacher_grid",
        "teacher_reference": copy.deepcopy(teacher_reference),
        "driver": driver,
        "model": model,
        "grid": grid,
        "original_n": original_n,
        "seed": seed,
        "axes": axes,
        "planned_nodes": planned,
        "nodes": nodes,
        "cache": cache,
        "evaluation_domains": evaluation_domains,
        "status": "unclosed_source_or_solver_defect"
        if defect
        else "executed"
        if complete
        else "failed_at_declared_cap",
        "reason": "original node solver/source defect" if defect else None,
        "unexecuted_node_count": len(planned) - len(nodes),
        "cap_evidence": None
        if complete or defect
        else {"metric": "wall_seconds", "limit": wall_cap_seconds, "consumed": elapsed},
        "expense": _expense(
            "teacher_grid_worker",
            elapsed,
            process_time() - cpu,
            failed=None if complete else "declared grid cap",
            cap=wall_cap_seconds,
        ),
        "financial_qualification": "unknown",
    }


def run_q_job(
    parameters,
    surface,
    *,
    model,
    seed,
    original_n,
    chunk_paths,
    call_cache,
    date,
    spot,
    state,
    bin_edges,
    state_id=None,
    wall_cap_seconds=None,
):
    """Actual coupled fine/half-step Q paths with every original failure retained."""
    from hullkit._dynamic_hedging_core import heston_records, local_records
    from hullkit._dynamic_hedging_surfaces import evaluate_call

    n = original_n
    times = date + np.arange(9) / 1536
    indices = np.array([0, 1, 2, 4, 8])
    recorded_times = times[indices]
    cache_indices = []
    for t in recorded_times:
        match = np.flatnonzero(np.isclose(call_cache["dates"], t, atol=1e-12, rtol=0))
        _require(len(match) == 1, "Q call cache must retain every full/half delta date")
        cache_indices.append(int(match[0]))
    S = np.full((n, 5), np.nan)
    V = np.full_like(S, np.nan)
    Q = np.full_like(S, np.nan)
    masks = np.zeros(n, dtype=bool)
    reasons = np.full(n, "not_executed", dtype="<U128")
    chunks = []
    generator = np.random.default_rng(seed)
    start, cpu = perf_counter(), process_time()
    for lo in range(0, n, chunk_paths):
        if wall_cap_seconds is not None and perf_counter() - start >= wall_cap_seconds:
            break
        hi = min(n, lo + chunk_paths)
        z = generator.standard_normal((hi - lo, 8, 2))
        sp = np.broadcast_to(spot, (n,))[lo:hi]
        st = np.broadcast_to(state, (n,))[lo:hi]
        _require(
            (hi - lo) * 8 <= 1_000_000_000 and z.nbytes <= 256 * 1024**2,
            "actual Q child path/byte cap exceeded",
        )
        S[lo:hi, 0] = sp
        V[lo:hi, 0] = st
        raw_records = []
        valid = np.ones(hi - lo, dtype=bool)
        for j, factor in enumerate((1, 2, 4, 8), start=1):
            delta = factor / 1536
            normal = z[:, :factor].sum(axis=1) / np.sqrt(factor)
            endpoint_times = np.array([date, date + delta])
            if model == "Heston":
                raw = heston_records(
                    parameters,
                    normal[:, None, :],
                    endpoint_times,
                    np.array([0, 1]),
                    spot=sp,
                    variance=st,
                )
                V[lo:hi, j] = raw["variance"][:, 1]
            else:
                raw = local_records(
                    parameters,
                    surface,
                    normal[:, None, :],
                    endpoint_times,
                    np.array([0, 1]),
                    spot=sp,
                    multiplier=state,
                )
                V[lo:hi, j] = st
            S[lo:hi, j] = raw["spot"][:, 1]
            valid &= raw["path_mask"]
            raw_records.append({"factor": factor, "normal": normal, "records": raw})
        query_status = []
        query_reason = []
        for j, ci in enumerate(cache_indices):
            call = evaluate_call(call_cache, ci, S[lo:hi, j], V[lo:hi, j])
            Q[lo:hi, j] = call["value"]
            query_status.append(call["status"])
            query_reason.append(call["reason"])
        masks[lo:hi] = valid
        reasons[lo:hi] = np.where(valid, "ok", "original_one_step_SDE_failure")
        chunks.append(
            {
                "path_start": lo,
                "path_stop": hi,
                "normal_sha256": hashlib.sha256(z.tobytes()).hexdigest(),
                "path_steps": (hi - lo) * 4,
                "global_normal_steps": 8,
                "normal": z,
                "raw_records": raw_records,
                "call_status": np.asarray(query_status).T,
                "call_reason": np.asarray(query_reason).T,
            }
        )
    discounted = Q * np.exp(-parameters.rate * (recorded_times - date))[None, :]
    inc = discounted[:, [4, 3, 2]] - Q[:, [0]]
    half = discounted[:, [3, 2, 1]] - Q[:, [0]]
    labels = np.digitize(S[:, 0], np.asarray(bin_edges))
    errors = np.asarray(call_cache.get("price_error", np.nan))
    ref = np.full(3, float(np.max(errors))) if np.isfinite(errors).all() else np.full(3, np.nan)
    done = sum(c["path_stop"] - c["path_start"] for c in chunks)
    return {
        "kind": "Q",
        "model": model,
        "parameters": parameters,
        "surface": surface,
        "initial_spot": spot,
        "initial_state": state,
        "original_n": n,
        "path_ids": np.arange(n),
        "seed": seed,
        "state_id": state_id,
        "times": recorded_times,
        "spots": S,
        "states": V,
        "quoted_calls": Q,
        "call_cache": call_cache,
        "cache_indices": cache_indices,
        "chunks": chunks,
        "path_mask": masks,
        "failure_reasons": reasons,
        "increments": inc,
        "half_increments": half,
        "delta": np.array([1 / 192, 1 / 384, 1 / 768]),
        "bin_ids": labels,
        "bin_edges": np.asarray(bin_edges),
        "reference_error": ref,
        "rate": parameters.rate,
        "status": "executed" if done == n else "failed_at_declared_cap",
        "cap_evidence": None
        if done == n
        else {
            "metric": "wall_seconds",
            "limit": wall_cap_seconds,
            "consumed": perf_counter() - start,
        },
        "financial_qualification": "unknown",
        "expense": _expense("Q_worker", perf_counter() - start, process_time() - cpu),
    }


def run_closure_job(**arguments):
    from deep_hedge_price._dynamic_hedging_closure import training_validation_closure

    return {
        "kind": "closure",
        "inputs": arguments,
        "closure": training_validation_closure(**arguments),
        "financial_qualification": "unknown",
    }


CLOSURE_SCHEMA = "rb-f04-pilot-closure-boundaries-v1"


def write_closure_artifact(directory, raw):
    """Bind every original fit/validation/dataset/risk boundary without downsampling."""
    directory = Path(directory)
    parts = []

    def split(value, path):
        semantic = path and path[-1] in (
            "fits",
            "nn_validation",
            "baseline_validation",
            "raw_validation",
            "train_datasets",
            "validation_datasets",
            "validation_risks",
        )
        if semantic and isinstance(value, (list, dict)):
            if isinstance(value, list):
                return {
                    "container": "list",
                    "items": [split(v, (*path, str(i))) for i, v in enumerate(value)],
                }
            return {
                "container": "dict",
                "items": {k: split(v, (*path, k)) for k, v in value.items()},
            }
        # Each roster row or generator dataset is an immutable numerical boundary.
        if len(path) >= 2 and (
            path[-2]
            in (
                "fits",
                "nn_validation",
                "baseline_validation",
                "raw_validation",
                "train_datasets",
                "validation_datasets",
                "validation_risks",
            )
        ):
            identifier = f"boundary{len(parts):04d}"
            parts.append((identifier, path, value))
            return {
                "boundary": identifier,
                "path": list(path),
                "payload_sha256": runner.payload_digest(value),
            }
        if isinstance(value, dict):
            return {
                "container": "dict",
                "items": {k: split(v, (*path, k)) for k, v in value.items()},
            }
        # Nonsemantic values remain in a bounded part, including expense rosters.
        identifier = f"boundary{len(parts):04d}"
        parts.append((identifier, path, value))
        return {
            "boundary": identifier,
            "path": list(path),
            "payload_sha256": runner.payload_digest(value),
        }

    tree = split(raw, ())
    receipt = protocol.write_artifact(
        directory, metadata={"schema": CLOSURE_SCHEMA, "tree": tree}, arrays={}
    )
    for identifier, path, value in parts:
        write_pilot_artifact(directory / identifier, {"path": list(path), "value": value})
    return receipt


def read_closure_artifact(directory):
    directory = Path(directory)
    meta, arrays, receipt = protocol.read_artifact(directory)
    _require(meta["schema"] == CLOSURE_SCHEMA and not arrays, "closure envelope schema mismatch")
    used = set()

    def rebuild(value, path):
        if "boundary" in value:
            identifier = value["boundary"]
            _require(
                identifier not in used and Path(identifier).name == identifier,
                "duplicate closure boundary",
            )
            used.add(identifier)
            part, _ = read_pilot_artifact(directory / identifier)
            _require(
                part["path"] == list(path) == value["path"],
                "closure original boundary path mismatch",
            )
            _require(
                runner.payload_digest(part["value"]) == value["payload_sha256"],
                "closure original boundary payload mismatch",
            )
            return part["value"]
        if value["container"] == "list":
            return [rebuild(v, (*path, str(i))) for i, v in enumerate(value["items"])]
        _require(value["container"] == "dict", "closure container mismatch")
        return {k: rebuild(v, (*path, k)) for k, v in value["items"].items()}

    raw = rebuild(meta["tree"], ())
    _require(
        {p.name for p in directory.iterdir() if p.is_dir()} == used,
        "extra/missing original closure boundaries",
    )
    return raw, receipt


def _combine_market_chunks(chunks, n):
    first = chunks[0]
    result = dict(first)
    for key in ("prices", "memory_sum", "payoff", "cashflows", "path_mask", "reasons"):
        result[key] = np.concatenate([c[key] for c in chunks], axis=0)
    result.update(
        original_n=n,
        path_ids=np.arange(n),
        qualification="qualified"
        if all(c["qualification"] == "qualified" for c in chunks)
        else "unknown",
    )
    market = dict(first["market"])
    for key in ("spot", "variance", "path_mask", "reasons"):
        market[key] = np.concatenate([c["market"][key] for c in chunks], axis=0)
    market["diagnostics"] = {
        "original_path_count": n,
        "failed_path_count": int((~market["path_mask"]).sum()),
        "raw_chunk_diagnostics": [c["market"]["diagnostics"] for c in chunks],
    }
    result["market"] = market
    actual = dict(first["actual_call"])
    for key in ("value", "status", "reason"):
        actual[key] = np.concatenate([c["actual_call"][key] for c in chunks], axis=0)
    actual["raw"] = []
    for j in range(len(first["times"])):
        item = {}
        raw_rows = [c["actual_call"]["raw"][j] for c in chunks]
        common = set.intersection(*(set(r) for r in raw_rows))
        for key in sorted(common):
            values = [r[key] for r in raw_rows]
            if all(isinstance(v, np.ndarray) and v.ndim > 0 for v in values):
                item[key] = np.concatenate(values, axis=0)
            else:
                item[key] = values[0]
        item["raw_original_chunks"] = raw_rows
        actual["raw"].append(item)
    result["actual_call"] = actual
    result["primitives"] = {k: v for k, v in first["primitives"].items() if k != "normals"}
    result["primitives"]["raw_driver_chunks"] = [c["primitives"]["normals"] for c in chunks]
    result["diagnostics"] = {
        "original_n": n,
        "failed_count": int((~result["path_mask"]).sum()),
        "raw_chunk_diagnostics": [c["diagnostics"] for c in chunks],
    }
    return result


def run_market_pair_job(
    parameters,
    surface,
    *,
    model,
    seed,
    original_n,
    chunk_paths,
    call_cache,
    premium,
    cost_rates,
    levels=(768, 1536),
    frequencies=(12, 12),
    wall_cap_seconds=None,
):
    """Actual paired market paths from one fine stream, preserving every original path."""
    _require(tuple(levels) == (768, 1536), "original independent SDE pair changed")
    _require(
        len(frequencies) == 2 and all(f in (12, 24, 48) for f in frequencies),
        "original diagnostic frequencies changed",
    )
    _require(
        chunk_paths > 0
        and chunk_paths * 1536 * 16 < 192 * 1024**2
        and chunk_paths * 1536 <= 1_000_000_000,
        "actual paired child byte/path cap exceeded",
    )
    generator = np.random.default_rng(seed)
    rows = [[], []]
    drivers = []
    start, cpu = perf_counter(), process_time()
    for lo in range(0, original_n, chunk_paths):
        if wall_cap_seconds is not None and perf_counter() - start >= wall_cap_seconds:
            break
        hi = min(original_n, lo + chunk_paths)
        fine = generator.standard_normal((hi - lo, 1536, 2))
        coarse = fine.reshape(hi - lo, 768, 2, 2).sum(axis=2) / np.sqrt(2)
        drivers.append(
            {
                "path_start": lo,
                "path_stop": hi,
                "fine_sha256": hashlib.sha256(fine.tobytes()).hexdigest(),
                "coarse_sha256": hashlib.sha256(coarse.tobytes()).hexdigest(),
                "path_steps": [(hi - lo) * 768, (hi - lo) * 1536],
            }
        )
        for k, (normals, level, frequency) in enumerate(
            zip((coarse, fine), levels, frequencies, strict=True)
        ):
            times = np.arange(level + 1) / level
            indices = np.round(np.arange(frequency + 1) * level / frequency).astype(int)
            raw = study.market_dataset(
                model.lower(),
                parameters,
                surface,
                normals,
                times,
                indices,
                np.arange(1, 13) / 12,
                call_cache,
                premium=premium,
                cost_rates=cost_rates,
            )
            rows[k].append(raw)
    done = sum(x["path_stop"] - x["path_start"] for x in drivers)
    datasets = (
        [_combine_market_chunks(group, original_n) for group in rows]
        if done == original_n
        else None
    )
    return {
        "kind": "market_pair",
        "model": model,
        "original_n": original_n,
        "path_ids": np.arange(original_n),
        "seed": seed,
        "levels": list(levels),
        "frequencies": list(frequencies),
        "driver_map": drivers,
        "raw_chunks": rows,
        "datasets": datasets,
        "call_cache": call_cache,
        "processed_n": done,
        "unexecuted_n": original_n - done,
        "status": "executed" if done == original_n else "failed_at_declared_cap",
        "cap_evidence": None
        if done == original_n
        else {
            "metric": "wall_seconds",
            "limit": wall_cap_seconds,
            "consumed": perf_counter() - start,
        },
        "expense": _expense(
            "market_pair_worker",
            perf_counter() - start,
            process_time() - cpu,
            failed=None if done == original_n else "declared market pair cap",
            cap=wall_cap_seconds,
        ),
        "financial_qualification": "unknown",
    }


def write_pilot_artifact(directory, payload):
    """Split every array into bounded immutable parts, preserving its full shape.

    The tree binds array bytes/shapes and exact part coverage. Byte identities
    establish provenance only, not numerical accuracy.
    """
    directory = Path(directory)
    payload, storage_descriptor = teacher_storage.prepare_teacher(payload)
    arrays = {}
    tree = runner._encode_tree(payload, arrays)
    descriptors, packs = {}, []
    limit = 128 * 1024**2
    pack, entries, expanded = {}, {}, 0
    for key, raw in arrays.items():
        array = raw.copy() if raw.ndim == 0 else np.ascontiguousarray(raw)
        _require(array.dtype.kind != "O", "object array prohibited")
        if array.ndim == 0:
            slices = [(0, 1, array)]
        else:
            row_bytes = max(1, array[0:1].nbytes)
            _require(row_bytes < limit, "one array row exceeds part limit")
            rows = max(1, limit // row_bytes)
            slices = [
                (lo, min(len(array), lo + rows), array[lo : lo + rows])
                for lo in range(0, len(array), rows)
            ] or [(0, 0, array)]
        refs = []
        for lo, hi, value in slices:
            if pack and (expanded + value.nbytes > limit or len(pack) >= 4096):
                packs.append((pack, entries))
                pack, entries, expanded = {}, {}, 0
            value_key = f"value{len(pack):06d}"
            identifier = f"pack{len(packs):06d}"
            refs.append({"id": identifier, "value_key": value_key, "start": lo, "stop": hi})
            pack[value_key] = value
            entries[value_key] = {"array": key, "start": lo, "stop": hi}
            expanded += value.nbytes
        descriptors[key] = {
            "shape": list(array.shape),
            "dtype": array.dtype.str,
            "sha256": hashlib.sha256(array.tobytes()).hexdigest(),
            "parts": refs,
        }
    if pack:
        packs.append((pack, entries))
    metadata = {"schema": PACK_SCHEMA, "tree": tree, "arrays": descriptors}
    if storage_descriptor is not None:
        metadata["teacher_storage"] = storage_descriptor
    receipt = protocol.write_artifact(directory, metadata=metadata, arrays={})
    for index, (values, entries) in enumerate(packs):
        identifier = f"pack{index:06d}"
        protocol.write_artifact(
            directory / identifier,
            metadata={"schema": PACK_SCHEMA, "part": identifier, "entries": entries},
            arrays=values,
            compress=storage_descriptor is not None,
        )
    return receipt


def _teacher_node_binding(directory, raw):
    """New recipes bind physical origin; legacy literals keep their raw digest."""
    metadata, _, _ = protocol.read_artifact(directory)
    if "teacher_storage" in metadata:
        teacher_storage.check_returned_origin(raw, metadata["teacher_storage"])
        return teacher_storage.physical_artifact_binding(directory)
    return {"kind": "literal_payload_v1", "raw_sha256": runner.payload_digest(raw)}


def _check_teacher_node_binding(node, directory, raw):
    """A declared physical kind never falls back to floating payload hashes."""
    if "raw_binding" not in node:
        _require(
            runner.payload_digest(raw) == node["raw_sha256"],
            "teacher raw node binding mismatch",
        )
        return
    binding = node["raw_binding"]
    _require(
        isinstance(binding, dict)
        and binding.get("kind") in ("teacher_recipe_physical_v1", "literal_payload_v1"),
        "unknown teacher node binding kind",
    )
    _require(binding == _teacher_node_binding(directory, raw), "teacher raw node binding mismatch")


def _read_packed_pilot(directory, metadata, receipt):
    arrays, packs, used = {}, {}, {}
    for key, descriptor in metadata["arrays"].items():
        parts, stop = [], 0
        for ref in descriptor["parts"]:
            _require(ref["start"] == stop, "array part gap or reorder")
            identifier, value_key = ref["id"], ref["value_key"]
            _require(Path(identifier).name == identifier, "invalid pack identifier")
            if identifier not in packs:
                packs[identifier] = protocol.read_artifact(directory / identifier)
                used[identifier] = set()
            meta, values, _ = packs[identifier]
            _require(
                meta["schema"] == PACK_SCHEMA
                and meta["part"] == identifier
                and meta["entries"].get(value_key)
                == {"array": key, "start": ref["start"], "stop": ref["stop"]},
                "packed original array identity mismatch",
            )
            _require(value_key not in used[identifier], "repeated packed array entry")
            used[identifier].add(value_key)
            value, shape = values[value_key], descriptor["shape"]
            expected = (ref["stop"] - ref["start"], *shape[1:]) if shape else ()
            _require(
                value.shape == expected and value.dtype.str == descriptor["dtype"],
                "packed original shape/dtype mismatch",
            )
            parts.append(value)
            stop = ref["stop"]
        array = np.concatenate(parts, axis=0) if descriptor["shape"] else parts[0]
        _require(
            list(array.shape) == descriptor["shape"]
            and hashlib.sha256(array.tobytes()).hexdigest() == descriptor["sha256"],
            "packed original array bytes/shape mismatch",
        )
        arrays[key] = array
    _require(
        {p.name for p in directory.iterdir() if p.is_dir()} == set(packs),
        "extra or missing original packs",
    )
    for identifier, (meta, values, _) in packs.items():
        _require(
            used[identifier] == set(values) == set(meta["entries"]),
            "extra/unreferenced packed raw array",
        )
    used_arrays = set()
    payload = runner._decode_tree(metadata["tree"], arrays, used_arrays)
    _require(used_arrays == set(arrays), "unused packed raw array")
    return payload, receipt


def read_pilot_artifact(directory):
    """Load bounded parts; reject gaps, reordered indices, or tampered array bytes."""
    directory = Path(directory)
    metadata, root_arrays, root_receipt = protocol.read_artifact(directory)
    _require(not root_arrays, "unexpected root raw array")
    if metadata.get("schema") == CLOSURE_SCHEMA:
        return read_closure_artifact(directory)
    if metadata.get("schema") == PACK_SCHEMA:
        payload, receipt = _read_packed_pilot(directory, metadata, root_receipt)
        if "teacher_storage" in metadata:
            payload = teacher_storage.restore_teacher(payload, metadata["teacher_storage"])
        return payload, receipt
    _require(metadata["schema"] == PART_SCHEMA, "not a pilot split artifact")
    arrays = {}
    expected_dirs = set()
    for key, descriptor in metadata["arrays"].items():
        parts, stop = [], 0
        for ref in descriptor["parts"]:
            _require(ref["start"] == stop, "array part gap or reorder")
            identifier = ref["id"]
            _require(
                identifier not in expected_dirs and Path(identifier).name == identifier,
                "invalid repeated array part",
            )
            expected_dirs.add(identifier)
            part_meta, values, _ = _read_artifact_parts(directory / identifier)
            _require(
                part_meta == {"schema": PART_SCHEMA, "array": key, "part": identifier},
                "part identity mismatch",
            )
            value = values["value"]
            shape = descriptor["shape"]
            _require(value.dtype.str == descriptor["dtype"], "part dtype mismatch")
            if shape:
                _require(
                    value.shape == (ref["stop"] - ref["start"], *shape[1:]),
                    "part original shape mismatch",
                )
            else:
                _require(value.shape == (), "scalar part shape mismatch")
            parts.append(value)
            stop = ref["stop"]
        array = np.concatenate(parts, axis=0) if descriptor["shape"] else parts[0]
        _require(list(array.shape) == descriptor["shape"], "original array shape mismatch")
        _require(
            hashlib.sha256(array.tobytes()).hexdigest() == descriptor["sha256"],
            "original array bytes mismatch",
        )
        arrays[key] = array
    actual_dirs = {p.name for p in directory.iterdir() if p.is_dir()}
    _require(actual_dirs == expected_dirs, "extra or missing raw array parts")
    used = set()
    result = runner._decode_tree(metadata["tree"], arrays, used)
    _require(used == set(arrays), "unused raw array")
    return result, root_receipt


def _read_artifact_parts(path):
    value = protocol.read_artifact(path)
    # Existing protocol returns metadata, arrays, receipt.
    return value


def _resolve(value, inputs, results, *, planned_jobs=None):
    if isinstance(value, dict) and set(value) == {"input"}:
        return inputs[value["input"]]
    if isinstance(value, dict) and set(value) in ({"job"}, {"job", "path"}):
        target = results[value["job"]]["raw"]
        for key in value.get("path", []):
            target = target[key]
        return target
    if isinstance(value, dict) and set(value) == {"job_record"}:
        return {k: v for k, v in results[value["job_record"]].items() if k != "artifact_path"}
    if isinstance(value, dict) and set(value) == {"job_arguments"}:
        identifier = value["job_arguments"]
        _require(
            planned_jobs is not None and identifier in planned_jobs,
            "prior original job arguments required",
        )
        if results[identifier]["status"] != "executed":
            if planned_jobs[identifier]["operation"] != "teacher_selection":
                return None
            # A completed selector may exceed its cap after inspecting original work.
            # Its authenticated metadata still binds N; it supplies no numerical input.
            _teacher_selection_control_raw(results[identifier])
        return _resolve(
            planned_jobs[identifier]["arguments"], inputs, results, planned_jobs=planned_jobs
        )
    if isinstance(value, dict) and set(value) == {"field_job"}:
        return materialize_field(results[value["field_job"]]["raw"])
    if isinstance(value, dict):
        return {
            k: _resolve(v, inputs, results, planned_jobs=planned_jobs) for k, v in value.items()
        }
    if isinstance(value, list):
        return [_resolve(v, inputs, results, planned_jobs=planned_jobs) for v in value]
    return value


def _dependency_ids(value):
    """Actual declared argument dependencies; literals never imply a dependency."""
    if isinstance(value, dict):
        if set(value) in ({"job"}, {"job", "path"}):
            return {value["job"]}
        if set(value) == {"field_job"}:
            return {value["field_job"]}
        if set(value) in ({"job_record"}, {"job_arguments"}):
            return {next(iter(value.values()))}
        return set().union(*(_dependency_ids(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_dependency_ids(v) for v in value))
    return set()


def _numeric_dependency_ids(value):
    """Control receipts bind real prior work, without requiring its numerical success."""
    if isinstance(value, dict):
        if set(value) in ({"job_record"}, {"job_arguments"}):
            return set()
        if set(value) in ({"job"}, {"job", "path"}):
            return {value["job"]}
        if set(value) == {"field_job"}:
            return {value["field_job"]}
        return set().union(*(_numeric_dependency_ids(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(_numeric_dependency_ids(v) for v in value))
    return set()


def _cap_parent_binding(row):
    """Bind consumed parent costs, raw and source without transferring its clock."""
    return {
        "job_id": row["id"],
        "operation": row["operation"],
        "job_payload_sha256": runner.payload_digest(
            {k: v for k, v in row.items() if k != "artifact_path"}
        ),
        "raw_sha256": runner.payload_digest(row["raw"]),
        "source_sha256": row["source_sha256"],
        "input_bindings": row["input_bindings"],
        "timing_events": row["timing_events"],
        "expense": row["expense"],
        "cap_evidence": row["cap_evidence"],
    }


def _control_receipts_allowed(job):
    return job["operation"] in ("teacher_selection", "teacher_selected_inputs") or (
        job["operation"] == "teacher_diagnostic" and job.get("original_n_source") is not None
    )


def _teacher_selection_control_raw(selector):
    """Authenticate completed selector metadata without granting cap qualification."""
    _require(
        selector["operation"] == "teacher_selection"
        and selector["status"]
        in ("executed", "failed_at_declared_cap", "unexecuted_dependency_cap"),
        "conditional original selector producer changed",
    )
    raw = (
        selector["raw"].get("selection_inspection")
        if selector["status"] == "unexecuted_dependency_cap"
        else selector["raw"]
    )
    _require(
        raw is not None and raw.get("kind") == "teacher_selection",
        "conditional original selector inspection missing",
    )
    if selector["status"] == "failed_at_declared_cap":
        cap = selector.get("cap_evidence")
        _require(
            isinstance(cap, dict)
            and cap.get("metric") == "wall_seconds"
            and np.isfinite(cap.get("limit", np.nan))
            and cap["limit"] > 0
            and np.isfinite(cap.get("consumed", np.nan))
            and cap["consumed"] >= cap["limit"]
            and selector.get("financial_qualification") == "unknown",
            "conditional selector actual cap receipt invalid",
        )
        events = selector["timing_events"]
        elapsed = (events["wall_stop_ns"] - events["wall_start_ns"]) / 1e9
        runner._same(elapsed, cap["consumed"], "conditional selector actual cap clock")
        runner._same(
            selector["expense"]["timing"]["wall_seconds"],
            elapsed,
            "conditional selector actual cap expense",
        )
    return raw


def _selector_job_n_binding(job, selector):
    source = job.get("original_n_source")
    if source is None:
        return None
    op = job["operation"]
    required = {"teacher_selection_job_id", "model"}
    _require(
        op in ("teacher_diagnostic", "teacher_selected_inputs")
        and set(source) == (required | {"purpose"} if op == "teacher_selected_inputs" else required)
        and job.get("original_n") is None,
        "conditional original-N source must be a prior typed diagnostic/adapter",
    )
    _require(
        selector["id"] == source["teacher_selection_job_id"],
        "conditional original selector producer changed",
    )
    raw = _teacher_selection_control_raw(selector)
    ladder = protocol.candidate_protocol()["teacher"]["n_candidates"]
    _require(
        raw is not None and raw["model"] == source["model"] and raw["original_n"] in ladder,
        "conditional original selector model/N changed",
    )
    n = raw["original_n"]
    if op == "teacher_selected_inputs":
        purpose = source["purpose"]
        _require(
            purpose == job["arguments"]["purpose"]
            and purpose in ("principal", "teacher_N", "teacher_grid", "extra_dates"),
            "conditional selected purpose changed",
        )
        if purpose == "teacher_N":
            n = ladder[min(ladder.index(n) + 1, len(ladder) - 1)]
    return {
        "teacher_selection_job_id": selector["id"],
        "model": source["model"],
        "selector_raw_sha256": input_identity(raw),
        "selected_original_n": raw["original_n"],
        "original_n": n,
    }


def _conditional_job_n_binding(job, results):
    source = job.get("original_n_source")
    if source is None:
        return None
    identifier = source["teacher_selection_job_id"]
    _require(identifier in results, "conditional prior selector unavailable")
    return _selector_job_n_binding(job, results[identifier])


def _prediction_for_original_n(job, n):
    prediction = job["prediction"]
    branches = prediction.get("by_original_n")
    if branches is None:
        _require(
            job.get("original_n_source") is None or job["operation"] == "teacher_selected_inputs",
            "conditional diagnostic original4N predictions missing",
        )
        return prediction
    ladder = protocol.candidate_protocol()["teacher"]["n_candidates"]
    _require(
        job["operation"] == "teacher_diagnostic"
        and job.get("original_n_source") is not None
        and set(branches) == {str(N) for N in ladder},
        "conditional diagnostic all original4N branches required",
    )
    fields = ("path_steps", "total_path_steps", "expanded_bytes")
    for N in ladder:
        branch = branches[str(N)]
        _require(
            branch["path_steps"] == N * 768
            and branch["total_path_steps"] == N * 768 * len(job["diagnostic_cases"])
            and 0
            <= branch["expanded_bytes"]
            <= protocol.candidate_protocol()["limits"]["chunk_uncompressed_bytes"]
            and branch.get("rate_source")
            in ("measured_prior_job", "independently_reviewed_estimate"),
            "conditional diagnostic prior N/work/bytes/rate changed",
        )
    _require(
        all(prediction[k] == max(row[k] for row in branches.values()) for k in fields),
        "conditional diagnostic top prediction must be conservative branch maximum",
    )
    _require(str(n) in branches, "conditional diagnostic selected N not a prior branch")
    return branches[str(n)]


def _dependency_cap_raw(job, dependencies, results):
    parents = set()
    for identifier in dependencies:
        row = results[identifier]
        if row["status"] == "failed_at_declared_cap":
            parents.add(identifier)
        elif row["status"] == "unexecuted_dependency_cap":
            parents.update(row["raw"]["parent_cap_job_ids"])
        else:
            _require(
                row["status"] == "executed"
                or (
                    _control_receipts_allowed(job)
                    and row["status"] == "not_required_after_qualified_prefix"
                ),
                "dependency source/solver defect",
            )
    _require(parents, "unexecuted dependency requires an actual consumed parent cap")
    original_binding = _conditional_job_n_binding(job, results)
    n = job.get("original_n") if original_binding is None else original_binding["original_n"]
    return {
        "kind": "unexecuted_dependency_cap",
        "planned_operation": job["operation"],
        "planned_arguments_sha256": input_identity(job["arguments"]),
        "original_n": n,
        "executed_n": 0,
        "unexecuted_n": n,
        **({"original_n_binding": original_binding} if original_binding is not None else {}),
        "dependency_job_ids": sorted(dependencies),
        "dependency_payload_sha256": {
            i: runner.payload_digest({k: v for k, v in results[i].items() if k != "artifact_path"})
            for i in sorted(dependencies)
        },
        "parent_cap_job_ids": sorted(parents),
        "parent_cap_bindings": [_cap_parent_binding(results[i]) for i in sorted(parents)],
        "financial_qualification": "unknown",
        "execution_evidence": "no numerical solver/RNG executed; actual dependency inspection only",
    }


def run_teacher_diagnostic_job(
    parameters,
    surface,
    *,
    model,
    original_n,
    seed,
    chunk_paths,
    cases,
    wall_cap_seconds=None,
    driver=None,
    selector=None,
    selected_inputs=None,
):
    """Execute only the fixed1/24 or1/48 representative restarts, keeping12 main separate."""
    if selector is not None or selected_inputs is not None:
        _require(
            selector is not None
            and selected_inputs is not None
            and selected_inputs["kind"] == "teacher_selected_inputs"
            and selected_inputs["purpose"] == "extra_dates"
            and selected_inputs["model"] == model
            and selected_inputs["availability"] == "available"
            and selected_inputs["original_n"] == original_n
            and selector["id"] == selected_inputs["selector_job_id"]
            and input_identity(driver) == input_identity(selected_inputs["driver"]),
            "selected additional-date cache/N/driver binding changed",
        )
        _require(
            selector["status"] == "executed",
            "selected additional-date capped selector cannot execute numerical input",
        )
        selected_raw = _teacher_selection_control_raw(selector)
        _require(
            selected_raw is not None
            and selected_raw["original_n"] == original_n
            and selected_raw["model"] == model
            and input_identity(selected_raw) == selected_inputs["selector_raw_sha256"],
            "selected additional-date original selector denominator changed",
        )
    _require(
        cases and len({r["id"] for r in cases}) == len(cases),
        "prior additional exact-date IDs required",
    )
    rows = []
    begin, cpu = perf_counter(), process_time()
    for case in cases:
        date = case["date"]
        _require(
            any(np.isclose(date, t) for t in (1 / 24, 1 / 48))
            and case["spot"] == 100.0
            and case["memory_count"] == 0
            and case["memory_sum"] == 0,
            "approved additional representative state changed",
        )
        if wall_cap_seconds is not None and perf_counter() - begin >= wall_cap_seconds:
            break
        remaining = (
            None if wall_cap_seconds is None else wall_cap_seconds - (perf_counter() - begin)
        )
        raw = run_teacher_job(
            parameters,
            surface,
            model=model,
            seed=seed,
            original_n=original_n,
            chunk_paths=chunk_paths,
            calendar_times=np.arange(769) / 768,
            start_index=round(date * 768),
            spot=case["spot"],
            state=case["state"],
            thresholds=case["thresholds"],
            wall_cap_seconds=remaining,
            driver=driver,
        )
        rows.append({"case": case, "teacher": raw})
        if raw.get("status") == "failed_at_declared_cap":
            break
    complete = len(rows) == len(cases) and all(r["teacher"].get("status") is None for r in rows)
    elapsed = perf_counter() - begin
    return {
        "kind": "teacher_diagnostic",
        "driver": driver,
        **(
            {"selector": selector, "selected_inputs": selected_inputs}
            if selector is not None
            else {}
        ),
        "model": model,
        "original_n": original_n,
        "seed": seed,
        "cases": cases,
        "rows": rows,
        "unexecuted_case_count": len(cases) - len(rows),
        "status": "executed" if complete else "failed_at_declared_cap",
        "cap_evidence": None
        if complete
        else {"metric": "wall_seconds", "limit": wall_cap_seconds, "consumed": elapsed},
        "expense": _expense(
            "additional_exact_teacher",
            elapsed,
            process_time() - cpu,
            failed=None if complete else "declared diagnostic cap",
            cap=wall_cap_seconds,
        ),
        "financial_qualification": "unknown",
    }


def bump_query_chunk(
    dataset, caches, *, model, date_index, path_start, path_stop, spot_bump, quote_bump
):
    """Refit all13 S/Q queries over the original common call domain before Asian patch."""
    from hullkit._dynamic_hedging_surfaces import evaluate_asian, fit_quote_state

    call = dict(caches[model]["call"])
    asian = caches[model]["asian"]
    call["asian_state_bounds"] = [float(asian["state_nodes"][0]), float(asian["state_nodes"][-1])]
    date = dataset["times"][date_index]
    ci = np.flatnonzero(np.isclose(call["dates"], date, atol=1e-12, rtol=0))
    ai = np.flatnonzero(np.isclose(asian["dates"], date, atol=1e-12, rtol=0))
    _require(len(ci) == len(ai) == 1, "one exact call/Asian date required; no time interpolation")
    sl = slice(path_start, path_stop)
    spots = dataset["prices"][sl, date_index, 0]
    quotes = dataset["prices"][sl, date_index, 1]
    memory = dataset["memory_sum"][sl, date_index]
    counts = np.broadcast_to(dataset["memory_count"], dataset["prices"].shape[:2])[sl, date_index]
    queries = [(spots, quotes)]
    for width in (1.0, 0.5, 2.0):
        queries.extend([(spots + spot_bump * width, quotes), (spots - spot_bump * width, quotes)])
    for width in (1.0, 0.5, 2.0):
        queries.extend([(spots, quotes + quote_bump * width), (spots, quotes - quote_bump * width)])
    records = []
    for S, Q in queries:
        # The known linear branch is an exact input identity, preserving the source branch.
        linear = memory >= 1200.0
        fits = []
        claims = []
        for i in range(len(S)):
            if linear[i]:
                fit = {
                    "status": "not_required_linear_claim",
                    "reason": "exact_original_memory",
                    "state": np.nan,
                    "root": np.nan,
                    "residual": np.nan,
                    "Ctheta": np.nan,
                    "condition": np.nan,
                    "roots": np.array([]),
                }
            else:
                fit = fit_quote_state(
                    call, int(ci[0]), S[i], Q[i], state_scale=0.04 if model == "heston" else 1.0
                )
            claim = evaluate_asian(asian, int(ai[0]), S[i], fit["state"], memory[i], int(counts[i]))
            fits.append(fit)
            claims.append(claim)
        records.append(
            {
                "spots": S,
                "quotes": Q,
                "fits": fits,
                "claims": claims,
                "prices": np.asarray([row["value"] for row in claims]),
            }
        )
    return {
        "model": model,
        "date_index": date_index,
        "path_start": path_start,
        "path_stop": path_stop,
        "memory_sum": memory,
        "memory_count": counts,
        "queries": records,
    }


def bump_risk_variants(base_risk, prices, *, spot_bump, quote_bump, parameters, dataset):
    """Same traded-call covariance; only scalar-cache price FD targets are replaced."""
    import copy

    from hullkit._dynamic_hedging_risk import stock_only_target

    variants = []
    for w, width in enumerate((1.0, 0.5, 2.0)):
        risk = copy.deepcopy(base_risk)
        for model, row in risk["models"].items():
            p = prices[model]
            target = np.stack(
                [
                    (p[1 + 2 * w] - p[2 + 2 * w]) / (2 * spot_bump * width),
                    (p[7 + 2 * w] - p[8 + 2 * w]) / (2 * quote_bump * width),
                ],
                axis=-1,
            )
            valid = np.isfinite(target).all(axis=-1)
            linear = row["linear_claim"]
            u1 = stock_only_target(
                {"stock": target[..., 0], "call": target[..., 1], "valid": valid},
                row["call_spot_derivative"],
                row["call_state_derivative"],
                model=model,
                spot=dataset["prices"][:, :-1, 0],
                xi=parameters.xi,
                rho=parameters.rho,
            )
            u1[linear] = target[..., 0][linear]
            row["u2_target"] = target
            row["u1_target"] = u1
            row["arithmetic_valid"] &= valid & np.isfinite(u1)
            row["band_arithmetic_valid"] &= row["arithmetic_valid"]
            row["qualification"] = np.where(
                row["arithmetic_valid"], row["qualification"], "unknown"
            )
            row["band_qualification"] = np.where(
                row["band_arithmetic_valid"], row["band_qualification"], "unknown"
            )
            row["within_cache_bump_width"] = width
        risk["position_method"] = "full-common-call-domain refit scalar-cache finite difference"
        variants.append(risk)
    return variants


def run_bump_risk_job(
    parameters,
    dataset,
    caches,
    base_risk,
    *,
    spot_bump=0.02,
    quote_bump=1e-4,
    chunk_paths=256,
    wall_cap_seconds=None,
):
    """All original market paths/dates/13 queries; a cap keeps every unexecuted target NaN.

    This measures cache position arithmetic, not independent MC truth. Teacher
    N/grid/SDE bias and the selected18×2 direct oracle remain separate obligations.
    """
    _require(
        spot_bump > 0 and quote_bump > 0 and chunk_paths > 0,
        "mathematically positive bump/chunk required",
    )
    n = dataset["original_n"]
    dates = len(dataset["times"]) - 1
    _require(
        base_risk["original_n"] == n and set(caches) == {"heston", "local"},
        "original all-path position denominator changed",
    )
    prices = {m: np.full((13, n, dates), np.nan) for m in ("heston", "local")}
    chunks = []
    begin, cpu = perf_counter(), process_time()
    stopped = False
    for model in ("heston", "local"):
        for di in range(dates):
            for lo in range(0, n, chunk_paths):
                if wall_cap_seconds is not None and perf_counter() - begin >= wall_cap_seconds:
                    stopped = True
                    break
                hi = min(n, lo + chunk_paths)
                raw = bump_query_chunk(
                    dataset,
                    caches,
                    model=model,
                    date_index=di,
                    path_start=lo,
                    path_stop=hi,
                    spot_bump=spot_bump,
                    quote_bump=quote_bump,
                )
                prices[model][:, lo:hi, di] = [q["prices"] for q in raw["queries"]]
                chunks.append(raw)
            if stopped:
                break
        if stopped:
            break
    elapsed = perf_counter() - begin
    variants = bump_risk_variants(
        base_risk,
        prices,
        spot_bump=spot_bump,
        quote_bump=quote_bump,
        parameters=parameters,
        dataset=dataset,
    )
    executed = sum((r["path_stop"] - r["path_start"]) * 13 for r in chunks)
    return {
        "kind": "bump_risk",
        "parameters": parameters,
        "dataset": dataset,
        "caches": caches,
        "base_risk": base_risk,
        "spot_bump": spot_bump,
        "quote_bump": quote_bump,
        "width_multipliers": [1.0, 0.5, 2.0],
        "selected_width_index": 1,
        "chunk_paths": chunk_paths,
        "original_n": n,
        "path_ids": np.arange(n),
        "prices": prices,
        "chunks": chunks,
        "risk_variants": variants,
        "value": variants[1],
        "original_query_path_count": 2 * 13 * n * dates,
        "executed_query_path_count": executed,
        "unexecuted_query_path_count": 2 * 13 * n * dates - executed,
        "status": "failed_at_declared_cap" if stopped else "executed",
        "cap_evidence": None
        if not stopped
        else {"metric": "wall_seconds", "limit": wall_cap_seconds, "consumed": elapsed},
        "expense": _expense(
            "all_path_scalar_cache_bump",
            elapsed,
            process_time() - cpu,
            failed="declared position cap" if stopped else None,
            cap=wall_cap_seconds,
        ),
        "scope": "within-cache full-root/refit FD; no MC truth certification",
        "financial_qualification": "unknown",
    }


def run_precision_job(
    *, datasets, risks, validation, stream_receipts, original_n, wall_cap_seconds=None
):
    """Actual16 Greek/band cells×3 pilot streams; never open a main test stream."""
    slots = [
        r for r in protocol.study_roster()["primary_cells"] if r["policy"] in ("greek", "band")
    ]
    planned = [dict(identity=r, stream_slot=i) for i in range(3) for r in slots]
    rows = []
    expenses = []
    begin, cpu = perf_counter(), process_time()
    _require(len(planned) == 48, "original worst Greek/band roster changed")
    for record in planned:
        if wall_cap_seconds is not None and perf_counter() - begin >= wall_cap_seconds:
            break
        identity = record["identity"]
        g = identity["generator"]
        u = identity["universe"]
        index = record["stream_slot"]
        data = datasets[g][index]
        risk = risks[g][index]
        _require(
            data["original_n"] == original_n and risk["original_n"] == original_n,
            "original precision denominator changed",
        )
        selected = validation[g + ":" + u]
        width = 0.0
        if identity["policy"] == "band":
            identifier = selected["selected_bands"][identity["valuation"]]
            if identifier is None:
                result = study._unknown_rollout(data, "all original band candidates failed")
            else:
                _require(
                    identifier
                    in {r["id"] for r in selected["candidates"] if r["status"] == "completed"},
                    "selected band not from full validation",
                )
                width = float(identifier.split(":width")[1])
                result = study.policy_rollout(
                    data,
                    risk,
                    universe=u,
                    policy="band",
                    model=identity["valuation"].lower(),
                    width=width,
                )
        else:
            result = study.policy_rollout(
                data, risk, universe=u, policy="greek", model=identity["valuation"].lower()
            )
        rows.append(record | {"width": width, "result": result})
        expenses.append(
            dict(
                result["expense"],
                id="precision:" + str(index) + ":" + identity["id"],
                scope="original_Greek_band_precision",
                parent_id="precision_worker",
            )
        )
    elapsed = perf_counter() - begin
    complete = len(rows) == len(planned)
    return {
        "kind": "precision",
        "original_n": original_n,
        "datasets": datasets,
        "risks": risks,
        "validation": validation,
        "stream_receipts": stream_receipts,
        "planned_cells": planned,
        "rows": rows,
        "unexecuted_cell_count": len(planned) - len(rows),
        "status": "executed" if complete else "failed_at_declared_cap",
        "expenses": [
            _expense(
                "precision_worker",
                elapsed,
                process_time() - cpu,
                failed=None if complete else "declared precision cap",
                cap=wall_cap_seconds,
            ),
            *expenses,
        ],
        "cap_evidence": None
        if complete
        else {"metric": "wall_seconds", "limit": wall_cap_seconds, "consumed": elapsed},
        "financial_qualification": "unknown",
    }


def run_tiny_fits_job(
    train_datasets, validation_datasets, validation_risks, *, pilot_training_config, stream_receipts
):
    """Four actual init11 pilots; their explicit config is separate from main12."""
    import copy

    from deep_hedge_price._dynamic_hedging_closure import _validate_nn
    from deep_hedge_price._dynamic_hedging_policy import fit_policy

    candidate = copy.deepcopy(protocol.candidate_protocol())
    candidate["training"] = dict(pilot_training_config)
    config = candidate["training"]
    _require(
        config["device"] == "cpu"
        and config["dtype"] == "float64"
        and config["architecture"] == [9, 32, 32, 2]
        and config["activation"] == "tanh"
        and config["optimizer"] == "Adam",
        "original tiny architecture changed",
    )
    _require(
        config["original_n"] >= 16
        and config["updates"] > 0
        and config["batch_size"] > 0
        and config["cap_seconds"] > 0,
        "prior explicit tiny sizes and cap required",
    )
    _require(
        set(train_datasets) == set(validation_datasets) == {"Heston", "local"},
        "tiny original generator roster changed",
    )
    fits, training_rows, validation, expenses = [], [], [], []
    for slot in protocol.study_roster()["fits"]:
        if slot["initialization"] != 11:
            continue
        begin, cpu = perf_counter(), process_time()
        data = train_datasets[slot["training_generator"]]
        _require(data["original_n"] == config["original_n"], "tiny original N changed")
        row = dict(
            slot,
            attempted=True,
            original_n=data["original_n"],
            requested_updates=config["updates"],
            raw_fit=None,
            checkpoint_id=None,
        )
        try:
            raw = fit_policy(
                data,
                universe=slot["universe"],
                seed=11,
                updates=config["updates"],
                batch_size=config["batch_size"],
                learning_rate=config["learning_rate"],
                cap_seconds=config["cap_seconds"],
            )
            complete = raw["status"] == "completed" and raw["complete"]
            raw.update(
                training_generator=slot["training_generator"],
                fit_id=slot["id"],
                checkpoint_id=candidate["hedging"]["checkpoint_rule"] if complete else None,
            )
            row.update(
                status="completed" if complete else "failed",
                reason=raw["reason"],
                updates=raw["updates"],
                raw_fit=raw,
                checkpoint_id=raw["checkpoint_id"],
            )
        except (ValueError, KeyError, RuntimeError, FloatingPointError) as error:
            row.update(status="failed", reason=f"{type(error).__name__}: {error}", updates=0)
        elapsed = perf_counter() - begin
        row.update(
            elapsed_seconds=elapsed,
            cap_seconds=config["cap_seconds"],
            overrun_seconds=max(0.0, elapsed - config["cap_seconds"]),
        )
        if elapsed > config["cap_seconds"]:
            row.update(status="failed", reason="inclusive tiny fit cap", checkpoint_id=None)
        expense = _expense(
            "tiny:" + slot["id"],
            elapsed,
            process_time() - cpu,
            failed=None if row["status"] == "completed" else row["reason"],
            cap=config["cap_seconds"],
        )
        row["expense"] = expense
        expenses.append(expense)
        training_rows.append(row)
        val, closed = _validate_nn(
            row, validation_datasets[slot["training_generator"]], data, candidate
        )
        fits.append(closed)
        validation.append(val)
        expenses.append(val["expense"])
    return {
        "kind": "tiny_fits",
        "candidate": candidate,
        "original_n": config["original_n"],
        "pilot_training_config": config,
        "stream_receipts": stream_receipts,
        "train_datasets": train_datasets,
        "validation_datasets": validation_datasets,
        "validation_risks": validation_risks,
        "fits": fits,
        "training_fits": training_rows,
        "nn_validation": validation,
        "expenses": expenses,
        "original_fit_slots": 4,
        "test_opened": False,
        "financial_qualification": "unknown",
    }


def run_date_gate_job(parameters, surface, *, model, call_cache, asian_cache, date_index, queries):
    """Use predeclared exact-date observable queries and the same16 block operator."""
    from hullkit._dynamic_hedging_risk import quote_positions
    from hullkit._dynamic_hedging_surfaces import evaluate_asian, evaluate_call, fit_quote_state

    _require(
        queries and len({q["id"] for q in queries}) == len(queries), "prior date query IDs required"
    )
    call = dict(call_cache)
    call["asian_state_bounds"] = [
        float(asian_cache["state_nodes"][0]),
        float(asian_cache["state_nodes"][-1]),
    ]
    rows = []
    for q in queries:
        fit = fit_quote_state(
            call, date_index, q["spot"], q["quote"], state_scale=0.04 if model == "Heston" else 1.0
        )
        claim = evaluate_asian(
            asian_cache, date_index, q["spot"], fit["state"], q["memory_sum"], q["memory_count"]
        )
        traded = evaluate_call(call, date_index, q["spot"], fit["state"])
        block = claim.get("block_values")
        values = None
        if block is not None:
            block = np.asarray(block)
            positions = quote_positions(
                block[:, 1], block[:, 2], traded["spot_derivative"], traded["state_derivative"]
            )
            values = np.column_stack([block[:, 0], positions["stock"], positions["call"]])
        rows.append(dict(query=q, fit=fit, claim=claim, traded=traded, block_gate_values=values))
    return {
        "kind": "date_gate",
        "model": model,
        "date_index": date_index,
        "queries": queries,
        "call_cache": call,
        "asian_cache": asian_cache,
        "rows": rows,
        "original_n": asian_cache["N"],
        "financial_qualification": "unknown",
    }


def run_empty_claim_job(q_record):
    """A real zero-claim unit-call cash account on every saved original Q path."""
    from hullkit._dynamic_hedging_core import cash_account

    n = q_record["original_n"]
    rows = []
    for column in (4, 3, 2):
        prices = np.column_stack(
            [q_record["quoted_calls"][:, 0], q_record["quoted_calls"][:, column]]
        )[:, :, None]
        times = q_record["times"][[0, column]]
        # Zero initial cash: the call holding is financed by its original mid.
        raw = cash_account(
            times,
            prices,
            np.ones((n, 1, 1)),
            np.zeros(n),
            premium=0.0,
            rate=q_record["rate"],
            cashflows=np.zeros_like(prices),
            cost_rates=np.zeros(1),
        )
        rows.append({"column": column, "times": times, "prices": prices, "raw": raw})
    return {
        "kind": "empty_claim",
        "Q": q_record,
        "rows": rows,
        "original_n": n,
        "path_ids": np.arange(n),
        "financial_qualification": "unknown",
    }


def pack_inputs(value):
    """Lossless actual local field encoding for private immutable artifacts."""
    if isinstance(value, LocalVarianceGrid):
        return {
            "__pilot_local_variance_grid__": {
                "times": value.times,
                "z_nodes": value.z_nodes,
                "values": value.values,
                "parameters": value.parameters,
                "wing_boundaries": value.wing_boundaries,
                "support_mask": value.support_mask,
            }
        }
    if isinstance(value, dict):
        _require("__pilot_local_variance_grid__" not in value, "reserved actual field marker")
        return {k: pack_inputs(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [pack_inputs(v) for v in value]
    return value


def unpack_inputs(value):
    if isinstance(value, dict):
        if "__pilot_local_variance_grid__" in value:
            _require(set(value) == {"__pilot_local_variance_grid__"}, "mixed actual field encoding")
            row = value["__pilot_local_variance_grid__"]
            field = LocalVarianceGrid(
                row["times"],
                row["z_nodes"],
                row["values"],
                row["parameters"],
                row["wing_boundaries"],
            )
            _require(
                np.array_equal(field.support_mask, row["support_mask"]),
                "original field support encoding differs",
            )
            return field
        return {k: unpack_inputs(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unpack_inputs(v) for v in value]
    return value


def _saved_operation(operation, arguments, function):
    return {
        "kind": operation,
        "arguments": pack_inputs(arguments),
        "value": function(**arguments),
        "financial_qualification": "unknown",
    }


def _dispatch(operation, arguments):
    # Closed dispatch: no trusted user-returned success callbacks.
    if operation == "teacher_selected_inputs":
        return run_teacher_selected_inputs_job(**arguments)
    if operation == "teacher_selection":
        return run_teacher_selection_job(**arguments)
    if operation == "teacher_domain_selection":
        return run_teacher_domain_selection_job(**arguments)
    if operation == "teacher_candidate_gate":
        return run_teacher_candidate_gate_job(**arguments)
    if operation == "market_pair":
        return run_market_pair_job(**arguments)
    if operation == "closure":
        return run_closure_job(**arguments)
    if operation == "call_table":
        from reference_methods import independent_call_table

        return independent_call_table(**arguments)
    if operation == "teacher_grid":
        return run_teacher_grid_job(**arguments)
    if operation == "teacher_driver":
        return run_teacher_driver_job(**arguments)
    if operation == "Q":
        return run_q_job(**arguments)
    if operation == "bump_risk":
        return run_bump_risk_job(**arguments)
    if operation == "teacher_diagnostic":
        return run_teacher_diagnostic_job(**arguments)
    if operation == "precision":
        return run_precision_job(**arguments)
    if operation == "tiny_fits":
        return run_tiny_fits_job(**arguments)
    if operation == "date_gate":
        return run_date_gate_job(**arguments)
    if operation == "empty_claim":
        return run_empty_claim_job(**arguments)
    if operation == "call_cache":
        from hullkit._dynamic_hedging_surfaces import build_call_cache

        return _saved_operation(operation, arguments, build_call_cache)
    if operation == "quotes":
        return run_quotes_job(**arguments)
    if operation == "field":
        return run_field_job(**arguments)
    if operation == "asian_cache":
        return run_cache_job(**arguments)
    if operation == "state":
        return run_state_job(**arguments)
    if operation == "paired_pnl":
        return run_paired_pnl_job(**arguments)
    if operation == "cell_pair":
        return run_cell_pair_job(**arguments)
    if operation == "teacher":
        return run_teacher_job(**arguments)
    if operation == "oracle":
        from reference_methods import quote_positions_oracle

        return quote_positions_oracle(**arguments)
    if operation == "premium":
        from reference_methods import premium_reference

        return premium_reference(**arguments)
    if operation == "market":
        return _saved_operation(operation, arguments, study.market_dataset)
    if operation == "quote_risk":
        return run_quote_risk_job(**arguments)
    if operation == "frequency_cache":
        return run_frequency_cache_job(**arguments)
    if operation == "stream_receipts":
        return run_stream_receipts_job(**arguments)
    if operation == "policy":
        return {"dataset": arguments["dataset"], "rollout": study.policy_rollout(**arguments)}
    if operation == "fits":
        return _saved_operation(operation, arguments, study.fit_roster)
    if operation == "validation":
        return _saved_operation(operation, arguments, study.select_validation)
    if operation == "roster":
        return _saved_operation(operation, arguments, study.test_roster)
    if operation == "source":
        return _pilot_source(arguments.get("source_root", ROOT))
    if operation == "initial_quotes":
        from check_initial_quotes import check_initial_quotes

        return arguments | {"check": check_initial_quotes(**arguments)}
    if operation == "selected_calls":
        from check_selected_calls import check_selected_calls

        return arguments | {"check": check_selected_calls(**arguments)}
    raise ValueError(f"unsupported actual pilot operation: {operation}")


def teacher_domain_rule(model):
    """The approved prior computational-support rule, never a precision gate."""
    _require(model in ("Heston", "local"), "original teacher domain model required")
    return {
        "schema": "rb-f04-teacher-domain-rule-v1",
        "model": model,
        "minimum_nodes_per_axis": 4,
        "finite_requirement": "f_and_all16blocks_all3components",
        "objective": "maximum_original_node_count",
        "tie_break": "lexicographic_half_open_axis_ranges",
        "anchors": {
            "state": 0.04 if model == "Heston" else 1.0,
            **({"spot": 100.0} if model == "local" else {}),
            "threshold": "12_minus_memory_count",
        },
        "qualification_scope": "computational_support_candidate_only",
    }


def _maximum_anchor_finite_box(mask, axes, anchors):
    """Enumerate prefix-axis intervals; maximal threshold run is then exact."""
    from itertools import product

    choices = []
    for axis, anchor in zip(axes[:-1], anchors[:-1], strict=True):
        choices.append(
            [
                (a, b)
                for a in range(len(axis))
                for b in range(a + 4, len(axis) + 1)
                if axis[a] <= anchor <= axis[b - 1]
            ]
        )
    threshold = axes[-1]
    anchor = anchors[-1]
    if not threshold[0] <= anchor <= threshold[-1]:
        return None
    left = int(np.searchsorted(threshold, anchor, side="right") - 1)
    right = int(np.searchsorted(threshold, anchor, side="left"))
    best = None
    best_key = None
    for prefix in product(*choices):
        slices = tuple(slice(a, b) for a, b in prefix)
        allowed = np.all(mask[slices], axis=tuple(range(mask.ndim - 1)))
        if not np.all(allowed[left : right + 1]):
            continue
        a, b = left, right + 1
        while a > 0 and allowed[a - 1]:
            a -= 1
        while b < len(threshold) and allowed[b]:
            b += 1
        if b - a < 4:
            continue
        ranges = (*prefix, (a, b))
        volume = int(np.prod([stop - start for start, stop in ranges]))
        key = (-volume, tuple(v for pair in ranges for v in pair))
        if best_key is None or key < best_key:
            best, best_key = ranges, key
    return best


def run_teacher_domain_selection_job(*, teacher, selection_rule):
    """Choose one immutable finite box per exact date from full original arrays."""
    from hullkit._dynamic_hedging_surfaces import _asian_evaluation_domains

    model = teacher["model"]
    runner._same(teacher_domain_rule(model), selection_rule, "prior teacher domain rule/anchors")
    cache = teacher["cache"]
    _require(cache is not None, "domain choice requires actual original full teacher cache")
    names = (["spot"] if model == "local" else []) + ["state", "threshold"]
    domains = []
    masks = []
    anchors = []
    for j, date in enumerate(cache["dates"]):
        sheet = cache.get("t0_sheet") if model == "local" and date == 0 else None
        values = sheet["f"] if sheet is not None else cache["f"][j]
        blocks = sheet["block_means"] if sheet is not None else cache["block_means"][j]
        _require(blocks.shape == (*values.shape, 16, 3), "full original domain16blocks required")
        mask = np.isfinite(values) & np.all(np.isfinite(blocks), axis=(-2, -1))
        axes = (
            [sheet["spot_nodes"] if sheet is not None else cache["spot_nodes"]]
            if model == "local"
            else []
        ) + [cache["state_nodes"], cache["threshold_nodes"][j]]
        anchor = ([100.0] if model == "local" else []) + [
            selection_rule["anchors"]["state"],
            float(12 - cache["memory_counts"][j]),
        ]
        ranges = _maximum_anchor_finite_box(mask, axes, anchor)
        domains.append(
            None
            if ranges is None
            else {name: list(interval) for name, interval in zip(names, ranges, strict=True)}
        )
        masks.append(mask)
        anchors.append(dict(zip(names, anchor, strict=True)))
    selected = dict(cache)
    selected.update(
        _asian_evaluation_domains(
            domains,
            model.lower(),
            cache["dates"],
            cache["state_nodes"],
            cache["threshold_nodes"],
            cache["spot_nodes"],
            None if cache.get("t0_sheet") is None else cache["t0_sheet"]["spot_nodes"],
        )
    )
    result = dict(teacher)
    result.update(
        cache=selected,
        evaluation_domains=domains,
        financial_qualification="unknown",
        domain_selection={
            "selection_rule": copy.deepcopy(selection_rule),
            "teacher_raw_sha256": input_identity(teacher),
            "finite_node_masks": masks,
            "date_anchors": anchors,
            "evaluation_domains": copy.deepcopy(domains),
            "qualification": "unknown",
            "scope": "computational support only; original failures and allN preserved",
        },
    )
    return result


def teacher_selection_rule(model):
    _require(model in ("Heston", "local"), "original teacher selection model required")
    return {
        "schema": "rb-f04-teacher-selection-rule-v1",
        "model": model,
        "candidate_order": [
            {"original_n": n, "grid": g}
            for n in (1024, 4096, 16384, 65536)
            for g in ("coarse", "high")
        ],
        "qualified_rule": "smallest_N_coarse_first",
        "all_unknown_rule": "completed_N65536_coarse_first_research_only",
        "no_max_cache_rule": "unavailable_None_actual_parent_cap",
    }


def _teacher_selection_source_geometry(*, model, stages, teachers, drivers):
    """Authenticate prior principal/N/grid producer identities without inventing success."""
    ladder = protocol.candidate_protocol()["teacher"]["n_candidates"]
    seed = protocol.candidate_protocol()["seeds"]["teacher"][0 if model == "Heston" else 1]
    required = {
        "teacher_job_id",
        "next_teacher_job_id",
        "grid_teacher_job_id",
        "teacher_driver_job_id",
    }
    for stage in stages:
        _require(required <= set(stage), "selected stage purpose producer bindings missing")
        n, grid = stage["original_n"], stage["grid"]
        next_n = ladder[min(ladder.index(n) + 1, len(ladder) - 1)]
        expected = {
            "teacher_job_id": (n, grid, False),
            "next_teacher_job_id": (next_n, grid, n == ladder[-1]),
            "grid_teacher_job_id": (n, "high" if grid == "coarse" else "coarse", False),
        }
        if stage["job"]["status"] == "executed":
            for key in required:
                _require(
                    stage[key] == stage["arguments"]["stage_plan"][key],
                    "selected stage prior purpose producer changed",
                )
        for key, (N, g, independent) in expected.items():
            identifier = stage[key]
            _require(
                identifier in teachers and teachers[identifier]["id"] == identifier,
                "selected actual teacher purpose producer missing",
            )
            row = teachers[identifier]
            _require(
                row["operation"] == "teacher_domain_selection"
                and row["status"]
                in (
                    "executed",
                    "failed_at_declared_cap",
                    "unexecuted_dependency_cap",
                    "not_required_after_qualified_prefix",
                ),
                "selected purpose must retain typed original teacher producer",
            )
            if row["status"] != "executed":
                continue
            raw = row["raw"]
            _require(
                raw["kind"] == "teacher_grid"
                and raw["model"] == model
                and raw["original_n"] == N
                and raw["grid"] == g,
                "selected teacher purpose N/grid/model changed",
            )
            reference = raw.get("teacher_reference")
            if independent:
                _require(reference is not None, "selected maximum reference cannot use principal")
                _validate_teacher_reference(reference, raw["seed"], N)
            else:
                _require(
                    reference is None and raw["seed"] == seed,
                    "selected principal/next-prefix stream changed",
                )
            if raw["cache"] is not None:
                _require(
                    raw["cache"]["original_N"] == N and raw["cache"]["model"] == model.lower(),
                    "selected original cache denominator/model changed",
                )
        identifier = stage["teacher_driver_job_id"]
        _require(
            identifier in drivers and drivers[identifier]["id"] == identifier,
            "selected actual principal driver producer missing",
        )
        row = drivers[identifier]
        _require(
            row["operation"] == "teacher_driver"
            and row["status"]
            in (
                "executed",
                "failed_at_declared_cap",
                "unexecuted_dependency_cap",
                "not_required_after_qualified_prefix",
            ),
            "selected original driver status changed",
        )
        if row["status"] == "executed":
            driver = row["raw"]
            _require(
                driver["kind"] == "teacher_driver"
                and driver["original_n"] == n
                and driver["seed"] == seed
                and driver.get("teacher_reference") is None,
                "selected principal driver N/stream/purpose changed",
            )
            principal = teachers[stage["teacher_job_id"]]
            if principal["status"] == "executed":
                _require(
                    input_identity(principal["raw"]["driver"]) == input_identity(driver),
                    "selected actual principal driver producer substituted",
                )


def run_teacher_selected_inputs_job(
    *, model, purpose, selector, selection_arguments, teachers, drivers, artifact_context=None
):
    """Extract the exact selected purpose; retain genuine unavailable parents as None."""
    _require(
        purpose in ("principal", "teacher_N", "teacher_grid", "extra_dates"),
        "selected original teacher purpose required",
    )
    saved = _teacher_selection_control_raw(selector)
    _require(
        selection_arguments["model"] == model
        and input_identity(teachers) == input_identity(selection_arguments["teachers"])
        and input_identity(drivers) == input_identity(selection_arguments["drivers"]),
        "selected original producer control maps changed",
    )
    calculated = run_teacher_selection_job(**selection_arguments, artifact_context=artifact_context)
    runner._same(calculated, saved, "selected actual teacher selector arithmetic")
    stage = next(
        row
        for row in selection_arguments["stages"]
        if row["id"] == calculated["selected_stage_job_id"]
    )
    key = {
        "principal": "teacher_job_id",
        "extra_dates": "teacher_job_id",
        "teacher_N": "next_teacher_job_id",
        "teacher_grid": "grid_teacher_job_id",
    }[purpose]
    identifier = stage[key]
    target = teachers[identifier]
    n, grid = stage["original_n"], stage["grid"]
    ladder = protocol.candidate_protocol()["teacher"]["n_candidates"]
    target_n = ladder[min(ladder.index(n) + 1, len(ladder) - 1)] if purpose == "teacher_N" else n
    target_grid = ("high" if grid == "coarse" else "coarse") if purpose == "teacher_grid" else grid
    unavailable = [selector["id"]] if selector["status"] == "failed_at_declared_cap" else []
    cache, driver, driver_id = None, None, None
    if calculated["selection_status"] == "unavailable":
        unavailable.extend(calculated["parent_unavailable_job_ids"])
    if target["status"] != "executed":
        _require(
            target["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap"),
            "selected required purpose cannot use unused or defective teacher",
        )
        unavailable.append(identifier)
    elif not unavailable:
        _require(target["raw"]["cache"] is not None, "selected completed purpose cache missing")
        cache, driver = target["raw"]["cache"], target["raw"]["driver"]
        matching = [
            identifier
            for identifier, row in drivers.items()
            if row["status"] == "executed" and input_identity(row["raw"]) == input_identity(driver)
        ]
        _require(len(matching) == 1, "selected exact purpose driver producer missing or ambiguous")
        driver_id = matching[0]
        if purpose in ("principal", "extra_dates"):
            _require(
                driver_id == stage["teacher_driver_job_id"],
                "selected extra-date principal driver changed",
            )
        _require(
            driver["original_n"] == target_n and cache["original_N"] == target_n,
            "selected exact purpose cache/driver denominator differs",
        )
    return {
        "kind": "teacher_selected_inputs",
        "model": model,
        "purpose": purpose,
        "availability": "unavailable" if unavailable else "available",
        "original_n": target_n,
        "selected_original_n": n,
        "grid": target_grid,
        "cache": cache,
        "driver": driver,
        "selector_job_id": selector["id"],
        "selector_raw_sha256": input_identity(saved),
        "selected_stage_job_id": stage["id"],
        "selected_teacher_job_id": identifier,
        "selected_teacher_driver_job_id": driver_id,
        "selected_teacher_raw_sha256": input_identity(target["raw"]),
        "selected_teacher_driver_raw_sha256": None if driver is None else input_identity(driver),
        "parent_unavailable_job_ids": sorted(set(unavailable)),
        "financial_qualification": "unknown",
        "scope": "saved typed purpose transport only; no financial/precision qualification",
    }


def run_teacher_selection_job(
    *, model, stages, teachers, selection_rule, artifact_context=None, drivers=None
):
    """Select from actual complete stage arithmetic; never from a qualification flag."""
    from check_pilot import calculate_teacher_candidate_gate

    runner._same(
        teacher_selection_rule(model), selection_rule, "prior original teacher selection rule"
    )
    expected = selection_rule["candidate_order"]
    _require(
        [{k: r[k] for k in ("original_n", "grid")} for r in stages] == expected,
        "all original ordered teacher stages required",
    )
    _require(
        len({r["id"] for r in stages}) == len(stages), "unique original teacher stages required"
    )
    if drivers is not None:
        _teacher_selection_source_geometry(
            model=model, stages=stages, teachers=teachers, drivers=drivers
        )
    inspected = []
    qualified = {}
    chosen = None
    for stage in stages:
        row = stage["job"]
        _require(row["id"] == stage["id"], "original stage control receipt identity changed")
        status = row["status"]
        if status == "executed":
            args = stage["arguments"]
            _require(args is not None, "actual executed stage argument binding required")
            calculated = calculate_teacher_candidate_gate(
                args["parameters"],
                args.get("surface"),
                stage_plan=args["stage_plan"],
                evidence=args["evidence"],
                artifact_context=artifact_context,
            )
            runner._same(calculated, row["raw"], "actual original teacher selection stage")
            _require(
                calculated["model"] == model
                and calculated["original_n"] == stage["original_n"]
                and calculated["grid"] == stage["grid"],
                "actual original teacher stage geometry changed",
            )
            if calculated["qualification"] == "qualified":
                qualified[stage["id"]] = row["raw"]
                if chosen is None:
                    chosen = stage
        elif status == "not_required_after_qualified_prefix":
            proof = row["raw"]
            identifier = proof["lower_gate_job_id"]
            _require(
                identifier in qualified
                and proof["lower_gate_evidence_sha256"] == input_identity(qualified[identifier])
                and proof["qualified_original_n"] == qualified[identifier]["original_n"],
                "unused original stage lacks actual lower qualification",
            )
        else:
            _require(
                status in ("failed_at_declared_cap", "unexecuted_dependency_cap"),
                "source/solver defect cannot qualify teacher selection",
            )
        if status == "executed":
            for key in ("state_bindings", "date_bindings"):
                _require(
                    stage[key] == stage["arguments"]["stage_plan"][key],
                    "prior selected state/date producer roster changed",
                )
        inspected.append(
            {
                "id": stage["id"],
                "status": status,
                "raw_sha256": input_identity(row["raw"]),
                "original_n": stage["original_n"],
                "grid": stage["grid"],
            }
        )
    if chosen is None:
        candidates = [r for r in stages if r["original_n"] == 65536]
        chosen = next(
            (
                r
                for r in candidates
                if teachers[r["teacher_job_id"]]["status"] == "executed"
                and teachers[r["teacher_job_id"]]["raw"].get("cache") is not None
            ),
            None,
        )
        selection_status = "research_only_unqualified" if chosen else "unavailable"
    else:
        selection_status = "qualified_selection"
    selected = None if chosen is None else teachers[chosen["teacher_job_id"]]
    if selected is not None:
        _require(
            selected["status"] == "executed"
            and selected["raw"].get("cache") is not None
            and selected["raw"]["model"] == model
            and selected["raw"]["original_n"] == chosen["original_n"]
            and selected["raw"]["grid"] == chosen["grid"]
            and selected["raw"].get("domain_selection") is not None,
            "actual original selected finite-domain teacher missing",
        )
    unavailable = (
        [] if chosen else [r["teacher_job_id"] for r in stages if r["original_n"] == 65536]
    )
    _require(
        chosen is not None
        or all(
            teachers[i]["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap")
            for i in unavailable
        ),
        "maximum missing cache needs actual prior cap, not source fallback",
    )
    projection_stage = (
        next(r for r in stages if r["original_n"] == 65536 and r["grid"] == "coarse")
        if chosen is None
        else chosen
    )
    states = projection_stage["state_bindings"]
    dates = projection_stage["date_bindings"]
    expected_states = {
        r["id"]
        for r in execution.execution_candidate()["pilot_cases"]
        if r["kind"] == "state" and r["identity"]["model"] == model
    }
    _require(
        len(states) == 18
        and {r["id"] for r in states} == expected_states
        and len(dates) == 12
        and {r["date_index"] for r in dates} == set(range(12)),
        "selected original18states/12dates missing",
    )
    return {
        "kind": "teacher_selection",
        "model": model,
        "selection_rule": copy.deepcopy(selection_rule),
        "selection_status": selection_status,
        "original_n": 65536 if chosen is None else chosen["original_n"],
        "grid": "coarse" if chosen is None else chosen["grid"],
        "cache": None if selected is None else selected["raw"]["cache"],
        "selected_teacher_job_id": projection_stage["teacher_job_id"],
        "selected_stage_job_id": projection_stage["id"],
        "selected_state_case_job_ids": {r["id"]: r["job_id"] for r in states},
        "selected_date_job_ids": {str(r["date_index"]): r["job_id"] for r in dates},
        "selection_stage_descriptor_sha256": input_identity(
            {k: v for k, v in projection_stage.items() if k not in ("job", "arguments")}
        ),
        "selected_teacher_raw_sha256": None
        if selected is None
        else input_identity(selected["raw"]),
        "stage_inspections": inspected,
        "parent_unavailable_job_ids": unavailable,
        "financial_qualification": "unknown",
        "scope": "numerical candidate selection; no financial pilot/main certification",
    }


def run_teacher_candidate_gate_job(parameters, surface, *, stage_plan, evidence):
    """Use the saved-only whole-original-stage arithmetic for candidate selection."""
    from check_pilot import calculate_teacher_candidate_gate

    return calculate_teacher_candidate_gate(
        parameters, surface, stage_plan=stage_plan, evidence=evidence
    )


def input_identity(value):
    """Bind actual field grids and numerical inputs, not a caller's qualification flag."""
    if isinstance(value, dict):
        value = {k: input_identity(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        value = [input_identity(v) for v in value]
    elif isinstance(value, LocalVarianceGrid):
        value = {
            "type": "LocalVarianceGrid",
            "times": value.times,
            "z_nodes": value.z_nodes,
            "values": value.values,
            "parameters": value.parameters,
            "wing_boundaries": value.wing_boundaries,
            "support_mask": value.support_mask,
        }
    return runner.payload_digest(value)


def _pilot_source(source_root):
    return runner.execution_source_identity(source_root)


def _locked_bindings(inputs, plan, source_root):
    _require(set(inputs) == set(plan.get("input_bindings", {})), "original input roster changed")
    for key, value in inputs.items():
        _require(
            input_identity(value) == plan["input_bindings"][key],
            f"stale or tampered actual input: {key}",
        )
    source = _pilot_source(source_root)
    _require(
        runner.payload_digest(source) == runner.payload_digest(plan.get("source")),
        "current transitive source differs from locked pilot source",
    )
    _require(not source.get("dynamic_imports", []), "unresolved dynamic financial source")
    return source


def _job_identity(job, arguments):
    """Validate actual sizes and original streams; wrapper children retain job caps."""
    op = job["operation"]
    original = protocol.candidate_protocol()
    n = arguments.get("original_n", arguments.get("n_paths"))
    size = {"path_steps": 0}
    if op in ("teacher", "teacher_grid", "teacher_driver"):
        _require(
            n in original["teacher"]["n_candidates"],
            "small source-probe N cannot be a formal teacher job",
        )
        expected = original["seeds"]["teacher"][
            0 if job.get("driver_model", arguments.get("model")) == "Heston" else 1
        ]
        reference = arguments.get("teacher_reference")
        if reference is None:
            _require(
                job.get("teacher_reference") is None,
                "principal teacher cannot use maximum reference purpose",
            )
            _require(arguments["seed"] == expected, "formal teacher independent stream changed")
        else:
            _require(
                op in ("teacher_grid", "teacher_driver")
                and job.get("teacher_reference") == reference,
                "maximum teacher reference purpose must match prior job",
            )
            _validate_teacher_reference(reference, arguments["seed"], n)
        if op in ("teacher", "teacher_driver"):
            times = np.asarray(arguments["calendar_times"])
            _require(
                len(times) == 769 and np.allclose(times, np.arange(769) / 768),
                "formal teacher original 768-step calendar changed",
            )
            size = {"original_n": n, "path_steps": n * 768, "total_path_steps": n * 768}
        else:
            axes = teacher_axes(arguments["grid"], arguments["model"])
            count = (
                12 * len(axes["state"])
                if arguments["model"] == "Heston"
                else (len(axes["t0_spot"]) + 11 * len(axes["spot"])) * len(axes["state"])
            )
            size = {
                "original_n": n,
                "path_steps": n * 768,
                "total_path_steps": n * 768 * count,
                "financial_child_count": count,
                "child_boundary": "original_teacher_node",
            }
    elif op == "teacher_diagnostic":
        _require(n in original["teacher"]["n_candidates"], "additional teacher original N changed")
        expected = original["seeds"]["teacher"][0 if arguments["model"] == "Heston" else 1]
        _require(arguments["seed"] == expected, "additional teacher original stream changed")
        _require(
            arguments["cases"] == job.get("diagnostic_cases"),
            "additional exact-date case roster not locked",
        )
        size = {
            "original_n": n,
            "path_steps": n * 768,
            "total_path_steps": n * 768 * len(arguments["cases"]),
        }
    elif op == "precision":
        _require(n in original["test"]["n_candidates"], "original precision N ladder changed")
        receipts = arguments["stream_receipts"]
        _require(
            isinstance(receipts, dict) and set(receipts) == {"Heston", "local"},
            "actual precision original stream receipts required",
        )
        for model in ("Heston", "local"):
            rows = receipts[model]
            _require(
                len(rows) == 3
                and [r["seed"] for r in rows] == original["seeds"]["refinement"]
                and all(
                    r["original_n"] == n
                    and isinstance(r["global_driver_id"], str)
                    and len(r["global_driver_id"]) == 64
                    for r in rows
                ),
                "precision actual N/seed/global stream binding changed",
            )
        size = {"original_n": n, "path_steps": 0}
    elif op in ("oracle", "premium"):
        _require(arguments.get("steps_per_year", 1536) == 1536, "original independent SDE changed")
        _require(
            n in original["teacher"]["n_candidates"] or (op == "premium" and n == 65536),
            "independent original N changed",
        )
        if op == "premium":
            _require(
                arguments["seed"] == original["premium"]["seed"] and n == 65536,
                "reserved premium stream changed",
            )
        else:
            _require(
                arguments["seed"] in original["seeds"]["oracle"],
                "original oracle namespace changed",
            )
        multiplier = 2 if op == "premium" else 26
        size = {
            "original_n": n,
            "path_steps": n * 1536,
            "total_path_steps": n * 1536 * multiplier,
            "financial_child_count": multiplier,
            "child_boundary": "level_query",
        }
    elif op in ("market_pair", "Q"):
        seeds = original["seeds"]["pilot"] + original["seeds"]["refinement"]
        _require(arguments["seed"] in seeds, "pilot cannot open training/validation/test streams")
        _require(n >= 1024, "small source probes cannot replace original formal paths")
        steps = 1536 if op == "market_pair" else 8
        size = {
            "original_n": n,
            "path_steps": n * steps,
            "total_path_steps": n * (2304 if op == "market_pair" else 8),
        }
    elif op == "quote_risk":
        n = arguments["dataset"]["original_n"]
        _require(n >= 1024, "small risk source probes cannot replace formal paths")
        _require(arguments.get("chunk_paths", 256) > 0, "original risk chunk required")
        size = {"original_n": n, "path_steps": 0}
    elif op == "closure":
        _require(arguments["candidate"] == original, "main closure candidate changed")
        size = {"original_n": 8192, "path_steps": 0}
    elif op == "tiny_fits":
        _require(
            arguments["pilot_training_config"] == job.get("pilot_training_config"),
            "tiny config not locked in original job plan",
        )
        streams = arguments["stream_receipts"]
        _require(
            isinstance(streams, dict) and set(streams) == {"train", "validation"},
            "tiny actual train/validation stream receipts required",
        )
        identities = []
        for role in ("train", "validation"):
            _require(
                set(streams[role]) == {"Heston", "local"}, "both original pilot streams required"
            )
            for k, model in enumerate(("Heston", "local")):
                receipt = streams[role][model]
                _require(
                    receipt["seed"] == original["seeds"]["pilot"][k + (0 if role == "train" else 2)]
                    and receipt["original_n"] == arguments["pilot_training_config"]["original_n"],
                    "tiny actual original stream seed/N changed",
                )
                identities.append(receipt["global_driver_id"])
        _require(
            all(isinstance(i, str) and len(i) == 64 for i in identities)
            and len(set(identities)) == 4,
            "tiny actual global streams must be distinct",
        )
    original_binding = None
    if job.get("original_n_source") is not None:
        _require("selector" in arguments, "conditional actual selector arguments missing")
        original_binding = _selector_job_n_binding(job, arguments["selector"])
        _require(
            n == original_binding["original_n"] or op == "teacher_selected_inputs",
            "conditional original selected denominator changed",
        )
        if op == "teacher_diagnostic":
            selected = arguments.get("selected_inputs")
            _require(
                selected is not None
                and selected["kind"] == "teacher_selected_inputs"
                and selected["purpose"] == "extra_dates"
                and selected["model"] == arguments["model"] == original_binding["model"]
                and selected["original_n"] == n
                and selected["availability"] == "available"
                and selected["selector_raw_sha256"] == original_binding["selector_raw_sha256"]
                and input_identity(selected["driver"]) == input_identity(arguments["driver"]),
                "conditional selected extra-date numerical input changed",
            )
        size["original_n_binding"] = original_binding
        size["original_n"] = original_binding["original_n"]
    predicted = _prediction_for_original_n(job, n)
    if "by_original_n" in job["prediction"]:
        size["selected_prediction_sha256"] = input_identity(predicted)
    _require(predicted["path_steps"] == size["path_steps"], "actual predicted path steps differ")
    if size.get("total_path_steps", 0) > original["limits"]["job_path_steps"]:
        _require(
            predicted.get("total_path_steps") == size["total_path_steps"]
            and predicted.get("financial_child_count") == size["financial_child_count"]
            and predicted.get("child_boundary") == size["child_boundary"],
            "original financial children and aggregate cost binding required",
        )
    return size


def teacher_activation_decision(
    job, inputs, results, planned_jobs, cache, *, artifact_context=None
):
    """Recompute the lower whole-stage gate once, never trust its saved flag."""
    activation = job.get("activation")
    if activation is None:
        return {"execute": True, "reason": "unconditional prior job"}
    _require(
        set(activation) == {"previous_teacher_gate_job_id"},
        "prior teacher activation schema differs",
    )
    identifier = activation["previous_teacher_gate_job_id"]
    _require(
        identifier in results
        and identifier in planned_jobs
        and planned_jobs[identifier]["operation"] == "teacher_candidate_gate",
        "prior original teacher candidate gate required",
    )
    previous = results[identifier]
    if previous["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap"):
        return {
            "execute": True,
            "reason": "lower candidate unavailable after actual declared cap",
            "lower_gate_job_id": identifier,
            "lower_gate_evidence_sha256": input_identity(previous["raw"]),
        }
    if previous["status"] == "not_required_after_qualified_prefix":
        prior_decision = teacher_activation_decision(
            planned_jobs[identifier],
            inputs,
            results,
            planned_jobs,
            cache,
            artifact_context=artifact_context,
        )
        runner._same(
            unused_teacher_prefix_raw(planned_jobs[identifier], prior_decision),
            previous["raw"],
            "authenticated inherited original unused prefix",
        )
        inherited = previous["raw"]
        return {
            "execute": False,
            "reason": "earlier whole-stage candidate already qualified",
            "lower_gate_job_id": inherited["lower_gate_job_id"],
            "qualified_original_n": inherited["qualified_original_n"],
            "lower_gate_evidence_sha256": inherited["lower_gate_evidence_sha256"],
        }
    _require(
        previous["status"] == "executed",
        "source/solver defect cannot control progressive qualification",
    )
    arguments = _resolve(
        planned_jobs[identifier]["arguments"], inputs, results, planned_jobs=planned_jobs
    )
    key = (identifier, input_identity(previous["raw"]), input_identity(arguments))
    if key not in cache:
        from check_pilot import calculate_teacher_candidate_gate

        calculated = calculate_teacher_candidate_gate(
            arguments["parameters"],
            arguments.get("surface"),
            stage_plan=arguments["stage_plan"],
            evidence=arguments["evidence"],
            artifact_context=artifact_context,
        )
        runner._same(calculated, previous["raw"], "actual lower original teacher stage")
        cache[key] = calculated
    calculated = cache[key]
    qualified = calculated["qualification"] == "qualified"
    return {
        "execute": not qualified,
        "reason": "lower original whole-stage candidate qualified"
        if qualified
        else "lower original whole-stage numerical gates unmet",
        "lower_gate_job_id": identifier,
        "qualified_original_n": calculated["original_n"],
        "lower_gate_evidence_sha256": input_identity(previous["raw"]),
    }


def unused_teacher_prefix_raw(job, decision):
    """Keep planned quantities and genuine nonexecution after an authenticated gate."""
    _require(decision["execute"] is False, "unused prefix requires actual lower qualification")
    n = job.get("original_n")
    axes = None
    if job["operation"] == "teacher_grid":
        axes = teacher_axes(job["arguments"]["grid"], job["arguments"]["model"])
    return {
        "kind": "not_required_after_qualified_prefix",
        "operation": job["operation"],
        "original_n": n,
        "processed_n": 0,
        "unexecuted_n": n,
        "qualification": "unknown",
        "financial_qualification": "unknown",
        "planned_arguments_sha256": input_identity(job["arguments"]),
        "planned_axes": axes,
        "execution_status": "not_executed",
        "lower_gate_job_id": decision["lower_gate_job_id"],
        "qualified_original_n": decision["qualified_original_n"],
        "lower_gate_evidence_sha256": decision["lower_gate_evidence_sha256"],
        "reason": "planned later work unnecessary after whole original lower-stage gate; not a measured attempt",
    }


def validate_locked_plan(plan):
    """Require the original full roster, limits, seed namespaces and prior budgets."""
    candidate = execution.execution_candidate()
    original = candidate["original_candidate"]
    _require(plan.get("schema") == "rb-f04-pilot-plan-v1", "pilot locked plan required")
    _require(plan.get("candidate") == candidate, "changed original candidate")
    _require(plan.get("test_opened") is False, "main test already opened")
    _require(
        plan.get("teacher_n_candidates") == original["teacher"]["n_candidates"]
        and plan.get("teacher_grid_candidates") == original["teacher"]["grid_candidates"]
        and plan.get("sde_levels") == [768, 1536]
        and plan.get("frequencies") == [12, 24, 48]
        and plan.get("seeds") == original["seeds"],
        "original ladder/streams changed",
    )
    _require(plan.get("limits") == original["limits"], "original job caps changed")
    cases = plan.get("case_plan", [])
    descriptors = candidate["pilot_cases"]
    _require(
        len(cases) == 121 and {r["id"] for r in cases} == {r["id"] for r in descriptors},
        "all 121 original case plans required",
    )
    for saved, descriptor in zip(
        sorted(cases, key=lambda r: r["id"]),
        sorted(descriptors, key=lambda r: r["id"]),
        strict=True,
    ):
        _require(
            all(saved.get(k) == descriptor[k] for k in ("kind", "identity", "gates")),
            "original case identity changed",
        )
    groups = plan.get("attempt_plan", [])
    _require(
        len(groups) == 51
        and {r["id"] for r in groups} == set(candidate["required_pilot_attempt_ids"]),
        "all 51 required plans required",
    )
    _require(
        isinstance(plan.get("history"), list) and plan["history"],
        "original historical costs/evidence required",
    )
    jobs = plan.get("jobs", [])
    _require(jobs and len({j["id"] for j in jobs}) == len(jobs), "unique actual jobs required")
    for job in jobs:
        prediction = job.get("prediction", {})
        if prediction.get("by_original_n") is not None:
            _prediction_for_original_n(job, original["teacher"]["n_candidates"][0])
        if job.get("original_n_source") is not None:
            source = job["original_n_source"]
            _require(
                job["arguments"].get("selector")
                == {"job_record": source["teacher_selection_job_id"]},
                "conditional prior selector control reference required",
            )
        _require(
            prediction.get("path_steps", -1) >= 0
            and prediction["path_steps"] <= original["limits"]["job_path_steps"],
            "predicted path-step cap exceeded",
        )
        _require(
            0
            <= prediction.get("expanded_bytes", -1)
            <= original["limits"]["chunk_uncompressed_bytes"],
            "predicted byte cap exceeded",
        )
        budget = job.get("budget", {})
        _require(
            budget.get("planned_before_attempt") is True
            and isinstance(budget.get("review_sha256"), str)
            and len(budget["review_sha256"]) == 64
            and budget.get("wall_seconds", 0) > 0,
            "prior reviewed job budget required",
        )
        _require(
            prediction.get("rate_source")
            in ("measured_prior_job", "independently_reviewed_estimate"),
            "next-job rate prediction provenance required",
        )
    prior = set()
    ancestors = {}
    all_jobs = {j["id"]: j for j in jobs}
    for job in jobs:
        dependencies = _dependency_ids(job["arguments"])
        activation = job.get("activation")
        if activation is not None:
            _require(
                set(activation) == {"previous_teacher_gate_job_id"}
                and activation["previous_teacher_gate_job_id"] in prior
                and all_jobs[activation["previous_teacher_gate_job_id"]]["operation"]
                == "teacher_candidate_gate",
                "activation needs a prior original teacher gate",
            )
        _require(dependencies <= prior, "job dependencies must be prior locked jobs")
        _require(
            dependencies == _numeric_dependency_ids(job["arguments"])
            or _control_receipts_allowed(job),
            "only typed selection/selected inputs/conditional diagnostic may consume control receipts",
        )
        ancestors[job["id"]] = dependencies | set().union(*(ancestors[i] for i in dependencies))
        prior.add(job["id"])
    for job in jobs:
        scope = job.get("cap_scope")
        if scope is None:
            continue
        _require(
            set(scope) == {"job_ids", "case_ids", "attempt_ids", "expense_id"},
            "explicit parent cap scope schema required",
        )
        _require(
            scope["expense_id"] == job["expense_id"],
            "cap scope must bind the parent's actual expense",
        )
        affected = scope["job_ids"]
        _require(
            len(set(affected)) == len(affected)
            and job["id"] in affected
            and set(affected) <= set(all_jobs),
            "cap scope original jobs differ",
        )
        _require(
            all(i == job["id"] or job["id"] in ancestors[i] for i in affected),
            "cap scope may only include actual dependency descendants",
        )
        _require(
            set(scope["case_ids"]) <= {r["id"] for r in descriptors}
            and set(scope["attempt_ids"]) <= {r["id"] for r in groups},
            "cap scope cannot invent obligations",
        )
    return candidate


def run_pilot(directory, *, inputs, locked_plan, source_root=ROOT, resume=False):
    """Execute independent jobs after caps; stop on source or solver defects.

    Dependent work remains unexecuted with original N and consumed parent bindings.
    No cap, resume or metadata inspection certifies its financial measurements.
    """
    phase_begin_ns, phase_cpu_ns = perf_counter_ns(), process_time_ns()
    locked_plan = copy.deepcopy(locked_plan)
    validate_locked_plan(locked_plan)
    source = _locked_bindings(inputs, locked_plan, source_root)
    directory = Path(directory)
    plan_digest = runner.payload_digest(locked_plan)
    if resume:
        saved, _ = read_pilot_artifact(directory / "plan")
        _require(runner.payload_digest(saved) == plan_digest, "resume locked plan differs")
    else:
        write_pilot_artifact(directory / "plan", locked_plan)
    previous_phases = []
    activation_artifact_context = None
    if resume:
        checkpoints = sorted(directory.glob("checkpoint*"))
        if checkpoints:
            prior_snapshot, _ = read_pilot_artifact(checkpoints[-1])
            _require(
                runner.payload_digest(prior_snapshot["locked_plan"]) == plan_digest,
                "resume previous phase plan differs",
            )
            previous_phases = prior_snapshot.get("execution_phases", [])
            activation_artifact_context = {
                "original_root": prior_snapshot["artifact_directory"],
                "restored_root": str(directory.resolve()),
            }
    measured_jobs = []
    activation_cache = {}
    planned_jobs = {j["id"]: j for j in locked_plan["jobs"]}
    results, events = {}, []
    for job in locked_plan["jobs"]:
        path = directory / "jobs" / job["id"]
        if resume and path.exists():
            row, _ = read_pilot_artifact(path)
            _require(row.get("plan_sha256") == plan_digest, "stale resume job")
            from check_pilot import check_job_envelope

            check_job_envelope(row, job, locked_plan)
            _require(
                row["input_bindings"] == locked_plan["input_bindings"]
                and row["source_sha256"] == runner.payload_digest(source),
                "stale actual resume source/input binding",
            )
            row["artifact_path"] = str(path)
            results[job["id"]] = row
            if row["status"] == "unclosed_source_or_solver_defect":
                break
            _require(
                row["status"]
                in (
                    "executed",
                    "failed_at_declared_cap",
                    "unexecuted_dependency_cap",
                    "not_required_after_qualified_prefix",
                ),
                "unknown resume status",
            )
            if row["status"] == "not_required_after_qualified_prefix":
                decision = teacher_activation_decision(
                    job,
                    inputs,
                    results,
                    planned_jobs,
                    activation_cache,
                    artifact_context=activation_artifact_context,
                )
                runner._same(
                    unused_teacher_prefix_raw(job, decision),
                    row["raw"],
                    "resume original unused prefix",
                )
            if row["status"] == "unexecuted_dependency_cap":
                from check_pilot import check_dependency_cap_job

                check_dependency_cap_job(
                    row,
                    job,
                    locked_plan,
                    results,
                    require_scope=False,
                    inputs=inputs,
                    artifact_context=activation_artifact_context,
                )
            continue
        begin_ns, cpu_ns = perf_counter_ns(), process_time_ns()
        measured_jobs.append(job["id"])
        common = {
            "id": job["id"],
            "operation": job["operation"],
            "plan_sha256": plan_digest,
            "input_bindings": locked_plan["input_bindings"],
            "source_sha256": runner.payload_digest(source),
            "prediction": job["prediction"],
            "budget": job["budget"],
            "size": None,
            "size_unavailable_reason": "argument resolution not completed",
        }
        decision = teacher_activation_decision(
            job,
            inputs,
            results,
            planned_jobs,
            activation_cache,
            artifact_context=activation_artifact_context,
        )
        if not decision["execute"]:
            raw = unused_teacher_prefix_raw(job, decision)
            end_ns, cpu_end_ns = perf_counter_ns(), process_time_ns()
            row = common | {
                "raw": raw,
                "status": "not_required_after_qualified_prefix",
                "reason": raw["reason"],
                "cap_evidence": None,
                "financial_qualification": "unknown",
                "expense": _expense(
                    job["expense_id"],
                    (end_ns - begin_ns) / 1e9,
                    (cpu_end_ns - cpu_ns) / 1e9,
                    cap=job["budget"]["wall_seconds"],
                ),
                "timing_events": {
                    "wall_start_ns": begin_ns,
                    "wall_stop_ns": end_ns,
                    "cpu_start_ns": cpu_ns,
                    "cpu_stop_ns": cpu_end_ns,
                },
            }
            write_pilot_artifact(path, row)
            row["artifact_path"] = str(path)
            results[job["id"]] = row
            events.append({"job": job["id"], "status": row["status"], "plan_sha256": plan_digest})
            continue
        dependencies = _dependency_ids(job["arguments"])
        _require(dependencies <= set(results), "missing prior job dependency")
        blocked = any(
            results[i]["status"] != "executed" for i in _numeric_dependency_ids(job["arguments"])
        )
        if blocked:
            raw = _dependency_cap_raw(job, dependencies, results)
            end_ns, cpu_end_ns = perf_counter_ns(), process_time_ns()
            row = common | {
                "raw": raw,
                "status": "unexecuted_dependency_cap",
                "reason": "required numerical input unavailable after consumed parent cap",
                "financial_qualification": "unknown",
                "cap_evidence": None,
                "expense": _expense(
                    job["expense_id"],
                    (end_ns - begin_ns) / 1e9,
                    (cpu_end_ns - cpu_ns) / 1e9,
                    failed="dependency unexecuted; metadata inspection only",
                    cap=job["budget"]["wall_seconds"],
                ),
            }
            row["timing_events"] = {
                "wall_start_ns": begin_ns,
                "wall_stop_ns": end_ns,
                "cpu_start_ns": cpu_ns,
                "cpu_stop_ns": cpu_end_ns,
            }
            write_pilot_artifact(path, row)
            row["artifact_path"] = str(path)
            results[job["id"]] = row
            events.append({"job": job["id"], "status": row["status"], "plan_sha256": plan_digest})
            continue
        try:
            arguments = _resolve(job["arguments"], inputs, results, planned_jobs=planned_jobs)
            if job["operation"] in (
                "teacher",
                "teacher_grid",
                "teacher_driver",
                "teacher_diagnostic",
                "bump_risk",
                "precision",
                "quote_risk",
                "quotes",
                "field",
                "Q",
                "market_pair",
                "oracle",
                "premium",
                "call_table",
            ):
                arguments["wall_cap_seconds"] = job["budget"]["wall_seconds"]
            if job["operation"] in ("teacher_grid", "teacher_driver"):
                arguments["work_directory"] = str(directory / "work" / job["id"])
            size = _job_identity(job, arguments)
            common.update(
                size=size,
                size_unavailable_reason=None,
                resolved_arguments_sha256=input_identity(arguments),
                argument_manifest={
                    k: v
                    for k, v in arguments.items()
                    if k
                    in (
                        "model",
                        "original_n",
                        "n_paths",
                        "seed",
                        "calendar_times",
                        "start_index",
                        "spot",
                        "state",
                        "date",
                        "quote",
                        "memory_sum",
                        "memory_count",
                        "spot_bump",
                        "quote_bump",
                        "steps_per_year",
                    )
                },
            )
            if job["operation"] == "quote_risk":
                common["argument_manifest"]["original_n"] = arguments["dataset"]["original_n"]
            raw = _dispatch(job["operation"], arguments)
            end_ns, cpu_end_ns = perf_counter_ns(), process_time_ns()
            elapsed = (end_ns - begin_ns) / 1e9
            limit = job["budget"]["wall_seconds"]
            child_cap = isinstance(raw, dict) and (
                raw.get("status") == "failed_at_declared_cap"
                or (
                    isinstance(raw.get("cap_evidence"), dict)
                    and raw["cap_evidence"].get("cap_reached") is True
                )
            )
            defect = (
                isinstance(raw, dict) and raw.get("status") == "unclosed_source_or_solver_defect"
            )
            capped = not defect and (elapsed > limit or child_cap)
            unavailable_selection = not capped and (
                (
                    job["operation"] == "teacher_selection"
                    and raw["selection_status"] == "unavailable"
                )
                or (
                    job["operation"] == "teacher_selected_inputs"
                    and raw["availability"] == "unavailable"
                )
            )
            if unavailable_selection:
                selection_inspection = raw
                raw = _dependency_cap_raw(job, dependencies, results)
                raw[
                    "selection_inspection"
                    if job["operation"] == "teacher_selection"
                    else "selected_inputs_inspection"
                ] = selection_inspection
            row = common | {
                "raw": raw,
                "status": "unclosed_source_or_solver_defect"
                if defect
                else "failed_at_declared_cap"
                if capped
                else "unexecuted_dependency_cap"
                if unavailable_selection
                else "executed",
                "reason": raw.get("reason")
                if defect
                else "actual wall cap reached"
                if capped
                else "maximum actual teacher unavailable after consumed prior cap"
                if unavailable_selection
                else None,
                "financial_qualification": "unknown",
                "cap_evidence": (
                    {"metric": "wall_seconds", "limit": limit, "consumed": elapsed}
                    if capped
                    else None
                ),
                "expense": _expense(
                    job["expense_id"],
                    elapsed,
                    (cpu_end_ns - cpu_ns) / 1e9,
                    failed=raw.get("reason")
                    if defect
                    else "actual wall cap reached"
                    if capped
                    else None,
                    cap=limit,
                ),
            }
        except (
            ValueError,
            KeyError,
            TypeError,
            FloatingPointError,
            RuntimeError,
            ImportError,
            OSError,
            MemoryError,
        ) as error:
            end_ns, cpu_end_ns = perf_counter_ns(), process_time_ns()
            row = common | failed_job_record(job["id"], f"{type(error).__name__}: {error}")
            row["expense"] = _expense(
                job["expense_id"],
                (end_ns - begin_ns) / 1e9,
                (cpu_end_ns - cpu_ns) / 1e9,
                failed=str(error),
                cap=job["budget"]["wall_seconds"],
            )
        row["timing_events"] = {
            "wall_start_ns": begin_ns,
            "wall_stop_ns": end_ns,
            "cpu_start_ns": cpu_ns,
            "cpu_stop_ns": cpu_end_ns,
        }
        if job["operation"] == "closure":
            write_closure_artifact(path, row)
        else:
            write_pilot_artifact(path, row)
        row["artifact_path"] = str(path)
        results[job["id"]] = row
        events.append({"job": job["id"], "status": row["status"], "plan_sha256": plan_digest})
        if row["status"] == "unclosed_source_or_solver_defect":
            break
    phase_end_ns, phase_cpu_end_ns = perf_counter_ns(), process_time_ns()
    phase = _expense(
        "pilot-execution-phase:" + str(len(previous_phases)),
        (phase_end_ns - phase_begin_ns) / 1e9,
        (phase_cpu_end_ns - phase_cpu_ns) / 1e9,
    )
    phase.update(
        scope="actual lifecycle inclusive timer before final checkpoint",
        covered_job_ids=measured_jobs,
        timing_events={
            "wall_start_ns": phase_begin_ns,
            "wall_stop_ns": phase_end_ns,
            "cpu_start_ns": phase_cpu_ns,
            "cpu_stop_ns": phase_cpu_end_ns,
        },
        plan_sha256=plan_digest,
        source_sha256=runner.payload_digest(source),
        input_bindings=copy.deepcopy(locked_plan["input_bindings"]),
        scope_limits="final checkpoint serialization and later saved check/review/CAS separate",
    )
    snapshot = {
        "schema": SCHEMA,
        "execution_phases": [*previous_phases, phase],
        "locked_plan": locked_plan,
        "source_root": str(source_root),
        "artifact_directory": str(directory.resolve()),
        "source": source,
        "input_bindings": locked_plan["input_bindings"],
        "jobs": list(results.values()),
        "events": events,
        "case_bindings": copy.deepcopy(locked_plan.get("case_bindings", [])),
        "attempt_bindings": copy.deepcopy(locked_plan.get("attempt_bindings", [])),
        "history": locked_plan["history"],
        "test_opened": False,
        "financial_qualification": "unknown",
        "verification": None,
    }
    persisted = dict(snapshot)
    persisted["jobs"] = [
        {k: v for k, v in row.items() if k != "raw"}
        | {
            "raw_job_payload_sha256": runner.payload_digest(
                {k: v for k, v in row.items() if k != "artifact_path"}
            )
        }
        for row in results.values()
    ]
    write_pilot_artifact(
        directory / f"checkpoint{len(list(directory.glob('checkpoint*'))):04d}", persisted
    )
    return snapshot


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Actual locked full-roster pilot; source-unit calls are separate."
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    plan, _ = read_pilot_artifact(args.plan)
    inputs, _ = read_pilot_artifact(args.inputs)
    snapshot = run_pilot(
        args.output, inputs=unpack_inputs(inputs), locked_plan=plan, resume=args.resume
    )
    print(
        {"jobs": len(snapshot["jobs"]), "test_opened": False, "financial_qualification": "unknown"}
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
