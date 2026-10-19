import numpy as np
import pandas as pd
from sector_leadlag.signal import (
    Spec,
    correlation,
    cross_standardize,
    full_correlation,
    lead_lag_signal,
    long_short,
    prior_subspace,
    propagate,
    standardize,
    target,
    top_sectors,
)
from sector_leadlag.timing import last_us_before, pair_rows

US = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
JP = tuple(range(1, 18))


def test_prior_subspace_is_orthonormal_and_points_where_the_paper_says():
    v0 = prior_subspace(US, JP)
    assert v0.shape == (28, 3)
    assert np.allclose(v0.T @ v0, np.eye(3))
    assert np.allclose(v0[:, 0], 1 / np.sqrt(28))
    assert (v0[:11, 1] > 0).all() and (v0[11:, 1] < 0).all()
    # cyclical XLE (US) and banks (sector 15) load above defensive XLU and retail (sector 14)
    assert v0[US.index("XLE"), 2] > v0[US.index("XLU"), 2]
    assert v0[11 + 14, 2] > v0[11 + 13, 2]


def test_target_is_a_correlation_matrix():
    rng = np.random.default_rng(1)
    _, _, usable, z = standardize(rng.normal(size=(400, 28)))
    c0 = target(correlation(z, usable), prior_subspace(US, JP))
    assert np.allclose(c0, c0.T) and np.allclose(np.diag(c0), 1.0)
    assert np.all(np.linalg.eigvalsh(c0) > -1e-12)


def test_an_unlaunched_column_gets_no_correlation_and_a_zero_score():
    rng = np.random.default_rng(2)
    block = rng.normal(size=(60, 4))
    block[:30, 2] = np.nan  # launched halfway through the window
    _, _, usable, z = standardize(block)
    assert usable.tolist() == [True, True, False, True]
    assert (z[:, 2] == 0).all()
    c = correlation(z, usable)
    assert c[2, 2] == 1.0 and (np.delete(c[2], 2) == 0).all()


def test_flipping_eigenvector_signs_leaves_the_signal_unchanged():
    rng = np.random.default_rng(3)
    vectors = np.linalg.qr(rng.normal(size=(28, 3)))[0]
    z_us = rng.normal(size=11)
    flipped = vectors * np.array([-1.0, 1.0, -1.0])
    assert np.allclose(propagate(vectors, 11, z_us), propagate(flipped, 11, z_us))


def _factor_world(n: int, seed: int):
    """US shocks g_t at t, the same g_t in Japan on the next day (strategy paper, eq. 23-24)."""
    rng = np.random.default_rng(seed)
    v_us = np.linalg.qr(rng.normal(size=(11, 3)))[0]
    v_jp = np.linalg.qr(rng.normal(size=(17, 3)))[0]
    g = rng.normal(size=(n, 3)) * np.array([3.0, 2.5, 2.0])
    us = g @ v_us.T + 0.3 * rng.normal(size=(n, 11))
    jp = np.vstack([np.zeros((1, 17)), g[:-1] @ v_jp.T]) + 0.3 * rng.normal(size=(n, 17))
    dates = pd.bdate_range("2020-01-01", periods=n)
    us_ret = pd.DataFrame(us, index=dates, columns=list(US))
    jp_ret = pd.DataFrame(jp, index=dates, columns=list(JP))  # row t answers US t-1
    return us_ret, jp_ret, v_us, v_jp


def test_plain_pca_recovers_the_best_linear_predictor():
    us_ret, jp_ret, v_us, v_jp = _factor_world(1600, 4)
    s_map = last_us_before(jp_ret.index, us_ret.index)
    rows = pair_rows("lagged", us_ret, jp_ret, s_map)
    c0 = np.eye(28)
    days = jp_ret.index[-300:]
    signal = lead_lag_signal(rows, us_ret, s_map, c0, days, Spec(lam=0.0, window=1200))
    mu = us_ret.iloc[-1500:].mean()
    sd = us_ret.iloc[-1500:].std(ddof=0)
    us_days = pd.DatetimeIndex(s_map.reindex(signal.index).to_numpy())
    z_us = ((us_ret.reindex(us_days) - mu) / sd).to_numpy()
    best = z_us @ v_us @ v_jp.T
    assert np.corrcoef(signal.to_numpy().ravel(), best.ravel())[0, 1] > 0.9


def test_lambda_zero_is_plain_pca_and_lambda_one_is_the_target():
    rng = np.random.default_rng(5)
    dates = pd.bdate_range("2024-01-01", periods=80)
    us_ret = pd.DataFrame(rng.normal(size=(80, 11)), index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(80, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    c0 = target(full_correlation(rows, (dates[0], dates[-1]))[0], prior_subspace(US, JP))
    day = dates[-1:]
    plain = lead_lag_signal(rows, us_ret, s_map, c0, day, Spec(lam=0.0))
    mu, sd, usable, z = standardize(np.hstack([rows.us, rows.jp])[-61:-1])
    values, vectors = np.linalg.eigh(correlation(z, usable))
    top = vectors[:, np.argsort(values)[::-1][:3]]
    z_us = (us_ret.loc[s_map.iloc[-1]].to_numpy() - mu[:11]) / sd[:11]
    assert np.allclose(plain.to_numpy()[0], propagate(top, 11, z_us))
    pure = lead_lag_signal(rows, us_ret, s_map, c0, day, Spec(lam=1.0))
    values, vectors = np.linalg.eigh(c0)
    top = vectors[:, np.argsort(values)[::-1][:3]]
    assert np.allclose(pure.to_numpy()[0], propagate(top, 11, z_us))


def test_a_column_before_launch_does_not_move_the_signal():
    rng = np.random.default_rng(6)
    dates = pd.bdate_range("2024-01-01", periods=80)
    us = rng.normal(size=(80, 11))
    us[:, US.index("XLC")] = np.nan
    us_ret = pd.DataFrame(us, index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(80, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    c_full, unusable = full_correlation(rows, (dates[0], dates[-1]))
    assert unusable == ["XLC"]
    c0 = target(c_full, prior_subspace(US, JP))
    base = lead_lag_signal(rows, us_ret, s_map, c0, dates[-5:])
    bumped = us_ret.copy()
    bumped.loc[dates[-6] :, "XLC"] = 0.5  # values that are not part of a full window
    moved = lead_lag_signal(rows, bumped, s_map, c0, dates[-5:])
    pd.testing.assert_frame_equal(base, moved)


def test_momentum_is_the_window_mean_of_japan():
    dates = pd.bdate_range("2024-01-01", periods=70)
    rng = np.random.default_rng(7)
    us_ret = pd.DataFrame(rng.normal(size=(70, 11)), index=dates, columns=list(US))
    jp_ret = pd.DataFrame(rng.normal(size=(70, 17)), index=dates, columns=list(JP))
    s_map = last_us_before(dates, dates)
    rows = pair_rows("same_date", us_ret, jp_ret, s_map)
    signal = lead_lag_signal(rows, us_ret, s_map, np.eye(28), dates[-1:], Spec(kind="momentum"))
    assert np.allclose(signal.to_numpy()[0], jp_ret.iloc[-61:-1].mean().to_numpy())


def test_long_short_weights_and_the_top_sectors():
    signal = pd.DataFrame([np.arange(17.0), np.arange(17.0)[::-1]], columns=list(JP))
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    available.iloc[1, :7] = False  # 10 sectors traded: n = 3
    w = long_short(signal, available)
    assert np.allclose(w.sum(axis=1), 0) and np.allclose(w.abs().sum(axis=1), 2)
    assert w.iloc[0][w.iloc[0] > 0].index.tolist() == [13, 14, 15, 16, 17]
    assert w.iloc[1][w.iloc[1] > 0].index.tolist() == [8, 9, 10]
    assert w.iloc[1][w.iloc[1] < 0].index.tolist() == [15, 16, 17]
    top = top_sectors(signal, 5)
    assert top.iloc[0][top.iloc[0]].index.tolist() == [13, 14, 15, 16, 17]
    sz = cross_standardize(signal)
    assert np.allclose(sz.mean(axis=1), 0) and np.allclose(sz.std(axis=1, ddof=0), 1)


def test_a_flat_signal_takes_no_position():
    signal = pd.DataFrame([np.zeros(17)], columns=list(JP))
    available = pd.DataFrame(True, index=signal.index, columns=signal.columns)
    assert (long_short(signal, available) == 0).all().all()
    assert not top_sectors(signal, 5).any().any()
    assert cross_standardize(signal).isna().all().all()
