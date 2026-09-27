import numpy as np
import pytest
from ratesvol.curves import discount_factor, instantaneous_forward, simple_forward

T = np.linspace(0, 10, 201)
Z = 0.02 + 0.03 * (1 - np.exp(-T / 5))


def test_instantaneous_forward_is_z_plus_t_dz_dt():
    exact = Z + T * 0.03 / 5 * np.exp(-T / 5)
    assert np.max(np.abs(instantaneous_forward(Z, T) - exact)) < 1e-4


def test_flat_curve_has_flat_forward():
    flat = np.full_like(T, 0.02)
    assert np.allclose(instantaneous_forward(flat, T), 0.02)


def test_discount_factor_and_simple_forward_are_consistent():
    p1, p2 = discount_factor(np.interp(2.0, T, Z), 2.0), discount_factor(np.interp(5.0, T, Z), 5.0)
    assert simple_forward(Z, T, 2.0, 5.0) == pytest.approx(np.log(p1 / p2) / 3.0)


def test_simple_forward_rejects_reversed_dates():
    with pytest.raises(ValueError):
        simple_forward(Z, T, 5.0, 2.0)
