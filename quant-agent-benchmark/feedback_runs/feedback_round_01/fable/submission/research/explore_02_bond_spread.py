"""Exploration 2: z-spreads of bonds over a crude OIS/deposit bootstrapped curve (backward coupon schedule)."""
import sys, numpy as np, pandas as pd
from scipy.optimize import brentq
pd.set_option("display.width", 250)
df = pd.read_csv(sys.argv[1])
ts = pd.to_datetime(df.timestamp, utc=True)
df = df[(ts.dt.date == pd.Timestamp("2026-01-15").date()) & ~df.obs_id.str.startswith("DUP")]
ois = df[df.instrument_type=="ois_swap"].copy(); ois["q"]=ois.quote_value.fillna((ois.bid+ois.ask)/2); ois.loc[ois.q<0.1,"q"]*=100; ois=ois[ois.q>1]
dep = df[df.instrument_type=="deposit"].copy(); dep["q"]=dep.quote_value; dep.loc[dep.q<0.1,"q"]*=100
med = ois.groupby("maturity_years").q.median(); dmed = dep.groupby("maturity_years").q.median()
knots={T: np.log(1+r/100*T)/T for T,r in dmed.items()}
def zc(t):
    ks=sorted(knots); return np.interp(t, ks, [knots[k] for k in ks])
def D(t, s=0.0): return np.exp(-(zc(t)+s)*t)
def ois_sched(T,f):
    n=max(1,int(round(T*f))); return np.array([T-(n-1-i)/f for i in range(n)]), np.full(n,1/f)
for T in sorted(med.index):
    f=1 if T<=2 else 2
    def obj(z):
        knots[T]=z; t,a=ois_sched(T,f); return med[T]/100*np.sum(a*D(t))-(1-D(T))
    knots[T]=brentq(obj,-0.05,0.2)
print("zero knots (cc %):", {k: round(v*100,3) for k,v in sorted(knots.items())})
b=df[df.instrument_type=="bond"].copy(); b["p"]=b.quote_value.fillna((b.bid+b.ask)/2); b.loc[b.p<10,"p"]*=100
out=[]
for _,r in b.iterrows():
    T=r.maturity_years; f=int(r.payment_frequency); c=r.coupon_rate*100/f
    n=int(np.ceil(T*f-1e-9)); t=np.array([T-(n-1-i)/f for i in range(n)])
    def pv(s): return np.sum(c*D(t,s))+100*D(T,s)-r.p
    s=brentq(pv,-0.05,0.05)
    dur = -(np.sum(c*t*D(t))+100*T*D(T))/ (np.sum(c*D(t))+100*D(T))
    out.append(dict(obs=r.obs_id,T=round(T,2),zspread_bp=round(s*1e4,1),price=round(r.p,3),pv0=round(pv(0)+r.p,3),res_pts=round(-pv(0),3),liq=round(r.liquidity_score,2),spr=round(r.ask-r.bid,3)))
o=pd.DataFrame(out); print(o.to_string(index=False))
print("\nmedian z-spread bp:", o.zspread_bp.median(), " MAD bp:", (o.zspread_bp-o.zspread_bp.median()).abs().median())
print("excluding |z|>12bp: median", o[o.zspread_bp.abs()<12].zspread_bp.median(), "mean", o[o.zspread_bp.abs()<12].zspread_bp.mean().round(2), "n", (o.zspread_bp.abs()<12).sum())
