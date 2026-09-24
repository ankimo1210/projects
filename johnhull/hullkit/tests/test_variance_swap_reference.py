"""Independent numerical references for Hull GE §26.16 (volatility and variance swaps).

The generator under test imports only NumPy/SciPy. hullkit is used here solely to
cross-check the generator's own Heston pricer against a second implementation.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

EX_STRIKES = [800.0, 850.0, 900.0, 950.0, 1000.0, 1050.0, 1100.0, 1150.0, 1200.0]
EX_VOLS = [0.29, 0.28, 0.27, 0.26, 0.25, 0.24, 0.23, 0.22, 0.21]
EX_Q_PRINTED = [2.22, 5.22, 11.05, 21.27, 51.21, 38.94, 20.69, 9.44, 3.57]
H1 = dict(v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.7)


def test_example_26_4_from_own_bsm():
    """Hull p.630: F0=1,027.68, S*=1,000, printed Q(K_i), strip 0.008139, E(V)=0.0621, 1.69."""
    from build_variance_swap_reference import example_26_4

    ex = example_26_4()
    assert ex["forward"] == pytest.approx(1027.68, abs=5e-3)
    assert ex["s_star"] == 1000.0
    assert ex["q_values"] == pytest.approx(EX_Q_PRINTED, abs=5e-3)
    assert ex["strip_sum"] == pytest.approx(0.008139, abs=5e-7)
    assert ex["expected_variance"] == pytest.approx(0.0621, abs=5e-5)
    assert ex["swap_value"] == pytest.approx(1.69, abs=5e-3)
    assert ex["printed_q_expected_variance"] == pytest.approx(0.0621, abs=5e-5)


def test_example_26_5_convexity():
    """Hull p.631: E(sigma)=0.2484 and a value of 1.82 ($m) against 23% on $100m."""
    from build_variance_swap_reference import example_26_5

    ex = example_26_5(0.0621)
    assert ex["expected_volatility"] == pytest.approx(0.2484, abs=5e-5)
    assert ex["swap_value"] == pytest.approx(1.82, abs=5e-3)
    assert ex["expected_volatility"] < math.sqrt(0.0621)


@pytest.mark.parametrize("s_star_ratio", [0.8, 1.0, 1.25])
def test_flat_smile_integral_is_sigma_squared_for_any_s_star(s_star_ratio):
    from build_variance_swap_reference import continuous_expected_variance, flat_pricer

    spot, rate, dividend, sigma, expiry = 100.0, 0.03, 0.01, 0.25, 0.5
    forward = spot * math.exp((rate - dividend) * expiry)
    value, error = continuous_expected_variance(
        flat_pricer(spot, rate, dividend, sigma, expiry),
        forward,
        rate,
        expiry,
        s_star=forward * s_star_ratio,
        log_range=(-12 * sigma * math.sqrt(expiry), 12 * sigma * math.sqrt(expiry)),
    )
    assert value == pytest.approx(sigma**2, abs=1e-9)
    assert error < 1e-9


def test_own_heston_pricer_matches_hullkit_and_parity():
    """hullkit's COS pricer (no dividend yield) is a second, differently built reference."""
    from build_variance_swap_reference import heston_call_put
    from hullkit import fourier, heston

    spot, rate, expiry = 100.0, 0.03, 0.5
    params = (H1["v0"], H1["kappa"], H1["theta"], H1["xi"], H1["rho"])

    def cf(u):
        return heston.heston_cf(u, rate, expiry, *params)

    for strike in (70.0, 100.0, 140.0):
        call, put = heston_call_put(spot, strike, rate, 0.0, expiry, **H1)
        other = fourier.cos_price(cf, spot, strike, rate, expiry, N=1024)
        assert call == pytest.approx(other, abs=1e-6)
        parity = spot - strike * math.exp(-rate * expiry)
        assert call - put == pytest.approx(parity, abs=1e-10)
    call_q, put_q = heston_call_put(spot, 100.0, rate, 0.01, expiry, **H1)
    assert call_q - put_q == pytest.approx(
        spot * math.exp(-0.01 * expiry) - 100.0 * math.exp(-rate * expiry), abs=1e-10
    )


def test_heston_replication_matches_closed_form_expected_variance():
    from build_variance_swap_reference import (
        continuous_expected_variance,
        heston_expected_variance,
        heston_pricer,
    )

    spot, rate, dividend, expiry = 100.0, 0.03, 0.01, 0.5
    forward = spot * math.exp((rate - dividend) * expiry)
    value, error = continuous_expected_variance(
        heston_pricer(spot, rate, dividend, expiry, **H1),
        forward,
        rate,
        expiry,
        s_star=forward,
        log_range=(-4.0, 2.5),
    )
    exact = heston_expected_variance(H1["v0"], H1["kappa"], H1["theta"], expiry)
    assert value == pytest.approx(exact, abs=1e-8)
    assert error < 1e-8


def test_integrated_variance_moments_and_laplace_limits():
    from build_variance_swap_reference import (
        cir_laplace_sqrt_mean,
        heston_expected_variance,
        heston_variance_of_variance,
    )

    # var(V) is exactly proportional to xi^2; xi -> 0 gives E[sqrt V] -> sqrt(E[V]).
    ev = heston_expected_variance(0.09, 2.0, 0.04, 0.25)
    small = heston_variance_of_variance(0.09, 2.0, 0.04, 1e-4, 0.25)
    large = heston_variance_of_variance(0.09, 2.0, 0.04, 0.5, 0.25)
    assert small / 1e-8 == pytest.approx(large / 0.25, rel=1e-12)
    assert cir_laplace_sqrt_mean(0.09, 2.0, 0.04, 1e-4, 0.25) == pytest.approx(
        math.sqrt(ev), abs=1e-9
    )
    # Eq. (26.9) is the second-order expansion: its error is O(xi^4), not O(xi^2).
    var = heston_variance_of_variance(0.09, 2.0, 0.04, 0.01, 0.25)
    exact = cir_laplace_sqrt_mean(0.09, 2.0, 0.04, 0.01, 0.25)
    assert exact == pytest.approx(math.sqrt(ev) * (1 - var / (8 * ev**2)), abs=1e-9)
    assert math.sqrt(ev) - exact > 1e-6
    # v0 = theta: E[V] = theta exactly.
    assert heston_expected_variance(0.0621, 2.0, 0.0621, 0.25) == pytest.approx(0.0621, abs=1e-15)


def test_laplace_and_variance_formula_against_exact_cir_mc():
    from build_variance_swap_reference import (
        cir_integrated_variance_mc,
        cir_laplace_sqrt_mean,
        heston_expected_variance,
        heston_variance_of_variance,
    )

    params = dict(v0=0.0621, kappa=2.0, theta=0.0621, xi=0.6, expiry=0.25)
    mc = cir_integrated_variance_mc(**params, steps=250, paths=100_000, seed=20260925)
    mean_v = heston_expected_variance(params["v0"], params["kappa"], params["theta"], 0.25)
    var_v = heston_variance_of_variance(**params)
    sqrt_mean = cir_laplace_sqrt_mean(**params)
    assert abs(mc["mean"] - mean_v) < 4 * mc["mean_se"]
    assert abs(mc["sqrt_mean"] - sqrt_mean) < 4 * mc["sqrt_mean_se"]
    assert mc["variance"] == pytest.approx(var_v, rel=0.03)


def test_daily_realized_variance_expectation_under_gbm():
    """Zero-mean estimator with n prices: E = A (n-1)(s^2 + m^2) / denominator."""
    from build_variance_swap_reference import realized_variance_expectation, realized_variance_mc

    n, sigma, drift = 64, 0.25, 0.02
    for denominator in ("n-2", "n-1"):
        exact = realized_variance_expectation(n, sigma, drift, denominator=denominator)
        mc = realized_variance_mc(n, sigma, drift, denominator=denominator, paths=200_000, seed=7)
        assert abs(mc["mean"] - exact) < 4 * mc["mean_se"]
    ratio = realized_variance_expectation(n, sigma, drift, denominator="n-2") / (
        realized_variance_expectation(n, sigma, drift, denominator="n-1")
    )
    assert ratio == pytest.approx((n - 1) / (n - 2), rel=1e-15)


def test_strip_error_shrinks_with_grid_and_range():
    from build_variance_swap_reference import (
        discrete_strip_expected_variance,
        flat_pricer,
    )

    spot, rate, dividend, sigma, expiry = 100.0, 0.03, 0.01, 0.25, 0.5
    pricer = flat_pricer(spot, rate, dividend, sigma, expiry)
    forward = spot * math.exp((rate - dividend) * expiry)
    errors = [
        discrete_strip_expected_variance(
            pricer, np.arange(20.0, 400.0 + step / 2, step), forward, rate, expiry
        )
        - sigma**2
        for step in (10.0, 5.0, 2.5)
    ]
    assert errors[0] > errors[1] > errors[2] > 0.0
    narrow = discrete_strip_expected_variance(
        pricer, np.arange(80.0, 125.1, 2.5), forward, rate, expiry
    )
    assert narrow < sigma**2


def test_vix_truncation_and_flat_interpolation():
    from build_variance_swap_reference import vix_interpolate, vix_truncation_gap

    ratio = 1027.68 / 1000.0
    gap = vix_truncation_gap(ratio)
    assert gap == pytest.approx(2 * (ratio - 1) ** 3 / 3, rel=0.05)
    sigma = 0.2
    assert vix_interpolate(23 / 365, sigma**2 * 23 / 365, 37 / 365, sigma**2 * 37 / 365) == (
        pytest.approx(sigma, abs=1e-15)
    )


def test_generated_reference_matches_committed_bytes():
    """The generator must reproduce the committed files byte for byte (same as --check)."""
    import json

    from build_variance_swap_reference import build_artifacts

    reference, record = build_artifacts()
    folder = Path(__file__).resolve().parents[2] / "docs/validation/section-26-16"
    for name, value in (("reference.json", reference), ("numerical-check.json", record)):
        content = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        assert (folder / name).read_bytes() == content.encode("utf-8"), f"{name} is stale"
    assert record["status"] == "PASS"
    assert record["printed_anchors"]["example_26_4"]["expected_variance"] == pytest.approx(
        0.0621, abs=5e-5
    )
    assert reference["section"] == "26.16"
