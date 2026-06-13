"""Tests for the NumPy MLP, its training, and a couple of torch model smoke checks."""

import numpy as np
import pytest
from nn_textbook import datasets, metrics
from nn_textbook.models import MLP, LoRALinear
from nn_textbook.training import train_numpy_mlp


def test_mlp_backward_matches_numeric_gradient():
    # Gradient check the from-scratch MLP against central differences.
    rng = np.random.default_rng(0)
    X = rng.standard_normal((10, 3))
    y = rng.integers(0, 2, size=10)
    model = MLP([3, 8, 2], activation="tanh", seed=1)

    model.loss(X, y)
    model.backward()
    W = model.layers[0].W
    dW = model.layers[0].dW

    eps = 1e-5
    i, j = 1, 2
    orig = W[i, j]
    W[i, j] = orig + eps
    lp = model.loss(X, y)
    W[i, j] = orig - eps
    lm = model.loss(X, y)
    W[i, j] = orig
    numeric = (lp - lm) / (2 * eps)
    assert abs(dW[i, j] - numeric) < 1e-4


def test_mlp_trains_on_moons():
    X, y = datasets.make_moons_dataset(n=400, noise=0.2, seed=0)
    model = MLP([2, 32, 32, 2], activation="relu", seed=0)
    hist = train_numpy_mlp(model, X, y, lr=0.3, epochs=120, batch_size=32, seed=0)
    assert hist["loss"][-1] < hist["loss"][0]  # loss went down
    acc = metrics.accuracy(model.predict(X), y)
    assert acc > 0.95


def test_mlp_trains_on_circles_and_spiral():
    for maker in (
        lambda: datasets.make_circles_dataset(n=400, noise=0.08, seed=0),
        lambda: datasets.make_spiral_dataset(n_per_class=120, n_classes=3, seed=0),
    ):
        X, y = maker()
        n_classes = int(y.max()) + 1
        model = MLP([2, 64, 64, n_classes], activation="relu", seed=0)
        train_numpy_mlp(model, X, y, lr=0.3, epochs=200, batch_size=32, seed=0)
        assert metrics.accuracy(model.predict(X), y) > 0.9


def test_regression_mlp_fits_sine():
    x, y = datasets.make_regression_1d(n=200, noise=0.05, seed=0)
    model = MLP([1, 64, 64, 1], activation="tanh", task="regression", seed=0)
    hist = train_numpy_mlp(model, x, y, lr=0.05, epochs=400, batch_size=32, seed=0)
    assert hist["loss"][-1] < 0.05


def test_hidden_representation_shape():
    X, _y = datasets.make_moons_dataset(n=50, seed=0)
    model = MLP([2, 16, 2], activation="relu", seed=0)
    H = model.hidden_representation(X, layer_index=-2)
    assert H.shape == (50, 16)


def test_lora_param_count_and_init():
    rng = np.random.default_rng(0)
    W0 = rng.standard_normal((100, 80))
    lora = LoRALinear(W0, rank=4, alpha=8.0)
    # B starts at zero, so the initial effective weight equals W0.
    np.testing.assert_allclose(lora.effective_weight(), W0)
    assert lora.n_lora_params() == 100 * 4 + 4 * 80
    assert lora.n_lora_params() < lora.n_full_params()


def test_torch_mlp_forward_smoke():
    torch = pytest.importorskip("torch")
    from nn_textbook.models import make_torch_mlp

    net = make_torch_mlp([2, 16, 2])
    out = net(torch.randn(5, 2))
    assert out.shape == (5, 2)


def test_transformer_block_shapes_and_attention():
    torch = pytest.importorskip("torch")
    from nn_textbook.models import make_transformer_block

    blk = make_transformer_block(d_model=32, n_heads=4, d_ff=64)
    x = torch.randn(2, 6, 32)
    out, attn = blk(x)
    assert out.shape == (2, 6, 32)
    assert attn.shape == (2, 4, 6, 6)  # (batch, heads, query, key)
    # Attention rows are probability distributions.
    torch.testing.assert_close(attn.sum(-1), torch.ones(2, 4, 6), atol=1e-5, rtol=0)


def test_denoiser_forward_and_learns():
    torch = pytest.importorskip("torch")
    from nn_textbook.models import make_denoiser

    torch.manual_seed(0)
    den = make_denoiser(input_dim=1, hidden=32)
    x = torch.randn(64, 1)
    t = torch.rand(64, 1)
    assert den(x, t).shape == (64, 1)
    # A few steps of denoising training must reduce the loss.
    opt = torch.optim.Adam(den.parameters(), lr=1e-2)
    clean = torch.randn(256, 1)
    losses = []
    for _ in range(30):
        tt = torch.rand(256, 1)
        noisy = clean + 0.5 * torch.randn_like(clean)
        loss = ((den(noisy, tt) - clean) ** 2).mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(loss.item())
    assert losses[-1] < losses[0]


def test_linear_ssm_impulse_decays():
    import numpy as np
    from nn_textbook.models import linear_ssm_scan

    x = np.zeros(30)
    x[0] = 1.0  # impulse input
    y = linear_ssm_scan(x, A_diag=[0.8], B=[1.0], C=[1.0])
    # h_0 = B*1 = 1, y_0 = C@h_0 = 1; then geometric decay 0.8^t.
    np.testing.assert_allclose(y[:5], [0.8**t for t in range(5)], atol=1e-9)
    assert abs(y[-1]) < abs(y[0])


def test_linear_attention_shape_and_normalization():
    import numpy as np
    from nn_textbook.models import linear_attention

    rng = np.random.default_rng(0)
    Q, K, V = (rng.standard_normal((6, 8)) for _ in range(3))
    out = linear_attention(Q, K, V)
    assert out.shape == (6, 8)
    # If all values are identical, any convex-combination attention returns that value.
    Vc = np.ones((6, 4)) * 3.0
    out_c = linear_attention(Q, K, Vc)
    np.testing.assert_allclose(out_c, 3.0, atol=1e-6)
