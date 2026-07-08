"""GBM Monte Carlo simulation (Hull 11e, Ch.14)."""

import numpy as np


def simulate_gbm_paths(S0, mu, sigma, T, n_steps, n_paths, rng=None):
    """Simulate GBM paths with the exact log-Euler scheme.

    ln S_t = ln S0 + (mu - sigma^2/2) t + sigma W_t  (Hull eq. 14.17),
    so the terminal distribution is exact for any step size — unlike the
    naive Euler scheme dS = mu S dt + sigma S dz.

    Returns an array of shape (n_paths, n_steps + 1); column 0 equals S0.
    """
    if rng is None:
        rng = np.random.default_rng(42)
    dt = T / n_steps
    z = rng.standard_normal((n_paths, n_steps))
    log_returns = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * z
    log_paths = np.log(S0) + np.cumsum(log_returns, axis=1)
    return np.column_stack([np.full(n_paths, S0), np.exp(log_paths)])


def gbm_theory(S0, mu, sigma, T):
    """Theoretical E[S_T] and Var[S_T] under GBM (Hull §14.7)."""
    e_st = S0 * np.exp(mu * T)
    var_st = S0**2 * np.exp(2.0 * mu * T) * (np.exp(sigma**2 * T) - 1.0)
    return float(e_st), float(var_st)


def price_european_mc(
    S0, K, r, sigma, T, q=0.0, kind="call", n_paths=100_000, antithetic=False, rng=None
):
    """Risk-neutral terminal-sampling MC price of a European option.

    Returns (price, standard_error) — Hull eq. (21.16) and §21.6/§21.7.
    Antithetic variates pair epsilon with -epsilon and average per pair
    before computing the standard error.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    if antithetic and (n_paths % 2 != 0 or n_paths < 4):
        raise ValueError("antithetic requires an even n_paths >= 4")
    if rng is None:
        rng = np.random.default_rng(42)
    drift = (r - q - 0.5 * sigma**2) * T
    vol = sigma * np.sqrt(T)
    if antithetic:
        z_half = rng.standard_normal(n_paths // 2)
        z = np.concatenate([z_half, -z_half])
    else:
        z = rng.standard_normal(n_paths)
    s_t = S0 * np.exp(drift + vol * z)
    payoff = np.maximum(s_t - K, 0.0) if kind == "call" else np.maximum(K - s_t, 0.0)
    disc = np.exp(-r * T) * payoff
    if antithetic:
        half = len(disc) // 2
        pair = 0.5 * (disc[:half] + disc[half:])
        return float(pair.mean()), float(pair.std(ddof=1) / np.sqrt(half))
    return float(disc.mean()), float(disc.std(ddof=1) / np.sqrt(n_paths))


def _lsm_backward(paths, K, r, T, kind):
    """Backward LSM sweep shared by the pricer and the boundary estimator.

    Returns (cf, records): cf is each path's cashflow discounted to step 1,
    records is a list of (step_index, extreme exercised spot) — max exercised
    S for a put, min for a call — for every step where exercise occurred.
    """
    n_steps = paths.shape[1] - 1

    def intrinsic(s):
        return np.maximum(s - K, 0.0) if kind == "call" else np.maximum(K - s, 0.0)

    dt = T / n_steps
    disc = np.exp(-r * dt)
    cf = intrinsic(paths[:, -1])
    records = []
    for i in range(n_steps - 1, 0, -1):
        cf = cf * disc
        s_i = paths[:, i]
        ex = intrinsic(s_i)
        itm = ex > 0.0
        if itm.sum() >= 3:
            x_itm = s_i[itm]
            basis = np.column_stack([np.ones_like(x_itm), x_itm, x_itm**2])
            coef, *_ = np.linalg.lstsq(basis, cf[itm], rcond=None)
            cont = basis @ coef
            exercise = ex[itm] > cont
            if exercise.any():
                s_ex = x_itm[exercise]
                records.append((i, float(s_ex.max() if kind == "put" else s_ex.min())))
            idx = np.nonzero(itm)[0][exercise]
            cf[idx] = ex[itm][exercise]
    return cf, records


def price_american_lsm(
    S0, K, r, sigma, T, q=0.0, kind="put", n_steps=50, n_paths=100_000, rng=None
):
    """American option via Longstaff-Schwartz least-squares MC (Hull Ch.27).

    Quadratic polynomial basis regressed on in-the-money paths; GBM paths
    with risk-neutral drift r - q from simulate_gbm_paths.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    paths = simulate_gbm_paths(S0, r - q, sigma, T, n_steps, n_paths, rng=rng)
    cf, _ = _lsm_backward(paths, K, r, T, kind)
    disc = np.exp(-r * T / n_steps)

    def intrinsic(s):
        return np.maximum(s - K, 0.0) if kind == "call" else np.maximum(K - s, 0.0)

    return float(max(intrinsic(S0), np.mean(cf * disc)))


def lsm_exercise_boundary(
    S0, K, r, sigma, T, q=0.0, kind="put", n_steps=50, n_paths=20_000, rng=None
):
    """Early-exercise boundary implied by the LSM rule (Hull Ch.27).

    At each step where the regression says exercise, record the extreme
    exercised spot (max S for a put, min for a call). Returns (taus, boundary)
    with tau = time to expiry, sorted by increasing tau — directly comparable
    to the finite-difference boundary from :func:`hullkit.fd.fd_vanilla`.
    """
    if kind not in ("call", "put"):
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    paths = simulate_gbm_paths(S0, r - q, sigma, T, n_steps, n_paths, rng=rng)
    _, records = _lsm_backward(paths, K, r, T, kind)
    dt = T / n_steps
    taus = [T - i * dt for i, _ in records]  # records run backward -> taus ascending
    boundary = [s for _, s in records]
    return taus, boundary
