"""Hull21.5: deterministic curves and a recombining variance clock."""

import math
from itertools import product

import numpy as np
import pytest
from hullkit import _numerical_trees as numerical
from hullkit import bsm
from scipy.linalg import solve_banded

EDGES = np.array([0, 0.25, 0.6, 1])
VARIANCE = np.array([0.04, 0.09, 0.16])
RATES = np.array([0.01, 0.04, 0.07])
YIELDS = np.array([0.02, 0.01, 0.03])


def independent_time_pde(spot, strike, edges, variance, rates, yields, n_s=800, n_t=2400):
    width = math.log(6)
    x = np.linspace(math.log(spot) - width, math.log(spot) + width, n_s + 1)
    stock = np.exp(x)
    dx, dt = x[1] - x[0], edges[-1] / n_t
    value = np.maximum(strike - stock, 0)
    for step in range(n_t - 1, -1, -1):
        t = step * dt
        segment = min(np.searchsorted(edges, t + dt / 2, side="right") - 1, len(variance) - 1)
        v, r, q = variance[segment], rates[segment], yields[segment]
        diffusion = v / (2 * dx**2)
        drift = (r - q - v / 2) / (2 * dx)
        lo, di, hi = diffusion - drift, -2 * diffusion - r, diffusion + drift
        matrix = np.zeros((3, n_s - 1))
        matrix[0, 1:] = -0.5 * dt * hi
        matrix[1] = 1 - 0.5 * dt * di
        matrix[2, :-1] = -0.5 * dt * lo
        remaining = np.maximum(edges[1:] - np.maximum(edges[:-1], t), 0)
        low = max(
            strike * math.exp(-np.dot(rates, remaining))
            - stock[0] * math.exp(-np.dot(yields, remaining)),
            strike - stock[0],
        )
        rhs = value[1:-1] + 0.5 * dt * (lo * value[:-2] + di * value[1:-1] + hi * value[2:])
        rhs[0] += 0.5 * dt * lo * low
        value = np.concatenate(([low], solve_banded((1, 1), matrix, rhs), [0]))
        value = np.maximum(value, strike - stock)
    return float(value[n_s // 2])


def test_equal_variance_clock_nonuniform_calendar_nodes():
    result = numerical.variance_clock([0, 0.25, 1], [0.04, 0.16], 4)
    assert result["times"] == pytest.approx([0, 0.390625, 0.59375, 0.796875, 1], abs=1e-12)
    assert result["total_variance"] == pytest.approx(0.13, abs=1e-12)
    assert result["variance_per_step"] == pytest.approx(0.0325, abs=1e-12)


def test_constant_curves_reduce_to_source_crr_price():
    result = numerical.time_dependent_lattice(
        50, 50, [0, 5 / 12], [0.4**2], [0.1], [0], 50, kind="put", american=True
    )
    assert result["price"] == pytest.approx(4.272021, abs=1e-6)
    assert result["times"] == pytest.approx(np.linspace(0, 5 / 12, 51), abs=1e-12)


def test_zero_forward_variance_interval_keeps_calendar_endpoints():
    result = numerical.variance_clock([0, 0.25, 0.75, 1], [0, 0.04, 0], 4)
    assert result["times"] == pytest.approx([0, 0.375, 0.5, 0.625, 1], abs=1e-12)
    tree = numerical.time_dependent_lattice(
        100, 100, [0, 0.25, 0.75, 1], [0, 0.04, 0], [0, 0, 0], [0, 0, 0], 400
    )
    assert tree["price"] == pytest.approx(
        bsm.call_price(100, 100, 0, math.sqrt(0.02), 1), abs=0.004
    )


@pytest.mark.parametrize("kind", ["call", "put"])
def test_european_integrated_bsm_limit(kind):
    result = numerical.time_dependent_lattice(
        100, 105, EDGES, VARIANCE, RATES, YIELDS, 1200, kind=kind
    )
    widths = np.diff(EDGES)
    vol = math.sqrt(np.dot(VARIANCE, widths))
    r, q = np.dot(RATES, widths), np.dot(YIELDS, widths)
    reference = (bsm.call_price if kind == "call" else bsm.put_price)(100, 105, r, vol, 1, q=q)
    assert result["price"] == pytest.approx(reference, abs=0.005)


def test_integrated_discounts_and_local_branch_growth():
    result = numerical.time_dependent_lattice(100, 105, EDGES, VARIANCE, RATES, YIELDS, 50)
    assert np.prod(result["discounts"]) == pytest.approx(
        math.exp(-np.dot(RATES, np.diff(EDGES))), abs=1e-12
    )
    p = result["probabilities"]
    assert p * result["up"] + (1 - p) * result["down"] == pytest.approx(
        result["growth_factors"], abs=1e-12
    )
    assert np.prod(result["growth_factors"]) == pytest.approx(
        math.exp(np.dot(RATES - YIELDS, np.diff(EDGES))), abs=1e-12
    )


def test_european_independent_enumeration_with_time_specific_probabilities():
    result = numerical.time_dependent_lattice(100, 105, EDGES, VARIANCE, RATES, YIELDS, 3)
    total = 0
    for bits in product([0, 1], repeat=3):
        weight = np.prod(
            [p if up else 1 - p for p, up in zip(result["probabilities"], bits, strict=True)]
        )
        terminal = 100 * math.exp(
            (2 * sum(bits) - 3) * math.sqrt(np.dot(VARIANCE, np.diff(EDGES)) / 3)
        )
        total += weight * max(terminal - 105, 0)
    assert result["price"] == pytest.approx(
        total * math.exp(-np.dot(RATES, np.diff(EDGES))), abs=1e-11
    )


def test_american_independent_enumeration_of_all_stopping_policies():
    result = numerical.time_dependent_lattice(
        100, 105, EDGES, VARIANCE, RATES, YIELDS, 3, kind="put", american=True
    )
    policy_prices = []
    cumulative_r = np.r_[0, np.cumsum(RATES * np.diff(EDGES))]
    discount = np.exp(-np.interp(result["times"], EDGES, cumulative_r))
    for policy in range(64):
        price = 0
        for bits in product([0, 1], repeat=3):
            weight = np.prod(
                [p if up else 1 - p for p, up in zip(result["probabilities"], bits, strict=True)]
            )
            downs = 0
            for level in range(4):
                stop = level == 3 or (policy >> (level * (level + 1) // 2 + downs)) & 1
                stock = 100 * result["up"] ** (level - downs) * result["down"] ** downs
                if stop:
                    price += weight * max(105 - stock, 0) * discount[level]
                    break
                downs += 1 - bits[level]
        policy_prices.append(price)
    assert result["price"] == pytest.approx(max(policy_prices), abs=1e-11)


def test_american_time_curves_independent_cn_pde():
    result = numerical.time_dependent_lattice(
        100, 105, EDGES, VARIANCE, RATES, YIELDS, 1200, kind="put", american=True
    )
    independent = independent_time_pde(100, 105, EDGES, VARIANCE, RATES, YIELDS)
    assert result["price"] == pytest.approx(independent, abs=0.009)


def test_negative_forward_variance_is_not_clipped():
    with pytest.raises(ValueError):
        numerical.variance_clock([0, 0.5, 1], [0.04, -0.01], 10)


def test_coarse_clock_with_invalid_branch_probability_requests_refinement():
    with pytest.raises(ValueError):
        numerical.time_dependent_lattice(100, 105, [0, 1], [0.0001], [0.9], [0], 2)
