"""Tests for the educational scalar autograd engine."""

import math

from nn_textbook.autograd import Value, topological_order


def _numeric_grad(f, x, h=1e-6):
    """Central-difference derivative of scalar f at x."""
    return (f(x + h) - f(x - h)) / (2 * h)


def test_add_mul_pow_gradients():
    # f = a*b + a**2, check grads against calculus by hand.
    a = Value(3.0)
    b = Value(-2.0)
    out = a * b + a**2
    out.backward()
    assert out.data == 3.0 * -2.0 + 9.0
    assert a.grad == -2.0 + 2 * 3.0  # b + 2a
    assert b.grad == 3.0  # a


def test_tanh_matches_numeric():
    x = Value(0.7)
    y = x.tanh()
    y.backward()
    expected = _numeric_grad(lambda v: math.tanh(v), 0.7)
    assert abs(x.grad - expected) < 1e-6


def test_relu_gradient_both_sides():
    pos = Value(2.0)
    pos.relu().backward()
    assert pos.grad == 1.0
    neg = Value(-2.0)
    neg.relu().backward()
    assert neg.grad == 0.0


def test_reused_node_accumulates():
    # a used twice: d(a + a)/da = 2.
    a = Value(4.0)
    (a + a).backward()
    assert a.grad == 2.0


def test_division_and_chain():
    a = Value(2.0)
    b = Value(4.0)
    out = a / b  # = 0.5
    out.backward()
    assert abs(out.data - 0.5) < 1e-12
    # d(a/b)/da = 1/b = 0.25 ; d(a/b)/db = -a/b^2 = -0.125
    assert abs(a.grad - 0.25) < 1e-9
    assert abs(b.grad + 0.125) < 1e-9


def test_topological_order_is_valid():
    a = Value(1.0)
    b = Value(2.0)
    c = a * b
    d = c + a
    order = topological_order(d)
    # Every node must appear after all of its children (inputs).
    pos = {v: i for i, v in enumerate(order)}
    for node in order:
        for child in node._prev:
            assert pos[child] < pos[node]
    assert order[-1] is d


def test_full_expression_against_numeric():
    # f(x) = tanh(x * 2 + 1) then relu; compare grad to central difference.
    def f(v):
        x = Value(v)
        return (x * 2 + 1).tanh()

    x = Value(0.3)
    y = (x * 2 + 1).tanh()
    y.backward()
    expected = _numeric_grad(lambda v: math.tanh(v * 2 + 1), 0.3)
    assert abs(x.grad - expected) < 1e-6
