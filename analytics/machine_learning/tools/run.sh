#!/usr/bin/env bash
# Build, execute (in place), and error-check one notebook.
# usage: bash run.sh build_nb02.py 02_data_preprocessing_and_features
set -euo pipefail
ROOT=/home/kazumasa/projects
ML="$ROOT/analytics/machine_learning"
build="$1"
nb="$2"
cd "$ROOT"
uv run --no-sync python "$ML/tools/$build"
PYTHONPATH="$ML/src" uv run --no-sync jupyter nbconvert --to notebook --execute --inplace \
  "$ML/notebooks/$nb.ipynb" 2>&1 | tail -2
python3 - "$ML/notebooks/$nb.ipynb" <<'PY'
import json, sys, os
p = sys.argv[1]
nb = json.load(open(p))
errs = [(i, o) for i, c in enumerate(nb["cells"]) if c["cell_type"] == "code"
        for o in c.get("outputs", []) if o.get("output_type") == "error"]
plotly = sum(1 for c in nb["cells"] if c["cell_type"] == "code"
             for o in c.get("outputs", []) if "application/vnd.plotly.v1+json" in o.get("data", {}))
print(f'CHECK {os.path.basename(p)}: errors={len(errs)} plotly={plotly} '
      f'size={os.path.getsize(p)//1024}KB cells={len(nb["cells"])}')
for i, o in errs[:3]:
    print("  ERROR cell", i, o.get("ename"), str(o.get("evalue"))[:300])
PY
