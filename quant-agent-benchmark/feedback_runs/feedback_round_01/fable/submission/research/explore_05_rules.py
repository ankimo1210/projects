"""Exploration 5: schedule-rule comparison and penalty shape under the full pipeline."""
import sys, time, numpy as np, pandas as pd
from quantcurve.io import load_market_data, parse_valuation_date
from quantcurve.cleaning import clean_market_data
from quantcurve.instruments import build_instrument
from quantcurve.baseline import fit_baseline
from quantcurve.weights import base_scales
from quantcurve.advanced import AdvancedConfig, fit_advanced
from quantcurve.pricing import rate_residual
from quantcurve.curve import PiecewiseLinearZeroCurve
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 300)
df = load_market_data(sys.argv[1]); res = clean_market_data(df, parse_valuation_date("2026-01-15"))
tab = res.instruments; types = tab.instrument_type.to_numpy(); cl = tab.tenor_cluster.to_numpy()
grid = np.array([1/12,0.25,0.5,0.75,1,1.25,1.5,2,3,5,7,8,9,10,15,20,25,30])
rows=[]
for rule in ["round","forward","linspace","ceil"]:
  for power in [1.0, 0.0]:
    insts = [build_instrument(r.instrument_id, r.instrument_type, r.maturity, r.quote, r.frequency, r.coupon_rate, stub_rule=rule) for r in tab.itertuples()]
    flat = PiecewiseLinearZeroCurve(np.array([1.0]), np.array([0.02]))
    base = fit_baseline(insts, 1/base_scales(tab, insts, flat)**2, cl); sc = base_scales(tab, insts, base)
    cfg = AdvancedConfig(penalty_power=power)
    t0=time.time(); adv = fit_advanced(insts, sc, types, cl, 30.0, cfg)
    r = np.array([rate_residual(i,adv.curve)*1e4 for i in insts]); f = adv.fit.robust_factor
    def rm(m): return float(np.sqrt(np.mean(r[m]**2)))
    kept = f>0
    row = dict(rule=rule, power=power, lam=adv.lam, lam_min=adv.cv.lam_min, cv_min=adv.cv.table.cv_score.min(), cv_sel=float(adv.cv.table.set_index("lambda").cv_score[adv.lam]),
        rmse_dep=rm(kept&(types=="deposit")), rmse_ois=rm(kept&(types=="ois_swap")), rmse_bond=rm(kept&(types=="bond")), n_excl=int((f==0).sum()), n_lowfac=int((f<0.5).sum()),
        res_1p25=r[tab.maturity.round(3)==1.25].mean(), res_1p5=r[tab.maturity.round(3)==1.5].mean(), res_7=r[(tab.maturity.round(3)==7.0)].mean(), res_1m=r[tab.maturity.round(3)==0.083].mean(),
        secs=time.time()-t0)
    rows.append(row); print(pd.DataFrame([row]).round(3).to_string(index=False))
    print("   forward %:", np.round(adv.curve.forward(grid)*100,3))
    print("   zero    %:", np.round(adv.curve.zero(grid)*100,4))
    print("   scales", {k: round(v,2) for k,v in adv.fit.type_scale.items()}, "excluded:", tab.instrument_id[f==0].tolist())
print(pd.DataFrame(rows).round(3).to_string(index=False))
