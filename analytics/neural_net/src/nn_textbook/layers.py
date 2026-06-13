"""NumPy educational layers with explicit forward / backward.

Every layer stores what it needs from the forward pass and returns the upstream
gradient on ``backward``. Shapes are written as comments so the notebooks can
reason about them. These mirror PyTorch's semantics closely enough that the
tests cross-check them against torch.
"""

from __future__ import annotations

import numpy as np


class Linear:
    """Affine layer: y = x W + b.   x:(N, in)  W:(in, out)  b:(out,)  y:(N, out)."""

    def __init__(self, n_in: int, n_out: int, seed: int = 0, init: str = "he"):
        rng = np.random.default_rng(seed)
        if init == "he":
            scale = np.sqrt(2.0 / n_in)
        elif init == "xavier":
            scale = np.sqrt(1.0 / n_in)
        else:
            scale = 0.01
        self.W = (rng.standard_normal((n_in, n_out)) * scale).astype(np.float64)
        self.b = np.zeros(n_out, dtype=np.float64)
        self.x = None
        self.dW = None
        self.db = None

    def forward(self, x):
        self.x = x
        return x @ self.W + self.b

    def backward(self, grad):
        # grad: (N, out). Chain rule through an affine map.
        self.dW = self.x.T @ grad  # (in, out)
        self.db = grad.sum(axis=0)  # (out,)
        return grad @ self.W.T  # (N, in) -> passed upstream

    def params_and_grads(self):
        return [(self.W, self.dW), (self.b, self.db)]


class ReLU:
    def forward(self, x):
        self.mask = x > 0
        return x * self.mask

    def backward(self, grad):
        return grad * self.mask


class Sigmoid:
    def forward(self, x):
        self.out = 1.0 / (1.0 + np.exp(-x))
        return self.out

    def backward(self, grad):
        return grad * self.out * (1.0 - self.out)


class Tanh:
    def forward(self, x):
        self.out = np.tanh(x)
        return self.out

    def backward(self, grad):
        return grad * (1.0 - self.out**2)


def softmax(logits):
    """Row-wise softmax with the standard max-subtraction for stability."""
    z = logits - logits.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


class MSELoss:
    """Mean squared error over all elements."""

    def forward(self, pred, target):
        self.pred = pred
        self.target = target
        self.n = pred.shape[0]
        return float(np.mean((pred - target) ** 2))

    def backward(self):
        # d/dpred mean((pred - target)^2) = 2 (pred - target) / num_elements
        return 2.0 * (self.pred - self.target) / self.pred.size


class CrossEntropyLoss:
    """Softmax + negative log-likelihood, averaged over the batch.

    forward(logits[N, C], targets[N] int) -> scalar loss.
    The backward gradient w.r.t. logits is the textbook (softmax - onehot) / N.
    """

    def forward(self, logits, targets):
        self.probs = softmax(logits)
        self.targets = targets
        self.n = logits.shape[0]
        log_likelihood = -np.log(self.probs[np.arange(self.n), targets] + 1e-12)
        return float(np.mean(log_likelihood))

    def backward(self):
        grad = self.probs.copy()
        grad[np.arange(self.n), self.targets] -= 1.0
        return grad / self.n
