"""Hull21.2: index, currency and futures carry on the same lattice."""

import math

import pytest
from hullkit import _numerical_trees as numerical
from hullkit import bsm
from hullkit._binomial_foundations import small_tree_stopping_values
from hullkit.fd import fd_vanilla


@pytest.mark.parametrize("asset", ["futures", "currency"])
def test_figures_21_5_and_21_6_all_thirty_source_nodes(asset):
    if asset == "futures":
        result = numerical.carry_lattice(
            300, 300, 0.08, 0.3, 1 / 3, 4, asset=asset, kind="call", american=True
        )
        stocks = [
            [300],
            [327.14, 275.11],
            [356.73, 300, 252.29],
            [389, 327.14, 275.11, 231.36],
            [424.19, 356.73, 300, 252.29, 212.17],
        ]
        values = [
            [19.16],
            [33.64, 6.13],
            [56.73, 12.90, 0],
            [89, 27.14, 0, 0],
            [124.19, 56.73, 0, 0, 0],
        ]
        tol = 0.005
    else:
        result = numerical.carry_lattice(
            1.61, 1.60, 0.08, 0.12, 1, 4, asset=asset, yield_rate=0.09, kind="put", american=True
        )
        stocks = [
            [1.61],
            [1.7096, 1.5162],
            [1.8153, 1.61, 1.4279],
            [1.9275, 1.7096, 1.5162, 1.3448],
            [2.0467, 1.8153, 1.61, 1.4279, 1.2665],
        ]
        values = [
            [0.0710],
            [0.0249, 0.1136],
            [0, 0.0475, 0.1752],
            [0, 0, 0.0904, 0.2552],
            [0, 0, 0, 0.1721, 0.3335],
        ]
        tol = 0.00005
    for actual, source in zip(result["stock"], stocks, strict=True):
        assert actual == pytest.approx(source, abs=tol)
    for actual, source in zip(result["option"], values, strict=True):
        assert actual == pytest.approx(source, abs=tol)


@pytest.mark.parametrize(
    "asset,steps,printed",
    [
        ("futures", 50, 20.18),
        ("futures", 100, 20.22),
        ("currency", 50, 0.0738),
        ("currency", 100, 0.0738),
    ],
)
def test_source_higher_step_prices(asset, steps, printed):
    args = (300, 300, 0.08, 0.3, 1 / 3) if asset == "futures" else (1.61, 1.6, 0.08, 0.12, 1)
    result = numerical.carry_lattice(
        *args,
        steps,
        asset=asset,
        yield_rate=0.09,
        kind="call" if asset == "futures" else "put",
        american=True,
    )
    assert result["price"] == pytest.approx(printed, abs=0.005 if asset == "futures" else 0.00005)


@pytest.mark.parametrize(
    "asset,spot,strike,rate,sigma,time,q,kind",
    [
        ("futures", 300, 300, 0.08, 0.3, 1 / 3, 0.08, "call"),
        ("currency", 1.61, 1.6, 0.08, 0.12, 1, 0.09, "put"),
    ],
)
def test_american_carry_against_independent_stopping_policy(
    asset, spot, strike, rate, sigma, time, q, kind
):
    result = numerical.carry_lattice(
        spot, strike, rate, sigma, time, 4, asset=asset, yield_rate=q, kind=kind, american=True
    )
    independent = small_tree_stopping_values(
        spot, strike, rate, time, 4, result["up"], result["down"], kind=kind, q=q
    )
    assert result["price"] == pytest.approx(independent["price"], abs=1e-11)


@pytest.mark.parametrize(
    "asset,spot,strike,rate,sigma,time,q,kind",
    [
        ("futures", 300, 300, 0.08, 0.3, 1 / 3, 0.08, "call"),
        ("currency", 1.61, 1.6, 0.08, 0.12, 1, 0.09, "put"),
    ],
)
def test_american_carry_independent_fd_limit(asset, spot, strike, rate, sigma, time, q, kind):
    result = numerical.carry_lattice(
        spot, strike, rate, sigma, time, 1000, asset=asset, yield_rate=q, kind=kind, american=True
    )
    independent = fd_vanilla(
        spot, strike, rate, sigma, time, q=q, kind=kind, american=True, n_s=800, n_t=1500
    )
    assert result["price"] == pytest.approx(independent, abs=spot * 1e-4)


@pytest.mark.parametrize("asset,q", [("index", 0.02), ("currency", 0.09), ("futures", 0.08)])
def test_european_closed_form_and_branch_growth_discount_are_separate(asset, q):
    result = numerical.carry_lattice(50, 50, 0.08, 0.3, 0.5, 1000, asset=asset, yield_rate=q)
    assert result["price"] == pytest.approx(bsm.call_price(50, 50, 0.08, 0.3, 0.5, q=q), abs=0.003)
    assert result["effective_yield"] == pytest.approx(q, abs=1e-12)
    p, dt = result["probability"], result["dt"]
    growth = p * result["up"] + (1 - p) * result["down"]
    assert growth == pytest.approx(math.exp((0.08 - q) * dt), abs=1e-12)
    if asset == "futures":
        assert growth == pytest.approx(1, abs=1e-12)
        assert math.exp(-0.08 * dt) < 1


def test_unknown_asset_has_no_carry_convention():
    with pytest.raises(ValueError):
        numerical.carry_lattice(50, 50, 0.08, 0.3, 0.5, 4, asset="unknown")
