"""Saved-only main SDE, quote, policy, cash, statistics and expense replay.

No RNG, teacher, CF/PDE or optimizer is called. Stored fine normals authorize
only deterministic SDE arithmetic; byte provenance is distinct from accuracy.
"""

from __future__ import annotations

from pathlib import Path
from time import perf_counter, process_time

import numpy as np
import run_main as main
import run_reference as runner

from deep_hedge_price import _dynamic_hedging_protocol as protocol
from deep_hedge_price import _dynamic_hedging_replay as replay
from deep_hedge_price import _dynamic_hedging_study as study


def same_finance(saved, recomputed, name):
    """Compare original arrays/statuses with tolerance, excluding live timings."""
    if isinstance(recomputed, main.pilot.LocalVarianceGrid):
        if not isinstance(saved, main.pilot.LocalVarianceGrid):
            raise ValueError(f"{name}: actual field type mismatch")
        same_finance(main.pilot.pack_inputs(saved), main.pilot.pack_inputs(recomputed), name)
    elif isinstance(recomputed, dict):
        if not isinstance(saved, dict) or saved.keys() != recomputed.keys():
            raise ValueError(f"{name}: saved keyset mismatch")
        for key in recomputed:
            if key != "expense":
                same_finance(saved[key], recomputed[key], f"{name}.{key}")
    elif isinstance(recomputed, (list, tuple)):
        if not isinstance(saved, (list, tuple)) or len(saved) != len(recomputed):
            raise ValueError(f"{name}: saved sequence mismatch")
        for i, (a, b) in enumerate(zip(saved, recomputed, strict=True)):
            same_finance(a, b, f"{name}[{i}]")
    else:
        runner._same(saved, recomputed, name)


def _clock_expense(identifier, scope, clock):
    main._require(
        set(clock) == {"wall_start", "wall_stop", "cpu_start", "cpu_stop"}
        and all(isinstance(x, (int, float)) and np.isfinite(x) and x >= 0 for x in clock.values())
        and clock["wall_stop"] >= clock["wall_start"]
        and clock["cpu_stop"] >= clock["cpu_start"],
        "saved actual clock timing boundary mismatch",
    )
    return main._expense(
        identifier,
        scope,
        clock["wall_stop"] - clock["wall_start"],
        clock["cpu_stop"] - clock["cpu_start"],
    )


def check_resume_work_record(record, directory, bindings):
    """Bind additional cost to original bytes and derive timings without finance/RNG."""
    main._require(
        record["kind"] == "additional_main_work"
        and isinstance(record["sequence"], int)
        and record["sequence"] > 0
        and record["id"] == f"resume:{record['sequence']:08d}"
        and record["scope"]
        in {
            "exact_job_load_and_binding",
            "dependency_load_and_binding",
            "evaluation_load_and_binding",
            "statistics_load_and_binding",
            "resumed_pretest_readiness",
            "completed_resume_readiness",
            "saved_main_check_receipt",
        },
        "typed additional work identity/scope mismatch",
    )
    runner._same(record["bindings"], bindings, "additional work original source/input binding")
    target = record["target"]
    saved, receipt = main.read_main_artifact(main.saved_path(directory, target["path"]))
    runner._same(target["receipt"], receipt, "additional work target bytes")
    main._require(
        target["payload_sha256"] == main.artifact_digest(saved),
        "additional work target payload binding mismatch",
    )
    if target["path"] == "statistics":
        costs, _ = main.read_main_artifact(Path(directory) / "statistics_costs")
        runner._same(costs["bindings"], bindings, "additional statistics target binding")
        runner._same(costs["receipt"], receipt, "additional statistics target receipt")
    else:
        target_bindings = saved.get("bindings", saved.get("identity", {}).get("bindings"))
        runner._same(target_bindings, bindings, "additional work target source/input binding")
    scope = record["scope"]
    path = Path(target["path"])
    main._require(
        (scope == "statistics_load_and_binding" and target["path"] == "statistics")
        or (scope == "resumed_pretest_readiness" and target["path"] == "pretest")
        or (scope == "completed_resume_readiness" and target["path"] == "main")
        or (
            scope
            in {
                "exact_job_load_and_binding",
                "dependency_load_and_binding",
                "evaluation_load_and_binding",
            }
            and path.parts[0] == "jobs"
        )
        or (scope == "saved_main_check_receipt" and saved.get("main_receipt") is not None),
        "additional work target scope binding mismatch",
    )
    if scope == "saved_main_check_receipt":
        _, original_receipt = main.read_main_artifact(Path(directory) / "main")
        runner._same(
            saved["main_receipt"], original_receipt, "posttest checker original main bytes"
        )
        main._require(
            len(record["observations"]) == 1, "actual saved checker cost observation required"
        )
        runner._same(
            saved["expense"],
            record["observations"][0]["observed"],
            "actual saved checker expense source binding",
        )
    rows = [_clock_expense(record["id"], record["scope"], record["clock"])]
    allowed = {
        "exact_job_load_and_binding": set(),
        "dependency_load_and_binding": {"replayed_dependency_inspection"},
        "evaluation_load_and_binding": {"replayed_evaluation"},
        "statistics_load_and_binding": {"replayed_statistics"},
        "resumed_pretest_readiness": {"main_input_load", "cold_imports"},
        "completed_resume_readiness": {"main_input_load", "cold_imports"},
        "saved_main_check_receipt": {"saved_main_check"},
    }[record["scope"]]
    for i, observation in enumerate(record["observations"]):
        scope, observed = observation["scope"], observation["observed"]
        main._require(scope in allowed, "additional work external timing scope mismatch")
        timing = observed.get("timing", observed)
        row = main._expense(
            f"{record['id']}:{scope}:{i}", scope, timing["wall_seconds"], timing["cpu_seconds"]
        )
        row["timing"]["overrun_seconds"] = timing.get("overrun_seconds", 0.0)
        rows.append(row)
    protocol.validate_expenses(rows, required_ids=[row["id"] for row in rows])
    return rows


def check_resume_costs(directory, bindings):
    """Reconstruct all append-only work and serialization receipts, retaining unknowns."""
    records, expenses, references = [], [], []
    for index, path in enumerate(main.resume_work_paths(directory), start=1):
        saved, receipt = main.read_main_artifact(path / "work")
        main._require(saved["sequence"] == index, "additional work inventory sequence mismatch")
        rows = check_resume_work_record(saved, directory, bindings)
        cost_path = path / "serialization"
        if cost_path.exists():
            cost, _ = main.read_main_artifact(cost_path)
            runner._same(
                cost["bindings"], bindings, "additional serialization source/input binding"
            )
            runner._same(cost["work_receipt"], receipt, "additional serialization work bytes")
            rows.append(
                _clock_expense(
                    f"{saved['id']}:serialization",
                    "additional_work_receipt_serialization",
                    cost["clock"],
                )
            )
            pending = main._pending_expense(
                f"{saved['id']}:measurement_receipt_write",
                "additional_work_final_measurement_receipt_write",
                "final receipt self-write and return metadata are outside its completed clock",
            )
            runner._same(
                cost["measurement_receipt_write"],
                pending,
                "additional final measurement unknown preserved",
            )
            rows.append(pending)
        else:
            rows.append(
                main._pending_expense(
                    f"{saved['id']}:serialization",
                    "interrupted_additional_work_receipt_serialization",
                    "additional serialization measurement interrupted before receipt",
                )
            )
        reference = {
            "path": str((path / "work").relative_to(directory)),
            "receipt": receipt,
            "payload_sha256": main.artifact_digest(saved),
        }
        references.append(reference)
        records.append(
            {
                "scope": saved["scope"],
                "target": saved["target"],
                "raw": saved,
                "expenses": rows,
                "reference": reference,
            }
        )
        expenses.extend(rows)
    accounting = protocol.validate_expenses(expenses, required_ids=[row["id"] for row in expenses])
    return {
        "records": records,
        "references": references,
        "expenses": expenses,
        "accounting": accounting,
    }


def check_market_job(record, parameters, surface):
    """Replay each adapted SDE level from stored fine normals and exact events."""
    main._require(record["kind"] == "main_market", "actual main market record required")
    n, fine_level = record["original_n"], record["fine_level"]
    main._require(np.array_equal(record["path_ids"], np.arange(n)), "original path order mismatch")
    stop, grouped = 0, {str(level): [] for level in record["levels"]}
    import hashlib

    full_digest = hashlib.sha256()

    for chunk in record["chunks"]:
        lo, hi = chunk["path_start"], chunk["path_stop"]
        main._require(lo == stop and lo < hi <= n, "original chunk path coverage mismatch")
        fine = np.asarray(chunk["fine_normals"])
        full_digest.update(fine.tobytes())
        main._require(
            fine.shape == (hi - lo, fine_level, 2)
            and fine.nbytes == chunk["normal_expanded_bytes"] <= 256 * 1024**2,
            "original normal chunk size/order mismatch",
        )
        main._require(
            hashlib.sha256(fine.tobytes()).hexdigest() == chunk["fine_sha256"],
            "stored fine normal binding mismatch",
        )
        main._require(
            chunk["path_steps"] == (hi - lo) * sum(record["levels"]),
            "original path-step accounting mismatch",
        )
        for level in record["levels"]:
            factor = fine_level // level
            normals = fine.reshape(hi - lo, level, factor, 2).sum(axis=2) / np.sqrt(factor)
            result = study.market_dataset(
                record["model"],
                parameters,
                surface,
                normals,
                np.arange(level + 1) / level,
                np.arange(record["frequency"] + 1) * (level // record["frequency"]),
                np.arange(1, 13) / 12,
                record["call_cache"],
                premium=record["premium"],
                cost_rates=record["cost_rates"],
            )
            result["path_ids"] = np.arange(lo, hi)
            result["primitives"].pop("normals")
            same_finance(chunk["datasets"][str(level)], result, "original market chunk")
            grouped[str(level)].append(result)
        stop = hi
    main._require(
        stop == record["processed_n"] and n - stop == record["unexecuted_n"],
        "original processed/unexecuted path denominator mismatch",
    )
    main._require(
        full_digest.hexdigest() == record["global_driver_id"],
        "global original driver binding mismatch",
    )
    if stop != n:
        main._require(
            record["status"] == "failed_at_declared_cap"
            and record["cap_evidence"]
            and record["datasets"] is None,
            "partial financial work needs original cap evidence",
        )
        return {
            "integrity": "pass",
            "original_n": n,
            "processed_n": stop,
            "qualification": "unknown",
            "rng_replayed": False,
        }
    main._require(record["status"] == "executed", "completed original market status mismatch")
    datasets = {key: main._merged_datasets(parts, n) for key, parts in grouped.items()}
    same_finance(record["datasets"], datasets, "original market/memory/quotes")
    for dataset in datasets.values():
        replay.check_market(
            dataset,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=record["call_cache"],
            generator=record["model"],
            latent_state=dataset["market"]["variance"] if record["model"] == "Heston" else None,
        )
    return {
        "integrity": "pass",
        "original_n": n,
        "processed_n": stop,
        "qualification": "unknown",
        "rng_replayed": False,
        "earlier_sde_replayed_from_saved_drivers": True,
        "boundary": "stored fine drivers/field/call tables to market/memory/actual quotes",
    }


def check_risk_job(record, parameters, surface, dataset, caches):
    """Recalculate only stored original path chunks; a partial risk stays unknown."""
    main._require(record["kind"] == "main_risk", "actual chunked main risk required")
    n, chunk_paths = dataset["original_n"], record["chunk_paths"]
    main._require(
        record["original_n"] == n and np.array_equal(record["path_ids"], np.arange(n)),
        "original risk path order/denominator mismatch",
    )
    main._require(
        isinstance(chunk_paths, int)
        and chunk_paths > 0
        and chunk_paths * 2 * (len(dataset["times"]) - 1) * 1024 * 8 <= 256 * 1024**2,
        "prior risk chunk budget mismatch",
    )
    stop, parts = 0, []
    for chunk in record["chunks"]:
        lo, hi = chunk["path_start"], chunk["path_stop"]
        main._require(
            lo == stop and hi == min(n, lo + chunk_paths),
            "original risk chunk path coverage mismatch",
        )
        recomputed = study.quote_risk_dataset(
            parameters, surface, main.slice_observable_dataset(dataset, lo, hi), caches
        )
        same_finance(chunk["risk"], recomputed, "original observable risk chunk")
        measured = main.chunk_payload_sizes(chunk["risk"])
        for key, value in measured.items():
            main._require(chunk[key] == value, "actual risk chunk byte accounting mismatch")
        main._require(
            measured["expanded_bytes"] <= 256 * 1024**2,
            "actual risk chunk expanded byte cap exceeded",
        )
        parts.append(recomputed)
        stop = hi
    main._require(
        stop == record["processed_n"] and n - stop == record["unexecuted_n"],
        "original risk processed/unexecuted denominator mismatch",
    )
    if record["status"] == "failed_at_declared_cap":
        evidence = record["cap_evidence"] or {}
        main._require(
            record["risk"] is None
            and record["financial_qualification"] == "unknown"
            and evidence.get("metric") == "wall_seconds"
            and evidence.get("limit", 0) > 0
            and evidence.get("consumed", -1) >= evidence["limit"]
            and evidence["consumed"] <= record["expense"]["wall_seconds"] + 2e-8,
            "partial original risk cap evidence mismatch",
        )
        return {
            "integrity": "pass",
            "original_n": n,
            "processed_n": stop,
            "qualification": "unknown",
            "risk": None,
        }
    main._require(
        record["status"] == "executed" and stop == n and record["phase"] == "complete",
        "unclosed or incomplete original risk source",
    )
    scope = record.get("retain_full_merged", True)
    main._require(isinstance(scope, bool), "explicit merged risk scope required")
    merge = main._merged_risks if scope else main._policy_risks
    risk = merge(parts, n)
    risk["empty_claim"] = main.empty_claim_diagnostics(dataset)
    same_finance(record["risk"], risk, "all original merged quote risk/empty claim cash")
    return {
        "integrity": "pass",
        "original_n": n,
        "processed_n": stop,
        "qualification": "unknown",
        "risk": risk,
    }


def _load_jobs(snapshot, directory):
    return main._ReferenceJobs(snapshot["jobs"], directory=directory)


def check_score_refinement(record):
    """Recompute independent empirical envelopes from raw loss/mask changes."""
    names = (
        "base_baseline_loss",
        "base_candidate_loss",
        "refined_baseline_loss",
        "refined_candidate_loss",
        "base_baseline_mask",
        "base_candidate_mask",
        "refined_baseline_mask",
        "refined_candidate_mask",
    )
    producers = record.get("producer_evidence")
    if producers is not None and producers.get("kind") == "typed_cell_pairs":
        expected = main.score_refinement_from_cell_pairs(
            baseline_records=producers["baseline_records"],
            candidate_records=producers["candidate_records"],
            original_n=record["original_n_per_seed"],
            group=record["group"],
            comparison_id=record["comparison_id"],
        )
    elif producers is not None:
        expected = main.score_refinement_from_rollouts(
            base_records=producers["base_records"],
            refined_records=producers["refined_records"],
            original_n=record["original_n_per_seed"],
            group=record["group"],
            comparison_id=record["comparison_id"],
        )
    else:
        expected = main.score_refinement(
            *(record[name] for name in names),
            original_n=record["original_n_per_seed"],
            group=record["group"],
            comparison_id=record["comparison_id"],
        )
    same_finance(record, expected, "saved independent paired-score envelope")
    return expected


def check_empty_claim_job(record):
    """Replay delegated zero-claim cash and retain its measured current expense."""
    from check_pilot import check_empty_claim_record

    main._require(
        set(record)
        == {"kind", "Q", "rows", "original_n", "path_ids", "financial_qualification", "expense"}
        and record["kind"] == "empty_claim",
        "original empty claim raw/worker expense required",
    )
    main.validate_empty_claim_q(record["Q"])
    expense = record["expense"]
    main._require(
        isinstance(expense, dict)
        and expense.get("id") == "empty_claim_worker"
        and expense.get("scope") == "original_zero_claim_unit_call_cash"
        and expense.get("status") == "complete",
        "actual current empty claim worker expense required",
    )
    timing, events = expense.get("timing", {}), expense.get("timing_events", {})
    for axis, key in (("wall", "wall_seconds"), ("cpu", "cpu_seconds")):
        elapsed, start, stop = (
            timing.get(key),
            events.get(axis + "_start"),
            events.get(axis + "_stop"),
        )
        main._require(
            all(value is not None and np.isfinite(value) for value in (elapsed, start, stop))
            and elapsed >= 0
            and stop >= start
            and np.isclose(elapsed, stop - start, rtol=1e-9, atol=2e-8),
            "actual empty claim worker timing/clock differs",
        )
    return check_empty_claim_record({k: v for k, v in record.items() if k != "expense"})


def check_refinement_binding(saved, args):
    """Tie real saved producers to the original resolved plan, source and inputs."""
    main._require(
        saved["identity"]["argument_identity"] == main.pilot.input_identity(args),
        "original resolved refinement argument binding differs",
    )
    operation, kwargs, raw = args["operation"], args["arguments"], saved["raw"]
    if operation in ("paired_score_refinement", "paired_score_cell_refinement"):
        keys = (
            ("baseline_records", "candidate_records")
            if operation.endswith("cell_refinement")
            else ("base_records", "refined_records")
        )
        for key in keys:
            same_finance(
                raw["producer_evidence"][key], kwargs[key], "original actual score producer binding"
            )
    elif operation == "empty_claim":
        same_finance(raw["Q"], kwargs["q_record"], "original empty claim actual Q producer binding")
    elif operation == "cell_pair":
        same_finance(
            raw["selection_inputs"],
            {k: kwargs[k] for k in ("identity", "validation", "fits")},
            "original actual typed selection producer binding",
        )
        for key in (
            "base_dataset",
            "refined_dataset",
            "base_risk",
            "refined_risk",
            "base_risk_source",
            "refined_risk_source",
            "shared_market",
            "refinement_kind",
        ):
            same_finance(raw[key], kwargs.get(key), "original actual typed producer binding")
        same_finance(
            raw["dataset_indices"],
            list(kwargs.get("dataset_indices", (0, 1))),
            "original typed dataset producer binding",
        )
    elif operation == "paired_pnl":
        for prefix in ("base", "refined"):
            for key in ("dataset", "risk"):
                same_finance(
                    raw[f"{prefix}_{key}"],
                    kwargs[prefix].get(key),
                    "original paired financial producer binding",
                )
            same_finance(
                raw[f"{prefix}_arguments"],
                {k: v for k, v in kwargs[prefix].items() if k not in ("dataset", "risk")},
                "original paired policy/fit producer binding",
            )
        for key in ("base_risk_source", "refined_risk_source", "shared_market"):
            same_finance(raw[key], kwargs.get(key), "original paired risk/driver producer binding")
    if "arguments" in raw:
        expected = dict(kwargs)
        if operation in (
            "frequency_market",
            "market_pair",
            "quote_risk",
            "teacher",
            "teacher_grid",
            "bump_risk",
            "Q",
            "oracle",
            "call_table",
        ):
            expected["wall_cap_seconds"] = saved["identity"]["plan"]["budget"]["wall_seconds"]
        expected = main.pilot.pack_inputs(expected)
        same_finance(raw["arguments"], expected, "original wrapped refinement input binding")


def check_evaluation_metadata(saved, identifier):
    """Check outer labels before the numerical result enters any statistic."""
    main._require(
        saved["identity"]["id"] == identifier, "original evaluation metadata identity mismatch"
    )
    main.check_evaluation_row_metadata(saved["raw"], identifier)


def check_main(directory, *, inputs, source_root=main.ROOT, save_receipt=None):
    """Recompute full original main financial boundaries from immutable saved jobs."""
    start, cpu = perf_counter(), process_time()
    directory = Path(directory)
    snapshot, receipt = main.read_main_artifact(directory / "main")
    main._require(snapshot["schema"] == main.SCHEMA, "main raw schema mismatch")
    plan = snapshot["plan"]
    _, bindings, _, _ = main._pretest(inputs, plan, source_root)
    runner._same(snapshot["bindings"], bindings, "main source/input/freeze binding")
    jobs = _load_jobs(snapshot, directory)
    pretest, _ = main.read_main_artifact(directory / "pretest")
    runner._same(pretest["bindings"], bindings, "saved pretest source/inputs binding")
    parameters, surface = main._parameters(inputs), main._surface(inputs)
    expected = set()
    market_checks = {}
    validations = {r["id"]: r for r in inputs["selection_receipts"]["validation"]}
    drivers = {}
    for identifier in jobs:
        saved = jobs[identifier]
        main.check_execution_status(saved, directory=directory)
        identity = saved["identity"]
        runner._same(identity["bindings"], bindings, "original main job source/input bindings")
        main._require(identity["id"] == identifier, "original main job identity mismatch")
        runner._same(
            identity["plan"], main._job_plan(plan, identifier), "original main job prior plan"
        )
    for model in main.MODELS:
        for slot, seed in enumerate(plan["test_seeds"]):
            market_id = f"market:{model}:seed{slot}"
            expected.add(market_id)
            market = jobs[market_id]["raw"]
            if slot in drivers:
                main._require(
                    all(
                        a == b
                        for a, b in zip(
                            drivers[slot],
                            [
                                (c["path_start"], c["path_stop"], c["fine_sha256"])
                                for c in market["chunks"]
                            ],
                            strict=False,
                        )
                    ),
                    "original cross-generator shared test driver mismatch",
                )
            drivers[slot] = [
                (c["path_start"], c["path_stop"], c["fine_sha256"]) for c in market["chunks"]
            ]
            main._require(
                market["model"] == model
                and market["seed"] == seed
                and market["original_n"] == plan["test_n"]
                and market["levels"] == [192, 384, 768]
                and market["frequency"] == 12,
                "main original market roster mismatch",
            )
            market_arguments = {
                "parameters": parameters,
                "surface": surface,
                "model": model,
                "seed": seed,
                "original_n": plan["test_n"],
                "chunk_paths": plan["chunk_paths"],
                "levels": plan["levels"],
                "frequency": 12,
                "call_cache": inputs["caches"][model.lower()]["call"],
                "premium": inputs["frozen"]["selection"]["premium"]["value"],
                "cost_rates": inputs["candidate"]["original_candidate"]["hedging"]["half_spreads"],
                "role": "test",
            }
            main._require(
                jobs[market_id]["identity"]["argument_identity"]
                == main.pilot.input_identity(market_arguments),
                "original main market argument binding differs",
            )
            same_finance(market["premium"], market_arguments["premium"], "original frozen premium")
            same_finance(
                market["cost_rates"], market_arguments["cost_rates"], "original actual fee rates"
            )
            runner._same(
                market["call_cache"],
                inputs["caches"][model.lower()]["call"],
                "frozen actual market call cache",
            )
            market_checks[market_id] = check_market_job(market, parameters, surface)
            for level in plan["levels"]:
                risk_id = f"risk:{model}:seed{slot}:level{level}"
                expected.add(risk_id)
                risk_saved = jobs[risk_id]
                risk_check = main.check_execution_status(risk_saved, directory=directory)
                if risk_saved["status"] == "unexecuted_dependency_cap":
                    main._require(
                        risk_saved["raw"]["original_n"] == plan["test_n"],
                        "original unexecuted risk N differs",
                    )
                    main._require(
                        [r["id"] for r in risk_saved["raw"]["dependency_references"]]
                        == [market_id],
                        "original risk cap dependency differs",
                    )
                    dataset = risk = None
                else:
                    dataset = market["datasets"][str(level)]
                    main._require(
                        risk_saved["identity"]["argument_identity"]
                        == main.pilot.input_identity(
                            {
                                "parameters": parameters,
                                "surface": surface,
                                "dataset": dataset,
                                "caches": inputs["caches"],
                                "chunk_paths": plan["chunk_paths"],
                                "retain_full_merged": False,
                            }
                        ),
                        "original main observable risk argument binding differs",
                    )
                    main._require(
                        risk_saved["raw"]["chunk_paths"] == plan["chunk_paths"],
                        "prior main risk chunk size mismatch",
                    )
                    risk = check_risk_job(
                        risk_saved["raw"], parameters, surface, dataset, inputs["caches"]
                    )["risk"]
                for universe in ("U1", "U2"):
                    identifier = f"evaluation:{model}:seed{slot}:level{level}:{universe}"
                    expected.add(identifier)
                    check_evaluation_metadata(jobs[identifier], identifier)
                    row = jobs[identifier]["raw"]
                    if not risk_check["qualified"]:
                        main._require(
                            jobs[identifier]["status"] == "unexecuted_dependency_cap",
                            "original unexecuted evaluation missing",
                        )
                        main._require(
                            [r["id"] for r in row["dependency_references"]] == [risk_id],
                            "original evaluation cap dependency differs",
                        )
                        reference = next(ref for ref in snapshot["jobs"] if ref["id"] == risk_id)
                        case = {
                            "generator": model,
                            "seed_slot": slot,
                            "level": level,
                            "execution_status": "unexecuted_dependency_cap",
                            "original_n": plan["test_n"],
                            "artifact_directory": str(directory),
                            "dependency_reference": reference,
                            "bindings": bindings,
                        }
                        result = main.dependency_cap_evaluation(case, universe, plan["test_n"])
                        same_finance(row["result"], result, "all original unexecuted policy slots")
                        continue
                    result = study.test_roster(
                        dataset,
                        risk,
                        inputs["closure"]["closed_fits"],
                        validations[f"selection:{model}:{universe}"],
                        generator=model,
                        universe=universe,
                    )
                    same_finance(row["result"], result, "saved original policy/actions/loss/masks")
                    for cell in row["result"]["cells"]:
                        replay.check_cash(dataset, cell["result"])
    for job in plan["refinement_jobs"]:
        expected.add(job["id"])
        from check_pilot import _raw_job_check

        saved = jobs[job["id"]]
        main.check_execution_status(saved, directory=directory)
        if saved["status"] == "unexecuted_dependency_cap":
            main._require(
                saved["raw"]["original_n"] == job["original_n"],
                "original unexecuted refinement N differs",
            )
            main._require(
                {r["id"] for r in saved["raw"]["dependency_references"]}
                == main.pilot._dependency_ids(job["arguments"]),
                "original declared refinement cap dependencies differ",
            )
            continue
        operation = saved["identity"]["operation"]
        main._require(operation == "refinement", "refinement identity mismatch")
        args = main.pilot._resolve(job["arguments"], inputs, jobs)
        check_refinement_binding(saved, args)
        main.check_refinement_outcome_raw(
            job, saved["raw"], plan, inputs["candidate"]["original_candidate"]
        )
        if args["operation"] == "frequency_market":
            check_market_job(saved["raw"], parameters, surface)
        elif args["operation"] in ("paired_score_refinement", "paired_score_cell_refinement"):
            main._require(saved["raw"].get("producer_evidence"), "actual rollout producer missing")
            check_score_refinement(saved["raw"])
        elif args["operation"] == "empty_claim":
            check_empty_claim_job(saved["raw"])
        else:
            if args["operation"] in ("paired_pnl", "cell_pair"):
                main.require_position_refinement(saved["raw"])
            _raw_job_check(
                {"operation": args["operation"], "raw": saved["raw"]},
                {"parameters": parameters, "surface": surface},
            )
    main._require(set(jobs) == expected, "all original main/refinement jobs required")
    statistics, stats_receipt = main.read_main_artifact(
        main.saved_path(directory, snapshot["statistics_path"])
    )
    runner._same(stats_receipt, snapshot["statistics_receipt"], "main statistics bytes")
    statistics_costs, _ = main.read_main_artifact(directory / "statistics_costs")
    runner._same(
        statistics_costs["bindings"], bindings, "statistics measurement source/input binding"
    )
    runner._same(statistics_costs["receipt"], stats_receipt, "statistics measurement bytes")
    runner._same(
        statistics_costs["expenses"], snapshot["expenses"], "original statistics expense history"
    )
    result = main.main_statistics(
        main.local_references(snapshot["jobs"], directory),
        inputs["selection_receipts"],
        statistics["bootstrap_indices"],
        main.numerical_envelopes(main.local_references(snapshot["jobs"], directory)),
        q_checks=main.q_qualification(main.local_references(snapshot["jobs"], directory)),
        job_checks=main.execution_checks(main.local_references(snapshot["jobs"], directory)),
    )
    same_finance(statistics, result, "main original paired/IUT statistics")
    main._require(
        snapshot["original_evaluation_records"] == result["original_records"] == 396,
        "original 396 evaluation denominator mismatch",
    )
    expenses = (
        main.history_expenses(plan["history"])
        + list(pretest["expenses"])
        + list(snapshot["expenses"])
    )
    pretest_cost, _ = main.read_main_artifact(directory / "costs" / "serialization_pretest")
    runner._same(pretest_cost["bindings"], bindings, "pretest serialization input/source binding")
    expenses.append(pretest_cost["expense"])
    for reference in snapshot["jobs"]:
        cost = main._read_cost(reference["serialization_cost"], directory=directory)
        runner._same(cost["bindings"], bindings, "original main serialization binding")
        main._require(
            cost["id"] == f"serialization:{reference['id']}",
            "original serialization expense identity mismatch",
        )
        expenses.append(cost["expense"])
    for identifier, job in jobs.items():
        if "expense" in job:
            row = job["expense"]
        else:
            raw = job["raw"]["result"]["expense"]
            row = main._expense(
                identifier, "fixed_main_policy_roster", raw["wall_seconds"], raw["cpu_seconds"]
            )
        expenses.append(row)
    final_cost, _ = main.read_main_artifact(directory / "main_serialization")
    runner._same(final_cost["bindings"], bindings, "main snapshot serialization binding")
    runner._same(final_cost["main_receipt"], receipt, "main snapshot serialization receipt binding")
    expenses.append(final_cost["expense"])
    required_ids = [row["id"] for row in main.history_expenses(plan["history"])]
    required_ids += [
        "cold_imports",
        "pretest_readiness",
        "main_input_load",
        "serialization:pretest",
        "main_statistics",
        "serialization:main_statistics",
        "serialization:main_snapshot",
    ]
    required_ids += list(expected) + [f"serialization:{identifier}" for identifier in expected]
    main._require(
        set(row["id"] for row in expenses) == set(required_ids),
        "complete original main cost keyset required",
    )
    additional = check_resume_costs(directory, bindings)
    original_refs = snapshot.get("resume_work", [])
    runner._same(
        original_refs,
        additional["references"][: len(original_refs)],
        "original main additional cost receipt prefix",
    )
    expenses.extend(additional["expenses"])
    required_ids.extend(row["id"] for row in additional["expenses"])
    accounting = protocol.validate_expenses(expenses, required_ids=required_ids)
    check_expense = main._expense(
        "saved_main_check",
        "saved_sde/quotes/cash/statistics/expenses",
        perf_counter() - start,
        process_time() - cpu,
    )
    checked = {
        "integrity": "pass",
        "receipt": receipt,
        "original_evaluation_records": 396,
        "original_test_n_per_seed": plan["test_n"],
        "market_checks": market_checks,
        "statistics": result,
        "expenses": accounting,
        "check_expense": check_expense,
        "additional_costs": additional["references"],
        "qualification": "unknown",
        "precision_selection": snapshot["precision_selection"],
        "verification_scope": "saved drivers/market/quotes/risk/policies/cash/masks/statistics/costs",
        "unverified": [
            "independent_financial_precision",
            "fresh_reserved_restart",
            "two_CAS_restores",
        ],
    }
    if save_receipt is not None:
        checked["check_cost_reference"] = save_checked_receipt(
            directory, save_receipt, checked, bindings, receipt
        )
    return checked


def save_checked_receipt(directory, path, checked, bindings, main_receipt):
    """Save a posttest checker receipt and its new expense, preserving old plans."""
    path, directory = Path(path), Path(directory)
    main._require(
        path.resolve().is_relative_to(directory.resolve()),
        "posttest check receipt must belong to this restored copy",
    )
    start, cpu = perf_counter(), process_time()
    payload = {
        "main_receipt": main_receipt,
        "bindings": bindings,
        "integrity": checked["integrity"],
        "verification_scope": checked["verification_scope"],
        "original_records": checked["original_evaluation_records"],
        "original_n": checked["original_test_n_per_seed"],
        "expense": checked["check_expense"],
        "qualification": "unknown",
        "costs": checked["expenses"],
        "additional_costs": checked.get("additional_costs", []),
    }
    receipt = main.write_main_artifact(path, payload)
    return main.save_resume_work(
        directory,
        "saved_main_check_receipt",
        {"path": str(path), "receipt": receipt, "payload_sha256": main.artifact_digest(payload)},
        bindings,
        start,
        cpu,
        observations=[{"scope": "saved_main_check", "observed": checked["check_expense"]}],
    )
