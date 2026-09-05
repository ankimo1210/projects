"""H1/H2: validate the pricing layer in isolation against an INDEPENDENT pricer.

No fitted curve is involved anywhere in this file.  A known analytic discount
function D(T) is handed to both implementations and their outputs compared.  The
reference pricer below is written from CONVENTIONS.md directly and deliberately
shares no schedule/cash-flow code with quantcurve.
"""
from __future__ import annotations
import json, math, sys
import numpy as np

sys.path.insert(0, sys.argv[1])          # submission/src
from quantcurve.curve import DiscountCurve
from quantcurve import pricing as qp
from quantcurve.instruments import Instrument
from quantcurve.conventions import swap_schedule, bond_schedule


# ---------------------------------------------------------------- known curves
class Analytic(DiscountCurve):
    """D(T) from a closed-form zero curve; no interpolation, no fitting."""
    def __init__(self, name, zfun):
        self.name, self._z = name, zfun
    def zero(self, t):
        t = np.asarray(t, float)
        return self._z(t)
    def discount(self, t):
        t = np.asarray(t, float)
        return np.exp(-self._z(t) * t)
    def forward(self, t):                      # f = z + T z'  (central difference)
        t = np.asarray(t, float); h = 1e-6
        return self._z(t) + t * (self._z(t + h) - self._z(t - h)) / (2 * h)
    def integrated_forward(self, t):
        t = np.asarray(t, float)
        return self._z(t) * t


CURVES = {
    "flat_2pc":      Analytic("flat_2pc",      lambda t: np.full_like(t, 0.02)),
    "upward":        Analytic("upward",        lambda t: 0.010 + 0.018 * (1 - np.exp(-t / 4.0))),
    "inverted":      Analytic("inverted",      lambda t: 0.040 - 0.020 * (1 - np.exp(-t / 5.0))),
    "humped":        Analytic("humped",        lambda t: 0.012 + 0.020 * (1 - np.exp(-t / 2.5)) - 0.012 * (t / 30.0) ** 1.4),
    "steep_front":   Analytic("steep_front",   lambda t: 0.004 + 0.026 * (1 - np.exp(-t / 0.6))),
    "negative":      Analytic("negative",      lambda t: -0.008 + 0.005 * (1 - np.exp(-t / 6.0))),
    "double_hump":   Analytic("double_hump",   lambda t: 0.018 + 0.004 * np.sin(t / 3.0) + 0.003 * np.sin(t / 9.0)),
}


# ------------------------------------------------------- independent reference
def ref_schedule(T, freq, rule="round"):
    """Payment dates, backwards from maturity, step 1/freq.  `rule` = period count."""
    x = T * freq
    if rule == "round":
        n = max(1, int(math.floor(x + 0.5)))
    elif rule == "ceil":
        n = max(1, int(math.ceil(x - 1e-12)))
    elif rule == "floor":
        n = max(1, int(math.floor(x + 1e-12)))
    else:
        raise ValueError(rule)
    times = [T - k / freq for k in range(n - 1, -1, -1)]
    return [t for t in times if t > 0.0]


def ref_deposit_rate(D, T):
    return (1.0 / D(T) - 1.0) / T                       # simple interest

def ref_swap_par(D, T, freq, rule="round"):
    ts = ref_schedule(T, freq, rule)
    a = sum((1.0 / freq) * D(t) for t in ts)
    return (1.0 - D(ts[-1])) / a

def ref_bond_price(D, T, coupon, freq, rule="round"):
    ts = ref_schedule(T, freq, rule)
    c = 100.0 * coupon / freq
    return sum(c * D(t) for t in ts) + 100.0 * D(ts[-1])


def inst(kind, T, quote, coupon=None, freq=1):
    return Instrument(obs_id="O", instrument_id="I", instrument_type=kind,
                      maturity_years=T, coupon_rate=coupon, payment_frequency=freq,
                      quote=quote, half_spread=0.001, liquidity_score=1.0, weight=1.0,
                      source="S", timestamp="2026-01-15T15:00:00Z")


def main():
    out = {"curves": {}, "worst": {}, "convention_spread": {}}
    tenors_int = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
    tenors_frac = [0.31, 1.25, 2.440754, 4.066428, 7.63, 12.237805, 18.42, 26.4]

    worst_dep = worst_swp = worst_bnd = 0.0
    for name, curve in CURVES.items():
        D = lambda t: float(curve.discount(np.array([t]))[0])
        rows = []
        for T in tenors_int + tenors_frac:
            # deposits (only quoted to 1Y in this market, but the formula is general)
            r_ref = ref_deposit_rate(D, T)
            r_mod = qp.deposit_simple_rate(curve, T)
            d_dep = abs(r_ref - r_mod) * 1e4
            worst_dep = max(worst_dep, d_dep)

            freq = 1 if T <= 2.0 else 2
            ts, acc = swap_schedule(T, freq)
            s_mod = qp.swap_par_rate(curve, ts, acc)
            s_ref = ref_swap_par(D, T, freq)
            d_swp = abs(s_ref - s_mod) * 1e4
            worst_swp = max(worst_swp, d_swp)

            cpn = 0.025
            bts = bond_schedule(T, 2)
            p_mod = qp.bond_price(curve, bts, cpn, 2)
            p_ref = ref_bond_price(D, T, cpn, 2)
            d_bnd = abs(p_ref - p_mod)
            worst_bnd = max(worst_bnd, d_bnd)

            rows.append({"T": T, "dep_bp": d_dep, "swap_bp": d_swp, "bond_pts": d_bnd,
                         "n_swap_ref": len(ref_schedule(T, freq)), "n_swap_mod": len(ts),
                         "n_bond_ref": len(ref_schedule(T, 2)), "n_bond_mod": len(bts)})
        out["curves"][name] = {
            "max_deposit_bp": max(r["dep_bp"] for r in rows),
            "max_swap_bp": max(r["swap_bp"] for r in rows),
            "max_bond_price_points": max(r["bond_pts"] for r in rows),
            "schedule_mismatches": [r for r in rows
                                    if r["n_swap_ref"] != r["n_swap_mod"]
                                    or r["n_bond_ref"] != r["n_bond_mod"]],
        }
    out["worst"] = {"deposit_bp": worst_dep, "swap_bp": worst_swp,
                    "bond_price_points": worst_bnd}

    # round-trip: quote generated from the curve must reprice to ~0 residual
    rt = []
    for name, curve in CURVES.items():
        D = lambda t: float(curve.discount(np.array([t]))[0])
        for T in [0.5, 1.25, 2.440754, 7.63, 26.4]:
            freq = 1 if T <= 2.0 else 2
            q = ref_swap_par(D, T, freq) * 100.0
            rt.append(abs(qp.residual_bp(curve, inst("ois_swap", T, q, freq=freq))))
            p = ref_bond_price(D, T, 0.025, 2)
            rt.append(abs(qp.residual_bp(curve, inst("bond", T, p, coupon=0.025, freq=2))))
            if T <= 1.0:
                r = ref_deposit_rate(D, T) * 100.0
                rt.append(abs(qp.residual_bp(curve, inst("deposit", T, r))))
    out["round_trip_max_residual_bp"] = max(rt)

    # H2: how much does the undetermined fractional-period rule move a price?
    D = lambda t: float(CURVES["upward"].discount(np.array([t]))[0])
    for T in tenors_frac:
        freq = 1 if T <= 2.0 else 2
        sw = {r: ref_swap_par(D, T, freq, r) * 1e4 for r in ("round", "ceil", "floor")}
        bd = {r: ref_bond_price(D, T, 0.025, 2, r) for r in ("round", "ceil", "floor")}
        out["convention_spread"][f"{T:g}"] = {
            "swap_par_bp": {k: round(v, 4) for k, v in sw.items()},
            "swap_spread_bp_round_vs_others": round(max(abs(sw["round"] - sw["ceil"]),
                                                        abs(sw["round"] - sw["floor"])), 4),
            "bond_price_points": {k: round(v, 6) for k, v in bd.items()},
            "bond_spread_points_round_vs_others": round(max(abs(bd["round"] - bd["ceil"]),
                                                            abs(bd["round"] - bd["floor"])), 6),
        }
    # negative-rate sanity
    neg = CURVES["negative"]
    g = np.linspace(0.05, 30.0, 200)
    out["negative_rate_check"] = {
        "all_discount_factors_positive": bool(np.all(neg.discount(g) > 0)),
        "all_finite": bool(np.all(np.isfinite(neg.discount(g)))),
        "max_abs_bond_price_error_points": max(
            abs(qp.bond_price(neg, bond_schedule(T, 2), 0.02, 2)
                - ref_bond_price(lambda t: float(neg.discount(np.array([t]))[0]), T, 0.02, 2))
            for T in tenors_int + tenors_frac),
    }
    print(json.dumps(out, indent=1, default=float))


main()
