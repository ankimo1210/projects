from __future__ import annotations

import numpy as np
from hullkit import bsm
from hullkit.surrogate_data import (
    analytic_bsm_rows,
    forward_surface_teacher,
    heston_cos_price,
    mc_black_scholes_call,
    mc_black_scholes_call_estimates,
    mc_bsm_rows,
    rbergomi_call_price,
)


def test_analytic_rows_use_common_schema():
    rows = analytic_bsm_rows(np.array([[1.0, 1.0, 0.02, 0.01, 0.2]]))
    for name in (
        "price",
        "delta",
        "gamma",
        "vega",
        "theta",
        "rho",
        "standard_error",
        "ci_lower",
        "ci_upper",
    ):
        assert rows[name].shape == (1,)
    assert rows["method"] == "analytic_bsm"


def test_mc_is_seed_addressable_and_ci_covers_reference():
    first = mc_black_scholes_call(100, 100, 0.02, 1.0, 0.2, q=0.01, n_paths=40_000, seed=7)
    second = mc_black_scholes_call(100, 100, 0.02, 1.0, 0.2, q=0.01, n_paths=40_000, seed=7)
    reference = bsm.call_price(100, 100, 0.02, 0.2, 1.0, 0.01)
    assert first == second
    assert abs(first.estimate - reference) < 4 * first.standard_error
    assert first.method == "mc_antithetic_control_variate"


def test_mc_empirical_ci_coverage_across_seeds():
    reference = bsm.call_price(100, 100, 0.02, 0.2, 1.0, 0.01)
    intervals = [
        mc_black_scholes_call(100, 100, 0.02, 1.0, 0.2, q=0.01, n_paths=8_000, seed=seed)
        for seed in range(20)
    ]
    coverage = np.mean([item.ci_lower <= reference <= item.ci_upper for item in intervals])
    assert 0.75 <= coverage <= 1.0


def test_mc_standard_error_scales_near_inverse_sqrt_n():
    small = mc_black_scholes_call(100, 105, 0.02, 1.0, 0.3, n_paths=10_000, seed=4)
    large = mc_black_scholes_call(100, 105, 0.02, 1.0, 0.3, n_paths=40_000, seed=4)
    assert 0.35 < large.standard_error / small.standard_error < 0.65


def test_mc_price_delta_and_vega_share_paths_and_cover_references():
    estimates = mc_black_scholes_call_estimates(
        100, 100, 0.02, 1.0, 0.2, q=0.01, n_paths=40_000, seed=13
    )
    references = {
        "price": bsm.call_price(100, 100, 0.02, 0.2, 1.0, 0.01),
        "delta": bsm.call_delta(100, 100, 0.02, 0.2, 1.0, 0.01),
        "vega": bsm.vega(100, 100, 0.02, 0.2, 1.0, 0.01),
    }
    results = (estimates.price, estimates.delta, estimates.vega)
    assert estimates.common_random_numbers
    assert len({item.path_stream_fingerprint for item in results}) == 1
    assert len({(item.seed, item.path_count) for item in results}) == 1
    assert all(
        abs(item.estimate - references[item.estimand]) < 4 * item.standard_error for item in results
    )


def test_mc_price_and_pathwise_greek_ci_coverage_across_seeds():
    references = {
        "price": bsm.call_price(100, 100, 0.02, 0.2, 1.0, 0.01),
        "delta": bsm.call_delta(100, 100, 0.02, 0.2, 1.0, 0.01),
        "vega": bsm.vega(100, 100, 0.02, 0.2, 1.0, 0.01),
    }
    samples = [
        mc_black_scholes_call_estimates(100, 100, 0.02, 1.0, 0.2, q=0.01, n_paths=8_000, seed=seed)
        for seed in range(20)
    ]
    for name, reference in references.items():
        coverage = np.mean(
            [
                getattr(item, name).ci_lower <= reference <= getattr(item, name).ci_upper
                for item in samples
            ]
        )
        assert 0.75 <= coverage <= 1.0


def test_mc_price_and_pathwise_greek_se_scale_at_four_times_paths():
    small = mc_black_scholes_call_estimates(100, 105, 0.02, 1.0, 0.3, n_paths=10_000, seed=4)
    large = mc_black_scholes_call_estimates(100, 105, 0.02, 1.0, 0.3, n_paths=40_000, seed=4)
    for name in ("price", "delta", "vega"):
        ratio = getattr(large, name).standard_error / getattr(small, name).standard_error
        assert 0.35 < ratio < 0.65


def test_mc_rows_do_not_reuse_analytic_greeks():
    rows = mc_bsm_rows(np.array([[1.0, 1.0, 0.02, 0.01, 0.2]]), n_paths=10_000, seed=5)
    assert rows["estimands"] == ("price", "delta", "vega")
    assert rows["unsupported_greeks"] == ("gamma", "theta", "rho")
    assert not {"gamma", "theta", "rho"} & rows.keys()
    for name in rows["estimands"]:
        assert rows[name].shape == rows[f"{name}_standard_error"].shape == (1,)
        assert rows[f"{name}_ci_lower"][0] <= rows[name][0] <= rows[f"{name}_ci_upper"][0]
        assert rows[f"{name}_standard_error"][0] > 0


def test_heston_cos_reduces_to_bsm():
    price = heston_cos_price(100, 100, 0.02, 1.0, v0=0.04, kappa=1.5, theta=0.04, xi=1e-3, rho=-0.5)
    assert abs(price - bsm.call_price(100, 100, 0.02, 0.2, 1.0)) < 2e-3


def test_rbergomi_eta_zero_reduces_to_bsm_inside_teacher_ci():
    estimate = rbergomi_call_price(
        100,
        100,
        0.02,
        1.0,
        xi0=0.04,
        eta=0.0,
        hurst=0.1,
        rho=-0.7,
        n_steps=24,
        n_paths=12_000,
        seed=19,
    )
    reference = bsm.call_price(100, 100, 0.02, 0.2, 1.0)
    assert abs(estimate.estimate - reference) < 4 * estimate.standard_error


def test_heston_sabr_and_rbergomi_share_surface_schema():
    common = dict(
        spot=100.0, strikes=np.array([90.0, 100.0, 110.0]), maturities=np.array([0.5]), rate=0.02
    )
    parameter_sets = {
        "heston": {"v0": 0.04, "kappa": 1.5, "theta": 0.04, "xi": 0.3, "rho": -0.6},
        "sabr": {"alpha": 0.2, "beta": 1.0, "rho": -0.3, "nu": 0.4},
        "rbergomi": {"xi0": 0.04, "eta": 0.0, "hurst": 0.1, "rho": -0.7, "n_steps": 12},
    }
    for model, parameters in parameter_sets.items():
        surface = forward_surface_teacher(
            model,
            parameters=parameters,
            n_paths=3_000,
            seed=4,
            **common,
        )
        assert surface["price"].shape == surface["implied_volatility"].shape == (1, 3)
        assert np.all(surface["price"] > 0)
        assert np.all(surface["implied_volatility"] > 0)
