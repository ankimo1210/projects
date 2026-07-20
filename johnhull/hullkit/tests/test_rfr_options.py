"""Bachelier and numerical-teacher tests for RFR options."""

import numpy as np
import pytest
from hullkit import rfr_options


def test_bachelier_parity_delta_and_zero_vol_limit() -> None:
    call = rfr_options.bachelier_price(0.02, 0.015, 0.01, 2.0, discount_factor=0.98)
    put = rfr_options.bachelier_price(0.02, 0.015, 0.01, 2.0, discount_factor=0.98, kind="put")
    assert call - put == pytest.approx(0.98 * (0.02 - 0.015))
    assert 0.0 < rfr_options.bachelier_delta(0.02, 0.015, 0.01, 2.0) < 1.0
    assert rfr_options.bachelier_price(-0.01, -0.02, 0.0, 1.0) == pytest.approx(0.01)


def test_adaptive_quadrature_teacher_agrees_with_bachelier() -> None:
    analytic = rfr_options.bachelier_price(0.02, 0.02, 0.01, 1.5)
    quadrature = rfr_options.gaussian_quadrature_price(0.02, 0.02, 0.01, 1.5)
    assert quadrature == pytest.approx(analytic, abs=1e-12)


def test_compounded_rate_mc_uses_exact_daily_factors() -> None:
    paths = np.array([[0.01, 0.02, 0.03], [0.02, 0.02, 0.02], [0.03, 0.02, 0.01]])
    counts = np.array([1, 3, 1])
    result = rfr_options.compounded_rate_option_mc(paths, counts, 0.015)
    expected = (np.prod(1.0 + paths * counts[None, :] / 360, axis=1) - 1.0) / (5 / 360)
    np.testing.assert_allclose(result.compounded_rates, expected)
    assert result.price == pytest.approx(np.maximum(expected - 0.015, 0.0).mean())
    assert result.standard_error >= 0.0
