"""Exploration 3: first end-to-end fit on the benchmark data (baseline + advanced)."""
import sys, time, numpy as np, pandas as pd
from quantcurve.io import load_market_data, parse_valuation_date
from quantcurve.cleaning import clean_market_data
from quantcurve.instruments import build_instrument
from quantcurve.baseline import fit_baseline
from quantcurve.weights import base_scales
from quantcurve.advanced import AdvancedConfig, fit_advanced
from quantcurve.pricing import rate_residual, model_quote
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
df = load_market_data(sys.argv[1]); res = clean_market_data(df, parse_valuation_date("2026-01-15"))
tab = res.instruments
insts = [build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate) for r in tab.itertuples()]
types = tab.instrument_type.to_numpy(); cl = tab.tenor_cluster.to_numpy()
# provisional weights for baseline: liquidity/(spread^2+tau^2) using a flat reference
from quantcurve.curve import PiecewiseLinearZeroCurve
flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([0.02]))
sc0 = base_scales(tab, insts, flat)
t0=time.time(); base = fit_baseline(insts, 1/sc0**2, cl); print("baseline knots", np.round(base.knots,3)); print("baseline zeros %", np.round(base.zeros*100,4), f"{time.time()-t0:.2f}s")
sc = base_scales(tab, insts, base)
cfg = AdvancedConfig()
t0=time.time(); adv = fit_advanced(insts, sc, types, cl, 30.0, cfg); print(f"advanced fit {time.time()-t0:.1f}s lambda={adv.lam:g} (min {adv.cv.lam_min:g}) iters={adv.fit.iterations} conv={adv.fit.converged}")
print("knots", adv.knots)
print(adv.cv.table[["lambda","cv_score"]].to_string(index=False))
print("type scales", adv.fit.type_scale)
grid = np.array([1/12,0.25,0.5,0.75,1,1.25,1.5,2,2.5,3,4,5,6,7,8,9,10,12,15,20,25,30])
print(pd.DataFrame({"t":grid,"base_z":base.zero(grid)*100,"adv_z":adv.curve.zero(grid)*100,"adv_f":adv.curve.forward(grid)*100,"base_f":base.forward(grid)*100}).round(4).to_string(index=False))
out = pd.DataFrame({"id":tab.instrument_id,"type":types,"T":tab.maturity.round(3),"quote":tab.quote_norm.round(4),
  "res_bp_adv":[rate_residual(i,adv.curve)*1e4 for i in insts],"res_bp_base":[rate_residual(i,base)*1e4 for i in insts],
  "u":adv.fit.std_residuals,"factor":adv.fit.robust_factor,"scale_bp":sc*1e4})
print(out.round(3).to_string(index=False))
