"""Tests for laplace_book.discrete (the z-transform / discrete bridge)."""

import numpy as np
from laplace_book import discrete as D


def test_numeric_ztransform_geometric():
    seq = D.geometric_sequence(0.5, 300)  # 0.5^k
    # sum_k a^k z^{-k} = z/(z-a) for |z| > |a|.
    assert abs(D.numeric_ztransform(seq, 2.0) - 2.0 / (2.0 - 0.5)) < 1e-6
    assert abs(D.numeric_ztransform(seq, 1.0 + 1j) - (1 + 1j) / (1 + 1j - 0.5)) < 1e-5


def test_s_to_z_maps_stability_region():
    assert abs(D.s_to_z(-1 + 2j, 0.1)) < 1.0  # LHP -> inside the unit circle
    assert abs(D.s_to_z(1 + 0j, 0.1)) > 1.0  # RHP -> outside
    assert abs(abs(D.s_to_z(3j, 0.1)) - 1.0) < 1e-12  # imaginary axis -> unit circle


def test_discrete_stability():
    assert D.is_stable_discrete(D.discrete_tf([1.0], [1.0, -0.5], 0.1))  # pole at z=0.5
    assert not D.is_stable_discrete(D.discrete_tf([1.0], [1.0, -1.5], 0.1))  # pole at z=1.5


def test_discrete_step_converges_to_dc_gain():
    # H(z) = 0.5/(z - 0.5): DC gain H(1) = 0.5/0.5 = 1.
    _, y = D.discrete_step_response(D.discrete_tf([0.5], [1.0, -0.5], 0.1), n=40)
    assert abs(y[-1] - 1.0) < 1e-2
