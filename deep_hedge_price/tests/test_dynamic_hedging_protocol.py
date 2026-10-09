"""Protocol contracts: original rosters, separation, evidence and byte replay."""

import copy
import hashlib
import importlib
import json

import numpy as np
import pytest


def protocol():
    """Lazy import makes the missing implementation an assertion in RED."""
    try:
        return importlib.import_module("deep_hedge_price._dynamic_hedging_protocol")
    except ModuleNotFoundError:
        pytest.fail("Task5 protocol component is not implemented")


def test_candidate_and_original_roster_keep_all_cross_model_slots():
    p = protocol()
    candidate = p.candidate_protocol()
    assert candidate["version"] == "rb-f04-dynamic-v1"
    assert candidate["claim"] == {
        "kind": "arithmetic_asian_call",
        "strike": 100.0,
        "expiry": 1.0,
        "quantity": 1.0,
        "fixing_times": [j / 12 for j in range(1, 13)],
    }
    assert candidate["market"]["generators"] == ["Heston", "local"]
    assert candidate["training"]["initializations"] == [11, 29, 47]
    assert candidate["training"]["original_n"] == 8192
    assert candidate["validation"]["original_n"] == 2048
    assert candidate["teacher"]["n_candidates"] == [1024, 4096, 16384, 65536]
    assert candidate["test"]["n_candidates"] == [8192, 16384, 32768]
    assert candidate["sde"]["main_levels"] == [192, 384, 768]
    roster = p.study_roster()
    assert len(roster["fits"]) == 12
    assert len({r["id"] for r in roster["fits"]}) == 12
    assert len(roster["primary_cells"]) == 44
    assert len({r["id"] for r in roster["primary_cells"]}) == 44
    for generator in ["Heston", "local"]:
        for universe in ["U1", "U2"]:
            cells = [
                r
                for r in roster["primary_cells"]
                if r["generator"] == generator and r["universe"] == universe
            ]
            assert [r["policy"] for r in cells].count("no_hedge") == 1
            assert [r["policy"] for r in cells].count("greek") == 2
            assert [r["policy"] for r in cells].count("band") == 2
            assert [r["policy"] for r in cells].count("nn") == 6
            assert {r["valuation"] for r in cells if r["policy"] == "greek"} == {"Heston", "local"}
            assert {r["training_generator"] for r in cells if r["policy"] == "nn"} == {
                "Heston",
                "local",
            }
    assert roster["dimensions"] == {"test_seed_slots": [0, 1, 2], "sde_levels": [192, 384, 768]}


def test_seeds_use_distinct_stable_namespaces_without_global_draws():
    p = protocol()
    before = np.random.get_state()
    first = p.main_seeds()
    second = p.main_seeds()
    after = np.random.get_state()
    assert first == second
    assert set(first) == {
        "train",
        "validation",
        "test",
        "teacher",
        "oracle",
        "bootstrap",
        "pilot",
        "premium",
        "refinement",
        "fresh",
        "optional_p",
    }
    assert len(first["train"]) == len(first["validation"]) == 2
    assert len(first["test"]) == len(first["oracle"]) == len(first["refinement"]) == 3
    flattened = [seed for seeds in first.values() for seed in seeds]
    assert len(set(flattened)) == len(flattened)
    assert before[0] == after[0] and np.array_equal(before[1], after[1])
    assert before[2:] == after[2:]
    first["test"][0] = -1
    assert p.main_seeds()["test"][0] >= 0


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def test_source_registry_hashes_only_existing_canonical_files(tmp_path):
    p = protocol()
    (tmp_path / "finance.py").write_bytes(b"actual source\n")
    registry = p.source_registry(tmp_path, ["finance.py"])
    assert registry == {"finance.py": hashlib.sha256(b"actual source\n").hexdigest()}
    for paths in [["missing.py"], ["../escape.py"], ["./finance.py"], ["finance.py", "finance.py"]]:
        with pytest.raises((ValueError, FileNotFoundError)):
            p.source_registry(tmp_path, paths)
    (tmp_path / "finance.py").write_bytes(b"changed source\n")
    assert p.source_registry(tmp_path, ["finance.py"]) != registry


def expense(identifier, wall, *, status="complete", parent=None, inclusive=False):
    return {
        "id": identifier,
        "scope": "pilot.teacher",
        "status": status,
        "parent_id": parent,
        "includes_children": inclusive,
        "timing": {
            "wall_seconds": wall,
            "cpu_seconds": wall,
            "overrun_seconds": None if wall is None else 0.0,
        },
        **({"reason": "reference failed"} if status == "failed" else {}),
    }


def test_expenses_retain_failed_pending_and_exclude_inclusive_descendant_charge():
    p = protocol()
    records = [
        expense("pilot", 10.0, inclusive=True),
        expense("failed", 4.0, status="failed", parent="pilot"),
        expense("reference", 2.0, parent="failed"),
        expense("main", None, status="pending"),
    ]
    got = p.validate_expenses(records, required_ids=["pilot", "failed", "reference", "main"])
    assert got["raw_records"] == records
    assert got["charged_ids"] == ["pilot", "main"]
    assert got["excluded_ids"] == ["failed", "reference"]
    assert got["raw_totals"]["wall_seconds"] is None
    assert got["charged_totals"]["wall_seconds"] is None
    assert got["raw_measured_subtotals"]["wall_seconds"] == 16.0
    assert got["charged_measured_subtotals"]["wall_seconds"] == 10.0
    assert got["unknown_ids"] == ["main"]
    records[0]["timing"]["wall_seconds"] = -8
    assert got["raw_records"][0]["timing"]["wall_seconds"] == 10.0


@pytest.mark.parametrize("invalid_inclusive", [-1, "false"])
def test_expenses_reject_nonboolean_inclusive_flag(invalid_inclusive):
    p = protocol()
    records = [
        expense("parent", 2.0, inclusive=invalid_inclusive),
        expense("child", 1.0, parent="parent"),
    ]
    with pytest.raises(ValueError, match="includes_children"):
        p.validate_expenses(records, required_ids=["parent", "child"])


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "negative", "key", "cycle", "pending", "reason"]
)
def test_expenses_reject_erasure_bad_timing_and_cyclic_parents(mutation):
    p = protocol()
    records = [expense("a", 2.0), expense("b", 1.0, parent="a", status="failed")]
    if mutation == "missing":
        records.pop()
    elif mutation == "duplicate":
        records[1]["id"] = "a"
    elif mutation == "negative":
        records[1]["timing"]["wall_seconds"] = -1.0
    elif mutation == "key":
        records[1]["timing"].pop("cpu_seconds")
    elif mutation == "cycle":
        records[0]["parent_id"] = "b"
    elif mutation == "pending":
        records[1]["status"] = "pending"
    elif mutation == "reason":
        records[1].pop("reason")
    with pytest.raises(ValueError):
        p.validate_expenses(records, required_ids=["a", "b"])


def test_artifact_round_trip_keeps_raw_nan_and_rng_state_without_overwrite(tmp_path):
    p = protocol()
    directory = tmp_path / "chunk"
    arrays = {"raw_loss": np.array([1.0, np.nan, -2.0]), "mask": np.array([True, False, True])}
    metadata = {
        "original_n": 3,
        "status": "unknown",
        "expenses": [expense("check", None, status="pending")],
    }
    before = np.random.get_state()
    receipt = p.write_artifact(directory, metadata=metadata, arrays=arrays)
    loaded, replay, observed = p.read_artifact(directory)
    after = np.random.get_state()
    assert loaded == metadata
    assert observed == receipt
    assert np.array_equal(replay["raw_loss"], arrays["raw_loss"], equal_nan=True)
    assert np.array_equal(replay["mask"], arrays["mask"])
    assert before[0] == after[0] and np.array_equal(before[1], after[1]) and before[2:] == after[2:]
    with pytest.raises(FileExistsError):
        p.write_artifact(directory, metadata=metadata, arrays=arrays)


@pytest.mark.parametrize("filename", ["metadata.json", "arrays.npz", "receipt.json"])
def test_artifact_read_rejects_changed_bytes(filename, tmp_path):
    p = protocol()
    p.write_artifact(
        tmp_path / "chunk", metadata={"original_n": 2}, arrays={"x": np.array([1.0, 2.0])}
    )
    path = tmp_path / "chunk" / filename
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        p.read_artifact(tmp_path / "chunk")


def test_artifact_refuses_object_arrays_and_oversize_uncompressed_chunk(tmp_path):
    p = protocol()
    with pytest.raises(ValueError, match="object"):
        p.write_artifact(
            tmp_path / "objects", metadata={}, arrays={"x": np.array([{}], dtype=object)}
        )
    # Broadcast view avoids a large allocated fixture, but its saved payload is
    # larger than the fixed 256 MiB limit and must be refused before saving.
    too_big = np.broadcast_to(np.array(0, dtype=np.uint8), (256 * 1024**2 + 1,))
    with pytest.raises(ValueError, match="256 MiB"):
        p.write_artifact(tmp_path / "oversize", metadata={}, arrays={"x": too_big})
    assert not (tmp_path / "objects").exists()
    assert not (tmp_path / "oversize").exists()


def verified(inputs):
    return {
        "checker": "synthetic_saved_fixture_checker",
        "evidence_sha256": "a" * 64,
        "inputs": inputs,
    }


def freeze_inputs():
    """Synthetic receipts exercise structure; they do not qualify a real pilot."""
    p = protocol()
    candidate = p.candidate_protocol()
    source = {"finance.py": "b" * 64}
    bindings = {"candidate": digest(candidate), "source": digest(source)}
    premium = {
        "value": 5.0,
        "se": 0.01,
        "scheme_error": 0.02,
        **{k: candidate["premium"][k] for k in ["original_n", "steps_per_year", "seed"]},
    }
    pilot = {
        "qualification": "qualified",
        "verification": verified(bindings),
        "original_counts": {
            "selected_states": 18,
            "initial_quotes": 37,
            "tiny_cells": 44,
            "tiny_fits": 4,
        },
        "measurements": {
            key: 0.0
            for key in candidate["gates"]
            if key not in ["mse_difference_absolute", "mse_difference_relative"]
        }
        | {"baseline_mse": 1.0, "mse_difference": 0.001},
        "teacher_n": {"Heston": 4096, "local": 1024},
        "teacher_grid": {"Heston": "high", "local": "coarse"},
        "test_precision": [
            {
                "original_n": 8192,
                "worst_mean_loss_se": 0.02,
                "worst_mse_se": 0.03,
                "baseline_mse": 1.0,
            },
            {
                "original_n": 16384,
                "worst_mean_loss_se": 0.008,
                "worst_mse_se": 0.015,
                "baseline_mse": 1.0,
            },
            {
                "original_n": 32768,
                "worst_mean_loss_se": 0.004,
                "worst_mse_se": 0.008,
                "baseline_mse": 1.0,
            },
        ],
        "premium": premium,
    }
    review = {
        "qualification": "qualified",
        "verification": verified(bindings | {"pilot": digest(pilot)}),
        "scopes": {"code": "approved", "math": "approved", "pilot": "approved"},
        "unresolved_issues": [],
    }
    selection = {
        "teacher_n": copy.deepcopy(pilot["teacher_n"]),
        "teacher_grid": copy.deepcopy(pilot["teacher_grid"]),
        "test_n": 16384,
        "premium": copy.deepcopy(premium),
        "band_width_candidates": [0.0, 0.01, 0.02, 0.05, 0.1, 0.2],
        "baseline_rule": "minimum_validation_discounted_pnl_mse",
        "checkpoint_rule": "last_finite_completed",
    }
    return candidate, source, pilot, review, selection


def test_freeze_detaches_and_digest_binds_every_component():
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    frozen = p.freeze_contract(candidate, source, pilot, review, selection)
    assert frozen["bindings"] == {
        "candidate": digest(candidate),
        "source": digest(source),
        "pilot": digest(pilot),
        "review": digest(review),
        "selection": digest(selection),
    }
    assert frozen["frozen_sha256"] == digest(
        {k: v for k, v in frozen.items() if k != "frozen_sha256"}
    )
    candidate["training"]["original_n"] = 1
    pilot["measurements"]["teacher_price_se"] = None
    selection["test_n"] = 32768
    assert frozen["candidate"]["training"]["original_n"] == 8192
    assert frozen["pilot"]["measurements"]["teacher_price_se"] == 0.0
    assert frozen["selection"]["test_n"] == 16384


@pytest.mark.parametrize(
    "change",
    [
        "flag_only",
        "unmeasured",
        "too_inaccurate",
        "wrong_count",
        "wrong_source",
        "review_flag",
        "review_pilot",
        "review_scope",
        "review_issues",
        "candidate",
        "teacher_n",
        "test_n",
        "premium",
        "widths",
    ],
)
def test_freeze_rejects_unqualified_or_unbound_evidence(change):
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    if change == "flag_only":
        pilot = {"qualification": "qualified"}
    elif change == "unmeasured":
        pilot["measurements"]["call_scaled_state_derivative_error"] = None
    elif change == "too_inaccurate":
        pilot["measurements"]["teacher_price_se"] = 0.04
    elif change == "wrong_count":
        pilot["original_counts"]["selected_states"] = 17
    elif change == "wrong_source":
        pilot["verification"]["inputs"]["source"] = "c" * 64
    elif change == "review_flag":
        review = {"qualification": "qualified"}
    elif change == "review_pilot":
        review["verification"]["inputs"]["pilot"] = "c" * 64
    elif change == "review_scope":
        review["scopes"]["math"] = "pending"
    elif change == "review_issues":
        review["unresolved_issues"] = ["unresolved denominator precision"]
    elif change == "candidate":
        candidate["gates"]["teacher_price_se"] = 1.0
    elif change == "teacher_n":
        selection["teacher_n"]["Heston"] = 65536
    elif change == "test_n":
        selection["test_n"] = 32768
    elif change == "premium":
        selection["premium"]["se"] = None
    elif change == "widths":
        selection["band_width_candidates"] = [0.0, 0.02]
    with pytest.raises(ValueError):
        p.freeze_contract(candidate, source, pilot, review, selection)


def main_selection_receipts(frozen):
    p = protocol()
    fit_rows = [
        {
            "id": fit["id"],
            "status": "completed",
            "attempted": True,
            "original_n": 8192,
            "requested_updates": 512,
            "updates": 512,
            "elapsed_seconds": 20.0,
            "selection_status": "completed",
            "validation_original_n": 2048,
            "checkpoint_id": "last_finite_completed",
        }
        for fit in p.study_roster()["fits"]
    ]
    validations = []
    for g in ["Heston", "local"]:
        for u in ["U1", "U2"]:
            candidates = []
            for m in ["Heston", "local"]:
                candidates.append(
                    {"id": f"greek:{m}", "original_n": 2048, "status": "completed", "mse": 1.0}
                )
                for w in [0.0, 0.01, 0.02, 0.05, 0.1, 0.2]:
                    candidates.append(
                        {
                            "id": f"band:{m}:width{w:g}",
                            "original_n": 2048,
                            "status": "completed",
                            "mse": 0.5 + w,
                        }
                    )
            validations.append(
                {
                    "id": f"selection:{g}:{u}",
                    "generator": g,
                    "universe": u,
                    "status": "completed",
                    "original_n": 2048,
                    "candidates": candidates,
                    "selected_bands": {
                        "Heston": "band:Heston:width0",
                        "local": "band:local:width0",
                    },
                    "selected_baseline": "band:Heston:width0",
                }
            )
    return {
        "verification": verified(
            {
                "frozen": frozen["frozen_sha256"],
                "candidate": frozen["bindings"]["candidate"],
                "source": frozen["bindings"]["source"],
            }
        ),
        "test_opened": False,
        "fits": fit_rows,
        "validation": validations,
    }


def test_main_readiness_retains_explicit_fit_failure_and_original_count():
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    frozen = p.freeze_contract(candidate, source, pilot, review, selection)
    receipts = main_selection_receipts(frozen)
    failed = receipts["fits"][0]
    failed.update(status="failed", selection_status="failed", updates=25, reason="nonfinite_loss")
    failed.pop("checkpoint_id")
    before = copy.deepcopy(receipts)
    assert p.assert_main_ready(frozen, candidate, source, receipts) is None
    assert receipts == before
    assert receipts["fits"][0]["status"] == "failed"
    assert receipts["fits"][0]["original_n"] == 8192


@pytest.mark.parametrize(
    "change",
    [
        "no_freeze",
        "source",
        "candidate",
        "frozen_tamper",
        "receipt_binding",
        "test_opened",
        "missing_fit",
        "duplicate_fit",
        "fit_n",
        "unattempted",
        "updates",
        "cap",
        "selection_pending",
        "missing_baseline",
        "missing_width",
        "validation_n",
        "wrong_best",
    ],
)
def test_main_readiness_rejects_missing_or_leaking_selection(change):
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    frozen = p.freeze_contract(candidate, source, pilot, review, selection)
    receipts = main_selection_receipts(frozen)
    if change == "no_freeze":
        frozen = {}
    elif change == "source":
        source["finance.py"] = "c" * 64
    elif change == "candidate":
        candidate["training"]["updates"] = 64
    elif change == "frozen_tamper":
        frozen["selection"]["test_n"] = 32768
    elif change == "receipt_binding":
        receipts["verification"]["inputs"]["frozen"] = "c" * 64
    elif change == "test_opened":
        receipts["test_opened"] = True
    elif change == "missing_fit":
        receipts["fits"].pop()
    elif change == "duplicate_fit":
        receipts["fits"][1] = copy.deepcopy(receipts["fits"][0])
    elif change == "fit_n":
        receipts["fits"][0]["original_n"] = 8191
    elif change == "unattempted":
        receipts["fits"][0]["attempted"] = False
    elif change == "updates":
        receipts["fits"][0]["updates"] = 511
    elif change == "cap":
        receipts["fits"][0]["elapsed_seconds"] = 300.01
    elif change == "selection_pending":
        receipts["fits"][0]["selection_status"] = "pending"
    elif change == "missing_baseline":
        receipts["validation"].pop()
    elif change == "missing_width":
        receipts["validation"][0]["candidates"].pop()
    elif change == "validation_n":
        receipts["validation"][0]["candidates"][0]["original_n"] = 2047
    elif change == "wrong_best":
        receipts["validation"][0]["selected_baseline"] = "greek:Heston"
    with pytest.raises(ValueError):
        p.assert_main_ready(frozen, candidate, source, receipts)


@pytest.mark.parametrize("extra_duplicate", ["fits", "validation"])
def test_main_readiness_rejects_extra_duplicate_attempts(extra_duplicate):
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    frozen = p.freeze_contract(candidate, source, pilot, review, selection)
    receipts = main_selection_receipts(frozen)
    receipts[extra_duplicate].append(copy.deepcopy(receipts[extra_duplicate][0]))
    with pytest.raises(ValueError):
        p.assert_main_ready(frozen, candidate, source, receipts)


def test_main_readiness_rejects_negative_failed_attempt_time():
    p = protocol()
    candidate, source, pilot, review, selection = freeze_inputs()
    frozen = p.freeze_contract(candidate, source, pilot, review, selection)
    receipts = main_selection_receipts(frozen)
    receipts["fits"][0].update(
        status="failed",
        selection_status="failed",
        reason="reference failed",
        elapsed_seconds=-1.0,
    )
    with pytest.raises(ValueError):
        p.assert_main_ready(frozen, candidate, source, receipts)
