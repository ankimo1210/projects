"""Short synthetic-session call teachers: independent math and IID accounting."""

import json
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pytest
from hullkit import _short_maturity_teachers as teacher
from hullkit.alternative_models import merton_jump_price
from hullkit.bsm import call_delta, call_price, gamma
from hullkit.zero_dte import TradingSession
from scipy.integrate import quad
from scipy.stats import norm, poisson

NY = ZoneInfo("America/New_York")
PARAMS = teacher.CallParameters(0.03, 0.0, -0.05, 0.10)
EXPIRY = datetime(2026, 10, 8, 16, tzinfo=NY)


def state(minutes=30, event=True):
    return teacher.clock_state(EXPIRY - timedelta(minutes=minutes), EXPIRY, event=event)


def density_values(spot, strike, clock, counts, z_jump):
    """Payoff times normal-density scores, without a call CDF formula."""
    jump = counts * PARAMS.jump_mean + np.sqrt(counts) * PARAMS.jump_std * z_jump
    w = np.sqrt(clock.variance)
    drift = (
        (PARAMS.rate - PARAMS.dividend) * clock.carry_years
        - np.expm1(PARAMS.jump_mean + PARAMS.jump_std**2 / 2) * clock.jump_mean_count
        - w * w / 2
        + jump
    )
    lower = (np.log(strike / spot) - drift) / w
    discount = np.exp(-PARAMS.rate * clock.carry_years)

    def integrand(z, component):
        payoff = discount * (spot * np.exp(drift + w * z) - strike)
        score = (1.0, z / (spot * w), (z * z - z * w - 1) / (spot * spot * w * w))[component]
        return payoff * score * norm.pdf(z)

    return np.array(
        [
            quad(integrand, lower, max(14.0, lower + 14), args=(j,), epsabs=1e-10, epsrel=1e-10)[0]
            for j in range(3)
        ]
    )


@pytest.mark.parametrize("day", [date(2026, 7, 2), date(2026, 1, 8)])
def test_clock_same_instant_utc_summer_winter_and_separate_units(day):
    expiry = datetime.combine(day, EXPIRY.timetz())
    opening = expiry.replace(hour=9, minute=30)
    clock = teacher.clock_state(opening, expiry, event=True)
    utc = teacher.clock_state(opening.astimezone(UTC), expiry.astimezone(UTC), event=True)
    assert clock.status == utc.status
    assert [
        clock.carry_years,
        clock.variance,
        clock.jump_mean_count,
        clock.remaining_seconds,
    ] == pytest.approx(
        [utc.carry_years, utc.variance, utc.jump_mean_count, utc.remaining_seconds],
        rel=1e-12,
        abs=1e-16,
    )
    assert clock.carry_years == pytest.approx(23400 / (365 * 86400))
    assert clock.variance == pytest.approx(0.20**2 / 252)
    assert clock.jump_mean_count == pytest.approx(0.028)
    assert clock.remaining_seconds == pytest.approx(23400)


@pytest.mark.parametrize("minutes", [390, 331.5, 58.5, 30, 5, 1, 1 / 60])
def test_u_clock_independent_piecewise_integral_and_pulse_overlap(minutes):
    clock = state(minutes)
    fraction = 1 - minutes / 390
    edges = [0.0, 0.15, 0.85, 1.0]
    remaining = sum(
        max(0.0, right - max(fraction, left)) * weight
        for left, right, weight in zip(edges[:-1], edges[1:], [2.0, 0.5, 2.0], strict=True)
    )
    assert clock.variance == pytest.approx(0.20**2 / 252 * remaining / 0.95, abs=1e-18)
    assert clock.jump_mean_count == pytest.approx(0.028 * min(minutes, 30) / 30)
    assert state(minutes, False).jump_mean_count == pytest.approx(0.0)


def test_clock_invalid_calendar_session_and_expiry_boundaries():
    with pytest.raises(ValueError, match="aware"):
        teacher.clock_state(datetime(2026, 10, 8, 15), EXPIRY, event=True)
    with pytest.raises(ValueError, match="trading day"):
        teacher.clock_state(
            EXPIRY - timedelta(minutes=1),
            EXPIRY,
            event=True,
            session=TradingSession(holidays=(EXPIRY.date(),)),
        )
    saturday = EXPIRY.replace(day=10)
    with pytest.raises(ValueError, match="trading day"):
        teacher.clock_state(saturday - timedelta(minutes=1), saturday, event=True)
    with pytest.raises(ValueError, match="session"):
        teacher.clock_state(EXPIRY - timedelta(hours=7), EXPIRY, event=True)
    with pytest.raises(ValueError, match=r"same.day"):
        teacher.clock_state(EXPIRY - timedelta(days=1), EXPIRY, event=True)
    with pytest.raises(ValueError, match="after"):
        teacher.clock_state(EXPIRY + timedelta(seconds=1), EXPIRY, event=True)
    end = teacher.clock_state(EXPIRY, EXPIRY, event=True)
    assert end.status == "expiry"
    assert [end.carry_years, end.variance, end.jump_mean_count] == pytest.approx([0.0, 0.0, 0.0])


@pytest.mark.parametrize("spot,count,z", [(100.0, 0, 0.0), (98.0, 1, -0.4), (103.0, 2, 0.7)])
def test_conditioning_matches_independent_density_scores_and_spot_bumps(spot, count, z):
    clock = state(30)
    value = teacher.conditional_values(spot, 100.0, clock, PARAMS, count, z)
    assert value == pytest.approx(density_values(spot, 100.0, clock, count, z), rel=2e-9, abs=1e-9)
    h = spot * np.sqrt(clock.variance) * 0.002
    low = teacher.conditional_values(spot - h, 100.0, clock, PARAMS, count, z)
    high = teacher.conditional_values(spot + h, 100.0, clock, PARAMS, count, z)
    assert value[1] == pytest.approx((high[0] - low[0]) / (2 * h), rel=2e-5, abs=1e-8)
    assert value[2] == pytest.approx((high[1] - low[1]) / (2 * h), rel=2e-5, abs=1e-8)


def test_event_zero_count_compensator_and_individual_labels_are_not_clipped():
    clock = state(30)
    event_zero = teacher.conditional_values(110.0, 100.0, clock, PARAMS, 0, 0.0)
    no_event = teacher.conditional_values(110.0, 100.0, state(30, False), PARAMS, 0, 0.0)
    assert event_zero[1] > 1.0
    assert event_zero[0] > no_event[0]
    extreme = teacher.conditional_values(100.0, 100.0, clock, PARAMS, 1, 30.0)
    assert extreme[0] > 100.0 and extreme[1] > 1.0
    paths = teacher.path_values(100.0, 100.0, clock, PARAMS, [1], [0.0], [30.0])
    assert paths["price"][0] > 100.0 and paths["pw_delta"][0] > 1.0


def test_small_variance_atm_price_and_physical_gamma_without_floor():
    clock = teacher.ClockState(0.0, 1e-24, 0.0, 1e-6, "active")
    value = teacher.conditional_values(
        100.0, 100.0, clock, teacher.CallParameters(0.0, 0.0, -0.05, 0.10), 0, 0.0
    )
    assert value[0] == pytest.approx(100 * np.sqrt(clock.variance / (2 * np.pi)), rel=1e-12)
    assert value[1] == pytest.approx(0.5, abs=1e-12)
    assert value[2] == pytest.approx(1 / (100 * np.sqrt(2 * np.pi * clock.variance)), rel=1e-12)


@pytest.mark.parametrize("spot", [90.0, 100.0, 110.0])
def test_expiry_payoff_defined_and_atm_ordinary_greeks_unknown(spot):
    clock = teacher.clock_state(EXPIRY, EXPIRY, event=True)
    result = teacher.mixture_values(spot, 100.0, clock, PARAMS)
    assert result["values"][0] == pytest.approx(max(spot - 100.0, 0.0))
    conditional = teacher.conditional_values(spot, 100.0, clock, PARAMS, 0, 0.0)
    raw = teacher.path_values(spot, 100.0, clock, PARAMS, 0, 0.0, 0.0)
    if spot == 100:
        assert np.isnan(result["values"][1:]).all()
        assert np.isnan(conditional[1:]).all()
        assert raw["delta_status"] == "undefined_atm"
        assert raw["gamma_status"] == "undefined_atm"
        assert result["reason"] == "ordinary_greeks_undefined_atm_expiry"
    else:
        assert result["values"][1:] == pytest.approx([float(spot > 100), 0.0])
        assert conditional == pytest.approx(result["values"])


def test_mixture_matches_existing_merton_and_tilted_tail_bounds_for_all_components():
    clock = state(30)
    for spot in [95.0, 100.0, 105.0]:
        full = teacher.mixture_values(spot, 100.0, clock, PARAMS, nmax=14)
        price = merton_jump_price(
            spot,
            100.0,
            PARAMS.rate,
            np.sqrt(clock.variance / clock.carry_years),
            clock.carry_years,
            clock.jump_mean_count / clock.carry_years,
            PARAMS.jump_mean,
            PARAMS.jump_std,
        )
        assert full["values"][0] == pytest.approx(price, abs=2e-12, rel=2e-11)
        partial = teacher.mixture_values(spot, 100.0, clock, PARAMS, nmax=0)
        tilt = clock.jump_mean_count * np.exp(PARAMS.jump_mean + PARAMS.jump_std**2 / 2)
        sf = poisson.sf(0, tilt)
        assert partial["tail_bounds"] == pytest.approx(
            [spot * sf, sf, sf / (spot * np.sqrt(2 * np.pi * clock.variance))]
        )
        assert np.all(full["values"] - partial["values"] >= -1e-12)
        assert np.all(full["values"] - partial["values"] <= partial["tail_bounds"] + 1e-12)
    assert teacher.mixture_values(100.0, 100.0, state(30, False), PARAMS)[
        "tail_bounds"
    ] == pytest.approx([0.0, 0.0, 0.0])


def test_raw_teachers_conditional_mean_martingale_and_log_variance_fixed_seed_six_se():
    clock = state(30)
    rng = np.random.default_rng(811)
    n = 300000
    counts = rng.poisson(clock.jump_mean_count, n)
    zb, zj = rng.standard_normal((2, n))
    raw = teacher.path_values(100.0, 100.0, clock, PARAMS, counts, zb, zj)
    expected = teacher.mixture_values(100.0, 100.0, clock, PARAMS)["values"]
    for key, component in [
        ("price", 0),
        ("pw_delta", 1),
        ("lr_delta", 1),
        ("lrpw_gamma", 2),
        ("lr2_gamma", 2),
    ]:
        samples = raw[key]
        assert (
            abs(samples.mean() - expected[component]) <= 6 * samples.std(ddof=1) / np.sqrt(n) + 1e-9
        )
    conditioned = teacher.conditional_values(100.0, 100.0, clock, PARAMS, counts, zj)
    assert np.all(
        np.abs(conditioned.mean(0) - expected) <= 6 * conditioned.std(0, ddof=1) / np.sqrt(n) + 1e-9
    )
    assert np.var(conditioned[:, 0]) < np.var(raw["price"])
    assert raw["naive_gamma"] == pytest.approx(np.zeros(n))
    terminal = raw["terminal_spot"]
    assert abs(terminal.mean() - 100 * np.exp(PARAMS.rate * clock.carry_years)) <= 6 * terminal.std(
        ddof=1
    ) / np.sqrt(n)
    logreturn = np.log(terminal / 100)
    squared = (logreturn - logreturn.mean()) ** 2
    target = clock.variance + clock.jump_mean_count * (PARAMS.jump_mean**2 + PARAMS.jump_std**2)
    assert abs(squared.mean() - target) <= 6 * squared.std(ddof=1) / np.sqrt(n)


def test_compact_reconstructs_full_iid_covariance_prefix_and_active_only_draw_counts():
    n = 10001
    clock = state(30)
    compact = teacher.compact_teacher(
        100.0, 100.0, clock, PARAMS, sample_count=n, count_seed=22, jump_seed=41
    )
    counts = np.random.default_rng(22).poisson(clock.jump_mean_count, n)
    indices = np.flatnonzero(counts)
    z = np.random.default_rng(41).standard_normal(len(indices))
    assert compact["active_indices"] == pytest.approx(indices)
    assert compact["active_counts"] == pytest.approx(counts[indices])
    assert compact["z_jump"] == pytest.approx(z)
    assert compact["actual_random_draws"] == n + len(indices)
    assert compact["normal_draw_policy"] == "active_only"
    full = np.repeat(compact["zero_values"][None, :], n, axis=0)
    full[indices] = teacher.conditional_values(100.0, 100.0, clock, PARAMS, counts[indices], z)
    for prefix in [101, 4000, n]:
        result = teacher.compact_moments(compact, sample_count=prefix)
        original = full[:prefix]
        assert result["count"] == prefix
        assert result["mean"] == pytest.approx(original.mean(0), rel=1e-12, abs=1e-13)
        assert result["covariance"] == pytest.approx(
            np.cov(original, rowvar=False), rel=1e-12, abs=1e-14
        )
        assert result["se"] == pytest.approx(
            original.std(0, ddof=1) / np.sqrt(prefix), rel=1e-12, abs=1e-14
        )
        assert result["active_count"] == np.count_nonzero(indices < prefix)


def test_analytic_zero_lambda_generates_no_randomness_and_does_not_claim_mc_count(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("analytic branch generated RNG")

    monkeypatch.setattr(np.random, "default_rng", forbidden)
    compact = teacher.compact_teacher(
        100.0, 100.0, state(30, False), PARAMS, sample_count=16384, count_seed=1, jump_seed=2
    )
    moments = teacher.compact_moments(compact)
    assert compact["actual_random_draws"] == 0
    assert compact["observed_mc_count"] == moments["count"] == 0
    assert moments["reserved_sample_count"] == 16384
    assert moments["status"] == "analytic_deterministic"
    assert moments["se"] == pytest.approx(np.zeros(3))
    assert moments["mean"] == pytest.approx(
        teacher.mixture_values(100.0, 100.0, state(30, False), PARAMS)["values"]
    )


@pytest.mark.parametrize(
    "active,status",
    [
        (0, "rare_event_unobserved"),
        (1, "rare_event_unresolved"),
        (99, "rare_event_unresolved"),
        (100, "ready"),
    ],
)
def test_rare_event_flags_preserve_finite_original_moments(active, status):
    n = 1000
    compact = dict(
        sample_count=n,
        reserved_sample_count=n,
        observed_mc_count=n,
        zero_count=n - active,
        zero_values=np.array([1.0, 0.5, 0.1]),
        active_indices=np.arange(active, dtype=np.int64),
        active_counts=np.ones(active, dtype=np.int64),
        z_jump=np.zeros(active),
        active_values=np.repeat([[2.0, 0.7, 0.2]], active, axis=0),
        status="ready",
        normal_draw_policy="active_only",
        actual_random_draws=n + active,
    )
    moments = teacher.compact_moments(compact)
    assert moments["status"] == status
    assert np.isfinite(moments["mean"]).all() and np.isfinite(moments["se"]).all()
    if active == 0:
        assert moments["se"] == pytest.approx([0.0, 0.0, 0.0])


def test_chan_covariance_large_offset_is_stable_and_singleton_active_allowed():
    offset = 1e12
    zero = np.array([offset, offset * 0.7, offset * 0.3])
    changes = np.array([[1.0, -0.2, 0.3], [2.0, 0.1, -0.4], [-1.0, 0.7, 0.6]])
    n = 10000
    active = zero + changes
    compact = dict(
        sample_count=n,
        reserved_sample_count=n,
        observed_mc_count=n,
        zero_count=n - 3,
        zero_values=zero,
        active_indices=np.array([2, 5, 9999]),
        active_counts=np.ones(3, dtype=np.int64),
        z_jump=np.zeros(3),
        active_values=active,
        status="ready",
        normal_draw_policy="active_only",
        actual_random_draws=n + 3,
    )
    relative = np.zeros((n, 3))
    relative[compact["active_indices"]] = active - zero
    moments = teacher.compact_moments(compact)
    assert moments["covariance"] == pytest.approx(
        np.cov(relative, rowvar=False), rel=1e-12, abs=1e-15
    )
    singleton = teacher.compact_moments(compact, sample_count=3)
    rel = np.array([np.zeros(3), np.zeros(3), active[0] - zero])
    assert singleton["covariance"] == pytest.approx(np.cov(rel, rowvar=False), rel=1e-12, abs=1e-15)


@pytest.mark.parametrize(
    "change", [dict(variance=-1.0), dict(jump_mean_count=-0.1), dict(carry_years=-1.0)]
)
def test_rejects_mathematically_invalid_state(change):
    data = dict(
        carry_years=0.01,
        variance=0.001,
        jump_mean_count=0.1,
        remaining_seconds=10.0,
        status="active",
    )
    data.update(change)
    with pytest.raises(ValueError):
        clock = teacher.ClockState(**data)
        teacher.mixture_values(100.0, 100.0, clock, PARAMS)


def test_rejects_invalid_counts_zero_spot_and_nonfinite_path_result():
    with pytest.raises(ValueError, match="count"):
        teacher.conditional_values(100.0, 100.0, state(), PARAMS, -1, 0.0)
    with pytest.raises(ValueError, match="positive"):
        teacher.conditional_values(0.0, 100.0, state(), PARAMS, 0, 0.0)
    with pytest.raises(ValueError, match=r"nonfinite|overflow"):
        teacher.path_values(100.0, 100.0, state(), PARAMS, 1, 0.0, 1e5)


def test_private_core_does_not_import_torch():
    code = "import sys,json; import hullkit._short_maturity_teachers; print(json.dumps('torch' in sys.modules))"
    result = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    )
    assert not json.loads(result.stdout)


def test_prefix_keeps_actual_full_generation_cost_separate_from_equivalent_prefix():
    compact = teacher.compact_teacher(
        100.0, 100.0, state(), PARAMS, sample_count=10000, count_seed=22, jump_seed=41
    )
    prefix = teacher.compact_moments(compact, sample_count=100)
    assert prefix["actual_random_draws"] == compact["actual_random_draws"]
    assert prefix["prefix_equivalent_draws"] == 100 + prefix["active_count"]


def test_lambda_zero_black_limit_with_dividend_and_vector_shape():
    clock = state(5, False)
    params = teacher.CallParameters(0.03, 0.07, -0.05, 0.10)
    spots = np.array([99.0, 100.0, 101.0])
    sigma = np.sqrt(clock.variance / clock.carry_years)
    expected = np.stack(
        [
            call_price(spots, 100.0, params.rate, sigma, clock.carry_years, params.dividend),
            call_delta(spots, 100.0, params.rate, sigma, clock.carry_years, params.dividend),
            gamma(spots, 100.0, params.rate, sigma, clock.carry_years, params.dividend),
        ],
        axis=-1,
    )
    conditioned = teacher.conditional_values(spots, 100.0, clock, params, 0, 0.0)
    mixture = teacher.mixture_values(spots, 100.0, clock, params)
    assert conditioned.shape == mixture["values"].shape == (3, 3)
    assert conditioned == pytest.approx(expected, rel=1e-10, abs=1e-12)
    assert mixture["values"] == pytest.approx(expected, rel=1e-10, abs=1e-12)
    tail = teacher.mixture_values(spots, 100.0, state(5), params, nmax=0)["tail_bounds"]
    sf = poisson.sf(0, state(5).jump_mean_count * np.exp(params.jump_mean + params.jump_std**2 / 2))
    assert tail[:, 1] == pytest.approx(
        np.repeat(np.exp(-params.dividend * clock.carry_years) * sf, 3)
    )


def test_expiry_compact_keeps_atm_unknown_reason_and_zero_random_draws():
    clock = teacher.clock_state(EXPIRY, EXPIRY, event=True)
    compact = teacher.compact_teacher(
        100.0, 100.0, clock, PARAMS, sample_count=10000, count_seed=1, jump_seed=2
    )
    moments = teacher.compact_moments(compact)
    assert moments["mean"][0] == pytest.approx(0.0)
    assert np.isnan(moments["mean"][1:]).all()
    assert moments["reason"] == "ordinary_greeks_undefined_atm_expiry"
    assert moments["actual_random_draws"] == 0


def test_pulse_and_clock_breaks_are_continuous_with_explicit_side_slopes():
    pulse_start = EXPIRY - timedelta(minutes=30)
    before = teacher.clock_state(pulse_start - timedelta(seconds=1), EXPIRY, event=True)
    at = teacher.clock_state(pulse_start, EXPIRY, event=True)
    after = teacher.clock_state(pulse_start + timedelta(seconds=1), EXPIRY, event=True)
    assert before.jump_mean_count == pytest.approx(at.jump_mean_count, abs=1e-15)
    assert at.jump_mean_count - after.jump_mean_count == pytest.approx(0.028 / 1800, rel=1e-12)
    for remaining, left_weight, right_weight in [(331.5, 2.0, 0.5), (58.5, 0.5, 2.0)]:
        middle = EXPIRY - timedelta(minutes=remaining)
        left = teacher.clock_state(middle - timedelta(seconds=1), EXPIRY, event=False)
        mid = teacher.clock_state(middle, EXPIRY, event=False)
        right = teacher.clock_state(middle + timedelta(seconds=1), EXPIRY, event=False)
        factor = 0.2**2 / (252 * 0.95 * 23400)
        assert left.variance - mid.variance == pytest.approx(
            left_weight * factor, rel=1e-10, abs=1e-18
        )
        assert mid.variance - right.variance == pytest.approx(
            right_weight * factor, rel=1e-10, abs=1e-18
        )
