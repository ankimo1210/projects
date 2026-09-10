"""Exploration 4: CV table with fold scores; residual summary at selected lambda; 1.5Y schedule variants."""
import sys, time, numpy as np, pandas as pd
from quantcurve.io import load_market_data, parse_valuation_date
from quantcurve.cleaning import clean_market_data
from quantcurve.instruments import build_instrument
from quantcurve.baseline import fit_baseline
from quantcurve.weights import base_scales
from quantcurve.advanced import AdvancedConfig, fit_advanced
from quantcurve.pricing import rate_residual, model_quote
from quantcurve.curve import PiecewiseLinearZeroCurve
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
df = load_market_data(sys.argv[1]); res = clean_market_data(df, parse_valuation_date("2026-01-15"))
tab = res.instruments
insts = [build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate) for r in tab.itertuples()]
types = tab.instrument_type.to_numpy(); cl = tab.tenor_cluster.to_numpy()
flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([0.02]))
base = fit_baseline(insts, 1/base_scales(tab, insts, flat)**2, cl)
sc = base_scales(tab, insts, base)
t0=time.time(); adv = fit_advanced(insts, sc, types, cl, 30.0, AdvancedConfig()); print(f"fit {time.time()-t0:.1f}s lambda={adv.lam:g} (min {adv.cv.lam_min:g}, thr {adv.cv.threshold:.4f}) iters={adv.fit.iterations} conv={adv.fit.converged}")
t = adv.cv.table.copy(); t["fold_scores"] = t.fold_scores.apply(lambda f: np.round(f,3).tolist()); print(t.to_string(index=False))
print("type scales", adv.fit.type_scale)
grid = np.array([1/12,0.25,0.5,0.75,1,1.25,1.5,2,2.5,3,4,5,6,7,8,9,10,12,15,20,25,30])
print(pd.DataFrame({"t":grid,"base_z":base.zero(grid)*100,"adv_z":adv.curve.zero(grid)*100,"adv_f":adv.curve.forward(grid)*100}).round(4).to_string(index=False))
r = np.array([rate_residual(i,adv.curve)*1e4 for i in insts])
out = pd.DataFrame({"id":tab.instrument_id,"type":types,"T":tab.maturity.round(3),"res_bp":r.round(2),"u":adv.fit.std_residuals.round(2),"factor":adv.fit.robust_factor.round(3)})
print(out[(np.abs(out.u)>2)|(out.factor<0.5)].to_string(index=False))
for t_ in ["deposit","ois_swap","bond"]:
    m=(types==t_)&(adv.fit.robust_factor>0); print(t_, "rmse bp (kept)", np.sqrt(np.mean(r[m]**2)).round(3), "max", np.abs(r[m]).max().round(2), "n", m.sum())
# 1.5Y under alternative schedules with the fitted curve
from quantcurve.conventions import schedule_times
for rule in ["round","ceil","linspace"]:
    for T in (1.25,1.5):
        ins = build_instrument("x","ois_swap",T,0.016,1,stub_rule=rule); print(rule, T, np.round(ins.times,3), "model par %", round(model_quote(ins, adv.curve)*100,4))
