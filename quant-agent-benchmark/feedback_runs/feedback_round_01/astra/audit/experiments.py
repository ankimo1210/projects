"""Predeclared local one-factor experiments. No hidden data or external service."""
from __future__ import annotations
from pathlib import Path
import json, math, time, traceback, hashlib
import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from quantcurve.io import load_market_data
from quantcurve.cleaning import clean_market_data
from quantcurve.curves import CurveBasis
from quantcurve import fitting
from quantcurve.pricing import PricingEngine
from quantcurve.research import maturity_groups, holdout_mask, metrics

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parent
SEED=20260905
VARIANTS={
 'reference':{}, 'simple_baseline':{'kind':'baseline','robust':True},
 'smoothing_lower':{'smoothing':.0001}, 'smoothing_higher':{'smoothing':.01},
 'long_knots_dense':{'knots':'dense'}, 'long_knots_sparse':{'knots':'sparse'},
 'endpoint_flat_zero':{'endpoint':'flat_zero'},
 'long_penalty_taper':{'penalty':'taper'},
 'huber_lower':{'threshold':1.5}, 'huber_higher':{'threshold':4.0},
 'no_robust':{'robust':False},
}
BANDS={'all':lambda t:np.ones(len(t),dtype=bool),'short':lambda t:t<=2,
       'middle':lambda t:(t>2)&(t<15),'long':lambda t:t>=15}


def truth(name,t):
    t=np.asarray(t,dtype=float)
    if name=='flat': z=np.full_like(t,.02); d=np.zeros_like(t)
    elif name=='negative_rising': z=-.006+.022*(1-np.exp(-t/7));d=.022/7*np.exp(-t/7)
    elif name=='inverted': z=.04-.022*(1-np.exp(-t/4));d=-.022/4*np.exp(-t/4)
    elif name=='middle_hump':
        g=np.exp(-((t-7)/2)**2);z=.015+.008*(1-np.exp(-t/5))+.005*g;d=.008/5*np.exp(-t/5)-.005*g*2*(t-7)/4
    elif name=='long_hump':
        g=np.exp(-((t-23)/3)**2);z=.017+.006*(1-np.exp(-t/8))+.004*g;d=.006/8*np.exp(-t/8)-.004*g*2*(t-23)/9
    else:raise ValueError(name)
    return z,z+t*d


def oracle(row,discount,stub='prorated'):
    """Scalar-loop independent cash flows; never calls production schedules."""
    T=float(row.maturity_years);freq=int(row.payment_frequency)
    if row.instrument_type=='deposit':return (1/float(discount(np.array([T]))[0])-1)/T
    dates=[];accrual=[];previous=0.0
    for n in range(1,math.ceil(T*freq)+1):
        now=min(n/freq,T)
        if now<=previous:continue
        dates.append(now);accrual.append(now-previous);previous=now
    ds=discount(np.array(dates));dt=float(discount(np.array([T]))[0])
    if row.instrument_type=='ois_swap':return (1-dt)/sum(a*d for a,d in zip(accrual,ds))
    coupon=float(row.coupon_rate)
    amounts=[]
    for j,a in enumerate(accrual):
        if j==len(accrual)-1 and a < 1/freq-1e-9:
            a=0 if stub=='none' else (1/freq if stub=='full' else a)
        amounts.append(100*coupon*a)
    return sum(c*d for c,d in zip(amounts,ds))+100*dt


def run_pricing(frame):
    out=[]
    for shape in ['flat','negative_rising','inverted','middle_hump','long_hump']:
        discount=lambda t:np.exp(-np.asarray(t)*truth(shape,t)[0])
        for stub in ['prorated','none','full']:
            pred=PricingEngine(frame,bond_stub=stub).quote_from_discount(discount)
            expected=np.array([oracle(r,discount,stub) for r in frame.itertuples()])
            for i,r in enumerate(frame.itertuples()):
                out.append({'shape':shape,'convention':stub,'instrument_id':r.instrument_id,'instrument_type':r.instrument_type,
                            'maturity_years':r.maturity_years,'production_quote':pred[i],'independent_quote':expected[i],
                            'difference':pred[i]-expected[i],'units':'price_points' if r.instrument_type=='bond' else 'annual_decimal'})
    result=pd.DataFrame(out);result.to_csv(AUDIT/'pricing_independent.csv',index=False)
    ok=(abs(result.difference)<=np.where(result.instrument_type=='bond',1e-8,1e-10)).all()
    summary={'passed':bool(ok),'comparisons':len(result),'maximum_rate_difference':float(abs(result.loc[result.instrument_type!='bond','difference']).max()),
             'maximum_price_difference':float(abs(result.loc[result.instrument_type=='bond','difference']).max()),
             'interpretation':'All match the independently implemented provisional cash-flow interpretations. This does not identify the hidden generator convention.',
             'unit_checks':'Original regression suite checks PERCENT, DECIMAL, BPS and PRICE_POINTS/per-face inference. Oracle returns annual decimals for rates and points per 100 for bonds.'}
    (AUDIT/'pricing_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if not ok:raise RuntimeError('Independent pricing gate failed; inspect pricing_independent.csv')
    print('Independent pricing:',summary,flush=True)


class ExperimentalBasis(CurveBasis):
    def __init__(self,kind,horizon,options):
        super().__init__(kind,horizon);self.options=options
        if kind!='advanced':return
        k=self.knots
        if options.get('knots')=='dense':k=np.unique(np.r_[k,17.5,22.5,27.5])
        if options.get('knots')=='sparse':k=np.r_[k[k<15],15,22.5,30,k[k>30]]
        boundary=('natural',(1,np.zeros(len(k)))) if options.get('endpoint')=='flat_zero' else 'natural'
        self.knots=k;self.size=len(k);self.spline=CubicSpline(np.log1p(k),np.eye(len(k)),axis=0,bc_type=boundary)

    def penalty(self):
        p=super().penalty()
        if self.kind=='advanced' and self.options.get('penalty')=='taper':
            t=np.expm1(np.linspace(0,np.log1p(self.horizon),len(p)))
            p=p*np.minimum(1,10/np.maximum(t,1e-12))[:,None]
        return p


def fit_variant(frame,name):
    options=VARIANTS[name].copy();factory=fitting.CurveBasis
    fitting.CurveBasis=lambda kind,horizon:ExperimentalBasis(kind,horizon,options)
    try:
        kwargs={k:v for k,v in options.items() if k in ('smoothing','threshold','kind','robust')}
        kwargs.setdefault('smoothing',.001)
        return fitting.fit_curve(frame,**kwargs)
    finally:fitting.CurveBasis=factory


def observation_metrics(frame,pred):
    result=[];t=frame.maturity_years.to_numpy();err=pred-frame.normalized_quote.to_numpy()
    for band,select in BANDS.items():
        for product in ['all','deposit','ois_swap','bond']:
            m=select(t)&(np.ones(len(t),bool) if product=='all' else frame.instrument_type.to_numpy()==product)
            n=int(m.sum())
            if not n:
                result.append((band,product,'rmse',None,'not_applicable',0));continue
            scaled=err[m]/frame.sigma.to_numpy()[m]; rel=frame.reliability.to_numpy()[m]
            loss=np.where(abs(scaled)<=2.5,scaled**2,5*abs(scaled)-6.25)
            result += [(band,product,'huber_loss',float(np.average(loss,weights=rel)),'dimensionless',n),
                       (band,product,'standardized_rmse',float(np.sqrt(np.average(scaled**2,weights=rel))),'dimensionless',n)]
            if product!='all':
                units='price_points' if product=='bond' else 'bp';e=err[m]*(1 if product=='bond' else 1e4)
                result.extend([(band,product,'rmse',float(np.sqrt(np.mean(e**2))),units,n),
                               (band,product,'median_absolute_error',float(np.median(abs(e))),units,n)])
    return result


def curve_metrics(curve,shape):
    t=np.linspace(1/12,30,721);z,f=truth(shape,t);dz=(curve.zero(t)-z)*1e4;df=(curve.forward(t)-f)*1e4
    result=[]
    for band,select in BANDS.items():
        m=select(t)
        result.extend([(band,'all','zero_rmse',float(np.sqrt(np.mean(dz[m]**2))),'bp',int(m.sum())),
                       (band,'all','forward_rmse',float(np.sqrt(np.mean(df[m]**2))),'bp',int(m.sum())),
                       (band,'all','forward_max_abs_error',float(np.max(abs(df[m]))),'bp',int(m.sum()))])
    return result


def synthetic(frame,shape,condition,index):
    f=frame.copy();rng=np.random.default_rng(SEED+index)
    discount=lambda t:np.exp(-np.asarray(t)*truth(shape,t)[0])
    q=np.array([oracle(r,discount) for r in f.itertuples()])
    q+=rng.normal(0,.2,len(f))*f.sigma.to_numpy()
    if condition=='outliers':
        ix=rng.choice(len(f),6,replace=False)
        q[ix]+=rng.choice([-1,1],len(ix))*np.where(f.iloc[ix].instrument_type.to_numpy()=='bond',1.5,.0025)
    f['normalized_quote']=q
    if condition=='long_illiquid':
        m=f.maturity_years>=15;f.loc[m,'reliability']*=.05;f.loc[m,'sigma']*=4
    f['normalized_bid']=q-f.sigma;f['normalized_ask']=q+f.sigma
    f['base_weight']=f.reliability/f.sigma**2;f['weight']=f.base_weight
    if condition=='remove_10_percent':f=f.drop(f.index[rng.choice(len(f),round(.1*len(f)),replace=False)])
    return f.reset_index(drop=True)


def public_splits(frame):
    groups=maturity_groups(frame);ordered=list(dict.fromkeys(groups))
    result=[]
    for split in range(4):
        test=holdout_mask(frame) if split==0 else (np.isin(groups,ordered[(1 if split==1 else 3):-1:5]) if split<3 else frame.maturity_years.to_numpy()>=20)
        train=~test;embargo=np.zeros(len(frame),bool)
        if split in (1,2,3):
            tt=frame.maturity_years.to_numpy()
            for v in tt[test]:embargo|=abs(tt-v)<=(.03 if v<=2 else (.3 if v<15 else .6))
            train&=~embargo
        result.append((f'S{split}',train,test,embargo&~test))
    (AUDIT/'splits.json').write_text(json.dumps({s:{'train_ids':frame.loc[a,'instrument_id'].tolist(),'test_ids':frame.loc[b,'instrument_id'].tolist(),'embargo_ids':frame.loc[c,'instrument_id'].tolist()} for s,a,b,c in result},indent=2)+'\n')
    return result


def main():
    (AUDIT/'curves').mkdir(exist_ok=True);(AUDIT/'synthetic').mkdir(exist_ok=True)
    raw=load_market_data(ROOT/'submission/data/market_observations.csv');frame,a=clean_market_data(raw,'2026-01-15')
    run_pricing(frame)
    records=[];curve_rows=[];weights=[];timings=[]
    def collect(exp,name,split,target,vals,elapsed,status='passed'):
        for band,product,metric,value,unit,n in vals:
            records.append(dict(experiment_id=exp,comparison_source='reference',changed_factor=name,input_split_id=split,model_kind='baseline' if name=='simple_baseline' else 'advanced',measurement_target=target,maturity_band=band,instrument_type=product,metric_name=metric,unit=unit,after_value=value,before_value=None,n=n,wall_seconds=elapsed,validation_status=status,adoption='pending'))
    for split,train,test,embargo in public_splits(frame):
        for name in VARIANTS:
            started=time.time()
            fit=fit_variant(frame.loc[train].reset_index(drop=True),name)
            q=PricingEngine(frame.loc[test]).quote(fit.curve)
            collect(f'{name}:public:{split}',name,f'public:{split}','public_holdout',observation_metrics(frame.loc[test],q),time.time()-started)
    for name in VARIANTS:
        started=time.time();fit=fit_variant(frame,name)
        collect(f'{name}:public:full',name,'public:full','public_in_sample',observation_metrics(frame,fit.quotes),time.time()-started)
        tt=np.linspace(1/12,30,721)
        for t,z,f in zip(tt,fit.curve.zero(tt),fit.curve.forward(tt)):curve_rows.append({'case':'public','variant':name,'maturity_years':t,'zero_rate':z,'forward_rate':f})
        for i,r in enumerate(frame.itertuples()):weights.append({'variant':name,'instrument_id':r.instrument_id,'instrument_type':r.instrument_type,'maturity_years':r.maturity_years,'sigma':r.sigma,'reliability':r.reliability,'robust_weight':fit.robust_weights[i],'residual':fit.quotes[i]-r.normalized_quote})
    for index,shape in enumerate(['flat','negative_rising','inverted','middle_hump','long_hump']):
        for ci,condition in enumerate(['normal','remove_10_percent','long_illiquid','outliers']):
            case=f'{shape}:{condition}';f=synthetic(frame,shape,condition,index*10+ci)
            f.to_csv(AUDIT/'synthetic'/f'{shape}_{condition}.csv',index=False)
            for name in VARIANTS:
                started=time.time();fit=fit_variant(f,name);elapsed=time.time()-started
                collect(f'{name}:synthetic:{case}',name,case,'synthetic_truth',curve_metrics(fit.curve,shape),elapsed)
                if condition in ('normal','long_illiquid'):
                    tt=np.linspace(1/12,30,721)
                    for t,z,fw,tz,tf in zip(tt,fit.curve.zero(tt),fit.curve.forward(tt),*truth(shape,tt)):
                        curve_rows.append({'case':case,'variant':name,'maturity_years':t,'zero_rate':z,'forward_rate':fw,'truth_zero':tz,'truth_forward':tf})
            print('Completed synthetic condition',case,flush=True)
    data=pd.DataFrame(records)
    keys=['input_split_id','measurement_target','maturity_band','instrument_type','metric_name','unit']
    reference=data[data.changed_factor=='reference'].set_index(keys).after_value
    data['before_value']=[reference.get(tuple(r[k] for k in keys),np.nan) for _,r in data.iterrows()]
    data['improvement_fraction']=np.where(data.before_value.notna()&(data.before_value!=0)&data.after_value.notna(),(data.before_value-data.after_value)/data.before_value,np.nan)
    decisions={}
    for name in VARIANTS:
        d=data[data.changed_factor==name];violations=[]
        synthetic_rows=d[d.measurement_target=='synthetic_truth']
        for metric,floor in [('zero_rmse',.25),('forward_rmse',1.),('forward_max_abs_error',2.)]:
            rows=synthetic_rows[synthetic_rows.metric_name==metric]
            bad=rows[rows.after_value-rows.before_value>np.maximum(.1*rows.before_value,floor)]
            violations.extend(bad[['input_split_id','maturity_band','metric_name','before_value','after_value']].to_dict('records'))
        pub=d[(d.measurement_target=='public_holdout')&(d.metric_name=='rmse')&d.before_value.notna()]
        tolerance=np.maximum(.1*pub.before_value,np.where(pub.unit=='bp',.25,.025))
        bad=pub[pub.after_value-pub.before_value>tolerance]
        violations.extend(bad[['input_split_id','maturity_band','instrument_type','metric_name','before_value','after_value']].to_dict('records'))
        means=d[(d.measurement_target=='public_holdout')&(d.metric_name=='huber_loss')&(d.maturity_band=='all')&(d.instrument_type=='all')]
        before_h=means.before_value.mean();after_h=means.after_value.mean()
        if after_h>1.02*before_h:violations.append({'metric_name':'public_mean_huber_loss','before_value':before_h,'after_value':after_h})
        long=synthetic_rows[(synthetic_rows.metric_name=='zero_rmse')&(synthetic_rows.maturity_band=='long')]
        before=long.before_value.mean();after=long.after_value.mean();improvement=(before-after)/before if before else None
        eligible=bool(name not in ('reference','simple_baseline') and improvement is not None and improvement>=.05 and not violations)
        decisions[name]={'eligible':eligible,'synthetic_long_zero_rmse_before_bp':before,'synthetic_long_zero_rmse_after_bp':after,'synthetic_long_improvement_fraction':improvement,
                         'public_mean_huber_before':before_h,'public_mean_huber_after':after_h,'guardrail_violation_count':len(violations),'violations':violations}
    eligible=[n for n in decisions if decisions[n]['eligible']]
    selected=min(eligible,key=lambda n:decisions[n]['synthetic_long_zero_rmse_after_bp']) if eligible else 'reference'
    for name in VARIANTS:data.loc[data.changed_factor==name,'adoption']='adopted' if name==selected else ('reference' if name=='reference' else 'rejected')
    data.to_csv(AUDIT/'experiments.csv',index=False)
    pd.DataFrame(curve_rows).to_csv(AUDIT/'curve_diagnostics.csv',index=False)
    pd.DataFrame(weights).to_csv(AUDIT/'weight_diagnostics.csv',index=False)
    result={'selected_variant':selected,'decisions':decisions,'conditions':20,'public_splits':4,
            'pricing_unchanged':True,'multi_factor_combination':False,
            'penalty_identity':'z_xx=(1+T)^2 z_TT+(1+T) z_T; original penalty integrates z_xx^2 dT/(1+T). A linear z(T) is not unpenalized. For 1bp/Y slope through 30Y the exact penalty is 480 bp^2, 73.4375% contributed after 15Y.',
            'unverified':'Synthetic curves are internally designed cases used for selection, not hidden-score estimates. Public unit preprocessing uses all visible tape as in the reference.'}
    (AUDIT/'selection.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('SELECTION',selected,flush=True)
    for name,d in decisions.items():print(name,'long zero',d['synthetic_long_zero_rmse_after_bp'],'violations',d['guardrail_violation_count'],flush=True)

if __name__=='__main__':main()
