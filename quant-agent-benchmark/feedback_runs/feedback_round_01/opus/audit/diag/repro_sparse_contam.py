"""Minimal reproduction of the one condition where the advanced fit degrades.

Five swap pillars (1, 2, 5, 10, 30Y) plus deposits and bonds, one +40bp gross
outlier planted at 5Y -- a maturity with no near neighbour.  Reported: what the
robust estimator does with an outlier it cannot triangulate against anything.
"""
from __future__ import annotations
import sys
import numpy as np
sys.path.insert(0, sys.argv[1])
from quantcurve.curve import DiscountCurve
from quantcurve.instruments import Instrument
from quantcurve.conventions import swap_schedule
from quantcurve import pricing as qp
from quantcurve.models import FitConfig, fit_advanced


class Up(DiscountCurve):
    def zero(self, t):
        t = np.asarray(t, float); return 0.010 + 0.018 * (1 - np.exp(-t / 4.0))
    def discount(self, t):
        t = np.asarray(t, float); return np.exp(-self.zero(t) * t)
    def forward(self, t):
        t = np.asarray(t, float); return self.zero(t) + t * (0.018 / 4.0 * np.exp(-t / 4.0))
    def integrated_forward(self, t):
        t = np.asarray(t, float); return self.zero(t) * t


truth = Up()
def mk(T, q, freq, oid):
    return Instrument(obs_id=oid, instrument_id=oid, instrument_type="ois_swap",
                      maturity_years=T, coupon_rate=None, payment_frequency=freq,
                      quote=q, half_spread=0.001, liquidity_score=1.0, weight=1.0,
                      source="S", timestamp="2026-01-15T15:00:00Z")

def build(outlier_bp):
    insts = []
    for k, T in enumerate([1.0, 2.0, 5.0, 10.0, 30.0]):
        f = 1 if T <= 2 else 2
        ts, a = swap_schedule(T, f)
        q = qp.swap_par_rate(truth, ts, a) * 100.0
        if T == 5.0:
            q += outlier_bp / 100.0
        insts.append(mk(T, q, f, f"S{k}"))
    return insts

grid = np.linspace(0.5, 30.0, 300)
print(f"{'outlier':>9} {'lambda':>9} {'zeroRMSE':>9} {'fwdRMSE':>9} {'fwdMAX':>9} {'w@5Y':>7}")
for bp in (0.0, 10.0, 40.0):
    for tag, cfg in (("cv-min", FitConfig()), ("1-SE", FitConfig(one_se_rule=True))):
        insts = build(bp)
        fit = fit_advanced(insts, cfg)
        dz = (np.asarray(fit.curve.zero(grid)) - np.asarray(truth.zero(grid))) * 1e4
        df = (np.asarray(fit.curve.forward(grid)) - np.asarray(truth.forward(grid))) * 1e4
        w5 = float(fit.robust_weights[2])
        print(f"{bp:>6.0f}bp {tag:>7} {fit.smoothing_lambda:>9.0e} "
              f"{np.sqrt(np.mean(dz**2)):9.2f} {np.sqrt(np.mean(df**2)):9.2f} "
              f"{np.max(np.abs(df)):9.2f} {w5:7.3f}")
