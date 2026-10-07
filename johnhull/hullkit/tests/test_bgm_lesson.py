"""Independent §33.2 LMM checks; source prices and synthetic inputs stay separate."""

import importlib
from itertools import pairwise

import numpy as np
import pytest
from scipy.stats import norm


def model():
    return importlib.import_module("hullkit._bgm_lesson")


def black_call(discount, forward, strike, integrated_variance):
    width = np.sqrt(integrated_variance)
    if width == 0:
        return discount * max(forward - strike, 0)
    d1 = np.log(forward / strike) / width + width / 2
    return discount * (forward * norm.cdf(d1) - strike * norm.cdf(d1 - width))


def flat_curve(periods):
    times = np.arange(periods + 1, dtype=float)
    return times, np.full(periods, np.expm1(0.05))


def test_simple_tenor_forwards_and_reinvestment_balance():
    m = model()
    times = np.array([0, 0.5, 1.25, 2.0])
    discounts = np.exp(-0.04 * times)
    forwards = m.tenor_forwards(times, discounts)
    assert forwards == pytest.approx(np.expm1(0.04 * np.diff(times)) / np.diff(times))
    assert np.prod(1 + np.diff(times) * forwards) * discounts[-1] == pytest.approx(1)
    with pytest.raises(ValueError):
        m.tenor_forwards([0, 1, 1], [1, 0.95, 0.9])
    with pytest.raises(ValueError):
        m.tenor_forwards(times, discounts / 2)


def test_example_33_1_table_33_1_and_nonuniform_bootstrap():
    m = model()
    assert m.bootstrap_forward_vols([0, 1, 2, 3], [0.24, 0.22, 0.20]) == pytest.approx(
        [0.24, 0.1979898987322333, 0.1523154621172782], abs=1e-13
    )
    spot = np.array([0.155, 0.1825, 0.1791, 0.1774, 0.1727, 0.1679, 0.163, 0.1601, 0.1576, 0.1554])
    printed = np.array([0.155, 0.2064, 0.1721, 0.1722, 0.1525, 0.1415, 0.1298, 0.1381, 0.136, 0.134])
    result = m.bootstrap_forward_vols(np.arange(11), spot)
    assert result == pytest.approx(printed, abs=0.00005)
    assert np.cumsum(result**2) == pytest.approx(spot**2 * np.arange(1, 11), abs=1e-14)
    # Independently expand the nonuniform triangular variance equations.
    total_variance = np.array(
        [0.2**2 * 0.25, 0.17**2 * 0.25 + 0.2**2 * 0.65,
         0.13**2 * 0.25 + 0.17**2 * 0.65 + 0.2**2 * 0.6]
    )
    times = np.array([0, 0.25, 0.9, 1.5])
    assert m.bootstrap_forward_vols(times, np.sqrt(total_variance / times[1:])) == pytest.approx(
        [0.2, 0.17, 0.13], abs=1e-13
    )
    with pytest.raises(ValueError, match="negative"):
        m.bootstrap_forward_vols([0, 1, 2], [0.25, 0.1])


TABLE_TWO = np.array(
    [[14.10, -6.45], [19.52, -6.70], [16.78, -3.84], [17.11, -1.96], [15.25, 0],
     [14.06, 1.61], [12.65, 2.89], [13.06, 4.48], [12.36, 5.65], [11.63, 6.65]]
) / 100
TABLE_THREE = np.array(
    [[13.65, -6.62, 3.19], [19.28, -7.02, 2.25], [16.72, -4.06, 0],
     [16.98, -2.06, -1.98], [14.85, 0, -3.47], [13.95, 1.69, -1.63],
     [12.61, 3.06, 0], [12.90, 4.70, 1.51], [11.97, 5.81, 2.80],
     [10.97, 6.66, 3.84]]
) / 100


def test_printed_factor_loadings_keep_norm_rounding_and_covariance():
    m = model()
    printed = np.array([0.155, 0.2064, 0.1721, 0.1722, 0.1525, 0.1415, 0.1298, 0.1381, 0.136, 0.134])
    two = m.loading_diagnostics(TABLE_TWO, printed)
    three = m.loading_diagnostics(TABLE_THREE, printed)
    assert two["norms"][0] == pytest.approx(0.1550524104939907, abs=1e-13)
    assert two["norms"][8] == pytest.approx(0.1359014716623748, abs=1e-13)
    assert np.max(np.abs(two["rounding_difference"])) < 0.0001
    assert np.max(np.abs(three["rounding_difference"])) < 0.000045
    assert two["covariance"] == pytest.approx(TABLE_TWO @ TABLE_TWO.T, abs=1e-15)
    assert two["correlation"][0, 9] < two["correlation"][0, 1]
    aligned = m.rescale_loading_norms(TABLE_TWO, printed)
    assert np.linalg.norm(aligned, axis=1) == pytest.approx(printed, abs=1e-15)
    assert m.loading_diagnostics(aligned)["correlation"] == pytest.approx(two["correlation"])
    assert not np.array_equal(aligned, TABLE_TWO)


@pytest.mark.parametrize("measure,payment_index", [("rolling", None), ("terminal", None), ("payment", 3)])
def test_multifactor_drift_from_numerically_differentiated_bond_products(measure, payment_index):
    m = model()
    forwards = np.array([0.031, 0.043, 0.048, 0.052])
    accruals = np.array([0.5, 0.75, 1.0, 0.5])
    loadings = np.array([[0.4, 0.1], [0.2, -0.1], [0.16, 0.14], [-0.08, 0.2]])
    alive = 1

    def log_bond(f, maturity):
        return -np.sum(np.log1p(accruals[alive:maturity] * f[alive:maturity]))

    h = 1e-5
    maturity = alive if measure == "rolling" else len(forwards) if measure == "terminal" else payment_index
    numerical = np.zeros_like(forwards)
    for k in range(alive, len(forwards)):
        for q in range(loadings.shape[1]):
            up = forwards * np.exp(h * loadings[:, q])
            down = forwards * np.exp(-h * loadings[:, q])
            num_vol = (log_bond(up, maturity) - log_bond(down, maturity)) / (2 * h)
            pay_vol = (log_bond(up, k + 1) - log_bond(down, k + 1)) / (2 * h)
            numerical[k] += loadings[k, q] * (num_vol - pay_vol)
    actual = m.lmm_drift(forwards, accruals, loadings, alive, measure, payment_index)
    assert actual == pytest.approx(numerical, abs=1e-11)
    if measure == "rolling":
        assert actual[alive] > 0
    if measure == "terminal":
        assert actual[-1] == 0
    if measure == "payment":
        assert actual[payment_index - 1] == pytest.approx(0, abs=1e-15)


def test_log_euler_innovation_covariance_and_reset_freeze():
    m = model()
    times, forwards = flat_curve(4)
    loadings = np.array([[0, 0], [0.2, -0.1], [0.18, 0.14], [-0.1, 0.19]])
    result = m.simulate_lmm(
        times, forwards, loadings, 40000, 1, np.random.default_rng(332001),
        measure="terminal", scheme="euler"
    )
    mu = m.lmm_drift(forwards, np.diff(times), loadings, 1, "terminal")
    innovations = np.log(result["reset_states"][1, :, 1:] / forwards[1:]) - (
        mu[1:] - 0.5 * np.sum(loadings[1:]**2, axis=1)
    )
    actual = np.cov(innovations, rowvar=False)
    oracle = loadings[1:] @ loadings[1:].T
    assert actual == pytest.approx(oracle, abs=0.0015)
    assert np.all(result["reset_states"][:, :, 0] == forwards[0])
    assert np.array_equal(result["reset_states"][1, :, 1], result["reset_states"][3, :, 1])
    assert np.any(result["reset_states"][1, :, 3] != result["reset_states"][3, :, 3])


@pytest.mark.parametrize("measure,payment_index", [("rolling", None), ("terminal", None), ("payment", 3)])
def test_zero_vol_discounted_cashflows_and_bank_account(measure, payment_index):
    m = model()
    times = np.array([0, 0.5, 1.25, 2])
    forwards = np.array([0.04, 0.05, 0.06])
    result = m.simulate_lmm(
        times, forwards, np.zeros((3, 2)), 8, 3, np.random.default_rng(22),
        measure=measure, payment_index=payment_index
    )
    discounts = np.r_[1, 1 / np.cumprod(1 + np.diff(times) * forwards)]
    assert result["fixings"] == pytest.approx(np.broadcast_to(forwards, (8, 3)))
    assert result["payment_weights"] == pytest.approx(np.broadcast_to(discounts[1:], (8, 3)))
    assert result["reset_discount_weights"] == pytest.approx(np.broadcast_to(discounts[:-1], (8, 3)))
    cf = 100 * np.diff(times) * np.maximum(forwards - 0.045, 0)
    prices = m.mc_estimate(result["payment_weights"] * cf)
    assert prices["mean"] == pytest.approx(discounts[1:] * cf)
    assert np.max(prices["standard_error"]) < 1e-15
    assert result["bank_accounts"][:, 1:] / result["bank_accounts"][:, :-1] == pytest.approx(
        np.broadcast_to(1 + np.diff(times)[:-1] * forwards[:-1], (8, 2))
    )


@pytest.mark.parametrize("measure,payment_index", [("rolling", None), ("terminal", None), ("payment", 2)])
def test_caplets_are_black_under_each_numeraire_with_each_own_six_se(measure, payment_index):
    m = model()
    times, forwards = flat_curve(3)
    loadings = np.array([[0, 0], [0.25, 0], [0.2, 0.15]])
    result = m.simulate_lmm(
        times, forwards, loadings, 60000, 16, np.random.default_rng(73017),
        measure=measure, payment_index=payment_index
    )
    for k in range(1, result["fixings"].shape[1]):
        discounted = 100 * np.maximum(result["fixings"][:, k] - forwards[k], 0) * result["payment_weights"][:, k]
        estimate = m.mc_estimate(discounted)
        expected = 100 * black_call(np.exp(-0.05 * (k + 1)), forwards[k], forwards[k], 0.25**2 * k)
        assert abs(estimate["mean"] - expected) <= 6 * estimate["standard_error"]


def test_antithetic_se_uses_pairs_and_totals_keep_cross_coupon_covariance():
    m = model()
    values = np.array([[1, 4], [3, 8], [5, 2], [7, 6]], dtype=float)
    result = m.mc_estimate(values)
    pairs = np.array([[3, 3], [5, 7]], dtype=float)
    assert result["mean"] == pytest.approx([4, 5])
    assert result["standard_error"] == pytest.approx(np.std(pairs, axis=0, ddof=1) / np.sqrt(2))
    total = m.mc_estimate(np.sum(values, axis=1))
    assert total["standard_error"] == pytest.approx(np.std([6, 12], ddof=1) / np.sqrt(2))


def test_ratchet_sticky_and_first_itm_quota_use_explicit_caller_contract():
    m = model()
    fixings = np.array([[0.05, 0.07, 0.04, 0.09], [0.05, 0.04, 0.08, 0.09]])
    accruals = np.array([0.5, 1, 0.5, 1])
    ratchet = m.cap_cashflows(fixings, accruals, "ratchet", spread=0.01, notional=100)
    sticky = m.cap_cashflows(
        fixings, accruals, "sticky", spread=0.01, initial_strike=0.05, notional=100
    )
    assert ratchet["strikes"][:, 1:] == pytest.approx(np.array([[0.06, 0.08, 0.05], [0.06, 0.05, 0.09]]))
    assert sticky["strikes"][:, 1:] == pytest.approx(np.array([[0.06, 0.07, 0.05], [0.06, 0.05, 0.06]]))
    assert sticky["cashflows"][:, 1:] == pytest.approx(np.array([[1, 0, 4], [0, 1.5, 3]]))
    flexi = m.cap_cashflows(
        fixings, accruals, "flexicap", strike=0.03, max_exercises=1, notional=100
    )
    assert flexi["cashflows"] == pytest.approx(np.array([[0, 4, 0, 0], [0, 1, 0, 0]]))
    no_rights = m.cap_cashflows(fixings, accruals, "flexicap", strike=0.03, max_exercises=0)
    assert np.all(no_rights["cashflows"] == 0)
    all_rights = m.cap_cashflows(fixings, accruals, "flexicap", strike=0.03, max_exercises=4)
    ordinary = m.cap_cashflows(fixings, accruals, "fixed", strike=0.03)
    assert np.array_equal(all_rights["cashflows"], ordinary["cashflows"])
    with pytest.raises(ValueError, match="initial_strike"):
        m.cap_cashflows(fixings, accruals, "sticky", spread=0.0025)
    with pytest.raises(ValueError, match="strike"):
        m.cap_cashflows(fixings, accruals, "flexicap", max_exercises=5)


def test_equal_marginal_caplet_variance_different_correlations_change_ratchet():
    m = model()
    times, forwards = flat_curve(4)
    norms = np.array([0.25, 0.2, 0.17])
    aligned = np.c_[norms, np.zeros(3)]
    rotated = np.array([[0.25, 0], [0, 0.2], [-0.17, 0]])
    exotic = []
    for loadings in (aligned, rotated):
        result = m.simulate_lmm(
            times, forwards, loadings, 60000, 16, np.random.default_rng(332003),
            stationary=True, measure="terminal"
        )
        for k in range(1, 4):
            values = 100 * np.maximum(result["fixings"][:, k] - forwards[k], 0) * result["payment_weights"][:, k]
            estimate = m.mc_estimate(values)
            expected = 100 * black_call(np.exp(-0.05 * (k + 1)), forwards[k], forwards[k], np.sum(norms[:k]**2))
            assert abs(estimate["mean"] - expected) < 6 * estimate["standard_error"]
        cashflows = m.cap_cashflows(result["fixings"], np.ones(4), "ratchet", spread=0.0025, notional=100)["cashflows"]
        exotic.append(m.mc_estimate(np.sum(cashflows * result["payment_weights"], axis=1)))
    assert abs(exotic[0]["mean"] - exotic[1]["mean"]) > 6 * np.hypot(
        exotic[0]["standard_error"], exotic[1]["standard_error"]
    )


def independent_swap_rate(forwards, accruals, groups):
    discounts = 1 / np.cumprod(1 + accruals * forwards)
    ends = np.asarray(groups[1:])
    tenors = np.array([sum(accruals[a:b]) for a, b in pairwise(groups)])
    annuity = np.sum(tenors * discounts[ends - 1])
    return (1 - discounts[-1]) / annuity, annuity


def test_swap_gradient_coarse_tenor_and_frozen_covariance_are_independent():
    m = model()
    forwards = np.array([0.03, 0.045, 0.04, 0.055])
    accruals = np.array([0.25, 0.25, 0.5, 0.5])
    groups = [0, 2, 4]
    stats = m.swap_rate_statistics(forwards, accruals, groups)
    s, annuity = independent_swap_rate(forwards, accruals, groups)
    h = 1e-6
    gradient = np.array([
        (independent_swap_rate(forwards + np.eye(4)[j] * h, accruals, groups)[0]
         - independent_swap_rate(forwards - np.eye(4)[j] * h, accruals, groups)[0]) / (2 * h)
        for j in range(4)
    ])
    assert stats["rate"] == pytest.approx(s, abs=1e-15)
    assert stats["annuity"] == pytest.approx(annuity, abs=1e-15)
    assert stats["gradient"] == pytest.approx(gradient, abs=2e-10)
    assert stats["coarse_forwards"] == pytest.approx([
        ((1 + 0.25 * forwards[0]) * (1 + 0.25 * forwards[1]) - 1) / 0.5,
        ((1 + 0.5 * forwards[2]) * (1 + 0.5 * forwards[3]) - 1)
    ])
    segments = np.array([[[0.2, 0.1], [0.19, -0.08], [0.15, 0.14], [0.12, 0.16]],
                         [[0.18, 0.1], [0.16, -0.09], [0.14, 0.1], [0.1, 0.13]]])
    weights = gradient * forwards / s
    variance = sum(dt * np.sum((weights @ loading)**2) for dt, loading in zip([0.4, 0.6], segments, strict=True))
    result = m.frozen_swaption_price(
        forwards, accruals, segments, [0.4, 0.6], 1, 0.97, s, groups=groups
    )
    assert result["integrated_variance"] == pytest.approx(variance, rel=1e-8)
    assert result["price"] == pytest.approx(black_call(0.97 * annuity, s, s, variance), rel=1e-8)
    fine = m.swap_rate_statistics(forwards, accruals)
    assert fine["annuity"] != pytest.approx(annuity)
    with pytest.raises(ValueError):
        m.swap_rate_statistics(forwards, accruals, [0, 1, 3])
    with pytest.raises(ValueError):
        m.frozen_swaption_price(forwards, accruals, segments, [0.4, 0.5], 1, 0.97, s)


def test_one_period_swaption_reduces_to_caplet_black():
    m = model()
    f, delta, horizon, sigma, df = 0.047, 0.5, 1.5, 0.22, 0.95
    result = m.frozen_swaption_price([f], [delta], [[[sigma]]], [horizon], horizon, df, f)
    expected = black_call(df * delta / (1 + delta * f), f, f, sigma**2 * horizon)
    assert result["integrated_variance"] == pytest.approx(sigma**2 * horizon)
    assert result["price"] == pytest.approx(expected, rel=1e-13)


def test_frozen_swaption_against_joint_mc_and_nonlinearity_shrinks_with_volatility():
    m = model()
    times, forwards = flat_curve(5)
    base = np.array([[0, 0], [0.25, 0], [0.2, 0.15], [0.12, 0.20], [-0.05, 0.21]])
    initial = m.swap_rate_statistics(forwards[1:], np.ones(4))
    errors = []
    for scale in [1, 0.1]:
        loading = scale * base
        result = m.simulate_lmm(
            times, forwards, loading, 60000, 16, np.random.default_rng(332004),
            measure="terminal", stop_reset=1
        )
        state = result["reset_states"][1, :, 1:]
        stats = m.swap_rate_statistics(state, np.ones(4))
        discounted = stats["annuity"] * np.maximum(stats["rate"] - initial["rate"], 0) * result["reset_discount_weights"][:, 1]
        estimate = m.mc_estimate(discounted)
        approximation = m.frozen_swaption_price(
            forwards[1:], np.ones(4), loading[None, 1:, :], [1], 1,
            np.exp(-0.05), initial["rate"]
        )
        if scale == 0.1:
            assert abs(estimate["mean"] - approximation["price"]) < 6 * estimate["standard_error"]
        linear = initial["rate"] + (state - forwards[1:]) @ initial["gradient"]
        errors.append(np.sqrt(np.mean((stats["rate"] - linear)**2)))
    assert errors[1] < errors[0] * 0.02


def test_pca_target_norms_column_sign_invariance_and_zero_direction_rejection():
    m = model()
    changes = np.array([[0.01, 0.02, -0.01], [-0.02, -0.01, 0.02], [0.015, 0.005, -0.01],
                        [-0.01, -0.025, 0.02], [0.02, 0.018, -0.015]])
    target = np.array([0.2, 0.18, 0.15])
    result = m.pca_factor_loadings(changes, target, 2)
    assert np.linalg.norm(result["loadings"], axis=1) == pytest.approx(target, abs=1e-14)
    assert result["eigenvalues"][0] >= result["eigenvalues"][1] >= 0
    flipped = result["loadings"] * np.array([-1, 1])
    assert flipped @ flipped.T == pytest.approx(result["loadings"] @ result["loadings"].T)
    with pytest.raises(ValueError):
        m.rescale_loading_norms([[0, 0]], [0.2])


def test_synthetic_frozen_price_calibration_keeps_caplet_norms_and_heldout_quote():
    m = model()
    forwards = np.array([0.04, 0.052])
    accruals = np.array([0.5, 0.5])
    target = np.array([0.2, 0.17])
    truth = np.array([[0.2, 0], [0.17 * np.cos(0.85), 0.17 * np.sin(0.85)]])

    def independent_price(groups, horizon, strike):
        s, annuity = independent_swap_rate(forwards, accruals, groups)
        h = 1e-6
        gradient = np.array([
            (independent_swap_rate(forwards + np.eye(2)[j] * h, accruals, groups)[0]
             - independent_swap_rate(forwards - np.eye(2)[j] * h, accruals, groups)[0]) / (2 * h)
            for j in range(2)
        ])
        variance = horizon * np.sum(((gradient * forwards / s) @ truth)**2)
        return black_call(0.96 * annuity, s, strike, variance)

    quotes = [
        {"expiry": 1, "discount": 0.96, "strike": 0.047, "groups": [0, 1, 2],
         "price": independent_price([0, 1, 2], 1, 0.047)},
        {"expiry": 2, "discount": 0.96, "strike": 0.05, "groups": [0, 2],
         "price": independent_price([0, 2], 2, 0.05)}
    ]
    for start in [0.2, 0.9, 1.4]:
        fit = m.calibrate_frozen_two_factor(forwards, accruals, target, quotes, [start])
        assert fit["success"]
        assert fit["rank"] == 1
        assert np.linalg.norm(fit["loadings"], axis=1) == pytest.approx(target, abs=1e-14)
        assert fit["loadings"] @ fit["loadings"].T == pytest.approx(truth @ truth.T, abs=2e-9)
        heldout = m.frozen_swaption_price(
            forwards, accruals, fit["loadings"][None, :, :], [1.4], 1.4, 0.96, 0.042
        )
        assert heldout["price"] == pytest.approx(independent_price([0, 1, 2], 1.4, 0.042), abs=1e-10)


@pytest.mark.parametrize("kwargs", [
    {"paths": True}, {"paths": 3}, {"steps_per_period": 0}, {"measure": "wrong"},
    {"payment_index": 1, "measure": "payment", "stop_reset": 1},
    {"scheme": "level-euler"}, {"stop_reset": 3}
])
def test_invalid_simulation_contracts_are_rejected(kwargs):
    m = model()
    args = dict(paths=8, steps_per_period=2, measure="terminal")
    args.update(kwargs)
    with pytest.raises(ValueError):
        m.simulate_lmm([0, 1, 2, 3], [0.05] * 3, np.ones((3, 1)) * 0.2, rng=np.random.default_rng(1), **args)
