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


def test_default_local_call_late_atm_meets_absolute_price_budget():
    surface = LocalVarianceGrid(
        np.array([1 / 4096, 1.25]), np.array([-20.0, 20.0]), np.full((2, 2), 0.04), P
    )
    date = 11 / 12
    cache = build_call_cache(
        P,
        surface,
        dates=[date],
        spot_nodes=[80.0, 100.0, 110.0, 120.0],
        state_nodes=[0.25, 0.5, 1.0, 2.0],
        model="local",
    )
    remaining = 1.25 - date
    sd = np.sqrt(0.04 * remaining)
    d1 = (P.rate * remaining + sd**2 / 2) / sd
    independent = 100.0 * ndtr(d1) - 100.0 * np.exp(-P.rate * remaining) * ndtr(d1 - sd)
    measured = evaluate_call(cache, 0, 100.0, 1.0)
    assert measured["value"] == pytest.approx(independent, abs=0.001)
    # A finite solve alone does not measure actual-field derivative error.
    assert cache["reference_status"] == "unmeasured"
    assert np.isnan(cache["derivative_error"])


def fixed_domain_fixture(model="heston", *, domains=None):
    """Nonuniform polynomial curves with correlated original sixteen blocks."""
    dates = np.array([0.0, 0.5])
    thresholds = np.array([0.0, 3.0, 8.0, 16.0, 24.0])
    states = (
        np.array([0.01, 0.02, 0.04, 0.06, 0.08])
        if model == "heston"
        else np.array([0.25, 0.5, 1.0, 2.0, 4.0])
    )
    axes = {"dates": dates, "state": states, "threshold": thresholds}
    offset = (np.arange(16) - 7.5) * 0.001

    def curves(spots=None):
        if model == "local":
            z, state, x = np.meshgrid(np.log(spots), np.log(states), thresholds, indexing="ij")
            f = 3.0 + 0.1 * z + 0.2 * state - 0.03 * x
            noise = 1.0 + 0.02 * z + 0.05 * state + 0.01 * x
        else:
            state, x = np.meshgrid(states, thresholds, indexing="ij")
            f = (
                3.0
                + 2.0 * state
                + 0.7 * state**2
                + 10.0 * state**3
                - 0.025 * x
                + 0.0004 * x**2
                - 2e-6 * x**3
                + 0.01 * state * x
            )
            noise = 1.0 + 2.0 * state + 0.01 * x
        block = np.broadcast_to(f[..., None, None], (*f.shape, 16, 3)).copy()
        block[..., 2] += noise[..., None] * offset
        return f, block

    if model == "local":
        axes["spot"] = np.array([80.0, 90.0, 100.0, 110.0, 120.0, 140.0])
        axes["t0_spot"] = np.array([99.5, 99.75, 100.0, 100.25, 100.5])
        f, blocks = curves(axes["spot"])
        t0_f, t0_blocks = curves(axes["t0_spot"])
    else:
        f, blocks = curves()
    raw = {
        "parameters": P,
        "N": 32,
        "f": np.stack([f, f]),
        "block_means": np.stack([blocks, blocks]),
    }
    if model == "local":
        raw.update(t0_f=t0_f, t0_block_means=t0_blocks)
    return build_asian_cache(raw, model=model, axes=axes, evaluation_domains=domains)


def fixed_domain(model="heston"):
    """One declared four-or-more-node box per date, never selected per query."""
    if model == "heston":
        return [
            {"state": [0, 4], "threshold": [0, 4]},
            {"state": [0, 4], "threshold": [0, 4]},
        ]
    return [
        {"spot": [0, 4], "state": [1, 5], "threshold": [0, 4]},
        {"spot": [1, 5], "state": [1, 5], "threshold": [0, 4]},
    ]


@pytest.mark.parametrize("model", ["heston", "local"])
def test_fixed_domain_full_axes_matches_unchanged_default(model):
    original = fixed_domain_fixture(model)
    domains = [
        {"state": [0, 5], "threshold": [0, 5]},
        {"state": [0, 5], "threshold": [0, 5]},
    ]
    if model == "local":
        domains[0]["spot"] = [0, 5]
        domains[1]["spot"] = [0, 6]
    selected = fixed_domain_fixture(model, domains=domains)
    state = 0.04 if model == "heston" else 1.1
    for date, memory, count in [(0, 0.0, 0), (1, 600.0, 6)]:
        old = evaluate_asian(original, date, 100.0, state, memory, count)
        new = evaluate_asian(selected, date, 100.0, state, memory, count)
        assert old["status"] == new["status"] == "ok"
        for key in [
            "value",
            "spot_derivative",
            "state_derivative",
            "block_values",
            "covariance",
            "standard_errors",
        ]:
            np.testing.assert_allclose(new[key], old[key], rtol=1e-12, atol=1e-12)
    assert "evaluation_domains" not in original
    assert selected["evaluation_domain_schema"] == "rb-f04-asian-fixed-domain-v1"
    assert selected["interpolation"] == original["interpolation"]


@pytest.mark.parametrize("model", ["heston", "local"])
def test_fixed_domain_far_nan_does_not_erase_original_nodes(model):
    cache = fixed_domain_fixture(model, domains=fixed_domain(model))
    original_f = cache["f"].copy()
    original_blocks = cache["block_means"].copy()
    cache["f"][1, ..., -1] = np.nan
    cache["block_means"][1, ..., -1, :, :] = np.nan
    state = 0.04 if model == "heston" else 1.1
    got = evaluate_asian(cache, 1, 101.0, state, 600.0, 6)
    assert got["status"] == "ok"
    assert cache["original_N"] == cache["primitive_groups"]["N"] == 32
    assert cache["threshold_nodes"].shape == (2, 5)
    assert cache["f"].shape == original_f.shape
    assert cache["block_means"].shape == original_blocks.shape
    assert np.isnan(cache["f"][1, ..., -1]).all()
    assert cache["primitive_groups"]["f"].shape == original_f.shape
    default = fixed_domain_fixture(model)
    default["f"][1, ..., -1] = np.nan
    assert evaluate_asian(default, 1, 101.0, state, 600.0, 6)["reason"] == "nonfinite_nodes"


def independent_domain_value(cache, date, spot, state, memory, *, derivative=None, blocks=False):
    """Direct reverse-axis SciPy interpolation independent of production basis."""
    from scipy.interpolate import CubicSpline

    domain = cache["evaluation_domains"][date]
    local = cache["model"] == "local"
    sheet = cache["t0_sheet"] if local and cache["dates"][date] == 0 else None
    raw = (
        sheet["block_means"][..., 2]
        if blocks and sheet is not None
        else cache["block_means"][date, ..., 2]
        if blocks
        else sheet["f"]
        if sheet is not None
        else cache["f"][date]
    )
    names = (["spot"] if local else []) + ["state", "threshold"]
    selected = raw[tuple(slice(*domain[name]) for name in names)]
    threshold = cache["threshold_nodes"][date][slice(*domain["threshold"])]
    state_axis = cache["state_nodes"][slice(*domain["state"])]
    point_x = (1200.0 - memory) / spot
    value = CubicSpline(threshold, selected, axis=len(names) - 1, extrapolate=False)(
        point_x, int(derivative == "threshold")
    )
    if local:
        value = CubicSpline(np.log(state_axis), value, axis=1, extrapolate=False)(
            np.log(state), int(derivative == "state")
        )
        spot_axis = (sheet["spot_nodes"] if sheet is not None else cache["spot_nodes"])[
            slice(*domain["spot"])
        ]
        return CubicSpline(np.log(spot_axis), value, axis=0, extrapolate=False)(
            np.log(spot), int(derivative == "spot")
        )
    return CubicSpline(state_axis, value, axis=0, extrapolate=False)(
        state, int(derivative == "state")
    )


@pytest.mark.parametrize("model", ["heston", "local"])
def test_fixed_domain_same_price_operator_greeks_and_shared_block_covariance(model):
    cache = fixed_domain_fixture(model, domains=fixed_domain(model))
    cache["f"][1, ..., -1] = np.nan
    cache["block_means"][1, ..., -1, :, :] = np.nan
    spot, state, memory = 101.0, 0.04 if model == "heston" else 1.1, 600.0
    discount = np.exp(-0.03 * 0.5)
    x = (1200.0 - memory) / spot
    f = independent_domain_value(cache, 1, spot, state, memory)
    fx = independent_domain_value(cache, 1, spot, state, memory, derivative="threshold")
    fs = independent_domain_value(cache, 1, spot, state, memory, derivative="state")
    fz = (
        independent_domain_value(cache, 1, spot, state, memory, derivative="spot")
        if model == "local"
        else 0.0
    )
    expected = np.array(
        [
            discount * spot * f / 12,
            discount * (f + fz - x * fx) / 12,
            discount * spot * fs / (12 * state if model == "local" else 12),
        ]
    )
    got = evaluate_asian(cache, 1, spot, state, memory, 6)
    np.testing.assert_allclose(
        [got[k] for k in ["value", "spot_derivative", "state_derivative"]],
        expected,
        rtol=1e-11,
        atol=1e-11,
    )
    fb = independent_domain_value(cache, 1, spot, state, memory, blocks=True)
    fxb = independent_domain_value(
        cache, 1, spot, state, memory, derivative="threshold", blocks=True
    )
    fsb = independent_domain_value(cache, 1, spot, state, memory, derivative="state", blocks=True)
    fzb = (
        independent_domain_value(cache, 1, spot, state, memory, derivative="spot", blocks=True)
        if model == "local"
        else 0.0
    )
    expected_blocks = np.stack(
        [
            discount * spot * fb / 12,
            discount * (fb + fzb - x * fxb) / 12,
            discount * spot * fsb / (12 * state if model == "local" else 12),
        ],
        axis=-1,
    )
    expected_covariance = np.cov(expected_blocks, rowvar=False, ddof=1) / 16
    np.testing.assert_allclose(got["block_values"], expected_blocks, atol=1e-11, rtol=1e-11)
    np.testing.assert_allclose(got["covariance"], expected_covariance, atol=1e-14, rtol=1e-10)
    assert abs(got["covariance"][0, 1]) > 1e-8
    for h in [0.02, 0.01, 0.005]:
        up = evaluate_asian(cache, 1, spot + h, state, memory, 6)
        down = evaluate_asian(cache, 1, spot - h, state, memory, 6)
        assert got["spot_derivative"] == pytest.approx(
            (up["value"] - down["value"]) / (2 * h), rel=1e-7, abs=1e-9
        )
    if model == "local":
        naive = discount * (f - x * fx) / 12
        assert abs(got["spot_derivative"] - naive) > 0.008
    assert np.isnan(got["error"])


@pytest.mark.parametrize(
    "damage,reason",
    [
        ("mean", "nonfinite_domain_nodes"),
        ("block", "nonfinite_domain_blocks"),
        ("negative", "domain_price_bounds"),
        ("upper", "domain_price_bounds"),
    ],
)
def test_fixed_domain_required_bad_node_is_unknown_without_repair(damage, reason):
    cache = fixed_domain_fixture(domains=fixed_domain())
    if damage == "mean":
        cache["f"][1, 1, 2] = np.nan
    elif damage == "block":
        cache["block_means"][1, 1, 2, 7, 2] = np.nan
    elif damage == "negative":
        cache["f"][1, 1, 2] = -0.001
    else:
        cache["f"][1, 1, 2] = 100.0
    before_f, before_blocks = cache["f"].copy(), cache["block_means"].copy()
    got = evaluate_asian(cache, 1, 100.0, 0.04, 600.0, 6)
    assert got["status"] == "unknown"
    assert got["reason"] == reason
    assert np.isnan(got["value"])
    assert cache["original_N"] == 32
    np.testing.assert_allclose(cache["f"], before_f, equal_nan=True)
    np.testing.assert_allclose(cache["block_means"], before_blocks, equal_nan=True)


def test_fixed_domain_unavailable_date_outside_rows_and_snapshot_are_explicit():
    domains = [None, {"state": [0, 4], "threshold": [0, 4]}]
    cache = fixed_domain_fixture(domains=domains)
    domains[1]["state"][:] = [1, 5]
    assert cache["evaluation_domains"][1]["state"] == [0, 4]
    assert evaluate_asian(cache, 0, 100.0, 0.04, 0.0, 0)["reason"] == "no_evaluation_domain"
    got = evaluate_asian(cache, 1, [100.0, 100.0], [0.04, 0.08], [600.0, 600.0], [6, 6])
    assert got["status"].tolist() == ["ok", "unknown"]
    assert got["reason"][1] == "outside_evaluation_domain"
    assert np.isnan(got["value"][1])
    assert got["block_values"].shape == (2, 16, 3)
    assert cache["original_N"] == 32
    assert cache["evaluation_domain_bounds"][1]["state"] == [0.01, 0.06]


@pytest.mark.parametrize(
    "bad",
    [
        [],
        [{"state": [0, 4], "threshold": [0, 4]}],
        [{"state": [0, 3], "threshold": [0, 4]}] * 2,
        [{"state": [-1, 4], "threshold": [0, 4]}] * 2,
        [{"state": [0, 9], "threshold": [0, 4]}] * 2,
        [{"state": [2, 2], "threshold": [0, 4]}] * 2,
        [{"state": [0, 4, 1], "threshold": [0, 4]}] * 2,
        [{"state": [0, 4], "threshold": [0, 4], "spot": [0, 4]}] * 2,
    ],
)
def test_fixed_domain_rejects_incomplete_or_noncontiguous_geometry(bad):
    with pytest.raises(ValueError, match="domain"):
        fixed_domain_fixture(domains=bad)


def test_fixed_domain_local_t0_uses_its_dedicated_spot_axis_and_all_blocks():
    cache = fixed_domain_fixture("local", domains=fixed_domain("local"))
    assert cache["evaluation_domain_sheets"] == ["t0_sheet", "main"]
    assert cache["evaluation_domain_bounds"][0]["spot"] == [99.5, 100.25]
    cache["f"][0] = np.nan
    cache["block_means"][0] = np.nan
    got = evaluate_asian(cache, 0, 100.0, 1.1, 0.0, 0)
    assert got["status"] == "ok"
    assert got["block_values"].shape == (16, 3)
    assert evaluate_asian(cache, 0, 100.5, 1.1, 0.0, 0)["reason"] == "outside_evaluation_domain"
    assert evaluate_asian(cache, 0, 120.0, 1.1, 0.0, 0)["reason"] == "outside_t0_support"
    expected = independent_domain_value(cache, 0, 100.0, 1.1, 0.0)
    assert got["value"] == pytest.approx(np.exp(-0.03) * 100.0 * expected / 12, rel=1e-12)
    for h in [0.02, 0.01, 0.005]:
        up = evaluate_asian(cache, 0, 100.0 + h, 1.1, 0.0, 0)
        down = evaluate_asian(cache, 0, 100.0 - h, 1.1, 0.0, 0)
        assert got["spot_derivative"] == pytest.approx(
            (up["value"] - down["value"]) / (2 * h), rel=1e-7
        )
    cache["t0_sheet"]["block_means"][1, 1, 2, 4, 2] = np.nan
    assert evaluate_asian(cache, 0, 100.0, 1.1, 0.0, 0)["reason"] == "nonfinite_domain_blocks"


def test_fixed_domain_linear_and_settled_do_not_require_patch_or_state():
    cache = fixed_domain_fixture(domains=[None, None])
    cache["f"][:] = np.nan
    cache["block_means"][:] = np.nan
    linear = evaluate_asian(cache, 1, 100.0, np.nan, 1300.0, 6)
    settled = evaluate_asian(cache, 1, 100.0, np.nan, 1300.0, 12)
    assert linear["status"] == "not_required_linear_claim"
    assert linear["state_derivative"] == 0.0
    assert settled["status"] == "not_required_settled_claim"
    assert settled["value"] == pytest.approx(1300.0 / 12 - 100.0)


@pytest.mark.parametrize("coordinate", [0.02, 0.04, 0.01, 0.06])
def test_fixed_domain_price_derivative_is_continuous_inside_and_one_sided_at_boundary(coordinate):
    cache = fixed_domain_fixture(domains=fixed_domain())
    got = evaluate_asian(cache, 1, 100.0, coordinate, 600.0, 6)
    assert got["status"] == "ok"
    for h in [1e-5, 5e-6, 2.5e-6]:
        if coordinate == 0.01:
            neighbour = evaluate_asian(cache, 1, 100.0, coordinate + h, 600.0, 6)
            derivative = (neighbour["value"] - got["value"]) / h
        elif coordinate == 0.06:
            neighbour = evaluate_asian(cache, 1, 100.0, coordinate - h, 600.0, 6)
            derivative = (got["value"] - neighbour["value"]) / h
        else:
            up = evaluate_asian(cache, 1, 100.0, coordinate + h, 600.0, 6)
            down = evaluate_asian(cache, 1, 100.0, coordinate - h, 600.0, 6)
            derivative = (up["value"] - down["value"]) / (2 * h)
            assert up["state_derivative"] == pytest.approx(
                down["state_derivative"], rel=1e-4, abs=5e-4
            )
        assert got["state_derivative"] == pytest.approx(derivative, rel=3e-5)
    assert (
        evaluate_asian(cache, 1, 100.0, 0.0601, 600.0, 6)["reason"] == "outside_evaluation_domain"
    )


def test_fixed_domain_keeps_original_nonunique_call_roots_instead_of_rescuing_patch_root():
    states = np.array([0.25, 0.5, 0.625, 0.75, 1.0, 2.0, 4.0])
    spots = np.array([80.0, 95.0, 105.0, 120.0])
    curve = 10.0 + (states - 0.6) * (states - 1.2) * (states - 3.0)
    call = {
        "model": "local",
        "dates": np.array([0.5]),
        "spot_nodes": spots,
        "state_nodes": states,
        "values": (0.3 * (spots[:, None] - 100.0) + curve[None, :])[None],
        "rate": 0.03,
        "dividend_yield": 0.0,
        "strike": 100.0,
        "maturity": 1.25,
        "derivative_error": 0.0,
    }
    threshold = np.array([0.0, 3.0, 8.0, 16.0, 24.0])
    f = np.broadcast_to(np.full((4, 7, 5), 2.0), (4, 7, 5)).copy()
    asian = build_asian_cache(
        {
            "parameters": P,
            "N": 32,
            "f": f[None],
            "block_means": np.broadcast_to(f[None, ..., None, None], (1, 4, 7, 5, 16, 3)).copy(),
        },
        model="local",
        axes={"dates": [0.5], "spot": spots, "state": states, "threshold": threshold},
        evaluation_domains=[{"spot": [0, 4], "state": [1, 5], "threshold": [0, 4]}],
    )
    fit = fit_quote_state(call, 0, 100.0, 10.0, state_scale=1.0)
    assert fit["status"] == "unknown"
    assert fit["reason"] == "nonunique"
    np.testing.assert_allclose(fit["roots"], [0.6, 1.2, 3.0], atol=1e-12)
    assert asian["evaluation_domain_bounds"][0]["state"] == [0.5, 1.0]
    assert "asian_state_bounds" not in call
    assert evaluate_asian(asian, 0, 100.0, fit["state"], 600.0, 6)["status"] == "unknown"


def test_fixed_domain_keeps_original_group_statuses_driver_and_denominator():
    states = np.array([0.01, 0.02, 0.04, 0.06, 0.08])
    threshold = np.array([0.0, 3.0, 8.0, 16.0, 24.0])
    groups = []
    for state in states:
        f = 3.0 + 2.0 * state - 0.03 * threshold
        status = np.full(5, "ready", dtype="<U40")
        status[-1] = "unknown_underresolved"
        groups.append(
            {
                "date_index": 0,
                "spot": 100.0,
                "state": state,
                "thresholds": threshold.copy(),
                "f": f.copy(),
                "N": 32,
                "block_means": np.broadcast_to(f[None, :, None], (16, 5, 3)).copy(),
                "status": status,
                "shared_driver_id": "original-global-iid",
                "calendar_times": np.array([0.5, 1.0]),
                "memory_count": 6,
            }
        )
    raw = {"groups": groups, "parameters": P, "N": 32}
    cache = build_asian_cache(
        raw,
        model="heston",
        axes={"dates": [0.5], "state": states, "threshold": threshold},
        evaluation_domains=[{"state": [0, 4], "threshold": [0, 4]}],
    )
    assert cache["primitive_groups"] is raw
    assert len(cache["primitive_groups"]["groups"]) == 5
    assert cache["original_N"] == 32
    assert cache["shared_driver_ids"] == ("original-global-iid",)
    assert cache["support_mask"].shape == (1, 5, 5)
    assert np.isnan(cache["f"][0, :, -1]).all()
    assert np.isnan(cache["block_means"][0, :, -1]).all()
    assert all(row["status"][-1] == "unknown_underresolved" for row in groups)
    assert all(np.isfinite(row["f"][-1]) for row in groups)
    assert all(row["block_means"].shape == (16, 5, 3) and row["N"] == 32 for row in groups)
    assert evaluate_asian(cache, 0, 100.0, 0.04, 600.0, 6)["status"] == "ok"


def test_fixed_domain_retains_signed_cv_blocks_instead_of_clipping_uncertainty():
    cache = fixed_domain_fixture(domains=fixed_domain())
    block_curves = cache["block_means"][1, ..., 2]
    block_curves[..., 0] -= 10.0
    block_curves[..., 1:] += 10.0 / 15.0
    original = block_curves.copy()
    np.testing.assert_allclose(block_curves.mean(axis=-1), cache["f"][1], atol=1e-12)
    got = evaluate_asian(cache, 1, 100.0, 0.04, 600.0, 6)
    assert got["status"] == "ok"
    assert got["block_values"].shape == (16, 3)
    assert got["block_values"][0, 0] < 0.0
    assert got["standard_errors"][0] > 1.0
    np.testing.assert_allclose(cache["block_means"][1, ..., 2], original)
    assert cache["original_N"] == 32


def test_fixed_domain_preserves_post_interpolation_price_derivative_bounds():
    cache = fixed_domain_fixture(domains=fixed_domain())
    values = 1.0 + 0.04 * cache["threshold_nodes"][1]
    cache["f"][1] = np.broadcast_to(values, cache["f"][1].shape)
    cache["block_means"][1] = np.broadcast_to(
        cache["f"][1, ..., None, None], cache["block_means"][1].shape
    )
    got = evaluate_asian(cache, 1, 100.0, 0.04, 600.0, 6)
    assert got["status"] == "unknown"
    assert got["reason"] == "price_bounds"
    assert got["raw_f_x"] == pytest.approx(0.04)


@pytest.mark.parametrize(
    "damage,reason",
    [
        ("nan", "nonfinite_nodes"),
        ("increasing", "price_bounds"),
    ],
)
def test_default_unknown_mean_or_bounds_preserves_original_early_rejection(damage, reason):
    cache = fixed_domain_fixture()
    if damage == "nan":
        cache["f"][1, 0, 0] = np.nan
    else:
        cache["f"][1] = np.broadcast_to(
            1.0 + 0.04 * cache["threshold_nodes"][1], cache["f"][1].shape
        )
    del cache["block_means"]
    got = evaluate_asian(cache, 1, 100.0, 0.04, 600.0, 6)
    assert got["status"] == "unknown"
    assert got["reason"] == reason
