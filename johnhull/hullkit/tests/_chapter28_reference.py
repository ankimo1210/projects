"""Independent chapter-28 display values and numerical acceptance adapter.

build() uses math/scipy and the existing pure-math §28.6 reference only.
Production imports are confined to verify(). All examples are synthetic.
"""

import math
from functools import lru_cache

from scipy.integrate import quad

from . import _forward_black_reference as black_teacher
from . import _forward_black_validation as black_validation


def _call(mean_log, variance, strike):
    if variance == 0:
        return max(math.exp(mean_log) - strike, 0)
    sd = math.sqrt(variance)
    boundary = (math.log(strike) - mean_log) / sd
    return quad(
        lambda z: (
            (math.exp(mean_log + sd * z) - strike) * math.exp(-z * z / 2) / math.sqrt(2 * math.pi)
        ),
        max(boundary, -12),
        12,
        epsabs=1e-10,
        epsrel=1e-11,
    )[0]


def _exchange(U, V, su, sv, rho, t, qu, qv):
    var = (su * su + sv * sv - 2 * rho * su * sv) * t
    mean = math.log(V / U) + (qu - qv) * t - var / 2
    return U * math.exp(-qu * t) * _call(mean, max(var, 0), 1)


def _bilinear(b, C, d):
    return math.fsum(b[i] * C[i][j] * d[j] for i in range(len(b)) for j in range(len(d)))


def _trace(role, x, y):
    return dict(role=role, x=x, y=y)


@lru_cache(maxsize=1)
def build():
    rows = {}
    rhos = [-1, -0.75, -0.5, -0.25, 0, 0.25, 0.5, 0.75, 1]
    vj = 0.03**2 * 2**3 / 3
    discount = math.exp(-0.04 * 2 + vj / 2)
    rows["martingale_black_forward_market"] = [
        _trace("forward", rhos, [100 / discount] * len(rhos)),
        _trace(
            "futures",
            rhos,
            [100 * math.exp(0.04 * 2 + vj / 2 + r * 0.03 * 0.25 * 2**2 / 2) for r in rhos],
        ),
    ]
    strikes = [70, 80, 90, 100, 105, 110, 120, 130, 140]
    variance = 0.25**2 * 2 + vj + 0.75 * 0.03 * 0.25 * 2**2
    q_mean = math.log(100) + 0.04 * 2 - 0.25**2 * 2 / 2
    cov = vj + 0.75 * 0.03 * 0.25 * 2**2 / 2
    rows["martingale_black_forward_prices"] = [
        _trace("black_T", strikes, [discount * _call(q_mean - cov, variance, k) for k in strikes]),
        _trace("outer_Q", strikes, [discount * _call(q_mean, variance, k) for k in strikes]),
    ]
    times = [0, 0.25, 0.5, 1, 1.5, 2]
    rows["martingale_exchange_ratio_means"] = [
        _trace("mean_given", times, [1.1 * math.exp(0.04 * t) for t in times]),
        _trace("mean_Q", times, [1.1 * math.exp(0.056 * t) for t in times]),
        _trace("no_income", times, [1.1] * len(times)),
    ]
    rhos = [-1, -0.5, 0, 0.4, 0.5, 1]
    rows["martingale_exchange_measure_prices"] = [
        _trace("income", rhos, [_exchange(100, 110, 0.25, 0.3, r, 1.5, 0.06, 0.02) for r in rhos]),
        _trace("no_income", rhos, [_exchange(100, 110, 0.25, 0.3, r, 1.5, 0, 0) for r in rhos]),
    ]
    rhos = [-1, -0.5, 0, 0.45, 1]
    delta = [-0.21, 0.09]
    correction = [_bilinear([0.2, -0.1], [[1, r], [r, 1]], delta) for r in rhos]
    rows["martingale_numeraire_drift_shift"] = [
        _trace("old", rhos, [0.08] * len(rhos)),
        _trace("new", rhos, [0.08 + x for x in correction]),
        _trace("restored", rhos, [0.08] * len(rhos)),
    ]
    states = [-20, 0, 50]
    C = [[1, 0.45, -0.3], [0.45, 1, 0.2], [-0.3, 0.2, 1]]
    old = [0.7 - 0.08 * x for x in states]
    new = [
        mu + _bilinear([3 + 0.005 * x, -1 + 0.002 * x, 2 - 0.001 * x], C, [-0.21, 0.09, 0.22])
        for x, mu in zip(states, old, strict=True)
    ]
    rows["martingale_numeraire_absolute_shift"] = [
        _trace("old", states, old),
        _trace("new", states, new),
    ]
    return dict(
        chapter=28,
        synthetic=True,
        printed_values=[],
        figures=rows,
        black=black_teacher.build(),
        physical_to_q=-0.052,
    )


def close_series(actual, expected):
    """Finite approximate comparisons; structure/roles still identify the lesson."""
    import numpy as np

    if set(actual) != set(expected):
        raise ValueError("chapter display figure set differs")
    error = 0.0
    for key, teacher in expected.items():
        if len(actual[key]) != len(teacher):
            raise ValueError(f"{key}: trace count differs")
        for a, b in zip(actual[key], teacher, strict=True):
            if a["role"] != b["role"]:
                raise ValueError(f"{key}: trace role differs")
            for axis in ("x", "y"):
                aa, bb = np.asarray(a[axis], dtype=float), np.asarray(b[axis], dtype=float)
                if (
                    aa.shape != bb.shape
                    or not np.all(np.isfinite(aa))
                    or not np.allclose(aa, bb, atol=1e-9, rtol=1e-10)
                ):
                    raise ValueError(f"{key}: numerical {axis} differs")
                error = max(error, float(np.max(np.abs(aa - bb))))
    return error


def verify(reference):
    from hullkit import _chapter28_lesson as lesson
    from hullkit import _numeraire_change as measure

    fresh = build()
    close_series(reference["figures"], fresh["figures"])
    black = black_validation.verify(reference["black"], reference=fresh["black"])
    display_error = close_series(lesson._series(), reference["figures"])
    if not math.isclose(
        measure.physical_to_q_drift(0.08, [0.2, -0.1, 0.15], [0.4, -0.25, 0.18]),
        reference["physical_to_q"],
        abs_tol=1e-12,
    ):
        raise ValueError("physical-to-Q drift differs")
    return dict(
        status="PASS",
        chapter=28,
        black=black,
        max_display_error=display_error,
        price_count=black["price_count"],
        max_mc_se=black["max_mc_se"],
        sections={
            "28.6": {
                "source_equations": "28.26–28.29",
                "independent": "Q/T quadrature, raw fixed-seed MC",
                "printed_values": [],
            },
            "28.7": {
                "source_equations": "28.30–28.32",
                "independent": "ratio quadrature; stochastic-rate MC in full suite",
                "printed_values": [],
            },
            "28.8": {
                "source_equations": "28.33–28.35",
                "independent": "covariance sum; Gaussian tilt/MC and TN20 in full suite",
                "printed_values": [],
            },
        },
    )
