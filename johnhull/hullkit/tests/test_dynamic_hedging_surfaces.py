"""Dynamic cache financial and support contracts on small synthetic grids."""

import importlib.util
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from hullkit._dynamic_hedging_surfaces import (
    build_asian_cache,
    build_call_cache,
    evaluate_asian,
    evaluate_call,
    fit_quote_state,
    normalized_price_greeks,
)
from hullkit._heston_local_surface import HestonParameters, LocalVarianceGrid
from scipy.special import ndtr

P = HestonParameters(100.0, 0.03, 0.0, 0.04, 2.0, 0.04, 0.0, -0.7)


def call_fixture(curve):
    spots = np.array([80.0, 95.0, 105.0, 120.0])
    states = np.array([0.25, 0.5, 1.0, 2.0, 4.0])
    values = 0.3 * (spots[:, None] - 100) + curve(states)[None, :]
    return {
        "model": "local",
        "dates": np.array([0.0]),
        "spot_nodes": spots,
        "state_nodes": states,
        "values": values[None],
        "rate": 0.03,
        "dividend_yield": 0.0,
        "strike": 100.0,
        "maturity": 1.25,
        "derivative_error": 0.0,
        "price_error": 0.0,
    }


def test_node_derivatives_and_spot_refit():
    cache = call_fixture(lambda w: 5 + 3 * w + 0.1 * w**3)
    got = evaluate_call(cache, 0, 100.0, 1.0)
    assert got["value"] == pytest.approx(8.1)
    assert got["spot_derivative"] == pytest.approx(0.3)
    assert got["state_derivative"] == pytest.approx(3.3)
    fit = fit_quote_state(cache, 0, 100.0, 8.1, state_scale=1.0)
    assert fit["status"] == "ok"
    assert fit["state"] == pytest.approx(1.0)
    h = 1e-3
    up = fit_quote_state(cache, 0, 100 + h, 8.1, state_scale=1.0)
    dn = fit_quote_state(cache, 0, 100 - h, 8.1, state_scale=1.0)
    assert (up["state"] - dn["state"]) / (2 * h) == pytest.approx(-0.3 / 3.3, rel=1e-5)


@pytest.mark.parametrize(
    "curve,quote,reason",
    [
        (lambda w: 10 + (w - 0.6) * (w - 1.2) * (w - 3), 10.0, "nonunique"),
        (lambda w: 10 + (w - 1.0) ** 2, 10.0, "ill_conditioned"),
        (lambda w: 10 + w, 30.0, "no_root"),
        (lambda w: 10 + w, 10.25, "bound"),
    ],
)
def test_quote_fit_rejects_each_failure(curve, quote, reason):
    got = fit_quote_state(call_fixture(curve), 0, 100.0, quote, state_scale=1.0)
    assert got["status"] == "unknown"
    assert got["reason"] == reason
    assert np.isnan(got["state"])


def test_local_normalized_spot_chain():
    got = normalized_price_greeks(
        100.0, 0.97, 1.2, 1.4, -0.3, 0.2, model="local", state=2.0, f_log_spot=0.1
    )
    assert got["spot_derivative"] == pytest.approx(0.97 * (1.4 + 0.1 + 1.2 * 0.3) / 12)
    assert got["state_derivative"] == pytest.approx(0.97 * 100 * 0.2 / (12 * 2))


def asian_fixture(model):
    dates = np.array([0.0, 0.5])
    v = np.array([0.01, 0.02, 0.04, 0.08])
    x = np.array([0.0, 3.0, 8.0, 24.0])
    axes = {"dates": dates, "state": v, "threshold": x}
    if model == "local":
        axes["spot"] = np.array([80.0, 95.0, 105.0, 120.0])
        z, w, xx = np.meshgrid(np.log(axes["spot"]), np.log(v), x, indexing="ij")
        f = 3 + 0.1 * z + 0.2 * w - 0.03 * xx
    else:
        w, xx = np.meshgrid(v, x, indexing="ij")
        f = 3 + 2 * w - 0.03 * xx
    f = np.stack([f, f])
    blocks = np.broadcast_to(f[..., None, None], (*f.shape, 16, 3)).copy()
    return build_asian_cache(
        {"f": f, "block_means": blocks, "parameters": P, "N": 32}, model=model, axes=axes
    )


@pytest.mark.parametrize("model", ["heston", "local"])
def test_same_asian_surface_derivatives_blocks_and_linear(model):
    cache = asian_fixture(model)
    s, state, a, n = 100.0, 0.04, 600.0, 6
    got = evaluate_asian(cache, 1, s, state, a, n)
    h = 1e-3
    up = evaluate_asian(cache, 1, s + h, state, a, n)
    dn = evaluate_asian(cache, 1, s - h, state, a, n)
    assert got["status"] == "ok"
    assert got["spot_derivative"] == pytest.approx((up["value"] - dn["value"]) / (2 * h), rel=1e-7)
    assert got["block_values"].shape == (16, 3)
    assert got["standard_errors"][0] < 1e-12
    linear = evaluate_asian(cache, 1, s, np.nan, 1300.0, n)
    expected = (
        np.exp(-0.03 * 0.5) * (1300 + s * np.exp(0.03 * np.arange(1, 7) / 12).sum() - 1200) / 12
    )
    assert linear["status"] == "not_required_linear_claim"
    assert linear["value"] == pytest.approx(expected)
    assert linear["state_derivative"] == 0.0


def test_no_time_interpolation_or_axis_extrapolation():
    cache = call_fixture(lambda w: 5 + 3 * w)
    assert evaluate_call(cache, 0.5, 100.0, 1.0)["reason"] == "date_index"
    assert evaluate_call(cache, 0, 130.0, 1.0)["reason"] == "outside_support"
    with pytest.raises(ValueError, match="four"):
        build_asian_cache(
            {"f": np.zeros((1, 3, 4)), "parameters": P},
            model="heston",
            axes={"dates": [0.0], "state": [0.01, 0.04, 0.1], "threshold": [0.0, 1.0, 2.0, 24.0]},
        )


def test_heston_call_uses_current_variance_and_remaining_maturity():
    spots = np.array([80.0, 95.0, 105.0, 120.0])
    v = np.array([0.01, 0.02, 0.04, 0.08])
    cache = build_call_cache(
        P, None, dates=[0.0, 0.5], spot_nodes=spots, state_nodes=v, model="heston"
    )
    p = replace(P, spot=95.0, v0=0.08)
    iv = p.integrated_variance(0.75)
    d1 = (np.log(95 / 100) + (0.03 * 0.75) + iv / 2) / np.sqrt(iv)
    expected = 95 * ndtr(d1) - 100 * np.exp(-0.03 * 0.75) * ndtr(d1 - np.sqrt(iv))
    assert evaluate_call(cache, 1, 95.0, 0.08)["value"] == pytest.approx(expected, abs=1e-10)


def test_local_call_keeps_absolute_calendar_coefficients():
    surface = LocalVarianceGrid(
        np.array([0.001, 0.5, 1.0, 1.25]),
        np.array([-20.0, 20.0]),
        np.array([[0.02, 0.02], [0.04, 0.04], [0.08, 0.08], [0.12, 0.12]]),
        P,
    )
    cache = build_call_cache(
        P,
        surface,
        dates=[0.0, 0.5, 1.0],
        spot_nodes=[80.0, 95.0, 105.0, 120.0],
        state_nodes=[0.25, 0.5, 1.0, 2.0],
        model="local",
    )
    # After .5, integral is .03+.025=.055; a reset would use early .02-.04 coefficients.
    iv = 0.055
    s, tau = 105.0, 0.75
    d1 = (np.log(s / 100) + 0.03 * tau + iv / 2) / np.sqrt(iv)
    expected = s * ndtr(d1) - 100 * np.exp(-0.03 * tau) * ndtr(d1 - np.sqrt(iv))
    assert evaluate_call(cache, 1, s, 1.0)["value"] == pytest.approx(expected, abs=0.035)
    assert cache["coefficient_min_times"][1] > 0.0


def test_independent_reference_calendar_snapshots_and_refinement():
    path = (
        Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging/reference_methods.py"
    )
    spec = importlib.util.spec_from_file_location("dynamic_reference", path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)

    def variance(t, s):
        return {"variance": np.full_like(s, 0.04 + 0.04 * t), "status": "interior"}

    result = ref.calendar_call_snapshots(
        100.0, 100.0, 1.25, variance, 0.03, 0.0, [0.0, 0.5, 1.0], space_nodes=151, time_steps=120
    )
    assert result["supported"]
    assert result["values"].shape == (3, 151)
    selected = ref.selected_call_refinement(
        P, None, model="heston", date=0.5, spot=100.0, state=0.04
    )
    assert selected["status"] == "measured"
    assert selected["price_error"] < 1e-8


def test_group_blocks_and_original_denominator_are_not_independent_nodes():
    states = np.array([0.01, 0.02, 0.04, 0.08])
    thresholds = np.array([0.0, 3.0, 8.0, 24.0])
    groups = []
    for v in states:
        f = 3 + 2 * v - 0.03 * thresholds
        block = np.broadcast_to(f[None, :, None], (16, 4, 3)).copy()
        block[:, :, 2] += np.arange(16)[:, None] * 0.001
        groups.append(
            {
                "date_index": 0,
                "spot": 100.0,
                "state": v,
                "thresholds": thresholds,
                "f": block[:, :, 2].mean(axis=0),
                "block_means": block,
                "N": 32,
                "shared_driver_id": "shared",
                "status": np.full(4, "ready"),
                "calendar_times": np.array([0.0, 1.0]),
                "memory_count": 0,
            }
        )
    axes = {"dates": [0.0], "state": states, "threshold": thresholds}
    cache = build_asian_cache({"groups": groups, "parameters": P}, model="heston", axes=axes)
    assert cache["original_N"] == 32
    got = evaluate_asian(cache, 0, 100.0, 0.04, 0.0, 0)
    expected = np.std(np.arange(16) * 0.001, ddof=1) / 4 * 100 * np.exp(-0.03) / 12
    assert got["standard_errors"][0] == pytest.approx(expected)
    groups[-1]["N"] = 64
    with pytest.raises(ValueError, match="denominator"):
        build_asian_cache({"groups": groups, "parameters": P}, model="heston", axes=axes)
    groups[-1]["N"] = 32
    groups[-1]["memory_count"] = 6
    with pytest.raises(ValueError, match="memory"):
        build_asian_cache({"groups": groups, "parameters": P}, model="heston", axes=axes)


def test_dedicated_t0_sheet_and_vector_unknown_statuses():
    cache = asian_fixture("local")
    near = np.array([99.9, 99.95, 100.05, 100.1])
    f = np.broadcast_to(np.full((4, 4, 4), 2.0), (4, 4, 4)).copy()
    cache["t0_sheet"] = {
        "spot_nodes": near,
        "f": f,
        "block_means": np.broadcast_to(f[..., None, None], (*f.shape, 16, 3)).copy(),
    }
    got = evaluate_asian(cache, 0, 100.0, 0.04, 0.0, 0)
    assert got["value"] == pytest.approx(100 * np.exp(-0.03) * 2 / 12)
    assert evaluate_asian(cache, 0, 80.0, 0.04, 0.0, 0)["reason"] == "outside_t0_support"
    vector = evaluate_asian(cache, 0, [100.0, 80.0], [0.04, 0.04], [0.0, 0.0], [0, 0])
    assert vector["status"].tolist() == ["ok", "unknown"]
    assert vector["block_values"].shape == (2, 16, 3)


def test_fit_intersection_vector_inputs_and_independent_j_uncertainty():
    cache = call_fixture(lambda w: 5 + 3 * w)
    cache["asian_state_bounds"] = (0.5, 2.0)
    fits = fit_quote_state(
        cache, 0, np.array([100.0, 100.0]), np.array([8.0, 14.0]), state_scale=1.0
    )
    assert fits["status"].tolist() == ["ok", "unknown"]
    assert fits["reason"][1] == "no_root"
    cache["derivative_error"] = 1.1
    assert (
        fit_quote_state(cache, 0, 100.0, 8.0, state_scale=1.0)["reason"] == "derivative_uncertainty"
    )


def test_direct_independent_one_fixing_price_and_crn_greeks():
    path = (
        Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging/reference_methods.py"
    )
    spec = importlib.util.spec_from_file_location("dynamic_reference_mc", path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    t = 11 / 12
    result = ref.direct_conditional_asian(
        P,
        None,
        model="heston",
        calendar_times=np.linspace(t, 1.0, 17),
        fixing_indices=np.array([16]),
        spot=100.0,
        state=0.04,
        memory_sum=1100.0,
        memory_count=11,
        seed=17,
        n_paths=4096,
    )
    tau = 1 - t
    d1 = (0.03 * tau + 0.04 * tau / 2) / np.sqrt(0.04 * tau)
    price = (100 * ndtr(d1) - 100 * np.exp(-0.03 * tau) * ndtr(d1 - np.sqrt(0.04 * tau))) / 12
    delta = ndtr(d1) / 12
    assert result["N"] == 4096
    assert result["mean"][0] == pytest.approx(price, abs=6 * result["standard_errors"][0])
    assert result["mean"][1] == pytest.approx(delta, abs=6 * result["standard_errors"][1])


def test_actual_stochastic_heston_cf_and_state_coordinate_invariance():
    p = replace(P, xi=0.3)
    cache = build_call_cache(
        p,
        None,
        dates=[0.5],
        spot_nodes=[80.0, 95.0, 105.0, 120.0],
        state_nodes=[0.01, 0.02, 0.04, 0.08],
        model="heston",
    )
    path = (
        Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging/reference_methods.py"
    )
    spec = importlib.util.spec_from_file_location("dynamic_reference_cf", path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    truth = ref.independent_heston_call([100.0], 0.75, replace(p, spot=105.0, v0=0.04))[0]
    assert evaluate_call(cache, 0, 105.0, 0.04)["value"] == pytest.approx(truth, abs=1e-8)
    # An invertible theta=u^2 change is represented exactly in both cubic fixtures.
    theta = np.array([0.25, 0.5, 1.0, 2.0, 4.0])
    physical = call_fixture(lambda v: 5 + 3 * v)
    changed = {**physical, "state_nodes": np.sqrt(theta)}
    fit1 = fit_quote_state(physical, 0, 100.0, 8.0, state_scale=1.0)
    fit2 = fit_quote_state(changed, 0, 100.0, 8.0, state_scale=1.0)
    assert fit2["state"] ** 2 == pytest.approx(fit1["state"])
    vtheta, vcoordinate = 0.4, 0.8
    assert vtheta / fit1["Ctheta"] == pytest.approx(vcoordinate / fit2["Ctheta"])


def test_independent_zero_xi_uses_exact_nonstationary_variance_transition():
    """Own payoff replay separates the exact xi=0 transition from Lamperti bias."""
    path = (
        Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging/reference_methods.py"
    )
    spec = importlib.util.spec_from_file_location("dynamic_reference_zero_xi", path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    times = np.array([11 / 12, 23 / 24, 1.0])
    seed, n_paths, initial_v = 41, 32, 0.08
    result = ref.direct_conditional_asian(
        P,
        None,
        model="heston",
        calendar_times=times,
        fixing_indices=np.array([2]),
        spot=100.0,
        state=initial_v,
        memory_sum=1100.0,
        memory_count=11,
        seed=seed,
        n_paths=n_paths,
    )
    rng = np.random.default_rng(seed)
    stock = np.full(n_paths, 100.0)
    variance = initial_v
    for dt in np.diff(times):
        zs = rng.standard_normal((n_paths, 2))[:, 0]
        stock *= np.exp(
            (P.rate - P.dividend_yield - variance / 2) * dt + np.sqrt(variance * dt) * zs
        )
        variance = P.theta + (variance - P.theta) * np.exp(-P.kappa * dt)
    expected = np.exp(-P.rate * (1 - times[0])) * np.maximum((1100 + stock) / 12 - 100.0, 0.0)
    assert result["status"] == "measured"
    assert result["original_path_count"] == n_paths
    np.testing.assert_allclose(result["samples"][:, 0], expected, rtol=0.0, atol=1e-14)


def test_independent_adaptive_integral_failure_keeps_receipt_and_is_unknown():
    path = (
        Path(__file__).resolve().parents[2] / "research/RB-F04/dynamic_hedging/reference_methods.py"
    )
    spec = importlib.util.spec_from_file_location("dynamic_reference_quad_failure", path)
    ref = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ref)
    p = replace(P, xi=0.3)
    result = ref.independent_heston_call([100.0], 0.75, p, quadrature_limit=1, return_receipt=True)
    assert result["status"] == "unknown"
    assert np.isfinite(result["raw_prices"][0])
    assert np.isnan(result["price"][0])
    assert result["price_unit_error"][0] > 0
    for integral in result["integration_receipts"][0]:
        assert integral["status"] == "nonconverged"
        assert integral["message"]
        assert integral["neval"] > 0
        assert integral["absolute_error"] > 0
    selected = ref.selected_call_refinement(
        p, None, model="heston", date=0.5, spot=100.0, state=0.04, quadrature_limit=1
    )
    assert selected["status"] == "unknown"
    assert selected["integration_receipts"]
