# ruff: noqa  -- archived working script, kept as run on 2026-09-12
"""Replicate an ETF's daily level from periodic holdings snapshots, shares held constant in between.

usage: python etf_daily2.py <cfg.json>
cfg: etf (yfinance symbol), snapshots (json {date: {ticker: market_value at that close}}), mode ('rebalance' = switch on the
     Monday after the 3rd Friday of the snapshot month; 'snapshot' = switch on the snapshot date), start/end, fee_pct,
     prices ('yf' or a pickle of adjusted closes), ca ({ticker: {to, cash_per_share}} for names delisted mid-interval), out
Position value path: mv_snap * adj[t] / adj[snap]  (split-proof: adjusted closes are on one basis, so no share restatement).
"""
import os
import json, sys
import numpy as np, pandas as pd, yfinance as yf

cfg = json.load(open(sys.argv[1]))
S = os.environ.get('ETF_PE_WORKDIR', './work/')
SNAP = {d: v for d, v in json.load(open(cfg['snapshots'])).items() if d >= cfg['start_snapshot']}
dates = sorted(SNAP)
ETF, START, END, MODE = cfg['etf'], cfg['start'], cfg['end'], cfg['mode']
CA = cfg.get('ca', {})
PROXY = cfg.get('proxy', {})  # {ticker: proxy_ticker} for names with no price history at all (delisted, purged from Yahoo)


def rebalance_effective(d):
    q = pd.Timestamp(d); fridays = pd.date_range(q.replace(day=1), q, freq='W-FRI')
    return (fridays[2] + pd.Timedelta(days=3)).strftime('%Y-%m-%d')


switch = {d: (rebalance_effective(d) if (MODE == 'rebalance' and d != dates[0]) else d) for d in dates}
tickers = sorted({t for s in SNAP.values() for t in s} | {v['to'] for v in CA.values()} | {v for v in PROXY.values() if v != 'CASH'})
if cfg['prices'] == 'yf':
    adj = yf.download(tickers + [ETF], start=dates[0], end=END, auto_adjust=True, progress=False)['Close']
    raw = yf.download(tickers, start=dates[0], end=END, auto_adjust=False, progress=False)['Close']
else:
    adj = pd.read_pickle(cfg['prices']); raw = adj
    extra = [t for t in tickers + [ETF] if t not in adj.columns]
    if extra:
        print('downloading missing', extra)
        more = yf.download(extra, start=dates[0], end=END, auto_adjust=True, progress=False)['Close']
        adj = pd.concat([adj, more], axis=1)
adj = adj.loc[:pd.Timestamp(END) - pd.Timedelta(days=1)]
missing_cols = [t for t in tickers if t not in adj.columns or adj[t].isna().all()]
print('no price data for', missing_cols)
idx = adj.loc[START:].index
adj_f = adj.ffill()

# value paths per basket: DataFrame index=idx, cols=tickers, values = position value
def basket_values(d):
    snap = SNAP[d]; d0 = pd.Timestamp(d); cols = {}; masks = {}; dropped = 0.0; tot = sum(snap.values())
    for t, mv in snap.items():
        if t in PROXY and PROXY[t] == 'CASH' and (t in missing_cols or t not in adj.columns):
            print(f'  {d}: {t} has no price history -> held as cash'); cols[t] = pd.Series(mv, index=idx); masks[t] = pd.Series(True, index=idx); continue
        if t in PROXY and (t in missing_cols or t not in adj.columns):
            print(f'  {d}: {t} has no price history -> proxied by {PROXY[t]} total return'); t_src = PROXY[t]
        else:
            t_src = t
        if t_src in missing_cols or t_src not in adj.columns or pd.isna(adj.at[d0, t_src]):
            dropped += mv; continue
        orig, t = t, t_src
        base = adj.at[d0, t]
        series = mv * adj_f[t].loc[idx] / base
        mask = adj[t].loc[idx].notna()
        last_valid = adj[t].last_valid_index()
        if last_valid is not None and last_valid < idx[-1]:
            tail = idx[idx > last_valid]
            mask.loc[tail] = True
            vL = mv * adj.at[last_valid, t] / base
            if t in CA:
                to, cash = CA[t]['to'], CA[t].get('cash', 0.0)
                cf = cash / raw.at[last_valid, t] if cash else 0.0
                series.loc[tail] = vL * (cf + (1 - cf) * adj_f[to].loc[tail] / adj.at[last_valid, to])
                print(f'  {d}: {t} delisted {last_valid.date()} -> {to} (cash frac {cf:.2f})')
            else:
                series.loc[tail] = vL
                print(f'  {d}: {t} delisted {last_valid.date()} -> held as cash')
        cols[orig] = series; masks[orig] = mask
    if dropped:
        print(f'  {d}: dropped weight {100 * dropped / tot:.2f}% (no price on snapshot date)')
    return pd.DataFrame(cols), pd.DataFrame(masks)

V = {d: basket_values(d) for d in dates}
def basket_change(d, t0, t1):
    vals, m = V[d]; ok = (m.loc[t0] & m.loc[t1]).values
    return vals.loc[t1].values[ok].sum() / vals.loc[t0].values[ok].sum() - 1
etf_px = adj[ETF].loc[START:]
if cfg.get('etf_div_mode') == 'manual':
    etf_px = yf.download([ETF], start=dates[0], end=END, auto_adjust=False, progress=False)['Close'][ETF].loc[START:pd.Timestamp(END) - pd.Timedelta(days=1)]
etf_px = etf_px.reindex(idx)
gaps = [str(t.date()) for t in idx if pd.isna(etf_px[t])]
print('ETF price missing on', len(gaps), 'days:', gaps)
eidx = etf_px.dropna().index
basket_ret = pd.Series(index=eidx, dtype=float); cur = 0
for i in range(1, len(eidx)):
    t0, t1 = eidx[i - 1], eidx[i]
    while cur + 1 < len(dates) and t0 >= pd.Timestamp(switch[dates[cur + 1]]):
        cur += 1
    basket_ret[t1] = basket_change(dates[cur], t0, t1)
etf_ret = etf_px.loc[eidx].pct_change()
if cfg.get('etf_div_mode') == 'manual':
    # Yahoo's adjusted close for JP ETFs books the distribution one business day late (drop on the true ex-date, jump the next day).
    # Rebuild: r_t = (P_t + D_t) / P_{t-1} - 1 with the ex-date located as the day in [D-3, D+1] where ETF-minus-basket is most negative.
    raw_etf = etf_px.loc[eidx]
    divs = yf.Ticker(ETF).dividends
    divs.index = divs.index.tz_localize(None)
    divs = divs.loc[START:]
    r = raw_etf.pct_change()
    tmp = (r - basket_ret).dropna()
    for dd, amt in divs.items():
        win = tmp.loc[dd - pd.Timedelta(days=5):dd + pd.Timedelta(days=2)]
        if not len(win): continue
        ex = win.idxmin()
        r[ex] = (raw_etf[ex] + amt) / raw_etf[raw_etf.index[raw_etf.index.get_loc(ex) - 1]] - 1
        print(f'  ETF distribution {amt} yahoo-dated {dd.date()} -> ex-date located {ex.date()} (drop {100 * win.min():.2f}%)')
    etf_ret = r
    etf_px = raw_etf.iloc[0] * (1 + etf_ret.fillna(0)).cumprod()
df = pd.DataFrame(dict(basket=basket_ret, etf=etf_ret)).dropna()
df['diff_bp'] = 1e4 * (df.etf - df.basket)
rep_level = etf_px.loc[df.index[0]] / (1 + df.etf.iloc[0]) * (1 + df.basket).cumprod()
etf_level = etf_px.loc[df.index]
df['cum_diff_%'] = 100 * (etf_level / rep_level - 1)
n = len(df)
st = dict(corr=round(df.basket.corr(df.etf), 5), mean_bp=round(df.diff_bp.mean(), 2), std_bp=round(df.diff_bp.std(), 2),
          te=round(df.diff_bp.std() * np.sqrt(252) / 100, 2), n=n, over20=int((df.diff_bp.abs() > 20).sum()), over50=int((df.diff_bp.abs() > 50).sum()),
          maxbp=round(df.diff_bp.abs().max(), 1), maxday=str(df.diff_bp.abs().idxmax().date()),
          etf_tr=round(100 * (etf_level.iloc[-1] / etf_level.iloc[0] - 1), 2), rep_tr=round(100 * (rep_level.iloc[-1] / rep_level.iloc[0] - 1), 2),
          cum_end=round(df['cum_diff_%'].iloc[-1], 2), cum_max=round(df['cum_diff_%'].abs().max(), 2), fee=cfg['fee_pct'])
print(f"\n== {ETF} mode={MODE} {df.index[0].date()} -> {df.index[-1].date()} n={n}")
print('corr %.5f  mean %+.2f bp  std %.2f bp  TE %.2f%%/yr  >20bp %d  >50bp %d  max %.1f bp on %s' % (st['corr'], st['mean_bp'], st['std_bp'], st['te'], st['over20'], st['over50'], st['maxbp'], st['maxday']))
print('ETF %+.2f%%  basket %+.2f%%  cum(ETF-rep) %+.2f%%  max|gap| %.2f%%' % (st['etf_tr'], st['rep_tr'], st['cum_end'], st['cum_max']))
intervals = []
bounds = [switch[d] for d in dates] + [str(df.index[-1].date())]
for a, b in zip(bounds[:-1], bounds[1:]):
    seg = df.loc[a:b]
    if len(seg) < 2: continue
    seg = seg.iloc[1:] if seg.index[0] == pd.Timestamp(a) and a != dates[0] else seg
    w = seg.diff_bp.abs().idxmax()
    intervals.append(dict(a=a, b=b, n=len(seg), corr=round(seg.basket.corr(seg.etf), 4), mean=round(seg.diff_bp.mean(), 2), std=round(seg.diff_bp.std(), 2),
                          cum=round(100 * ((1 + seg.etf).prod() / (1 + seg.basket).prod() - 1), 2), wday=str(w.date()), wbp=round(seg.diff_bp[w], 0)))
    print('  %s -> %s n %3d corr %.4f mean %+.2f std %.2f cum %+.2f%% worst %s %+.0f' % tuple(intervals[-1].values()))
worst = df.reindex(df.diff_bp.abs().sort_values(ascending=False).index[:6])
print('worst days:\n' + worst[['basket', 'etf', 'diff_bp']].assign(basket=lambda d: (100 * d.basket).round(2), etf=lambda d: (100 * d.etf).round(2), diff_bp=lambda d: d.diff_bp.round(0)).to_string())
out = cfg['out']
df.to_csv(out + '_tieout.csv'); pd.DataFrame(dict(etf=etf_level, replicated=rep_level)).to_csv(out + '_levels.csv')
chart = dict(etf=ETF, dates=[str(d.date()) for d in df.index], etf_level=[round(float(v), 2) for v in etf_level], rep=[round(float(v), 2) for v in rep_level],
             diff=[round(float(v), 1) for v in df.diff_bp], cum=[round(float(v), 3) for v in df['cum_diff_%']], switches=[switch[d] for d in dates[1:]], stats=st, intervals=intervals,
             worst=[dict(d=str(i.date()), etf=round(100 * r.etf, 2), basket=round(100 * r.basket, 2), bp=round(r.diff_bp, 0)) for i, r in worst.iterrows()])
json.dump(chart, open(out + '_chart.json', 'w'))
