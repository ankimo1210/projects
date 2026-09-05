"""Exploration 1: stale timestamps, bond yields vs OIS, schedule hypotheses for 1.25Y/1.5Y OIS."""
import sys, numpy as np, pandas as pd
from scipy.optimize import brentq
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30); pd.set_option("display.max_rows", 300)
df = pd.read_csv(sys.argv[1])
ts = pd.to_datetime(df.timestamp, utc=True)
print("=== stale-date rows")
print(df[ts.dt.date != pd.Timestamp("2026-01-15").date()][["obs_id","instrument_id","source","timestamp","instrument_type","maturity_years","quote_value","bid","ask","liquidity_score"]].to_string(index=False))

# --- crude OIS zero curve from clean per-tenor medians (excluding obviously bad rows) to test hypotheses
ois = df[(df.instrument_type=="ois_swap")].copy()
ois["q"] = ois.quote_value.fillna((ois.bid+ois.ask)/2)
ois.loc[ois.q < 0.1, "q"] *= 100  # scale fix
ois = ois[ois.q > 1.0]  # drop level-corrupted
med = ois.groupby("maturity_years").q.median()
print("\n=== OIS per-tenor medians (%)"); print(med.to_string())
dep = df[df.instrument_type=="deposit"].copy()
dep = dep[~dep.obs_id.str.startswith("DUP")]
dep["q"] = dep.quote_value.copy(); dep.loc[dep.q<0.1,"q"]*=100
dmed = dep.groupby("maturity_years").q.median()
print("\n=== deposit per-tenor medians (%)"); print(dmed.to_string())

# bootstrap zero (cc) using integer-period tenors only, linear interp in zero rate
knots = {}
for T, r in dmed.items():
    knots[T] = np.log(1 + r/100*T)/T
def zc(t):
    ks = sorted(knots); zs = [knots[k] for k in ks]
    return np.interp(t, ks, zs)
def D(t): return np.exp(-zc(t)*t)
def sched(T, f, mode):
    if mode == "std_short_last":  # forward from 0, short last stub
        n = int(np.floor(T*f + 1e-9)); times = [(i+1)/f for i in range(n)]
        if T - (times[-1] if times else 0) > 1e-9: times.append(T)
        alphas = np.diff([0.0]+times); return np.array(times), alphas
    if mode == "std_short_first":  # backward from T, short first stub
        n = int(np.ceil(T*f - 1e-9)); times = [T - (n-1-i)/f for i in range(n)]
        alphas = np.diff([0.0]+times); return np.array(times), alphas
    if mode == "round_full_alpha_linspace":
        n = max(1, int(round(T*f))); times = np.linspace(T/n, T, n); return times, np.full(n, 1/f)
    if mode == "round_full_alpha_backward":
        n = max(1, int(round(T*f))); times = np.array([T-(n-1-i)/f for i in range(n)]); return times, np.full(n, 1/f)
    if mode == "round_full_alpha_forward":
        n = max(1, int(round(T*f))); times = np.array([(i+1)/f for i in range(n-1)]+[T]); return times, np.full(n, 1/f)
    raise ValueError(mode)
for T in [1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0]:
    f = 1 if T <= 2 else 2
    # sequential bootstrap for this tenor using std schedule (integer tenors only) - solve knot
    if T not in (1.25, 1.5):
        def obj(z):
            knots[T] = z
            times, al = sched(T, f, "std_short_last")
            return med[T]/100*np.sum(al*D(times)) - (1 - D(T))
        knots[T] = brentq(obj, -0.05, 0.2)
print("\n=== bootstrapped zero (cc, %) from deposit+OIS medians (integer tenors)")
print({k: round(v*100,4) for k,v in sorted(knots.items())})
print("\n=== 1.25Y / 1.5Y model par under schedule hypotheses vs market median")
for T in (1.25, 1.5):
    for mode in ["std_short_last","std_short_first","round_full_alpha_linspace","round_full_alpha_backward","round_full_alpha_forward"]:
        times, al = sched(T, 1, mode)
        par = (1 - D(T))/np.sum(al*D(times))*100
        print(f"T={T} {mode:30s} times={np.round(times,3)} alphas={np.round(al,3)} model={par:.4f} market={med[T]:.4f} diff_bp={(par-med[T])*100:.1f}")

# --- bonds: yields and model prices under backward/forward schedules
print("\n=== bonds: price vs model price from bootstrapped OIS curve (backward vs forward coupon schedules)")
b = df[df.instrument_type=="bond"].copy()
b["p"] = b.quote_value.fillna((b.bid+b.ask)/2); b.loc[b.p<10,"p"]*=100
rows=[]
for _,r in b.iterrows():
    T=r.maturity_years; f=int(r.payment_frequency); c=r.coupon_rate*100/f
    # backward
    n=int(np.ceil(T*f-1e-9)); tb=np.array([T-(n-1-i)/f for i in range(n)])
    pv_b=np.sum(c*D(tb))+100*D(T)
    # forward: coupons at i/f up to T, plus final at T
    m=int(np.floor(T*f+1e-9)); tf=[(i+1)/f for i in range(m)]
    if T-(tf[-1] if tf else 0)>1e-9: tf.append(T)
    tf=np.array(tf); pv_f=np.sum(c*D(tf))+100*D(T)
    # ytm (semi-annual comp, backward schedule)
    def pf(y): return np.sum(c*(1+y/f)**(-tb*f))+100*(1+y/f)**(-T*f)-r.p
    y=brentq(pf,-0.05,0.2)
    rows.append(dict(obs=r.obs_id,T=round(T,3),cpn=round(r.coupon_rate*100,3),price=round(r.p,3),pv_back=round(pv_b,3),pv_fwd=round(pv_f,3),res_back=round(r.p-pv_b,3),res_fwd=round(r.p-pv_f,3),ytm=round(y*100,4),ois_z=round(zc(T)*100,4),liq=round(r.liquidity_score,3)))
print(pd.DataFrame(rows).to_string(index=False))
