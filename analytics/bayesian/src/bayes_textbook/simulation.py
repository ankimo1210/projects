"""Synthetic data generators and Monte Carlo helpers (seeded, no downloads)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def make_ab_test_data(
    n_a: int = 1000, n_b: int = 1000, p_a: float = 0.052, p_b: float = 0.061, seed: int = 8
) -> pd.DataFrame:
    """Per-arm conversion summary for an A/B test. True rates are hidden inputs."""
    r = np.random.default_rng(seed)
    conv_a = int(r.binomial(n_a, p_a))
    conv_b = int(r.binomial(n_b, p_b))
    return pd.DataFrame(
        {"variant": ["A", "B"], "visitors": [n_a, n_b], "conversions": [conv_a, conv_b]}
    )


def prob_a_beats_b(post_a, post_b, n: int = 100_000, seed: int = 42) -> float:
    """Monte Carlo P(theta_A > theta_B) from two posterior objects with .sample()."""
    a = post_a.sample(n, seed=seed)
    b = post_b.sample(n, seed=seed + 1)
    return float((a > b).mean())


def make_store_conversions(
    n_stores: int = 12,
    base_rate: float = 0.06,
    sd_logit: float = 0.35,
    visits_lo: int = 20,
    visits_hi: int = 3000,
    seed: int = 42,
) -> pd.DataFrame:
    """Store-level CVR data with very unequal sample sizes (for hierarchical Bayes).

    True per-store rates vary around base_rate on the logit scale; some stores
    have only a handful of visits, which is what makes pooling interesting.
    """
    r = np.random.default_rng(seed)
    logit = np.log(base_rate / (1 - base_rate)) + sd_logit * r.standard_normal(n_stores)
    true_rate = 1 / (1 + np.exp(-logit))
    # Log-uniform visit counts: a few big stores, many small ones.
    visits = np.exp(r.uniform(np.log(visits_lo), np.log(visits_hi), n_stores)).astype(int)
    conversions = r.binomial(visits, true_rate)
    return pd.DataFrame(
        {
            "store": [f"S{i:02d}" for i in range(n_stores)],
            "visits": visits,
            "conversions": conversions,
            "true_rate": true_rate,
        }
    )


def make_batting_data(
    n_players: int = 15,
    mean_avg: float = 0.265,
    sd: float = 0.02,
    ab_lo: int = 10,
    ab_hi: int = 600,
    seed: int = 7,
) -> pd.DataFrame:
    """Baseball batting data: at-bats vary wildly across players."""
    r = np.random.default_rng(seed)
    true_avg = np.clip(r.normal(mean_avg, sd, n_players), 0.15, 0.40)
    at_bats = np.exp(r.uniform(np.log(ab_lo), np.log(ab_hi), n_players)).astype(int)
    hits = r.binomial(at_bats, true_avg)
    return pd.DataFrame(
        {
            "player": [f"P{i:02d}" for i in range(n_players)],
            "at_bats": at_bats,
            "hits": hits,
            "true_avg": true_avg,
        }
    )


def make_wine_ratings(
    n_wines: int = 10,
    raters_lo: int = 3,
    raters_hi: int = 60,
    quality_sd: float = 0.8,
    rating_sd: float = 1.0,
    seed: int = 11,
) -> pd.DataFrame:
    """Long-format wine ratings: true quality + rater noise, uneven coverage."""
    r = np.random.default_rng(seed)
    quality = 6.0 + quality_sd * r.standard_normal(n_wines)
    rows = []
    for i in range(n_wines):
        n_raters = int(np.exp(r.uniform(np.log(raters_lo), np.log(raters_hi))))
        scores = np.clip(quality[i] + rating_sd * r.standard_normal(n_raters), 1, 10)
        rows += [{"wine": f"W{i:02d}", "rating": s, "true_quality": quality[i]} for s in scores]
    return pd.DataFrame(rows)


def make_returns(
    n_days: int = 250, mu_annual: float = 0.06, sigma_annual: float = 0.20, seed: int = 21
) -> np.ndarray:
    """Daily stock returns with a small positive drift buried in noise."""
    r = np.random.default_rng(seed)
    mu_d, sd_d = mu_annual / 252, sigma_annual / np.sqrt(252)
    return mu_d + sd_d * r.standard_normal(n_days)


def write_sample_csvs(data_dir: Path | None = None) -> list[Path]:
    """Write the small committed CSVs under data/ (reproducible from seeds)."""
    data_dir = Path(data_dir) if data_dir is not None else DATA_DIR
    data_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, df in [
        ("ab_test.csv", make_ab_test_data()),
        ("store_conversions.csv", make_store_conversions()),
    ]:
        p = data_dir / name
        df.to_csv(p, index=False)
        paths.append(p)
    return paths
