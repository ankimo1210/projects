"""Saved-only raw pilot arithmetic with explicit unclosed obligations.

This checker never generates financial paths, runs CF/PDE, retrains, or repairs
failed states. Byte hashes bind evidence; raw calculations establish only their
stated numerical boundary. It does not create an independent-review decision.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

if __name__ == "__main__":
    _CLI_ROOT = Path(__file__).resolve().parents[4]
    sys.path[:0] = [
        str(_CLI_ROOT / "johnhull/hullkit/src"),
        str(_CLI_ROOT / "deep_hedge_price/src"),
    ]

import numpy as np
import run_reference as runner

from deep_hedge_price import _dynamic_hedging_execution as execution
from deep_hedge_price import _dynamic_hedging_protocol as protocol
from deep_hedge_price import _dynamic_hedging_replay as replay

ROOT = Path(__file__).resolve().parents[4]


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _path_order(record, n):
    _require(
        np.array_equal(np.asarray(record["path_ids"]), np.arange(n)),
        "original absolute path ordering mismatch",
    )


def _moments(samples, original_n):
    samples = np.asarray(samples, dtype=float)
    _require(len(samples) == original_n and original_n >= 2, "original sample denominator mismatch")
    shape = samples.shape[1:]
    if not np.isfinite(samples).all():
        return {
            "mean": np.full(shape, np.nan),
            "standard_errors": np.full(shape, np.nan),
            "covariance": np.full((int(np.prod(shape)),) * 2, np.nan),
            "block_means": None,
            "block_covariance": None,
        }
    flat = samples.reshape(original_n, -1)
    covariance = np.atleast_2d(np.cov(flat, rowvar=False, ddof=1)) / original_n
    result = {
        "mean": samples.mean(axis=0),
        "standard_errors": np.sqrt(np.diag(covariance)).reshape(shape),
        "covariance": covariance,
        "block_means": None,
        "block_covariance": None,
    }
    if original_n >= 16 and original_n % 16 == 0:
        blocks = samples.reshape(16, original_n // 16, *shape).mean(axis=1)
        result.update(
            block_means=blocks,
            block_covariance=np.atleast_2d(np.cov(blocks.reshape(16, -1), rowvar=False, ddof=1))
            / 16,
        )
    return result


def check_teacher_record(record, parameters, surface, *, artifact_context=None):
    """Recompute labels once on original N; no chunk-average pseudo-replication."""
    n = record["original_n"]
    _path_order(record, n)
    _require(
        n >= 16
        and n % 16 == 0
        and np.array_equal(record["cluster_ids"], np.arange(n) // (n // 16)),
        "original 16 global cluster assignment mismatch",
    )
    stop = 0
    for chunk in record["chunks"]:
        _require(
            chunk["path_start"] == stop and chunk["path_stop"] > stop,
            "teacher chunk path gap/reorder",
        )
        stop = chunk["path_stop"]
        _require(
            chunk["path_steps"]
            == (chunk["path_stop"] - chunk["path_start"]) * chunk["global_steps"],
            "teacher chunk path-step cost mismatch",
        )
        _require(
            chunk["normal_expanded_bytes"] == chunk["path_steps"] * 16,
            "teacher chunk normal bytes mismatch",
        )
        _require(
            chunk["path_steps"] <= 1_000_000_000
            and chunk["normal_expanded_bytes"] <= 256 * 1024**2,
            "teacher original job cap exceeded",
        )
    _require(
        stop == n
        and record["primitives"]["N"] == n
        and record["primitives"]["original_path_count"] == n,
        "teacher original path count mismatch",
    )
    full_sde_replayed = False
    if record.get("driver") is not None:
        from hullkit._dynamic_hedging_conditional import teacher_primitives
        from run_pilot import _merge_primitives, read_teacher_driver_chunks

        driver = record["driver"]
        restart = record["restart"]
        _require(
            driver["status"] == "executed"
            and driver["seed"] == record["seed"]
            and driver["original_n"] == n,
            "original teacher SDE driver changed",
        )
        full_digest = hashlib.sha256()
        slice_digest = hashlib.sha256()
        originals = []
        begin = restart["start_index"]
        for chunk in read_teacher_driver_chunks(driver, artifact_context=artifact_context):
            normals = chunk["normal"]
            sliced = normals[:, begin:]
            full_digest.update(normals.tobytes())
            slice_digest.update(np.ascontiguousarray(sliced).tobytes())
            lo, hi = chunk["path_start"], chunk["path_stop"]
            spot = np.asarray(restart["spot"])
            state = np.asarray(restart["state"])
            original = teacher_primitives(
                record["model"].lower(),
                parameters,
                sliced,
                calendar_times=np.asarray(restart["calendar_times"])[begin:],
                fixing_indices=np.asarray(restart["fixing_indices"]),
                spot=spot.item() if spot.ndim == 0 else spot[lo:hi],
                state=state.item() if state.ndim == 0 else state[lo:hi],
                memory_count=record["date_index"],
                surface=surface,
                compact_status=True,
            )
            originals.append(original)
        computed = _merge_primitives(originals, n, slice_digest.hexdigest())
        _require(
            full_digest.hexdigest() == record["global_driver_id"] == driver["global_driver_id"],
            "full original SDE driver hash binding differs",
        )
        runner._same(computed, record["primitives"], "full saved-driver SDE primitive replay")
        full_sde_replayed = True
    checked = replay.replay_teacher(record["primitives"], record["thresholds"], parameters, surface)
    labels = checked["labels"]
    labels["shared_driver_id"] = record["global_driver_id"]
    labels["date_index"] = record["date_index"]
    runner._same(labels, record["labels"], "teacher saved labels")
    mapping = record["driver_mapping"]
    _require(
        mapping["original_n"] == n
        and mapping["aggregation_factor"] == 1
        and mapping["slice_sha256"] == record["primitives"]["shared_driver_id"],
        "global slice binding mismatch",
    )
    _require(
        record["date_index"] == int(record["primitives"]["memory_count"]),
        "teacher original fixing count mismatch",
    )
    masks = np.asarray(record["primitives"]["path_mask"])
    status = np.asarray(labels["status"]).astype(str)
    unknown = ~np.isin(status, ["ready", "not_required_linear_claim", "not_required_settled_claim"])
    return {
        "scope": "saved_primitive_boundary",
        "full_saved_driver_sde_replayed": full_sde_replayed,
        "original_n": n,
        "invalid_path_count": int((~masks).sum()),
        "raw_status": status,
        "raw_standard_errors": np.asarray(labels["f_se"]).copy(),
        "gate_standard_errors": [
            None if bad else float(se) for bad, se in zip(unknown, labels["f_se"], strict=True)
        ],
        "unknown_node_count": int(unknown.sum()),
        "labels": labels,
        "financial_qualification": "unknown",
        "unverified": (["earlier_sde"] if not full_sde_replayed else [])
        + ["global_driver_generation", "independent_accuracy"],
    }


def paired_pnl_metrics(base, refined, *, original_n, path_ids=None):
    """Paired original-N comparison; never condition on surviving paths."""
    a, b = np.asarray(base, dtype=float), np.asarray(refined, dtype=float)
    _require(a.shape == b.shape == (original_n,), "paired P&L original denominator mismatch")
    if path_ids is not None:
        _require(np.array_equal(path_ids, np.arange(original_n)), "paired P&L path order mismatch")
    diff = b - a
    invalid = ~np.isfinite(a) | ~np.isfinite(b)
    return {
        "original_n": original_n,
        "invalid_count": int(invalid.sum()),
        "raw_difference": diff.copy(),
        "pnl_rms_difference": None if invalid.any() else float(np.sqrt(np.mean(diff**2))),
        "baseline_mse": None if invalid.any() else float(np.mean(a * a)),
        "mse_difference": None if invalid.any() else float(abs(np.mean(b * b - a * a))),
        "paired_difference_statistics": _moments(diff[:, None], original_n),
    }


def check_paired_pnl_record(record):
    n = record["original_n"]
    _path_order(record, n)
    shared_checked = False
    if record.get("selection_inputs") is not None:
        from run_pilot import cell_policy_arguments, input_identity

        selection = record["selection_inputs"]
        _require(
            input_identity(record["identity"]) == input_identity(selection["identity"]),
            "original paired selection identity changed",
        )
        arguments = cell_policy_arguments(**selection)
        for prefix in ("base", "refined"):
            _require(
                input_identity(arguments) == input_identity(record[prefix + "_arguments"]),
                "paired arguments differ from original cell selection",
            )
    if record.get("shared_market") is not None:
        shared = record["shared_market"]
        check_market_pair_record(shared)
        expected = runner.payload_digest(
            {k: shared[k] for k in ("seed", "driver_map", "original_n", "levels", "frequencies")}
        )
        _require(
            record["shared_driver_binding"] == expected, "paired raw shared-driver binding changed"
        )
        indices = record.get("dataset_indices", [0, 1])
        _require(
            len(indices) == 2 and all(i in (0, 1) for i in indices),
            "original paired dataset indices invalid",
        )
        if record.get("refinement_kind") in ("teacher_N", "teacher_grid", "position", "pnl"):
            _require(
                indices[0] == indices[1],
                "single changed numerical ingredient requires same original market",
            )
        for key, index in zip(("base_dataset", "refined_dataset"), indices, strict=True):
            runner._same(record[key], shared["datasets"][index], "paired original market dataset")
        shared_checked = True
    for prefix in ("base", "refined"):
        source = record.get(prefix + "_risk_source")
        if source is not None:
            if source.get("kind") == "bump_risk":
                check_bump_risk_record(source)
                index = record.get(prefix + "_risk_width_index")
                if index is not None:
                    _require(
                        prefix == "refined"
                        and record["refinement_kind"] == "position"
                        and index in (0, 1, 2),
                        "original bump width variant binding invalid",
                    )
                    risk = source["risk_variants"][index]
                else:
                    risk = source["value"]
            elif source.get("kind") == "quote_risk":
                check_wrapped_operation(source, "quote_risk", {})
                risk = source["value"]
            else:
                raise ValueError("unknown original paired risk producer")
            runner._same(
                record[prefix + "_risk"], risk, "actual paired width variant risk producer"
            )
    for prefix in ("base", "refined"):
        dataset, rollout = record[prefix + "_dataset"], record[prefix + "_rollout"]
        _require(
            dataset["original_n"] == n and rollout["original_n"] == n,
            "paired original cash denominator mismatch",
        )
        replay.check_cash(dataset, rollout)
        from run_pilot import paired_policy_rollout

        actual = paired_policy_rollout(
            dataset, record.get(prefix + "_risk"), **record[prefix + "_arguments"]
        )
        runner._same(
            _without_timing(actual), _without_timing(rollout), prefix + " actual policy targets"
        )
        independent = record.get("comparison_quantity") == "cash_vs_independent_gain"
        _require(
            not independent or record["refinement_kind"] == "pnl",
            "independent gain comparison outside original P&L reconstruction",
        )
        target = "discounted_gain_pnl" if prefix == "refined" and independent else "discounted_pnl"
        runner._same(record[prefix], rollout[target], prefix + " P&L raw mismatch")
    result = paired_pnl_metrics(
        record["base"], record["refined"], original_n=n, path_ids=record["path_ids"]
    )
    result["shared_CRN_checked"] = shared_checked
    return result


def _oracle_samples(payoff, spot_bump, quote_bump):
    payoff = np.asarray(payoff, dtype=float)
    n = payoff.shape[1]
    _require(
        payoff.shape == (13, n) and spot_bump > 0 and quote_bump > 0,
        "full 13-bump payoff array required",
    )
    positions = np.empty((3, n, 2))
    for i, multiplier in enumerate((1.0, 0.5, 2.0)):
        positions[i, :, 0] = (payoff[1 + 2 * i] - payoff[2 + 2 * i]) / (2 * spot_bump * multiplier)
        positions[i, :, 1] = (payoff[7 + 2 * i] - payoff[8 + 2 * i]) / (2 * quote_bump * multiplier)
    return np.column_stack((payoff[0], positions[1])), positions


def check_oracle_record(record, *, original_n):
    """Recompute prices/observable S,Q Greeks from all 13 independent bump arrays."""
    n = original_n
    _require(
        record.get("N") == n and record.get("original_path_count") == n,
        "oracle original path count mismatch",
    )
    raw = np.asarray(record["payoff_samples"])
    _require(raw.shape == (13, n), "oracle original payoff denominator mismatch")
    samples, widths = _oracle_samples(raw, record["spot_bump"], record["quote_bump"])
    runner._same(samples, record["samples"], "oracle saved samples")
    runner._same(widths, record["width_position_samples"], "oracle width samples")
    if "path_status" in record:
        status = np.asarray(record["path_status"])
        if record.get("path_status_encoding") == "uint16_dictionary":
            labels = np.asarray(record["path_status_labels"]).astype(str)
            _require(
                status.dtype.kind in "ui" and status.size and status.max() < len(labels),
                "oracle compact original statuses invalid",
            )
            status = labels[status]
        else:
            status = status.astype(str)
        _require(status.shape == (13, n), "oracle original query/path statuses missing")
        mask = np.all(np.isin(status, ["supported", "exact_input_identity"]), axis=0)
    else:
        mask = np.asarray(record["path_mask"], dtype=bool)
    _require(mask.shape == (n,), "oracle original mask denominator mismatch")
    stats = _moments(samples, n)
    invalid = not mask.all() or not np.isfinite(samples).all()
    # Constant zero sample labels cannot certify an unseen payoff event.
    inputs = record.get("input_state", {})
    exact_settled = inputs.get("memory_count") == 12
    exact_linear = inputs.get("memory_count", 12) < 12 and inputs.get("memory_sum", -1) >= 1200.0
    unresolved = np.ptp(samples, axis=0) == 0 if not invalid else np.ones(3, dtype=bool)
    if exact_settled or exact_linear:
        unresolved[:] = False
        _require(
            record.get("exact_branch") == ("settled" if exact_settled else "linear"),
            "exact claim input proof differs from saved branch",
        )
    gate_se = [
        None if invalid or unresolved[i] else float(stats["standard_errors"][i]) for i in range(3)
    ]
    scheme = record.get("scheme_refinement")
    scheme_stats = None
    if scheme is not None:
        _require(scheme.get("levels") == [768, 1536], "original oracle SDE levels changed")
        payoffs = np.asarray(scheme["payoff_samples"])
        _require(payoffs.shape == (2, 13, n), "oracle scheme original payoff denominator mismatch")
        pair = np.stack(
            [_oracle_samples(v, record["spot_bump"], record["quote_bump"])[0] for v in payoffs]
        )
        runner._same(pair, scheme["samples"], "oracle scheme samples")
        runner._same(
            pair[1] - pair[0], scheme["paired_difference_samples"], "oracle paired difference"
        )
        scheme_stats = _moments(pair[1] - pair[0], n)
    if "path_indices" in record:
        _require(
            np.array_equal(record["path_indices"], np.arange(n)),
            "oracle original absolute path IDs changed",
        )
    if "mean" in record:
        runner._same(stats["mean"], record["mean"], "oracle original mean")
        runner._same(stats["standard_errors"], record["standard_errors"], "oracle original raw SE")
        runner._same(stats["covariance"], record["covariance"], "oracle original covariance")
    return {
        "scope": "saved_direct_payoff_and_bumps",
        "original_n": n,
        "samples": samples,
        "width_position_samples": widths,
        "mean": stats["mean"],
        "raw_standard_errors": stats["standard_errors"],
        "gate_standard_errors": gate_se,
        "block_means": stats["block_means"],
        "block_covariance": stats["block_covariance"],
        "width_difference_statistics": [_moments(widths[i] - widths[1], n) for i in (0, 2)],
        "scheme_difference_statistics": scheme_stats,
        "financial_qualification": "unknown",
        "unresolved": (["invalid_original_path"] if invalid else [])
        + (["zero_event_underresolution"] if unresolved.any() else [])
        + (["scheme_refinement_missing"] if scheme is None else []),
        "unverified": ["independent_path_generation", "full_common_domain_call_fit"],
    }


def check_premium_record(record, *, candidate=None):
    original = (candidate or execution.execution_candidate())["original_candidate"]["premium"]
    n = original["original_n"]
    _require(record.get("original_path_count", record.get("N")) == n, "premium original N changed")
    _require(
        record.get("seed") == original["seed"] and record.get("levels") == [768, 1536],
        "premium original independent stream/levels changed",
    )
    values = np.asarray(record["samples"], dtype=float)
    _require(values.shape == (2, n), "premium original paired sample denominator mismatch")
    stats = _moments(values[1, :, None], n)
    diff = _moments((values[1] - values[0])[:, None], n)
    valid = np.isfinite(values).all() and np.any(values[1] != 0)
    return {
        "original_n": n,
        "value": float(stats["mean"][0]) if valid else None,
        "standard_error": float(stats["standard_errors"][0]) if valid else None,
        "raw_standard_error": stats["standard_errors"][0],
        "scheme_error": float(abs(diff["mean"][0]) + 6 * diff["standard_errors"][0])
        if valid
        else None,
        "paired_difference_statistics": diff,
        "financial_qualification": "unknown",
        "scope": "saved_finite_grid_direct_payoff",
    }


def check_q_record(record):
    """Saved one-step Q diagnostics, with original per-bin counts and 6SE gate."""
    native = record.get("kind") == "Q" or any(
        key in record for key in ("quoted_calls", "chunks", "parameters", "call_cache")
    )
    if native:
        required = {
            "kind",
            "model",
            "parameters",
            "surface",
            "initial_spot",
            "initial_state",
            "original_n",
            "seed",
            "state_id",
            "times",
            "spots",
            "states",
            "quoted_calls",
            "call_cache",
            "cache_indices",
            "chunks",
            "path_ids",
            "path_mask",
            "failure_reasons",
            "increments",
            "half_increments",
            "delta",
            "bin_ids",
            "bin_edges",
            "reference_error",
            "rate",
            "status",
        }
        _require(
            required <= set(record) and record.get("kind") == "Q",
            "native Q required saved inputs/arrays missing; SDE replay cannot be waived",
        )
        from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid
        from run_pilot import unpack_inputs

        _require(record["model"] in ("Heston", "local"), "native Q model input invalid")
        _require(
            isinstance(record["parameters"], HestonParameters),
            "native Q required parameters input missing or invalid",
        )
        if record["model"] == "local":
            _require(
                isinstance(unpack_inputs(record["surface"]), LocalVarianceGrid),
                "native Q required local field input missing or invalid",
            )
    n = record["original_n"]
    _path_order(record, n)
    increments = np.asarray(record["increments"], dtype=float)
    delta = np.asarray(record["delta"], dtype=float)
    errors = np.asarray(record["reference_error"], dtype=float)
    _require(
        increments.shape == (n, 3)
        and delta.shape == errors.shape == (3,)
        and np.allclose(delta, [1 / 192, 1 / 384, 1 / 768])
        and np.all(np.isnan(errors) | (np.isfinite(errors) & (errors >= 0))),
        "original Q delta/refinement shape mismatch",
    )
    if native:
        import hashlib

        from hullkit._dynamic_hedging_surfaces import evaluate_call

        stop = 0
        for chunk in record["chunks"]:
            _require(chunk["path_start"] == stop, "Q original path chunks reordered")
            count = chunk["path_stop"] - stop
            normal = np.asarray(chunk["normal"])
            _require(
                normal.shape == (count, 8, 2)
                and chunk["path_steps"] == count * 4
                and chunk["global_normal_steps"] == 8
                and chunk["normal_sha256"] == hashlib.sha256(normal.tobytes()).hexdigest(),
                "Q original actual one-step driver/cost changed",
            )
            _require(
                [r["factor"] for r in chunk["raw_records"]] == [1, 2, 4, 8],
                "original four one-step conditional refinements missing",
            )
            for j, row in enumerate(chunk["raw_records"], start=1):
                factor = row["factor"]
                runner._same(
                    normal[:, :factor].sum(axis=1) / np.sqrt(factor),
                    row["normal"],
                    "Q original shared conditional normal aggregation",
                )
                runner._same(
                    row["records"]["spot"][:, 1],
                    record["spots"][stop : chunk["path_stop"], j],
                    "Q actual one-step endpoint spot",
                )
                from hullkit._dynamic_hedging_core import heston_records, local_records

                initial_spot = np.broadcast_to(record["initial_spot"], (n,))[
                    stop : chunk["path_stop"]
                ]
                initial_state = np.broadcast_to(record["initial_state"], (n,))[
                    stop : chunk["path_stop"]
                ]
                endpoint_times = record["times"][[0, j]]
                if record["model"] == "Heston":
                    actual = heston_records(
                        record["parameters"],
                        row["normal"][:, None, :],
                        endpoint_times,
                        np.array([0, 1]),
                        spot=initial_spot,
                        variance=initial_state,
                    )
                    expected_state = actual["variance"][:, 1]
                else:
                    # The local field API takes the original scalar multiplier.
                    from run_pilot import unpack_inputs

                    actual = local_records(
                        record["parameters"],
                        unpack_inputs(record["surface"]),
                        row["normal"][:, None, :],
                        endpoint_times,
                        np.array([0, 1]),
                        spot=initial_spot,
                        multiplier=record["initial_state"],
                    )
                    expected_state = initial_state
                runner._same(actual, row["records"], "Q saved one-step SDE record")
                runner._same(
                    expected_state,
                    record["states"][stop : chunk["path_stop"], j],
                    "Q saved one-step observable state",
                )
            stop = chunk["path_stop"]
        _require(
            stop == n or record["status"] == "failed_at_declared_cap",
            "Q original unexecuted paths erased",
        )
        q = np.asarray(record["quoted_calls"])
        _require(q.shape == (n, 5), "Q original full/half quote arrays missing")
        for j, index in enumerate(record["cache_indices"]):
            computed = evaluate_call(
                record["call_cache"], index, record["spots"][:, j], record["states"][:, j]
            )
            runner._same(computed["value"], q[:, j], "Q saved call query")
        discounted = q * np.exp(-record["rate"] * (record["times"] - record["times"][0]))[None, :]
        runner._same(discounted[:, [4, 3, 2]] - q[:, [0]], increments, "Q saved full increments")
        runner._same(
            discounted[:, [3, 2, 1]] - q[:, [0]],
            record["half_increments"],
            "Q saved half increments",
        )
        runner._same(
            np.digitize(record["spots"][:, 0], record["bin_edges"]),
            record["bin_ids"],
            "Q fixed observable bins",
        )
    bins = np.asarray(record["bin_ids"])
    _require(bins.shape == (n,), "Q original bin denominator mismatch")
    results = []
    planned_bins = (
        list(range(len(record["bin_edges"]) + 1))
        if "bin_edges" in record
        else np.unique(bins).tolist()
    )
    for identifier in [None, *planned_bins]:
        values = increments if identifier is None else increments[bins == identifier]
        count = len(values)
        invalid = not np.isfinite(values).all()
        stats = _moments(values, count) if count >= 2 else None
        valid = count >= 256 and not invalid and np.isfinite(errors).all()
        drift = None if not valid else np.abs(stats["mean"])
        observed = None if not valid else drift + 6 * stats["standard_errors"] + errors
        if valid and "half_increments" in record:
            half = np.asarray(record["half_increments"])
            half = half if identifier is None else half[bins == identifier]
            refinement = _moments(values - 2 * half, count)
            observed = observed + abs(refinement["mean"]) + 6 * refinement["standard_errors"]
        results.append(
            {
                "id": identifier,
                "original_n": count,
                "mean": None if stats is None else stats["mean"],
                "raw_standard_errors": None if stats is None else stats["standard_errors"],
                "call_accumulated_drift_error": None if not valid else float(768 * observed[-1]),
                "qualification": "measured" if valid else "unknown",
                "reason": None
                if valid
                else "bin_count_below_256_original_path_unknown_or_reference_unmeasured",
            }
        )
    return {
        "original_n": n,
        "whole": results[0],
        "bins": results[1:],
        "financial_qualification": "unknown",
    }


def check_quotes_record(record):
    from check_initial_quotes import _cf_prices, _roster

    n = 37
    _require(
        record["original_n"] == n and np.array_equal(record["quote_ids"], np.arange(n)),
        "original 37 quote denominator changed",
    )
    groups = _roster()
    _require(len(record["groups"]) == 8, "current full37 solver groups missing")
    truth250 = np.full(n, np.nan)
    truth500 = np.full(n, np.nan)
    errors = np.full(n, np.nan)
    production = np.full((3, n), np.nan)
    pdes = np.full_like(record["pde_prices"], np.nan)
    for row, (role, t, strikes) in zip(record["groups"], groups, strict=True):
        ids = row["quote_ids"]
        _require(
            row["role"] == role and row["date"] == t and np.array_equal(row["strikes"], strikes),
            "original quote group identity changed",
        )
        low, _ = _cf_prices(row["low"], strikes, t, record["parameters"])
        high, error = _cf_prices(row["high"], strikes, t, record["parameters"])
        truth250[ids] = low
        truth500[ids] = high
        errors[ids] = error
        _require(len(row["production"]) == 3, "original Fourier refinements missing")
        production[:, ids] = [v["price"] for v in row["production"]]
        _require(
            len(row["pdes"]) == len(record["pde_stages"]), "original PDE refinements incomplete"
        )
        for j, pde in enumerate(row["pdes"]):
            if pde["failure"] is not None or not pde["supported"]:
                continue
            grid = pde["grid"]
            _require(
                grid["values"].shape == (len(strikes), len(grid["log_spots"])),
                "raw PDE original grid denominator mismatch",
            )
            price = np.asarray(
                [
                    np.interp(np.log(record["parameters"]["spot"]), grid["log_spots"], v)
                    for v in grid["values"]
                ]
            )
            runner._same(price, pde["price"], "raw PDE query")
            pdes[j, ids] = price
    for key, value in (
        ("truth250", truth250),
        ("truth500", truth500),
        ("truth500_error", errors),
        ("production", production),
        ("pde_prices", pdes),
    ):
        runner._same(value, record[key], f"current37 {key}")
    stage_errors = np.max(np.abs(pdes - truth500), axis=1)
    valid = np.isfinite(stage_errors)
    chosen = None if not valid.any() else int(np.argmin(np.where(valid, stage_errors, np.inf)))
    cf_error = np.maximum(
        np.abs(truth250 - truth500), np.maximum(np.max(abs(production - truth500), axis=0), errors)
    )
    return {
        "original_n": n,
        "quote_ids": np.arange(n),
        "chosen_common_stage": chosen,
        "initial_quote_error": None if chosen is None else np.abs(pdes[chosen] - truth500),
        "cf_order_cutoff_error": cf_error,
        "raw_cf_error": cf_error,
        "scope": "saved_current37_CF_subintervals_and_PDE_grids",
        "financial_qualification": "unknown",
    }


def check_cap_partial(record, *, expected_n):
    """Inspect all retained prefix work without inventing values for unexecuted paths."""
    _require(record.get("original_n") == expected_n, "cap original N changed")
    _path_order(record, expected_n)
    done = 0
    for chunk in record["chunks"]:
        _require(
            chunk["path_start"] == done
            and chunk["path_stop"] > done
            and chunk["path_stop"] <= expected_n,
            "cap raw chunk gap/duplicate",
        )
        done = chunk["path_stop"]
    _require(
        np.array_equal(record["executed_path_ids"], np.arange(done))
        and record["unexecuted_path_count"] == expected_n - done,
        "cap full original path closure mismatch",
    )
    _require(
        np.asarray(record["path_status"]).shape == (expected_n,)
        and np.all(record["path_status"][done:] == "not_executed_at_declared_cap"),
        "cap original unexecuted statuses erased",
    )
    _require(len(record["raw_chunks"]) == len(record["chunks"]), "cap raw prefix missing")
    for raw, chunk in zip(record["raw_chunks"], record["chunks"], strict=True):
        _require(
            raw["N"] == chunk["path_stop"] - chunk["path_start"],
            "cap primitive original chunk N changed",
        )
    _require(record["labels"] is None, "partial originalN cannot produce finite block labels")
    return {
        "original_n": expected_n,
        "executed_n": done,
        "unexecuted_n": expected_n - done,
        "financial_qualification": "unknown",
    }


def check_job_envelope(row, job, plan):
    _require(
        row["id"] == job["id"] and row["operation"] == job["operation"],
        "job original operation/ID mismatch",
    )
    _require(row["plan_sha256"] == runner.payload_digest(plan), "job prior plan mismatch")
    _require(
        row["source_sha256"] == runner.payload_digest(plan["source"])
        and row["input_bindings"] == plan["input_bindings"],
        "job source/input mismatch",
    )
    _require(
        row["prediction"] == job["prediction"] and row["budget"] == job["budget"],
        "job prior prediction/budget mismatch",
    )
    _require(row["expense"]["id"] == job["expense_id"], "job expense scope mismatch")
    event = row["timing_events"]
    elapsed = (event["wall_stop_ns"] - event["wall_start_ns"]) / 1e9
    cpu = (event["cpu_stop_ns"] - event["cpu_start_ns"]) / 1e9
    timing = row["expense"]["timing"]
    _require(elapsed >= 0 and cpu >= 0, "job negative actual clock interval")
    runner._same(elapsed, timing["wall_seconds"], "job actual wall cost")
    runner._same(cpu, timing["cpu_seconds"], "job actual CPU cost")
    runner._same(
        max(0.0, elapsed - job["budget"]["wall_seconds"]),
        timing["overrun_seconds"],
        "job actual overrun cost",
    )
    protocol.validate_expenses([row["expense"]], required_ids=[job["expense_id"]])
    if row["status"] == "failed_at_declared_cap":
        cap = row["cap_evidence"]
        _require(
            cap["metric"] == "wall_seconds"
            and cap["limit"] == job["budget"]["wall_seconds"]
            and cap["consumed"] >= cap["limit"]
            and cap["consumed"] <= elapsed + 1e-8,
            "job cap consumption not measured",
        )
    return {"elapsed": elapsed, "cpu": cpu}


def check_resolved_job_arguments(row, job, *, inputs, jobs, artifact_directory, planned_jobs=None):
    """Rebind saved worker inputs to original prior inputs and actual dependency raw.

    Rebased paths are used only for reading restored raw; identity remains tied to
    the original artifact container. Legacy direct probes can omit a driver, but
    a locked driver dependency cannot be removed from the saved worker.
    """
    from run_pilot import _resolve, input_identity

    arguments = _resolve(job["arguments"], inputs, jobs, planned_jobs=planned_jobs)
    op = job["operation"]
    if op in (
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
    if op in ("teacher_grid", "teacher_driver"):
        _require(artifact_directory is not None, "original artifact container binding missing")
        arguments["work_directory"] = str(Path(artifact_directory) / "work" / job["id"])
    _require(
        row.get("resolved_arguments_sha256") == input_identity(arguments),
        "saved resolved original worker arguments changed",
    )
    raw = row["raw"]
    if op == "Q":
        from run_pilot import unpack_inputs

        required = {
            "kind",
            "parameters",
            "surface",
            "initial_spot",
            "initial_state",
            "model",
            "seed",
            "original_n",
            "state_id",
            "call_cache",
            "times",
            "bin_edges",
            "chunks",
            "quoted_calls",
            "rate",
        }
        _require(
            required <= set(raw) and raw.get("kind") == "Q",
            "native Q required original producer inputs missing",
        )
        mapping = {
            "parameters": "parameters",
            "surface": "surface",
            "initial_spot": "spot",
            "initial_state": "state",
            "model": "model",
            "seed": "seed",
            "original_n": "original_n",
            "state_id": "state_id",
            "call_cache": "call_cache",
        }
        for raw_key, argument_key in mapping.items():
            actual = unpack_inputs(raw[raw_key]) if raw_key == "surface" else raw[raw_key]
            _require(
                input_identity(actual) == input_identity(arguments.get(argument_key)),
                "Q original actual producer input changed: " + raw_key,
            )
        _require(
            input_identity(np.asarray(raw["bin_edges"]))
            == input_identity(np.asarray(arguments["bin_edges"])),
            "Q original actual producer input changed: bin_edges",
        )
        expected_times = arguments["date"] + np.array([0, 1, 2, 4, 8]) / 1536
        runner._same(expected_times, raw["times"], "Q original date/timeline input")
        runner._same(arguments["parameters"].rate, raw["rate"], "Q original rate input")
        stop = 0
        for chunk in raw["chunks"]:
            _require(
                chunk["path_start"] == stop
                and chunk["path_stop"]
                == min(stop + arguments["chunk_paths"], arguments["original_n"]),
                "Q original chunk_paths input changed",
            )
            stop = chunk["path_stop"]
    if job.get("original_n_source") is not None:
        from run_pilot import _job_identity

        computed_size = _job_identity(job, arguments)
        runner._same(computed_size, row.get("size"), "conditional actual original N/branch size")
    if (
        op in ("teacher", "teacher_grid", "teacher_diagnostic")
        and arguments.get("driver") is not None
    ):
        _require(
            raw.get("driver") is not None
            and input_identity(raw["driver"]) == input_identity(arguments["driver"]),
            "original shared teacher driver dependency removed or changed",
        )
        if op == "teacher_diagnostic":
            _require(
                all(
                    input_identity(r["teacher"].get("driver"))
                    == input_identity(arguments["driver"])
                    for r in raw["rows"]
                ),
                "exact-date teacher driver dependency changed",
            )
    if op == "cell_pair":
        expected = {k: arguments[k] for k in ("validation", "fits", "identity")}
        _require(
            input_identity(raw.get("selection_inputs")) == input_identity(expected),
            "original prior cell selection dependency changed",
        )
        for key in (
            "base_dataset",
            "refined_dataset",
            "base_risk",
            "refined_risk",
            "base_risk_source",
            "refined_risk_source",
            "shared_market",
        ):
            _require(
                input_identity(raw.get(key)) == input_identity(arguments.get(key)),
                "original paired dependency changed: " + key,
            )
    keys = {
        "precision": ("datasets", "risks", "validation", "stream_receipts"),
        "tiny_fits": (
            "train_datasets",
            "validation_datasets",
            "validation_risks",
            "stream_receipts",
            "pilot_training_config",
        ),
        "bump_risk": ("dataset", "caches", "base_risk", "spot_bump", "quote_bump", "chunk_paths"),
        "market_pair": ("model", "seed", "original_n", "call_cache", "levels", "frequencies"),
        "teacher_diagnostic": ("model", "seed", "original_n", "cases"),
        "teacher_driver": ("seed", "original_n", "calendar_times", "chunk_paths"),
        "teacher_grid": ("model", "seed", "original_n", "grid", "evaluation_domains"),
    }.get(op, ())
    for key in keys:
        _require(
            input_identity(raw.get(key)) == input_identity(arguments.get(key)),
            "original actual producer input changed: " + key,
        )
    if op == "teacher_diagnostic" and job.get("original_n_source") is not None:
        for key in ("selector", "selected_inputs"):
            _require(
                input_identity(raw.get(key)) == input_identity(arguments.get(key)),
                "selected additional-date actual input changed: " + key,
            )
    if "arguments" in raw:
        from run_pilot import unpack_inputs

        _require(
            input_identity(unpack_inputs(raw["arguments"])) == input_identity(arguments),
            "saved wrapped worker input dependency changed",
        )
    return arguments


def check_dependency_cap_job(
    row, job, plan, jobs, *, require_scope=True, inputs=None, artifact_context=None
):
    """Verify unexecuted dependency evidence against consumed immutable parents.

    The child's expense measures metadata inspection only. Parent cap consumption
    remains attached to the parent's actual clock and raw numerical attempt.
    """
    from run_pilot import (
        _cap_parent_binding,
        _conditional_job_n_binding,
        _control_receipts_allowed,
        _dependency_ids,
        input_identity,
    )

    _require(
        row["status"] == "unexecuted_dependency_cap" and row.get("cap_evidence") is None,
        "dependency must remain unexecuted",
    )
    raw = row["raw"]
    dependencies = sorted(_dependency_ids(job["arguments"]))
    _require(
        raw["dependency_job_ids"] == dependencies
        and raw["planned_operation"] == job["operation"]
        and raw["planned_arguments_sha256"] == input_identity(job["arguments"]),
        "unexecuted original dependency plan changed",
    )
    original_binding = _conditional_job_n_binding(job, jobs)
    n = job.get("original_n") if original_binding is None else original_binding["original_n"]
    _require(
        raw["original_n"] == n and raw["unexecuted_n"] == n and raw["executed_n"] == 0,
        "unexecuted original denominator changed",
    )
    if original_binding is not None:
        runner._same(
            original_binding,
            raw.get("original_n_binding"),
            "conditional unexecuted original selector binding",
        )
    _require(
        dependencies and all(i in jobs for i in dependencies), "original dependency job missing"
    )
    expected_parents = set()
    for identifier in dependencies:
        prior = jobs[identifier]
        digest = runner.payload_digest({k: v for k, v in prior.items() if k != "artifact_path"})
        _require(
            raw["dependency_payload_sha256"][identifier] == digest,
            "dependency immutable job binding differs",
        )
        if prior["status"] == "failed_at_declared_cap":
            expected_parents.add(identifier)
        elif prior["status"] == "unexecuted_dependency_cap":
            expected_parents.update(prior["raw"]["parent_cap_job_ids"])
        else:
            _require(
                prior["status"] == "executed"
                or (
                    _control_receipts_allowed(job)
                    and prior["status"] == "not_required_after_qualified_prefix"
                ),
                "dependency defect cannot become a cap",
            )
    if job["operation"] == "teacher_selection":
        from run_pilot import _resolve, run_teacher_selection_job

        _require(
            inputs is not None and "selection_inspection" in raw,
            "actual unavailable teacher selection inspection required",
        )
        args = _resolve(
            job["arguments"], inputs, jobs, planned_jobs={j["id"]: j for j in plan["jobs"]}
        )
        computed = run_teacher_selection_job(**args, artifact_context=artifact_context)
        _require(
            computed["selection_status"] == "unavailable" and computed["cache"] is None,
            "missing maximum teacher cannot be substituted by a cache",
        )
        runner._same(computed, raw["selection_inspection"], "actual unavailable selection")
    if job["operation"] == "teacher_selected_inputs":
        from run_pilot import _resolve, run_teacher_selected_inputs_job

        _require(
            inputs is not None and "selected_inputs_inspection" in raw,
            "actual unavailable selected-purpose inspection required",
        )
        args = _resolve(
            job["arguments"],
            inputs,
            jobs,
            planned_jobs={j["id"]: j for j in plan["jobs"]},
        )
        computed = run_teacher_selected_inputs_job(**args, artifact_context=artifact_context)
        _require(
            computed["availability"] == "unavailable"
            and computed["cache"] is None
            and computed["driver"] is None,
            "missing selected purpose cannot use a principal fallback",
        )
        runner._same(
            computed,
            raw["selected_inputs_inspection"],
            "actual unavailable selected-purpose inputs",
        )
    parents = raw["parent_cap_job_ids"]
    _require(parents == sorted(expected_parents) and parents, "dependency cap ancestors changed")
    _require(len(raw["parent_cap_bindings"]) == len(parents), "parent cap binding missing")
    planned = {j["id"]: j for j in plan["jobs"]}
    for identifier, binding in zip(parents, raw["parent_cap_bindings"], strict=True):
        parent = jobs[identifier]
        _require(
            parent["status"] == "failed_at_declared_cap",
            "source defect cannot qualify a dependent cap",
        )
        check_job_envelope(parent, planned[identifier], plan)
        _require(
            runner.payload_digest(binding) == runner.payload_digest(_cap_parent_binding(parent)),
            "actual parent cap binding differs",
        )
        if require_scope:
            scope = planned[identifier].get("cap_scope", {})
            _require(
                row["id"] in scope.get("job_ids", [])
                and identifier in scope.get("job_ids", [])
                and scope.get("expense_id") == parent["expense"]["id"],
                "unexecuted dependency outside prior reviewed parent cap scope",
            )
    return {
        "original_n": raw["original_n"],
        "executed_n": 0,
        "unexecuted_n": raw["unexecuted_n"],
        "cap_scope_parent_ids": parents,
        "financial_qualification": "unknown",
        "execution_status": "unexecuted_dependency_cap",
        "scope": "saved parent budget closure; no child solver or precision measurement",
    }


def _cap_scope_parents(identifier, kind, job_ids, jobs, checks, planned_jobs):
    """The union of actual independent caps must cover every affected job.

    One cap cannot absorb unrelated work. Each parent keeps its own original
    prior budget, numerical raw, actual timer and expense binding.
    """
    parent_ids = set()
    affected = {
        i
        for i in job_ids
        if jobs[i]["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap")
    }
    for i in job_ids:
        if jobs[i]["status"] == "not_required_after_qualified_prefix":
            _require(
                checks[i].get("integrity") == "pass" and checks[i].get("executed_original_n") == 0,
                "unused work must have actual authenticated lower qualification",
            )
    for jid in job_ids:
        row = jobs[jid]
        if row["status"] == "failed_at_declared_cap":
            parent_ids.add(jid)
        elif row["status"] == "unexecuted_dependency_cap":
            parent_ids.update(checks[jid]["cap_scope_parent_ids"])
    _require(parent_ids, "measured parent cap missing")
    covered = set()
    ordered = [i for i in planned_jobs if i in parent_ids]
    key = "case_ids" if kind == "case" else "attempt_ids"
    for jid in ordered:
        scope = planned_jobs[jid].get("cap_scope", {})
        _require(
            identifier in scope.get(key, [])
            and scope.get("expense_id") == jobs[jid]["expense"]["id"],
            "original obligation outside prior reviewed parent cap scope",
        )
        covered.update(scope.get("job_ids", []))
    _require(affected <= covered, "original affected work outside reviewed cap scope union")
    return [jobs[i] for i in ordered]


def _all_cap_bindings(parents):
    from run_pilot import _cap_parent_binding

    return {
        "cap_parent_job_ids": [p["id"] for p in parents],
        "parent_cap_bindings": [_cap_parent_binding(p) for p in parents],
    }


def check_teacher_grid_record(record, parameters, surface, *, artifact_context=None):
    from run_pilot import (
        _check_teacher_node_binding,
        _validate_teacher_reference,
        bound_artifact_path,
        read_pilot_artifact,
        teacher_axes,
    )

    _validate_teacher_reference(
        record.get("teacher_reference"), record["seed"], record["original_n"]
    )
    _require(
        record.get("driver") is None
        or record["driver"].get("teacher_reference") == record.get("teacher_reference"),
        "principal/reference saved teacher driver purpose differs",
    )
    axes = teacher_axes(record["grid"], record["model"])
    runner._same(axes, record["axes"], "original teacher grid axes")
    expected = []
    for j in range(12):
        spots = (
            (axes["t0_spot"] if j == 0 else axes["spot"]) if record["model"] == "local" else [100.0]
        )
        for spot in spots:
            for state in axes["state"]:
                expected.append({"date_index": j, "spot": float(spot), "state": float(state)})
    _require(record["planned_nodes"] == expected, "original teacher node roster changed")
    n = record["original_n"]
    nodes = record["nodes"]
    _require(
        len(nodes) <= len(expected)
        and record["unexecuted_node_count"] == len(expected) - len(nodes),
        "original teacher node denominator changed",
    )
    checks = []

    def rows():
        for index, node in enumerate(nodes):
            _require(
                all(node[k] == expected[index][k] for k in expected[index]),
                "teacher raw node order changed",
            )
            directory = bound_artifact_path(node["path"], artifact_context)
            row, _ = read_pilot_artifact(directory)
            _check_teacher_node_binding(node, directory, row)
            _require(
                row["original_n"] == n and row["seed"] == record["seed"],
                "teacher original N/CRN differs",
            )
            if row.get("status") == "failed_at_declared_cap":
                checks.append(check_cap_partial(row, expected_n=n))
                continue
            checks.append(
                check_teacher_record(row, parameters, surface, artifact_context=artifact_context)
            )
            row["surface"] = surface
            yield row

    if record["cache"] is None:
        list(rows())
        return {
            "original_n": n,
            "original_node_count": len(expected),
            "executed_node_count": len(nodes),
            "raw_checks": checks,
            "status": "unclosed_or_declared_cap",
            "financial_qualification": "unknown",
        }
    _require(len(nodes) == len(expected), "cache cannot hide unexecuted nodes")
    result = replay.rebuild_asian_cache(
        rows(),
        parameters,
        axes,
        model=record["model"].lower(),
        evaluation_domains=record["evaluation_domains"],
        saved_cache=record["cache"],
    )
    return {
        "original_n": n,
        "original_node_count": len(expected),
        "executed_node_count": len(nodes),
        "raw_checks": checks,
        "cache": result["cache"],
        "financial_qualification": "unknown",
    }


def check_call_table(table):
    """Rebuild independent table prices from saved quad/PDE raw, not solver calls."""
    from check_fresh import _cf_value
    from scipy.interpolate import CubicSpline

    prices = np.asarray(table["prices"])
    nodes = np.asarray(table["state_nodes"])
    spots = np.asarray(table["query_spots"])
    dates = np.asarray(table["dates"])
    expected_bounds = [1e-5, 0.5] if table["model"] == "heston" else [0.25, 4.0]
    _require(
        table["original_bounds"] == expected_bounds
        and nodes[0] == expected_bounds[0]
        and nodes[-1] == expected_bounds[-1],
        "independent call original full root domain changed",
    )
    reconstructed = np.full_like(prices, np.nan)
    seen = set()
    if table["model"] == "heston":
        for row in table["integration_receipts"]:
            index = tuple(row[k] for k in ("level", "date_index", "spot_index", "state_index"))
            _require(index not in seen, "independent call duplicate raw cell")
            seen.add(index)
            level, d, sp, st = index
            p = {**table["parameters"], "spot": float(spots[sp]), "v0": float(nodes[st])}
            value, error = _cf_value(row, 1.25 - dates[d], p)
            reconstructed[index] = value
            runner._same(error, table["price_unit_errors"][index], "independent call quad error")
        _require(len(seen) == prices.size, "independent call original table cells missing")
    else:
        for row in table["pde_receipts"]:
            level, st = row["level"], row["state_index"]
            _require((level, st) not in seen, "independent PDE duplicate state/level")
            seen.add((level, st))
            if not row["supported"] or row["failure"] is not None:
                continue
            _require(
                np.asarray(row["values"]).shape == (len(dates), len(row["spots"])),
                "independent PDE original dates missing",
            )
            inside = (spots >= row["spots"][0]) & (spots <= row["spots"][-1])
            for d in range(len(dates)):
                reconstructed[level, d, inside, st] = CubicSpline(
                    np.log(row["spots"]), row["values"][d], extrapolate=False
                )(np.log(spots[inside]))
        _require(
            len(seen) == len(nodes) * prices.shape[0], "independent PDE original states missing"
        )
    runner._same(reconstructed, prices, "independent full call table")
    return reconstructed


def _check_oracle_fits(record):
    from reference_methods import fit_independent_quote

    table = record["call_table"]
    prices = check_call_table(table)
    inputs = record["input_state"]
    date = inputs["date"]
    di = np.flatnonzero(np.isclose(table["dates"], date, rtol=0, atol=1e-12))
    _require(len(di) == 1, "oracle independent calendar identity mismatch")
    _require(len(record["query_fits"]) == 13, "oracle original 13 query fits missing")
    inp = record["input_state"]
    s0 = inp["spot"]
    q0 = inp["quote"]
    spots = [s0]
    quotes = [q0]
    for width in (1.0, 0.5, 2.0):
        spots.extend([s0 + record["spot_bump"] * width, s0 - record["spot_bump"] * width])
        quotes.extend([q0, q0])
    for width in (1.0, 0.5, 2.0):
        spots.extend([s0, s0])
        quotes.extend([q0 + record["quote_bump"] * width, q0 - record["quote_bump"] * width])
    _require(
        len(record["query_ids"]) == 13 and len(set(record["query_ids"])) == 13,
        "original oracle query IDs differ",
    )
    for index, saved in enumerate(record["query_fits"]):
        _require(
            saved["query_id"] == record["query_ids"][index]
            and np.isclose(saved["spot"], spots[index], rtol=0, atol=1e-12)
            and np.isclose(saved["quote"], quotes[index], rtol=0, atol=1e-12),
            "original oracle bump query identity changed",
        )
        si = np.flatnonzero(np.isclose(table["query_spots"], saved["spot"], rtol=0, atol=1e-12))
        _require(len(si) == 1, "oracle original independent spot query missing")
        computed = fit_independent_quote(
            table["state_nodes"],
            prices[-1, di[0], si[0]],
            saved["quote"],
            model=record["model"],
            spot=saved["spot"],
            query_id=saved["query_id"],
        )
        for key, value in computed.items():
            runner._same(value, saved[key], "independent original full-root fit " + key)
        _require(
            len(saved["refinement_fits"]) == len(prices), "all independent call levels missing"
        )
        for level, curve in enumerate(prices[:, di[0], si[0]]):
            computed = fit_independent_quote(
                table["state_nodes"],
                curve,
                saved["quote"],
                model=record["model"],
                spot=saved["spot"],
                query_id=saved["query_id"],
            )
            for key, value in computed.items():
                runner._same(
                    value,
                    saved["refinement_fits"][level][key],
                    "independent level full-root fit " + key,
                )
    return record["query_fits"]


def check_state_record(record, parameters, surface):
    """Same fixed cache/block operator plus independent observable-coordinate errors."""
    from hullkit._dynamic_hedging_risk import quote_positions
    from run_pilot import run_state_job

    kwargs = {
        k: record[k]
        for k in (
            "model",
            "call_cache",
            "asian_cache",
            "date_index",
            "spot",
            "quote",
            "memory_sum",
            "memory_count",
            "oracle",
        )
    }
    computed = run_state_job(parameters, surface, **kwargs)
    for key in ("fit", "claim", "traded", "positions"):
        runner._same(computed[key], record[key], "state saved " + key)
    _require(
        computed["original_n"] == record["original_n"]
        and computed["oracle_original_n"] == record["oracle_original_n"],
        "original teacher/oracle distinct denominator changed",
    )
    oracle = check_oracle_record(record["oracle"], original_n=record["oracle_original_n"])
    _require(
        record["oracle"].get("scheme_refinement") is not None,
        "independent state scheme oracle not executed",
    )
    fits = _check_oracle_fits(record["oracle"])
    independent = fits[0]
    rawfit = record["fit"]
    claim = record["claim"]
    call = record["traded"]
    reason = rawfit["reason"]
    structural = None
    if reason == "ill_conditioned" and independent.get("condition_number", 0) > 0.25:
        structural = "ill_conditioned"
    elif reason == "nonunique" and independent["solver_status"] == "nonunique":
        structural = "nonunique"
    elif reason == "no_root" and independent["solver_status"] == "no_root":
        structural = "no_root"
    elif reason == "bound" and independent.get("reason") == "bound":
        structural = "bound"
    if reason.startswith("solver"):
        raise ValueError("source/solver defect cannot close state")
    block = claim.get("block_values")
    teacher_se = np.full(3, np.nan)
    position_mean = np.full(2, np.nan)
    positions_se = np.full(2, np.nan)
    if block is not None and np.isfinite(block).all():
        block = np.asarray(block)
        _require(block.shape == (16, 3), "original 16 state blocks missing")
        teacher_se = np.std(block, axis=0, ddof=1) / 4
        bp = quote_positions(
            block[:, 1], block[:, 2], call["spot_derivative"], call["state_derivative"]
        )
        joined = np.column_stack([bp["stock"], bp["call"]])
        position_mean = np.array(
            [float(record["positions"]["stock"]), float(record["positions"]["call"])]
        )
        positions_se = np.std(joined, axis=0, ddof=1) / 4
    ref = record["oracle"].get("call_refinements")
    gate = {k: None for k in execution.execution_candidate()["pilot_cases"][37]["gates"]}
    gate["quote_condition_number"] = (
        float(rawfit["condition"]) if np.isfinite(rawfit["condition"]) else None
    )
    if ref is not None:
        prices = np.asarray(ref["prices"])
        cs = np.asarray(ref["spot_derivatives"])
        ct = np.asarray(ref["state_derivatives"])
        widths = np.asarray(ref["three_width_derivatives"])
        runner._same(
            np.max(abs(prices - prices[0])), ref["price_error"], "call raw price refinement"
        )
        runner._same(
            np.max(abs(cs - cs[0])), ref["spot_derivative_error"], "call raw CS refinement"
        )
        runner._same(
            np.max(abs(ct - ct[0])), ref["state_derivative_error"], "call raw Ctheta refinement"
        )
        width_error = np.max(abs(widths - widths[:, :, [1]]), axis=(0, 2))
        runner._same(width_error, ref["finite_width_errors"], "call raw width error")
        gate["call_price_error"] = float(
            abs(call["value"] - record["quote"])
            + np.max(abs(prices - prices[0]))
            + ref["price_unit_error"]
        )
        gate["call_stock_derivative_error"] = float(
            abs(call["spot_derivative"] - cs[-1])
            + np.max(abs(cs - cs[0]))
            + width_error[0]
            + ref["integration_derivative_error"][0]
        )
        scale = 0.04 if record["model"] == "Heston" else 1.0
        gate["call_scaled_state_derivative_error"] = float(
            scale
            * (
                abs(call["state_derivative"] - ct[-1])
                + np.max(abs(ct - ct[0]))
                + width_error[1]
                + ref["integration_derivative_error"][1]
            )
        )
    if np.isfinite(teacher_se).all() and np.isfinite(position_mean).all():
        gate["teacher_price_se"] = float(teacher_se[0])
        gate["stock_position_se"], gate["call_position_se"] = map(float, positions_se)
        scheme = oracle["scheme_difference_statistics"]
        errors = (
            6 * oracle["raw_standard_errors"] + abs(scheme["mean"]) + 6 * scheme["standard_errors"]
        )
        for width in oracle["width_difference_statistics"]:
            errors[1:] += abs(width["mean"]) + 6 * width["standard_errors"]
        valid = np.isfinite(errors).all() and all(
            x is not None for x in oracle["gate_standard_errors"]
        )
        if valid:
            gate["asian_price_error"] = float(abs(claim["value"] - oracle["mean"][0]) + errors[0])
            gate["stock_position_error"] = float(
                abs(position_mean[0] - oracle["mean"][1]) + errors[1]
            )
            gate["call_position_error"] = float(
                abs(position_mean[1] - oracle["mean"][2]) + errors[2]
            )
    return {
        "original_n": record["original_n"],
        "measurements": gate,
        "structural_rejection": structural,
        "fit": rawfit,
        "oracle": oracle,
        "unmeasured_reasons": {
            k: "original unknown/support/underresolution or independent uncertainty"
            for k, v in gate.items()
            if v is None
        },
        "raw_teacher_standard_errors": teacher_se,
        "raw_position_standard_errors": positions_se,
        "financial_qualification": "unknown",
    }


def check_market_pair_record(record):
    from run_pilot import _combine_market_chunks

    n = record["original_n"]
    _path_order(record, n)
    _require(
        record["levels"] == [768, 1536]
        and len(record["frequencies"]) == 2
        and all(f in (12, 24, 48) for f in record["frequencies"]),
        "original SDE/frequency pair changed",
    )
    stop = 0
    for index, driver in enumerate(record["driver_map"]):
        _require(driver["path_start"] == stop, "paired driver original path gap")
        stop = driver["path_stop"]
        fine = record["raw_chunks"][1][index]["primitives"]["normals"]
        coarse = record["raw_chunks"][0][index]["primitives"]["normals"]
        _require(
            fine.shape == (stop - driver["path_start"], 1536, 2),
            "paired fine original shape changed",
        )
        runner._same(
            coarse,
            fine.reshape(len(fine), 768, 2, 2).sum(axis=2) / np.sqrt(2),
            "shared CRN coarsening",
        )
        import hashlib

        _require(
            driver["fine_sha256"] == hashlib.sha256(fine.tobytes()).hexdigest()
            and driver["coarse_sha256"] == hashlib.sha256(coarse.tobytes()).hexdigest(),
            "original shared driver byte binding changed",
        )
        _require(
            driver["path_steps"] == [len(fine) * 768, len(fine) * 1536],
            "original shared driver path-step cost changed",
        )
        for k in (0, 1):
            chunk = record["raw_chunks"][k][index]
            _require(chunk["original_n"] == len(fine), "paired chunk original N changed")
            replay.check_market(
                chunk,
                fixing_times=np.arange(1, 13) / 12,
                call_cache=record["call_cache"],
                generator=record["model"].lower(),
                latent_state=chunk["market"]["variance"] if record["model"] == "Heston" else None,
            )
    _require(
        stop == record["processed_n"] and n - stop == record["unexecuted_n"],
        "paired original unexecuted denominator changed",
    )
    if record["datasets"] is not None:
        _require(stop == n, "paired full dataset hides cap remainder")
        for chunks, saved in zip(record["raw_chunks"], record["datasets"], strict=True):
            actual = _combine_market_chunks(chunks, n)
            runner._same(actual, saved, "paired full original market")
    return {
        "original_n": n,
        "processed_n": stop,
        "unexecuted_n": n - stop,
        "financial_qualification": "unknown",
        "scope": "saved_market_and_CRN_pairing",
    }


def _check_actual_expense_clock(expense, events):
    _require(isinstance(events, dict), "actual expense clock events missing")
    for axis in ("wall", "cpu"):
        start, stop = events.get(axis + "_start_ns"), events.get(axis + "_stop_ns")
        _require(
            isinstance(start, int) and isinstance(stop, int) and 0 <= start <= stop,
            "actual expense clock boundary invalid",
        )
        value = expense["timing"].get(axis + "_seconds")
        _require(
            value is not None
            and np.isfinite(value)
            and np.isclose(value, (stop - start) / 1e9, rtol=1e-12, atol=1e-9),
            "actual expense clock duration differs",
        )


def project_execution_expense_aliases(expenses, aliases, *, jobs):
    """Copy actual parent clocks into distinct prior aliases, charge the tree once.

    An alias is an explicit inclusive scope, not a new measurement of the child.
    Its parent must be an actual job or a measured phase enclosing each bound job.
    This function cannot provide missing external review/serialization/CAS timers.
    """
    import copy

    rows = copy.deepcopy(list(expenses))
    original = {r["id"]: r for r in rows}
    _require(len(original) == len(rows), "actual current expense IDs repeated")
    parent_jobs = {
        j.get("expense", {}).get("id"): j for j in jobs.values() if j.get("expense") is not None
    }
    for specification in aliases:
        identifier = specification["id"]
        parent_id = specification.get("parent_expense_id")
        _require(
            parent_id in original and identifier not in original,
            "prior alias parent unavailable or alias repeated",
        )
        parent = original[parent_id]
        _require(
            parent.get("includes_children") is True and parent["status"] in ("complete", "failed"),
            "actual alias parent must be inclusive and measured",
        )
        selected = specification.get("required_job_ids")
        _require(
            isinstance(selected, list) and selected and len(set(selected)) == len(selected),
            "original alias job scope missing",
        )
        if parent_id in parent_jobs:
            job = parent_jobs[parent_id]
            _require(set(selected) <= {job["id"]}, "alias jobs not covered by actual job")
            events = job.get("timing_events")
            _require(
                run_pilot_identity(job["expense"])
                == parent.get("actual_job_expense_sha256", run_pilot_identity(parent)),
                "actual alias parent expense differs",
            )
        else:
            _require(
                isinstance(parent.get("covered_job_ids"), list),
                "actual measured phase scope missing",
            )
            _require(
                set(selected) <= set(parent["covered_job_ids"]) <= set(jobs),
                "alias jobs not covered by actual phase",
            )
            events = parent.get("timing_events")
            for jid in selected:
                child = jobs[jid]
                _check_actual_expense_clock(child["expense"], child.get("timing_events"))
                for axis in ("wall", "cpu"):
                    _require(
                        events is not None
                        and events[axis + "_start_ns"] <= child["timing_events"][axis + "_start_ns"]
                        and events[axis + "_stop_ns"] >= child["timing_events"][axis + "_stop_ns"],
                        "actual phase clock does not cover original job",
                    )
        _check_actual_expense_clock(parent, events)
        row = copy.deepcopy(parent)
        row.update(
            id=identifier,
            scope="prior inclusive execution alias:" + identifier,
            parent_id=parent_id,
            includes_children=True,
            timing_events=copy.deepcopy(events),
            covered_job_ids=list(selected),
            alias_scope="actual parent inclusive clock; not separately timed child",
            actual_parent_sha256=run_pilot_identity(parent),
            prior_alias_sha256=run_pilot_identity(specification),
        )
        rows.append(row)
        original[identifier] = row
    return protocol.validate_expenses(rows, required_ids=[r["id"] for r in rows])


def run_pilot_identity(value):
    from run_pilot import input_identity

    return input_identity(value)


def check_raw_costs(snapshot, plan):
    """Keep required unexecuted costs explicit; never infer a smaller cost roster."""
    import copy

    phases = copy.deepcopy(snapshot.get("execution_phases", []))
    coverage = {}
    for phase in phases:
        _check_actual_expense_clock(phase, phase.get("timing_events"))
        _require(phase["includes_children"] is True, "actual execution phase must be inclusive")
        for identifier in phase["covered_job_ids"]:
            _require(identifier not in coverage, "actual job charged in repeated execution phases")
            coverage[identifier] = phase
    rows = list(phases)
    for job in snapshot["jobs"]:
        expense = copy.deepcopy(job["expense"])
        if job["id"] in coverage:
            phase = coverage[job["id"]]
            _check_actual_expense_clock(expense, job.get("timing_events"))
            for axis in ("wall", "cpu"):
                _require(
                    phase["timing_events"][axis + "_start_ns"]
                    <= job["timing_events"][axis + "_start_ns"]
                    <= job["timing_events"][axis + "_stop_ns"]
                    <= phase["timing_events"][axis + "_stop_ns"],
                    "actual inclusive phase does not cover original job clock",
                )
            expense.update(
                parent_id=phase["id"], actual_job_expense_sha256=run_pilot_identity(job["expense"])
            )
        rows.append(expense)
        raw = job.get("raw") or {}
        children = raw.get("expenses", [])
        if "expense" in raw:
            children = [raw["expense"], *children]
        for i, child in enumerate(children):
            value = dict(child)
            timing = value.get("timing")
            if timing is None:
                timing = {
                    k: value.get(k) for k in ("wall_seconds", "cpu_seconds", "overrun_seconds")
                }
                if timing["overrun_seconds"] is None and timing["wall_seconds"] is not None:
                    timing["overrun_seconds"] = 0.0
            rows.append(
                {
                    "id": job["expense"]["id"] + ":child" + str(i),
                    "scope": value.get("scope", "raw_worker"),
                    "status": value.get(
                        "status", "complete" if timing["wall_seconds"] is not None else "pending"
                    ),
                    "parent_id": job["expense"]["id"],
                    "includes_children": True,
                    "timing": timing,
                    "reason": value.get("reason"),
                    "raw": value,
                }
            )
    required = [j["expense_id"] for j in plan["jobs"]] + plan.get(
        "required_external_expense_ids", []
    )
    rows += snapshot.get("external_expenses", [])
    _require(len({r["id"] for r in rows}) == len(rows), "repeated current expense scope")
    missing = sorted(set(required) - {r["id"] for r in rows})
    current = (
        protocol.validate_expenses(rows, required_ids=[r["id"] for r in rows]) if rows else None
    )
    histories = []
    for h in plan["history"]:
        if "expenses" in h:
            histories.append(
                protocol.validate_expenses(
                    h["expenses"], required_ids=[r["id"] for r in h["expenses"]]
                )
            )
    return {
        "current": current,
        "historical": histories,
        "raw_expenses": rows,
        "missing_current_expense_ids": missing,
        "closed": not missing
        and all(
            r["timing"].get("wall_seconds") is not None
            and r["timing"].get("cpu_seconds") is not None
            for r in rows
        ),
        "financial_speedup_supported": False,
    }


def _without_timing(value):
    if isinstance(value, dict):
        return {
            k: _without_timing(v)
            for k, v in value.items()
            if k not in ("expense", "expenses", "elapsed_seconds", "cpu_seconds", "wall_seconds")
        }
    if isinstance(value, list):
        return [_without_timing(v) for v in value]
    return value


def check_date_gate_record(record, parameters, surface):
    from run_pilot import run_date_gate_job

    kwargs = {k: record[k] for k in ("model", "call_cache", "asian_cache", "date_index", "queries")}
    actual = run_date_gate_job(parameters, surface, **kwargs)
    runner._same(actual, record, "same-box original block date queries")
    errors = []
    for row in record["rows"]:
        block = row["block_gate_values"]
        if block is None or not np.isfinite(block).all():
            errors.append([None] * 3)
        else:
            _require(np.asarray(block).shape == (16, 3), "date gate original 16 blocks changed")
            errors.append(np.std(block, axis=0, ddof=1) / 4)
    values = {}
    for i, name in enumerate(("teacher_price_se", "stock_position_se", "call_position_se")):
        column = [r[i] for r in errors]
        values[name] = None if any(v is None for v in column) else float(max(column))
    return {
        "measurements": values,
        "original_n": record["original_n"],
        "queries": record["queries"],
        "raw_standard_errors": errors,
        "model": record["model"],
        "date_index": record["date_index"],
        "financial_qualification": "unknown",
    }


def check_empty_claim_record(record):
    from run_pilot import run_empty_claim_job

    checked = check_q_record(record["Q"])
    actual = run_empty_claim_job(record["Q"])
    runner._same(actual, record, "empty claim actual zero-claim unit-call cash")
    for row, column in zip(record["rows"], (4, 3, 2), strict=True):
        delta = record["Q"]["times"][column] - record["Q"]["times"][0]
        expected = (
            record["Q"]["quoted_calls"][:, column] * np.exp(-record["Q"]["rate"] * delta)
            - record["Q"]["quoted_calls"][:, 0]
        )
        runner._same(row["raw"]["discounted_pnl"], expected, "empty claim discounted Q gain")
    return {
        "original_n": record["original_n"],
        "measurements": {
            "call_accumulated_drift_error": checked["whole"]["call_accumulated_drift_error"]
        },
        "Q_check": checked,
        "financial_qualification": "unknown",
    }


def check_tiny_fits_record(raw):
    from deep_hedge_price._dynamic_hedging_closure import _failure, _validate_nn
    from deep_hedge_price._dynamic_hedging_study import policy_rollout

    from deep_hedge_price import _dynamic_hedging_policy as policy

    config = raw["pilot_training_config"]
    candidate = raw["candidate"]
    _require(
        candidate["training"] == config and raw["test_opened"] is False,
        "tiny original prior config changed",
    )
    slots = [r for r in protocol.study_roster()["fits"] if r["initialization"] == 11]
    rows = raw["training_fits"]
    _require(
        len(rows) == 4 and {r["id"] for r in rows} == {r["id"] for r in slots},
        "four original tiny fit slots required; full12 main is separate",
    )
    validations = {r["fit_id"]: r for r in raw["nn_validation"]}
    _require(len(validations) == 4, "four original tiny validations required")
    result = []
    for slot in slots:
        row = next(r for r in rows if r["id"] == slot["id"])
        _require(
            all(row[k] == v for k, v in slot.items())
            and row["attempted"] is True
            and row["original_n"] == config["original_n"]
            and row["requested_updates"] == config["updates"],
            "tiny original fit identity changed",
        )
        data = raw["train_datasets"][slot["training_generator"]]
        _require(data["original_n"] == config["original_n"], "tiny training original N changed")
        fitted = row.get("raw_fit")
        if fitted is not None:
            _require(
                fitted["seed"] == 11
                and fitted["original_path_count"] == config["original_n"]
                and fitted["requested_updates"] == config["updates"]
                and fitted["batch_size"] == config["batch_size"],
                "tiny raw optimizer identity changed",
            )
            batch = np.asarray(fitted["batch_indices"])
            _require(
                batch.shape == (fitted["attempt_count"], config["batch_size"])
                and np.all((batch >= 0) & (batch < config["original_n"])),
                "tiny original batches changed",
            )
            _require(
                len(fitted["losses"]) == len(fitted["attempt_events"]) == fitted["attempt_count"],
                "tiny optimizer attempts erased",
            )
            if fitted["status"] == "completed":
                runner._same(
                    fitted["scaler"],
                    policy._normalization(policy._dataset(data)),
                    "tiny training-only normalization",
                )
                for name, shape in {
                    "w1": (9, 32),
                    "b1": (32,),
                    "w2": (32, 32),
                    "b2": (32,),
                    "w3": (32, 2),
                    "b3": (2,),
                }.items():
                    _require(
                        np.asarray(fitted["weights"][name]).shape == shape
                        and np.isfinite(fitted["weights"][name]).all(),
                        "tiny fixed checkpoint invalid",
                    )
                _require(
                    fitted["updates"] == config["updates"] and fitted["complete"] is True,
                    "tiny original updates incomplete",
                )
                rollout = policy_rollout(
                    data, None, universe=slot["universe"], policy="nn", fit=fitted
                )
                runner._same(
                    rollout["holdings"], fitted["train_holdings"], "tiny fixed training holdings"
                )
                runner._same(
                    rollout["discounted_pnl"], fitted["train_discounted_pnl"], "tiny training cash"
                )
        validation, closed = _validate_nn(
            row, raw["validation_datasets"][slot["training_generator"]], data, candidate
        )
        runner._same(
            _without_timing(validation),
            _without_timing(validations[slot["id"]]),
            "tiny saved fixed-checkpoint validation",
        )
        runner._same(
            _without_timing(closed),
            _without_timing(next(r for r in raw["fits"] if r["id"] == slot["id"])),
            "tiny all original closed checkpoint slots",
        )
        kind = _failure(row, data, candidate)
        result.append(
            {
                "id": slot["id"],
                "original_n": row["original_n"],
                "failure_kind": kind,
                "closed": kind != "source_or_optimizer_defect",
                "qualification": "qualified"
                if kind is None and validation["status"] == "completed"
                else "unknown",
                "row": closed,
            }
        )
    return {
        "fits": result,
        "original_fit_slots": 4,
        "closed": all(r["closed"] for r in result),
        "financial_qualification": "unknown",
        "scope": "tiny4_saved_checkpoint_validation",
        "unverified": ["optimizer_history", "actual_rng_generation"],
    }


def check_stream_receipts_record(raw, *, markets, roles, seed_namespace):
    from run_pilot import run_stream_receipts_job

    for value in markets.values():
        check_market_pair_record(value)
    computed = run_stream_receipts_job(markets=markets, roles=roles, seed_namespace=seed_namespace)
    runner._same(computed, raw, "actual saved market global stream receipt binding")
    return {
        "financial_qualification": "unknown",
        "value": computed["value"],
        "scope": "actual saved fine normal bytes/order/seed/N receipt",
    }


def check_frequency_cache_record(raw):
    from run_pilot import run_frequency_cache_job

    computed = run_frequency_cache_job(**raw["arguments"])
    runner._same(computed, raw, "saved exact-date unknown sheet view")
    return {
        "financial_qualification": "unknown",
        "date_maps": raw["date_maps"],
        "scope": "original monthly operator; no unsupported gap qualification",
    }


def check_wrapped_operation(raw, operation, context):
    from hullkit._dynamic_hedging_surfaces import evaluate_call
    from run_pilot import unpack_inputs

    from deep_hedge_price import _dynamic_hedging_study as study

    args = unpack_inputs(raw["arguments"])
    value = raw["value"]
    _require(raw["kind"] == operation, "saved operation kind changed")
    if operation == "quote_risk" and raw.get("chunked_worker") is not None:
        from check_main import check_risk_job

        source = raw["chunked_worker"]
        computed = check_risk_job(
            source, args["parameters"], args["surface"], args["dataset"], args["caches"]
        )
        runner._same(computed["risk"], value, "saved bounded original quote risk value")
        _require(
            raw["status"] == source["status"]
            and raw["original_n"] == args["dataset"]["original_n"],
            "original bounded quote risk status/N changed",
        )
        return {
            "original_n": raw["original_n"],
            "value": value,
            "processed_n": computed["processed_n"],
            "financial_qualification": "unknown",
            "scope": "saved_quote_risk",
            "chunked": True,
        }
    if operation == "quote_risk":
        computed = study.quote_risk_dataset(**args)
        runner._same(
            _without_timing(computed), _without_timing(value), "saved observable quote risk"
        )
    elif operation in ("roster", "validation"):
        fn = study.test_roster if operation == "roster" else study.select_validation
        computed = fn(**args)
        runner._same(
            _without_timing(computed), _without_timing(value), "saved original policy roster"
        )
        rows = value["cells"] if operation == "roster" else value["candidates"]
        for row in rows:
            replay.check_cash(args["dataset"], row["result"])
    elif operation == "call_cache":
        _require(
            np.asarray(value["values"]).shape
            == (len(value["dates"]), len(value["spot_nodes"]), len(value["state_nodes"])),
            "call original Cartesian values missing",
        )
        _require(
            len(value["spot_nodes"]) >= 4 and len(value["state_nodes"]) >= 4,
            "original call cubic stencil missing",
        )
        for key in ("dates", "spot_nodes", "state_nodes", "model"):
            runner._same(args[key], value[key], "actual call cache input " + key)
        for j in range(len(value["dates"])):
            S, V = np.meshgrid(value["spot_nodes"], value["state_nodes"], indexing="ij")
            computed = evaluate_call(value, j, S, V)
            runner._same(
                computed["value"], value["values"][j], "original saved call node evaluation"
            )
    elif operation == "market":
        dataset = value
        generator = args["generator"].lower() if "generator" in args else args["model"].lower()
        replay.check_market(
            dataset,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=args["call_cache"],
            generator=generator,
            latent_state=dataset["market"]["variance"] if generator == "heston" else None,
        )
    else:
        raise ValueError("standalone fit helper is not a pilot/main closure")
    return {
        "original_n": value.get("original_n"),
        "value": value,
        "scope": "saved_" + operation,
        "financial_qualification": "unknown",
    }


def check_teacher_diagnostic_record(raw, parameters, surface, *, artifact_context=None):
    _require(raw["model"] in ("Heston", "local"), "additional teacher model changed")
    _require(
        len(raw["rows"]) <= len(raw["cases"])
        and raw["unexecuted_case_count"] == len(raw["cases"]) - len(raw["rows"]),
        "additional exact-date original denominator changed",
    )
    result = []
    for expected, row in zip(raw["cases"], raw["rows"], strict=False):
        runner._same(expected, row["case"], "additional original case")
        date = expected["date"]
        _require(
            date in (1 / 24, 1 / 48)
            and expected["spot"] == 100.0
            and expected["memory_count"] == 0
            and expected["memory_sum"] == 0,
            "additional representative-date roster changed",
        )
        teacher = row["teacher"]
        _require(
            teacher["original_n"] == raw["original_n"] and teacher["seed"] == raw["seed"],
            "additional original N/stream changed",
        )
        if teacher.get("status") == "failed_at_declared_cap":
            result.append(check_cap_partial(teacher, expected_n=raw["original_n"]))
        else:
            _require(
                np.isclose(teacher["primitives"]["calendar_times"][0], date),
                "additional exact-date restart changed",
            )
            result.append(
                check_teacher_record(
                    teacher, parameters, surface, artifact_context=artifact_context
                )
            )
    return {
        "original_n": raw["original_n"],
        "cases": raw["cases"],
        "checks": result,
        "unexecuted_case_count": raw["unexecuted_case_count"],
        "financial_qualification": "unknown",
    }


def check_bump_risk_record(raw):
    from run_pilot import bump_query_chunk, bump_risk_variants

    n = raw["original_n"]
    _path_order(raw, n)
    dataset = raw["dataset"]
    _require(
        dataset["original_n"] == raw["base_risk"]["original_n"] == n,
        "original bump path denominator changed",
    )
    d = len(dataset["times"]) - 1
    reconstructed = {m: np.full((13, n, d), np.nan) for m in ("heston", "local")}
    planned = [
        (m, j, lo, min(n, lo + raw["chunk_paths"]))
        for m in ("heston", "local")
        for j in range(d)
        for lo in range(0, n, raw["chunk_paths"])
    ]
    _require(len(raw["chunks"]) <= len(planned), "extra bump query chunks")
    for expected, saved in zip(planned, raw["chunks"], strict=False):
        m, j, lo, hi = expected
        _require(
            (saved["model"], saved["date_index"], saved["path_start"], saved["path_stop"])
            == expected,
            "original bump chunk order changed",
        )
        actual = bump_query_chunk(
            dataset,
            raw["caches"],
            model=m,
            date_index=j,
            path_start=lo,
            path_stop=hi,
            spot_bump=raw["spot_bump"],
            quote_bump=raw["quote_bump"],
        )
        runner._same(actual, saved, "all original13 refit query fits and scalar prices")
        for query in saved["queries"]:
            _require(
                not any(str(fit["reason"]).startswith("solver") for fit in query["fits"]),
                "source/solver bump defect cannot close as precision failure",
            )
        reconstructed[m][:, lo:hi, j] = [q["prices"] for q in saved["queries"]]
    runner._same(reconstructed, raw["prices"], "original bump full/unexecuted scalar price arrays")
    done = sum((r["path_stop"] - r["path_start"]) * 13 for r in raw["chunks"])
    _require(
        raw["original_query_path_count"] == 2 * 13 * n * d
        and raw["executed_query_path_count"] == done
        and raw["unexecuted_query_path_count"] == 2 * 13 * n * d - done,
        "original bump all query/path denominator changed",
    )
    variants = bump_risk_variants(
        raw["base_risk"],
        reconstructed,
        spot_bump=raw["spot_bump"],
        quote_bump=raw["quote_bump"],
        parameters=raw["parameters"],
        dataset=dataset,
    )
    runner._same(variants, raw["risk_variants"], "original scalar-price FD position variants")
    runner._same(variants[1], raw["value"], "halfwidth adopted risk")
    return {
        "original_n": n,
        "risk_variants": variants,
        "unexecuted_query_path_count": 2 * 13 * n * d - done,
        "scope": "all-path scalar-cache full-root/refit FD, not MC truth",
        "financial_qualification": "unknown",
    }


def check_precision_record(raw):
    from deep_hedge_price import _dynamic_hedging_study as study

    slots = [
        r for r in protocol.study_roster()["primary_cells"] if r["policy"] in ("greek", "band")
    ]
    expected = [dict(identity=r, stream_slot=i) for i in range(3) for r in slots]
    _require(
        raw["planned_cells"] == expected
        and len(raw["rows"]) <= 48
        and raw["unexecuted_cell_count"] == 48 - len(raw["rows"]),
        "original precision48-cell roster changed",
    )
    n = raw["original_n"]
    stats = []
    for plan, row in zip(expected, raw["rows"], strict=False):
        _require(
            row["identity"] == plan["identity"] and row["stream_slot"] == plan["stream_slot"],
            "original precision cell identity changed",
        )
        identity = plan["identity"]
        g = identity["generator"]
        u = identity["universe"]
        data = raw["datasets"][g][plan["stream_slot"]]
        risk = raw["risks"][g][plan["stream_slot"]]
        _require(
            data["original_n"] == n and risk["original_n"] == n, "precision original N changed"
        )
        selected = raw["validation"][g + ":" + u]
        width = 0.0
        if identity["policy"] == "band":
            name = selected["selected_bands"][identity["valuation"]]
            if name is None:
                actual = study._unknown_rollout(data, "all original band candidates failed")
            else:
                _require(
                    name in {r["id"] for r in selected["candidates"] if r["status"] == "completed"},
                    "precision width lacks original validation candidate",
                )
                width = float(name.split(":width")[1])
                actual = study.policy_rollout(
                    data,
                    risk,
                    universe=u,
                    policy="band",
                    model=identity["valuation"].lower(),
                    width=width,
                )
        else:
            actual = study.policy_rollout(
                data, risk, universe=u, policy="greek", model=identity["valuation"].lower()
            )
        runner._same(width, row["width"], "precision actual selected width")
        runner._same(
            _without_timing(actual), _without_timing(row["result"]), "precision original raw policy"
        )
        replay.check_cash(data, row["result"])
        loss = np.asarray(actual["loss"])
        moment = _moments(np.column_stack([loss, loss**2]), n)
        eligible = np.isfinite(loss).all() and np.asarray(actual["qualified_path_mask"]).all()
        stats.append(
            {
                "id": identity["id"],
                "stream_slot": plan["stream_slot"],
                "original_n": n,
                "raw_mean": moment["mean"],
                "raw_SE": moment["standard_errors"],
                "mean_loss_se": float(moment["standard_errors"][0]) if eligible else None,
                "mse_se": float(moment["standard_errors"][1]) if eligible else None,
                "baseline_mse": float(moment["mean"][1]) if eligible else None,
            }
        )
    complete = len(stats) == 48
    valid = complete and all(s["mean_loss_se"] is not None for s in stats)
    worst_loss = max(r["mean_loss_se"] for r in stats) if valid else None
    worst_mse = max(r["mse_se"] for r in stats) if valid else None
    baseline = min(r["baseline_mse"] for r in stats) if valid else None
    candidate = protocol.candidate_protocol()["test"]
    passed = (
        valid
        and worst_loss <= candidate["mean_loss_se_max"]
        and worst_mse <= max(candidate["mse_se_absolute"], candidate["mse_se_relative"] * baseline)
    )
    return {
        "original_n": n,
        "rows": stats,
        "worst_mean_loss_se": worst_loss,
        "worst_mse_se": worst_mse,
        "baseline_mse": baseline,
        "qualification": "qualified" if passed else "unknown",
        "reason": None
        if passed
        else "original48 cells incomplete/unknown or precision gates failed",
        "evidence_sha256": runner.payload_digest(raw),
        "financial_qualification": "unknown",
    }


def _scalar(value):
    return None if value is None or not np.isfinite(value) else float(value)


def _projection(descriptor, measurements, original_n, *, structural=None):
    gates = descriptor["gates"]
    values = {k: _scalar(measurements.get(k)) for k in gates}
    reasons = {
        k: "original evidence unknown, underresolved, unsupported or unmeasured"
        for k, v in values.items()
        if v is None
    }
    original = execution.execution_candidate()["original_candidate"]
    passed = execution._measurements(
        gates, {"measurements": values, "unmeasured_reasons": reasons}, original
    )
    return {
        "id": descriptor["id"],
        "original_n": original_n,
        "measurements": values,
        "unmeasured_reasons": reasons,
        "outcome": "validated_structural_rejection"
        if structural
        else "within_envelope"
        if passed
        else "measured_precision_failure",
        "rejection_kind": structural,
        "financial_qualification": "qualified" if passed and structural is None else "unknown",
        "reason": None
        if passed and structural is None
        else structural or "original uncertainty or precision gate failed",
    }


def project_case(descriptor, checked, raw, plan):
    """Only raw typed evidence contributes one original case; no flag-based qualification."""
    n = plan.get("original_n")
    _require(n is not None, "original case N missing")
    kind = descriptor["kind"]
    if kind == "quote":
        _require(
            n == 1
            and checked["original_n"] == 37
            and raw.get("original_n") == 37
            and np.array_equal(raw.get("quote_ids"), np.arange(37)),
            "original quote case/full raw count or ordering changed",
        )
        index = int(descriptor["id"][5:])
        values = {
            key: None if checked[key] is None else checked[key][index]
            for key in descriptor["gates"]
        }
        return _projection(descriptor, values, n) | {
            "raw_original_n": 37,
            "raw_quote_index": index,
        }
    _require(raw.get("original_n") == n, "case original denominator differs from prior plan")
    if kind == "state":
        identity = descriptor["identity"]
        _require(
            raw["model"] == identity["model"]
            and np.isclose(raw["spot"], identity["spot"])
            and np.isclose(raw["call_cache"]["dates"][raw["date_index"]], identity["date"]),
            "original selected-state identity changed",
        )
        _require(
            raw["memory_count"] == round(identity["date"] * 12)
            and np.isclose(raw["memory_sum"], 100 * raw["memory_count"]),
            "original selected Asian memory changed",
        )
        projected = _projection(
            descriptor, checked["measurements"], n, structural=checked["structural_rejection"]
        )
        projected["first_failure_date"] = (
            None if projected["financial_qualification"] == "qualified" else identity["date"]
        )
        return projected
    if kind == "cell":
        _require(
            raw.get("identity") == descriptor["identity"],
            "original full pilot cell policy identity changed",
        )
        _require(
            raw.get("refinement_kind") == "SDE" and raw.get("shared_driver_binding"),
            "pilot paired cell actual shared SDE refinement binding missing",
        )
        identity = descriptor["identity"]
        for key in ("base_arguments", "refined_arguments"):
            args = raw[key]
            _require(
                args["universe"] == identity["universe"]
                and args["policy"]
                == ("none" if identity["policy"] == "no_hedge" else identity["policy"]),
                "original cell actual policy identity changed",
            )
            if identity["valuation"] is not None:
                _require(
                    args["model"].lower() == identity["valuation"].lower(),
                    "original cell valuation model changed",
                )
            if identity["policy"] == "nn" and args.get("fit") is not None:
                _require(
                    args["fit"]["fit_id"]
                    == "fit:"
                    + identity["training_generator"]
                    + ":"
                    + identity["universe"]
                    + ":init"
                    + str(identity["initialization"]),
                    "original NN checkpoint identity changed",
                )
        _require(checked.get("shared_CRN_checked") is True, "pilot paired cell CRN raw not checked")
        return _projection(descriptor, checked, n)
    if kind == "fit":
        _require(
            raw.get("kind") == "tiny_fits", "pilot4 fit cannot be replaced by full12 main closure"
        )
        fit_id = descriptor["identity"]["id"]
        row = next(r for r in checked["fits"] if r["id"] == fit_id)
        _require(row["closed"], "source or optimizer defect leaves tiny fit unclosed")
        training = next(r for r in raw["training_fits"] if r["id"] == fit_id)
        validation = next(r for r in raw["nn_validation"] if r["fit_id"] == fit_id)
        fitted = training.get("raw_fit")
        _require(
            fitted is not None
            and fitted.get("status") == "completed"
            and fitted.get("complete") is True
            and training["status"] == "completed",
            "incomplete optimizer needs actual cap or source-defect closure",
        )
        _require(
            validation["original_n"] == plan.get("validation_original_n"),
            "fit original validation denominator differs from prior plan",
        )
        result = _projection(descriptor, {}, n)
        evidence = runner.payload_digest(raw)
        failure_date = validation.get("first_failure_date")
        result.update(
            evidence_sha256=evidence,
            first_failure_date=failure_date,
            fit_validation={
                "fit_id": fit_id,
                "training_original_n": n,
                "validation_original_n": validation["original_n"],
                "optimizer_status": fitted["status"],
                "optimizer_complete": fitted["complete"],
                "validation_status": validation["status"],
                "validation_qualification": validation["qualification"],
                "first_failure_date": failure_date,
                "evidence_sha256": evidence,
            },
        )
        result["financial_qualification"] = row["qualification"]
        if row["qualification"] != "qualified":
            result.update(
                outcome="measured_precision_failure",
                reason=row["failure_kind"] or "tiny validation unknown",
            )
        return result
    raise ValueError("unknown original case kind")


def _max_gates(rows, gates):
    result = {}
    for gate in gates:
        values = [r.get("measurements", r).get(gate) for r in rows]
        result[gate] = (
            None
            if not values or any(v is None or not np.isfinite(v) for v in values)
            else float(max(values))
        )
    return result


def project_attempt(identifier, job_ids, jobs, checks, candidate, context):
    """Close only the named original semantic obligation and its real prerequisites."""
    _require(job_ids and len(set(job_ids)) == len(job_ids), "required original work IDs missing")
    _require(all(i in jobs and i in checks for i in job_ids), "required actual work unexecuted")
    selected = [jobs[i] for i in job_ids]
    values = [checks[i] for i in job_ids]
    _require(
        all(
            j["status"] == "executed"
            or (
                identifier in ("saved_replay", "costs")
                and j["status"] == "not_required_after_qualified_prefix"
                and checks[j["id"]].get("integrity") == "pass"
            )
            for j in selected
        ),
        "declared cap requires explicit cap projection",
    )
    operations = [j["operation"] for j in selected]
    raw = [j["raw"] for j in selected]
    gates = candidate["pilot_attempt_gates"][identifier]
    measure = {}
    if identifier.startswith("teacher:"):
        _, model, date = identifier.split(":")
        di = int(date[4:])
        _require(
            any(op in ("teacher_grid", "teacher_domain_selection") for op in operations)
            and "date_gate" in operations,
            "teacher group requires full original grid and same-block observable positions",
        )
        grids = [r for r in raw if r.get("kind") == "teacher_grid"]
        date_values = [
            v
            for j, v in zip(selected, values, strict=True)
            if j["operation"] == "date_gate"
            and j["raw"]["model"] == model
            and j["raw"]["date_index"] == di
        ]
        _require(
            any(r["model"] == model and r["cache"] is not None for r in grids) and date_values,
            "original teacher date/model incomplete",
        )
        measure = _max_gates(date_values, gates)
    elif identifier.startswith(("refinement:", "frequency:")):
        paired = [
            (j, v)
            for j, v in zip(selected, values, strict=True)
            if j["operation"] in ("paired_pnl", "cell_pair")
        ]
        market = [r for r in raw if r.get("kind") == "market_pair"]
        _require(paired and market, "paired P&L and actual CRN market raw required")
        kind = identifier.split(":")[1] if identifier.startswith("refinement:") else "frequency"
        model = identifier.split(":")[-1] if identifier.startswith("refinement:") else None
        _require(
            all(
                j["raw"].get("refinement_kind") == kind and v.get("shared_CRN_checked")
                for j, v in paired
            ),
            "original refinement kind or actual CRN differs",
        )
        if model is not None:
            _require(all(r["model"] == model for r in market), "original refinement model changed")
        if kind == "frequency":
            frequency = int(identifier.split(":")[1])
            _require(
                all(frequency in r["frequencies"] and 12 in r["frequencies"] for r in market),
                "selected exact frequency pair missing",
            )
            _require(
                "teacher_diagnostic" in operations,
                "extra exact-date teacher diagnostic required; no time interpolation",
            )
        elif kind == "teacher_N":
            ns = {r["original_n"] for r in raw if r.get("kind") == "teacher_grid"}
            grids = [r for r in raw if r.get("kind") == "teacher_grid"]
            valid_prefix = len(ns) >= 2 and ns <= set(
                candidate["original_candidate"]["teacher"]["n_candidates"]
            )
            if not valid_prefix and ns == {65536}:
                principal = next((r for r in grids if r.get("teacher_reference") is None), None)
                reference = next((r for r in grids if r.get("teacher_reference") is not None), None)
                _require(
                    principal is not None and reference is not None,
                    "original maximum reserved comparison missing",
                )
                check_teacher_driver_comparison(
                    principal,
                    reference,
                    reference_rule="independent_reserved_stream_grid_max",
                    artifact_context=context.get("artifact_context"),
                )
                valid_prefix = True
            _require(valid_prefix, "actual original N prefix refinement missing")
        elif kind == "teacher_grid":
            _require(
                {r["grid"] for r in raw if r.get("kind") == "teacher_grid"} == {"coarse", "high"},
                "original coarse/high grid comparison missing",
            )
        elif kind == "position":
            _require(
                "oracle" in operations and "bump_risk" in operations,
                "all-path3widthrefit positions plus independent selected-state oracle required",
            )
            for job, _ in paired:
                source = job["raw"].get("refined_risk_source")
                _require(
                    isinstance(source, dict) and source.get("kind") == "bump_risk",
                    "position comparison must use actual refit risk; tags cannot substitute",
                )
        measure = _max_gates([v for _, v in paired], gates)
    elif identifier.startswith("Q:"):
        _, kind, model = identifier.split(":")
        expected = "empty_claim" if kind == "empty_claim" else "Q"
        _require(expected in operations, "actual Q/empty-claim raw operation required")
        qrows = [
            r["Q"] if r.get("kind") == "empty_claim" else r
            for j, r in zip(selected, raw, strict=True)
            if j["operation"] == expected
        ]
        _require(all(r["model"] == model for r in qrows), "original Q model changed")
        identity = context.get("q_state_plan")
        _require(
            isinstance(identity, list) and len(identity) == 18,
            "original eighteen Q states must be prior locked",
        )
        _require(
            {r.get("state_id") for r in qrows} == {r["id"] for r in identity},
            "original Q eighteen-state denominator incomplete",
        )
        extracted = []
        for j, v in zip(selected, values, strict=True):
            if j["operation"] != expected:
                continue
            q = v["Q_check"] if expected == "empty_claim" else v
            if kind == "state_bins":
                _require(q["bins"], "original fixed bins missing")
                extracted.extend(q["bins"])
            else:
                extracted.append(q["whole"])
        measure = _max_gates(extracted, gates)
    elif identifier == "initial_common_surface":
        _require(
            operations == ["quotes"] and values[0]["original_n"] == 37,
            "current source full37 solver evidence required",
        )
    elif identifier == "premium":
        _require(
            operations == ["premium"] and values[0]["original_n"] == 65536,
            "reserved independent full premium required",
        )
    elif identifier == "tiny_nn":
        _require(
            operations == ["tiny_fits"] and values[0]["closed"],
            "four actual tiny fits and validation closure required",
        )
    elif identifier == "tiny_roster":
        _require(all(op == "roster" for op in operations), "actual full tiny roster required")
        cells = [r for v in values for r in v["value"]["cells"]]
        required = candidate["original_roster"]["primary_cells"]
        _require(
            len(cells) == 44 and {r["id"] for r in cells} == {r["id"] for r in required},
            "all44 original tiny cells required",
        )
    elif identifier == "source_closure":
        _require(
            operations == ["source"] and "actual_source" in values[0],
            "current transitive source byte closure required",
        )
    elif identifier == "domain_selection":
        from run_pilot import teacher_domain_rule

        _require(
            context.get("domain_plan") is not None, "prior original domain selection rule required"
        )
        if "teacher_selection" in operations:
            _require(
                operations == ["teacher_selection", "teacher_selection"]
                and {r["model"] for r in raw} == {"Heston", "local"},
                "both actual original teacher domain selections required",
            )
            rules = context["domain_plan"]["selection_rules"]
            for row in raw:
                runner._same(
                    teacher_domain_rule(row["model"]),
                    rules[row["model"]],
                    "prior original finite domain rule",
                )
                _require(
                    row["cache"] is not None and len(row["cache"]["evaluation_domains"]) == 12,
                    "all original exact domain dates required",
                )
        else:
            _require(
                "teacher_grid" in operations,
                "fixed prior domain selection and full original nodes required",
            )
            saved = [r for r in raw if r.get("kind") == "teacher_grid"]
            _require(
                all(r["evaluation_domains"] == context["domain_plan"][r["model"]] for r in saved),
                "raw fixed domain differs from prior selection",
            )
    elif identifier == "saved_replay":
        _require(
            context.get("saved_replay_complete") is not None
            and set(context["saved_replay_complete"]) == set(jobs),
            "all saved raw original jobs must be checked",
        )
    elif identifier == "costs":
        _require(
            context.get("cost_check", {}).get("closed") is True,
            "all original measured current costs required",
        )
    elif identifier == "test_precision":
        _require(
            all(op == "precision" for op in operations), "all original precision workers required"
        )
        _require(
            [r["original_n"] for r in raw] == [8192, 16384, 32768],
            "original ordered testN projections missing",
        )
    else:
        raise ValueError("unimplemented required attempt semantics: " + identifier)
    descriptor = {"id": identifier, "gates": gates}
    n = max((r.get("original_n") or 1 for r in raw), default=1)
    projected = _projection(descriptor, measure, n)
    projected["status"] = "complete"
    projected["required_job_ids"] = list(job_ids)
    if identifier == "test_precision":
        qualified = [
            r["original_n"]
            for r, v in zip(raw, values, strict=True)
            if v.get("qualification") == "qualified"
        ]
        projected.update(
            selected_test_n=min(qualified) if qualified else None,
            unavailable_at_original_n=None if qualified else 32768,
            precision_attempts=[
                {
                    "original_n": r["original_n"],
                    "qualification": v.get("qualification", "unknown"),
                    "reason": v.get(
                        "reason", "original required precision measurement unavailable"
                    ),
                }
                for r, v in zip(raw, values, strict=True)
            ],
        )
        if not qualified:
            projected.update(
                financial_qualification="unknown",
                reason="unavailable at original N32768; no smaller N promotion",
            )
    return projected


def _raw_job_check(job, context):
    op, raw = job["operation"], job["raw"]
    if op == "teacher_selected_inputs":
        return check_teacher_selected_inputs_record(
            raw, **context["resolved_arguments"], artifact_context=context.get("artifact_context")
        )
    if op == "teacher_selection":
        return check_teacher_selection_record(
            raw, **context["resolved_arguments"], artifact_context=context.get("artifact_context")
        )
    if op == "teacher_domain_selection":
        args = context.get("resolved_arguments", {})
        _require(
            "teacher" in args and "selection_rule" in args,
            "original domain source/rule argument binding required",
        )
        check_teacher_domain_selection_record(
            args["teacher"], raw, selection_rule=args["selection_rule"]
        )
        return check_teacher_grid_record(
            raw,
            context["parameters"],
            context.get("surface"),
            artifact_context=context.get("artifact_context"),
        )
    if op == "teacher_candidate_gate":
        arguments = context["resolved_arguments"]
        computed = calculate_teacher_candidate_gate(
            arguments["parameters"],
            arguments.get("surface"),
            stage_plan=arguments["stage_plan"],
            evidence=arguments["evidence"],
            artifact_context=context.get("artifact_context"),
        )
        runner._same(computed, raw, "whole original teacher candidate gate")
        return computed
    if op == "bump_risk":
        return check_bump_risk_record(raw)
    if op == "frequency_cache":
        return check_frequency_cache_record(raw)
    if op == "stream_receipts":
        return check_stream_receipts_record(raw, **context["resolved_arguments"])
    if op == "teacher_diagnostic":
        return check_teacher_diagnostic_record(
            raw,
            context["parameters"],
            context.get("surface"),
            artifact_context=context.get("artifact_context"),
        )
    if op == "precision":
        return check_precision_record(raw)
    if op == "date_gate":
        return check_date_gate_record(raw, context["parameters"], context.get("surface"))
    if op == "empty_claim":
        return check_empty_claim_record(raw)
    if op == "tiny_fits":
        return check_tiny_fits_record(raw)
    if op in ("call_cache", "quote_risk", "roster", "validation", "market", "fits"):
        return check_wrapped_operation(raw, op, context)
    if op == "asian_cache":
        from run_pilot import run_cache_job

        computed = run_cache_job(
            context["parameters"],
            rows=raw["rows"],
            axes=raw["axes"],
            model=raw["model"],
            evaluation_domains=raw["evaluation_domains"],
        )
        runner._same(computed, raw, "saved Asian full raw cache")
        return {"cache": computed["cache"], "original_n": raw["original_n"]}
    if op == "field":
        args = context.get("resolved_arguments", {})
        controls = {k: raw[k] for k in ("order", "cutoff", "frequency_scale", "density_floor")}
        if args:
            expected = {
                "order": args.get("order", 2048),
                "cutoff": args.get("cutoff", 1024),
                "frequency_scale": args.get("frequency_scale"),
                "density_floor": args.get("density_floor", 1e-10),
            }
            runner._same(expected, controls, "original field controls")
            runner._same(args["times"], raw["times"], "original field controls times")
            runner._same(args["z_nodes"], raw["z_nodes"], "original field controls z")
        _require(
            raw["frequency_rule"]
            == ("fixed_cutoff" if controls["frequency_scale"] is None else "scale_over_sqrt_time"),
            "original field frequency rule changed",
        )
        for row in raw["rows"]:
            expected_cutoff = (
                controls["cutoff"]
                if controls["frequency_scale"] is None
                else controls["frequency_scale"] / np.sqrt(row["date"])
            )
            _require(
                row["order"] == controls["order"]
                and row["density_floor"] == controls["density_floor"]
                and np.isclose(row["max_frequency"], expected_cutoff, rtol=1e-14, atol=0),
                "original field frequency controls changed",
            )
        values = np.asarray(raw["raw_values"])
        support = np.asarray(raw["support_mask"])
        _require(
            values.shape == support.shape == (len(raw["times"]), len(raw["z_nodes"])),
            "original field Cartesian axes changed",
        )
        for j, row in enumerate(raw["rows"]):
            f = row["surface"]
            v = np.full(len(raw["z_nodes"]), np.nan)
            np.divide(f["weighted_density"], f["density"], out=v, where=f["supported"])
            runner._same(v, values[j], "raw local variance density ratio")
            runner._same(f["supported"], support[j], "raw field support")
        from run_pilot import input_identity, materialize_field

        actual = materialize_field(raw)
        columns = [
            int(np.flatnonzero(np.isclose(raw["z_nodes"], z, rtol=0, atol=1e-12))[0])
            for z in actual.z_nodes
        ]
        _require(
            np.array_equal(actual.values, values[:, columns], equal_nan=True),
            "actual field differs from original supported raw nodes",
        )
        return {"field_sha256": input_identity(actual), "financial_qualification": "unknown"}
    if op == "source":
        from run_pilot import _pilot_source

        actual = _pilot_source(context.get("source_root", ROOT))
        runner._same(actual, raw, "actual transitive source bytes")
        _require(not actual.get("dynamic_imports"), "unresolved dynamic source")
        return {"actual_source": actual, "financial_qualification": "unknown"}
    if op == "market_pair":
        return check_market_pair_record(raw)
    if op == "closure":
        from deep_hedge_price._dynamic_hedging_closure import check_training_closure

        result = check_training_closure(raw["closure"], **raw["inputs"])
        return {
            "scope": "saved_full_training_validation_closure",
            "result": result,
            "closure": raw["closure"],
            "financial_qualification": "unknown",
        }
    if op == "state":
        return check_state_record(raw, context["parameters"], context.get("surface"))
    if op == "call_table":
        return {"prices": check_call_table(raw), "financial_qualification": "unknown"}
    if op == "quotes":
        return check_quotes_record(raw)
    if op == "teacher_grid":
        return check_teacher_grid_record(
            raw,
            context["parameters"],
            context.get("surface"),
            artifact_context=context.get("artifact_context"),
        )
    if op == "teacher":
        return check_teacher_record(
            raw,
            context["parameters"],
            context.get("surface"),
            artifact_context=context.get("artifact_context"),
        )
    if op == "teacher_driver":
        from run_pilot import read_teacher_driver_chunks

        count = sum(
            len(r["normal"])
            for r in read_teacher_driver_chunks(
                raw, artifact_context=context.get("artifact_context")
            )
        )
        _require(
            count == raw["original_n"] and raw["status"] == "executed",
            "full original shared driver incomplete",
        )
        return {
            "original_n": count,
            "scope": "saved original normal bytes/order/16clusters",
            "financial_qualification": "unknown",
        }
    if op == "oracle":
        expected_n = job.get("argument_manifest", {}).get("n_paths")
        _require(expected_n is not None, "locked original oracle N missing")
        return check_oracle_record(raw, original_n=expected_n)
    if op == "premium":
        return check_premium_record(raw)
    if op in ("initial_quotes", "selected_calls"):
        if op == "initial_quotes":
            from check_initial_quotes import check_initial_quotes

            computed = check_initial_quotes(raw["metadata"], raw["arrays"])
        else:
            from check_selected_calls import check_selected_calls

            computed = check_selected_calls(raw["metadata"], raw["arrays"])
        runner._same(computed, raw["check"], f"{op} saved check")
        return computed
    if op == "policy":
        checked = replay.check_cash(raw["dataset"], raw["rollout"])
        return {"scope": "saved_cash", "original_n": raw["dataset"]["original_n"], "check": checked}
    if op in ("paired_pnl", "cell_pair"):
        return check_paired_pnl_record(raw)
    if op == "Q":
        return check_q_record(raw)
    raise ValueError(f"required semantic operation remains unimplemented: {op}")


def check_capped_job_raw(job, *, artifact_context=None, context=None):
    """Retain original arrays and measured boundary; cap never turns a defect ready."""
    raw = job["raw"]
    op = job["operation"]
    _require(isinstance(raw, dict), "capped actual raw attempt missing")
    _require(
        raw.get("status") != "unclosed_source_or_solver_defect", "solver defect cannot close at cap"
    )
    if op == "teacher_selection":
        _require(
            context is not None and "resolved_arguments" in context,
            "capped selector actual arguments required",
        )
        from run_pilot import _teacher_selection_control_raw

        _teacher_selection_control_raw(job)
        return check_teacher_selection_record(
            raw, **context["resolved_arguments"], artifact_context=artifact_context
        )
    if op == "teacher_selected_inputs":
        _require(
            context is not None and "resolved_arguments" in context,
            "capped selected-purpose actual arguments required",
        )
        return check_teacher_selected_inputs_record(
            raw, **context["resolved_arguments"], artifact_context=artifact_context
        )
    if op == "quote_risk":
        checked = check_wrapped_operation(raw, "quote_risk", context or {})
        _require(
            checked["original_n"] == job["argument_manifest"]["original_n"],
            "capped original quote risk denominator changed",
        )
        return checked
    if op == "teacher_driver":
        from run_pilot import read_teacher_driver_chunks

        count = sum(
            len(r["normal"])
            for r in read_teacher_driver_chunks(raw, artifact_context=artifact_context)
        )
        _require(
            count + raw["unexecuted_n"] == raw["original_n"], "partial driver denominator changed"
        )
        return {
            "original_n": raw["original_n"],
            "executed_n": count,
            "financial_qualification": "unknown",
        }
    if op == "teacher":
        n = job["argument_manifest"]["original_n"]
        if raw.get("status") is None and raw.get("primitives") is not None:
            _require(
                context is not None and "parameters" in context,
                "completed capped teacher actual context required",
            )
            checked = check_teacher_record(
                raw,
                context["parameters"],
                context.get("surface"),
                artifact_context=artifact_context,
            )
            _require(checked["original_n"] == n, "completed capped teacher original N differs")
            return {**checked, "executed_n": n, "financial_qualification": "unknown"}
        return check_cap_partial(raw, expected_n=n)
    if op in ("oracle", "premium"):
        n = raw["original_path_count"]
        payoff = np.asarray(raw["payoff_samples"] if op == "oracle" else raw["samples"])
        _require(payoff.shape[-1] == n, "capped original oracle payoff paths missing")
        codes = np.asarray(raw["path_status"])
        labels = np.asarray(raw["path_status_labels"]).astype(str)
        _require(
            codes.dtype.kind in "ui" and codes.size and codes.max() < len(labels),
            "capped original compact statuses missing",
        )
        decoded = labels[codes]
        count = int(np.count_nonzero(decoded == "unmeasured_cap"))
        _require(count > 0 or np.isfinite(payoff).all(), "capped unexecuted raw statuses missing")
        _require(
            np.all(~np.isfinite(payoff[decoded == "unmeasured_cap"])),
            "capped oracle paths were imputed",
        )
        return {
            "original_n": n,
            "raw_unmeasured_count": count,
            "financial_qualification": "unknown",
        }
    if op == "quotes":
        _require(
            raw["original_n"] == 37 and np.array_equal(raw["quote_ids"], np.arange(37)),
            "capped quote original roster missing",
        )
        _require(
            np.asarray(raw["pde_prices"]).shape == (len(raw["pde_stages"]), 37),
            "capped original PDE slots erased",
        )
        return {
            "original_n": 37,
            "executed_group_count": len(raw["groups"]),
            "financial_qualification": "unknown",
        }
    if op == "Q":
        return check_q_record(raw)
    if op == "market_pair":
        _path_order(raw, raw["original_n"])
        _require(
            raw["processed_n"] + raw["unexecuted_n"] == raw["original_n"],
            "capped paired original denominator changed",
        )
        return {"original_n": raw["original_n"], "financial_qualification": "unknown"}
    if op in ("teacher_grid", "teacher_diagnostic", "bump_risk", "precision", "field"):
        _require(raw.get("cap_evidence") is not None, "actual partial phase cap receipt missing")
        return {"original_n": raw.get("original_n"), "financial_qualification": "unknown"}
    raise ValueError("cap semantic raw boundary unsupported for original operation")


def project_cap(identifier, gates, job, original_n):
    _require(job["status"] == "failed_at_declared_cap", "actual declared-cap status required")
    cap = job["cap_evidence"]
    _require(
        cap["metric"] == "wall_seconds" and cap["consumed"] >= cap["limit"],
        "actual approved cap was not consumed",
    )
    values = {g: None for g in gates}
    return {
        "id": identifier,
        "original_n": original_n,
        "measurements": values,
        "unmeasured_reasons": {
            g: "actual prior approved cap retained original raw and unexecuted paths" for g in gates
        },
        "outcome": "attempt_failed_at_declared_cap",
        "status": "failed_at_declared_cap",
        "reason": "actual prior approved cap reached",
        "cap_evidence": cap,
        "financial_qualification": "unknown",
        "evidence_sha256": runner.payload_digest(job["raw"]),
    }


def _selected_teacher_raw(source, jobs):
    _require(
        isinstance(source, dict) and set(source) == {"teacher_selection_job_id", "model"},
        "original conditional selector source schema differs",
    )
    identifier = source["teacher_selection_job_id"]
    _require(
        identifier in jobs and jobs[identifier]["operation"] == "teacher_selection",
        "original conditional teacher selector missing",
    )
    from run_pilot import _teacher_selection_control_raw

    raw = _teacher_selection_control_raw(jobs[identifier])
    _require(
        raw["model"] == source["model"] and raw["original_n"] in (1024, 4096, 16384, 65536),
        "original selector model/N changed",
    )
    return raw


def _selected_attempt_kind(identifier):
    allowed = {
        f"refinement:{kind}:{model}"
        for kind in ("teacher_N", "teacher_grid")
        for model in ("Heston", "local")
    }
    _require(identifier in allowed, "conditional selected-purpose attempt scope changed")
    return identifier.split(":")[1]


def _selected_attempt_input_raw(identifier, jobs, *, model, purpose):
    from run_pilot import input_identity

    _require(identifier in jobs, "conditional selected input source missing")
    row = jobs[identifier]
    _require(
        row["operation"] == "teacher_selected_inputs"
        and row["status"] in ("executed", "failed_at_declared_cap", "unexecuted_dependency_cap"),
        "conditional selected input typed producer changed",
    )
    raw = (
        row["raw"].get("selected_inputs_inspection")
        if row["status"] == "unexecuted_dependency_cap"
        else row["raw"]
    )
    _require(
        raw is not None
        and raw["kind"] == "teacher_selected_inputs"
        and raw["model"] == model
        and raw["purpose"] == purpose,
        "conditional selected input model/purpose changed",
    )
    selector = _selected_teacher_raw(
        {"teacher_selection_job_id": raw["selector_job_id"], "model": model}, jobs
    )
    _require(
        raw["selector_raw_sha256"] == input_identity(selector)
        and raw["selected_stage_job_id"] == selector["selected_stage_job_id"],
        "conditional selected input actual selector source changed",
    )
    n, grid = selector["original_n"], selector["grid"]
    ladder = execution.execution_candidate()["original_candidate"]["teacher"]["n_candidates"]
    expected_n = ladder[min(ladder.index(n) + 1, len(ladder) - 1)] if purpose == "teacher_N" else n
    expected_grid = (
        ("high" if grid == "coarse" else "coarse") if purpose == "teacher_grid" else grid
    )
    _require(
        raw["original_n"] == expected_n
        and raw["selected_original_n"] == n
        and raw["grid"] == expected_grid,
        "conditional selected purpose original N/grid changed",
    )
    target_id = raw["selected_teacher_job_id"]
    _require(target_id in jobs, "conditional selected actual teacher source missing")
    target = jobs[target_id]
    _require(
        target["operation"] == "teacher_domain_selection"
        and raw["selected_teacher_raw_sha256"] == input_identity(target["raw"]),
        "conditional selected actual teacher source SHA changed",
    )
    if raw["availability"] == "available":
        t = target["raw"]
        _require(
            target["status"] == "executed"
            and t["kind"] == "teacher_grid"
            and t["model"] == model
            and t["original_n"] == expected_n
            and t["grid"] == expected_grid
            and input_identity(t["cache"]) == input_identity(raw["cache"]),
            "conditional selected current cache/producer changed",
        )
        reference = t.get("teacher_reference")
        if purpose == "teacher_N" and n == ladder[-1]:
            from run_pilot import _validate_teacher_reference

            _require(reference is not None, "conditional selected maximum reference uses principal")
            _validate_teacher_reference(reference, t["seed"], expected_n)
        else:
            _require(reference is None, "conditional selected principal/grid reference changed")
        di = raw["selected_teacher_driver_job_id"]
        _require(
            di in jobs
            and jobs[di]["operation"] == "teacher_driver"
            and jobs[di]["status"] == "executed"
            and input_identity(jobs[di]["raw"])
            == input_identity(t["driver"])
            == input_identity(raw["driver"])
            == raw["selected_teacher_driver_raw_sha256"],
            "conditional selected exact current driver source changed",
        )
    else:
        _require(
            raw["availability"] == "unavailable"
            and raw["cache"] is None
            and raw["driver"] is None
            and raw["parent_unavailable_job_ids"]
            and row["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap"),
            "conditional selected unavailable source cannot be imputed",
        )
    return raw


def _selected_attempt_source_map(identifier, source, jobs):
    kind = _selected_attempt_kind(identifier)
    _require(
        isinstance(source, dict)
        and set(source) == {"Heston", "local"}
        and all(set(source[m]) == {"principal", kind} for m in ("Heston", "local")),
        "conditional selected full model/purpose source map changed",
    )
    raw = {
        m: {
            p: _selected_attempt_input_raw(source[m][p], jobs, model=m, purpose=p)
            for p in ("principal", kind)
        }
        for m in ("Heston", "local")
    }
    return raw


def conditional_binding_source_ids(source):
    if "teacher_selection_job_id" in source:
        return {source["teacher_selection_job_id"]}
    if "teacher_selection_job_ids" in source:
        return set(source["teacher_selection_job_ids"].values())
    if "selected_inputs_job_ids" in source:
        return {
            identifier
            for by_purpose in source["selected_inputs_job_ids"].values()
            for identifier in by_purpose.values()
        }
    raise ValueError("conditional original source schema unsupported")


def concrete_original_n_plan(plan, jobs):
    import copy

    result = copy.deepcopy(plan)
    source = plan.get("original_n_source")
    if source is None:
        return result
    if "teacher_selection_job_ids" in source:
        _require(
            plan["id"] in ("domain_selection", "frequency:24", "frequency:48")
            and plan.get("original_n") is None
            and set(source) == {"teacher_selection_job_ids", "rule"}
            and source["rule"] == "max_selected_teacher_N"
            and set(source["teacher_selection_job_ids"]) == {"Heston", "local"},
            "conditional selected teacher-count attempt scope changed",
        )
        actual = {
            m: _selected_teacher_raw(
                {"teacher_selection_job_id": source["teacher_selection_job_ids"][m], "model": m},
                jobs,
            )
            for m in ("Heston", "local")
        }
        result.update(
            original_n=max(raw["original_n"] for raw in actual.values()),
            prior_template_sha256=run_pilot_identity(plan),
            selector_raw_sha256=run_pilot_identity(actual),
        )
        return result
    if "selected_inputs_job_ids" in source:
        _require(
            plan.get("original_n") is None
            and set(source) == {"selected_inputs_job_ids", "rule"}
            and source["rule"] == "max_selected_purpose_N",
            "conditional selected purpose-count attempt scope changed",
        )
        actual = _selected_attempt_source_map(plan["id"], source["selected_inputs_job_ids"], jobs)
        result.update(
            original_n=max(
                raw["original_n"] for by_purpose in actual.values() for raw in by_purpose.values()
            ),
            prior_template_sha256=run_pilot_identity(plan),
            selector_raw_sha256=run_pilot_identity(actual),
        )
        return result
    allowed = {
        r["id"] for r in execution.execution_candidate()["pilot_cases"] if r["kind"] == "state"
    }
    allowed |= {f"teacher:{m}:date{j}" for m in ("Heston", "local") for j in range(12)}
    _require(
        plan["id"] in allowed and plan.get("original_n") is None,
        "fixed original denominator cannot become a conditional count",
    )
    raw = _selected_teacher_raw(source, jobs)
    result.update(
        original_n=raw["original_n"],
        prior_template_sha256=run_pilot_identity(plan),
        selector_raw_sha256=run_pilot_identity(raw),
    )
    return result


def concrete_case_binding(binding, jobs):
    if "job_id_source" not in binding:
        return dict(binding)
    source = binding["job_id_source"]
    _require(
        set(source) == {"teacher_selection_job_id", "model", "case_id"}
        and source["case_id"] == binding["id"],
        "original selected case source changed",
    )
    descriptor = next(
        (
            r
            for r in execution.execution_candidate()["pilot_cases"]
            if r["id"] == binding["id"] and r["kind"] == "state"
        ),
        None,
    )
    _require(
        descriptor is not None and descriptor["identity"]["model"] == source["model"],
        "original selected state/model changed",
    )
    raw = _selected_teacher_raw({k: v for k, v in source.items() if k != "case_id"}, jobs)
    return dict(
        binding,
        job_id=raw["selected_state_case_job_ids"][source["case_id"]],
        control_job_ids=[source["teacher_selection_job_id"]],
    )


def concrete_attempt_binding(binding, jobs):
    if "job_ids_source" not in binding:
        return dict(binding)
    source = binding["job_ids_source"]
    if "selected_inputs_job_ids" in source:
        _require(
            set(source) == {"selected_inputs_job_ids", "fixed_job_ids"},
            "conditional selected attempt binding schema changed",
        )
        raw = _selected_attempt_source_map(binding["id"], source["selected_inputs_job_ids"], jobs)
        kind = _selected_attempt_kind(binding["id"])
        fixed = source["fixed_job_ids"]
        _require(
            isinstance(fixed, list)
            and len(set(fixed)) == len(fixed)
            and all(identifier in jobs for identifier in fixed),
            "conditional fixed original attempt work missing or duplicated",
        )
        selected = [
            raw[m][p]["selected_teacher_job_id"]
            for m in ("Heston", "local")
            for p in ("principal", kind)
        ]
        control = [
            source["selected_inputs_job_ids"][m][p]
            for m in ("Heston", "local")
            for p in ("principal", kind)
        ]
        control += [raw[m]["principal"]["selector_job_id"] for m in ("Heston", "local")]
        return dict(
            binding,
            job_ids=list(dict.fromkeys(fixed + selected)),
            control_job_ids=list(dict.fromkeys(control)),
            conditional_source_sha256=run_pilot_identity(raw),
        )
    _require(
        set(source) == {"teacher_selection_job_id", "model", "date_index"}
        and binding["id"] == f"teacher:{source['model']}:date{source['date_index']}",
        "original selected date source changed",
    )
    raw = _selected_teacher_raw({k: v for k, v in source.items() if k != "date_index"}, jobs)
    return dict(
        binding,
        job_ids=[
            raw["selected_teacher_job_id"],
            raw["selected_date_job_ids"][str(source["date_index"])],
        ],
        control_job_ids=[source["teacher_selection_job_id"]],
    )


def check_teacher_selected_inputs_record(record, **arguments):
    from run_pilot import run_teacher_selected_inputs_job

    calculated = run_teacher_selected_inputs_job(**arguments)
    runner._same(calculated, record, "selected original purpose input arithmetic")
    return {
        "integrity": "pass",
        "original_n": calculated["original_n"],
        "availability": calculated["availability"],
        "selected_teacher_job_id": calculated["selected_teacher_job_id"],
        "financial_qualification": "unknown",
    }


def check_teacher_selection_record(record, **arguments):
    from run_pilot import run_teacher_selection_job

    calculated = run_teacher_selection_job(**arguments)
    runner._same(calculated, record, "original actual teacher selection")
    return {
        "integrity": "pass",
        "original_n": calculated["original_n"],
        "selection_status": calculated["selection_status"],
        "financial_qualification": "unknown",
        "cache": calculated["cache"],
    }


def check_unused_teacher_job(
    job, planned, *, inputs, jobs, planned_jobs, activation_cache, artifact_context=None
):
    from run_pilot import teacher_activation_decision, unused_teacher_prefix_raw

    _require(
        job["status"] == "not_required_after_qualified_prefix",
        "actual unused prefix status required",
    )
    decision = teacher_activation_decision(
        planned, inputs, jobs, planned_jobs, activation_cache, artifact_context=artifact_context
    )
    _require(decision["execute"] is False, "actual original lower candidate must be qualified")
    runner._same(
        unused_teacher_prefix_raw(planned, decision), job["raw"], "original unused teacher prefix"
    )
    return {
        "integrity": "pass",
        "original_n": planned.get("original_n"),
        "executed_original_n": 0,
        "execution_status": "not_executed",
        "qualification": "unknown",
        "lower_gate_job_id": decision["lower_gate_job_id"],
        "lower_gate_evidence_sha256": decision["lower_gate_evidence_sha256"],
    }


def check_teacher_domain_selection_record(teacher, record, *, selection_rule):
    from run_pilot import run_teacher_domain_selection_job

    calculated = run_teacher_domain_selection_job(teacher=teacher, selection_rule=selection_rule)
    runner._same(calculated, record, "original fixed domain box selection")
    return {
        "integrity": "pass",
        "original_n": teacher["original_n"],
        "financial_qualification": "unknown",
        "evaluation_domains": calculated["evaluation_domains"],
        "scope": "computational support candidate; no SE/Greek qualification",
    }


def check_teacher_driver_comparison(teacher, reference, *, reference_rule, artifact_context=None):
    """Authenticate saved full drivers and exact shared prefixes without RNG."""
    from run_pilot import _validate_teacher_reference, read_teacher_driver_chunks

    left, right = teacher["driver"], reference["driver"]
    n, m = teacher["original_n"], reference["original_n"]
    if reference_rule == "independent_reserved_stream_grid_max":
        _require(
            n == m == 65536 and left["global_driver_id"] != right["global_driver_id"],
            "maximum reserved independent driver required",
        )
        purpose = {
            "reference_rule": reference_rule,
            "stream_namespace": "oracle",
            "seed": reference["seed"],
        }
        _validate_teacher_reference(purpose, reference["seed"], m)
        _require(
            reference.get("teacher_reference") == right.get("teacher_reference") == purpose
            and teacher.get("teacher_reference") is None,
            "maximum reserved reference purpose cannot enter principal teacher",
        )
        _require(
            left["original_n"] == n and right["original_n"] == m,
            "original independent driver denominator differs",
        )
        for driver in (left, right):
            for _ in read_teacher_driver_chunks(driver, artifact_context=artifact_context):
                pass
        return {
            "reference_rule": reference_rule,
            "original_teacher_n": n,
            "original_reference_n": m,
            "independent_driver_ids": [left["global_driver_id"], right["global_driver_id"]],
            "financial_qualification": "unknown",
        }
    _require(
        reference_rule == "next_prefix"
        and n < m
        and teacher["seed"] == reference["seed"] == left["seed"] == right["seed"]
        and np.array_equal(left["calendar_times"], right["calendar_times"]),
        "original next-prefix stream changed",
    )
    _require(
        left["original_n"] == n and right["original_n"] == m,
        "original prefix driver denominator differs",
    )
    larger = iter(read_teacher_driver_chunks(right, artifact_context=artifact_context))
    current = next(larger)
    done = 0
    for small in read_teacher_driver_chunks(left, artifact_context=artifact_context):
        pos, stop = small["path_start"], small["path_stop"]
        while pos < stop:
            if pos == current["path_stop"]:
                current = next(larger)
            _require(
                current["path_start"] <= pos < current["path_stop"], "original prefix driver gap"
            )
            end = min(stop, current["path_stop"])
            _require(
                np.array_equal(
                    small["normal"][pos - small["path_start"] : end - small["path_start"]],
                    current["normal"][pos - current["path_start"] : end - current["path_start"]],
                ),
                "actual original saved teacher prefix differs",
            )
            done += end - pos
            pos = end
    for _ in larger:
        pass
    _require(done == n, "actual entire original prefix missing")
    return {
        "reference_rule": reference_rule,
        "actual_prefix_n": n,
        "original_reference_n": m,
        "financial_qualification": "unknown",
    }


def _teacher_stage_cache_values(stage_plan, rows):
    """Resolve exact original producer arrays before testing any financial gate."""
    declared = stage_plan.get("cache_bindings")
    _require(
        isinstance(declared, dict) and set(declared) == set(stage_plan["pnl_bindings"]),
        "stage cache bindings missing or refinement scope changed",
    )
    values, hashes, identifiers = {}, {}, set()
    from run_pilot import input_identity

    for kind, sides in declared.items():
        _require(set(sides) == {"base", "refined"}, "stage cache side bindings changed")
        values[kind], hashes[kind] = {}, {}
        for prefix, models in sides.items():
            _require(set(models) == {"Heston", "local"}, "stage cache model roster changed")
            values[kind][prefix], hashes[kind][prefix] = {}, {}
            for model, binding in models.items():
                _require(
                    set(binding) == {"call_job_id", "asian_job_id"},
                    "stage cache producer schema changed",
                )
                ci, ai = binding["call_job_id"], binding["asian_job_id"]
                _require(ci in rows and ai in rows, "stage cache producer evidence missing")
                call, asian = rows[ci], rows[ai]
                _require(
                    call["operation"] == "call_cache"
                    and call["raw"].get("kind") == "call_cache"
                    and asian["operation"] in ("teacher_grid", "teacher_domain_selection")
                    and asian["raw"].get("kind") == "teacher_grid",
                    "stage cache must use actual original typed producers",
                )
                c, a = call["raw"]["value"], asian["raw"]["cache"]
                _require(
                    c is not None
                    and a is not None
                    and c["model"] == a["model"] == model.lower()
                    and asian["raw"]["model"] == model,
                    "stage cache model or unavailable producer changed",
                )
                values[kind][prefix][model.lower()] = {"call": c, "asian": a}
                hashes[kind][prefix][model] = {
                    "call": input_identity(c),
                    "asian": input_identity(a),
                }
                identifiers.update((ci, ai))
    return values, hashes, identifiers


def _teacher_stage_cache_geometry(stage_plan, rows):
    declared = stage_plan["cache_bindings"]
    model, other = stage_plan["model"], ("local" if stage_plan["model"] == "Heston" else "Heston")
    original = next(iter(declared.values()))["base"]
    call_ids = {m: original[m]["call_job_id"] for m in ("Heston", "local")}
    other_id = original[other]["asian_job_id"]
    _require(
        rows[other_id]["raw"]["original_n"] == 1024
        and rows[other_id]["raw"]["grid"] == "coarse"
        and rows[other_id]["raw"]["cache"]["original_N"] == 1024,
        "stage other-model cache must retain actual1024coarse baseline",
    )
    expected = {
        "base": stage_plan["teacher_job_id"],
        "teacher_N": stage_plan["next_teacher_job_id"],
        "teacher_grid": stage_plan["grid_teacher_job_id"],
    }
    for kind, sides in declared.items():
        for prefix, bindings in sides.items():
            _require(
                all(bindings[m]["call_job_id"] == call_ids[m] for m in call_ids),
                "stage original common call cache producer changed",
            )
            _require(
                bindings[other]["asian_job_id"] == other_id,
                "stage other-model cache changed during candidate refinement",
            )
            ai = expected.get(kind, expected["base"]) if prefix == "refined" else expected["base"]
            _require(
                bindings[model]["asian_job_id"] == ai,
                "stage candidate cache is not the declared N/grid refinement",
            )
    for key in ("teacher_job_id", "next_teacher_job_id", "grid_teacher_job_id"):
        raw = rows[stage_plan[key]]["raw"]
        _require(
            raw["cache"]["original_N"] == raw["original_n"],
            "stage cache original teacher denominator differs",
        )


def check_teacher_stage_risk_sources(parameters, surface, *, stage_plan, rows):
    """Bind saved cache/risk/cash transport; this alone certifies no financial scope."""
    from run_pilot import input_identity, unpack_inputs

    caches, hashes, identifiers = _teacher_stage_cache_values(stage_plan, rows)
    for identifier in identifiers:
        row = rows[identifier]
        if row["operation"] != "call_cache":
            continue
        args = unpack_inputs(row["raw"].get("arguments"))
        _require(
            isinstance(args, dict) and "parameters" in args and "surface" in args,
            "stage cache actual call producer arguments missing",
        )
        _require(
            input_identity(args["parameters"]) == input_identity(parameters),
            "stage cache parameters differ from actual risk parameters",
        )
        _require(
            (row["raw"]["value"]["model"] == "heston" and args["surface"] is None)
            or input_identity(args["surface"]) == input_identity(surface),
            "stage cache local field differs from actual risk field",
        )
    risk_arguments, validations, fit_hashes = {}, {}, set()
    pairs = 0
    for kind, bindings in stage_plan["pnl_bindings"].items():
        for binding in bindings:
            _require(
                {"job_id", "base_risk_job_id", "refined_risk_job_id"} <= set(binding),
                "stage actual pair/risk producer bindings required",
            )
            ji = binding["job_id"]
            _require(ji in rows, "stage actual paired producer missing")
            pair = rows[ji]
            _require(
                pair["operation"] == "cell_pair", "stage original typed cell producer required"
            )
            raw, actual = pair["raw"], pair.get("arguments")
            _require(isinstance(actual, dict), "stage actual paired arguments missing")
            selection = raw.get("selection_inputs")
            _require(isinstance(selection, dict), "stage original validation selection missing")
            _require(
                input_identity(selection)
                == input_identity({k: actual[k] for k in ("validation", "fits", "identity")}),
                "stage original validation/fit/identity producer changed",
            )
            key = (raw["identity"]["generator"], raw["identity"]["universe"])
            digest = input_identity(selection["validation"])
            _require(
                key not in validations or validations[key] == digest,
                "stage fixed validation changed across numerical refinements",
            )
            validations[key] = digest
            fit_hashes.add(input_identity(selection["fits"]))
            _require(len(fit_hashes) == 1, "stage fixed fit roster changed across refinements")
            for prefix in ("base", "refined"):
                ri = binding[prefix + "_risk_job_id"]
                _require(ri in rows, "stage actual risk producer evidence missing")
                source = rows[ri]
                risk = source["raw"]
                expected_op = (
                    "bump_risk" if kind == "position" and prefix == "refined" else "quote_risk"
                )
                _require(
                    source["operation"] == risk.get("kind") == expected_op,
                    "stage risk producer has wrong numerical method",
                )
                if ri not in risk_arguments:
                    source_args = unpack_inputs(source.get("arguments"))
                    _require(
                        isinstance(source_args, dict),
                        "stage actual risk producer arguments missing",
                    )
                    if expected_op == "quote_risk":
                        args = unpack_inputs(risk["arguments"])
                        _require(
                            input_identity(args) == input_identity(source_args),
                            "stage risk producer actual argument binding changed",
                        )
                        _require(
                            input_identity(args["surface"]) == input_identity(surface),
                            "stage actual risk field changed",
                        )
                    else:
                        args = source_args
                        _require(
                            all(
                                input_identity(args[k]) == input_identity(risk[k])
                                for k in ("parameters", "dataset", "caches", "base_risk")
                            ),
                            "stage bump risk producer actual arguments changed",
                        )
                    _require(
                        input_identity(args["parameters"]) == input_identity(parameters),
                        "stage actual risk parameters changed",
                    )
                    risk_arguments[ri] = args
                args = risk_arguments[ri]
                _require(
                    input_identity(args["caches"]) == input_identity(caches[kind][prefix]),
                    "stage actual risk cache differs from declared producer arrays",
                )
                _require(
                    input_identity(args["dataset"])
                    == input_identity(raw[prefix + "_dataset"])
                    == input_identity(actual[prefix + "_dataset"]),
                    "stage actual risk dataset differs from paired original paths",
                )
                _require(
                    input_identity(risk)
                    == input_identity(raw[prefix + "_risk_source"])
                    == input_identity(actual[prefix + "_risk_source"]),
                    "stage paired risk producer substituted",
                )
                if expected_op == "bump_risk":
                    width = binding.get("width_index")
                    _require(
                        width in (0, 1, 2)
                        and raw.get("refined_risk_width_index") == width
                        and actual.get("refined_risk_width_index") == width,
                        "stage original position width binding changed",
                    )
                    value = risk["risk_variants"][width]
                    _require(
                        input_identity(risk["base_risk"]) == input_identity(raw["base_risk"]),
                        "stage refit base risk differs from actual IFT producer",
                    )
                else:
                    value = risk["value"]
                _require(
                    input_identity(value)
                    == input_identity(raw[prefix + "_risk"])
                    == input_identity(actual[prefix + "_risk"]),
                    "stage paired actual risk value/width substituted",
                )
                identifiers.add(ri)
            _require(
                raw["refinement_kind"] == actual["refinement_kind"] == kind
                and input_identity(raw.get("shared_market"))
                == input_identity(actual.get("shared_market")),
                "stage actual shared market/refinement producer changed",
            )
            identifiers.add(ji)
            pairs += 1
    return {
        "bound_pair_count": pairs,
        "bound_producer_ids": sorted(identifiers),
        "raw_cache_sha256": hashes,
        "financial_qualification": "unknown",
        "scope": "saved exact producer/input binding only; original gates separately required",
    }


def calculate_teacher_candidate_gate(
    parameters, surface, *, stage_plan, evidence, artifact_context=None
):
    """Recompute a whole original teacher candidate from typed saved evidence.

    Lower candidates require next-prefix comparison. The maximum uses the
    original reserved independent stream/grid exception, never invented N262144.
    Failures stay in all18 states/all12 dates/all Greek-band cells.
    """
    candidate = execution.execution_candidate()
    required_keys = {
        "model",
        "original_n",
        "grid",
        "required_job_ids",
        "teacher_job_id",
        "next_teacher_job_id",
        "grid_teacher_job_id",
        "date_bindings",
        "state_bindings",
        "pnl_bindings",
        "reference_rule",
        "oracle_original_n",
    }
    _require(required_keys <= set(stage_plan), "original teacher stage binding missing")
    model, n, grid = (stage_plan[k] for k in ("model", "original_n", "grid"))
    ladder = candidate["original_candidate"]["teacher"]["n_candidates"]
    _require(
        model in ("Heston", "local") and n in ladder and grid in ("coarse", "high"),
        "original teacher candidate N/grid changed",
    )
    dates, states = stage_plan["date_bindings"], stage_plan["state_bindings"]
    expected_states = [
        r
        for r in candidate["pilot_cases"]
        if r["kind"] == "state" and r["identity"]["model"] == model
    ]
    _require(
        len(dates) == 12
        and {r["date_index"] for r in dates} == set(range(12))
        and len(states) == 18
        and {r["id"] for r in states} == {r["id"] for r in expected_states},
        "full12date and18state stage roster required",
    )
    cells = [
        r for r in candidate["original_roster"]["primary_cells"] if r["policy"] in ("greek", "band")
    ]
    kinds = {"SDE", "teacher_N", "teacher_grid", "position", "pnl"}
    _require(
        set(stage_plan["pnl_bindings"]) == kinds,
        "original full numeric refinement stage bindings missing",
    )
    for kind, bindings in stage_plan["pnl_bindings"].items():
        expected = {
            (r["id"], w) for r in cells for w in ((0, 1, 2) if kind == "position" else (None,))
        }
        _require(
            len(bindings) == len(expected)
            and {(r["cell_id"], r.get("width_index")) for r in bindings} == expected,
            "original all Greek-band/three-width refinement roster changed",
        )
    rows = {r["id"]: r for r in evidence}
    _require(
        len(rows) == len(evidence) and set(rows) == set(stage_plan["required_job_ids"]),
        "original stage typed evidence scope differs",
    )
    bound = {
        stage_plan["teacher_job_id"],
        stage_plan["next_teacher_job_id"],
        stage_plan["grid_teacher_job_id"],
    }
    bound |= {r["job_id"] for r in dates + states}
    bound |= {r["job_id"] for value in stage_plan["pnl_bindings"].values() for r in value}
    _require(bound <= set(rows), "original stage referenced work unexecuted")
    reference_n = ladder[min(ladder.index(n) + 1, len(ladder) - 1)]
    reference_rule = "next_prefix" if n != ladder[-1] else "independent_reserved_stream_grid_max"
    _require(
        stage_plan["reference_rule"] == reference_rule
        and stage_plan["oracle_original_n"] == reference_n,
        "original ordered teacher reference rule/N changed",
    )
    cache_risk_binding = check_teacher_stage_risk_sources(
        parameters, surface, stage_plan=stage_plan, rows=rows
    )
    _teacher_stage_cache_geometry(stage_plan, rows)
    _require(
        set(cache_risk_binding["bound_producer_ids"]) <= set(stage_plan["required_job_ids"]),
        "original stage cache/risk producer evidence scope missing",
    )
    context = {"parameters": parameters, "surface": surface, "artifact_context": artifact_context}
    checks = {}
    for identifier, row in rows.items():
        manifest = {"n_paths": row["raw"].get("original_path_count")}
        checks[identifier] = _raw_job_check(
            {"operation": row["operation"], "raw": row["raw"], "argument_manifest": manifest},
            dict(context, resolved_arguments=row.get("arguments", {})),
        )
    teacher = rows[stage_plan["teacher_job_id"]]["raw"]
    higher = rows[stage_plan["next_teacher_job_id"]]["raw"]
    highgrid = rows[stage_plan["grid_teacher_job_id"]]["raw"]
    _require(
        teacher["kind"] == higher["kind"] == highgrid["kind"] == "teacher_grid"
        and teacher["model"] == higher["model"] == highgrid["model"] == model
        and teacher["original_n"] == highgrid["original_n"] == n
        and higher["original_n"] == reference_n
        and teacher["grid"] == grid
        and highgrid["grid"] != grid,
        "original full-grid N/grid candidate comparison differs",
    )
    comparison = check_teacher_driver_comparison(
        teacher, higher, reference_rule=reference_rule, artifact_context=artifact_context
    )
    for identifier in (
        stage_plan["teacher_job_id"],
        stage_plan["next_teacher_job_id"],
        stage_plan["grid_teacher_job_id"],
    ):
        value = checks[identifier]
        _require(
            value["cache"] is not None
            and all(r["full_saved_driver_sde_replayed"] for r in value["raw_checks"]),
            "actual full saved-driver teacher SDE evidence missing",
        )
    projected = []
    for binding in dates:
        row = rows[binding["job_id"]]
        _require(
            row["operation"] == "date_gate"
            and row["raw"]["model"] == model
            and row["raw"]["date_index"] == binding["date_index"]
            and row["raw"]["original_n"] == n,
            "original full-date teacher stage identity changed",
        )
        projected.append(
            _projection(
                {
                    "id": "teacher-date:" + str(binding["date_index"]),
                    "gates": ["teacher_price_se", "stock_position_se", "call_position_se"],
                },
                checks[binding["job_id"]]["measurements"],
                n,
            )
        )
    state_descriptors = {r["id"]: r for r in expected_states}
    oracle_seeds = set()
    for binding in states:
        row = rows[binding["job_id"]]
        _require(row["operation"] == "state", "stage selected state typed source differs")
        oracle = row["raw"]["oracle"]
        _require(
            oracle.get("original_path_count", oracle.get("N")) == reference_n
            and oracle["scheme_refinement"]["levels"] == [768, 1536],
            "independent all13query reference N/grid changed",
        )
        oracle_seeds.add(oracle["seed"])
        projected.append(
            project_case(
                state_descriptors[binding["id"]],
                checks[binding["job_id"]],
                row["raw"],
                {"original_n": n},
            )
        )
    _require(
        oracle_seeds == set(candidate["original_candidate"]["seeds"]["oracle"]),
        "original three reserved independent oracle streams changed",
    )
    for kind, bindings in stage_plan["pnl_bindings"].items():
        for binding in bindings:
            row = rows[binding["job_id"]]
            _require(
                row["operation"] in ("cell_pair", "paired_pnl")
                and row["raw"]["identity"]["id"] == binding["cell_id"]
                and row["raw"]["refinement_kind"] == kind
                and row["raw"].get("refined_risk_width_index") == binding.get("width_index"),
                "original dynamic numeric refinement identity changed",
            )
            _require(
                checks[binding["job_id"]]["shared_CRN_checked"],
                "stage full original paired shared-market evidence missing",
            )
            projected.append(
                _projection(
                    {
                        "id": kind
                        + ":"
                        + binding["cell_id"]
                        + ":"
                        + str(binding.get("width_index")),
                        "gates": ["pnl_rms_difference", "mse_difference", "baseline_mse"],
                    },
                    checks[binding["job_id"]],
                    row["raw"]["original_n"],
                )
            )
    passed = all(r["financial_qualification"] == "qualified" for r in projected)
    return {
        "kind": "teacher_candidate_gate",
        "model": model,
        "original_n": n,
        "grid": grid,
        "reference_rule": reference_rule,
        "driver_comparison": comparison,
        "stage_cache_risk_bindings": cache_risk_binding,
        "oracle_original_n": reference_n,
        "original_date_count": 12,
        "original_state_count": 18,
        "original_greek_band_cell_count": len(cells),
        "projected_gate_rows": projected,
        "qualification": "qualified" if passed else "unknown",
        "reason": None
        if passed
        else "original full stage numerical uncertainty/precision gate failed",
        "stage_plan_sha256": run_pilot_identity(stage_plan),
        "raw_evidence_sha256": {
            identifier: runner.payload_digest(row) for identifier, row in rows.items()
        },
        "financial_qualification": "unknown",
        "scope": "teacher candidate numerical gate only; not formal pilot/main certification",
    }


def _execution_verification(inputs, evidence):
    return {
        "checker": "saved full-original pilot semantic projection",
        "evidence_sha256": runner.payload_digest(evidence),
        "inputs": inputs,
    }


def _prior_execution_projection(row, base_plan, specification, jobs):
    """Choose only an immutable pretest cap option bound to an actual parent."""
    import copy

    plan = copy.deepcopy(base_plan)
    alias = {
        "id": base_plan["expense_id"],
        "parent_expense_id": specification.get("parent_expense_id"),
        "required_job_ids": specification["required_job_ids"],
    }
    decision = None
    if row.get("cap_evidence") is not None:
        parents = row.get("cap_parent_job_ids", [row["cap_parent_job_id"]])
        options = specification.get("cap_options", [])
        option = next((r for r in options if r.get("parent_job_id") in parents), None)
        _require(option is not None, "actual cap lacks compatible prior execution option")
        parent = jobs[option["parent_job_id"]]
        _require(
            parent["status"] == "failed_at_declared_cap",
            "execution cap parent was not actually consumed",
        )
        selected = copy.deepcopy(option["plan"])
        _require(
            {k: v for k, v in selected.items() if k != "cap"}
            == {k: v for k, v in base_plan.items() if k != "cap"},
            "prior cap option changes original case/attempt plan",
        )
        cap = selected.get("cap")
        actual = parent["cap_evidence"]
        _require(
            cap is not None
            and cap.get("planned_before_attempt") is True
            and cap["metric"] == actual["metric"]
            and cap["limit"] == actual["limit"],
            "execution cap metric/limit differs from actual reviewed parent",
        )
        decision = option.get("budget_decision")
        _require(
            isinstance(decision, dict)
            and decision.get("decision") == "approved"
            and decision.get("planned_before_attempt") is True
            and cap["budget_review_sha256"] == execution._digest(decision),
            "execution cap lacks prior independent budget decision",
        )
        _require(
            decision.get("plan_sha256")
            == execution._digest(
                {k: v for k, v in selected.items() if k != "cap"}
                | {"cap": {k: v for k, v in cap.items() if k != "budget_review_sha256"}}
            ),
            "prior execution cap decision differs from exact plan",
        )
        plan = selected
        row["cap_evidence"] = copy.deepcopy(actual) | {
            "evidence_sha256": runner.payload_digest(
                {
                    "actual_parent": parent,
                    "prior_option": option,
                    "all_parent_bindings": row.get("parent_cap_bindings"),
                }
            ),
        }
        alias.update(parent_expense_id=parent["expense"]["id"], required_job_ids=[parent["id"]])
        row["execution_cap_parent_job_id"] = parent["id"]
        row["prior_cap_option_sha256"] = runner.payload_digest(option)
    else:
        _require(plan.get("cap") is None, "uncapped record needs prior ordinary execution plan")
    row["expense_id"] = plan["expense_id"]
    row.setdefault("cap_evidence", None)
    row.setdefault("first_failure_date", None)
    return plan, alias, decision


def concrete_execution_specification(specification, jobs):
    import copy

    result = copy.deepcopy(specification)
    if "required_case_binding" in result:
        _require("required_job_ids" not in result, "ambiguous prior case alias work")
        bound = concrete_case_binding(result["required_case_binding"], jobs)
        result["required_job_ids"] = [bound["job_id"], *bound.get("control_job_ids", [])]
    elif "required_attempt_binding" in result:
        _require("required_job_ids" not in result, "ambiguous prior attempt alias work")
        bound = concrete_attempt_binding(result["required_attempt_binding"], jobs)
        result["required_job_ids"] = list(
            dict.fromkeys(bound["job_ids"] + bound.get("control_job_ids", []))
        )
    _require(result.get("required_job_ids"), "prior original alias work source missing")
    return result


def derive_execution_selection(specification, jobs, checks):
    """Derive realized values from verified raw; the prior binds rules/producer IDs."""
    import copy

    original = execution.execution_candidate()["original_candidate"]
    static = {
        k: original["hedging"][k]
        for k in ("band_width_candidates", "baseline_rule", "checkpoint_rule")
    }
    runner._same(static, specification["static"], "prior original selection rules")
    result = copy.deepcopy(static)
    result.update(teacher_n={}, teacher_grid={}, teacher_selection_status={})
    identifiers = specification["teacher_selection_job_ids"]
    _require(set(identifiers) == {"Heston", "local"}, "prior both teacher selectors missing")
    for model, identifier in identifiers.items():
        _require(identifier in checks, "unverified original teacher selection")
        raw = _selected_teacher_raw({"teacher_selection_job_id": identifier, "model": model}, jobs)
        result["teacher_n"][model] = raw["original_n"]
        result["teacher_grid"][model] = raw["grid"]
        result["teacher_selection_status"][model] = (
            raw["selection_status"] if jobs[identifier]["status"] == "executed" else "unavailable"
        )
    identifier = specification["premium_job_id"]
    _require(
        identifier in checks
        and jobs[identifier]["operation"] == "premium"
        and jobs[identifier]["status"] == "executed",
        "actual independent premium unavailable",
    )
    premium = checks[identifier]
    _require(
        premium["original_n"] == 65536
        and all(premium[k] is not None for k in ("value", "standard_error", "scheme_error")),
        "independent premium not numerically established",
    )
    result["premium"] = copy.deepcopy(original["premium"]) | {
        "value": premium["value"],
        "se": premium["standard_error"],
        "scheme_error": premium["scheme_error"],
    }
    precision = [checks[i] for i in specification["precision_job_ids"]]
    _require(
        [r["original_n"] for r in precision] == original["test"]["n_candidates"],
        "all original precision candidates required for selection",
    )
    qualified = [r["original_n"] for r in precision if r.get("qualification") == "qualified"]
    result.update(
        test_n=min(qualified) if qualified else 32768,
        precision_selection="smallest_qualified" if qualified else "unavailable",
    )
    return result


def derive_execution_domains(specification, jobs, checks):
    """Keep unavailable dates and original raw; defined means geometric support only."""
    from run_pilot import teacher_domain_rule

    result = []
    for model, identifier in specification["teacher_selection_job_ids"].items():
        _require(identifier in checks, "unverified original domain selector")
        raw = _selected_teacher_raw({"teacher_selection_job_id": identifier, "model": model}, jobs)
        teacher_id = raw["selected_teacher_job_id"]
        cache = raw.get("cache") if jobs[identifier]["status"] == "executed" else None
        teacher = jobs[teacher_id]["raw"]
        if cache is not None:
            runner._same(
                teacher_domain_rule(model),
                teacher["domain_selection"]["selection_rule"],
                "prior original domain selection rule",
            )
        for j in range(12):
            indices = None if cache is None else cache["evaluation_domains"][j]
            result.append(
                {
                    "id": f"domain:{model}:date{j}",
                    "model": model,
                    "date_index": j,
                    "selected_before_test": True,
                    "method": "fixed_cartesian_not_a_knot",
                    "selection_rule": "independent_pilot_fixed_box",
                    "status": "unavailable" if indices is None else "defined",
                    "indices": indices,
                    "reason": "no eligible original finite box" if indices is None else None,
                    "evidence_sha256": run_pilot_identity(
                        {"selector_raw": raw, "teacher_raw": teacher, "date_index": j}
                    ),
                    "financial_qualification": "unknown",
                    "scope": "geometric support only",
                }
            )
    return result


def project_execution_pilot(snapshot, *, expected_plan, context, selection, domains):
    """Recompute saved full raw before producing the private A input envelope.

    This is a metadata bridge, not an independent execution review or financial
    certificate. Missing raw obligations, original-N, phase/review/CAS clocks,
    progressive selection, and compatible pretest cap options cannot be filled.
    """
    import copy

    checked = check_pilot_records(snapshot, expected_plan=expected_plan, context=context)
    _require(
        checked["closed"] and checked.get("verification", {}).get("integrity") == "pass",
        "saved original pilot is not closed",
    )
    candidate = execution.execution_candidate()
    source = snapshot["source"]["protocol_source"]
    specifications = expected_plan.get("execution_projection")
    _require(isinstance(specifications, dict), "prior execution projection missing")
    case_plans = {p["id"]: p for p in expected_plan["case_plan"]}
    attempt_plans = {p["id"]: p for p in expected_plan["attempt_plan"]}
    case_specs = {p["id"]: p for p in specifications.get("cases", [])}
    attempt_specs = {p["id"]: p for p in specifications.get("attempts", [])}
    _require(
        set(case_specs) == set(case_plans) and set(attempt_specs) == set(attempt_plans),
        "prior execution projection changed original121/51",
    )
    jobs = {j["id"]: j for j in snapshot["jobs"]}
    _require(
        isinstance(specifications.get("selection_policy"), dict),
        "prior selection producer/rule policy required",
    )
    realized = derive_execution_selection(
        specifications["selection_policy"], jobs, checked["raw_checks"]
    )
    runner._same(realized, selection, "actual source-bound selection")
    realized_domains = derive_execution_domains(
        specifications["selection_policy"], jobs, checked["raw_checks"]
    )
    runner._same(realized_domains, domains, "actual source-bound fixed domains")
    cases, attempts, plans, groups, aliases, decisions = [], [], [], [], [], []
    for values, saved_plans, specs, rows_out, plans_out in (
        (checked["case_results"], case_plans, case_specs, cases, plans),
        (checked["attempt_results"], attempt_plans, attempt_specs, attempts, groups),
    ):
        for original_row in values:
            row = copy.deepcopy(original_row)
            identifier = row["id"]
            base_plan = concrete_original_n_plan(saved_plans[identifier], jobs)
            selector_sha = base_plan.pop("selector_raw_sha256", None)
            if selector_sha is not None:
                row["conditional_selection_binding"] = {
                    "prior_template_sha256": base_plan["prior_template_sha256"],
                    "selector_raw_sha256": selector_sha,
                    "producer_job_ids": row.get("required_job_ids", [row.get("job_id")]),
                }
            _require(
                isinstance(base_plan.get("original_n"), int)
                and row["original_n"] == base_plan["original_n"],
                "execution original N differs from prior plan",
            )
            required = row.get("required_job_ids", [row.get("job_id")])
            specification = concrete_execution_specification(specs[identifier], jobs)
            _require(
                specification["required_job_ids"] == required,
                "execution alias original work binding differs",
            )
            plan, alias, decision = _prior_execution_projection(row, base_plan, specification, jobs)
            if identifier in case_plans and base_plan["kind"] == "state":
                row["first_failure_date"] = (
                    base_plan["identity"]["date"]
                    if row["financial_qualification"] != "qualified"
                    else None
                )
            if (
                identifier in case_plans
                and base_plan["kind"] == "fit"
                and row["cap_evidence"] is None
            ):
                _require(
                    row.get("fit_validation") is not None,
                    "actual original fit-validation receipt missing",
                )
            if "outcome" not in row:
                row["outcome"] = (
                    "within_envelope"
                    if row["financial_qualification"] == "qualified"
                    else "measured_precision_failure"
                )
            if "status" not in row:
                row["status"] = (
                    "complete" if row["cap_evidence"] is None else "failed_at_declared_cap"
                )
            rows_out.append(row)
            plans_out.append(plan)
            aliases.append(alias)
            if decision is not None:
                decisions.append(copy.deepcopy(decision))
    expense_result = project_execution_expense_aliases(
        checked["costs"]["raw_expenses"], aliases, jobs=jobs
    )
    expenses = expense_result["raw_records"]
    by_expense = {r["id"]: r for r in expenses}
    for identifier in candidate["current_pilot_expense_ids"]:
        _require(identifier in by_expense, "actual current review/storage expense missing")
        value = by_expense[identifier]
        _check_actual_expense_clock(value, value.get("timing_events"))
        _require(
            value["status"] in ("complete", "failed"),
            "actual current review/storage expense pending",
        )
    common = {
        "candidate": execution._digest(candidate),
        "source": execution._digest(source),
        "domains": execution._digest(domains),
    }
    for rows_out, plans_out in ((cases, plans), (attempts, groups)):
        by_plan = {p["id"]: p for p in plans_out}
        for row in rows_out:
            row["verification"] = _execution_verification(
                common
                | {
                    "plan": execution._digest(by_plan[row["id"]]),
                    "record": execution._digest(
                        {k: v for k, v in row.items() if k != "verification"}
                    ),
                },
                {
                    "raw_snapshot": runner.payload_digest(snapshot),
                    "raw_check": checked["verification"],
                },
            )
    precision = []
    for job in snapshot["jobs"]:
        if job["operation"] == "precision":
            value = checked["raw_checks"][job["id"]]
            precision.append(
                {
                    k: value[k]
                    for k in (
                        "original_n",
                        "worst_mean_loss_se",
                        "worst_mse_se",
                        "baseline_mse",
                        "qualification",
                        "reason",
                        "evidence_sha256",
                    )
                }
            )
    pilot = {
        "schema": "rb-f04-execution-pilot-v1.1",
        "test_opened": False,
        "plans_locked_before_execution": True,
        "original_counts": copy.deepcopy(candidate["original_candidate"]["pilot"]),
        "original_model_state_slots": 36,
        "case_plan": plans,
        "cases": cases,
        "attempt_plan": groups,
        "attempts": attempts,
        "expenses": expenses,
        "history": copy.deepcopy(expected_plan["history"]),
        "test_precision": sorted(precision, key=lambda r: r["original_n"]),
        "integrity": {
            "source_complete": True,
            "raw_checked": True,
            "original_counts_checked": True,
            "rng_isolation_checked": True,
            "history_complete": True,
            "unresolved_issues": [],
        },
        "raw_snapshot_sha256": runner.payload_digest(snapshot),
        "saved_raw_verification": copy.deepcopy(checked["verification"]),
        "verification": _execution_verification(
            common | {"selection": execution._digest(selection)}, checked["verification"]
        ),
    }
    execution._selection(candidate, pilot, selection)
    execution._domains(candidate, selection, domains)
    _require(
        "selection_sha256" not in specifications and "domains_sha256" not in specifications,
        "pretest policy must not require future realized value hashes",
    )
    pilot["prior_selection_policy_sha256"] = runner.payload_digest(
        specifications["selection_policy"]
    )
    financial = (
        all(r["financial_qualification"] == "qualified" for r in cases + attempts)
        and all(d["status"] == "defined" for d in domains)
        and all(v == "qualified_selection" for v in selection["teacher_selection_status"].values())
        and selection["precision_selection"] == "smallest_qualified"
    )
    pilot["financial_qualification"] = "qualified" if financial else "unknown"
    execution._pilot(candidate, source, pilot, selection, domains)
    return {
        "pilot": pilot,
        "used_prior_budget_decisions": decisions,
        "financial_qualification": pilot["financial_qualification"],
        "scope": "saved raw A bridge; independent source/math/execution review still required",
    }


def check_pilot_records(snapshot, *, expected_plan, context=None):
    """Return raw recomputation and exact outstanding roster, never flag-only ready."""
    _require(snapshot.get("schema") == "rb-f04-pilot-raw-v1", "raw pilot schema mismatch")
    candidate = execution.execution_candidate()
    cases = {r["id"]: r for r in candidate["pilot_cases"]}
    attempts = set(candidate["required_pilot_attempt_ids"])
    if expected_plan is not None:
        from run_pilot import validate_locked_plan

        validate_locked_plan(expected_plan)
        _require(
            runner.payload_digest(snapshot["locked_plan"]) == runner.payload_digest(expected_plan),
            "saved prior plan mismatch",
        )
    _require(snapshot.get("test_opened", False) is False, "main test opened before pilot")
    jobs = {j["id"]: j for j in snapshot.get("jobs", [])}
    _require(len(jobs) == len(snapshot.get("jobs", [])), "repeated pilot job ID")
    context = dict(context or {})
    if "inputs" in context and "parameters" in context["inputs"]:
        from run_pilot import input_identity

        actual_parameters = context["inputs"]["parameters"]
        _require(
            "parameters" not in context
            or input_identity(context["parameters"]) == input_identity(actual_parameters),
            "checker financial parameters differ from original bound input",
        )
        context["parameters"] = actual_parameters
    checks, issues = {}, []
    activation_cache = {}
    planned_jobs = {} if expected_plan is None else {j["id"]: j for j in expected_plan["jobs"]}
    for identifier, job in jobs.items():
        if expected_plan is not None:
            _require(identifier in planned_jobs, "unplanned financial job")
            check_job_envelope(job, planned_jobs[identifier], expected_plan)
        if expected_plan is not None and job.get("status") in (
            "executed",
            "failed_at_declared_cap",
        ):
            try:
                _require("inputs" in context, "actual original pilot input context required")
                from run_pilot import _dependency_ids, _numeric_dependency_ids

                dependencies = _dependency_ids(planned_jobs[identifier]["arguments"])
                numeric = _numeric_dependency_ids(planned_jobs[identifier]["arguments"])
                _require(
                    all(i in checks for i in dependencies)
                    and all(jobs[i]["status"] == "executed" for i in numeric),
                    "unverified original numerical dependency cannot become executed",
                )
                context["resolved_arguments"] = check_resolved_job_arguments(
                    job,
                    planned_jobs[identifier],
                    inputs=context["inputs"],
                    jobs=jobs,
                    artifact_directory=snapshot.get("artifact_directory"),
                    planned_jobs=planned_jobs,
                )
            except (ValueError, KeyError) as error:
                issues.append(
                    {
                        "id": identifier,
                        "reason": str(error),
                        "status": "unclosed_original_dependency_binding",
                    }
                )
                continue
        if job.get("status") != "executed":
            try:
                if job.get("status") == "failed_at_declared_cap":
                    checks[identifier] = check_capped_job_raw(
                        job, artifact_context=context.get("artifact_context"), context=context
                    )
                elif job.get("status") == "not_required_after_qualified_prefix":
                    _require(
                        expected_plan is not None and "inputs" in context,
                        "prior actual unused teacher inputs required",
                    )
                    checks[identifier] = check_unused_teacher_job(
                        job,
                        planned_jobs[identifier],
                        inputs=context["inputs"],
                        jobs=jobs,
                        planned_jobs=planned_jobs,
                        activation_cache=activation_cache,
                        artifact_context=context.get("artifact_context"),
                    )
                elif job.get("status") == "unexecuted_dependency_cap":
                    _require(expected_plan is not None, "prior dependency cap plan required")
                    checks[identifier] = check_dependency_cap_job(
                        job,
                        planned_jobs[identifier],
                        expected_plan,
                        jobs,
                        inputs=context.get("inputs"),
                        artifact_context=context.get("artifact_context"),
                    )
                else:
                    issues.append(
                        {"id": identifier, "reason": job.get("reason"), "status": job.get("status")}
                    )
            except (ValueError, KeyError) as error:
                issues.append(
                    {
                        "id": identifier,
                        "reason": str(error),
                        "status": "unclosed_cap_semantic_check",
                    }
                )
            continue
        try:
            checks[identifier] = _raw_job_check(job, context)
            if job["operation"] == "field":
                from run_pilot import materialize_field

                context["surface"] = materialize_field(job["raw"])
        except (ValueError, KeyError) as error:
            issues.append(
                {"id": identifier, "reason": str(error), "status": "unclosed_semantic_check"}
            )
    bound_cases = snapshot.get("case_bindings", [])
    bound_attempts = snapshot.get("attempt_bindings", [])
    if expected_plan is not None:
        runner._same(
            expected_plan.get("case_bindings", []), bound_cases, "prior original case bindings"
        )
        runner._same(
            expected_plan.get("attempt_bindings", []),
            bound_attempts,
            "prior original attempt bindings",
        )
    for binding in bound_cases + bound_attempts:
        source = binding.get("job_id_source", binding.get("job_ids_source"))
        if source is not None:
            _require(
                conditional_binding_source_ids(source) <= set(checks),
                "unverified conditional original selector/adapter source",
            )
    bound_cases = [concrete_case_binding(r, jobs) for r in bound_cases]
    bound_attempts = [concrete_attempt_binding(r, jobs) for r in bound_attempts]
    _require(
        len({r["id"] for r in bound_cases}) == len(bound_cases)
        and len({r["id"] for r in bound_attempts}) == len(bound_attempts),
        "duplicate original case/group binding",
    )
    _require(
        {r["id"] for r in bound_cases} <= set(cases)
        and {r["id"] for r in bound_attempts} <= attempts,
        "unknown original pilot case/group binding",
    )
    plans = (
        {}
        if expected_plan is None
        else {p["id"]: concrete_original_n_plan(p, jobs) for p in expected_plan["case_plan"]}
    )
    case_results = []
    attempt_results = []
    attempt_plans = (
        {}
        if expected_plan is None
        else {p["id"]: concrete_original_n_plan(p, jobs) for p in expected_plan["attempt_plan"]}
    )
    for binding in bound_cases:
        identifier = binding["id"]
        jid = binding.get("job_id")
        if jid not in checks or jid not in jobs:
            issues.append(
                {
                    "id": identifier,
                    "reason": "bound required raw case unexecuted",
                    "status": "unclosed",
                }
            )
            continue
        try:
            job = jobs[jid]
            descriptor = cases[identifier]
            expected_operation = {
                "quote": "quotes",
                "state": "state",
                "cell": "paired_pnl",
                "fit": "tiny_fits",
            }[descriptor["kind"]]
            _require(
                job["operation"] == expected_operation
                or (descriptor["kind"] == "cell" and job["operation"] == "cell_pair"),
                "case typed source operation differs",
            )
            control = binding.get("control_job_ids", [])
            required = list(dict.fromkeys([jid, *control]))
            _require(
                all(i in checks and i in jobs for i in required),
                "bound original case control work unverified",
            )
            if any(
                jobs[i]["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap")
                for i in required
            ):
                n = plans.get(identifier, {}).get("original_n")
                _require(
                    checks[jid].get("original_n") == (37 if descriptor["kind"] == "quote" else n),
                    "capped case original denominator changed",
                )
                parents = _cap_scope_parents(
                    identifier, "case", required, jobs, checks, planned_jobs
                )
                parent = parents[0]
                row = project_cap(identifier, descriptor["gates"], parent, n)
                row.update(_all_cap_bindings(parents))
                row.update(
                    job_id=jid,
                    required_job_ids=required,
                    cap_parent_job_id=parent["id"],
                    execution_status=job["status"],
                    child_evidence_sha256=runner.payload_digest(job["raw"]),
                )
                case_results.append(row)
                continue
            _require(job["status"] == "executed", "case original attempt not completely executed")
            expected_operation = {
                "quote": "quotes",
                "state": "state",
                "cell": "paired_pnl",
                "fit": "tiny_fits",
            }[descriptor["kind"]]
            _require(
                job["operation"] == expected_operation
                or (descriptor["kind"] == "cell" and job["operation"] == "cell_pair"),
                "case typed source operation differs",
            )
            row = project_case(descriptor, checks[jid], job["raw"], plans.get(identifier, {}))
            row.update(
                job_id=jid,
                **({"required_job_ids": required} if control else {}),
                evidence_sha256=runner.payload_digest(job["raw"]),
                raw_check_sha256=runner.payload_digest(checks[jid]),
            )
            case_results.append(row)
        except (ValueError, KeyError, StopIteration) as error:
            issues.append(
                {"id": identifier, "reason": str(error), "status": "unclosed_semantic_case"}
            )
    cost_check = None
    if expected_plan is not None:
        try:
            cost_check = check_raw_costs(snapshot, expected_plan)
        except ValueError as error:
            issues.append({"id": "costs", "reason": str(error), "status": "unclosed_costs"})
    computed_context = dict(context or {})
    computed_context["cost_check"] = cost_check or {}
    computed_context["saved_replay_complete"] = list(checks) if len(checks) == len(jobs) else None
    if expected_plan is not None:
        for key in ("domain_plan", "q_state_plan"):
            computed_context[key] = expected_plan.get(key)
    for binding in bound_attempts:
        identifier = binding["id"]
        try:
            numerical_job_ids = binding.get("job_ids", [])
            job_ids = list(dict.fromkeys(numerical_job_ids + binding.get("control_job_ids", [])))
            capped = [
                i
                for i in job_ids
                if i in checks
                and jobs[i]["status"] in ("failed_at_declared_cap", "unexecuted_dependency_cap")
            ]
            if capped:
                _require(
                    all(i in checks and i in jobs for i in job_ids),
                    "unexecuted required work cannot be hidden by one job cap",
                )
                parents = _cap_scope_parents(
                    identifier, "attempt", job_ids, jobs, checks, planned_jobs
                )
                job = parents[0]
                row = project_cap(
                    identifier,
                    candidate["pilot_attempt_gates"][identifier],
                    job,
                    attempt_plans.get(identifier, {}).get(
                        "original_n", checks[capped[0]]["original_n"]
                    ),
                )
                row.update(_all_cap_bindings(parents))
                row.update(
                    required_job_ids=job_ids,
                    cap_parent_job_id=job["id"],
                    unexecuted_dependency_job_ids=[
                        i for i in job_ids if jobs[i]["status"] == "unexecuted_dependency_cap"
                    ],
                )

            else:
                row = project_attempt(
                    identifier, numerical_job_ids, jobs, checks, candidate, computed_context
                )
                row["required_job_ids"] = job_ids
            row["evidence_sha256"] = runner.payload_digest(
                [jobs[i]["raw"] for i in row["required_job_ids"]]
            )
            row["raw_original_n_by_job"] = {
                i: jobs[i]["raw"].get("original_n") for i in row["required_job_ids"]
            }
            attempt_results.append(row)
        except (ValueError, KeyError, StopIteration) as error:
            issues.append(
                {"id": identifier, "reason": str(error), "status": "unclosed_semantic_obligation"}
            )
    missing_cases = sorted(set(cases) - {r["id"] for r in case_results})
    missing_attempts = sorted(attempts - {r["id"] for r in attempt_results})
    planned_missing = sorted(set(planned_jobs) - set(jobs))
    source_verified = False
    if expected_plan is not None and context is not None and "inputs" in context:
        from run_pilot import _locked_bindings

        actual = _locked_bindings(
            context["inputs"], expected_plan, context.get("source_root", ROOT)
        )
        runner._same(actual, snapshot["source"], "saved pilot actual source")
        source_verified = True
    else:
        issues.append(
            {
                "id": "source_and_inputs",
                "reason": "actual source/input context not supplied",
                "status": "unclosed_provenance",
            }
        )
    closed = (
        not missing_cases
        and not missing_attempts
        and not planned_missing
        and not issues
        and source_verified
    )
    qualified = closed and all(
        r["financial_qualification"] == "qualified" for r in case_results + attempt_results
    )
    receipt = None
    if closed:
        receipt = {
            "checker": "saved check_pilot raw semantic boundary",
            "integrity": "pass",
            "evidence_sha256": runner.payload_digest(snapshot),
            "inputs": {
                "plan_sha256": runner.payload_digest(expected_plan),
                "source_sha256": runner.payload_digest(snapshot["source"]),
                "case_results_sha256": runner.payload_digest(case_results),
                "attempt_results_sha256": runner.payload_digest(attempt_results),
            },
            "scope": "saved arrays/counts/blocks/cash/refinements/costs; original RNG and earlier solves require independent review",
        }
    return {
        "closed": closed,
        "financial_qualification": "qualified" if qualified else "unknown",
        "verification": receipt,
        "case_results": case_results,
        "attempt_results": attempt_results,
        "raw_checks": checks,
        "costs": cost_check,
        "issues": issues,
        "missing_cases": missing_cases,
        "missing_attempts": missing_attempts,
        "missing_jobs": planned_missing,
        "raw_snapshot": snapshot,
        "scope": "saved_full_original_pilot_semantic_boundary",
        "unverified": [
            "earlier_source_solver_and_RNG_correctness",
            "independent_execution_review",
            "financial_pilot_approval",
            "main_freeze",
        ],
    }


def check_pilot(directory, *, expected_plan, source_root=ROOT, context=None):
    """Load saved checkpoint parts only; no financial solver or RNG regeneration."""
    from run_pilot import bound_artifact_path, read_pilot_artifact

    directory = Path(directory)
    candidates = sorted(directory.glob("checkpoint*"))
    _require(bool(candidates), "no saved pilot checkpoint")
    snapshot, _ = read_pilot_artifact(candidates[-1])
    artifact_context = {
        "original_root": snapshot["artifact_directory"],
        "restored_root": str(directory.resolve()),
    }
    hydrated = []
    for reference in snapshot["jobs"]:
        row, _ = read_pilot_artifact(
            bound_artifact_path(reference["artifact_path"], artifact_context)
        )
        _require(
            runner.payload_digest(row) == reference["raw_job_payload_sha256"],
            "immutable original job payload differs from checkpoint",
        )
        hydrated.append(row)
    snapshot["jobs"] = hydrated
    context = dict(context or {}, source_root=source_root, artifact_context=artifact_context)
    result = check_pilot_records(snapshot, expected_plan=expected_plan, context=context)
    result["source_root"] = str(source_root)
    return result


def main(argv=None):
    import argparse

    from run_pilot import read_pilot_artifact, unpack_inputs, write_pilot_artifact

    parser = argparse.ArgumentParser(
        description="Saved-only original pilot checker; no financial RNG or solves."
    )
    parser.add_argument("--pilot", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    plan, _ = read_pilot_artifact(args.plan)
    context, _ = read_pilot_artifact(args.context)
    result = check_pilot(args.pilot, expected_plan=plan, context=unpack_inputs(context))
    write_pilot_artifact(args.output, result)
    print(
        {
            key: result[key]
            for key in ("closed", "financial_qualification", "missing_cases", "missing_attempts")
        }
    )
    return 0 if result["closed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
