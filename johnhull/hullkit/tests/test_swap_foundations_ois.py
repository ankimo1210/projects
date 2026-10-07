"""Hull Table7.3 OIS zero rates and Table7.2 hypothetical principal."""

import numpy as np
import pytest
from hullkit import _swap_foundations as s
from scipy.optimize import root

T = np.array([1 / 12, 0.25, 0.5, 1, 2, 5])
Q = np.array([0.018, 0.02, 0.022, 0.025, 0.03, 0.04])


def test_source_all_eight_values():
    curve = s.ois_bootstrap(T, Q)
    assert 100 * curve[1] == pytest.approx(
        [1.7987, 1.9950, 2.1880, 2.4693, 2.9994, 4.0401], abs=0.00005
    )
    a = s.swap_terminal_principal(1e8, 0.03, [0.038], 0.25)
    assert [a["floating"][-1] / 1000, -a["fixed"][-1] / 1000] == pytest.approx([100950, 100750])
    assert a["net"][-1] == pytest.approx(200000)


def test_independent_all_nodes_par_bond_system():
    schedules = []
    for t, q in zip(T, Q, strict=True):
        dates = np.array([t]) if t <= 1 else np.arange(0.25, t + 1e-10, 0.25)
        cash = (
            np.array([100 * (1 + q * t)])
            if t <= 1
            else np.r_[np.full(len(dates) - 1, 100 * q / 4), 100 + 100 * q / 4]
        )
        schedules.append((dates, cash))

    def residual(z):
        return [np.dot(cf, np.exp(-np.interp(ts, T, z) * ts)) - 100 for ts, cf in schedules]

    fit = root(residual, np.full(6, 0.03))
    assert fit.success
    assert s.ois_bootstrap(T, Q)[1] == pytest.approx(fit.x, abs=1e-9)
    assert residual(fit.x) == pytest.approx(np.zeros(6), abs=1e-7)
