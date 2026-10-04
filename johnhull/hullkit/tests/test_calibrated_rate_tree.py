"""§32.5 original HW/BK trees, DG201 dates and independent curve/price oracles."""

import importlib
import itertools
import math
from decimal import Decimal

import numpy as np
import pytest
from hullkit._fitted_short_rate import gaussian_fitted_bond
from hullkit._short_rate_bond_options import gaussian_bond_option

DAYS = (
    np.array([3, 31, 62, 94, 185, 367, 731, 1096, 1461, 1826, 2194, 2558, 2922, 3287, 3653]) / 365
)
ZEROS = (
    np.array(
        [
            5.01772,
            4.98284,
            4.97234,
            4.96157,
            4.99058,
            5.09389,
            5.79733,
            6.30595,
            6.73464,
            6.94816,
            7.08807,
            7.27527,
            7.30852,
            7.39790,
            7.49015,
        ]
    )
    / 100
)


def model():
    return importlib.import_module("hullkit._calibrated_rate_tree")


def small_df(t):
    return math.exp(
        -t
        * np.interp(
            t, [0.5, 1, 1.5, 2, 2.5, 3], [0.03430, 0.03824, 0.04183, 0.04512, 0.04812, 0.05086]
        )
    )


def source_df(t):
    return math.exp(-t * np.interp(t, DAYS, ZEROS))


@pytest.mark.parametrize("which,a,sigma,dt", [("hw", 0.1, 0.01, 1), ("bk", 0.22, 0.25, 0.5)])
def test_figures_32_6_7_8_original_nodes_and_independent_path_curve_price(which, a, sigma, dt):
    tree = model().build_rate_tree(np.arange(4) * dt, small_df, a, sigma, model=which)
    layers = tree["layers"]
    if which == "hw":
        expected = [[3.824], [6.937, 5.205, 3.473], [9.716, 7.984, 6.252, 4.520, 2.788]]
        qs = [[1], [0.1604, 0.6417, 0.1604], [0.0182, 0.1998, 0.4736, 0.2033, 0.0189]]
        for layer, prices, state in zip(layers[:3], expected, qs, strict=True):
            assert layer["rates"][::-1] * 100 == pytest.approx(prices, abs=0.0005)
            assert layer["state_prices"][::-1] == pytest.approx(state, abs=0.00005)
        assert layers[2]["states"][::-1] * 100 == pytest.approx(
            [3.464, 1.732, 0, -1.732, -3.464], abs=0.0005
        )
    else:
        expected = [[3.430], [5.642, 4.154, 3.058], [8.803, 6.481, 4.772, 3.513, 2.587]]
        logs = [[-3.373], [-2.875, -3.181, -3.487], [-2.430, -2.736, -3.042, -3.349, -3.655]]
        for layer, prices, x in zip(layers[:3], expected, logs, strict=True):
            assert layer["rates"][::-1] * 100 == pytest.approx(prices, abs=0.0005)
            assert np.log(layer["rates"][::-1]) == pytest.approx(x, abs=0.0005)
    # Independent enumeration, not the stored Arrow-Debreu propagation.
    total = 0
    for moves in itertools.product(range(3), repeat=3):
        node = 0
        weight = 1
        for i, move in enumerate(moves):
            layer = layers[i]
            weight *= layer["probabilities"][node, move] * math.exp(-layer["rates"][node] * dt)
            node = layer["successors"][node, move]
        total += weight
    assert total == pytest.approx(small_df(3 * dt), abs=2e-13)
    assert tree["max_curve_residual"] < 2e-13


def test_period_rate_conversion_reproduces_short_discount_and_instantaneous_formula():
    m = model()
    a = 0.1
    s = 0.01
    t = 2
    delta = 0.25
    T = 7
    r = 0.052

    def logdf(u):
        return -0.04 * u

    def fwd(u):
        return 0.04

    def discount(u):
        return math.exp(logdf(u))

    short = gaussian_fitted_bond(t, t + delta, r, a, s, logdf, fwd)
    R = -math.log(short) / delta
    converted = m.finite_period_gaussian_bond(t, T, R, delta, a, s, discount)
    exact = gaussian_fitted_bond(t, T, r, a, s, logdf, fwd)
    assert math.exp(-R * delta) == pytest.approx(short, abs=1e-14)
    assert converted == pytest.approx(exact, abs=1e-13)
    assert abs(gaussian_fitted_bond(t, T, R, a, s, logdf, fwd) - exact) > 1e-5
    assert m.finite_period_gaussian_bond(t, t + delta, R, delta, a, s, discount) == pytest.approx(
        short, abs=1e-13
    )


@pytest.mark.parametrize(
    "N,printed",
    [(10, 1.8468), (30, 1.8172), (50, 1.8057), (100, 1.8128), (200, 1.8090), (500, 1.8091)],
)
def test_table_32_3_all_original_tree_prices_and_finite_period_date_convention(N, printed):
    m = model()
    expiry = 3
    terminal_delta = float(DAYS[DAYS > expiry][0] - expiry)
    assert terminal_delta == pytest.approx(1 / 365, abs=1e-14)
    tree = m.build_rate_tree(
        np.linspace(0, expiry, N + 1), source_df, 0.1, 0.01, terminal_delta=terminal_delta
    )
    last = tree["layers"][-1]
    bonds = 100 * m.finite_period_gaussian_bond(
        3, 9, last["rates"], terminal_delta, 0.1, 0.01, source_df
    )
    price = float(last["state_prices"] @ np.maximum(63 - bonds, 0))
    assert price == pytest.approx(printed, abs=0.00005)
    assert tree["max_curve_residual"] < 2e-12
    assert tree["min_probability"] >= 0
    if N == 500:
        analytic = gaussian_bond_option(
            3, 9, 0.1, 0.01, source_df(3), source_df(9), 63, principal=100, kind="put"
        )["price"]
        assert analytic == pytest.approx(1.8093, abs=0.00005)
        assert abs(price - analytic) < 0.0004


FIGURE = [
    [("99.51021", ".671933", "5.0000")],
    [
        ("94.69", ".058227", "6.1362"),
        ("101.4979", ".471654", "4.9633"),
        ("107.6802", "2.16306", "4.0146"),
    ],
    [
        ("87.0692", "0", "7.5348"),
        ("94.32588", ".017063", "6.0946"),
        ("100.9787", ".273599", "4.9297"),
        ("107.0004", "1.771632", "3.9874"),
        ("112.3922", "6.142178", "3.2253"),
    ],
    [
        ("79.19393", "0", "9.2572"),
        ("86.85737", "0", "7.4877"),
        ("93.96242", "0", "6.0565"),
        ("100.4532", ".09907", "4.8989"),
        ("106.3087", "1.275943", "3.9625"),
        ("111.5353", "5.910323", "3.2051"),
        ("116.1587", "10.53372", "2.5925"),
    ],
    [
        ("71.13165", "0", "11.3744"),
        ("79.13643", "0", "9.2003"),
        ("86.65577", "0", "7.4417"),
        ("93.60053", "0", "6.0193"),
        ("99.92196", "0", "4.8687"),
        ("105.6054", ".605443", "3.9381"),
        ("110.6623", "5.662307", "3.1854"),
        ("115.1222", "10.12224", "2.5765"),
        ("119.0263", "14.02632", "2.0840"),
    ],
]


def build_figure(N):
    m = model()
    payments = np.arange(0.5, 10.01, 0.5)
    coupons = np.full(20, 2.5)
    times, rate_dates = m.bond_option_source_mesh(1.5, N, payments, post_step_limit=0.125)
    tree = m.build_rate_tree(times, lambda t: math.exp(-0.05 * t), 0.05, 0.20, model="bk")
    bonds = m.coupon_node_prices(tree, N, rate_dates, payments, coupons, principal=100)
    accrual = np.array([m.coupon_accrual(t, payments, coupons) for t in times[: N + 1]])
    payoffs = [np.maximum(b - 105 - ac, 0) for b, ac in zip(bonds, accrual, strict=True)]
    options = m.rollback_option(tree, payoffs, range(N + 1))
    return tree, bonds, options, accrual


def test_figure_32_9_all_75_printed_fields_from_complete_bk_tree():
    tree, bonds, options, accrual = build_figure(4)
    assert len(tree["layers"]) - 1 == 89
    assert tree["max_curve_residual"] < 2e-12
    assert tree["min_probability"] > 0
    assert accrual == pytest.approx([0, 1.875, 1.25, 0.625, 0], abs=1e-13)
    assert options["price"] == pytest.approx(0.671933, abs=0.0000005)
    for i, printed_row in enumerate(FIGURE):
        rows = np.column_stack(
            [bonds[i][::-1], options["values"][i][::-1], 100 * tree["layers"][i]["rates"][::-1]]
        )
        for actual, expected in zip(rows, printed_row, strict=True):
            for value, text in zip(actual, expected, strict=True):
                tolerance = (
                    1e-12
                    if text == "0"
                    else float(Decimal(5).scaleb(Decimal(text).as_tuple().exponent - 1))
                )
                assert value == pytest.approx(float(text), abs=tolerance, rel=0)
    assert [int(x.sum()) for x in options["early_exercise"]] == [0, 0, 1, 2, 0]


def test_figure_32_9_hundred_steps_and_bermudan_is_bounded_by_european_american():
    tree, bonds, american, accrual = build_figure(100)
    assert len(tree["layers"]) - 1 == 185
    assert american["price"] == pytest.approx(0.703, abs=0.0005)
    m = model()
    payoffs = [np.maximum(b - 105 - ac, 0) for b, ac in zip(bonds, accrual, strict=True)]
    european = m.rollback_option(tree, payoffs, [100])["price"]
    bermudan = m.rollback_option(tree, payoffs, [0, 25, 50, 75, 100])["price"]
    assert european <= bermudan <= american["price"]


def test_bk_negative_forward_feasibility_and_shifted_model_curve_fit():
    m = model()

    def negative(t):
        return math.exp(0.005 * t)

    with pytest.raises(ValueError):
        m.build_rate_tree([0, 0.5, 1], negative, 0.1, 0.2, model="bk")
    tree = m.build_rate_tree([0, 0.5, 1], negative, 0.1, 0.2, model="bk", rate_shift=0.01)
    assert tree["max_curve_residual"] < 1e-12
    assert all(np.all(x["rates"] > -0.01) for x in tree["layers"][:-1])
    gaussian = m.build_rate_tree([0, 0.5, 1], negative, 0.1, 0.01)
    assert gaussian["layers"][0]["rates"][0] < 0
