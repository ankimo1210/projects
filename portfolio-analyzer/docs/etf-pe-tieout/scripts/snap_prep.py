# ruff: noqa  -- archived working script, kept as run on 2026-09-12
"""Build {date: {ticker: market_value}} snapshot files for each ETF (US from N-PORT, JP from iShares holdings CSVs)."""
import os
import json, glob, csv, io, re
S = os.environ.get('ETF_PE_WORKDIR', './work/')
F=json.load(open(S+'figi_map.json'))
def key_of(h): return h['cusip'] if h['cusip'] and h['cusip'] not in ('N/A','000000000') else ('ISIN:'+h['isin'] if h['isin'] else 'NAME:'+h['name'])
XLE={'APA Corp':'APA','Baker Hughes Co':'BKR','Expand Energy Corp':'EXE','Chevron Corp':'CVX','ConocoPhillips':'COP','Coterra Energy Inc':'CTRA','Devon Energy Corp':'DVN','Diamondback Energy Inc':'FANG','EOG Resources Inc':'EOG','EQT Corp':'EQT','Exxon Mobil Corp':'XOM','Halliburton Co':'HAL','Hess Corp':'HES','Kinder Morgan Inc':'KMI','Marathon Petroleum Corp':'MPC','Occidental Petroleum Corp':'OXY','ONEOK Inc':'OKE','Phillips 66':'PSX','Schlumberger NV':'SLB','SLB Ltd':'SLB','Targa Resources Corp':'TRGP','Texas Pacific Land Corp':'TPL','Valero Energy Corp':'VLO','Williams Cos Inc/The':'WMB'}
for etf in ('smh','qqq','xle'):
    H=json.load(open(S+f'nport/{etf}/holdings.json')); out={}
    for d in sorted(H):
        if d<'2025-06-30': continue
        snap={}
        for h in H[d]['holdings']:
            if h['valUSD']<=0: continue
            t=(F.get(key_of(h)) or {}).get('ticker') if etf!='xle' else XLE.get(h['name'])
            if not t: print('UNMAPPED',etf,d,h['name']); continue
            snap[t]=snap.get(t,0)+h['valUSD']
        out[d]=snap
    json.dump(out,open(S+f'snap_{etf}.json','w')); print(etf,{d:len(v) for d,v in out.items()})
# JP: iShares holdings CSV (UTF-8 BOM); keep equities only
for code in ('1329','1475'):
    out={}; skipped={}
    for f in sorted(glob.glob(S+f'jp_hold/{code}_*.csv')):
        d=re.search(r'_(\d{8})\.csv',f).group(1); d=f'{d[:4]}-{d[4:6]}-{d[6:]}'
        txt=open(f,encoding='utf-8-sig').read()
        lines=txt.splitlines(); hdr=[i for i,l in enumerate(lines) if l.startswith('Ticker,')][0]
        rows=list(csv.DictReader(io.StringIO('\n'.join(lines[hdr:]))))
        snap={}
        for r in rows:
            ac=r.get('Asset Class') or ''; mv=(r.get('Market Value') or '').replace(',','').replace('"','')
            try: mv=float(mv)
            except: continue
            if ac!='株式': skipped[ac]=skipped.get(ac,0)+1; continue
            t=r['Ticker'].strip()+'.T'
            snap[t]=snap.get(t,0)+mv
        out[d]=snap
    json.dump(out,open(S+f'snap_{code}.json','w')); print(code,{d:len(v) for d,v in out.items()},'skipped classes',skipped)
    print('  sample row keys',list(rows[0].keys()), rows[0])
