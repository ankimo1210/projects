"""Independent §28.6 private interfaces; copied into the M31 branch at Task 1."""

import math

import numpy as np
import pytest


def forward_black_price(*args, **kwargs):
    from hullkit._forward_black import forward_black_price as price

    return price(*args, **kwargs)


def gaussian_forward_statistics(*args, **kwargs):
    from hullkit._forward_black import gaussian_forward_statistics as statistics

    return statistics(*args, **kwargs)


def pure_price(discount, forward, strike, sigma, horizon, kind):
    w = sigma * math.sqrt(horizon)
    if w == 0:
        return discount * max((forward - strike) if kind == "call" else (strike - forward), 0)
    d1 = (math.log(forward / strike) + w * w / 2) / w
    d2 = d1 - w

    def cdf(x):
        return math.erfc(-x / math.sqrt(2)) / 2

    if kind == "call":
        return discount * (forward * cdf(d1) - strike * cdf(d2))
    return discount * (strike * cdf(-d2) - forward * cdf(-d1))


@pytest.mark.parametrize("kind", ["call", "put"])
@pytest.mark.parametrize("strike", [70.0, 105.0, 140.0])
@pytest.mark.parametrize("rho", [-0.75, 0.0, 0.75])
def test_price_is_forward_under_payment_measure(kind, strike, rho):
    T, eta, sigma, r0 = 2.0, 0.03, 0.25, 0.04
    discount = math.exp(-r0 * T + eta * eta * T**3 / 6)
    forward = 100 / discount
    variance = eta * eta * T**3 / 3 + sigma * sigma * T + rho * eta * sigma * T * T
    effective = math.sqrt(variance / T)
    expected = pure_price(discount, forward, strike, effective, T, kind)
    assert forward_black_price(discount, forward, strike, effective, T, kind) == pytest.approx(
        expected, rel=1e-11, abs=1e-11
    )


@pytest.mark.parametrize("T,sigma", [(0.0, 0.25), (1.0, 0.0), (1e-8, 0.25), (1.0, 1e-8)])
@pytest.mark.parametrize("F,K", [(80.0, 100.0), (100.0, 100.0), (125.0, 100.0)])
def test_zero_and_small_horizon_or_volatility_parity(T, sigma, F, K):
    discount = 1.0 if T == 0 else math.exp(-0.04 * T)
    call = forward_black_price(discount, F, K, sigma, T, "call")
    put = forward_black_price(discount, F, K, sigma, T, "put")
    assert call >= 0 and put >= 0
    assert call - put == pytest.approx(discount * (F - K), abs=1e-11)
    assert call == pytest.approx(pure_price(discount, F, K, sigma, T, "call"), abs=1e-11)
    assert put == pytest.approx(pure_price(discount, F, K, sigma, T, "put"), abs=1e-11)


def test_tiny_atm_time_value_is_not_lost_to_cdf_subtraction():
    sigma = 1e-12
    expected = 1.04 * 100 * math.erf(sigma / (2 * math.sqrt(2)))
    actual = forward_black_price(1.04, 100, 100, sigma, 1.0)
    assert actual > 0
    assert actual == pytest.approx(expected, rel=1e-10, abs=1e-25)


@pytest.mark.parametrize("rho", [-1.0, -0.75, 0.0, 0.75, 1.0])
def test_gaussian_statistics_discount_forward_futures_and_terminal_variance(rho):
    T, r, eta, sigma, S = 2.0, 0.04, 0.03, 0.25, 100.0
    row = gaussian_forward_statistics(S, r, eta, sigma, rho, T)
    vj = eta * eta * T**3 / 3
    vy = vj + sigma * sigma * T + rho * eta * sigma * T * T
    p = math.exp(-r * T + vj / 2)
    assert row["discount"] == pytest.approx(p, rel=1e-13)
    assert row["forward"] == pytest.approx(S / p, rel=1e-13)
    assert row["futures"] == pytest.approx(
        S * math.exp(r * T + vj / 2 + rho * eta * sigma * T * T / 2), rel=1e-13
    )
    assert row["terminal_variance"] == pytest.approx(vy, abs=1e-14)
    assert row["forward_sigma"] == pytest.approx(math.sqrt(vy / T), rel=1e-13)
    assert row["mean_log_spot_Q"] == pytest.approx(math.log(S) + r * T - sigma * sigma * T / 2)
    assert row["cov_integral_log_spot"] == pytest.approx(vj + rho * eta * sigma * T * T / 2)
    assert row["mean_integral"] == pytest.approx(r * T)
    assert row["variance_integral"] == pytest.approx(vj)


def test_rank_one_driving_brownian_still_has_nonzero_integral_bridge_variance():
    T, eta = 2.0, 0.03
    row = gaussian_forward_statistics(100, 0.04, eta, eta * T / 2, -1.0, T)
    assert row["terminal_variance"] == pytest.approx(eta * eta * T**3 / 12, rel=1e-13)
    assert row["terminal_variance"] > 0


def test_horizon_zero_and_negative_interest_rates_are_supported():
    zero = gaussian_forward_statistics(100, -0.02, 0.03, 0.25, 0.5, 0.0)
    assert zero["discount"] == 1 and zero["forward"] == 100 and zero["futures"] == 100
    assert zero["terminal_variance"] == 0 and zero["forward_sigma"] == 0.25
    negative = gaussian_forward_statistics(100, -0.02, 0.03, 0.25, 0.5, 2.0)
    assert negative["discount"] > 1
    assert (
        forward_black_price(
            negative["discount"], negative["forward"], 100, negative["forward_sigma"], 2
        )
        > 0
    )


def test_scalar_and_leading_batch_shapes():
    assert isinstance(forward_black_price(0.93, 98, 100, 0.35, 0.5), float)
    actual = forward_black_price(
        np.array([[0.93], [1.04]]), np.array([98.0, 102.0, 105.0]), 100, 0.35, 0.5
    )
    assert actual.shape == (2, 3)
    for i, p in enumerate([0.93, 1.04]):
        for j, F in enumerate([98.0, 102.0, 105.0]):
            assert actual[i, j] == pytest.approx(
                pure_price(p, F, 100, 0.35, 0.5, "call"), abs=1e-11
            )
    rows = gaussian_forward_statistics(
        100, np.array([0.04, -0.02]), 0.03, 0.25, 0.5, np.array([[1.0], [2.0]])
    )
    assert all(value.shape == (2, 2) for value in rows.values())
    assert forward_black_price(np.array([]), 100, 100, 0.25, 1).shape == (0,)


@pytest.mark.parametrize(
    "bad",
    [
        True,
        [1.0, True],
        "1",
        1j,
        np.nan,
        np.inf,
        np.datetime64("2026-10-04"),
        np.timedelta64(1, "D"),
        np.array([1.0], dtype=object),
    ],
)
@pytest.mark.parametrize("index", range(5))
def test_price_rejects_nonfinite_nonreal_and_implicit_time_units_before_float(index, bad):
    values = [0.93, 100, 105, 0.25, 1]
    values[index] = bad
    with pytest.raises(ValueError):
        forward_black_price(*values)


@pytest.mark.parametrize("index,bad", [(0, 0), (0, -1), (1, 0), (2, -1), (3, -0.01), (4, -1)])
def test_invalid_domain_cannot_be_hidden_by_empty_batch(index, bad):
    values = [np.array([]), 100, 105, 0.25, 1.0]
    if index == 0:
        values[1] = np.array([])
    values[index] = bad
    with pytest.raises(ValueError):
        forward_black_price(*values)


@pytest.mark.parametrize("kind", [True, 1, "CALL", "other", [], None])
def test_kind_requires_explicit_call_or_put(kind):
    with pytest.raises(ValueError):
        forward_black_price(0.93, 100, 105, 0.25, 1, kind)


@pytest.mark.parametrize(
    "index,bad",
    [
        (0, 0),
        (2, -0.01),
        (3, -0.01),
        (4, 1.00001),
        (4, -1.00001),
        (5, -1),
        (1, np.datetime64("2026-10-04")),
        (2, True),
        (3, [0.25, True]),
    ],
)
def test_gaussian_statistics_invalid_domain_and_types(index, bad):
    values = [100, 0.04, 0.03, 0.25, 0.5, 2.0]
    values[index] = bad
    with pytest.raises(ValueError):
        gaussian_forward_statistics(*values)


def test_unrepresentable_statistics_fail_explicitly():
    with pytest.raises(ValueError):
        gaussian_forward_statistics(100, 1000, 0.03, 0.25, 0.5, 2.0)
    with pytest.raises(ValueError):
        gaussian_forward_statistics(100, 0.04, 1e300, 0.25, 0.5, 2.0)
