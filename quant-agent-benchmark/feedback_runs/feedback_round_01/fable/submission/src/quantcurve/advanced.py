"""Advanced model: penalised cubic B-spline forward curve with robust IRLS.

Objective (coefficients ``theta`` in percent units, ``beta = theta / 100``)::

    sum_i rho( r_i(beta) / (s_type(i) * scale_i) ) + lambda * theta' Omega theta

* ``r_i`` - market-minus-model residual in yield-equivalent rate units;
* ``scale_i`` - spread/liquidity base scale (``weights.base_scales``);
* ``s_type`` - robust residual scale per instrument type (MAD based, floored
  at 1 so a quote is never treated as more precise than its spread-based
  scale), so noisier instrument classes (bonds) are automatically
  down-weighted relative to precise ones (OIS);
* ``rho`` - Tukey's biweight (redescending: gross outliers get zero weight);
* ``Omega`` - exact integrated squared second derivative of the forward curve.

Robust residual treatment has three layers:

1. cross-sectional peer screens inside replicated tenor clusters (cleaning);
2. a leave-tenor-out screen: every tenor cluster is refitted without itself
   and quotes in *small* clusters (fewer than three rate quotes, and every
   bond) whose out-of-sample residual is extreme are excluded - this is what
   catches a wrong quote that is the only liquid quote at its tenor;
3. IRLS with Tukey weights at the target ``lambda``, guarded so that a tenor
   cluster whose quotes agree with each other but not with the curve is never
   rejected wholesale (that is model misfit, not bad data).

``lambda`` is chosen by maturity-grouped K-fold cross-validation (whole tenor
clusters are held out together so near-duplicate quotes never leak across
folds; the shortest and longest clusters are always kept in the training set).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from .curve import BSplineForwardCurve
from .instruments import Instrument
from .pricing import SplineResidualEngine

PCT = 100.0


@dataclass
class AdvancedConfig:
    lambda_grid: np.ndarray = field(default_factory=lambda: np.logspace(-3, 4, 22))
    lambda_fixed: float | None = None
    lambda_reference: float = 10.0
    huber_c: float = 1.345
    tukey_c: float = 4.685
    loo_c: float = 6.0
    loo_min_dev_bp: float = 3.0
    max_iterations: int = 60
    tol: float = 1e-6
    scale_floor: float = 1.0
    min_type_members: int = 5
    n_folds: int = 5
    cv_max_tolerance: float = 0.0
    max_knots: int = 28
    penalty_t0: float = 0.5
    penalty_tref: float = 5.0
    penalty_power: float = 1.0
    penalty_power_grid: tuple[float, ...] = (0.0, 0.5, 1.0)
    select_penalty_power: bool = False


def make_knots(maturities: np.ndarray, types: np.ndarray, t_max: float, max_knots: int = 28) -> np.ndarray:
    """Interior knots at the tenor clusters of rate instruments (fallback: all)."""
    maturities = np.asarray(maturities, dtype=float)
    rate_mask = np.isin(types, ["deposit", "ois_swap"])
    cand = np.unique(np.round(maturities[rate_mask], 6)) if rate_mask.sum() >= 4 else np.unique(np.round(maturities, 6))
    cand = cand[(cand > 0) & (cand < t_max - 1e-9)]
    knots: list[float] = []
    for m in cand:
        if not knots or (m - knots[-1]) > max(0.04, 0.03 * m):
            knots.append(float(m))
    while len(knots) > max_knots:
        gaps = np.diff([0.0] + knots + [t_max])
        drop = int(np.argmin(gaps[:-1] + gaps[1:]))
        knots.pop(drop)
    return np.array(knots)


def penalty_weight(cfg: "AdvancedConfig", power: float | None = None):
    """Maturity-dependent roughness weight ``((t + t0) / (tref + t0)) ** p``.

    Information density falls with maturity (quarterly deposits, yearly then
    five-yearly swaps), so the forward curve is allowed more curvature at the
    front end and less at the long end (Anderson & Sleath, 2001). ``p = 0``
    recovers the uniform penalty; ``p`` is selected by cross-validation.
    """
    power = cfg.penalty_power if power is None else power
    if power == 0:
        return None
    return lambda t: ((np.asarray(t, dtype=float) + cfg.penalty_t0) / (cfg.penalty_tref + cfg.penalty_t0)) ** power


def penalty_root(omega: np.ndarray) -> np.ndarray:
    """``L`` with ``L'L = Omega`` (eigen square root, tiny modes dropped)."""
    vals, vecs = np.linalg.eigh((omega + omega.T) / 2.0)
    keep = vals > 1e-12 * vals.max()
    return np.sqrt(vals[keep])[:, None] * vecs[:, keep].T


def huber_factor(u: np.ndarray, c: float) -> np.ndarray:
    a = np.abs(u)
    return np.where(a <= c, 1.0, c / np.maximum(a, 1e-300))


def tukey_factor(u: np.ndarray, c: float) -> np.ndarray:
    a = np.abs(u)
    return np.where(a < c, (1.0 - (a / c) ** 2) ** 2, 0.0)


def type_scales(std_res: np.ndarray, types: np.ndarray, floor: float, min_members: int, all_types: np.ndarray | None = None) -> dict[str, float]:
    """Robust per-type residual scale (MAD about zero / 0.6745), floored.

    Types with fewer than ``min_members`` active residuals - including types
    that are absent from ``types`` altogether but present in ``all_types``
    (e.g. every deposit of a sparse training fold currently down-weighted to
    zero) - fall back to the global scale instead of raising.
    """
    out: dict[str, float] = {}
    global_scale = max(float(np.median(np.abs(std_res))) / 0.6745, floor) if len(std_res) else floor
    universe = np.unique(types) if all_types is None else np.unique(np.concatenate([np.unique(types), np.unique(all_types)]))
    for t in universe:
        r = std_res[types == t]
        out[str(t)] = max(float(np.median(np.abs(r))) / 0.6745, floor) if len(r) >= min_members else global_scale
    return out


def solve_penalized(engine: SplineResidualEngine, weights: np.ndarray, lam: float, L: np.ndarray, theta0: np.ndarray) -> np.ndarray:
    """Weighted penalised least squares in the coefficients (percent units)."""
    sw = np.sqrt(np.maximum(weights, 0.0))
    sl = np.sqrt(lam)
    active = sw > 0

    def fun(theta: np.ndarray) -> np.ndarray:
        r = engine.residuals(theta / PCT)
        return np.concatenate([(sw * r)[active], sl * (L @ theta)])

    def jac(theta: np.ndarray) -> np.ndarray:
        J = engine.jacobian(theta / PCT) / PCT
        return np.vstack([(sw[:, None] * J)[active], sl * L])

    sol = least_squares(fun, theta0, jac=jac, method="lm", xtol=1e-12, ftol=1e-12, gtol=1e-12, max_nfev=400)
    if not np.all(np.isfinite(sol.x)):
        raise RuntimeError("penalised least squares diverged")
    return sol.x


def _cluster_guard(factor: np.ndarray, u: np.ndarray, types: np.ndarray, cluster_ids: np.ndarray | None, c_huber: float) -> np.ndarray:
    """Tenor-cluster consensus guard.

    When every rate quote of a tenor cluster (>= 2 members) deviates from the
    curve in the same direction by more than the Huber constant, the quotes
    agree with each other and disagree with the curve: that is model misfit
    (or a convention mismatch), not a data error. The redescending Tukey
    weights would silently discard the whole tenor, so they are replaced by
    Huber weights, which keep a bounded but non-vanishing pull on the curve.
    """
    if cluster_ids is None:
        return factor
    out = factor.copy()
    rate = np.isin(types, ["deposit", "ois_swap"])
    for cid in np.unique(cluster_ids[rate]):
        members = np.flatnonzero(rate & (cluster_ids == cid))
        um = u[members]
        if len(members) < 2:
            # Singleton guard (feedback round 1): a lone quote has no peer that
            # could corroborate a hard rejection, and on thin front ends the
            # redescending weight discarded genuine curvature (three lone
            # deposits on a humped synthetic curve, 23bp front-end error).
            # It keeps a bounded Huber pull instead of vanishing.
            if np.abs(um[0]) > c_huber:
                out[members] = huber_factor(um, c_huber)
            continue
        if np.all(np.abs(um) > c_huber) and (np.all(um > 0) or np.all(um < 0)):
            out[members] = huber_factor(um, c_huber)
    return out


@dataclass
class LooScreen:
    std_residuals: np.ndarray  # leave-tenor-out residual / base scale
    scales: dict[str, float]
    excluded: np.ndarray  # bool mask


def leave_tenor_out_screen(
    engine: SplineResidualEngine,
    base_scale: np.ndarray,
    types: np.ndarray,
    cluster_ids: np.ndarray,
    lam: float,
    L: np.ndarray,
    theta: np.ndarray,
    cfg: AdvancedConfig,
    factor: np.ndarray,
) -> LooScreen:
    """Out-of-sample residual of every instrument when its tenor cluster is left out."""
    n = len(base_scale)
    loo = np.zeros(n)
    curve = engine.curve
    insts = engine.instruments
    weights = factor / base_scale**2
    for cid in np.unique(cluster_ids):
        test = cluster_ids == cid
        train = ~test
        if train.sum() < curve.n_basis // 2:
            loo[test] = engine.residuals(theta / PCT)[test] / base_scale[test]
            continue
        sub = SplineResidualEngine(curve, [i for i, m in zip(insts, train) if m])
        th = solve_penalized(sub, weights[train], lam, L, theta)
        test_engine = SplineResidualEngine(curve, [i for i, m in zip(insts, test) if m])
        loo[test] = test_engine.residuals(th / PCT) / base_scale[test]
    scales = type_scales(loo[factor > 0], types[factor > 0], cfg.scale_floor, cfg.min_type_members, all_types=types)
    s_vec = np.array([scales[str(t)] for t in types])
    u = loo / s_vec
    rate = np.isin(types, ["deposit", "ois_swap"])
    small = np.zeros(n, dtype=bool)
    for cid in np.unique(cluster_ids):
        members = cluster_ids == cid
        if (members & rate).sum() < 3:
            small |= members & rate
    small |= ~rate
    dev_bp = np.abs(loo * base_scale) * 1e4
    excluded = small & (np.abs(u) > cfg.loo_c) & (dev_bp > cfg.loo_min_dev_bp)
    # Consensus guard: a rate cluster whose quotes are *all* flagged with the
    # same sign disagrees with the curve, not with itself - keep it.
    for cid in np.unique(cluster_ids):
        members = np.flatnonzero(rate & (cluster_ids == cid))
        if len(members) >= 2 and np.all(excluded[members]) and (np.all(u[members] > 0) or np.all(u[members] < 0)):
            excluded[members] = False
    # Edge guard (feedback round 1): leaving out the shortest or the longest
    # rate cluster turns the "out-of-sample" prediction into an extrapolation,
    # which cannot distinguish genuine front/back-end curvature from a bad
    # quote (a lone 1M deposit on a strongly humped curve was rejected with
    # u=-44 on synthetic data). Edge rate clusters are left to the Tukey stage.
    if rate.any():
        mats = np.array([i.maturity for i in insts])
        edge_ids = []
        for cid in np.unique(cluster_ids[rate]):
            members = rate & (cluster_ids == cid)
            edge_ids.append((float(np.median(mats[members])), cid))
        edge_ids.sort()
        for _, cid in (edge_ids[0], edge_ids[-1]):
            excluded[rate & (cluster_ids == cid)] = False
    return LooScreen(std_residuals=loo, scales=scales, excluded=excluded)


@dataclass
class RobustFitResult:
    theta: np.ndarray
    robust_factor: np.ndarray
    std_residuals: np.ndarray
    type_scale: dict[str, float]
    weights: np.ndarray
    iterations: int
    converged: bool
    loo: LooScreen | None = None


def robust_fit(
    engine: SplineResidualEngine,
    base_scale: np.ndarray,
    types: np.ndarray,
    lam: float,
    L: np.ndarray,
    theta0: np.ndarray,
    cfg: AdvancedConfig,
    fixed_factor: np.ndarray | None = None,
    cluster_ids: np.ndarray | None = None,
    run_loo: bool = True,
) -> RobustFitResult:
    """Leave-tenor-out screen followed by Tukey IRLS at the target lambda."""
    theta = np.array(theta0, dtype=float)
    types = np.asarray(types)
    n = len(base_scale)
    if fixed_factor is not None:
        factor = np.asarray(fixed_factor, dtype=float)
        r = engine.residuals(theta / PCT) / base_scale
        scales = type_scales(r[factor > 0], types[factor > 0], cfg.scale_floor, cfg.min_type_members, all_types=types)
        s_vec = np.array([scales[str(t)] for t in types])
        weights = factor / (base_scale * s_vec) ** 2
        theta = solve_penalized(engine, weights, lam, L, theta)
        r = engine.residuals(theta / PCT) / base_scale
        return RobustFitResult(theta, factor, r / s_vec, scales, weights, 1, True)

    # Stage 0: plain weighted fit, then one Huber pass to tame gross outliers.
    theta = solve_penalized(engine, 1.0 / base_scale**2, lam, L, theta)
    r = engine.residuals(theta / PCT) / base_scale
    g = max(float(np.median(np.abs(r))) / 0.6745, cfg.scale_floor)
    factor = huber_factor(r / g, cfg.huber_c)
    theta = solve_penalized(engine, factor / (base_scale * g) ** 2, lam, L, theta)

    # Stage 1: leave-tenor-out screen (sticky exclusions).
    sticky = np.ones(n)
    loo = None
    if run_loo and cluster_ids is not None:
        r = engine.residuals(theta / PCT) / base_scale
        factor = huber_factor(r / g, cfg.huber_c)
        loo = leave_tenor_out_screen(engine, base_scale, types, cluster_ids, lam, L, theta, cfg, factor)
        sticky[loo.excluded] = 0.0

    # Stage 2: Tukey IRLS with per-type scales and the cluster guard.
    iterations = 0
    converged = False
    scales = {str(t): 1.0 for t in np.unique(types)}
    u = np.zeros(n)
    factor = sticky.copy()
    for _ in range(cfg.max_iterations):
        r = engine.residuals(theta / PCT) / base_scale
        good = factor > 0
        scales = type_scales(r[good], types[good], cfg.scale_floor, cfg.min_type_members, all_types=types)
        s_vec = np.array([scales[str(t)] for t in types])
        u = r / s_vec
        factor = sticky * _cluster_guard(tukey_factor(u, cfg.tukey_c), u, types, cluster_ids, cfg.huber_c)
        weights = factor / (base_scale * s_vec) ** 2
        new_theta = solve_penalized(engine, weights, lam, L, theta)
        iterations += 1
        step = float(np.max(np.abs(new_theta - theta)))
        theta = new_theta
        if step < cfg.tol * max(1.0, float(np.max(np.abs(theta)))):
            converged = True
            break
    r = engine.residuals(theta / PCT) / base_scale
    s_vec = np.array([scales[str(t)] for t in types])
    u = r / s_vec
    factor = sticky * _cluster_guard(tukey_factor(u, cfg.tukey_c), u, types, cluster_ids, cfg.huber_c)
    weights = factor / (base_scale * s_vec) ** 2
    return RobustFitResult(theta, factor, u, scales, weights, iterations, converged, loo)


def grouped_folds(cluster_ids: np.ndarray, maturities: np.ndarray, n_folds: int) -> np.ndarray:
    """Fold id per instrument; -1 marks always-train anchor clusters."""
    cluster_ids = np.asarray(cluster_ids)
    maturities = np.asarray(maturities, dtype=float)
    clusters = sorted(np.unique(cluster_ids), key=lambda c: float(np.median(maturities[cluster_ids == c])))
    folds = np.full(len(cluster_ids), -1, dtype=int)
    if len(clusters) <= 2:
        return folds
    for rank, cid in enumerate(clusters[1:-1]):
        folds[cluster_ids == cid] = rank % n_folds
    return folds


@dataclass
class CVResult:
    table: pd.DataFrame
    lam: float
    lam_min: float
    threshold: float
    power: float = 1.0
    power_table: pd.DataFrame | None = None


def cross_validate_lambda(
    curve: BSplineForwardCurve,
    instruments: list[Instrument],
    base_scale: np.ndarray,
    types: np.ndarray,
    fixed_factor: np.ndarray,
    folds: np.ndarray,
    L: np.ndarray,
    theta0: np.ndarray,
    cfg: AdvancedConfig,
) -> CVResult:
    """Grouped K-fold CV score (RMSE of standardised held-out residuals) per lambda."""
    rows = []
    fold_ids = sorted(set(int(f) for f in folds if f >= 0))
    evaluable = fixed_factor > 0
    for lam in cfg.lambda_grid:
        sq, count, per_fold = 0.0, 0, []
        for f in fold_ids:
            train = folds != f
            test = (folds == f) & evaluable
            if test.sum() == 0:
                continue
            sub = SplineResidualEngine(curve, [inst for inst, m in zip(instruments, train) if m])
            fit = robust_fit(sub, base_scale[train], types[train], lam, L, theta0, cfg, fixed_factor=fixed_factor[train])
            test_engine = SplineResidualEngine(curve, [inst for inst, m in zip(instruments, test) if m])
            s_vec = np.array([fit.type_scale.get(str(t), 1.0) for t in types[test]])
            u = test_engine.residuals(fit.theta / PCT) / (base_scale[test] * s_vec)
            per_fold.append(float(np.sqrt(np.mean(u**2))))
            sq += float(np.sum(u**2))
            count += int(test.sum())
        rows.append({"lambda": float(lam), "cv_score": float(np.sqrt(sq / max(count, 1))), "fold_scores": per_fold})
    table = pd.DataFrame(rows)
    table["fold_se"] = [float(np.std(f, ddof=1) / np.sqrt(len(f))) if len(f) > 1 else 0.0 for f in table["fold_scores"]]
    best_idx = int(table["cv_score"].idxmin())
    best = float(table.loc[best_idx, "cv_score"])
    lam_min = float(table.loc[best_idx, "lambda"])
    # One-standard-error rule (parsimony): the stiffest curve whose CV score is
    # within one fold standard error of the minimum, capped at a relative
    # tolerance so a noisy fold split cannot force gross over-smoothing.
    tolerance = min(float(table.loc[best_idx, "fold_se"]), cfg.cv_max_tolerance * best)
    threshold = best + tolerance
    lam = float(table.loc[table["cv_score"] <= threshold, "lambda"].max())
    return CVResult(table=table, lam=lam, lam_min=lam_min, threshold=threshold)


@dataclass
class AdvancedFit:
    curve: BSplineForwardCurve
    lam: float
    power: float
    fit: RobustFitResult
    cv: CVResult | None
    knots: np.ndarray
    base_scale: np.ndarray
    folds: np.ndarray
    L: np.ndarray


def fit_advanced(
    instruments: list[Instrument],
    base_scale: np.ndarray,
    types: np.ndarray,
    cluster_ids: np.ndarray,
    t_max: float,
    cfg: AdvancedConfig,
    lam: float | None = None,
    power: float | None = None,
    knots: np.ndarray | None = None,
    folds: np.ndarray | None = None,
    run_cv: bool = True,
) -> AdvancedFit:
    """Fit the advanced model; ``lam``/``power`` are selected by grouped CV unless given."""
    maturities = np.array([i.maturity for i in instruments])
    types = np.asarray(types)
    cluster_ids = np.asarray(cluster_ids)
    if knots is None:
        knots = make_knots(maturities, types, t_max, cfg.max_knots)
    curve = BSplineForwardCurve(knots, t_max)
    engine = SplineResidualEngine(curve, instruments)
    rate_quotes = [i.quote for i in instruments if i.is_rate]
    level = float(np.median(rate_quotes)) if rate_quotes else 0.02
    theta0 = np.full(curve.n_basis, level * PCT)
    if folds is None:
        folds = grouped_folds(cluster_ids, maturities, cfg.n_folds)
    cv = None
    if lam is None:
        lam = cfg.lambda_fixed
    select_power = power is None and cfg.select_penalty_power
    power = cfg.penalty_power if power is None else power
    if lam is None:
        L_ref = penalty_root(curve.penalty_matrix(penalty_weight(cfg, cfg.penalty_power)))
        pre = robust_fit(engine, base_scale, types, cfg.lambda_reference, L_ref, theta0, cfg, cluster_ids=cluster_ids)
        theta0 = pre.theta
        if run_cv:
            # CV over lambda for every candidate penalty shape (reported for
            # information); the shape is only *selected* by CV when requested,
            # otherwise the a-priori maturity-weighted shape is kept because it
            # is markedly more robust at the front end (see sensitivity checks).
            powers = tuple(sorted(set(cfg.penalty_power_grid) | {float(power)}))
            results = {}
            summaries = []
            for p in powers:
                L_p = penalty_root(curve.penalty_matrix(penalty_weight(cfg, p)))
                res = cross_validate_lambda(curve, instruments, base_scale, types, pre.robust_factor, folds, L_p, pre.theta, cfg)
                res.power = float(p)
                results[float(p)] = res
                summaries.append({"penalty_power": float(p), "lambda": res.lam, "cv_score": float(res.table.set_index("lambda")["cv_score"][res.lam]), "selected": False})
            if select_power:
                power = min(summaries, key=lambda r: r["cv_score"])["penalty_power"]
            cv = results[float(power)]
            for r in summaries:
                r["selected"] = r["penalty_power"] == float(power)
            cv.power_table = pd.DataFrame(summaries)
            lam = cv.lam
        else:
            lam = cfg.lambda_reference
    L = penalty_root(curve.penalty_matrix(penalty_weight(cfg, power)))
    fit = robust_fit(engine, base_scale, types, lam, L, theta0, cfg, cluster_ids=cluster_ids)
    return AdvancedFit(curve=curve.with_coeffs(fit.theta / PCT), lam=float(lam), power=float(power), fit=fit, cv=cv, knots=knots, base_scale=base_scale, folds=folds, L=L)
