"""Saved-only dynamic finance replay; raw fixtures and tamper boundaries."""

import numpy as np
import pytest
from hullkit._dynamic_hedging_conditional import primitive_labels, teacher_primitives
from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid

from deep_hedge_price._dynamic_hedging_replay import (
    check_cash,
    check_market,
    check_statistics,
    rebuild_asian_cache,
    replay_teacher,
)


def parameters(**changes):
    values = dict(
        spot=100.0, rate=0.03, dividend_yield=0.0, v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.7
    )
    values.update(changes)
    return HestonParameters(**values)


def primitives(*, model="heston", state=0.04, spot=100.0, date=11 / 12):
    p = parameters()
    steps = round((1 - date) * 12)
    times = np.linspace(date, 1.0, steps + 1)
    # Hand-specified finite drivers: no RNG is needed even in fixture setup.
    normals = np.zeros((32, steps, 2))
    normals[:, :, 0] = np.linspace(-1.7, 1.7, 32)[:, None]
    normals[:, :, 1] = np.linspace(0.8, -0.8, 32)[:, None]
    surface = (
        LocalVarianceGrid(np.array([0.01, 1.25]), np.array([-8.0, 8.0]), np.full((2, 2), 0.04), p)
        if model == "local"
        else None
    )
    got = teacher_primitives(
        model,
        p,
        normals,
        calendar_times=times,
        fixing_indices=np.arange(1, steps + 1),
        spot=spot,
        state=state,
        memory_count=12 - steps,
        surface=surface,
    )
    return got, p, surface


def cash_fixture():
    return (
        dict(
            times=np.array([0.0, 0.5, 1.0]),
            prices=np.array([[[100.0, 6.0], [104.0, 8.0], [102.0, 5.0]]]),
            cashflows=np.zeros((1, 3, 2)),
            payoff=np.array([3.0]),
            cost_rates=np.array([0.001, 0.005]),
            premium=7.0,
            rate=0.05,
        ),
        dict(holdings=np.array([[[0.4, 0.5], [0.6, 0.2]]])),
    )


def test_teacher_replays_analytic_last_step_and_preserves_boundary():
    raw, p, surface = primitives()
    got = replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)
    assert got["integrity"] == "pass"
    assert got["qualification"] == "unknown"
    assert got["earlier_sde_verified"] is False
    assert got["original_path_count"] == 32
    # At the restart spot, a one-fixing K100 claim is ordinary BS at 1/12.
    from scipy.special import ndtr

    tau = 1 / 12
    d1 = (0.03 + 0.04 / 2) * np.sqrt(tau / 0.04)
    expected = np.exp(0.03 * tau) * ndtr(d1) - ndtr(d1 - 0.2 * np.sqrt(tau))
    assert got["labels"]["f"][1] == pytest.approx(expected, abs=2e-13)
    assert got["labels"]["block_means"].shape == (16, 3, 3)


@pytest.mark.parametrize(
    "field",
    [
        "rate",
        "dividend_yield",
        "control_variance",
        "aux_last_loading",
        "expiry_delay",
        "total_fixings",
        "analytic_conditional",
        "deterministic_model",
    ],
)
def test_teacher_rejects_tampered_derived_scalar(field):
    raw, p, surface = primitives()
    if isinstance(raw[field], bool):
        raw[field] = not raw[field]
    else:
        raw[field] += 0.01
    with pytest.raises(ValueError, match=field):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


@pytest.mark.parametrize("field", ["c", "mu", "sigma", "last_left_coefficient"])
def test_teacher_rejects_tampered_last_step_relation(field):
    raw, p, surface = primitives()
    raw[field][0] += 0.01
    with pytest.raises(ValueError, match=field):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_teacher_rejects_original_denominator_tamper():
    raw, p, surface = primitives()
    raw["N"] = 16
    with pytest.raises(ValueError, match="N"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_teacher_saved_label_tamper_is_not_accepted():
    raw, p, surface = primitives()
    labels = primitive_labels(raw, np.array([0.5, 1.0, 2.0]))
    labels["block_means"][0, 1, 2] += 0.1
    with pytest.raises(ValueError, match="block_means"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface, saved_labels=labels)


def test_teacher_invalid_original_path_stays_unknown_with_denominator():
    raw, p, surface = primitives()
    raw["path_mask"][0] = False
    raw["primitive_status"][0] = "invalid"
    raw["failure_reasons"][0] = "nonfinite_driver"
    for key in (
        "b",
        "c",
        "mu",
        "sigma",
        "last_z",
        "last_left_spot",
        "last_left_variance",
        "last_left_coefficient",
        "aux_logG_prefix",
    ):
        raw[key][0] = np.nan
    got = replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)
    assert got["original_path_count"] == 32
    assert got["valid_path_count"] == 31
    assert got["qualification"] == "unknown"
    assert np.isnan(got["labels"]["f"]).all()


def test_local_control_variance_is_derived_from_saved_field():
    raw, p, surface = primitives(model="local", state=2.0)
    got = replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)
    assert got["derived_primitives"]["control_variance"] == pytest.approx(0.08)
    raw["control_variance"] = 0.04
    with pytest.raises(ValueError, match="control_variance"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_cash_recomputed_against_independent_hand_calculation():
    data, cell = cash_fixture()
    got = check_cash(data, cell)
    assert got["integrity"] == "pass"
    assert got["original_path_count"] == 1
    assert got["recomputed"]["discounted_pnl"][0] == pytest.approx(2.2171179961044647, abs=1e-12)
    assert got["recomputed"]["costs"][0] == pytest.approx([0.055, 0.0328, 0.0662], abs=1e-12)
    assert got["recomputed"]["discounted_gain_pnl"] == pytest.approx(
        got["recomputed"]["discounted_pnl"], abs=2e-13
    )


@pytest.mark.parametrize("field", ["cash", "costs", "discounted_pnl", "discounted_gain_pnl"])
def test_cash_saved_numeric_tamper_is_refused(field):
    data, cell = cash_fixture()
    result = check_cash(data, cell)["recomputed"]
    cell[field] = result[field].copy()
    cell[field].flat[0] += 0.1
    with pytest.raises(ValueError, match=field):
        check_cash(data, cell)


def test_cash_failure_is_preserved_and_never_dropped():
    data, cell = cash_fixture()
    data["prices"] = np.repeat(data["prices"], 2, axis=0)
    data["cashflows"] = np.repeat(data["cashflows"], 2, axis=0)
    data["payoff"] = np.repeat(data["payoff"], 2)
    cell["holdings"] = np.repeat(cell["holdings"], 2, axis=0)
    cell["holdings"][1, 0, 0] = np.nan
    result = check_cash(data, cell)
    assert result["original_path_count"] == 2
    assert result["valid_path_count"] == 1
    assert result["qualification"] == "unknown"
    assert np.isnan(result["recomputed"]["discounted_pnl"][1])


def test_cash_rejects_outside_legal_holdings_without_clipping():
    data, cell = cash_fixture()
    cell["holdings"][0, 0, 0] = 2.1
    with pytest.raises(ValueError, match="holding"):
        check_cash(data, cell)


def market_fixture():
    times = np.arange(13) / 12
    stock = np.broadcast_to(100 * np.exp(0.03 * times), (32, 13)).copy()
    state = np.full_like(stock, 0.04)
    quote = 0.2 * stock + 10 * state
    prices = np.stack([stock, quote], axis=-1)
    A = np.cumsum(np.column_stack([np.zeros(32), stock[:, 1:]]), axis=1)
    n = np.arange(13)
    spots = np.array([80.0, 90.0, 110.0, 140.0])
    states = np.array([0.01, 0.02, 0.04, 0.08])
    values = np.broadcast_to(
        0.2 * spots[None, :, None] + 10 * states[None, None, :], (13, 4, 4)
    ).copy()
    cache = dict(
        model="heston",
        dates=times,
        spot_nodes=spots,
        state_nodes=states,
        values=values,
        rate=0.03,
        dividend_yield=0.0,
        strike=100.0,
        maturity=1.25,
        price_error=np.nan,
    )
    data = dict(
        times=times,
        prices=prices,
        memory_sum=A,
        memory_count=n,
        payoff=np.maximum(A[:, -1] / 12 - 100, 0.0),
        cashflows=np.zeros_like(prices),
        rate=0.03,
    )
    return data, cache, state


def test_market_replays_fixing_first_memory_payoff_and_actual_quote():
    data, cache, state = market_fixture()
    out = check_market(
        data,
        fixing_times=np.arange(1, 13) / 12,
        call_cache=cache,
        generator="heston",
        latent_state=state,
    )
    assert out["integrity"] == "pass"
    assert out["original_path_count"] == 32
    assert out["qualification"] == "unknown"
    assert out["earlier_sde_verified"] is False
    assert out["recomputed"]["discounted_gains"].shape == (32, 12, 2)
    assert out["recomputed"]["mean_total_gains"][0] == pytest.approx(0.0, abs=3e-14)
    assert out["recomputed"]["memory_count"].tolist() == list(range(13))


@pytest.mark.parametrize("field", ["memory_sum", "memory_count", "payoff"])
def test_market_rejects_saved_observable_tamper(field):
    data, cache, state = market_fixture()
    data[field] = data[field].astype(float)
    data[field].flat[-1] += 0.1
    with pytest.raises(ValueError, match=field):
        check_market(
            data,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=cache,
            generator="heston",
            latent_state=state,
        )


def test_market_rejects_actual_quote_tamper():
    data, cache, state = market_fixture()
    data["prices"][0, 1, 1] += 0.01
    with pytest.raises(ValueError, match="call"):
        check_market(
            data,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=cache,
            generator="heston",
            latent_state=state,
        )


def test_market_requires_latent_state_only_to_check_actual_heston_prices():
    data, cache, _ = market_fixture()
    with pytest.raises(ValueError, match="latent_state"):
        check_market(data, fixing_times=np.arange(1, 13) / 12, call_cache=cache, generator="heston")


def test_market_invalid_original_path_keeps_count_and_unknown_gain():
    data, cache, state = market_fixture()
    data["prices"][0, 3:, 0] = np.nan
    data["prices"][0, 3:, 1] = np.nan
    data["memory_sum"][0, 3:] = np.nan
    data["payoff"][0] = np.nan
    state[0, 3:] = np.nan
    out = check_market(
        data,
        fixing_times=np.arange(1, 13) / 12,
        call_cache=cache,
        generator="heston",
        latent_state=state,
    )
    assert out["original_path_count"] == 32
    assert out["valid_path_count"] == 31
    assert out["qualification"] == "unknown"
    assert np.isnan(out["recomputed"]["mean_total_gains"]).all()


def test_rebuild_uses_global_driver_mapping_without_claiming_earlier_sde():
    p = parameters()
    rows = []
    for state in [0.01, 0.02, 0.04, 0.08]:
        raw, _, _ = primitives(state=state)
        rows.append(
            dict(
                primitives=raw,
                thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
                date_index=0,
                global_driver_id="global-fixture",
                driver_mapping=dict(
                    original_n=32,
                    global_steps=768,
                    start_step=704,
                    stop_step=768,
                    aggregation_factor=64,
                ),
            )
        )
    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    out = rebuild_asian_cache(rows, p, axes, model="heston")
    assert out["integrity"] == "pass"
    assert out["earlier_sde_verified"] is False
    assert out["cache"]["f"].shape == (1, 4, 4)
    assert out["cache"]["block_means"].shape == (1, 4, 4, 16, 3)
    assert out["cache"]["shared_driver_ids"] == ("global-fixture",)
    assert all(row["slice_driver_id"] for row in out["driver_bindings"])


def test_rebuild_rejects_wrong_driver_mapping_calendar():
    p = parameters()
    raw, _, _ = primitives()
    row = dict(
        primitives=raw,
        thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
        date_index=0,
        global_driver_id="global-fixture",
        driver_mapping=dict(
            original_n=32, global_steps=768, start_step=0, stop_step=64, aggregation_factor=64
        ),
    )
    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    with pytest.raises(ValueError, match="driver_mapping"):
        rebuild_asian_cache([row], p, axes, model="heston")


def statistics_fixture():
    from hullkit._dynamic_hedging_statistics import paired_statistics

    base = np.broadcast_to(np.tile([1.0, 2.0, 3.0, 4.0], 32), (3, 128)).copy()
    candidate = 0.8 * base
    indices = np.array(
        [
            [[0, 0], [0, 1], [1, 1]],
            [[1, 1], [1, 0], [0, 0]],
            [[0, 1], [1, 1], [1, 0]],
            [[1, 0], [0, 0], [0, 1]],
        ],
        dtype=np.int16,
    )
    envelope = dict(absolute=0.0, relative=0.0)
    saved = paired_statistics(base, candidate, indices, numerical_envelope=envelope)
    return base, candidate, indices, envelope, saved


def test_statistics_recomputes_saved_ci_scores_es_without_rng(monkeypatch):
    base, candidate, indices, envelope, saved = statistics_fixture()

    def forbidden(*args, **kwargs):
        raise AssertionError("saved checker must not draw RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(np.random, "SeedSequence", forbidden)
    out = check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)
    assert out["integrity"] == "pass"
    assert out["recomputed"]["means"]["absolute"] == pytest.approx(-2.7)
    assert out["recomputed"]["means"]["relative"] == pytest.approx(-2.325)
    assert out["recomputed"]["candidate_summary"]["es95"] == pytest.approx(3.2)
    assert out["original_path_count"] == 384


@pytest.mark.parametrize("field", ["scores", "block_scores", "bootstrap_scores", "upper_bounds"])
def test_statistics_rejects_rawscore_block_ci_tamper(field):
    base, candidate, indices, envelope, saved = statistics_fixture()
    saved[field]["absolute"] = np.asarray(saved[field]["absolute"]).copy()
    saved[field]["absolute"].flat[0] += 0.1
    with pytest.raises(ValueError, match=field):
        check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)


def test_statistics_missing_envelope_stays_unknown():
    base, candidate, indices, _, _ = statistics_fixture()
    from hullkit._dynamic_hedging_statistics import paired_statistics

    saved = paired_statistics(base, candidate, indices)
    out = check_statistics(base, candidate, indices, saved)
    assert out["qualification"] == "unknown"


def test_statistics_nonfinite_original_pair_remains_unknown_with_original_n():
    base, candidate, indices, envelope, _ = statistics_fixture()
    candidate[0, 0] = np.nan
    from hullkit._dynamic_hedging_statistics import paired_statistics

    saved = paired_statistics(base, candidate, indices, numerical_envelope=envelope)
    out = check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)
    assert out["original_path_count"] == 384
    assert out["qualification"] == "unknown"
    assert out["recomputed"]["counts"]["unknown"] == 1


def test_teacher_all_failed_raw_attempt_keeps_denominator_and_raw_flags():
    raw, p, surface = primitives()
    normals = np.full((32, 1, 2), np.nan)
    raw = teacher_primitives(
        "heston",
        p,
        normals,
        calendar_times=np.array([11 / 12, 1.0]),
        fixing_indices=np.array([1]),
        spot=100.0,
        state=0.04,
        memory_count=11,
    )
    got = replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)
    assert got["original_path_count"] == 32
    assert got["valid_path_count"] == 0
    assert got["qualification"] == "unknown"
    assert got["raw_metadata"]["deterministic_model"] is True
    assert got["derived_primitives"]["deterministic_model"] is False


@pytest.mark.parametrize("compact", [False, True])
def test_teacher_replays_status_encodings_with_identical_financial_labels(compact):
    p = parameters()
    normals = np.zeros((32, 2, 2))
    normals[:, :, 0] = np.linspace(-1.7, 1.7, 32)[:, None]
    raw = teacher_primitives(
        "heston",
        p,
        normals,
        calendar_times=np.array([10 / 12, 11 / 12, 1.0]),
        fixing_indices=np.array([1, 2]),
        spot=100.0,
        state=0.04,
        memory_count=10,
        compact_status=compact,
    )
    out = replay_teacher(raw, np.array([0.0, 1.0, 2.0, 4.0]), p, None)
    assert out["integrity"] == "pass"
    assert out["labels"]["block_means"].shape == (16, 4, 3)
    assert out["step_status_summary"]["original_evaluations"] == 64
    assert out["step_status_summary"]["not_executed"] == 0


def compact_primitives():
    p = parameters()
    raw = teacher_primitives(
        "heston",
        p,
        np.zeros((32, 1, 2)),
        calendar_times=np.array([11 / 12, 1.0]),
        fixing_indices=np.array([1]),
        spot=100.0,
        state=0.04,
        memory_count=11,
        compact_status=True,
    )
    return raw, p


@pytest.mark.parametrize("kind", ["range", "legend", "unexecuted"])
def test_teacher_rejects_tampered_compact_step_status(kind):
    raw, p = compact_primitives()
    if kind == "range":
        raw["local_step_status"][0, 0] = 200
    elif kind == "legend":
        raw["local_step_status_labels"][1] = "wing_left"
    else:
        raw["local_step_status"][0, 0] = 0
    with pytest.raises(ValueError, match="local_step_status"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, None)


def test_teacher_rejects_nonzero_preceding_sum_with_only_one_future_fixing():
    raw, p, surface = primitives()
    raw["b"][0] = 0.01
    with pytest.raises(ValueError, match="b"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_teacher_rejects_last_left_spot_tamper_at_analytic_restart():
    raw, p, surface = primitives()
    # Changing both c and left stock keeps their local relation but contradicts
    # the one-step restart. It must not pass simply because derived c matches.
    raw["last_left_spot"][0] += 1.0
    raw["c"][0] = raw["last_left_spot"][0] / raw["spot"]
    with pytest.raises(ValueError, match="last_left_spot"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_cash_nonzero_dividend_cf_and_terminal_call_mid_are_counted_once():
    data, cell = cash_fixture()
    data["cashflows"][0, 1, 0] = 2.0
    data["cashflows"][0, 2, 0] = 1.0
    got = check_cash(data, cell)["recomputed"]
    # Previous holdings receive .4*2 at .5 and .6*1 at 1. The T1 call remains
    # alive: its terminal market mid is recovered once, without a second payoff.
    expected = 2.2171179961044647 + 0.8 * np.exp(-0.025) + 0.6 * np.exp(-0.05)
    assert got["discounted_pnl"][0] == pytest.approx(expected, abs=1e-12)


def test_cash_zero_fee_counterfactual_recomputes_same_holdings():
    data, cell = cash_fixture()
    data["cost_rates"] = np.zeros(2)
    got = check_cash(data, cell)["recomputed"]
    expected = 2.2171179961044647 + 0.055 + 0.0328 * np.exp(-0.025) + 0.0662 * np.exp(-0.05)
    assert got["discounted_pnl"][0] == pytest.approx(expected, abs=1e-12)
    assert got["costs"] == pytest.approx(np.zeros((1, 3)), abs=1e-15)


def test_teacher_rejects_analytic_aux_prefix_tamper_without_saved_labels():
    raw, p, surface = primitives()
    raw["aux_logG_prefix"][0] += 0.01
    with pytest.raises(ValueError, match="aux_logG_prefix"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_teacher_rejects_negative_preceding_normalized_fixing_sum():
    raw, p, surface = primitives(date=10 / 12)
    raw["b"][0] = -0.01
    with pytest.raises(ValueError, match="b"):
        replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)


def test_rebuild_keeps_shared_cluster_summaries_without_retaining_node_samples():
    rows = []
    for state in [0.01, 0.02, 0.04, 0.08]:
        raw, p, _ = primitives(state=state)
        rows.append(
            dict(
                primitives=raw,
                thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
                date_index=0,
                global_driver_id="global-fixture",
                driver_mapping=dict(
                    original_n=32,
                    global_steps=768,
                    start_step=704,
                    stop_step=768,
                    aggregation_factor=64,
                ),
            )
        )
    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    out = rebuild_asian_cache(rows, p, axes, model="heston")
    for group in out["cache"]["primitive_groups"]["groups"]:
        # The consumed source cache keeps groups; storing full path samples in
        # each group would scale as Cartesian nodes * N * thresholds.
        assert all(
            np.asarray(v).shape[:1] != (32,) for v in group.values() if isinstance(v, np.ndarray)
        )
    assert out["cache"]["block_means"][0, 2, 2, :, 2] == pytest.approx(
        np.full(16, 0.024331739688747106), abs=2e-13
    )


def test_rebuild_missing_original_node_is_unknown_not_implicit_extension():
    raw, p, _ = primitives()
    row = dict(
        primitives=raw,
        thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
        date_index=0,
        global_driver_id="global-fixture",
        driver_mapping=dict(
            original_n=32, global_steps=768, start_step=704, stop_step=768, aggregation_factor=64
        ),
    )
    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    out = rebuild_asian_cache([row], p, axes, model="heston")
    assert out["original_group_count"] == 4
    assert out["saved_group_count"] == 1
    assert out["qualification"] == "unknown"
    assert np.isnan(out["cache"]["f"][0, 0]).all()


def test_cash_refuses_hidden_discount_convention_from_nonzero_restart():
    data, cell = cash_fixture()
    data["times"] += 0.1
    with pytest.raises(ValueError, match="times"):
        check_cash(data, cell)


def test_statistics_rejects_erased_original_count_even_with_unchanged_means():
    base, candidate, indices, envelope, saved = statistics_fixture()
    saved["counts"]["original"] -= 1
    with pytest.raises(ValueError, match="original"):
        check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)


def test_statistics_rejects_erased_failed_pair_in_finite_subset():
    base, candidate, indices, envelope, _ = statistics_fixture()
    candidate[0, 0] = np.nan
    from hullkit._dynamic_hedging_statistics import paired_statistics

    saved = paired_statistics(base, candidate, indices, numerical_envelope=envelope)
    saved["counts"]["unknown"] = 0
    saved["status"] = "supported"
    with pytest.raises(ValueError):
        check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)


def test_rebuild_accepts_single_pass_primitive_stream_for_bounded_memory():
    p = parameters()

    def rows():
        for state in [0.01, 0.02, 0.04, 0.08]:
            raw, _, _ = primitives(state=state)
            yield dict(
                primitives=raw,
                thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
                date_index=0,
                global_driver_id="global-fixture",
                driver_mapping=dict(
                    original_n=32,
                    global_steps=768,
                    start_step=704,
                    stop_step=768,
                    aggregation_factor=64,
                ),
            )

    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    out = rebuild_asian_cache(rows(), p, axes, model="heston")
    assert out["saved_group_count"] == 4
    assert np.isfinite(out["cache"]["f"][:, :, :3]).all()


def test_all_replay_boundaries_forbid_rng_simulation_training_and_call_rebuild(monkeypatch):
    raw, p, surface = primitives()
    data, cache, state = market_fixture()
    cash_data, cell = cash_fixture()
    base, candidate, indices, envelope, saved = statistics_fixture()

    def forbidden(*args, **kwargs):
        raise AssertionError("saved boundary must not regenerate or train")

    import hullkit._dynamic_hedging_conditional as conditional
    import hullkit._dynamic_hedging_core as core
    import hullkit._dynamic_hedging_surfaces as surfaces

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(np.random, "SeedSequence", forbidden)
    monkeypatch.setattr(conditional, "teacher_primitives", forbidden)
    monkeypatch.setattr(core, "heston_records", forbidden)
    monkeypatch.setattr(core, "local_records", forbidden)
    monkeypatch.setattr(core, "cash_account", forbidden)
    monkeypatch.setattr(surfaces, "build_call_cache", forbidden)
    assert replay_teacher(raw, np.array([0.5, 1.0, 2.0]), p, surface)["integrity"] == "pass"
    assert (
        check_market(
            data,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=cache,
            generator="heston",
            latent_state=state,
        )["integrity"]
        == "pass"
    )
    assert check_cash(cash_data, cell)["integrity"] == "pass"
    assert (
        check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)["integrity"]
        == "pass"
    )


def test_market_singleton_se_remains_unknown_without_invented_zero():
    data, cache, state = market_fixture()
    for key in ("prices", "memory_sum", "payoff", "cashflows"):
        data[key] = data[key][:1].copy()
    out = check_market(
        data,
        fixing_times=np.arange(1, 13) / 12,
        call_cache=cache,
        generator="heston",
        latent_state=state[:1],
    )
    assert out["original_path_count"] == 1
    assert np.isnan(out["recomputed"]["total_gain_se"]).all()
    assert out["qualification"] == "unknown"


def test_cash_raw_holdings_constraint_tamper_is_detected():
    data, cell = cash_fixture()
    cell["raw_holdings"] = cell["holdings"].copy()
    cell["raw_holdings"][0, 0, 0] = 0.9
    with pytest.raises(ValueError, match="raw_holdings"):
        check_cash(data, cell)


def test_statistics_es_original_individual_tail_count_tamper_is_detected():
    base, candidate, indices, envelope, saved = statistics_fixture()
    assert saved["candidate_summary"]["es95_tail_count"] == 20
    saved["candidate_summary"]["es95_tail_count"] = 1
    with pytest.raises(ValueError, match="es95_tail_count"):
        check_statistics(base, candidate, indices, saved, numerical_envelope=envelope)


@pytest.mark.parametrize("declaration", ["original_n", "original_path_count"])
def test_cash_rejects_erased_dataset_original_paths(declaration):
    data, cell = cash_fixture()
    # The declared two-path population cannot become a complete one-path
    # accounting result merely by removing a failed original row.
    data[declaration] = 2
    with pytest.raises(ValueError, match=declaration):
        check_cash(data, cell)


@pytest.mark.parametrize("declaration", ["original_n", "original_path_count"])
def test_market_rejects_erased_dataset_original_paths(declaration):
    data, cache, state = market_fixture()
    data[declaration] = 64
    with pytest.raises(ValueError, match=declaration):
        check_market(
            data,
            fixing_times=np.arange(1, 13) / 12,
            call_cache=cache,
            generator="heston",
            latent_state=state,
        )


@pytest.mark.parametrize("declaration", ["original_n", "original_path_count"])
def test_cash_rejects_erased_cell_original_paths(declaration):
    data, cell = cash_fixture()
    cell[declaration] = 2
    with pytest.raises(ValueError, match=declaration):
        check_cash(data, cell)


def test_cash_accepts_consistent_original_count_aliases():
    data, cell = cash_fixture()
    data.update(original_n=1, original_path_count=1)
    cell.update(original_n=1, original_path_count=1)
    out = check_cash(data, cell)
    assert out["original_path_count"] == 1
    assert out["recomputed"]["discounted_pnl"][0] == pytest.approx(2.2171179961044647, abs=1e-12)


def test_market_accepts_consistent_original_count_aliases():
    data, cache, state = market_fixture()
    data.update(original_n=32, original_path_count=32)
    out = check_market(
        data,
        fixing_times=np.arange(1, 13) / 12,
        call_cache=cache,
        generator="heston",
        latent_state=state,
    )
    assert out["original_path_count"] == 32
    assert out["valid_path_count"] == 32


def test_rebuild_rejects_conflicting_global_length_with_same_sliced_calendar():
    rows = []
    for i, state in enumerate([0.01, 0.02, 0.04, 0.08]):
        raw, p, _ = primitives(state=state)
        ratio = 2 if i == 3 else 1
        rows.append(
            dict(
                primitives=raw,
                thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
                date_index=0,
                global_driver_id="same-global-driver",
                driver_mapping=dict(
                    original_n=32,
                    global_steps=768 * ratio,
                    start_step=704 * ratio,
                    stop_step=768 * ratio,
                    aggregation_factor=64 * ratio,
                ),
            )
        )
    axes = dict(
        dates=np.array([11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    # Both maps give [11/12, 1], but one shared global array cannot have two
    # lengths. Comparing only the derived restart calendar misses this tamper.
    with pytest.raises(ValueError, match="global_steps"):
        rebuild_asian_cache(rows, p, axes, model="heston")


def test_rebuild_keeps_legitimate_per_date_slice_and_time_aggregation():
    p = parameters()
    rows = []
    for j, date in enumerate([10 / 12, 11 / 12]):
        for state in [0.01, 0.02, 0.04, 0.08]:
            if j == 0:
                raw, _, _ = primitives(date=date, state=state)
                mapping = dict(
                    original_n=32,
                    global_steps=768,
                    start_step=640,
                    stop_step=768,
                    aggregation_factor=64,
                )
            else:
                normals = np.zeros((32, 2, 2))
                normals[:, :, 0] = np.linspace(-1.7, 1.7, 32)[:, None]
                raw = teacher_primitives(
                    "heston",
                    p,
                    normals,
                    calendar_times=np.array([11 / 12, 23 / 24, 1.0]),
                    fixing_indices=np.array([2]),
                    spot=100.0,
                    state=state,
                    memory_count=11,
                    compact_status=True,
                )
                mapping = dict(
                    original_n=32,
                    global_steps=768,
                    start_step=704,
                    stop_step=768,
                    aggregation_factor=32,
                )
            rows.append(
                dict(
                    primitives=raw,
                    thresholds=np.array([0.0, 0.5, 1.0, 2.0]),
                    date_index=j,
                    global_driver_id="same-global-driver",
                    driver_mapping=mapping,
                )
            )
    axes = dict(
        dates=np.array([10 / 12, 11 / 12]),
        state=np.array([0.01, 0.02, 0.04, 0.08]),
        threshold=np.array([0.0, 0.5, 1.0, 2.0]),
    )
    out = rebuild_asian_cache(rows, p, axes, model="heston")
    assert out["original_group_count"] == 8
    assert out["saved_group_count"] == 8
    assert {x["driver_mapping"]["global_steps"] for x in out["driver_bindings"]} == {768}
    assert {x["driver_mapping"]["aggregation_factor"] for x in out["driver_bindings"]} == {32, 64}


def test_cash_zero_call_exposure_ignores_unknown_call_without_repairing_market():
    data, cell = cash_fixture()
    cell["universe"] = "U1"
    cell["holdings"][..., 1] = 0.0
    data["prices"][..., 1] = np.nan
    data["cashflows"][..., 1] = np.nan
    cell["unused_call_price_mask"] = np.ones((1, 3), dtype=bool)
    cell["unused_call_cashflow_mask"] = np.ones((1, 3), dtype=bool)
    out = check_cash(data, cell)
    dhalf, dend = np.exp(-0.025), np.exp(-0.05)
    expected = (
        7.0
        + 0.4 * (104.0 * dhalf - 100.0)
        + 0.6 * (102.0 * dend - 104.0 * dhalf)
        - 0.04
        - 0.0208 * dhalf
        - 0.0612 * dend
        - 3.0 * dend
    )
    assert out["qualification"] == "verified"
    assert out["recomputed"]["discounted_pnl"][0] == pytest.approx(expected, abs=1e-12)
    assert np.isnan(data["prices"][..., 1]).all()
    assert np.isnan(data["cashflows"][..., 1]).all()
    assert out["recomputed"]["unused_call_price_mask"].all()
    assert out["recomputed"]["unused_call_cashflow_mask"].all()


def test_cash_empty_hedge_needs_no_unknown_call_market_input():
    data, cell = cash_fixture()
    cell.update(universe="U2", policy="none")
    cell["holdings"][:] = 0.0
    data["prices"][..., 1] = np.nan
    data["cashflows"][..., 1] = np.nan
    out = check_cash(data, cell)
    assert out["qualification"] == "verified"
    assert out["recomputed"]["discounted_pnl"][0] == pytest.approx(
        7.0 - 3.0 * np.exp(-0.05), abs=1e-12
    )


@pytest.mark.parametrize("event", [1, 2])
def test_cash_nonzero_call_trade_or_liquidation_keeps_unknown_original_path(event):
    data, cell = cash_fixture()
    data["prices"] = np.repeat(data["prices"], 2, axis=0)
    data["cashflows"] = np.repeat(data["cashflows"], 2, axis=0)
    data["payoff"] = np.repeat(data["payoff"], 2)
    cell["holdings"] = np.repeat(cell["holdings"], 2, axis=0)
    data.update(original_n=2)
    cell.update(original_n=2, universe="U2")
    data["prices"][1, event, 1] = np.nan
    out = check_cash(data, cell)
    assert out["original_path_count"] == 2
    assert out["valid_path_count"] == 1
    assert out["qualification"] == "unknown"
    assert np.isnan(out["recomputed"]["discounted_pnl"][1])
    assert not out["recomputed"]["unused_call_price_mask"][1, event]


def test_cash_no_previous_call_entitlement_ignores_unknown_interim_call_cashflow():
    data, cell = cash_fixture()
    cell["holdings"][0, 0, 1] = 0.0
    data["prices"][0, 0, 1] = np.nan
    data["cashflows"][0, 1, 1] = np.nan
    out = check_cash(data, cell)
    assert out["qualification"] == "verified"
    assert out["recomputed"]["unused_call_price_mask"][0, 0]
    assert out["recomputed"]["unused_call_cashflow_mask"][0, 1]
    data["cashflows"][0, 2, 1] = np.nan  # .2 contracts are now entitled.
    out = check_cash(data, cell)
    assert out["qualification"] == "unknown"
    assert not out["recomputed"]["unused_call_cashflow_mask"][0, 2]


@pytest.mark.parametrize("field", ["unused_call_price_mask", "unused_call_cashflow_mask"])
def test_cash_unused_unknown_input_mask_cannot_be_forged(field):
    data, cell = cash_fixture()
    cell["holdings"][..., 1] = 0.0
    # Known valid quotes/CF are not ignored unknown-input contributions.
    cell[field] = np.ones((1, 3), dtype=bool)
    with pytest.raises(ValueError, match=field):
        check_cash(data, cell)


def test_cash_invalid_raw_target_keeps_whole_action_failure_and_separate_reason():
    data, cell = cash_fixture()
    cell["raw_holdings"] = np.array([[[np.nan, 0.0], [0.6, 0.0]]])
    cell["holdings"][:] = np.nan
    cell["point_valid"] = np.zeros((1, 2), dtype=bool)
    cell["reasons"] = np.array(["arithmetic_market/risk/policy/cash_failure"])
    cell["raw_account"] = dict(reasons=np.array(["invalid_cash_event"]))
    out = check_cash(data, cell)
    assert out["qualification"] == "unknown"
    assert out["original_path_count"] == 1
    assert out["valid_path_count"] == 0
    assert np.isnan(out["recomputed"]["discounted_pnl"]).all()
    assert out["recomputed"]["reasons"][0] == "invalid_cash_event"


def test_cash_invalid_raw_target_cannot_be_repaired_to_finite_holding():
    data, cell = cash_fixture()
    cell["raw_holdings"] = cell["holdings"].copy()
    cell["raw_holdings"][0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="raw_holdings"):
        check_cash(data, cell)


def test_cash_invalid_raw_target_failure_reason_cannot_be_erased():
    data, cell = cash_fixture()
    cell["raw_holdings"] = np.array([[[np.nan, 0.0], [0.6, 0.0]]])
    cell["holdings"][:] = np.nan
    cell["point_valid"] = np.zeros((1, 2), dtype=bool)
    cell["reasons"] = np.array([""])
    with pytest.raises(ValueError, match="reason"):
        check_cash(data, cell)


def _domain_replay_fixture(*, model="heston"):
    states = np.array([0.001, 0.01, 0.02, 0.04, 0.08, 0.16])
    thresholds = np.array([0.0, 0.4, 0.8, 1.2, 1.6, 24.0])
    dates = np.array([11 / 12])
    spots = np.array([80.0, 95.0, 105.0, 120.0])
    if model == "local":
        states = np.array([0.25, 0.5, 1.0, 2.0])
        dates = np.array([0.0, 11 / 12])
        thresholds = np.array([[0.0, 9.5, 11.0, 12.0, 13.5, 24.0], thresholds])
    t0_spots = np.array([99.8, 99.9, 99.95, 100.05, 100.1, 100.2])
    axes = dict(dates=dates, state=states, threshold=thresholds)
    if model == "local":
        axes.update(spot=spots, t0_spot=t0_spots)
    rows = []
    for j, date in enumerate(dates):
        date_spots = t0_spots if date == 0 else spots
        for spot in date_spots if model == "local" else [100.0]:
            for state in states:
                raw, p, surface = primitives(model=model, state=state, spot=spot, date=date)
                rows.append(
                    dict(
                        primitives=raw,
                        thresholds=thresholds[j] if thresholds.ndim == 2 else thresholds,
                        date_index=j,
                        global_driver_id="fixed-domain-global",
                        driver_mapping=dict(
                            original_n=32,
                            global_steps=768,
                            start_step=round(date * 768),
                            stop_step=768,
                            aggregation_factor=64,
                        ),
                        surface=surface,
                    )
                )
    return rows, p, axes


def test_rebuild_fixed_domain_retains_full_original_nodes_and_unknown_tail_without_rng(monkeypatch):
    from hullkit._dynamic_hedging_surfaces import evaluate_asian

    rows, p, axes = _domain_replay_fixture()
    domain = [{"state": [1, 5], "threshold": [0, 4]}]
    original_tail = replay_teacher(rows[0]["primitives"], axes["threshold"], p, None)
    assert original_tail["labels"]["status"][-1] == "unknown_underresolved"

    def forbidden(*args, **kwargs):
        raise AssertionError("domain replay must not regenerate drivers or teachers")

    import hullkit._dynamic_hedging_conditional as conditional

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    monkeypatch.setattr(conditional, "teacher_primitives", forbidden)
    got = rebuild_asian_cache(iter(rows), p, axes, model="heston", evaluation_domains=domain)
    cache = got["cache"]
    assert got["original_path_count"] == 32
    assert got["original_group_count"] == got["saved_group_count"] == 6
    assert got["qualification"] == "unknown"
    assert cache["f"].shape == (1, 6, 6)
    assert cache["block_means"].shape == (1, 6, 6, 16, 3)
    assert np.isnan(cache["f"][0, 0, -1])
    assert cache["state_nodes"] == pytest.approx(axes["state"])
    assert cache["threshold_nodes"][0] == pytest.approx(axes["threshold"])
    assert cache["evaluation_domain_schema"] == "rb-f04-asian-fixed-domain-v1"
    assert cache["evaluation_domains"] == [{"state": [1, 5], "threshold": [0, 4]}]
    assert cache["evaluation_domain_sheets"] == ["main"]
    value = evaluate_asian(cache, 0, 100.0, 0.04, 1100.0, 11)
    assert value["status"] == "ok"
    # At x=0 the claim is exactly linear, independently of the domain geometry.
    linear = evaluate_asian(cache, 0, 100.0, np.nan, 1200.0, 11)
    assert linear["value"] == pytest.approx(100.0 / 12, abs=2e-12)
    group = cache["primitive_groups"]["groups"][0]
    assert group["status"][-1] == "unknown_underresolved"
    assert group["original_path_count"] == 32
    assert group["blocks"] == 16
    assert all(
        np.asarray(v).shape[:1] != (32,) for v in group.values() if isinstance(v, np.ndarray)
    )


def test_rebuild_domain_descriptor_is_detached_and_explicit_none_never_uses_default():
    from hullkit._dynamic_hedging_surfaces import evaluate_asian

    rows, p, axes = _domain_replay_fixture()
    domains = [{"state": [1, 5], "threshold": [0, 4]}]
    got = rebuild_asian_cache(rows, p, axes, model="heston", evaluation_domains=domains)
    domains[0]["state"][0] = 0
    assert got["cache"]["evaluation_domains"] == [{"state": [1, 5], "threshold": [0, 4]}]
    absent = rebuild_asian_cache(rows, p, axes, model="heston", evaluation_domains=[None])
    assert absent["cache"]["evaluation_domains"] == [None]
    assert evaluate_asian(absent["cache"], 0, 100.0, 0.04, 1100.0, 11)["reason"] == (
        "no_evaluation_domain"
    )
    legacy = rebuild_asian_cache(rows, p, axes, model="heston")
    assert "evaluation_domains" not in legacy["cache"]


def test_rebuild_saved_domain_compares_full_arrays_with_tolerance_without_qualification():
    import copy

    rows, p, axes = _domain_replay_fixture()
    domains = [{"state": [1, 5], "threshold": [0, 4]}]
    saved = rebuild_asian_cache(rows, p, axes, model="heston", evaluation_domains=domains)["cache"]
    perturbed = copy.deepcopy(saved)
    perturbed["f"] += 1e-12
    perturbed["block_means"] += 1e-12
    out = rebuild_asian_cache(
        iter(rows),
        p,
        axes,
        model="heston",
        evaluation_domains=domains,
        saved_cache=perturbed,
    )
    assert out["integrity"] == "pass"
    assert out["qualification"] == "unknown"
    assert out["cache"]["f"] == pytest.approx(saved["f"], nan_ok=True)
    assert out["cache"]["block_means"] == pytest.approx(saved["block_means"], nan_ok=True)


@pytest.mark.parametrize(
    "tamper",
    [
        "domain",
        "noninteger_domain",
        "schema",
        "sheet",
        "bounds",
        "original_N",
        "state_nodes",
        "dates",
        "outside_mean",
        "inside_block",
        "outside_block",
        "group_status",
        "group_count",
    ],
)
def test_rebuild_rejects_misbound_saved_domain_or_full_evidence(tamper):
    import copy

    rows, p, axes = _domain_replay_fixture()
    domains = [{"state": [1, 5], "threshold": [0, 4]}]
    saved = copy.deepcopy(
        rebuild_asian_cache(rows, p, axes, model="heston", evaluation_domains=domains)["cache"]
    )
    if tamper == "domain":
        saved["evaluation_domains"][0]["state"] = [0, 4]
    elif tamper == "noninteger_domain":
        saved["evaluation_domains"][0]["state"][0] = 1.00000000001
    elif tamper == "schema":
        saved["evaluation_domain_schema"] = "other-domain-schema"
    elif tamper == "sheet":
        saved["evaluation_domain_sheets"][0] = "t0_sheet"
    elif tamper == "bounds":
        saved["evaluation_domain_bounds"][0]["state"][0] += 0.001
    elif tamper == "original_N":
        saved["original_N"] = 16
    elif tamper == "state_nodes":
        saved["state_nodes"][0] += 0.0001
    elif tamper == "dates":
        saved["dates"][0] -= 1 / 12
    elif tamper == "outside_mean":
        saved["f"][0, 0, -1] = 0.0
    elif tamper == "inside_block":
        saved["block_means"][0, 2, 2, 0, 2] += 0.01
    elif tamper == "outside_block":
        saved["block_means"][0, 0, -1, 0, 2] = 0.0
    elif tamper == "group_status":
        saved["primitive_groups"]["groups"][0]["status"][-1] = "ready"
    elif tamper == "group_count":
        saved["primitive_groups"]["groups"].pop()
    with pytest.raises(ValueError, match="saved_cache"):
        rebuild_asian_cache(
            rows, p, axes, model="heston", evaluation_domains=domains, saved_cache=saved
        )


def test_rebuild_saved_legacy_missing_or_null_domain_metadata_is_compatible():
    import copy

    rows, p, axes = _domain_replay_fixture()
    legacy = rebuild_asian_cache(rows, p, axes, model="heston")["cache"]
    assert rebuild_asian_cache(rows, p, axes, model="heston", saved_cache=legacy)["integrity"] == (
        "pass"
    )
    nulls = copy.deepcopy(legacy)
    for key in (
        "evaluation_domains",
        "evaluation_domain_schema",
        "evaluation_domain_bounds",
        "evaluation_domain_sheets",
    ):
        nulls[key] = None
    assert rebuild_asian_cache(rows, p, axes, model="heston", saved_cache=nulls)["integrity"] == (
        "pass"
    )
    fixed = rebuild_asian_cache(
        rows,
        p,
        axes,
        model="heston",
        evaluation_domains=[{"state": [1, 5], "threshold": [0, 4]}],
    )["cache"]
    with pytest.raises(ValueError, match="saved_cache"):
        rebuild_asian_cache(rows, p, axes, model="heston", saved_cache=fixed)
    with pytest.raises(ValueError, match="saved_cache"):
        rebuild_asian_cache(
            rows,
            p,
            axes,
            model="heston",
            evaluation_domains=[{"state": [1, 5], "threshold": [0, 4]}],
            saved_cache=legacy,
        )


def test_rebuild_saved_local_domain_uses_t0_sheet_and_all_original_groups():
    from hullkit._dynamic_hedging_surfaces import evaluate_asian

    rows, p, axes = _domain_replay_fixture(model="local")
    domains = [
        {"spot": [1, 5], "state": [0, 4], "threshold": [1, 5]},
        {"spot": [0, 4], "state": [0, 4], "threshold": [0, 4]},
    ]
    first = rebuild_asian_cache(rows, p, axes, model="local", evaluation_domains=domains)
    again = rebuild_asian_cache(
        iter(rows),
        p,
        axes,
        model="local",
        evaluation_domains=domains,
        saved_cache=first["cache"],
    )
    assert again["qualification"] == "unknown"
    assert again["original_group_count"] == again["saved_group_count"] == 40
    assert again["cache"]["original_N"] == 32
    assert again["cache"]["evaluation_domain_sheets"] == ["t0_sheet", "main"]
    assert again["cache"]["t0_sheet"]["spot_nodes"] == pytest.approx(axes["t0_spot"])
    assert again["cache"]["t0_sheet"]["block_means"].shape == (6, 4, 6, 16, 3)
    assert again["cache"]["f"].shape == (2, 4, 4, 6)
    assert evaluate_asian(again["cache"], 0, 99.8, 1.0, 0.0, 0)["reason"] == (
        "outside_evaluation_domain"
    )

    inside = evaluate_asian(again["cache"], 0, 99.95, 1.0, 0.0, 0)
    assert inside["status"] == "ok"
    assert np.isfinite(inside["covariance"]).all()


def test_rebuild_compares_original_generated_cache_with_full_label_evidence():
    from hullkit._dynamic_hedging_surfaces import build_asian_cache

    rows, p, axes = _domain_replay_fixture()
    groups = []
    for row in rows:
        labels = primitive_labels(row["primitives"], row["thresholds"], blocks=16)
        labels["date_index"] = row["date_index"]
        labels["shared_driver_id"] = row["global_driver_id"]
        groups.append(labels)
    domains = [{"state": [1, 5], "threshold": [0, 4]}]
    generated = build_asian_cache(
        {"groups": groups, "parameters": p, "N": 32},
        model="heston",
        axes=axes,
        evaluation_domains=domains,
    )
    got = rebuild_asian_cache(
        rows,
        p,
        axes,
        model="heston",
        evaluation_domains=domains,
        saved_cache=generated,
    )
    assert got["integrity"] == "pass"
    assert got["qualification"] == "unknown"
    assert got["cache"]["original_N"] == 32
    assert got["cache"]["evaluation_domains"] == [{"state": [1, 5], "threshold": [0, 4]}]
    assert len(got["cache"]["primitive_groups"]["groups"]) == 6
