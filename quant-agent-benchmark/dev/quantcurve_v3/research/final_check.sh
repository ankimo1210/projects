#!/bin/sh
# Final verification of the development version: tests, clean-state CLI on the public data, determinism, schema checks.
set -e
DEV=$(cd "$(dirname "$0")/.." && pwd)
PYBIN=${PYTHON_BIN:-python}
PUB=${1:?usage: final_check.sh <market_observations.csv>}
export PYTHONDONTWRITEBYTECODE=1
cd "$DEV"
PYTHONPATH=src "$PYBIN" -m pytest -p no:cacheprovider -q tests
rm -rf outputs reports .tmp/final_b
PYTHONPATH=src "$PYBIN" -m quantcurve.cli run --market-data "$PUB" --output-dir "$DEV/outputs" --valuation-date 2026-01-15 --report-dir "$DEV/reports"
PYTHONPATH=src "$PYBIN" -m quantcurve.cli run --market-data "$PUB" --output-dir "$DEV/.tmp/final_b" --valuation-date 2026-01-15 --report-dir "$DEV/.tmp/final_b/reports" --quiet
for f in curves/curve.csv diagnostics/cleaning.csv diagnostics/repricing.csv diagnostics/risk.csv diagnostics/model_comparison.json diagnostics/sensitivity.json charts/curve.png; do
  cmp -s "outputs/$f" ".tmp/final_b/$f" && echo "deterministic: $f" || { echo "NOT deterministic: $f"; exit 1; }
done
PYTHONPATH=src "$PYBIN" - <<'PY'
import json, numpy as np, pandas as pd
c=pd.read_csv("outputs/curves/curve.csv"); t=c.maturity_years.to_numpy()
assert len(c)>=361 and t[0]<=1/12+1e-9 and t[-1]>=30-1e-9 and c.maturity_years.is_monotonic_increasing and np.isfinite(c.to_numpy()).all() and (c.discount_factor>0).all()
assert np.any(np.abs(t-1/12)<1e-9)
ld=np.log(c.discount_factor.to_numpy()); fd=-(ld[2:]-ld[:-2])/(t[2:]-t[:-2]); assert np.abs(fd-c.forward_rate.to_numpy()[1:-1]).max()*1e4 < 0.5
for f,cols in (("diagnostics/cleaning.csv",{"obs_id","instrument_id","action","normalized_quote","weight","reason"}),("diagnostics/repricing.csv",{"instrument_id","instrument_type","market_quote","model_quote","residual","weight"}),("diagnostics/risk.csv",{"instrument_id","dv01","key_2y","key_5y","key_10y","key_30y"})):
    d=pd.read_csv("outputs/"+f); assert cols<=set(d.columns), f
mc=json.load(open("outputs/diagnostics/model_comparison.json")); assert {"baseline","advanced","selected_model","selection_rationale"}<=set(mc)
s=json.load(open("outputs/diagnostics/sensitivity.json")); assert len(s)>=3 and all(v.get("condition") and v.get("results") and v.get("interpretation") for v in s.values())
h=mc["advanced"]["holdout"]["overall"]; print("OK: rows=%d adv holdout wRMSE=%.3f RMSE=%.3f"%(len(c), h["weighted_rmse_bp"], h["rmse_bp"]))
PY
