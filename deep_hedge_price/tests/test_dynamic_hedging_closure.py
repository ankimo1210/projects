"""Full-count closure contracts; optimizer is supplied only in source-unit tests."""

import copy
import importlib
import importlib.util

import numpy as np
import pytest

from deep_hedge_price import _dynamic_hedging_policy as policy
from deep_hedge_price import _dynamic_hedging_protocol as protocol
from deep_hedge_price import _dynamic_hedging_study as study


def module():
    name = "deep_hedge_price._dynamic_hedging_closure"
    assert importlib.util.find_spec(name) is not None, "raw training/validation closure missing"
    return importlib.import_module(name)


def market(n, model):
    times = np.arange(13) / 12
    stock = np.broadcast_to(100 * np.exp(0.03 * times), (n, 13)).copy()
    prices = np.stack([stock, np.full_like(stock, 10.0)], axis=-1)
    memory = np.zeros_like(stock)
    memory[:, 1:] = np.cumsum(stock[:, 1:], axis=1)
    return {
        "times": times,
        "prices": prices,
        "memory_sum": memory,
        "memory_count": np.arange(13),
        "payoff": np.maximum(memory[:, -1] / 12 - 100, 0),
        "cashflows": np.zeros_like(prices),
        "premium": 5.0,
        "rate": 0.03,
        "cost_rates": np.array([0.0005, 0.005]),
        "original_n": n,
        "path_ids": np.arange(n),
        "model": model,
        "qualification": "qualified",
    }


def risk(n):
    return {
        "original_n": n,
        "times": np.arange(12) / 12,
        "models": {
            model: {
                "u1_target": np.zeros((n, 12)),
                "u2_target": np.zeros((n, 12, 2)),
                "arithmetic_valid": np.ones((n, 12), bool),
                "band_arithmetic_valid": np.ones((n, 12), bool),
                "qualification": np.full((n, 12), "qualified"),
                "band_qualification": np.full((n, 12), "qualified"),
                "price_covariance": np.broadcast_to(np.eye(2), (n, 12, 2, 2)).copy(),
            }
            for model in ("heston", "local")
        },
    }


def inputs():
    candidate = protocol.candidate_protocol()
    train = {m: market(8192, m) for m in ("Heston", "local")}
    valid = {m: market(2048, m) for m in ("Heston", "local")}
    risks = {m: risk(2048) for m in valid}
    streams = {
        role: {
            model: {
                "seed": candidate["seeds"][role][i],
                "global_driver_id": f"unit:{role}:{model}",
                "original_n": n,
            }
            for i, model in enumerate(("Heston", "local"))
        }
        for role, n in (("train", 8192), ("validation", 2048))
    }
    return dict(
        train_datasets=train,
        validation_datasets=valid,
        validation_risks=risks,
        stream_receipts=streams,
        candidate=candidate,
    )


def training_fixture(train, candidate):
    rows = []
    updates = candidate["training"]["updates"]
    batch_size = candidate["training"]["batch_size"]
    for slot in protocol.study_roster()["fits"]:
        data = train[slot["training_generator"]]
        scaler = policy._normalization(policy._dataset(data))
        weights = {
            "w1": np.zeros((9, 32)),
            "b1": np.zeros(32),
            "w2": np.zeros((32, 32)),
            "b2": np.zeros(32),
            "w3": np.zeros((32, 2)),
            "b3": np.zeros(2),
        }
        raw = {
            "status": "completed",
            "complete": True,
            "reason": None,
            "original_path_count": 8192,
            "universe": slot["universe"],
            "seed": slot["initialization"],
            "training_generator": slot["training_generator"],
            "fit_id": slot["id"],
            "checkpoint_id": "last_finite_completed",
            "weights": weights,
            "scaler": scaler,
            "requested_updates": updates,
            "updates": updates,
            "batch_size": batch_size,
            "learning_rate": candidate["training"]["learning_rate"],
            "device": "cpu",
            "dtype": "float64",
            "batch_seed_components": [slot["initialization"], 1937],
            "batch_indices": np.zeros((updates, batch_size), dtype=np.int32),
            "losses": np.ones(updates),
            "attempt_count": updates,
            "attempt_events": [{"attempt": i + 1, "status": "completed"} for i in range(updates)],
            "train_holdings": np.zeros((8192, 12, 2)),
            "train_discounted_pnl": 5 - np.exp(-0.03) * data["payoff"],
            "elapsed_seconds": 1.0,
            "cap_seconds": 300.0,
            "overrun_seconds": 0.0,
        }
        rows.append(
            {
                **slot,
                "status": "completed",
                "attempted": True,
                "original_n": 8192,
                "requested_updates": updates,
                "updates": updates,
                "raw_fit": raw,
                "reason": None,
                "checkpoint_id": "last_finite_completed",
                "elapsed_seconds": 1.0,
                "cap_seconds": 300.0,
                "overrun_seconds": 0.0,
                "validation_status": "not_run",
                "expense": {
                    "id": slot["id"],
                    "scope": "training",
                    "status": "completed",
                    "wall_seconds": 1.0,
                    "cpu_seconds": 0.5,
                    "includes_children": True,
                    "parent_id": None,
                    "reason": None,
                    "overrun_seconds": 0.0,
                },
            }
        )
    return {"fits": rows, "expenses": [r["expense"] for r in rows], "test_opened": False}


def supply_training(monkeypatch, args, mutate=None):
    training = training_fixture(args["train_datasets"], args["candidate"])
    if mutate is not None:
        mutate(training)
    monkeypatch.setattr(study, "fit_roster", lambda *a, **kw: copy.deepcopy(training))
    return training


def test_all_twelve_fixed_checkpoints_validate_original_paths_and_hand_cash(monkeypatch):
    api = module()
    args = inputs()
    original = supply_training(monkeypatch, args)
    out = api.training_validation_closure(**args)
    assert out["test_opened"] is False and out["closure_status"] == "closed"
    assert len(out["nn_validation"]) == 12 and len(out["baseline_validation"]) == 4
    assert len(out["closed_fits"]["fits"]) == 12
    for row in out["nn_validation"]:
        model = row["training_generator"]
        expected = np.exp(-0.03) * args["validation_datasets"][model]["payoff"] - 5
        assert row["result"]["loss"].shape == (2048,)
        assert row["result"]["loss"] == pytest.approx(expected, abs=2e-13)
        assert row["mse"] == pytest.approx(float(np.mean(expected**2)), abs=2e-12)
        assert row["status"] == "completed" and row["qualification"] == "qualified"
    assert all(r["validation_status"] == "not_run" for r in original["fits"])
    assert all(len(r["candidates"]) == 14 for r in out["baseline_validation"])
    expense_ids = {e["id"] for e in out["expenses"]}
    assert all("validation:" + r["id"] in expense_ids for r in original["fits"])


def test_finite_validation_with_unknown_market_never_selects_checkpoint(monkeypatch):
    api = module()
    args = inputs()
    original = supply_training(monkeypatch, args)
    args["validation_datasets"]["Heston"]["qualification"] = "unknown"
    out = api.training_validation_closure(**args)
    for row in out["nn_validation"]:
        if row["training_generator"] == "Heston":
            assert np.isfinite(row["result"]["loss"]).all()
            assert row["status"] == "failed" and row["mse"] is None
            assert row["result"]["qualified_path_mask"].shape == (2048,)
            assert not row["result"]["qualified_path_mask"].any()
    closed = {r["id"]: r for r in out["closed_fits"]["fits"]}
    for row in original["fits"]:
        fixed = closed[row["id"]]
        if row["training_generator"] == "Heston":
            assert fixed["failure_kind"] == "unqualified_validation"
            assert fixed["status"] == "failed" and fixed["checkpoint_id"] is None
            assert fixed["raw_fit"]["status"] == "completed"
    for row in out["baseline_validation"]:
        if row["generator"] == "Heston":
            assert row["selected_baseline"] is None
            assert all(v is None for v in row["selected_bands"].values())


def test_optimizer_error_is_retained_unclosed_instead_of_permitted_financial_failure(monkeypatch):
    api = module()
    args = inputs()

    def corrupt(training):
        row = training["fits"][0]
        row.update(status="failed", reason="optimizer defect", checkpoint_id=None)
        row["raw_fit"].update(
            status="optimizer_error",
            complete=False,
            reason="optimizer defect",
            checkpoint_id=None,
            updates=511,
        )

    supply_training(monkeypatch, args, corrupt)
    out = api.training_validation_closure(**args)
    assert out["closure_status"] == "unclosed"
    assert out["closed_fits"]["fits"][0]["failure_kind"] == "source_or_optimizer_defect"
    assert out["training"]["fits"][0]["raw_fit"]["reason"] == "optimizer defect"
    assert out["nn_validation"][0]["result"]["loss"].shape == (2048,)
    assert not np.isfinite(out["nn_validation"][0]["result"]["loss"]).any()


@pytest.mark.parametrize("field", ["seed", "global_driver_id", "original_n"])
def test_wrong_or_reused_stream_cannot_open_optimizer(monkeypatch, field):
    args = inputs()
    receipt = args["stream_receipts"]["validation"]["Heston"]
    if field == "global_driver_id":
        receipt[field] = args["stream_receipts"]["train"]["Heston"][field]
    else:
        receipt[field] += 1

    def forbidden(*args, **kwargs):
        pytest.fail("optimizer opened before stream/count validation")

    monkeypatch.setattr(study, "fit_roster", forbidden)
    with pytest.raises(ValueError):
        module().training_validation_closure(**args)


def test_completed_fit_cannot_use_validation_scaler(monkeypatch):
    args = inputs()
    data = args["validation_datasets"]["Heston"]
    data["prices"][:, :, 0] *= np.exp(0.1 * data["times"])
    data["memory_sum"][:, 1:] = np.cumsum(data["prices"][:, 1:, 0], axis=1)
    data["payoff"] = np.maximum(data["memory_sum"][:, -1] / 12 - 100, 0)

    def contaminate(training):
        training["fits"][0]["raw_fit"]["scaler"] = policy._normalization(
            policy._dataset(args["validation_datasets"]["Heston"])
        )

    supply_training(monkeypatch, args, contaminate)
    with pytest.raises(ValueError, match="training-only scaler"):
        module().training_validation_closure(**args)


@pytest.mark.parametrize("corruption", ["lost_slot", "batch_ids", "updates", "identity"])
def test_completed_fit_requires_original_identity_updates_and_batch_domain(monkeypatch, corruption):
    args = inputs()

    def corrupt(training):
        first = training["fits"][0]
        if corruption == "lost_slot":
            training["fits"].pop()
        elif corruption == "batch_ids":
            first["raw_fit"]["batch_indices"][0, 0] = 8192
        elif corruption == "updates":
            first["raw_fit"]["updates"] = 511
        else:
            first["raw_fit"]["seed"] = 29

    supply_training(monkeypatch, args, corrupt)
    with pytest.raises(ValueError):
        module().training_validation_closure(**args)


def test_saved_closure_replays_without_rng_training_or_teacher(monkeypatch):
    args = inputs()
    supply_training(monkeypatch, args)
    saved = module().training_validation_closure(**args)

    def forbidden(*a, **kw):
        pytest.fail("saved replay opened RNG/training")

    monkeypatch.setattr(study, "fit_roster", forbidden)
    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(np.random, "SeedSequence", forbidden)
    result = module().check_training_closure(saved, **args)
    assert result["integrity"] == "pass" and result["test_opened"] is False
    assert result["original_fit_slots"] == 12 and result["original_validation_n"] == 2048
    assert result["optimizer_history_authenticated"] is False


@pytest.mark.parametrize(
    "corruption", ["loss", "mask", "checkpoint", "baseline", "train_pnl", "expense"]
)
def test_saved_closure_tampering_cannot_reseal_numerical_selection(monkeypatch, corruption):
    args = inputs()
    supply_training(monkeypatch, args)
    saved = module().training_validation_closure(**args)
    if corruption == "loss":
        saved["nn_validation"][0]["result"]["loss"][0] += 0.5
    elif corruption == "mask":
        saved["nn_validation"][0]["result"]["qualified_path_mask"][0] = False
    elif corruption == "checkpoint":
        saved["closed_fits"]["fits"][0]["checkpoint_id"] = "best_validation"
    elif corruption == "baseline":
        saved["baseline_validation"][0]["selected_baseline"] = "band:local:width0.2"
    elif corruption == "train_pnl":
        saved["training"]["fits"][0]["raw_fit"]["train_discounted_pnl"][0] += 0.5
    else:
        saved["expenses"][0]["wall_seconds"] = 0.0
    with pytest.raises(ValueError):
        module().check_training_closure(saved, **args)


def test_legitimate_cap_failure_remains_full_n_unknown_with_raw_weights(monkeypatch):
    args = inputs()

    def cap(training):
        row = training["fits"][0]
        row.update(
            status="failed",
            reason="time cap",
            checkpoint_id=None,
            elapsed_seconds=300.1,
            overrun_seconds=0.1,
            updates=511,
        )
        row["raw_fit"].update(
            status="time_cap",
            complete=False,
            reason="time cap",
            checkpoint_id=None,
            elapsed_seconds=300.1,
            overrun_seconds=0.1,
            updates=511,
            attempt_count=511,
        )
        row["raw_fit"]["batch_indices"] = row["raw_fit"]["batch_indices"][:511]
        row["raw_fit"]["losses"] = row["raw_fit"]["losses"][:511]
        row["raw_fit"]["attempt_events"] = row["raw_fit"]["attempt_events"][:511]
        row["expense"].update(status="failed", reason="time cap", wall_seconds=300.1)

    supply_training(monkeypatch, args, cap)
    out = module().training_validation_closure(**args)
    assert out["closure_status"] == "closed"
    assert out["closed_fits"]["fits"][0]["failure_kind"] == "time_cap"
    assert out["training"]["fits"][0]["raw_fit"]["weights"]
    assert np.isnan(out["nn_validation"][0]["result"]["loss"]).all()
    assert out["nn_validation"][0]["original_n"] == 2048


@pytest.mark.parametrize("outer_status", ["completed", "failed"])
def test_connector_overrun_cannot_keep_completed_checkpoint(monkeypatch, outer_status):
    args = inputs()

    def overrun(training):
        row = training["fits"][0]
        row.update(status=outer_status, elapsed_seconds=300.1, overrun_seconds=0.1)
        if outer_status == "failed":
            row.update(checkpoint_id=None, reason="fit connector including setup exceeded cap")
        row["expense"].update(wall_seconds=300.1, overrun_seconds=0.1)

    supply_training(monkeypatch, args, overrun)
    out = module().training_validation_closure(**args)
    closed = out["closed_fits"]["fits"][0]
    assert out["closure_status"] == "closed"
    assert closed["status"] == "failed" and closed["failure_kind"] == "time_cap"
    assert closed["checkpoint_id"] is None
    assert out["training"]["fits"][0]["raw_fit"]["status"] == "completed"
    assert np.isnan(out["nn_validation"][0]["result"]["loss"]).all()


@pytest.mark.parametrize("field", ["rate", "cost_rates", "payoff", "memory_count", "premium"])
def test_changed_claim_fees_rate_or_shared_premium_rejected_before_fit(monkeypatch, field):
    args = inputs()
    data = args["validation_datasets"]["Heston"]
    if field in {"rate", "premium"}:
        data[field] += 0.1
    else:
        data[field] = np.asarray(data[field]).copy()
        data[field].flat[0] += 1

    def forbidden(*a, **kw):
        pytest.fail("optimizer opened with changed claim/fees/rate/premium")

    monkeypatch.setattr(study, "fit_roster", forbidden)
    with pytest.raises(ValueError):
        module().training_validation_closure(**args)


def test_missing_raw_fit_on_finite_input_is_unclosed_source_defect(monkeypatch):
    args = inputs()

    def defect(training):
        row = training["fits"][0]
        row.update(
            status="failed",
            reason="ValueError: wrong architecture",
            raw_fit=None,
            updates=0,
            checkpoint_id=None,
        )
        row["expense"].update(status="failed", reason=row["reason"])

    supply_training(monkeypatch, args, defect)
    out = module().training_validation_closure(**args)
    assert out["closure_status"] == "unclosed"
    assert out["closed_fits"]["fits"][0]["failure_kind"] == "source_or_optimizer_defect"


def test_nonfinite_training_market_is_explicit_failed_attempt_not_optimizer_defect(monkeypatch):
    args = inputs()

    def invalid(training):
        for row in training["fits"]:
            if row["training_generator"] == "Heston":
                row.update(
                    status="failed",
                    reason="nonfinite training price",
                    raw_fit=None,
                    updates=0,
                    checkpoint_id=None,
                )
                row["expense"].update(status="failed", reason=row["reason"])

    supply_training(monkeypatch, args, invalid)
    data = args["train_datasets"]["Heston"]
    data["prices"][0, 2, 0] = np.nan
    data["memory_sum"][:, 1:] = np.cumsum(data["prices"][:, 1:, 0], axis=1)
    data["payoff"] = np.maximum(data["memory_sum"][:, -1] / 12 - 100, 0)
    data["qualification"] = "unknown"
    out = module().training_validation_closure(**args)
    assert out["closure_status"] == "closed"
    assert all(
        r["failure_kind"] == "unqualified_training_data"
        for r in out["closed_fits"]["fits"]
        if r["training_generator"] == "Heston"
    )


@pytest.mark.parametrize(
    "field", ["weights_extra", "weights_shape", "learning_rate", "device", "dtype"]
)
def test_checkpoint_architecture_and_declared_training_config_must_match(monkeypatch, field):
    args = inputs()

    def corrupt(training):
        raw = training["fits"][0]["raw_fit"]
        if field == "weights_extra":
            raw["weights"]["unused"] = np.zeros(1)
        elif field == "weights_shape":
            raw["weights"]["w1"] = np.zeros((9, 31))
        elif field == "learning_rate":
            raw[field] = 0.01
        else:
            raw[field] = "wrong"

    supply_training(monkeypatch, args, corrupt)
    with pytest.raises(ValueError):
        module().training_validation_closure(**args)


def test_arithmetic_replay_cannot_certify_financial_precision_when_baselines_unknown(monkeypatch):
    args = inputs()
    supply_training(monkeypatch, args)
    for risk_data in args["validation_risks"].values():
        for row in risk_data["models"].values():
            row["qualification"][:] = "unknown"
            row["band_qualification"][:] = "unknown"
    saved = module().training_validation_closure(**args)
    assert all(r["status"] == "completed" for r in saved["nn_validation"])
    assert all(r["selected_baseline"] is None for r in saved["baseline_validation"])
    result = module().check_training_closure(saved, **args)
    assert result["qualification"] == "unknown"
    assert result["nn_validation_qualification"] == "qualified"
    assert result["baseline_validation_qualification"] == "unknown"


@pytest.mark.parametrize("field", ["missing_time", "raw_time", "cap", "overrun"])
def test_missing_or_contradictory_measured_cost_cannot_close_fit(monkeypatch, field):
    args = inputs()

    def corrupt(training):
        row = training["fits"][0]
        if field == "missing_time":
            row["elapsed_seconds"] = np.nan
        elif field == "raw_time":
            row["raw_fit"]["elapsed_seconds"] = 2.0
        elif field == "cap":
            row["cap_seconds"] = 600.0
        else:
            row["overrun_seconds"] = 1.0

    supply_training(monkeypatch, args, corrupt)
    with pytest.raises(ValueError):
        module().training_validation_closure(**args)
