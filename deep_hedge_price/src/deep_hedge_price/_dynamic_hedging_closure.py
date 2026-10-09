"""Private original-roster training and validation closure for dynamic hedging.

This producer never opens test streams or certifies financial precision. It
retains optimizer failures, all original paths and fixed last checkpoints.
Saved numerical replay can check final policies and selections, but cannot
authenticate earlier optimizer iterations or random-stream provenance.
"""

import copy

import numpy as np

from . import _dynamic_hedging_protocol as protocol
from . import _dynamic_hedging_study as study

_MODELS = ("Heston", "local")
# Deterministic protocol/seed declarations are snapshotted before any work.
_ORIGINAL_CANDIDATE = protocol.candidate_protocol()
_ALLOWED_FAILURES = {"time_cap", "nonfinite", "unqualified_training_data", "unqualified_validation"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _inputs(train, validation, risks, streams, candidate):
    _require(candidate == _ORIGINAL_CANDIDATE, "unchanged original financial candidate required")
    _require(
        set(train) == set(validation) == set(risks) == set(_MODELS),
        "both original generators required",
    )
    _require(
        set(streams) == {"train", "validation"}, "only reserved train/validation streams required"
    )
    identities = []
    shared_premium = train["Heston"].get("premium")
    _require(np.isfinite(shared_premium), "shared finite preselected premium required")
    times = np.arange(13) / 12
    for role, datasets, n in (
        ("train", train, candidate["training"]["original_n"]),
        ("validation", validation, candidate["validation"]["original_n"]),
    ):
        _require(set(streams[role]) == set(_MODELS), "both reserved model streams required")
        for i, model in enumerate(_MODELS):
            data, receipt = datasets[model], streams[role][model]
            recorded, prices, _, _ = study._dataset_shape(data)
            _require(
                len(prices) == n and data.get("original_n") == n,
                "original path count cannot be reduced",
            )
            _require(np.array_equal(recorded, times), "original monthly dates required")
            _require(
                data.get("model", "").lower() == model.lower(), "market generator identity differs"
            )
            _require(data.get("rate") == candidate["market"]["rate"], "fixed market rate required")
            _require(
                np.array_equal(data["cost_rates"], candidate["hedging"]["half_spreads"]),
                "fixed half spreads required",
            )
            _require(
                data.get("premium") == shared_premium, "one shared preselected premium required"
            )
            _require(
                np.array_equal(
                    np.broadcast_to(np.asarray(data["memory_count"]), (n, 13)),
                    np.broadcast_to(np.arange(13), (n, 13)),
                ),
                "original monthly fixing count required",
            )
            memory = np.zeros((n, 13))
            memory[:, 1:] = np.cumsum(prices[:, 1:, 0], axis=1)
            _require(
                np.allclose(data["memory_sum"], memory, rtol=2e-10, atol=2e-11, equal_nan=True),
                "original monthly fixing memory differs",
            )
            expected_payoff = np.maximum(memory[:, -1] / 12 - candidate["claim"]["strike"], 0.0)
            _require(
                np.allclose(
                    data["payoff"], expected_payoff, rtol=2e-10, atol=2e-11, equal_nan=True
                ),
                "original Asian claim payoff differs",
            )
            _require(
                np.array_equal(data.get("path_ids"), np.arange(n)), "all original path IDs required"
            )
            _require(
                receipt.get("seed") == candidate["seeds"][role][i], "reserved stream seed differs"
            )
            _require(receipt.get("original_n") == n, "stream original path count differs")
            identity = receipt.get("global_driver_id")
            _require(isinstance(identity, str) and bool(identity), "missing global driver identity")
            identities.append(identity)
    _require(len(set(identities)) == 4, "train/validation global streams must be disjoint")
    return candidate


def _timing(record, cap):
    elapsed = record.get("elapsed_seconds")
    _require(
        isinstance(elapsed, (int, float, np.integer, np.floating))
        and np.isfinite(elapsed)
        and elapsed >= 0,
        "measured finite fit time required",
    )
    _same(record.get("cap_seconds"), cap, "original fit cap")
    _same(record.get("overrun_seconds"), max(0.0, elapsed - cap), "actual fit overrun")
    return elapsed


def _fit_rows(training, candidate):
    slots = protocol.study_roster()["fits"]
    rows = training.get("fits", [])
    _require(training.get("test_opened") is False, "training cannot open test streams")
    _require(
        len(rows) == 12 and {r["id"] for r in rows} == {r["id"] for r in slots},
        "all twelve original fit slots required",
    )
    by_id = {row["id"]: row for row in rows}
    for slot in slots:
        row = by_id[slot["id"]]
        _timing(row, candidate["training"]["cap_seconds"])
        _require(
            all(row.get(k) == v for k, v in slot.items()) and row.get("attempted") is True,
            "original fit slot must be attempted",
        )
        _require(
            row.get("original_n") == candidate["training"]["original_n"]
            and row.get("requested_updates") == candidate["training"]["updates"],
            "original training denominator and updates required",
        )
    return [by_id[slot["id"]] for slot in slots]


def _failure(row, data, candidate):
    raw = row.get("raw_fit")
    cap = candidate["training"]["cap_seconds"]
    elapsed = row.get("elapsed_seconds", np.nan)
    if not isinstance(raw, dict):
        # Only directly visible invalid market numbers establish this kind.
        # Missing fields, shapes and arbitrary input-validation exceptions
        # are source/contract defects rather than financial observations.
        arrays = [data[k] for k in ("prices", "memory_sum", "payoff", "cashflows")]
        numeric_failure = any(
            not np.isfinite(np.asarray(value, dtype=float)).all() for value in arrays
        )
        prices = np.asarray(data["prices"])
        numeric_failure |= bool(np.any(prices[..., 0] <= 0) or np.any(prices[..., 1] < 0))
        return "unqualified_training_data" if numeric_failure else "source_or_optimizer_defect"
    if raw.get("status") == "optimizer_error":
        return "source_or_optimizer_defect"
    if raw.get("status") == "time_cap" or elapsed > cap:
        return (
            "time_cap" if np.isfinite(elapsed) and elapsed >= cap else "source_or_optimizer_defect"
        )
    if raw.get("status") in {"nonfinite_loss", "nonfinite_gradient", "nonfinite_parameters"}:
        return "nonfinite"
    if (
        row.get("status") != "completed"
        or raw.get("status") != "completed"
        or raw.get("complete") is not True
    ):
        return "source_or_optimizer_defect"
    if data.get("qualification") != "qualified":
        return "unqualified_training_data"
    return None


def _expense(identifier, scope, result, status, reason):
    measurement = copy.deepcopy(result["expense"])
    measurement.update(id=identifier, scope=scope, status=status, reason=reason, parent_id=None)
    return measurement


def _validate_nn(row, dataset, training_data, candidate):
    reason = _failure(row, training_data, candidate)
    raw = row.get("raw_fit")
    # A completed checkpoint can be replayed diagnostically even when the
    # market precision is unknown. An incomplete optimizer cannot be rescued.
    completed = (
        row.get("status") == "completed"
        and isinstance(raw, dict)
        and raw.get("status") == "completed"
        and raw.get("complete") is True
        and reason not in {"time_cap", "source_or_optimizer_defect"}
    )
    if completed:
        result = study.policy_rollout(dataset, None, universe=row["universe"], policy="nn", fit=raw)
    else:
        result = study._unknown_rollout(dataset, row.get("reason") or "original fit incomplete")
    with np.errstate(over="ignore", invalid="ignore"):
        raw_mse = float(np.mean(np.asarray(result["loss"]) ** 2))
    qualified = (
        reason is None
        and result["status"] == "completed"
        and np.asarray(result["qualified_path_mask"]).all()
        and np.isfinite(raw_mse)
    )
    if not qualified and reason is None:
        reason = "unqualified_validation"
    if completed and reason == "unqualified_training_data":
        result["raw_validation_qualified_path_mask"] = result["qualified_path_mask"].copy()
        result["qualified_path_mask"][:] = False
        result.update(status="unknown", reason="training market precision not qualified")
    validation = {key: row[key] for key in ("training_generator", "universe", "initialization")}
    validation.update(
        id="validation:" + row["id"],
        fit_id=row["id"],
        original_n=len(dataset["prices"]),
        status="completed" if qualified else "failed",
        qualification="qualified" if qualified else "unknown",
        mse=raw_mse if qualified else None,
        raw_mse=raw_mse,
        reason=None if qualified else (result.get("reason") or row.get("reason") or reason),
        result=result,
    )
    validation["expense"] = _expense(
        validation["id"],
        "fixed_checkpoint_validation",
        result,
        validation["status"],
        validation["reason"],
    )
    closed = copy.deepcopy(row)
    closed.update(
        validation_original_n=validation["original_n"],
        validation_status=validation["status"],
        selection_status=validation["status"],
        qualification=validation["qualification"],
    )
    if not qualified:
        closed.update(
            status="failed",
            failure_kind=reason,
            checkpoint_id=None,
            reason=validation["reason"] or reason,
        )
    return validation, closed


def training_validation_closure(
    *, train_datasets, validation_datasets, validation_risks, stream_receipts, candidate
) -> dict:
    """Attempt all twelve original fits and close fixed-checkpoint validation.

    Original v1 counts (8192 train, 2048 validation, 512 updates), seeds and
    twelve initialization slots are required. Training-only scalers are made
    by the original optimizer. Four strong-baseline selections retain all
    fourteen original candidates. Finite losses with unknown qualification
    cannot select a checkpoint or fallback baseline. Source/optimizer defects
    remain unclosed, whereas genuine financial/cap failures remain explicit.
    Stream receipts bind declared identity, not actual RNG authenticity.
    """
    train, validation, risks, streams, candidate = copy.deepcopy(
        (train_datasets, validation_datasets, validation_risks, stream_receipts, candidate)
    )
    _inputs(train, validation, risks, streams, candidate)
    training = study.fit_roster(train, candidate=candidate)
    _audit_training(training, train, candidate)
    return _assemble(training, train, validation, risks, streams, candidate)


def _assemble(training, train, validation, risks, streams, candidate):
    rows = _fit_rows(training, candidate)
    nn_rows, closed, baselines, raw_validation = [], [], [], {}
    expenses = copy.deepcopy(training["expenses"])
    for row in rows:
        model = row["training_generator"]
        nn, fixed = _validate_nn(row, validation[model], train[model], candidate)
        nn_rows.append(nn)
        closed.append(fixed)
        expenses.append(nn["expense"])
    for model in _MODELS:
        for universe in candidate["universes"]:
            selection = study.select_validation(
                validation[model],
                risks[model],
                generator=model,
                universe=universe,
                widths=candidate["hedging"]["band_width_candidates"],
            )
            for item in selection["candidates"]:
                item["qualification"] = "qualified" if item["status"] == "completed" else "unknown"
            baselines.append(selection)
            raw_validation[selection["id"]] = {
                "losses": {k: v["loss"].copy() for k, v in selection["rollouts"].items()},
                "qualifications": {
                    k: v["qualified_path_mask"].copy() for k, v in selection["rollouts"].items()
                },
            }
            expenses.append(
                _expense(
                    selection["id"],
                    "baseline_validation_and_selection",
                    selection,
                    selection["status"],
                    selection["reason"],
                )
            )
    closed_status = all(
        row.get("failure_kind") in _ALLOWED_FAILURES
        for row in closed
        if row["status"] != "completed"
    )
    return {
        "schema": "rb-f04-training-validation-raw-v1",
        "candidate": candidate,
        "stream_receipts": streams,
        "training": training,
        "nn_validation": nn_rows,
        "baseline_validation": baselines,
        "raw_validation": raw_validation,
        "closed_fits": {"fits": closed, "original_fit_slots": 12, "test_opened": False},
        "expenses": expenses,
        "closure_status": "closed" if closed_status else "unclosed",
        "test_opened": False,
        "verification_scope": "raw fixed checkpoints and original validation; optimizer history not authenticated",
    }


def _same(actual, expected, name):
    if isinstance(expected, dict):
        _require(
            isinstance(actual, dict) and set(actual) == set(expected), f"{name}: fields differ"
        )
        for key in expected:
            if key != "expense":
                _same(actual[key], expected[key], f"{name}.{key}")
    elif isinstance(expected, (list, tuple)):
        _require(
            isinstance(actual, (list, tuple)) and len(actual) == len(expected),
            f"{name}: rows differ",
        )
        for i, (a, e) in enumerate(zip(actual, expected, strict=True)):
            _same(a, e, f"{name}[{i}]")
    elif isinstance(expected, np.ndarray):
        a, e = np.asarray(actual), expected
        _require(a.shape == e.shape, f"{name}: original axes differ")
        if np.issubdtype(e.dtype, np.number):
            _require(
                np.allclose(a, e, rtol=2e-10, atol=2e-11, equal_nan=True), f"{name}: numbers differ"
            )
        else:
            _require(np.array_equal(a, e), f"{name}: identities/masks differ")
    elif isinstance(expected, (float, np.floating)):
        _require(
            np.isclose(actual, expected, rtol=2e-10, atol=2e-11, equal_nan=True),
            f"{name}: number differs",
        )
    else:
        _require(actual == expected, f"{name}: value differs")


def _audit_training(training, train, candidate):
    from . import _dynamic_hedging_policy as policy

    config = candidate["training"]
    rows = _fit_rows(training, candidate)
    for row in rows:
        raw = row.get("raw_fit")
        if raw is None:
            continue
        _require(isinstance(raw, dict), "raw fit must retain its attempted record")
        raw_elapsed = _timing(raw, config["cap_seconds"])
        _require(
            raw_elapsed <= row["elapsed_seconds"] + 2e-10,
            "raw fit time exceeds inclusive connector time",
        )
        if raw.get("status") == "optimizer_error":
            # Retain the complete defect as unclosed, even if progress fields
            # are contradictory. It cannot be a financial/cap failure.
            continue
        identity = {
            "original_path_count": config["original_n"],
            "universe": row["universe"],
            "seed": row["initialization"],
            "training_generator": row["training_generator"],
            "fit_id": row["id"],
            "requested_updates": config["updates"],
            "batch_size": config["batch_size"],
            "batch_seed_components": [row["initialization"], 1937],
            "cap_seconds": config["cap_seconds"],
            "learning_rate": config["learning_rate"],
            "device": config["device"],
            "dtype": config["dtype"],
        }
        for key, value in identity.items():
            _same(raw.get(key), value, f"raw fit identity.{key}")
        updates, attempts = raw.get("updates"), raw.get("attempt_count")
        _require(
            isinstance(updates, int)
            and isinstance(attempts, int)
            and 0 <= updates <= attempts <= config["updates"],
            "invalid original update/attempt count",
        )
        batch = np.asarray(raw.get("batch_indices"))
        _require(
            batch.shape == (attempts, config["batch_size"])
            and np.issubdtype(batch.dtype, np.integer)
            and np.all((batch >= 0) & (batch < config["original_n"])),
            "batch IDs outside original training paths",
        )
        events = raw.get("attempt_events", [])
        losses = np.asarray(raw.get("losses"))
        _require(
            len(events) == attempts and losses.shape == (attempts,),
            "original optimizer attempts lost",
        )
        _require(
            [e.get("attempt") for e in events] == list(range(1, attempts + 1)),
            "optimizer attempt IDs differ",
        )
        completed = row.get("status") == "completed"
        if completed:
            shapes = {
                "w1": (9, 32),
                "b1": (32,),
                "w2": (32, 32),
                "b2": (32,),
                "w3": (32, 2),
                "b3": (2,),
            }
            weights = raw.get("weights", {})
            _require(set(weights) == set(shapes), "fixed checkpoint weight keys differ")
            for key, shape in shapes.items():
                value = np.asarray(weights[key])
                _require(
                    value.shape == shape and np.isfinite(value).all(),
                    "fixed checkpoint weight shape/values differ",
                )
            _require(
                raw.get("status") == "completed"
                and raw.get("complete") is True
                and row.get("updates") == updates == config["updates"]
                and attempts == updates
                and all(e.get("status") == "completed" for e in events)
                and np.isfinite(losses).all(),
                "completed optimizer did not finish original updates",
            )
            _require(
                row.get("checkpoint_id")
                == raw.get("checkpoint_id")
                == candidate["hedging"]["checkpoint_rule"],
                "fixed last checkpoint required",
            )
            expected = policy._normalization(policy._dataset(train[row["training_generator"]]))
            _same(raw.get("scaler"), expected, "training-only scaler")
            result = study.policy_rollout(
                train[row["training_generator"]],
                None,
                universe=row["universe"],
                policy="nn",
                fit=raw,
            )
            _same(
                raw.get("train_holdings"), result["holdings"], "last checkpoint training holdings"
            )
            _same(
                raw.get("train_discounted_pnl"),
                result["discounted_pnl"],
                "last checkpoint training cash",
            )


def _audit_costs(saved):
    expected = list(saved["training"]["expenses"])
    for row in saved["nn_validation"]:
        expected.append(
            _expense(
                row["id"],
                "fixed_checkpoint_validation",
                row["result"],
                row["status"],
                row["reason"],
            )
        )
    for row in saved["baseline_validation"]:
        expected.append(
            _expense(
                row["id"], "baseline_validation_and_selection", row, row["status"], row["reason"]
            )
        )
    _same(saved["expenses"], expected, "original expense ledger")
    # _same deliberately ignores nested expense for financial replay, but
    # these are direct cost records and every measurement is checked here.
    for actual, original in zip(saved["expenses"], expected, strict=True):
        _same(actual, original, "original expense row")
        _require(
            actual["parent_id"] is None and actual["includes_children"] is True,
            "inclusive root costs must be charged once",
        )
        for key in ("wall_seconds", "cpu_seconds"):
            _require(np.isfinite(actual[key]) and actual[key] >= 0, "cost measurement missing")
    _require(
        len(saved["expenses"]) == 28 and len({e["id"] for e in saved["expenses"]}) == 28,
        "all original cost IDs required",
    )
    by_id = {e["id"]: e for e in saved["expenses"]}
    for row in saved["training"]["fits"]:
        _same(by_id[row["id"]]["wall_seconds"], row["elapsed_seconds"], "training wall time")
        _same(row["expense"], by_id[row["id"]], "training inclusive expense")


def check_training_closure(
    saved, *, train_datasets, validation_datasets, validation_risks, stream_receipts, candidate
) -> dict:
    """Replay fixed policies/cash and every original validation selection.

    No RNG, teacher, fit or optimizer is opened. Final training holdings and
    discounted cash are independently recalculated with NumPy from saved
    weights and training-only scales. All twelve NN and four fourteen-candidate
    baseline validations use original 2048 paths. Array comparisons have
    numerical tolerances. Recorded timings are cross-bound to raw attempt
    expenses; external byte/source authentication remains caller-owned.
    Earlier optimizer history and actual RNG provenance are not authenticated.
    """
    saved, train, validation, risks, streams, candidate = copy.deepcopy(
        (saved, train_datasets, validation_datasets, validation_risks, stream_receipts, candidate)
    )
    _inputs(train, validation, risks, streams, candidate)
    _same(saved["candidate"], candidate, "saved candidate")
    _same(saved["stream_receipts"], streams, "saved stream binding")
    _audit_training(saved["training"], train, candidate)
    expected = _assemble(saved["training"], train, validation, risks, streams, candidate)
    for key in (
        "schema",
        "nn_validation",
        "baseline_validation",
        "raw_validation",
        "closed_fits",
        "closure_status",
        "test_opened",
    ):
        _same(saved[key], expected[key], f"saved closure.{key}")
    _audit_costs(saved)
    return {
        "integrity": "pass",
        "closure_status": expected["closure_status"],
        "original_fit_slots": 12,
        "original_validation_n": candidate["validation"]["original_n"],
        "test_opened": False,
        "optimizer_history_authenticated": False,
        "random_stream_provenance_authenticated": False,
        "qualification": "unknown",
        "nn_validation_qualification": "qualified"
        if all(row["status"] == "completed" for row in expected["nn_validation"])
        else "unknown",
        "baseline_validation_qualification": "qualified"
        if all(row["status"] == "completed" for row in expected["baseline_validation"])
        else "unknown",
        "verification_scope": "fixed checkpoint/scaler/cash/selection arithmetic and retained expenses",
    }
