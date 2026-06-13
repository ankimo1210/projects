"""Datasets for the textbook.

Synthetic data is generated locally with fixed seeds. Image datasets
(MNIST / Fashion-MNIST) are downloaded once into ``_data/`` via torchvision.
Everything is designed to run on a normal laptop.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from sklearn.datasets import make_blobs as _sk_blobs
from sklearn.datasets import make_circles as _sk_circles
from sklearn.datasets import make_moons as _sk_moons

# Repo-relative cache directory for downloaded image datasets.
DATA_ROOT = Path(__file__).resolve().parents[3] / "_data"


# ---------------------------------------------------------------------------
# 2-D synthetic classification datasets
# ---------------------------------------------------------------------------


def make_moons_dataset(n: int = 400, noise: float = 0.2, seed: int = 0):
    """Two interleaving half-moons. Returns (X[n, 2] float32, y[n] int64)."""
    X, y = _sk_moons(n_samples=n, noise=noise, random_state=seed)
    return X.astype(np.float32), y.astype(np.int64)


def make_circles_dataset(n: int = 400, noise: float = 0.1, factor: float = 0.5, seed: int = 0):
    """Concentric circles (inner vs outer). Returns (X[n, 2], y[n])."""
    X, y = _sk_circles(n_samples=n, noise=noise, factor=factor, random_state=seed)
    return X.astype(np.float32), y.astype(np.int64)


def make_blobs_dataset(n: int = 400, centers: int = 3, cluster_std: float = 1.0, seed: int = 0):
    """Isotropic Gaussian blobs. Returns (X[n, 2], y[n])."""
    X, y = _sk_blobs(n_samples=n, centers=centers, cluster_std=cluster_std, random_state=seed)
    return X.astype(np.float32), y.astype(np.int64)


def make_spiral_dataset(
    n_per_class: int = 200, n_classes: int = 3, noise: float = 0.2, seed: int = 0
):
    """Multi-arm spiral (the classic CS231n benchmark).

    Returns (X[n_per_class * n_classes, 2], y) where each class is one spiral arm.
    """
    rng = np.random.default_rng(seed)
    X = np.zeros((n_per_class * n_classes, 2), dtype=np.float32)
    y = np.zeros(n_per_class * n_classes, dtype=np.int64)
    for c in range(n_classes):
        idx = range(n_per_class * c, n_per_class * (c + 1))
        r = np.linspace(0.0, 1.0, n_per_class)
        # Each arm spans 4 radians and is rotated by 2*pi/n_classes per class.
        t = np.linspace(c * 4, (c + 1) * 4, n_per_class) + rng.standard_normal(n_per_class) * noise
        X[idx] = np.c_[r * np.sin(t), r * np.cos(t)].astype(np.float32)
        y[idx] = c
    return X, y


def make_regression_1d(n: int = 100, noise: float = 0.15, seed: int = 0):
    """1-D regression target y = sin(2 pi x) + small noise on x in [0, 1].

    Returns (x[n, 1], y[n, 1]) as float32.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(0.0, 1.0, n)).astype(np.float32)
    y = np.sin(2 * np.pi * x) + noise * rng.standard_normal(n).astype(np.float32)
    return x[:, None], y[:, None].astype(np.float32)


# ---------------------------------------------------------------------------
# 1-D sequence datasets
# ---------------------------------------------------------------------------


def make_sine_wave_dataset(n_steps: int = 400, periods: float = 6.0):
    """Clean sine wave sampled at n_steps points. Returns (t, y) float32."""
    t = np.linspace(0.0, periods * 2 * np.pi, n_steps).astype(np.float32)
    return t, np.sin(t).astype(np.float32)


def make_noisy_sine_wave_dataset(
    n_steps: int = 400, periods: float = 6.0, noise: float = 0.1, seed: int = 0
):
    """Sine wave plus observation noise. Returns (t, y) float32."""
    rng = np.random.default_rng(seed)
    t, y = make_sine_wave_dataset(n_steps, periods)
    return t, (y + noise * rng.standard_normal(n_steps)).astype(np.float32)


def make_ar_process_dataset(
    n_steps: int = 400, coeffs=(0.6, -0.3), noise: float = 0.2, seed: int = 0
):
    """Autoregressive AR(p) process y_t = sum_i coeffs[i] * y_{t-1-i} + eps.

    Returns y[n_steps] float32.
    """
    rng = np.random.default_rng(seed)
    coeffs = np.asarray(coeffs, dtype=np.float32)
    p = len(coeffs)
    y = np.zeros(n_steps, dtype=np.float32)
    y[:p] = rng.standard_normal(p)
    for t in range(p, n_steps):
        y[t] = coeffs @ y[t - p : t][::-1] + noise * rng.standard_normal()
    return y


def make_sequence_windows(series, window: int, horizon: int = 1):
    """Slice a 1-D series into supervised (input window -> next value) pairs.

    Returns (X[n, window, 1], Y[n, horizon]) float32. Shapes are stated so the
    notebooks can wire them straight into an RNN of batch_first layout.
    """
    series = np.asarray(series, dtype=np.float32)
    xs, ys = [], []
    for i in range(len(series) - window - horizon + 1):
        xs.append(series[i : i + window])
        ys.append(series[i + window : i + window + horizon])
    X = np.array(xs, dtype=np.float32)[:, :, None]
    Y = np.array(ys, dtype=np.float32)
    return X, Y


# ---------------------------------------------------------------------------
# Generative-model datasets
# ---------------------------------------------------------------------------


def make_gaussian_mixture_dataset(
    n: int = 800, n_components: int = 8, radius: float = 2.0, std: float = 0.15, seed: int = 0
):
    """2-D Gaussian mixture with components on a ring. Returns (X[n, 2], comp[n]).

    A ring layout makes GAN mode collapse easy to see (the generator covering
    only a few of the modes).
    """
    rng = np.random.default_rng(seed)
    angles = np.linspace(0, 2 * np.pi, n_components, endpoint=False)
    centers = radius * np.c_[np.cos(angles), np.sin(angles)]
    comp = rng.integers(0, n_components, size=n)
    X = (centers[comp] + std * rng.standard_normal((n, 2))).astype(np.float32)
    return X, comp.astype(np.int64)


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

TINY_CORPUS = (
    "neural networks learn representations from data. "
    "a network is a composition of linear and nonlinear transformations. "
    "gradients flow backward through the computation graph. "
    "attention lets a token look at every other token. "
    "deep models learn features layer by layer. "
    "the model predicts the next token from the previous tokens. "
)


def make_tiny_text_corpus(repeat: int = 1) -> str:
    """Return a tiny, fully built-in text corpus (no downloads)."""
    return (TINY_CORPUS * repeat).strip()


class CharTokenizer:
    """Minimal character-level tokenizer for the text / LLM notebooks."""

    def __init__(self, text: str):
        self.chars = sorted(set(text))
        self.stoi = {c: i for i, c in enumerate(self.chars)}
        self.itos = {i: c for i, c in enumerate(self.chars)}

    @property
    def vocab_size(self) -> int:
        return len(self.chars)

    def encode(self, s: str):
        return np.array([self.stoi[c] for c in s], dtype=np.int64)

    def decode(self, ids) -> str:
        return "".join(self.itos[int(i)] for i in ids)


# ---------------------------------------------------------------------------
# Image datasets (downloaded once, cached under _data/)
# ---------------------------------------------------------------------------


def _load_torchvision(name: str, train: bool, n: int | None, seed: int):
    import torch
    from torchvision import datasets as tvd
    from torchvision import transforms

    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    tfm = transforms.ToTensor()  # -> float tensor in [0, 1], shape (1, 28, 28)
    cls = {"mnist": tvd.MNIST, "fashion": tvd.FashionMNIST}[name]
    ds = cls(root=str(DATA_ROOT), train=train, download=True, transform=tfm)
    if n is not None and n < len(ds):
        g = torch.Generator().manual_seed(seed)
        idx = torch.randperm(len(ds), generator=g)[:n]
        ds = torch.utils.data.Subset(ds, idx.tolist())
    return ds


def load_mnist(train: bool = True, n: int | None = None, seed: int = 0):
    """MNIST as a torchvision dataset (optionally a random subset of size n)."""
    return _load_torchvision("mnist", train, n, seed)


def load_fashion_mnist(train: bool = True, n: int | None = None, seed: int = 0):
    """Fashion-MNIST as a torchvision dataset (optionally a random subset)."""
    return _load_torchvision("fashion", train, n, seed)


FASHION_CLASSES = [
    "T-shirt",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle boot",
]


# ---------------------------------------------------------------------------
# Splitting helpers
# ---------------------------------------------------------------------------


def train_val_split(X, y, val_frac: float = 0.2, seed: int = 0):
    """Shuffle and split arrays into train / validation. Returns 4 arrays."""
    X = np.asarray(X)
    y = np.asarray(y)
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(X))
    n_val = int(len(X) * val_frac)
    val, tr = perm[:n_val], perm[n_val:]
    return X[tr], y[tr], X[val], y[val]


def load_text_corpus(path=None, repeat: int = 1) -> str:
    """Text for the language-model notebooks (07 / 10).

    Bring-your-own-data hook: with a file ``path`` it returns that file's text
    (swap in Tiny Shakespeare, your own corpus, etc.); with ``path=None`` it
    returns the built-in tiny corpus, keeping the textbook download-free.
    """
    if path is None:
        return make_tiny_text_corpus(repeat=repeat)
    from pathlib import Path

    return Path(path).read_text(encoding="utf-8")


def make_capstone_dataset(n: int = 40, x_range=(-3.0, 3.0), noise: float = 0.35, seed: int = 0):
    """Shared 1-D regression data for the cross-book capstone (three lenses).

    The SAME generator is defined identically in all three analytics books so
    each can solve the same problem from its own lens without importing the
    others. True curve f(x) = sin(1.5 x) + 0.3 x, with Gaussian noise. Returns
    (x, y) as float64 arrays sorted by x.
    """
    rng = np.random.default_rng(seed)
    x = np.sort(rng.uniform(x_range[0], x_range[1], n))
    f = np.sin(1.5 * x) + 0.3 * x
    y = f + noise * rng.standard_normal(n)
    return x, y
