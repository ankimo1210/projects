"""Tests for the NumPy layers, cross-checked against PyTorch where it matters."""

import numpy as np
import pytest
from nn_textbook import layers


def test_linear_forward_shape_and_value():
    lin = layers.Linear(3, 2, seed=0)
    x = np.ones((4, 3))
    out = lin.forward(x)
    assert out.shape == (4, 2)
    np.testing.assert_allclose(out, x @ lin.W + lin.b)


def test_linear_backward_matches_torch():
    torch = pytest.importorskip("torch")
    rng = np.random.default_rng(0)
    x = rng.standard_normal((5, 3))
    lin = layers.Linear(3, 2, seed=1)
    out = lin.forward(x)
    grad_out = rng.standard_normal((5, 2))
    dx = lin.backward(grad_out)

    # Torch reference with the same weights.
    xt = torch.tensor(x, requires_grad=True)
    Wt = torch.tensor(lin.W, requires_grad=True)
    bt = torch.tensor(lin.b, requires_grad=True)
    out_t = xt @ Wt + bt
    out_t.backward(torch.tensor(grad_out))
    np.testing.assert_allclose(dx, xt.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(lin.dW, Wt.grad.numpy(), atol=1e-10)
    np.testing.assert_allclose(lin.db, bt.grad.numpy(), atol=1e-10)


@pytest.mark.parametrize("act_name", ["relu", "sigmoid", "tanh"])
def test_activation_backward_matches_torch(act_name):
    torch = pytest.importorskip("torch")
    rng = np.random.default_rng(2)
    x = rng.standard_normal((6, 4))
    act = {"relu": layers.ReLU, "sigmoid": layers.Sigmoid, "tanh": layers.Tanh}[act_name]()
    out = act.forward(x)
    grad_out = rng.standard_normal((6, 4))
    dx = act.backward(grad_out)

    xt = torch.tensor(x, requires_grad=True)
    fn = {"relu": torch.relu, "sigmoid": torch.sigmoid, "tanh": torch.tanh}[act_name]
    out_t = fn(xt)
    np.testing.assert_allclose(out, out_t.detach().numpy(), atol=1e-12)
    out_t.backward(torch.tensor(grad_out))
    np.testing.assert_allclose(dx, xt.grad.numpy(), atol=1e-10)


def test_softmax_rows_sum_to_one():
    rng = np.random.default_rng(3)
    logits = rng.standard_normal((7, 5))
    p = layers.softmax(logits)
    np.testing.assert_allclose(p.sum(axis=1), np.ones(7), atol=1e-12)
    assert (p > 0).all()


def test_cross_entropy_matches_torch():
    torch = pytest.importorskip("torch")
    rng = np.random.default_rng(4)
    logits = rng.standard_normal((8, 3))
    targets = rng.integers(0, 3, size=8)
    ce = layers.CrossEntropyLoss()
    loss = ce.forward(logits, targets)
    grad = ce.backward()

    lt = torch.tensor(logits, requires_grad=True)
    loss_t = torch.nn.functional.cross_entropy(lt, torch.tensor(targets))
    assert abs(loss - loss_t.item()) < 1e-10
    loss_t.backward()
    np.testing.assert_allclose(grad, lt.grad.numpy(), atol=1e-10)


def test_mse_loss_and_grad():
    rng = np.random.default_rng(5)
    pred = rng.standard_normal((4, 2))
    target = rng.standard_normal((4, 2))
    mse = layers.MSELoss()
    loss = mse.forward(pred, target)
    assert abs(loss - np.mean((pred - target) ** 2)) < 1e-12
    grad = mse.backward()
    np.testing.assert_allclose(grad, 2 * (pred - target) / pred.size, atol=1e-12)
