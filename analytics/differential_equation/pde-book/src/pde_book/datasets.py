"""Initial / boundary conditions and small sample fields — no downloads.

All shapes are sampled directly from formulas on a grid, so every notebook runs
offline and reproducibly.
"""

from __future__ import annotations

import numpy as np


def bump(x, center=0.5, width=0.15, height=1.0):
    """A flat-topped bump (indicator of |x-center| < width). Discontinuous edges."""
    x = np.asarray(x, dtype=float)
    return np.where(np.abs(x - center) < width, height, 0.0)


def gaussian(x, center=0.5, sigma=0.08, height=1.0):
    """A smooth Gaussian profile."""
    x = np.asarray(x, dtype=float)
    return height * np.exp(-((x - center) ** 2) / (2 * sigma**2))


def step(x, x0=0.5, left=1.0, right=0.0):
    """A single jump (Riemann-problem style) at x0."""
    x = np.asarray(x, dtype=float)
    return np.where(x < x0, left, right)


def sine_mode(x, mode=1, L=1.0, amp=1.0):
    """A single Dirichlet eigenfunction sin(mode pi x / L)."""
    x = np.asarray(x, dtype=float)
    return amp * np.sin(mode * np.pi * x / L)


def sine_combo(x, modes=(1, 3, 5), amps=(1.0, 0.4, 0.2), L=1.0):
    """A superposition of sine modes (to show mode-wise decay in the heat eqn)."""
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    for m, a in zip(modes, amps, strict=False):
        out += a * np.sin(m * np.pi * x / L)
    return out


def hot_edge_boundary(grid, value=1.0):
    """Dirichlet boundary array (ny, nx): one hot edge (top), the rest zero.

    Useful for a Laplace/steady-heat demo on a plate.
    """
    b = np.zeros((grid.ny, grid.nx))
    b[-1, :] = value  # top edge (largest y) held hot
    return b


def make_test_image(size=96, seed=0):
    """Synthetic grayscale image with sharp edges + noise (for diffusion smoothing).

    Values in [0, 1]. Diffusion (the heat equation) blurs the noise and edges.
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size] / (size - 1)
    img = 0.2 + 0.0 * xx
    img[(xx - 0.35) ** 2 + (yy - 0.4) ** 2 < 0.03] = 0.9  # disk
    img[int(0.6 * size) : int(0.85 * size), int(0.55 * size) : int(0.9 * size)] = 0.75  # block
    img += 0.12 * rng.standard_normal((size, size))  # salt-ish noise
    return np.clip(img, 0.0, 1.0)
