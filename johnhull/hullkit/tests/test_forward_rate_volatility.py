"""§32.3 same 3-month tenor, units and independent bond-ratio shock variance."""

import importlib
import math

import numpy as np
import pytest
from scipy.linalg import expm


def model():
    return importlib.import_module("hullkit._forward_rate_volatility")


def test_figure_32_3_flat_decreasing_humped_shapes_use_same_quarterly_rate():
    m = model()
    horizons = np.linspace(0, 10, 41)
    delta = 0.25
    ratio = math.exp(0.04 * delta)

    def curve(a, b, s1, s2, rho):
        return [
            m.finite_tenor_forward_volatility(0, t, t + delta, a, b, s1, s2, rho, 1, 1 / ratio)[
                "normal_vol"
            ]
            for t in horizons
        ]

    ho = np.array(curve(0, 0, 0.01, 0, 0))
    hw = np.array(curve(1, 0.1, 0.01, 0, 0))
    two = np.array(curve(1, 0.1, 0.01, 0.0165, 0.6))
    assert ho == pytest.approx(np.full(len(horizons), ratio * 0.01), rel=1e-12)
    assert np.all(np.diff(hw) < 0)
    assert np.argmax(two) > 0 and two.max() > two[0] and two.max() > two[-1]
    row = m.finite_tenor_forward_volatility(0, 2, 2.25, 1, 0.1, 0.01, 0.0165, 0.6, 1, 1 / ratio)
    assert row["tenor"] == pytest.approx(0.25)
    assert row["black_equivalent_vol"] == pytest.approx(
        row["normal_vol"] / row["forward"], rel=1e-14
    )
    # Figure has no numerical curve/parameter pins; the two-factor inputs are synthetic.


@pytest.mark.parametrize(
    "a,b,s1,s2,rho",
    [
        (0, 0, 0.01, 0, 0),
        (1, 0.1, 0.01, 0, 0),
        (1, 0.1, 0.01, 0.0165, 0.6),
        (0.3, 0.3, 0.012, 0.02, -1),
        (0.3, 0.3, 0.012, 0.02, 1),
    ],
)
def test_instantaneous_forward_variance_matches_independent_block_exponential_and_small_time_mc(
    a, b, s1, s2, rho
):
    t = 0.5
    start = 2.0
    end = 2.25
    delta = end - start
    ratio = math.exp(0.04 * delta)
    row = model().finite_tenor_forward_volatility(t, start, end, a, b, s1, s2, rho, 1, 1 / ratio)
    A = np.array([[-a, 1, 0], [0, -b, 0], [1, 0, 0.0]])
    loading = (expm(A * (end - t)) - expm(A * (start - t)))[2, :2]
    instantaneous = np.array([[s1 * s1, rho * s1 * s2], [rho * s1 * s2, s2 * s2]])
    target = ratio * ratio / delta**2 * float(loading @ instantaneous @ loading)
    assert row["normal_vol"] ** 2 == pytest.approx(target, rel=1e-11, abs=1e-15)
    dt = 1e-6
    rng = np.random.default_rng(3232026)
    z = rng.standard_normal((2, 131072))
    shocks = np.array(
        [
            s1 * math.sqrt(dt) * z[0],
            s2 * math.sqrt(dt) * (rho * z[0] + math.sqrt(1 - rho * rho) * z[1]),
        ]
    )
    # Independent Gaussian bond ratios: log ratio shock is the integrated-state loading.
    change = ratio * np.expm1(loading @ shocks) / delta
    squared = change * change / dt
    se = squared.std(ddof=1) / math.sqrt(squared.size)
    assert abs(squared.mean() - target) < 5 * se


def test_zero_second_factor_matches_hw_and_zero_tenor_is_rejected():
    m = model()
    a = 0.2
    start = 3
    end = 3.25
    ratio = math.exp(0.04 * (end - start))
    row = m.finite_tenor_forward_volatility(0, start, end, a, 0.7, 0.012, 0, 0.8, 1, 1 / ratio)
    expected = (
        ratio / (end - start) * 0.012 * math.exp(-a * start) * (-math.expm1(-a * (end - start))) / a
    )
    assert row["normal_vol"] == pytest.approx(expected, rel=1e-12)
    with pytest.raises(ValueError):
        m.finite_tenor_forward_volatility(0, 1, 1, a, 0.7, 0.012, 0, 0.8, 1, 1)


def test_zero_and_negative_forward_keep_normal_vol_without_black_relabeling():
    m = model()
    for ratio in [1, 0.999]:
        row = m.finite_tenor_forward_volatility(0, 1, 1.25, 0, 0, 0.01, 0, 0, 1, 1 / ratio)
        assert row["normal_vol"] > 0 and row["black_equivalent_vol"] is None
