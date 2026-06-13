"""Models for the textbook.

- ``MLP`` is a pure-NumPy multilayer perceptron built from ``layers.py`` and is
  the centerpiece of notebook 03 ("from scratch").
- The PyTorch models (TorchMLP, SmallCNN, recurrent wrappers, the transformer
  block, autoencoders, GAN parts, the denoiser) are thin, readable reference
  implementations used from notebook 04 onward. Torch is imported lazily so the
  NumPy-only notebooks and tests do not pay for it.
"""

from __future__ import annotations

import numpy as np

from .layers import CrossEntropyLoss, Linear, MSELoss, ReLU, Sigmoid, Tanh

_ACTIVATIONS = {"relu": ReLU, "sigmoid": Sigmoid, "tanh": Tanh}


class MLP:
    """NumPy multilayer perceptron for classification or regression.

    Architecture: Linear -> activation -> ... -> Linear (no final activation;
    the loss adds softmax / identity). Built so notebook 03 can read every step.
    """

    def __init__(
        self,
        sizes,
        activation: str = "relu",
        task: str = "classification",
        seed: int = 0,
        init: str = "he",
    ):
        self.task = task
        self.layers = []
        rng = np.random.default_rng(seed)
        act_cls = _ACTIVATIONS[activation]
        for i in range(len(sizes) - 1):
            self.layers.append(
                Linear(sizes[i], sizes[i + 1], seed=int(rng.integers(1 << 30)), init=init)
            )
            if i < len(sizes) - 2:  # no activation after the output layer
                self.layers.append(act_cls())
        self.loss_fn = CrossEntropyLoss() if task == "classification" else MSELoss()

    def forward(self, x):
        for layer in self.layers:
            x = layer.forward(x)
        return x

    def loss(self, x, target):
        logits = self.forward(x)
        return self.loss_fn.forward(logits, target)

    def backward(self):
        grad = self.loss_fn.backward()
        for layer in reversed(self.layers):
            grad = layer.backward(grad)
        return grad

    def params_and_grads(self):
        for layer in self.layers:
            if isinstance(layer, Linear):
                yield from layer.params_and_grads()

    def predict(self, x):
        out = self.forward(x)
        return out.argmax(axis=1) if self.task == "classification" else out

    def hidden_representation(self, x, layer_index: int = -2):
        """Activations at a chosen layer — used to show how data gets warped.

        layer_index counts Linear+activation entries in ``self.layers``.
        """
        for layer in self.layers[:layer_index]:
            x = layer.forward(x)
        return x


# ---------------------------------------------------------------------------
# PyTorch reference models (lazy torch import)
# ---------------------------------------------------------------------------


def _torch_nn():
    import torch.nn as nn

    return nn


def make_torch_mlp(sizes, activation: str = "relu", dropout: float = 0.0, batchnorm: bool = False):
    """Sequential PyTorch MLP. ``sizes`` includes input and output dims."""
    nn = _torch_nn()
    act = {"relu": nn.ReLU, "tanh": nn.Tanh, "sigmoid": nn.Sigmoid}[activation]
    layers = []
    for i in range(len(sizes) - 1):
        layers.append(nn.Linear(sizes[i], sizes[i + 1]))
        if i < len(sizes) - 2:
            if batchnorm:
                layers.append(nn.BatchNorm1d(sizes[i + 1]))
            layers.append(act())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
    return nn.Sequential(*layers)


def make_small_cnn(n_classes: int = 10, in_channels: int = 1):
    """Compact CNN for 28x28 images: 2 conv blocks + a classifier head."""
    nn = _torch_nn()
    return nn.Sequential(
        nn.Conv2d(in_channels, 16, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),  # 28 -> 14
        nn.Conv2d(16, 32, 3, padding=1),
        nn.ReLU(),
        nn.MaxPool2d(2),  # 14 -> 7
        nn.Flatten(),
        nn.Linear(32 * 7 * 7, 64),
        nn.ReLU(),
        nn.Linear(64, n_classes),
    )


def make_rnn(kind: str = "lstm", input_size: int = 1, hidden_size: int = 32, n_layers: int = 1):
    """Wrap nn.RNN/LSTM/GRU + a linear head for 1-step-ahead forecasting."""
    import torch.nn as nn

    rnn_cls = {"rnn": nn.RNN, "lstm": nn.LSTM, "gru": nn.GRU}[kind]

    class Forecaster(nn.Module):
        def __init__(self):
            super().__init__()
            self.rnn = rnn_cls(input_size, hidden_size, n_layers, batch_first=True)
            self.head = nn.Linear(hidden_size, 1)

        def forward(self, x):  # x: (B, T, input_size)
            out, _ = self.rnn(x)
            return self.head(out[:, -1, :])  # use the last time step -> (B, 1)

    return Forecaster()


class NumpyRNNCell:
    """A single vanilla RNN cell in NumPy (forward only) for notebook 06.

    h_t = tanh(x_t W_xh + h_{t-1} W_hh + b_h).
    """

    def __init__(self, input_size: int, hidden_size: int, seed: int = 0):
        rng = np.random.default_rng(seed)
        s = 1.0 / np.sqrt(hidden_size)
        self.W_xh = rng.uniform(-s, s, (input_size, hidden_size))
        self.W_hh = rng.uniform(-s, s, (hidden_size, hidden_size))
        self.b_h = np.zeros(hidden_size)

    def step(self, x_t, h_prev):
        return np.tanh(x_t @ self.W_xh + h_prev @ self.W_hh + self.b_h)

    def run(self, xs):
        """xs: (T, input_size) -> stacked hidden states (T, hidden_size)."""
        h = np.zeros(self.b_h.shape)
        hs = []
        for x_t in xs:
            h = self.step(x_t, h)
            hs.append(h)
        return np.array(hs)


def make_transformer_block(
    d_model: int = 64, n_heads: int = 4, d_ff: int = 256, dropout: float = 0.0
):
    """A pre-norm transformer encoder block (self-attention + MLP)."""
    import torch.nn as nn

    class Block(nn.Module):
        def __init__(self):
            super().__init__()
            self.ln1 = nn.LayerNorm(d_model)
            self.attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
            self.ln2 = nn.LayerNorm(d_model)
            self.mlp = nn.Sequential(
                nn.Linear(d_model, d_ff), nn.GELU(), nn.Linear(d_ff, d_model), nn.Dropout(dropout)
            )

        def forward(self, x, attn_mask=None):
            h = self.ln1(x)
            a, attn_w = self.attn(
                h, h, h, attn_mask=attn_mask, need_weights=True, average_attn_weights=False
            )
            x = x + a
            x = x + self.mlp(self.ln2(x))
            return x, attn_w

    return Block()


def make_autoencoder(latent_dim: int = 2, input_dim: int = 784):
    """Symmetric MLP autoencoder (used on flattened 28x28 images)."""
    import torch.nn as nn

    class AE(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 32),
                nn.ReLU(),
                nn.Linear(32, latent_dim),
            )
            self.decoder = nn.Sequential(
                nn.Linear(latent_dim, 32),
                nn.ReLU(),
                nn.Linear(32, 128),
                nn.ReLU(),
                nn.Linear(128, input_dim),
                nn.Sigmoid(),
            )

        def forward(self, x):
            z = self.encoder(x)
            return self.decoder(z), z

    return AE()


def make_vae(latent_dim: int = 2, input_dim: int = 784):
    """Variational autoencoder with a diagonal-Gaussian latent."""
    import torch
    import torch.nn as nn

    class VAE(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = nn.Sequential(nn.Linear(input_dim, 128), nn.ReLU())
            self.mu = nn.Linear(128, latent_dim)
            self.logvar = nn.Linear(128, latent_dim)
            self.decoder = nn.Sequential(
                nn.Linear(latent_dim, 128),
                nn.ReLU(),
                nn.Linear(128, input_dim),
                nn.Sigmoid(),
            )

        def encode(self, x):
            h = self.enc(x)
            return self.mu(h), self.logvar(h)

        def reparameterize(self, mu, logvar):
            # z = mu + sigma * eps, with sigma = exp(0.5 * logvar)
            std = torch.exp(0.5 * logvar)
            return mu + std * torch.randn_like(std)

        def forward(self, x):
            mu, logvar = self.encode(x)
            z = self.reparameterize(mu, logvar)
            return self.decoder(z), mu, logvar

    return VAE()


def make_gan_2d(latent_dim: int = 2, hidden: int = 64):
    """Generator + discriminator for the 2-D Gaussian-mixture GAN demo."""
    import torch.nn as nn

    generator = nn.Sequential(
        nn.Linear(latent_dim, hidden),
        nn.ReLU(),
        nn.Linear(hidden, hidden),
        nn.ReLU(),
        nn.Linear(hidden, 2),
    )
    discriminator = nn.Sequential(
        nn.Linear(2, hidden),
        nn.LeakyReLU(0.2),
        nn.Linear(hidden, hidden),
        nn.LeakyReLU(0.2),
        nn.Linear(hidden, 1),  # raw logit, pair with BCEWithLogitsLoss
    )
    return generator, discriminator


def make_denoiser(input_dim: int = 784, hidden: int = 256):
    """Tiny time-conditioned denoiser for the diffusion demo.

    Input is the noisy image concatenated with the (scalar) noise level.
    """
    import torch.nn as nn

    class Denoiser(nn.Module):
        def __init__(self):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim + 1, hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden),
                nn.ReLU(),
                nn.Linear(hidden, input_dim),
            )

        def forward(self, x, t):  # x: (B, input_dim), t: (B, 1) in [0, 1]
            return self.net(torch.cat([x, t], dim=1))

    import torch

    return Denoiser()


class LoRALinear:
    """LoRA low-rank update demo (NumPy): W_eff = W0 + (alpha / r) * A @ B.

    A: (in, r), B: (r, out). Only A and B are 'trainable'; W0 is frozen. Used in
    notebook 10 to show how few parameters a low-rank adapter adds.
    """

    def __init__(self, W0, rank: int = 4, alpha: float = 8.0, seed: int = 0):
        self.W0 = np.asarray(W0, dtype=np.float64)
        n_in, n_out = self.W0.shape
        rng = np.random.default_rng(seed)
        self.A = rng.standard_normal((n_in, rank)) * 0.01
        self.B = np.zeros((rank, n_out))  # B starts at 0 so the update starts as identity
        self.scale = alpha / rank

    def effective_weight(self):
        return self.W0 + self.scale * self.A @ self.B

    def n_lora_params(self) -> int:
        return self.A.size + self.B.size

    def n_full_params(self) -> int:
        return self.W0.size
