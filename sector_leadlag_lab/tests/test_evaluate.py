import numpy as np
import pandas as pd
import pytest
from sector_leadlag.evaluate import (
    Evidence,
    describe,
    h3_label,
    mean_test,
    monthly_metrics,
    panel_fit,
    ratio_interval,
    two_way_demean,
    verdict,
)


def _panel(seed: int, days: int = 60, sectors: int = 5, beta: float = 0.5, holes: float = 0.2):
    rng = np.random.default_rng(seed)
    index = pd.bdate_range("2026-01-05", periods=days)
    x = pd.DataFrame(rng.normal(size=(days, sectors)), index=index, columns=range(1, sectors + 1))
    day_effect = rng.normal(size=(days, 1))
    sector_effect = rng.normal(size=(1, sectors))
    y = beta * x + day_effect + sector_effect + rng.normal(size=(days, sectors))
    y = y.mask(rng.random((days, sectors)) < holes)
    return y, x


def _dummy_ols(y: pd.DataFrame, x: pd.DataFrame):
    """The same regression with explicit dummies, and its day-clustered standard error."""
    stack = pd.DataFrame({"y": y.stack(), "x": x.stack()}).dropna()
    day = stack.index.get_level_values(0)
    sector = stack.index.get_level_values(1)
    dummies = pd.get_dummies(pd.Series(day), drop_first=False).to_numpy(float)
    sector_dummies = pd.get_dummies(pd.Series(sector), drop_first=True).to_numpy(float)
    design = np.column_stack([stack["x"].to_numpy(), dummies, sector_dummies])
    coef, *_ = np.linalg.lstsq(design, stack["y"].to_numpy(), rcond=None)
    resid = stack["y"].to_numpy() - design @ coef
    bread = np.linalg.pinv(design.T @ design)
    codes = pd.factorize(day)[0]
    scores = np.zeros((codes.max() + 1, design.shape[1]))
    np.add.at(scores, codes, design * resid[:, None])
    g, n = codes.max() + 1, len(resid)
    k = 1 + len(np.unique(sector)) - 1
    cov = g / (g - 1) * (n - 1) / (n - k) * bread @ scores.T @ scores @ bread
    return coef[0], np.sqrt(cov[0, 0])


def test_the_within_estimator_matches_ols_with_dummies():
    y, x = _panel(1)
    fit = panel_fit(y, x)
    beta, se = _dummy_ols(y, x)
    assert fit.beta[0] == pytest.approx(beta, rel=1e-9)
    assert fit.se[0] == pytest.approx(se, rel=1e-6)
    assert fit.days.equals(y.index[y.notna().any(axis=1)])
    assert fit.score.sum() / fit.weight.sum() == pytest.approx(fit.beta[0], rel=1e-9)


def test_a_true_effect_is_found_and_a_null_one_is_not():
    y, x = _panel(2, days=400, beta=0.3)
    assert panel_fit(y, x).p < 0.01
    y, x = _panel(3, days=400, beta=0.0)
    assert panel_fit(y, x).p > 0.01


def test_a_control_enters_the_same_regression():
    y, x = _panel(4, days=200)
    control = x * 0.0 + np.random.default_rng(5).normal(size=x.shape)
    fit = panel_fit(y + 2.0 * control, x, [control])
    assert fit.beta[1] == pytest.approx(2.0, abs=0.2)


def test_demeaning_a_balanced_panel_takes_both_means_out():
    rng = np.random.default_rng(6)
    values = rng.normal(size=(12, 3))
    stacked = values.ravel()
    day = np.repeat(np.arange(12), 3)
    sector = np.tile(np.arange(3), 12)
    out = two_way_demean(stacked, day, sector)[:, 0].reshape(12, 3)
    expected = values - values.mean(axis=1, keepdims=True) - values.mean(axis=0) + values.mean()
    assert np.allclose(out, expected)


def test_ratio_interval_is_reproducible_and_holds_the_estimate():
    y, x = _panel(7, days=300, beta=0.4)
    y2, _ = _panel(8, days=300, beta=0.8)
    numerator, denominator = panel_fit(y, x), panel_fit(y2, x)
    first = ratio_interval(numerator, denominator, n_boot=400)
    assert first == ratio_interval(numerator, denominator, n_boot=400)
    assert first[0] < numerator.beta[0] / denominator.beta[0] < first[1]


def test_mean_test():
    rng = np.random.default_rng(9)
    days = pd.bdate_range("2020-01-01", periods=1500)
    assert (
        mean_test(pd.Series(0.002 + 0.01 * rng.normal(size=1500), index=days), n_boot=500).p < 0.01
    )
    flat = mean_test(pd.Series(0.0, index=days), n_boot=200)
    assert flat.p == 1.0 and flat.days == 1500


def test_describe_and_the_papers_monthly_metrics():
    days = pd.bdate_range("2026-01-01", "2026-03-31")
    r = pd.Series(0.001, index=days)
    stats = describe(r)
    assert stats["mean_ann"] == pytest.approx(0.252) and stats["sharpe"] == 0.0
    assert stats["cumulative"] == pytest.approx(1.001 ** len(days) - 1)
    r.loc["2026-02"] = -0.002
    m = monthly_metrics(r)
    assert m["months"] == 3 and m["mdd"] == pytest.approx(1 - 0.998 ** len(r.loc["2026-02"]))


def test_h3_labels():
    a = pd.Series(np.tile([0.006, -0.004], 1000))  # mean 0.001
    falling = pd.Series(np.tile([-0.001, -0.007], 24))  # mean -0.004, clearly below 0
    assert h3_label(falling, a)["label"] == "decay_continued"
    recovered = pd.Series(np.tile([0.007, -0.003], 24))  # mean 0.002, not below A
    assert h3_label(recovered, a)["label"] == "decay_faded"
    noisy = pd.Series(np.tile([0.019, -0.021], 24))  # mean -0.001, not significant
    assert h3_label(noisy, a)["label"] == "unclear"
    high_a = pd.Series(np.tile([0.011, 0.009], 1000))  # mean 0.01
    flat = pd.Series(np.tile([0.0011, -0.0009], 24))  # mean 0.0001: >= 0 but far below A
    out = h3_label(flat, high_a)
    assert out["label"] == "unclear" and out["days_b2"] == 48


def test_verdict_branches():
    good = Evidence(True, 0.001, 1e-4, 0.01, 0.01, True, 1e-4, 1e-4)
    assert verdict(good) == "usable"
    assert verdict(Evidence(False, *[0.0] * 7)) == "replication_failed"
    assert verdict(Evidence(True, 0.2, 1e-4, 0.01, 0.01, True, 1e-4, 1e-4)) == "etf_only"
    assert (
        verdict(Evidence(True, 0.001, -1e-4, 0.01, 0.01, True, 1e-4, 1e-4)) == "real_then_decayed"
    )
    assert verdict(Evidence(True, 0.001, 1e-4, 0.2, 0.01, True, 1e-4, 1e-4)) == "real_not_usable"
    assert verdict(Evidence(True, 0.001, 1e-4, 0.01, 0.01, False, 1e-4, 1e-4)) == "real_not_usable"
    assert verdict(Evidence(True, 0.001, 1e-4, 0.01, 0.01, True, -1e-4, 1e-4)) == "real_not_usable"
