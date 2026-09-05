"""H3/H4: fit BOTH estimators to synthetic markets built from KNOWN curves and
measure zero *and* instantaneous-forward error by maturity band.

Nothing here guesses at the hidden data set.  The curves, the maturity sets and
the defects are all chosen by me and stated in the output.
"""
from __future__ import annotations
import json, math, sys, time
import numpy as np

sys.path.insert(0, sys.argv[1])              # src
from quantcurve.curve import DiscountCurve
from quantcurve.instruments import Instrument
from quantcurve.conventions import swap_schedule, bond_schedule
from quantcurve import pricing as qp
from quantcurve.models import FitConfig, fit_advanced, fit_baseline
from quantcurve.holdout import HoldoutConfig, forward_admissibility

SEED = 20260905


class Analytic(DiscountCurve):
    def __init__(self, name, z, dz):
        self.name, self._z, self._dz = name, z, dz
    def zero(self, t):
        return self._z(np.asarray(t, float))
    def discount(self, t):
        t = np.asarray(t, float); return np.exp(-self._z(t) * t)
    def forward(self, t):
        t = np.asarray(t, float); return self._z(t) + t * self._dz(t)
    def integrated_forward(self, t):
        t = np.asarray(t, float); return self._z(t) * t


def mk(name, z, dz):
    return Analytic(name, z, dz)

CURVES = {
    "upward":      mk("upward",      lambda t: 0.010 + 0.018*(1-np.exp(-t/4.0)),
                                     lambda t: 0.018/4.0*np.exp(-t/4.0)),
    "inverted":    mk("inverted",    lambda t: 0.040 - 0.020*(1-np.exp(-t/5.0)),
                                     lambda t: -0.020/5.0*np.exp(-t/5.0)),
    "humped":      mk("humped",      lambda t: 0.012 + 0.020*(1-np.exp(-t/2.5)) - 0.012*(t/30.0)**1.4,
                                     lambda t: 0.020/2.5*np.exp(-t/2.5) - 0.012*1.4/30.0*(t/30.0)**0.4),
    "steep_front": mk("steep_front", lambda t: 0.004 + 0.026*(1-np.exp(-t/0.6)),
                                     lambda t: 0.026/0.6*np.exp(-t/0.6)),
    "negative":    mk("negative",    lambda t: -0.008 + 0.005*(1-np.exp(-t/6.0)),
                                     lambda t: 0.005/6.0*np.exp(-t/6.0)),
}

DEPOSITS = [1/12, 0.25, 0.5, 0.75, 1.0]
SWAPS    = [1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0]
BONDS    = [(2.44, 0.021), (4.07, 0.023), (7.63, 0.025), (12.24, 0.020),
            (18.42, 0.024), (26.40, 0.030)]
SPARSE_SWAPS = [1.0, 2.0, 5.0, 10.0, 30.0]          # big holes at 3-4Y, 7Y, 12-25Y


def make(kind, T, quote, coupon=None, freq=1, hs=0.001, liq=1.0, oid="O"):
    return Instrument(obs_id=oid, instrument_id=oid, instrument_type=kind,
                      maturity_years=T, coupon_rate=coupon, payment_frequency=freq,
                      quote=quote, half_spread=hs, liquidity_score=liq, weight=1.0,
                      source="S", timestamp="2026-01-15T15:00:00Z")


def market(curve, condition, rng):
    D = lambda t: float(curve.discount(np.array([t]))[0])
    out, k = [], 0
    swaps = SPARSE_SWAPS if condition in ("sparse", "sparse_contam") else SWAPS
    for T in DEPOSITS:
        k += 1
        out.append(make("deposit", T, ((1/D(T) - 1)/T)*100.0, oid=f"D{k:03d}"))
    for T in swaps:
        k += 1
        f = 1 if T <= 2.0 else 2
        ts, a = swap_schedule(T, f)
        out.append(make("ois_swap", T, qp.swap_par_rate(curve, ts, a)*100.0, freq=f, oid=f"S{k:03d}"))
    for T, c in BONDS:
        k += 1
        out.append(make("bond", T, qp.bond_price(curve, bond_schedule(T, 2), c, 2),
                        coupon=c, freq=2, oid=f"B{k:03d}"))
    if condition in ("contaminated", "sparse_contam"):
        # two gross outliers + one moderate, at maturities chosen a priori
        for idx, bump in ((len(out)//2, 0.40), (len(out)-3, -0.35), (2, 0.12)):
            i = out[idx]
            q = i.quote + (bump if i.is_rate_quote else bump*3.0)
            out[idx] = make(i.instrument_type, i.maturity_years, q, i.coupon_rate,
                            i.payment_frequency, i.half_spread, i.liquidity_score, i.obs_id)
    if condition == "illiquid":
        out = [make(i.instrument_type, i.maturity_years, i.quote, i.coupon_rate,
                    i.payment_frequency, hs=0.02 if i.maturity_years > 8 else 0.001,
                    liq=0.12 if i.maturity_years > 8 else 1.0, oid=i.obs_id) for i in out]
    return out


BANDS = (("short", 0.0834, 2.0), ("mid", 2.0, 15.0), ("long", 15.0, 30.0))


def score(fitted, truth):
    res = {}
    for name, lo, hi in BANDS:
        g = np.linspace(lo, hi, 240)
        dz = (np.asarray(fitted.zero(g)) - np.asarray(truth.zero(g))) * 1e4
        df = (np.asarray(fitted.forward(g)) - np.asarray(truth.forward(g))) * 1e4
        res[f"zero_rmse_bp_{name}"] = float(np.sqrt(np.mean(dz**2)))
        res[f"zero_max_bp_{name}"] = float(np.max(np.abs(dz)))
        res[f"fwd_rmse_bp_{name}"] = float(np.sqrt(np.mean(df**2)))
        res[f"fwd_max_bp_{name}"] = float(np.max(np.abs(df)))
    g = np.linspace(0.0834, 30.0, 600)
    res["df_positive"] = bool(np.all(np.asarray(fitted.discount(g)) > 0))
    return res


def run(config, tag, results):
    rng = np.random.default_rng(SEED)
    for cname, curve in CURVES.items():
        for cond in ("clean", "sparse", "contaminated", "illiquid", "sparse_contam"):
            insts = market(curve, cond, rng)
            for model in ("baseline", "advanced"):
                t0 = time.time()
                try:
                    fit = (fit_baseline(insts, config) if model == "baseline"
                           else fit_advanced(insts, config))
                    row = score(fit.curve, curve)
                    row["lambda"] = getattr(fit, "smoothing_lambda", None)
                    row["power"] = getattr(fit, "penalty_power", None)
                    adm = forward_admissibility(fit.curve, insts, 30.0, 2.0)
                    row["forward_admissible"] = adm["admissible"]
                    row["forward_breach_pct"] = adm["breach_percent"]
                except Exception as exc:                       # pragma: no cover
                    row = {"error": f"{type(exc).__name__}: {exc}"}
                row.update(variant=tag, curve=cname, condition=cond, model=model,
                           n_instruments=len(insts), seconds=round(time.time()-t0, 2))
                results.append(row)
    return results


if __name__ == "__main__":
    variant = sys.argv[2] if len(sys.argv) > 2 else "as_is"
    cfg = FitConfig()
    if variant == "one_se":
        cfg = FitConfig(one_se_rule=True)
    elif variant == "lam_floor":
        cfg = FitConfig(lambda_grid=tuple(l for l in FitConfig().lambda_grid if l >= 1e-4))
    rows = run(cfg, variant, [])
    json.dump(rows, open(sys.argv[3], "w"), indent=1, default=float)
    print(f"{variant}: {len(rows)} fits written")
