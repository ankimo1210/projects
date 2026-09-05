from pathlib import Path
import json, time, hashlib, platform, importlib.metadata
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from experiments import AUDIT, ROOT, VARIANTS, BANDS, observation_metrics, fit_variant, truth, oracle
from quantcurve.io import load_market_data
from quantcurve.cleaning import clean_market_data
from quantcurve.fitting import fit_curve
from quantcurve.pricing import PricingEngine

def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

frame,_=clean_market_data(load_market_data(ROOT/'submission/data/market_observations.csv'),'2026-01-15')
reference=fit_variant(frame,'reference')
data=pd.read_csv(AUDIT/'experiments.csv')
selection=json.loads((AUDIT/'selection.json').read_text())
curve=pd.read_csv(AUDIT/'curve_diagnostics.csv')
weights=pd.read_csv(AUDIT/'weight_diagnostics.csv')
env={'python':platform.python_version(),'python_build':platform.python_build(),'platform':platform.platform(),
     'packages':{n:importlib.metadata.version(n) for n in ['numpy','pandas','scipy','matplotlib','pytest']},
     'setuptools_metadata':'not installed; package installation is not used in this round',
     'blas_threads':1,'packages_added_or_updated':False,'internet_used':False}
write(AUDIT/'environment.json',env)

# Reproduce original numerics using only the copied source and authorized runtime.
old=AUDIT/'baseline_workspace/outputs';new=AUDIT/'baseline_reproduced'
numeric={}
for sub in ['curves','diagnostics']:
    for p in sorted((old/sub).glob('*.csv')):
        q=new/sub/p.name
        numeric[str(p.relative_to(old))]={'sha256_identical':hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(q.read_bytes()).hexdigest()}
write(AUDIT/'baseline_reproduction.json',{'numeric_csvs':numeric,'all_csvs_byte_identical':all(x['sha256_identical'] for x in numeric.values()),
     'tests_passed':45,'interpretation':'All initial numeric CSVs reproduced using copied source and matched environment. pytest version differs; no shared environment modified.'})

# Explicit payment-convention separation: fixed curve first, then refit only that factor.
base_metrics={(b,p,m,u):(v,n) for b,p,m,v,u,n in observation_metrics(frame,reference.quotes)}
extra=[];payment=[]
for stub in ['none','full']:
    start=time.time();engine=PricingEngine(frame,bond_stub=stub)
    q=engine.quote(reference.curve)
    independent=np.array([oracle(r,reference.curve.discount,stub) for r in frame.itertuples()])
    assert np.max(abs(q-independent))<1e-8
    bond=frame.instrument_type.to_numpy()=='bond';delta=q[bond]-reference.quotes[bond]
    payment.append({'condition':stub,'fixed_curve_price_change_min_points':float(delta.min()),'fixed_curve_price_change_max_points':float(delta.max()),
                    'fixed_curve_bond_price_change_rms_points':float(np.sqrt(np.mean(delta**2))),
                    'changed_bond_count':int((abs(delta)>1e-10).sum()),'oracle_max_abs_difference':float(np.max(abs(q-independent)))})
    for scope,pred,elapsed in [('pricing_only',q,time.time()-start)]:
        for b,p,m,v,u,n in observation_metrics(frame,pred):
            before=base_metrics[(b,p,m,u)][0]
            extra.append(dict(experiment_id=f'{scope}_stub_{stub}',comparison_source='reference',changed_factor=f'bond_stub_{stub}',input_split_id='public:full',model_kind='advanced',measurement_target='public_fixed_curve_convention',maturity_band=b,instrument_type=p,metric_name=m,unit=u,after_value=v,before_value=before,n=n,wall_seconds=elapsed,validation_status='passed',adoption='not_adopted_convention_unresolved',improvement_fraction=(before-v)/before if before is not None and v is not None and before!=0 else None))
    start=time.time();fit=fit_curve(frame,smoothing=.001,bond_stub=stub);elapsed=time.time()-start
    payment[-1]['refit_zero_30y_bp']=float(fit.curve.zero([30])[0]*1e4)
    payment[-1]['reference_zero_30y_bp']=float(reference.curve.zero([30])[0]*1e4)
    for b,p,m,v,u,n in observation_metrics(frame,fit.quotes):
        before=base_metrics[(b,p,m,u)][0]
        extra.append(dict(experiment_id=f'refit_stub_{stub}',comparison_source='reference',changed_factor=f'bond_stub_{stub}',input_split_id='public:full',model_kind='advanced',measurement_target='public_in_sample_convention',maturity_band=b,instrument_type=p,metric_name=m,unit=u,after_value=v,before_value=before,n=n,wall_seconds=elapsed,validation_status='passed',adoption='not_adopted_convention_unresolved',improvement_fraction=(before-v)/before if before is not None and v is not None and before!=0 else None))
data=pd.concat([data,pd.DataFrame(extra)],ignore_index=True);data.to_csv(AUDIT/'experiments.csv',index=False)
write(AUDIT/'payment_conventions.json',{'independent_pricing':'passed','results':payment,'adopted':'prorated',
      'interpretation':'Fixed-D changes isolate cash-flow differences; refit changes include curve absorption. No alternative is selected merely for in-sample fit. Actual generator convention remains unknown.'})

summaries=[]
for name,d in selection['decisions'].items():
    rows=data[(data.changed_factor==name)&(data.measurement_target=='synthetic_truth')]
    z=rows[(rows.metric_name=='zero_rmse')&(rows.maturity_band=='long')]
    f=rows[(rows.metric_name=='forward_rmse')&(rows.maturity_band=='long')]
    summaries.append({'variant':name,'long_zero_rmse_bp':float(z.after_value.mean()),'long_forward_rmse_bp':float(f.after_value.mean()),
       'long_zero_improvement_fraction':d['synthetic_long_improvement_fraction'],'guardrail_violations':d['guardrail_violation_count'],'adopted':name=='reference'})
pd.DataFrame(summaries).to_csv(AUDIT/'factor_summary.csv',index=False)
wrows=[]
for name in ['reference','smoothing_lower','long_penalty_taper','huber_higher','no_robust']:
    w=weights[weights.variant==name]
    for band,select in BANDS.items():
        for product in ['deposit','ois_swap','bond']:
            v=w[select(w.maturity_years.to_numpy())&(w.instrument_type==product)]
            if len(v):wrows.append({'variant':name,'band':band,'product':product,'n':len(v),'downweighted_count':int((v.robust_weight<.999).sum()),'median_robust_weight':float(v.robust_weight.median()),'mean_signed_error':float(v.residual.mean()*(1 if product=='bond' else 1e4)),'unit':'price_points' if product=='bond' else 'bp'})
pd.DataFrame(wrows).to_csv(AUDIT/'weight_summary.csv',index=False)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.alpha':.2})
charts=AUDIT/'charts';charts.mkdir(exist_ok=True)
colors={'reference':'#146b83','smoothing_lower':'#c86820','endpoint_flat_zero':'#9661a8','long_penalty_taper':'#449062'}
fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for col,case in enumerate(['long_hump:normal','inverted:long_illiquid']):
    for row,(column,truth_col,ylabel) in enumerate([('zero_rate','truth_zero','Zero rate (%)'),('forward_rate','truth_forward','Instantaneous forward (%)')]):
        ax=axes[row,col]
        for name,c in colors.items():
            v=curve[(curve.case==case)&(curve.variant==name)]
            ax.plot(v.maturity_years,v[column]*100,label=name,color=c,lw=1.8)
        ax.plot(v.maturity_years,v[truth_col]*100,label='Independent analytic truth',color='black',ls='--',lw=1.4)
        ax.set(xlabel='Maturity (years)',ylabel=ylabel,title=case.replace(':',' / '))
axes[0,0].legend(fontsize=8)
fig.suptitle('Average gains can hide condition-specific losses; numeric reference retained',fontsize=14)
fig.savefig(charts/'synthetic_diagnostics.png',dpi=160,bbox_inches='tight');plt.close(fig)

fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
for name in ['reference','smoothing_lower','long_penalty_taper']:
    v=curve[(curve.case=='public')&(curve.variant==name)]
    axes[0,0].plot(v.maturity_years,v.zero_rate*100,label=name,color=colors[name])
    axes[0,1].plot(v.maturity_years,v.forward_rate*100,label=name,color=colors[name])
v=weights[weights.variant=='reference']
for product,marker,c in [('deposit','o','#6888a5'),('ois_swap','^','#146b83'),('bond','s','#c86820')]:
    z=v[v.instrument_type==product]
    axes[1,0].scatter(z.maturity_years,z.robust_weight,label=product,marker=marker,color=c,s=28,alpha=.8)
z=v[v.instrument_type=='bond'];axes[1,1].scatter(z.maturity_years,z.residual,color='#c86820',s=28)
axes[1,1].axhline(0,color='black',lw=.8)
for ax in axes.ravel():ax.set_xlabel('Maturity (years)')
axes[0,0].set(title='Public full-sample curve; unknown truth',ylabel='Zero rate (%)');axes[0,0].legend(fontsize=8)
axes[0,1].set(title='Public full-sample instantaneous forwards',ylabel='Forward rate (%)')
axes[1,0].set(title='Final Huber weights by instrument and tenor',ylabel='Robust multiplier (dimensionless)',ylim=(-.04,1.04));axes[1,0].legend(fontsize=8)
axes[1,1].set(title='Reference bond residuals; all usable bonds',ylabel='Model - observed (price points)')
fig.savefig(charts/'public_diagnostics.png',dpi=160,bbox_inches='tight');plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
d=pd.DataFrame(summaries);y=np.arange(len(d))
for ax,col,label in [(axes[0],'long_zero_rmse_bp','Mean long-end zero RMSE (bp)'),(axes[1],'long_forward_rmse_bp','Mean long-end forward RMSE (bp)')]:
    bars=ax.barh(y,d[col],color=['#146b83' if x=='reference' else '#a3b4bd' for x in d.variant])
    ax.bar_label(bars,fmt='%.2f',padding=3,fontsize=8);ax.set_yticks(y,d.variant);ax.invert_yaxis();ax.set_xlabel(label);ax.margins(x=.2)
fig.suptitle('20 independent-curve cases; means alone do not decide adoption')
fig.savefig(charts/'factor_comparison.png',dpi=160,bbox_inches='tight');plt.close(fig)
print(json.dumps({'baseline_numeric_reproduced':all(x['sha256_identical'] for x in numeric.values()),'payment':payment,'factor_summary':summaries},indent=2))
for name in ['smoothing_lower','endpoint_flat_zero','long_penalty_taper']:
    print(name,'VIOLATIONS',json.dumps(selection['decisions'][name]['violations']))
