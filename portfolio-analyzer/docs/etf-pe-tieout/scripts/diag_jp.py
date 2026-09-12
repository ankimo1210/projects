# ruff: noqa  -- archived working script, kept as run on 2026-09-12
"""Is the JP residual basket error or ETF closing-price noise? Compare the same basket against a second ETF on the same index."""
import os
import pandas as pd, numpy as np, yfinance as yf, json
S = os.environ.get('ETF_PE_WORKDIR', './work/')
px=pd.read_pickle(S+'jp_px_adj.pkl')
alt=yf.download(['1321.T','1306.T'],start='2025-06-20',end='2026-09-11',auto_adjust=False,progress=False)['Close']
out={}
for code,alt_code,idx in (('1329','1321.T','^N225'),('1475','1306.T',None)):
    df=pd.read_csv(S+f'rep_{code}_q_tieout.csv',index_col=0,parse_dates=True)
    a=alt[alt_code].reindex(df.index).pct_change()
    d2=1e4*(a-df.basket)
    # drop the alt ETF's own distribution window (Yahoo dates it late): July for both
    divs=yf.Ticker(alt_code).dividends; divs.index=divs.index.tz_localize(None)
    mask=pd.Series(True,index=df.index)
    for dd in divs.index:
        mask.loc[dd-pd.Timedelta(days=6):dd+pd.Timedelta(days=2)]=False
    x=df.diff_bp[mask]; y=d2[mask].dropna(); j=x.index.intersection(y.index); x=x.loc[j]; y=y.loc[j]
    r=dict(alt=alt_code, n=len(j), alt_std=round(y.std(),1), own_std=round(x.std(),1), corr_of_residuals=round(np.corrcoef(x,y)[0,1],3),
           alt_corr=round(a.loc[j].corr(df.basket.loc[j]),5))
    if idx:
        n=px[idx].reindex(df.index).pct_change(); dn=1e4*(n-df.basket)
        # exclude ex-dividend clusters of the constituents (last 2 business days of Mar/Sep and first of Apr/Oct) where a price index must diverge from a TR basket
        ex=dn.index[(dn.index.month.isin([3,9])&(dn.index.day>=27))|(dn.index.month.isin([4,10])&(dn.index.day<=1))]
        dn2=dn.drop(ex).dropna()
        r.update(index=idx, idx_std_all=round(dn.std(),1), idx_std_ex_divdays=round(dn2.std(),1), idx_corr=round(n.corr(df.basket),5), idx_max=round(dn2.abs().max(),1), idx_over20=int((dn2.abs()>20).sum()))
    out[code]=r; print(code,r)
json.dump(out,open(S+'diag_jp.json','w'))
