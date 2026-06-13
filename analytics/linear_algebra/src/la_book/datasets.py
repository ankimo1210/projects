"""Synthetic datasets for the notebooks — fully reproducible, no downloads."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_correlated_cloud(
    n: int = 300, mean=(0.0, 0.0), cov=((3.0, 1.4), (1.4, 1.0)), seed: int = 0
):
    """2-D Gaussian point cloud with the given covariance. Returns X of shape (n, 2)."""
    rng = np.random.default_rng(seed)
    return rng.multivariate_normal(np.asarray(mean, float), np.asarray(cov, float), size=n)


def make_noisy_line(
    n: int = 40,
    slope: float = 1.8,
    intercept: float = 0.5,
    noise: float = 0.6,
    x_range=(0.0, 5.0),
    seed: int = 1,
):
    """Noisy samples of y = slope * x + intercept. Returns (x, y)."""
    rng = np.random.default_rng(seed)
    x = np.linspace(*x_range, n)
    y = slope * x + intercept + noise * rng.standard_normal(n)
    return x, y


def make_test_image(size: int = 128):
    """Synthetic grayscale image (gradient + circle + block + stripes).

    Built to have clear low-rank structure plus fine detail, so SVD
    compression is visually instructive. Values in [0, 1].
    """
    yy, xx = np.mgrid[0:size, 0:size] / (size - 1)
    img = 0.55 * xx + 0.30 * yy
    img[(xx - 0.35) ** 2 + (yy - 0.38) ** 2 < 0.045] = 1.0
    img[int(0.62 * size) : int(0.85 * size), int(0.55 * size) : int(0.92 * size)] = 0.08
    img += 0.12 * np.sin(18 * np.pi * (xx + 0.5 * yy))
    return np.clip(img, 0.0, 1.0)


def make_yield_curves(
    n_days: int = 500,
    maturities=(0.25, 0.5, 1, 2, 3, 5, 7, 10, 20, 30),
    seed: int = 42,
):
    """Synthetic government yield-curve panel driven by 3 latent factors.

    Level / slope / curvature factors follow AR(1) dynamics and load onto
    maturities via Nelson-Siegel-style loadings, plus small observation noise.
    Returns (maturities, DataFrame of shape (n_days, n_maturities), in %).
    """
    rng = np.random.default_rng(seed)
    mats = np.asarray(maturities, dtype=float)
    x = mats / 2.0
    load_level = np.ones_like(mats)
    load_slope = (1 - np.exp(-x)) / x
    load_curv = load_slope - np.exp(-x)

    # Innovation sizes chosen so PCA on daily changes recovers the familiar
    # level (~90%) / slope / curvature ordering of real curve data.
    f_mean = np.array([1.6, -0.9, 0.5])
    phi = np.array([0.999, 0.995, 0.99])
    sig = np.array([0.04, 0.02, 0.02])
    f = np.zeros((n_days, 3))
    f_prev = f_mean.copy()
    for t in range(n_days):
        f_prev = f_mean + phi * (f_prev - f_mean) + sig * rng.standard_normal(3)
        f[t] = f_prev

    curves = (
        f[:, [0]] * load_level + f[:, [1]] * load_slope + f[:, [2]] * load_curv
    ) + 0.003 * rng.standard_normal((n_days, len(mats)))
    cols = [f"{m:g}Y" for m in mats]
    return mats, pd.DataFrame(curves, columns=cols)


def make_asset_returns(n_days: int = 750, seed: int = 7):
    """Daily returns for 6 assets from a market + 2 sector factor model.

    Returns a DataFrame; correlations are strong within sectors, so the
    covariance eigenstructure is interpretable.
    """
    rng = np.random.default_rng(seed)
    names = ["TECH1", "TECH2", "BANK1", "BANK2", "UTIL1", "BOND1"]
    market = 0.0003 + 0.010 * rng.standard_normal(n_days)
    tech = 0.012 * rng.standard_normal(n_days)
    fin = 0.008 * rng.standard_normal(n_days)
    beta_m = np.array([1.3, 1.2, 1.0, 0.9, 0.6, -0.1])
    beta_t = np.array([1.0, 0.9, 0.0, 0.0, 0.0, 0.0])
    beta_f = np.array([0.0, 0.0, 1.0, 0.8, 0.2, 0.0])
    R = (
        market[:, None] * beta_m
        + tech[:, None] * beta_t
        + fin[:, None] * beta_f
        + 0.006 * rng.standard_normal((n_days, 6))
    )
    return pd.DataFrame(R, columns=names)


def make_web_graph():
    """Small directed web graph for PageRank: adj[i, j] = 1 if page i links to j.

    Page A is the hub; page G is dangling (no outlinks). Returns (names, adj).
    """
    names = ["A", "B", "C", "D", "E", "F", "G"]
    idx = {n: i for i, n in enumerate(names)}
    edges = [
        ("B", "A"),
        ("C", "A"),
        ("D", "A"),
        ("E", "A"),
        ("A", "B"),
        ("A", "C"),
        ("B", "C"),
        ("C", "D"),
        ("D", "E"),
        ("E", "F"),
        ("F", "A"),
        ("F", "G"),
    ]
    adj = np.zeros((7, 7))
    for src, dst in edges:
        adj[idx[src], idx[dst]] = 1.0
    return names, adj


def make_two_cluster_graph(n_per: int = 12, p_in: float = 0.8, p_out: float = 0.05, seed: int = 3):
    """Random undirected graph with two communities (planted partition).

    Returns (adj, labels): adjacency matrix and true community labels.
    """
    rng = np.random.default_rng(seed)
    n = 2 * n_per
    labels = np.array([0] * n_per + [1] * n_per)
    adj = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            p = p_in if labels[i] == labels[j] else p_out
            if rng.random() < p:
                adj[i, j] = adj[j, i] = 1.0
    return adj, labels
