import numpy as np
import pytest
from ratesvol.options import (
    bachelier_call,
    bachelier_delta,
    bachelier_gamma,
    bachelier_implied_vol,
    bachelier_put,
    bachelier_vega,
    bachelier_vega_per_bp,
    black76_call,
    black76_delta,
    black76_gamma,
    black76_implied_vol,
    black76_put,
    black76_vega_per_vol_pt,
)

F, K, T, SIG, SIG_N = 0.03, 0.032, 1.5, 0.25, 0.008


def test_black76_greeks_match_finite_differences():
    h = 1e-6
    fd_delta = (black76_call(F + h, K, T, SIG) - black76_call(F - h, K, T, SIG)) / (2 * h)
    h2 = 1e-5
    fd_gamma = (
        black76_call(F + h2, K, T, SIG)
        - 2 * black76_call(F, K, T, SIG)
        + black76_call(F - h2, K, T, SIG)
    ) / h2**2
    fd_vega_pt = black76_call(F, K, T, SIG + 0.005) - black76_call(F, K, T, SIG - 0.005)
    assert black76_delta(F, K, T, SIG) == pytest.approx(fd_delta, rel=1e-6)
    assert black76_gamma(F, K, T, SIG) == pytest.approx(fd_gamma, rel=1e-5)
    assert black76_vega_per_vol_pt(F, K, T, SIG) == pytest.approx(fd_vega_pt, rel=1e-4)


def test_bachelier_greeks_match_finite_differences():
    h = 1e-6
    fd_delta = (bachelier_call(F + h, K, T, SIG_N) - bachelier_call(F - h, K, T, SIG_N)) / (2 * h)
    h2 = 1e-5
    fd_gamma = (
        bachelier_call(F + h2, K, T, SIG_N)
        - 2 * bachelier_call(F, K, T, SIG_N)
        + bachelier_call(F - h2, K, T, SIG_N)
    ) / h2**2
    fd_vega_bp = bachelier_call(F, K, T, SIG_N + 0.5e-4) - bachelier_call(F, K, T, SIG_N - 0.5e-4)
    assert bachelier_delta(F, K, T, SIG_N) == pytest.approx(fd_delta, rel=1e-6)
    assert bachelier_gamma(F, K, T, SIG_N) == pytest.approx(fd_gamma, rel=1e-4)
    assert bachelier_vega_per_bp(F, K, T, SIG_N) == pytest.approx(fd_vega_bp, rel=1e-6)
    # the old notebook printed the per-unit vega as "per 1bp": the two differ by 1e4
    assert bachelier_vega(F, K, T, SIG_N) == pytest.approx(
        1e4 * bachelier_vega_per_bp(F, K, T, SIG_N)
    )


def test_put_call_parity():
    df = 0.97
    assert black76_call(F, K, T, SIG, df) - black76_put(F, K, T, SIG, df) == pytest.approx(
        df * (F - K)
    )
    assert bachelier_call(F, K, T, SIG_N, df) - bachelier_put(F, K, T, SIG_N, df) == pytest.approx(
        df * (F - K)
    )


def test_bachelier_prices_negative_forwards_and_black_refuses_them():
    assert bachelier_call(-0.002, 0.0, 1.0, 0.006) > 0
    with pytest.raises(ValueError):
        black76_call(-0.002, 0.001, 1.0, 0.2)


@pytest.mark.parametrize("strike", [0.01, 0.02, 0.03, 0.04, 0.05])
def test_implied_vol_round_trip(strike):
    assert black76_implied_vol(black76_call(F, strike, T, SIG), F, strike, T) == pytest.approx(
        SIG, abs=1e-10
    )
    assert bachelier_implied_vol(
        bachelier_call(F, strike, T, SIG_N), F, strike, T
    ) == pytest.approx(SIG_N, abs=1e-12)


def test_implied_vol_is_nan_below_intrinsic():
    assert np.isnan(black76_implied_vol(0.0, F, 0.02, T))
    assert np.isnan(bachelier_implied_vol(0.0, F, 0.02, T))


def test_bachelier_implied_vol_works_for_negative_forwards():
    price = bachelier_call(-0.002, 0.001, 1.0, 0.006)
    assert bachelier_implied_vol(price, -0.002, 0.001, 1.0) == pytest.approx(0.006, abs=1e-12)


def test_black76_implied_vol_of_a_tiny_deep_otm_price_is_finite():
    assert np.isfinite(black76_implied_vol(1e-12, 0.03, 0.06, 1.0))
