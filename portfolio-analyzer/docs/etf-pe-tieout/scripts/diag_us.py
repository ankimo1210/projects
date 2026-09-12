# ruff: noqa  -- archived working script, kept as run on 2026-09-12
"""Diagnostics: (a) per-name adj-vs-raw discrepancy inside each interval (flags distributions/spin-offs), (b) ETF vs index."""
import os
import json, sys, pandas as pd, numpy as np, yfinance as yf
S = os.environ.get('ETF_PE_WORKDIR', './work/')
etf=sys.argv[1]; idxsym=sys.argv[2]
SNAP=json.load(open(S+f'snap_{etf.lower()}.json')); dates=sorted(SNAP)
tick=sorted({t for s in SNAP.values() for t in s})
adj=yf.download(tick+[etf,idxsym],start='2025-06-30',end='2026-09-11',auto_adjust=True,progress=False)['Close']
raw=yf.download(tick+[etf,idxsym],start='2025-06-30',end='2026-09-11',auto_adjust=False,progress=False)['Close']
def reb(d):
    q=pd.Timestamp(d); f=pd.date_range(q.replace(day=1),q,freq='W-FRI'); return (f[2]+pd.Timedelta(days=3)).strftime('%Y-%m-%d')
bounds=[dates[0]]+[reb(d) for d in dates[1:]]+['2026-09-10']
print('== adj/raw ratio drift per interval (names with |drift|>1.5%): distributions, spin-offs, split mismatches')
for k,(a,b) in enumerate(zip(bounds[:-1],bounds[1:])):
    snap=SNAP[dates[k]]; tot=sum(snap.values()); rows=[]
    for t,mv in snap.items():
        if t not in adj.columns: continue
        A=adj[t].loc[a:b].dropna(); R=raw[t].loc[a:b].dropna()
        if len(A)<2: continue
        dr=(A.iloc[-1]/A.iloc[0])/(R.iloc[-1]/R.iloc[0])-1
        if abs(dr)>0.015: rows.append((t,round(100*mv/tot,2),round(100*dr,2)))
    print(a,'->',b,sorted(rows,key=lambda r:-abs(r[1]*r[2]))[:8])
print('== ETF (adj) vs index (price) cumulative per interval, % (ETF TR - index PR ~ yield - fee)')
for a,b in zip(bounds[:-1],bounds[1:]):
    e=adj[etf].loc[a:b]; i=raw[idxsym].loc[a:b]
    print(a,'->',b,'ETF %+.2f%%  index %+.2f%%  diff %+.2f%%'%(100*(e.iloc[-1]/e.iloc[0]-1),100*(i.iloc[-1]/i.iloc[0]-1),100*(e.iloc[-1]/e.iloc[0]-i.iloc[-1]/i.iloc[0])))
# daily diff drift check for the interval with the largest mean: cumulative sum path
df=pd.read_csv(S+f'rep_{etf.lower()}_tieout.csv',index_col=0,parse_dates=True)
seg=df.loc['2026-03-23':'2026-06-22']
print('== Q2-2026 cumulative diff path (bp), every 5th day'); print((seg.diff_bp.cumsum().round(0)).iloc[::5].to_string())
