"""Perturbation, refit and stability checks for the advanced curve."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .advanced import PCT, AdvancedConfig, AdvancedFit, fit_advanced, penalty_root, penalty_weight, solve_penalized
from .conventions import StubRule
from .instruments import Instrument, build_instrument
from .pricing import SplineResidualEngine, dollar_duration, rate_residual


def _curve_delta(reference, other, grid: np.ndarray) -> dict:
    dz = (other.zero(grid) - reference.zero(grid)) * 1e4
    df_ = (other.forward(grid) - reference.forward(grid)) * 1e4
    return {
        "max_abs_zero_change_bp": float(np.max(np.abs(dz))),
        "mean_abs_zero_change_bp": float(np.mean(np.abs(dz))),
        "max_abs_forward_change_bp": float(np.max(np.abs(df_))),
        "zero_change_bp_at_grid": dz,
    }


def _rmse_by_type(instruments: list[Instrument], curve, types: np.ndarray, factor: np.ndarray) -> dict:
    res = np.array([rate_residual(i, curve) * 1e4 for i in instruments])
    out = {}
    for t in np.unique(types):
        m = (types == t) & (factor > 0)
        out[str(t)] = float(np.sqrt(np.mean(res[m] ** 2))) if m.any() else None
    m = factor > 0
    out["all"] = float(np.sqrt(np.mean(res[m] ** 2))) if m.any() else None
    return out


def run_sensitivity(
    adv: AdvancedFit,
    instruments: list[Instrument],
    table: pd.DataFrame,
    base_scale: np.ndarray,
    cluster_ids: np.ndarray,
    cfg: AdvancedConfig,
    t_max: float,
    stub_rule: StubRule,
    grid: np.ndarray,
    seed: int = 20260115,
    n_noise: int = 20,
) -> tuple[dict, pd.DataFrame]:
    types = table["instrument_type"].to_numpy()
    factor = adv.fit.robust_factor
    ref = adv.curve
    checks = []
    deltas = {"maturity_years": grid}

    def refit(insts=None, scales=None, lam=None, power=None, knots=None):
        return fit_advanced(
            insts or instruments,
            base_scale if scales is None else scales,
            types,
            cluster_ids,
            t_max,
            cfg,
            lam=adv.lam if lam is None else lam,
            power=adv.power if power is None else power,
            knots=adv.knots if knots is None else knots,
            run_cv=False,
        )

    # 1. smoothing parameter perturbation
    for mult in (1.0 / 3.0, 3.0):
        alt = refit(lam=adv.lam * mult)
        d = _curve_delta(ref, alt.curve, grid)
        name = f"lambda_x{mult:.2f}"
        deltas[name] = d.pop("zero_change_bp_at_grid")
        checks.append(
            {
                "name": name,
                "description": f"Refit with the smoothing parameter multiplied by {mult:.2f} (lambda={adv.lam * mult:.4g}).",
                "outcome": {**d, "train_rmse_bp": _rmse_by_type(instruments, alt.curve, types, alt.fit.robust_factor), "n_excluded": int((alt.fit.robust_factor == 0).sum())},
            }
        )

    # 2. penalty shape
    alt_power = 0.0 if adv.power != 0.0 else 1.0
    alt = refit(power=alt_power)
    d = _curve_delta(ref, alt.curve, grid)
    deltas[f"penalty_power_{alt_power:g}"] = d.pop("zero_change_bp_at_grid")
    checks.append(
        {
            "name": f"penalty_power_{alt_power:g}",
            "description": f"Refit with the maturity-weight exponent of the roughness penalty set to {alt_power:g} instead of the CV-selected {adv.power:g} (same lambda).",
            "outcome": {**d, "train_rmse_bp": _rmse_by_type(instruments, alt.curve, types, alt.fit.robust_factor)},
        }
    )

    # 3. schedule convention alternatives
    for rule in ("round", "linspace", "ceil"):
        if rule == stub_rule:
            continue
        alt_insts = [
            build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate, stub_rule=rule)
            for r in table.itertuples()
        ]
        alt = refit(insts=alt_insts)
        d = _curve_delta(ref, alt.curve, grid)
        deltas[f"stub_rule_{rule}"] = d.pop("zero_change_bp_at_grid")
        checks.append(
            {
                "name": f"stub_rule_{rule}",
                "description": f"Rebuild every OIS/bond schedule with the '{rule}' stub rule instead of '{stub_rule}' and refit (same lambda).",
                "outcome": {**d, "train_rmse_bp": _rmse_by_type(alt_insts, alt.curve, types, alt.fit.robust_factor), "n_excluded": int((alt.fit.robust_factor == 0).sum())},
            }
        )

    # 4. instrument-class exclusion: rates only
    rate_mask = np.isin(types, ["deposit", "ois_swap"])
    if rate_mask.sum() >= 6 and (~rate_mask).any():
        sub = [i for i, m in zip(instruments, rate_mask) if m]
        alt = fit_advanced(sub, base_scale[rate_mask], types[rate_mask], cluster_ids[rate_mask], t_max, cfg, lam=adv.lam, power=adv.power, knots=adv.knots, run_cv=False)
        d = _curve_delta(ref, alt.curve, grid)
        deltas["rates_only"] = d.pop("zero_change_bp_at_grid")
        bond_idx = np.flatnonzero(~rate_mask & (factor > 0))
        bond_err = np.array([rate_residual(instruments[j], alt.curve) * 1e4 for j in bond_idx])
        checks.append(
            {
                "name": "rates_only",
                "description": "Refit using deposits and OIS only; bonds are then priced off the rates-only curve.",
                "outcome": {**d, "bond_repricing_rmse_bp_on_rates_only_curve": float(np.sqrt(np.mean(bond_err**2))) if len(bond_err) else None, "bond_repricing_rmse_bp_on_full_curve": _rmse_by_type(instruments, ref, types, factor).get("bond")},
            }
        )

    # 5. uniform weights
    alt = refit(scales=np.full(len(base_scale), float(np.median(base_scale))))
    d = _curve_delta(ref, alt.curve, grid)
    deltas["uniform_weights"] = d.pop("zero_change_bp_at_grid")
    checks.append(
        {
            "name": "uniform_weights",
            "description": "Refit with every quote given the same base scale (spread and liquidity information ignored; robust reweighting still active).",
            "outcome": {**d, "train_rmse_bp": _rmse_by_type(instruments, alt.curve, types, alt.fit.robust_factor)},
        }
    )

    # 6. parallel quote shift (+1bp yield-equivalent): curve should move ~1bp
    shifted = []
    for inst in instruments:
        if inst.is_rate:
            shifted.append(build_instrument(inst.instrument_id, inst.instrument_type, inst.maturity, inst.quote + 1e-4, inst.frequency, inst.coupon_rate, stub_rule=stub_rule))
        else:
            dd = dollar_duration(inst, ref)
            shifted.append(build_instrument(inst.instrument_id, inst.instrument_type, inst.maturity, inst.quote - dd * 1e-4, inst.frequency, inst.coupon_rate, stub_rule=stub_rule))
    alt = refit(insts=shifted)
    dz = (alt.curve.zero(grid) - ref.zero(grid)) * 1e4
    deltas["quote_shift_+1bp"] = dz
    checks.append(
        {
            "name": "quote_shift_+1bp",
            "description": "Shift every market quote by +1bp (bond prices by minus one basis point of yield) and refit; a well-behaved estimator moves the zero curve by about +1bp everywhere.",
            "outcome": {"mean_zero_change_bp": float(np.mean(dz)), "min_zero_change_bp": float(np.min(dz)), "max_zero_change_bp": float(np.max(dz)), "max_abs_deviation_from_1bp": float(np.max(np.abs(dz - 1.0)))},
        }
    )

    # 7. jackknife over tenor clusters (fixed robust weights: plain penalised WLS)
    engine = SplineResidualEngine(adv.curve, instruments)
    L = adv.L
    weights = adv.fit.weights
    theta_full = adv.curve.coeffs * PCT
    jack = []
    for cid in np.unique(cluster_ids):
        keep = cluster_ids != cid
        if keep.sum() < adv.curve.n_basis // 2:
            continue
        sub = SplineResidualEngine(adv.curve, [i for i, m in zip(instruments, keep) if m])
        th = solve_penalized(sub, weights[keep], adv.lam, L, theta_full)
        c = adv.curve.with_coeffs(th / PCT)
        dz = (c.zero(grid) - ref.zero(grid)) * 1e4
        members = table.loc[cluster_ids == cid, "instrument_id"].tolist()
        jack.append({"cluster": int(cid), "maturity_years": float(np.median(table.loc[cluster_ids == cid, "maturity"])), "members": members, "max_abs_zero_change_bp": float(np.max(np.abs(dz)))})
    jack_df = pd.DataFrame(jack).sort_values("max_abs_zero_change_bp", ascending=False)
    checks.append(
        {
            "name": "jackknife_tenor_clusters",
            "description": "Leave one tenor cluster out at a time (robust weights fixed) and measure the largest change in the zero curve; large values flag tenors that single-handedly shape the curve.",
            "outcome": {
                "n_clusters": int(len(jack_df)),
                "max_abs_zero_change_bp": float(jack_df["max_abs_zero_change_bp"].max()) if len(jack_df) else None,
                "median_abs_zero_change_bp": float(jack_df["max_abs_zero_change_bp"].median()) if len(jack_df) else None,
                "most_influential": jack_df.head(5).to_dict(orient="records"),
            },
        }
    )

    # 8. quote-noise bootstrap (seeded, fixed robust weights)
    rng = np.random.default_rng(seed)
    s_vec = np.array([adv.fit.type_scale.get(str(t), 1.0) for t in types])
    sigma = base_scale * s_vec
    zs = []
    for _ in range(n_noise):
        noise = rng.standard_normal(len(instruments)) * sigma
        perturbed = []
        for inst, eps in zip(instruments, noise):
            if inst.is_rate:
                q = inst.quote + eps
            else:
                q = inst.quote - dollar_duration(inst, ref) * eps
            perturbed.append(build_instrument(inst.instrument_id, inst.instrument_type, inst.maturity, q, inst.frequency, inst.coupon_rate, stub_rule=stub_rule))
        eng = SplineResidualEngine(adv.curve, perturbed)
        th = solve_penalized(eng, weights, adv.lam, L, theta_full)
        zs.append(adv.curve.with_coeffs(th / PCT).zero(grid) * 1e4)
    zs = np.array(zs)
    std = zs.std(axis=0, ddof=1)
    deltas["noise_std"] = std
    key_pts = {f"{t:g}y": float(np.interp(t, grid, std)) for t in (0.25, 1, 2, 5, 10, 20, 30) if grid.min() <= t <= grid.max()}
    checks.append(
        {
            "name": "quote_noise_bootstrap",
            "description": f"{n_noise} seeded replications adding Gaussian noise of one estimated noise scale to every quote (robust weights fixed); reports the standard deviation of the fitted zero curve.",
            "outcome": {"n_replications": n_noise, "seed": seed, "max_zero_std_bp": float(std.max()), "median_zero_std_bp": float(np.median(std)), "zero_std_bp_at": key_pts},
        }
    )
    return {"checks": checks}, pd.DataFrame(deltas)
