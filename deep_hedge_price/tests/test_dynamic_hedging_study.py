"""Independent contracts for the observable dynamic study connector."""

import copy

import numpy as np
import pytest
from hullkit._heston_local_surface import HestonParameters

from deep_hedge_price import _dynamic_hedging_study as study
from deep_hedge_price._dynamic_hedging_protocol import candidate_protocol, study_roster


def parameters():
    return HestonParameters(
        spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.0, rho=-0.7
    )


class ConstantField:
    def evaluate(self, time, spot):
        spots = np.asarray(spot, float)
        return {
            "variance": np.full(spots.shape, 0.04),
            "status": np.full(spots.shape, "ok", dtype="<U16"),
        }


def call_cache(model, dates):
    spots = np.array([90.0, 100.0, 110.0, 120.0])
    states = (
        np.array([0.00001, 0.04, 0.1, 0.5])
        if model == "heston"
        else np.array([0.25, 1.0, 2.0, 4.0])
    )
    intercept, slope = (0.0, 5.0) if model == "heston" else (-0.3, 0.5)
    values = np.broadcast_to(
        0.2 * spots[None, :, None] - 10 + intercept + slope * states[None, None, :],
        (len(dates), len(spots), len(states)),
    ).copy()
    return {
        "model": model,
        "dates": dates.copy(),
        "spot_nodes": spots,
        "state_nodes": states,
        "values": values,
        "rate": 0.03,
        "dividend_yield": 0.0,
        "strike": 100.0,
        "maturity": 1.25,
        "price_error": 1e-8,
        "spot_derivative_error": 1e-8,
        "derivative_error": 1e-8,
        "reference_status": "measured",
    }


def asian_cache(model, dates):
    from hullkit._dynamic_hedging_surfaces import build_asian_cache

    states = (
        np.array([0.00001, 0.04, 0.1, 0.5])
        if model == "heston"
        else np.array([0.25, 1.0, 2.0, 4.0])
    )
    x = np.linspace(0, 24, 5)
    m = 12 - np.floor(dates * 12 + 1e-9)
    if model == "heston":
        f = 0.4 * m[:, None, None] + 0.1 * states[None, :, None] - 0.01 * x[None, None, :]
        axes = {"dates": dates, "state": states, "threshold": x}
    else:
        spots = np.array([90.0, 100.0, 110.0, 120.0])
        f = (
            0.4 * m[:, None, None, None]
            + 0.01 * np.log(states)[None, None, :, None]
            - 0.01 * x[None, None, None, :]
            + np.zeros((1, 4, 1, 1))
        )
        axes = {
            "dates": dates,
            "state": states,
            "threshold": x,
            "spot": spots,
            "t0_spot": np.array([99.5, 99.75, 100.0, 100.25, 100.5]),
        }
    block = np.broadcast_to(f[..., None, None], (*f.shape, 16, 3)).copy()
    delta = (np.arange(16) - 7.5) * 1e-4
    # Perturbation is a state derivative label as well as a price perturbation.
    perturb = states if model == "heston" else np.log(states)
    shape = (1, len(states), 1, 1, 1) if model == "heston" else (1, 1, len(states), 1, 1, 1)
    block += perturb.reshape(shape) * delta.reshape((1,) * f.ndim + (16, 1))
    data = {"parameters": parameters(), "N": 16, "f": f, "block_means": block}
    if model == "local":
        t0_f = (
            0.4 * m[0]
            + 0.01 * np.log(states)[None, :, None]
            - 0.01 * x[None, None, :]
            + np.zeros((5, 1, 1))
        )
        data["t0_f"] = t0_f
        data["t0_block_means"] = np.broadcast_to(t0_f[..., None, None], (*t0_f.shape, 16, 3)).copy()
        data["t0_block_means"] += (
            np.log(states)[None, :, None, None, None] * delta[None, None, None, :, None]
        )
    result = build_asian_cache(data, model=model, axes=axes)
    result["deterministic_error"] = {
        "value": 1e-8,
        "spot_derivative": 1e-8,
        "state_derivative": 1e-8,
    }
    return result


def setup(n=4, generator="heston"):
    times = np.linspace(0.0, 1.0, 13)
    normals = np.zeros((n, 12, 2))
    caches = {
        m: {"call": call_cache(m, times), "asian": asian_cache(m, times[:-1])}
        for m in ["heston", "local"]
    }
    data = study.market_dataset(
        generator,
        parameters(),
        ConstantField(),
        normals,
        times,
        np.arange(13),
        times[1:],
        caches[generator]["call"],
        premium=5.0,
        cost_rates=np.array([0.0005, 0.005]),
    )
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    return data, risk, caches


def hand_cash(data, holdings):
    times, prices = data["times"], data["prices"]
    cash = np.full(len(prices), data["premium"])
    old = np.zeros((len(prices), 2))
    cash_history = []
    costs = []
    for j, t in enumerate(times):
        if j:
            cash *= np.exp(data["rate"] * (t - times[j - 1]))
            cash += np.sum(old * data["cashflows"][:, j], axis=1)
        new = holdings[:, j] if j < len(times) - 1 else np.zeros_like(old)
        fee = np.sum(np.abs(new - old) * prices[:, j] * data["cost_rates"], axis=1)
        cash -= np.sum((new - old) * prices[:, j], axis=1) + fee
        if j == len(times) - 1:
            cash -= data["payoff"]
        cash_history.append(cash.copy())
        costs.append(fee)
        old = new
    return np.stack(cash_history, 1), np.stack(costs, 1)


@pytest.mark.parametrize("model", ["heston", "local"])
def test_market_memory_is_added_before_action_and_excludes_initial_spot(model):
    data, _, _ = setup(generator=model)
    assert data["prices"].shape == (4, 13, 2)
    expected = 100 * np.exp(0.01 * data["times"])
    assert data["prices"][0, :, 0] == pytest.approx(expected)
    assert data["memory_count"] == pytest.approx(np.arange(13))
    assert data["memory_sum"][0] == pytest.approx(np.r_[0, np.cumsum(expected[1:])])
    assert data["payoff"] == pytest.approx(max(expected[1:].mean() - 100, 0))
    assert data["original_n"] == 4


def test_market_rejects_date_alias_instead_of_interpolating():
    times = np.linspace(0, 1, 13)
    cache = call_cache("heston", times + 1e-8)
    with pytest.raises(ValueError, match="date"):
        study.market_dataset(
            "heston",
            parameters(),
            ConstantField(),
            np.zeros((4, 12, 2)),
            times,
            np.arange(13),
            times[1:],
            cache,
            premium=5,
            cost_rates=[0.0005, 0.005],
        )


def test_market_failed_path_retains_original_denominator():
    times = np.linspace(0, 1, 13)
    normals = np.zeros((4, 12, 2))
    normals[1, 5, 0] = np.nan
    data = study.market_dataset(
        "heston",
        parameters(),
        ConstantField(),
        normals,
        times,
        np.arange(13),
        times[1:],
        call_cache("heston", times),
        premium=5.0,
        cost_rates=[0.0005, 0.005],
    )
    assert data["original_n"] == 4
    assert not data["path_mask"][1]
    assert np.isnan(data["payoff"][1])
    assert data["market"]["reasons"][1] == "nonfinite_normal"


def test_quote_risk_uses_observables_and_not_latent_market_variance():
    data, risk, caches = setup()
    data["market"]["variance"][:] = 999
    changed = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    for m in ["heston", "local"]:
        assert changed["models"][m]["state"] == pytest.approx(risk["models"][m]["state"])
        assert changed["models"][m]["u2_target"] == pytest.approx(risk["models"][m]["u2_target"])
    assert risk["models"]["heston"]["state"] == pytest.approx(0.04)
    assert risk["models"]["local"]["state"] == pytest.approx(1.0)


def test_quote_risk_independent_recalibrated_spot_quote_bumps():
    data, risk, _ = setup()
    row = risk["models"]["heston"]
    s, t, a, n, q = (
        data["prices"][0, 3, 0],
        data["times"][3],
        data["memory_sum"][0, 3],
        data["memory_count"][3],
        data["prices"][0, 3, 1],
    )

    def value(stock, quote):
        v = (quote - 0.2 * stock + 10) / 5
        x = (1200 - a) / stock
        f = 0.4 * (12 - n) + 0.1 * v - 0.01 * x
        return np.exp(-0.03 * (1 - t)) * stock * f / 12

    dq, ds = 1e-4, 1e-3
    hq = (value(s, q + dq) - value(s, q - dq)) / (2 * dq)
    hs = (value(s + ds, q) - value(s - ds, q)) / (2 * ds)
    assert row["u2_target"][0, 3] == pytest.approx([hs, hq], abs=1e-9)
    # Explicit physical-v to log-v coordinate transformation leaves targets invariant.
    vs = row["asian_spot_derivative"][0, 3]
    vv = row["asian_state_derivative"][0, 3]
    cv = row["call_state_derivative"][0, 3]
    cs = row["call_spot_derivative"][0, 3]
    assert [vs - (vv * 0.04) / (cv * 0.04) * cs, (vv * 0.04) / (cv * 0.04)] == pytest.approx(
        [hs, hq], abs=1e-9
    )


def test_position_block_variance_is_joint_ift_propagation():
    data, risk, _ = setup()
    row = risk["models"]["heston"]
    s, t = data["prices"][0, 3, 0], data["times"][3]
    discount = np.exp(-0.03 * (1 - t))
    delta = (np.arange(16) - 7.5) * 1e-4
    vs_block = discount * (0.4 * 9 + (0.1 + delta) * 0.04) / 12
    vv_block = discount * s * (0.1 + delta) / 12
    positions = np.column_stack([vs_block - vv_block / 5 * 0.2, vv_block / 5])
    covariance = np.cov(positions, rowvar=False, ddof=1) / 16
    assert row["u2_block_positions"][0, 3] == pytest.approx(positions)
    assert row["u2_position_covariance"][0, 3] == pytest.approx(covariance)
    assert row["u2_position_se"][0, 3] == pytest.approx(np.sqrt(np.diag(covariance)))


@pytest.mark.parametrize(
    "missing", ["price_error", "spot_derivative_error", "derivative_error", "asian"]
)
def test_unmeasured_error_does_not_erase_arithmetic_but_is_unknown(missing):
    data, _, caches = setup()
    if missing == "asian":
        caches["heston"]["asian"].pop("deterministic_error")
    else:
        caches["heston"]["call"][missing] = np.nan
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    row = risk["models"]["heston"]
    assert np.isfinite(row["u2_target"]).all()
    assert np.all(row["qualification"] == "unknown")
    result = study.policy_rollout(data, risk, universe="U2", policy="greek", model="heston")
    assert result["status"] == "unknown"
    assert np.isfinite(result["discounted_pnl"]).all()


def test_quote_fit_intersects_support_and_does_not_mutate_cache():
    data, _, caches = setup()
    caches["heston"]["asian"]["state_nodes"] = np.array([0.1, 0.2, 0.3, 0.5])
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    row = risk["models"]["heston"]
    assert np.all(row["fit_status"] == "unknown")
    assert np.isnan(row["u2_target"]).all()
    assert "asian_state_bounds" not in caches["heston"]["call"]


@pytest.mark.parametrize("policy,width", [("none", 0.0), ("greek", 0.0), ("band", 0.02)])
@pytest.mark.parametrize("universe", ["U1", "U2"])
def test_rollout_independent_cash_all_initial_and_terminal_costs(policy, width, universe):
    data, risk, _ = setup()
    result = study.policy_rollout(
        data, risk, universe=universe, policy=policy, model="heston", width=width
    )
    expected_cash, expected_costs = hand_cash(data, result["holdings"])
    assert result["cash"] == pytest.approx(expected_cash)
    assert result["costs"] == pytest.approx(expected_costs)
    assert result["discounted_pnl"] == pytest.approx(expected_cash[:, -1] * np.exp(-0.03))
    assert result["discounted_gain_pnl"] == pytest.approx(result["discounted_pnl"], abs=1e-12)
    assert result["discounted_gross_pnl"] - result["discounted_pnl"] == pytest.approx(
        (expected_costs * np.exp(-0.03 * data["times"])).sum(axis=1)
    )
    if universe == "U1":
        assert result["holdings"][..., 1] == pytest.approx(0)


def test_failed_risk_remains_unknown_without_implicit_holding_fallback():
    data, risk, _ = setup()
    risk["models"]["heston"]["u2_target"][1, 4] = np.nan
    result = study.policy_rollout(
        data, risk, universe="U2", policy="band", model="heston", width=0.02
    )
    assert result["original_n"] == 4
    assert np.isnan(result["holdings"][1, 4:]).all()
    assert np.isnan(result["discounted_pnl"][1])
    assert result["status"] == "unknown"


def test_validation_keeps_fourteen_candidates_and_fixed_tie_order():
    data, risk, _ = setup()
    validation = study.select_validation(
        data, risk, generator="Heston", universe="U2", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
    )
    assert len(validation["candidates"]) == 14
    assert all(row["original_n"] == 4 for row in validation["candidates"])
    completed = [row for row in validation["candidates"] if row["status"] == "completed"]
    best = min(completed, key=lambda row: row["mse"])
    assert validation["selected_baseline"] == best["id"]
    for m in ["Heston", "local"]:
        assert validation["selected_bands"][m].startswith("band:" + m + ":width")


def test_all_failed_validation_does_not_select_zero_width_fallback():
    data, risk, _ = setup()
    for row in risk["models"].values():
        row["qualification"][:] = "unknown"
    validation = study.select_validation(
        data, risk, generator="Heston", universe="U2", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
    )
    assert validation["status"] == "failed"
    assert len(validation["candidates"]) == 14
    assert validation["selected_baseline"] is None
    assert validation["selected_bands"] == {"Heston": None, "local": None}
    assert all(row["reason"] for row in validation["candidates"])


def test_failed_training_dataset_still_has_all_twelve_original_attempt_slots():
    data, _, _ = setup()
    data["prices"][1, 2, 0] = np.nan
    candidate = candidate_protocol()
    candidate["training"]["original_n"] = 4
    result = study.fit_roster({"Heston": data, "local": data}, candidate=candidate)
    assert len(result["fits"]) == 12
    assert {row["id"] for row in result["fits"]} == {row["id"] for row in study_roster()["fits"]}
    assert all(row["status"] == "failed" and row["attempted"] for row in result["fits"])
    assert all(row["original_n"] == 4 and row["reason"] for row in result["fits"])
    assert all(row["elapsed_seconds"] >= 0 for row in result["fits"])


def test_tiny_real_training_roster_keeps_all_updates_and_rng_state():
    data, _, _ = setup()
    candidate = candidate_protocol()
    candidate["training"].update(original_n=4, updates=1, batch_size=4, cap_seconds=30)
    import torch

    old_np = np.random.get_state()
    old_torch = torch.get_rng_state().clone()
    local_data, _, _ = setup(generator="local")
    result = study.fit_roster({"Heston": data, "local": local_data}, candidate=candidate)
    assert len(result["fits"]) == 12
    assert all(row["status"] == "completed" for row in result["fits"])
    assert all(
        row["updates"] == 1 and row["raw_fit"]["batch_indices"].shape == (1, 4)
        for row in result["fits"]
    )
    assert np.array_equal(old_np[1], np.random.get_state()[1])
    assert torch.equal(old_torch, torch.get_rng_state())


def test_test_subroster_preserves_six_failed_nn_and_all_eleven_policy_ids():
    data, risk, _ = setup()
    fits = {
        "fits": [
            {
                "id": slot["id"],
                **slot,
                "status": "failed",
                "reason": "cap",
                "original_n": 4,
                "attempted": True,
            }
            for slot in study_roster()["fits"]
        ]
    }
    validation = study.select_validation(
        data, risk, generator="Heston", universe="U1", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
    )
    result = study.test_roster(data, risk, fits, validation, generator="Heston", universe="U1")
    assert len(result["cells"]) == 11
    assert {row["id"] for row in result["cells"]} == {
        row["id"]
        for row in study_roster()["primary_cells"]
        if row["generator"] == "Heston" and row["universe"] == "U1"
    }
    failed_nn = [row for row in result["cells"] if row["policy"] == "nn"]
    assert len(failed_nn) == 6
    assert all(
        row["status"] == "unknown" and np.isnan(row["result"]["discounted_pnl"]).all()
        for row in failed_nn
    )


def test_saved_rollout_creates_no_random_generator(monkeypatch):
    data, risk, _ = setup()

    def forbidden(*args, **kwargs):
        raise AssertionError("RNG forbidden in saved-only calculation")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(np.random, "seed", forbidden)
    result = study.policy_rollout(
        data, risk, universe="U2", policy="band", model="local", width=0.02
    )
    assert np.isfinite(result["discounted_pnl"]).all()


def test_linear_claim_exact_branch_has_zero_label_uncertainty():
    data, _, caches = setup()
    data["memory_sum"][:, 3] = 1300.0
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    for model in ["heston", "local"]:
        row = risk["models"][model]
        assert np.all(row["asian_status"][:, 3] == "not_required_linear_claim")
        assert row["asian_standard_errors"][:, 3] == pytest.approx(0)
        assert row["u2_position_se"][:, 3] == pytest.approx(0)
        assert np.all(row["qualification"][:, 3] == "qualified")


def test_no_hedge_raw_pnl_is_independent_of_untraded_call_price():
    data, risk, _ = setup()
    baseline = study.policy_rollout(data, risk, universe="U2", policy="none")
    data["prices"][1, 4, 1] = np.nan
    data["qualification"] = "unknown"
    changed = study.policy_rollout(data, risk, universe="U2", policy="none")
    assert changed["discounted_pnl"] == pytest.approx(baseline["discounted_pnl"])
    assert changed["status"] == "unknown"


def test_unknown_fit_retains_original_arrays_and_measured_replay_expense():
    data, risk, _ = setup()
    result = study.policy_rollout(
        data, risk, universe="U1", policy="nn", fit={"status": "time_cap", "complete": False}
    )
    assert result["original_n"] == 4
    assert result["expense"]["wall_seconds"] >= 0
    assert result["expense"]["cpu_seconds"] >= 0
    assert result["raw_fit"]["status"] == "time_cap"


def test_market_preserves_inputs_for_saved_earlier_sde_replay():
    data, _, _ = setup()
    assert data["primitives"]["normals"].shape == (4, 12, 2)
    assert data["primitives"]["calendar_times"] == pytest.approx(data["times"])
    assert data["primitives"]["record_indices"] == pytest.approx(np.arange(13))
    assert data["primitives"]["fixing_times"] == pytest.approx(data["times"][1:])


def test_linear_claim_does_not_require_an_unused_mc_cache_error():
    data, _, caches = setup()
    data["memory_sum"][:, 3] = 1300.0
    for pair in caches.values():
        pair["asian"].pop("deterministic_error")
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    for row in risk["models"].values():
        assert np.all(row["qualification"][:, 3] == "qualified")
        assert np.all(row["qualification"][:, 2] == "unknown")


def test_validation_tie_order_is_fixed_even_when_width_inputs_are_reversed():
    data, risk, _ = setup()
    for row in risk["models"].values():
        row["u2_target"][:] = 0.0
        row["u1_target"][:] = 0.0
    validation = study.select_validation(
        data, risk, generator="Heston", universe="U2", widths=[0.2, 0.1, 0.05, 0.02, 0.01, 0]
    )
    assert validation["selected_baseline"] == "greek:Heston"
    assert validation["selected_bands"] == {
        "Heston": "band:Heston:width0",
        "local": "band:local:width0",
    }


def test_validation_rejects_wrong_generator_annotation():
    data, risk, _ = setup()
    with pytest.raises(ValueError, match="generator"):
        study.select_validation(
            data, risk, generator="local", universe="U2", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
        )


def test_risk_rollout_rejects_another_time_grid_with_same_shape():
    data, risk, _ = setup()
    risk["times"] = risk["times"] + 0.001
    with pytest.raises(ValueError, match="date"):
        study.policy_rollout(data, risk, universe="U2", policy="greek", model="heston")


def test_validation_and_test_roster_have_measured_inclusive_expenses():
    data, risk, _ = setup()
    selection = study.select_validation(
        data, risk, generator="Heston", universe="U2", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
    )
    result = study.test_roster(
        data, risk, {"fits": []}, selection, generator="Heston", universe="U2"
    )
    for receipt in [selection, result]:
        assert receipt["expense"]["wall_seconds"] >= 0
        assert receipt["expense"]["cpu_seconds"] >= 0
        assert receipt["expense"]["includes_children"] is True
    assert all(row["result"]["expense"]["wall_seconds"] >= 0 for row in result["cells"])


def test_nn_rollout_numpy_actions_match_training_cash_and_fee_outputs():
    data, risk, _ = setup()
    from deep_hedge_price._dynamic_hedging_policy import fit_policy

    fit = fit_policy(
        data, universe="U2", seed=11, updates=1, batch_size=4, learning_rate=0.003, cap_seconds=30
    )
    replay = study.policy_rollout(data, risk, universe="U2", policy="nn", fit=fit)
    assert replay["holdings"] == pytest.approx(fit["train_holdings"], abs=1e-12)
    assert replay["discounted_pnl"] == pytest.approx(fit["train_discounted_pnl"], abs=1e-12)
    expected_cash, expected_costs = hand_cash(data, replay["holdings"])
    assert replay["cash"] == pytest.approx(expected_cash, abs=1e-12)
    assert replay["costs"] == pytest.approx(expected_costs, abs=1e-12)


def test_training_generator_mismatch_keeps_six_reasoned_failed_local_slots():
    data, _, _ = setup()
    candidate = candidate_protocol()
    candidate["training"].update(original_n=4, updates=1, batch_size=4, cap_seconds=30)
    fitted = study.fit_roster({"Heston": data, "local": data}, candidate=candidate)
    local_rows = [row for row in fitted["fits"] if row["training_generator"] == "local"]
    assert len(fitted["fits"]) == 12
    assert len(local_rows) == 6
    assert all(row["status"] == "failed" for row in local_rows)
    assert all(row["original_n"] == 4 and "generator" in row["reason"] for row in local_rows)
    assert all(row["raw_fit"] is None for row in local_rows)


@pytest.fixture(scope="module")
def tiny_identity_roster():
    data, risk, _ = setup()
    local_data, _, _ = setup(generator="local")
    candidate = candidate_protocol()
    candidate["training"].update(original_n=4, updates=1, batch_size=4, cap_seconds=30)
    fitted = study.fit_roster({"Heston": data, "local": local_data}, candidate=candidate)
    validation = study.select_validation(
        data, risk, generator="Heston", universe="U2", widths=[0, 0.01, 0.02, 0.05, 0.1, 0.2]
    )
    return data, risk, fitted, validation


@pytest.mark.parametrize(
    "field,bad",
    [
        ("seed", 29),
        ("universe", "U1"),
        ("original_path_count", 3),
        ("training_generator", "local"),
        ("fit_id", "fit:Heston:U1:init29"),
        ("checkpoint_id", "best_test_mse"),
    ],
)
def test_test_roster_raw_checkpoint_mismatch_keeps_original_cell_unknown(
    tiny_identity_roster, field, bad
):
    data, risk, fitted, validation = tiny_identity_roster
    altered = copy.deepcopy(fitted)
    row = next(row for row in altered["fits"] if row["id"] == "fit:Heston:U2:init11")
    row["raw_fit"][field] = bad
    result = study.test_roster(data, risk, altered, validation, generator="Heston", universe="U2")
    cell = next(cell for cell in result["cells"] if cell["policy_id"] == "nn:trainHeston:init11")
    assert len(result["cells"]) == 11
    assert cell["status"] == "unknown"
    assert cell["original_n"] == 4
    assert np.isnan(cell["result"]["discounted_pnl"]).all()
    assert "identity" in cell["reason"]
    unaffected = next(
        cell for cell in result["cells"] if cell["policy_id"] == "nn:trainHeston:init29"
    )
    assert unaffected["status"] == "completed"


@pytest.mark.parametrize(
    "field,bad",
    [
        ("universe", "U1"),
        ("initialization", 29),
        ("training_generator", "local"),
        ("original_n", 3),
        ("original_n", None),
        ("checkpoint_id", "best_test_mse"),
    ],
)
def test_test_roster_outer_checkpoint_mismatch_is_not_replayed(tiny_identity_roster, field, bad):
    data, risk, fitted, validation = tiny_identity_roster
    altered = copy.deepcopy(fitted)
    row = next(row for row in altered["fits"] if row["id"] == "fit:Heston:U2:init11")
    row[field] = bad
    result = study.test_roster(data, risk, altered, validation, generator="Heston", universe="U2")
    cell = next(cell for cell in result["cells"] if cell["policy_id"] == "nn:trainHeston:init11")
    assert cell["status"] == "unknown"
    assert np.isnan(cell["result"]["discounted_pnl"]).all()


class CalendarField:
    def evaluate(self, time, spots):
        spots = np.asarray(spots, float)
        unsupported = (time == 0) & (spots != 100)
        return {
            "variance": np.where(unsupported, np.nan, 0.04 + 0.24 * time),
            "status": np.where(unsupported, "unsupported_initial", "ok"),
        }


def test_local_covariance_uses_current_calendar_state_not_monthly_midpoint():
    data, _, caches = setup()
    risk = study.quote_risk_dataset(parameters(), CalendarField(), data, caches)
    row = risk["models"]["local"]
    j = 3
    time, spot = data["times"][j], data["prices"][0, j, 0]
    expected_base = 0.04 + 0.24 * time
    expected_covariance = expected_base * spot**2 * np.diff(data["times"])[j]
    assert row["local_base_variance"][0, j] == pytest.approx(expected_base)
    assert row["price_covariance"][0, j, 0, 0] == pytest.approx(expected_covariance)


def test_t0_unsupported_covariance_uses_saved_first_internal_midpoint():
    data, _, caches = setup()
    data["prices"][:, 0, 0] = [99.95, 100, 100.05, 100]
    data["prices"][:, 0, 1] = 0.2 * data["prices"][:, 0, 0] - 10 + 0.2
    data["primitives"]["calendar_times"] = np.arange(193) / 192
    data["primitives"]["record_indices"] = np.arange(13) * 16
    risk = study.quote_risk_dataset(parameters(), CalendarField(), data, caches)
    row = risk["models"]["local"]
    expected = np.array([0.04 + 0.24 / 384, 0.04, 0.04 + 0.24 / 384, 0.04])
    assert row["local_base_variance"][:, 0] == pytest.approx(expected)
    assert row["local_base_source_time"][:, 0] == pytest.approx([1 / 384, 0, 1 / 384, 0])
    assert row["local_base_early_proxy"][:, 0] == pytest.approx([True, False, True, False])


def test_t0_unsupported_covariance_without_internal_grid_stays_unknown():
    data, _, caches = setup()
    data["prices"][:, 0, 0] = 99.95
    data["prices"][:, 0, 1] = 0.2 * 99.95 - 10 + 0.2
    data.pop("primitives")
    risk = study.quote_risk_dataset(parameters(), CalendarField(), data, caches)
    row = risk["models"]["local"]
    assert np.isnan(row["local_base_variance"][:, 0]).all()
    assert np.all(row["band_qualification"][:, 0] == "unknown")
    assert np.all(row["qualification"][:, 0] == "qualified")


@pytest.mark.parametrize("quote", [99.0, np.nan])
def test_exact_linear_targets_do_not_depend_on_an_unnecessary_quote_fit(quote):
    data, _, caches = setup()
    data["memory_sum"][:, 3] = 1300
    data["prices"][:, 3, 1] = quote
    for pair in caches.values():
        pair["call"]["derivative_error"] = np.nan
        pair["asian"].pop("deterministic_error")
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    t = data["times"][3]
    expected = np.exp(-0.03 * (1 - t)) * np.exp(0.03 * (np.arange(4, 13) / 12 - t)).sum() / 12
    for row in risk["models"].values():
        assert np.all(row["fit_status"][:, 3] == "unknown")
        assert row["u2_target"][:, 3] == pytest.approx(np.tile([expected, 0], (4, 1)))
        assert row["u1_target"][:, 3] == pytest.approx(expected)
        assert row["u2_position_se"][:, 3] == pytest.approx(0)
        assert row["u2_deterministic_error"][:, 3] == pytest.approx(0)
        assert np.all(row["qualification"][:, 3] == "qualified")
        assert np.all(row["band_qualification"][:, 3] == "unknown")


@pytest.mark.parametrize("universe", ["U1", "U2"])
def test_greek_linear_action_survives_no_root_but_band_keeps_unknown_covariance(universe):
    data, _, caches = setup()
    data["memory_sum"][:, 3] = 1300
    data["prices"][:, 3, 1] = 99
    risk = study.quote_risk_dataset(parameters(), ConstantField(), data, caches)
    greek = study.policy_rollout(data, risk, universe=universe, policy="greek", model="heston")
    band = study.policy_rollout(
        data, risk, universe=universe, policy="band", model="heston", width=0.02
    )
    assert np.isfinite(greek["holdings"][:, 3]).all()
    assert greek["holdings"][:, 3, 1] == pytest.approx(0)
    assert np.isfinite(greek["discounted_pnl"]).all()
    assert np.isnan(band["holdings"][:, 3:]).all()
    assert band["status"] == "unknown"


def test_zero_call_exposure_does_not_require_unknown_unused_call_mid_or_cf():
    data, risk, _ = setup()
    row = risk["models"]["heston"]
    row["u2_target"][..., 1] = 0
    baseline = study.policy_rollout(data, risk, universe="U2", policy="greek", model="heston")
    data["prices"][1, 4, 1] = np.nan
    data["cashflows"][1, 4, 1] = np.nan
    data["qualification"] = "unknown"
    changed = study.policy_rollout(data, risk, universe="U2", policy="greek", model="heston")
    assert changed["discounted_pnl"] == pytest.approx(baseline["discounted_pnl"])
    assert changed["discounted_gain_pnl"] == pytest.approx(baseline["discounted_gain_pnl"])
    assert changed["costs"] == pytest.approx(baseline["costs"])
    assert changed["status"] == "unknown"
    assert changed["unused_call_price_mask"][1, 4]
    assert changed["unused_call_cashflow_mask"][1, 4]
    assert changed["unused_call_price_mask"].sum() == 1
    assert changed["unused_call_cashflow_mask"].sum() == 1


def test_unknown_call_mid_cannot_be_ignored_when_liquidating_a_nonzero_call():
    data, risk, _ = setup()
    row = risk["models"]["heston"]
    row["u2_target"][..., 1] = 0
    row["u2_target"][:, 3, 1] = 0.5
    data["prices"][:, 4, 1] = np.nan
    result = study.policy_rollout(data, risk, universe="U2", policy="greek", model="heston")
    assert np.isnan(result["discounted_pnl"]).all()
    assert result["status"] == "unknown"
    assert not np.any(result["unused_call_price_mask"][:, 4])


@pytest.mark.parametrize("universe,policy", [("U1", "greek"), ("U2", "none")])
def test_unused_invalid_call_masks_use_the_same_zero_exposure_definition(universe, policy):
    data, risk, _ = setup()
    data["prices"][1, 4, 1] = np.nan
    data["cashflows"][1, 4, 1] = np.nan
    data["qualification"] = "unknown"
    result = study.policy_rollout(data, risk, universe=universe, policy=policy, model="heston")
    assert np.isfinite(result["discounted_pnl"]).all()
    assert result["unused_call_price_mask"][1, 4]
    assert result["unused_call_cashflow_mask"][1, 4]
    assert result["unused_call_price_mask"].sum() == 1
    assert result["unused_call_cashflow_mask"].sum() == 1
