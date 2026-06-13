"""Tests for laplace_book.transforms (symbolic + numeric)."""

import numpy as np
import sympy as sp
from laplace_book import transforms as T


def test_table_pairs_roundtrip():
    # Every concrete table entry must satisfy L{f} = F (skip the symbolic-n row).
    n = sp.symbols("n", positive=True, integer=True)
    for f, F, _ in T.laplace_pairs():
        if f.has(n):
            continue
        assert T.verify_pair(f, F), f"pair failed: {f} -> {F}"


def test_derivative_rule_symbolic():
    a, w = sp.symbols("a omega", positive=True)
    assert T.verify_derivative_rule(sp.exp(-a * T.t))
    assert T.verify_derivative_rule(sp.sin(w * T.t))


def test_partial_fractions():
    F = 1 / ((T.s + 1) * (T.s + 2))
    expanded = T.partial_fractions(F)
    expected = 1 / (T.s + 1) - 1 / (T.s + 2)
    assert sp.simplify(expanded - expected) == 0


def test_numeric_laplace_real():
    # f = e^{-2t}  ->  F(s) = 1/(s+2). At s=3 that is 1/5.
    F = T.numeric_laplace(lambda x: np.exp(-2.0 * x), 3.0)
    assert abs(F - 0.2) < 1e-6


def test_numeric_laplace_complex():
    # f = e^{-t} -> F(s) = 1/(s+1). At s = i: 1/(1+i) = 0.5 - 0.5i.
    F = T.numeric_laplace(lambda x: np.exp(-x), 1j)
    assert abs(F - (0.5 - 0.5j)) < 1e-4


def test_numeric_laplace_array_matches_analytic():
    s_vals = np.array([1.0, 2.0, 4.0])
    F = T.numeric_laplace(lambda x: np.exp(-x), s_vals)
    np.testing.assert_allclose(F.real, 1.0 / (s_vals + 1.0), atol=1e-6)


def test_as_function_lambdify():
    f = T.as_function(sp.exp(-T.t))
    np.testing.assert_allclose(f(np.array([0.0, 1.0])), np.array([1.0, np.exp(-1.0)]), atol=1e-12)
