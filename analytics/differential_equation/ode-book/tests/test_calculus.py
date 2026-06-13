"""Tests for ode_book.calculus — checked against hand-computed values."""

import numpy as np
import sympy as sp
from ode_book import calculus


def test_numerical_derivative_matches_known_slopes():
    # sin'(0) = 1, (x^2)'(3) = 6
    assert abs(calculus.numerical_derivative(np.sin, 0.0) - 1.0) < 1e-7
    assert abs(calculus.numerical_derivative(lambda x: x**2, 3.0) - 6.0) < 1e-5


def test_second_derivative():
    # (x^2)'' = 2 everywhere
    assert abs(calculus.second_derivative(lambda x: x**2, 1.7) - 2.0) < 1e-4


def test_secant_slope_approaches_derivative():
    f = np.sin
    slopes = [calculus.secant_slope(f, 0.0, h) for h in (0.5, 0.1, 0.01)]
    # secant slopes -> cos(0) = 1 as h shrinks
    assert slopes[0] < slopes[1] < slopes[2] <= 1.0
    assert abs(slopes[-1] - 1.0) < 1e-2


def test_integration_rules_on_quadratic():
    f = lambda x: x**2  # integral over [0,1] is 1/3  # noqa: E731
    assert abs(calculus.riemann_sum(f, 0, 1, 200, "mid") - 1 / 3) < 1e-4
    assert abs(calculus.trapezoid(f, 0, 1, 200) - 1 / 3) < 1e-4
    # Simpson is exact (to round-off) for cubics and below
    assert abs(calculus.simpson(f, 0, 1, 10) - 1 / 3) < 1e-12
    assert abs(calculus.quad(f, 0, 1) - 1 / 3) < 1e-10


def test_integration_on_sine():
    # integral of sin over [0, pi] = 2
    assert abs(calculus.simpson(np.sin, 0, np.pi, 100) - 2.0) < 1e-4


def test_cumulative_integral_recovers_antiderivative():
    xs = np.linspace(0, np.pi, 400)
    F = calculus.cumulative_integral(np.cos, xs)  # should track sin(x)
    np.testing.assert_allclose(F, np.sin(xs), atol=2e-3)


def test_gradient_and_partials():
    f = lambda p: p[0] ** 2 + 3 * p[1] ** 2  # grad = (2x, 6y)  # noqa: E731
    g = calculus.gradient(f, [1.0, 2.0])
    np.testing.assert_allclose(g, [2.0, 12.0], atol=1e-4)
    assert abs(calculus.partial_derivative(f, [1.0, 2.0], 0) - 2.0) < 1e-4


def test_directional_derivative_equals_grad_dot_unit():
    f = lambda p: p[0] ** 2 + 3 * p[1] ** 2  # noqa: E731
    d = calculus.directional_derivative(f, [1.0, 2.0], [1.0, 0.0])
    assert abs(d - 2.0) < 1e-4  # along +x: equals df/dx = 2


def test_hessian_symmetric_and_correct():
    f = lambda p: p[0] ** 2 + p[0] * p[1] + 2 * p[1] ** 2  # noqa: E731
    H = calculus.hessian(f, [0.5, -0.3])
    np.testing.assert_allclose(H, [[2.0, 1.0], [1.0, 4.0]], atol=1e-3)
    np.testing.assert_allclose(H, H.T, atol=1e-10)


def test_taylor_series_of_exp():
    x = sp.symbols("x")
    poly = calculus.taylor_series(sp.exp(x), x, 0, 3)
    assert sp.simplify(poly - (1 + x + x**2 / 2 + x**3 / 6)) == 0


def test_taylor_approx_callable_matches_function_near_center():
    x = sp.symbols("x")
    approx = calculus.taylor_approx(sp.cos(x), x, 0.0, 4)
    # near 0 the 4th-order approx is very close to cos
    assert abs(approx(0.3) - np.cos(0.3)) < 1e-3
