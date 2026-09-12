# ruff: noqa  -- archived working script, kept as run on 2026-09-12
import os
import json, pandas as pd, yfinance as yf, time
S = os.environ.get('ETF_PE_WORKDIR', './work/')
H=json.load(open(S+'jp_holdings.json')); syms=sorted(set(H['h1329'])|set(H['h1475'])|{'1329.T','1475.T','^N225'})
frames=[]
for i in range(0,len(syms),200):
    chunk=syms[i:i+200]
    for attempt in range(3):
        try:
            df=yf.download(chunk, start='2025-06-20', end='2026-09-12', auto_adjust=True, progress=False, threads=True)['Close']
            frames.append(df); print('chunk',i,df.shape, flush=True); break
        except Exception as e:
            print('retry',i,repr(e)[:100], flush=True); time.sleep(20)
    time.sleep(2)
px=pd.concat(frames,axis=1); px=px.loc[:,~px.columns.duplicated()]
px.to_pickle(S+'jp_px_adj.pkl'); print('ADJ-DONE', px.shape, 'all-nan cols', int(px.isna().all().sum()), flush=True)
