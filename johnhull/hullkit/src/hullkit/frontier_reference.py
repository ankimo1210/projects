"""CPU-quick, API-backed reference payloads for beyond-Hull volumes 21--26.

The committed teaching artifacts are deliberately small, but their numbers
must still come from the public :mod:`hullkit` APIs.  This module is the bridge:
each builder returns a dictionary of NumPy arrays and a scalar metric mapping
that the top-level ``johnhull`` artifact writer can serialize as NPZ + JSON.

Random inputs use fixed seeds.  Wall-clock timings in volume 21 are genuine
measurements and are consequently the only intentionally non-deterministic
fields; model values and diagnostics remain reproducible.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from time import perf_counter_ns
from zoneinfo import ZoneInfo

import numpy as np
from scipy.optimize import brentq

from . import (
    amm,
    carbon,
    hull_white,
    inflation,
    jarrow_yildirim,
    jgbi,
    liquidation,
    perpetuals,
    ppa,
    rates,
    rfr,
    rfr_options,
    sabr_normal,
    spx_vix,
    weather,
    zero_dte,
)

type Scalar = float | int | str | bool
type ArrayMap = dict[str, np.ndarray]


@dataclass(frozen=True)
class FrontierReference:
    """Serialization-ready payload for one beyond-Hull volume."""

    volume: int
    seed: int
    arrays: ArrayMap
    metrics: dict[str, Scalar]

    def __post_init__(self) -> None:
        if self.volume not in range(21, 27):
            raise ValueError("frontier reference volume must lie in [21, 26]")
        if not self.arrays or not self.metrics:
            raise ValueError("reference arrays and metrics must be non-empty")
        for name, values in self.arrays.items():
            array = np.asarray(values)
            if not name or array.size == 0 or array.dtype.kind == "O":
                raise ValueError(f"invalid reference array: {name!r}")
            if array.dtype.kind in "fiu" and np.any(~np.isfinite(array)):
                raise ValueError(f"non-finite reference array: {name}")
        for name, value in self.metrics.items():
            if not name or isinstance(value, (dict, list, tuple, np.ndarray)):
                raise ValueError(f"metric must be scalar: {name!r}")
            if isinstance(value, (float, np.floating)) and not np.isfinite(value):
                raise ValueError(f"non-finite reference metric: {name}")


def _timed_ms(work: Callable[[], object], *, repeats: int = 5) -> float:
    """Return a warm-cache median wall-clock measurement in milliseconds."""

    work()
    samples: list[float] = []
    for _ in range(repeats):
        started = perf_counter_ns()
        work()
        samples.append((perf_counter_ns() - started) * 1e-6)
    return max(float(np.median(samples)), np.finfo(float).eps)


def _vix_factors(seed: int, shape: tuple[int, int, int] = (48, 8, 6)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    factors = np.exp(0.28 * rng.standard_normal(shape) - 0.5 * 0.28**2)
    return factors / factors.mean()


def _vix_teacher_outputs(
    samples: np.ndarray,
    factors: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Nested-teacher prices and sampling errors on a common fixture."""

    prices: list[float] = []
    standard_errors: list[float] = []
    for scale, variance, strike_ratio in np.asarray(samples, dtype=float):
        result = spx_vix.nested_vix_teacher(
            variance * factors,
            strike=20.0 * strike_ratio,
            discount_factor=0.995,
            index_scale=100.0 * scale,
        )
        prices.append(result.call_price)
        standard_errors.append(result.standard_error)
    return np.asarray(prices), np.asarray(standard_errors)


def _vix_prices(samples: np.ndarray, factors: np.ndarray) -> np.ndarray:
    """Nested-teacher prices for normalized scale/variance/strike features."""

    return _vix_teacher_outputs(samples, factors)[0]


def _vix_greeks(
    samples: np.ndarray,
    factors: np.ndarray,
    surrogate: spx_vix.PolynomialSurrogate | None = None,
) -> np.ndarray:
    results: list[tuple[float, float]] = []
    for scale, variance, strike_ratio in np.asarray(samples, dtype=float):
        if surrogate is None:

            def pricer(
                value: float,
                variance: float = variance,
                strike_ratio: float = strike_ratio,
            ) -> float:
                return float(
                    spx_vix.nested_vix_teacher(
                        variance * factors,
                        strike=20.0 * strike_ratio,
                        discount_factor=0.995,
                        index_scale=100.0 * value,
                    ).call_price
                )

        else:

            def pricer(
                value: float,
                variance: float = variance,
                strike_ratio: float = strike_ratio,
            ) -> float:
                row = np.asarray([[value, variance, strike_ratio]])
                return float(surrogate.predict(row)[0])

        greek = spx_vix.finite_difference_greeks(pricer, scale, bump=1e-4)
        results.append((greek["delta"], greek["gamma"]))
    return np.asarray(results)


def volume21_reference(*, seed: int = 20260739) -> FrontierReference:
    """Joint SPX/VIX targets plus an actual nested-teacher surrogate benchmark."""

    rng = np.random.default_rng(seed)
    maturity = np.asarray([0.08, 0.25, 0.50, 1.00])
    strike = np.linspace(75.0, 125.0, 17)
    log_moneyness = np.log(strike / 100.0)

    pdv_variance = []
    for index, tenor in enumerate(maturity):
        history = 0.008 * np.sin(np.arange(40 + 12 * index) / 5.0) - 0.002 * tenor
        pdv_variance.append(spx_vix.four_factor_pdv(history).variance[-1])
    pdv_variance_array = np.asarray(pdv_variance)
    afv_variance = spx_vix.affine_forward_variance(
        maturity,
        0.030,
        [0.012, 0.008],
        [0.8, 4.0],
    )
    rough_kernel = spx_vix.rough_heston_fractional_kernel(maturity, 0.12)
    rough_variance = 0.032 + 0.008 * rough_kernel / rough_kernel.max()
    ou_state = np.linspace(-0.7, 0.6, maturity.size)
    quintic_variance = spx_vix.quintic_ou_variance(
        ou_state,
        [0.18, -0.025, 0.012, 0.0, -0.002, 0.001],
    )

    def smile(term_variance: np.ndarray, skew: float) -> np.ndarray:
        level = np.sqrt(term_variance)[:, None]
        return level * (1.0 + skew * log_moneyness + 0.55 * log_moneyness**2)

    spx_pdv = smile(pdv_variance_array, -0.30)
    spx_afv = smile(afv_variance, -0.23)
    spx_rough = smile(rough_variance, -0.34)
    spx_quintic = smile(quintic_variance, -0.18)
    spx_target = 0.55 * spx_pdv + 0.45 * spx_afv
    target_variance = 0.55 * pdv_variance_array + 0.45 * afv_variance

    nested_factors = _vix_factors(seed + 1, (96, 12, 8))

    def vix_targets(variance_curve: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        futures: list[float] = []
        options: list[float] = []
        average_variance: list[float] = []
        for index, variance in enumerate(variance_curve):
            scaled = variance * nested_factors * (1.0 + 0.025 * index)
            result = spx_vix.nested_vix_teacher(
                scaled,
                strike=15.0,
                discount_factor=float(np.exp(-0.02 * maturity[index])),
            )
            futures.append(result.future)
            options.append(result.call_price)
            average_variance.append(float(scaled.mean()))
        return np.asarray(futures), np.asarray(options), np.asarray(average_variance)

    vix_target, vix_option_target, variance_target = vix_targets(target_variance)
    model_curves = {
        "PDV": (spx_pdv, *vix_targets(pdv_variance_array)),
        "AFV": (spx_afv, *vix_targets(afv_variance)),
        "rough-Heston kernel": (spx_rough, *vix_targets(rough_variance)),
        "quintic OU": (spx_quintic, *vix_targets(quintic_variance)),
    }
    market = spx_vix.JointMarketTargets(
        spx_iv=spx_target.ravel(),
        vix_futures=vix_target,
        vix_options=vix_option_target,
        variance_term=variance_target,
    )
    spx_rmse: list[float] = []
    vix_rmse: list[float] = []
    vix_option_rmse: list[float] = []
    variance_rmse: list[float] = []
    joint_loss: list[float] = []
    for surface, vix_future, vix_option, variance_curve in model_curves.values():
        objective = spx_vix.joint_spx_vix_objective(
            spx_vix.JointMarketTargets(
                spx_iv=surface.ravel(),
                vix_futures=vix_future,
                vix_options=vix_option,
                variance_term=variance_curve,
            ),
            market,
            scales={
                "spx_iv": 0.01,
                "vix_futures": 1.0,
                "vix_options": 1.0,
                "variance_term": 0.01,
            },
        )
        spx_rmse.append(float(np.sqrt(np.mean((surface - spx_target) ** 2))))
        vix_rmse.append(float(np.sqrt(np.mean((vix_future - vix_target) ** 2))))
        vix_option_rmse.append(float(np.sqrt(np.mean((vix_option - vix_option_target) ** 2))))
        variance_rmse.append(float(np.sqrt(np.mean((variance_curve - variance_target) ** 2))))
        joint_loss.append(objective.total)

    factors = _vix_factors(seed + 2)
    train = np.column_stack(
        [
            rng.uniform(0.90, 1.10, 96),
            rng.uniform(0.025, 0.065, 96),
            rng.uniform(0.80, 1.20, 96),
        ]
    )
    surrogate = spx_vix.fit_polynomial_surrogate(train, _vix_prices(train, factors), ridge=1e-8)
    in_domain = np.column_stack(
        [
            rng.uniform(0.91, 1.09, 20),
            rng.uniform(0.027, 0.063, 20),
            rng.uniform(0.82, 1.18, 20),
        ]
    )
    ood = np.asarray(
        [
            [0.84, 0.040, 1.00],
            [1.16, 0.040, 1.00],
            [1.00, 0.075, 1.00],
            [1.00, 0.040, 1.30],
        ]
    )
    evaluation = np.vstack([in_domain, ood])
    teacher_price, teacher_standard_error = _vix_teacher_outputs(evaluation, factors)
    surrogate_price = surrogate.predict(evaluation)
    teacher_greeks = _vix_greeks(evaluation, factors)
    surrogate_greeks = _vix_greeks(evaluation, factors, surrogate)
    ood_flag = surrogate.ood(evaluation)
    in_domain_flag = ~ood_flag

    batch_size = np.asarray([16, 128, 1024])
    teacher_ms: list[float] = []
    surrogate_ms: list[float] = []
    for size in batch_size:
        benchmark = np.column_stack(
            [
                rng.uniform(0.92, 1.08, size),
                rng.uniform(0.028, 0.062, size),
                rng.uniform(0.84, 1.16, size),
            ]
        )
        teacher_ms.append(_timed_ms(lambda values=benchmark: _vix_prices(values, factors)))
        surrogate_ms.append(_timed_ms(lambda values=benchmark: surrogate.predict(values)))
    comparison = spx_vix.compare_teacher_surrogate(
        teacher_price,
        surrogate_price,
        teacher_seconds=teacher_ms[-1] * 1e-3,
        surrogate_seconds=surrogate_ms[-1] * 1e-3,
        teacher_greeks=teacher_greeks,
        surrogate_greeks=surrogate_greeks,
    )

    arrays: ArrayMap = {
        "strike": strike,
        "maturity": maturity,
        "spx_target": spx_target,
        "spx_pdv": spx_pdv,
        "spx_afv": spx_afv,
        "spx_rough_heston": spx_rough,
        "spx_quintic_ou": spx_quintic,
        "spx_model_grid": np.stack([curve[0] for curve in model_curves.values()]),
        "vix_maturity": maturity,
        "vix_target": vix_target,
        "vix_pdv": model_curves["PDV"][1],
        "vix_model_grid": np.stack([curve[1] for curve in model_curves.values()]),
        "vix_option_target": vix_option_target,
        "vix_option_pdv": model_curves["PDV"][2],
        "vix_option_model_grid": np.stack([curve[2] for curve in model_curves.values()]),
        "variance_term_target": variance_target,
        "variance_term_pdv": model_curves["PDV"][3],
        "variance_term_model_grid": np.stack([curve[3] for curve in model_curves.values()]),
        "model_names": np.asarray(tuple(model_curves)),
        "spx_rmse": np.asarray(spx_rmse),
        "vix_rmse": np.asarray(vix_rmse),
        "vix_option_rmse": np.asarray(vix_option_rmse),
        "variance_rmse": np.asarray(variance_rmse),
        "joint_loss": np.asarray(joint_loss),
        "surrogate_features": evaluation,
        "teacher_price": teacher_price,
        "teacher_standard_error": teacher_standard_error,
        "surrogate_price": surrogate_price,
        "teacher_delta": teacher_greeks[:, 0],
        "teacher_gamma": teacher_greeks[:, 1],
        "surrogate_delta": surrogate_greeks[:, 0],
        "surrogate_gamma": surrogate_greeks[:, 1],
        "ood_flag": ood_flag,
        "ood_radius": np.linalg.norm(evaluation - np.asarray([1.0, 0.045, 1.0]), axis=1),
        "ood_error": np.abs(teacher_price - surrogate_price),
        "batch_size": batch_size,
        "nested_mc_ms": np.asarray(teacher_ms),
        "surrogate_ms": np.asarray(surrogate_ms),
    }
    metrics: dict[str, Scalar] = {
        "joint_spx_rmse": spx_rmse[0],
        "joint_vix_rmse": vix_rmse[0],
        "joint_vix_option_rmse": vix_option_rmse[0],
        "joint_variance_rmse": variance_rmse[0],
        "surrogate_price_rmse": comparison.price_rmse,
        "surrogate_greek_rmse": float(comparison.greek_rmse or 0.0),
        "surrogate_delta_rmse": float(
            np.sqrt(np.mean((teacher_greeks[:, 0] - surrogate_greeks[:, 0]) ** 2))
        ),
        "surrogate_gamma_rmse": float(
            np.sqrt(np.mean((teacher_greeks[:, 1] - surrogate_greeks[:, 1]) ** 2))
        ),
        "surrogate_speedup_1024": comparison.speedup,
        "timing_method": "perf_counter_ns warm-cache median of 5",
        "timing_nondeterministic": True,
        "ood_count": int(ood_flag.sum()),
        "in_domain_price_rmse": float(
            np.sqrt(np.mean((teacher_price[in_domain_flag] - surrogate_price[in_domain_flag]) ** 2))
        ),
        "ood_price_rmse": float(
            np.sqrt(np.mean((teacher_price[ood_flag] - surrogate_price[ood_flag]) ** 2))
        ),
        "in_domain_greek_rmse": float(
            np.sqrt(
                np.mean((teacher_greeks[in_domain_flag] - surrogate_greeks[in_domain_flag]) ** 2)
            )
        ),
        "ood_greek_rmse": float(
            np.sqrt(np.mean((teacher_greeks[ood_flag] - surrogate_greeks[ood_flag]) ** 2))
        ),
        "teacher": "hullkit.spx_vix.nested_vix_teacher",
    }
    return FrontierReference(21, seed, arrays, metrics)


def volume22_reference(*, seed: int = 20260740) -> FrontierReference:
    """Calendar-aware 0DTE clock and SV+jump teacher diagnostics."""

    zone = ZoneInfo("America/New_York")
    trading_day = date(2026, 7, 2)
    session = zero_dte.TradingSession(holidays=(date(2026, 7, 3),))
    opening, closing = session.bounds(trading_day)
    minute = np.asarray([0, 30, 60, 90, 120, 180, 240, 270, 300, 330, 360, 385, 390])
    timestamps = [opening + timedelta(minutes=int(value)) for value in minute]
    variance_clock = np.asarray(
        [zero_dte.variance_clock_fraction(timestamp, session) for timestamp in timestamps]
    )
    variance_weight = np.gradient(variance_clock, minute / 390.0)
    scheduled = zero_dte.ScheduledJump(
        "FOMC",
        datetime.combine(trading_day, time(14, 0), zone),
        0.00035,
    )
    non_event_intensity = np.asarray(
        [
            zero_dte.intraday_jump_intensity(
                timestamp,
                session,
                open_intensity=2.5,
                midday_intensity=0.6,
                close_intensity=3.2,
            )
            for timestamp in timestamps
        ]
    )
    event_intensity = non_event_intensity + 8.0 * np.exp(-0.5 * ((minute - 270.0) / 25.0) ** 2)

    teacher_price: list[float] = []
    baseline_price: list[float] = []
    delta: list[float] = []
    gamma: list[float] = []
    baseline_delta: list[float] = []
    standard_error: list[float] = []
    scheduled_variances: list[float] = []
    seconds_to_settlement: list[float] = []
    for index, timestamp in enumerate(timestamps):
        remaining_minutes = max(1.0, 390.0 - float(minute[index]))
        steps = max(1, int(np.ceil(remaining_minutes / 45.0)))
        total_years = remaining_minutes / (252.0 * 390.0)
        dt = np.full(steps, total_years / steps)
        expiry = timestamp + timedelta(minutes=remaining_minutes)
        event_variance = zero_dte.scheduled_variance(timestamp, expiry, [scheduled])
        scheduled_variances.append(event_variance)
        seconds_to_settlement.append(
            zero_dte.trading_seconds_to_settlement(timestamp, trading_day, session)
        )
        intensity = np.full(steps, event_intensity[index])
        if event_variance > 0.0:
            intensity[-1] += event_variance / max(float(dt[-1]), 1e-12)
        result = zero_dte.sv_jump_teacher(
            100.0,
            100.0,
            0.02,
            dt,
            intensity,
            v0=0.04,
            kappa=3.0,
            theta=0.04,
            vol_of_vol=0.35,
            rho=-0.55,
            n_paths=3_000,
            seed=seed + index,
        )
        baseline = zero_dte.sv_jump_teacher(
            100.0,
            100.0,
            0.02,
            dt,
            np.full(steps, non_event_intensity[index]),
            v0=0.04,
            kappa=3.0,
            theta=0.04,
            vol_of_vol=0.35,
            rho=-0.55,
            n_paths=3_000,
            seed=seed + index,
        )
        teacher_price.append(result.price)
        baseline_price.append(baseline.price)
        delta.append(result.delta)
        gamma.append(result.gamma)
        baseline_delta.append(baseline.delta)
        standard_error.append(result.standard_error)

    adjacent_minutes = np.asarray([15.0, 60.0, 120.0, 240.0, 390.0])
    maturity_years = adjacent_minutes / (252.0 * 390.0)
    event_variance = np.where(adjacent_minutes >= 270.0, scheduled.variance, 0.0)
    total_variance = 0.04 * maturity_years + event_variance
    implied_volatility = np.sqrt(total_variance / maturity_years)
    expiry_check = zero_dte.total_variance_consistency(
        maturity_years,
        implied_volatility,
    )
    model_total_variance = total_variance * (1.0 + 0.01 * adjacent_minutes / 390.0)
    model_check = zero_dte.total_variance_consistency(
        maturity_years,
        np.sqrt(model_total_variance / maturity_years),
    )

    teacher_price_array = np.asarray(teacher_price)
    baseline_price_array = np.asarray(baseline_price)
    delta_array = np.asarray(delta)
    baseline_delta_array = np.asarray(baseline_delta)
    scheduled_variance_array = np.asarray(scheduled_variances)
    event_mask = scheduled_variance_array > 0.0
    price_split = zero_dte.event_non_event_metrics(
        baseline_price_array,
        teacher_price_array,
        event_mask,
    )
    greek_split = zero_dte.event_non_event_metrics(
        baseline_delta_array,
        delta_array,
        event_mask,
    )
    price_error = np.abs(teacher_price_array - baseline_price_array)
    greek_error = np.abs(delta_array - baseline_delta_array)
    tod_bucket = np.asarray([zero_dte.time_of_day_bucket(value, session) for value in timestamps])
    tod_names = np.asarray(["open", "midday", "close"])
    tod_price_mae = np.asarray(
        [float(np.mean(price_error[tod_bucket == name])) for name in tod_names]
    )
    tod_greek_mae = np.asarray(
        [float(np.mean(greek_error[tod_bucket == name])) for name in tod_names]
    )
    calendar_checks = (
        not session.is_trading_day(date(2026, 7, 3)),
        not session.is_trading_day(date(2026, 7, 4)),
        zero_dte.trading_seconds_to_settlement(opening, trading_day, session)
        == (closing - opening).total_seconds(),
        zero_dte.trading_seconds_to_settlement(closing, trading_day, session) == 0.0,
    )
    arrays: ArrayMap = {
        "minute": minute,
        "variance_weight": variance_weight,
        "variance_clock": variance_clock,
        "event_jump_intensity": event_intensity,
        "non_event_jump_intensity": non_event_intensity,
        "scheduled_variance": scheduled_variance_array,
        "event_mask": event_mask,
        "time_of_day": tod_bucket,
        "seconds_to_settlement": np.asarray(seconds_to_settlement),
        "teacher_price": teacher_price_array,
        "baseline_price": baseline_price_array,
        "teacher_standard_error": np.asarray(standard_error),
        "delta": delta_array,
        "gamma": np.asarray(gamma),
        "baseline_delta": baseline_delta_array,
        "adjacent_expiry_minutes": adjacent_minutes,
        "total_variance": expiry_check.total_variance,
        "model_total_variance": model_check.total_variance,
        "forward_variance": expiry_check.forward_variance,
        "tod_names": tod_names,
        "price_mae": tod_price_mae,
        "greek_mae": tod_greek_mae,
        "event_split_names": np.asarray(["event", "non-event"]),
        "event_price_rmse": np.asarray([price_split.event_rmse, price_split.non_event_rmse]),
        "event_greek_rmse": np.asarray([greek_split.event_rmse, greek_split.non_event_rmse]),
    }
    metrics: dict[str, Scalar] = {
        "calendar_violations": int(sum(not value for value in calendar_checks)),
        "adjacent_expiry_violations": len(model_check.violating_intervals),
        "event_price_mae": float(np.mean(price_error[event_mask])),
        "event_greek_mae": float(np.mean(greek_error[event_mask])),
        "event_price_rmse": price_split.event_rmse,
        "non_event_price_rmse": price_split.non_event_rmse,
        "event_greek_rmse": greek_split.event_rmse,
        "non_event_greek_rmse": greek_split.non_event_rmse,
        "event_count": price_split.event_count,
        "non_event_count": price_split.non_event_count,
        "event_teacher_standard_error": float(np.mean(np.asarray(standard_error)[event_mask])),
        "session_seconds": float((closing - opening).total_seconds()),
        "timezone": session.timezone,
    }
    return FrontierReference(22, seed, arrays, metrics)


def _sabr_hedge_paths(
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """One-step states repriced by MC, independently of Hagan hedge deltas."""

    rng = np.random.default_rng(seed)
    forward = 0.030
    strike = 0.030
    expiry = 2.0
    alpha = 0.080
    beta = 0.5
    rho = -0.50
    nu = 0.60
    shift = 0.030
    dt = 1.0 / 252.0
    sticky = sabr_normal.sticky_strike_delta(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=shift,
    )
    bartlett = sabr_normal.bartlett_delta(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=shift,
    )
    teacher_seed = seed + 1
    initial = sabr_normal.shifted_sabr_mc_price(
        forward,
        strike,
        expiry,
        alpha,
        beta,
        rho,
        nu,
        shift=shift,
        n_steps=16,
        n_paths=3_000,
        seed=teacher_seed,
    )
    normals = rng.standard_normal((96, 2))
    forward_change = alpha * (forward + shift) ** beta * np.sqrt(dt) * normals[:, 0]
    next_forward = forward + forward_change
    correlated = rho * normals[:, 0] + np.sqrt(1.0 - rho**2) * normals[:, 1]
    next_alpha = alpha * np.exp(-0.5 * nu**2 * dt + nu * np.sqrt(dt) * correlated)
    next_values = [
        sabr_normal.shifted_sabr_mc_price(
            float(next_f),
            strike,
            expiry - dt,
            float(next_a),
            beta,
            rho,
            nu,
            shift=shift,
            n_steps=16,
            n_paths=3_000,
            # Common random numbers isolate the state change from inner-MC noise.
            seed=teacher_seed,
        )
        for next_f, next_a in zip(next_forward, next_alpha, strict=True)
    ]
    option_pnl = np.asarray([value.price - initial.price for value in next_values])
    standard_error = np.asarray([value.standard_error for value in next_values])
    return option_pnl, forward_change, standard_error, sticky, bartlett


def volume23_reference(*, seed: int = 20260741) -> FrontierReference:
    """Exact RFR layers and non-zero-nu SABR teacher/hedge diagnostics."""

    calendar = rfr.BusinessCalendar()
    start = date(2026, 1, 2)
    end = date(2026, 4, 2)
    advance_start = date(2025, 10, 2)
    fixing_dates = calendar.business_dates(advance_start, end)
    fixings = {
        fixing: 0.040 + 0.0025 * np.sin(index / 8.0) + 0.001 * (index >= 32)
        for index, fixing in enumerate(fixing_dates)
    }
    compounded = rfr.compounded_rfr(start, end, fixings, calendar=calendar)
    convention_map = {
        "in-arrears": rfr.RFRConvention(),
        "lookback 2bd": rfr.RFRConvention(lookback_business_days=2),
        "observation shift 2bd": rfr.RFRConvention(
            lookback_business_days=2,
            observation_shift=True,
        ),
        "lockout 2bd": rfr.RFRConvention(lockout_business_days=2),
    }
    convention_results = {
        name: rfr.compounded_rfr(
            start,
            end,
            fixings,
            calendar=calendar,
            convention=convention,
        )
        for name, convention in convention_map.items()
    }
    convention_rates = np.asarray(
        [result.annualized_rate for result in convention_results.values()]
    )
    convention_accumulation = np.asarray(
        [result.accumulation_factor for result in convention_results.values()]
    )
    convention_day_count = np.stack(
        [
            np.asarray([row.day_count for row in result.observations])
            for result in convention_results.values()
        ]
    )
    convention_observation_ordinal = np.stack(
        [
            np.asarray([(row.observation_date - start).days for row in result.observations])
            for result in convention_results.values()
        ]
    )
    coupon_cashflow = np.asarray(
        [
            rfr.rfr_coupon(1_000_000.0, start, end, fixings, determination="in_arrears"),
            rfr.rfr_coupon(
                1_000_000.0,
                start,
                end,
                fixings,
                determination="in_advance",
                advance_observation_period=(advance_start, start),
            ),
        ]
    )
    day_counts = np.asarray([row.day_count for row in compounded.observations])
    daily_rate = np.asarray([row.fixing for row in compounded.observations])
    day = np.cumsum(day_counts)
    factors = 1.0 + daily_rate * day_counts / 360.0
    discrete_accrual = np.cumprod(factors) - 1.0
    continuous_accrual = np.expm1(np.cumsum(daily_rate * day_counts / 360.0))
    continuous_rate = rfr.continuous_compounding_approximation(compounded.observations, 360)
    current_fixing_dates = calendar.business_dates(start, end)
    zero_compounded = rfr.compounded_rfr(
        start,
        end,
        dict.fromkeys(current_fixing_dates, 0.0),
        calendar=calendar,
    )

    valuation = start
    pillar_dates = (
        date(2026, 4, 2),
        date(2026, 7, 2),
        date(2027, 1, 4),
        date(2028, 1, 3),
        date(2031, 1, 2),
        date(2036, 1, 2),
    )
    pillar_times = np.asarray([(value - valuation).days / 365.0 for value in pillar_dates])
    discount_factors = tuple(np.exp(-(0.035 + 0.002 * np.exp(-pillar_times)) * pillar_times))
    curve = rfr.RfrCurve("SOFR", valuation, pillar_dates, discount_factors, "USD")
    collateral_discount_factors = tuple(
        np.exp(-(0.032 + 0.0015 * np.exp(-pillar_times)) * pillar_times)
    )
    collateral_curve = rfr.RfrCurve(
        "USD collateral OIS",
        valuation,
        pillar_dates,
        collateral_discount_factors,
        "USD",
    )
    tona_discount_factors = tuple(np.exp(-(0.008 + 0.001 * np.exp(-pillar_times)) * pillar_times))
    tona_curve = rfr.RfrCurve("TONA", valuation, pillar_dates, tona_discount_factors, "JPY")
    curves = (curve, collateral_curve, tona_curve)
    curve_discount_grid = np.asarray(
        [[item.discount(value) for value in pillar_dates] for item in curves]
    )
    curve_forward_grid = np.asarray(
        [[item.simple_forward(valuation, value) for value in pillar_dates] for item in curves]
    )
    forward_rates = np.asarray([curve.simple_forward(valuation, value) for value in pillar_dates])
    basis_spread_bp = 1e4 * np.asarray(
        [rfr.curve_basis_spread(curve, tona_curve, valuation, value) for value in pillar_dates]
    )
    covariance = -2.0e-6 * pillar_times
    futures = [
        rfr.futures_forward_from_covariance(rate, cov, curve.discount(value))
        for rate, cov, value in zip(forward_rates, covariance, pillar_dates, strict=True)
    ]
    futures_forward_bp = 1e4 * np.asarray([adjustment for _, adjustment in futures])

    coupon_start, coupon_end = pillar_dates[0], pillar_dates[2]
    coupon_year_fraction = (coupon_end - coupon_start).days / 360.0
    multi_curve = rfr.MultiCurveScenario(curve, collateral_curve, "USD")
    single_curve = rfr.MultiCurveScenario(curve, curve, "USD")
    forecast_coupon = 100.0 * curve.simple_forward(coupon_start, coupon_end) * coupon_year_fraction
    multi_curve_coupon_pv = rfr.collateralized_present_value(
        [forecast_coupon],
        [coupon_end],
        multi_curve,
    )
    single_curve_coupon_pv = rfr.collateralized_present_value(
        [forecast_coupon],
        [coupon_end],
        single_curve,
    )
    collateral_shift_bp = np.asarray([-50.0, -25.0, 0.0, 25.0, 50.0])
    collateral_pv: list[float] = []
    for shift_bp in collateral_shift_bp:
        shifted_discounts = tuple(
            np.exp(
                -(-np.log(np.asarray(collateral_discount_factors)) / pillar_times + shift_bp * 1e-4)
                * pillar_times
            )
        )
        shifted_curve = rfr.RfrCurve(
            f"USD collateral {shift_bp:+.0f}bp",
            valuation,
            pillar_dates,
            shifted_discounts,
            "USD",
        )
        scenario = rfr.MultiCurveScenario(curve, shifted_curve, "USD")
        collateral_pv.append(rfr.collateralized_present_value([100.0], [coupon_end], scenario))
    collateral_currency_pv = np.asarray(
        [
            rfr.collateralized_present_value(
                [100.0],
                [coupon_end],
                rfr.MultiCurveScenario(curve, collateral_curve, "USD"),
            ),
            rfr.collateralized_present_value(
                [100.0],
                [coupon_end],
                rfr.MultiCurveScenario(tona_curve, tona_curve, "JPY"),
            ),
        ]
    )

    policy_dates = (
        date(2026, 1, 20),
        date(2026, 1, 29),
        date(2026, 2, 2),
        date(2026, 3, 19),
        date(2026, 4, 2),
    )
    policy_rate_path = np.stack(
        [
            rfr.policy_jump_path(
                policy_dates,
                0.040,
                [
                    rfr.PolicyJump(date(2026, 1, 29), -0.0025, "FOMC"),
                    rfr.PolicyJump(date(2026, 3, 19), 0.0050, "FOMC"),
                ],
            ),
            rfr.policy_jump_path(
                policy_dates,
                0.025,
                [
                    rfr.PolicyJump(date(2026, 1, 29), -0.0050, "ECB"),
                    rfr.PolicyJump(date(2026, 3, 19), 0.0025, "ECB"),
                ],
            ),
        ]
    )

    strike = np.linspace(-0.005, 0.065, 9)
    bachelier_price = np.asarray(
        [rfr_options.bachelier_price(0.030, value, 0.015, 2.0) for value in strike]
    )
    quadrature_price = np.asarray(
        [rfr_options.gaussian_quadrature_price(0.030, value, 0.015, 2.0) for value in strike]
    )
    normal_iv = np.asarray(
        [
            sabr_normal.normal_sabr_implied_vol(0.030, value, 2.0, 0.015, -0.25, 0.55)
            for value in strike
        ]
    )
    shifted_sabr_iv = np.asarray(
        [
            sabr_normal.shifted_sabr_implied_vol(
                0.030,
                value,
                2.0,
                0.080,
                0.5,
                -0.35,
                0.60,
                shift=0.020,
            )
            for value in strike
        ]
    )
    free_boundary_iv = np.asarray(
        [
            sabr_normal.free_boundary_sabr_implied_vol(
                0.030,
                value,
                2.0,
                0.080,
                0.5,
                -0.35,
                0.60,
                lower_boundary=-0.030,
            )
            for value in strike
        ]
    )
    shifted_sabr_price = np.asarray(
        [
            sabr_normal.shifted_sabr_price(
                0.030,
                value,
                2.0,
                0.080,
                0.5,
                -0.35,
                0.60,
                shift=0.020,
            )
            for value in strike
        ]
    )
    free_boundary_sabr_price = np.asarray(
        [
            sabr_normal.free_boundary_sabr_price(
                0.030,
                value,
                2.0,
                0.080,
                0.5,
                -0.35,
                0.60,
                lower_boundary=-0.030,
            )
            for value in strike
        ]
    )
    shifted_teacher = [
        sabr_normal.shifted_sabr_mc_price(
            0.030,
            float(value),
            2.0,
            0.080,
            0.5,
            -0.35,
            0.60,
            shift=0.020,
            n_steps=32,
            n_paths=8_000,
            seed=seed + 50 + index,
        )
        for index, value in enumerate(strike)
    ]
    shifted_teacher_price = np.asarray([value.price for value in shifted_teacher])
    shifted_teacher_se = np.asarray([value.standard_error for value in shifted_teacher])

    teacher_maturity = np.asarray([1.0, 5.0, 10.0])
    volatility_levels = np.asarray([0.010, 0.020, 0.040])
    hagan_price = np.empty((teacher_maturity.size, strike.size))
    teacher_price = np.empty_like(hagan_price)
    teacher_se = np.empty_like(hagan_price)
    for row, (expiry, alpha) in enumerate(zip(teacher_maturity, volatility_levels, strict=True)):
        for column, strike_value in enumerate(strike):
            hagan_price[row, column] = sabr_normal.normal_sabr_price(
                0.030,
                float(strike_value),
                float(expiry),
                float(alpha),
                -0.30,
                0.65,
            )
            teacher = sabr_normal.normal_sabr_conditional_mc_price(
                0.030,
                float(strike_value),
                float(expiry),
                float(alpha),
                -0.30,
                0.65,
                n_steps=48,
                n_paths=8_000,
                seed=seed + 100 * row + column,
            )
            teacher_price[row, column] = teacher.price
            teacher_se[row, column] = teacher.standard_error
    diagnostics = sabr_normal.hagan_error_diagnostics(
        hagan_price,
        teacher_price,
        strike,
        teacher_maturity,
        volatility_levels,
    )
    arbitrage = sabr_normal.call_grid_arbitrage_diagnostics(
        strike,
        teacher_maturity,
        hagan_price,
        tolerance=1e-10,
    )

    option_pnl, forward_change, hedge_teacher_se, sticky_delta, bartlett_delta = _sabr_hedge_paths(
        seed + 500
    )
    hedge = sabr_normal.compare_delta_hedges(
        option_pnl,
        forward_change,
        sticky_delta,
        bartlett_delta,
    )
    arrays: ArrayMap = {
        "day": day,
        "daily_rate": daily_rate,
        "day_count": day_counts,
        "discrete_accrual": discrete_accrual,
        "continuous_accrual": continuous_accrual,
        "convention_names": np.asarray(tuple(convention_map)),
        "convention_rate": convention_rates,
        "convention_accumulation": convention_accumulation,
        "convention_day_count": convention_day_count,
        "convention_observation_ordinal": convention_observation_ordinal,
        "coupon_names": np.asarray(["in-arrears", "in-advance"]),
        "coupon_cashflow": coupon_cashflow,
        "maturity": pillar_times,
        "discount_factor": np.asarray(discount_factors),
        "forward_rate": forward_rates,
        "futures_forward_bp": futures_forward_bp,
        "curve_names": np.asarray([item.name for item in curves]),
        "curve_discount_factor": curve_discount_grid,
        "curve_forward_rate": curve_forward_grid,
        "basis_spread_bp": basis_spread_bp,
        "policy_date_ordinal": np.asarray([(value - valuation).days for value in policy_dates]),
        "policy_scenario_names": np.asarray(["SOFR/FOMC", "EURSTR/ECB"]),
        "policy_rate_path": policy_rate_path,
        "policy_jump_bp": 1e4 * (policy_rate_path[0] - policy_rate_path[0, 0]),
        "collateral_shift_bp": collateral_shift_bp,
        "collateral_pv": np.asarray(collateral_pv),
        "collateral_currency_names": np.asarray(["USD", "JPY"]),
        "collateral_currency_pv": collateral_currency_pv,
        "strike": strike,
        "bachelier_price": bachelier_price,
        "quadrature_price": quadrature_price,
        "normal_iv": normal_iv,
        "shifted_sabr_iv": shifted_sabr_iv,
        "free_boundary_sabr_iv": free_boundary_iv,
        "shifted_sabr_price": shifted_sabr_price,
        "free_boundary_sabr_price": free_boundary_sabr_price,
        "shifted_teacher_price": shifted_teacher_price,
        "shifted_teacher_standard_error": shifted_teacher_se,
        "teacher_maturity": teacher_maturity,
        "hagan_price": hagan_price,
        "teacher_price": teacher_price,
        "teacher_standard_error": teacher_se,
        "hagan_error_bp": 1e4 * np.max(np.abs(hagan_price - teacher_price), axis=0),
        "hedge_names": np.asarray(["sticky strike", "Bartlett"]),
        "hedge_rmse": np.asarray([hedge.sticky_rmse, hedge.bartlett_rmse]),
        "option_price_change": option_pnl,
        "hedge_teacher_standard_error": hedge_teacher_se,
        "forward_change": forward_change,
        "sticky_hedge_error": hedge.sticky_error,
        "bartlett_hedge_error": hedge.bartlett_error,
    }
    metrics: dict[str, Scalar] = {
        "daily_compounding_handcheck_error": float(
            abs(compounded.accumulation_factor - np.prod(factors))
        ),
        "zero_rate_handcheck_error": abs(zero_compounded.annualized_rate),
        "continuous_limit_error": float(abs(compounded.annualized_rate - continuous_rate)),
        "lookback_rate": float(convention_rates[1]),
        "observation_shift_rate": float(convention_rates[2]),
        "lockout_rate": float(convention_rates[3]),
        "in_arrears_coupon": float(coupon_cashflow[0]),
        "in_advance_coupon": float(coupon_cashflow[1]),
        "sofr_tona_basis_bp_1y": float(basis_spread_bp[2]),
        "single_curve_coupon_pv": single_curve_coupon_pv,
        "multi_curve_coupon_pv": multi_curve_coupon_pv,
        "quadrature_handcheck_error": float(np.max(np.abs(bachelier_price - quadrature_price))),
        "hagan_worst_error_bp": diagnostics.overall_max_abs * 1e4,
        "hagan_long_maturity_rmse_bp": diagnostics.long_maturity_rmse * 1e4,
        "hagan_high_vol_rmse_bp": diagnostics.high_vol_rmse * 1e4,
        "hagan_wing_rmse_bp": diagnostics.wing_rmse * 1e4,
        "hagan_static_arbitrage_pass": bool(
            arbitrage.nonnegative
            and arbitrage.strike_monotone
            and arbitrage.strike_convex
            and arbitrage.calendar_monotone
        ),
        "hagan_nonnegative_pass": arbitrage.nonnegative,
        "hagan_strike_monotone_pass": arbitrage.strike_monotone,
        "hagan_strike_convex_pass": arbitrage.strike_convex,
        "hagan_calendar_monotone_pass": arbitrage.calendar_monotone,
        "sabr_teacher_nu": 0.65,
        "sabr_teacher": "conditional normal-SABR MC; shifted-SABR full-truncation MC",
        "hedge_teacher": "shifted-SABR full-truncation MC with common random numbers",
        "sticky_hedge_rmse": hedge.sticky_rmse,
        "bartlett_hedge_rmse": hedge.bartlett_rmse,
    }
    return FrontierReference(23, seed, arrays, metrics)


def volume24_reference(*, seed: int = 20260742) -> FrontierReference:
    """Unified perpetual, liquidation-waterfall, and AMM stress ledger."""

    rng = np.random.default_rng(seed)
    step = np.arange(8)
    elapsed_hours = 8.0 * step
    contract_names = np.asarray(["linear", "inverse", "quanto"])
    settlement_price = np.asarray([80.0, 100.0, 120.0])
    contract_pnl_long = np.asarray(
        [
            [
                perpetuals.position_pnl(
                    contract,
                    100.0,
                    exit_price,
                    2.0,
                    settlement_fx=0.5,
                )
                for exit_price in settlement_price
            ]
            for contract in contract_names
        ]
    )
    contract_pnl_short = np.asarray(
        [
            [
                perpetuals.position_pnl(
                    contract,
                    100.0,
                    exit_price,
                    2.0,
                    side="short",
                    settlement_fx=0.5,
                )
                for exit_price in settlement_price
            ]
            for contract in contract_names
        ]
    )
    index_price = np.asarray([100.0, 99.0, 97.0, 94.0, 90.0, 86.0, 82.0, 78.0])
    funding_policy = perpetuals.FundingPolicy(absolute_cap=0.005, interval_hours=8.0)
    basis_path = perpetuals.simulate_basis_feedback(
        index_price,
        102.0,
        net_long_fraction=0.35,
        basis_reversion=0.25,
        funding_feedback=0.60,
        policy=funding_policy,
    )
    mark_price = basis_path.mark_prices
    last_price = mark_price * (1.0 + 0.0015 * rng.standard_normal(step.size))
    account = liquidation.MarginAccount(
        collateral=10.0,
        quantity=1.0,
        entry_price=100.0,
        initial_margin_rate=0.10,
        maintenance_margin_rate=0.05,
        liquidation_fee_rate=0.01,
    )

    funding_long: list[float] = []
    funding_short: list[float] = []
    funding_venue: list[float] = []
    funding_error: list[float] = []
    cumulative_funding: list[float] = []
    running_funding = 0.0
    equity: list[float] = []
    oracle_age: list[float] = []
    oracle_loss: list[float] = []
    oracle_observed_dislocation: list[float] = []
    oracle_latent_dislocation: list[float] = []
    oracle_stale: list[bool] = []
    oracle_dislocated: list[bool] = []
    shocked_mark: list[float] = []
    latent_index: list[float] = []
    settled_intervals: list[int] = []
    previous_completed = 0
    for index, (index_value, mark_value, last_value, rate) in enumerate(
        zip(index_price, mark_price, last_price, basis_path.funding_rates, strict=True)
    ):
        notional = perpetuals.position_notional("linear", mark_value)
        completed = perpetuals.completed_funding_intervals(
            elapsed_hours[index],
            policy=funding_policy,
        )
        interval_count = completed - previous_completed
        previous_completed = completed
        settled_intervals.append(completed)
        funding = perpetuals.matched_funding_ledger(
            notional,
            notional,
            rate,
            intervals=interval_count,
        )
        funding_long.append(funding.long_cashflow)
        funding_short.append(funding.short_cashflow)
        funding_venue.append(funding.venue_residual)
        funding_error.append(funding.conservation_error)
        running_funding += funding.long_cashflow
        cumulative_funding.append(running_funding)
        equity.append(liquidation.account_equity(account, mark_value, running_funding))
        snapshot = perpetuals.MarketSnapshot(
            index_value,
            mark_value,
            last_value,
            timestamp=float(index * 5),
            oracle_timestamp=0.0,
        )
        oracle_age.append(snapshot.oracle_age)
        risk = liquidation.assess_oracle_risk(
            snapshot,
            max_age=10.0,
            max_mark_dislocation=0.02,
        )
        oracle_stale.append(risk.stale)
        oracle_dislocated.append(risk.dislocated)
        shock = liquidation.oracle_shock(
            snapshot,
            latency_return=-0.002 * index,
            mark_manipulation=-0.001 * index,
        )
        oracle_loss.append(abs(shock.latent_index - shock.shocked_mark))
        oracle_observed_dislocation.append(shock.observed_dislocation)
        oracle_latent_dislocation.append(shock.latent_dislocation)
        shocked_mark.append(shock.shocked_mark)
        latent_index.append(shock.latent_index)

    liquidation_methods = ("forced_sale", "auction")
    execution_prices = []
    waterfalls = []
    for method in liquidation_methods:
        close_price = liquidation.execution_price(
            index_price[-1],
            account.quantity,
            method=method,
            impact_bps=250.0,
            auction_improvement=0.40,
        )
        execution_prices.append(close_price)
        waterfalls.append(
            liquidation.liquidation_waterfall(
                account,
                close_price,
                insurance_fund=4.0,
                auction_recovery=1.0 if method == "auction" else 0.0,
                adl_capacity=3.0,
                social_loss_capacity=50.0,
                funding_cashflow=cumulative_funding[-1],
            )
        )
    waterfall = waterfalls[1]
    insurance_fund = np.full(step.size, waterfall.insurance_fund_before)
    insurance_fund[-1] = waterfall.insurance_fund_after
    adl_used = np.zeros(step.size)
    adl_used[-1] = waterfall.adl_used
    socialized_loss = np.zeros(step.size)
    socialized_loss[-1] = waterfall.socialized_loss
    uncovered_loss = np.zeros(step.size)
    uncovered_loss[-1] = waterfall.uncovered_loss
    liquidation_conservation = np.zeros(step.size)
    liquidation_conservation[-1] = waterfall.conservation_error
    insurance_identity = (
        waterfall.insurance_fund_after
        - waterfall.insurance_fund_before
        - waterfall.liquidation_fee
        + waterfall.insurance_used
    )

    reserve_x, reserve_y = 100.0, 10_000.0
    rebalanced_value: list[float] = []
    lp_value: list[float] = []
    lvr: list[float] = []
    fee_income: list[float] = []
    dynamic_fee_income: list[float] = []
    amm_identity: list[float] = []
    fixed_net_lvr: list[float] = []
    dynamic_net_lvr: list[float] = []
    fixed_gross_lvr: list[float] = []
    dynamic_gross_lvr: list[float] = []
    concentrated_lp_value: list[float] = []
    concentrated_lvr: list[float] = []
    cpmm_swap_identity: list[float] = []
    cpmm_invariant_gain: list[float] = []
    cumulative_fixed_fee = 0.0
    cumulative_dynamic_fee = 0.0
    concentrated_lower = 64.0
    concentrated_upper = 144.0
    unscaled_concentrated_value = amm.concentrated_liquidity_value(
        1_000.0,
        concentrated_lower,
        concentrated_upper,
        index_price[0],
    )
    concentrated_liquidity = 1_000.0 * (
        (reserve_x * index_price[0] + reserve_y) / unscaled_concentrated_value
    )
    for index, price in enumerate(index_price):
        trade_notional = 0.0 if index == 0 else abs(price - index_price[index - 1]) * reserve_x
        cumulative_fixed_fee += 0.003 * trade_notional
        dynamic_rate = amm.dynamic_fee_rate(
            0.003,
            0.0 if index == 0 else abs(np.log(price / index_price[index - 1])),
            inventory_skew=float(mark_price[index] / price - 1.0),
            volatility_sensitivity=0.20,
            inventory_sensitivity=0.05,
            max_fee=0.03,
        )
        cumulative_dynamic_fee += dynamic_rate * trade_notional
        fixed_result = amm.loss_versus_rebalancing(
            reserve_x,
            reserve_y,
            price,
            fee_compensation=cumulative_fixed_fee,
        )
        result = amm.loss_versus_rebalancing(
            reserve_x,
            reserve_y,
            price,
            fee_compensation=cumulative_dynamic_fee,
        )
        rebalanced_value.append(result.rebalancing_value)
        lp_value.append(result.lp_value_before_fees)
        lvr.append(result.gross_lvr)
        fee_income.append(cumulative_fixed_fee)
        dynamic_fee_income.append(cumulative_dynamic_fee)
        fixed_net_lvr.append(fixed_result.net_lvr)
        dynamic_net_lvr.append(result.net_lvr)
        fixed_gross_lvr.append(fixed_result.gross_lvr)
        dynamic_gross_lvr.append(result.gross_lvr)
        amm_identity.append(result.gross_lvr - result.fee_compensation - result.net_lvr)
        concentrated = amm.concentrated_loss_versus_rebalancing(
            concentrated_liquidity,
            concentrated_lower,
            concentrated_upper,
            index_price[0],
            price,
            fee_compensation=cumulative_dynamic_fee,
        )
        concentrated_lp_value.append(concentrated.lp_value_before_fees)
        concentrated_lvr.append(concentrated.gross_lvr)
        swap = amm.cpmm_swap_x_for_y(
            reserve_x,
            reserve_y,
            1.0 + trade_notional / max(price, 1e-12),
            fee_rate=dynamic_rate,
        )
        cpmm_swap_identity.append(
            abs((swap.reserve_x_after - swap.reserve_x_before) - swap.amount_in)
            + abs((swap.reserve_y_before - swap.reserve_y_after) - swap.amount_out)
        )
        cpmm_invariant_gain.append(swap.invariant_after - swap.invariant_before)

    liability = np.maximum(-np.asarray(equity), 0.0)
    cashflow_conservation_error = max(
        float(np.max(np.abs(funding_error))),
        max(abs(item.conservation_error) for item in waterfalls),
        float(np.max(np.abs(amm_identity))),
        float(np.max(np.abs(cpmm_swap_identity))),
    )
    solvency_identity_error = max(abs(insurance_identity), abs(waterfall.uncovered_loss))
    arrays: ArrayMap = {
        "contract_names": contract_names,
        "contract_settlement_price": settlement_price,
        "contract_pnl_long": contract_pnl_long,
        "contract_pnl_short": contract_pnl_short,
        "step": step,
        "elapsed_hours": elapsed_hours,
        "index_price": index_price,
        "mark_price": mark_price,
        "last_price": last_price,
        "mark_index_basis": basis_path.basis,
        "funding_rate": basis_path.funding_rates,
        "funding_rate_cap": np.full(step.size, funding_policy.absolute_cap),
        "funding_settled_intervals": np.asarray(settled_intervals),
        "funding_long_cashflow": np.asarray(funding_long),
        "funding_short_cashflow": np.asarray(funding_short),
        "funding_venue_cashflow": np.asarray(funding_venue),
        "funding_conservation_error": np.asarray(funding_error),
        "funding_cashflow": np.asarray(cumulative_funding),
        "equity": np.asarray(equity),
        "liability": liability,
        "initial_margin_requirement": np.asarray(
            [liquidation.margin_requirement(account, price, initial=True) for price in mark_price]
        ),
        "maintenance_margin_requirement": np.asarray(
            [liquidation.margin_requirement(account, price) for price in mark_price]
        ),
        "bankruptcy_price": np.full(step.size, liquidation.bankruptcy_price(account)),
        "liquidation_price": np.full(step.size, liquidation.liquidation_price(account)),
        "insurance_fund": insurance_fund,
        "insurance_used": np.asarray([0.0] * (step.size - 1) + [waterfall.insurance_used]),
        "adl_notional": adl_used,
        "socialized_loss": socialized_loss,
        "uncovered_loss": uncovered_loss,
        "liquidation_conservation_error": liquidation_conservation,
        "liquidation_method_names": np.asarray(liquidation_methods),
        "liquidation_execution_price": np.asarray(execution_prices),
        "liquidation_method_equity": np.asarray([item.account_equity for item in waterfalls]),
        "liquidation_method_auction_recovery": np.asarray(
            [item.auction_recovery for item in waterfalls]
        ),
        "liquidation_method_insurance_used": np.asarray(
            [item.insurance_used for item in waterfalls]
        ),
        "liquidation_method_adl_used": np.asarray([item.adl_used for item in waterfalls]),
        "liquidation_method_socialized_loss": np.asarray(
            [item.socialized_loss for item in waterfalls]
        ),
        "liquidation_method_uncovered_loss": np.asarray(
            [item.uncovered_loss for item in waterfalls]
        ),
        "liquidation_method_conservation_error": np.asarray(
            [item.conservation_error for item in waterfalls]
        ),
        "rebalanced_value": np.asarray(rebalanced_value),
        "lp_value": np.asarray(lp_value),
        "lvr": np.asarray(lvr),
        "fee_income": np.asarray(fee_income),
        "dynamic_fee_income": np.asarray(dynamic_fee_income),
        "fixed_fee_net_lvr": np.asarray(fixed_net_lvr),
        "dynamic_fee_net_lvr": np.asarray(dynamic_net_lvr),
        "fixed_fee_gross_lvr": np.asarray(fixed_gross_lvr),
        "dynamic_fee_gross_lvr": np.asarray(dynamic_gross_lvr),
        "concentrated_lp_value": np.asarray(concentrated_lp_value),
        "concentrated_lvr": np.asarray(concentrated_lvr),
        "cpmm_swap_identity_error": np.asarray(cpmm_swap_identity),
        "cpmm_invariant_gain": np.asarray(cpmm_invariant_gain),
        "amm_identity_error": np.asarray(amm_identity),
        "oracle_age": np.asarray(oracle_age),
        "oracle_stale": np.asarray(oracle_stale),
        "oracle_dislocated": np.asarray(oracle_dislocated),
        "oracle_shocked_mark": np.asarray(shocked_mark),
        "oracle_latent_index": np.asarray(latent_index),
        "oracle_observed_dislocation": np.asarray(oracle_observed_dislocation),
        "oracle_latent_dislocation": np.asarray(oracle_latent_dislocation),
        "liquidation_loss": np.asarray(oracle_loss),
    }
    metrics: dict[str, Scalar] = {
        "cashflow_conservation_error": cashflow_conservation_error,
        "solvency_identity_error": solvency_identity_error,
        "insurance_identity_error": abs(insurance_identity),
        "ending_insurance_fund": waterfall.insurance_fund_after,
        "ending_adl_notional": waterfall.adl_used,
        "ending_socialized_loss": waterfall.socialized_loss,
        "ending_uncovered_loss": waterfall.uncovered_loss,
        "solvent": waterfall.solvent,
        "contract_long_short_sign_error": float(
            np.max(np.abs(contract_pnl_long + contract_pnl_short))
        ),
        "contract_zero_move_error": float(np.max(np.abs(contract_pnl_long[:, 1]))),
        "funding_interval_hours": funding_policy.interval_hours,
        "funding_absolute_cap": funding_policy.absolute_cap,
        "oracle_stale_count": int(np.count_nonzero(oracle_stale)),
        "oracle_dislocated_count": int(np.count_nonzero(oracle_dislocated)),
        "forced_sale_socialized_loss": waterfalls[0].socialized_loss,
        "auction_socialized_loss": waterfalls[1].socialized_loss,
        "dynamic_fee_gross_lvr_reduction": float(
            np.max(np.abs(np.asarray(fixed_gross_lvr) - np.asarray(dynamic_gross_lvr)))
        ),
        "dynamic_fee_compensation": float(dynamic_fee_income[-1]),
        "synthetic_cascade": True,
    }
    return FrontierReference(24, seed, arrays, metrics)


def _black76_implied_volatility(
    price: float,
    forward: float,
    strike: float,
    rate: float,
    maturity: float,
) -> float:
    intrinsic = carbon.black76_price(forward, strike, rate, 0.0, maturity)
    if price <= intrinsic + 1e-12:
        return 0.0
    return float(
        brentq(
            lambda volatility: (
                carbon.black76_price(
                    forward,
                    strike,
                    rate,
                    volatility,
                    maturity,
                )
                - price
            ),
            1e-8,
            5.0,
        )
    )


def volume25_reference(*, seed: int = 20260743) -> FrontierReference:
    """Carbon, incomplete-market weather, and PPA sensitivity payload."""

    forward = 100.0
    rate = 0.02
    maturity = 1.0
    strike = np.linspace(70.0, 130.0, 9)
    gbm_dynamics = carbon.CarbonDynamics(v0=0.0625, theta=0.0625, vol_of_vol=0.0)
    heston_dynamics = carbon.CarbonDynamics(
        v0=0.0625,
        theta=0.0625,
        vol_of_vol=0.45,
        rho=-0.40,
    )
    jump_dynamics = carbon.CarbonDynamics(
        v0=0.0625,
        theta=0.0625,
        vol_of_vol=0.45,
        jump_intensity=0.45,
        jump_mean=-0.06,
        jump_volatility=0.12,
    )
    gbm_terminal = carbon.simulate_terminal_futures(
        forward,
        maturity,
        model="gbm",
        dynamics=gbm_dynamics,
        n_steps=16,
        n_paths=8_000,
        seed=seed,
    )
    heston_terminal = carbon.simulate_terminal_futures(
        forward,
        maturity,
        model="heston",
        dynamics=heston_dynamics,
        n_steps=16,
        n_paths=8_000,
        seed=seed + 1,
    )
    jump_terminal = carbon.simulate_terminal_futures(
        forward,
        maturity,
        model="sv_jump",
        dynamics=jump_dynamics,
        n_steps=16,
        n_paths=8_000,
        seed=seed + 2,
    )
    discount = np.exp(-rate * maturity)
    black76_price = np.asarray(
        [carbon.black76_price(forward, value, rate, 0.25, maturity) for value in strike]
    )
    gbm_payoff = np.asarray([np.maximum(gbm_terminal - value, 0.0) for value in strike])
    gbm_price = np.asarray([discount * payoff.mean() for payoff in gbm_payoff])
    gbm_se = discount * gbm_payoff.std(axis=1, ddof=1) / np.sqrt(gbm_terminal.size)
    heston_payoff = np.asarray([np.maximum(heston_terminal - value, 0.0) for value in strike])
    heston_price = discount * heston_payoff.mean(axis=1)
    heston_se = discount * heston_payoff.std(axis=1, ddof=1) / np.sqrt(heston_terminal.size)
    jump_payoff = np.asarray([np.maximum(jump_terminal - value, 0.0) for value in strike])
    jump_price = discount * jump_payoff.mean(axis=1)
    jump_se = discount * jump_payoff.std(axis=1, ddof=1) / np.sqrt(jump_terminal.size)
    carbon_gbm_iv = np.asarray(
        [
            _black76_implied_volatility(price, forward, value, rate, maturity)
            for price, value in zip(gbm_price, strike, strict=True)
        ]
    )
    carbon_jump_iv = np.asarray(
        [
            _black76_implied_volatility(price, forward, value, rate, maturity)
            for price, value in zip(jump_price, strike, strict=True)
        ]
    )
    carbon_heston_iv = np.asarray(
        [
            _black76_implied_volatility(price, forward, value, rate, maturity)
            for price, value in zip(heston_price, strike, strict=True)
        ]
    )
    carbon_sensitivity = carbon.risk_premium_sensitivity(
        forward,
        100.0,
        rate,
        maturity,
        dynamics=jump_dynamics,
        n_steps=12,
        n_paths=5_000,
        seed=seed + 3,
    )

    day = np.arange(180, dtype=float)
    seasonal = weather.seasonal_temperature_mean(
        day,
        intercept=14.0,
        trend_per_year=0.8,
        amplitude=10.0,
        peak_day=200.0,
    )
    ou_paths = weather.simulate_ou_temperature(
        seasonal,
        seasonal[0],
        kappa=0.18,
        sigma=2.0,
        n_paths=160,
        seed=seed + 4,
    )
    fou_paths = weather.simulate_fractional_ou_temperature(
        seasonal,
        seasonal[0],
        kappa=0.18,
        sigma=1.3,
        hurst=0.78,
        n_paths=160,
        seed=seed + 5,
    )
    degree_days = weather.degree_day_index(ou_paths)
    fou_degree_days = weather.degree_day_index(fou_paths)
    ou_deviation = ou_paths - seasonal
    fou_deviation = fou_paths - seasonal
    temperature_lag1 = np.asarray(
        [
            np.corrcoef(ou_deviation[:, :-1].ravel(), ou_deviation[:, 1:].ravel())[0, 1],
            np.corrcoef(fou_deviation[:, :-1].ravel(), fou_deviation[:, 1:].ravel())[0, 1],
        ]
    )
    weather_payoff = 10.0 * np.maximum(degree_days - np.median(degree_days), 0.0)
    premium_principle_names = np.asarray(["expected_value", "standard_deviation", "exponential"])
    weather_premium = np.asarray(
        [
            weather.weather_contract_premium(weather_payoff, principle="expected_value"),
            weather.weather_contract_premium(
                weather_payoff,
                principle="standard_deviation",
                loading=0.25,
            ),
            weather.weather_contract_premium(
                weather_payoff,
                principle="exponential",
                risk_aversion=0.002,
            ),
        ]
    )
    station_distance = np.asarray([0.0, 10.0, 25.0, 50.0, 100.0, 200.0])
    basis_rmse: list[float] = []
    basis_residual: list[float] = []
    basis_hedge_ratio: list[float] = []
    basis_variance_reduction: list[float] = []
    basis_rng = np.random.default_rng(seed + 6)
    for distance in station_distance:
        station_payoff = weather_payoff + (distance / 35.0) * basis_rng.standard_normal(
            weather_payoff.size
        )
        report = weather.optimal_basis_hedge(weather_payoff, station_payoff)
        basis_rmse.append(report.mismatch_rmse)
        basis_residual.append(report.residual_std)
        basis_hedge_ratio.append(report.hedge_ratio)
        basis_variance_reduction.append(report.variance_reduction)

    scenarios = ppa.simulate_price_generation(
        1_000,
        12,
        base_price=60.0,
        base_generation=1.0,
        correlation=-0.60,
        seed=seed + 7,
    )
    ppa_inputs = (
        (
            "fixed",
            {"fixed_price": 60.0, "contracted_volume": 1.0},
        ),
        ("pay_as_produced", {"fixed_price": 60.0}),
        ("floor_collar", {"floor": 50.0, "cap": 75.0}),
    )
    valuations = [
        ppa.evaluate_ppa(
            kind,
            scenarios.spot_prices,
            scenarios.generation,
            **terms,
        )
        for kind, terms in ppa_inputs
    ]
    hedge_ratio = np.linspace(0.0, 1.0, 5)
    hedge_sensitivity = ppa.hedge_sensitivity(
        "pay_as_produced",
        scenarios.spot_prices,
        scenarios.generation,
        hedge_ratio,
        fixed_price=60.0,
    )
    ppa_settlements = [
        ppa.ppa_settlement(
            kind,
            scenarios.spot_prices,
            scenarios.generation,
            **terms,
        ).mean(axis=0)
        for kind, terms in ppa_inputs
    ]
    arrays: ArrayMap = {
        "strike": strike,
        "carbon_model_names": np.asarray(["Black-76", "GBM MC", "Heston MC", "SV+jump MC"]),
        "carbon_model_price": np.stack([black76_price, gbm_price, heston_price, jump_price]),
        "carbon_model_standard_error": np.stack(
            [np.zeros_like(gbm_se), gbm_se, heston_se, jump_se]
        ),
        "carbon_black76_price": black76_price,
        "carbon_gbm_price": gbm_price,
        "carbon_gbm_standard_error": gbm_se,
        "carbon_heston_price": heston_price,
        "carbon_heston_standard_error": heston_se,
        "carbon_jump_price": jump_price,
        "carbon_jump_standard_error": jump_se,
        "carbon_gbm_iv": carbon_gbm_iv,
        "carbon_heston_iv": carbon_heston_iv,
        "carbon_jump_iv": carbon_jump_iv,
        "risk_premium_names": np.asarray(["return", "variance", "jump"]),
        "premium_sensitivity": np.asarray(
            [
                carbon_sensitivity.return_effect,
                carbon_sensitivity.variance_effect,
                carbon_sensitivity.jump_effect,
            ]
        ),
        "day": day,
        "temperature_seasonal": seasonal,
        "temperature_ou": ou_paths.mean(axis=0),
        "temperature_fou": fou_paths.mean(axis=0),
        "temperature_model_names": np.asarray(["OU", "fractional OU"]),
        "temperature_path_std": np.asarray([ou_paths.std(), fou_paths.std()]),
        "temperature_lag1_autocorrelation": temperature_lag1,
        "degree_day_mean": np.asarray([degree_days.mean(), fou_degree_days.mean()]),
        "degree_day_std": np.asarray([degree_days.std(), fou_degree_days.std()]),
        "premium_principle_names": premium_principle_names,
        "weather_premium": weather_premium,
        "station_distance_km": station_distance,
        "basis_rmse": np.asarray(basis_rmse),
        "basis_residual": np.asarray(basis_residual),
        "basis_hedge_ratio": np.asarray(basis_hedge_ratio),
        "basis_variance_reduction": np.asarray(basis_variance_reduction),
        "ppa_fixed": ppa_settlements[0],
        "ppa_pay_as_produced": ppa_settlements[1],
        "ppa_floor_collar": ppa_settlements[2],
        "risk_names": np.asarray(["fixed", "pay-as-produced", "floor-collar"]),
        "cvar95": np.asarray([value.cash_flow_cvar for value in valuations]),
        "cash_flow_at_risk": np.asarray([value.cash_flow_at_risk for value in valuations]),
        "hedge_residual": np.asarray([value.hedge_residual_std for value in valuations]),
        "unhedged_cash_flow_std": np.asarray([value.unhedged_std for value in valuations]),
        "expected_hedged_cash_flow": np.asarray(
            [value.expected_hedged_cash_flow for value in valuations]
        ),
        "ppa_fair_value": np.asarray([value.fair_value for value in valuations]),
        "ppa_volume_risk": np.asarray([value.volume_risk for value in valuations]),
        "ppa_shape_risk": np.asarray([value.shape_risk for value in valuations]),
        "ppa_profile_risk": np.asarray([value.profile_risk for value in valuations]),
        "hedge_ratio": hedge_ratio,
        "hedge_ratio_residual": np.asarray(
            [hedge_sensitivity[float(value)] for value in hedge_ratio]
        ),
    }
    metrics: dict[str, Scalar] = {
        "carbon_model_ladder_complete": True,
        "carbon_atm_black76_price": float(black76_price[strike.size // 2]),
        "carbon_atm_heston_price": float(heston_price[strike.size // 2]),
        "carbon_atm_jump_price": float(jump_price[strike.size // 2]),
        "carbon_atm_standard_error": float(jump_se[strike.size // 2]),
        "weather_premium_principle": "standard_deviation",
        "premium_principle": "standard_deviation",
        "weather_basis_rmse_100km": float(basis_rmse[4]),
        "weather_ou_lag1_autocorrelation": float(temperature_lag1[0]),
        "weather_fou_lag1_autocorrelation": float(temperature_lag1[1]),
        "ppa_cvar95": float(valuations[1].cash_flow_cvar),
        "ppa_cash_flow_at_risk95": float(valuations[1].cash_flow_at_risk),
        "ppa_hedge_residual": float(valuations[1].hedge_residual_std),
        "hedge_residual": float(valuations[1].hedge_residual_std),
        "price_generation_correlation": scenarios.realized_correlation,
        "market_completeness": "incomplete",
    }
    return FrontierReference(25, seed, arrays, metrics)


def volume26_reference(*, seed: int = 20260744) -> FrontierReference:
    """Build the synthetic Hull--White, inflation-swap, JY, and JGBi reference."""
    nominal_curve = ((0.0, 1.0, 2.0, 5.0, 10.0), (0.012, 0.014, 0.016, 0.019, 0.022))
    real_curve = ((0.0, 1.0, 2.0, 5.0, 10.0), (0.002, 0.003, 0.004, 0.006, 0.008))
    maturity = np.asarray([1.0, 2.0, 5.0, 10.0])
    nominal_discount = np.asarray(
        [rates.discount_factor(value, nominal_curve) for value in maturity]
    )
    real_discount = np.asarray([rates.discount_factor(value, real_curve) for value in maturity])

    hw_params = hull_white.HullWhiteParams(0.10, 0.009)
    hw_market_discount = nominal_discount.copy()
    hw_model_discount = np.asarray(
        [hull_white.hw_discount_bond(0.0, value, 0.0, nominal_curve, hw_params) for value in maturity]
    )
    swaption_expiry = np.asarray([1.0, 2.0, 3.0])
    swaption_price: list[float] = []
    for expiry in swaption_expiry:
        payment_times = tuple(np.arange(expiry + 1.0, expiry + 5.0, 1.0))
        cashflows = [0.025] * len(payment_times)
        cashflows[-1] += 1.0
        spec = hull_white.HullWhiteSwaption(
            float(expiry), payment_times, tuple(cashflows), "receiver"
        )
        swaption_price.append(
            hull_white.hw_jamshidian_swaption(spec, nominal_curve, hw_params)
        )

    raw_seasonality = np.asarray(
        [0.0030, -0.0015, 0.0010, -0.0020, 0.0025, -0.0010] * 2
    )
    raw_seasonality -= raw_seasonality.mean()
    seasonality = inflation.MonthlySeasonality(tuple(raw_seasonality))
    flat_seasonality = inflation.MonthlySeasonality((0.0,) * 12)
    base_date = date(2026, 1, 1)
    seasonal_curve = inflation.ZeroCouponInflationCurve(
        base_date, 100.0, (1.0, 2.0, 5.0, 10.0), (0.012, 0.014, 0.016, 0.018), seasonality
    )
    trend_curve = inflation.ZeroCouponInflationCurve(
        base_date,
        100.0,
        seasonal_curve.maturities,
        seasonal_curve.zero_rates,
        flat_seasonality,
    )
    month_dates = tuple(
        date(2026 + month_index // 12, month_index % 12 + 1, 1)
        for month_index in range(24)
    )
    cpi_trend = np.asarray(
        [inflation.seasonal_forward_index(day, trend_curve) for day in month_dates]
    )
    cpi_seasonal = np.asarray(
        [inflation.seasonal_forward_index(day, seasonal_curve) for day in month_dates]
    )

    zcis_maturity = np.asarray([1.0, 2.0, 5.0, 10.0])
    zcis_quote = np.asarray([0.012, 0.014, 0.016, 0.018])
    zcis_curve = inflation.bootstrap_zc_inflation_curve(
        base_date, 100.0, zcis_maturity, zcis_quote, seasonality=seasonality
    )
    zcis_repriced = np.asarray(
        [zcis_curve.zero_rate(value) for value in zcis_maturity]
    )

    jy_params = jarrow_yildirim.JarrowYildirimParams(
        0.08, 0.010, 0.12, 0.008, 0.015, 0.25, -0.15, 0.30
    )
    yoy_payment = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0])
    yoy_deterministic_ratio = np.asarray(
        [
            jarrow_yildirim.jy_cpi_forward(
                0.0, end, 100.0, nominal_curve, real_curve
            )
            / jarrow_yildirim.jy_cpi_forward(
                0.0, end - 1.0, 100.0, nominal_curve, real_curve
            )
            for end in yoy_payment
        ]
    )
    yoy_jy_ratio = np.asarray(
        [
            jarrow_yildirim.jy_expected_cpi_ratio(
                0.0,
                end - 1.0,
                end,
                end,
                100.0,
                nominal_curve,
                real_curve,
                jy_params,
            )
            for end in yoy_payment
        ]
    )
    jy_observation = np.asarray([1.0, 2.0, 5.0])
    jy_forward_index = np.asarray(
        [
            jarrow_yildirim.jy_payment_forward_cpi(
                0.0, value, 5.0, 100.0, nominal_curve, real_curve, jy_params
            )
            for value in jy_observation
        ]
    )
    jy_samples = jarrow_yildirim.simulate_jy_forward_levels(
        jy_observation,
        5.0,
        100.0,
        nominal_curve,
        real_curve,
        jy_params,
        n_paths=120_000,
        seed=seed,
    )
    jy_mc_forward = jy_samples.mean(axis=0)
    jy_mc_standard_error = jy_samples.std(axis=0, ddof=1) / np.sqrt(len(jy_samples))

    monthly_cpi: dict[date, float] = {}
    cpi_value = 110.0
    for year in range(2025, 2032):
        for month in range(1, 13):
            monthly_cpi[date(year, month, 1)] = cpi_value
            cpi_value -= 0.12
    coupon_dates = tuple(
        date(year, month, 10)
        for year in range(2027, 2032)
        for month in (1, 7)
        if date(year, month, 10) <= date(2031, 7, 10)
    )
    base_terms = dict(
        issue_date=date(2026, 7, 10),
        maturity_date=date(2031, 7, 10),
        coupon_dates=coupon_dates,
        coupon_rate=0.005,
        face_value=100.0,
        base_reference_date=date(2026, 7, 10),
    )
    floored_terms = jgbi.JGBITerms(**base_terms, principal_floor=True)
    unfloored_terms = jgbi.JGBITerms(**base_terms, principal_floor=False)
    floored_cashflows = jgbi.jgbi_cashflows(floored_terms, monthly_cpi)
    unfloored_cashflows = jgbi.jgbi_cashflows(unfloored_terms, monthly_cpi)
    jgbi_payment_year = np.asarray(
        [(row.payment_date - floored_terms.issue_date).days / 365.25 for row in floored_cashflows]
    )

    base_index = jgbi.jgbi_reference_index(floored_terms.base_reference_date, monthly_cpi)
    inflation_volatility = np.asarray([0.0, 0.01, 0.02, 0.03])
    floor_analytic: list[float] = []
    floor_mc: list[float] = []
    floor_mc_standard_error: list[float] = []
    floor_models: list[jarrow_yildirim.JarrowYildirimParams] = []
    for index, volatility in enumerate(inflation_volatility):
        model = jarrow_yildirim.JarrowYildirimParams(
            0.08, 0.0, 0.12, 0.0, float(volatility), 0.0, 0.0, 0.0
        )
        floor_models.append(model)
        analytic = jgbi.jgbi_deflation_floor_jy(
            100.0,
            base_index,
            0.0,
            5.0,
            5.0,
            base_index,
            nominal_curve,
            real_curve,
            model,
        )
        mc = jgbi.jgbi_deflation_floor_jy_mc(
            100.0,
            base_index,
            0.0,
            5.0,
            5.0,
            base_index,
            nominal_curve,
            real_curve,
            model,
            n_paths=100_000,
            seed=seed + index + 1,
        )
        floor_analytic.append(analytic)
        floor_mc.append(mc.value)
        floor_mc_standard_error.append(mc.standard_error)
    floor_analytic_array = np.asarray(floor_analytic)
    floor_mc_array = np.asarray(floor_mc)
    floor_se_array = np.asarray(floor_mc_standard_error)

    raw_real_yield = 0.005
    nominal_yield = 0.015
    raw_clean_price = jgbi.jgbi_real_clean_price(
        raw_real_yield, floored_terms.issue_date, floored_terms
    )
    adjusted_clean_price = raw_clean_price + floor_analytic_array[2]
    adjusted_real_yield = jgbi.jgbi_real_yield(
        adjusted_clean_price, floored_terms.issue_date, floored_terms
    )
    breakeven = np.asarray(
        [
            jgbi.jgbi_breakeven_inflation(nominal_yield, raw_real_yield),
            jgbi.jgbi_breakeven_inflation(nominal_yield, adjusted_real_yield),
        ]
    )
    floor_risk = jgbi.jgbi_floor_risk(
        100.0,
        base_index,
        0.0,
        5.0,
        5.0,
        base_index,
        nominal_curve,
        real_curve,
        floor_models[2],
    )

    jy_zscores = np.abs(jy_mc_forward - jy_forward_index) / jy_mc_standard_error
    nonzero_floor_se = floor_se_array > 0.0
    floor_zscores = np.zeros_like(floor_se_array)
    floor_zscores[nonzero_floor_se] = np.abs(
        floor_mc_array[nonzero_floor_se] - floor_analytic_array[nonzero_floor_se]
    ) / floor_se_array[nonzero_floor_se]
    coupon_floor_error = max(
        abs(left.coupon - right.coupon)
        for left, right in zip(floored_cashflows, unfloored_cashflows, strict=True)
    )
    replication_error = abs(
        (raw_clean_price + floor_analytic_array[2]) - adjusted_clean_price
    )
    arrays: ArrayMap = {
        "maturity": maturity,
        "nominal_discount_factor": nominal_discount,
        "real_discount_factor": real_discount,
        "hw_market_discount_factor": hw_market_discount,
        "hw_model_discount_factor": hw_model_discount,
        "hw_swaption_expiry": swaption_expiry,
        "hw_swaption_price": np.asarray(swaption_price),
        "month_index": np.arange(len(month_dates), dtype=float),
        "month_names": np.asarray(
            ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        ),
        "seasonality_log_factor": raw_seasonality,
        "cpi_trend": cpi_trend,
        "cpi_seasonal": cpi_seasonal,
        "zcis_maturity": zcis_maturity,
        "zcis_quote": zcis_quote,
        "zcis_repriced": zcis_repriced,
        "yoy_payment": yoy_payment,
        "yoy_deterministic_ratio": yoy_deterministic_ratio,
        "yoy_jy_ratio": yoy_jy_ratio,
        "jy_observation": jy_observation,
        "jy_forward_index": jy_forward_index,
        "jy_mc_forward_index": jy_mc_forward,
        "jy_mc_standard_error": jy_mc_standard_error,
        "jgbi_payment_year": jgbi_payment_year,
        "jgbi_cashflow_names": np.asarray(
            [row.payment_date.isoformat() for row in floored_cashflows]
        ),
        "jgbi_index_ratio": np.asarray([row.index_ratio for row in floored_cashflows]),
        "jgbi_coupon": np.asarray([row.coupon for row in floored_cashflows]),
        "jgbi_unfloored_principal": np.asarray([row.principal for row in unfloored_cashflows]),
        "jgbi_floored_principal": np.asarray([row.principal for row in floored_cashflows]),
        "inflation_volatility": inflation_volatility,
        "floor_analytic": floor_analytic_array,
        "floor_mc": floor_mc_array,
        "floor_mc_standard_error": floor_se_array,
        "bei_names": np.asarray(["raw", "floor-adjusted"]),
        "breakeven_inflation": breakeven,
        "hedge_risk_names": np.asarray(["nominal duration", "CPI delta"]),
        "unhedged_normalized_risk": np.asarray([1.0, 1.0]),
        "hedged_normalized_risk": np.asarray([0.0, 0.0]),
        "floor_value": np.asarray([floor_risk.value]),
        "floor_cpi_delta": np.asarray([floor_risk.cpi_delta]),
        "floor_inflation_vega": np.asarray([floor_risk.inflation_vega]),
    }
    metrics: dict[str, Scalar] = {
        "hw_curve_fit_max_error": float(np.max(np.abs(hw_market_discount - hw_model_discount))),
        "seasonality_annual_log_sum": float(abs(raw_seasonality.sum())),
        "zcis_repricing_max_error": float(np.max(np.abs(zcis_quote - zcis_repriced))),
        "yoy_convexity_bp": float(10_000.0 * np.max(np.abs(yoy_jy_ratio - yoy_deterministic_ratio))),
        "jy_forward_mc_zscore_max": float(np.max(jy_zscores)),
        "floor_mc_zscore_max": float(np.max(floor_zscores)),
        "floor_monotone_in_volatility": bool(np.all(np.diff(floor_analytic_array) >= 0.0)),
        "coupon_floor_max_error": float(coupon_floor_error),
        "floor_decomposition_error": float(replication_error),
        "principal_floor_redemption_only": True,
        "raw_breakeven_inflation": float(breakeven[0]),
        "floor_adjusted_breakeven_inflation": float(breakeven[1]),
        "measure_treatment": "nominal_payment_forward",
    }
    return FrontierReference(26, seed, arrays, metrics)


_BUILDERS: dict[int, Callable[..., FrontierReference]] = {
    21: volume21_reference,
    22: volume22_reference,
    23: volume23_reference,
    24: volume24_reference,
    25: volume25_reference,
    26: volume26_reference,
}


def build_frontier_reference(volume: int, *, seed: int | None = None) -> FrontierReference:
    """Build a serialization-ready vol 21--26 payload by volume number."""

    try:
        builder = _BUILDERS[volume]
    except KeyError as exc:
        raise ValueError("frontier reference volume must lie in [21, 26]") from exc
    return builder() if seed is None else builder(seed=seed)
