"""Fixed discrete monitoring, unbiased scores and Markov-integration checks."""

import importlib
import importlib.util

import numpy as np
import pytest
from scipy.integrate import quad


def teachers():
    name = "hullkit._discrete_barrier_teachers"
    assert importlib.util.find_spec(name) is not None, "discrete barrier teachers missing"
    return importlib.import_module(name)


def density_oracle(spot, maturity, *, strike=100.0, barrier=120.0, rate=0.03, sigma=0.2):
    """Own scalar terminal-lognormal density, with K/H held fixed."""
    width = sigma * np.sqrt(maturity)
    center = np.log(spot) + (rate - sigma**2 / 2) * maturity

    def density(x):
        return np.exp(-0.5 * ((x - center) / width) ** 2) / (width * np.sqrt(2 * np.pi))

    discount = np.exp(-rate * maturity)
    lo, hi = np.log(strike), np.log(barrier)
    price = discount * quad(lambda x: (np.exp(x) - strike) * density(x), lo, hi)[0]
    delta = (
        discount
        * quad(
            lambda x: (np.exp(x) - strike) * density(x) * (x - center) / (spot * width**2),
            lo,
            hi,
        )[0]
    )
    naive = discount * quad(lambda x: np.exp(x) / spot * density(x), lo, hi)[0]
    return price, delta, naive


@pytest.mark.parametrize("spot", [80.0, 100.0, 119.0])
@pytest.mark.parametrize("maturity", [0.25, 1.0, 2.0])
def test_one_monitor_truncated_call_and_true_delta_match_own_density(spot, maturity):
    module = teachers()
    result = module.one_step(spot, maturity)
    price, delta, naive = density_oracle(spot, maturity)
    assert result["price"] == pytest.approx(price, abs=2e-12, rel=1e-11)
    assert result["delta"] == pytest.approx(delta, abs=2e-12, rel=1e-11)
    assert result["naive_pw_mean"] == pytest.approx(naive, abs=2e-12, rel=1e-11)
    assert result["boundary_term"] == pytest.approx(naive - delta, abs=2e-12)
    assert result["delta_defined"]


def test_true_delta_can_be_negative_and_h_boundary_is_a_jump():
    module = teachers()
    left = module.one_step(119.999, 1.0)
    contact = module.one_step(120.0, 1.0)
    right = module.one_step(120.001, 1.0)
    assert left["price"] > 0.1
    assert left["delta"] < 0 < left["naive_pw_mean"]
    assert contact["price"] == 0
    assert np.isnan(contact["delta"]) and not contact["delta_defined"]
    assert right["price"] == 0 and right["delta"] == 0 and right["delta_defined"]


def test_monitoring_includes_time_zero_and_terminal_and_contact_knocks_out():
    module = teachers()
    times = module.monitoring_times(1.5, 12)
    np.testing.assert_allclose(times, np.arange(13) * 1.5 / 12)
    z = np.array([[0.0, 0.0], [4.0, -4.0], [-1.0, 1.0]])
    sample = module.samples(110.0, 1.0, z)
    assert sample["paths"].shape == (3, 3)
    assert sample["survival"].tolist() == [True, False, True]
    assert sample["payoff"][1] == 0  # Re-entry below H after an earlier hit is still KO.
    contact = module.samples(120.0, 1.0, z)
    assert not np.any(contact["survival"])
    np.testing.assert_allclose(contact["payoff"], 0)
    assert not contact["delta_defined"] and np.isnan(contact["lrm"]).all()


def test_first_transition_score_and_naive_pathwise_have_the_stated_physical_units():
    module = teachers()
    z = np.array([[0.3, -0.1, 0.2], [-0.5, 0.4, 0.6], [0.6, -0.8, 0.1]])
    sample = module.samples(105.0, 1.5, z)
    score = z[:, 0] / (105.0 * 0.2 * np.sqrt(1.5 / 3))
    np.testing.assert_allclose(sample["lrm"], sample["payoff"] * score)
    expected = (
        np.exp(-0.03 * 1.5)
        * sample["paths"][:, -1]
        / 105.0
        * sample["survival"]
        * (sample["paths"][:, -1] > 100.0)
    )
    np.testing.assert_allclose(sample["naive_pw"], expected)


def test_last_increment_is_removed_only_from_conditioned_teachers():
    module = teachers()
    z = np.array([[0.3, -0.2, 0.1], [-0.5, 0.4, -0.3], [0.0, 0.1, 0.2]])
    changed = z.copy()
    changed[:, -1] = [3.0, 1.5, -4.0]
    original = module.samples(105.0, 1.0, z)
    other = module.samples(105.0, 1.0, changed)
    for key in ("last_conditional", "last_conditional_lrm", "last_conditional_pw"):
        np.testing.assert_allclose(original[key], other[key], atol=1e-13, rtol=1e-12)
    score = z[:, 0] / (105.0 * 0.2 * np.sqrt(1.0 / 3))
    np.testing.assert_allclose(
        original["last_conditional_lrm"], original["last_conditional"] * score
    )
    assert np.any(np.abs(original["payoff"] - other["payoff"]) > 0.1)
    one = module.samples(105.0, 1.0, z[:, :1])
    assert "last_conditional_lrm" not in one  # m1 remains its independent analytic check.


def test_one_monitor_mc_and_crn_bump_have_separate_sampling_and_width_errors():
    module = teachers()
    spot, maturity = 110.0, 1.0
    z = np.random.default_rng(1107).standard_normal((262144, 1))
    reference = density_oracle(spot, maturity)
    sample = module.samples(spot, maturity, z)
    for key, target in [
        ("payoff", reference[0]),
        ("lrm", reference[1]),
        ("naive_pw", reference[2]),
    ]:
        stats = module.summarize(sample[key])
        assert stats["se"] > 0
        assert abs(stats["mean"] - target) <= 6 * stats["se"] + 2e-11
    for bump in (0.08, 0.04, 0.02):
        up = module.samples(spot + bump, maturity, z)["payoff"]
        down = module.samples(spot - bump, maturity, z)["payoff"]
        stats = module.summarize((up - down) / (2 * bump))
        assert stats["se"] > 0
        assert abs(stats["mean"] - reference[1]) <= 6 * stats["se"] + 2e-5


@pytest.mark.parametrize("spot,maturity", [(80.0, 0.25), (100.0, 1.0), (119.0, 2.0)])
def test_twelve_monitor_grid_convergence_is_distinct_from_iid_mc_se(spot, maturity):
    module = teachers()
    coarse = module.markov_reference(spot, maturity, monitoring=12, order=64)
    fine = module.markov_reference(spot, maturity, monitoring=12, order=128)
    wider = module.markov_reference(spot, maturity, monitoring=12, order=128, tail_sigma=12)
    for key in ("price", "delta", "naive_pw_mean"):
        assert coarse[key] == pytest.approx(fine[key], abs=3e-6, rel=2e-6)
        assert wider[key] == pytest.approx(fine[key], abs=2e-9, rel=2e-8)
    assert fine["tail_price_bound"] < 1e-18
    assert fine["tail_delta_bound"] < 1e-9
    z = np.random.default_rng(20261011).standard_normal((131072, 12))
    sample = module.samples(spot, maturity, z)
    targets = [
        ("payoff", fine["price"]),
        ("lrm", fine["delta"]),
        ("last_conditional", fine["price"]),
        ("last_conditional_lrm", fine["delta"]),
        ("naive_pw", fine["naive_pw_mean"]),
    ]
    for key, target in targets:
        stats = module.summarize(sample[key])
        assert stats["se"] > 0 and sample["survival"].any()
        assert abs(stats["mean"] - target) <= 6 * stats["se"] + 3e-6


def test_naive_pw_and_last_score_negative_controls_miss_intermediate_boundaries():
    module = teachers()
    spot, maturity = 119.0, 1.0
    exact = module.markov_reference(spot, maturity, monitoring=12, order=128)
    z = np.random.default_rng(6017).standard_normal((262144, 12))
    sample = module.samples(spot, maturity, z)
    naive = module.summarize(sample["naive_pw"])
    assert naive["mean"] - exact["delta"] > 6 * naive["se"]
    wrong_score = module.summarize(
        sample["payoff"] * z[:, -1] / (spot * 0.2 * np.sqrt(maturity / 12))
    )
    assert abs(wrong_score["mean"] - exact["delta"]) > 6 * wrong_score["se"]
    partial_pw = module.summarize(sample["last_conditional_pw"])
    assert abs(partial_pw["mean"] - exact["delta"]) > 6 * partial_pw["se"]


def test_markov_one_monitor_uses_its_own_transition_integral():
    module = teachers()
    exact = density_oracle(115.0, 0.25)
    result = module.markov_reference(115.0, 0.25, monitoring=1, order=96)
    for key, target in zip(("price", "delta", "naive_pw_mean"), exact, strict=True):
        assert result[key] == pytest.approx(target, abs=2e-12, rel=1e-11)


def test_lower_tail_bounds_use_probability_for_price_but_sqrt_probability_for_delta():
    module = teachers()
    result = module.markov_reference(100.0, 1.0, monitoring=12, order=128, tail_sigma=4.0)
    probability = result["tail_probability_bound"]
    assert 0 < probability < 1e-3
    cap = 20.0 * np.exp(-0.03)
    assert result["tail_price_bound"] == pytest.approx(cap * probability)
    assert result["tail_delta_bound"] == pytest.approx(
        cap * np.sqrt(probability) / (100.0 * 0.2 * np.sqrt(1.0 / 12)),
    )


@pytest.mark.parametrize(
    "kwargs", [{"spot": 0}, {"maturity": -1}, {"volatility": 0}, {"barrier": 0}]
)
def test_only_mathematically_required_input_checks(kwargs):
    module = teachers()
    parameters = {"spot": 100.0, "maturity": 1.0, **kwargs}
    with pytest.raises(ValueError):
        module.one_step(**parameters)


def test_zero_strike_and_barrier_below_strike_are_valid_payoff_contracts():
    module = teachers()
    assert module.one_step(100.0, 1.0, strike=0.0)["price"] > 0
    for method in (module.one_step, module.markov_reference):
        result = method(80.0, 1.0, strike=100.0, barrier=90.0)
        assert result["price"] == 0 and result["delta"] == 0


def test_initial_knockout_shortcut_has_no_artificial_lower_cutoff_requirement():
    module = teachers()
    for strike in (0.0, 100.0, 9000.0):
        result = module.markov_reference(5000.0, 0.25, strike=strike)
        assert result["price"] == 0.0 and result["delta"] == 0.0
        assert result["delta_defined"]


def test_markov_score_delta_matches_revaluation_with_a_fixed_log_cutoff():
    module = teachers()
    spot, maturity = 119.0, 0.25
    reference = module.markov_reference(spot, maturity, order=128)
    lower = reference["log_lower"]
    estimates = []
    for bump in (0.01, 0.001):
        up = module.markov_reference(spot + bump, maturity, order=128, log_lower=lower)
        down = module.markov_reference(spot - bump, maturity, order=128, log_lower=lower)
        estimates.append((up["price"] - down["price"]) / (2 * bump))
        assert not up["log_lower_depends_on_spot"]
    assert abs(estimates[1] - reference["delta"]) < abs(estimates[0] - reference["delta"])
    assert estimates[1] == pytest.approx(reference["delta"], abs=2e-9, rel=1e-7)


def test_one_step_survival_matches_one_monitor_integral_in_price_and_delta():
    module = teachers()
    u = np.random.default_rng(1107).uniform(size=(131072, 1))
    result = module.one_step_survival(110.0, 1.0, u)
    exact = density_oracle(110.0, 1.0)
    assert result["status"] == "ok" and result["valid"].all()
    for key, target in (("payoff", exact[0]), ("delta", exact[1])):
        stats = module.summarize(result[key])
        assert stats["se"] > 0
        assert abs(stats["mean"] - target) < 6 * stats["se"]
    assert result["positive_payoff_count"] > 0
    assert not result["zero_price_se"] and not result["zero_delta_se"]


def test_one_step_survival_twelve_monitor_matches_markov_and_weight_control_is_biased():
    module = teachers()
    u = np.random.default_rng(6017).uniform(size=(131072, 12))
    result = module.one_step_survival(119.0, 1.0, u)
    exact = module.markov_reference(119.0, 1.0, monitoring=12, order=128)
    assert result["status"] == "ok" and result["valid"].all()
    for key, target in (("payoff", exact["price"]), ("delta", exact["delta"])):
        stats = module.summarize(result[key])
        assert stats["se"] > 0
        assert abs(stats["mean"] - target) < 6 * stats["se"] + 3e-6
    control = module.summarize(result["without_weight_delta"])
    assert abs(control["mean"] - exact["delta"]) > 6 * control["se"]
    np.testing.assert_allclose(
        result["delta"],
        result["without_weight_delta"] + result["weight_delta"],
        atol=2e-14,
        rtol=1e-12,
    )


@pytest.mark.parametrize("monitoring", [1, 12])
def test_one_step_survival_derivative_matches_same_uniform_revaluation(monitoring):
    module = teachers()
    u = np.random.default_rng(20261011).uniform(size=(32, monitoring))
    spot, maturity, bump = 110.0, 1.0, 1e-4
    result = module.one_step_survival(spot, maturity, u)
    up = module.one_step_survival(spot + bump, maturity, u)
    down = module.one_step_survival(spot - bump, maturity, u)
    finite_difference = (up["payoff"] - down["payoff"]) / (2 * bump)
    # These fixed paths stay away from the final strike kink over this bump.
    np.testing.assert_allclose(result["delta"], finite_difference, atol=2e-9, rtol=2e-7)


@pytest.mark.parametrize("endpoint", [0.0, 1.0])
def test_one_step_survival_rejects_uniform_endpoints(endpoint):
    module = teachers()
    with pytest.raises(ValueError, match="strictly"):
        module.one_step_survival(100.0, 1.0, np.array([[0.5, endpoint]]))


def test_one_step_survival_contact_and_probability_underflow_are_explicit():
    module = teachers()
    contact = module.one_step_survival(120.0, 1.0, np.full((4, 12), 0.5))
    assert contact["status"] == "undefined_delta_at_barrier"
    assert not contact["delta_defined"] and np.isnan(contact["delta"]).all()
    np.testing.assert_allclose(contact["payoff"], 0)
    unsupported = module.one_step_survival(100.0, 1.0, np.full((4, 1), 0.5), rate=10000.0)
    assert unsupported["status"] == "unsupported_underflow"
    assert unsupported["probability_underflow"].all() and not unsupported["valid"].any()
    assert np.isnan(unsupported["payoff"]).all() and np.isnan(unsupported["delta"]).all()
    assert unsupported["positive_payoff_count"] == 0


def test_one_step_survival_weight_underflow_and_zero_sample_se_are_not_hidden():
    module = teachers()
    rare = module.one_step_survival(119.0, 1.0, np.full((2, 1200), 0.999))
    assert rare["weight_underflow"].all() and not rare["valid"].any()
    assert rare["status"] == "unsupported_underflow"
    assert np.isnan(rare["payoff"]).all() and np.isnan(rare["delta"]).all()
    assert np.isfinite(rare["log_survival_weight"]).all()
    zero = module.one_step_survival(80.0, 0.25, np.full((4, 12), 0.1))
    assert zero["status"] == "no_positive_payoffs"
    assert zero["positive_payoff_count"] == 0
    assert zero["zero_price_se"] and zero["zero_delta_se"]
    assert not zero["statistically_informative"]


def test_markov_batch_matches_scalar_across_shared_maturities_with_separate_tail_bounds():
    module = teachers()
    inputs = np.array(
        [
            [119.0, 1.0],
            [80.0, 0.25],
            [100.0, 2.0],
            [100.0, 1.0],
            [119.0, 0.25],
            [80.0, 2.0],
        ]
    )
    result = module.markov_batch(inputs, order=128, tail_sigma=12)
    assert result["price"].shape == result["delta"].shape == (6, 1)
    assert result["tail_bounds"].shape == (6, 3)
    assert result["transition_setup_count"] == 3
    assert len(result["groups"]) == 3
    for i, (spot, maturity) in enumerate(inputs):
        scalar = module.markov_reference(spot, maturity, order=128, tail_sigma=12)
        for key, bound in (
            ("price", "tail_price_bound"),
            ("delta", "tail_delta_bound"),
        ):
            tolerance = 1e-10 + result[bound][i, 0] + scalar[bound]
            assert abs(result[key][i, 0] - scalar[key]) < tolerance
        naive_tail = (
            np.exp(-0.03 * maturity)
            * 120.0
            / spot
            * (result["tail_probability_bound"][i, 0] + scalar["tail_probability_bound"])
        )
        assert abs(result["naive_pw_mean"][i, 0] - scalar["naive_pw_mean"]) < 1e-10 + naive_tail
        assert result["tail_bounds"][i, 1] == pytest.approx(result["tail_price_bound"][i, 0])
        assert result["tail_bounds"][i, 2] == pytest.approx(result["tail_delta_bound"][i, 0])
    # T=1's shared cutoff includes S=100 and fixed K=100.
    indices = np.array([0, 3])
    np.testing.assert_allclose(result["log_lower"][indices], np.log(100.0) - 2.4)
    assert result["delta"][0, 0] < 0  # No monotonic-Delta restriction.


def test_markov_batch_single_and_duplicate_rows_give_the_same_contract_value():
    module = teachers()
    single = module.markov_batch(np.array([[119.0, 1.0]]))
    repeated = module.markov_batch(np.array([[119.0, 1.0], [119.0, 1.0]]))
    for key in ("price", "delta", "naive_pw_mean"):
        np.testing.assert_allclose(repeated[key][:, 0], single[key][0, 0], atol=1e-12, rtol=1e-11)
    assert repeated["transition_setup_count"] == 1


def test_markov_batch_delta_matches_crn_revaluation_with_shared_fixed_cutoff():
    module = teachers()
    inputs = np.array([[80.0, 0.25], [100.0, 0.25], [119.0, 0.25]])
    reference = module.markov_batch(inputs)
    bump = 0.001
    plus, minus = inputs.copy(), inputs.copy()
    plus[:, 0] += bump
    minus[:, 0] -= bump
    lower = reference["log_lower"][0, 0]
    up = module.markov_batch(plus, log_lower=lower)
    down = module.markov_batch(minus, log_lower=lower)
    difference = (up["price"] - down["price"]) / (2 * bump)
    np.testing.assert_allclose(reference["delta"], difference, atol=1e-8, rtol=2e-7)


def test_markov_batch_uses_exact_maturity_groups_and_does_not_loop_over_scalar_api(monkeypatch):
    module = teachers()

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "batch oracle must share transition setup rather than call scalar per row"
        )

    monkeypatch.setattr(module, "markov_reference", forbidden)
    inputs = np.array([[100.0, 1.0], [100.0, 1.0 + 1e-8], [115.0, 1.0]])
    result = module.markov_batch(inputs)
    assert result["transition_setup_count"] == 2 and len(result["groups"]) == 2
    assert result["group_index"][0] == result["group_index"][2]
    assert result["group_index"][0] != result["group_index"][1]
    assert np.isfinite(result["price"]).all() and np.isfinite(result["delta"]).all()


def test_markov_batch_respects_initial_contact_jump_and_defined_zero_above_barrier():
    module = teachers()
    inputs = np.array([[119.999, 1.0], [120.0, 1.0], [121.0, 1.0]])
    result = module.markov_batch(inputs)
    assert result["price"][0, 0] > 0.1 and result["delta"][0, 0] < 0
    np.testing.assert_allclose(result["price"][1:], 0)
    assert np.isnan(result["delta"][1, 0]) and not result["delta_defined"][1, 0]
    assert result["delta"][2, 0] == 0 and result["delta_defined"][2, 0]


def test_markov_batch_does_not_reuse_results_after_input_mutation_between_calls():
    module = teachers()
    inputs = np.array([[100.0, 1.0]])
    first = module.markov_batch(inputs)
    initial_value = first["price"].copy()
    inputs[0, 0] = 119.0
    second = module.markov_batch(inputs)
    assert abs(first["price"][0, 0] - second["price"][0, 0]) > 0.1
    np.testing.assert_allclose(first["price"], initial_value)
    assert second["delta"][0, 0] < 0


def test_markov_batch_optional_refinement_matches_separate_higher_order_call():
    module = teachers()
    inputs = np.array([[80.0, 0.25], [100.0, 1.0], [119.0, 1.0]])
    result = module.markov_batch(inputs, order=64, check_order=128)
    higher = module.markov_batch(inputs, order=128)
    assert result["refinement"]["order"] == 128
    for key in ("price", "delta", "naive_pw_mean"):
        np.testing.assert_allclose(
            result["refinement"][key],
            abs(higher[key] - result[key]),
            atol=1e-14,
            rtol=1e-10,
        )
    assert result["refinement"]["tail_bounds"].shape == (3, 3)


@pytest.mark.parametrize("inputs", [np.array([[0.0, 1.0]]), np.array([[100.0, 0.0]])])
def test_markov_batch_rejects_mathematically_invalid_row(inputs):
    with pytest.raises(ValueError):
        teachers().markov_batch(inputs)
