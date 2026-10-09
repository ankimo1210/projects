"""Bounded dynamic RB-F04 runner and saved-only arithmetic checking.

Tiny constant-volatility inputs exercise actual private APIs; they are not the
fixed Heston/local pilot. No full pilot or freeze is created. The main test
loader is called only after raw validation replay and assert_main_ready.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from time import perf_counter, process_time

ROOT = Path(__file__).resolve().parents[4]
if __name__ == "__main__":
    # Direct CLI uses this checkout even when the shared editable venv points at main.
    sys.path[:0] = [
        str(ROOT / "johnhull/hullkit/src"),
        str(ROOT / "deep_hedge_price/src"),
    ]

import numpy as np
from deep_hedge_price._dynamic_hedging_protocol import candidate_protocol
from hullkit._dynamic_hedging_conditional import primitive_labels, teacher_primitives
from hullkit._dynamic_hedging_surfaces import build_asian_cache, build_call_cache
from hullkit._heston_local_surface import HestonParameters
from scipy.special import ndtr

from deep_hedge_price import _dynamic_hedging_execution as execution
from deep_hedge_price import _dynamic_hedging_protocol as protocol
from deep_hedge_price import _dynamic_hedging_replay as replay
from deep_hedge_price import _dynamic_hedging_study as study

MODELS = ("Heston", "local")
UNIVERSES = ("U1", "U2")
SCHEMA = "rb-f04-runner-tree-v1"


def _digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _same(actual, expected, name):
    if isinstance(actual, dict) and isinstance(expected, dict):
        if actual.keys() != expected.keys():
            raise ValueError(f"{name}: saved keyset mismatch")
        for key in actual:
            _same(actual[key], expected[key], f"{name}.{key}")
    elif isinstance(actual, (list, tuple)) and isinstance(expected, (list, tuple)):
        if len(actual) != len(expected):
            raise ValueError(f"{name}: saved sequence length mismatch")
        for i, (a, b) in enumerate(zip(actual, expected, strict=True)):
            _same(a, b, f"{name}[{i}]")
    elif isinstance(actual, (np.ndarray, np.number, float, int, bool)):
        a, b = np.asarray(actual), np.asarray(expected)
        equal = a.shape == b.shape and (
            np.allclose(a, b, rtol=2e-9, atol=2e-10, equal_nan=True)
            if a.dtype.kind in "buifc" and b.dtype.kind in "buifc"
            else np.array_equal(a, b)
        )
        if not equal:
            raise ValueError(f"{name}: saved value mismatch")
    elif actual != expected:
        raise ValueError(f"{name}: saved value mismatch")


def source_identity(root=ROOT, *, entrypoints=None, package_roots=None) -> dict:
    """Record transitive local imports, package initializers and actual versions.

    Imports inside functions and from-import submodules are included. External
    versions come from installed distribution metadata without module imports.
    Dynamic imports are explicitly listed and not treated as resolved silently.
    """
    root = Path(root).resolve(strict=True)
    package_roots = package_roots or {
        "hullkit": "johnhull/hullkit/src/hullkit",
        "deep_hedge_price": "deep_hedge_price/src/deep_hedge_price",
        "dynamic_research": "johnhull/research/RB-F04/dynamic_hedging",
    }
    entrypoints = entrypoints or [
        "dynamic_research.run_reference",
        "dynamic_research.check_initial_quotes",
        "dynamic_research.check_selected_calls",
    ]
    bases = {name: root / value for name, value in package_roots.items()}
    pending, paths, graph, external, dynamic = list(entrypoints), {}, {}, set(), []

    def resolve(name):
        for package, base in bases.items():
            if name == package:
                path = base / "__init__.py"
            elif name.startswith(package + "."):
                relative = name[len(package) + 1 :].replace(".", "/")
                path = base / (relative + ".py")
                if not path.is_file():
                    path = base / relative / "__init__.py"
            else:
                continue
            return path if path.is_file() else None
        return None

    while pending:
        name = pending.pop()
        if name in paths:
            continue
        path = resolve(name)
        if path is None:
            external.add(name.split(".")[0])
            continue
        if path.resolve() != path or not path.is_relative_to(root):
            raise ValueError("source closure requires canonical local paths")
        paths[name] = path.relative_to(root).as_posix()
        package = name if path.name == "__init__.py" else name.rsplit(".", 1)[0]
        pieces = name.split(".")
        for count in range(1, len(pieces)):
            parent = ".".join(pieces[:count])
            parent_path = resolve(parent)
            if parent_path is not None and parent_path.name == "__init__.py":
                pending.append(parent)
        dependencies = set()
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                dependencies.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    parts = package.split(".")
                    base = ".".join(parts[: len(parts) - node.level + 1])
                    module = base + ("." + node.module if node.module else "")
                else:
                    module = node.module or ""
                dependencies.add(module)
                dependencies.update(
                    module + "." + alias.name
                    for alias in node.names
                    if resolve(module + "." + alias.name)
                )
            elif isinstance(node, ast.Call):
                text = ast.unparse(node.func)
                if text in (
                    "__import__",
                    "importlib.import_module",
                    "importlib.util.spec_from_file_location",
                ):
                    dynamic.append({"source": paths[name], "line": node.lineno, "call": text})
        graph[paths[name]] = sorted(dep for dep in dependencies if resolve(dep))
        for dependency in dependencies:
            if resolve(dependency):
                pending.append(dependency)
            elif dependency:
                external.add(dependency.split(".")[0])
    files = protocol.source_registry(root, sorted(set(paths.values())))
    for module_name, relative in paths.items():
        loaded = sys.modules.get(module_name)
        if loaded is not None and getattr(loaded, "__file__", None):
            if Path(loaded.__file__).resolve() != root / relative:
                raise ValueError(f"loaded source differs from registered checkout: {module_name}")
    distributions = importlib.metadata.packages_distributions()
    versions = {}
    for module in sorted(external - set(sys.stdlib_module_names)):
        names = distributions.get(module, [])
        versions[module] = {name: importlib.metadata.version(name) for name in names} or {
            "unmapped": None
        }
    environment = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "distributions": versions,
    }
    return {
        "files": files,
        "protocol_source": files | {"environment:versions": _digest(environment)},
        "local_import_graph": graph,
        "environment": environment,
        "environment_sha256": _digest(environment),
        "dynamic_imports": dynamic,
        "boundary": "AST local imports and package init; execution branches are not certified",
    }


def execution_source_identity(root=ROOT) -> dict:
    """Include all required phase entry points and reject missing local source.

    The older bounded runner keeps its original source roots. Research execution
    additionally binds independent references and fresh verification; missing
    phase implementations cannot be treated as external libraries.
    """
    root = Path(root).resolve(strict=True)
    base = root / "johnhull/research/RB-F04/dynamic_hedging"
    required = [
        "reference_methods",
        "run_fresh",
        "run_reference",
        "check_initial_quotes",
        "check_selected_calls",
    ]
    for name in required:
        if not (base / f"{name}.py").is_file():
            raise ValueError(f"required execution source missing: {name}")
    return source_identity(root, entrypoints=[f"dynamic_research.{name}" for name in required])


def validation_candidate_ids(widths=None):
    """Return the fixed model, Greek-then-width tie order."""
    widths = candidate_protocol()["hedging"]["band_width_candidates"] if widths is None else widths
    return [
        name
        for model in MODELS
        for name in [f"greek:{model}"] + [f"band:{model}:width{w:g}" for w in widths]
    ]


def check_validation(saved, losses, *, original_n, qualifications=None):
    """Recalculate MSE and selections from all original per-path losses.

    Optional qualification masks must come from finance replay, not receipt
    flags. Absent masks this boundary checks finite arithmetic only.
    """
    ids = validation_candidate_ids()
    candidates = saved.get("candidates", [])
    if (
        len(candidates) != len(ids)
        or {row.get("id") for row in candidates} != set(ids)
        or set(losses) != set(ids)
        or saved.get("original_n") != original_n
    ):
        raise ValueError("all fourteen original validation candidates and original N required")
    by_id, rows, scores = {row["id"]: row for row in candidates}, [], {}
    for identifier in ids:
        loss = np.asarray(losses[identifier], float)
        if loss.shape != (original_n,) or by_id[identifier].get("original_n") != original_n:
            raise ValueError("validation original denominator cannot be changed")
        row, finite, qualified = by_id[identifier], np.isfinite(loss), True
        if qualifications is not None:
            mask = np.asarray(qualifications[identifier], bool)
            if mask.shape != loss.shape:
                raise ValueError("qualification must retain every original validation path")
            qualified = bool(mask.all())
        with np.errstate(over="ignore", invalid="ignore"):
            mse = float(np.mean(loss**2))
        complete = bool(finite.all() and qualified and np.isfinite(mse))
        if complete:
            if row.get("status") != "completed":
                raise ValueError("finite qualified validation losses cannot be discarded")
            _same(mse, row.get("mse"), f"{identifier}.MSE")
            scores[identifier] = mse
        elif row.get("status") != "failed" or not row.get("reason") or row.get("mse") is not None:
            raise ValueError("unknown validation path needs failed status/reason")
        rows.append(
            {
                "id": identifier,
                "status": "completed" if complete else "failed",
                "original_n": original_n,
                "finite_n": int(finite.sum()),
                "mse": mse if complete else None,
            }
        )
    baseline = min(scores, key=lambda k: (scores[k], ids.index(k))) if scores else None
    if saved.get("selected_baseline") != baseline:
        raise ValueError("saved baseline differs from original raw validation minimum")
    bands = {}
    for model in MODELS:
        available = [key for key in scores if key.startswith(f"band:{model}:")]
        bands[model] = (
            min(available, key=lambda k: (scores[k], ids.index(k))) if available else None
        )
        if saved.get("selected_bands", {}).get(model) != bands[model]:
            raise ValueError("saved band differs from raw validation minimum")
        if not available and not saved.get("band_failures", {}).get(model):
            raise ValueError("all-failed band needs its failure reason")
    if saved.get("status") != ("completed" if scores else "failed"):
        raise ValueError("saved validation status differs from original raw losses")
    return {
        "integrity": "pass",
        "rows": rows,
        "selection": {"selected_baseline": baseline, "selected_bands": bands},
    }


def run_main(
    *,
    frozen,
    candidate,
    source,
    selection_receipts,
    raw_validation,
    main_test_loader,
    closed_fits=None,
):
    """Use the unchanged strict v1 gate before evaluating supplied main data.

    Generation, statistics, Q checks, all expenses and fresh lifecycle remain
    caller-owned obligations; this boundary does not certify financial accuracy.
    """
    return _run_closed_main(
        frozen=frozen,
        candidate=candidate,
        gate_candidate=candidate,
        source=source,
        selection_receipts=selection_receipts,
        raw_validation=raw_validation,
        main_test_loader=main_test_loader,
        closed_fits=closed_fits,
        readiness_guard=protocol.assert_main_ready,
        source_provider=source_identity,
    )


def run_execution_main(
    *,
    frozen,
    candidate,
    source,
    selection_receipts,
    raw_validation,
    main_test_loader,
    closed_fits=None,
):
    """Use the separate research execution gate, retaining unknown precision.

    The full execution candidate is checked without a synthetic qualified v1
    freeze. The financial calculation uses its exact original v1 candidate.
    This supplied-data boundary is not a complete experiment or an acceptance.
    """
    fixed_candidate, fixed_frozen = copy.deepcopy((candidate, frozen))
    precision = fixed_frozen.get("selection", {}).get("precision_selection")
    result = _run_closed_main(
        frozen=fixed_frozen,
        candidate=fixed_candidate.get("original_candidate", {}),
        gate_candidate=fixed_candidate,
        source=source,
        selection_receipts=selection_receipts,
        raw_validation=raw_validation,
        main_test_loader=main_test_loader,
        closed_fits=closed_fits,
        readiness_guard=execution.assert_execution_ready,
        source_provider=execution_source_identity,
    )
    return result | {
        "precision_selection": precision,
        "execution_contract": fixed_frozen.get("schema"),
        "kind": "rb-f04-execution-main-v1.1",
    }


def _run_closed_main(
    *,
    frozen,
    candidate,
    gate_candidate,
    source,
    selection_receipts,
    raw_validation,
    main_test_loader,
    closed_fits,
    readiness_guard,
    source_provider,
):
    """Recalculate raw closed selections before either gated test loader."""
    frozen, candidate, gate_candidate, source, selection_receipts, raw_validation, closed_fits = (
        copy.deepcopy(
            (
                frozen,
                candidate,
                gate_candidate,
                source,
                selection_receipts,
                raw_validation,
                closed_fits,
            )
        )
    )
    if not frozen:
        readiness_guard(frozen, gate_candidate, source, selection_receipts)
    if "training" not in candidate or "validation" not in candidate:
        raise ValueError("complete original financial candidate required")
    _same(source_provider()["protocol_source"], source, "main.source_identity")
    if closed_fits is None:
        raise ValueError("closed training fits must be fixed before test access")
    _check_original_fits(
        closed_fits, candidate["training"]["original_n"], candidate["training"]["updates"]
    )
    if selection_receipts.get("closed_fits_sha256") != payload_digest(closed_fits):
        raise ValueError("closed fits differ from the prior training selection receipt")
    selected_fits = {row["id"]: row for row in selection_receipts.get("fits", [])}
    if len(selected_fits) != 12:
        raise ValueError("twelve prior training selection fit records required")
    for row in closed_fits["fits"]:
        selected = selected_fits[row["id"]]
        for key in [
            "status",
            "attempted",
            "original_n",
            "requested_updates",
            "updates",
            "elapsed_seconds",
        ]:
            _same(row[key], selected[key], f"closed_fits.{row['id']}.{key}")
    # All prior source/protocol/fit/selection inputs are detached above.
    fixed_fits = closed_fits
    validations = selection_receipts.get("validation", [])
    if len(validations) != 4:
        raise ValueError("all four raw validation selections required before test loading")
    for record in validations:
        raw = raw_validation[record["id"]]
        losses = raw.get("losses", raw)
        qualifications = raw.get("qualifications") if "losses" in raw else None
        check_validation(
            record,
            losses,
            original_n=candidate["validation"]["original_n"],
            qualifications=qualifications,
        )
    readiness_guard(frozen, gate_candidate, source, selection_receipts)
    loaded = main_test_loader()
    if "fits" in loaded:
        _same(fixed_fits, loaded["fits"], "test_artifact.closed_fits")
    if "test_cases" not in loaded:
        return {
            "test_opened": True,
            "main_execution": "not_implemented",
            "qualification": "unknown",
            "reason": "all eighteen cases not supplied",
        }
    expected = {
        (g, seed, level)
        for g in MODELS
        for seed in range(3)
        for level in candidate["sde"]["main_levels"]
    }
    keys = [(c["generator"], c["seed_slot"], c["level"]) for c in loaded["test_cases"]]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("all original generator/seed/level main cases required")
    fits = fixed_fits
    by_selection = {row["id"]: row for row in validations}
    evaluated = []
    for case in loaded["test_cases"]:
        if case["dataset"]["original_n"] != frozen["selection"]["test_n"]:
            raise ValueError("main original N differs from frozen selection")
        for universe in UNIVERSES:
            result = study.test_roster(
                case["dataset"],
                case["risk"],
                fits,
                by_selection[f"selection:{case['generator']}:{universe}"],
                generator=case["generator"],
                universe=universe,
            )
            evaluated.append(
                {k: case[k] for k in ["generator", "seed_slot", "level"]}
                | {"universe": universe, "result": result}
            )
    return {
        "test_opened": True,
        "main_execution": "supplied_data_evaluated",
        "evaluations": evaluated,
        "qualification": "unknown",
        "unverified": [
            "main_statistics",
            "Q_diagnostics",
            "independent_refinements",
            "all_expenses",
        ],
    }


def _encode_tree(value, arrays):
    if isinstance(value, np.ndarray):
        name = f"a{len(arrays):06d}"
        arrays[name] = value
        return {"__array__": name}
    if isinstance(value, np.generic):
        return _encode_tree(value.item(), arrays)
    if isinstance(value, HestonParameters):
        return {"__heston_parameters__": vars(value)}
    if isinstance(value, float) and not np.isfinite(value):
        return {"__nonfinite__": "nan" if np.isnan(value) else "inf" if value > 0 else "-inf"}
    if isinstance(value, dict):
        return {key: _encode_tree(value[key], arrays) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_encode_tree(item, arrays) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError(f"unsupported saved value: {type(value).__name__}")


def _decode_tree(value, arrays, used):
    if isinstance(value, list):
        return [_decode_tree(item, arrays, used) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"__array__"}:
        name = value["__array__"]
        used.add(name)
        return arrays[name]
    if set(value) == {"__heston_parameters__"}:
        return HestonParameters(**value["__heston_parameters__"])
    if set(value) == {"__nonfinite__"}:
        return {"nan": np.nan, "inf": np.inf, "-inf": -np.inf}[value["__nonfinite__"]]
    return {key: _decode_tree(item, arrays, used) for key, item in value.items()}


def payload_digest(payload):
    """Bind a prior saved payload by provenance; not a numeric approval."""
    arrays = {}
    tree = _encode_tree(payload, arrays)
    array_bindings = {
        key: {
            "shape": list(value.shape),
            "dtype": value.dtype.str,
            "sha256": hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest(),
        }
        for key, value in arrays.items()
    }
    return _digest({"tree": tree, "arrays": array_bindings})


def _check_original_fits(fits, original_n, requested_updates):
    rows, slots = fits.get("fits", []), protocol.study_roster()["fits"]
    identifiers = [row.get("id") for row in rows]
    if (
        len(rows) != 12
        or len(set(identifiers)) != 12
        or set(identifiers) != {slot["id"] for slot in slots}
    ):
        raise ValueError("all twelve original fit attempts must be retained")
    by_id = {row["id"]: row for row in rows}
    for slot in slots:
        row = by_id[slot["id"]]
        for key, value in slot.items():
            _same(row.get(key), value, f"fit_slot.{key}")
        if (
            row.get("attempted") is not True
            or row.get("original_n") != original_n
            or row.get("requested_updates") != requested_updates
        ):
            raise ValueError("original fit attempts and requested denominator required")
        if row.get("status") == "completed":
            raw = row.get("raw_fit")
            if (
                not raw
                or raw.get("status") != "completed"
                or raw.get("complete") is not True
                or raw.get("seed") != slot["initialization"]
                or raw.get("universe") != slot["universe"]
                or raw.get("original_path_count") != original_n
                or raw.get("training_generator") != slot["training_generator"]
                or raw.get("fit_id") != slot["id"]
                or raw.get("checkpoint_id") != "last_finite_completed"
                or row.get("checkpoint_id") != "last_finite_completed"
                or raw.get("requested_updates") != requested_updates
                or raw.get("updates") != requested_updates
                or not raw.get("weights")
                or not raw.get("scaler")
                or row.get("updates") != requested_updates
            ):
                raise ValueError("completed fit slot needs its own raw identity/checkpoint")
            expected_shapes = {
                "w1": (9, 32),
                "b1": (32,),
                "w2": (32, 32),
                "b2": (32,),
                "w3": (32, 2),
                "b3": (2,),
            }
            if set(raw["weights"]) != set(expected_shapes):
                raise ValueError("completed fit slot needs full raw checkpoint weights")
            for key, shape in expected_shapes.items():
                value = np.asarray(raw["weights"][key])
                if value.shape != shape or not np.isfinite(value).all():
                    raise ValueError("completed fit slot has invalid raw checkpoint weights")
            scaler = raw["scaler"]
            if (
                not {"mean", "std"} <= scaler.keys()
                or np.asarray(scaler["mean"]).shape != (9,)
                or np.asarray(scaler["std"]).shape != (9,)
                or not np.isfinite(scaler["mean"]).all()
                or not np.isfinite(scaler["std"]).all()
                or np.any(np.asarray(scaler["std"]) <= 0)
            ):
                raise ValueError("completed fit slot has invalid raw checkpoint scaler")
        elif row.get("status") != "failed" or not row.get("reason"):
            raise ValueError("failed original fit requires its retained reason")


def save_bundle(directory, payload):
    """Write a new immutable tree through the existing no-pickle chunk protocol."""
    arrays = {}
    tree = _encode_tree(payload, arrays)
    return protocol.write_artifact(
        directory, metadata={"schema": SCHEMA, "tree": tree}, arrays=arrays
    )


def load_bundle(directory):
    """Validate byte provenance and load saved arrays, without finance claims."""
    metadata, arrays, receipt = protocol.read_artifact(directory)
    if metadata.get("schema") != SCHEMA:
        raise ValueError("runner tree schema required")
    used = set()
    payload = _decode_tree(metadata["tree"], arrays, used)
    if used != set(arrays):
        raise ValueError("saved references must cover the original array roster")
    return payload, receipt


def teacher_restart(
    model, parameters, surface, normals, calendar_times, *, start_index, spot, state, thresholds
):
    """Make compact last-step evidence, retaining global and slice CRN identities."""
    normals, calendar_times = np.asarray(normals), np.asarray(calendar_times)
    if normals.shape[1] != len(calendar_times) - 1 or not 0 <= start_index < normals.shape[1]:
        raise ValueError("global driver/calendar restart identity required")
    restart, times = normals[:, start_index:], calendar_times[start_index:]
    future = np.arange(int(np.floor(times[0] * 12 + 1e-9)) + 1, 13) / 12
    indices = []
    for time in future:
        matches = np.flatnonzero(np.isclose(times, time, rtol=0, atol=1e-12))
        if len(matches) != 1:
            raise ValueError("all future monthly fixings must be driver events")
        indices.append(int(matches[0]))
    primitives = teacher_primitives(
        model,
        parameters,
        restart,
        calendar_times=times,
        fixing_indices=np.array(indices),
        spot=spot,
        state=state,
        memory_count=12 - len(indices),
        surface=surface,
        compact_status=True,
    )
    global_id = hashlib.sha256(np.ascontiguousarray(normals).tobytes()).hexdigest()
    labels = primitive_labels(primitives, thresholds, blocks=16)
    labels["shared_driver_id"] = global_id
    labels["date_index"] = int(np.floor(times[0] * 12 + 1e-9))
    mapping = {
        "global_steps": normals.shape[1],
        "start_step": start_index,
        "stop_step": normals.shape[1],
        "original_n": len(normals),
        "aggregation_factor": 1,
        "slice_sha256": primitives["shared_driver_id"],
    }
    return {
        "primitives": primitives,
        "thresholds": np.asarray(thresholds).copy(),
        "labels": labels,
        "date_index": int(np.floor(times[0] * 12 + 1e-9)),
        "global_driver_id": global_id,
        "driver_mapping": mapping,
    }


class ConstantVarianceField:
    """Constant-volatility smoke fixture; not the Heston marginal local field."""

    def evaluate(self, time, spot):
        spot = np.asarray(spot)
        return {
            "variance": np.full(spot.shape, 0.04),
            "status": np.full(spot.shape, "tiny_constant_variance", dtype="<U32"),
        }


def _tiny_call_cache(model, parameters, dates, spots, states):
    if model == "heston":
        return build_call_cache(
            parameters, None, dates=dates, spot_nodes=spots, state_nodes=states, model=model
        )
    tau, stock = 1.25 - dates[:, None, None], spots[None, :, None]
    variance = 0.04 * states[None, None, :]
    sigma = np.sqrt(variance * tau)
    d1 = (np.log(stock / 100) + (0.03 + variance / 2) * tau) / sigma
    values = stock * ndtr(d1) - 100 * np.exp(-0.03 * tau) * ndtr(d1 - sigma)
    return {
        "model": model,
        "dates": dates.copy(),
        "spot_nodes": spots.copy(),
        "state_nodes": states.copy(),
        "values": values,
        "rate": 0.03,
        "dividend_yield": 0.0,
        "strike": 100.0,
        "maturity": 1.25,
        "price_error": np.nan,
        "derivative_error": np.nan,
        "reference_status": "unmeasured",
        "support_mask": np.isfinite(values),
        "interpolation": "not_a_knot_tensor_cubic",
        "diagnostics": [{"method": "tiny_constant_volatility_analytic"}],
    }


def _expense(identifier, start=None, cpu_start=None, *, parent=None, failed=None):
    pending = start is None
    return {
        "id": identifier,
        "scope": identifier,
        "parent_id": parent,
        "includes_children": True,
        "status": "pending" if pending else "failed" if failed else "complete",
        "reason": failed,
        "timing": {
            "wall_seconds": None if pending else perf_counter() - start,
            "cpu_seconds": None if pending else process_time() - cpu_start,
            "overrun_seconds": None if pending else 0.0,
        },
    }


def required_tiny_expenses():
    """Return the source-owned ledger; surviving rows cannot shrink it."""
    ids = ["source:registry", "training:all_12"]
    ids += [f"{phase}:{g}" for phase in ["call", "teacher", "market", "risk"] for g in MODELS]
    ids += [row["id"] for row in protocol.study_roster()["fits"]]
    ids += [
        f"{phase}:{g}:{u}" for phase in ["validation", "cells"] for g in MODELS for u in UNIVERSES
    ]
    ids += [
        "cold_import",
        "serialization",
        "load",
        "saved_check",
        "fresh",
        "CAS_primary",
        "CAS_mirror",
        "plots",
    ]
    return ids


def run_tiny(*, original_n=32, updates=1, train=True, evaluation_domains_by_model=None):
    """Run a bounded smoke through teacher/cache/12 fit attempts/44 policy slots.

    Twelve monthly fixings are retained. N is a multiple of sixteen. xi0 and
    constant local variance, shared train/validation fixtures and unmeasured
    precision do not support formal pilot, OOS or performance claims.
    """
    if original_n < 16 or original_n > 64 or original_n % 16 or updates not in [0, 1, 2]:
        raise ValueError("tiny scope: N16/32/48/64 and zero to two updates")
    evaluation_domains_by_model = copy.deepcopy(evaluation_domains_by_model)
    if evaluation_domains_by_model is not None and set(evaluation_domains_by_model) != {
        "heston",
        "local",
    }:
        raise ValueError("explicit evaluation domains require both model descriptors")
    start, cpu = perf_counter(), process_time()
    identity = source_identity()
    expenses = [_expense("source:registry", start, cpu)]
    p = HestonParameters(100.0, 0.03, 0.0, 0.04, 2.0, 0.04, 0.0, -0.7)
    surface = ConstantVarianceField()
    times, spots = np.arange(13) / 12, np.array([50.0, 90.0, 110.0, 200.0])
    state_axes = {
        "heston": np.array([0.01, 0.04, 0.1, 0.5]),
        "local": np.array([0.25, 1.0, 2.0, 4.0]),
    }
    thresholds = np.array([-1.0, 0.0, 1.0, 12.0, 24.0])
    caches, teachers = {}, {}
    teacher_driver = np.random.default_rng(202610090401).normal(size=(original_n, 12, 2))
    for model, name in zip(["heston", "local"], MODELS, strict=True):
        start, cpu = perf_counter(), process_time()
        call = _tiny_call_cache(model, p, times, np.geomspace(50.0, 200.0, 33), state_axes[model])
        expenses.append(_expense(f"call:{name}", start, cpu))
        start, cpu = perf_counter(), process_time()
        rows = []
        t0_spots = np.array([99.5, 99.75, 100.0, 100.25, 100.5])
        for date_index in range(12):
            restart_spots = [100.0] if model == "heston" else t0_spots if date_index == 0 else spots
            for spot in restart_spots:
                for state in state_axes[model]:
                    rows.append(
                        teacher_restart(
                            model,
                            p,
                            surface,
                            teacher_driver,
                            times,
                            start_index=date_index,
                            spot=float(spot),
                            state=float(state),
                            thresholds=thresholds,
                        )
                    )
        axes = {"dates": times[:-1], "state": state_axes[model], "threshold": thresholds}
        if model == "local":
            axes.update(spot=spots, t0_spot=t0_spots)
        domain = None if evaluation_domains_by_model is None else evaluation_domains_by_model[model]
        asian = build_asian_cache(
            {"groups": [row["labels"] for row in rows], "parameters": p, "N": original_n},
            model=model,
            axes=axes,
            evaluation_domains=domain,
        )
        caches[model], teachers[model] = (
            {"call": call, "asian": asian},
            {"rows": rows, "axes": axes, "evaluation_domains": copy.deepcopy(domain)},
        )
        expenses.append(_expense(f"teacher:{name}", start, cpu))
    datasets, risks = {}, {}
    driver = np.random.default_rng(202610090402).normal(size=(original_n, 12, 2))
    for name in MODELS:
        model = name.lower()
        start, cpu = perf_counter(), process_time()
        data = study.market_dataset(
            model,
            p,
            surface,
            driver,
            times,
            np.arange(13),
            times[1:],
            caches[model]["call"],
            premium=5.0,
            cost_rates=[0.0005, 0.005],
        )
        datasets[name] = data
        expenses.append(_expense(f"market:{name}", start, cpu))
        start, cpu = perf_counter(), process_time()
        risks[name] = study.quote_risk_dataset(p, surface, data, caches)
        expenses.append(_expense(f"risk:{name}", start, cpu))
    candidate = candidate_protocol()
    candidate["training"].update(
        original_n=original_n, updates=updates, batch_size=16, cap_seconds=30.0
    )
    candidate["validation"]["original_n"] = original_n
    start, cpu = perf_counter(), process_time()
    fits = study.fit_roster(datasets if train else {}, candidate=candidate)
    expenses.append(_expense("training:all_12", start, cpu))
    for row in fits["fits"]:
        raw = row["expense"]
        expenses.append(
            {
                "id": row["id"],
                "scope": "tiny_training",
                "parent_id": "training:all_12",
                "includes_children": True,
                "status": "complete" if row["status"] == "completed" else "failed",
                "reason": row["reason"],
                "timing": {
                    key: raw[key] for key in ["wall_seconds", "cpu_seconds", "overrun_seconds"]
                },
            }
        )
    validations, evaluations = {}, {}
    for name in MODELS:
        for universe in UNIVERSES:
            start, cpu = perf_counter(), process_time()
            selected = study.select_validation(
                datasets[name],
                risks[name],
                generator=name,
                universe=universe,
                widths=candidate["hedging"]["band_width_candidates"],
            )
            validations[f"selection:{name}:{universe}"] = selected
            expenses.append(_expense(f"validation:{name}:{universe}", start, cpu))
            start, cpu = perf_counter(), process_time()
            evaluations[f"{name}:{universe}"] = study.test_roster(
                datasets[name], risks[name], fits, selected, generator=name, universe=universe
            )
            expenses.append(_expense(f"cells:{name}:{universe}", start, cpu))
    for identifier in required_tiny_expenses():
        if identifier not in {row["id"] for row in expenses}:
            expenses.append(_expense(identifier))
    return {
        "kind": "tiny",
        "formal_pilot_qualification": "unknown",
        "work_estimate": {
            "scope": "predefined bounded smoke; no automatic formal-candidate product",
            "teacher_path_steps": {
                "Heston": original_n * 4 * sum(range(1, 13)),
                "local": original_n * 4 * (5 * 12 + 4 * sum(range(1, 12))),
            },
            "market_path_steps": 2 * original_n * 12,
            "chunk_limit_bytes": 256 * 1024**2,
        },
        "source_identity": identity,
        "candidate": candidate,
        "parameters": p,
        "fixture": "xi0 constant variance; train/validation share data; not OOS",
        "teachers": teachers,
        "caches": caches,
        "datasets": datasets,
        "risks": risks,
        "fits": fits,
        "validation": validations,
        "evaluations": evaluations,
        "expenses": expenses,
        "teacher_global_driver": teacher_driver,
        "unverified": [
            "formal37quote",
            "actual_Heston_local18states",
            "call_asian_precision",
            "premium",
            "independent_refinements",
            "Q_diagnostics",
            "full_pilot",
            "freeze",
            "main",
            "fresh",
            "CAS",
            "plots",
        ],
    }


def check_bundle(bundle):
    """Replay tiny saved boundaries, without RNG/train/optimizer/CF/PDE solves."""
    if bundle.get("kind") != "tiny":
        raise ValueError("only explicitly scoped tiny bundles are supported here")
    _same(source_identity(), bundle["source_identity"], "source_identity")
    p, surface = bundle["parameters"], ConstantVarianceField()
    n = bundle["candidate"]["training"]["original_n"]
    _check_original_fits(bundle["fits"], n, bundle["candidate"]["training"]["updates"])
    if n != len(bundle["teacher_global_driver"]):
        raise ValueError("teacher original N mismatch")
    expense_check = protocol.validate_expenses(
        bundle["expenses"], required_ids=required_tiny_expenses()
    )
    teacher_checks = {}
    driver = np.asarray(bundle["teacher_global_driver"])
    driver_id = hashlib.sha256(np.ascontiguousarray(driver).tobytes()).hexdigest()
    for model in ["heston", "local"]:
        records = bundle["teachers"][model]
        for row in records["rows"]:
            mapping = row["driver_mapping"]
            expected_slice = driver[:, mapping["start_step"] : mapping["stop_step"]]
            if mapping["aggregation_factor"] != 1:
                raise ValueError("tiny driver mapping cannot change its aggregation")
            slice_id = hashlib.sha256(np.ascontiguousarray(expected_slice).tobytes()).hexdigest()
            if (
                row["global_driver_id"] != driver_id
                or row["primitives"]["shared_driver_id"] != slice_id
                or mapping["slice_sha256"] != slice_id
            ):
                raise ValueError("saved driver/slice provenance does not match original arrays")
        rows = [{**row, "surface": surface} for row in records["rows"]]
        saved = bundle["caches"][model]["asian"]
        cache = replay.rebuild_asian_cache(
            rows,
            p,
            records["axes"],
            model=model,
            evaluation_domains=records.get("evaluation_domains"),
            saved_cache=saved,
        )["cache"]
        for key in ["f", "block_means", "support_mask", "threshold_nodes", "state_nodes"]:
            _same(cache[key], saved[key], f"{model}.asian.{key}")
        if model == "local":
            _same(cache["t0_sheet"], saved["t0_sheet"], "local.t0_sheet")
        teacher_checks[model] = {"original_n": n, "rows": len(records["rows"]), "integrity": "pass"}
    checks = {}
    for name in MODELS:
        model, data = name.lower(), bundle["datasets"][name]
        if data.get("original_n") != n or len(data["prices"]) != n or data["model"] != model:
            raise ValueError("market original N and generator identity required")
        market = replay.check_market(
            data,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=bundle["caches"][model]["call"],
            generator=model,
            latent_state=data["market"]["variance"] if model == "heston" else None,
        )
        risk = study.quote_risk_dataset(p, surface, data, bundle["caches"])
        for valuation in ["heston", "local"]:
            for key in [
                "state",
                "u1_target",
                "u2_target",
                "qualification",
                "arithmetic_valid",
                "price_covariance",
            ]:
                _same(
                    risk["models"][valuation][key],
                    bundle["risks"][name]["models"][valuation][key],
                    f"{name}.{valuation}.{key}",
                )
        for universe in UNIVERSES:
            identifier = f"selection:{name}:{universe}"
            validation = bundle["validation"][identifier]
            selected = study.select_validation(
                data,
                risk,
                generator=name,
                universe=universe,
                widths=bundle["candidate"]["hedging"]["band_width_candidates"],
            )
            for key in ["candidates", "selected_bands", "selected_baseline", "status"]:
                _same(selected[key], validation[key], f"{identifier}.{key}")
            check_validation(
                validation,
                {key: row["loss"] for key, row in selected["rollouts"].items()},
                original_n=n,
                qualifications={
                    key: row["qualified_path_mask"] for key, row in selected["rollouts"].items()
                },
            )
            expected = study.test_roster(
                data, risk, bundle["fits"], validation, generator=name, universe=universe
            )
            saved = bundle["evaluations"][f"{name}:{universe}"]
            if len(saved["cells"]) != 11 or [c["id"] for c in saved["cells"]] != [
                c["id"] for c in expected["cells"]
            ]:
                raise ValueError("all eleven original policy slots required")
            for actual, wanted in zip(saved["cells"], expected["cells"], strict=True):
                if actual["original_n"] != n:
                    raise ValueError("cell original N mismatch")
                result, recalculated = actual["result"], wanted["result"]
                for key in [
                    "holdings",
                    "raw_holdings",
                    "cash",
                    "costs",
                    "loss",
                    "discounted_pnl",
                    "discounted_gain_pnl",
                    "path_mask",
                    "qualified_path_mask",
                    "status",
                    "reason",
                ]:
                    _same(result[key], recalculated[key], f"{actual['id']}.{key}")
                cash_record = {
                    "holdings": result["holdings"],
                    "raw_holdings": result["raw_holdings"],
                    "universe": universe,
                    "original_n": n,
                    "reasons": result["reasons"],
                }
                for key in ["cash", "costs", "pnl", "discounted_pnl", "discounted_gain_pnl"]:
                    if key in result:
                        cash_record[key] = result[key]
                if "raw_account" in result:
                    cash_record["raw_account"] = result["raw_account"]
                if "point_valid" in result:
                    cash_record["point_valid"] = result["point_valid"]
                replay.check_cash(data, cash_record)
            checks[f"{name}:{universe}"] = {
                "integrity": "pass",
                "original_n": n,
                "cells": 11,
                "market": market["integrity"],
            }
    return {
        "integrity": "pass",
        "formal_pilot_qualification": "unknown",
        "kind": "tiny_saved_boundary",
        "teacher_checks": teacher_checks,
        "cells": checks,
        "expense_check": expense_check,
        "unverified": [
            "earlier_SDE_and_global_driver_generation",
            "independent_call_and_Asian_precision",
            "train_only_scaler_and_training_data_origin",
            "exported_weights_binding_to_actual_training_events",
            "original_training_loss_update_and_cap_history",
            "original_expense_timing_measurement",
            "conditional_and_binned_Q_accuracy",
            "formal37quote_and18states",
            "premium",
            "full_pilot",
            "freeze",
            "main_statistics",
            "independent_refinements",
            "fresh",
            "CAS",
            "plots",
        ],
    }


def initial_quote_pilot(directory):
    """Check the saved initial-37-quote component; full pilot remains unknown."""
    import importlib.util

    path = Path(__file__).with_name("check_initial_quotes.py")
    spec = importlib.util.spec_from_file_location("dynamic_initial_quotes_component", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    directory = Path(directory)
    metadata = json.loads((directory / "initial-quotes.json").read_text())
    with np.load(directory / "reference.npz", allow_pickle=False) as archive:
        arrays = {name: archive[name] for name in archive.files}
    checked = module.check_initial_quotes(metadata, arrays)
    return {
        "kind": "initial_quote_pilot_component",
        "component": checked,
        "formal_pilot_qualification": "unknown",
        "unverified": [
            "selected18states",
            "conditional_teacher",
            "Q_drift",
            "premium",
            "dynamic_policy_precision",
            "full_expenses",
        ],
    }


def main(argv=None):
    """Expose bounded tiny, saved pilot component, sealed main and saved check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase", required=True, choices=["tiny", "pilot", "main", "execution-main", "check"]
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--frozen", type=Path)
    parser.add_argument("--test-artifact", type=Path)
    parser.add_argument("--original-n", type=int, default=32)
    parser.add_argument("--updates", type=int, default=1)
    args = parser.parse_args(argv)
    if args.phase == "tiny":
        if args.output is None:
            parser.error("tiny requires a new immutable --output directory")
        bundle = run_tiny(original_n=args.original_n, updates=args.updates)
        saved = save_bundle(args.output, bundle)
        result = {"kind": "tiny", "receipt": saved, "checks": check_bundle(bundle)}
    elif args.phase == "pilot":
        if args.input is None:
            parser.error("pilot requires saved initial-quote component --input")
        result = initial_quote_pilot(args.input)
    elif args.phase == "check":
        if args.input is None:
            parser.error("check requires --input saved runner artifact")
        bundle, receipt = load_bundle(args.input)
        result = check_bundle(bundle) | {"receipt": receipt}
    else:
        if (
            args.frozen is None
            or args.input is None
            or args.test_artifact is None
            or args.output is None
        ):
            parser.error(
                f"{args.phase} requires --frozen, closed train/validation --input, "
                "--test-artifact and --output"
            )
        frozen = json.loads(args.frozen.read_text())
        training, _ = load_bundle(args.input)
        entry = run_execution_main if args.phase == "execution-main" else run_main
        source_provider = (
            execution_source_identity if args.phase == "execution-main" else source_identity
        )
        current_candidate = (
            execution.execution_candidate()
            if args.phase == "execution-main"
            else candidate_protocol()
        )
        result = entry(
            frozen=frozen,
            candidate=current_candidate,
            source=source_provider()["protocol_source"],
            selection_receipts=training["selection_receipts"],
            raw_validation=training["raw_validation"],
            closed_fits=training["closed_fits"],
            main_test_loader=lambda: load_bundle(args.test_artifact)[0],
        )
        receipt = save_bundle(args.output, result)
        result = {
            "main_execution": result["main_execution"],
            "qualification": result["qualification"],
            "receipt": receipt,
        }
    print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
