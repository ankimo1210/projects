"""A tiny educational scalar autograd engine (micrograd-style).

Each ``Value`` wraps a single number and remembers how it was produced, so a
backward pass can apply the chain rule over the whole computation graph. This
is for *understanding* backprop in notebook 02 — not for real training.
"""

from __future__ import annotations

import math


class Value:
    """A scalar node in a computation graph.

    Attributes:
        data: the forward value.
        grad: d(output) / d(self), filled in by ``backward()``.
    """

    def __init__(self, data: float, _children: tuple = (), _op: str = "", label: str = ""):
        self.data = float(data)
        self.grad = 0.0
        self._backward = lambda: None  # local gradient rule, set by each op
        self._prev = set(_children)
        self._op = _op
        self.label = label

    def __repr__(self) -> str:
        return f"Value(data={self.data:.4f}, grad={self.grad:.4f}, op={self._op!r})"

    # -- core ops; each sets up the local derivative for the backward pass -----

    def __add__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data + other.data, (self, other), "+")

        def _backward():
            # d(a+b)/da = 1, d(a+b)/db = 1
            self.grad += out.grad
            other.grad += out.grad

        out._backward = _backward
        return out

    def __mul__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        out = Value(self.data * other.data, (self, other), "*")

        def _backward():
            # d(a*b)/da = b, d(a*b)/db = a
            self.grad += other.data * out.grad
            other.grad += self.data * out.grad

        out._backward = _backward
        return out

    def __pow__(self, exponent):
        assert isinstance(exponent, (int, float)), "only numeric powers supported"
        out = Value(self.data**exponent, (self,), f"**{exponent}")

        def _backward():
            # d(a**n)/da = n * a**(n-1)
            self.grad += exponent * self.data ** (exponent - 1) * out.grad

        out._backward = _backward
        return out

    def tanh(self):
        t = math.tanh(self.data)
        out = Value(t, (self,), "tanh")

        def _backward():
            # d(tanh)/dx = 1 - tanh(x)^2
            self.grad += (1 - t * t) * out.grad

        out._backward = _backward
        return out

    def relu(self):
        out = Value(max(0.0, self.data), (self,), "relu")

        def _backward():
            # d(relu)/dx = 1 if x > 0 else 0
            self.grad += (out.data > 0) * out.grad

        out._backward = _backward
        return out

    def exp(self):
        e = math.exp(self.data)
        out = Value(e, (self,), "exp")

        def _backward():
            self.grad += e * out.grad

        out._backward = _backward
        return out

    # -- convenience arithmetic ------------------------------------------------

    def __neg__(self):
        return self * -1

    def __sub__(self, other):
        return self + (-other if isinstance(other, Value) else Value(-other))

    def __radd__(self, other):
        return self + other

    def __rmul__(self, other):
        return self * other

    def __rsub__(self, other):
        return (-self) + other

    def __truediv__(self, other):
        other = other if isinstance(other, Value) else Value(other)
        return self * other**-1

    # -- backward pass ---------------------------------------------------------

    def backward(self):
        """Run reverse-mode autodiff: fill ``.grad`` for every ancestor node."""
        topo: list[Value] = []
        visited: set[Value] = set()

        def build(v: Value):
            if v not in visited:
                visited.add(v)
                for child in v._prev:
                    build(child)
                topo.append(v)

        build(self)
        self.grad = 1.0
        # Process nodes from output back to inputs (reverse topological order).
        for node in reversed(topo):
            node._backward()


def topological_order(root: Value) -> list[Value]:
    """Return the nodes of the graph rooted at ``root`` in topological order.

    Useful for drawing the computation graph in notebook 02.
    """
    topo: list[Value] = []
    visited: set[Value] = set()

    def build(v: Value):
        if v not in visited:
            visited.add(v)
            for child in v._prev:
                build(child)
            topo.append(v)

    build(root)
    return topo
