"""Pricing-only interpretation check; no adoption or curve tuning."""
from pathlib import Path
import time,json
import numpy as np
import pandas as pd
from experiments import AUDIT,ROOT,fit_variant,observation_metrics,truth
from quantcurve.cleaning import clean_market_data
from quantcurve.io import load_market_data
from quantcurve.pricing import PricingEngine

f,_=clean_market_data(load_market_data(ROOT/'submission/data/market_observations.csv'),'2026-01-15')
start=time.time();fit=fit_variant(f,'reference');q=fit.quotes.copy();differences=[]
for shape in ['reference','flat','negative_rising','inverted','middle_hump','long_hump']:
    D=fit.curve.discount if shape=='reference' else lambda t:np.exp(-np.asarray(t)*truth(shape,t)[0])
    regular=PricingEngine(f).quote_from_discount(D)
    for i,r in enumerate(f.itertuples()):
        if r.instrument_type!='ois_swap' or r.maturity_years<=2:continue
        T=r.maturity_years
        times=np.r_[1.,2.,np.arange(2.5,T,0.5),T]
        times=np.unique(times);alpha=np.diff(np.r_[0.,times])
        alternative=(1-D(np.array([T]))[0])/sum(alpha*D(times))
        differences.append({'curve':shape,'instrument_id':r.instrument_id,'maturity_years':T,
                             'whole_leg_frequency_quote':regular[i],'annual_to_2y_then_semiannual_quote':alternative,
                             'quote_change_bp':(alternative-regular[i])*1e4})
        if shape=='reference':q[i]=alternative
pd.DataFrame(differences).to_csv(AUDIT/'ois_frequency_difference.csv',index=False)
before={(b,p,m,u):v for b,p,m,v,u,n in observation_metrics(f,fit.quotes)}
rows=[]
for b,p,m,v,u,n in observation_metrics(f,q):
    a=before[b,p,m,u]
    rows.append(dict(experiment_id='pricing_only_ois_mixed_frequency',comparison_source='reference',changed_factor='annual_to_2y_then_semiannual',input_split_id='public:full',model_kind='advanced',measurement_target='public_fixed_curve_convention',maturity_band=b,instrument_type=p,metric_name=m,unit=u,before_value=a,after_value=v,n=n,wall_seconds=time.time()-start,validation_status='passed',adoption='not_adopted_convention_unresolved',improvement_fraction=(a-v)/a if a is not None and v is not None and a!=0 else None))
data=pd.read_csv(AUDIT/'experiments.csv');data=pd.concat([data,pd.DataFrame(rows)],ignore_index=True);data.to_csv(AUDIT/'experiments.csv',index=False)
d=pd.DataFrame(differences);public=d[d.curve=='reference']
summary={'condition':'OIS fixed payments annual until 2Y then semiannual; curve fixed; original uses payment_frequency over entire leg',
         'affected_public_swaps':len(public),'reference_curve_min_quote_change_bp':float(public.quote_change_bp.min()),
         'reference_curve_max_quote_change_bp':float(public.quote_change_bp.max()),
         'all_analytic_curves_max_abs_quote_change_bp':float(abs(d.quote_change_bp).max()),
         'adopted':False,'interpretation':'Ambiguous prose alone is insufficient to replace observed payment_frequency. This prices the alternative only; its calibration and contractual correctness remain unverified.'}
(AUDIT/'ois_convention_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
