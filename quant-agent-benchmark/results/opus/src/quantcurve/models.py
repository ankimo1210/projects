"""The two zero-curve estimators and the machinery they share.

Baseline -- ``fit_baseline``
    A textbook sequential bootstrap.  Instruments are collapsed into one
    consensus quote per pillar and each pillar is repriced *exactly* by solving
    for the constant instantaneous forward on the segment it adds.  Discount
    factors are therefore log-linear in maturity and forwards are piecewise
    constant.  The method is transparent and reproducible, but it interpolates
    the noise: every quote error is transmitted one-for-one into the curve, and
    two pillars close together create a large forward step.

Advanced -- ``fit_advanced``
    A penalised, robustly reweighted spline in the instantaneous forward rate.
    The objective is

    .. math::
        \\sum_i w_i \\rho\\big(r_i(\\theta)\\big) + \\lambda \\int (f''(u))^2 du

    with ``r_i`` the yield-equivalent repricing residual in basis points, ``w_i``
    the spread/liquidity precision weight, ``rho`` Tukey's biweight applied by
    iteratively reweighted least squares with a *fixed* robust scale, and the
    roughness penalty discretised on the knot grid.  The smoothing weight
    ``lambda`` is chosen by maturity-blocked cross-validation *inside the
    training sample only*, so a holdout metric computed afterwards stays honest.

Both estimators return a :class:`~quantcurve.curve.DiscountCurve`, so every
downstream diagnostic, chart and risk number is computed identically for the two
models.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import brentq, least_squares

from .curve import DiscountCurve, PiecewiseFlatForwardCurve, SplineForwardCurve
from .instruments import Instrument
from .pricing import CalibrationSet, model_quote

__all__ = [
    "FitConfig",
    "BaselineFit",
    "AdvancedFit",
    "Pillar",
    "fit_baseline",
    "fit_advanced",
    "residuals_bp",
    "weighted_rmse_bp",
    "fit_metrics",
    "select_knots",
    "consensus_pillars",
    "screen_outliers",
    "local_residuals",
]


@dataclass(frozen=True)
class FitConfig:
    """Estimator settings.  Every default is documented in ``MODEL_RISKS.md``."""

    # -- baseline --------------------------------------------------------
    #: Pillars closer together than this (in years) are merged; bootstrapping
    #: two nearly coincident maturities produces an explosive forward step.
    min_pillar_gap_years: float = 0.10
    #: Bracket used when solving for a segment forward.
    forward_bracket: tuple[float, float] = (-0.95, 1.50)

    # -- advanced --------------------------------------------------------
    max_knots: int = 24
    min_knots: int = 4
    observations_per_knot: float = 4.0
    #: Knot-budget floor driven by maturity *coverage* rather than sample size.
    #: A basis has to be able to represent the curvature the term structure
    #: actually has; how much of that flexibility is used is then decided by the
    #: cross-validated roughness penalty, not by the knot count.  Without this
    #: floor a small but wide data set (twenty quotes spanning 1M to 30Y) gets a
    #: five-knot basis that cannot bend at the money-market end and mis-prices
    #: the shortest deposit by ~10bp.
    knots_per_log_decade: float = 4.0
    #: Minimum separation between knots as a fraction of the log-maturity span.
    min_knot_log_gap: float = 0.02
    #: Candidate roughness weights explored by cross-validation.  The scale is
    #: set by the objective units: residuals in bp, forwards in bp, maturities in
    #: years, so ``lambda`` is a bp^2/year^3 penalty on forward curvature.
    lambda_grid: tuple[float, ...] = (
        1.0e-6, 1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0, 1.0e1,
    )
    #: Roughness is penalised more heavily at long maturities.  An unweighted
    #: integral of ``f''^2`` over-penalises the front end, where curvature
    #: naturally scales like ``1/T^2`` and where the data are densest; the
    #: maturity-dependent weight ``(T / reference)^power`` is the standard
    #: Waggoner (1997) remedy.
    penalty_maturity_power: float = 2.0
    #: The exponent is itself selected by the inner cross-validation, jointly
    #: with ``lambda``: how fast the smoothing should tighten with maturity is a
    #: property of the data, not something to assert a priori.
    penalty_power_grid: tuple[float, ...] = (1.0, 2.0)
    penalty_reference_years: float = 1.0
    #: Tukey biweight tuning constant, in units of the robust residual scale.
    tukey_c: float = 4.685
    #: Huber tuning constant used for the warm-up sweeps.  Tukey's biweight is
    #: redescending, so its objective is not convex and it can settle on the wrong
    #: cluster when the starting curve is dragged away by gross outliers.  Huber's
    #: loss is convex, so the warm-up has a unique solution and gives the
    #: redescending stage a high-breakdown starting point.
    huber_c: float = 1.345
    huber_iterations: int = 4
    max_irls_iterations: int = 25
    irls_tolerance: float = 1.0e-3
    #: The robust scale is re-estimated for this many sweeps and then frozen, so
    #: that the redescending weight function cannot oscillate indefinitely.
    scale_freeze_iteration: int = 3
    #: Floor on the robust scale (bp) so a near-perfect fit cannot make the
    #: reweighting infinitely sensitive.  Half a basis point is the smallest
    #: credible dispersion of a set of independently sourced market quotes around
    #: a fitted curve; below it the scale is measuring rounding, and every
    #: ordinary quote becomes a many-sigma event.
    min_robust_scale_bp: float = 0.5
    #: Number of maturity blocks used by the inner cross-validation.
    cv_folds: int = 4
    #: Optional one-standard-error rule: among the candidates statistically
    #: indistinguishable from the best, take the smoothest.  Left off, because on
    #: this class of problem it costs measurable calibration accuracy at genuine
    #: term-structure features (the 7Y hump) in exchange for a stability gain
    #: that the sensitivity suite shows is already adequate.  The full
    #: cross-validation table is published so the trade-off can be re-checked.
    one_se_rule: bool = False
    #: Largest share of the sample the outlier screen may exclude.
    max_exclusion_fraction: float = 0.25
    #: The outlier screen uses a *fixed, deliberately flexible* reference fit
    #: rather than a cross-validated one.  A cross-validated roughness weight is
    #: chosen for prediction, and on a contaminated sample it can be stiff enough
    #: that ordinary smoothing bias at a steep part of the curve looks exactly
    #: like a cluster of bad quotes.  Robust reweighting is what stops the
    #: flexible reference from chasing the outliers themselves.
    screening_lambda: float = 1.0e-5
    screening_power: float = 1.0
    #: Number of maturity neighbours used to build the local residual reference.
    screening_neighbours: int = 8
    #: Absolute economic gate on exclusion.  Standardised distance alone is not
    #: enough: with a flexible reference fit the robust scale can collapse to a
    #: fraction of a basis point, at which point a quote sitting 2bp from its
    #: neighbours -- inside any plausible bid/ask, and well inside the ~3bp
    #: idiosyncratic spread noise measured on the bonds -- looks like a 40-sigma
    #: outlier.  An observation must be *both* statistically extreme and
    #: economically material before it is thrown away.
    min_outlier_bp: float = 5.0


# --------------------------------------------------------------------------
# shared residual helpers
# --------------------------------------------------------------------------
def residuals_bp(
    curve: DiscountCurve, instruments: list[Instrument] | CalibrationSet
) -> np.ndarray:
    """Yield-equivalent repricing residuals (market minus model) in basis points."""
    calset = instruments if isinstance(instruments, CalibrationSet) else CalibrationSet(instruments)
    return calset.residuals_bp(curve)


def weighted_rmse_bp(
    curve: DiscountCurve, instruments: list[Instrument] | CalibrationSet
) -> float:
    calset = instruments if isinstance(instruments, CalibrationSet) else CalibrationSet(instruments)
    if calset.n == 0:
        return float("nan")
    r = calset.residuals_bp(curve)
    w = calset.weights
    if w.sum() <= 0:
        return float(np.sqrt(np.mean(r**2)))
    return float(np.sqrt(np.sum(w * r**2) / np.sum(w)))


def fit_metrics(
    curve: DiscountCurve, instruments: list[Instrument] | CalibrationSet
) -> dict[str, float]:
    """Standard repricing statistics for a curve / instrument-set pair."""
    calset = instruments if isinstance(instruments, CalibrationSet) else CalibrationSet(instruments)
    if calset.n == 0:
        return {
            "n_instruments": 0,
            "rmse_bp": float("nan"),
            "weighted_rmse_bp": float("nan"),
            "mae_bp": float("nan"),
            "max_abs_bp": float("nan"),
            "median_abs_bp": float("nan"),
        }
    r = calset.residuals_bp(curve)
    w = calset.weights
    wsum = float(w.sum())
    return {
        "n_instruments": int(calset.n),
        "rmse_bp": float(np.sqrt(np.mean(r**2))),
        "weighted_rmse_bp": float(
            np.sqrt(np.sum(w * r**2) / wsum) if wsum > 0 else np.sqrt(np.mean(r**2))
        ),
        "mae_bp": float(np.mean(np.abs(r))),
        "max_abs_bp": float(np.max(np.abs(r))),
        "median_abs_bp": float(np.median(np.abs(r))),
    }


# --------------------------------------------------------------------------
# baseline bootstrap
# --------------------------------------------------------------------------
@dataclass
class Pillar:
    maturity_years: float
    representative: Instrument
    members: list[Instrument]
    consensus_quote: float
    total_weight: float


@dataclass
class BaselineFit:
    curve: PiecewiseFlatForwardCurve
    pillars: list[Pillar]
    skipped: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    name = "bootstrap_loglinear_df"
    description = (
        "sequential bootstrap of consensus pillars; log-linear discount factors "
        "(piecewise-constant instantaneous forwards); every pillar repriced exactly"
    )


def consensus_pillars(
    instruments: list[Instrument], config: FitConfig | None = None
) -> list[Pillar]:
    """Collapse economically identical quotes into one consensus pillar each.

    Instruments are identical when their type, maturity, coupon and payment
    frequency agree.  Their quotes are averaged with the cleaning weights, which
    is the standard way a desk forms a composite from several venues.  Pillars
    closer than ``min_pillar_gap_years`` are then merged, keeping the most
    heavily weighted one, because an exact bootstrap cannot support two nearly
    coincident maturities without producing an explosive forward step.
    """
    config = config or FitConfig()
    groups: dict[tuple, list[Instrument]] = {}
    for inst in instruments:
        key = (
            inst.instrument_type,
            round(inst.maturity_years, 9),
            None if inst.coupon_rate is None else round(inst.coupon_rate, 12),
            inst.fixed_frequency,
        )
        groups.setdefault(key, []).append(inst)

    pillars: list[Pillar] = []
    for key in sorted(groups, key=lambda k: (k[1], k[0], str(k[2]), k[3])):
        members = groups[key]
        weights = np.array([m.weight for m in members], dtype=float)
        total = float(weights.sum())
        if total <= 0:
            continue
        quote = float(np.sum(weights * np.array([m.quote for m in members])) / total)
        representative = max(members, key=lambda m: (m.weight, m.instrument_id))
        pillars.append(
            Pillar(
                maturity_years=float(key[1]),
                representative=representative.with_weight(total),
                members=members,
                consensus_quote=quote,
                total_weight=total,
            )
        )

    pillars.sort(key=lambda p: p.maturity_years)
    merged: list[Pillar] = []
    for pillar in pillars:
        if (
            merged
            and pillar.maturity_years - merged[-1].maturity_years
            < config.min_pillar_gap_years
        ):
            if pillar.total_weight > merged[-1].total_weight:
                merged[-1] = pillar
            continue
        merged.append(pillar)
    return merged


def _pillar_quote_error(curve: PiecewiseFlatForwardCurve, pillar: Pillar) -> float:
    inst = pillar.representative
    trial = inst.with_weight(inst.weight)
    trial = Instrument(
        obs_id=inst.obs_id,
        instrument_id=inst.instrument_id,
        instrument_type=inst.instrument_type,
        maturity_years=inst.maturity_years,
        coupon_rate=inst.coupon_rate,
        payment_frequency=inst.payment_frequency,
        quote=pillar.consensus_quote,
        half_spread=inst.half_spread,
        liquidity_score=inst.liquidity_score,
        weight=inst.weight,
        source=inst.source,
        timestamp=inst.timestamp,
    )
    return pillar.consensus_quote - model_quote(curve, trial)


def fit_baseline(
    instruments: list[Instrument], config: FitConfig | None = None
) -> BaselineFit:
    """Sequential bootstrap with piecewise-constant instantaneous forwards."""
    config = config or FitConfig()
    pillars = consensus_pillars(instruments, config)
    if not pillars:
        raise ValueError("no usable instruments for the baseline bootstrap")

    times: list[float] = []
    forwards: list[float] = []
    used: list[Pillar] = []
    skipped: list[str] = []
    notes: list[str] = []

    for pillar in pillars:
        candidate_times = times + [pillar.maturity_years]

        def objective(f: float, _times=candidate_times, _pillar=pillar) -> float:
            trial = PiecewiseFlatForwardCurve(
                np.array(_times), np.array(forwards + [f])
            )
            return _pillar_quote_error(trial, _pillar)

        lo, hi = config.forward_bracket
        solved: float | None = None
        for scale in (1.0, 3.0, 10.0):
            a, b = lo * scale, hi * scale
            try:
                fa, fb = objective(a), objective(b)
            except (ValueError, FloatingPointError, OverflowError):
                continue
            if not (np.isfinite(fa) and np.isfinite(fb)) or fa * fb > 0:
                continue
            solved = float(
                brentq(objective, a, b, xtol=1.0e-14, rtol=8.9e-16, maxiter=200)
            )
            break
        if solved is None:
            skipped.append(
                f"{pillar.representative.instrument_id} @ {pillar.maturity_years:.4f}Y"
            )
            continue
        times = candidate_times
        forwards.append(solved)
        used.append(pillar)

    if not times:
        raise ValueError(
            "the bootstrap failed for every pillar; the quotes are not arbitrage-free"
        )
    if skipped:
        notes.append(
            f"bootstrap could not solve {len(skipped)} pillar(s), dropped: "
            + ", ".join(skipped)
        )
    curve = PiecewiseFlatForwardCurve(np.array(times), np.array(forwards))
    return BaselineFit(curve=curve, pillars=used, skipped=skipped, notes=notes)


# --------------------------------------------------------------------------
# advanced penalised spline
# --------------------------------------------------------------------------
@dataclass
class AdvancedFit:
    curve: SplineForwardCurve
    knots: np.ndarray
    smoothing_lambda: float
    penalty_power: float
    robust_weights: np.ndarray
    iterations: int
    converged: bool
    robust_scale_bp: float = float("nan")
    cv_scores: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    name = "penalised_robust_forward_spline"
    description = (
        "cubic spline in the instantaneous forward rate, fitted by weighted "
        "non-linear least squares with a second-derivative roughness penalty and "
        "Tukey-biweight iteratively reweighted least squares; flat-forward "
        "extrapolation outside the calibrated maturity range"
    )


def select_knots(
    instruments: list[Instrument], config: FitConfig | None = None
) -> np.ndarray:
    """Log-uniform knots snapped to observed maturities.

    Term structures carry far more curvature per year at the front than at the
    back, so knots are spread uniformly in ``log T`` rather than in ``T`` or in
    sample quantiles -- pure maturity quantiles starve the money-market end,
    where a handful of deposits describe the steepest part of the curve.  Each
    target is then snapped to the nearest maturity actually quoted, so no knot
    ever sits in a region the data cannot support, and duplicates are dropped.
    """
    config = config or FitConfig()
    maturities = np.array([i.maturity_years for i in instruments], dtype=float)
    maturities = maturities[np.isfinite(maturities) & (maturities > 0)]
    if maturities.size == 0:
        raise ValueError("no usable maturities for knot selection")
    unique = np.unique(maturities)
    if unique.size <= 2:
        return unique

    # Prefer snapping onto benchmark rate maturities.  Deposits and OIS swaps are
    # the instruments that actually define the curve; bond maturities are dense,
    # arbitrary and carry idiosyncratic spreads, so a knot placed on one buys
    # flexibility exactly where the data are least trustworthy.
    preferred = np.unique(
        np.array(
            [i.maturity_years for i in instruments if i.is_rate_quote and i.maturity_years > 0],
            dtype=float,
        )
    )
    anchors = preferred if preferred.size >= config.min_knots else unique

    decades = float(np.log10(unique[-1] / unique[0]))
    coverage = int(np.ceil(decades * config.knots_per_log_decade)) + 1
    budget = int(
        np.clip(
            max(round(maturities.size / config.observations_per_knot), coverage),
            config.min_knots,
            config.max_knots,
        )
    )
    budget = min(budget, unique.size)
    if anchors.size <= budget:
        # Every benchmark maturity gets a knot.  With a roughness penalty doing
        # the smoothing this is the standard penalised-spline setup: place knots
        # generously, then let the penalty (chosen by cross-validation) decide how
        # much of that flexibility is actually used.
        snapped = anchors
    else:
        targets = np.exp(np.linspace(np.log(unique[0]), np.log(unique[-1]), budget))
        snapped = anchors[np.abs(anchors[None, :] - targets[:, None]).argmin(axis=1)]
    candidates = np.unique(np.concatenate([[unique[0]], snapped, [unique[-1]]]))

    span = float(np.log(unique[-1]) - np.log(unique[0]))
    min_gap = config.min_knot_log_gap * max(span, 1.0e-9)
    kept = [float(candidates[0])]
    for value in candidates[1:-1]:
        if np.log(value) - np.log(kept[-1]) >= min_gap:
            kept.append(float(value))
    last = float(candidates[-1])
    if last > kept[-1]:
        if np.log(last) - np.log(kept[-1]) < min_gap and len(kept) > 1:
            kept[-1] = last
        else:
            kept.append(last)
    return np.array(kept, dtype=float)


def _penalty_operator(
    knots: np.ndarray, config: FitConfig | None = None, power: float | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Second-difference operator and quadrature weights for unequal knots.

    The quadrature weight carries the maturity-dependent roughness factor, so the
    penalty discretises ``lambda * integral (T/T_ref)^p f''(T)^2 dT``.
    """
    config = config or FitConfig()
    power = config.penalty_maturity_power if power is None else float(power)
    k = knots.size
    if k < 3:
        return np.zeros((0, k)), np.zeros(0)
    h = np.diff(knots)
    rows = np.zeros((k - 2, k))
    quad = np.zeros(k - 2)
    reference = max(config.penalty_reference_years, 1.0e-9)
    for j in range(1, k - 1):
        hm, hp = h[j - 1], h[j]
        scale = 2.0 / (hm + hp)
        rows[j - 1, j - 1] = scale / hm
        rows[j - 1, j] = -scale * (1.0 / hm + 1.0 / hp)
        rows[j - 1, j + 1] = scale / hp
        weight = (max(knots[j], 1.0e-9) / reference) ** power
        quad[j - 1] = 0.5 * (hm + hp) * weight
    return rows, quad


def _flat_start(calset: CalibrationSet) -> float:
    """One-parameter flat-forward fit used as a deterministic starting point."""
    if calset.n == 0:
        return 0.02
    rate_levels = [i.quote / 100.0 for i in calset.instruments if i.is_rate_quote]
    guess = float(np.median(rate_levels)) if rate_levels else 0.02
    anchor = float(np.min(calset.maturities))
    sqrt_w = np.sqrt(np.maximum(calset.weights, 0.0))

    def resid(theta: np.ndarray) -> np.ndarray:
        curve = SplineForwardCurve(np.array([anchor]), np.array([theta[0] / 1.0e4]))
        out = calset.residuals_bp(curve) * sqrt_w
        return np.where(np.isfinite(out), out, 1.0e6)

    try:
        sol = least_squares(
            resid, np.array([guess * 1.0e4]), method="lm", xtol=1e-12, ftol=1e-12
        )
        value = float(sol.x[0]) / 1.0e4
    except Exception:  # pragma: no cover - defensive
        value = guess
    if not np.isfinite(value):
        value = guess
    return float(np.clip(value, -0.5, 1.0))


def _solve_penalised(
    calset: CalibrationSet,
    knots: np.ndarray,
    lam: float,
    weights: np.ndarray,
    theta0: np.ndarray,
    config: FitConfig | None = None,
    power: float | None = None,
) -> tuple[np.ndarray, bool]:
    """Weighted penalised least squares for the knot forwards (in basis points)."""
    penalty_rows, quad = _penalty_operator(knots, config, power)
    sqrt_w = np.sqrt(np.maximum(weights, 0.0))
    penalty_scale = np.sqrt(lam * quad) if quad.size else np.zeros(0)

    def residual(theta: np.ndarray) -> np.ndarray:
        curve = SplineForwardCurve(knots, theta / 1.0e4)
        data = calset.residuals_bp(curve) * sqrt_w
        if not np.all(np.isfinite(data)):
            data = np.where(np.isfinite(data), data, 1.0e6)
        if penalty_rows.size:
            return np.concatenate([data, penalty_scale * (penalty_rows @ theta)])
        return data

    try:
        sol = least_squares(
            residual,
            theta0,
            method="lm",
            xtol=1.0e-12,
            ftol=1.0e-12,
            gtol=1.0e-12,
            max_nfev=20000,
        )
        theta = np.asarray(sol.x, dtype=float)
        ok = bool(np.all(np.isfinite(theta)))
    except Exception:  # pragma: no cover - defensive
        theta, ok = np.asarray(theta0, dtype=float), False
    if not ok:
        theta = np.asarray(theta0, dtype=float)
    return theta, ok


def _robust_scale(standardised: np.ndarray, config: FitConfig) -> float:
    centre = float(np.median(standardised))
    mad = float(np.median(np.abs(standardised - centre)))
    return max(1.4826 * mad, config.min_robust_scale_bp)


def fit_advanced(
    instruments: list[Instrument] | CalibrationSet,
    config: FitConfig | None = None,
    lam: float | None = None,
    knots: np.ndarray | None = None,
    robust: bool = True,
    power: float | None = None,
) -> AdvancedFit:
    """Penalised robust spline fit.

    ``lam=None`` selects the roughness weight *and* the maturity exponent of the
    penalty by maturity-blocked cross-validation on the supplied sample.
    """
    config = config or FitConfig()
    calset = (
        instruments
        if isinstance(instruments, CalibrationSet)
        else CalibrationSet(instruments)
    )
    if calset.n == 0:
        raise ValueError("no usable instruments for the advanced fit")
    if knots is None:
        knots = select_knots(calset.instruments, config)
    notes: list[str] = []
    cv_scores: dict[str, float] = {}

    if lam is None:
        lam, power, cv_scores, cv_note = _select_hyperparameters(calset, knots, config)
        if cv_note:
            notes.append(cv_note)
    if power is None:
        power = config.penalty_maturity_power

    theta = np.full(knots.size, _flat_start(calset) * 1.0e4, dtype=float)
    base_weights = calset.weights.copy()
    robust_weights = np.ones(calset.n, dtype=float)
    iterations = 0
    converged = not robust
    scale = float("nan")

    theta, _ = _solve_penalised(calset, knots, lam, base_weights, theta, config, power)
    if robust and calset.n >= 3:
        # Convex Huber warm-up: gives the redescending stage a starting curve that
        # gross outliers cannot have dragged onto the wrong cluster of quotes.
        for _ in range(config.huber_iterations):
            curve = SplineForwardCurve(knots, theta / 1.0e4)
            standardised = calset.residuals_bp(curve) * np.sqrt(base_weights)
            scale = _robust_scale(standardised, config)
            u = np.abs(standardised) / (config.huber_c * scale)
            huber_weights = np.where(u <= 1.0, 1.0, 1.0 / np.maximum(u, 1.0e-12))
            theta, _ = _solve_penalised(
                calset, knots, lam, base_weights * huber_weights, theta, config, power
            )
        for iterations in range(1, config.max_irls_iterations + 1):
            curve = SplineForwardCurve(knots, theta / 1.0e4)
            standardised = calset.residuals_bp(curve) * np.sqrt(base_weights)
            # The robust scale is re-estimated for the first few sweeps -- freezing
            # it at the initial, non-robust fit would inflate it exactly when gross
            # outliers are present -- and then held fixed so that the redescending
            # weight function converges instead of oscillating.
            if iterations <= config.scale_freeze_iteration or not np.isfinite(scale):
                scale = _robust_scale(standardised, config)
            u = standardised / (config.tukey_c * scale)
            new_weights = np.where(np.abs(u) < 1.0, (1.0 - u**2) ** 2, 0.0)
            if float(np.sum(base_weights * new_weights)) <= 0.0:
                notes.append("robust reweighting removed every observation; reverted")
                break
            delta = float(np.max(np.abs(new_weights - robust_weights)))
            robust_weights = new_weights
            theta, _ = _solve_penalised(
                calset, knots, lam, base_weights * robust_weights, theta, config, power
            )
            if delta < config.irls_tolerance and iterations > config.scale_freeze_iteration:
                converged = True
                break
        else:  # pragma: no cover - only when the cap binds
            notes.append(
                f"IRLS stopped at the iteration cap ({config.max_irls_iterations})"
            )

    curve = SplineForwardCurve(knots, theta / 1.0e4)
    return AdvancedFit(
        curve=curve,
        knots=np.asarray(knots, dtype=float),
        smoothing_lambda=float(lam),
        penalty_power=float(power),
        robust_weights=robust_weights,
        iterations=int(iterations),
        converged=bool(converged),
        robust_scale_bp=float(scale),
        cv_scores=cv_scores,
        notes=notes,
    )


def maturity_blocks(instruments: list[Instrument], folds: int) -> list[list[int]]:
    """Interleaved maturity blocks; quotes on the same pillar never split."""
    order = sorted(
        range(len(instruments)),
        key=lambda k: (instruments[k].maturity_years, instruments[k].instrument_id),
    )
    groups: list[list[int]] = []
    for idx in order:
        if groups and abs(
            instruments[idx].maturity_years
            - instruments[groups[-1][-1]].maturity_years
        ) < 1.0e-9:
            groups[-1].append(int(idx))
        else:
            groups.append([int(idx)])
    blocks: list[list[int]] = [[] for _ in range(folds)]
    for position, group in enumerate(groups):
        blocks[position % folds].extend(group)
    return blocks


def _select_hyperparameters(
    calset: CalibrationSet, knots: np.ndarray, config: FitConfig
) -> tuple[float, float, dict[str, float], str]:
    """Choose the roughness weight and maturity exponent by blocked CV."""
    instruments = calset.instruments
    folds = min(config.cv_folds, len(instruments))
    default = float(config.lambda_grid[len(config.lambda_grid) // 2])
    default_power = float(config.penalty_maturity_power)
    # The gate is on sample size, not on the knot count.  In a *penalised* spline
    # the effective degrees of freedom are set by lambda, and choosing lambda is
    # exactly what this routine does, so refusing to cross-validate whenever the
    # basis is generous relative to the sample would skip the selection precisely
    # when it matters most and fall back to an arbitrary median weight.
    if folds < 2 or len(instruments) < max(2 * folds, config.min_knots + 2):
        return default, default_power, {}, (
            "too few instruments for cross-validation; the median roughness weight "
            f"lambda={default:g} was used"
        )
    blocks = maturity_blocks(instruments, folds)
    fold_sets: list[tuple[CalibrationSet, CalibrationSet]] = []
    for block in blocks:
        if not block:
            continue
        hold = set(block)
        train = [inst for k, inst in enumerate(instruments) if k not in hold]
        test = [instruments[k] for k in block]
        if len(train) < max(3, knots.size // 2) or not test:
            continue
        fold_sets.append((CalibrationSet(train), CalibrationSet(test)))
    if not fold_sets:
        return default, default_power, {}, "cross-validation produced no usable folds"

    scores: dict[tuple[float, float], float] = {}
    standard_errors: dict[tuple[float, float], float] = {}
    for power in config.penalty_power_grid:
        for lam in config.lambda_grid:
            errors: list[float] = []
            for train_set, test_set in fold_sets:
                fit = fit_advanced(
                    train_set, config, lam=lam, knots=knots, robust=True, power=power
                )
                r = test_set.residuals_bp(fit.curve)
                w = test_set.weights
                if w.sum() <= 0 or not np.all(np.isfinite(r)):
                    continue
                errors.append(float(np.sum(w * r**2) / np.sum(w)))
            if errors:
                key = (float(lam), float(power))
                scores[key] = float(np.sqrt(np.mean(errors)))
                standard_errors[key] = float(
                    np.std(np.sqrt(errors), ddof=1) / np.sqrt(len(errors))
                    if len(errors) > 1
                    else 0.0
                )
    if not scores:
        return default, default_power, {}, "cross-validation produced no usable folds"
    best = min(scores, key=lambda k: (scores[k], k[0], k[1]))
    chosen = best
    if config.one_se_rule:
        threshold = scores[best] + standard_errors.get(best, 0.0)
        admissible = [key for key, value in scores.items() if value <= threshold]
        chosen = max(admissible) if admissible else best
    note = ""
    if chosen != best:
        note = (
            f"one-standard-error rule: lambda={chosen[0]:g}, power={chosen[1]:g} "
            f"(CV {scores[chosen]:.3f}bp) chosen over the CV minimum lambda="
            f"{best[0]:g}, power={best[1]:g} (CV {scores[best]:.3f}bp)"
        )
    reported = {f"lambda={k[0]:g},power={k[1]:g}": v for k, v in scores.items()}
    return chosen[0], chosen[1], reported, note


def _preserve_pillars(
    instruments: list[Instrument],
    flagged: np.ndarray,
    z: np.ndarray,
    neighbourhood: float = 0.25,
) -> np.ndarray:
    """Stop the screen from deleting a maturity the curve has no other view on.

    A lone off-market bond *should* be removed -- the neighbouring instruments
    still pin the curve there.  What must never happen is that every quote in a
    maturity neighbourhood disappears at once, because then the curve is
    extrapolating through a hole with nothing to hold it.  The least extreme
    observation of such a neighbourhood is reinstated; the robust weighting
    inside the estimator still discounts it.
    """
    if flagged.size == 0:
        return flagged
    dropped = set(int(i) for i in flagged)
    maturities = np.array([i.maturity_years for i in instruments], dtype=float)
    for idx in sorted(flagged.tolist()):
        if idx not in dropped:
            continue
        centre = maturities[idx]
        window = max(neighbourhood * centre, 0.25)
        neighbours = [
            k
            for k in range(len(instruments))
            if k not in dropped and abs(maturities[k] - centre) <= window
        ]
        if neighbours:
            continue
        group = [
            k
            for k in range(len(instruments))
            if abs(maturities[k] - centre) <= window
        ]
        best = min(group, key=lambda m: (z[m], instruments[m].obs_id))
        dropped.discard(best)
    return np.array(sorted(dropped), dtype=int)


def _shorth(values: np.ndarray) -> float:
    """Location of the shortest interval covering half the sample.

    A high-breakdown location estimator.  Unlike the median it does not drift
    towards a contaminated minority: with residuals ``{-170, -16, 0, 0}`` the
    median is ``-8`` -- which makes the two *good* quotes look as deviant as the
    bad ones -- while the shorth returns ``0``.
    """
    ordered = np.sort(np.asarray(values, dtype=float))
    n = ordered.size
    if n == 0:
        return 0.0
    half = max(2, int(np.ceil(n / 2.0)))
    if half >= n:
        return float(np.median(ordered))
    widths = ordered[half - 1 :] - ordered[: n - half + 1]
    start = int(np.argmin(widths))
    return float(np.median(ordered[start : start + half]))


def local_residuals(
    instruments: list[Instrument], residuals: np.ndarray, neighbours: int = 8
) -> np.ndarray:
    """Residuals measured against their own local consensus.

    The screen must target *idiosyncratic* quote errors, not curve-shape error.
    Any curve carries smoothing bias, and that bias is shared by every quote on
    the same pillar: three 7Y swaps that agree with each other to a third of a
    basis point are not three bad prints, however far the fitted curve sits from
    them.  So the reference is

    * the **shorth** of the residuals on the same pillar (same maturity and
      instrument type) whenever the pillar carries at least three quotes -- a
      high-breakdown consensus that a contaminated minority cannot move;
    * otherwise the median residual of the nearest maturities, which is the only
      comparison available for an instrument quoted once.

    What is left is the disagreement between an observation and its own peers,
    which is what a bad print actually looks like.
    """
    residuals = np.asarray(residuals, dtype=float)
    n = residuals.size
    if n < 3:
        return residuals - float(np.median(residuals))
    maturities = np.array([i.maturity_years for i in instruments], dtype=float)
    pillars: dict[tuple[str, float], list[int]] = {}
    for k, inst in enumerate(instruments):
        pillars.setdefault((inst.instrument_type, round(inst.maturity_years, 9)), []).append(k)
    out = np.empty(n, dtype=float)
    for i in range(n):
        key = (instruments[i].instrument_type, round(maturities[i], 9))
        members = pillars[key]
        if len(members) >= 3:
            out[i] = residuals[i] - _shorth(residuals[members])
            continue
        others = np.array([k for k in range(n) if k != i])
        order = np.argsort(np.abs(maturities[others] - maturities[i]), kind="stable")
        take = others[order[: min(neighbours, others.size)]]
        out[i] = residuals[i] - float(np.median(residuals[take]))
    return out


def screen_outliers(
    instruments: list[Instrument],
    config: FitConfig | None = None,
) -> tuple[dict[str, str], AdvancedFit]:
    """Flag gross outliers against a cross-validated, robustly fitted reference.

    The reference curve is itself robust, so contaminated quotes barely move it;
    the screen simply promotes "the robust estimator gave this observation zero
    weight" into an explicit, audited exclusion.  At most
    ``max_exclusion_fraction`` of the sample can be removed, which stops a badly
    specified scenario from deleting the whole data set.
    """
    config = config or FitConfig()
    fit = fit_advanced(
        instruments,
        config,
        lam=config.screening_lambda,
        power=config.screening_power,
        robust=True,
    )
    calset = CalibrationSet(instruments)
    r = calset.residuals_bp(fit.curve)
    local = local_residuals(instruments, r, config.screening_neighbours)
    standardised = local * np.sqrt(calset.weights)
    scale = _robust_scale(standardised, config)
    z = np.abs(standardised) / scale
    flagged = np.flatnonzero(
        (z > config.tukey_c) & (np.abs(local) >= config.min_outlier_bp)
    )
    budget = int(np.floor(config.max_exclusion_fraction * len(instruments)))
    if flagged.size > budget:
        flagged = flagged[np.argsort(-z[flagged], kind="stable")][:budget]
    flagged = _preserve_pillars(instruments, flagged, z)
    reasons = {
        instruments[int(i)].obs_id: (
            f"robust outlier: repricing residual {r[int(i)]:+.2f}bp, "
            f"{local[int(i)]:+.2f}bp against its maturity neighbours, is "
            f"{z[int(i)]:.1f} robust sigma from the screening reference"
        )
        for i in sorted(flagged.tolist())
    }
    return reasons, fit
