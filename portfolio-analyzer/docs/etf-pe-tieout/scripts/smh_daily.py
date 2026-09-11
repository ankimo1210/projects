# ruff: noqa  -- archived working script, kept as run on 2026-09-11
"""Replicate SMH's daily level from its N-PORT baskets (quarterly snapshots, shares held constant in between)."""
import json, os
import numpy as np, pandas as pd, yfinance as yf

S = os.environ.get('ETF_PE_WORKDIR', './work/')
H = json.load(open(S + 'nport/smh/holdings.json')); F = json.load(open(S + 'figi_map.json'))
START = '2025-06-30'


def key_of(h):
    return h['cusip'] if h['cusip'] and h['cusip'] not in ('N/A', '000000000') else ('ISIN:' + h['isin'] if h['isin'] else 'NAME:' + h['name'])


SPL = json.load(open(S + 'us_splits_smh.json'))


def split_after(t, d):
    f = 1.0
    for sd, r in (SPL.get(t) or {}).items():
        if not sd.startswith('_') and sd > d and r:
            f *= r
    return f


snaps = {}
for rd in sorted(H):
    if rd < START:
        continue
    # N-PORT shares are as of the snapshot; restate onto today's (split-adjusted price) basis
    snaps[rd] = {F[key_of(h)]['ticker']: dict(sh=h['balance'] * split_after(F[key_of(h)]['ticker'], rd), val=h['valUSD']) for h in H[rd]['holdings']}
dates = sorted(snaps)
import sys
MODE = sys.argv[1] if len(sys.argv) > 1 else 'quarter_end'


def rebalance_effective(d):
    """MVIS quarterly review: effective after the close of the 3rd Friday of Mar/Jun/Sep/Dec -> the following Monday."""
    q = pd.Timestamp(d)
    fridays = pd.date_range(q.replace(day=1), q, freq='W-FRI')
    return (fridays[2] + pd.Timedelta(days=3)).strftime('%Y-%m-%d')


# basket k is assumed in force from `switch[k]` (quarter-end snapshot date, or the rebalance effective date of that quarter)
switch = {d: (rebalance_effective(d) if (MODE == 'rebalance' and d != dates[0]) else d) for d in dates}
print('basket switch dates:', switch)
tickers = sorted({t for s in snaps.values() for t in s})
raw = yf.download(tickers + ['SMH'], start='2025-06-20', end='2026-09-12', auto_adjust=False, progress=False)
adj = yf.download(tickers + ['SMH'], start='2025-06-20', end='2026-09-12', auto_adjust=True, progress=False)['Close'].ffill()
close = raw['Close'].ffill()

# 1) consistency: N-PORT implied price vs Yahoo close on the snapshot date
print('== N-PORT price vs Yahoo close on snapshot dates (max |diff|)')
for d in dates:
    diffs = []
    for t, x in snaps[d].items():
        p_np = x['val'] / x['sh']; p_y = close.at[pd.Timestamp(d), t]  # both on today's split basis
        diffs.append((t, round(100 * (p_np / p_y - 1), 2)))
    worst = sorted(diffs, key=lambda z: -abs(z[1]))[:3]
    print(d, 'max|diff|', worst)

# 2) basket total-return path with constant shares between snapshots
idx = adj.loc[START:].index
basket_ret = pd.Series(index=idx, dtype=float)
cur = 0
for i in range(1, len(idx)):
    t0, t1 = idx[i - 1], idx[i]
    # switch to the next basket the day after its snapshot date
    while cur + 1 < len(dates) and t0 >= pd.Timestamp(switch[dates[cur + 1]]):
        cur += 1
    b = snaps[dates[cur]]
    v0 = sum(x['sh'] * adj.at[t0, t] for t, x in b.items()); v1 = sum(x['sh'] * adj.at[t1, t] for t, x in b.items())
    basket_ret[t1] = v1 / v0 - 1
etf_ret = adj['SMH'].loc[START:].pct_change()
df = pd.DataFrame(dict(basket=basket_ret, etf=etf_ret)).dropna()
df['diff_bp'] = 1e4 * (df.etf - df.basket)
rep_level = adj['SMH'].loc[START] * (1 + df.basket).cumprod()
etf_level = adj['SMH'].loc[df.index]
df['cum_diff_%'] = 100 * (etf_level / rep_level - 1)

print('\n== daily tracking (ETF adjusted close vs replicated basket), %s -> %s, %d days' % (df.index[0].date(), df.index[-1].date(), len(df)))
print('corr of daily returns      %.5f' % df.basket.corr(df.etf))
print('mean diff  %+.2f bp/day  (%+.2f %%/yr)' % (df.diff_bp.mean(), df.diff_bp.mean() * 252 / 100))
print('std  diff  %.2f bp/day  (tracking error %.2f %%/yr)' % (df.diff_bp.std(), df.diff_bp.std() * np.sqrt(252) / 100))
print('|diff| > 20bp days: %d   > 50bp: %d   max |diff| %.1f bp on %s' % ((df.diff_bp.abs() > 20).sum(), (df.diff_bp.abs() > 50).sum(), df.diff_bp.abs().max(), df.diff_bp.abs().idxmax().date()))
print('cumulative: ETF %+.2f%%  basket %+.2f%%  -> ETF minus basket %+.2f%% over the period; max |level gap| %.2f%%' % (100 * (etf_level.iloc[-1] / etf_level.iloc[0] - 1), 100 * (rep_level.iloc[-1] / rep_level.iloc[0] - 1), df['cum_diff_%'].iloc[-1], df['cum_diff_%'].abs().max()))
print('\n== per interval (basket held constant)')
bounds = [switch[d] for d in dates] + [str(df.index[-1].date())]
for a, b in zip(bounds[:-1], bounds[1:]):
    seg = df.loc[a:b]
    if len(seg) < 2:
        continue
    seg = seg.iloc[1:] if seg.index[0] == pd.Timestamp(a) and a != START else seg
    print('%s -> %s  days %3d  corr %.4f  mean %+.2f bp  std %.2f bp  cum(ETF-basket) %+.2f%%  worst day %s %+.0f bp' % (a, b, len(seg), seg.basket.corr(seg.etf), seg.diff_bp.mean(), seg.diff_bp.std(), 100 * ((1 + seg.etf).prod() / (1 + seg.basket).prod() - 1), seg.diff_bp.abs().idxmax().date(), seg.diff_bp[seg.diff_bp.abs().idxmax()]))
print('\n== worst 8 days')
print(df.reindex(df.diff_bp.abs().sort_values(ascending=False).index[:8])[['basket', 'etf', 'diff_bp']].assign(basket=lambda d: (100 * d.basket).round(2), etf=lambda d: (100 * d.etf).round(2), diff_bp=lambda d: d.diff_bp.round(0)).to_string())
df.to_csv(S + f'smh_daily_tieout_{MODE}.csv')
pd.DataFrame(dict(etf=etf_level, replicated=rep_level)).to_csv(S + f'smh_daily_levels_{MODE}.csv')

# 3) attribution of the worst day: per-name return contribution in the basket vs the ETF move
wd = df.diff_bp.abs().idxmax(); i = list(idx).index(wd); t0 = idx[i - 1]
cur = max(k for k, d in enumerate(dates) if pd.Timestamp(switch[d]) <= t0) if any(pd.Timestamp(switch[d]) <= t0 for d in dates) else 0
b = snaps[dates[cur]]; v0 = sum(x['sh'] * adj.at[t0, t] for t, x in b.items())
contrib = sorted(((t, 100 * x['sh'] * adj.at[t0, t] / v0, 100 * (adj.at[wd, t] / adj.at[t0, t] - 1)) for t, x in b.items()), key=lambda z: -abs(z[1] * z[2]))
print('\n== worst day %s: ETF %+.2f%% basket %+.2f%%; top contributors (weight%%, ret%%)' % (wd.date(), 100 * df.etf[wd], 100 * df.basket[wd]))
print([(t, round(w, 1), round(r, 2)) for t, w, r in contrib[:8]])
