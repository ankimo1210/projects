"""Private v1 protocol, provenance, expense and immutable artifact boundaries.

This module performs no training, financial qualification or random draws.
Financial checkers own numerical semantics and transitive source selection.
Canonical JSON digests identify evidence; they are not accuracy certificates.
Returned dictionaries are detached snapshots. Their digests detect subsequent
mutation, rather than making Python dictionaries physically read-only.
"""

import hashlib
import io
import json
import zipfile
from pathlib import Path, PurePosixPath

import numpy as np


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _snapshot(value):
    return json.loads(_canonical(value))


def main_seeds() -> dict:
    """Return distinct local SeedSequence namespaces, with no global RNG draws.

    Stable numeric tags 1..11 and root entropy 2026100904 are part of v1.
    Train/validation slots refer to Heston/local; test and oracle have three
    independent slots shared across generators by an explicit CRN convention.
    Init IDs 11/29/47 identify policy initializations, not market streams.
    """
    counts = {
        "train": 2,
        "validation": 2,
        "test": 3,
        "teacher": 2,
        "oracle": 3,
        "bootstrap": 1,
        "pilot": 6,
        "premium": 1,
        "refinement": 3,
        "fresh": 3,
        "optional_p": 3,
    }
    return {
        name: [
            int(np.random.SeedSequence([2026100904, tag, slot]).generate_state(1)[0])
            for slot in range(count)
        ]
        for tag, (name, count) in enumerate(counts.items(), 1)
    }


def candidate_protocol() -> dict:
    """Return the fixed original v1 candidate; no measured achievement is implied.

    Selection may choose only the listed teacher/test N and grid candidates.
    Precision gates, main dates, all init IDs and original counts stay fixed.
    Changes require a new source/candidate revision and new pilot/review.
    """
    return {
        "version": "rb-f04-dynamic-v1",
        "market": {
            "generators": ["Heston", "local"],
            "spot": 100.0,
            "rate": 0.03,
            "dividend_yield": 0.0,
            "heston": {"v0": 0.04, "kappa": 2.0, "mean_variance": 0.04, "xi": 0.3, "rho": -0.7},
        },
        "claim": {
            "kind": "arithmetic_asian_call",
            "strike": 100.0,
            "expiry": 1.0,
            "quantity": 1.0,
            "fixing_times": [j / 12 for j in range(1, 13)],
        },
        "universes": ["U1", "U2"],
        "traded_call": {"strike": 100.0, "expiry": 1.25, "rolling": False},
        "hedging": {
            "dates": [j / 12 for j in range(12)],
            "half_spreads": [0.0005, 0.005],
            "position_bounds": [-2.0, 2.0],
            "band_width_candidates": [0.0, 0.01, 0.02, 0.05, 0.1, 0.2],
            "baseline_rule": "minimum_validation_discounted_pnl_mse",
            "checkpoint_rule": "last_finite_completed",
            "frequency_diagnostics": [24, 48],
        },
        "training": {
            "original_n": 8192,
            "initializations": [11, 29, 47],
            "updates": 512,
            "batch_size": 256,
            "optimizer": "Adam",
            "learning_rate": 0.003,
            "cap_seconds": 300.0,
            "architecture": [9, 32, 32, 2],
            "activation": "tanh",
            "device": "cpu",
            "dtype": "float64",
            "price_level": 768,
        },
        "validation": {"original_n": 2048, "selection_only": True},
        "sde": {"main_levels": [192, 384, 768], "independent_level": 1536},
        "teacher": {
            "n_candidates": [1024, 4096, 16384, 65536],
            "iid_blocks": 16,
            "driver_level": 768,
            "grid_candidates": ["coarse", "high"],
            "heston_state_counts": [9, 13],
            "local_spot_counts": [9, 17],
            "local_state_counts": [5, 7],
            "threshold_counts": [33, 65],
            "heston_bounds": [0.00001, 0.5],
            "local_bounds": [0.25, 4.0],
        },
        "test": {
            "n_candidates": [8192, 16384, 32768],
            "seed_slots": 3,
            "minimum_n": 8192,
            "mean_loss_se_max": 0.01,
            "mse_se_absolute": 0.001,
            "mse_se_relative": 0.02,
            "selection_rule": "smallest_n_from_worst_pilot_greek_band_se",
        },
        "premium": {
            "model": "Heston",
            "original_n": 65536,
            "steps_per_year": 1536,
            "seed": main_seeds()["premium"][0],
        },
        "statistics": {
            "block_paths": 64,
            "bootstrap_replicates": 2000,
            "family_count": 8,
            "alpha": 0.05,
            "absolute_improvement": 0.001,
            "relative_improvement": 0.05,
            "all_initializations_required": True,
        },
        "gates": {
            "initial_quote_error": 0.001,
            "cf_order_cutoff_error": 1e-8,
            "call_price_error": 0.001,
            "call_stock_derivative_error": 0.002,
            "call_scaled_state_derivative_error": 0.01,
            "call_accumulated_drift_error": 0.01,
            "teacher_price_se": 0.03,
            "stock_position_se": 0.002,
            "call_position_se": 0.005,
            "asian_price_error": 0.05,
            "stock_position_error": 0.01,
            "call_position_error": 0.01,
            "quote_condition_number": 0.25,
            "pnl_rms_difference": 0.05,
            "mse_difference_absolute": 0.001,
            "mse_difference_relative": 0.02,
        },
        "pilot": {"selected_states": 18, "initial_quotes": 37, "tiny_cells": 44, "tiny_fits": 4},
        "limits": {"job_path_steps": 1_000_000_000, "chunk_uncompressed_bytes": 256 * 1024**2},
        "seeds": main_seeds(),
    }


def study_roster() -> dict:
    """Return 12 immutable-ID fit slots and 44 primary cell slots, not successes.

    Each cell has explicit generator, valuation, universe, policy,
    training_generator and initialization fields. Null is a real nonapplicable
    field. Dimensions add three test seed slots and three levels to every cell;
    these dimensions do not multiply an IID path denominator by nine.
    """
    models, universes, initializations = ["Heston", "local"], ["U1", "U2"], [11, 29, 47]
    fits = [
        {"id": f"fit:{g}:{u}:init{i}", "training_generator": g, "universe": u, "initialization": i}
        for g in models
        for u in universes
        for i in initializations
    ]
    policies = [
        {
            "policy_id": "no_hedge",
            "policy": "no_hedge",
            "valuation": None,
            "training_generator": None,
            "initialization": None,
        }
    ]
    policies += [
        {
            "policy_id": f"{policy}:{m}",
            "policy": policy,
            "valuation": m,
            "training_generator": None,
            "initialization": None,
        }
        for policy in ["greek", "band"]
        for m in models
    ]
    policies += [
        {
            "policy_id": f"nn:train{g}:init{i}",
            "policy": "nn",
            "valuation": None,
            "training_generator": g,
            "initialization": i,
        }
        for g in models
        for i in initializations
    ]
    cells = [
        {"id": f"cell:{g}:{u}:{p['policy_id']}", "generator": g, "universe": u, **p}
        for g in models
        for u in universes
        for p in policies
    ]
    return {
        "fits": fits,
        "primary_cells": cells,
        "dimensions": {"test_seed_slots": [0, 1, 2], "sde_levels": [192, 384, 768]},
    }


def source_registry(root, relative_paths) -> dict:
    """Hash explicitly selected existing canonical files under root.

    The caller must include the actual transitive financial import closure.
    This function validates filenames and bytes, not dependency completeness
    or mathematical correctness. Canonical paths use relative POSIX spelling
    without aliases, parent traversal, duplicates or symlink indirection.
    """
    root = Path(root).resolve(strict=True)
    result = {}
    for name in relative_paths:
        name = str(name)
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or str(relative) != name
            or ".." in relative.parts
            or "\\" in name
            or name in result
        ):
            raise ValueError("unique canonical relative source paths required")
        path = root / name
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root) or resolved != path or not path.is_file():
            raise ValueError("existing canonical source file under root required")
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not result:
        raise ValueError("source registry cannot be empty")
    return result


def _finite_nonnegative(value, name):
    try:
        value = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be measured, finite and nonnegative") from error
    if not np.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be measured, finite and nonnegative")
    return value


def _is_sha(value):
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _verified(receipt, expected_inputs):
    verification = receipt.get("verification", {})
    if (
        not verification.get("checker")
        or not _is_sha(verification.get("evidence_sha256"))
        or verification.get("inputs") != expected_inputs
    ):
        raise ValueError(
            "caller-verified evidence receipt and exact input digest bindings required"
        )


def freeze_contract(candidate, source, pilot, review, selection) -> dict:
    """Bind fixed candidate/source/pilot/review/selection into detached snapshots.

    This is a receipt boundary, not a financial gate recalculation. The caller
    must first run an independent saved checker over original raw arrays and
    emit verification={checker, evidence_sha256, inputs}; inputs holds the
    canonical SHA256 for candidate/source, and review additionally binds pilot.
    Canonical bytes are UTF-8 json.dumps(sort_keys=True, separators=(",", ":"),
    allow_nan=False). Digests identify evidence, not reviewer authenticity.

    pilot requires qualification="qualified", original_counts exactly matching
    candidate.pilot, finite nonnegative measurements for every candidate gate
    except mse_difference_absolute/relative (instead baseline_mse and
    mse_difference), teacher_n/grid by model, all three test_precision rows
    (original_n/worst_mean_loss_se/worst_mse_se/baseline_mse), and premium
    (value/se/scheme_error plus original_n/steps_per_year/seed). Measurements
    are worst-case reductions over all required raw cases, with failed and
    unmeasured cases refusing qualification; this aggregation is caller-owned.
    review requires approved code/math/pilot scopes and no unresolved issues.

    selection must exactly bind those teacher N/grids, the smallest qualified
    test N, premium, and candidate band widths/baseline/checkpoint algorithms.
    A flag-only or unmeasured formal pilot cannot freeze or launch main.
    """
    if _digest(candidate) != _digest(candidate_protocol()):
        raise ValueError("candidate differs from fixed original v1 protocol")
    if not source or not all(_is_sha(value) for value in source.values()):
        raise ValueError("nonempty source registry of SHA256 values required")
    inputs = {"candidate": _digest(candidate), "source": _digest(source)}
    if pilot.get("qualification") != "qualified":
        raise ValueError("formally qualified pilot required")
    _verified(pilot, inputs)
    if pilot.get("original_counts") != candidate["pilot"]:
        raise ValueError("all original pilot state/quote/cell/fit counts required")
    measurements = pilot.get("measurements", {})
    for name, limit in candidate["gates"].items():
        if name in ["mse_difference_absolute", "mse_difference_relative"]:
            continue
        if _finite_nonnegative(measurements.get(name), name) > limit:
            raise ValueError(f"pilot exceeds fixed {name} gate")
    baseline_mse = _finite_nonnegative(measurements.get("baseline_mse"), "baseline_mse")
    mse_difference = _finite_nonnegative(measurements.get("mse_difference"), "mse_difference")
    if mse_difference > max(
        candidate["gates"]["mse_difference_absolute"],
        candidate["gates"]["mse_difference_relative"] * baseline_mse,
    ):
        raise ValueError("pilot exceeds fixed MSE refinement gate")
    models = candidate["market"]["generators"]
    teacher_n, teacher_grid = pilot.get("teacher_n", {}), pilot.get("teacher_grid", {})
    if set(teacher_n) != set(models) or set(teacher_grid) != set(models):
        raise ValueError("teacher selection for both original models required")
    if any(teacher_n[m] not in candidate["teacher"]["n_candidates"] for m in models):
        raise ValueError("teacher N outside fixed candidates")
    if any(teacher_grid[m] not in candidate["teacher"]["grid_candidates"] for m in models):
        raise ValueError("teacher grid outside fixed candidates")
    precisions = pilot.get("test_precision", [])
    if [r.get("original_n") for r in precisions] != candidate["test"]["n_candidates"]:
        raise ValueError("ordered pilot precision projections for all test N required")
    qualified_n = []
    for row in precisions:
        mean_se = _finite_nonnegative(row.get("worst_mean_loss_se"), "pilot mean-loss SE")
        mse_se = _finite_nonnegative(row.get("worst_mse_se"), "pilot MSE SE")
        baseline = _finite_nonnegative(row.get("baseline_mse"), "pilot baseline MSE")
        if mean_se <= candidate["test"]["mean_loss_se_max"] and mse_se <= max(
            candidate["test"]["mse_se_absolute"], candidate["test"]["mse_se_relative"] * baseline
        ):
            qualified_n.append(row["original_n"])
    if not qualified_n:
        raise ValueError("no test N meets fixed pilot precision gates")
    premium = pilot.get("premium", {})
    for name in ["value", "se", "scheme_error"]:
        _finite_nonnegative(premium.get(name), f"premium {name}")
    if any(
        premium.get(name) != candidate["premium"][name]
        for name in ["original_n", "steps_per_year", "seed"]
    ):
        raise ValueError("premium requires reserved independent original-N pilot")
    if review.get("qualification") != "qualified":
        raise ValueError("independent code/math/pilot review qualification required")
    _verified(review, inputs | {"pilot": _digest(pilot)})
    if (
        review.get("scopes") != {"code": "approved", "math": "approved", "pilot": "approved"}
        or review.get("unresolved_issues") != []
    ):
        raise ValueError("all review scopes must approve without unresolved issues")
    expected_selection = {
        "teacher_n": teacher_n,
        "teacher_grid": teacher_grid,
        "test_n": qualified_n[0],
        "premium": premium,
        "band_width_candidates": candidate["hedging"]["band_width_candidates"],
        "baseline_rule": candidate["hedging"]["baseline_rule"],
        "checkpoint_rule": candidate["hedging"]["checkpoint_rule"],
    }
    if _digest(selection) != _digest(expected_selection):
        raise ValueError("selection differs from qualified pilot or fixed candidate")
    components = {
        "candidate": candidate,
        "source": source,
        "pilot": pilot,
        "review": review,
        "selection": selection,
    }
    frozen = _snapshot(components)
    frozen["schema"] = "rb-f04-source-freeze-v1"
    frozen["bindings"] = {name: _digest(value) for name, value in components.items()}
    frozen["frozen_sha256"] = _digest(frozen)
    return frozen


def assert_main_ready(frozen, candidate, source, selection_receipts) -> None:
    """Refuse test access until all original attempts and selections are closed.

    This is called at the train/validation-to-test boundary, not to authorize
    pre-freeze training. selection_receipts requires test_opened=False and
    verification inputs binding frozen/candidate/source. It contains all 12
    fit records and four generator/universe validation records. Each fit has
    id/status/attempted/original_n/requested_updates/updates/elapsed_seconds/
    selection_status/validation_original_n and, when selected, checkpoint_id.
    Failed fits or failed checkpoint selections retain reason and original N;
    they never become members of a completed NN family. Completed fits must
    have exactly 512 updates and include final diagnostics within the cap.

    Validation records have id/generator/universe/status/original_n/candidates.
    Every Greek and every width candidate of both valuation models has an
    id/status/original_n/mse (failed candidates also retain reason). Completed
    selections require selected_bands={model: candidate_id or None} and a
    selected_baseline; each minimizes finite original-N validation MSE. Ties
    use the fixed Heston/local, Greek-then-width candidate order. An all-failed
    band requires band_failures[model]; all-failed baseline selection requires
    status="failed" and a reason. No fallback or test-based reselection occurs.

    Raw finance, attempt history, weights and timing completeness are checked
    by the caller's bound saved checker. Passing this boundary is neither a
    financial acceptance nor a claim that failed fits completed successfully.
    """
    required = {
        "schema",
        "bindings",
        "candidate",
        "source",
        "pilot",
        "review",
        "selection",
        "frozen_sha256",
    }
    if not required <= frozen.keys():
        raise ValueError("complete immutable frozen protocol required")
    identity = {key: value for key, value in frozen.items() if key != "frozen_sha256"}
    if frozen["frozen_sha256"] != _digest(identity):
        raise ValueError("frozen protocol was modified")
    expected = freeze_contract(
        candidate, source, frozen["pilot"], frozen["review"], frozen["selection"]
    )
    if _digest(frozen) != _digest(expected):
        raise ValueError("current source/candidate differs from frozen identity")
    _verified(
        selection_receipts,
        {
            "frozen": frozen["frozen_sha256"],
            "candidate": frozen["bindings"]["candidate"],
            "source": frozen["bindings"]["source"],
        },
    )
    if selection_receipts.get("test_opened") is not False:
        raise ValueError("test must stay unopened until all selections are closed")
    fits = selection_receipts.get("fits", [])
    ids = [row.get("id") for row in fits]
    if (
        len(ids) != 12
        or len(set(ids)) != 12
        or set(ids) != {row["id"] for row in study_roster()["fits"]}
    ):
        raise ValueError("all 12 distinct original fit attempts required")
    for row in fits:
        if (
            row.get("attempted") is not True
            or row.get("original_n") != candidate["training"]["original_n"]
            or row.get("validation_original_n") != candidate["validation"]["original_n"]
            or row.get("requested_updates") != candidate["training"]["updates"]
            or row.get("status") not in ["completed", "failed"]
            or row.get("selection_status") not in ["completed", "failed"]
        ):
            raise ValueError("original-N attempted fits and closed validation selections required")
        updates = _finite_nonnegative(row.get("updates"), "fit updates")
        if updates != int(updates) or updates > candidate["training"]["updates"]:
            raise ValueError("invalid fit update count")
        if row.get("elapsed_seconds") is not None:
            _finite_nonnegative(row["elapsed_seconds"], "fit elapsed_seconds")
        if row["status"] == "completed":
            elapsed = _finite_nonnegative(row.get("elapsed_seconds"), "fit elapsed_seconds")
            if (
                updates != candidate["training"]["updates"]
                or elapsed > candidate["training"]["cap_seconds"]
            ):
                raise ValueError("incomplete or over-cap fit cannot be labeled completed")
        elif not row.get("reason") or row["selection_status"] != "failed":
            raise ValueError("failed fit requires reason and failed checkpoint selection")
        if row["selection_status"] == "completed":
            if row.get("checkpoint_id") != candidate["hedging"]["checkpoint_rule"]:
                raise ValueError("fixed completed checkpoint selection required")
        elif not row.get("reason"):
            raise ValueError("failed checkpoint selection requires original reason")
    models, universes = candidate["market"]["generators"], candidate["universes"]
    validations = selection_receipts.get("validation", [])
    ids = [row.get("id") for row in validations]
    if (
        len(ids) != 4
        or len(set(ids)) != 4
        or set(ids) != {f"selection:{g}:{u}" for g in models for u in universes}
    ):
        raise ValueError("all four original generator/universe baseline selections required")
    candidate_ids = [
        name
        for model in models
        for name in [f"greek:{model}"]
        + [f"band:{model}:width{w:g}" for w in candidate["hedging"]["band_width_candidates"]]
    ]
    for row in validations:
        if (
            row.get("generator") not in models
            or row.get("universe") not in universes
            or row["id"] != f"selection:{row.get('generator')}:{row.get('universe')}"
            or row.get("original_n") != candidate["validation"]["original_n"]
            or row.get("status") not in ["completed", "failed"]
        ):
            raise ValueError("closed original-N baseline validation required")
        candidates = row.get("candidates", [])
        ids = [item.get("id") for item in candidates]
        if len(ids) != len(candidate_ids) or set(ids) != set(candidate_ids):
            raise ValueError("all original Greek and band width candidates required")
        scores = {}
        for item in candidates:
            if item.get("original_n") != candidate["validation"]["original_n"]:
                raise ValueError("validation failure paths cannot change original N")
            if item.get("status") == "completed":
                scores[item["id"]] = _finite_nonnegative(item.get("mse"), "validation MSE")
            elif item.get("status") != "failed" or not item.get("reason"):
                raise ValueError("validation candidates must be completed or explicit failures")
        if row["status"] == "failed":
            if not row.get("reason") or scores:
                raise ValueError(
                    "failed baseline selection requires all-failed candidates and reason"
                )
            continue
        if not scores or set(row.get("selected_bands", {})) != set(models):
            raise ValueError("completed validation requires baseline and both band decisions")
        best = min(
            scores, key=lambda identifier: (scores[identifier], candidate_ids.index(identifier))
        )
        if row.get("selected_baseline") != best:
            raise ValueError("baseline must minimize original-N validation MSE")
        for model in models:
            band_ids = [
                identifier for identifier in scores if identifier.startswith(f"band:{model}:")
            ]
            selected = row["selected_bands"][model]
            if band_ids:
                best_band = min(
                    band_ids,
                    key=lambda identifier: (scores[identifier], candidate_ids.index(identifier)),
                )
                if selected != best_band:
                    raise ValueError("band width must minimize original-N validation MSE")
            elif selected is not None or not row.get("band_failures", {}).get(model):
                raise ValueError(
                    "all-failed band must remain explicit failure, not width-zero fallback"
                )


def validate_expenses(expenses, *, required_ids) -> dict:
    """Retain raw records and charge each inclusive expense tree once.

    Each record requires id, scope, status, parent_id, includes_children, and
    timing keys wall_seconds/cpu_seconds/overrun_seconds. includes_children must
    be a bool; truthy numeric/string values are invalid. Status complete or
    failed permits nonnegative measured values or None (unknown); failed also
    requires a reason. Pending requires all three timings None. Overrun is a
    diagnostic subset of wall time, never an extra additive charge.

    Parent IDs must exist and form a forest. An inclusive ancestor covers all
    descendants regardless of their status; their raw cost/failure survives.
    Any None in included records makes the corresponding total None; measured
    subtotals are labeled separately. required_ids is the caller's full phase
    ledger, not a list this function is allowed to infer from surviving rows.
    """
    records = _snapshot(list(expenses))
    required = list(required_ids)
    timing_keys = {"wall_seconds", "cpu_seconds", "overrun_seconds"}
    fields = {"id", "scope", "status", "parent_id", "includes_children", "timing"}
    by_id = {}
    for record in records:
        if not fields <= record.keys() or not record["id"] or not record["scope"]:
            raise ValueError("expense ID, scope, parent, status and timing keys required")
        if not isinstance(record["includes_children"], bool):
            raise ValueError("includes_children must be a bool")
        identifier = record["id"]
        if identifier in by_id or record["status"] not in ("complete", "failed", "pending"):
            raise ValueError("unique expense IDs and known status required")
        timing = record["timing"]
        if not timing_keys <= timing.keys():
            raise ValueError("complete timing keyset required, including unknown values")
        for value in timing.values():
            if value is not None and (not np.isfinite(value) or value < 0):
                raise ValueError("timings must be finite nonnegative values or None")
        if record["status"] == "pending" and any(v is not None for v in timing.values()):
            raise ValueError("pending timings must remain None")
        if record["status"] == "failed" and not record.get("reason"):
            raise ValueError("failed expense requires its original reason")
        if (
            timing["wall_seconds"] is not None
            and timing["overrun_seconds"] is not None
            and timing["overrun_seconds"] > timing["wall_seconds"]
        ):
            raise ValueError("overrun is part of wall time")
        by_id[identifier] = record
    if len(set(required)) != len(required) or not set(required) <= by_id.keys():
        raise ValueError("required expense IDs erased or duplicated")
    excluded = []
    for record in records:
        parent, ancestors, covered = record["parent_id"], {record["id"]}, False
        while parent is not None:
            if parent not in by_id or parent in ancestors:
                raise ValueError("expense parents must exist and be acyclic")
            ancestors.add(parent)
            covered |= by_id[parent]["includes_children"]
            parent = by_id[parent]["parent_id"]
        if covered:
            excluded.append(record["id"])
    charged = [r for r in records if r["id"] not in excluded]

    def totals(rows):
        measured = {
            key: sum(r["timing"][key] for r in rows if r["timing"][key] is not None)
            for key in ["wall_seconds", "cpu_seconds"]
        }
        complete = {
            key: measured[key] if all(r["timing"][key] is not None for r in rows) else None
            for key in measured
        }
        return complete, measured

    raw_total, raw_measured = totals(records)
    charged_total, charged_measured = totals(charged)
    return {
        "raw_records": records,
        "charged_ids": [r["id"] for r in charged],
        "excluded_ids": excluded,
        "unknown_ids": [r["id"] for r in records if any(v is None for v in r["timing"].values())],
        "raw_totals": raw_total,
        "charged_totals": charged_total,
        "raw_measured_subtotals": raw_measured,
        "charged_measured_subtotals": charged_measured,
    }


def write_artifact(directory, *, metadata, arrays, compress=False) -> dict:
    """Write one new immutable JSON+nonobject NPZ chunk and return its receipt.

    metadata.json contains detached metadata and array dtype/shape/nbytes.
    receipt.json binds exact metadata/NPZ bytes and is itself canonical JSON.
    Expanded NPY payload (including headers) is capped at 256 MiB per chunk;
    larger studies split at caller-owned date/state/path boundaries. Object
    arrays cannot be serialized; NaN, booleans and numeric failure arrays are
    preserved. Existing directories are never silently overwritten.
    """
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError(f"immutable artifact already exists: {directory}")
    data = {name: np.asarray(array) for name, array in arrays.items()}
    if any(a.dtype.hasobject for a in data.values()):
        raise ValueError("object arrays are prohibited; no pickle")
    limit = 256 * 1024**2
    if sum(a.nbytes for a in data.values()) > limit:
        raise ValueError("artifact chunk exceeds 256 MiB uncompressed")
    buffer = io.BytesIO()
    (np.savez_compressed if compress else np.savez)(buffer, **data)
    array_bytes = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(array_bytes)) as archive:
        expanded = sum(item.file_size for item in archive.infolist())
    if expanded > limit:
        raise ValueError("artifact chunk exceeds 256 MiB uncompressed including headers")
    manifest = {
        "schema": "rb-f04-array-chunk-v1",
        "metadata": metadata,
        "arrays": {
            name: {"dtype": array.dtype.str, "shape": list(array.shape), "nbytes": array.nbytes}
            for name, array in data.items()
        },
    }
    metadata_bytes = _canonical(manifest)
    receipt = {
        "schema": "rb-f04-array-receipt-v1",
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "arrays_sha256": hashlib.sha256(array_bytes).hexdigest(),
        "uncompressed_bytes": expanded,
    }
    receipt["artifact_sha256"] = _digest(receipt)
    directory.mkdir(parents=True, exist_ok=False)
    for filename, payload in [
        ("metadata.json", metadata_bytes),
        ("arrays.npz", array_bytes),
        ("receipt.json", _canonical(receipt)),
    ]:
        with (directory / filename).open("xb") as stream:
            stream.write(payload)
    return receipt


def read_artifact(directory) -> tuple[dict, dict, dict]:
    """Read only saved bytes after provenance validation, with no RNG or training.

    Return (metadata, arrays, receipt). Checks hashes, canonical receipt,
    array shape/dtype and chunk size. The caller's saved-only semantic checker
    must then recalculate finance, original denominators, expense ledger and
    qualifications from raw arrays; matching bytes alone cannot pass them.
    """
    directory = Path(directory)
    try:
        metadata_bytes = (directory / "metadata.json").read_bytes()
        array_bytes = (directory / "arrays.npz").read_bytes()
        receipt_bytes = (directory / "receipt.json").read_bytes()
    except FileNotFoundError as error:
        raise ValueError("artifact is incomplete") from error
    receipt = json.loads(receipt_bytes)
    identity = {key: value for key, value in receipt.items() if key != "artifact_sha256"}
    if (
        receipt_bytes != _canonical(receipt)
        or receipt.get("schema") != "rb-f04-array-receipt-v1"
        or receipt.get("artifact_sha256") != _digest(identity)
        or receipt.get("metadata_sha256") != hashlib.sha256(metadata_bytes).hexdigest()
        or receipt.get("arrays_sha256") != hashlib.sha256(array_bytes).hexdigest()
    ):
        raise ValueError("artifact byte provenance mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(array_bytes)) as archive:
            expanded = sum(item.file_size for item in archive.infolist())
        if expanded > 256 * 1024**2 or expanded != receipt.get("uncompressed_bytes"):
            raise ValueError("artifact expanded size mismatch or exceeds 256 MiB")
        manifest = json.loads(metadata_bytes)
        with np.load(io.BytesIO(array_bytes), allow_pickle=False) as stored:
            arrays = {name: stored[name] for name in stored.files}
    except (zipfile.BadZipFile, OSError) as error:
        raise ValueError("invalid NPZ artifact") from error
    if (
        manifest.get("schema") != "rb-f04-array-chunk-v1"
        or arrays.keys() != manifest.get("arrays", {}).keys()
    ):
        raise ValueError("artifact array roster mismatch")
    for name, array in arrays.items():
        expected = manifest["arrays"][name]
        if expected != {
            "dtype": array.dtype.str,
            "shape": list(array.shape),
            "nbytes": array.nbytes,
        }:
            raise ValueError("artifact array schema mismatch")
    return manifest["metadata"], arrays, receipt
