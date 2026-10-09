"""Independent checks of saved conditional Asian teacher primitives."""

from dataclasses import replace

import numpy as np
import pytest
from hullkit._heston_local_surface import HestonParameters
from scipy.integrate import quad
from scipy.special import ndtr
from scipy.stats import norm


def _api():
    from hullkit import _dynamic_hedging_conditional

    return _dynamic_hedging_conditional


def _parameters(**changes):
    return replace(HestonParameters(100, 0.03, 0.01, 0.04, 2, 0.04, 0.3, -0.6), **changes)


class _Local:
    def evaluate(self, t, spots):
        return {
            "variance": (0.2 + 0.001 * (spots - 100)) ** 2,
            "status": np.full(spots.shape, "interior"),
        }


def test_tail_against_independent_quadrature():
    api = _api()
    b, c, mu, sigma, x = 2.0, 1.2, -0.01, 0.3, 3.1
    ref = quad(
        lambda z: max(b + c * np.exp(mu + sigma * z) - x, 0) * norm.pdf(z),
        -12,
        12,
        epsabs=1e-11,
        points=[(np.log((x - b) / c) - mu) / sigma],
    )[0]
    got = api.conditional_tail(b, c, mu, sigma, x)
    assert got["f"] == pytest.approx(ref, abs=2e-10)
    prob = quad(norm.pdf, (np.log((x - b) / c) - mu) / sigma, 12, epsabs=1e-11)[0]
    assert got["f_x"] == pytest.approx(-prob, abs=2e-12)


def test_tail_linear_and_deterministic_atom_are_distinct():
    api = _api()
    linear = api.conditional_tail(2, 1.2, -0.01, 0.3, 1.5)
    assert linear["f"] == pytest.approx(0.5 + 1.2 * np.exp(0.035))
    assert linear["f_x"] == -1
    atom = api.conditional_tail(2, 1.2, 0, 0, 3.2)
    assert atom["f"] == 0
    assert np.isnan(atom["f_x"])
    assert atom["status"] == "unknown_atom"


def test_auxiliary_one_fixing_is_black_with_calendar_delay_and_memory():
    api = _api()
    spot, var, delay, expiry, rate, q = 100.0, 0.09, 0.2, 0.3, 0.03, 0.01
    memory, strike = 1100.0, 100.0
    effective_strike = 12 * strike - memory
    sd = np.sqrt(var * delay)
    d2 = (np.log(spot / effective_strike) + (rate - q - var / 2) * delay) / sd
    ref = (
        np.exp(-rate * expiry)
        / 12
        * (spot * np.exp((rate - q) * delay) * ndtr(d2 + sd) - effective_strike * ndtr(d2))
    )
    assert api.auxiliary_geometric_mean(
        spot,
        var,
        np.array([delay]),
        expiry,
        rate=rate,
        dividend_yield=q,
        memory_sum=memory,
        strike=strike,
    ) == pytest.approx(ref, abs=1e-12)


def test_auxiliary_irregular_calendar_matches_independent_gaussian_quadrature():
    api = _api()
    delays = np.array([0.07, 0.24, 0.55])
    # Three independent Brownian intervals: log G weights 1, 2/3, 1/3.
    variance = 0.06
    mean = np.log(103) + (0.02 - variance / 2) * delays.mean()
    sd = np.sqrt(variance * (0.07 + 4 / 9 * 0.17 + 1 / 9 * 0.31))
    ref = (
        np.exp(-0.03 * 0.6)
        / 4
        * quad(
            lambda z: max(np.exp(mean + sd * z) - 98, 0) * norm.pdf(z),
            -12,
            12,
            epsabs=1e-10,
            points=[(np.log(98) - mean) / sd],
        )[0]
    )
    got = api.auxiliary_geometric_mean(
        103,
        variance,
        delays,
        0.6,
        rate=0.03,
        dividend_yield=0.01,
        memory_sum=906,
        strike=100,
    )
    assert got == pytest.approx(ref, abs=2e-10)


def _primitives(model="heston", *, normals=None, spot=100, state=0.04, surface=None):
    if normals is None:
        normals = np.random.default_rng(117).normal(size=(256, 6, 2))
    return _api().teacher_primitives(
        model,
        _parameters(),
        normals,
        calendar_times=np.array([0.5, 0.53, 0.59, 0.67, 0.74, 0.81, 1.0]),
        fixing_indices=np.array([2, 4, 6]),
        spot=spot,
        state=state,
        memory_count=9,
        surface=surface,
    )


def test_saved_raw_primitives_reconstruct_arithmetic_and_shared_last_normal():
    api = _api()
    normals = np.random.default_rng(222).normal(size=(256, 6, 2))
    p = _primitives(normals=normals)
    stock = np.full(256, 100.0)
    v = np.full(256, 0.04)
    total = np.zeros(256)
    # Independent positive quadratic root, with left variance in stock.
    params = _parameters()
    for j, dt in enumerate(np.diff(p["calendar_times"])):
        old = v.copy()
        stock *= np.exp(0.02 * dt - old * dt / 2 + np.sqrt(old * dt) * normals[:, j, 0])
        zv = params.rho * normals[:, j, 0] + np.sqrt(1 - params.rho**2) * normals[:, j, 1]
        a = (4 * params.kappa * params.theta - params.xi**2) / 8
        u = np.sqrt(v) + params.xi / 2 * np.sqrt(dt) * zv
        v = (
            (u + np.sqrt(u * u + 4 * (1 + params.kappa * dt / 2) * a * dt))
            / (2 * (1 + params.kappa * dt / 2))
        ) ** 2
        if j + 1 in (2, 4, 6):
            total += stock / 100
    reconstructed = p["b"] + p["c"] * np.exp(p["mu"] + p["sigma"] * p["last_z"])
    np.testing.assert_allclose(reconstructed, total, atol=1e-14, rtol=1e-14)
    np.testing.assert_array_equal(p["last_z"], normals[:, -1, 0])
    assert p["last_left_spot"].shape == (256,)
    assert p["original_path_count"] == 256


def test_linear_memory_uses_exact_risk_neutral_mean_and_original_metadata():
    api = _api()
    p = _primitives()
    labels = api.primitive_labels(p, np.array([-1.0, 0.0, 3.0]))
    exact = np.exp(0.02 * np.array([0.09, 0.24, 0.5])).sum()
    np.testing.assert_allclose(labels["f"][:2], exact + np.array([1.0, 0.0]), atol=1e-14)
    np.testing.assert_array_equal(labels["f_x"][:2], [-1, -1])
    assert labels["status"][0] == "not_required_linear_claim"
    for key in ("spot", "state", "memory_count", "original_path_count", "shared_driver_id"):
        assert labels[key] == p[key]
    np.testing.assert_allclose(labels["fixing_delays"], [0.09, 0.24, 0.5], atol=1e-15)


def test_joint_blocks_preserve_correlated_curve_and_three_components():
    api = _api()
    p = _primitives()
    labels = api.primitive_labels(p, np.array([2.8, 3.0, 3.2]))
    assert labels["block_means"].shape == (16, 3, 3)
    samples = np.stack(
        [labels["raw_samples"], labels["conditioned_samples"], labels["cv_samples"]], axis=-1
    )
    expected_blocks = samples.reshape(16, 16, 3, 3).mean(axis=1)
    np.testing.assert_allclose(labels["block_means"], expected_blocks)
    expected_covariance = np.cov(expected_blocks.reshape(16, -1), rowvar=False, ddof=1) / 16
    np.testing.assert_allclose(labels["block_covariance"], expected_covariance)
    assert labels["original_path_count"] == 256
    assert labels["block_path_count"] == 16
    assert labels["block_covariance"][2, 5] != 0


def test_auxiliary_conditioning_uses_same_last_z_and_beta_one_without_clipping():
    api = _api()
    p = _primitives()
    labels = api.primitive_labels(p, np.array([3.0, 5.0]))
    m = 3
    raw_aux = np.maximum(
        m * np.exp(p["aux_logG_prefix"] + p["aux_last_loading"] * p["last_z"])
        - np.array([3, 5])[:, None],
        0,
    ).T
    np.testing.assert_allclose(labels["aux_raw_samples"], raw_aux)
    np.testing.assert_allclose(
        labels["cv_samples"],
        labels["conditioned_samples"] - labels["aux_conditioned_samples"] + labels["aux_mean"],
    )
    # A control variate sample may be negative; it is evidence, not a price bound.
    assert np.any(labels["cv_samples"] < 0)


def test_local_control_and_model_recompute_for_spot_and_state_bumps():
    surface = _Local()
    for spot, ell in [(99, 0.8), (100, 1.0), (101, 1.2)]:
        p = _primitives("local", spot=spot, state=ell, surface=surface)
        assert p["control_variance"] == pytest.approx(ell * (0.2 + 0.001 * (spot - 100)) ** 2)
        assert p["aux_first_midpoint"] == pytest.approx(0.515)
        np.testing.assert_allclose(
            p["last_left_coefficient"] ** 2,
            ell * (0.2 + 0.001 * (p["last_left_spot"] - 100)) ** 2,
        )


def test_heston_control_uses_expected_average_variance_at_bumped_state():
    for state in [0.02, 0.04, 0.08]:
        p = _primitives(state=state)
        ref = 0.04 + (state - 0.04) * (1 - np.exp(-2 * 0.5)) / (2 * 0.5)
        assert p["control_variance"] == pytest.approx(ref)


def test_nonconstant_local_spot_chain_matches_independent_one_step_price_bump():
    api = _api()
    normals = np.zeros((32, 1, 2))
    params = _parameters()
    surface = _Local()

    def price(s, ell=1):
        p = api.teacher_primitives(
            "local",
            params,
            normals,
            calendar_times=np.array([0.5, 1.0]),
            fixing_indices=np.array([1]),
            spot=s,
            state=ell,
            memory_count=11,
            surface=surface,
        )
        return np.exp(-0.03 * 0.5) * s / 12 * api.primitive_labels(p, np.array([100 / s]))["f"][0]

    def independent_price(s, ell=1):
        variance = ell * (0.2 + 0.001 * (s - 100)) ** 2
        sd = np.sqrt(variance * 0.5)
        d2 = (np.log(s / 100) + (0.02 - variance / 2) * 0.5) / sd
        return np.exp(-0.03 * 0.5) / 12 * (s * np.exp(0.01) * ndtr(d2 + sd) - 100 * ndtr(d2))

    h = 0.01
    actual = (price(100 + h) - price(100 - h)) / (2 * h)
    expected = (independent_price(100 + h) - independent_price(100 - h)) / (2 * h)
    homogeneous = np.exp(-0.01 * 0.5) * ndtr((0.02 + 0.04 / 2) * 0.5 / np.sqrt(0.04 * 0.5)) / 12
    assert actual == pytest.approx(expected, abs=1e-11)
    assert abs(actual - homogeneous) > 0.002
    state_bump = (price(100, 1 + h) - price(100, 1 - h)) / (2 * h)
    state_ref = (independent_price(100, 1 + h) - independent_price(100, 1 - h)) / (2 * h)
    assert state_bump == pytest.approx(state_ref, abs=1e-11)


def test_underresolved_zero_samples_and_zero_se_are_unknown():
    api = _api()
    p = _primitives(normals=np.zeros((32, 6, 2)))
    labels = api.primitive_labels(p, np.array([3.0, 1000.0]))
    assert labels["status"][0] == "unknown_underresolved"
    assert labels["status"][1] == "unknown_underresolved"


def test_unsupported_path_is_retained_and_invalidates_whole_label():
    api = _api()

    class Unsupported(_Local):
        def evaluate(self, t, spots):
            result = super().evaluate(t, spots)
            result["status"] = np.full(spots.shape, "unsupported_fixture")
            return result

    p = _primitives("local", state=1, surface=Unsupported())
    assert p["original_path_count"] == 256
    assert not np.any(p["path_mask"])
    labels = api.primitive_labels(p, np.array([3.0]))
    assert labels["status"][0] == "unknown_invalid_primitives"
    assert np.isnan(labels["f"][0])


def test_invalid_original_path_keeps_derivative_diagnostics_and_covariance_unknown():
    api = _api()
    normals = np.random.default_rng(722).normal(size=(32, 6, 2))
    normals[0, 0, 0] = np.nan
    p = _primitives(normals=normals)
    labels = api.primitive_labels(p, np.array([2.9, 3.1]))
    assert labels["original_path_count"] == 32
    assert labels["N"] == 32
    np.testing.assert_array_equal(labels["path_mask"], [False] + [True] * 31)
    assert np.all(labels["status"] == "unknown_invalid_primitives")
    assert np.isnan(labels["f"]).all()
    assert np.isnan(labels["f_x"]).all()
    # One missing original path makes all component estimates unknown. A NaN
    # payoff must not become raw derivative zero through a boolean comparison.
    assert np.isnan(labels["derivative_component_means"]).all()
    assert np.isnan(labels["derivative_component_se"]).all()
    assert np.isnan(labels["derivative_block_means"][0]).all()
    assert np.isnan(labels["derivative_block_covariance"]).all()
    assert np.isnan(labels["joint_block_covariance"]).all()
    assert np.isnan(labels["joint_block_means"][0]).all()
    for key in ("raw_x_samples", "conditioned_x_samples", "f_x_samples"):
        assert labels[key].shape == (32, 2)
        assert np.isnan(labels[key][0]).all()
        assert np.isfinite(labels[key][1:]).all()


@pytest.mark.parametrize("delays", [np.array([-0.1]), np.array([0.4, 0.3]), np.array([0.7])])
def test_auxiliary_rejects_invalid_calendar(delays):
    with pytest.raises(ValueError):
        _api().auxiliary_geometric_mean(
            100,
            0.04,
            delays,
            0.5,
            rate=0.03,
            dividend_yield=0,
            memory_sum=0,
            strike=100,
        )


def test_labels_reject_non_iid_block_partition_and_unsorted_thresholds():
    api = _api()
    p = _primitives(normals=np.zeros((33, 6, 2)))
    with pytest.raises(ValueError):
        api.primitive_labels(p, np.array([3.0]))
    with pytest.raises(ValueError):
        api.primitive_labels(_primitives(), np.array([3.0, 2.0]))


def test_exact_linear_price_and_derivative_are_the_saved_block_curves():
    api = _api()
    labels = api.primitive_labels(_primitives(), np.array([-1.0, 0.0, 3.0]))
    np.testing.assert_allclose(
        labels["block_means"][:, :2, 2], np.broadcast_to(labels["f"][:2], (16, 2)), atol=1e-14
    )
    np.testing.assert_array_equal(labels["f_x_block_means"][:, :2], -np.ones((16, 2)))
    np.testing.assert_allclose(labels["f_samples"].mean(axis=0), labels["f"], atol=1e-14)


def test_last_variance_shock_is_unused_for_claim_primitives():
    normals = np.random.default_rng(17).normal(size=(32, 6, 2))
    regular = _primitives(normals=normals)
    normals[:, -1, 1] = np.nan
    changed = _primitives(normals=normals)
    np.testing.assert_array_equal(changed["path_mask"], np.ones(32, dtype=bool))
    for key in ("b", "c", "mu", "sigma", "last_left_variance"):
        np.testing.assert_allclose(changed[key], regular[key])


def test_settled_claim_and_atom_do_not_require_future_simulation():
    api = _api()
    p = api.teacher_primitives(
        "heston",
        _parameters(),
        np.empty((32, 0, 2)),
        calendar_times=np.array([1.0]),
        fixing_indices=np.array([], dtype=int),
        spot=100,
        state=0.04,
        memory_count=12,
    )
    labels = api.primitive_labels(p, np.array([-1.0, 0.0, 1.0]))
    np.testing.assert_allclose(labels["f"], [1, 0, 0])
    assert labels["status"].tolist() == [
        "not_required_settled_claim",
        "unknown_atom",
        "not_required_settled_claim",
    ]
    assert np.isnan(labels["f_x"][1])
    assert (
        api.auxiliary_geometric_mean(
            100,
            0.04,
            np.array([]),
            0.0,
            rate=0.03,
            dividend_yield=0,
            memory_sum=1212,
            strike=100,
        )
        == 1
    )


def test_joint_saved_price_derivative_covariance_preserves_cross_risk_errors():
    api = _api()
    p = _primitives()
    labels = api.primitive_labels(p, np.array([2.9, 3.1]))
    samples = np.concatenate(
        [
            np.stack(
                [labels["raw_samples"], labels["conditioned_samples"], labels["cv_samples"]],
                axis=-1,
            ).reshape(256, -1),
            np.stack(
                [
                    -(
                        (p["b"] + p["c"] * np.exp(p["mu"] + p["sigma"] * p["last_z"]))[:, None]
                        > np.array([2.9, 3.1])
                    ).astype(float),
                    api.conditional_tail(
                        *[p[key][:, None] for key in ("b", "c", "mu", "sigma")],
                        np.array([2.9, 3.1]),
                    )["f_x"],
                    labels["f_x_samples"],
                ],
                axis=-1,
            ).reshape(256, -1),
        ],
        axis=1,
    )
    ref = np.cov(samples.reshape(16, 16, -1).mean(axis=1), rowvar=False, ddof=1) / 16
    np.testing.assert_allclose(labels["joint_block_covariance"], ref)
    assert abs(ref[2, 8]) > 0


def test_analytic_one_step_underflow_is_not_a_qualified_zero_price():
    api = _api()
    p = api.teacher_primitives(
        "heston",
        _parameters(),
        np.zeros((32, 1, 2)),
        calendar_times=np.array([0.5, 1.0]),
        fixing_indices=np.array([1]),
        spot=100,
        state=0.04,
        memory_count=11,
    )
    labels = api.primitive_labels(p, np.array([1.0, 1e100]))
    assert labels["status"][0] == "ready"
    assert labels["status"][1] == "unknown_underresolved"


def test_local_zero_variance_branch_is_exact_but_atom_greek_is_unknown():
    api = _api()

    class ZeroVariance(_Local):
        def evaluate(self, t, spots):
            return {"variance": np.zeros_like(spots), "status": np.full(spots.shape, "interior")}

    p = api.teacher_primitives(
        "local",
        _parameters(rate=0, dividend_yield=0),
        np.zeros((32, 2, 2)),
        calendar_times=np.array([0.0, 0.5, 1.0]),
        fixing_indices=np.array([1, 2]),
        spot=100,
        state=1,
        memory_count=10,
        surface=ZeroVariance(),
    )
    labels = api.primitive_labels(p, np.array([1.0, 2.0, 3.0]))
    np.testing.assert_array_equal(labels["f"], [1, 0, 0])
    assert labels["status"].tolist() == ["ready", "unknown_atom", "ready"]
    assert np.isnan(labels["f_x"][1])


def test_local_control_recomputed_analytic_mean_agrees_with_independent_law():
    api = _api()
    for spot, ell in [(99, 0.8), (101, 1.2)]:
        p = _primitives("local", spot=spot, state=ell, surface=_Local())
        labels = api.primitive_labels(p, np.array([3.0]))
        variance = ell * (0.2 + 0.001 * (spot - 100)) ** 2
        mean = (0.02 - variance / 2) * (0.09 + 0.24 + 0.5) / 3
        sd = np.sqrt(variance * (0.09 + 4 * 0.09 + 0.24 + 2 * 0.24 + 0.5) / 9)
        ref = quad(
            lambda z, mean=mean, sd=sd: max(3 * np.exp(mean + sd * z) - 3, 0) * norm.pdf(z),
            -12,
            12,
            epsabs=1e-11,
            points=[-mean / sd],
        )[0]
        assert labels["aux_mean"][0] == pytest.approx(ref, abs=1e-10)
